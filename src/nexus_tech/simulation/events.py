"""Selection and orchestration for dynamic business events."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.domain.models import EventHistoryEntry, GameState, PendingEvent
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.campaign_decisions import (
    build_due_campaign_decision_event,
    campaign_adjusted_event_weight,
    is_campaign_decision_event,
)
from nexus_tech.simulation.decision_ledger import record_named_decision
from nexus_tech.simulation.event_effects import (
    EventApplicationOutcome,
    apply_pending_event_choice,
)
from nexus_tech.simulation.event_registry import EventDefinition, get_event_registry
from nexus_tech.simulation.randomness import RandomLike


@dataclass(frozen=True)
class EventTurnOutcome:
    """Result of the event engine for a resolved business turn."""

    state: GameState
    pending_event: PendingEvent | None = None
    history_entry: EventHistoryEntry | None = None


def get_eligible_event_definitions(state: GameState) -> list[EventDefinition]:
    """Return events that are currently eligible and not cooling down."""

    eligible_definitions: list[EventDefinition] = []
    for definition in get_event_registry():
        if not definition.is_eligible(state):
            continue
        if is_event_on_cooldown(
            state,
            event_id=definition.event_id,
            cooldown_turns=definition.cooldown_turns,
        ):
            continue
        eligible_definitions.append(definition)
    return eligible_definitions


def is_event_on_cooldown(state: GameState, event_id: str, cooldown_turns: int) -> bool:
    """Check whether an event is still cooling down from recent history."""

    recent_turns = [
        entry.resolved_turn for entry in state.event_history if entry.event_id == event_id
    ]
    if not recent_turns:
        return False
    return (state.company.current_turn - max(recent_turns)) <= cooldown_turns


def select_event_definition(
    state: GameState,
    rng: RandomLike,
    enforce_trigger_roll: bool = True,
) -> EventDefinition | None:
    """Choose one weighted eligible event definition, if any."""

    if state.pending_event is not None or state.company.game_over:
        return None
    if state.company.current_turn < BALANCE.event_trigger_min_turn:
        return None
    if enforce_trigger_roll:
        trigger_roll = rng.randint(1, 100)
        if trigger_roll > BALANCE.event_trigger_chance_percent:
            return None

    eligible_definitions = get_eligible_event_definitions(state)
    if not eligible_definitions:
        return None
    return select_weighted_definition(eligible_definitions, rng, state=state)


def select_weighted_definition(
    definitions: list[EventDefinition],
    rng: RandomLike,
    *,
    state: GameState | None = None,
) -> EventDefinition:
    """Pick one definition based on its configured weight."""

    weights = [
        (
            campaign_adjusted_event_weight(state, definition.category, definition.weight)
            if state is not None
            else definition.weight
        )
        for definition in definitions
    ]
    total_weight = sum(weights)
    roll = rng.randint(1, total_weight)
    running_total = 0
    for definition, weight in zip(definitions, weights, strict=True):
        running_total += weight
        if roll <= running_total:
            return definition
    return definitions[-1]


def resolve_turn_event(state: GameState, rng: RandomLike) -> EventTurnOutcome:
    """Generate a turn event and auto-resolve it when no choice is required."""

    campaign_event = build_due_campaign_decision_event(state)
    if campaign_event is not None:
        state.pending_event = campaign_event
        return EventTurnOutcome(state=state, pending_event=campaign_event)

    definition = select_event_definition(state, rng)
    if definition is None:
        return EventTurnOutcome(state=state)

    pending_event = definition.build_pending_event(state, rng, definition.cooldown_turns)
    if len(pending_event.options) == 1:
        application = apply_pending_event_choice(
            state.model_copy(update={"pending_event": pending_event}, deep=True),
            pending_event.options[0].id,
        )
        return EventTurnOutcome(
            state=application.state,
            history_entry=application.history_entry,
        )

    state.pending_event = pending_event
    return EventTurnOutcome(
        state=state,
        pending_event=pending_event,
    )


def resolve_pending_event(state: GameState, option_id: str) -> EventApplicationOutcome:
    """Resolve the current pending event with a selected option."""

    outcome = apply_pending_event_choice(state, option_id)
    entry = outcome.history_entry
    campaign_choice = is_campaign_decision_event(entry.event_id)
    record_named_decision(
        state,
        outcome.state,
        command=f"event:{entry.event_id}",
        label=entry.selected_option_label,
        family="Campaign Decision" if campaign_choice else "Event Choice",
        summary=entry.result_text,
        timing=(
            "Choice applied now; campaign pressure and route consequences continue on later turns."
            if campaign_choice
            else "Choice applied now; downstream effects continue through the normal turn loop."
        ),
    )
    return outcome
