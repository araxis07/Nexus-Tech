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
from nexus_tech.simulation.endgame import calculate_endgame_pressure, calculate_endgame_readiness
from nexus_tech.simulation.partnerships import calculate_partnership_portfolio
from nexus_tech.simulation.support import clamp_int
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


def apply_raise_reserve_target(state: GameState) -> CapitalPlanSummary:
    """Raise reserve expectations and shift more allocation toward resilience."""

    capital_plan = state.capital_plan
    mode = capital_plan.mode
    if capital_plan.mode is CapitalPlanMode.EXPAND:
        mode = CapitalPlanMode.BALANCED

    reserve_target = quantize_money(
        capital_plan.reserve_target + BALANCE.capital_plan_raise_reserve_target_step
    )
    planning_horizon_turns = min(
        12,
        capital_plan.planning_horizon_turns + BALANCE.capital_plan_raise_reserve_horizon_gain,
    )
    reserve_share = capital_plan.reserve_share + BALANCE.capital_plan_raise_reserve_share_shift
    go_to_market_share = max(
        0,
        capital_plan.go_to_market_share - BALANCE.capital_plan_raise_reserve_share_shift,
    )
    product_share = capital_plan.product_investment_share
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
    return CapitalPlanSummary(
        message=(
            f"Reserve target raised to {format_money(reserve_target)} over "
            f"{planning_horizon_turns} turns. Allocation now "
            f"P {product_share}% / GTM {go_to_market_share}% / Reserve {reserve_share}%."
        ),
        capital_plan=state.capital_plan,
    )


def apply_step_up_reserve_discipline(state: GameState) -> CapitalPlanSummary:
    """Tighten the capital plan around reserve durability and lighter late-game burn."""

    capital_plan = state.capital_plan
    reserve_target = quantize_money(
        capital_plan.reserve_target + BALANCE.capital_plan_step_up_reserve_target_step
    )
    planning_horizon_turns = min(
        12,
        capital_plan.planning_horizon_turns + BALANCE.capital_plan_step_up_reserve_horizon_gain,
    )
    reserve_share = capital_plan.reserve_share + BALANCE.capital_plan_step_up_reserve_share_shift
    go_to_market_share = max(
        0,
        capital_plan.go_to_market_share - BALANCE.capital_plan_step_up_reserve_share_shift,
    )
    product_share = max(
        0,
        capital_plan.product_investment_share - BALANCE.capital_plan_step_up_product_share_shift,
    )
    product_share, go_to_market_share, reserve_share = _normalize_capital_shares(
        product_share,
        go_to_market_share,
        reserve_share,
    )
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.CONSERVE,
        source_preference=capital_plan.source_preference,
        planning_horizon_turns=planning_horizon_turns,
        reserve_target=reserve_target,
        product_investment_share=product_share,
        go_to_market_share=go_to_market_share,
        reserve_share=reserve_share,
    )
    state.finance.board_pressure = max(
        0,
        state.finance.board_pressure - BALANCE.capital_plan_step_up_board_pressure_relief,
    )
    state.finance.covenant_risk = max(
        0,
        state.finance.covenant_risk - BALANCE.capital_plan_step_up_covenant_relief,
    )
    state.finance.investor_pressure = max(
        0,
        state.finance.investor_pressure - BALANCE.capital_plan_step_up_investor_pressure_relief,
    )
    state.finance.board_confidence = min(
        100,
        state.finance.board_confidence + BALANCE.capital_plan_step_up_board_confidence_gain,
    )
    return CapitalPlanSummary(
        message=(
            "Stepped up reserve discipline. "
            f"Reserve target {format_money(reserve_target)} over {planning_horizon_turns} turns. "
            f"Allocation now P {product_share}% / GTM {go_to_market_share}% / "
            f"Reserve {reserve_share}%."
        ),
        capital_plan=state.capital_plan,
    )


def apply_harden_financing_posture(state: GameState) -> CapitalPlanSummary:
    """Pay a small financing tax now to improve durability and de-risk capital posture."""

    if state.company.cash_on_hand < BALANCE.capital_plan_harden_financing_posture_cost:
        raise ValueError("Not enough cash to harden the financing posture this turn.")

    capital_plan = state.capital_plan
    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.capital_plan_harden_financing_posture_cost
    )
    reserve_target = quantize_money(
        capital_plan.reserve_target + BALANCE.capital_plan_harden_financing_target_step
    )
    planning_horizon_turns = min(
        12,
        capital_plan.planning_horizon_turns + BALANCE.capital_plan_harden_financing_horizon_gain,
    )
    reserve_share = (
        capital_plan.reserve_share + BALANCE.capital_plan_harden_financing_reserve_share_shift
    )
    go_to_market_share = max(
        0,
        capital_plan.go_to_market_share - BALANCE.capital_plan_harden_financing_gtm_share_shift,
    )
    product_share = max(
        0,
        capital_plan.product_investment_share
        - BALANCE.capital_plan_harden_financing_product_share_shift,
    )
    product_share, go_to_market_share, reserve_share = _normalize_capital_shares(
        product_share,
        go_to_market_share,
        reserve_share,
    )
    if capital_plan.source_preference is CapitalSourcePreference.DEBT:
        source_preference = CapitalSourcePreference.BOOTSTRAP
    elif capital_plan.source_preference is CapitalSourcePreference.VENTURE:
        source_preference = CapitalSourcePreference.ANGEL
    elif capital_plan.source_preference is CapitalSourcePreference.ANGEL:
        source_preference = CapitalSourcePreference.BOOTSTRAP
    else:
        source_preference = capital_plan.source_preference

    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.CONSERVE,
        source_preference=source_preference,
        planning_horizon_turns=planning_horizon_turns,
        reserve_target=reserve_target,
        product_investment_share=product_share,
        go_to_market_share=go_to_market_share,
        reserve_share=reserve_share,
    )
    if state.finance.debt_principal > Decimal("0.00"):
        state.finance.loan_interest_rate = max(
            Decimal("0.0000"),
            state.finance.loan_interest_rate
            - BALANCE.capital_plan_harden_financing_interest_relief,
        )
    state.finance.board_pressure = max(
        0,
        state.finance.board_pressure - BALANCE.capital_plan_harden_financing_board_pressure_relief,
    )
    state.finance.covenant_risk = max(
        0,
        state.finance.covenant_risk - BALANCE.capital_plan_harden_financing_covenant_relief,
    )
    state.finance.investor_pressure = max(
        0,
        state.finance.investor_pressure
        - BALANCE.capital_plan_harden_financing_investor_pressure_relief,
    )
    state.finance.board_confidence = min(
        100,
        state.finance.board_confidence
        + BALANCE.capital_plan_harden_financing_board_confidence_gain,
    )
    return CapitalPlanSummary(
        message=(
            "Hardened financing posture. "
            f"Reserve target {format_money(reserve_target)} over {planning_horizon_turns} turns. "
            f"Allocation now P {product_share}% / GTM {go_to_market_share}% / "
            f"Reserve {reserve_share}% with {source_preference.value} capital."
        ),
        capital_plan=state.capital_plan,
    )


def apply_refinancing_posture(state: GameState) -> CapitalPlanSummary:
    """Bias the capital plan toward calmer covenant and rollover pressure."""

    if state.finance.debt_principal <= Decimal("0.00"):
        raise ValueError("There is no debt stack to refinance right now.")
    if state.company.cash_on_hand < BALANCE.capital_plan_refinancing_posture_cost:
        raise ValueError("Not enough cash to set a refinancing posture this turn.")

    capital_plan = state.capital_plan
    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.capital_plan_refinancing_posture_cost
    )
    reserve_target = quantize_money(
        capital_plan.reserve_target + BALANCE.capital_plan_refinancing_posture_target_step
    )
    planning_horizon_turns = min(
        12,
        capital_plan.planning_horizon_turns + BALANCE.capital_plan_refinancing_posture_horizon_gain,
    )
    reserve_share = (
        capital_plan.reserve_share + BALANCE.capital_plan_refinancing_posture_reserve_share_shift
    )
    go_to_market_share = max(
        0,
        capital_plan.go_to_market_share - BALANCE.capital_plan_refinancing_posture_gtm_share_shift,
    )
    product_share = max(
        0,
        capital_plan.product_investment_share
        - BALANCE.capital_plan_refinancing_posture_product_share_shift,
    )
    product_share, go_to_market_share, reserve_share = _normalize_capital_shares(
        product_share,
        go_to_market_share,
        reserve_share,
    )
    if capital_plan.source_preference in {
        CapitalSourcePreference.DEBT,
        CapitalSourcePreference.VENTURE,
    }:
        source_preference = CapitalSourcePreference.ANGEL
    else:
        source_preference = capital_plan.source_preference

    mode = (
        CapitalPlanMode.CONSERVE
        if capital_plan.mode is CapitalPlanMode.EXPAND or state.finance.covenant_risk >= 16
        else capital_plan.mode
    )
    state.capital_plan = CapitalPlan(
        mode=mode,
        source_preference=source_preference,
        planning_horizon_turns=planning_horizon_turns,
        reserve_target=reserve_target,
        product_investment_share=product_share,
        go_to_market_share=go_to_market_share,
        reserve_share=reserve_share,
    )
    state.finance.loan_interest_rate = max(
        Decimal("0.0000"),
        state.finance.loan_interest_rate - BALANCE.capital_plan_refinancing_posture_interest_relief,
    )
    state.finance.board_pressure = max(
        0,
        state.finance.board_pressure
        - BALANCE.capital_plan_refinancing_posture_board_pressure_relief,
    )
    state.finance.covenant_risk = max(
        0,
        state.finance.covenant_risk - BALANCE.capital_plan_refinancing_posture_covenant_relief,
    )
    state.finance.investor_pressure = max(
        0,
        state.finance.investor_pressure
        - BALANCE.capital_plan_refinancing_posture_investor_pressure_relief,
    )
    state.finance.board_confidence = min(
        100,
        state.finance.board_confidence
        + BALANCE.capital_plan_refinancing_posture_board_confidence_gain,
    )
    return CapitalPlanSummary(
        message=(
            "Set a refinancing posture. "
            f"Reserve target {format_money(reserve_target)} over {planning_horizon_turns} turns. "
            f"Allocation now P {product_share}% / GTM {go_to_market_share}% / "
            f"Reserve {reserve_share}% with {source_preference.value} capital."
        ),
        capital_plan=state.capital_plan,
    )


