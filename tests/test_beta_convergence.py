from __future__ import annotations

from collections import Counter

from nexus_tech.domain.models import EventCategory, EventHistoryEntry
from nexus_tech.frontend_2d.viewmodels import (
    build_game_view_model,
    build_run_review_view_model,
)
from nexus_tech.persistence.save_coordinator import SaveLoadCoordinator
from nexus_tech.simulation.beta_contract import (
    BETA_CATALOG_CEILING,
    MANUAL_BETA_TARGETS,
    capture_catalog_snapshot,
    catalog_ceiling_violations,
)
from nexus_tech.simulation.campaign_decisions import (
    build_due_campaign_decision_event,
    get_campaign_path_labels,
    list_campaign_decisions,
)
from nexus_tech.simulation.campaign_journey import CampaignActId
from nexus_tech.simulation.engine import create_new_game
from nexus_tech.simulation.event_effects import _trim_event_history
from nexus_tech.simulation.events import resolve_pending_event, resolve_turn_event
from nexus_tech.simulation.randomness import RandomSource


def _history_entry(event_id: str, turn: int) -> EventHistoryEntry:
    return EventHistoryEntry(
        event_id=event_id,
        category=EventCategory.MARKET_OPPORTUNITY,
        title=f"History {turn}",
        triggered_turn=turn,
        resolved_turn=turn,
        selected_option_id="recorded",
        selected_option_label="Recorded",
        result_text="A prior choice was recorded.",
    )


def test_beta_catalog_is_frozen_at_the_convergence_baseline() -> None:
    snapshot = capture_catalog_snapshot()

    assert snapshot == BETA_CATALOG_CEILING
    assert catalog_ceiling_violations(snapshot) == ()


def test_beta_playtest_targets_remain_explicitly_manual() -> None:
    assert len(MANUAL_BETA_TARGETS) == 5
    assert all(target.manual_evidence_required for target in MANUAL_BETA_TARGETS)
    assert all(target.minimum_sessions >= 6 for target in MANUAL_BETA_TARGETS)
    assert any(target.key == "layout_readability" for target in MANUAL_BETA_TARGETS)


def test_featured_campaigns_have_two_unique_mechanical_decisions() -> None:
    decisions = list_campaign_decisions()
    by_scenario = Counter(decision.scenario_id for decision in decisions)

    assert len(decisions) == 12
    assert set(by_scenario.values()) == {2}
    assert len({decision.event_id for decision in decisions}) == len(decisions)
    assert all(len(decision.options) == 2 for decision in decisions)
    assert {(decision.act_id, decision.trigger_after_turn) for decision in decisions} == {
        (CampaignActId.COMMITMENT, 4),
        (CampaignActId.CONSEQUENCE, 9),
    }
    assert all(
        option.effect != option.effect.__class__(result_text=option.effect.result_text)
        for decision in decisions
        for option in decision.options
    )
    assert any(
        option.effect.employee_morale_delta or option.effect.employee_energy_delta
        for decision in decisions
        for option in decision.options
    )


def test_campaign_decision_takes_priority_and_records_a_persistent_path() -> None:
    state = create_new_game(scenario_id="founder_journey")
    state.company.current_turn = 4

    turn_outcome = resolve_turn_event(state, RandomSource(seed=1))

    assert turn_outcome.pending_event is not None
    assert turn_outcome.pending_event.event_id == "campaign_founder_commitment"
    resolved = resolve_pending_event(turn_outcome.state, "sharpen_focus")
    assert resolved.message.startswith("The flagship became")
    assert resolved.state.products[0].quality > state.products[0].quality
    assert get_campaign_path_labels(resolved.state) == ("Act 2: Sharpen the Flagship",)
    assert build_due_campaign_decision_event(resolved.state) is None

    resolved.state.company.current_turn = 9
    consequence = build_due_campaign_decision_event(resolved.state)
    assert consequence is not None
    assert consequence.event_id == "campaign_founder_consequence"
    resolved.state.pending_event = consequence
    final = resolve_pending_event(resolved.state, "defend_control")
    assert get_campaign_path_labels(final.state) == (
        "Act 2: Sharpen the Flagship",
        "Act 3: Defend Control",
    )


def test_every_campaign_option_applies_and_returns_frontend_message() -> None:
    decisions = list_campaign_decisions()

    for decision in decisions:
        for selected_option in decision.options:
            state = create_new_game(scenario_id=decision.scenario_id)
            state.company.current_turn = decision.trigger_after_turn
            for prior in decisions:
                if (
                    prior.scenario_id == decision.scenario_id
                    and prior.trigger_after_turn < decision.trigger_after_turn
                ):
                    state.event_history.append(
                        EventHistoryEntry(
                            event_id=prior.event_id,
                            category=prior.category,
                            title=prior.title,
                            triggered_turn=prior.trigger_after_turn,
                            resolved_turn=prior.trigger_after_turn,
                            selected_option_id=prior.options[0].option_id,
                            selected_option_label=prior.options[0].label,
                            result_text=prior.options[0].effect.result_text,
                        )
                    )
            pending = build_due_campaign_decision_event(state)
            assert pending is not None and pending.event_id == decision.event_id
            state.pending_event = pending
            starting_morale = [employee.morale for employee in state.employees]
            starting_energy = [employee.energy for employee in state.employees]

            outcome = resolve_pending_event(state, selected_option.option_id)

            assert outcome.message == selected_option.effect.result_text
            assert outcome.state.pending_event is None
            assert outcome.history_entry.selected_option_label == selected_option.label
            if selected_option.effect.employee_morale_delta:
                assert [employee.morale for employee in outcome.state.employees] != starting_morale
            if selected_option.effect.employee_energy_delta:
                assert [employee.energy for employee in outcome.state.employees] != starting_energy


def test_history_pruning_never_discards_campaign_commitments() -> None:
    campaign = _history_entry("campaign_founder_commitment", 4)
    entries = [campaign] + [_history_entry(f"systemic_{turn}", turn) for turn in range(5, 80)]

    trimmed = _trim_event_history(entries)

    assert len(trimmed) == 64
    assert campaign in trimmed
    assert trimmed[-1].event_id == "systemic_79"


def test_campaign_pending_event_and_path_round_trip_through_sqlite(tmp_path) -> None:
    coordinator = SaveLoadCoordinator(tmp_path / "campaign-round-trip.db")
    rng = RandomSource(seed=282)
    state = create_new_game(scenario_id="technical_rebuild")
    state.company.current_turn = 4
    state.pending_event = build_due_campaign_decision_event(state)
    assert state.pending_event is not None

    coordinator.save_game("campaign", state, rng)
    loaded_pending = coordinator.load_game("campaign")

    assert loaded_pending.state.pending_event is not None
    assert loaded_pending.state.pending_event.event_id == "campaign_rebuild_commitment"
    assert [option.id for option in loaded_pending.state.pending_event.options] == [
        "freeze_for_rebuild",
        "phase_the_rebuild",
    ]

    resolved = resolve_pending_event(loaded_pending.state, "freeze_for_rebuild")
    coordinator.save_game("campaign", resolved.state, loaded_pending.rng)
    loaded_path = coordinator.load_game("campaign").state
    live_view = build_game_view_model(loaded_path)
    review_view = build_run_review_view_model(loaded_path)

    assert loaded_path.pending_event is None
    assert get_campaign_path_labels(loaded_path) == ("Act 2: Freeze for Rebuild",)
    assert live_view.campaign_lens.startswith("Act 2: Freeze for Rebuild")
    assert "Act 2: Freeze for Rebuild" in review_view.badges
