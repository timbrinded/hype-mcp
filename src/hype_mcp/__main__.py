"""Entry point for the MCP server."""

import asyncio
import sys

from .config import load_config
from .server import HyperliquidMCPServer


def main():
    """Main entry point for the MCP server."""
    try:
        asyncio.run(async_main())
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


async def async_main():
    """Async main function."""
    config = load_config()

    server = HyperliquidMCPServer(config)

    await server.run()


if __name__ == "__main__":
    main()
