"""Main MCP server implementation."""

from typing import Optional


class HyperliquidMCPServer:
    """Main MCP server class for Hyperliquid integration."""

    def __init__(
        self,
        testnet: bool = True,
        wallet_address: Optional[str] = None,
        private_key: Optional[str] = None,
    ):
        """
        Initialize the Hyperliquid MCP server.

        Args:
            testnet: Whether to use testnet (default: True)
            wallet_address: Wallet address (defaults to address derived from private key)
            private_key: Private key for signing transactions (required)
        """
        if private_key is None:
            raise ValueError("Private key is required")

        self.testnet = testnet
        self.private_key = private_key
        self.wallet_address = wallet_address
        # TODO: Derive wallet address from private key if not provided

    async def run(self):
        """Start the MCP server."""
        # TODO: Implement server startup logic
        pass
