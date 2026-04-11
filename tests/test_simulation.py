from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest

from nexus_tech.config import DEFAULT_COMPANY_NAME, DEFAULT_PRODUCT_NAME
from nexus_tech.domain.models import (
    Company,
    CompanyStrategy,
    Employee,
    EmployeeRole,
    EventCategory,
    EventHistoryEntry,
    GameState,
    LifecycleStage,
    MarketSegment,
    MilestoneEntry,
    MilestoneId,
    PendingEvent,
    PricingTier,
    Product,
    RoadmapFocus,
    Seniority,
    TurnAction,
)
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.economy import (
    calculate_total_operating_cost,
    calculate_total_revenue,
    calculate_total_salary_cost,
)
from nexus_tech.simulation.engine import ActionContext, apply_action, create_new_game, resolve_turn
from nexus_tech.simulation.event_registry import EventDefinition, get_event_registry
from nexus_tech.simulation.events import (
    get_eligible_event_definitions,
    resolve_pending_event,
    select_event_definition,
    select_weighted_definition,
)
from nexus_tech.simulation.growth import calculate_churned_users
from nexus_tech.simulation.pricing import calculate_effective_revenue_per_user
from nexus_tech.simulation.product_progression import calculate_delivery_penalty
from nexus_tech.simulation.randomness import RandomSource
from nexus_tech.simulation.reporting import calculate_run_score
from nexus_tech.simulation.team import calculate_effective_productivity


class FixedRandom:
    def __init__(self, value: int) -> None:
        self.value = value

    def randint(self, start: int, end: int) -> int:
        return self.value


class SequenceRandom:
    def __init__(self, values: list[int]) -> None:
        self.values = values
        self.index = 0

    def randint(self, start: int, end: int) -> int:
        value = self.values[self.index % len(self.values)]
        self.index += 1
        return value


def make_product(
    name: str,
    *,
    lifecycle_stage: LifecycleStage = LifecycleStage.GROWTH,
    quality: int = 58,
    bug_level: int = 18,
    market_fit: int = 52,
    technical_debt: int = 14,
    user_count: int = 35,
    revenue_per_user: Decimal = Decimal("30.00"),
    feature_count: int = 1,
    maintenance_cost: Decimal = Decimal("260.00"),
    acquisition_rate: Decimal = Decimal("0.0600"),
    churn_rate: Decimal = Decimal("0.0500"),
    pricing_tier: PricingTier = PricingTier.STANDARD,
    target_segment: MarketSegment = MarketSegment.STARTUP,
    is_active: bool = True,
) -> Product:
    return Product(
        name=name,
        lifecycle_stage=lifecycle_stage,
        quality=quality,
        bug_level=bug_level,
        market_fit=market_fit,
        technical_debt=technical_debt,
        user_count=user_count,
        revenue_per_user=revenue_per_user,
        feature_count=feature_count,
        maintenance_cost=maintenance_cost,
        acquisition_rate=acquisition_rate,
        churn_rate=churn_rate,
        pricing_tier=pricing_tier,
        target_segment=target_segment,
        is_active=is_active,
    )


def make_employee(
    full_name: str,
    role: EmployeeRole,
    *,
    seniority: Seniority = Seniority.MID,
    salary: Decimal | None = None,
    energy: int = 82,
    morale: int = 76,
    productivity: int | None = None,
    specialization: str = "generalist",
    assigned_product_id: UUID | None = None,
) -> Employee:
    return Employee(
        full_name=full_name,
        role=role,
        seniority=seniority,
        salary=salary or Decimal("800.00"),
        energy=energy,
        morale=morale,
        productivity=productivity or 64,
        specialization=specialization,
        assigned_product_id=assigned_product_id,
    )


