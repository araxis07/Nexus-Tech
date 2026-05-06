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
    PricingTier,
    RenewalOfferType,
    SubscriptionPackage,
    SupportTier,
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
                plan_tier,
                subscription_package,
                support_tier,
                contract_cadence,
                billing_model,
                seat_count,
                usage_units,
                add_on_count,
                annual_prepay,
                discount_rate,
                satisfaction,
                onboarding_health,
                support_load,
                open_tickets,
                sla_breach_risk,
                invoice_risk,
                failed_payment_risk,
                dunning_steps,
                escalation_count,
                ticket_queue_age,
                renewal_offer_active,
                renewal_offer_type,
                win_back_attempts,
                expansion_potential,
                renewal_health,
                renewal_turn,
                churn_risk,
                status
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?
            )
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
                    account.plan_tier.value,
                    account.subscription_package.value,
                    account.support_tier.value,
                    account.contract_cadence.value,
                    account.billing_model.value,
                    account.seat_count,
                    account.usage_units,
                    account.add_on_count,
                    int(account.annual_prepay),
                    str(account.discount_rate),
                    account.satisfaction,
                    account.onboarding_health,
                    account.support_load,
                    account.open_tickets,
                    account.sla_breach_risk,
                    account.invoice_risk,
                    account.failed_payment_risk,
                    account.dunning_steps,
                    account.escalation_count,
                    account.ticket_queue_age,
                    int(account.renewal_offer_active),
                    account.renewal_offer_type.value
                    if account.renewal_offer_type is not None
                    else None,
                    account.win_back_attempts,
                    account.expansion_potential,
                    account.renewal_health,
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
                plan_tier,
                subscription_package,
                support_tier,
                contract_cadence,
                billing_model,
                seat_count,
                usage_units,
                add_on_count,
                annual_prepay,
                discount_rate,
                satisfaction,
                onboarding_health,
                support_load,
                open_tickets,
                sla_breach_risk,
                invoice_risk,
                failed_payment_risk,
                dunning_steps,
                escalation_count,
                ticket_queue_age,
                renewal_offer_active,
                renewal_offer_type,
                win_back_attempts,
                expansion_potential,
                renewal_health,
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
                plan_tier=PricingTier(row["plan_tier"] or "standard"),
                subscription_package=SubscriptionPackage(row["subscription_package"] or "growth"),
                support_tier=SupportTier(row["support_tier"] or "standard"),
                contract_cadence=ContractCadence(row["contract_cadence"] or "annual"),
                billing_model=ContractBillingModel(row["billing_model"] or "flat"),
                seat_count=row["seat_count"] if row["seat_count"] is not None else 0,
                usage_units=row["usage_units"] if row["usage_units"] is not None else 0,
                add_on_count=row["add_on_count"] if row["add_on_count"] is not None else 0,
                annual_prepay=bool(row["annual_prepay"]),
                discount_rate=Decimal(row["discount_rate"] or "0.0000"),
                satisfaction=row["satisfaction"],
                onboarding_health=(
                    row["onboarding_health"] if row["onboarding_health"] is not None else 60
                ),
                support_load=row["support_load"] if row["support_load"] is not None else 20,
                open_tickets=row["open_tickets"] if row["open_tickets"] is not None else 0,
                sla_breach_risk=(
                    row["sla_breach_risk"] if row["sla_breach_risk"] is not None else 0
                ),
                invoice_risk=row["invoice_risk"] if row["invoice_risk"] is not None else 0,
                failed_payment_risk=(
                    row["failed_payment_risk"] if row["failed_payment_risk"] is not None else 0
                ),
                dunning_steps=row["dunning_steps"] if row["dunning_steps"] is not None else 0,
                escalation_count=(
                    row["escalation_count"] if row["escalation_count"] is not None else 0
                ),
                ticket_queue_age=(
                    row["ticket_queue_age"] if row["ticket_queue_age"] is not None else 0
                ),
                renewal_offer_active=bool(row["renewal_offer_active"]),
                renewal_offer_type=(
                    RenewalOfferType(row["renewal_offer_type"])
                    if row["renewal_offer_type"]
                    else None
                ),
                win_back_attempts=(
                    row["win_back_attempts"] if row["win_back_attempts"] is not None else 0
                ),
                expansion_potential=row["expansion_potential"],
                renewal_health=row["renewal_health"] if row["renewal_health"] is not None else 60,
                renewal_turn=row["renewal_turn"],
                churn_risk=row["churn_risk"],
                status=CustomerAccountStatus(row["status"]),
            )
            for row in rows
        ]