def apply_lock_capital_buffer(state: GameState) -> CapitalPlanSummary:
    """Force a more defensive reserve buffer before late-game fragility compounds."""

    if state.company.cash_on_hand < BALANCE.capital_plan_lock_buffer_cost:
        raise ValueError("Not enough cash to lock a capital buffer this turn.")

    capital_plan = state.capital_plan
    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.capital_plan_lock_buffer_cost
    )
    reserve_target = quantize_money(
        capital_plan.reserve_target + BALANCE.capital_plan_lock_buffer_target_step
    )
    planning_horizon_turns = min(
        12,
        capital_plan.planning_horizon_turns + BALANCE.capital_plan_lock_buffer_horizon_gain,
    )
    reserve_share = (
        capital_plan.reserve_share + BALANCE.capital_plan_lock_buffer_reserve_share_shift
    )
    go_to_market_share = max(
        0,
        capital_plan.go_to_market_share - BALANCE.capital_plan_lock_buffer_gtm_share_shift,
    )
    product_share = max(
        0,
        capital_plan.product_investment_share
        - BALANCE.capital_plan_lock_buffer_product_share_shift,
    )
    product_share, go_to_market_share, reserve_share = _normalize_capital_shares(
        product_share,
        go_to_market_share,
        reserve_share,
    )
    if capital_plan.source_preference in {
        CapitalSourcePreference.DEBT,
        CapitalSourcePreference.VENTURE,
    }:
        source_preference = CapitalSourcePreference.ANGEL
    else:
        source_preference = capital_plan.source_preference

    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.CONSERVE,
        source_preference=source_preference,
        planning_horizon_turns=planning_horizon_turns,
        reserve_target=reserve_target,
        product_investment_share=product_share,
        go_to_market_share=go_to_market_share,
        reserve_share=reserve_share,
    )
    state.finance.board_pressure = max(
        0,
        state.finance.board_pressure - BALANCE.capital_plan_lock_buffer_board_pressure_relief,
    )
    state.finance.covenant_risk = max(
        0,
        state.finance.covenant_risk - BALANCE.capital_plan_lock_buffer_covenant_relief,
    )
    state.finance.investor_pressure = max(
        0,
        state.finance.investor_pressure - BALANCE.capital_plan_lock_buffer_investor_pressure_relief,
    )
    state.finance.board_confidence = min(
        100,
        state.finance.board_confidence + BALANCE.capital_plan_lock_buffer_board_confidence_gain,
    )
    return CapitalPlanSummary(
        message=(
            "Locked a capital buffer. "
            f"Reserve target {format_money(reserve_target)} over {planning_horizon_turns} turns. "
            f"Allocation now P {product_share}% / GTM {go_to_market_share}% / "
            f"Reserve {reserve_share}% with {source_preference.value} capital."
        ),
        capital_plan=state.capital_plan,
    )


def apply_set_covenant_firewall(state: GameState) -> CapitalPlanSummary:
    """Build a harder reserve and covenant buffer before debt and board heat converge."""

    if (
        state.finance.debt_principal <= Decimal("0.00")
        and state.finance.covenant_risk < 12
        and state.finance.board_pressure < 24
    ):
        raise ValueError("There is no covenant heat severe enough to justify this posture yet.")
    if state.company.cash_on_hand < BALANCE.capital_plan_covenant_firewall_cost:
        raise ValueError("Not enough cash to set a covenant firewall this turn.")

    capital_plan = state.capital_plan
    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.capital_plan_covenant_firewall_cost
    )
    reserve_target = quantize_money(
        capital_plan.reserve_target + BALANCE.capital_plan_covenant_firewall_target_step
    )
    planning_horizon_turns = min(
        12,
        capital_plan.planning_horizon_turns + BALANCE.capital_plan_covenant_firewall_horizon_gain,
    )
    reserve_share = (
        capital_plan.reserve_share + BALANCE.capital_plan_covenant_firewall_reserve_share_shift
    )
    go_to_market_share = max(
        0,
        capital_plan.go_to_market_share - BALANCE.capital_plan_covenant_firewall_gtm_share_shift,
    )
    product_share = max(
        0,
        capital_plan.product_investment_share
        - BALANCE.capital_plan_covenant_firewall_product_share_shift,
    )
    product_share, go_to_market_share, reserve_share = _normalize_capital_shares(
        product_share,
        go_to_market_share,
        reserve_share,
    )
    if capital_plan.source_preference in {
        CapitalSourcePreference.DEBT,
        CapitalSourcePreference.VENTURE,
    }:
        source_preference = CapitalSourcePreference.ANGEL
    else:
        source_preference = capital_plan.source_preference

    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.CONSERVE,
        source_preference=source_preference,
        planning_horizon_turns=planning_horizon_turns,
        reserve_target=reserve_target,
        product_investment_share=product_share,
        go_to_market_share=go_to_market_share,
        reserve_share=reserve_share,
    )
    state.finance.loan_interest_rate = max(
        Decimal("0.0000"),
        state.finance.loan_interest_rate - BALANCE.capital_plan_covenant_firewall_interest_relief,
    )
    state.finance.board_pressure = max(
        0,
        state.finance.board_pressure - BALANCE.capital_plan_covenant_firewall_board_pressure_relief,
    )
    state.finance.covenant_risk = max(
        0,
        state.finance.covenant_risk - BALANCE.capital_plan_covenant_firewall_covenant_relief,
    )
    state.finance.investor_pressure = max(
        0,
        state.finance.investor_pressure
        - BALANCE.capital_plan_covenant_firewall_investor_pressure_relief,
    )
    state.finance.board_confidence = min(
        100,
        state.finance.board_confidence
        + BALANCE.capital_plan_covenant_firewall_board_confidence_gain,
    )
    return CapitalPlanSummary(
        message=(
            "Set a covenant firewall. "
            f"Reserve target {format_money(reserve_target)} over {planning_horizon_turns} turns. "
            f"Allocation now P {product_share}% / GTM {go_to_market_share}% / "
            f"Reserve {reserve_share}% with {source_preference.value} capital."
        ),
        capital_plan=state.capital_plan,
    )


def apply_set_debt_strategy(state: GameState) -> CapitalPlanSummary:
    """Deliberately shrink debt exposure before covenant and board heat harden late-game paths."""

    if state.finance.debt_principal <= Decimal("0.00") and state.finance.covenant_risk < 12:
        raise ValueError("There is no debt heat serious enough to justify a debt strategy yet.")
    if state.company.cash_on_hand < BALANCE.capital_plan_debt_strategy_cost:
        raise ValueError("Not enough cash to set a debt strategy this turn.")

    capital_plan = state.capital_plan
    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.capital_plan_debt_strategy_cost
    )
    paydown = min(state.finance.debt_principal, BALANCE.capital_plan_debt_strategy_paydown)
    state.finance.debt_principal = quantize_money(state.finance.debt_principal - paydown)
    reserve_target = quantize_money(
        capital_plan.reserve_target + BALANCE.capital_plan_debt_strategy_target_step
    )
    planning_horizon_turns = min(
        12,
        capital_plan.planning_horizon_turns + BALANCE.capital_plan_debt_strategy_horizon_gain,
    )
    reserve_share = (
        capital_plan.reserve_share + BALANCE.capital_plan_debt_strategy_reserve_share_shift
    )
    go_to_market_share = max(
        0,
        capital_plan.go_to_market_share - BALANCE.capital_plan_debt_strategy_gtm_share_shift,
    )
    product_share = max(
        0,
        capital_plan.product_investment_share
        - BALANCE.capital_plan_debt_strategy_product_share_shift,
    )
    product_share, go_to_market_share, reserve_share = _normalize_capital_shares(
        product_share,
        go_to_market_share,
        reserve_share,
    )
    if capital_plan.source_preference in {
        CapitalSourcePreference.DEBT,
        CapitalSourcePreference.VENTURE,
    }:
        source_preference = CapitalSourcePreference.BOOTSTRAP
    else:
        source_preference = capital_plan.source_preference

    mode = (
        CapitalPlanMode.CONSERVE
        if capital_plan.mode is CapitalPlanMode.EXPAND or state.finance.covenant_risk >= 16
        else CapitalPlanMode.BALANCED
    )
    state.capital_plan = CapitalPlan(
        mode=mode,
        source_preference=source_preference,
        planning_horizon_turns=planning_horizon_turns,
        reserve_target=reserve_target,
        product_investment_share=product_share,
        go_to_market_share=go_to_market_share,
        reserve_share=reserve_share,
    )
    state.finance.loan_interest_rate = max(
        Decimal("0.0000"),
        state.finance.loan_interest_rate - BALANCE.capital_plan_debt_strategy_interest_relief,
    )
    state.finance.board_pressure = max(
        0,
        state.finance.board_pressure - BALANCE.capital_plan_debt_strategy_board_pressure_relief,
    )
    state.finance.covenant_risk = max(
        0,
        state.finance.covenant_risk - BALANCE.capital_plan_debt_strategy_covenant_relief,
    )
    state.finance.investor_pressure = max(
        0,
        state.finance.investor_pressure
        - BALANCE.capital_plan_debt_strategy_investor_pressure_relief,
    )
    state.finance.board_confidence = min(
        100,
        state.finance.board_confidence + BALANCE.capital_plan_debt_strategy_board_confidence_gain,
    )
    return CapitalPlanSummary(
        message=(
            "Set a debt strategy. "
            f"Debt paydown {format_money(paydown)}, reserve target {format_money(reserve_target)} "
            f"over {planning_horizon_turns} turns. Allocation now P {product_share}% / GTM "
            f"{go_to_market_share}% / Reserve {reserve_share}% with "
            f"{source_preference.value} capital."
        ),
        capital_plan=state.capital_plan,
    )


