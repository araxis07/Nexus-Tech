"""Customer success actions layered on top of key-account management."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from nexus_tech.domain.models import (
    ContractCadence,
    CustomerAccount,
    CustomerAccountStatus,
    GameState,
)
from nexus_tech.domain.money import format_rate, quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.support import clamp_int, clamp_rate


@dataclass(frozen=True)
class CustomerSuccessActionSummary:
    """Summary of one customer-success action."""

    message: str


def invest_in_customer_success(
    state: GameState,
    product_id: UUID,
) -> CustomerSuccessActionSummary:
    """Improve onboarding and account health for one product's book of business."""

    matching_accounts = _get_product_accounts(state.customer_accounts, product_id)
    if not matching_accounts:
        raise ValueError("That product does not have active customer accounts yet.")
    if state.company.cash_on_hand < BALANCE.customer_success_investment_cost:
        raise ValueError("Not enough cash to invest in customer success this turn.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.customer_success_investment_cost
    )
    for account in matching_accounts:
        account.onboarding_health = clamp_int(
            account.onboarding_health + BALANCE.customer_success_onboarding_gain
        )
        account.satisfaction = clamp_int(
            account.satisfaction + BALANCE.customer_success_satisfaction_gain
        )
        account.support_load = clamp_int(
            account.support_load - BALANCE.customer_success_support_relief
        )
        account.churn_risk = clamp_int(
            account.churn_risk - BALANCE.customer_success_churn_risk_relief
        )
        if account.status is CustomerAccountStatus.AT_RISK and account.churn_risk < 40:
            account.status = CustomerAccountStatus.ACTIVE

    return CustomerSuccessActionSummary(
        message=(
            f"Invested in customer success for {len(matching_accounts)} account(s). "
            f"Cash -{BALANCE.customer_success_investment_cost}."
        )
    )


def run_retention_play(state: GameState, account_id: UUID) -> CustomerSuccessActionSummary:
    """Target one account with a retention save offer and white-glove follow-up."""

    account = get_customer_account_by_id(state.customer_accounts, account_id)
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < BALANCE.retention_play_cost:
        raise ValueError("Not enough cash to run a retention play this turn.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.retention_play_cost
    )
    account.discount_rate = clamp_rate(
        account.discount_rate + BALANCE.retention_discount_rate_increase
    )
    account.satisfaction = clamp_int(account.satisfaction + BALANCE.retention_satisfaction_gain)
    account.onboarding_health = clamp_int(
        account.onboarding_health + BALANCE.retention_onboarding_gain
    )
    account.support_load = clamp_int(account.support_load - BALANCE.retention_support_relief)
    account.churn_risk = clamp_int(account.churn_risk - BALANCE.retention_churn_risk_relief)
    if account.contract_cadence is ContractCadence.MONTHLY and account.discount_rate >= Decimal(
        "0.1000"
    ):
        account.contract_cadence = ContractCadence.ANNUAL
    if account.churn_risk < BALANCE.key_account_status_at_risk_threshold:
        account.status = CustomerAccountStatus.ACTIVE

    return CustomerSuccessActionSummary(
        message=(
            f"Retention play launched for {account.name}. "
            f"Discount now {format_rate(account.discount_rate)}, "
            f"cash -{BALANCE.retention_play_cost}."
        )
    )


def get_customer_account_by_id(
    accounts: list[CustomerAccount],
    account_id: UUID | None,
) -> CustomerAccount:
    """Resolve one customer account from the current run state."""

    if account_id is None:
        raise ValueError("This action requires selecting a customer account.")
    for account in accounts:
        if account.id == account_id:
            return account
    raise ValueError("Selected customer account was not found.")


def _get_product_accounts(
    accounts: list[CustomerAccount],
    product_id: UUID,
) -> list[CustomerAccount]:
    return [
        account
        for account in accounts
        if account.product_id == product_id and account.status is not CustomerAccountStatus.CHURNED
    ]
