"""Tests for Audit Logging & Traceability - Requirement 6."""
from src.audit.logger import AuditLogger

def test_audit_log_entry_creation(test_db):
    """Test creating and retrieving timestamped immutable audit log records."""
    entry = AuditLogger.log(
        agent_id="agent-amz-001",
        customer_id="cust-amz-001",
        action_type="PURCHASE_ORDER",
        payload_summary="Purchase Kindle for ₹9,999",
        rules_evaluated=[{"rule_id": "SEC-R07", "matched": True}],
        decision="ASK CUSTOMER",
        reason="Order exceeds threshold",
        execution_status="HELD_FOR_APPROVAL",
        db_path=test_db
    )

    assert entry.audit_id.startswith("aud-amz-")
    assert entry.timestamp is not None
    assert entry.decision == "ASK CUSTOMER"
    assert entry.execution_status == "HELD_FOR_APPROVAL"

    # Query log
    fetched = AuditLogger.get_log(entry.audit_id, db_path=test_db)
    assert fetched is not None
    assert fetched.audit_id == entry.audit_id
    assert fetched.reason == "Order exceeds threshold"

    # List logs by customer
    logs = AuditLogger.query_logs(customer_id="cust-amz-001", db_path=test_db)
    assert len(logs) == 1
    assert logs[0].audit_id == entry.audit_id
