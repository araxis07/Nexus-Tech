"""Repository for persisted finance state and funding history."""

from __future__ import annotations

import sqlite3
from decimal import Decimal

from nexus_tech.domain.models import FinanceState, FundingHistoryEntry, FundingType


class FinanceRepository:
    """Save and load finance state for a slot."""

    def save(self, connection: sqlite3.Connection, slot_name: str, finance: FinanceState) -> None:
        """Replace finance state for one slot."""

        connection.execute("DELETE FROM finance_state WHERE slot_name = ?", (slot_name,))
        connection.execute(
            """
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
                last_funding_turn
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
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
                finance.last_funding_turn,
            ),
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
