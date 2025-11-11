# Hype MCP

A Model Context Protocol (MCP) server that integrates with the Hyperliquid decentralized exchange. This server enables AI agents to discover and interact with Hyperliquid's trading functionality through well-documented endpoints.

## Features

- Query market data and account information (Info Endpoint)
- Execute spot and perpetual trades (Exchange Endpoint)
- Automatic decimal precision handling for different asset types
- Support for both testnet and mainnet environments
- Comprehensive tool documentation for AI agent discovery

## Installation

### For End Users

Run directly with `uvx` (no installation needed):

```bash
uvx hype-mcp
```

### For Development

```bash
# Clone the repository
git clone <repo-url>
cd hype-mcp

# Install dependencies
uv sync

# Run in development mode
uv run hype-mcp
```

## Configuration

Configure the server in your MCP settings:

```json
{
  "mcpServers": {
    "hyperliquid": {
      "command": "uvx",
      "args": ["hype-mcp"],
      "env": {
        "HYPERLIQUID_PRIVATE_KEY": "0x...",
        "HYPERLIQUID_WALLET_ADDRESS": "0x...",
        "HYPERLIQUID_TESTNET": "true"
      }
    }
  }
}
```

## Requirements

- Python >= 3.10
- Private key for transaction signing
- Wallet address (optional, derived from private key if not provided)

## Development

```bash
# Run tests
uv run pytest

# Format code
uv run ruff format .

# Lint code
uv run ruff check .
```

## License

MIT
