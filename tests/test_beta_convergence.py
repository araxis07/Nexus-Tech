from __future__ import annotations

from collections import Counter
from dataclasses import replace
from decimal import Decimal

from nexus_tech.domain.models import (
    CampaignGoalId,
    DifficultyMode,
    EventCategory,
    EventHistoryEntry,
    RoadmapFocus,
    TurnLedgerEntry,
)
from nexus_tech.frontend_2d.viewmodels import (
    build_game_view_model,
    build_run_review_view_model,
)
from nexus_tech.persistence.save_coordinator import RunArchiveSummary, SaveLoadCoordinator
from nexus_tech.simulation.balance_lab import evaluate_balance_cell, run_balance_matrix
from nexus_tech.simulation.beta_contract import (
    BETA_CATALOG_CEILING,
    MANUAL_BETA_TARGETS,
    capture_catalog_snapshot,
    catalog_ceiling_violations,
)
from nexus_tech.simulation.beta_evidence import build_beta_archive_evidence
from nexus_tech.simulation.campaign import evaluate_campaign_goal
from nexus_tech.simulation.campaign_decisions import (
    build_due_campaign_decision_event,
    campaign_adjusted_event_weight,
    get_campaign_path_labels,
    get_campaign_path_outlook,
    list_campaign_decisions,
    list_campaign_event_biases,
)
from nexus_tech.simulation.campaign_journey import (
    CampaignActId,
    list_featured_campaign_journeys,
)
from nexus_tech.simulation.campaign_readiness import (
    evaluate_campaign_readiness_cell,
    format_campaign_readiness_markdown,
    list_campaign_routes,
    run_campaign_readiness_matrix,
)
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


