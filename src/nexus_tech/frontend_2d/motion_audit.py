"""Deterministic 2D motion pressure audit helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from time import perf_counter

from nexus_tech.domain.models import (
    DifficultyMode,
    ProductReleaseType,
    RoadmapProjectType,
    TurnAction,
)
from nexus_tech.frontend_2d.app import Frontend2DUnavailableError
from nexus_tech.simulation.engine import ActionContext, apply_action, create_new_game, resolve_turn
from nexus_tech.simulation.randomness import RandomSource

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
    average_frame_ms: float

    @property
    def status(self) -> str:
        """Classify whether the viewport stayed within motion stability budgets."""

        if (
            self.run_after_pulses <= 18
            and self.summary_after_pulses <= 12
            and self.average_frame_ms <= 24.0
        ):
            return "pass"
        if (
            self.run_after_pulses <= 24
            and self.summary_after_pulses <= 18
            and self.average_frame_ms <= 33.0
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
        if self.average_frame_ms > 24.0:
            notes.append("frame budget above target")
        return "; ".join(notes) if notes else "stable"


@dataclass(frozen=True)
class MotionAuditReport:
    """Complete deterministic 2D motion audit result."""

    scenario_id: str
    difficulty: str
    seed: int
    frames: int
    cells: tuple[MotionAuditCell, ...]

    @property
    def status(self) -> str:
        """Return the worst status across all viewport cells."""

        statuses = {cell.status for cell in self.cells}
        if "fail" in statuses:
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
) -> MotionAuditReport:
    """Run a deterministic headless 2D motion stability audit."""

    if frames < 1:
        raise ValueError("frames must be at least 1")

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    try:
        import pygame
    except ModuleNotFoundError as error:
        raise Frontend2DUnavailableError(
            "pygame-ce is not installed. Install the optional 2D runtime first."
        ) from error

    from nexus_tech.frontend_2d.scenes import RunScene, TurnSummaryScene
    from nexus_tech.frontend_2d.widgets import create_fonts

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
            )
            run_scene._set_deep_panel("endgame")
            run_scene._open_inspector("endgame")
            _seed_dense_run_pulses(run_scene)
            run_before = run_scene._motion_pulses.live_count()
            frame_start = perf_counter()
            for _index in range(frames):
                run_scene.update(1 / 60)
                run_scene.draw(surface)
            run_elapsed = perf_counter() - frame_start

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
            )
            _seed_dense_summary_pulses(summary_scene)
            summary_before = summary_scene._motion_pulses.live_count()
            summary_start = perf_counter()
            for _index in range(frames):
                summary_scene.update(1 / 60)
                summary_scene.draw(surface)
            summary_elapsed = perf_counter() - summary_start
            average_frame_ms = ((run_elapsed + summary_elapsed) / (frames * 2)) * 1000
            cells.append(
                MotionAuditCell(
                    width=width,
                    height=height,
                    run_before_pulses=run_before,
                    run_after_pulses=run_scene._motion_pulses.live_count(),
                    summary_before_pulses=summary_before,
                    summary_after_pulses=summary_scene._motion_pulses.live_count(),
                    average_frame_ms=round(average_frame_ms, 2),
                )
            )
        return MotionAuditReport(
            scenario_id=scenario_id,
            difficulty=difficulty_mode.value if difficulty_mode is not None else "scenario",
            seed=seed,
            frames=frames,
            cells=tuple(cells),
        )
    finally:
        pygame.quit()


run_motion_audit = run_2d_motion_audit


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
