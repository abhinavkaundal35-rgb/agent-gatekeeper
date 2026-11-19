"""Customer Approval Service managing human-in-the-loop state machine."""
import json
import uuid
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from src.core.database import get_db_connection

class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

class CustomerApprovalDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class ApprovalResponse(BaseModel):
    approval_id: str
    agent_id: str
    customer_id: str
    action_type: str
    payload: Dict[str, Any]
    challenge_message: str
    status: ApprovalStatus
    created_at: str
    resolved_at: Optional[str] = None
    decision_by: Optional[str] = None

class CustomerDecisionRequest(BaseModel):
    decision: CustomerApprovalDecision
    decision_note: Optional[str] = None

class ApprovalService:
    @staticmethod
    def create_approval_request(
        agent_id: str,
        customer_id: str,
        action_type: str,
        payload: Dict[str, Any],
        challenge_message: str,
        db_path: Optional[str] = None
    ) -> ApprovalResponse:
        """Create a new pending customer approval challenge."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        approval_id = f"app-amz-{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        payload_json = json.dumps(payload)

        cursor.execute("""
        INSERT INTO approval_requests (
            approval_id, agent_id, customer_id, action_type, payload,
            challenge_message, status, created_at, resolved_at, decision_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
        """, (
            approval_id,
            agent_id,
            customer_id,
            action_type,
            payload_json,
            challenge_message,
            ApprovalStatus.PENDING.value,
            now_iso
        ))
        conn.commit()
        conn.close()

        return ApprovalResponse(
            approval_id=approval_id,
            agent_id=agent_id,
            customer_id=customer_id,
            action_type=action_type,
            payload=payload,
            challenge_message=challenge_message,
            status=ApprovalStatus.PENDING,
            created_at=now_iso,
            resolved_at=None,
            decision_by=None
        )

    @staticmethod
    def get_approval(approval_id: str, db_path: Optional[str] = None) -> Optional[ApprovalResponse]:
        """Fetch approval request by ID."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM approval_requests WHERE approval_id = ?", (approval_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return ApprovalResponse(
            approval_id=row["approval_id"],
            agent_id=row["agent_id"],
            customer_id=row["customer_id"],
            action_type=row["action_type"],
            payload=json.loads(row["payload"]),
            challenge_message=row["challenge_message"],
            status=ApprovalStatus(row["status"]),
            created_at=row["created_at"],
            resolved_at=row["resolved_at"],
            decision_by=row["decision_by"]
        )

    @staticmethod
    def resolve_approval(
        approval_id: str,
        decision: CustomerApprovalDecision,
        decision_by: str = "CUSTOMER",
        db_path: Optional[str] = None
    ) -> Optional[ApprovalResponse]:
        """Resolve a pending customer approval request."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM approval_requests WHERE approval_id = ?", (approval_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        if row["status"] != ApprovalStatus.PENDING.value:
            conn.close()
            # Already resolved
            return ApprovalService.get_approval(approval_id, db_path=db_path)

        now_iso = datetime.now(timezone.utc).isoformat()
        new_status = ApprovalStatus.APPROVED.value if decision == CustomerApprovalDecision.APPROVED else ApprovalStatus.REJECTED.value

        cursor.execute("""
        UPDATE approval_requests
        SET status = ?, resolved_at = ?, decision_by = ?
        WHERE approval_id = ?
        """, (new_status, now_iso, decision_by, approval_id))
        conn.commit()
        conn.close()

        return ApprovalService.get_approval(approval_id, db_path=db_path)

    @staticmethod
    def list_approvals(
        customer_id: Optional[str] = None,
        status: Optional[ApprovalStatus] = None,
        db_path: Optional[str] = None
    ) -> List[ApprovalResponse]:
        """List approval requests."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM approval_requests WHERE 1=1"
        params: List[Any] = []

        if customer_id:
            query += " AND customer_id = ?"
            params.append(customer_id)
        if status:
            query += " AND status = ?"
            params.append(status.value)

        query += " ORDER BY created_at DESC"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        conn.close()

        return [
            ApprovalResponse(
                approval_id=r["approval_id"],
                agent_id=r["agent_id"],
                customer_id=r["customer_id"],
                action_type=r["action_type"],
                payload=json.loads(r["payload"]),
                challenge_message=r["challenge_message"],
                status=ApprovalStatus(r["status"]),
                created_at=r["created_at"],
                resolved_at=r["resolved_at"],
                decision_by=r["decision_by"]
            )
            for r in rows
        ]
