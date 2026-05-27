from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from typer.testing import CliRunner

import nexus_tech.cli as cli_module
from nexus_tech.cli import app
from nexus_tech.domain.models import CandidateTrait, EmployeeRole, Seniority, TurnAction
from nexus_tech.frontend_2d import launch_2d_frontend, launch_2d_menu
from nexus_tech.frontend_2d.catalog import (
    list_campaign_start_choices,
    list_scenario_choices,
)
from nexus_tech.frontend_2d.context import (
    ContextPicker,
    build_command_request,
    explain_command_unavailable,
)
from nexus_tech.frontend_2d.event_queue import build_action_events
from nexus_tech.frontend_2d.viewmodels import (
    build_deep_dive_panel_view_models,
    build_game_view_model,
    build_run_review_view_model,
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


def test_build_command_request_supports_pipeline_and_candidate_actions() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")

    release_picker = build_command_request(
        state,
        command=TurnAction.PLAN_RELEASE.value,
        selected_product_id=state.products[0].id.hex,
    )
    candidate_state = apply_action(
        state,
        TurnAction.SOURCE_CANDIDATES,
        context=ActionContext(),
    ).state
    screen_picker = build_command_request(
        candidate_state,
        command=TurnAction.SCREEN_CANDIDATE.value,
        selected_product_id=candidate_state.products[0].id.hex,
    )

    assert isinstance(release_picker, ContextPicker)
    assert release_picker.options
    assert isinstance(screen_picker, ContextPicker)
    assert screen_picker.options


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


def test_build_deep_dive_panel_view_models_exposes_finance_and_customer_actions() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")

    panels = build_deep_dive_panel_view_models(
        state,
        selected_product_id=state.products[0].id.hex,
    )

    keys = {panel.key for panel in panels}
    assert {"team", "finance", "customers", "partnerships", "board", "pipeline", "report"} <= keys
    finance_panel = next(panel for panel in panels if panel.key == "finance")
    customer_panel = next(panel for panel in panels if panel.key == "customers")
    board_panel = next(panel for panel in panels if panel.key == "board")
    pipeline_panel = next(panel for panel in panels if panel.key == "pipeline")
    report_panel = next(panel for panel in panels if panel.key == "report")
    assert any(
        action.command == TurnAction.SET_CAPITAL_PLAN.value for action in finance_panel.actions
    )
    assert any(
        action.command == TurnAction.ADJUST_PRICING.value for action in customer_panel.actions
    )
    assert any(action.command == TurnAction.REVIEW_BOARD.value for action in board_panel.actions)
    assert any(
        action.command == TurnAction.CREATE_SALES_DEAL.value for action in pipeline_panel.actions
    )
    assert any(action.command == TurnAction.VIEW_REPORT.value for action in report_panel.actions)


def test_explain_command_unavailable_surfaces_specific_reason() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")

    assign_reason = explain_command_unavailable(
        state,
        command=TurnAction.ASSIGN_EMPLOYEE.value,
        selected_product_id=state.products[0].id.hex,
    )
    release_reason = explain_command_unavailable(
        state,
        command=TurnAction.WORK_RELEASE.value,
        selected_product_id=state.products[0].id.hex,
    )

    assert assign_reason is not None
    assert "Hire" in assign_reason or "employee" in assign_reason
    assert release_reason is not None
    assert "release" in release_reason.lower()


def test_catalog_choices_mix_unlocked_and_locked_content(tmp_path: Path) -> None:
    scenario_choices = list_scenario_choices(tmp_path / "menu.db")
    campaign_start_choices = list_campaign_start_choices(tmp_path / "menu.db")

    assert scenario_choices
    assert campaign_start_choices
    assert any(not choice.locked for choice in scenario_choices)
    assert any(choice.locked for choice in scenario_choices)
    assert any(not choice.locked for choice in campaign_start_choices)


def test_build_run_review_view_model_exposes_findings() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")
    state.company.game_over = True
    state.company.cash_on_hand = Decimal("-250.00")

    review = build_run_review_view_model(state)

    assert review.title in {"Failure Postmortem", "After-Action Review"}
    assert review.findings
    assert review.next_focus


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


def test_launch_2d_menu_headless_exits_after_frame_cap(tmp_path: Path) -> None:
    result = launch_2d_menu(
        db_path=tmp_path / "menu-2d.db",
        headless=True,
        max_frames=2,
        window_size=(960, 640),
    )

    assert result.exit_reason == "max_frames"
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


def test_menu_2d_command_routes_to_menu_launcher(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_launch_2d_menu(**kwargs):
        captured.update(kwargs)

        class Result:
            exit_reason = "max_frames"
            slot_name = "active"

        return Result()

    monkeypatch.setattr(cli_module, "launch_2d_menu", fake_launch_2d_menu)

    result = runner.invoke(
        app,
        [
            "menu-2d",
            "--headless",
            "--max-frames",
            "2",
        ],
    )

    assert result.exit_code == 0
    assert captured["headless"] is True
    assert captured["max_frames"] == 2