def make_state(
    *products: Product,
    employees: list[Employee] | None = None,
    cash_on_hand: Decimal = Decimal("6000.00"),
    strategy: CompanyStrategy = CompanyStrategy.BALANCED,
    roadmap_focus: RoadmapFocus = RoadmapFocus.BALANCED_EXECUTION,
    current_turn: int = 1,
    pending_event: PendingEvent | None = None,
    event_history: list[EventHistoryEntry] | None = None,
    milestone_history: list[MilestoneEntry] | None = None,
) -> GameState:
    return GameState(
        company=Company(
            name="NEXUS TECH",
            cash_on_hand=cash_on_hand,
            reputation=50,
            strategy=strategy,
            current_turn=current_turn,
        ),
        products=list(products),
        employees=employees or [],
        pending_event=pending_event,
        event_history=event_history or [],
        milestone_history=milestone_history or [],
        roadmap_focus=roadmap_focus,
        roadmap_set_turn=max(1, current_turn - 1),
        action_points_remaining=BALANCE.actions_per_turn,
    )


def test_product_operating_cost_includes_support_and_technical_debt() -> None:
    product = make_product(
        "Costly",
        user_count=25,
        maintenance_cost=Decimal("300.00"),
        technical_debt=10,
    )
    state = make_state(product)

    operating_cost = calculate_total_operating_cost(state.company, [product], [])

    assert operating_cost == Decimal("1210.00")


def test_multi_product_revenue_aggregates_only_active_products() -> None:
    state = make_state(
        make_product("Core", user_count=20, revenue_per_user=Decimal("25.00")),
        make_product("Cloud", user_count=10, revenue_per_user=Decimal("40.00")),
        make_product(
            "Legacy",
            user_count=99,
            revenue_per_user=Decimal("99.00"),
            is_active=False,
        ),
    )

    revenue = calculate_total_revenue(state.products)

    assert revenue == Decimal("900.00")


def test_churn_behavior_is_higher_for_bad_product_health() -> None:
    bad_product = make_product(
        "Buggy",
        lifecycle_stage=LifecycleStage.DECLINING,
        quality=25,
        bug_level=65,
        market_fit=20,
        technical_debt=70,
        user_count=100,
        churn_rate=Decimal("0.1200"),
    )
    healthy_product = make_product(
        "Healthy",
        quality=80,
        bug_level=5,
        market_fit=75,
        technical_debt=8,
        user_count=100,
        churn_rate=Decimal("0.0400"),
    )

    bad_churn = calculate_churned_users(bad_product, FixedRandom(0))
    healthy_churn = calculate_churned_users(healthy_product, FixedRandom(0))

    assert bad_churn > healthy_churn


def test_technical_debt_penalty_reduces_quality_improvement_efficiency() -> None:
    low_debt_state = make_state(make_product("Low Debt", technical_debt=10))
    high_debt_state = make_state(make_product("High Debt", technical_debt=80))

    low_outcome = apply_action(
        low_debt_state,
        TurnAction.IMPROVE_QUALITY,
        context=ActionContext(target_product_id=low_debt_state.products[0].id),
    )
    high_outcome = apply_action(
        high_debt_state,
        TurnAction.IMPROVE_QUALITY,
        context=ActionContext(target_product_id=high_debt_state.products[0].id),
    )

    low_gain = low_outcome.state.products[0].quality - low_debt_state.products[0].quality
    high_gain = high_outcome.state.products[0].quality - high_debt_state.products[0].quality

    assert calculate_delivery_penalty(high_debt_state.products[0]) > calculate_delivery_penalty(
        low_debt_state.products[0]
    )
    assert low_gain > high_gain


def test_company_strategy_changes_operating_cost_profile() -> None:
    product = make_product("Core")
    growth_state = make_state(product.model_copy(deep=True), strategy=CompanyStrategy.GROWTH)
    efficiency_state = make_state(
        product.model_copy(deep=True),
        strategy=CompanyStrategy.EFFICIENCY,
    )

    growth_cost = calculate_total_operating_cost(
        growth_state.company,
        growth_state.products,
        growth_state.employees,
    )
    efficiency_cost = calculate_total_operating_cost(
        efficiency_state.company,
        efficiency_state.products,
        efficiency_state.employees,
    )

    assert growth_cost > efficiency_cost


