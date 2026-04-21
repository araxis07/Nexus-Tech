from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest

from nexus_tech.config import DEFAULT_COMPANY_NAME, DEFAULT_PRODUCT_NAME
from nexus_tech.domain.models import (
    BudgetStance,
    CampaignGoalId,
    Company,
    CompanyStrategy,
    Competitor,
    CompetitorMove,
    CustomerAccount,
    CustomerAccountStatus,
    DifficultyMode,
    Employee,
    EmployeeRole,
    EventCategory,
    EventHistoryEntry,
    ExitOutcome,
    FinanceState,
    GameState,
    LifecycleStage,
    MarketCycle,
    MarketSegment,
    MilestoneEntry,
    MilestoneId,
    PendingEvent,
    PricingTier,
    Product,
    RoadmapFocus,
    Seniority,
    TurnAction,
    TurnLedgerEntry,
)
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.balance_lab import (
    format_balance_matrix_csv,
    format_balance_report_markdown,
    run_balance_audit,
    run_balance_batch,
    run_balance_comparison,
    run_balance_matrix,
)
from nexus_tech.simulation.campaign import evaluate_campaign_goal
from nexus_tech.simulation.competition import advance_competitors, calculate_competitor_pressure
from nexus_tech.simulation.customers import (
    apply_end_of_turn_customers,
    calculate_account_revenue,
)
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
from nexus_tech.simulation.finance import apply_end_of_turn_finance_drift
from nexus_tech.simulation.growth import (
    calculate_acquired_users,
    calculate_churned_users,
    calculate_effective_churn_rate_for_context,
)
from nexus_tech.simulation.late_game import (
    apply_end_of_turn_late_game,
    calculate_late_game_summary,
)
from nexus_tech.simulation.milestones import resolve_new_milestones
from nexus_tech.simulation.operations import calculate_operations_summary
from nexus_tech.simulation.planning import build_quarter_plan, is_quarter_plan_due
from nexus_tech.simulation.pricing import calculate_effective_revenue_per_user
from nexus_tech.simulation.product_progression import calculate_delivery_penalty
from nexus_tech.simulation.randomness import RandomSource
from nexus_tech.simulation.reporting import calculate_run_score
from nexus_tech.simulation.scaling import (
    calculate_company_scale_pressure,
    calculate_product_scale_pressure,
)
from nexus_tech.simulation.team import (
    calculate_effective_productivity,
    calculate_product_team_modifier,
)


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
    competitors: list[Competitor] | None = None,
    finance: FinanceState | None = None,
    cash_on_hand: Decimal = Decimal("6000.00"),
    strategy: CompanyStrategy = CompanyStrategy.BALANCED,
    roadmap_focus: RoadmapFocus = RoadmapFocus.BALANCED_EXECUTION,
    current_turn: int = 1,
    market_cycle: MarketCycle = MarketCycle.STEADY,
    market_cycle_turns_remaining: int = 3,
    budget_stance: BudgetStance = BudgetStance.BALANCED,
    difficulty_mode: DifficultyMode = DifficultyMode.STANDARD,
    campaign_goal_id: CampaignGoalId = CampaignGoalId.PROFIT_MACHINE,
    pending_event: PendingEvent | None = None,
    event_history: list[EventHistoryEntry] | None = None,
    milestone_history: list[MilestoneEntry] | None = None,
    customer_accounts: list[CustomerAccount] | None = None,
) -> GameState:
    state = GameState(
        company=Company(
            name="NEXUS TECH",
            cash_on_hand=cash_on_hand,
            reputation=50,
            strategy=strategy,
            current_turn=current_turn,
        ),
        products=list(products),
        employees=employees or [],
        finance=finance or FinanceState(),
        competitors=competitors or [],
        customer_accounts=customer_accounts or [],
        pending_event=pending_event,
        event_history=event_history or [],
        milestone_history=milestone_history or [],
        roadmap_focus=roadmap_focus,
        roadmap_set_turn=max(1, current_turn - 1),
        market_cycle=market_cycle,
        market_cycle_turns_remaining=market_cycle_turns_remaining,
        difficulty_mode=difficulty_mode,
        campaign_goal_id=campaign_goal_id,
        action_points_remaining=BALANCE.actions_per_turn,
    )
    state.quarter_plan = build_quarter_plan(state, budget_stance=budget_stance)
    return state


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


def test_key_account_revenue_aggregates_active_accounts_only() -> None:
    product = make_product("Enterprise Desk", target_segment=MarketSegment.ENTERPRISE)
    active_account = CustomerAccount(
        name="Enterprise Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("900.00"),
        satisfaction=72,
        expansion_potential=60,
        renewal_turn=4,
        churn_risk=12,
        status=CustomerAccountStatus.ACTIVE,
    )
    churned_account = active_account.model_copy(
        update={
            "name": "Lost Account",
            "contract_value": Decimal("700.00"),
            "status": CustomerAccountStatus.CHURNED,
        }
    )

    revenue = calculate_account_revenue([active_account, churned_account])

    assert revenue == Decimal("900.00")


