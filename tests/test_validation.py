"""Tests for input validation and error handling."""

import pytest
from pydantic import ValidationError

from hype_mcp.validation import (
    SpotOrderParams,
    PerpOrderParams,
    CancelOrderParams,
    ClosePositionParams,
    MarketDataParams,
    WalletAddressParams,
)
from hype_mcp.errors import (
    HyperliquidMCPError,
    ValidationError as CustomValidationError,
    APIError,
    PrecisionError,
    AssetNotFoundError,
    LeverageExceededError,
    PositionNotFoundError,
    OrderNotFoundError,
    format_error_response,
)


class TestSpotOrderParams:
    """Tests for SpotOrderParams validation."""

    def test_valid_spot_order(self):
        """Test valid spot order parameters."""
        params = SpotOrderParams(
            symbol="PURR",
            side="buy",
            size=100.5,
            price=0.05,
            order_type="limit"
        )
        assert params.symbol == "PURR"
        assert params.side == "buy"
        assert params.size == 100.5
        assert params.price == 0.05
        assert params.order_type == "limit"

    def test_case_insensitive_side(self):
        """Test that side is case-insensitive."""
        # Lowercase works
        params = SpotOrderParams(
            symbol="PURR",
            side="buy",
            size=100
        )
        assert params.side == "buy"
        
        # Uppercase also works and gets normalized
        params = SpotOrderParams(
            symbol="PURR",
            side="BUY",
            size=100
        )
        assert params.side == "buy"

    def test_invalid_side(self):
        """Test that invalid side raises error."""
        with pytest.raises(ValidationError):
            SpotOrderParams(
                symbol="PURR",
                side="invalid",
                size=100
            )

    def test_negative_size(self):
        """Test that negative size raises error."""
        with pytest.raises(ValidationError):
            SpotOrderParams(
                symbol="PURR",
                side="buy",
                size=-100
            )

    def test_limit_order_without_price(self):
        """Test that limit order without price raises error."""
        with pytest.raises(ValidationError):
            SpotOrderParams(
                symbol="PURR",
                side="buy",
                size=100,
                order_type="limit"
            )

    def test_market_order_without_price(self):
        """Test that market order without price is valid."""
        params = SpotOrderParams(
            symbol="PURR",
            side="buy",
            size=100,
            order_type="market"
        )
        assert params.price is None


class TestPerpOrderParams:
    """Tests for PerpOrderParams validation."""

    def test_valid_perp_order(self):
        """Test valid perpetual order parameters."""
        params = PerpOrderParams(
            symbol="BTC",
            side="buy",
            size=0.5,
            leverage=5,
            price=50000.0,
            order_type="limit"
        )
        assert params.symbol == "BTC"
        assert params.side == "buy"
        assert params.size == 0.5
        assert params.leverage == 5
        assert params.price == 50000.0
        assert params.order_type == "limit"

    def test_leverage_too_low(self):
        """Test that leverage < 1 raises error."""
        with pytest.raises(ValidationError):
            PerpOrderParams(
                symbol="BTC",
                side="buy",
                size=0.5,
                leverage=0
            )

    def test_leverage_too_high(self):
        """Test that leverage > 100 raises error."""
        with pytest.raises(ValidationError):
            PerpOrderParams(
                symbol="BTC",
                side="buy",
                size=0.5,
                leverage=101
            )

    def test_reduce_only_flag(self):
        """Test reduce_only flag."""
        params = PerpOrderParams(
            symbol="BTC",
            side="sell",
            size=0.5,
            leverage=1,
            reduce_only=True
        )
        assert params.reduce_only is True


class TestCancelOrderParams:
    """Tests for CancelOrderParams validation."""

    def test_valid_cancel_params(self):
        """Test valid cancel order parameters."""
        params = CancelOrderParams(
            symbol="BTC",
            order_id=123456
        )
        assert params.symbol == "BTC"
        assert params.order_id == 123456

    def test_negative_order_id(self):
        """Test that negative order_id raises error."""
        with pytest.raises(ValidationError):
            CancelOrderParams(
                symbol="BTC",
                order_id=-1
            )


class TestClosePositionParams:
    """Tests for ClosePositionParams validation."""

    def test_valid_close_full_position(self):
        """Test valid close position without size."""
        params = ClosePositionParams(symbol="BTC")
        assert params.symbol == "BTC"
        assert params.size is None

    def test_valid_close_partial_position(self):
        """Test valid close position with size."""
        params = ClosePositionParams(
            symbol="BTC",
            size=0.5
        )
        assert params.symbol == "BTC"
        assert params.size == 0.5

    def test_negative_size(self):
        """Test that negative size raises error."""
        with pytest.raises(ValidationError):
            ClosePositionParams(
                symbol="BTC",
                size=-0.5
            )


