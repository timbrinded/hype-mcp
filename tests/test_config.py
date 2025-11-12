"""Tests for configuration and initialization."""

import os
from unittest.mock import patch

import pytest

from hype_mcp.config import HyperliquidConfig, load_config


class TestHyperliquidConfig:
    """Tests for HyperliquidConfig class."""

    def test_from_env_with_all_values(self):
        """Test loading configuration with all environment variables set."""
        env_vars = {
            "HYPERLIQUID_PRIVATE_KEY": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "HYPERLIQUID_WALLET_ADDRESS": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1",
            "HYPERLIQUID_TESTNET": "true",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = HyperliquidConfig.from_env()

            assert config.private_key == env_vars["HYPERLIQUID_PRIVATE_KEY"]
            assert config.wallet_address == env_vars["HYPERLIQUID_WALLET_ADDRESS"]
            assert config.testnet is True

    def test_from_env_derives_wallet_address(self):
        """Test that wallet address is derived from private key when not provided."""
        # Known private key and its corresponding address
        private_key = (
            "0xb25c7db31feed9122727bf0939dc769a96564b2de4c4726d035b36ecf1e5b364"
        )
        expected_address = "0x5ce9454909639D2D17A3F753ce7d93fa0b9aB12E"

        env_vars = {
            "HYPERLIQUID_PRIVATE_KEY": private_key,
            "HYPERLIQUID_TESTNET": "true",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = HyperliquidConfig.from_env()

            assert config.wallet_address == expected_address
            assert config.private_key == private_key

    def test_from_env_missing_private_key(self):
        """Test that missing private key raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="HYPERLIQUID_PRIVATE_KEY.*required"):
                HyperliquidConfig.from_env()

    def test_from_env_testnet_flag_variations(self):
        """Test various testnet flag values."""
        private_key = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )

        # Test true values
        for value in ["true", "True", "TRUE", "1", "yes"]:
            with patch.dict(
                os.environ,
                {"HYPERLIQUID_PRIVATE_KEY": private_key, "HYPERLIQUID_TESTNET": value},
                clear=True,
            ):
                config = HyperliquidConfig.from_env()
                assert config.testnet is True

        # Test false values
        for value in ["false", "False", "FALSE", "0", "no"]:
            with patch.dict(
                os.environ,
                {"HYPERLIQUID_PRIVATE_KEY": private_key, "HYPERLIQUID_TESTNET": value},
                clear=True,
            ):
                config = HyperliquidConfig.from_env()
                assert config.testnet is False

    def test_from_env_default_testnet(self):
        """Test that testnet defaults to True when not specified."""
        private_key = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )

        with patch.dict(
            os.environ, {"HYPERLIQUID_PRIVATE_KEY": private_key}, clear=True
        ):
            config = HyperliquidConfig.from_env()
            assert config.testnet is True

    def test_normalize_private_key_with_prefix(self):
        """Test normalizing private key that already has 0x prefix."""
        key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        normalized = HyperliquidConfig._normalize_private_key(key)
        assert normalized == key

    def test_normalize_private_key_without_prefix(self):
        """Test normalizing private key without 0x prefix."""
        key = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        expected = f"0x{key}"
        normalized = HyperliquidConfig._normalize_private_key(key)
        assert normalized == expected

    def test_normalize_private_key_invalid_length(self):
        """Test that invalid private key length raises ValueError."""
        with pytest.raises(ValueError, match="Invalid private key length"):
            HyperliquidConfig._normalize_private_key("0x123")

    def test_normalize_private_key_invalid_hex(self):
        """Test that invalid hex format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid private key format"):
            HyperliquidConfig._normalize_private_key(
                "0xGGGG567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
            )

    def test_derive_wallet_address(self):
        """Test wallet address derivation from private key."""
        private_key = (
            "0xb25c7db31feed9122727bf0939dc769a96564b2de4c4726d035b36ecf1e5b364"
        )
        expected_address = "0x5ce9454909639D2D17A3F753ce7d93fa0b9aB12E"

        address = HyperliquidConfig._derive_wallet_address(private_key)
        assert address == expected_address

    def test_derive_wallet_address_invalid_key(self):
        """Test that invalid private key raises ValueError during derivation."""
        with pytest.raises(ValueError, match="Failed to derive wallet address"):
            HyperliquidConfig._derive_wallet_address("0xinvalid")

    def test_validate_success(self):
        """Test successful validation."""
        config = HyperliquidConfig(
            private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1",
            testnet=True,
        )
        config.validate()  # Should not raise

    def test_validate_empty_private_key(self):
        """Test validation fails with empty private key."""
        config = HyperliquidConfig(
            private_key="",
            wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1",
            testnet=True,
        )
        with pytest.raises(ValueError, match="Private key cannot be empty"):
            config.validate()

    def test_validate_empty_wallet_address(self):
        """Test validation fails with empty wallet address."""
        config = HyperliquidConfig(
            private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            wallet_address="",
            testnet=True,
        )
        with pytest.raises(ValueError, match="Wallet address cannot be empty"):
            config.validate()

    def test_validate_wallet_address_missing_prefix(self):
        """Test validation fails when wallet address missing 0x prefix."""
        config = HyperliquidConfig(
            private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            wallet_address="742d35Cc6634C0532925a3b844Bc9e7595f0bEb1",
            testnet=True,
        )
        with pytest.raises(ValueError, match="must start with 0x"):
            config.validate()

    def test_validate_wallet_address_invalid_length(self):
        """Test validation fails with invalid wallet address length."""
        config = HyperliquidConfig(
            private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            wallet_address="0x123",
            testnet=True,
        )
        with pytest.raises(ValueError, match="Invalid wallet address length"):
            config.validate()

    def test_validate_wallet_address_invalid_hex(self):
        """Test validation fails with invalid hex in wallet address."""
        config = HyperliquidConfig(
            private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            wallet_address="0xGGGG35Cc6634C0532925a3b844Bc9e7595f0bEb1",
            testnet=True,
        )
        with pytest.raises(ValueError, match="Invalid wallet address format"):
            config.validate()


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_success(self):
        """Test successful configuration loading."""
        env_vars = {
            "HYPERLIQUID_PRIVATE_KEY": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "HYPERLIQUID_WALLET_ADDRESS": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1",
            "HYPERLIQUID_TESTNET": "true",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config()
            assert config.private_key == env_vars["HYPERLIQUID_PRIVATE_KEY"]
            assert config.wallet_address == env_vars["HYPERLIQUID_WALLET_ADDRESS"]
            assert config.testnet is True

    def test_load_config_missing_private_key(self):
        """Test that load_config raises ValueError when private key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="HYPERLIQUID_PRIVATE_KEY.*required"):
                load_config()
