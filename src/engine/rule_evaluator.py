"""Security Policy Rules Evaluator enforcing priority triage: BLOCK > ASK CUSTOMER > ALLOW."""
from typing import Optional, List, Dict, Any
from src.engine.models import (
    GatekeeperVerdict,
    SecurityRulesConfig,
    RuleEvaluationContext,
    EvaluationResult,
    SecurityRule
)
from src.engine.rule_loader import RuleLoader

class RuleEvaluator:
    @staticmethod
    def _evaluate_condition(
        rule: SecurityRule,
        ctx: RuleEvaluationContext,
        config: SecurityRulesConfig
    ) -> bool:
        """
        Safely and deterministically evaluate a declarative rule condition against the context.
        """
        # Scope / Action filter
        if rule.action_type != "ALL" and rule.action_type != ctx.action_type:
            return False

        r_id = rule.rule_id
        thresh = config.thresholds

        # SEC-R01: Revoked Agent Intercept
        if r_id == "SEC-R01":
            return ctx.agent_is_revoked

        # SEC-R02: Unauthorized Scope Intercept
        if r_id == "SEC-R02":
            if ctx.requested_scope is None:
                return False
            return ctx.requested_scope not in ctx.agent_scopes

        # SEC-R03: Transaction Hard Cap Exceeded
        if r_id == "SEC-R03":
            return ctx.transaction_amount > thresh.transaction_hard_cap_inr

        # SEC-R04: Daily Spending Limit Hard Cap
        if r_id == "SEC-R04":
            return ctx.daily_spend_cumulative > thresh.daily_spend_hard_cap_inr

        # SEC-R05: Non-Returnable Category Check
        if r_id == "SEC-R05":
            return any(cat in config.non_returnable_categories for cat in ctx.item_categories)

        # SEC-R06: Return Window Expired
        if r_id == "SEC-R06":
            if ctx.days_since_delivery is not None:
                return ctx.days_since_delivery > thresh.return_window_days
            return False

        # SEC-R07: High Value Purchase Step-Up Approval
        if r_id == "SEC-R07":
            return ctx.transaction_amount > thresh.auto_approval_max_inr

        # SEC-R08: Unverified Shipping Address
        if r_id == "SEC-R08":
            if ctx.shipping_pincode:
                return ctx.shipping_pincode not in ctx.customer_verified_pincodes
            return False

        # SEC-R09: High Risk Category Step-Up
        if r_id == "SEC-R09":
            return any(cat in config.restricted_categories for cat in ctx.item_categories)

        # SEC-R10: High Value Refund Approval
        if r_id == "SEC-R10":
            if ctx.refund_amount is not None:
                return ctx.refund_amount > thresh.refund_auto_approval_max_inr
            return False

        # Fallback for dynamic/custom conditions: safe evaluation environment
        try:
            safe_scope = {
                "agent_is_revoked": ctx.agent_is_revoked,
                "requested_scope": ctx.requested_scope,
                "agent_scopes": ctx.agent_scopes,
                "transaction_amount": ctx.transaction_amount,
                "daily_spend_cumulative": ctx.daily_spend_cumulative,
                "shipping_pincode": ctx.shipping_pincode,
                "customer_verified_pincodes": ctx.customer_verified_pincodes,
                "item_categories": ctx.item_categories,
                "days_since_delivery": ctx.days_since_delivery,
                "refund_amount": ctx.refund_amount,
                "thresholds": thresh,
                "restricted_categories": config.restricted_categories,
                "non_returnable_categories": config.non_returnable_categories,
            }
            # Simple expression check
            return bool(eval(rule.condition, {"__builtins__": {}}, safe_scope))
        except Exception:
            return False

    @classmethod
    def evaluate(
        cls,
        context: RuleEvaluationContext,
        config: Optional[SecurityRulesConfig] = None
    ) -> EvaluationResult:
        """
        Evaluate context against all active security rules.
        Enforces: BLOCK (highest precedence) > ASK CUSTOMER > ALLOW.
        """
        rules_cfg = config or RuleLoader.load_rules()
        # Sort by priority ascending (lower number = higher precedence)
        sorted_rules = sorted(rules_cfg.rules, key=lambda r: r.priority)

        evaluated_traces: List[Dict[str, Any]] = []
        candidate_ask: Optional[tuple[SecurityRule, str]] = None

        for rule in sorted_rules:
            matched = cls._evaluate_condition(rule, context, rules_cfg)
            evaluated_traces.append({
                "rule_id": rule.rule_id,
                "name": rule.name,
                "verdict": rule.verdict.value,
                "matched": matched,
                "priority": rule.priority
            })

            if matched:
                if rule.verdict == GatekeeperVerdict.BLOCK:
                    # BLOCK has absolute priority; return immediately
                    return EvaluationResult(
                        verdict=GatekeeperVerdict.BLOCK,
                        reason=rule.message,
                        triggered_rule_id=rule.rule_id,
                        triggered_rule_name=rule.name,
                        evaluated_rules=evaluated_traces
                    )
                elif rule.verdict == GatekeeperVerdict.ASK_CUSTOMER and candidate_ask is None:
                    # Record candidate ASK_CUSTOMER, but keep checking for any subsequent BLOCK
                    candidate_ask = (rule, rule.message)

        # If a rule triggered ASK_CUSTOMER and no rule triggered BLOCK:
        if candidate_ask:
            rule, message = candidate_ask
            return EvaluationResult(
                verdict=GatekeeperVerdict.ASK_CUSTOMER,
                reason=message,
                triggered_rule_id=rule.rule_id,
                triggered_rule_name=rule.name,
                evaluated_rules=evaluated_traces
            )

        # No blocking or approval triggers -> ALLOW
        return EvaluationResult(
            verdict=GatekeeperVerdict.ALLOW,
            reason="Request conforms to all security policies and spending guardrails.",
            triggered_rule_id=None,
            triggered_rule_name=None,
            evaluated_rules=evaluated_traces
        )
