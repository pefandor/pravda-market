"""
SQLAlchemy Models для Pravda Market

Базовые модели для MVP:
- User: пользователи из Telegram
- Market: prediction markets
- Order: ставки пользователей
- LedgerEntry: история транзакций
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, BigInteger, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, timezone


def utcnow():
    """Helper for timezone-aware UTC datetime (replaces deprecated utcnow)"""
    return datetime.now(timezone.utc)


Base = declarative_base()


class User(Base):
    """
    Пользователь Telegram

    Минимальная версия без balance column
    (по production плану - balance через ledger, но для MVP упрощаем)
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    orders = relationship("Order", back_populates="user")
    ledger_entries = relationship("LedgerEntry", back_populates="user")
    ton_transactions = relationship("TonTransaction", back_populates="user")
    withdrawal_requests = relationship("WithdrawalRequest", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, first_name='{self.first_name}')>"


class Market(Base):
    """
    Prediction Market

    Рынок для прогнозирования событий
    """
    __tablename__ = "markets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True, index=True)

    # Дедлайн события
    deadline = Column(DateTime, nullable=False)

    # Резолюция
    resolved = Column(Boolean, default=False, index=True)
    resolution_value = Column(Boolean, nullable=True)  # True=YES, False=NO, None=не резолвнут (deprecated, use outcome)
    outcome = Column(String(10), nullable=True)  # "yes" or "no" - which side won
    resolved_at = Column(DateTime, nullable=True)  # When market was resolved

    # Временные поля для цен (в production это будет вычисляться из orderbook)
    # Для MVP - просто храним здесь
    yes_price = Column(Integer, default=5000)  # в basis points (5000 = 50%)
    no_price = Column(Integer, default=5000)   # в basis points

    # Volume (для статистики)
    volume = Column(BigInteger, default=0)  # в копейках

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    orders = relationship("Order", back_populates="market")

    def __repr__(self):
        return f"<Market(id={self.id}, title='{self.title[:50]}...', resolved={self.resolved})>"

    @property
    def yes_price_decimal(self):
        """Цена YES в десятичном формате (0.0 - 1.0)"""
        return self.yes_price / 10000

    @property
    def no_price_decimal(self):
        """Цена NO в десятичном формате (0.0 - 1.0)"""
        return self.no_price / 10000

    @property
    def volume_rubles(self):
        """Volume в рублях"""
        return self.volume / 100


