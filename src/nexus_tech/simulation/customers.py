"""Key-account simulation for customer depth and renewal pressure."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.constants import ZERO_MONEY
from nexus_tech.domain.models import (
    CustomerAccount,
    CustomerAccountStatus,
    LifecycleStage,
    MarketSegment,
    Product,
)
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.support import clamp_int


@dataclass(frozen=True)
class CustomerTurnSummary:
    """Customer account changes created during an end-of-turn tick."""

    account_revenue: Decimal
    created_accounts: int
    renewed_accounts: int
    churned_accounts: int
    at_risk_accounts: int
    expansion_revenue: Decimal
    summary: str


def calculate_account_revenue(accounts: list[CustomerAccount]) -> Decimal:
    """Return recurring revenue from active key accounts."""

    return quantize_money(
        sum(
            (
                account.contract_value
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
) -> CustomerTurnSummary:
    """Update account satisfaction, renewal risk, and account creation."""

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

        satisfaction_delta = _calculate_satisfaction_delta(product)
        account.satisfaction = clamp_int(
            account.satisfaction + satisfaction_delta,
            0,
            100,
        )
        if account.satisfaction >= BALANCE.key_account_satisfaction_good_threshold:
            account.churn_risk = clamp_int(
                account.churn_risk - BALANCE.key_account_churn_risk_relief,
                0,
                100,
            )
        if account.satisfaction <= BALANCE.key_account_satisfaction_bad_threshold:
            account.churn_risk = clamp_int(
                account.churn_risk + BALANCE.key_account_churn_risk_gain,
                0,
                100,
            )
        account.status = (
            CustomerAccountStatus.AT_RISK
            if account.churn_risk >= BALANCE.key_account_status_at_risk_threshold
            else CustomerAccountStatus.ACTIVE
        )

        if current_turn < account.renewal_turn:
            continue

        account.renewal_turn = current_turn + BALANCE.key_account_renewal_interval
        if account.churn_risk >= BALANCE.key_account_churn_threshold:
            account.status = CustomerAccountStatus.CHURNED
            product.user_count = max(
                0,
                product.user_count - BALANCE.key_account_renewal_churn_user_loss,
            )
            churned_accounts += 1
            continue

        renewed_accounts += 1
        if account.satisfaction >= BALANCE.key_account_satisfaction_good_threshold:
            expansion = min(
                BALANCE.key_account_expansion_contract_gain,
                Decimal(account.expansion_potential) * Decimal("3.00"),
            )
            account.contract_value = quantize_money(account.contract_value + expansion)
            expansion_revenue = quantize_money(expansion_revenue + expansion)
            account.expansion_potential = clamp_int(account.expansion_potential - 4, 0, 100)

    account_revenue = calculate_account_revenue(accounts)
    at_risk_accounts = sum(
        1 for account in accounts if account.status is CustomerAccountStatus.AT_RISK
    )
    summary = _build_customer_summary(
        created_accounts=created_accounts,
        renewed_accounts=renewed_accounts,
        churned_accounts=churned_accounts,
        at_risk_accounts=at_risk_accounts,
    )
    return CustomerTurnSummary(
        account_revenue=account_revenue,
        created_accounts=created_accounts,
        renewed_accounts=renewed_accounts,
        churned_accounts=churned_accounts,
        at_risk_accounts=at_risk_accounts,
        expansion_revenue=expansion_revenue,
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
                        max(
                            1,
                            product.user_count // BALANCE.key_account_contract_user_divisor,
                        )
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
        0,
        100,
    )
    return CustomerAccount(
        name=f"{product.target_segment.value.title()} Anchor: {product.name}",
        product_id=product.id,
        segment=product.target_segment,
        contract_value=contract_value,
        satisfaction=satisfaction,
        expansion_potential=clamp_int(product.market_fit + product.feature_count * 2, 0, 100),
        renewal_turn=current_turn + BALANCE.key_account_renewal_interval,
        churn_risk=max(0, 65 - satisfaction),
    )


def _calculate_satisfaction_delta(product: Product) -> int:
    raw_delta = (
        (product.quality - 55) // 12
        + (product.market_fit - 50) // 15
        - (product.bug_level // 22)
        - (product.technical_debt // 30)
    )
    return clamp_int(
        raw_delta,
        -BALANCE.key_account_satisfaction_delta_cap,
        BALANCE.key_account_satisfaction_delta_cap,
    )


def _build_customer_summary(
    *,
    created_accounts: int,
    renewed_accounts: int,
    churned_accounts: int,
    at_risk_accounts: int,
) -> str:
    if churned_accounts:
        return f"{churned_accounts} key account(s) churned under renewal pressure."
    if renewed_accounts:
        return f"{renewed_accounts} key account(s) renewed; {at_risk_accounts} remain at risk."
    if created_accounts:
        return f"{created_accounts} new key account(s) emerged from stronger product traction."
    if at_risk_accounts:
        return f"{at_risk_accounts} key account(s) are at risk and need attention."
    return "Key accounts remained stable this turn."