def apply_set_growth_firebreak(state: GameState) -> CapitalPlanSummary:
    """Shift the capital plan toward resilience when growth pressure is outrunning control."""

    if (
        state.finance.board_pressure < 22
        and state.finance.governance_risk < 46
        and state.support_program.backlog_queue < 10
        and state.support_program.escalation_queue < 4
    ):
        raise ValueError("There is not enough capital or governance stress for a growth firebreak.")
    if state.company.cash_on_hand < BALANCE.capital_plan_growth_firebreak_cost:
        raise ValueError("Not enough cash to set a growth firebreak this turn.")

    capital_plan = state.capital_plan
    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.capital_plan_growth_firebreak_cost
    )
    reserve_target = quantize_money(
        capital_plan.reserve_target + BALANCE.capital_plan_growth_firebreak_target_step
    )
    planning_horizon_turns = min(
        12,
        capital_plan.planning_horizon_turns + BALANCE.capital_plan_growth_firebreak_horizon_gain,
    )
    reserve_share = (
        capital_plan.reserve_share + BALANCE.capital_plan_growth_firebreak_reserve_share_shift
    )
    go_to_market_share = max(
        0,
        capital_plan.go_to_market_share - BALANCE.capital_plan_growth_firebreak_gtm_share_shift,
    )
    product_share = max(
        0,
        capital_plan.product_investment_share
        - BALANCE.capital_plan_growth_firebreak_product_share_shift,
    )
    product_share, go_to_market_share, reserve_share = _normalize_capital_shares(
        product_share,
        go_to_market_share,
        reserve_share,
    )

    if capital_plan.source_preference is CapitalSourcePreference.DEBT:
        source_preference = CapitalSourcePreference.BOOTSTRAP
    elif capital_plan.source_preference is CapitalSourcePreference.VENTURE:
        source_preference = CapitalSourcePreference.ANGEL
    else:
        source_preference = capital_plan.source_preference

    mode = (
        CapitalPlanMode.CONSERVE
        if capital_plan.mode is CapitalPlanMode.EXPAND
        or state.finance.board_pressure >= 28
        or state.finance.governance_risk >= 50
        else CapitalPlanMode.BALANCED
    )
    state.capital_plan = CapitalPlan(
        mode=mode,
        source_preference=source_preference,
        planning_horizon_turns=planning_horizon_turns,
        reserve_target=reserve_target,
        product_investment_share=product_share,
        go_to_market_share=go_to_market_share,
        reserve_share=reserve_share,
    )
    state.finance.board_pressure = max(
        0,
        state.finance.board_pressure - BALANCE.capital_plan_growth_firebreak_board_pressure_relief,
    )
    state.finance.governance_risk = max(
        0,
        state.finance.governance_risk
        - BALANCE.capital_plan_growth_firebreak_governance_risk_relief,
    )
    state.finance.investor_pressure = max(
        0,
        state.finance.investor_pressure
        - BALANCE.capital_plan_growth_firebreak_investor_pressure_relief,
    )
    state.finance.board_confidence = min(
        100,
        state.finance.board_confidence
        + BALANCE.capital_plan_growth_firebreak_board_confidence_gain,
    )
    return CapitalPlanSummary(
        message=(
            "Set a growth firebreak. "
            f"Reserve target {format_money(reserve_target)} over {planning_horizon_turns} turns. "
            f"Allocation now P {product_share}% / GTM {go_to_market_share}% / "
            f"Reserve {reserve_share}% with {source_preference.value} capital."
        ),
        capital_plan=state.capital_plan,
    )


def apply_set_path_capital_posture(state: GameState) -> CapitalPlanSummary:
    """Set a path-aware capital posture that matches the current late-game route."""

    readiness = calculate_endgame_readiness(state)
    queue_exposure = calculate_support_queue_exposure(state)
    portfolio = calculate_partnership_portfolio(state)
    reserve_gap = state.capital_plan.reserve_target - state.company.cash_on_hand

    if (
        state.finance.board_pressure < 18
        and state.finance.governance_risk < 40
        and state.finance.covenant_risk < 12
        and reserve_gap <= Decimal("0.00")
        and queue_exposure.enterprise_queue_risk_accounts <= 0
        and queue_exposure.white_glove_queue_risk_accounts <= 0
        and portfolio.hotspot_dependency_score
        < BALANCE.finance_planner_reactivate_dependency_threshold
    ):
        raise ValueError("There is not enough path pressure to justify a path capital posture.")
    if state.company.cash_on_hand < BALANCE.capital_plan_path_capital_posture_cost:
        raise ValueError("Not enough cash to set a path capital posture this turn.")

    capital_plan = state.capital_plan
    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.capital_plan_path_capital_posture_cost
    )
    reserve_target = quantize_money(
        capital_plan.reserve_target + BALANCE.capital_plan_path_capital_posture_target_step
    )
    planning_horizon_turns = min(
        12,
        capital_plan.planning_horizon_turns
        + BALANCE.capital_plan_path_capital_posture_horizon_gain,
    )
    reserve_share = (
        capital_plan.reserve_share + BALANCE.capital_plan_path_capital_posture_reserve_share_shift
    )
    go_to_market_share = max(
        0,
        capital_plan.go_to_market_share - BALANCE.capital_plan_path_capital_posture_gtm_share_shift,
    )
    product_share = max(
        0,
        capital_plan.product_investment_share
        - BALANCE.capital_plan_path_capital_posture_product_share_shift,
    )
    source_preference = capital_plan.source_preference
    mode = CapitalPlanMode.BALANCED
    posture_note = readiness.strategic_outlook.replace("_", " ")

    if readiness.strategic_outlook == "ipo_ready":
        if source_preference is CapitalSourcePreference.DEBT:
            source_preference = CapitalSourcePreference.BOOTSTRAP
        elif source_preference is CapitalSourcePreference.VENTURE:
            source_preference = CapitalSourcePreference.ANGEL
        product_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    elif readiness.strategic_outlook == "strategic_acquisition":
        if source_preference is CapitalSourcePreference.DEBT:
            source_preference = CapitalSourcePreference.ANGEL
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    else:
        source_preference = CapitalSourcePreference.BOOTSTRAP
        reserve_share += 2
        go_to_market_share = max(0, go_to_market_share - 2)
        mode = CapitalPlanMode.CONSERVE

    if queue_exposure.enterprise_queue_risk_accounts > 0:
        product_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if queue_exposure.white_glove_queue_risk_accounts > 0:
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if (
        portfolio.hotspot_dependency_score
        >= BALANCE.finance_planner_reactivate_dependency_threshold
    ):
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)

    if (
        capital_plan.mode is CapitalPlanMode.EXPAND
        or state.finance.board_pressure >= 28
        or state.finance.governance_risk >= 50
    ):
        mode = CapitalPlanMode.CONSERVE

    product_share, go_to_market_share, reserve_share = _normalize_capital_shares(
        product_share,
        go_to_market_share,
        reserve_share,
    )
    state.capital_plan = CapitalPlan(
        mode=mode,
        source_preference=source_preference,
        planning_horizon_turns=planning_horizon_turns,
        reserve_target=reserve_target,
        product_investment_share=product_share,
        go_to_market_share=go_to_market_share,
        reserve_share=reserve_share,
    )
    state.finance.board_pressure = max(
        0,
        state.finance.board_pressure
        - BALANCE.capital_plan_path_capital_posture_board_pressure_relief,
    )
    state.finance.governance_risk = max(
        0,
        state.finance.governance_risk
        - BALANCE.capital_plan_path_capital_posture_governance_risk_relief,
    )
    state.finance.investor_pressure = max(
        0,
        state.finance.investor_pressure
        - BALANCE.capital_plan_path_capital_posture_investor_pressure_relief,
    )
    state.finance.board_confidence = min(
        100,
        state.finance.board_confidence
        + BALANCE.capital_plan_path_capital_posture_board_confidence_gain,
    )
    return CapitalPlanSummary(
        message=(
            f"Set a {posture_note} capital posture. Reserve target "
            f"{format_money(reserve_target)} over {planning_horizon_turns} turns. Allocation now "
            f"P {product_share}% / GTM {go_to_market_share}% / Reserve {reserve_share}% with "
            f"{source_preference.value} capital."
        ),
        capital_plan=state.capital_plan,
    )