def _archive_summary(
    scenario_id: str,
    *,
    difficulty_mode: str = "standard",
    commitment: str = "Commitment",
    consequence: str = "Consequence",
) -> RunArchiveSummary:
    return RunArchiveSummary(
        archive_key=f"{scenario_id}:12:none",
        slot_name=scenario_id,
        company_name="Evidence Co",
        scenario_title=scenario_id.replace("_", " ").title(),
        completed_turn=12,
        victory_achieved=True,
        game_over=False,
        exit_outcome="none",
        total_score=180,
        score_tier="strong",
        campaign_grade="A",
        estimated_valuation=Decimal("42000.00"),
        achievement_badges=(),
        strategic_outlook="profitable_independence",
        offer_value=Decimal("0.00"),
        final_cash=Decimal("12000.00"),
        final_reputation=64,
        archived_at="2026-07-14T00:00:00+00:00",
        scenario_id=scenario_id,
        difficulty_mode=difficulty_mode,
        campaign_commitment_choice=commitment,
        campaign_consequence_choice=consequence,
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


def test_featured_campaign_release_matrix_covers_every_difficulty_without_failures() -> None:
    scenario_ids = [journey.scenario_id for journey in list_featured_campaign_journeys()]

    matrix = run_balance_matrix(
        scenario_ids=scenario_ids,
        campaign_goal_id=CampaignGoalId.PROFIT_MACHINE,
        runs=1,
        turns=12,
        seed_base=28300,
    )

    assert len(matrix.cells) == len(scenario_ids) * len(DifficultyMode)
    assert {cell.scenario_id for cell in matrix.cells} == set(scenario_ids)
    assert {cell.difficulty_mode for cell in matrix.cells} == set(DifficultyMode)
    assert all(
        evaluate_balance_cell(cell, runs=matrix.runs, turns=matrix.turns).status != "fail"
        for cell in matrix.cells
    )


def test_featured_campaign_route_catalog_exposes_all_four_authored_paths() -> None:
    journeys = list_featured_campaign_journeys()

    for journey in journeys:
        routes = list_campaign_routes(journey.scenario_id)

        assert len(routes) == 4
        assert len({route.route_id for route in routes}) == 4
        assert all(len(route.choices) == 2 for route in routes)
        assert all(len(route.option_labels) == 2 for route in routes)


def test_campaign_readiness_exercises_every_founder_route_across_difficulties() -> None:
    matrix = run_campaign_readiness_matrix(
        scenario_ids=["founder_journey"],
        runs_per_route=1,
        turns=12,
        seed_base=28500,
    )

    assert len(matrix.cells) == len(DifficultyMode)
    assert matrix.route_count == 12
    assert matrix.goal_mode == "scenario_native"
    assert matrix.automated_gate_passed is True
    assert matrix.manual_signoff_required is True
    assert all(cell.ready_routes == 4 for cell in matrix.cells)
    assert all(cell.shutdowns == 0 for cell in matrix.cells)
    assert all(cell.campaign_goal_id is CampaignGoalId.PROFIT_MACHINE for cell in matrix.cells)
    assert all(evaluate_campaign_readiness_cell(cell).status == "pass" for cell in matrix.cells)
    comparison_cell = replace(
        matrix.cells[0],
        routes=tuple(
            replace(
                route,
                runs=3,
                full_path_runs=3,
                act_three_survivors=3,
                average_score=100.0 + index * 60,
            )
            for index, route in enumerate(matrix.cells[0].routes)
        ),
    )
    assert evaluate_campaign_readiness_cell(comparison_cell).status == "watch"
    report = format_campaign_readiness_markdown(matrix)
    assert "Authored routes exercised: `12`" in report
    assert "Goal mode: `scenario_native`" in report
    assert "Human playtest signoff: `required`" in report


def test_campaign_readiness_uses_native_goals_and_keeps_portfolio_routes_viable() -> None:
    matrix = run_campaign_readiness_matrix(
        scenario_ids=["portfolio_machine"],
        runs_per_route=3,
        turns=20,
        seed_base=28800,
    )

    assert matrix.goal_mode == "scenario_native"
    assert len(matrix.cells) == len(DifficultyMode)
    assert all(cell.campaign_goal_id is CampaignGoalId.PORTFOLIO_EMPIRE for cell in matrix.cells)
    assert all(cell.ready_routes == 4 for cell in matrix.cells)
    assert all(cell.shutdowns == 0 for cell in matrix.cells)
    assert sum(route.goal_completions for cell in matrix.cells for route in cell.routes) > 0
    assert all(evaluate_campaign_readiness_cell(cell).status == "pass" for cell in matrix.cells)


def test_featured_campaign_goal_waits_for_both_authored_decisions() -> None:
    state = create_new_game(scenario_id="founder_journey")
    state.company.current_turn = 9
    state.company.cash_on_hand = Decimal("50000.00")
    state.finance.debt_principal = Decimal("0.00")
    state.turn_history = [
        TurnLedgerEntry(
            turn=turn,
            total_revenue=Decimal("3000.00"),
            total_operating_cost=Decimal("1000.00"),
            net_cash_flow=Decimal("2000.00"),
            cash_on_hand=Decimal("50000.00"),
            reputation=70,
            total_users=200,
            headcount=4,
            roadmap_focus=RoadmapFocus.BALANCED_EXECUTION,
        )
        for turn in (6, 7, 8)
    ]

    before_path = evaluate_campaign_goal(state)

    assert before_path.completed is False
    assert before_path.progress_lines[-1] == "Campaign decisions: 0/2"

    for event_id, option_id, option_label, turn in (
        ("campaign_founder_commitment", "sharpen_focus", "Sharpen the Flagship", 4),
        ("campaign_founder_consequence", "defend_control", "Defend Control", 9),
    ):
        state.event_history.append(
            EventHistoryEntry(
                event_id=event_id,
                category=EventCategory.MARKET_OPPORTUNITY,
                title=option_label,
                triggered_turn=turn,
                resolved_turn=turn,
                selected_option_id=option_id,
                selected_option_label=option_label,
                result_text="Recorded campaign choice.",
            )
        )

    after_path = evaluate_campaign_goal(state)

    assert after_path.completed is True
    assert after_path.progress_lines[-1] == "Campaign decisions: 2/2"


def test_beta_archive_evidence_covers_every_featured_path_without_faking_signoff() -> None:
    scenario_ids = sorted({decision.scenario_id for decision in list_campaign_decisions()})
    archives = [
        _archive_summary(
            scenario_id,
            difficulty_mode=("builder", "standard", "founder")[index % 3],
        )
        for index, scenario_id in enumerate(scenario_ids)
    ]

    evidence = build_beta_archive_evidence(archives)

    assert evidence.ready_for_manual_review is True
    assert evidence.status == "ready-for-manual-review"
    assert evidence.covered_campaigns == 6
    assert evidence.covered_difficulties == ("builder", "standard", "founder")
    assert evidence.manual_signoff_required is True
    assert "real tester observations" in evidence.next_action


def test_beta_archive_evidence_names_the_next_missing_campaign() -> None:
    evidence = build_beta_archive_evidence([_archive_summary("founder_journey")])

    assert evidence.ready_for_manual_review is False
    assert evidence.status == "archive-evidence-needed"
    assert evidence.missing_campaigns
    assert evidence.next_action == f"Complete and archive {evidence.missing_campaigns[0]}."


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


def test_every_campaign_option_declares_a_bounded_long_run_event_bias() -> None:
    option_ids = {
        option.option_id for decision in list_campaign_decisions() for option in decision.options
    }
    biases = list_campaign_event_biases()

    assert len(biases) == 24
    assert {bias.option_id for bias in biases} == option_ids
    assert all(bias.summary.endswith(".") for bias in biases)
    assert all(bias.adjustments for bias in biases)
    assert all(
        -35 <= adjustment <= 35 for bias in biases for _category, adjustment in bias.adjustments
    )


def test_campaign_decision_takes_priority_and_records_a_persistent_path() -> None:
    state = create_new_game(scenario_id="founder_journey")
    state.company.current_turn = 4

    turn_outcome = resolve_turn_event(state, RandomSource(seed=1))

    assert turn_outcome.pending_event is not None
    assert turn_outcome.pending_event.event_id == "campaign_founder_commitment"
    assert all("Long-run:" in option.description for option in turn_outcome.pending_event.options)
    resolved = resolve_pending_event(turn_outcome.state, "sharpen_focus")
    assert resolved.message.startswith("The flagship became")
    assert resolved.state.products[0].quality > state.products[0].quality
    assert get_campaign_path_labels(resolved.state) == ("Act 2: Sharpen the Flagship",)
    assert get_campaign_path_outlook(resolved.state) == (
        "Fewer product incidents; slightly more market openings."
    )
    assert (
        campaign_adjusted_event_weight(
            resolved.state,
            EventCategory.PRODUCT_INCIDENT,
            100,
        )
        == 75
    )
    assert (
        campaign_adjusted_event_weight(
            resolved.state,
            EventCategory.MARKET_OPPORTUNITY,
            100,
        )
        == 110
    )
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


def test_completed_campaign_archive_preserves_beta_evidence_fields(tmp_path) -> None:
    coordinator = SaveLoadCoordinator(tmp_path / "campaign-archive.db")
    state = create_new_game(scenario_id="founder_journey")
    state.company.current_turn = 12
    state.difficulty_mode = DifficultyMode.FOUNDER
    state.victory_achieved = True
    state.victory_reason = "The company proved a durable path."
    state.event_history.extend(
        (
            EventHistoryEntry(
                event_id="campaign_founder_commitment",
                category=EventCategory.MARKET_OPPORTUNITY,
                title="Founder Commitment",
                triggered_turn=4,
                resolved_turn=4,
                selected_option_id="sharpen_focus",
                selected_option_label="Sharpen the Flagship",
                result_text="The flagship became the operating center.",
            ),
            EventHistoryEntry(
                event_id="campaign_founder_consequence",
                category=EventCategory.FUNDING_OPPORTUNITY,
                title="Founder Consequence",
                triggered_turn=9,
                resolved_turn=9,
                selected_option_id="defend_control",
                selected_option_label="Defend Control",
                result_text="Control stayed with the company.",
            ),
        )
    )

    coordinator.save_game("evidence", state, RandomSource(seed=24))
    archives = coordinator.list_run_archives()

    assert len(archives) == 1
    archive = archives[0]
    assert archive.scenario_id == "founder_journey"
    assert archive.difficulty_mode == "founder"
    assert archive.campaign_path == ("Sharpen the Flagship", "Defend Control")
    assert archive.terminal_reason == "The company proved a durable path."
    assert coordinator.check_save_health().schema_version == 25