def test_adjust_pricing_changes_effective_revenue_and_market_fit() -> None:
    state = make_state(make_product("Core", quality=70))

    adjusted = apply_action(
        state,
        TurnAction.ADJUST_PRICING,
        context=ActionContext(
            target_product_id=state.products[0].id,
            pricing_tier=PricingTier.PREMIUM,
        ),
    )

    adjusted_product = adjusted.state.products[0]
    assert adjusted_product.pricing_tier is PricingTier.PREMIUM
    assert (
        calculate_effective_revenue_per_user(adjusted_product) > adjusted_product.revenue_per_user
    )
    assert adjusted_product.market_fit > state.products[0].market_fit


def test_budget_pricing_reduces_churn_pressure() -> None:
    budget_product = make_product(
        "Budget",
        pricing_tier=PricingTier.BUDGET,
        user_count=100,
        churn_rate=Decimal("0.0600"),
        bug_level=20,
        technical_debt=20,
    )
    premium_product = make_product(
        "Premium",
        pricing_tier=PricingTier.PREMIUM,
        user_count=100,
        churn_rate=Decimal("0.0600"),
        bug_level=20,
        technical_debt=20,
        quality=75,
    )

    assert calculate_churned_users(budget_product, FixedRandom(0)) < calculate_churned_users(
        premium_product,
        FixedRandom(0),
    )


def test_enterprise_segment_has_higher_churn_than_indie_under_same_conditions() -> None:
    indie_product = make_product(
        "Indie",
        pricing_tier=PricingTier.PREMIUM,
        quality=55,
        market_fit=46,
        bug_level=24,
        technical_debt=22,
        user_count=120,
        target_segment=MarketSegment.INDIE,
    )
    enterprise_product = make_product(
        "Enterprise",
        pricing_tier=PricingTier.PREMIUM,
        quality=55,
        market_fit=46,
        bug_level=24,
        technical_debt=22,
        user_count=120,
        target_segment=MarketSegment.ENTERPRISE,
    )

    assert calculate_churned_users(indie_product, FixedRandom(0)) < calculate_churned_users(
        enterprise_product,
        FixedRandom(0),
    )


def test_sunsetting_product_removes_it_from_active_economy() -> None:
    state = make_state(make_product("Analytics"))

    outcome = apply_action(
        state,
        TurnAction.SUNSET_PRODUCT,
        context=ActionContext(target_product_id=state.products[0].id),
    )

    sunset_product = outcome.state.products[0]
    assert sunset_product.is_active is False
    assert sunset_product.lifecycle_stage is LifecycleStage.SUNSET
    assert sunset_product.user_count == 0
    assert calculate_total_revenue(outcome.state.products) == Decimal("0.00")


def test_set_company_strategy_action_updates_company_state() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")

    outcome = apply_action(
        state,
        TurnAction.SET_COMPANY_STRATEGY,
        context=ActionContext(strategy=CompanyStrategy.QUALITY),
    )

    assert outcome.state.company.strategy is CompanyStrategy.QUALITY


def test_set_target_segment_updates_product_segment() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")

    outcome = apply_action(
        state,
        TurnAction.SET_TARGET_SEGMENT,
        context=ActionContext(
            target_product_id=state.products[0].id,
            target_segment=MarketSegment.SMB,
        ),
    )

    assert outcome.state.products[0].target_segment is MarketSegment.SMB


