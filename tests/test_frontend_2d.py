from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from typer.testing import CliRunner

import nexus_tech.cli as cli_module
from nexus_tech.cli import app
from nexus_tech.domain.models import CandidateTrait, EmployeeRole, Seniority, TurnAction
from nexus_tech.frontend_2d import launch_2d_frontend
from nexus_tech.frontend_2d.context import ContextPicker, build_command_request
from nexus_tech.frontend_2d.event_queue import build_action_events
from nexus_tech.frontend_2d.viewmodels import (
    build_game_view_model,
    build_turn_summary_view_model,
)
from nexus_tech.simulation.engine import ActionContext, apply_action, create_new_game, resolve_turn
from nexus_tech.simulation.randomness import RandomSource

runner = CliRunner()


def test_build_game_view_model_exposes_products_and_coach_lines() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")

    view_model = build_game_view_model(state)

    assert view_model.company_name == "NEXUS TECH"
    assert view_model.products
    assert view_model.coach_lines
    assert view_model.snapshot_chips
    assert any(gauge.title == "Cash" for gauge in view_model.stats)


def test_build_command_request_returns_strategy_picker() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")

    picker = build_command_request(state, command=TurnAction.SET_COMPANY_STRATEGY.value)

    assert isinstance(picker, ContextPicker)
    assert len(picker.options) == 4
    assert picker.options[0].request.action is TurnAction.SET_COMPANY_STRATEGY
    assert picker.options[0].request.context.strategy is not None


def test_build_command_request_returns_assign_picker_for_idle_employee() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")
    hire_outcome = apply_action(
        state,
        TurnAction.HIRE_EMPLOYEE,
        context=ActionContext(
            hire_full_name="2D Engineer 1",
            hire_role=EmployeeRole.ENGINEER,
            hire_seniority=Seniority.MID,
            hire_specialization="product",
            hire_trait=CandidateTrait.STEADY_OPERATOR,
        ),
    )

    picker = build_command_request(
        hire_outcome.state,
        command=TurnAction.ASSIGN_EMPLOYEE.value,
        selected_product_id=hire_outcome.state.products[0].id.hex,
    )

    assert isinstance(picker, ContextPicker)
    assert picker.options
    assert picker.options[0].request.action is TurnAction.ASSIGN_EMPLOYEE
    assert picker.options[0].request.context.employee_id is not None
    assert picker.options[0].request.context.target_product_id == hire_outcome.state.products[0].id


def test_build_action_events_surfaces_cash_and_product_deltas() -> None:
    previous_state = create_new_game("NEXUS TECH", "Nexus One")
    current_state = previous_state.model_copy(deep=True)
    current_state.company.cash_on_hand += Decimal("800.00")
    current_state.company.reputation += 3
    current_state.products[0].quality += 4
    current_state.products[0].bug_level -= 2

    events = build_action_events(
        previous_state,
        current_state,
        action_label="improve_quality",
        message="Quality work landed.",
    )

    titles = {event.title for event in events}
    assert "Cash Changed" in titles
    assert "Reputation Shifted" in titles
    assert f"{current_state.products[0].name} Quality" in titles
    assert f"{current_state.products[0].name} Bugs" in titles


def test_build_turn_summary_view_model_exposes_resolution_metrics() -> None:
    previous_state = create_new_game("NEXUS TECH", "Nexus One")
    working_state = previous_state.model_copy(deep=True)
    working_state = apply_action(
        working_state,
        TurnAction.IMPROVE_QUALITY,
        context=ActionContext(target_product_id=working_state.products[0].id),
    ).state
    resolution = resolve_turn(working_state, RandomSource(seed=17))

    summary = build_turn_summary_view_model(previous_state, resolution)

    assert summary.title.startswith("Turn ")
    assert any(metric.label == "Net Cash" for metric in summary.metrics)
    assert summary.product_lines


def test_launch_2d_frontend_headless_exits_after_frame_cap(tmp_path: Path) -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")
    rng = RandomSource(seed=11)

    result = launch_2d_frontend(
        state=state,
        rng=rng,
        db_path=tmp_path / "headless-2d.db",
        slot_name="active",
        headless=True,
        max_frames=2,
        window_size=(960, 640),
    )

    assert result.exit_reason == "max_frames"
    assert result.slot_name == "active"
    assert result.saved_on_exit is False


def test_play_2d_command_routes_to_new_frontend_launcher(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_start_new_game_2d(**kwargs) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(cli_module, "start_new_game_2d", fake_start_new_game_2d)

    result = runner.invoke(
        app,
        [
            "play-2d",
            "--scenario",
            "founder_journey",
            "--seed",
            "7",
            "--headless",
            "--max-frames",
            "2",
        ],
    )

    assert result.exit_code == 0
    assert captured["scenario_id"] == "founder_journey"
    assert captured["seed"] == 7
    assert captured["headless"] is True
    assert captured["max_frames"] == 2
