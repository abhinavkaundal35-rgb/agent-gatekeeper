"""Agent Gatekeeper - Live Academic Demonstration Script.

Simulates customer AI agent interactions with the Gatekeeper and showcases
all three governance verdicts: ALLOW, ASK CUSTOMER, and BLOCK,
along with the human-in-the-loop approval and immutable audit trail.
"""
import sys
import json
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.database import init_db
from src.iam.service import IAMService
from src.iam.models import StandardScopes
from src.gatekeeper.evaluator import GatekeeperPipeline, GatekeeperEvaluationRequest
from src.approvals.approval_service import ApprovalService, CustomerApprovalDecision
from src.audit.logger import AuditLogger

SEPARATOR = "=" * 80
SUB_SEP = "-" * 80

def print_header(title: str):
    print("\n" + SEPARATOR)
    print(f"  {title}")
    print(SEPARATOR)

def print_result(res):
    print(f"  >>> GATEKEEPER DECISION: [{res.decision}]")
    print(f"  Reason: {res.reason}")
    if res.triggered_rule:
        print(f"  Triggered Rule: {res.triggered_rule}")
    if res.approval_id:
        print(f"  Approval Challenge ID: {res.approval_id}")
    if res.execution_result:
        print(f"  Execution Output: {json.dumps(res.execution_result, indent=4)}")
    print(f"  Audit Record ID: {res.audit_id}")