def test_set_roadmap_updates_state_and_platform_rebuild_changes_execution_profile() -> None:
    product = make_product("Core", maintenance_cost=Decimal("260.00"), technical_debt=36)
    base_state = make_state(product)
    platform_state = apply_action(
        base_state,
        TurnAction.SET_ROADMAP,
        context=ActionContext(roadmap_focus=RoadmapFocus.PLATFORM_REBUILD),
    ).state

    baseline_cost = calculate_total_operating_cost(
        base_state.company,
        base_state.products,
        base_state.employees,
        roadmap_focus=base_state.roadmap_focus,
        roadmap_set_turn=base_state.roadmap_set_turn,
    )
    platform_cost = calculate_total_operating_cost(
        platform_state.company,
        platform_state.products,
        platform_state.employees,
        roadmap_focus=platform_state.roadmap_focus,
        roadmap_set_turn=platform_state.roadmap_set_turn,
    )
    debt_reduction = apply_action(
        platform_state,
        TurnAction.REDUCE_TECHNICAL_DEBT,
        context=ActionContext(target_product_id=platform_state.products[0].id),
    )

    assert platform_state.roadmap_focus is RoadmapFocus.PLATFORM_REBUILD
    assert platform_cost > baseline_cost
    assert (
        debt_reduction.state.products[0].technical_debt
        < platform_state.products[0].technical_debt
    )


def test_create_product_validation_rejects_duplicate_names() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")

    with pytest.raises(ValueError, match="already exists"):
        apply_action(
            state,
            TurnAction.CREATE_PRODUCT,
            context=ActionContext(new_product_name="Nexus One"),
        )


def test_resolve_turn_sets_game_over_when_portfolio_burn_exceeds_cash() -> None:
    state = make_state(
        make_product(
            "Burner",
            user_count=0,
            revenue_per_user=Decimal("0.00"),
            maintenance_cost=Decimal("500.00"),
            technical_debt=80,
        ),
        cash_on_hand=Decimal("100.00"),
    )

    resolution = resolve_turn(state, FixedRandom(0))

    assert resolution.state.company.game_over is True
    assert resolution.state.company.cash_on_hand < Decimal("0.00")


def test_resolve_turn_unlocks_milestone_when_user_threshold_is_reached() -> None:
    state = make_state(
        make_product("Core", user_count=102, quality=72, market_fit=70),
        current_turn=3,
    )

    resolution = resolve_turn(state, FixedRandom(0))

    assert any(
        entry.milestone_id is MilestoneId.FIRST_100_USERS
        for entry in resolution.state.milestone_history
    )
    assert any(
        entry.milestone_id is MilestoneId.FIRST_100_USERS
        for entry in resolution.unlocked_milestones
    )


def test_hiring_and_firing_change_salary_burden() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")

    hired = apply_action(
        state,
        TurnAction.HIRE_EMPLOYEE,
        context=ActionContext(
            hire_full_name="Ada Wong",
            hire_role=EmployeeRole.ENGINEER,
            hire_seniority=Seniority.MID,
            hire_specialization="platform",
        ),
    )

    assert calculate_total_salary_cost(hired.state.employees) > Decimal("0.00")
    assert calculate_total_operating_cost(
        hired.state.company,
        hired.state.products,
        hired.state.employees,
    ) > (
        calculate_total_operating_cost(
            state.company,
            state.products,
            state.employees,
        )
    )

    employee_id = hired.state.employees[0].id
    fired = apply_action(
        hired.state,
        TurnAction.FIRE_EMPLOYEE,
        context=ActionContext(employee_id=employee_id),
    )

    assert calculate_total_salary_cost(fired.state.employees) == Decimal("0.00")


