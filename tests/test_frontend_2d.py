from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from typer.testing import CliRunner

import nexus_tech.cli as cli_module
from nexus_tech.cli import app
from nexus_tech.domain.models import (
    CandidateTrait,
    EmployeeRole,
    ProductReleaseType,
    RoadmapProjectType,
    Seniority,
    TurnAction,
)
from nexus_tech.frontend_2d import launch_2d_frontend, launch_2d_menu
from nexus_tech.frontend_2d.catalog import (
    list_campaign_start_choices,
    list_scenario_choices,
)
from nexus_tech.frontend_2d.context import (
    ActionRequest,
    ContextPicker,
    build_command_request,
    build_inspector_action_request,
    explain_command_unavailable,
    explain_inspector_action_unavailable,
)
from nexus_tech.frontend_2d.event_queue import build_action_events, build_turn_resolution_events
from nexus_tech.frontend_2d.scenes import RunScene, TitleScene, TurnSummaryScene
from nexus_tech.frontend_2d.viewmodels import (
    build_deep_dive_panel_view_models,
    build_endgame_cockpit_actions,
    build_game_view_model,
    build_run_review_view_model,
    build_turn_summary_view_model,
)
from nexus_tech.frontend_2d.widgets import create_fonts
from nexus_tech.persistence.save_coordinator import SaveLoadCoordinator
from nexus_tech.simulation.endgame import (
    calculate_endgame_pressure,
    calculate_endgame_readiness,
    evaluate_exit_outcome,
)
from nexus_tech.simulation.engine import ActionContext, apply_action, create_new_game, resolve_turn
from nexus_tech.simulation.opening_guide import build_guided_opening
from nexus_tech.simulation.randomness import RandomSource
from nexus_tech.simulation.risk_forecast import build_risk_forecast
from nexus_tech.simulation.turn_coach import build_turn_coach

runner = CliRunner()


def _build_enriched_2d_state():
    state = create_new_game("NEXUS TECH", "Nexus One")
    state.action_points_remaining = 12
    state = apply_action(state, TurnAction.SOURCE_CANDIDATES, context=ActionContext()).state
    state = apply_action(
        state,
        TurnAction.CREATE_SALES_DEAL,
        context=ActionContext(target_product_id=state.products[0].id),
    ).state
    state = apply_action(
        state,
        TurnAction.PLAN_RELEASE,
        context=ActionContext(
            target_product_id=state.products[0].id,
            release_type=ProductReleaseType.MINOR_RELEASE,
        ),
    ).state
    state = apply_action(
        state,
        TurnAction.START_ROADMAP_PROJECT,
        context=ActionContext(
            target_product_id=state.products[0].id,
            roadmap_project_type=RoadmapProjectType.PLATFORM_REBUILD,
        ),
    ).state
    return state


def _build_paged_2d_state():
    state = _build_enriched_2d_state()
    state.action_points_remaining = 20
    for _ in range(4):
        state = apply_action(
            state,
            TurnAction.SOURCE_CANDIDATES,
            context=ActionContext(),
        ).state
    return state


def _build_pygame_bundle():
    import os

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    import pygame

    pygame.init()
    pygame.font.init()
    surface = pygame.display.set_mode((960, 640), pygame.HIDDEN)
    return pygame, create_fonts(pygame), surface


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
    assert any(metric.label == "Blocked Gates" for metric in summary.metrics)
    assert summary.product_lines
    assert summary.strategic_lines
    assert summary.focus_command


def test_build_turn_resolution_events_exposes_gate_and_outlook_cards() -> None:
    previous_state = create_new_game("NEXUS TECH", "Nexus One")
    working_state = previous_state.model_copy(deep=True)
    working_state = apply_action(
        working_state,
        TurnAction.IMPROVE_QUALITY,
        context=ActionContext(target_product_id=working_state.products[0].id),
    ).state
    resolution = resolve_turn(working_state, RandomSource(seed=19))

    events = build_turn_resolution_events(previous_state, resolution)

    titles = {event.title for event in events}
    assert "Gate Command" in titles
    assert "Turn 1 Resolved" in titles


