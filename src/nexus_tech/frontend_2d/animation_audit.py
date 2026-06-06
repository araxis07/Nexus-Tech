"""High-level 2D animation completeness audit."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.domain.models import DifficultyMode
from nexus_tech.frontend_2d.motion_audit import MotionAuditReport, run_2d_motion_audit
from nexus_tech.frontend_2d.tween import MotionMode
from nexus_tech.frontend_2d.visual_audit import VisualAuditReport, run_2d_visual_audit

DEFAULT_ANIMATION_AUDIT_SIZES: tuple[tuple[int, int], ...] = ((820, 620),)

_REQUIRED_SCENE_LAYERS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "run_dashboard",
        "Run Dashboard",
        ("transition", "motion-pulses", "product-drama", "actor-timeline", "sprite-clips"),
    ),
    ("run_drama_feedback", "Product/Risk Drama", ("product-drama", "risk-drama")),
    (
        "run_pending_feedback",
        "Pending Event Preview",
        ("pending", "overlay-transition", "pending-choice-preview"),
    ),
    ("run_impact_feedback", "Impact Feedback", ("impact-cue", "action-feedback")),
    (
        "run_picker_feedback",
        "Late-Game Command Choreography",
        ("picker", "action-feedback", "late-game-choreography"),
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
            "Manual open-window playtest is still required for human read speed and overlap.",
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
    required_layers = ("actor-timeline", "sprite-clips", "actor-off-gate")
    visual_actor_layers = {
        layer
        for cell in visual_report.cells
        for layer in cell.active_layers
        if layer in {"actor-timeline", "sprite-clips"}
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
        layer for layer in ("actor-timeline", "sprite-clips") if layer not in active_layers
    )
    status = "pass" if not missing and full_active and off_disabled else "fail"
    notes = "timeline active and off-mode gated"
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


def _build_advisory_cells() -> tuple[AnimationCoverageCell, ...]:
    return (
        AnimationCoverageCell(
            area="Manual Playtest",
            required_layers=("open-window-readability",),
            active_layers=("advisory",),
            status="advisory",
            notes="headless audits cannot judge human timing or visual fatigue",
        ),
    )
