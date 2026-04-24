"""Pricing and packaging effects for product monetization and growth."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import (
    CustomerAccount,
    CustomerAccountStatus,
    PackagingStrategy,
    PricingTier,
    Product,
    SubscriptionPackage,
)
from nexus_tech.domain.money import format_money, quantize_money, quantize_rate
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.support import clamp_int, clamp_rate


@dataclass(frozen=True)
class PricingActionSummary:
    """Summary of changing a product pricing tier."""

    message: str


@dataclass(frozen=True)
class PricingProfile:
    """Modifiers implied by one pricing tier."""

    revenue_multiplier: Decimal
    acquisition_bonus: int
    churn_modifier: Decimal


@dataclass(frozen=True)
class PackagingProfile:
    """Modifiers implied by one packaging strategy."""

    revenue_multiplier: Decimal
    acquisition_bonus: int
    churn_modifier: Decimal
    support_cost_multiplier: Decimal
    add_on_bonus: int
    enterprise_probability_bonus: int


@dataclass(frozen=True)
class PackagingActionSummary:
    """Summary of changing a product packaging strategy."""

    message: str


@dataclass(frozen=True)
class PriceIncreaseSummary:
    """Summary of an explicit price increase decision."""

    message: str


_PRICING_PROFILES = {
    PricingTier.BUDGET: PricingProfile(
        revenue_multiplier=BALANCE.pricing_budget_revenue_multiplier,
        acquisition_bonus=BALANCE.pricing_budget_acquisition_bonus,
        churn_modifier=BALANCE.pricing_budget_churn_modifier,
    ),
    PricingTier.STANDARD: PricingProfile(
        revenue_multiplier=Decimal("1.00"),
        acquisition_bonus=0,
        churn_modifier=Decimal("0.0000"),
    ),
    PricingTier.PREMIUM: PricingProfile(
        revenue_multiplier=BALANCE.pricing_premium_revenue_multiplier,
        acquisition_bonus=BALANCE.pricing_premium_acquisition_bonus,
        churn_modifier=BALANCE.pricing_premium_churn_modifier,
    ),
}

_PACKAGING_PROFILES = {
    PackagingStrategy.STREAMLINED: PackagingProfile(
        revenue_multiplier=BALANCE.packaging_revenue_multiplier["streamlined"],
        acquisition_bonus=BALANCE.packaging_acquisition_bonus["streamlined"],
        churn_modifier=BALANCE.packaging_churn_modifier["streamlined"],
        support_cost_multiplier=BALANCE.packaging_support_cost_multiplier["streamlined"],
        add_on_bonus=BALANCE.packaging_add_on_bonus["streamlined"],
        enterprise_probability_bonus=BALANCE.packaging_enterprise_probability_bonus["streamlined"],
    ),
    PackagingStrategy.MODULAR: PackagingProfile(
        revenue_multiplier=BALANCE.packaging_revenue_multiplier["modular"],
        acquisition_bonus=BALANCE.packaging_acquisition_bonus["modular"],
        churn_modifier=BALANCE.packaging_churn_modifier["modular"],
        support_cost_multiplier=BALANCE.packaging_support_cost_multiplier["modular"],
        add_on_bonus=BALANCE.packaging_add_on_bonus["modular"],
        enterprise_probability_bonus=BALANCE.packaging_enterprise_probability_bonus["modular"],
    ),
    PackagingStrategy.SUITE: PackagingProfile(
        revenue_multiplier=BALANCE.packaging_revenue_multiplier["suite"],
        acquisition_bonus=BALANCE.packaging_acquisition_bonus["suite"],
        churn_modifier=BALANCE.packaging_churn_modifier["suite"],
        support_cost_multiplier=BALANCE.packaging_support_cost_multiplier["suite"],
        add_on_bonus=BALANCE.packaging_add_on_bonus["suite"],
        enterprise_probability_bonus=BALANCE.packaging_enterprise_probability_bonus["suite"],
    ),
}


def get_pricing_profile(pricing_tier: PricingTier) -> PricingProfile:
    """Return the effective profile for a pricing tier."""

    return _PRICING_PROFILES[pricing_tier]


def get_packaging_profile(packaging_strategy: PackagingStrategy) -> PackagingProfile:
    """Return the effective profile for a packaging strategy."""

    return _PACKAGING_PROFILES[packaging_strategy]


def calculate_effective_revenue_per_user(product: Product) -> Decimal:
    """Return revenue per user after pricing-tier modifiers."""

    pricing_profile = get_pricing_profile(product.pricing_tier)
    packaging_profile = get_packaging_profile(product.packaging_strategy)
    return quantize_money(
        product.revenue_per_user
        * pricing_profile.revenue_multiplier
        * packaging_profile.revenue_multiplier
    )


def get_pricing_acquisition_bonus(product: Product) -> int:
    """Return the acquisition bonus or penalty from the current pricing tier."""

    pricing_profile = get_pricing_profile(product.pricing_tier)
    packaging_profile = get_packaging_profile(product.packaging_strategy)
    return pricing_profile.acquisition_bonus + packaging_profile.acquisition_bonus


def get_pricing_churn_modifier(product: Product) -> Decimal:
    """Return the churn modifier from the current pricing tier."""

    pricing_profile = get_pricing_profile(product.pricing_tier)
    packaging_profile = get_packaging_profile(product.packaging_strategy)
    return quantize_rate(pricing_profile.churn_modifier + packaging_profile.churn_modifier)


def get_packaging_support_cost_multiplier(product: Product) -> Decimal:
    """Return the operating-cost multiplier created by packaging complexity."""

    return get_packaging_profile(product.packaging_strategy).support_cost_multiplier


def get_packaging_add_on_bonus(product: Product) -> int:
    """Return add-on depth created by the chosen packaging strategy."""

    return get_packaging_profile(product.packaging_strategy).add_on_bonus


def get_packaging_enterprise_probability_bonus(product: Product) -> int:
    """Return enterprise pipeline lift implied by the packaging strategy."""

    return get_packaging_profile(product.packaging_strategy).enterprise_probability_bonus


def get_default_subscription_package(product: Product) -> SubscriptionPackage:
    """Return the default contract package implied by segment and packaging posture."""

    if product.packaging_strategy is PackagingStrategy.SUITE:
        if product.target_segment.value == "enterprise":
            return SubscriptionPackage.ENTERPRISE_SUITE
        return SubscriptionPackage.GROWTH
    if product.packaging_strategy is PackagingStrategy.MODULAR:
        return SubscriptionPackage.GROWTH
    return SubscriptionPackage.STARTER


def apply_adjust_pricing(
    product: Product,
    pricing_tier: PricingTier,
) -> PricingActionSummary:
    """Change a product pricing tier and apply a light market-fit response."""

    if product.pricing_tier is pricing_tier:
        raise ValueError(f"{product.name} is already on {pricing_tier.value} pricing.")

    product.pricing_tier = pricing_tier
    fit_delta = 0

    if pricing_tier is PricingTier.BUDGET:
        fit_delta = BALANCE.pricing_budget_market_fit_bonus
    elif pricing_tier is PricingTier.PREMIUM:
        if product.quality >= BALANCE.pricing_premium_quality_threshold:
            fit_delta = BALANCE.pricing_premium_market_fit_bonus
        else:
            fit_delta = -BALANCE.pricing_premium_market_fit_penalty

    product.market_fit = clamp_int(product.market_fit + fit_delta)
    product.acquisition_rate = clamp_rate(product.acquisition_rate)
    product.churn_rate = clamp_rate(product.churn_rate)

    effective_rpu = calculate_effective_revenue_per_user(product)
    return PricingActionSummary(
        message=(
            f"{product.name} moved to {pricing_tier.value} pricing. "
            f"Effective revenue per user is now {format_money(effective_rpu)}"
            f" and market fit changed by {fit_delta:+d}."
        )
    )


def apply_set_packaging_strategy(
    product: Product,
    packaging_strategy: PackagingStrategy,
) -> PackagingActionSummary:
    """Change a product packaging strategy and re-center market fit expectations."""

    if product.packaging_strategy is packaging_strategy:
        raise ValueError(f"{product.name} is already using {packaging_strategy.value} packaging.")

    product.packaging_strategy = packaging_strategy
    fit_delta = BALANCE.packaging_market_fit_shift_by_segment[packaging_strategy.value][
        product.target_segment.value
    ]
    product.market_fit = clamp_int(product.market_fit + fit_delta)
    product.acquisition_rate = clamp_rate(product.acquisition_rate)
    product.churn_rate = clamp_rate(product.churn_rate)
    effective_rpu = calculate_effective_revenue_per_user(product)
    add_on_bonus = get_packaging_add_on_bonus(product)
    return PackagingActionSummary(
        message=(
            f"{product.name} shifted to {packaging_strategy.value} packaging. "
            f"Effective revenue per user is now {format_money(effective_rpu)}, "
            f"market fit {fit_delta:+d}, add-on depth {add_on_bonus:+d}."
        )
    )


def apply_run_price_increase(
    product: Product,
    customer_accounts: list[CustomerAccount],
) -> PriceIncreaseSummary:
    """Raise product monetization and let account tension absorb part of the shock."""

    multiplier = BALANCE.price_increase_base_multiplier
    if product.pricing_tier is PricingTier.PREMIUM:
        multiplier += BALANCE.price_increase_premium_bonus
    elif product.pricing_tier is PricingTier.BUDGET:
        multiplier += BALANCE.price_increase_budget_penalty
    if product.packaging_strategy is PackagingStrategy.SUITE:
        multiplier += BALANCE.price_increase_suite_bonus

    product.revenue_per_user = quantize_money(product.revenue_per_user * multiplier)
    market_fit_penalty = max(
        1,
        BALANCE.price_increase_market_fit_penalty_by_segment[product.target_segment.value]
        - (product.quality // BALANCE.price_increase_quality_relief_divisor)
        - BALANCE.price_increase_packaging_relief[product.packaging_strategy.value],
    )
    product.market_fit = clamp_int(product.market_fit - market_fit_penalty)
    product.churn_rate = clamp_rate(product.churn_rate + BALANCE.price_increase_churn_rate_gain)

    adjusted_accounts = 0
    for account in customer_accounts:
        if account.product_id != product.id or account.status is CustomerAccountStatus.CHURNED:
            continue
        adjusted_accounts += 1
        account.contract_value = quantize_money(
            account.contract_value * BALANCE.price_increase_account_value_multiplier
        )
        satisfaction_loss = max(
            1,
            BALANCE.price_increase_account_satisfaction_loss_by_segment[account.segment.value]
            - (1 if account.annual_prepay else 0)
            - (1 if product.packaging_strategy is PackagingStrategy.SUITE else 0),
        )
        account.satisfaction = clamp_int(account.satisfaction - satisfaction_loss)
        account.renewal_health = clamp_int(
            account.renewal_health - BALANCE.price_increase_account_renewal_health_loss
        )
        account.invoice_risk = clamp_int(
            account.invoice_risk + BALANCE.price_increase_account_invoice_risk_gain
        )
        account.churn_risk = clamp_int(
            account.churn_risk + BALANCE.price_increase_account_churn_risk_gain
        )

    return PriceIncreaseSummary(
        message=(
            f"Raised pricing on {product.name}. Base ARPU is now "
            f"{format_money(product.revenue_per_user)} with market fit "
            f"-{market_fit_penalty} and {adjusted_accounts} account(s) repriced."
        )
    )