class TestMarketDataParams:
    """Tests for MarketDataParams validation."""

    def test_valid_symbol(self):
        """Test valid symbol."""
        params = MarketDataParams(symbol="BTC")
        assert params.symbol == "BTC"

    def test_empty_symbol(self):
        """Test that empty symbol raises error."""
        with pytest.raises(ValidationError):
            MarketDataParams(symbol="")


class TestWalletAddressParams:
    """Tests for WalletAddressParams validation."""

    def test_valid_address(self):
        """Test valid wallet address."""
        params = WalletAddressParams(
            user_address="0x1234567890123456789012345678901234567890"
        )
        assert params.user_address == "0x1234567890123456789012345678901234567890"

    def test_none_address(self):
        """Test that None address is valid."""
        params = WalletAddressParams(user_address=None)
        assert params.user_address is None

    def test_invalid_address_no_prefix(self):
        """Test that address without 0x raises error."""
        with pytest.raises(ValidationError):
            WalletAddressParams(
                user_address="1234567890123456789012345678901234567890"
            )

    def test_invalid_address_length(self):
        """Test that address with wrong length raises error."""
        with pytest.raises(ValidationError):
            WalletAddressParams(user_address="0x123")


class TestCustomErrors:
    """Tests for custom error classes."""

    def test_validation_error(self):
        """Test ValidationError."""
        error = CustomValidationError(
            message="Invalid value",
            field="size",
            value=100,
            constraint="must be positive"
        )
        result = error.to_dict()
        assert result["success"] is False
        assert result["error"] == "Invalid value"
        assert result["error_type"] == "ValidationError"
        assert result["details"]["field"] == "size"
        assert result["details"]["value"] == 100

    def test_api_error(self):
        """Test APIError."""
        error = APIError(
            message="API request failed",
            api_response={"status": "error"},
            status_code=500
        )
        result = error.to_dict()
        assert result["success"] is False
        assert result["error"] == "API request failed"
        assert result["error_type"] == "APIError"
        assert result["details"]["status_code"] == 500

    def test_precision_error(self):
        """Test PrecisionError."""
        error = PrecisionError(
            message="Too many decimals",
            symbol="BTC",
            value=0.123456,
            constraint="max 5 decimals"
        )
        result = error.to_dict()
        assert result["success"] is False
        assert result["error_type"] == "PrecisionError"
        assert result["details"]["symbol"] == "BTC"

    def test_asset_not_found_error(self):
        """Test AssetNotFoundError."""
        error = AssetNotFoundError(symbol="INVALID")
        result = error.to_dict()
        assert result["success"] is False
        assert result["error_type"] == "AssetNotFoundError"
        assert "INVALID" in result["error"]

    def test_leverage_exceeded_error(self):
        """Test LeverageExceededError."""
        error = LeverageExceededError(
            symbol="BTC",
            requested_leverage=50,
            max_leverage=25
        )
        result = error.to_dict()
        assert result["success"] is False
        assert result["error_type"] == "LeverageExceededError"
        assert result["details"]["requested_leverage"] == 50
        assert result["details"]["max_leverage"] == 25

    def test_position_not_found_error(self):
        """Test PositionNotFoundError."""
        error = PositionNotFoundError(symbol="ETH")
        result = error.to_dict()
        assert result["success"] is False
        assert result["error_type"] == "PositionNotFoundError"
        assert "ETH" in result["error"]

    def test_order_not_found_error(self):
        """Test OrderNotFoundError."""
        error = OrderNotFoundError(symbol="BTC", order_id=12345)
        result = error.to_dict()
        assert result["success"] is False
        assert result["error_type"] == "OrderNotFoundError"
        assert "12345" in result["error"]


class TestFormatErrorResponse:
    """Tests for format_error_response function."""

    def test_format_custom_error(self):
        """Test formatting custom error."""
        error = CustomValidationError(
            message="Test error",
            field="test",
            value="invalid"
        )
        result = format_error_response(error)
        assert result["success"] is False
        assert result["error"] == "Test error"
        assert result["error_type"] == "ValidationError"

    def test_format_pydantic_error(self):
        """Test formatting Pydantic validation error."""
        try:
            SpotOrderParams(
                symbol="BTC",
                side="invalid",
                size=100
            )
        except ValidationError as e:
            result = format_error_response(e)
            assert result["success"] is False
            assert result["error_type"] == "ValidationError"
            assert "side" in result["error"]

    def test_format_generic_exception(self):
        """Test formatting generic exception."""
        error = ValueError("Generic error")
        result = format_error_response(error)
        assert result["success"] is False
        assert result["error"] == "Generic error"
        assert result["error_type"] == "ValueError"
