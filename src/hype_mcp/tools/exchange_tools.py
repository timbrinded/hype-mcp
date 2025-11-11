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


async def cancel_order(
    client_manager: HyperliquidClientManager,
    symbol: str,
    order_id: int,
) -> dict[str, Any]:
    """
    Cancel an open order.

    This tool cancels a specific open order on Hyperliquid. You need to provide
    the asset symbol and the order ID. The order ID can be obtained from the
    get_open_orders tool.

    Args:
        client_manager: Hyperliquid client manager instance
        symbol: Asset symbol for the order (e.g., "BTC", "ETH", "PURR"). Must match
               the symbol of the order you want to cancel.
        order_id: Order ID to cancel. This is the unique identifier returned when
                 the order was placed or can be found using get_open_orders.

    Returns:
        Dictionary containing:
        - success: Boolean indicating if the cancellation was successful
        - data: Cancellation result including:
            - status: "ok" if successful, or error details
            - response: Cancellation confirmation
        - error: Error message if the cancellation failed
        - error_type: Type of error that occurred

    Raises:
        Exception: If the API request fails or order cannot be cancelled

    Example:
        >>> # Cancel a specific order
        >>> result = await cancel_order(
        ...     client_manager,
        ...     symbol="BTC",
        ...     order_id=123456789
        ... )
        >>> print(f"Cancellation status: {result['data']['status']}")
    """
    try:
        # Prepare cancellation parameters
        cancel_params = {
            "coin": symbol,
            "oid": order_id,
        }

        # Submit cancellation via Exchange client
        result = client_manager.exchange.cancel(cancel_params)

        return {
            "success": True,
            "data": {
                "status": result.get("status", "unknown"),
                "response": result.get("response", {}),
                "cancelled_order_id": order_id,
                "symbol": symbol,
            },
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to cancel order: {str(e)}",
            "error_type": type(e).__name__,
            "details": {
                "symbol": symbol,
                "order_id": order_id,
            },
        }


async def cancel_all_orders(
    client_manager: HyperliquidClientManager,
    symbol: Optional[str] = None,
) -> dict[str, Any]:
    """
    Cancel all open orders, optionally filtered by symbol.

    This tool cancels all open orders on Hyperliquid. You can optionally filter
    by symbol to cancel only orders for a specific asset. If no symbol is provided,
    all open orders across all assets will be cancelled.

    Args:
        client_manager: Hyperliquid client manager instance
        symbol: Optional asset symbol to filter cancellations (e.g., "BTC", "ETH", "PURR").
               If provided, only orders for this symbol will be cancelled. If None,
               all orders across all assets will be cancelled.

    Returns:
        Dictionary containing:
        - success: Boolean indicating if the cancellation was successful
        - data: Cancellation result including:
            - status: "ok" if successful, or error details
            - response: Cancellation confirmation
            - cancelled_count: Number of orders cancelled
            - symbol: Symbol filter used (if any)
        - error: Error message if the cancellation failed
        - error_type: Type of error that occurred

    Raises:
        Exception: If the API request fails or orders cannot be cancelled

    Example:
        >>> # Cancel all orders for BTC
        >>> result = await cancel_all_orders(
        ...     client_manager,
        ...     symbol="BTC"
        ... )
        >>> print(f"Cancelled {result['data']['cancelled_count']} orders")

        >>> # Cancel all orders across all assets
        >>> result = await cancel_all_orders(client_manager)
        >>> print(f"Cancelled {result['data']['cancelled_count']} orders")
    """
    try:
        # First, get all open orders to count them
        from .info_tools import get_open_orders
        
        orders_result = await get_open_orders(client_manager)
        
        if not orders_result.get("success"):
            return {
                "success": False,
                "error": "Failed to fetch open orders before cancellation",
                "error_type": "APIError",
            }
        
        open_orders = orders_result.get("data", [])
        
        # Filter by symbol if provided
        if symbol:
            orders_to_cancel = [o for o in open_orders if o.get("coin") == symbol]
        else:
            orders_to_cancel = open_orders
        
        if not orders_to_cancel:
            return {
                "success": True,
                "data": {
                    "status": "ok",
                    "cancelled_count": 0,
                    "symbol": symbol,
                    "message": f"No open orders found{f' for {symbol}' if symbol else ''}",
                },
            }
        
        # Cancel each order
        cancelled_count = 0
        failed_cancellations = []
        
        for order in orders_to_cancel:
            try:
                cancel_params = {
                    "coin": order["coin"],
                    "oid": order["oid"],
                }
                result = client_manager.exchange.cancel(cancel_params)
                
                if result.get("status") == "ok":
                    cancelled_count += 1
                else:
                    failed_cancellations.append({
                        "order_id": order["oid"],
                        "symbol": order["coin"],
                        "error": result.get("response", "Unknown error"),
                    })
            except Exception as e:
                failed_cancellations.append({
                    "order_id": order["oid"],
                    "symbol": order["coin"],
                    "error": str(e),
                })
        
        return {
            "success": True,
            "data": {
                "status": "ok",
                "cancelled_count": cancelled_count,
                "total_orders": len(orders_to_cancel),
                "symbol": symbol,
                "failed_cancellations": failed_cancellations if failed_cancellations else None,
            },
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to cancel orders: {str(e)}",
            "error_type": type(e).__name__,
            "details": {
                "symbol": symbol,
            },
        }