def test_key_accounts_are_seeded_from_strong_product_traction() -> None:
    product = make_product(
        "Enterprise Desk",
        target_segment=MarketSegment.ENTERPRISE,
        user_count=30,
        quality=76,
        market_fit=72,
        bug_level=8,
        technical_debt=10,
    )
    accounts: list[CustomerAccount] = []

    summary = apply_end_of_turn_customers(accounts, [product], current_turn=3)

    assert summary.created_accounts == 1
    assert accounts[0].segment is MarketSegment.ENTERPRISE
    assert accounts[0].status is CustomerAccountStatus.ACTIVE
    assert summary.account_revenue > Decimal("0.00")


def test_renewal_churns_high_risk_key_account_and_reduces_users() -> None:
    product = make_product("Risky", user_count=40, quality=28, bug_level=70, technical_debt=80)
    account = CustomerAccount(
        name="Risky Renewal",
        product_id=product.id,
        segment=MarketSegment.STARTUP,
        contract_value=Decimal("500.00"),
        satisfaction=20,
        expansion_potential=25,
        renewal_turn=1,
        churn_risk=90,
        status=CustomerAccountStatus.AT_RISK,
    )

    summary = apply_end_of_turn_customers([account], [product], current_turn=1)

    assert summary.churned_accounts == 1
    assert account.status is CustomerAccountStatus.CHURNED
    assert product.user_count == 32


def test_resolve_turn_includes_key_account_revenue() -> None:
    product = make_product(
        "Account Core",
        user_count=0,
        revenue_per_user=Decimal("0.00"),
        maintenance_cost=Decimal("0.00"),
    )
    account = CustomerAccount(
        name="Anchor Account",
        product_id=product.id,
        segment=MarketSegment.STARTUP,
        contract_value=Decimal("500.00"),
        satisfaction=70,
        expansion_potential=40,
        renewal_turn=4,
        churn_risk=10,
        status=CustomerAccountStatus.ACTIVE,
    )
    state = make_state(product, customer_accounts=[account])

    resolution = resolve_turn(state, FixedRandom(0))

    assert resolution.customer_summary.account_revenue == Decimal("500.00")
    assert resolution.total_revenue >= Decimal("500.00")


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
        debt_reduction.state.products[0].technical_debt < platform_state.products[0].technical_debt
    )


def test_set_budget_stance_action_refreshes_quarter_plan_targets() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")
    original_plan = state.quarter_plan.model_copy(deep=True)

    outcome = apply_action(
        state,
        TurnAction.SET_BUDGET_STANCE,
        context=ActionContext(budget_stance=BudgetStance.AGGRESSIVE),
    )

    assert outcome.state.quarter_plan.budget_stance is BudgetStance.AGGRESSIVE
    assert outcome.state.quarter_plan.set_turn == state.company.current_turn
    assert outcome.state.quarter_plan.headcount_cap >= original_plan.headcount_cap


def test_operations_summary_adds_cost_when_portfolio_load_outpaces_team() -> None:
    state = make_state(
        make_product(
            "Desk",
            user_count=150,
            bug_level=32,
            technical_debt=38,
            feature_count=4,
            target_segment=MarketSegment.SMB,
        ),
        make_product(
            "Mesh",
            user_count=92,
            bug_level=28,
            technical_debt=34,
            feature_count=3,
            target_segment=MarketSegment.STARTUP,
        ),
        employees=[
            make_employee("Solo PM", EmployeeRole.PRODUCT_MANAGER, productivity=60),
        ],
        current_turn=9,
    )

    summary = calculate_operations_summary(
        state.products,
        state.employees,
        current_turn=state.company.current_turn,
    )

    assert summary.overload > 0
    assert summary.added_cost > Decimal("0.00")


def test_resolve_turn_reports_operations_cost_and_summary() -> None:
    state = make_state(
        make_product(
            "Desk",
            user_count=150,
            bug_level=32,
            technical_debt=38,
            feature_count=4,
            target_segment=MarketSegment.SMB,
        ),
        make_product(
            "Mesh",
            user_count=92,
            bug_level=28,
            technical_debt=34,
            feature_count=3,
            target_segment=MarketSegment.STARTUP,
        ),
        employees=[make_employee("Solo PM", EmployeeRole.PRODUCT_MANAGER, productivity=60)],
        current_turn=9,
    )

    resolution = resolve_turn(state, FixedRandom(0))

    assert resolution.total_operations_cost > Decimal("0.00")
    assert resolution.operations_summary.overload > 0
    assert resolution.operations_summary.summary


def test_expanding_market_cycle_improves_acquisition_vs_cooling() -> None:
    product = make_product(
        "Core",
        quality=72,
        market_fit=68,
        bug_level=12,
        technical_debt=16,
        user_count=80,
        target_segment=MarketSegment.STARTUP,
    )
    company = Company(
        name="NEXUS TECH",
        cash_on_hand=Decimal("6000.00"),
        reputation=58,
        strategy=CompanyStrategy.BALANCED,
        current_turn=3,
    )
    team_modifier = calculate_product_team_modifier([], product.id)

    cooling = calculate_acquired_users(
        company,
        product,
        FixedRandom(0),
        team_modifier,
        market_cycle=MarketCycle.COOLING,
    )
    expanding = calculate_acquired_users(
        company,
        product,
        FixedRandom(0),
        team_modifier,
        market_cycle=MarketCycle.EXPANDING,
    )

    assert expanding > cooling


