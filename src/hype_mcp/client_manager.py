"""Hyperliquid client manager for Info and Exchange endpoints."""

from typing import Optional

from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange


class HyperliquidClientManager:
    """Manages Hyperliquid SDK clients for Info and Exchange endpoints."""

    def __init__(
        self,
        testnet: bool,
        wallet_address: str,
        private_key: str,
        account_address: Optional[str] = None,
    ):
        """
        Initialize Hyperliquid clients.

        Args:
            testnet: Whether to use testnet environment
            wallet_address: Wallet address for the account
            private_key: Private key for signing transactions
            account_address: Optional account address (defaults to wallet_address)
        """
        self.testnet = testnet
        self.wallet_address = wallet_address
        self.private_key = private_key
        self.account_address = account_address or wallet_address

        # Select API URL based on testnet flag
        self.base_url = self._get_base_url()

        # Initialize clients
        self._info_client: Optional[Info] = None
        self._exchange_client: Optional[Exchange] = None

    def _get_base_url(self) -> str:
        """
        Get the appropriate API URL based on testnet flag.

        Returns:
            Base URL for the Hyperliquid API
        """
        if self.testnet:
            return "https://api.hyperliquid-testnet.xyz"
        return "https://api.hyperliquid.xyz"

    @property
    def info(self) -> Info:
        """
        Get Info endpoint client for read-only operations.

        Returns:
            Initialized Info client
        """
        if self._info_client is None:
            self._info_client = Info(base_url=self.base_url, skip_ws=True)
        return self._info_client

    @property
    def exchange(self) -> Exchange:
        """
        Get Exchange endpoint client for trade execution.

        Returns:
            Initialized Exchange client
        """
        if self._exchange_client is None:
            # Create LocalAccount from private key
            wallet = Account.from_key(self.private_key)
            self._exchange_client = Exchange(
                wallet=wallet,
                base_url=self.base_url,
                account_address=self.account_address,
            )
        return self._exchange_client

    async def validate_connection(self) -> bool:
        """
        Validate connection to Hyperliquid API.

        Returns:
            True if connection is valid, False otherwise

        Raises:
            Exception: If connection validation fails
        """
        try:
            # Test Info endpoint by fetching all mids
            result = self.info.all_mids()
            return result is not None
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to Hyperliquid API at {self.base_url}: {str(e)}"
            ) from e
