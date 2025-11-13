"""Exchange endpoint MCP tools for trade execution."""

import asyncio
from typing import Any, Literal, Optional

from hyperliquid.utils.signing import OrderType
from pydantic import ValidationError as PydanticValidationError

from ..asset_router import AssetRouter
from ..client_manager import HyperliquidClientManager
from ..decimal_manager import DecimalPrecisionManager
from ..errors import (
    APIError,
    AssetNotFoundError,
    LeverageExceededError,
    OrderNotFoundError,
    PositionNotFoundError,
    PrecisionError,
    ValidationError,
    format_error_response,
)
from ..validation import (
    CancelOrderParams,
    ClosePositionParams,
    MarketDataParams,
    PerpOrderParams,
    SpotOrderParams,
    UsdClassTransferParams,
)


DEFAULT_MARKET_SLIPPAGE = 0.05


def _limit_order_type(tif: Literal["Alo", "Ioc", "Gtc"]) -> OrderType:
    """Hyperliquid expects market orders as IOC limit orders."""

    return {"limit": {"tif": tif}}


async def place_spot_order(
    client_manager: HyperliquidClientManager,
    decimal_manager: DecimalPrecisionManager,
    asset_router: AssetRouter,
    symbol: Optional[str] = None,
    side: Optional[Literal["buy", "sell"]] = None,
    size: Optional[float] = None,
    price: Optional[float] = None,
    order_type: Literal["market", "limit"] = "market",
) -> dict[str, Any]:
    try:
        params = SpotOrderParams(
            symbol=symbol,
            side=side,
            size=size,
            price=price,
            order_type=order_type,
        )
    except PydanticValidationError as exc:
        return format_error_response(exc)

    user_symbol = params.symbol
    side = params.side
    size = params.size
    price = params.price
    order_type = params.order_type

    try:
        try:
            spot_token = asset_router.resolve_spot_symbol(user_symbol)
        except AssetNotFoundError as exc:
            return format_error_response(exc)

        symbol = spot_token.symbol
        api_symbol = spot_token.api_symbol

        try:
            metadata = await decimal_manager.get_asset_metadata(symbol)
        except ValueError as exc:
            raise AssetNotFoundError(user_symbol) from exc

        if metadata.asset_type != "spot":
            raise ValidationError(
                message=f"{user_symbol} is not a spot asset.",
                field="symbol",
                value=user_symbol,
                constraint="spot orders require spot assets",
            )

        if spot_token.token_index < 0:
            raise ValidationError(
                message=f"Spot asset metadata for {user_symbol} is missing token index.",
                field="symbol",
                value=user_symbol,
                constraint="spot assets must provide an index identifier",
            )

        if spot_token.market_index is None:
            raise ValidationError(
                message=(
                    f"Spot market metadata for {user_symbol} is missing the USDC pair index."
                ),
                field="symbol",
                value=user_symbol,
                constraint="spot assets must provide a market identifier",
            )

        try:
            formatted_size = await decimal_manager.format_size_for_api(symbol, size)
        except ValueError as exc:
            if "not found" in str(exc).lower():
                raise AssetNotFoundError(user_symbol) from exc
            raise PrecisionError(
                message=f"Invalid size precision for {user_symbol}: {exc}",
                symbol=user_symbol,
                value=size,
                constraint="size must match asset's szDecimals",
            ) from exc

        limit_px: Optional[float] = None
        if order_type == "limit" and price is not None:
            try:
                formatted_price = await decimal_manager.format_price_for_api(
                    symbol, price
                )
            except ValueError as exc:
                constraint = (
                    "price must have max 5 significant figures"
                    if "significant figures" in str(exc).lower()
                    else "price must match asset's decimal constraints"
                )
                raise PrecisionError(
                    message=f"Invalid price precision for {user_symbol}: {exc}",
                    symbol=user_symbol,
                    value=price,
                    constraint=constraint,
                ) from exc
            limit_px = float(formatted_price)

        is_buy = side == "buy"

        try:
            if order_type == "market":
                result = await asyncio.to_thread(
                    client_manager.exchange.market_open,
                    name=api_symbol,
                    is_buy=is_buy,
                    sz=float(formatted_size),
                    px=None,
                    slippage=DEFAULT_MARKET_SLIPPAGE,
                )
            else:
                # limit orders always have a price after validation
                if limit_px is None:
                    raise PrecisionError(
                        message=f"Limit order for {user_symbol} requires a price",
                        symbol=user_symbol,
                        value=price or 0,
                        constraint="limit orders must include price",
                    )
                result = await asyncio.to_thread(
                    client_manager.exchange.order,
                    name=api_symbol,
                    is_buy=is_buy,
                    sz=float(formatted_size),
                    limit_px=limit_px,
                    order_type=_limit_order_type("Gtc"),
                    reduce_only=False,
                )
        except Exception as exc:
            raise APIError(
                message=f"Failed to submit spot order to Hyperliquid API: {exc}",
                api_response=None,
            ) from exc

        if result.get("status") != "ok":
            raise APIError(
                message=f"Order rejected by Hyperliquid: {result.get('response', 'Unknown error')}",
                api_response=result,
            )

        return {
            "success": True,
            "data": {
                "status": result.get("status", "unknown"),
                "response": result.get("response", {}),
            },
        }

    except (ValidationError, APIError, PrecisionError, AssetNotFoundError) as exc:
        return format_error_response(exc)
    except Exception as exc:
        return format_error_response(exc)


