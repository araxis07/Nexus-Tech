from __future__ import annotations

from nexus_tech.domain.models import CampaignGoalId, TurnAction
from nexus_tech.frontend_2d.catalog import list_scenario_choices
from nexus_tech.frontend_2d.viewmodels import build_game_view_model
from nexus_tech.simulation.action_catalog import ActionFamily, get_action_presentation
from nexus_tech.simulation.balance_lab import evaluate_balance_cell, run_balance_matrix
from nexus_tech.simulation.engine import create_new_game
from nexus_tech.simulation.run_phase import RunPhaseId, get_run_phase


def test_every_turn_action_has_readable_player_facing_metadata() -> None:
    presentations = tuple(get_action_presentation(action) for action in TurnAction)

    assert len(presentations) == len(TurnAction)
    assert {presentation.command for presentation in presentations} == {
        action.value for action in TurnAction
    }
    assert {presentation.family for presentation in presentations} == set(ActionFamily)
    assert all("_" not in presentation.label for presentation in presentations)
    assert all(1 <= len(presentation.label) <= 38 for presentation in presentations)


def test_run_phases_cover_opening_through_endgame_boundaries() -> None:
    expectations = {
        1: RunPhaseId.OPENING,
        4: RunPhaseId.OPENING,
        5: RunPhaseId.GROWTH,
        9: RunPhaseId.GROWTH,
        10: RunPhaseId.SCALE,
        14: RunPhaseId.SCALE,
        15: RunPhaseId.ENDGAME,
        20: RunPhaseId.ENDGAME,
    }

    for turn, expected_phase in expectations.items():
        phase = get_run_phase(turn)
        assert phase.phase_id is expected_phase
        assert phase.objective
        assert 0.0 <= phase.progress <= 1.0


def test_featured_scenarios_lead_the_wizard_as_a_guided_journey(tmp_path) -> None:
    choices = list_scenario_choices(tmp_path / "featured-scenarios.db")

    assert [choice.scenario_id for choice in choices[:6]] == [
        "founder_journey",
        "bootstrap_studio",
        "technical_rebuild",
        "portfolio_machine",
        "debt_crunch",
        "public_market_countdown",
    ]
    assert [choice.featured_rank for choice in choices[:6]] == list(range(1, 7))
    assert all(choice.track_label != "Challenge" for choice in choices[:6])
    assert all(choice.stage_hint for choice in choices)


def test_game_view_model_uses_phase_and_readable_coach_commands() -> None:
    state = create_new_game(scenario_id="founder_journey")

    view_model = build_game_view_model(state)

    assert view_model.phase_label == "Opening / Turns 1-4"
    assert "Next:" in view_model.header_note
    assert view_model.coach_lines
    assert all("_" not in line.label for line in view_model.coach_lines)
    assert all(line.family_label for line in view_model.coach_lines)


def test_founder_journey_long_session_gate_covers_every_campaign_goal() -> None:
    for index, goal in enumerate(CampaignGoalId):
        matrix = run_balance_matrix(
            scenario_ids=["founder_journey"],
            campaign_goal_id=goal,
            runs=2,
            turns=20,
            seed_base=7300 + (index * 1000),
        )

        assert all(cell.shutdowns == 0 for cell in matrix.cells)
        assert all(
            evaluate_balance_cell(cell, runs=matrix.runs, turns=matrix.turns).status != "fail"
            for cell in matrix.cells
        )
