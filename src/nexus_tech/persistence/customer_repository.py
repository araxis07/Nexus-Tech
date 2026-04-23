"""Repository for persisted key customer accounts."""

from __future__ import annotations

import sqlite3
from decimal import Decimal
from uuid import UUID

from nexus_tech.domain.models import (
    ContractBillingModel,
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
                billing_model,
                seat_count,
                usage_units,
                discount_rate,
                satisfaction,
                onboarding_health,
                support_load,
                open_tickets,
                sla_breach_risk,
                expansion_potential,
                renewal_turn,
                churn_risk,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    account.billing_model.value,
                    account.seat_count,
                    account.usage_units,
                    str(account.discount_rate),
                    account.satisfaction,
                    account.onboarding_health,
                    account.support_load,
                    account.open_tickets,
                    account.sla_breach_risk,
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
                billing_model,
                seat_count,
                usage_units,
                discount_rate,
                satisfaction,
                onboarding_health,
                support_load,
                open_tickets,
                sla_breach_risk,
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
                billing_model=ContractBillingModel(row["billing_model"] or "flat"),
                seat_count=row["seat_count"] or 0,
                usage_units=row["usage_units"] or 0,
                discount_rate=Decimal(row["discount_rate"] or "0.0000"),
                satisfaction=row["satisfaction"],
                onboarding_health=row["onboarding_health"] or 60,
                support_load=row["support_load"] or 20,
                open_tickets=row["open_tickets"] or 0,
                sla_breach_risk=row["sla_breach_risk"] or 0,
                expansion_potential=row["expansion_potential"],
                renewal_turn=row["renewal_turn"],
                churn_risk=row["churn_risk"],
                status=CustomerAccountStatus(row["status"]),
            )
            for row in rows
        ]