async def place_perp_order(
    client_manager: HyperliquidClientManager,
    decimal_manager: DecimalPrecisionManager,
    symbol: Optional[str] = None,
    side: Optional[Literal["buy", "sell"]] = None,
    size: Optional[float] = None,
    leverage: Optional[int] = None,
    price: Optional[float] = None,
    order_type: Literal["market", "limit"] = "market",
    reduce_only: bool = False,
) -> dict[str, Any]:
    try:
        params = PerpOrderParams(
            symbol=symbol,
            side=side,
            size=size,
            leverage=leverage,
            price=price,
            order_type=order_type,
            reduce_only=reduce_only,
        )
    except PydanticValidationError as exc:
        return format_error_response(exc)

    symbol = params.symbol
    side = params.side
    size = params.size
    leverage = params.leverage
    price = params.price
    order_type = params.order_type
    reduce_only = params.reduce_only

    try:
        try:
            metadata = await decimal_manager.get_asset_metadata(symbol)
        except ValueError as exc:
            if "not found" in str(exc).lower():
                raise AssetNotFoundError(symbol) from exc
            raise

        if metadata.max_leverage is not None and leverage > metadata.max_leverage:
            raise LeverageExceededError(
                symbol=symbol,
                requested_leverage=leverage,
                max_leverage=metadata.max_leverage,
            )

        try:
            formatted_size = await decimal_manager.format_size_for_api(symbol, size)
        except ValueError as exc:
            raise PrecisionError(
                message=f"Invalid size precision for {symbol}: {exc}",
                symbol=symbol,
                value=size,
                constraint="size must match asset's szDecimals",
            ) from exc

        limit_px: Optional[float] = None
        if order_type == "limit" and price is not None:
            try:
                formatted_price = await decimal_manager.format_price_for_api(
                    symbol, price
                )
            except ValueError as exc:
                constraint = (
                    "price must have max 5 significant figures"
                    if "significant figures" in str(exc).lower()
                    else "price must match asset's decimal constraints"
                )
                raise PrecisionError(
                    message=f"Invalid price precision for {symbol}: {exc}",
                    symbol=symbol,
                    value=price,
                    constraint=constraint,
                ) from exc
            limit_px = float(formatted_price)

        is_buy = side == "buy"

        try:
            if order_type == "market" and not reduce_only:
                result = await asyncio.to_thread(
                    client_manager.exchange.market_open,
                    name=symbol,
                    is_buy=is_buy,
                    sz=float(formatted_size),
                    px=None,
                    slippage=DEFAULT_MARKET_SLIPPAGE,
                )
            else:
                if order_type == "market":
                    market_px = await asyncio.to_thread(
                        client_manager.exchange._slippage_price,
                        symbol,
                        is_buy,
                        DEFAULT_MARKET_SLIPPAGE,
                        None,
                    )
                    limit_value = float(market_px)
                    order_type_dict = _limit_order_type("Ioc")
                else:
                    if limit_px is None:
                        raise PrecisionError(
                            message=f"Limit order for {symbol} requires a price",
                            symbol=symbol,
                            value=price or 0,
                            constraint="limit orders must include price",
                        )
                    limit_value = limit_px
                    order_type_dict = _limit_order_type("Gtc")

                result = await asyncio.to_thread(
                    client_manager.exchange.order,
                    name=symbol,
                    is_buy=is_buy,
                    sz=float(formatted_size),
                    limit_px=limit_value,
                    order_type=order_type_dict,
                    reduce_only=reduce_only,
                )
        except Exception as exc:
            raise APIError(
                message=f"Failed to submit perpetual order to Hyperliquid API: {exc}",
                api_response=None,
            ) from exc

        if result.get("status") != "ok":
            raise APIError(
                message=f"Order rejected by Hyperliquid: {result.get('response', 'Unknown error')}",
                api_response=result,
            )

        return {
            "success": True,
            "data": {
                "status": result.get("status", "unknown"),
                "response": result.get("response", {}),
                "leverage": leverage,
            },
        }

    except (
        ValidationError,
        APIError,
        PrecisionError,
        AssetNotFoundError,
        LeverageExceededError,
    ) as exc:
        return format_error_response(exc)
    except Exception as exc:
        return format_error_response(exc)


