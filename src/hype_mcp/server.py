"""Main MCP server implementation."""

import json
from functools import partial
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .client_manager import HyperliquidClientManager
from .config import HyperliquidConfig
from .decimal_manager import DecimalPrecisionManager
from .errors import format_error_response
from .tools import (
    cancel_all_orders,
    cancel_order,
    close_position,
    get_account_state,
    get_all_assets,
    get_market_data,
    get_open_orders,
    place_perp_order,
    place_spot_order,
)


class HyperliquidMCPServer:
    """Main MCP server class for Hyperliquid integration."""

    def __init__(self, config: HyperliquidConfig):
        """
        Initialize the Hyperliquid MCP server.

        Args:
            config: Validated configuration for the server
        """
        self.config = config
        self.testnet = config.testnet
        self.private_key = config.private_key
        self.wallet_address = config.wallet_address

        # Initialize client manager
        self.client_manager = HyperliquidClientManager(
            testnet=self.testnet,
            wallet_address=self.wallet_address,
            private_key=self.private_key,
        )

        # Initialize decimal precision manager
        self.decimal_manager = DecimalPrecisionManager(
            info_client=self.client_manager.info
        )

        self.mcp = Server("hyperliquid-mcp-server")
        self._init_tool_handlers()
        self._register_tools()

    def _init_tool_handlers(self) -> None:
        self._tool_handlers = {
            "get_account_state": partial(get_account_state, self.client_manager),
            "get_open_orders": partial(get_open_orders, self.client_manager),
            "get_market_data": partial(get_market_data, self.client_manager),
            "get_all_assets": partial(get_all_assets, self.client_manager),
            "place_spot_order": partial(
                place_spot_order,
                self.client_manager,
                self.decimal_manager,
            ),
            "place_perp_order": partial(
                place_perp_order,
                self.client_manager,
                self.decimal_manager,
            ),
            "cancel_order": partial(cancel_order, self.client_manager),
            "cancel_all_orders": partial(cancel_all_orders, self.client_manager),
            "close_position": partial(
                close_position,
                self.client_manager,
                self.decimal_manager,
            ),
        }
        self._tool_arguments = {
            "get_account_state": ["user_address"],
            "get_open_orders": ["user_address"],
            "get_market_data": ["symbol"],
            "get_all_assets": [],
            "place_spot_order": ["symbol", "side", "size", "price", "order_type"],
            "place_perp_order": [
                "symbol",
                "side",
                "size",
                "leverage",
                "price",
                "order_type",
                "reduce_only",
            ],
            "cancel_order": ["symbol", "order_id"],
            "cancel_all_orders": ["symbol"],
            "close_position": ["symbol", "size"],
        }

    def _register_tools(self):
        """Register all MCP tools."""

        @self.mcp.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available tools."""
            return [
                Tool(
                    name="get_account_state",
                    description=(
                        "Get the current state of a user's account including positions, "
                        "balances, and margin. Returns comprehensive account information "
                        "including open positions, available balances, margin usage, and "
                        "withdrawal limits."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_address": {
                                "type": "string",
                                "description": (
                                    "Wallet address to query. If not provided, defaults to "
                                    "the configured wallet address. Must be a valid Ethereum "
                                    "address starting with 0x."
                                ),
                            },
                        },
                    },
                ),
                Tool(
                    name="get_open_orders",
                    description=(
                        "Get all open orders for a user. Returns all currently open orders "
                        "across all assets with full details including order ID, symbol, "
                        "side, size, price, and timestamp."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_address": {
                                "type": "string",
                                "description": (
                                    "Wallet address to query. If not provided, defaults to "
                                    "the configured wallet address. Must be a valid Ethereum "
                                    "address starting with 0x."
                                ),
                            },
                        },
                    },
                ),
                Tool(
                    name="get_market_data",
                    description=(
                        "Get current market data for an asset including price, volume, "
                        "and funding rate. Returns real-time market information including "
                        "current prices, 24-hour volume, funding rates (for perpetuals), "
                        "and open interest."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": (
                                    "Asset symbol to query (e.g., 'BTC', 'ETH', 'PURR', 'SOL'). "
                                    "Symbol is case-sensitive and must match exactly."
                                ),
                            },
                        },
                        "required": ["symbol"],
                    },
                ),
                Tool(
                    name="get_all_assets",
                    description=(
                        "Get metadata for all available assets on Hyperliquid. Returns "
                        "comprehensive metadata for all tradeable assets including both "
                        "perpetual contracts and spot assets. Includes important trading "
                        "parameters like decimal precision and maximum leverage."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                Tool(
                    name="place_spot_order",
                    description=(
                        "Place a spot market order. Decimal precision is handled automatically. "
                        "You can place either market orders (immediate execution) or limit orders "
                        "(execute at specific price). This tool automatically formats sizes and "
                        "prices according to Hyperliquid's decimal precision requirements."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": (
                                    "Spot asset symbol (e.g., 'PURR', 'HYPE'). Must be a valid "
                                    "spot asset available on Hyperliquid."
                                ),
                            },
                            "side": {
                                "type": "string",
                                "enum": ["buy", "sell"],
                                "description": (
                                    "Order side - 'buy' to purchase the asset, 'sell' to sell the asset"
                                ),
                            },
                            "size": {
                                "type": "number",
                                "description": (
                                    "Quantity to trade in human-readable format (e.g., 100.5, 1000). "
                                    "Will be automatically formatted to match asset's decimal precision."
                                ),
                            },
                            "price": {
                                "type": "number",
                                "description": (
                                    "Limit price for the order. Required for limit orders, ignored for "
                                    "market orders. Will be automatically formatted to match precision rules."
                                ),
                            },
                            "order_type": {
                                "type": "string",
                                "enum": ["market", "limit"],
                                "description": (
                                    "Type of order - 'market' for immediate execution at current market "
                                    "price, 'limit' to execute only at specified price or better. "
                                    "Defaults to 'market'."
                                ),
                            },
                        },
                        "required": ["symbol", "side", "size"],
                    },
                ),
                Tool(
                    name="place_perp_order",
                    description=(
                        "Place a perpetual futures order. Decimal precision is handled automatically. "
                        "You can place either market orders (immediate execution) or limit orders "
                        "(execute at specific price). Supports leverage trading and reduce-only orders "
                        "for position management. This tool automatically formats sizes and prices "
                        "according to Hyperliquid's decimal precision requirements."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": (
                                    "Perpetual contract symbol (e.g., 'BTC', 'ETH', 'SOL'). Must be a "
                                    "valid perpetual contract available on Hyperliquid."
                                ),
                            },
                            "side": {
                                "type": "string",
                                "enum": ["buy", "sell"],
                                "description": (
                                    "Order side - 'buy' to go long (bet on price increase), 'sell' to "
                                    "go short (bet on price decrease)"
                                ),
                            },
                            "size": {
                                "type": "number",
                                "description": (
                                    "Position size in human-readable format (e.g., 0.5 for 0.5 BTC, "
                                    "10 for 10 ETH). Will be automatically formatted to match asset's "
                                    "decimal precision."
                                ),
                            },
                            "leverage": {
                                "type": "integer",
                                "description": (
                                    "Leverage multiplier (e.g., 5 for 5x leverage, 10 for 10x leverage). "
                                    "Must be within the asset's maximum allowed leverage. Higher leverage "
                                    "amplifies both gains and losses."
                                ),
                            },
                            "price": {
                                "type": "number",
                                "description": (
                                    "Limit price for the order. Required for limit orders, ignored for "
                                    "market orders. Will be automatically formatted to match precision rules."
                                ),
                            },
                            "order_type": {
                                "type": "string",
                                "enum": ["market", "limit"],
                                "description": (
                                    "Type of order - 'market' for immediate execution at current market "
                                    "price, 'limit' to execute only at specified price or better. "
                                    "Defaults to 'market'."
                                ),
                            },
                            "reduce_only": {
                                "type": "boolean",
                                "description": (
                                    "If true, order can only reduce an existing position and cannot "
                                    "increase it or open a new position. Useful for taking profits or "
                                    "cutting losses. Defaults to false."
                                ),
                            },
                        },
                        "required": ["symbol", "side", "size", "leverage"],
                    },
                ),
                Tool(
                    name="cancel_order",
                    description=(
                        "Cancel an open order. You need to provide the asset symbol and the order ID. "
                        "The order ID can be obtained from the get_open_orders tool."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": (
                                    "Asset symbol for the order (e.g., 'BTC', 'ETH', 'PURR'). Must match "
                                    "the symbol of the order you want to cancel."
                                ),
                            },
                            "order_id": {
                                "type": "integer",
                                "description": (
                                    "Order ID to cancel. This is the unique identifier returned when "
                                    "the order was placed or can be found using get_open_orders."
                                ),
                            },
                        },
                        "required": ["symbol", "order_id"],
                    },
                ),
                Tool(
                    name="cancel_all_orders",
                    description=(
                        "Cancel all open orders, optionally filtered by symbol. If no symbol is provided, "
                        "all open orders across all assets will be cancelled. Returns the count of "
                        "cancelled orders."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": (
                                    "Optional asset symbol to filter cancellations (e.g., 'BTC', 'ETH', 'PURR'). "
                                    "If provided, only orders for this symbol will be cancelled. If not provided, "
                                    "all orders across all assets will be cancelled."
                                ),
                            },
                        },
                    },
                ),
                Tool(
                    name="close_position",
                    description=(
                        "Close a perpetual position (full or partial). Automatically queries your current "
                        "position to determine the correct side and size. You can close the entire position "
                        "or specify a partial size to close."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": (
                                    "Perpetual contract symbol (e.g., 'BTC', 'ETH', 'SOL'). Must be a "
                                    "valid perpetual contract with an open position."
                                ),
                            },
                            "size": {
                                "type": "number",
                                "description": (
                                    "Optional amount to close. If not provided, closes the entire position. "
                                    "If provided, must not exceed the current position size. Will be "
                                    "automatically formatted to match asset's decimal precision."
                                ),
                            },
                        },
                        "required": ["symbol"],
                    },
                ),
            ]

        @self.mcp.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            handler = self._tool_handlers.get(name)
            if handler is None:
                error = {"success": False, "error": f"Unknown tool: {name}"}
                return [TextContent(type="text", text=json.dumps(error, indent=2))]

            arguments = arguments or {}
            tool_args = {
                key: arguments[key]
                for key in self._tool_arguments.get(name, [])
                if key in arguments
            }

            try:
                result = await handler(**tool_args)
            except Exception as exc:  # pragma: no cover - delegated to formatter
                error_result = format_error_response(exc)
                return [
                    TextContent(type="text", text=json.dumps(error_result, indent=2))
                ]

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def run(self):
        """Start the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.mcp.run(
                read_stream,
                write_stream,
                self.mcp.create_initialization_options(),
            )
