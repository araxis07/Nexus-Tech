"""Deterministic visual QA captures for the 2D frontend."""

from __future__ import annotations

import os
import zlib
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from nexus_tech.domain.models import (
    DifficultyMode,
    EventCategory,
    EventOption,
    PendingEvent,
    ProductReleaseType,
    RoadmapProjectType,
    TurnAction,
)
from nexus_tech.frontend_2d.app import Frontend2DUnavailableError
from nexus_tech.frontend_2d.context import ActionRequest
from nexus_tech.frontend_2d.tween import MotionMode, normalize_motion_mode
from nexus_tech.frontend_2d.viewmodels import build_run_review_view_model
from nexus_tech.frontend_2d.widgets import finish_typography_audit, start_typography_audit
from nexus_tech.persistence.save_coordinator import SaveLoadCoordinator
from nexus_tech.simulation.engine import (
    ActionContext,
    apply_action,
    create_new_game,
    resolve_turn,
)
from nexus_tech.simulation.randomness import RandomSource

DEFAULT_VISUAL_AUDIT_SIZES: tuple[tuple[int, int], ...] = (
    (820, 620),
    (960, 640),
    (1280, 720),
    (1440, 900),
)
MIN_UNIQUE_COLOR_SAMPLES = 18
MIN_LUMINANCE_SPREAD = 28
MIN_NON_DARK_RATIO = 0.05
MAX_EDGE_DENSITY = 0.72
MAX_BRIGHT_RATIO = 0.42
VISUAL_AUDIT_SUMMARY_NAME = "visual-audit-summary.md"
VISUAL_AUDIT_CONTACT_SHEET_PREFIX = "visual-audit-contact-sheet"
MIN_CLICK_TARGET_WIDTH = 28
MIN_CLICK_TARGET_HEIGHT = 24

_CONTROL_TARGET_LAYER_GROUPS: tuple[tuple[str, frozenset[str]], ...] = (
    ("pause-control", frozenset({"pause_toggle", "pause_resume"})),
    (
        "back-control",
        frozenset(
            {
                "run_back",
                "review_primary",
                "wizard_back",
                "close_help",
                "close_picker",
                "close_panel",
                "close_inspector",
                "close_outcome",
                "close_summary",
                "cancel_text",
                "cancel_delete",
            }
        ),
    ),
    ("help-control", frozenset({"open_help", "close_help"})),
    ("save-control", frozenset({"save", "pause_save", "review_save"})),
    ("flow-control", frozenset({"continue", "open_review", "close_outcome", "close_summary"})),
)
_CRITICAL_TARGET_OVERLAP_GROUPS = (
    frozenset({"pause_toggle", "run_back", "open_help"}),
    frozenset({"pause_resume", "pause_save", "pause_menu", "pause_quit"}),
    frozenset({"open_review", "save", "close_outcome"}),
    frozenset({"continue", "save", "close_summary"}),
    frozenset({"review_primary", "review_save"}),
    frozenset({"wizard_launch", "wizard_back"}),
    frozenset({"open_panel_inspector", "close_panel"}),
    frozenset(
        {
            "close_inspector",
            "inspector_cycle_sort",
            "inspector_cycle_filter",
            "inspector_focus_actionable",
            "inspector_focus_hotspot",
            "inspector_prev_page",
            "inspector_next_page",
        }
    ),
    frozenset(
        {
            "submit_text",
            "cancel_text",
            "confirm_delete",
            "cancel_delete",
            "close_help",
            "close_picker",
        }
    ),
)


@dataclass(frozen=True)
class VisualAuditCell:
    """One captured 2D scene frame and its visual-health metrics."""

    scene_key: str
    width: int
    height: int
    checksum: int
    unique_color_samples: int
    luminance_spread: int
    non_dark_ratio: float
    active_layers: tuple[str, ...]
    expected_layers: tuple[str, ...]
    edge_density: float = 0.0
    bright_ratio: float = 0.0
    layout_violations: tuple[str, ...] = ()
    click_target_count: int = 0
    min_click_target_size: tuple[int, int] = (0, 0)
    typography_violations: tuple[str, ...] = ()
    text_fit_count: int = 0
    wrapped_clamp_count: int = 0
    min_text_fit_ratio: float = 1.0
    output_path: str | None = None

    @property
    def missing_layers(self) -> tuple[str, ...]:
        """Return expected scene layers that were not active in the capture."""

        return tuple(layer for layer in self.expected_layers if layer not in self.active_layers)

    @property
    def status(self) -> str:
        """Return pass when the frame is non-empty and expected layers are visible."""

        if self.missing_layers:
            return "fail"
        if self.unique_color_samples < MIN_UNIQUE_COLOR_SAMPLES:
            return "fail"
        if self.luminance_spread < MIN_LUMINANCE_SPREAD:
            return "fail"
        if self.non_dark_ratio < self.minimum_non_dark_ratio:
            return "fail"
        if self.edge_density > MAX_EDGE_DENSITY:
            return "fail"
        if self.bright_ratio > MAX_BRIGHT_RATIO:
            return "fail"
        if self.layout_violations:
            return "fail"
        if self.typography_violations:
            return "fail"
        return "pass"

    @property
    def notes(self) -> str:
        """Return a compact note for CLI output."""

        if self.status == "pass":
            return "captured"
        notes: list[str] = []
        if self.missing_layers:
            notes.append(f"missing {','.join(self.missing_layers)}")
        if self.unique_color_samples < MIN_UNIQUE_COLOR_SAMPLES:
            notes.append("low color variance")
        if self.luminance_spread < MIN_LUMINANCE_SPREAD:
            notes.append("low contrast")
        if self.non_dark_ratio < self.minimum_non_dark_ratio:
            notes.append("mostly dark")
        if self.edge_density > MAX_EDGE_DENSITY:
            notes.append("visual clutter")
        if self.bright_ratio > MAX_BRIGHT_RATIO:
            notes.append("high flash pressure")
        if self.layout_violations:
            notes.append(f"layout {','.join(self.layout_violations[:3])}")
        if self.typography_violations:
            notes.append(f"typography {','.join(self.typography_violations[:3])}")
        return "; ".join(notes)

    @property
    def minimum_non_dark_ratio(self) -> float:
        """Use a lower fill threshold for large presentation windows with intentional margins."""

        if self.width >= 1280 and self.height >= 800:
            return 0.02
        return MIN_NON_DARK_RATIO


