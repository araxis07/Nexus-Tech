from __future__ import annotations

from nexus_tech.domain.models import EventCategory, EventHistoryEntry, GameState
from nexus_tech.simulation.engine import create_new_game
from nexus_tech.simulation.first_archive_mission import (
    FirstArchiveStepId,
    build_first_archive_mission,
)


def _founder_state() -> GameState:
    return create_new_game(
        "NEXUS TECH",
        "Nexus One",
        scenario_id="founder_journey",
    )


def _record_campaign_choice(
    state: GameState,
    *,
    event_id: str,
    option_id: str,
    option_label: str,
    turn: int,
) -> None:
    state.event_history.append(
        EventHistoryEntry(
            event_id=event_id,
            category=EventCategory.MARKET_OPPORTUNITY,
            title="Campaign Decision",
            triggered_turn=turn,
            resolved_turn=turn,
            chain_id="campaign:founder_journey",
            chain_stage=1 if turn == 4 else 2,
            selected_option_id=option_id,
            selected_option_label=option_label,
            result_text="The campaign choice was recorded for journey progress.",
        )
    )


def _record_founder_commitment(state: GameState) -> None:
    _record_campaign_choice(
        state,
        event_id="campaign_founder_commitment",
        option_id="sharpen_focus",
        option_label="Sharpen the Flagship",
        turn=4,
    )


def _record_founder_consequence(state: GameState) -> None:
    _record_campaign_choice(
        state,
        event_id="campaign_founder_consequence",
        option_id="defend_control",
        option_label="Defend Control",
        turn=9,
    )


def test_first_archive_mission_starts_with_guided_opening() -> None:
    mission = build_first_archive_mission(_founder_state())

    assert mission.current_step.step_id is FirstArchiveStepId.GUIDED_OPENING
    assert mission.step_label == "1/6"
    assert mission.progress_label == "0/6 complete"
    assert "Coach" in mission.next_action


def test_first_archive_mission_tracks_featured_campaign_decisions() -> None:
    state = _founder_state()
    state.company.current_turn = 7
    _record_founder_commitment(state)

    mission = build_first_archive_mission(state)

    assert mission.completed_steps == 2
    assert mission.current_step.step_id is FirstArchiveStepId.CONSEQUENCE
    assert mission.step_label == "3/6"


def test_first_archive_mission_moves_from_endgame_to_archive() -> None:
    state = _founder_state()
    state.company.current_turn = 15
    _record_founder_commitment(state)
    _record_founder_consequence(state)

    endgame = build_first_archive_mission(state)
    assert endgame.completed_steps == 4
    assert endgame.current_step.step_id is FirstArchiveStepId.FINISH_RUN

    state.victory_achieved = True
    state.victory_reason = "The company completed its campaign goal."
    terminal = build_first_archive_mission(state)
    assert terminal.completed_steps == 5
    assert terminal.current_step.step_id is FirstArchiveStepId.ARCHIVE_RUN
    assert "Save & Archive" in terminal.next_action


def test_existing_archive_completes_first_archive_mission_for_any_current_state() -> None:
    mission = build_first_archive_mission(_founder_state(), archive_count=1)

    assert mission.complete
    assert mission.completed_steps == 6
    assert mission.progress == 1.0
    assert "next unexplored route" in mission.next_action


def test_non_featured_scenario_uses_turn_chapters_instead_of_campaign_events() -> None:
    state = _founder_state()
    state.scenario_id = "custom_challenge"
    state.company.current_turn = 10

    mission = build_first_archive_mission(state)

    assert mission.completed_steps == 2
    assert mission.current_step.step_id is FirstArchiveStepId.CONSEQUENCE
    assert "Scale" in mission.current_step.detail
