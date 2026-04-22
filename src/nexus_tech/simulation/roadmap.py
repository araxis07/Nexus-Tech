"""Quarter-scale roadmap planning profiles and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.constants import ZERO_MONEY
from nexus_tech.domain.models import RoadmapFocus
from nexus_tech.simulation.balance import BALANCE


@dataclass(frozen=True)
class RoadmapProfile:
    """Gameplay modifiers implied by one roadmap focus."""

    quality_bonus: int = 0
    market_fit_bonus: int = 0
    debt_reduction_bonus: int = 0
    acquisition_bonus: int = 0
    reputation_bonus: int = 0
    feature_risk_modifier: int = 0
    operating_cost_modifier: Decimal = ZERO_MONEY
    competitor_pressure_relief: int = 0
    summary: str = ""


_BALANCED_PROFILE = RoadmapProfile(
    summary="Keep the company steady with balanced execution across the portfolio."
)

_ROADMAP_PROFILES = {
    RoadmapFocus.BALANCED_EXECUTION: _BALANCED_PROFILE,
    RoadmapFocus.GROWTH_PUSH: RoadmapProfile(
        acquisition_bonus=BALANCE.roadmap_growth_acquisition_bonus,
        feature_risk_modifier=BALANCE.roadmap_growth_feature_risk_modifier,
        operating_cost_modifier=BALANCE.roadmap_growth_operating_cost_modifier,
        competitor_pressure_relief=BALANCE.roadmap_growth_competitor_relief,
        summary="Push growth, accept a little more delivery risk, and spend harder.",
    ),
    RoadmapFocus.PLATFORM_REBUILD: RoadmapProfile(
        quality_bonus=BALANCE.roadmap_platform_quality_bonus,
        debt_reduction_bonus=BALANCE.roadmap_platform_debt_bonus,
        operating_cost_modifier=BALANCE.roadmap_platform_operating_cost_modifier,
        competitor_pressure_relief=BALANCE.roadmap_platform_competitor_relief,
        summary="Slow down feature pressure and rebuild quality, reliability, and maintainability.",
    ),
    RoadmapFocus.PREMIUM_EXPANSION: RoadmapProfile(
        quality_bonus=BALANCE.roadmap_premium_quality_bonus,
        market_fit_bonus=BALANCE.roadmap_premium_market_fit_bonus,
        reputation_bonus=BALANCE.roadmap_premium_reputation_bonus,
        acquisition_bonus=BALANCE.roadmap_premium_acquisition_penalty,
        competitor_pressure_relief=BALANCE.roadmap_premium_competitor_relief,
        summary="Move the business up-market and trade raw volume for stronger product quality.",
    ),
    RoadmapFocus.PORTFOLIO_CONSOLIDATION: RoadmapProfile(
        debt_reduction_bonus=BALANCE.roadmap_portfolio_efficiency_bonus,
        acquisition_bonus=BALANCE.roadmap_portfolio_acquisition_penalty,
        operating_cost_modifier=BALANCE.roadmap_portfolio_operating_cost_modifier,
        competitor_pressure_relief=BALANCE.roadmap_portfolio_competitor_relief,
        summary="Tighten the portfolio, reduce waste, and protect operating leverage.",
    ),
    RoadmapFocus.AI_TRUST_PROGRAM: RoadmapProfile(
        quality_bonus=BALANCE.roadmap_ai_trust_quality_bonus,
        market_fit_bonus=BALANCE.roadmap_ai_trust_market_fit_bonus,
        debt_reduction_bonus=BALANCE.roadmap_ai_trust_debt_bonus,
        reputation_bonus=BALANCE.roadmap_ai_trust_reputation_bonus,
        operating_cost_modifier=BALANCE.roadmap_ai_trust_operating_cost_modifier,
        competitor_pressure_relief=BALANCE.roadmap_ai_trust_competitor_relief,
        summary="Invest in trust, controls, and credible AI governance for regulated buyers.",
    ),
    RoadmapFocus.COMMUNITY_GROWTH: RoadmapProfile(
        market_fit_bonus=BALANCE.roadmap_community_growth_market_fit_bonus,
        acquisition_bonus=BALANCE.roadmap_community_growth_acquisition_bonus,
        reputation_bonus=BALANCE.roadmap_community_growth_reputation_bonus,
        feature_risk_modifier=BALANCE.roadmap_community_growth_feature_risk_modifier,
        operating_cost_modifier=BALANCE.roadmap_community_growth_operating_cost_modifier,
        summary="Build community-led distribution while accepting some feature delivery noise.",
    ),
    RoadmapFocus.ENTERPRISE_SALES_PUSH: RoadmapProfile(
        quality_bonus=BALANCE.roadmap_enterprise_sales_quality_bonus,
        market_fit_bonus=BALANCE.roadmap_enterprise_sales_market_fit_bonus,
        acquisition_bonus=BALANCE.roadmap_enterprise_sales_acquisition_bonus,
        reputation_bonus=BALANCE.roadmap_enterprise_sales_reputation_bonus,
        operating_cost_modifier=BALANCE.roadmap_enterprise_sales_operating_cost_modifier,
        competitor_pressure_relief=BALANCE.roadmap_enterprise_sales_competitor_relief,
        summary="Push enterprise sales motions with higher cost and stronger buyer fit.",
    ),
}


def get_effective_roadmap_focus(
    roadmap_focus: RoadmapFocus,
    *,
    roadmap_set_turn: int,
    current_turn: int,
) -> RoadmapFocus:
    """Return the active roadmap focus, falling back to balanced if the quarter expired."""

    if is_roadmap_due(roadmap_set_turn=roadmap_set_turn, current_turn=current_turn):
        return RoadmapFocus.BALANCED_EXECUTION
    return roadmap_focus


def get_roadmap_profile(
    roadmap_focus: RoadmapFocus,
    *,
    roadmap_set_turn: int,
    current_turn: int,
) -> RoadmapProfile:
    """Return the currently active roadmap profile."""

    effective_focus = get_effective_roadmap_focus(
        roadmap_focus,
        roadmap_set_turn=roadmap_set_turn,
        current_turn=current_turn,
    )
    return _ROADMAP_PROFILES[effective_focus]


def is_roadmap_due(*, roadmap_set_turn: int, current_turn: int) -> bool:
    """Return whether the current roadmap quarter has expired."""

    return (current_turn - roadmap_set_turn) >= BALANCE.roadmap_duration_turns


def get_roadmap_turns_remaining(*, roadmap_set_turn: int, current_turn: int) -> int:
    """Return how many turns remain before the roadmap goes stale."""

    remaining = BALANCE.roadmap_duration_turns - (current_turn - roadmap_set_turn)
    return max(0, remaining)