def test_build_deep_dive_panel_view_models_exposes_finance_and_customer_actions() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")
    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state, readiness)

    panels = build_deep_dive_panel_view_models(
        state,
        selected_product_id=state.products[0].id.hex,
    )

    keys = {panel.key for panel in panels}
    assert {
        "team",
        "finance",
        "customers",
        "partnerships",
        "board",
        "pipeline",
        "report",
        "endgame",
    } <= keys
    finance_panel = next(panel for panel in panels if panel.key == "finance")
    customer_panel = next(panel for panel in panels if panel.key == "customers")
    board_panel = next(panel for panel in panels if panel.key == "board")
    pipeline_panel = next(panel for panel in panels if panel.key == "pipeline")
    report_panel = next(panel for panel in panels if panel.key == "report")
    endgame_panel = next(panel for panel in panels if panel.key == "endgame")
    team_panel = next(panel for panel in panels if panel.key == "team")
    assert any(
        action.command == TurnAction.SET_CAPITAL_PLAN.value for action in finance_panel.actions
    )
    assert any(action.command == TurnAction.REVIEW_TEAM.value for action in team_panel.actions)
    assert any(
        action.command == TurnAction.REVIEW_FINANCE.value for action in finance_panel.actions
    )
    assert any(
        action.command == TurnAction.ADJUST_PRICING.value for action in customer_panel.actions
    )
    assert any(action.command == TurnAction.REVIEW_BOARD.value for action in board_panel.actions)
    assert any(
        action.command == TurnAction.CREATE_SALES_DEAL.value for action in pipeline_panel.actions
    )
    assert any(action.command == TurnAction.VIEW_REPORT.value for action in report_panel.actions)
    assert any(
        action.command == pressure.path_gate_command_alert for action in endgame_panel.actions
    )


def test_deep_dive_panels_expose_live_inspector_sections() -> None:
    state = _build_enriched_2d_state()

    panels = build_deep_dive_panel_view_models(
        state,
        selected_product_id=state.products[0].id.hex,
    )

    pipeline_panel = next(panel for panel in panels if panel.key == "pipeline")
    board_panel = next(panel for panel in panels if panel.key == "board")
    report_panel = next(panel for panel in panels if panel.key == "report")
    endgame_panel = next(panel for panel in panels if panel.key == "endgame")
    assert {section.key for section in pipeline_panel.inspectors} == {
        "deals",
        "releases",
        "projects",
        "candidates",
    }
    assert pipeline_panel.inspectors[0].items[0].title != "No Sales Deals"
    assert {section.key for section in board_panel.inspectors} == {
        "resolution",
        "scorecard",
        "alerts",
    }
    assert {section.key for section in report_panel.inspectors} == {
        "turns",
        "funding",
        "milestones",
        "events",
    }
    assert {section.key for section in endgame_panel.inspectors} == {
        "paths",
        "watchlist",
        "projection",
    }


def test_deep_panel_actions_are_supported_or_explained() -> None:
    for state in (create_new_game("NEXUS TECH", "Nexus One"), _build_enriched_2d_state()):
        panels = build_deep_dive_panel_view_models(
            state,
            selected_product_id=state.products[0].id.hex,
        )
        for panel in panels:
            for action in panel.actions:
                request = build_command_request(
                    state,
                    command=action.command,
                    selected_product_id=state.products[0].id.hex,
                )
                reason = explain_command_unavailable(
                    state,
                    command=action.command,
                    selected_product_id=state.products[0].id.hex,
                )
                assert request is not None or reason is not None, (panel.key, action.command)


def test_build_inspector_action_request_targets_live_entities() -> None:
    state = _build_enriched_2d_state()
    panels = build_deep_dive_panel_view_models(
        state,
        selected_product_id=state.products[0].id.hex,
    )
    pipeline_panel = next(panel for panel in panels if panel.key == "pipeline")
    release_item = next(
        section.items[0] for section in pipeline_panel.inspectors if section.key == "releases"
    )
    deal_item = next(
        section.items[0] for section in pipeline_panel.inspectors if section.key == "deals"
    )

    release_request = build_inspector_action_request(
        state,
        panel_key="pipeline",
        section_key="releases",
        command=TurnAction.WORK_RELEASE.value,
        payload=release_item.payload,
        selected_product_id=state.products[0].id.hex,
    )
    deal_request = build_inspector_action_request(
        state,
        panel_key="pipeline",
        section_key="deals",
        command=TurnAction.ADVANCE_SALES_DEAL.value,
        payload=deal_item.payload,
        selected_product_id=state.products[0].id.hex,
    )

    assert isinstance(release_request, ActionRequest)
    assert release_request.context.release_id == state.product_releases[0].id
    assert isinstance(deal_request, ActionRequest)
    assert deal_request.context.sales_deal_id == state.sales_deals[0].id


