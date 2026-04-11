"""Customer segment and competitor pressure rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import MarketSegment, Product, RoadmapFocus
from nexus_tech.domain.money import quantize_rate
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.roadmap import get_roadmap_profile
from nexus_tech.simulation.support import clamp_int


@dataclass(frozen=True)
class MarketSegmentProfile:
    """Behavioral profile for one customer segment."""

    acquisition_bonus: int
    base_churn_modifier: Decimal
    support_cost_multiplier: Decimal
    price_sensitivity_multiplier: Decimal
    market_fit_threshold: int
    quality_threshold: int
    bug_tolerance_divisor: int
    fit_bonus_divisor: int
    competitor_pressure_base: int


@dataclass(frozen=True)
class SegmentDynamics:
    """Resolved per-product segment effects for one turn."""

    acquisition_bonus: int
    churn_modifier: Decimal
    support_cost_multiplier: Decimal
    competitor_pressure: int


_SEGMENT_PROFILES = {
    segment: MarketSegmentProfile(
        acquisition_bonus=BALANCE.segment_base_acquisition_bonus[segment.value],
        base_churn_modifier=BALANCE.segment_base_churn_modifier[segment.value],
        support_cost_multiplier=BALANCE.segment_support_cost_multiplier[segment.value],
        price_sensitivity_multiplier=BALANCE.segment_price_sensitivity_multiplier[segment.value],
        market_fit_threshold=BALANCE.segment_market_fit_threshold[segment.value],
        quality_threshold=BALANCE.segment_quality_threshold[segment.value],
        bug_tolerance_divisor=BALANCE.segment_bug_tolerance_divisor[segment.value],
        fit_bonus_divisor=BALANCE.segment_fit_bonus_divisor[segment.value],
        competitor_pressure_base=BALANCE.competitor_pressure_base[segment.value],
    )
    for segment in MarketSegment
}


def get_market_segment_profile(segment: MarketSegment) -> MarketSegmentProfile:
    """Return the static profile for one customer segment."""

    return _SEGMENT_PROFILES[segment]


def calculate_competitor_pressure(
    product: Product,
    *,
    current_turn: int,
    roadmap_focus: RoadmapFocus,
    roadmap_set_turn: int,
) -> int:
    """Estimate how much market competition is pressing on a product this turn."""

    profile = get_market_segment_profile(product.target_segment)
    roadmap_profile = get_roadmap_profile(
        roadmap_focus,
        roadmap_set_turn=roadmap_set_turn,
        current_turn=current_turn,
    )
    pressure = (
        profile.competitor_pressure_base
        + (current_turn // BALANCE.competitor_pressure_turn_divisor)
        + (product.user_count // BALANCE.competitor_pressure_user_divisor)
        + (1 if product.lifecycle_stage.value == "mature" else 0)
        - roadmap_profile.competitor_pressure_relief
    )
    return clamp_int(pressure, minimum=0, maximum=BALANCE.competitor_pressure_cap)


def resolve_segment_dynamics(
    product: Product,
    *,
    current_turn: int,
    roadmap_focus: RoadmapFocus,
    roadmap_set_turn: int,
    pricing_churn_modifier: Decimal,
) -> SegmentDynamics:
    """Resolve segment-specific acquisition, churn, and competitive pressure."""

    profile = get_market_segment_profile(product.target_segment)
    competitor_pressure = calculate_competitor_pressure(
        product,
        current_turn=current_turn,
        roadmap_focus=roadmap_focus,
        roadmap_set_turn=roadmap_set_turn,
    )

    fit_bonus = (
        max(0, product.market_fit - profile.market_fit_threshold) // profile.fit_bonus_divisor
    )
    quality_bonus = max(0, product.quality - profile.quality_threshold) // 12
    bug_penalty = product.bug_level // profile.bug_tolerance_divisor
    price_modifier = quantize_rate(pricing_churn_modifier * profile.price_sensitivity_multiplier)
    churn_modifier = clamp_rate(
        max(
            Decimal("-0.0500"),
            min(
                Decimal("0.1500"),
                profile.base_churn_modifier
                + price_modifier
                + quantize_rate(
                    Decimal(competitor_pressure)
                    / Decimal(BALANCE.competitor_pressure_churn_modifier_divisor)
                ),
            ),
        )
    )
    acquisition_bonus = (
        profile.acquisition_bonus
        + fit_bonus
        + quality_bonus
        - bug_penalty
        - (competitor_pressure // BALANCE.competitor_pressure_growth_penalty_divisor)
    )
    return SegmentDynamics(
        acquisition_bonus=acquisition_bonus,
        churn_modifier=churn_modifier,
        support_cost_multiplier=profile.support_cost_multiplier,
        competitor_pressure=competitor_pressure,
    )


def clamp_rate(value: Decimal) -> Decimal:
    """Clamp a Decimal rate to a safe signed range for local segment modifiers."""

    return quantize_rate(max(Decimal("-0.0500"), min(Decimal("0.1500"), value)))
