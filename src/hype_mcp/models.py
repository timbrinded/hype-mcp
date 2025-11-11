"""Data models for the MCP server."""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class AssetMetadata:
    """Metadata for a trading asset."""

    symbol: str
    asset_type: Literal["spot", "perp"]
    sz_decimals: int
    max_decimals: int  # 8 for spot, 6 for perp
    max_leverage: Optional[int] = None  # Only for perps


@dataclass
class OrderRequest:
    """Internal representation of an order."""

    symbol: str
    side: Literal["buy", "sell"]
    size: str  # Formatted for API
    price: Optional[str]  # Formatted for API
    order_type: Literal["market", "limit"]
    is_spot: bool
    leverage: Optional[int] = None  # Only for perps
    reduce_only: bool = False


@dataclass
class ToolResponse:
    """Standardized response format for all tools."""

    success: bool
    data: Optional[dict | list] = None
    error: Optional[str] = None
