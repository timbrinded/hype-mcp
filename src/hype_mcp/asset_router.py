"""Asset routing helpers for mapping perp and spot identifiers."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Set

from .errors import APIError, AssetNotFoundError
from .validation import _normalize_symbol


@dataclass(frozen=True)
class SpotMarketRoute:
    """Represents the preferred market to trade a given token."""

    market_index: int
    quote_index: Optional[int]
    quote_symbol: Optional[str]
    is_canonical: bool


@dataclass(frozen=True)
class SpotTokenInfo:
    """Represents a tradable spot token."""

    symbol: str
    token_index: int
    sz_decimals: int
    full_name: Optional[str] = None
    market_index: Optional[int] = None
    quote_token_index: Optional[int] = None
    quote_symbol: Optional[str] = None

    @property
    def api_symbol(self) -> str:
        """Return the string identifier required by the Exchange API."""
        target_index = (
            self.market_index if self.market_index is not None else self.token_index
        )
        return f"@{target_index}"


class AssetRouter:
    """Maps user-friendly symbols to spot token identifiers."""

    REFRESH_TTL = 86400.0  # seconds (1 day)
    QUOTE_PRIORITY = ("USDC", "UETH", "UBTC")

    def __init__(self, info_client: Any) -> None:
        self.info_client = info_client
        self._spot_tokens: Dict[str, SpotTokenInfo] = {}
        self._spot_alias_map: Dict[str, SpotTokenInfo] = {}
        self._market_routes: Dict[int, SpotMarketRoute] = {}
        self._perp_symbols: Set[str] = set()
        self._last_refresh: float = 0.0
        self.refresh()

    def refresh(self) -> None:
        """Fetch metadata from Hyperliquid and rebuild routing tables."""
        try:
            perp_meta = self.info_client.meta()
            spot_meta = self.info_client.spot_meta()
        except Exception as exc:  # pragma: no cover - network error pass-through
            raise APIError(
                message=f"Failed to load asset metadata from Hyperliquid: {exc}",
                api_response=None,
            ) from exc

        perp_universe = perp_meta.get("universe", [])
        spot_tokens = spot_meta.get("tokens") or []
        spot_markets = spot_meta.get("universe") or []

        if not spot_tokens or not spot_markets:
            if not self._spot_tokens:
                raise APIError(
                    message="Hyperliquid spot metadata is missing tokens or markets.",
                    api_response=None,
                )
            # Keep previously cached routes if refresh returned incomplete data.
            return

        market_routes = self._build_market_routes(spot_tokens, spot_markets)
        new_spot_tokens: Dict[str, SpotTokenInfo] = {}
        new_alias_map: Dict[str, SpotTokenInfo] = {}

        for token in spot_tokens:
            token_name = token.get("name")
            token_index = token.get("index")
            if not token_name or token_index is None:
                continue

            route = market_routes.get(token_index)
            info = SpotTokenInfo(
                symbol=token_name.upper(),
                token_index=token_index,
                sz_decimals=token.get("szDecimals", 0),
                full_name=token.get("fullName"),
                market_index=route.market_index if route else None,
                quote_token_index=route.quote_index if route else None,
                quote_symbol=route.quote_symbol if route else None,
            )
            new_spot_tokens[info.symbol] = info
            for alias in self._derive_aliases(token):
                if alias and alias not in new_alias_map:
                    new_alias_map[alias] = info
            canonical_alias = self._normalize_alias(info.symbol)
            if canonical_alias:
                new_alias_map[canonical_alias] = info

        if not new_spot_tokens:
            if not self._spot_tokens:
                raise APIError(
                    message="Hyperliquid spot metadata returned zero tradable tokens.",
                    api_response=None,
                )
            return

        self._perp_symbols = {asset.get("name", "").upper() for asset in perp_universe}
        self._spot_tokens = new_spot_tokens
        self._spot_alias_map = new_alias_map
        self._market_routes = market_routes
        self._last_refresh = time.time()

    def resolve_spot_symbol(self, symbol: str) -> SpotTokenInfo:
        """Return the spot token information for a user supplied symbol."""
        self._refresh_if_stale()
        normalized = _normalize_symbol(symbol)
        match = self._spot_alias_map.get(normalized)
        if match:
            return match
        # Symbol is unknown under the cached metadata; force a refresh in case
        # a new token was listed after the last refresh.
        self.refresh()
        match = self._spot_alias_map.get(normalized)
        if match:
            return match
        raise AssetNotFoundError(symbol)

    def _refresh_if_stale(self) -> None:
        if (time.time() - self._last_refresh) > self.REFRESH_TTL:
            self.refresh()

    def _build_market_routes(
        self, tokens: list[dict[str, Any]], markets: list[dict[str, Any]]
    ) -> Dict[int, SpotMarketRoute]:
        """Map token indices to their preferred markets with deterministic priority."""
        name_to_index = {
            (token.get("name") or "").upper(): token.get("index")
            for token in tokens
            if token.get("index") is not None
        }
        token_lookup = {
            token.get("index"): token
            for token in tokens
            if token.get("index") is not None
        }
        quote_priority: Dict[Optional[int], int] = {}
        for rank, quote_name in enumerate(self.QUOTE_PRIORITY):
            idx = name_to_index.get(quote_name)
            if idx is not None:
                quote_priority[idx] = rank

        market_routes: Dict[int, SpotMarketRoute] = {}
        for market in markets:
            pair = market.get("tokens") or []
            if len(pair) < 2:
                continue

            base_index, quote_index = pair[0], pair[1]
            if base_index is None or quote_index is None:
                continue

            market_index = self._extract_market_index(market)
            if market_index is None:
                continue

            quote_symbol = None
            quote_token = token_lookup.get(quote_index)
            if quote_token:
                quote_name = quote_token.get("name")
                if isinstance(quote_name, str):
                    quote_symbol = quote_name.upper()
            candidate = SpotMarketRoute(
                market_index=market_index,
                quote_index=quote_index,
                quote_symbol=quote_symbol,
                is_canonical=bool(market.get("isCanonical")),
            )
            existing = market_routes.get(base_index)
            market_routes[base_index] = self._select_market_route(
                existing, candidate, quote_priority
            )

        return market_routes

    @staticmethod
    def _extract_market_index(market: dict[str, Any]) -> Optional[int]:
        """Return the market index, falling back to parsing the name if needed."""
        market_index = market.get("index")
        if isinstance(market_index, int):
            return market_index

        name = market.get("name")
        if isinstance(name, str) and name.startswith("@"):
            maybe_number = name[1:]
            if maybe_number.isdigit():
                return int(maybe_number)
        return None

    def _select_market_route(
        self,
        existing: Optional[SpotMarketRoute],
        candidate: SpotMarketRoute,
        quote_priority: Dict[Optional[int], int],
    ) -> SpotMarketRoute:
        """Choose the better route based on quote priority and canonical status."""
        if existing is None:
            return candidate

        default_priority = len(self.QUOTE_PRIORITY)
        existing_priority = quote_priority.get(existing.quote_index, default_priority)
        candidate_priority = quote_priority.get(candidate.quote_index, default_priority)

        if candidate_priority != existing_priority:
            return candidate if candidate_priority < existing_priority else existing

        if candidate.is_canonical != existing.is_canonical:
            return candidate if candidate.is_canonical else existing

        if candidate.market_index != existing.market_index:
            return (
                candidate
                if candidate.market_index < existing.market_index
                else existing
            )

        return candidate

    def _derive_aliases(self, token: dict[str, Any]) -> Set[str]:
        """Generate all alias strings that should route to this token."""
        aliases: Set[str] = set()
        name = token.get("name")
        if name:
            normalized = self._normalize_alias(name)
            if normalized:
                aliases.add(normalized)
            if name.startswith("U") and len(name) > 1:
                stripped = self._normalize_alias(name[1:])
                if stripped:
                    aliases.add(stripped)

        full_name = token.get("fullName") or ""
        if full_name:
            full_alias = self._normalize_alias(full_name)
            if full_alias:
                aliases.add(full_alias)
                if full_alias.startswith("UNIT") and len(full_alias) > 4:
                    trimmed = full_alias[4:]
                    if trimmed:
                        aliases.add(trimmed)

        token_id = token.get("tokenId")
        if token_id:
            alias = self._normalize_alias(token_id)
            if alias:
                aliases.add(alias)

        return aliases

    @staticmethod
    def _normalize_alias(value: str) -> Optional[str]:
        """Normalize metadata derived aliases into the same format as user input."""
        cleaned = "".join(
            ch for ch in value.upper().strip() if ch.isalnum() or ch in {"-", "_"}
        )
        return cleaned or None
