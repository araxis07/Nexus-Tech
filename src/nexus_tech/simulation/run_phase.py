"""Readable run phases for pacing, onboarding, and late-game handoff."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RunPhaseId(StrEnum):
    """Four stable chapters in a standard company run."""

    OPENING = "opening"
    GROWTH = "growth"
    SCALE = "scale"
    ENDGAME = "endgame"


@dataclass(frozen=True)
class RunPhase:
    """Player-facing chapter metadata for the current turn."""

    phase_id: RunPhaseId
    title: str
    turn_window: str
    objective: str
    progress: float


def get_run_phase(turn: int) -> RunPhase:
    """Return the run chapter and progress for a one-based turn number."""

    if turn <= 4:
        return RunPhase(
            phase_id=RunPhaseId.OPENING,
            title="Opening",
            turn_window="Turns 1-4",
            objective="Build one healthy product loop without losing runway.",
            progress=_phase_progress(turn, 1, 4),
        )
    if turn <= 9:
        return RunPhase(
            phase_id=RunPhaseId.GROWTH,
            title="Growth",
            turn_window="Turns 5-9",
            objective="Choose a market position and turn traction into repeatable growth.",
            progress=_phase_progress(turn, 5, 9),
        )
    if turn <= 14:
        return RunPhase(
            phase_id=RunPhaseId.SCALE,
            title="Scale",
            turn_window="Turns 10-14",
            objective="Control team, customer, support, and board pressure while scaling.",
            progress=_phase_progress(turn, 10, 14),
        )
    return RunPhase(
        phase_id=RunPhaseId.ENDGAME,
        title="Endgame",
        turn_window="Turn 15+",
        objective="Commit to an exit path and survive the final operating pressure.",
        progress=min(1.0, 0.2 + ((turn - 15) * 0.2)),
    )


def _phase_progress(turn: int, start: int, end: int) -> float:
    return min(1.0, max(0.0, (turn - start + 1) / (end - start + 1)))
