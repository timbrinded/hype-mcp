"""Info endpoint MCP tools for read-only operations."""

from typing import Any, Optional
from pydantic import ValidationError as PydanticValidationError

from ..client_manager import HyperliquidClientManager
from ..validation import WalletAddressParams, MarketDataParams
from ..errors import format_error_response, APIError, AssetNotFoundError


async def get_account_state(
    client_manager: HyperliquidClientManager,
    user_address: Optional[str] = None,
) -> dict[str, Any]:
    """
    Get the current state of a user's account including positions, balances, and margin.

    This tool queries the Hyperliquid Info endpoint to retrieve comprehensive account
    information including open positions, available balances, margin usage, and
    withdrawal limits.

    Args:
        client_manager: Hyperliquid client manager instance
        user_address: Wallet address to query. If not provided, defaults to the
                     configured wallet address. Must be a valid Ethereum address
                     starting with 0x.

    Returns:
        Dictionary containing account state with the following structure:
        - assetPositions: List of open positions with details for each asset
        - crossMarginSummary: Cross-margin account summary including total value
                             and leverage
        - marginSummary: Per-asset margin details
        - withdrawable: Available balance that can be withdrawn

    Raises:
        Exception: If the API request fails or returns an error

    Example:
        >>> state = await get_account_state(client_manager)
        >>> print(f"Withdrawable: {state['withdrawable']}")
        >>> print(f"Positions: {state['assetPositions']}")
    """
    try:
        # Validate input parameters using Pydantic
        try:
            params = WalletAddressParams(user_address=user_address)
        except PydanticValidationError as e:
            return format_error_response(e)
        
        # Use configured wallet address if not specified
        address = params.user_address or client_manager.wallet_address

        # Query account state from Info endpoint
        try:
            result = client_manager.info.user_state(address)
        except Exception as e:
            raise APIError(
                message=f"Failed to fetch account state from Hyperliquid API: {str(e)}",
                api_response=None
            ) from e

        return {
            "success": True,
            "data": result,
        }
    except APIError as e:
        return format_error_response(e)
    except Exception as e:
        return format_error_response(e)


async def get_open_orders(
    client_manager: HyperliquidClientManager,
    user_address: Optional[str] = None,
) -> dict[str, Any]:
    """
    Get all open orders for a user.

    This tool retrieves all currently open orders across all assets for the specified
    user account. Orders are returned with full details including order ID, symbol,
    side, size, price, and timestamp.

    Args:
        client_manager: Hyperliquid client manager instance
        user_address: Wallet address to query. If not provided, defaults to the
                     configured wallet address. Must be a valid Ethereum address
                     starting with 0x.

    Returns:
        Dictionary containing:
        - success: Boolean indicating if the request succeeded
        - data: List of open orders, each containing:
            - oid: Order ID (unique identifier)
            - coin: Asset symbol (e.g., "BTC", "ETH", "PURR")
            - side: "B" for buy or "A" for sell/ask
            - sz: Order size as a string
            - px: Limit price as a string
            - timestamp: Order creation time in milliseconds
            - orderType: Type of order (e.g., "Limit")

    Raises:
        Exception: If the API request fails or returns an error

    Example:
        >>> orders = await get_open_orders(client_manager)
        >>> for order in orders['data']:
        ...     print(f"{order['coin']}: {order['side']} {order['sz']} @ {order['px']}")
    """
    try:
        # Validate input parameters using Pydantic
        try:
            params = WalletAddressParams(user_address=user_address)
        except PydanticValidationError as e:
            return format_error_response(e)
        
        # Use configured wallet address if not specified
        address = params.user_address or client_manager.wallet_address

        # Query open orders from Info endpoint
        try:
            result = client_manager.info.open_orders(address)
        except Exception as e:
            raise APIError(
                message=f"Failed to fetch open orders from Hyperliquid API: {str(e)}",
                api_response=None
            ) from e

        return {
            "success": True,
            "data": result,
        }
    except APIError as e:
        return format_error_response(e)
    except Exception as e:
        return format_error_response(e)


