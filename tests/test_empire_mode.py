from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from nexus_tech.domain.models import CampaignGoalId, MarketSegment
from nexus_tech.frontend_2d.catalog import list_scenario_choices
from nexus_tech.frontend_2d.viewmodels import build_deep_dive_panel_view_models
from nexus_tech.persistence.save_coordinator import SaveLoadCoordinator
from nexus_tech.simulation.beta_contract import BETA_CATALOG_CEILING, capture_catalog_snapshot
from nexus_tech.simulation.empire import (
    EMPIRE_MIN_VICTORY_TURN,
    EMPIRE_SCENARIO_ID,
    EmpireCrisisId,
    EmpireEraId,
    ScaleThesisId,
    TerritoryStatus,
    apply_empire_turn_effects,
    build_empire_snapshot,
    get_empire_era,
    get_scale_thesis,
)
from nexus_tech.simulation.engine import create_new_game, resolve_turn
from nexus_tech.simulation.randomness import RandomSource
from nexus_tech.simulation.reporting import check_victory
from nexus_tech.simulation.scenarios import create_product_from_template


@pytest.mark.parametrize(
    ("turn", "expected_era"),
    [
        (1, EmpireEraId.FOUNDATION),
        (5, EmpireEraId.FOUNDATION),
        (6, EmpireEraId.GROWTH),
        (10, EmpireEraId.GROWTH),
        (11, EmpireEraId.SCALE),
        (16, EmpireEraId.SCALE),
        (17, EmpireEraId.EXPANSION),
        (24, EmpireEraId.EXPANSION),
        (25, EmpireEraId.LEGACY),
    ],
)
def test_empire_era_boundaries(turn: int, expected_era: EmpireEraId) -> None:
    assert get_empire_era(turn).era_id is expected_era


def test_campaign_goals_map_to_distinct_scale_theses() -> None:
    assert (
        get_scale_thesis(CampaignGoalId.PROFIT_MACHINE).thesis_id
        is ScaleThesisId.OPERATING_FLYWHEEL
    )
    assert (
        get_scale_thesis(CampaignGoalId.PORTFOLIO_EMPIRE).thesis_id
        is ScaleThesisId.PLATFORM_ECOSYSTEM
    )
    assert (
        get_scale_thesis(CampaignGoalId.CATEGORY_LEADER).thesis_id
        is ScaleThesisId.CATEGORY_STANDARD
    )


def test_empire_scenario_exposes_four_derived_territories() -> None:
    state = create_new_game(scenario_id=EMPIRE_SCENARIO_ID)

    snapshot = build_empire_snapshot(state)

    assert snapshot.era.era_id is EmpireEraId.FOUNDATION
    assert snapshot.thesis.thesis_id is ScaleThesisId.PLATFORM_ECOSYSTEM
    assert {territory.segment for territory in snapshot.territories} == set(MarketSegment)
    startup = next(
        territory
        for territory in snapshot.territories
        if territory.segment is MarketSegment.STARTUP
    )
    assert startup.active_products == 1
    assert startup.users == 50
    assert startup.status in {TerritoryStatus.UNDER_PRESSURE, TerritoryStatus.CONTESTED}
    assert snapshot.next_milestone == "Growth at Turn 6 with a healthy core"


def test_standard_scenario_is_unchanged_by_empire_turn_layer() -> None:
    state = create_new_game(scenario_id="founder_journey")
    before = state.model_dump()

    summary = apply_empire_turn_effects(
        state,
        resolved_turn=8,
        net_cash_flow=Decimal("2500.00"),
    )

    assert summary is None
    assert state.model_dump() == before


def test_operating_flywheel_repairs_the_operating_core() -> None:
    state = create_new_game(
        scenario_id=EMPIRE_SCENARIO_ID,
        campaign_goal_id=CampaignGoalId.PROFIT_MACHINE,
    )
    state.products[0].technical_debt = 20
    state.support_program.backlog_queue = 3
    initial_profitability_score = state.finance.board_profitability_score

    summary = apply_empire_turn_effects(
        state,
        resolved_turn=6,
        net_cash_flow=Decimal("500.00"),
    )

    assert summary is not None
    assert state.products[0].technical_debt == 19
    assert state.support_program.backlog_queue == 2
    assert state.finance.board_profitability_score == initial_profitability_score + 1


def test_platform_ecosystem_improves_the_weakest_cross_segment_product() -> None:
    state = create_new_game(scenario_id=EMPIRE_SCENARIO_ID)
    product, _ = create_product_from_template(
        "Nexus Work",
        state.products,
        template_id="workflow_suite",
    )
    product.target_segment = MarketSegment.SMB
    product.market_fit = 30
    state.products.append(product)

    summary = apply_empire_turn_effects(
        state,
        resolved_turn=6,
        net_cash_flow=Decimal("0.00"),
    )

    assert summary is not None
    assert product.market_fit == 31
    assert "weakest product-market fit" in summary.thesis_effect


