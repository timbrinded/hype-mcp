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


async def place_perp_order(
    client_manager: HyperliquidClientManager,
    decimal_manager: DecimalPrecisionManager,
    symbol: str,
    side: Literal["buy", "sell"],
    size: float,
    leverage: int,
    price: Optional[float] = None,
    order_type: Literal["market", "limit"] = "market",
    reduce_only: bool = False,
) -> dict[str, Any]:
    """
    Place a perpetual futures order. Decimal precision is handled automatically.

    This tool places a perpetual futures order on Hyperliquid, automatically handling
    all decimal precision requirements. You can place either market orders (immediate
    execution) or limit orders (execute at specific price). Supports leverage trading
    and reduce-only orders for position management.

    Args:
        client_manager: Hyperliquid client manager instance
        decimal_manager: Decimal precision manager for formatting
        symbol: Perpetual contract symbol (e.g., "BTC", "ETH", "SOL"). Must be a
               valid perpetual contract available on Hyperliquid.
        side: Order side - "buy" to go long (bet on price increase), "sell" to go
             short (bet on price decrease)
        size: Position size in human-readable format (e.g., 0.5 for 0.5 BTC, 10 for
             10 ETH). Will be automatically formatted to match asset's decimal precision.
        leverage: Leverage multiplier (e.g., 5 for 5x leverage, 10 for 10x leverage).
                 Must be within the asset's maximum allowed leverage. Higher leverage
                 amplifies both gains and losses.
        price: Limit price for the order. Required for limit orders, ignored for
              market orders. Will be automatically formatted to match precision rules.
        order_type: Type of order - "market" for immediate execution at current
                   market price, "limit" to execute only at specified price or better.
                   Defaults to "market".
        reduce_only: If True, order can only reduce an existing position and cannot
                    increase it or open a new position. Useful for taking profits or
                    cutting losses without risk of over-trading. Defaults to False.

    Returns:
        Dictionary containing:
        - success: Boolean indicating if the order was placed successfully
        - data: Order result including:
            - status: "ok" if successful, or error details
            - response: Order confirmation with:
                - statuses: List of order statuses
                - data: Additional order data including fills and position updates
        - error: Error message if the order failed
        - error_type: Type of error that occurred

    Raises:
        ValueError: If parameters are invalid (e.g., limit order without price,
                   leverage exceeds maximum)
        Exception: If the API request fails or order is rejected

    Example:
        >>> # Place market long order with 3x leverage
        >>> result = await place_perp_order(
        ...     client_manager, decimal_manager,
        ...     symbol="BTC", side="buy", size=0.1, leverage=3, order_type="market"
        ... )
        >>> print(f"Order status: {result['data']['status']}")

        >>> # Place limit short order with 5x leverage
        >>> result = await place_perp_order(
        ...     client_manager, decimal_manager,
        ...     symbol="ETH", side="sell", size=1.0, leverage=5,
        ...     price=3500.0, order_type="limit"
        ... )

        >>> # Place reduce-only order to close part of position
        >>> result = await place_perp_order(
        ...     client_manager, decimal_manager,
        ...     symbol="SOL", side="sell", size=10, leverage=1,
        ...     order_type="market", reduce_only=True
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

        # Validate leverage is positive
        if leverage <= 0:
            return {
                "success": False,
                "error": f"Leverage must be positive, got {leverage}",
                "error_type": "ValueError",
            }

        # Get asset metadata to check max leverage
        metadata = await decimal_manager.get_asset_metadata(symbol)
        if metadata.max_leverage is not None and leverage > metadata.max_leverage:
            return {
                "success": False,
                "error": f"Leverage {leverage} exceeds maximum allowed leverage {metadata.max_leverage} for {symbol}",
                "error_type": "ValueError",
                "details": {
                    "symbol": symbol,
                    "requested_leverage": leverage,
                    "max_leverage": metadata.max_leverage,
                },
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
            "reduce_only": reduce_only,
        }

        # Submit order via Exchange client (spot=False for perpetuals)
        result = client_manager.exchange.order(order_params, spot=False)

        return {
            "success": True,
            "data": {
                "status": result.get("status", "unknown"),
                "response": result.get("response", {}),
                "leverage": leverage,
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
                "leverage": leverage,
                "price": price,
                "order_type": order_type,
                "reduce_only": reduce_only,
            },
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to place perpetual order: {str(e)}",
            "error_type": type(e).__name__,
            "details": {
                "symbol": symbol,
                "side": side,
                "size": size,
                "leverage": leverage,
                "price": price,
                "order_type": order_type,
                "reduce_only": reduce_only,
            },
        }


# TODO: Implement remaining Exchange endpoint tools:
# - cancel_order
# - cancel_all_orders
# - close_position