def apply_set_endgame_capital_map(state: GameState) -> CapitalPlanSummary:
    """Aggressively remap capital to the current late-game path and its active fragilities."""

    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    queue_exposure = calculate_support_queue_exposure(state)
    portfolio = calculate_partnership_portfolio(state)
    reserve_gap = state.capital_plan.reserve_target - state.company.cash_on_hand

    if (
        pressure.board_reset_risk < 60
        and pressure.public_market_scrutiny < 62
        and pressure.acquirer_diligence < 62
        and pressure.independence_discipline < 62
        and state.finance.governance_risk < 46
        and state.finance.covenant_risk < 14
        and reserve_gap <= Decimal("0.00")
        and queue_exposure.hotspot_lane_overflow <= 0
        and portfolio.hotspot_dependency_score
        < BALANCE.finance_planner_reactivate_dependency_threshold
    ):
        raise ValueError("There is not enough late-game strain to justify an endgame capital map.")
    if state.company.cash_on_hand < BALANCE.capital_plan_endgame_capital_map_cost:
        raise ValueError("Not enough cash to set an endgame capital map this turn.")

    capital_plan = state.capital_plan
    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.capital_plan_endgame_capital_map_cost
    )
    reserve_target = quantize_money(
        capital_plan.reserve_target + BALANCE.capital_plan_endgame_capital_map_target_step
    )
    planning_horizon_turns = min(
        12,
        capital_plan.planning_horizon_turns + BALANCE.capital_plan_endgame_capital_map_horizon_gain,
    )
    reserve_share = (
        capital_plan.reserve_share + BALANCE.capital_plan_endgame_capital_map_reserve_share_shift
    )
    go_to_market_share = max(
        0,
        capital_plan.go_to_market_share - BALANCE.capital_plan_endgame_capital_map_gtm_share_shift,
    )
    product_share = max(
        0,
        capital_plan.product_investment_share
        - BALANCE.capital_plan_endgame_capital_map_product_share_shift,
    )
    source_preference = capital_plan.source_preference
    mode = CapitalPlanMode.BALANCED
    map_note = readiness.strategic_outlook.replace("_", " ")

    if (
        pressure.board_reset_risk >= 64
        or state.finance.governance_risk >= 52
        or state.finance.restructuring_pressure >= 44
    ):
        source_preference = CapitalSourcePreference.BOOTSTRAP
        reserve_share += 3
        go_to_market_share = max(0, go_to_market_share - 2)
        mode = CapitalPlanMode.CONSERVE
        map_note = "board reset"
    elif readiness.strategic_outlook == "ipo_ready":
        if source_preference in {
            CapitalSourcePreference.DEBT,
            CapitalSourcePreference.VENTURE,
        }:
            source_preference = CapitalSourcePreference.ANGEL
        product_share += 2
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 3)
    elif readiness.strategic_outlook == "strategic_acquisition":
        if source_preference is CapitalSourcePreference.DEBT:
            source_preference = CapitalSourcePreference.ANGEL
        reserve_share += 2
        product_share += 1
        go_to_market_share = max(0, go_to_market_share - 3)
    else:
        source_preference = CapitalSourcePreference.BOOTSTRAP
        reserve_share += 3
        go_to_market_share = max(0, go_to_market_share - 3)
        mode = CapitalPlanMode.CONSERVE

    if queue_exposure.hotspot_lane_overflow > 0:
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if queue_exposure.white_glove_queue_risk_accounts > 0:
        product_share += 1
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if (
        queue_exposure.renewal_queue_risk_accounts > 0
        and readiness.strategic_outlook != "ipo_ready"
    ):
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if (
        portfolio.hotspot_dependency_score
        >= BALANCE.finance_planner_reactivate_dependency_threshold
    ):
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if reserve_gap > Decimal("0.00") or state.finance.covenant_risk >= 16:
        reserve_share += 1

    if (
        capital_plan.mode is CapitalPlanMode.EXPAND
        or state.finance.board_pressure >= 28
        or state.finance.governance_risk >= 50
        or pressure.board_reset_risk >= 64
    ):
        mode = CapitalPlanMode.CONSERVE

    product_share, go_to_market_share, reserve_share = _normalize_capital_shares(
        product_share,
        go_to_market_share,
        reserve_share,
    )
    state.capital_plan = CapitalPlan(
        mode=mode,
        source_preference=source_preference,
        planning_horizon_turns=planning_horizon_turns,
        reserve_target=reserve_target,
        product_investment_share=product_share,
        go_to_market_share=go_to_market_share,
        reserve_share=reserve_share,
    )
    state.finance.board_pressure = max(
        0,
        state.finance.board_pressure
        - BALANCE.capital_plan_endgame_capital_map_board_pressure_relief,
    )
    state.finance.governance_risk = max(
        0,
        state.finance.governance_risk
        - BALANCE.capital_plan_endgame_capital_map_governance_risk_relief,
    )
    state.finance.investor_pressure = max(
        0,
        state.finance.investor_pressure
        - BALANCE.capital_plan_endgame_capital_map_investor_pressure_relief,
    )
    state.finance.covenant_risk = max(
        0,
        state.finance.covenant_risk - BALANCE.capital_plan_endgame_capital_map_covenant_relief,
    )
    state.finance.board_confidence = min(
        100,
        state.finance.board_confidence
        + BALANCE.capital_plan_endgame_capital_map_board_confidence_gain,
    )
    return CapitalPlanSummary(
        message=(
            f"Set an endgame capital map for the {map_note} story. Reserve target "
            f"{format_money(reserve_target)} over {planning_horizon_turns} turns. Allocation now "
            f"P {product_share}% / GTM {go_to_market_share}% / Reserve {reserve_share}% with "
            f"{source_preference.value} capital."
        ),
        capital_plan=state.capital_plan,
    )


def apply_set_exit_readiness_buffer(state: GameState) -> CapitalPlanSummary:
    """Build a tighter path-aware liquidity buffer before late-game pressure hardens."""

    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    queue_exposure = calculate_support_queue_exposure(state)
    portfolio = calculate_partnership_portfolio(state)
    reserve_gap = state.capital_plan.reserve_target - state.company.cash_on_hand

    if (
        pressure.board_reset_risk < 58
        and pressure.public_market_scrutiny < 58
        and pressure.acquirer_diligence < 58
        and pressure.independence_discipline < 58
        and state.finance.governance_risk < 42
        and state.finance.covenant_risk < 12
        and reserve_gap <= Decimal("0.00")
        and queue_exposure.hotspot_lane_overflow <= 0
        and portfolio.hotspot_dependency_score
        < BALANCE.finance_planner_reactivate_dependency_threshold
    ):
        raise ValueError(
            "There is not enough late-game strain to justify an exit-readiness buffer."
        )
    if state.company.cash_on_hand < BALANCE.capital_plan_endgame_capital_map_cost:
        raise ValueError("Not enough cash to set an exit-readiness buffer this turn.")

    capital_plan = state.capital_plan
    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.capital_plan_endgame_capital_map_cost
    )
    reserve_target = quantize_money(
        capital_plan.reserve_target + BALANCE.capital_plan_endgame_capital_map_target_step
    )
    planning_horizon_turns = min(
        12,
        capital_plan.planning_horizon_turns
        + BALANCE.capital_plan_path_capital_posture_horizon_gain,
    )
    product_share = capital_plan.product_investment_share
    go_to_market_share = capital_plan.go_to_market_share
    reserve_share = capital_plan.reserve_share
    source_preference = capital_plan.source_preference
    mode = capital_plan.mode
    buffer_note = readiness.strategic_outlook.replace("_", " ")

    if (
        pressure.board_reset_risk >= 62
        or pressure.dominant_pressure == "board_reset_risk"
        or state.finance.governance_risk >= 48
        or state.finance.restructuring_pressure >= 42
    ):
        source_preference = CapitalSourcePreference.BOOTSTRAP
        reserve_share += 5
        go_to_market_share = max(0, go_to_market_share - 4)
        product_share = max(0, product_share - 1)
        mode = CapitalPlanMode.CONSERVE
        buffer_note = "board reset"
    elif readiness.strategic_outlook == "ipo_ready":
        if source_preference in {
            CapitalSourcePreference.DEBT,
            CapitalSourcePreference.VENTURE,
        }:
            source_preference = CapitalSourcePreference.ANGEL
        reserve_share += 3
        go_to_market_share = max(0, go_to_market_share - 3)
        product_share += 1
        buffer_note = "IPO readiness"
    elif readiness.strategic_outlook == "strategic_acquisition":
        if source_preference is CapitalSourcePreference.DEBT:
            source_preference = CapitalSourcePreference.ANGEL
        reserve_share += 3
        go_to_market_share = max(0, go_to_market_share - 3)
        product_share += 1
        buffer_note = "buyer-close"
    else:
        source_preference = CapitalSourcePreference.BOOTSTRAP
        reserve_share += 4
        go_to_market_share = max(0, go_to_market_share - 3)
        product_share = max(0, product_share - 1)
        mode = CapitalPlanMode.CONSERVE
        buffer_note = "independence"

    if queue_exposure.hotspot_lane_overflow > 0:
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if queue_exposure.white_glove_queue_risk_accounts > 0:
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if queue_exposure.renewal_queue_risk_accounts > 0:
        reserve_share += 1
        product_share = max(0, product_share - 1)
    if (
        portfolio.hotspot_dependency_score
        >= BALANCE.finance_planner_reactivate_dependency_threshold
    ):
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if reserve_gap > Decimal("0.00") or state.finance.covenant_risk >= 14:
        reserve_share += 1
        product_share = max(0, product_share - 1)

    if (
        capital_plan.mode is CapitalPlanMode.EXPAND
        or state.finance.board_pressure >= 26
        or state.finance.governance_risk >= 46
        or pressure.board_reset_risk >= 62
    ):
        mode = CapitalPlanMode.CONSERVE

    product_share, go_to_market_share, reserve_share = _normalize_capital_shares(
        product_share,
        go_to_market_share,
        reserve_share,
    )
    state.capital_plan = CapitalPlan(
        mode=mode,
        source_preference=source_preference,
        planning_horizon_turns=planning_horizon_turns,
        reserve_target=reserve_target,
        product_investment_share=product_share,
        go_to_market_share=go_to_market_share,
        reserve_share=reserve_share,
    )
    state.finance.board_pressure = max(
        0,
        state.finance.board_pressure
        - BALANCE.capital_plan_endgame_capital_map_board_pressure_relief,
    )
    state.finance.governance_risk = max(
        0,
        state.finance.governance_risk
        - BALANCE.capital_plan_endgame_capital_map_governance_risk_relief,
    )
    state.finance.investor_pressure = max(
        0,
        state.finance.investor_pressure
        - BALANCE.capital_plan_endgame_capital_map_investor_pressure_relief,
    )
    state.finance.covenant_risk = max(
        0,
        state.finance.covenant_risk - BALANCE.capital_plan_endgame_capital_map_covenant_relief,
    )
    state.finance.board_confidence = min(
        100,
        state.finance.board_confidence
        + BALANCE.capital_plan_endgame_capital_map_board_confidence_gain,
    )
    return CapitalPlanSummary(
        message=(
            f"Set an exit-readiness buffer for the {buffer_note} story. Reserve target "
            f"{format_money(reserve_target)} over {planning_horizon_turns} turns. Allocation now "
            f"P {product_share}% / GTM {go_to_market_share}% / Reserve {reserve_share}% with "
            f"{source_preference.value} capital."
        ),
        capital_plan=state.capital_plan,
    )


