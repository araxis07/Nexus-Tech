"""Repository for persisted finance state and funding history."""

from __future__ import annotations

import sqlite3
from decimal import Decimal

from nexus_tech.domain.models import (
    BoardAsk,
    BoardDirective,
    BoardResolution,
    FinanceState,
    FundingHistoryEntry,
    FundingType,
)


class FinanceRepository:
    """Save and load finance state for a slot."""

    def save(self, connection: sqlite3.Connection, slot_name: str, finance: FinanceState) -> None:
        """Replace finance state for one slot."""

        connection.execute("DELETE FROM finance_state WHERE slot_name = ?", (slot_name,))
        values = (
            slot_name,
            str(finance.debt_principal),
            str(finance.loan_interest_rate),
            str(finance.equity_dilution),
            finance.investor_pressure,
            finance.board_confidence,
            finance.covenant_risk,
            finance.missed_board_targets,
            str(finance.total_raised),
            str(finance.forecast_net_cash_flow),
            finance.forecast_runway_turns,
            str(finance.burn_multiple),
            finance.governance_risk,
            finance.board_pressure,
            finance.board_directive.value,
            finance.active_board_ask.value,
            finance.board_resolution.value,
            finance.board_score,
            finance.board_profitability_score,
            finance.board_reliability_score,
            finance.board_team_health_score,
            finance.board_portfolio_focus_score,
            int(finance.board_warning_active),
            finance.board_warning_level,
            finance.quarterly_review_count,
            finance.restructuring_pressure,
            int(finance.governance_crisis_active),
            finance.governance_crisis_level,
            finance.board_recovery_focus.value,
            finance.board_recovery_turns_remaining,
            int(finance.board_resolution_due),
            finance.board_resolution_window,
            finance.board_resolution_miss_streak,
            finance.last_board_review_turn,
            finance.last_funding_turn,
        )
        placeholders = ", ".join(["?"] * len(values))
        connection.execute(
            f"""
            INSERT INTO finance_state (
                slot_name,
                debt_principal,
                loan_interest_rate,
                equity_dilution,
                investor_pressure,
                board_confidence,
                covenant_risk,
                missed_board_targets,
                total_raised,
                forecast_net_cash_flow,
                forecast_runway_turns,
                burn_multiple,
                governance_risk,
                board_pressure,
                board_directive,
                active_board_ask,
                board_resolution,
                board_score,
                board_profitability_score,
                board_reliability_score,
                board_team_health_score,
                board_portfolio_focus_score,
                board_warning_active,
                board_warning_level,
                quarterly_review_count,
                restructuring_pressure,
                governance_crisis_active,
                governance_crisis_level,
                board_recovery_focus,
                board_recovery_turns_remaining,
                board_resolution_due,
                board_resolution_window,
                board_resolution_miss_streak,
                last_board_review_turn,
                last_funding_turn
            )
            VALUES ({placeholders})
            """,
            values,
        )

    def load(self, connection: sqlite3.Connection, slot_name: str) -> FinanceState | None:
        """Load finance state for one slot."""

        row = connection.execute(
            """
            SELECT
                debt_principal,
                loan_interest_rate,
                equity_dilution,
                investor_pressure,
                board_confidence,
                covenant_risk,
                missed_board_targets,
                total_raised,
                forecast_net_cash_flow,
                forecast_runway_turns,
                burn_multiple,
                governance_risk,
                board_pressure,
                board_directive,
                active_board_ask,
                board_resolution,
                board_score,
                board_profitability_score,
                board_reliability_score,
                board_team_health_score,
                board_portfolio_focus_score,
                board_warning_active,
                board_warning_level,
                quarterly_review_count,
                restructuring_pressure,
                governance_crisis_active,
                governance_crisis_level,
                board_recovery_focus,
                board_recovery_turns_remaining,
                board_resolution_due,
                board_resolution_window,
                board_resolution_miss_streak,
                last_board_review_turn,
                last_funding_turn
            FROM finance_state
            WHERE slot_name = ?
            """,
            (slot_name,),
        ).fetchone()
        if row is None:
            return None

        return FinanceState(
            debt_principal=Decimal(row["debt_principal"]),
            loan_interest_rate=Decimal(row["loan_interest_rate"]),
            equity_dilution=Decimal(row["equity_dilution"]),
            investor_pressure=row["investor_pressure"],
            board_confidence=(
                row["board_confidence"] if row["board_confidence"] is not None else 55
            ),
            covenant_risk=row["covenant_risk"] or 0,
            missed_board_targets=row["missed_board_targets"] or 0,
            total_raised=Decimal(row["total_raised"]),
            forecast_net_cash_flow=Decimal(row["forecast_net_cash_flow"] or "0.00"),
            forecast_runway_turns=row["forecast_runway_turns"],
            burn_multiple=Decimal(row["burn_multiple"] or "0.00"),
            governance_risk=row["governance_risk"] or 0,
            board_pressure=row["board_pressure"] or 0,
            board_directive=BoardDirective(row["board_directive"] or "accelerate_growth"),
            active_board_ask=BoardAsk(row["active_board_ask"] or "profitability"),
            board_resolution=BoardResolution(row["board_resolution"] or "hold_course"),
            board_score=row["board_score"] or 55,
            board_profitability_score=row["board_profitability_score"] or 55,
            board_reliability_score=row["board_reliability_score"] or 55,
            board_team_health_score=row["board_team_health_score"] or 55,
            board_portfolio_focus_score=row["board_portfolio_focus_score"] or 55,
            board_warning_active=bool(row["board_warning_active"]),
            board_warning_level=row["board_warning_level"] or 0,
            quarterly_review_count=row["quarterly_review_count"] or 0,
            restructuring_pressure=row["restructuring_pressure"] or 0,
            governance_crisis_active=bool(row["governance_crisis_active"]),
            governance_crisis_level=row["governance_crisis_level"] or 0,
            board_recovery_focus=BoardAsk(row["board_recovery_focus"] or "profitability"),
            board_recovery_turns_remaining=row["board_recovery_turns_remaining"] or 0,
            board_resolution_due=bool(row["board_resolution_due"]),
            board_resolution_window=row["board_resolution_window"] or 0,
            board_resolution_miss_streak=row["board_resolution_miss_streak"] or 0,
            last_board_review_turn=row["last_board_review_turn"],
            last_funding_turn=row["last_funding_turn"],
        )

    def save_history(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
        funding_history: list[FundingHistoryEntry],
    ) -> None:
        """Replace funding history for one slot."""

        connection.execute("DELETE FROM funding_history WHERE slot_name = ?", (slot_name,))
        connection.executemany(
            """
            INSERT INTO funding_history (
                slot_name,
                entry_index,
                funding_type,
                turn,
                amount,
                dilution_added,
                debt_added,
                summary
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    slot_name,
                    index,
                    entry.funding_type.value,
                    entry.turn,
                    str(entry.amount),
                    str(entry.dilution_added),
                    str(entry.debt_added),
                    entry.summary,
                )
                for index, entry in enumerate(funding_history)
            ],
        )

    def load_history(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
    ) -> list[FundingHistoryEntry]:
        """Load funding history for one slot."""

        rows = connection.execute(
            """
            SELECT
                funding_type,
                turn,
                amount,
                dilution_added,
                debt_added,
                summary
            FROM funding_history
            WHERE slot_name = ?
            ORDER BY entry_index ASC
            """,
            (slot_name,),
        ).fetchall()
        return [
            FundingHistoryEntry(
                funding_type=FundingType(row["funding_type"]),
                turn=row["turn"],
                amount=Decimal(row["amount"]),
                dilution_added=Decimal(row["dilution_added"]),
                debt_added=Decimal(row["debt_added"]),
                summary=row["summary"],
            )
            for row in rows
        ]
