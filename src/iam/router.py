"""IAM Router for Agent Gatekeeper."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Header, Query
from src.iam.models import AgentRegistrationRequest, AgentResponse, AgentRevocationResponse
from src.iam.service import IAMService

router = APIRouter(prefix="/api/v1/agents", tags=["Agent IAM"])

@router.post("/register", response_model=AgentResponse, status_code=201)
def register_agent(req: AgentRegistrationRequest):
    """Register a new customer AI agent."""
    agent = IAMService.register_agent(
        name=req.name,
        customer_id=req.customer_id,
        scopes=req.scopes
    )
    return agent

@router.post("/{agent_id}/revoke", response_model=AgentRevocationResponse)
def revoke_agent(agent_id: str):
    """Revoke an agent's access immediately."""
    agent = IAMService.revoke_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return AgentRevocationResponse(
        agent_id=agent.agent_id,
        status=agent.status,
        revoked_at=agent.revoked_at or "",
        message=f"Agent '{agent.name}' ({agent.agent_id}) has been revoked."
    )

@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str):
    """Get details of a registered agent."""
    agent = IAMService.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return agent

@router.get("", response_model=List[AgentResponse])
def list_agents(customer_id: Optional[str] = Query(None, description="Filter by customer ID")):
    """List all registered agents."""
    return IAMService.list_agents(customer_id=customer_id)
