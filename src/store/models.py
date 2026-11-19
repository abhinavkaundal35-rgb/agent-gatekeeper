"""Amazon India E-Commerce Domain Models."""
import re
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class ProductCategory(str, Enum):
    ELECTRONICS = "Electronics"
    GROCERY = "Grocery"
    JEWELRY = "Jewelry"
    FASHION = "Fashion"
    HOME = "Home"
    GIFT_CARDS = "Gift Cards"
    PERSONAL_HYGIENE = "Personal Hygiene"
    BOOKS = "Books"
    BEAUTY = "Beauty"

class OrderStatus(str, Enum):
    PLACED = "PLACED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    RETURNED = "RETURNED"

class RefundMethod(str, Enum):
    AMAZON_PAY_BALANCE = "AMAZON_PAY_BALANCE"
    ORIGINAL_PAYMENT = "ORIGINAL_PAYMENT"

class IndianAddress(BaseModel):
    address_line: str
    landmark: Optional[str] = None
    city: str
    state: str
    pincode: str = Field(..., description="6-digit Indian PIN code")

    @field_validator("pincode")
    @classmethod
    def validate_pincode(cls, v: str) -> str:
        v_clean = v.strip()
        if not re.match(r"^[1-9][0-9]{5}$", v_clean):
            raise ValueError(f"Invalid Indian PIN code format: '{v}'. Must be 6 digits and not start with 0.")
        return v_clean

class CartItem(BaseModel):
    item_id: str
    name: str
    category: ProductCategory
    unit_price_inr: float = Field(..., gt=0)
    quantity: int = Field(default=1, gt=0)

    @property
    def total_price(self) -> float:
        return self.unit_price_inr * self.quantity

class OrderCreateRequest(BaseModel):
    items: List[CartItem] = Field(..., min_length=1)
    shipping_address: IndianAddress

class OrderResponse(BaseModel):
    order_id: str
    customer_id: str
    agent_id: str
    total_amount: float
    currency: str = "INR"
    status: OrderStatus
    shipping_address: IndianAddress
    items: List[CartItem]
    placed_at: str
    delivered_at: Optional[str] = None

class ReturnCreateRequest(BaseModel):
    order_id: str
    item_id: str
    reason: str
    refund_method: RefundMethod = Field(default=RefundMethod.AMAZON_PAY_BALANCE)
    days_since_delivery: Optional[int] = Field(
        default=2,
        description="Simulated or calculated days elapsed since delivery",
        ge=0
    )

class ReturnResponse(BaseModel):
    return_id: str
    order_id: str
    customer_id: str
    agent_id: str
    item_id: str
    reason: str
    refund_amount: float
    refund_method: RefundMethod
    status: str
    created_at: str
    message: str
