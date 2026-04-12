"""Customer segment and competitor pressure rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import (
    Competitor,
    MarketCycle,
    MarketSegment,
    Product,
    RoadmapFocus,
)
from nexus_tech.domain.money import quantize_rate
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.competition import (
    calculate_competitor_pressure as calculate_live_competitor_pressure,
)
from nexus_tech.simulation.market import get_market_profile


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
    competitors: list[Competitor] | None = None,
    *,
    market_cycle: MarketCycle = MarketCycle.STEADY,
    current_turn: int,
    roadmap_focus: RoadmapFocus,
    roadmap_set_turn: int,
) -> int:
    """Estimate how much market competition is pressing on a product this turn."""

    return calculate_live_competitor_pressure(
        product,
        competitors or [],
        market_cycle=market_cycle,
        current_turn=current_turn,
        roadmap_focus=roadmap_focus,
        roadmap_set_turn=roadmap_set_turn,
    )


def resolve_segment_dynamics(
    product: Product,
    competitors: list[Competitor] | None = None,
    *,
    market_cycle: MarketCycle = MarketCycle.STEADY,
    current_turn: int,
    roadmap_focus: RoadmapFocus,
    roadmap_set_turn: int,
    pricing_churn_modifier: Decimal,
) -> SegmentDynamics:
    """Resolve segment-specific acquisition, churn, and competitive pressure."""

    profile = get_market_segment_profile(product.target_segment)
    market_profile = get_market_profile(market_cycle)
    competitor_pressure = calculate_competitor_pressure(
        product,
        competitors or [],
        market_cycle=market_cycle,
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
                + market_profile.churn_modifier
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
        + market_profile.acquisition_bonus
        + market_profile.segment_bonus[product.target_segment]
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