async def cancel_order(
    client_manager: HyperliquidClientManager,
    symbol: Optional[str] = None,
    order_id: Optional[int] = None,
) -> dict[str, Any]:
    try:
        params = CancelOrderParams(symbol=symbol, order_id=order_id)
    except PydanticValidationError as exc:
        return format_error_response(exc)

    symbol = params.symbol
    order_id = params.order_id

    try:
        try:
            result = await asyncio.to_thread(
                client_manager.exchange.cancel,
                symbol,
                order_id,
            )
        except Exception as exc:
            raise APIError(
                message=f"Failed to cancel order via Hyperliquid API: {exc}",
                api_response=None,
            ) from exc

        if result.get("status") != "ok":
            response_str = str(result.get("response", ""))
            if (
                "not found" in response_str.lower()
                or "does not exist" in response_str.lower()
            ):
                raise OrderNotFoundError(symbol=symbol, order_id=order_id)
            raise APIError(
                message=f"Order cancellation rejected by Hyperliquid: {result.get('response', 'Unknown error')}",
                api_response=result,
            )

        return {
            "success": True,
            "data": {
                "status": result.get("status", "unknown"),
                "response": result.get("response", {}),
                "cancelled_order_id": order_id,
                "symbol": symbol,
            },
        }
    except (ValidationError, APIError, OrderNotFoundError) as exc:
        return format_error_response(exc)
    except Exception as exc:
        return format_error_response(exc)


async def cancel_all_orders(
    client_manager: HyperliquidClientManager,
    symbol: Optional[str] = None,
) -> dict[str, Any]:
    try:
        if symbol is not None:
            try:
                params = MarketDataParams(symbol=symbol)
            except PydanticValidationError as exc:
                return format_error_response(exc)
            symbol = params.symbol

        from .info_tools import get_open_orders

        orders_result = await get_open_orders(client_manager)
        if not orders_result.get("success"):
            raise APIError(
                message="Failed to fetch open orders before cancellation",
                api_response=orders_result,
            )

        open_orders = orders_result.get("data", [])
        orders_to_cancel = (
            [o for o in open_orders if o.get("coin") == symbol]
            if symbol
            else open_orders
        )

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

        cancelled_count = 0
        failed_cancellations: list[dict[str, Any]] = []

        for order in orders_to_cancel:
            try:
                result = await asyncio.to_thread(
                    client_manager.exchange.cancel,
                    order["coin"],
                    order["oid"],
                )
                if result.get("status") == "ok":
                    cancelled_count += 1
                else:
                    failed_cancellations.append(
                        {
                            "order_id": order["oid"],
                            "symbol": order["coin"],
                            "error": result.get("response", "Unknown error"),
                        }
                    )
            except Exception as exc:
                failed_cancellations.append(
                    {
                        "order_id": order["oid"],
                        "symbol": order["coin"],
                        "error": str(exc),
                    }
                )

        return {
            "success": True,
            "data": {
                "status": "ok",
                "cancelled_count": cancelled_count,
                "total_orders": len(orders_to_cancel),
                "symbol": symbol,
                "failed_cancellations": failed_cancellations or None,
            },
        }
    except (ValidationError, APIError) as exc:
        return format_error_response(exc)
    except Exception as exc:
        return format_error_response(exc)