def test_assignment_increases_engineer_effect_on_quality_work() -> None:
    product = make_product("Core")
    assigned_engineer = make_employee(
        "Rin Dev",
        EmployeeRole.ENGINEER,
        assigned_product_id=product.id,
        productivity=72,
    )
    unassigned_engineer = make_employee(
        "Rin Dev",
        EmployeeRole.ENGINEER,
        assigned_product_id=None,
        productivity=72,
    )
    assigned_state = make_state(product.model_copy(deep=True), employees=[assigned_engineer])
    unassigned_state = make_state(product.model_copy(deep=True), employees=[unassigned_engineer])

    assigned_outcome = apply_action(
        assigned_state,
        TurnAction.IMPROVE_QUALITY,
        context=ActionContext(target_product_id=assigned_state.products[0].id),
    )
    unassigned_outcome = apply_action(
        unassigned_state,
        TurnAction.IMPROVE_QUALITY,
        context=ActionContext(target_product_id=unassigned_state.products[0].id),
    )

    assigned_gain = assigned_outcome.state.products[0].quality - assigned_state.products[0].quality
    unassigned_gain = (
        unassigned_outcome.state.products[0].quality - unassigned_state.products[0].quality
    )

    assert assigned_gain > unassigned_gain


def test_burnout_reduces_effective_productivity_and_rest_team_recovers() -> None:
    product = make_product("Core", bug_level=50, technical_debt=70)
    employee = make_employee(
        "Tired Dev",
        EmployeeRole.ENGINEER,
        assigned_product_id=product.id,
        energy=42,
        morale=60,
        productivity=70,
    )
    state = make_state(product, employees=[employee])

    before_productivity = calculate_effective_productivity(state.employees[0])
    resolution = resolve_turn(state, FixedRandom(0))
    after_turn_productivity = calculate_effective_productivity(resolution.state.employees[0])

    rested = apply_action(
        resolution.state,
        TurnAction.REST_TEAM,
        context=ActionContext(),
    )
    after_rest_productivity = calculate_effective_productivity(rested.state.employees[0])

    assert resolution.state.employees[0].energy < employee.energy
    assert after_turn_productivity < before_productivity
    assert after_rest_productivity > after_turn_productivity


def test_role_specific_contributions_are_visible_in_outcomes() -> None:
    base_product = make_product("LaunchPad", market_fit=45, bug_level=12)

    engineer = make_employee(
        "Eli Engineer",
        EmployeeRole.ENGINEER,
        assigned_product_id=base_product.id,
        productivity=74,
    )
    marketer = make_employee(
        "Mara Marketer",
        EmployeeRole.MARKETER,
        assigned_product_id=base_product.id,
        productivity=74,
    )

    engineer_quality_state = make_state(base_product.model_copy(deep=True), employees=[engineer])
    marketer_quality_state = make_state(base_product.model_copy(deep=True), employees=[marketer])

    engineer_quality = apply_action(
        engineer_quality_state,
        TurnAction.IMPROVE_QUALITY,
        context=ActionContext(target_product_id=engineer_quality_state.products[0].id),
    )
    marketer_quality = apply_action(
        marketer_quality_state,
        TurnAction.IMPROVE_QUALITY,
        context=ActionContext(target_product_id=marketer_quality_state.products[0].id),
    )

    engineer_marketing_state = make_state(
        base_product.model_copy(deep=True),
        employees=[engineer.model_copy(deep=True)],
    )
    marketer_marketing_state = make_state(
        base_product.model_copy(deep=True),
        employees=[marketer.model_copy(deep=True)],
    )

    engineer_marketing = apply_action(
        engineer_marketing_state,
        TurnAction.MARKET_PRODUCT,
        context=ActionContext(target_product_id=engineer_marketing_state.products[0].id),
    )
    marketer_marketing = apply_action(
        marketer_marketing_state,
        TurnAction.MARKET_PRODUCT,
        context=ActionContext(target_product_id=marketer_marketing_state.products[0].id),
    )

    engineer_quality_gain = (
        engineer_quality.state.products[0].quality - engineer_quality_state.products[0].quality
    )
    marketer_quality_gain = (
        marketer_quality.state.products[0].quality - marketer_quality_state.products[0].quality
    )
    engineer_user_gain = (
        engineer_marketing.state.products[0].user_count
        - engineer_marketing_state.products[0].user_count
    )
    marketer_user_gain = (
        marketer_marketing.state.products[0].user_count
        - marketer_marketing_state.products[0].user_count
    )

    assert engineer_quality_gain > marketer_quality_gain
    assert marketer_user_gain > engineer_user_gain


