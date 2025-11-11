"""Decimal precision manager for Hyperliquid assets."""

from cachetools import TTLCache

from hype_mcp.models import AssetMetadata


class DecimalPrecisionManager:
    """Handles decimal precision for spot and perpetual assets."""

    def __init__(self, info_client):
        """
        Initialize decimal precision manager.

        Args:
            info_client: Hyperliquid Info client for metadata queries
        """
        self.info_client = info_client
        # TTL cache with 1 hour expiration (3600 seconds)
        self._cache: TTLCache = TTLCache(maxsize=1000, ttl=3600)

    async def get_asset_metadata(self, symbol: str) -> AssetMetadata:
        """
        Fetch and cache asset metadata including szDecimals.

        Args:
            symbol: Asset symbol

        Returns:
            Asset metadata

        Raises:
            ValueError: If asset symbol is not found
        """
        # Check cache first
        if symbol in self._cache:
            return self._cache[symbol]

        # Fetch metadata from API
        metadata = await self._fetch_asset_metadata(symbol)
        
        # Cache the result
        self._cache[symbol] = metadata
        
        return metadata

    async def _fetch_asset_metadata(self, symbol: str) -> AssetMetadata:
        """
        Fetch asset metadata from Hyperliquid Info endpoint.

        Args:
            symbol: Asset symbol

        Returns:
            Asset metadata

        Raises:
            ValueError: If asset symbol is not found
        """
        # Fetch metadata for all assets
        meta_response = self.info_client.meta()
        
        # Detect asset type and extract metadata
        asset_type = self._detect_asset_type(symbol, meta_response)
        
        if asset_type == "spot":
            return self._extract_spot_metadata(symbol, meta_response)
        else:  # perp
            return self._extract_perp_metadata(symbol, meta_response)

    def _detect_asset_type(self, symbol: str, meta_response: dict) -> str:
        """
        Detect whether an asset is spot or perpetual.

        Args:
            symbol: Asset symbol
            meta_response: Response from meta() endpoint

        Returns:
            "spot" or "perp"

        Raises:
            ValueError: If asset symbol is not found
        """
        # Check spot assets
        spot_tokens = meta_response.get("tokens", [])
        for token in spot_tokens:
            if token.get("name") == symbol:
                return "spot"
        
        # Check perp assets
        universe = meta_response.get("universe", [])
        for asset in universe:
            if asset.get("name") == symbol:
                return "perp"
        
        raise ValueError(f"Asset '{symbol}' not found in Hyperliquid metadata")

    def _extract_spot_metadata(self, symbol: str, meta_response: dict) -> AssetMetadata:
        """
        Extract metadata for a spot asset.

        Args:
            symbol: Asset symbol
            meta_response: Response from meta() endpoint

        Returns:
            Asset metadata for spot asset

        Raises:
            ValueError: If asset not found
        """
        spot_tokens = meta_response.get("tokens", [])
        for token in spot_tokens:
            if token.get("name") == symbol:
                return AssetMetadata(
                    symbol=symbol,
                    asset_type="spot",
                    sz_decimals=token.get("szDecimals", 0),
                    max_decimals=8,  # Spot assets have MAX_DECIMALS = 8
                    max_leverage=None,  # Spot assets don't have leverage
                )
        
        raise ValueError(f"Spot asset '{symbol}' not found in metadata")

    def _extract_perp_metadata(self, symbol: str, meta_response: dict) -> AssetMetadata:
        """
        Extract metadata for a perpetual asset.

        Args:
            symbol: Asset symbol
            meta_response: Response from meta() endpoint

        Returns:
            Asset metadata for perpetual asset

        Raises:
            ValueError: If asset not found
        """
        universe = meta_response.get("universe", [])
        for asset in universe:
            if asset.get("name") == symbol:
                return AssetMetadata(
                    symbol=symbol,
                    asset_type="perp",
                    sz_decimals=asset.get("szDecimals", 0),
                    max_decimals=6,  # Perp assets have MAX_DECIMALS = 6
                    max_leverage=asset.get("maxLeverage"),
                )
        
        raise ValueError(f"Perpetual asset '{symbol}' not found in metadata")

    async def format_size_for_api(self, symbol: str, size: float) -> str:
        """
        Convert human-readable size to API format.

        Args:
            symbol: Asset symbol
            size: Size in human-readable format

        Returns:
            Formatted size string

        Raises:
            ValueError: If size has too many decimal places
        """
        from decimal import Decimal, ROUND_DOWN
        
        # Get asset metadata
        metadata = await self.get_asset_metadata(symbol)
        sz_decimals = metadata.sz_decimals
        
        # Use Decimal for precise rounding
        size_decimal = Decimal(str(size))
        quantizer = Decimal(10) ** -sz_decimals
        rounded = size_decimal.quantize(quantizer, rounding=ROUND_DOWN)
        
        # Convert to string and remove trailing zeros
        formatted = str(rounded)
        if '.' in formatted:
            formatted = formatted.rstrip('0').rstrip('.')
        
        return formatted

    async def format_price_for_api(self, symbol: str, price: float) -> str:
        """
        Convert human-readable price to API format.

        Args:
            symbol: Asset symbol
            price: Price in human-readable format

        Returns:
            Formatted price string

        Raises:
            ValueError: If price has too many significant figures or decimal places
        """
        from decimal import Decimal, ROUND_DOWN
        import re
        
        # Get asset metadata
        metadata = await self.get_asset_metadata(symbol)
        max_price_decimals = metadata.max_decimals - metadata.sz_decimals
        
        # Use Decimal for precise rounding
        price_decimal = Decimal(str(price))
        
        # Check if integer (integers always allowed regardless of sig figs)
        if price_decimal == price_decimal.to_integral_value():
            return str(int(price_decimal))
        
        # Round to max allowed decimal places
        quantizer = Decimal(10) ** -max_price_decimals
        rounded = price_decimal.quantize(quantizer, rounding=ROUND_DOWN)
        
        # Remove trailing zeros
        formatted = str(rounded).rstrip('0').rstrip('.')
        
        # Validate significant figures (max 5)
        sig_figs = len(re.sub(r'[^0-9]', '', formatted.lstrip('0').lstrip('.')))
        
        if sig_figs > 5:
            raise ValueError(
                f"Price {price} has {sig_figs} significant figures, maximum is 5"
            )
        
        return formatted
