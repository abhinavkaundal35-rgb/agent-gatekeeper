"""Audit Logging Router."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from src.audit.models import AuditLogEntry
from src.audit.logger import AuditLogger

router = APIRouter(prefix="/api/v1/audit", tags=["Audit & Governance"])

@router.get("", response_model=List[AuditLogEntry])
def query_audit_logs(
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    decision: Optional[str] = Query(None, description="Filter by decision (ALLOW, ASK CUSTOMER, BLOCK)"),
    limit: int = Query(50, ge=1, le=200, description="Max logs to return")
):
    """Retrieve immutable audit logs."""
    return AuditLogger.query_logs(
        customer_id=customer_id,
        agent_id=agent_id,
        decision=decision,
        limit=limit
    )

@router.get("/{audit_id}", response_model=AuditLogEntry)
def get_audit_log(audit_id: str):
    """Retrieve a single audit log entry by ID."""
    entry = AuditLogger.get_log(audit_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Audit log entry not found.")
    return entry
