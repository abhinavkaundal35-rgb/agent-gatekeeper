"""Tests for Spending Limits & Customer Approval - Requirement 5."""
from src.approvals.spending_tracker import SpendingTracker
from src.approvals.approval_service import (
    ApprovalService,
    ApprovalStatus,
    CustomerApprovalDecision
)
from src.store.service import StoreService
from src.store.models import CartItem, IndianAddress, ProductCategory

def test_daily_spending_calculation(test_db, active_agent):
    """Test accurate aggregation of customer's 24-hour spend in INR."""
    initial_spend = SpendingTracker.get_daily_spend(active_agent.customer_id, db_path=test_db)
    assert initial_spend == 0.0

    # Place an order
    address = IndianAddress(
        address_line="Flat 402, MG Road",
        city="Bengaluru",
        state="Karnataka",
        pincode="560001"
    )
    StoreService.create_order(
        customer_id=active_agent.customer_id,
        agent_id=active_agent.agent_id,
        items=[
            CartItem(item_id="AMZ-01", name="Item 1", category=ProductCategory.HOME, unit_price_inr=1500.0, quantity=1)
        ],
        shipping_address=address,
        db_path=test_db
    )

    updated_spend = SpendingTracker.get_daily_spend(active_agent.customer_id, db_path=test_db)
    assert updated_spend == 1500.0

def test_approval_lifecycle_approved(test_db, active_agent):
    """Test approval state transition from PENDING to APPROVED."""
    payload = {
        "items": [{"item_id": "AMZ-ELEC-01", "name": "Kindle", "category": "Electronics", "unit_price_inr": 8999.0, "quantity": 1}],
        "shipping_address": {"address_line": "12, MG Road", "city": "Bengaluru", "state": "Karnataka", "pincode": "560001"}
    }
    appr = ApprovalService.create_approval_request(
        agent_id=active_agent.agent_id,
        customer_id=active_agent.customer_id,
        action_type="PURCHASE_ORDER",
        payload=payload,
        challenge_message="Purchase ₹8,999 exceeds auto-limit",
        db_path=test_db
    )
    assert appr.status == ApprovalStatus.PENDING

    # Customer approves
    resolved = ApprovalService.resolve_approval(
        approval_id=appr.approval_id,
        decision=CustomerApprovalDecision.APPROVED,
        db_path=test_db
    )
    assert resolved.status == ApprovalStatus.APPROVED
    assert resolved.resolved_at is not None

def test_approval_lifecycle_rejected(test_db, active_agent):
    """Test approval state transition from PENDING to REJECTED."""
    payload = {"order_id": "ord-01", "item_id": "it-01"}
    appr = ApprovalService.create_approval_request(
        agent_id=active_agent.agent_id,
        customer_id=active_agent.customer_id,
        action_type="RETURN_REQUEST",
        payload=payload,
        challenge_message="Sensitive return",
        db_path=test_db
    )
    assert appr.status == ApprovalStatus.PENDING

    # Customer rejects
    resolved = ApprovalService.resolve_approval(
        approval_id=appr.approval_id,
        decision=CustomerApprovalDecision.REJECTED,
        db_path=test_db
    )
    assert resolved.status == ApprovalStatus.REJECTED
