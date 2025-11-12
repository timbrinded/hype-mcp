"""Tests for exchange endpoint helpers."""

import pytest
from unittest.mock import AsyncMock

from hype_mcp.models import AssetMetadata
from hype_mcp.tools.exchange_tools import place_spot_order, transfer_wallet_funds


class TestPlaceSpotOrder:
    """Spot order placement unit tests."""

    @pytest.mark.asyncio
    async def test_market_order_uses_spot_index(
        self, mock_client_manager, mock_decimal_manager, mock_asset_router
    ):
        """Ensure market spot orders use the market index identifier."""
        metadata = AssetMetadata(
            symbol="PURR",
            asset_type="spot",
            sz_decimals=2,
            max_decimals=8,
            max_leverage=None,
            spot_index=12,
        )
        mock_decimal_manager.get_asset_metadata = AsyncMock(return_value=metadata)
        mock_decimal_manager.format_size_for_api = AsyncMock(return_value="1")
        mock_client_manager.exchange.market_open.reset_mock()

        result = await place_spot_order(
            mock_client_manager,
            mock_decimal_manager,
            mock_asset_router,
            symbol="PURR",
            side="buy",
            size=1,
            order_type="market",
        )

        assert result["success"] is True
        mock_client_manager.exchange.market_open.assert_called_once()
        expected_symbol = mock_asset_router.resolve_spot_symbol("PURR").api_symbol
        assert (
            mock_client_manager.exchange.market_open.call_args.kwargs["name"]
            == expected_symbol
        )

    @pytest.mark.asyncio
    async def test_limit_order_uses_spot_index(
        self, mock_client_manager, mock_decimal_manager, mock_asset_router
    ):
        """Ensure limit spot orders use the market index identifier."""
        metadata = AssetMetadata(
            symbol="PURR",
            asset_type="spot",
            sz_decimals=2,
            max_decimals=8,
            max_leverage=None,
            spot_index=34,
        )
        mock_decimal_manager.get_asset_metadata = AsyncMock(return_value=metadata)
        mock_decimal_manager.format_size_for_api = AsyncMock(return_value="1")
        mock_decimal_manager.format_price_for_api = AsyncMock(return_value="0.1")
        mock_client_manager.exchange.order.reset_mock()

        result = await place_spot_order(
            mock_client_manager,
            mock_decimal_manager,
            mock_asset_router,
            symbol="PURR",
            side="buy",
            size=1,
            price=0.1,
            order_type="limit",
        )

        assert result["success"] is True
        mock_client_manager.exchange.order.assert_called_once()
        expected_symbol = mock_asset_router.resolve_spot_symbol("PURR").api_symbol
        assert (
            mock_client_manager.exchange.order.call_args.kwargs["name"]
            == expected_symbol
        )

    @pytest.mark.asyncio
    async def test_invalid_metadata_type_rejected(
        self, mock_client_manager, mock_decimal_manager, mock_asset_router
    ):
        """Ensure metadata mismatches are surfaced."""
        metadata = AssetMetadata(
            symbol="PURR",
            asset_type="perp",
            sz_decimals=4,
            max_decimals=6,
            max_leverage=10,
            spot_index=None,
        )
        mock_decimal_manager.get_asset_metadata = AsyncMock(return_value=metadata)
        mock_decimal_manager.format_size_for_api = AsyncMock(return_value="1")

        result = await place_spot_order(
            mock_client_manager,
            mock_decimal_manager,
            mock_asset_router,
            symbol="PURR",
            side="buy",
            size=1,
            order_type="market",
        )

        assert result["success"] is False
        assert "spot asset" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_rejects_non_spot_assets(
        self, mock_client_manager, mock_decimal_manager, mock_asset_router
    ):
        """Unknown symbols should raise a validation error."""
        metadata = AssetMetadata(
            symbol="BTC",
            asset_type="perp",
            sz_decimals=4,
            max_decimals=6,
            max_leverage=50,
        )
        mock_decimal_manager.get_asset_metadata = AsyncMock(return_value=metadata)
        mock_decimal_manager.format_size_for_api = AsyncMock(return_value="0.1")

        result = await place_spot_order(
            mock_client_manager,
            mock_decimal_manager,
            mock_asset_router,
            symbol="UNKNOWN",
            side="buy",
            size=0.1,
            order_type="market",
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestTransferWalletFunds:
    """Wallet transfer helper tests."""

    @pytest.mark.asyncio
    async def test_perp_to_spot_transfer(self, mock_client_manager):
        result = await transfer_wallet_funds(
            mock_client_manager,
            amount=1.5,
            direction="perp_to_spot",
        )

        assert result["success"] is True
        mock_client_manager.exchange.usd_class_transfer.assert_called_once_with(
            1.5, False
        )

    @pytest.mark.asyncio
    async def test_spot_to_perp_transfer(self, mock_client_manager):
        mock_client_manager.exchange.usd_class_transfer.reset_mock()

        result = await transfer_wallet_funds(
            mock_client_manager,
            amount=2.25,
            direction="spot_to_perp",
        )

        assert result["success"] is True
        mock_client_manager.exchange.usd_class_transfer.assert_called_once_with(
            2.25, True
        )

    @pytest.mark.asyncio
    async def test_invalid_account_address(self, mock_client_manager):
        mock_client_manager.exchange.account_address = "0xabc"
        mock_client_manager.exchange.wallet.address = "0xdef"

        result = await transfer_wallet_funds(
            mock_client_manager,
            amount=5,
            direction="perp_to_spot",
        )

        assert result["success"] is False
        assert result["error_type"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_api_error_surface(self, mock_client_manager):
        mock_client_manager.exchange.usd_class_transfer.return_value = {
            "status": "error",
            "response": {"message": "failure"},
        }

        result = await transfer_wallet_funds(
            mock_client_manager,
            amount=1,
            direction="spot_to_perp",
        )

        assert result["success"] is False
        assert result["error_type"] == "APIError"