def test_matching_competitor_increases_effective_churn_rate() -> None:
    product = make_product(
        "Core",
        pricing_tier=PricingTier.STANDARD,
        target_segment=MarketSegment.STARTUP,
        user_count=120,
        quality=58,
        market_fit=50,
        bug_level=22,
        technical_debt=24,
    )
    competitor = Competitor(
        name="Pressure Labs",
        focus_segment=MarketSegment.STARTUP,
        strength=74,
        aggression=69,
        pricing_tier=PricingTier.STANDARD,
        active_product_count=3,
    )

    baseline = calculate_effective_churn_rate_for_context(
        product,
        current_turn=4,
        market_cycle=MarketCycle.STEADY,
        competitors=[],
    )
    pressured = calculate_effective_churn_rate_for_context(
        product,
        current_turn=4,
        market_cycle=MarketCycle.STEADY,
        competitors=[competitor],
    )

    assert pressured > baseline


def test_quarter_plan_due_when_target_turn_has_passed() -> None:
    state = make_state(make_product("Core"), current_turn=5)
    state.quarter_plan.target_turn = 4

    assert is_quarter_plan_due(state) is True


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
    assert resolution.state.exit_outcome is not None
    assert resolution.state.exit_summary


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


def test_discount_push_competitor_move_shifts_pricing_and_expands_count() -> None:
    competitor = Competitor(
        name="Price Warp",
        focus_segment=MarketSegment.STARTUP,
        strength=62,
        aggression=58,
        pricing_tier=PricingTier.STANDARD,
        active_product_count=1,
    )

    advance_competitors([competitor], SequenceRandom([5, 0, 0]), market_cycle=MarketCycle.STEADY)

    assert competitor.current_move is CompetitorMove.DISCOUNT_PUSH
    assert competitor.pricing_tier is PricingTier.BUDGET
    assert competitor.active_product_count == 2


def test_competitor_feature_sprint_can_pivot_to_hottest_player_segment() -> None:
    competitor = Competitor(
        name="Pivot Labs",
        focus_segment=MarketSegment.INDIE,
        strength=64,
        aggression=57,
        pricing_tier=PricingTier.STANDARD,
        active_product_count=1,
        momentum=72,
    )
    portfolio = [
        make_product(
            "Enterprise Core",
            target_segment=MarketSegment.ENTERPRISE,
            user_count=210,
            market_fit=78,
            quality=80,
        )
    ]

    advance_competitors(
        [competitor],
        SequenceRandom([8, 0, 0]),
        market_cycle=MarketCycle.STEADY,
        portfolio_products=portfolio,
    )

    assert competitor.current_move is CompetitorMove.FEATURE_SPRINT
    assert competitor.focus_segment is MarketSegment.ENTERPRISE


def test_retrench_competitor_move_reduces_product_count() -> None:
    competitor = Competitor(
        name="Retrench Labs",
        focus_segment=MarketSegment.ENTERPRISE,
        strength=50,
        aggression=47,
        pricing_tier=PricingTier.BUDGET,
        active_product_count=3,
        momentum=30,
    )

    advance_competitors([competitor], SequenceRandom([12, 0, 0]), market_cycle=MarketCycle.STEADY)

    assert competitor.current_move is CompetitorMove.RETRENCH
    assert competitor.active_product_count == 2
    assert competitor.pricing_tier is PricingTier.PREMIUM


def test_strong_competitor_can_raise_funding_pressure() -> None:
    competitor = Competitor(
        name="Funded Rival",
        focus_segment=MarketSegment.STARTUP,
        strength=82,
        aggression=78,
        pricing_tier=PricingTier.STANDARD,
        active_product_count=2,
        momentum=88,
        funding_level=0,
    )

    advance_competitors([competitor], SequenceRandom([1, 0, 0]), market_cycle=MarketCycle.STEADY)

    assert competitor.funding_level > 0


def test_balance_batch_is_deterministic_under_fixed_seed_base() -> None:
    batch_a = run_balance_batch(
        scenario_id="founder_journey",
        difficulty_mode=DifficultyMode.STANDARD,
        campaign_goal_id=CampaignGoalId.PROFIT_MACHINE,
        runs=2,
        turns=4,
        seed_base=40,
    )
    batch_b = run_balance_batch(
        scenario_id="founder_journey",
        difficulty_mode=DifficultyMode.STANDARD,
        campaign_goal_id=CampaignGoalId.PROFIT_MACHINE,
        runs=2,
        turns=4,
        seed_base=40,
    )

    assert batch_a.victories == batch_b.victories
    assert batch_a.average_score == batch_b.average_score
    assert batch_a.results == batch_b.results


def test_balance_matrix_csv_export_is_stable() -> None:
    matrix = run_balance_matrix(
        scenario_ids=["founder_journey"],
        campaign_goal_id=CampaignGoalId.PROFIT_MACHINE,
        runs=1,
        turns=2,
        seed_base=30,
    )

    csv_output = format_balance_matrix_csv(matrix)

    assert csv_output.startswith(
        "scenario_id,difficulty,average_score,average_cash,average_users,victories,shutdowns"
    )
    assert "founder_journey" in csv_output


