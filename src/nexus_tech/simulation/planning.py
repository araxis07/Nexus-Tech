"""Quarter planning, budget stance, and target evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.constants import ZERO_MONEY
from nexus_tech.domain.models import BudgetStance, GameState, QuarterPlan
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE


@dataclass(frozen=True)
class BudgetProfile:
    """Operating posture implied by one budget stance."""

    operating_cost_modifier: Decimal
    marketing_cost_multiplier: Decimal
    marketing_bonus: int
    burnout_modifier: int
    headcount_cap_bonus: int
    summary: str


@dataclass(frozen=True)
class QuarterPlanProgress:
    """Progress against the active quarter plan."""

    revenue_progress: float
    user_progress: float
    cash_progress: float
    headcount_within_cap: bool
    completed_target_count: int


_BUDGET_PROFILES = {
    BudgetStance.LEAN: BudgetProfile(
        operating_cost_modifier=BALANCE.budget_lean_operating_cost_modifier,
        marketing_cost_multiplier=BALANCE.budget_lean_marketing_cost_multiplier,
        marketing_bonus=BALANCE.budget_lean_marketing_bonus,
        burnout_modifier=BALANCE.budget_lean_burnout_modifier,
        headcount_cap_bonus=BALANCE.budget_lean_headcount_cap_bonus,
        summary="Protect cash, cap payroll growth, and spend carefully.",
    ),
    BudgetStance.BALANCED: BudgetProfile(
        operating_cost_modifier=BALANCE.budget_balanced_operating_cost_modifier,
        marketing_cost_multiplier=BALANCE.budget_balanced_marketing_cost_multiplier,
        marketing_bonus=BALANCE.budget_balanced_marketing_bonus,
        burnout_modifier=BALANCE.budget_balanced_burnout_modifier,
        headcount_cap_bonus=BALANCE.budget_balanced_headcount_cap_bonus,
        summary="Balance growth, stability, and runway pressure.",
    ),
    BudgetStance.AGGRESSIVE: BudgetProfile(
        operating_cost_modifier=BALANCE.budget_aggressive_operating_cost_modifier,
        marketing_cost_multiplier=BALANCE.budget_aggressive_marketing_cost_multiplier,
        marketing_bonus=BALANCE.budget_aggressive_marketing_bonus,
        burnout_modifier=BALANCE.budget_aggressive_burnout_modifier,
        headcount_cap_bonus=BALANCE.budget_aggressive_headcount_cap_bonus,
        summary="Spend harder to force growth, but accept more burn and fatigue.",
    ),
}


def get_budget_profile(budget_stance: BudgetStance) -> BudgetProfile:
    """Return the effective profile for a budget stance."""

    return _BUDGET_PROFILES[budget_stance]


def build_quarter_plan(
    state: GameState,
    *,
    budget_stance: BudgetStance | None = None,
) -> QuarterPlan:
    """Build or refresh a quarter plan from the current run state."""

    budget_stance = budget_stance or state.quarter_plan.budget_stance
    budget_profile = get_budget_profile(budget_stance)
    current_revenue = _get_reference_revenue(state)
    current_users = sum(product.user_count for product in state.products if product.is_active)
    roadmap_multiplier = BALANCE.quarter_plan_revenue_growth_by_roadmap[state.roadmap_focus.value]
    revenue_target = quantize_money(current_revenue * roadmap_multiplier)
    user_target = current_users + BALANCE.quarter_plan_user_growth_by_budget[budget_stance.value]
    cash_target = quantize_money(
        state.company.cash_on_hand + BALANCE.quarter_plan_cash_buffer_by_budget[budget_stance.value]
    )
    headcount_cap = len(state.employees) + budget_profile.headcount_cap_bonus
    return QuarterPlan(
        budget_stance=budget_stance,
        set_turn=state.company.current_turn,
        target_turn=state.company.current_turn + BALANCE.roadmap_duration_turns - 1,
        revenue_target=revenue_target,
        user_target=user_target,
        cash_reserve_target=cash_target,
        headcount_cap=headcount_cap,
    )


def evaluate_quarter_plan(state: GameState) -> QuarterPlanProgress:
    """Return compact progress metrics for the active quarter plan."""

    revenue = _get_reference_revenue(state)
    users = sum(product.user_count for product in state.products if product.is_active)
    headcount = len(state.employees)
    plan = state.quarter_plan
    revenue_progress = _safe_ratio(revenue, plan.revenue_target)
    user_progress = _safe_ratio(Decimal(users), Decimal(max(1, plan.user_target)))
    cash_progress = _safe_ratio(state.company.cash_on_hand, plan.cash_reserve_target)
    headcount_within_cap = headcount <= plan.headcount_cap or plan.headcount_cap == 0
    completed_target_count = sum(
        [
            revenue_progress >= 1.0,
            user_progress >= 1.0,
            cash_progress >= 1.0,
            headcount_within_cap,
        ]
    )
    return QuarterPlanProgress(
        revenue_progress=revenue_progress,
        user_progress=user_progress,
        cash_progress=cash_progress,
        headcount_within_cap=headcount_within_cap,
        completed_target_count=completed_target_count,
    )


def is_quarter_plan_due(state: GameState) -> bool:
    """Return whether the current quarter plan has expired."""

    return state.company.current_turn > state.quarter_plan.target_turn


def _get_reference_revenue(state: GameState) -> Decimal:
    if state.turn_history:
        return state.turn_history[-1].total_revenue
    current_revenue = sum(
        (
            Decimal(product.user_count) * product.revenue_per_user
            for product in state.products
            if product.is_active
        ),
        ZERO_MONEY,
    )
    return quantize_money(max(ZERO_MONEY, current_revenue))


def _safe_ratio(value: Decimal, target: Decimal) -> float:
    if target <= ZERO_MONEY:
        return 1.0
    return max(0.0, float(value / target))
