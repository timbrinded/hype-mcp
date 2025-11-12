"""Configuration helpers for the Hyperliquid MCP server."""

import os
from dataclasses import dataclass

from eth_account import Account


def _require_env(key: str, message: str) -> str:
    value = os.getenv(key)
    if not value:
        raise ValueError(message)
    return value


def _bool_from_env(value: str | None, *, default: bool = True) -> bool:
    comparison = (value or ("true" if default else "false")).strip().lower()
    return comparison in {"1", "true", "yes"}


@dataclass(slots=True)
class HyperliquidConfig:
    private_key: str
    wallet_address: str
    testnet: bool = True

    @classmethod
    def from_env(cls) -> "HyperliquidConfig":
        private_key = cls._normalize_private_key(
            _require_env(
                "HYPERLIQUID_PRIVATE_KEY",
                "HYPERLIQUID_PRIVATE_KEY environment variable is required. Please set it to your private key for signing transactions.",
            )
        )
        wallet_address = os.getenv(
            "HYPERLIQUID_WALLET_ADDRESS"
        ) or cls._derive_wallet_address(private_key)
        testnet = _bool_from_env(os.getenv("HYPERLIQUID_TESTNET"))
        return cls(
            private_key=private_key, wallet_address=wallet_address, testnet=testnet
        )

    @staticmethod
    def _normalize_private_key(raw_key: str) -> str:
        key = raw_key.strip()
        if not key.startswith("0x"):
            key = f"0x{key}"
        if len(key) != 66:
            raise ValueError(
                "Invalid private key length: expected 66 characters (including 0x prefix), "
                "got {len_val}. Private key should be a 64-character hex string.".format(
                    len_val=len(key)
                )
            )
        try:
            int(key, 16)
        except ValueError as exc:
            raise ValueError(
                f"Invalid private key format: must be a valid hexadecimal string. Error: {exc}"
            ) from exc
        return key

    @staticmethod
    def _derive_wallet_address(private_key: str) -> str:
        try:
            return Account.from_key(private_key).address
        except Exception as exc:  # pragma: no cover - SDK errors bubble up
            raise ValueError(
                f"Failed to derive wallet address from private key: {exc}"
            ) from exc

    def validate(self) -> None:
        if not self.private_key:
            raise ValueError("Private key cannot be empty")
        if not self.wallet_address:
            raise ValueError("Wallet address cannot be empty")
        if not self.wallet_address.startswith("0x"):
            raise ValueError(
                f"Invalid wallet address format: {self.wallet_address}. Address must start with 0x"
            )
        if len(self.wallet_address) != 42:
            raise ValueError(
                f"Invalid wallet address length: expected 42 characters, got {len(self.wallet_address)}"
            )
        try:
            int(self.wallet_address, 16)
        except ValueError as exc:
            raise ValueError(
                f"Invalid wallet address format: must be a valid hexadecimal string. Error: {exc}"
            ) from exc


def load_config() -> HyperliquidConfig:
    config = HyperliquidConfig.from_env()
    config.validate()
    return config
