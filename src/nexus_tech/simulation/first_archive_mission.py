"""A save-compatible journey from the opening turn to the first archive."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from nexus_tech.domain.models import GameState
from nexus_tech.simulation.action_catalog import get_action_label
from nexus_tech.simulation.campaign_decisions import get_campaign_choice_label
from nexus_tech.simulation.campaign_journey import CampaignActId, get_campaign_journey
from nexus_tech.simulation.opening_guide import build_guided_opening


class FirstArchiveStepId(StrEnum):
    """Stable identifiers for the six first-run journey milestones."""

    GUIDED_OPENING = "guided_opening"
    COMMITMENT = "commitment"
    CONSEQUENCE = "consequence"
    ENDGAME = "endgame"
    FINISH_RUN = "finish_run"
    ARCHIVE_RUN = "archive_run"


@dataclass(frozen=True)
class FirstArchiveStep:
    """One milestone in the first completed-and-archived run."""

    step_id: FirstArchiveStepId
    title: str
    detail: str
    complete: bool


@dataclass(frozen=True)
class FirstArchiveMission:
    """Player-facing progress derived entirely from existing state and archives."""

    steps: tuple[FirstArchiveStep, ...]
    current_step: FirstArchiveStep
    current_step_number: int
    completed_steps: int
    next_action: str

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def complete(self) -> bool:
        return self.completed_steps == self.total_steps

    @property
    def progress(self) -> float:
        if not self.steps:
            return 1.0
        return self.completed_steps / len(self.steps)

    @property
    def step_label(self) -> str:
        return f"{self.current_step_number}/{self.total_steps}"

    @property
    def progress_label(self) -> str:
        return f"{self.completed_steps}/{self.total_steps} complete"

    @property
    def summary(self) -> str:
        if self.complete:
            return "First archive complete. Open Progress to choose the next campaign route."
        return f"Step {self.step_label}: {self.current_step.title}. {self.current_step.detail}"


def build_first_archive_mission(
    state: GameState,
    *,
    archive_count: int = 0,
) -> FirstArchiveMission:
    """Derive one continuous first-run journey without adding save fields."""

    terminal = state.victory_achieved or state.company.game_over
    turn = state.company.current_turn
    featured = get_campaign_journey(state.scenario_id) is not None
    commitment_choice = get_campaign_choice_label(state, CampaignActId.COMMITMENT)
    consequence_choice = get_campaign_choice_label(state, CampaignActId.CONSEQUENCE)
    archive_complete = archive_count > 0

    commitment_complete = (
        archive_complete or terminal or (commitment_choice is not None if featured else turn >= 10)
    )
    consequence_complete = (
        archive_complete or terminal or (consequence_choice is not None if featured else turn >= 15)
    )
    steps = (
        FirstArchiveStep(
            FirstArchiveStepId.GUIDED_OPENING,
            "Guided Opening",
            "Build one focused operating loop and reach Turn 5.",
            archive_complete or terminal or turn >= 5,
        ),
        FirstArchiveStep(
            FirstArchiveStepId.COMMITMENT,
            "Commitment",
            (
                "Resolve the Act 2 campaign choice."
                if featured
                else "Carry the company through the Growth chapter."
            ),
            commitment_complete,
        ),
        FirstArchiveStep(
            FirstArchiveStepId.CONSEQUENCE,
            "Consequence",
            (
                "Resolve the Act 3 campaign choice."
                if featured
                else "Carry the company through the Scale chapter."
            ),
            consequence_complete,
        ),
        FirstArchiveStep(
            FirstArchiveStepId.ENDGAME,
            "Enter Endgame",
            "Reach Turn 15 or a terminal outcome with the company intact.",
            archive_complete or terminal or turn >= 15,
        ),
        FirstArchiveStep(
            FirstArchiveStepId.FINISH_RUN,
            "Finish the Run",
            "Reach victory or a company shutdown to produce a final review.",
            archive_complete or terminal,
        ),
        FirstArchiveStep(
            FirstArchiveStepId.ARCHIVE_RUN,
            "Save & Archive",
            "Record the ending so progression and Route Atlas can use it.",
            archive_complete,
        ),
    )
    completed_steps = sum(step.complete for step in steps)
    current_step_number, current_step = next(
        ((index, step) for index, step in enumerate(steps, start=1) if not step.complete),
        (len(steps), steps[-1]),
    )
    return FirstArchiveMission(
        steps=steps,
        current_step=current_step,
        current_step_number=current_step_number,
        completed_steps=completed_steps,
        next_action=_next_archive_action(
            state,
            current_step.step_id,
            featured=featured,
            complete=archive_complete,
        ),
    )


def _next_archive_action(
    state: GameState,
    step_id: FirstArchiveStepId,
    *,
    featured: bool,
    complete: bool,
) -> str:
    if complete:
        return "Open Progress and choose the next unexplored route."
    if step_id is FirstArchiveStepId.GUIDED_OPENING:
        opening = build_guided_opening(state)
        return f"Open Coach and use {get_action_label(opening.current_command)} next."
    if step_id is FirstArchiveStepId.COMMITMENT:
        return (
            "Advance to the Act 2 event, then choose the pressure you want to carry."
            if featured
            else "Advance through Growth while protecting runway and product health."
        )
    if step_id is FirstArchiveStepId.CONSEQUENCE:
        return (
            "Advance to the Act 3 event, then choose how the company will finish."
            if featured
            else "Advance through Scale while keeping the exit gates reachable."
        )
    if step_id is FirstArchiveStepId.ENDGAME:
        return "Reach Turn 15 while protecting cash, trust, and the chosen exit path."
    if step_id is FirstArchiveStepId.FINISH_RUN:
        return "Clear the exit gates or survive until the run reaches a terminal outcome."
    return "Open Review Run, then choose Save & Archive or press S."
