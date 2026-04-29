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
    RenewalOfferType,
    SubscriptionPackage,
)
from nexus_tech.domain.money import format_money, format_rate, quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.pricing import determine_target_subscription_package
from nexus_tech.simulation.support import clamp_int, clamp_rate
from nexus_tech.simulation.support_program import improve_support_program


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
    improve_support_program(
        state.support_program,
        knowledge_base_gain=BALANCE.customer_success_knowledge_base_gain,
        automation_gain=BALANCE.customer_success_automation_gain,
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
        account.open_tickets = max(0, account.open_tickets - BALANCE.customer_success_ticket_relief)
        account.sla_breach_risk = clamp_int(
            account.sla_breach_risk - BALANCE.customer_success_sla_relief
        )
        account.failed_payment_risk = clamp_int(
            account.failed_payment_risk - (BALANCE.customer_success_sla_relief // 2)
        )
        account.churn_risk = clamp_int(
            account.churn_risk - BALANCE.customer_success_churn_risk_relief
        )
        account.renewal_health = clamp_int(account.renewal_health + 6)
        if account.status is CustomerAccountStatus.AT_RISK and account.churn_risk < 40:
            account.status = CustomerAccountStatus.ACTIVE

    return CustomerSuccessActionSummary(
        message=(
            f"Invested in customer success for {len(matching_accounts)} account(s). "
            f"Cash -{BALANCE.customer_success_investment_cost}. "
            f"Knowledge base {state.support_program.knowledge_base_level}, "
            f"automation {state.support_program.automation_level}."
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
    account.open_tickets = max(0, account.open_tickets - BALANCE.retention_ticket_relief)
    account.sla_breach_risk = clamp_int(account.sla_breach_risk - BALANCE.retention_sla_relief)
    account.invoice_risk = clamp_int(account.invoice_risk - BALANCE.retention_sla_relief)
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk - BALANCE.retention_sla_relief
    )
    account.dunning_steps = max(0, account.dunning_steps - 1)
    account.escalation_count = max(0, account.escalation_count - 1)
    account.churn_risk = clamp_int(account.churn_risk - BALANCE.retention_churn_risk_relief)
    account.renewal_health = clamp_int(account.renewal_health + 10)
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


def make_renewal_offer(
    state: GameState,
    account_id: UUID,
    *,
    offer_type: RenewalOfferType = RenewalOfferType.LIGHT_DISCOUNT,
) -> CustomerSuccessActionSummary:
    """Proactively offer renewal concessions before the next contract decision."""

    account = get_customer_account_by_id(state.customer_accounts, account_id)
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if account.renewal_offer_active:
        raise ValueError("A renewal offer is already active for that account.")
    if state.company.cash_on_hand < BALANCE.renewal_offer_cost:
        raise ValueError("Not enough cash to make a renewal offer this turn.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.renewal_offer_cost
    )
    account.renewal_offer_active = True
    account.renewal_offer_type = offer_type
    account.renewal_health = clamp_int(account.renewal_health + BALANCE.renewal_offer_health_gain)
    account.satisfaction = clamp_int(account.satisfaction + BALANCE.renewal_offer_satisfaction_gain)
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk - BALANCE.renewal_offer_risk_relief
    )
    offer_summary = "light discount"
    if offer_type is RenewalOfferType.LIGHT_DISCOUNT:
        account.discount_rate = clamp_rate(
            account.discount_rate
            + BALANCE.renewal_offer_discount_increase
            + BALANCE.renewal_offer_light_discount_extra
        )
    elif offer_type is RenewalOfferType.BUNDLE_UPGRADE:
        product = next(
            (product for product in state.products if product.id == account.product_id),
            None,
        )
        account.add_on_count += BALANCE.renewal_offer_bundle_add_on_gain
        if product is None:
            account.subscription_package = _upgrade_subscription_package(
                account.subscription_package
            )
        else:
            account.add_on_count += max(0, product.add_on_catalog_depth // 2)
            target_package = determine_target_subscription_package(product, account)
            if _package_rank(target_package) <= _package_rank(account.subscription_package):
                account.subscription_package = _upgrade_subscription_package(
                    account.subscription_package
                )
            else:
                account.subscription_package = target_package
            account.renewal_health = clamp_int(
                account.renewal_health + product.package_catalog_depth
            )
        account.renewal_health = clamp_int(
            account.renewal_health + BALANCE.renewal_offer_bundle_health_gain
        )
        offer_summary = "bundle upgrade"
    else:
        if account.contract_cadence is ContractCadence.MONTHLY:
            account.contract_cadence = ContractCadence.ANNUAL
        account.annual_prepay = True
        account.failed_payment_risk = clamp_int(
            account.failed_payment_risk - BALANCE.renewal_offer_term_extension_risk_relief
        )
        account.renewal_health = clamp_int(
            account.renewal_health + BALANCE.renewal_offer_term_extension_health_gain
        )
        offer_summary = "term extension"
    if account.renewal_turn > state.company.current_turn + BALANCE.renewal_offer_turn_window:
        account.renewal_turn = state.company.current_turn + BALANCE.renewal_offer_turn_window
    if account.status is CustomerAccountStatus.AT_RISK and account.renewal_health >= 60:
        account.status = CustomerAccountStatus.ACTIVE

    return CustomerSuccessActionSummary(
        message=(
            f"Made a {offer_summary} renewal offer to {account.name}. "
            f"Discount now {format_rate(account.discount_rate)}, "
            f"renewal turn {account.renewal_turn}, "
            f"cash -{BALANCE.renewal_offer_cost}."
        )
    )


def run_win_back_play(state: GameState, account_id: UUID) -> CustomerSuccessActionSummary:
    """Attempt to recover a churned account with a higher-touch commercial save."""

    account = get_customer_account_by_id(state.customer_accounts, account_id)
    if account.status is not CustomerAccountStatus.CHURNED:
        raise ValueError("That account has not churned and does not need a win-back play.")
    if state.company.cash_on_hand < BALANCE.win_back_play_cost:
        raise ValueError("Not enough cash to run a win-back play this turn.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.win_back_play_cost
    )
    account.status = CustomerAccountStatus.ACTIVE
    account.win_back_attempts += 1
    account.contract_value = quantize_money(
        account.contract_value * BALANCE.win_back_contract_multiplier
    )
    account.satisfaction = clamp_int(BALANCE.win_back_satisfaction_reset)
    account.onboarding_health = clamp_int(BALANCE.win_back_onboarding_reset)
    account.support_load = clamp_int(BALANCE.win_back_support_load_reset)
    account.churn_risk = clamp_int(BALANCE.win_back_churn_risk_reset)
    account.renewal_health = clamp_int(BALANCE.win_back_renewal_health_reset)
    account.failed_payment_risk = clamp_int(account.failed_payment_risk - 10)
    account.open_tickets = max(0, account.open_tickets - BALANCE.win_back_open_ticket_relief)
    account.dunning_steps = 0
    account.escalation_count = max(0, account.escalation_count - 1)
    account.renewal_offer_active = False
    account.renewal_offer_type = None
    account.renewal_turn = state.company.current_turn + 1

    return CustomerSuccessActionSummary(
        message=(
            f"Won back {account.name} at {format_money(account.contract_value)} ARR-equivalent. "
            f"Cash -{BALANCE.win_back_play_cost}."
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


def _upgrade_subscription_package(package: SubscriptionPackage) -> SubscriptionPackage:
    if package is SubscriptionPackage.STARTER:
        return SubscriptionPackage.GROWTH
    return SubscriptionPackage.ENTERPRISE_SUITE


def _package_rank(package: SubscriptionPackage) -> int:
    if package is SubscriptionPackage.STARTER:
        return 0
    if package is SubscriptionPackage.GROWTH:
        return 1
    return 2