def apply_set_terminal_liquidity_controls(state: GameState) -> CapitalPlanSummary:
    """Force the hardest path-aware liquidity controls once late-game fragility dominates."""

    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    queue_exposure = calculate_support_queue_exposure(state)
    portfolio = calculate_partnership_portfolio(state)
    reserve_gap = state.capital_plan.reserve_target - state.company.cash_on_hand
    cost = quantize_money(
        BALANCE.capital_plan_endgame_capital_map_cost
        + BALANCE.capital_plan_path_capital_posture_cost
    )

    if (
        pressure.board_reset_risk < 64
        and pressure.public_market_scrutiny < 64
        and pressure.acquirer_diligence < 64
        and pressure.independence_discipline < 64
        and state.finance.governance_risk < 48
        and state.finance.covenant_risk < 16
        and reserve_gap <= Decimal("0.00")
        and queue_exposure.hotspot_lane_overflow <= 0
        and portfolio.hotspot_dependency_score
        < BALANCE.finance_planner_reactivate_dependency_threshold
    ):
        raise ValueError(
            "There is not enough terminal late-game strain to justify liquidity controls."
        )
    if state.company.cash_on_hand < cost:
        raise ValueError("Not enough cash to set terminal liquidity controls this turn.")

    capital_plan = state.capital_plan
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - cost)
    reserve_target = quantize_money(
        capital_plan.reserve_target
        + BALANCE.capital_plan_endgame_capital_map_target_step
        + BALANCE.capital_plan_path_capital_posture_target_step
    )
    planning_horizon_turns = min(
        12,
        capital_plan.planning_horizon_turns
        + BALANCE.capital_plan_path_capital_posture_horizon_gain
        + BALANCE.capital_plan_path_capital_posture_horizon_gain,
    )
    product_share = max(
        0,
        capital_plan.product_investment_share
        - BALANCE.capital_plan_path_capital_posture_product_share_shift,
    )
    go_to_market_share = max(
        0,
        capital_plan.go_to_market_share
        - BALANCE.capital_plan_path_capital_posture_gtm_share_shift
        - 2,
    )
    reserve_share = (
        capital_plan.reserve_share
        + BALANCE.capital_plan_path_capital_posture_reserve_share_shift
        + 3
    )
    source_preference = capital_plan.source_preference
    mode = CapitalPlanMode.CONSERVE
    control_note = readiness.strategic_outlook.replace("_", " ")

    if (
        pressure.board_reset_risk >= 64
        or state.finance.governance_risk >= 50
        or pressure.dominant_pressure == "board_reset_risk"
    ):
        source_preference = CapitalSourcePreference.BOOTSTRAP
        reserve_share += 2
        go_to_market_share = max(0, go_to_market_share - 2)
        product_share = max(0, product_share - 1)
        control_note = "board reset"
    elif readiness.strategic_outlook == "ipo_ready":
        if source_preference in {
            CapitalSourcePreference.DEBT,
            CapitalSourcePreference.VENTURE,
        }:
            source_preference = CapitalSourcePreference.ANGEL
        reserve_share += 1
        product_share += 1
        control_note = "IPO readiness"
    elif readiness.strategic_outlook == "strategic_acquisition":
        if source_preference is CapitalSourcePreference.DEBT:
            source_preference = CapitalSourcePreference.ANGEL
        reserve_share += 1
        product_share += 1
        control_note = "buyer close"
    else:
        source_preference = CapitalSourcePreference.BOOTSTRAP
        reserve_share += 2
        go_to_market_share = max(0, go_to_market_share - 1)
        product_share = max(0, product_share - 1)
        control_note = "independence"

    if queue_exposure.hotspot_lane_overflow > 0:
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if queue_exposure.white_glove_queue_risk_accounts > 0:
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if queue_exposure.renewal_queue_risk_accounts > 0:
        reserve_share += 1
        product_share = max(0, product_share - 1)
    if (
        portfolio.hotspot_dependency_score
        >= BALANCE.finance_planner_reactivate_dependency_threshold
    ):
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if reserve_gap > Decimal("0.00") or state.finance.covenant_risk >= 16:
        reserve_share += 1
        product_share = max(0, product_share - 1)

    product_share, go_to_market_share, reserve_share = _normalize_capital_shares(
        product_share,
        go_to_market_share,
        reserve_share,
    )
    state.capital_plan = CapitalPlan(
        mode=mode,
        source_preference=source_preference,
        planning_horizon_turns=planning_horizon_turns,
        reserve_target=reserve_target,
        product_investment_share=product_share,
        go_to_market_share=go_to_market_share,
        reserve_share=reserve_share,
    )
    state.finance.board_pressure = max(
        0,
        state.finance.board_pressure
        - (
            BALANCE.capital_plan_endgame_capital_map_board_pressure_relief
            + BALANCE.capital_plan_path_capital_posture_board_pressure_relief
        ),
    )
    state.finance.governance_risk = max(
        0,
        state.finance.governance_risk
        - (
            BALANCE.capital_plan_endgame_capital_map_governance_risk_relief
            + BALANCE.capital_plan_path_capital_posture_governance_risk_relief
        ),
    )
    state.finance.investor_pressure = max(
        0,
        state.finance.investor_pressure
        - (
            BALANCE.capital_plan_endgame_capital_map_investor_pressure_relief
            + BALANCE.capital_plan_path_capital_posture_investor_pressure_relief
        ),
    )
    state.finance.covenant_risk = max(
        0,
        state.finance.covenant_risk - BALANCE.capital_plan_endgame_capital_map_covenant_relief,
    )
    state.finance.board_confidence = min(
        100,
        state.finance.board_confidence
        + BALANCE.capital_plan_endgame_capital_map_board_confidence_gain
        + BALANCE.capital_plan_path_capital_posture_board_confidence_gain,
    )
    return CapitalPlanSummary(
        message=(
            f"Set terminal liquidity controls for the {control_note} path. Reserve target "
            f"{format_money(reserve_target)} over {planning_horizon_turns} turns. Allocation now "
            f"P {product_share}% / GTM {go_to_market_share}% / Reserve {reserve_share}% with "
            f"{source_preference.value} capital."
        ),
        capital_plan=state.capital_plan,
    )


def apply_set_capital_reallocation_grid(state: GameState) -> CapitalPlanSummary:
    """Force a deeper endgame capital map once queue drag, dependency, and fragility align."""

    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    queue_exposure = calculate_support_queue_exposure(state)
    portfolio = calculate_partnership_portfolio(state)
    reserve_gap = state.capital_plan.reserve_target - state.company.cash_on_hand
    cost = quantize_money(
        BALANCE.capital_plan_endgame_capital_map_cost
        + BALANCE.capital_plan_path_capital_posture_cost
        + BALANCE.capital_plan_growth_firebreak_cost
    )

    if (
        pressure.board_reset_risk < 68
        and pressure.public_market_scrutiny < 68
        and pressure.acquirer_diligence < 68
        and pressure.independence_discipline < 68
        and state.finance.governance_risk < 50
        and state.finance.covenant_risk < 18
        and reserve_gap <= Decimal("0.00")
        and queue_exposure.hotspot_lane_overflow <= 0
        and portfolio.hotspot_dependency_score
        < BALANCE.finance_planner_reactivate_dependency_threshold
    ):
        raise ValueError(
            "There is not enough combined late-game strain to justify a capital reallocation grid."
        )
    if state.company.cash_on_hand < cost:
        raise ValueError("Not enough cash to set a capital reallocation grid this turn.")

    capital_plan = state.capital_plan
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - cost)
    reserve_target = quantize_money(
        capital_plan.reserve_target
        + BALANCE.capital_plan_endgame_capital_map_target_step
        + BALANCE.capital_plan_path_capital_posture_target_step
        + BALANCE.capital_plan_growth_firebreak_target_step
    )
    planning_horizon_turns = min(
        12,
        capital_plan.planning_horizon_turns
        + BALANCE.capital_plan_path_capital_posture_horizon_gain
        + BALANCE.capital_plan_growth_firebreak_horizon_gain,
    )
    product_share = max(
        0,
        capital_plan.product_investment_share
        - BALANCE.capital_plan_path_capital_posture_product_share_shift
        - BALANCE.capital_plan_growth_firebreak_product_share_shift,
    )
    go_to_market_share = max(
        0,
        capital_plan.go_to_market_share
        - BALANCE.capital_plan_path_capital_posture_gtm_share_shift
        - BALANCE.capital_plan_growth_firebreak_gtm_share_shift,
    )
    reserve_share = (
        capital_plan.reserve_share
        + BALANCE.capital_plan_path_capital_posture_reserve_share_shift
        + BALANCE.capital_plan_growth_firebreak_reserve_share_shift
        + 2
    )
    mode = CapitalPlanMode.CONSERVE
    source_preference = capital_plan.source_preference
    control_note = readiness.strategic_outlook.replace("_", " ")

    if (
        pressure.board_reset_risk >= 68
        or state.finance.governance_risk >= 52
        or pressure.dominant_pressure == "board_reset_risk"
    ):
        source_preference = CapitalSourcePreference.BOOTSTRAP
        reserve_share += 2
        product_share = max(0, product_share - 1)
        go_to_market_share = max(0, go_to_market_share - 2)
        control_note = "board reset"
    elif readiness.strategic_outlook == "ipo_ready":
        if source_preference in {
            CapitalSourcePreference.DEBT,
            CapitalSourcePreference.VENTURE,
        }:
            source_preference = CapitalSourcePreference.ANGEL
        reserve_share += 1
        product_share += 1
        control_note = "IPO readiness"
    elif readiness.strategic_outlook == "strategic_acquisition":
        if source_preference is CapitalSourcePreference.DEBT:
            source_preference = CapitalSourcePreference.ANGEL
        reserve_share += 1
        product_share += 1
        control_note = "buyer close"
    else:
        source_preference = CapitalSourcePreference.BOOTSTRAP
        reserve_share += 2
        product_share = max(0, product_share - 1)
        go_to_market_share = max(0, go_to_market_share - 1)
        control_note = "independence"

    if queue_exposure.hotspot_lane_overflow > 0:
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if queue_exposure.enterprise_queue_risk_accounts > 0:
        reserve_share += 1
        product_share += 1
    if queue_exposure.white_glove_queue_risk_accounts > 0:
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if queue_exposure.renewal_queue_risk_accounts > 0:
        reserve_share += 1
        product_share = max(0, product_share - 1)
    if (
        portfolio.hotspot_dependency_score
        >= BALANCE.finance_planner_reactivate_dependency_threshold
    ):
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if reserve_gap > Decimal("0.00") or state.finance.covenant_risk >= 18:
        reserve_share += 1
        product_share = max(0, product_share - 1)

    product_share, go_to_market_share, reserve_share = _normalize_capital_shares(
        product_share,
        go_to_market_share,
        reserve_share,
    )
    state.capital_plan = CapitalPlan(
        mode=mode,
        source_preference=source_preference,
        planning_horizon_turns=planning_horizon_turns,
        reserve_target=reserve_target,
        product_investment_share=product_share,
        go_to_market_share=go_to_market_share,
        reserve_share=reserve_share,
    )
    state.finance.board_pressure = max(
        0,
        state.finance.board_pressure
        - (
            BALANCE.capital_plan_endgame_capital_map_board_pressure_relief
            + BALANCE.capital_plan_path_capital_posture_board_pressure_relief
            + BALANCE.capital_plan_growth_firebreak_board_pressure_relief
        ),
    )
    state.finance.governance_risk = max(
        0,
        state.finance.governance_risk
        - (
            BALANCE.capital_plan_endgame_capital_map_governance_risk_relief
            + BALANCE.capital_plan_path_capital_posture_governance_risk_relief
        ),
    )
    state.finance.investor_pressure = max(
        0,
        state.finance.investor_pressure
        - (
            BALANCE.capital_plan_endgame_capital_map_investor_pressure_relief
            + BALANCE.capital_plan_path_capital_posture_investor_pressure_relief
        ),
    )
    state.finance.covenant_risk = max(
        0,
        state.finance.covenant_risk - BALANCE.capital_plan_endgame_capital_map_covenant_relief,
    )
    state.finance.board_confidence = min(
        100,
        state.finance.board_confidence
        + BALANCE.capital_plan_endgame_capital_map_board_confidence_gain
        + BALANCE.capital_plan_path_capital_posture_board_confidence_gain
        + 1,
    )
    return CapitalPlanSummary(
        message=(
            f"Set a capital reallocation grid for the {control_note} path. Reserve target "
            f"{format_money(reserve_target)} over {planning_horizon_turns} turns. Allocation now "
            f"P {product_share}% / GTM {go_to_market_share}% / Reserve {reserve_share}% with "
            f"{source_preference.value} capital."
        ),
        capital_plan=state.capital_plan,
    )