def test_balance_report_markdown_includes_matrix_and_audit_sections() -> None:
    matrix = run_balance_matrix(
        scenario_ids=["founder_journey"],
        campaign_goal_id=CampaignGoalId.PROFIT_MACHINE,
        runs=1,
        turns=2,
        seed_base=30,
    )
    audit = run_balance_audit(
        scenario_ids=["founder_journey"],
        campaign_goal_id=CampaignGoalId.PROFIT_MACHINE,
        runs=1,
        turns=2,
        seed_base=30,
    )

    report = format_balance_report_markdown(matrix, audit)

    assert report.startswith("# NEXUS TECH Balance Report")
    assert "## Matrix" in report
    assert "## Audit Findings" in report
    assert "founder_journey" in report


def test_referral_wave_event_rewards_healthy_product() -> None:
    product = make_product(
        "Glow",
        quality=74,
        bug_level=10,
        market_fit=64,
        user_count=55,
    )
    state = make_state(product, current_turn=5)
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "referral_wave"
    )
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "staff_referrals")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.products[0].user_count > state.products[0].user_count
    assert outcome.history_entry.event_id == "referral_wave"


def test_compliance_review_event_applies_trust_tradeoff() -> None:
    product = make_product(
        "Secure Desk",
        target_segment=MarketSegment.ENTERPRISE,
        market_fit=62,
        technical_debt=48,
        user_count=24,
    )
    state = make_state(product, current_turn=6)
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "compliance_review"
    )
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "fund_review")

    assert outcome.state.products[0].technical_debt < state.products[0].technical_debt
    assert outcome.state.company.reputation > state.company.reputation
    assert outcome.history_entry.event_id == "compliance_review"


def test_key_account_expansion_event_expands_contract() -> None:
    product = make_product(
        "Account Desk",
        target_segment=MarketSegment.ENTERPRISE,
        user_count=45,
        quality=74,
        market_fit=70,
    )
    account = CustomerAccount(
        name="Anchor Account",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("900.00"),
        satisfaction=76,
        expansion_potential=70,
        renewal_turn=6,
        churn_risk=12,
        status=CustomerAccountStatus.ACTIVE,
    )
    state = make_state(
        product,
        customer_accounts=[account],
        cash_on_hand=Decimal("9000.00"),
        current_turn=6,
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "key_account_expansion"
    )
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "build_success_plan")

    assert outcome.state.customer_accounts[0].contract_value > account.contract_value
    assert outcome.state.customer_accounts[0].satisfaction > account.satisfaction
    assert outcome.history_entry.event_id == "key_account_expansion"


def test_security_audit_event_protects_enterprise_trust() -> None:
    product = make_product(
        "Trust Center",
        target_segment=MarketSegment.ENTERPRISE,
        user_count=42,
        bug_level=22,
        technical_debt=36,
    )
    state = make_state(product, cash_on_hand=Decimal("9000.00"), current_turn=7)
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "security_audit"
    )
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "fund_audit")

    assert outcome.state.products[0].technical_debt < state.products[0].technical_debt
    assert outcome.state.products[0].bug_level < state.products[0].bug_level
    assert outcome.state.company.reputation > state.company.reputation
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.history_entry.event_id == "security_audit"


def test_enterprise_sales_cycle_can_expand_contract_value() -> None:
    product = make_product(
        "Enterprise Desk",
        target_segment=MarketSegment.ENTERPRISE,
        market_fit=62,
        user_count=42,
        revenue_per_user=Decimal("38.00"),
    )
    employee = make_employee(
        "Enterprise PM",
        EmployeeRole.PRODUCT_MANAGER,
        assigned_product_id=product.id,
        energy=80,
    )
    state = make_state(
        product,
        employees=[employee],
        cash_on_hand=Decimal("9000.00"),
        current_turn=6,
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "enterprise_sales_cycle"
    )
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "fund_poc")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.products[0].user_count > state.products[0].user_count
    assert outcome.state.products[0].revenue_per_user > state.products[0].revenue_per_user
    assert outcome.state.employees[0].energy < state.employees[0].energy
    assert outcome.history_entry.event_id == "enterprise_sales_cycle"


def test_product_launch_window_campaign_increases_demand_and_noise() -> None:
    product = make_product(
        "Launch Ready",
        quality=68,
        market_fit=62,
        feature_count=4,
        bug_level=10,
        user_count=60,
    )
    state = make_state(product, cash_on_hand=Decimal("9000.00"), current_turn=5)
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "product_launch_window"
    )
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "launch_campaign")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.products[0].user_count > state.products[0].user_count
    assert outcome.state.products[0].acquisition_rate > state.products[0].acquisition_rate
    assert outcome.state.products[0].bug_level > state.products[0].bug_level
    assert outcome.history_entry.event_id == "product_launch_window"


def test_platform_outage_recovery_reduces_bugs_but_costs_cash_and_energy() -> None:
    product = make_product(
        "Scale Core",
        user_count=140,
        bug_level=36,
        technical_debt=34,
    )
    employee = make_employee(
        "Oncall Engineer",
        EmployeeRole.ENGINEER,
        assigned_product_id=product.id,
        energy=82,
    )
    state = make_state(
        product,
        employees=[employee],
        cash_on_hand=Decimal("9000.00"),
        current_turn=7,
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "platform_outage"
    )
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "all_hands_recovery")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.products[0].bug_level < state.products[0].bug_level
    assert outcome.state.employees[0].energy < state.employees[0].energy
    assert outcome.history_entry.event_id == "platform_outage"


