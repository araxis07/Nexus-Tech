"""Near-term operating risk forecast for live turns and reports."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.constants import ZERO_MONEY
from nexus_tech.domain.models import GameState, Product, TurnAction
from nexus_tech.domain.money import format_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.endgame import calculate_endgame_pressure, calculate_endgame_readiness
from nexus_tech.simulation.finance import (
    build_finance_planner,
    calculate_cash_flow_forecast_scenarios,
)
from nexus_tech.simulation.opening_guide import build_guided_opening
from nexus_tech.simulation.partnerships import calculate_partnership_portfolio
from nexus_tech.simulation.reporting import calculate_run_score
from nexus_tech.simulation.support_program import (
    calculate_support_account_risk_counts,
    calculate_support_account_risk_values,
    calculate_support_queue_exposure,
)
from nexus_tech.simulation.turn_coach import build_turn_coach


@dataclass(frozen=True)
class RiskForecastItem:
    """One forecasted near-term failure mode."""

    rank: int
    area: str
    severity: str
    command: str
    summary: str
    consequence: str
    horizon_turns: int


@dataclass(frozen=True)
class RiskForecastSummary:
    """Compact ranked risk summary for the next few turns."""

    headline: str
    overall_risk: str
    top_command: str
    items: tuple[RiskForecastItem, ...]


def build_risk_forecast(state: GameState) -> RiskForecastSummary:
    """Summarize the highest near-term risks if the run continues on its current path."""

    coach = build_turn_coach(state)
    opening = build_guided_opening(state)
    run_score = calculate_run_score(state)
    readiness = calculate_endgame_readiness(state, run_score)
    pressure = calculate_endgame_pressure(state, readiness)
    queue_exposure = calculate_support_queue_exposure(state)
    portfolio = calculate_partnership_portfolio(state)
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
    _, conservative_forecast, _ = calculate_cash_flow_forecast_scenarios(
        state.company.cash_on_hand,
        state.turn_history,
        latest_net_cash_flow=_latest_net_cash_flow(state),
        finance=state.finance,
        capital_plan=state.capital_plan,
    )
    flagship = _choose_flagship_product(state)

    candidates: list[tuple[int, str, str, str, str, int]] = []

    if opening.active and (
        not state.employees
        or any(employee.assigned_product_id is None for employee in state.employees)
    ):
        candidates.append(
            (
                84,
                "opening",
                coach.primary_command,
                "Early execution loop is still incomplete.",
                (
                    "The first turns will stay flat until the team is hired and focused on the "
                    "flagship product."
                ),
                1,
            )
        )

    if _finance_risk_active(planner, conservative_forecast.projected_runway_turns):
        runway_text = (
            "cashflow+"
            if conservative_forecast.projected_runway_turns is None
            else f"{conservative_forecast.projected_runway_turns} turn(s)"
        )
        candidates.append(
            (
                _finance_severity_score(
                    planner.reserve_break_risk,
                    conservative_forecast.projected_runway_turns,
                ),
                "finance",
                coach.finance_command,
                (
                    f"Conservative runway is {runway_text} with reserve risk "
                    f"`{planner.reserve_break_risk}`."
                ),
                f"{planner.capital_alert} {planner.reserve_plan}",
                1 if conservative_forecast.projected_runway_turns in {1, 2} else 2,
            )
        )

    if state.finance.board_resolution_due or state.finance.governance_risk >= 58:
        candidates.append(
            (
                95 if state.finance.board_resolution_due else 82,
                "board",
                (
                    TurnAction.EXECUTE_BOARD_RESPONSE.value
                    if state.finance.board_resolution_due
                    else TurnAction.START_BOARD_RECOVERY_PLAN.value
                ),
                (
                    "Board resolution is due now."
                    if state.finance.board_resolution_due
                    else f"Governance risk is {state.finance.governance_risk} and rising."
                ),
                (
                    "Board heat can turn into restructuring pressure and distort funding or "
                    "exit options."
                ),
                1,
            )
        )

    if (
        state.company.current_turn >= 10
        and pressure.path_gate_command_alert != TurnAction.VIEW_STATUS.value
        and ("blocked" in pressure.path_gate_alert or "action:" in pressure.path_gate_alert)
    ):
        candidates.append(
            (
                88,
                "endgame",
                coach.gate_command,
                pressure.path_gate_alert,
                (
                    pressure.path_watchlist[0]
                    if pressure.path_watchlist
                    else "Preferred endgame paths stay closed until the blocker is removed."
                ),
                2,
            )
        )

    if _support_risk_active(
        state,
        queue_exposure,
        revenue_at_risk_accounts,
        renewal_pressure_accounts,
    ):
        hotspot = queue_exposure.hotspot_lane.value if queue_exposure.hotspot_lane else "support"
        candidates.append(
            (
                _support_severity_score(state, queue_exposure, revenue_at_risk_value),
                "support",
                coach.support_command,
                (
                    f"{hotspot} pressure is spilling across "
                    f"{queue_exposure.hotspot_lane_account_count} hotspot account(s)."
                ),
                (
                    f"Revenue at risk is {format_money(revenue_at_risk_value)} with "
                    f"{revenue_at_risk_accounts} revenue-risk and "
                    f"{renewal_pressure_accounts} renewal-risk account(s)."
                ),
                1 if queue_exposure.severe_queue_accounts > 0 else 2,
            )
        )

    if _channel_risk_active(portfolio):
        candidates.append(
            (
                _channel_severity_score(portfolio),
                "channel",
                coach.channel_command,
                (
                    f"{portfolio.hotspot_channel} is the dependency hotspot with "
                    f"dependency {portfolio.hotspot_dependency_score}."
                ),
                (
                    f"{portfolio.channel_failure_mode}. {portfolio.channel_recovery_priority} "
                    "should happen before channel drag hardens further."
                ),
                2,
            )
        )

    if flagship.bug_level >= 24 or flagship.quality <= 54 or flagship.technical_debt >= 28:
        product_command = (
            TurnAction.REDUCE_TECHNICAL_DEBT.value
            if flagship.technical_debt > flagship.bug_level and flagship.quality >= 55
            else TurnAction.IMPROVE_QUALITY.value
        )
        candidates.append(
            (
                min(
                    82,
                    42
                    + max(0, flagship.bug_level - 18)
                    + max(0, 58 - flagship.quality)
                    + max(0, flagship.technical_debt - 20) // 2,
                ),
                "product",
                product_command,
                (
                    f"{flagship.name} is fragile at Q {flagship.quality} / "
                    f"B {flagship.bug_level} / D {flagship.technical_debt}."
                ),
                (
                    "Product health drag will leak into acquisition, churn, support load, and "
                    "the board story."
                ),
                1,
            )
        )

    ranked = _rank_candidates(candidates)
    top_command = ranked[0].command if ranked else TurnAction.VIEW_STATUS.value
    overall_risk = ranked[0].severity if ranked else "controlled"
    headline = (
        f"If you continue from here, `{top_command}` is the sharpest near-term control move."
        if ranked
        else "Near-term operating risk is controlled."
    )
    return RiskForecastSummary(
        headline=headline,
        overall_risk=overall_risk,
        top_command=top_command,
        items=ranked,
    )


def _rank_candidates(
    candidates: list[tuple[int, str, str, str, str, int]],
) -> tuple[RiskForecastItem, ...]:
    best_by_area: dict[str, tuple[int, str, str, str, str, int]] = {}
    for candidate in candidates:
        score, area, *_ = candidate
        current = best_by_area.get(area)
        if current is None or score > current[0]:
            best_by_area[area] = candidate
    ordered = sorted(
        best_by_area.values(),
        key=lambda candidate: (candidate[0], -candidate[5]),
        reverse=True,
    )
    return tuple(
        RiskForecastItem(
            rank=index,
            area=area,
            severity=_severity_label(score),
            command=command,
            summary=summary,
            consequence=consequence,
            horizon_turns=horizon_turns,
        )
        for index, (score, area, command, summary, consequence, horizon_turns) in enumerate(
            ordered[:4], start=1
        )
    )


def _finance_risk_active(planner, conservative_runway_turns: int | None) -> bool:
    return (
        planner.reserve_break_risk in {"critical", "high", "elevated"}
        or planner.reserve_gap < ZERO_MONEY
        or (conservative_runway_turns is not None and conservative_runway_turns <= 4)
    )


def _finance_severity_score(reserve_break_risk: str, conservative_runway_turns: int | None) -> int:
    if conservative_runway_turns is not None and conservative_runway_turns <= 2:
        return 96
    if reserve_break_risk == "critical":
        return 92
    if reserve_break_risk == "high":
        return 84
    return 72


def _support_risk_active(
    state: GameState,
    queue_exposure,
    revenue_at_risk_accounts: int,
    renewal_pressure_accounts: int,
) -> bool:
    return (
        queue_exposure.severe_queue_accounts > 0
        or state.support_program.backlog_queue
        >= BALANCE.support_program_backlog_reputation_threshold
        or queue_exposure.lane_saturation_index >= 10
        or revenue_at_risk_accounts > 0
        or renewal_pressure_accounts > 0
    )


def _support_severity_score(
    state: GameState,
    queue_exposure,
    revenue_at_risk_value: Decimal,
) -> int:
    score = 44
    score += min(24, queue_exposure.lane_saturation_index * 3)
    score += min(18, queue_exposure.severe_queue_accounts * 6)
    score += min(10, state.support_program.escalation_queue * 2)
    if revenue_at_risk_value > ZERO_MONEY:
        score += min(10, int(revenue_at_risk_value // Decimal("1200.00")))
    return min(92, score)


def _channel_risk_active(portfolio) -> bool:
    return (
        portfolio.channel_dependency_risk
        >= BALANCE.commercial_pressure_channel_dependency_threshold
        or portfolio.channel_conflict_index >= BALANCE.finance_planner_channel_volatility_threshold
        or portfolio.paused_dependency_score > 0
        or portfolio.recovery_drag_score > 0
    )


def _channel_severity_score(portfolio) -> int:
    return min(
        86,
        40
        + min(22, portfolio.channel_dependency_risk // 2)
        + min(14, portfolio.channel_volatility_index // 3)
        + min(10, portfolio.paused_dependency_score // 10),
    )


def _severity_label(score: int) -> str:
    if score >= 90:
        return "critical"
    if score >= 78:
        return "high"
    if score >= 64:
        return "elevated"
    return "watch"


def _choose_flagship_product(state: GameState) -> Product:
    active_products = [product for product in state.products if product.is_active]
    candidates = active_products or state.products
    return max(
        candidates,
        key=lambda product: (
            product.user_count,
            product.quality,
            product.market_fit,
            -product.bug_level,
        ),
    )


def _latest_net_cash_flow(state: GameState) -> Decimal:
    if not state.turn_history:
        return Decimal("0.00")
    return state.turn_history[-1].net_cash_flow
