"""Audit Logger persisting immutable, timestamped event records."""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from src.core.database import get_db_connection
from src.audit.models import AuditLogEntry

class AuditLogger:
    @staticmethod
    def log(
        agent_id: str,
        customer_id: str,
        action_type: str,
        payload_summary: str,
        rules_evaluated: List[Dict[str, Any]],
        decision: str,
        reason: str,
        execution_status: str,
        db_path: Optional[str] = None
    ) -> AuditLogEntry:
        """
        Record an immutable gatekeeper decision in the audit log with UTC timestamp.
        """
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        audit_id = f"aud-amz-{uuid.uuid4().hex[:10]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        rules_json = json.dumps(rules_evaluated)

        cursor.execute("""
        INSERT INTO audit_logs (
            audit_id, timestamp, agent_id, customer_id, action_type,
            payload_summary, rules_evaluated, decision, reason, execution_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            audit_id,
            now_iso,
            agent_id,
            customer_id,
            action_type,
            payload_summary,
            rules_json,
            decision,
            reason,
            execution_status
        ))
        conn.commit()
        conn.close()

        return AuditLogEntry(
            audit_id=audit_id,
            timestamp=now_iso,
            agent_id=agent_id,
            customer_id=customer_id,
            action_type=action_type,
            payload_summary=payload_summary,
            rules_evaluated=rules_evaluated,
            decision=decision,
            reason=reason,
            execution_status=execution_status
        )

    @staticmethod
    def get_log(audit_id: str, db_path: Optional[str] = None) -> Optional[AuditLogEntry]:
        """Fetch audit log by ID."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs WHERE audit_id = ?", (audit_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return AuditLogEntry(
            audit_id=row["audit_id"],
            timestamp=row["timestamp"],
            agent_id=row["agent_id"],
            customer_id=row["customer_id"],
            action_type=row["action_type"],
            payload_summary=row["payload_summary"],
            rules_evaluated=json.loads(row["rules_evaluated"]),
            decision=row["decision"],
            reason=row["reason"],
            execution_status=row["execution_status"]
        )

    @staticmethod
    def query_logs(
        customer_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        decision: Optional[str] = None,
        limit: int = 50,
        db_path: Optional[str] = None
    ) -> List[AuditLogEntry]:
        """Query audit log entries."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM audit_logs WHERE 1=1"
        params: List[Any] = []

        if customer_id:
            query += " AND customer_id = ?"
            params.append(customer_id)
        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)
        if decision:
            query += " AND decision = ?"
            params.append(decision)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        conn.close()

        return [
            AuditLogEntry(
                audit_id=r["audit_id"],
                timestamp=r["timestamp"],
                agent_id=r["agent_id"],
                customer_id=r["customer_id"],
                action_type=r["action_type"],
                payload_summary=r["payload_summary"],
                rules_evaluated=json.loads(r["rules_evaluated"]),
                decision=r["decision"],
                reason=r["reason"],
                execution_status=r["execution_status"]
            )
            for r in rows
        ]
