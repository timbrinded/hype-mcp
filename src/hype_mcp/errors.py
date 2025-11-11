"""Custom exceptions and error handling for the MCP server."""

from typing import Any, Optional


class HyperliquidMCPError(Exception):
    """Base exception for Hyperliquid MCP server errors."""
    
    def __init__(
        self,
        message: str,
        error_type: str = "HyperliquidMCPError",
        details: Optional[dict[str, Any]] = None
    ):
        """
        Initialize error.
        
        Args:
            message: Human-readable error message
            error_type: Type/category of error
            details: Additional context about the error
        """
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.details = details or {}
    
    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary format for API responses."""
        result = {
            "success": False,
            "error": self.message,
            "error_type": self.error_type,
        }
        if self.details:
            result["details"] = self.details
        return result


class ValidationError(HyperliquidMCPError):
    """Error raised when input validation fails."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        constraint: Optional[str] = None
    ):
        """
        Initialize validation error.
        
        Args:
            message: Human-readable error message
            field: Name of the field that failed validation
            value: The invalid value
            constraint: Description of the constraint that was violated
        """
        details = {}
        if field is not None:
            details["field"] = field
        if value is not None:
            details["value"] = value
        if constraint is not None:
            details["constraint"] = constraint
        
        super().__init__(
            message=message,
            error_type="ValidationError",
            details=details
        )


class APIError(HyperliquidMCPError):
    """Error raised when Hyperliquid API request fails."""
    
    def __init__(
        self,
        message: str,
        api_response: Optional[dict[str, Any]] = None,
        status_code: Optional[int] = None
    ):
        """
        Initialize API error.
        
        Args:
            message: Human-readable error message
            api_response: Raw API response if available
            status_code: HTTP status code if available
        """
        details = {}
        if api_response is not None:
            details["api_response"] = api_response
        if status_code is not None:
            details["status_code"] = status_code
        
        super().__init__(
            message=message,
            error_type="APIError",
            details=details
        )


class PrecisionError(HyperliquidMCPError):
    """Error raised when decimal precision validation fails."""
    
    def __init__(
        self,
        message: str,
        symbol: str,
        value: float,
        constraint: str
    ):
        """
        Initialize precision error.
        
        Args:
            message: Human-readable error message
            symbol: Asset symbol
            value: The value that violated precision constraints
            constraint: Description of the precision constraint
        """
        super().__init__(
            message=message,
            error_type="PrecisionError",
            details={
                "symbol": symbol,
                "value": value,
                "constraint": constraint
            }
        )


class AssetNotFoundError(HyperliquidMCPError):
    """Error raised when an asset symbol is not found."""
    
    def __init__(self, symbol: str):
        """
        Initialize asset not found error.
        
        Args:
            symbol: The asset symbol that was not found
        """
        super().__init__(
            message=f"Asset '{symbol}' not found on Hyperliquid. Please verify the symbol is correct and the asset is available for trading.",
            error_type="AssetNotFoundError",
            details={"symbol": symbol}
        )


class InsufficientBalanceError(HyperliquidMCPError):
    """Error raised when account has insufficient balance for an operation."""
    
    def __init__(
        self,
        message: str,
        required: Optional[float] = None,
        available: Optional[float] = None
    ):
        """
        Initialize insufficient balance error.
        
        Args:
            message: Human-readable error message
            required: Required balance for the operation
            available: Available balance in the account
        """
        details = {}
        if required is not None:
            details["required"] = required
        if available is not None:
            details["available"] = available
        
        super().__init__(
            message=message,
            error_type="InsufficientBalanceError",
            details=details
        )


class PositionNotFoundError(HyperliquidMCPError):
    """Error raised when a position is not found."""
    
    def __init__(self, symbol: str):
        """
        Initialize position not found error.
        
        Args:
            symbol: The asset symbol for which no position was found
        """
        super().__init__(
            message=f"No open position found for {symbol}. You can only close positions that exist.",
            error_type="PositionNotFoundError",
            details={"symbol": symbol}
        )


class LeverageExceededError(HyperliquidMCPError):
    """Error raised when requested leverage exceeds maximum allowed."""
    
    def __init__(
        self,
        symbol: str,
        requested_leverage: int,
        max_leverage: int
    ):
        """
        Initialize leverage exceeded error.
        
        Args:
            symbol: Asset symbol
            requested_leverage: The leverage that was requested
            max_leverage: Maximum allowed leverage for the asset
        """
        super().__init__(
            message=f"Leverage {requested_leverage}x exceeds maximum allowed leverage {max_leverage}x for {symbol}. Please reduce leverage to {max_leverage}x or lower.",
            error_type="LeverageExceededError",
            details={
                "symbol": symbol,
                "requested_leverage": requested_leverage,
                "max_leverage": max_leverage
            }
        )


class OrderNotFoundError(HyperliquidMCPError):
    """Error raised when an order is not found."""
    
    def __init__(self, symbol: str, order_id: int):
        """
        Initialize order not found error.
        
        Args:
            symbol: Asset symbol
            order_id: The order ID that was not found
        """
        super().__init__(
            message=f"Order {order_id} not found for {symbol}. The order may have already been filled or cancelled.",
            error_type="OrderNotFoundError",
            details={
                "symbol": symbol,
                "order_id": order_id
            }
        )


def format_error_response(error: Exception) -> dict[str, Any]:
    """
    Format any exception into a standardized error response.
    
    Args:
        error: The exception to format
        
    Returns:
        Dictionary with standardized error format
    """
    if isinstance(error, HyperliquidMCPError):
        return error.to_dict()
    
    # Handle Pydantic validation errors
    if hasattr(error, "errors"):
        # Pydantic ValidationError
        errors = error.errors()
        if errors:
            first_error = errors[0]
            field = ".".join(str(loc) for loc in first_error.get("loc", []))
            message = first_error.get("msg", str(error))
            
            return {
                "success": False,
                "error": f"Validation error for field '{field}': {message}",
                "error_type": "ValidationError",
                "details": {
                    "field": field,
                    "validation_errors": errors
                }
            }
    
    # Generic exception
    return {
        "success": False,
        "error": str(error),
        "error_type": type(error).__name__
    }
