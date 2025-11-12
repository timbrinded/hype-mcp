"""Pytest configuration and shared fixtures for testing."""

import os
from typing import AsyncGenerator
from unittest.mock import AsyncMock, Mock

import pytest

from hype_mcp.asset_router import AssetRouter
from hype_mcp.client_manager import HyperliquidClientManager
from hype_mcp.config import HyperliquidConfig
from hype_mcp.decimal_manager import DecimalPrecisionManager


# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
def test_private_key() -> str:
    """Provide a test private key for testing."""
    return "0xb25c7db31feed9122727bf0939dc769a96564b2de4c4726d035b36ecf1e5b364"


@pytest.fixture
def test_wallet_address() -> str:
    """Provide a test wallet address for testing."""
    return "0x5ce9454909639D2D17A3F753ce7d93fa0b9aB12E"


@pytest.fixture
def test_config(test_private_key: str, test_wallet_address: str) -> HyperliquidConfig:
    """Provide a test configuration."""
    return HyperliquidConfig(
        private_key=test_private_key,
        wallet_address=test_wallet_address,
        testnet=True,
    )


@pytest.fixture
def mock_info_client():
    """Create a mock Info client for testing."""
    mock = Mock()

    # Mock common Info endpoint methods
    mock.all_mids = Mock(return_value={"BTC": "50000", "ETH": "3000"})
    mock.user_state = Mock(
        return_value={
            "assetPositions": [],
            "crossMarginSummary": {"accountValue": "1000.0"},
            "withdrawable": "1000.0",
        }
    )
    mock.open_orders = Mock(return_value=[])
    mock.meta = Mock(
        return_value={
            "universe": [
                {"name": "BTC", "szDecimals": 4, "maxLeverage": 50},
                {"name": "ETH", "szDecimals": 3, "maxLeverage": 50},
            ]
        }
    )
    mock.spot_meta = Mock(
        return_value={
            "tokens": [
                {"name": "PURR", "szDecimals": 2, "index": 0},
                {"name": "HYPE", "szDecimals": 2, "index": 1},
                {"name": "USDC", "szDecimals": 6, "index": 2},
            ],
            "universe": [
                {"tokens": [0, 2], "name": "@700", "index": 700},
                {"tokens": [1, 2], "name": "@701", "index": 701},
            ],
        }
    )
    mock.meta_and_asset_ctxs = Mock(
        return_value=[
            [
                {
                    "coin": "BTC",
                    "markPx": "50000",
                    "dayNtlVlm": "1000000",
                    "funding": "0.0001",
                    "openInterest": "100000",
                },
                {
                    "coin": "ETH",
                    "markPx": "3000",
                    "dayNtlVlm": "500000",
                    "funding": "0.0002",
                    "openInterest": "50000",
                },
            ]
        ]
    )

    return mock


@pytest.fixture
def mock_exchange_client():
    """Create a mock Exchange client for testing."""
    mock = Mock()

    # Mock common Exchange endpoint methods
    mock.order = Mock(
        return_value={
            "status": "ok",
            "response": {
                "type": "order",
                "data": {
                    "statuses": [{"filled": {"totalSz": "0.1", "avgPx": "50000"}}]
                },
            },
        }
    )
    mock.market_open = Mock(
        return_value={
            "status": "ok",
            "response": {
                "type": "order",
                "data": {
                    "statuses": [{"filled": {"totalSz": "0.1", "avgPx": "50000"}}]
                },
            },
        }
    )
    mock.cancel = Mock(
        return_value={
            "status": "ok",
            "response": {"type": "cancel", "data": {"statuses": ["success"]}},
        }
    )
    mock.cancel_all = Mock(
        return_value={
            "status": "ok",
            "response": {
                "type": "cancel",
                "data": {"statuses": ["success", "success"]},
            },
        }
    )
    mock.usd_class_transfer = Mock(
        return_value={
            "status": "ok",
            "response": {
                "type": "usdClassTransfer",
                "data": {
                    "nonce": 1234567890,
                    "amount": "1.0",
                    "toPerp": True,
                },
            },
        }
    )
    mock.wallet = Mock()
    mock.wallet.address = "0x5ce9454909639D2D17A3F753ce7d93fa0b9aB12E"
    mock.account_address = mock.wallet.address

    return mock