def test_competitor_acquisition_forces_portfolio_response() -> None:
    product = make_product("Flagship", quality=66, market_fit=61, user_count=120)
    competitor = Competitor(
        name="Bundle Giant",
        focus_segment=MarketSegment.STARTUP,
        strength=78,
        aggression=72,
        pricing_tier=PricingTier.STANDARD,
        active_product_count=3,
        momentum=80,
        funding_level=2,
    )
    state = make_state(
        product,
        competitors=[competitor],
        cash_on_hand=Decimal("9000.00"),
        current_turn=6,
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "competitor_acquisition"
    )
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "differentiate_against_stack")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.products[0].quality > state.products[0].quality
    assert outcome.state.products[0].market_fit > state.products[0].market_fit
    assert outcome.state.competitors[0].aggression > state.competitors[0].aggression
    assert outcome.history_entry.event_id == "competitor_acquisition"


def test_regulatory_shift_proactive_controls_reduce_debt_and_increase_trust() -> None:
    product = make_product(
        "Regulated Core",
        target_segment=MarketSegment.ENTERPRISE,
        market_fit=62,
        technical_debt=42,
        user_count=70,
    )
    state = make_state(product, cash_on_hand=Decimal("9000.00"), current_turn=8)
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "regulatory_shift"
    )
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "proactive_controls")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.products[0].technical_debt < state.products[0].technical_debt
    assert outcome.state.company.reputation > state.company.reputation
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.history_entry.event_id == "regulatory_shift"


def test_profitable_streak_milestone_unlocks_after_three_positive_turns() -> None:
    state = make_state(make_product("Core"), current_turn=6)
    state.turn_history = [
        TurnLedgerEntry(
            turn=3,
            total_revenue=Decimal("2100.00"),
            total_operating_cost=Decimal("1600.00"),
            net_cash_flow=Decimal("500.00"),
            cash_on_hand=Decimal("9000.00"),
            reputation=54,
            total_users=70,
            headcount=2,
            roadmap_focus=RoadmapFocus.BALANCED_EXECUTION,
        ),
        TurnLedgerEntry(
            turn=4,
            total_revenue=Decimal("2250.00"),
            total_operating_cost=Decimal("1700.00"),
            net_cash_flow=Decimal("550.00"),
            cash_on_hand=Decimal("9550.00"),
            reputation=55,
            total_users=78,
            headcount=2,
            roadmap_focus=RoadmapFocus.BALANCED_EXECUTION,
        ),
        TurnLedgerEntry(
            turn=5,
            total_revenue=Decimal("2400.00"),
            total_operating_cost=Decimal("1750.00"),
            net_cash_flow=Decimal("650.00"),
            cash_on_hand=Decimal("10200.00"),
            reputation=56,
            total_users=86,
            headcount=2,
            roadmap_focus=RoadmapFocus.BALANCED_EXECUTION,
        ),
    ]

    unlocked = resolve_new_milestones(state, unlocked_turn=6)

    assert any(entry.milestone_id is MilestoneId.PROFITABLE_STREAK for entry in unlocked)


def test_finance_costs_are_included_in_operating_burn() -> None:
    product = make_product("Core")
    finance = FinanceState(
        debt_principal=Decimal("3000.00"),
        loan_interest_rate=Decimal("0.0350"),
        investor_pressure=20,
    )
    state = make_state(product, finance=finance)

    operating_cost = calculate_total_operating_cost(
        state.company,
        state.products,
        state.employees,
        finance=state.finance,
    )

    assert operating_cost == Decimal("1335.00")


def test_board_confidence_moves_with_cash_flow_and_pressure() -> None:
    company = Company(
        name="NEXUS TECH",
        cash_on_hand=Decimal("8000.00"),
        reputation=55,
        current_turn=4,
    )
    finance = FinanceState(board_confidence=50, investor_pressure=0)

    apply_end_of_turn_finance_drift(
        finance,
        company,
        net_cash_flow=Decimal("200.00"),
    )
    after_positive_flow = finance.board_confidence
    finance.investor_pressure = 20
    apply_end_of_turn_finance_drift(
        finance,
        company,
        net_cash_flow=Decimal("-300.00"),
    )

    assert after_positive_flow > 50
    assert finance.board_confidence < after_positive_flow


def test_exit_evaluation_can_classify_independent_outcome() -> None:
    state = make_state(
        make_product("Core", user_count=80, market_fit=65),
        cash_on_hand=Decimal("16000.00"),
        current_turn=8,
    )

    resolution = resolve_turn(state, FixedRandom(0))
    resolution.state.victory_achieved = True
    resolution.state.exit_outcome = None
    from nexus_tech.simulation.endgame import apply_exit_outcome

    evaluation = apply_exit_outcome(resolution.state)

    assert evaluation.outcome in {
        ExitOutcome.PROFITABLE_INDEPENDENCE,
        ExitOutcome.STRATEGIC_ACQUISITION,
        ExitOutcome.IPO_READY,
    }
    assert resolution.state.exit_summary


