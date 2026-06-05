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
    ProductReleaseType,
    RoadmapProjectType,
    TurnAction,
)
from nexus_tech.frontend_2d.app import Frontend2DUnavailableError
from nexus_tech.frontend_2d.context import ActionRequest
from nexus_tech.frontend_2d.tween import MotionMode, normalize_motion_mode
from nexus_tech.frontend_2d.viewmodels import build_run_review_view_model
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
    (1280, 720),
)
MIN_UNIQUE_COLOR_SAMPLES = 18
MIN_LUMINANCE_SPREAD = 28
MIN_NON_DARK_RATIO = 0.05


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
        if self.non_dark_ratio < MIN_NON_DARK_RATIO:
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
        if self.non_dark_ratio < MIN_NON_DARK_RATIO:
            notes.append("mostly dark")
        return "; ".join(notes)


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
                            ("transition", "motion-pulses"),
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
                            ("transition", "motion-pulses"),
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
                            ("transition", "motion-pulses"),
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
                            ("transition", "motion-pulses"),
                            motion_mode=motion_mode,
                        ),
                        output_dir=output_dir,
                    )
                )
        return VisualAuditReport(
            scenario_id=scenario_id,
            difficulty=difficulty_mode.value if difficulty_mode is not None else "scenario",
            seed=seed,
            motion_mode=motion_mode.value,
            cells=tuple(cells),
            output_dir=output_dir_text,
        )
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
    for _index in range(2):
        scene.update(1 / 60)
    scene.draw(surface)
    width, height = surface.get_size()
    active_layers = _active_layers(scene)
    raw = pygame.image.tobytes(surface, "RGB")
    checksum = zlib.adler32(raw)
    unique_color_samples, luminance_spread, non_dark_ratio = _sample_frame_metrics(
        raw, width, height
    )
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
        output_path=str(output_path) if output_path is not None else None,
    )


def _sample_frame_metrics(raw: bytes, width: int, height: int) -> tuple[int, int, float]:
    pixel_count = width * height
    stride = max(1, pixel_count // 3200)
    unique_colors: set[bytes] = set()
    min_luminance = 255
    max_luminance = 0
    non_dark = 0
    sample_count = 0
    for pixel_index in range(0, pixel_count, stride):
        offset = pixel_index * 3
        red = raw[offset]
        green = raw[offset + 1]
        blue = raw[offset + 2]
        unique_colors.add(raw[offset : offset + 3])
        luminance = int(red * 0.2126 + green * 0.7152 + blue * 0.0722)
        min_luminance = min(min_luminance, luminance)
        max_luminance = max(max_luminance, luminance)
        if luminance > 32:
            non_dark += 1
        sample_count += 1
    return (
        len(unique_colors),
        max_luminance - min_luminance,
        non_dark / max(1, sample_count),
    )


def _active_layers(scene) -> tuple[str, ...]:
    layers: list[str] = []
    if scene.scene_transition_active():
        layers.append("transition")
    motion_bank = getattr(scene, "_motion_pulses", None)
    if motion_bank is not None and motion_bank.live_count() > 0:
        layers.append("motion-pulses")
    if getattr(scene, "_deep_panel_key", None) is not None:
        layers.append("deep-panel")
    if getattr(scene, "_context_picker", None) is not None:
        layers.append("picker")
    if getattr(scene, "_inspector_panel_key", None) is not None:
        layers.append("inspector")
    if getattr(scene, "_action_feedback_cues", ()):
        layers.append("action-feedback")
    if getattr(scene, "_impact_cues", ()):
        layers.append("impact-cue")
    if getattr(scene, "overlay_transition_active", lambda: False)():
        layers.append("overlay-transition")
    if getattr(scene, "_visible_event_count", 0) > 0:
        layers.append("summary-reveal")
    if getattr(scene, "summary_cinematic_active", lambda: False)():
        layers.append("summary-cinematic")
    return tuple(layers)


def _expected_layers(layers: tuple[str, ...], *, motion_mode: MotionMode) -> tuple[str, ...]:
    if motion_mode is not MotionMode.OFF:
        return layers
    disabled_layers = {
        "transition",
        "motion-pulses",
        "action-feedback",
        "impact-cue",
        "overlay-transition",
        "summary-cinematic",
    }
    return tuple(layer for layer in layers if layer not in disabled_layers)


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
