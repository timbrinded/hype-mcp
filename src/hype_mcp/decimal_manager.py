"""Decimal precision helpers."""

import asyncio
import re
from decimal import Decimal, ROUND_DOWN

from cachetools import TTLCache

from hype_mcp.models import AssetMetadata


class DecimalPrecisionManager:
    CACHE_TTL = 3600

    def __init__(self, info_client) -> None:
        self.info_client = info_client
        self._cache: TTLCache[str, AssetMetadata] = TTLCache(
            maxsize=1000, ttl=self.CACHE_TTL
        )

    async def get_asset_metadata(self, symbol: str) -> AssetMetadata:
        cached = self._cache.get(symbol)
        if cached:
            return cached
        loop = asyncio.get_running_loop()
        meta = await loop.run_in_executor(None, self.info_client.meta)
        metadata = self._extract_metadata(symbol, meta)
        self._cache[symbol] = metadata
        return metadata

    def _extract_metadata(self, symbol: str, meta: dict) -> AssetMetadata:
        asset_type = self._detect_asset_type(symbol, meta)
        if asset_type == "spot":
            return self._extract_spot_metadata(symbol, meta)
        return self._extract_perp_metadata(symbol, meta)

    def _detect_asset_type(self, symbol: str, meta_response: dict) -> str:
        for token in meta_response.get("tokens", []):
            if token.get("name") == symbol:
                return "spot"
        for asset in meta_response.get("universe", []):
            if asset.get("name") == symbol:
                return "perp"
        raise ValueError(f"Asset '{symbol}' not found in Hyperliquid metadata")

    def _extract_spot_metadata(self, symbol: str, meta_response: dict) -> AssetMetadata:
        for token in meta_response.get("tokens", []):
            if token.get("name") == symbol:
                return AssetMetadata(
                    symbol=symbol,
                    asset_type="spot",
                    sz_decimals=token.get("szDecimals", 0),
                    max_decimals=8,
                    max_leverage=None,
                )
        raise ValueError(f"Spot asset '{symbol}' not found in metadata")

    def _extract_perp_metadata(self, symbol: str, meta_response: dict) -> AssetMetadata:
        for asset in meta_response.get("universe", []):
            if asset.get("name") == symbol:
                return AssetMetadata(
                    symbol=symbol,
                    asset_type="perp",
                    sz_decimals=asset.get("szDecimals", 0),
                    max_decimals=6,
                    max_leverage=asset.get("maxLeverage"),
                )
        raise ValueError(f"Perpetual asset '{symbol}' not found in metadata")

    async def format_size_for_api(self, symbol: str, size: float) -> str:
        metadata = await self.get_asset_metadata(symbol)
        quantizer = Decimal(10) ** -metadata.sz_decimals
        rounded = Decimal(str(size)).quantize(quantizer, rounding=ROUND_DOWN)
        text = str(rounded)
        return text.rstrip("0").rstrip(".") if "." in text else text

    async def format_price_for_api(self, symbol: str, price: float) -> str:
        metadata = await self.get_asset_metadata(symbol)
        max_price_decimals = metadata.max_decimals - metadata.sz_decimals
        price_decimal = Decimal(str(price))
        if price_decimal == price_decimal.to_integral_value():
            return str(int(price_decimal))
        quantizer = Decimal(10) ** -max_price_decimals
        rounded = price_decimal.quantize(quantizer, rounding=ROUND_DOWN)
        formatted = str(rounded).rstrip("0").rstrip(".")
        sig_figs = len(re.sub(r"[^0-9]", "", formatted.lstrip("0").lstrip(".")))
        if sig_figs > 5:
            raise ValueError(
                f"Price {price} has {sig_figs} significant figures, maximum is 5"
            )
        return formatted
