"""Pure completed-run presentation policy for the lightweight 2D frontend."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.domain.models import GameState
from nexus_tech.domain.money import format_money
from nexus_tech.frontend_2d.viewmodels import GameViewModel

__all__ = [
    "OutcomeMetricViewModel",
    "OutcomeOverlayViewModel",
    "build_outcome_overlay_view_model",
]


@dataclass(frozen=True)
class OutcomeMetricViewModel:
    """One compact run fact shown before the player archives an ending."""

    label: str
    value: str
    tone: str


@dataclass(frozen=True)
class OutcomeOverlayViewModel:
    """Readable completion context for the completed-run outcome overlay."""

    title: str
    eyebrow: str
    detail: str
    progression: str
    metrics: tuple[OutcomeMetricViewModel, ...]


def build_outcome_overlay_view_model(
    state: GameState,
    game_view_model: GameViewModel,
    *,
    archive_saved: bool,
) -> OutcomeOverlayViewModel:
    """Build concise ending context without changing the completed run."""

    if archive_saved:
        title = "Archive Recorded"
        eyebrow = "ARCHIVED ENDING"
        detail = (
            "This ending now counts toward progression and Route Atlas. "
            "Return to the title menu when the review is complete."
        )
        progression = "Archive recorded. Open Progress from the title menu for the next route."
    elif state.victory_achieved:
        title = "Victory Achieved"
        eyebrow = "VICTORY OUTCOME"
        detail = (
            state.victory_reason or state.exit_summary or "The company reached a winning end state."
        )
        progression = (
            f"Journey {game_view_model.run_journey.step_label}: Review why, then "
            "Save & Archive to keep progression."
        )
    else:
        title = "Company Shutdown"
        eyebrow = "SHUTDOWN CAUSE"
        detail = (
            f"Cash closed at {format_money(state.company.cash_on_hand)}. "
            "Runway exhausted before the next control move could land."
            if state.company.cash_on_hand < 0
            else "The company can no longer continue. Open Review for the ranked causes."
        )
        progression = (
            f"Journey {game_view_model.run_journey.step_label}: Review why, then "
            "Save & Archive to keep progression."
        )

    return OutcomeOverlayViewModel(
        title=title,
        eyebrow=eyebrow,
        detail=detail,
        progression=progression,
        metrics=(
            OutcomeMetricViewModel(
                label="CASH",
                value=format_money(state.company.cash_on_hand),
                tone="danger" if state.company.cash_on_hand < 0 else "success",
            ),
            OutcomeMetricViewModel(
                label="SCORE",
                value=game_view_model.score_label,
                tone="info",
            ),
            OutcomeMetricViewModel(
                label="LAST TURN",
                value=game_view_model.turn_label,
                tone="warning" if state.company.game_over else "info",
            ),
        ),
    )
