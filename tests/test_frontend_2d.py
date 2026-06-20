from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from typer.testing import CliRunner

import nexus_tech.cli as cli_module
import nexus_tech.frontend_2d.animation_audit as animation_audit_module
import nexus_tech.frontend_2d.scenes as scenes_module
from nexus_tech.cli import app
from nexus_tech.domain.models import (
    CandidateTrait,
    EmployeeRole,
    EventCategory,
    EventOption,
    PendingEvent,
    ProductReleaseType,
    RoadmapProjectType,
    Seniority,
    TurnAction,
)
from nexus_tech.frontend_2d import (
    ANIMATION_MATRIX_REPORT_NAME,
    ANIMATION_PLAYTEST_PREP_REPORT_NAME,
    ANIMATION_PLAYTEST_REPORT_NAME,
    AnimationAuditReport,
    AnimationCoverageCell,
    AnimationMatrixCell,
    AnimationMatrixReport,
    AnimationPlaytestReadinessPlan,
    AnimationPlaytestReportValidation,
    FlowAuditReport,
    MotionAuditCell,
    MotionAuditReport,
    VisualAuditCell,
    VisualAuditReport,
    build_2d_animation_playtest_command_queue,
    build_2d_animation_playtest_prep_report,
    build_2d_animation_playtest_readiness_plan,
    launch_2d_frontend,
    launch_2d_menu,
    run_2d_animation_audit,
    run_2d_animation_matrix_audit,
    run_2d_flow_audit,
    run_2d_motion_audit,
    run_2d_visual_audit,
    summarize_2d_animation_playtest_report,
    validate_2d_animation_playtest_command_queue,
    validate_2d_animation_playtest_readiness_plan,
    validate_2d_animation_playtest_report,
    write_2d_animation_matrix_report,
    write_2d_animation_playtest_command_queue,
    write_2d_animation_playtest_prep_report,
    write_2d_animation_playtest_readiness_plan,
    write_2d_animation_playtest_report_template,
)
from nexus_tech.frontend_2d.catalog import (
    list_campaign_start_choices,
    list_scenario_choices,
)
from nexus_tech.frontend_2d.context import (
    ActionRequest,
    ContextPicker,
    PickerOption,
    build_command_request,
    build_inspector_action_request,
    explain_command_unavailable,
    explain_inspector_action_unavailable,
)
from nexus_tech.frontend_2d.event_queue import (
    FrontendEvent,
    build_action_events,
    build_turn_resolution_events,
    describe_action_motion_profile,
)
from nexus_tech.frontend_2d.input_map import FrontendIntent
from nexus_tech.frontend_2d.scenes import (
    ClickTarget,
    ReviewScene,
    RunScene,
    TitleScene,
    TurnSummaryScene,
)
from nexus_tech.frontend_2d.tween import MotionMode, PulseBank, normalize_motion_mode
from nexus_tech.frontend_2d.viewmodels import (
    build_deep_dive_panel_view_models,
    build_endgame_cockpit_actions,
    build_game_view_model,
    build_run_review_view_model,
    build_turn_summary_view_model,
)
from nexus_tech.frontend_2d.visual_audit import (
    MAX_BRIGHT_RATIO,
    MAX_EDGE_DENSITY,
    VISUAL_AUDIT_SUMMARY_NAME,
)
from nexus_tech.frontend_2d.widgets import (
    DANGER,
    create_fonts,
    draw_button,
    draw_wrapped_text,
    fit_text_line,
)
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


def test_2d_widget_text_fit_ellipsizes_to_available_width() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        fitted = fit_text_line(
            fonts.small,
            "This dashboard command description is intentionally too long",
            118,
        )

        assert fitted.endswith("...")
        assert fonts.small.size(fitted)[0] <= 118
        assert fit_text_line(fonts.small, "Short label", 118) == "Short label"
    finally:
        pygame.quit()


def test_2d_font_pack_keeps_compact_layout_metrics_stable() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        assert fonts.title.get_height() <= 28
        assert fonts.heading.get_height() <= 20
        assert fonts.body.get_height() <= 16
        assert fonts.small.get_height() <= 13
        assert fonts.mono.get_height() <= 14
        assert fonts.heading.size("Action Bar")[0] <= 120
        assert fonts.small.size("Space End Turn")[0] <= 120
    finally:
        pygame.quit()


def test_2d_widget_wrapping_and_buttons_stay_inside_compact_rects() -> None:
    pygame, fonts, surface = _build_pygame_bundle()
    try:
        text_rect = pygame.Rect(12, 12, 126, 16)
        consumed = draw_wrapped_text(
            surface,
            fonts.small,
            "Long unbroken-dashboard-command-copy should still stay inside the panel",
            DANGER,
            text_rect,
            line_height=16,
        )
        draw_button(
            surface,
            pygame,
            rect=pygame.Rect(20, 44, 128, 44),
            title="Space End Turn With Preview",
            detail="Resolve this turn with warning gates and consequence previews.",
            accent=DANGER,
            title_font=fonts.small,
            detail_font=fonts.small,
        )

        assert consumed == 16
    finally:
        pygame.quit()


def _assert_actor_readability_clear(scene) -> None:
    assert scene.actor_sprite_bounds()
    assert scene.actor_readability_violations() == ()
    assert scene.actor_readability_clear()


def _collect_surfaced_2d_commands(tmp_path: Path) -> set[str]:
    commands: set[str] = set()
    unlocked_choices = [
        choice
        for choice in list_scenario_choices(tmp_path / "motion-audit.db")
        if not choice.locked
    ]
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
        pressure = calculate_endgame_pressure(state, calculate_endgame_readiness(state))
        commands.update(pressure.path_gate_commands)
        commands.add(pressure.path_gate_command_alert)
        outcome = evaluate_exit_outcome(state)
        commands.update(outcome.path_gate_commands)
        commands.add(outcome.path_gate_command_alert)
        for panel in build_deep_dive_panel_view_models(state, selected_product_id=pid):
            commands.update(action.command for action in panel.actions)
    return commands


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


def test_build_action_events_emit_motion_targets() -> None:
    previous_state = create_new_game("NEXUS TECH", "Nexus One")
    current_state = previous_state.model_copy(deep=True)
    current_state.company.cash_on_hand += Decimal("500.00")
    current_state.products[0].quality += 2

    events = build_action_events(
        previous_state,
        current_state,
        action_label=TurnAction.IMPROVE_QUALITY.value,
        message="Quality work landed.",
    )

    event_by_title = {event.title: event for event in events}
    assert event_by_title["Improve Quality"].targets == ("feed", "panel:products")
    assert event_by_title["Cash Changed"].targets == ("stat:cash", "summary:metrics")
    assert event_by_title[f"{current_state.products[0].name} Quality"].targets == (
        f"product:{current_state.products[0].id.hex}",
        f"product:{current_state.products[0].id.hex}:quality",
    )


def test_build_action_events_emit_action_choreography_cards() -> None:
    previous_state = create_new_game("NEXUS TECH", "Nexus One")
    current_state = previous_state.model_copy(deep=True)
    current_state.products[0].user_count += 42

    events = build_action_events(
        previous_state,
        current_state,
        action_label=TurnAction.MARKET_PRODUCT.value,
        message="Demand work landed.",
    )

    event_by_title = {event.title: event for event in events}
    assert "Demand Push" in event_by_title
    assert event_by_title["Demand Push"].targets == (
        f"product:{current_state.products[0].id.hex}",
        f"product:{current_state.products[0].id.hex}:quality",
        f"product:{current_state.products[0].id.hex}:bugs",
        f"product:{current_state.products[0].id.hex}:fit",
        f"product:{current_state.products[0].id.hex}:debt",
        "stat:users",
        "panel:customers",
    )
    assert f"{current_state.products[0].name} Users" in event_by_title


def test_build_action_events_emit_remaining_family_choreography_cards() -> None:
    previous_state = create_new_game("NEXUS TECH", "Nexus One")
    current_state = previous_state.model_copy(deep=True)
    current_state.company.cash_on_hand += Decimal("15000.00")

    events = build_action_events(
        previous_state,
        current_state,
        action_label=TurnAction.REFINANCE_DEBT.value,
        message="Refinancing posture changed.",
    )

    event_by_title = {event.title: event for event in events}
    assert "Capital Shuffle" in event_by_title
    assert event_by_title["Capital Shuffle"].targets == (
        "panel:finance",
        "stat:cash",
        "stat:runway",
    )


def test_build_action_events_emit_endgame_gate_choreography_cards() -> None:
    previous_state = create_new_game("NEXUS TECH", "Nexus One")
    current_state = previous_state.model_copy(deep=True)
    current_state.company.cash_on_hand -= Decimal("1200.00")
    current_state.finance.board_pressure += 6

    events = build_action_events(
        previous_state,
        current_state,
        action_label=TurnAction.SET_BOARD_RESET_CONTINGENCY_BUFFER.value,
        message="Reserve posture hardened.",
    )

    event_by_title = {event.title: event for event in events}
    assert "Reset Buffer" in event_by_title
    assert event_by_title["Reset Buffer"].targets == (
        "panel:endgame",
        "panel:board",
        "panel:finance",
        "stat:cash",
        "stat:board_pressure",
    )


def test_build_action_events_emit_specific_finance_bridge_choreography_cards() -> None:
    previous_state = create_new_game("NEXUS TECH", "Nexus One")
    current_state = previous_state.model_copy(deep=True)
    current_state.company.cash_on_hand += Decimal("15000.00")

    events = build_action_events(
        previous_state,
        current_state,
        action_label=TurnAction.TAKE_LOAN.value,
        message="Debt bridge secured.",
    )

    event_by_title = {event.title: event for event in events}
    assert "Debt Bridge" in event_by_title
    assert event_by_title["Debt Bridge"].targets == (
        "panel:finance",
        "stat:cash",
        "stat:runway",
    )


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
    gate_event = next(event for event in events if event.title == "Gate Command")
    assert "panel:endgame" in gate_event.targets
    assert "summary:timeline" in gate_event.targets
    assert any(
        target.startswith("panel:") and target not in {"panel:endgame"}
        for target in gate_event.targets
    )
    assert events[0].title == "Turn 1 Resolved"
    if "Cash Changed" in titles:
        cash_index = next(
            index for index, event in enumerate(events) if event.title == "Cash Changed"
        )
        gate_index = next(
            index for index, event in enumerate(events) if event.title == "Gate Command"
        )
        assert gate_index < cash_index


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
    assert any(action.label == "Hotspot Review" for action in actions)


def test_run_scene_opening_endgame_panel_pushes_cockpit_brief_event() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=17),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._set_deep_panel("endgame")

        assert any(event.payload.title == "Endgame Cockpit" for event in scene._events)
        assert scene._motion_pulses.get("panel:endgame") > 0
    finally:
        pygame.quit()


def test_run_scene_endgame_cockpit_command_pushes_handoff_event() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=19),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._set_deep_panel("endgame")
        panel = scene.deep_panel
        assert panel is not None
        hotspot_action = next(
            action for action in panel.actions if action.label == "Hotspot Review"
        )

        scene._run_endgame_cockpit_command(hotspot_action.command)

        expected_panel = scene._inspector_key_for_command(
            hotspot_action.command
        ) or scene._workspace_panel_key_for_command(hotspot_action.command)
        assert expected_panel is not None
        assert any(event.payload.title == "Cockpit Handoff" for event in scene._events)
        assert scene._deep_panel_key == expected_panel
    finally:
        pygame.quit()


def test_run_scene_coalesces_duplicate_events() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=23),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        payload = FrontendEvent(
            title="Endgame Cockpit",
            detail="Blocked paths: 2/4 | next review_board",
            severity="warning",
            ttl=5.2,
        )
        scene.push_event(payload)
        scene.push_event(payload)

        assert len(scene._events) == 1
        assert scene._events[0].payload.title == "Endgame Cockpit"
        assert scene._events[0].time_left == payload.ttl
    finally:
        pygame.quit()


def test_run_scene_info_event_ttl_shortens_when_queue_is_dense() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        pygame.display.set_mode((880, 640), pygame.HIDDEN)
        state = create_new_game("NEXUS TECH", "Nexus One")
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=24),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._set_deep_panel("finance")
        for index in range(4):
            scene.push_event(
                FrontendEvent(
                    title=f"Queue {index}",
                    detail="Background motion.",
                    severity="info",
                    ttl=5.0,
                )
            )

        payload = FrontendEvent(
            title="Compact Feed",
            detail="Queue density should shorten this card.",
            severity="info",
            ttl=6.0,
        )
        scene.push_event(payload)

        assert scene._events[0].payload.title == "Compact Feed"
        assert scene._events[0].time_left < payload.ttl
    finally:
        pygame.quit()


def test_pulse_bank_reports_live_count_and_total_intensity() -> None:
    bank = PulseBank(decay=2.0)

    bank.trigger("feed", intensity=0.5)
    bank.trigger("panel:finance", intensity=0.8)

    assert bank.live_count() == 2
    assert bank.total_intensity() == 1.3

    bank.update(1.0)

    assert bank.live_count() == 0
    assert bank.total_intensity() == 0.0


def test_pulse_bank_prune_drops_weak_unprotected_pulses_first() -> None:
    bank = PulseBank(decay=2.0)

    bank.trigger("feed", intensity=0.7)
    bank.trigger("panel:endgame", intensity=0.6)
    bank.trigger("busy:low", intensity=0.08)
    bank.trigger("busy:mid", intensity=0.12)
    bank.trigger("busy:high", intensity=0.4)

    removed = bank.prune(
        max_count=3,
        min_value=0.15,
        protected_prefixes=("feed", "panel:endgame"),
    )

    assert removed == 2
    assert bank.live_count() == 3
    assert bank.get("feed") > 0
    assert bank.get("panel:endgame") > 0
    assert bank.get("busy:high") > 0
    assert bank.get("busy:low") == 0.0
    assert bank.get("busy:mid") == 0.0


def test_motion_mode_scales_or_disables_new_pulses() -> None:
    assert normalize_motion_mode("reduced") is MotionMode.REDUCED

    reduced_bank = PulseBank(decay=2.0, intensity_scale=MotionMode.REDUCED.pulse_scale)
    reduced_bank.trigger("feed", intensity=1.0)

    assert reduced_bank.live_count() == 1
    assert round(reduced_bank.get("feed"), 2) == 0.38

    off_bank = PulseBank(decay=2.0, intensity_scale=MotionMode.OFF.pulse_scale)
    off_bank.trigger("feed", intensity=1.0)

    assert off_bank.live_count() == 0
    assert off_bank.get("feed") == 0.0


def test_scene_entry_transition_tracks_motion_mode() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        full_scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=61),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
            entry_transition="title_to_run",
        )
        reduced_scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=62),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
            motion_mode=MotionMode.REDUCED,
            entry_transition="title_to_run",
        )
        off_scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=63),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
            motion_mode=MotionMode.OFF,
            entry_transition="title_to_run",
        )

        assert full_scene.scene_transition_key == "title_to_run"
        assert full_scene.scene_transition_active()
        assert reduced_scene.scene_transition_active()
        assert not off_scene.scene_transition_active()
        assert full_scene._entity_motion_strength(
            "panel:products"
        ) > reduced_scene._entity_motion_strength("panel:products")
        assert reduced_scene._entity_motion_strength("panel:products") > 0
        assert off_scene._entity_motion_strength("panel:products") == 0
        phase_before = full_scene._entity_motion_phase()
        full_scene.update(1.0)

        assert full_scene._entity_motion_phase() > phase_before
        assert full_scene.scene_transition_progress() == 1.0
        assert not full_scene.scene_transition_active()
    finally:
        pygame.quit()


def test_run_scene_busy_motion_bank_shortens_info_ttl_further() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        quiet_scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=64),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )
        busy_scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=65),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )
        payload = FrontendEvent(
            title="Queue Watch",
            detail="Info card for pressure test.",
            severity="info",
            ttl=6.0,
        )

        quiet_ttl = quiet_scene._normalized_event_payload(payload).ttl
        for index in range(12):
            busy_scene._motion_pulses.trigger(f"busy:{index}", intensity=0.7, decay=1.8)
        busy_ttl = busy_scene._normalized_event_payload(payload).ttl

        assert busy_ttl < quiet_ttl
    finally:
        pygame.quit()


def test_run_scene_busy_motion_bank_dampens_feed_pulse() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        quiet_scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=66),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )
        busy_scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=67),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )
        payload = FrontendEvent(
            title="Queue Watch",
            detail="Info card for feed damping.",
            severity="info",
            ttl=5.0,
            targets=("panel:finance",),
        )

        quiet_scene.push_event(payload)
        quiet_feed = quiet_scene._motion_pulses.get("feed")
        for index in range(12):
            busy_scene._motion_pulses.trigger(f"busy:{index}", intensity=0.7, decay=1.8)
        busy_scene.push_event(payload)
        busy_feed = busy_scene._motion_pulses.get("feed")

        assert busy_feed < quiet_feed
    finally:
        pygame.quit()


def test_run_scene_stabilize_motion_bank_prunes_dense_low_value_pulses() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=71),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._set_deep_panel("finance")
        scene._motion_pulses.trigger("feed", intensity=0.8, decay=1.8)
        scene._motion_pulses.trigger("panel:finance", intensity=0.7, decay=1.8)
        for index in range(24):
            scene._motion_pulses.trigger(f"busy:{index}", intensity=0.1, decay=1.8)

        before = scene._motion_pulses.live_count()
        scene._stabilize_motion_bank()
        after = scene._motion_pulses.live_count()

        assert after < before
        assert scene._motion_pulses.get("feed") > 0
        assert scene._motion_pulses.get("panel:finance") > 0
    finally:
        pygame.quit()