async def close_position(
    client_manager: HyperliquidClientManager,
    decimal_manager: DecimalPrecisionManager,
    symbol: str,
    size: Optional[float] = None,
) -> dict[str, Any]:
    """
    Close a perpetual position (full or partial).

    This tool closes an open perpetual position by placing an opposite order.
    It automatically queries your current position to determine the correct side
    and size. You can close the entire position or specify a partial size to close.

    Args:
        client_manager: Hyperliquid client manager instance
        decimal_manager: Decimal precision manager for formatting
        symbol: Perpetual contract symbol (e.g., "BTC", "ETH", "SOL"). Must be a
               valid perpetual contract with an open position.
        size: Optional amount to close. If not provided, closes the entire position.
             If provided, must not exceed the current position size. Will be
             automatically formatted to match asset's decimal precision.

    Returns:
        Dictionary containing:
        - success: Boolean indicating if the position was closed successfully
        - data: Close result including:
            - status: "ok" if successful, or error details
            - response: Order confirmation for the closing trade
            - closed_size: Amount of position closed
            - side: Side of the closing order ("buy" or "sell")
            - position_side: Original position side ("long" or "short")
        - error: Error message if the close failed
        - error_type: Type of error that occurred

    Raises:
        ValueError: If no position exists for the symbol or size exceeds position
        Exception: If the API request fails or order is rejected

    Example:
        >>> # Close entire BTC position
        >>> result = await close_position(
        ...     client_manager, decimal_manager,
        ...     symbol="BTC"
        ... )
        >>> print(f"Closed {result['data']['closed_size']} BTC position")

        >>> # Close partial ETH position (close 0.5 ETH of a larger position)
        >>> result = await close_position(
        ...     client_manager, decimal_manager,
        ...     symbol="ETH",
        ...     size=0.5
        ... )
        >>> print(f"Closed {result['data']['closed_size']} ETH")
    """
    try:
        # Get current account state to find the position
        from .info_tools import get_account_state
        
        account_result = await get_account_state(client_manager)
        
        if not account_result.get("success"):
            return {
                "success": False,
                "error": "Failed to fetch account state",
                "error_type": "APIError",
            }
        
        # Find the position for this symbol
        positions = account_result.get("data", {}).get("assetPositions", [])
        position = None
        
        for pos in positions:
            if pos.get("position", {}).get("coin") == symbol:
                position = pos.get("position", {})
                break
        
        if not position:
            return {
                "success": False,
                "error": f"No open position found for {symbol}",
                "error_type": "ValueError",
                "details": {
                    "symbol": symbol,
                },
            }
        
        # Get position details
        position_size_str = position.get("szi", "0")
        position_size = float(position_size_str)
        
        if position_size == 0:
            return {
                "success": False,
                "error": f"Position size is zero for {symbol}",
                "error_type": "ValueError",
                "details": {
                    "symbol": symbol,
                },
            }
        
        # Determine position side and closing side
        is_long = position_size > 0
        position_side = "long" if is_long else "short"
        closing_side = "sell" if is_long else "buy"
        
        # Determine size to close
        abs_position_size = abs(position_size)
        if size is None:
            # Close entire position
            close_size = abs_position_size
        else:
            # Close partial position
            if size > abs_position_size:
                return {
                    "success": False,
                    "error": f"Requested close size {size} exceeds position size {abs_position_size}",
                    "error_type": "ValueError",
                    "details": {
                        "symbol": symbol,
                        "requested_size": size,
                        "position_size": abs_position_size,
                    },
                }
            close_size = size
        
        # Place opposite order to close position
        # Use reduce_only=True to ensure we only close, not open opposite position
        result = await place_perp_order(
            client_manager=client_manager,
            decimal_manager=decimal_manager,
            symbol=symbol,
            side=closing_side,
            size=close_size,
            leverage=1,  # Leverage doesn't matter for closing
            order_type="market",
            reduce_only=True,
        )
        
        if result.get("success"):
            # Add additional context to the result
            result["data"]["closed_size"] = close_size
            result["data"]["side"] = closing_side
            result["data"]["position_side"] = position_side
            result["data"]["was_full_close"] = size is None
        
        return result

    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": "ValueError",
            "details": {
                "symbol": symbol,
                "size": size,
            },
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to close position: {str(e)}",
            "error_type": type(e).__name__,
            "details": {
                "symbol": symbol,
                "size": size,
            },
        }
