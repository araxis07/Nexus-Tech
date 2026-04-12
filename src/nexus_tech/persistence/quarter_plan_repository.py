"""Repository for the current quarter plan."""

from __future__ import annotations

import sqlite3
from decimal import Decimal

from nexus_tech.domain.models import BudgetStance, QuarterPlan


class QuarterPlanRepository:
    """Save and load the quarter plan for a slot."""

    def save(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
        quarter_plan: QuarterPlan,
    ) -> None:
        """Replace the quarter plan for one slot."""

        connection.execute("DELETE FROM quarter_plan WHERE slot_name = ?", (slot_name,))
        connection.execute(
            """
            INSERT INTO quarter_plan (
                slot_name,
                budget_stance,
                set_turn,
                target_turn,
                revenue_target,
                user_target,
                cash_reserve_target,
                headcount_cap
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                slot_name,
                quarter_plan.budget_stance.value,
                quarter_plan.set_turn,
                quarter_plan.target_turn,
                str(quarter_plan.revenue_target),
                quarter_plan.user_target,
                str(quarter_plan.cash_reserve_target),
                quarter_plan.headcount_cap,
            ),
        )

    def load(self, connection: sqlite3.Connection, slot_name: str) -> QuarterPlan | None:
        """Load the quarter plan for one slot."""

        row = connection.execute(
            """
            SELECT
                budget_stance,
                set_turn,
                target_turn,
                revenue_target,
                user_target,
                cash_reserve_target,
                headcount_cap
            FROM quarter_plan
            WHERE slot_name = ?
            """,
            (slot_name,),
        ).fetchone()
        if row is None:
            return None

        return QuarterPlan(
            budget_stance=BudgetStance(row["budget_stance"]),
            set_turn=row["set_turn"],
            target_turn=row["target_turn"],
            revenue_target=Decimal(row["revenue_target"]),
            user_target=row["user_target"],
            cash_reserve_target=Decimal(row["cash_reserve_target"]),
            headcount_cap=row["headcount_cap"],
        )
