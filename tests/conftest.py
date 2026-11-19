"""Pytest fixtures and test environment setup."""
import os
import pytest
from starlette.testclient import TestClient
from src.core.database import init_db
from src.iam.service import IAMService
from src.iam.models import StandardScopes
from src.main import app

@pytest.fixture
def test_db(tmp_path):
    """Provides an isolated test database for each test function."""
    db_file = str(tmp_path / "test_gatekeeper.db")
    init_db(db_path=db_file)
    return db_file

@pytest.fixture
def client(test_db, monkeypatch):
    """Provides a TestClient wired to the isolated test database."""
    # Monkeypatch default DB_PATH in modules to point to the test database
    import src.core.database
    import src.approvals.spending_tracker
    import src.iam.service
    import src.store.service
    import src.approvals.approval_service
    import src.audit.logger
    import src.gatekeeper.evaluator

    monkeypatch.setattr(src.core.database, "DB_PATH", test_db)
    monkeypatch.setattr(src.approvals.spending_tracker, "DB_PATH", test_db)
    monkeypatch.setattr(src.iam.service, "get_db_connection", lambda p=None: src.core.database.get_db_connection(p or test_db))
    monkeypatch.setattr(src.store.service, "get_db_connection", lambda p=None: src.core.database.get_db_connection(p or test_db))
    monkeypatch.setattr(src.approvals.approval_service, "get_db_connection", lambda p=None: src.core.database.get_db_connection(p or test_db))
    monkeypatch.setattr(src.audit.logger, "get_db_connection", lambda p=None: src.core.database.get_db_connection(p or test_db))

    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def active_agent(test_db):
    """Fixture providing an active registered agent."""
    return IAMService.register_agent(
        name="SmartBuyerBot",
        customer_id="cust-amz-001",
        scopes=StandardScopes.ALL_SCOPES,
        db_path=test_db
    )

@pytest.fixture
def revoked_agent(test_db):
    """Fixture providing an initially active, then revoked agent."""
    agent = IAMService.register_agent(
        name="SuspiciousBot",
        customer_id="cust-amz-001",
        scopes=StandardScopes.ALL_SCOPES,
        db_path=test_db
    )
    revoked = IAMService.revoke_agent(agent.agent_id, db_path=test_db)
    return revoked
