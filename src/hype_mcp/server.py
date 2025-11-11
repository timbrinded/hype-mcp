"""Main MCP server implementation."""

from .config import HyperliquidConfig


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

    async def run(self):
        """Start the MCP server."""
        # TODO: Implement server startup logic
        pass
