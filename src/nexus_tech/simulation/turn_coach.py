"""Turn-level recommendation board derived from current operating pressure."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.constants import ZERO_MONEY
from nexus_tech.domain.models import GameState, SupportLaneFocus, TurnAction
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.endgame import calculate_endgame_pressure, calculate_endgame_readiness
from nexus_tech.simulation.finance import build_finance_planner
from nexus_tech.simulation.opening_guide import build_guided_opening
from nexus_tech.simulation.partnerships import calculate_partnership_portfolio
from nexus_tech.simulation.reporting import calculate_run_score
from nexus_tech.simulation.support_program import (
    calculate_support_account_risk_counts,
    calculate_support_account_risk_values,
    calculate_support_queue_exposure,
)


@dataclass(frozen=True)
class TurnCoachRecommendation:
    """One ranked command the player can act on this turn."""

    rank: int
    command: str
    title: str
    rationale: str
    source: str
    urgency: int
    horizon_turns: int
    consequence: str


@dataclass(frozen=True)
class TurnCoachSummary:
    """Compact mission board for the current turn."""

    primary_command: str
    focus: str
    recommendations: tuple[TurnCoachRecommendation, ...]
    mission_window: str
    opening_command: str
    gate_command: str
    finance_command: str
    support_command: str
    channel_command: str
    summary: str


def build_turn_coach(state: GameState) -> TurnCoachSummary:
    """Build a short, command-oriented mission board from the current game state."""

    run_score = calculate_run_score(state)
    readiness = calculate_endgame_readiness(state, run_score)
    pressure = calculate_endgame_pressure(state, readiness)
    queue_exposure = calculate_support_queue_exposure(state)
    portfolio = calculate_partnership_portfolio(state)
    opening = build_guided_opening(state)
    revenue_at_risk_value, renewal_pressure_value = calculate_support_account_risk_values(state)
    revenue_at_risk_accounts, renewal_pressure_accounts = calculate_support_account_risk_counts(
        state
    )
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

    gate_command = pressure.path_gate_command_alert
    finance_command = (
        planner.recommended_actions[0]
        if planner.recommended_actions
        else TurnAction.REVIEW_FINANCE.value
    )
    opening_command = opening.current_command
    support_command = _choose_support_command(state, queue_exposure)
    channel_command = _choose_channel_command(portfolio)

    current_opening_step = next(
        (
            step
            for step in opening.steps
            if step.command == opening.current_command and step.status != "done"
        ),
        opening.steps[0],
    )
    candidates: list[TurnCoachRecommendation] = [
        TurnCoachRecommendation(
            rank=0,
            command=gate_command,
            title="Clear the most exposed endgame gate",
            rationale=pressure.path_gate_alert,
            source="endgame",
            urgency=_gate_urgency(pressure.path_gate_alert),
            horizon_turns=1 if _gate_urgency(pressure.path_gate_alert) >= 90 else 2,
            consequence=(
                pressure.path_watchlist[0]
                if pressure.path_watchlist
                else "Blocked exit paths stay closed until the gate is repaired."
            ),
        ),
        TurnCoachRecommendation(
            rank=0,
            command=finance_command,
            title="Follow the capital planner",
            rationale=planner.action_sequence[0] if planner.action_sequence else planner.summary,
            source="finance",
            urgency=_finance_urgency(planner.reserve_break_risk, planner.capital_priority),
            horizon_turns=_finance_horizon(planner.reserve_break_risk),
            consequence=f"{planner.capital_alert} {planner.reserve_plan}",
        ),
        TurnCoachRecommendation(
            rank=0,
            command=support_command,
            title="Stabilize the hottest support lane",
            rationale=_support_rationale(
                state,
                queue_exposure,
                revenue_at_risk_accounts=revenue_at_risk_accounts,
                renewal_pressure_accounts=renewal_pressure_accounts,
                revenue_at_risk_value=revenue_at_risk_value,
            ),
            source="support",
            urgency=_support_urgency(state, queue_exposure, revenue_at_risk_value),
            horizon_turns=_support_horizon(queue_exposure),
            consequence=_support_consequence(
                state,
                queue_exposure,
                revenue_at_risk_accounts=revenue_at_risk_accounts,
                revenue_at_risk_value=revenue_at_risk_value,
            ),
        ),
        TurnCoachRecommendation(
            rank=0,
            command=channel_command,
            title="De-risk channel dependency",
            rationale=_channel_rationale(portfolio),
            source="channel",
            urgency=_channel_urgency(portfolio),
            horizon_turns=_channel_horizon(portfolio),
            consequence=_channel_consequence(portfolio),
        ),
    ]
    if opening.active and opening_command not in {
        TurnAction.END_TURN.value,
        TurnAction.VIEW_REPORT.value,
    }:
        candidates.append(
            TurnCoachRecommendation(
                rank=0,
                command=opening_command,
                title=current_opening_step.title,
                rationale=current_opening_step.rationale,
                source="opening",
                urgency=_opening_urgency(state, opening_command),
                horizon_turns=1,
                consequence=_opening_consequence(state, current_opening_step.title),
            )
        )
    if state.finance.board_resolution_due or state.finance.governance_risk >= 52:
        candidates.append(
            TurnCoachRecommendation(
                rank=0,
                command=(
                    TurnAction.EXECUTE_BOARD_RESPONSE.value
                    if state.finance.board_resolution_due
                    else TurnAction.START_BOARD_RECOVERY_PLAN.value
                ),
                title="Resolve board pressure",
                rationale=(
                    "Board resolution is due now."
                    if state.finance.board_resolution_due
                    else "Governance heat is high enough to distort late-game options."
                ),
                source="board",
                urgency=88 if state.finance.board_resolution_due else 72,
                horizon_turns=1 if state.finance.board_resolution_due else 2,
                consequence=(
                    "Board heat can harden into restructuring pressure and narrow "
                    "financing options."
                ),
            )
        )

    ranked = _rank_recommendations(candidates)
    primary = ranked[0].command if ranked else TurnAction.VIEW_STATUS.value
    focus = ranked[0].title if ranked else "Review current status"
    mission_window = _build_mission_window(ranked)
    summary = (
        f"Work `{primary}` now, then line up "
        f"{', '.join(recommendation.command for recommendation in ranked[1:3]) or 'review status'} "
        f"over the {mission_window}."
    )
    return TurnCoachSummary(
        primary_command=primary,
        focus=focus,
        recommendations=ranked,
        mission_window=mission_window,
        opening_command=opening_command,
        gate_command=gate_command,
        finance_command=finance_command,
        support_command=support_command,
        channel_command=channel_command,
        summary=summary,
    )


def _rank_recommendations(
    candidates: list[TurnCoachRecommendation],
) -> tuple[TurnCoachRecommendation, ...]:
    best_by_command: dict[str, TurnCoachRecommendation] = {}
    for candidate in candidates:
        current = best_by_command.get(candidate.command)
        if current is None or candidate.urgency > current.urgency:
            best_by_command[candidate.command] = candidate
    ordered = sorted(
        best_by_command.values(),
        key=lambda item: (item.urgency, _source_priority(item.source)),
        reverse=True,
    )
    return tuple(
        TurnCoachRecommendation(
            rank=index,
            command=recommendation.command,
            title=recommendation.title,
            rationale=recommendation.rationale,
            source=recommendation.source,
            urgency=recommendation.urgency,
            horizon_turns=recommendation.horizon_turns,
            consequence=recommendation.consequence,
        )
        for index, recommendation in enumerate(ordered[:4], start=1)
    )


def _choose_support_command(state: GameState, queue_exposure) -> str:
    if queue_exposure.focus_alignment_gap > 0:
        return TurnAction.SET_SUPPORT_LANE_FOCUS.value
    if queue_exposure.enterprise_queue_risk_accounts > 0:
        return TurnAction.RUN_ENTERPRISE_QUEUE_RESET.value
    if queue_exposure.renewal_queue_risk_accounts > 0:
        return TurnAction.RUN_BILLING_RENEWAL_WATCH.value
    if queue_exposure.premium_queue_risk_accounts > 0:
        return TurnAction.RUN_WHITE_GLOVE_RECOVERY.value
    if state.support_program.escalation_queue > 0 or state.support_program.backlog_queue > 0:
        return TurnAction.TRIAGE_SUPPORT_BACKLOG.value
    if queue_exposure.hotspot_lane is SupportLaneFocus.ONBOARDING:
        return TurnAction.RUN_ONBOARDING_RECOVERY.value
    return TurnAction.REVIEW_CUSTOMERS.value


def _choose_channel_command(portfolio) -> str:
    if portfolio.paused_dependency_score >= BALANCE.finance_planner_reactivate_dependency_threshold:
        return TurnAction.REACTIVATE_PARTNERSHIP.value
    if (
        portfolio.hotspot_dependency_score
        >= BALANCE.finance_planner_reactivate_dependency_threshold
    ):
        return TurnAction.RUN_CHANNEL_DEPENDENCY_RESET.value
    if portfolio.channel_conflict_index >= BALANCE.finance_planner_channel_volatility_threshold:
        return TurnAction.RUN_CHANNEL_FIREBREAK.value
    if portfolio.recovery_ready_count > 0 or portfolio.recovery_drag_score > 0:
        return TurnAction.RUN_PARTNER_RECOVERY_SPRINT.value
    if portfolio.total_count > 0:
        return TurnAction.REVIEW_PARTNERSHIPS.value
    return TurnAction.CREATE_PARTNERSHIP.value


def _gate_urgency(gate_alert: str) -> int:
    return 92 if "blocked" in gate_alert or "action:" in gate_alert else 28


def _finance_urgency(reserve_break_risk: str, capital_priority: str) -> int:
    if reserve_break_risk == "critical":
        return 96
    if reserve_break_risk == "high":
        return 86
    if "board reset" in capital_priority:
        return 84
    if reserve_break_risk == "elevated":
        return 72
    return 52


def _finance_horizon(reserve_break_risk: str) -> int:
    if reserve_break_risk in {"critical", "high"}:
        return 1
    if reserve_break_risk == "elevated":
        return 2
    return 3


def _support_urgency(state: GameState, queue_exposure, revenue_at_risk_value: Decimal) -> int:
    urgency = 35
    urgency += min(35, queue_exposure.lane_saturation_index * 4)
    urgency += min(18, queue_exposure.severe_queue_accounts * 6)
    urgency += min(12, state.support_program.escalation_queue * 2)
    if revenue_at_risk_value > ZERO_MONEY:
        urgency += min(12, int(revenue_at_risk_value // Decimal("1000.00")))
    return min(98, urgency)


def _channel_urgency(portfolio) -> int:
    return min(
        95,
        30
        + min(30, portfolio.commercial_dependency_score // 2)
        + min(18, portfolio.channel_volatility_index // 2)
        + min(12, portfolio.paused_dependency_score // 8),
    )


def _support_horizon(queue_exposure) -> int:
    return 1 if queue_exposure.severe_queue_accounts > 0 else 2


def _channel_horizon(portfolio) -> int:
    return 2 if portfolio.total_count > 0 else 3


def _support_rationale(
    state: GameState,
    queue_exposure,
    *,
    revenue_at_risk_accounts: int,
    renewal_pressure_accounts: int,
    revenue_at_risk_value: Decimal,
) -> str:
    if queue_exposure.severe_queue_accounts > 0:
        return (
            f"{queue_exposure.hotspot_lane.value} support has "
            f"{queue_exposure.severe_queue_accounts} severe account(s), "
            f"{revenue_at_risk_accounts} revenue-risk account(s), and "
            f"{renewal_pressure_accounts} renewal-risk account(s)."
        )
    if state.support_program.backlog_queue > 0:
        return (
            f"Support backlog is {state.support_program.backlog_queue} with "
            f"{revenue_at_risk_value} revenue at risk."
        )
    return "Support pressure is controlled; keep the account review loop warm."


def _support_consequence(
    state: GameState,
    queue_exposure,
    *,
    revenue_at_risk_accounts: int,
    revenue_at_risk_value: Decimal,
) -> str:
    if queue_exposure.focus_alignment_gap > 0:
        return "Lane focus is mismatched, so backlog will keep compounding in the wrong queue."
    if queue_exposure.severe_queue_accounts > 0:
        return (
            f"{queue_exposure.severe_queue_accounts} severe support account(s) can spill into "
            "renewal drag and board heat."
        )
    if revenue_at_risk_accounts > 0:
        return f"{revenue_at_risk_accounts} account(s) are putting {revenue_at_risk_value} at risk."
    return "Support pressure can return quickly if the review loop goes cold."


def _channel_rationale(portfolio) -> str:
    if portfolio.total_count == 0:
        return "No active channel portfolio exists yet."
    return (
        f"{portfolio.hotspot_channel} is the hotspot with dependency "
        f"{portfolio.hotspot_dependency_score} and volatility "
        f"{portfolio.channel_volatility_index}."
    )


def _channel_consequence(portfolio) -> str:
    if portfolio.total_count == 0:
        return "No channel diversification exists yet, so direct demand must carry the run alone."
    return (
        f"{portfolio.channel_failure_mode}. {portfolio.channel_recovery_priority} is the next "
        "de-risking move."
    )


def _opening_urgency(state: GameState, opening_command: str) -> int:
    if state.company.current_turn == 1 and opening_command == TurnAction.HIRE_EMPLOYEE.value:
        return 90
    if opening_command == TurnAction.ASSIGN_EMPLOYEE.value:
        return 84
    if opening_command in {TurnAction.IMPROVE_QUALITY.value, TurnAction.MARKET_PRODUCT.value}:
        return 78
    return 66


def _opening_consequence(state: GameState, title: str) -> str:
    if not state.employees:
        return "The run stays underpowered until the first hire exists."
    if any(employee.assigned_product_id is None for employee in state.employees):
        return "Salary burn grows while execution still lacks a focused delivery loop."
    return f"Skipping `{title}` makes the first turns harder to read and harder to stabilize."


def _source_priority(source: str) -> int:
    priority = {
        "opening": 6,
        "endgame": 5,
        "finance": 4,
        "board": 3,
        "support": 2,
        "channel": 1,
    }
    return priority.get(source, 0)


def _build_mission_window(recommendations: tuple[TurnCoachRecommendation, ...]) -> str:
    if not recommendations:
        return "next turn"
    horizon = max(recommendation.horizon_turns for recommendation in recommendations[:3])
    return "next turn" if horizon <= 1 else f"next {horizon} turns"


def _latest_net_cash_flow(state: GameState) -> Decimal:
    if not state.turn_history:
        return Decimal("0.00")
    return state.turn_history[-1].net_cash_flow
