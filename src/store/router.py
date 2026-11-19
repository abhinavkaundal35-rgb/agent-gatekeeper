"""Store Router for orders, returns, and catalog."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Header
from src.store.models import (
    CartItem,
    OrderCreateRequest,
    OrderResponse,
    ReturnCreateRequest,
    ReturnResponse
)
from src.store.service import StoreService, SAMPLE_CATALOG

router = APIRouter(prefix="/api/v1/store", tags=["Amazon India Store"])

@router.get("/catalog", response_model=List[CartItem])
def get_catalog():
    """Retrieve Amazon India sample product catalog."""
    return SAMPLE_CATALOG

@router.get("/orders", response_model=List[OrderResponse])
def list_orders(
    customer_id: Optional[str] = Query(None, description="Customer ID filter"),
    agent_id: Optional[str] = Query(None, description="Agent ID filter")
):
    """View order history."""
    return StoreService.list_orders(customer_id=customer_id, agent_id=agent_id)

@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: str):
    """Retrieve a specific order by ID."""
    order = StoreService.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    return order

@router.get("/returns", response_model=List[ReturnResponse])
def list_returns(customer_id: Optional[str] = Query(None, description="Customer ID filter")):
    """List customer return requests."""
    return StoreService.list_returns(customer_id=customer_id)
