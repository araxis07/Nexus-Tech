from __future__ import annotations

import re

from nexus_tech.domain.models import TurnAction
from nexus_tech.frontend_2d.catalog import list_scenario_choices
from nexus_tech.frontend_2d.viewmodels import (
    build_game_view_model,
    build_turn_summary_view_model,
)
from nexus_tech.simulation.action_catalog import (
    get_action_presentation,
    humanize_action_text,
)
from nexus_tech.simulation.campaign_journey import (
    get_campaign_journey_progress,
    list_featured_campaign_journeys,
)
from nexus_tech.simulation.engine import ActionContext, apply_action, create_new_game, resolve_turn
from nexus_tech.simulation.randomness import RandomSource
from nexus_tech.simulation.strategic_rhythm import build_strategic_rhythm
from nexus_tech.simulation.turn_coach import build_turn_coach


def _contains_raw_command(text: str) -> bool:
    return any(
        re.search(rf"(?<![A-Za-z0-9_]){re.escape(action.value)}(?![A-Za-z0-9_])", text)
        for action in TurnAction
    )


def test_action_catalog_collapses_internal_ladders_without_losing_routes() -> None:
    presentations = tuple(get_action_presentation(action) for action in TurnAction)

    assert len(presentations) == len(TurnAction)
    assert len({presentation.program_key for presentation in presentations}) <= 100
    assert all("_" not in presentation.label for presentation in presentations)
    assert all(
        presentation.command in TurnAction._value2member_map_ for presentation in presentations
    )
    assert get_action_presentation("run_enterprise_reference_council").label == ("Enterprise Trust")
    assert get_action_presentation("run_enterprise_reference_council").stage_label == "Council"


def test_action_text_humanizer_removes_embedded_internal_commands() -> None:
    text = humanize_action_text(
        "Run `run_enterprise_reference_council`, then hire_employee before end_turn."
    )

    assert text == "Run Enterprise Trust, then Hire Teammate before End Turn."
    assert not _contains_raw_command(text)


def test_featured_campaign_catalog_exposes_three_authored_acts(tmp_path) -> None:
    journeys = list_featured_campaign_journeys()
    choices = list_scenario_choices(tmp_path / "ux-clarity.db")[:6]

    assert len(journeys) == len(choices) == 6
    assert all(len(journey.chapters) == 3 for journey in journeys)
    assert all(choice.act_preview.count(" > ") == 2 for choice in choices)
    for journey in journeys:
        assert get_campaign_journey_progress(journey.scenario_id, 4).chapter_index == 0
        assert get_campaign_journey_progress(journey.scenario_id, 5).chapter_index == 1
        assert get_campaign_journey_progress(journey.scenario_id, 10).chapter_index == 2


def test_live_hud_exposes_current_act_and_readable_next_move() -> None:
    state = create_new_game(scenario_id="founder_journey")

    view_model = build_game_view_model(state)

    assert view_model.campaign_chapter_label == "Act 1/3: Foundation Loop"
    assert view_model.campaign_objective == "Staff and stabilize the flagship."
    assert "Next:" in view_model.header_note
    assert "Due:" in view_model.header_note
    assert "End Turn:" in view_model.header_note
    assert "Plan " not in view_model.header_note
    assert not _contains_raw_command(view_model.header_note)
    assert all(not _contains_raw_command(line.label) for line in view_model.coach_lines)
    assert view_model.decision_brief.objective_label == "Act 1/3: Foundation Loop"
    assert view_model.decision_brief.plan_label == "Balanced Execution / Balanced budget"
    assert view_model.decision_brief.plan_progress_label.endswith("turns left")
    assert 0.0 <= view_model.decision_brief.plan_progress <= 1.0
    assert view_model.decision_brief.plan_tone in {"info", "warning", "success", "danger"}
    assert view_model.decision_brief.command == view_model.coach_lines[0].command
    assert view_model.decision_brief.command == TurnAction.HIRE_EMPLOYEE.value
    assert view_model.decision_brief.command_label == view_model.coach_lines[0].label
    assert view_model.decision_brief.command_effect == "Build the first execution loop"
    assert view_model.decision_brief.command_source == "opening"
    assert view_model.decision_brief.command_consequence
    assert view_model.decision_brief.urgency_label
    assert view_model.decision_brief.end_turn_label in {
        "Ready to Resolve",
        "Review Risk",
        "Confirm High Risk",
    }
    assert view_model.decision_brief.end_turn_tone in {"success", "warning", "danger"}
    assert view_model.decision_brief.later_label
    assert view_model.decision_brief.later_detail
    assert any(chip.label == "Plan" for chip in view_model.snapshot_chips)
    assert not _contains_raw_command(view_model.decision_brief.later_detail)
    assert all(not line.startswith("endgame:") for line in view_model.risk_lines)


def test_strategic_rhythm_marks_stale_plan_and_keeps_follow_on_visible() -> None:
    state = create_new_game(scenario_id="founder_journey")
    state.company.current_turn = state.quarter_plan.target_turn + 1

    rhythm = build_strategic_rhythm(state)

    assert rhythm.plan_progress_label.endswith("refresh due")
    assert rhythm.plan_tone == "danger"
    assert "Refresh the roadmap" in rhythm.plan_detail
    assert rhythm.command in TurnAction._value2member_map_
    assert rhythm.later_label
    assert rhythm.later_detail


def test_strategic_rhythm_uses_current_turn_decision_follow_on() -> None:
    state = create_new_game(scenario_id="founder_journey")
    outcome = apply_action(
        state,
        TurnAction.IMPROVE_QUALITY,
        context=ActionContext(target_product_id=state.products[0].id),
    )

    rhythm = build_strategic_rhythm(outcome.state)

    assert rhythm.later_label == "Improve Quality follow-on"
    assert "resolves at end of turn" in rhythm.later_detail
    assert not _contains_raw_command(rhythm.command_detail)


def test_endgame_coach_lane_stays_out_of_opening_and_unlocks_in_act_three() -> None:
    state = create_new_game(scenario_id="founder_journey")

    for turn in (1, 5, 9):
        state.company.current_turn = turn
        assert all(item.source != "endgame" for item in build_turn_coach(state).recommendations)

    state.company.current_turn = 10
    assert any(item.source == "endgame" for item in build_turn_coach(state).recommendations)


def test_turn_summary_explains_causes_and_keeps_routing_internal() -> None:
    previous_state = create_new_game(scenario_id="founder_journey")
    working_state = apply_action(
        previous_state.model_copy(deep=True),
        TurnAction.IMPROVE_QUALITY,
        context=ActionContext(target_product_id=previous_state.products[0].id),
    ).state
    resolution = resolve_turn(working_state, RandomSource(seed=281))

    summary = build_turn_summary_view_model(previous_state, resolution)

    assert len(summary.cause_lines) == 4
    assert summary.cause_lines[0].startswith("Cash: revenue")
    assert summary.cause_lines[1].startswith("Demand: users")
    assert summary.cause_lines[2].startswith("Pressure: board")
    assert summary.focus_command in TurnAction._value2member_map_
    assert summary.strategic_headline.startswith("Act 1/3: Foundation Loop | Plan ")
    assert summary.focus_command != TurnAction.SET_PATH_CASH_WATERFALL.value
    assert not _contains_raw_command(summary.focus_label)
    assert not _contains_raw_command(summary.focus_detail)
    assert summary.strategic_lines[-1].startswith("Later:")
    assert all(not _contains_raw_command(line) for line in summary.strategic_lines)
