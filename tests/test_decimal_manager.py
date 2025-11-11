"""Tests for decimal precision manager."""

import pytest
from unittest.mock import Mock
from decimal import Decimal

from hype_mcp.decimal_manager import DecimalPrecisionManager
from hype_mcp.models import AssetMetadata


class TestDecimalPrecisionManager:
    """Tests for DecimalPrecisionManager class."""

    @pytest.fixture
    def mock_info_client(self):
        """Create a mock Info client."""
        mock = Mock()
        mock.meta = Mock(return_value={
            "universe": [
                {"name": "BTC", "szDecimals": 4, "maxLeverage": 50},
                {"name": "ETH", "szDecimals": 3, "maxLeverage": 50},
                {"name": "SOL", "szDecimals": 2, "maxLeverage": 20},
            ],
            "tokens": [
                {"name": "PURR", "szDecimals": 2, "index": 0},
                {"name": "HYPE", "szDecimals": 1, "index": 1},
            ]
        })
        return mock

    @pytest.fixture
    def manager(self, mock_info_client):
        """Create a DecimalPrecisionManager instance."""
        return DecimalPrecisionManager(mock_info_client)

    @pytest.mark.asyncio
    async def test_get_asset_metadata_perp(self, manager):
        """Test fetching metadata for a perpetual asset."""
        metadata = await manager.get_asset_metadata("BTC")
        
        assert metadata.symbol == "BTC"
        assert metadata.asset_type == "perp"
        assert metadata.sz_decimals == 4
        assert metadata.max_decimals == 6
        assert metadata.max_leverage == 50

    @pytest.mark.asyncio
    async def test_get_asset_metadata_spot(self, manager):
        """Test fetching metadata for a spot asset."""
        metadata = await manager.get_asset_metadata("PURR")
        
        assert metadata.symbol == "PURR"
        assert metadata.asset_type == "spot"
        assert metadata.sz_decimals == 2
        assert metadata.max_decimals == 8
        assert metadata.max_leverage is None

    @pytest.mark.asyncio
    async def test_get_asset_metadata_caching(self, manager, mock_info_client):
        """Test that asset metadata is cached."""
        # First call should fetch from API
        await manager.get_asset_metadata("BTC")
        assert mock_info_client.meta.call_count == 1
        
        # Second call should use cache
        await manager.get_asset_metadata("BTC")
        assert mock_info_client.meta.call_count == 1  # Still 1, not 2

    @pytest.mark.asyncio
    async def test_get_asset_metadata_not_found(self, manager):
        """Test that unknown asset raises ValueError."""
        with pytest.raises(ValueError, match="Asset 'INVALID' not found"):
            await manager.get_asset_metadata("INVALID")

    @pytest.mark.asyncio
    async def test_format_size_for_api_basic(self, manager):
        """Test basic size formatting."""
        # BTC has szDecimals=4
        result = await manager.format_size_for_api("BTC", 0.12345)
        assert result == "0.1234"

    @pytest.mark.asyncio
    async def test_format_size_for_api_removes_trailing_zeros(self, manager):
        """Test that trailing zeros are removed."""
        # BTC has szDecimals=4
        result = await manager.format_size_for_api("BTC", 1.1000)
        assert result == "1.1"
        
        result = await manager.format_size_for_api("BTC", 1.0)
        assert result == "1"

    @pytest.mark.asyncio
    async def test_format_size_for_api_various_decimals(self, manager):
        """Test size formatting with various szDecimals values."""
        # ETH has szDecimals=3
        result = await manager.format_size_for_api("ETH", 0.12345)
        assert result == "0.123"
        
        # SOL has szDecimals=2
        result = await manager.format_size_for_api("SOL", 10.999)
        assert result == "10.99"
        
        # HYPE has szDecimals=1
        result = await manager.format_size_for_api("HYPE", 100.567)
        assert result == "100.5"

    @pytest.mark.asyncio
    async def test_format_size_for_api_very_small_numbers(self, manager):
        """Test size formatting with very small numbers."""
        # BTC has szDecimals=4
        result = await manager.format_size_for_api("BTC", 0.00001)
        assert result == "0"
        
        result = await manager.format_size_for_api("BTC", 0.00009)
        assert result == "0"

    @pytest.mark.asyncio
    async def test_format_size_for_api_very_large_numbers(self, manager):
        """Test size formatting with very large numbers."""
        # BTC has szDecimals=4
        result = await manager.format_size_for_api("BTC", 123456.789012)
        assert result == "123456.789"

    @pytest.mark.asyncio
    async def test_format_size_for_api_integers(self, manager):
        """Test size formatting with integer values."""
        # BTC has szDecimals=4
        result = await manager.format_size_for_api("BTC", 100)
        assert result == "100"

    @pytest.mark.asyncio
    async def test_format_price_for_api_basic(self, manager):
        """Test basic price formatting."""
        # BTC perp: max_decimals=6, sz_decimals=4, so max_price_decimals=2
        # Use a price with 5 or fewer significant figures
        result = await manager.format_price_for_api("BTC", 1234.5)
        assert result == "1234.5"

    @pytest.mark.asyncio
    async def test_format_price_for_api_integer(self, manager):
        """Test that integer prices are always allowed."""
        # BTC perp: max_decimals=6, sz_decimals=4
        result = await manager.format_price_for_api("BTC", 123456)
        assert result == "123456"

    @pytest.mark.asyncio
    async def test_format_price_for_api_significant_figures_validation(self, manager):
        """Test that prices with >5 significant figures raise error."""
        # BTC perp: max_decimals=6, sz_decimals=4
        # 123456.7 has 7 significant figures
        with pytest.raises(ValueError, match="has 7 significant figures, maximum is 5"):
            await manager.format_price_for_api("BTC", 123456.7)

    @pytest.mark.asyncio
    async def test_format_price_for_api_five_sig_figs_allowed(self, manager):
        """Test that prices with exactly 5 significant figures are allowed."""
        # BTC perp: max_decimals=6, sz_decimals=4, max_price_decimals=2
        result = await manager.format_price_for_api("BTC", 12345.0)
        assert result == "12345"

    @pytest.mark.asyncio
    async def test_format_price_for_api_removes_trailing_zeros(self, manager):
        """Test that trailing zeros are removed."""
        # BTC perp: max_decimals=6, sz_decimals=4
        result = await manager.format_price_for_api("BTC", 1234.10)
        assert result == "1234.1"

    @pytest.mark.asyncio
    async def test_format_price_for_api_spot_vs_perp(self, manager):
        """Test different max_decimals for spot vs perp."""
        # PURR spot: max_decimals=8, sz_decimals=2, max_price_decimals=6
        # Use price with exactly 5 sig figs: 0.01234 (1,2,3,4 are the sig figs after leading zeros)
        result = await manager.format_price_for_api("PURR", 0.01234)
        assert result == "0.01234"
        
        # BTC perp: max_decimals=6, sz_decimals=4, max_price_decimals=2
        result = await manager.format_price_for_api("BTC", 123.45)
        assert result == "123.45"

    @pytest.mark.asyncio
    async def test_format_price_for_api_edge_cases(self, manager):
        """Test edge cases for price formatting."""
        # Very small price with spot asset (2 sig figs: 1,2)
        result = await manager.format_price_for_api("PURR", 0.00012)
        assert result == "0.00012"
        
        # Price that rounds to zero
        result = await manager.format_price_for_api("PURR", 0.0000001)
        assert result == "0"

    @pytest.mark.asyncio
    async def test_detect_asset_type_perp(self, manager, mock_info_client):
        """Test detecting perpetual asset type."""
        meta_response = mock_info_client.meta()
        asset_type = manager._detect_asset_type("BTC", meta_response)
        assert asset_type == "perp"

    @pytest.mark.asyncio
    async def test_detect_asset_type_spot(self, manager, mock_info_client):
        """Test detecting spot asset type."""
        meta_response = mock_info_client.meta()
        asset_type = manager._detect_asset_type("PURR", meta_response)
        assert asset_type == "spot"

    @pytest.mark.asyncio
    async def test_detect_asset_type_not_found(self, manager, mock_info_client):
        """Test that unknown asset raises ValueError."""
        meta_response = mock_info_client.meta()
        with pytest.raises(ValueError, match="Asset 'INVALID' not found"):
            manager._detect_asset_type("INVALID", meta_response)

    @pytest.mark.asyncio
    async def test_extract_spot_metadata(self, manager, mock_info_client):
        """Test extracting spot asset metadata."""
        meta_response = mock_info_client.meta()
        metadata = manager._extract_spot_metadata("PURR", meta_response)
        
        assert metadata.symbol == "PURR"
        assert metadata.asset_type == "spot"
        assert metadata.sz_decimals == 2
        assert metadata.max_decimals == 8
        assert metadata.max_leverage is None

    @pytest.mark.asyncio
    async def test_extract_perp_metadata(self, manager, mock_info_client):
        """Test extracting perpetual asset metadata."""
        meta_response = mock_info_client.meta()
        metadata = manager._extract_perp_metadata("BTC", meta_response)
        
        assert metadata.symbol == "BTC"
        assert metadata.asset_type == "perp"
        assert metadata.sz_decimals == 4
        assert metadata.max_decimals == 6
        assert metadata.max_leverage == 50
