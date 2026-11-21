"""Comprehensive End-to-End Automated Test Cases for Agent Gatekeeper."""
from src.gatekeeper.evaluator import GatekeeperPipeline, GatekeeperEvaluationRequest
from src.approvals.approval_service import ApprovalService, CustomerApprovalDecision
from src.store.service import StoreService
from src.store.models import CartItem, IndianAddress, ProductCategory

# ==========================================
# 1. ALLOW SCENARIOS
# ==========================================

def test_verdict_allow_routine_order(test_db, active_agent):
    """
    Scenario: Active AI agent orders grocery items totaling ₹1,040 (< ₹2,000 auto limit)
    to the customer's verified PIN code (560001).
    Expected Decision: ALLOW. Order placed immediately.
    """
    req = GatekeeperEvaluationRequest(
        agent_id=active_agent.agent_id,
        api_token=active_agent.api_token,
        customer_id=active_agent.customer_id,
        action_type="PURCHASE_ORDER",
        payload={
            "items": [
                {
                    "item_id": "AMZ-GROC-01",
                    "name": "Tata Tea Gold 1kg",
                    "category": "Grocery",
                    "unit_price_inr": 520.0,
                    "quantity": 2
                }
            ],
            "shipping_address": {
                "address_line": "Flat 402, Green Palms, MG Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001"
            }
        }
    )

    response = GatekeeperPipeline.evaluate(req, db_path=test_db)
    assert response.decision == "ALLOW"
    assert response.approval_id is None
    assert response.execution_result is not None
    assert response.execution_result["status"] == "PLACED"
    assert response.execution_result["total_amount"] == 1040.0

def test_verdict_allow_view_orders(test_db, active_agent):
    """
    Scenario: Active agent requests to view past customer order history.
    Expected Decision: ALLOW.
    """
    req = GatekeeperEvaluationRequest(
        agent_id=active_agent.agent_id,
        api_token=active_agent.api_token,
        customer_id=active_agent.customer_id,
        action_type="VIEW_ORDERS",
        payload={}
    )

    response = GatekeeperPipeline.evaluate(req, db_path=test_db)
    assert response.decision == "ALLOW"
    assert "orders" in response.execution_result

def test_verdict_allow_routine_return(test_db, active_agent):
    """
    Scenario: Agent requests a return for a defective item within 2 days of delivery
    with refund amount under ₹1,000 threshold.
    Expected Decision: ALLOW. Return processed immediately.
    """
    # Pre-create delivered order
    order = StoreService.create_order(
        customer_id=active_agent.customer_id,
        agent_id=active_agent.agent_id,
        items=[
            CartItem(item_id="AMZ-FASH-01", name="Shirt", category=ProductCategory.FASHION, unit_price_inr=899.0, quantity=1)
        ],
        shipping_address=IndianAddress(
            address_line="Flat 402", city="Bengaluru", state="Karnataka", pincode="560001"
        ),
        db_path=test_db
    )

    req = GatekeeperEvaluationRequest(
        agent_id=active_agent.agent_id,
        api_token=active_agent.api_token,
        customer_id=active_agent.customer_id,
        action_type="RETURN_REQUEST",
        payload={
            "order_id": order.order_id,
            "item_id": "AMZ-FASH-01",
            "reason": "Size does not fit",
            "refund_amount": 899.0,
            "days_since_delivery": 2,
            "category": "Fashion"
        }
    )

    response = GatekeeperPipeline.evaluate(req, db_path=test_db)
    assert response.decision == "ALLOW"
    assert response.execution_result["status"] == "APPROVED"

# ==========================================
# 2. ASK CUSTOMER SCENARIOS
# ==========================================

def test_verdict_ask_customer_high_value_order(test_db, active_agent):
    """
    Scenario: AI agent orders Fire TV Stick 4K for ₹5,999 (> ₹5,000 threshold).
    Expected Decision: ASK CUSTOMER. Approval session token generated.
    """
    req = GatekeeperEvaluationRequest(
        agent_id=active_agent.agent_id,
        api_token=active_agent.api_token,
        customer_id=active_agent.customer_id,
        action_type="PURCHASE_ORDER",
        payload={
            "items": [
                {
                    "item_id": "AMZ-ELEC-07",
                    "name": "Fire TV Stick 4K with Alexa Voice Remote",
                    "category": "Electronics",
                    "unit_price_inr": 5999.0,
                    "quantity": 1
                }
            ],
            "shipping_address": {
                "address_line": "Flat 402, Green Palms, MG Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001"
            }
        }
    )

    response = GatekeeperPipeline.evaluate(req, db_path=test_db)
    assert response.decision == "ASK CUSTOMER"
    assert response.triggered_rule == "SEC-R07"
    assert response.approval_id is not None
    assert response.approval_id.startswith("app-amz-")
    assert "₹5,000" in response.reason

