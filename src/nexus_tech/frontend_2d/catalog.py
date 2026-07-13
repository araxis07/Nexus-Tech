"""Catalog helpers for the 2D frontend menu and new-game wizard."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nexus_tech.content.models import ScenarioDefinition
from nexus_tech.domain.models import CampaignGoalId, DifficultyMode
from nexus_tech.persistence.save_coordinator import RunArchiveSummary, SaveLoadCoordinator
from nexus_tech.simulation.campaign import list_campaign_goals
from nexus_tech.simulation.campaign_starts import CampaignStartDefinition, list_campaign_starts
from nexus_tech.simulation.difficulty import get_difficulty_profile
from nexus_tech.simulation.meta_progression import is_reward_unlocked
from nexus_tech.simulation.scenarios import get_available_scenarios

_FEATURED_SCENARIO_TRACKS = {
    "founder_journey": (1, "Learn", "Opening fundamentals"),
    "bootstrap_studio": (2, "Profit", "Cash discipline"),
    "technical_rebuild": (3, "Quality", "Product recovery"),
    "portfolio_machine": (4, "Portfolio", "Multi-product scale"),
    "debt_crunch": (5, "Debt", "Capital pressure"),
    "public_market_countdown": (6, "Endgame", "Exit readiness"),
}


@dataclass(frozen=True)
class ScenarioChoice:
    """One scenario option for the 2D new-game wizard."""

    scenario_id: str
    title: str
    description: str
    objective: str
    default_difficulty: DifficultyMode
    default_goal_id: CampaignGoalId
    track_label: str
    stage_hint: str
    featured_rank: int | None
    locked: bool
    lock_reason: str


@dataclass(frozen=True)
class CampaignStartChoice:
    """One campaign-start option for the 2D new-game wizard."""

    start_id: str
    title: str
    description: str
    turn_hint: str
    pressure_hint: str
    locked: bool
    lock_reason: str


@dataclass(frozen=True)
class DifficultyChoice:
    """One difficulty option for the 2D new-game wizard."""

    mode: DifficultyMode
    title: str
    summary: str
    watch_for: str


@dataclass(frozen=True)
class CampaignGoalChoice:
    """One campaign-goal option for the 2D new-game wizard."""

    goal_id: CampaignGoalId
    title: str
    description: str


def list_scenario_choices(db_path: Path) -> tuple[ScenarioChoice, ...]:
    """Return scenario choices with progression-lock status for the 2D wizard."""

    archives = _load_archives(db_path)
    choices = tuple(
        _build_scenario_choice(scenario, archives=archives)
        for scenario in get_available_scenarios()
    )
    return tuple(
        sorted(
            choices,
            key=lambda choice: (
                choice.featured_rank is None,
                choice.featured_rank or 999,
                choice.title.casefold(),
            ),
        )
    )


def list_campaign_start_choices(db_path: Path) -> tuple[CampaignStartChoice, ...]:
    """Return campaign-start choices with progression-lock status for the 2D wizard."""

    archives = _load_archives(db_path)
    return tuple(
        _build_campaign_start_choice(definition, archives=archives)
        for definition in list_campaign_starts()
    )


def list_difficulty_choices() -> tuple[DifficultyChoice, ...]:
    """Return all difficulty choices for the 2D wizard."""

    return tuple(
        DifficultyChoice(
            mode=mode,
            title=mode.value.replace("_", " ").title(),
            summary=get_difficulty_profile(mode).summary,
            watch_for=get_difficulty_profile(mode).watch_for,
        )
        for mode in DifficultyMode
    )


def list_campaign_goal_choices() -> tuple[CampaignGoalChoice, ...]:
    """Return all campaign-goal choices for the 2D wizard."""

    return tuple(
        CampaignGoalChoice(
            goal_id=definition.goal_id,
            title=definition.title,
            description=definition.description,
        )
        for definition in list_campaign_goals()
    )


def _build_scenario_choice(
    scenario: ScenarioDefinition,
    *,
    archives: list[RunArchiveSummary],
) -> ScenarioChoice:
    locked = not is_reward_unlocked(
        archives,
        reward_type="scenario",
        reward_id=scenario.scenario_id,
    )
    featured = _FEATURED_SCENARIO_TRACKS.get(scenario.scenario_id)
    return ScenarioChoice(
        scenario_id=scenario.scenario_id,
        title=scenario.title,
        description=scenario.description,
        objective=scenario.objective,
        default_difficulty=scenario.difficulty_mode,
        default_goal_id=scenario.campaign_goal_id,
        track_label=featured[1] if featured is not None else "Challenge",
        stage_hint=featured[2] if featured is not None else "Optional specialist scenario",
        featured_rank=featured[0] if featured is not None else None,
        locked=locked,
        lock_reason=(
            "Archive more completed runs to unlock this scenario."
            if locked
            else "Scenario unlocked."
        ),
    )


def _build_campaign_start_choice(
    definition: CampaignStartDefinition,
    *,
    archives: list[RunArchiveSummary],
) -> CampaignStartChoice:
    locked = False
    if definition.unlock_reward_id is not None and definition.unlock_reward_type is not None:
        locked = not is_reward_unlocked(
            archives,
            reward_type=definition.unlock_reward_type,
            reward_id=definition.unlock_reward_id,
        )
    return CampaignStartChoice(
        start_id=definition.start_id,
        title=definition.title,
        description=definition.description,
        turn_hint=definition.turn_hint,
        pressure_hint=definition.pressure_hint,
        locked=locked,
        lock_reason=(
            "Archive more completed runs to unlock this campaign start."
            if locked
            else "Campaign start unlocked."
        ),
    )


def _load_archives(db_path: Path) -> list[RunArchiveSummary]:
    coordinator = SaveLoadCoordinator(db_path)
    try:
        return coordinator.list_run_archives()
    except Exception:
        return []