async def close_position(
    client_manager: HyperliquidClientManager,
    decimal_manager: DecimalPrecisionManager,
    symbol: Optional[str] = None,
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
        params = ClosePositionParams(symbol=symbol, size=size)
    except PydanticValidationError as exc:
        return format_error_response(exc)

    symbol = params.symbol
    size = params.size

    try:
        # Get current account state to find the position
        from .info_tools import get_account_state

        account_result = await get_account_state(client_manager)

        if not account_result.get("success"):
            raise APIError(
                message="Failed to fetch account state", api_response=account_result
            )

        # Find the position for this symbol
        positions = account_result.get("data", {}).get("assetPositions", [])
        position = None

        for pos in positions:
            if pos.get("position", {}).get("coin") == symbol:
                position = pos.get("position", {})
                break

        if not position:
            raise PositionNotFoundError(symbol=symbol)

        # Get position details
        position_size_str = position.get("szi", "0")
        position_size = float(position_size_str)

        if position_size == 0:
            raise PositionNotFoundError(symbol=symbol)

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
                raise ValidationError(
                    message=f"Requested close size {size} exceeds position size {abs_position_size}. You can only close up to {abs_position_size}.",
                    field="size",
                    value=size,
                    constraint=f"size must be <= {abs_position_size}",
                )
            close_size = size

        # Close position using market_close for full close, or place_perp_order for partial
        if size is None:
            try:
                result_raw = await asyncio.to_thread(
                    client_manager.exchange.market_close,
                    symbol,
                )
                if result_raw.get("status") != "ok":
                    raise APIError(
                        message=f"Position close rejected by Hyperliquid: {result_raw.get('response', 'Unknown error')}",
                        api_response=result_raw,
                    )
                result = {
                    "success": True,
                    "data": {
                        "status": result_raw.get("status", "unknown"),
                        "response": result_raw.get("response", {}),
                        "closed_size": close_size,
                        "side": closing_side,
                        "position_side": position_side,
                        "was_full_close": True,
                    },
                }
            except Exception as exc:
                if not isinstance(exc, APIError):
                    raise APIError(
                        message=f"Failed to close position via Hyperliquid API: {exc}",
                        api_response=None,
                    ) from exc
                raise
        else:
            # Partial close - use place_perp_order with reduce_only
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
                result["data"]["was_full_close"] = False

        return result

    except (
        ValidationError,
        APIError,
        PositionNotFoundError,
        PrecisionError,
        AssetNotFoundError,
        LeverageExceededError,
    ) as e:
        return format_error_response(e)
    except Exception as e:
        return format_error_response(e)


async def transfer_wallet_funds(
    client_manager: HyperliquidClientManager,
    amount: Optional[float] = None,
    direction: Optional[str] = None,
) -> dict[str, Any]:
    """Transfer USDC between perp and spot wallets."""

    try:
        params = UsdClassTransferParams(amount=amount, direction=direction)
    except PydanticValidationError as exc:
        return format_error_response(exc)

    to_perp = params.direction == "spot_to_perp"

    try:
        exchange = client_manager.exchange
        wallet_address = getattr(getattr(exchange, "wallet", None), "address", None)
        account_address = getattr(exchange, "account_address", None)

        if account_address and wallet_address:
            if account_address.lower() != wallet_address.lower():
                raise ValidationError(
                    message=(
                        "Internal transfers require the configured account address "
                        "to match the signing wallet. Update your configuration or "
                        "run the server with direct wallet control."
                    ),
                    field="direction",
                    value=params.direction,
                    constraint="account_address must equal wallet address for transfers",
                )

        try:
            result = await asyncio.to_thread(
                exchange.usd_class_transfer,
                float(params.amount),
                to_perp,
            )
        except Exception as exc:
            raise APIError(
                message=f"Failed to submit wallet transfer to Hyperliquid API: {exc}",
                api_response=None,
            ) from exc

        if result.get("status") != "ok":
            raise APIError(
                message=f"Wallet transfer rejected by Hyperliquid: {result.get('response', 'Unknown error')}",
                api_response=result,
            )

        return {
            "success": True,
            "data": {
                "status": result.get("status", "unknown"),
                "response": result.get("response", {}),
                "direction": params.direction,
                "amount": float(params.amount),
            },
        }

    except (ValidationError, APIError) as exc:
        return format_error_response(exc)
    except Exception as exc:
        return format_error_response(exc)