def test_run_scene_event_backlog_keeps_priority_warning_cards() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        pygame.display.set_mode((880, 640), pygame.HIDDEN)
        state = create_new_game("NEXUS TECH", "Nexus One")
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=25),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene.push_event(
            FrontendEvent(
                title="Gate Command",
                detail="Priority warning should survive queue trimming.",
                severity="warning",
                ttl=5.0,
                motion="flash",
                targets=("panel:endgame", "panel:finance"),
            )
        )
        for index in range(8):
            scene.push_event(
                FrontendEvent(
                    title=f"Info {index}",
                    detail="Lower-priority queue filler.",
                    severity="info",
                    ttl=4.0,
                )
            )

        assert len(scene._events) <= scene._event_retention_limit()
        assert any(event.payload.title == "Gate Command" for event in scene._events)
    finally:
        pygame.quit()


def test_run_scene_footer_status_lines_reflect_workspace_and_picker() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=29),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._set_deep_panel("endgame")
        workspace_line, hint_line = scene._footer_status_lines()
        assert "Endgame: Endgame / Exit Board" in workspace_line
        assert "Gate:" in workspace_line
        assert "Hotspot:" in workspace_line
        assert hint_line.startswith("Watch:")

        picker = ContextPicker(
            title="Capital Plan",
            description="Choose the next capital posture.",
            severity="warning",
            options=(
                PickerOption(
                    key_hint="1",
                    title="Balanced",
                    description="Hold a balanced reserve posture.",
                    request=ActionRequest(
                        action=TurnAction.SET_CAPITAL_PLAN,
                        context=ActionContext(),
                        label=TurnAction.SET_CAPITAL_PLAN.value,
                    ),
                ),
            ),
        )
        scene._set_context_picker(picker)
        picker_line, _ = scene._footer_status_lines()

        assert picker_line.startswith("Picker: Capital Plan")
    finally:
        pygame.quit()


def test_run_scene_endgame_footer_status_compacts_commands_on_small_windows() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        pygame.display.set_mode((920, 640), pygame.HIDDEN)
        state = create_new_game("NEXUS TECH", "Nexus One")
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=31),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._set_deep_panel("endgame")
        workspace_line, _hint_line = scene._footer_status_lines()

        assert "Endgame: Endgame / Exit Board" in workspace_line
        assert "set_board_reset_cont..." not in workspace_line
        assert "Gate:" in workspace_line
    finally:
        pygame.quit()


def test_run_scene_hover_tooltip_rect_clamps_inside_surface() -> None:
    pygame, fonts, surface = _build_pygame_bundle()
    try:
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=32),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        rect = scene._hover_tooltip_rect(
            surface,
            mouse_x=950,
            mouse_y=620,
            width=320,
            height=88,
        )

        assert rect.left >= 16
        assert rect.top >= 16
        assert rect.right <= surface.get_width() - 16
        assert rect.bottom <= surface.get_height() - 16
    finally:
        pygame.quit()


def test_run_scene_endgame_panel_action_tooltip_mentions_handoff_destination() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=31),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._set_deep_panel("endgame")
        panel = scene.deep_panel
        assert panel is not None
        action = next(entry for entry in panel.actions if entry.label == "Hotspot Review")
        hint = scene._describe_click_target(
            ClickTarget("panel_action", action.command, _surface.get_rect())
        )

        assert "from the cockpit" in hint
        assert "hand off into" in hint
    finally:
        pygame.quit()


def test_run_scene_inspector_primary_action_summary_reflects_ready_state() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = _build_enriched_2d_state()
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=41),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._open_inspector("pipeline")
        scene._select_inspector_section("releases")

        summary = scene._selected_inspector_primary_action_summary()
        badge = scene._inspector_item_action_badge(scene._selected_inspector_item())

        assert summary.startswith("Next: 1 ")
        assert badge is not None
        assert badge[0] in {"READY", "BLOCKED"}
    finally:
        pygame.quit()


def test_game_view_model_uses_compact_score_label() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")

    view_model = build_game_view_model(state, selected_product_id=state.products[0].id.hex)

    assert not view_model.score_label.startswith("RunScore(")
    assert "(" in view_model.score_label


def test_run_scene_overlay_button_detail_compacts_long_copy() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=43),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        detail = scene._overlay_button_detail(
            TurnAction.REVIEW_FINANCE.value,
            "Refresh reserve, debt, and capital posture for the whole company.",
            enabled=True,
        )

        assert len(detail) <= 32
    finally:
        pygame.quit()


def test_run_scene_footer_button_detail_compacts_on_narrow_layout() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=47),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        compact_detail = scene._footer_button_detail(
            scenes_module._ACTION_BUTTONS[0],
            enabled=True,
            button_cols=4,
        )
        narrow_detail = scene._footer_button_detail(
            scenes_module._ACTION_BUTTONS[0],
            enabled=True,
            button_cols=5,
        )
        button_cols, button_height, footer_band_height = scene._footer_layout_metrics(820, 320)
        rows = max(1, (len(scenes_module._ACTION_BUTTONS) + button_cols - 1) // button_cols)

        assert len(compact_detail) <= 24
        assert len(narrow_detail) <= 28
        assert button_cols == 5
        assert footer_band_height == 48
        assert rows * button_height + max(0, rows - 1) * 10 <= 320 - footer_band_height
    finally:
        pygame.quit()


def test_run_scene_inspector_item_line_limit_tightens_for_small_cards() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=49),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        assert scene._inspector_item_line_limit(72, 540) == 1
        assert scene._inspector_item_line_limit(96, 700) == 3
    finally:
        pygame.quit()


def test_run_scene_inspector_focus_summary_text_compacts_for_small_layouts() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = _build_enriched_2d_state()
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=50),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._set_deep_panel("pipeline")
        scene._open_inspector("pipeline")
        item = scene._selected_inspector_item()

        assert item is not None
        compact_summary = scene._inspector_focus_summary_text(item, compact=True)
        full_summary = scene._inspector_focus_summary_text(item, compact=False)

        assert compact_summary.startswith("Focus:")
        assert len(compact_summary) < len(full_summary)
    finally:
        pygame.quit()


def test_run_scene_inspector_items_per_page_tracks_window_size() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=51),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        pygame.display.set_mode((820, 620), pygame.HIDDEN)
        assert scene._inspector_items_per_page() == 2

        pygame.display.set_mode((960, 640), pygame.HIDDEN)
        assert scene._inspector_items_per_page() == 3
    finally:
        pygame.quit()


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


def test_run_scene_pause_and_back_hotkeys_are_distinct() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=71),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p, unicode="p"))
        assert scene._pause_overlay_visible
        scene.draw(_surface)
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode=""))
        assert not scene._pause_overlay_visible

        scene._set_deep_panel("finance")
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode=""))
        assert scene._deep_panel_key is None
        assert not scene._pause_overlay_visible
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode=""))
        assert scene._pause_overlay_visible
        scene.draw(_surface)
        assert not scene.should_exit
    finally:
        pygame.quit()


def test_run_scene_pause_menu_returns_to_title_shell(tmp_path: Path) -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        saved_slots: list[str] = []
        coordinator = SaveLoadCoordinator(tmp_path / "pause-menu.db")

        def save_callback(state, rng, slot_name):
            saved_slots.append(slot_name)

        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=72),
            slot_name="active",
            save_callback=save_callback,
            dirty=True,
            show_ready_event=False,
            return_scene_factory=lambda: TitleScene(
                pygame=pygame,
                fonts=fonts,
                state=create_new_game("NEXUS TECH", "Nexus One"),
                rng=RandomSource(seed=73),
                slot_name="active",
                save_callback=save_callback,
                coordinator=coordinator,
                initial_mode="menu",
            ),
        )

        scene._set_pause_overlay_visible(True)
        scene._dispatch_click_target(ClickTarget("pause_menu", "", _surface.get_rect()))
        next_scene = scene.pop_next_scene()

        assert saved_slots == ["active"]
        assert isinstance(next_scene, TitleScene)
        assert not scene.should_exit
    finally:
        pygame.quit()


def test_run_scene_hover_hints_cover_pause_back_help_controls() -> None:
    pygame, fonts, surface = _build_pygame_bundle()
    try:
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=73),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )
        rect = surface.get_rect()

        assert "open Pause" in scene._describe_click_target(ClickTarget("pause_toggle", "", rect))
        assert "close the current overlay" in scene._describe_click_target(
            ClickTarget("run_back", "", rect)
        )
        assert "control guide" in scene._describe_click_target(ClickTarget("open_help", "", rect))
        assert "save the current run" in scene._describe_click_target(
            ClickTarget("pause_save", "", rect)
        )
        assert "return to the 2D title menu" in scene._describe_click_target(
            ClickTarget("pause_menu", "", rect)
        )
        assert "close Help" in scene._describe_click_target(ClickTarget("close_help", "", rect))
    finally:
        pygame.quit()


def test_run_scene_partner_binding_moves_to_o_so_p_can_pause() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=74),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        assert scene._intent_for_key(pygame.K_o) is FrontendIntent.CREATE_PARTNERSHIP
        assert scene._intent_for_key(pygame.K_p) is None
        assert any(
            button.key_hint == "O" and button.title == "Partner"
            for button in scenes_module._ACTION_BUTTONS
        )
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
        assert scene._action_feedback_cues
        assert scene._action_feedback_cues[0].family == "finance"
        assert "panel:finance" in scene._action_feedback_cues[0].targets
    finally:
        pygame.quit()


def test_run_scene_action_request_triggers_motion_pulses() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=41),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._apply_action_request(
            ActionRequest(
                action=TurnAction.IMPROVE_QUALITY,
                context=ActionContext(target_product_id=state.products[0].id),
                label=TurnAction.IMPROVE_QUALITY.value,
            )
        )

        product_key = f"product:{state.products[0].id.hex}"
        assert scene._motion_pulses.get("feed") > 0
        assert scene._motion_pulses.get("panel:products") > 0
        assert scene._motion_pulses.get(product_key) > 0
        assert scene._motion_pulses.get(f"{product_key}:quality") > 0
        assert scene._action_feedback_cues
        assert scene._action_feedback_cues[0].family == "product"
        assert f"product:{state.products[0].id.hex}" in scene._action_feedback_cues[0].targets
        assert scene._impact_cues
        assert any("Quality" in cue.label for cue in scene._impact_cues)
    finally:
        pygame.quit()


def test_run_scene_blocked_action_triggers_blocked_feedback() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=43),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._run_command(TurnAction.SCREEN_CANDIDATE.value)

        assert scene._action_feedback_cues
        cue = scene._action_feedback_cues[0]
        assert cue.outcome == "blocked"
        assert cue.label.startswith("Blocked:")
        assert cue.detail.startswith("Source candidates first")
        assert "feed" in cue.targets
        assert scene._motion_pulses.get("feed") > 0
        actor_states = {clip.key: clip.state for clip in scene._run_actor_sprite_clips()}
        assert actor_states["founder"] == "blocked"
        assert actor_states["product"] == "blocked"
    finally:
        pygame.quit()


def test_run_actor_sprite_clips_react_to_action_feedback() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=42),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._apply_action_request(
            ActionRequest(
                action=TurnAction.IMPROVE_QUALITY,
                context=ActionContext(target_product_id=state.products[0].id),
                label=TurnAction.IMPROVE_QUALITY.value,
            )
        )

        actor_states = {clip.key: clip.state for clip in scene._run_actor_sprite_clips()}
        assert actor_states["founder"] == "coaching"
        assert actor_states["product"] == "shipping"
    finally:
        pygame.quit()


def test_run_scene_impact_cues_cover_business_deltas() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        previous_state = create_new_game("NEXUS TECH", "Nexus One")
        current_state = previous_state.model_copy(deep=True)
        current_state.company.cash_on_hand += Decimal("1200.00")
        current_state.company.reputation += 2
        current_state.finance.board_pressure += 3
        current_state.products[0].user_count += 25
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=previous_state,
            rng=RandomSource(seed=42),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._queue_impact_cues(previous_state, current_state)

        labels = {cue.label for cue in scene._impact_cues}
        assert {"Cash", "Users", "Reputation", "Board"} <= labels
        assert scene._motion_pulses.get("stat:cash") > 0
        assert scene._motion_pulses.get("stat:users") > 0
        assert scene._motion_pulses.get("stat:board_pressure") > 0
    finally:
        pygame.quit()


def test_run_scene_action_feedback_respects_motion_off() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=42),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
            motion_mode=MotionMode.OFF,
        )

        scene._run_command(TurnAction.SET_CAPITAL_PLAN.value)

        assert scene._context_picker is not None
        assert not scene._action_feedback_cues
        assert not scene._impact_cues
    finally:
        pygame.quit()


def test_run_scene_overlay_transition_tracks_enter_and_exit() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=43),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._set_deep_panel("finance")
        scene.update(1 / 60)
        assert scene.overlay_transition_active()
        scene.update(1.0)
        assert not scene.overlay_transition_active()

        scene._set_deep_panel(None)
        assert scene.overlay_transition_active()
        scene.update(1.0)
        assert not scene.overlay_transition_active()
    finally:
        pygame.quit()


def test_run_scene_overlay_transition_respects_motion_off() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=44),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
            motion_mode=MotionMode.OFF,
        )

        scene._set_deep_panel("finance")
        scene.update(1 / 60)

        assert not scene.overlay_transition_active()
    finally:
        pygame.quit()


def test_run_scene_product_and_risk_drama_layers_respect_motion_modes() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        state.company.cash_on_hand = Decimal("900.00")
        state.finance.board_pressure = 74
        state.products[0].quality = 84
        state.products[0].bug_level = 66
        state.products[0].technical_debt = 74
        full_scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state.model_copy(deep=True),
            rng=RandomSource(seed=46),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )
        off_scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state.model_copy(deep=True),
            rng=RandomSource(seed=47),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
            motion_mode=MotionMode.OFF,
        )

        assert full_scene.product_drama_active()
        assert full_scene.risk_drama_active()
        assert not off_scene.product_drama_active()
        assert not off_scene.risk_drama_active()
    finally:
        pygame.quit()


def test_run_scene_pending_choice_cue_tracks_resolution_feedback() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        state.pending_event = PendingEvent(
            event_id="audit_pending_choice",
            category=EventCategory.MARKET_OPPORTUNITY,
            title="Audit Pending Choice",
            description="A deterministic pending event for 2D feedback coverage.",
            triggered_turn=state.company.current_turn,
            cooldown_turns=0,
            options=[
                EventOption(
                    id="stabilize",
                    label="Stabilize rollout",
                    description="Choose a lower-risk response path.",
                )
            ],
        )
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=48),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._queue_pending_choice_cue(
            state.pending_event.options[0].label,
            "Resolved the event with a visible consequence flash.",
        )

        assert scene.pending_choice_active()
        assert scene._motion_pulses.get("overlay:pending_choice") > 0
        scene.update(2.0)
        assert not scene.pending_choice_active()
    finally:
        pygame.quit()


def test_run_scene_pending_choice_preview_respects_motion_modes() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        state.pending_event = PendingEvent(
            event_id="audit_pending_preview",
            category=EventCategory.MARKET_OPPORTUNITY,
            title="Audit Pending Preview",
            description="A deterministic pending event for preview motion coverage.",
            triggered_turn=state.company.current_turn,
            cooldown_turns=0,
            options=[
                EventOption(
                    id="stabilize",
                    label="Stabilize rollout",
                    description="Protect quality and trust before scaling.",
                ),
                EventOption(
                    id="stretch",
                    label="Stretch the plan",
                    description="Accept cost risk and pressure to chase upside.",
                ),
            ],
        )
        full_scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state.model_copy(deep=True),
            rng=RandomSource(seed=49),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )
        off_scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state.model_copy(deep=True),
            rng=RandomSource(seed=50),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
            motion_mode=MotionMode.OFF,
        )

        assert full_scene.pending_choice_preview_active()
        assert full_scene._pending_option_tone("Stabilize rollout", "Protect quality") == "success"
        assert full_scene._pending_option_tone("Stretch the plan", "Accept risk") == "warning"
        assert not off_scene.pending_choice_preview_active()
    finally:
        pygame.quit()


def test_run_scene_late_game_choreography_respects_motion_modes() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        full_scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state.model_copy(deep=True),
            rng=RandomSource(seed=51),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )
        off_scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state.model_copy(deep=True),
            rng=RandomSource(seed=52),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
            motion_mode=MotionMode.OFF,
        )

        full_scene._queue_late_game_choreography(TurnAction.SET_TERMINAL_SOLVENCY_MANDATE.value)
        off_scene._queue_late_game_choreography(TurnAction.SET_TERMINAL_SOLVENCY_MANDATE.value)

        assert full_scene.late_game_choreography_active()
        assert full_scene._late_game_choreography_cues[0].family == "endgame"
        assert full_scene._motion_pulses.get("panel:endgame") > 0
        assert not off_scene.late_game_choreography_active()
        full_scene.update(2.0)
        assert not full_scene.late_game_choreography_active()
    finally:
        pygame.quit()


def test_run_scene_late_game_path_repairs_use_specific_choreography() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state.model_copy(deep=True),
            rng=RandomSource(seed=53),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        expectations = (
            (
                TurnAction.SET_PATH_CONTROL_MATRIX.value,
                "IPO Controls",
                "ipo",
                "panel:customers",
            ),
            (
                TurnAction.SET_PATH_RESILIENCE_GRID.value,
                "M&A Resilience",
                "m&a",
                "panel:partnerships",
            ),
            (
                TurnAction.SET_PATH_CASH_WATERFALL.value,
                "Independence Cash",
                "cash",
                "panel:finance",
            ),
            (
                TurnAction.SET_BOARD_RESET_CONTINGENCY_BUFFER.value,
                "Reset Buffer",
                "reset",
                "panel:finance",
            ),
        )
        for command, label, family, target in expectations:
            scene._late_game_choreography_cues.clear()
            scene._queue_late_game_choreography(command)
            cue = scene._late_game_choreography_cues[0]

            assert cue.label == label
            assert cue.family == family
            assert "panel:endgame" in cue.targets
            assert target in cue.targets
    finally:
        pygame.quit()


