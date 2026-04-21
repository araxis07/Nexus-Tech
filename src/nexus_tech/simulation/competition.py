"""Lightweight competitor simulation and pressure modeling."""

from __future__ import annotations

from nexus_tech.domain.models import (
    Competitor,
    CompetitorMove,
    MarketCycle,
    MarketSegment,
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
    archetype_id: str | None = None,
    focus_segment,
    strength: int,
    aggression: int,
    pricing_tier: PricingTier = PricingTier.STANDARD,
    active_product_count: int = 1,
    current_move: CompetitorMove = CompetitorMove.HOLD,
    momentum: int = 50,
    funding_level: int = 0,
) -> Competitor:
    """Create one validated competitor model."""

    return Competitor(
        name=name,
        archetype_id=archetype_id,
        focus_segment=focus_segment,
        strength=strength,
        aggression=aggression,
        pricing_tier=pricing_tier,
        active_product_count=active_product_count,
        current_move=current_move,
        momentum=momentum,
        funding_level=funding_level,
    )


def advance_competitors(
    competitors: list[Competitor],
    rng: RandomLike,
    *,
    market_cycle: MarketCycle,
    portfolio_products: list[Product] | None = None,
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
        aggression_drift = (
            rng.randint(
                -BALANCE.competitor_aggression_drift_max,
                BALANCE.competitor_aggression_drift_max,
            )
            + market_profile.competitor_pressure_modifier
        )
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
        _apply_competitor_move_side_effects(
            competitor,
            portfolio_products=portfolio_products or [],
        )


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
        rival_pressure += BALANCE.competitor_archetype_pressure_bonus.get(
            competitor.archetype_id or "",
            0,
        )
        rival_pressure += competitor.strength // BALANCE.competitor_strength_divisor
        rival_pressure += competitor.aggression // BALANCE.competitor_aggression_divisor
        rival_pressure += (
            max(0, competitor.active_product_count - 1) * BALANCE.competitor_product_count_bonus
        )
        if competitor.pricing_tier is product.pricing_tier:
            rival_pressure += BALANCE.competitor_price_match_bonus
        rival_pressure += BALANCE.competitor_move_pressure_bonus[competitor.current_move.value]
        rival_pressure += competitor.momentum // BALANCE.competitor_momentum_divisor
        rival_pressure += competitor.funding_level
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
        key=lambda competitor: competitor.aggression + competitor.strength + competitor.momentum,
        reverse=True,
    )
    top_rivals = ranked[: BALANCE.competitor_move_summary_limit]
    return ", ".join(
        (
            f"{competitor.name}: {competitor.current_move.value.replace('_', ' ')} / "
            f"{competitor.focus_segment.value} / {competitor.pricing_tier.value} / "
            f"{competitor.active_product_count} product(s)"
        )
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
    move_bias = BALANCE.competitor_archetype_move_bias.get(competitor.archetype_id or "", {})
    weights = (
        (
            CompetitorMove.HOLD,
            _adjust_move_weight(
                BALANCE.competitor_move_hold_weight + max(0, 1 - cooling_penalty),
                move_bias.get(CompetitorMove.HOLD.value, 0),
            ),
        ),
        (
            CompetitorMove.DISCOUNT_PUSH,
            _adjust_move_weight(
                BALANCE.competitor_move_discount_weight
                + frothy_bonus
                + (1 if competitor.pricing_tier is PricingTier.BUDGET else 0),
                move_bias.get(CompetitorMove.DISCOUNT_PUSH.value, 0),
            ),
        ),
        (
            CompetitorMove.FEATURE_SPRINT,
            _adjust_move_weight(
                BALANCE.competitor_move_feature_weight
                + frothy_bonus
                + (1 if competitor.strength >= 60 else 0),
                move_bias.get(CompetitorMove.FEATURE_SPRINT.value, 0),
            ),
        ),
        (
            CompetitorMove.RETRENCH,
            _adjust_move_weight(
                BALANCE.competitor_move_retrench_weight
                + cooling_penalty
                + (1 if competitor.momentum <= 40 else 0),
                move_bias.get(CompetitorMove.RETRENCH.value, 0),
            ),
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


def _apply_competitor_move_side_effects(
    competitor: Competitor,
    *,
    portfolio_products: list[Product],
) -> None:
    """Let rival moves reshape product count and pricing posture over time."""

    if competitor.current_move is CompetitorMove.DISCOUNT_PUSH:
        competitor.pricing_tier = PricingTier.BUDGET
        if competitor.momentum >= BALANCE.competitor_discount_expansion_momentum_threshold:
            competitor.active_product_count = min(6, competitor.active_product_count + 1)
        if competitor.archetype_id == "price_raider":
            competitor.active_product_count = min(6, competitor.active_product_count + 1)
            competitor.aggression = clamp_int(competitor.aggression + 1)
        if competitor.archetype_id in {"channel_aggregator", "ecosystem_broker"}:
            competitor.strength = clamp_int(competitor.strength + 1)
        _maybe_pivot_focus_segment(competitor, portfolio_products)
        _maybe_raise_competitor_funding(competitor)
        return

    if competitor.current_move is CompetitorMove.FEATURE_SPRINT:
        if competitor.momentum >= BALANCE.competitor_feature_expansion_momentum_threshold:
            competitor.active_product_count = min(6, competitor.active_product_count + 1)
        if competitor.archetype_id in {"feature_blitzer", "ai_fast_follower"}:
            competitor.active_product_count = min(6, competitor.active_product_count + 1)
        if competitor.archetype_id == "vertical_specialist":
            competitor.strength = clamp_int(competitor.strength + 1)
        if competitor.focus_segment.value == "enterprise":
            competitor.pricing_tier = PricingTier.PREMIUM
        else:
            competitor.pricing_tier = PricingTier.STANDARD
        _maybe_pivot_focus_segment(competitor, portfolio_products)
        _maybe_raise_competitor_funding(competitor)
        return

    if competitor.current_move is CompetitorMove.RETRENCH:
        competitor.active_product_count = max(1, competitor.active_product_count - 1)
        if competitor.focus_segment.value in {"enterprise", "smb"}:
            competitor.pricing_tier = PricingTier.PREMIUM
        else:
            competitor.pricing_tier = PricingTier.STANDARD
        if competitor.archetype_id == "retreating_incumbent":
            competitor.strength = clamp_int(competitor.strength - 1)
        competitor.funding_level = max(0, competitor.funding_level - 1)
        return

    if competitor.archetype_id in {"platform_bulwark", "trust_monolith", "governance_giant"}:
        competitor.pricing_tier = PricingTier.PREMIUM
        competitor.strength = clamp_int(competitor.strength + 1)
    elif competitor.archetype_id == "niche_defender":
        competitor.strength = clamp_int(competitor.strength + 1)
        competitor.aggression = clamp_int(competitor.aggression - 1)
    if competitor.pricing_tier is PricingTier.BUDGET and competitor.momentum <= 45:
        competitor.pricing_tier = PricingTier.STANDARD
    _maybe_raise_competitor_funding(competitor)


def _maybe_raise_competitor_funding(competitor: Competitor) -> None:
    """Let strong rivals accumulate capital pressure over time."""

    if competitor.momentum + competitor.aggression + competitor.strength < 190:
        return
    competitor.funding_level = min(5, competitor.funding_level + 1)
    competitor.strength = clamp_int(competitor.strength + 1)


def _maybe_pivot_focus_segment(
    competitor: Competitor,
    portfolio_products: list[Product],
) -> None:
    """Let rivals chase the segment where the player has visible traction."""

    hottest_segment = _get_hottest_segment(portfolio_products)
    if hottest_segment is None or hottest_segment is competitor.focus_segment:
        return
    pivot_threshold = (
        BALANCE.competitor_focus_pivot_threshold
        + BALANCE.competitor_archetype_pivot_threshold_bonus.get(competitor.archetype_id or "", 0)
    )
    if competitor.momentum < pivot_threshold:
        return

    competitor.focus_segment = hottest_segment
    competitor.strength = clamp_int(
        competitor.strength + BALANCE.competitor_focus_pivot_bonus_strength,
    )
    competitor.aggression = clamp_int(
        competitor.aggression + BALANCE.competitor_focus_pivot_bonus_aggression,
    )


def _adjust_move_weight(base_weight: int, bias: int) -> int:
    """Keep competitor move selection valid after archetype bias is applied."""

    return max(1, base_weight + bias)


def _get_hottest_segment(products: list[Product]) -> MarketSegment | None:
    active_products = [product for product in products if product.is_active]
    if not active_products:
        return None
    return max(
        active_products,
        key=lambda product: product.user_count + product.market_fit + product.quality,
    ).target_segment
