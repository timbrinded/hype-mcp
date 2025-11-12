"""Info endpoint MCP tools for read-only operations."""

import asyncio
from typing import Any, Optional

from pydantic import ValidationError as PydanticValidationError

from ..client_manager import HyperliquidClientManager
from ..errors import APIError, AssetNotFoundError, format_error_response
from ..validation import MarketDataParams, WalletAddressParams

async def get_account_state(
    client_manager: HyperliquidClientManager,
    user_address: Optional[str] = None,
) -> dict[str, Any]:
    try:
        params = WalletAddressParams(user_address=user_address)
    except PydanticValidationError as exc:
        return format_error_response(exc)

    address = params.user_address or client_manager.wallet_address
    try:
        result = await asyncio.to_thread(client_manager.info.user_state, address)
        return {"success": True, "data": result}
    except Exception as exc:
        return format_error_response(
            APIError(
                message=f"Failed to fetch account state from Hyperliquid API: {exc}",
                api_response=None,
            )
        )


async def get_open_orders(
    client_manager: HyperliquidClientManager,
    user_address: Optional[str] = None,
) -> dict[str, Any]:
    try:
        params = WalletAddressParams(user_address=user_address)
    except PydanticValidationError as exc:
        return format_error_response(exc)

    address = params.user_address or client_manager.wallet_address
    try:
        result = await asyncio.to_thread(client_manager.info.open_orders, address)
        return {"success": True, "data": result}
    except Exception as exc:
        return format_error_response(
            APIError(
                message=f"Failed to fetch open orders from Hyperliquid API: {exc}",
                api_response=None,
            )
        )


async def get_market_data(
    client_manager: HyperliquidClientManager,
    symbol: Optional[str] = None,
) -> dict[str, Any]:
    try:
        params = MarketDataParams(symbol=symbol)
    except PydanticValidationError as exc:
        return format_error_response(exc)

    symbol = params.symbol

    try:
        all_mids = await asyncio.to_thread(client_manager.info.all_mids)
    except Exception as exc:
        return format_error_response(
            APIError(
                message=f"Failed to fetch market data from Hyperliquid API: {exc}",
                api_response=None,
            )
        )

    market_data = None

    if symbol in all_mids:
        try:
            meta = await asyncio.to_thread(client_manager.info.meta)
            meta_and_asset_ctxs = await asyncio.to_thread(
                client_manager.info.meta_and_asset_ctxs
            )
        except Exception as exc:
            return format_error_response(
                APIError(
                    message=f"Failed to fetch perpetual metadata: {exc}",
                    api_response=None,
                )
            )
        perp_meta = next(
            (asset for asset in meta.get("universe", []) if asset.get("name") == symbol),
            None,
        )
        if perp_meta:
            asset_ctxs = _extract_asset_contexts(meta_and_asset_ctxs)
            asset_ctx = next(
                (
                    ctx
                    for ctx in asset_ctxs
                    if isinstance(ctx, dict) and ctx.get("coin") == symbol
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

    spot_meta = None
    try:
        spot_meta = await asyncio.to_thread(client_manager.info.spot_meta)
    except Exception:
        pass

    if spot_meta and "tokens" in spot_meta:
        spot_token = next(
            (token for token in spot_meta["tokens"] if token.get("name") == symbol),
            None,
        )
        if spot_token:
            try:
                spot_mids = await asyncio.to_thread(
                    client_manager.info.spot_meta_and_asset_ctxs
                )
            except Exception as exc:
                return format_error_response(
                    APIError(
                        message=f"Failed to fetch spot metadata: {exc}",
                        api_response=None,
                    )
                )
            spot_ctxs = _extract_asset_contexts(spot_mids)
            spot_ctx = next(
                (
                    ctx
                    for ctx in spot_ctxs
                    if isinstance(ctx, dict) and ctx.get("coin") == symbol
                ),
                None,
            )
            market_data = {
                "coin": symbol,
                "markPx": spot_ctx.get("markPx") if spot_ctx else None,
                "midPx": spot_ctx.get("midPx") if spot_ctx else None,
                "prevDayPx": spot_ctx.get("prevDayPx") if spot_ctx else None,
                "dayNtlVlm": spot_ctx.get("dayNtlVlm") if spot_ctx else None,
            }

    if market_data is None:
        return format_error_response(AssetNotFoundError(symbol))

    return {"success": True, "data": market_data}


def _extract_asset_contexts(response: Any) -> list[dict[str, Any]]:
    if isinstance(response, dict):
        ctxs = response.get("assetCtxs")
        return ctxs if isinstance(ctxs, list) else []
    if isinstance(response, list):
        for item in response:
            if isinstance(item, list):
                return item
            if isinstance(item, dict):
                ctxs = item.get("assetCtxs")
                if isinstance(ctxs, list):
                    return ctxs
    return []


async def get_all_assets(
    client_manager: HyperliquidClientManager,
) -> dict[str, Any]:
    try:
        perp_meta = await asyncio.to_thread(client_manager.info.meta)
    except Exception as exc:
        return format_error_response(
            APIError(
                message=f"Failed to fetch perpetual metadata from Hyperliquid API: {exc}",
                api_response=None,
            )
        )

    perps = [
        {
            "name": asset["name"],
            "szDecimals": asset["szDecimals"],
            "maxLeverage": asset.get("maxLeverage"),
        }
        for asset in perp_meta.get("universe", [])
    ]

    try:
        spot_meta = await asyncio.to_thread(client_manager.info.spot_meta)
    except Exception as exc:
        return format_error_response(
            APIError(
                message=f"Failed to fetch spot metadata from Hyperliquid API: {exc}",
                api_response=None,
            )
        )

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

    return {"success": True, "data": {"perps": perps, "spot": spots}}
