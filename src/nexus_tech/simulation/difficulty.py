"""Difficulty profiles used to tune run pressure without changing core rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import DifficultyMode
from nexus_tech.simulation.balance import BALANCE


@dataclass(frozen=True)
class DifficultyProfile:
    """Effective modifiers implied by one difficulty mode."""

    acquisition_bonus: int
    churn_modifier: Decimal
    operating_cost_multiplier: Decimal
    burnout_modifier: int
    score_modifier: int
    summary: str
    target_experience: str
    player_goal: str
    watch_for: str


_DIFFICULTY_PROFILES = {
    DifficultyMode.BUILDER: DifficultyProfile(
        acquisition_bonus=BALANCE.difficulty_builder_acquisition_bonus,
        churn_modifier=BALANCE.difficulty_builder_churn_modifier,
        operating_cost_multiplier=BALANCE.difficulty_builder_operating_cost_multiplier,
        burnout_modifier=BALANCE.difficulty_builder_burnout_modifier,
        score_modifier=BALANCE.difficulty_builder_score_modifier,
        summary="Lower burn and softer churn for easier portfolio growth.",
        target_experience="Safest learning curve with room to experiment.",
        player_goal="Learn the loop and reach stable product-market traction.",
        watch_for="Do not mistake easy runway for permission to ignore quality or debt.",
    ),
    DifficultyMode.STANDARD: DifficultyProfile(
        acquisition_bonus=BALANCE.difficulty_standard_acquisition_bonus,
        churn_modifier=BALANCE.difficulty_standard_churn_modifier,
        operating_cost_multiplier=BALANCE.difficulty_standard_operating_cost_multiplier,
        burnout_modifier=BALANCE.difficulty_standard_burnout_modifier,
        score_modifier=BALANCE.difficulty_standard_score_modifier,
        summary="Balanced difficulty intended for normal runs and demos.",
        target_experience="Disciplined default where systems should feel fair but demanding.",
        player_goal="Build a durable company without wasting capital or attention.",
        watch_for="Weak finance, support, or governance choices should start to compound visibly.",
    ),
    DifficultyMode.FOUNDER: DifficultyProfile(
        acquisition_bonus=BALANCE.difficulty_founder_acquisition_bonus,
        churn_modifier=BALANCE.difficulty_founder_churn_modifier,
        operating_cost_multiplier=BALANCE.difficulty_founder_operating_cost_multiplier,
        burnout_modifier=BALANCE.difficulty_founder_burnout_modifier,
        score_modifier=BALANCE.difficulty_founder_score_modifier,
        summary="Higher burn, harsher churn, and tighter execution windows.",
        target_experience="Pressure-first mode where mistakes need faster correction.",
        player_goal="Survive concentrated pressure without losing the late-game path.",
        watch_for="Cash, support backlog, and board trust can all break the run quickly.",
    ),
}


def get_difficulty_profile(mode: DifficultyMode) -> DifficultyProfile:
    """Return the effective profile for one difficulty mode."""

    return _DIFFICULTY_PROFILES[mode]
