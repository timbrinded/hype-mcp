"""Exchange endpoint MCP tools for trade execution."""

from typing import Any, Literal, Optional

from ..client_manager import HyperliquidClientManager
from ..decimal_manager import DecimalPrecisionManager


async def place_spot_order(
    client_manager: HyperliquidClientManager,
    decimal_manager: DecimalPrecisionManager,
    symbol: str,
    side: Literal["buy", "sell"],
    size: float,
    price: Optional[float] = None,
    order_type: Literal["market", "limit"] = "market",
) -> dict[str, Any]:
    """
    Place a spot market order. Decimal precision is handled automatically.

    This tool places a spot order on Hyperliquid, automatically handling all decimal
    precision requirements. You can place either market orders (immediate execution)
    or limit orders (execute at specific price).

    Args:
        client_manager: Hyperliquid client manager instance
        decimal_manager: Decimal precision manager for formatting
        symbol: Spot asset symbol (e.g., "PURR", "HYPE"). Must be a valid spot
               asset available on Hyperliquid.
        side: Order side - "buy" to purchase the asset, "sell" to sell the asset
        size: Quantity to trade in human-readable format (e.g., 100.5, 1000).
             Will be automatically formatted to match asset's decimal precision.
        price: Limit price for the order. Required for limit orders, ignored for
              market orders. Will be automatically formatted to match precision rules.
        order_type: Type of order - "market" for immediate execution at current
                   market price, "limit" to execute only at specified price or better.
                   Defaults to "market".

    Returns:
        Dictionary containing:
        - success: Boolean indicating if the order was placed successfully
        - data: Order result including:
            - status: "ok" if successful, or error details
            - response: Order confirmation with:
                - statuses: List of order statuses
                - data: Additional order data including fills
        - error: Error message if the order failed
        - error_type: Type of error that occurred

    Raises:
        ValueError: If parameters are invalid (e.g., limit order without price)
        Exception: If the API request fails or order is rejected

    Example:
        >>> # Place market buy order
        >>> result = await place_spot_order(
        ...     client_manager, decimal_manager,
        ...     symbol="PURR", side="buy", size=1000, order_type="market"
        ... )
        >>> print(f"Order status: {result['data']['status']}")

        >>> # Place limit sell order
        >>> result = await place_spot_order(
        ...     client_manager, decimal_manager,
        ...     symbol="PURR", side="sell", size=500, price=0.05, order_type="limit"
        ... )
    """
    try:
        # Validate parameters
        if order_type == "limit" and price is None:
            return {
                "success": False,
                "error": "Price is required for limit orders",
                "error_type": "ValueError",
            }

        # Format size with proper decimal precision
        formatted_size = await decimal_manager.format_size_for_api(symbol, size)

        # Format price if provided
        formatted_price = None
        if price is not None:
            formatted_price = await decimal_manager.format_price_for_api(symbol, price)

        # Convert side to Hyperliquid format ("B" for buy, "A" for sell/ask)
        is_buy = side.lower() == "buy"

        # Prepare order parameters
        order_params = {
            "coin": symbol,
            "is_buy": is_buy,
            "sz": float(formatted_size),
            "limit_px": float(formatted_price) if formatted_price else None,
            "order_type": {"limit": {"tif": "Gtc"}} if order_type == "limit" else {"market": {}},
            "reduce_only": False,
        }

        # Submit order via Exchange client
        result = client_manager.exchange.order(order_params, spot=True)

        return {
            "success": True,
            "data": {
                "status": result.get("status", "unknown"),
                "response": result.get("response", {}),
            },
        }

    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": "ValueError",
            "details": {
                "symbol": symbol,
                "side": side,
                "size": size,
                "price": price,
                "order_type": order_type,
            },
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to place spot order: {str(e)}",
            "error_type": type(e).__name__,
            "details": {
                "symbol": symbol,
                "side": side,
                "size": size,
                "price": price,
                "order_type": order_type,
            },
        }


# TODO: Implement remaining Exchange endpoint tools:
# - place_perp_order
# - cancel_order
# - cancel_all_orders
# - close_position
