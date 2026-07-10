"""Automated first-time player clarity checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nexus_tech.config import DEFAULT_SCENARIO_ID, DEMO_SEED_EXAMPLE
from nexus_tech.domain.models import DifficultyMode, TurnAction
from nexus_tech.simulation.campaign_starts import STANDARD_CAMPAIGN_START_ID
from nexus_tech.simulation.engine import create_new_game
from nexus_tech.simulation.opening_guide import build_guided_opening
from nexus_tech.simulation.risk_forecast import build_risk_forecast
from nexus_tech.simulation.turn_coach import build_turn_coach

ONBOARDING_FLOW_AUDIT_REPORT_NAME = "onboarding-flow-audit.md"
ONBOARDING_VISIBLE_PLAYTEST_PACKET_NAME = "onboarding-visible-playtest.md"
ONBOARDING_VISIBLE_PLAYTEST_REPORT_NAME = "onboarding-visible-playtest-report.md"
ONBOARDING_VISIBLE_PLAYTEST_NEXT_NAME = "onboarding-visible-playtest-next.md"
ONBOARDING_VISIBLE_TERMINAL_BATCH_NAME = "onboarding-visible-terminal-batch.md"
ONBOARDING_VISIBLE_TERMINAL_EVIDENCE_SHEET_NAME = "onboarding-visible-terminal-evidence-sheet.md"
ONBOARDING_VISIBLE_WINDOW_EVIDENCE_SHEET_NAME = "onboarding-visible-window-evidence-sheet.md"
ONBOARDING_VISIBLE_EVIDENCE_MATRIX_NAME = "onboarding-visible-evidence-matrix.md"
ONBOARDING_VISIBLE_MANUAL_SESSION_NAME = "onboarding-visible-manual-session.md"
ONBOARDING_VISIBLE_UX_ISSUE_INTAKE_NAME = "onboarding-visible-ux-issue-intake.md"
ONBOARDING_VISIBLE_UX_FIX_PLAN_NAME = "onboarding-visible-ux-fix-plan.md"
ONBOARDING_VISIBLE_UX_TRIAGE_SPRINT_NAME = "onboarding-visible-ux-triage-sprint.md"
ONBOARDING_VISIBLE_UX_TRIAGE_NEXT_NAME = "onboarding-visible-ux-triage-next.md"
ONBOARDING_VISIBLE_UX_RECORDING_QUEUE_NAME = "onboarding-visible-ux-recording-queue.md"
ONBOARDING_VISIBLE_UX_PROGRESS_NAME = "onboarding-visible-ux-progress.md"
DEFAULT_ONBOARDING_VISIBLE_WINDOWS: tuple[tuple[int, int], ...] = (
    (820, 620),
    (1280, 720),
    (1440, 900),
)
DEFAULT_ONBOARDING_VISIBLE_MOTION_MODES: tuple[str, ...] = ("full", "reduced", "off")
ONBOARDING_VISIBLE_RESULT_VALUES: tuple[str, ...] = ("todo", "pass", "watch", "fail")
ONBOARDING_VISIBLE_NOTE_PLACEHOLDER = "<replace with observed visible-window notes>"
_PLACEHOLDER_TERMS = ("todo", "placeholder", "tbd", "unknown")
_GENERIC_NOTE_TERMS = (
    "ok",
    "good",
    "fine",
    "pass",
    "passed",
    "works",
    "n/a",
    "na",
    "none",
    "เรียบร้อย",
    "โอเค",
)


@dataclass(frozen=True)
class OnboardingFlowAuditCheck:
    """One first-time player clarity check."""

    area: str
    status: str
    summary: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class OnboardingFlowAuditReport:
    """Audit report for onboarding guidance and first-turn clarity."""

    scenario_id: str
    difficulty: str
    campaign_start_id: str
    checks: tuple[OnboardingFlowAuditCheck, ...]

    @property
    def status(self) -> str:
        """Return pass only when every onboarding clarity check passes."""

        return "pass" if all(check.status == "pass" for check in self.checks) else "fail"

    @property
    def failed_checks(self) -> tuple[OnboardingFlowAuditCheck, ...]:
        """Return checks that still block the onboarding gate."""

        return tuple(check for check in self.checks if check.status != "pass")


@dataclass(frozen=True)
class OnboardingVisiblePlaytestStep:
    """One visible-window onboarding playtest command."""

    rank: int
    route: str
    command: str
    objective: str
    required_evidence: tuple[str, ...]
    window: str = "terminal"
    motion_mode: str = "n/a"


@dataclass(frozen=True)
class OnboardingVisiblePlaytestPacket:
    """Manual visible-window packet for first-time player QA."""

    scenario_id: str
    difficulty: str
    campaign_start_id: str
    seed: int
    command_prefix: str
    windows: tuple[tuple[int, int], ...]
    motion_modes: tuple[str, ...]
    steps: tuple[OnboardingVisiblePlaytestStep, ...]

    @property
    def status(self) -> str:
        """Visible-window packets always require human execution."""

        return "manual-required"


@dataclass(frozen=True)
class OnboardingVisiblePlaytestValidationReport:
    """Validation report for a visible-window onboarding QA packet."""

    packet_path: Path
    checks: tuple[OnboardingFlowAuditCheck, ...]

    @property
    def status(self) -> str:
        """Return pass only when every packet integrity check passes."""

        return "pass" if all(check.status == "pass" for check in self.checks) else "fail"

    @property
    def failed_checks(self) -> tuple[OnboardingFlowAuditCheck, ...]:
        """Return packet checks that still block the handoff."""

        return tuple(check for check in self.checks if check.status != "pass")


@dataclass(frozen=True)
class OnboardingVisiblePlaytestReportRow:
    """One visible-window onboarding evidence row."""

    rank: int
    route: str
    window: str
    motion_mode: str
    command: str
    result: str
    evidence_notes: str
    required_evidence: tuple[str, ...]


@dataclass(frozen=True)
class OnboardingVisiblePlaytestEvidenceReport:
    """Manual visible-window onboarding evidence report."""

    packet_path: Path
    rows: tuple[OnboardingVisiblePlaytestReportRow, ...]

    @property
    def status(self) -> str:
        """Return release status from recorded visible-window evidence."""

        if any(row.result == "fail" for row in self.rows):
            return "fail"
        if self.rows and all(
            row.result == "pass" and _has_real_observation_notes(row.evidence_notes)
            for row in self.rows
        ):
            return "pass"
        return "manual-required"

    @property
    def incomplete_rows(self) -> tuple[OnboardingVisiblePlaytestReportRow, ...]:
        """Return rows that still need real visible-window observations."""

        return tuple(
            row
            for row in self.rows
            if row.result != "pass" or not _has_real_observation_notes(row.evidence_notes)
        )


@dataclass(frozen=True)
class OnboardingVisiblePlaytestEvidenceRecord:
    """Result of recording one onboarding visible QA row."""

    rank: int
    route: str
    window: str
    motion_mode: str
    result: str
    evidence_notes: str


@dataclass(frozen=True)
class OnboardingVisiblePlaytestReportValidation:
    """Validation report for onboarding visible QA evidence."""

    report_path: Path
    status: str
    checks: tuple[OnboardingFlowAuditCheck, ...]

    @property
    def ok(self) -> bool:
        """Return true when the evidence report structure is valid."""

        return all(check.status == "pass" for check in self.checks)

    @property
    def failed_checks(self) -> tuple[OnboardingFlowAuditCheck, ...]:
        """Return report checks that still block validation."""

        return tuple(check for check in self.checks if check.status != "pass")


@dataclass(frozen=True)
class OnboardingVisiblePlaytestStatusSummary:
    """Status and next action for onboarding visible QA evidence."""

    report_path: Path
    status: str
    total_rows: int
    pass_count: int
    watch_count: int
    fail_count: int
    todo_count: int
    incomplete_count: int
    next_row: OnboardingVisiblePlaytestReportRow | None
    next_visible_command: str
    next_recorder_command: str


@dataclass(frozen=True)
class OnboardingVisiblePlaytestNextStep:
    """Copy-ready handoff for the next visible-window onboarding QA action."""

    report_path: Path
    status: str
    total_rows: int
    pass_count: int
    watch_count: int
    fail_count: int
    todo_count: int
    incomplete_count: int
    next_row: OnboardingVisiblePlaytestReportRow | None
    next_visible_command: str
    next_recorder_command: str
    validate_command: str
    status_command: str


@dataclass(frozen=True)
class OnboardingVisiblePlaytestNextStepValidation:
    """Validation report for the next visible-window onboarding QA handoff."""

    next_path: Path
    status: str
    checks: tuple[OnboardingFlowAuditCheck, ...]

    @property
    def ok(self) -> bool:
        """Return true when the next-step handoff matches the current report."""

        return all(check.status == "pass" for check in self.checks)

    @property
    def failed_checks(self) -> tuple[OnboardingFlowAuditCheck, ...]:
        """Return next-step handoff checks that still block validation."""

        return tuple(check for check in self.checks if check.status != "pass")


@dataclass(frozen=True)
class OnboardingVisibleTerminalBatch:
    """Copy-ready handoff for the first terminal onboarding visible QA batch."""

    report_path: Path
    status: str
    total_rows: int
    terminal_rows: tuple[OnboardingVisiblePlaytestReportRow, ...]
    incomplete_terminal_rows: tuple[OnboardingVisiblePlaytestReportRow, ...]
    recorder_commands: tuple[str, ...]
    validate_command: str
    status_command: str
    next_step_command: str


@dataclass(frozen=True)
class OnboardingVisibleTerminalBatchValidation:
    """Validation report for the terminal onboarding visible QA batch handoff."""

    batch_path: Path
    status: str
    checks: tuple[OnboardingFlowAuditCheck, ...]

    @property
    def ok(self) -> bool:
        """Return true when the terminal batch matches the current report."""

        return all(check.status == "pass" for check in self.checks)

    @property
    def failed_checks(self) -> tuple[OnboardingFlowAuditCheck, ...]:
        """Return terminal batch checks that still block validation."""

        return tuple(check for check in self.checks if check.status != "pass")


@dataclass(frozen=True)
class OnboardingVisibleTerminalEvidenceSheet:
    """Evidence worksheet for closing the terminal onboarding visible QA rows."""

    report_path: Path
    status: str
    terminal_rows: tuple[OnboardingVisiblePlaytestReportRow, ...]
    incomplete_terminal_rows: tuple[OnboardingVisiblePlaytestReportRow, ...]
    recorder_commands: tuple[str, ...]
    validate_command: str
    status_command: str
    batch_command: str


@dataclass(frozen=True)
class OnboardingVisibleTerminalEvidenceSheetValidation:
    """Validation report for the terminal onboarding evidence worksheet."""

    sheet_path: Path
    status: str
    checks: tuple[OnboardingFlowAuditCheck, ...]

    @property
    def ok(self) -> bool:
        """Return true when the terminal evidence sheet matches the report."""

        return all(check.status == "pass" for check in self.checks)

    @property
    def failed_checks(self) -> tuple[OnboardingFlowAuditCheck, ...]:
        """Return terminal evidence sheet checks that still block validation."""

        return tuple(check for check in self.checks if check.status != "pass")


@dataclass(frozen=True)
class OnboardingVisibleWindowEvidenceSheet:
    """Evidence worksheet for one visible-window onboarding QA slice."""

    report_path: Path
    status: str
    window: str
    window_rows: tuple[OnboardingVisiblePlaytestReportRow, ...]
    incomplete_window_rows: tuple[OnboardingVisiblePlaytestReportRow, ...]
    recorder_commands: tuple[str, ...]
    validate_command: str
    status_command: str
    next_step_command: str


@dataclass(frozen=True)
class OnboardingVisibleWindowEvidenceSheetValidation:
    """Validation report for a visible-window onboarding evidence worksheet."""

    sheet_path: Path
    status: str
    checks: tuple[OnboardingFlowAuditCheck, ...]

    @property
    def ok(self) -> bool:
        """Return true when the visible-window evidence sheet matches the report."""

        return all(check.status == "pass" for check in self.checks)

    @property
    def failed_checks(self) -> tuple[OnboardingFlowAuditCheck, ...]:
        """Return visible-window evidence sheet checks that still block validation."""

        return tuple(check for check in self.checks if check.status != "pass")


@dataclass(frozen=True)
class OnboardingVisibleEvidenceMatrixGroup:
    """One terminal or visible-window group inside the onboarding evidence matrix."""

    name: str
    rows: tuple[OnboardingVisiblePlaytestReportRow, ...]
    recorder_commands: tuple[str, ...]
    pass_count: int
    watch_count: int
    fail_count: int
    todo_count: int
    incomplete_count: int


@dataclass(frozen=True)
class OnboardingVisibleEvidenceMatrix:
    """Cross-window onboarding evidence matrix for manual QA closeout."""

    report_path: Path
    status: str
    total_rows: int
    pass_count: int
    watch_count: int
    fail_count: int
    todo_count: int
    incomplete_count: int
    groups: tuple[OnboardingVisibleEvidenceMatrixGroup, ...]
    next_row: OnboardingVisiblePlaytestReportRow | None
    next_visible_command: str
    next_recorder_command: str
    validate_command: str
    status_command: str
    next_step_command: str


@dataclass(frozen=True)
class OnboardingVisibleEvidenceMatrixValidation:
    """Validation report for the onboarding visible evidence matrix artifact."""

    matrix_path: Path
    status: str
    checks: tuple[OnboardingFlowAuditCheck, ...]

    @property
    def ok(self) -> bool:
        """Return true when the matrix artifact matches the current report."""

        return all(check.status == "pass" for check in self.checks)

    @property
    def failed_checks(self) -> tuple[OnboardingFlowAuditCheck, ...]:
        """Return matrix checks that still block validation."""

        return tuple(check for check in self.checks if check.status != "pass")


@dataclass(frozen=True)
class OnboardingVisibleManualSession:
    """Operator session packet for recording real onboarding visible QA evidence."""

    report_path: Path
    status: str
    total_rows: int
    incomplete_count: int
    groups: tuple[OnboardingVisibleEvidenceMatrixGroup, ...]
    prerequisite_commands: tuple[str, ...]
    worksheet_commands: tuple[str, ...]
    closure_commands: tuple[str, ...]


@dataclass(frozen=True)
class OnboardingVisibleManualSessionValidation:
    """Validation report for the onboarding visible manual session artifact."""

    session_path: Path
    status: str
    checks: tuple[OnboardingFlowAuditCheck, ...]

    @property
    def ok(self) -> bool:
        """Return true when the manual session packet matches the current report."""

        return all(check.status == "pass" for check in self.checks)

    @property
    def failed_checks(self) -> tuple[OnboardingFlowAuditCheck, ...]:
        """Return manual session checks that still block validation."""

        return tuple(check for check in self.checks if check.status != "pass")


@dataclass(frozen=True)
class OnboardingVisibleUxIssueIntake:
    """UX issue intake sheet for real onboarding visible QA observations."""

    report_path: Path
    status: str
    total_rows: int
    incomplete_count: int
    groups: tuple[OnboardingVisibleEvidenceMatrixGroup, ...]
    manual_session_command: str
    preflight_command: str
    validate_report_command: str
    status_command: str


@dataclass(frozen=True)
class OnboardingVisibleUxIssueIntakeValidation:
    """Validation report for the onboarding visible UX issue intake artifact."""

    intake_path: Path
    status: str
    checks: tuple[OnboardingFlowAuditCheck, ...]

    @property
    def ok(self) -> bool:
        """Return true when the UX issue intake matches the current report."""

        return all(check.status == "pass" for check in self.checks)

    @property
    def failed_checks(self) -> tuple[OnboardingFlowAuditCheck, ...]:
        """Return UX issue intake checks that still block validation."""

        return tuple(check for check in self.checks if check.status != "pass")


@dataclass(frozen=True)
class OnboardingVisibleUxFixPlanRow:
    """One UX issue triage row carried from the visible onboarding intake."""

    group: str
    rank: int
    route: str
    window: str
    motion_mode: str
    result: str
    command: str
    ux_areas: str
    severity: str
    issue_notes: str
    follow_up: str


@dataclass(frozen=True)
class OnboardingVisibleUxIssueRecord:
    """One recorded UX issue intake row update."""

    intake_path: Path
    row: OnboardingVisibleUxFixPlanRow


@dataclass(frozen=True)
class OnboardingVisibleUxFixPlan:
    """Prioritized UX fix plan derived from real visible onboarding issue intake."""

    report_path: Path
    intake_path: Path
    status: str
    rows: tuple[OnboardingVisibleUxFixPlanRow, ...]
    p0_count: int
    p1_count: int
    p2_count: int
    none_count: int
    todo_count: int
    validate_intake_command: str
    validate_report_command: str
    status_command: str

    @property
    def total_rows(self) -> int:
        """Return the number of visible onboarding UX rows in the plan."""

        return len(self.rows)


@dataclass(frozen=True)
class OnboardingVisibleUxFixPlanValidation:
    """Validation report for the onboarding visible UX fix plan artifact."""

    plan_path: Path
    status: str
    checks: tuple[OnboardingFlowAuditCheck, ...]

    @property
    def ok(self) -> bool:
        """Return true when the UX fix plan matches the current intake."""

        return all(check.status == "pass" for check in self.checks)

    @property
    def failed_checks(self) -> tuple[OnboardingFlowAuditCheck, ...]:
        """Return UX fix plan checks that still block validation."""

        return tuple(check for check in self.checks if check.status != "pass")


@dataclass(frozen=True)
class OnboardingVisibleUxTriageSprint:
    """Focused sprint packet for closing visible onboarding UX triage and fixes."""

    report_path: Path
    intake_path: Path
    plan_path: Path
    status: str
    rows: tuple[OnboardingVisibleUxFixPlanRow, ...]
    p0_count: int
    p1_count: int
    p2_count: int
    none_count: int
    todo_count: int
    rebuild_fix_plan_command: str
    validate_fix_plan_command: str
    validate_intake_command: str
    validate_report_command: str
    status_command: str

    @property
    def total_rows(self) -> int:
        """Return the number of rows carried into the UX triage sprint."""

        return len(self.rows)

    @property
    def blocker_count(self) -> int:
        """Return P0/P1 blockers that must close before UI signoff."""

        return self.p0_count + self.p1_count


@dataclass(frozen=True)
class OnboardingVisibleUxTriageSprintValidation:
    """Validation report for the onboarding visible UX triage sprint artifact."""

    sprint_path: Path
    status: str
    checks: tuple[OnboardingFlowAuditCheck, ...]

    @property
    def ok(self) -> bool:
        """Return true when the sprint packet matches the current fix plan."""

        return all(check.status == "pass" for check in self.checks)

    @property
    def failed_checks(self) -> tuple[OnboardingFlowAuditCheck, ...]:
        """Return triage sprint checks that still block validation."""

        return tuple(check for check in self.checks if check.status != "pass")


@dataclass(frozen=True)
class OnboardingVisibleUxTriageNextStep:
    """Copy-ready next action from the onboarding visible UX triage sprint."""

    report_path: Path
    intake_path: Path
    plan_path: Path
    sprint_path: Path
    status: str
    row: OnboardingVisibleUxFixPlanRow
    phase: str
    priority: str
    open_command: str
    report_recorder_command: str
    intake_recorder_command: str
    validate_intake_command: str
    rebuild_fix_plan_command: str
    validate_fix_plan_command: str
    rebuild_sprint_command: str
    validate_sprint_command: str
    validate_report_command: str
    status_command: str


@dataclass(frozen=True)
class OnboardingVisibleUxTriageNextStepValidation:
    """Validation report for the onboarding visible UX triage next-step artifact."""

    next_path: Path
    status: str
    checks: tuple[OnboardingFlowAuditCheck, ...]

    @property
    def ok(self) -> bool:
        """Return true when the next-step handoff matches the current sprint."""

        return all(check.status == "pass" for check in self.checks)

    @property
    def failed_checks(self) -> tuple[OnboardingFlowAuditCheck, ...]:
        """Return next-step checks that still block validation."""

        return tuple(check for check in self.checks if check.status != "pass")


@dataclass(frozen=True)
class OnboardingVisibleUxRecordingQueueRow:
    """One copy-ready manual recording row from the onboarding UX sprint."""

    row: OnboardingVisibleUxFixPlanRow
    phase: str
    priority: str
    open_command: str
    report_recorder_command: str
    intake_recorder_command: str


@dataclass(frozen=True)
class OnboardingVisibleUxRecordingQueue:
    """Manual queue for recording onboarding visible UX evidence without fabrication."""

    report_path: Path
    intake_path: Path
    plan_path: Path
    sprint_path: Path
    status: str
    rows: tuple[OnboardingVisibleUxRecordingQueueRow, ...]
    blocker_count: int
    todo_count: int
    validate_intake_command: str
    rebuild_fix_plan_command: str
    validate_fix_plan_command: str
    rebuild_sprint_command: str
    validate_sprint_command: str
    validate_report_command: str
    status_command: str

    @property
    def total_rows(self) -> int:
        """Return the number of manual recording rows still needing attention."""

        return len(self.rows)


@dataclass(frozen=True)
class OnboardingVisibleUxRecordingQueueValidation:
    """Validation report for the onboarding visible UX recording queue artifact."""

    queue_path: Path
    status: str
    checks: tuple[OnboardingFlowAuditCheck, ...]

    @property
    def ok(self) -> bool:
        """Return true when the queue matches the current UX triage sprint."""

        return all(check.status == "pass" for check in self.checks)

    @property
    def failed_checks(self) -> tuple[OnboardingFlowAuditCheck, ...]:
        """Return recording queue checks that still block validation."""

        return tuple(check for check in self.checks if check.status != "pass")


@dataclass(frozen=True)
class OnboardingVisibleUxProgressBoard:
    """Progress board for onboarding visible UX evidence closure."""

    report_path: Path
    intake_path: Path
    plan_path: Path
    sprint_path: Path
    queue_path: Path
    status: str
    total_rows: int
    report_complete_count: int
    report_incomplete_count: int
    intake_classified_count: int
    intake_todo_count: int
    blocker_count: int
    queue_count: int
    next_row: OnboardingVisibleUxRecordingQueueRow | None
    validate_report_command: str
    validate_intake_command: str
    rebuild_queue_command: str
    validate_queue_command: str
    status_command: str

    @property
    def completion_percent(self) -> int:
        """Return percent of rows with both report evidence and intake classification."""

        if self.total_rows <= 0:
            return 100
        closed_rows = min(self.report_complete_count, self.intake_classified_count)
        return round((closed_rows / self.total_rows) * 100)


@dataclass(frozen=True)
class OnboardingVisibleUxProgressBoardValidation:
    """Validation report for the onboarding visible UX progress board artifact."""

    progress_path: Path
    status: str
    checks: tuple[OnboardingFlowAuditCheck, ...]

    @property
    def ok(self) -> bool:
        """Return true when the progress board matches the current queue."""

        return all(check.status == "pass" for check in self.checks)

    @property
    def failed_checks(self) -> tuple[OnboardingFlowAuditCheck, ...]:
        """Return progress board checks that still block validation."""

        return tuple(check for check in self.checks if check.status != "pass")


def run_onboarding_flow_audit(
    *,
    scenario_id: str = DEFAULT_SCENARIO_ID,
    difficulty_mode: DifficultyMode | None = DifficultyMode.BUILDER,
    campaign_start_id: str = STANDARD_CAMPAIGN_START_ID,
) -> OnboardingFlowAuditReport:
    """Build a fresh run and verify the first-time player guidance path."""

    state = create_new_game(
        "NEXUS TECH",
        "Nexus One",
        scenario_id=scenario_id,
        difficulty_mode=difficulty_mode,
        campaign_start_id=campaign_start_id,
    )
    opening = build_guided_opening(state)
    coach = build_turn_coach(state)
    forecast = build_risk_forecast(state)
    valid_commands = {action.value for action in TurnAction}

    checks = (
        _build_check(
            area="Guided Opening",
            passed=(
                opening.active
                and len(opening.steps) >= 6
                and opening.current_command in valid_commands
                and all(step.command in valid_commands for step in opening.steps)
                and all(step.status in {"done", "next", "later"} for step in opening.steps)
                and _is_clear_copy(opening.headline, opening.summary)
            ),
            summary="Opening guide has a valid current command, six-step path, and clear copy.",
            evidence=(
                f"current:{opening.current_command}",
                f"steps:{len(opening.steps)}",
                f"statuses:{','.join(sorted({step.status for step in opening.steps}))}",
            ),
        ),
        _build_check(
            area="Safe First Actions",
            passed=_safe_first_actions_present(tuple(step.command for step in opening.steps)),
            summary="Opening path starts with hire/assign and includes quality, end turn, report.",
            evidence=tuple(step.command for step in opening.steps[:6]),
        ),
        _build_check(
            area="Turn Coach",
            passed=(
                coach.primary_command in valid_commands
                and 2 <= len(coach.recommendations) <= 4
                and {recommendation.rank for recommendation in coach.recommendations}
                == set(range(1, len(coach.recommendations) + 1))
                and all(
                    recommendation.command in valid_commands
                    and recommendation.rationale
                    and recommendation.consequence
                    and recommendation.horizon_turns >= 1
                    for recommendation in coach.recommendations
                )
                and _is_clear_copy(coach.summary, coach.focus)
            ),
            summary="Turn Coach gives ranked valid commands with consequences and horizons.",
            evidence=(
                f"primary:{coach.primary_command}",
                f"recommendations:{len(coach.recommendations)}",
                f"window:{coach.mission_window}",
            ),
        ),
        _build_check(
            area="Risk Forecast",
            passed=(
                forecast.top_command in valid_commands
                and len(forecast.items) >= 1
                and all(
                    item.command in valid_commands
                    and item.summary
                    and item.consequence
                    and item.horizon_turns >= 1
                    for item in forecast.items
                )
                and _is_clear_copy(forecast.headline, forecast.overall_risk)
            ),
            summary="Risk Forecast exposes at least one valid next-risk mitigation command.",
            evidence=(
                f"top:{forecast.top_command}",
                f"items:{len(forecast.items)}",
                f"risk:{forecast.overall_risk}",
            ),
        ),
        _build_check(
            area="Cross-Panel Handoff",
            passed=(
                coach.primary_command
                in {recommendation.command for recommendation in coach.recommendations}
                and forecast.top_command in valid_commands
                and opening.current_command in valid_commands
                and _is_clear_copy(
                    opening.summary,
                    coach.summary,
                    forecast.headline,
                )
            ),
            summary="Opening, coach, and forecast all hand off through concrete valid commands.",
            evidence=(
                f"opening:{opening.current_command}",
                f"coach:{coach.primary_command}",
                f"forecast:{forecast.top_command}",
            ),
        ),
    )

    difficulty = state.difficulty_mode.value if state.difficulty_mode is not None else "scenario"
    return OnboardingFlowAuditReport(
        scenario_id=scenario_id,
        difficulty=difficulty,
        campaign_start_id=campaign_start_id,
        checks=checks,
    )


def build_onboarding_visible_playtest_packet(
    *,
    scenario_id: str = DEFAULT_SCENARIO_ID,
    difficulty_mode: DifficultyMode | None = DifficultyMode.BUILDER,
    campaign_start_id: str = STANDARD_CAMPAIGN_START_ID,
    seed: int = DEMO_SEED_EXAMPLE,
    command_prefix: str = "uv run nexus-tech",
    windows: tuple[tuple[int, int], ...] = DEFAULT_ONBOARDING_VISIBLE_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_ONBOARDING_VISIBLE_MOTION_MODES,
) -> OnboardingVisiblePlaytestPacket:
    """Build the manual visible-window packet for first-time player QA."""

    difficulty = difficulty_mode.value if difficulty_mode is not None else "scenario"
    base_play_args = f"--scenario {scenario_id} --campaign-start {campaign_start_id} --seed {seed}"
    if difficulty_mode is not None:
        base_play_args = f"{base_play_args} --difficulty {difficulty_mode.value}"

    steps: list[OnboardingVisiblePlaytestStep] = [
        OnboardingVisiblePlaytestStep(
            rank=1,
            route="terminal-guide",
            command=f"{command_prefix} guide",
            objective="Confirm the quick guide tells a first-time player where to look first.",
            required_evidence=("Opening flow", "Risk Forecast", "Difficulty cues"),
        ),
        OnboardingVisiblePlaytestStep(
            rank=2,
            route="terminal-tutorial",
            command=f"{command_prefix} tutorial",
            objective="Confirm the tutorial names the safe first actions and watch-for fields.",
            required_evidence=("hire_employee", "Turn Summary", "Watch For"),
        ),
        OnboardingVisiblePlaytestStep(
            rank=3,
            route="automated-clarity-gate",
            command=(
                f"{command_prefix} audit-onboarding-flow "
                "--output /tmp/nexus-tech-onboarding-flow-audit.md"
            ),
            objective="Refresh automated onboarding clarity evidence before the visible pass.",
            required_evidence=("Guided Opening", "Turn Coach", "Risk Forecast"),
        ),
    ]

    for width, height in windows:
        window = f"{width}x{height}"
        for motion_mode in motion_modes:
            steps.append(
                OnboardingVisiblePlaytestStep(
                    rank=len(steps) + 1,
                    route="title-onboarding",
                    command=(
                        f"{command_prefix} menu-2d --window-size {window} "
                        f"--motion-mode {motion_mode}"
                    ),
                    objective=(
                        "Verify the title menu, wizard path, help affordance, and save/meta "
                        "navigation are discoverable without source-code knowledge."
                    ),
                    required_evidence=(
                        "title",
                        "wizard",
                        "help",
                        "back/menu",
                    ),
                    window=window,
                    motion_mode=motion_mode,
                )
            )
            steps.append(
                OnboardingVisiblePlaytestStep(
                    rank=len(steps) + 1,
                    route="first-turn-play",
                    command=(
                        f"{command_prefix} play-2d {base_play_args} "
                        f"--window-size {window} --motion-mode {motion_mode}"
                    ),
                    objective=(
                        "Verify a new player can read the first-turn coach, risk forecast, "
                        "action bar, pause/back/menu controls, and next command."
                    ),
                    required_evidence=(
                        "coach",
                        "risk",
                        "next command",
                        "pause/back/menu",
                    ),
                    window=window,
                    motion_mode=motion_mode,
                )
            )

    return OnboardingVisiblePlaytestPacket(
        scenario_id=scenario_id,
        difficulty=difficulty,
        campaign_start_id=campaign_start_id,
        seed=seed,
        command_prefix=command_prefix,
        windows=windows,
        motion_modes=motion_modes,
        steps=tuple(steps),
    )


def write_onboarding_flow_audit_report(
    report: OnboardingFlowAuditReport,
    output_path: Path,
) -> None:
    """Write a Markdown artifact for first-time player onboarding readiness."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NEXUS TECH Onboarding Flow Audit",
        "",
        f"- Scenario: `{report.scenario_id}`",
        f"- Difficulty: `{report.difficulty}`",
        f"- Campaign start: `{report.campaign_start_id}`",
        f"- Status: `{report.status}`",
        f"- Checks: `{len(report.checks)}` total, "
        f"`{len(report.checks) - len(report.failed_checks)}` pass, "
        f"`{len(report.failed_checks)}` fail",
        "- Manual result: `not completed by automation`",
        "",
        "This automated gate confirms first-time guidance uses concrete commands and clear "
        "handoffs. It does not replace visible-window playtest notes.",
        "",
        "| Area | Status | Summary | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for check in report.checks:
        lines.append(
            "| "
            f"`{check.area}` | "
            f"`{check.status}` | "
            f"{_markdown_escape(check.summary)} | "
            f"{_markdown_escape(', '.join(check.evidence))} |"
        )
    lines.extend(
        [
            "",
            "## Manual Follow-up",
            "",
            "- Run the visible tutorial/menu/play path before beta signoff.",
            "- Confirm a new player can identify the next command without reading source code.",
            "- Keep `MANUAL-REQUIRED` if tutorial, coach, risk, or button copy feels ambiguous.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_onboarding_visible_playtest_packet(
    packet: OnboardingVisiblePlaytestPacket,
    output_path: Path,
) -> None:
    """Write a Markdown visible-window onboarding QA packet."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    window_labels = ", ".join(f"{width}x{height}" for width, height in packet.windows)
    lines = [
        "# NEXUS TECH Onboarding Visible Playtest Packet",
        "",
        f"- Scenario: `{packet.scenario_id}`",
        f"- Difficulty: `{packet.difficulty}`",
        f"- Campaign start: `{packet.campaign_start_id}`",
        f"- Seed: `{packet.seed}`",
        f"- Command prefix: `{packet.command_prefix}`",
        f"- Windows: `{window_labels}`",
        f"- Motion modes: `{', '.join(packet.motion_modes)}`",
        f"- Status: `{packet.status}`",
        "- Manual result: `not completed by automation`",
        "",
        "Run these commands in a real visible window. Do not mark onboarding beta-ready until "
        "a tester records concrete notes for each route.",
        "",
        "| # | Route | Window | Motion | Command | Required Evidence | Objective |",
        "| ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for step in packet.steps:
        lines.append(
            "| "
            f"{step.rank} | "
            f"`{step.route}` | "
            f"`{step.window}` | "
            f"`{step.motion_mode}` | "
            f"`{_markdown_escape(step.command)}` | "
            f"{_markdown_escape(', '.join(step.required_evidence))} | "
            f"{_markdown_escape(step.objective)} |"
        )
    lines.extend(
        [
            "",
            "## Result Rules",
            "",
            "- `pass`: the player can identify the next command and recover with pause/back/menu.",
            "- `watch`: playable, but copy, contrast, motion, or placement slows understanding.",
            (
                "- `fail`: the player cannot find the next command, recover navigation, "
                "or read a key panel."
            ),
            (
                "- Keep `MANUAL-REQUIRED` until visible-window observations replace "
                "these instructions."
            ),
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_onboarding_visible_playtest_evidence_report(
    packet: OnboardingVisiblePlaytestPacket,
    *,
    packet_path: Path = Path("/tmp/nexus-tech-onboarding-visible-playtest.md"),
) -> OnboardingVisiblePlaytestEvidenceReport:
    """Build a manual evidence report draft from a visible onboarding packet."""

    rows = tuple(
        OnboardingVisiblePlaytestReportRow(
            rank=step.rank,
            route=step.route,
            window=step.window,
            motion_mode=step.motion_mode,
            command=step.command,
            result="todo",
            evidence_notes=ONBOARDING_VISIBLE_NOTE_PLACEHOLDER,
            required_evidence=step.required_evidence,
        )
        for step in packet.steps
    )
    return OnboardingVisiblePlaytestEvidenceReport(
        packet_path=packet_path,
        rows=rows,
    )


def write_onboarding_visible_playtest_evidence_report(
    report: OnboardingVisiblePlaytestEvidenceReport,
    output_path: Path,
) -> None:
    """Write a Markdown evidence report for real visible-window onboarding QA."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NEXUS TECH Onboarding Visible Playtest Report",
        "",
        f"- Packet: `{report.packet_path}`",
        f"- Status: `{report.status}`",
        f"- Rows: `{len(report.rows)}`",
        "- Evidence policy: `real visible-window observations required`",
        "- Recorder command: `record-onboarding-visible-playtest-route`",
        "",
        "This report stores human-visible onboarding evidence. Generated `todo` rows are "
        "not signoff; replace them only after opening the game window and observing the route.",
        "",
        "| # | Route | Window | Motion | Command | Result | Evidence Notes | Required Evidence |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report.rows:
        lines.append(_format_onboarding_visible_report_row(row))
    lines.extend(
        [
            "",
            "## Result Rules",
            "",
            "- `pass`: readable, navigable, and the next command/recovery path is clear.",
            "- `watch`: playable, but has a concrete UI, copy, contrast, or motion concern.",
            "- `fail`: route blocks navigation, readability, or first-turn understanding.",
            "- Keep `manual-required` until every row is recorded from a real window.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_onboarding_visible_playtest_packet(
    packet_path: Path,
    *,
    scenario_id: str = DEFAULT_SCENARIO_ID,
    difficulty_mode: DifficultyMode | None = DifficultyMode.BUILDER,
    campaign_start_id: str = STANDARD_CAMPAIGN_START_ID,
    seed: int = DEMO_SEED_EXAMPLE,
    command_prefix: str = "uv run nexus-tech",
    windows: tuple[tuple[int, int], ...] = DEFAULT_ONBOARDING_VISIBLE_WINDOWS,
    motion_modes: tuple[str, ...] = DEFAULT_ONBOARDING_VISIBLE_MOTION_MODES,
) -> OnboardingVisiblePlaytestValidationReport:
    """Validate that a visible-window onboarding packet matches current expectations."""

    expected = build_onboarding_visible_playtest_packet(
        scenario_id=scenario_id,
        difficulty_mode=difficulty_mode,
        campaign_start_id=campaign_start_id,
        seed=seed,
        command_prefix=command_prefix,
        windows=windows,
        motion_modes=motion_modes,
    )
    if not packet_path.exists():
        return OnboardingVisiblePlaytestValidationReport(
            packet_path=packet_path,
            checks=(
                _build_check(
                    area="Packet File",
                    passed=False,
                    summary="The onboarding visible playtest packet file must exist.",
                    evidence=(f"missing:{packet_path}",),
                ),
            ),
        )

    text = packet_path.read_text(encoding="utf-8")
    metadata_markers = (
        "# NEXUS TECH Onboarding Visible Playtest Packet",
        f"- Scenario: `{expected.scenario_id}`",
        f"- Difficulty: `{expected.difficulty}`",
        f"- Campaign start: `{expected.campaign_start_id}`",
        f"- Seed: `{expected.seed}`",
        f"- Command prefix: `{expected.command_prefix}`",
        "- Status: `manual-required`",
        "- Manual result: `not completed by automation`",
    )
    window_labels = ", ".join(f"{width}x{height}" for width, height in expected.windows)
    command_markers = tuple(step.command for step in expected.steps)
    route_markers = tuple(f"`{step.route}`" for step in expected.steps)
    evidence_markers = tuple(
        marker for step in expected.steps for marker in (*step.required_evidence, step.objective)
    )
    guardrail_markers = (
        "Run these commands in a real visible window.",
        "Do not mark onboarding beta-ready",
        "- `pass`: the player can identify the next command",
        "- `watch`: playable, but copy, contrast, motion, or placement slows understanding.",
        "- `fail`: the player cannot find the next command",
        "Keep `MANUAL-REQUIRED` until visible-window observations replace",
    )
    checks = (
        _build_presence_check(
            area="Packet Metadata",
            text=text,
            markers=(
                *metadata_markers,
                f"- Windows: `{window_labels}`",
                f"- Motion modes: `{', '.join(expected.motion_modes)}`",
            ),
            summary="Metadata matches the current onboarding visible playtest target.",
        ),
        _build_presence_check(
            area="Visible Commands",
            text=text,
            markers=command_markers,
            summary="Every expected guide/tutorial/audit/menu/play command is present.",
        ),
        _build_presence_check(
            area="Route Matrix",
            text=text,
            markers=route_markers,
            summary="Every expected terminal, title, and first-turn route row is present.",
        ),
        _build_presence_check(
            area="Evidence Prompts",
            text=text,
            markers=evidence_markers,
            summary="Tester-facing evidence prompts and objectives are intact.",
        ),
        _build_presence_check(
            area="Manual Guardrails",
            text=text,
            markers=guardrail_markers,
            summary="The packet still blocks beta signoff until real visible QA is recorded.",
        ),
    )
    return OnboardingVisiblePlaytestValidationReport(
        packet_path=packet_path,
        checks=checks,
    )


def record_onboarding_visible_playtest_route(
    report_path: Path,
    *,
    result: str,
    evidence_notes: str,
    rank: int | None = None,
    route: str | None = None,
    window: str | None = None,
    motion_mode: str | None = None,
) -> OnboardingVisiblePlaytestEvidenceRecord:
    """Record one real visible-window onboarding QA observation."""

    normalized_result = result.strip().lower()
    if normalized_result not in {"pass", "watch", "fail"}:
        raise ValueError("Result must be one of: pass, watch, fail.")
    if not _has_real_observation_notes(evidence_notes):
        raise ValueError(
            "Evidence notes must describe a real visible-window observation, not a placeholder."
        )
    report = read_onboarding_visible_playtest_evidence_report(report_path)
    matched_index = _find_onboarding_visible_report_row(
        report.rows,
        rank=rank,
        route=route,
        window=window,
        motion_mode=motion_mode,
    )
    updated_row = OnboardingVisiblePlaytestReportRow(
        rank=report.rows[matched_index].rank,
        route=report.rows[matched_index].route,
        window=report.rows[matched_index].window,
        motion_mode=report.rows[matched_index].motion_mode,
        command=report.rows[matched_index].command,
        result=normalized_result,
        evidence_notes=evidence_notes.strip(),
        required_evidence=report.rows[matched_index].required_evidence,
    )
    updated_rows = (
        *report.rows[:matched_index],
        updated_row,
        *report.rows[matched_index + 1 :],
    )
    write_onboarding_visible_playtest_evidence_report(
        OnboardingVisiblePlaytestEvidenceReport(
            packet_path=report.packet_path,
            rows=updated_rows,
        ),
        report_path,
    )
    return OnboardingVisiblePlaytestEvidenceRecord(
        rank=updated_row.rank,
        route=updated_row.route,
        window=updated_row.window,
        motion_mode=updated_row.motion_mode,
        result=updated_row.result,
        evidence_notes=updated_row.evidence_notes,
    )


def validate_onboarding_visible_playtest_evidence_report(
    report_path: Path,
    *,
    packet: OnboardingVisiblePlaytestPacket,
) -> OnboardingVisiblePlaytestReportValidation:
    """Validate a manual visible-window onboarding evidence report artifact."""

    if not report_path.exists():
        return OnboardingVisiblePlaytestReportValidation(
            report_path=report_path,
            status="fail",
            checks=(
                _build_check(
                    area="Evidence Report File",
                    passed=False,
                    summary="The onboarding visible playtest evidence report must exist.",
                    evidence=(f"missing:{report_path}",),
                ),
            ),
        )

    text = report_path.read_text(encoding="utf-8")
    try:
        report = read_onboarding_visible_playtest_evidence_report(report_path)
    except ValueError as error:
        return OnboardingVisiblePlaytestReportValidation(
            report_path=report_path,
            status="fail",
            checks=(
                _build_check(
                    area="Evidence Report Parse",
                    passed=False,
                    summary="The onboarding visible playtest report must be parseable.",
                    evidence=(str(error),),
                ),
            ),
        )

    expected_keys = tuple(
        (step.rank, step.route, step.window, step.motion_mode, step.command)
        for step in packet.steps
    )
    row_keys = tuple(
        (row.rank, row.route, row.window, row.motion_mode, row.command) for row in report.rows
    )
    expected_required = {
        (
            step.rank,
            step.route,
            step.window,
            step.motion_mode,
            step.command,
        ): step.required_evidence
        for step in packet.steps
    }
    invalid_results = tuple(
        row.result for row in report.rows if row.result not in ONBOARDING_VISIBLE_RESULT_VALUES
    )
    stale_required = tuple(
        f"{row.rank}:{row.route}"
        for row in report.rows
        if row.required_evidence
        != expected_required.get(
            (row.rank, row.route, row.window, row.motion_mode, row.command),
            (),
        )
    )
    bad_notes = tuple(
        f"{row.rank}:{row.route}"
        for row in report.rows
        if row.result in {"pass", "watch", "fail"}
        and not _has_real_observation_notes(row.evidence_notes)
    )
    checks = (
        _build_presence_check(
            area="Evidence Report Structure",
            text=text,
            markers=(
                "# NEXUS TECH Onboarding Visible Playtest Report",
                "- Evidence policy: `real visible-window observations required`",
                "- Recorder command: `record-onboarding-visible-playtest-route`",
                (
                    "| # | Route | Window | Motion | Command | Result | Evidence Notes | "
                    "Required Evidence |"
                ),
                "## Result Rules",
            ),
            summary="The evidence report keeps the required sections and recorder guidance.",
        ),
        _build_check(
            area="Route Rows",
            passed=row_keys == expected_keys,
            summary="The evidence report rows match the current onboarding visible packet.",
            evidence=(
                f"expected:{len(expected_keys)}",
                f"actual:{len(row_keys)}",
            )
            if row_keys == expected_keys
            else (
                f"missing:{len(set(expected_keys) - set(row_keys))}",
                f"unexpected:{len(set(row_keys) - set(expected_keys))}",
            ),
        ),
        _build_check(
            area="Result Values",
            passed=not invalid_results,
            summary="Every evidence row uses a supported result value.",
            evidence=("valid",)
            if not invalid_results
            else tuple(f"invalid:{value}" for value in invalid_results[:8]),
        ),
        _build_check(
            area="Required Evidence",
            passed=not stale_required,
            summary="Required evidence prompts still match the packet.",
            evidence=("current",)
            if not stale_required
            else tuple(f"stale:{value}" for value in stale_required[:8]),
        ),
        _build_check(
            area="Recorded Notes",
            passed=not bad_notes,
            summary="Recorded pass/watch/fail rows use real visible-window notes.",
            evidence=("todo rows allowed",)
            if not bad_notes
            else tuple(f"placeholder:{value}" for value in bad_notes[:8]),
        ),
        _build_check(
            area="Status Line",
            passed=f"- Status: `{report.status}`" in text,
            summary="The report status line matches the recorded rows.",
            evidence=(f"status:{report.status}",),
        ),
    )
    return OnboardingVisiblePlaytestReportValidation(
        report_path=report_path,
        status=report.status if all(check.status == "pass" for check in checks) else "fail",
        checks=checks,
    )


def summarize_onboarding_visible_playtest_status(
    report_path: Path,
    *,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisiblePlaytestStatusSummary:
    """Return visible onboarding QA progress and the next recorder command."""

    report = read_onboarding_visible_playtest_evidence_report(report_path)
    pass_count = sum(1 for row in report.rows if row.result == "pass")
    watch_count = sum(1 for row in report.rows if row.result == "watch")
    fail_count = sum(1 for row in report.rows if row.result == "fail")
    todo_count = sum(1 for row in report.rows if row.result == "todo")
    next_row = report.incomplete_rows[0] if report.incomplete_rows else None
    next_visible_command = (
        next_row.command
        if next_row is not None
        else (
            f"{command_prefix} validate-onboarding-visible-playtest-report --report {report_path}"
        )
    )
    next_recorder_command = (
        _build_onboarding_visible_recorder_command(
            report_path,
            next_row,
            command_prefix=command_prefix,
        )
        if next_row is not None
        else (
            f"{command_prefix} validate-onboarding-visible-playtest-report --report {report_path}"
        )
    )
    return OnboardingVisiblePlaytestStatusSummary(
        report_path=report_path,
        status=report.status,
        total_rows=len(report.rows),
        pass_count=pass_count,
        watch_count=watch_count,
        fail_count=fail_count,
        todo_count=todo_count,
        incomplete_count=len(report.incomplete_rows),
        next_row=next_row,
        next_visible_command=next_visible_command,
        next_recorder_command=next_recorder_command,
    )


def build_onboarding_visible_playtest_next_step(
    report_path: Path,
    *,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisiblePlaytestNextStep:
    """Build a copy-ready next-step packet from the current visible QA report."""

    summary = summarize_onboarding_visible_playtest_status(
        report_path,
        command_prefix=command_prefix,
    )
    validate_command = (
        f"{command_prefix} validate-onboarding-visible-playtest-report --report {report_path}"
    )
    status_command = f"{command_prefix} onboarding-visible-playtest-status --report {report_path}"
    return OnboardingVisiblePlaytestNextStep(
        report_path=summary.report_path,
        status=summary.status,
        total_rows=summary.total_rows,
        pass_count=summary.pass_count,
        watch_count=summary.watch_count,
        fail_count=summary.fail_count,
        todo_count=summary.todo_count,
        incomplete_count=summary.incomplete_count,
        next_row=summary.next_row,
        next_visible_command=summary.next_visible_command,
        next_recorder_command=summary.next_recorder_command,
        validate_command=validate_command,
        status_command=status_command,
    )


def write_onboarding_visible_playtest_next_step(
    next_step: OnboardingVisiblePlaytestNextStep,
    output_path: Path,
) -> None:
    """Write a copy-ready Markdown packet for the next manual visible QA action."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NEXUS TECH Onboarding Visible Next Step",
        "",
        f"- Report: `{next_step.report_path}`",
        f"- Status: `{next_step.status}`",
        f"- Rows: `{next_step.total_rows}`",
        f"- Pass: `{next_step.pass_count}`",
        f"- Watch: `{next_step.watch_count}`",
        f"- Fail: `{next_step.fail_count}`",
        f"- Todo: `{next_step.todo_count}`",
        f"- Incomplete: `{next_step.incomplete_count}`",
        "- Evidence policy: `real visible-window observations required`",
        "",
    ]
    if next_step.next_row is None:
        lines.extend(
            [
                "## Next Action",
                "",
                "All visible onboarding rows are recorded as `pass` with concrete notes.",
                "Run validation before treating the onboarding visible gate as closed.",
                "",
                "```bash",
                next_step.validate_command,
                "```",
                "",
                "```bash",
                next_step.status_command,
                "```",
                "",
                "## Result Rules",
                "",
                "- `pass`: readable, navigable, and the next command/recovery path is clear.",
                "- `watch`: playable, but has a concrete UI, copy, contrast, or motion concern.",
                "- `fail`: route blocks navigation, readability, or first-turn understanding.",
            ]
        )
    else:
        row = next_step.next_row
        lines.extend(
            [
                "## Next Action",
                "",
                "| Rank | Route | Window | Motion | Result |",
                "| ---: | --- | --- | --- | --- |",
                (
                    f"| {row.rank} | `{row.route}` | `{row.window}` | "
                    f"`{row.motion_mode}` | `{row.result}` |"
                ),
                "",
                "## Copy Commands",
                "",
                "### 1. Open The Visible Route",
                "",
                "```bash",
                next_step.next_visible_command,
                "```",
                "",
                "### 2. Record The Observation After Playing",
                "",
                "Replace the placeholder notes with concrete visible-window observations.",
                "",
                "```bash",
                next_step.next_recorder_command,
                "```",
                "",
                "### 3. Validate And Refresh Status",
                "",
                "```bash",
                next_step.validate_command,
                next_step.status_command,
                "```",
                "",
                "## Evidence Checklist",
                "",
                *(
                    f"- {item}"
                    for item in (
                        *row.required_evidence,
                        "Text stays inside its panel and remains readable.",
                        "Pause/back/menu recovery affordance is visible where the route needs it.",
                        "Notes mention the route, window/motion mode, and observed UI behavior.",
                    )
                ),
                "",
                "## Result Rules",
                "",
                "- `pass`: readable, navigable, and the next command/recovery path is clear.",
                "- `watch`: playable, but has a concrete UI, copy, contrast, or motion concern.",
                "- `fail`: route blocks navigation, readability, or first-turn understanding.",
            ]
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_onboarding_visible_playtest_next_step(
    next_path: Path,
    *,
    report_path: Path,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisiblePlaytestNextStepValidation:
    """Validate that a next-step handoff matches the current visible QA report."""

    try:
        expected = build_onboarding_visible_playtest_next_step(
            report_path,
            command_prefix=command_prefix,
        )
    except (OSError, ValueError) as error:
        return OnboardingVisiblePlaytestNextStepValidation(
            next_path=next_path,
            status="fail",
            checks=(
                _build_check(
                    area="Source Report",
                    passed=False,
                    summary="The source visible QA report must be readable.",
                    evidence=(str(error),),
                ),
            ),
        )
    if not next_path.exists():
        return OnboardingVisiblePlaytestNextStepValidation(
            next_path=next_path,
            status="fail",
            checks=(
                _build_check(
                    area="Next Step File",
                    passed=False,
                    summary="The onboarding visible next-step handoff file must exist.",
                    evidence=(f"missing:{next_path}",),
                ),
            ),
        )

    text = next_path.read_text(encoding="utf-8")
    metadata_markers = (
        "# NEXUS TECH Onboarding Visible Next Step",
        f"- Report: `{expected.report_path}`",
        f"- Status: `{expected.status}`",
        f"- Rows: `{expected.total_rows}`",
        f"- Pass: `{expected.pass_count}`",
        f"- Watch: `{expected.watch_count}`",
        f"- Fail: `{expected.fail_count}`",
        f"- Todo: `{expected.todo_count}`",
        f"- Incomplete: `{expected.incomplete_count}`",
        "- Evidence policy: `real visible-window observations required`",
    )
    if expected.next_row is None:
        action_markers = (
            "All visible onboarding rows are recorded as `pass` with concrete notes.",
            "Run validation before treating the onboarding visible gate as closed.",
            expected.validate_command,
            expected.status_command,
        )
        checklist_markers: tuple[str, ...] = ()
    else:
        row = expected.next_row
        action_markers = (
            "| Rank | Route | Window | Motion | Result |",
            (
                f"| {row.rank} | `{row.route}` | `{row.window}` | "
                f"`{row.motion_mode}` | `{row.result}` |"
            ),
            "## Copy Commands",
            "### 1. Open The Visible Route",
            expected.next_visible_command,
            "### 2. Record The Observation After Playing",
            expected.next_recorder_command,
            "### 3. Validate And Refresh Status",
            expected.validate_command,
            expected.status_command,
        )
        checklist_markers = (
            *row.required_evidence,
            "Text stays inside its panel and remains readable.",
            "Pause/back/menu recovery affordance is visible where the route needs it.",
            "Notes mention the route, window/motion mode, and observed UI behavior.",
        )
    checks = (
        _build_presence_check(
            area="Next Step Metadata",
            text=text,
            markers=metadata_markers,
            summary="The next-step handoff metadata matches the current report.",
        ),
        _build_presence_check(
            area="Next Action",
            text=text,
            markers=action_markers,
            summary="The next-step handoff points to the current next visible route.",
        ),
        _build_presence_check(
            area="Evidence Checklist",
            text=text,
            markers=checklist_markers,
            summary="The next-step evidence checklist matches the current route.",
        ),
        _build_presence_check(
            area="Result Rules",
            text=text,
            markers=(
                "- `pass`: readable, navigable, and the next command/recovery path is clear.",
                "- `watch`: playable, but has a concrete UI, copy, contrast, or motion concern.",
                "- `fail`: route blocks navigation, readability, or first-turn understanding.",
            ),
            summary="The next-step handoff keeps manual result rules visible.",
        ),
    )
    return OnboardingVisiblePlaytestNextStepValidation(
        next_path=next_path,
        status="pass" if all(check.status == "pass" for check in checks) else "fail",
        checks=checks,
    )


def build_onboarding_visible_terminal_batch(
    report_path: Path,
    *,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleTerminalBatch:
    """Build a focused terminal-route batch from the current visible QA report."""

    report = read_onboarding_visible_playtest_evidence_report(report_path)
    terminal_rows = tuple(row for row in report.rows if row.window == "terminal")
    incomplete_terminal_rows = tuple(
        row
        for row in terminal_rows
        if row.result != "pass" or not _has_real_observation_notes(row.evidence_notes)
    )
    recorder_commands = tuple(
        _build_onboarding_visible_recorder_command(
            report_path,
            row,
            command_prefix=command_prefix,
        )
        for row in terminal_rows
    )
    return OnboardingVisibleTerminalBatch(
        report_path=report_path,
        status=report.status,
        total_rows=len(report.rows),
        terminal_rows=terminal_rows,
        incomplete_terminal_rows=incomplete_terminal_rows,
        recorder_commands=recorder_commands,
        validate_command=(
            f"{command_prefix} validate-onboarding-visible-playtest-report --report {report_path}"
        ),
        status_command=(
            f"{command_prefix} onboarding-visible-playtest-status --report {report_path}"
        ),
        next_step_command=(
            f"{command_prefix} onboarding-visible-playtest-next --report {report_path}"
        ),
    )


def write_onboarding_visible_terminal_batch(
    batch: OnboardingVisibleTerminalBatch,
    output_path: Path,
) -> None:
    """Write a focused Markdown handoff for terminal onboarding visible QA."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NEXUS TECH Onboarding Visible Terminal Batch",
        "",
        f"- Report: `{batch.report_path}`",
        f"- Status: `{batch.status}`",
        f"- Rows: `{batch.total_rows}`",
        f"- Terminal rows: `{len(batch.terminal_rows)}`",
        f"- Incomplete terminal rows: `{len(batch.incomplete_terminal_rows)}`",
        "- Evidence policy: `real visible-window observations required`",
        "",
        (
            "This focused batch closes the terminal onboarding routes before the 2D "
            "window and motion matrix begins."
        ),
        "",
        "| Rank | Route | Result | Command | Required Evidence |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for row in batch.terminal_rows:
        lines.append(
            "| "
            f"{row.rank} | "
            f"`{row.route}` | "
            f"`{row.result}` | "
            f"`{_markdown_escape(row.command)}` | "
            f"{_markdown_escape(', '.join(row.required_evidence))} |"
        )
    lines.extend(
        [
            "",
            "## Copy Commands",
            "",
        ]
    )
    for row, recorder_command in zip(batch.terminal_rows, batch.recorder_commands, strict=True):
        lines.extend(
            [
                f"### Rank {row.rank}: {row.route}",
                "",
                "Open the route:",
                "",
                "```bash",
                row.command,
                "```",
                "",
                "Record the observation after playing:",
                "",
                "```bash",
                recorder_command,
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Batch Closure",
            "",
            "Run these after recording terminal-route observations:",
            "",
            "```bash",
            batch.validate_command,
            batch.status_command,
            batch.next_step_command,
            "```",
            "",
            "## Evidence Checklist",
            "",
            "- Terminal guide exposes the opening flow, Risk Forecast, and difficulty cues.",
            "- Tutorial names safe first actions, Turn Summary, and Watch For fields.",
            "- Automated clarity gate refreshes Guided Opening, Turn Coach, and Risk Forecast.",
            "- Notes mention the route, exact terminal output observed, and any unclear copy.",
            "- Keep `manual-required` until every terminal row has concrete observed notes.",
            "",
            "## Result Rules",
            "",
            "- `pass`: readable, navigable, and the next command/recovery path is clear.",
            "- `watch`: playable, but has a concrete UI, copy, contrast, or motion concern.",
            "- `fail`: route blocks navigation, readability, or first-turn understanding.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_onboarding_visible_terminal_batch(
    batch_path: Path,
    *,
    report_path: Path,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleTerminalBatchValidation:
    """Validate that a terminal batch handoff matches the current report."""

    try:
        expected = build_onboarding_visible_terminal_batch(
            report_path,
            command_prefix=command_prefix,
        )
    except (OSError, ValueError) as error:
        return OnboardingVisibleTerminalBatchValidation(
            batch_path=batch_path,
            status="fail",
            checks=(
                _build_check(
                    area="Source Report",
                    passed=False,
                    summary="The source visible QA report must be readable.",
                    evidence=(str(error),),
                ),
            ),
        )
    if not batch_path.exists():
        return OnboardingVisibleTerminalBatchValidation(
            batch_path=batch_path,
            status="fail",
            checks=(
                _build_check(
                    area="Terminal Batch File",
                    passed=False,
                    summary="The terminal onboarding batch handoff file must exist.",
                    evidence=(f"missing:{batch_path}",),
                ),
            ),
        )

    text = batch_path.read_text(encoding="utf-8")
    metadata_markers = (
        "# NEXUS TECH Onboarding Visible Terminal Batch",
        f"- Report: `{expected.report_path}`",
        f"- Status: `{expected.status}`",
        f"- Rows: `{expected.total_rows}`",
        f"- Terminal rows: `{len(expected.terminal_rows)}`",
        f"- Incomplete terminal rows: `{len(expected.incomplete_terminal_rows)}`",
        "- Evidence policy: `real visible-window observations required`",
    )
    route_markers = tuple(
        marker
        for row in expected.terminal_rows
        for marker in (
            f"| {row.rank} | `{row.route}` | `{row.result}` |",
            row.command,
            *row.required_evidence,
        )
    )
    command_markers = tuple(
        marker
        for row, recorder_command in zip(
            expected.terminal_rows,
            expected.recorder_commands,
            strict=True,
        )
        for marker in (
            f"### Rank {row.rank}: {row.route}",
            row.command,
            recorder_command,
        )
    )
    closure_markers = (
        expected.validate_command,
        expected.status_command,
        expected.next_step_command,
    )
    checks = (
        _build_presence_check(
            area="Terminal Batch Metadata",
            text=text,
            markers=metadata_markers,
            summary="The terminal batch metadata matches the current visible QA report.",
        ),
        _build_presence_check(
            area="Terminal Route Rows",
            text=text,
            markers=route_markers,
            summary="The terminal batch includes the current terminal onboarding routes.",
        ),
        _build_presence_check(
            area="Copy Commands",
            text=text,
            markers=command_markers,
            summary="The terminal batch has current open and recorder commands.",
        ),
        _build_presence_check(
            area="Batch Closure",
            text=text,
            markers=closure_markers,
            summary="The terminal batch points back to report validation and next-step refresh.",
        ),
        _build_presence_check(
            area="Manual Guardrails",
            text=text,
            markers=(
                "real visible-window observations required",
                "Keep `manual-required` until every terminal row has concrete observed notes.",
                "- `pass`: readable, navigable, and the next command/recovery path is clear.",
                "- `watch`: playable, but has a concrete UI, copy, contrast, or motion concern.",
                "- `fail`: route blocks navigation, readability, or first-turn understanding.",
            ),
            summary="The terminal batch keeps manual evidence rules visible.",
        ),
    )
    return OnboardingVisibleTerminalBatchValidation(
        batch_path=batch_path,
        status="pass" if all(check.status == "pass" for check in checks) else "fail",
        checks=checks,
    )


def build_onboarding_visible_terminal_evidence_sheet(
    report_path: Path,
    *,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleTerminalEvidenceSheet:
    """Build a terminal-route evidence worksheet from the current visible QA report."""

    batch = build_onboarding_visible_terminal_batch(
        report_path,
        command_prefix=command_prefix,
    )
    return OnboardingVisibleTerminalEvidenceSheet(
        report_path=batch.report_path,
        status=batch.status,
        terminal_rows=batch.terminal_rows,
        incomplete_terminal_rows=batch.incomplete_terminal_rows,
        recorder_commands=batch.recorder_commands,
        validate_command=batch.validate_command,
        status_command=batch.status_command,
        batch_command=(
            f"{command_prefix} onboarding-visible-terminal-batch --report {report_path}"
        ),
    )


def write_onboarding_visible_terminal_evidence_sheet(
    sheet: OnboardingVisibleTerminalEvidenceSheet,
    output_path: Path,
) -> None:
    """Write a terminal onboarding evidence worksheet for human QA."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NEXUS TECH Onboarding Visible Terminal Evidence Sheet",
        "",
        f"- Report: `{sheet.report_path}`",
        f"- Status: `{sheet.status}`",
        f"- Terminal rows: `{len(sheet.terminal_rows)}`",
        f"- Incomplete terminal rows: `{len(sheet.incomplete_terminal_rows)}`",
        "- Evidence policy: `observe route output before recording`",
        "- Recorder safety: `replace placeholder notes with real observed terminal output`",
        "",
        (
            "Use this worksheet while closing the first three terminal onboarding rows. "
            "It does not mark a row complete by itself."
        ),
        "",
        "| Rank | Route | Result | Open Command | Observation Prompt | Recorder Command |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for row, recorder_command in zip(sheet.terminal_rows, sheet.recorder_commands, strict=True):
        lines.append(
            "| "
            f"{row.rank} | "
            f"`{row.route}` | "
            f"`{row.result}` | "
            f"`{_markdown_escape(row.command)}` | "
            f"{_markdown_escape(_build_terminal_observation_prompt(row))} | "
            f"`{_markdown_escape(recorder_command)}` |"
        )
    lines.extend(
        [
            "",
            "## Operator Loop",
            "",
        ]
    )
    for row, recorder_command in zip(sheet.terminal_rows, sheet.recorder_commands, strict=True):
        lines.extend(
            [
                f"### Rank {row.rank}: {row.route}",
                "",
                "1. Run the terminal route:",
                "",
                "```bash",
                row.command,
                "```",
                "",
                "2. Check these visible terms in the output:",
                "",
                *(f"- {item}" for item in row.required_evidence),
                "",
                "3. Record only after replacing the placeholder with observed output notes:",
                "",
                "```bash",
                recorder_command,
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Closure Commands",
            "",
            "Run these after all terminal rows have real observations:",
            "",
            "```bash",
            sheet.validate_command,
            sheet.status_command,
            sheet.batch_command,
            "```",
            "",
            "## Evidence Rules",
            "",
            "- `pass`: output is readable and explains the first-time onboarding cue clearly.",
            "- `watch`: output is usable but copy, ordering, or wording slows understanding.",
            "- `fail`: output omits a required cue or leaves the next player action unclear.",
            "- Keep `manual-required` until the report rows contain observed terminal notes.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_onboarding_visible_terminal_evidence_sheet(
    sheet_path: Path,
    *,
    report_path: Path,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleTerminalEvidenceSheetValidation:
    """Validate that a terminal evidence worksheet matches the current report."""

    try:
        expected = build_onboarding_visible_terminal_evidence_sheet(
            report_path,
            command_prefix=command_prefix,
        )
    except (OSError, ValueError) as error:
        return OnboardingVisibleTerminalEvidenceSheetValidation(
            sheet_path=sheet_path,
            status="fail",
            checks=(
                _build_check(
                    area="Source Report",
                    passed=False,
                    summary="The source visible QA report must be readable.",
                    evidence=(str(error),),
                ),
            ),
        )
    if not sheet_path.exists():
        return OnboardingVisibleTerminalEvidenceSheetValidation(
            sheet_path=sheet_path,
            status="fail",
            checks=(
                _build_check(
                    area="Terminal Evidence Sheet File",
                    passed=False,
                    summary="The terminal evidence worksheet file must exist.",
                    evidence=(f"missing:{sheet_path}",),
                ),
            ),
        )

    text = sheet_path.read_text(encoding="utf-8")
    metadata_markers = (
        "# NEXUS TECH Onboarding Visible Terminal Evidence Sheet",
        f"- Report: `{expected.report_path}`",
        f"- Status: `{expected.status}`",
        f"- Terminal rows: `{len(expected.terminal_rows)}`",
        f"- Incomplete terminal rows: `{len(expected.incomplete_terminal_rows)}`",
        "- Evidence policy: `observe route output before recording`",
        "- Recorder safety: `replace placeholder notes with real observed terminal output`",
    )
    row_markers = tuple(
        marker
        for row, recorder_command in zip(
            expected.terminal_rows,
            expected.recorder_commands,
            strict=True,
        )
        for marker in (
            f"| {row.rank} | `{row.route}` | `{row.result}` |",
            row.command,
            _build_terminal_observation_prompt(row),
            recorder_command,
        )
    )
    loop_markers = tuple(
        marker
        for row, recorder_command in zip(
            expected.terminal_rows,
            expected.recorder_commands,
            strict=True,
        )
        for marker in (
            f"### Rank {row.rank}: {row.route}",
            row.command,
            *row.required_evidence,
            recorder_command,
        )
    )
    closure_markers = (
        expected.validate_command,
        expected.status_command,
        expected.batch_command,
    )
    checks = (
        _build_presence_check(
            area="Terminal Evidence Metadata",
            text=text,
            markers=metadata_markers,
            summary="The terminal evidence worksheet metadata matches the report.",
        ),
        _build_presence_check(
            area="Terminal Evidence Rows",
            text=text,
            markers=row_markers,
            summary="The worksheet lists current terminal rows and recorder commands.",
        ),
        _build_presence_check(
            area="Operator Loop",
            text=text,
            markers=loop_markers,
            summary="Each terminal route has run, check, and record instructions.",
        ),
        _build_presence_check(
            area="Closure Commands",
            text=text,
            markers=closure_markers,
            summary="The worksheet points back to validation, status, and batch refresh.",
        ),
        _build_presence_check(
            area="Evidence Rules",
            text=text,
            markers=(
                "It does not mark a row complete by itself.",
                "Record only after replacing the placeholder with observed output notes:",
                "- `pass`: output is readable and explains the first-time onboarding cue clearly.",
                "- `watch`: output is usable but copy, ordering, or wording slows understanding.",
                "- `fail`: output omits a required cue or leaves the next player action unclear.",
                "Keep `manual-required` until the report rows contain observed terminal notes.",
            ),
            summary="The worksheet keeps manual evidence rules explicit.",
        ),
    )
    return OnboardingVisibleTerminalEvidenceSheetValidation(
        sheet_path=sheet_path,
        status="pass" if all(check.status == "pass" for check in checks) else "fail",
        checks=checks,
    )


def build_onboarding_visible_window_evidence_sheet(
    report_path: Path,
    *,
    window: str = "820x620",
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleWindowEvidenceSheet:
    """Build an evidence worksheet for one visible onboarding window."""

    report = read_onboarding_visible_playtest_evidence_report(report_path)
    window_rows = tuple(row for row in report.rows if row.window == window)
    if not window_rows:
        raise ValueError(f"No onboarding visible report rows found for window {window}.")
    incomplete_window_rows = tuple(
        row
        for row in window_rows
        if row.result != "pass" or not _has_real_observation_notes(row.evidence_notes)
    )
    recorder_commands = tuple(
        _build_onboarding_visible_recorder_command(
            report_path,
            row,
            command_prefix=command_prefix,
        )
        for row in window_rows
    )
    return OnboardingVisibleWindowEvidenceSheet(
        report_path=report_path,
        status=report.status,
        window=window,
        window_rows=window_rows,
        incomplete_window_rows=incomplete_window_rows,
        recorder_commands=recorder_commands,
        validate_command=(
            f"{command_prefix} validate-onboarding-visible-playtest-report --report {report_path}"
        ),
        status_command=(
            f"{command_prefix} onboarding-visible-playtest-status --report {report_path}"
        ),
        next_step_command=(
            f"{command_prefix} onboarding-visible-playtest-next --report {report_path}"
        ),
    )


def write_onboarding_visible_window_evidence_sheet(
    sheet: OnboardingVisibleWindowEvidenceSheet,
    output_path: Path,
) -> None:
    """Write a visible-window onboarding evidence worksheet for human QA."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NEXUS TECH Onboarding Visible Window Evidence Sheet",
        "",
        f"- Report: `{sheet.report_path}`",
        f"- Status: `{sheet.status}`",
        f"- Window: `{sheet.window}`",
        f"- Window rows: `{len(sheet.window_rows)}`",
        f"- Incomplete window rows: `{len(sheet.incomplete_window_rows)}`",
        "- Evidence policy: `observe the visible 2D window before recording`",
        "- Recorder safety: `replace placeholder notes with real observed UI behavior`",
        "",
        (
            "Use this worksheet to close the compact visible-window onboarding rows. "
            "It does not mark a row complete by itself."
        ),
        "",
        (
            "| Rank | Route | Motion | Result | Open Command | Observation Prompt | "
            "Recorder Command |"
        ),
        "| ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for row, recorder_command in zip(sheet.window_rows, sheet.recorder_commands, strict=True):
        lines.append(
            "| "
            f"{row.rank} | "
            f"`{row.route}` | "
            f"`{row.motion_mode}` | "
            f"`{row.result}` | "
            f"`{_markdown_escape(row.command)}` | "
            f"{_markdown_escape(_build_window_observation_prompt(row))} | "
            f"`{_markdown_escape(recorder_command)}` |"
        )
    lines.extend(
        [
            "",
            "## Operator Loop",
            "",
        ]
    )
    for row, recorder_command in zip(sheet.window_rows, sheet.recorder_commands, strict=True):
        lines.extend(
            [
                f"### Rank {row.rank}: {row.route} | {row.motion_mode}",
                "",
                "1. Run the visible 2D route:",
                "",
                "```bash",
                row.command,
                "```",
                "",
                "2. Observe the compact-window UX checks:",
                "",
                "- Text stays inside panels and remains readable at 820x620.",
                "- Buttons, footer controls, and action targets stay separated.",
                "- Pause/back/menu affordance is visible and recoverable.",
                "- Motion does not cover text, controls, or feedback states.",
                *(f"- Required evidence: {item}" for item in row.required_evidence),
                "",
                "3. Record only after replacing the placeholder with observed UI notes:",
                "",
                "```bash",
                recorder_command,
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Closure Commands",
            "",
            "Run these after all rows for this window have real observations:",
            "",
            "```bash",
            sheet.validate_command,
            sheet.status_command,
            sheet.next_step_command,
            "```",
            "",
            "## Evidence Rules",
            "",
            "- `pass`: layout is readable, navigable, and the next player action is clear.",
            "- `watch`: playable, but copy, contrast, motion, or placement slows understanding.",
            "- `fail`: layout blocks reading, navigation recovery, or first-turn understanding.",
            "- Keep `manual-required` until report rows contain observed visible-window notes.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_onboarding_visible_window_evidence_sheet(
    sheet_path: Path,
    *,
    report_path: Path,
    window: str = "820x620",
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleWindowEvidenceSheetValidation:
    """Validate a visible-window evidence worksheet against the current report."""

    try:
        expected = build_onboarding_visible_window_evidence_sheet(
            report_path,
            window=window,
            command_prefix=command_prefix,
        )
    except (OSError, ValueError) as error:
        return OnboardingVisibleWindowEvidenceSheetValidation(
            sheet_path=sheet_path,
            status="fail",
            checks=(
                _build_check(
                    area="Source Report",
                    passed=False,
                    summary="The source visible QA report must include the requested window.",
                    evidence=(str(error),),
                ),
            ),
        )
    if not sheet_path.exists():
        return OnboardingVisibleWindowEvidenceSheetValidation(
            sheet_path=sheet_path,
            status="fail",
            checks=(
                _build_check(
                    area="Window Evidence Sheet File",
                    passed=False,
                    summary="The visible-window evidence worksheet file must exist.",
                    evidence=(f"missing:{sheet_path}",),
                ),
            ),
        )

    text = sheet_path.read_text(encoding="utf-8")
    metadata_markers = (
        "# NEXUS TECH Onboarding Visible Window Evidence Sheet",
        f"- Report: `{expected.report_path}`",
        f"- Status: `{expected.status}`",
        f"- Window: `{expected.window}`",
        f"- Window rows: `{len(expected.window_rows)}`",
        f"- Incomplete window rows: `{len(expected.incomplete_window_rows)}`",
        "- Evidence policy: `observe the visible 2D window before recording`",
        "- Recorder safety: `replace placeholder notes with real observed UI behavior`",
    )
    row_markers = tuple(
        marker
        for row, recorder_command in zip(
            expected.window_rows,
            expected.recorder_commands,
            strict=True,
        )
        for marker in (
            f"| {row.rank} | `{row.route}` | `{row.motion_mode}` | `{row.result}` |",
            row.command,
            _build_window_observation_prompt(row),
            recorder_command,
        )
    )
    loop_markers = tuple(
        marker
        for row, recorder_command in zip(
            expected.window_rows,
            expected.recorder_commands,
            strict=True,
        )
        for marker in (
            f"### Rank {row.rank}: {row.route} | {row.motion_mode}",
            row.command,
            *row.required_evidence,
            recorder_command,
        )
    )
    closure_markers = (
        expected.validate_command,
        expected.status_command,
        expected.next_step_command,
    )
    checks = (
        _build_presence_check(
            area="Window Evidence Metadata",
            text=text,
            markers=metadata_markers,
            summary="The window evidence worksheet metadata matches the report.",
        ),
        _build_presence_check(
            area="Window Evidence Rows",
            text=text,
            markers=row_markers,
            summary="The worksheet lists current window rows and recorder commands.",
        ),
        _build_presence_check(
            area="Operator Loop",
            text=text,
            markers=loop_markers,
            summary="Each visible route has run, UX check, and record instructions.",
        ),
        _build_presence_check(
            area="Closure Commands",
            text=text,
            markers=closure_markers,
            summary="The worksheet points back to report validation and status refresh.",
        ),
        _build_presence_check(
            area="Evidence Rules",
            text=text,
            markers=(
                "It does not mark a row complete by itself.",
                "Text stays inside panels and remains readable at 820x620.",
                "Pause/back/menu affordance is visible and recoverable.",
                "Motion does not cover text, controls, or feedback states.",
                "- `pass`: layout is readable, navigable, and the next player action is clear.",
                (
                    "- `watch`: playable, but copy, contrast, motion, or placement slows "
                    "understanding."
                ),
                (
                    "- `fail`: layout blocks reading, navigation recovery, or first-turn "
                    "understanding."
                ),
                "Keep `manual-required` until report rows contain observed visible-window notes.",
            ),
            summary="The worksheet keeps compact-window manual evidence rules explicit.",
        ),
    )
    return OnboardingVisibleWindowEvidenceSheetValidation(
        sheet_path=sheet_path,
        status="pass" if all(check.status == "pass" for check in checks) else "fail",
        checks=checks,
    )


def build_onboarding_visible_evidence_matrix(
    report_path: Path,
    *,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleEvidenceMatrix:
    """Build a cross-window evidence closeout matrix from the visible QA report."""

    report = read_onboarding_visible_playtest_evidence_report(report_path)
    rows = report.rows
    group_names = _ordered_onboarding_visible_group_names(rows)
    groups = tuple(
        _build_onboarding_visible_evidence_matrix_group(
            report_path,
            name=name,
            rows=tuple(row for row in rows if _onboarding_visible_group_name(row) == name),
            command_prefix=command_prefix,
        )
        for name in group_names
    )
    next_row = report.incomplete_rows[0] if report.incomplete_rows else None
    next_recorder_command = (
        _build_onboarding_visible_recorder_command(
            report_path,
            next_row,
            command_prefix=command_prefix,
        )
        if next_row is not None
        else ""
    )
    return OnboardingVisibleEvidenceMatrix(
        report_path=report_path,
        status=report.status,
        total_rows=len(rows),
        pass_count=sum(1 for row in rows if row.result == "pass"),
        watch_count=sum(1 for row in rows if row.result == "watch"),
        fail_count=sum(1 for row in rows if row.result == "fail"),
        todo_count=sum(1 for row in rows if row.result == "todo"),
        incomplete_count=len(report.incomplete_rows),
        groups=groups,
        next_row=next_row,
        next_visible_command=next_row.command if next_row is not None else "",
        next_recorder_command=next_recorder_command,
        validate_command=(
            f"{command_prefix} validate-onboarding-visible-playtest-report --report {report_path}"
        ),
        status_command=(
            f"{command_prefix} onboarding-visible-playtest-status --report {report_path}"
        ),
        next_step_command=(
            f"{command_prefix} onboarding-visible-playtest-next --report {report_path}"
        ),
    )


def write_onboarding_visible_evidence_matrix(
    matrix: OnboardingVisibleEvidenceMatrix,
    output_path: Path,
) -> None:
    """Write a cross-window onboarding evidence closeout matrix."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NEXUS TECH Onboarding Visible Evidence Matrix",
        "",
        f"- Report: `{matrix.report_path}`",
        f"- Status: `{matrix.status}`",
        f"- Rows: `{matrix.total_rows}`",
        f"- Pass: `{matrix.pass_count}`",
        f"- Watch: `{matrix.watch_count}`",
        f"- Fail: `{matrix.fail_count}`",
        f"- Todo: `{matrix.todo_count}`",
        f"- Incomplete: `{matrix.incomplete_count}`",
        f"- Groups: `{len(matrix.groups)}`",
        "- Evidence policy: `real visible-window observations required`",
        "- Recorder safety: `matrix does not replace observed terminal or 2D window notes`",
        "",
        (
            "Use this matrix as the final preflight before manual onboarding QA. "
            "It summarizes terminal rows and every visible window worksheet in one place."
        ),
        "",
        "## Group Summary",
        "",
        "| Group | Rows | Pass | Watch | Fail | Todo | Incomplete |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for group in matrix.groups:
        lines.append(
            "| "
            f"`{group.name}` | "
            f"{len(group.rows)} | "
            f"{group.pass_count} | "
            f"{group.watch_count} | "
            f"{group.fail_count} | "
            f"{group.todo_count} | "
            f"{group.incomplete_count} |"
        )
    lines.extend(["", "## Matrix Rows", ""])
    for group in matrix.groups:
        lines.extend(
            [
                f"### {group.name}",
                "",
                "| Rank | Route | Window | Motion | Result | Open Command | Recorder Command |",
                "| ---: | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row, recorder_command in zip(group.rows, group.recorder_commands, strict=True):
            lines.append(
                "| "
                f"{row.rank} | "
                f"`{row.route}` | "
                f"`{row.window}` | "
                f"`{row.motion_mode}` | "
                f"`{row.result}` | "
                f"`{_markdown_escape(row.command)}` | "
                f"`{_markdown_escape(recorder_command)}` |"
            )
        lines.append("")
    lines.extend(["## Next Action", ""])
    if matrix.next_row is None:
        lines.extend(
            [
                "All onboarding visible groups are recorded as `pass` with concrete notes.",
                "Run closure validation before treating the onboarding visible gate as closed.",
                "",
                "```bash",
                matrix.validate_command,
                matrix.status_command,
                "```",
                "",
            ]
        )
    else:
        row = matrix.next_row
        lines.extend(
            [
                "| Rank | Route | Window | Motion | Result |",
                "| ---: | --- | --- | --- | --- |",
                (
                    f"| {row.rank} | `{row.route}` | `{row.window}` | "
                    f"`{row.motion_mode}` | `{row.result}` |"
                ),
                "",
                "Open the current incomplete route:",
                "",
                "```bash",
                matrix.next_visible_command,
                "```",
                "",
                (
                    "Record only after replacing placeholder notes with observed output "
                    "or UI behavior:"
                ),
                "",
                "```bash",
                matrix.next_recorder_command,
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Closure Commands",
            "",
            "Run these after terminal and all window groups have real observations:",
            "",
            "```bash",
            matrix.validate_command,
            matrix.status_command,
            matrix.next_step_command,
            "```",
            "",
            "## Evidence Rules",
            "",
            "- `pass`: readable, navigable, and the next command/recovery path is clear.",
            "- `watch`: playable, but has a concrete UI, copy, contrast, or motion concern.",
            "- `fail`: route blocks navigation, readability, or first-turn understanding.",
            "- Keep `manual-required` until every group contains concrete observed notes.",
            "- The matrix is a closeout index; it does not fabricate manual observations.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_onboarding_visible_evidence_matrix(
    matrix_path: Path,
    *,
    report_path: Path,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleEvidenceMatrixValidation:
    """Validate that the evidence matrix matches the current visible QA report."""

    try:
        expected = build_onboarding_visible_evidence_matrix(
            report_path,
            command_prefix=command_prefix,
        )
    except (OSError, ValueError) as error:
        return OnboardingVisibleEvidenceMatrixValidation(
            matrix_path=matrix_path,
            status="fail",
            checks=(
                _build_check(
                    area="Source Report",
                    passed=False,
                    summary="The source visible QA report must be readable.",
                    evidence=(str(error),),
                ),
            ),
        )
    if not matrix_path.exists():
        return OnboardingVisibleEvidenceMatrixValidation(
            matrix_path=matrix_path,
            status="fail",
            checks=(
                _build_check(
                    area="Evidence Matrix File",
                    passed=False,
                    summary="The onboarding visible evidence matrix file must exist.",
                    evidence=(f"missing:{matrix_path}",),
                ),
            ),
        )

    text = matrix_path.read_text(encoding="utf-8")
    metadata_markers = (
        "# NEXUS TECH Onboarding Visible Evidence Matrix",
        f"- Report: `{expected.report_path}`",
        f"- Status: `{expected.status}`",
        f"- Rows: `{expected.total_rows}`",
        f"- Pass: `{expected.pass_count}`",
        f"- Watch: `{expected.watch_count}`",
        f"- Fail: `{expected.fail_count}`",
        f"- Todo: `{expected.todo_count}`",
        f"- Incomplete: `{expected.incomplete_count}`",
        f"- Groups: `{len(expected.groups)}`",
        "- Evidence policy: `real visible-window observations required`",
        "- Recorder safety: `matrix does not replace observed terminal or 2D window notes`",
    )
    group_markers = tuple(
        "| "
        f"`{group.name}` | "
        f"{len(group.rows)} | "
        f"{group.pass_count} | "
        f"{group.watch_count} | "
        f"{group.fail_count} | "
        f"{group.todo_count} | "
        f"{group.incomplete_count} |"
        for group in expected.groups
    )
    row_markers = tuple(
        marker
        for group in expected.groups
        for row, recorder_command in zip(group.rows, group.recorder_commands, strict=True)
        for marker in (
            f"### {group.name}",
            (
                f"| {row.rank} | `{row.route}` | `{row.window}` | "
                f"`{row.motion_mode}` | `{row.result}` |"
            ),
            row.command,
            recorder_command,
        )
    )
    if expected.next_row is None:
        next_markers = (
            "All onboarding visible groups are recorded as `pass` with concrete notes.",
            "Run closure validation before treating the onboarding visible gate as closed.",
            expected.validate_command,
            expected.status_command,
        )
    else:
        row = expected.next_row
        next_markers = (
            "| Rank | Route | Window | Motion | Result |",
            (
                f"| {row.rank} | `{row.route}` | `{row.window}` | "
                f"`{row.motion_mode}` | `{row.result}` |"
            ),
            "Open the current incomplete route:",
            expected.next_visible_command,
            "Record only after replacing placeholder notes with observed output or UI behavior:",
            expected.next_recorder_command,
        )
    closure_markers = (
        expected.validate_command,
        expected.status_command,
        expected.next_step_command,
    )
    checks = (
        _build_presence_check(
            area="Evidence Matrix Metadata",
            text=text,
            markers=metadata_markers,
            summary="The evidence matrix metadata matches the current visible QA report.",
        ),
        _build_presence_check(
            area="Group Summary",
            text=text,
            markers=group_markers,
            summary="The matrix summarizes all terminal and visible-window groups.",
        ),
        _build_presence_check(
            area="Matrix Rows",
            text=text,
            markers=row_markers,
            summary="The matrix lists current open and recorder commands for every row.",
        ),
        _build_presence_check(
            area="Next Action",
            text=text,
            markers=next_markers,
            summary="The matrix points to the current next incomplete evidence row.",
        ),
        _build_presence_check(
            area="Closure Commands",
            text=text,
            markers=closure_markers,
            summary="The matrix points back to report validation, status, and next-step refresh.",
        ),
        _build_presence_check(
            area="Manual Guardrails",
            text=text,
            markers=(
                "- `pass`: readable, navigable, and the next command/recovery path is clear.",
                "- `watch`: playable, but has a concrete UI, copy, contrast, or motion concern.",
                "- `fail`: route blocks navigation, readability, or first-turn understanding.",
                "Keep `manual-required` until every group contains concrete observed notes.",
                "The matrix is a closeout index; it does not fabricate manual observations.",
            ),
            summary="The matrix keeps manual evidence rules and no-fabrication guardrails visible.",
        ),
    )
    return OnboardingVisibleEvidenceMatrixValidation(
        matrix_path=matrix_path,
        status="pass" if all(check.status == "pass" for check in checks) else "fail",
        checks=checks,
    )


def build_onboarding_visible_manual_session(
    report_path: Path,
    *,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleManualSession:
    """Build an operator packet for the real onboarding visible manual QA pass."""

    matrix = build_onboarding_visible_evidence_matrix(
        report_path,
        command_prefix=command_prefix,
    )
    window_groups = tuple(group for group in matrix.groups if group.name != "terminal")
    prerequisite_commands = (
        f"{command_prefix} validate-onboarding-visible-playtest-report --report {report_path}",
        f"{command_prefix} onboarding-visible-playtest-status --report {report_path}",
        (
            f"{command_prefix} onboarding-visible-evidence-matrix --report {report_path} "
            "--output /tmp/nexus-tech-onboarding-visible-evidence-matrix.md"
        ),
        (
            f"{command_prefix} validate-onboarding-visible-evidence-matrix "
            f"--report {report_path} "
            "--input /tmp/nexus-tech-onboarding-visible-evidence-matrix.md"
        ),
        (
            f"{command_prefix} onboarding-visible-window-preflight --frames 1 "
            "--output /tmp/nexus-tech-onboarding-visible-window-preflight.md"
        ),
    )
    worksheet_commands = (
        (
            f"{command_prefix} onboarding-visible-terminal-evidence-sheet "
            f"--report {report_path} "
            "--output /tmp/nexus-tech-onboarding-visible-terminal-evidence-sheet.md"
        ),
        (
            f"{command_prefix} validate-onboarding-visible-terminal-evidence-sheet "
            f"--report {report_path} "
            "--input /tmp/nexus-tech-onboarding-visible-terminal-evidence-sheet.md"
        ),
        *tuple(
            command
            for group in window_groups
            for command in (
                (
                    f"{command_prefix} onboarding-visible-window-evidence-sheet "
                    f"--report {report_path} --window {group.name} "
                    f"--output /tmp/nexus-tech-onboarding-visible-{group.name}-evidence-sheet.md"
                ),
                (
                    f"{command_prefix} validate-onboarding-visible-window-evidence-sheet "
                    f"--report {report_path} --window {group.name} "
                    f"--input /tmp/nexus-tech-onboarding-visible-{group.name}-evidence-sheet.md"
                ),
            )
        ),
    )
    closure_commands = (
        f"{command_prefix} validate-onboarding-visible-playtest-report --report {report_path}",
        f"{command_prefix} onboarding-visible-playtest-status --report {report_path}",
        f"{command_prefix} onboarding-visible-playtest-next --report {report_path}",
        (
            f"{command_prefix} validate-onboarding-visible-evidence-matrix "
            f"--report {report_path} "
            "--input /tmp/nexus-tech-onboarding-visible-evidence-matrix.md"
        ),
    )
    return OnboardingVisibleManualSession(
        report_path=matrix.report_path,
        status=matrix.status,
        total_rows=matrix.total_rows,
        incomplete_count=matrix.incomplete_count,
        groups=matrix.groups,
        prerequisite_commands=prerequisite_commands,
        worksheet_commands=worksheet_commands,
        closure_commands=closure_commands,
    )


def write_onboarding_visible_manual_session(
    session: OnboardingVisibleManualSession,
    output_path: Path,
) -> None:
    """Write a real-window onboarding manual QA operator packet."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NEXUS TECH Onboarding Visible Manual Session",
        "",
        f"- Report: `{session.report_path}`",
        f"- Status: `{session.status}`",
        f"- Rows: `{session.total_rows}`",
        f"- Incomplete: `{session.incomplete_count}`",
        f"- Groups: `{len(session.groups)}`",
        "- Manual result: `not completed by automation`",
        "- Evidence policy: `real visible-window observations required`",
        "- Recorder safety: `replace placeholder notes only after playing the visible route`",
        "",
        (
            "Use this packet as the ordered operator checklist for the real onboarding "
            "visible QA pass. Automation can prepare it, but only observed notes close rows."
        ),
        "",
        "## Preflight Refresh",
        "",
        "Run these before recording manual evidence:",
        "",
        "```bash",
        *session.prerequisite_commands,
        "```",
        "",
        "## Worksheet Refresh",
        "",
        "Regenerate worksheets before opening the real windows:",
        "",
        "```bash",
        *session.worksheet_commands,
        "```",
        "",
        "## Operator Order",
        "",
        "| Group | Rank | Route | Window | Motion | Result | Open Command | Recorder Command |",
        "| --- | ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for group in session.groups:
        for row, recorder_command in zip(group.rows, group.recorder_commands, strict=True):
            lines.append(
                "| "
                f"`{group.name}` | "
                f"{row.rank} | "
                f"`{row.route}` | "
                f"`{row.window}` | "
                f"`{row.motion_mode}` | "
                f"`{row.result}` | "
                f"`{_markdown_escape(row.command)}` | "
                f"`{_markdown_escape(recorder_command)}` |"
            )
    lines.extend(
        [
            "",
            "## Recording Rules",
            "",
            "- Open the visible route first; never record from source-code assumptions.",
            "- Notes must mention window size, motion mode, readability, controls, and blockers.",
            "- Use `watch` for concrete UX concerns and `fail` for blocked navigation/readability.",
            "- Keep `manual-required` until every pass/watch/fail row has observed notes.",
            "",
            "## Closure Commands",
            "",
            "Run these after each manual recording batch:",
            "",
            "```bash",
            *session.closure_commands,
            "```",
            "",
            "## No-Fabrication Guardrail",
            "",
            "- This session packet is a checklist, not evidence.",
            "- Headless preflight confirms launch health only; it does not prove UI readability.",
            "- Do not mark onboarding complete until real visible-window observations validate.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_onboarding_visible_manual_session(
    session_path: Path,
    *,
    report_path: Path,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleManualSessionValidation:
    """Validate that the manual session packet matches the current report."""

    try:
        expected = build_onboarding_visible_manual_session(
            report_path,
            command_prefix=command_prefix,
        )
    except (OSError, ValueError) as error:
        return OnboardingVisibleManualSessionValidation(
            session_path=session_path,
            status="fail",
            checks=(
                _build_check(
                    area="Source Report",
                    passed=False,
                    summary="The source visible QA report must be readable.",
                    evidence=(str(error),),
                ),
            ),
        )
    if not session_path.exists():
        return OnboardingVisibleManualSessionValidation(
            session_path=session_path,
            status="fail",
            checks=(
                _build_check(
                    area="Manual Session File",
                    passed=False,
                    summary="The onboarding visible manual session file must exist.",
                    evidence=(f"missing:{session_path}",),
                ),
            ),
        )

    text = session_path.read_text(encoding="utf-8")
    metadata_markers = (
        "# NEXUS TECH Onboarding Visible Manual Session",
        f"- Report: `{expected.report_path}`",
        f"- Status: `{expected.status}`",
        f"- Rows: `{expected.total_rows}`",
        f"- Incomplete: `{expected.incomplete_count}`",
        f"- Groups: `{len(expected.groups)}`",
        "- Manual result: `not completed by automation`",
        "- Evidence policy: `real visible-window observations required`",
        "- Recorder safety: `replace placeholder notes only after playing the visible route`",
    )
    command_markers = (
        *expected.prerequisite_commands,
        *expected.worksheet_commands,
        *expected.closure_commands,
    )
    row_markers = tuple(
        marker
        for group in expected.groups
        for row, recorder_command in zip(group.rows, group.recorder_commands, strict=True)
        for marker in (
            (
                f"| `{group.name}` | {row.rank} | `{row.route}` | "
                f"`{row.window}` | `{row.motion_mode}` | `{row.result}` |"
            ),
            row.command,
            recorder_command,
        )
    )
    checks = (
        _build_presence_check(
            area="Manual Session Metadata",
            text=text,
            markers=metadata_markers,
            summary="The manual session metadata matches the current visible QA report.",
        ),
        _build_presence_check(
            area="Refresh Commands",
            text=text,
            markers=command_markers,
            summary=(
                "The manual session includes current preflight, worksheet, and closure commands."
            ),
        ),
        _build_presence_check(
            area="Operator Order",
            text=text,
            markers=row_markers,
            summary="The manual session lists each current row with matching recorder command.",
        ),
        _build_presence_check(
            area="Manual Evidence Rules",
            text=text,
            markers=(
                "Open the visible route first; never record from source-code assumptions.",
                "Notes must mention window size, motion mode, readability, controls, and blockers.",
                "Keep `manual-required` until every pass/watch/fail row has observed notes.",
                "This session packet is a checklist, not evidence.",
                "Headless preflight confirms launch health only; it does not prove UI readability.",
                "Do not mark onboarding complete until real visible-window observations validate.",
            ),
            summary="The manual session keeps no-fabrication guardrails visible.",
        ),
    )
    return OnboardingVisibleManualSessionValidation(
        session_path=session_path,
        status="pass" if all(check.status == "pass" for check in checks) else "fail",
        checks=checks,
    )


def build_onboarding_visible_ux_issue_intake(
    report_path: Path,
    *,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleUxIssueIntake:
    """Build a UX issue intake sheet for real visible onboarding QA findings."""

    matrix = build_onboarding_visible_evidence_matrix(
        report_path,
        command_prefix=command_prefix,
    )
    return OnboardingVisibleUxIssueIntake(
        report_path=matrix.report_path,
        status=matrix.status,
        total_rows=matrix.total_rows,
        incomplete_count=matrix.incomplete_count,
        groups=matrix.groups,
        manual_session_command=(
            f"{command_prefix} onboarding-visible-manual-session "
            f"--report {report_path} "
            "--output /tmp/nexus-tech-onboarding-visible-manual-session.md"
        ),
        preflight_command=(
            f"{command_prefix} onboarding-visible-window-preflight --frames 1 "
            "--output /tmp/nexus-tech-onboarding-visible-window-preflight.md"
        ),
        validate_report_command=(
            f"{command_prefix} validate-onboarding-visible-playtest-report --report {report_path}"
        ),
        status_command=(
            f"{command_prefix} onboarding-visible-playtest-status --report {report_path}"
        ),
    )


def write_onboarding_visible_ux_issue_intake(
    intake: OnboardingVisibleUxIssueIntake,
    output_path: Path,
) -> None:
    """Write a UX issue intake sheet for manual visible-window observations."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NEXUS TECH Onboarding Visible UX Issue Intake",
        "",
        f"- Report: `{intake.report_path}`",
        f"- Status: `{intake.status}`",
        f"- Rows: `{intake.total_rows}`",
        f"- Incomplete: `{intake.incomplete_count}`",
        f"- Groups: `{len(intake.groups)}`",
        "- Manual result: `not completed by automation`",
        "- Evidence policy: `record only issues observed during real visible-window play`",
        "- Intake safety: `todo rows are issue slots, not proof of defects`",
        "",
        (
            "Use this intake after running the manual visible onboarding session. "
            "Record concrete UX/UI issues that were observed in the actual terminal "
            "or 2D window; leave rows as `todo` until a real observation exists."
        ),
        "",
        "## Required Refresh",
        "",
        "```bash",
        intake.manual_session_command,
        intake.preflight_command,
        intake.validate_report_command,
        intake.status_command,
        "```",
        "",
        "## Issue Intake Rows",
        "",
        (
            "| Group | Rank | Route | Window | Motion | Result | Open Command | "
            "UX Areas | Severity | Issue Notes | Follow-up |"
        ),
        "| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for group in intake.groups:
        for row in group.rows:
            lines.append(
                "| "
                f"`{group.name}` | "
                f"{row.rank} | "
                f"`{row.route}` | "
                f"`{row.window}` | "
                f"`{row.motion_mode}` | "
                f"`{row.result}` | "
                f"`{_markdown_escape(row.command)}` | "
                f"`{_onboarding_visible_ux_issue_areas(row)}` | "
                "`todo` | "
                "`<record observed UX issue or none>` | "
                "`owner/date or none` |"
            )
    lines.extend(
        [
            "",
            "## Severity Rules",
            "",
            (
                "- `P0`: blocks reading, navigation, save/load, pause/back/menu, "
                "or first-turn action."
            ),
            "- `P1`: playable but materially slows first-time understanding.",
            "- `P2`: polish issue that should not block manual evidence.",
            (
                "- `none`: no issue observed; still record evidence notes in the "
                "main report separately."
            ),
            "",
            "## Closure Commands",
            "",
            "```bash",
            intake.validate_report_command,
            intake.status_command,
            "```",
            "",
            "## No-Fabrication Guardrail",
            "",
            "- This intake is not evidence; it only captures observed UX issues.",
            "- Do not invent defects to make a row look tested.",
            (
                "- Keep onboarding manual-required until report rows contain real "
                "visible-window notes."
            ),
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_onboarding_visible_ux_issue_intake(
    intake_path: Path,
    *,
    report_path: Path,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleUxIssueIntakeValidation:
    """Validate that the UX issue intake matches the current visible QA report."""

    try:
        expected = build_onboarding_visible_ux_issue_intake(
            report_path,
            command_prefix=command_prefix,
        )
    except (OSError, ValueError) as error:
        return OnboardingVisibleUxIssueIntakeValidation(
            intake_path=intake_path,
            status="fail",
            checks=(
                _build_check(
                    area="Source Report",
                    passed=False,
                    summary="The source visible QA report must be readable.",
                    evidence=(str(error),),
                ),
            ),
        )
    if not intake_path.exists():
        return OnboardingVisibleUxIssueIntakeValidation(
            intake_path=intake_path,
            status="fail",
            checks=(
                _build_check(
                    area="UX Issue Intake File",
                    passed=False,
                    summary="The onboarding visible UX issue intake file must exist.",
                    evidence=(f"missing:{intake_path}",),
                ),
            ),
        )

    text = intake_path.read_text(encoding="utf-8")
    metadata_markers = (
        "# NEXUS TECH Onboarding Visible UX Issue Intake",
        f"- Report: `{expected.report_path}`",
        f"- Status: `{expected.status}`",
        f"- Rows: `{expected.total_rows}`",
        f"- Incomplete: `{expected.incomplete_count}`",
        f"- Groups: `{len(expected.groups)}`",
        "- Manual result: `not completed by automation`",
        "- Evidence policy: `record only issues observed during real visible-window play`",
        "- Intake safety: `todo rows are issue slots, not proof of defects`",
    )
    command_markers = (
        expected.manual_session_command,
        expected.preflight_command,
        expected.validate_report_command,
        expected.status_command,
    )
    row_markers = tuple(
        marker
        for group in expected.groups
        for row in group.rows
        for marker in (
            (
                f"| `{group.name}` | {row.rank} | `{row.route}` | "
                f"`{row.window}` | `{row.motion_mode}` | `{row.result}` |"
            ),
            row.command,
            _onboarding_visible_ux_issue_areas(row),
        )
    )
    checks = (
        _build_presence_check(
            area="UX Intake Metadata",
            text=text,
            markers=metadata_markers,
            summary="The UX issue intake metadata matches the current visible QA report.",
        ),
        _build_presence_check(
            area="Refresh Commands",
            text=text,
            markers=command_markers,
            summary=(
                "The UX issue intake includes current session, preflight, and closure commands."
            ),
        ),
        _build_presence_check(
            area="Issue Intake Rows",
            text=text,
            markers=row_markers,
            summary="The UX issue intake lists every current row with matching open commands.",
        ),
        _build_presence_check(
            area="Severity Rules",
            text=text,
            markers=(
                "`P0`: blocks reading, navigation, save/load, pause/back/menu",
                "`P1`: playable but materially slows first-time understanding.",
                "`P2`: polish issue that should not block manual evidence.",
                "`none`: no issue observed; still record evidence notes",
            ),
            summary="The UX issue intake keeps severity rules visible.",
        ),
        _build_presence_check(
            area="No-Fabrication Guardrail",
            text=text,
            markers=(
                "This intake is not evidence; it only captures observed UX issues.",
                "Do not invent defects to make a row look tested.",
                (
                    "Keep onboarding manual-required until report rows contain real "
                    "visible-window notes."
                ),
            ),
            summary="The UX issue intake keeps no-fabrication guardrails visible.",
        ),
    )
    return OnboardingVisibleUxIssueIntakeValidation(
        intake_path=intake_path,
        status="pass" if all(check.status == "pass" for check in checks) else "fail",
        checks=checks,
    )


def record_onboarding_visible_ux_issue(
    intake_path: Path,
    *,
    severity: str,
    issue_notes: str,
    follow_up: str,
    rank: int | None = None,
    route: str | None = None,
    window: str | None = None,
    motion_mode: str | None = None,
) -> OnboardingVisibleUxIssueRecord:
    """Record one observed UX issue classification in the intake sheet."""

    normalized_severity = _normalize_onboarding_visible_ux_severity(severity)
    if normalized_severity == "todo":
        raise ValueError("Severity must be one of: P0, P1, P2, none.")
    if not _has_real_observation_notes(issue_notes):
        raise ValueError(
            "Issue notes must describe a real visible-window observation, not a placeholder."
        )
    if not _is_clear_follow_up(follow_up):
        raise ValueError("Follow-up must name an owner/date or explicitly say none.")
    if not intake_path.exists():
        raise ValueError(f"Onboarding visible UX issue intake not found: {intake_path}")

    lines = intake_path.read_text(encoding="utf-8").splitlines()
    parsed_rows = tuple(
        (index, row)
        for index, line in enumerate(lines)
        if (row := _parse_onboarding_visible_ux_issue_row(line)) is not None
    )
    matched_index, matched_row = _find_onboarding_visible_ux_issue_row(
        parsed_rows,
        rank=rank,
        route=route,
        window=window,
        motion_mode=motion_mode,
    )
    updated_row = OnboardingVisibleUxFixPlanRow(
        group=matched_row.group,
        rank=matched_row.rank,
        route=matched_row.route,
        window=matched_row.window,
        motion_mode=matched_row.motion_mode,
        result=matched_row.result,
        command=matched_row.command,
        ux_areas=matched_row.ux_areas,
        severity=normalized_severity,
        issue_notes=issue_notes.strip(),
        follow_up=follow_up.strip(),
    )
    lines[matched_index] = _format_onboarding_visible_ux_issue_row(updated_row)
    intake_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return OnboardingVisibleUxIssueRecord(
        intake_path=intake_path,
        row=updated_row,
    )


def build_onboarding_visible_ux_fix_plan(
    intake_path: Path,
    *,
    report_path: Path,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleUxFixPlan:
    """Build a prioritized UX fix plan from the visible onboarding issue intake."""

    intake_validation = validate_onboarding_visible_ux_issue_intake(
        intake_path,
        report_path=report_path,
        command_prefix=command_prefix,
    )
    if not intake_validation.ok:
        failed = ", ".join(check.area for check in intake_validation.failed_checks)
        raise ValueError(f"UX issue intake must validate before fix planning: {failed}")

    text = intake_path.read_text(encoding="utf-8")
    rows = tuple(
        row
        for line in text.splitlines()
        if (row := _parse_onboarding_visible_ux_issue_row(line)) is not None
    )
    if not rows:
        raise ValueError("Onboarding visible UX issue intake has no issue rows.")

    p0_count = sum(1 for row in rows if row.severity == "P0")
    p1_count = sum(1 for row in rows if row.severity == "P1")
    p2_count = sum(1 for row in rows if row.severity == "P2")
    none_count = sum(1 for row in rows if row.severity == "none")
    todo_count = sum(1 for row in rows if row.severity == "todo")
    if todo_count:
        status = "triage-required"
    elif p0_count or p1_count:
        status = "fix-required"
    else:
        status = "ready-for-manual-evidence"

    return OnboardingVisibleUxFixPlan(
        report_path=report_path,
        intake_path=intake_path,
        status=status,
        rows=rows,
        p0_count=p0_count,
        p1_count=p1_count,
        p2_count=p2_count,
        none_count=none_count,
        todo_count=todo_count,
        validate_intake_command=(
            f"{command_prefix} validate-onboarding-visible-ux-issue-intake "
            f"--report {report_path} --input {intake_path}"
        ),
        validate_report_command=(
            f"{command_prefix} validate-onboarding-visible-playtest-report --report {report_path}"
        ),
        status_command=(
            f"{command_prefix} onboarding-visible-playtest-status --report {report_path}"
        ),
    )


def write_onboarding_visible_ux_fix_plan(
    plan: OnboardingVisibleUxFixPlan,
    output_path: Path,
) -> None:
    """Write a prioritized UX fix plan without converting it into evidence."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NEXUS TECH Onboarding Visible UX Fix Plan",
        "",
        f"- Report: `{plan.report_path}`",
        f"- Intake: `{plan.intake_path}`",
        f"- Status: `{plan.status}`",
        f"- Rows: `{plan.total_rows}`",
        f"- P0: `{plan.p0_count}`",
        f"- P1: `{plan.p1_count}`",
        f"- P2: `{plan.p2_count}`",
        f"- None: `{plan.none_count}`",
        f"- Todo: `{plan.todo_count}`",
        "- Manual result: `not completed by automation`",
        "- Evidence policy: `fix plan must come from observed intake rows`",
        "- Release gate: `no P0/P1 and no todo severities before UI signoff`",
        "",
        (
            "Use this fix plan after the UX issue intake is filled from real visible "
            "play. It is a prioritization artifact, not proof that the UI was fixed."
        ),
        "",
        "## Required Refresh",
        "",
        "```bash",
        plan.validate_intake_command,
        plan.validate_report_command,
        plan.status_command,
        "```",
        "",
        "## Fix Queue",
        "",
        (
            "| Priority | Group | Rank | Route | Window | Motion | Severity | "
            "UX Areas | Issue Notes | Follow-up | Open Command |"
        ),
        "| --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in plan.rows:
        lines.append(
            "| "
            f"`{_onboarding_visible_ux_fix_priority(row)}` | "
            f"`{row.group}` | "
            f"{row.rank} | "
            f"`{row.route}` | "
            f"`{row.window}` | "
            f"`{row.motion_mode}` | "
            f"`{row.severity}` | "
            f"`{_markdown_escape(row.ux_areas)}` | "
            f"{_markdown_escape(row.issue_notes)} | "
            f"{_markdown_escape(row.follow_up)} | "
            f"`{_markdown_escape(row.command)}` |"
        )
    lines.extend(
        [
            "",
            "## Release Gate Rules",
            "",
            "- P0 and P1 counts must be zero before UI signoff.",
            "- `todo` severities mean manual UX triage is incomplete.",
            "- `none` rows still need real evidence notes in the onboarding report.",
            "- Re-run the intake validator after editing any issue row.",
            "",
            "## No-Fabrication Guardrail",
            "",
            "- This fix plan is not manual evidence; it only prioritizes observed issues.",
            "- Do not create fixes from placeholder intake rows.",
            "- Do not mark UI signoff complete until visible-window notes exist.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_onboarding_visible_ux_fix_plan(
    plan_path: Path,
    *,
    intake_path: Path,
    report_path: Path,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleUxFixPlanValidation:
    """Validate that the UX fix plan matches the current issue intake."""

    try:
        expected = build_onboarding_visible_ux_fix_plan(
            intake_path,
            report_path=report_path,
            command_prefix=command_prefix,
        )
    except (OSError, ValueError) as error:
        return OnboardingVisibleUxFixPlanValidation(
            plan_path=plan_path,
            status="fail",
            checks=(
                _build_check(
                    area="Source Intake",
                    passed=False,
                    summary="The source UX issue intake must validate before fix planning.",
                    evidence=(str(error),),
                ),
            ),
        )
    if not plan_path.exists():
        return OnboardingVisibleUxFixPlanValidation(
            plan_path=plan_path,
            status="fail",
            checks=(
                _build_check(
                    area="UX Fix Plan File",
                    passed=False,
                    summary="The onboarding visible UX fix plan file must exist.",
                    evidence=(f"missing:{plan_path}",),
                ),
            ),
        )

    text = plan_path.read_text(encoding="utf-8")
    metadata_markers = (
        "# NEXUS TECH Onboarding Visible UX Fix Plan",
        f"- Report: `{expected.report_path}`",
        f"- Intake: `{expected.intake_path}`",
        f"- Status: `{expected.status}`",
        f"- Rows: `{expected.total_rows}`",
        f"- P0: `{expected.p0_count}`",
        f"- P1: `{expected.p1_count}`",
        f"- P2: `{expected.p2_count}`",
        f"- None: `{expected.none_count}`",
        f"- Todo: `{expected.todo_count}`",
        "- Manual result: `not completed by automation`",
        "- Evidence policy: `fix plan must come from observed intake rows`",
        "- Release gate: `no P0/P1 and no todo severities before UI signoff`",
    )
    command_markers = (
        expected.validate_intake_command,
        expected.validate_report_command,
        expected.status_command,
    )
    row_markers = tuple(
        marker
        for row in expected.rows
        for marker in (
            (
                f"| `{_onboarding_visible_ux_fix_priority(row)}` | `{row.group}` | "
                f"{row.rank} | `{row.route}` | `{row.window}` | "
                f"`{row.motion_mode}` | `{row.severity}` |"
            ),
            row.ux_areas,
            row.issue_notes,
            row.follow_up,
            row.command,
        )
    )
    checks = (
        _build_presence_check(
            area="UX Fix Plan Metadata",
            text=text,
            markers=metadata_markers,
            summary="The UX fix plan metadata matches the current issue intake.",
        ),
        _build_presence_check(
            area="Refresh Commands",
            text=text,
            markers=command_markers,
            summary="The UX fix plan includes current intake, report, and status commands.",
        ),
        _build_presence_check(
            area="Fix Queue Rows",
            text=text,
            markers=row_markers,
            summary="The UX fix plan lists every current issue intake row.",
        ),
        _build_presence_check(
            area="Release Gate Rules",
            text=text,
            markers=(
                "P0 and P1 counts must be zero before UI signoff.",
                "`todo` severities mean manual UX triage is incomplete.",
                "`none` rows still need real evidence notes in the onboarding report.",
                "Re-run the intake validator after editing any issue row.",
            ),
            summary="The UX fix plan keeps UI signoff gates visible.",
        ),
        _build_presence_check(
            area="No-Fabrication Guardrail",
            text=text,
            markers=(
                "This fix plan is not manual evidence; it only prioritizes observed issues.",
                "Do not create fixes from placeholder intake rows.",
                "Do not mark UI signoff complete until visible-window notes exist.",
            ),
            summary="The UX fix plan keeps no-fabrication guardrails visible.",
        ),
    )
    return OnboardingVisibleUxFixPlanValidation(
        plan_path=plan_path,
        status="pass" if all(check.status == "pass" for check in checks) else "fail",
        checks=checks,
    )


def build_onboarding_visible_ux_triage_sprint(
    plan_path: Path,
    *,
    intake_path: Path,
    report_path: Path,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleUxTriageSprint:
    """Build a focused sprint packet from the current visible UX fix plan."""

    plan_validation = validate_onboarding_visible_ux_fix_plan(
        plan_path,
        intake_path=intake_path,
        report_path=report_path,
        command_prefix=command_prefix,
    )
    if not plan_validation.ok:
        failed = ", ".join(check.area for check in plan_validation.failed_checks)
        raise ValueError(f"UX fix plan must validate before sprint planning: {failed}")

    plan = build_onboarding_visible_ux_fix_plan(
        intake_path,
        report_path=report_path,
        command_prefix=command_prefix,
    )
    blocker_count = plan.p0_count + plan.p1_count
    if blocker_count:
        status = "fix-and-triage-required" if plan.todo_count else "fix-required"
    elif plan.todo_count:
        status = "triage-required"
    elif plan.p2_count:
        status = "polish-ready"
    else:
        status = "ready-for-manual-evidence"

    return OnboardingVisibleUxTriageSprint(
        report_path=report_path,
        intake_path=intake_path,
        plan_path=plan_path,
        status=status,
        rows=tuple(sorted(plan.rows, key=_onboarding_visible_ux_sprint_sort_key)),
        p0_count=plan.p0_count,
        p1_count=plan.p1_count,
        p2_count=plan.p2_count,
        none_count=plan.none_count,
        todo_count=plan.todo_count,
        rebuild_fix_plan_command=(
            f"{command_prefix} onboarding-visible-ux-fix-plan "
            f"--report {report_path} --input {intake_path} --output {plan_path}"
        ),
        validate_fix_plan_command=(
            f"{command_prefix} validate-onboarding-visible-ux-fix-plan "
            f"--report {report_path} --intake {intake_path} --input {plan_path}"
        ),
        validate_intake_command=(
            f"{command_prefix} validate-onboarding-visible-ux-issue-intake "
            f"--report {report_path} --input {intake_path}"
        ),
        validate_report_command=(
            f"{command_prefix} validate-onboarding-visible-playtest-report --report {report_path}"
        ),
        status_command=(
            f"{command_prefix} onboarding-visible-playtest-status --report {report_path}"
        ),
    )


def write_onboarding_visible_ux_triage_sprint(
    sprint: OnboardingVisibleUxTriageSprint,
    output_path: Path,
) -> None:
    """Write the focused UX triage sprint without fabricating manual evidence."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NEXUS TECH Onboarding Visible UX Triage Sprint",
        "",
        f"- Report: `{sprint.report_path}`",
        f"- Intake: `{sprint.intake_path}`",
        f"- Fix Plan: `{sprint.plan_path}`",
        f"- Status: `{sprint.status}`",
        f"- Rows: `{sprint.total_rows}`",
        f"- P0: `{sprint.p0_count}`",
        f"- P1: `{sprint.p1_count}`",
        f"- P2: `{sprint.p2_count}`",
        f"- None: `{sprint.none_count}`",
        f"- Todo: `{sprint.todo_count}`",
        f"- Blockers: `{sprint.blocker_count}`",
        "- Manual result: `not completed by automation`",
        "- Sprint policy: `triage todo rows and close P0/P1 before UI signoff`",
        "",
        (
            "Use this sprint as the operator handoff for the next visible-window UX pass. "
            "It orders observed P0/P1 rows first, then unclassified `todo` rows, without "
            "claiming that manual evidence was captured."
        ),
        "",
        "## Required Refresh",
        "",
        "```bash",
        sprint.validate_intake_command,
        sprint.rebuild_fix_plan_command,
        sprint.validate_fix_plan_command,
        sprint.validate_report_command,
        sprint.status_command,
        "```",
        "",
        "## Sprint Queue",
        "",
        (
            "| Phase | Priority | Group | Rank | Route | Window | Motion | Severity | "
            "Manual Step | Open Command |"
        ),
        "| --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for row in sprint.rows:
        lines.append(
            "| "
            f"`{_onboarding_visible_ux_sprint_phase(row)}` | "
            f"`{_onboarding_visible_ux_fix_priority(row)}` | "
            f"`{row.group}` | "
            f"{row.rank} | "
            f"`{row.route}` | "
            f"`{row.window}` | "
            f"`{row.motion_mode}` | "
            f"`{row.severity}` | "
            f"{_markdown_escape(_onboarding_visible_ux_sprint_step(row))} | "
            f"`{_markdown_escape(row.command)}` |"
        )
    lines.extend(
        [
            "",
            "## Exit Criteria",
            "",
            "- Every `todo` severity is replaced with P0, P1, P2, or none after visible play.",
            "- P0 and P1 counts are zero before UI signoff.",
            "- Main report rows contain real visible-window notes, not placeholders.",
            "- Fix plan, intake, report, and sprint validators all pass after edits.",
            "",
            "## No-Fabrication Guardrail",
            "",
            "- This sprint packet is not evidence; it only sequences triage and fix work.",
            "- Do not mark a row fixed unless the visible route was opened again.",
            "- Do not close onboarding UX until the report and intake agree on real observations.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_onboarding_visible_ux_triage_sprint(
    sprint_path: Path,
    *,
    plan_path: Path,
    intake_path: Path,
    report_path: Path,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleUxTriageSprintValidation:
    """Validate that the UX triage sprint matches the current fix plan."""

    try:
        expected = build_onboarding_visible_ux_triage_sprint(
            plan_path,
            intake_path=intake_path,
            report_path=report_path,
            command_prefix=command_prefix,
        )
    except (OSError, ValueError) as error:
        return OnboardingVisibleUxTriageSprintValidation(
            sprint_path=sprint_path,
            status="fail",
            checks=(
                _build_check(
                    area="Source Fix Plan",
                    passed=False,
                    summary="The source UX fix plan must validate before sprint planning.",
                    evidence=(str(error),),
                ),
            ),
        )
    if not sprint_path.exists():
        return OnboardingVisibleUxTriageSprintValidation(
            sprint_path=sprint_path,
            status="fail",
            checks=(
                _build_check(
                    area="UX Triage Sprint File",
                    passed=False,
                    summary="The onboarding visible UX triage sprint file must exist.",
                    evidence=(f"missing:{sprint_path}",),
                ),
            ),
        )

    text = sprint_path.read_text(encoding="utf-8")
    metadata_markers = (
        "# NEXUS TECH Onboarding Visible UX Triage Sprint",
        f"- Report: `{expected.report_path}`",
        f"- Intake: `{expected.intake_path}`",
        f"- Fix Plan: `{expected.plan_path}`",
        f"- Status: `{expected.status}`",
        f"- Rows: `{expected.total_rows}`",
        f"- P0: `{expected.p0_count}`",
        f"- P1: `{expected.p1_count}`",
        f"- P2: `{expected.p2_count}`",
        f"- None: `{expected.none_count}`",
        f"- Todo: `{expected.todo_count}`",
        f"- Blockers: `{expected.blocker_count}`",
        "- Manual result: `not completed by automation`",
        "- Sprint policy: `triage todo rows and close P0/P1 before UI signoff`",
    )
    command_markers = (
        expected.validate_intake_command,
        expected.rebuild_fix_plan_command,
        expected.validate_fix_plan_command,
        expected.validate_report_command,
        expected.status_command,
    )
    row_markers = tuple(
        marker
        for row in expected.rows
        for marker in (
            (
                f"| `{_onboarding_visible_ux_sprint_phase(row)}` | "
                f"`{_onboarding_visible_ux_fix_priority(row)}` | `{row.group}` | "
                f"{row.rank} | `{row.route}` | `{row.window}` | "
                f"`{row.motion_mode}` | `{row.severity}` |"
            ),
            _onboarding_visible_ux_sprint_step(row),
            row.command,
        )
    )
    checks = (
        _build_presence_check(
            area="UX Triage Sprint Metadata",
            text=text,
            markers=metadata_markers,
            summary="The UX triage sprint metadata matches the current fix plan.",
        ),
        _build_presence_check(
            area="Refresh Commands",
            text=text,
            markers=command_markers,
            summary="The sprint includes current intake, fix plan, report, and status commands.",
        ),
        _build_presence_check(
            area="Sprint Queue Rows",
            text=text,
            markers=row_markers,
            summary="The sprint lists every current fix-plan row with matching open command.",
        ),
        _build_presence_check(
            area="Exit Criteria",
            text=text,
            markers=(
                "Every `todo` severity is replaced with P0, P1, P2, or none after visible play.",
                "P0 and P1 counts are zero before UI signoff.",
                "Main report rows contain real visible-window notes, not placeholders.",
                "Fix plan, intake, report, and sprint validators all pass after edits.",
            ),
            summary="The sprint keeps completion gates visible.",
        ),
        _build_presence_check(
            area="No-Fabrication Guardrail",
            text=text,
            markers=(
                "This sprint packet is not evidence; it only sequences triage and fix work.",
                "Do not mark a row fixed unless the visible route was opened again.",
                (
                    "Do not close onboarding UX until the report and intake agree on real "
                    "observations."
                ),
            ),
            summary="The sprint keeps no-fabrication guardrails visible.",
        ),
    )
    return OnboardingVisibleUxTriageSprintValidation(
        sprint_path=sprint_path,
        status="pass" if all(check.status == "pass" for check in checks) else "fail",
        checks=checks,
    )


def build_onboarding_visible_ux_triage_next_step(
    sprint_path: Path,
    *,
    plan_path: Path,
    intake_path: Path,
    report_path: Path,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleUxTriageNextStep:
    """Build the next copy-ready manual UX triage action from the sprint."""

    sprint_validation = validate_onboarding_visible_ux_triage_sprint(
        sprint_path,
        plan_path=plan_path,
        intake_path=intake_path,
        report_path=report_path,
        command_prefix=command_prefix,
    )
    if not sprint_validation.ok:
        failed = ", ".join(check.area for check in sprint_validation.failed_checks)
        raise ValueError(f"UX triage sprint must validate before next-step handoff: {failed}")

    sprint = build_onboarding_visible_ux_triage_sprint(
        plan_path,
        intake_path=intake_path,
        report_path=report_path,
        command_prefix=command_prefix,
    )
    if not sprint.rows:
        raise ValueError("Onboarding visible UX triage sprint has no rows.")

    row = next(
        (
            candidate
            for candidate in sprint.rows
            if candidate.severity in {"P0", "P1", "todo", "P2"}
        ),
        sprint.rows[0],
    )
    phase = _onboarding_visible_ux_sprint_phase(row)
    priority = _onboarding_visible_ux_fix_priority(row)
    return OnboardingVisibleUxTriageNextStep(
        report_path=report_path,
        intake_path=intake_path,
        plan_path=plan_path,
        sprint_path=sprint_path,
        status=phase,
        row=row,
        phase=phase,
        priority=priority,
        open_command=row.command,
        report_recorder_command=(
            f"{command_prefix} record-onboarding-visible-playtest-route "
            f"--report {report_path} --rank {row.rank} --result watch "
            f'--notes "<replace with observed visible-window notes mentioning '
            f'{row.ux_areas}>"'
        ),
        intake_recorder_command=(
            f"{command_prefix} record-onboarding-visible-ux-issue "
            f"--input {intake_path} --rank {row.rank} --severity P1 "
            f'--issue-notes "<replace with observed UX issue or no-issue notes '
            f'mentioning {row.ux_areas}>" --follow-up "owner/date or none"'
        ),
        validate_intake_command=(
            f"{command_prefix} validate-onboarding-visible-ux-issue-intake "
            f"--report {report_path} --input {intake_path}"
        ),
        rebuild_fix_plan_command=(
            f"{command_prefix} onboarding-visible-ux-fix-plan "
            f"--report {report_path} --input {intake_path} --output {plan_path}"
        ),
        validate_fix_plan_command=(
            f"{command_prefix} validate-onboarding-visible-ux-fix-plan "
            f"--report {report_path} --intake {intake_path} --input {plan_path}"
        ),
        rebuild_sprint_command=(
            f"{command_prefix} onboarding-visible-ux-triage-sprint "
            f"--report {report_path} --intake {intake_path} "
            f"--plan {plan_path} --output {sprint_path}"
        ),
        validate_sprint_command=(
            f"{command_prefix} validate-onboarding-visible-ux-triage-sprint "
            f"--report {report_path} --intake {intake_path} "
            f"--plan {plan_path} --input {sprint_path}"
        ),
        validate_report_command=(
            f"{command_prefix} validate-onboarding-visible-playtest-report --report {report_path}"
        ),
        status_command=(
            f"{command_prefix} onboarding-visible-playtest-status --report {report_path}"
        ),
    )


def write_onboarding_visible_ux_triage_next_step(
    next_step: OnboardingVisibleUxTriageNextStep,
    output_path: Path,
) -> None:
    """Write the next UX triage handoff without recording tester evidence."""

    row = next_step.row
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NEXUS TECH Onboarding Visible UX Triage Next Step",
        "",
        f"- Report: `{next_step.report_path}`",
        f"- Intake: `{next_step.intake_path}`",
        f"- Fix Plan: `{next_step.plan_path}`",
        f"- Sprint: `{next_step.sprint_path}`",
        f"- Status: `{next_step.status}`",
        f"- Phase: `{next_step.phase}`",
        f"- Priority: `{next_step.priority}`",
        f"- Group: `{row.group}`",
        f"- Rank: `{row.rank}`",
        f"- Route: `{row.route}`",
        f"- Window: `{row.window}`",
        f"- Motion: `{row.motion_mode}`",
        f"- Severity: `{row.severity}`",
        f"- UX Areas: `{_markdown_escape(row.ux_areas)}`",
        "- Manual result: `not completed by automation`",
        "- Handoff policy: `open the route and update intake/report from real observation`",
        "",
        "## Next Manual Action",
        "",
        f"- Phase: `{next_step.phase}`",
        f"- Priority: `{next_step.priority}`",
        f"- Step: {_markdown_escape(_onboarding_visible_ux_sprint_step(row))}",
        f"- Intake row: `{row.group}` rank `{row.rank}` route `{row.route}`",
        "",
        "Open the route first:",
        "",
        "```bash",
        next_step.open_command,
        "```",
        "",
        "Record report notes only after observing the visible route:",
        "",
        "```bash",
        next_step.report_recorder_command,
        "```",
        "",
        "Then update the intake row from the same observation after replacing placeholders:",
        "",
        "```bash",
        next_step.intake_recorder_command,
        "```",
        "",
        "## Refresh Commands",
        "",
        "```bash",
        next_step.validate_intake_command,
        next_step.rebuild_fix_plan_command,
        next_step.validate_fix_plan_command,
        next_step.rebuild_sprint_command,
        next_step.validate_sprint_command,
        next_step.validate_report_command,
        next_step.status_command,
        "```",
        "",
        "## Exit Criteria",
        "",
        "- The selected row is no longer `todo` after real visible play.",
        "- If severity is P0/P1, the UI is fixed and reopened before signoff.",
        "- Report notes mention window, motion mode, readability, controls, and blocker status.",
        "- Intake, fix plan, sprint, next-step, and report validators pass after updates.",
        "",
        "## No-Fabrication Guardrail",
        "",
        "- This next-step handoff is not evidence; it only points to the next row.",
        "- Do not run the recorder command until the visible route has been opened.",
        "- Do not downgrade severity without observed notes that explain why.",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_onboarding_visible_ux_triage_next_step(
    next_path: Path,
    *,
    sprint_path: Path,
    plan_path: Path,
    intake_path: Path,
    report_path: Path,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleUxTriageNextStepValidation:
    """Validate that the UX triage next-step matches the current sprint."""

    try:
        expected = build_onboarding_visible_ux_triage_next_step(
            sprint_path,
            plan_path=plan_path,
            intake_path=intake_path,
            report_path=report_path,
            command_prefix=command_prefix,
        )
    except (OSError, ValueError) as error:
        return OnboardingVisibleUxTriageNextStepValidation(
            next_path=next_path,
            status="fail",
            checks=(
                _build_check(
                    area="Source Sprint",
                    passed=False,
                    summary="The source UX triage sprint must validate before next-step.",
                    evidence=(str(error),),
                ),
            ),
        )
    if not next_path.exists():
        return OnboardingVisibleUxTriageNextStepValidation(
            next_path=next_path,
            status="fail",
            checks=(
                _build_check(
                    area="UX Triage Next-Step File",
                    passed=False,
                    summary="The onboarding visible UX triage next-step file must exist.",
                    evidence=(f"missing:{next_path}",),
                ),
            ),
        )

    row = expected.row
    text = next_path.read_text(encoding="utf-8")
    metadata_markers = (
        "# NEXUS TECH Onboarding Visible UX Triage Next Step",
        f"- Report: `{expected.report_path}`",
        f"- Intake: `{expected.intake_path}`",
        f"- Fix Plan: `{expected.plan_path}`",
        f"- Sprint: `{expected.sprint_path}`",
        f"- Status: `{expected.status}`",
        f"- Phase: `{expected.phase}`",
        f"- Priority: `{expected.priority}`",
        f"- Group: `{row.group}`",
        f"- Rank: `{row.rank}`",
        f"- Route: `{row.route}`",
        f"- Window: `{row.window}`",
        f"- Motion: `{row.motion_mode}`",
        f"- Severity: `{row.severity}`",
        "- Manual result: `not completed by automation`",
        "- Handoff policy: `open the route and update intake/report from real observation`",
    )
    command_markers = (
        expected.open_command,
        expected.report_recorder_command,
        expected.intake_recorder_command,
        expected.validate_intake_command,
        expected.rebuild_fix_plan_command,
        expected.validate_fix_plan_command,
        expected.rebuild_sprint_command,
        expected.validate_sprint_command,
        expected.validate_report_command,
        expected.status_command,
    )
    checks = (
        _build_presence_check(
            area="UX Triage Next-Step Metadata",
            text=text,
            markers=metadata_markers,
            summary="The UX triage next-step metadata matches the current sprint.",
        ),
        _build_presence_check(
            area="Next Manual Action",
            text=text,
            markers=(
                f"- Step: {_markdown_escape(_onboarding_visible_ux_sprint_step(row))}",
                f"- Intake row: `{row.group}` rank `{row.rank}` route `{row.route}`",
                "Open the route first:",
                "Record report notes only after observing the visible route:",
                (
                    "Then update the intake row from the same observation after "
                    "replacing placeholders:"
                ),
            ),
            summary="The next-step handoff names the exact manual action and row.",
        ),
        _build_presence_check(
            area="Refresh Commands",
            text=text,
            markers=command_markers,
            summary="The next-step handoff includes current open, recorder, and refresh commands.",
        ),
        _build_presence_check(
            area="Exit Criteria",
            text=text,
            markers=(
                "The selected row is no longer `todo` after real visible play.",
                "If severity is P0/P1, the UI is fixed and reopened before signoff.",
                (
                    "Report notes mention window, motion mode, readability, controls, "
                    "and blocker status."
                ),
                "Intake, fix plan, sprint, next-step, and report validators pass after updates.",
            ),
            summary="The next-step handoff keeps completion gates visible.",
        ),
        _build_presence_check(
            area="No-Fabrication Guardrail",
            text=text,
            markers=(
                "This next-step handoff is not evidence; it only points to the next row.",
                "Do not run the recorder command until the visible route has been opened.",
                "Do not downgrade severity without observed notes that explain why.",
            ),
            summary="The next-step handoff keeps no-fabrication guardrails visible.",
        ),
    )
    return OnboardingVisibleUxTriageNextStepValidation(
        next_path=next_path,
        status="pass" if all(check.status == "pass" for check in checks) else "fail",
        checks=checks,
    )


def build_onboarding_visible_ux_recording_queue(
    sprint_path: Path,
    *,
    plan_path: Path,
    intake_path: Path,
    report_path: Path,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleUxRecordingQueue:
    """Build the copy-ready queue for manual visible UX recording."""

    sprint_validation = validate_onboarding_visible_ux_triage_sprint(
        sprint_path,
        plan_path=plan_path,
        intake_path=intake_path,
        report_path=report_path,
        command_prefix=command_prefix,
    )
    if not sprint_validation.ok:
        failed = ", ".join(check.area for check in sprint_validation.failed_checks)
        raise ValueError(f"UX triage sprint must validate before recording queue: {failed}")

    sprint = build_onboarding_visible_ux_triage_sprint(
        plan_path,
        intake_path=intake_path,
        report_path=report_path,
        command_prefix=command_prefix,
    )
    rows = tuple(
        _build_onboarding_visible_ux_recording_queue_row(
            row,
            report_path=report_path,
            intake_path=intake_path,
            command_prefix=command_prefix,
        )
        for row in sprint.rows
        if row.severity in {"P0", "P1", "todo", "P2"}
    )
    status = "ready-for-manual-evidence" if not rows else sprint.status
    return OnboardingVisibleUxRecordingQueue(
        report_path=report_path,
        intake_path=intake_path,
        plan_path=plan_path,
        sprint_path=sprint_path,
        status=status,
        rows=rows,
        blocker_count=sprint.blocker_count,
        todo_count=sprint.todo_count,
        validate_intake_command=(
            f"{command_prefix} validate-onboarding-visible-ux-issue-intake "
            f"--report {report_path} --input {intake_path}"
        ),
        rebuild_fix_plan_command=(
            f"{command_prefix} onboarding-visible-ux-fix-plan "
            f"--report {report_path} --input {intake_path} --output {plan_path}"
        ),
        validate_fix_plan_command=(
            f"{command_prefix} validate-onboarding-visible-ux-fix-plan "
            f"--report {report_path} --intake {intake_path} --input {plan_path}"
        ),
        rebuild_sprint_command=(
            f"{command_prefix} onboarding-visible-ux-triage-sprint "
            f"--report {report_path} --intake {intake_path} "
            f"--plan {plan_path} --output {sprint_path}"
        ),
        validate_sprint_command=(
            f"{command_prefix} validate-onboarding-visible-ux-triage-sprint "
            f"--report {report_path} --intake {intake_path} "
            f"--plan {plan_path} --input {sprint_path}"
        ),
        validate_report_command=(
            f"{command_prefix} validate-onboarding-visible-playtest-report --report {report_path}"
        ),
        status_command=(
            f"{command_prefix} onboarding-visible-playtest-status --report {report_path}"
        ),
    )


def write_onboarding_visible_ux_recording_queue(
    queue: OnboardingVisibleUxRecordingQueue,
    output_path: Path,
) -> None:
    """Write the manual UX recording queue without creating evidence."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NEXUS TECH Onboarding Visible UX Recording Queue",
        "",
        f"- Report: `{queue.report_path}`",
        f"- Intake: `{queue.intake_path}`",
        f"- Fix Plan: `{queue.plan_path}`",
        f"- Sprint: `{queue.sprint_path}`",
        f"- Status: `{queue.status}`",
        f"- Rows: `{queue.total_rows}`",
        f"- Blockers: `{queue.blocker_count}`",
        f"- Todo: `{queue.todo_count}`",
        "- Manual result: `not completed by automation`",
        (
            "- Queue policy: `open each route, then update report and intake "
            "from the same observation`"
        ),
        "",
        "## Operator Order",
        "",
        "- Open the route command first and inspect the real visible output.",
        "- Record report notes only after observing readability, controls, and motion.",
        "- Record the UX issue intake row from the same observation before rebuilding plans.",
        "- Re-run the refresh commands after each completed row or blocker fix.",
        "",
        "## Refresh Commands",
        "",
        "```bash",
        queue.validate_intake_command,
        queue.rebuild_fix_plan_command,
        queue.validate_fix_plan_command,
        queue.rebuild_sprint_command,
        queue.validate_sprint_command,
        queue.validate_report_command,
        queue.status_command,
        "```",
        "",
        "## Recording Queue",
        "",
        (
            "| Phase | Priority | Rank | Route | Window | Motion | Severity | "
            "Open Command | Report Recorder | Intake Recorder |"
        ),
        "| --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for queue_row in queue.rows:
        row = queue_row.row
        lines.append(
            "| "
            f"`{queue_row.phase}` | "
            f"`{queue_row.priority}` | "
            f"{row.rank} | "
            f"`{row.route}` | "
            f"`{row.window}` | "
            f"`{row.motion_mode}` | "
            f"`{row.severity}` | "
            f"`{_markdown_escape(queue_row.open_command)}` | "
            f"`{_markdown_escape(queue_row.report_recorder_command)}` | "
            f"`{_markdown_escape(queue_row.intake_recorder_command)}` |"
        )
    if not queue.rows:
        lines.append(
            "| `ready-for-manual-evidence` | `none` | 0 | `complete` | `n/a` | "
            "`n/a` | `none` | `n/a` | `n/a` | `n/a` |"
        )
    lines.extend(
        [
            "",
            "## Exit Criteria",
            "",
            "- Every queued route has real report notes recorded after visible play.",
            "- Every queued intake row is no longer `todo` after the same observation.",
            "- P0/P1 rows are fixed, reopened, and reclassified before UI signoff.",
            "- Intake, fix plan, sprint, queue, and report validators pass after updates.",
            "",
            "## No-Fabrication Guardrail",
            "",
            "- This recording queue is not evidence; it only orders the manual work.",
            "- Do not run recorder commands until the corresponding route was opened.",
            "- Do not use `pass`, `none`, or lower severity unless the observation supports it.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_onboarding_visible_ux_recording_queue(
    queue_path: Path,
    *,
    sprint_path: Path,
    plan_path: Path,
    intake_path: Path,
    report_path: Path,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleUxRecordingQueueValidation:
    """Validate that the UX recording queue matches the current sprint."""

    try:
        expected = build_onboarding_visible_ux_recording_queue(
            sprint_path,
            plan_path=plan_path,
            intake_path=intake_path,
            report_path=report_path,
            command_prefix=command_prefix,
        )
    except (OSError, ValueError) as error:
        return OnboardingVisibleUxRecordingQueueValidation(
            queue_path=queue_path,
            status="fail",
            checks=(
                _build_check(
                    area="Source Sprint",
                    passed=False,
                    summary="The source UX triage sprint must validate before queueing.",
                    evidence=(str(error),),
                ),
            ),
        )
    if not queue_path.exists():
        return OnboardingVisibleUxRecordingQueueValidation(
            queue_path=queue_path,
            status="fail",
            checks=(
                _build_check(
                    area="UX Recording Queue File",
                    passed=False,
                    summary="The onboarding visible UX recording queue file must exist.",
                    evidence=(f"missing:{queue_path}",),
                ),
            ),
        )

    text = queue_path.read_text(encoding="utf-8")
    metadata_markers = (
        "# NEXUS TECH Onboarding Visible UX Recording Queue",
        f"- Report: `{expected.report_path}`",
        f"- Intake: `{expected.intake_path}`",
        f"- Fix Plan: `{expected.plan_path}`",
        f"- Sprint: `{expected.sprint_path}`",
        f"- Status: `{expected.status}`",
        f"- Rows: `{expected.total_rows}`",
        f"- Blockers: `{expected.blocker_count}`",
        f"- Todo: `{expected.todo_count}`",
        "- Manual result: `not completed by automation`",
        (
            "- Queue policy: `open each route, then update report and intake "
            "from the same observation`"
        ),
    )
    command_markers = (
        expected.validate_intake_command,
        expected.rebuild_fix_plan_command,
        expected.validate_fix_plan_command,
        expected.rebuild_sprint_command,
        expected.validate_sprint_command,
        expected.validate_report_command,
        expected.status_command,
    )
    row_markers = tuple(
        marker
        for queue_row in expected.rows
        for row in (queue_row.row,)
        for marker in (
            (
                f"| `{queue_row.phase}` | `{queue_row.priority}` | {row.rank} | "
                f"`{row.route}` | `{row.window}` | `{row.motion_mode}` | "
                f"`{row.severity}` |"
            ),
            queue_row.open_command,
            queue_row.report_recorder_command,
            queue_row.intake_recorder_command,
        )
    )
    if not row_markers:
        row_markers = ("| `ready-for-manual-evidence` | `none` | 0 |",)
    checks = (
        _build_presence_check(
            area="UX Recording Queue Metadata",
            text=text,
            markers=metadata_markers,
            summary="The UX recording queue metadata matches the current sprint.",
        ),
        _build_presence_check(
            area="Operator Order",
            text=text,
            markers=(
                "Open the route command first and inspect the real visible output.",
                "Record report notes only after observing readability, controls, and motion.",
                (
                    "Record the UX issue intake row from the same observation before "
                    "rebuilding plans."
                ),
                "Re-run the refresh commands after each completed row or blocker fix.",
            ),
            summary="The queue states the manual order before recorder commands.",
        ),
        _build_presence_check(
            area="Refresh Commands",
            text=text,
            markers=command_markers,
            summary="The queue includes current intake, fix plan, sprint, and report commands.",
        ),
        _build_presence_check(
            area="Recording Queue Rows",
            text=text,
            markers=row_markers,
            summary="The queue lists every open UX recording row with recorder commands.",
        ),
        _build_presence_check(
            area="Exit Criteria",
            text=text,
            markers=(
                "Every queued route has real report notes recorded after visible play.",
                "Every queued intake row is no longer `todo` after the same observation.",
                "P0/P1 rows are fixed, reopened, and reclassified before UI signoff.",
                "Intake, fix plan, sprint, queue, and report validators pass after updates.",
            ),
            summary="The queue keeps completion gates visible.",
        ),
        _build_presence_check(
            area="No-Fabrication Guardrail",
            text=text,
            markers=(
                "This recording queue is not evidence; it only orders the manual work.",
                "Do not run recorder commands until the corresponding route was opened.",
                (
                    "Do not use `pass`, `none`, or lower severity unless the observation "
                    "supports it."
                ),
            ),
            summary="The queue keeps no-fabrication guardrails visible.",
        ),
    )
    return OnboardingVisibleUxRecordingQueueValidation(
        queue_path=queue_path,
        status="pass" if all(check.status == "pass" for check in checks) else "fail",
        checks=checks,
    )


def build_onboarding_visible_ux_progress_board(
    queue_path: Path,
    *,
    sprint_path: Path,
    plan_path: Path,
    intake_path: Path,
    report_path: Path,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleUxProgressBoard:
    """Build a progress board from the current UX report, intake, and queue."""

    queue_validation = validate_onboarding_visible_ux_recording_queue(
        queue_path,
        sprint_path=sprint_path,
        plan_path=plan_path,
        intake_path=intake_path,
        report_path=report_path,
        command_prefix=command_prefix,
    )
    if not queue_validation.ok:
        failed = ", ".join(check.area for check in queue_validation.failed_checks)
        raise ValueError(f"UX recording queue must validate before progress board: {failed}")

    report = read_onboarding_visible_playtest_evidence_report(report_path)
    plan = build_onboarding_visible_ux_fix_plan(
        intake_path,
        report_path=report_path,
        command_prefix=command_prefix,
    )
    queue = build_onboarding_visible_ux_recording_queue(
        sprint_path,
        plan_path=plan_path,
        intake_path=intake_path,
        report_path=report_path,
        command_prefix=command_prefix,
    )
    report_complete_count = len(report.rows) - len(report.incomplete_rows)
    intake_classified_count = plan.p0_count + plan.p1_count + plan.p2_count + plan.none_count
    if plan.p0_count or plan.p1_count:
        status = "fix-required"
    elif plan.todo_count or report.incomplete_rows:
        status = "manual-required"
    elif plan.p2_count:
        status = "polish-ready"
    else:
        status = "ready-for-signoff"

    return OnboardingVisibleUxProgressBoard(
        report_path=report_path,
        intake_path=intake_path,
        plan_path=plan_path,
        sprint_path=sprint_path,
        queue_path=queue_path,
        status=status,
        total_rows=len(report.rows),
        report_complete_count=report_complete_count,
        report_incomplete_count=len(report.incomplete_rows),
        intake_classified_count=intake_classified_count,
        intake_todo_count=plan.todo_count,
        blocker_count=plan.p0_count + plan.p1_count,
        queue_count=queue.total_rows,
        next_row=queue.rows[0] if queue.rows else None,
        validate_report_command=(
            f"{command_prefix} validate-onboarding-visible-playtest-report --report {report_path}"
        ),
        validate_intake_command=(
            f"{command_prefix} validate-onboarding-visible-ux-issue-intake "
            f"--report {report_path} --input {intake_path}"
        ),
        rebuild_queue_command=(
            f"{command_prefix} onboarding-visible-ux-recording-queue "
            f"--report {report_path} --intake {intake_path} --plan {plan_path} "
            f"--sprint {sprint_path} --output {queue_path}"
        ),
        validate_queue_command=(
            f"{command_prefix} validate-onboarding-visible-ux-recording-queue "
            f"--report {report_path} --intake {intake_path} --plan {plan_path} "
            f"--sprint {sprint_path} --input {queue_path}"
        ),
        status_command=(
            f"{command_prefix} onboarding-visible-playtest-status --report {report_path}"
        ),
    )


def write_onboarding_visible_ux_progress_board(
    progress: OnboardingVisibleUxProgressBoard,
    output_path: Path,
) -> None:
    """Write the visible UX progress board without marking evidence complete."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NEXUS TECH Onboarding Visible UX Progress",
        "",
        f"- Report: `{progress.report_path}`",
        f"- Intake: `{progress.intake_path}`",
        f"- Fix Plan: `{progress.plan_path}`",
        f"- Sprint: `{progress.sprint_path}`",
        f"- Queue: `{progress.queue_path}`",
        f"- Status: `{progress.status}`",
        f"- Rows: `{progress.total_rows}`",
        f"- Completion: `{progress.completion_percent}%`",
        f"- Report Complete: `{progress.report_complete_count}`",
        f"- Report Incomplete: `{progress.report_incomplete_count}`",
        f"- Intake Classified: `{progress.intake_classified_count}`",
        f"- Intake Todo: `{progress.intake_todo_count}`",
        f"- Blockers: `{progress.blocker_count}`",
        f"- Queue Rows: `{progress.queue_count}`",
        "- Manual result: `not completed by automation`",
        "- Evidence policy: `progress is derived from report/intake rows only`",
        "",
        "## Progress Lanes",
        "",
        "| Lane | Done | Open | Gate |",
        "| --- | ---: | ---: | --- |",
        (
            f"| `report evidence` | {progress.report_complete_count} | "
            f"{progress.report_incomplete_count} | `real visible-window notes required` |"
        ),
        (
            f"| `ux intake` | {progress.intake_classified_count} | "
            f"{progress.intake_todo_count} | `todo must become P0/P1/P2/none` |"
        ),
        (
            f"| `blockers` | {progress.total_rows - progress.blocker_count} | "
            f"{progress.blocker_count} | `P0/P1 must be fixed and reopened` |"
        ),
        (
            f"| `recording queue` | {progress.total_rows - progress.queue_count} | "
            f"{progress.queue_count} | `queue must be empty before signoff` |"
        ),
        "",
        "## Next Manual Action",
        "",
    ]
    if progress.next_row is None:
        lines.extend(
            [
                "- Next row: `none`",
                "- Action: validate report, intake, queue, and prepare final signoff.",
            ]
        )
    else:
        row = progress.next_row.row
        lines.extend(
            [
                f"- Phase: `{progress.next_row.phase}`",
                f"- Priority: `{progress.next_row.priority}`",
                f"- Rank: `{row.rank}`",
                f"- Route: `{row.route}`",
                f"- Window: `{row.window}`",
                f"- Motion: `{row.motion_mode}`",
                f"- Severity: `{row.severity}`",
                "",
                "Open command:",
                "",
                "```bash",
                progress.next_row.open_command,
                "```",
                "",
                "Report recorder:",
                "",
                "```bash",
                progress.next_row.report_recorder_command,
                "```",
                "",
                "UX intake recorder:",
                "",
                "```bash",
                progress.next_row.intake_recorder_command,
                "```",
            ]
        )
    lines.extend(
        [
            "",
            "## Refresh Commands",
            "",
            "```bash",
            progress.validate_report_command,
            progress.validate_intake_command,
            progress.rebuild_queue_command,
            progress.validate_queue_command,
            progress.status_command,
            "```",
            "",
            "## Exit Criteria",
            "",
            "- Report incomplete count is zero after real visible-window notes are recorded.",
            "- Intake todo count is zero after matching UX severity is recorded.",
            "- Blocker count is zero after P0/P1 rows are fixed and reopened.",
            "- Queue rows are zero before final onboarding UX signoff.",
            "",
            "## No-Fabrication Guardrail",
            "",
            "- This progress board is not evidence; it only summarizes recorded rows.",
            "- Do not reduce counts manually; update report and intake with recorder commands.",
            "- Keep status manual-required until real visible-window evidence closes the rows.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_onboarding_visible_ux_progress_board(
    progress_path: Path,
    *,
    queue_path: Path,
    sprint_path: Path,
    plan_path: Path,
    intake_path: Path,
    report_path: Path,
    command_prefix: str = "uv run nexus-tech",
) -> OnboardingVisibleUxProgressBoardValidation:
    """Validate the visible UX progress board against the current queue."""

    try:
        expected = build_onboarding_visible_ux_progress_board(
            queue_path,
            sprint_path=sprint_path,
            plan_path=plan_path,
            intake_path=intake_path,
            report_path=report_path,
            command_prefix=command_prefix,
        )
    except (OSError, ValueError) as error:
        return OnboardingVisibleUxProgressBoardValidation(
            progress_path=progress_path,
            status="fail",
            checks=(
                _build_check(
                    area="Source Queue",
                    passed=False,
                    summary="The UX recording queue must validate before progress.",
                    evidence=(str(error),),
                ),
            ),
        )
    if not progress_path.exists():
        return OnboardingVisibleUxProgressBoardValidation(
            progress_path=progress_path,
            status="fail",
            checks=(
                _build_check(
                    area="UX Progress File",
                    passed=False,
                    summary="The onboarding visible UX progress board file must exist.",
                    evidence=(f"missing:{progress_path}",),
                ),
            ),
        )

    text = progress_path.read_text(encoding="utf-8")
    metadata_markers = (
        "# NEXUS TECH Onboarding Visible UX Progress",
        f"- Report: `{expected.report_path}`",
        f"- Intake: `{expected.intake_path}`",
        f"- Fix Plan: `{expected.plan_path}`",
        f"- Sprint: `{expected.sprint_path}`",
        f"- Queue: `{expected.queue_path}`",
        f"- Status: `{expected.status}`",
        f"- Rows: `{expected.total_rows}`",
        f"- Completion: `{expected.completion_percent}%`",
        f"- Report Complete: `{expected.report_complete_count}`",
        f"- Report Incomplete: `{expected.report_incomplete_count}`",
        f"- Intake Classified: `{expected.intake_classified_count}`",
        f"- Intake Todo: `{expected.intake_todo_count}`",
        f"- Blockers: `{expected.blocker_count}`",
        f"- Queue Rows: `{expected.queue_count}`",
        "- Manual result: `not completed by automation`",
        "- Evidence policy: `progress is derived from report/intake rows only`",
    )
    command_markers = (
        expected.validate_report_command,
        expected.validate_intake_command,
        expected.rebuild_queue_command,
        expected.validate_queue_command,
        expected.status_command,
    )
    next_markers: tuple[str, ...]
    if expected.next_row is None:
        next_markers = ("- Next row: `none`",)
    else:
        row = expected.next_row.row
        next_markers = (
            f"- Phase: `{expected.next_row.phase}`",
            f"- Rank: `{row.rank}`",
            f"- Route: `{row.route}`",
            expected.next_row.open_command,
            expected.next_row.report_recorder_command,
            expected.next_row.intake_recorder_command,
        )
    checks = (
        _build_presence_check(
            area="UX Progress Metadata",
            text=text,
            markers=metadata_markers,
            summary="The UX progress metadata matches the current report, intake, and queue.",
        ),
        _build_presence_check(
            area="Progress Lanes",
            text=text,
            markers=(
                "| `report evidence` |",
                "| `ux intake` |",
                "| `blockers` |",
                "| `recording queue` |",
            ),
            summary="The progress board lists report, intake, blocker, and queue lanes.",
        ),
        _build_presence_check(
            area="Next Manual Action",
            text=text,
            markers=next_markers,
            summary="The progress board exposes the next row and recorder commands.",
        ),
        _build_presence_check(
            area="Refresh Commands",
            text=text,
            markers=command_markers,
            summary="The progress board includes current validation and rebuild commands.",
        ),
        _build_presence_check(
            area="Exit Criteria",
            text=text,
            markers=(
                "Report incomplete count is zero after real visible-window notes are recorded.",
                "Intake todo count is zero after matching UX severity is recorded.",
                "Blocker count is zero after P0/P1 rows are fixed and reopened.",
                "Queue rows are zero before final onboarding UX signoff.",
            ),
            summary="The progress board keeps closure gates visible.",
        ),
        _build_presence_check(
            area="No-Fabrication Guardrail",
            text=text,
            markers=(
                "This progress board is not evidence; it only summarizes recorded rows.",
                "Do not reduce counts manually; update report and intake with recorder commands.",
                ("Keep status manual-required until real visible-window evidence closes the rows."),
            ),
            summary="The progress board keeps no-fabrication guardrails visible.",
        ),
    )
    return OnboardingVisibleUxProgressBoardValidation(
        progress_path=progress_path,
        status="pass" if all(check.status == "pass" for check in checks) else "fail",
        checks=checks,
    )


def read_onboarding_visible_playtest_evidence_report(
    report_path: Path,
) -> OnboardingVisiblePlaytestEvidenceReport:
    """Read a Markdown onboarding visible QA report."""

    text = report_path.read_text(encoding="utf-8")
    packet_path = Path(_extract_backtick_metadata(text, "Packet"))
    rows = tuple(_parse_onboarding_visible_report_row(line) for line in text.splitlines())
    rows = tuple(row for row in rows if row is not None)
    if not rows:
        raise ValueError("Onboarding visible playtest report has no evidence rows.")
    return OnboardingVisiblePlaytestEvidenceReport(
        packet_path=packet_path,
        rows=rows,
    )


def _build_check(
    *,
    area: str,
    passed: bool,
    summary: str,
    evidence: tuple[str, ...],
) -> OnboardingFlowAuditCheck:
    return OnboardingFlowAuditCheck(
        area=area,
        status="pass" if passed else "fail",
        summary=summary,
        evidence=evidence,
    )


def _build_presence_check(
    *,
    area: str,
    text: str,
    markers: tuple[str, ...],
    summary: str,
) -> OnboardingFlowAuditCheck:
    missing = tuple(marker for marker in markers if marker not in text)
    evidence = (
        (f"present:{len(markers)}",)
        if not missing
        else tuple(f"missing:{marker}" for marker in missing[:8])
    )
    if len(missing) > 8:
        evidence = (*evidence, f"missing-more:{len(missing) - 8}")
    return _build_check(
        area=area,
        passed=not missing,
        summary=summary,
        evidence=evidence,
    )


def _format_onboarding_visible_report_row(row: OnboardingVisiblePlaytestReportRow) -> str:
    return (
        "| "
        f"{row.rank} | "
        f"`{row.route}` | "
        f"`{row.window}` | "
        f"`{row.motion_mode}` | "
        f"`{_markdown_escape(row.command)}` | "
        f"`{row.result}` | "
        f"{_markdown_escape(row.evidence_notes)} | "
        f"{_markdown_escape(', '.join(row.required_evidence))} |"
    )


def _parse_onboarding_visible_report_row(
    line: str,
) -> OnboardingVisiblePlaytestReportRow | None:
    if not line.startswith("| "):
        return None
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    if len(cells) != 8 or not cells[0].isdigit():
        return None
    return OnboardingVisiblePlaytestReportRow(
        rank=int(cells[0]),
        route=_strip_backticks(cells[1]),
        window=_strip_backticks(cells[2]),
        motion_mode=_strip_backticks(cells[3]),
        command=_strip_backticks(cells[4]).replace("\\|", "|").strip(),
        result=_strip_backticks(cells[5]).lower(),
        evidence_notes=cells[6].replace("\\|", "|").strip(),
        required_evidence=tuple(
            item.strip() for item in cells[7].replace("\\|", "|").split(",") if item.strip()
        ),
    )


def _find_onboarding_visible_report_row(
    rows: tuple[OnboardingVisiblePlaytestReportRow, ...],
    *,
    rank: int | None,
    route: str | None,
    window: str | None,
    motion_mode: str | None,
) -> int:
    matches: list[int] = []
    for index, row in enumerate(rows):
        if rank is not None and row.rank != rank:
            continue
        if route is not None and row.route != route:
            continue
        if window is not None and row.window != window:
            continue
        if motion_mode is not None and row.motion_mode != motion_mode:
            continue
        matches.append(index)
    if not matches:
        raise ValueError("No onboarding visible report row matched the provided selector.")
    if len(matches) > 1:
        raise ValueError("Selector matched multiple onboarding visible report rows; add --rank.")
    return matches[0]


def _onboarding_visible_group_name(row: OnboardingVisiblePlaytestReportRow) -> str:
    return "terminal" if row.window == "terminal" else row.window


def _ordered_onboarding_visible_group_names(
    rows: tuple[OnboardingVisiblePlaytestReportRow, ...],
) -> tuple[str, ...]:
    default_windows = tuple(
        f"{width}x{height}" for width, height in DEFAULT_ONBOARDING_VISIBLE_WINDOWS
    )
    report_windows = tuple(dict.fromkeys(row.window for row in rows if row.window != "terminal"))
    ordered_windows = tuple(window for window in default_windows if window in report_windows)
    ordered_windows = (
        *ordered_windows,
        *(window for window in report_windows if window not in ordered_windows),
    )
    groups = []
    if any(row.window == "terminal" for row in rows):
        groups.append("terminal")
    groups.extend(ordered_windows)
    return tuple(groups)


def _build_onboarding_visible_evidence_matrix_group(
    report_path: Path,
    *,
    name: str,
    rows: tuple[OnboardingVisiblePlaytestReportRow, ...],
    command_prefix: str,
) -> OnboardingVisibleEvidenceMatrixGroup:
    return OnboardingVisibleEvidenceMatrixGroup(
        name=name,
        rows=rows,
        recorder_commands=tuple(
            _build_onboarding_visible_recorder_command(
                report_path,
                row,
                command_prefix=command_prefix,
            )
            for row in rows
        ),
        pass_count=sum(1 for row in rows if row.result == "pass"),
        watch_count=sum(1 for row in rows if row.result == "watch"),
        fail_count=sum(1 for row in rows if row.result == "fail"),
        todo_count=sum(1 for row in rows if row.result == "todo"),
        incomplete_count=sum(
            1
            for row in rows
            if row.result != "pass" or not _has_real_observation_notes(row.evidence_notes)
        ),
    )


def _build_terminal_observation_prompt(row: OnboardingVisiblePlaytestReportRow) -> str:
    return (
        "Confirm terminal output includes "
        f"{', '.join(row.required_evidence)}; notes must mention exact wording, "
        "readability, and whether the next player action is clear."
    )


def _build_window_observation_prompt(row: OnboardingVisiblePlaytestReportRow) -> str:
    return (
        f"Confirm {row.window} {row.route} in {row.motion_mode} mode: "
        "text containment, button spacing, pause/back/menu recovery, and motion readability "
        f"while checking {', '.join(row.required_evidence)}."
    )


def _onboarding_visible_ux_issue_areas(row: OnboardingVisiblePlaytestReportRow) -> str:
    if row.window == "terminal":
        return "copy/readability/navigation"
    return "text containment/button spacing/pause-back-menu/motion readability"


def _parse_onboarding_visible_ux_issue_row(
    line: str,
) -> OnboardingVisibleUxFixPlanRow | None:
    if not line.startswith("| `"):
        return None
    cells = _split_markdown_table_cells(line)
    if len(cells) != 11 or not cells[1].isdigit():
        return None
    severity = _normalize_onboarding_visible_ux_severity(_strip_backticks(cells[8]))
    return OnboardingVisibleUxFixPlanRow(
        group=_strip_backticks(cells[0]),
        rank=int(cells[1]),
        route=_strip_backticks(cells[2]),
        window=_strip_backticks(cells[3]),
        motion_mode=_strip_backticks(cells[4]),
        result=_strip_backticks(cells[5]),
        command=_strip_backticks(cells[6]).replace("\\|", "|").strip(),
        ux_areas=_strip_backticks(cells[7]).replace("\\|", "|").strip(),
        severity=severity,
        issue_notes=_strip_backticks(cells[9]).replace("\\|", "|").strip(),
        follow_up=_strip_backticks(cells[10]).replace("\\|", "|").strip(),
    )


def _split_markdown_table_cells(line: str) -> list[str]:
    cells: list[str] = []
    cell: list[str] = []
    for character in line.strip().strip("|"):
        if character == "|" and (not cell or cell[-1] != "\\"):
            cells.append("".join(cell).strip())
            cell = []
            continue
        cell.append(character)
    cells.append("".join(cell).strip())
    return cells


def _format_onboarding_visible_ux_issue_row(row: OnboardingVisibleUxFixPlanRow) -> str:
    return (
        "| "
        f"`{row.group}` | "
        f"{row.rank} | "
        f"`{row.route}` | "
        f"`{row.window}` | "
        f"`{row.motion_mode}` | "
        f"`{row.result}` | "
        f"`{_markdown_escape(row.command)}` | "
        f"`{_markdown_escape(row.ux_areas)}` | "
        f"`{row.severity}` | "
        f"`{_markdown_escape(row.issue_notes)}` | "
        f"`{_markdown_escape(row.follow_up)}` |"
    )


def _find_onboarding_visible_ux_issue_row(
    rows: tuple[tuple[int, OnboardingVisibleUxFixPlanRow], ...],
    *,
    rank: int | None,
    route: str | None,
    window: str | None,
    motion_mode: str | None,
) -> tuple[int, OnboardingVisibleUxFixPlanRow]:
    matches: list[tuple[int, OnboardingVisibleUxFixPlanRow]] = []
    for index, row in rows:
        if rank is not None and row.rank != rank:
            continue
        if route is not None and row.route != route:
            continue
        if window is not None and row.window != window:
            continue
        if motion_mode is not None and row.motion_mode != motion_mode:
            continue
        matches.append((index, row))
    if not matches:
        raise ValueError("No onboarding visible UX issue intake row matched the selector.")
    if len(matches) > 1:
        raise ValueError("Selector matched multiple UX issue rows; add --rank.")
    return matches[0]


def _normalize_onboarding_visible_ux_severity(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"p0", "0", "blocker"}:
        return "P0"
    if normalized in {"p1", "1", "high"}:
        return "P1"
    if normalized in {"p2", "2", "polish"}:
        return "P2"
    if normalized in {"none", "no issue", "no-issue", "clear"}:
        return "none"
    return "todo"


def _onboarding_visible_ux_fix_priority(row: OnboardingVisibleUxFixPlanRow) -> str:
    if row.severity == "P0":
        return "blocker"
    if row.severity == "P1":
        return "high"
    if row.severity == "P2":
        return "polish"
    if row.severity == "none":
        return "no-issue"
    return "triage"


def _onboarding_visible_ux_sprint_sort_key(
    row: OnboardingVisibleUxFixPlanRow,
) -> tuple[int, int, int]:
    severity_order = {"P0": 0, "P1": 1, "todo": 2, "P2": 3, "none": 4}
    group_order = {"terminal": 0, "820x620": 1, "1280x720": 2, "1440x900": 3}
    return (
        severity_order.get(row.severity, 5),
        group_order.get(row.group, 9),
        row.rank,
    )


def _onboarding_visible_ux_sprint_phase(row: OnboardingVisibleUxFixPlanRow) -> str:
    if row.severity in {"P0", "P1"}:
        return "fix-before-signoff"
    if row.severity == "todo":
        return "triage-visible"
    if row.severity == "P2":
        return "polish-backlog"
    return "evidence-confirm"


def _onboarding_visible_ux_sprint_step(row: OnboardingVisibleUxFixPlanRow) -> str:
    if row.severity in {"P0", "P1"}:
        return (
            "Fix the observed UX blocker, reopen this route, then update report notes "
            "and regenerate the intake/fix plan."
        )
    if row.severity == "todo":
        return (
            "Open this route in the real visible window, classify severity, and replace "
            "placeholder issue notes before coding."
        )
    if row.severity == "P2":
        return (
            "Keep as polish backlog after P0/P1 are closed, then verify the row still "
            "has real visible notes."
        )
    return (
        "Confirm report evidence remains real and keep this row as no-issue unless a "
        "new visible defect appears."
    )


def _build_onboarding_visible_ux_recording_queue_row(
    row: OnboardingVisibleUxFixPlanRow,
    *,
    report_path: Path,
    intake_path: Path,
    command_prefix: str,
) -> OnboardingVisibleUxRecordingQueueRow:
    severity_hint = row.severity if row.severity in {"P0", "P1", "P2"} else "P1"
    return OnboardingVisibleUxRecordingQueueRow(
        row=row,
        phase=_onboarding_visible_ux_sprint_phase(row),
        priority=_onboarding_visible_ux_fix_priority(row),
        open_command=row.command,
        report_recorder_command=(
            f"{command_prefix} record-onboarding-visible-playtest-route "
            f"--report {report_path} --rank {row.rank} --result watch "
            f'--notes "<replace with observed visible-window notes mentioning '
            f'{row.ux_areas}>"'
        ),
        intake_recorder_command=(
            f"{command_prefix} record-onboarding-visible-ux-issue "
            f"--input {intake_path} --rank {row.rank} --severity {severity_hint} "
            f'--issue-notes "<replace with observed UX issue or no-issue notes '
            f'mentioning {row.ux_areas}>" --follow-up "owner/date or none"'
        ),
    )


def _build_onboarding_visible_recorder_command(
    report_path: Path,
    row: OnboardingVisiblePlaytestReportRow,
    *,
    command_prefix: str,
) -> str:
    return (
        f"{command_prefix} record-onboarding-visible-playtest-route "
        f"--report {report_path} "
        f"--rank {row.rank} "
        "--result pass "
        f'--notes "{ONBOARDING_VISIBLE_NOTE_PLACEHOLDER}"'
    )


def _extract_backtick_metadata(text: str, label: str) -> str:
    prefix = f"- {label}: `"
    for line in text.splitlines():
        if line.startswith(prefix) and line.endswith("`"):
            return line[len(prefix) : -1]
    raise ValueError(f"missing metadata line: {label}")


def _strip_backticks(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`"):
        return value[1:-1]
    return value


def _has_real_observation_notes(notes: str) -> bool:
    normalized = " ".join(notes.strip().lower().split())
    if len(normalized) < 30:
        return False
    if ONBOARDING_VISIBLE_NOTE_PLACEHOLDER.strip("<>").lower() in normalized:
        return False
    if any(term in normalized for term in ("<replace", "placeholder", "todo", "tbd")):
        return False
    return normalized not in _GENERIC_NOTE_TERMS


def _safe_first_actions_present(commands: tuple[str, ...]) -> bool:
    return (
        len(commands) >= 6
        and commands[0] == TurnAction.HIRE_EMPLOYEE.value
        and commands[1] == TurnAction.ASSIGN_EMPLOYEE.value
        and (
            TurnAction.IMPROVE_QUALITY.value in commands[:4]
            or TurnAction.MARKET_PRODUCT.value in commands[:4]
        )
        and TurnAction.END_TURN.value in commands[:5]
        and TurnAction.VIEW_REPORT.value in commands[:6]
    )


def _is_clear_copy(*values: str) -> bool:
    normalized = " ".join(value.strip().lower() for value in values if value.strip())
    return bool(normalized) and not any(term in normalized for term in _PLACEHOLDER_TERMS)


def _is_clear_follow_up(value: str) -> bool:
    normalized = " ".join(value.strip().lower().split())
    if normalized == "none":
        return True
    return len(normalized) >= 4 and not any(term in normalized for term in _PLACEHOLDER_TERMS)


def _markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