def test_category_standard_converts_quality_into_reputation() -> None:
    state = create_new_game(
        scenario_id=EMPIRE_SCENARIO_ID,
        campaign_goal_id=CampaignGoalId.CATEGORY_LEADER,
    )
    state.products[0].quality = 65
    initial_reputation = state.company.reputation

    summary = apply_empire_turn_effects(
        state,
        resolved_turn=6,
        net_cash_flow=Decimal("0.00"),
    )

    assert summary is not None
    assert state.company.reputation == initial_reputation + 1
    assert summary.reputation_delta == 1


def test_platform_crisis_reduces_reliability_confidence() -> None:
    state = create_new_game(scenario_id=EMPIRE_SCENARIO_ID)
    state.products[0].technical_debt = 70
    initial_reliability_score = state.finance.board_reliability_score
    initial_reputation = state.company.reputation

    before = build_empire_snapshot(state)
    summary = apply_empire_turn_effects(
        state,
        resolved_turn=6,
        net_cash_flow=Decimal("0.00"),
    )

    assert before.dominant_crisis is not None
    assert before.dominant_crisis.crisis_id is EmpireCrisisId.PLATFORM_INTEGRITY
    assert summary is not None
    assert state.finance.board_reliability_score == initial_reliability_score - 1
    assert state.company.reputation == initial_reputation - 1


def test_empire_rival_counters_strongest_territory_on_response_turn() -> None:
    state = create_new_game(scenario_id=EMPIRE_SCENARIO_ID)
    state.company.current_turn = 8
    startup_rival = next(
        competitor
        for competitor in state.competitors
        if competitor.focus_segment is MarketSegment.STARTUP
    )
    initial_aggression = startup_rival.aggression

    summary = apply_empire_turn_effects(
        state,
        resolved_turn=8,
        net_cash_flow=Decimal("500.00"),
    )

    assert summary is not None
    assert startup_rival.aggression == initial_aggression + 2
    assert "Launch Dominion countered" in summary.rival_response


def test_empire_victory_is_blocked_until_legacy_era() -> None:
    state = create_new_game(scenario_id=EMPIRE_SCENARIO_ID)
    state.products[0].user_count = 70
    for name, segment in (
        ("Nexus Work", MarketSegment.SMB),
        ("Nexus Command", MarketSegment.ENTERPRISE),
    ):
        product, _ = create_product_from_template(
            name,
            state.products,
            template_id="workflow_suite",
        )
        product.target_segment = segment
        product.user_count = 70
        state.products.append(product)

    state.company.current_turn = EMPIRE_MIN_VICTORY_TURN - 1
    assert check_victory(state) is None

    state.company.current_turn = EMPIRE_MIN_VICTORY_TURN
    assert check_victory(state) is not None


def test_empire_resolution_surfaces_strategy_feedback() -> None:
    state = create_new_game(scenario_id=EMPIRE_SCENARIO_ID)

    resolution = resolve_turn(state, RandomSource(seed=37))

    assert "Empire: Foundation | control 0/4." in resolution.narrative
    assert resolution.state.company.current_turn == 2


def test_empire_catalog_copy_marks_the_long_run(tmp_path: Path) -> None:
    choice = next(
        choice
        for choice in list_scenario_choices(tmp_path / "catalog.db")
        if choice.scenario_id == EMPIRE_SCENARIO_ID
    )

    assert choice.track_label == "Empire"
    assert choice.stage_hint == "25-turn strategic expansion"
    assert choice.act_preview == "Foundation > Growth > Scale > Expansion > Legacy"
    assert choice.locked is False


def test_empire_preview_does_not_expand_the_frozen_beta_catalog() -> None:
    assert capture_catalog_snapshot() == BETA_CATALOG_CEILING


def test_empire_report_reuses_existing_panel_without_adding_workspace() -> None:
    state = create_new_game(scenario_id=EMPIRE_SCENARIO_ID)

    panels = build_deep_dive_panel_view_models(
        state,
        selected_product_id=state.products[0].id.hex,
    )
    report = next(panel for panel in panels if panel.key == "report")

    assert len(panels) == 8
    assert report.title == "Empire Plan / Market Map"
    assert [metric.label for metric in report.metrics] == [
        "Era",
        "Empire",
        "Control",
        "Crisis",
    ]
    assert any(line.startswith("STARTUP:") for line in report.detail_lines)


def test_empire_save_round_trip_preserves_all_source_state(tmp_path: Path) -> None:
    coordinator = SaveLoadCoordinator(tmp_path / "empire-save.db")
    state = create_new_game(scenario_id=EMPIRE_SCENARIO_ID)
    state.company.current_turn = 17
    before_snapshot = build_empire_snapshot(state)

    coordinator.save_game("empire", state, RandomSource(seed=71))
    loaded = coordinator.load_game("empire")
    after_snapshot = build_empire_snapshot(loaded.state)

    assert loaded.state.model_dump() == state.model_dump()
    assert after_snapshot == before_snapshot
