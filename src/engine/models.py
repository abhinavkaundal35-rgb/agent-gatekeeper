"""Security Policy and Rules Engine Models."""
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator

class GatekeeperVerdict(str, Enum):
    ALLOW = "ALLOW"
    ASK_CUSTOMER = "ASK CUSTOMER"
    BLOCK = "BLOCK"

class SecurityRule(BaseModel):
    rule_id: str
    name: str
    action_type: str  # "ALL", "PURCHASE_ORDER", "RETURN_REQUEST", "VIEW_ORDERS"
    condition: str
    verdict: GatekeeperVerdict
    priority: int = 100
    message: str

    @field_validator("verdict", mode="before")
    @classmethod
    def normalize_verdict(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_norm = v.replace("_", " ").strip()
            if v_norm == "ASK CUSTOMER":
                return GatekeeperVerdict.ASK_CUSTOMER
        return v

class ThresholdConfig(BaseModel):
    auto_approval_max_inr: float = 2000.0
    transaction_hard_cap_inr: float = 15000.0
    daily_spend_hard_cap_inr: float = 25000.0
    return_window_days: int = 7
    refund_auto_approval_max_inr: float = 1000.0

class SecurityRulesConfig(BaseModel):
    system: str = "Agent Gatekeeper Security Rules"
    version: str = "1.0.0"
    reference_entity: str = "Amazon India"
    currency: str = "INR"
    thresholds: ThresholdConfig = Field(default_factory=ThresholdConfig)
    restricted_categories: List[str] = Field(default_factory=lambda: ["Jewelry", "Gift Cards", "Digital Goods"])
    non_returnable_categories: List[str] = Field(default_factory=lambda: ["Grocery", "Personal Hygiene", "Innerwear"])
    rules: List[SecurityRule] = Field(default_factory=list)

class RuleEvaluationContext(BaseModel):
    action_type: str
    requested_scope: Optional[str] = None
    agent_id: str
    agent_is_revoked: bool = False
    agent_scopes: List[str] = Field(default_factory=list)
    customer_id: str
    customer_verified_pincodes: List[str] = Field(default_factory=list)
    transaction_amount: float = 0.0
    daily_spend_cumulative: float = 0.0
    shipping_pincode: Optional[str] = None
    item_categories: List[str] = Field(default_factory=list)
    days_since_delivery: Optional[int] = None
    refund_amount: Optional[float] = None

class EvaluationResult(BaseModel):
    verdict: GatekeeperVerdict
    reason: str
    triggered_rule_id: Optional[str] = None
    triggered_rule_name: Optional[str] = None
    evaluated_rules: List[Dict[str, Any]] = Field(default_factory=list)
