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
DEFAULT_ONBOARDING_VISIBLE_WINDOWS: tuple[tuple[int, int], ...] = (
    (820, 620),
    (1280, 720),
    (1440, 900),
)
DEFAULT_ONBOARDING_VISIBLE_MOTION_MODES: tuple[str, ...] = ("full", "reduced", "off")
_PLACEHOLDER_TERMS = ("todo", "placeholder", "tbd", "unknown")


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