def test_resolve_turn_resets_action_points_for_next_turn() -> None:
    state = create_new_game(DEFAULT_COMPANY_NAME, DEFAULT_PRODUCT_NAME)
    state.action_points_remaining = 0

    resolution = resolve_turn(state, FixedRandom(0))

    assert resolution.state.company.current_turn == 2
    assert resolution.state.action_points_remaining == BALANCE.actions_per_turn


def test_resolve_turn_appends_turn_history_and_run_score() -> None:
    state = create_new_game(DEFAULT_COMPANY_NAME, DEFAULT_PRODUCT_NAME)

    resolution = resolve_turn(state, FixedRandom(0))

    assert len(resolution.state.turn_history) == 1
    entry = resolution.state.turn_history[0]
    assert entry.turn == 1
    assert entry.total_users == resolution.run_score.total_users
    assert resolution.run_score.total_score == calculate_run_score(resolution.state).total_score


def test_resolve_turn_sets_victory_when_company_hits_scale_threshold() -> None:
    state = make_state(
        make_product(
            "Core",
            lifecycle_stage=LifecycleStage.MATURE,
            quality=84,
            market_fit=82,
            bug_level=6,
            technical_debt=10,
            user_count=260,
            revenue_per_user=Decimal("40.00"),
            maintenance_cost=Decimal("220.00"),
            target_segment=MarketSegment.SMB,
        ),
        make_product(
            "Flow",
            lifecycle_stage=LifecycleStage.MATURE,
            quality=80,
            market_fit=79,
            bug_level=8,
            technical_debt=12,
            user_count=210,
            revenue_per_user=Decimal("34.00"),
            maintenance_cost=Decimal("210.00"),
            target_segment=MarketSegment.STARTUP,
        ),
        cash_on_hand=Decimal("22000.00"),
        current_turn=BALANCE.victory_min_turn,
    )
    state.company.reputation = 78

    resolution = resolve_turn(state, FixedRandom(0))

    assert resolution.state.victory_achieved is True
    assert resolution.victory_reason is not None


def test_three_turn_gameplay_integration_remains_stable() -> None:
    state = create_new_game(DEFAULT_COMPANY_NAME, DEFAULT_PRODUCT_NAME)
    rng = RandomSource(seed=23)
    initial_quality = state.products[0].quality

    state = apply_action(
        state,
        TurnAction.HIRE_EMPLOYEE,
        context=ActionContext(
            hire_full_name="Ada Wong",
            hire_role=EmployeeRole.ENGINEER,
            hire_seniority=Seniority.MID,
            hire_specialization="platform",
        ),
    ).state
    employee_id = state.employees[0].id
    state = apply_action(
        state,
        TurnAction.ASSIGN_EMPLOYEE,
        context=ActionContext(
            employee_id=employee_id,
            target_product_id=state.products[0].id,
        ),
    ).state
    state = resolve_turn(state, rng).state

    state = apply_action(
        state,
        TurnAction.IMPROVE_QUALITY,
        context=ActionContext(target_product_id=state.products[0].id),
    ).state
    state = apply_action(
        state,
        TurnAction.MARKET_PRODUCT,
        context=ActionContext(target_product_id=state.products[0].id),
    ).state
    state = resolve_turn(state, rng).state

    state = apply_action(
        state,
        TurnAction.CREATE_PRODUCT,
        context=ActionContext(new_product_name="Nexus Flow"),
    ).state
    new_product = next(product for product in state.products if product.name == "Nexus Flow")
    state = apply_action(
        state,
        TurnAction.ASSIGN_EMPLOYEE,
        context=ActionContext(
            employee_id=employee_id,
            target_product_id=new_product.id,
        ),
    ).state
    state = resolve_turn(state, rng).state

    assert state.company.game_over is False
    assert state.company.current_turn == 4
    assert state.action_points_remaining == BALANCE.actions_per_turn
    assert len(state.products) == 2
    assert len(state.employees) == 1
    assert state.products[0].quality > initial_quality
    assert state.products[1].name == "Nexus Flow"
    assert state.employees[0].assigned_product_id == new_product.id
    assert len(state.turn_history) == 3
    assert state.company.cash_on_hand != BALANCE.starting_cash


