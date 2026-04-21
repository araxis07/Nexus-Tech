"""Late-game portfolio pressure rules for scale, saturation, and coordination drag."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import PricingTier, Product
from nexus_tech.simulation.balance import BALANCE


@dataclass(frozen=True)
class CompanyScalePressure:
    """High-level pressure created by managing a larger portfolio."""

    coordination_drag: int
    portfolio_load: int
    maintenance_multiplier: Decimal
    summary: str


@dataclass(frozen=True)
class ProductScalePressure:
    """Per-product penalties caused by portfolio scale and crowding."""

    saturation_penalty: int
    cannibalization_penalty: int
    coordination_penalty: int
    acquisition_penalty: int
    churn_modifier: Decimal
    maintenance_multiplier: Decimal
    burnout_modifier: int


def calculate_company_scale_pressure(
    products: list[Product],
    *,
    headcount: int,
    current_turn: int,
) -> CompanyScalePressure:
    """Summarize late-game portfolio drag at the company level."""

    active_products = [product for product in products if product.is_active]
    if not active_products:
        return CompanyScalePressure(
            coordination_drag=0,
            portfolio_load=0,
            maintenance_multiplier=Decimal("1.00"),
            summary="No active portfolio load.",
        )

    active_count = len(active_products)
    feature_load = sum(product.feature_count for product in active_products)
    late_turn_pressure = (
        max(
            0,
            current_turn - BALANCE.scale_late_game_turn_threshold,
        )
        // BALANCE.scale_turn_pressure_divisor
    )
    coordination_capacity = max(1, headcount * BALANCE.scale_coordination_headcount_factor)
    coordination_drag = max(0, active_count - max(1, headcount))
    coordination_drag += (
        max(0, feature_load - coordination_capacity) // BALANCE.scale_feature_pressure_divisor
    )
    coordination_drag += late_turn_pressure

    portfolio_load = max(0, active_count - 2) + max(0, feature_load - 6) // 2
    maintenance_multiplier = Decimal("1.00") + (
        Decimal(portfolio_load) / Decimal(BALANCE.scale_maintenance_multiplier_divisor)
    )

    if coordination_drag >= 4:
        summary = "Coordination drag is now a real scaling tax."
    elif portfolio_load >= 3:
        summary = "Portfolio sprawl is raising maintenance pressure."
    else:
        summary = "Scale pressure is still manageable."

    return CompanyScalePressure(
        coordination_drag=coordination_drag,
        portfolio_load=portfolio_load,
        maintenance_multiplier=maintenance_multiplier,
        summary=summary,
    )


def calculate_product_scale_pressure(
    product: Product,
    portfolio_products: list[Product],
    *,
    headcount: int,
    current_turn: int,
) -> ProductScalePressure:
    """Return acquisition, churn, and maintenance penalties from portfolio scale."""

    company_pressure = calculate_company_scale_pressure(
        portfolio_products,
        headcount=headcount,
        current_turn=current_turn,
    )
    active_products = [candidate for candidate in portfolio_products if candidate.is_active]
    adjacent_products = [
        candidate
        for candidate in active_products
        if candidate.id != product.id and candidate.target_segment is product.target_segment
    ]
    matching_price_count = sum(
        1 for candidate in adjacent_products if candidate.pricing_tier is product.pricing_tier
    )

    segment_threshold = BALANCE.scale_segment_saturation_threshold[product.target_segment.value]
    segment_divisor = BALANCE.scale_segment_saturation_divisor[product.target_segment.value]
    saturation_penalty = max(0, product.user_count - segment_threshold) // segment_divisor
    cannibalization_penalty = (
        len(adjacent_products) * BALANCE.scale_cannibalization_same_segment_penalty
    ) + (matching_price_count * BALANCE.scale_cannibalization_price_match_penalty)
    coordination_penalty = max(
        0,
        company_pressure.coordination_drag - BALANCE.scale_coordination_relief_base,
    )
    acquisition_penalty = (
        saturation_penalty + cannibalization_penalty + min(3, coordination_penalty)
    )
    churn_modifier = (
        Decimal(saturation_penalty + max(0, cannibalization_penalty - 1)) / Decimal("100")
    ) + (Decimal(min(3, coordination_penalty)) / Decimal(BALANCE.scale_coordination_churn_divisor))
    maintenance_multiplier = company_pressure.maintenance_multiplier + (
        Decimal(max(0, product.feature_count - 3))
        / Decimal(BALANCE.scale_feature_maintenance_divisor)
    )
    burnout_modifier = min(3, coordination_penalty + (len(adjacent_products) // 2))

    return ProductScalePressure(
        saturation_penalty=saturation_penalty,
        cannibalization_penalty=cannibalization_penalty,
        coordination_penalty=coordination_penalty,
        acquisition_penalty=acquisition_penalty,
        churn_modifier=churn_modifier,
        maintenance_multiplier=maintenance_multiplier,
        burnout_modifier=burnout_modifier,
    )


def is_crowded_pricing_lane(products: list[Product], pricing_tier: PricingTier) -> bool:
    """Return whether the portfolio is concentrated in one pricing posture."""

    return (
        sum(1 for product in products if product.is_active and product.pricing_tier is pricing_tier)
        >= 3
    )
