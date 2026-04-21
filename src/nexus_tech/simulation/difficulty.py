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


_DIFFICULTY_PROFILES = {
    DifficultyMode.BUILDER: DifficultyProfile(
        acquisition_bonus=BALANCE.difficulty_builder_acquisition_bonus,
        churn_modifier=BALANCE.difficulty_builder_churn_modifier,
        operating_cost_multiplier=BALANCE.difficulty_builder_operating_cost_multiplier,
        burnout_modifier=BALANCE.difficulty_builder_burnout_modifier,
        score_modifier=BALANCE.difficulty_builder_score_modifier,
        summary="Lower burn and softer churn for easier portfolio growth.",
    ),
    DifficultyMode.STANDARD: DifficultyProfile(
        acquisition_bonus=BALANCE.difficulty_standard_acquisition_bonus,
        churn_modifier=BALANCE.difficulty_standard_churn_modifier,
        operating_cost_multiplier=BALANCE.difficulty_standard_operating_cost_multiplier,
        burnout_modifier=BALANCE.difficulty_standard_burnout_modifier,
        score_modifier=BALANCE.difficulty_standard_score_modifier,
        summary="Balanced difficulty intended for normal runs and demos.",
    ),
    DifficultyMode.FOUNDER: DifficultyProfile(
        acquisition_bonus=BALANCE.difficulty_founder_acquisition_bonus,
        churn_modifier=BALANCE.difficulty_founder_churn_modifier,
        operating_cost_multiplier=BALANCE.difficulty_founder_operating_cost_multiplier,
        burnout_modifier=BALANCE.difficulty_founder_burnout_modifier,
        score_modifier=BALANCE.difficulty_founder_score_modifier,
        summary="Higher burn, harsher churn, and tighter execution windows.",
    ),
}


def get_difficulty_profile(mode: DifficultyMode) -> DifficultyProfile:
    """Return the effective profile for one difficulty mode."""

    return _DIFFICULTY_PROFILES[mode]
