"""High-level 2D animation completeness audit."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

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
    MIN_CLICK_TARGET_HEIGHT,
    MIN_CLICK_TARGET_WIDTH,
    VisualAuditReport,
    run_2d_visual_audit,
)
from nexus_tech.persistence.save_coordinator import SaveLoadCoordinator
from nexus_tech.simulation.engine import create_new_game
from nexus_tech.simulation.randomness import RandomSource

DEFAULT_ANIMATION_AUDIT_SIZES: tuple[tuple[int, int], ...] = (
    (820, 620),
    (960, 640),
    (1440, 900),
)
DEFAULT_ANIMATION_MATRIX_SCENARIOS: tuple[str, ...] = (
    "founder_journey",
    "bootstrap_studio",
    "enterprise_compliance",
    "debt_crunch",
    "market_shock",
    "renewal_crunch",
    "late_scale_drag",
)
DEFAULT_ANIMATION_MATRIX_SEEDS: tuple[int, ...] = (7, 13, 29)
ANIMATION_MATRIX_REPORT_NAME = "animation-readiness-matrix.md"
ANIMATION_PLAYTEST_PREP_REPORT_NAME = "animation-playtest-prep.md"
ANIMATION_PLAYTEST_REPORT_NAME = "animation-playtest-report.md"
DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS: tuple[tuple[int, int], ...] = (
    (820, 620),
    (960, 640),
    (1440, 900),
)
DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES: tuple[str, ...] = ("full", "reduced", "off")
DEFAULT_OPEN_WINDOW_PLAYTEST_CONTROL_CHECKS: tuple[tuple[str, str], ...] = (
    (
        "Pause / Resume",
        "P and the Pause rail open the pause modal; Resume returns to the same run state.",
    ),
    (
        "Back / Escape",
        "Esc closes overlays first, then opens pause; it does not accidentally quit live play.",
    ),
    (
        "Menu Return",
        "Pause -> Menu saves and returns to the 2D title shell when a title shell exists.",
    ),
    (
        "Help / Hover",
        "F1, ?, and hover hints explain the current controls without hiding primary actions.",
    ),
    (
        "Control Replay Safety",
        (
            "Automated key/click replay verifies pause, resume, back, help, hover copy, "
            "and title-menu return before manual control-feel checks."
        ),
    ),
    (
        "Control Affordance Coverage",
        (
            "Visual and animation audits expose title, run, outcome, summary, review, "
            "pause, back, help, save, and flow controls before manual feel checks."
        ),
    ),
    (
        "UI Layout Safety",
        (
            "Visual and animation audits keep click targets in-bounds, large enough, "
            "non-overlapping, and clear of actor sprites before manual feel checks."
        ),
    ),
    (
        "Typography Safety",
        (
            "Visual and animation audits flag severe button-title fitting and hidden text before "
            "manual readability checks."
        ),
    ),
    (
        "Motion Modes",
        "Full, reduced, and off modes keep the same clickable actions and readable labels.",
    ),
)
DEFAULT_OPEN_WINDOW_PLAYTEST_SCENE_CHECKS: tuple[tuple[str, str], ...] = (
    (
        "Title/Menu",
        (
            "Wizard, saves, archive, meta board, archive comparison signals, "
            "and title actors stay readable."
        ),
    ),
    ("Live Dashboard", "Actors and product motion do not hide metrics, cards, or actions."),
    (
        "Action Picker",
        "Picker cards, path-specific late-game choreography, and cues do not compete for focus.",
    ),
    ("Pending Event", "Option preview motion clarifies choices without hiding text."),
    ("Inspector", "Selected row, pager, chips, actor routing, and footer stay readable."),
    ("Endgame Board", "Path-fix buttons stay primary while cockpit motion stays secondary."),
    ("Turn Summary", "Timeline cards reveal readably and actors do not hide metrics."),
    ("Outcome/Review", "Final cinematic and review actors do not hide after-action notes."),
    (
        "Scene Handoffs",
        ("Boot, run, summary, and review transitions feel purposeful without hiding navigation."),
    ),
)
DEFAULT_OPEN_WINDOW_PLAYTEST_FEEDBACK_CHECKS: tuple[tuple[str, str], ...] = (
    (
        "Success Feedback",
        "After a successful command, the player can tell which workspace or product changed.",
    ),
    (
        "Blocked Feedback",
        (
            "Blocked commands show a readable reason and a clear target "
            "without hiding primary actions."
        ),
    ),
    (
        "Impact Values",
        "Cash, users, reputation, board, and product deltas are readable before the cue fades.",
    ),
    (
        "Actor + Feedback Match",
        "Actor pose, action cue, and metric pulse describe the same outcome instead of competing.",
    ),
)
DEFAULT_OPEN_WINDOW_PLAYTEST_BALANCE_COMMANDS: tuple[str, ...] = (
    (
        "uv run nexus-tech balance-audit --scenario founder_journey --scenario debt_crunch "
        "--runs 1 --turns 6 --seed-base 7"
    ),
    (
        "uv run nexus-tech simulate-balance --scenario founder_journey --difficulty founder "
        "--runs 2 --turns 10 --seed-base 700"
    ),
    (
        "uv run nexus-tech balance-report --output /tmp/nexus-tech-balance-report.md "
        "--scenario founder_journey --runs 1 --turns 3 --seed-base 7"
    ),
)
REQUIRED_ANIMATION_PLAYTEST_AUTOMATED_GATES: tuple[str, ...] = (
    "ruff check src tests",
    "pytest tests/test_frontend_2d.py -q",
    "pytest -q",
    "audit-2d-motion full/reduced/off",
    "audit-2d-visual full/off",
    "audit-2d-animation",
    "audit-2d-animation-matrix --output",
    "prepare-2d-animation-playtest --output",
    "Balance / long-session preflight",
    "validate-animation-playtest-report",
    "Headless menu-2d / play-2d",
    "Open-window menu-2d / play-2d smoke",
)
REQUIRED_ANIMATION_PLAYTEST_BUILD_FIELDS: tuple[str, ...] = (
    "Version",
    "Commit",
    "Tester",
    "Date",
    "Platform",
)
REQUIRED_ANIMATION_PLAYTEST_BLOCKER_FIELDS: tuple[str, ...] = (
    "Hidden primary actions",
    "Unreadable disabled reasons",
    "Actor, tooltip, footer, modal, or button collisions",
    "Missing or unclear actor state reactions",
    "Unclear pause, back, help, save, or menu behavior",
    "Motion-mode regressions",
    "CI artifact anomalies",
    "visual-audit-summary.md anomalies",
    "animation-readiness-matrix.md anomalies",
    "Balance preflight warnings",
)
REQUIRED_ANIMATION_PLAYTEST_DECISION_FIELDS: tuple[str, ...] = (
    "Required fixes before presenting",
    "Nice-to-have polish",
    "Validator result",
)
MAX_ANIMATION_PACING_ACTIVE_SAMPLES = 36
MAX_REDUCED_ACTIVE_SAMPLE_OVERRUN = 3
COMPACT_READABILITY_WIDTH = 820
MAX_COMPACT_READABILITY_EDGE_DENSITY = 0.36
MIN_ACTOR_STATE_VARIANTS = 7

_ACTOR_STATE_GROUPS: tuple[tuple[str, frozenset[str]], ...] = (
    ("baseline", frozenset({"idle", "build", "handoff"})),
    ("positive", frozenset({"success", "shipping", "coaching", "negotiating"})),
    ("pressure", frozenset({"risk", "alert", "blocked", "firefighting"})),
)

_REQUIRED_TRANSITION_KEYS: tuple[str, ...] = (
    "transition-key:boot_title",
    "transition-key:boot_run",
    "transition-key:run_to_summary",
    "transition-key:run_to_review",
)

_REQUIRED_CONTROL_AFFORDANCE_LAYERS: tuple[str, ...] = (
    "click-targets",
    "title-nav-controls",
    "pause-control",
    "back-control",
    "help-control",
    "save-control",
    "flow-control",
    "run-nav-controls",
    "outcome-nav-controls",
    "summary-nav-controls",
    "review-nav-controls",
)

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

_READABILITY_ACTOR_SCENES = {
    "title_menu",
    "run_dashboard",
    "run_inspector",
    "run_endgame_board",
    "turn_summary",
    "review",
}

_READABILITY_OVERLAY_SCENES = {
    "run_pending_feedback",
    "run_blocked_feedback",
    "run_picker_feedback",
    "run_inspector",
    "run_outcome_overlay",
}

_LONG_SESSION_VISUAL_SCENES = {
    "run_dashboard",
    "run_inspector",
    "run_endgame_board",
    "turn_summary",
    "review",
}

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
            "actor-pose-depth",
        ),
    ),
    (
        "title_meta",
        "Archive/Meta Comparison Motion",
        (
            "transition",
            "motion-pulses",
            "title-actor",
            "archive-comparison",
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
            "actor-pose-depth",
        ),
    ),
    ("run_drama_feedback", "Product/Risk Drama", ("product-drama", "risk-drama")),
    (
        "run_pending_feedback",
        "Pending Event Preview",
        ("pending", "overlay-transition", "pending-choice-preview"),
    ),
    (
        "run_impact_feedback",
        "Impact Feedback",
        (
            "impact-cue",
            "impact-cue-targets",
            "impact-value-label",
            "action-feedback",
            "action-feedback-targets",
        ),
    ),
    (
        "run_blocked_feedback",
        "Blocked Action Feedback",
        (
            "action-feedback",
            "action-feedback-targets",
            "blocked-action-feedback",
            "blocked-action-reason",
        ),
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
            "actor-pose-depth",
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
            "actor-pose-depth",
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
            "actor-pose-depth",
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
            "actor-pose-depth",
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


@dataclass(frozen=True)
class AnimationMatrixCell:
    """One scenario/seed result from the broad 2D animation readiness matrix."""

    scenario_id: str
    difficulty: str
    seed: int
    status: str
    visual_baseline: str
    failed_areas: tuple[str, ...]
    advisory_gaps: tuple[str, ...]


@dataclass(frozen=True)
class AnimationMatrixReport:
    """Broad animation readiness report across multiple scenarios and seeds."""

    scenario_ids: tuple[str, ...]
    difficulty: str
    seeds: tuple[int, ...]
    frames: int
    cells: tuple[AnimationMatrixCell, ...]

    @property
    def status(self) -> str:
        """Return pass only when every scenario/seed animation gate passes."""

        return "pass" if all(cell.status == "pass" for cell in self.cells) else "fail"


@dataclass(frozen=True)
class AnimationPlaytestPrepReport:
    """Automated preflight package for the human open-window animation pass."""

    version: str
    matrix_report: AnimationMatrixReport
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES
    control_checks: tuple[tuple[str, str], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_CONTROL_CHECKS
    scene_checks: tuple[tuple[str, str], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_SCENE_CHECKS
    feedback_checks: tuple[tuple[str, str], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_FEEDBACK_CHECKS
    balance_commands: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_BALANCE_COMMANDS
    visual_artifact_name: str = "nexus-tech-2d-visual-audit"
    matrix_artifact_name: str = "nexus-tech-2d-animation-matrix"
    playtest_artifact_name: str = "nexus-tech-2d-animation-playtest-prep"

    @property
    def status(self) -> str:
        """Return ready only when the automated scenario/seed matrix passes."""

        return "ready" if self.matrix_report.status == "pass" else "blocked"


@dataclass(frozen=True)
class AnimationPlaytestCommand:
    """One visible-window command that must be run during manual animation QA."""

    target: str
    window_size: str
    motion_mode: str
    command: str


@dataclass(frozen=True)
class AnimationPlaytestCommandQueueValidation:
    """Validation result for a manual animation playtest command queue artifact."""

    path: str
    expected_count: int
    findings: tuple[str, ...]

    @property
    def status(self) -> str:
        """Return pass only when the queue covers every required command exactly."""

        return "pass" if not self.findings else "fail"


@dataclass(frozen=True)
class AnimationPlaytestReportValidation:
    """Validation result for a completed manual 2D animation playtest report."""

    path: str
    release_decision: str
    findings: tuple[str, ...]

    @property
    def status(self) -> str:
        """Return pass only when the report is completed and signed off."""

        return "pass" if not self.findings else "fail"


@dataclass(frozen=True)
class AnimationPlaytestReportStatusArea:
    """Grouped status for one section of the manual animation playtest report."""

    area: str
    findings: tuple[str, ...]
    next_step: str

    @property
    def incomplete_count(self) -> int:
        """Return how many validation findings remain in this section."""

        return len(self.findings)


@dataclass(frozen=True)
class AnimationPlaytestPlanStep:
    """One actionable manual animation QA step derived from current artifacts."""

    area: str
    status: str
    next_step: str
    open_items: int


@dataclass(frozen=True)
class AnimationPlaytestReadinessPlan:
    """Combined readiness plan for command queue and manual animation report."""

    report: AnimationPlaytestReportValidation
    commands: AnimationPlaytestCommandQueueValidation
    steps: tuple[AnimationPlaytestPlanStep, ...]

    @property
    def status(self) -> str:
        """Return the current handoff status without faking manual signoff."""

        if self.commands.status != "pass":
            return "blocked"
        if self.report.status != "pass":
            return "manual-required"
        return "pass"

    @property
    def open_item_count(self) -> int:
        """Return total unresolved queue and report issues."""

        return len(self.report.findings) + len(self.commands.findings)


@dataclass(frozen=True)
class AnimationPlaytestPlanArtifactValidation:
    """Validation result for an exported animation playtest plan artifact."""

    path: str
    expected_status: str
    findings: tuple[str, ...]

    @property
    def status(self) -> str:
        """Return pass only when the exported plan matches current artifacts."""

        return "pass" if not self.findings else "fail"


_ANIMATION_PLAYTEST_STATUS_AREAS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        "Automated Gates",
        ("automated gate",),
        "Rerun local/CI preflight or draft with --prefill-automated-gates after it passes.",
    ),
    (
        "Manual Window Matrix",
        ("window matrix",),
        "Test 820x620, 960x640, and 1440x900 in full, reduced, and off modes.",
    ),
    (
        "Manual Control Checks",
        ("control check",),
        "Verify pause/resume, back/escape, menu return, help/hover, layout, typography, and modes.",
    ),
    (
        "Manual Scene Checks",
        ("scene check",),
        "Review title, dashboard, picker, pending event, inspector, endgame, summary, and review.",
    ),
    (
        "Manual Game Feel",
        ("game-feel check",),
        "Confirm success, blocked, impact, and actor/feedback cues are readable and aligned.",
    ),
    (
        "Manual Evidence Notes",
        ("evidence",),
        "Replace generic notes like ok/clear/readable with concise observed tester evidence.",
    ),
    (
        "Signoff Fields",
        ("missing field", "release decision"),
        "Fill release blocker notes, decision fields, validator result, and final pass decision.",
    ),
    (
        "Template Cleanup",
        ("todo cells", "blank table cells"),
        "Replace template placeholders with pass/watch/fail and real tester notes.",
    ),
)


def validate_2d_animation_playtest_report(report_path: Path) -> AnimationPlaytestReportValidation:
    """Validate that a manual animation playtest report is completed, not still a template."""

    text = report_path.read_text(encoding="utf-8")
    findings: list[str] = []
    normalized = text.lower()
    rows = _extract_markdown_table_rows(text)
    if "`todo`" in normalized or re.search(r"\|\s*todo\s*\|", normalized):
        findings.append("report still contains todo cells")
    if re.search(r"\|[ \t]*\|", text):
        findings.append("report still contains blank table cells")

    for label in REQUIRED_ANIMATION_PLAYTEST_BUILD_FIELDS:
        if _is_placeholder_field(_extract_report_field(text, label)):
            findings.append(f"missing field: {label}")

    _validate_required_result_rows(
        findings,
        rows,
        REQUIRED_ANIMATION_PLAYTEST_AUTOMATED_GATES,
        "automated gate",
        evidence_columns=((2, "notes"),),
    )
    _validate_required_window_matrix(findings, rows)
    _validate_required_result_rows(
        findings,
        rows,
        tuple(area for area, _ in DEFAULT_OPEN_WINDOW_PLAYTEST_CONTROL_CHECKS),
        "control check",
        evidence_columns=((2, "notes"),),
    )
    _validate_required_result_rows(
        findings,
        rows,
        tuple(scene for scene, _ in DEFAULT_OPEN_WINDOW_PLAYTEST_SCENE_CHECKS),
        "scene check",
        evidence_columns=((2, "readability notes"), (3, "motion notes")),
    )
    _validate_required_result_rows(
        findings,
        rows,
        tuple(area for area, _ in DEFAULT_OPEN_WINDOW_PLAYTEST_FEEDBACK_CHECKS),
        "game-feel check",
        evidence_columns=((2, "notes"),),
    )

    release_decision = _extract_report_field(text, "Release decision")
    decision = release_decision.strip("` ").lower()
    if not release_decision:
        findings.append("missing release decision")
    elif "/" in release_decision or decision not in {"pass", "watch", "fail"}:
        findings.append("release decision is still the template placeholder")
    elif decision != "pass":
        findings.append(f"release decision is {decision}, not pass")

    for label in (
        *REQUIRED_ANIMATION_PLAYTEST_BLOCKER_FIELDS,
        *REQUIRED_ANIMATION_PLAYTEST_DECISION_FIELDS,
    ):
        value = _extract_report_field(text, label)
        if _is_placeholder_field(value):
            findings.append(f"missing field: {label}")

    return AnimationPlaytestReportValidation(
        path=str(report_path),
        release_decision=decision if release_decision else "",
        findings=tuple(findings),
    )


def summarize_2d_animation_playtest_report(
    validation: AnimationPlaytestReportValidation,
) -> tuple[AnimationPlaytestReportStatusArea, ...]:
    """Group manual animation report validation findings into actionable areas."""

    grouped: list[AnimationPlaytestReportStatusArea] = []
    matched: set[str] = set()
    for area, markers, next_step in _ANIMATION_PLAYTEST_STATUS_AREAS:
        findings = tuple(
            finding
            for finding in validation.findings
            if any(marker in finding.lower() for marker in markers)
        )
        if not findings:
            continue
        matched.update(findings)
        grouped.append(
            AnimationPlaytestReportStatusArea(
                area=area,
                findings=findings,
                next_step=next_step,
            )
        )

    uncategorized = tuple(finding for finding in validation.findings if finding not in matched)
    if uncategorized:
        grouped.append(
            AnimationPlaytestReportStatusArea(
                area="Other Findings",
                findings=uncategorized,
                next_step="Review the remaining validator findings directly.",
            )
        )

    return tuple(grouped)


def build_2d_animation_playtest_readiness_plan(
    report_path: Path,
    command_path: Path,
    *,
    scenario_id: str = "founder_journey",
    seed: int = 7,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    command_prefix: str = "uv run nexus-tech",
) -> AnimationPlaytestReadinessPlan:
    """Build an actionable handoff plan from the current manual QA artifacts."""

    report = validate_2d_animation_playtest_report(report_path)
    commands = validate_2d_animation_playtest_command_queue(
        command_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    steps: list[AnimationPlaytestPlanStep] = []
    if commands.findings:
        steps.append(
            AnimationPlaytestPlanStep(
                area="Command Queue",
                status="blocked",
                next_step=(
                    "Regenerate the visible-window queue, then rerun "
                    "validate-animation-playtest-commands before manual testing."
                ),
                open_items=len(commands.findings),
            )
        )

    for area in summarize_2d_animation_playtest_report(report):
        steps.append(
            AnimationPlaytestPlanStep(
                area=area.area,
                status="manual-required",
                next_step=area.next_step,
                open_items=area.incomplete_count,
            )
        )

    if not steps:
        steps.append(
            AnimationPlaytestPlanStep(
                area="Release Signoff",
                status="pass",
                next_step=(
                    "Manual animation signoff report is complete; attach validator "
                    "evidence before presentation."
                ),
                open_items=0,
            )
        )

    return AnimationPlaytestReadinessPlan(
        report=report,
        commands=commands,
        steps=tuple(steps),
    )


def write_2d_animation_playtest_readiness_plan(
    plan: AnimationPlaytestReadinessPlan,
    output_path: Path,
) -> None:
    """Write the grouped manual animation QA plan as a Markdown handoff artifact."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    manual_result = _plan_manual_result(plan)
    release_decision = _plan_release_decision(plan)
    lines = [
        "# NEXUS TECH 2D Animation Playtest Plan",
        "",
        f"- Status: `{plan.status}`",
        f"- Report: `{plan.report.path}`",
        f"- Commands: `{plan.commands.path}`",
        f"- Command queue status: `{plan.commands.status}`",
        f"- Report status: `{plan.report.status}`",
        f"- Release decision: `{release_decision}`",
        f"- Open items: `{plan.open_item_count}`",
        f"- Manual result: `{manual_result}`",
        "- Completion gate: `validate-animation-playtest-report must pass before signoff`",
        "",
        "## Next Animation QA Steps",
        "",
        "| Area | Status | Open Items | Next Step |",
        "| --- | --- | ---: | --- |",
    ]
    for step in plan.steps:
        lines.append(
            "| "
            f"{_markdown_table_cell(step.area)} | "
            f"`{step.status}` | "
            f"`{step.open_items}` | "
            f"{_markdown_table_cell(step.next_step)} |"
        )

    if plan.commands.findings:
        lines.extend(
            [
                "",
                "## Command Queue Findings",
                "",
                "| Finding |",
                "| --- |",
            ]
        )
        for finding in plan.commands.findings:
            lines.append(f"| {_markdown_table_cell(finding)} |")

    if plan.report.findings:
        lines.extend(
            [
                "",
                "## Report Findings",
                "",
                "| Finding |",
                "| --- |",
            ]
        )
        for finding in plan.report.findings:
            lines.append(f"| {_markdown_table_cell(finding)} |")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_2d_animation_playtest_readiness_plan(
    plan_path: Path,
    report_path: Path,
    command_path: Path,
    *,
    scenario_id: str = "founder_journey",
    seed: int = 7,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    command_prefix: str = "uv run nexus-tech",
) -> AnimationPlaytestPlanArtifactValidation:
    """Validate that an exported animation plan still matches the source artifacts."""

    text = plan_path.read_text(encoding="utf-8")
    plan = build_2d_animation_playtest_readiness_plan(
        report_path,
        command_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    findings: list[str] = []
    expected_lines = (
        "# NEXUS TECH 2D Animation Playtest Plan",
        f"- Status: `{plan.status}`",
        f"- Report: `{plan.report.path}`",
        f"- Commands: `{plan.commands.path}`",
        f"- Command queue status: `{plan.commands.status}`",
        f"- Report status: `{plan.report.status}`",
        f"- Release decision: `{_plan_release_decision(plan)}`",
        f"- Open items: `{plan.open_item_count}`",
        f"- Manual result: `{_plan_manual_result(plan)}`",
        "- Completion gate: `validate-animation-playtest-report must pass before signoff`",
    )
    for line in expected_lines:
        if line not in text:
            findings.append(f"missing or stale plan line: {line}")

    rows = _extract_markdown_table_rows(text)
    for step in plan.steps:
        row = _find_report_table_row(rows, step.area)
        if row is None:
            findings.append(f"missing plan step row: {step.area}")
            continue
        if len(row) <= 3:
            findings.append(f"incomplete plan step row: {step.area}")
            continue
        status = _strip_markdown_code(row[1])
        open_items = _strip_markdown_code(row[2])
        next_step = row[3].replace(r"\|", "|").strip()
        if status != step.status:
            findings.append(f"plan step {step.area} status is {status}, expected {step.status}")
        if open_items != str(step.open_items):
            findings.append(
                f"plan step {step.area} open items is {open_items}, expected {step.open_items}"
            )
        if _normalize_report_key(next_step) != _normalize_report_key(step.next_step):
            findings.append(f"plan step {step.area} next step is stale")

    for finding in plan.commands.findings:
        if finding not in text:
            findings.append(f"missing command queue finding: {finding}")
    for finding in plan.report.findings:
        if finding not in text:
            findings.append(f"missing report finding: {finding}")

    return AnimationPlaytestPlanArtifactValidation(
        path=str(plan_path),
        expected_status=plan.status,
        findings=tuple(findings),
    )


def _plan_manual_result(plan: AnimationPlaytestReadinessPlan) -> str:
    return (
        "report validator passed before this plan was written"
        if plan.status == "pass"
        else "not completed by automation"
    )


def _plan_release_decision(plan: AnimationPlaytestReadinessPlan) -> str:
    raw_release_decision = plan.report.release_decision
    if "/" in raw_release_decision or _is_placeholder_field(raw_release_decision):
        return "-"
    return raw_release_decision or "-"


def _extract_markdown_table_rows(text: str) -> tuple[tuple[str, ...], ...]:
    rows: list[tuple[str, ...]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = tuple(cell.strip() for cell in stripped.strip("|").split("|"))
        if not cells or _is_markdown_separator_row(cells):
            continue
        rows.append(cells)
    return tuple(rows)


def _strip_markdown_code(value: str) -> str:
    return value.strip().strip("` ")


def _markdown_table_cell(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("|", r"\|")).strip()


def _is_markdown_separator_row(cells: tuple[str, ...]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)


def _validate_required_window_matrix(
    findings: list[str],
    rows: tuple[tuple[str, ...], ...],
) -> None:
    for width, height in DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS:
        label = f"{width}x{height}"
        row = _find_report_table_row(rows, label)
        if row is None:
            findings.append(f"missing window matrix row: {label}")
            continue
        for index, mode in enumerate(("Full", "Reduced", "Off"), start=1):
            if len(row) <= index or _is_placeholder_result(row[index]):
                findings.append(f"incomplete window matrix result: {label} {mode}")
                continue
            if not _is_passing_result(row[index]):
                result = _normalize_report_result(row[index]) or "blank"
                findings.append(f"window matrix {label} {mode} is {result}, not pass")
        if len(row) <= 4 or _is_thin_evidence(row[4]):
            findings.append(f"missing window matrix evidence: {label} notes")


def _validate_required_result_rows(
    findings: list[str],
    rows: tuple[tuple[str, ...], ...],
    labels: tuple[str, ...],
    category: str,
    *,
    evidence_columns: tuple[tuple[int, str], ...] = (),
) -> None:
    for label in labels:
        row = _find_report_table_row(rows, label)
        if row is None:
            findings.append(f"missing {category} row: {label}")
            continue
        if len(row) <= 1 or _is_placeholder_result(row[1]):
            findings.append(f"incomplete {category} result: {label}")
            continue
        if not _is_passing_result(row[1]):
            result = _normalize_report_result(row[1]) or "blank"
            findings.append(f"{category} {label} is {result}, not pass")
        for column_index, evidence_name in evidence_columns:
            if len(row) <= column_index or _is_thin_evidence(row[column_index]):
                findings.append(f"missing {category} evidence: {label} {evidence_name}")


def _find_report_table_row(
    rows: tuple[tuple[str, ...], ...],
    label: str,
) -> tuple[str, ...] | None:
    key = _normalize_report_key(label)
    for row in rows:
        if row and _normalize_report_key(row[0]) == key:
            return row
    return None


def _normalize_report_key(value: str) -> str:
    value = value.strip().strip("` ")
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _normalize_report_result(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().strip("` ")).lower()


def _is_placeholder_result(value: str) -> bool:
    normalized = _normalize_report_result(value)
    return (
        not normalized
        or normalized in {"-", "n/a", "na", "pending", "tbd", "todo", "fill-me", "fill me"}
        or "pass / watch / fail" in normalized
        or "pass/watch/fail" in normalized
    )


def _is_passing_result(value: str) -> bool:
    normalized = _normalize_report_result(value)
    return (
        normalized in {"ok", "pass", "passed", "success", "completed success", "green"}
        or normalized.startswith("pass ")
        or normalized.startswith("passed ")
        or normalized.startswith("success ")
    )


def _is_placeholder_field(value: str) -> bool:
    normalized = _normalize_report_result(value)
    return (
        not normalized
        or normalized in {"-", "n/a", "na", "pending", "tbd", "todo", "fill-me", "fill me"}
        or "fill me" in normalized
        or "pass / watch / fail" in normalized
        or "pass/watch/fail" in normalized
    )


def _is_thin_evidence(value: str) -> bool:
    normalized = _normalize_report_result(value)
    return _is_placeholder_field(value) or normalized in {
        "ok",
        "clear",
        "readable",
        "stable",
        "verified",
        "works",
        "pass",
        "passed",
        "success",
        "none",
    }


def _extract_report_field(text: str, label: str) -> str:
    pattern = re.compile(rf"^\s*-?\s*{re.escape(label)}:\s*(.+?)\s*$", re.IGNORECASE)
    for line in text.splitlines():
        match = pattern.match(line)
        if match is None:
            continue
        value = match.group(1).strip()
        return value.strip("` ")
    return ""


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
    reduced_motion_report = run_2d_motion_audit(
        scenario_id=scenario_id,
        difficulty_mode=difficulty_mode,
        seed=seed,
        frames=frames,
        sizes=sizes,
        motion_mode=MotionMode.REDUCED,
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
    cells.append(_build_long_session_motion_cell(motion_report))
    cells.append(_build_motion_off_cell(off_motion_report))
    cells.append(
        _build_motion_mode_differentiation_cell(
            motion_report,
            reduced_motion_report,
            off_motion_report,
        )
    )
    cells.append(
        _build_scene_transition_handoff_cell(visual_report, motion_report, off_motion_report)
    )
    cells.append(_build_control_affordance_cell(visual_report))
    cells.append(_build_control_replay_safety_cell(seed=seed))
    cells.append(_build_ui_layout_safety_cell(visual_report))
    cells.append(_build_typography_safety_cell(visual_report))
    cells.append(_build_actor_sprite_cell(visual_report, motion_report, off_motion_report))
    cells.append(_build_actor_state_coverage_cell(visual_report))
    cells.append(_build_action_feedback_clarity_cell(visual_report))
    cells.append(_build_visual_fatigue_cell(visual_report))
    cells.append(_build_animation_pacing_cell(motion_report))
    cells.append(_build_scene_motion_profile_cell(visual_report))
    cells.append(_build_readability_guard_cell(visual_report))
    cells.append(_build_long_session_visual_readiness_cell(visual_report))
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


def run_2d_animation_matrix_audit(
    *,
    scenario_ids: tuple[str, ...] = DEFAULT_ANIMATION_MATRIX_SCENARIOS,
    difficulty_mode: DifficultyMode | None,
    seeds: tuple[int, ...] = DEFAULT_ANIMATION_MATRIX_SEEDS,
    frames: int = 1,
    sizes: tuple[tuple[int, int], ...] = DEFAULT_ANIMATION_AUDIT_SIZES,
) -> AnimationMatrixReport:
    """Run the animation-completeness gate across a scenario/seed matrix."""

    cells: list[AnimationMatrixCell] = []
    for scenario_id in scenario_ids:
        for seed in seeds:
            report = run_2d_animation_audit(
                scenario_id=scenario_id,
                difficulty_mode=difficulty_mode,
                seed=seed,
                frames=frames,
                sizes=sizes,
            )
            failed_areas = tuple(cell.area for cell in report.cells if cell.status == "fail")
            cells.append(
                AnimationMatrixCell(
                    scenario_id=scenario_id,
                    difficulty=report.difficulty,
                    seed=seed,
                    status=report.status,
                    visual_baseline=report.visual_report.baseline_signature,
                    failed_areas=failed_areas,
                    advisory_gaps=report.advisory_gaps,
                )
            )
    return AnimationMatrixReport(
        scenario_ids=scenario_ids,
        difficulty=difficulty_mode.value if difficulty_mode is not None else "scenario",
        seeds=seeds,
        frames=frames,
        cells=tuple(cells),
    )


def write_2d_animation_matrix_report(
    report: AnimationMatrixReport,
    output_path: Path,
) -> None:
    """Write a Markdown readiness artifact for a broad animation matrix run."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    passed = sum(1 for cell in report.cells if cell.status == "pass")
    failed = len(report.cells) - passed
    lines = [
        "# NEXUS TECH 2D Animation Matrix",
        "",
        f"- Status: `{report.status}`",
        f"- Difficulty: `{report.difficulty}`",
        f"- Scenarios: `{', '.join(report.scenario_ids)}`",
        f"- Seeds: `{', '.join(str(seed) for seed in report.seeds)}`",
        f"- Frames: `{report.frames}`",
        f"- Cells: `{len(report.cells)}` total, `{passed}` pass, `{failed}` fail",
        "- Manual playtest: `required for human read speed and control feel`",
        "",
        "| Scenario | Seed | Status | Baseline | Failed Areas | Advisory Gaps |",
        "| --- | ---: | --- | --- | --- | ---: |",
    ]
    for cell in report.cells:
        failed_areas = ", ".join(cell.failed_areas) if cell.failed_areas else "-"
        lines.append(
            "| "
            f"`{cell.scenario_id}` | "
            f"`{cell.seed}` | "
            f"`{cell.status}` | "
            f"`{cell.visual_baseline}` | "
            f"{failed_areas} | "
            f"`{len(cell.advisory_gaps)}` |"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_2d_animation_playtest_prep_report(
    *,
    version: str,
    matrix_report: AnimationMatrixReport,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    control_checks: tuple[tuple[str, str], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_CONTROL_CHECKS,
    scene_checks: tuple[tuple[str, str], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_SCENE_CHECKS,
    feedback_checks: tuple[tuple[str, str], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_FEEDBACK_CHECKS,
    balance_commands: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_BALANCE_COMMANDS,
) -> AnimationPlaytestPrepReport:
    """Build the report shell used before the real open-window animation pass."""

    return AnimationPlaytestPrepReport(
        version=version,
        matrix_report=matrix_report,
        windows=windows,
        motion_modes=motion_modes,
        control_checks=control_checks,
        scene_checks=scene_checks,
        feedback_checks=feedback_checks,
        balance_commands=balance_commands,
    )


def build_2d_animation_playtest_command_queue(
    *,
    scenario_id: str = "founder_journey",
    seed: int = 7,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    command_prefix: str = "uv run nexus-tech",
) -> tuple[AnimationPlaytestCommand, ...]:
    """Return the visible-window command queue required for manual animation QA."""

    queue: list[AnimationPlaytestCommand] = []
    for width, height in windows:
        window_size = f"{width}x{height}"
        for mode in motion_modes:
            menu_command = (
                f"{command_prefix} menu-2d --window-size {window_size} --motion-mode {mode}"
            )
            queue.append(
                AnimationPlaytestCommand(
                    target="menu",
                    window_size=window_size,
                    motion_mode=mode,
                    command=menu_command,
                )
            )
            play_command = (
                f"{command_prefix} play-2d --scenario {scenario_id} --seed {seed} "
                f"--window-size {window_size} --motion-mode {mode}"
            )
            queue.append(
                AnimationPlaytestCommand(
                    target="play",
                    window_size=window_size,
                    motion_mode=mode,
                    command=play_command,
                )
            )
    return tuple(queue)


def write_2d_animation_playtest_command_queue(
    queue: tuple[AnimationPlaytestCommand, ...],
    output_path: Path,
) -> None:
    """Write the manual animation QA command queue without marking signoff complete."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NEXUS TECH 2D Manual Animation Playtest Commands",
        "",
        "- Manual result: `not completed by automation`",
        "- Fill the strict playtest report with real tester observations after running these.",
        "",
        "| Step | Target | Window | Motion | Command |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for index, item in enumerate(queue, start=1):
        lines.append(
            f"| {index} | `{item.target}` | `{item.window_size}` | "
            f"`{item.motion_mode}` | `{item.command}` |"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_2d_animation_playtest_command_queue(
    queue_path: Path,
    *,
    scenario_id: str = "founder_journey",
    seed: int = 7,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    command_prefix: str = "uv run nexus-tech",
) -> AnimationPlaytestCommandQueueValidation:
    """Validate that an exported manual animation QA command queue is complete."""

    text = queue_path.read_text(encoding="utf-8")
    findings: list[str] = []
    if "- Manual result: `not completed by automation`" not in text:
        findings.append("manual result guard is missing")

    rows = _extract_markdown_table_rows(text)
    command_rows = tuple(row for row in rows if len(row) >= 5 and row[0].isdigit())
    expected_queue = build_2d_animation_playtest_command_queue(
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    expected_commands = {item.command for item in expected_queue}
    actual_commands = tuple(_strip_markdown_code(row[4]) for row in command_rows)
    actual_command_set = set(actual_commands)

    if len(command_rows) != len(expected_queue):
        findings.append(f"expected {len(expected_queue)} command rows, found {len(command_rows)}")
    if len(actual_commands) != len(actual_command_set):
        findings.append("command queue contains duplicate commands")

    for item in expected_queue:
        if item.command not in actual_command_set:
            findings.append(f"missing command: {item.command}")

    for command in actual_commands:
        if command not in expected_commands:
            findings.append(f"unexpected command: {command}")

    return AnimationPlaytestCommandQueueValidation(
        path=str(queue_path),
        expected_count=len(expected_queue),
        findings=tuple(findings),
    )


def write_2d_animation_playtest_prep_report(
    report: AnimationPlaytestPrepReport,
    output_path: Path,
) -> None:
    """Write a Markdown playtest prep artifact with automated evidence and human checks."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    matrix = report.matrix_report
    passed = sum(1 for cell in matrix.cells if cell.status == "pass")
    failed = len(matrix.cells) - passed
    release_blocker_fields = (
        *REQUIRED_ANIMATION_PLAYTEST_BLOCKER_FIELDS,
        *REQUIRED_ANIMATION_PLAYTEST_DECISION_FIELDS,
    )
    lines = [
        "# NEXUS TECH 2D Animation Playtest Prep",
        "",
        f"- Status: `{report.status}`",
        f"- Version: `{report.version}`",
        f"- Automated matrix: `{matrix.status}`",
        f"- Matrix cells: `{len(matrix.cells)}` total, `{passed}` pass, `{failed}` fail",
        f"- Scenarios: `{', '.join(matrix.scenario_ids)}`",
        f"- Seeds: `{', '.join(str(seed) for seed in matrix.seeds)}`",
        f"- Frames per matrix cell: `{matrix.frames}`",
        "- Manual result: `not completed by automation`",
        f"- CI visual artifact: `{report.visual_artifact_name}`",
        f"- CI matrix artifact: `{report.matrix_artifact_name}`",
        f"- CI playtest prep artifact: `{report.playtest_artifact_name}`",
        "- Completion gate: `manual signoff required before calling animation complete`",
        "",
        "## Required Local Preflight",
        "",
        "```bash",
        "uv run nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 2",
        (
            "uv run nexus-tech audit-2d-motion --scenario founder_journey --seed 7 "
            "--frames 1 --motion-mode reduced"
        ),
        (
            "uv run nexus-tech audit-2d-motion --scenario founder_journey --seed 7 "
            "--frames 1 --motion-mode off"
        ),
        (
            "uv run nexus-tech audit-2d-visual --scenario founder_journey --seed 7 "
            "--output-dir /tmp/nexus-tech-visual-audit/full"
        ),
        (
            "uv run nexus-tech audit-2d-visual --scenario founder_journey --seed 7 "
            "--motion-mode off --output-dir /tmp/nexus-tech-visual-audit/off"
        ),
        "uv run nexus-tech audit-2d-animation --scenario founder_journey --seed 7 --frames 1",
        (
            "uv run nexus-tech audit-2d-animation-matrix --frames 1 "
            "--output /tmp/nexus-tech-animation-matrix.md"
        ),
        (
            "uv run nexus-tech prepare-2d-animation-playtest --frames 1 "
            "--output /tmp/nexus-tech-animation-playtest-prep.md"
        ),
        "```",
        "",
        "## Balance And Long-Session Preflight",
        "",
        "Run these before marking the manual animation pass ready for presentation. "
        "Balance warnings should be named as intentional pressure or fixed before adding "
        "more animation layers.",
        "",
        "```bash",
    ]
    lines.extend(report.balance_commands)
    lines.extend(
        [
            "```",
            "",
            "## Open-Window Commands",
            "",
            "Launch each target size directly and repeat the scene checks.",
            "",
            "```bash",
        ]
    )
    for item in build_2d_animation_playtest_command_queue(
        windows=report.windows,
        motion_modes=report.motion_modes,
    ):
        lines.append(item.command)
    lines.extend(
        [
            "```",
            "",
            "## Window And Motion Matrix",
            "",
            "| Window | Full | Reduced | Off | Required Check |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for width, height in report.windows:
        lines.append(
            f"| `{width}x{height}` | `todo` | `todo` | `todo` | "
            "No hidden primary action, unreadable disabled reason, or actor collision |"
        )
    lines.extend(
        [
            "",
            "## Control Clarity Checklist",
            "",
            "| Control Area | Required Human Judgment | Result |",
            "| --- | --- | --- |",
        ]
    )
    for area, required_judgment in report.control_checks:
        lines.append(f"| {area} | {required_judgment} | `todo` |")
    lines.extend(
        [
            "",
            "## Scene Checklist",
            "",
            "| Scene | Required Human Judgment | Result |",
            "| --- | --- | --- |",
        ]
    )
    for scene, required_judgment in report.scene_checks:
        lines.append(f"| {scene} | {required_judgment} | `todo` |")
    lines.extend(
        [
            "",
            "## Game Feel Checklist",
            "",
            "| Feedback Area | Required Human Judgment | Result |",
            "| --- | --- | --- |",
        ]
    )
    for area, required_judgment in report.feedback_checks:
        lines.append(f"| {area} | {required_judgment} | `todo` |")
    lines.extend(
        [
            "",
            "## Manual Completion Gate",
            "",
            "- Every window/motion cell must be `pass` or an accepted `watch` with a named owner.",
            (
                "- Every control row must be `pass`; unclear pause, back, help, save, "
                "or menu behavior is a blocker."
            ),
            "- Every scene row must be `pass` before adding more animation layers.",
            (
                "- Every game-feel row must be `pass`; unclear success, blocked, "
                "or impact feedback is a blocker."
            ),
            (
                "- Keep generated PNGs and local readiness reports out of git; commit only "
                "source, tests, and docs."
            ),
            (
                "- The completed report must include every automated gate, every window/motion "
                "cell, every control row, every scene row, and every game-feel row as `pass`."
            ),
            (
                "- Run `validate-animation-playtest-report` after filling the report; "
                "fail means no presentation signoff."
            ),
            "",
            "## Required Report Sections",
            "",
            "| Section | Required Rows Or Fields |",
            "| --- | --- |",
            (
                "| Build | "
                f"{', '.join(REQUIRED_ANIMATION_PLAYTEST_BUILD_FIELDS)}, Release decision |"
            ),
            (
                "| Automated Gate Summary | "
                f"{', '.join(REQUIRED_ANIMATION_PLAYTEST_AUTOMATED_GATES)} |"
            ),
            (
                "| Window Matrix | "
                + ", ".join(f"{width}x{height}" for width, height in report.windows)
                + " across Full, Reduced, and Off |"
            ),
            (
                "| Control Clarity Results | "
                f"{', '.join(area for area, _ in report.control_checks)} |"
            ),
            f"| Scene Results | {', '.join(scene for scene, _ in report.scene_checks)} |",
            f"| Game Feel Results | {', '.join(area for area, _ in report.feedback_checks)} |",
            (f"| Release Blockers + Decision | {', '.join(release_blocker_fields)} |"),
            "",
            "## Matrix Cells",
            "",
            "| Scenario | Seed | Status | Baseline | Failed Areas | Advisory Gaps |",
            "| --- | ---: | --- | --- | --- | ---: |",
        ]
    )
    for cell in matrix.cells:
        failed_areas = ", ".join(cell.failed_areas) if cell.failed_areas else "-"
        lines.append(
            "| "
            f"`{cell.scenario_id}` | "
            f"`{cell.seed}` | "
            f"`{cell.status}` | "
            f"`{cell.visual_baseline}` | "
            f"{failed_areas} | "
            f"`{len(cell.advisory_gaps)}` |"
        )
    lines.extend(
        [
            "",
            "## Manual Result",
            "",
            "- Tester:",
            "- Date:",
            "- Platform:",
            "- Release decision: `pass` / `watch` / `fail`",
            "- Blockers:",
            "- Follow-up fixes:",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_2d_animation_playtest_report_template(
    output_path: Path,
    *,
    version: str,
    commit: str = "",
    tester: str = "",
    platform: str = "",
    date: str = "",
    prefill_automated_gates: bool = False,
) -> None:
    """Write the strict manual signoff report skeleton used by the validator."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    def field(value: str) -> str:
        return value.strip() if value.strip() else "fill-me"

    lines = [
        "# Animation Playtest Report",
        "",
        (
            "This draft is intentionally incomplete. Replace every `todo` and `fill-me` "
            "after the real open-window playtest, then run "
            "`validate-animation-playtest-report` before presentation signoff."
        ),
        "",
        "## Build",
        "",
        f"- Version: {field(version)}",
        f"- Commit: {field(commit)}",
        f"- Tester: {field(tester)}",
        f"- Date: {field(date)}",
        f"- Platform: {field(platform)}",
        "",
        "## Automated Gate Summary",
        "",
        "| Gate | Result | Notes |",
        "| --- | --- | --- |",
    ]
    for gate in REQUIRED_ANIMATION_PLAYTEST_AUTOMATED_GATES:
        if prefill_automated_gates:
            lines.append(f"| {gate} | `pass` | Verified by local or CI preflight evidence |")
        else:
            lines.append(f"| {gate} | `todo` | Record command output or CI artifact evidence |")

    lines.extend(
        [
            "",
            "## Window Matrix",
            "",
            "| Window | Full | Reduced | Off | Notes |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for width, height in DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS:
        window_size = f"{width}x{height}"
        lines.append(
            f"| `{window_size}` | `todo` | `todo` | `todo` | "
            f"Launch with `--window-size {window_size}` and record real window notes |"
        )

    lines.extend(
        [
            "",
            "## Control Clarity Results",
            "",
            "| Control Area | Result | Notes | Follow-up |",
            "| --- | --- | --- | --- |",
        ]
    )
    for area, required_check in DEFAULT_OPEN_WINDOW_PLAYTEST_CONTROL_CHECKS:
        lines.append(f"| {area} | `todo` | {required_check} | owner/date if not pass |")

    lines.extend(
        [
            "",
            "## Scene Results",
            "",
            "| Scene | Result | Readability Notes | Motion Notes | Follow-up |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for scene, required_check in DEFAULT_OPEN_WINDOW_PLAYTEST_SCENE_CHECKS:
        lines.append(
            f"| {scene} | `todo` | {required_check} | Motion notes | owner/date if not pass |"
        )

    lines.extend(
        [
            "",
            "## Game Feel Results",
            "",
            "| Feedback Area | Result | Notes | Follow-up |",
            "| --- | --- | --- | --- |",
        ]
    )
    for area, required_check in DEFAULT_OPEN_WINDOW_PLAYTEST_FEEDBACK_CHECKS:
        lines.append(f"| {area} | `todo` | {required_check} | owner/date if not pass |")

    lines.extend(["", "## Release Blockers", ""])
    for label in REQUIRED_ANIMATION_PLAYTEST_BLOCKER_FIELDS:
        lines.append(f"- {label}: todo")

    lines.extend(
        [
            "",
            "## Decision",
            "",
            "- Release decision: `pass` / `watch` / `fail`",
        ]
    )
    for label in REQUIRED_ANIMATION_PLAYTEST_DECISION_FIELDS:
        lines.append(f"- {label}: todo")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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


def _build_long_session_motion_cell(motion_report: MotionAuditReport) -> AnimationCoverageCell:
    max_before = max((cell.long_run_before_pulses for cell in motion_report.cells), default=0)
    max_after = max((cell.long_run_after_pulses for cell in motion_report.cells), default=0)
    min_recovery = min(
        (cell.long_run_before_pulses - cell.long_run_after_pulses for cell in motion_report.cells),
        default=0,
    )
    max_average_frame = max((cell.average_frame_ms for cell in motion_report.cells), default=0.0)
    max_frame_spike = max((cell.max_frame_ms for cell in motion_report.cells), default=0.0)
    status = (
        "pass"
        if max_after <= 18 and max_average_frame <= 24.0 and max_frame_spike <= 50.0
        else "fail"
    )
    active_layers = (
        f"before:{max_before}",
        f"after:{max_after}",
        f"recovered:{min_recovery}",
        f"avg-frame:{max_average_frame:.2f}ms",
        f"max-frame:{max_frame_spike:.2f}ms",
    )
    notes = (
        f"long-run pulses cooled to {max_after} after dense stress"
        if status == "pass"
        else (
            f"long-run after {max_after}, avg {max_average_frame:.2f} ms, "
            f"max {max_frame_spike:.2f} ms"
        )
    )
    return AnimationCoverageCell(
        area="Long Session Motion Stress",
        required_layers=("long-run-pulse-recovery", "frame-budget", "stress-cooldown"),
        active_layers=active_layers,
        status=status,
        notes=notes,
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


def _build_motion_mode_differentiation_cell(
    motion_report: MotionAuditReport,
    reduced_motion_report: MotionAuditReport,
    off_motion_report: MotionAuditReport,
) -> AnimationCoverageCell:
    full_active = max(
        (_animation_active_sample_count(cell) for cell in motion_report.cells),
        default=0,
    )
    reduced_active = max(
        (_animation_active_sample_count(cell) for cell in reduced_motion_report.cells),
        default=0,
    )
    off_active = max(
        (_animation_active_sample_count(cell) for cell in off_motion_report.cells),
        default=0,
    )
    full_residual = _max_residual_motion_pulses(motion_report)
    reduced_residual = _max_residual_motion_pulses(reduced_motion_report)
    off_residual = _max_residual_motion_pulses(off_motion_report)

    findings: list[str] = []
    if motion_report.status != "pass":
        findings.append(f"full status {motion_report.status}")
    if reduced_motion_report.status != "pass":
        findings.append(f"reduced status {reduced_motion_report.status}")
    if off_motion_report.status != "pass":
        findings.append(f"off status {off_motion_report.status}")
    if full_active <= 0:
        findings.append("full mode has no active motion samples")
    if reduced_active <= 0:
        findings.append("reduced mode lost all state-change motion")
    reduced_overrun = reduced_active - full_active
    if reduced_overrun > MAX_REDUCED_ACTIVE_SAMPLE_OVERRUN:
        findings.append(f"reduced active {reduced_active}>{full_active}")
    if off_active > 0 or off_residual > 0:
        findings.append(f"off still active {off_active}/{off_residual}")

    active_layers = (
        f"full-active:{full_active}",
        f"reduced-active:{reduced_active}",
        f"reduced-active-overrun:{reduced_overrun}",
        f"off-active:{off_active}",
        f"full-residual:{full_residual}",
        f"reduced-residual:{reduced_residual}",
        f"reduced-residual-delta:{reduced_residual - full_residual}",
        f"off-residual:{off_residual}",
    )
    return AnimationCoverageCell(
        area="Motion Mode Differentiation",
        required_layers=(
            "full-motion",
            "reduced-motion",
            "off-motion",
            "mode-distinction",
        ),
        active_layers=active_layers,
        status="pass" if not findings else "fail",
        notes=(
            (
                f"full {full_active}, reduced {reduced_active}, off {off_active}; "
                f"residual {full_residual}/{reduced_residual}/{off_residual}"
            )
            if not findings
            else "; ".join(findings[:4])
        ),
    )


def _build_scene_transition_handoff_cell(
    visual_report: VisualAuditReport,
    motion_report: MotionAuditReport,
    off_motion_report: MotionAuditReport,
) -> AnimationCoverageCell:
    transition_layers = tuple(
        sorted(
            {
                layer
                for cell in visual_report.cells
                for layer in cell.active_layers
                if layer == "transition" or layer.startswith("transition-key:")
            }
        )
    )
    full_transition_samples = max(
        (cell.transition_active_scenes for cell in motion_report.cells),
        default=0,
    )
    off_disabled = all(cell.transition_active_scenes == 0 for cell in off_motion_report.cells)
    active_layers = tuple(
        sorted(
            set(transition_layers)
            | {f"transition-samples:{full_transition_samples}"}
            | ({"transition-off-gate"} if off_disabled else set())
        )
    )
    missing = tuple(layer for layer in _REQUIRED_TRANSITION_KEYS if layer not in active_layers)
    status = "pass" if not missing and full_transition_samples > 0 and off_disabled else "fail"
    notes = "boot, run, summary, and review handoff transitions covered and off-mode gated"
    if missing:
        notes = f"missing {','.join(missing)}"
    elif full_transition_samples <= 0:
        notes = "motion audit did not see scene transitions"
    elif not off_disabled:
        notes = "scene transitions still active in motion-mode off"
    return AnimationCoverageCell(
        area="Scene Transition Handoff",
        required_layers=(
            *_REQUIRED_TRANSITION_KEYS,
            "transition-samples",
            "transition-off-gate",
        ),
        active_layers=active_layers,
        status=status,
        notes=notes,
    )


def _build_control_affordance_cell(visual_report: VisualAuditReport) -> AnimationCoverageCell:
    active_layers = tuple(
        sorted(
            {
                layer
                for cell in visual_report.cells
                for layer in cell.active_layers
                if layer in _REQUIRED_CONTROL_AFFORDANCE_LAYERS
                or layer.endswith("-control")
                or layer.endswith("-controls")
            }
        )
    )
    missing = tuple(
        layer for layer in _REQUIRED_CONTROL_AFFORDANCE_LAYERS if layer not in active_layers
    )
    notes = (
        "title, run, outcome, summary, review, pause, back, help, save, and flow controls covered"
    )
    if missing:
        notes = f"missing {','.join(missing)}"
    return AnimationCoverageCell(
        area="Control Affordance Coverage",
        required_layers=_REQUIRED_CONTROL_AFFORDANCE_LAYERS,
        active_layers=active_layers,
        status="pass" if not missing else "fail",
        notes=notes,
    )


def _build_control_replay_safety_cell(*, seed: int) -> AnimationCoverageCell:
    findings: list[str] = []
    active_layers: list[str] = []

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    try:
        import pygame
    except ModuleNotFoundError:
        return AnimationCoverageCell(
            area="Control Replay Safety",
            required_layers=(
                "pause-key-open",
                "pause-resume-click",
                "back-closes-overlay",
                "back-opens-pause",
                "help-key-toggle",
                "hover-hints",
                "pause-menu-return",
            ),
            active_layers=("pygame-unavailable",),
            status="fail",
            notes="pygame-ce is not installed",
        )

    from nexus_tech.frontend_2d.scenes import ClickTarget, RunScene, TitleScene
    from nexus_tech.frontend_2d.widgets import create_fonts

    pygame.init()
    pygame.font.init()
    try:
        surface = pygame.display.set_mode((960, 640), pygame.HIDDEN)
        fonts = create_fonts(pygame)
        rect = surface.get_rect()

        with TemporaryDirectory(prefix="nexus-tech-control-replay-") as tmpdir:
            coordinator = SaveLoadCoordinator(Path(tmpdir) / "control-replay.db")
            saved_slots: list[str] = []

            def save_callback(_state, _rng, slot_name):
                saved_slots.append(slot_name)

            def make_title_scene():
                return TitleScene(
                    pygame=pygame,
                    fonts=fonts,
                    state=create_new_game("NEXUS TECH", "Nexus One"),
                    rng=RandomSource(seed=seed + 100),
                    slot_name="active",
                    save_callback=save_callback,
                    coordinator=coordinator,
                    initial_mode="menu",
                    motion_mode=MotionMode.FULL,
                    entry_transition="boot_title",
                )

            def make_run_scene(*, dirty: bool = False):
                return RunScene(
                    pygame=pygame,
                    fonts=fonts,
                    state=create_new_game("NEXUS TECH", "Nexus One"),
                    rng=RandomSource(seed=seed + 101),
                    slot_name="active",
                    save_callback=save_callback,
                    dirty=dirty,
                    show_ready_event=False,
                    return_scene_factory=make_title_scene,
                    motion_mode=MotionMode.FULL,
                    entry_transition="boot_run",
                )

            pause_scene = make_run_scene()
            pause_scene.handle_event(
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p, unicode="p")
            )
            if pause_scene._pause_overlay_visible and not pause_scene.should_exit:
                active_layers.append("pause-key-open")
            else:
                findings.append("P did not open pause safely")
            pause_scene.draw(surface)
            pause_scene._dispatch_click_target(ClickTarget("pause_resume", "", rect))
            if not pause_scene._pause_overlay_visible and not pause_scene.should_exit:
                active_layers.append("pause-resume-click")
            else:
                findings.append("Pause resume did not return to run")

            back_scene = make_run_scene()
            back_scene._set_deep_panel("finance")
            back_scene.handle_event(
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode="")
            )
            if back_scene._deep_panel_key is None and not back_scene._pause_overlay_visible:
                active_layers.append("back-closes-overlay")
            else:
                findings.append("Esc did not close the active overlay first")
            back_scene.handle_event(
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode="")
            )
            if back_scene._pause_overlay_visible and not back_scene.should_exit:
                active_layers.append("back-opens-pause")
            else:
                findings.append("Esc did not open pause after overlays were closed")

            help_scene = make_run_scene()
            help_scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1, unicode=""))
            help_opened = help_scene._help_overlay_visible and not help_scene._pause_overlay_visible
            help_scene.handle_event(
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode="")
            )
            help_closed = not help_scene._help_overlay_visible and not help_scene.should_exit
            if help_opened and help_closed:
                active_layers.append("help-key-toggle")
            else:
                findings.append("F1/Esc help overlay replay failed")

            hint_scene = make_run_scene()
            hover_expectations = (
                (ClickTarget("pause_toggle", "", rect), "open Pause"),
                (ClickTarget("run_back", "", rect), "close the current overlay"),
                (ClickTarget("open_help", "", rect), "control guide"),
                (ClickTarget("pause_save", "", rect), "save the current run"),
                (ClickTarget("pause_menu", "", rect), "return to the 2D title menu"),
                (ClickTarget("close_help", "", rect), "close Help"),
            )
            hint_misses = tuple(
                expected
                for target, expected in hover_expectations
                if expected not in hint_scene._describe_click_target(target)
            )
            if not hint_misses:
                active_layers.append("hover-hints")
            else:
                findings.append(f"missing hover copy: {','.join(hint_misses[:2])}")

            menu_scene = make_run_scene(dirty=True)
            menu_scene._set_pause_overlay_visible(True)
            menu_scene._dispatch_click_target(ClickTarget("pause_menu", "", rect))
            next_scene = menu_scene.pop_next_scene()
            if (
                isinstance(next_scene, TitleScene)
                and saved_slots
                and saved_slots[-1] == "active"
                and not menu_scene.should_exit
            ):
                active_layers.append("pause-menu-return")
                active_layers.append("pause-save-before-menu")
            else:
                findings.append("Pause menu did not save and return to title shell")
    finally:
        pygame.quit()

    required_layers = (
        "pause-key-open",
        "pause-resume-click",
        "back-closes-overlay",
        "back-opens-pause",
        "help-key-toggle",
        "hover-hints",
        "pause-menu-return",
    )
    missing = tuple(layer for layer in required_layers if layer not in active_layers)
    if missing:
        findings.append(f"missing replay layers: {','.join(missing)}")
    return AnimationCoverageCell(
        area="Control Replay Safety",
        required_layers=required_layers,
        active_layers=tuple(active_layers),
        status="pass" if not findings else "fail",
        notes=(
            "pause, resume, back, help, hover hints, save, and menu return replayed"
            if not findings
            else "; ".join(findings[:4])
        ),
    )


def _build_ui_layout_safety_cell(visual_report: VisualAuditReport) -> AnimationCoverageCell:
    target_cells = tuple(cell for cell in visual_report.cells if cell.click_target_count > 0)
    violations = tuple(
        f"{cell.scene_key}:{violation}"
        for cell in visual_report.cells
        for violation in cell.layout_violations
    )
    min_width = min((cell.min_click_target_size[0] for cell in target_cells), default=0)
    min_height = min((cell.min_click_target_size[1] for cell in target_cells), default=0)
    actor_clear = all(
        not any(violation.startswith("actor:") for violation in cell.layout_violations)
        for cell in visual_report.cells
    )
    findings: list[str] = []
    if not target_cells:
        findings.append("missing click target captures")
    if violations:
        findings.extend(violations[:4])
    if min_width and min_width < MIN_CLICK_TARGET_WIDTH:
        findings.append(f"min target width {min_width}<{MIN_CLICK_TARGET_WIDTH}")
    if min_height and min_height < MIN_CLICK_TARGET_HEIGHT:
        findings.append(f"min target height {min_height}<{MIN_CLICK_TARGET_HEIGHT}")
    if not actor_clear:
        findings.append("actor/control collision")

    active_layers = (
        "layout-pass" if not violations else f"layout-violations:{len(violations)}",
        f"target-cells:{len(target_cells)}",
        f"min-target:{min_width}x{min_height}",
        "target-bounds",
        "target-size",
        "actor-control-clearance" if actor_clear else "actor-control-collision",
    )
    return AnimationCoverageCell(
        area="UI Layout Safety",
        required_layers=(
            "layout-pass",
            "target-bounds",
            "target-size",
            "actor-control-clearance",
        ),
        active_layers=active_layers,
        status="pass" if not findings else "fail",
        notes=(
            (
                f"{len(target_cells)} target captures, min target {min_width}x{min_height}, "
                "actor/control clear"
            )
            if not findings
            else "; ".join(findings[:4])
        ),
    )


def _build_typography_safety_cell(visual_report: VisualAuditReport) -> AnimationCoverageCell:
    violations = tuple(
        f"{cell.scene_key}:{violation}"
        for cell in visual_report.cells
        for violation in cell.typography_violations
    )
    fit_events = sum(cell.text_fit_count for cell in visual_report.cells)
    wrapped_clamps = sum(cell.wrapped_clamp_count for cell in visual_report.cells)
    min_ratio = min((cell.min_text_fit_ratio for cell in visual_report.cells), default=1.0)
    active_layers = (
        "text-overflow-clear" if not violations else f"text-overflow:{len(violations)}",
        f"text-fit-events:{fit_events}",
        f"wrapped-clamps:{wrapped_clamps}",
        f"min-fit-ratio:{min_ratio:.2f}",
        "button-title-fit",
        "wrapped-text-budget",
    )
    return AnimationCoverageCell(
        area="Typography Safety",
        required_layers=(
            "text-overflow-clear",
            "button-title-fit",
            "wrapped-text-budget",
        ),
        active_layers=active_layers,
        status="pass" if not violations else "fail",
        notes=(
            f"{fit_events} fitted text draws, {wrapped_clamps} wrapped clamps, "
            f"min fit ratio {min_ratio:.2f}"
            if not violations
            else "; ".join(violations[:4])
        ),
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
        "actor-pose-depth",
        "actor-off-gate",
    )
    visual_actor_layers = {
        layer
        for cell in visual_report.cells
        for layer in cell.active_layers
        if layer in {"actor-timeline", "sprite-clips", "actor-readability", "actor-pose-depth"}
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
        for layer in ("actor-timeline", "sprite-clips", "actor-readability", "actor-pose-depth")
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


def _build_actor_state_coverage_cell(visual_report: VisualAuditReport) -> AnimationCoverageCell:
    states = tuple(
        sorted(
            {
                layer.removeprefix("actor-state:")
                for cell in visual_report.cells
                for layer in cell.active_layers
                if layer.startswith("actor-state:")
            }
        )
    )
    state_set = set(states)
    active_layers = tuple(f"actor-state:{state}" for state in states)
    active_layers += tuple(
        f"state-group:{group_name}"
        for group_name, allowed_states in _ACTOR_STATE_GROUPS
        if state_set & allowed_states
    )
    findings: list[str] = []
    if len(states) < MIN_ACTOR_STATE_VARIANTS:
        findings.append(f"only {len(states)} actor states")
    for group_name, allowed_states in _ACTOR_STATE_GROUPS:
        if not state_set & allowed_states:
            findings.append(f"missing {group_name} state")
    if "blocked" not in state_set:
        findings.append("missing blocked actor reaction")

    notes = f"{len(states)} states: {','.join(states[:10])}"
    if findings:
        notes = "; ".join(findings[:4])
    return AnimationCoverageCell(
        area="Actor State Coverage",
        required_layers=(
            "state-group:baseline",
            "state-group:positive",
            "state-group:pressure",
            "actor-state:blocked",
            f"state-variants:{MIN_ACTOR_STATE_VARIANTS}",
        ),
        active_layers=active_layers,
        status="pass" if not findings else "fail",
        notes=notes,
    )


def _build_action_feedback_clarity_cell(
    visual_report: VisualAuditReport,
) -> AnimationCoverageCell:
    required_layers = (
        "action-feedback",
        "action-feedback-targets",
        "blocked-action-feedback",
        "blocked-action-reason",
        "impact-cue",
        "impact-cue-targets",
        "impact-value-label",
    )
    interesting_layers = set(required_layers)
    active_layers = tuple(
        sorted(
            {
                layer
                for cell in visual_report.cells
                for layer in cell.active_layers
                if layer in interesting_layers or layer.startswith("action-family:")
            }
        )
    )
    missing = tuple(layer for layer in required_layers if layer not in active_layers)
    status = "pass" if not missing else "fail"
    notes = "success, blocked, and impact cues expose targets, values, and reasons"
    if missing:
        notes = f"missing {','.join(missing)}"
    return AnimationCoverageCell(
        area="Action Feedback Clarity",
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


def _build_readability_guard_cell(visual_report: VisualAuditReport) -> AnimationCoverageCell:
    compact_cells = tuple(
        cell for cell in visual_report.cells if cell.width <= COMPACT_READABILITY_WIDTH
    )
    findings: list[str] = []
    if not compact_cells:
        findings.append(f"missing {COMPACT_READABILITY_WIDTH}px compact captures")

    actor_checks = 0
    overlay_checks = 0
    max_edge_density = 0.0
    for cell in compact_cells:
        max_edge_density = max(max_edge_density, cell.edge_density)
        if cell.status != "pass":
            findings.append(f"{cell.scene_key} visual {cell.notes}")
        if cell.scene_key in _READABILITY_ACTOR_SCENES:
            actor_checks += 1
            if "actor-readability" not in cell.active_layers:
                findings.append(f"{cell.scene_key} missing actor-readability")
        if cell.scene_key in _READABILITY_OVERLAY_SCENES:
            overlay_checks += 1
            if cell.edge_density > MAX_COMPACT_READABILITY_EDGE_DENSITY:
                findings.append(
                    f"{cell.scene_key} edge {cell.edge_density:.2f}>"
                    f"{MAX_COMPACT_READABILITY_EDGE_DENSITY:.2f}"
                )

    active_layers = (
        f"compact-captures:{len(compact_cells)}",
        f"actor-scenes:{actor_checks}",
        f"overlay-scenes:{overlay_checks}",
        f"max-edge:{max_edge_density:.2f}",
    )
    return AnimationCoverageCell(
        area="Readability Guard",
        required_layers=(
            "compact-viewport",
            "actor-readability",
            "overlay-density",
            "visual-status",
        ),
        active_layers=active_layers,
        status="pass" if not findings else "fail",
        notes=(
            (
                f"{len(compact_cells)} compact captures, {actor_checks} actor checks, "
                f"max edge {max_edge_density:.2f}"
            )
            if not findings
            else "; ".join(findings[:4])
        ),
    )


def _build_long_session_visual_readiness_cell(
    visual_report: VisualAuditReport,
) -> AnimationCoverageCell:
    important_cells = tuple(
        cell for cell in visual_report.cells if cell.scene_key in _LONG_SESSION_VISUAL_SCENES
    )
    compact_cells = tuple(
        cell for cell in important_cells if cell.width <= COMPACT_READABILITY_WIDTH
    )
    captured_scenes = {cell.scene_key for cell in compact_cells}
    missing_scenes = tuple(sorted(_LONG_SESSION_VISUAL_SCENES - captured_scenes))
    max_edge_density = max((cell.edge_density for cell in compact_cells), default=0.0)
    max_bright_ratio = max((cell.bright_ratio for cell in compact_cells), default=0.0)

    findings: list[str] = []
    if missing_scenes:
        findings.append(f"missing compact scenes {','.join(missing_scenes)}")
    for cell in compact_cells:
        if cell.status != "pass":
            findings.append(f"{cell.scene_key} visual {cell.notes}")
        if cell.edge_density > MAX_COMPACT_READABILITY_EDGE_DENSITY:
            findings.append(
                f"{cell.scene_key} edge {cell.edge_density:.2f}>"
                f"{MAX_COMPACT_READABILITY_EDGE_DENSITY:.2f}"
            )
        if (
            cell.scene_key in _READABILITY_ACTOR_SCENES
            and "actor-readability" not in cell.active_layers
        ):
            findings.append(f"{cell.scene_key} missing actor-readability")

    active_layers = (
        f"scenes:{len(captured_scenes)}",
        f"compact-captures:{len(compact_cells)}",
        f"max-edge:{max_edge_density:.2f}",
        f"max-bright:{max_bright_ratio:.2f}",
    )
    return AnimationCoverageCell(
        area="Long Session Visual Readiness",
        required_layers=(
            "late-session-scenes",
            "compact-readability",
            "visual-health",
            "actor-readability",
        ),
        active_layers=active_layers,
        status="pass" if not findings else "fail",
        notes=(
            (
                f"{len(captured_scenes)} scenes, max edge {max_edge_density:.2f}, "
                f"bright {max_bright_ratio:.2f}"
            )
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


def _max_residual_motion_pulses(report: MotionAuditReport) -> int:
    return max(
        (
            max(
                cell.run_after_pulses,
                cell.summary_after_pulses,
                cell.title_after_pulses,
                cell.review_after_pulses,
                cell.inspector_after_pulses,
                cell.long_run_after_pulses,
            )
            for cell in report.cells
        ),
        default=0,
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
