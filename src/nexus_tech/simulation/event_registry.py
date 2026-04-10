"""Registry and selection metadata for dynamic business events."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.domain.models import (
    Employee,
    EventCategory,
    EventOption,
    GameState,
    PendingEvent,
    Product,
)
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.randomness import RandomLike
from nexus_tech.simulation.team import calculate_effective_productivity


@dataclass(frozen=True)
class EventDefinition:
    """Static event metadata used by the event engine."""

    event_id: str
    category: EventCategory
    weight: int
    cooldown_turns: int
    is_eligible: callable
    build_pending_event: callable


def get_event_registry() -> tuple[EventDefinition, ...]:
    """Return the full registry of supported events."""

    return (
        EventDefinition(
            event_id="severe_bug_incident",
            category=EventCategory.PRODUCT_INCIDENT,
            weight=BALANCE.event_bug_incident_weight,
            cooldown_turns=BALANCE.event_bug_incident_cooldown,
            is_eligible=_is_bug_incident_eligible,
            build_pending_event=_build_bug_incident_event,
        ),
        EventDefinition(
            event_id="favorable_market_trend",
            category=EventCategory.MARKET_OPPORTUNITY,
            weight=BALANCE.event_market_trend_weight,
            cooldown_turns=BALANCE.event_market_trend_cooldown,
            is_eligible=_is_market_trend_eligible,
            build_pending_event=_build_market_trend_event,
        ),
        EventDefinition(
            event_id="investor_outreach",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_investor_outreach_weight,
            cooldown_turns=BALANCE.event_investor_outreach_cooldown,
            is_eligible=_is_investor_outreach_eligible,
            build_pending_event=_build_investor_outreach_event,
        ),
        EventDefinition(
            event_id="sudden_press_mention",
            category=EventCategory.REPUTATION_INCIDENT,
            weight=BALANCE.event_press_mention_weight,
            cooldown_turns=BALANCE.event_press_mention_cooldown,
            is_eligible=_is_press_mention_eligible,
            build_pending_event=_build_press_mention_event,
        ),
        EventDefinition(
            event_id="team_burnout_spike",
            category=EventCategory.EMPLOYEE_ISSUE,
            weight=BALANCE.event_burnout_spike_weight,
            cooldown_turns=BALANCE.event_burnout_spike_cooldown,
            is_eligible=_is_burnout_spike_eligible,
            build_pending_event=_build_burnout_spike_event,
        ),
        EventDefinition(
            event_id="competitor_pressure",
            category=EventCategory.MARKET_OPPORTUNITY,
            weight=BALANCE.event_competitor_pressure_weight,
            cooldown_turns=BALANCE.event_competitor_pressure_cooldown,
            is_eligible=_is_competitor_pressure_eligible,
            build_pending_event=_build_competitor_pressure_event,
        ),
    )


def _is_bug_incident_eligible(state: GameState) -> bool:
    return any(
        product.is_active
        and (
            product.bug_level >= BALANCE.event_bug_incident_bug_threshold
            or product.technical_debt >= BALANCE.event_bug_incident_debt_threshold
        )
        for product in state.products
    )


def _build_bug_incident_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [
            product
            for product in state.products
            if product.is_active
            and (
                product.bug_level >= BALANCE.event_bug_incident_bug_threshold
                or product.technical_debt >= BALANCE.event_bug_incident_debt_threshold
            )
        ],
        rng,
        score=lambda product: product.bug_level + product.technical_debt,
    )
    return PendingEvent(
        event_id="severe_bug_incident",
        category=EventCategory.PRODUCT_INCIDENT,
        title="Severe Bug Incident",
        description=(
            f"{target.name} is taking heat from a visible defect spike. "
            "You can pay for a fast containment push or absorb the public damage."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        target_product_id=target.id,
        options=[
            EventOption(
                id="hotfix",
                label="Fund an emergency hotfix",
                description="Pay cash, burn team energy, and contain the damage.",
            ),
            EventOption(
                id="delay",
                label="Delay and manage the fallout",
                description="Save cash now, but let users and reputation take the hit.",
            ),
        ],
    )


def _is_market_trend_eligible(state: GameState) -> bool:
    return any(
        product.is_active and product.market_fit >= BALANCE.event_market_trend_fit_threshold
        for product in state.products
    )


def _build_market_trend_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [
            product
            for product in state.products
            if product.is_active
            and product.market_fit >= BALANCE.event_market_trend_fit_threshold
        ],
        rng,
        score=lambda product: product.market_fit + (product.user_count // 8),
    )
    return PendingEvent(
        event_id="favorable_market_trend",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Favorable Market Trend",
        description=(
            f"Demand is rising around {target.name}. "
            "You can lean into the moment or take a smaller win without straining the team."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        target_product_id=target.id,
        options=[
            EventOption(
                id="lean_in",
                label="Lean into the trend",
                description="Spend cash for a stronger user spike and better acquisition.",
            ),
            EventOption(
                id="bank_it",
                label="Take the lighter win",
                description="Capture some upside without extra cost or pressure.",
            ),
        ],
    )


def _is_investor_outreach_eligible(state: GameState) -> bool:
    return state.company.current_turn >= 3 and (
        state.company.reputation >= BALANCE.event_investor_reputation_threshold
        or state.company.cash_on_hand <= BALANCE.event_investor_cash_threshold
    )


def _build_investor_outreach_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    return PendingEvent(
        event_id="investor_outreach",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Investor Outreach",
        description=(
            "A small investor wants to talk after seeing your recent traction. "
            "Fresh cash is available, but it will also add pressure to the team."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        options=[
            EventOption(
                id="take_capital",
                label="Take the meeting and close fast",
                description="Increase cash now, but the team feels the added pressure.",
            ),
            EventOption(
                id="stay_bootstrapped",
                label="Stay bootstrapped",
                description="Skip the cash and keep the team focused and calmer.",
            ),
        ],
    )


def _is_press_mention_eligible(state: GameState) -> bool:
    return any(
        product.is_active
        and (
            product.market_fit >= BALANCE.event_press_market_fit_threshold
            or product.user_count >= BALANCE.event_competitor_pressure_user_threshold
        )
        for product in state.products
    )


def _build_press_mention_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [
            product
            for product in state.products
            if product.is_active
            and (
                product.market_fit >= BALANCE.event_press_market_fit_threshold
                or product.user_count >= BALANCE.event_competitor_pressure_user_threshold
            )
        ],
        rng,
        score=lambda product: product.market_fit + (product.user_count // 10),
    )
    return PendingEvent(
        event_id="sudden_press_mention",
        category=EventCategory.REPUTATION_INCIDENT,
        title="Sudden Press Mention",
        description=(
            f"A niche outlet picked up {target.name}. "
            "The attention should convert into curiosity right away."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        target_product_id=target.id,
        options=[
            EventOption(
                id="ride_the_wave",
                label="Ride the wave",
                description="Take the lift in reputation and incoming traffic.",
            )
        ],
    )


def _is_burnout_spike_eligible(state: GameState) -> bool:
    return any(
        employee.energy <= BALANCE.event_burnout_spike_energy_threshold
        or employee.morale <= BALANCE.event_burnout_spike_morale_threshold
        for employee in state.employees
    )


def _build_burnout_spike_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_employee(
        [
            employee
            for employee in state.employees
            if employee.energy <= BALANCE.event_burnout_spike_energy_threshold
            or employee.morale <= BALANCE.event_burnout_spike_morale_threshold
        ],
        rng,
        score=lambda employee: -(employee.energy + employee.morale),
    )
    return PendingEvent(
        event_id="team_burnout_spike",
        category=EventCategory.EMPLOYEE_ISSUE,
        title="Team Burnout Spike",
        description=(
            f"{target.full_name} is close to burning out, and the tension is visible. "
            "You can intervene now or squeeze a little more output and accept the risk."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        target_employee_id=target.id,
        target_product_id=target.assigned_product_id,
        options=[
            EventOption(
                id="cool_off",
                label="Fund recovery time",
                description="Spend cash to restore energy and morale.",
            ),
            EventOption(
                id="push_through",
                label="Push through the crunch",
                description="Save cash, but risk product quality and team condition.",
            ),
        ],
    )


def _is_competitor_pressure_eligible(state: GameState) -> bool:
    return any(
        product.is_active and product.user_count >= BALANCE.event_competitor_pressure_user_threshold
        for product in state.products
    )


def _build_competitor_pressure_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [
            product
            for product in state.products
            if product.is_active
            and product.user_count >= BALANCE.event_competitor_pressure_user_threshold
        ],
        rng,
        score=lambda product: product.user_count + product.market_fit,
    )
    return PendingEvent(
        event_id="competitor_pressure",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Competitor Pressure",
        description=(
            f"A rival is making noise in {target.name}'s lane. "
            "You can rush a response or sharpen the product and defend the brand."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        target_product_id=target.id,
        options=[
            EventOption(
                id="rush_countermove",
                label="Rush a counter-move",
                description="Ship faster, but accept more bugs, debt, and team strain.",
            ),
            EventOption(
                id="differentiate",
                label="Differentiate on quality",
                description="Defend the brand with product quality, even if growth pauses.",
            ),
        ],
    )


def _pick_best_product(
    products: list[Product],
    rng: RandomLike,
    score: callable,
) -> Product:
    best_score = max(score(product) for product in products)
    candidates = [product for product in products if score(product) == best_score]
    return candidates[rng.randint(0, len(candidates) - 1)]


def _pick_best_employee(
    employees: list[Employee],
    rng: RandomLike,
    score: callable,
) -> Employee:
    best_score = max(score(employee) for employee in employees)
    candidates = [employee for employee in employees if score(employee) == best_score]
    return candidates[rng.randint(0, len(candidates) - 1)]


def get_designer_or_marketer_support(
    employees: list[Employee],
    product_id,
) -> list[Employee]:
    """Return comms-facing employees assigned to a product."""

    return [
        employee
        for employee in employees
        if employee.assigned_product_id == product_id
        and employee.role.value in {"designer", "marketer"}
        and calculate_effective_productivity(employee) > 0
    ]