def apply_set_path_control_matrix(state: GameState) -> CapitalPlanSummary:
    """Apply the hardest cross-system capital posture once one endgame path is clearly at risk."""

    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    queue_exposure = calculate_support_queue_exposure(state)
    portfolio = calculate_partnership_portfolio(state)
    reserve_gap = state.capital_plan.reserve_target - state.company.cash_on_hand
    extra_cost = quantize_money(
        BALANCE.capital_plan_endgame_capital_map_cost
        + BALANCE.capital_plan_path_capital_posture_cost
    )
    total_cost = quantize_money(
        BALANCE.capital_plan_endgame_capital_map_cost
        + BALANCE.capital_plan_path_capital_posture_cost
        + BALANCE.capital_plan_growth_firebreak_cost
        + extra_cost
    )

    if (
        pressure.board_reset_risk < 72
        and pressure.public_market_scrutiny < 72
        and pressure.acquirer_diligence < 72
        and pressure.independence_discipline < 72
        and state.finance.governance_risk < 54
        and state.finance.covenant_risk < 20
        and reserve_gap <= Decimal("0.00")
        and queue_exposure.hotspot_lane_overflow <= 1
        and portfolio.hotspot_dependency_score
        < BALANCE.finance_planner_reactivate_dependency_threshold + 4
    ):
        raise ValueError(
            "There is not enough path-specific late-game strain to justify a path control matrix."
        )
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to set a path control matrix this turn.")

    apply_set_capital_reallocation_grid(state)
    capital_plan = state.capital_plan
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    reserve_target = quantize_money(
        capital_plan.reserve_target
        + BALANCE.capital_plan_endgame_capital_map_target_step
        + BALANCE.capital_plan_path_capital_posture_target_step
    )
    planning_horizon_turns = min(
        12,
        capital_plan.planning_horizon_turns
        + BALANCE.capital_plan_path_capital_posture_horizon_gain,
    )
    product_share = max(
        0,
        capital_plan.product_investment_share
        - BALANCE.capital_plan_path_capital_posture_product_share_shift,
    )
    go_to_market_share = max(
        0,
        capital_plan.go_to_market_share - BALANCE.capital_plan_path_capital_posture_gtm_share_shift,
    )
    reserve_share = (
        capital_plan.reserve_share
        + BALANCE.capital_plan_path_capital_posture_reserve_share_shift
        + 1
    )
    source_preference = capital_plan.source_preference
    mode = CapitalPlanMode.CONSERVE
    control_note = readiness.strategic_outlook.replace("_", " ")

    if (
        pressure.board_reset_risk >= 72
        or pressure.dominant_pressure == "board_reset_risk"
        or state.finance.governance_risk >= 56
    ):
        source_preference = CapitalSourcePreference.BOOTSTRAP
        reserve_share += 2
        go_to_market_share = max(0, go_to_market_share - 1)
        product_share = max(0, product_share - 1)
        control_note = "board reset"
    elif readiness.strategic_outlook == "ipo_ready":
        if source_preference in {
            CapitalSourcePreference.DEBT,
            CapitalSourcePreference.VENTURE,
        }:
            source_preference = CapitalSourcePreference.ANGEL
        reserve_share += 1
        product_share += 1
        control_note = "IPO readiness"
    elif readiness.strategic_outlook == "strategic_acquisition":
        if source_preference is CapitalSourcePreference.DEBT:
            source_preference = CapitalSourcePreference.ANGEL
        reserve_share += 1
        product_share += 1
        control_note = "buyer close"
    else:
        source_preference = CapitalSourcePreference.BOOTSTRAP
        reserve_share += 2
        go_to_market_share = max(0, go_to_market_share - 1)
        control_note = "independence"

    if queue_exposure.hotspot_lane_overflow > 0:
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if queue_exposure.enterprise_queue_risk_accounts > 0:
        reserve_share += 1
        product_share += 1
    if queue_exposure.white_glove_queue_risk_accounts > 0:
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if queue_exposure.renewal_queue_risk_accounts > 0:
        reserve_share += 1
        product_share = max(0, product_share - 1)
    if (
        portfolio.hotspot_dependency_score
        >= BALANCE.finance_planner_reactivate_dependency_threshold
    ):
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if reserve_gap > Decimal("0.00") or state.finance.covenant_risk >= 18:
        reserve_share += 1
        product_share = max(0, product_share - 1)

    product_share, go_to_market_share, reserve_share = _normalize_capital_shares(
        product_share,
        go_to_market_share,
        reserve_share,
    )
    state.capital_plan = CapitalPlan(
        mode=mode,
        source_preference=source_preference,
        planning_horizon_turns=planning_horizon_turns,
        reserve_target=reserve_target,
        product_investment_share=product_share,
        go_to_market_share=go_to_market_share,
        reserve_share=reserve_share,
    )
    state.finance.board_pressure = max(
        0,
        state.finance.board_pressure
        - BALANCE.capital_plan_path_capital_posture_board_pressure_relief,
    )
    state.finance.governance_risk = max(
        0,
        state.finance.governance_risk
        - BALANCE.capital_plan_path_capital_posture_governance_risk_relief,
    )
    state.finance.investor_pressure = max(
        0,
        state.finance.investor_pressure
        - BALANCE.capital_plan_path_capital_posture_investor_pressure_relief,
    )
    state.finance.covenant_risk = max(
        0,
        state.finance.covenant_risk - BALANCE.capital_plan_endgame_capital_map_covenant_relief,
    )
    state.finance.board_confidence = min(
        100,
        state.finance.board_confidence
        + BALANCE.capital_plan_path_capital_posture_board_confidence_gain,
    )
    return CapitalPlanSummary(
        message=(
            f"Set a path control matrix for the {control_note} path. Reserve target "
            f"{format_money(reserve_target)} over {planning_horizon_turns} turns. Allocation now "
            f"P {product_share}% / GTM {go_to_market_share}% / Reserve {reserve_share}% with "
            f"{source_preference.value} capital."
        ),
        capital_plan=state.capital_plan,
    )


