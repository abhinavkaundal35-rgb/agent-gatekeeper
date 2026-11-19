# Agent Gatekeeper

> **Academic Project**: Security Gatekeeper for Customer AI Agents  
> **Assigned Business Category**: **Online Store** (Enrolment ending in 7)  
> **Real-World Reference Company**: **Amazon India**  
> **Core Objective**: Intercept and evaluate requests from customer AI agents and return one of three governance decisions:
> - **`ALLOW`**: Safe, authorized, within budget and policy limits. Executes immediately.
> - **`ASK CUSTOMER`**: Sensitive action, high transaction value, delivery address change, or return policy boundary requiring human customer sign-off.
> - **`BLOCK`**: Revoked agent, unauthorized action scope, hard spending limit breach, or security policy violation.

---

## Architecture & Integration Pipeline

```
[ Customer AI Agent ]
         │ (HTTP POST: agent_id, api_token, action_type, payload)
         ▼
[ 1. Agent IAM Gateway (Role 1) ] ──────────► (If Revoked/Invalid) ──► BLOCK
         │ (Authenticated Agent)
         ▼
[ 2. Amazon India Domain Validator (Role 2) ]
         │ (Validated Order / Return / View)
         ▼
[ 3. Spending Limit Tracker (Role 4) ]
         │ (Current rolling 24-hr aggregate + proposed INR value)
         ▼
[ 4. Configurable Security Rules Engine (Role 3) ]
         │ (Priority order: BLOCK > ASK CUSTOMER > ALLOW)
         ├──────────────────────────────────────────────┬──────────────────────────────┐
         ▼                                              ▼                              ▼
  [ Verdict: BLOCK ]                         [ Verdict: ASK CUSTOMER ]          [ Verdict: ALLOW ]
  (Security/Hard-Cap Breach)                 (High Value / Address Change)      (Routine, Within Budget)
         │                                              │                              │
         │                                              ▼                              ▼
         │                                   [ Customer Approval Queue ]      [ Amazon India Mock Store ]
         │                                   (Role 4: Token Challenge)        (Role 2: Order Placed/Returned)
         │                                              │                              │
         └──────────────────────────────────────────────┴──────────────────────────────┘
                                                        │
                                                        ▼
                                        [ 5. Immutable Audit Logger (Role 5) ]
                                        (Timestamped trace with evaluated rules)
```

---

## Specialist Development Roles & Contributions

The project is structured modularly across six specialist engineering roles:

| Role | Domain Area | Responsibilities & Implemented Components |
| :--- | :--- | :--- |
| **Role 1** | **Agent IAM Specialist** | Agent registration, credential lifecycle (`api_token`), status management (`ACTIVE`/`REVOKED`), permission scopes (`orders:view`, `orders:buy`, `returns:create`), and instant revocation (`src/iam/`). |
| **Role 2** | **E-Commerce Domain Specialist** | Amazon India domain models (INR ₹ pricing, Indian 6-digit PIN validation, items, catalog), order creation, order viewing, and return/refund eligibility checks (`src/store/`). |
| **Role 3** | **Security Rules Engine Specialist** | Declarative rules configuration (`config/security_rules.json`), rule parser (`rule_loader.py`), priority-based condition evaluator enforcing `BLOCK > ASK CUSTOMER > ALLOW` (`src/engine/`). |
| **Role 4** | **Spending Limit & Approvals Specialist** | Rolling 24-hour spending aggregate tracking in INR, threshold caps (auto ₹2,000; hard cap ₹15,000; daily cap ₹25,000), and customer approval challenge state machine (`src/approvals/`). |
| **Role 5** | **Audit Logging & Governance Specialist** | Immutable, append-only SQLite audit log recording UTC timestamps (ISO-8601), requesting agent, customer, evaluated rule IDs, final decision, and execution status (`src/audit/`). |
| **Role 6** | **QA & Security Testing Specialist** | Automated Pytest test suite with 100% pass rate across 23 test cases verifying registration, revocation, orders, returns, rules, limits, and full end-to-end flows (`tests/`). |

---

## Directory Structure

```
agent-gatekeeper/
├── config/
│   └── security_rules.json          # Declarative security rules and thresholds
├── src/
│   ├── main.py                      # FastAPI application entry point
│   ├── core/                        # Core configuration and SQLite database setup
│   ├── iam/                         # Role 1: Agent IAM (Registration & Revocation)
│   ├── store/                       # Role 2: Amazon India Store (Orders & Returns)
│   ├── engine/                      # Role 3: Security Policy & Rules Engine
│   ├── approvals/                   # Role 4: Spending Limits & Customer Approvals
│   ├── audit/                       # Role 5: Immutable Audit Logging
│   └── gatekeeper/                  # Pipeline Orchestrator integrating all roles
├── tests/                           # Role 6: Comprehensive Automated Test Suite
│   ├── test_iam.py                  # Agent registration, token check, revocation
│   ├── test_orders.py               # Order viewing and purchasing in INR
│   ├── test_returns.py              # Return window and refund policy
│   ├── test_rules_engine.py         # Rules evaluator and priority checks
│   ├── test_spending_limits.py      # Daily and per-transaction limits in INR
│   ├── test_audit.py                # Audit log creation and query verification
│   └── test_gatekeeper_e2e.py       # End-to-end tests for ALLOW, ASK, and BLOCK
├── demo/
│   └── run_demo.py                  # Interactive CLI presentation demo
├── requirements.txt                 # Project dependencies
└── README.md                        # Documentation
```

---

## Getting Started

### 1. Prerequisites
- Python 3.10+ (Verified on Python 3.14)
- Git

### 2. Install Dependencies
```bash
python -m pip install -r requirements.txt
```

### 3. Run Automated Tests
Execute the full test suite with verbose output:
```bash
python -m pytest tests/ -v
```
*(All 23 tests pass covering all functional requirements).*

### 4. Run the Live Demonstration
Run the included demonstration script to simulate agent requests and review the gatekeeper's triage decisions live in the terminal:
```bash
python demo/run_demo.py
```

### 5. Launch the REST API Server
Start the FastAPI server:
```bash
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```
- Interactive Swagger UI: Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) in your browser.
- Health Check: `GET http://127.0.0.1:8000/health`

---

## REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/gatekeeper/evaluate` | **Core Gatekeeper Interceptor**: Evaluates agent requests to `ALLOW`, `ASK CUSTOMER`, or `BLOCK` |
| `POST` | `/api/v1/agents/register` | Register a new customer AI agent and receive an API token |
| `POST` | `/api/v1/agents/{id}/revoke` | Immediately revoke an AI agent's access |
| `GET` | `/api/v1/agents` | List registered agents |
| `GET` | `/api/v1/store/catalog` | View Amazon India reference product catalog |
| `GET` | `/api/v1/store/orders` | View past customer orders |
| `GET` | `/api/v1/store/returns` | List return requests |
| `GET` | `/api/v1/spending/{customer_id}`| View rolling 24-hour spend aggregate in INR |
| `POST` | `/api/v1/approvals/{id}/respond` | Customer response (`APPROVED`/`REJECTED`) for held transactions |
| `GET` | `/api/v1/audit` | Query immutable audit log records |
