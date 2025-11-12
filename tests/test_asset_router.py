"""Tests for the AssetRouter helper."""

from typing import Any

import pytest

from hype_mcp.asset_router import AssetRouter
from hype_mcp.errors import AssetNotFoundError


class StubInfoClient:
    """Simple stub that mimics the Info client metadata responses."""

    def __init__(
        self,
        spot_tokens: list[dict[str, Any]] | None = None,
        spot_universe: list[dict[str, Any]] | None = None,
    ):
        self._perp_meta = {
            "universe": [
                {"name": "ETH", "szDecimals": 4, "maxLeverage": 25},
                {"name": "FARTCOIN", "szDecimals": 1, "maxLeverage": 10},
            ]
        }
        default_tokens = [
            {
                "name": "USDC",
                "szDecimals": 2,
                "index": 0,
                "fullName": "USD Coin",
                "tokenId": "0xusdc",
            },
            {
                "name": "UETH",
                "szDecimals": 4,
                "index": 221,
                "fullName": "Unit Ethereum",
                "tokenId": "0xabc",
            },
            {
                "name": "UFART",
                "szDecimals": 1,
                "index": 333,
                "fullName": "Unit Fartcoin",
                "tokenId": "0xdef",
            },
        ]
        default_universe = [
            {
                "tokens": [221, 0],
                "name": "@9001",
                "index": 9001,
                "isCanonical": True,
            },
            {
                "tokens": [333, 0],
                "name": "@9002",
                "index": 9002,
                "isCanonical": True,
            },
        ]
        self._spot_meta = {
            "tokens": spot_tokens or default_tokens,
            "universe": spot_universe or default_universe,
        }

    def set_spot_metadata(
        self,
        tokens: list[dict[str, Any]],
        universe: list[dict[str, Any]],
    ) -> None:
        self._spot_meta = {"tokens": tokens, "universe": universe}

    def meta(self):
        return self._perp_meta

    def spot_meta(self):
        return self._spot_meta


class TestAssetRouter:
    """Unit tests for AssetRouter."""

    @pytest.fixture
    def router(self):
        return AssetRouter(StubInfoClient())

    def test_resolves_u_prefix_symbol(self, router):
        spot = router.resolve_spot_symbol("ETH")
        assert spot.symbol == "UETH"
        assert spot.api_symbol == "@9001"

    def test_resolves_full_name_alias(self, router):
        spot = router.resolve_spot_symbol("FARTCOIN")
        assert spot.symbol == "UFART"
        assert spot.api_symbol == "@9002"

    def test_unknown_symbol_raises(self, router):
        with pytest.raises(AssetNotFoundError):
            router.resolve_spot_symbol("DOES_NOT_EXIST")

    def test_refreshes_alias_after_ttl(self):
        initial_tokens = [
            {"name": "USDC", "szDecimals": 2, "index": 0},
            {
                "name": "ULMY",
                "szDecimals": 2,
                "index": 101,
                "fullName": "Unit Fartcoin",
                "tokenId": "0xaaa",
            },
        ]
        initial_universe = [
            {
                "tokens": [101, 0],
                "name": "@2001",
                "index": 2001,
                "isCanonical": True,
            }
        ]
        updated_tokens = [
            {"name": "USDC", "szDecimals": 2, "index": 0},
            {
                "name": "UFART",
                "szDecimals": 1,
                "index": 333,
                "fullName": "Unit Fartcoin",
                "tokenId": "0xdef",
            },
        ]
        updated_universe = [
            {
                "tokens": [333, 0],
                "name": "@2002",
                "index": 2002,
                "isCanonical": True,
            }
        ]
        client = StubInfoClient(
            spot_tokens=initial_tokens, spot_universe=initial_universe
        )
        router = AssetRouter(client)
        assert router.resolve_spot_symbol("FARTCOIN").symbol == "ULMY"
        assert router.resolve_spot_symbol("FARTCOIN").api_symbol == "@2001"

        client.set_spot_metadata(updated_tokens, updated_universe)
        router._last_refresh -= router.REFRESH_TTL + 1

        refreshed = router.resolve_spot_symbol("FARTCOIN")
        assert refreshed.symbol == "UFART"
        assert refreshed.api_symbol == "@2002"

    def test_refresh_on_symbol_miss(self):
        initial_tokens = [
            {"name": "USDC", "szDecimals": 2, "index": 0},
            {
                "name": "UETH",
                "szDecimals": 4,
                "index": 221,
                "fullName": "Unit Ethereum",
                "tokenId": "0xabc",
            },
        ]
        initial_universe = [
            {
                "tokens": [221, 0],
                "name": "@3001",
                "index": 3001,
                "isCanonical": True,
            }
        ]
        client = StubInfoClient(
            spot_tokens=initial_tokens, spot_universe=initial_universe
        )
        router = AssetRouter(client)

        client.set_spot_metadata(
            [
                {"name": "USDC", "szDecimals": 2, "index": 0},
                {
                    "name": "UFART",
                    "szDecimals": 1,
                    "index": 333,
                    "fullName": "Unit Fartcoin",
                    "tokenId": "0xdef",
                },
            ],
            [
                {
                    "tokens": [333, 0],
                    "name": "@3002",
                    "index": 3002,
                    "isCanonical": True,
                }
            ],
        )

        refreshed = router.resolve_spot_symbol("FARTCOIN")
        assert refreshed.symbol == "UFART"
        assert refreshed.api_symbol == "@3002"