def test_verdict_ask_customer_unverified_shipping_address(test_db, active_agent):
    """
    Scenario: AI agent places an order below ₹2,000 (₹899), but to an unrecognized PIN code (400001).
    Expected Decision: ASK CUSTOMER.
    """
    req = GatekeeperEvaluationRequest(
        agent_id=active_agent.agent_id,
        api_token=active_agent.api_token,
        customer_id=active_agent.customer_id,
        action_type="PURCHASE_ORDER",
        payload={
            "items": [
                {
                    "item_id": "AMZ-FASH-01",
                    "name": "Cotton Casual Shirt",
                    "category": "Fashion",
                    "unit_price_inr": 899.0,
                    "quantity": 1
                }
            ],
            "shipping_address": {
                "address_line": "15 Nariman Point",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400001"  # Not in customer's verified PIN list
            }
        }
    )

    response = GatekeeperPipeline.evaluate(req, db_path=test_db)
    assert response.decision == "ASK CUSTOMER"
    assert response.triggered_rule == "SEC-R08"
    assert "PIN code" in response.reason

def test_verdict_ask_customer_high_value_refund(test_db, active_agent):
    """
    Scenario: Return request with refund amount ₹2,499 (> ₹2,000 threshold).
    Expected Decision: ASK CUSTOMER.
    """
    req = GatekeeperEvaluationRequest(
        agent_id=active_agent.agent_id,
        api_token=active_agent.api_token,
        customer_id=active_agent.customer_id,
        action_type="RETURN_REQUEST",
        payload={
            "order_id": "ord-amz-demo1",
            "item_id": "AMZ-ELEC-02",
            "reason": "Battery life issues",
            "refund_amount": 2499.0,
            "days_since_delivery": 3,
            "category": "Electronics"
        }
    )

    response = GatekeeperPipeline.evaluate(req, db_path=test_db)
    assert response.decision == "ASK CUSTOMER"
    assert response.triggered_rule == "SEC-R10"
    assert response.approval_id is not None

def test_verdict_ask_customer_restricted_category_luxury_order(test_db):
    """
    Scenario: agent-luxury-006 orders a Clara Silver Solitaire Ring for ₹1,899 (category: Jewelry).
    Even though ₹1,899 <= ₹5,000 allowance, the restricted category triggers Rule SEC-R09.
    Expected Decision: ASK CUSTOMER.
    """
    req = GatekeeperEvaluationRequest(
        agent_id="agent-luxury-006",
        api_token="amz_gatekeeper_token_luxury_006",
        customer_id="cust-amz-001",
        action_type="PURCHASE_ORDER",
        payload={
            "items": [
                {
                    "item_id": "AMZ-JEWL-02",
                    "name": "Clara 925 Sterling Silver Solitaire Ring",
                    "category": "Jewelry",
                    "unit_price_inr": 1899.0,
                    "quantity": 1
                }
            ],
            "shipping_address": {
                "address_line": "Flat 402, Green Palms, MG Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001"
            }
        }
    )

    response = GatekeeperPipeline.evaluate(req, db_path=test_db)
    assert response.decision == "ASK CUSTOMER"
    assert response.triggered_rule == "SEC-R09"
    assert response.approval_id is not None
    assert "restricted" in response.reason.lower() or "jewelry" in response.reason.lower()

# ==========================================
# 3. BLOCK SCENARIOS
# ==========================================

def test_verdict_block_revoked_agent(test_db, revoked_agent):
    """
    Scenario: Decommissioned / Revoked AI agent attempts to place an order.
    Expected Decision: BLOCK.
    """
    req = GatekeeperEvaluationRequest(
        agent_id=revoked_agent.agent_id,
        api_token=revoked_agent.api_token,
        customer_id=revoked_agent.customer_id,
        action_type="PURCHASE_ORDER",
        payload={
            "items": [
                {"item_id": "AMZ-GROC-01", "name": "Tea", "category": "Grocery", "unit_price_inr": 520.0, "quantity": 1}
            ],
            "shipping_address": {"address_line": "MG Road", "city": "Bengaluru", "state": "Karnataka", "pincode": "560001"}
        }
    )

    response = GatekeeperPipeline.evaluate(req, db_path=test_db)
    assert response.decision == "BLOCK"
    assert response.triggered_rule == "SEC-R01"
    assert "revoked" in response.reason.lower()