def apply_set_path_resilience_grid(state: GameState) -> CapitalPlanSummary:
    """Apply the hardest late-game capital control once one path dominates every other concern."""

    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    queue_exposure = calculate_support_queue_exposure(state)
    portfolio = calculate_partnership_portfolio(state)
    reserve_gap = state.capital_plan.reserve_target - state.company.cash_on_hand
    base_cost = quantize_money(
        BALANCE.capital_plan_endgame_capital_map_cost
        + BALANCE.capital_plan_path_capital_posture_cost
        + BALANCE.capital_plan_growth_firebreak_cost
        + (
            BALANCE.capital_plan_endgame_capital_map_cost
            + BALANCE.capital_plan_path_capital_posture_cost
        )
    )
    extra_cost = quantize_money(
        BALANCE.capital_plan_growth_firebreak_cost + BALANCE.capital_plan_path_capital_posture_cost
    )
    total_cost = quantize_money(base_cost + extra_cost)

    if (
        pressure.board_reset_risk < 80
        and pressure.public_market_scrutiny < 80
        and pressure.acquirer_diligence < 80
        and pressure.independence_discipline < 80
        and state.finance.governance_risk < 58
        and state.finance.covenant_risk < 22
        and reserve_gap <= Decimal("0.00")
        and queue_exposure.hotspot_lane_overflow <= 2
        and portfolio.hotspot_dependency_score
        < BALANCE.finance_planner_reactivate_dependency_threshold + 8
    ):
        raise ValueError(
            "There is not enough path-specific late-game strain to justify a path resilience grid."
        )
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to set a path resilience grid this turn.")

    apply_set_path_control_matrix(state)
    capital_plan = state.capital_plan
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    reserve_target = quantize_money(
        capital_plan.reserve_target + BALANCE.capital_plan_growth_firebreak_target_step
    )
    planning_horizon_turns = min(
        12,
        capital_plan.planning_horizon_turns + BALANCE.capital_plan_growth_firebreak_horizon_gain,
    )
    product_share = max(
        0,
        capital_plan.product_investment_share
        - BALANCE.capital_plan_growth_firebreak_product_share_shift,
    )
    go_to_market_share = max(
        0,
        capital_plan.go_to_market_share - BALANCE.capital_plan_growth_firebreak_gtm_share_shift,
    )
    reserve_share = (
        capital_plan.reserve_share + BALANCE.capital_plan_growth_firebreak_reserve_share_shift + 1
    )
    source_preference = capital_plan.source_preference
    control_note = readiness.strategic_outlook.replace("_", " ")
    if (
        pressure.board_reset_risk >= 80
        or pressure.dominant_pressure == "board_reset_risk"
        or state.finance.governance_risk >= 60
    ):
        source_preference = CapitalSourcePreference.BOOTSTRAP
        reserve_share += 1
        control_note = "board reset"
    elif readiness.strategic_outlook == "ipo_ready":
        if source_preference in {
            CapitalSourcePreference.DEBT,
            CapitalSourcePreference.VENTURE,
        }:
            source_preference = CapitalSourcePreference.ANGEL
        control_note = "IPO readiness"
    elif readiness.strategic_outlook == "strategic_acquisition":
        if source_preference is CapitalSourcePreference.DEBT:
            source_preference = CapitalSourcePreference.ANGEL
        control_note = "buyer close"
    else:
        source_preference = CapitalSourcePreference.BOOTSTRAP
        reserve_share += 1
        control_note = "independence"

    product_share, go_to_market_share, reserve_share = _normalize_capital_shares(
        product_share,
        go_to_market_share,
        reserve_share,
    )
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.CONSERVE,
        source_preference=source_preference,
        planning_horizon_turns=planning_horizon_turns,
        reserve_target=reserve_target,
        product_investment_share=product_share,
        go_to_market_share=go_to_market_share,
        reserve_share=reserve_share,
    )
    state.finance.board_pressure = max(
        0,
        state.finance.board_pressure - BALANCE.capital_plan_growth_firebreak_board_pressure_relief,
    )
    state.finance.governance_risk = max(
        0,
        state.finance.governance_risk
        - BALANCE.capital_plan_growth_firebreak_governance_risk_relief,
    )
    state.finance.investor_pressure = max(
        0,
        state.finance.investor_pressure
        - BALANCE.capital_plan_growth_firebreak_investor_pressure_relief,
    )
    state.finance.covenant_risk = max(
        0,
        state.finance.covenant_risk - BALANCE.capital_plan_endgame_capital_map_covenant_relief,
    )
    state.finance.board_confidence = min(
        100,
        state.finance.board_confidence
        + BALANCE.capital_plan_growth_firebreak_board_confidence_gain,
    )
    return CapitalPlanSummary(
        message=(
            f"Set a path resilience grid for the {control_note} path. Reserve target "
            f"{format_money(reserve_target)} over {planning_horizon_turns} turns. Allocation now "
            f"P {product_share}% / GTM {go_to_market_share}% / Reserve {reserve_share}% with "
            f"{source_preference.value} capital."
        ),
        capital_plan=state.capital_plan,
    )


def apply_set_balance_sheet_recovery_mesh(state: GameState) -> CapitalPlanSummary:
    """Apply the final late-game capital control once path pressure becomes balance-sheet risk."""

    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    queue_exposure = calculate_support_queue_exposure(state)
    portfolio = calculate_partnership_portfolio(state)
    reserve_gap = state.capital_plan.reserve_target - state.company.cash_on_hand
    base_cost = quantize_money(
        BALANCE.capital_plan_endgame_capital_map_cost * 2
        + BALANCE.capital_plan_path_capital_posture_cost * 3
        + BALANCE.capital_plan_growth_firebreak_cost * 2
    )
    extra_cost = quantize_money(
        BALANCE.capital_plan_growth_firebreak_cost + BALANCE.capital_plan_path_capital_posture_cost
    )
    total_cost = quantize_money(base_cost + extra_cost)

    if (
        pressure.board_reset_risk < 86
        and pressure.public_market_scrutiny < 86
        and pressure.acquirer_diligence < 86
        and pressure.independence_discipline < 86
        and state.finance.governance_risk < 62
        and state.finance.covenant_risk < 24
        and reserve_gap <= Decimal("0.00")
        and queue_exposure.hotspot_lane_overflow <= 3
        and portfolio.hotspot_dependency_score
        < BALANCE.finance_planner_reactivate_dependency_threshold + 12
    ):
        raise ValueError(
            "There is not enough balance-sheet strain to justify a recovery mesh right now."
        )
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to set a balance-sheet recovery mesh this turn.")

    apply_set_path_resilience_grid(state)
    capital_plan = state.capital_plan
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    reserve_target = quantize_money(
        capital_plan.reserve_target + BALANCE.capital_plan_growth_firebreak_target_step
    )
    planning_horizon_turns = min(
        12,
        capital_plan.planning_horizon_turns + BALANCE.capital_plan_growth_firebreak_horizon_gain,
    )
    product_share = max(
        0,
        capital_plan.product_investment_share
        - BALANCE.capital_plan_growth_firebreak_product_share_shift,
    )
    go_to_market_share = max(
        0,
        capital_plan.go_to_market_share - BALANCE.capital_plan_growth_firebreak_gtm_share_shift,
    )
    reserve_share = (
        capital_plan.reserve_share + BALANCE.capital_plan_growth_firebreak_reserve_share_shift + 2
    )
    source_preference = capital_plan.source_preference
    control_note = readiness.strategic_outlook.replace("_", " ")

    if (
        pressure.board_reset_risk >= 86
        or pressure.dominant_pressure == "board_reset_risk"
        or state.finance.governance_risk >= 62
    ):
        source_preference = CapitalSourcePreference.BOOTSTRAP
        reserve_share += 2
        go_to_market_share = max(0, go_to_market_share - 1)
        product_share = max(0, product_share - 1)
        control_note = "board reset"
    elif readiness.strategic_outlook == "ipo_ready":
        if source_preference in {
            CapitalSourcePreference.DEBT,
            CapitalSourcePreference.VENTURE,
        }:
            source_preference = CapitalSourcePreference.ANGEL
        reserve_share += 1
        product_share += 1
        control_note = "IPO readiness"
    elif readiness.strategic_outlook == "strategic_acquisition":
        if source_preference is CapitalSourcePreference.DEBT:
            source_preference = CapitalSourcePreference.ANGEL
        reserve_share += 1
        product_share += 1
        control_note = "buyer close"
    else:
        source_preference = CapitalSourcePreference.BOOTSTRAP
        reserve_share += 2
        go_to_market_share = max(0, go_to_market_share - 1)
        control_note = "independence"

    if queue_exposure.hotspot_lane_overflow > 1:
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if queue_exposure.enterprise_queue_risk_accounts > 1:
        reserve_share += 1
        product_share += 1
    if queue_exposure.white_glove_queue_risk_accounts > 0:
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if queue_exposure.renewal_queue_risk_accounts > 1:
        reserve_share += 1
        product_share = max(0, product_share - 1)
    if (
        portfolio.hotspot_dependency_score
        >= BALANCE.finance_planner_reactivate_dependency_threshold + 4
    ):
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if portfolio.channel_conflict_index >= 30:
        reserve_share += 1
        product_share = max(0, product_share - 1)
    if reserve_gap > Decimal("0.00") or state.finance.covenant_risk >= 20:
        reserve_share += 1
        product_share = max(0, product_share - 1)

    product_share, go_to_market_share, reserve_share = _normalize_capital_shares(
        product_share,
        go_to_market_share,
        reserve_share,
    )
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.CONSERVE,
        source_preference=source_preference,
        planning_horizon_turns=planning_horizon_turns,
        reserve_target=reserve_target,
        product_investment_share=product_share,
        go_to_market_share=go_to_market_share,
        reserve_share=reserve_share,
    )
    state.finance.board_pressure = max(
        0,
        state.finance.board_pressure
        - (
            BALANCE.capital_plan_growth_firebreak_board_pressure_relief
            + BALANCE.capital_plan_path_capital_posture_board_pressure_relief
        ),
    )
    state.finance.governance_risk = max(
        0,
        state.finance.governance_risk
        - (
            BALANCE.capital_plan_growth_firebreak_governance_risk_relief
            + BALANCE.capital_plan_path_capital_posture_governance_risk_relief
        ),
    )
    state.finance.investor_pressure = max(
        0,
        state.finance.investor_pressure
        - (
            BALANCE.capital_plan_growth_firebreak_investor_pressure_relief
            + BALANCE.capital_plan_path_capital_posture_investor_pressure_relief
        ),
    )
    state.finance.covenant_risk = max(
        0,
        state.finance.covenant_risk - BALANCE.capital_plan_endgame_capital_map_covenant_relief,
    )
    state.finance.board_confidence = min(
        100,
        state.finance.board_confidence
        + (
            BALANCE.capital_plan_growth_firebreak_board_confidence_gain
            + BALANCE.capital_plan_path_capital_posture_board_confidence_gain
        ),
    )
    return CapitalPlanSummary(
        message=(
            f"Set a balance-sheet recovery mesh for the {control_note} path. Reserve target "
            f"{format_money(reserve_target)} over {planning_horizon_turns} turns. Allocation now "
            f"P {product_share}% / GTM {go_to_market_share}% / Reserve {reserve_share}% with "
            f"{source_preference.value} capital."
        ),
        capital_plan=state.capital_plan,
    )


