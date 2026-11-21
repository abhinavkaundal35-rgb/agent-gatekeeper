"""Database connection and table initialization for Agent Gatekeeper."""
import sqlite3
import json
from datetime import datetime, timezone
from typing import Optional
from src.core.config import DB_PATH

def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Return a configured SQLite database connection."""
    target_path = db_path or DB_PATH
    conn = sqlite3.connect(target_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: Optional[str] = None) -> None:
    """Initialize SQLite database tables and default seed data."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 1. Customers Table (verified Indian addresses & PIN codes)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        verified_pincodes TEXT NOT NULL,
        default_address TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    # 2. Agents Table (Role 1: IAM)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agents (
        agent_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        name TEXT NOT NULL,
        status TEXT NOT NULL, -- ACTIVE, REVOKED
        api_token TEXT NOT NULL,
        scopes TEXT NOT NULL, -- JSON array of granted scopes
        created_at TEXT NOT NULL,
        revoked_at TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
    );
    """)

    # 3. Orders Table (Role 2: Amazon India Store)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        agent_id TEXT NOT NULL,
        total_amount REAL NOT NULL,
        currency TEXT NOT NULL DEFAULT 'INR',
        status TEXT NOT NULL, -- PLACED, DELIVERED, CANCELLED, RETURNED
        shipping_address TEXT NOT NULL, -- JSON
        items TEXT NOT NULL, -- JSON array
        placed_at TEXT NOT NULL,
        delivered_at TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
        FOREIGN KEY (agent_id) REFERENCES agents (agent_id)
    );
    """)

    # 4. Returns & Refunds Table (Role 2: Amazon India Store)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS returns (
        return_id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        agent_id TEXT NOT NULL,
        item_id TEXT NOT NULL,
        reason TEXT NOT NULL,
        refund_amount REAL NOT NULL,
        refund_method TEXT NOT NULL, -- AMAZON_PAY_BALANCE, ORIGINAL_PAYMENT
        status TEXT NOT NULL, -- INITIATED, APPROVED, REJECTED, REFUNDED
        created_at TEXT NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders (order_id)
    );
    """)

    # 5. Customer Approvals Table (Role 4: Spending & Approvals)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS approval_requests (
        approval_id TEXT PRIMARY KEY,
        agent_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        action_type TEXT NOT NULL,
        payload TEXT NOT NULL, -- JSON
        challenge_message TEXT NOT NULL,
        status TEXT NOT NULL, -- PENDING, APPROVED, REJECTED, EXPIRED
        created_at TEXT NOT NULL,
        resolved_at TEXT,
        decision_by TEXT -- CUSTOMER, TIMEOUT
    );
    """)

    # 6. Audit Logs Table (Role 5: Audit & Governance)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        audit_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        agent_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        action_type TEXT NOT NULL,
        payload_summary TEXT NOT NULL,
        rules_evaluated TEXT NOT NULL, -- JSON array of rule summaries
        decision TEXT NOT NULL, -- ALLOW, ASK CUSTOMER, BLOCK
        reason TEXT NOT NULL,
        execution_status TEXT NOT NULL -- EXECUTED, HELD_FOR_APPROVAL, BLOCKED
    );
    """)

    conn.commit()

    # Seed initial test customer if not exists
    cursor.execute("SELECT customer_id FROM customers WHERE customer_id = 'cust-amz-001'")
    now_iso = datetime.now(timezone.utc).isoformat()
    if not cursor.fetchone():
        cursor.execute("""
        INSERT INTO customers (customer_id, name, email, verified_pincodes, default_address, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "cust-amz-001",
            "Aarav Sharma",
            "aarav.sharma@example.in",
            json.dumps(["560001", "560034", "110001"]),
            json.dumps({
                "address_line": "Flat 402, Green Palms, MG Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001"
            }),
            now_iso
        ))

    # Seed specialized agents for distinct tasks (Teacher Requirement)
    specialized_agents = [
        (
            "agent-allow-001",
            "cust-amz-001",
            "RoutineShopperBot (ALLOW Agent)",
            "ACTIVE",
            "amz_gatekeeper_token_allow_001",
            json.dumps(["orders:buy", "orders:view"]),
            now_iso,
            None
        ),
        (
            "agent-ask-002",
            "cust-amz-001",
            "HighValueBuyerBot (ASK CUSTOMER Agent)",
            "ACTIVE",
            "amz_gatekeeper_token_ask_002",
            json.dumps(["orders:buy", "orders:view"]),
            now_iso,
            None
        ),
        (
            "agent-history-003",
            "cust-amz-001",
            "HistoryCheckerBot (HISTORY CHECK Agent)",
            "ACTIVE",
            "amz_gatekeeper_token_history_003",
            json.dumps(["orders:view"]),  # Read-only scope: blocks on buy attempts!
            now_iso,
            None
        ),
        (
            "agent-block-004",
            "cust-amz-001",
            "DecommissionedBot (BLOCK Agent)",
            "REVOKED",
            "amz_gatekeeper_token_block_004",
            json.dumps(["orders:buy", "orders:view"]),
            now_iso,
            now_iso  # Revoked timestamp
        ),
        (
            "agent-return-005",
            "cust-amz-001",
            "ReturnsRefundBot (RETURNS Agent)",
            "ACTIVE",
            "amz_gatekeeper_token_return_005",
            json.dumps(["returns:create", "returns:view", "orders:view"]),
            now_iso,
            None
        ),
        (
            "agent-luxury-006",
            "cust-amz-001",
            "LuxuryJewelryBot (RESTRICTED CATEGORY Agent)",
            "ACTIVE",
            "amz_gatekeeper_token_luxury_006",
            json.dumps(["orders:buy", "orders:view"]),
            now_iso,
            None
        )
    ]

    for ag in specialized_agents:
        cursor.execute("SELECT agent_id FROM agents WHERE agent_id = ?", (ag[0],))
        if not cursor.fetchone():
            cursor.execute("""
            INSERT INTO agents (agent_id, customer_id, name, status, api_token, scopes, created_at, revoked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ag)

    conn.commit()
    conn.close()
