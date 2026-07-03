"""High-level 2D animation completeness audit."""

from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

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
MENU_ROUTE_EVIDENCE_TERMS: tuple[str, ...] = (
    "title",
    "wizard",
    "save",
    "archive",
    "meta",
    "hover",
    "text",
)
PLAY_ROUTE_EVIDENCE_TERMS: tuple[str, ...] = (
    "dashboard",
    "action",
    "pending",
    "inspector",
    "endgame",
    "summary",
    "pause",
    "motion",
)
WINDOW_MATRIX_EVIDENCE_TERMS: tuple[str, ...] = (
    "menu",
    "play",
    "primary",
    "disabled",
    "layout",
    "motion",
)
CONTROL_EVIDENCE_TERMS: dict[str, tuple[str, ...]] = {
    "Pause / Resume": ("pause", "resume", "run"),
    "Back / Escape": ("escape", "overlay", "pause"),
    "Menu Return": ("menu", "save", "title"),
    "Help / Hover": ("help", "hover", "controls"),
    "Control Replay Safety": ("replay", "pause", "help", "save", "menu"),
    "Control Affordance Coverage": ("click", "title", "run", "pause", "save", "flow"),
    "UI Layout Safety": ("target", "bounds", "actor", "collision"),
    "Typography Safety": ("label", "text", "fit"),
    "Motion Modes": ("full", "reduced", "off", "controls"),
}
SCENE_READABILITY_EVIDENCE_TERMS: dict[str, tuple[str, ...]] = {
    "Title/Menu": ("wizard", "save", "visible"),
    "Live Dashboard": ("stat", "product", "legible"),
    "Action Picker": ("picker", "option", "text"),
    "Pending Event": ("option", "text", "readable"),
    "Inspector": ("selected", "row", "pager"),
    "Endgame Board": ("path", "fix", "button"),
    "Turn Summary": ("timeline", "card", "readable"),
    "Outcome/Review": ("action", "note", "visible"),
    "Scene Handoffs": ("navigation", "context", "visible"),
}
SCENE_MOTION_EVIDENCE_TERMS: dict[str, tuple[str, ...]] = {
    "Title/Menu": ("title", "actor", "label"),
    "Live Dashboard": ("actor", "control", "cover"),
    "Action Picker": ("choreography", "target", "lane"),
    "Pending Event": ("preview", "motion", "choice"),
    "Inspector": ("actor", "routing", "chip"),
    "Endgame Board": ("cockpit", "motion", "control"),
    "Turn Summary": ("reveal", "pacing", "metric"),
    "Outcome/Review": ("outcome", "cinematic", "focal"),
    "Scene Handoffs": ("transition", "oriented", "control"),
}
FEEDBACK_EVIDENCE_TERMS: dict[str, tuple[str, ...]] = {
    "Success Feedback": ("success", "target", "changed"),
    "Blocked Feedback": ("blocked", "prerequisite", "reason"),
    "Impact Values": ("delta", "target", "value"),
    "Actor + Feedback Match": ("actor", "pose", "family"),
}
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
_ROUTE_BATCH_RESULT_DECISION_ROWS: tuple[tuple[str, str, str, str], ...] = (
    (
        "pass",
        "No defect trigger applies after the visible command.",
        "Keep --result pass and replace notes with observed evidence.",
        "Do not use generic ok/pass wording.",
    ),
    (
        "watch",
        "Issue is visible but task remains playable/readable.",
        "Change recorder to --result watch and name the follow-up risk.",
        "Keep release gate manual-required until accepted or fixed.",
    ),
    (
        "fail",
        "UI, navigation, readability, or motion blocks the task/signoff.",
        "Change recorder to --result fail and keep the blocker open.",
        "Fix before release, rerun visible command, then record new evidence.",
    ),
)
_ROUTE_BATCH_DEFECT_TRIGGER_ROWS: tuple[tuple[str, str, str, str], ...] = (
    (
        "Layout containment",
        "Text, cards, or actor motion touches another region but the route remains usable.",
        "Text/control is clipped, unreadable, or covers a required action.",
        "Record watch/fail and name the scene plus control.",
    ),
    (
        "Navigation recovery",
        "Pause/back/menu/help affordance is visible but unclear or slow to discover.",
        "Player cannot pause, back out, return to menu, save, or understand a disabled action.",
        "Record control evidence before closing the batch.",
    ),
    (
        "Motion readability",
        "Motion distracts or competes but labels remain readable.",
        "Animation covers text, controls, feedback, or the decision target.",
        "Rerun in full/reduced/off and record the affected mode.",
    ),
    (
        "Feedback clarity",
        "Outcome is visible but target, metric, or reason needs clearer copy.",
        "Success, blocked, or impact feedback does not identify the target, value, or reason.",
        "Attach route notes to the matching feedback row.",
    ),
    (
        "Evidence quality",
        "Observation lacks one required term or needs a stronger note.",
        "Notes are generic or recorder placeholders remain.",
        "Do not run final validation until notes name observed behavior.",
    ),
)
_ROUTE_BATCH_DEFECT_INTAKE_ROWS: tuple[tuple[str, str], ...] = (
    (
        "Severity",
        "Choose P0 for blocked navigation/readability, P1 for risky but playable, P2 for polish.",
    ),
    (
        "Reproduction",
        "Copy the visible command, expected result, actual result, window, route, and motion mode.",
    ),
    (
        "Evidence",
        "Name the affected UI element, defect trigger, and required evidence terms seen on screen.",
    ),
    (
        "Recorder action",
        "Change the route/window recorder to watch or fail; never keep pass for an open blocker.",
    ),
    (
        "Follow-up",
        "Assign fix-or-accept decision before rerunning the visible command and validator.",
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
REQUIRED_ANIMATION_PLAYTEST_SECTIONS: tuple[str, ...] = (
    "Build",
    "Automated Gate Summary",
    "Window Matrix",
    "Visible Route Evidence",
    "Control Clarity Results",
    "Scene Results",
    "Game Feel Results",
    "Release Blockers",
    "Decision",
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
    visible_route: tuple[AnimationPlaytestCommand, ...]

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


@dataclass(frozen=True)
class AnimationPlaytestReportRecord:
    """Result for one safe manual evidence update in the playtest report."""

    path: str
    section: str
    target: str
    result: str


@dataclass(frozen=True)
class AnimationPlaytestRecorderHint:
    """Next safe recorder command for a manual animation report."""

    status: str
    area: str
    target: str
    recorder_command: str
    evidence_prompt: str
    required_terms: tuple[str, ...] = ()
    visible_command: str = ""


@dataclass(frozen=True)
class AnimationPlaytestRecorderQueueValidation:
    """Validation result for an exported recorder queue artifact."""

    path: str
    expected_count: int
    findings: tuple[str, ...]

    @property
    def status(self) -> str:
        """Return pass only when the recorder queue matches current artifacts."""

        return "pass" if not self.findings else "fail"


@dataclass(frozen=True)
class AnimationPlaytestRouteBatchPlanValidation:
    """Validation result for an exported visible-route batch artifact."""

    path: str
    expected_batches: int
    expected_route_rows: int
    findings: tuple[str, ...]

    @property
    def status(self) -> str:
        """Return pass only when the route-batch artifact matches current gaps."""

        return "pass" if not self.findings else "fail"


@dataclass(frozen=True)
class AnimationPlaytestSessionValidation:
    """Validation result for a complete manual animation handoff package."""

    report: AnimationPlaytestReportValidation
    commands: AnimationPlaytestCommandQueueValidation
    plan: AnimationPlaytestPlanArtifactValidation
    recorder_queue: AnimationPlaytestRecorderQueueValidation
    route_batches: AnimationPlaytestRouteBatchPlanValidation | None = None

    @property
    def findings(self) -> tuple[str, ...]:
        """Return artifact findings that block handoff before manual testing."""

        route_batch_findings = (
            ()
            if self.route_batches is None
            else tuple(f"route batches: {finding}" for finding in self.route_batches.findings)
        )
        return (
            tuple(f"command queue: {finding}" for finding in self.commands.findings)
            + tuple(f"plan artifact: {finding}" for finding in self.plan.findings)
            + tuple(f"recorder queue: {finding}" for finding in self.recorder_queue.findings)
            + route_batch_findings
        )

    @property
    def artifact_status(self) -> str:
        """Return pass when every generated handoff artifact is current."""

        return "pass" if not self.findings else "fail"

    @property
    def handoff_status(self) -> str:
        """Return the current handoff state without completing manual signoff."""

        if self.artifact_status != "pass":
            return "blocked"
        if self.report.status != "pass":
            return "manual-required"
        return "pass"


@dataclass(frozen=True)
class AnimationPlaytestHandoff:
    """One generated manual-animation handoff sheet."""

    session: AnimationPlaytestSessionValidation
    plan: AnimationPlaytestReadinessPlan
    recorder_hint: AnimationPlaytestRecorderHint

    @property
    def status(self) -> str:
        """Return the handoff status from the validated package."""

        return self.session.handoff_status


@dataclass(frozen=True)
class AnimationPlaytestRouteBatchItem:
    """One visible route command paired with its manual recorder hint."""

    step: int
    target: str
    window_size: str
    motion_mode: str
    status: str
    visible_command: str
    recorder_command: str
    evidence_prompt: str
    required_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class AnimationPlaytestRouteBatch:
    """One window-sized batch for the manual visible-route pass."""

    batch_number: int
    window_size: str
    items: tuple[AnimationPlaytestRouteBatchItem, ...]
    window_recorder_hint: AnimationPlaytestRecorderHint | None = None

    @property
    def open_items(self) -> int:
        """Return incomplete route/window evidence rows in this batch."""

        route_open_items = sum(1 for item in self.items if item.status != "pass")
        window_open_items = (
            1
            if self.window_recorder_hint is not None and self.window_recorder_hint.status != "pass"
            else 0
        )
        return route_open_items + window_open_items

    @property
    def status(self) -> str:
        """Return pass only when this visible-window batch has no open rows."""

        return "pass" if self.open_items == 0 else "manual-required"


@dataclass(frozen=True)
class AnimationPlaytestRouteBatchPlan:
    """Manual visible-route batches derived from the current QA artifacts."""

    report: AnimationPlaytestReportValidation
    commands: AnimationPlaytestCommandQueueValidation
    batches: tuple[AnimationPlaytestRouteBatch, ...]
    scenario_id: str = "founder_journey"
    seed: int = 7
    command_prefix: str = "uv run nexus-tech"

    @property
    def status(self) -> str:
        """Return the route-batch handoff status without completing signoff."""

        if self.commands.status != "pass":
            return "blocked"
        if self.report.status != "pass":
            return "manual-required"
        return "pass"

    @property
    def route_open_items(self) -> int:
        """Return open visible-route and window-matrix rows covered by batches."""

        return sum(batch.open_items for batch in self.batches)

    @property
    def open_item_count(self) -> int:
        """Return all unresolved command/report findings."""

        return len(self.report.findings) + len(self.commands.findings)


@dataclass(frozen=True)
class AnimationPlaytestUITriageItem:
    """One manual UI/animation issue lane that still needs human review or repair."""

    step: int
    priority: str
    area: str
    lane: str
    status: str
    open_items: int
    required_evidence: str
    next_action: str


@dataclass(frozen=True)
class AnimationPlaytestUITriagePlan:
    """Structured triage backlog for manual animation and UI polish."""

    session: AnimationPlaytestSessionValidation
    items: tuple[AnimationPlaytestUITriageItem, ...]

    @property
    def status(self) -> str:
        """Return the triage state without completing manual signoff."""

        if self.session.artifact_status != "pass":
            return "blocked"
        if self.session.report.status != "pass":
            return "manual-required"
        return "pass"

    @property
    def open_item_count(self) -> int:
        """Return unresolved triage work item count."""

        return sum(item.open_items for item in self.items if item.status != "pass")

    @property
    def blocker_count(self) -> int:
        """Return unresolved P0/P1 triage lanes."""

        return sum(
            1 for item in self.items if item.status != "pass" and item.priority in {"P0", "P1"}
        )


@dataclass(frozen=True)
class AnimationPlaytestUITriageValidation:
    """Validation result for an exported manual UI triage artifact."""

    path: str
    expected_count: int
    findings: tuple[str, ...]

    @property
    def status(self) -> str:
        """Return pass only when the triage artifact matches current handoff state."""

        return "pass" if not self.findings else "fail"


@dataclass(frozen=True)
class AnimationPlaytestReleaseGateCheck:
    """One release-readiness check for the manual animation gate."""

    name: str
    status: str
    blocker_count: int
    next_action: str


@dataclass(frozen=True)
class AnimationPlaytestReleaseGate:
    """Final release gate for the current manual animation QA package."""

    session: AnimationPlaytestSessionValidation
    triage: AnimationPlaytestUITriagePlan
    triage_validation: AnimationPlaytestUITriageValidation
    recorder_hint: AnimationPlaytestRecorderHint
    checks: tuple[AnimationPlaytestReleaseGateCheck, ...]

    @property
    def artifact_status(self) -> str:
        """Return pass only when all generated handoff artifacts are current."""

        if self.session.artifact_status != "pass" or self.triage_validation.status != "pass":
            return "fail"
        return "pass"

    @property
    def manual_result(self) -> str:
        """Return whether the human visible-window pass has completed."""

        return "complete" if self.session.report.status == "pass" else "not completed by automation"

    @property
    def status(self) -> str:
        """Return release readiness without faking manual playtest evidence."""

        if self.artifact_status != "pass":
            return "blocked"
        if self.session.report.status != "pass" or self.triage.blocker_count:
            return "manual-required"
        return "pass"

    @property
    def blocking_check_count(self) -> int:
        """Return how many release checks still block or require manual evidence."""

        return sum(1 for check in self.checks if check.status != "pass")


@dataclass(frozen=True)
class AnimationPlaytestReleaseGateValidation:
    """Validation result for an exported animation release-gate artifact."""

    path: str
    expected_count: int
    findings: tuple[str, ...]

    @property
    def status(self) -> str:
        """Return pass only when the release-gate artifact is current."""

        return "pass" if not self.findings else "fail"


@dataclass(frozen=True)
class AnimationPlaytestProgressLane:
    """One progress lane for the manual animation QA board."""

    area: str
    status: str
    total_items: int
    open_items: int
    next_action: str

    @property
    def completed_items(self) -> int:
        """Return completed work items without allowing negative counts."""

        return max(0, self.total_items - self.open_items)

    @property
    def completion_percent(self) -> int:
        """Return a whole-number completion percentage for this lane."""

        if self.total_items <= 0:
            return 100
        return round(self.completed_items * 100 / self.total_items)


@dataclass(frozen=True)
class AnimationPlaytestProgressBoard:
    """Manual animation QA progress board derived from current artifacts."""

    release_gate: AnimationPlaytestReleaseGate
    lanes: tuple[AnimationPlaytestProgressLane, ...]

    @property
    def status(self) -> str:
        """Return release status without completing manual evidence."""

        return self.release_gate.status

    @property
    def total_item_count(self) -> int:
        """Return all tracked progress items across lanes."""

        return sum(lane.total_items for lane in self.lanes)

    @property
    def open_item_count(self) -> int:
        """Return unresolved work items across progress lanes."""

        return sum(lane.open_items for lane in self.lanes)

    @property
    def completed_item_count(self) -> int:
        """Return completed work items across progress lanes."""

        return sum(lane.completed_items for lane in self.lanes)

    @property
    def completion_percent(self) -> int:
        """Return weighted progress completion across all lanes."""

        if self.total_item_count <= 0:
            return 100
        return round(self.completed_item_count * 100 / self.total_item_count)


@dataclass(frozen=True)
class AnimationPlaytestProgressBoardValidation:
    """Validation result for an exported animation progress board artifact."""

    path: str
    expected_count: int
    findings: tuple[str, ...]

    @property
    def status(self) -> str:
        """Return pass only when the progress board matches current artifacts."""

        return "pass" if not self.findings else "fail"


@dataclass(frozen=True)
class AnimationPlaytestExecutionGuide:
    """Operator guide for completing manual animation QA from current artifacts."""

    progress: AnimationPlaytestProgressBoard
    recorder_steps: tuple[AnimationPlaytestRecorderHint, ...]
    progress_path: str
    scenario_id: str
    seed: int
    command_prefix: str

    @property
    def status(self) -> str:
        """Return the current manual QA status."""

        return self.progress.status

    @property
    def open_step_count(self) -> int:
        """Return recorder steps that still require manual action."""

        return sum(1 for step in self.recorder_steps if step.status != "pass")


@dataclass(frozen=True)
class AnimationPlaytestExecutionGuideValidation:
    """Validation result for an exported manual animation execution guide."""

    path: str
    expected_count: int
    findings: tuple[str, ...]

    @property
    def status(self) -> str:
        """Return pass only when the execution guide matches current artifacts."""

        return "pass" if not self.findings else "fail"


@dataclass(frozen=True)
class AnimationPlaytestIssue:
    """One manual animation QA item that still needs evidence or a fix."""

    priority: str
    status: str
    area: str
    target: str
    result: str
    evidence: str
    follow_up: str
    next_action: str


@dataclass(frozen=True)
class AnimationPlaytestIssueBacklog:
    """Backlog derived from the current manual animation playtest report."""

    report: AnimationPlaytestReportValidation
    issues: tuple[AnimationPlaytestIssue, ...]

    @property
    def status(self) -> str:
        """Return blocked when fixes are known, otherwise mirror evidence state."""

        if any(issue.priority == "P0" for issue in self.issues):
            return "blocked"
        if self.issues:
            return "manual-required"
        return "pass"

    @property
    def issue_count(self) -> int:
        """Return total open backlog items."""

        return len(self.issues)

    @property
    def p0_count(self) -> int:
        """Return release-blocking fix count."""

        return sum(1 for issue in self.issues if issue.priority == "P0")

    @property
    def p1_count(self) -> int:
        """Return watch item count."""

        return sum(1 for issue in self.issues if issue.priority == "P1")

    @property
    def p2_count(self) -> int:
        """Return missing-evidence item count."""

        return sum(1 for issue in self.issues if issue.priority == "P2")


@dataclass(frozen=True)
class AnimationPlaytestIssueBacklogValidation:
    """Validation result for an exported manual animation issue backlog."""

    path: str
    expected_count: int
    findings: tuple[str, ...]

    @property
    def status(self) -> str:
        """Return pass only when the backlog matches the current report."""

        return "pass" if not self.findings else "fail"


@dataclass(frozen=True)
class AnimationPlaytestSprintPacket:
    """One focused manual QA sprint derived from the current animation package."""

    execution_guide: AnimationPlaytestExecutionGuide
    issue_backlog: AnimationPlaytestIssueBacklog
    execution_guide_path: str
    issue_backlog_path: str
    observation_steps: tuple[AnimationPlaytestRecorderHint, ...]
    blocker_issues: tuple[AnimationPlaytestIssue, ...]
    max_observation_steps: int

    @property
    def status(self) -> str:
        """Return the current sprint status without completing manual evidence."""

        return self.execution_guide.status

    @property
    def open_observation_count(self) -> int:
        """Return visible/manual observation steps included in this sprint."""

        return len(self.observation_steps)

    @property
    def next_observation(self) -> AnimationPlaytestRecorderHint | None:
        """Return the next manual observation row for this sprint."""

        return self.observation_steps[0] if self.observation_steps else None

    @property
    def blocker_count(self) -> int:
        """Return P0/P1 issue count carried into this sprint."""

        return len(self.blocker_issues)

    @property
    def checklist_count(self) -> int:
        """Return manual acceptance checks included in the sprint."""

        return len(_ANIMATION_SPRINT_OBSERVATION_CHECKS)

    @property
    def execution_batches(self) -> tuple[tuple[str, str, str, str], ...]:
        """Return ordered manual execution batches for the sprint."""

        return _ANIMATION_SPRINT_EXECUTION_BATCHES

    @property
    def execution_batch_count(self) -> int:
        """Return manual execution batches included in the sprint."""

        return len(self.execution_batches)

    @property
    def layout_repair_count(self) -> int:
        """Return layout repair checks included in the sprint."""

        return len(_ANIMATION_SPRINT_LAYOUT_REPAIR_ROWS)

    @property
    def layout_recording_count(self) -> int:
        """Return layout recorder rows included in the sprint."""

        return len(_ANIMATION_SPRINT_LAYOUT_RECORDING_ROWS)

    @property
    def navigation_drill_count(self) -> int:
        """Return recovery navigation drills included in the sprint."""

        return len(_ANIMATION_SPRINT_NAVIGATION_RECOVERY_DRILLS)

    @property
    def navigation_recording_count(self) -> int:
        """Return navigation recorder rows included in the sprint."""

        return len(_ANIMATION_SPRINT_NAVIGATION_RECORDING_ROWS)

    @property
    def defect_intake_count(self) -> int:
        """Return manual defect intake rows included in the sprint."""

        return len(_ANIMATION_SPRINT_DEFECT_INTAKE_ROWS)

    @property
    def exit_criteria_count(self) -> int:
        """Return sprint closure checks included in the sprint."""

        return len(_ANIMATION_SPRINT_EXIT_CRITERIA)

    @property
    def evidence_capture_count(self) -> int:
        """Return evidence capture prompt rows included in the sprint."""

        return len(self.observation_steps)

    @property
    def evidence_template_count(self) -> int:
        """Return evidence note templates included in the sprint."""

        return len(_ANIMATION_SPRINT_EVIDENCE_NOTE_TEMPLATES)


@dataclass(frozen=True)
class AnimationPlaytestSprintPacketValidation:
    """Validation result for an exported manual animation sprint packet."""

    path: str
    expected_observation_count: int
    expected_blocker_count: int
    findings: tuple[str, ...]

    @property
    def status(self) -> str:
        """Return pass only when the sprint packet matches current artifacts."""

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
        "Manual Route Evidence",
        ("visible route",),
        "Run every visible test route step and record observed notes for each menu/play launch.",
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
        ("todo cells", "blank table cells", "draft warning", "follow-up placeholder"),
        "Replace template placeholders with pass/watch/fail and real tester notes.",
    ),
)

_MANUAL_ANIMATION_EVIDENCE_CHECKLIST: tuple[tuple[str, str], ...] = (
    (
        "Window Matrix Evidence",
        (
            "Record 820x620, 960x640, and 1440x900 in full, reduced, and off "
            "with notes for primary actions, disabled reasons, layout collisions, "
            "and motion-mode behavior."
        ),
    ),
    (
        "Route Evidence Notes",
        (
            "Complete all 18 visible menu/play route rows with target-specific notes: "
            "menu covers title, wizard, save, archive, meta, hover, and text; play "
            "covers dashboard, action, pending, inspector, endgame, summary, pause, "
            "and motion."
        ),
    ),
    (
        "Control Evidence",
        (
            "Verify pause/resume, back/escape, menu return, help/hover, replay safety, "
            "affordance coverage, layout safety, typography safety, and motion modes."
        ),
    ),
    (
        "Scene Evidence",
        (
            "Review title/menu, dashboard, action picker, pending event, inspector, "
            "endgame board, turn summary, outcome/review, and scene handoffs."
        ),
    ),
    (
        "Game Feel Evidence",
        (
            "Confirm success, blocked, impact-value, and actor-feedback cues are readable, "
            "aligned with the event, and not hidden by animation."
        ),
    ),
    (
        "Signoff Evidence",
        (
            "Fill blocker fields, required fixes, nice-to-have polish, validator result, "
            "and final release decision after the report validator passes."
        ),
    ),
)

_MANUAL_ANIMATION_RUNBOOK_STEPS: tuple[tuple[str, str, str], ...] = (
    (
        "Refresh Artifacts",
        (
            "Run prepare-animation-playtest-session with prefilled automated gates, "
            "then validate the command queue and playtest plan."
        ),
        "Report, command queue, and plan artifacts are current and plan validation passes.",
    ),
    (
        "Execute Visible Windows",
        (
            "Run all 18 visible menu/play commands in order across 820x620, 960x640, "
            "and 1440x900 in full, reduced, and off motion modes."
        ),
        "Every visible route row has observed notes from a real open-window run.",
    ),
    (
        "Fill Evidence Notes",
        (
            "Replace todo cells and prompt text with window, control, scene, game-feel, "
            "route, blocker, and decision observations."
        ),
        "Generic notes are gone and each required evidence term remains represented.",
    ),
    (
        "Validate Signoff",
        (
            "Run validate-animation-playtest-report and attach the passing report before "
            "calling animation complete."
        ),
        "Release decision is pass and the final report validator returns PASS.",
    ),
)

_ANIMATION_UI_TRIAGE_PROFILES: dict[str, tuple[str, str, str]] = {
    "Command Queue": (
        "P0",
        "Artifact Hygiene",
        "Queue rows, route commands, and evidence prompts match the current build.",
    ),
    "Manual Window Matrix": (
        "P0",
        "Responsive Layout",
        (
            "820x620, 960x640, and 1440x900 notes cover layout, motion, "
            "primary actions, and disabled states."
        ),
    ),
    "Manual Route Evidence": (
        "P0",
        "Route Flow Coverage",
        "All 18 menu/play route notes cover target-specific visible evidence after real runs.",
    ),
    "Manual Control Checks": (
        "P0",
        "Controls / Navigation",
        (
            "Pause, resume, back, menu return, help, hover, and shortcut behavior "
            "are observed and readable."
        ),
    ),
    "Manual Scene Checks": (
        "P1",
        "Scene Readability",
        (
            "Title, dashboard, picker, pending event, inspector, endgame, summary, "
            "and review scenes stay readable."
        ),
    ),
    "Manual Game Feel": (
        "P1",
        "Motion / Feedback",
        (
            "Success, blocked, impact, and actor feedback cues match the same outcome "
            "without hiding controls."
        ),
    ),
    "Manual Evidence Notes": (
        "P2",
        "Evidence Quality",
        "Notes are specific observed facts, not generic ok/clear/readable placeholders.",
    ),
    "Signoff Fields": (
        "P0",
        "Release Decision",
        "Blockers, required fixes, validator result, and release decision are explicit and final.",
    ),
    "Template Cleanup": (
        "P2",
        "Report Hygiene",
        "Todo cells, blank cells, draft warnings, and follow-up placeholders are removed.",
    ),
    "Release Signoff": (
        "PASS",
        "Release Decision",
        "Manual animation report validates and is ready to attach to presentation notes.",
    ),
}

_ANIMATION_UI_TRIAGE_POLICY_LINE = (
    "- UI policy: `layout, typography, controls, and motion issues stay open until "
    "observed evidence clears them`"
)

_ANIMATION_RELEASE_GATE_POLICY_LINE = (
    "- Release policy: `no animation release while the gate is blocked or manual-required`"
)
_ANIMATION_PROGRESS_POLICY_LINE = (
    "- Progress policy: `progress board is advisory and does not record tester evidence`"
)
_ANIMATION_EXECUTION_GUIDE_POLICY_LINE = (
    "- Execution policy: `run visible commands first; recorder placeholders require "
    "real tester observations`"
)
_ANIMATION_ISSUE_BACKLOG_POLICY_LINE = (
    "- Backlog policy: `derived from the manual report; it never replaces visible-window "
    "tester evidence`"
)
_ANIMATION_SPRINT_POLICY_LINE = (
    "- Sprint policy: `observe visible commands before recorder commands; P0/P1 blockers "
    "stay open until real evidence and validators clear them`"
)
_ANIMATION_SPRINT_OBSERVATION_CHECKS: tuple[tuple[str, str, str], ...] = (
    (
        "Layout bounds",
        "No overlapping text, clipped labels, or controls outside panels.",
        "Window size, route, panel or control names, and visible result.",
    ),
    (
        "Navigation controls",
        "Pause, back, menu, help, save, and disabled actions are discoverable.",
        "Which controls were tried and whether the response was clear.",
    ),
    (
        "Typography contrast",
        "Primary labels, disabled reasons, tooltips, and footer text stay readable.",
        "Any hard-to-read label, color pairing, or clipped copy.",
    ),
    (
        "Motion readability",
        "Full, reduced, and off modes keep state changes understandable.",
        "Mode, actor or panel motion, and whether the cue helped or distracted.",
    ),
    (
        "Evidence wording",
        "Recorder notes describe observed facts instead of generic ok/pass wording.",
        "Specific UI elements, animation cues, and blocker names.",
    ),
)
_ANIMATION_SPRINT_EXECUTION_BATCHES: tuple[tuple[str, str, str, str], ...] = (
    (
        "Artifact refresh",
        "Regenerate the session package and run artifact validators before opening windows.",
        "Sprint, guide, backlog, route batches, and release gate are current.",
        "Stop on stale artifact, command-prefix mismatch, or failing validator.",
    ),
    (
        "820x620 layout first",
        "Run 820x620 full, reduced, and off menu/play commands before larger windows.",
        "Window matrix plus responsive frame, button grid, and text containment rows.",
        "Escalate P0 on overlap, clipped controls, or controls outside panels.",
    ),
    (
        "960x640 recovery controls",
        "Run 960x640 route rows plus pause, back, menu, help, and hover drills.",
        "Pause/resume, back/escape, menu return, help/hover, and replay safety rows.",
        "Escalate P0 when recovery is hidden, destructive, or unclear.",
    ),
    (
        "1440x900 motion readability",
        "Run 1440x900 full, reduced, and off routes while comparing motion behavior.",
        "Motion modes, scene checks, game-feel rows, and motion separation evidence.",
        "Escalate P0/P1 when animation hides state, text, controls, or next decisions.",
    ),
    (
        "Report closure",
        "Rerun validators after recorder rows and update signoff only from evidence.",
        "Release blocker notes, validator result, final decision, and accepted watch risk.",
        "Keep manual-required while placeholders, P0/P1 blockers, or missing evidence remain.",
    ),
)
_ANIMATION_SPRINT_LAYOUT_REPAIR_ROWS: tuple[tuple[str, str, str, str], ...] = (
    (
        "Responsive frame",
        "820x620, 960x640, and 1440x900",
        "Panel bounds, footer rails, modal edges, and title/menu sidebars do not collide.",
        "Record fail/watch evidence before accepting any overlap or overflow.",
    ),
    (
        "Button grid",
        "Title, run, pause, inspector, endgame, summary, and review controls",
        "Primary, secondary, disabled, back, pause, help, save, and menu buttons align.",
        "Fix button placement or copy before marking the route pass.",
    ),
    (
        "Text containment",
        "Headers, cards, tooltips, disabled reasons, and footer status lines",
        "Labels stay inside their cards or intentionally truncate without hiding meaning.",
        "Capture the exact clipped or overlapping text in the defect intake row.",
    ),
    (
        "Navigation affordance",
        "Pause/back/menu/help/hover paths",
        "The player can see how to pause, back out, return to menu, and request help.",
        "Treat unclear navigation as P0 until the visible command proves recovery.",
    ),
    (
        "Motion separation",
        "Actors, pulses, overlays, transition sweeps, and feedback cards",
        "Motion cues do not cover text, controls, or the next required decision.",
        "Compare full, reduced, and off modes before deciding watch versus fail.",
    ),
)
_ANIMATION_SPRINT_LAYOUT_RECORDING_ROWS: tuple[tuple[str, str, str], ...] = (
    ("Responsive frame 820x620", "window", "820x620"),
    ("Responsive frame 960x640", "window", "960x640"),
    ("Responsive frame 1440x900", "window", "1440x900"),
    ("Button grid", "control", "Control Affordance Coverage"),
    ("Text containment", "control", "Typography Safety"),
    ("Navigation affordance", "control", "UI Layout Safety"),
    ("Motion separation", "control", "Motion Modes"),
)
_ANIMATION_SPRINT_NAVIGATION_RECOVERY_DRILLS: tuple[tuple[str, str, str, str], ...] = (
    (
        "Pause open",
        "Press P and click the Pause rail from live play.",
        "Pause overlay opens without hiding the current run context or primary recovery actions.",
        "Mark P0 if the player cannot discover pause without guessing.",
    ),
    (
        "Resume",
        "Click Resume from the pause overlay.",
        "The same run state returns and the player can identify what changed or did not change.",
        "Mark P0 if resume exits, advances, or loses visible context.",
    ),
    (
        "Back / Escape",
        "Open an overlay, press Esc, then press Esc again from the cleared run view.",
        "Esc closes overlays first, then opens pause instead of quitting or advancing the turn.",
        "Mark P0 if back behavior is destructive or ambiguous.",
    ),
    (
        "Menu return",
        "Open Pause, choose Menu, and confirm the title shell is reachable.",
        "The path back to title/menu is visible, labeled, and does not strand the player.",
        "Mark P0 until menu return is obvious and recoverable.",
    ),
    (
        "Help / hover",
        "Open help with F1 or ? and hover over primary controls.",
        (
            "Help and hover copy explain available controls without covering the button "
            "being explained."
        ),
        "Mark P1 when the control exists but the affordance copy is unclear.",
    ),
)
_ANIMATION_SPRINT_NAVIGATION_RECORDING_ROWS: tuple[tuple[str, str], ...] = (
    ("Pause open + Resume", "Pause / Resume"),
    ("Back / Escape", "Back / Escape"),
    ("Menu return", "Menu Return"),
    ("Help / hover", "Help / Hover"),
    ("Control replay safety", "Control Replay Safety"),
)
_ANIMATION_SPRINT_DEFECT_INTAKE_ROWS: tuple[tuple[str, str, str, str], ...] = (
    (
        "Text overlap, clipped labels, or controls outside panels",
        "P0",
        "Window size, route, motion mode, exact label/control, and screenshot note.",
        "Record fail evidence, fix layout before release, then rerun the visible command.",
    ),
    (
        "Pause, back, menu, help, save, or disabled action is unclear",
        "P0",
        "Control tried, expected navigation, actual response, and visible feedback.",
        "Record control evidence, fix interaction copy/state, then rerun the command.",
    ),
    (
        "Motion hides state changes or makes text hard to follow",
        "P0/P1",
        "Motion mode, actor or panel, state change, and whether reduced/off clears it.",
        "Record fail/watch evidence and tune motion before release candidate review.",
    ),
    (
        "Contrast, typography, or tooltip readability is questionable",
        "P1",
        "Text, color pairing, panel, route, and reading condition.",
        "Record watch evidence and decide fix or accepted watch risk before RC.",
    ),
    (
        "Small polish issue that does not block task completion",
        "P2",
        "Route, element, observed annoyance, and why gameplay remains usable.",
        "Record follow-up evidence; do not clear P0/P1 signoff until blockers are resolved.",
    ),
)
_ANIMATION_SPRINT_EXIT_CRITERIA: tuple[tuple[str, str, str], ...] = (
    (
        "Observation rows recorded",
        "Every visible command in this sprint has real observed notes or an explicit fail/watch.",
        "No recorder command still contains placeholder notes for completed rows.",
    ),
    (
        "Defects classified",
        "Every observed UI or animation issue is mapped to the defect intake priority.",
        "P0/P1 items stay open in the blocker queue until fixed or accepted by signoff.",
    ),
    (
        "Signoff fields updated",
        "Release blocker notes, validator result, and final pass decision are not placeholders.",
        "Report fields name either clear evidence, remaining blockers, or accepted watch risk.",
    ),
    (
        "Validation rerun",
        "Sprint, execution guide, issue backlog, and report validators are rerun after edits.",
        "The packet is regenerated when any report row, blocker, or code fix changes.",
    ),
)
_ANIMATION_SPRINT_EVIDENCE_NOTE_TEMPLATES: tuple[tuple[str, str, str, str], ...] = (
    (
        "pass",
        "Checklist passed and no defect intake trigger applies.",
        "Window size, route, motion mode, checked controls or labels, and visible cue.",
        "Observed {window} {route} in {mode}; {controls_or_labels} stayed readable; "
        "{motion_cue} made the state change clear.",
    ),
    (
        "watch",
        "Issue is visible but does not block completing the task.",
        (
            "Specific UI element, route, motion mode, why gameplay remains usable, "
            "and follow-up owner."
        ),
        (
            "Observed {window} {route} in {mode}; {element} was questionable because "
            "{reason}; gameplay remained usable because {mitigation}."
        ),
    ),
    (
        "fail",
        "P0/P1 defect blocks task completion, readability, navigation, or release signoff.",
        (
            "Exact blocker, reproduction route, expected behavior, actual behavior, "
            "and rerun condition."
        ),
        (
            "Observed {window} {route} in {mode}; expected {expected}; actual {actual}; "
            "block classified as {P0_or_P1}."
        ),
    ),
)
_RELEASE_GATE_CHECKS: frozenset[str] = frozenset(
    {
        "Session Artifacts",
        "UI Triage Artifact",
        "Manual Report Signoff",
        "P0/P1 UI Lanes",
        "Release Decision",
    }
)
_PROGRESS_BOARD_LANES: tuple[str, ...] = (
    "Automated Gates",
    "Manual Window Matrix",
    "Manual Route Evidence",
    "Manual Control Checks",
    "Manual Scene Checks",
    "Manual Game Feel",
    "Manual Evidence Notes",
    "Signoff Fields",
    "Template Cleanup",
    "Session Artifacts",
    "UI Triage Artifact",
    "P0/P1 UI Lanes",
    "Release Gate",
)
_PROGRESS_BOARD_LANE_NAMES: frozenset[str] = frozenset(_PROGRESS_BOARD_LANES)

_TEMPLATE_EVIDENCE_PROMPT_KEYS: tuple[str, ...] = (
    "pass notes must mention",
    "record command output or ci artifact evidence",
    "record title menu wizard save slot archive meta board hover and text fit observations for",
    (
        "record dashboard action picker pending event inspector endgame summary "
        "pause back and motion feel observations for"
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
    if "this draft is intentionally incomplete" in normalized:
        findings.append("report still contains draft warning text")
    if "owner/date if not pass" in normalized:
        findings.append("report still contains follow-up placeholder text")

    for section in REQUIRED_ANIMATION_PLAYTEST_SECTIONS:
        if re.search(rf"^##\s+{re.escape(section)}\s*$", text, re.MULTILINE) is None:
            findings.append(f"missing report section: {section}")

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
    _validate_required_visible_route_evidence(findings, rows)
    _validate_required_result_rows(
        findings,
        rows,
        tuple(area for area, _ in DEFAULT_OPEN_WINDOW_PLAYTEST_CONTROL_CHECKS),
        "control check",
        evidence_columns=((2, "notes"),),
        evidence_terms=CONTROL_EVIDENCE_TERMS,
    )
    _validate_required_result_rows(
        findings,
        rows,
        tuple(scene for scene, _ in DEFAULT_OPEN_WINDOW_PLAYTEST_SCENE_CHECKS),
        "scene check",
        evidence_columns=((2, "readability notes"), (3, "motion notes")),
        evidence_terms={
            (scene, "readability notes"): terms
            for scene, terms in SCENE_READABILITY_EVIDENCE_TERMS.items()
        }
        | {(scene, "motion notes"): terms for scene, terms in SCENE_MOTION_EVIDENCE_TERMS.items()},
    )
    _validate_required_result_rows(
        findings,
        rows,
        tuple(area for area, _ in DEFAULT_OPEN_WINDOW_PLAYTEST_FEEDBACK_CHECKS),
        "game-feel check",
        evidence_columns=((2, "notes"),),
        evidence_terms=FEEDBACK_EVIDENCE_TERMS,
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
            continue
        if label in REQUIRED_ANIMATION_PLAYTEST_BLOCKER_FIELDS and not _is_clear_signoff_value(
            value
        ):
            findings.append(f"blocker field is not clear: {label}")
        if label == "Required fixes before presenting" and not _is_clear_signoff_value(value):
            findings.append("required fixes before presenting are not clear")
        if label == "Validator result" and not _is_passing_result(value):
            findings.append("validator result is not pass")

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
            if finding not in matched and any(marker in finding.lower() for marker in markers)
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
    visible_route = build_2d_animation_playtest_command_queue(
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
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
        visible_route=visible_route,
    )


def build_2d_animation_playtest_recorder_hint(
    report_path: Path,
    command_path: Path,
    *,
    scenario_id: str = "founder_journey",
    seed: int = 7,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    command_prefix: str = "uv run nexus-tech",
) -> AnimationPlaytestRecorderHint:
    """Return the next manual recorder command without filling tester evidence."""

    plan = build_2d_animation_playtest_readiness_plan(
        report_path,
        command_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    if plan.commands.status != "pass":
        return AnimationPlaytestRecorderHint(
            status="blocked",
            area="Command Queue",
            target=str(command_path),
            recorder_command=(
                f"{command_prefix} animation-playtest-commands "
                f"--scenario {_shell_arg(scenario_id)} --seed {seed} "
                f"--command-prefix {_shell_arg(command_prefix)} "
                f"--output {_shell_arg(command_path)}"
            ),
            evidence_prompt="Regenerate and validate the visible-window command queue first.",
        )

    if plan.status == "pass":
        return AnimationPlaytestRecorderHint(
            status="pass",
            area="Release Signoff",
            target=str(report_path),
            recorder_command=(
                f"{command_prefix} validate-animation-playtest-report {_shell_arg(report_path)}"
            ),
            evidence_prompt="Manual animation signoff is complete; attach the passing report.",
        )

    route_hint = _build_next_route_recorder_hint(
        plan,
        report_path=report_path,
        command_prefix=command_prefix,
    )
    if route_hint is not None:
        return route_hint

    window_hint = _build_next_window_recorder_hint(
        plan.report.findings,
        report_path=report_path,
        command_prefix=command_prefix,
    )
    if window_hint is not None:
        return window_hint

    control_hint = _build_next_labeled_recorder_hint(
        plan.report.findings,
        report_path=report_path,
        command_prefix=command_prefix,
        marker="control check",
        section="Control Clarity Results",
        command_name="record-animation-playtest-control",
        option_name="--notes",
        labels=tuple(label for label, _ in DEFAULT_OPEN_WINDOW_PLAYTEST_CONTROL_CHECKS),
        evidence_terms=CONTROL_EVIDENCE_TERMS,
        evidence_prompt_prefix="Replace placeholder with observed control notes.",
    )
    if control_hint is not None:
        return control_hint

    scene_hint = _build_next_scene_recorder_hint(
        plan.report.findings,
        report_path=report_path,
        command_prefix=command_prefix,
    )
    if scene_hint is not None:
        return scene_hint

    feedback_hint = _build_next_labeled_recorder_hint(
        plan.report.findings,
        report_path=report_path,
        command_prefix=command_prefix,
        marker="game-feel check",
        section="Game Feel Results",
        command_name="record-animation-playtest-feedback",
        option_name="--notes",
        labels=tuple(label for label, _ in DEFAULT_OPEN_WINDOW_PLAYTEST_FEEDBACK_CHECKS),
        evidence_terms=FEEDBACK_EVIDENCE_TERMS,
        evidence_prompt_prefix="Replace placeholder with observed feedback notes.",
    )
    if feedback_hint is not None:
        return feedback_hint

    field_hint = _build_next_field_recorder_hint(
        plan.report.findings,
        report_path=report_path,
        command_prefix=command_prefix,
    )
    if field_hint is not None:
        return field_hint

    return AnimationPlaytestRecorderHint(
        status="manual-required",
        area="Template Cleanup",
        target=str(report_path),
        recorder_command=f"{command_prefix} animation-playtest-status {_shell_arg(report_path)}",
        evidence_prompt="Review remaining template cleanup findings, then rerun recorder-next.",
    )


def build_2d_animation_playtest_recorder_queue(
    report_path: Path,
    command_path: Path,
    *,
    scenario_id: str = "founder_journey",
    seed: int = 7,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    command_prefix: str = "uv run nexus-tech",
) -> tuple[AnimationPlaytestRecorderHint, ...]:
    """Return safe recorder commands for every currently incomplete manual row."""

    plan = build_2d_animation_playtest_readiness_plan(
        report_path,
        command_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    if plan.commands.status != "pass" or plan.status == "pass":
        return (
            build_2d_animation_playtest_recorder_hint(
                report_path,
                command_path,
                scenario_id=scenario_id,
                seed=seed,
                windows=windows,
                motion_modes=motion_modes,
                command_prefix=command_prefix,
            ),
        )

    hints: list[AnimationPlaytestRecorderHint] = []
    for route_index in _route_finding_indexes(plan.report.findings):
        if 1 <= route_index <= len(plan.visible_route):
            hints.append(
                _build_route_recorder_hint(
                    plan,
                    route_index=route_index,
                    report_path=report_path,
                    command_prefix=command_prefix,
                )
            )

    for window_size in _window_finding_labels(plan.report.findings):
        hints.append(
            _build_window_recorder_hint(
                window_size,
                report_path=report_path,
                command_prefix=command_prefix,
            )
        )

    for area in _labeled_finding_labels(
        plan.report.findings,
        labels=tuple(label for label, _ in DEFAULT_OPEN_WINDOW_PLAYTEST_CONTROL_CHECKS),
        marker="control check",
    ):
        hints.append(
            _build_labeled_recorder_hint(
                area,
                report_path=report_path,
                command_prefix=command_prefix,
                section="Control Clarity Results",
                command_name="record-animation-playtest-control",
                option_name="--notes",
                evidence_terms=CONTROL_EVIDENCE_TERMS,
                evidence_prompt_prefix="Replace placeholder with observed control notes.",
            )
        )

    for scene in _labeled_finding_labels(
        plan.report.findings,
        labels=tuple(label for label, _ in DEFAULT_OPEN_WINDOW_PLAYTEST_SCENE_CHECKS),
        marker="scene check",
    ):
        hints.append(
            _build_scene_recorder_hint(
                scene,
                report_path=report_path,
                command_prefix=command_prefix,
            )
        )

    for area in _labeled_finding_labels(
        plan.report.findings,
        labels=tuple(label for label, _ in DEFAULT_OPEN_WINDOW_PLAYTEST_FEEDBACK_CHECKS),
        marker="game-feel check",
    ):
        hints.append(
            _build_labeled_recorder_hint(
                area,
                report_path=report_path,
                command_prefix=command_prefix,
                section="Game Feel Results",
                command_name="record-animation-playtest-feedback",
                option_name="--notes",
                evidence_terms=FEEDBACK_EVIDENCE_TERMS,
                evidence_prompt_prefix="Replace placeholder with observed feedback notes.",
            )
        )

    for field_name in _field_finding_labels(plan.report.findings):
        hints.append(
            _build_field_recorder_hint(
                field_name,
                report_path=report_path,
                command_prefix=command_prefix,
            )
        )

    if hints:
        return tuple(hints)
    return (
        AnimationPlaytestRecorderHint(
            status="manual-required",
            area="Template Cleanup",
            target=str(report_path),
            recorder_command=(
                f"{command_prefix} animation-playtest-status {_shell_arg(report_path)}"
            ),
            evidence_prompt="Review remaining template cleanup findings, then rerun recorder-next.",
        ),
    )


def write_2d_animation_playtest_recorder_queue(
    hints: tuple[AnimationPlaytestRecorderHint, ...],
    output_path: Path,
) -> None:
    """Write recorder hints as a Markdown handoff artifact."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NEXUS TECH 2D Animation Recorder Queue",
        "",
        "- Manual result: `not completed by automation`",
        "- Recorder commands: `placeholders require real tester observations before use`",
        "- Completion gate: `validate-animation-playtest-report must pass before signoff`",
        "",
        (
            "| Step | Status | Area | Target | Visible Command | Required Terms | "
            "Evidence Prompt | Recorder Command |"
        ),
        "| ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for index, hint in enumerate(hints, start=1):
        required_terms = ", ".join(hint.required_terms) if hint.required_terms else "-"
        visible_command = hint.visible_command or "-"
        lines.append(
            "| "
            f"{index} | "
            f"`{hint.status}` | "
            f"{_markdown_table_cell(hint.area)} | "
            f"{_markdown_table_cell(hint.target)} | "
            f"`{_markdown_table_cell(visible_command)}` | "
            f"{_markdown_table_cell(required_terms)} | "
            f"{_markdown_table_cell(hint.evidence_prompt)} | "
            f"`{_markdown_table_cell(hint.recorder_command)}` |"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_2d_animation_playtest_recorder_queue(
    queue_path: Path,
    report_path: Path,
    command_path: Path,
    *,
    scenario_id: str = "founder_journey",
    seed: int = 7,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    command_prefix: str = "uv run nexus-tech",
) -> AnimationPlaytestRecorderQueueValidation:
    """Validate that a recorder queue artifact matches the current report gaps."""

    text = queue_path.read_text(encoding="utf-8")
    expected_hints = build_2d_animation_playtest_recorder_queue(
        report_path,
        command_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    findings: list[str] = []
    required_lines = (
        "# NEXUS TECH 2D Animation Recorder Queue",
        "- Manual result: `not completed by automation`",
        "- Recorder commands: `placeholders require real tester observations before use`",
        "- Completion gate: `validate-animation-playtest-report must pass before signoff`",
    )
    for line in required_lines:
        if line not in text:
            findings.append(f"missing recorder queue guard: {line}")

    rows = _extract_markdown_table_rows(text)
    recorder_rows = tuple(row for row in rows if len(row) >= 8 and row[0].isdigit())
    if len(recorder_rows) != len(expected_hints):
        findings.append(f"expected {len(expected_hints)} recorder rows, found {len(recorder_rows)}")

    rows_by_step: dict[int, tuple[str, ...]] = {}
    for row in recorder_rows:
        step = int(row[0])
        if step in rows_by_step:
            findings.append(f"duplicate recorder queue step: {step}")
            continue
        rows_by_step[step] = row

    for index, hint in enumerate(expected_hints, start=1):
        row = rows_by_step.get(index)
        if row is None:
            findings.append(f"missing recorder queue row: {index}")
            continue
        _validate_recorder_queue_row(findings, index, row, hint)

    return AnimationPlaytestRecorderQueueValidation(
        path=str(queue_path),
        expected_count=len(expected_hints),
        findings=tuple(findings),
    )


def validate_2d_animation_playtest_session(
    report_path: Path,
    command_path: Path,
    plan_path: Path,
    recorder_queue_path: Path,
    route_batch_path: Path | None = None,
    *,
    scenario_id: str = "founder_journey",
    seed: int = 7,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    command_prefix: str = "uv run nexus-tech",
) -> AnimationPlaytestSessionValidation:
    """Validate that the complete manual animation handoff package is in sync."""

    report = validate_2d_animation_playtest_report(report_path)
    commands = validate_2d_animation_playtest_command_queue(
        command_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    plan = validate_2d_animation_playtest_readiness_plan(
        plan_path,
        report_path,
        command_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    recorder_queue = validate_2d_animation_playtest_recorder_queue(
        recorder_queue_path,
        report_path,
        command_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    route_batches = (
        None
        if route_batch_path is None
        else validate_2d_animation_playtest_route_batch_plan(
            route_batch_path,
            report_path,
            command_path,
            scenario_id=scenario_id,
            seed=seed,
            windows=windows,
            motion_modes=motion_modes,
            command_prefix=command_prefix,
        )
    )
    return AnimationPlaytestSessionValidation(
        report=report,
        commands=commands,
        plan=plan,
        recorder_queue=recorder_queue,
        route_batches=route_batches,
    )


def build_2d_animation_playtest_handoff(
    report_path: Path,
    command_path: Path,
    plan_path: Path,
    recorder_queue_path: Path,
    route_batch_path: Path | None = None,
    *,
    scenario_id: str = "founder_journey",
    seed: int = 7,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    command_prefix: str = "uv run nexus-tech",
) -> AnimationPlaytestHandoff:
    """Build the current manual animation handoff without completing signoff."""

    session = validate_2d_animation_playtest_session(
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        route_batch_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    plan = build_2d_animation_playtest_readiness_plan(
        report_path,
        command_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    recorder_hint = build_2d_animation_playtest_recorder_hint(
        report_path,
        command_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    return AnimationPlaytestHandoff(
        session=session,
        plan=plan,
        recorder_hint=recorder_hint,
    )


def build_2d_animation_playtest_route_batch_plan(
    report_path: Path,
    command_path: Path,
    *,
    scenario_id: str = "founder_journey",
    seed: int = 7,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    command_prefix: str = "uv run nexus-tech",
) -> AnimationPlaytestRouteBatchPlan:
    """Build window-sized manual route batches without writing tester evidence."""

    report = validate_2d_animation_playtest_report(report_path)
    commands = validate_2d_animation_playtest_command_queue(
        command_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    visible_route = build_2d_animation_playtest_command_queue(
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    plan = AnimationPlaytestReadinessPlan(
        report=report,
        commands=commands,
        steps=(),
        visible_route=visible_route,
    )
    open_route_indexes = set(_route_finding_indexes(report.findings))
    open_window_sizes = set(_window_finding_labels(report.findings))
    route_items_by_window: dict[str, list[AnimationPlaytestRouteBatchItem]] = {}
    window_order: list[str] = []

    for route_index, item in enumerate(visible_route, start=1):
        if item.window_size not in route_items_by_window:
            route_items_by_window[item.window_size] = []
            window_order.append(item.window_size)
        status = "manual-required" if route_index in open_route_indexes else "pass"
        hint = (
            _build_route_recorder_hint(
                plan,
                route_index=route_index,
                report_path=report_path,
                command_prefix=command_prefix,
            )
            if status != "pass"
            else None
        )
        route_items_by_window[item.window_size].append(
            AnimationPlaytestRouteBatchItem(
                step=route_index,
                target=item.target,
                window_size=item.window_size,
                motion_mode=item.motion_mode,
                status=status,
                visible_command=item.command,
                recorder_command=hint.recorder_command if hint is not None else "",
                evidence_prompt=hint.evidence_prompt if hint is not None else "Already recorded.",
                required_terms=hint.required_terms if hint is not None else (),
            )
        )

    batches: list[AnimationPlaytestRouteBatch] = []
    for batch_number, window_size in enumerate(window_order, start=1):
        window_hint = (
            _build_window_recorder_hint(
                window_size,
                report_path=report_path,
                command_prefix=command_prefix,
            )
            if window_size in open_window_sizes
            else None
        )
        batches.append(
            AnimationPlaytestRouteBatch(
                batch_number=batch_number,
                window_size=window_size,
                items=tuple(route_items_by_window[window_size]),
                window_recorder_hint=window_hint,
            )
        )

    return AnimationPlaytestRouteBatchPlan(
        report=report,
        commands=commands,
        batches=tuple(batches),
        scenario_id=scenario_id,
        seed=seed,
        command_prefix=command_prefix,
    )


def build_2d_animation_playtest_ui_triage_plan(
    report_path: Path,
    command_path: Path,
    plan_path: Path,
    recorder_queue_path: Path,
    route_batch_path: Path | None = None,
    *,
    scenario_id: str = "founder_journey",
    seed: int = 7,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    command_prefix: str = "uv run nexus-tech",
) -> AnimationPlaytestUITriagePlan:
    """Build a manual UI/animation triage backlog from current handoff artifacts."""

    session = validate_2d_animation_playtest_session(
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        route_batch_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    items: list[AnimationPlaytestUITriageItem] = []
    if session.findings:
        for finding in session.findings:
            items.append(
                AnimationPlaytestUITriageItem(
                    step=len(items) + 1,
                    priority="P0",
                    area="Session Artifact",
                    lane="Artifact Hygiene",
                    status="blocked",
                    open_items=1,
                    required_evidence=(
                        "Regenerate and validate stale handoff artifacts before manual UI review."
                    ),
                    next_action=finding,
                )
            )
        return AnimationPlaytestUITriagePlan(session=session, items=tuple(items))

    plan = build_2d_animation_playtest_readiness_plan(
        report_path,
        command_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    for step in plan.steps:
        priority, lane, required_evidence = _animation_ui_triage_profile(step.area)
        items.append(
            AnimationPlaytestUITriageItem(
                step=len(items) + 1,
                priority="PASS" if step.status == "pass" else priority,
                area=step.area,
                lane=lane,
                status=step.status,
                open_items=step.open_items,
                required_evidence=required_evidence,
                next_action=step.next_step,
            )
        )

    return AnimationPlaytestUITriagePlan(session=session, items=tuple(items))


def write_2d_animation_playtest_ui_triage_plan(
    triage: AnimationPlaytestUITriagePlan,
    output_path: Path,
) -> None:
    """Write a structured manual UI/animation triage backlog."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    manual_result = "complete" if triage.status == "pass" else "not completed by automation"
    lines = [
        "# NEXUS TECH 2D Animation UI Triage",
        "",
        f"- Status: `{triage.status}`",
        f"- Artifact status: `{triage.session.artifact_status}`",
        f"- Handoff status: `{triage.session.handoff_status}`",
        f"- Manual result: `{manual_result}`",
        f"- Report: `{triage.session.report.path}`",
        f"- Command queue: `{triage.session.commands.path}`",
        f"- Recorder queue: `{triage.session.recorder_queue.path}`",
        *(
            ()
            if triage.session.route_batches is None
            else (f"- Route batches: `{triage.session.route_batches.path}`",)
        ),
        f"- Open triage items: `{triage.open_item_count}`",
        f"- P0/P1 lanes: `{triage.blocker_count}`",
        "- Completion gate: `validate-animation-playtest-report must pass before signoff`",
        _ANIMATION_UI_TRIAGE_POLICY_LINE,
        "",
        "## Triage Backlog",
        "",
        "| Step | Priority | Area | Lane | Status | Open Items | Required Evidence | Next Action |",
        "| ---: | --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for item in triage.items:
        lines.append(
            "| "
            f"{item.step} | "
            f"`{item.priority}` | "
            f"{_markdown_table_cell(item.area)} | "
            f"{_markdown_table_cell(item.lane)} | "
            f"`{item.status}` | "
            f"{item.open_items} | "
            f"{_markdown_table_cell(item.required_evidence)} | "
            f"{_markdown_table_cell(item.next_action)} |"
        )
    lines.extend(
        [
            "",
            "## Triage Rules",
            "",
            "- `P0` lanes block beta until they pass or have a named accepted blocker.",
            "- `P1` lanes block presentation polish until real open-window evidence clears them.",
            (
                "- `P2` lanes can wait only when the release decision explicitly "
                "accepts the follow-up."
            ),
            "- This artifact is a backlog aid only; it never completes manual signoff by itself.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_2d_animation_playtest_ui_triage_plan(
    triage_path: Path,
    report_path: Path,
    command_path: Path,
    plan_path: Path,
    recorder_queue_path: Path,
    route_batch_path: Path | None = None,
    *,
    scenario_id: str = "founder_journey",
    seed: int = 7,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    command_prefix: str = "uv run nexus-tech",
) -> AnimationPlaytestUITriageValidation:
    """Validate that a UI triage artifact matches the current handoff package."""

    text = triage_path.read_text(encoding="utf-8")
    triage = build_2d_animation_playtest_ui_triage_plan(
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        route_batch_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    findings: list[str] = []
    manual_result = "complete" if triage.status == "pass" else "not completed by automation"
    required_lines = (
        "# NEXUS TECH 2D Animation UI Triage",
        f"- Status: `{triage.status}`",
        f"- Artifact status: `{triage.session.artifact_status}`",
        f"- Handoff status: `{triage.session.handoff_status}`",
        f"- Manual result: `{manual_result}`",
        f"- Report: `{triage.session.report.path}`",
        f"- Command queue: `{triage.session.commands.path}`",
        f"- Recorder queue: `{triage.session.recorder_queue.path}`",
        f"- Open triage items: `{triage.open_item_count}`",
        f"- P0/P1 lanes: `{triage.blocker_count}`",
        "- Completion gate: `validate-animation-playtest-report must pass before signoff`",
        _ANIMATION_UI_TRIAGE_POLICY_LINE,
    )
    for line in required_lines:
        if line not in text:
            findings.append(f"missing ui triage guard: {line}")
    if triage.session.route_batches is not None:
        route_line = f"- Route batches: `{triage.session.route_batches.path}`"
        if route_line not in text:
            findings.append(f"missing ui triage guard: {route_line}")

    rows = _extract_markdown_table_rows(text)
    triage_rows = tuple(row for row in rows if len(row) >= 8 and row[0].isdigit())
    if len(triage_rows) != len(triage.items):
        findings.append(f"expected {len(triage.items)} ui triage rows, found {len(triage_rows)}")

    rows_by_step: dict[int, tuple[str, ...]] = {}
    for row in triage_rows:
        step = int(row[0])
        if step in rows_by_step:
            findings.append(f"duplicate ui triage step: {step}")
            continue
        rows_by_step[step] = row

    for item in triage.items:
        row = rows_by_step.get(item.step)
        if row is None:
            findings.append(f"missing ui triage row: {item.step}")
            continue
        _validate_ui_triage_row(findings, item, row)

    return AnimationPlaytestUITriageValidation(
        path=str(triage_path),
        expected_count=len(triage.items),
        findings=tuple(findings),
    )


def build_2d_animation_playtest_release_gate(
    report_path: Path,
    command_path: Path,
    plan_path: Path,
    recorder_queue_path: Path,
    triage_path: Path,
    route_batch_path: Path | None = None,
    *,
    scenario_id: str = "founder_journey",
    seed: int = 7,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    command_prefix: str = "uv run nexus-tech",
) -> AnimationPlaytestReleaseGate:
    """Build a go/no-go release gate for the current manual animation QA package."""

    session = validate_2d_animation_playtest_session(
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        route_batch_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    triage = build_2d_animation_playtest_ui_triage_plan(
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        route_batch_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    triage_validation = validate_2d_animation_playtest_ui_triage_plan(
        triage_path,
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        route_batch_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    recorder_hint = build_2d_animation_playtest_recorder_hint(
        report_path,
        command_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    checks = (
        AnimationPlaytestReleaseGateCheck(
            name="Session Artifacts",
            status=session.artifact_status,
            blocker_count=len(session.findings),
            next_action=(
                "Regenerate stale command, plan, recorder, or route artifacts."
                if session.findings
                else "Session artifacts are current."
            ),
        ),
        AnimationPlaytestReleaseGateCheck(
            name="UI Triage Artifact",
            status=triage_validation.status,
            blocker_count=len(triage_validation.findings),
            next_action=(
                "Regenerate animation-playtest-ui-triage, then rerun its validator."
                if triage_validation.findings
                else "UI triage artifact matches the current handoff package."
            ),
        ),
        AnimationPlaytestReleaseGateCheck(
            name="Manual Report Signoff",
            status=session.report.status if session.report.status == "pass" else "manual-required",
            blocker_count=len(session.report.findings),
            next_action=(
                "Run visible-window QA and record real evidence until the report validates."
                if session.report.status != "pass"
                else "Manual animation report validates."
            ),
        ),
        AnimationPlaytestReleaseGateCheck(
            name="P0/P1 UI Lanes",
            status="pass" if triage.blocker_count == 0 else triage.status,
            blocker_count=triage.blocker_count,
            next_action=(
                "Clear P0/P1 layout, typography, control, motion, and signoff lanes."
                if triage.blocker_count
                else "No open P0/P1 UI triage lanes."
            ),
        ),
        AnimationPlaytestReleaseGateCheck(
            name="Release Decision",
            status=(
                "blocked"
                if session.artifact_status != "pass" or triage_validation.status != "pass"
                else "pass"
                if session.report.status == "pass" and triage.blocker_count == 0
                else "manual-required"
            ),
            blocker_count=0
            if session.artifact_status == "pass"
            and triage_validation.status == "pass"
            and session.report.status == "pass"
            and triage.blocker_count == 0
            else 1,
            next_action=(
                "Release can proceed with the passing manual animation evidence attached."
                if session.artifact_status == "pass"
                and triage_validation.status == "pass"
                and session.report.status == "pass"
                and triage.blocker_count == 0
                else "Keep release blocked until artifacts, manual report, and UI triage all pass."
            ),
        ),
    )
    return AnimationPlaytestReleaseGate(
        session=session,
        triage=triage,
        triage_validation=triage_validation,
        recorder_hint=recorder_hint,
        checks=checks,
    )


def write_2d_animation_playtest_release_gate(
    gate: AnimationPlaytestReleaseGate,
    output_path: Path,
) -> None:
    """Write the final manual animation release gate as Markdown."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    hint = gate.recorder_hint
    required_terms = ", ".join(hint.required_terms) if hint.required_terms else "-"
    visible_command = hint.visible_command or "-"
    lines = [
        "# NEXUS TECH 2D Animation Release Gate",
        "",
        f"- Status: `{gate.status}`",
        f"- Artifact status: `{gate.artifact_status}`",
        f"- Manual result: `{gate.manual_result}`",
        f"- Handoff status: `{gate.session.handoff_status}`",
        f"- Report status: `{gate.session.report.status}`",
        f"- UI triage status: `{gate.triage.status}`",
        f"- UI triage artifact: `{gate.triage_validation.status}`",
        f"- Report: `{gate.session.report.path}`",
        f"- Command queue: `{gate.session.commands.path}`",
        f"- Plan: `{gate.session.plan.path}`",
        f"- Recorder queue: `{gate.session.recorder_queue.path}`",
        *(
            ()
            if gate.session.route_batches is None
            else (f"- Route batches: `{gate.session.route_batches.path}`",)
        ),
        f"- Open report items: `{len(gate.session.report.findings)}`",
        f"- Open UI triage items: `{gate.triage.open_item_count}`",
        f"- P0/P1 lanes: `{gate.triage.blocker_count}`",
        f"- Blocking checks: `{gate.blocking_check_count}`",
        f"- Next manual area: `{hint.area}`",
        f"- Next manual target: `{hint.target}`",
        f"- Next manual status: `{hint.status}`",
        (
            "- Completion gate: "
            "`validate-animation-playtest-report and validate-animation-playtest-ui-triage "
            "must pass before release`"
        ),
        _ANIMATION_RELEASE_GATE_POLICY_LINE,
        "",
        "## Release Gate Checks",
        "",
        "| Check | Status | Blockers | Next Action |",
        "| --- | --- | ---: | --- |",
    ]
    for check in gate.checks:
        lines.append(
            "| "
            f"{_markdown_table_cell(check.name)} | "
            f"`{check.status}` | "
            f"{check.blocker_count} | "
            f"{_markdown_table_cell(check.next_action)} |"
        )
    lines.extend(
        [
            "",
            "## Next Manual Action",
            "",
            (
                "| Area | Target | Status | Required Terms | Evidence Prompt | "
                "Visible Command | Recorder Command |"
            ),
            "| --- | --- | --- | --- | --- | --- | --- |",
            (
                "| "
                f"{_markdown_table_cell(hint.area)} | "
                f"{_markdown_table_cell(hint.target)} | "
                f"`{hint.status}` | "
                f"{_markdown_table_cell(required_terms)} | "
                f"{_markdown_table_cell(hint.evidence_prompt)} | "
                f"`{_markdown_table_cell(visible_command)}` | "
                f"`{_markdown_table_cell(hint.recorder_command)}` |"
            ),
            "",
            "## Release Rules",
            "",
            "- `blocked` means at least one generated handoff artifact is stale.",
            (
                "- `manual-required` means visible-window evidence or P0/P1 UI "
                "closure is still missing."
            ),
            "- `pass` means the session, triage, and manual report are all current and signed off.",
            "- This artifact is a release gate only; it never records tester evidence by itself.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_2d_animation_playtest_release_gate(
    gate_path: Path,
    report_path: Path,
    command_path: Path,
    plan_path: Path,
    recorder_queue_path: Path,
    triage_path: Path,
    route_batch_path: Path | None = None,
    *,
    scenario_id: str = "founder_journey",
    seed: int = 7,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    command_prefix: str = "uv run nexus-tech",
) -> AnimationPlaytestReleaseGateValidation:
    """Validate that a release-gate artifact matches the current QA package."""

    text = gate_path.read_text(encoding="utf-8")
    gate = build_2d_animation_playtest_release_gate(
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        triage_path,
        route_batch_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    findings: list[str] = []
    required_lines = (
        "# NEXUS TECH 2D Animation Release Gate",
        f"- Status: `{gate.status}`",
        f"- Artifact status: `{gate.artifact_status}`",
        f"- Manual result: `{gate.manual_result}`",
        f"- Handoff status: `{gate.session.handoff_status}`",
        f"- Report status: `{gate.session.report.status}`",
        f"- UI triage status: `{gate.triage.status}`",
        f"- UI triage artifact: `{gate.triage_validation.status}`",
        f"- Report: `{gate.session.report.path}`",
        f"- Command queue: `{gate.session.commands.path}`",
        f"- Plan: `{gate.session.plan.path}`",
        f"- Recorder queue: `{gate.session.recorder_queue.path}`",
        f"- Open report items: `{len(gate.session.report.findings)}`",
        f"- Open UI triage items: `{gate.triage.open_item_count}`",
        f"- P0/P1 lanes: `{gate.triage.blocker_count}`",
        f"- Blocking checks: `{gate.blocking_check_count}`",
        f"- Next manual area: `{gate.recorder_hint.area}`",
        f"- Next manual target: `{gate.recorder_hint.target}`",
        f"- Next manual status: `{gate.recorder_hint.status}`",
        (
            "- Completion gate: "
            "`validate-animation-playtest-report and validate-animation-playtest-ui-triage "
            "must pass before release`"
        ),
        _ANIMATION_RELEASE_GATE_POLICY_LINE,
    )
    for line in required_lines:
        if line not in text:
            findings.append(f"missing release gate guard: {line}")
    if gate.session.route_batches is not None:
        route_line = f"- Route batches: `{gate.session.route_batches.path}`"
        if route_line not in text:
            findings.append(f"missing release gate guard: {route_line}")

    rows = _extract_markdown_table_rows(text)
    gate_rows = tuple(row for row in rows if len(row) >= 4 and row[0] in _RELEASE_GATE_CHECKS)
    if len(gate_rows) != len(gate.checks):
        findings.append(f"expected {len(gate.checks)} release gate rows, found {len(gate_rows)}")

    rows_by_check = {row[0].replace(r"\|", "|").strip(): row for row in gate_rows}
    for check in gate.checks:
        row = rows_by_check.get(check.name)
        if row is None:
            findings.append(f"missing release gate row: {check.name}")
            continue
        _validate_release_gate_row(findings, check, row)

    next_action_rows = tuple(
        row for row in rows if len(row) >= 7 and row[0] == gate.recorder_hint.area
    )
    if len(next_action_rows) != 1:
        findings.append("expected 1 release gate next-action row")
    else:
        _validate_release_gate_next_action(findings, gate.recorder_hint, next_action_rows[0])

    return AnimationPlaytestReleaseGateValidation(
        path=str(gate_path),
        expected_count=len(gate.checks),
        findings=tuple(findings),
    )


def build_2d_animation_playtest_progress_board(
    report_path: Path,
    command_path: Path,
    plan_path: Path,
    recorder_queue_path: Path,
    triage_path: Path,
    route_batch_path: Path | None = None,
    *,
    scenario_id: str = "founder_journey",
    seed: int = 7,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    command_prefix: str = "uv run nexus-tech",
) -> AnimationPlaytestProgressBoard:
    """Build a manual animation progress board without recording tester evidence."""

    gate = build_2d_animation_playtest_release_gate(
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        triage_path,
        route_batch_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    route = build_2d_animation_playtest_command_queue(
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    report_areas = {
        area.area: area for area in summarize_2d_animation_playtest_report(gate.session.report)
    }
    report_lane_totals = _animation_progress_report_lane_totals(
        route_count=len(route),
        windows=windows,
        motion_modes=motion_modes,
    )
    lanes: list[AnimationPlaytestProgressLane] = []
    for lane_name in _PROGRESS_BOARD_LANES:
        if lane_name in report_lane_totals:
            area = report_areas.get(lane_name)
            open_items = 0 if area is None else area.incomplete_count
            total_items = max(report_lane_totals[lane_name], open_items)
            lanes.append(
                AnimationPlaytestProgressLane(
                    area=lane_name,
                    status="pass" if open_items == 0 else "manual-required",
                    total_items=total_items,
                    open_items=open_items,
                    next_action=(
                        "Current report lane is complete." if area is None else area.next_step
                    ),
                )
            )
            continue
        if lane_name == "Session Artifacts":
            lanes.append(
                AnimationPlaytestProgressLane(
                    area=lane_name,
                    status="pass" if gate.session.artifact_status == "pass" else "blocked",
                    total_items=max(1, len(gate.session.findings)),
                    open_items=len(gate.session.findings),
                    next_action=_release_gate_check_next_action(gate, lane_name),
                )
            )
            continue
        if lane_name == "UI Triage Artifact":
            lanes.append(
                AnimationPlaytestProgressLane(
                    area=lane_name,
                    status="pass" if gate.triage_validation.status == "pass" else "blocked",
                    total_items=max(1, len(gate.triage_validation.findings)),
                    open_items=len(gate.triage_validation.findings),
                    next_action=_release_gate_check_next_action(gate, lane_name),
                )
            )
            continue
        if lane_name == "P0/P1 UI Lanes":
            total_items = max(
                1,
                sum(1 for item in gate.triage.items if item.priority in {"P0", "P1"}),
                gate.triage.blocker_count,
            )
            lanes.append(
                AnimationPlaytestProgressLane(
                    area=lane_name,
                    status="pass" if gate.triage.blocker_count == 0 else "manual-required",
                    total_items=total_items,
                    open_items=gate.triage.blocker_count,
                    next_action=_release_gate_check_next_action(gate, lane_name),
                )
            )
            continue
        lanes.append(
            AnimationPlaytestProgressLane(
                area=lane_name,
                status=gate.status,
                total_items=max(1, len(gate.checks)),
                open_items=gate.blocking_check_count,
                next_action=_release_gate_check_next_action(gate, "Release Decision"),
            )
        )

    return AnimationPlaytestProgressBoard(
        release_gate=gate,
        lanes=tuple(lanes),
    )


def write_2d_animation_playtest_progress_board(
    board: AnimationPlaytestProgressBoard,
    output_path: Path,
) -> None:
    """Write the current manual animation QA progress board as Markdown."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    gate = board.release_gate
    hint = gate.recorder_hint
    required_terms = ", ".join(hint.required_terms) if hint.required_terms else "-"
    visible_command = hint.visible_command or "-"
    lines = [
        "# NEXUS TECH 2D Animation Progress Board",
        "",
        f"- Status: `{board.status}`",
        f"- Completion: `{board.completion_percent}%`",
        f"- Completed items: `{board.completed_item_count}`",
        f"- Open work items: `{board.open_item_count}`",
        f"- Total tracked items: `{board.total_item_count}`",
        f"- Release gate status: `{gate.status}`",
        f"- Artifact status: `{gate.artifact_status}`",
        f"- Manual result: `{gate.manual_result}`",
        f"- Report: `{gate.session.report.path}`",
        f"- Command queue: `{gate.session.commands.path}`",
        f"- Plan: `{gate.session.plan.path}`",
        f"- Recorder queue: `{gate.session.recorder_queue.path}`",
        *(
            ()
            if gate.session.route_batches is None
            else (f"- Route batches: `{gate.session.route_batches.path}`",)
        ),
        f"- UI triage status: `{gate.triage.status}`",
        f"- P0/P1 lanes: `{gate.triage.blocker_count}`",
        f"- Blocking checks: `{gate.blocking_check_count}`",
        f"- Next manual area: `{hint.area}`",
        f"- Next manual target: `{hint.target}`",
        (
            "- Completion gate: "
            "`validate-animation-playtest-report, validate-animation-playtest-ui-triage, "
            "and validate-animation-playtest-release-gate must pass before release`"
        ),
        _ANIMATION_PROGRESS_POLICY_LINE,
        "",
        "## Progress Lanes",
        "",
        "| Lane | Status | Done | Open | Completion | Next Action |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for lane in board.lanes:
        lines.append(
            "| "
            f"{_markdown_table_cell(lane.area)} | "
            f"`{lane.status}` | "
            f"{lane.completed_items}/{lane.total_items} | "
            f"{lane.open_items} | "
            f"{lane.completion_percent}% | "
            f"{_markdown_table_cell(lane.next_action)} |"
        )
    lines.extend(
        [
            "",
            "## Next Manual Action",
            "",
            (
                "| Area | Target | Status | Required Terms | Evidence Prompt | "
                "Visible Command | Recorder Command |"
            ),
            "| --- | --- | --- | --- | --- | --- | --- |",
            (
                "| "
                f"{_markdown_table_cell(hint.area)} | "
                f"{_markdown_table_cell(hint.target)} | "
                f"`{hint.status}` | "
                f"{_markdown_table_cell(required_terms)} | "
                f"{_markdown_table_cell(hint.evidence_prompt)} | "
                f"`{_markdown_table_cell(visible_command)}` | "
                f"`{_markdown_table_cell(hint.recorder_command)}` |"
            ),
            "",
            "## Board Rules",
            "",
            "- Use this board to decide the next manual QA target; do not attach it as evidence.",
            "- Use the recorder command only after observing the visible-window command yourself.",
            "- The release gate remains authoritative for go/no-go status.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_2d_animation_playtest_progress_board(
    progress_path: Path,
    report_path: Path,
    command_path: Path,
    plan_path: Path,
    recorder_queue_path: Path,
    triage_path: Path,
    route_batch_path: Path | None = None,
    *,
    scenario_id: str = "founder_journey",
    seed: int = 7,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    command_prefix: str = "uv run nexus-tech",
) -> AnimationPlaytestProgressBoardValidation:
    """Validate that a progress board artifact matches the current QA package."""

    text = progress_path.read_text(encoding="utf-8")
    board = build_2d_animation_playtest_progress_board(
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        triage_path,
        route_batch_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    gate = board.release_gate
    findings: list[str] = []
    required_lines = (
        "# NEXUS TECH 2D Animation Progress Board",
        f"- Status: `{board.status}`",
        f"- Completion: `{board.completion_percent}%`",
        f"- Completed items: `{board.completed_item_count}`",
        f"- Open work items: `{board.open_item_count}`",
        f"- Total tracked items: `{board.total_item_count}`",
        f"- Release gate status: `{gate.status}`",
        f"- Artifact status: `{gate.artifact_status}`",
        f"- Manual result: `{gate.manual_result}`",
        f"- Report: `{gate.session.report.path}`",
        f"- Command queue: `{gate.session.commands.path}`",
        f"- Plan: `{gate.session.plan.path}`",
        f"- Recorder queue: `{gate.session.recorder_queue.path}`",
        f"- UI triage status: `{gate.triage.status}`",
        f"- P0/P1 lanes: `{gate.triage.blocker_count}`",
        f"- Blocking checks: `{gate.blocking_check_count}`",
        f"- Next manual area: `{gate.recorder_hint.area}`",
        f"- Next manual target: `{gate.recorder_hint.target}`",
        (
            "- Completion gate: "
            "`validate-animation-playtest-report, validate-animation-playtest-ui-triage, "
            "and validate-animation-playtest-release-gate must pass before release`"
        ),
        _ANIMATION_PROGRESS_POLICY_LINE,
    )
    for line in required_lines:
        if line not in text:
            findings.append(f"missing progress board guard: {line}")
    if gate.session.route_batches is not None:
        route_line = f"- Route batches: `{gate.session.route_batches.path}`"
        if route_line not in text:
            findings.append(f"missing progress board guard: {route_line}")

    rows = _extract_markdown_table_rows(text)
    lane_rows = tuple(row for row in rows if len(row) >= 6 and row[0] in _PROGRESS_BOARD_LANE_NAMES)
    if len(lane_rows) != len(board.lanes):
        findings.append(f"expected {len(board.lanes)} progress lanes, found {len(lane_rows)}")

    rows_by_lane = {row[0].replace(r"\|", "|").strip(): row for row in lane_rows}
    for lane in board.lanes:
        row = rows_by_lane.get(lane.area)
        if row is None:
            findings.append(f"missing progress lane: {lane.area}")
            continue
        _validate_progress_lane_row(findings, lane, row)

    next_action_rows = tuple(
        row for row in rows if len(row) >= 7 and row[0] == gate.recorder_hint.area
    )
    if len(next_action_rows) != 1:
        findings.append("expected 1 progress board next-action row")
    else:
        _validate_release_gate_next_action(findings, gate.recorder_hint, next_action_rows[0])

    return AnimationPlaytestProgressBoardValidation(
        path=str(progress_path),
        expected_count=len(board.lanes),
        findings=tuple(findings),
    )


def build_2d_animation_playtest_execution_guide(
    report_path: Path,
    command_path: Path,
    plan_path: Path,
    recorder_queue_path: Path,
    triage_path: Path,
    route_batch_path: Path | None = None,
    *,
    progress_path: Path = Path("/tmp/nexus-tech-animation-progress.md"),
    scenario_id: str = "founder_journey",
    seed: int = 7,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    command_prefix: str = "uv run nexus-tech",
) -> AnimationPlaytestExecutionGuide:
    """Build the manual animation execution guide without recording evidence."""

    progress = build_2d_animation_playtest_progress_board(
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        triage_path,
        route_batch_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    recorder_steps = build_2d_animation_playtest_recorder_queue(
        report_path,
        command_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    return AnimationPlaytestExecutionGuide(
        progress=progress,
        recorder_steps=recorder_steps,
        progress_path=str(progress_path),
        scenario_id=scenario_id,
        seed=seed,
        command_prefix=command_prefix,
    )


def write_2d_animation_playtest_execution_guide(
    guide: AnimationPlaytestExecutionGuide,
    output_path: Path,
) -> None:
    """Write a manual animation QA operator guide as Markdown."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    progress = guide.progress
    gate = progress.release_gate
    route_batch_args = (
        ""
        if gate.session.route_batches is None
        else f" --route-batches {_shell_arg(gate.session.route_batches.path)}"
    )
    validation_context_args = (
        f" --scenario {_shell_arg(guide.scenario_id)}"
        f" --seed {guide.seed}"
        f" --command-prefix {_shell_arg(guide.command_prefix)}"
    )
    progress_validation_command = (
        f"{guide.command_prefix} validate-animation-playtest-progress "
        f"{_shell_arg(guide.progress_path)} "
        f"{_shell_arg(gate.session.report.path)} {_shell_arg(gate.session.commands.path)} "
        f"{_shell_arg(gate.session.plan.path)} "
        f"{_shell_arg(gate.session.recorder_queue.path)} "
        f"{_shell_arg(gate.triage_validation.path)}{route_batch_args}"
        f"{validation_context_args}"
    )
    guide_validation_command = (
        f"{guide.command_prefix} validate-animation-playtest-execution-guide "
        f"{_shell_arg(output_path)} "
        f"{_shell_arg(gate.session.report.path)} {_shell_arg(gate.session.commands.path)} "
        f"{_shell_arg(gate.session.plan.path)} "
        f"{_shell_arg(gate.session.recorder_queue.path)} "
        f"{_shell_arg(gate.triage_validation.path)}{route_batch_args}"
        f" --progress-path {_shell_arg(guide.progress_path)}"
        f"{validation_context_args}"
    )
    report_validation_command = (
        f"{guide.command_prefix} validate-animation-playtest-report "
        f"{_shell_arg(gate.session.report.path)}"
    )
    lines = [
        "# NEXUS TECH 2D Animation Execution Guide",
        "",
        f"- Status: `{guide.status}`",
        f"- Completion: `{progress.completion_percent}%`",
        f"- Open progress items: `{progress.open_item_count}`",
        f"- Open recorder steps: `{guide.open_step_count}`",
        f"- Manual result: `{gate.manual_result}`",
        f"- Report: `{gate.session.report.path}`",
        f"- Command queue: `{gate.session.commands.path}`",
        f"- Plan: `{gate.session.plan.path}`",
        f"- Recorder queue: `{gate.session.recorder_queue.path}`",
        f"- Progress board: `{guide.progress_path}`",
        f"- Next manual area: `{gate.recorder_hint.area}`",
        f"- Next manual target: `{gate.recorder_hint.target}`",
        (
            "- Completion gate: "
            "`record real visible-window evidence, then rerun progress, release-gate, "
            "and report validators`"
        ),
        _ANIMATION_EXECUTION_GUIDE_POLICY_LINE,
        "",
        "## Operator Loop",
        "",
        "| Step | Action | Required Result |",
        "| ---: | --- | --- |",
        (
            "| 1 | Run the visible command for the current row when one is listed. | "
            "Game window opens at the expected size and motion mode. |"
        ),
        (
            "| 2 | Observe layout, text, controls, scene motion, and feedback without "
            "editing placeholders first. | Notes describe what was actually visible. |"
        ),
        (
            "| 3 | Run the recorder command with real notes replacing the placeholder text. | "
            "The report row changes from todo to the observed result. |"
        ),
        (
            "| 4 | Rerun progress and release-gate validators. | "
            "The next open lane or next manual action advances. |"
        ),
        "",
        "## Execution Queue",
        "",
        (
            "| Step | Phase | Status | Area | Target | Visible Command | Required Terms | "
            "Evidence Prompt | Recorder Command |"
        ),
        "| ---: | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for index, hint in enumerate(guide.recorder_steps, start=1):
        required_terms = ", ".join(hint.required_terms) if hint.required_terms else "-"
        visible_command = hint.visible_command or "-"
        lines.append(
            "| "
            f"{index} | "
            f"{_markdown_table_cell(_execution_phase_for_area(hint.area))} | "
            f"`{hint.status}` | "
            f"{_markdown_table_cell(hint.area)} | "
            f"{_markdown_table_cell(hint.target)} | "
            f"`{_markdown_table_cell(visible_command)}` | "
            f"{_markdown_table_cell(required_terms)} | "
            f"{_markdown_table_cell(hint.evidence_prompt)} | "
            f"`{_markdown_table_cell(hint.recorder_command)}` |"
        )
    lines.extend(
        [
            "",
            "## Validation Commands",
            "",
            "```bash",
            progress_validation_command,
            guide_validation_command,
            report_validation_command,
            "```",
            "",
            "## Guide Rules",
            "",
            "- This guide does not complete the manual pass by itself.",
            "- Do not run recorder commands with placeholder text.",
            "- If a row fails visually, record the actual failure and keep release blocked.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_2d_animation_playtest_execution_guide(
    guide_path: Path,
    report_path: Path,
    command_path: Path,
    plan_path: Path,
    recorder_queue_path: Path,
    triage_path: Path,
    route_batch_path: Path | None = None,
    *,
    progress_path: Path = Path("/tmp/nexus-tech-animation-progress.md"),
    scenario_id: str = "founder_journey",
    seed: int = 7,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    command_prefix: str = "uv run nexus-tech",
) -> AnimationPlaytestExecutionGuideValidation:
    """Validate that an execution guide matches the current QA package."""

    text = guide_path.read_text(encoding="utf-8")
    guide = build_2d_animation_playtest_execution_guide(
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        triage_path,
        route_batch_path,
        progress_path=progress_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    progress = guide.progress
    gate = progress.release_gate
    route_batch_args = (
        ""
        if gate.session.route_batches is None
        else f" --route-batches {_shell_arg(gate.session.route_batches.path)}"
    )
    validation_context_args = (
        f" --scenario {_shell_arg(guide.scenario_id)}"
        f" --seed {guide.seed}"
        f" --command-prefix {_shell_arg(guide.command_prefix)}"
    )
    progress_validation_command = (
        f"{guide.command_prefix} validate-animation-playtest-progress "
        f"{_shell_arg(guide.progress_path)} "
        f"{_shell_arg(gate.session.report.path)} {_shell_arg(gate.session.commands.path)} "
        f"{_shell_arg(gate.session.plan.path)} "
        f"{_shell_arg(gate.session.recorder_queue.path)} "
        f"{_shell_arg(gate.triage_validation.path)}{route_batch_args}"
        f"{validation_context_args}"
    )
    guide_validation_command = (
        f"{guide.command_prefix} validate-animation-playtest-execution-guide "
        f"{_shell_arg(guide_path)} "
        f"{_shell_arg(gate.session.report.path)} {_shell_arg(gate.session.commands.path)} "
        f"{_shell_arg(gate.session.plan.path)} "
        f"{_shell_arg(gate.session.recorder_queue.path)} "
        f"{_shell_arg(gate.triage_validation.path)}{route_batch_args}"
        f" --progress-path {_shell_arg(guide.progress_path)}"
        f"{validation_context_args}"
    )
    report_validation_command = (
        f"{guide.command_prefix} validate-animation-playtest-report "
        f"{_shell_arg(gate.session.report.path)}"
    )
    findings: list[str] = []
    required_lines = (
        "# NEXUS TECH 2D Animation Execution Guide",
        f"- Status: `{guide.status}`",
        f"- Completion: `{progress.completion_percent}%`",
        f"- Open progress items: `{progress.open_item_count}`",
        f"- Open recorder steps: `{guide.open_step_count}`",
        f"- Manual result: `{gate.manual_result}`",
        f"- Report: `{gate.session.report.path}`",
        f"- Command queue: `{gate.session.commands.path}`",
        f"- Plan: `{gate.session.plan.path}`",
        f"- Recorder queue: `{gate.session.recorder_queue.path}`",
        f"- Progress board: `{guide.progress_path}`",
        f"- Next manual area: `{gate.recorder_hint.area}`",
        f"- Next manual target: `{gate.recorder_hint.target}`",
        (
            "- Completion gate: "
            "`record real visible-window evidence, then rerun progress, release-gate, "
            "and report validators`"
        ),
        _ANIMATION_EXECUTION_GUIDE_POLICY_LINE,
        progress_validation_command,
        guide_validation_command,
        report_validation_command,
    )
    for line in required_lines:
        if line not in text:
            findings.append(f"missing execution guide guard: {line}")

    rows = _extract_markdown_table_rows(text)
    execution_rows = tuple(row for row in rows if len(row) >= 9 and row[0].isdigit())
    if len(execution_rows) != len(guide.recorder_steps):
        findings.append(
            f"expected {len(guide.recorder_steps)} execution rows, found {len(execution_rows)}"
        )

    rows_by_step: dict[int, tuple[str, ...]] = {}
    for row in execution_rows:
        step = int(row[0])
        if step in rows_by_step:
            findings.append(f"duplicate execution guide step: {step}")
            continue
        rows_by_step[step] = row

    for index, hint in enumerate(guide.recorder_steps, start=1):
        row = rows_by_step.get(index)
        if row is None:
            findings.append(f"missing execution guide row: {index}")
            continue
        _validate_execution_guide_row(findings, index, row, hint)

    return AnimationPlaytestExecutionGuideValidation(
        path=str(guide_path),
        expected_count=len(guide.recorder_steps),
        findings=tuple(findings),
    )


def build_2d_animation_playtest_issue_backlog(
    report_path: Path,
) -> AnimationPlaytestIssueBacklog:
    """Build a fix/evidence backlog from the current manual animation report."""

    text = report_path.read_text(encoding="utf-8")
    validation = validate_2d_animation_playtest_report(report_path)
    issues: list[AnimationPlaytestIssue] = []

    for row in _extract_report_section_table_rows(text, "Automated Gate Summary"):
        if len(row) < 3 or _normalize_report_key(row[0]) == "gate":
            continue
        _append_animation_issue(
            issues,
            area="Automated Gate",
            target=row[0],
            result=row[1],
            evidence=row[2],
            follow_up="-",
        )

    for row in _extract_report_section_table_rows(text, "Window Matrix"):
        if len(row) < 5 or _normalize_report_key(row[0]) == "window":
            continue
        window = _strip_markdown_code(row[0])
        for result_index, mode in enumerate(("full", "reduced", "off"), start=1):
            _append_animation_issue(
                issues,
                area="Window Matrix",
                target=f"{window} {mode}",
                result=row[result_index],
                evidence=row[4],
                follow_up="-",
            )

    for row in _extract_report_section_table_rows(text, "Visible Route Evidence"):
        if len(row) < 6 or not row[0].isdigit():
            continue
        target = (
            f"step {row[0]} {_strip_markdown_code(row[1])} "
            f"{_strip_markdown_code(row[2])} {_strip_markdown_code(row[3])}"
        )
        _append_animation_issue(
            issues,
            area="Visible Route Evidence",
            target=target,
            result=row[4],
            evidence=row[5],
            follow_up="-",
        )

    for row in _extract_report_section_table_rows(text, "Control Clarity Results"):
        if len(row) < 4 or _normalize_report_key(row[0]) == "control area":
            continue
        _append_animation_issue(
            issues,
            area="Control Clarity Results",
            target=row[0],
            result=row[1],
            evidence=row[2],
            follow_up=row[3],
        )

    for row in _extract_report_section_table_rows(text, "Scene Results"):
        if len(row) < 5 or _normalize_report_key(row[0]) == "scene":
            continue
        evidence = f"readability: {row[2]}; motion: {row[3]}"
        _append_animation_issue(
            issues,
            area="Scene Results",
            target=row[0],
            result=row[1],
            evidence=evidence,
            follow_up=row[4],
        )

    for row in _extract_report_section_table_rows(text, "Game Feel Results"):
        if len(row) < 4 or _normalize_report_key(row[0]) == "feedback area":
            continue
        _append_animation_issue(
            issues,
            area="Game Feel Results",
            target=row[0],
            result=row[1],
            evidence=row[2],
            follow_up=row[3],
        )

    release_decision = _extract_report_field(text, "Release decision")
    _append_animation_issue(
        issues,
        area="Decision",
        target="Release decision",
        result=release_decision,
        evidence=release_decision or "missing release decision",
        follow_up=_extract_report_field(text, "Required fixes before presenting") or "-",
    )

    for field_name in REQUIRED_ANIMATION_PLAYTEST_BLOCKER_FIELDS:
        value = _extract_report_field(text, field_name)
        if _is_clear_signoff_value(value):
            continue
        _append_manual_report_field_issue(
            issues,
            field_name=field_name,
            value=value,
            priority="P0",
        )

    for field_name in REQUIRED_ANIMATION_PLAYTEST_DECISION_FIELDS:
        value = _extract_report_field(text, field_name)
        if field_name == "Validator result":
            if _is_passing_result(value):
                continue
            priority = "P0"
        elif field_name == "Required fixes before presenting":
            if _is_clear_signoff_value(value):
                continue
            priority = "P1"
        else:
            if not _is_placeholder_field(value):
                continue
            priority = "P2"
        _append_manual_report_field_issue(
            issues,
            field_name=field_name,
            value=value,
            priority=priority,
        )

    return AnimationPlaytestIssueBacklog(
        report=validation,
        issues=tuple(issues),
    )


def write_2d_animation_playtest_issue_backlog(
    backlog: AnimationPlaytestIssueBacklog,
    output_path: Path,
) -> None:
    """Write the manual animation issue backlog as Markdown."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NEXUS TECH 2D Animation Issue Backlog",
        "",
        f"- Status: `{backlog.status}`",
        f"- Report: `{backlog.report.path}`",
        f"- Report validation: `{backlog.report.status}`",
        f"- Release decision: `{backlog.report.release_decision or '-'}`",
        f"- Total issues: `{backlog.issue_count}`",
        f"- P0 issues: `{backlog.p0_count}`",
        f"- P1 issues: `{backlog.p1_count}`",
        f"- P2 issues: `{backlog.p2_count}`",
        _ANIMATION_ISSUE_BACKLOG_POLICY_LINE,
        "",
        "## Issue Queue",
        "",
        "| Priority | Status | Area | Target | Result | Evidence | Follow-up | Next Action |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for issue in backlog.issues:
        lines.append(_format_animation_issue_row(issue))
    lines.extend(
        [
            "",
            "## Validation Commands",
            "",
            "```bash",
            (
                "uv run nexus-tech validate-animation-playtest-report "
                f"{_shell_arg(backlog.report.path)}"
            ),
            (
                f"uv run nexus-tech validate-animation-playtest-issue-backlog "
                f"{_shell_arg(output_path)} {_shell_arg(backlog.report.path)}"
            ),
            "```",
            "",
            "## Backlog Rules",
            "",
            "- P0 items block release and need a code or content fix before signoff.",
            "- P1 items need an explicit watch/fix decision before release candidate.",
            "- P2 items mean tester evidence is still missing or placeholder text remains.",
            "- Regenerate this backlog after every manual report edit.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_2d_animation_playtest_issue_backlog(
    backlog_path: Path,
    report_path: Path,
) -> AnimationPlaytestIssueBacklogValidation:
    """Validate that an issue backlog matches the current manual report."""

    text = backlog_path.read_text(encoding="utf-8")
    backlog = build_2d_animation_playtest_issue_backlog(report_path)
    findings: list[str] = []
    required_lines = (
        "# NEXUS TECH 2D Animation Issue Backlog",
        f"- Status: `{backlog.status}`",
        f"- Report: `{backlog.report.path}`",
        f"- Report validation: `{backlog.report.status}`",
        f"- Release decision: `{backlog.report.release_decision or '-'}`",
        f"- Total issues: `{backlog.issue_count}`",
        f"- P0 issues: `{backlog.p0_count}`",
        f"- P1 issues: `{backlog.p1_count}`",
        f"- P2 issues: `{backlog.p2_count}`",
        _ANIMATION_ISSUE_BACKLOG_POLICY_LINE,
        f"uv run nexus-tech validate-animation-playtest-report {_shell_arg(backlog.report.path)}",
        (
            f"uv run nexus-tech validate-animation-playtest-issue-backlog "
            f"{_shell_arg(backlog_path)} {_shell_arg(backlog.report.path)}"
        ),
    )
    for line in required_lines:
        if line not in text:
            findings.append(f"missing issue backlog guard: {line}")

    rows = _extract_markdown_table_rows(text)
    issue_rows = tuple(row for row in rows if len(row) >= 8 and row[0] in {"P0", "P1", "P2"})
    if len(issue_rows) != len(backlog.issues):
        findings.append(f"expected {len(backlog.issues)} issue rows, found {len(issue_rows)}")

    expected_rows = tuple(_format_animation_issue_row(issue) for issue in backlog.issues)
    actual_rows = tuple(
        "| " + " | ".join(_markdown_table_cell(cell) for cell in row) + " |" for row in issue_rows
    )
    for expected in expected_rows:
        if expected not in actual_rows:
            findings.append(f"missing issue backlog row: {expected}")

    return AnimationPlaytestIssueBacklogValidation(
        path=str(backlog_path),
        expected_count=len(backlog.issues),
        findings=tuple(findings),
    )


def build_2d_animation_playtest_sprint_packet(
    report_path: Path,
    command_path: Path,
    plan_path: Path,
    recorder_queue_path: Path,
    triage_path: Path,
    route_batch_path: Path | None = None,
    *,
    progress_path: Path = Path("/tmp/nexus-tech-animation-progress.md"),
    execution_guide_path: Path = Path("/tmp/nexus-tech-animation-execution-guide.md"),
    issue_backlog_path: Path = Path("/tmp/nexus-tech-animation-issues.md"),
    max_observation_steps: int = 12,
    scenario_id: str = "founder_journey",
    seed: int = 7,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    command_prefix: str = "uv run nexus-tech",
) -> AnimationPlaytestSprintPacket:
    """Build a focused manual animation QA sprint without recording evidence."""

    guide = build_2d_animation_playtest_execution_guide(
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        triage_path,
        route_batch_path,
        progress_path=progress_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    backlog = build_2d_animation_playtest_issue_backlog(report_path)
    open_steps = tuple(step for step in guide.recorder_steps if step.status != "pass")
    capped_count = max(1, max_observation_steps)
    blocker_issues = tuple(issue for issue in backlog.issues if issue.priority in {"P0", "P1"})
    return AnimationPlaytestSprintPacket(
        execution_guide=guide,
        issue_backlog=backlog,
        execution_guide_path=str(execution_guide_path),
        issue_backlog_path=str(issue_backlog_path),
        observation_steps=open_steps[:capped_count],
        blocker_issues=blocker_issues,
        max_observation_steps=capped_count,
    )


def write_2d_animation_playtest_sprint_packet(
    sprint: AnimationPlaytestSprintPacket,
    output_path: Path,
) -> None:
    """Write one focused manual animation QA sprint packet as Markdown."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    guide = sprint.execution_guide
    progress = guide.progress
    gate = progress.release_gate
    route_batch_args = (
        ""
        if gate.session.route_batches is None
        else f" --route-batches {_shell_arg(gate.session.route_batches.path)}"
    )
    validation_context_args = (
        f" --scenario {_shell_arg(guide.scenario_id)}"
        f" --seed {guide.seed}"
        f" --command-prefix {_shell_arg(guide.command_prefix)}"
    )
    sprint_validation_command = (
        f"{guide.command_prefix} validate-animation-playtest-sprint "
        f"{_shell_arg(output_path)} "
        f"{_shell_arg(gate.session.report.path)} {_shell_arg(gate.session.commands.path)} "
        f"{_shell_arg(gate.session.plan.path)} "
        f"{_shell_arg(gate.session.recorder_queue.path)} "
        f"{_shell_arg(gate.triage_validation.path)}{route_batch_args}"
        f" --progress-path {_shell_arg(guide.progress_path)}"
        f" --execution-guide-path {_shell_arg(sprint.execution_guide_path)}"
        f" --issue-backlog-path {_shell_arg(sprint.issue_backlog_path)}"
        f" --max-observation-steps {sprint.max_observation_steps}"
        f"{validation_context_args}"
    )
    guide_validation_command = (
        f"{guide.command_prefix} validate-animation-playtest-execution-guide "
        f"{_shell_arg(sprint.execution_guide_path)} "
        f"{_shell_arg(gate.session.report.path)} {_shell_arg(gate.session.commands.path)} "
        f"{_shell_arg(gate.session.plan.path)} "
        f"{_shell_arg(gate.session.recorder_queue.path)} "
        f"{_shell_arg(gate.triage_validation.path)}{route_batch_args}"
        f" --progress-path {_shell_arg(guide.progress_path)}"
        f"{validation_context_args}"
    )
    backlog_validation_command = (
        f"{guide.command_prefix} validate-animation-playtest-issue-backlog "
        f"{_shell_arg(sprint.issue_backlog_path)} {_shell_arg(sprint.issue_backlog.report.path)}"
    )
    report_validation_command = (
        f"{guide.command_prefix} validate-animation-playtest-report "
        f"{_shell_arg(gate.session.report.path)}"
    )
    lines = [
        "# NEXUS TECH 2D Animation Sprint Packet",
        "",
        f"- Status: `{sprint.status}`",
        f"- Completion: `{progress.completion_percent}%`",
        f"- Report: `{gate.session.report.path}`",
        f"- Command queue: `{gate.session.commands.path}`",
        f"- Progress board: `{guide.progress_path}`",
        f"- Execution guide: `{sprint.execution_guide_path}`",
        f"- Issue backlog: `{sprint.issue_backlog_path}`",
        f"- Observation steps: `{sprint.open_observation_count}`",
        f"- Max observation steps: `{sprint.max_observation_steps}`",
        f"- Observation checklist items: `{sprint.checklist_count}`",
        f"- Execution batches: `{sprint.execution_batch_count}`",
        f"- Layout repair checks: `{sprint.layout_repair_count}`",
        f"- Layout recording rows: `{sprint.layout_recording_count}`",
        f"- Navigation recovery drills: `{sprint.navigation_drill_count}`",
        f"- Navigation recording rows: `{sprint.navigation_recording_count}`",
        f"- Defect intake rows: `{sprint.defect_intake_count}`",
        f"- Exit criteria: `{sprint.exit_criteria_count}`",
        f"- Evidence capture rows: `{sprint.evidence_capture_count}`",
        f"- Evidence note templates: `{sprint.evidence_template_count}`",
        f"- P0/P1 blockers: `{sprint.blocker_count}`",
        f"- Backlog status: `{sprint.issue_backlog.status}`",
        f"- Next manual area: `{gate.recorder_hint.area}`",
        f"- Next manual target: `{gate.recorder_hint.target}`",
        _ANIMATION_SPRINT_POLICY_LINE,
        "",
        "## Sprint Order",
        "",
        "| Step | Action | Required Result |",
        "| ---: | --- | --- |",
        (
            "| 1 | Work the observation queue from top to bottom. | "
            "Visible window was inspected before editing report rows. |"
        ),
        (
            "| 2 | Replace recorder placeholders only with real notes. | "
            "Report rows move from todo/watch/fail based on observed behavior. |"
        ),
        (
            "| 3 | Review the P0/P1 blocker queue after observation. | "
            "Code fixes, risk decisions, or clear signoff fields are explicit. |"
        ),
        "| 4 | Run the validation commands. | Sprint, guide, backlog, and report status agree. |",
        "",
        "## Next Sprint Action",
        "",
        "| Area | Target | Visible Command | Required Terms | Recorder Command |",
        "| --- | --- | --- | --- | --- |",
        _format_animation_sprint_next_action_row(sprint.next_observation),
        "",
        "## Next Sprint Copy Commands",
        "",
        "```bash",
        *_animation_sprint_next_action_copy_commands(sprint.next_observation),
        "```",
        "",
        "## Manual Execution Batches",
        "",
        "| Batch | Visible Scope | Record After | Stop / Escalate If |",
        "| --- | --- | --- | --- |",
    ]
    for batch in _ANIMATION_SPRINT_EXECUTION_BATCHES:
        lines.append(_format_animation_sprint_execution_batch_row(batch))
    lines.extend(
        [
            "",
            "## Manual Observation Checklist",
            "",
            "| Check | Pass Criteria | Evidence Must Name |",
            "| --- | --- | --- |",
        ]
    )
    for checklist_item in _ANIMATION_SPRINT_OBSERVATION_CHECKS:
        lines.append(_format_animation_sprint_checklist_row(checklist_item))
    lines.extend(
        [
            "",
            "## Layout Repair Pass",
            "",
            "| Focus | Applies To | Pass Criteria | Repair Rule |",
            "| --- | --- | --- | --- |",
        ]
    )
    for repair_row in _ANIMATION_SPRINT_LAYOUT_REPAIR_ROWS:
        lines.append(_format_animation_sprint_layout_repair_row(repair_row))
    lines.extend(
        [
            "",
            "## Layout Recording Map",
            "",
            "| Focus | Report Row | Required Terms | Recorder Command |",
            "| --- | --- | --- | --- |",
        ]
    )
    for recording_row in _ANIMATION_SPRINT_LAYOUT_RECORDING_ROWS:
        lines.append(
            _format_animation_sprint_layout_recording_row(
                recording_row,
                report_path=Path(gate.session.report.path),
                command_prefix=guide.command_prefix,
            )
        )
    lines.extend(
        [
            "",
            "## Navigation Recovery Drills",
            "",
            "| Drill | Manual Action | Pass Criteria | Escalation Rule |",
            "| --- | --- | --- | --- |",
        ]
    )
    for drill in _ANIMATION_SPRINT_NAVIGATION_RECOVERY_DRILLS:
        lines.append(_format_animation_sprint_navigation_drill_row(drill))
    lines.extend(
        [
            "",
            "## Navigation Recording Map",
            "",
            "| Drill Group | Report Row | Required Terms | Recorder Command |",
            "| --- | --- | --- | --- |",
        ]
    )
    for recording_row in _ANIMATION_SPRINT_NAVIGATION_RECORDING_ROWS:
        lines.append(
            _format_animation_sprint_navigation_recording_row(
                recording_row,
                report_path=Path(gate.session.report.path),
                command_prefix=guide.command_prefix,
            )
        )
    lines.extend(
        [
            "",
            "## Manual Defect Intake",
            "",
            "| Trigger | Priority | Evidence Must Name | Required Action |",
            "| --- | --- | --- | --- |",
        ]
    )
    for intake_row in _ANIMATION_SPRINT_DEFECT_INTAKE_ROWS:
        lines.append(_format_animation_sprint_defect_intake_row(intake_row))
    lines.extend(
        [
            "",
            "## Sprint Exit Criteria",
            "",
            "| Criteria | Done Means | Validation Guard |",
            "| --- | --- | --- |",
        ]
    )
    for exit_criteria in _ANIMATION_SPRINT_EXIT_CRITERIA:
        lines.append(_format_animation_sprint_exit_criteria_row(exit_criteria))
    lines.extend(
        [
            "",
            "## Evidence Capture Prompts",
            "",
            "| Step | Capture Focus | Result Choices | Defect Decision | Evidence Must Name |",
            "| ---: | --- | --- | --- | --- |",
        ]
    )
    for index, hint in enumerate(sprint.observation_steps, start=1):
        lines.append(_format_animation_sprint_evidence_capture_row(index, hint))
    lines.extend(
        [
            "",
            "## Evidence Note Templates",
            "",
            "| Result | Use When | Note Must Include | Template Skeleton |",
            "| --- | --- | --- | --- |",
        ]
    )
    for note_template in _ANIMATION_SPRINT_EVIDENCE_NOTE_TEMPLATES:
        lines.append(_format_animation_sprint_evidence_note_template_row(note_template))
    lines.extend(
        [
            "",
            "## Observation Queue",
            "",
            (
                "| Step | Phase | Status | Area | Target | Visible Command | Required Terms | "
                "Evidence Prompt | Recorder Command |"
            ),
            "| ---: | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for index, hint in enumerate(sprint.observation_steps, start=1):
        lines.append(_format_animation_sprint_observation_row(index, hint))
    lines.extend(
        [
            "",
            "## P0/P1 Blocker Queue",
            "",
            (
                "| Priority | Status | Phase | Area | Target | Result | "
                "Evidence Dependency | Next Action |"
            ),
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for issue in sprint.blocker_issues:
        lines.append(_format_animation_sprint_blocker_row(issue))
    lines.extend(
        [
            "",
            "## Validation Commands",
            "",
            "```bash",
            guide_validation_command,
            backlog_validation_command,
            sprint_validation_command,
            report_validation_command,
            "```",
            "",
            "## Sprint Rules",
            "",
            "- This packet is a work order, not release evidence.",
            "- Visible commands must be observed before recorder commands are used.",
            (
                "- Leave P0/P1 blockers open when notes show a real UI, layout, "
                "control, or motion defect."
            ),
            "- Regenerate this packet after every report edit or code fix.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_2d_animation_playtest_sprint_packet(
    sprint_path: Path,
    report_path: Path,
    command_path: Path,
    plan_path: Path,
    recorder_queue_path: Path,
    triage_path: Path,
    route_batch_path: Path | None = None,
    *,
    progress_path: Path = Path("/tmp/nexus-tech-animation-progress.md"),
    execution_guide_path: Path = Path("/tmp/nexus-tech-animation-execution-guide.md"),
    issue_backlog_path: Path = Path("/tmp/nexus-tech-animation-issues.md"),
    max_observation_steps: int = 12,
    scenario_id: str = "founder_journey",
    seed: int = 7,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    command_prefix: str = "uv run nexus-tech",
) -> AnimationPlaytestSprintPacketValidation:
    """Validate that a sprint packet matches the current animation QA package."""

    text = sprint_path.read_text(encoding="utf-8")
    sprint = build_2d_animation_playtest_sprint_packet(
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        triage_path,
        route_batch_path,
        progress_path=progress_path,
        execution_guide_path=execution_guide_path,
        issue_backlog_path=issue_backlog_path,
        max_observation_steps=max_observation_steps,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    guide = sprint.execution_guide
    progress = guide.progress
    gate = progress.release_gate
    route_batch_args = (
        ""
        if gate.session.route_batches is None
        else f" --route-batches {_shell_arg(gate.session.route_batches.path)}"
    )
    validation_context_args = (
        f" --scenario {_shell_arg(guide.scenario_id)}"
        f" --seed {guide.seed}"
        f" --command-prefix {_shell_arg(guide.command_prefix)}"
    )
    sprint_validation_command = (
        f"{guide.command_prefix} validate-animation-playtest-sprint "
        f"{_shell_arg(sprint_path)} "
        f"{_shell_arg(gate.session.report.path)} {_shell_arg(gate.session.commands.path)} "
        f"{_shell_arg(gate.session.plan.path)} "
        f"{_shell_arg(gate.session.recorder_queue.path)} "
        f"{_shell_arg(gate.triage_validation.path)}{route_batch_args}"
        f" --progress-path {_shell_arg(guide.progress_path)}"
        f" --execution-guide-path {_shell_arg(sprint.execution_guide_path)}"
        f" --issue-backlog-path {_shell_arg(sprint.issue_backlog_path)}"
        f" --max-observation-steps {sprint.max_observation_steps}"
        f"{validation_context_args}"
    )
    guide_validation_command = (
        f"{guide.command_prefix} validate-animation-playtest-execution-guide "
        f"{_shell_arg(sprint.execution_guide_path)} "
        f"{_shell_arg(gate.session.report.path)} {_shell_arg(gate.session.commands.path)} "
        f"{_shell_arg(gate.session.plan.path)} "
        f"{_shell_arg(gate.session.recorder_queue.path)} "
        f"{_shell_arg(gate.triage_validation.path)}{route_batch_args}"
        f" --progress-path {_shell_arg(guide.progress_path)}"
        f"{validation_context_args}"
    )
    backlog_validation_command = (
        f"{guide.command_prefix} validate-animation-playtest-issue-backlog "
        f"{_shell_arg(sprint.issue_backlog_path)} {_shell_arg(sprint.issue_backlog.report.path)}"
    )
    report_validation_command = (
        f"{guide.command_prefix} validate-animation-playtest-report "
        f"{_shell_arg(gate.session.report.path)}"
    )
    findings: list[str] = []
    required_lines = (
        "# NEXUS TECH 2D Animation Sprint Packet",
        f"- Status: `{sprint.status}`",
        f"- Completion: `{progress.completion_percent}%`",
        f"- Report: `{gate.session.report.path}`",
        f"- Command queue: `{gate.session.commands.path}`",
        f"- Progress board: `{guide.progress_path}`",
        f"- Execution guide: `{sprint.execution_guide_path}`",
        f"- Issue backlog: `{sprint.issue_backlog_path}`",
        f"- Observation steps: `{sprint.open_observation_count}`",
        f"- Max observation steps: `{sprint.max_observation_steps}`",
        f"- Observation checklist items: `{sprint.checklist_count}`",
        f"- Execution batches: `{sprint.execution_batch_count}`",
        f"- Layout repair checks: `{sprint.layout_repair_count}`",
        f"- Layout recording rows: `{sprint.layout_recording_count}`",
        f"- Navigation recovery drills: `{sprint.navigation_drill_count}`",
        f"- Navigation recording rows: `{sprint.navigation_recording_count}`",
        f"- Defect intake rows: `{sprint.defect_intake_count}`",
        f"- Exit criteria: `{sprint.exit_criteria_count}`",
        f"- Evidence capture rows: `{sprint.evidence_capture_count}`",
        f"- Evidence note templates: `{sprint.evidence_template_count}`",
        f"- P0/P1 blockers: `{sprint.blocker_count}`",
        f"- Backlog status: `{sprint.issue_backlog.status}`",
        f"- Next manual area: `{gate.recorder_hint.area}`",
        f"- Next manual target: `{gate.recorder_hint.target}`",
        _ANIMATION_SPRINT_POLICY_LINE,
        guide_validation_command,
        backlog_validation_command,
        sprint_validation_command,
        report_validation_command,
        "## Next Sprint Action",
        "| Area | Target | Visible Command | Required Terms | Recorder Command |",
        _format_animation_sprint_next_action_row(sprint.next_observation),
        "## Next Sprint Copy Commands",
        *_animation_sprint_next_action_copy_commands(sprint.next_observation),
        "## Manual Execution Batches",
        "| Batch | Visible Scope | Record After | Stop / Escalate If |",
        *(
            _format_animation_sprint_execution_batch_row(batch)
            for batch in _ANIMATION_SPRINT_EXECUTION_BATCHES
        ),
        "## Manual Observation Checklist",
        "| Check | Pass Criteria | Evidence Must Name |",
        *(
            _format_animation_sprint_checklist_row(checklist_item)
            for checklist_item in _ANIMATION_SPRINT_OBSERVATION_CHECKS
        ),
        "## Layout Repair Pass",
        "| Focus | Applies To | Pass Criteria | Repair Rule |",
        *(
            _format_animation_sprint_layout_repair_row(repair_row)
            for repair_row in _ANIMATION_SPRINT_LAYOUT_REPAIR_ROWS
        ),
        "## Layout Recording Map",
        "| Focus | Report Row | Required Terms | Recorder Command |",
        *(
            _format_animation_sprint_layout_recording_row(
                recording_row,
                report_path=Path(gate.session.report.path),
                command_prefix=guide.command_prefix,
            )
            for recording_row in _ANIMATION_SPRINT_LAYOUT_RECORDING_ROWS
        ),
        "## Navigation Recovery Drills",
        "| Drill | Manual Action | Pass Criteria | Escalation Rule |",
        *(
            _format_animation_sprint_navigation_drill_row(drill)
            for drill in _ANIMATION_SPRINT_NAVIGATION_RECOVERY_DRILLS
        ),
        "## Navigation Recording Map",
        "| Drill Group | Report Row | Required Terms | Recorder Command |",
        *(
            _format_animation_sprint_navigation_recording_row(
                recording_row,
                report_path=Path(gate.session.report.path),
                command_prefix=guide.command_prefix,
            )
            for recording_row in _ANIMATION_SPRINT_NAVIGATION_RECORDING_ROWS
        ),
        "## Manual Defect Intake",
        "| Trigger | Priority | Evidence Must Name | Required Action |",
        *(
            _format_animation_sprint_defect_intake_row(intake_row)
            for intake_row in _ANIMATION_SPRINT_DEFECT_INTAKE_ROWS
        ),
        "## Sprint Exit Criteria",
        "| Criteria | Done Means | Validation Guard |",
        *(
            _format_animation_sprint_exit_criteria_row(exit_criteria)
            for exit_criteria in _ANIMATION_SPRINT_EXIT_CRITERIA
        ),
        "## Evidence Capture Prompts",
        "| Step | Capture Focus | Result Choices | Defect Decision | Evidence Must Name |",
        *(
            _format_animation_sprint_evidence_capture_row(index, hint)
            for index, hint in enumerate(sprint.observation_steps, start=1)
        ),
        "## Evidence Note Templates",
        "| Result | Use When | Note Must Include | Template Skeleton |",
        *(
            _format_animation_sprint_evidence_note_template_row(note_template)
            for note_template in _ANIMATION_SPRINT_EVIDENCE_NOTE_TEMPLATES
        ),
    )
    for line in required_lines:
        if line not in text:
            findings.append(f"missing sprint packet guard: {line}")

    try:
        guide_validation = validate_2d_animation_playtest_execution_guide(
            execution_guide_path,
            report_path,
            command_path,
            plan_path,
            recorder_queue_path,
            triage_path,
            route_batch_path,
            progress_path=progress_path,
            scenario_id=scenario_id,
            seed=seed,
            windows=windows,
            motion_modes=motion_modes,
            command_prefix=command_prefix,
        )
    except FileNotFoundError:
        findings.append(f"missing sprint execution guide artifact: {execution_guide_path}")
    else:
        findings.extend(f"execution guide: {finding}" for finding in guide_validation.findings)

    try:
        backlog_validation = validate_2d_animation_playtest_issue_backlog(
            issue_backlog_path,
            report_path,
        )
    except FileNotFoundError:
        findings.append(f"missing sprint issue backlog artifact: {issue_backlog_path}")
    else:
        findings.extend(f"issue backlog: {finding}" for finding in backlog_validation.findings)

    rows = _extract_markdown_table_rows(text)
    observation_rows = tuple(row for row in rows if len(row) >= 9 and row[0].isdigit())
    if len(observation_rows) != len(sprint.observation_steps):
        findings.append(
            f"expected {len(sprint.observation_steps)} sprint observation rows, "
            f"found {len(observation_rows)}"
        )
    rows_by_step: dict[int, tuple[str, ...]] = {}
    for row in observation_rows:
        step = int(row[0])
        if step in rows_by_step:
            findings.append(f"duplicate sprint observation row: {step}")
            continue
        rows_by_step[step] = row
    for index, hint in enumerate(sprint.observation_steps, start=1):
        row = rows_by_step.get(index)
        if row is None:
            findings.append(f"missing sprint observation row: {index}")
            continue
        _validate_execution_guide_row(findings, index, row, hint)

    blocker_rows = tuple(row for row in rows if len(row) >= 8 and row[0] in {"P0", "P1"})
    if len(blocker_rows) != len(sprint.blocker_issues):
        findings.append(
            f"expected {len(sprint.blocker_issues)} sprint blocker rows, found {len(blocker_rows)}"
        )
    expected_blocker_rows = tuple(
        _format_animation_sprint_blocker_row(issue) for issue in sprint.blocker_issues
    )
    actual_blocker_rows = tuple(
        "| " + " | ".join(_markdown_table_cell(cell) for cell in row) + " |" for row in blocker_rows
    )
    for expected in expected_blocker_rows:
        if expected not in actual_blocker_rows:
            findings.append(f"missing sprint blocker row: {expected}")

    return AnimationPlaytestSprintPacketValidation(
        path=str(sprint_path),
        expected_observation_count=len(sprint.observation_steps),
        expected_blocker_count=len(sprint.blocker_issues),
        findings=tuple(findings),
    )


def _append_animation_issue(
    issues: list[AnimationPlaytestIssue],
    *,
    area: str,
    target: str,
    result: str,
    evidence: str,
    follow_up: str,
) -> None:
    normalized_result = _normalize_issue_result(result)
    if _is_passing_result(result) and not _is_placeholder_result(result):
        return
    priority = _animation_issue_priority(normalized_result)
    issues.append(
        AnimationPlaytestIssue(
            priority=priority,
            status=_animation_issue_status(normalized_result),
            area=area,
            target=_strip_markdown_code(target),
            result=normalized_result or "missing",
            evidence=_markdown_table_cell(evidence or "missing evidence"),
            follow_up=_markdown_table_cell(follow_up or "-"),
            next_action=_animation_issue_next_action(priority),
        )
    )


def _append_manual_report_field_issue(
    issues: list[AnimationPlaytestIssue],
    *,
    field_name: str,
    value: str,
    priority: str,
) -> None:
    normalized = _normalize_issue_result(value)
    issues.append(
        AnimationPlaytestIssue(
            priority=priority,
            status="manual-required" if priority == "P2" else "fix-needed",
            area="Report Field",
            target=field_name,
            result=normalized or "missing",
            evidence=_markdown_table_cell(value or "missing field value"),
            follow_up="-",
            next_action=_animation_issue_next_action(priority),
        )
    )


def _animation_issue_priority(normalized_result: str) -> str:
    if normalized_result == "fail":
        return "P0"
    if normalized_result == "watch":
        return "P1"
    return "P2"


def _normalize_issue_result(value: str) -> str:
    return _normalize_report_result(value).replace("`", "")


def _animation_issue_status(normalized_result: str) -> str:
    if normalized_result in {"fail", "watch"}:
        return "fix-needed"
    return "manual-required"


def _animation_issue_next_action(priority: str) -> str:
    if priority == "P0":
        return "Fix before release, rerun the visible command, and record new evidence."
    if priority == "P1":
        return "Triage before release candidate and decide fix or accepted watch risk."
    return "Run the manual check and replace placeholders with real observed evidence."


def animation_playtest_sprint_blocker_phase(issue: AnimationPlaytestIssue) -> str:
    """Classify how a sprint blocker should be handled during manual QA."""

    if issue.area == "Report Field" and _is_placeholder_result(issue.evidence):
        return "post-observation signoff"
    if issue.priority == "P1":
        return "watch-triage"
    return "fix-before-release"


def animation_playtest_sprint_blocker_dependency(issue: AnimationPlaytestIssue) -> str:
    """Return the evidence dependency that must be cleared for a sprint blocker."""

    phase = animation_playtest_sprint_blocker_phase(issue)
    if phase == "post-observation signoff":
        return "Complete visible observation rows, then clear or name this signoff blocker."
    if phase == "watch-triage":
        return "Record watch evidence, then decide accepted risk or follow-up fix."
    return "Fix the observed defect, rerun the visible command, then record evidence."


def animation_playtest_sprint_blocker_next_action(issue: AnimationPlaytestIssue) -> str:
    """Return the next action that is specific to the sprint blocker phase."""

    phase = animation_playtest_sprint_blocker_phase(issue)
    if phase == "post-observation signoff":
        return "Observe visible checks, then replace the signoff placeholder."
    if phase == "watch-triage":
        return "Triage watch evidence before the release candidate."
    return issue.next_action


def _format_animation_issue_row(issue: AnimationPlaytestIssue) -> str:
    return (
        "| "
        f"{_markdown_table_cell(issue.priority)} | "
        f"{_markdown_table_cell(issue.status)} | "
        f"{_markdown_table_cell(issue.area)} | "
        f"{_markdown_table_cell(issue.target)} | "
        f"{_markdown_table_cell(issue.result)} | "
        f"{_markdown_table_cell(issue.evidence)} | "
        f"{_markdown_table_cell(issue.follow_up)} | "
        f"{_markdown_table_cell(issue.next_action)} |"
    )


def _format_animation_sprint_blocker_row(issue: AnimationPlaytestIssue) -> str:
    return (
        "| "
        f"{_markdown_table_cell(issue.priority)} | "
        f"{_markdown_table_cell(issue.status)} | "
        f"{_markdown_table_cell(animation_playtest_sprint_blocker_phase(issue))} | "
        f"{_markdown_table_cell(issue.area)} | "
        f"{_markdown_table_cell(issue.target)} | "
        f"{_markdown_table_cell(issue.result)} | "
        f"{_markdown_table_cell(animation_playtest_sprint_blocker_dependency(issue))} | "
        f"{_markdown_table_cell(animation_playtest_sprint_blocker_next_action(issue))} |"
    )


def _format_animation_sprint_checklist_row(checklist_item: tuple[str, str, str]) -> str:
    check, pass_criteria, evidence_terms = checklist_item
    return (
        "| "
        f"{_markdown_table_cell(check)} | "
        f"{_markdown_table_cell(pass_criteria)} | "
        f"{_markdown_table_cell(evidence_terms)} |"
    )


def _format_animation_sprint_execution_batch_row(batch: tuple[str, str, str, str]) -> str:
    name, visible_scope, record_after, stop_condition = batch
    return (
        "| "
        f"{_markdown_table_cell(name)} | "
        f"{_markdown_table_cell(visible_scope)} | "
        f"{_markdown_table_cell(record_after)} | "
        f"{_markdown_table_cell(stop_condition)} |"
    )


def _format_animation_sprint_layout_repair_row(repair_row: tuple[str, str, str, str]) -> str:
    focus, applies_to, pass_criteria, repair_rule = repair_row
    return (
        "| "
        f"{_markdown_table_cell(focus)} | "
        f"{_markdown_table_cell(applies_to)} | "
        f"{_markdown_table_cell(pass_criteria)} | "
        f"{_markdown_table_cell(repair_rule)} |"
    )


def _format_animation_sprint_layout_recording_row(
    recording_row: tuple[str, str, str],
    *,
    report_path: Path,
    command_prefix: str,
) -> str:
    focus, row_type, target = recording_row
    if row_type == "window":
        required_terms = WINDOW_MATRIX_EVIDENCE_TERMS
        recorder_command = (
            f"{command_prefix} record-animation-playtest-window "
            f"{_shell_arg(report_path)} {_shell_arg(target)} "
            "--full pass --reduced pass --off pass "
            "--notes '<replace with observed window-matrix notes>'"
        )
    else:
        required_terms = CONTROL_EVIDENCE_TERMS[target]
        recorder_command = (
            f"{command_prefix} record-animation-playtest-control "
            f"{_shell_arg(report_path)} {_shell_arg(target)} --result pass "
            "--notes '<replace with observed evidence notes>' --follow-up none"
        )
    return (
        "| "
        f"{_markdown_table_cell(focus)} | "
        f"{_markdown_table_cell(target)} | "
        f"{_markdown_table_cell(', '.join(required_terms))} | "
        f"`{_markdown_table_cell(recorder_command)}` |"
    )


def _format_animation_sprint_navigation_drill_row(
    drill: tuple[str, str, str, str],
) -> str:
    name, manual_action, pass_criteria, escalation_rule = drill
    return (
        "| "
        f"{_markdown_table_cell(name)} | "
        f"{_markdown_table_cell(manual_action)} | "
        f"{_markdown_table_cell(pass_criteria)} | "
        f"{_markdown_table_cell(escalation_rule)} |"
    )


def _format_animation_sprint_navigation_recording_row(
    recording_row: tuple[str, str],
    *,
    report_path: Path,
    command_prefix: str,
) -> str:
    drill_group, report_row = recording_row
    required_terms = CONTROL_EVIDENCE_TERMS[report_row]
    recorder_command = (
        f"{command_prefix} record-animation-playtest-control "
        f"{_shell_arg(report_path)} {_shell_arg(report_row)} --result pass "
        "--notes '<replace with observed evidence notes>' --follow-up none"
    )
    return (
        "| "
        f"{_markdown_table_cell(drill_group)} | "
        f"{_markdown_table_cell(report_row)} | "
        f"{_markdown_table_cell(', '.join(required_terms))} | "
        f"`{_markdown_table_cell(recorder_command)}` |"
    )


def _format_animation_sprint_defect_intake_row(intake_row: tuple[str, str, str, str]) -> str:
    trigger, priority, evidence_terms, required_action = intake_row
    return (
        "| "
        f"{_markdown_table_cell(trigger)} | "
        f"{_markdown_table_cell(priority)} | "
        f"{_markdown_table_cell(evidence_terms)} | "
        f"{_markdown_table_cell(required_action)} |"
    )


def _format_animation_sprint_exit_criteria_row(exit_criteria: tuple[str, str, str]) -> str:
    criteria, done_means, validation_guard = exit_criteria
    return (
        "| "
        f"{_markdown_table_cell(criteria)} | "
        f"{_markdown_table_cell(done_means)} | "
        f"{_markdown_table_cell(validation_guard)} |"
    )


def _format_animation_sprint_evidence_capture_row(
    index: int,
    hint: AnimationPlaytestRecorderHint,
) -> str:
    required_terms = ", ".join(hint.required_terms) if hint.required_terms else "-"
    return (
        "| "
        f"{index} | "
        f"{_markdown_table_cell(hint.area)}: {_markdown_table_cell(hint.target)} | "
        "pass / watch / fail | "
        "Use Manual Defect Intake before recorder command. | "
        f"{_markdown_table_cell(required_terms)} |"
    )


def _format_animation_sprint_evidence_note_template_row(
    note_template: tuple[str, str, str, str],
) -> str:
    result, use_when, note_must_include, template_skeleton = note_template
    return (
        "| "
        f"{_markdown_table_cell(result)} | "
        f"{_markdown_table_cell(use_when)} | "
        f"{_markdown_table_cell(note_must_include)} | "
        f"{_markdown_table_cell(template_skeleton)} |"
    )


def _format_animation_sprint_next_action_row(
    hint: AnimationPlaytestRecorderHint | None,
) -> str:
    if hint is None:
        return "| none | none | `-` | - | `-` |"
    required_terms = ", ".join(hint.required_terms) if hint.required_terms else "-"
    visible_command = hint.visible_command or "-"
    return (
        "| "
        f"{_markdown_table_cell(hint.area)} | "
        f"{_markdown_table_cell(hint.target)} | "
        f"`{_markdown_table_cell(visible_command)}` | "
        f"{_markdown_table_cell(required_terms)} | "
        f"`{_markdown_table_cell(hint.recorder_command)}` |"
    )


def _animation_sprint_next_action_copy_commands(
    hint: AnimationPlaytestRecorderHint | None,
) -> tuple[str, ...]:
    if hint is None:
        return ("# No open sprint action.",)
    visible_command = hint.visible_command or "# No visible command for this row."
    return (
        visible_command,
        "# After observing the visible window, replace placeholder notes before running:",
        hint.recorder_command,
    )


def _format_animation_sprint_observation_row(
    index: int,
    hint: AnimationPlaytestRecorderHint,
) -> str:
    required_terms = ", ".join(hint.required_terms) if hint.required_terms else "-"
    visible_command = hint.visible_command or "-"
    return (
        "| "
        f"{index} | "
        f"{_markdown_table_cell(_execution_phase_for_area(hint.area))} | "
        f"`{_markdown_table_cell(hint.status)}` | "
        f"{_markdown_table_cell(hint.area)} | "
        f"{_markdown_table_cell(hint.target)} | "
        f"`{_markdown_table_cell(visible_command)}` | "
        f"{_markdown_table_cell(required_terms)} | "
        f"{_markdown_table_cell(hint.evidence_prompt)} | "
        f"`{_markdown_table_cell(hint.recorder_command)}` |"
    )


def _animation_ui_triage_profile(area: str) -> tuple[str, str, str]:
    return _ANIMATION_UI_TRIAGE_PROFILES.get(
        area,
        (
            "P2",
            "Manual QA",
            "Observed issue is named, reproducible, and attached to the current playtest report.",
        ),
    )


def _validate_ui_triage_row(
    findings: list[str],
    item: AnimationPlaytestUITriageItem,
    row: tuple[str, ...],
) -> None:
    priority = _strip_markdown_code(row[1])
    area = row[2].replace(r"\|", "|").strip()
    lane = row[3].replace(r"\|", "|").strip()
    status = _strip_markdown_code(row[4])
    open_items = row[5].strip()
    required_evidence = row[6].replace(r"\|", "|").strip()
    next_action = row[7].replace(r"\|", "|").strip()
    expected_values = (
        ("priority", priority, item.priority),
        ("area", area, item.area),
        ("lane", lane, item.lane),
        ("status", status, item.status),
        ("open items", open_items, str(item.open_items)),
        ("required evidence", required_evidence, item.required_evidence),
        ("next action", next_action, item.next_action),
    )
    for field, actual, expected in expected_values:
        if _normalize_report_key(actual) != _normalize_report_key(expected):
            findings.append(f"ui triage row {item.step} {field} is stale")


def _animation_progress_report_lane_totals(
    *,
    route_count: int,
    windows: tuple[tuple[int, int], ...],
    motion_modes: tuple[str, ...],
) -> dict[str, int]:
    """Return expected manual report item totals by progress lane."""

    return {
        "Automated Gates": len(REQUIRED_ANIMATION_PLAYTEST_AUTOMATED_GATES),
        "Manual Window Matrix": len(windows) * len(motion_modes),
        "Manual Route Evidence": route_count,
        "Manual Control Checks": len(DEFAULT_OPEN_WINDOW_PLAYTEST_CONTROL_CHECKS),
        "Manual Scene Checks": len(DEFAULT_OPEN_WINDOW_PLAYTEST_SCENE_CHECKS),
        "Manual Game Feel": len(DEFAULT_OPEN_WINDOW_PLAYTEST_FEEDBACK_CHECKS),
        "Manual Evidence Notes": 1,
        "Signoff Fields": (
            len(REQUIRED_ANIMATION_PLAYTEST_BUILD_FIELDS)
            + len(REQUIRED_ANIMATION_PLAYTEST_BLOCKER_FIELDS)
            + len(REQUIRED_ANIMATION_PLAYTEST_DECISION_FIELDS)
            + 1
        ),
        "Template Cleanup": 4,
    }


def _release_gate_check_next_action(
    gate: AnimationPlaytestReleaseGate,
    check_name: str,
) -> str:
    """Return the current release-gate next action for one check."""

    for check in gate.checks:
        if check.name == check_name:
            return check.next_action
    return "Review the current release gate before continuing."


def _validate_progress_lane_row(
    findings: list[str],
    lane: AnimationPlaytestProgressLane,
    row: tuple[str, ...],
) -> None:
    area = row[0].replace(r"\|", "|").strip()
    status = _strip_markdown_code(row[1])
    done = row[2].strip()
    open_items = row[3].strip()
    completion = row[4].strip()
    next_action = row[5].replace(r"\|", "|").strip()
    expected_values = (
        ("lane", area, lane.area),
        ("status", status, lane.status),
        ("done", done, f"{lane.completed_items}/{lane.total_items}"),
        ("open", open_items, str(lane.open_items)),
        ("completion", completion, f"{lane.completion_percent}%"),
        ("next action", next_action, lane.next_action),
    )
    for field, actual, expected in expected_values:
        if _normalize_report_key(actual) != _normalize_report_key(expected):
            findings.append(f"progress lane {lane.area} {field} is stale")


def _execution_phase_for_area(area: str) -> str:
    """Return the operator phase for one recorder area."""

    if area == "Visible Route Evidence":
        return "visible-route"
    if area in {"Manual Window Matrix", "Window Matrix"}:
        return "window-matrix"
    if area == "Control Clarity Results":
        return "control"
    if area == "Scene Results":
        return "scene"
    if area == "Game Feel Results":
        return "game-feel"
    if area in {"Build", "Release Blockers", "Decision", "Signoff Fields", "Report Field"}:
        return "signoff"
    if area == "Command Queue":
        return "artifact"
    return "cleanup"


def _validate_execution_guide_row(
    findings: list[str],
    index: int,
    row: tuple[str, ...],
    hint: AnimationPlaytestRecorderHint,
) -> None:
    phase = row[1].replace(r"\|", "|").strip()
    status = _strip_markdown_code(row[2])
    area = row[3].replace(r"\|", "|").strip()
    target = row[4].replace(r"\|", "|").strip()
    visible_command = _strip_markdown_code(row[5]).replace(r"\|", "|")
    required_terms = row[6].replace(r"\|", "|").strip()
    evidence_prompt = row[7].replace(r"\|", "|").strip()
    recorder_command = _strip_markdown_code(row[8]).replace(r"\|", "|")
    expected_terms = ", ".join(hint.required_terms) if hint.required_terms else "-"
    expected_visible_command = hint.visible_command or "-"
    expected_values = (
        ("phase", phase, _execution_phase_for_area(hint.area)),
        ("status", status, hint.status),
        ("area", area, hint.area),
        ("target", target, hint.target),
        ("visible command", visible_command, expected_visible_command),
        ("required terms", required_terms, expected_terms),
        ("evidence prompt", evidence_prompt, hint.evidence_prompt),
        ("recorder command", recorder_command, hint.recorder_command),
    )
    for field, actual, expected in expected_values:
        if _normalize_report_key(actual) != _normalize_report_key(expected):
            findings.append(f"execution guide row {index} {field} is stale")


def _validate_release_gate_row(
    findings: list[str],
    check: AnimationPlaytestReleaseGateCheck,
    row: tuple[str, ...],
) -> None:
    name = row[0].replace(r"\|", "|").strip()
    status = _strip_markdown_code(row[1])
    blockers = row[2].strip()
    next_action = row[3].replace(r"\|", "|").strip()
    expected_values = (
        ("check", name, check.name),
        ("status", status, check.status),
        ("blockers", blockers, str(check.blocker_count)),
        ("next action", next_action, check.next_action),
    )
    for field, actual, expected in expected_values:
        if _normalize_report_key(actual) != _normalize_report_key(expected):
            findings.append(f"release gate row {check.name} {field} is stale")


def _validate_release_gate_next_action(
    findings: list[str],
    hint: AnimationPlaytestRecorderHint,
    row: tuple[str, ...],
) -> None:
    area = row[0].replace(r"\|", "|").strip()
    target = row[1].replace(r"\|", "|").strip()
    status = _strip_markdown_code(row[2])
    required_terms = row[3].replace(r"\|", "|").strip()
    evidence_prompt = row[4].replace(r"\|", "|").strip()
    visible_command = _strip_markdown_code(row[5]).replace(r"\|", "|")
    recorder_command = _strip_markdown_code(row[6]).replace(r"\|", "|")
    expected_terms = ", ".join(hint.required_terms) if hint.required_terms else "-"
    expected_visible_command = hint.visible_command or "-"
    expected_values = (
        ("area", area, hint.area),
        ("target", target, hint.target),
        ("status", status, hint.status),
        ("required terms", required_terms, expected_terms),
        ("evidence prompt", evidence_prompt, hint.evidence_prompt),
        ("visible command", visible_command, expected_visible_command),
        ("recorder command", recorder_command, hint.recorder_command),
    )
    for field, actual, expected in expected_values:
        if _normalize_report_key(actual) != _normalize_report_key(expected):
            findings.append(f"release gate next action {field} is stale")


def _validate_recorder_queue_row(
    findings: list[str],
    index: int,
    row: tuple[str, ...],
    hint: AnimationPlaytestRecorderHint,
) -> None:
    status = _strip_markdown_code(row[1])
    area = row[2].replace(r"\|", "|").strip()
    target = row[3].replace(r"\|", "|").strip()
    visible_command = _strip_markdown_code(row[4]).replace(r"\|", "|")
    required_terms = row[5].replace(r"\|", "|").strip()
    evidence_prompt = row[6].replace(r"\|", "|").strip()
    recorder_command = _strip_markdown_code(row[7]).replace(r"\|", "|")
    expected_visible_command = hint.visible_command or "-"
    expected_terms = ", ".join(hint.required_terms) if hint.required_terms else "-"
    expected_values = (
        ("status", status, hint.status),
        ("area", area, hint.area),
        ("target", target, hint.target),
        ("visible command", visible_command, expected_visible_command),
        ("required terms", required_terms, expected_terms),
        ("evidence prompt", evidence_prompt, hint.evidence_prompt),
        ("recorder command", recorder_command, hint.recorder_command),
    )
    for field, actual, expected in expected_values:
        if _normalize_report_key(actual) != _normalize_report_key(expected):
            findings.append(f"recorder queue row {index} {field} is stale")


def _validate_route_batch_summary_row(
    findings: list[str],
    batch: AnimationPlaytestRouteBatch,
    row: tuple[str, ...],
) -> None:
    window_size = _strip_markdown_code(row[1])
    status = _strip_markdown_code(row[2])
    open_items = row[3].strip()
    visible_commands = row[4].strip()
    expected_values = (
        ("window", window_size, batch.window_size),
        ("status", status, batch.status),
        ("open items", open_items, str(batch.open_items)),
        ("visible commands", visible_commands, str(len(batch.items))),
    )
    for field, actual, expected in expected_values:
        if _normalize_report_key(actual) != _normalize_report_key(expected):
            findings.append(f"route batch {batch.batch_number} summary {field} is stale")


def _validate_route_batch_item_row(
    findings: list[str],
    item: AnimationPlaytestRouteBatchItem,
    row: tuple[str, ...],
) -> None:
    target = _strip_markdown_code(row[1])
    motion = _strip_markdown_code(row[2])
    status = _strip_markdown_code(row[3])
    visible_command = _strip_markdown_code(row[4]).replace(r"\|", "|")
    required_terms = row[5].replace(r"\|", "|").strip()
    recorder_command = _strip_markdown_code(row[6]).replace(r"\|", "|")
    expected_terms = ", ".join(item.required_terms) if item.required_terms else "-"
    expected_recorder = item.recorder_command or "-"
    expected_values = (
        ("target", target, item.target),
        ("motion", motion, item.motion_mode),
        ("status", status, item.status),
        ("visible command", visible_command, item.visible_command),
        ("required terms", required_terms, expected_terms),
        ("recorder command", recorder_command, expected_recorder),
    )
    for field, actual, expected in expected_values:
        if _normalize_report_key(actual) != _normalize_report_key(expected):
            findings.append(f"route batch row {item.step} {field} is stale")


def _validate_route_batch_window_hint(
    findings: list[str],
    hint: AnimationPlaytestRecorderHint,
    text: str,
) -> None:
    required_terms = ", ".join(hint.required_terms) if hint.required_terms else "-"
    expected_snippets = (
        f"- Status: `{hint.status}`",
        f"- Required terms: `{_markdown_table_cell(required_terms)}`",
        f"- Evidence prompt: {_markdown_table_cell(hint.evidence_prompt)}",
        f"`{_markdown_table_cell(hint.recorder_command)}`",
    )
    for snippet in expected_snippets:
        if snippet not in text:
            findings.append(f"route batch window recorder {hint.target} is stale")
            return


def _build_next_route_recorder_hint(
    plan: AnimationPlaytestReadinessPlan,
    *,
    report_path: Path,
    command_prefix: str,
) -> AnimationPlaytestRecorderHint | None:
    route_index = _first_route_finding_index(plan.report.findings)
    if route_index is None or not 1 <= route_index <= len(plan.visible_route):
        return None
    return _build_route_recorder_hint(
        plan,
        route_index=route_index,
        report_path=report_path,
        command_prefix=command_prefix,
    )


def _build_route_recorder_hint(
    plan: AnimationPlaytestReadinessPlan,
    *,
    route_index: int,
    report_path: Path,
    command_prefix: str,
) -> AnimationPlaytestRecorderHint:
    route_item = plan.visible_route[route_index - 1]
    required_terms = (
        MENU_ROUTE_EVIDENCE_TERMS if route_item.target == "menu" else PLAY_ROUTE_EVIDENCE_TERMS
    )
    evidence_prompt = (
        f"Run the visible command first, then replace the notes placeholder with observed "
        f"{route_item.target} evidence mentioning: {', '.join(required_terms)}."
    )
    return AnimationPlaytestRecorderHint(
        status="manual-required",
        area="Visible Route Evidence",
        target=str(route_index),
        recorder_command=(
            f"{command_prefix} record-animation-playtest-route "
            f"{_shell_arg(report_path)} {route_index} --result pass "
            "--notes '<replace with observed visible-window notes>'"
        ),
        evidence_prompt=evidence_prompt,
        required_terms=required_terms,
        visible_command=route_item.command,
    )


def _build_next_window_recorder_hint(
    findings: tuple[str, ...],
    *,
    report_path: Path,
    command_prefix: str,
) -> AnimationPlaytestRecorderHint | None:
    window_size = _first_window_finding_label(findings)
    if window_size is None:
        return None
    return _build_window_recorder_hint(
        window_size,
        report_path=report_path,
        command_prefix=command_prefix,
    )


def _build_window_recorder_hint(
    window_size: str,
    *,
    report_path: Path,
    command_prefix: str,
) -> AnimationPlaytestRecorderHint:
    return AnimationPlaytestRecorderHint(
        status="manual-required",
        area="Window Matrix",
        target=window_size,
        recorder_command=(
            f"{command_prefix} record-animation-playtest-window "
            f"{_shell_arg(report_path)} {_shell_arg(window_size)} "
            "--full pass --reduced pass --off pass "
            "--notes '<replace with observed window-matrix notes>'"
        ),
        evidence_prompt=(
            "Replace the notes placeholder after testing this window across full, reduced, "
            f"and off modes. Required terms: {', '.join(WINDOW_MATRIX_EVIDENCE_TERMS)}."
        ),
        required_terms=WINDOW_MATRIX_EVIDENCE_TERMS,
    )


def _build_next_labeled_recorder_hint(
    findings: tuple[str, ...],
    *,
    report_path: Path,
    command_prefix: str,
    marker: str,
    section: str,
    command_name: str,
    option_name: str,
    labels: tuple[str, ...],
    evidence_terms: dict[str, tuple[str, ...]],
    evidence_prompt_prefix: str,
) -> AnimationPlaytestRecorderHint | None:
    label = _first_labeled_finding(findings, labels=labels, marker=marker)
    if label is None:
        return None
    return _build_labeled_recorder_hint(
        label,
        report_path=report_path,
        command_prefix=command_prefix,
        section=section,
        command_name=command_name,
        option_name=option_name,
        evidence_terms=evidence_terms,
        evidence_prompt_prefix=evidence_prompt_prefix,
    )


def _build_labeled_recorder_hint(
    label: str,
    *,
    report_path: Path,
    command_prefix: str,
    section: str,
    command_name: str,
    option_name: str,
    evidence_terms: dict[str, tuple[str, ...]],
    evidence_prompt_prefix: str,
) -> AnimationPlaytestRecorderHint:
    required_terms = evidence_terms[label]
    return AnimationPlaytestRecorderHint(
        status="manual-required",
        area=section,
        target=label,
        recorder_command=(
            f"{command_prefix} {command_name} {_shell_arg(report_path)} {_shell_arg(label)} "
            "--result pass "
            f"{option_name} '<replace with observed evidence notes>' --follow-up none"
        ),
        evidence_prompt=(f"{evidence_prompt_prefix} Required terms: {', '.join(required_terms)}."),
        required_terms=required_terms,
    )


def _build_next_scene_recorder_hint(
    findings: tuple[str, ...],
    *,
    report_path: Path,
    command_prefix: str,
) -> AnimationPlaytestRecorderHint | None:
    label = _first_labeled_finding(
        findings,
        labels=tuple(label for label, _ in DEFAULT_OPEN_WINDOW_PLAYTEST_SCENE_CHECKS),
        marker="scene check",
    )
    if label is None:
        return None
    return _build_scene_recorder_hint(
        label,
        report_path=report_path,
        command_prefix=command_prefix,
    )


def _build_scene_recorder_hint(
    label: str,
    *,
    report_path: Path,
    command_prefix: str,
) -> AnimationPlaytestRecorderHint:
    readability_terms = SCENE_READABILITY_EVIDENCE_TERMS[label]
    motion_terms = SCENE_MOTION_EVIDENCE_TERMS[label]
    return AnimationPlaytestRecorderHint(
        status="manual-required",
        area="Scene Results",
        target=label,
        recorder_command=(
            f"{command_prefix} record-animation-playtest-scene "
            f"{_shell_arg(report_path)} {_shell_arg(label)} --result pass "
            "--readability-notes '<replace with observed readability notes>' "
            "--motion-notes '<replace with observed motion notes>' --follow-up none"
        ),
        evidence_prompt=(
            "Replace both placeholders after viewing the scene. "
            f"Readability terms: {', '.join(readability_terms)}. "
            f"Motion terms: {', '.join(motion_terms)}."
        ),
        required_terms=(*readability_terms, *motion_terms),
    )


def _build_next_field_recorder_hint(
    findings: tuple[str, ...],
    *,
    report_path: Path,
    command_prefix: str,
) -> AnimationPlaytestRecorderHint | None:
    field_name = _first_field_finding_label(findings)
    if field_name is None:
        return None
    return _build_field_recorder_hint(
        field_name,
        report_path=report_path,
        command_prefix=command_prefix,
    )


def _build_field_recorder_hint(
    field_name: str,
    *,
    report_path: Path,
    command_prefix: str,
) -> AnimationPlaytestRecorderHint:
    return AnimationPlaytestRecorderHint(
        status="manual-required",
        area="Report Field",
        target=field_name,
        recorder_command=(
            f"{command_prefix} record-animation-playtest-field "
            f"{_shell_arg(report_path)} {_shell_arg(field_name)} "
            "--value '<replace with final signoff value>'"
        ),
        evidence_prompt=(
            "Replace the value placeholder with a real build, blocker, validator, or "
            "decision value from the completed manual pass."
        ),
    )


def _first_route_finding_index(findings: tuple[str, ...]) -> int | None:
    indexes = _route_finding_indexes(findings)
    return indexes[0] if indexes else None


def _route_finding_indexes(findings: tuple[str, ...]) -> tuple[int, ...]:
    route_patterns = (
        r"visible route evidence row (\d+)",
        r"visible route evidence result: (\d+)",
        r"visible route evidence note: (\d+)",
        r"missing visible route evidence row: (\d+)",
        r"incomplete visible route evidence result: (\d+)",
        r"visible test route row (\d+)",
        r"missing visible test route row: (\d+)",
    )
    indexes: list[int] = []
    seen: set[int] = set()
    for finding in findings:
        normalized = finding.lower()
        for pattern in route_patterns:
            match = re.search(pattern, normalized)
            if match is None:
                continue
            index = int(match.group(1))
            if index not in seen:
                indexes.append(index)
                seen.add(index)
            break
    return tuple(sorted(indexes))


def _first_window_finding_label(findings: tuple[str, ...]) -> str | None:
    labels = _window_finding_labels(findings)
    return labels[0] if labels else None


def _window_finding_labels(findings: tuple[str, ...]) -> tuple[str, ...]:
    labels: list[str] = []
    seen: set[str] = set()
    for finding in findings:
        if "window matrix" not in finding.lower():
            continue
        match = re.search(r"\b(\d+x\d+)\b", finding.lower())
        if match is None:
            continue
        label = match.group(1)
        if label in seen:
            continue
        labels.append(label)
        seen.add(label)
    return tuple(labels)


def _first_labeled_finding(
    findings: tuple[str, ...],
    *,
    labels: tuple[str, ...],
    marker: str,
) -> str | None:
    labels_found = _labeled_finding_labels(findings, labels=labels, marker=marker)
    return labels_found[0] if labels_found else None


def _labeled_finding_labels(
    findings: tuple[str, ...],
    *,
    labels: tuple[str, ...],
    marker: str,
) -> tuple[str, ...]:
    normalized_marker = marker.lower()
    labels_found: list[str] = []
    seen: set[str] = set()
    for finding in findings:
        if normalized_marker not in finding.lower():
            continue
        normalized_finding = _normalize_report_key(finding)
        for label in labels:
            if _normalize_report_key(label) in normalized_finding:
                if label not in seen:
                    labels_found.append(label)
                    seen.add(label)
                break
    return tuple(labels_found)


def _first_field_finding_label(findings: tuple[str, ...]) -> str | None:
    labels = _field_finding_labels(findings)
    return labels[0] if labels else None


def _field_finding_labels(findings: tuple[str, ...]) -> tuple[str, ...]:
    allowed_fields = (
        *REQUIRED_ANIMATION_PLAYTEST_BUILD_FIELDS,
        "Release decision",
        *REQUIRED_ANIMATION_PLAYTEST_BLOCKER_FIELDS,
        *REQUIRED_ANIMATION_PLAYTEST_DECISION_FIELDS,
    )
    labels: list[str] = []
    seen: set[str] = set()
    for finding in findings:
        normalized = finding.lower()
        field_name = ""
        if normalized.startswith("missing field: "):
            field_name = finding.split(":", maxsplit=1)[1].strip()
        elif "release decision" in normalized:
            field_name = "Release decision"
        elif normalized.startswith("blocker field is not clear: "):
            field_name = finding.split(":", maxsplit=1)[1].strip()
        elif "required fixes before presenting" in normalized:
            field_name = "Required fixes before presenting"
        elif "validator result" in normalized:
            field_name = "Validator result"

        if not field_name:
            continue
        label = _normalize_allowed_manual_label(field_name, allowed_fields, "Report field")
        if label in seen:
            continue
        labels.append(label)
        seen.add(label)
    return tuple(labels)


def _shell_arg(value: str | Path) -> str:
    return shlex.quote(str(value))


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

    lines.extend(
        [
            "",
            "## Manual Evidence Checklist",
            "",
            "| Area | Required Evidence |",
            "| --- | --- |",
        ]
    )
    for area, required_evidence in _MANUAL_ANIMATION_EVIDENCE_CHECKLIST:
        lines.append(
            f"| {_markdown_table_cell(area)} | {_markdown_table_cell(required_evidence)} |"
        )

    lines.extend(
        [
            "",
            "## Manual Runbook",
            "",
            "| Step | Action | Exit Criteria |",
            "| --- | --- | --- |",
        ]
    )
    for step, action, exit_criteria in _MANUAL_ANIMATION_RUNBOOK_STEPS:
        lines.append(
            "| "
            f"{_markdown_table_cell(step)} | "
            f"{_markdown_table_cell(action)} | "
            f"{_markdown_table_cell(exit_criteria)} |"
        )

    lines.extend(
        [
            "",
            "## Visible Test Route",
            "",
            "| Step | Target | Window | Motion | Evidence To Record | Command |",
            "| ---: | --- | --- | --- | --- | --- |",
        ]
    )
    for index, item in enumerate(plan.visible_route, start=1):
        lines.append(
            "| "
            f"{index} | "
            f"`{item.target}` | "
            f"`{item.window_size}` | "
            f"`{item.motion_mode}` | "
            f"{_markdown_table_cell(_animation_playtest_route_evidence(item))} | "
            f"`{_markdown_table_cell(item.command)}` |"
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


def write_2d_animation_playtest_handoff(
    handoff: AnimationPlaytestHandoff,
    output_path: Path,
) -> None:
    """Write a concise manual animation handoff sheet."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    next_step = handoff.plan.steps[0]
    hint = handoff.recorder_hint
    required_terms = ", ".join(hint.required_terms) if hint.required_terms else "-"
    visible_command = hint.visible_command or "-"
    manual_result = "not completed by automation" if handoff.status != "pass" else "complete"
    lines = [
        "# NEXUS TECH 2D Animation Manual Handoff",
        "",
        f"- Artifact status: `{handoff.session.artifact_status}`",
        f"- Handoff status: `{handoff.status}`",
        f"- Manual result: `{manual_result}`",
        f"- Report: `{handoff.session.report.path}`",
        f"- Commands: `{handoff.session.commands.path}`",
        f"- Plan: `{handoff.session.plan.path}`",
        f"- Recorder queue: `{handoff.session.recorder_queue.path}`",
        *(
            ()
            if handoff.session.route_batches is None
            else (f"- Route batches: `{handoff.session.route_batches.path}`",)
        ),
        f"- Report open items: `{len(handoff.session.report.findings)}`",
        f"- Recorder queue rows: `{handoff.session.recorder_queue.expected_count}`",
        "- Completion gate: `validate-animation-playtest-report must pass before signoff`",
        "",
        "## Current Status",
        "",
        "| Artifact | Status |",
        "| --- | --- |",
        f"| Command queue | `{handoff.session.commands.status}` |",
        f"| Plan artifact | `{handoff.session.plan.status}` |",
        f"| Recorder queue | `{handoff.session.recorder_queue.status}` |",
        *(
            ()
            if handoff.session.route_batches is None
            else (f"| Route batches | `{handoff.session.route_batches.status}` |",)
        ),
        f"| Final report | `{handoff.session.report.status}` |",
        "",
        "## Next Manual Step",
        "",
        "| Area | Status | Open Items | Next Step |",
        "| --- | --- | ---: | --- |",
        (
            "| "
            f"{_markdown_table_cell(next_step.area)} | "
            f"`{next_step.status}` | "
            f"`{next_step.open_items}` | "
            f"{_markdown_table_cell(next_step.next_step)} |"
        ),
        "",
        "## Next Visible Command",
        "",
        f"`{_markdown_table_cell(visible_command)}`",
        "",
        "## Next Recorder Command",
        "",
        f"- Area: `{hint.area}`",
        f"- Target: `{hint.target}`",
        f"- Required terms: `{_markdown_table_cell(required_terms)}`",
        f"- Evidence prompt: {_markdown_table_cell(hint.evidence_prompt)}",
        "",
        f"`{_markdown_table_cell(hint.recorder_command)}`",
        "",
        "## Open Areas",
        "",
        "| Area | Status | Open Items | Next Step |",
        "| --- | --- | ---: | --- |",
    ]
    for step in handoff.plan.steps:
        lines.append(
            "| "
            f"{_markdown_table_cell(step.area)} | "
            f"`{step.status}` | "
            f"`{step.open_items}` | "
            f"{_markdown_table_cell(step.next_step)} |"
        )

    if handoff.session.findings:
        lines.extend(
            [
                "",
                "## Artifact Findings",
                "",
                "| Finding |",
                "| --- |",
            ]
        )
        for finding in handoff.session.findings:
            lines.append(f"| {_markdown_table_cell(finding)} |")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_2d_animation_playtest_route_batch_plan(
    batch_plan: AnimationPlaytestRouteBatchPlan,
    output_path: Path,
) -> None:
    """Write visible-window manual QA batches as a Markdown artifact."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    manual_result = "complete" if batch_plan.status == "pass" else "not completed by automation"
    lines = [
        "# NEXUS TECH 2D Animation Visible Route Batches",
        "",
        f"- Status: `{batch_plan.status}`",
        f"- Manual result: `{manual_result}`",
        f"- Command queue: `{batch_plan.commands.status}`",
        f"- Final report: `{batch_plan.report.status}`",
        f"- Report open items: `{len(batch_plan.report.findings)}`",
        f"- Route/window open items: `{batch_plan.route_open_items}`",
        "- Completion gate: `validate-animation-playtest-report must pass before signoff`",
        "",
        "## Batch Summary",
        "",
        "| Batch | Window | Status | Open Items | Visible Commands |",
        "| ---: | --- | --- | ---: | ---: |",
    ]
    for batch in batch_plan.batches:
        lines.append(
            "| "
            f"{batch.batch_number} | "
            f"`{batch.window_size}` | "
            f"`{batch.status}` | "
            f"{batch.open_items} | "
            f"{len(batch.items)} |"
        )

    for batch in batch_plan.batches:
        lines.extend(
            [
                "",
                f"## Batch {batch.batch_number}: {batch.window_size}",
                "",
                (
                    "| Step | Target | Motion | Status | Visible Command | "
                    "Required Terms | Recorder Command |"
                ),
                "| ---: | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for item in batch.items:
            required_terms = ", ".join(item.required_terms) if item.required_terms else "-"
            recorder_command = item.recorder_command or "-"
            lines.append(
                "| "
                f"{item.step} | "
                f"`{item.target}` | "
                f"`{item.motion_mode}` | "
                f"`{item.status}` | "
                f"`{_markdown_table_cell(item.visible_command)}` | "
                f"{_markdown_table_cell(required_terms)} | "
                f"`{_markdown_table_cell(recorder_command)}` |"
            )
        lines.extend(
            [
                "",
                f"### Batch {batch.batch_number} Preflight Checks",
                "",
                "| Check | Required Action |",
                "| --- | --- |",
            ]
        )
        for row in animation_playtest_route_batch_preflight_rows(batch):
            lines.append(_format_route_batch_preflight_row(row))
        lines.extend(
            [
                "",
                f"### Batch {batch.batch_number} Evidence Checklist",
                "",
                "| Item | Status | Required Evidence | Result Decision | Recorder Timing |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for row in animation_playtest_route_batch_evidence_checklist_rows(batch):
            lines.append(_format_route_batch_evidence_checklist_row(row))
        lines.extend(
            [
                "",
                f"### Batch {batch.batch_number} Result Decision Guide",
                "",
                "| Result | Use When | Recorder Edit | Release Rule |",
                "| --- | --- | --- | --- |",
            ]
        )
        for row in animation_playtest_route_batch_result_decision_rows():
            lines.append(_format_route_batch_result_decision_row(row))
        lines.extend(
            [
                "",
                f"### Batch {batch.batch_number} Defect Trigger Checklist",
                "",
                "| Trigger | Record Watch When | Record Fail When | Required Action |",
                "| --- | --- | --- | --- |",
            ]
        )
        for row in animation_playtest_route_batch_defect_trigger_rows():
            lines.append(_format_route_batch_defect_trigger_row(row))
        lines.extend(
            [
                "",
                f"### Batch {batch.batch_number} Defect Intake Template",
                "",
                "| Field | Required Detail |",
                "| --- | --- |",
            ]
        )
        for row in animation_playtest_route_batch_defect_intake_rows(batch):
            lines.append(_format_route_batch_defect_intake_row(row))
        lines.extend(
            [
                "",
                f"### Batch {batch.batch_number} Copy Commands",
                "",
                "```bash",
                *animation_playtest_route_batch_copy_commands(batch),
                "```",
            ]
        )
        lines.extend(
            [
                "",
                f"### Batch {batch.batch_number} Operator Steps",
                "",
                "```bash",
                *animation_playtest_route_batch_operator_steps(batch),
                "```",
            ]
        )
        if batch.window_recorder_hint is not None:
            hint = batch.window_recorder_hint
            required_terms = ", ".join(hint.required_terms) if hint.required_terms else "-"
            lines.extend(
                [
                    "",
                    "### Window Summary Recorder",
                    "",
                    f"- Status: `{hint.status}`",
                    f"- Required terms: `{_markdown_table_cell(required_terms)}`",
                    f"- Evidence prompt: {_markdown_table_cell(hint.evidence_prompt)}",
                    "",
                    f"`{_markdown_table_cell(hint.recorder_command)}`",
                ]
            )
        lines.extend(
            [
                "",
                f"### Batch {batch.batch_number} Closure Checklist",
                "",
                "| Check | Required Action |",
                "| --- | --- |",
            ]
        )
        for row in animation_playtest_route_batch_closure_rows(batch):
            lines.append(_format_route_batch_closure_row(row))
        lines.extend(
            [
                "",
                f"### Batch {batch.batch_number} Post-Recording Commands",
                "",
                "```bash",
                *animation_playtest_route_batch_post_recording_commands(
                    batch_plan,
                    output_path,
                ),
                "```",
            ]
        )

    if batch_plan.commands.findings:
        lines.extend(
            [
                "",
                "## Command Queue Findings",
                "",
                "| Finding |",
                "| --- |",
            ]
        )
        for finding in batch_plan.commands.findings:
            lines.append(f"| {_markdown_table_cell(finding)} |")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_2d_animation_playtest_route_batch_plan(
    batch_path: Path,
    report_path: Path,
    command_path: Path,
    *,
    scenario_id: str = "founder_journey",
    seed: int = 7,
    windows: tuple[tuple[int, int], ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_OPEN_WINDOW_PLAYTEST_MOTION_MODES,
    command_prefix: str = "uv run nexus-tech",
) -> AnimationPlaytestRouteBatchPlanValidation:
    """Validate that a route-batch artifact matches the current manual QA gaps."""

    text = batch_path.read_text(encoding="utf-8")
    batch_plan = build_2d_animation_playtest_route_batch_plan(
        report_path,
        command_path,
        scenario_id=scenario_id,
        seed=seed,
        windows=windows,
        motion_modes=motion_modes,
        command_prefix=command_prefix,
    )
    findings: list[str] = []
    manual_result = "complete" if batch_plan.status == "pass" else "not completed by automation"
    required_lines = (
        "# NEXUS TECH 2D Animation Visible Route Batches",
        f"- Status: `{batch_plan.status}`",
        f"- Manual result: `{manual_result}`",
        f"- Command queue: `{batch_plan.commands.status}`",
        f"- Final report: `{batch_plan.report.status}`",
        f"- Report open items: `{len(batch_plan.report.findings)}`",
        f"- Route/window open items: `{batch_plan.route_open_items}`",
        "- Completion gate: `validate-animation-playtest-report must pass before signoff`",
    )
    for line in required_lines:
        if line not in text:
            findings.append(f"missing route batch guard: {line}")

    rows = _extract_markdown_table_rows(text)
    summary_rows = tuple(row for row in rows if len(row) == 5 and row[0].isdigit())
    if len(summary_rows) != len(batch_plan.batches):
        findings.append(f"expected {len(batch_plan.batches)} batch summary rows")

    summary_by_batch: dict[int, tuple[str, ...]] = {}
    for row in summary_rows:
        batch_number = int(row[0])
        if batch_number in summary_by_batch:
            findings.append(f"duplicate route batch summary row: {batch_number}")
            continue
        summary_by_batch[batch_number] = row

    for batch in batch_plan.batches:
        row = summary_by_batch.get(batch.batch_number)
        if row is None:
            findings.append(f"missing route batch summary row: {batch.batch_number}")
            continue
        _validate_route_batch_summary_row(findings, batch, row)

    route_rows = tuple(
        row
        for row in rows
        if len(row) >= 7 and row[0].isdigit() and _strip_markdown_code(row[1]) in {"menu", "play"}
    )
    expected_items = tuple(item for batch in batch_plan.batches for item in batch.items)
    if len(route_rows) != len(expected_items):
        findings.append(f"expected {len(expected_items)} route batch rows, found {len(route_rows)}")

    route_rows_by_step: dict[int, tuple[str, ...]] = {}
    for row in route_rows:
        step = int(row[0])
        if step in route_rows_by_step:
            findings.append(f"duplicate route batch step: {step}")
            continue
        route_rows_by_step[step] = row

    for item in expected_items:
        row = route_rows_by_step.get(item.step)
        if row is None:
            findings.append(f"missing route batch row: {item.step}")
            continue
        _validate_route_batch_item_row(findings, item, row)

    for batch in batch_plan.batches:
        preflight_lines = (
            f"### Batch {batch.batch_number} Preflight Checks",
            "| Check | Required Action |",
            *(
                _format_route_batch_preflight_row(row)
                for row in animation_playtest_route_batch_preflight_rows(batch)
            ),
        )
        for line in preflight_lines:
            if line not in text:
                findings.append(f"missing route batch preflight guard: {line}")
        evidence_checklist_lines = (
            f"### Batch {batch.batch_number} Evidence Checklist",
            "| Item | Status | Required Evidence | Result Decision | Recorder Timing |",
            *(
                _format_route_batch_evidence_checklist_row(row)
                for row in animation_playtest_route_batch_evidence_checklist_rows(batch)
            ),
        )
        for line in evidence_checklist_lines:
            if line not in text:
                findings.append(f"missing route batch evidence checklist guard: {line}")
        result_decision_lines = (
            f"### Batch {batch.batch_number} Result Decision Guide",
            "| Result | Use When | Recorder Edit | Release Rule |",
            *(
                _format_route_batch_result_decision_row(row)
                for row in animation_playtest_route_batch_result_decision_rows()
            ),
        )
        for line in result_decision_lines:
            if line not in text:
                findings.append(f"missing route batch result decision guard: {line}")
        defect_trigger_lines = (
            f"### Batch {batch.batch_number} Defect Trigger Checklist",
            "| Trigger | Record Watch When | Record Fail When | Required Action |",
            *(
                _format_route_batch_defect_trigger_row(row)
                for row in animation_playtest_route_batch_defect_trigger_rows()
            ),
        )
        for line in defect_trigger_lines:
            if line not in text:
                findings.append(f"missing route batch defect trigger guard: {line}")
        defect_intake_lines = (
            f"### Batch {batch.batch_number} Defect Intake Template",
            "| Field | Required Detail |",
            *(
                _format_route_batch_defect_intake_row(row)
                for row in animation_playtest_route_batch_defect_intake_rows(batch)
            ),
        )
        for line in defect_intake_lines:
            if line not in text:
                findings.append(f"missing route batch defect intake guard: {line}")
        copy_block_lines = (
            f"### Batch {batch.batch_number} Copy Commands",
            *animation_playtest_route_batch_copy_commands(batch),
        )
        for line in copy_block_lines:
            if line not in text:
                findings.append(f"missing route batch copy command guard: {line}")
        operator_step_lines = (
            f"### Batch {batch.batch_number} Operator Steps",
            *animation_playtest_route_batch_operator_steps(batch),
        )
        for line in operator_step_lines:
            if line not in text:
                findings.append(f"missing route batch operator step guard: {line}")
        closure_lines = (
            f"### Batch {batch.batch_number} Closure Checklist",
            "| Check | Required Action |",
            *(
                _format_route_batch_closure_row(row)
                for row in animation_playtest_route_batch_closure_rows(batch)
            ),
        )
        for line in closure_lines:
            if line not in text:
                findings.append(f"missing route batch closure guard: {line}")
        post_recording_lines = (
            f"### Batch {batch.batch_number} Post-Recording Commands",
            *animation_playtest_route_batch_post_recording_commands(
                batch_plan,
                batch_path,
            ),
        )
        for line in post_recording_lines:
            if line not in text:
                findings.append(f"missing route batch post-recording guard: {line}")
        if batch.window_recorder_hint is not None:
            _validate_route_batch_window_hint(findings, batch.window_recorder_hint, text)

    return AnimationPlaytestRouteBatchPlanValidation(
        path=str(batch_path),
        expected_batches=len(batch_plan.batches),
        expected_route_rows=len(expected_items),
        findings=tuple(findings),
    )


def animation_playtest_route_batch_copy_commands(
    batch: AnimationPlaytestRouteBatch,
) -> tuple[str, ...]:
    """Return copy-paste commands for one visible-window route batch."""

    open_items = tuple(item for item in batch.items if item.status != "pass")
    has_open_window_summary = (
        batch.window_recorder_hint is not None and batch.window_recorder_hint.status != "pass"
    )
    if not open_items and not has_open_window_summary:
        return (f"# Batch {batch.batch_number}: {batch.window_size} already recorded.",)

    lines: list[str] = [f"# Batch {batch.batch_number}: {batch.window_size} visible commands"]
    for item in open_items:
        lines.append(item.visible_command)

    recorder_commands = tuple(item.recorder_command for item in open_items if item.recorder_command)
    if recorder_commands:
        lines.append(
            "# Replace recorder placeholders with observed notes after each visible command:"
        )
        lines.extend(recorder_commands)

    if has_open_window_summary and batch.window_recorder_hint is not None:
        lines.append(
            f"# Record the {batch.window_size} window summary after all motion modes are observed:"
        )
        lines.append(batch.window_recorder_hint.recorder_command)

    return tuple(lines)


def animation_playtest_route_batch_operator_steps(
    batch: AnimationPlaytestRouteBatch,
) -> tuple[str, ...]:
    """Return an ordered run-observe-record sequence for one route batch."""

    open_items = tuple(item for item in batch.items if item.status != "pass")
    has_open_window_summary = (
        batch.window_recorder_hint is not None and batch.window_recorder_hint.status != "pass"
    )
    if not open_items and not has_open_window_summary:
        return (f"# Batch {batch.batch_number}: {batch.window_size} already recorded.",)

    lines: list[str] = [
        f"# Batch {batch.batch_number}: {batch.window_size} operator sequence",
        "# Do not run recorder commands until the matching visible window has been observed.",
    ]
    for step_number, item in enumerate(open_items, start=1):
        required_terms = ", ".join(item.required_terms) if item.required_terms else "-"
        route_label = f"route {item.step} ({item.target}/{item.motion_mode})"
        lines.extend(
            [
                f"# Step {step_number}: observe {route_label}",
                item.visible_command,
                f"# Required evidence terms: {required_terms}",
                "# Replace recorder placeholders with real visible-window notes:",
            ]
        )
        if item.recorder_command:
            lines.append(item.recorder_command)
    if has_open_window_summary and batch.window_recorder_hint is not None:
        hint = batch.window_recorder_hint
        required_terms = ", ".join(hint.required_terms) if hint.required_terms else "-"
        lines.extend(
            [
                f"# Final step: record the {batch.window_size} window summary",
                f"# Required evidence terms: {required_terms}",
                "# Replace recorder placeholders with the observed full/reduced/off summary:",
                hint.recorder_command,
            ]
        )
    return tuple(lines)


def animation_playtest_route_batch_preflight_rows(
    batch: AnimationPlaytestRouteBatch,
) -> tuple[tuple[str, str], ...]:
    """Return preflight checks testers must confirm before a route batch."""

    open_items = tuple(item for item in batch.items if item.status != "pass")
    has_open_window_summary = (
        batch.window_recorder_hint is not None and batch.window_recorder_hint.status != "pass"
    )
    if not open_items and not has_open_window_summary:
        return (
            (
                "Batch state",
                f"{batch.window_size} already has recorded route and window evidence.",
            ),
        )

    pending_modes = tuple(dict.fromkeys(item.motion_mode for item in open_items))
    route_terms = tuple(dict.fromkeys(term for item in open_items for term in item.required_terms))
    window_terms = (
        batch.window_recorder_hint.required_terms
        if batch.window_recorder_hint is not None and has_open_window_summary
        else ()
    )
    required_route_terms = ", ".join(route_terms) if route_terms else "-"
    required_window_terms = ", ".join(window_terms) if window_terms else "-"
    pending_mode_text = ", ".join(pending_modes) if pending_modes else "-"
    return (
        (
            "Visible window",
            f"Open the {batch.window_size} command window exactly; do not resize mid-batch.",
        ),
        (
            "Pending routes",
            f"{len(open_items)} menu/play route row(s) still require observed evidence.",
        ),
        ("Motion modes", f"Observe this batch in these mode(s): {pending_mode_text}."),
        ("Route evidence terms", required_route_terms),
        ("Window summary terms", required_window_terms),
        (
            "Recorder safety",
            (
                "Run recorder commands only after visible observation and after replacing "
                "placeholder notes."
            ),
        ),
    )


def animation_playtest_route_batch_evidence_checklist_rows(
    batch: AnimationPlaytestRouteBatch,
) -> tuple[tuple[str, str, str, str, str], ...]:
    """Return observed-evidence checklist rows for one route batch."""

    rows: list[tuple[str, str, str, str, str]] = []
    for item in batch.items:
        required_terms = ", ".join(item.required_terms) if item.required_terms else "-"
        rows.append(
            (
                f"Route {item.step}: {item.target}/{item.motion_mode}",
                item.status,
                required_terms,
                "Choose pass, watch, or fail after observing the visible command.",
                "Run the route recorder only after replacing placeholder notes.",
            )
        )
    if batch.window_recorder_hint is not None:
        hint = batch.window_recorder_hint
        required_terms = ", ".join(hint.required_terms) if hint.required_terms else "-"
        rows.append(
            (
                f"Window summary: {batch.window_size}",
                hint.status,
                required_terms,
                "Summarize the full/reduced/off window result from observed behavior.",
                "Run the window recorder after all batch motion modes are checked.",
            )
        )
    return tuple(rows)


def animation_playtest_route_batch_result_decision_rows() -> tuple[tuple[str, str, str, str], ...]:
    """Return pass/watch/fail decision guidance for route-batch recorder commands."""

    return _ROUTE_BATCH_RESULT_DECISION_ROWS


def animation_playtest_route_batch_defect_trigger_rows() -> tuple[tuple[str, str, str, str], ...]:
    """Return defect trigger guidance for manual route-batch observations."""

    return _ROUTE_BATCH_DEFECT_TRIGGER_ROWS


def animation_playtest_route_batch_defect_intake_rows(
    batch: AnimationPlaytestRouteBatch,
) -> tuple[tuple[str, str], ...]:
    """Return defect intake fields for one manual route batch."""

    pending_items = tuple(item for item in batch.items if item.status != "pass")
    pending_labels = ", ".join(
        f"{item.step}:{item.target}/{item.motion_mode}" for item in pending_items
    )
    batch_context = (
        f"{batch.window_size}; pending routes: {pending_labels}"
        if pending_labels
        else f"{batch.window_size}; no pending route rows"
    )
    return (
        ("Batch context", batch_context),
        *_ROUTE_BATCH_DEFECT_INTAKE_ROWS,
    )


def animation_playtest_route_batch_closure_rows(
    batch: AnimationPlaytestRouteBatch,
) -> tuple[tuple[str, str], ...]:
    """Return closure checks before moving to the next route batch."""

    open_items = tuple(item for item in batch.items if item.status != "pass")
    has_open_window_summary = (
        batch.window_recorder_hint is not None and batch.window_recorder_hint.status != "pass"
    )
    if not open_items and not has_open_window_summary:
        return (
            (
                "Batch closed",
                f"{batch.window_size} route rows and window summary are already recorded.",
            ),
        )

    return (
        (
            "Route recorders",
            (
                f"Record observed notes for {len(open_items)} pending route row(s); "
                "switch result to watch/fail for any defect trigger."
            ),
        ),
        (
            "Window summary",
            (
                f"Record the {batch.window_size} full/reduced/off summary after every "
                "motion mode is observed."
            ),
        ),
        (
            "Defect intake",
            (
                "For any watch/fail, capture severity, reproduction, evidence, recorder "
                "action, and follow-up ownership."
            ),
        ),
        (
            "Artifact refresh",
            "Run the post-recording commands so route batches and report status update.",
        ),
        (
            "Validation gate",
            (
                "Run route-batch validation and animation-playtest-status; manual-required "
                "is expected until every batch and signoff field passes."
            ),
        ),
        (
            "Next batch gate",
            f"Move past {batch.window_size} only after this batch no longer has placeholder notes.",
        ),
    )


def animation_playtest_route_batch_post_recording_commands(
    batch_plan: AnimationPlaytestRouteBatchPlan,
    output_path: Path,
) -> tuple[str, ...]:
    """Return commands to refresh and validate route batches after manual recording."""

    context_args = (
        f" --scenario {_shell_arg(batch_plan.scenario_id)}"
        f" --seed {batch_plan.seed}"
        f" --command-prefix {_shell_arg(batch_plan.command_prefix)}"
    )
    return (
        "# After recording observed notes for this batch, refresh the route-batch artifact:",
        (
            f"{batch_plan.command_prefix} animation-playtest-route-batches "
            f"{_shell_arg(batch_plan.report.path)} {_shell_arg(batch_plan.commands.path)}"
            f"{context_args} --output {_shell_arg(output_path)}"
        ),
        "# Validate that the refreshed route-batch artifact still matches the report:",
        (
            f"{batch_plan.command_prefix} validate-animation-playtest-route-batches "
            f"{_shell_arg(output_path)} {_shell_arg(batch_plan.report.path)} "
            f"{_shell_arg(batch_plan.commands.path)}{context_args}"
        ),
        "# Check the report status; MANUAL-REQUIRED is expected until all batches/signoff pass:",
        (
            f"{batch_plan.command_prefix} animation-playtest-status "
            f"{_shell_arg(batch_plan.report.path)}"
        ),
    )


def _format_route_batch_preflight_row(row: tuple[str, str]) -> str:
    check, required_action = row
    return f"| {_markdown_table_cell(check)} | {_markdown_table_cell(required_action)} |"


def _format_route_batch_evidence_checklist_row(
    row: tuple[str, str, str, str, str],
) -> str:
    item, status, required_evidence, result_decision, recorder_timing = row
    return (
        "| "
        f"{_markdown_table_cell(item)} | "
        f"`{_markdown_table_cell(status)}` | "
        f"{_markdown_table_cell(required_evidence)} | "
        f"{_markdown_table_cell(result_decision)} | "
        f"{_markdown_table_cell(recorder_timing)} |"
    )


def _format_route_batch_result_decision_row(row: tuple[str, str, str, str]) -> str:
    result, use_when, recorder_edit, release_rule = row
    return (
        "| "
        f"`{_markdown_table_cell(result)}` | "
        f"{_markdown_table_cell(use_when)} | "
        f"{_markdown_table_cell(recorder_edit)} | "
        f"{_markdown_table_cell(release_rule)} |"
    )


def _format_route_batch_defect_trigger_row(row: tuple[str, str, str, str]) -> str:
    trigger, record_watch_when, record_fail_when, required_action = row
    return (
        "| "
        f"{_markdown_table_cell(trigger)} | "
        f"{_markdown_table_cell(record_watch_when)} | "
        f"{_markdown_table_cell(record_fail_when)} | "
        f"{_markdown_table_cell(required_action)} |"
    )


def _format_route_batch_defect_intake_row(row: tuple[str, str]) -> str:
    field, required_detail = row
    return f"| {_markdown_table_cell(field)} | {_markdown_table_cell(required_detail)} |"


def _format_route_batch_closure_row(row: tuple[str, str]) -> str:
    check, required_action = row
    return f"| {_markdown_table_cell(check)} | {_markdown_table_cell(required_action)} |"


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

    if "## Manual Evidence Checklist" not in text:
        findings.append("missing manual evidence checklist section")

    for area, required_evidence in _MANUAL_ANIMATION_EVIDENCE_CHECKLIST:
        row = _find_report_table_row(rows, area)
        if row is None:
            findings.append(f"missing manual evidence checklist row: {area}")
            continue
        if len(row) <= 1:
            findings.append(f"incomplete manual evidence checklist row: {area}")
            continue
        evidence = row[1].replace(r"\|", "|").strip()
        if _normalize_report_key(evidence) != _normalize_report_key(required_evidence):
            findings.append(f"manual evidence checklist row {area} is stale")

    if "## Manual Runbook" not in text:
        findings.append("missing manual runbook section")

    for step, action, exit_criteria in _MANUAL_ANIMATION_RUNBOOK_STEPS:
        row = _find_report_table_row(rows, step)
        if row is None:
            findings.append(f"missing manual runbook row: {step}")
            continue
        if len(row) <= 2:
            findings.append(f"incomplete manual runbook row: {step}")
            continue
        action_text = row[1].replace(r"\|", "|").strip()
        exit_text = row[2].replace(r"\|", "|").strip()
        if _normalize_report_key(action_text) != _normalize_report_key(action):
            findings.append(f"manual runbook row {step} action is stale")
        if _normalize_report_key(exit_text) != _normalize_report_key(exit_criteria):
            findings.append(f"manual runbook row {step} exit criteria is stale")

    if "## Visible Test Route" not in text:
        findings.append("missing visible test route section")

    route_rows = tuple(row for row in rows if len(row) >= 6 and row[0].isdigit())
    if len(route_rows) != len(plan.visible_route):
        findings.append(
            f"expected {len(plan.visible_route)} visible test route rows, found {len(route_rows)}"
        )
    route_by_step: dict[int, tuple[str, ...]] = {}
    for row in route_rows:
        step = int(row[0])
        if step in route_by_step:
            findings.append(f"duplicate visible test route step: {step}")
            continue
        route_by_step[step] = row

    for index, item in enumerate(plan.visible_route, start=1):
        row = route_by_step.get(index)
        if row is None:
            findings.append(f"missing visible test route row: {index}")
            continue
        target = _strip_markdown_code(row[1])
        window = _strip_markdown_code(row[2])
        motion = _strip_markdown_code(row[3])
        evidence = row[4].replace(r"\|", "|").strip()
        command = _strip_markdown_code(row[5]).replace(r"\|", "|")
        expected_evidence = _animation_playtest_route_evidence(item)
        if target != item.target:
            findings.append(
                f"visible test route row {index} target is {target}, expected {item.target}"
            )
        if window != item.window_size:
            findings.append(
                f"visible test route row {index} window is {window}, expected {item.window_size}"
            )
        if motion != item.motion_mode:
            findings.append(
                f"visible test route row {index} motion is {motion}, expected {item.motion_mode}"
            )
        if _normalize_report_key(evidence) != _normalize_report_key(expected_evidence):
            findings.append(f"visible test route row {index} evidence prompt is stale")
        if command != item.command:
            findings.append(f"visible test route row {index} command is stale")

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


def record_2d_animation_playtest_window_evidence(
    report_path: Path,
    *,
    window_size: str,
    full_result: str,
    reduced_result: str,
    off_result: str,
    notes: str,
) -> AnimationPlaytestReportRecord:
    """Record manual window-matrix evidence without touching unrelated signoff rows."""

    normalized_window = _normalize_manual_window_size(window_size)
    full = _normalize_manual_playtest_result(full_result)
    reduced = _normalize_manual_playtest_result(reduced_result)
    off = _normalize_manual_playtest_result(off_result)
    evidence = _normalize_manual_evidence_notes(
        notes,
        required_terms=WINDOW_MATRIX_EVIDENCE_TERMS,
    )
    text = report_path.read_text(encoding="utf-8")

    def replacement(row: tuple[str, ...]) -> str:
        if len(row) < 5:
            raise ValueError(f"Window matrix row {normalized_window} is incomplete.")
        return (
            f"| `{normalized_window}` | `{full}` | `{reduced}` | `{off}` | "
            f"{_markdown_table_cell(evidence)} |"
        )

    updated = _replace_report_table_row(
        text,
        section="Window Matrix",
        row_key=normalized_window,
        replacement=replacement,
    )
    report_path.write_text(updated, encoding="utf-8")
    return AnimationPlaytestReportRecord(
        path=str(report_path),
        section="Window Matrix",
        target=normalized_window,
        result=f"full={full}, reduced={reduced}, off={off}",
    )


def record_2d_animation_playtest_route_evidence(
    report_path: Path,
    *,
    step: int,
    result: str,
    notes: str,
) -> AnimationPlaytestReportRecord:
    """Record one visible-route manual observation row in the playtest report."""

    if step < 1:
        raise ValueError("Visible route step must be 1 or greater.")
    normalized_result = _normalize_manual_playtest_result(result)
    text = report_path.read_text(encoding="utf-8")

    def replacement(row: tuple[str, ...]) -> str:
        if len(row) < 6:
            raise ValueError(f"Visible route evidence row {step} is incomplete.")
        target = _strip_markdown_code(row[1])
        window = _strip_markdown_code(row[2])
        motion = _strip_markdown_code(row[3])
        evidence = _normalize_manual_evidence_notes(
            notes,
            required_terms=(
                MENU_ROUTE_EVIDENCE_TERMS if target == "menu" else PLAY_ROUTE_EVIDENCE_TERMS
            ),
        )
        return (
            f"| {step} | `{target}` | `{window}` | `{motion}` | "
            f"`{normalized_result}` | {_markdown_table_cell(evidence)} |"
        )

    updated = _replace_report_table_row(
        text,
        section="Visible Route Evidence",
        row_key=str(step),
        replacement=replacement,
    )
    report_path.write_text(updated, encoding="utf-8")
    return AnimationPlaytestReportRecord(
        path=str(report_path),
        section="Visible Route Evidence",
        target=str(step),
        result=normalized_result,
    )


def record_2d_animation_playtest_control_evidence(
    report_path: Path,
    *,
    area: str,
    result: str,
    notes: str,
    follow_up: str = "none",
) -> AnimationPlaytestReportRecord:
    """Record one manual control-clarity row in the playtest report."""

    normalized_area = _normalize_allowed_manual_label(
        area,
        tuple(label for label, _ in DEFAULT_OPEN_WINDOW_PLAYTEST_CONTROL_CHECKS),
        "Control area",
    )
    normalized_result = _normalize_manual_playtest_result(result)
    evidence = _normalize_manual_evidence_notes(
        notes,
        required_terms=CONTROL_EVIDENCE_TERMS[normalized_area],
    )
    normalized_follow_up = _normalize_manual_follow_up(follow_up)
    text = report_path.read_text(encoding="utf-8")

    def replacement(row: tuple[str, ...]) -> str:
        if len(row) < 4:
            raise ValueError(f"Control row {normalized_area} is incomplete.")
        return (
            f"| {normalized_area} | `{normalized_result}` | "
            f"{_markdown_table_cell(evidence)} | {_markdown_table_cell(normalized_follow_up)} |"
        )

    updated = _replace_report_table_row(
        text,
        section="Control Clarity Results",
        row_key=normalized_area,
        replacement=replacement,
    )
    report_path.write_text(updated, encoding="utf-8")
    return AnimationPlaytestReportRecord(
        path=str(report_path),
        section="Control Clarity Results",
        target=normalized_area,
        result=normalized_result,
    )


def record_2d_animation_playtest_scene_evidence(
    report_path: Path,
    *,
    scene: str,
    result: str,
    readability_notes: str,
    motion_notes: str,
    follow_up: str = "none",
) -> AnimationPlaytestReportRecord:
    """Record one manual scene-readability and motion row in the playtest report."""

    normalized_scene = _normalize_allowed_manual_label(
        scene,
        tuple(label for label, _ in DEFAULT_OPEN_WINDOW_PLAYTEST_SCENE_CHECKS),
        "Scene",
    )
    normalized_result = _normalize_manual_playtest_result(result)
    readability = _normalize_manual_evidence_notes(
        readability_notes,
        required_terms=SCENE_READABILITY_EVIDENCE_TERMS[normalized_scene],
    )
    motion = _normalize_manual_evidence_notes(
        motion_notes,
        required_terms=SCENE_MOTION_EVIDENCE_TERMS[normalized_scene],
    )
    normalized_follow_up = _normalize_manual_follow_up(follow_up)
    text = report_path.read_text(encoding="utf-8")

    def replacement(row: tuple[str, ...]) -> str:
        if len(row) < 5:
            raise ValueError(f"Scene row {normalized_scene} is incomplete.")
        return (
            f"| {normalized_scene} | `{normalized_result}` | "
            f"{_markdown_table_cell(readability)} | {_markdown_table_cell(motion)} | "
            f"{_markdown_table_cell(normalized_follow_up)} |"
        )

    updated = _replace_report_table_row(
        text,
        section="Scene Results",
        row_key=normalized_scene,
        replacement=replacement,
    )
    report_path.write_text(updated, encoding="utf-8")
    return AnimationPlaytestReportRecord(
        path=str(report_path),
        section="Scene Results",
        target=normalized_scene,
        result=normalized_result,
    )


def record_2d_animation_playtest_feedback_evidence(
    report_path: Path,
    *,
    area: str,
    result: str,
    notes: str,
    follow_up: str = "none",
) -> AnimationPlaytestReportRecord:
    """Record one manual game-feel feedback row in the playtest report."""

    normalized_area = _normalize_allowed_manual_label(
        area,
        tuple(label for label, _ in DEFAULT_OPEN_WINDOW_PLAYTEST_FEEDBACK_CHECKS),
        "Feedback area",
    )
    normalized_result = _normalize_manual_playtest_result(result)
    evidence = _normalize_manual_evidence_notes(
        notes,
        required_terms=FEEDBACK_EVIDENCE_TERMS[normalized_area],
    )
    normalized_follow_up = _normalize_manual_follow_up(follow_up)
    text = report_path.read_text(encoding="utf-8")

    def replacement(row: tuple[str, ...]) -> str:
        if len(row) < 4:
            raise ValueError(f"Game-feel row {normalized_area} is incomplete.")
        return (
            f"| {normalized_area} | `{normalized_result}` | "
            f"{_markdown_table_cell(evidence)} | {_markdown_table_cell(normalized_follow_up)} |"
        )

    updated = _replace_report_table_row(
        text,
        section="Game Feel Results",
        row_key=normalized_area,
        replacement=replacement,
    )
    report_path.write_text(updated, encoding="utf-8")
    return AnimationPlaytestReportRecord(
        path=str(report_path),
        section="Game Feel Results",
        target=normalized_area,
        result=normalized_result,
    )


def record_2d_animation_playtest_field(
    report_path: Path,
    *,
    field_name: str,
    value: str,
) -> AnimationPlaytestReportRecord:
    """Record one build, blocker, or decision field in the manual report."""

    normalized_field = _normalize_allowed_manual_label(
        field_name,
        (
            *REQUIRED_ANIMATION_PLAYTEST_BUILD_FIELDS,
            "Release decision",
            *REQUIRED_ANIMATION_PLAYTEST_BLOCKER_FIELDS,
            *REQUIRED_ANIMATION_PLAYTEST_DECISION_FIELDS,
        ),
        "Report field",
    )
    normalized_value = _normalize_manual_field_value(normalized_field, value)
    text = report_path.read_text(encoding="utf-8")
    updated = _replace_report_field(
        text,
        field_name=normalized_field,
        value=normalized_value,
    )
    report_path.write_text(updated, encoding="utf-8")
    return AnimationPlaytestReportRecord(
        path=str(report_path),
        section="Report Field",
        target=normalized_field,
        result=normalized_value,
    )


def _replace_report_table_row(
    text: str,
    *,
    section: str,
    row_key: str,
    replacement: Callable[[tuple[str, ...]], str],
) -> str:
    """Replace a Markdown table row inside one report section."""

    lines = text.splitlines()
    in_section = False
    target_key = _normalize_report_key(row_key)
    for index, line in enumerate(lines):
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading is not None:
            in_section = _normalize_report_key(heading.group(1)) == _normalize_report_key(section)
            continue
        if not in_section:
            continue
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = tuple(cell.strip() for cell in stripped.strip("|").split("|"))
        if not cells or _is_markdown_separator_row(cells):
            continue
        if _normalize_report_key(cells[0]) != target_key:
            continue
        lines[index] = replacement(cells)
        return "\n".join(lines) + ("\n" if text.endswith("\n") else "")

    raise ValueError(f"Could not find {section} row: {row_key}.")


def _replace_report_field(
    text: str,
    *,
    field_name: str,
    value: str,
) -> str:
    """Replace one report bullet field while preserving the report structure."""

    pattern = re.compile(rf"^\s*-\s*{re.escape(field_name)}:\s*.*$", re.IGNORECASE)
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if pattern.match(line) is None:
            continue
        lines[index] = f"- {field_name}: {value}"
        return "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    raise ValueError(f"Could not find report field: {field_name}.")


def _normalize_allowed_manual_label(
    value: str,
    allowed_values: tuple[str, ...],
    label: str,
) -> str:
    key = _normalize_report_key(value)
    for allowed_value in allowed_values:
        if _normalize_report_key(allowed_value) == key:
            return allowed_value
    allowed = ", ".join(allowed_values)
    raise ValueError(f"{label} must be one of: {allowed}.")


def _normalize_manual_window_size(window_size: str) -> str:
    normalized = window_size.strip().lower()
    expected = {f"{width}x{height}" for width, height in DEFAULT_OPEN_WINDOW_PLAYTEST_WINDOWS}
    if normalized not in expected:
        allowed = ", ".join(sorted(expected))
        raise ValueError(f"Window size must be one of: {allowed}.")
    return normalized


def _normalize_manual_playtest_result(result: str) -> str:
    normalized = _normalize_report_result(result)
    if normalized not in {"pass", "watch", "fail"}:
        raise ValueError("Result must be one of: pass, watch, fail.")
    return normalized


def _normalize_manual_evidence_notes(
    notes: str,
    *,
    required_terms: tuple[str, ...] = (),
) -> str:
    evidence = _markdown_table_cell(notes)
    if _is_missing_report_evidence(evidence) or len(evidence) < 24:
        raise ValueError(
            "Evidence notes must describe real observed details, not generic/template text."
        )
    missing_terms = _missing_evidence_terms(evidence, required_terms)
    if missing_terms:
        raise ValueError(f"Evidence notes missing required terms: {', '.join(missing_terms)}.")
    return evidence


def _normalize_manual_follow_up(follow_up: str) -> str:
    normalized = _markdown_table_cell(follow_up or "none")
    if _is_placeholder_field(normalized) and _normalize_report_result(normalized) != "none":
        raise ValueError("Follow-up must be a real note or `none`.")
    if "owner/date if not pass" in _normalize_report_key(normalized):
        raise ValueError("Follow-up must replace the template owner/date placeholder.")
    return normalized


def _normalize_manual_field_value(field_name: str, value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip())
    if field_name == "Release decision":
        return f"`{_normalize_manual_playtest_result(normalized)}`"
    if _is_placeholder_field(normalized):
        raise ValueError("Field value must not be blank, todo, or a template placeholder.")
    if "\n" in value:
        raise ValueError("Field value must fit on one line.")
    return normalized


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


def _animation_playtest_route_evidence(item: AnimationPlaytestCommand) -> str:
    """Return the human evidence prompt for one visible-window route step."""

    window_context = f"{item.window_size} {item.motion_mode}"
    if item.target == "menu":
        return (
            "Record title/menu, wizard, save-slot, archive, meta-board, hover, "
            f"and text-fit observations for {window_context}."
        )
    return (
        "Record dashboard, action picker, pending event, inspector, endgame, "
        f"summary, pause/back, and motion-feel observations for {window_context}."
    )


def _required_terms_prompt(terms: tuple[str, ...]) -> str:
    """Return a compact prompt for evidence terms the final validator expects."""

    return f"Pass notes must mention: {', '.join(terms)}."


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


def _extract_report_section_table_rows(text: str, section: str) -> tuple[tuple[str, ...], ...]:
    rows: list[tuple[str, ...]] = []
    in_section = False
    section_key = _normalize_report_key(section)
    for line in text.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading is not None:
            in_section = _normalize_report_key(heading.group(1)) == section_key
            continue
        if not in_section:
            continue
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
        row_results_pass = True
        for index, mode in enumerate(("Full", "Reduced", "Off"), start=1):
            if len(row) <= index or _is_placeholder_result(row[index]):
                findings.append(f"incomplete window matrix result: {label} {mode}")
                row_results_pass = False
                continue
            if not _is_passing_result(row[index]):
                result = _normalize_report_result(row[index]) or "blank"
                findings.append(f"window matrix {label} {mode} is {result}, not pass")
                row_results_pass = False
        if len(row) <= 4 or (row_results_pass and _is_missing_report_evidence(row[4])):
            findings.append(f"missing window matrix evidence: {label} notes")
        elif row_results_pass:
            missing_terms = _missing_evidence_terms(row[4], WINDOW_MATRIX_EVIDENCE_TERMS)
            if missing_terms:
                findings.append(
                    f"window matrix {label} evidence missing observed terms: "
                    f"{', '.join(missing_terms)}"
                )


def _validate_required_visible_route_evidence(
    findings: list[str],
    rows: tuple[tuple[str, ...], ...],
) -> None:
    expected_route = build_2d_animation_playtest_command_queue()
    route_rows = tuple(
        row
        for row in rows
        if len(row) >= 5 and row[0].isdigit() and _strip_markdown_code(row[1]) in {"menu", "play"}
    )
    if len(route_rows) != len(expected_route):
        findings.append(
            f"expected {len(expected_route)} visible route evidence rows, found {len(route_rows)}"
        )

    route_by_step: dict[int, tuple[str, ...]] = {}
    for row in route_rows:
        step = int(row[0])
        if step in route_by_step:
            findings.append(f"duplicate visible route evidence step: {step}")
            continue
        route_by_step[step] = row

    for index, item in enumerate(expected_route, start=1):
        row = route_by_step.get(index)
        if row is None:
            findings.append(f"missing visible route evidence row: {index}")
            continue
        target = _strip_markdown_code(row[1])
        window = _strip_markdown_code(row[2])
        motion = _strip_markdown_code(row[3])
        if target != item.target:
            findings.append(
                f"visible route evidence row {index} target is {target}, expected {item.target}"
            )
        if window != item.window_size:
            findings.append(
                f"visible route evidence row {index} window is {window}, "
                f"expected {item.window_size}"
            )
        if motion != item.motion_mode:
            findings.append(
                f"visible route evidence row {index} motion is {motion}, "
                f"expected {item.motion_mode}"
            )
        route_result_pass = False
        if len(row) <= 4 or _is_placeholder_result(row[4]):
            findings.append(f"incomplete visible route evidence result: {index}")
        elif not _is_passing_result(row[4]):
            result = _normalize_report_result(row[4]) or "blank"
            findings.append(f"visible route evidence row {index} is {result}, not pass")
        else:
            route_result_pass = True
        if route_result_pass and (len(row) <= 5 or _is_missing_report_evidence(row[5])):
            findings.append(f"missing visible route evidence note: {index}")
        elif route_result_pass:
            missing_terms = _missing_route_evidence_terms(item, row[5])
            if missing_terms:
                findings.append(
                    f"visible route evidence row {index} missing observed terms: "
                    f"{', '.join(missing_terms)}"
                )


def _validate_required_result_rows(
    findings: list[str],
    rows: tuple[tuple[str, ...], ...],
    labels: tuple[str, ...],
    category: str,
    *,
    evidence_columns: tuple[tuple[int, str], ...] = (),
    evidence_terms: dict[str | tuple[str, str], tuple[str, ...]] | None = None,
) -> None:
    evidence_terms = evidence_terms or {}
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
            if len(row) <= column_index or _is_missing_report_evidence(row[column_index]):
                findings.append(f"missing {category} evidence: {label} {evidence_name}")
                continue
            required_terms = evidence_terms.get((label, evidence_name)) or evidence_terms.get(label)
            if not required_terms:
                continue
            missing_terms = _missing_evidence_terms(row[column_index], required_terms)
            if missing_terms:
                findings.append(
                    f"{category} evidence {label} {evidence_name} "
                    f"missing observed terms: {', '.join(missing_terms)}"
                )


def _missing_route_evidence_terms(
    item: AnimationPlaytestCommand,
    evidence: str,
) -> tuple[str, ...]:
    required_terms = (
        MENU_ROUTE_EVIDENCE_TERMS if item.target == "menu" else PLAY_ROUTE_EVIDENCE_TERMS
    )
    return _missing_evidence_terms(evidence, required_terms)


def _missing_evidence_terms(
    evidence: str,
    required_terms: tuple[str, ...],
) -> tuple[str, ...]:
    tokens = set(re.findall(r"[a-z0-9]+", _normalize_report_result(evidence)))
    return tuple(term for term in required_terms if term not in tokens)


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
    return re.sub(r"\s+", " ", value.strip().strip("` ").replace("`", "")).lower()


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


def _is_clear_signoff_value(value: str) -> bool:
    normalized = _normalize_report_result(value)
    return (
        normalized in {"none", "no", "no issues", "no blockers", "no required fixes", "clear"}
        or normalized.startswith("none ")
        or normalized.startswith("no ")
        or normalized.endswith(" none")
        or normalized.endswith(" clear")
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


def _is_missing_report_evidence(value: str) -> bool:
    return _is_thin_evidence(value) or _is_template_evidence_prompt(value)


def _is_template_evidence_prompt(value: str) -> bool:
    normalized = _normalize_report_key(value)
    return any(prompt in normalized for prompt in _TEMPLATE_EVIDENCE_PROMPT_KEYS)


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
        "- Evidence prompts: `required in every command row`",
        "",
        "| Step | Target | Window | Motion | Command | Evidence To Record |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for index, item in enumerate(queue, start=1):
        lines.append(
            f"| {index} | `{item.target}` | `{item.window_size}` | "
            f"`{item.motion_mode}` | `{item.command}` | "
            f"{_markdown_table_cell(_animation_playtest_route_evidence(item))} |"
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
    if "- Evidence prompts: `required in every command row`" not in text:
        findings.append("evidence prompt guard is missing")

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
    expected_by_step = dict(enumerate(expected_queue, start=1))

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

    seen_steps: set[int] = set()
    for row in command_rows:
        step = int(row[0])
        if step in seen_steps:
            findings.append(f"duplicate command queue step: {step}")
            continue
        seen_steps.add(step)

        expected_item = expected_by_step.get(step)
        if expected_item is None:
            findings.append(f"unexpected command queue step: {step}")
            continue

        target = _strip_markdown_code(row[1])
        window = _strip_markdown_code(row[2])
        motion = _strip_markdown_code(row[3])
        command = _strip_markdown_code(row[4])
        if target != expected_item.target:
            findings.append(
                f"command queue step {step} target is {target}, expected {expected_item.target}"
            )
        if window != expected_item.window_size:
            findings.append(
                f"command queue step {step} window is {window}, "
                f"expected {expected_item.window_size}"
            )
        if motion != expected_item.motion_mode:
            findings.append(
                f"command queue step {step} motion is {motion}, "
                f"expected {expected_item.motion_mode}"
            )
        if command != expected_item.command:
            findings.append(f"command queue step {step} command is stale")
        if len(row) <= 5 or _is_thin_evidence(row[5]):
            findings.append(f"missing command evidence prompt: step {step}")
            continue
        evidence = row[5].replace(r"\|", "|").strip()
        expected_evidence = _animation_playtest_route_evidence(expected_item)
        if _normalize_report_key(evidence) != _normalize_report_key(expected_evidence):
            findings.append(f"command evidence prompt is stale: step {step}")

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
            "--viewport 820x620 --viewport 960x640 --viewport 1440x900 "
            "--output-dir /tmp/nexus-tech-visual-audit/full"
        ),
        (
            "uv run nexus-tech audit-2d-visual --scenario founder_journey --seed 7 "
            "--motion-mode off --viewport 820x620 --viewport 960x640 "
            "--viewport 1440x900 --output-dir /tmp/nexus-tech-visual-audit/off"
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
            f"Launch with `--window-size {window_size}`. "
            f"{_required_terms_prompt(WINDOW_MATRIX_EVIDENCE_TERMS)} |"
        )

    lines.extend(
        [
            "",
            "## Visible Route Evidence",
            "",
            "| Step | Target | Window | Motion | Result | Evidence Notes |",
            "| ---: | --- | --- | --- | --- | --- |",
        ]
    )
    for index, item in enumerate(build_2d_animation_playtest_command_queue(), start=1):
        lines.append(
            "| "
            f"{index} | "
            f"`{item.target}` | "
            f"`{item.window_size}` | "
            f"`{item.motion_mode}` | "
            "`todo` | "
            f"{_animation_playtest_route_evidence(item)} |"
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
        lines.append(
            f"| {area} | `todo` | {required_check} "
            f"{_required_terms_prompt(CONTROL_EVIDENCE_TERMS[area])} | "
            "owner/date if not pass |"
        )

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
            f"| {scene} | `todo` | {required_check} "
            f"{_required_terms_prompt(SCENE_READABILITY_EVIDENCE_TERMS[scene])} | "
            f"Motion notes. {_required_terms_prompt(SCENE_MOTION_EVIDENCE_TERMS[scene])} | "
            "owner/date if not pass |"
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
        lines.append(
            f"| {area} | `todo` | {required_check} "
            f"{_required_terms_prompt(FEEDBACK_EVIDENCE_TERMS[area])} | "
            "owner/date if not pass |"
        )

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
