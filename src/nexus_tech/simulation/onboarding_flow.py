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


def _markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