def test_run_scene_outcome_cinematic_respects_motion_modes() -> None:
    pygame, fonts, surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        state.company.game_over = True
        state.company.cash_on_hand = Decimal("-125.00")
        full_scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state.model_copy(deep=True),
            rng=RandomSource(seed=53),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )
        off_scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state.model_copy(deep=True),
            rng=RandomSource(seed=54),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
            motion_mode=MotionMode.OFF,
        )

        full_scene.update(1 / 60)
        full_scene.draw(surface)
        off_scene.update(1 / 60)
        off_scene.draw(surface)

        assert full_scene.outcome_cinematic_active()
        assert not off_scene.outcome_cinematic_active()
    finally:
        pygame.quit()


def test_2d_actor_sprite_layers_respect_motion_modes() -> None:
    pygame, fonts, surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        previous_state = state.model_copy(deep=True)
        resolution = resolve_turn(state.model_copy(deep=True), RandomSource(seed=55))
        run_scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state.model_copy(deep=True),
            rng=RandomSource(seed=56),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )
        run_off_scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state.model_copy(deep=True),
            rng=RandomSource(seed=57),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
            motion_mode=MotionMode.OFF,
        )
        summary_scene = TurnSummaryScene(
            pygame=pygame,
            fonts=fonts,
            state=resolution.state,
            rng=RandomSource(seed=58),
            slot_name="active",
            save_callback=lambda *_args: None,
            previous_state=previous_state,
            resolution=resolution,
            selected_product_id=resolution.state.products[0].id.hex,
            dirty=False,
        )
        summary_off_scene = TurnSummaryScene(
            pygame=pygame,
            fonts=fonts,
            state=resolution.state,
            rng=RandomSource(seed=59),
            slot_name="active",
            save_callback=lambda *_args: None,
            previous_state=previous_state,
            resolution=resolution,
            selected_product_id=resolution.state.products[0].id.hex,
            dirty=False,
            motion_mode=MotionMode.OFF,
        )

        run_scene.update(1 / 60)
        run_scene.draw(surface)
        summary_scene.update(1 / 60)
        summary_scene.draw(surface)

        assert run_scene.actor_timeline_active()
        assert run_scene.sprite_clips_active()
        _assert_actor_readability_clear(run_scene)
        assert summary_scene.actor_timeline_active()
        assert summary_scene.sprite_clips_active()
        _assert_actor_readability_clear(summary_scene)
        assert not run_off_scene.actor_timeline_active()
        assert not run_off_scene.sprite_clips_active()
        assert not summary_off_scene.actor_timeline_active()
        assert not summary_off_scene.sprite_clips_active()
    finally:
        pygame.quit()


def test_title_and_review_actor_sprite_layers_respect_motion_modes(tmp_path: Path) -> None:
    pygame, fonts, surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        state.company.game_over = True
        state.company.cash_on_hand = Decimal("-125.00")
        coordinator = SaveLoadCoordinator(tmp_path / "actor-scenes.db")
        title_scene = TitleScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=60),
            slot_name="active",
            save_callback=lambda *_args: None,
            coordinator=coordinator,
            initial_mode="menu",
        )
        title_off_scene = TitleScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=61),
            slot_name="active",
            save_callback=lambda *_args: None,
            coordinator=coordinator,
            initial_mode="menu",
            motion_mode=MotionMode.OFF,
        )
        review_scene = ReviewScene(
            pygame=pygame,
            fonts=fonts,
            state=state.model_copy(deep=True),
            rng=RandomSource(seed=62),
            slot_name="active",
            save_callback=lambda *_args: None,
            view_model=build_run_review_view_model(state),
            accent=DANGER,
            primary_title="Esc Close",
            primary_detail="Leave the 2D shell.",
            return_scene_factory=None,
            allow_save=False,
            dirty=False,
        )
        review_off_scene = ReviewScene(
            pygame=pygame,
            fonts=fonts,
            state=state.model_copy(deep=True),
            rng=RandomSource(seed=63),
            slot_name="active",
            save_callback=lambda *_args: None,
            view_model=build_run_review_view_model(state),
            accent=DANGER,
            primary_title="Esc Close",
            primary_detail="Leave the 2D shell.",
            return_scene_factory=None,
            allow_save=False,
            dirty=False,
            motion_mode=MotionMode.OFF,
        )

        title_scene.update(1 / 60)
        title_scene.draw(surface)
        review_scene.update(1 / 60)
        review_scene.draw(surface)

        assert title_scene.actor_timeline_active()
        assert title_scene.sprite_clips_active()
        assert title_scene.title_actor_active()
        _assert_actor_readability_clear(title_scene)
        assert review_scene.actor_timeline_active()
        assert review_scene.sprite_clips_active()
        assert review_scene.review_actor_active()
        _assert_actor_readability_clear(review_scene)
        assert not title_off_scene.actor_timeline_active()
        assert not title_off_scene.sprite_clips_active()
        assert not title_off_scene.title_actor_active()
        assert not review_off_scene.actor_timeline_active()
        assert not review_off_scene.sprite_clips_active()
        assert not review_off_scene.review_actor_active()
    finally:
        pygame.quit()


def test_run_overlay_actor_sprite_layers_cover_inspector_and_endgame() -> None:
    pygame, fonts, surface = _build_pygame_bundle()
    try:
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=64),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )
        off_scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=65),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
            motion_mode=MotionMode.OFF,
        )

        scene._set_deep_panel("pipeline")
        scene._open_inspector("pipeline")
        scene.update(1 / 60)
        scene.draw(surface)
        assert scene.inspector_actor_active()
        _assert_actor_readability_clear(scene)

        scene._close_inspector()
        scene._set_deep_panel("endgame")
        scene.update(1 / 60)
        scene.draw(surface)
        assert scene.endgame_actor_active()
        _assert_actor_readability_clear(scene)

        off_scene._set_deep_panel("pipeline")
        off_scene._open_inspector("pipeline")
        assert not off_scene.inspector_actor_active()
        off_scene._close_inspector()
        off_scene._set_deep_panel("endgame")
        assert not off_scene.endgame_actor_active()
    finally:
        pygame.quit()


def test_run_scene_event_queue_visible_count_drops_when_overlay_is_open() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=45),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        assert scene._event_queue_visible_count(320) == 4
        scene._set_deep_panel("finance")
        assert scene._event_queue_visible_count(320) == 2
        assert scene._event_queue_visible_count(170) == 2
        pygame.display.set_mode((880, 640), pygame.HIDDEN)
        for index in range(5):
            scene.push_event(
                FrontendEvent(
                    title=f"Dense {index}",
                    detail="Dense queue card.",
                    severity="info",
                    ttl=4.0,
                )
            )
        assert scene._event_queue_visible_count(320) == 1
    finally:
        pygame.quit()


def test_run_scene_panel_and_picker_overlay_motion_are_triggered() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=43),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._set_deep_panel("finance")
        scene._run_command(TurnAction.SET_CAPITAL_PLAN.value)

        assert scene._deep_panel_key == "finance"
        assert scene._context_picker is not None
        assert scene._motion_pulses.get("overlay:panel") > 0
        assert scene._motion_pulses.get("overlay:picker") > 0
    finally:
        pygame.quit()


def test_run_scene_board_command_triggers_board_and_endgame_motion() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=47),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )

        scene._run_command(TurnAction.START_BOARD_RECOVERY_PLAN.value)

        assert scene._deep_panel_key == "board"
        assert scene._motion_pulses.get("panel:board") > 0
        assert scene._motion_pulses.get("stat:board_pressure") > 0
        assert scene._motion_pulses.get("panel:endgame") > 0
    finally:
        pygame.quit()


def test_run_scene_reduced_motion_scales_command_pulses() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        full_scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=51),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
        )
        reduced_scene = RunScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=52),
            slot_name="active",
            save_callback=lambda *_args: None,
            show_ready_event=False,
            motion_mode=MotionMode.REDUCED,
        )

        full_scene._set_deep_panel("endgame")
        reduced_scene._set_deep_panel("endgame")

        assert reduced_scene.motion_mode is MotionMode.REDUCED
        assert (
            0
            < reduced_scene._motion_pulses.get("panel:endgame")
            < full_scene._motion_pulses.get("panel:endgame")
        )
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
        assert any("Best:" in line for line in meta_lines)
        scene.draw(surface)
    finally:
        pygame.quit()


def test_title_scene_meta_board_compacts_summary_when_space_is_tight(tmp_path: Path) -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        coordinator = SaveLoadCoordinator(tmp_path / "title-compact.db")
        scene = TitleScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=15),
            slot_name="active",
            save_callback=lambda *_args: None,
            coordinator=coordinator,
            initial_mode="meta",
        )

        compact = scene._meta_board_compact_layout(pygame.Rect(0, 0, 900, 240))
        lines = scene._meta_board_summary_lines(compact)

        assert compact is True
        assert len(lines) == 4
        assert all("Recommendation:" not in line for line in lines)
    finally:
        pygame.quit()


def test_title_scene_mode_and_overlay_motion_are_triggered(tmp_path: Path) -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        coordinator = SaveLoadCoordinator(tmp_path / "title-motion.db")
        scene = TitleScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=17),
            slot_name="active",
            save_callback=lambda *_args: None,
            coordinator=coordinator,
            initial_mode="menu",
        )

        scene._handle_menu_action("meta")
        scene._open_wizard_text_modal("company")

        assert scene._mode == "meta"
        assert scene._text_input is not None
        assert scene._motion_pulses.get("title:mode:meta") > 0
        assert scene._motion_pulses.get("title:overlay:text_input") > 0
    finally:
        pygame.quit()


def test_title_scene_preserves_motion_mode_when_loading_run(tmp_path: Path) -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        coordinator = SaveLoadCoordinator(tmp_path / "title-motion-mode.db")
        loaded_state = create_new_game("NEXUS TECH", "Nexus One")
        scene = TitleScene(
            pygame=pygame,
            fonts=fonts,
            state=loaded_state,
            rng=RandomSource(seed=18),
            slot_name="active",
            save_callback=lambda *_args: None,
            coordinator=coordinator,
            initial_mode="menu",
            motion_mode=MotionMode.OFF,
        )

        scene._open_loaded_game(loaded_state, RandomSource(seed=19), "active")

        assert scene.motion_mode is MotionMode.OFF
        assert scene._motion_pulses.live_count() == 0
        assert scene._next_scene is not None
        assert scene._next_scene.motion_mode is MotionMode.OFF
        assert scene._next_scene.scene_transition_key == "title_to_run"
        assert not scene._next_scene.scene_transition_active()
    finally:
        pygame.quit()


def test_title_scene_feed_visible_count_tracks_sidebar_height(tmp_path: Path) -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        coordinator = SaveLoadCoordinator(tmp_path / "title-feed.db")
        scene = TitleScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=21),
            slot_name="active",
            save_callback=lambda *_args: None,
            coordinator=coordinator,
            initial_mode="menu",
        )

        assert scene._title_feed_visible_count(160) == 2
        assert scene._title_feed_visible_count(220) == 3
        assert scene._title_feed_visible_count(320) == 4
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


def test_surfaced_2d_commands_have_motion_coverage(tmp_path: Path) -> None:
    commands = _collect_surfaced_2d_commands(tmp_path)
    profiles = {
        command: describe_action_motion_profile(command)
        for command in sorted(commands)
        if command != TurnAction.END_TURN.value
    }
    assert profiles
    assert set(profiles.values()) == {"specific"}


def test_high_priority_2d_commands_use_specific_motion_profiles() -> None:
    for command in (
        TurnAction.REVIEW_BOARD.value,
        TurnAction.REVIEW_FINANCE.value,
        TurnAction.REVIEW_CUSTOMERS.value,
        TurnAction.REVIEW_PARTNERSHIPS.value,
        TurnAction.REVIEW_PIPELINE.value,
        TurnAction.REVIEW_TEAM.value,
        TurnAction.VIEW_REPORT.value,
        TurnAction.SET_FUNCTIONAL_BUDGET.value,
        TurnAction.SET_CAPITAL_PLAN.value,
        TurnAction.SET_BOARD_RESET_CONTINGENCY_BUFFER.value,
        TurnAction.SET_PATH_CASH_WATERFALL.value,
        TurnAction.TAKE_LOAN.value,
        TurnAction.RAISE_ANGEL.value,
        TurnAction.REPAY_DEBT.value,
        TurnAction.EXECUTE_RESTRUCTURE_PLAN.value,
        TurnAction.REBALANCE_CHANNEL_MIX.value,
        TurnAction.RENEGOTIATE_PARTNERSHIP.value,
        TurnAction.RUN_PARTNER_RECOVERY_SPRINT.value,
        TurnAction.RUN_BILLING_STABILIZATION.value,
    ):
        assert describe_action_motion_profile(command) == "specific", command


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
        scene._focus_inspector_actionable()
        scene._focus_inspector_hotspot()
        filtered_items = scene._filtered_sorted_inspector_items()
        scene._deep_panel_key = "endgame"
        scene._help_overlay_visible = True
        scene.draw(surface)

        assert scene._inspector_sort_mode_label() == "Highest Risk"
        assert scene._inspector_filter_mode_label() == "Attention"
        assert len(filtered_items) <= len(base_items)
        assert scene._active_panel_key() == "pipeline"
        assert scene._motion_pulses.get("inspector:sort") > 0
        assert scene._motion_pulses.get("inspector:filter") > 0
        assert scene._motion_pulses.get("inspector:actionable") > 0
        assert scene._motion_pulses.get("inspector:hotspot") > 0
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
        motion_mode=MotionMode.REDUCED,
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
        assert not scene.summary_metric_sequence_active()
    finally:
        pygame.quit()


def test_turn_summary_scene_metric_sequence_respects_motion_modes() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        previous_state = create_new_game("NEXUS TECH", "Nexus One")
        working_state = apply_action(
            previous_state.model_copy(deep=True),
            TurnAction.IMPROVE_QUALITY,
            context=ActionContext(target_product_id=previous_state.products[0].id),
        ).state
        resolution = resolve_turn(working_state, RandomSource(seed=31))
        full_scene = TurnSummaryScene(
            pygame=pygame,
            fonts=fonts,
            state=resolution.state,
            rng=RandomSource(seed=31),
            slot_name="active",
            save_callback=lambda *_args: None,
            previous_state=previous_state,
            resolution=resolution,
            selected_product_id=resolution.state.products[0].id.hex,
            dirty=True,
        )
        off_scene = TurnSummaryScene(
            pygame=pygame,
            fonts=fonts,
            state=resolution.state,
            rng=RandomSource(seed=32),
            slot_name="active",
            save_callback=lambda *_args: None,
            previous_state=previous_state,
            resolution=resolution,
            selected_product_id=resolution.state.products[0].id.hex,
            dirty=True,
            motion_mode=MotionMode.OFF,
        )

        assert full_scene.summary_metric_sequence_active()
        assert full_scene._summary_metric_reveal_progress(0) == 0.0
        assert not off_scene.summary_metric_sequence_active()
        assert off_scene._summary_metric_reveal_progress(0) == 1.0
    finally:
        pygame.quit()


def test_turn_summary_scene_outcome_lanes_respect_motion_modes() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        previous_state = create_new_game("NEXUS TECH", "Nexus One")
        working_state = apply_action(
            previous_state.model_copy(deep=True),
            TurnAction.IMPROVE_QUALITY,
            context=ActionContext(target_product_id=previous_state.products[0].id),
        ).state
        resolution = resolve_turn(working_state, RandomSource(seed=33))
        full_scene = TurnSummaryScene(
            pygame=pygame,
            fonts=fonts,
            state=resolution.state,
            rng=RandomSource(seed=33),
            slot_name="active",
            save_callback=lambda *_args: None,
            previous_state=previous_state,
            resolution=resolution,
            selected_product_id=resolution.state.products[0].id.hex,
            dirty=True,
        )
        off_scene = TurnSummaryScene(
            pygame=pygame,
            fonts=fonts,
            state=resolution.state,
            rng=RandomSource(seed=34),
            slot_name="active",
            save_callback=lambda *_args: None,
            previous_state=previous_state,
            resolution=resolution,
            selected_product_id=resolution.state.products[0].id.hex,
            dirty=True,
            motion_mode=MotionMode.OFF,
        )

        assert full_scene.summary_outcome_lanes_active()
        assert full_scene._summary_outcome_lane_progress(0) == 0.0
        assert not off_scene.summary_outcome_lanes_active()
        full_scene.update(2.3)
        assert not full_scene.summary_outcome_lanes_active()
    finally:
        pygame.quit()


