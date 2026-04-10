"""Repository for persisted company state."""

from __future__ import annotations

import sqlite3
from decimal import Decimal
from uuid import UUID

from nexus_tech.domain.models import Company


class CompanyRepository:
    """Save and load the company aggregate."""

    def save(self, connection: sqlite3.Connection, slot_name: str, company: Company) -> None:
        """Replace the company state for one slot."""

        connection.execute(
            "DELETE FROM companies WHERE slot_name = ?",
            (slot_name,),
        )
        connection.execute(
            """
            INSERT INTO companies (
                slot_name,
                company_id,
                name,
                cash_on_hand,
                reputation,
                current_turn,
                game_over
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                slot_name,
                str(company.id),
                company.name,
                str(company.cash_on_hand),
                company.reputation,
                company.current_turn,
                int(company.game_over),
            ),
        )

    def load(self, connection: sqlite3.Connection, slot_name: str) -> Company | None:
        """Load company state for one slot."""

        row = connection.execute(
            """
            SELECT company_id, name, cash_on_hand, reputation, current_turn, game_over
            FROM companies
            WHERE slot_name = ?
            """,
            (slot_name,),
        ).fetchone()
        if row is None:
            return None

        return Company(
            id=UUID(row["company_id"]),
            name=row["name"],
            cash_on_hand=Decimal(row["cash_on_hand"]),
            reputation=row["reputation"],
            current_turn=row["current_turn"],
            game_over=bool(row["game_over"]),
        )
