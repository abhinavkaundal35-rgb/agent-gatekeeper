"""Spending Tracker calculating cumulative daily expenditures and checking guardrails."""
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from src.core.database import get_db_connection

class SpendingTracker:
    @staticmethod
    def get_daily_spend(customer_id: str, db_path: Optional[str] = None) -> float:
        """
        Calculate total INR spent by a customer within the rolling past 24 hours.
        """
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

        cursor.execute("""
        SELECT SUM(total_amount) as daily_total
        FROM orders
        WHERE customer_id = ?
          AND placed_at >= ?
          AND status IN ('PLACED', 'SHIPPED', 'DELIVERED')
        """, (customer_id, cutoff))

        row = cursor.fetchone()
        conn.close()

        if row and row["daily_total"]:
            return float(row["daily_total"])
        return 0.0

    @staticmethod
    def get_spending_summary(
        customer_id: str,
        proposed_amount: float = 0.0,
        db_path: Optional[str] = None
    ) -> dict:
        """
        Return a breakdown of daily and proposed spending metrics.
        """
        current_daily = SpendingTracker.get_daily_spend(customer_id, db_path=db_path)
        return {
            "customer_id": customer_id,
            "current_daily_spend_inr": current_daily,
            "proposed_transaction_inr": proposed_amount,
            "projected_daily_spend_inr": current_daily + proposed_amount,
            "currency": "INR"
        }
