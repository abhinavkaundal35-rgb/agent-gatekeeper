"""IAM Models for Agent Gatekeeper."""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class AgentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"

class StandardScopes:
    ORDERS_VIEW = "orders:view"
    ORDERS_BUY = "orders:buy"
    RETURNS_CREATE = "returns:create"
    RETURNS_VIEW = "returns:view"
    ALL_SCOPES = [ORDERS_VIEW, ORDERS_BUY, RETURNS_CREATE, RETURNS_VIEW]

class AgentRegistrationRequest(BaseModel):
    name: str = Field(..., description="Descriptive name of the AI agent")
    customer_id: str = Field(..., description="Customer ID this agent acts on behalf of")
    scopes: List[str] = Field(
        default_factory=lambda: [StandardScopes.ORDERS_VIEW, StandardScopes.ORDERS_BUY],
        description="Permission scopes granted to the agent"
    )

class AgentResponse(BaseModel):
    agent_id: str
    customer_id: str
    name: str
    status: AgentStatus
    api_token: str
    scopes: List[str]
    created_at: str
    revoked_at: Optional[str] = None

class AgentRevocationResponse(BaseModel):
    agent_id: str
    status: AgentStatus
    revoked_at: str
    message: str
