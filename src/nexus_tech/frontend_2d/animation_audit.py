"""High-level 2D animation completeness audit."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.domain.models import DifficultyMode
from nexus_tech.frontend_2d.motion_audit import (
    MotionAuditCell,
    MotionAuditReport,
    run_2d_motion_audit,
)
from nexus_tech.frontend_2d.tween import MotionMode
from nexus_tech.frontend_2d.visual_audit import (
    MAX_BRIGHT_RATIO,
    MAX_EDGE_DENSITY,
    VisualAuditReport,
    run_2d_visual_audit,
)

DEFAULT_ANIMATION_AUDIT_SIZES: tuple[tuple[int, int], ...] = ((820, 620),)
MAX_ANIMATION_PACING_ACTIVE_SAMPLES = 36

_MOTION_PROFILE_LAYERS = {
    "action-feedback",
    "actor-timeline",
    "blocked-action-feedback",
    "endgame-actor",
    "impact-cue",
    "inspector-actor",
    "late-game-choreography",
    "motion-pulses",
    "outcome-cinematic",
    "overlay-transition",
    "pending-choice",
    "pending-choice-preview",
    "product-drama",
    "review-actor",
    "risk-drama",
    "sprite-clips",
    "summary-cinematic",
    "summary-lanes",
    "summary-sequence",
    "title-actor",
    "transition",
}

_SCENE_MOTION_PROFILES: tuple[tuple[str, str, int], ...] = (
    ("title_menu", "title onboarding", 5),
    ("title_meta", "meta/archive board", 5),
    ("run_dashboard", "live dashboard", 6),
    ("run_drama_feedback", "product and risk drama", 6),
    ("run_pending_feedback", "pending-event preview", 8),
    ("run_impact_feedback", "impact feedback", 8),
    ("run_blocked_feedback", "blocked-action feedback", 9),
    ("run_picker_feedback", "picker choreography", 9),
    ("run_inspector", "inspector routing", 9),
    ("run_endgame_board", "endgame cockpit", 8),
    ("run_outcome_overlay", "outcome cinematic", 8),
    ("turn_summary", "turn-summary reveal", 7),
    ("review", "post-run review", 5),
)

_REQUIRED_SCENE_LAYERS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "title_menu",
        "Title/Menu Actors",
        (
            "transition",
            "motion-pulses",
            "actor-timeline",
            "sprite-clips",
            "title-actor",
            "actor-readability",
        ),
    ),
    (
        "run_dashboard",
        "Run Dashboard",
        (
            "transition",
            "motion-pulses",
            "product-drama",
            "actor-timeline",
            "sprite-clips",
            "actor-readability",
        ),
    ),
    ("run_drama_feedback", "Product/Risk Drama", ("product-drama", "risk-drama")),
    (
        "run_pending_feedback",
        "Pending Event Preview",
        ("pending", "overlay-transition", "pending-choice-preview"),
    ),
    ("run_impact_feedback", "Impact Feedback", ("impact-cue", "action-feedback")),
    (
        "run_blocked_feedback",
        "Blocked Action Feedback",
        ("action-feedback", "blocked-action-feedback"),
    ),
    (
        "run_picker_feedback",
        "Late-Game Command Choreography",
        ("picker", "action-feedback", "late-game-choreography"),
    ),
    (
        "run_inspector",
        "Inspector Actors",
        (
            "inspector",
            "overlay-transition",
            "actor-timeline",
            "sprite-clips",
            "inspector-actor",
            "actor-readability",
        ),
    ),
    (
        "run_endgame_board",
        "Endgame Board Actors",
        (
            "deep-panel",
            "actor-timeline",
            "sprite-clips",
            "endgame-actor",
            "actor-readability",
        ),
    ),
    (
        "run_outcome_overlay",
        "Outcome Cinematic",
        ("outcome", "overlay-transition", "outcome-cinematic"),
    ),
    (
        "turn_summary",
        "Turn Summary Cinematic",
        (
            "summary-reveal",
            "summary-cinematic",
            "summary-sequence",
            "summary-lanes",
            "actor-timeline",
            "sprite-clips",
            "actor-readability",
        ),
    ),
    (
        "review",
        "Review Actors",
        (
            "transition",
            "motion-pulses",
            "actor-timeline",
            "sprite-clips",
            "review-actor",
            "actor-readability",
        ),
    ),
)


@dataclass(frozen=True)
class AnimationCoverageCell:
    """One high-level animation coverage result."""

    area: str
    required_layers: tuple[str, ...]
    active_layers: tuple[str, ...]
    status: str
    notes: str


@dataclass(frozen=True)
class AnimationAuditReport:
    """Combined completeness report for the current 2D animation stack."""

    scenario_id: str
    difficulty: str
    seed: int
    cells: tuple[AnimationCoverageCell, ...]
    visual_report: VisualAuditReport
    motion_report: MotionAuditReport
    off_motion_report: MotionAuditReport
    advisory_gaps: tuple[str, ...]

    @property
    def status(self) -> str:
        """Return pass when required animation layers and budgets pass."""

        if any(cell.status == "fail" for cell in self.cells):
            return "fail"
        if self.visual_report.status != "pass":
            return "fail"
        if self.motion_report.status != "pass":
            return "fail"
        if self.off_motion_report.status != "pass":
            return "fail"
        return "pass"


def run_2d_animation_audit(
    *,
    scenario_id: str,
    difficulty_mode: DifficultyMode | None,
    seed: int,
    frames: int = 1,
    sizes: tuple[tuple[int, int], ...] = DEFAULT_ANIMATION_AUDIT_SIZES,
) -> AnimationAuditReport:
    """Run a combined animation-completeness audit from visual and motion gates."""

    visual_report = run_2d_visual_audit(
        scenario_id=scenario_id,
        difficulty_mode=difficulty_mode,
        seed=seed,
        sizes=sizes,
        motion_mode=MotionMode.FULL,
    )
    motion_report = run_2d_motion_audit(
        scenario_id=scenario_id,
        difficulty_mode=difficulty_mode,
        seed=seed,
        frames=frames,
        sizes=sizes,
        motion_mode=MotionMode.FULL,
    )
    off_motion_report = run_2d_motion_audit(
        scenario_id=scenario_id,
        difficulty_mode=difficulty_mode,
        seed=seed,
        frames=frames,
        sizes=sizes,
        motion_mode=MotionMode.OFF,
    )
    cells = list(_build_visual_coverage_cells(visual_report))
    cells.append(_build_motion_budget_cell(motion_report))
    cells.append(_build_motion_off_cell(off_motion_report))
    cells.append(_build_actor_sprite_cell(visual_report, motion_report, off_motion_report))
    cells.append(_build_visual_fatigue_cell(visual_report))
    cells.append(_build_animation_pacing_cell(motion_report))
    cells.append(_build_scene_motion_profile_cell(visual_report))
    cells.extend(_build_advisory_cells())
    return AnimationAuditReport(
        scenario_id=scenario_id,
        difficulty=difficulty_mode.value if difficulty_mode is not None else "scenario",
        seed=seed,
        cells=tuple(cells),
        visual_report=visual_report,
        motion_report=motion_report,
        off_motion_report=off_motion_report,
        advisory_gaps=(
            "Manual open-window playtest is still required for human read speed and rhythm.",
        ),
    )


def _build_visual_coverage_cells(
    visual_report: VisualAuditReport,
) -> tuple[AnimationCoverageCell, ...]:
    cells: list[AnimationCoverageCell] = []
    for scene_key, area, required_layers in _REQUIRED_SCENE_LAYERS:
        matching_cells = tuple(cell for cell in visual_report.cells if cell.scene_key == scene_key)
        active_layers = tuple(
            sorted({layer for cell in matching_cells for layer in cell.active_layers})
        )
        missing = tuple(layer for layer in required_layers if layer not in active_layers)
        if not matching_cells:
            cells.append(
                AnimationCoverageCell(
                    area=area,
                    required_layers=required_layers,
                    active_layers=(),
                    status="fail",
                    notes=f"missing visual scene {scene_key}",
                )
            )
            continue
        failed_frames = sum(1 for cell in matching_cells if cell.status != "pass")
        status = "fail" if missing or failed_frames else "pass"
        notes = "captured"
        if missing:
            notes = f"missing {','.join(missing)}"
        elif failed_frames:
            notes = f"{failed_frames} visual frame(s) failed"
        cells.append(
            AnimationCoverageCell(
                area=area,
                required_layers=required_layers,
                active_layers=active_layers,
                status=status,
                notes=notes,
            )
        )
    return tuple(cells)


def _build_motion_budget_cell(motion_report: MotionAuditReport) -> AnimationCoverageCell:
    return AnimationCoverageCell(
        area="Motion Budget",
        required_layers=("pulse-cooldown", "frame-budget", "request-paths"),
        active_layers=(motion_report.status, motion_report.flow_report.status),
        status="pass" if motion_report.status == "pass" else "fail",
        notes=(
            f"{len(motion_report.cells)} viewport(s), "
            f"{motion_report.flow_report.command_count} commands"
        ),
    )


def _build_motion_off_cell(off_motion_report: MotionAuditReport) -> AnimationCoverageCell:
    disabled = True
    for cell in off_motion_report.cells:
        disabled = disabled and cell.outcome_cinematic_active_samples == 0
        disabled = disabled and cell.pending_choice_preview_active_samples == 0
        disabled = disabled and cell.late_game_choreography_active_samples == 0
        disabled = disabled and cell.summary_lanes_active_samples == 0
        disabled = disabled and cell.actor_timeline_active_samples == 0
        disabled = disabled and cell.sprite_clips_active_samples == 0
    return AnimationCoverageCell(
        area="Motion Off Gate",
        required_layers=(
            "outcome-off",
            "pending-preview-off",
            "late-game-off",
            "summary-lanes-off",
            "actor-timeline-off",
            "sprite-clips-off",
        ),
        active_layers=("disabled",) if disabled else ("still-active",),
        status="pass" if disabled and off_motion_report.status == "pass" else "fail",
        notes=f"{len(off_motion_report.cells)} viewport(s) checked",
    )


def _build_actor_sprite_cell(
    visual_report: VisualAuditReport,
    motion_report: MotionAuditReport,
    off_motion_report: MotionAuditReport,
) -> AnimationCoverageCell:
    required_layers = (
        "actor-timeline",
        "sprite-clips",
        "actor-readability",
        "actor-off-gate",
    )
    visual_actor_layers = {
        layer
        for cell in visual_report.cells
        for layer in cell.active_layers
        if layer in {"actor-timeline", "sprite-clips", "actor-readability"}
    }
    full_active = any(
        cell.actor_timeline_active_samples > 0 and cell.sprite_clips_active_samples > 0
        for cell in motion_report.cells
    )
    off_disabled = all(
        cell.actor_timeline_active_samples == 0 and cell.sprite_clips_active_samples == 0
        for cell in off_motion_report.cells
    )
    active_layers = tuple(
        sorted(visual_actor_layers | ({"actor-off-gate"} if off_disabled else set()))
    )
    missing = tuple(
        layer
        for layer in ("actor-timeline", "sprite-clips", "actor-readability")
        if layer not in active_layers
    )
    status = "pass" if not missing and full_active and off_disabled else "fail"
    notes = "timeline active, readable, and off-mode gated"
    if missing:
        notes = f"missing {','.join(missing)}"
    elif not full_active:
        notes = "motion audit did not see active actor clips"
    elif not off_disabled:
        notes = "actor clips still active in motion-mode off"
    return AnimationCoverageCell(
        area="Sprite/Actor Layer",
        required_layers=required_layers,
        active_layers=active_layers,
        status=status,
        notes=notes,
    )


def _build_visual_fatigue_cell(visual_report: VisualAuditReport) -> AnimationCoverageCell:
    max_edge_density = max((cell.edge_density for cell in visual_report.cells), default=0.0)
    max_bright_ratio = max((cell.bright_ratio for cell in visual_report.cells), default=0.0)
    active_layers = (
        f"edge:{max_edge_density:.2f}",
        f"bright:{max_bright_ratio:.2f}",
        "visual-health",
    )
    status = (
        "pass"
        if max_edge_density <= MAX_EDGE_DENSITY and max_bright_ratio <= MAX_BRIGHT_RATIO
        else "fail"
    )
    notes = (
        f"edge <= {MAX_EDGE_DENSITY:.2f}, bright <= {MAX_BRIGHT_RATIO:.2f}"
        if status == "pass"
        else f"edge {max_edge_density:.2f} / bright {max_bright_ratio:.2f}"
    )
    return AnimationCoverageCell(
        area="Visual Fatigue Budget",
        required_layers=("edge-density", "bright-ratio", "visual-health"),
        active_layers=active_layers,
        status=status,
        notes=notes,
    )


def _build_animation_pacing_cell(motion_report: MotionAuditReport) -> AnimationCoverageCell:
    max_active_samples = max(
        (_animation_active_sample_count(cell) for cell in motion_report.cells),
        default=0,
    )
    max_average_frame = max((cell.average_frame_ms for cell in motion_report.cells), default=0.0)
    max_frame_spike = max((cell.max_frame_ms for cell in motion_report.cells), default=0.0)
    max_residual_pulses = max(
        (
            max(
                cell.run_after_pulses,
                cell.summary_after_pulses,
                cell.title_after_pulses,
                cell.review_after_pulses,
                cell.inspector_after_pulses,
                cell.long_run_after_pulses,
            )
            for cell in motion_report.cells
        ),
        default=0,
    )
    density_ok = max_active_samples <= MAX_ANIMATION_PACING_ACTIVE_SAMPLES
    frame_ok = max_average_frame <= 24.0 and max_frame_spike <= 50.0
    cooldown_ok = motion_report.status == "pass"
    status = "pass" if density_ok and frame_ok and cooldown_ok else "fail"
    active_layers = (
        f"active-samples:{max_active_samples}",
        f"residual-pulses:{max_residual_pulses}",
        f"avg-frame:{max_average_frame:.2f}ms",
        f"max-frame:{max_frame_spike:.2f}ms",
    )
    notes = f"samples <= {MAX_ANIMATION_PACING_ACTIVE_SAMPLES}, frames and cooldowns in budget"
    if not density_ok:
        notes = (
            f"animation sample density {max_active_samples} exceeds "
            f"{MAX_ANIMATION_PACING_ACTIVE_SAMPLES}"
        )
    elif not frame_ok:
        notes = f"frame budget avg {max_average_frame:.2f} ms / spike {max_frame_spike:.2f} ms"
    elif not cooldown_ok:
        notes = f"motion report status {motion_report.status}"
    return AnimationCoverageCell(
        area="Animation Pacing Budget",
        required_layers=(
            "sample-density",
            "pulse-cooldown",
            "frame-budget",
            "open-window-readiness",
        ),
        active_layers=active_layers,
        status=status,
        notes=notes,
    )


def _build_scene_motion_profile_cell(visual_report: VisualAuditReport) -> AnimationCoverageCell:
    profile_by_scene = {
        scene_key: (label, max_layers) for scene_key, label, max_layers in _SCENE_MOTION_PROFILES
    }
    observed_scene_keys = {cell.scene_key for cell in visual_report.cells}
    unprofiled = tuple(sorted(observed_scene_keys - set(profile_by_scene)))
    findings: list[str] = []
    scene_layer_counts: list[int] = []
    for scene_key, (label, max_layers) in profile_by_scene.items():
        matching_cells = tuple(cell for cell in visual_report.cells if cell.scene_key == scene_key)
        if not matching_cells:
            findings.append(f"missing {scene_key}")
            continue
        scene_max = max(_scene_motion_layer_count(cell) for cell in matching_cells)
        scene_layer_counts.append(scene_max)
        if scene_max > max_layers:
            findings.append(f"{label} {scene_max}>{max_layers}")
    if unprofiled:
        findings.append(f"unprofiled {','.join(unprofiled)}")

    max_observed = max(scene_layer_counts, default=0)
    active_layers = (
        f"profiles:{len(_SCENE_MOTION_PROFILES)}",
        f"max-scene-layers:{max_observed}",
        f"unprofiled:{len(unprofiled)}",
    )
    return AnimationCoverageCell(
        area="Scene Motion Profile",
        required_layers=("scene-profile-map", "max-motion-layers", "unprofiled-scene-gate"),
        active_layers=active_layers,
        status="pass" if not findings else "fail",
        notes=(
            f"{len(_SCENE_MOTION_PROFILES)} scene profiles, max motion layers {max_observed}"
            if not findings
            else "; ".join(findings[:4])
        ),
    )


def _animation_active_sample_count(cell: MotionAuditCell) -> int:
    return (
        cell.transition_active_scenes
        + cell.entity_motion_active_samples
        + cell.action_feedback_active_samples
        + cell.impact_cue_active_samples
        + cell.overlay_transition_active_samples
        + cell.outcome_cinematic_active_samples
        + cell.summary_cinematic_active_samples
        + cell.product_drama_active_samples
        + cell.risk_drama_active_samples
        + cell.pending_choice_active_samples
        + cell.pending_choice_preview_active_samples
        + cell.late_game_choreography_active_samples
        + cell.summary_sequence_active_samples
        + cell.summary_lanes_active_samples
        + cell.actor_timeline_active_samples
        + cell.sprite_clips_active_samples
    )


def _scene_motion_layer_count(cell) -> int:
    return sum(1 for layer in cell.active_layers if layer in _MOTION_PROFILE_LAYERS)


def _build_advisory_cells() -> tuple[AnimationCoverageCell, ...]:
    return (
        AnimationCoverageCell(
            area="Manual Playtest",
            required_layers=("open-window-readability",),
            active_layers=("advisory",),
            status="advisory",
            notes="headless audits cannot judge subjective timing or control feel",
        ),
    )
