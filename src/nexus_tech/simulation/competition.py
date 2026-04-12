"""Lightweight competitor simulation and pressure modeling."""

from __future__ import annotations

from nexus_tech.domain.models import (
    Competitor,
    CompetitorMove,
    MarketCycle,
    PricingTier,
    Product,
    RoadmapFocus,
)
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
    current_move: CompetitorMove = CompetitorMove.HOLD,
    momentum: int = 50,
) -> Competitor:
    """Create one validated competitor model."""

    return Competitor(
        name=name,
        focus_segment=focus_segment,
        strength=strength,
        aggression=aggression,
        pricing_tier=pricing_tier,
        active_product_count=active_product_count,
        current_move=current_move,
        momentum=momentum,
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
        competitor.current_move = _choose_competitor_move(
            competitor,
            rng,
            market_cycle=market_cycle,
        )
        strength_drift = rng.randint(
            -BALANCE.competitor_strength_drift_max,
            BALANCE.competitor_strength_drift_max,
        )
        aggression_drift = rng.randint(
            -BALANCE.competitor_aggression_drift_max,
            BALANCE.competitor_aggression_drift_max,
        ) + market_profile.competitor_pressure_modifier
        if competitor.current_move is CompetitorMove.DISCOUNT_PUSH:
            aggression_drift += BALANCE.competitor_discount_extra_aggression
            competitor.momentum = clamp_int(
                competitor.momentum + BALANCE.competitor_momentum_change_on_discount
            )
        elif competitor.current_move is CompetitorMove.FEATURE_SPRINT:
            strength_drift += BALANCE.competitor_feature_extra_strength
            competitor.momentum = clamp_int(
                competitor.momentum + BALANCE.competitor_momentum_change_on_feature
            )
        elif competitor.current_move is CompetitorMove.RETRENCH:
            strength_drift -= BALANCE.competitor_retrench_strength_loss
            aggression_drift -= BALANCE.competitor_retrench_aggression_loss
            competitor.momentum = clamp_int(
                competitor.momentum + BALANCE.competitor_momentum_change_on_retrench
            )
        else:
            competitor.momentum = clamp_int(
                competitor.momentum + BALANCE.competitor_momentum_change_on_hold
            )
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
        rival_pressure += BALANCE.competitor_move_pressure_bonus[competitor.current_move.value]
        rival_pressure += competitor.momentum // BALANCE.competitor_momentum_divisor
    return clamp_int(
        base_pressure + rival_pressure,
        minimum=0,
        maximum=BALANCE.competitor_pressure_cap_total,
    )


def summarize_competitor_moves(competitors: list[Competitor]) -> str:
    """Build a compact summary of the most active rival postures."""

    if not competitors:
        return "No active rivals are shaping the market right now."

    ranked = sorted(
        competitors,
        key=lambda competitor: (
            competitor.aggression + competitor.strength + competitor.momentum
        ),
        reverse=True,
    )
    top_rivals = ranked[: BALANCE.competitor_move_summary_limit]
    return ", ".join(
        f"{competitor.name}: {competitor.current_move.value.replace('_', ' ')}"
        for competitor in top_rivals
    )


def _choose_competitor_move(
    competitor: Competitor,
    rng: RandomLike,
    *,
    market_cycle: MarketCycle,
) -> CompetitorMove:
    """Choose one tactical move for a competitor this turn."""

    cooling_penalty = 1 if market_cycle is MarketCycle.COOLING else 0
    frothy_bonus = 1 if market_cycle is MarketCycle.FROTHY else 0
    weights = (
        (
            CompetitorMove.HOLD,
            BALANCE.competitor_move_hold_weight + max(0, 1 - cooling_penalty),
        ),
        (
            CompetitorMove.DISCOUNT_PUSH,
            BALANCE.competitor_move_discount_weight
            + frothy_bonus
            + (1 if competitor.pricing_tier is PricingTier.BUDGET else 0),
        ),
        (
            CompetitorMove.FEATURE_SPRINT,
            BALANCE.competitor_move_feature_weight
            + frothy_bonus
            + (1 if competitor.strength >= 60 else 0),
        ),
        (
            CompetitorMove.RETRENCH,
            BALANCE.competitor_move_retrench_weight
            + cooling_penalty
            + (1 if competitor.momentum <= 40 else 0),
        ),
    )
    total_weight = sum(weight for _, weight in weights)
    roll = rng.randint(1, total_weight)
    cumulative = 0
    for move, weight in weights:
        cumulative += weight
        if roll <= cumulative:
            return move
    return CompetitorMove.HOLD
