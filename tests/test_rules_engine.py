"""Tests for Configurable Security Rules Engine - Requirement 4."""
from src.engine.models import (
    RuleEvaluationContext,
    GatekeeperVerdict,
    SecurityRulesConfig,
    SecurityRule,
    ThresholdConfig
)
from src.engine.rule_evaluator import RuleEvaluator
from src.engine.rule_loader import RuleLoader

def test_load_configurable_rules():
    """Test loading and validating the declarative rules configuration."""
    config = RuleLoader.load_rules()
    assert config.currency == "INR"
    assert config.thresholds.auto_approval_max_inr == 2000.0
    assert config.thresholds.transaction_hard_cap_inr == 15000.0
    assert len(config.rules) >= 8

def test_priority_block_over_ask_customer():
    """Test invariant: BLOCK rules take precedence over ASK CUSTOMER rules."""
    custom_config = SecurityRulesConfig(
        thresholds=ThresholdConfig(auto_approval_max_inr=1000.0, transaction_hard_cap_inr=5000.0),
        rules=[
            SecurityRule(
                rule_id="RULE-ASK",
                name="Ask over 1000",
                action_type="PURCHASE_ORDER",
                condition="transaction_amount > thresholds.auto_approval_max_inr",
                verdict=GatekeeperVerdict.ASK_CUSTOMER,
                priority=50,
                message="Ask customer"
            ),
            SecurityRule(
                rule_id="RULE-BLOCK",
                name="Block over 5000",
                action_type="PURCHASE_ORDER",
                condition="transaction_amount > thresholds.transaction_hard_cap_inr",
                verdict=GatekeeperVerdict.BLOCK,
                priority=20,
                message="Hard limit exceeded"
            )
        ]
    )

    # When amount is 6000, both conditions trigger, but BLOCK must win
    ctx = RuleEvaluationContext(
        action_type="PURCHASE_ORDER",
        agent_id="agent-01",
        customer_id="cust-01",
        transaction_amount=6000.0
    )
    result = RuleEvaluator.evaluate(ctx, config=custom_config)
    assert result.verdict == GatekeeperVerdict.BLOCK
    assert result.triggered_rule_id == "RULE-BLOCK"

def test_allow_when_no_rules_triggered():
    """Test default ALLOW verdict when transaction is clean and under thresholds."""
    config = RuleLoader.load_rules()
    ctx = RuleEvaluationContext(
        action_type="PURCHASE_ORDER",
        agent_id="agent-01",
        agent_is_revoked=False,
        agent_scopes=["orders:buy"],
        requested_scope="orders:buy",
        customer_id="cust-01",
        customer_verified_pincodes=["560001"],
        shipping_pincode="560001",
        transaction_amount=899.0, # Well below ₹2,000 threshold
        daily_spend_cumulative=899.0,
        item_categories=["Fashion"]
    )
    result = RuleEvaluator.evaluate(ctx, config=config)
    assert result.verdict == GatekeeperVerdict.ALLOW
    assert "conforms" in result.reason.lower()
