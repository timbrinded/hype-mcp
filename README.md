# Hype MCP

A Model Context Protocol (MCP) server that integrates with the Hyperliquid decentralized exchange. This server enables AI agents to discover and interact with Hyperliquid's trading functionality through well-documented endpoints.

## Features

- **Query market data and account information** - Access real-time prices, positions, balances, and order status
- **Execute spot and perpetual trades** - Place market and limit orders with automatic precision handling
- **Automatic decimal precision handling** - No need to understand Hyperliquid's complex decimal rules
- **Support for testnet and mainnet** - Test safely before trading with real funds
- **Comprehensive tool documentation** - Every tool includes detailed descriptions, parameters, and examples

## Installation

### For End Users

Run directly with `uvx` (no installation needed):

```bash
uvx hype-mcp
```

The first time you run this command, `uvx` will automatically download and install all dependencies. Subsequent runs will be instant.

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

### MCP Settings

Configure the server in your MCP client settings (e.g., Claude Desktop, Cline):

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

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HYPERLIQUID_PRIVATE_KEY` | Yes | - | Your Ethereum private key for signing transactions (starts with 0x) |
| `HYPERLIQUID_WALLET_ADDRESS` | No | Derived from private key | Your wallet address (starts with 0x) |
| `HYPERLIQUID_TESTNET` | No | `true` | Set to `"true"` for testnet, `"false"` for mainnet |

**Security Note**: Always start with testnet (`HYPERLIQUID_TESTNET="true"`) to test your setup before using real funds on mainnet.

## Available Tools

### Info Endpoint Tools (Read-Only)

#### `get_account_state`

Get your account state including positions, balances, and margin.

**Parameters:**
- `user_address` (optional): Wallet address to query. Defaults to your configured wallet.

**Example:**
```
Get my account state
```

**Returns:**
- `assetPositions`: List of open positions
- `crossMarginSummary`: Total account value and leverage
- `marginSummary`: Per-asset margin details
- `withdrawable`: Available balance for withdrawal

---

#### `get_open_orders`

Get all your open orders across all assets.

**Parameters:**
- `user_address` (optional): Wallet address to query. Defaults to your configured wallet.

**Example:**
```
Show me my open orders
```

**Returns:**
List of orders with:
- `oid`: Order ID
- `coin`: Asset symbol
- `side`: "B" (buy) or "A" (sell)
- `sz`: Order size
- `px`: Limit price
- `timestamp`: Order creation time

---

#### `get_market_data`

Get current market data for a specific asset.

**Parameters:**
- `symbol` (required): Asset symbol (e.g., "BTC", "ETH", "PURR")

**Example:**
```
What's the current price of BTC?
```

**Returns:**
- `markPx`: Current mark price
- `midPx`: Mid price from orderbook
- `prevDayPx`: Price 24 hours ago
- `dayNtlVlm`: 24-hour volume
- `funding`: Funding rate (perps only)
- `openInterest`: Open interest (perps only)

---

#### `get_all_assets`

Get metadata for all available assets on Hyperliquid.

**Example:**
```
List all available assets
```

**Returns:**
- `perps`: List of perpetual contracts with leverage limits
- `spot`: List of spot assets

---

### Exchange Endpoint Tools (Trading)

#### `place_spot_order`

Place a spot market order with automatic decimal precision handling.

**Parameters:**
- `symbol` (required): Spot asset symbol (e.g., "PURR", "HYPE")
- `side` (required): "buy" or "sell"
- `size` (required): Quantity to trade (e.g., 1000)
- `price` (optional): Limit price (required for limit orders)
- `order_type` (optional): "market" (default) or "limit"

**Examples:**
```
Buy 1000 PURR at market price

Sell 500 HYPE at limit price 0.05
```

---

#### `place_perp_order`

Place a perpetual futures order with automatic decimal precision handling.

**Parameters:**
- `symbol` (required): Perpetual symbol (e.g., "BTC", "ETH", "SOL")
- `side` (required): "buy" (long) or "sell" (short)
- `size` (required): Position size (e.g., 0.1 for 0.1 BTC)
- `leverage` (required): Leverage multiplier (e.g., 5 for 5x)
- `price` (optional): Limit price (required for limit orders)
- `order_type` (optional): "market" (default) or "limit"
- `reduce_only` (optional): If true, can only reduce existing position

**Examples:**
```
Buy 0.1 BTC with 3x leverage at market price

Sell 1 ETH with 5x leverage at limit price 3500

Close 10 SOL with reduce_only order
```

---

#### `cancel_order`

Cancel a specific open order.

**Parameters:**
- `symbol` (required): Asset symbol
- `order_id` (required): Order ID to cancel

**Example:**
```
Cancel order 123456789 for BTC
```

---

#### `cancel_all_orders`

Cancel all open orders, optionally filtered by symbol.

**Parameters:**
- `symbol` (optional): If provided, only cancel orders for this symbol

**Examples:**
```
Cancel all my BTC orders