def main():
    print_header("AGENT GATEKEEPER - LIVE DEMONSTRATION")
    print("Assigned Domain: Online Store (Amazon India Reference)")
    print("Governance Decision Engine: ALLOW | ASK CUSTOMER | BLOCK\n")

    # Step 0: Initialize Clean SQLite Database
    demo_db = "data/demo_gatekeeper.db"
    init_db(db_path=demo_db)
    customer_id = "cust-amz-001"
    print("[INIT] Initialized database and seeded verified customer 'Aarav Sharma' (PIN: 560001).")

    # Step 1: Agent Registration (Role 1: IAM)
    print_header("STEP 1: Customer AI Agent Registration (Role 1: IAM)")
    agent = IAMService.register_agent(
        name="AmazonSmartShopperBot",
        customer_id=customer_id,
        scopes=StandardScopes.ALL_SCOPES,
        db_path=demo_db
    )
    print(f"Agent Registered Successfully:")
    print(f"  Agent ID:   {agent.agent_id}")
    print(f"  Name:       {agent.name}")
    print(f"  Status:     {agent.status.value}")
    print(f"  Token:      {agent.api_token[:25]}...")
    print(f"  Scopes:     {agent.scopes}")

    # Scenario 1: ALLOW - Routine Order Below INR 2,000
    print_header("SCENARIO 1: Routine Grocery Order below INR 2,000 threshold (Decision: ALLOW)")
    req1 = GatekeeperEvaluationRequest(
        agent_id=agent.agent_id,
        api_token=agent.api_token,
        customer_id=customer_id,
        action_type="PURCHASE_ORDER",
        payload={
            "items": [
                {"item_id": "AMZ-GROC-01", "name": "Tata Tea Gold 1kg", "category": "Grocery", "unit_price_inr": 520.0, "quantity": 1},
                {"item_id": "AMZ-GROC-02", "name": "Aashirvaad Atta 10kg", "category": "Grocery", "unit_price_inr": 495.0, "quantity": 1}
            ],
            "shipping_address": {
                "address_line": "Flat 402, Green Palms, MG Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001"
            }
        }
    )
    res1 = GatekeeperPipeline.evaluate(req1, db_path=demo_db)
    print_result(res1)

    # Scenario 2: ASK CUSTOMER - High-Value Order (> INR 2,000)
    print_header("SCENARIO 2: High-Value Electronics Order of INR 4,499 (Decision: ASK CUSTOMER)")
    req2 = GatekeeperEvaluationRequest(
        agent_id=agent.agent_id,
        api_token=agent.api_token,
        customer_id=customer_id,
        action_type="PURCHASE_ORDER",
        payload={
            "items": [
                {"item_id": "AMZ-ELEC-01", "name": "Echo Dot (5th Gen) Smart Speaker", "category": "Electronics", "unit_price_inr": 4499.0, "quantity": 1}
            ],
            "shipping_address": {
                "address_line": "Flat 402, Green Palms, MG Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001"
            }
        }
    )
    res2 = GatekeeperPipeline.evaluate(req2, db_path=demo_db)
    print_result(res2)

    # Scenario 3: Human Customer Reviews and Approves
    print_header("SCENARIO 3: Human Customer Resolves Approval Challenge (Role 4: Approvals)")
    print(f"Customer notified on Amazon Mobile App: '{res2.reason}'")
    print("Customer enters OTP / clicks 'Approve Order'...")
    resolved = ApprovalService.resolve_approval(
        approval_id=res2.approval_id,
        decision=CustomerApprovalDecision.APPROVED,
        db_path=demo_db
    )
    print(f"Approval Challenge Status: {resolved.status.value}")
    print(f"Resolved at (UTC): {resolved.resolved_at}")
    print(f"Decision by: {resolved.decision_by}")

    # Scenario 4: ASK CUSTOMER - Unverified Delivery PIN Code
    print_header("SCENARIO 4: Delivery to Unverified PIN Code (Decision: ASK CUSTOMER)")
    req4 = GatekeeperEvaluationRequest(
        agent_id=agent.agent_id,
        api_token=agent.api_token,
        customer_id=customer_id,
        action_type="PURCHASE_ORDER",
        payload={
            "items": [
                {"item_id": "AMZ-FASH-01", "name": "Cotton Casual Shirt", "category": "Fashion", "unit_price_inr": 899.0, "quantity": 1}
            ],
            "shipping_address": {
                "address_line": "15 Marine Drive",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400001"  # Not in customer's verified list
            }
        }
    )
    res4 = GatekeeperPipeline.evaluate(req4, db_path=demo_db)
    print_result(res4)

    # Scenario 5: BLOCK - Decommissioned / Revoked Agent
    print_header("SCENARIO 5: Action by Revoked AI Agent (Decision: BLOCK)")
    revoked_agent = IAMService.register_agent(
        name="OldDealFinderBot",
        customer_id=customer_id,
        scopes=StandardScopes.ALL_SCOPES,
        db_path=demo_db
    )
    IAMService.revoke_agent(revoked_agent.agent_id, db_path=demo_db)
    print(f"Agent '{revoked_agent.agent_id}' has been REVOKED by customer.")

    req5 = GatekeeperEvaluationRequest(
        agent_id=revoked_agent.agent_id,
        api_token=revoked_agent.api_token,
        customer_id=customer_id,
        action_type="PURCHASE_ORDER",
        payload={
            "items": [
                {"item_id": "AMZ-GROC-01", "name": "Tata Tea", "category": "Grocery", "unit_price_inr": 520.0, "quantity": 1}
            ],
            "shipping_address": {"address_line": "MG Road", "city": "Bengaluru", "state": "Karnataka", "pincode": "560001"}
        }
    )
    res5 = GatekeeperPipeline.evaluate(req5, db_path=demo_db)
    print_result(res5)

    # Scenario 6: BLOCK - Transaction Exceeding Hard Cap (INR 18,500 > INR 15,000)
    print_header("SCENARIO 6: Order Exceeds Hard Spending Cap of INR 15,000 (Decision: BLOCK)")
    req6 = GatekeeperEvaluationRequest(
        agent_id=agent.agent_id,
        api_token=agent.api_token,
        customer_id=customer_id,
        action_type="PURCHASE_ORDER",
        payload={
            "items": [
                {"item_id": "AMZ-JEWL-01", "name": "Kalyan Jewellers Gold Pendant", "category": "Jewelry", "unit_price_inr": 18500.0, "quantity": 1}
            ],
            "shipping_address": {
                "address_line": "Flat 402, Green Palms, MG Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001"
            }
        }
    )
    res6 = GatekeeperPipeline.evaluate(req6, db_path=demo_db)
    print_result(res6)

    # Scenario 7: BLOCK - Expired Return Window (> 7 days)
    print_header("SCENARIO 7: Return Request after 14 Days Expired Window (Decision: BLOCK)")
    req7 = GatekeeperEvaluationRequest(
        agent_id=agent.agent_id,
        api_token=agent.api_token,
        customer_id=customer_id,
        action_type="RETURN_REQUEST",
        payload={
            "order_id": "ord-amz-past-01",
            "item_id": "AMZ-ELEC-01",
            "reason": "Unwanted gift",
            "refund_amount": 4499.0,
            "days_since_delivery": 14,
            "category": "Electronics"
        }
    )
    res7 = GatekeeperPipeline.evaluate(req7, db_path=demo_db)
    print_result(res7)

    # Scenario 8: Audit Log Inspection
    print_header("SCENARIO 8: Immutable Audit Trail Inspection (Role 5: Audit)")
    logs = AuditLogger.query_logs(customer_id=customer_id, limit=5, db_path=demo_db)
    print(f"Total Audit Entries in Log: {len(logs)}\n")
    for idx, log in enumerate(logs, 1):
        print(f"[{idx}] Timestamp (UTC): {log.timestamp}")
        print(f"    Action: {log.action_type} | Decision: {log.decision} | Status: {log.execution_status}")
        print(f"    Payload Summary: {log.payload_summary}")
        print(f"    Reason: {log.reason}")
        print(f"    Audit Record ID: {log.audit_id}\n")

    print_header("DEMONSTRATION COMPLETED SUCCESSFULLY")

if __name__ == "__main__":
    main()
