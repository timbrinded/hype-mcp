# Test Infrastructure

This directory contains the test suite for the Hyperliquid MCP server.

## Overview

The test infrastructure is built using:
- **pytest**: Python testing framework
- **pytest-asyncio**: Support for async test functions
- **unittest.mock**: Mocking SDK clients for unit tests

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and pytest configuration
├── test_config.py           # Configuration and initialization tests
├── test_decimal_manager.py  # Decimal precision manager tests
├── test_integration.py      # Integration tests against testnet
├── test_tools.py            # MCP tool tests
├── test_validation.py       # Input validation and error handling tests
└── README.md               # This file
```

## Running Tests

### Run all unit tests (excluding integration tests)
```bash
uv run pytest tests/ -v -k "not integration"
```

### Run specific test file
```bash
uv run pytest tests/test_config.py -v
```

### Run specific test class or function
```bash
uv run pytest tests/test_config.py::TestHyperliquidConfig::test_from_env_with_all_values -v
```

### Run integration tests (requires real API credentials)
```bash
# Set environment variables first
export HYPERLIQUID_PRIVATE_KEY="0x..."
export HYPERLIQUID_WALLET_ADDRESS="0x..."
export HYPERLIQUID_TESTNET="true"

# Run integration tests
uv run pytest tests/ -v -m integration
```

### Run with coverage (if pytest-cov is installed)
```bash
uv run pytest tests/ --cov=src/hype_mcp --cov-report=term-missing
```

## Test Fixtures

The `conftest.py` file provides shared fixtures for all tests:

### Configuration Fixtures
- `test_private_key`: Test private key for testing
- `test_wallet_address`: Test wallet address
- `test_config`: Complete test configuration
- `testnet_env_vars`: Environment variables for testnet
- `mainnet_env_vars`: Environment variables for mainnet

### Mock Fixtures
- `mock_info_client`: Mocked Hyperliquid Info client
- `mock_exchange_client`: Mocked Hyperliquid Exchange client
- `mock_client_manager`: Mocked HyperliquidClientManager
- `mock_decimal_manager`: Mocked DecimalPrecisionManager

### Integration Test Fixtures
- `integration_config`: Real configuration from environment
- `integration_client_manager`: Real client manager for API testing
- `integration_decimal_manager`: Real decimal manager for API testing

### Utility Fixtures
- `clean_env`: Automatically cleans environment variables before each test

## Writing Tests

### Unit Tests

Unit tests use mocked SDK clients and don't make real API calls:

```python
import pytest

@pytest.mark.asyncio
async def test_my_function(mock_client_manager):
    """Test my function with mocked clients."""
    result = await my_function(mock_client_manager)
    assert result["success"] is True
```

### Integration Tests

Integration tests connect to the real Hyperliquid testnet API:

```python
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_api(integration_client_manager):
    """Test against real API."""
    result = await integration_client_manager.info.all_mids()
    assert result is not None
```

Integration tests are automatically marked and can be run separately:
```bash
# Run only integration tests
uv run pytest -m integration

# Skip integration tests
uv run pytest -m "not integration"
```

## Test Configuration

The `pytest.ini` file configures pytest behavior:

- **asyncio_mode**: Set to `auto` for automatic async test detection
- **testpaths**: Tests are discovered in the `tests/` directory
- **markers**: Custom markers for integration and slow tests
- **addopts**: Default options for verbose output and strict markers

## Best Practices

1. **Use fixtures**: Leverage shared fixtures from `conftest.py` instead of creating new ones
2. **Mock external dependencies**: Unit tests should not make real API calls
3. **Test one thing**: Each test should verify a single behavior
4. **Descriptive names**: Use clear test names that describe what is being tested
5. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification
6. **Clean up**: Use fixtures with cleanup to ensure tests don't affect each other
7. **Mark integration tests**: Use `@pytest.mark.integration` for tests requiring real API

## Continuous Integration

For CI/CD pipelines, run unit tests only (skip integration tests):

```bash
uv run pytest tests/ -v -k "not integration" --tb=short
```

Integration tests should be run separately with proper credentials configured.

## Troubleshooting

### Tests fail with "event loop is closed"
- Ensure `pytest-asyncio` is installed: `uv add --dev pytest-asyncio`
- Check that `pytest.ini` has `asyncio_mode = auto`

### Integration tests are skipped
- Set required environment variables:
  - `HYPERLIQUID_PRIVATE_KEY`
  - `HYPERLIQUID_WALLET_ADDRESS` (optional, derived from private key)
  - `HYPERLIQUID_TESTNET` (default: "true")

### Mock fixtures not working
- Ensure you're importing fixtures from `conftest.py`
- Check that fixture names match exactly
- Verify fixture scope is appropriate for your test

## Adding New Tests

When adding new tests:

1. Choose the appropriate test file based on what you're testing
2. Use existing fixtures from `conftest.py` when possible
3. Add new fixtures to `conftest.py` if they'll be reused
4. Mark integration tests with `@pytest.mark.integration`
5. Add docstrings to explain what the test verifies
6. Follow existing naming conventions

Example:

```python
import pytest

@pytest.mark.asyncio
async def test_new_feature(mock_client_manager):
    """Test that new feature works correctly."""
    # Arrange
    expected_result = {"success": True}
    
    # Act
    result = await new_feature(mock_client_manager)
    
    # Assert
    assert result == expected_result
```