async def get_market_data(
    client_manager: HyperliquidClientManager,
    symbol: str,
) -> dict[str, Any]:
    """
    Get current market data for an asset including price, volume, and funding rate.

    This tool retrieves real-time market information for a specific asset symbol,
    including current prices, 24-hour volume, funding rates (for perpetuals),
    and open interest.

    Args:
        client_manager: Hyperliquid client manager instance
        symbol: Asset symbol to query (e.g., "BTC", "ETH", "PURR", "SOL").
               Symbol is case-sensitive and must match exactly.

    Returns:
        Dictionary containing:
        - success: Boolean indicating if the request succeeded
        - data: Market data including:
            - coin: Asset symbol
            - markPx: Current mark price as a string
            - midPx: Mid price from orderbook as a string
            - prevDayPx: Price 24 hours ago as a string
            - dayNtlVlm: 24-hour notional volume as a string
            - funding: Current funding rate (perpetuals only)
            - openInterest: Total open interest (perpetuals only)
            - premium: Premium/discount to index (perpetuals only)

    Raises:
        Exception: If the API request fails, symbol is invalid, or returns an error

    Example:
        >>> data = await get_market_data(client_manager, "BTC")
        >>> print(f"BTC Mark Price: ${data['data']['markPx']}")
        >>> print(f"24h Volume: ${data['data']['dayNtlVlm']}")
    """
    try:
        # Validate input parameters using Pydantic
        try:
            params = MarketDataParams(symbol=symbol)
        except PydanticValidationError as e:
            return format_error_response(e)
        
        # Use validated symbol
        symbol = params.symbol

        # Query all market data
        try:
            all_mids = client_manager.info.all_mids()
        except Exception as e:
            raise APIError(
                message=f"Failed to fetch market data from Hyperliquid API: {str(e)}",
                api_response=None
            ) from e

        # Check if symbol exists in spot or perp markets
        market_data = None

        # Check perpetuals
        if symbol in all_mids:
            # Get detailed perp data
            meta = client_manager.info.meta()
            perp_meta = next(
                (asset for asset in meta["universe"] if asset["name"] == symbol),
                None,
            )

            if perp_meta:
                # Get additional market stats
                meta_and_asset_ctxs = client_manager.info.meta_and_asset_ctxs()
                asset_ctx = next(
                    (
                        ctx
                        for ctx in meta_and_asset_ctxs[0]
                        if ctx["coin"] == symbol
                    ),
                    None,
                )

                market_data = {
                    "coin": symbol,
                    "markPx": asset_ctx.get("markPx") if asset_ctx else all_mids[symbol],
                    "midPx": all_mids[symbol],
                    "prevDayPx": asset_ctx.get("prevDayPx") if asset_ctx else None,
                    "dayNtlVlm": asset_ctx.get("dayNtlVlm") if asset_ctx else None,
                    "funding": asset_ctx.get("funding") if asset_ctx else None,
                    "openInterest": asset_ctx.get("openInterest") if asset_ctx else None,
                    "premium": asset_ctx.get("premium") if asset_ctx else None,
                }

        # Check spot markets
        spot_meta = client_manager.info.spot_meta()
        if spot_meta and "tokens" in spot_meta:
            spot_token = next(
                (token for token in spot_meta["tokens"] if token["name"] == symbol),
                None,
            )
            if spot_token:
                spot_mids = client_manager.info.spot_meta_and_asset_ctxs()
                spot_ctx = next(
                    (
                        ctx
                        for ctx in spot_mids[0]
                        if ctx["coin"] == symbol
                    ),
                    None,
                ) if spot_mids else None

                market_data = {
                    "coin": symbol,
                    "markPx": spot_ctx.get("markPx") if spot_ctx else None,
                    "midPx": spot_ctx.get("midPx") if spot_ctx else None,
                    "prevDayPx": spot_ctx.get("prevDayPx") if spot_ctx else None,
                    "dayNtlVlm": spot_ctx.get("dayNtlVlm") if spot_ctx else None,
                }

        if market_data is None:
            raise AssetNotFoundError(symbol)

        return {
            "success": True,
            "data": market_data,
        }
    except (APIError, AssetNotFoundError) as e:
        return format_error_response(e)
    except Exception as e:
        return format_error_response(e)


async def get_all_assets(
    client_manager: HyperliquidClientManager,
) -> dict[str, Any]:
    """
    Get metadata for all available assets on Hyperliquid.

    This tool retrieves comprehensive metadata for all tradeable assets on the
    Hyperliquid exchange, including both perpetual contracts and spot assets.
    The metadata includes important trading parameters like decimal precision
    and maximum leverage.

    Args:
        client_manager: Hyperliquid client manager instance

    Returns:
        Dictionary containing:
        - success: Boolean indicating if the request succeeded
        - data: Dictionary with two keys:
            - perps: List of perpetual contract metadata, each containing:
                - name: Asset symbol (e.g., "BTC", "ETH")
                - szDecimals: Number of decimal places for size precision
                - maxLeverage: Maximum allowed leverage for this asset
            - spot: List of spot asset metadata, each containing:
                - name: Asset symbol (e.g., "PURR", "HYPE")
                - szDecimals: Number of decimal places for size precision
                - index: Token index in the spot market

    Raises:
        Exception: If the API request fails or returns an error

    Example:
        >>> assets = await get_all_assets(client_manager)
        >>> print(f"Perpetuals: {len(assets['data']['perps'])}")
        >>> print(f"Spot assets: {len(assets['data']['spot'])}")
        >>> for perp in assets['data']['perps']:
        ...     print(f"{perp['name']}: {perp['maxLeverage']}x leverage")
    """
    try:
        # Get perpetual metadata
        try:
            perp_meta = client_manager.info.meta()
        except Exception as e:
            raise APIError(
                message=f"Failed to fetch perpetual metadata from Hyperliquid API: {str(e)}",
                api_response=None
            ) from e
        
        perps = [
            {
                "name": asset["name"],
                "szDecimals": asset["szDecimals"],
                "maxLeverage": asset.get("maxLeverage"),
            }
            for asset in perp_meta.get("universe", [])
        ]

        # Get spot metadata
        try:
            spot_meta = client_manager.info.spot_meta()
        except Exception as e:
            raise APIError(
                message=f"Failed to fetch spot metadata from Hyperliquid API: {str(e)}",
                api_response=None
            ) from e
        
        spots = []
        if spot_meta and "tokens" in spot_meta:
            spots = [
                {
                    "name": token["name"],
                    "szDecimals": token["szDecimals"],
                    "index": token["index"],
                }
                for token in spot_meta["tokens"]
            ]

        return {
            "success": True,
            "data": {
                "perps": perps,
                "spot": spots,
            },
        }
    except APIError as e:
        return format_error_response(e)
    except Exception as e:
        return format_error_response(e)
