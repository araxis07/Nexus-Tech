"""Effect application for pending business events."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import EventHistoryEntry, GameState, PendingEvent
from nexus_tech.domain.money import quantize_money, quantize_rate
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.economy import is_game_over
from nexus_tech.simulation.event_registry import get_designer_or_marketer_support
from nexus_tech.simulation.product_progression import infer_lifecycle_stage


@dataclass(frozen=True)
class EventApplicationOutcome:
    """Result of applying one event option."""

    state: GameState
    history_entry: EventHistoryEntry


def apply_pending_event_choice(
    state: GameState,
    option_id: str,
) -> EventApplicationOutcome:
    """Apply one option for the currently pending event."""

    if state.pending_event is None:
        raise ValueError("There is no pending event to resolve.")

    option = next(
        (
            event_option
            for event_option in state.pending_event.options
            if event_option.id == option_id
        ),
        None,
    )
    if option is None:
        raise ValueError("Selected event option was not found.")

    next_state = state.model_copy(deep=True)
    pending_event = next_state.pending_event
    if pending_event is None:
        raise ValueError("There is no pending event to resolve.")

    handler = EVENT_EFFECT_HANDLERS.get(pending_event.event_id)
    if handler is None:
        raise ValueError(f"No handler registered for event {pending_event.event_id}.")

    result_text = handler(next_state, pending_event, option_id)
    next_state.company.game_over = is_game_over(next_state.company)
    next_state.pending_event = None

    history_entry = EventHistoryEntry(
        event_id=pending_event.event_id,
        category=pending_event.category,
        title=pending_event.title,
        triggered_turn=pending_event.triggered_turn,
        resolved_turn=pending_event.triggered_turn,
        selected_option_id=option.id,
        selected_option_label=option.label,
        result_text=result_text,
    )
    next_state.event_history.append(history_entry)
    if len(next_state.event_history) > BALANCE.event_history_limit:
        next_state.event_history = next_state.event_history[-BALANCE.event_history_limit :]

    return EventApplicationOutcome(
        state=next_state,
        history_entry=history_entry,
    )


def _apply_severe_bug_incident(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)
    affected_employees = _get_assigned_employees(state, product.id)

    if option_id == "hotfix":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_bug_hotfix_cost
        )
        product.bug_level = _clamp_int(
            product.bug_level - BALANCE.event_bug_hotfix_bug_reduction,
            0,
            100,
        )
        product.quality = _clamp_int(
            product.quality - BALANCE.event_bug_hotfix_quality_loss,
            0,
            100,
        )
        state.company.reputation = _clamp_int(
            state.company.reputation - BALANCE.event_bug_hotfix_reputation_loss,
            0,
            100,
        )
        for employee in affected_employees:
            employee.energy = _clamp_int(
                employee.energy - BALANCE.event_bug_hotfix_energy_loss,
                0,
                100,
            )
            employee.morale = _clamp_int(
                employee.morale - BALANCE.event_bug_hotfix_morale_loss,
                0,
                100,
            )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"Emergency patch funded for {product.name}. Cash -{BALANCE.event_bug_hotfix_cost}, "
            f"bugs -{BALANCE.event_bug_hotfix_bug_reduction}, reputation "
            f"-{BALANCE.event_bug_hotfix_reputation_loss}."
        )

    if option_id == "delay":
        user_loss = min(
            product.user_count,
            max(
                BALANCE.event_bug_delay_min_user_loss,
                product.user_count // BALANCE.event_bug_delay_user_loss_divisor,
            ),
        )
        product.bug_level = _clamp_int(
            product.bug_level + BALANCE.event_bug_delay_bug_increase,
            0,
            100,
        )
        product.user_count = max(0, product.user_count - user_loss)
        state.company.reputation = _clamp_int(
            state.company.reputation - BALANCE.event_bug_delay_reputation_loss,
            0,
            100,
        )
        for employee in affected_employees:
            employee.energy = _clamp_int(
                employee.energy - BALANCE.event_bug_delay_energy_loss,
                0,
                100,
            )
            employee.morale = _clamp_int(
                employee.morale - BALANCE.event_bug_delay_morale_loss,
                0,
                100,
            )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"{product.name} took visible damage. Users -{user_loss}, "
            f"bugs +{BALANCE.event_bug_delay_bug_increase}, reputation "
            f"-{BALANCE.event_bug_delay_reputation_loss}."
        )

    raise ValueError(f"Unsupported option {option_id} for severe bug incident.")


def _apply_favorable_market_trend(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)
    affected_employees = _get_assigned_employees(state, product.id)

    if option_id == "lean_in":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_market_trend_invest_cost
        )
        product.user_count += BALANCE.event_market_trend_big_user_gain
        product.acquisition_rate = _clamp_rate(
            product.acquisition_rate + BALANCE.event_market_trend_acquisition_gain
        )
        state.company.reputation = _clamp_int(
            state.company.reputation + BALANCE.event_market_trend_reputation_gain,
            0,
            100,
        )
        for employee in affected_employees:
            employee.energy = _clamp_int(
                employee.energy - BALANCE.event_market_trend_energy_loss,
                0,
                100,
            )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You leaned into the market trend around {product.name}. "
            f"Cash -{BALANCE.event_market_trend_invest_cost}, users "
            f"+{BALANCE.event_market_trend_big_user_gain}."
        )

    if option_id == "bank_it":
        product.user_count += BALANCE.event_market_trend_small_user_gain
        state.company.reputation = _clamp_int(
            state.company.reputation + BALANCE.event_market_trend_reputation_gain,
            0,
            100,
        )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You banked a lighter win for {product.name}. "
            f"Users +{BALANCE.event_market_trend_small_user_gain}, reputation "
            f"+{BALANCE.event_market_trend_reputation_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for favorable market trend.")


def _apply_investor_outreach(state: GameState, event: PendingEvent, option_id: str) -> str:
    del event

    if option_id == "take_capital":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand + BALANCE.event_investor_cash_gain
        )
        state.company.reputation = _clamp_int(
            state.company.reputation + BALANCE.event_investor_reputation_gain,
            0,
            100,
        )
        for employee in state.employees:
            employee.morale = _clamp_int(
                employee.morale - BALANCE.event_investor_team_morale_penalty,
                0,
                100,
            )
        return (
            f"The investor round closed quickly. Cash +{BALANCE.event_investor_cash_gain}, "
            f"reputation +{BALANCE.event_investor_reputation_gain}, team morale "
            f"-{BALANCE.event_investor_team_morale_penalty}."
        )

    if option_id == "stay_bootstrapped":
        state.company.reputation = _clamp_int(
            state.company.reputation + BALANCE.event_bootstrap_reputation_gain,
            0,
            100,
        )
        for employee in state.employees:
            employee.morale = _clamp_int(
                employee.morale + BALANCE.event_bootstrap_team_morale_gain,
                0,
                100,
            )
        return (
            f"You stayed bootstrapped. Reputation +{BALANCE.event_bootstrap_reputation_gain}, "
            f"team morale +{BALANCE.event_bootstrap_team_morale_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for investor outreach.")


def _apply_sudden_press_mention(state: GameState, event: PendingEvent, option_id: str) -> str:
    if option_id != "ride_the_wave":
        raise ValueError(f"Unsupported option {option_id} for sudden press mention.")

    product = _get_target_product(state, event)
    gained_users = max(
        BALANCE.event_press_min_user_gain,
        product.user_count // BALANCE.event_press_user_gain_divisor,
    )
    product.user_count += gained_users
    product.acquisition_rate = _clamp_rate(
        product.acquisition_rate + BALANCE.event_press_acquisition_gain
    )
    state.company.reputation = _clamp_int(
        state.company.reputation + BALANCE.event_press_reputation_gain,
        0,
        100,
    )
    for employee in get_designer_or_marketer_support(state.employees, product.id):
        employee.morale = _clamp_int(
            employee.morale + BALANCE.event_press_marketer_morale_gain,
            0,
            100,
        )
    product.lifecycle_stage = infer_lifecycle_stage(product)
    return (
        f"{product.name} caught a press bump. Users +{gained_users}, reputation "
        f"+{BALANCE.event_press_reputation_gain}."
    )


def _apply_team_burnout_spike(state: GameState, event: PendingEvent, option_id: str) -> str:
    employee = _get_target_employee(state, event)

    if option_id == "cool_off":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_burnout_relief_cost
        )
        employee.energy = _clamp_int(
            employee.energy + BALANCE.event_burnout_relief_energy_gain,
            0,
            100,
        )
        employee.morale = _clamp_int(
            employee.morale + BALANCE.event_burnout_relief_morale_gain,
            0,
            100,
        )
        for teammate in state.employees:
            if teammate.id == employee.id:
                continue
            teammate.morale = _clamp_int(
                teammate.morale + BALANCE.event_burnout_relief_team_morale_gain,
                0,
                100,
            )
        return (
            f"You funded recovery time for {employee.full_name}. Cash "
            f"-{BALANCE.event_burnout_relief_cost}, energy "
            f"+{BALANCE.event_burnout_relief_energy_gain}."
        )

    if option_id == "push_through":
        employee.energy = _clamp_int(
            employee.energy - BALANCE.event_burnout_push_energy_loss,
            0,
            100,
        )
        employee.morale = _clamp_int(
            employee.morale - BALANCE.event_burnout_push_morale_loss,
            0,
            100,
        )
        state.company.reputation = _clamp_int(
            state.company.reputation - BALANCE.event_burnout_push_reputation_loss,
            0,
            100,
        )
        if employee.assigned_product_id is not None:
            product = _get_product_by_id(state, employee.assigned_product_id)
            product.quality = _clamp_int(
                product.quality - BALANCE.event_burnout_push_quality_loss,
                0,
                100,
            )
            product.lifecycle_stage = infer_lifecycle_stage(product)
            return (
                f"You pushed {employee.full_name} through the crunch. "
                f"{product.name} quality -{BALANCE.event_burnout_push_quality_loss}, "
                f"reputation -{BALANCE.event_burnout_push_reputation_loss}."
            )
        return (
            f"You pushed {employee.full_name} through the crunch. "
            f"Reputation -{BALANCE.event_burnout_push_reputation_loss}."
        )

    raise ValueError(f"Unsupported option {option_id} for team burnout spike.")


def _apply_competitor_pressure(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)
    affected_employees = _get_assigned_employees(state, product.id)

    if option_id == "rush_countermove":
        product.feature_count += BALANCE.event_competitor_rush_feature_gain
        product.market_fit = _clamp_int(
            product.market_fit + BALANCE.event_competitor_rush_market_fit_gain,
            0,
            100,
        )
        product.bug_level = _clamp_int(
            product.bug_level + BALANCE.event_competitor_rush_bug_increase,
            0,
            100,
        )
        product.technical_debt = _clamp_int(
            product.technical_debt + BALANCE.event_competitor_rush_debt_increase,
            0,
            100,
        )
        for employee in affected_employees:
            employee.energy = _clamp_int(
                employee.energy - BALANCE.event_competitor_rush_energy_loss,
                0,
                100,
            )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You rushed a response for {product.name}. Features "
            f"+{BALANCE.event_competitor_rush_feature_gain}, bugs "
            f"+{BALANCE.event_competitor_rush_bug_increase}, debt "
            f"+{BALANCE.event_competitor_rush_debt_increase}."
        )

    if option_id == "differentiate":
        user_loss = min(product.user_count, BALANCE.event_competitor_focus_user_loss)
        product.quality = _clamp_int(
            product.quality + BALANCE.event_competitor_focus_quality_gain,
            0,
            100,
        )
        product.bug_level = _clamp_int(
            product.bug_level - BALANCE.event_competitor_focus_bug_reduction,
            0,
            100,
        )
        product.market_fit = _clamp_int(
            product.market_fit + BALANCE.event_competitor_focus_market_fit_gain,
            0,
            100,
        )
        product.user_count = max(0, product.user_count - user_loss)
        state.company.reputation = _clamp_int(
            state.company.reputation + BALANCE.event_competitor_focus_reputation_gain,
            0,
            100,
        )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You defended {product.name} with quality. Users -{user_loss}, quality "
            f"+{BALANCE.event_competitor_focus_quality_gain}, reputation "
            f"+{BALANCE.event_competitor_focus_reputation_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for competitor pressure.")


def _get_target_product(state: GameState, event: PendingEvent):
    if event.target_product_id is None:
        raise ValueError("This event expected a product target.")
    return _get_product_by_id(state, event.target_product_id)


def _get_product_by_id(state: GameState, product_id):
    for product in state.products:
        if product.id == product_id:
            return product
    raise ValueError("Event product target was not found.")


def _get_target_employee(state: GameState, event: PendingEvent):
    if event.target_employee_id is None:
        raise ValueError("This event expected an employee target.")
    for employee in state.employees:
        if employee.id == event.target_employee_id:
            return employee
    raise ValueError("Event employee target was not found.")


def _get_assigned_employees(state: GameState, product_id) -> list:
    return [
        employee for employee in state.employees if employee.assigned_product_id == product_id
    ]


def _clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _clamp_rate(value: Decimal) -> Decimal:
    return quantize_rate(max(Decimal("0.0000"), min(Decimal("1.0000"), value)))


EVENT_EFFECT_HANDLERS = {
    "severe_bug_incident": _apply_severe_bug_incident,
    "favorable_market_trend": _apply_favorable_market_trend,
    "investor_outreach": _apply_investor_outreach,
    "sudden_press_mention": _apply_sudden_press_mention,
    "team_burnout_spike": _apply_team_burnout_spike,
    "competitor_pressure": _apply_competitor_pressure,
}
