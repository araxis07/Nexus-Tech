"""Capital-planning configuration and drift helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import (
    BoardAsk,
    CapitalPlan,
    CapitalPlanMode,
    CapitalSourcePreference,
    Company,
    FinanceState,
    GameState,
    SupportLaneFocus,
)
from nexus_tech.domain.money import format_money, quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.partnerships import calculate_partnership_portfolio
from nexus_tech.simulation.support_program import calculate_support_queue_exposure


@dataclass(frozen=True)
class CapitalPlanSummary:
    """Human-readable result when the capital plan changes."""

    message: str
    capital_plan: CapitalPlan


@dataclass(frozen=True)
class CapitalPlanDrift:
    """Passive finance drift coming from the selected capital posture."""

    investor_pressure_delta: int
    covenant_risk_delta: int
    board_confidence_delta: int
    runway_target_modifier: int
    reserve_gap: Decimal
    alignment_score: int
    reserve_status: str
    execution_status: str
    recommended_posture: str
    summary: str


def get_capital_plan_profile(
    mode: CapitalPlanMode,
    source_preference: CapitalSourcePreference,
) -> CapitalPlan:
    """Build a normalized capital plan from one strategic posture."""

    return CapitalPlan(
        mode=mode,
        source_preference=source_preference,
        planning_horizon_turns=BALANCE.capital_plan_horizon_by_mode[mode.value],
        reserve_target=BALANCE.capital_plan_reserve_target_by_mode[mode.value],
        product_investment_share=BALANCE.capital_plan_product_share_by_mode[mode.value],
        go_to_market_share=BALANCE.capital_plan_go_to_market_share_by_mode[mode.value],
        reserve_share=BALANCE.capital_plan_reserve_share_by_mode[mode.value],
    )


def apply_set_capital_plan(
    state: GameState,
    mode: CapitalPlanMode,
    source_preference: CapitalSourcePreference,
    *,
    planning_horizon_turns: int | None = None,
    reserve_target: Decimal | None = None,
    product_investment_share: int | None = None,
    go_to_market_share: int | None = None,
    reserve_share: int | None = None,
) -> CapitalPlanSummary:
    """Apply a new capital-planning posture to the in-memory run state."""

    capital_plan = get_capital_plan_profile(mode, source_preference)
    capital_plan = CapitalPlan(
        mode=mode,
        source_preference=source_preference,
        planning_horizon_turns=(
            planning_horizon_turns
            if planning_horizon_turns is not None
            else capital_plan.planning_horizon_turns
        ),
        reserve_target=reserve_target
        if reserve_target is not None
        else capital_plan.reserve_target,
        product_investment_share=(
            product_investment_share
            if product_investment_share is not None
            else capital_plan.product_investment_share
        ),
        go_to_market_share=(
            go_to_market_share
            if go_to_market_share is not None
            else capital_plan.go_to_market_share
        ),
        reserve_share=reserve_share if reserve_share is not None else capital_plan.reserve_share,
    )
    state.capital_plan = capital_plan
    allocation_summary = (
        f"P {capital_plan.product_investment_share}% / "
        f"GTM {capital_plan.go_to_market_share}% / "
        f"Reserve {capital_plan.reserve_share}%"
    )
    return CapitalPlanSummary(
        message=(
            f"Capital plan set to {mode.value} with a {source_preference.value} bias. "
            f"Reserve target {format_money(capital_plan.reserve_target)} over "
            f"{capital_plan.planning_horizon_turns} turns. Allocation {allocation_summary}."
        ),
        capital_plan=capital_plan,
    )


def apply_rebalance_capital(state: GameState) -> CapitalPlanSummary:
    """Auto-rebalance capital shares around the current reserve, support, and channel strain."""

    queue_exposure = calculate_support_queue_exposure(state)
    portfolio = calculate_partnership_portfolio(state)
    capital_plan = state.capital_plan

    mode = capital_plan.mode
    reserve_target = capital_plan.reserve_target
    planning_horizon_turns = capital_plan.planning_horizon_turns
    product_share = capital_plan.product_investment_share
    go_to_market_share = capital_plan.go_to_market_share
    reserve_share = capital_plan.reserve_share
    notes: list[str] = []

    if (
        state.company.cash_on_hand < capital_plan.reserve_target
        or state.finance.covenant_risk >= 16
        or state.finance.board_pressure >= 26
    ):
        mode = CapitalPlanMode.CONSERVE
        reserve_target = quantize_money(
            reserve_target + BALANCE.capital_plan_rebalance_reserve_target_step
        )
        planning_horizon_turns = min(
            12,
            planning_horizon_turns + BALANCE.capital_plan_rebalance_horizon_gain,
        )
        reserve_share += BALANCE.capital_plan_rebalance_reserve_share_shift
        go_to_market_share -= BALANCE.capital_plan_rebalance_reserve_share_shift
        notes.append("reserve stress")
    elif capital_plan.mode is CapitalPlanMode.EXPAND and (
        queue_exposure.hotspot_lane_overflow > 0
        or portfolio.hotspot_dependency_score
        >= BALANCE.finance_planner_reactivate_dependency_threshold
    ):
        mode = CapitalPlanMode.BALANCED
        notes.append("execution drag")

    if state.finance.active_board_ask is BoardAsk.RELIABILITY:
        product_share += BALANCE.capital_plan_rebalance_product_share_shift
        go_to_market_share -= BALANCE.capital_plan_rebalance_product_share_shift
        notes.append("reliability mandate")
    elif state.finance.active_board_ask is BoardAsk.PROFITABILITY:
        reserve_share += 2
        go_to_market_share -= 2
        notes.append("profitability mandate")
    elif state.finance.active_board_ask is BoardAsk.TEAM_HEALTH:
        reserve_share += 2
        product_share += 1
        go_to_market_share -= 3
        notes.append("team-health mandate")
    elif state.finance.active_board_ask is BoardAsk.PORTFOLIO_FOCUS:
        product_share += 2
        go_to_market_share -= 2
        notes.append("portfolio focus")

    if queue_exposure.hotspot_lane_overflow > 0:
        if queue_exposure.hotspot_lane is SupportLaneFocus.ENTERPRISE:
            product_share += 2
            go_to_market_share -= 2
        elif queue_exposure.hotspot_lane is SupportLaneFocus.BILLING:
            reserve_share += 2
            go_to_market_share -= 2
        elif queue_exposure.hotspot_lane is SupportLaneFocus.ONBOARDING:
            reserve_share += 1
            product_share += 1
            go_to_market_share -= 2
        notes.append(f"{queue_exposure.hotspot_lane.value} hotspot")

    if queue_exposure.focus_alignment_gap > 0:
        reserve_share += 1
        go_to_market_share -= 1
        notes.append("support focus mismatch")

    if (
        portfolio.hotspot_dependency_score
        >= BALANCE.finance_planner_reactivate_dependency_threshold
        or portfolio.hotspot_revenue_share_percent
        >= BALANCE.finance_planner_volatile_share_threshold
    ):
        reserve_share += 2
        go_to_market_share -= 2
        notes.append("channel concentration")

    if portfolio.paused_dependency_score >= BALANCE.finance_planner_reactivate_dependency_threshold:
        reserve_share += 1
        product_share += 1
        go_to_market_share -= 2
        notes.append("paused channel dependency")

    product_share, go_to_market_share, reserve_share = _normalize_capital_shares(
        product_share,
        go_to_market_share,
        reserve_share,
    )
    state.capital_plan = CapitalPlan(
        mode=mode,
        source_preference=capital_plan.source_preference,
        planning_horizon_turns=planning_horizon_turns,
        reserve_target=reserve_target,
        product_investment_share=product_share,
        go_to_market_share=go_to_market_share,
        reserve_share=reserve_share,
    )
    note_summary = ", ".join(dict.fromkeys(notes)) if notes else "no major drift"
    return CapitalPlanSummary(
        message=(
            f"Capital was rebalanced toward {state.capital_plan.mode.value}. "
            f"Reserve target {format_money(state.capital_plan.reserve_target)} over "
            f"{state.capital_plan.planning_horizon_turns} turns. Allocation "
            f"P {state.capital_plan.product_investment_share}% / "
            f"GTM {state.capital_plan.go_to_market_share}% / "
            f"Reserve {state.capital_plan.reserve_share}% ({note_summary})."
        ),
        capital_plan=state.capital_plan,
    )


def evaluate_capital_plan(
    company: Company,
    finance: FinanceState,
    capital_plan: CapitalPlan,
    *,
    latest_net_cash_flow: Decimal,
    technical_debt_load: int = 0,
    active_channels: int = 0,
    support_backlog: int = 0,
) -> CapitalPlanDrift:
    """Return finance modifiers implied by the active capital plan."""

    reserve_gap = quantize_money(company.cash_on_hand - capital_plan.reserve_target)
    investor_pressure_delta = 0
    covenant_risk_delta = 0
    board_confidence_delta = 0
    summary_notes: list[str] = []

    if reserve_gap < Decimal("0.00"):
        investor_pressure_delta += BALANCE.capital_plan_reserve_shortfall_pressure_by_mode[
            capital_plan.mode.value
        ]
        covenant_risk_delta += 1
        summary_notes.append("reserve shortfall")
    else:
        board_confidence_delta += BALANCE.capital_plan_reserve_surplus_confidence_bonus_by_mode[
            capital_plan.mode.value
        ]
        summary_notes.append("reserve target covered")

    if latest_net_cash_flow < Decimal("0.00"):
        investor_pressure_delta += BALANCE.capital_plan_negative_cash_pressure_by_mode[
            capital_plan.mode.value
        ]
        if capital_plan.mode is CapitalPlanMode.EXPAND:
            board_confidence_delta -= BALANCE.capital_plan_expand_confidence_penalty
            summary_notes.append("expand mode is amplifying burn")
    elif capital_plan.mode is CapitalPlanMode.CONSERVE:
        covenant_risk_delta -= BALANCE.capital_plan_conserve_covenant_relief
        board_confidence_delta += BALANCE.capital_plan_conserve_execution_bonus
        summary_notes.append("conserve mode is cushioning cash")

    if (
        capital_plan.product_investment_share < BALANCE.capital_plan_low_product_share_threshold
        and technical_debt_load >= 50
    ):
        board_confidence_delta -= BALANCE.capital_plan_low_product_share_confidence_penalty
        summary_notes.append("product investment is light versus technical debt")

    if (
        capital_plan.go_to_market_share >= BALANCE.capital_plan_high_gtm_share_threshold
        and active_channels == 0
    ):
        investor_pressure_delta += BALANCE.capital_plan_gtm_without_channels_pressure_gain
        board_confidence_delta -= 1
        summary_notes.append("GTM allocation is ahead of channel execution")
    elif (
        capital_plan.go_to_market_share >= BALANCE.capital_plan_high_gtm_share_threshold
        and active_channels > 0
        and latest_net_cash_flow >= Decimal("0.00")
    ):
        board_confidence_delta += BALANCE.capital_plan_expand_execution_bonus
        summary_notes.append("GTM allocation is being translated into channels")

    if (
        capital_plan.reserve_share < BALANCE.capital_plan_low_reserve_share_threshold
        and support_backlog >= BALANCE.support_program_backlog_reputation_threshold
    ):
        covenant_risk_delta += BALANCE.capital_plan_support_reserve_covenant_penalty
        summary_notes.append("reserve posture is thin for current support load")

    if capital_plan.source_preference is CapitalSourcePreference.BOOTSTRAP:
        if reserve_gap >= Decimal("0.00") and latest_net_cash_flow >= Decimal("0.00"):
            investor_pressure_delta -= BALANCE.capital_plan_bootstrap_pressure_relief
            board_confidence_delta += BALANCE.capital_plan_bootstrap_confidence_bonus
            summary_notes.append("bootstrap bias is rewarding discipline")
    elif capital_plan.source_preference is CapitalSourcePreference.DEBT:
        if finance.debt_principal >= BALANCE.finance_covenant_risk_debt_threshold:
            covenant_risk_delta += BALANCE.capital_plan_debt_covenant_penalty
            summary_notes.append("debt bias is stressing covenants")
    elif capital_plan.source_preference is CapitalSourcePreference.ANGEL:
        if reserve_gap < Decimal("0.00"):
            investor_pressure_delta -= BALANCE.capital_plan_angel_pressure_relief
            summary_notes.append("angel bias softens short-term pressure")
    elif (
        capital_plan.source_preference is CapitalSourcePreference.VENTURE
        and company.cash_on_hand
        <= BALANCE.capital_plan_expand_investor_pressure_relief_cash_threshold
    ):
        investor_pressure_delta -= BALANCE.capital_plan_venture_pressure_relief
        summary_notes.append("venture bias accepts lower cash buffers")
    if (
        capital_plan.source_preference is CapitalSourcePreference.VENTURE
        and finance.equity_dilution >= BALANCE.capital_plan_dilution_warning_threshold
    ):
        board_confidence_delta -= BALANCE.capital_plan_venture_dilution_confidence_penalty
        summary_notes.append("venture dilution is becoming a board concern")

    reserve_status = "covered"
    if reserve_gap < Decimal("0.00"):
        reserve_status = "under target"
    elif reserve_gap >= capital_plan.reserve_target * Decimal("0.30"):
        reserve_status = "buffered"

    execution_status = "aligned"
    if support_backlog >= BALANCE.support_program_backlog_reputation_threshold:
        execution_status = "support constrained"
    elif (
        technical_debt_load >= 50
        and capital_plan.product_investment_share < BALANCE.capital_plan_low_product_share_threshold
    ):
        execution_status = "product constrained"
    elif (
        capital_plan.go_to_market_share >= BALANCE.capital_plan_high_gtm_share_threshold
        and active_channels == 0
    ):
        execution_status = "gtm ahead of execution"

    if reserve_gap < Decimal("0.00"):
        recommended_posture = "Move closer to conserve until the reserve target is covered."
    elif execution_status == "gtm ahead of execution":
        recommended_posture = "Convert GTM allocation into active channels before expanding spend."
    elif execution_status == "product constrained":
        recommended_posture = "Rebalance more capital into product quality and debt reduction."
    elif execution_status == "support constrained":
        recommended_posture = "Fund support relief before pushing more customer volume."
    else:
        recommended_posture = "Current capital posture is coherent with execution."

    alignment_score = max(
        0,
        min(
            100,
            58
            + (board_confidence_delta * 5)
            - (investor_pressure_delta * 4)
            - (covenant_risk_delta * 6)
            + (4 if reserve_gap >= Decimal("0.00") else -6),
        ),
    )

    summary = (
        f"{capital_plan.mode.value} / {capital_plan.source_preference.value} plan, "
        f"reserve gap {format_money(reserve_gap)}"
        + (f" ({'; '.join(summary_notes)})." if summary_notes else ".")
    )
    return CapitalPlanDrift(
        investor_pressure_delta=investor_pressure_delta,
        covenant_risk_delta=covenant_risk_delta,
        board_confidence_delta=board_confidence_delta,
        runway_target_modifier=BALANCE.capital_plan_runway_target_modifier_by_mode[
            capital_plan.mode.value
        ],
        reserve_gap=reserve_gap,
        alignment_score=alignment_score,
        reserve_status=reserve_status,
        execution_status=execution_status,
        recommended_posture=recommended_posture,
        summary=summary,
    )


def _normalize_capital_shares(
    product_share: int,
    go_to_market_share: int,
    reserve_share: int,
) -> tuple[int, int, int]:
    shares = [
        max(0, product_share),
        max(0, go_to_market_share),
        max(0, reserve_share),
    ]
    total_share = sum(shares)
    if total_share > 100:
        excess = total_share - 100
        for index in (1, 0, 2):
            reducible = min(excess, shares[index])
            shares[index] -= reducible
            excess -= reducible
            if excess <= 0:
                break
    elif total_share < 100:
        shares[2] += 100 - total_share
    return shares[0], shares[1], shares[2]