def test_turn_summary_scene_event_pacing_helpers_track_window_size() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        previous_state = create_new_game("NEXUS TECH", "Nexus One")
        working_state = previous_state.model_copy(deep=True)
        working_state = apply_action(
            working_state,
            TurnAction.IMPROVE_QUALITY,
            context=ActionContext(target_product_id=working_state.products[0].id),
        ).state
        resolution = resolve_turn(working_state, RandomSource(seed=41))
        scene = TurnSummaryScene(
            pygame=pygame,
            fonts=fonts,
            state=resolution.state,
            rng=RandomSource(seed=41),
            slot_name="active",
            save_callback=lambda *_args: None,
            previous_state=previous_state,
            resolution=resolution,
            selected_product_id=resolution.state.products[0].id.hex,
            dirty=True,
        )

        pygame.display.set_mode((960, 640), pygame.HIDDEN)
        scene._events = scene._events[:1]
        assert scene._summary_event_reveal_interval() == 0.45
        assert scene._summary_top_section_ratio(820) == 0.52
        scene._events = scene._events + (
            FrontendEvent(title="Extra 1", detail="Load", severity="info"),
            FrontendEvent(title="Extra 2", detail="Load", severity="warning"),
            FrontendEvent(title="Extra 3", detail="Load", severity="info"),
        )
        assert scene._summary_event_reveal_interval() == 0.5
        assert scene._summary_top_section_ratio(820) == 0.5
        pygame.display.set_mode((1280, 720), pygame.HIDDEN)
        scene._events = scene._events[:1]
        assert scene._summary_event_reveal_interval() == 0.35
        assert scene._summary_strategy_height(140) == 72
        assert scene._summary_timeline_visible_count(130) == 1
        assert scene._summary_timeline_visible_count(200) == 2
        assert scene._summary_timeline_visible_count(320) == 3
        for index in range(8):
            scene._motion_pulses.trigger(f"busy:{index}", intensity=0.7, decay=1.8)
        assert scene._summary_motion_pressure_ratio() > 0
        assert scene._summary_event_reveal_interval() > 0.35
    finally:
        pygame.quit()


def test_turn_summary_scene_busy_motion_bank_dampens_timeline_pulse() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        previous_state = create_new_game("NEXUS TECH", "Nexus One")
        working_state = previous_state.model_copy(deep=True)
        resolution = resolve_turn(working_state, RandomSource(seed=68))
        quiet_scene = TurnSummaryScene(
            pygame=pygame,
            fonts=fonts,
            state=resolution.state,
            rng=RandomSource(seed=68),
            slot_name="active",
            save_callback=lambda *_args: None,
            previous_state=previous_state,
            resolution=resolution,
            selected_product_id=resolution.state.products[0].id.hex,
            dirty=True,
        )
        busy_scene = TurnSummaryScene(
            pygame=pygame,
            fonts=fonts,
            state=resolution.state,
            rng=RandomSource(seed=69),
            slot_name="active",
            save_callback=lambda *_args: None,
            previous_state=previous_state,
            resolution=resolution,
            selected_product_id=resolution.state.products[0].id.hex,
            dirty=True,
        )
        event = FrontendEvent(
            title="Timeline Pulse",
            detail="Pressure damping test.",
            severity="info",
            targets=("panel:finance",),
        )

        quiet_scene._motion_pulses = PulseBank(decay=1.9)
        busy_scene._motion_pulses = PulseBank(decay=1.9)
        quiet_scene._trigger_summary_event_motion(event)
        quiet_pulse = quiet_scene._motion_pulses.get("panel:finance")
        for index in range(8):
            busy_scene._motion_pulses.trigger(f"busy:{index}", intensity=0.7, decay=1.8)
        busy_scene._trigger_summary_event_motion(event)
        busy_pulse = busy_scene._motion_pulses.get("panel:finance")

        assert busy_pulse < quiet_pulse
    finally:
        pygame.quit()


def test_turn_summary_scene_stabilize_motion_bank_preserves_timeline_lane() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        previous_state = create_new_game("NEXUS TECH", "Nexus One")
        resolution = resolve_turn(previous_state, RandomSource(seed=72))
        scene = TurnSummaryScene(
            pygame=pygame,
            fonts=fonts,
            state=resolution.state,
            rng=RandomSource(seed=72),
            slot_name="active",
            save_callback=lambda *_args: None,
            previous_state=previous_state,
            resolution=resolution,
            selected_product_id=resolution.state.products[0].id.hex,
            dirty=True,
        )

        scene._motion_pulses = PulseBank(decay=1.9)
        scene._motion_pulses.trigger("summary:timeline", intensity=0.75, decay=1.8)
        scene._motion_pulses.trigger("summary:metrics", intensity=0.65, decay=1.8)
        for index in range(20):
            scene._motion_pulses.trigger(f"busy:{index}", intensity=0.1, decay=1.8)

        before = scene._motion_pulses.live_count()
        scene._stabilize_motion_bank()
        after = scene._motion_pulses.live_count()

        assert after < before
        assert scene._motion_pulses.get("summary:timeline") > 0
        assert scene._motion_pulses.get("summary:metrics") > 0
    finally:
        pygame.quit()


def test_review_scene_initializes_motion_and_draws() -> None:
    pygame, fonts, surface = _build_pygame_bundle()
    try:
        state = create_new_game("NEXUS TECH", "Nexus One")
        state.company.game_over = True
        state.company.cash_on_hand = Decimal("-125.00")
        review = build_run_review_view_model(state)
        scene = ReviewScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=RandomSource(seed=53),
            slot_name="active",
            save_callback=lambda *_args: None,
            view_model=review,
            accent=DANGER,
            primary_title="Esc Close",
            primary_detail="Leave the 2D shell.",
            return_scene_factory=None,
            allow_save=False,
            dirty=False,
        )

        scene.draw(surface)

        assert scene._motion_pulses.get("review:header") > 0
        assert scene._motion_pulses.get("review:findings") > 0
        assert scene._motion_pulses.get("review:sidebar") > 0
    finally:
        pygame.quit()


def test_turn_summary_scene_handoff_restores_workspace_focus() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        previous_state = create_new_game("NEXUS TECH", "Nexus One")
        working_state = previous_state.model_copy(deep=True)
        working_state = apply_action(
            working_state,
            TurnAction.IMPROVE_QUALITY,
            context=ActionContext(target_product_id=working_state.products[0].id),
        ).state
        resolution = resolve_turn(working_state, RandomSource(seed=29))
        scene = TurnSummaryScene(
            pygame=pygame,
            fonts=fonts,
            state=resolution.state,
            rng=RandomSource(seed=29),
            slot_name="active",
            save_callback=lambda *_args: None,
            previous_state=previous_state,
            resolution=resolution,
            selected_product_id=resolution.state.products[0].id.hex,
            dirty=True,
        )

        scene._continue_to_run()
        next_scene = scene.pop_next_scene()

        assert isinstance(next_scene, RunScene)
        assert next_scene._deep_panel_key == next_scene._workspace_panel_key_for_command(
            scene._view_model.focus_command
        )
        assert next_scene.scene_transition_key == "summary_to_run"
        assert next_scene.scene_transition_active()
        assert any(event.payload.title == "Next Focus" for event in next_scene._events)
    finally:
        pygame.quit()


def test_turn_summary_scene_next_focus_event_warns_for_late_game_lane() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        previous_state = create_new_game("NEXUS TECH", "Nexus One")
        working_state = previous_state.model_copy(deep=True)
        working_state = apply_action(
            working_state,
            TurnAction.IMPROVE_QUALITY,
            context=ActionContext(target_product_id=working_state.products[0].id),
        ).state
        resolution = resolve_turn(working_state, RandomSource(seed=31))
        scene = TurnSummaryScene(
            pygame=pygame,
            fonts=fonts,
            state=resolution.state,
            rng=RandomSource(seed=31),
            slot_name="active",
            save_callback=lambda *_args: None,
            previous_state=previous_state,
            resolution=resolution,
            selected_product_id=resolution.state.products[0].id.hex,
            dirty=True,
        )

        event = scene._build_return_focus_event("finance")

        assert event is not None
        assert event.severity == "warning"
        assert event.motion == "flash"
        assert "summary:timeline" in event.targets
        assert "panel:finance" in event.targets
    finally:
        pygame.quit()


def test_turn_summary_scene_compacts_focus_command_copy() -> None:
    pygame, fonts, _surface = _build_pygame_bundle()
    try:
        previous_state = create_new_game("NEXUS TECH", "Nexus One")
        working_state = previous_state.model_copy(deep=True)
        working_state = apply_action(
            working_state,
            TurnAction.IMPROVE_QUALITY,
            context=ActionContext(target_product_id=working_state.products[0].id),
        ).state
        resolution = resolve_turn(working_state, RandomSource(seed=37))
        scene = TurnSummaryScene(
            pygame=pygame,
            fonts=fonts,
            state=resolution.state,
            rng=RandomSource(seed=37),
            slot_name="active",
            save_callback=lambda *_args: None,
            previous_state=previous_state,
            resolution=resolution,
            selected_product_id=resolution.state.products[0].id.hex,
            dirty=True,
        )

        title = scene._summary_focus_command_title()
        detail = scene._summary_focus_command_detail()

        assert title.startswith("Next ")
        assert len(detail) <= 48
    finally:
        pygame.quit()


def test_launch_2d_menu_headless_exits_after_frame_cap(tmp_path: Path) -> None:
    result = launch_2d_menu(
        db_path=tmp_path / "menu-2d.db",
        headless=True,
        max_frames=2,
        window_size=(960, 640),
        motion_mode=MotionMode.REDUCED,
    )

    assert result.exit_reason == "max_frames"
    assert result.saved_on_exit is False


def test_run_2d_motion_audit_reports_stabilized_pulse_banks() -> None:
    report = run_2d_motion_audit(
        scenario_id="founder_journey",
        difficulty_mode=None,
        seed=7,
        frames=2,
        sizes=((820, 620),),
    )

    assert report.status == "pass"
    assert report.motion_mode == MotionMode.FULL.value
    assert len(report.cells) == 1
    cell = report.cells[0]
    assert cell.run_before_pulses > cell.run_after_pulses
    assert cell.summary_before_pulses > cell.summary_after_pulses
    assert cell.run_after_pulses <= 18
    assert cell.summary_after_pulses <= 12
    assert cell.title_before_pulses >= cell.title_after_pulses
    assert cell.review_before_pulses >= cell.review_after_pulses
    assert cell.title_after_pulses <= 14
    assert cell.review_after_pulses <= 6
    assert cell.inspector_before_pulses >= cell.inspector_after_pulses
    assert cell.long_run_before_pulses > cell.long_run_after_pulses
    assert cell.inspector_after_pulses <= 12
    assert cell.long_run_after_pulses <= 18
    assert cell.transition_active_scenes == 4
    assert cell.transition_disabled_scenes == 0
    assert cell.entity_motion_active_samples == 3
    assert cell.entity_motion_disabled_samples == 0
    assert cell.action_feedback_active_samples == 1
    assert cell.action_feedback_disabled_samples == 0
    assert cell.impact_cue_active_samples == 1
    assert cell.impact_cue_disabled_samples == 0
    assert cell.overlay_transition_active_samples == 1
    assert cell.overlay_transition_disabled_samples == 0
    assert cell.outcome_cinematic_active_samples == 1
    assert cell.outcome_cinematic_disabled_samples == 0
    assert cell.summary_cinematic_active_samples == 1
    assert cell.summary_cinematic_disabled_samples == 0
    assert cell.product_drama_active_samples == 1
    assert cell.product_drama_disabled_samples == 0
    assert cell.risk_drama_active_samples == 1
    assert cell.risk_drama_disabled_samples == 0
    assert cell.pending_choice_active_samples == 1
    assert cell.pending_choice_disabled_samples == 0
    assert cell.pending_choice_preview_active_samples == 1
    assert cell.pending_choice_preview_disabled_samples == 0
    assert cell.late_game_choreography_active_samples == 1
    assert cell.late_game_choreography_disabled_samples == 0
    assert cell.summary_sequence_active_samples == 1
    assert cell.summary_sequence_disabled_samples == 0
    assert cell.summary_lanes_active_samples == 1
    assert cell.summary_lanes_disabled_samples == 0
    assert cell.actor_timeline_active_samples == 6
    assert cell.actor_timeline_disabled_samples == 0
    assert cell.sprite_clips_active_samples == 6
    assert cell.sprite_clips_disabled_samples == 0
    assert cell.max_frame_ms >= cell.average_frame_ms
    assert report.flow_report.status == "pass"


def test_run_2d_motion_audit_can_disable_highlight_pulses() -> None:
    report = run_2d_motion_audit(
        scenario_id="founder_journey",
        difficulty_mode=None,
        seed=7,
        frames=1,
        sizes=((820, 620),),
        motion_mode=MotionMode.OFF,
    )

    cell = report.cells[0]
    assert report.status == "pass"
    assert report.motion_mode == MotionMode.OFF.value
    assert cell.run_before_pulses == 0
    assert cell.run_after_pulses == 0
    assert cell.summary_before_pulses == 0
    assert cell.summary_after_pulses == 0
    assert cell.title_before_pulses == 0
    assert cell.title_after_pulses == 0
    assert cell.review_before_pulses == 0
    assert cell.review_after_pulses == 0
    assert cell.inspector_before_pulses == 0
    assert cell.inspector_after_pulses == 0
    assert cell.long_run_before_pulses == 0
    assert cell.long_run_after_pulses == 0
    assert cell.transition_active_scenes == 0
    assert cell.transition_disabled_scenes == 4
    assert cell.entity_motion_active_samples == 0
    assert cell.entity_motion_disabled_samples == 3
    assert cell.action_feedback_active_samples == 0
    assert cell.action_feedback_disabled_samples == 1
    assert cell.impact_cue_active_samples == 0
    assert cell.impact_cue_disabled_samples == 1
    assert cell.overlay_transition_active_samples == 0
    assert cell.overlay_transition_disabled_samples == 1
    assert cell.outcome_cinematic_active_samples == 0
    assert cell.outcome_cinematic_disabled_samples == 1
    assert cell.summary_cinematic_active_samples == 0
    assert cell.summary_cinematic_disabled_samples == 1
    assert cell.product_drama_active_samples == 0
    assert cell.product_drama_disabled_samples == 1
    assert cell.risk_drama_active_samples == 0
    assert cell.risk_drama_disabled_samples == 1
    assert cell.pending_choice_active_samples == 0
    assert cell.pending_choice_disabled_samples == 1
    assert cell.pending_choice_preview_active_samples == 0
    assert cell.pending_choice_preview_disabled_samples == 1
    assert cell.late_game_choreography_active_samples == 0
    assert cell.late_game_choreography_disabled_samples == 1
    assert cell.summary_sequence_active_samples == 0
    assert cell.summary_sequence_disabled_samples == 1
    assert cell.summary_lanes_active_samples == 0
    assert cell.summary_lanes_disabled_samples == 1
    assert cell.actor_timeline_active_samples == 0
    assert cell.actor_timeline_disabled_samples == 6
    assert cell.sprite_clips_active_samples == 0
    assert cell.sprite_clips_disabled_samples == 6


def test_run_2d_flow_audit_reports_no_missing_request_paths() -> None:
    report = run_2d_flow_audit(seed=7)

    assert report.status == "pass"
    assert report.command_count >= 40
    assert report.inspector_action_count > 0
    assert report.findings == ()