@dataclass(frozen=True)
class VisualAuditReport:
    """A deterministic visual QA capture report for core 2D surfaces."""

    scenario_id: str
    difficulty: str
    seed: int
    motion_mode: str
    cells: tuple[VisualAuditCell, ...]
    output_dir: str | None = None

    @property
    def status(self) -> str:
        """Return pass only when every captured surface passes visual checks."""

        return "pass" if all(cell.status == "pass" for cell in self.cells) else "fail"

    @property
    def baseline_signature(self) -> str:
        """Return a stable compact signature for the captured visual baseline."""

        digest = 1
        for cell in sorted(self.cells, key=lambda item: (item.scene_key, item.width, item.height)):
            payload = (
                f"{cell.scene_key}:{cell.width}x{cell.height}:"
                f"{cell.checksum}:{cell.unique_color_samples}:"
                f"{cell.luminance_spread}:{cell.non_dark_ratio}:"
                f"{cell.edge_density}:{cell.bright_ratio}:"
                f"{cell.click_target_count}:{cell.min_click_target_size}:"
                f"{','.join(cell.layout_violations)}:"
                f"{cell.text_fit_count}:{cell.wrapped_clamp_count}:"
                f"{cell.min_text_fit_ratio}:{','.join(cell.typography_violations)}"
            )
            digest = zlib.adler32(payload.encode("utf-8"), digest)
        return f"{len(self.cells)}:{digest:08x}"