def test_verdict_block_exceeded_hard_spending_cap(test_db, active_agent):
    """
    Scenario: Agent attempts to purchase Bridal Necklace Set for ₹35,000 (> ₹25,000 hard limit).
    Expected Decision: BLOCK (SEC-R03 takes priority over ask-customer).
    """
    req = GatekeeperEvaluationRequest(
        agent_id=active_agent.agent_id,
        api_token=active_agent.api_token,
        customer_id=active_agent.customer_id,
        action_type="PURCHASE_ORDER",
        payload={
            "items": [
                {
                    "item_id": "AMZ-JEWL-04",
                    "name": "Tanishq 22K Gold & Diamond Bridal Necklace Set",
                    "category": "Jewelry",
                    "unit_price_inr": 35000.0,
                    "quantity": 1
                }
            ],
            "shipping_address": {
                "address_line": "Flat 402, Green Palms, MG Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001"
            }
        }
    )

    response = GatekeeperPipeline.evaluate(req, db_path=test_db)
    assert response.decision == "BLOCK"
    assert response.triggered_rule == "SEC-R03"
    assert "₹25,000" in response.reason

def test_verdict_block_expired_return_window(test_db, active_agent):
    """
    Scenario: Return requested 14 days after delivery (> 7 days Amazon India window).
    Expected Decision: BLOCK.
    """
    req = GatekeeperEvaluationRequest(
        agent_id=active_agent.agent_id,
        api_token=active_agent.api_token,
        customer_id=active_agent.customer_id,
        action_type="RETURN_REQUEST",
        payload={
            "order_id": "ord-amz-old",
            "item_id": "AMZ-ELEC-01",
            "reason": "Changed my mind",
            "refund_amount": 999.0,
            "days_since_delivery": 14,
            "category": "Electronics"
        }
    )

    response = GatekeeperPipeline.evaluate(req, db_path=test_db)
    assert response.decision == "BLOCK"
    assert response.triggered_rule == "SEC-R06"
    assert "7-day" in response.reason

def test_verdict_block_non_returnable_category(test_db, active_agent):
    """
    Scenario: Return requested on grocery items (perishable goods policy).
    Expected Decision: BLOCK.
    """
    req = GatekeeperEvaluationRequest(
        agent_id=active_agent.agent_id,
        api_token=active_agent.api_token,
        customer_id=active_agent.customer_id,
        action_type="RETURN_REQUEST",
        payload={
            "order_id": "ord-amz-groc",
            "item_id": "AMZ-GROC-01",
            "reason": "Do not need anymore",
            "refund_amount": 520.0,
            "days_since_delivery": 1,
            "category": "Grocery"
        }
    )

    response = GatekeeperPipeline.evaluate(req, db_path=test_db)
    assert response.decision == "BLOCK"
    assert response.triggered_rule == "SEC-R05"
    assert "non-returnable" in response.reason.lower()

# ==========================================
# 4. FULL HUMAN-IN-THE-LOOP APPROVAL FLOW
# ==========================================

def test_end_to_end_customer_approval_and_execution_flow(test_db, active_agent):
    """
    Scenario:
    1. Agent initiates order for ₹4,499.
    2. Gatekeeper returns ASK CUSTOMER with approval token.
    3. Customer signs off with APPROVED.
    4. Order is executed and recorded in database.
    """
    req = GatekeeperEvaluationRequest(
        agent_id=active_agent.agent_id,
        api_token=active_agent.api_token,
        customer_id=active_agent.customer_id,
        action_type="PURCHASE_ORDER",
        payload={
            "items": [
                {
                    "item_id": "AMZ-ELEC-07",
                    "name": "Fire TV Stick 4K",
                    "category": "Electronics",
                    "unit_price_inr": 5999.0,
                    "quantity": 1
                }
            ],
            "shipping_address": {
                "address_line": "Flat 402, MG Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001"
            }
        }
    )

    eval_res = GatekeeperPipeline.evaluate(req, db_path=test_db)
    assert eval_res.decision == "ASK CUSTOMER"
    appr_id = eval_res.approval_id
    assert appr_id is not None

    # Customer responds with APPROVED
    resolved = ApprovalService.resolve_approval(
        approval_id=appr_id,
        decision=CustomerApprovalDecision.APPROVED,
        db_path=test_db
    )
    assert resolved.status.value == "APPROVED"

    # Verify order execution
    items = [CartItem(**item) for item in req.payload["items"]]
    addr = IndianAddress(**req.payload["shipping_address"])
    order = StoreService.create_order(
        customer_id=req.customer_id,
        agent_id=req.agent_id,
        items=items,
        shipping_address=addr,
        db_path=test_db
    )
    assert order.status.value == "PLACED"
    assert order.total_amount == 5999.0