def test_run_2d_visual_audit_captures_core_scene_layers(tmp_path: Path) -> None:
    report = run_2d_visual_audit(
        scenario_id="founder_journey",
        difficulty_mode=None,
        seed=7,
        sizes=((820, 620),),
        output_dir=tmp_path,
    )

    assert report.status == "pass"
    assert report.motion_mode == MotionMode.FULL.value
    assert report.output_dir == str(tmp_path)
    scene_keys = {cell.scene_key for cell in report.cells}
    assert {
        "title_menu",
        "title_meta",
        "run_dashboard",
        "run_drama_feedback",
        "run_pending_feedback",
        "run_impact_feedback",
        "run_blocked_feedback",
        "run_picker_feedback",
        "run_inspector",
        "run_endgame_board",
        "run_outcome_overlay",
        "turn_summary",
        "review",
    } <= scene_keys
    assert all(cell.checksum > 0 for cell in report.cells)
    assert report.baseline_signature.startswith(f"{len(report.cells)}:")
    assert all(cell.unique_color_samples >= 18 for cell in report.cells)
    assert all(0.0 <= cell.edge_density <= MAX_EDGE_DENSITY for cell in report.cells)
    assert all(0.0 <= cell.bright_ratio <= MAX_BRIGHT_RATIO for cell in report.cells)
    assert all(cell.layout_violations == () for cell in report.cells)
    assert all(cell.click_target_count > 0 for cell in report.cells)
    assert all(cell.min_click_target_size[0] >= 28 for cell in report.cells)
    assert all(cell.min_click_target_size[1] >= 24 for cell in report.cells)
    assert all(cell.typography_violations == () for cell in report.cells)
    assert all(0.0 <= cell.min_text_fit_ratio <= 1.0 for cell in report.cells)
    assert all(Path(cell.output_path or "").exists() for cell in report.cells)
    summary_path = tmp_path / VISUAL_AUDIT_SUMMARY_NAME
    assert summary_path.exists()
    summary = summary_path.read_text(encoding="utf-8")
    assert "NEXUS TECH 2D Visual Audit" in summary
    assert report.baseline_signature in summary
    assert "`run_dashboard`" in summary
    title_menu = next(cell for cell in report.cells if cell.scene_key == "title_menu")
    title_meta = next(cell for cell in report.cells if cell.scene_key == "title_meta")
    impact = next(cell for cell in report.cells if cell.scene_key == "run_impact_feedback")
    blocked = next(cell for cell in report.cells if cell.scene_key == "run_blocked_feedback")
    dashboard = next(cell for cell in report.cells if cell.scene_key == "run_dashboard")
    drama = next(cell for cell in report.cells if cell.scene_key == "run_drama_feedback")
    pending = next(cell for cell in report.cells if cell.scene_key == "run_pending_feedback")
    picker = next(cell for cell in report.cells if cell.scene_key == "run_picker_feedback")
    inspector = next(cell for cell in report.cells if cell.scene_key == "run_inspector")
    endgame = next(cell for cell in report.cells if cell.scene_key == "run_endgame_board")
    outcome = next(cell for cell in report.cells if cell.scene_key == "run_outcome_overlay")
    summary = next(cell for cell in report.cells if cell.scene_key == "turn_summary")
    review = next(cell for cell in report.cells if cell.scene_key == "review")
    assert "title-actor" in title_menu.active_layers
    assert "transition-key:boot_title" in title_menu.active_layers
    assert "click-targets" in title_menu.active_layers
    assert "title-nav-controls" in title_menu.active_layers
    assert "actor-timeline" in title_menu.active_layers
    assert "sprite-clips" in title_menu.active_layers
    assert "actor-readability" in title_menu.active_layers
    assert "actor-pose-depth" in title_menu.active_layers
    assert any(layer.startswith("actor-state:") for layer in title_menu.active_layers)
    assert any(layer.startswith("actor-pose:") for layer in title_menu.active_layers)
    assert "archive-comparison" in title_meta.active_layers
    assert "actor-timeline" in dashboard.active_layers
    assert "transition-key:boot_run" in dashboard.active_layers
    assert "sprite-clips" in dashboard.active_layers
    assert "actor-readability" in dashboard.active_layers
    assert "actor-pose-depth" in dashboard.active_layers
    assert "actor-state:handoff" in dashboard.active_layers
    assert "actor-pose:handoff" in dashboard.active_layers
    assert "click-targets" in dashboard.active_layers
    assert "pause-control" in dashboard.active_layers
    assert "back-control" in dashboard.active_layers
    assert "help-control" in dashboard.active_layers
    assert "run-nav-controls" in dashboard.active_layers
    assert "product-drama" in drama.active_layers
    assert "risk-drama" in drama.active_layers
    assert "pending" in pending.active_layers
    assert "pending-choice-preview" in pending.active_layers
    assert "impact-cue" in impact.active_layers
    assert "action-feedback" in impact.active_layers
    assert "impact-cue-targets" in impact.active_layers
    assert "impact-value-label" in impact.active_layers
    assert "action-feedback-targets" in impact.active_layers
    assert "action-family:product" in impact.active_layers
    assert "action-feedback" in blocked.active_layers
    assert "action-feedback-targets" in blocked.active_layers
    assert "blocked-action-feedback" in blocked.active_layers
    assert "blocked-action-reason" in blocked.active_layers
    assert "actor-state:blocked" in blocked.active_layers
    assert "picker" in picker.active_layers
    assert "overlay-transition" in picker.active_layers
    assert "action-feedback" in picker.active_layers
    assert "late-game-choreography" in picker.active_layers
    assert "inspector" in inspector.active_layers
    assert "overlay-transition" in inspector.active_layers
    assert "inspector-actor" in inspector.active_layers
    assert "actor-timeline" in inspector.active_layers
    assert "sprite-clips" in inspector.active_layers
    assert "actor-readability" in inspector.active_layers
    assert "actor-pose-depth" in inspector.active_layers
    assert "endgame-actor" in endgame.active_layers
    assert "deep-panel" in endgame.active_layers
    assert "actor-timeline" in endgame.active_layers
    assert "sprite-clips" in endgame.active_layers
    assert "actor-readability" in endgame.active_layers
    assert "actor-pose-depth" in endgame.active_layers
    assert "outcome" in outcome.active_layers
    assert "outcome-cinematic" in outcome.active_layers
    assert "transition-key:run_to_review" in outcome.active_layers
    assert "save-control" in outcome.active_layers
    assert "flow-control" in outcome.active_layers
    assert "outcome-nav-controls" in outcome.active_layers
    assert "summary-reveal" in summary.active_layers
    assert "summary-cinematic" in summary.active_layers
    assert "summary-sequence" in summary.active_layers
    assert "summary-lanes" in summary.active_layers
    assert "transition-key:run_to_summary" in summary.active_layers
    assert "actor-timeline" in summary.active_layers
    assert "sprite-clips" in summary.active_layers
    assert "actor-readability" in summary.active_layers
    assert "actor-pose-depth" in summary.active_layers
    assert "save-control" in summary.active_layers
    assert "flow-control" in summary.active_layers
    assert "summary-nav-controls" in summary.active_layers
    assert "review-actor" in review.active_layers
    assert "actor-timeline" in review.active_layers
    assert "sprite-clips" in review.active_layers
    assert "actor-readability" in review.active_layers
    assert "actor-pose-depth" in review.active_layers
    assert "back-control" in review.active_layers
    assert "review-nav-controls" in review.active_layers


def test_run_2d_visual_audit_motion_off_drops_archive_comparison_layer() -> None:
    report = run_2d_visual_audit(
        scenario_id="founder_journey",
        difficulty_mode=None,
        seed=7,
        sizes=((820, 620),),
        motion_mode=MotionMode.OFF,
    )

    title_meta = next(cell for cell in report.cells if cell.scene_key == "title_meta")

    assert report.status == "pass"
    assert report.motion_mode == MotionMode.OFF.value
    assert "archive-comparison" not in title_meta.expected_layers
    assert "archive-comparison" not in title_meta.active_layers


def test_actor_sprite_pose_key_defaults_to_state_depth() -> None:
    blocked = scenes_module.ActorSpriteClip(
        key="blocked",
        label="Blocked Ops",
        role="Ops",
        state="blocked",
        accent=DANGER,
        lane="risk",
    )
    custom = scenes_module.ActorSpriteClip(
        key="custom",
        label="Coach",
        role="Advisor",
        state="idle",
        accent=DANGER,
        lane="team",
        pose="coach",
    )

    assert blocked.pose_key == "block"
    assert custom.pose_key == "coach"


def test_visual_audit_cell_fails_visual_fatigue_thresholds() -> None:
    cluttered = VisualAuditCell(
        scene_key="run_dashboard",
        width=820,
        height=620,
        checksum=12345,
        unique_color_samples=42,
        luminance_spread=128,
        non_dark_ratio=0.42,
        active_layers=("transition",),
        expected_layers=("transition",),
        edge_density=MAX_EDGE_DENSITY + 0.01,
        bright_ratio=MAX_BRIGHT_RATIO + 0.01,
    )

    assert cluttered.status == "fail"
    assert "visual clutter" in cluttered.notes
    assert "high flash pressure" in cluttered.notes


def test_visual_audit_cell_fails_layout_safety_violations() -> None:
    unsafe = VisualAuditCell(
        scene_key="run_dashboard",
        width=820,
        height=620,
        checksum=12345,
        unique_color_samples=42,
        luminance_spread=128,
        non_dark_ratio=0.42,
        active_layers=("click-targets",),
        expected_layers=("click-targets",),
        layout_violations=("target-too-small:pause_toggle:20x18",),
        click_target_count=1,
        min_click_target_size=(20, 18),
    )

    assert unsafe.status == "fail"
    assert "layout target-too-small:pause_toggle:20x18" in unsafe.notes


def test_visual_audit_cell_fails_typography_safety_violations() -> None:
    unsafe = VisualAuditCell(
        scene_key="title_menu",
        width=820,
        height=620,
        checksum=12345,
        unique_color_samples=42,
        luminance_spread=128,
        non_dark_ratio=0.42,
        active_layers=("click-targets",),
        expected_layers=("click-targets",),
        typography_violations=("button-title-fit:0.20",),
        text_fit_count=1,
        min_text_fit_ratio=0.2,
    )

    assert unsafe.status == "fail"
    assert "typography button-title-fit:0.20" in unsafe.notes


def test_run_2d_animation_audit_reports_required_and_advisory_layers() -> None:
    report = run_2d_animation_audit(
        scenario_id="founder_journey",
        difficulty_mode=None,
        seed=7,
        frames=1,
        sizes=((820, 620),),
    )

    assert report.status == "pass"
    assert report.visual_report.baseline_signature.startswith("13:")
    areas = {cell.area: cell for cell in report.cells}
    assert areas["Title/Menu Actors"].status == "pass"
    assert "title-actor" in areas["Title/Menu Actors"].active_layers
    assert areas["Archive/Meta Comparison Motion"].status == "pass"
    assert "archive-comparison" in areas["Archive/Meta Comparison Motion"].active_layers
    assert areas["Long Session Motion Stress"].status == "pass"
    assert "long-run-pulse-recovery" in areas["Long Session Motion Stress"].required_layers
    assert areas["Pending Event Preview"].status == "pass"
    assert "pending-choice-preview" in areas["Pending Event Preview"].active_layers
    assert areas["Blocked Action Feedback"].status == "pass"
    assert "blocked-action-feedback" in areas["Blocked Action Feedback"].active_layers
    assert areas["Late-Game Command Choreography"].status == "pass"
    assert "late-game-choreography" in areas["Late-Game Command Choreography"].active_layers
    assert areas["Outcome Cinematic"].status == "pass"
    assert "outcome-cinematic" in areas["Outcome Cinematic"].active_layers
    assert areas["Inspector Actors"].status == "pass"
    assert "inspector-actor" in areas["Inspector Actors"].active_layers
    assert areas["Endgame Board Actors"].status == "pass"
    assert "endgame-actor" in areas["Endgame Board Actors"].active_layers
    assert areas["Review Actors"].status == "pass"
    assert "review-actor" in areas["Review Actors"].active_layers
    assert areas["Sprite/Actor Layer"].status == "pass"
    assert "actor-timeline" in areas["Sprite/Actor Layer"].active_layers
    assert "sprite-clips" in areas["Sprite/Actor Layer"].active_layers
    assert "actor-readability" in areas["Sprite/Actor Layer"].active_layers
    assert "actor-pose-depth" in areas["Sprite/Actor Layer"].active_layers
    assert "actor-pose-depth" in areas["Sprite/Actor Layer"].required_layers
    assert areas["Actor State Coverage"].status == "pass"
    assert "actor-state:blocked" in areas["Actor State Coverage"].required_layers
    assert "state-group:baseline" in areas["Actor State Coverage"].active_layers
    assert "state-group:positive" in areas["Actor State Coverage"].active_layers
    assert "state-group:pressure" in areas["Actor State Coverage"].active_layers
    assert areas["Action Feedback Clarity"].status == "pass"
    assert "action-feedback-targets" in areas["Action Feedback Clarity"].active_layers
    assert "blocked-action-reason" in areas["Action Feedback Clarity"].active_layers
    assert "impact-value-label" in areas["Action Feedback Clarity"].active_layers
    assert "impact-cue-targets" in areas["Action Feedback Clarity"].required_layers
    assert areas["Visual Fatigue Budget"].status == "pass"
    assert "visual-health" in areas["Visual Fatigue Budget"].active_layers
    assert areas["Animation Pacing Budget"].status == "pass"
    assert "sample-density" in areas["Animation Pacing Budget"].required_layers
    assert any(
        layer.startswith("active-samples:")
        for layer in areas["Animation Pacing Budget"].active_layers
    )
    assert areas["Scene Motion Profile"].status == "pass"
    assert "scene-profile-map" in areas["Scene Motion Profile"].required_layers
    assert "unprofiled:0" in areas["Scene Motion Profile"].active_layers
    assert areas["Readability Guard"].status == "pass"
    assert "compact-viewport" in areas["Readability Guard"].required_layers
    assert any(
        layer.startswith("compact-captures:") for layer in areas["Readability Guard"].active_layers
    )
    assert areas["Long Session Visual Readiness"].status == "pass"
    assert "late-session-scenes" in areas["Long Session Visual Readiness"].required_layers
    assert any(
        layer.startswith("scenes:")
        for layer in areas["Long Session Visual Readiness"].active_layers
    )
    assert areas["Motion Mode Differentiation"].status == "pass"
    assert "mode-distinction" in areas["Motion Mode Differentiation"].required_layers
    assert any(
        layer.startswith("reduced-active:")
        for layer in areas["Motion Mode Differentiation"].active_layers
    )
    assert areas["Scene Transition Handoff"].status == "pass"
    assert "transition-key:boot_title" in areas["Scene Transition Handoff"].active_layers
    assert "transition-key:boot_run" in areas["Scene Transition Handoff"].active_layers
    assert "transition-key:run_to_summary" in areas["Scene Transition Handoff"].active_layers
    assert "transition-key:run_to_review" in areas["Scene Transition Handoff"].active_layers
    assert "transition-off-gate" in areas["Scene Transition Handoff"].active_layers
    assert areas["Control Affordance Coverage"].status == "pass"
    assert "pause-control" in areas["Control Affordance Coverage"].active_layers
    assert "run-nav-controls" in areas["Control Affordance Coverage"].required_layers
    assert "summary-nav-controls" in areas["Control Affordance Coverage"].active_layers
    assert areas["Control Replay Safety"].status == "pass"
    assert "pause-key-open" in areas["Control Replay Safety"].active_layers
    assert "pause-resume-click" in areas["Control Replay Safety"].active_layers
    assert "back-opens-pause" in areas["Control Replay Safety"].active_layers
    assert "hover-hints" in areas["Control Replay Safety"].active_layers
    assert "pause-menu-return" in areas["Control Replay Safety"].active_layers
    assert areas["UI Layout Safety"].status == "pass"
    assert "layout-pass" in areas["UI Layout Safety"].active_layers
    assert "target-size" in areas["UI Layout Safety"].required_layers
    assert "actor-control-clearance" in areas["UI Layout Safety"].active_layers
    assert areas["Typography Safety"].status == "pass"
    assert "text-overflow-clear" in areas["Typography Safety"].active_layers
    assert "button-title-fit" in areas["Typography Safety"].required_layers
    assert any(
        layer.startswith("min-fit-ratio:") for layer in areas["Typography Safety"].active_layers
    )
    assert areas["Motion Off Gate"].status == "pass"
    assert areas["Manual Playtest"].status == "advisory"
    assert not any("Sprite/actor animation" in gap for gap in report.advisory_gaps)


def test_motion_mode_differentiation_records_reduced_residual_without_failing() -> None:
    def _report(*, residual: int, active: int, mode: MotionMode) -> MotionAuditReport:
        return MotionAuditReport(
            scenario_id="founder_journey",
            difficulty="scenario",
            seed=7,
            frames=1,
            motion_mode=mode.value,
            flow_report=FlowAuditReport(command_count=1, inspector_action_count=1, findings=()),
            cells=(
                MotionAuditCell(
                    width=820,
                    height=620,
                    run_before_pulses=residual + 4,
                    run_after_pulses=residual,
                    summary_before_pulses=0,
                    summary_after_pulses=0,
                    title_before_pulses=0,
                    title_after_pulses=0,
                    review_before_pulses=0,
                    review_after_pulses=0,
                    inspector_before_pulses=0,
                    inspector_after_pulses=0,
                    long_run_before_pulses=0,
                    long_run_after_pulses=0,
                    average_frame_ms=1.0,
                    max_frame_ms=2.0,
                    action_feedback_active_samples=active,
                    actor_timeline_active_samples=active,
                    sprite_clips_active_samples=active,
                ),
            ),
        )

    full_report = _report(residual=10, active=4, mode=MotionMode.FULL)
    reduced_with_jitter = _report(residual=12, active=3, mode=MotionMode.REDUCED)
    reduced_with_more_residual = _report(residual=13, active=3, mode=MotionMode.REDUCED)
    reduced_with_active_jitter = _report(residual=12, active=5, mode=MotionMode.REDUCED)
    reduced_with_active_regression = _report(residual=12, active=6, mode=MotionMode.REDUCED)
    off_report = _report(residual=0, active=0, mode=MotionMode.OFF)
    off_report_with_residual = _report(residual=1, active=0, mode=MotionMode.OFF)

    small_jitter = animation_audit_module._build_motion_mode_differentiation_cell(
        full_report,
        reduced_with_jitter,
        off_report,
    )
    larger_reduced_residual = animation_audit_module._build_motion_mode_differentiation_cell(
        full_report,
        reduced_with_more_residual,
        off_report,
    )
    active_jitter = animation_audit_module._build_motion_mode_differentiation_cell(
        full_report,
        reduced_with_active_jitter,
        off_report,
    )
    active_regression = animation_audit_module._build_motion_mode_differentiation_cell(
        full_report,
        reduced_with_active_regression,
        off_report,
    )
    off_regression = animation_audit_module._build_motion_mode_differentiation_cell(
        full_report,
        reduced_with_jitter,
        off_report_with_residual,
    )

    assert small_jitter.status == "pass"
    assert "reduced-residual-delta:2" in small_jitter.active_layers
    assert larger_reduced_residual.status == "pass"
    assert "reduced-residual-delta:3" in larger_reduced_residual.active_layers
    assert active_jitter.status == "pass"
    assert "reduced-active-overrun:3" in active_jitter.active_layers
    assert active_regression.status == "fail"
    assert "reduced active 18>12" in active_regression.notes
    assert off_regression.status == "fail"
    assert "off still active 0/1" in off_regression.notes


