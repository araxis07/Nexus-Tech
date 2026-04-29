"""Key-account simulation for customer depth, support, and contract pressure."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.constants import ZERO_MONEY
from nexus_tech.domain.models import (
    ContractCadence,
    CustomerAccount,
    CustomerAccountStatus,
    LifecycleStage,
    MarketSegment,
    Product,
    RenewalOfferType,
    SubscriptionPackage,
    SupportProgram,
    SupportTier,
)
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.contracts import (
    apply_commercial_renewal,
    apply_support_drift,
    build_contract_shape,
    calculate_account_recurring_revenue,
    get_contract_interval,
)
from nexus_tech.simulation.pricing import (
    get_default_subscription_package,
    get_packaging_add_on_bonus,
)
from nexus_tech.simulation.support import clamp_int
from nexus_tech.simulation.support_program import calculate_support_program_relief


@dataclass(frozen=True)
class CustomerTurnSummary:
    """Customer account changes created during an end-of-turn tick."""

    account_revenue: Decimal
    created_accounts: int
    renewed_accounts: int
    churned_accounts: int
    at_risk_accounts: int
    expansion_revenue: Decimal
    total_open_tickets: int
    sla_risk_accounts: int
    summary: str


def calculate_account_revenue(accounts: list[CustomerAccount]) -> Decimal:
    """Return recurring revenue from active key accounts."""

    return quantize_money(
        sum(
            (
                calculate_account_recurring_revenue(account)
                for account in accounts
                if account.status is not CustomerAccountStatus.CHURNED
            ),
            ZERO_MONEY,
        )
    )


def apply_end_of_turn_customers(
    accounts: list[CustomerAccount],
    products: list[Product],
    *,
    current_turn: int,
    customer_success_bonus: int = 0,
    support_program: SupportProgram | None = None,
) -> CustomerTurnSummary:
    """Update account satisfaction, support health, and commercial renewals."""

    created_accounts = _seed_new_accounts(accounts, products, current_turn=current_turn)
    renewed_accounts = 0
    churned_accounts = 0
    expansion_revenue = ZERO_MONEY
    products_by_id = {product.id: product for product in products}

    for account in accounts:
        if account.status is CustomerAccountStatus.CHURNED:
            continue
        product = products_by_id.get(account.product_id)
        if product is None or not product.is_active:
            account.status = CustomerAccountStatus.CHURNED
            churned_accounts += 1
            continue

        if support_program is None:
            support_ticket_relief, support_sla_relief = 0, 0
        else:
            support_ticket_relief, support_sla_relief = calculate_support_program_relief(
                support_program,
                customer_success_bonus=customer_success_bonus,
            )
        apply_support_drift(
            account,
            product,
            customer_success_bonus=customer_success_bonus,
        )
        account.open_tickets = max(0, account.open_tickets - support_ticket_relief)
        account.sla_breach_risk = clamp_int(account.sla_breach_risk - support_sla_relief)

        onboarding_delta = 0
        if product.market_fit >= 60 and product.quality >= 60:
            onboarding_delta += 2
        if product.bug_level >= 28:
            onboarding_delta -= 2
        if account.open_tickets >= 12:
            onboarding_delta -= 1
        onboarding_delta += customer_success_bonus
        account.onboarding_health = clamp_int(account.onboarding_health + onboarding_delta)
        account.renewal_health = clamp_int(
            48
            + ((account.satisfaction - 50) // 2)
            + ((account.onboarding_health - 50) // 3)
            - (account.open_tickets // 10)
            - (account.sla_breach_risk // 18)
            - BALANCE.subscription_package_support_burden[account.subscription_package.value]
        )

        satisfaction_delta = _calculate_satisfaction_delta(
            product,
            account,
            customer_success_bonus=customer_success_bonus,
        )
        account.satisfaction = clamp_int(account.satisfaction + satisfaction_delta)
        expansion_revenue = quantize_money(
            expansion_revenue
            + _apply_packaging_expansion_drift(
                account,
                product,
                current_turn=current_turn,
            )
        )
        if account.satisfaction >= BALANCE.key_account_satisfaction_good_threshold:
            account.churn_risk = clamp_int(
                account.churn_risk - BALANCE.key_account_churn_risk_relief,
            )
        if account.satisfaction <= BALANCE.key_account_satisfaction_bad_threshold:
            account.churn_risk = clamp_int(
                account.churn_risk + BALANCE.key_account_churn_risk_gain,
            )
        if account.sla_breach_risk >= BALANCE.contract_sla_risk_threshold:
            account.churn_risk = clamp_int(
                account.churn_risk + BALANCE.contract_sla_breach_churn_risk_gain,
            )
        invoice_risk_delta = 0
        if account.contract_cadence is ContractCadence.MONTHLY:
            invoice_risk_delta += BALANCE.contract_invoice_risk_monthly_gain
        invoice_risk_delta += int(
            account.discount_rate / BALANCE.contract_invoice_risk_discount_gain_divisor
        )
        invoice_risk_delta += account.open_tickets // BALANCE.contract_invoice_risk_ticket_divisor
        invoice_risk_delta -= (
            account.onboarding_health // BALANCE.contract_invoice_risk_onboarding_relief_divisor
        )
        if account.annual_prepay:
            invoice_risk_delta -= BALANCE.contract_invoice_risk_prepay_relief
        account.invoice_risk = clamp_int(account.invoice_risk + invoice_risk_delta)
        if account.invoice_risk >= BALANCE.contract_invoice_risk_threshold:
            account.churn_risk = clamp_int(
                account.churn_risk + BALANCE.contract_invoice_risk_churn_gain,
            )
        if account.invoice_risk >= BALANCE.contract_invoice_risk_severe_threshold:
            account.satisfaction = clamp_int(
                account.satisfaction - BALANCE.contract_invoice_risk_satisfaction_loss
            )
        failed_payment_delta = 0
        if account.contract_cadence is ContractCadence.MONTHLY:
            failed_payment_delta += BALANCE.contract_failed_payment_monthly_gain
        failed_payment_delta += (
            account.invoice_risk // BALANCE.contract_failed_payment_invoice_divisor
        )
        failed_payment_delta += int(
            account.discount_rate / BALANCE.contract_failed_payment_discount_divisor
        )
        failed_payment_delta -= (
            account.renewal_health // BALANCE.contract_failed_payment_health_relief_divisor
        )
        if account.annual_prepay:
            failed_payment_delta -= BALANCE.contract_failed_payment_prepay_relief
        account.failed_payment_risk = clamp_int(account.failed_payment_risk + failed_payment_delta)
        if account.failed_payment_risk >= BALANCE.contract_failed_payment_threshold:
            account.dunning_steps += 1
            account.satisfaction = clamp_int(
                account.satisfaction - BALANCE.contract_failed_payment_dunning_satisfaction_loss
            )
            account.churn_risk = clamp_int(
                account.churn_risk + BALANCE.contract_failed_payment_churn_gain
            )
        elif account.dunning_steps > 0 and account.failed_payment_risk < 30:
            account.dunning_steps -= 1
        account.escalation_count = 0
        if account.open_tickets >= BALANCE.support_program_escalation_ticket_threshold:
            account.escalation_count += 1
        if account.sla_breach_risk >= BALANCE.support_program_escalation_sla_threshold:
            account.escalation_count += 1
        if account.failed_payment_risk >= BALANCE.contract_failed_payment_threshold:
            account.escalation_count += 1

        if account.dunning_steps >= BALANCE.contract_failed_payment_dunning_limit:
            account.status = CustomerAccountStatus.CHURNED
            product.user_count = max(
                0,
                product.user_count - BALANCE.key_account_renewal_churn_user_loss,
            )
            churned_accounts += 1
            continue

        account.status = (
            CustomerAccountStatus.AT_RISK
            if account.churn_risk >= BALANCE.key_account_status_at_risk_threshold
            else CustomerAccountStatus.ACTIVE
        )

        if current_turn < account.renewal_turn:
            continue

        account.renewal_turn = current_turn + get_contract_interval(account.contract_cadence)
        discount_penalty = int(account.discount_rate / BALANCE.key_account_discount_risk_divisor)
        renewal_offer_relief = 0
        if account.renewal_offer_active:
            renewal_offer_relief += BALANCE.renewal_offer_risk_relief
            if account.renewal_offer_type is RenewalOfferType.TERM_EXTENSION:
                renewal_offer_relief += BALANCE.renewal_offer_term_extension_risk_relief // 2
        effective_churn_risk = clamp_int(
            account.churn_risk
            + discount_penalty
            + (account.sla_breach_risk // BALANCE.contract_sla_ticket_divisor)
            + (account.invoice_risk // BALANCE.contract_sla_support_divisor)
            - renewal_offer_relief
            - customer_success_bonus,
        )
        if effective_churn_risk >= BALANCE.key_account_churn_threshold:
            account.status = CustomerAccountStatus.CHURNED
            product.user_count = max(
                0,
                product.user_count - BALANCE.key_account_renewal_churn_user_loss,
            )
            account.renewal_offer_active = False
            account.renewal_offer_type = None
            churned_accounts += 1
            continue

        renewed_accounts += 1
        revenue_before = calculate_account_recurring_revenue(account)
        apply_commercial_renewal(account, customer_success_bonus=customer_success_bonus)
        account.renewal_offer_active = False
        account.renewal_offer_type = None
        revenue_after = calculate_account_recurring_revenue(account)
        if revenue_after > revenue_before:
            expansion_revenue = quantize_money(expansion_revenue + (revenue_after - revenue_before))

    account_revenue = calculate_account_revenue(accounts)
    active_accounts = [
        account for account in accounts if account.status is not CustomerAccountStatus.CHURNED
    ]
    at_risk_accounts = sum(
        1 for account in active_accounts if account.status is CustomerAccountStatus.AT_RISK
    )
    total_open_tickets = sum(account.open_tickets for account in active_accounts)
    sla_risk_accounts = sum(
        1
        for account in active_accounts
        if account.sla_breach_risk >= BALANCE.contract_sla_risk_threshold
    )
    summary = _build_customer_summary(
        created_accounts=created_accounts,
        renewed_accounts=renewed_accounts,
        churned_accounts=churned_accounts,
        at_risk_accounts=at_risk_accounts,
        total_open_tickets=total_open_tickets,
        sla_risk_accounts=sla_risk_accounts,
    )
    return CustomerTurnSummary(
        account_revenue=account_revenue,
        created_accounts=created_accounts,
        renewed_accounts=renewed_accounts,
        churned_accounts=churned_accounts,
        at_risk_accounts=at_risk_accounts,
        expansion_revenue=expansion_revenue,
        total_open_tickets=total_open_tickets,
        sla_risk_accounts=sla_risk_accounts,
        summary=summary,
    )


def _seed_new_accounts(
    accounts: list[CustomerAccount],
    products: list[Product],
    *,
    current_turn: int,
) -> int:
    existing_product_ids = {
        account.product_id
        for account in accounts
        if account.status is not CustomerAccountStatus.CHURNED
    }
    created = 0
    for product in products:
        if not product.is_active or product.id in existing_product_ids:
            continue
        if not _is_account_worthy_product(product):
            continue
        accounts.append(_create_account_from_product(product, current_turn=current_turn))
        existing_product_ids.add(product.id)
        created += 1
    return created


def _is_account_worthy_product(product: Product) -> bool:
    if product.lifecycle_stage is LifecycleStage.SUNSET:
        return False
    if product.target_segment is MarketSegment.ENTERPRISE:
        return product.user_count >= BALANCE.key_account_enterprise_user_threshold
    return product.user_count >= BALANCE.key_account_user_threshold and product.market_fit >= 54


def _create_account_from_product(product: Product, *, current_turn: int) -> CustomerAccount:
    contract_value = quantize_money(
        min(
            BALANCE.key_account_max_contract_value,
            max(
                BALANCE.key_account_min_contract_value,
                (
                    product.revenue_per_user
                    * Decimal(
                        max(1, product.user_count // BALANCE.key_account_contract_user_divisor)
                    )
                ),
            ),
        )
    )
    satisfaction = clamp_int(
        BALANCE.key_account_base_satisfaction
        + (product.quality // BALANCE.key_account_quality_divisor)
        - (product.bug_level // BALANCE.key_account_bug_divisor)
        - (product.technical_debt // BALANCE.key_account_debt_divisor),
    )
    contract_cadence = (
        ContractCadence.MONTHLY
        if product.target_segment is MarketSegment.STARTUP
        else ContractCadence.ANNUAL
    )
    billing_model, seat_count, usage_units = build_contract_shape(
        product.target_segment,
        pricing_tier=product.pricing_tier,
    )
    return CustomerAccount(
        name=f"{product.target_segment.value.title()} Anchor: {product.name}",
        product_id=product.id,
        segment=product.target_segment,
        contract_value=contract_value,
        plan_tier=product.pricing_tier,
        subscription_package=get_default_subscription_package(product),
        contract_cadence=contract_cadence,
        billing_model=billing_model,
        seat_count=seat_count,
        usage_units=usage_units,
        add_on_count=BALANCE.contract_default_add_on_commitment_by_segment[
            product.target_segment.value
        ]
        + get_packaging_add_on_bonus(product),
        support_tier=(
            SupportTier.WHITE_GLOVE
            if product.packaging_strategy.value == "suite"
            and product.target_segment is MarketSegment.ENTERPRISE
            else (
                SupportTier.PRIORITY
                if product.target_segment is MarketSegment.ENTERPRISE
                else SupportTier.STANDARD
            )
        ),
        annual_prepay=product.target_segment is MarketSegment.ENTERPRISE,
        discount_rate=Decimal("0.0000"),
        satisfaction=satisfaction,
        onboarding_health=clamp_int(satisfaction - 4),
        support_load=clamp_int(product.bug_level // 2),
        open_tickets=clamp_int(product.bug_level // 5, 0, 1000),
        sla_breach_risk=clamp_int(max(0, 45 - satisfaction)),
        invoice_risk=18 if product.target_segment is MarketSegment.ENTERPRISE else 26,
        failed_payment_risk=8 if contract_cadence is ContractCadence.MONTHLY else 0,
        dunning_steps=0,
        escalation_count=0,
        expansion_potential=clamp_int(product.market_fit + product.feature_count * 2),
        renewal_health=clamp_int(satisfaction - 2),
        renewal_turn=current_turn + get_contract_interval(contract_cadence),
        churn_risk=max(0, 65 - satisfaction),
    )


def _calculate_satisfaction_delta(
    product: Product,
    account: CustomerAccount,
    *,
    customer_success_bonus: int,
) -> int:
    raw_delta = (
        (product.quality - 55) // 12
        + (product.market_fit - 50) // 15
        - (product.bug_level // 22)
        - (product.technical_debt // 30)
        + (account.onboarding_health - 55) // 18
        - (account.support_load // 20)
        - (account.open_tickets // 12)
        - (account.sla_breach_risk // 24)
        - (account.invoice_risk // 30)
        - (account.failed_payment_risk // 32)
        + customer_success_bonus
    )
    if account.sla_breach_risk >= BALANCE.contract_sla_risk_threshold:
        raw_delta -= BALANCE.contract_sla_breach_satisfaction_loss
    return clamp_int(
        raw_delta,
        -BALANCE.key_account_satisfaction_delta_cap,
        BALANCE.key_account_satisfaction_delta_cap,
    )


def _apply_packaging_expansion_drift(
    account: CustomerAccount,
    product: Product,
    *,
    current_turn: int,
) -> Decimal:
    if current_turn % BALANCE.packaging_expansion_interval != 0:
        return ZERO_MONEY
    if (
        account.satisfaction < BALANCE.packaging_expansion_satisfaction_threshold
        or account.onboarding_health < BALANCE.packaging_expansion_onboarding_threshold
        or account.open_tickets > BALANCE.packaging_expansion_ticket_threshold
    ):
        return ZERO_MONEY

    revenue_before = calculate_account_recurring_revenue(account)
    package_depth_bonus = max(
        0,
        product.package_catalog_depth // BALANCE.packaging_expansion_package_depth_bonus_divisor,
    )
    add_on_depth_bonus = max(
        0,
        product.add_on_catalog_depth // BALANCE.packaging_expansion_add_on_depth_bonus_divisor,
    )
    if product.packaging_strategy.value == "suite":
        if (
            account.segment is MarketSegment.ENTERPRISE
            and account.subscription_package.value != "enterprise_suite"
        ):
            account.subscription_package = SubscriptionPackage.ENTERPRISE_SUITE
            account.support_tier = SupportTier.WHITE_GLOVE
        account.add_on_count += BALANCE.packaging_expansion_add_on_gain + add_on_depth_bonus
        if account.billing_model.value == "seat_based":
            account.seat_count += (
                BALANCE.packaging_expansion_enterprise_seat_gain + package_depth_bonus
            )
        elif account.billing_model.value == "usage_based":
            account.usage_units += BALANCE.packaging_expansion_usage_gain + (add_on_depth_bonus * 2)
    elif product.packaging_strategy.value == "modular":
        account.add_on_count += BALANCE.packaging_expansion_add_on_gain + add_on_depth_bonus
        if (
            product.package_catalog_depth >= BALANCE.package_catalog_enterprise_upgrade_threshold
            and account.subscription_package is SubscriptionPackage.STARTER
        ):
            account.subscription_package = SubscriptionPackage.GROWTH
    else:
        account.contract_value = quantize_money(
            account.contract_value
            + BALANCE.packaging_expansion_contract_gain
            + (Decimal(package_depth_bonus) * BALANCE.packaging_catalog_contract_gain_per_depth)
        )
        if account.support_tier is SupportTier.WHITE_GLOVE:
            account.support_tier = SupportTier.PRIORITY

    account.expansion_potential = clamp_int(account.expansion_potential - 4)
    revenue_after = calculate_account_recurring_revenue(account)
    if revenue_after <= revenue_before:
        return ZERO_MONEY
    return revenue_after - revenue_before


def _build_customer_summary(
    *,
    created_accounts: int,
    renewed_accounts: int,
    churned_accounts: int,
    at_risk_accounts: int,
    total_open_tickets: int,
    sla_risk_accounts: int,
) -> str:
    parts = [
        f"{created_accounts} new",
        f"{renewed_accounts} renewed",
        f"{churned_accounts} churned",
        f"{at_risk_accounts} at risk",
    ]
    if total_open_tickets > 0:
        parts.append(f"{total_open_tickets} open tickets")
    if sla_risk_accounts > 0:
        parts.append(f"{sla_risk_accounts} with SLA pressure")
    return ", ".join(parts) + "."
