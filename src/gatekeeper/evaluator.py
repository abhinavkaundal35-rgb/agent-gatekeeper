"""Gatekeeper Pipeline Orchestrator integrating IAM, Domain, Spending, Rules, and Audit."""
import json
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from src.iam.service import IAMService
from src.iam.models import StandardScopes
from src.store.service import StoreService
from src.store.models import CartItem, IndianAddress, RefundMethod
from src.engine.models import RuleEvaluationContext, GatekeeperVerdict
from src.engine.rule_evaluator import RuleEvaluator
from src.approvals.spending_tracker import SpendingTracker
from src.approvals.approval_service import ApprovalService
from src.audit.logger import AuditLogger

class GatekeeperEvaluationRequest(BaseModel):
    agent_id: str
    api_token: Optional[str] = None
    customer_id: str
    action_type: str = Field(..., description="PURCHASE_ORDER, VIEW_ORDERS, or RETURN_REQUEST")
    payload: Dict[str, Any] = Field(default_factory=dict)

class GatekeeperEvaluationResponse(BaseModel):
    decision: str  # ALLOW, ASK CUSTOMER, BLOCK
    reason: str
    triggered_rule: Optional[str] = None
    audit_id: str
    approval_id: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None

class GatekeeperPipeline:
    @staticmethod
    def evaluate(
        req: GatekeeperEvaluationRequest,
        db_path: Optional[str] = None
    ) -> GatekeeperEvaluationResponse:
        """
        Execute the multi-tier gatekeeper pipeline.
        """
        # Determine required scope based on action
        scope_mapping = {
            "PURCHASE_ORDER": StandardScopes.ORDERS_BUY,
            "VIEW_ORDERS": StandardScopes.ORDERS_VIEW,
            "RETURN_REQUEST": StandardScopes.RETURNS_CREATE
        }
        required_scope = scope_mapping.get(req.action_type, "unknown:scope")

        # Step 1: IAM Credential & Revocation Verification (Role 1)
        is_valid, iam_reason, agent = IAMService.verify_agent_credentials(
            agent_id=req.agent_id,
            token=req.api_token,
            required_scope=required_scope,
            db_path=db_path
        )

        agent_is_revoked = False
        agent_scopes: List[str] = []
        if agent:
            agent_is_revoked = (agent.status.value == "REVOKED")
            agent_scopes = agent.scopes
        else:
            agent_is_revoked = True

        # Step 2: Context Extraction & Amazon India Domain Mapping (Role 2 & Role 4)
        transaction_amount = 0.0
        shipping_pincode: Optional[str] = None
        item_categories: List[str] = []
        days_since_delivery: Optional[int] = None
        refund_amount: Optional[float] = None
        payload_summary = f"Action: {req.action_type}"

        if req.action_type == "PURCHASE_ORDER":
            items_raw = req.payload.get("items", [])
            items = []
            for item in items_raw:
                try:
                    c_item = CartItem(**item)
                    items.append(c_item)
                    item_categories.append(c_item.category.value)
                except Exception:
                    pass
            transaction_amount = sum(i.total_price for i in items)
            shipping_addr = req.payload.get("shipping_address", {})
            shipping_pincode = shipping_addr.get("pincode")
            payload_summary = f"Purchase {len(items)} items for ₹{transaction_amount:,.2f} to PIN {shipping_pincode}"

        elif req.action_type == "RETURN_REQUEST":
            days_since_delivery = req.payload.get("days_since_delivery", 1)
            refund_amount = req.payload.get("refund_amount", 0.0)
            order_id = req.payload.get("order_id", "")
            item_id = req.payload.get("item_id", "")
            # If refund amount is zero or missing, look up from order item
            if (not refund_amount or refund_amount == 0.0) and order_id:
                order = StoreService.get_order(order_id, db_path=db_path)
                if order:
                    for it in order.items:
                        if it.item_id == item_id:
                            refund_amount = it.total_price
                            item_categories.append(it.category.value)
                            break
            # Also check if category was passed directly in payload
            if "category" in req.payload:
                item_categories.append(req.payload["category"])
            payload_summary = f"Return item {item_id} from order {order_id} (Refund: ₹{refund_amount or 0:,.2f})"

        elif req.action_type == "VIEW_ORDERS":
            payload_summary = f"View order history for customer {req.customer_id}"

        # Fetch spending history & customer verified pincodes
        daily_spend = SpendingTracker.get_daily_spend(req.customer_id, db_path=db_path)
        customer_pincodes = StoreService.get_customer_verified_pincodes(req.customer_id, db_path=db_path)

        # Build Rule Context
        eval_context = RuleEvaluationContext(
            action_type=req.action_type,
            requested_scope=required_scope,
            agent_id=req.agent_id,
            agent_is_revoked=agent_is_revoked,
            agent_scopes=agent_scopes,
            customer_id=req.customer_id,
            customer_verified_pincodes=customer_pincodes,
            transaction_amount=transaction_amount,
            daily_spend_cumulative=daily_spend + transaction_amount,
            shipping_pincode=shipping_pincode,
            item_categories=item_categories,
            days_since_delivery=days_since_delivery,
            refund_amount=refund_amount
        )

        # Step 3: Security Rules Engine Evaluation (Role 3)
        # Pre-check: if agent was non-existent or token invalid, trigger block
        if not agent:
            eval_result = RuleEvaluator.evaluate(eval_context)
            final_verdict = GatekeeperVerdict.BLOCK
            final_reason = f"Security block: {iam_reason}"
            triggered_rule = "SEC-R01"
            evaluated_rules = eval_result.evaluated_rules
        elif not is_valid and not agent_is_revoked and (required_scope not in agent_scopes):
            eval_result = RuleEvaluator.evaluate(eval_context)
            final_verdict = eval_result.verdict
            final_reason = eval_result.reason
            triggered_rule = eval_result.triggered_rule_id
            evaluated_rules = eval_result.evaluated_rules
        else:
            eval_result = RuleEvaluator.evaluate(eval_context)
            final_verdict = eval_result.verdict
            final_reason = eval_result.reason
            triggered_rule = eval_result.triggered_rule_id
            evaluated_rules = eval_result.evaluated_rules

        # Step 4: Decision Dispatch & Execution Routing
        approval_id: Optional[str] = None
        execution_result: Optional[Dict[str, Any]] = None
        exec_status = "BLOCKED"

        if final_verdict == GatekeeperVerdict.ALLOW:
            exec_status = "EXECUTED"
            # Execute underlying store action (Role 2)
            if req.action_type == "PURCHASE_ORDER":
                items = [CartItem(**item) for item in req.payload.get("items", [])]
                address = IndianAddress(**req.payload["shipping_address"])
                order_res = StoreService.create_order(
                    customer_id=req.customer_id,
                    agent_id=req.agent_id,
                    items=items,
                    shipping_address=address,
                    db_path=db_path
                )
                execution_result = order_res.model_dump()
            elif req.action_type == "VIEW_ORDERS":
                orders_res = StoreService.list_orders(
                    customer_id=req.customer_id,
                    agent_id=None,
                    db_path=db_path
                )
                execution_result = {"orders": [o.model_dump() for o in orders_res]}
            elif req.action_type == "RETURN_REQUEST":
                ret_method_val = req.payload.get("refund_method", RefundMethod.AMAZON_PAY_BALANCE.value)
                ret_res = StoreService.process_return(
                    customer_id=req.customer_id,
                    agent_id=req.agent_id,
                    order_id=req.payload["order_id"],
                    item_id=req.payload["item_id"],
                    reason=req.payload["reason"],
                    refund_method=RefundMethod(ret_method_val),
                    refund_amount=refund_amount,
                    db_path=db_path
                )
                execution_result = ret_res.model_dump()

        elif final_verdict == GatekeeperVerdict.ASK_CUSTOMER:
            exec_status = "HELD_FOR_APPROVAL"
            # Create Customer Approval Session (Role 4)
            challenge_msg = f"{final_reason} (Action: {req.action_type})"
            approval_res = ApprovalService.create_approval_request(
                agent_id=req.agent_id,
                customer_id=req.customer_id,
                action_type=req.action_type,
                payload=req.payload,
                challenge_message=challenge_msg,
                db_path=db_path
            )
            approval_id = approval_res.approval_id
            execution_result = {
                "approval_id": approval_id,
                "challenge_message": challenge_msg,
                "status": "AWAITING_CUSTOMER_CONFIRMATION"
            }

        elif final_verdict == GatekeeperVerdict.BLOCK:
            exec_status = "BLOCKED"
            execution_result = {
                "error": "Action blocked by Gatekeeper policy.",
                "reason": final_reason
            }

        # Step 5: Audit Log Persistence (Role 5)
        audit_entry = AuditLogger.log(
            agent_id=req.agent_id,
            customer_id=req.customer_id,
            action_type=req.action_type,
            payload_summary=payload_summary,
            rules_evaluated=evaluated_rules,
            decision=final_verdict.value,
            reason=final_reason,
            execution_status=exec_status,
            db_path=db_path
        )

        return GatekeeperEvaluationResponse(
            decision=final_verdict.value,
            reason=final_reason,
            triggered_rule=triggered_rule,
            audit_id=audit_entry.audit_id,
            approval_id=approval_id,
            execution_result=execution_result
        )