def test_take_loan_and_repay_debt_change_finance_state() -> None:
    state = make_state(make_product("Core"), cash_on_hand=Decimal("8000.00"))

    loan_outcome = apply_action(state, TurnAction.TAKE_LOAN)

    assert loan_outcome.state.finance.debt_principal == Decimal("2500.00")
    assert loan_outcome.state.company.cash_on_hand == Decimal("10500.00")

    repay_outcome = apply_action(loan_outcome.state, TurnAction.REPAY_DEBT)

    assert repay_outcome.state.finance.debt_principal == Decimal("700.00")
    assert repay_outcome.state.company.cash_on_hand == Decimal("8700.00")


def test_raise_vc_requires_real_traction() -> None:
    weak_state = make_state(make_product("Core", user_count=35), cash_on_hand=Decimal("7000.00"))
    weak_state.company.reputation = 60

    with pytest.raises(ValueError, match="larger user base"):
        apply_action(weak_state, TurnAction.RAISE_VC)

    strong_state = make_state(
        make_product("Core", user_count=150, market_fit=70),
        cash_on_hand=Decimal("9000.00"),
        strategy=CompanyStrategy.GROWTH,
    )
    strong_state.company.reputation = 60

    outcome = apply_action(strong_state, TurnAction.RAISE_VC)

    assert outcome.state.finance.equity_dilution == Decimal("0.1500")
    assert outcome.state.company.cash_on_hand == Decimal("18600.00")


def test_competitor_move_and_momentum_raise_pressure() -> None:
    product = make_product(
        "Core",
        user_count=8,
        target_segment=MarketSegment.STARTUP,
        pricing_tier=PricingTier.STANDARD,
    )
    calm_competitor = Competitor(
        name="Calm Rival",
        focus_segment=MarketSegment.STARTUP,
        strength=55,
        aggression=42,
        pricing_tier=PricingTier.STANDARD,
        active_product_count=1,
        current_move=CompetitorMove.HOLD,
        momentum=18,
    )
    aggressive_competitor = calm_competitor.model_copy(
        update={
            "name": "Aggro Rival",
            "current_move": CompetitorMove.FEATURE_SPRINT,
            "momentum": 82,
            "strength": 68,
            "aggression": 63,
        }
    )
    calm_state = make_state(
        product.model_copy(deep=True),
        competitors=[calm_competitor],
        current_turn=1,
    )
    aggressive_state = make_state(
        product.model_copy(deep=True),
        competitors=[aggressive_competitor],
        current_turn=1,
    )

    calm_resolution = resolve_turn(calm_state, FixedRandom(0))
    aggressive_resolution = resolve_turn(aggressive_state, FixedRandom(0))

    assert aggressive_resolution.product_summaries[0].competitor_pressure > (
        calm_resolution.product_summaries[0].competitor_pressure
    )


def test_founder_difficulty_is_harsher_than_builder() -> None:
    product = make_product("Core", user_count=48, market_fit=60)
    builder_state = make_state(
        product.model_copy(deep=True),
        difficulty_mode=DifficultyMode.BUILDER,
    )
    founder_state = make_state(
        product.model_copy(deep=True),
        difficulty_mode=DifficultyMode.FOUNDER,
    )

    builder_cost = calculate_total_operating_cost(
        builder_state.company,
        builder_state.products,
        builder_state.employees,
        difficulty_mode=builder_state.difficulty_mode,
    )
    founder_cost = calculate_total_operating_cost(
        founder_state.company,
        founder_state.products,
        founder_state.employees,
        difficulty_mode=founder_state.difficulty_mode,
    )
    builder_acquisition = calculate_acquired_users(
        builder_state.company,
        builder_state.products[0],
        FixedRandom(0),
        calculate_product_team_modifier(builder_state.employees, builder_state.products[0].id),
        difficulty_mode=builder_state.difficulty_mode,
    )
    founder_acquisition = calculate_acquired_users(
        founder_state.company,
        founder_state.products[0],
        FixedRandom(0),
        calculate_product_team_modifier(founder_state.employees, founder_state.products[0].id),
        difficulty_mode=founder_state.difficulty_mode,
    )

    assert builder_cost < founder_cost
    assert builder_acquisition > founder_acquisition


def test_scale_pressure_penalizes_crowded_same_segment_portfolio() -> None:
    crowded_products = [
        make_product(
            f"Startup {index}",
            user_count=210 if index == 0 else 85,
            target_segment=MarketSegment.STARTUP,
            pricing_tier=PricingTier.STANDARD,
            feature_count=5,
        )
        for index in range(3)
    ]
    focused_products = [
        make_product(
            "Focused Core",
            user_count=210,
            target_segment=MarketSegment.STARTUP,
            pricing_tier=PricingTier.STANDARD,
            feature_count=5,
        ),
        make_product(
            "Ops",
            user_count=40,
            target_segment=MarketSegment.SMB,
            pricing_tier=PricingTier.PREMIUM,
        ),
    ]

    crowded_pressure = calculate_product_scale_pressure(
        crowded_products[0],
        crowded_products,
        headcount=2,
        current_turn=12,
    )
    focused_pressure = calculate_product_scale_pressure(
        focused_products[0],
        focused_products,
        headcount=5,
        current_turn=12,
    )
    crowded_company_pressure = calculate_company_scale_pressure(
        crowded_products,
        headcount=2,
        current_turn=12,
    )

    assert crowded_pressure.acquisition_penalty > focused_pressure.acquisition_penalty
    assert crowded_pressure.churn_modifier > focused_pressure.churn_modifier
    assert crowded_company_pressure.coordination_drag > 0


