"""Input validation helpers."""

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


def _normalize_symbol(value: str, *, strict: bool = True) -> str:
    cleaned = value.strip().upper()
    if not cleaned:
        raise ValueError("Symbol cannot be empty")
    if strict and not cleaned.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Symbol must be alphanumeric (hyphen/underscore allowed)")
    return cleaned


def _normalize_side(value: str) -> str:
    normalized = value.lower().strip()
    if normalized not in {"buy", "sell"}:
        raise ValueError("Side must be 'buy' or 'sell'")
    return normalized


def _normalize_order_type(value: str) -> str:
    normalized = value.lower().strip()
    if normalized not in {"market", "limit"}:
        raise ValueError("order_type must be 'market' or 'limit'")
    return normalized


class OrderSideValidator(BaseModel):
    side: Literal["buy", "sell"] = Field(description="Order side")

    @field_validator("side", mode="before")
    @classmethod
    def validate_side(cls, value: str) -> str:
        return _normalize_side(value)


class OrderTypeValidator(BaseModel):
    order_type: Literal["market", "limit"] = Field(
        default="market", description="Order type"
    )

    @field_validator("order_type", mode="before")
    @classmethod
    def validate_order_type(cls, value: str) -> str:
        return _normalize_order_type(value)


class SpotOrderParams(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    side: Literal["buy", "sell"]
    size: float = Field(gt=0)
    price: Optional[float] = Field(default=None, gt=0)
    order_type: Literal["market", "limit"] = Field(default="market")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)

    @field_validator("side", mode="before")
    @classmethod
    def validate_side(cls, value: str) -> str:
        return _normalize_side(value)

    @field_validator("order_type", mode="before")
    @classmethod
    def validate_order_type(cls, value: str) -> str:
        return _normalize_order_type(value)

    @model_validator(mode="after")
    def validate_limit_order_price(self):
        if self.order_type == "limit" and self.price is None:
            raise ValueError("Price is required for limit orders")
        return self


class PerpOrderParams(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    side: Literal["buy", "sell"]
    size: float = Field(gt=0)
    leverage: int = Field(ge=1, le=100)
    price: Optional[float] = Field(default=None, gt=0)
    order_type: Literal["market", "limit"] = Field(default="market")
    reduce_only: bool = Field(default=False)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)

    @field_validator("side", mode="before")
    @classmethod
    def validate_side(cls, value: str) -> str:
        return _normalize_side(value)

    @field_validator("order_type", mode="before")
    @classmethod
    def validate_order_type(cls, value: str) -> str:
        return _normalize_order_type(value)

    @model_validator(mode="after")
    def validate_limit_order_price(self):
        if self.order_type == "limit" and self.price is None:
            raise ValueError("Price is required for limit orders")
        return self


class CancelOrderParams(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    order_id: int = Field(ge=0)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        return _normalize_symbol(value, strict=False)


class ClosePositionParams(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    size: Optional[float] = Field(default=None, gt=0)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        return _normalize_symbol(value, strict=False)


class MarketDataParams(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        return _normalize_symbol(value, strict=False)


class WalletAddressParams(BaseModel):
    user_address: Optional[str] = Field(default=None)

    @field_validator("user_address")
    @classmethod
    def validate_address(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        address = value.strip()
        if not address.startswith("0x"):
            raise ValueError("Wallet address must start with '0x'")
        if len(address) != 42:
            raise ValueError("Wallet address must be 42 characters long")
        try:
            int(address, 16)
        except ValueError as exc:
            raise ValueError("Wallet address must be hexadecimal") from exc
        return address
