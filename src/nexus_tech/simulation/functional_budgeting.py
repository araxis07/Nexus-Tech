"""Cross-functional operating allocation profiles."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.domain.models import FunctionalBudget, FunctionalBudgetPreset, GameState
from nexus_tech.simulation.support import clamp_int


@dataclass(frozen=True)
class FunctionalBudgetProfile:
    """Derived execution modifiers from one functional-budget allocation."""

    engineering_bonus: int
    marketing_bonus: int
    customer_success_bonus: int
    g_and_a_bonus: int
    burnout_relief: int
    board_confidence_bonus: int
    summary: str


_BUDGET_PRESETS = {
    FunctionalBudgetPreset.BALANCED: FunctionalBudget(
        preset=FunctionalBudgetPreset.BALANCED,
        engineering_share=30,
        marketing_share=25,
        customer_success_share=25,
        g_and_a_share=20,
    ),
    FunctionalBudgetPreset.PRODUCT_PUSH: FunctionalBudget(
        preset=FunctionalBudgetPreset.PRODUCT_PUSH,
        engineering_share=40,
        marketing_share=20,
        customer_success_share=15,
        g_and_a_share=25,
    ),
    FunctionalBudgetPreset.GROWTH_PUSH: FunctionalBudget(
        preset=FunctionalBudgetPreset.GROWTH_PUSH,
        engineering_share=24,
        marketing_share=40,
        customer_success_share=16,
        g_and_a_share=20,
    ),
    FunctionalBudgetPreset.CUSTOMER_TRUST: FunctionalBudget(
        preset=FunctionalBudgetPreset.CUSTOMER_TRUST,
        engineering_share=25,
        marketing_share=18,
        customer_success_share=37,
        g_and_a_share=20,
    ),
    FunctionalBudgetPreset.CASH_GUARD: FunctionalBudget(
        preset=FunctionalBudgetPreset.CASH_GUARD,
        engineering_share=24,
        marketing_share=18,
        customer_success_share=24,
        g_and_a_share=34,
    ),
}

_BUDGET_SUMMARIES = {
    FunctionalBudgetPreset.BALANCED: ("Balanced execution across product, growth, and retention."),
    FunctionalBudgetPreset.PRODUCT_PUSH: (
        "Bias harder toward engineering throughput and platform work."
    ),
    FunctionalBudgetPreset.GROWTH_PUSH: (
        "Prioritize marketing and pipeline generation over product depth."
    ),
    FunctionalBudgetPreset.CUSTOMER_TRUST: (
        "Protect renewals, onboarding, and long-term account health."
    ),
    FunctionalBudgetPreset.CASH_GUARD: (
        "Favor operational discipline and org resilience over raw speed."
    ),
}


def build_functional_budget(preset: FunctionalBudgetPreset) -> FunctionalBudget:
    """Return a fresh functional-budget allocation from one named preset."""

    return _BUDGET_PRESETS[preset].model_copy(deep=True)


def get_functional_budget_profile(functional_budget: FunctionalBudget) -> FunctionalBudgetProfile:
    """Convert allocation shares into compact system modifiers."""

    engineering_bonus = clamp_int((functional_budget.engineering_share - 30) // 5, -2, 3)
    marketing_bonus = clamp_int((functional_budget.marketing_share - 25) // 5, -2, 3)
    customer_success_bonus = clamp_int(
        (functional_budget.customer_success_share - 25) // 5,
        -2,
        4,
    )
    g_and_a_bonus = clamp_int((functional_budget.g_and_a_share - 20) // 5, -2, 3)
    return FunctionalBudgetProfile(
        engineering_bonus=engineering_bonus,
        marketing_bonus=marketing_bonus,
        customer_success_bonus=customer_success_bonus,
        g_and_a_bonus=g_and_a_bonus,
        burnout_relief=max(0, g_and_a_bonus),
        board_confidence_bonus=max(0, g_and_a_bonus),
        summary=_BUDGET_SUMMARIES[functional_budget.preset],
    )


def apply_set_functional_budget(
    state: GameState,
    preset: FunctionalBudgetPreset,
) -> FunctionalBudgetProfile:
    """Set the active cross-functional budget preset on the run state."""

    state.functional_budget = build_functional_budget(preset)
    return get_functional_budget_profile(state.functional_budget)