def test_campaign_goal_progress_completes_when_profit_machine_is_stable() -> None:
    state = make_state(
        make_product("Core", user_count=95, market_fit=70),
        cash_on_hand=Decimal("13200.00"),
        current_turn=9,
        campaign_goal_id=CampaignGoalId.PROFIT_MACHINE,
        finance=FinanceState(debt_principal=Decimal("3200.00")),
    )
    state.turn_history = [
        TurnLedgerEntry(
            turn=6,
            total_revenue=Decimal("1900.00"),
            total_operating_cost=Decimal("1500.00"),
            net_cash_flow=Decimal("400.00"),
            cash_on_hand=Decimal("11100.00"),
            reputation=58,
            total_users=90,
            headcount=0,
            roadmap_focus=RoadmapFocus.BALANCED_EXECUTION,
        ),
        TurnLedgerEntry(
            turn=7,
            total_revenue=Decimal("2100.00"),
            total_operating_cost=Decimal("1600.00"),
            net_cash_flow=Decimal("500.00"),
            cash_on_hand=Decimal("11600.00"),
            reputation=59,
            total_users=94,
            headcount=0,
            roadmap_focus=RoadmapFocus.BALANCED_EXECUTION,
        ),
        TurnLedgerEntry(
            turn=8,
            total_revenue=Decimal("2250.00"),
            total_operating_cost=Decimal("1680.00"),
            net_cash_flow=Decimal("570.00"),
            cash_on_hand=Decimal("12170.00"),
            reputation=60,
            total_users=95,
            headcount=0,
            roadmap_focus=RoadmapFocus.BALANCED_EXECUTION,
        ),
    ]

    progress = evaluate_campaign_goal(state)

    assert progress.completed is True
    assert progress.title == "Profit Machine"


def test_late_game_summary_rises_for_concentrated_portfolio() -> None:
    flagship = make_product(
        "Shield",
        lifecycle_stage=LifecycleStage.MATURE,
        quality=67,
        bug_level=29,
        market_fit=64,
        technical_debt=37,
        user_count=300,
        feature_count=6,
        target_segment=MarketSegment.ENTERPRISE,
        pricing_tier=PricingTier.PREMIUM,
    )
    adjacent = make_product(
        "Pulse",
        lifecycle_stage=LifecycleStage.GROWTH,
        user_count=24,
        market_fit=48,
        technical_debt=22,
        target_segment=MarketSegment.SMB,
    )
    legacy = make_product(
        "Legacy",
        lifecycle_stage=LifecycleStage.MATURE,
        user_count=32,
        technical_debt=42,
        target_segment=MarketSegment.ENTERPRISE,
    )
    ops = make_product(
        "Ops",
        lifecycle_stage=LifecycleStage.MATURE,
        user_count=28,
        technical_debt=40,
        target_segment=MarketSegment.SMB,
    )

    summary = calculate_late_game_summary(
        [flagship, adjacent, legacy, ops],
        current_turn=12,
        headcount=7,
    )

    assert summary.total_risk > 0
    assert summary.concentration_risk > 0
    assert summary.renewal_risk > 0
    assert summary.org_drag > 0
    assert summary.product_risks


def test_apply_end_of_turn_late_game_reduces_users_on_risky_product() -> None:
    product = make_product(
        "Renewal OS",
        lifecycle_stage=LifecycleStage.MATURE,
        quality=60,
        bug_level=30,
        market_fit=35,
        technical_debt=40,
        user_count=190,
        feature_count=7,
        target_segment=MarketSegment.ENTERPRISE,
        pricing_tier=PricingTier.PREMIUM,
    )

    summary = apply_end_of_turn_late_game([product], current_turn=12, headcount=0)

    assert summary.total_risk > 0
    assert product.user_count == 184
    assert product.market_fit == 34


def test_new_milestones_unlock_for_debt_free_and_category_moat() -> None:
    state = make_state(
        make_product(
            "Moat",
            lifecycle_stage=LifecycleStage.MATURE,
            quality=74,
            market_fit=71,
            user_count=150,
        ),
        cash_on_hand=Decimal("12500.00"),
        current_turn=8,
        finance=FinanceState(debt_principal=Decimal("0.00")),
    )

    unlocked = resolve_new_milestones(state, unlocked_turn=8)
    unlocked_ids = {entry.milestone_id for entry in unlocked}

    assert MilestoneId.DEBT_FREE_OPERATOR in unlocked_ids
    assert MilestoneId.CATEGORY_MOAT in unlocked_ids