@pytest.fixture
def mock_client_manager(
    test_wallet_address: str, mock_info_client, mock_exchange_client
) -> HyperliquidClientManager:
    """Create a mock HyperliquidClientManager for testing."""
    manager = Mock(spec=HyperliquidClientManager)
    manager.wallet_address = test_wallet_address
    manager.testnet = True
    manager.base_url = "https://api.hyperliquid-testnet.xyz"
    manager.info = mock_info_client
    manager.exchange = mock_exchange_client

    return manager


@pytest.fixture
def mock_asset_router(mock_info_client) -> AssetRouter:
    """Provide an AssetRouter backed by the mocked info client."""
    return AssetRouter(mock_info_client)


@pytest.fixture
async def mock_decimal_manager(mock_info_client) -> DecimalPrecisionManager:
    """Create a mock DecimalPrecisionManager for testing."""
    manager = Mock(spec=DecimalPrecisionManager)

    # Mock asset metadata
    manager.get_asset_metadata = AsyncMock(
        return_value=Mock(
            symbol="BTC",
            asset_type="perp",
            sz_decimals=4,
            max_decimals=6,
            max_leverage=50,
        )
    )

    # Mock formatting methods
    manager.format_size_for_api = AsyncMock(return_value="0.1000")
    manager.format_price_for_api = AsyncMock(return_value="50000")
    manager.format_size_for_display = Mock(return_value=0.1)

    return manager


@pytest.fixture
def testnet_env_vars(test_private_key: str, test_wallet_address: str) -> dict:
    """Provide environment variables for testnet configuration."""
    return {
        "HYPERLIQUID_PRIVATE_KEY": test_private_key,
        "HYPERLIQUID_WALLET_ADDRESS": test_wallet_address,
        "HYPERLIQUID_TESTNET": "true",
    }


@pytest.fixture
def mainnet_env_vars(test_private_key: str, test_wallet_address: str) -> dict:
    """Provide environment variables for mainnet configuration."""
    return {
        "HYPERLIQUID_PRIVATE_KEY": test_private_key,
        "HYPERLIQUID_WALLET_ADDRESS": test_wallet_address,
        "HYPERLIQUID_TESTNET": "false",
    }


@pytest.fixture(autouse=True)
def clean_env():
    """Clean environment variables before each test."""
    # Store original environment
    original_env = os.environ.copy()

    # Clear Hyperliquid-related environment variables
    for key in list(os.environ.keys()):
        if key.startswith("HYPERLIQUID_"):
            del os.environ[key]

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# Integration test fixtures (for real API testing)


@pytest.fixture
def integration_config() -> HyperliquidConfig:
    """
    Load configuration for integration tests from environment.

    Integration tests require real credentials to be set in environment variables.
    These tests are skipped if credentials are not available.
    """
    try:
        return HyperliquidConfig.from_env()
    except ValueError:
        pytest.skip("Integration test credentials not configured")


@pytest.fixture
async def integration_client_manager(
    integration_config: HyperliquidConfig,
) -> AsyncGenerator[HyperliquidClientManager, None]:
    """
    Create a real HyperliquidClientManager for integration tests.

    This fixture connects to the actual Hyperliquid testnet API.
    """
    manager = HyperliquidClientManager(
        testnet=integration_config.testnet,
        wallet_address=integration_config.wallet_address,
        private_key=integration_config.private_key,
    )

    # Validate connection
    try:
        await manager.validate_connection()
    except Exception as e:
        pytest.skip(f"Cannot connect to Hyperliquid API: {e}")

    yield manager

    # Cleanup if needed
    # (SDK clients don't require explicit cleanup)


@pytest.fixture
async def integration_decimal_manager(
    integration_client_manager: HyperliquidClientManager,
) -> DecimalPrecisionManager:
    """Create a real DecimalPrecisionManager for integration tests."""
    return DecimalPrecisionManager(integration_client_manager.info)


@pytest.fixture
async def integration_asset_router(
    integration_client_manager: HyperliquidClientManager,
) -> AssetRouter:
    """Create a real AssetRouter for integration tests."""
    return AssetRouter(integration_client_manager.info)


# Pytest configuration


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires real API credentials)",
    )
    config.addinivalue_line("markers", "slow: mark test as slow running")


def pytest_collection_modifyitems(config, items):
    """Automatically mark integration tests."""
    for item in items:
        # Mark tests in test_integration.py as integration tests
        if "test_integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
