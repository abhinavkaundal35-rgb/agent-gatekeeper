"""Tests for Agent Identity & Access Management (IAM) - Requirement 1."""
from src.iam.service import IAMService
from src.iam.models import AgentStatus, StandardScopes

def test_agent_registration(test_db):
    """Test registering a new AI agent generates token and sets status to ACTIVE."""
    agent = IAMService.register_agent(
        name="AmazonGroceryAssistant",
        customer_id="cust-amz-001",
        scopes=[StandardScopes.ORDERS_BUY, StandardScopes.ORDERS_VIEW],
        db_path=test_db
    )
    assert agent.agent_id.startswith("agent-amz-")
    assert agent.status == AgentStatus.ACTIVE
    assert agent.api_token.startswith("amz_gatekeeper_")
    assert StandardScopes.ORDERS_BUY in agent.scopes
    assert agent.revoked_at is None

def test_agent_revocation(test_db):
    """Test revoking an active agent immediately updates status and sets timestamp."""
    agent = IAMService.register_agent(
        name="AutoDealShopper",
        customer_id="cust-amz-001",
        scopes=[StandardScopes.ORDERS_BUY],
        db_path=test_db
    )
    assert agent.status == AgentStatus.ACTIVE

    revoked = IAMService.revoke_agent(agent.agent_id, db_path=test_db)
    assert revoked is not None
    assert revoked.status == AgentStatus.REVOKED
    assert revoked.revoked_at is not None

    # Verification should now fail
    is_valid, reason, _ = IAMService.verify_agent_credentials(
        agent_id=agent.agent_id,
        token=agent.api_token,
        db_path=test_db
    )
    assert not is_valid
    assert "revoked" in reason.lower()

def test_agent_scope_verification(test_db):
    """Test verifying permissions scopes (e.g. read-only vs buy)."""
    agent = IAMService.register_agent(
        name="ReadOnlyMonitor",
        customer_id="cust-amz-001",
        scopes=[StandardScopes.ORDERS_VIEW],
        db_path=test_db
    )

    # Allowed scope
    valid, _, _ = IAMService.verify_agent_credentials(
        agent.agent_id, agent.api_token, required_scope=StandardScopes.ORDERS_VIEW, db_path=test_db
    )
    assert valid

    # Disallowed scope
    valid, reason, _ = IAMService.verify_agent_credentials(
        agent.agent_id, agent.api_token, required_scope=StandardScopes.ORDERS_BUY, db_path=test_db
    )
    assert not valid
    assert "scope" in reason.lower()
