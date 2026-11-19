"""Audit Logging Models."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class AuditLogEntry(BaseModel):
    audit_id: str
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp")
    agent_id: str
    customer_id: str
    action_type: str
    payload_summary: str
    rules_evaluated: List[Dict[str, Any]]
    decision: str  # ALLOW, ASK CUSTOMER, BLOCK
    reason: str
    execution_status: str  # EXECUTED, HELD_FOR_APPROVAL, BLOCKED