def test_endgame_inspector_actions_are_supported_or_explained() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")
    panel = next(
        panel
        for panel in build_deep_dive_panel_view_models(
            state,
            selected_product_id=state.products[0].id.hex,
        )
        if panel.key == "endgame"
    )

    for section in panel.inspectors:
        for item in section.items:
            for action in item.actions:
                request = build_inspector_action_request(
                    state,
                    panel_key=panel.key,
                    section_key=section.key,
                    command=action.command,
                    payload=item.payload,
                    selected_product_id=state.products[0].id.hex,
                )
                reason = explain_inspector_action_unavailable(
                    state,
                    panel_key=panel.key,
                    section_key=section.key,
                    command=action.command,
                    payload=item.payload,
                    selected_product_id=state.products[0].id.hex,
                )
                assert request is not None or reason is not None, (
                    section.key,
                    item.title,
                    action.command,
                )


def test_endgame_cockpit_actions_expose_all_path_fix_buttons() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")

    actions = build_endgame_cockpit_actions(
        state,
        selected_product_id=state.products[0].id.hex,
    )

    labels = {action.label for action in actions}
    assert {"IPO Fix", "M&A Fix", "Independence Fix", "Reset Fix"} <= labels
    assert any(action.label == "Gate Command" for action in actions)


def test_run_scene_inspector_supports_selection_paging_and_item_actions() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = _build_paged_2d_state()
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=7),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._open_inspector("pipeline")
        scene._select_inspector_section("candidates")
        assert scene._selected_inspector_section().key == "candidates"
        assert scene._inspector_total_pages() >= 2
        first_page_title = scene._selected_inspector_item().title

        scene._change_inspector_page(1)
        assert scene._inspector_page == 1
        assert scene._selected_inspector_item().title != first_page_title

        scene._select_inspector_section("releases")
        before_progress = scene.state.product_releases[0].progress
        scene._run_selected_inspector_primary_action()

        assert scene.state.product_releases[0].progress > before_progress
    finally:
        pygame.quit()


def test_run_scene_inspector_reopen_restores_panel_memory() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = _build_paged_2d_state()
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=29),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._open_inspector("pipeline")
        scene._select_inspector_section("candidates")
        scene._set_inspector_sort_mode("risk")
        scene._set_inspector_filter_mode("actionable")
        scene._change_inspector_page(1)
        remembered_title = scene._selected_inspector_item().title

        scene._open_inspector("finance")
        scene._open_inspector("pipeline")

        assert scene._selected_inspector_section().key == "candidates"
        assert scene._inspector_page == 1
        assert scene._inspector_sort_mode_label() == "Highest Risk"
        assert scene._inspector_filter_mode_label() == "Actionable"
        assert scene._selected_inspector_item().title == remembered_title
    finally:
        pygame.quit()


def test_run_scene_inspector_hotkeys_focus_actionable_and_hotspot() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = _build_paged_2d_state()
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=31),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._open_inspector("pipeline")
        scene._select_inspector_section("candidates")
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, unicode="a"))
        assert scene._inspector_filter_mode_label() == "Actionable"

        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_h, unicode="h"))
        assert scene._inspector_sort_mode_label() == "Highest Risk"
        assert scene._inspector_filter_mode_label() == "Attention"
    finally:
        pygame.quit()


def test_run_scene_can_open_endgame_panel_inspector_from_hotkey() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=7),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._deep_panel_key = "endgame"
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i, unicode="i"))

        assert scene._inspector_panel_key == "endgame"
        assert scene._selected_inspector_section().key == "paths"
    finally:
        pygame.quit()


def test_run_scene_routes_capital_plan_command_to_finance_workspace() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=37),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._run_command(TurnAction.SET_CAPITAL_PLAN.value)

        assert scene._deep_panel_key == "finance"
        assert scene._context_picker is not None
    finally:
        pygame.quit()


def test_title_scene_sidebar_surfaces_meta_progression(tmp_path: Path) -> None:
    pygame, fonts, surface = _build_pygame_bundle()
    try:
        coordinator = SaveLoadCoordinator(tmp_path / "title-scene.db")
        scene = TitleScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=13),
            slot_name="active",
            save_callback=lambda *_args: None,
            coordinator=coordinator,
            initial_mode="menu",
        )

        menu_lines = scene._title_sidebar_lines()
        assert any(line.startswith("Campaign tier:") for line in menu_lines)
        assert any(line.startswith("Next reward:") for line in menu_lines)

        scene._mode = "archives"
        archive_lines = scene._title_sidebar_lines()
        assert any("Coverage gap:" in line for line in archive_lines)
        scene._mode = "meta"
        meta_lines = scene._title_sidebar_lines()
        assert any("Best path labels:" in line for line in meta_lines)
        scene.draw(surface)
    finally:
        pygame.quit()