def test_weighted_selection_prefers_heavier_event() -> None:
    lightweight = EventDefinition(
        event_id="lightweight",
        category=EventCategory.MARKET_OPPORTUNITY,
        weight=1,
        cooldown_turns=0,
        is_eligible=lambda state: True,
        build_pending_event=lambda state, rng, cooldown_turns: PendingEvent(
            event_id="lightweight",
            category=EventCategory.MARKET_OPPORTUNITY,
            title="Lightweight",
            description="Lightweight test event.",
            triggered_turn=state.company.current_turn,
            cooldown_turns=cooldown_turns,
            options=[],
        ),
    )
    heavyweight = EventDefinition(
        event_id="heavyweight",
        category=EventCategory.MARKET_OPPORTUNITY,
        weight=9,
        cooldown_turns=0,
        is_eligible=lambda state: True,
        build_pending_event=lambda state, rng, cooldown_turns: PendingEvent(
            event_id="heavyweight",
            category=EventCategory.MARKET_OPPORTUNITY,
            title="Heavyweight",
            description="Heavyweight test event.",
            triggered_turn=state.company.current_turn,
            cooldown_turns=cooldown_turns,
            options=[],
        ),
    )
    rng = SequenceRandom(list(range(1, 11)) * 5)

    selected_ids = [
        select_weighted_definition([lightweight, heavyweight], rng).event_id for _ in range(50)
    ]

    assert selected_ids.count("heavyweight") > selected_ids.count("lightweight")


def test_event_cooldown_filters_recent_event() -> None:
    product = make_product("Signal", market_fit=60, user_count=45)
    history_entry = EventHistoryEntry(
        event_id="sudden_press_mention",
        category=EventCategory.REPUTATION_INCIDENT,
        title="Sudden Press Mention",
        triggered_turn=2,
        resolved_turn=2,
        selected_option_id="ride_the_wave",
        selected_option_label="Ride the wave",
        result_text="Users jumped.",
    )
    state = make_state(
        product,
        current_turn=4,
        event_history=[history_entry],
    )

    eligible_ids = {definition.event_id for definition in get_eligible_event_definitions(state)}

    assert "sudden_press_mention" not in eligible_ids


def test_event_effect_application_updates_product_company_and_team() -> None:
    product = make_product("Core", bug_level=48, technical_debt=52)
    employee = make_employee(
        "Ada Wong",
        EmployeeRole.ENGINEER,
        assigned_product_id=product.id,
        energy=78,
        morale=74,
    )
    state = make_state(product, employees=[employee], current_turn=3)
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "severe_bug_incident"
    )
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "hotfix")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.products[0].bug_level < state.products[0].bug_level
    assert outcome.state.employees[0].energy < state.employees[0].energy
    assert outcome.history_entry.event_id == "severe_bug_incident"


def test_event_selection_is_deterministic_under_fixed_seed() -> None:
    state_a = make_state(
        make_product("Core", market_fit=62, user_count=50, bug_level=40, technical_debt=52),
        current_turn=4,
    )
    state_b = state_a.model_copy(deep=True)

    definition_a = select_event_definition(
        state_a,
        RandomSource(seed=17),
        enforce_trigger_roll=False,
    )
    definition_b = select_event_definition(
        state_b,
        RandomSource(seed=17),
        enforce_trigger_roll=False,
    )

    assert definition_a is not None
    assert definition_b is not None
    assert definition_a.event_id == definition_b.event_id