def apply_set_terminal_recovery_lattice(state: GameState) -> CapitalPlanSummary:
    """Apply the deepest terminal capital control when every late-game path is still fragile."""

    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    queue_exposure = calculate_support_queue_exposure(state)
    portfolio = calculate_partnership_portfolio(state)
    reserve_gap = state.capital_plan.reserve_target - state.company.cash_on_hand
    base_cost = quantize_money(
        BALANCE.capital_plan_endgame_capital_map_cost * 2
        + BALANCE.capital_plan_path_capital_posture_cost * 3
        + BALANCE.capital_plan_growth_firebreak_cost * 2
    )
    extra_cost = quantize_money(
        BALANCE.capital_plan_growth_firebreak_cost * 2
        + BALANCE.capital_plan_path_capital_posture_cost
    )
    total_cost = quantize_money(base_cost + extra_cost)

    if (
        pressure.board_reset_risk < 90
        and pressure.public_market_scrutiny < 90
        and pressure.acquirer_diligence < 90
        and pressure.independence_discipline < 90
        and state.finance.governance_risk < 60
        and state.finance.covenant_risk < 26
        and reserve_gap <= Decimal("0.00")
        and queue_exposure.hotspot_lane_overflow <= 4
        and portfolio.hotspot_dependency_score
        < BALANCE.finance_planner_reactivate_dependency_threshold + 16
    ):
        raise ValueError(
            "There is not enough terminal late-game strain to justify a recovery lattice."
        )
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to set a terminal recovery lattice this turn.")

    apply_set_balance_sheet_recovery_mesh(state)
    capital_plan = state.capital_plan
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    reserve_target = quantize_money(
        capital_plan.reserve_target + BALANCE.capital_plan_growth_firebreak_target_step
    )
    planning_horizon_turns = min(
        12,
        capital_plan.planning_horizon_turns + BALANCE.capital_plan_growth_firebreak_horizon_gain,
    )
    product_share = max(
        0,
        capital_plan.product_investment_share
        - BALANCE.capital_plan_growth_firebreak_product_share_shift
        - 1,
    )
    go_to_market_share = max(
        0,
        capital_plan.go_to_market_share - BALANCE.capital_plan_growth_firebreak_gtm_share_shift - 2,
    )
    reserve_share = (
        capital_plan.reserve_share + BALANCE.capital_plan_growth_firebreak_reserve_share_shift + 3
    )
    source_preference = capital_plan.source_preference
    control_note = readiness.strategic_outlook.replace("_", " ")

    if (
        pressure.board_reset_risk >= 90
        or pressure.dominant_pressure == "board_reset_risk"
        or state.finance.governance_risk >= 60
    ):
        source_preference = CapitalSourcePreference.BOOTSTRAP
        reserve_share += 2
        go_to_market_share = max(0, go_to_market_share - 1)
        control_note = "board reset"
    elif readiness.strategic_outlook == "ipo_ready":
        if source_preference in {
            CapitalSourcePreference.DEBT,
            CapitalSourcePreference.VENTURE,
        }:
            source_preference = CapitalSourcePreference.ANGEL
        reserve_share += 1
        product_share += 1
        control_note = "IPO readiness"
    elif readiness.strategic_outlook == "strategic_acquisition":
        if source_preference is CapitalSourcePreference.DEBT:
            source_preference = CapitalSourcePreference.ANGEL
        reserve_share += 1
        product_share += 1
        control_note = "buyer close"
    else:
        source_preference = CapitalSourcePreference.BOOTSTRAP
        reserve_share += 2
        go_to_market_share = max(0, go_to_market_share - 1)
        control_note = "independence"

    if queue_exposure.hotspot_lane_overflow > 2:
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if queue_exposure.enterprise_queue_risk_accounts > 1:
        reserve_share += 1
        product_share += 1
    if queue_exposure.white_glove_queue_risk_accounts > 0:
        reserve_share += 1
    if (
        portfolio.hotspot_dependency_score
        >= BALANCE.finance_planner_reactivate_dependency_threshold + 8
        or portfolio.paused_dependency_score
        >= BALANCE.finance_planner_reactivate_dependency_threshold + 4
    ):
        reserve_share += 2
        go_to_market_share = max(0, go_to_market_share - 1)
        product_share = max(0, product_share - 1)

    product_share, go_to_market_share, reserve_share = _normalize_capital_shares(
        product_share,
        go_to_market_share,
        reserve_share,
    )
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.CONSERVE,
        source_preference=source_preference,
        planning_horizon_turns=planning_horizon_turns,
        reserve_target=reserve_target,
        product_investment_share=product_share,
        go_to_market_share=go_to_market_share,
        reserve_share=reserve_share,
    )
    state.finance.board_pressure = min(100, state.finance.board_pressure)
    state.finance.board_confidence = min(
        100,
        state.finance.board_confidence
        + BALANCE.capital_plan_growth_firebreak_board_confidence_gain,
    )
    return CapitalPlanSummary(
        message=(
            f"Set a terminal recovery lattice for the {control_note} path. Reserve target "
            f"{format_money(reserve_target)} over {planning_horizon_turns} turns. Allocation now "
            f"P {product_share}% / GTM {go_to_market_share}% / Reserve {reserve_share}% with "
            f"{source_preference.value} capital."
        ),
        capital_plan=state.capital_plan,
    )


def apply_set_terminal_continuity_matrix(state: GameState) -> CapitalPlanSummary:
    """Apply the final capital-control move when the whole late-game stack is still fragile."""

    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    queue_exposure = calculate_support_queue_exposure(state)
    portfolio = calculate_partnership_portfolio(state)
    reserve_gap = state.capital_plan.reserve_target - state.company.cash_on_hand
    base_cost = quantize_money(
        BALANCE.capital_plan_endgame_capital_map_cost * 2
        + BALANCE.capital_plan_path_capital_posture_cost * 4
        + BALANCE.capital_plan_growth_firebreak_cost * 4
    )
    extra_cost = quantize_money(
        BALANCE.capital_plan_growth_firebreak_cost * 2
        + BALANCE.capital_plan_path_capital_posture_cost * 2
    )
    total_cost = quantize_money(base_cost + extra_cost)

    if (
        pressure.board_reset_risk < 94
        and pressure.public_market_scrutiny < 94
        and pressure.acquirer_diligence < 94
        and pressure.independence_discipline < 94
        and state.finance.governance_risk < 62
        and state.finance.covenant_risk < 28
        and reserve_gap <= Decimal("0.00")
        and queue_exposure.hotspot_lane_overflow <= 5
        and portfolio.hotspot_dependency_score
        < BALANCE.finance_planner_reactivate_dependency_threshold + 18
    ):
        raise ValueError(
            "There is not enough terminal multi-path strain to justify a continuity matrix."
        )
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to set a terminal continuity matrix this turn.")

    apply_set_terminal_recovery_lattice(state)
    capital_plan = state.capital_plan
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    reserve_target = quantize_money(
        capital_plan.reserve_target + BALANCE.capital_plan_growth_firebreak_target_step
    )
    planning_horizon_turns = min(12, capital_plan.planning_horizon_turns + 1)
    product_share = max(0, capital_plan.product_investment_share - 1)
    go_to_market_share = max(0, capital_plan.go_to_market_share - 2)
    reserve_share = capital_plan.reserve_share + 3
    source_preference = capital_plan.source_preference
    control_note = readiness.strategic_outlook.replace("_", " ")

    if (
        pressure.board_reset_risk >= 94
        or pressure.dominant_pressure == "board_reset_risk"
        or state.finance.governance_risk >= 62
    ):
        source_preference = CapitalSourcePreference.BOOTSTRAP
        reserve_share += 2
        go_to_market_share = max(0, go_to_market_share - 1)
        control_note = "board reset"
    elif readiness.strategic_outlook == "ipo_ready":
        if source_preference in {
            CapitalSourcePreference.DEBT,
            CapitalSourcePreference.VENTURE,
        }:
            source_preference = CapitalSourcePreference.ANGEL
        reserve_share += 1
        product_share += 1
        control_note = "IPO readiness"
    elif readiness.strategic_outlook == "strategic_acquisition":
        if source_preference is CapitalSourcePreference.DEBT:
            source_preference = CapitalSourcePreference.ANGEL
        reserve_share += 1
        product_share += 1
        control_note = "buyer close"
    else:
        source_preference = CapitalSourcePreference.BOOTSTRAP
        reserve_share += 2
        go_to_market_share = max(0, go_to_market_share - 1)
        control_note = "independence"

    if queue_exposure.hotspot_lane_overflow > 3:
        reserve_share += 1
        go_to_market_share = max(0, go_to_market_share - 1)
    if queue_exposure.enterprise_queue_risk_accounts > 1:
        reserve_share += 1
        product_share += 1
    if queue_exposure.white_glove_queue_risk_accounts > 0:
        reserve_share += 1
    if (
        portfolio.hotspot_dependency_score
        >= BALANCE.finance_planner_reactivate_dependency_threshold + 10
        or portfolio.paused_dependency_score
        >= BALANCE.finance_planner_reactivate_dependency_threshold + 6
    ):
        reserve_share += 2
        go_to_market_share = max(0, go_to_market_share - 1)
        product_share = max(0, product_share - 1)

    product_share, go_to_market_share, reserve_share = _normalize_capital_shares(
        product_share,
        go_to_market_share,
        reserve_share,
    )
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.CONSERVE,
        source_preference=source_preference,
        planning_horizon_turns=planning_horizon_turns,
        reserve_target=reserve_target,
        product_investment_share=product_share,
        go_to_market_share=go_to_market_share,
        reserve_share=reserve_share,
    )
    state.finance.investor_pressure = clamp_int(state.finance.investor_pressure - 1)
    state.finance.covenant_risk = clamp_int(state.finance.covenant_risk - 1)
    state.finance.board_confidence = min(
        100,
        state.finance.board_confidence
        + BALANCE.capital_plan_growth_firebreak_board_confidence_gain,
    )
    return CapitalPlanSummary(
        message=(
            f"Set a terminal continuity matrix for the {control_note} path. Reserve target "
            f"{format_money(reserve_target)} over {planning_horizon_turns} turns. Allocation now "
            f"P {product_share}% / GTM {go_to_market_share}% / Reserve {reserve_share}% with "
            f"{source_preference.value} capital."
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
