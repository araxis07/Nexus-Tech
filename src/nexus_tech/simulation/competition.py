"""Lightweight competitor simulation and pressure modeling."""

from __future__ import annotations

from nexus_tech.domain.models import Competitor, MarketCycle, PricingTier, Product, RoadmapFocus
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.market import get_market_profile
from nexus_tech.simulation.randomness import RandomLike
from nexus_tech.simulation.roadmap import get_roadmap_profile
from nexus_tech.simulation.support import clamp_int


def create_competitor(
    *,
    name: str,
    focus_segment,
    strength: int,
    aggression: int,
    pricing_tier: PricingTier = PricingTier.STANDARD,
    active_product_count: int = 1,
) -> Competitor:
    """Create one validated competitor model."""

    return Competitor(
        name=name,
        focus_segment=focus_segment,
        strength=strength,
        aggression=aggression,
        pricing_tier=pricing_tier,
        active_product_count=active_product_count,
    )


def advance_competitors(
    competitors: list[Competitor],
    rng: RandomLike,
    *,
    market_cycle: MarketCycle,
) -> None:
    """Apply a light drift to competitor posture between turns."""

    market_profile = get_market_profile(market_cycle)
    for competitor in competitors:
        strength_drift = rng.randint(
            -BALANCE.competitor_strength_drift_max,
            BALANCE.competitor_strength_drift_max,
        )
        aggression_drift = rng.randint(
            -BALANCE.competitor_aggression_drift_max,
            BALANCE.competitor_aggression_drift_max,
        ) + market_profile.competitor_pressure_modifier
        competitor.strength = clamp_int(competitor.strength + strength_drift)
        competitor.aggression = clamp_int(competitor.aggression + aggression_drift)


def calculate_competitor_pressure(
    product: Product,
    competitors: list[Competitor],
    *,
    market_cycle: MarketCycle,
    current_turn: int,
    roadmap_focus: RoadmapFocus,
    roadmap_set_turn: int,
) -> int:
    """Estimate how much direct rival pressure one product is under."""

    roadmap_profile = get_roadmap_profile(
        roadmap_focus,
        roadmap_set_turn=roadmap_set_turn,
        current_turn=current_turn,
    )
    market_profile = get_market_profile(market_cycle)
    base_pressure = (
        BALANCE.competitor_pressure_base[product.target_segment.value]
        + market_profile.competitor_pressure_modifier
        + (current_turn // BALANCE.competitor_pressure_turn_divisor)
        + (product.user_count // BALANCE.competitor_pressure_user_divisor)
        + (1 if product.lifecycle_stage.value == "mature" else 0)
        - roadmap_profile.competitor_pressure_relief
    )
    rival_pressure = 0
    for competitor in competitors:
        if competitor.focus_segment is not product.target_segment:
            continue
        rival_pressure += BALANCE.competitor_segment_match_bonus
        rival_pressure += competitor.strength // BALANCE.competitor_strength_divisor
        rival_pressure += competitor.aggression // BALANCE.competitor_aggression_divisor
        rival_pressure += (
            max(0, competitor.active_product_count - 1)
            * BALANCE.competitor_product_count_bonus
        )
        if competitor.pricing_tier is product.pricing_tier:
            rival_pressure += BALANCE.competitor_price_match_bonus
    return clamp_int(
        base_pressure + rival_pressure,
        minimum=0,
        maximum=BALANCE.competitor_pressure_cap_total,
    )