Cancel all my orders
```

---

#### `close_position`

Close a perpetual position (full or partial).

**Parameters:**
- `symbol` (required): Perpetual symbol
- `size` (optional): Amount to close. If not provided, closes entire position.

**Examples:**
```
Close my entire BTC position

Close 0.5 ETH from my position
```

---

## Common Trading Scenarios

### Scenario 1: Check Account and Place Market Order

```
1. "What's my account state?"
2. "What's the current price of BTC?"
3. "Buy 0.1 BTC with 3x leverage at market price"
```

### Scenario 2: Place Limit Order and Monitor

```
1. "What's the current price of ETH?"
2. "Buy 1 ETH with 5x leverage at limit price 3500"
3. "Show me my open orders"
```

### Scenario 3: Close Position

```
1. "What positions do I have open?"
2. "Close my entire SOL position"
```

### Scenario 4: Spot Trading

```
1. "List all spot assets"
2. "What's the price of PURR?"
3. "Buy 1000 PURR at market price"
```

## Decimal Precision Handling

Hyperliquid has strict decimal precision rules that vary by asset. This MCP server handles all precision automatically, so you don't need to worry about the details.

### How It Works

**Size Precision:**
- Each asset has a `szDecimals` value (e.g., 3 for BTC means 0.001 is the minimum size increment)
- The server automatically rounds your size to the correct precision
- Example: If you request 0.12345 BTC and `szDecimals=3`, it becomes 0.123

**Price Precision:**
- Prices must have at most 5 significant figures
- Prices cannot exceed `MAX_DECIMALS - szDecimals` decimal places
- Integer prices are always allowed
- The server validates and formats prices automatically

**What This Means for You:**
- Just use normal decimal numbers (e.g., 0.1, 1000, 3500.50)
- The server handles all formatting and validation
- If there's a precision error, you'll get a clear error message

## Troubleshooting

### "Private key is required"

**Problem:** The server cannot start without a private key.

**Solution:** Add `HYPERLIQUID_PRIVATE_KEY` to your MCP configuration:
```json
"env": {
  "HYPERLIQUID_PRIVATE_KEY": "0x..."
}
```

### "Asset not found"

**Problem:** The symbol you're trying to trade doesn't exist.

**Solution:** 
1. Use `get_all_assets` to see available assets
2. Check that the symbol is spelled correctly (case-sensitive)
3. Verify you're using the right symbol (e.g., "BTC" not "BITCOIN")

### "Leverage exceeds maximum"

**Problem:** You're requesting more leverage than the asset allows.

**Solution:**
1. Use `get_all_assets` to check the `maxLeverage` for your asset
2. Reduce your leverage to the maximum allowed
3. Example: If BTC has `maxLeverage: 50`, you can't use 100x

### "Invalid size precision"

**Problem:** Your size has too many decimal places for the asset.

**Solution:** This should be handled automatically, but if you see this error:
1. Use `get_all_assets` to check the asset's `szDecimals`
2. Round your size to fewer decimal places
3. Example: If `szDecimals=2`, use 1.23 instead of 1.234

### "Order rejected by Hyperliquid"

**Problem:** The exchange rejected your order.

**Common causes:**
- Insufficient balance
- Invalid price (too far from market)
- Market is paused
- Position limits exceeded

**Solution:** Check the error message for specific details and adjust your order accordingly.

### Connection Issues

**Problem:** Cannot connect to Hyperliquid API.

**Solution:**
1. Check your internet connection
2. Verify you're using the correct network (testnet vs mainnet)
3. Try again in a few moments (may be temporary API issue)

### Testing on Testnet

**Always test on testnet first!**

1. Set `HYPERLIQUID_TESTNET="true"` in your configuration
2. Get testnet funds from the Hyperliquid Discord
3. Test all your trading strategies
4. Only switch to mainnet when you're confident

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_tools.py

# Run with verbose output
uv run pytest -v
```

### Code Quality

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type checking
uv run mypy src/
```

### Project Structure

```
hype-mcp/
├── src/hype_mcp/
│   ├── __init__.py
│   ├── __main__.py          # Entry point
│   ├── server.py            # MCP server setup
│   ├── client_manager.py    # Hyperliquid client management
│   ├── decimal_manager.py   # Decimal precision handling
│   ├── config.py            # Configuration
│   ├── errors.py            # Error handling
│   ├── models.py            # Data models
│   ├── validation.py        # Input validation
│   └── tools/
│       ├── info_tools.py    # Read-only tools
│       └── exchange_tools.py # Trading tools
├── tests/
├── pyproject.toml
└── README.md
```

## Requirements

- Python >= 3.10
- Private key for transaction signing
- Wallet address (optional, derived from private key if not provided)

## Security Best Practices

1. **Never share your private key** - Keep it secure and never commit it to version control
2. **Use testnet first** - Always test with testnet before using real funds
3. **Start small** - Begin with small position sizes to verify everything works
4. **Monitor your positions** - Regularly check your account state and open orders
5. **Use reduce_only** - When closing positions, use `reduce_only=true` to prevent accidentally opening opposite positions

## License

MIT