def test_run_2d_animation_matrix_audit_records_scenario_seed_cells(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, int]] = []

    def fake_run_2d_animation_audit(**kwargs):
        calls.append((kwargs["scenario_id"], kwargs["seed"]))
        visual_report = VisualAuditReport(
            scenario_id=kwargs["scenario_id"],
            difficulty="scenario",
            seed=kwargs["seed"],
            motion_mode=MotionMode.FULL.value,
            cells=(
                VisualAuditCell(
                    scene_key="run_dashboard",
                    width=820,
                    height=620,
                    checksum=kwargs["seed"],
                    unique_color_samples=42,
                    luminance_spread=128,
                    non_dark_ratio=0.42,
                    active_layers=("actor-state:handoff",),
                    expected_layers=(),
                ),
            ),
        )
        motion_report = MotionAuditReport(
            scenario_id=kwargs["scenario_id"],
            difficulty="scenario",
            seed=kwargs["seed"],
            frames=kwargs["frames"],
            cells=(),
        )
        return AnimationAuditReport(
            scenario_id=kwargs["scenario_id"],
            difficulty="scenario",
            seed=kwargs["seed"],
            cells=(
                AnimationCoverageCell(
                    area="Actor State Coverage",
                    required_layers=("actor-state:blocked",),
                    active_layers=("actor-state:handoff",),
                    status="pass",
                    notes="mocked",
                ),
            ),
            visual_report=visual_report,
            motion_report=motion_report,
            off_motion_report=motion_report,
            advisory_gaps=("Manual open-window playtest is still required.",),
        )

    monkeypatch.setattr(
        animation_audit_module,
        "run_2d_animation_audit",
        fake_run_2d_animation_audit,
    )

    report = run_2d_animation_matrix_audit(
        scenario_ids=("founder_journey", "bootstrap_studio"),
        difficulty_mode=None,
        seeds=(7, 13),
        frames=1,
    )

    assert report.status == "pass"
    assert report.scenario_ids == ("founder_journey", "bootstrap_studio")
    assert report.seeds == (7, 13)
    assert len(report.cells) == 4
    assert calls == [
        ("founder_journey", 7),
        ("founder_journey", 13),
        ("bootstrap_studio", 7),
        ("bootstrap_studio", 13),
    ]
    assert all(cell.visual_baseline.startswith("1:") for cell in report.cells)
    report_path = tmp_path / ANIMATION_MATRIX_REPORT_NAME
    write_2d_animation_matrix_report(report, report_path)
    report_text = report_path.read_text(encoding="utf-8")
    assert "NEXUS TECH 2D Animation Matrix" in report_text
    assert "`founder_journey`" in report_text
    assert "`bootstrap_studio`" in report_text
    assert "- Cells: `4` total, `4` pass, `0` fail" in report_text


def test_write_2d_animation_playtest_prep_report_keeps_manual_scope(tmp_path: Path) -> None:
    matrix_report = AnimationMatrixReport(
        scenario_ids=("founder_journey", "bootstrap_studio"),
        difficulty="scenario",
        seeds=(7, 13),
        frames=1,
        cells=(
            AnimationMatrixCell(
                scenario_id="founder_journey",
                difficulty="scenario",
                seed=7,
                status="pass",
                visual_baseline="13:abc12345",
                failed_areas=(),
                advisory_gaps=("Manual open-window playtest is still required.",),
            ),
            AnimationMatrixCell(
                scenario_id="bootstrap_studio",
                difficulty="scenario",
                seed=13,
                status="pass",
                visual_baseline="13:def67890",
                failed_areas=(),
                advisory_gaps=("Manual open-window playtest is still required.",),
            ),
        ),
    )
    report = build_2d_animation_playtest_prep_report(
        version="0.142.0",
        matrix_report=matrix_report,
    )
    output_path = tmp_path / ANIMATION_PLAYTEST_PREP_REPORT_NAME

    write_2d_animation_playtest_prep_report(report, output_path)

    report_text = output_path.read_text(encoding="utf-8")
    assert "- Status: `ready`" in report_text
    assert "- Version: `0.142.0`" in report_text
    assert "- Manual result: `not completed by automation`" in report_text
    assert "`820x620`" in report_text
    assert "`960x640`" in report_text
    assert "`1440x900`" in report_text
    assert "menu-2d --window-size 820x620 --motion-mode full" in report_text
    assert (
        "play-2d --scenario founder_journey --seed 7 --window-size 960x640 --motion-mode reduced"
    ) in report_text
    assert "menu-2d --window-size 1440x900 --motion-mode off" in report_text
    assert "## Control Clarity Checklist" in report_text
    assert "Pause / Resume" in report_text
    assert "Back / Escape" in report_text
    assert "Control Replay Safety" in report_text
    assert "## Game Feel Checklist" in report_text
    assert "Success Feedback" in report_text
    assert "Blocked Feedback" in report_text
    assert "Impact Values" in report_text
    assert "## Balance And Long-Session Preflight" in report_text
    assert "balance-audit --scenario founder_journey --scenario debt_crunch" in report_text
    assert "simulate-balance --scenario founder_journey --difficulty founder" in report_text
    assert "balance-report --output /tmp/nexus-tech-balance-report.md" in report_text
    assert "## Manual Completion Gate" in report_text
    assert "Every game-feel row must be `pass`" in report_text
    assert "## Required Report Sections" in report_text
    assert "Window Matrix | 820x620, 960x640, 1440x900 across Full, Reduced, and Off" in report_text
    assert "Game Feel Results | Success Feedback, Blocked Feedback, Impact Values" in report_text
    assert "manual signoff required before calling animation complete" in report_text
    assert "nexus-tech-2d-visual-audit" in report_text
    assert "nexus-tech-2d-animation-matrix" in report_text
    assert "nexus-tech-2d-animation-playtest-prep" in report_text
    assert "`founder_journey` | `7` | `pass` | `13:abc12345`" in report_text


def test_build_2d_animation_playtest_command_queue_covers_manual_matrix() -> None:
    queue = build_2d_animation_playtest_command_queue(
        scenario_id="debt_crunch",
        seed=99,
    )

    assert len(queue) == 18
    assert queue[0].target == "menu"
    assert queue[0].window_size == "820x620"
    assert queue[0].motion_mode == "full"
    assert queue[0].command == (
        "uv run nexus-tech menu-2d --window-size 820x620 --motion-mode full"
    )
    assert queue[1].target == "play"
    assert "--scenario debt_crunch" in queue[1].command
    assert "--seed 99" in queue[1].command
    assert queue[-1].window_size == "1440x900"
    assert queue[-1].motion_mode == "off"
    assert sum(1 for item in queue if item.target == "menu") == 9
    assert sum(1 for item in queue if item.target == "play") == 9


def test_write_2d_animation_playtest_command_queue_keeps_manual_scope(tmp_path: Path) -> None:
    queue = build_2d_animation_playtest_command_queue()
    output_path = tmp_path / "manual-animation-commands.md"

    write_2d_animation_playtest_command_queue(queue, output_path)

    report_text = output_path.read_text(encoding="utf-8")
    assert "NEXUS TECH 2D Manual Animation Playtest Commands" in report_text
    assert "- Manual result: `not completed by automation`" in report_text
    assert "menu-2d --window-size 820x620 --motion-mode full" in report_text
    assert "play-2d --scenario founder_journey --seed 7" in report_text
    assert "play-2d --scenario founder_journey --seed 7 --window-size 1440x900" in (report_text)


def test_validate_2d_animation_playtest_command_queue_accepts_complete_queue(
    tmp_path: Path,
) -> None:
    queue = build_2d_animation_playtest_command_queue(scenario_id="debt_crunch", seed=99)
    output_path = tmp_path / "manual-animation-commands.md"
    write_2d_animation_playtest_command_queue(queue, output_path)

    validation = validate_2d_animation_playtest_command_queue(
        output_path,
        scenario_id="debt_crunch",
        seed=99,
    )

    assert validation.status == "pass"
    assert validation.expected_count == 18
    assert validation.findings == ()


def test_validate_2d_animation_playtest_command_queue_rejects_missing_command(
    tmp_path: Path,
) -> None:
    queue = build_2d_animation_playtest_command_queue()
    output_path = tmp_path / "manual-animation-commands.md"
    write_2d_animation_playtest_command_queue(queue[:-1], output_path)

    validation = validate_2d_animation_playtest_command_queue(output_path)

    assert validation.status == "fail"
    assert "expected 18 command rows, found 17" in validation.findings
    assert any("missing command:" in finding for finding in validation.findings)


