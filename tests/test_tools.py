"""Tests for MCP tools."""

import pytest
from unittest.mock import Mock

from hype_mcp.client_manager import HyperliquidClientManager
from hype_mcp.tools import (
    get_account_state,
    get_all_assets,
    get_market_data,
    get_open_orders,
)


@pytest.fixture
def mock_client_manager():
    """Create a mock client manager for testing."""
    manager = Mock(spec=HyperliquidClientManager)
    manager.wallet_address = "0x1234567890123456789012345678901234567890"
    manager.info = Mock()
    return manager


@pytest.mark.asyncio
async def test_get_account_state_success(mock_client_manager):
    """Test get_account_state with successful response."""
    # Mock the user_state response
    mock_response = {
        "assetPositions": [],
        "crossMarginSummary": {"accountValue": "1000.0"},
        "withdrawable": "1000.0",
    }
    mock_client_manager.info.user_state.return_value = mock_response

    result = await get_account_state(mock_client_manager)

    assert result["success"] is True
    assert result["data"] == mock_response
    mock_client_manager.info.user_state.assert_called_once()


@pytest.mark.asyncio
async def test_get_account_state_with_custom_address(mock_client_manager):
    """Test get_account_state with custom user address."""
    custom_address = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
    mock_response = {"assetPositions": []}
    mock_client_manager.info.user_state.return_value = mock_response

    result = await get_account_state(mock_client_manager, user_address=custom_address)

    assert result["success"] is True
    mock_client_manager.info.user_state.assert_called_once_with(custom_address)


@pytest.mark.asyncio
async def test_get_open_orders_success(mock_client_manager):
    """Test get_open_orders with successful response."""
    mock_response = [
        {
            "oid": 123,
            "coin": "BTC",
            "side": "B",
            "sz": "0.1",
            "px": "50000",
        }
    ]
    mock_client_manager.info.open_orders.return_value = mock_response

    result = await get_open_orders(mock_client_manager)

    assert result["success"] is True
    assert result["data"] == mock_response
    mock_client_manager.info.open_orders.assert_called_once()


@pytest.mark.asyncio
async def test_get_market_data_perp_success(mock_client_manager):
    """Test get_market_data for perpetual asset."""
    symbol = "BTC"
    mock_client_manager.info.all_mids.return_value = {symbol: "50000"}
    mock_client_manager.info.meta.return_value = {
        "universe": [{"name": symbol, "szDecimals": 4}]
    }
    mock_client_manager.info.meta_and_asset_ctxs.return_value = [
        [
            {
                "coin": symbol,
                "markPx": "50000",
                "dayNtlVlm": "1000000",
                "funding": "0.0001",
            }
        ]
    ]
    mock_client_manager.info.spot_meta.return_value = {"tokens": []}

    result = await get_market_data(mock_client_manager, symbol)

    assert result["success"] is True
    assert result["data"]["coin"] == symbol
    assert "markPx" in result["data"]


@pytest.mark.asyncio
async def test_get_market_data_invalid_symbol(mock_client_manager):
    """Test get_market_data with invalid symbol."""
    mock_client_manager.info.all_mids.return_value = {}
    mock_client_manager.info.meta.return_value = {"universe": []}
    mock_client_manager.info.spot_meta.return_value = {"tokens": []}

    result = await get_market_data(mock_client_manager, "INVALID")

    assert result["success"] is False
    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_get_all_assets_success(mock_client_manager):
    """Test get_all_assets with successful response."""
    mock_client_manager.info.meta.return_value = {
        "universe": [
            {"name": "BTC", "szDecimals": 4, "maxLeverage": 50},
            {"name": "ETH", "szDecimals": 3, "maxLeverage": 50},
        ]
    }
    mock_client_manager.info.spot_meta.return_value = {
        "tokens": [
            {"name": "PURR", "szDecimals": 2, "index": 0},
        ]
    }

    result = await get_all_assets(mock_client_manager)

    assert result["success"] is True
    assert "perps" in result["data"]
    assert "spot" in result["data"]
    assert len(result["data"]["perps"]) == 2
    assert len(result["data"]["spot"]) == 1
    assert result["data"]["perps"][0]["name"] == "BTC"
    assert result["data"]["spot"][0]["name"] == "PURR"


@pytest.mark.asyncio
async def test_error_handling(mock_client_manager):
    """Test error handling in tools."""
    mock_client_manager.info.user_state.side_effect = Exception("API Error")

    result = await get_account_state(mock_client_manager)

    assert result["success"] is False
    assert "error" in result
    assert "API Error" in result["error"]
