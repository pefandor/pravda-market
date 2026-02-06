"""
TON Deposit Indexer

Сервис для отслеживания депозитов в Escrow контракт.
Периодически проверяет новые транзакции и зачисляет балансы.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable, Awaitable, TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import ton_settings
from .client import TonCenterClient, Transaction, get_ton_client

# Type hints only - avoid circular imports
if TYPE_CHECKING:
    from ..db.models import User, LedgerEntry, TonTransaction

logger = logging.getLogger(__name__)


def _get_session_local():
    """Lazy import of SessionLocal to avoid circular imports"""
    from ..db.session import SessionLocal
    return SessionLocal


def _get_models():
    """Lazy import of models to avoid circular imports"""
    from ..db.models import User, LedgerEntry, TonTransaction
    return User, LedgerEntry, TonTransaction


class DepositIndexer:
    """
    Deposit indexer service

    Polls TON blockchain for new deposits and credits user balances.
    """

    def __init__(
        self,
        client: TonCenterClient | None = None,
        escrow_address: str | None = None,
        polling_interval: int | None = None,
        db_session_factory: Callable[[], Session] | None = None,
    ):
        self.client = client
        self.escrow_address = escrow_address or ton_settings.ESCROW_ADDRESS
        self.polling_interval = polling_interval or ton_settings.POLLING_INTERVAL_SECONDS
        self._db_session_factory = db_session_factory

        self._running = False
        self._task: asyncio.Task | None = None
        self._last_lt: int | None = None  # Last processed logical time

    @property
    def db_session_factory(self):
        """Lazy-loaded session factory"""
        if self._db_session_factory is None:
            self._db_session_factory = _get_session_local()
        return self._db_session_factory

    async def start(self):
        """Start the indexer background task"""
        if self._running:
            logger.warning("Indexer already running")
            return

        if self.client is None:
            self.client = await get_ton_client()

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Deposit indexer started (address=%s, interval=%ds)",
            self.escrow_address,
            self.polling_interval,
        )

    async def stop(self):
        """Stop the indexer"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Deposit indexer stopped")

    async def _run_loop(self):
        """Main polling loop"""
        while self._running:
            try:
                await self._poll_deposits()
            except Exception as e:
                logger.error("Error in deposit polling: %s", e, exc_info=True)

            await asyncio.sleep(self.polling_interval)

    async def _poll_deposits(self):
        """Poll for new deposits and process them"""
        if not self.client:
            return

        # Get recent transactions
        transactions = await self.client.get_transactions(
            address=self.escrow_address,
            limit=ton_settings.MAX_TRANSACTIONS_PER_POLL,
        )

        if not transactions:
            logger.debug("No transactions found")
            return

        logger.debug("Found %d transactions to process", len(transactions))

        # Process each transaction
        processed_count = 0
        for tx_data in transactions:
            try:
                parsed = self.client.parse_transaction(tx_data)
                if parsed and await self._process_transaction(parsed):
                    processed_count += 1
            except Exception as e:
                logger.error(
                    "Error processing transaction: %s",
                    e,
                    exc_info=True,
                    extra={"tx_data": tx_data},
                )

        if processed_count > 0:
            logger.info("Processed %d new deposits", processed_count)

    async def _process_transaction(self, tx: Transaction) -> bool:
        """
        Process a single transaction

        Returns True if this was a new deposit that was credited.
        """
        # Skip if not a successful incoming transaction
        if not tx.success or not tx.sender:
            return False

        # Skip if amount is below minimum
        if tx.value_nanoton < ton_settings.MIN_DEPOSIT_NANOTON:
            logger.debug(
                "Transaction %s below minimum deposit (%.4f TON)",
                tx.hash[:16],
                tx.value_nanoton / 1e9,
            )
            return False

        # Parse deposit memo to get telegram_id
        telegram_id = self.client.parse_deposit_memo(tx.body_data) if self.client else None
        if telegram_id is None:
            logger.debug("Transaction %s is not a valid deposit (no telegram_id)", tx.hash[:16])
            return False

        # Check if already processed (using database)
        with self.db_session_factory() as db:
            return self._credit_deposit(db, tx, telegram_id)

    def _credit_deposit(
        self,
        db: Session,
        tx: Transaction,
        telegram_id: int,
    ) -> bool:
        """
        Credit deposit to user balance

        Args:
            db: Database session
            tx: Parsed transaction
            telegram_id: User's Telegram ID from memo

        Returns:
            True if deposit was credited, False if already processed
        """
        User, LedgerEntry, TonTransaction = _get_models()

        # Check if transaction already processed
        existing = db.execute(
            select(TonTransaction).where(TonTransaction.tx_hash == tx.hash)
        ).scalar_one_or_none()

        if existing:
            logger.debug("Transaction %s already processed", tx.hash[:16])
            return False

        # Find or create user
        user = db.execute(
            select(User).where(User.telegram_id == telegram_id)
        ).scalar_one_or_none()

        if not user:
            logger.warning(
                "User with telegram_id=%d not found for deposit %s. Creating placeholder.",
                telegram_id,
                tx.hash[:16],
            )
            # Create user with minimal info (will be updated on first login)
            user = User(
                telegram_id=telegram_id,
                username=None,
                first_name=f"TON User {telegram_id}",
            )
            db.add(user)
            db.flush()  # Get user.id

        # Convert nanoTON to kopecks using current rate
        amount_kopecks = self._convert_to_kopecks(tx.value_nanoton)

        # Create ledger entry
        ledger_entry = LedgerEntry(
            user_id=user.id,
            amount_kopecks=amount_kopecks,
            type="deposit",
            reference_id=None,  # Will be updated to ton_transaction.id
        )
        db.add(ledger_entry)
        db.flush()

        # Create TonTransaction record
        ton_tx = TonTransaction(
            tx_hash=tx.hash,
            lt=tx.lt,
            sender_address=tx.sender,
            amount_nanoton=tx.value_nanoton,
            telegram_id=telegram_id,
            status="credited",
            user_id=user.id,
            ledger_entry_id=ledger_entry.id,
        )
        db.add(ton_tx)

        # Update ledger entry reference
        ledger_entry.reference_id = ton_tx.id

        db.commit()

        logger.info(
            "Credited deposit: user=%d, amount=%.4f TON (%.2f RUB), tx=%s",
            telegram_id,
            tx.value_nanoton / 1e9,
            amount_kopecks / 100,
            tx.hash[:16],
        )

        return True

    def _convert_to_kopecks(self, nanoton: int) -> int:
        """
        Convert nanoTON to kopecks

        Uses configured rate. In production, this should use
        a real-time exchange rate from an oracle or API.
        """
        ton = nanoton / 1e9
        kopecks = int(ton * ton_settings.TON_TO_KOPECKS_RATE)
        return kopecks