def test_write_2d_animation_playtest_report_template_matches_validator_contract(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / ANIMATION_PLAYTEST_REPORT_NAME

    write_2d_animation_playtest_report_template(
        output_path,
        version="0.162.0",
        commit="abc1234",
        tester="araxis07",
        platform="macOS local",
        date="2026-06-19",
    )

    report_text = output_path.read_text(encoding="utf-8")
    assert "- Version: 0.162.0" in report_text
    assert "- Commit: abc1234" in report_text
    assert "| audit-2d-animation-matrix --output | `todo`" in report_text
    assert "| `820x620` | `todo` | `todo` | `todo`" in report_text
    assert "| UI Layout Safety | `todo`" in report_text
    assert "| Scene Handoffs | `todo`" in report_text
    assert "| Actor + Feedback Match | `todo`" in report_text
    assert "- visual-audit-summary.md anomalies: todo" in report_text

    validation = validate_2d_animation_playtest_report(output_path)

    assert validation.status == "fail"
    assert "report still contains todo cells" in validation.findings
    assert "incomplete automated gate result: audit-2d-animation-matrix --output" in (
        validation.findings
    )
    assert "incomplete window matrix result: 820x620 Full" in validation.findings


def test_write_2d_animation_playtest_report_template_can_prefill_automated_gates(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / ANIMATION_PLAYTEST_REPORT_NAME

    write_2d_animation_playtest_report_template(
        output_path,
        version="0.163.0",
        commit="abc1234",
        tester="araxis07",
        platform="macOS local",
        date="2026-06-19",
        prefill_automated_gates=True,
    )

    report_text = output_path.read_text(encoding="utf-8")
    assert "| audit-2d-animation-matrix --output | `pass`" in report_text
    assert "| prepare-2d-animation-playtest --output | `pass`" in report_text
    assert "| `820x620` | `todo` | `todo` | `todo`" in report_text

    validation = validate_2d_animation_playtest_report(output_path)

    assert validation.status == "fail"
    assert "incomplete automated gate result: audit-2d-animation-matrix --output" not in (
        validation.findings
    )
    assert "incomplete window matrix result: 820x620 Full" in validation.findings


def test_summarize_2d_animation_playtest_report_groups_manual_gaps(tmp_path: Path) -> None:
    output_path = tmp_path / ANIMATION_PLAYTEST_REPORT_NAME
    write_2d_animation_playtest_report_template(
        output_path,
        version="0.164.0",
        commit="abc1234",
        tester="araxis07",
        platform="macOS local",
        date="2026-06-19",
        prefill_automated_gates=True,
    )

    validation = validate_2d_animation_playtest_report(output_path)
    summary = summarize_2d_animation_playtest_report(validation)
    areas = {area.area: area for area in summary}

    assert "Automated Gates" not in areas
    assert areas["Manual Window Matrix"].incomplete_count == 9
    assert areas["Manual Route Evidence"].incomplete_count == 18
    assert areas["Manual Control Checks"].incomplete_count == 9
    assert areas["Manual Scene Checks"].incomplete_count == 9
    assert areas["Manual Game Feel"].incomplete_count == 4
    assert areas["Signoff Fields"].incomplete_count >= 1
    assert areas["Template Cleanup"].incomplete_count == 1


def test_build_2d_animation_playtest_readiness_plan_blocks_missing_queue(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / ANIMATION_PLAYTEST_REPORT_NAME
    commands_path = tmp_path / "manual-animation-commands.md"
    write_2d_animation_playtest_report_template(
        report_path,
        version="0.169.0",
        commit="abc1234",
        tester="araxis07",
        platform="macOS local",
        date="2026-06-20",
        prefill_automated_gates=True,
    )
    queue = build_2d_animation_playtest_command_queue()
    write_2d_animation_playtest_command_queue(queue[:-1], commands_path)

    plan = build_2d_animation_playtest_readiness_plan(report_path, commands_path)

    assert isinstance(plan, AnimationPlaytestReadinessPlan)
    assert plan.status == "blocked"
    assert plan.commands.status == "fail"
    assert plan.report.status == "fail"
    assert any(step.area == "Command Queue" for step in plan.steps)
    assert plan.open_item_count > len(plan.report.findings)


def test_build_2d_animation_playtest_readiness_plan_tracks_manual_gaps(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / ANIMATION_PLAYTEST_REPORT_NAME
    commands_path = tmp_path / "manual-animation-commands.md"
    write_2d_animation_playtest_report_template(
        report_path,
        version="0.169.0",
        commit="abc1234",
        tester="araxis07",
        platform="macOS local",
        date="2026-06-20",
        prefill_automated_gates=True,
    )
    queue = build_2d_animation_playtest_command_queue(seed=13)
    write_2d_animation_playtest_command_queue(queue, commands_path)

    plan = build_2d_animation_playtest_readiness_plan(report_path, commands_path, seed=13)
    areas = {step.area: step for step in plan.steps}

    assert plan.status == "manual-required"
    assert plan.commands.status == "pass"
    assert areas["Manual Window Matrix"].open_items == 9
    assert areas["Manual Control Checks"].status == "manual-required"
    assert "Command Queue" not in areas


def test_write_2d_animation_playtest_readiness_plan_exports_handoff_artifact(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / ANIMATION_PLAYTEST_REPORT_NAME
    commands_path = tmp_path / "manual-animation-commands.md"
    output_path = tmp_path / "manual-animation-plan.md"
    write_2d_animation_playtest_report_template(
        report_path,
        version="0.170.0",
        commit="abc1234",
        tester="araxis07",
        platform="macOS local",
        date="2026-06-20",
        prefill_automated_gates=True,
    )
    write_2d_animation_playtest_command_queue(
        build_2d_animation_playtest_command_queue(seed=23),
        commands_path,
    )
    plan = build_2d_animation_playtest_readiness_plan(report_path, commands_path, seed=23)

    write_2d_animation_playtest_readiness_plan(plan, output_path)

    plan_text = output_path.read_text(encoding="utf-8")
    assert "# NEXUS TECH 2D Animation Playtest Plan" in plan_text
    assert "- Status: `manual-required`" in plan_text
    assert "- Release decision: `-`" in plan_text
    assert "- Manual result: `not completed by automation`" in plan_text
    assert "| Manual Window Matrix | `manual-required` | `9` |" in plan_text
    assert "## Visible Test Route" in plan_text
    assert "| 18 | `play` | `1440x900` | `off` |" in plan_text
    assert "## Report Findings" in plan_text


def test_validate_2d_animation_playtest_readiness_plan_accepts_current_artifact(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / ANIMATION_PLAYTEST_REPORT_NAME
    commands_path = tmp_path / "manual-animation-commands.md"
    plan_path = tmp_path / "manual-animation-plan.md"
    write_2d_animation_playtest_report_template(
        report_path,
        version="0.171.0",
        commit="abc1234",
        tester="araxis07",
        platform="macOS local",
        date="2026-06-20",
        prefill_automated_gates=True,
    )
    write_2d_animation_playtest_command_queue(
        build_2d_animation_playtest_command_queue(seed=29),
        commands_path,
    )
    plan = build_2d_animation_playtest_readiness_plan(report_path, commands_path, seed=29)
    write_2d_animation_playtest_readiness_plan(plan, plan_path)

    validation = validate_2d_animation_playtest_readiness_plan(
        plan_path,
        report_path,
        commands_path,
        seed=29,
    )

    assert validation.status == "pass"
    assert validation.expected_status == "manual-required"
    assert validation.findings == ()


def test_validate_2d_animation_playtest_readiness_plan_rejects_missing_route(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / ANIMATION_PLAYTEST_REPORT_NAME
    commands_path = tmp_path / "manual-animation-commands.md"
    plan_path = tmp_path / "manual-animation-plan.md"
    write_2d_animation_playtest_report_template(
        report_path,
        version="0.174.0",
        commit="abc1234",
        tester="araxis07",
        platform="macOS local",
        date="2026-06-20",
        prefill_automated_gates=True,
    )
    write_2d_animation_playtest_command_queue(
        build_2d_animation_playtest_command_queue(seed=31),
        commands_path,
    )
    plan = build_2d_animation_playtest_readiness_plan(report_path, commands_path, seed=31)
    write_2d_animation_playtest_readiness_plan(plan, plan_path)
    plan_path.write_text(
        plan_path.read_text(encoding="utf-8").split("## Visible Test Route", maxsplit=1)[0],
        encoding="utf-8",
    )

    validation = validate_2d_animation_playtest_readiness_plan(
        plan_path,
        report_path,
        commands_path,
        seed=31,
    )

    assert validation.status == "fail"
    assert "missing visible test route section" in validation.findings
    assert "expected 18 visible test route rows, found 0" in validation.findings


def test_validate_2d_animation_playtest_readiness_plan_rejects_stale_artifact(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / ANIMATION_PLAYTEST_REPORT_NAME
    commands_path = tmp_path / "manual-animation-commands.md"
    plan_path = tmp_path / "manual-animation-plan.md"
    write_2d_animation_playtest_report_template(
        report_path,
        version="0.171.0",
        commit="abc1234",
        tester="araxis07",
        platform="macOS local",
        date="2026-06-20",
        prefill_automated_gates=True,
    )
    write_2d_animation_playtest_command_queue(
        build_2d_animation_playtest_command_queue(seed=31),
        commands_path,
    )
    plan = build_2d_animation_playtest_readiness_plan(report_path, commands_path, seed=31)
    write_2d_animation_playtest_readiness_plan(plan, plan_path)
    plan_path.write_text(
        plan_path.read_text(encoding="utf-8").replace(
            "- Status: `manual-required`",
            "- Status: `pass`",
        ),
        encoding="utf-8",
    )

    validation = validate_2d_animation_playtest_readiness_plan(
        plan_path,
        report_path,
        commands_path,
        seed=31,
    )

    assert validation.status == "fail"
    assert any("missing or stale plan line" in finding for finding in validation.findings)


def test_build_2d_animation_playtest_readiness_plan_accepts_signed_pass(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "signed-animation-report.md"
    commands_path = tmp_path / "manual-animation-commands.md"
    report_path.write_text(_completed_animation_playtest_report_text(), encoding="utf-8")
    write_2d_animation_playtest_command_queue(
        build_2d_animation_playtest_command_queue(),
        commands_path,
    )

    plan = build_2d_animation_playtest_readiness_plan(report_path, commands_path)

    assert plan.status == "pass"
    assert plan.open_item_count == 0
    assert plan.steps[0].area == "Release Signoff"


def _completed_animation_playtest_report_text() -> str:
    lines = [
        "# Animation Playtest Report",
        "",
        "## Build",
        "",
        "- Version: 0.161.0",
        "- Commit: abc1234",
        "- Tester: araxis07",
        "- Date: 2026-06-19",
        "- Platform: macOS local",
        "",
        "## Automated Gate Summary",
        "",
        "| Gate | Result | Notes |",
        "| --- | --- | --- |",
        "| ruff check src tests | `pass` | local lint output clean |",
        "| pytest tests/test_frontend_2d.py -q | `pass` | frontend regression subset passed |",
        "| pytest -q | `pass` | full suite completed green |",
        "| audit-2d-motion full/reduced/off | `pass` | all motion modes met budgets |",
        "| audit-2d-visual full/off | `pass` | full and off captures passed |",
        "| audit-2d-animation | `pass` | animation coverage gate passed |",
        "| audit-2d-animation-matrix --output | `pass` | matrix artifact passed default cells |",
        (
            "| prepare-2d-animation-playtest --output | `pass` | "
            "prep artifact generated from matrix evidence |"
        ),
        (
            "| Balance / long-session preflight | `pass` | "
            "balance sweep stayed within release thresholds |"
        ),
        (
            "| validate-animation-playtest-report | `pass` | "
            "completed report validated after manual notes |"
        ),
        "| Headless menu-2d / play-2d | `pass` | headless launchers closed by max frame cap |",
        (
            "| Open-window menu-2d / play-2d smoke | `pass` | "
            "visible windows launched and closed cleanly |"
        ),
        "",
        "## Window Matrix",
        "",
        "| Window | Full | Reduced | Off | Notes |",
        "| --- | --- | --- | --- | --- |",
        "| `820x620` | `pass` | `pass` | `pass` | menu and play checked at compact size |",
        "| `960x640` | `pass` | `pass` | `pass` | menu and play checked at small laptop size |",
        "| `1440x900` | `pass` | `pass` | `pass` | menu and play checked at presentation size |",
        "",
        "## Control Clarity Results",
        "",
        "| Control Area | Result | Notes | Follow-up |",
        "| --- | --- | --- | --- |",
        "| Pause / Resume | `pass` | P opens pause and resume returns to run | none |",
        "| Back / Escape | `pass` | Escape closes overlays before pause | none |",
        "| Menu Return | `pass` | pause menu return lands on title shell | none |",
        "| Help / Hover | `pass` | F1 and hover hints identify controls | none |",
        "| Control Replay Safety | `pass` | replay path covered pause help save menu | none |",
        (
            "| Control Affordance Coverage | `pass` | "
            "click targets present for navigation rails | none |"
        ),
        "| UI Layout Safety | `pass` | compact controls stayed in bounds | none |",
        "| Typography Safety | `pass` | compact labels stayed clipped or fitted | none |",
        "| Motion Modes | `pass` | full reduced off kept same controls | none |",
        "",
        "## Scene Results",
        "",
        "| Scene | Result | Readability Notes | Motion Notes | Follow-up |",
        "| --- | --- | --- | --- | --- |",
        (
            "| Title/Menu | `pass` | wizard and save copy stayed visible | "
            "title actors stayed outside action labels | none |"
        ),
        (
            "| Live Dashboard | `pass` | stat chips and product cards stayed legible | "
            "actor clips did not cover primary controls | none |"
        ),
        (
            "| Action Picker | `pass` | picker cards kept readable option text | "
            "choreography cues pointed at target lane | none |"
        ),
        (
            "| Pending Event | `pass` | option text remained readable | "
            "preview motion stayed secondary to choices | none |"
        ),
        (
            "| Inspector | `pass` | selected row and pager stayed visible | "
            "actor routing did not hide status chips | none |"
        ),
        (
            "| Endgame Board | `pass` | path-fix buttons stayed primary | "
            "cockpit motion stayed behind decision controls | none |"
        ),
        (
            "| Turn Summary | `pass` | timeline cards stayed readable | "
            "reveal pacing supported metrics | none |"
        ),
        (
            "| Outcome/Review | `pass` | after-action notes stayed visible | "
            "outcome cinematic remained the focal state | none |"
        ),
        (
            "| Scene Handoffs | `pass` | navigation context stayed visible | "
            "transitions oriented without hiding controls | none |"
        ),
        "",
        "## Game Feel Results",
        "",
        "| Feedback Area | Result | Notes | Follow-up |",
        "| --- | --- | --- | --- |",
        "| Success Feedback | `pass` | success card named the changed target | none |",
        "| Blocked Feedback | `pass` | blocked card named missing prerequisite | none |",
        "| Impact Values | `pass` | deltas displayed target and value | none |",
        "| Actor + Feedback Match | `pass` | actor pose matched feedback family | none |",
        "",
        "## Release Blockers",
        "",
        "- Hidden primary actions: none",
        "- Unreadable disabled reasons: none",
        "- Actor, tooltip, footer, modal, or button collisions: none",
        "- Missing or unclear actor state reactions: none",
        "- Unclear pause, back, help, save, or menu behavior: none",
        "- Motion-mode regressions: none",
        "- CI artifact anomalies: none",
        "- visual-audit-summary.md anomalies: none",
        "- animation-readiness-matrix.md anomalies: none",
        "- Balance preflight warnings: none",
        "",
        "## Decision",
        "",
        "- Release decision: `pass`",
        "- Required fixes before presenting: none",
        "- Nice-to-have polish: none",
        "- Validator result: pass",
    ]
    route_rows = [
        "",
        "## Visible Route Evidence",
        "",
        "| Step | Target | Window | Motion | Result | Evidence Notes |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for index, item in enumerate(build_2d_animation_playtest_command_queue(), start=1):
        route_rows.append(
            "| "
            f"{index} | "
            f"`{item.target}` | "
            f"`{item.window_size}` | "
            f"`{item.motion_mode}` | "
            "`pass` | "
            f"{item.target} route observed at {item.window_size} with {item.motion_mode} motion |"
        )
    insert_index = lines.index("## Control Clarity Results") - 1
    lines[insert_index:insert_index] = route_rows
    return "\n".join(lines) + "\n"


def test_validate_2d_animation_playtest_report_rejects_unsigned_template(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "unsigned-animation-report.md"
    report_path.write_text(
        "\n".join(
            [
                "# Animation Playtest Report",
                "",
                "| Window | Full |",
                "| --- | --- |",
                "| `820x620` | `todo` |",
                "",
                "- Tester:",
                "- Date:",
                "- Platform:",
                "- Release decision: `pass` / `watch` / `fail`",
                "- Blockers:",
                "- Balance preflight warnings:",
                "- Follow-up fixes:",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    validation = validate_2d_animation_playtest_report(report_path)

    assert isinstance(validation, AnimationPlaytestReportValidation)
    assert validation.status == "fail"
    assert "report still contains todo cells" in validation.findings
    assert "release decision is still the template placeholder" in validation.findings
    assert "missing field: Tester" in validation.findings


def test_validate_2d_animation_playtest_report_accepts_signed_pass(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "signed-animation-report.md"
    report_path.write_text(_completed_animation_playtest_report_text(), encoding="utf-8")

    validation = validate_2d_animation_playtest_report(report_path)

    assert validation.status == "pass"
    assert validation.release_decision == "pass"
    assert validation.findings == ()


def test_validate_2d_animation_playtest_report_rejects_generic_evidence_notes(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "thin-evidence-animation-report.md"
    report_text = _completed_animation_playtest_report_text()
    report_text = report_text.replace(
        "| ruff check src tests | `pass` | local lint output clean |",
        "| ruff check src tests | `pass` | ok |",
    )
    report_text = report_text.replace(
        "| `820x620` | `pass` | `pass` | `pass` | menu and play checked at compact size |",
        "| `820x620` | `pass` | `pass` | `pass` | readable |",
    )
    report_text = report_text.replace(
        "| Pause / Resume | `pass` | P opens pause and resume returns to run | none |",
        "| Pause / Resume | `pass` | clear | none |",
    )
    report_path.write_text(report_text, encoding="utf-8")

    validation = validate_2d_animation_playtest_report(report_path)

    assert validation.status == "fail"
    assert "missing automated gate evidence: ruff check src tests notes" in validation.findings
    assert "missing window matrix evidence: 820x620 notes" in validation.findings
    assert "missing control check evidence: Pause / Resume notes" in validation.findings


def test_validate_2d_animation_playtest_report_rejects_missing_visible_route(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "missing-route-animation-report.md"
    report_text = _completed_animation_playtest_report_text()
    report_text = report_text.replace(
        "\n".join(
            [
                "",
                "## Visible Route Evidence",
                "",
                "| Step | Target | Window | Motion | Result | Evidence Notes |",
                "| ---: | --- | --- | --- | --- | --- |",
            ]
        )
        + "\n"
        + "\n".join(
            (
                "| "
                f"{index} | "
                f"`{item.target}` | "
                f"`{item.window_size}` | "
                f"`{item.motion_mode}` | "
                "`pass` | "
                f"{item.target} route observed at {item.window_size} "
                f"with {item.motion_mode} motion |"
            )
            for index, item in enumerate(build_2d_animation_playtest_command_queue(), start=1)
        )
        + "\n",
        "\n",
    )
    report_path.write_text(report_text, encoding="utf-8")

    validation = validate_2d_animation_playtest_report(report_path)

    assert validation.status == "fail"
    assert "expected 18 visible route evidence rows, found 0" in validation.findings
    assert "missing visible route evidence row: 1" in validation.findings


def test_validate_2d_animation_playtest_report_rejects_missing_required_rows(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "partial-animation-report.md"
    report_text = _completed_animation_playtest_report_text()
    report_text = report_text.replace(
        "| `960x640` | `pass` | `pass` | `pass` | menu and play checked at small laptop size |\n",
        "",
    )
    report_text = report_text.replace(
        "| Inspector | `pass` | selected row and pager stayed visible | "
        "actor routing did not hide status chips | none |\n",
        "",
    )
    report_path.write_text(report_text, encoding="utf-8")

    validation = validate_2d_animation_playtest_report(report_path)

    assert validation.status == "fail"
    assert "missing window matrix row: 960x640" in validation.findings
    assert "missing scene check row: Inspector" in validation.findings


def test_audit_2d_motion_command_reports_matrix(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def fake_run_2d_motion_audit(**kwargs):
        calls.update(kwargs)
        return MotionAuditReport(
            scenario_id=kwargs["scenario_id"],
            difficulty="scenario",
            seed=kwargs["seed"],
            frames=kwargs["frames"],
            cells=(
                MotionAuditCell(
                    width=820,
                    height=620,
                    run_before_pulses=33,
                    run_after_pulses=14,
                    summary_before_pulses=29,
                    summary_after_pulses=12,
                    title_before_pulses=7,
                    title_after_pulses=7,
                    review_before_pulses=4,
                    review_after_pulses=4,
                    inspector_before_pulses=10,
                    inspector_after_pulses=9,
                    long_run_before_pulses=42,
                    long_run_after_pulses=14,
                    average_frame_ms=4.0,
                    max_frame_ms=8.0,
                ),
            ),
            motion_mode=kwargs["motion_mode"].value,
            flow_report=FlowAuditReport(
                command_count=43,
                inspector_action_count=24,
                findings=(),
            ),
        )

    monkeypatch.setattr(cli_module, "run_2d_motion_audit", fake_run_2d_motion_audit)

    result = runner.invoke(
        app,
        [
            "audit-2d-motion",
            "--scenario",
            "founder_journey",
            "--seed",
            "7",
            "--frames",
            "2",
            "--motion-mode",
            "reduced",
        ],
    )

    assert result.exit_code == 0
    assert "2D Motion Audit" in result.output
    assert "motion reduced" in result.output
    assert "2D flow request paths: PASS" in result.output
    assert calls["scenario_id"] == "founder_journey"
    assert calls["seed"] == 7
    assert calls["frames"] == 2
    assert calls["motion_mode"] is MotionMode.REDUCED


def test_audit_2d_visual_command_reports_scene_matrix(monkeypatch, tmp_path: Path) -> None:
    calls: dict[str, object] = {}

    def fake_run_2d_visual_audit(**kwargs):
        calls.update(kwargs)
        return VisualAuditReport(
            scenario_id=kwargs["scenario_id"],
            difficulty="scenario",
            seed=kwargs["seed"],
            motion_mode=kwargs["motion_mode"].value,
            output_dir=str(kwargs["output_dir"]),
            cells=(
                VisualAuditCell(
                    scene_key="run_picker_feedback",
                    width=820,
                    height=620,
                    checksum=12345,
                    unique_color_samples=42,
                    luminance_spread=128,
                    non_dark_ratio=0.42,
                    active_layers=("transition", "picker", "action-feedback"),
                    expected_layers=("transition", "picker", "action-feedback"),
                    output_path=str(tmp_path / "run_picker_feedback_820x620.png"),
                ),
            ),
        )

    monkeypatch.setattr(cli_module, "run_2d_visual_audit", fake_run_2d_visual_audit)

    result = runner.invoke(
        app,
        [
            "audit-2d-visual",
            "--scenario",
            "founder_journey",
            "--seed",
            "7",
            "--motion-mode",
            "reduced",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "2D Visual Audit" in result.output
    assert "motion reduced" in result.output
    assert "Visual audit status: PASS" in result.output
    assert calls["scenario_id"] == "founder_journey"
    assert calls["seed"] == 7
    assert calls["motion_mode"] is MotionMode.REDUCED
    assert calls["output_dir"] == tmp_path


def test_audit_2d_animation_command_reports_completeness_matrix(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def fake_run_2d_animation_audit(**kwargs):
        calls.update(kwargs)
        visual_report = VisualAuditReport(
            scenario_id=kwargs["scenario_id"],
            difficulty="scenario",
            seed=kwargs["seed"],
            motion_mode=MotionMode.FULL.value,
            cells=(
                VisualAuditCell(
                    scene_key="run_outcome_overlay",
                    width=820,
                    height=620,
                    checksum=12345,
                    unique_color_samples=42,
                    luminance_spread=128,
                    non_dark_ratio=0.42,
                    active_layers=("outcome", "outcome-cinematic"),
                    expected_layers=("outcome", "outcome-cinematic"),
                ),
            ),
        )
        motion_report = MotionAuditReport(
            scenario_id=kwargs["scenario_id"],
            difficulty="scenario",
            seed=kwargs["seed"],
            frames=kwargs["frames"],
            cells=(),
            flow_report=FlowAuditReport(
                command_count=44,
                inspector_action_count=82,
                findings=(),
            ),
        )
        return AnimationAuditReport(
            scenario_id=kwargs["scenario_id"],
            difficulty="scenario",
            seed=kwargs["seed"],
            cells=(
                AnimationCoverageCell(
                    area="Outcome Cinematic",
                    required_layers=("outcome-cinematic",),
                    active_layers=("outcome-cinematic",),
                    status="pass",
                    notes="captured",
                ),
                AnimationCoverageCell(
                    area="Manual Playtest",
                    required_layers=("open-window-readability",),
                    active_layers=("advisory",),
                    status="advisory",
                    notes="manual timing still required",
                ),
            ),
            visual_report=visual_report,
            motion_report=motion_report,
            off_motion_report=motion_report,
            advisory_gaps=("Manual open-window playtest is still required.",),
        )

    monkeypatch.setattr(cli_module, "run_2d_animation_audit", fake_run_2d_animation_audit)

    result = runner.invoke(
        app,
        [
            "audit-2d-animation",
            "--scenario",
            "founder_journey",
            "--seed",
            "7",
            "--frames",
            "1",
        ],
    )

    assert result.exit_code == 0
    assert "2D Animation Audit" in result.output
    assert "Outcome Cinematic" in result.output
    assert "Animation Advisory Gaps" in result.output
    assert "Animation audit status: PASS" in result.output
    assert calls["scenario_id"] == "founder_journey"
    assert calls["seed"] == 7
    assert calls["frames"] == 1


def test_audit_2d_animation_matrix_command_reports_broad_readiness(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: dict[str, object] = {}

    def fake_run_2d_animation_matrix_audit(**kwargs):
        calls.update(kwargs)
        return AnimationMatrixReport(
            scenario_ids=kwargs["scenario_ids"],
            difficulty="scenario",
            seeds=kwargs["seeds"],
            frames=kwargs["frames"],
            cells=(
                AnimationMatrixCell(
                    scenario_id="founder_journey",
                    difficulty="scenario",
                    seed=7,
                    status="pass",
                    visual_baseline="13:abc12345",
                    failed_areas=(),
                    advisory_gaps=("Manual open-window playtest is still required.",),
                ),
                AnimationMatrixCell(
                    scenario_id="bootstrap_studio",
                    difficulty="scenario",
                    seed=13,
                    status="pass",
                    visual_baseline="13:def67890",
                    failed_areas=(),
                    advisory_gaps=("Manual open-window playtest is still required.",),
                ),
            ),
        )

    monkeypatch.setattr(
        cli_module,
        "run_2d_animation_matrix_audit",
        fake_run_2d_animation_matrix_audit,
    )

    output_path = tmp_path / ANIMATION_MATRIX_REPORT_NAME
    result = runner.invoke(
        app,
        [
            "audit-2d-animation-matrix",
            "--scenario",
            "founder_journey",
            "--scenario",
            "bootstrap_studio",
            "--seed",
            "7",
            "--seed",
            "13",
            "--frames",
            "1",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert "2D Animation Matrix" in result.output
    assert "founder_journey" in result.output
    assert "bootstrap_studio" in result.output
    assert "Animation matrix status: PASS" in result.output
    assert "Animation matrix report written" in result.output
    assert output_path.exists()
    assert "13:abc12345" in output_path.read_text(encoding="utf-8")
    assert calls["scenario_ids"] == ("founder_journey", "bootstrap_studio")
    assert calls["seeds"] == (7, 13)
    assert calls["frames"] == 1


def test_prepare_2d_animation_playtest_command_writes_prep_report(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: dict[str, object] = {}

    def fake_run_2d_animation_matrix_audit(**kwargs):
        calls.update(kwargs)
        return AnimationMatrixReport(
            scenario_ids=kwargs["scenario_ids"],
            difficulty="scenario",
            seeds=kwargs["seeds"],
            frames=kwargs["frames"],
            cells=(
                AnimationMatrixCell(
                    scenario_id="founder_journey",
                    difficulty="scenario",
                    seed=7,
                    status="pass",
                    visual_baseline="13:abc12345",
                    failed_areas=(),
                    advisory_gaps=("Manual open-window playtest is still required.",),
                ),
            ),
        )

    monkeypatch.setattr(
        cli_module,
        "run_2d_animation_matrix_audit",
        fake_run_2d_animation_matrix_audit,
    )

    output_path = tmp_path / ANIMATION_PLAYTEST_PREP_REPORT_NAME
    result = runner.invoke(
        app,
        [
            "prepare-2d-animation-playtest",
            "--scenario",
            "founder_journey",
            "--seed",
            "7",
            "--frames",
            "1",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert "2D Animation Playtest Prep" in result.output
    assert "Manual Control Clarity Gate" in result.output
    assert "Manual Scene Animation Gate" in result.output
    assert "Manual Game Feel Gate" in result.output
    assert "Manual Signoff Required" in result.output
    assert "Status READY" in result.output
    assert "Animation playtest prep report written" in result.output
    assert output_path.exists()
    report_text = output_path.read_text(encoding="utf-8")
    assert "- Manual result: `not completed by automation`" in report_text
    assert "Control Clarity Checklist" in report_text
    assert "Manual Completion Gate" in report_text
    assert "`founder_journey` | `7` | `pass` | `13:abc12345`" in report_text
    assert calls["scenario_ids"] == ("founder_journey",)
    assert calls["seeds"] == (7,)
    assert calls["frames"] == 1


def test_draft_animation_playtest_report_command_writes_strict_template(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / ANIMATION_PLAYTEST_REPORT_NAME

    result = runner.invoke(
        app,
        [
            "draft-animation-playtest-report",
            "--output",
            str(output_path),
            "--commit",
            "abc1234",
            "--tester",
            "araxis07",
            "--platform",
            "macOS local",
            "--date",
            "2026-06-19",
        ],
    )

    assert result.exit_code == 0
    assert "Animation Playtest Report Draft" in result.output
    assert output_path.exists()
    report_text = output_path.read_text(encoding="utf-8")
    assert "- Commit: abc1234" in report_text
    assert "| Pause / Resume | `todo`" in report_text
    assert "| Outcome/Review | `todo`" in report_text
    assert "| Actor + Feedback Match | `todo`" in report_text


def test_draft_animation_playtest_report_command_prefills_automated_gates(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / ANIMATION_PLAYTEST_REPORT_NAME

    result = runner.invoke(
        app,
        [
            "draft-animation-playtest-report",
            "--output",
            str(output_path),
            "--commit",
            "abc1234",
            "--tester",
            "araxis07",
            "--platform",
            "macOS local",
            "--date",
            "2026-06-19",
            "--prefill-automated-gates",
        ],
    )

    assert result.exit_code == 0
    report_text = output_path.read_text(encoding="utf-8")
    assert "| ruff check src tests | `pass`" in report_text
    assert "| Open-window menu-2d / play-2d smoke | `pass`" in report_text
    assert "| Pause / Resume | `todo`" in report_text


def test_validate_animation_playtest_report_command_accepts_completed_report(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "completed-animation-report.md"
    report_path.write_text(_completed_animation_playtest_report_text(), encoding="utf-8")

    result = runner.invoke(app, ["validate-animation-playtest-report", str(report_path)])

    assert result.exit_code == 0
    assert "Animation Playtest Report Validation" in result.output
    assert "Status" in result.output
    assert "PASS" in result.output


def test_validate_animation_playtest_report_command_rejects_incomplete_report(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "incomplete-animation-report.md"
    report_path.write_text(
        "\n".join(
            [
                "# Animation Playtest Report",
                "",
                "| Control | Result |",
                "| --- | --- |",
                "| Pause / Resume | `todo` |",
                "",
                "- Tester:",
                "- Date:",
                "- Platform:",
                "- Release decision: `pass` / `watch` / `fail`",
                "- Blockers:",
                "- Balance preflight warnings:",
                "- Follow-up fixes:",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["validate-animation-playtest-report", str(report_path)])

    assert result.exit_code == 1
    assert "Validation Findings" in result.output
    assert "Manual animation signoff is incomplete" in result.output


def test_animation_playtest_status_command_groups_incomplete_report(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / ANIMATION_PLAYTEST_REPORT_NAME
    write_2d_animation_playtest_report_template(
        report_path,
        version="0.164.0",
        commit="abc1234",
        tester="araxis07",
        platform="macOS local",
        date="2026-06-19",
        prefill_automated_gates=True,
    )

    result = runner.invoke(app, ["animation-playtest-status", str(report_path)])

    assert result.exit_code == 0
    assert "Animation Playtest Status" in result.output
    assert "Manual Window Matrix" in result.output
    assert "Manual Control Checks" in result.output
    assert "Manual Scene Checks" in result.output
    assert "Manual Game Feel" in result.output
    assert "Status FAIL" in result.output


def test_animation_playtest_status_command_can_fail_on_incomplete(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / ANIMATION_PLAYTEST_REPORT_NAME
    write_2d_animation_playtest_report_template(
        report_path,
        version="0.164.0",
        commit="abc1234",
        tester="araxis07",
        platform="macOS local",
        date="2026-06-19",
        prefill_automated_gates=True,
    )

    result = runner.invoke(
        app,
        ["animation-playtest-status", str(report_path), "--fail-on-incomplete"],
    )

    assert result.exit_code == 1
    assert "Status FAIL" in result.output


def test_animation_playtest_status_command_accepts_completed_report(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / ANIMATION_PLAYTEST_REPORT_NAME
    report_path.write_text(_completed_animation_playtest_report_text(), encoding="utf-8")

    result = runner.invoke(app, ["animation-playtest-status", str(report_path)])

    assert result.exit_code == 0
    assert "Complete" in result.output
    assert "Status PASS" in result.output


def test_animation_playtest_commands_command_writes_queue(tmp_path: Path) -> None:
    output_path = tmp_path / "manual-animation-commands.md"

    result = runner.invoke(
        app,
        [
            "animation-playtest-commands",
            "--scenario",
            "founder_journey",
            "--seed",
            "11",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert "Animation Playtest Command Queue" in result.output
    assert "18 command(s) queued" in result.output
    assert "Animation playtest command queue written" in result.output
    assert output_path.exists()
    report_text = output_path.read_text(encoding="utf-8")
    assert "- Manual result: `not completed by automation`" in report_text
    assert "play-2d --scenario founder_journey --seed 11" in report_text
    assert "menu-2d --window-size 1440x900 --motion-mode off" in report_text


def test_validate_animation_playtest_commands_command_accepts_complete_queue(
    tmp_path: Path,
) -> None:
    queue = build_2d_animation_playtest_command_queue(seed=11)
    output_path = tmp_path / "manual-animation-commands.md"
    write_2d_animation_playtest_command_queue(queue, output_path)

    result = runner.invoke(
        app,
        [
            "validate-animation-playtest-commands",
            str(output_path),
            "--seed",
            "11",
        ],
    )

    assert result.exit_code == 0
    assert "Animation Playtest Command Validation" in result.output
    assert "Status" in result.output
    assert "PASS" in result.output


def test_validate_animation_playtest_commands_command_rejects_missing_queue_row(
    tmp_path: Path,
) -> None:
    queue = build_2d_animation_playtest_command_queue()
    output_path = tmp_path / "manual-animation-commands.md"
    write_2d_animation_playtest_command_queue(queue[:-1], output_path)

    result = runner.invoke(
        app,
        ["validate-animation-playtest-commands", str(output_path)],
    )

    assert result.exit_code == 1
    assert "Command Queue Findings" in result.output
    assert "expected 18 command rows, found 17" in result.output


def test_animation_playtest_plan_command_reports_manual_required(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / ANIMATION_PLAYTEST_REPORT_NAME
    commands_path = tmp_path / "manual-animation-commands.md"
    write_2d_animation_playtest_report_template(
        report_path,
        version="0.169.0",
        commit="abc1234",
        tester="araxis07",
        platform="macOS local",
        date="2026-06-20",
        prefill_automated_gates=True,
    )
    write_2d_animation_playtest_command_queue(
        build_2d_animation_playtest_command_queue(seed=17),
        commands_path,
    )

    result = runner.invoke(
        app,
        [
            "animation-playtest-plan",
            str(report_path),
            str(commands_path),
            "--seed",
            "17",
        ],
    )

    assert result.exit_code == 0
    assert "Animation Playtest Plan" in result.output
    assert "MANUAL-REQUIRED" in result.output
    assert "Manual Window Matrix" in result.output
    assert "Next Animation QA Steps" in result.output


def test_animation_playtest_plan_command_writes_markdown_output(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / ANIMATION_PLAYTEST_REPORT_NAME
    commands_path = tmp_path / "manual-animation-commands.md"
    output_path = tmp_path / "manual-animation-plan.md"
    write_2d_animation_playtest_report_template(
        report_path,
        version="0.170.0",
        commit="abc1234",
        tester="araxis07",
        platform="macOS local",
        date="2026-06-20",
        prefill_automated_gates=True,
    )
    write_2d_animation_playtest_command_queue(
        build_2d_animation_playtest_command_queue(seed=19),
        commands_path,
    )

    result = runner.invoke(
        app,
        [
            "animation-playtest-plan",
            str(report_path),
            str(commands_path),
            "--seed",
            "19",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert "Animation playtest plan written" in result.output
    plan_text = output_path.read_text(encoding="utf-8")
    assert "- Status: `manual-required`" in plan_text
    assert "- Manual result: `not completed by automation`" in plan_text
    assert "## Next Animation QA Steps" in plan_text


def test_validate_animation_playtest_plan_command_accepts_current_artifact(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / ANIMATION_PLAYTEST_REPORT_NAME
    commands_path = tmp_path / "manual-animation-commands.md"
    plan_path = tmp_path / "manual-animation-plan.md"
    write_2d_animation_playtest_report_template(
        report_path,
        version="0.171.0",
        commit="abc1234",
        tester="araxis07",
        platform="macOS local",
        date="2026-06-20",
        prefill_automated_gates=True,
    )
    write_2d_animation_playtest_command_queue(
        build_2d_animation_playtest_command_queue(seed=37),
        commands_path,
    )
    write_2d_animation_playtest_readiness_plan(
        build_2d_animation_playtest_readiness_plan(report_path, commands_path, seed=37),
        plan_path,
    )

    result = runner.invoke(
        app,
        [
            "validate-animation-playtest-plan",
            str(report_path),
            str(commands_path),
            str(plan_path),
            "--seed",
            "37",
        ],
    )

    assert result.exit_code == 0
    assert "Animation Playtest Plan Validation" in result.output
    assert "MANUAL-REQUIRED" in result.output
    assert "PASS" in result.output


def test_validate_animation_playtest_plan_command_rejects_stale_artifact(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / ANIMATION_PLAYTEST_REPORT_NAME
    commands_path = tmp_path / "manual-animation-commands.md"
    plan_path = tmp_path / "manual-animation-plan.md"
    write_2d_animation_playtest_report_template(
        report_path,
        version="0.171.0",
        commit="abc1234",
        tester="araxis07",
        platform="macOS local",
        date="2026-06-20",
        prefill_automated_gates=True,
    )
    write_2d_animation_playtest_command_queue(
        build_2d_animation_playtest_command_queue(),
        commands_path,
    )
    plan = build_2d_animation_playtest_readiness_plan(report_path, commands_path)
    write_2d_animation_playtest_readiness_plan(plan, plan_path)
    plan_path.write_text(
        plan_path.read_text(encoding="utf-8").replace(
            f"- Open items: `{plan.open_item_count}`",
            "- Open items: `0`",
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "validate-animation-playtest-plan",
            str(report_path),
            str(commands_path),
            str(plan_path),
        ],
    )

    assert result.exit_code == 1
    assert "Plan Artifact Findings" in result.output
    assert "missing or stale plan line" in result.output


def test_animation_playtest_plan_command_can_fail_on_incomplete(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / ANIMATION_PLAYTEST_REPORT_NAME
    commands_path = tmp_path / "manual-animation-commands.md"
    write_2d_animation_playtest_report_template(
        report_path,
        version="0.169.0",
        commit="abc1234",
        tester="araxis07",
        platform="macOS local",
        date="2026-06-20",
        prefill_automated_gates=True,
    )
    write_2d_animation_playtest_command_queue(
        build_2d_animation_playtest_command_queue(),
        commands_path,
    )

    result = runner.invoke(
        app,
        [
            "animation-playtest-plan",
            str(report_path),
            str(commands_path),
            "--fail-on-incomplete",
        ],
    )

    assert result.exit_code == 1
    assert "MANUAL-REQUIRED" in result.output


def test_animation_playtest_plan_command_accepts_completed_report(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "signed-animation-report.md"
    commands_path = tmp_path / "manual-animation-commands.md"
    report_path.write_text(_completed_animation_playtest_report_text(), encoding="utf-8")
    write_2d_animation_playtest_command_queue(
        build_2d_animation_playtest_command_queue(),
        commands_path,
    )

    result = runner.invoke(
        app,
        ["animation-playtest-plan", str(report_path), str(commands_path)],
    )

    assert result.exit_code == 0
    assert "Status" in result.output
    assert "PASS" in result.output
    assert "Release Signoff" in result.output


def test_prepare_animation_playtest_session_command_writes_draft_queue_and_plan(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / ANIMATION_PLAYTEST_REPORT_NAME
    commands_path = tmp_path / "manual-animation-commands.md"
    plan_path = tmp_path / "manual-animation-plan.md"

    result = runner.invoke(
        app,
        [
            "prepare-animation-playtest-session",
            "--scenario",
            "founder_journey",
            "--seed",
            "17",
            "--report-output",
            str(report_path),
            "--commands-output",
            str(commands_path),
            "--plan-output",
            str(plan_path),
            "--commit",
            "abc1234",
            "--tester",
            "araxis07",
            "--platform",
            "macOS local",
            "--date",
            "2026-06-20",
            "--prefill-automated-gates",
        ],
    )

    assert result.exit_code == 0
    assert "Animation Playtest Session" in result.output
    assert "Animation Playtest Status" in result.output
    assert "Status FAIL" in result.output
    assert report_path.exists()
    assert commands_path.exists()
    assert plan_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    commands_text = commands_path.read_text(encoding="utf-8")
    plan_text = plan_path.read_text(encoding="utf-8")
    assert "- Commit: abc1234" in report_text
    assert "- Tester: araxis07" in report_text
    assert "| ruff check src tests | `pass`" in report_text
    assert "| `820x620` | `todo` | `todo` | `todo`" in report_text
    assert "- Manual result: `not completed by automation`" in commands_text
    assert "play-2d --scenario founder_journey --seed 17" in commands_text
    assert "menu-2d --window-size 1440x900 --motion-mode off" in commands_text
    assert "- Status: `manual-required`" in plan_text
    assert "- Command queue status: `pass`" in plan_text
    assert "- Report status: `fail`" in plan_text
    assert "- Manual result: `not completed by automation`" in plan_text
    assert "## Visible Test Route" in plan_text
    assert "| 18 | `play` | `1440x900` | `off` |" in plan_text


def test_ci_workflow_runs_animation_matrix_artifact_gate() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert (
        "uv run nexus-tech audit-2d-animation-matrix --frames 1 "
        "--output /tmp/nexus-tech-animation-matrix.md"
    ) in workflow
    assert "nexus-tech-2d-animation-matrix" in workflow
    assert "path: /tmp/nexus-tech-animation-matrix.md" in workflow
    assert (
        "uv run nexus-tech prepare-2d-animation-playtest --frames 1 "
        "--output /tmp/nexus-tech-animation-playtest-prep.md"
    ) in workflow
    assert "nexus-tech-2d-animation-playtest-prep" in workflow


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
            "--window-size",
            "820x620",
            "--motion-mode",
            "off",
        ],
    )

    assert result.exit_code == 0
    assert captured["scenario_id"] == "founder_journey"
    assert captured["seed"] == 7
    assert captured["headless"] is True
    assert captured["window_size"] == (820, 620)
    assert captured["max_frames"] == 2
    assert captured["motion_mode"] is MotionMode.OFF


def test_play_2d_command_rejects_invalid_window_size(monkeypatch) -> None:
    called = False

    def fake_start_new_game_2d(**_kwargs) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(cli_module, "start_new_game_2d", fake_start_new_game_2d)

    result = runner.invoke(app, ["play-2d", "--window-size", "tiny"])

    assert result.exit_code == 1
    assert "Invalid 2D Window Size" in result.output
    assert "Use WIDTHxHEIGHT" in result.output
    assert called is False


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
            "--window-size",
            "960x640",
            "--motion-mode",
            "reduced",
        ],
    )

    assert result.exit_code == 0
    assert captured["headless"] is True
    assert captured["window_size"] == (960, 640)
    assert captured["max_frames"] == 2
    assert captured["motion_mode"] is MotionMode.REDUCED
