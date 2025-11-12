"""Asset routing helpers for mapping perp and spot identifiers."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Set

from .errors import APIError, AssetNotFoundError
from .validation import _normalize_symbol


@dataclass(frozen=True)
class SpotTokenInfo:
    """Represents a tradable spot token."""

    symbol: str
    token_index: int
    sz_decimals: int
    full_name: Optional[str] = None
    market_index: Optional[int] = None

    @property
    def api_symbol(self) -> str:
        """Return the string identifier required by the Exchange API."""
        target_index = (
            self.market_index if self.market_index is not None else self.token_index
        )
        return f"@{target_index}"


class AssetRouter:
    """Maps user-friendly symbols to spot token identifiers."""

    REFRESH_TTL = 60.0  # seconds

    def __init__(self, info_client: Any) -> None:
        self.info_client = info_client
        self._spot_tokens: Dict[str, SpotTokenInfo] = {}
        self._spot_alias_map: Dict[str, SpotTokenInfo] = {}
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

        self._perp_symbols = {
            asset.get("name", "").upper() for asset in perp_meta.get("universe", [])
        }
        self._spot_tokens = {}
        self._spot_alias_map = {}

        market_map = self._build_market_map(spot_meta)
        tokens = spot_meta.get("tokens", [])
        for token in tokens:
            token_name = token.get("name")
            if not token_name:
                continue
            token_index = token.get("index", -1)
            market_info = market_map.get(token_index, {})
            info = SpotTokenInfo(
                symbol=token_name.upper(),
                token_index=token_index,
                sz_decimals=token.get("szDecimals", 0),
                full_name=token.get("fullName"),
                market_index=market_info.get("market_index"),
            )
            self._spot_tokens[info.symbol] = info
            for alias in self._derive_aliases(token):
                if alias and alias not in self._spot_alias_map:
                    self._spot_alias_map[alias] = info
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

    def _build_market_map(
        self, spot_meta: dict[str, Any]
    ) -> Dict[int, dict[str, Optional[int]]]:
        """Map token indices to their preferred market indices (USDC pairs first)."""
        tokens = spot_meta.get("tokens", [])
        usdc_index = next(
            (
                token.get("index")
                for token in tokens
                if (token.get("name") or "").upper() == "USDC"
            ),
            0,
        )

        market_map: Dict[int, dict[str, Optional[int]]] = {}
        for market in spot_meta.get("universe", []) or []:
            market_tokens = market.get("tokens")
            if not market_tokens or len(market_tokens) < 2:
                continue

            base_index, quote_index = market_tokens[0], market_tokens[1]
            market_index = market.get("index")

            # Process both tokens in the pair to ensure they both get mapped
            for token_to_map, other_token in [
                (base_index, quote_index),
                (quote_index, base_index),
            ]:
                if token_to_map is None:
                    continue

                should_override = False
                existing = market_map.get(token_to_map)

                if existing is None:
                    should_override = True
                elif (
                    other_token == usdc_index
                    and existing.get("quote_index") != usdc_index
                ):
                    should_override = True

                if should_override:
                    market_map[token_to_map] = {
                        "market_index": market_index,
                        "quote_index": other_token,
                    }

        return market_map

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
