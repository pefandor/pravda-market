"""
TonCenter API Client

Клиент для работы с TonCenter API (indexer для TON блокчейна).
Поддерживает rate limiting и retries.
"""

import asyncio
import logging
from typing import Any
from dataclasses import dataclass

import httpx

from .config import ton_settings

logger = logging.getLogger(__name__)


@dataclass
class Transaction:
    """Parsed TON transaction"""
    hash: str
    lt: int  # Logical time
    utime: int  # Unix timestamp
    sender: str
    destination: str
    value_nanoton: int
    body_hash: str
    body_data: bytes | None
    success: bool


class TonCenterError(Exception):
    """TonCenter API error"""
    pass


class RateLimitError(TonCenterError):
    """Rate limit exceeded"""
    pass


class TonCenterClient:
    """
    Async client for TonCenter API

    Handles:
    - Rate limiting with automatic retries
    - Transaction fetching and parsing
    - Error handling
    """

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
    ):
        self.api_url = api_url or ton_settings.TONCENTER_API_URL
        self.api_key = api_key or ton_settings.TONCENTER_API_KEY
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None or self._client.is_closed:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                headers=headers,
                timeout=30.0,
            )
        return self._client

    async def close(self):
        """Close HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        use_post: bool = False,
    ) -> Any:
        """
        Make API request with retries and rate limit handling

        Args:
            method: API method name (e.g., "getTransactions")
            params: Request parameters
            use_post: Use POST instead of GET

        Returns:
            API response result

        Raises:
            TonCenterError: On API errors
            RateLimitError: On rate limit (after all retries exhausted)
        """
        client = await self._get_client()
        last_error: Exception | None = None

        for attempt in range(ton_settings.API_RETRY_ATTEMPTS):
            try:
                if use_post:
                    response = await client.post(f"/{method}", json=params or {})
                else:
                    response = await client.get(f"/{method}", params=params or {})

                if response.status_code == 429:
                    # Rate limited
                    delay = ton_settings.API_RETRY_DELAY_SECONDS * (attempt + 1)
                    logger.warning(
                        "TonCenter rate limit hit, retrying in %.1fs (attempt %d/%d)",
                        delay,
                        attempt + 1,
                        ton_settings.API_RETRY_ATTEMPTS,
                    )
                    await asyncio.sleep(delay)
                    continue

                response.raise_for_status()
                data = response.json()

                if not data.get("ok"):
                    error_msg = data.get("error") or data.get("result") or "Unknown error"
                    raise TonCenterError(f"API error: {error_msg}")

                return data.get("result")

            except httpx.HTTPStatusError as e:
                last_error = TonCenterError(f"HTTP error {e.response.status_code}: {e.response.text}")
                if e.response.status_code >= 500:
                    # Server error, retry
                    await asyncio.sleep(ton_settings.API_RETRY_DELAY_SECONDS)
                    continue
                raise last_error

            except httpx.RequestError as e:
                last_error = TonCenterError(f"Request error: {e}")
                await asyncio.sleep(ton_settings.API_RETRY_DELAY_SECONDS)
                continue

        # All retries exhausted
        if last_error:
            raise last_error
        raise RateLimitError("Rate limit exceeded after all retries")

    async def get_transactions(
        self,
        address: str,
        limit: int = 50,
        lt: int | None = None,
        hash: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get transactions for an address

        Args:
            address: TON address to query
            limit: Maximum number of transactions to return
            lt: Start from this logical time (for pagination)
            hash: Start from this transaction hash (for pagination)

        Returns:
            List of transaction dictionaries
        """
        params: dict[str, Any] = {
            "address": address,
            "limit": min(limit, ton_settings.MAX_TRANSACTIONS_PER_POLL),
        }
        if lt is not None:
            params["lt"] = lt
        if hash is not None:
            params["hash"] = hash

        result = await self._request("getTransactions", params)

        if not isinstance(result, list):
            logger.error("Unexpected getTransactions response: %s", type(result))
            return []

        return result

    async def get_address_info(self, address: str) -> dict[str, Any]:
        """Get address information including balance"""
        return await self._request("getAddressInformation", {"address": address})

    async def get_contract_state(self, address: str) -> dict[str, Any]:
        """Get contract state"""
        return await self._request("getAddressState", {"address": address})

    def parse_transaction(self, tx_data: dict[str, Any]) -> Transaction | None:
        """
        Parse raw transaction data into Transaction object

        Args:
            tx_data: Raw transaction from API

        Returns:
            Parsed Transaction or None if parsing fails
        """
        try:
            tx_id = tx_data.get("transaction_id", {})
            in_msg = tx_data.get("in_msg", {})

            # Extract basic fields
            tx_hash = tx_id.get("hash", "")
            lt = int(tx_id.get("lt", 0))
            utime = int(tx_data.get("utime", 0))

            # Sender and destination
            sender = in_msg.get("source", "")
            destination = in_msg.get("destination", "")

            # Value in nanoTON
            value_str = in_msg.get("value", "0")
            value_nanoton = int(value_str) if value_str else 0

            # Message body
            body_hash = in_msg.get("body_hash", "")
            msg_data = in_msg.get("msg_data", {})

            # Try to decode body
            body_data = None
            if msg_data.get("body"):
                import base64
                try:
                    body_data = base64.b64decode(msg_data["body"])
                except Exception:
                    pass

            # Check if transaction was successful (no out_msgs with bounce)
            out_msgs = tx_data.get("out_msgs", [])
            success = True
            for out_msg in out_msgs:
                # If there's a bounce message back to sender, transaction failed
                if out_msg.get("destination") == sender and out_msg.get("bounce"):
                    success = False
                    break

            return Transaction(
                hash=tx_hash,
                lt=lt,
                utime=utime,
                sender=sender,
                destination=destination,
                value_nanoton=value_nanoton,
                body_hash=body_hash,
                body_data=body_data,
                success=success,
            )

        except Exception as e:
            logger.error("Failed to parse transaction: %s", e, exc_info=True)
            return None

    def parse_deposit_memo(self, body_data: bytes) -> int | None:
        """
        Parse deposit message body to extract telegram_id

        Deposit message format:
        - 32 bits: opcode (0x00000001)
        - 64 bits: telegram_id

        Args:
            body_data: Raw message body bytes

        Returns:
            telegram_id if valid deposit, None otherwise
        """
        if not body_data or len(body_data) < 12:
            return None

        try:
            # First 4 bytes = opcode (big endian)
            opcode = int.from_bytes(body_data[:4], "big")

            if opcode != ton_settings.DEPOSIT_OPCODE:
                logger.debug("Not a deposit opcode: 0x%08x", opcode)
                return None

            # Next 8 bytes = telegram_id (big endian)
            telegram_id = int.from_bytes(body_data[4:12], "big")

            if telegram_id <= 0:
                logger.warning("Invalid telegram_id in deposit: %d", telegram_id)
                return None

            return telegram_id

        except Exception as e:
            logger.error("Failed to parse deposit memo: %s", e)
            return None


# Singleton instance for convenience
_client: TonCenterClient | None = None


async def get_ton_client() -> TonCenterClient:
    """Get global TonCenter client instance"""
    global _client
    if _client is None:
        _client = TonCenterClient()
    return _client
