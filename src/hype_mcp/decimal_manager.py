"""Decimal precision manager for Hyperliquid assets."""


class DecimalPrecisionManager:
    """Handles decimal precision for spot and perpetual assets."""

    def __init__(self, info_client):
        """
        Initialize decimal precision manager.

        Args:
            info_client: Hyperliquid Info client for metadata queries
        """
        self.info_client = info_client
        # TODO: Initialize caching mechanism

    async def get_asset_metadata(self, symbol: str):
        """
        Fetch and cache asset metadata including szDecimals.

        Args:
            symbol: Asset symbol

        Returns:
            Asset metadata
        """
        # TODO: Implement metadata fetching and caching
        pass

    async def format_size_for_api(self, symbol: str, size: float) -> str:
        """
        Convert human-readable size to API format.

        Args:
            symbol: Asset symbol
            size: Size in human-readable format

        Returns:
            Formatted size string
        """
        # TODO: Implement size formatting
        pass

    async def format_price_for_api(self, symbol: str, price: float) -> str:
        """
        Convert human-readable price to API format.

        Args:
            symbol: Asset symbol
            price: Price in human-readable format

        Returns:
            Formatted price string
        """
        # TODO: Implement price formatting
        pass
