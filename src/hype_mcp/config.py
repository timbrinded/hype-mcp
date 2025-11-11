"""Configuration and initialization for the Hyperliquid MCP server."""

import os
from dataclasses import dataclass
from typing import Optional

from eth_account import Account


@dataclass
class HyperliquidConfig:
    """Configuration for the Hyperliquid MCP server."""

    private_key: str
    wallet_address: str
    testnet: bool = True

    @classmethod
    def from_env(cls) -> "HyperliquidConfig":
        """
        Load configuration from environment variables.

        Environment variables:
            HYPERLIQUID_PRIVATE_KEY: Private key for signing transactions (required)
            HYPERLIQUID_WALLET_ADDRESS: Wallet address (optional, derived from private key if not provided)
            HYPERLIQUID_TESTNET: Whether to use testnet (default: "true")

        Returns:
            HyperliquidConfig: Validated configuration

        Raises:
            ValueError: If private key is missing or invalid
        """
        private_key = os.getenv("HYPERLIQUID_PRIVATE_KEY")
        if not private_key:
            raise ValueError(
                "HYPERLIQUID_PRIVATE_KEY environment variable is required. "
                "Please set it to your private key for signing transactions."
            )

        # Validate and normalize private key format
        private_key = cls._normalize_private_key(private_key)

        # Get wallet address or derive from private key
        wallet_address = os.getenv("HYPERLIQUID_WALLET_ADDRESS")
        if not wallet_address:
            wallet_address = cls._derive_wallet_address(private_key)

        # Parse testnet flag
        testnet_str = os.getenv("HYPERLIQUID_TESTNET", "true").lower()
        testnet = testnet_str in ("true", "1", "yes")

        return cls(
            private_key=private_key,
            wallet_address=wallet_address,
            testnet=testnet,
        )

    @staticmethod
    def _normalize_private_key(private_key: str) -> str:
        """
        Normalize private key format.

        Args:
            private_key: Private key in hex format (with or without 0x prefix)

        Returns:
            str: Normalized private key with 0x prefix

        Raises:
            ValueError: If private key format is invalid
        """
        private_key = private_key.strip()

        # Add 0x prefix if missing
        if not private_key.startswith("0x"):
            private_key = f"0x{private_key}"

        # Validate length (64 hex chars + 0x prefix = 66 total)
        if len(private_key) != 66:
            raise ValueError(
                f"Invalid private key length: expected 66 characters (including 0x prefix), "
                f"got {len(private_key)}. Private key should be a 64-character hex string."
            )

        # Validate hex format
        try:
            int(private_key, 16)
        except ValueError as e:
            raise ValueError(
                f"Invalid private key format: must be a valid hexadecimal string. Error: {e}"
            ) from e

        return private_key

    @staticmethod
    def _derive_wallet_address(private_key: str) -> str:
        """
        Derive wallet address from private key.

        Args:
            private_key: Private key in hex format with 0x prefix

        Returns:
            str: Ethereum wallet address derived from the private key

        Raises:
            ValueError: If private key is invalid
        """
        try:
            account = Account.from_key(private_key)
            return account.address
        except Exception as e:
            raise ValueError(
                f"Failed to derive wallet address from private key: {e}"
            ) from e

    def validate(self) -> None:
        """
        Validate the configuration.

        Raises:
            ValueError: If any configuration value is invalid
        """
        # Validate private key
        if not self.private_key:
            raise ValueError("Private key cannot be empty")

        # Validate wallet address format
        if not self.wallet_address:
            raise ValueError("Wallet address cannot be empty")

        if not self.wallet_address.startswith("0x"):
            raise ValueError(
                f"Invalid wallet address format: {self.wallet_address}. "
                "Address must start with 0x"
            )

        if len(self.wallet_address) != 42:
            raise ValueError(
                f"Invalid wallet address length: expected 42 characters, "
                f"got {len(self.wallet_address)}"
            )

        # Validate hex format
        try:
            int(self.wallet_address, 16)
        except ValueError as e:
            raise ValueError(
                f"Invalid wallet address format: must be a valid hexadecimal string. Error: {e}"
            ) from e


def load_config() -> HyperliquidConfig:
    """
    Load and validate configuration from environment variables.

    Returns:
        HyperliquidConfig: Validated configuration

    Raises:
        ValueError: If configuration is invalid or missing required values
    """
    config = HyperliquidConfig.from_env()
    config.validate()
    return config
