"""Gatekeeper Router exposing the core evaluation endpoint."""
from fastapi import APIRouter
from src.gatekeeper.evaluator import (
    GatekeeperPipeline,
    GatekeeperEvaluationRequest,
    GatekeeperEvaluationResponse
)

router = APIRouter(prefix="/api/v1/gatekeeper", tags=["Gatekeeper Core"])

@router.post("/evaluate", response_model=GatekeeperEvaluationResponse)
def evaluate_agent_request(req: GatekeeperEvaluationRequest):
    """
    Core Gatekeeper Interceptor:
    Evaluates customer AI agent requests and returns ALLOW, ASK CUSTOMER, or BLOCK.
    """
    return GatekeeperPipeline.evaluate(req)
