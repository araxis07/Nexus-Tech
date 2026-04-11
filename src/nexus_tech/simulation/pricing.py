"""Pricing-tier effects for product monetization and growth."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import PricingTier, Product
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


def get_pricing_profile(pricing_tier: PricingTier) -> PricingProfile:
    """Return the effective profile for a pricing tier."""

    return _PRICING_PROFILES[pricing_tier]


def calculate_effective_revenue_per_user(product: Product) -> Decimal:
    """Return revenue per user after pricing-tier modifiers."""

    profile = get_pricing_profile(product.pricing_tier)
    return quantize_money(product.revenue_per_user * profile.revenue_multiplier)


def get_pricing_acquisition_bonus(product: Product) -> int:
    """Return the acquisition bonus or penalty from the current pricing tier."""

    return get_pricing_profile(product.pricing_tier).acquisition_bonus


def get_pricing_churn_modifier(product: Product) -> Decimal:
    """Return the churn modifier from the current pricing tier."""

    return quantize_rate(get_pricing_profile(product.pricing_tier).churn_modifier)


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