# ============================================================================
# Background task management
# ============================================================================

_indexer: DepositIndexer | None = None


async def start_deposit_indexer():
    """Start global deposit indexer"""
    global _indexer
    if _indexer is None:
        _indexer = DepositIndexer()
    await _indexer.start()


async def stop_deposit_indexer():
    """Stop global deposit indexer"""
    global _indexer
    if _indexer:
        await _indexer.stop()
        _indexer = None


def get_deposit_indexer() -> DepositIndexer | None:
    """Get global indexer instance"""
    return _indexer


# ============================================================================
# Manual processing (for testing/debugging)
# ============================================================================

async def process_deposit_by_hash(tx_hash: str) -> bool:
    """
    Manually process a specific transaction by hash

    Useful for testing or re-processing failed transactions.
    """
    client = await get_ton_client()

    # Get transactions and find the one with matching hash
    transactions = await client.get_transactions(
        address=ton_settings.ESCROW_ADDRESS,
        limit=100,
    )

    for tx_data in transactions:
        tx_id = tx_data.get("transaction_id", {})
        if tx_id.get("hash") == tx_hash:
            parsed = client.parse_transaction(tx_data)
            if parsed:
                indexer = DepositIndexer(client=client)
                return await indexer._process_transaction(parsed)

    logger.error("Transaction %s not found", tx_hash)
    return False
