"""Deterministic 2D motion pressure audit helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from nexus_tech.domain.models import (
    DifficultyMode,
    ProductReleaseType,
    RoadmapProjectType,
    TurnAction,
)
from nexus_tech.frontend_2d.app import Frontend2DUnavailableError
from nexus_tech.frontend_2d.catalog import list_scenario_choices
from nexus_tech.frontend_2d.context import (
    build_command_request,
    build_inspector_action_request,
    explain_command_unavailable,
    explain_inspector_action_unavailable,
)
from nexus_tech.frontend_2d.tween import MotionMode, normalize_motion_mode
from nexus_tech.frontend_2d.viewmodels import (
    build_deep_dive_panel_view_models,
    build_run_review_view_model,
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

DEFAULT_MOTION_AUDIT_SIZES: tuple[tuple[int, int], ...] = (
    (820, 620),
    (960, 640),
    (1280, 720),
)


@dataclass(frozen=True)
class MotionAuditCell:
    """One viewport result from the 2D motion audit."""

    width: int
    height: int
    run_before_pulses: int
    run_after_pulses: int
    summary_before_pulses: int
    summary_after_pulses: int
    title_before_pulses: int
    title_after_pulses: int
    review_before_pulses: int
    review_after_pulses: int
    inspector_before_pulses: int
    inspector_after_pulses: int
    long_run_before_pulses: int
    long_run_after_pulses: int
    average_frame_ms: float
    max_frame_ms: float
    transition_active_scenes: int = 0
    transition_disabled_scenes: int = 0
    entity_motion_active_samples: int = 0
    entity_motion_disabled_samples: int = 0

    @property
    def status(self) -> str:
        """Classify whether the viewport stayed within motion stability budgets."""

        if (
            self.run_after_pulses <= 18
            and self.summary_after_pulses <= 12
            and self.title_after_pulses <= 14
            and self.review_after_pulses <= 6
            and self.inspector_after_pulses <= 12
            and self.long_run_after_pulses <= 18
            and self.average_frame_ms <= 24.0
            and self.max_frame_ms <= 50.0
        ):
            return "pass"
        if (
            self.run_after_pulses <= 24
            and self.summary_after_pulses <= 18
            and self.title_after_pulses <= 18
            and self.review_after_pulses <= 10
            and self.inspector_after_pulses <= 16
            and self.long_run_after_pulses <= 24
            and self.average_frame_ms <= 33.0
            and self.max_frame_ms <= 75.0
        ):
            return "watch"
        return "fail"

    @property
    def notes(self) -> str:
        """Return a compact human-readable summary for CLI output."""

        notes: list[str] = []
        if self.run_after_pulses > 18:
            notes.append("run pulse bank above target")
        if self.summary_after_pulses > 12:
            notes.append("summary pulse bank above target")
        if self.title_after_pulses > 14:
            notes.append("title pulse bank above target")
        if self.review_after_pulses > 6:
            notes.append("review pulse bank above target")
        if self.inspector_after_pulses > 12:
            notes.append("inspector pulse bank above target")
        if self.long_run_after_pulses > 18:
            notes.append("long-run pulse bank above target")
        if self.average_frame_ms > 24.0:
            notes.append("frame budget above target")
        if self.max_frame_ms > 50.0:
            notes.append("max frame spike above target")
        return "; ".join(notes) if notes else "stable"


@dataclass(frozen=True)
class FlowAuditFinding:
    """One 2D command or inspector action that can still fall through at runtime."""

    surface: str
    command: str
    detail: str


@dataclass(frozen=True)
class FlowAuditReport:
    """Request-path coverage for the 2D command and inspector surfaces."""

    command_count: int
    inspector_action_count: int
    findings: tuple[FlowAuditFinding, ...]

    @property
    def status(self) -> str:
        """Return pass only when no runtime fallback path remains."""

        return "pass" if not self.findings else "fail"


@dataclass(frozen=True)
class MotionAuditReport:
    """Complete deterministic 2D motion audit result."""

    scenario_id: str
    difficulty: str
    seed: int
    frames: int
    cells: tuple[MotionAuditCell, ...]
    motion_mode: str = MotionMode.FULL.value
    flow_report: FlowAuditReport = FlowAuditReport(
        command_count=0,
        inspector_action_count=0,
        findings=(),
    )

    @property
    def status(self) -> str:
        """Return the worst status across all viewport cells."""

        statuses = {cell.status for cell in self.cells}
        if "fail" in statuses:
            return "fail"
        if self.flow_report.status == "fail":
            return "fail"
        if "watch" in statuses:
            return "watch"
        return "pass"


def run_2d_motion_audit(
    *,
    scenario_id: str,
    difficulty_mode: DifficultyMode | None,
    seed: int,
    frames: int = 90,
    sizes: tuple[tuple[int, int], ...] = DEFAULT_MOTION_AUDIT_SIZES,
    motion_mode: MotionMode | str = MotionMode.FULL,
) -> MotionAuditReport:
    """Run a deterministic headless 2D motion stability audit."""

    if frames < 1:
        raise ValueError("frames must be at least 1")
    motion_mode = normalize_motion_mode(motion_mode)

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    try:
        import pygame
    except ModuleNotFoundError as error:
        raise Frontend2DUnavailableError(
            "pygame-ce is not installed. Install the optional 2D runtime first."
        ) from error

    from nexus_tech.frontend_2d.scenes import ReviewScene, RunScene, TitleScene, TurnSummaryScene
    from nexus_tech.frontend_2d.widgets import DANGER, create_fonts

    pygame.init()
    pygame.font.init()
    try:
        fonts = create_fonts(pygame)
        state = _build_motion_audit_state(
            scenario_id=scenario_id,
            difficulty_mode=difficulty_mode,
            seed=seed,
        )
        previous_state = state.model_copy(deep=True)
        resolution = resolve_turn(state, RandomSource(seed=seed + 7))
        cells: list[MotionAuditCell] = []
        flow_report = run_2d_flow_audit(seed=seed)
        with TemporaryDirectory(prefix="nexus-tech-motion-audit-") as tmpdir:
            coordinator = SaveLoadCoordinator(Path(tmpdir) / "motion-audit.db")
            for width, height in sizes:
                surface = pygame.display.set_mode((width, height), pygame.HIDDEN)
                run_scene = RunScene(
                    pygame=pygame,
                    fonts=fonts,
                    state=state,
                    rng=RandomSource(seed=seed),
                    slot_name="motion-audit",
                    save_callback=lambda *_args: None,
                    show_ready_event=False,
                    motion_mode=motion_mode,
                    entry_transition="boot_run",
                )
                transition_active_count = int(run_scene.scene_transition_active())
                transition_disabled_count = int(not run_scene.scene_transition_active())
                entity_active_count = int(run_scene._entity_motion_strength("panel:products") > 0)
                entity_active_count += int(run_scene._entity_motion_strength("panel:stats") > 0)
                entity_disabled_count = 2 - entity_active_count
                run_scene._set_deep_panel("pipeline")
                entity_active_count += int(run_scene._entity_motion_strength("panel:pipeline") > 0)
                entity_disabled_count += int(
                    run_scene._entity_motion_strength("panel:pipeline") <= 0
                )
                run_scene._open_inspector("pipeline")
                _exercise_inspector_interactions(run_scene)
                inspector_before = run_scene._motion_pulses.live_count()
                inspector_avg, inspector_max = _exercise_scene(run_scene, surface, frames)
                inspector_after = run_scene._motion_pulses.live_count()
                run_scene._set_deep_panel("endgame")
                run_scene._run_command(TurnAction.SET_COMPANY_STRATEGY.value)
                _seed_dense_run_pulses(run_scene)
                run_before = run_scene._motion_pulses.live_count()
                run_avg, run_max = _exercise_scene(run_scene, surface, frames)
                long_before, long_after, long_avg, long_max = _exercise_long_run_pressure(
                    run_scene,
                    surface,
                    frames,
                )

                summary_scene = TurnSummaryScene(
                    pygame=pygame,
                    fonts=fonts,
                    state=resolution.state,
                    rng=RandomSource(seed=seed + 7),
                    slot_name="motion-audit",
                    save_callback=lambda *_args: None,
                    previous_state=previous_state,
                    resolution=resolution,
                    selected_product_id=resolution.state.products[0].id.hex,
                    dirty=True,
                    motion_mode=motion_mode,
                    entry_transition="run_to_summary",
                )
                transition_active_count += int(summary_scene.scene_transition_active())
                transition_disabled_count += int(not summary_scene.scene_transition_active())
                _seed_dense_summary_pulses(summary_scene)
                summary_before = summary_scene._motion_pulses.live_count()
                summary_avg, summary_max = _exercise_scene(summary_scene, surface, frames)

                title_scene = TitleScene(
                    pygame=pygame,
                    fonts=fonts,
                    state=create_new_game("NEXUS TECH", "Nexus One"),
                    rng=RandomSource(seed=seed + 11),
                    slot_name="motion-audit",
                    save_callback=lambda *_args: None,
                    coordinator=coordinator,
                    initial_mode="menu",
                    motion_mode=motion_mode,
                    entry_transition="boot_title",
                )
                transition_active_count += int(title_scene.scene_transition_active())
                transition_disabled_count += int(not title_scene.scene_transition_active())
                _exercise_title_subflows(title_scene, coordinator, seed)
                title_before = title_scene._motion_pulses.live_count()
                title_avg, title_max = _exercise_scene(title_scene, surface, frames)

                review_state = resolution.state.model_copy(deep=True)
                review_state.company.game_over = True
                review_state.company.cash_on_hand = Decimal("-125.00")
                review_scene = ReviewScene(
                    pygame=pygame,
                    fonts=fonts,
                    state=review_state,
                    rng=RandomSource(seed=seed + 13),
                    slot_name="motion-audit",
                    save_callback=lambda *_args: None,
                    view_model=build_run_review_view_model(review_state),
                    accent=DANGER,
                    primary_title="Esc Close",
                    primary_detail="Leave the 2D shell.",
                    return_scene_factory=None,
                    allow_save=False,
                    dirty=False,
                    motion_mode=motion_mode,
                    entry_transition="run_to_review",
                )
                transition_active_count += int(review_scene.scene_transition_active())
                transition_disabled_count += int(not review_scene.scene_transition_active())
                review_before = review_scene._motion_pulses.live_count()
                review_avg, review_max = _exercise_scene(review_scene, surface, frames)

                averages = (
                    run_avg,
                    summary_avg,
                    title_avg,
                    review_avg,
                    inspector_avg,
                    long_avg,
                )
                maxes = (
                    run_max,
                    summary_max,
                    title_max,
                    review_max,
                    inspector_max,
                    long_max,
                )
                cells.append(
                    MotionAuditCell(
                        width=width,
                        height=height,
                        run_before_pulses=run_before,
                        run_after_pulses=run_scene._motion_pulses.live_count(),
                        summary_before_pulses=summary_before,
                        summary_after_pulses=summary_scene._motion_pulses.live_count(),
                        title_before_pulses=title_before,
                        title_after_pulses=title_scene._motion_pulses.live_count(),
                        review_before_pulses=review_before,
                        review_after_pulses=review_scene._motion_pulses.live_count(),
                        inspector_before_pulses=inspector_before,
                        inspector_after_pulses=inspector_after,
                        long_run_before_pulses=long_before,
                        long_run_after_pulses=long_after,
                        average_frame_ms=round(sum(averages) / len(averages), 2),
                        max_frame_ms=round(max(maxes), 2),
                        transition_active_scenes=transition_active_count,
                        transition_disabled_scenes=transition_disabled_count,
                        entity_motion_active_samples=entity_active_count,
                        entity_motion_disabled_samples=entity_disabled_count,
                    )
                )
        return MotionAuditReport(
            scenario_id=scenario_id,
            difficulty=difficulty_mode.value if difficulty_mode is not None else "scenario",
            seed=seed,
            frames=frames,
            cells=tuple(cells),
            motion_mode=motion_mode.value,
            flow_report=flow_report,
        )
    finally:
        pygame.quit()


run_motion_audit = run_2d_motion_audit


def run_2d_flow_audit(*, seed: int = 7) -> FlowAuditReport:
    """Audit runtime request paths before 2D actions can hit fallback warnings."""

    findings: list[FlowAuditFinding] = []
    with TemporaryDirectory(prefix="nexus-tech-flow-audit-") as tmpdir:
        choices = [
            choice
            for choice in list_scenario_choices(Path(tmpdir) / "flow-audit.db")
            if not choice.locked
        ]
    commands = _collect_surfaced_commands(choices)
    for command in sorted(commands):
        command_supported = False
        command_explained = False
        for choice in choices:
            state = create_new_game(
                "NEXUS TECH",
                "Nexus One",
                scenario_id=choice.scenario_id,
                difficulty_mode=choice.default_difficulty,
                campaign_goal_id=choice.default_goal_id,
            )
            product_id = state.products[0].id.hex
            request = build_command_request(
                state,
                command=command,
                selected_product_id=product_id,
            )
            reason = explain_command_unavailable(
                state,
                command=command,
                selected_product_id=product_id,
            )
            command_supported = command_supported or request is not None
            command_explained = command_explained or reason is not None
        if not command_supported and not command_explained:
            findings.append(
                FlowAuditFinding(
                    surface="command",
                    command=command,
                    detail="surfaced command has no request path or disabled explanation",
                )
            )

    inspector_count = 0
    for state in (
        create_new_game("NEXUS TECH", "Nexus One"),
        _build_motion_audit_state(
            scenario_id="founder_journey",
            difficulty_mode=None,
            seed=seed,
        ),
    ):
        product_id = state.products[0].id.hex
        for panel in build_deep_dive_panel_view_models(state, selected_product_id=product_id):
            for section in panel.inspectors:
                for item in section.items:
                    for action in item.actions:
                        inspector_count += 1
                        request = build_inspector_action_request(
                            state,
                            panel_key=panel.key,
                            section_key=section.key,
                            command=action.command,
                            payload=item.payload,
                            selected_product_id=product_id,
                        )
                        reason = explain_inspector_action_unavailable(
                            state,
                            panel_key=panel.key,
                            section_key=section.key,
                            command=action.command,
                            payload=item.payload,
                            selected_product_id=product_id,
                        )
                        if request is None and reason is None:
                            findings.append(
                                FlowAuditFinding(
                                    surface=f"inspector:{panel.key}:{section.key}",
                                    command=action.command,
                                    detail=(
                                        f"{item.title} has no request path or disabled explanation"
                                    ),
                                )
                            )
    return FlowAuditReport(
        command_count=len(commands),
        inspector_action_count=inspector_count,
        findings=tuple(findings),
    )


def _collect_surfaced_commands(choices) -> set[str]:
    commands: set[str] = set()
    for choice in choices:
        state = create_new_game(
            "NEXUS TECH",
            "Nexus One",
            scenario_id=choice.scenario_id,
            difficulty_mode=choice.default_difficulty,
            campaign_goal_id=choice.default_goal_id,
        )
        product_id = state.products[0].id.hex
        guide = build_guided_opening(state)
        commands.add(guide.current_command)
        commands.update(step.command for step in guide.steps)
        commands.update(rec.command for rec in build_turn_coach(state).recommendations)
        commands.update(item.command for item in build_risk_forecast(state).items)
        pressure = calculate_endgame_pressure(state, calculate_endgame_readiness(state))
        commands.update(pressure.path_gate_commands)
        if pressure.path_gate_command_alert in TurnAction._value2member_map_:
            commands.add(pressure.path_gate_command_alert)
        outcome = evaluate_exit_outcome(state)
        commands.update(outcome.path_gate_commands)
        if outcome.path_gate_command_alert in TurnAction._value2member_map_:
            commands.add(outcome.path_gate_command_alert)
        for panel in build_deep_dive_panel_view_models(state, selected_product_id=product_id):
            commands.update(action.command for action in panel.actions)
    return commands


def _exercise_scene(scene, surface, frames: int) -> tuple[float, float]:
    frame_times: list[float] = []
    for _index in range(frames):
        frame_start = perf_counter()
        scene.update(1 / 60)
        scene.draw(surface)
        frame_times.append((perf_counter() - frame_start) * 1000)
    return sum(frame_times) / len(frame_times), max(frame_times)


def _exercise_title_subflows(scene, coordinator: SaveLoadCoordinator, seed: int) -> None:
    slot_state = create_new_game("NEXUS TECH", "Nexus One")
    coordinator.save_game("motion-audit-slot", slot_state, RandomSource(seed=seed + 21))
    archive_state = slot_state.model_copy(deep=True)
    archive_state.company.game_over = True
    archive_state.company.cash_on_hand = Decimal("-125.00")
    coordinator.save_game("motion-audit-archive", archive_state, RandomSource(seed=seed + 22))
    scene._refresh_lists()
    scene._handle_menu_action("load_slots")
    scene._open_slot_detail("motion-audit-slot")
    scene._handle_slot_action("rename")
    scene._set_text_input(None)
    scene._handle_slot_action("delete")
    scene._set_confirm_delete_slot_name(None)
    scene._handle_menu_action("archives")
    scene._handle_menu_action("meta")
    scene._handle_menu_action("new_wizard")
    scene._open_wizard_text_modal("company")


def _exercise_inspector_interactions(scene) -> None:
    scene._select_inspector_section("candidates")
    scene._cycle_inspector_sort_mode()
    scene._cycle_inspector_filter_mode()
    scene._focus_inspector_actionable()
    scene._focus_inspector_hotspot()
    scene._change_inspector_page(1)
    scene._change_inspector_item(1)


def _exercise_long_run_pressure(scene, surface, frames: int) -> tuple[int, int, float, float]:
    for index in range(36):
        scene._motion_pulses.trigger(f"audit:long:{index}", intensity=0.16, decay=1.6)
        if index % 4 == 0:
            scene._motion_pulses.trigger("feed", intensity=0.42, decay=1.6)
        if index % 6 == 0:
            scene._motion_pulses.trigger("panel:endgame", intensity=0.48, decay=1.8)
    before = scene._motion_pulses.live_count()
    average, max_frame = _exercise_scene(scene, surface, max(16, frames * 8))
    return before, scene._motion_pulses.live_count(), average, max_frame


def _build_motion_audit_state(
    *,
    scenario_id: str,
    difficulty_mode: DifficultyMode | None,
    seed: int,
):
    state = create_new_game(
        "NEXUS TECH",
        "Nexus One",
        scenario_id=scenario_id,
        difficulty_mode=difficulty_mode,
    )
    state.action_points_remaining = 20
    product_id = state.products[0].id
    for action, context in (
        (TurnAction.SOURCE_CANDIDATES, ActionContext()),
        (TurnAction.CREATE_SALES_DEAL, ActionContext(target_product_id=product_id)),
        (
            TurnAction.PLAN_RELEASE,
            ActionContext(
                target_product_id=product_id,
                release_type=ProductReleaseType.MINOR_RELEASE,
            ),
        ),
        (
            TurnAction.START_ROADMAP_PROJECT,
            ActionContext(
                target_product_id=product_id,
                roadmap_project_type=RoadmapProjectType.PLATFORM_REBUILD,
            ),
        ),
        (TurnAction.IMPROVE_QUALITY, ActionContext(target_product_id=product_id)),
    ):
        state = apply_action(state, action, context=context).state
    for offset in range(2):
        state = resolve_turn(state, RandomSource(seed=seed + offset)).state
        state.action_points_remaining = 20
    return state


def _seed_dense_run_pulses(scene) -> None:
    scene._motion_pulses.trigger("feed", intensity=0.8, decay=1.8)
    scene._motion_pulses.trigger("overlay:inspector", intensity=0.72, decay=1.8)
    scene._motion_pulses.trigger("panel:endgame", intensity=0.7, decay=1.8)
    for index in range(28):
        scene._motion_pulses.trigger(f"audit:run:{index}", intensity=0.12, decay=1.8)


def _seed_dense_summary_pulses(scene) -> None:
    scene._motion_pulses.trigger("summary:timeline", intensity=0.76, decay=1.8)
    scene._motion_pulses.trigger("summary:metrics", intensity=0.68, decay=1.8)
    scene._motion_pulses.trigger("panel:endgame", intensity=0.55, decay=1.8)
    for index in range(24):
        scene._motion_pulses.trigger(f"audit:summary:{index}", intensity=0.12, decay=1.8)
