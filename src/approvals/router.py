"""Approvals and Spending Limits Router."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from src.approvals.approval_service import (
    ApprovalService,
    ApprovalResponse,
    CustomerDecisionRequest,
    ApprovalStatus
)
from src.approvals.spending_tracker import SpendingTracker
from src.store.service import StoreService
from src.store.models import CartItem, IndianAddress

router = APIRouter(prefix="/api/v1", tags=["Approvals & Spending"])

@router.get("/spending/{customer_id}")
def get_customer_spending(customer_id: str):
    """Retrieve rolling 24-hour spend statistics for a customer."""
    return SpendingTracker.get_spending_summary(customer_id)

@router.get("/approvals", response_model=List[ApprovalResponse])
def list_approvals(
    customer_id: Optional[str] = Query(None, description="Customer ID filter"),
    status: Optional[ApprovalStatus] = Query(None, description="Approval status filter")
):
    """List customer approval sessions."""
    return ApprovalService.list_approvals(customer_id=customer_id, status=status)

@router.get("/approvals/{approval_id}", response_model=ApprovalResponse)
def get_approval(approval_id: str):
    """Retrieve a specific approval session by ID."""
    appr = ApprovalService.get_approval(approval_id)
    if not appr:
        raise HTTPException(status_code=404, detail="Approval request not found.")
    return appr

@router.post("/approvals/{approval_id}/respond", response_model=ApprovalResponse)
def respond_to_approval(approval_id: str, req: CustomerDecisionRequest):
    """
    Simulate customer response (APPROVED or REJECTED).
    If approved, automatically executes the underlying held e-commerce action.
    """
    existing = ApprovalService.get_approval(approval_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Approval request not found.")

    if existing.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Approval request is already resolved with status '{existing.status.value}'."
        )

    resolved = ApprovalService.resolve_approval(approval_id, req.decision)

    # If customer approved, execute held store action
    if req.decision == req.decision.APPROVED:
        payload = existing.payload
        if existing.action_type == "PURCHASE_ORDER":
            items = [CartItem(**item) for item in payload.get("items", [])]
            address = IndianAddress(**payload["shipping_address"])
            StoreService.create_order(
                customer_id=existing.customer_id,
                agent_id=existing.agent_id,
                items=items,
                shipping_address=address
            )
        elif existing.action_type == "RETURN_REQUEST":
            StoreService.process_return(
                customer_id=existing.customer_id,
                agent_id=existing.agent_id,
                order_id=payload["order_id"],
                item_id=payload["item_id"],
                reason=payload["reason"],
                refund_amount=payload.get("refund_amount")
            )

    return resolved
