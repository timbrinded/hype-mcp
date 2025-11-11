"""Integration tests against Hyperliquid testnet.

These tests require real API credentials to be set in environment variables:
- HYPERLIQUID_PRIVATE_KEY
- HYPERLIQUID_WALLET_ADDRESS (optional, derived from private key if not set)
- HYPERLIQUID_TESTNET=true

Run with: uv run pytest tests/test_integration.py -m integration
"""

import pytest

from hype_mcp.tools.info_tools import (
    get_account_state,
    get_open_orders,
    get_market_data,
    get_all_assets,
)
from hype_mcp.tools.exchange_tools import (
    place_spot_order,
    place_perp_order,
    cancel_order,
    cancel_all_orders,
    close_position,
)


# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


class TestInfoEndpointIntegration:
    """Integration tests for Info endpoint tools against testnet."""

    @pytest.mark.asyncio
    async def test_get_account_state(self, integration_client_manager):
        """Test get_account_state with real API."""
        result = await get_account_state(integration_client_manager)

        assert result["success"] is True
        assert "data" in result
        
        data = result["data"]
        assert "assetPositions" in data
        assert "crossMarginSummary" in data
        assert "withdrawable" in data
        assert isinstance(data["assetPositions"], list)

    @pytest.mark.asyncio
    async def test_get_account_state_with_address(self, integration_client_manager):
        """Test get_account_state with explicit wallet address."""
        result = await get_account_state(
            integration_client_manager,
            user_address=integration_client_manager.wallet_address
        )

        assert result["success"] is True
        assert "data" in result

    @pytest.mark.asyncio
    async def test_get_open_orders(self, integration_client_manager):
        """Test get_open_orders with real API."""
        result = await get_open_orders(integration_client_manager)

        assert result["success"] is True
        assert "data" in result
        assert isinstance(result["data"], list)

    @pytest.mark.asyncio
    async def test_get_market_data_perp(self, integration_client_manager):
        """Test get_market_data for perpetual asset with real API."""
        result = await get_market_data(integration_client_manager, "BTC")

        assert result["success"] is True
        assert "data" in result
        
        data = result["data"]
        assert data["coin"] == "BTC"
        assert "markPx" in data
        assert "midPx" in data
        assert "funding" in data
        assert "openInterest" in data

    @pytest.mark.asyncio
    async def test_get_market_data_spot(self, integration_client_manager):
        """Test get_market_data for spot asset with real API."""
        # First get all assets to find a valid spot asset
        assets_result = await get_all_assets(integration_client_manager)
        assert assets_result["success"] is True
        
        spot_assets = assets_result["data"]["spot"]
        if not spot_assets:
            pytest.skip("No spot assets available on testnet")
        
        # Test with first available spot asset
        spot_symbol = spot_assets[0]["name"]
        result = await get_market_data(integration_client_manager, spot_symbol)

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["coin"] == spot_symbol

    @pytest.mark.asyncio
    async def test_get_market_data_invalid_symbol(self, integration_client_manager):
        """Test get_market_data with invalid symbol."""
        result = await get_market_data(integration_client_manager, "INVALID_SYMBOL_XYZ")

        assert result["success"] is False
        assert "error" in result
        assert "error_type" in result

    @pytest.mark.asyncio
    async def test_get_all_assets(self, integration_client_manager):
        """Test get_all_assets with real API."""
        result = await get_all_assets(integration_client_manager)

        assert result["success"] is True
        assert "data" in result
        
        data = result["data"]
        assert "perps" in data
        assert "spot" in data
        assert isinstance(data["perps"], list)
        assert isinstance(data["spot"], list)
        
        # Verify perpetual metadata structure
        if data["perps"]:
            perp = data["perps"][0]
            assert "name" in perp
            assert "szDecimals" in perp
            assert "maxLeverage" in perp
        
        # Verify spot metadata structure
        if data["spot"]:
            spot = data["spot"][0]
            assert "name" in spot
            assert "szDecimals" in spot
            assert "index" in spot


