"""Input validation and error handling for MCP tools."""

from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class OrderSideValidator(BaseModel):
    """Validator for order side parameter."""
    
    side: Literal["buy", "sell"] = Field(
        description="Order side - 'buy' or 'sell'"
    )
    
    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        """Validate and normalize side parameter."""
        normalized = v.lower().strip()
        if normalized not in ["buy", "sell"]:
            raise ValueError(
                f"Invalid side '{v}'. Must be 'buy' or 'sell' (case-insensitive)"
            )
        return normalized


class OrderTypeValidator(BaseModel):
    """Validator for order type parameter."""
    
    order_type: Literal["market", "limit"] = Field(
        default="market",
        description="Order type - 'market' or 'limit'"
    )
    
    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        """Validate and normalize order type parameter."""
        normalized = v.lower().strip()
        if normalized not in ["market", "limit"]:
            raise ValueError(
                f"Invalid order_type '{v}'. Must be 'market' or 'limit' (case-insensitive)"
            )
        return normalized


class SpotOrderParams(BaseModel):
    """Validation model for spot order parameters."""
    
    symbol: str = Field(
        min_length=1,
        max_length=20,
        description="Spot asset symbol (e.g., 'PURR', 'HYPE')"
    )
    side: str = Field(
        description="Order side - 'buy' or 'sell'"
    )
    size: float = Field(
        gt=0,
        description="Quantity to trade (must be positive)"
    )
    price: Optional[float] = Field(
        default=None,
        gt=0,
        description="Limit price (must be positive if provided)"
    )
    order_type: str = Field(
        default="market",
        description="Order type - 'market' or 'limit'"
    )
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol format."""
        v = v.strip().upper()
        if not v:
            raise ValueError("Symbol cannot be empty")
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                f"Invalid symbol '{v}'. Symbol must contain only alphanumeric characters, hyphens, or underscores"
            )
        return v
    
    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        """Validate and normalize side parameter."""
        normalized = v.lower().strip()
        if normalized not in ["buy", "sell"]:
            raise ValueError(
                f"Invalid side '{v}'. Must be 'buy' or 'sell' (case-insensitive)"
            )
        return normalized
    
    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        """Validate and normalize order type parameter."""
        normalized = v.lower().strip()
        if normalized not in ["market", "limit"]:
            raise ValueError(
                f"Invalid order_type '{v}'. Must be 'market' or 'limit' (case-insensitive)"
            )
        return normalized
    
    @model_validator(mode="after")
    def validate_limit_order_price(self):
        """Validate that limit orders have a price."""
        if self.order_type == "limit" and self.price is None:
            raise ValueError(
                "Price is required for limit orders. Either provide a price or use order_type='market'"
            )
        return self


class PerpOrderParams(BaseModel):
    """Validation model for perpetual order parameters."""
    
    symbol: str = Field(
        min_length=1,
        max_length=20,
        description="Perpetual contract symbol (e.g., 'BTC', 'ETH', 'SOL')"
    )
    side: str = Field(
        description="Order side - 'buy' or 'sell'"
    )
    size: float = Field(
        gt=0,
        description="Position size (must be positive)"
    )
    leverage: int = Field(
        ge=1,
        le=100,
        description="Leverage multiplier (1-100)"
    )
    price: Optional[float] = Field(
        default=None,
        gt=0,
        description="Limit price (must be positive if provided)"
    )
    order_type: str = Field(
        default="market",
        description="Order type - 'market' or 'limit'"
    )
    reduce_only: bool = Field(
        default=False,
        description="If true, order can only reduce existing position"
    )
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol format."""
        v = v.strip().upper()
        if not v:
            raise ValueError("Symbol cannot be empty")
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                f"Invalid symbol '{v}'. Symbol must contain only alphanumeric characters, hyphens, or underscores"
            )
        return v
    
    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        """Validate and normalize side parameter."""
        normalized = v.lower().strip()
        if normalized not in ["buy", "sell"]:
            raise ValueError(
                f"Invalid side '{v}'. Must be 'buy' or 'sell' (case-insensitive)"
            )
        return normalized
    
    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        """Validate and normalize order type parameter."""
        normalized = v.lower().strip()
        if normalized not in ["market", "limit"]:
            raise ValueError(
                f"Invalid order_type '{v}'. Must be 'market' or 'limit' (case-insensitive)"
            )
        return normalized
    
    @model_validator(mode="after")
    def validate_limit_order_price(self):
        """Validate that limit orders have a price."""
        if self.order_type == "limit" and self.price is None:
            raise ValueError(
                "Price is required for limit orders. Either provide a price or use order_type='market'"
            )
        return self


class CancelOrderParams(BaseModel):
    """Validation model for cancel order parameters."""
    
    symbol: str = Field(
        min_length=1,
        max_length=20,
        description="Asset symbol"
    )
    order_id: int = Field(
        ge=0,
        description="Order ID to cancel (must be non-negative)"
    )
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol format."""
        v = v.strip().upper()
        if not v:
            raise ValueError("Symbol cannot be empty")
        return v


class ClosePositionParams(BaseModel):
    """Validation model for close position parameters."""
    
    symbol: str = Field(
        min_length=1,
        max_length=20,
        description="Perpetual contract symbol"
    )
    size: Optional[float] = Field(
        default=None,
        gt=0,
        description="Amount to close (must be positive if provided)"
    )
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol format."""
        v = v.strip().upper()
        if not v:
            raise ValueError("Symbol cannot be empty")
        return v


class MarketDataParams(BaseModel):
    """Validation model for market data query parameters."""
    
    symbol: str = Field(
        min_length=1,
        max_length=20,
        description="Asset symbol to query"
    )
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol format."""
        v = v.strip().upper()
        if not v:
            raise ValueError("Symbol cannot be empty")
        return v


class WalletAddressParams(BaseModel):
    """Validation model for wallet address parameters."""
    
    user_address: Optional[str] = Field(
        default=None,
        description="Ethereum wallet address (0x...)"
    )
    
    @field_validator("user_address")
    @classmethod
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate Ethereum address format."""
        if v is None:
            return None
        
        v = v.strip()
        
        if not v.startswith("0x"):
            raise ValueError(
                f"Invalid wallet address '{v}'. Address must start with '0x'"
            )
        
        if len(v) != 42:
            raise ValueError(
                f"Invalid wallet address length. Expected 42 characters (including '0x'), got {len(v)}"
            )
        
        # Validate hex format
        try:
            int(v, 16)
        except ValueError as e:
            raise ValueError(
                f"Invalid wallet address format. Must be a valid hexadecimal string: {e}"
            ) from e
        
        return v