def test_new_milestones_unlock_for_capital_discipline_and_rival_resilience() -> None:
    state = make_state(
        make_product("Core", user_count=210),
        make_product("Expansion", user_count=42, target_segment=MarketSegment.SMB),
        cash_on_hand=Decimal("12600.00"),
        finance=FinanceState(
            debt_principal=Decimal("0.00"),
            equity_dilution=Decimal("0.0800"),
        ),
        competitors=[
            Competitor(
                name="Price Rival",
                focus_segment=MarketSegment.STARTUP,
                strength=68,
                aggression=70,
                pricing_tier=PricingTier.BUDGET,
            ),
            Competitor(
                name="Platform Rival",
                focus_segment=MarketSegment.ENTERPRISE,
                strength=72,
                aggression=55,
                pricing_tier=PricingTier.PREMIUM,
            ),
            Competitor(
                name="Channel Rival",
                focus_segment=MarketSegment.SMB,
                strength=64,
                aggression=60,
                pricing_tier=PricingTier.STANDARD,
            ),
        ],
    )
    state.company.reputation = 64

    unlocked = resolve_new_milestones(state, unlocked_turn=9)
    unlocked_ids = {entry.milestone_id for entry in unlocked}

    assert MilestoneId.CAPITAL_DISCIPLINE in unlocked_ids
    assert MilestoneId.RIVAL_RESILIENCE in unlocked_ids


def test_new_event_ids_are_registered() -> None:
    registry_ids = {definition.event_id for definition in get_event_registry()}

    assert "renewal_risk" in registry_ids
    assert "partner_offer" in registry_ids
    assert "talent_bidding_war" in registry_ids
    assert "platform_breakthrough" in registry_ids
    assert "loan_covenant" in registry_ids
    assert "down_round_pressure" in registry_ids
    assert "key_account_expansion" in registry_ids
    assert "security_audit" in registry_ids
    assert "enterprise_sales_cycle" in registry_ids
    assert "product_launch_window" in registry_ids
    assert "platform_outage" in registry_ids
    assert "competitor_acquisition" in registry_ids
    assert "regulatory_shift" in registry_ids


def test_archetype_competitor_adds_segment_pressure() -> None:
    product = make_product(
        "Core",
        target_segment=MarketSegment.STARTUP,
        pricing_tier=PricingTier.STANDARD,
    )
    plain = Competitor(
        name="Plain Rival",
        focus_segment=MarketSegment.STARTUP,
        strength=30,
        aggression=30,
        pricing_tier=PricingTier.STANDARD,
    )
    price_raider = plain.model_copy(update={"name": "Price Raider", "archetype_id": "price_raider"})

    plain_pressure = calculate_competitor_pressure(
        product,
        [plain],
        market_cycle=MarketCycle.STEADY,
        current_turn=6,
        roadmap_focus=RoadmapFocus.BALANCED_EXECUTION,
        roadmap_set_turn=1,
    )
    archetype_pressure = calculate_competitor_pressure(
        product,
        [price_raider],
        market_cycle=MarketCycle.STEADY,
        current_turn=6,
        roadmap_focus=RoadmapFocus.BALANCED_EXECUTION,
        roadmap_set_turn=1,
    )

    assert archetype_pressure > plain_pressure


def test_balance_comparison_returns_ranked_scenarios() -> None:
    comparison = run_balance_comparison(
        scenario_ids=["founder_journey", "technical_rebuild"],
        difficulty_mode=DifficultyMode.STANDARD,
        campaign_goal_id=CampaignGoalId.PROFIT_MACHINE,
        runs=1,
        turns=2,
        seed_base=20,
    )

    assert len(comparison.comparisons) == 2
    assert comparison.comparisons[0].average_score >= comparison.comparisons[1].average_score


def test_balance_audit_returns_actionable_result() -> None:
    audit = run_balance_audit(
        scenario_ids=["founder_journey"],
        campaign_goal_id=CampaignGoalId.PROFIT_MACHINE,
        runs=1,
        turns=2,
        seed_base=40,
    )

    assert audit.runs == 1
    assert audit.turns == 2
    assert isinstance(audit.findings, tuple)


def test_new_milestones_unlock_for_talent_and_platform_credibility() -> None:
    product = make_product(
        "Core",
        quality=74,
        technical_debt=10,
        user_count=90,
    )
    employees = [
        make_employee("A", EmployeeRole.ENGINEER, morale=74),
        make_employee("B", EmployeeRole.DESIGNER, morale=72),
        make_employee("C", EmployeeRole.MARKETER, morale=71),
        make_employee("D", EmployeeRole.PRODUCT_MANAGER, morale=70),
        make_employee("E", EmployeeRole.ENGINEER, morale=73),
        make_employee("F", EmployeeRole.MARKETER, morale=75),
    ]
    state = make_state(product, employees=employees, current_turn=8)

    unlocked = resolve_new_milestones(state, unlocked_turn=8)
    unlocked_ids = {entry.milestone_id for entry in unlocked}

    assert MilestoneId.TALENT_BENCH in unlocked_ids
    assert MilestoneId.PLATFORM_CREDIBILITY in unlocked_ids


def test_balance_matrix_returns_all_difficulty_cells() -> None:
    matrix = run_balance_matrix(
        scenario_ids=["founder_journey", "technical_rebuild"],
        campaign_goal_id=CampaignGoalId.PROFIT_MACHINE,
        runs=1,
        turns=2,
        seed_base=30,
    )

    assert len(matrix.cells) == 6
    assert {cell.difficulty_mode for cell in matrix.cells} == set(DifficultyMode)
