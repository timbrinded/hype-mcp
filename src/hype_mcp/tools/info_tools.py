"""Info endpoint MCP tools for read-only operations."""

import asyncio
from collections.abc import Mapping, Sequence
from typing import Any, Optional

from pydantic import ValidationError as PydanticValidationError

from ..asset_router import AssetRouter
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
    *,
    asset_router: Optional[AssetRouter] = None,
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
            (
                asset
                for asset in meta.get("universe", [])
                if asset.get("name") == symbol
            ),
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
    spot_token_meta: Optional[Mapping[str, Any]] = None
    spot_lookup_symbol = symbol
    spot_market_index: Optional[int] = None
    spot_quote_symbol: Optional[str] = None
    spot_match_keys: set[str] = {symbol}

    if asset_router is not None:
        try:
            spot_info = asset_router.resolve_spot_symbol(symbol)
            spot_lookup_symbol = spot_info.symbol
            spot_market_index = spot_info.market_index
            spot_quote_symbol = spot_info.quote_symbol
            spot_match_keys.update(
                _build_spot_context_keys(
                    user_symbol=symbol,
                    canonical_symbol=spot_info.symbol,
                    quote_symbol=spot_info.quote_symbol,
                    market_index=spot_info.market_index,
                )
            )
        except AssetNotFoundError:
            spot_info = None
    else:
        spot_info = None
    try:
        spot_meta = await asyncio.to_thread(client_manager.info.spot_meta)
    except Exception:
        pass

    if spot_meta and "tokens" in spot_meta:
        spot_token_meta = _match_spot_token(spot_lookup_symbol, spot_meta["tokens"])
        if spot_token_meta is None and spot_lookup_symbol != symbol:
            spot_token_meta = _match_spot_token(symbol, spot_meta["tokens"])

        canonical_symbol = None
        if spot_token_meta and spot_token_meta.get("name"):
            canonical_symbol = (spot_token_meta.get("name") or "").upper()
        elif spot_info:
            canonical_symbol = spot_info.symbol

        if spot_token_meta or spot_info:
            derived_market_index, derived_quote_symbol = (None, None)
            if spot_token_meta:
                (
                    derived_market_index,
                    derived_quote_symbol,
                ) = _derive_spot_market_details(spot_token_meta, spot_meta)

            if spot_market_index is None:
                spot_market_index = (
                    spot_info.market_index if spot_info else derived_market_index
                )
            if spot_quote_symbol is None:
                spot_quote_symbol = (
                    spot_info.quote_symbol if spot_info else derived_quote_symbol
                )

            spot_match_keys.update(
                _build_spot_context_keys(
                    user_symbol=symbol,
                    canonical_symbol=canonical_symbol,
                    quote_symbol=spot_quote_symbol,
                    market_index=spot_market_index,
                )
            )

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
                    if isinstance(ctx, dict) and ctx.get("coin") in spot_match_keys
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


def _match_spot_token(
    symbol: Optional[str], tokens: Sequence[Mapping[str, Any]]
) -> Optional[Mapping[str, Any]]:
    if symbol is None:
        return None
    for token in tokens:
        name = token.get("name")
        if isinstance(name, str) and name.upper() == symbol:
            return token
    return None


def _derive_spot_market_details(
    spot_token: Mapping[str, Any], spot_meta: Mapping[str, Any]
) -> tuple[Optional[int], Optional[str]]:
    base_index = spot_token.get("index")
    if base_index is None:
        return None, None
    quote_symbol: Optional[str] = None
    market_index: Optional[int] = None
    markets = spot_meta.get("universe") or []
    tokens = spot_meta.get("tokens") or []

    for market in markets:
        pair = market.get("tokens") or []
        if len(pair) < 2 or pair[0] != base_index:
            continue
        market_index = market.get("index")
        if not isinstance(market_index, int):
            name = market.get("name")
            if isinstance(name, str) and name.startswith("@") and name[1:].isdigit():
                market_index = int(name[1:])
        quote_index = pair[1]
        for token in tokens:
            if token.get("index") == quote_index:
                quote_name = token.get("name")
                if isinstance(quote_name, str):
                    quote_symbol = quote_name.upper()
                break
        break

    return market_index, quote_symbol


def _build_spot_context_keys(
    *,
    user_symbol: str,
    canonical_symbol: Optional[str],
    quote_symbol: Optional[str],
    market_index: Optional[int],
) -> set[str]:
    keys: set[str] = set()

    if canonical_symbol:
        keys.add(canonical_symbol)
        if canonical_symbol.startswith("U") and len(canonical_symbol) > 1:
            stripped = canonical_symbol[1:]
            keys.add(stripped)
            if quote_symbol:
                keys.add(f"{stripped}/{quote_symbol}")

    if quote_symbol:
        if canonical_symbol:
            keys.add(f"{canonical_symbol}/{quote_symbol}")
        keys.add(f"{user_symbol}/{quote_symbol}")

    if market_index is not None:
        keys.add(f"@{market_index}")

    return {key for key in keys if key}


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
