"""Hyperliquid client manager for Info and Exchange endpoints."""

import asyncio
from typing import Any, Optional

from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info


class HyperliquidClientManager:
    def __init__(
        self,
        testnet: bool,
        wallet_address: str,
        private_key: str,
        account_address: Optional[str] = None,
    ) -> None:
        self.testnet = testnet
        self.wallet_address = wallet_address
        self.private_key = private_key
        self.account_address = account_address or wallet_address
        self.base_url = (
            "https://api.hyperliquid-testnet.xyz"
            if self.testnet
            else "https://api.hyperliquid.xyz"
        )
        self._info_client: Any = None
        self._exchange_client: Any = None

    @property
    def info(self) -> Any:
        if self._info_client is None:
            self._info_client = Info(base_url=self.base_url, skip_ws=False)
        return self._info_client

    @property
    def exchange(self) -> Any:
        if self._exchange_client is None:
            wallet = Account.from_key(self.private_key)  # pyrefly: ignore
            self._exchange_client = Exchange(
                wallet=wallet,
                base_url=self.base_url,
                account_address=self.account_address,
            )
        return self._exchange_client

    async def validate_connection(self) -> bool:
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(None, self.info.all_mids)
            return bool(result)
        except Exception as exc:  # pragma: no cover - real network failures
            raise ConnectionError(
                f"Failed to connect to Hyperliquid API at {self.base_url}: {exc}"
            ) from exc
