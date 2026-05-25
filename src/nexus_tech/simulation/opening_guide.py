"""Early-turn guidance for first-run and onboarding flows."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import GameState, Product, TurnAction
from nexus_tech.simulation.finance import estimate_runway


@dataclass(frozen=True)
class GuidedOpeningStep:
    """One step inside the guided opening plan."""

    rank: int
    command: str
    title: str
    rationale: str
    turn_window: str
    status: str


@dataclass(frozen=True)
class GuidedOpeningSummary:
    """Compact early-turn checklist derived from the current run state."""

    active: bool
    headline: str
    current_command: str
    summary: str
    steps: tuple[GuidedOpeningStep, ...]


def build_guided_opening(state: GameState) -> GuidedOpeningSummary:
    """Return a compact opening checklist for the first few turns."""

    flagship = _choose_flagship_product(state)
    quality_ready = flagship.quality >= 60 and flagship.bug_level <= 18
    assigned_to_flagship = any(
        employee.assigned_product_id == flagship.id for employee in state.employees
    )
    everyone_assigned = bool(state.employees) and all(
        employee.assigned_product_id is not None for employee in state.employees
    )
    resolved_turns = len(state.turn_history)
    growth_ready = quality_ready and (
        flagship.user_count >= 50 or state.company.reputation >= 54 or resolved_turns >= 2
    )
    review_ready = resolved_turns > 0
    expansion_ready = review_ready and quality_ready and state.company.current_turn >= 3
    review_command = (
        TurnAction.REVIEW_CUSTOMERS.value
        if state.customer_accounts
        else TurnAction.REVIEW_FINANCE.value
    )
    runway = estimate_runway(state.company.cash_on_hand, _latest_net_cash_flow(state))

    steps = (
        GuidedOpeningStep(
            rank=1,
            command=TurnAction.HIRE_EMPLOYEE.value,
            title="Build the first execution loop",
            rationale=(
                "One extra teammate unlocks real throughput. Keep the first hire tight if runway "
                f"is {runway} turns."
                if runway is not None and runway <= 4
                else "One extra teammate unlocks real throughput without over-complicating the org."
            ),
            turn_window="T1",
            status="done" if state.employees else "next",
        ),
        GuidedOpeningStep(
            rank=2,
            command=TurnAction.ASSIGN_EMPLOYEE.value,
            title="Focus the team on the flagship",
            rationale=(
                f"Put the first builder on {flagship.name}. Unassigned teammates add salary burn "
                "but no delivery."
            ),
            turn_window="T1",
            status=(
                "done"
                if everyone_assigned and assigned_to_flagship
                else "next"
                if state.employees
                else "later"
            ),
        ),
        GuidedOpeningStep(
            rank=3,
            command=(
                TurnAction.MARKET_PRODUCT.value
                if quality_ready
                else TurnAction.IMPROVE_QUALITY.value
            ),
            title="Stabilize product health before forcing growth",
            rationale=(
                f"{flagship.name} is healthy enough to buy demand."
                if quality_ready
                else (
                    f"{flagship.name} is still fragile at Q {flagship.quality} / "
                    f"B {flagship.bug_level}. Fix quality before bugs compound into churn."
                )
            ),
            turn_window="T1-T2",
            status=(
                "done"
                if quality_ready and resolved_turns > 0
                else "next"
                if everyone_assigned
                else "later"
            ),
        ),
        GuidedOpeningStep(
            rank=4,
            command=TurnAction.END_TURN.value,
            title="Resolve one clean operating turn",
            rationale=(
                "Spend the first actions, then simulate a turn so revenue, churn, costs, and "
                "events expose the real pressure."
            ),
            turn_window="T1-T2",
            status=(
                "done"
                if review_ready
                else "next"
                if everyone_assigned and quality_ready
                else "later"
            ),
        ),
        GuidedOpeningStep(
            rank=5,
            command=TurnAction.VIEW_REPORT.value,
            title="Read the first summary before scaling harder",
            rationale=(
                "Use the report to check runway, score direction, and whether support or board "
                "pressure is starting to form."
            ),
            turn_window="T2-T3",
            status=(
                "done"
                if state.company.current_turn >= 3 and review_ready
                else "next"
                if review_ready
                else "later"
            ),
        ),
        GuidedOpeningStep(
            rank=6,
            command=review_command,
            title="Open the first control panel",
            rationale=(
                "Review customers when accounts exist; otherwise review finance so the second "
                "hire or marketing push does not outrun runway."
            ),
            turn_window="T3-T6",
            status=(
                "done"
                if state.company.current_turn >= 4 and (state.customer_accounts or review_ready)
                else "next"
                if expansion_ready or growth_ready
                else "later"
            ),
        ),
    )

    current_step = next(
        (step for step in steps if step.status == "next"),
        next((step for step in steps if step.status != "done"), steps[-1]),
    )
    active = state.company.current_turn <= 6 or any(step.status != "done" for step in steps[:4])
    summary = (
        f"Guided opening points to `{current_step.command}` next. "
        f"Keep the first loop focused around {flagship.name}."
    )
    return GuidedOpeningSummary(
        active=active,
        headline="Turns 1-6: build one focused operating loop before you scale wider.",
        current_command=current_step.command,
        summary=summary,
        steps=steps,
    )


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