def run_2d_visual_audit(
    *,
    scenario_id: str,
    difficulty_mode: DifficultyMode | None,
    seed: int,
    sizes: tuple[tuple[int, int], ...] = DEFAULT_VISUAL_AUDIT_SIZES,
    motion_mode: MotionMode | str = MotionMode.FULL,
    output_dir: Path | None = None,
) -> VisualAuditReport:
    """Render deterministic 2D scene snapshots and verify expected motion layers."""

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
        state = _build_visual_audit_state(
            scenario_id=scenario_id,
            difficulty_mode=difficulty_mode,
            seed=seed,
        )
        previous_state = state.model_copy(deep=True)
        resolution = resolve_turn(state, RandomSource(seed=seed + 17))
        cells: list[VisualAuditCell] = []
        output_dir_text = str(output_dir) if output_dir is not None else None
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix="nexus-tech-visual-audit-") as tmpdir:
            coordinator = SaveLoadCoordinator(Path(tmpdir) / "visual-audit.db")
            for width, height in sizes:
                surface = pygame.display.set_mode((width, height), pygame.HIDDEN)
                title_menu = TitleScene(
                    pygame=pygame,
                    fonts=fonts,
                    state=create_new_game("NEXUS TECH", "Nexus One"),
                    rng=RandomSource(seed=seed),
                    slot_name="visual-audit",
                    save_callback=lambda *_args: None,
                    coordinator=coordinator,
                    initial_mode="menu",
                    motion_mode=motion_mode,
                    entry_transition="boot_title",
                )
                cells.append(
                    _capture_visual_cell(
                        pygame,
                        surface,
                        title_menu,
                        scene_key="title_menu",
                        expected_layers=_expected_layers(
                            (
                                "transition",
                                "motion-pulses",
                                "actor-timeline",
                                "sprite-clips",
                                "title-actor",
                            ),
                            motion_mode=motion_mode,
                        ),
                        output_dir=output_dir,
                    )
                )

                title_meta = TitleScene(
                    pygame=pygame,
                    fonts=fonts,
                    state=create_new_game("NEXUS TECH", "Nexus One"),
                    rng=RandomSource(seed=seed + 1),
                    slot_name="visual-audit",
                    save_callback=lambda *_args: None,
                    coordinator=coordinator,
                    initial_mode="meta",
                    motion_mode=motion_mode,
                    entry_transition="boot_title",
                )
                cells.append(
                    _capture_visual_cell(
                        pygame,
                        surface,
                        title_meta,
                        scene_key="title_meta",
                        expected_layers=_expected_layers(
                            (
                                "transition",
                                "motion-pulses",
                                "actor-timeline",
                                "sprite-clips",
                                "title-actor",
                                "archive-comparison",
                            ),
                            motion_mode=motion_mode,
                        ),
                        output_dir=output_dir,
                    )
                )

                run_scene = RunScene(
                    pygame=pygame,
                    fonts=fonts,
                    state=state.model_copy(deep=True),
                    rng=RandomSource(seed=seed + 2),
                    slot_name="visual-audit",
                    save_callback=lambda *_args: None,
                    show_ready_event=True,
                    motion_mode=motion_mode,
                    entry_transition="boot_run",
                )
                cells.append(
                    _capture_visual_cell(
                        pygame,
                        surface,
                        run_scene,
                        scene_key="run_dashboard",
                        expected_layers=_expected_layers(
                            (
                                "transition",
                                "motion-pulses",
                                "product-drama",
                                "actor-timeline",
                                "sprite-clips",
                            ),
                            motion_mode=motion_mode,
                        ),
                        output_dir=output_dir,
                    )
                )

                drama_state = state.model_copy(deep=True)
                drama_state.company.cash_on_hand = Decimal("900.00")
                drama_state.finance.board_pressure = 72
                drama_state.products[0].quality = 84
                drama_state.products[0].bug_level = 66
                drama_state.products[0].market_fit = 78
                drama_state.products[0].technical_debt = 74
                drama_state.products[0].user_count = max(
                    drama_state.products[0].user_count,
                    180,
                )
                drama_scene = RunScene(
                    pygame=pygame,
                    fonts=fonts,
                    state=drama_state,
                    rng=RandomSource(seed=seed + 8),
                    slot_name="visual-audit",
                    save_callback=lambda *_args: None,
                    show_ready_event=False,
                    motion_mode=motion_mode,
                    entry_transition="boot_run",
                )
                drama_scene._motion_pulses.trigger("panel:products", intensity=0.6, decay=1.8)
                drama_scene._motion_pulses.trigger(
                    "stat:board_pressure",
                    intensity=0.58,
                    decay=1.8,
                )
                cells.append(
                    _capture_visual_cell(
                        pygame,
                        surface,
                        drama_scene,
                        scene_key="run_drama_feedback",
                        expected_layers=_expected_layers(
                            (
                                "transition",
                                "motion-pulses",
                                "product-drama",
                                "risk-drama",
                            ),
                            motion_mode=motion_mode,
                        ),
                        output_dir=output_dir,
                    )
                )

                pending_state = state.model_copy(deep=True)
                pending_state.pending_event = _build_audit_pending_event(
                    pending_state.company.current_turn
                )
                pending_scene = RunScene(
                    pygame=pygame,
                    fonts=fonts,
                    state=pending_state,
                    rng=RandomSource(seed=seed + 10),
                    slot_name="visual-audit",
                    save_callback=lambda *_args: None,
                    show_ready_event=False,
                    motion_mode=motion_mode,
                    entry_transition="boot_run",
                )
                cells.append(
                    _capture_visual_cell(
                        pygame,
                        surface,
                        pending_scene,
                        scene_key="run_pending_feedback",
                        expected_layers=_expected_layers(
                            (
                                "transition",
                                "motion-pulses",
                                "overlay-transition",
                                "pending",
                                "pending-choice-preview",
                            ),
                            motion_mode=motion_mode,
                        ),
                        output_dir=output_dir,
                    )
                )

                impact_scene = RunScene(
                    pygame=pygame,
                    fonts=fonts,
                    state=state.model_copy(deep=True),
                    rng=RandomSource(seed=seed + 6),
                    slot_name="visual-audit",
                    save_callback=lambda *_args: None,
                    show_ready_event=False,
                    motion_mode=motion_mode,
                    entry_transition="boot_run",
                )
                impact_scene._apply_action_request(
                    ActionRequest(
                        action=TurnAction.IMPROVE_QUALITY,
                        context=ActionContext(target_product_id=impact_scene.selected_product.id),
                        label=TurnAction.IMPROVE_QUALITY.value,
                    )
                )
                cells.append(
                    _capture_visual_cell(
                        pygame,
                        surface,
                        impact_scene,
                        scene_key="run_impact_feedback",
                        expected_layers=_expected_layers(
                            (
                                "transition",
                                "motion-pulses",
                                "impact-cue",
                                "action-feedback",
                            ),
                            motion_mode=motion_mode,
                        ),
                        output_dir=output_dir,
                    )
                )

                blocked_state = state.model_copy(deep=True)
                blocked_state.employees = []
                blocked_scene = RunScene(
                    pygame=pygame,
                    fonts=fonts,
                    state=blocked_state,
                    rng=RandomSource(seed=seed + 13),
                    slot_name="visual-audit",
                    save_callback=lambda *_args: None,
                    show_ready_event=False,
                    motion_mode=motion_mode,
                    entry_transition="boot_run",
                )
                blocked_scene._run_command(TurnAction.PROMOTE_EMPLOYEE.value)
                cells.append(
                    _capture_visual_cell(
                        pygame,
                        surface,
                        blocked_scene,
                        scene_key="run_blocked_feedback",
                        expected_layers=_expected_layers(
                            (
                                "transition",
                                "motion-pulses",
                                "action-feedback",
                                "blocked-action-feedback",
                            ),
                            motion_mode=motion_mode,
                        ),
                        output_dir=output_dir,
                    )
                )

                picker_scene = RunScene(
                    pygame=pygame,
                    fonts=fonts,
                    state=state.model_copy(deep=True),
                    rng=RandomSource(seed=seed + 3),
                    slot_name="visual-audit",
                    save_callback=lambda *_args: None,
                    show_ready_event=False,
                    motion_mode=motion_mode,
                    entry_transition="boot_run",
                )
                picker_scene._run_command(TurnAction.SET_CAPITAL_PLAN.value)
                cells.append(
                    _capture_visual_cell(
                        pygame,
                        surface,
                        picker_scene,
                        scene_key="run_picker_feedback",
                        expected_layers=_expected_layers(
                            (
                                "transition",
                                "motion-pulses",
                                "overlay-transition",
                                "deep-panel",
                                "picker",
                                "action-feedback",
                                "late-game-choreography",
                            ),
                            motion_mode=motion_mode,
                        ),
                        output_dir=output_dir,
                    )
                )

                inspector_scene = RunScene(
                    pygame=pygame,
                    fonts=fonts,
                    state=state.model_copy(deep=True),
                    rng=RandomSource(seed=seed + 4),
                    slot_name="visual-audit",
                    save_callback=lambda *_args: None,
                    show_ready_event=False,
                    motion_mode=motion_mode,
                    entry_transition="boot_run",
                )
                inspector_scene._set_deep_panel("pipeline")
                inspector_scene._open_inspector("pipeline")
                cells.append(
                    _capture_visual_cell(
                        pygame,
                        surface,
                        inspector_scene,
                        scene_key="run_inspector",
                        expected_layers=_expected_layers(
                            (
                                "transition",
                                "motion-pulses",
                                "overlay-transition",
                                "deep-panel",
                                "inspector",
                                "action-feedback",
                                "actor-timeline",
                                "sprite-clips",
                                "inspector-actor",
                            ),
                            motion_mode=motion_mode,
                        ),
                        output_dir=output_dir,
                    )
                )

                endgame_scene = RunScene(
                    pygame=pygame,
                    fonts=fonts,
                    state=state.model_copy(deep=True),
                    rng=RandomSource(seed=seed + 12),
                    slot_name="visual-audit",
                    save_callback=lambda *_args: None,
                    show_ready_event=False,
                    motion_mode=motion_mode,
                    entry_transition="boot_run",
                )
                endgame_scene._set_deep_panel("endgame")
                cells.append(
                    _capture_visual_cell(
                        pygame,
                        surface,
                        endgame_scene,
                        scene_key="run_endgame_board",
                        expected_layers=_expected_layers(
                            (
                                "transition",
                                "motion-pulses",
                                "overlay-transition",
                                "deep-panel",
                                "actor-timeline",
                                "sprite-clips",
                                "endgame-actor",
                            ),
                            motion_mode=motion_mode,
                        ),
                        output_dir=output_dir,
                    )
                )

                outcome_state = resolution.state.model_copy(deep=True)
                outcome_state.pending_event = None
                outcome_state.company.game_over = True
                outcome_state.company.cash_on_hand = Decimal("-125.00")
                outcome_scene = RunScene(
                    pygame=pygame,
                    fonts=fonts,
                    state=outcome_state,
                    rng=RandomSource(seed=seed + 11),
                    slot_name="visual-audit",
                    save_callback=lambda *_args: None,
                    show_ready_event=False,
                    motion_mode=motion_mode,
                    entry_transition="run_to_review",
                )
                cells.append(
                    _capture_visual_cell(
                        pygame,
                        surface,
                        outcome_scene,
                        scene_key="run_outcome_overlay",
                        expected_layers=_expected_layers(
                            (
                                "transition",
                                "motion-pulses",
                                "overlay-transition",
                                "outcome",
                                "outcome-cinematic",
                            ),
                            motion_mode=motion_mode,
                        ),
                        output_dir=output_dir,
                    )
                )

                summary_scene = TurnSummaryScene(
                    pygame=pygame,
                    fonts=fonts,
                    state=resolution.state,
                    rng=RandomSource(seed=seed + 17),
                    slot_name="visual-audit",
                    save_callback=lambda *_args: None,
                    previous_state=previous_state,
                    resolution=resolution,
                    selected_product_id=resolution.state.products[0].id.hex,
                    dirty=True,
                    motion_mode=motion_mode,
                    entry_transition="run_to_summary",
                )
                cells.append(
                    _capture_visual_cell(
                        pygame,
                        surface,
                        summary_scene,
                        scene_key="turn_summary",
                        expected_layers=_expected_layers(
                            (
                                "transition",
                                "motion-pulses",
                                "summary-reveal",
                                "summary-cinematic",
                                "summary-sequence",
                                "summary-lanes",
                                "actor-timeline",
                                "sprite-clips",
                            ),
                            motion_mode=motion_mode,
                        ),
                        output_dir=output_dir,
                    )
                )

                review_state = resolution.state.model_copy(deep=True)
                review_state.company.game_over = True
                review_state.company.cash_on_hand = Decimal("-125.00")
                review_scene = ReviewScene(
                    pygame=pygame,
                    fonts=fonts,
                    state=review_state,
                    rng=RandomSource(seed=seed + 5),
                    slot_name="visual-audit",
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
                cells.append(
                    _capture_visual_cell(
                        pygame,
                        surface,
                        review_scene,
                        scene_key="review",
                        expected_layers=_expected_layers(
                            (
                                "transition",
                                "motion-pulses",
                                "actor-timeline",
                                "sprite-clips",
                                "review-actor",
                            ),
                            motion_mode=motion_mode,
                        ),
                        output_dir=output_dir,
                    )
                )
        report = VisualAuditReport(
            scenario_id=scenario_id,
            difficulty=difficulty_mode.value if difficulty_mode is not None else "scenario",
            seed=seed,
            motion_mode=motion_mode.value,
            cells=tuple(cells),
            output_dir=output_dir_text,
        )
        if output_dir is not None:
            _write_visual_audit_contact_sheets(pygame, report, output_dir)
            _write_visual_audit_summary(report, output_dir)
        return report
    finally:
        pygame.quit()


def _capture_visual_cell(
    pygame,
    surface,
    scene,
    *,
    scene_key: str,
    expected_layers: tuple[str, ...],
    output_dir: Path | None,
) -> VisualAuditCell:
    width, height = surface.get_size()
    _set_visual_audit_mouse_safe_point(pygame, width, height)
    for _index in range(2):
        scene.update(1 / 60)
    start_typography_audit()
    try:
        scene.draw(surface)
        typography_events = finish_typography_audit()
    except Exception:
        finish_typography_audit()
        raise
    active_layers = _active_layers(scene)
    layout_violations, click_target_count, min_click_target_size = _layout_safety_metrics(
        scene,
        width,
        height,
    )
    (
        typography_violations,
        text_fit_count,
        wrapped_clamp_count,
        min_text_fit_ratio,
    ) = _typography_safety_metrics(typography_events)
    raw = pygame.image.tobytes(surface, "RGB")
    checksum = zlib.adler32(raw)
    (
        unique_color_samples,
        luminance_spread,
        non_dark_ratio,
        edge_density,
        bright_ratio,
    ) = _sample_frame_metrics(raw, width, height)
    output_path = None
    if output_dir is not None:
        output_path = output_dir / f"{scene_key}_{width}x{height}.png"
        pygame.image.save(surface, output_path)
    return VisualAuditCell(
        scene_key=scene_key,
        width=width,
        height=height,
        checksum=checksum,
        unique_color_samples=unique_color_samples,
        luminance_spread=luminance_spread,
        non_dark_ratio=round(non_dark_ratio, 4),
        active_layers=active_layers,
        expected_layers=expected_layers,
        edge_density=round(edge_density, 4),
        bright_ratio=round(bright_ratio, 4),
        layout_violations=layout_violations,
        click_target_count=click_target_count,
        min_click_target_size=min_click_target_size,
        typography_violations=typography_violations,
        text_fit_count=text_fit_count,
        wrapped_clamp_count=wrapped_clamp_count,
        min_text_fit_ratio=min_text_fit_ratio,
        output_path=str(output_path) if output_path is not None else None,
    )


def _typography_safety_metrics(events) -> tuple[tuple[str, ...], int, int, float]:
    text_fit_events = tuple(event for event in events if event.kind.endswith("-fit"))
    wrapped_clamp_events = tuple(event for event in events if event.kind == "wrapped-clamp")
    ratios = tuple(event.ratio for event in events if event.kind != "wrapped-clamp")
    min_ratio = round(min(ratios), 3) if ratios else 1.0
    violations = tuple(
        sorted({f"{event.kind}:{event.ratio:.2f}" for event in events if event.severe})
    )
    return violations, len(text_fit_events), len(wrapped_clamp_events), min_ratio


def _layout_safety_metrics(
    scene, width: int, height: int
) -> tuple[tuple[str, ...], int, tuple[int, int]]:
    targets = tuple(getattr(scene, "_click_targets", ()))
    violations: list[str] = []
    min_width = 0
    min_height = 0

    for target in targets:
        rect = getattr(target, "rect", None)
        kind = getattr(target, "kind", "target")
        if rect is None:
            violations.append(f"target-missing-rect:{kind}")
            continue
        target_width = int(getattr(rect, "width", 0))
        target_height = int(getattr(rect, "height", 0))
        min_width = target_width if min_width == 0 else min(min_width, target_width)
        min_height = target_height if min_height == 0 else min(min_height, target_height)
        if target_width < MIN_CLICK_TARGET_WIDTH or target_height < MIN_CLICK_TARGET_HEIGHT:
            violations.append(f"target-too-small:{kind}:{target_width}x{target_height}")
        if (
            int(getattr(rect, "left", 0)) < 0
            or int(getattr(rect, "top", 0)) < 0
            or int(getattr(rect, "right", 0)) > width
            or int(getattr(rect, "bottom", 0)) > height
        ):
            violations.append(f"target-offscreen:{kind}")

    for index, first in enumerate(targets):
        first_rect = getattr(first, "rect", None)
        first_kind = getattr(first, "kind", "target")
        if first_rect is None:
            continue
        for second in targets[index + 1 :]:
            second_rect = getattr(second, "rect", None)
            second_kind = getattr(second, "kind", "target")
            if second_rect is None or not _should_check_target_overlap(first_kind, second_kind):
                continue
            if _rects_overlap(first_rect, second_rect):
                violations.append(f"target-overlap:{first_kind}:{second_kind}")

    actor_layout_violations = getattr(scene, "actor_sprite_layout_violations", None)
    if callable(actor_layout_violations):
        violations.extend(f"actor:{violation}" for violation in actor_layout_violations())

    return tuple(sorted(set(violations))), len(targets), (min_width, min_height)


def _should_check_target_overlap(first_kind: str, second_kind: str) -> bool:
    if first_kind == second_kind:
        return True
    return any(
        first_kind in overlap_group and second_kind in overlap_group
        for overlap_group in _CRITICAL_TARGET_OVERLAP_GROUPS
    )


def _rects_overlap(first_rect, second_rect) -> bool:
    return max(int(getattr(first_rect, "left", 0)), int(getattr(second_rect, "left", 0))) < min(
        int(getattr(first_rect, "right", 0)), int(getattr(second_rect, "right", 0))
    ) and max(int(getattr(first_rect, "top", 0)), int(getattr(second_rect, "top", 0))) < min(
        int(getattr(first_rect, "bottom", 0)), int(getattr(second_rect, "bottom", 0))
    )


def _set_visual_audit_mouse_safe_point(pygame, width: int, height: int) -> None:
    pygame_error = getattr(pygame, "error", RuntimeError)
    try:
        pygame.mouse.set_pos((max(0, width - 1), max(0, height - 1)))
    except (AttributeError, pygame_error):
        return


def _sample_frame_metrics(
    raw: bytes,
    width: int,
    height: int,
) -> tuple[int, int, float, float, float]:
    pixel_count = width * height
    step = max(1, int((pixel_count / 3200) ** 0.5))
    unique_colors: set[bytes] = set()
    min_luminance = 255
    max_luminance = 0
    non_dark = 0
    bright = 0
    sample_count = 0
    edge_changes = 0
    edge_checks = 0

    def luminance_at(x: int, y: int) -> int:
        offset = (y * width + x) * 3
        return int(raw[offset] * 0.2126 + raw[offset + 1] * 0.7152 + raw[offset + 2] * 0.0722)

    for y in range(0, height, step):
        for x in range(0, width, step):
            offset = (y * width + x) * 3
            red = raw[offset]
            green = raw[offset + 1]
            blue = raw[offset + 2]
            unique_colors.add(raw[offset : offset + 3])
            luminance = int(red * 0.2126 + green * 0.7152 + blue * 0.0722)
            min_luminance = min(min_luminance, luminance)
            max_luminance = max(max_luminance, luminance)
            if luminance > 32:
                non_dark += 1
            if luminance >= 210:
                bright += 1
            next_x = x + step
            if next_x < width:
                edge_checks += 1
                if abs(luminance - luminance_at(next_x, y)) >= 32:
                    edge_changes += 1
            next_y = y + step
            if next_y < height:
                edge_checks += 1
                if abs(luminance - luminance_at(x, next_y)) >= 32:
                    edge_changes += 1
            sample_count += 1
    return (
        len(unique_colors),
        max_luminance - min_luminance,
        non_dark / max(1, sample_count),
        edge_changes / max(1, edge_checks),
        bright / max(1, sample_count),
    )


def _write_visual_audit_summary(report: VisualAuditReport, output_dir: Path) -> None:
    passed = sum(1 for cell in report.cells if cell.status == "pass")
    failed = len(report.cells) - passed
    max_edge_density = max((cell.edge_density for cell in report.cells), default=0.0)
    max_bright_ratio = max((cell.bright_ratio for cell in report.cells), default=0.0)
    lines = [
        "# NEXUS TECH 2D Visual Audit",
        "",
        f"- Scenario: `{report.scenario_id}`",
        f"- Difficulty: `{report.difficulty}`",
        f"- Seed: `{report.seed}`",
        f"- Motion mode: `{report.motion_mode}`",
        f"- Status: `{report.status}`",
        f"- Baseline: `{report.baseline_signature}`",
        f"- Captures: `{len(report.cells)}` total, `{passed}` pass, `{failed}` fail",
        f"- Max edge density: `{max_edge_density:.2f}`",
        f"- Max bright ratio: `{max_bright_ratio:.2f}`",
        "",
        "| Scene | Viewport | Status | Clutter | Bright | Capture | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for cell in report.cells:
        capture = Path(cell.output_path).name if cell.output_path is not None else "-"
        lines.append(
            "| "
            f"`{cell.scene_key}` | "
            f"`{cell.width}x{cell.height}` | "
            f"`{cell.status}` | "
            f"`{cell.edge_density:.2f}` | "
            f"`{cell.bright_ratio:.2f}` | "
            f"`{capture}` | "
            f"{cell.notes} |"
        )
    (output_dir / VISUAL_AUDIT_SUMMARY_NAME).write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def _write_visual_audit_contact_sheets(pygame, report: VisualAuditReport, output_dir: Path) -> None:
    """Create one compact visual-review sheet for each audited viewport."""

    grouped_cells: dict[tuple[int, int], list[VisualAuditCell]] = {}
    for cell in report.cells:
        if cell.output_path is not None:
            grouped_cells.setdefault((cell.width, cell.height), []).append(cell)

    for (width, height), cells in sorted(grouped_cells.items()):
        columns = min(3, len(cells))
        thumbnail_width = min(320, max(180, int(width * 0.3)))
        thumbnail_height = max(120, int(thumbnail_width * height / width))
        label_height = 28
        header_height = 40
        padding = 16
        gap = 12
        rows = (len(cells) + columns - 1) // columns
        sheet_width = padding * 2 + columns * thumbnail_width + (columns - 1) * gap
        sheet_height = (
            padding * 2
            + header_height
            + rows * (label_height + thumbnail_height)
            + (rows - 1) * gap
        )
        sheet = pygame.Surface((sheet_width, sheet_height))
        sheet.fill((8, 13, 22))
        title_font = pygame.font.Font(None, 26)
        label_font = pygame.font.Font(None, 18)
        title = title_font.render(
            f"NEXUS TECH visual QA | {width}x{height} | {report.motion_mode}",
            True,
            (222, 231, 241),
        )
        sheet.blit(title, (padding, padding + 8))

        for index, cell in enumerate(cells):
            source = pygame.image.load(cell.output_path).convert()
            thumbnail = pygame.transform.smoothscale(
                source,
                (thumbnail_width, thumbnail_height),
            )
            column = index % columns
            row = index // columns
            left = padding + column * (thumbnail_width + gap)
            top = padding + header_height + row * (label_height + thumbnail_height + gap)
            tile_rect = pygame.Rect(
                left - 1,
                top - 1,
                thumbnail_width + 2,
                label_height + thumbnail_height + 2,
            )
            pygame.draw.rect(sheet, (30, 56, 82), tile_rect, width=1, border_radius=4)
            label = label_font.render(cell.scene_key.replace("_", " "), True, (169, 190, 214))
            sheet.blit(label, (left + 6, top + 6))
            sheet.blit(thumbnail, (left, top + label_height))

        contact_sheet = output_dir / f"{VISUAL_AUDIT_CONTACT_SHEET_PREFIX}-{width}x{height}.png"
        pygame.image.save(sheet, contact_sheet)


def _active_layers(scene) -> tuple[str, ...]:
    layers: list[str] = []
    if scene.scene_transition_active():
        layers.append("transition")
        transition_key = getattr(scene, "scene_transition_key", "")
        if transition_key:
            layers.append(f"transition-key:{transition_key}")
    layers.extend(_control_affordance_layers(scene))
    motion_bank = getattr(scene, "_motion_pulses", None)
    if motion_bank is not None and motion_bank.live_count() > 0:
        layers.append("motion-pulses")
    if getattr(scene, "_deep_panel_key", None) is not None:
        layers.append("deep-panel")
    if getattr(scene, "_context_picker", None) is not None:
        layers.append("picker")
    if getattr(getattr(scene, "state", None), "pending_event", None) is not None:
        layers.append("pending")
    scene_state = getattr(scene, "state", None)
    if scene_state is not None and (scene_state.company.game_over or scene_state.victory_achieved):
        layers.append("outcome")
    if getattr(scene, "_inspector_panel_key", None) is not None:
        layers.append("inspector")
    if getattr(scene, "_action_feedback_cues", ()):
        layers.append("action-feedback")
        if any(cue.targets for cue in scene._action_feedback_cues):
            layers.append("action-feedback-targets")
        layers.extend(
            sorted({f"action-family:{cue.family}" for cue in scene._action_feedback_cues})
        )
        if any(cue.outcome == "blocked" for cue in scene._action_feedback_cues):
            layers.append("blocked-action-feedback")
        if any(cue.outcome == "blocked" and cue.detail for cue in scene._action_feedback_cues):
            layers.append("blocked-action-reason")
    if getattr(scene, "_impact_cues", ()):
        layers.append("impact-cue")
        if any(cue.targets for cue in scene._impact_cues):
            layers.append("impact-cue-targets")
        if any(cue.value_text for cue in scene._impact_cues):
            layers.append("impact-value-label")
    if getattr(scene, "overlay_transition_active", lambda: False)():
        layers.append("overlay-transition")
    if getattr(scene, "product_drama_active", lambda: False)():
        layers.append("product-drama")
    if getattr(scene, "risk_drama_active", lambda: False)():
        layers.append("risk-drama")
    if getattr(scene, "pending_choice_active", lambda: False)():
        layers.append("pending-choice")
    if getattr(scene, "outcome_cinematic_active", lambda: False)():
        layers.append("outcome-cinematic")
    if getattr(scene, "pending_choice_preview_active", lambda: False)():
        layers.append("pending-choice-preview")
    if getattr(scene, "late_game_choreography_active", lambda: False)():
        layers.append("late-game-choreography")
    if getattr(scene, "actor_timeline_active", lambda: False)():
        layers.append("actor-timeline")
        layers.extend(_actor_state_layers(scene))
        layers.extend(_actor_pose_layers(scene))
    if getattr(scene, "sprite_clips_active", lambda: False)():
        layers.append("sprite-clips")
    if getattr(scene, "title_actor_active", lambda: False)():
        layers.append("title-actor")
    if getattr(scene, "archive_comparison_active", lambda: False)():
        layers.append("archive-comparison")
    if getattr(scene, "inspector_actor_active", lambda: False)():
        layers.append("inspector-actor")
    if getattr(scene, "endgame_actor_active", lambda: False)():
        layers.append("endgame-actor")
    if getattr(scene, "review_actor_active", lambda: False)():
        layers.append("review-actor")
    if getattr(scene, "actor_readability_clear", lambda: False)():
        layers.append("actor-readability")
    if getattr(scene, "_visible_event_count", 0) > 0:
        layers.append("summary-reveal")
    if getattr(scene, "summary_cinematic_active", lambda: False)():
        layers.append("summary-cinematic")
    if getattr(scene, "summary_metric_sequence_active", lambda: False)():
        layers.append("summary-sequence")
    if getattr(scene, "summary_outcome_lanes_active", lambda: False)():
        layers.append("summary-lanes")
    return tuple(layers)


def _control_affordance_layers(scene) -> tuple[str, ...]:
    target_kinds = {
        kind
        for target in getattr(scene, "_click_targets", ())
        if isinstance((kind := getattr(target, "kind", "")), str) and kind
    }
    if not target_kinds:
        return ()

    layers = {"click-targets"}
    for layer, kinds in _CONTROL_TARGET_LAYER_GROUPS:
        if target_kinds & kinds:
            layers.add(layer)

    scene_name = scene.__class__.__name__
    if scene_name == "TitleScene" and target_kinds & {
        "archive",
        "menu",
        "slot",
        "slot_action",
        "wizard_back",
        "wizard_launch",
    }:
        layers.add("title-nav-controls")
    if scene_name == "RunScene" and {"pause_toggle", "run_back", "open_help"} <= target_kinds:
        layers.add("run-nav-controls")
    if scene_name == "RunScene" and {"open_review", "save", "close_outcome"} <= target_kinds:
        layers.add("outcome-nav-controls")
    if scene_name == "TurnSummaryScene" and {"continue", "save", "close_summary"} <= target_kinds:
        layers.add("summary-nav-controls")
    if scene_name == "ReviewScene" and "review_primary" in target_kinds:
        layers.add("review-nav-controls")

    return tuple(sorted(layers))


def _actor_state_layers(scene) -> tuple[str, ...]:
    states: set[str] = set()
    for clip in _iter_actor_sprite_clips(scene):
        states.add(f"actor-state:{clip.state}")
    return tuple(sorted(states))


def _actor_pose_layers(scene) -> tuple[str, ...]:
    poses: set[str] = set()
    for clip in _iter_actor_sprite_clips(scene):
        pose_key = getattr(clip, "pose_key", None)
        if isinstance(pose_key, str) and pose_key:
            poses.add(f"actor-pose:{pose_key}")
    if not poses:
        return ()
    return ("actor-pose-depth", *tuple(sorted(poses)))


def _iter_actor_sprite_clips(scene):
    for method_name in (
        "_title_actor_sprite_clips",
        "_run_actor_sprite_clips",
        "_inspector_actor_sprite_clips",
        "_endgame_actor_sprite_clips",
        "_review_actor_sprite_clips",
        "_summary_actor_sprite_clips",
    ):
        method = getattr(scene, method_name, None)
        if not callable(method):
            continue
        for clip in method():
            yield clip


def _expected_layers(layers: tuple[str, ...], *, motion_mode: MotionMode) -> tuple[str, ...]:
    if motion_mode is not MotionMode.OFF:
        return layers
    disabled_layers = {
        "transition",
        "motion-pulses",
        "action-feedback",
        "action-feedback-targets",
        "blocked-action-feedback",
        "blocked-action-reason",
        "impact-cue",
        "impact-cue-targets",
        "impact-value-label",
        "overlay-transition",
        "product-drama",
        "risk-drama",
        "pending-choice",
        "outcome-cinematic",
        "pending-choice-preview",
        "late-game-choreography",
        "summary-cinematic",
        "summary-sequence",
        "summary-lanes",
        "actor-timeline",
        "sprite-clips",
        "title-actor",
        "archive-comparison",
        "inspector-actor",
        "endgame-actor",
        "review-actor",
        "actor-readability",
        "actor-pose-depth",
    }
    return tuple(layer for layer in layers if layer not in disabled_layers)


def _build_audit_pending_event(turn: int) -> PendingEvent:
    return PendingEvent(
        event_id="visual_audit_pending_choice",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Audit Pending Choice",
        description=(
            "Choose a response path so pending-event preview motion has deterministic data."
        ),
        triggered_turn=turn,
        cooldown_turns=0,
        options=[
            EventOption(
                id="stabilize",
                label="Stabilize rollout",
                description="Protect quality and reduce launch risk before scaling.",
            ),
            EventOption(
                id="stretch",
                label="Stretch the plan",
                description="Accept pressure and cost risk to chase the upside now.",
            ),
        ],
    )


def _build_visual_audit_state(
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
    state.action_points_remaining = 18
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
    state.action_points_remaining = 18
    state = resolve_turn(state, RandomSource(seed=seed + 9)).state
    state.action_points_remaining = 18
    return state