class Order(Base):
    """
    Ордер пользователя (ставка)

    Хранит информацию о размещённой ставке
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=False, index=True)
    side = Column(String(3), nullable=False)  # 'yes' or 'no'
    price_bp = Column(Integer, nullable=False)  # basis points (6500 = 65%)
    amount_kopecks = Column(BigInteger, nullable=False)  # в копейках
    filled_kopecks = Column(BigInteger, default=0)
    status = Column(String(20), default='open', index=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    user = relationship("User", back_populates="orders")
    market = relationship("Market", back_populates="orders")

    # Constraints (CRITICAL - data integrity)
    __table_args__ = (
        CheckConstraint('price_bp >= 0 AND price_bp <= 10000', name='valid_price'),
        CheckConstraint('amount_kopecks > 0', name='positive_amount'),
        CheckConstraint("side IN ('yes', 'no')", name='valid_side'),
        CheckConstraint("status IN ('open', 'partial', 'filled', 'cancelled')", name='valid_status'),
        # Composite index for matching engine performance
        Index('idx_orders_matching', 'market_id', 'side', 'price_bp', 'created_at'),
    )

    def __repr__(self):
        return f"<Order(id={self.id}, user_id={self.user_id}, market_id={self.market_id}, side={self.side}, status={self.status})>"

    @property
    def price_decimal(self) -> float:
        """Цена в десятичном формате (0.0 - 1.0)"""
        return self.price_bp / 10000

    @property
    def amount_rubles(self) -> float:
        """Сумма в рублях"""
        return self.amount_kopecks / 100


class LedgerEntry(Base):
    """
    Запись в ledger (история транзакций)

    Используется для ledger-based balance management
    """
    __tablename__ = "ledger"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount_kopecks = Column(BigInteger, nullable=False)
    type = Column(String(30), nullable=False, index=True)
    reference_id = Column(BigInteger, nullable=True)  # order_id, trade_id
    created_at = Column(DateTime, default=utcnow)

    # Relationship
    user = relationship("User", back_populates="ledger_entries")

    # Composite index для get_available_balance() performance
    __table_args__ = (
        Index('idx_ledger_user_type', 'user_id', 'type'),
    )

    def __repr__(self):
        return f"<LedgerEntry(id={self.id}, user_id={self.user_id}, type={self.type}, amount={self.amount_kopecks/100:.2f}₽)>"


class Trade(Base):
    """
    Исполненная сделка между YES и NO ордерами

    Каждый Trade представляет matched сделку:
    - YES order @ price_bp
    - NO order @ (10000 - price_bp)
    - Settlement: yes_cost + no_cost = amount_kopecks (INVARIANT!)
    """
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=False, index=True)

    # Ордера участники сделки
    yes_order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    no_order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)

    # Детали сделки
    price_bp = Column(Integer, nullable=False)  # YES price in basis points
    amount_kopecks = Column(BigInteger, nullable=False)  # Matched amount

    # Settlement amounts (CRITICAL: must sum to amount_kopecks)
    yes_cost_kopecks = Column(BigInteger, nullable=False)  # YES pays this
    no_cost_kopecks = Column(BigInteger, nullable=False)   # NO pays this

    created_at = Column(DateTime, default=utcnow, index=True)

    # Relationships (for eager loading, prevents N+1 queries)
    yes_order = relationship("Order", foreign_keys=[yes_order_id])
    no_order = relationship("Order", foreign_keys=[no_order_id])

    # Constraints (CRITICAL - data integrity + settlement invariant)
    __table_args__ = (
        CheckConstraint('price_bp >= 0 AND price_bp <= 10000', name='trade_valid_price'),
        CheckConstraint('amount_kopecks > 0', name='trade_positive_amount'),
        CheckConstraint('yes_cost_kopecks >= 0', name='trade_positive_yes_cost'),
        CheckConstraint('no_cost_kopecks >= 0', name='trade_positive_no_cost'),
        # CRITICAL: Settlement invariant at database level!
        CheckConstraint('yes_cost_kopecks + no_cost_kopecks = amount_kopecks', name='trade_settlement_invariant'),
        # Indexes for performance optimization
        Index('idx_trades_market_created', 'market_id', 'created_at'),
        Index('idx_trades_yes_order', 'yes_order_id'),
        Index('idx_trades_no_order', 'no_order_id'),
    )

    def __repr__(self):
        return f"<Trade(id={self.id}, market_id={self.market_id}, amount={self.amount_rubles:.2f}₽, price={self.price_decimal:.2%})>"

    @property
    def price_decimal(self) -> float:
        """Цена в десятичном формате (0.0 - 1.0)"""
        return self.price_bp / 10000

    @property
    def amount_rubles(self) -> float:
        """Сумма в рублях"""
        return self.amount_kopecks / 100


class TonTransaction(Base):
    """
    TON blockchain transaction record

    Отслеживает обработанные транзакции для предотвращения
    двойного зачисления и аудита.
    """
    __tablename__ = "ton_transactions"

    id = Column(Integer, primary_key=True, index=True)

    # Transaction identification (unique on blockchain)
    tx_hash = Column(String(64), unique=True, nullable=False, index=True)
    lt = Column(BigInteger, nullable=False)  # Logical time

    # Transaction details
    sender_address = Column(String(68), nullable=False)  # TON address
    amount_nanoton = Column(BigInteger, nullable=False)

    # Parsed memo data
    telegram_id = Column(BigInteger, nullable=False, index=True)

    # Processing status
    status = Column(String(20), default='pending', nullable=False, index=True)
    # pending - detected but not processed
    # confirmed - confirmed on blockchain
    # credited - balance credited to user
    # failed - processing failed

    # Links to our system
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    ledger_entry_id = Column(Integer, ForeignKey("ledger.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utcnow)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="ton_transactions")
    ledger_entry = relationship("LedgerEntry")

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'confirmed', 'credited', 'failed')", name='ton_tx_valid_status'),
        CheckConstraint('amount_nanoton > 0', name='ton_tx_positive_amount'),
        Index('idx_ton_tx_status_created', 'status', 'created_at'),
    )

    def __repr__(self):
        return f"<TonTransaction(hash={self.tx_hash[:16]}..., amount={self.amount_nanoton/1e9:.4f} TON, status={self.status})>"

    @property
    def amount_ton(self) -> float:
        """Amount in TON"""
        return self.amount_nanoton / 1e9


class WithdrawalRequest(Base):
    """
    Withdrawal request for TON

    Заявка на вывод средств через TON блокчейн.
    Обрабатывается оператором через batch withdrawals.
    """
    __tablename__ = "withdrawal_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Destination address
    ton_address = Column(String(68), nullable=False)

    # Amount to withdraw (in nanoTON)
    amount_nanoton = Column(BigInteger, nullable=False)

    # Processing status
    status = Column(String(20), default='pending', nullable=False, index=True)
    # pending - waiting for processing
    # processing - operator is processing
    # completed - successfully sent
    # failed - processing failed
    # cancelled - cancelled by user or admin

    # Transaction hash (filled after sending)
    tx_hash = Column(String(64), nullable=True, unique=True)

    # Error message (if failed)
    error_message = Column(Text, nullable=True)

    # Links to ledger
    ledger_entry_id = Column(Integer, ForeignKey("ledger.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utcnow)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="withdrawal_requests")
    ledger_entry = relationship("LedgerEntry")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')",
            name='withdrawal_valid_status'
        ),
        CheckConstraint('amount_nanoton > 0', name='withdrawal_positive_amount'),
        Index('idx_withdrawal_status_created', 'status', 'created_at'),
        Index('idx_withdrawal_user_status', 'user_id', 'status'),
    )

    def __repr__(self):
        return f"<WithdrawalRequest(id={self.id}, user_id={self.user_id}, amount={self.amount_ton:.4f} TON, status={self.status})>"

    @property
    def amount_ton(self) -> float:
        """Amount in TON"""
        return self.amount_nanoton / 1e9


# В будущем добавим:
# - PaymentRequest (платежи)
# - OrderEvent (audit trail)
