"""Terminal-state postmortem and after-action review summaries."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import GameState, TurnAction
from nexus_tech.simulation.endgame import calculate_endgame_pressure, calculate_endgame_readiness
from nexus_tech.simulation.finance import build_finance_planner
from nexus_tech.simulation.partnerships import calculate_partnership_portfolio
from nexus_tech.simulation.reporting import calculate_run_score
from nexus_tech.simulation.risk_forecast import build_risk_forecast
from nexus_tech.simulation.support_program import (
    calculate_support_account_risk_values,
    calculate_support_queue_exposure,
)


@dataclass(frozen=True)
class PostmortemFinding:
    """One ranked takeaway from a finished run."""

    rank: int
    area: str
    severity: str
    summary: str
    command: str
    lesson: str


@dataclass(frozen=True)
class PostmortemSummary:
    """Compact postmortem for game-over and victory states."""

    title: str
    headline: str
    next_run_focus: str
    findings: tuple[PostmortemFinding, ...]


def build_run_postmortem(state: GameState) -> PostmortemSummary:
    """Build a ranked postmortem from the terminal state."""

    forecast = build_risk_forecast(state)
    run_score = calculate_run_score(state)
    readiness = calculate_endgame_readiness(state, run_score)
    pressure = calculate_endgame_pressure(state, readiness)
    queue_exposure = calculate_support_queue_exposure(state)
    portfolio = calculate_partnership_portfolio(state)
    revenue_at_risk_value, renewal_pressure_value = calculate_support_account_risk_values(state)
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=_latest_net_cash_flow(state),
        capital_plan=state.capital_plan,
        support_backlog=state.support_program.backlog_queue,
        support_escalations=state.support_program.escalation_queue,
        revenue_at_risk_value=revenue_at_risk_value,
        renewal_pressure_value=renewal_pressure_value,
        channel_conflict_index=portfolio.channel_conflict_index,
        channel_dependency_risk=portfolio.channel_dependency_risk,
        commercial_dependency_score=portfolio.commercial_dependency_score,
        volatile_revenue_share_percent=portfolio.volatile_revenue_share_percent,
        enterprise_queue_exposure_value=queue_exposure.enterprise_queue_exposure_value,
        renewal_queue_exposure_value=queue_exposure.renewal_queue_exposure_value,
        enterprise_queue_risk_accounts=queue_exposure.enterprise_queue_risk_accounts,
        renewal_queue_risk_accounts=queue_exposure.renewal_queue_risk_accounts,
        premium_queue_risk_accounts=queue_exposure.premium_queue_risk_accounts,
        support_lane_saturation_index=queue_exposure.lane_saturation_index,
        support_lane_focus=state.support_program.lane_focus,
        support_hotspot_lane=queue_exposure.hotspot_lane,
        support_hotspot_lane_overflow=queue_exposure.hotspot_lane_overflow,
        hotspot_lane_account_count=queue_exposure.hotspot_lane_account_count,
        focus_alignment_gap=queue_exposure.focus_alignment_gap,
        recovery_drag_score=portfolio.recovery_drag_score,
        paused_dependency_score=portfolio.paused_dependency_score,
        paused_revenue_share_percent=portfolio.paused_revenue_share_percent,
        hotspot_dependency_score=portfolio.hotspot_dependency_score,
        hotspot_revenue_share_percent=portfolio.hotspot_revenue_share_percent,
        hotspot_channel=portfolio.hotspot_channel,
        hotspot_status_note=portfolio.hotspot_status_note,
        strategic_outlook=readiness.strategic_outlook,
        dominant_endgame_pressure=pressure.dominant_pressure,
        commercial_fragility=pressure.commercial_fragility,
        capital_fragility=pressure.capital_fragility,
    )
    findings: list[PostmortemFinding] = []

    if state.company.game_over and state.company.cash_on_hand < Decimal("0.00"):
        findings.append(
            PostmortemFinding(
                rank=0,
                area="finance",
                severity="critical",
                summary=(
                    f"Cash closed at {state.company.cash_on_hand}, so the company shut down before "
                    "the next control move could land."
                ),
                command=(
                    planner.recommended_actions[0]
                    if planner.recommended_actions
                    else TurnAction.REVIEW_FINANCE.value
                ),
                lesson=f"{planner.capital_alert} {planner.reserve_plan}",
            )
        )

    if state.finance.board_resolution_due or state.finance.governance_risk >= 58:
        findings.append(
            PostmortemFinding(
                rank=0,
                area="board",
                severity="high" if state.company.game_over else "watch",
                summary=(
                    "Board pressure stayed unresolved long enough to distort capital and "
                    "execution choices."
                ),
                command=(
                    TurnAction.EXECUTE_BOARD_RESPONSE.value
                    if state.finance.board_resolution_due
                    else TurnAction.START_BOARD_RECOVERY_PLAN.value
                ),
                lesson=(
                    f"Governance risk {state.finance.governance_risk} and board pressure "
                    f"{state.finance.board_pressure} need earlier intervention."
                ),
            )
        )

    for item in forecast.items[:3]:
        findings.append(
            PostmortemFinding(
                rank=0,
                area=item.area,
                severity=item.severity,
                summary=item.summary,
                command=item.command,
                lesson=item.consequence,
            )
        )

    ranked = _rank_findings(findings)
    if state.company.game_over:
        title = "Failure Postmortem"
        headline = "The run collapsed because one or more pressure lanes outran the control loop."
    else:
        title = "After-Action Review"
        headline = "The run ended well enough, but these were the strains closest to breaking."
    next_run_focus = ranked[0].command if ranked else TurnAction.VIEW_REPORT.value
    return PostmortemSummary(
        title=title,
        headline=headline,
        next_run_focus=next_run_focus,
        findings=ranked,
    )


def _rank_findings(findings: list[PostmortemFinding]) -> tuple[PostmortemFinding, ...]:
    best_by_area: dict[str, PostmortemFinding] = {}
    for finding in findings:
        current = best_by_area.get(finding.area)
        if current is None or _severity_score(finding.severity) > _severity_score(current.severity):
            best_by_area[finding.area] = finding
    ordered = sorted(
        best_by_area.values(),
        key=lambda finding: _severity_score(finding.severity),
        reverse=True,
    )
    return tuple(
        PostmortemFinding(
            rank=index,
            area=finding.area,
            severity=finding.severity,
            summary=finding.summary,
            command=finding.command,
            lesson=finding.lesson,
        )
        for index, finding in enumerate(ordered[:3], start=1)
    )


def _severity_score(severity: str) -> int:
    return {"critical": 4, "high": 3, "elevated": 2, "watch": 1}.get(severity, 0)


def _latest_net_cash_flow(state: GameState) -> Decimal:
    if not state.turn_history:
        return Decimal("0.00")
    return state.turn_history[-1].net_cash_flow
