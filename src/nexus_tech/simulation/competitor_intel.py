"""Competitor intelligence history generated from rival moves."""

from __future__ import annotations

from nexus_tech.domain.models import Competitor, CompetitorIntelEntry, GameState
from nexus_tech.simulation.balance import BALANCE


def record_competitor_intel(
    state: GameState,
    previous_competitors: list[Competitor],
    *,
    current_turn: int,
) -> None:
    """Append compact intel entries when rival posture changes."""

    previous_by_id = {competitor.id: competitor for competitor in previous_competitors}
    for competitor in state.competitors:
        previous = previous_by_id.get(competitor.id)
        if previous is None:
            continue
        if competitor.current_move is previous.current_move and competitor.momentum < 72:
            continue
        state.competitor_intel.append(
            CompetitorIntelEntry(
                turn=current_turn,
                competitor_name=competitor.name,
                move=competitor.current_move,
                summary=(
                    f"{competitor.name} shifted to {competitor.current_move.value} "
                    f"with momentum {competitor.momentum}."
                ),
            )
        )

    if len(state.competitor_intel) > BALANCE.competitor_intel_limit:
        state.competitor_intel = state.competitor_intel[-BALANCE.competitor_intel_limit :]
