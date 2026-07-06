"""Automated first-time player clarity checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nexus_tech.config import DEFAULT_SCENARIO_ID
from nexus_tech.domain.models import DifficultyMode, TurnAction
from nexus_tech.simulation.campaign_starts import STANDARD_CAMPAIGN_START_ID
from nexus_tech.simulation.engine import create_new_game
from nexus_tech.simulation.opening_guide import build_guided_opening
from nexus_tech.simulation.risk_forecast import build_risk_forecast
from nexus_tech.simulation.turn_coach import build_turn_coach

ONBOARDING_FLOW_AUDIT_REPORT_NAME = "onboarding-flow-audit.md"
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
