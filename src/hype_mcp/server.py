"""Main MCP server implementation."""

from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .client_manager import HyperliquidClientManager
from .config import HyperliquidConfig
from .tools import (
    get_account_state,
    get_all_assets,
    get_market_data,
    get_open_orders,
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

        # Initialize MCP server
        self.mcp = Server("hyperliquid-mcp-server")

        # Register tools
        self._register_tools()

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
            ]

        @self.mcp.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls."""
            try:
                if name == "get_account_state":
                    result = await get_account_state(
                        self.client_manager,
                        user_address=arguments.get("user_address"),
                    )
                elif name == "get_open_orders":
                    result = await get_open_orders(
                        self.client_manager,
                        user_address=arguments.get("user_address"),
                    )
                elif name == "get_market_data":
                    if "symbol" not in arguments:
                        return [
                            TextContent(
                                type="text",
                                text='{"success": false, "error": "symbol parameter is required"}',
                            )
                        ]
                    result = await get_market_data(
                        self.client_manager,
                        symbol=arguments["symbol"],
                    )
                elif name == "get_all_assets":
                    result = await get_all_assets(self.client_manager)
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f'{{"success": false, "error": "Unknown tool: {name}"}}',
                        )
                    ]

                # Format result as JSON string
                import json
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            except Exception as e:
                import json
                error_result = {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
                return [TextContent(type="text", text=json.dumps(error_result, indent=2))]

    async def run(self):
        """Start the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.mcp.run(
                read_stream,
                write_stream,
                self.mcp.create_initialization_options(),
            )
