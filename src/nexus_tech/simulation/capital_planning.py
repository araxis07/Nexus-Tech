"""Capital-planning configuration and drift helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import (
    CapitalPlan,
    CapitalPlanMode,
    CapitalSourcePreference,
    Company,
    FinanceState,
    GameState,
)
from nexus_tech.domain.money import format_money, quantize_money
from nexus_tech.simulation.balance import BALANCE


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
) -> CapitalPlanSummary:
    """Apply a new capital-planning posture to the in-memory run state."""

    capital_plan = get_capital_plan_profile(mode, source_preference)
    state.capital_plan = capital_plan
    return CapitalPlanSummary(
        message=(
            f"Capital plan set to {mode.value} with a {source_preference.value} bias. "
            f"Reserve target {format_money(capital_plan.reserve_target)} over "
            f"{capital_plan.planning_horizon_turns} turns."
        ),
        capital_plan=capital_plan,
    )


def evaluate_capital_plan(
    company: Company,
    finance: FinanceState,
    capital_plan: CapitalPlan,
    *,
    latest_net_cash_flow: Decimal,
) -> CapitalPlanDrift:
    """Return finance modifiers implied by the active capital plan."""

    reserve_gap = quantize_money(company.cash_on_hand - capital_plan.reserve_target)
    investor_pressure_delta = 0
    covenant_risk_delta = 0
    board_confidence_delta = 0

    if reserve_gap < Decimal("0.00"):
        investor_pressure_delta += BALANCE.capital_plan_reserve_shortfall_pressure_by_mode[
            capital_plan.mode.value
        ]
        covenant_risk_delta += 1
    else:
        board_confidence_delta += BALANCE.capital_plan_reserve_surplus_confidence_bonus_by_mode[
            capital_plan.mode.value
        ]

    if latest_net_cash_flow < Decimal("0.00"):
        investor_pressure_delta += BALANCE.capital_plan_negative_cash_pressure_by_mode[
            capital_plan.mode.value
        ]
        if capital_plan.mode is CapitalPlanMode.EXPAND:
            board_confidence_delta -= BALANCE.capital_plan_expand_confidence_penalty
    elif capital_plan.mode is CapitalPlanMode.CONSERVE:
        covenant_risk_delta -= BALANCE.capital_plan_conserve_covenant_relief

    if capital_plan.source_preference is CapitalSourcePreference.BOOTSTRAP:
        if reserve_gap >= Decimal("0.00") and latest_net_cash_flow >= Decimal("0.00"):
            investor_pressure_delta -= BALANCE.capital_plan_bootstrap_pressure_relief
            board_confidence_delta += BALANCE.capital_plan_bootstrap_confidence_bonus
    elif capital_plan.source_preference is CapitalSourcePreference.DEBT:
        if finance.debt_principal >= BALANCE.finance_covenant_risk_debt_threshold:
            covenant_risk_delta += BALANCE.capital_plan_debt_covenant_penalty
    elif capital_plan.source_preference is CapitalSourcePreference.ANGEL:
        if reserve_gap < Decimal("0.00"):
            investor_pressure_delta -= BALANCE.capital_plan_angel_pressure_relief
    elif (
        capital_plan.source_preference is CapitalSourcePreference.VENTURE
        and company.cash_on_hand
        <= BALANCE.capital_plan_expand_investor_pressure_relief_cash_threshold
    ):
        investor_pressure_delta -= BALANCE.capital_plan_venture_pressure_relief

    summary = (
        f"{capital_plan.mode.value} / {capital_plan.source_preference.value} plan, "
        f"reserve gap {format_money(reserve_gap)}."
    )
    return CapitalPlanDrift(
        investor_pressure_delta=investor_pressure_delta,
        covenant_risk_delta=covenant_risk_delta,
        board_confidence_delta=board_confidence_delta,
        runway_target_modifier=BALANCE.capital_plan_runway_target_modifier_by_mode[
            capital_plan.mode.value
        ],
        reserve_gap=reserve_gap,
        summary=summary,
    )
