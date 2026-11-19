"""IAM Service handling Agent registration, revocation, and token verification."""
import secrets
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from src.core.database import get_db_connection
from src.iam.models import AgentStatus, AgentResponse

class IAMService:
    @staticmethod
    def register_agent(
        name: str,
        customer_id: str,
        scopes: List[str],
        db_path: Optional[str] = None
    ) -> AgentResponse:
        """Register a new customer AI agent and generate an API key."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        agent_id = f"agent-amz-{uuid.uuid4().hex[:8]}"
        api_token = f"amz_gatekeeper_{secrets.token_urlsafe(24)}"
        now_iso = datetime.now(timezone.utc).isoformat()
        scopes_json = json.dumps(scopes)

        cursor.execute("""
        INSERT INTO agents (agent_id, customer_id, name, status, api_token, scopes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            agent_id,
            customer_id,
            name,
            AgentStatus.ACTIVE.value,
            api_token,
            scopes_json,
            now_iso
        ))
        conn.commit()
        conn.close()

        return AgentResponse(
            agent_id=agent_id,
            customer_id=customer_id,
            name=name,
            status=AgentStatus.ACTIVE,
            api_token=api_token,
            scopes=scopes,
            created_at=now_iso,
            revoked_at=None
        )

    @staticmethod
    def revoke_agent(agent_id: str, db_path: Optional[str] = None) -> Optional[AgentResponse]:
        """Revoke an active agent, immediately disallowing any future requests."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        now_iso = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
        UPDATE agents
        SET status = ?, revoked_at = ?
        WHERE agent_id = ?
        """, (AgentStatus.REVOKED.value, now_iso, agent_id))
        conn.commit()

        cursor.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,))
        updated = cursor.fetchone()
        conn.close()

        return AgentResponse(
            agent_id=updated["agent_id"],
            customer_id=updated["customer_id"],
            name=updated["name"],
            status=AgentStatus(updated["status"]),
            api_token=updated["api_token"],
            scopes=json.loads(updated["scopes"]),
            created_at=updated["created_at"],
            revoked_at=updated["revoked_at"]
        )

    @staticmethod
    def get_agent(agent_id: str, db_path: Optional[str] = None) -> Optional[AgentResponse]:
        """Fetch agent details by ID."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return AgentResponse(
            agent_id=row["agent_id"],
            customer_id=row["customer_id"],
            name=row["name"],
            status=AgentStatus(row["status"]),
            api_token=row["api_token"],
            scopes=json.loads(row["scopes"]),
            created_at=row["created_at"],
            revoked_at=row["revoked_at"]
        )

    @staticmethod
    def list_agents(customer_id: Optional[str] = None, db_path: Optional[str] = None) -> List[AgentResponse]:
        """List registered agents, optionally filtered by customer."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        if customer_id:
            cursor.execute("SELECT * FROM agents WHERE customer_id = ? ORDER BY created_at DESC", (customer_id,))
        else:
            cursor.execute("SELECT * FROM agents ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()

        return [
            AgentResponse(
                agent_id=row["agent_id"],
                customer_id=row["customer_id"],
                name=row["name"],
                status=AgentStatus(row["status"]),
                api_token=row["api_token"],
                scopes=json.loads(row["scopes"]),
                created_at=row["created_at"],
                revoked_at=row["revoked_at"]
            )
            for row in rows
        ]

    @staticmethod
    def verify_agent_credentials(
        agent_id: str,
        token: Optional[str],
        required_scope: Optional[str] = None,
        db_path: Optional[str] = None
    ) -> Tuple[bool, str, Optional[AgentResponse]]:
        """
        Validate agent existence, token match, active status, and required scope.
        Returns: (is_valid, failure_reason, agent_object)
        """
        agent = IAMService.get_agent(agent_id, db_path=db_path)
        if not agent:
            return False, "Agent not found in registry.", None

        if token and agent.api_token != token:
            return False, "Invalid API token provided.", agent

        if agent.status == AgentStatus.REVOKED:
            return False, "Agent has been revoked and is inactive.", agent

        if required_scope and required_scope not in agent.scopes:
            return False, f"Agent lacks required permission scope '{required_scope}'.", agent

        return True, "Valid", agent
