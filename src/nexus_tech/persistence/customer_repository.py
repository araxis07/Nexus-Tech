"""Repository for persisted key customer accounts."""

from __future__ import annotations

import sqlite3
from decimal import Decimal
from uuid import UUID

from nexus_tech.domain.models import (
    ContractCadence,
    CustomerAccount,
    CustomerAccountStatus,
    MarketSegment,
)


class CustomerAccountRepository:
    """Save and load key accounts for a slot."""

    def save_all(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
        accounts: list[CustomerAccount],
    ) -> None:
        """Replace the account roster for one slot."""

        connection.execute("DELETE FROM customer_accounts WHERE slot_name = ?", (slot_name,))
        connection.executemany(
            """
            INSERT INTO customer_accounts (
                slot_name,
                account_id,
                display_order,
                name,
                product_id,
                segment,
                contract_value,
                contract_cadence,
                discount_rate,
                satisfaction,
                onboarding_health,
                support_load,
                expansion_potential,
                renewal_turn,
                churn_risk,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    slot_name,
                    str(account.id),
                    index,
                    account.name,
                    str(account.product_id),
                    account.segment.value,
                    str(account.contract_value),
                    account.contract_cadence.value,
                    str(account.discount_rate),
                    account.satisfaction,
                    account.onboarding_health,
                    account.support_load,
                    account.expansion_potential,
                    account.renewal_turn,
                    account.churn_risk,
                    account.status.value,
                )
                for index, account in enumerate(accounts)
            ],
        )

    def load_all(self, connection: sqlite3.Connection, slot_name: str) -> list[CustomerAccount]:
        """Load customer accounts for one slot."""

        rows = connection.execute(
            """
            SELECT
                account_id,
                name,
                product_id,
                segment,
                contract_value,
                contract_cadence,
                discount_rate,
                satisfaction,
                onboarding_health,
                support_load,
                expansion_potential,
                renewal_turn,
                churn_risk,
                status
            FROM customer_accounts
            WHERE slot_name = ?
            ORDER BY display_order ASC
            """,
            (slot_name,),
        ).fetchall()
        return [
            CustomerAccount(
                id=UUID(row["account_id"]),
                name=row["name"],
                product_id=UUID(row["product_id"]),
                segment=MarketSegment(row["segment"]),
                contract_value=Decimal(row["contract_value"]),
                contract_cadence=ContractCadence(row["contract_cadence"] or "annual"),
                discount_rate=Decimal(row["discount_rate"] or "0.0000"),
                satisfaction=row["satisfaction"],
                onboarding_health=row["onboarding_health"] or 60,
                support_load=row["support_load"] or 20,
                expansion_potential=row["expansion_potential"],
                renewal_turn=row["renewal_turn"],
                churn_risk=row["churn_risk"],
                status=CustomerAccountStatus(row["status"]),
            )
            for row in rows
        ]