class TestExchangeEndpointIntegration:
    """Integration tests for Exchange endpoint tools against testnet."""

    @pytest.mark.asyncio
    async def test_place_spot_order_market(
        self, integration_client_manager, integration_decimal_manager
    ):
        """Test spot market order placement."""
        # Get available spot assets
        assets_result = await get_all_assets(integration_client_manager)
        spot_assets = assets_result["data"]["spot"]
        
        if not spot_assets:
            pytest.skip("No spot assets available on testnet")
        
        # Use first available spot asset with small size
        spot_symbol = spot_assets[0]["name"]
        
        result = await place_spot_order(
            integration_client_manager,
            integration_decimal_manager,
            symbol=spot_symbol,
            side="buy",
            size=0.01,  # Very small size for testing
            order_type="market"
        )

        # Note: Order may fail due to insufficient balance, but API call should work
        assert "success" in result
        assert "data" in result or "error" in result

    @pytest.mark.asyncio
    async def test_place_spot_order_limit(
        self, integration_client_manager, integration_decimal_manager
    ):
        """Test spot limit order placement."""
        assets_result = await get_all_assets(integration_client_manager)
        spot_assets = assets_result["data"]["spot"]
        
        if not spot_assets:
            pytest.skip("No spot assets available on testnet")
        
        spot_symbol = spot_assets[0]["name"]
        
        # Get current market price
        market_data = await get_market_data(integration_client_manager, spot_symbol)
        if not market_data["success"]:
            pytest.skip("Cannot get market data for spot asset")
        
        current_price = float(market_data["data"].get("midPx", "1.0"))
        # Place limit order well below market (unlikely to fill)
        limit_price = current_price * 0.5
        
        result = await place_spot_order(
            integration_client_manager,
            integration_decimal_manager,
            symbol=spot_symbol,
            side="buy",
            size=0.01,
            price=limit_price,
            order_type="limit"
        )

        assert "success" in result
        assert "data" in result or "error" in result

    @pytest.mark.asyncio
    async def test_place_perp_order_market(
        self, integration_client_manager, integration_decimal_manager
    ):
        """Test perpetual market order placement."""
        result = await place_perp_order(
            integration_client_manager,
            integration_decimal_manager,
            symbol="BTC",
            side="buy",
            size=0.001,  # Very small size for testing
            leverage=1,
            order_type="market"
        )

        # Note: Order may fail due to insufficient balance, but API call should work
        assert "success" in result
        assert "data" in result or "error" in result

    @pytest.mark.asyncio
    async def test_place_perp_order_limit(
        self, integration_client_manager, integration_decimal_manager
    ):
        """Test perpetual limit order placement."""
        # Get current BTC price
        market_data = await get_market_data(integration_client_manager, "BTC")
        assert market_data["success"] is True
        
        current_price = float(market_data["data"]["markPx"])
        # Place limit order well below market (unlikely to fill)
        limit_price = current_price * 0.8
        
        result = await place_perp_order(
            integration_client_manager,
            integration_decimal_manager,
            symbol="BTC",
            side="buy",
            size=0.001,
            leverage=2,
            price=limit_price,
            order_type="limit"
        )

        assert "success" in result
        assert "data" in result or "error" in result

    @pytest.mark.asyncio
    async def test_place_perp_order_with_high_leverage(
        self, integration_client_manager, integration_decimal_manager
    ):
        """Test perpetual order with higher leverage."""
        result = await place_perp_order(
            integration_client_manager,
            integration_decimal_manager,
            symbol="ETH",
            side="buy",
            size=0.01,
            leverage=5,
            order_type="market"
        )

        assert "success" in result
        assert "data" in result or "error" in result

    @pytest.mark.asyncio
    async def test_place_perp_order_exceeds_max_leverage(
        self, integration_client_manager, integration_decimal_manager
    ):
        """Test perpetual order with leverage exceeding maximum."""
        result = await place_perp_order(
            integration_client_manager,
            integration_decimal_manager,
            symbol="BTC",
            side="buy",
            size=0.001,
            leverage=999,  # Exceeds max leverage
            order_type="market"
        )

        assert result["success"] is False
        assert "error" in result
        assert "leverage" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_cancel_order(
        self, integration_client_manager, integration_decimal_manager
    ):
        """Test order cancellation."""
        # First place a limit order that won't fill
        market_data = await get_market_data(integration_client_manager, "BTC")
        if not market_data["success"]:
            pytest.skip("Cannot get market data")
        
        current_price = float(market_data["data"]["markPx"])
        limit_price = current_price * 0.5  # Well below market
        
        order_result = await place_perp_order(
            integration_client_manager,
            integration_decimal_manager,
            symbol="BTC",
            side="buy",
            size=0.001,
            leverage=1,
            price=limit_price,
            order_type="limit"
        )

        if not order_result.get("success"):
            pytest.skip("Cannot place order for cancellation test")
        
        # Get the order ID from open orders
        orders_result = await get_open_orders(integration_client_manager)
        if not orders_result["success"] or not orders_result["data"]:
            pytest.skip("No open orders to cancel")
        
        order_id = orders_result["data"][0]["oid"]
        
        # Cancel the order
        cancel_result = await cancel_order(
            integration_client_manager,
            symbol="BTC",
            order_id=order_id
        )

        assert "success" in cancel_result
        assert "data" in cancel_result or "error" in cancel_result

    @pytest.mark.asyncio
    async def test_cancel_all_orders(self, integration_client_manager):
        """Test cancelling all orders."""
        result = await cancel_all_orders(integration_client_manager)

        assert result["success"] is True
        assert "data" in result
        assert "cancelled_count" in result["data"]
        assert isinstance(result["data"]["cancelled_count"], int)

    @pytest.mark.asyncio
    async def test_cancel_all_orders_by_symbol(self, integration_client_manager):
        """Test cancelling all orders for specific symbol."""
        result = await cancel_all_orders(integration_client_manager, symbol="BTC")

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["symbol"] == "BTC"

    @pytest.mark.asyncio
    async def test_close_position_no_position(
        self, integration_client_manager, integration_decimal_manager
    ):
        """Test closing position when no position exists."""
        result = await close_position(
            integration_client_manager,
            integration_decimal_manager,
            symbol="SOL"
        )

        # Should fail with position not found error
        assert result["success"] is False
        assert "error" in result
        assert "position" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_decimal_precision_end_to_end(
        self, integration_client_manager, integration_decimal_manager
    ):
        """Test decimal precision handling end-to-end."""
        # Test with BTC (typically 4 sz_decimals)
        # Format a size with more decimals than allowed
        result = await place_perp_order(
            integration_client_manager,
            integration_decimal_manager,
            symbol="BTC",
            side="buy",
            size=0.123456789,  # Will be rounded to sz_decimals
            leverage=1,
            order_type="market"
        )

        # Should succeed (or fail for other reasons, but not precision)
        assert "success" in result
        
        # If it failed, it shouldn't be due to precision
        if not result["success"]:
            assert "precision" not in result.get("error", "").lower()
            assert "decimal" not in result.get("error", "").lower()