def test_guidance_and_endgame_commands_are_supported_or_explained(tmp_path: Path) -> None:
    unlocked_choices = [
        choice for choice in list_scenario_choices(tmp_path / "audit.db") if not choice.locked
    ]
    commands: set[str] = set()
    for choice in unlocked_choices:
        state = create_new_game(
            "NEXUS TECH",
            "Nexus One",
            scenario_id=choice.scenario_id,
            difficulty_mode=choice.default_difficulty,
            campaign_goal_id=choice.default_goal_id,
        )
        pid = state.products[0].id.hex
        guide = build_guided_opening(state)
        commands.add(guide.current_command)
        commands.update(step.command for step in guide.steps)
        commands.update(rec.command for rec in build_turn_coach(state).recommendations)
        commands.update(item.command for item in build_risk_forecast(state).items)
        readiness = calculate_endgame_readiness(state)
        pressure = calculate_endgame_pressure(state, readiness)
        commands.update(pressure.path_gate_commands)
        if pressure.path_gate_command_alert in TurnAction._value2member_map_:
            commands.add(pressure.path_gate_command_alert)
        outcome = evaluate_exit_outcome(state)
        commands.update(outcome.path_gate_commands)
        if outcome.path_gate_command_alert in TurnAction._value2member_map_:
            commands.add(outcome.path_gate_command_alert)
        for panel in build_deep_dive_panel_view_models(state, selected_product_id=pid):
            commands.update(action.command for action in panel.actions)

    for command in sorted(commands):
        command_supported = False
        command_explained = False
        for choice in unlocked_choices:
            state = create_new_game(
                "NEXUS TECH",
                "Nexus One",
                scenario_id=choice.scenario_id,
                difficulty_mode=choice.default_difficulty,
                campaign_goal_id=choice.default_goal_id,
            )
            pid = state.products[0].id.hex
            request = build_command_request(
                state,
                command=command,
                selected_product_id=pid,
            )
            reason = explain_command_unavailable(
                state,
                command=command,
                selected_product_id=pid,
            )
            command_supported = command_supported or request is not None
            command_explained = command_explained or reason is not None
        assert command_supported or command_explained, command


def test_run_scene_inspector_sort_filter_and_small_window_draw() -> None:
    pygame, fonts, surface = _build_pygame_bundle()
    try:
        surface = pygame.display.set_mode((820, 620), pygame.HIDDEN)
        state = _build_paged_2d_state()
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=17),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._open_inspector("pipeline")
        scene._select_inspector_section("candidates")
        base_items = scene._filtered_sorted_inspector_items()
        scene._cycle_inspector_sort_mode()
        scene._cycle_inspector_filter_mode()
        filtered_items = scene._filtered_sorted_inspector_items()
        scene._deep_panel_key = "endgame"
        scene._help_overlay_visible = True
        scene.draw(surface)

        assert scene._inspector_sort_mode_label() == "Highest Risk"
        assert scene._inspector_filter_mode_label() == "Actionable"
        assert len(filtered_items) <= len(base_items)
        assert scene._active_panel_key() == "pipeline"
    finally:
        pygame.quit()


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


def test_turn_summary_scene_reveals_all_phases_and_draws_small_window() -> None:
    pygame, fonts, surface = _build_pygame_bundle()
    try:
        surface = pygame.display.set_mode((900, 640), pygame.HIDDEN)
        previous_state = create_new_game("NEXUS TECH", "Nexus One")
        working_state = previous_state.model_copy(deep=True)
        working_state = apply_action(
            working_state,
            TurnAction.IMPROVE_QUALITY,
            context=ActionContext(target_product_id=working_state.products[0].id),
        ).state
        resolution = resolve_turn(working_state, RandomSource(seed=23))
        scene = TurnSummaryScene(
            pygame=pygame,
            fonts=fonts,
            state=resolution.state,
            rng=RandomSource(seed=23),
            slot_name="active",
            save_callback=lambda *_args: None,
            previous_state=previous_state,
            resolution=resolution,
            selected_product_id=resolution.state.products[0].id.hex,
            dirty=True,
        )

        scene.update(2.7)
        scene.draw(surface)

        assert scene._phase_index() == 2
        assert scene._visible_metric_count() == len(scene._view_model.metrics)
        assert scene._visible_product_count() == len(scene._view_model.product_lines)
    finally:
        pygame.quit()


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
