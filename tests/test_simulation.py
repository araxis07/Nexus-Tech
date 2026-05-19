from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest

from nexus_tech.config import DEFAULT_COMPANY_NAME, DEFAULT_PRODUCT_NAME
from nexus_tech.domain.models import (
    BoardAsk,
    BoardResolution,
    BudgetStance,
    CampaignGoalId,
    CandidateTrait,
    CapitalPlan,
    CapitalPlanMode,
    CapitalSourcePreference,
    Company,
    CompanyStrategy,
    Competitor,
    CompetitorMove,
    ContractBillingModel,
    ContractCadence,
    CustomerAccount,
    CustomerAccountStatus,
    DifficultyMode,
    Employee,
    EmployeeRole,
    EventCategory,
    EventHistoryEntry,
    EventOption,
    ExitOutcome,
    FinanceState,
    FunctionalBudget,
    FunctionalBudgetPreset,
    GameState,
    HiringCandidateStage,
    LifecycleStage,
    MarketCycle,
    MarketSegment,
    MilestoneEntry,
    MilestoneId,
    PackagingStrategy,
    PartnerChannel,
    PartnershipDeal,
    PartnershipStatus,
    PendingEvent,
    PricingTier,
    Product,
    ProductReleaseStatus,
    ProductReleaseType,
    RenewalOfferType,
    RoadmapFocus,
    RoadmapProjectStatus,
    RoadmapProjectType,
    SalesDealStage,
    ScenarioObjectiveMetric,
    Seniority,
    SubscriptionPackage,
    SupportInvestmentFocus,
    SupportLaneFocus,
    SupportProgram,
    SupportTier,
    TurnAction,
    TurnLedgerEntry,
)
from nexus_tech.persistence.save_coordinator import RunArchiveSummary
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.balance_lab import (
    calculate_cash_warning_threshold,
    format_balance_matrix_csv,
    format_balance_report_markdown,
    run_balance_audit,
    run_balance_batch,
    run_balance_comparison,
    run_balance_matrix,
)
from nexus_tech.simulation.campaign import evaluate_campaign_goal
from nexus_tech.simulation.competition import advance_competitors, calculate_competitor_pressure
from nexus_tech.simulation.competitor_intel import record_competitor_intel
from nexus_tech.simulation.contracts import calculate_account_recurring_revenue
from nexus_tech.simulation.customers import (
    apply_end_of_turn_customers,
    calculate_account_revenue,
)
from nexus_tech.simulation.economy import (
    calculate_total_operating_cost,
    calculate_total_revenue,
    calculate_total_salary_cost,
)
from nexus_tech.simulation.employee_progression import apply_end_of_turn_employee_progression
from nexus_tech.simulation.endgame import (
    apply_exit_outcome,
    calculate_endgame_pressure,
    calculate_endgame_readiness,
    evaluate_exit_outcome,
)
from nexus_tech.simulation.engine import ActionContext, apply_action, create_new_game, resolve_turn
from nexus_tech.simulation.event_registry import EventDefinition, get_event_registry
from nexus_tech.simulation.events import (
    get_eligible_event_definitions,
    resolve_pending_event,
    select_event_definition,
    select_weighted_definition,
)
from nexus_tech.simulation.finance import (
    apply_end_of_turn_finance_drift,
    build_finance_planner,
    calculate_cash_flow_forecast_scenarios,
)
from nexus_tech.simulation.governance import (
    apply_end_of_turn_governance,
    get_governance_tradeoff_focus,
)
from nexus_tech.simulation.growth import (
    calculate_acquired_users,
    calculate_churned_users,
    calculate_effective_churn_rate_for_context,
)
from nexus_tech.simulation.hiring import generate_candidate_pool
from nexus_tech.simulation.hiring_pipeline import (
    interview_candidate,
    make_hiring_offer,
    screen_candidate,
    source_candidates,
)
from nexus_tech.simulation.late_game import (
    apply_end_of_turn_late_game,
    calculate_late_game_summary,
)
from nexus_tech.simulation.meta_progression import (
    build_archive_comparison,
    build_unlock_catalog,
    is_reward_unlocked,
    summarize_meta_progression,
)
from nexus_tech.simulation.milestones import resolve_new_milestones
from nexus_tech.simulation.objectives import evaluate_scenario_objective
from nexus_tech.simulation.operations import calculate_operations_summary
from nexus_tech.simulation.partnerships import (
    apply_end_of_turn_partnerships,
    calculate_partnership_fatigue,
    calculate_partnership_portfolio,
)
from nexus_tech.simulation.planning import build_quarter_plan, is_quarter_plan_due
from nexus_tech.simulation.pricing import (
    calculate_effective_revenue_per_user,
    determine_target_subscription_package,
)
from nexus_tech.simulation.product_progression import calculate_delivery_penalty
from nexus_tech.simulation.randomness import RandomSource
from nexus_tech.simulation.releases import plan_product_release, work_product_release
from nexus_tech.simulation.reporting import calculate_run_badges, calculate_run_score
from nexus_tech.simulation.roadmap import get_roadmap_profile
from nexus_tech.simulation.roadmap_projects import (
    start_roadmap_project,
    work_roadmap_project,
)
from nexus_tech.simulation.sales import advance_sales_deal, create_sales_deal
from nexus_tech.simulation.scaling import (
    calculate_company_scale_pressure,
    calculate_product_scale_pressure,
)
from nexus_tech.simulation.support_program import (
    apply_end_of_turn_support_program,
    calculate_support_account_risk_counts,
    calculate_support_account_risk_values,
    calculate_support_lane_snapshots,
    calculate_support_lane_staffing_plan,
    calculate_support_staff_capacity,
    classify_account_support_lane,
    triage_support_backlog,
)
from nexus_tech.simulation.team import (
    calculate_base_productivity,
    calculate_effective_productivity,
    calculate_product_team_modifier,
    calculate_salary,
    calculate_team_condition,
    calculate_trait_productivity,
    calculate_trait_salary,
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
    packaging_strategy: PackagingStrategy = PackagingStrategy.STREAMLINED,
    package_catalog_depth: int = 0,
    add_on_catalog_depth: int = 0,
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
        packaging_strategy=packaging_strategy,
        package_catalog_depth=package_catalog_depth,
        add_on_catalog_depth=add_on_catalog_depth,
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
    leadership_score: int = 55,
    assigned_product_id: UUID | None = None,
    manager_id: UUID | None = None,
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
        leadership_score=leadership_score,
        assigned_product_id=assigned_product_id,
        manager_id=manager_id,
    )


def make_state(
    *products: Product,
    employees: list[Employee] | None = None,
    competitors: list[Competitor] | None = None,
    finance: FinanceState | None = None,
    partnerships: list[PartnershipDeal] | None = None,
    capital_plan: CapitalPlan | None = None,
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
    functional_budget: FunctionalBudget | None = None,
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
        partnerships=partnerships or [],
        capital_plan=capital_plan or CapitalPlan(),
        functional_budget=functional_budget or FunctionalBudget(),
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

    assert revenue == Decimal("955.00")


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

    assert resolution.customer_summary.account_revenue == Decimal("555.00")
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


def test_new_roadmap_initiatives_have_distinct_profiles() -> None:
    trust_profile = get_roadmap_profile(
        RoadmapFocus.AI_TRUST_PROGRAM,
        roadmap_set_turn=1,
        current_turn=1,
    )
    community_profile = get_roadmap_profile(
        RoadmapFocus.COMMUNITY_GROWTH,
        roadmap_set_turn=1,
        current_turn=1,
    )
    enterprise_profile = get_roadmap_profile(
        RoadmapFocus.ENTERPRISE_SALES_PUSH,
        roadmap_set_turn=1,
        current_turn=1,
    )

    assert trust_profile.reputation_bonus > 0
    assert community_profile.acquisition_bonus > trust_profile.acquisition_bonus
    assert enterprise_profile.market_fit_bonus > community_profile.market_fit_bonus


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


def test_candidate_pool_generation_is_seeded_and_role_valid() -> None:
    first_pool = generate_candidate_pool(RandomSource(seed=77), count=4)
    second_pool = generate_candidate_pool(RandomSource(seed=77), count=4)

    assert first_pool == second_pool
    assert len(first_pool) == 4
    assert all(candidate.role in set(EmployeeRole) for candidate in first_pool)


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


def test_create_new_game_applies_board_recovery_campaign_start() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="board_recovery_crucible",
    )

    assert state.company.current_turn == 8
    assert state.finance.active_board_ask is BoardAsk.RELIABILITY
    assert state.finance.board_resolution_due is True
    assert state.finance.board_recovery_turns_remaining >= 3
    assert state.support_program.backlog_queue >= 10
    assert state.customer_accounts


def test_create_new_game_applies_ipo_campaign_start() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="ipo_readiness_launchpad",
    )

    assert state.company.current_turn == 14
    assert state.finance.board_confidence >= 68
    assert state.capital_plan.source_preference is CapitalSourcePreference.ANGEL
    assert len(state.customer_accounts) >= 2


def test_create_new_game_applies_acquisition_diligence_campaign_start() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="acquisition_diligence_sprint",
    )

    assert state.company.current_turn == 15
    assert state.capital_plan.source_preference is CapitalSourcePreference.VENTURE
    assert state.support_program.backlog_queue >= 11
    assert len(state.customer_accounts) >= 2
    assert len(state.partnerships) >= 2


def test_create_new_game_applies_independence_compounder_campaign_start() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="independence_compounder",
    )

    assert state.company.current_turn == 16
    assert state.capital_plan.source_preference is CapitalSourcePreference.BOOTSTRAP
    assert state.capital_plan.reserve_share >= 42
    assert state.finance.board_confidence >= 70
    assert len(state.customer_accounts) >= 1


def test_resolve_turn_surfaces_commercial_pressure_from_support_and_channel_risk() -> None:
    state = create_new_game(DEFAULT_COMPANY_NAME, DEFAULT_PRODUCT_NAME)
    state.company.current_turn = 7
    state.customer_accounts.append(
        CustomerAccount(
            name="Enterprise Anchor",
            product_id=state.products[0].id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("1600.00"),
            plan_tier=PricingTier.PREMIUM,
            support_tier=SupportTier.WHITE_GLOVE,
            contract_cadence=ContractCadence.ANNUAL,
            billing_model=ContractBillingModel.FLAT,
            satisfaction=58,
            onboarding_health=48,
            support_load=42,
            open_tickets=18,
            sla_breach_risk=82,
            invoice_risk=18,
            failed_payment_risk=14,
            ticket_queue_age=4,
            expansion_potential=60,
            renewal_health=46,
            renewal_turn=8,
            churn_risk=44,
            status=CustomerAccountStatus.ACTIVE,
        )
    )
    state.partnerships.append(
        PartnershipDeal(
            name="Dependence Lane",
            product_id=state.products[0].id,
            channel=PartnerChannel.RESELLER,
            status=PartnershipStatus.PAUSED,
            quality=56,
            risk=62,
            conflict_pressure=58,
            enablement_level=28,
            sourced_revenue=Decimal("2400.00"),
            sourced_users=34,
        )
    )
    starting_board_pressure = state.finance.board_pressure

    resolution = resolve_turn(state, FixedRandom(0))

    assert resolution.commercial_pressure_summary != "Commercial pressure is under control."
    assert "revenue-critical accounts" in resolution.commercial_pressure_summary
    assert resolution.state.finance.board_pressure > starting_board_pressure
    assert resolution.state.finance.board_team_health_score <= state.finance.board_team_health_score
    assert any(
        account.name == "Enterprise Anchor" and account.status is CustomerAccountStatus.AT_RISK
        for account in resolution.state.customer_accounts
    )


def test_resolve_turn_commercial_pressure_hits_direct_channel_conflict() -> None:
    state = create_new_game(DEFAULT_COMPANY_NAME, DEFAULT_PRODUCT_NAME)
    for index in range(4):
        state.customer_accounts.append(
            CustomerAccount(
                name=f"Conflict Account {index}",
                product_id=state.products[0].id,
                segment=MarketSegment.ENTERPRISE if index < 2 else MarketSegment.SMB,
                contract_value=Decimal("1200.00"),
                satisfaction=66,
                onboarding_health=60,
                support_load=26,
                expansion_potential=60,
                renewal_turn=state.company.current_turn + 3,
                churn_risk=18,
                status=CustomerAccountStatus.ACTIVE,
            )
        )
    state.partnerships.append(
        PartnershipDeal(
            name="Direct Conflict Reseller",
            product_id=state.products[0].id,
            channel=PartnerChannel.RESELLER,
            status=PartnershipStatus.ACTIVE,
            quality=62,
            risk=28,
            enablement_level=34,
            conflict_pressure=28,
        )
    )
    starting_focus_score = state.finance.board_portfolio_focus_score

    resolution = resolve_turn(state, FixedRandom(0))

    assert "channel conflict" in resolution.commercial_pressure_summary
    assert resolution.state.finance.board_pressure > state.finance.board_pressure
    assert resolution.state.finance.board_portfolio_focus_score != starting_focus_score


def test_resolve_turn_commercial_pressure_applies_path_specific_scrutiny() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="ipo_readiness_launchpad",
    )
    anchor = state.customer_accounts[0]
    anchor.segment = MarketSegment.ENTERPRISE
    anchor.support_tier = SupportTier.WHITE_GLOVE
    anchor.contract_value = Decimal("3200.00")
    anchor.open_tickets = 18
    anchor.sla_breach_risk = 84
    anchor.ticket_queue_age = 5
    anchor.renewal_health = 44
    anchor.churn_risk = 40
    state.support_program.backlog_queue = max(state.support_program.backlog_queue, 18)
    state.support_program.escalation_queue = max(state.support_program.escalation_queue, 6)
    starting_governance_risk = state.finance.governance_risk
    starting_board_pressure = state.finance.board_pressure

    resolution = resolve_turn(state, FixedRandom(0))

    assert "public-market scrutiny" in resolution.commercial_pressure_summary
    assert resolution.state.finance.board_pressure > starting_board_pressure
    assert resolution.state.finance.governance_risk > starting_governance_risk


def test_long_run_late_game_progression_resolves_without_crashing() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="independence_compounder",
    )
    rng = RandomSource(seed=29)

    for _ in range(18):
        resolution = resolve_turn(state, rng)
        state = resolution.state
        if state.pending_event is not None:
            state = resolve_pending_event(state, state.pending_event.options[0].id).state
        if state.company.game_over or state.victory_achieved:
            break

    assert len(state.turn_history) >= 1
    assert state.company.current_turn >= 20 or state.victory_achieved or state.company.game_over
    assert state.company.cash_on_hand == state.company.cash_on_hand


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


def test_thirty_turn_long_run_simulation_remains_stable() -> None:
    products = [
        make_product(
            "Core Suite",
            lifecycle_stage=LifecycleStage.GROWTH,
            quality=62,
            bug_level=16,
            market_fit=56,
            technical_debt=24,
            user_count=38,
            revenue_per_user=Decimal("28.00"),
            maintenance_cost=Decimal("300.00"),
            acquisition_rate=Decimal("0.0320"),
            churn_rate=Decimal("0.0380"),
            pricing_tier=PricingTier.PREMIUM,
            packaging_strategy=PackagingStrategy.SUITE,
            target_segment=MarketSegment.ENTERPRISE,
        ),
        make_product(
            "Ops Edge",
            lifecycle_stage=LifecycleStage.GROWTH,
            quality=58,
            bug_level=18,
            market_fit=52,
            technical_debt=26,
            user_count=24,
            revenue_per_user=Decimal("22.00"),
            maintenance_cost=Decimal("240.00"),
            acquisition_rate=Decimal("0.0300"),
            churn_rate=Decimal("0.0400"),
            packaging_strategy=PackagingStrategy.MODULAR,
            target_segment=MarketSegment.SMB,
        ),
    ]
    manager = make_employee(
        "Mira Holt",
        EmployeeRole.PRODUCT_MANAGER,
        seniority=Seniority.SENIOR,
        assigned_product_id=products[0].id,
        leadership_score=80,
    )
    manager.is_team_lead = True
    employees = [
        manager,
        make_employee(
            "Dev Lin",
            EmployeeRole.ENGINEER,
            seniority=Seniority.SENIOR,
            assigned_product_id=products[0].id,
            manager_id=manager.id,
        ),
        make_employee(
            "June Park",
            EmployeeRole.MARKETER,
            assigned_product_id=products[1].id,
            manager_id=manager.id,
        ),
        make_employee(
            "Rae Ito",
            EmployeeRole.DESIGNER,
            assigned_product_id=products[1].id,
            manager_id=manager.id,
        ),
    ]
    state = make_state(
        *products,
        employees=employees,
        cash_on_hand=Decimal("45000.00"),
        current_turn=1,
        market_cycle=MarketCycle.EXPANDING,
        market_cycle_turns_remaining=3,
        campaign_goal_id=CampaignGoalId.PORTFOLIO_EMPIRE,
    )
    state.finance.debt_principal = Decimal("6500.00")
    state.finance.investor_pressure = 18
    rng = RandomSource(seed=73)

    for _ in range(30):
        resolution = resolve_turn(state, rng)
        state = resolution.state
        if state.pending_event is not None:
            state = resolve_pending_event(state, state.pending_event.options[0].id).state
        if state.company.game_over:
            break

    assert state.company.current_turn >= 20
    assert len(state.turn_history) >= 19
    assert state.turn_history[-1].cash_on_hand == state.company.cash_on_hand


def test_long_run_regression_stays_coherent_through_extended_play() -> None:
    products = [
        make_product(
            "Core Platform",
            lifecycle_stage=LifecycleStage.MATURE,
            quality=74,
            bug_level=10,
            market_fit=70,
            technical_debt=18,
            user_count=160,
            revenue_per_user=Decimal("34.00"),
        ),
        make_product(
            "Ops Cloud",
            lifecycle_stage=LifecycleStage.GROWTH,
            quality=66,
            bug_level=14,
            market_fit=62,
            technical_debt=20,
            user_count=96,
            revenue_per_user=Decimal("28.00"),
        ),
    ]
    manager = make_employee(
        "June Park",
        EmployeeRole.PRODUCT_MANAGER,
        seniority=Seniority.SENIOR,
        salary=Decimal("1180.00"),
        productivity=72,
        leadership_score=72,
        assigned_product_id=products[0].id,
    )
    employees = [
        manager,
        make_employee(
            "Rin Costa",
            EmployeeRole.ENGINEER,
            assigned_product_id=products[0].id,
            manager_id=manager.id,
        ),
        make_employee(
            "Ari Vale",
            EmployeeRole.MARKETER,
            assigned_product_id=products[1].id,
            manager_id=manager.id,
        ),
        make_employee(
            "Lena Hart",
            EmployeeRole.DESIGNER,
            assigned_product_id=products[1].id,
            manager_id=manager.id,
        ),
    ]
    accounts = [
        CustomerAccount(
            name="Scale Anchor",
            product_id=products[0].id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("1800.00"),
            satisfaction=76,
            onboarding_health=72,
            support_load=24,
            expansion_potential=64,
            renewal_turn=8,
            churn_risk=10,
            status=CustomerAccountStatus.ACTIVE,
        ),
        CustomerAccount(
            name="Growth Team",
            product_id=products[1].id,
            segment=MarketSegment.SMB,
            contract_value=Decimal("820.00"),
            satisfaction=71,
            onboarding_health=70,
            support_load=18,
            expansion_potential=58,
            renewal_turn=7,
            churn_risk=12,
            status=CustomerAccountStatus.ACTIVE,
        ),
    ]
    state = make_state(
        *products,
        employees=employees,
        customer_accounts=accounts,
        cash_on_hand=Decimal("62000.00"),
        current_turn=1,
        market_cycle=MarketCycle.EXPANDING,
        market_cycle_turns_remaining=3,
        campaign_goal_id=CampaignGoalId.PORTFOLIO_EMPIRE,
    )
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.BALANCED,
        source_preference=CapitalSourcePreference.BOOTSTRAP,
        planning_horizon_turns=8,
        reserve_target=Decimal("8000.00"),
        product_investment_share=36,
        go_to_market_share=34,
        reserve_share=30,
    )
    rng = RandomSource(seed=133)

    for _ in range(60):
        resolution = resolve_turn(state, rng)
        state = resolution.state
        if state.pending_event is not None:
            state = resolve_pending_event(state, state.pending_event.options[0].id).state
        if state.company.game_over or state.victory_achieved:
            break

    assert state.company.current_turn >= 10
    assert len(state.turn_history) >= 9
    assert state.turn_history[-1].cash_on_hand == state.company.cash_on_hand
    assert state.turn_history[-1].headcount == len(state.employees)
    if state.victory_achieved:
        assert state.exit_outcome is not None


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


def test_event_chain_followup_becomes_eligible_after_related_history() -> None:
    product = make_product(
        "Regulated Core",
        target_segment=MarketSegment.ENTERPRISE,
        market_fit=62,
        technical_debt=36,
        user_count=58,
    )
    history_entry = EventHistoryEntry(
        event_id="security_audit",
        category=EventCategory.REPUTATION_INCIDENT,
        title="Security Audit",
        triggered_turn=5,
        resolved_turn=5,
        selected_option_id="fund_audit",
        selected_option_label="Fund audit",
        result_text="Audit funded.",
    )
    state = make_state(product, current_turn=7, event_history=[history_entry])

    eligible_ids = {definition.event_id for definition in get_eligible_event_definitions(state)}

    assert "audit_followup_review" in eligible_ids


def test_event_chain_followup_applies_evidence_tradeoff() -> None:
    product = make_product(
        "Regulated Core",
        target_segment=MarketSegment.ENTERPRISE,
        market_fit=62,
        technical_debt=36,
        user_count=58,
    )
    account = CustomerAccount(
        name="Enterprise Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("900.00"),
        satisfaction=66,
        expansion_potential=52,
        renewal_turn=8,
        churn_risk=22,
    )
    state = make_state(
        product,
        customer_accounts=[account],
        cash_on_hand=Decimal("9000.00"),
        current_turn=7,
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "audit_followup_review"
    )
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "package_evidence")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.products[0].technical_debt < state.products[0].technical_debt
    assert outcome.state.company.reputation > state.company.reputation
    assert outcome.state.customer_accounts[0].churn_risk < state.customer_accounts[0].churn_risk
    assert outcome.history_entry.event_id == "audit_followup_review"


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

    evaluation = apply_exit_outcome(resolution.state)

    assert evaluation.outcome in {
        ExitOutcome.PROFITABLE_INDEPENDENCE,
        ExitOutcome.STRATEGIC_ACQUISITION,
        ExitOutcome.IPO_READY,
    }
    assert evaluation.ending_variant
    assert evaluation.outcome_tags
    assert resolution.state.exit_summary


def test_take_loan_and_repay_debt_change_finance_state() -> None:
    state = make_state(make_product("Core"), cash_on_hand=Decimal("8000.00"))

    loan_outcome = apply_action(state, TurnAction.TAKE_LOAN)

    assert loan_outcome.state.finance.debt_principal == Decimal("2500.00")
    assert loan_outcome.state.company.cash_on_hand == Decimal("10500.00")

    repay_outcome = apply_action(loan_outcome.state, TurnAction.REPAY_DEBT)

    assert repay_outcome.state.finance.debt_principal == Decimal("700.00")
    assert repay_outcome.state.company.cash_on_hand == Decimal("8700.00")


def test_refinance_debt_trades_interest_for_covenant_relief() -> None:
    state = make_state(
        make_product("Refi Core"),
        cash_on_hand=Decimal("4200.00"),
        finance=FinanceState(
            debt_principal=Decimal("3400.00"),
            loan_interest_rate=Decimal("0.0300"),
            covenant_risk=26,
            board_confidence=62,
        ),
    )

    outcome = apply_action(state, TurnAction.REFINANCE_DEBT)

    assert outcome.state.company.cash_on_hand == Decimal("5400.00")
    assert outcome.state.finance.debt_principal == Decimal("4600.00")
    assert outcome.state.finance.loan_interest_rate > Decimal("0.0300")
    assert outcome.state.finance.covenant_risk < 26
    assert outcome.state.finance.board_confidence < 62


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
    assert "audit_followup_review" in registry_ids
    assert "launch_aftershock" in registry_ids
    assert "enterprise_procurement_delay" in registry_ids
    assert "support_meltdown" in registry_ids
    assert "board_reckoning" in registry_ids
    assert "partner_qbr" in registry_ids
    assert "partner_breakdown" in registry_ids
    assert "partner_renegotiation" in registry_ids
    assert "channel_concentration_crackdown" in registry_ids
    assert "board_recovery_window" in registry_ids
    assert "board_reset_showdown" in registry_ids
    assert "capital_market_freeze" in registry_ids
    assert "succession_gap" in registry_ids
    assert "strategic_crossroads" in registry_ids
    assert "public_market_scrutiny" in registry_ids
    assert "ipo_audit_committee" in registry_ids
    assert "ipo_reference_crack" in registry_ids
    assert "ipo_listing_window" in registry_ids
    assert "ipo_governance_lockstep" in registry_ids
    assert "ipo_syndicate_commitment" in registry_ids
    assert "ipo_pricing_committee" in registry_ids
    assert "ipo_reference_committee" in registry_ids
    assert "ipo_roadshow_lock" in registry_ids
    assert "ipo_bookbuild_corridor" in registry_ids
    assert "ipo_allocation_lock" in registry_ids
    assert "acquirer_diligence" in registry_ids
    assert "buyer_reference_check" in registry_ids
    assert "buyer_channel_conflict_review" in registry_ids
    assert "buyer_term_sheet" in registry_ids
    assert "buyer_synergy_map" in registry_ids
    assert "buyer_integration_blueprint" in registry_ids
    assert "buyer_operating_memo" in registry_ids
    assert "buyer_signing_committee" in registry_ids
    assert "buyer_close_readiness" in registry_ids
    assert "buyer_board_alignment" in registry_ids
    assert "buyer_close_cadence" in registry_ids
    assert "independence_reckoning" in registry_ids
    assert "independence_cash_crunch" in registry_ids
    assert "independence_refinancing_wall" in registry_ids
    assert "independence_profit_floor" in registry_ids
    assert "independence_operating_covenant" in registry_ids
    assert "independence_buffer_ratchet" in registry_ids
    assert "independence_cash_yield_pact" in registry_ids
    assert "independence_treasury_compact" in registry_ids
    assert "independence_cash_command" in registry_ids
    assert "independence_liquidity_charter" in registry_ids
    assert "independence_margin_charter" in registry_ids
    assert "reseller_enablement_gap" in registry_ids
    assert "reseller_reference_summit" in registry_ids
    assert "reseller_commitment_review" in registry_ids
    assert "reseller_margin_council" in registry_ids
    assert "reseller_pipeline_cadence" in registry_ids
    assert "reseller_recovery_compact" in registry_ids
    assert "integration_cutover_risk" in registry_ids
    assert "integration_cutover_board" in registry_ids
    assert "integration_release_cutline" in registry_ids
    assert "integration_support_bridge" in registry_ids
    assert "integration_go_live_shield" in registry_ids
    assert "integration_cutover_command" in registry_ids
    assert "marketplace_chargeback_wave" in registry_ids
    assert "marketplace_dispute_program" in registry_ids
    assert "marketplace_refund_charter" in registry_ids
    assert "marketplace_trust_reset" in registry_ids
    assert "marketplace_policy_appeal" in registry_ids
    assert "marketplace_penalty_panel" in registry_ids
    assert "board_reset_execution_plan" in registry_ids
    assert "board_reset_operating_cadence" in registry_ids
    assert "board_reset_governance_table" in registry_ids
    assert "board_reset_balance_sheet_treaty" in registry_ids
    assert "board_reset_trust_vote" in registry_ids
    assert "board_reset_cash_charter" in registry_ids


def test_board_reckoning_event_can_shift_capital_plan_to_conserve() -> None:
    product = make_product("Board Core")
    state = make_state(product, cash_on_hand=Decimal("6000.00"))
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.EXPAND,
        source_preference=CapitalSourcePreference.VENTURE,
        planning_horizon_turns=6,
        reserve_target=Decimal("4000.00"),
        product_investment_share=35,
        go_to_market_share=40,
        reserve_share=25,
    )
    state.pending_event = PendingEvent(
        event_id="board_reckoning",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Board Reckoning",
        description="Test event",
        triggered_turn=state.company.current_turn,
        cooldown_turns=5,
        options=[
            EventOption(id="reset_plan", label="Reset", description="Reset"),
            EventOption(id="defend_growth", label="Defend", description="Defend"),
        ],
    )

    outcome = resolve_pending_event(state, "reset_plan")

    assert outcome.state.capital_plan.mode is CapitalPlanMode.CONSERVE
    assert outcome.state.finance.board_resolution_due is False


def test_board_recovery_window_event_improves_governance_signals() -> None:
    product = make_product("Recovery Core")
    state = make_state(product, cash_on_hand=Decimal("7200.00"))
    state.finance.board_recovery_turns_remaining = 2
    state.finance.board_confidence = 48
    state.finance.board_score = 50
    state.finance.governance_risk = 24
    state.pending_event = PendingEvent(
        event_id="board_recovery_window",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Board Recovery Window",
        description="Test event",
        triggered_turn=state.company.current_turn,
        cooldown_turns=5,
        options=[
            EventOption(id="fund_control_room", label="Fund", description="Fund"),
            EventOption(id="narrow_scope", label="Narrow", description="Narrow"),
        ],
    )

    outcome = resolve_pending_event(state, "fund_control_room")

    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.governance_risk < state.finance.governance_risk


def test_board_reset_showdown_event_can_accept_reset_plan() -> None:
    product = make_product("Reset Showdown Core")
    state = make_state(product, cash_on_hand=Decimal("6400.00"), current_turn=16)
    state.finance.board_pressure = 34
    state.finance.governance_risk = 28
    state.finance.restructuring_pressure = 18
    state.finance.governance_crisis_level = 2
    state.finance.governance_crisis_active = True
    state.finance.board_warning_level = 3
    state.finance.board_resolution_due = True
    state.support_program.backlog_queue = 18
    state.support_program.escalation_queue = 6
    state.event_history.append(
        EventHistoryEntry(
            event_id="board_recovery_window",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Board Recovery Window",
            triggered_turn=15,
            resolved_turn=15,
            selected_option_id="fund_control_room",
            selected_option_label="Fund control room",
            result_text="Governance optics improved.",
        )
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "board_reset_showdown"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "accept_reset_plan")

    assert outcome.state.capital_plan.mode is CapitalPlanMode.CONSERVE
    assert outcome.state.capital_plan.reserve_share > state.capital_plan.reserve_share
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.history_entry.event_id == "board_reset_showdown"


def test_board_reset_execution_plan_event_can_codify_reset() -> None:
    product = make_product("Reset Execution Core")
    state = make_state(product, cash_on_hand=Decimal("6200.00"), current_turn=17)
    state.finance.board_pressure = 35
    state.finance.governance_risk = 30
    state.finance.restructuring_pressure = 22
    state.finance.governance_crisis_level = 2
    state.finance.governance_crisis_active = True
    state.finance.board_warning_level = 3
    state.finance.board_resolution_due = True
    state.finance.board_confidence = 34
    state.company.reputation = 68
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.BALANCED,
        source_preference=CapitalSourcePreference.DEBT,
        planning_horizon_turns=6,
        reserve_target=Decimal("4200.00"),
        product_investment_share=36,
        go_to_market_share=40,
        reserve_share=24,
    )
    state.event_history.append(
        EventHistoryEntry(
            event_id="board_reset_showdown",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Board Reset Showdown",
            triggered_turn=16,
            resolved_turn=16,
            selected_option_id="accept_reset_plan",
            selected_option_label="Accept the reset plan",
            result_text="Reset plan accepted.",
        )
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "board_reset_execution_plan"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "codify_operating_reset")

    assert outcome.state.capital_plan.mode is CapitalPlanMode.CONSERVE
    assert outcome.state.capital_plan.reserve_share > state.capital_plan.reserve_share
    assert outcome.state.capital_plan.go_to_market_share < state.capital_plan.go_to_market_share
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.governance_risk < state.finance.governance_risk
    assert outcome.state.finance.board_resolution_due is False
    assert outcome.state.finance.board_warning_level < state.finance.board_warning_level
    assert outcome.history_entry.event_id == "board_reset_execution_plan"


def test_board_reset_operating_cadence_event_can_install_reset_cadence() -> None:
    product = make_product("Reset Cadence Core")
    state = make_state(product, cash_on_hand=Decimal("6400.00"), current_turn=18)
    state.finance.board_pressure = 36
    state.finance.governance_risk = 32
    state.finance.restructuring_pressure = 26
    state.finance.governance_crisis_level = 2
    state.finance.governance_crisis_active = True
    state.finance.board_warning_level = 3
    state.finance.board_resolution_due = True
    state.finance.board_confidence = 34
    state.finance.board_score = 38
    state.company.reputation = 68
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.BALANCED,
        source_preference=CapitalSourcePreference.DEBT,
        planning_horizon_turns=6,
        reserve_target=Decimal("4300.00"),
        product_investment_share=36,
        go_to_market_share=40,
        reserve_share=24,
    )
    state.event_history.append(
        EventHistoryEntry(
            event_id="board_reset_execution_plan",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Board Reset Execution Plan",
            triggered_turn=17,
            resolved_turn=17,
            selected_option_id="codify_operating_reset",
            selected_option_label="Codify the operating reset",
            result_text="Reset execution codified.",
        )
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "board_reset_operating_cadence"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "install_reset_cadence")

    assert outcome.state.capital_plan.mode is CapitalPlanMode.CONSERVE
    assert outcome.state.capital_plan.reserve_share > state.capital_plan.reserve_share
    assert outcome.state.capital_plan.go_to_market_share < state.capital_plan.go_to_market_share
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.governance_risk < state.finance.governance_risk
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.board_resolution_due is False
    assert outcome.history_entry.event_id == "board_reset_operating_cadence"


def test_board_reset_governance_table_event_can_ratify_reset_table() -> None:
    product = make_product("Reset Governance Table Core")
    state = make_state(product, cash_on_hand=Decimal("6500.00"), current_turn=19)
    state.finance.board_pressure = 38
    state.finance.governance_risk = 34
    state.finance.restructuring_pressure = 28
    state.finance.governance_crisis_level = 3
    state.finance.governance_crisis_active = True
    state.finance.board_warning_level = 3
    state.finance.board_resolution_due = True
    state.finance.board_confidence = 34
    state.finance.board_score = 38
    state.company.reputation = 68
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.BALANCED,
        source_preference=CapitalSourcePreference.DEBT,
        planning_horizon_turns=6,
        reserve_target=Decimal("4300.00"),
        product_investment_share=36,
        go_to_market_share=40,
        reserve_share=24,
    )
    state.event_history.append(
        EventHistoryEntry(
            event_id="board_reset_operating_cadence",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Board Reset Operating Cadence",
            triggered_turn=18,
            resolved_turn=18,
            selected_option_id="install_reset_cadence",
            selected_option_label="Install the reset cadence",
            result_text="Reset cadence installed.",
        )
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "board_reset_governance_table"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "ratify_reset_table")

    assert outcome.state.capital_plan.mode is CapitalPlanMode.CONSERVE
    assert outcome.state.capital_plan.reserve_share > state.capital_plan.reserve_share
    assert outcome.state.capital_plan.go_to_market_share < state.capital_plan.go_to_market_share
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.governance_risk < state.finance.governance_risk
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.board_resolution_due is False
    assert outcome.history_entry.event_id == "board_reset_governance_table"


def test_board_reset_balance_sheet_treaty_event_can_ratify_treaty() -> None:
    product = make_product("Reset Balance Sheet Treaty Core")
    state = make_state(product, cash_on_hand=Decimal("6600.00"), current_turn=20)
    state.finance.board_pressure = 40
    state.finance.governance_risk = 36
    state.finance.restructuring_pressure = 30
    state.finance.governance_crisis_level = 3
    state.finance.governance_crisis_active = True
    state.finance.board_warning_level = 3
    state.finance.board_resolution_due = True
    state.finance.board_confidence = 34
    state.finance.board_score = 38
    state.company.reputation = 68
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.BALANCED,
        source_preference=CapitalSourcePreference.DEBT,
        planning_horizon_turns=6,
        reserve_target=Decimal("4300.00"),
        product_investment_share=36,
        go_to_market_share=40,
        reserve_share=24,
    )
    state.event_history.append(
        EventHistoryEntry(
            event_id="board_reset_governance_table",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Board Reset Governance Table",
            triggered_turn=19,
            resolved_turn=19,
            selected_option_id="ratify_reset_table",
            selected_option_label="Ratify the reset table",
            result_text="Reset table ratified.",
        )
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "board_reset_balance_sheet_treaty"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "ratify_balance_sheet_treaty")

    assert outcome.state.capital_plan.mode is CapitalPlanMode.CONSERVE
    assert outcome.state.capital_plan.reserve_share > state.capital_plan.reserve_share
    assert outcome.state.capital_plan.go_to_market_share < state.capital_plan.go_to_market_share
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.governance_risk < state.finance.governance_risk
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.board_resolution_due is False
    assert outcome.history_entry.event_id == "board_reset_balance_sheet_treaty"


def test_support_meltdown_event_can_trade_cash_for_queue_relief() -> None:
    product = make_product("Support Core")
    account = CustomerAccount(
        name="Escalated Account",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("1280.00"),
        satisfaction=62,
        expansion_potential=64,
        renewal_turn=8,
        churn_risk=26,
        support_tier=SupportTier.WHITE_GLOVE,
        open_tickets=14,
        sla_breach_risk=44,
        escalation_count=2,
        status=CustomerAccountStatus.ACTIVE,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("7000.00"))
    state.support_program.backlog_queue = 24
    state.support_program.escalation_queue = 5
    state.pending_event = PendingEvent(
        event_id="support_meltdown",
        category=EventCategory.PRODUCT_INCIDENT,
        title="Support Meltdown",
        description="Test event",
        triggered_turn=state.company.current_turn,
        cooldown_turns=5,
        target_product_id=product.id,
        options=[
            EventOption(id="staff_emergency", label="Staff", description="Staff"),
            EventOption(id="ration_support", label="Ration", description="Ration"),
        ],
    )

    outcome = resolve_pending_event(state, "staff_emergency")

    assert outcome.state.support_program.backlog_queue < state.support_program.backlog_queue
    assert outcome.state.support_program.staffing_level > state.support_program.staffing_level


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


def test_cash_warning_threshold_scales_with_audit_horizon() -> None:
    short_threshold = calculate_cash_warning_threshold(3)
    long_threshold = calculate_cash_warning_threshold(12)

    assert short_threshold == BALANCE.base_operating_cost
    assert long_threshold > short_threshold
    assert long_threshold <= BALANCE.finance_pressure_relief_cash_threshold / Decimal("2")


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


def test_scenario_objective_tracks_closed_sales_deals() -> None:
    product = make_product("Pipeline", target_segment=MarketSegment.ENTERPRISE, market_fit=74)
    state = make_state(
        product,
        cash_on_hand=Decimal("12000.00"),
    )
    state.scenario_objective = "Close one enterprise deal."
    state.scenario_objective_metric = ScenarioObjectiveMetric.CLOSED_DEALS
    state.scenario_objective_target = 1

    create_sales_deal(state, product)
    deal_id = state.sales_deals[0].id
    advance_sales_deal(state, deal_id)
    advance_sales_deal(state, deal_id)
    advance_sales_deal(state, deal_id)

    progress = evaluate_scenario_objective(state)

    assert progress.current_value == 1
    assert progress.complete


def test_release_plan_work_ships_stability_patch() -> None:
    product = make_product("Stable", quality=55, bug_level=30, technical_debt=36)
    state = make_state(product, cash_on_hand=Decimal("9000.00"))

    plan_product_release(state, product, ProductReleaseType.STABILITY_PATCH)
    release_id = state.product_releases[0].id
    work_product_release(state, release_id)
    work_product_release(state, release_id)

    release = state.product_releases[0]

    assert release.status is ProductReleaseStatus.SHIPPED
    assert product.bug_level < 30
    assert product.technical_debt < 36


def test_sales_deal_close_creates_customer_account() -> None:
    product = make_product(
        "Enterprise Desk",
        target_segment=MarketSegment.ENTERPRISE,
        market_fit=80,
        quality=78,
    )
    state = make_state(product, cash_on_hand=Decimal("12000.00"))

    create_sales_deal(state, product)
    deal = state.sales_deals[0]
    advance_sales_deal(state, deal.id)
    advance_sales_deal(state, deal.id)
    advance_sales_deal(state, deal.id)

    assert deal.stage is SalesDealStage.CLOSED_WON
    assert len(state.customer_accounts) == 1
    assert state.customer_accounts[0].product_id == product.id


def test_roadmap_project_completion_improves_target_product() -> None:
    product = make_product("Debt Box", quality=50, bug_level=30, technical_debt=60)
    employee = make_employee(
        "PM",
        EmployeeRole.PRODUCT_MANAGER,
        assigned_product_id=product.id,
    )
    state = make_state(product, employees=[employee], cash_on_hand=Decimal("10000.00"))

    start_roadmap_project(state, RoadmapProjectType.PLATFORM_REBUILD, product.id)
    project_id = state.roadmap_projects[0].id
    work_roadmap_project(state, project_id)
    work_roadmap_project(state, project_id)

    project = state.roadmap_projects[0]

    assert project.status is RoadmapProjectStatus.COMPLETED
    assert product.technical_debt < 60
    assert product.bug_level < 30


def test_candidate_trait_changes_salary_and_productivity() -> None:
    base_salary = calculate_salary(EmployeeRole.ENGINEER, Seniority.SENIOR)
    base_productivity = calculate_base_productivity(EmployeeRole.ENGINEER, Seniority.SENIOR)

    expert_salary = calculate_trait_salary(base_salary, CandidateTrait.EXPENSIVE_EXPERT)
    expert_productivity = calculate_trait_productivity(
        base_productivity,
        CandidateTrait.EXPENSIVE_EXPERT,
    )

    assert expert_salary > base_salary
    assert expert_productivity > base_productivity


def test_competitor_intel_records_changed_move() -> None:
    competitor = Competitor(
        name="Velocity",
        focus_segment=MarketSegment.STARTUP,
        strength=60,
        aggression=60,
        pricing_tier=PricingTier.STANDARD,
        current_move=CompetitorMove.HOLD,
    )
    state = make_state(make_product("Core"), competitors=[competitor])
    previous_competitors = [competitor.model_copy(deep=True)]
    state.competitors[0].current_move = CompetitorMove.FEATURE_SPRINT

    record_competitor_intel(state, previous_competitors, current_turn=3)

    assert state.competitor_intel
    assert state.competitor_intel[0].move is CompetitorMove.FEATURE_SPRINT


def test_account_revenue_applies_discount_rate() -> None:
    product = make_product("Enterprise Desk")
    account = CustomerAccount(
        name="Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("1000.00"),
        contract_cadence=ContractCadence.ANNUAL,
        discount_rate=Decimal("0.1000"),
        satisfaction=70,
        onboarding_health=72,
        support_load=18,
        expansion_potential=58,
        renewal_turn=5,
        churn_risk=16,
    )

    assert calculate_account_revenue([account]) == Decimal("949.50")


def test_seat_based_account_revenue_includes_contract_commitment() -> None:
    product = make_product("Enterprise Desk")
    account = CustomerAccount(
        name="Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("1000.00"),
        contract_cadence=ContractCadence.ANNUAL,
        billing_model=ContractBillingModel.SEAT_BASED,
        seat_count=20,
        discount_rate=Decimal("0.1000"),
        satisfaction=70,
        onboarding_health=72,
        support_load=18,
        expansion_potential=58,
        renewal_turn=5,
        churn_risk=16,
    )

    assert calculate_account_revenue([account]) == Decimal("1273.50")


def test_customer_turn_tracks_support_backlog_and_sla_pressure() -> None:
    product = make_product("Support Cloud", quality=44, bug_level=36, market_fit=52)
    account = CustomerAccount(
        name="Support Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("900.00"),
        contract_cadence=ContractCadence.ANNUAL,
        billing_model=ContractBillingModel.SEAT_BASED,
        seat_count=18,
        satisfaction=58,
        onboarding_health=50,
        support_load=34,
        open_tickets=10,
        sla_breach_risk=54,
        expansion_potential=62,
        renewal_turn=6,
        churn_risk=38,
    )

    summary = apply_end_of_turn_customers(
        [account],
        [product],
        current_turn=3,
        customer_success_bonus=0,
    )

    assert summary.total_open_tickets > 0
    assert summary.sla_risk_accounts >= 1
    assert account.open_tickets >= 10
    assert account.sla_breach_risk >= 48


def test_customer_success_action_reduces_risk_and_support_load() -> None:
    product = make_product("Renewal Hub")
    account = CustomerAccount(
        name="Renewal Anchor",
        product_id=product.id,
        segment=MarketSegment.STARTUP,
        contract_value=Decimal("700.00"),
        contract_cadence=ContractCadence.MONTHLY,
        discount_rate=Decimal("0.0000"),
        satisfaction=55,
        onboarding_health=52,
        support_load=38,
        expansion_potential=50,
        renewal_turn=3,
        churn_risk=58,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("5000.00"))

    outcome = apply_action(
        state,
        TurnAction.INVEST_IN_CUSTOMER_SUCCESS,
        ActionContext(target_product_id=product.id),
    )

    updated_account = outcome.state.customer_accounts[0]
    assert updated_account.churn_risk < account.churn_risk
    assert updated_account.support_load < account.support_load
    assert updated_account.open_tickets <= account.open_tickets
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_retention_play_adds_discount_and_restores_account_health() -> None:
    product = make_product("Renewal Hub")
    account = CustomerAccount(
        name="Renewal Anchor",
        product_id=product.id,
        segment=MarketSegment.STARTUP,
        contract_value=Decimal("700.00"),
        contract_cadence=ContractCadence.MONTHLY,
        discount_rate=Decimal("0.0000"),
        satisfaction=49,
        onboarding_health=48,
        support_load=36,
        expansion_potential=50,
        renewal_turn=3,
        churn_risk=64,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("5000.00"))

    outcome = apply_action(
        state,
        TurnAction.RUN_RETENTION_PLAY,
        ActionContext(customer_account_id=account.id),
    )

    updated_account = outcome.state.customer_accounts[0]
    assert updated_account.discount_rate > account.discount_rate
    assert updated_account.churn_risk < account.churn_risk
    assert updated_account.satisfaction > account.satisfaction


def test_train_employee_increases_readiness_and_productivity() -> None:
    product = make_product("Core")
    employee = make_employee("Ada", EmployeeRole.ENGINEER, assigned_product_id=product.id)
    state = make_state(product, employees=[employee], cash_on_hand=Decimal("5000.00"))

    outcome = apply_action(
        state,
        TurnAction.TRAIN_EMPLOYEE,
        ActionContext(employee_id=employee.id),
    )

    updated_employee = outcome.state.employees[0]
    assert updated_employee.promotion_readiness > employee.promotion_readiness
    assert updated_employee.productivity > employee.productivity
    assert updated_employee.performance_rating > employee.performance_rating
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_promote_employee_advances_seniority_and_salary() -> None:
    product = make_product("Core")
    employee = make_employee(
        "Ada",
        EmployeeRole.ENGINEER,
        seniority=Seniority.JUNIOR,
        assigned_product_id=product.id,
    )
    employee.promotion_readiness = 76
    state = make_state(product, employees=[employee])

    outcome = apply_action(
        state,
        TurnAction.PROMOTE_EMPLOYEE,
        ActionContext(employee_id=employee.id),
    )

    updated_employee = outcome.state.employees[0]
    assert updated_employee.seniority is Seniority.MID
    assert updated_employee.salary > employee.salary
    assert updated_employee.productivity > employee.productivity
    assert updated_employee.leadership_score > employee.leadership_score


def test_comp_review_action_raises_salary_and_reduces_attrition() -> None:
    product = make_product("Core")
    employee = make_employee(
        "Ada",
        EmployeeRole.ENGINEER,
        seniority=Seniority.MID,
        salary=Decimal("620.00"),
        assigned_product_id=product.id,
    )
    employee.attrition_risk = 42
    employee.performance_rating = 76
    state = make_state(product, employees=[employee], cash_on_hand=Decimal("5000.00"))

    outcome = apply_action(
        state,
        TurnAction.RUN_COMP_REVIEW,
        ActionContext(employee_id=employee.id),
    )

    updated_employee = outcome.state.employees[0]
    assert updated_employee.salary > employee.salary
    assert updated_employee.attrition_risk < employee.attrition_risk
    assert updated_employee.performance_rating >= employee.performance_rating


def test_comp_review_relieves_succession_risk_for_manager() -> None:
    product = make_product("Ops Grid")
    manager = make_employee(
        "June",
        EmployeeRole.PRODUCT_MANAGER,
        seniority=Seniority.SENIOR,
        salary=Decimal("1180.00"),
        assigned_product_id=product.id,
        leadership_score=70,
    )
    manager.succession_risk = 16
    state = make_state(product, employees=[manager], cash_on_hand=Decimal("6400.00"))

    outcome = apply_action(
        state,
        TurnAction.RUN_COMP_REVIEW,
        ActionContext(employee_id=manager.id),
    )

    updated_manager = outcome.state.employees[0]
    assert updated_manager.salary > manager.salary
    assert updated_manager.succession_risk < manager.succession_risk


def test_succession_review_action_can_designate_backup_lead() -> None:
    product = make_product("Core")
    manager = make_employee(
        "June",
        EmployeeRole.PRODUCT_MANAGER,
        seniority=Seniority.SENIOR,
        salary=Decimal("1180.00"),
        assigned_product_id=product.id,
        leadership_score=64,
    )
    report_a = make_employee(
        "Kai",
        EmployeeRole.ENGINEER,
        assigned_product_id=product.id,
        manager_id=manager.id,
        leadership_score=58,
    )
    report_b = make_employee(
        "Nia",
        EmployeeRole.DESIGNER,
        assigned_product_id=product.id,
        manager_id=manager.id,
        leadership_score=56,
    )
    state = make_state(
        product,
        employees=[manager, report_a, report_b],
        cash_on_hand=Decimal("5200.00"),
    )

    outcome = apply_action(
        state,
        TurnAction.RUN_SUCCESSION_REVIEW,
        ActionContext(employee_id=manager.id),
    )

    updated_manager = next(
        employee for employee in outcome.state.employees if employee.id == manager.id
    )
    backup = next(
        employee
        for employee in outcome.state.employees
        if employee.id != manager.id and employee.is_team_lead
    )
    backup_count = sum(1 for employee in outcome.state.employees if employee.is_team_lead)
    assert updated_manager.leadership_score > manager.leadership_score
    assert backup_count >= 1
    assert backup.promotion_readiness > 0
    assert backup.performance_rating >= report_a.performance_rating
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_employee_progression_adds_career_pressure_for_ready_under_market_staff() -> None:
    employee = make_employee(
        "Terry",
        EmployeeRole.ENGINEER,
        seniority=Seniority.MID,
        salary=Decimal("700.00"),
        productivity=72,
    )
    employee.promotion_readiness = 76
    employee.performance_rating = 78
    employee.tenure_turns = 5

    summary = apply_end_of_turn_employee_progression(
        [employee],
        net_cash_flow=Decimal("200.00"),
    )

    assert summary.high_attrition_risk_count == 0 or employee.attrition_risk > 0
    assert employee.attrition_risk >= BALANCE.employee_promotion_pressure_attrition_gain


def test_employee_progression_adds_org_gap_pressure_for_unmanaged_team() -> None:
    product = make_product("Org Debt")
    employees = [
        make_employee(
            f"Builder {index}",
            EmployeeRole.ENGINEER,
            assigned_product_id=product.id,
            energy=60,
            morale=60,
        )
        for index in range(1, 6)
    ]

    apply_end_of_turn_employee_progression(
        employees,
        net_cash_flow=Decimal("200.00"),
    )

    assert all(
        employee.attrition_risk >= BALANCE.management_unmanaged_attrition_gain
        for employee in employees
    )
    assert any(employee.morale < 60 for employee in employees)


def test_low_performance_reduces_effective_productivity() -> None:
    employee = make_employee("Ada", EmployeeRole.ENGINEER, productivity=72)
    employee.performance_rating = 30
    weak_productivity = calculate_effective_productivity(employee)

    employee.performance_rating = 78
    strong_productivity = calculate_effective_productivity(employee)

    assert strong_productivity > weak_productivity


def test_extreme_attrition_can_cause_resignation_on_turn_resolution() -> None:
    product = make_product("Core")
    employee = make_employee("Ada", EmployeeRole.ENGINEER, assigned_product_id=product.id)
    employee.attrition_risk = 95
    employee.morale = 20
    employee.energy = 20
    employee.performance_rating = 32
    employee.underperformance_streak = 3
    state = make_state(product, employees=[employee], cash_on_hand=Decimal("9000.00"))

    resolution = resolve_turn(state, FixedRandom(1))

    assert len(resolution.state.employees) == 0
    assert "left the company" in resolution.narrative


def test_roadmap_project_dependency_is_enforced() -> None:
    product = make_product("Enterprise Desk")
    state = make_state(product, cash_on_hand=Decimal("9000.00"))

    with pytest.raises(ValueError, match="depends on completing platform_rebuild"):
        start_roadmap_project(
            state,
            RoadmapProjectType.ENTERPRISE_CERTIFICATION,
            product.id,
        )


def test_late_roadmap_project_completion_reduces_board_confidence() -> None:
    product = make_product("Debt Box", quality=50, bug_level=30, technical_debt=60)
    employee = make_employee(
        "PM",
        EmployeeRole.PRODUCT_MANAGER,
        assigned_product_id=product.id,
    )
    state = make_state(product, employees=[employee], cash_on_hand=Decimal("10000.00"))

    start_roadmap_project(state, RoadmapProjectType.PLATFORM_REBUILD, product.id)
    project_id = state.roadmap_projects[0].id
    state.company.current_turn = 8
    starting_confidence = state.finance.board_confidence

    work_roadmap_project(state, project_id)
    work_roadmap_project(state, project_id)
    work_roadmap_project(state, project_id)

    assert state.roadmap_projects[0].status is RoadmapProjectStatus.COMPLETED
    assert state.finance.board_confidence < starting_confidence


def test_functional_budget_affects_customer_risk_drift() -> None:
    product = make_product("Trust Cloud", quality=52, bug_level=26, market_fit=56)
    account = CustomerAccount(
        name="Trust Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("900.00"),
        contract_cadence=ContractCadence.ANNUAL,
        discount_rate=Decimal("0.0000"),
        satisfaction=58,
        onboarding_health=55,
        support_load=30,
        expansion_potential=62,
        renewal_turn=8,
        churn_risk=40,
    )
    balanced_state = make_state(
        product.model_copy(deep=True),
        customer_accounts=[account.model_copy(deep=True)],
        functional_budget=FunctionalBudget(),
    )
    trust_state = make_state(
        product.model_copy(deep=True),
        customer_accounts=[account.model_copy(deep=True)],
        functional_budget=FunctionalBudget(
            preset=FunctionalBudgetPreset.CUSTOMER_TRUST,
            engineering_share=25,
            marketing_share=18,
            customer_success_share=37,
            g_and_a_share=20,
        ),
    )

    balanced_resolution = resolve_turn(balanced_state, RandomSource(seed=7))
    trust_resolution = resolve_turn(trust_state, RandomSource(seed=7))

    assert (
        trust_resolution.state.customer_accounts[0].churn_risk
        <= balanced_resolution.state.customer_accounts[0].churn_risk
    )


def test_account_recurring_revenue_includes_add_ons() -> None:
    account = CustomerAccount(
        name="Expansion Anchor",
        product_id=UUID(int=1),
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("1000.00"),
        plan_tier=PricingTier.PREMIUM,
        contract_cadence=ContractCadence.ANNUAL,
        billing_model=ContractBillingModel.FLAT,
        add_on_count=2,
        discount_rate=Decimal("0.1000"),
        satisfaction=74,
        expansion_potential=60,
        renewal_turn=8,
        churn_risk=12,
    )

    assert calculate_account_recurring_revenue(account) == Decimal("1021.50")


def test_explicit_support_program_relief_reduces_account_pressure() -> None:
    product = make_product("Support Guard", quality=46, bug_level=34, market_fit=54)
    account = CustomerAccount(
        name="Support Guard Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("960.00"),
        contract_cadence=ContractCadence.ANNUAL,
        billing_model=ContractBillingModel.SEAT_BASED,
        seat_count=16,
        satisfaction=59,
        onboarding_health=52,
        support_load=32,
        open_tickets=14,
        sla_breach_risk=57,
        expansion_potential=63,
        renewal_turn=7,
        churn_risk=34,
    )

    baseline_account = account.model_copy(deep=True)
    support_account = account.model_copy(deep=True)
    baseline_summary = apply_end_of_turn_customers(
        [baseline_account],
        [product],
        current_turn=4,
    )
    support_summary = apply_end_of_turn_customers(
        [support_account],
        [product],
        current_turn=4,
        support_program=SupportProgram(
            knowledge_base_level=74,
            automation_level=68,
        ),
    )

    assert support_summary.total_open_tickets < baseline_summary.total_open_tickets
    assert support_account.sla_breach_risk < baseline_account.sla_breach_risk
    assert support_account.invoice_risk <= baseline_account.invoice_risk


def test_support_program_backlog_creates_queue_pressure() -> None:
    product = make_product("Ticket Storm", quality=42, bug_level=40, market_fit=50)
    account = CustomerAccount(
        name="Storm Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("1100.00"),
        contract_cadence=ContractCadence.ANNUAL,
        satisfaction=48,
        onboarding_health=45,
        support_load=42,
        open_tickets=28,
        sla_breach_risk=66,
        expansion_potential=52,
        renewal_turn=6,
        churn_risk=44,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("9000.00"))
    state.support_program = SupportProgram(
        knowledge_base_level=6,
        automation_level=4,
        backlog_queue=18,
    )

    summary = apply_end_of_turn_support_program(state)

    assert summary.backlog_queue > 18
    assert summary.sla_breaches >= 1
    assert summary.queue_age_pressure > 0
    assert summary.reputation_delta <= 0
    assert summary.morale_penalty >= 0


def test_support_program_surfaces_revenue_and_renewal_risk_counts() -> None:
    product = make_product("Renewal Queue", quality=44, bug_level=38, market_fit=52)
    account = CustomerAccount(
        name="Critical Renewal",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("1400.00"),
        support_tier=SupportTier.WHITE_GLOVE,
        satisfaction=50,
        onboarding_health=46,
        support_load=44,
        open_tickets=18,
        sla_breach_risk=68,
        renewal_health=46,
        expansion_potential=58,
        renewal_turn=7,
        churn_risk=42,
        status=CustomerAccountStatus.ACTIVE,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("8800.00"))
    state.support_program = SupportProgram(
        knowledge_base_level=10,
        automation_level=8,
        backlog_queue=16,
    )

    summary = apply_end_of_turn_support_program(state)
    revenue_at_risk_accounts, renewal_pressure_accounts = calculate_support_account_risk_counts(
        state
    )
    revenue_at_risk_value, renewal_pressure_value = calculate_support_account_risk_values(state)

    assert summary.revenue_at_risk_accounts >= 1
    assert summary.revenue_at_risk_value >= Decimal("1400.00")
    assert summary.enterprise_revenue_at_risk_value >= Decimal("1400.00")
    assert summary.premium_revenue_at_risk_value >= Decimal("1400.00")
    assert summary.white_glove_revenue_at_risk_value >= Decimal("1400.00")
    assert summary.premium_queue_exposure_value >= Decimal("1400.00")
    assert summary.enterprise_queue_exposure_value >= Decimal("1400.00")
    assert summary.renewal_queue_exposure_value >= Decimal("1400.00")
    assert summary.premium_queue_risk_accounts >= 1
    assert summary.enterprise_queue_risk_accounts >= 1
    assert summary.renewal_queue_risk_accounts >= 1
    assert summary.high_value_risk_accounts >= 0
    assert summary.renewal_pressure_accounts >= 1
    assert summary.renewal_pressure_value >= Decimal("1400.00")
    assert summary.white_glove_breach_accounts >= 1
    assert summary.white_glove_queue_risk_accounts >= 1
    assert summary.severe_queue_accounts >= 1
    assert summary.account_queue_risk_score > 0
    assert summary.lane_saturation_index > 0
    assert summary.hotspot_lane is SupportLaneFocus.ENTERPRISE
    assert summary.hotspot_lane_overflow >= 0
    assert summary.sla_credit_cost > Decimal("0.00")
    assert summary.service_tier_pressure >= 3
    assert summary.commercial_breach_pressure >= 2
    assert revenue_at_risk_accounts >= 1
    assert renewal_pressure_accounts >= 1
    assert revenue_at_risk_value >= Decimal("1400.00")
    assert renewal_pressure_value >= Decimal("1400.00")
    assert state.customer_accounts[0].renewal_health < 46


def test_support_program_recovery_loop_restores_healthy_accounts() -> None:
    product = make_product("Recovery Desk", quality=72, bug_level=10, market_fit=68)
    account = CustomerAccount(
        name="Recovering Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2200.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=70,
        onboarding_health=72,
        support_load=18,
        open_tickets=0,
        sla_breach_risk=10,
        renewal_health=68,
        expansion_potential=62,
        renewal_turn=8,
        churn_risk=12,
        ticket_queue_age=1,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("9800.00"))
    state.support_program = SupportProgram(
        knowledge_base_level=28,
        automation_level=24,
        backlog_queue=1,
        staffing_level=2,
    )

    summary = apply_end_of_turn_support_program(state)

    assert summary.recovery_ready_accounts >= 1
    assert state.customer_accounts[0].satisfaction > 70
    assert state.customer_accounts[0].renewal_health > 68
    assert state.customer_accounts[0].churn_risk < 12


def test_set_support_lane_focus_updates_program_bias() -> None:
    product = make_product("White Glove")
    account = CustomerAccount(
        name="Enterprise Queue",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("1200.00"),
        support_tier=SupportTier.WHITE_GLOVE,
        satisfaction=61,
        expansion_potential=58,
        renewal_turn=6,
        churn_risk=24,
        open_tickets=10,
        status=CustomerAccountStatus.ACTIVE,
    )
    state = make_state(product, customer_accounts=[account])
    state.support_program.backlog_queue = 5
    state.support_program.escalation_queue = 3

    outcome = apply_action(
        state,
        TurnAction.SET_SUPPORT_LANE_FOCUS,
        context=ActionContext(support_lane_focus=SupportLaneFocus.ENTERPRISE),
    )

    assert outcome.state.support_program.lane_focus is SupportLaneFocus.ENTERPRISE
    assert outcome.state.support_program.backlog_queue <= 4
    assert outcome.state.support_program.escalation_queue <= 3
    assert outcome.state.customer_accounts[0].open_tickets < 10


def test_route_support_escalation_prioritizes_billing_lane_pressure() -> None:
    product = make_product("Collections Desk")
    account = CustomerAccount(
        name="Late Invoice Co",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("720.00"),
        contract_cadence=ContractCadence.MONTHLY,
        satisfaction=45,
        onboarding_health=52,
        support_load=26,
        open_tickets=5,
        sla_breach_risk=18,
        invoice_risk=78,
        failed_payment_risk=74,
        dunning_steps=2,
        escalation_count=1,
        expansion_potential=44,
        renewal_health=38,
        renewal_turn=4,
        churn_risk=53,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("5000.00"))
    state.support_program.escalation_queue = 3

    lane = classify_account_support_lane(account)
    outcome = apply_action(
        state,
        TurnAction.ROUTE_SUPPORT_ESCALATION,
        context=ActionContext(customer_account_id=account.id),
    )

    updated = outcome.state.customer_accounts[0]
    assert lane is SupportLaneFocus.BILLING
    assert "billing escalation" in outcome.message
    assert updated.invoice_risk < account.invoice_risk
    assert updated.failed_payment_risk < account.failed_payment_risk
    assert updated.dunning_steps < account.dunning_steps
    assert updated.renewal_health > account.renewal_health


def test_run_account_rescue_stabilizes_revenue_critical_account() -> None:
    product = make_product("Rescue Desk", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Revenue Shield",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2200.00"),
        support_tier=SupportTier.WHITE_GLOVE,
        satisfaction=44,
        onboarding_health=54,
        support_load=28,
        open_tickets=8,
        sla_breach_risk=24,
        invoice_risk=68,
        failed_payment_risk=74,
        dunning_steps=2,
        escalation_count=2,
        ticket_queue_age=4,
        expansion_potential=42,
        renewal_health=34,
        renewal_turn=4,
        churn_risk=57,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("5000.00"))
    state.support_program.backlog_queue = 8
    state.support_program.escalation_queue = 3

    outcome = apply_action(
        state,
        TurnAction.RUN_ACCOUNT_RESCUE,
        context=ActionContext(customer_account_id=account.id),
    )

    updated = outcome.state.customer_accounts[0]
    assert "rescue" in outcome.message
    assert updated.open_tickets < account.open_tickets
    assert updated.sla_breach_risk < account.sla_breach_risk
    assert updated.invoice_risk < account.invoice_risk
    assert updated.failed_payment_risk < account.failed_payment_risk
    assert updated.renewal_health > account.renewal_health
    assert updated.churn_risk < account.churn_risk
    assert outcome.state.support_program.backlog_queue < 8
    assert outcome.state.support_program.escalation_queue < 3


def test_run_lane_recovery_stabilizes_hotspot_lane() -> None:
    product = make_product("Enterprise Lane Core", target_segment=MarketSegment.ENTERPRISE)
    enterprise_account = CustomerAccount(
        name="Critical Enterprise",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2100.00"),
        support_tier=SupportTier.WHITE_GLOVE,
        satisfaction=52,
        onboarding_health=56,
        support_load=30,
        open_tickets=7,
        sla_breach_risk=26,
        ticket_queue_age=4,
        expansion_potential=54,
        renewal_health=42,
        renewal_turn=5,
        churn_risk=38,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(
        product,
        customer_accounts=[enterprise_account],
        cash_on_hand=Decimal("5200.00"),
    )
    state.support_program.backlog_queue = 9
    state.support_program.escalation_queue = 4
    state.support_program.lane_focus = SupportLaneFocus.BALANCED

    outcome = apply_action(
        state,
        TurnAction.RUN_LANE_RECOVERY,
        context=ActionContext(support_lane_focus=SupportLaneFocus.ENTERPRISE),
    )

    updated = outcome.state.customer_accounts[0]
    assert outcome.state.support_program.lane_focus is SupportLaneFocus.ENTERPRISE
    assert updated.open_tickets < enterprise_account.open_tickets
    assert updated.sla_breach_risk < enterprise_account.sla_breach_risk
    assert updated.renewal_health > enterprise_account.renewal_health
    assert updated.churn_risk < enterprise_account.churn_risk
    assert outcome.state.support_program.backlog_queue < 9
    assert outcome.state.support_program.escalation_queue < 4
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_renewal_sweep_stabilizes_imminent_renewals() -> None:
    product = make_product("Renewal Sweep Core", target_segment=MarketSegment.ENTERPRISE)
    billing_account = CustomerAccount(
        name="Billing Renewal",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("920.00"),
        contract_cadence=ContractCadence.MONTHLY,
        support_tier=SupportTier.PRIORITY,
        satisfaction=48,
        onboarding_health=54,
        support_load=24,
        open_tickets=4,
        sla_breach_risk=18,
        invoice_risk=72,
        failed_payment_risk=70,
        dunning_steps=2,
        ticket_queue_age=4,
        expansion_potential=40,
        renewal_health=36,
        renewal_turn=2,
        churn_risk=44,
        status=CustomerAccountStatus.AT_RISK,
    )
    enterprise_account = CustomerAccount(
        name="Enterprise Renewal",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2100.00"),
        support_tier=SupportTier.WHITE_GLOVE,
        satisfaction=56,
        onboarding_health=58,
        support_load=28,
        open_tickets=5,
        sla_breach_risk=20,
        ticket_queue_age=3,
        expansion_potential=56,
        renewal_health=44,
        renewal_turn=3,
        churn_risk=36,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(
        product,
        customer_accounts=[billing_account, enterprise_account],
        cash_on_hand=Decimal("5600.00"),
    )
    state.support_program.backlog_queue = 6
    state.support_program.escalation_queue = 3

    outcome = apply_action(state, TurnAction.RUN_RENEWAL_SWEEP, context=ActionContext())

    updated_billing = outcome.state.customer_accounts[0]
    updated_enterprise = outcome.state.customer_accounts[1]
    assert updated_billing.renewal_health > billing_account.renewal_health
    assert updated_billing.invoice_risk < billing_account.invoice_risk
    assert updated_billing.failed_payment_risk < billing_account.failed_payment_risk
    assert updated_billing.churn_risk < billing_account.churn_risk
    assert updated_enterprise.renewal_health > enterprise_account.renewal_health
    assert updated_enterprise.satisfaction > enterprise_account.satisfaction
    assert outcome.state.support_program.backlog_queue < 6
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_enterprise_assurance_stabilizes_ipo_accounts() -> None:
    product = make_product("Enterprise Assurance Core", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Assurance Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("3200.00"),
        support_tier=SupportTier.STANDARD,
        satisfaction=52,
        onboarding_health=62,
        support_load=30,
        open_tickets=6,
        sla_breach_risk=28,
        ticket_queue_age=4,
        expansion_potential=58,
        renewal_health=42,
        renewal_turn=4,
        churn_risk=40,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("6400.00"))
    state.support_program.backlog_queue = 7
    state.support_program.escalation_queue = 4
    state.finance.board_pressure = 18

    outcome = apply_action(state, TurnAction.RUN_ENTERPRISE_ASSURANCE, context=ActionContext())

    updated_account = outcome.state.customer_accounts[0]
    assert updated_account.support_tier is SupportTier.PRIORITY
    assert updated_account.open_tickets < account.open_tickets
    assert updated_account.sla_breach_risk < account.sla_breach_risk
    assert updated_account.renewal_health > account.renewal_health
    assert updated_account.satisfaction > account.satisfaction
    assert outcome.state.support_program.backlog_queue < 7
    assert outcome.state.finance.board_pressure < 18
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_billing_stabilization_cools_renewal_hotspot_accounts() -> None:
    product = make_product("Billing Stabilization Core", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Billing Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2800.00"),
        support_tier=SupportTier.WHITE_GLOVE,
        satisfaction=50,
        onboarding_health=58,
        support_load=26,
        open_tickets=5,
        sla_breach_risk=22,
        invoice_risk=68,
        failed_payment_risk=64,
        dunning_steps=2,
        ticket_queue_age=4,
        expansion_potential=52,
        renewal_health=38,
        renewal_turn=2,
        churn_risk=42,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("6200.00"))
    state.support_program.backlog_queue = 6
    state.support_program.escalation_queue = 3
    state.finance.investor_pressure = 12

    outcome = apply_action(state, TurnAction.RUN_BILLING_STABILIZATION, context=ActionContext())

    updated_account = outcome.state.customer_accounts[0]
    assert updated_account.invoice_risk < account.invoice_risk
    assert updated_account.failed_payment_risk < account.failed_payment_risk
    assert updated_account.renewal_health > account.renewal_health
    assert updated_account.churn_risk < account.churn_risk
    assert outcome.state.support_program.backlog_queue < 6
    assert outcome.state.finance.investor_pressure < 12
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_onboarding_recovery_rebuilds_implementation_hotspots() -> None:
    product = make_product("Onboarding Recovery Core", target_segment=MarketSegment.STARTUP)
    account = CustomerAccount(
        name="Implementation Anchor",
        product_id=product.id,
        segment=MarketSegment.STARTUP,
        contract_value=Decimal("2200.00"),
        support_tier=SupportTier.STANDARD,
        satisfaction=52,
        onboarding_health=18,
        support_load=40,
        open_tickets=8,
        sla_breach_risk=48,
        ticket_queue_age=4,
        expansion_potential=60,
        renewal_health=44,
        renewal_turn=6,
        churn_risk=30,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("6100.00"))
    state.support_program.backlog_queue = 7
    state.support_program.escalation_queue = 3
    state.finance.board_pressure = 18

    outcome = apply_action(state, TurnAction.RUN_ONBOARDING_RECOVERY, context=ActionContext())

    updated_account = outcome.state.customer_accounts[0]
    assert updated_account.onboarding_health > account.onboarding_health
    assert updated_account.support_load < account.support_load
    assert updated_account.renewal_health > account.renewal_health
    assert updated_account.churn_risk < account.churn_risk
    assert outcome.state.support_program.backlog_queue < 7
    assert outcome.state.finance.board_pressure < 18
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_onboarding_fast_track_recovers_implementation_account() -> None:
    product = make_product("Onboarding Fast Track Core", target_segment=MarketSegment.STARTUP)
    account = CustomerAccount(
        name="Fast Track Anchor",
        product_id=product.id,
        segment=MarketSegment.STARTUP,
        contract_value=Decimal("2400.00"),
        support_tier=SupportTier.STANDARD,
        satisfaction=50,
        onboarding_health=16,
        support_load=42,
        open_tickets=8,
        sla_breach_risk=52,
        ticket_queue_age=5,
        expansion_potential=58,
        renewal_health=40,
        renewal_turn=5,
        churn_risk=34,
        escalation_count=2,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("6200.00"))
    state.support_program.backlog_queue = 7
    state.support_program.escalation_queue = 3
    state.finance.board_pressure = 17

    outcome = apply_action(
        state,
        TurnAction.RUN_ONBOARDING_FAST_TRACK,
        context=ActionContext(customer_account_id=account.id),
    )

    updated_account = outcome.state.customer_accounts[0]
    assert updated_account.support_tier is SupportTier.PRIORITY
    assert updated_account.open_tickets < account.open_tickets
    assert updated_account.sla_breach_risk < account.sla_breach_risk
    assert updated_account.onboarding_health > account.onboarding_health
    assert updated_account.renewal_health > account.renewal_health
    assert outcome.state.support_program.backlog_queue < 7
    assert outcome.state.finance.board_pressure < 17
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_reference_rescue_stabilizes_flagship_account() -> None:
    product = make_product("Reference Rescue Core", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Flagship Reference",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("3200.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=58,
        onboarding_health=52,
        support_load=26,
        open_tickets=5,
        sla_breach_risk=42,
        ticket_queue_age=3,
        expansion_potential=68,
        renewal_health=48,
        renewal_turn=7,
        churn_risk=24,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("6800.00"))
    state.support_program.backlog_queue = 5
    state.support_program.escalation_queue = 2
    state.finance.board_pressure = 16
    state.finance.board_confidence = 44

    outcome = apply_action(
        state,
        TurnAction.RUN_REFERENCE_RESCUE,
        context=ActionContext(customer_account_id=account.id),
    )

    updated_account = outcome.state.customer_accounts[0]
    assert updated_account.support_tier is SupportTier.WHITE_GLOVE
    assert updated_account.open_tickets < account.open_tickets
    assert updated_account.sla_breach_risk < account.sla_breach_risk
    assert updated_account.renewal_health > account.renewal_health
    assert updated_account.satisfaction > account.satisfaction
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_enterprise_queue_reset_stabilizes_flagship_queue_account() -> None:
    product = make_product("Enterprise Queue Reset Core", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Enterprise Queue Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("3600.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=54,
        onboarding_health=44,
        support_load=40,
        open_tickets=9,
        sla_breach_risk=58,
        ticket_queue_age=5,
        expansion_potential=72,
        renewal_health=42,
        renewal_turn=6,
        churn_risk=32,
        escalation_count=2,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("7200.00"))
    state.support_program.backlog_queue = 8
    state.support_program.escalation_queue = 3
    state.finance.board_pressure = 22
    state.finance.board_confidence = 46

    outcome = apply_action(
        state,
        TurnAction.RUN_ENTERPRISE_QUEUE_RESET,
        context=ActionContext(customer_account_id=account.id),
    )

    updated_account = outcome.state.customer_accounts[0]
    assert outcome.state.support_program.lane_focus is SupportLaneFocus.ENTERPRISE
    assert updated_account.support_tier is SupportTier.WHITE_GLOVE
    assert updated_account.open_tickets < account.open_tickets
    assert updated_account.sla_breach_risk < account.sla_breach_risk
    assert updated_account.ticket_queue_age < account.ticket_queue_age
    assert updated_account.support_load < account.support_load
    assert updated_account.onboarding_health > account.onboarding_health
    assert updated_account.renewal_health > account.renewal_health
    assert updated_account.satisfaction > account.satisfaction
    assert updated_account.churn_risk < account.churn_risk
    assert outcome.state.support_program.backlog_queue < state.support_program.backlog_queue
    assert outcome.state.support_program.escalation_queue < state.support_program.escalation_queue
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_white_glove_recovery_stabilizes_premium_account() -> None:
    product = make_product("White Glove Recovery Core", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="White Glove Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("4200.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=52,
        onboarding_health=50,
        support_load=38,
        open_tickets=10,
        sla_breach_risk=66,
        ticket_queue_age=4,
        expansion_potential=72,
        renewal_health=44,
        renewal_turn=6,
        churn_risk=34,
        invoice_risk=18,
        failed_payment_risk=16,
        escalation_count=2,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("7800.00"))
    state.support_program.backlog_queue = 9
    state.support_program.escalation_queue = 4
    state.finance.board_pressure = 24
    state.finance.board_confidence = 42

    outcome = apply_action(
        state,
        TurnAction.RUN_WHITE_GLOVE_RECOVERY,
        context=ActionContext(customer_account_id=account.id),
    )

    updated_account = outcome.state.customer_accounts[0]
    assert outcome.state.support_program.lane_focus is SupportLaneFocus.ENTERPRISE
    assert updated_account.support_tier is SupportTier.WHITE_GLOVE
    assert updated_account.open_tickets < account.open_tickets
    assert updated_account.sla_breach_risk < account.sla_breach_risk
    assert updated_account.ticket_queue_age < account.ticket_queue_age
    assert updated_account.support_load < account.support_load
    assert updated_account.invoice_risk < account.invoice_risk
    assert updated_account.failed_payment_risk < account.failed_payment_risk
    assert updated_account.renewal_health > account.renewal_health
    assert updated_account.satisfaction > account.satisfaction
    assert outcome.state.support_program.backlog_queue < state.support_program.backlog_queue
    assert outcome.state.support_program.escalation_queue < state.support_program.escalation_queue
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_white_glove_backstop_stabilizes_flagship_account() -> None:
    product = make_product("White Glove Backstop Core", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Flagship Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("4600.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=50,
        onboarding_health=52,
        support_load=40,
        open_tickets=11,
        sla_breach_risk=68,
        ticket_queue_age=4,
        expansion_potential=74,
        renewal_health=42,
        renewal_turn=6,
        churn_risk=36,
        escalation_count=2,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("8400.00"))
    state.support_program.backlog_queue = 10
    state.support_program.escalation_queue = 4
    state.finance.board_pressure = 24
    state.finance.board_confidence = 40
    state.company.reputation = 70

    outcome = apply_action(
        state,
        TurnAction.RUN_WHITE_GLOVE_BACKSTOP,
        context=ActionContext(customer_account_id=account.id),
    )

    updated_account = outcome.state.customer_accounts[0]
    assert outcome.state.support_program.lane_focus is SupportLaneFocus.ENTERPRISE
    assert updated_account.support_tier is SupportTier.WHITE_GLOVE
    assert updated_account.open_tickets < account.open_tickets
    assert updated_account.sla_breach_risk < account.sla_breach_risk
    assert updated_account.ticket_queue_age < account.ticket_queue_age
    assert updated_account.support_load < account.support_load
    assert updated_account.renewal_health > account.renewal_health
    assert updated_account.satisfaction > account.satisfaction
    assert updated_account.churn_risk < account.churn_risk
    assert outcome.state.support_program.backlog_queue < state.support_program.backlog_queue
    assert outcome.state.support_program.escalation_queue < state.support_program.escalation_queue
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.reputation > state.company.reputation
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_white_glove_renewal_guard_stabilizes_flagship_renewal_account() -> None:
    product = make_product(
        "White Glove Renewal Guard Core", target_segment=MarketSegment.ENTERPRISE
    )
    account = CustomerAccount(
        name="Flagship Renewal Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("4800.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=52,
        onboarding_health=54,
        support_load=38,
        open_tickets=10,
        sla_breach_risk=62,
        ticket_queue_age=4,
        expansion_potential=76,
        renewal_health=40,
        renewal_turn=5,
        churn_risk=34,
        invoice_risk=22,
        failed_payment_risk=18,
        escalation_count=2,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("8600.00"))
    state.support_program.backlog_queue = 11
    state.support_program.escalation_queue = 4
    state.finance.board_pressure = 24
    state.finance.board_confidence = 40
    state.company.reputation = 70

    outcome = apply_action(
        state,
        TurnAction.RUN_WHITE_GLOVE_RENEWAL_GUARD,
        context=ActionContext(customer_account_id=account.id),
    )

    updated_account = outcome.state.customer_accounts[0]
    assert outcome.state.support_program.lane_focus is SupportLaneFocus.ENTERPRISE
    assert updated_account.support_tier is SupportTier.WHITE_GLOVE
    assert updated_account.open_tickets < account.open_tickets
    assert updated_account.sla_breach_risk < account.sla_breach_risk
    assert updated_account.ticket_queue_age < account.ticket_queue_age
    assert updated_account.support_load < account.support_load
    assert updated_account.invoice_risk < account.invoice_risk
    assert updated_account.failed_payment_risk < account.failed_payment_risk
    assert updated_account.renewal_health > account.renewal_health
    assert updated_account.satisfaction > account.satisfaction
    assert updated_account.churn_risk < account.churn_risk
    assert outcome.state.support_program.backlog_queue < state.support_program.backlog_queue
    assert outcome.state.support_program.escalation_queue < state.support_program.escalation_queue
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.reputation > state.company.reputation
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_white_glove_reference_ring_strengthens_flagship_reference_account() -> None:
    product = make_product(
        "White Glove Reference Ring Core", target_segment=MarketSegment.ENTERPRISE
    )
    account = CustomerAccount(
        name="Flagship Reference Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("5100.00"),
        support_tier=SupportTier.WHITE_GLOVE,
        satisfaction=54,
        onboarding_health=56,
        support_load=34,
        open_tickets=8,
        sla_breach_risk=50,
        ticket_queue_age=3,
        expansion_potential=70,
        renewal_health=46,
        renewal_turn=6,
        churn_risk=28,
        escalation_count=2,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("8700.00"))
    state.support_program.backlog_queue = 9
    state.support_program.escalation_queue = 3
    state.finance.board_pressure = 22
    state.finance.board_confidence = 42
    state.finance.board_score = 40
    state.company.reputation = 70

    outcome = apply_action(
        state,
        TurnAction.RUN_WHITE_GLOVE_REFERENCE_RING,
        context=ActionContext(customer_account_id=account.id),
    )

    updated_account = outcome.state.customer_accounts[0]
    assert outcome.state.support_program.lane_focus is SupportLaneFocus.ENTERPRISE
    assert updated_account.support_tier is SupportTier.WHITE_GLOVE
    assert updated_account.open_tickets < account.open_tickets
    assert updated_account.sla_breach_risk < account.sla_breach_risk
    assert updated_account.ticket_queue_age < account.ticket_queue_age
    assert updated_account.support_load < account.support_load
    assert updated_account.onboarding_health > account.onboarding_health
    assert updated_account.renewal_health > account.renewal_health
    assert updated_account.satisfaction > account.satisfaction
    assert updated_account.expansion_potential > account.expansion_potential
    assert updated_account.churn_risk < account.churn_risk
    assert outcome.state.support_program.backlog_queue < state.support_program.backlog_queue
    assert outcome.state.support_program.escalation_queue < state.support_program.escalation_queue
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.company.reputation > state.company.reputation
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_white_glove_reference_committee_rebuilds_flagship_account() -> None:
    product = make_product(
        "White Glove Reference Committee Core",
        target_segment=MarketSegment.ENTERPRISE,
    )
    account = CustomerAccount(
        name="Committee Flagship",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("5200.00"),
        support_tier=SupportTier.WHITE_GLOVE,
        satisfaction=52,
        onboarding_health=58,
        support_load=36,
        open_tickets=9,
        sla_breach_risk=56,
        ticket_queue_age=3,
        expansion_potential=68,
        renewal_health=44,
        renewal_turn=6,
        churn_risk=30,
        escalation_count=2,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("8800.00"))
    state.support_program.backlog_queue = 10
    state.support_program.escalation_queue = 4
    state.finance.board_pressure = 24
    state.finance.board_confidence = 40
    state.finance.board_score = 38
    state.finance.investor_pressure = 16
    state.company.reputation = 69

    outcome = apply_action(
        state,
        TurnAction.RUN_WHITE_GLOVE_REFERENCE_COMMITTEE,
        context=ActionContext(customer_account_id=account.id),
    )

    updated_account = outcome.state.customer_accounts[0]
    assert outcome.state.support_program.lane_focus is SupportLaneFocus.ENTERPRISE
    assert updated_account.support_tier is SupportTier.WHITE_GLOVE
    assert updated_account.open_tickets < account.open_tickets
    assert updated_account.sla_breach_risk < account.sla_breach_risk
    assert updated_account.ticket_queue_age < account.ticket_queue_age
    assert updated_account.support_load < account.support_load
    assert updated_account.renewal_health > account.renewal_health
    assert updated_account.satisfaction > account.satisfaction
    assert updated_account.expansion_potential > account.expansion_potential
    assert updated_account.churn_risk < account.churn_risk
    assert outcome.state.support_program.backlog_queue < state.support_program.backlog_queue
    assert outcome.state.support_program.escalation_queue < state.support_program.escalation_queue
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.company.reputation > state.company.reputation
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_enterprise_reference_cycle_strengthens_flagship_account() -> None:
    product = make_product("Reference Cycle Core", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Reference Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("3600.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=64,
        onboarding_health=58,
        support_load=24,
        open_tickets=3,
        sla_breach_risk=22,
        ticket_queue_age=2,
        expansion_potential=60,
        renewal_health=58,
        renewal_turn=8,
        churn_risk=18,
        escalation_count=1,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("8200.00"))
    state.support_program.backlog_queue = 6
    state.support_program.escalation_queue = 2
    state.finance.board_pressure = 20
    state.finance.board_confidence = 44
    state.finance.board_score = 42
    state.company.reputation = 70

    outcome = apply_action(
        state,
        TurnAction.RUN_ENTERPRISE_REFERENCE_CYCLE,
        context=ActionContext(customer_account_id=account.id),
    )

    updated_account = outcome.state.customer_accounts[0]
    assert outcome.state.support_program.lane_focus is SupportLaneFocus.ENTERPRISE
    assert updated_account.open_tickets < account.open_tickets
    assert updated_account.sla_breach_risk < account.sla_breach_risk
    assert updated_account.support_load < account.support_load
    assert updated_account.renewal_health > account.renewal_health
    assert updated_account.satisfaction > account.satisfaction
    assert updated_account.expansion_potential > account.expansion_potential
    assert updated_account.churn_risk < account.churn_risk
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.company.reputation > state.company.reputation
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_enterprise_renewal_cabinet_stabilizes_enterprise_renewal_account() -> None:
    product = make_product("Renewal Cabinet Core", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Renewal Cabinet Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("3900.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=60,
        onboarding_health=56,
        support_load=26,
        open_tickets=4,
        sla_breach_risk=24,
        ticket_queue_age=2,
        expansion_potential=58,
        renewal_health=52,
        renewal_turn=6,
        churn_risk=24,
        escalation_count=1,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("8300.00"))
    state.support_program.backlog_queue = 7
    state.support_program.escalation_queue = 2
    state.finance.board_pressure = 22
    state.finance.board_confidence = 42
    state.finance.board_score = 40
    state.company.reputation = 69

    outcome = apply_action(
        state,
        TurnAction.RUN_ENTERPRISE_RENEWAL_CABINET,
        context=ActionContext(customer_account_id=account.id),
    )

    updated_account = outcome.state.customer_accounts[0]
    assert outcome.state.support_program.lane_focus is SupportLaneFocus.ENTERPRISE
    assert updated_account.open_tickets < account.open_tickets
    assert updated_account.sla_breach_risk < account.sla_breach_risk
    assert updated_account.support_load < account.support_load
    assert updated_account.onboarding_health > account.onboarding_health
    assert updated_account.renewal_health > account.renewal_health
    assert updated_account.satisfaction > account.satisfaction
    assert updated_account.expansion_potential > account.expansion_potential
    assert updated_account.churn_risk < account.churn_risk
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.company.reputation > state.company.reputation
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_billing_retention_reset_cools_one_billing_hotspot() -> None:
    product = make_product("Billing Reset Core", target_segment=MarketSegment.SMB)
    account = CustomerAccount(
        name="Billing Anchor",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("1900.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=52,
        onboarding_health=64,
        support_load=24,
        open_tickets=4,
        sla_breach_risk=24,
        ticket_queue_age=2,
        expansion_potential=54,
        renewal_health=46,
        renewal_turn=4,
        churn_risk=28,
        invoice_risk=38,
        failed_payment_risk=34,
        dunning_steps=2,
        escalation_count=1,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("7400.00"))
    state.support_program.backlog_queue = 5
    state.support_program.escalation_queue = 3
    state.finance.board_pressure = 18
    state.finance.investor_pressure = 15
    state.finance.board_confidence = 48

    outcome = apply_action(
        state,
        TurnAction.RUN_BILLING_RETENTION_RESET,
        context=ActionContext(customer_account_id=account.id),
    )

    updated_account = outcome.state.customer_accounts[0]
    assert outcome.state.support_program.lane_focus is SupportLaneFocus.BILLING
    assert updated_account.invoice_risk < account.invoice_risk
    assert updated_account.failed_payment_risk < account.failed_payment_risk
    assert updated_account.dunning_steps < account.dunning_steps
    assert updated_account.renewal_health > account.renewal_health
    assert updated_account.satisfaction > account.satisfaction
    assert updated_account.churn_risk < account.churn_risk
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_billing_covenant_reset_cools_billing_covenant_heat() -> None:
    product = make_product("Billing Covenant Reset Core", target_segment=MarketSegment.SMB)
    account = CustomerAccount(
        name="Billing Covenant Anchor",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("2100.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=50,
        onboarding_health=62,
        support_load=26,
        open_tickets=5,
        sla_breach_risk=28,
        ticket_queue_age=2,
        expansion_potential=52,
        renewal_health=44,
        renewal_turn=4,
        churn_risk=30,
        invoice_risk=42,
        failed_payment_risk=36,
        dunning_steps=2,
        escalation_count=1,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("7600.00"))
    state.support_program.backlog_queue = 6
    state.support_program.escalation_queue = 3
    state.finance.board_pressure = 20
    state.finance.investor_pressure = 18
    state.finance.covenant_risk = 12
    state.finance.board_confidence = 46

    outcome = apply_action(
        state,
        TurnAction.RUN_BILLING_COVENANT_RESET,
        context=ActionContext(customer_account_id=account.id),
    )

    updated_account = outcome.state.customer_accounts[0]
    assert outcome.state.support_program.lane_focus is SupportLaneFocus.BILLING
    assert updated_account.open_tickets < account.open_tickets
    assert updated_account.sla_breach_risk < account.sla_breach_risk
    assert updated_account.ticket_queue_age < account.ticket_queue_age
    assert updated_account.support_load < account.support_load
    assert updated_account.invoice_risk < account.invoice_risk
    assert updated_account.failed_payment_risk < account.failed_payment_risk
    assert updated_account.dunning_steps < account.dunning_steps
    assert updated_account.renewal_health > account.renewal_health
    assert updated_account.satisfaction > account.satisfaction
    assert updated_account.churn_risk < account.churn_risk
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.covenant_risk < state.finance.covenant_risk
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_onboarding_control_tower_stabilizes_implementation_hotspot() -> None:
    product = make_product("Onboarding Control Tower Core", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Implementation Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2600.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=54,
        onboarding_health=38,
        support_load=28,
        open_tickets=5,
        sla_breach_risk=30,
        ticket_queue_age=2,
        expansion_potential=50,
        renewal_health=46,
        renewal_turn=6,
        churn_risk=24,
        escalation_count=1,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("8200.00"))
    state.support_program.backlog_queue = 8
    state.support_program.escalation_queue = 3
    state.finance.board_pressure = 20

    outcome = apply_action(
        state,
        TurnAction.RUN_ONBOARDING_CONTROL_TOWER,
        context=ActionContext(customer_account_id=account.id),
    )

    updated_account = outcome.state.customer_accounts[0]
    assert outcome.state.support_program.lane_focus is SupportLaneFocus.ONBOARDING
    assert updated_account.open_tickets < account.open_tickets
    assert updated_account.sla_breach_risk < account.sla_breach_risk
    assert updated_account.support_load < account.support_load
    assert updated_account.onboarding_health > account.onboarding_health
    assert updated_account.renewal_health > account.renewal_health
    assert updated_account.satisfaction > account.satisfaction
    assert updated_account.churn_risk < account.churn_risk
    assert outcome.state.support_program.backlog_queue < state.support_program.backlog_queue
    assert outcome.state.support_program.escalation_queue < state.support_program.escalation_queue
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_white_glove_escalation_cell_rebuilds_flagship_premium_account() -> None:
    product = make_product(
        "White Glove Escalation Cell Core",
        target_segment=MarketSegment.ENTERPRISE,
    )
    account = CustomerAccount(
        name="Escalation Flagship",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("5600.00"),
        support_tier=SupportTier.WHITE_GLOVE,
        satisfaction=50,
        onboarding_health=54,
        support_load=38,
        open_tickets=10,
        sla_breach_risk=58,
        ticket_queue_age=3,
        expansion_potential=66,
        renewal_health=42,
        renewal_turn=5,
        churn_risk=32,
        invoice_risk=16,
        failed_payment_risk=14,
        escalation_count=3,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("9800.00"))
    state.support_program.backlog_queue = 12
    state.support_program.escalation_queue = 5
    state.finance.board_pressure = 28
    state.finance.board_confidence = 36
    state.finance.board_score = 34
    state.finance.investor_pressure = 18
    state.company.reputation = 70

    outcome = apply_action(
        state,
        TurnAction.RUN_WHITE_GLOVE_ESCALATION_CELL,
        context=ActionContext(customer_account_id=account.id),
    )

    updated_account = outcome.state.customer_accounts[0]
    assert outcome.state.support_program.lane_focus is SupportLaneFocus.ENTERPRISE
    assert updated_account.support_tier is SupportTier.WHITE_GLOVE
    assert updated_account.open_tickets < account.open_tickets
    assert updated_account.sla_breach_risk < account.sla_breach_risk
    assert updated_account.ticket_queue_age < account.ticket_queue_age
    assert updated_account.support_load < account.support_load
    assert updated_account.invoice_risk < account.invoice_risk
    assert updated_account.failed_payment_risk < account.failed_payment_risk
    assert updated_account.renewal_health > account.renewal_health
    assert updated_account.satisfaction > account.satisfaction
    assert updated_account.expansion_potential > account.expansion_potential
    assert updated_account.churn_risk < account.churn_risk
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.company.reputation > state.company.reputation
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_billing_dispute_desk_cools_payment_and_covenant_stress() -> None:
    product = make_product("Billing Dispute Desk Core", target_segment=MarketSegment.SMB)
    account = CustomerAccount(
        name="Dispute Desk Anchor",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("2400.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=48,
        onboarding_health=60,
        support_load=28,
        open_tickets=6,
        sla_breach_risk=30,
        ticket_queue_age=2,
        expansion_potential=50,
        renewal_health=42,
        renewal_turn=4,
        churn_risk=32,
        invoice_risk=46,
        failed_payment_risk=40,
        dunning_steps=3,
        escalation_count=2,
        status=CustomerAccountStatus.AT_RISK,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("8600.00"))
    state.support_program.backlog_queue = 7
    state.support_program.escalation_queue = 3
    state.finance.board_pressure = 22
    state.finance.investor_pressure = 20
    state.finance.covenant_risk = 16
    state.finance.board_confidence = 42

    outcome = apply_action(
        state,
        TurnAction.RUN_BILLING_DISPUTE_DESK,
        context=ActionContext(customer_account_id=account.id),
    )

    updated_account = outcome.state.customer_accounts[0]
    assert outcome.state.support_program.lane_focus is SupportLaneFocus.BILLING
    assert updated_account.open_tickets < account.open_tickets
    assert updated_account.sla_breach_risk < account.sla_breach_risk
    assert updated_account.support_load < account.support_load
    assert updated_account.invoice_risk < account.invoice_risk
    assert updated_account.failed_payment_risk < account.failed_payment_risk
    assert updated_account.dunning_steps < account.dunning_steps
    assert updated_account.renewal_health > account.renewal_health
    assert updated_account.satisfaction > account.satisfaction
    assert updated_account.churn_risk < account.churn_risk
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.covenant_risk < state.finance.covenant_risk
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_hiring_pipeline_can_source_interview_and_close_offer() -> None:
    product = make_product("Hiring Hub")
    state = make_state(product, cash_on_hand=Decimal("15000.00"))
    state.company.reputation = 72

    source_summary = source_candidates(state, count=1)

    assert "Sourced 1 candidate" in source_summary.message
    assert len(state.hiring_candidates) == 1
    candidate = state.hiring_candidates[0]
    assert candidate.stage is HiringCandidateStage.SOURCED

    with pytest.raises(ValueError, match="screened"):
        interview_candidate(state, candidate.id)

    screen_summary = screen_candidate(state, candidate.id)

    assert "Screened" in screen_summary.message
    assert candidate.stage is HiringCandidateStage.SCREENED

    interview_summary = interview_candidate(state, candidate.id)

    assert "Interviewed" in interview_summary.message
    assert candidate.stage is HiringCandidateStage.INTERVIEWED

    candidate.acceptance_chance = 90
    candidate.interview_score = 84
    candidate.salary_expectation = Decimal("650.00")
    offer_summary = make_hiring_offer(state, candidate.id)

    assert "accepted the offer" in offer_summary.message
    assert len(state.hiring_candidates) == 0
    assert any(employee.full_name == candidate.full_name for employee in state.employees)


def test_hiring_offer_negotiation_can_raise_salary_before_acceptance() -> None:
    product = make_product("Negotiation Hub")
    state = make_state(product, cash_on_hand=Decimal("15000.00"))
    state.company.reputation = 58
    source_candidates(state, count=1)
    candidate = state.hiring_candidates[0]
    screen_candidate(state, candidate.id)
    interview_candidate(state, candidate.id)

    candidate.acceptance_chance = 45
    candidate.interview_score = 6
    candidate.salary_expectation = Decimal("900.00")
    negotiation_summary = make_hiring_offer(state, candidate.id)

    assert "stronger package" in negotiation_summary.message
    assert candidate.negotiation_rounds == 1
    assert candidate.salary_expectation == Decimal("945.00")
    assert candidate.stage is HiringCandidateStage.INTERVIEWED

    candidate.acceptance_chance = 88
    candidate.interview_score = 80
    accepted_summary = make_hiring_offer(state, candidate.id)

    assert "accepted the offer" in accepted_summary.message
    assert not state.hiring_candidates


def test_support_triage_reduces_backlog_and_account_pressure() -> None:
    product = make_product("Service Desk")
    account = CustomerAccount(
        name="Queue Heavy",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("1300.00"),
        contract_cadence=ContractCadence.MONTHLY,
        satisfaction=46,
        onboarding_health=44,
        support_load=40,
        open_tickets=24,
        sla_breach_risk=74,
        invoice_risk=48,
        failed_payment_risk=55,
        escalation_count=2,
        expansion_potential=48,
        renewal_health=40,
        renewal_turn=4,
        churn_risk=52,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("5000.00"))
    state.support_program = SupportProgram(
        knowledge_base_level=20,
        automation_level=14,
        backlog_queue=20,
        escalation_queue=6,
    )

    summary = triage_support_backlog(state)

    assert "support triage sprint" in summary.message
    assert state.support_program.backlog_queue < 20
    assert state.support_program.escalation_queue < 6
    assert account.open_tickets < 24
    assert account.sla_breach_risk < 74
    assert account.failed_payment_risk < 55


def test_failed_payment_dunning_can_force_customer_churn() -> None:
    product = make_product("Billing Core", user_count=30)
    account = CustomerAccount(
        name="Dunning Risk",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("480.00"),
        contract_cadence=ContractCadence.MONTHLY,
        billing_model=ContractBillingModel.FLAT,
        satisfaction=42,
        onboarding_health=28,
        support_load=26,
        invoice_risk=90,
        failed_payment_risk=58,
        dunning_steps=2,
        expansion_potential=35,
        renewal_health=12,
        renewal_turn=3,
        churn_risk=60,
        status=CustomerAccountStatus.AT_RISK,
    )

    summary = apply_end_of_turn_customers([account], [product], current_turn=3)

    assert summary.churned_accounts == 1
    assert account.status is CustomerAccountStatus.CHURNED
    assert product.user_count < 30


def test_governance_layer_raises_warning_when_cash_and_support_are_weak() -> None:
    product = make_product("Governance Core")
    state = make_state(product, cash_on_hand=Decimal("2200.00"), current_turn=4)
    state.finance.board_confidence = 35
    state.finance.forecast_runway_turns = 2
    state.finance.missed_board_targets = 1
    state.support_program.backlog_queue = 16
    state.support_program.escalation_queue = 6

    customer_summary = apply_end_of_turn_customers(
        state.customer_accounts,
        [product],
        current_turn=4,
    )
    operations_summary = calculate_operations_summary(
        state.products,
        state.employees,
        current_turn=state.company.current_turn,
        customer_accounts=state.customer_accounts,
    )
    summary = apply_end_of_turn_governance(
        state,
        resolved_turn=4,
        total_revenue=Decimal("1200.00"),
        net_cash_flow=Decimal("-950.00"),
        customer_summary=customer_summary,
        operations_summary=operations_summary,
    )

    assert summary.board_review_happened is True
    assert summary.board_warning_active is True
    assert state.finance.board_pressure > 0
    assert state.finance.board_directive.value == "stabilize_cash"


def test_finance_forecast_updates_board_and_covenant_pressure() -> None:
    finance = FinanceState(
        debt_principal=Decimal("5200.00"),
        loan_interest_rate=Decimal("0.0300"),
        investor_pressure=14,
        board_confidence=64,
    )
    company = Company(
        name="Forecast Labs",
        cash_on_hand=Decimal("1800.00"),
        reputation=52,
    )
    turn_history = [
        TurnLedgerEntry(
            turn=1,
            total_revenue=Decimal("1100.00"),
            total_operating_cost=Decimal("1900.00"),
            net_cash_flow=Decimal("-800.00"),
            cash_on_hand=Decimal("3000.00"),
            reputation=50,
            total_users=38,
            headcount=2,
            roadmap_focus=RoadmapFocus.BALANCED_EXECUTION,
        ),
        TurnLedgerEntry(
            turn=2,
            total_revenue=Decimal("1180.00"),
            total_operating_cost=Decimal("1980.00"),
            net_cash_flow=Decimal("-800.00"),
            cash_on_hand=Decimal("2200.00"),
            reputation=51,
            total_users=40,
            headcount=2,
            roadmap_focus=RoadmapFocus.BALANCED_EXECUTION,
        ),
    ]

    summary = apply_end_of_turn_finance_drift(
        finance,
        company,
        net_cash_flow=Decimal("-900.00"),
        turn_history=turn_history,
    )

    assert summary.forecast_net_cash_flow == Decimal("-833.33")
    assert summary.forecast_runway_turns == 2
    assert finance.covenant_risk > 0
    assert finance.missed_board_targets > 0
    assert finance.board_confidence < 64


def test_set_packaging_strategy_changes_product_economics() -> None:
    product = make_product("Atlas", revenue_per_user=Decimal("30.00"))
    state = make_state(product)

    baseline_rpu = calculate_effective_revenue_per_user(product)
    outcome = apply_action(
        state,
        TurnAction.SET_PACKAGING_STRATEGY,
        context=ActionContext(
            target_product_id=product.id,
            packaging_strategy=PackagingStrategy.MODULAR,
        ),
    )

    updated_product = outcome.state.products[0]
    assert updated_product.packaging_strategy is PackagingStrategy.MODULAR
    assert calculate_effective_revenue_per_user(updated_product) > baseline_rpu


def test_upgrade_support_program_spends_cash_and_improves_focus_metric() -> None:
    state = make_state(make_product("Support Atlas"), cash_on_hand=Decimal("4000.00"))
    starting_cash = state.company.cash_on_hand
    starting_automation = state.support_program.automation_level

    outcome = apply_action(
        state,
        TurnAction.UPGRADE_SUPPORT_PROGRAM,
        context=ActionContext(support_investment_focus=SupportInvestmentFocus.AUTOMATION),
    )

    assert outcome.state.company.cash_on_hand < starting_cash
    assert outcome.state.support_program.automation_level > starting_automation


def test_assign_manager_increases_managed_coverage_and_coordination() -> None:
    product = make_product("Managed Platform")
    manager = make_employee(
        "Morgan Lead",
        EmployeeRole.PRODUCT_MANAGER,
        seniority=Seniority.SENIOR,
        assigned_product_id=product.id,
        leadership_score=82,
    )
    engineer = make_employee(
        "Ada Builder",
        EmployeeRole.ENGINEER,
        assigned_product_id=product.id,
    )
    designer = make_employee(
        "Rin Design",
        EmployeeRole.DESIGNER,
        assigned_product_id=product.id,
    )
    state = make_state(product, employees=[manager, engineer, designer])

    baseline_modifier = calculate_product_team_modifier(state.employees, product.id)
    baseline_condition = calculate_team_condition(state.employees)

    first_assignment = apply_action(
        state,
        TurnAction.ASSIGN_MANAGER,
        context=ActionContext(employee_id=engineer.id, manager_id=manager.id),
    )
    second_assignment = apply_action(
        first_assignment.state,
        TurnAction.ASSIGN_MANAGER,
        context=ActionContext(employee_id=designer.id, manager_id=manager.id),
    )

    updated_modifier = calculate_product_team_modifier(
        second_assignment.state.employees,
        product.id,
    )
    updated_condition = calculate_team_condition(second_assignment.state.employees)

    assert updated_condition.managed_headcount > baseline_condition.managed_headcount
    assert updated_modifier.coordination_bonus > baseline_modifier.coordination_bonus


def test_assign_manager_rejects_reporting_cycles() -> None:
    product = make_product("Hierarchy Core")
    leader = make_employee(
        "Morgan Lead",
        EmployeeRole.PRODUCT_MANAGER,
        seniority=Seniority.SENIOR,
        assigned_product_id=product.id,
        leadership_score=84,
    )
    squad_lead = make_employee(
        "Rin Squad",
        EmployeeRole.DESIGNER,
        assigned_product_id=product.id,
        leadership_score=74,
    )
    builder = make_employee(
        "Ada Builder",
        EmployeeRole.ENGINEER,
        assigned_product_id=product.id,
    )
    state = make_state(product, employees=[leader, squad_lead, builder])
    state.action_points_remaining = 4

    managed = apply_action(
        state,
        TurnAction.ASSIGN_MANAGER,
        context=ActionContext(employee_id=squad_lead.id, manager_id=leader.id),
    )
    managed = apply_action(
        managed.state,
        TurnAction.ASSIGN_MANAGER,
        context=ActionContext(employee_id=builder.id, manager_id=squad_lead.id),
    )

    with pytest.raises(ValueError, match="cycle"):
        apply_action(
            managed.state,
            TurnAction.ASSIGN_MANAGER,
            context=ActionContext(employee_id=leader.id, manager_id=squad_lead.id),
        )


def test_governance_tracks_board_ask_and_warning_level() -> None:
    product = make_product("Governance Atlas", bug_level=26, technical_debt=34)
    state = make_state(product)
    state.finance.forecast_runway_turns = 4
    state.finance.board_confidence = 30
    state.support_program.backlog_queue = 30
    state.support_program.escalation_queue = 8
    customer_summary = apply_end_of_turn_customers(
        state.customer_accounts,
        [product],
        current_turn=4,
    )
    operations_summary = calculate_operations_summary(
        state.products,
        state.employees,
        current_turn=state.company.current_turn,
        customer_accounts=state.customer_accounts,
    )

    summary = apply_end_of_turn_governance(
        state,
        resolved_turn=4,
        total_revenue=Decimal("900.00"),
        net_cash_flow=Decimal("-1100.00"),
        customer_summary=customer_summary,
        operations_summary=operations_summary,
    )

    assert state.finance.active_board_ask is BoardAsk.PROFITABILITY
    assert summary.board_warning_level >= 1
    assert state.finance.board_warning_active is True


def test_governance_forced_tradeoff_applies_when_resolution_is_due() -> None:
    product = make_product("Risk Atlas", bug_level=36, technical_debt=30)
    state = make_state(product)
    state.finance.active_board_ask = BoardAsk.RELIABILITY
    state.finance.board_resolution_due = True
    state.finance.board_resolution_window = 2
    state.support_program.backlog_queue = 26
    state.support_program.escalation_queue = 7
    starting_backlog = state.support_program.backlog_queue
    starting_bug_level = state.products[0].bug_level

    customer_summary = apply_end_of_turn_customers(
        state.customer_accounts,
        [product],
        current_turn=4,
    )
    operations_summary = calculate_operations_summary(
        state.products,
        state.employees,
        current_turn=state.company.current_turn,
        customer_accounts=state.customer_accounts,
    )
    summary = apply_end_of_turn_governance(
        state,
        resolved_turn=4,
        total_revenue=Decimal("900.00"),
        net_cash_flow=Decimal("-900.00"),
        customer_summary=customer_summary,
        operations_summary=operations_summary,
    )

    assert summary.forced_tradeoff_active is True
    assert summary.forced_tradeoff_focus is BoardAsk.RELIABILITY
    assert get_governance_tradeoff_focus(state) is BoardAsk.RELIABILITY
    assert state.support_program.backlog_queue < starting_backlog
    assert state.products[0].bug_level < starting_bug_level
    assert "Forced trade-off" in summary.summary


def test_run_price_increase_lifts_product_and_account_revenue() -> None:
    product = make_product(
        "Monetize Me",
        quality=72,
        revenue_per_user=Decimal("50.00"),
        pricing_tier=PricingTier.PREMIUM,
        packaging_strategy=PackagingStrategy.SUITE,
        target_segment=MarketSegment.ENTERPRISE,
    )
    account = CustomerAccount(
        name="Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("1200.00"),
        plan_tier=PricingTier.PREMIUM,
        subscription_package=SubscriptionPackage.GROWTH,
        contract_cadence=ContractCadence.ANNUAL,
        billing_model=ContractBillingModel.SEAT_BASED,
        seat_count=24,
        usage_units=0,
        add_on_count=2,
        annual_prepay=True,
        discount_rate=Decimal("0.0200"),
        satisfaction=78,
        onboarding_health=74,
        support_load=16,
        open_tickets=3,
        sla_breach_risk=10,
        invoice_risk=12,
        failed_payment_risk=8,
        expansion_potential=68,
        renewal_health=73,
        renewal_turn=6,
        churn_risk=16,
        status=CustomerAccountStatus.ACTIVE,
    )
    state = make_state(product, customer_accounts=[account])

    outcome = apply_action(
        state,
        TurnAction.RUN_PRICE_INCREASE,
        context=ActionContext(target_product_id=product.id),
    )

    assert outcome.state.products[0].revenue_per_user > product.revenue_per_user
    assert outcome.state.customer_accounts[0].contract_value > account.contract_value
    assert outcome.state.customer_accounts[0].satisfaction < account.satisfaction


def test_determine_target_subscription_package_uses_catalog_depth() -> None:
    product = make_product(
        "Catalog Engine",
        packaging_strategy=PackagingStrategy.SUITE,
        target_segment=MarketSegment.ENTERPRISE,
        package_catalog_depth=3,
        add_on_catalog_depth=2,
    )
    account = CustomerAccount(
        name="Tiered Buyer",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("1100.00"),
        plan_tier=PricingTier.PREMIUM,
        support_tier=SupportTier.PRIORITY,
        satisfaction=74,
        expansion_potential=64,
        renewal_turn=6,
        churn_risk=18,
        status=CustomerAccountStatus.ACTIVE,
    )

    target_package = determine_target_subscription_package(product, account)

    assert target_package is SubscriptionPackage.ENTERPRISE_SUITE


def test_package_migration_and_catalog_expansion_prepare_accounts() -> None:
    product = make_product(
        "Monetization Grid",
        packaging_strategy=PackagingStrategy.SUITE,
        target_segment=MarketSegment.ENTERPRISE,
        package_catalog_depth=2,
        add_on_catalog_depth=1,
    )
    account = CustomerAccount(
        name="Expansion Buyer",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("980.00"),
        plan_tier=PricingTier.PREMIUM,
        subscription_package=SubscriptionPackage.GROWTH,
        support_tier=SupportTier.PRIORITY,
        contract_cadence=ContractCadence.ANNUAL,
        billing_model=ContractBillingModel.SEAT_BASED,
        seat_count=18,
        usage_units=0,
        add_on_count=1,
        annual_prepay=False,
        discount_rate=Decimal("0.0100"),
        satisfaction=77,
        onboarding_health=70,
        support_load=18,
        open_tickets=2,
        sla_breach_risk=12,
        invoice_risk=14,
        failed_payment_risk=10,
        expansion_potential=66,
        renewal_health=68,
        renewal_turn=6,
        churn_risk=17,
        status=CustomerAccountStatus.ACTIVE,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("6000.00"))
    state.action_points_remaining = 4

    package_expansion = apply_action(
        state,
        TurnAction.EXPAND_PACKAGE_CATALOG,
        context=ActionContext(target_product_id=product.id),
    )
    add_on_expansion = apply_action(
        package_expansion.state,
        TurnAction.EXPAND_ADD_ON_CATALOG,
        context=ActionContext(target_product_id=product.id),
    )
    migrated = apply_action(
        add_on_expansion.state,
        TurnAction.RUN_PACKAGE_MIGRATION,
        context=ActionContext(target_product_id=product.id),
    )

    updated_account = migrated.state.customer_accounts[0]
    assert "prepared 1 account" in package_expansion.message
    assert "primed 1 account" in add_on_expansion.message
    assert updated_account.subscription_package is SubscriptionPackage.ENTERPRISE_SUITE
    assert updated_account.contract_value > account.contract_value
    assert updated_account.annual_prepay is True
    assert updated_account.add_on_count > account.add_on_count


def test_suite_packaging_creates_expansion_drift_before_renewal() -> None:
    product = make_product(
        "Suite Engine",
        target_segment=MarketSegment.ENTERPRISE,
        packaging_strategy=PackagingStrategy.SUITE,
    )
    account = CustomerAccount(
        name="Expansion Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("950.00"),
        plan_tier=PricingTier.PREMIUM,
        subscription_package=SubscriptionPackage.GROWTH,
        contract_cadence=ContractCadence.ANNUAL,
        billing_model=ContractBillingModel.SEAT_BASED,
        seat_count=18,
        usage_units=0,
        add_on_count=1,
        annual_prepay=True,
        discount_rate=Decimal("0.0000"),
        satisfaction=82,
        onboarding_health=78,
        support_load=12,
        open_tickets=2,
        sla_breach_risk=8,
        invoice_risk=8,
        failed_payment_risk=4,
        expansion_potential=72,
        renewal_health=76,
        renewal_turn=10,
        churn_risk=10,
        status=CustomerAccountStatus.ACTIVE,
    )

    summary = apply_end_of_turn_customers(
        [account],
        [product],
        current_turn=3,
        support_program=SupportProgram(),
    )

    assert account.subscription_package is SubscriptionPackage.ENTERPRISE_SUITE
    assert account.add_on_count > 1
    assert summary.expansion_revenue > Decimal("0.00")


def test_reorg_team_reduces_management_gaps() -> None:
    product = make_product("Org Atlas")
    manager = make_employee(
        "Morgan Lead",
        EmployeeRole.PRODUCT_MANAGER,
        seniority=Seniority.SENIOR,
        assigned_product_id=product.id,
        leadership_score=84,
    )
    engineer = make_employee("Ada Builder", EmployeeRole.ENGINEER, assigned_product_id=product.id)
    designer = make_employee("Rin Design", EmployeeRole.DESIGNER, assigned_product_id=product.id)
    marketer = make_employee("Jae Growth", EmployeeRole.MARKETER, assigned_product_id=product.id)
    state = make_state(product, employees=[manager, engineer, designer, marketer])

    before = calculate_team_condition(state.employees)
    outcome = apply_action(state, TurnAction.REORG_TEAM)
    after = calculate_team_condition(outcome.state.employees)

    assert after.managed_headcount > before.managed_headcount
    assert after.org_drag <= before.org_drag
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_team_condition_tracks_layers_and_span_risk() -> None:
    product = make_product("Scale Org")
    leader = make_employee(
        "Core PM",
        EmployeeRole.PRODUCT_MANAGER,
        seniority=Seniority.SENIOR,
        assigned_product_id=product.id,
        leadership_score=86,
    )
    team_lead = make_employee(
        "Lead Eng",
        EmployeeRole.ENGINEER,
        seniority=Seniority.SENIOR,
        assigned_product_id=product.id,
        leadership_score=72,
    )
    reports = [
        make_employee(f"Builder {index}", EmployeeRole.ENGINEER, assigned_product_id=product.id)
        for index in range(1, 6)
    ]
    state = make_state(product, employees=[leader, team_lead, *reports])
    team_lead.manager_id = leader.id
    for report in reports:
        report.manager_id = team_lead.id

    condition = calculate_team_condition(state.employees)

    assert condition.management_layers >= 2
    assert condition.max_span >= 5
    assert condition.span_risk > 0


def test_resolve_turn_org_drag_reduces_board_team_health_score() -> None:
    product = make_product("Org Strain")
    unmanaged_employees = [
        make_employee(
            f"Builder {index}",
            EmployeeRole.ENGINEER,
            assigned_product_id=product.id,
            energy=64,
            morale=62,
        )
        for index in range(1, 6)
    ]
    manager = make_employee(
        "Morgan PM",
        EmployeeRole.PRODUCT_MANAGER,
        seniority=Seniority.SENIOR,
        assigned_product_id=product.id,
        leadership_score=86,
    )
    managed_reports = [
        make_employee(
            f"Managed {index}",
            EmployeeRole.ENGINEER,
            assigned_product_id=product.id,
            energy=64,
            morale=62,
            manager_id=manager.id,
        )
        for index in range(1, 6)
    ]

    unmanaged_state = make_state(product, employees=unmanaged_employees)
    managed_state = make_state(product, employees=[manager, *managed_reports])
    unmanaged_resolution = resolve_turn(unmanaged_state, FixedRandom(7))
    managed_resolution = resolve_turn(managed_state, FixedRandom(7))

    assert (
        unmanaged_resolution.state.finance.board_team_health_score
        < managed_resolution.state.finance.board_team_health_score
    )
    assert unmanaged_resolution.team_condition.org_drag > managed_resolution.team_condition.org_drag


def test_execute_board_response_reliability_resets_pressure() -> None:
    product = make_product("Trust Layer", bug_level=28, technical_debt=34)
    state = make_state(product)
    state.finance.board_pressure = 42
    state.finance.governance_risk = 31
    state.finance.board_warning_active = True
    state.finance.board_warning_level = 2
    state.finance.active_board_ask = BoardAsk.RELIABILITY
    state.support_program.backlog_queue = 20
    state.support_program.escalation_queue = 6

    outcome = apply_action(state, TurnAction.EXECUTE_BOARD_RESPONSE)

    assert outcome.state.support_program.backlog_queue < 20
    assert outcome.state.support_program.escalation_queue < 6
    assert outcome.state.finance.board_pressure < 42
    assert outcome.state.finance.governance_risk < 31


def test_forecast_scenarios_bracket_base_projection() -> None:
    turn_history = [
        TurnLedgerEntry(
            turn=1,
            total_revenue=Decimal("900.00"),
            total_operating_cost=Decimal("1600.00"),
            net_cash_flow=Decimal("-700.00"),
            cash_on_hand=Decimal("6000.00"),
            reputation=50,
            total_users=40,
            headcount=2,
            roadmap_focus=RoadmapFocus.BALANCED_EXECUTION,
        ),
        TurnLedgerEntry(
            turn=2,
            total_revenue=Decimal("920.00"),
            total_operating_cost=Decimal("1720.00"),
            net_cash_flow=Decimal("-800.00"),
            cash_on_hand=Decimal("5200.00"),
            reputation=49,
            total_users=42,
            headcount=2,
            roadmap_focus=RoadmapFocus.BALANCED_EXECUTION,
        ),
    ]

    base, conservative, aggressive = calculate_cash_flow_forecast_scenarios(
        Decimal("4800.00"),
        turn_history,
        latest_net_cash_flow=Decimal("-900.00"),
    )

    assert conservative.projected_net_cash_flow < base.projected_net_cash_flow
    assert aggressive.projected_net_cash_flow > base.projected_net_cash_flow
    assert conservative.projected_runway_turns <= base.projected_runway_turns


def test_appoint_team_lead_sets_flag_and_reduces_succession_blind_spot() -> None:
    product = make_product("Ops Core")
    lead_candidate = make_employee(
        "Rin Lead",
        EmployeeRole.DESIGNER,
        assigned_product_id=product.id,
        leadership_score=72,
    )
    state = make_state(product, employees=[lead_candidate])

    outcome = apply_action(
        state,
        TurnAction.APPOINT_TEAM_LEAD,
        context=ActionContext(employee_id=lead_candidate.id),
    )

    promoted = outcome.state.employees[0]
    condition = calculate_team_condition(outcome.state.employees)
    assert promoted.is_team_lead is True
    assert condition.team_lead_count == 1


def test_route_support_escalation_upgrades_support_tier_and_reduces_risk() -> None:
    product = make_product("Trust Desk", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Escalating Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("980.00"),
        satisfaction=58,
        expansion_potential=60,
        renewal_turn=6,
        churn_risk=42,
        open_tickets=9,
        sla_breach_risk=24,
        escalation_count=2,
        status=CustomerAccountStatus.ACTIVE,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("5000.00"))

    outcome = apply_action(
        state,
        TurnAction.ROUTE_SUPPORT_ESCALATION,
        context=ActionContext(customer_account_id=account.id),
    )

    routed = outcome.state.customer_accounts[0]
    assert routed.support_tier is SupportTier.PRIORITY
    assert routed.open_tickets < account.open_tickets
    assert routed.churn_risk < account.churn_risk
    assert routed.renewal_health > account.renewal_health
    assert routed.satisfaction > account.satisfaction


def test_run_add_on_campaign_expands_healthy_accounts() -> None:
    product = make_product("Bundle Ops", packaging_strategy=PackagingStrategy.MODULAR)
    account = CustomerAccount(
        name="Expansion Desk",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("620.00"),
        satisfaction=76,
        expansion_potential=64,
        renewal_turn=6,
        churn_risk=16,
        add_on_count=1,
        status=CustomerAccountStatus.ACTIVE,
    )
    state = make_state(product, customer_accounts=[account])

    outcome = apply_action(
        state,
        TurnAction.RUN_ADD_ON_CAMPAIGN,
        context=ActionContext(target_product_id=product.id),
    )

    expanded = outcome.state.customer_accounts[0]
    assert expanded.add_on_count > account.add_on_count
    assert expanded.contract_value > account.contract_value
    assert outcome.state.products[0].technical_debt > product.technical_debt


def test_run_package_migration_aligns_accounts_to_packaging_strategy() -> None:
    product = make_product(
        "Migration Suite",
        packaging_strategy=PackagingStrategy.SUITE,
        target_segment=MarketSegment.ENTERPRISE,
    )
    account = CustomerAccount(
        name="Migration Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("920.00"),
        satisfaction=72,
        expansion_potential=70,
        renewal_turn=8,
        churn_risk=14,
        subscription_package=SubscriptionPackage.STARTER,
        status=CustomerAccountStatus.ACTIVE,
    )
    state = make_state(product, customer_accounts=[account])

    outcome = apply_action(
        state,
        TurnAction.RUN_PACKAGE_MIGRATION,
        context=ActionContext(target_product_id=product.id),
    )

    migrated = outcome.state.customer_accounts[0]
    assert migrated.subscription_package is SubscriptionPackage.ENTERPRISE_SUITE
    assert migrated.contract_value > account.contract_value


def test_quarterly_board_review_sets_resolution_and_restructuring_pressure() -> None:
    product = make_product("Board Heat", bug_level=40, technical_debt=44, user_count=120)
    state = make_state(product, current_turn=4)
    state.finance.board_pressure = 58
    state.finance.governance_risk = 52
    state.finance.board_confidence = 28
    state.finance.active_board_ask = BoardAsk.PROFITABILITY
    state.finance.forecast_runway_turns = 4
    state.support_program.backlog_queue = 28

    summary = apply_end_of_turn_governance(
        state,
        resolved_turn=4,
        total_revenue=Decimal("1400.00"),
        net_cash_flow=Decimal("-2100.00"),
        customer_summary=apply_end_of_turn_customers([], [product], current_turn=4),
        operations_summary=calculate_operations_summary(
            state.products,
            state.employees,
            current_turn=4,
            customer_accounts=state.customer_accounts,
            support_backlog_queue=state.support_program.backlog_queue,
        ),
    )

    assert summary.board_resolution is BoardResolution.RESTRUCTURE_NOW
    assert summary.board_resolution_due is True
    assert summary.board_resolution_window == BALANCE.board_resolution_window_turns
    assert state.finance.quarterly_review_count == 1
    assert state.finance.restructuring_pressure > 0


def test_board_resolution_due_expires_into_more_pressure() -> None:
    product = make_product("Board Clock")
    state = make_state(product, current_turn=5)
    state.finance.board_resolution_due = True
    state.finance.board_resolution_window = 1
    starting_pressure = state.finance.board_pressure
    starting_risk = state.finance.governance_risk
    starting_confidence = state.finance.board_confidence

    apply_end_of_turn_governance(
        state,
        resolved_turn=5,
        total_revenue=Decimal("1100.00"),
        net_cash_flow=Decimal("-900.00"),
        customer_summary=apply_end_of_turn_customers([], [product], current_turn=5),
        operations_summary=calculate_operations_summary(
            state.products,
            state.employees,
            current_turn=5,
            customer_accounts=state.customer_accounts,
        ),
    )

    assert state.finance.board_pressure > starting_pressure
    assert state.finance.governance_risk > starting_risk
    assert state.finance.board_confidence < starting_confidence
    assert state.finance.board_resolution_due is True
    assert state.finance.board_resolution_window == BALANCE.board_resolution_window_turns


def test_execute_restructure_plan_cuts_headcount_and_pressure() -> None:
    product = make_product("Reset Core")
    employees = [
        make_employee(
            "Core PM",
            EmployeeRole.PRODUCT_MANAGER,
            seniority=Seniority.SENIOR,
            assigned_product_id=product.id,
            leadership_score=84,
        ),
        make_employee(
            "Low Perf Eng",
            EmployeeRole.ENGINEER,
            assigned_product_id=None,
            productivity=48,
            leadership_score=40,
        ),
        make_employee(
            "Low Perf Design",
            EmployeeRole.DESIGNER,
            assigned_product_id=None,
            productivity=46,
            leadership_score=42,
        ),
        make_employee(
            "Growth Marketer",
            EmployeeRole.MARKETER,
            assigned_product_id=product.id,
            productivity=64,
        ),
    ]
    state = make_state(product, employees=employees, cash_on_hand=Decimal("5000.00"))
    state.finance.restructuring_pressure = 14
    state.finance.board_pressure = 40
    state.finance.governance_risk = 30

    outcome = apply_action(state, TurnAction.EXECUTE_RESTRUCTURE_PLAN)

    assert len(outcome.state.employees) < len(state.employees)
    assert outcome.state.finance.restructuring_pressure < 14
    assert outcome.state.finance.board_pressure < 40


def test_expand_catalog_actions_increase_depth_and_consume_cash() -> None:
    product = make_product(
        "Catalog Core",
        packaging_strategy=PackagingStrategy.MODULAR,
        package_catalog_depth=1,
        add_on_catalog_depth=1,
    )
    state = make_state(product, cash_on_hand=Decimal("4000.00"))

    packaged = apply_action(
        state,
        TurnAction.EXPAND_PACKAGE_CATALOG,
        context=ActionContext(target_product_id=product.id),
    )
    add_ons = apply_action(
        packaged.state,
        TurnAction.EXPAND_ADD_ON_CATALOG,
        context=ActionContext(target_product_id=product.id),
    )

    assert packaged.state.products[0].package_catalog_depth == 2
    assert add_ons.state.products[0].add_on_catalog_depth == 2
    assert add_ons.state.company.cash_on_hand < state.company.cash_on_hand


def test_make_renewal_offer_flags_account_and_pulls_renewal_forward() -> None:
    product = make_product("Renewal Desk")
    account = CustomerAccount(
        name="Renewal Anchor",
        product_id=product.id,
        segment=MarketSegment.STARTUP,
        contract_value=Decimal("640.00"),
        satisfaction=68,
        expansion_potential=58,
        renewal_turn=8,
        churn_risk=22,
        status=CustomerAccountStatus.ACTIVE,
    )
    state = make_state(product, customer_accounts=[account], current_turn=4)

    outcome = apply_action(
        state,
        TurnAction.MAKE_RENEWAL_OFFER,
        context=ActionContext(customer_account_id=account.id),
    )

    renewed = outcome.state.customer_accounts[0]
    assert renewed.renewal_offer_active is True
    assert renewed.renewal_offer_type is RenewalOfferType.LIGHT_DISCOUNT
    assert renewed.renewal_turn <= 6
    assert renewed.discount_rate > account.discount_rate


def test_make_renewal_offer_bundle_upgrade_expands_package_depth() -> None:
    product = make_product("Bundle Renewal")
    account = CustomerAccount(
        name="Bundle Anchor",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("740.00"),
        subscription_package=SubscriptionPackage.STARTER,
        add_on_count=0,
        satisfaction=70,
        expansion_potential=60,
        renewal_turn=7,
        churn_risk=18,
        status=CustomerAccountStatus.ACTIVE,
    )
    state = make_state(product, customer_accounts=[account], current_turn=4)

    outcome = apply_action(
        state,
        TurnAction.MAKE_RENEWAL_OFFER,
        context=ActionContext(
            customer_account_id=account.id,
            renewal_offer_type=RenewalOfferType.BUNDLE_UPGRADE,
        ),
    )

    renewed = outcome.state.customer_accounts[0]
    assert renewed.renewal_offer_type is RenewalOfferType.BUNDLE_UPGRADE
    assert renewed.subscription_package is SubscriptionPackage.GROWTH
    assert renewed.add_on_count == 1


def test_make_renewal_offer_term_extension_locks_longer_contract() -> None:
    product = make_product("Term Renewal")
    account = CustomerAccount(
        name="Term Anchor",
        product_id=product.id,
        segment=MarketSegment.STARTUP,
        contract_value=Decimal("580.00"),
        contract_cadence=ContractCadence.MONTHLY,
        annual_prepay=False,
        satisfaction=66,
        expansion_potential=54,
        renewal_turn=8,
        churn_risk=28,
        status=CustomerAccountStatus.ACTIVE,
    )
    state = make_state(product, customer_accounts=[account], current_turn=4)

    outcome = apply_action(
        state,
        TurnAction.MAKE_RENEWAL_OFFER,
        context=ActionContext(
            customer_account_id=account.id,
            renewal_offer_type=RenewalOfferType.TERM_EXTENSION,
        ),
    )

    renewed = outcome.state.customer_accounts[0]
    assert renewed.renewal_offer_type is RenewalOfferType.TERM_EXTENSION
    assert renewed.contract_cadence is ContractCadence.ANNUAL
    assert renewed.annual_prepay is True


def test_run_win_back_play_restores_churned_account() -> None:
    product = make_product("Winback Core")
    account = CustomerAccount(
        name="Lost Anchor",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("780.00"),
        satisfaction=22,
        expansion_potential=44,
        renewal_turn=4,
        churn_risk=92,
        open_tickets=6,
        status=CustomerAccountStatus.CHURNED,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("5000.00"))

    outcome = apply_action(
        state,
        TurnAction.RUN_WIN_BACK_PLAY,
        context=ActionContext(customer_account_id=account.id),
    )

    restored = outcome.state.customer_accounts[0]
    assert restored.status is CustomerAccountStatus.ACTIVE
    assert restored.win_back_attempts == 1
    assert restored.renewal_turn == state.company.current_turn + 1


def test_support_staffing_investment_increases_capacity_and_turn_service_cost() -> None:
    product = make_product("Support Load")
    account = CustomerAccount(
        name="Support Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("900.00"),
        satisfaction=70,
        expansion_potential=62,
        renewal_turn=5,
        churn_risk=18,
        open_tickets=10,
        sla_breach_risk=44,
        status=CustomerAccountStatus.ACTIVE,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("5000.00"))
    base_capacity = calculate_support_staff_capacity(state)

    invested = apply_action(state, TurnAction.INVEST_IN_SUPPORT_STAFFING)
    resolution = resolve_turn(invested.state, FixedRandom(0))

    assert calculate_support_staff_capacity(invested.state) > base_capacity
    assert resolution.state.support_program.service_cost_last_turn > Decimal("0.00")


def test_start_board_recovery_plan_sets_focus_and_duration() -> None:
    product = make_product("Board Core")
    state = make_state(product, cash_on_hand=Decimal("5000.00"))
    state.finance.board_pressure = 42
    state.finance.governance_risk = 38
    state.finance.active_board_ask = BoardAsk.RELIABILITY

    outcome = apply_action(state, TurnAction.START_BOARD_RECOVERY_PLAN)

    assert outcome.state.finance.board_recovery_focus is BoardAsk.RELIABILITY
    assert outcome.state.finance.board_recovery_turns_remaining == BALANCE.board_recovery_turns
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_start_board_recovery_plan_profitability_shifts_capital_posture() -> None:
    product = make_product("Capital Discipline")
    state = make_state(product, cash_on_hand=Decimal("5200.00"))
    state.finance.board_pressure = 40
    state.finance.active_board_ask = BoardAsk.PROFITABILITY
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.EXPAND,
        source_preference=CapitalSourcePreference.VENTURE,
    )

    outcome = apply_action(state, TurnAction.START_BOARD_RECOVERY_PLAN)

    assert outcome.state.capital_plan.mode is CapitalPlanMode.CONSERVE
    assert outcome.state.capital_plan.source_preference is CapitalSourcePreference.VENTURE


def test_start_board_recovery_plan_reliability_shifts_support_focus_and_tooling() -> None:
    product = make_product("Support Heat")
    account = CustomerAccount(
        name="Billing Heat",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("680.00"),
        satisfaction=62,
        expansion_potential=52,
        renewal_turn=7,
        churn_risk=26,
        invoice_risk=58,
        failed_payment_risk=44,
        dunning_steps=2,
        open_tickets=3,
        status=CustomerAccountStatus.ACTIVE,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("5000.00"))
    state.finance.board_pressure = 40
    state.finance.active_board_ask = BoardAsk.RELIABILITY
    state.support_program.billing_ticket_pressure = 16

    outcome = apply_action(state, TurnAction.START_BOARD_RECOVERY_PLAN)

    assert outcome.state.support_program.lane_focus is SupportLaneFocus.BILLING
    assert outcome.state.support_program.automation_level > state.support_program.automation_level
    assert (
        outcome.state.support_program.knowledge_base_level
        > state.support_program.knowledge_base_level
    )


def test_board_actions_clear_resolution_deadline() -> None:
    product = make_product("Board Relief")
    state = make_state(product, cash_on_hand=Decimal("7000.00"))
    state.finance.board_pressure = 44
    state.finance.governance_risk = 35
    state.finance.active_board_ask = BoardAsk.TEAM_HEALTH
    state.finance.board_resolution_due = True
    state.finance.board_resolution_window = 2

    outcome = apply_action(state, TurnAction.START_BOARD_RECOVERY_PLAN)

    assert outcome.state.finance.board_resolution_due is False
    assert outcome.state.finance.board_resolution_window == 0


def test_governance_crisis_activates_after_repeated_resolution_misses() -> None:
    product = make_product("Crisis Clock")
    state = make_state(product, current_turn=5)
    state.finance.board_pressure = 58
    state.finance.board_confidence = 28
    state.finance.governance_risk = 46
    state.finance.board_resolution_due = True
    state.finance.board_resolution_window = 1
    state.finance.board_resolution_miss_streak = 1
    state.finance.forecast_runway_turns = 5
    state.finance.active_board_ask = BoardAsk.PROFITABILITY

    summary = apply_end_of_turn_governance(
        state,
        resolved_turn=5,
        total_revenue=Decimal("900.00"),
        net_cash_flow=Decimal("-1200.00"),
        customer_summary=apply_end_of_turn_customers([], [product], current_turn=5),
        operations_summary=calculate_operations_summary(
            state.products,
            state.employees,
            current_turn=5,
            customer_accounts=state.customer_accounts,
            support_backlog_queue=state.support_program.backlog_queue,
        ),
    )

    assert state.finance.board_resolution_miss_streak >= 2
    assert state.finance.governance_crisis_active is True
    assert state.finance.governance_crisis_level >= 2
    assert summary.governance_crisis_active is True


def test_support_lane_focus_penalizes_mismatched_queue_mix() -> None:
    product = make_product("Lane Mix")
    enterprise_account = CustomerAccount(
        name="Enterprise Queue",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("1200.00"),
        satisfaction=70,
        expansion_potential=68,
        renewal_turn=7,
        churn_risk=16,
        open_tickets=10,
        support_tier=SupportTier.WHITE_GLOVE,
        status=CustomerAccountStatus.ACTIVE,
    )
    startup_account = CustomerAccount(
        name="Onboarding Queue",
        product_id=product.id,
        segment=MarketSegment.STARTUP,
        contract_value=Decimal("420.00"),
        satisfaction=64,
        onboarding_health=52,
        expansion_potential=52,
        renewal_turn=6,
        churn_risk=24,
        open_tickets=2,
        status=CustomerAccountStatus.ACTIVE,
    )
    state = make_state(
        product,
        customer_accounts=[enterprise_account, startup_account],
    )
    state.support_program.lane_focus = SupportLaneFocus.ONBOARDING

    summary = apply_end_of_turn_support_program(state)

    assert summary.enterprise_ticket_pressure > summary.onboarding_ticket_pressure
    assert summary.focus_mismatch_penalty > 0
    assert state.support_program.enterprise_ticket_pressure == summary.enterprise_ticket_pressure


def test_support_billing_lane_tracks_invoice_and_dunning_pressure() -> None:
    product = make_product("Billing Core")
    account = CustomerAccount(
        name="Collections Anchor",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("620.00"),
        satisfaction=60,
        expansion_potential=48,
        renewal_turn=6,
        churn_risk=28,
        invoice_risk=56,
        failed_payment_risk=48,
        dunning_steps=2,
        open_tickets=2,
        status=CustomerAccountStatus.ACTIVE,
    )
    state = make_state(product, customer_accounts=[account])
    state.support_program.lane_focus = SupportLaneFocus.BILLING

    summary = apply_end_of_turn_support_program(state)

    assert summary.billing_ticket_pressure > 0
    assert state.support_program.billing_ticket_pressure == summary.billing_ticket_pressure
    assert summary.focus_mismatch_penalty == 0


def test_support_lane_snapshots_surface_lane_overflow_when_focus_is_off() -> None:
    product = make_product("Lane Capacity")
    accounts = [
        CustomerAccount(
            name="Enterprise One",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("1200.00"),
            satisfaction=68,
            expansion_potential=60,
            renewal_turn=6,
            churn_risk=18,
            support_tier=SupportTier.WHITE_GLOVE,
            open_tickets=12,
            sla_breach_risk=40,
            status=CustomerAccountStatus.ACTIVE,
        ),
        CustomerAccount(
            name="Enterprise Two",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("1280.00"),
            satisfaction=70,
            expansion_potential=64,
            renewal_turn=6,
            churn_risk=16,
            support_tier=SupportTier.PRIORITY,
            open_tickets=10,
            sla_breach_risk=36,
            status=CustomerAccountStatus.ACTIVE,
        ),
    ]
    state = make_state(product, customer_accounts=accounts)
    state.support_program.lane_focus = SupportLaneFocus.ONBOARDING

    snapshots = calculate_support_lane_snapshots(state)

    assert snapshots[SupportLaneFocus.ENTERPRISE].pressure > 0
    assert snapshots[SupportLaneFocus.ENTERPRISE].overflow > 0
    assert snapshots[SupportLaneFocus.ONBOARDING].capacity > 0


def test_support_lane_staffing_plan_biases_units_toward_billing_focus() -> None:
    product = make_product("Billing Load")
    accounts = [
        CustomerAccount(
            name="Collections A",
            product_id=product.id,
            segment=MarketSegment.SMB,
            contract_value=Decimal("620.00"),
            satisfaction=60,
            expansion_potential=48,
            renewal_turn=6,
            churn_risk=28,
            invoice_risk=56,
            failed_payment_risk=48,
            dunning_steps=2,
            open_tickets=2,
            status=CustomerAccountStatus.ACTIVE,
        ),
        CustomerAccount(
            name="Enterprise Anchor",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("1240.00"),
            satisfaction=70,
            expansion_potential=64,
            renewal_turn=8,
            churn_risk=16,
            support_tier=SupportTier.WHITE_GLOVE,
            open_tickets=8,
            sla_breach_risk=40,
            status=CustomerAccountStatus.ACTIVE,
        ),
    ]
    state = make_state(product, customer_accounts=accounts)
    state.support_program.staffing_level = 4
    state.support_program.lane_focus = SupportLaneFocus.BILLING

    staffing_plan = calculate_support_lane_staffing_plan(state)

    assert staffing_plan[SupportLaneFocus.BILLING] >= staffing_plan[SupportLaneFocus.ONBOARDING]


def test_support_program_service_cost_rises_for_premium_support_tiers() -> None:
    product = make_product("Premium Support")
    priority_account = CustomerAccount(
        name="Priority",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("640.00"),
        satisfaction=66,
        expansion_potential=52,
        renewal_turn=7,
        churn_risk=18,
        support_tier=SupportTier.PRIORITY,
        open_tickets=5,
        status=CustomerAccountStatus.ACTIVE,
    )
    white_glove_account = CustomerAccount(
        name="White Glove",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("1420.00"),
        satisfaction=70,
        expansion_potential=66,
        renewal_turn=9,
        churn_risk=14,
        support_tier=SupportTier.WHITE_GLOVE,
        open_tickets=5,
        status=CustomerAccountStatus.ACTIVE,
    )

    priority_state = make_state(product, customer_accounts=[priority_account])
    white_glove_state = make_state(product, customer_accounts=[white_glove_account])

    priority_summary = apply_end_of_turn_support_program(priority_state)
    white_glove_summary = apply_end_of_turn_support_program(white_glove_state)

    assert white_glove_summary.service_cost > priority_summary.service_cost


def test_run_badges_capture_durable_company_strength() -> None:
    products = [
        make_product("Ops Core", lifecycle_stage=LifecycleStage.MATURE, user_count=180),
        make_product("Growth Edge", user_count=120),
        make_product("Trust Layer", user_count=90),
    ]
    employees = [
        make_employee("Lead PM", EmployeeRole.PRODUCT_MANAGER, seniority=Seniority.SENIOR),
        make_employee("Senior Eng", EmployeeRole.ENGINEER, seniority=Seniority.SENIOR),
        make_employee("Designer", EmployeeRole.DESIGNER),
        make_employee("Marketer", EmployeeRole.MARKETER),
    ]
    accounts = [
        CustomerAccount(
            name="Atlas Bank",
            product_id=products[0].id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("1400.00"),
            satisfaction=80,
            expansion_potential=72,
            renewal_turn=8,
            churn_risk=10,
            status=CustomerAccountStatus.ACTIVE,
        ),
        CustomerAccount(
            name="Northwind Ops",
            product_id=products[1].id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("1180.00"),
            satisfaction=78,
            expansion_potential=66,
            renewal_turn=8,
            churn_risk=12,
            status=CustomerAccountStatus.ACTIVE,
        ),
    ]
    state = make_state(
        *products,
        employees=employees,
        customer_accounts=accounts,
        cash_on_hand=Decimal("18000.00"),
    )
    state.company.reputation = 74
    state.finance.board_confidence = 78
    state.finance.board_reliability_score = 70
    state.finance.board_team_health_score = 73
    state.support_program.enterprise_ticket_pressure = 9
    state.support_program.onboarding_ticket_pressure = 2

    badges = calculate_run_badges(state, calculate_run_score(state))

    assert "capital_disciplined" in badges
    assert "board_trusted" in badges
    assert "enterprise_operator" in badges


def test_run_badges_capture_billing_governance_and_monetization_depth() -> None:
    products = [
        make_product(
            "Billing Suite",
            lifecycle_stage=LifecycleStage.MATURE,
            user_count=140,
            package_catalog_depth=2,
            add_on_catalog_depth=2,
        ),
        make_product("Expansion Hub", user_count=90),
    ]
    accounts = [
        CustomerAccount(
            name="Core Buyer",
            product_id=products[0].id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("1350.00"),
            satisfaction=78,
            expansion_potential=70,
            renewal_turn=7,
            churn_risk=14,
            dunning_steps=0,
            status=CustomerAccountStatus.ACTIVE,
        ),
        CustomerAccount(
            name="Ops Buyer",
            product_id=products[1].id,
            segment=MarketSegment.SMB,
            contract_value=Decimal("640.00"),
            satisfaction=74,
            expansion_potential=58,
            renewal_turn=7,
            churn_risk=16,
            dunning_steps=0,
            status=CustomerAccountStatus.ACTIVE,
        ),
    ]
    state = make_state(*products, customer_accounts=accounts, cash_on_hand=Decimal("9500.00"))
    state.finance.board_confidence = 61
    state.finance.quarterly_review_count = 2
    state.support_program.billing_ticket_pressure = 6
    state.support_program.escalation_queue = 1

    badges = calculate_run_badges(state, calculate_run_score(state))

    assert "billing_operator" in badges
    assert "governance_survivor" in badges
    assert "monetization_architect" in badges


def test_endgame_readiness_surfaces_acquisition_and_ipo_scores() -> None:
    product = make_product(
        "Scale Core",
        lifecycle_stage=LifecycleStage.MATURE,
        user_count=220,
        market_fit=72,
        technical_debt=18,
        bug_level=14,
    )
    accounts = [
        CustomerAccount(
            name="Northwind Bank",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("1680.00"),
            satisfaction=82,
            expansion_potential=74,
            renewal_turn=8,
            churn_risk=10,
            status=CustomerAccountStatus.ACTIVE,
        ),
        CustomerAccount(
            name="Atlas Cloud",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("1440.00"),
            satisfaction=78,
            expansion_potential=68,
            renewal_turn=8,
            churn_risk=12,
            status=CustomerAccountStatus.ACTIVE,
        ),
    ]
    state = make_state(product, customer_accounts=accounts, cash_on_hand=Decimal("22000.00"))
    state.company.reputation = 76
    state.finance.board_confidence = 80
    state.finance.board_score = 78
    state.finance.board_team_health_score = 74
    state.finance.governance_risk = 12
    state.finance.restructuring_pressure = 2

    readiness = calculate_endgame_readiness(state, calculate_run_score(state))

    assert readiness.ipo_readiness_score > 0
    assert readiness.acquisition_interest_score > 0
    assert readiness.independence_score > 0
    assert readiness.strategic_outlook in {
        "ipo_ready",
        "strategic_acquisition",
        "profitable_independence",
    }


def test_exit_evaluation_exposes_board_readout_and_next_chapter() -> None:
    product = make_product(
        "Exit Core",
        lifecycle_stage=LifecycleStage.MATURE,
        user_count=210,
        market_fit=74,
        technical_debt=14,
        bug_level=10,
    )
    state = make_state(product, cash_on_hand=Decimal("26000.00"))
    state.company.reputation = 78
    state.finance.board_confidence = 82
    state.finance.board_score = 79
    state.finance.board_team_health_score = 76
    state.finance.governance_risk = 10
    state.finance.restructuring_pressure = 1

    evaluation = evaluate_exit_outcome(state, calculate_run_score(state))

    assert evaluation.board_readout
    assert evaluation.pressure_readout
    assert len(evaluation.path_scorecard) == 4
    assert evaluation.strategic_clarity in {"clear path", "clear but stressed", "contested"}
    assert evaluation.next_chapter
    assert evaluation.outcome in {
        ExitOutcome.IPO_READY,
        ExitOutcome.STRATEGIC_ACQUISITION,
        ExitOutcome.PROFITABLE_INDEPENDENCE,
        ExitOutcome.RESTRUCTURE,
    }


def test_finance_planner_projects_horizon_cash_positions() -> None:
    product = make_product("Planner Core", user_count=120)
    state = make_state(product, cash_on_hand=Decimal("9000.00"))
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.BALANCED,
        source_preference=CapitalSourcePreference.BOOTSTRAP,
        planning_horizon_turns=6,
        reserve_target=Decimal("5000.00"),
        product_investment_share=35,
        go_to_market_share=35,
        reserve_share=30,
    )
    state.turn_history = [
        TurnLedgerEntry(
            turn=1,
            total_revenue=Decimal("4200.00"),
            total_operating_cost=Decimal("4650.00"),
            net_cash_flow=Decimal("-450.00"),
            cash_on_hand=Decimal("9550.00"),
            reputation=60,
            total_users=110,
            headcount=0,
            roadmap_focus=RoadmapFocus.BALANCED_EXECUTION,
        )
    ]

    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-400.00"),
        capital_plan=state.capital_plan,
    )

    assert planner.horizon_turns == 6
    assert planner.conservative_end_cash <= planner.aggressive_end_cash
    assert planner.recommended_posture in {"conserve", "balanced", "expand"}
    assert planner.reserve_break_risk in {"critical", "high", "elevated", "controlled"}
    assert planner.allocation_signal
    assert len(planner.capital_mix) == 3
    assert planner.funding_posture
    assert planner.dilution_outlook in {
        "no dilution pressure",
        "contained dilution",
        "elevated dilution",
        "heavy dilution",
    }
    assert planner.covenant_outlook in {
        "covenants are controlled",
        "covenants need monitoring",
        "covenants are fragile",
    }
    assert planner.reserve_plan
    assert planner.debt_rollover_signal
    assert planner.funding_window
    assert planner.capital_action_window
    assert planner.tradeoff_note
    assert planner.liquidity_risk
    assert planner.execution_drag
    assert planner.commercial_financing_risk
    assert planner.capital_priority
    assert len(planner.scenario_compare) == 3
    assert planner.action_sequence
    assert planner.allocation_actions
    assert planner.capital_alert
    assert planner.summary


def test_finance_planner_recommends_funding_actions_under_reserve_stress() -> None:
    state = make_state(
        make_product("Planner Stress"),
        cash_on_hand=Decimal("1200.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.EXPAND,
            source_preference=CapitalSourcePreference.VENTURE,
            reserve_target=Decimal("6000.00"),
            product_investment_share=32,
            go_to_market_share=43,
            reserve_share=25,
        ),
    )
    state.finance.investor_pressure = 14
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-900.00"),
        capital_plan=state.capital_plan,
    )

    assert "raise_vc" in planner.recommended_actions
    assert (
        "slow_expansion" in planner.allocation_actions
        or "lift_reserve_share" in planner.allocation_actions
    )
    assert planner.liquidity_risk in {
        "reserve break is imminent",
        "liquidity is fragile",
        "liquidity needs active monitoring",
        "liquidity is controlled",
    }


def test_finance_planner_flags_commercial_financing_risk_and_actions() -> None:
    state = make_state(
        make_product("Capital Stress"),
        cash_on_hand=Decimal("3800.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.EXPAND,
            source_preference=CapitalSourcePreference.ANGEL,
            reserve_target=Decimal("5200.00"),
            product_investment_share=30,
            go_to_market_share=45,
            reserve_share=25,
        ),
    )
    state.finance.covenant_risk = 18
    state.finance.debt_principal = Decimal("2600.00")
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-680.00"),
        capital_plan=state.capital_plan,
        support_backlog=16,
        support_escalations=5,
        revenue_at_risk_value=Decimal("4200.00"),
        renewal_pressure_value=Decimal("2600.00"),
        channel_conflict_index=30,
        channel_dependency_risk=58,
        commercial_dependency_score=72,
        volatile_revenue_share_percent=44,
        enterprise_queue_exposure_value=Decimal("3600.00"),
        renewal_queue_exposure_value=Decimal("2600.00"),
        enterprise_queue_risk_accounts=2,
        renewal_queue_risk_accounts=2,
        premium_queue_risk_accounts=2,
        support_lane_saturation_index=16,
        support_lane_focus=SupportLaneFocus.BALANCED,
        support_hotspot_lane=SupportLaneFocus.ENTERPRISE,
        support_hotspot_lane_overflow=4,
        hotspot_lane_account_count=3,
        focus_alignment_gap=7,
        recovery_drag_score=38,
        paused_dependency_score=66,
        paused_revenue_share_percent=22,
        hotspot_dependency_score=74,
        hotspot_revenue_share_percent=40,
        hotspot_channel="integration",
        hotspot_status_note="integration is the hotspot and is still in recovery mode.",
        strategic_outlook="ipo_ready",
        dominant_endgame_pressure="public_market_scrutiny",
        commercial_fragility=62,
        capital_fragility=54,
    )

    assert planner.commercial_financing_risk in {
        "commercial exposure is large enough to distort funding quality.",
        "commercial strain is now shaping which capital sources remain credible.",
    }
    assert planner.capital_priority in {
        "protect reserve first",
        "stabilize service revenue",
        "de-risk channel mix",
        "hold balanced execution",
    }
    assert "run_channel_firebreak" in planner.recommended_actions
    assert planner.funding_resilience in {
        "funding resilience is durable",
        "funding resilience is workable but exposed",
        "funding resilience is fragile",
    }


def test_finance_planner_flags_onboarding_recovery_for_hotspot_lane() -> None:
    state = make_state(
        make_product("Implementation Pressure"),
        cash_on_hand=Decimal("4200.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.BALANCED,
            source_preference=CapitalSourcePreference.ANGEL,
            reserve_target=Decimal("4800.00"),
            product_investment_share=36,
            go_to_market_share=34,
            reserve_share=30,
        ),
    )
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-420.00"),
        capital_plan=state.capital_plan,
        support_backlog=11,
        support_escalations=3,
        support_lane_focus=SupportLaneFocus.BALANCED,
        support_hotspot_lane=SupportLaneFocus.ONBOARDING,
        support_hotspot_lane_overflow=3,
        hotspot_lane_account_count=2,
        focus_alignment_gap=5,
    )

    assert "run_onboarding_recovery" in planner.recommended_actions
    assert any("onboarding recovery" in step for step in planner.action_sequence)
    assert planner.capital_discipline_index >= 0
    assert "triage_support_backlog" in planner.recommended_actions
    assert "set_support_lane_focus" in planner.recommended_actions
    assert "run_lane_recovery" in planner.recommended_actions
    assert "rebalance_capital" in planner.recommended_actions
    assert "raise_reserve_target" in planner.recommended_actions
    assert planner.support_lane_signal
    assert "misaligned" in planner.lane_focus_note
    assert planner.queue_hotspot_note
    assert planner.capital_rebalance_note


def test_finance_planner_recommends_fast_track_realignment_and_reserve_discipline() -> None:
    state = make_state(
        make_product("Late Game Coordination"),
        cash_on_hand=Decimal("3400.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.BALANCED,
            source_preference=CapitalSourcePreference.DEBT,
            reserve_target=Decimal("5200.00"),
            product_investment_share=36,
            go_to_market_share=40,
            reserve_share=24,
        ),
    )
    state.finance.covenant_risk = 19
    state.finance.debt_principal = Decimal("2800.00")
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-640.00"),
        capital_plan=state.capital_plan,
        support_backlog=12,
        support_escalations=3,
        support_lane_focus=SupportLaneFocus.BALANCED,
        support_hotspot_lane=SupportLaneFocus.ONBOARDING,
        support_hotspot_lane_overflow=3,
        hotspot_lane_account_count=2,
        focus_alignment_gap=5,
        channel_dependency_risk=64,
        paused_dependency_score=66,
        hotspot_dependency_score=76,
        hotspot_revenue_share_percent=41,
        hotspot_channel="integration",
        strategic_outlook="profitable_independence",
        dominant_endgame_pressure="independence_discipline",
        commercial_fragility=61,
        capital_fragility=58,
    )

    assert "run_onboarding_fast_track" in planner.recommended_actions
    assert "run_channel_realignment" in planner.recommended_actions
    assert "step_up_reserve_discipline" in planner.recommended_actions
    assert any("fast-track" in step for step in planner.action_sequence)
    assert any("realign" in step for step in planner.action_sequence)
    assert any("step up reserve discipline" in step for step in planner.action_sequence)


def test_finance_planner_recommends_enterprise_queue_reset_for_ipo_pressure() -> None:
    state = make_state(
        make_product("IPO Operations Core"),
        cash_on_hand=Decimal("3600.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.BALANCED,
            source_preference=CapitalSourcePreference.ANGEL,
            reserve_target=Decimal("5200.00"),
            product_investment_share=34,
            go_to_market_share=40,
            reserve_share=26,
        ),
    )
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-620.00"),
        capital_plan=state.capital_plan,
        support_backlog=13,
        support_escalations=4,
        revenue_at_risk_value=Decimal("2600.00"),
        enterprise_queue_risk_accounts=2,
        support_lane_focus=SupportLaneFocus.BILLING,
        support_hotspot_lane=SupportLaneFocus.ENTERPRISE,
        support_hotspot_lane_overflow=3,
        hotspot_lane_account_count=2,
        focus_alignment_gap=4,
        strategic_outlook="ipo_ready",
        dominant_endgame_pressure="public_market_scrutiny",
        commercial_fragility=64,
        capital_fragility=54,
    )

    assert "run_enterprise_queue_reset" in planner.recommended_actions
    assert any("enterprise queue reset" in step for step in planner.action_sequence)


def test_finance_planner_recommends_channel_synergy_reset_for_acquisition_pressure() -> None:
    state = make_state(
        make_product("Acquisition Pressure Core"),
        cash_on_hand=Decimal("3600.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.EXPAND,
            source_preference=CapitalSourcePreference.DEBT,
            reserve_target=Decimal("5400.00"),
            product_investment_share=34,
            go_to_market_share=42,
            reserve_share=24,
        ),
    )
    state.finance.covenant_risk = 18
    state.finance.debt_principal = Decimal("3200.00")
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-720.00"),
        capital_plan=state.capital_plan,
        support_backlog=13,
        support_escalations=4,
        revenue_at_risk_value=Decimal("2600.00"),
        enterprise_queue_risk_accounts=2,
        support_lane_focus=SupportLaneFocus.BALANCED,
        support_hotspot_lane=SupportLaneFocus.ENTERPRISE,
        support_hotspot_lane_overflow=3,
        hotspot_lane_account_count=2,
        focus_alignment_gap=4,
        channel_conflict_index=31,
        paused_dependency_score=68,
        hotspot_dependency_score=74,
        hotspot_revenue_share_percent=41,
        hotspot_channel="integration",
        strategic_outlook="strategic_acquisition",
        dominant_endgame_pressure="acquirer_diligence",
        commercial_fragility=64,
        capital_fragility=61,
    )

    assert "run_channel_synergy_reset" in planner.recommended_actions
    assert any("synergy reset" in step for step in planner.action_sequence)
    assert "run_enterprise_queue_reset" not in planner.recommended_actions
    assert "harden_financing_posture" not in planner.recommended_actions


def test_finance_planner_recommends_financing_hardening_for_independence_pressure() -> None:
    state = make_state(
        make_product("Independence Finance Core"),
        cash_on_hand=Decimal("3400.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.EXPAND,
            source_preference=CapitalSourcePreference.DEBT,
            reserve_target=Decimal("5200.00"),
            product_investment_share=34,
            go_to_market_share=42,
            reserve_share=24,
        ),
    )
    state.finance.covenant_risk = 18
    state.finance.debt_principal = Decimal("3200.00")
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-740.00"),
        capital_plan=state.capital_plan,
        support_backlog=10,
        support_escalations=3,
        support_lane_focus=SupportLaneFocus.BALANCED,
        support_hotspot_lane=SupportLaneFocus.BILLING,
        support_hotspot_lane_overflow=2,
        hotspot_lane_account_count=1,
        focus_alignment_gap=2,
        renewal_queue_risk_accounts=2,
        renewal_pressure_value=Decimal("2200.00"),
        channel_dependency_risk=48,
        strategic_outlook="profitable_independence",
        dominant_endgame_pressure="independence_discipline",
        commercial_fragility=58,
        capital_fragility=64,
    )

    assert "harden_financing_posture" in planner.recommended_actions
    assert any("harden financing posture" in step for step in planner.action_sequence)


def test_finance_planner_recommends_white_glove_recovery_for_premium_queue_pressure() -> None:
    state = make_state(
        make_product("White Glove Planning Core"),
        cash_on_hand=Decimal("4800.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.BALANCED,
            source_preference=CapitalSourcePreference.ANGEL,
            reserve_target=Decimal("5200.00"),
            product_investment_share=34,
            go_to_market_share=38,
            reserve_share=28,
        ),
    )
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-540.00"),
        capital_plan=state.capital_plan,
        support_backlog=14,
        support_escalations=4,
        revenue_at_risk_value=Decimal("3200.00"),
        high_value_risk_accounts=2,
        enterprise_queue_risk_accounts=2,
        support_lane_focus=SupportLaneFocus.BILLING,
        support_hotspot_lane=SupportLaneFocus.ENTERPRISE,
        support_hotspot_lane_overflow=3,
        hotspot_lane_account_count=2,
        focus_alignment_gap=4,
        strategic_outlook="ipo_ready",
        dominant_endgame_pressure="public_market_scrutiny",
        commercial_fragility=66,
        capital_fragility=48,
    )

    assert "run_white_glove_recovery" in planner.recommended_actions
    assert any("white-glove recovery" in step for step in planner.action_sequence)


def test_finance_planner_recommends_enterprise_reference_cycle_for_flagship_queue_risk() -> None:
    state = make_state(
        make_product("Reference Planning Core"),
        cash_on_hand=Decimal("5000.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.BALANCED,
            source_preference=CapitalSourcePreference.ANGEL,
            reserve_target=Decimal("5200.00"),
            product_investment_share=34,
            go_to_market_share=38,
            reserve_share=28,
        ),
    )
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-580.00"),
        capital_plan=state.capital_plan,
        support_backlog=12,
        support_escalations=4,
        revenue_at_risk_value=Decimal("2600.00"),
        high_value_risk_accounts=2,
        enterprise_queue_risk_accounts=2,
        support_lane_focus=SupportLaneFocus.BALANCED,
        support_hotspot_lane=SupportLaneFocus.ENTERPRISE,
        support_hotspot_lane_overflow=2,
        hotspot_lane_account_count=2,
        focus_alignment_gap=2,
        strategic_outlook="ipo_ready",
        dominant_endgame_pressure="public_market_scrutiny",
        commercial_fragility=64,
        capital_fragility=50,
    )

    assert "run_enterprise_reference_cycle" in planner.recommended_actions
    assert any("enterprise reference cycle" in step for step in planner.action_sequence)


def test_finance_planner_recommends_enterprise_renewal_cabinet_for_flagship_renewal_heat() -> None:
    state = make_state(
        make_product("Renewal Cabinet Planning Core"),
        cash_on_hand=Decimal("5000.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.BALANCED,
            source_preference=CapitalSourcePreference.ANGEL,
            reserve_target=Decimal("5200.00"),
            product_investment_share=34,
            go_to_market_share=38,
            reserve_share=28,
        ),
    )
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-600.00"),
        capital_plan=state.capital_plan,
        support_backlog=11,
        support_escalations=4,
        revenue_at_risk_value=Decimal("2400.00"),
        renewal_pressure_value=Decimal("2300.00"),
        high_value_risk_accounts=1,
        enterprise_queue_risk_accounts=1,
        renewal_queue_risk_accounts=1,
        support_lane_focus=SupportLaneFocus.BALANCED,
        support_hotspot_lane=SupportLaneFocus.ENTERPRISE,
        support_hotspot_lane_overflow=2,
        hotspot_lane_account_count=2,
        focus_alignment_gap=1,
        strategic_outlook="ipo_ready",
        dominant_endgame_pressure="public_market_scrutiny",
        commercial_fragility=66,
        capital_fragility=52,
    )

    assert "run_enterprise_renewal_cabinet" in planner.recommended_actions
    assert any("enterprise renewal cabinet" in step for step in planner.action_sequence)


def test_finance_planner_recommends_partner_margin_reset_for_acquisition_hotspot() -> None:
    state = make_state(
        make_product("Partner Margin Planning Core"),
        cash_on_hand=Decimal("5200.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.EXPAND,
            source_preference=CapitalSourcePreference.DEBT,
            reserve_target=Decimal("5400.00"),
            product_investment_share=34,
            go_to_market_share=42,
            reserve_share=24,
        ),
    )
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-760.00"),
        capital_plan=state.capital_plan,
        support_backlog=12,
        support_escalations=4,
        support_lane_focus=SupportLaneFocus.BALANCED,
        support_hotspot_lane=SupportLaneFocus.ENTERPRISE,
        support_hotspot_lane_overflow=2,
        hotspot_lane_account_count=2,
        focus_alignment_gap=2,
        channel_conflict_index=32,
        paused_dependency_score=62,
        hotspot_dependency_score=76,
        hotspot_revenue_share_percent=43,
        hotspot_channel="integration",
        volatile_revenue_share_percent=26,
        strategic_outlook="strategic_acquisition",
        dominant_endgame_pressure="acquirer_diligence",
        commercial_fragility=68,
        capital_fragility=56,
    )

    assert "run_partner_margin_reset" in planner.recommended_actions
    assert any("partner margins" in step for step in planner.action_sequence)


def test_finance_planner_recommends_channel_stability_reset_for_hotspot_dependency() -> None:
    state = make_state(
        make_product("Channel Stability Planning Core"),
        cash_on_hand=Decimal("5200.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.EXPAND,
            source_preference=CapitalSourcePreference.DEBT,
            reserve_target=Decimal("5400.00"),
            product_investment_share=34,
            go_to_market_share=42,
            reserve_share=24,
        ),
    )
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-700.00"),
        capital_plan=state.capital_plan,
        support_backlog=11,
        support_escalations=3,
        support_lane_focus=SupportLaneFocus.BALANCED,
        support_hotspot_lane=SupportLaneFocus.ENTERPRISE,
        support_hotspot_lane_overflow=2,
        hotspot_lane_account_count=2,
        focus_alignment_gap=2,
        channel_conflict_index=29,
        paused_dependency_score=56,
        hotspot_dependency_score=78,
        hotspot_revenue_share_percent=39,
        volatile_revenue_share_percent=25,
        hotspot_channel="reseller",
        strategic_outlook="strategic_acquisition",
        dominant_endgame_pressure="acquirer_diligence",
        commercial_fragility=66,
        capital_fragility=56,
    )

    assert "run_channel_stability_reset" in planner.recommended_actions
    assert any("channel stability reset" in step for step in planner.action_sequence)


def test_finance_planner_recommends_lock_capital_buffer_for_independence_fragility() -> None:
    state = make_state(
        make_product("Capital Buffer Planning Core"),
        cash_on_hand=Decimal("3800.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.EXPAND,
            source_preference=CapitalSourcePreference.DEBT,
            reserve_target=Decimal("5200.00"),
            product_investment_share=36,
            go_to_market_share=41,
            reserve_share=23,
        ),
    )
    state.finance.debt_principal = Decimal("3600.00")
    state.finance.covenant_risk = 18
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-780.00"),
        capital_plan=state.capital_plan,
        support_backlog=10,
        support_escalations=3,
        support_lane_focus=SupportLaneFocus.BALANCED,
        support_hotspot_lane=SupportLaneFocus.BILLING,
        support_hotspot_lane_overflow=2,
        hotspot_lane_account_count=1,
        focus_alignment_gap=1,
        renewal_queue_risk_accounts=2,
        renewal_pressure_value=Decimal("2400.00"),
        strategic_outlook="profitable_independence",
        dominant_endgame_pressure="independence_discipline",
        commercial_fragility=58,
        capital_fragility=72,
    )

    assert "lock_capital_buffer" in planner.recommended_actions
    assert any("lock a capital buffer" in step for step in planner.action_sequence)


def test_finance_planner_recommends_refinancing_posture_for_debt_heat() -> None:
    state = make_state(
        make_product("Refinancing Planning Core"),
        cash_on_hand=Decimal("3900.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.EXPAND,
            source_preference=CapitalSourcePreference.DEBT,
            reserve_target=Decimal("5200.00"),
            product_investment_share=35,
            go_to_market_share=41,
            reserve_share=24,
        ),
    )
    state.finance.debt_principal = Decimal("3400.00")
    state.finance.covenant_risk = 16
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-760.00"),
        capital_plan=state.capital_plan,
        support_backlog=10,
        support_escalations=3,
        support_lane_focus=SupportLaneFocus.BILLING,
        support_hotspot_lane=SupportLaneFocus.BILLING,
        support_hotspot_lane_overflow=1,
        hotspot_lane_account_count=1,
        focus_alignment_gap=0,
        renewal_queue_risk_accounts=2,
        renewal_pressure_value=Decimal("2300.00"),
        strategic_outlook="profitable_independence",
        dominant_endgame_pressure="independence_discipline",
        commercial_fragility=56,
        capital_fragility=60,
    )

    assert "set_refinancing_posture" in planner.recommended_actions
    assert any("refinancing posture" in step for step in planner.action_sequence)


def test_finance_planner_recommends_white_glove_backstop_for_premium_hotspot() -> None:
    state = make_state(
        make_product("White Glove Backstop Planning Core"),
        cash_on_hand=Decimal("5200.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.BALANCED,
            source_preference=CapitalSourcePreference.ANGEL,
            reserve_target=Decimal("5400.00"),
            product_investment_share=34,
            go_to_market_share=38,
            reserve_share=28,
        ),
    )
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-620.00"),
        capital_plan=state.capital_plan,
        support_backlog=14,
        support_escalations=4,
        revenue_at_risk_value=Decimal("3200.00"),
        premium_revenue_at_risk_value=Decimal("2800.00"),
        high_value_risk_accounts=2,
        enterprise_queue_risk_accounts=2,
        premium_queue_risk_accounts=2,
        support_lane_focus=SupportLaneFocus.BILLING,
        support_hotspot_lane=SupportLaneFocus.ENTERPRISE,
        support_hotspot_lane_overflow=3,
        hotspot_lane_account_count=2,
        focus_alignment_gap=4,
        strategic_outlook="ipo_ready",
        dominant_endgame_pressure="public_market_scrutiny",
        commercial_fragility=70,
        capital_fragility=50,
    )

    assert "run_white_glove_backstop" in planner.recommended_actions
    assert any("white-glove backstop" in step for step in planner.action_sequence)


def test_finance_planner_recommends_reseller_enablement_reset_for_hotspot_lane() -> None:
    state = make_state(
        make_product("Reseller Enablement Planning Core"),
        cash_on_hand=Decimal("5200.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.EXPAND,
            source_preference=CapitalSourcePreference.DEBT,
            reserve_target=Decimal("5400.00"),
            product_investment_share=34,
            go_to_market_share=42,
            reserve_share=24,
        ),
    )
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-700.00"),
        capital_plan=state.capital_plan,
        support_backlog=11,
        support_escalations=3,
        support_lane_focus=SupportLaneFocus.BALANCED,
        support_hotspot_lane=SupportLaneFocus.ENTERPRISE,
        support_hotspot_lane_overflow=2,
        hotspot_lane_account_count=2,
        focus_alignment_gap=2,
        channel_conflict_index=26,
        paused_dependency_score=50,
        hotspot_dependency_score=76,
        hotspot_revenue_share_percent=39,
        volatile_revenue_share_percent=22,
        hotspot_channel="reseller",
        strategic_outlook="strategic_acquisition",
        dominant_endgame_pressure="acquirer_diligence",
        commercial_fragility=66,
        capital_fragility=56,
    )

    assert "run_reseller_enablement_reset" in planner.recommended_actions


def test_finance_planner_recommends_white_glove_renewal_guard_for_premium_renewal_heat() -> None:
    state = make_state(
        make_product("Premium Renewal Planning Core"),
        cash_on_hand=Decimal("5200.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.EXPAND,
            source_preference=CapitalSourcePreference.DEBT,
            reserve_target=Decimal("5400.00"),
            product_investment_share=34,
            go_to_market_share=42,
            reserve_share=24,
        ),
    )
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-680.00"),
        capital_plan=state.capital_plan,
        support_backlog=11,
        support_escalations=3,
        high_value_risk_accounts=1,
        premium_revenue_at_risk_value=Decimal("2600.00"),
        premium_queue_risk_accounts=2,
        renewal_queue_risk_accounts=2,
        renewal_pressure_value=Decimal("2200.00"),
        support_lane_focus=SupportLaneFocus.BILLING,
        support_hotspot_lane=SupportLaneFocus.ENTERPRISE,
        support_hotspot_lane_overflow=2,
        hotspot_lane_account_count=2,
        focus_alignment_gap=2,
        strategic_outlook="ipo_ready",
        dominant_endgame_pressure="public_market_scrutiny",
        commercial_fragility=66,
        capital_fragility=50,
    )

    assert "run_white_glove_renewal_guard" in planner.recommended_actions
    assert any("white-glove renewal guard" in step for step in planner.action_sequence)


def test_finance_planner_recommends_white_glove_reference_ring_for_flagship_pressure() -> None:
    state = make_state(
        make_product("White Glove Reference Planning Core"),
        cash_on_hand=Decimal("5200.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.BALANCED,
            source_preference=CapitalSourcePreference.ANGEL,
            reserve_target=Decimal("5400.00"),
            product_investment_share=34,
            go_to_market_share=38,
            reserve_share=28,
        ),
    )
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-660.00"),
        capital_plan=state.capital_plan,
        support_backlog=12,
        support_escalations=4,
        high_value_risk_accounts=2,
        premium_revenue_at_risk_value=Decimal("2800.00"),
        white_glove_queue_risk_accounts=1,
        premium_queue_risk_accounts=2,
        renewal_queue_risk_accounts=2,
        renewal_pressure_value=Decimal("2200.00"),
        support_lane_focus=SupportLaneFocus.BILLING,
        support_hotspot_lane=SupportLaneFocus.ENTERPRISE,
        support_hotspot_lane_overflow=2,
        hotspot_lane_account_count=2,
        focus_alignment_gap=2,
        strategic_outlook="ipo_ready",
        dominant_endgame_pressure="public_market_scrutiny",
        commercial_fragility=68,
        capital_fragility=52,
    )

    assert "run_white_glove_reference_ring" in planner.recommended_actions
    assert any("white-glove reference ring" in step for step in planner.action_sequence)


def test_finance_planner_recommends_white_glove_reference_committee_for_flagship_heat() -> None:
    state = make_state(
        make_product("White Glove Reference Committee Planning Core"),
        cash_on_hand=Decimal("5400.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.BALANCED,
            source_preference=CapitalSourcePreference.ANGEL,
            reserve_target=Decimal("5600.00"),
            product_investment_share=34,
            go_to_market_share=37,
            reserve_share=29,
        ),
    )
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-690.00"),
        capital_plan=state.capital_plan,
        support_backlog=13,
        support_escalations=4,
        high_value_risk_accounts=2,
        premium_revenue_at_risk_value=Decimal("3100.00"),
        white_glove_queue_risk_accounts=2,
        premium_queue_risk_accounts=2,
        support_lane_focus=SupportLaneFocus.BILLING,
        support_hotspot_lane=SupportLaneFocus.ENTERPRISE,
        support_hotspot_lane_overflow=3,
        hotspot_lane_account_count=2,
        focus_alignment_gap=3,
        strategic_outlook="ipo_ready",
        dominant_endgame_pressure="public_market_scrutiny",
        commercial_fragility=72,
        capital_fragility=54,
    )

    assert "run_white_glove_reference_committee" in planner.recommended_actions


def test_finance_planner_recommends_white_glove_escalation_cell_for_extreme_premium_heat() -> None:
    state = make_state(
        make_product("White Glove Escalation Planning Core"),
        cash_on_hand=Decimal("5600.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.BALANCED,
            source_preference=CapitalSourcePreference.ANGEL,
            reserve_target=Decimal("5800.00"),
            product_investment_share=34,
            go_to_market_share=37,
            reserve_share=29,
        ),
    )
    state.finance.board_pressure = 28
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-710.00"),
        capital_plan=state.capital_plan,
        support_backlog=14,
        support_escalations=4,
        high_value_risk_accounts=2,
        premium_revenue_at_risk_value=Decimal("3200.00"),
        white_glove_queue_risk_accounts=2,
        premium_queue_risk_accounts=2,
        renewal_queue_risk_accounts=2,
        renewal_pressure_value=Decimal("2200.00"),
        support_lane_focus=SupportLaneFocus.BILLING,
        support_hotspot_lane=SupportLaneFocus.ENTERPRISE,
        support_hotspot_lane_overflow=3,
        hotspot_lane_account_count=2,
        focus_alignment_gap=3,
        strategic_outlook="ipo_ready",
        dominant_endgame_pressure="public_market_scrutiny",
        commercial_fragility=74,
        capital_fragility=56,
    )

    assert "run_white_glove_escalation_cell" in planner.recommended_actions
    assert any("white-glove escalation cell" in step for step in planner.action_sequence)


def test_finance_planner_recommends_billing_covenant_reset_for_independence_heat() -> None:
    state = make_state(
        make_product("Billing Covenant Planning Core"),
        cash_on_hand=Decimal("4900.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.EXPAND,
            source_preference=CapitalSourcePreference.DEBT,
            reserve_target=Decimal("6000.00"),
            product_investment_share=34,
            go_to_market_share=42,
            reserve_share=24,
        ),
    )
    state.finance.covenant_risk = 16
    state.finance.investor_pressure = 18
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-740.00"),
        capital_plan=state.capital_plan,
        support_backlog=10,
        support_escalations=3,
        renewal_queue_risk_accounts=2,
        renewal_pressure_value=Decimal("2500.00"),
        support_lane_focus=SupportLaneFocus.ONBOARDING,
        support_hotspot_lane=SupportLaneFocus.BILLING,
        support_hotspot_lane_overflow=2,
        hotspot_lane_account_count=2,
        focus_alignment_gap=2,
        strategic_outlook="profitable_independence",
        dominant_endgame_pressure="independence_discipline",
        commercial_fragility=66,
        capital_fragility=68,
    )

    assert "run_billing_covenant_reset" in planner.recommended_actions


def test_finance_planner_recommends_billing_dispute_desk_for_billing_capital_heat() -> None:
    state = make_state(
        make_product("Billing Dispute Planning Core"),
        cash_on_hand=Decimal("5000.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.EXPAND,
            source_preference=CapitalSourcePreference.DEBT,
            reserve_target=Decimal("6100.00"),
            product_investment_share=34,
            go_to_market_share=42,
            reserve_share=24,
        ),
    )
    state.finance.covenant_risk = 18
    state.finance.debt_principal = Decimal("3400.00")
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-760.00"),
        capital_plan=state.capital_plan,
        support_backlog=10,
        support_escalations=3,
        renewal_queue_risk_accounts=2,
        renewal_pressure_value=Decimal("2500.00"),
        support_lane_focus=SupportLaneFocus.ONBOARDING,
        support_hotspot_lane=SupportLaneFocus.BILLING,
        support_hotspot_lane_overflow=2,
        hotspot_lane_account_count=2,
        focus_alignment_gap=2,
        strategic_outlook="profitable_independence",
        dominant_endgame_pressure="independence_discipline",
        commercial_fragility=68,
        capital_fragility=70,
    )

    assert "run_billing_dispute_desk" in planner.recommended_actions
    assert any("billing dispute desk" in step for step in planner.action_sequence)


def test_finance_planner_recommends_onboarding_control_tower_for_multi_account_drag() -> None:
    state = make_state(
        make_product("Onboarding Tower Planning Core"),
        cash_on_hand=Decimal("5200.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.BALANCED,
            source_preference=CapitalSourcePreference.ANGEL,
            reserve_target=Decimal("5400.00"),
            product_investment_share=34,
            go_to_market_share=38,
            reserve_share=28,
        ),
    )
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-640.00"),
        capital_plan=state.capital_plan,
        support_backlog=13,
        support_escalations=4,
        revenue_at_risk_value=Decimal("2000.00"),
        support_lane_focus=SupportLaneFocus.BALANCED,
        support_hotspot_lane=SupportLaneFocus.ONBOARDING,
        support_hotspot_lane_overflow=3,
        hotspot_lane_account_count=3,
        focus_alignment_gap=3,
        strategic_outlook="ipo_ready",
        dominant_endgame_pressure="public_market_scrutiny",
        commercial_fragility=64,
        capital_fragility=50,
    )

    assert "run_onboarding_control_tower" in planner.recommended_actions
    assert any("onboarding control tower" in step for step in planner.action_sequence)


def test_finance_planner_recommends_endgame_capital_map_for_board_reset_heat() -> None:
    state = make_state(
        make_product("Endgame Capital Map Planning Core"),
        cash_on_hand=Decimal("5200.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.EXPAND,
            source_preference=CapitalSourcePreference.DEBT,
            reserve_target=Decimal("5500.00"),
            product_investment_share=36,
            go_to_market_share=42,
            reserve_share=22,
        ),
    )
    state.finance.board_pressure = 30
    state.finance.governance_risk = 44
    state.finance.restructuring_pressure = 18
    state.finance.board_warning_level = 2
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-810.00"),
        capital_plan=state.capital_plan,
        support_backlog=14,
        support_escalations=4,
        support_lane_focus=SupportLaneFocus.BILLING,
        support_hotspot_lane=SupportLaneFocus.ENTERPRISE,
        support_hotspot_lane_overflow=3,
        hotspot_lane_account_count=2,
        focus_alignment_gap=3,
        channel_conflict_index=30,
        paused_dependency_score=46,
        hotspot_dependency_score=74,
        hotspot_revenue_share_percent=39,
        volatile_revenue_share_percent=24,
        hotspot_channel="reseller",
        strategic_outlook="board_reset",
        dominant_endgame_pressure="board_reset_risk",
        commercial_fragility=70,
        capital_fragility=72,
    )

    assert "set_endgame_capital_map" in planner.recommended_actions


def test_finance_planner_recommends_exit_readiness_buffer_for_path_heat() -> None:
    state = make_state(
        make_product("Exit Buffer Planning Core"),
        cash_on_hand=Decimal("5200.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.EXPAND,
            source_preference=CapitalSourcePreference.DEBT,
            reserve_target=Decimal("5600.00"),
            product_investment_share=36,
            go_to_market_share=42,
            reserve_share=22,
        ),
    )
    state.finance.board_pressure = 28
    state.finance.governance_risk = 48
    state.finance.covenant_risk = 16
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-820.00"),
        capital_plan=state.capital_plan,
        support_backlog=14,
        support_escalations=4,
        support_lane_focus=SupportLaneFocus.BILLING,
        support_hotspot_lane=SupportLaneFocus.ENTERPRISE,
        support_hotspot_lane_overflow=3,
        hotspot_lane_account_count=2,
        focus_alignment_gap=3,
        channel_conflict_index=30,
        paused_dependency_score=46,
        hotspot_dependency_score=74,
        hotspot_revenue_share_percent=39,
        volatile_revenue_share_percent=24,
        hotspot_channel="reseller",
        strategic_outlook="board_reset",
        dominant_endgame_pressure="board_reset_risk",
        commercial_fragility=72,
        capital_fragility=74,
    )

    assert "set_exit_readiness_buffer" in planner.recommended_actions
    assert any("exit-readiness buffer" in step for step in planner.action_sequence)


def test_finance_planner_recommends_integration_cutover_reset_for_hotspot_lane() -> None:
    state = make_state(
        make_product("Integration Planning Core"),
        cash_on_hand=Decimal("5200.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.EXPAND,
            source_preference=CapitalSourcePreference.DEBT,
            reserve_target=Decimal("5400.00"),
            product_investment_share=34,
            go_to_market_share=42,
            reserve_share=24,
        ),
    )
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-710.00"),
        capital_plan=state.capital_plan,
        support_backlog=10,
        support_escalations=3,
        support_lane_focus=SupportLaneFocus.ONBOARDING,
        support_hotspot_lane=SupportLaneFocus.ONBOARDING,
        support_hotspot_lane_overflow=2,
        hotspot_lane_account_count=2,
        focus_alignment_gap=1,
        channel_conflict_index=28,
        paused_dependency_score=44,
        hotspot_dependency_score=76,
        hotspot_revenue_share_percent=31,
        volatile_revenue_share_percent=18,
        hotspot_channel="integration",
        strategic_outlook="strategic_acquisition",
        dominant_endgame_pressure="acquirer_diligence",
        commercial_fragility=64,
        capital_fragility=56,
    )

    assert "run_integration_cutover_reset" in planner.recommended_actions


def test_finance_planner_recommends_marketplace_chargeback_reset_for_billing_lane() -> None:
    state = make_state(
        make_product("Marketplace Chargeback Planning Core"),
        cash_on_hand=Decimal("5200.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.EXPAND,
            source_preference=CapitalSourcePreference.DEBT,
            reserve_target=Decimal("5400.00"),
            product_investment_share=34,
            go_to_market_share=42,
            reserve_share=24,
        ),
    )
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-720.00"),
        capital_plan=state.capital_plan,
        support_backlog=10,
        support_escalations=3,
        support_lane_focus=SupportLaneFocus.BILLING,
        support_hotspot_lane=SupportLaneFocus.BILLING,
        support_hotspot_lane_overflow=2,
        hotspot_lane_account_count=2,
        focus_alignment_gap=1,
        renewal_queue_risk_accounts=2,
        renewal_pressure_value=Decimal("2600.00"),
        channel_conflict_index=18,
        paused_dependency_score=58,
        hotspot_dependency_score=64,
        hotspot_revenue_share_percent=28,
        volatile_revenue_share_percent=26,
        hotspot_channel="marketplace",
        strategic_outlook="strategic_acquisition",
        dominant_endgame_pressure="acquirer_diligence",
        commercial_fragility=64,
        capital_fragility=54,
    )

    assert "run_marketplace_chargeback_reset" in planner.recommended_actions


def test_finance_planner_recommends_covenant_firewall_for_heat() -> None:
    state = make_state(
        make_product("Covenant Firewall Planning Core"),
        cash_on_hand=Decimal("4200.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.EXPAND,
            source_preference=CapitalSourcePreference.DEBT,
            reserve_target=Decimal("5200.00"),
            product_investment_share=35,
            go_to_market_share=41,
            reserve_share=24,
        ),
    )
    state.finance.debt_principal = Decimal("3600.00")
    state.finance.covenant_risk = 18
    state.finance.board_pressure = 30
    state.finance.governance_risk = 52
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-820.00"),
        capital_plan=state.capital_plan,
        support_backlog=12,
        support_escalations=4,
        support_lane_focus=SupportLaneFocus.BILLING,
        support_hotspot_lane=SupportLaneFocus.BILLING,
        support_hotspot_lane_overflow=2,
        hotspot_lane_account_count=2,
        focus_alignment_gap=1,
        renewal_queue_risk_accounts=2,
        renewal_pressure_value=Decimal("2400.00"),
        strategic_outlook="profitable_independence",
        dominant_endgame_pressure="independence_discipline",
        commercial_fragility=60,
        capital_fragility=66,
    )

    assert "set_covenant_firewall" in planner.recommended_actions
    assert any("covenant firewall" in step for step in planner.action_sequence)


def test_finance_planner_recommends_debt_strategy_for_heavy_covenant_heat() -> None:
    state = make_state(
        make_product("Debt Strategy Planning Core"),
        cash_on_hand=Decimal("4400.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.EXPAND,
            source_preference=CapitalSourcePreference.DEBT,
            reserve_target=Decimal("5200.00"),
            product_investment_share=35,
            go_to_market_share=41,
            reserve_share=24,
        ),
    )
    state.finance.debt_principal = Decimal("3800.00")
    state.finance.covenant_risk = 22
    state.finance.board_pressure = 32
    state.finance.governance_risk = 54
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-840.00"),
        capital_plan=state.capital_plan,
        support_backlog=12,
        support_escalations=4,
        support_lane_focus=SupportLaneFocus.BILLING,
        support_hotspot_lane=SupportLaneFocus.BILLING,
        support_hotspot_lane_overflow=2,
        hotspot_lane_account_count=2,
        focus_alignment_gap=1,
        renewal_queue_risk_accounts=2,
        renewal_pressure_value=Decimal("2400.00"),
        strategic_outlook="profitable_independence",
        dominant_endgame_pressure="independence_discipline",
        commercial_fragility=60,
        capital_fragility=68,
    )

    assert "set_debt_strategy" in planner.recommended_actions
    assert any("debt strategy" in step for step in planner.action_sequence)


def test_finance_planner_recommends_growth_firebreak_for_capital_fragility() -> None:
    state = make_state(
        make_product("Growth Firebreak Planning Core"),
        cash_on_hand=Decimal("4300.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.EXPAND,
            source_preference=CapitalSourcePreference.DEBT,
            reserve_target=Decimal("5200.00"),
            product_investment_share=35,
            go_to_market_share=41,
            reserve_share=24,
        ),
    )
    state.finance.board_pressure = 30
    state.finance.governance_risk = 50
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-840.00"),
        capital_plan=state.capital_plan,
        support_backlog=12,
        support_escalations=4,
        support_lane_focus=SupportLaneFocus.ENTERPRISE,
        support_hotspot_lane=SupportLaneFocus.ENTERPRISE,
        support_hotspot_lane_overflow=2,
        hotspot_lane_account_count=2,
        focus_alignment_gap=1,
        strategic_outlook="profitable_independence",
        dominant_endgame_pressure="independence_discipline",
        commercial_fragility=60,
        capital_fragility=68,
    )

    assert "set_growth_firebreak" in planner.recommended_actions
    assert any("growth firebreak" in step for step in planner.action_sequence)


def test_finance_planner_recommends_path_capital_posture_for_path_heat() -> None:
    state = make_state(
        make_product("Path Posture Planning Core"),
        cash_on_hand=Decimal("4300.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.EXPAND,
            source_preference=CapitalSourcePreference.DEBT,
            reserve_target=Decimal("5200.00"),
            product_investment_share=35,
            go_to_market_share=41,
            reserve_share=24,
        ),
    )
    state.finance.board_pressure = 28
    state.finance.governance_risk = 46
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-820.00"),
        capital_plan=state.capital_plan,
        support_backlog=12,
        support_escalations=4,
        enterprise_queue_risk_accounts=2,
        support_lane_focus=SupportLaneFocus.BALANCED,
        support_hotspot_lane=SupportLaneFocus.ENTERPRISE,
        support_hotspot_lane_overflow=2,
        hotspot_lane_account_count=2,
        focus_alignment_gap=2,
        hotspot_dependency_score=70,
        strategic_outlook="ipo_ready",
        dominant_endgame_pressure="public_market_scrutiny",
        commercial_fragility=64,
        capital_fragility=66,
    )

    assert "set_path_capital_posture" in planner.recommended_actions
    assert any("path capital posture" in step for step in planner.action_sequence)


def test_finance_planner_flags_reference_and_conflict_reset_actions() -> None:
    state = make_state(
        make_product("Exit Pressure"),
        cash_on_hand=Decimal("4600.00"),
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.BALANCED,
            source_preference=CapitalSourcePreference.ANGEL,
            reserve_target=Decimal("5200.00"),
            product_investment_share=34,
            go_to_market_share=38,
            reserve_share=28,
        ),
    )
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-560.00"),
        capital_plan=state.capital_plan,
        support_backlog=14,
        support_escalations=4,
        revenue_at_risk_value=Decimal("2600.00"),
        enterprise_queue_risk_accounts=2,
        support_hotspot_lane=SupportLaneFocus.ENTERPRISE,
        support_hotspot_lane_overflow=3,
        hotspot_lane_account_count=2,
        channel_conflict_index=32,
        hotspot_dependency_score=74,
        paused_dependency_score=68,
        hotspot_revenue_share_percent=42,
        hotspot_channel="reseller",
        strategic_outlook="strategic_acquisition",
        dominant_endgame_pressure="acquirer_diligence",
        commercial_fragility=66,
        capital_fragility=50,
    )

    assert "run_reference_rescue" in planner.recommended_actions
    assert "run_channel_conflict_reset" in planner.recommended_actions
    assert any("reference rescue" in step for step in planner.action_sequence)
    assert any("channel conflict" in step for step in planner.action_sequence)


def test_bridge_round_event_applies_cash_and_dilution() -> None:
    product = make_product("Bridge Core")
    capital_plan = CapitalPlan(
        mode=CapitalPlanMode.EXPAND,
        source_preference=CapitalSourcePreference.VENTURE,
    )
    state = make_state(
        product,
        capital_plan=capital_plan,
        cash_on_hand=Decimal("1800.00"),
        current_turn=9,
    )
    state.finance.investor_pressure = 20
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "bridge_round"
    )
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "take_bridge")

    assert outcome.state.company.cash_on_hand > state.company.cash_on_hand
    assert outcome.state.finance.equity_dilution > state.finance.equity_dilution
    assert outcome.history_entry.event_id == "bridge_round"


def test_exit_interest_event_rewards_strong_company_signal() -> None:
    product = make_product(
        "Exit Core",
        lifecycle_stage=LifecycleStage.MATURE,
        user_count=220,
        quality=74,
        market_fit=72,
    )
    state = make_state(product, cash_on_hand=Decimal("22000.00"), current_turn=12)
    state.company.reputation = 76
    state.finance.board_confidence = 80
    state.finance.board_score = 78
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "exit_interest"
    )
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "explore_interest")

    assert outcome.state.company.cash_on_hand > state.company.cash_on_hand
    assert outcome.state.company.reputation >= state.company.reputation
    assert outcome.history_entry.event_id == "exit_interest"


def test_strategic_crossroads_event_can_formalize_late_game_path() -> None:
    product = make_product(
        "Crossroads Core",
        lifecycle_stage=LifecycleStage.MATURE,
        user_count=240,
        quality=76,
        market_fit=74,
    )
    state = make_state(product, cash_on_hand=Decimal("18400.00"), current_turn=11)
    state.company.reputation = 74
    state.finance.board_confidence = 77
    state.finance.board_score = 73
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "strategic_crossroads"
    )
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "formalize_process")

    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.history_entry.event_id == "strategic_crossroads"


def test_public_market_scrutiny_event_can_fund_control_response() -> None:
    product = make_product(
        "Listing Core",
        lifecycle_stage=LifecycleStage.MATURE,
        user_count=260,
        quality=78,
        market_fit=76,
    )
    state = make_state(product, cash_on_hand=Decimal("16000.00"), current_turn=12)
    state.company.reputation = 78
    state.finance.board_confidence = 74
    state.finance.board_score = 75
    state.finance.board_pressure = 20
    state.finance.governance_risk = 18
    state.support_program.sla_breaches_last_turn = 4
    pressure = calculate_endgame_pressure(state)

    assert (
        pressure.public_market_scrutiny >= BALANCE.event_public_market_scrutiny_pressure_threshold
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "public_market_scrutiny"
    )
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "tighten_controls")

    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.governance_risk < state.finance.governance_risk
    assert outcome.history_entry.event_id == "public_market_scrutiny"


def test_public_market_scrutiny_event_requires_ipo_outlook() -> None:
    product = make_product(
        "Durable Core",
        lifecycle_stage=LifecycleStage.MATURE,
        user_count=78,
        quality=64,
        market_fit=60,
    )
    account = CustomerAccount(
        name="Independence Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("1800.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=66,
        onboarding_health=60,
        support_load=34,
        open_tickets=10,
        sla_breach_risk=62,
        renewal_health=60,
        expansion_potential=58,
        renewal_turn=15,
        churn_risk=28,
        status=CustomerAccountStatus.ACTIVE,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("24000.00"))
    state.company.current_turn = 16
    state.company.reputation = 82
    state.finance.board_confidence = 16
    state.finance.board_score = 18
    state.finance.board_pressure = 34
    state.finance.governance_risk = 28
    state.finance.board_team_health_score = 82
    state.support_program.sla_breaches_last_turn = 5
    state.support_program.escalation_queue = 4
    state.support_program.queue_age_pressure = 6

    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state, readiness)
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "public_market_scrutiny"
    )

    assert readiness.strategic_outlook == "profitable_independence"
    assert (
        pressure.public_market_scrutiny >= BALANCE.event_public_market_scrutiny_pressure_threshold
    )
    assert definition.is_eligible(state) is False


def test_ipo_audit_committee_event_triggers_after_public_market_scrutiny() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="ipo_readiness_launchpad",
    )
    product = state.products[0]
    state.company.current_turn = 18
    state.finance.board_resolution_due = True
    state.finance.board_confidence = 82
    state.finance.board_score = 78
    state.finance.board_pressure = 30
    state.finance.governance_risk = 12
    state.finance.investor_pressure = 24
    state.finance.missed_board_targets = 2
    state.finance.board_team_health_score = 44
    state.capital_plan.reserve_target = Decimal("26000.00")
    state.support_program.sla_breaches_last_turn = 5
    state.support_program.backlog_queue = 8
    state.event_history.append(
        EventHistoryEntry(
            event_id="public_market_scrutiny",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Public-Market Scrutiny",
            triggered_turn=17,
            resolved_turn=17,
            selected_option_id="tighten_controls",
            selected_option_label="Tighten controls",
            result_text="Controls tightened.",
        )
    )
    state.customer_accounts = [
        CustomerAccount(
            name="IPO Anchor",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("2600.00"),
            support_tier=SupportTier.WHITE_GLOVE,
            satisfaction=60,
            onboarding_health=56,
            support_load=34,
            open_tickets=8,
            sla_breach_risk=62,
            renewal_health=58,
            expansion_potential=64,
            renewal_turn=8,
            churn_risk=22,
            ticket_queue_age=4,
            status=CustomerAccountStatus.ACTIVE,
        )
    ]
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "ipo_audit_committee"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "fund_audit_readiness")

    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.governance_risk < state.finance.governance_risk
    assert outcome.history_entry.event_id == "ipo_audit_committee"


def test_ipo_reference_crack_event_can_fund_reference_reset() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="ipo_readiness_launchpad",
    )
    product = state.products[0]
    state.company.current_turn = 19
    state.company.cash_on_hand = Decimal("6800.00")
    state.finance.board_confidence = 72
    state.finance.board_score = 70
    state.finance.board_pressure = 28
    state.finance.governance_risk = 14
    state.support_program.backlog_queue = 7
    state.support_program.escalation_queue = 4
    state.support_program.queue_age_pressure = 5
    state.event_history.append(
        EventHistoryEntry(
            event_id="ipo_audit_committee",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="IPO Audit Committee",
            triggered_turn=18,
            resolved_turn=18,
            selected_option_id="fund_audit_readiness",
            selected_option_label="Fund audit readiness",
            result_text="Readiness funded.",
        )
    )
    state.customer_accounts = [
        CustomerAccount(
            name="Flagship Reference",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("3400.00"),
            support_tier=SupportTier.PRIORITY,
            satisfaction=58,
            onboarding_health=54,
            support_load=30,
            open_tickets=6,
            sla_breach_risk=66,
            renewal_health=46,
            expansion_potential=70,
            renewal_turn=8,
            churn_risk=26,
            ticket_queue_age=4,
            status=CustomerAccountStatus.AT_RISK,
        )
    ]
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "ipo_reference_crack"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "fund_reference_reset")

    updated_account = outcome.state.customer_accounts[0]
    assert updated_account.support_tier is SupportTier.WHITE_GLOVE
    assert updated_account.sla_breach_risk < state.customer_accounts[0].sla_breach_risk
    assert updated_account.renewal_health > state.customer_accounts[0].renewal_health
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.history_entry.event_id == "ipo_reference_crack"


def test_ipo_listing_window_event_can_slow_and_certify() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="ipo_readiness_launchpad",
    )
    product = state.products[0]
    state.company.current_turn = 20
    state.company.cash_on_hand = Decimal("4200.00")
    state.company.reputation = 78
    state.finance.board_confidence = 58
    state.finance.board_score = 56
    state.finance.board_pressure = 30
    state.finance.governance_risk = 22
    state.support_program.backlog_queue = 8
    state.support_program.escalation_queue = 4
    state.event_history.append(
        EventHistoryEntry(
            event_id="ipo_reference_crack",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="IPO Reference Crack",
            triggered_turn=19,
            resolved_turn=19,
            selected_option_id="fund_reference_reset",
            selected_option_label="Fund a reference reset",
            result_text="Reference path stabilized.",
        )
    )
    state.customer_accounts = [
        CustomerAccount(
            name="IPO Window Anchor",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("2800.00"),
            support_tier=SupportTier.WHITE_GLOVE,
            satisfaction=60,
            onboarding_health=54,
            support_load=32,
            open_tickets=6,
            sla_breach_risk=58,
            renewal_health=56,
            expansion_potential=68,
            renewal_turn=9,
            churn_risk=20,
            ticket_queue_age=4,
            status=CustomerAccountStatus.ACTIVE,
        )
    ]
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "ipo_listing_window"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "slow_and_certify")

    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.governance_risk < state.finance.governance_risk
    assert outcome.history_entry.event_id == "ipo_listing_window"


def test_ipo_governance_lockstep_event_can_lock_governance_path() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="ipo_readiness_launchpad",
    )
    product = state.products[0]
    state.company.current_turn = 21
    state.company.cash_on_hand = Decimal("5200.00")
    state.company.reputation = 80
    state.finance.board_confidence = 60
    state.finance.board_score = 58
    state.finance.board_pressure = 28
    state.finance.governance_risk = 52
    state.finance.board_resolution_due = True
    state.finance.board_warning_level = 2
    state.finance.board_warning_active = True
    state.support_program.backlog_queue = 10
    state.support_program.escalation_queue = 4
    state.support_program.queue_age_pressure = 5
    state.event_history.append(
        EventHistoryEntry(
            event_id="ipo_listing_window",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="IPO Listing Window",
            triggered_turn=20,
            resolved_turn=20,
            selected_option_id="slow_and_certify",
            selected_option_label="Slow down and certify the path",
            result_text="Listing path tightened.",
        )
    )
    state.customer_accounts = [
        CustomerAccount(
            name="Governance Queue Anchor",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("3200.00"),
            support_tier=SupportTier.WHITE_GLOVE,
            satisfaction=58,
            onboarding_health=52,
            support_load=34,
            open_tickets=8,
            sla_breach_risk=68,
            renewal_health=48,
            expansion_potential=72,
            renewal_turn=9,
            churn_risk=28,
            ticket_queue_age=4,
            status=CustomerAccountStatus.AT_RISK,
        )
    ]
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "ipo_governance_lockstep"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "lock_governance_path")

    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.governance_risk < state.finance.governance_risk
    assert outcome.state.finance.board_resolution_due is False
    assert outcome.state.finance.board_warning_level < state.finance.board_warning_level
    assert outcome.history_entry.event_id == "ipo_governance_lockstep"


def test_ipo_syndicate_commitment_event_can_anchor_book() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="ipo_readiness_launchpad",
    )
    product = state.products[0]
    state.company.current_turn = 22
    state.company.cash_on_hand = Decimal("5400.00")
    state.company.reputation = 82
    state.finance.board_confidence = 62
    state.finance.board_score = 58
    state.finance.board_pressure = 30
    state.finance.governance_risk = 48
    state.event_history.append(
        EventHistoryEntry(
            event_id="ipo_governance_lockstep",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="IPO Governance Lockstep",
            triggered_turn=21,
            resolved_turn=21,
            selected_option_id="lock_governance_path",
            selected_option_label="Lock the governance path",
            result_text="Governance path locked.",
        )
    )
    state.customer_accounts = [
        CustomerAccount(
            name="Syndicate Anchor",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("3200.00"),
            support_tier=SupportTier.WHITE_GLOVE,
            satisfaction=60,
            onboarding_health=54,
            support_load=30,
            open_tickets=7,
            sla_breach_risk=56,
            renewal_health=52,
            expansion_potential=70,
            renewal_turn=9,
            churn_risk=22,
            status=CustomerAccountStatus.ACTIVE,
        )
    ]
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "ipo_syndicate_commitment"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "anchor_book")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.governance_risk < state.finance.governance_risk
    assert outcome.state.company.reputation > state.company.reputation
    assert outcome.history_entry.event_id == "ipo_syndicate_commitment"


def test_ipo_pricing_committee_event_can_lock_pricing_discipline() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="ipo_readiness_launchpad",
    )
    product = state.products[0]
    state.company.current_turn = 23
    state.company.cash_on_hand = Decimal("5600.00")
    state.company.reputation = 84
    state.finance.board_confidence = 64
    state.finance.board_score = 58
    state.finance.board_pressure = 30
    state.finance.governance_risk = 46
    state.event_history.append(
        EventHistoryEntry(
            event_id="ipo_syndicate_commitment",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="IPO Syndicate Commitment",
            triggered_turn=22,
            resolved_turn=22,
            selected_option_id="anchor_book",
            selected_option_label="Anchor the syndicate",
            result_text="Syndicate anchored.",
        )
    )
    state.customer_accounts = [
        CustomerAccount(
            name="Pricing Anchor",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("3400.00"),
            support_tier=SupportTier.WHITE_GLOVE,
            satisfaction=62,
            onboarding_health=56,
            support_load=28,
            open_tickets=6,
            sla_breach_risk=52,
            renewal_health=54,
            expansion_potential=72,
            renewal_turn=9,
            churn_risk=20,
            status=CustomerAccountStatus.ACTIVE,
        )
    ]
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "ipo_pricing_committee"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "lock_pricing_discipline")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.governance_risk < state.finance.governance_risk
    assert outcome.state.company.reputation > state.company.reputation
    assert outcome.history_entry.event_id == "ipo_pricing_committee"


def test_ipo_reference_committee_event_can_fund_committee() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="ipo_readiness_launchpad",
    )
    product = state.products[0]
    state.company.current_turn = 24
    state.company.cash_on_hand = Decimal("5400.00")
    state.company.reputation = 82
    state.finance.board_confidence = 66
    state.finance.board_score = 60
    state.finance.board_pressure = 28
    state.finance.governance_risk = 44
    state.finance.board_warning_level = 2
    state.event_history.append(
        EventHistoryEntry(
            event_id="ipo_pricing_committee",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="IPO Pricing Committee",
            triggered_turn=23,
            resolved_turn=23,
            selected_option_id="lock_pricing_discipline",
            selected_option_label="Lock pricing discipline",
            result_text="Pricing discipline locked.",
        )
    )
    state.customer_accounts = [
        CustomerAccount(
            name="Reference Board",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("3200.00"),
            support_tier=SupportTier.WHITE_GLOVE,
            satisfaction=60,
            onboarding_health=54,
            support_load=30,
            open_tickets=7,
            sla_breach_risk=54,
            renewal_health=50,
            expansion_potential=68,
            renewal_turn=10,
            churn_risk=24,
            status=CustomerAccountStatus.ACTIVE,
        )
    ]
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "ipo_reference_committee"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "fund_reference_committee")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.governance_risk < state.finance.governance_risk
    assert outcome.state.customer_accounts[0].support_load < state.customer_accounts[0].support_load
    assert (
        outcome.state.customer_accounts[0].renewal_health
        > state.customer_accounts[0].renewal_health
    )
    assert outcome.history_entry.event_id == "ipo_reference_committee"


def test_ipo_roadshow_lock_event_can_fund_lock() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="ipo_readiness_launchpad",
    )
    product = state.products[0]
    state.company.current_turn = 25
    state.company.cash_on_hand = Decimal("5400.00")
    state.company.reputation = 82
    state.finance.board_confidence = 66
    state.finance.board_score = 60
    state.finance.board_pressure = 30
    state.finance.governance_risk = 46
    state.finance.board_warning_level = 2
    state.event_history.append(
        EventHistoryEntry(
            event_id="ipo_reference_committee",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="IPO Reference Committee",
            triggered_turn=24,
            resolved_turn=24,
            selected_option_id="fund_reference_committee",
            selected_option_label="Fund the reference committee",
            result_text="Reference committee funded.",
        )
    )
    state.customer_accounts = [
        CustomerAccount(
            name="Roadshow Reference Board",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("3400.00"),
            support_tier=SupportTier.WHITE_GLOVE,
            satisfaction=60,
            onboarding_health=54,
            support_load=30,
            open_tickets=7,
            sla_breach_risk=54,
            renewal_health=50,
            expansion_potential=68,
            renewal_turn=10,
            churn_risk=24,
            status=CustomerAccountStatus.ACTIVE,
        )
    ]
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "ipo_roadshow_lock"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "fund_roadshow_lock")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.governance_risk < state.finance.governance_risk
    assert outcome.state.customer_accounts[0].support_load < state.customer_accounts[0].support_load
    assert (
        outcome.state.customer_accounts[0].renewal_health
        > state.customer_accounts[0].renewal_health
    )
    assert outcome.history_entry.event_id == "ipo_roadshow_lock"


def test_support_meltdown_event_can_trigger_from_hotspot_lane_pressure() -> None:
    product = make_product("Queue Hotspot Core", lifecycle_stage=LifecycleStage.MATURE)
    account = CustomerAccount(
        name="Premium Queue Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2100.00"),
        support_tier=SupportTier.WHITE_GLOVE,
        satisfaction=60,
        onboarding_health=54,
        support_load=38,
        open_tickets=13,
        sla_breach_risk=70,
        renewal_health=52,
        expansion_potential=60,
        renewal_turn=12,
        churn_risk=24,
        ticket_queue_age=4,
        status=CustomerAccountStatus.ACTIVE,
    )
    state = make_state(product, customer_accounts=[account], cash_on_hand=Decimal("9500.00"))
    state.support_program.backlog_queue = 2
    state.support_program.escalation_queue = 1
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "support_meltdown"
    )

    assert definition.is_eligible(state) is True


def test_endgame_pressure_surfaces_support_channel_and_reset_fragility() -> None:
    product = make_product(
        "Fragility Core",
        lifecycle_stage=LifecycleStage.MATURE,
        user_count=240,
        quality=72,
        market_fit=70,
    )
    account = CustomerAccount(
        name="Fragility Enterprise",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("1800.00"),
        support_tier=SupportTier.WHITE_GLOVE,
        satisfaction=54,
        onboarding_health=48,
        support_load=42,
        open_tickets=20,
        sla_breach_risk=74,
        renewal_health=44,
        expansion_potential=56,
        renewal_turn=13,
        churn_risk=44,
        status=CustomerAccountStatus.ACTIVE,
    )
    partnership = PartnershipDeal(
        name="Fragility Marketplace",
        product_id=product.id,
        channel=PartnerChannel.MARKETPLACE,
        status=PartnershipStatus.STRAINED,
        quality=58,
        risk=60,
        conflict_pressure=62,
        enablement_level=28,
        sourced_revenue=Decimal("1800.00"),
        rev_share_rate=Decimal("0.2500"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        cash_on_hand=Decimal("5200.00"),
        current_turn=14,
    )
    state.finance.board_pressure = 24
    state.finance.board_warning_level = 2
    state.finance.restructuring_pressure = 12
    state.finance.governance_crisis_level = 1
    state.finance.board_resolution_due = True
    state.support_program.backlog_queue = 18
    state.support_program.escalation_queue = 5
    state.support_program.sla_breaches_last_turn = 3
    state.support_program.queue_age_pressure = 5

    pressure = calculate_endgame_pressure(state)

    assert pressure.support_fragility > 0
    assert pressure.channel_fragility > 0
    assert pressure.commercial_fragility > 0
    assert pressure.capital_fragility > 0
    assert pressure.board_reset_risk > 0
    assert len(pressure.path_scorecard) == 4
    assert len(pressure.path_watchlist) == 4
    assert pressure.strategic_clarity in {"clear path", "clear but stressed", "contested"}
    assert pressure.operating_durability in {"resilient", "stretched", "fragile"}
    assert pressure.restructure_heat >= pressure.board_reset_risk // 3


def test_endgame_pressure_counts_queue_exposure_and_channel_recovery_drag() -> None:
    product = make_product(
        "Fragile Enterprise Core",
        lifecycle_stage=LifecycleStage.MATURE,
        user_count=220,
        quality=72,
        market_fit=70,
    )
    account = CustomerAccount(
        name="Late Enterprise Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2600.00"),
        support_tier=SupportTier.WHITE_GLOVE,
        satisfaction=50,
        onboarding_health=46,
        support_load=44,
        open_tickets=18,
        sla_breach_risk=76,
        renewal_health=42,
        expansion_potential=52,
        renewal_turn=13,
        churn_risk=46,
        ticket_queue_age=4,
        status=CustomerAccountStatus.ACTIVE,
    )
    partnership = PartnershipDeal(
        name="Recovery Marketplace",
        product_id=product.id,
        channel=PartnerChannel.MARKETPLACE,
        status=PartnershipStatus.RECOVERY,
        quality=58,
        risk=54,
        conflict_pressure=50,
        enablement_level=28,
        sourced_revenue=Decimal("2200.00"),
        rev_share_rate=Decimal("0.2500"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        cash_on_hand=Decimal("4800.00"),
        current_turn=15,
    )
    state.support_program.backlog_queue = 16
    state.support_program.escalation_queue = 5
    state.support_program.queue_age_pressure = 6

    pressure = calculate_endgame_pressure(state)

    assert pressure.support_fragility >= 40
    assert pressure.channel_fragility >= 30
    assert pressure.commercial_fragility >= 30
    assert pressure.operating_durability in {"stretched", "fragile"}


def test_endgame_pressure_raises_ipo_scrutiny_on_enterprise_focus_mismatch() -> None:
    product = make_product(
        "Enterprise Listing Core",
        lifecycle_stage=LifecycleStage.MATURE,
        user_count=260,
        quality=78,
        market_fit=76,
    )
    account = CustomerAccount(
        name="Enterprise Queue Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("1600.00"),
        support_tier=SupportTier.WHITE_GLOVE,
        satisfaction=60,
        onboarding_health=54,
        support_load=34,
        open_tickets=10,
        sla_breach_risk=58,
        renewal_health=58,
        expansion_potential=60,
        renewal_turn=12,
        churn_risk=28,
        ticket_queue_age=3,
        status=CustomerAccountStatus.ACTIVE,
    )
    mismatched = make_state(
        product,
        customer_accounts=[account.model_copy(deep=True)],
        cash_on_hand=Decimal("18000.00"),
        current_turn=15,
    )
    aligned = make_state(
        product,
        customer_accounts=[account.model_copy(deep=True)],
        cash_on_hand=Decimal("18000.00"),
        current_turn=15,
    )
    for state in (mismatched, aligned):
        state.company.reputation = 82
        state.finance.board_confidence = 76
        state.finance.board_score = 72
        state.finance.board_pressure = 14
        state.support_program.backlog_queue = 8
        state.support_program.escalation_queue = 2
        state.support_program.queue_age_pressure = 3
    mismatched.support_program.lane_focus = SupportLaneFocus.BILLING
    aligned.support_program.lane_focus = SupportLaneFocus.ENTERPRISE

    mismatch_pressure = calculate_endgame_pressure(mismatched)
    aligned_pressure = calculate_endgame_pressure(aligned)

    assert mismatch_pressure.public_market_scrutiny >= aligned_pressure.public_market_scrutiny
    assert mismatch_pressure.support_fragility > aligned_pressure.support_fragility
    assert "IPO:" in mismatch_pressure.path_watchlist[0]


def test_independence_reckoning_event_can_take_bridge_flex() -> None:
    product = make_product(
        "Independent Core",
        lifecycle_stage=LifecycleStage.MATURE,
        user_count=180,
        quality=70,
        market_fit=68,
    )
    state = make_state(
        product,
        cash_on_hand=Decimal("4200.00"),
        current_turn=12,
        finance=FinanceState(
            debt_principal=Decimal("2800.00"),
            loan_interest_rate=Decimal("0.0320"),
            investor_pressure=24,
            covenant_risk=20,
            board_confidence=66,
        ),
    )
    state.company.reputation = 72
    state.capital_plan.reserve_target = Decimal("5200.00")
    pressure = calculate_endgame_pressure(state)

    assert pressure.independence_discipline > 0
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "independence_reckoning"
    )
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "take_bridge_flex")

    assert outcome.state.company.cash_on_hand > state.company.cash_on_hand
    assert outcome.state.finance.debt_principal > state.finance.debt_principal
    assert outcome.state.finance.loan_interest_rate > state.finance.loan_interest_rate
    assert outcome.history_entry.event_id == "independence_reckoning"


def test_acquirer_diligence_event_requires_acquisition_outlook() -> None:
    product = make_product(
        "Listing Bias Core",
        lifecycle_stage=LifecycleStage.MATURE,
        user_count=260,
        quality=80,
        market_fit=78,
    )
    accounts = [
        CustomerAccount(
            name="Atlas Finance",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("1900.00"),
            support_tier=SupportTier.WHITE_GLOVE,
            satisfaction=62,
            onboarding_health=56,
            support_load=36,
            open_tickets=9,
            sla_breach_risk=60,
            renewal_health=58,
            expansion_potential=64,
            renewal_turn=14,
            churn_risk=26,
            status=CustomerAccountStatus.ACTIVE,
        )
    ]
    partnerships = [
        PartnershipDeal(
            name="Noisy Reseller",
            product_id=product.id,
            channel=PartnerChannel.RESELLER,
            status=PartnershipStatus.STRAINED,
            quality=64,
            risk=52,
            conflict_pressure=54,
            enablement_level=34,
            sourced_revenue=Decimal("1500.00"),
            rev_share_rate=Decimal("0.2100"),
        )
    ]
    state = make_state(
        product,
        customer_accounts=accounts,
        partnerships=partnerships,
        cash_on_hand=Decimal("18000.00"),
    )
    state.company.current_turn = 16
    state.company.reputation = 80
    state.finance.board_confidence = 84
    state.finance.board_score = 82
    state.finance.board_pressure = 24
    state.finance.governance_risk = 10
    state.support_program.escalation_queue = 6
    state.support_program.sla_breaches_last_turn = 3

    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state, readiness)
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "acquirer_diligence"
    )

    assert readiness.strategic_outlook == "ipo_ready"
    assert pressure.acquirer_diligence >= BALANCE.event_acquirer_diligence_pressure_threshold
    assert definition.is_eligible(state) is False


def test_acquirer_diligence_event_triggers_from_hotspot_channel_under_mna_outlook() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="acquisition_diligence_sprint",
    )
    product = state.products[0]
    state.customer_accounts = [
        CustomerAccount(
            name="Buyer Anchor",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("2600.00"),
            support_tier=SupportTier.WHITE_GLOVE,
            satisfaction=64,
            onboarding_health=58,
            support_load=34,
            open_tickets=8,
            sla_breach_risk=52,
            renewal_health=62,
            expansion_potential=68,
            renewal_turn=14,
            churn_risk=18,
            status=CustomerAccountStatus.ACTIVE,
        )
    ]
    state.partnerships = [
        PartnershipDeal(
            name="Hotspot Integration",
            product_id=product.id,
            channel=PartnerChannel.INTEGRATION,
            status=PartnershipStatus.RECOVERY,
            quality=66,
            risk=50,
            conflict_pressure=52,
            enablement_level=34,
            sourced_revenue=Decimal("3200.00"),
            rev_share_rate=Decimal("0.2300"),
        ),
        PartnershipDeal(
            name="Second Integration",
            product_id=product.id,
            channel=PartnerChannel.INTEGRATION,
            status=PartnershipStatus.STRAINED,
            quality=62,
            risk=54,
            conflict_pressure=50,
            enablement_level=30,
            sourced_revenue=Decimal("1800.00"),
            rev_share_rate=Decimal("0.2200"),
        ),
    ]
    state.finance.board_confidence = 20
    state.finance.board_score = 18
    state.finance.governance_risk = 42
    state.finance.restructuring_pressure = 9
    state.finance.debt_principal = Decimal("9800.00")
    state.finance.investor_pressure = 28
    state.finance.missed_board_targets = 3
    state.support_program.escalation_queue = 5
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "acquirer_diligence"
    )
    readiness = calculate_endgame_readiness(state)

    assert readiness.strategic_outlook == "strategic_acquisition"
    assert definition.is_eligible(state) is True


def test_acquirer_diligence_penalizes_paused_channel_dependency() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="acquisition_diligence_sprint",
    )
    product = state.products[0]
    common_kwargs = dict(
        product_id=product.id,
        channel=PartnerChannel.INTEGRATION,
        quality=64,
        risk=52,
        conflict_pressure=48,
        enablement_level=30,
        sourced_revenue=Decimal("2400.00"),
        rev_share_rate=Decimal("0.2200"),
    )
    active_state = state.model_copy(deep=True)
    paused_state = state.model_copy(deep=True)
    active_state.partnerships = [
        PartnershipDeal(
            name="Active Integration",
            status=PartnershipStatus.STRAINED,
            **common_kwargs,
        ),
    ]
    paused_state.partnerships = [
        PartnershipDeal(
            name="Paused Integration",
            status=PartnershipStatus.PAUSED,
            **common_kwargs,
        ),
    ]

    active_pressure = calculate_endgame_pressure(active_state)
    paused_pressure = calculate_endgame_pressure(paused_state)

    assert paused_pressure.acquirer_diligence >= active_pressure.acquirer_diligence
    assert "M&A:" in paused_pressure.path_watchlist[1]


def test_buyer_reference_check_event_triggers_after_acquirer_diligence() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="acquisition_diligence_sprint",
    )
    product = state.products[0]
    state.company.current_turn = 19
    state.company.cash_on_hand = Decimal("2600.00")
    state.finance.board_confidence = 12
    state.finance.board_score = 18
    state.finance.board_pressure = 28
    state.finance.governance_risk = 24
    state.finance.investor_pressure = 20
    state.finance.board_team_health_score = 42
    state.support_program.escalation_queue = 5
    state.event_history.append(
        EventHistoryEntry(
            event_id="acquirer_diligence",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Acquirer Diligence",
            triggered_turn=18,
            resolved_turn=18,
            selected_option_id="open_data_room",
            selected_option_label="Open data room",
            result_text="Diligence opened.",
        )
    )
    state.customer_accounts = [
        CustomerAccount(
            name="Buyer Anchor",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("2400.00"),
            support_tier=SupportTier.WHITE_GLOVE,
            satisfaction=62,
            onboarding_health=56,
            support_load=28,
            open_tickets=6,
            sla_breach_risk=44,
            renewal_health=58,
            expansion_potential=66,
            renewal_turn=10,
            churn_risk=18,
            status=CustomerAccountStatus.ACTIVE,
        ),
        CustomerAccount(
            name="Buyer Anchor Two",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("3200.00"),
            support_tier=SupportTier.PRIORITY,
            satisfaction=60,
            onboarding_health=52,
            support_load=30,
            open_tickets=5,
            sla_breach_risk=46,
            renewal_health=56,
            expansion_potential=62,
            renewal_turn=11,
            churn_risk=20,
            status=CustomerAccountStatus.ACTIVE,
        ),
    ]
    state.partnerships = [
        PartnershipDeal(
            name="Hotspot Integration",
            product_id=product.id,
            channel=PartnerChannel.INTEGRATION,
            status=PartnershipStatus.RECOVERY,
            quality=62,
            risk=50,
            conflict_pressure=52,
            enablement_level=32,
            sourced_revenue=Decimal("2600.00"),
            rev_share_rate=Decimal("0.2200"),
        )
    ]
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "buyer_reference_check"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "fund_reference_program")

    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.history_entry.event_id == "buyer_reference_check"


def test_buyer_channel_conflict_review_event_can_separate_terms() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="acquisition_diligence_sprint",
    )
    product = state.products[0]
    state.company.current_turn = 20
    state.company.cash_on_hand = Decimal("2600.00")
    state.finance.board_confidence = 12
    state.finance.board_score = 18
    state.finance.board_pressure = 28
    state.finance.governance_risk = 24
    state.finance.investor_pressure = 20
    state.finance.board_team_health_score = 42
    state.support_program.escalation_queue = 5
    state.event_history.append(
        EventHistoryEntry(
            event_id="buyer_reference_check",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Buyer Reference Check",
            triggered_turn=19,
            resolved_turn=19,
            selected_option_id="fund_reference_program",
            selected_option_label="Fund reference program",
            result_text="Reference program funded.",
        )
    )
    state.customer_accounts = [
        CustomerAccount(
            name="Buyer Anchor",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("2400.00"),
            support_tier=SupportTier.WHITE_GLOVE,
            satisfaction=62,
            onboarding_health=56,
            support_load=28,
            open_tickets=6,
            sla_breach_risk=44,
            renewal_health=58,
            expansion_potential=66,
            renewal_turn=10,
            churn_risk=18,
            status=CustomerAccountStatus.ACTIVE,
        ),
        CustomerAccount(
            name="Buyer Anchor Two",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("3200.00"),
            support_tier=SupportTier.PRIORITY,
            satisfaction=60,
            onboarding_health=52,
            support_load=30,
            open_tickets=5,
            sla_breach_risk=46,
            renewal_health=56,
            expansion_potential=62,
            renewal_turn=11,
            churn_risk=20,
            status=CustomerAccountStatus.ACTIVE,
        ),
    ]
    state.partnerships = [
        PartnershipDeal(
            name="Conflict Integration",
            product_id=product.id,
            channel=PartnerChannel.INTEGRATION,
            status=PartnershipStatus.RECOVERY,
            quality=62,
            risk=50,
            conflict_pressure=52,
            enablement_level=32,
            sourced_revenue=Decimal("2600.00"),
            sourced_users=34,
            rev_share_rate=Decimal("0.2200"),
        )
    ]
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "buyer_channel_conflict_review"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "separate_partner_terms")

    updated_partnership = outcome.state.partnerships[0]
    assert updated_partnership.conflict_pressure < state.partnerships[0].conflict_pressure
    assert updated_partnership.risk < state.partnerships[0].risk
    assert updated_partnership.rev_share_rate > state.partnerships[0].rev_share_rate
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.history_entry.event_id == "buyer_channel_conflict_review"


def test_buyer_term_sheet_event_can_sign_clean_terms() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="acquisition_diligence_sprint",
    )
    product = state.products[0]
    state.company.current_turn = 21
    state.company.cash_on_hand = Decimal("3400.00")
    state.company.reputation = 62
    state.finance.board_confidence = 18
    state.finance.board_score = 22
    state.finance.board_pressure = 30
    state.finance.governance_risk = 42
    state.finance.investor_pressure = 28
    state.finance.restructuring_pressure = 9
    state.finance.debt_principal = Decimal("9800.00")
    state.finance.missed_board_targets = 3
    state.finance.board_team_health_score = 42
    state.support_program.escalation_queue = 6
    state.event_history.append(
        EventHistoryEntry(
            event_id="buyer_channel_conflict_review",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Buyer Channel Conflict Review",
            triggered_turn=20,
            resolved_turn=20,
            selected_option_id="separate_partner_terms",
            selected_option_label="Separate partner terms",
            result_text="Channel terms cleaned up.",
        )
    )
    state.customer_accounts = [
        CustomerAccount(
            name="Buyer Terms Anchor",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("2800.00"),
            support_tier=SupportTier.WHITE_GLOVE,
            satisfaction=60,
            onboarding_health=54,
            support_load=30,
            open_tickets=6,
            sla_breach_risk=48,
            renewal_health=56,
            expansion_potential=68,
            renewal_turn=10,
            churn_risk=22,
            status=CustomerAccountStatus.ACTIVE,
        )
    ]
    state.partnerships = [
        PartnershipDeal(
            name="Terms Integration",
            product_id=product.id,
            channel=PartnerChannel.INTEGRATION,
            status=PartnershipStatus.RECOVERY,
            quality=62,
            risk=54,
            conflict_pressure=58,
            enablement_level=30,
            sourced_revenue=Decimal("3200.00"),
            sourced_users=38,
            rev_share_rate=Decimal("0.2200"),
        )
    ]
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "buyer_term_sheet"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "sign_clean_terms")

    updated_partnership = outcome.state.partnerships[0]
    assert updated_partnership.conflict_pressure < state.partnerships[0].conflict_pressure
    assert updated_partnership.risk < state.partnerships[0].risk
    assert updated_partnership.enablement_level > state.partnerships[0].enablement_level
    assert updated_partnership.rev_share_rate > state.partnerships[0].rev_share_rate
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.history_entry.event_id == "buyer_term_sheet"


def test_buyer_synergy_map_event_can_publish_synergy_map() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="acquisition_diligence_sprint",
    )
    product = state.products[0]
    state.company.current_turn = 22
    state.company.cash_on_hand = Decimal("3200.00")
    state.company.reputation = 64
    state.finance.board_confidence = 20
    state.finance.board_score = 24
    state.finance.board_pressure = 30
    state.finance.governance_risk = 34
    state.finance.investor_pressure = 26
    state.support_program.escalation_queue = 6
    state.event_history.append(
        EventHistoryEntry(
            event_id="buyer_term_sheet",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Buyer Term Sheet",
            triggered_turn=21,
            resolved_turn=21,
            selected_option_id="sign_clean_terms",
            selected_option_label="Sign cleaner terms",
            result_text="Cleaner terms accepted.",
        )
    )
    state.customer_accounts = [
        CustomerAccount(
            name="Synergy Buyer Anchor",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("2800.00"),
            support_tier=SupportTier.WHITE_GLOVE,
            satisfaction=60,
            onboarding_health=54,
            support_load=30,
            open_tickets=6,
            sla_breach_risk=46,
            renewal_health=56,
            expansion_potential=68,
            renewal_turn=10,
            churn_risk=20,
            status=CustomerAccountStatus.ACTIVE,
        ),
        CustomerAccount(
            name="Synergy Buyer Anchor Two",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("2400.00"),
            support_tier=SupportTier.PRIORITY,
            satisfaction=58,
            onboarding_health=50,
            support_load=28,
            open_tickets=5,
            sla_breach_risk=44,
            renewal_health=54,
            expansion_potential=64,
            renewal_turn=11,
            churn_risk=22,
            status=CustomerAccountStatus.ACTIVE,
        ),
    ]
    state.partnerships = [
        PartnershipDeal(
            name="Synergy Hotspot Integration",
            product_id=product.id,
            channel=PartnerChannel.INTEGRATION,
            status=PartnershipStatus.RECOVERY,
            quality=62,
            risk=54,
            conflict_pressure=56,
            enablement_level=30,
            sourced_revenue=Decimal("3400.00"),
            sourced_users=40,
            rev_share_rate=Decimal("0.2200"),
        )
    ]
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "buyer_synergy_map"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "publish_synergy_map")

    updated_partnership = outcome.state.partnerships[0]
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert updated_partnership.conflict_pressure < state.partnerships[0].conflict_pressure
    assert updated_partnership.risk < state.partnerships[0].risk
    assert updated_partnership.enablement_level > state.partnerships[0].enablement_level
    assert outcome.state.customer_accounts[0].support_load < state.customer_accounts[0].support_load
    assert (
        outcome.state.customer_accounts[0].renewal_health
        > state.customer_accounts[0].renewal_health
    )
    assert outcome.history_entry.event_id == "buyer_synergy_map"


def test_buyer_integration_blueprint_event_can_fund_clean_room() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="acquisition_diligence_sprint",
    )
    product = state.products[0]
    state.company.current_turn = 23
    state.company.cash_on_hand = Decimal("3400.00")
    state.company.reputation = 64
    state.finance.board_confidence = 20
    state.finance.board_score = 24
    state.finance.board_pressure = 32
    state.finance.governance_risk = 34
    state.event_history.append(
        EventHistoryEntry(
            event_id="buyer_synergy_map",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Buyer Synergy Map",
            triggered_turn=22,
            resolved_turn=22,
            selected_option_id="publish_synergy_map",
            selected_option_label="Publish the synergy map",
            result_text="Cleaner synergy map published.",
        )
    )
    state.customer_accounts = [
        CustomerAccount(
            name="Blueprint Anchor",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("3000.00"),
            support_tier=SupportTier.WHITE_GLOVE,
            satisfaction=60,
            onboarding_health=54,
            support_load=34,
            open_tickets=8,
            sla_breach_risk=48,
            renewal_health=54,
            expansion_potential=68,
            renewal_turn=10,
            churn_risk=22,
            status=CustomerAccountStatus.ACTIVE,
        ),
        CustomerAccount(
            name="Blueprint Anchor Two",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("2500.00"),
            support_tier=SupportTier.PRIORITY,
            satisfaction=58,
            onboarding_health=50,
            support_load=32,
            open_tickets=7,
            sla_breach_risk=46,
            renewal_health=52,
            expansion_potential=64,
            renewal_turn=11,
            churn_risk=24,
            status=CustomerAccountStatus.ACTIVE,
        ),
    ]
    state.partnerships = [
        PartnershipDeal(
            name="Blueprint Integration",
            product_id=product.id,
            channel=PartnerChannel.INTEGRATION,
            status=PartnershipStatus.RECOVERY,
            quality=62,
            risk=56,
            conflict_pressure=58,
            enablement_level=30,
            sourced_revenue=Decimal("3600.00"),
            sourced_users=40,
            rev_share_rate=Decimal("0.2200"),
        )
    ]
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "buyer_integration_blueprint"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "fund_clean_room")

    updated_partnership = outcome.state.partnerships[0]
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert updated_partnership.conflict_pressure < state.partnerships[0].conflict_pressure
    assert updated_partnership.risk < state.partnerships[0].risk
    assert updated_partnership.enablement_level > state.partnerships[0].enablement_level
    assert outcome.state.customer_accounts[0].support_load < state.customer_accounts[0].support_load
    assert (
        outcome.state.customer_accounts[0].renewal_health
        > state.customer_accounts[0].renewal_health
    )
    assert outcome.history_entry.event_id == "buyer_integration_blueprint"


def test_buyer_operating_memo_event_can_publish_memo() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="acquisition_diligence_sprint",
    )
    product = state.products[0]
    state.company.current_turn = 24
    state.company.cash_on_hand = Decimal("5200.00")
    state.company.reputation = 80
    state.finance.board_confidence = 58
    state.finance.board_score = 56
    state.finance.board_pressure = 28
    state.finance.governance_risk = 44
    state.event_history.append(
        EventHistoryEntry(
            event_id="buyer_integration_blueprint",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Buyer Integration Blueprint",
            triggered_turn=23,
            resolved_turn=23,
            selected_option_id="fund_clean_room",
            selected_option_label="Fund the clean room",
            result_text="Buyer clean room funded.",
        )
    )
    state.customer_accounts = [
        CustomerAccount(
            name="Memo Account",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("2800.00"),
            support_tier=SupportTier.PRIORITY,
            satisfaction=56,
            onboarding_health=46,
            support_load=30,
            open_tickets=5,
            sla_breach_risk=34,
            renewal_health=54,
            expansion_potential=66,
            renewal_turn=10,
            churn_risk=22,
            status=CustomerAccountStatus.ACTIVE,
        )
    ]
    state.partnerships = [
        PartnershipDeal(
            name="Memo Integration",
            product_id=product.id,
            channel=PartnerChannel.INTEGRATION,
            status=PartnershipStatus.RECOVERY,
            quality=60,
            risk=56,
            conflict_pressure=58,
            enablement_level=28,
            sourced_revenue=Decimal("3400.00"),
            sourced_users=40,
            rev_share_rate=Decimal("0.2200"),
        )
    ]
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "buyer_operating_memo"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "publish_operating_memo")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.customer_accounts[0].support_load < state.customer_accounts[0].support_load
    assert outcome.history_entry.event_id == "buyer_operating_memo"


def test_buyer_signing_committee_event_can_staff_committee() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="acquisition_diligence_sprint",
    )
    product = state.products[0]
    state.company.current_turn = 24
    state.company.cash_on_hand = Decimal("5600.00")
    state.finance.board_confidence = 20
    state.finance.board_score = 18
    state.finance.board_pressure = 34
    state.finance.governance_risk = 42
    state.event_history.append(
        EventHistoryEntry(
            event_id="buyer_operating_memo",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Buyer Operating Memo",
            triggered_turn=23,
            resolved_turn=23,
            selected_option_id="publish_operating_memo",
            selected_option_label="Publish the operating memo",
            result_text="Operating memo published.",
        )
    )
    state.customer_accounts = [
        CustomerAccount(
            name="Buyer Anchor",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("2600.00"),
            support_tier=SupportTier.WHITE_GLOVE,
            satisfaction=60,
            onboarding_health=52,
            support_load=28,
            open_tickets=6,
            sla_breach_risk=46,
            renewal_health=52,
            expansion_potential=68,
            renewal_turn=11,
            churn_risk=24,
            status=CustomerAccountStatus.ACTIVE,
        )
    ]
    state.partnerships = [
        PartnershipDeal(
            name="Integration Hotspot",
            product_id=product.id,
            channel=PartnerChannel.INTEGRATION,
            status=PartnershipStatus.RECOVERY,
            quality=60,
            risk=54,
            conflict_pressure=56,
            enablement_level=28,
            sourced_revenue=Decimal("2800.00"),
            rev_share_rate=Decimal("0.2200"),
        )
    ]
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "buyer_signing_committee"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "staff_signing_committee")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.customer_accounts[0].support_load < state.customer_accounts[0].support_load
    assert (
        outcome.state.customer_accounts[0].renewal_health
        > state.customer_accounts[0].renewal_health
    )
    assert outcome.history_entry.event_id == "buyer_signing_committee"


def test_buyer_close_readiness_event_can_staff_close_plan() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="acquisition_diligence_sprint",
    )
    product = state.products[0]
    state.company.current_turn = 25
    state.company.cash_on_hand = Decimal("5600.00")
    state.finance.board_confidence = 20
    state.finance.board_score = 18
    state.finance.board_pressure = 36
    state.finance.governance_risk = 44
    state.event_history.append(
        EventHistoryEntry(
            event_id="buyer_signing_committee",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Buyer Signing Committee",
            triggered_turn=24,
            resolved_turn=24,
            selected_option_id="staff_signing_committee",
            selected_option_label="Staff the signing committee",
            result_text="Buyer signing committee staffed.",
        )
    )
    state.customer_accounts = [
        CustomerAccount(
            name="Buyer Close Anchor",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("2600.00"),
            support_tier=SupportTier.WHITE_GLOVE,
            satisfaction=60,
            onboarding_health=52,
            support_load=28,
            open_tickets=6,
            sla_breach_risk=46,
            renewal_health=52,
            expansion_potential=68,
            renewal_turn=11,
            churn_risk=24,
            status=CustomerAccountStatus.ACTIVE,
        )
    ]
    state.partnerships = [
        PartnershipDeal(
            name="Close Readiness Integration",
            product_id=product.id,
            channel=PartnerChannel.INTEGRATION,
            status=PartnershipStatus.RECOVERY,
            quality=60,
            risk=56,
            conflict_pressure=58,
            enablement_level=28,
            sourced_revenue=Decimal("2800.00"),
            rev_share_rate=Decimal("0.2200"),
        )
    ]
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "buyer_close_readiness"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "staff_close_readiness")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.customer_accounts[0].support_load < state.customer_accounts[0].support_load
    assert (
        outcome.state.customer_accounts[0].renewal_health
        > state.customer_accounts[0].renewal_health
    )
    assert outcome.history_entry.event_id == "buyer_close_readiness"


def test_independence_discipline_penalizes_low_reserve_share() -> None:
    product = make_product("Reserve Discipline Core", lifecycle_stage=LifecycleStage.MATURE)
    high_reserve_state = make_state(product, cash_on_hand=Decimal("6200.00"), current_turn=14)
    low_reserve_state = high_reserve_state.model_copy(deep=True)
    high_reserve_state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.BALANCED,
        source_preference=CapitalSourcePreference.BOOTSTRAP,
        planning_horizon_turns=8,
        reserve_target=Decimal("4800.00"),
        product_investment_share=34,
        go_to_market_share=28,
        reserve_share=38,
    )
    low_reserve_state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.EXPAND,
        source_preference=CapitalSourcePreference.DEBT,
        planning_horizon_turns=5,
        reserve_target=Decimal("2600.00"),
        product_investment_share=45,
        go_to_market_share=40,
        reserve_share=15,
    )

    high_pressure = calculate_endgame_pressure(high_reserve_state)
    low_pressure = calculate_endgame_pressure(low_reserve_state)

    assert low_pressure.independence_discipline >= high_pressure.independence_discipline
    assert "raise the reserve target" in low_pressure.path_watchlist[2]


def test_independence_cash_crunch_event_can_shift_capital_to_reserve() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="independence_compounder",
    )
    state.company.current_turn = 20
    state.company.cash_on_hand = Decimal("3000.00")
    state.company.reputation = 92
    state.finance.board_confidence = 0
    state.finance.board_score = 0
    state.finance.governance_risk = 55
    state.finance.board_team_health_score = 96
    state.finance.investor_pressure = 0
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.BALANCED,
        source_preference=CapitalSourcePreference.BOOTSTRAP,
        planning_horizon_turns=6,
        reserve_target=Decimal("4200.00"),
        product_investment_share=44,
        go_to_market_share=32,
        reserve_share=24,
    )
    state.finance.debt_principal = Decimal("3600.00")
    state.finance.covenant_risk = 18
    state.event_history.append(
        EventHistoryEntry(
            event_id="independence_reckoning",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Independence Reckoning",
            triggered_turn=19,
            resolved_turn=19,
            selected_option_id="double_down_efficiency",
            selected_option_label="Double down on efficiency",
            result_text="Efficiency path chosen.",
        )
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "independence_cash_crunch"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "cut_to_reserve")

    assert outcome.state.capital_plan.reserve_share > state.capital_plan.reserve_share
    assert outcome.state.capital_plan.go_to_market_share < state.capital_plan.go_to_market_share
    assert outcome.state.capital_plan.mode is CapitalPlanMode.CONSERVE
    assert outcome.history_entry.event_id == "independence_cash_crunch"


def test_independence_refinancing_wall_event_can_lock_reserve_discipline() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="independence_compounder",
    )
    state.company.current_turn = 21
    state.company.cash_on_hand = Decimal("3000.00")
    state.company.reputation = 92
    state.finance.board_confidence = 0
    state.finance.board_score = 0
    state.finance.governance_risk = 55
    state.finance.board_team_health_score = 96
    state.finance.board_pressure = 18
    state.finance.investor_pressure = 0
    state.finance.covenant_risk = 18
    state.finance.debt_principal = Decimal("3600.00")
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.BALANCED,
        source_preference=CapitalSourcePreference.BOOTSTRAP,
        planning_horizon_turns=6,
        reserve_target=Decimal("4200.00"),
        product_investment_share=44,
        go_to_market_share=32,
        reserve_share=24,
    )
    state.event_history.append(
        EventHistoryEntry(
            event_id="independence_cash_crunch",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Independence Cash Crunch",
            triggered_turn=20,
            resolved_turn=20,
            selected_option_id="cut_to_reserve",
            selected_option_label="Cut to reserve",
            result_text="Reserve path chosen.",
        )
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "independence_refinancing_wall"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "lock_reserve_discipline")

    assert outcome.state.capital_plan.reserve_share > state.capital_plan.reserve_share
    assert outcome.state.capital_plan.go_to_market_share < state.capital_plan.go_to_market_share
    assert outcome.state.capital_plan.mode is CapitalPlanMode.CONSERVE
    assert outcome.state.finance.covenant_risk < state.finance.covenant_risk
    assert outcome.history_entry.event_id == "independence_refinancing_wall"


def test_independence_profit_floor_event_can_lock_profit_floor() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="independence_compounder",
    )
    state.company.current_turn = 22
    state.company.cash_on_hand = Decimal("3000.00")
    state.company.reputation = 90
    state.finance.board_confidence = 0
    state.finance.board_score = 0
    state.finance.governance_risk = 54
    state.finance.board_team_health_score = 94
    state.finance.board_pressure = 18
    state.finance.investor_pressure = 0
    state.finance.covenant_risk = 18
    state.finance.debt_principal = Decimal("3600.00")
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.BALANCED,
        source_preference=CapitalSourcePreference.BOOTSTRAP,
        planning_horizon_turns=6,
        reserve_target=Decimal("4200.00"),
        product_investment_share=44,
        go_to_market_share=32,
        reserve_share=24,
    )
    state.event_history.append(
        EventHistoryEntry(
            event_id="independence_refinancing_wall",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Independence Refinancing Wall",
            triggered_turn=21,
            resolved_turn=21,
            selected_option_id="lock_reserve_discipline",
            selected_option_label="Lock reserve discipline",
            result_text="Reserve discipline tightened.",
        )
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "independence_profit_floor"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "lock_profit_floor")

    assert outcome.state.capital_plan.reserve_share > state.capital_plan.reserve_share
    assert outcome.state.capital_plan.go_to_market_share < state.capital_plan.go_to_market_share
    assert outcome.state.capital_plan.mode is CapitalPlanMode.CONSERVE
    assert outcome.state.finance.covenant_risk < state.finance.covenant_risk
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.history_entry.event_id == "independence_profit_floor"


def test_independence_operating_covenant_event_can_commit_operating_floor() -> None:
    state = create_new_game(DEFAULT_COMPANY_NAME, DEFAULT_PRODUCT_NAME)
    state.company.current_turn = 23
    state.company.cash_on_hand = Decimal("9000.00")
    state.company.reputation = 72
    state.products[0].user_count = 6
    state.products[0].quality = 30
    state.products[0].market_fit = 26
    state.products[0].lifecycle_stage = LifecycleStage.MATURE
    state.finance.board_confidence = 0
    state.finance.board_score = 0
    state.finance.governance_risk = 40
    state.finance.board_team_health_score = 90
    state.finance.board_pressure = 16
    state.finance.investor_pressure = 8
    state.finance.covenant_risk = 24
    state.finance.debt_principal = Decimal("9200.00")
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.BALANCED,
        source_preference=CapitalSourcePreference.BOOTSTRAP,
        planning_horizon_turns=6,
        reserve_target=Decimal("14000.00"),
        product_investment_share=46,
        go_to_market_share=31,
        reserve_share=23,
    )
    state.event_history.append(
        EventHistoryEntry(
            event_id="independence_profit_floor",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Independence Profit Floor",
            triggered_turn=22,
            resolved_turn=22,
            selected_option_id="lock_profit_floor",
            selected_option_label="Lock the profit floor",
            result_text="Profit floor tightened.",
        )
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "independence_operating_covenant"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "commit_operating_floor")

    assert outcome.state.capital_plan.reserve_share > state.capital_plan.reserve_share
    assert outcome.state.capital_plan.go_to_market_share < state.capital_plan.go_to_market_share
    assert outcome.state.capital_plan.mode is CapitalPlanMode.CONSERVE
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.covenant_risk < state.finance.covenant_risk
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.reputation < state.company.reputation
    assert outcome.history_entry.event_id == "independence_operating_covenant"


def test_independence_buffer_ratchet_event_can_ratchet_buffer() -> None:
    product = make_product("Independence Buffer Core", lifecycle_stage=LifecycleStage.MATURE)
    state = make_state(product, cash_on_hand=Decimal("3200.00"), current_turn=24)
    state.company.reputation = 90
    state.finance.board_confidence = 8
    state.finance.board_score = 6
    state.finance.governance_risk = 46
    state.finance.board_team_health_score = 96
    state.finance.board_pressure = 18
    state.finance.investor_pressure = 12
    state.finance.covenant_risk = 20
    state.finance.debt_principal = Decimal("3600.00")
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.BALANCED,
        source_preference=CapitalSourcePreference.BOOTSTRAP,
        planning_horizon_turns=6,
        reserve_target=Decimal("4200.00"),
        product_investment_share=44,
        go_to_market_share=32,
        reserve_share=24,
    )
    state.event_history.append(
        EventHistoryEntry(
            event_id="independence_operating_covenant",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Independence Operating Covenant",
            triggered_turn=23,
            resolved_turn=23,
            selected_option_id="commit_operating_floor",
            selected_option_label="Commit to a harder operating floor",
            result_text="Operating floor committed.",
        )
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "independence_buffer_ratchet"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "ratchet_buffer")

    assert outcome.state.capital_plan.reserve_share > state.capital_plan.reserve_share
    assert outcome.state.capital_plan.go_to_market_share < state.capital_plan.go_to_market_share
    assert outcome.state.capital_plan.mode is CapitalPlanMode.CONSERVE
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.covenant_risk < state.finance.covenant_risk
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.reputation < state.company.reputation
    assert outcome.history_entry.event_id == "independence_buffer_ratchet"


def test_independence_cash_yield_pact_event_can_ratify_pact() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="independence_compounder",
    )
    state.company.current_turn = 25
    state.company.cash_on_hand = Decimal("3100.00")
    state.company.reputation = 90
    state.finance.board_confidence = 10
    state.finance.board_score = 8
    state.finance.governance_risk = 42
    state.finance.board_team_health_score = 96
    state.finance.board_pressure = 18
    state.finance.investor_pressure = 12
    state.finance.covenant_risk = 20
    state.finance.debt_principal = Decimal("3600.00")
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.BALANCED,
        source_preference=CapitalSourcePreference.BOOTSTRAP,
        planning_horizon_turns=6,
        reserve_target=Decimal("4200.00"),
        product_investment_share=44,
        go_to_market_share=32,
        reserve_share=24,
    )
    state.event_history.append(
        EventHistoryEntry(
            event_id="independence_buffer_ratchet",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Independence Buffer Ratchet",
            triggered_turn=24,
            resolved_turn=24,
            selected_option_id="ratchet_buffer",
            selected_option_label="Ratchet the buffer",
            result_text="Buffer ratcheted higher.",
        )
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "independence_cash_yield_pact"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "ratify_cash_yield_pact")

    assert outcome.state.capital_plan.reserve_share > state.capital_plan.reserve_share
    assert outcome.state.capital_plan.go_to_market_share < state.capital_plan.go_to_market_share
    assert outcome.state.capital_plan.mode is CapitalPlanMode.CONSERVE
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.covenant_risk < state.finance.covenant_risk
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.reputation < state.company.reputation
    assert outcome.history_entry.event_id == "independence_cash_yield_pact"


def test_independence_treasury_compact_event_can_ratify_compact() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="independence_compounder",
    )
    state.company.current_turn = 26
    state.company.cash_on_hand = Decimal("3200.00")
    state.company.reputation = 88
    state.finance.board_confidence = 12
    state.finance.board_score = 8
    state.finance.governance_risk = 42
    state.finance.board_team_health_score = 96
    state.finance.board_pressure = 18
    state.finance.investor_pressure = 14
    state.finance.covenant_risk = 20
    state.finance.debt_principal = Decimal("3800.00")
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.BALANCED,
        source_preference=CapitalSourcePreference.BOOTSTRAP,
        planning_horizon_turns=6,
        reserve_target=Decimal("4200.00"),
        product_investment_share=44,
        go_to_market_share=32,
        reserve_share=24,
    )
    state.event_history.append(
        EventHistoryEntry(
            event_id="independence_cash_yield_pact",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Independence Cash Yield Pact",
            triggered_turn=25,
            resolved_turn=25,
            selected_option_id="ratify_cash_yield_pact",
            selected_option_label="Ratify the cash-yield pact",
            result_text="Cash-yield pact ratified.",
        )
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "independence_treasury_compact"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "ratify_treasury_compact")

    assert outcome.state.capital_plan.mode is CapitalPlanMode.CONSERVE
    assert outcome.state.capital_plan.reserve_share > state.capital_plan.reserve_share
    assert outcome.state.capital_plan.go_to_market_share < state.capital_plan.go_to_market_share
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.covenant_risk < state.finance.covenant_risk
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.reputation < state.company.reputation
    assert outcome.history_entry.event_id == "independence_treasury_compact"


def test_independence_cash_command_event_can_ratify_command() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="independence_compounder",
    )
    state.company.current_turn = 27
    state.company.cash_on_hand = Decimal("3100.00")
    state.company.reputation = 88
    state.finance.board_confidence = 14
    state.finance.board_score = 10
    state.finance.governance_risk = 44
    state.finance.board_team_health_score = 96
    state.finance.board_pressure = 20
    state.finance.investor_pressure = 16
    state.finance.covenant_risk = 20
    state.finance.debt_principal = Decimal("3900.00")
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.BALANCED,
        source_preference=CapitalSourcePreference.BOOTSTRAP,
        planning_horizon_turns=6,
        reserve_target=Decimal("4300.00"),
        product_investment_share=44,
        go_to_market_share=32,
        reserve_share=24,
    )
    state.event_history.append(
        EventHistoryEntry(
            event_id="independence_treasury_compact",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Independence Treasury Compact",
            triggered_turn=26,
            resolved_turn=26,
            selected_option_id="ratify_treasury_compact",
            selected_option_label="Ratify the treasury compact",
            result_text="Treasury compact ratified.",
        )
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "independence_cash_command"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "ratify_cash_command")

    assert outcome.state.capital_plan.mode is CapitalPlanMode.CONSERVE
    assert outcome.state.capital_plan.reserve_share > state.capital_plan.reserve_share
    assert outcome.state.capital_plan.go_to_market_share < state.capital_plan.go_to_market_share
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.covenant_risk < state.finance.covenant_risk
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.reputation < state.company.reputation
    assert outcome.history_entry.event_id == "independence_cash_command"


def test_partner_breakdown_event_can_trigger_from_hotspot_dependency_score() -> None:
    product = make_product(
        "Channel Fragility Core",
        lifecycle_stage=LifecycleStage.MATURE,
        user_count=210,
        quality=72,
        market_fit=70,
    )
    state = make_state(
        product,
        partnerships=[
            PartnershipDeal(
                name="Integration Hotspot",
                product_id=product.id,
                channel=PartnerChannel.INTEGRATION,
                status=PartnershipStatus.RECOVERY,
                quality=60,
                risk=56,
                conflict_pressure=54,
                enablement_level=28,
                sourced_revenue=Decimal("3400.00"),
                rev_share_rate=Decimal("0.2400"),
            ),
            PartnershipDeal(
                name="Integration Tail",
                product_id=product.id,
                channel=PartnerChannel.INTEGRATION,
                status=PartnershipStatus.STRAINED,
                quality=58,
                risk=54,
                conflict_pressure=52,
                enablement_level=30,
                sourced_revenue=Decimal("1800.00"),
                rev_share_rate=Decimal("0.2300"),
            ),
        ],
        event_history=[
            EventHistoryEntry(
                event_id="partner_qbr",
                category=EventCategory.MARKET_OPPORTUNITY,
                title="Channel Partner QBR",
                triggered_turn=14,
                resolved_turn=14,
                selected_option_id="double_enablement",
                selected_option_label="Double down on enablement",
                result_text="Partner friction remained active despite more investment.",
            )
        ],
        current_turn=16,
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "partner_breakdown"
    )
    portfolio = calculate_partnership_portfolio(state)

    assert (
        portfolio.hotspot_dependency_score
        >= BALANCE.finance_planner_reactivate_dependency_threshold
    )
    assert definition.is_eligible(state) is True


def test_reseller_enablement_gap_event_can_fund_reset() -> None:
    product = make_product("Reseller Enablement Core", lifecycle_stage=LifecycleStage.MATURE)
    account = CustomerAccount(
        name="Reseller Renewal",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("1800.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=54,
        onboarding_health=58,
        support_load=20,
        open_tickets=3,
        renewal_health=46,
        expansion_potential=58,
        renewal_turn=8,
        churn_risk=24,
        status=CustomerAccountStatus.AT_RISK,
    )
    partnership = PartnershipDeal(
        name="Enablement Reseller",
        product_id=product.id,
        channel=PartnerChannel.RESELLER,
        status=PartnershipStatus.STRAINED,
        quality=62,
        risk=50,
        conflict_pressure=48,
        enablement_level=24,
        sourced_revenue=Decimal("2400.00"),
        sourced_users=32,
        rev_share_rate=Decimal("0.1800"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        event_history=[
            EventHistoryEntry(
                event_id="partner_qbr",
                category=EventCategory.MARKET_OPPORTUNITY,
                title="Channel Partner QBR",
                triggered_turn=10,
                resolved_turn=10,
                selected_option_id="double_enablement",
                selected_option_label="Double down on enablement",
                result_text="Enablement still lagged.",
            )
        ],
        current_turn=12,
        cash_on_hand=Decimal("6200.00"),
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "reseller_enablement_gap"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "fund_enablement_gap")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.partnerships[0].enablement_level > state.partnerships[0].enablement_level
    assert outcome.state.customer_accounts[0].satisfaction > state.customer_accounts[0].satisfaction
    assert (
        outcome.state.customer_accounts[0].renewal_health
        > state.customer_accounts[0].renewal_health
    )
    assert outcome.history_entry.event_id == "reseller_enablement_gap"


def test_integration_cutover_risk_event_can_staff_team() -> None:
    product = make_product("Integration Cutover Core", lifecycle_stage=LifecycleStage.MATURE)
    account = CustomerAccount(
        name="Implementation Account",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2600.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=56,
        onboarding_health=40,
        support_load=28,
        open_tickets=5,
        renewal_health=52,
        expansion_potential=62,
        renewal_turn=9,
        churn_risk=22,
        status=CustomerAccountStatus.ACTIVE,
    )
    partnership = PartnershipDeal(
        name="Cutover Integration",
        product_id=product.id,
        channel=PartnerChannel.INTEGRATION,
        status=PartnershipStatus.RECOVERY,
        quality=60,
        risk=56,
        conflict_pressure=50,
        enablement_level=28,
        sourced_revenue=Decimal("3200.00"),
        sourced_users=36,
        rev_share_rate=Decimal("0.2100"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        event_history=[
            EventHistoryEntry(
                event_id="partner_breakdown",
                category=EventCategory.MARKET_OPPORTUNITY,
                title="Partner Breakdown",
                triggered_turn=11,
                resolved_turn=11,
                selected_option_id="fund_recovery",
                selected_option_label="Fund recovery",
                result_text="Partner recovery started.",
            )
        ],
        current_turn=13,
        cash_on_hand=Decimal("6400.00"),
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "integration_cutover_risk"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "staff_cutover_team")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.partnerships[0].enablement_level > state.partnerships[0].enablement_level
    assert (
        outcome.state.customer_accounts[0].onboarding_health
        > state.customer_accounts[0].onboarding_health
    )
    assert outcome.state.customer_accounts[0].support_load < state.customer_accounts[0].support_load
    assert outcome.history_entry.event_id == "integration_cutover_risk"


def test_marketplace_chargeback_wave_event_can_fund_ops() -> None:
    product = make_product("Marketplace Chargeback Core", lifecycle_stage=LifecycleStage.MATURE)
    account = CustomerAccount(
        name="Marketplace Billing Anchor",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("2100.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=54,
        onboarding_health=60,
        support_load=24,
        open_tickets=4,
        renewal_health=48,
        expansion_potential=54,
        renewal_turn=8,
        churn_risk=26,
        invoice_risk=32,
        failed_payment_risk=28,
        status=CustomerAccountStatus.AT_RISK,
    )
    partnership = PartnershipDeal(
        name="Marketplace Billing Lane",
        product_id=product.id,
        channel=PartnerChannel.MARKETPLACE,
        status=PartnershipStatus.STRAINED,
        quality=60,
        risk=52,
        conflict_pressure=46,
        enablement_level=30,
        sourced_revenue=Decimal("2800.00"),
        sourced_users=34,
        rev_share_rate=Decimal("0.2200"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        event_history=[
            EventHistoryEntry(
                event_id="channel_concentration_crackdown",
                category=EventCategory.MARKET_OPPORTUNITY,
                title="Marketplace Concentration Crackdown",
                triggered_turn=12,
                resolved_turn=12,
                selected_option_id="fund_firebreak",
                selected_option_label="Fund a channel firebreak",
                result_text="Channel concentration cooled.",
            )
        ],
        current_turn=14,
        cash_on_hand=Decimal("6500.00"),
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "marketplace_chargeback_wave"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "fund_chargeback_ops")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.customer_accounts[0].invoice_risk < state.customer_accounts[0].invoice_risk
    assert (
        outcome.state.customer_accounts[0].failed_payment_risk
        < state.customer_accounts[0].failed_payment_risk
    )
    assert (
        outcome.state.customer_accounts[0].renewal_health
        > state.customer_accounts[0].renewal_health
    )
    assert outcome.history_entry.event_id == "marketplace_chargeback_wave"


def test_reseller_reference_summit_event_can_fund_reset() -> None:
    product = make_product("Reseller Summit Core", lifecycle_stage=LifecycleStage.MATURE)
    account = CustomerAccount(
        name="Reseller Anchor",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("1800.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=54,
        onboarding_health=58,
        support_load=20,
        open_tickets=3,
        renewal_health=46,
        expansion_potential=58,
        renewal_turn=8,
        churn_risk=24,
        status=CustomerAccountStatus.AT_RISK,
    )
    partnership = PartnershipDeal(
        name="Summit Reseller",
        product_id=product.id,
        channel=PartnerChannel.RESELLER,
        status=PartnershipStatus.STRAINED,
        quality=62,
        risk=52,
        conflict_pressure=50,
        enablement_level=24,
        sourced_revenue=Decimal("2500.00"),
        sourced_users=33,
        rev_share_rate=Decimal("0.1800"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        event_history=[
            EventHistoryEntry(
                event_id="reseller_enablement_gap",
                category=EventCategory.MARKET_OPPORTUNITY,
                title="Reseller Enablement Gap",
                triggered_turn=12,
                resolved_turn=12,
                selected_option_id="fund_enablement_gap",
                selected_option_label="Fund the enablement gap",
                result_text="Enablement still needed tighter references.",
            )
        ],
        current_turn=14,
        cash_on_hand=Decimal("6500.00"),
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "reseller_reference_summit"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "fund_reseller_summit")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.partnerships[0].enablement_level > state.partnerships[0].enablement_level
    assert outcome.state.partnerships[0].status is PartnershipStatus.RECOVERY
    assert outcome.state.customer_accounts[0].satisfaction > state.customer_accounts[0].satisfaction
    assert (
        outcome.state.customer_accounts[0].renewal_health
        > state.customer_accounts[0].renewal_health
    )
    assert outcome.history_entry.event_id == "reseller_reference_summit"


def test_integration_cutover_board_event_can_fund_reset() -> None:
    product = make_product("Integration Board Core", lifecycle_stage=LifecycleStage.MATURE)
    account = CustomerAccount(
        name="Implementation Account",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2600.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=56,
        onboarding_health=40,
        support_load=28,
        open_tickets=5,
        renewal_health=52,
        expansion_potential=62,
        renewal_turn=9,
        churn_risk=22,
        status=CustomerAccountStatus.ACTIVE,
    )
    partnership = PartnershipDeal(
        name="Board Integration",
        product_id=product.id,
        channel=PartnerChannel.INTEGRATION,
        status=PartnershipStatus.RECOVERY,
        quality=60,
        risk=56,
        conflict_pressure=52,
        enablement_level=28,
        sourced_revenue=Decimal("3200.00"),
        sourced_users=36,
        rev_share_rate=Decimal("0.2100"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        event_history=[
            EventHistoryEntry(
                event_id="integration_cutover_risk",
                category=EventCategory.PRODUCT_INCIDENT,
                title="Integration Cutover Risk",
                triggered_turn=13,
                resolved_turn=13,
                selected_option_id="staff_cutover_team",
                selected_option_label="Staff the cutover team",
                result_text="Integration cutover still needed governance.",
            )
        ],
        current_turn=15,
        cash_on_hand=Decimal("6600.00"),
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "integration_cutover_board"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "fund_cutover_board")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.partnerships[0].enablement_level > state.partnerships[0].enablement_level
    assert (
        outcome.state.customer_accounts[0].onboarding_health
        > state.customer_accounts[0].onboarding_health
    )
    assert outcome.state.customer_accounts[0].support_load < state.customer_accounts[0].support_load
    assert outcome.history_entry.event_id == "integration_cutover_board"


def test_marketplace_dispute_program_event_can_fund_reset() -> None:
    product = make_product("Marketplace Dispute Core", lifecycle_stage=LifecycleStage.MATURE)
    account = CustomerAccount(
        name="Marketplace Billing Anchor",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("2100.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=54,
        onboarding_health=60,
        support_load=24,
        open_tickets=4,
        renewal_health=48,
        expansion_potential=54,
        renewal_turn=8,
        churn_risk=26,
        invoice_risk=32,
        failed_payment_risk=28,
        status=CustomerAccountStatus.AT_RISK,
    )
    partnership = PartnershipDeal(
        name="Dispute Marketplace",
        product_id=product.id,
        channel=PartnerChannel.MARKETPLACE,
        status=PartnershipStatus.STRAINED,
        quality=60,
        risk=52,
        conflict_pressure=46,
        enablement_level=30,
        sourced_revenue=Decimal("2800.00"),
        sourced_users=34,
        rev_share_rate=Decimal("0.2200"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        event_history=[
            EventHistoryEntry(
                event_id="marketplace_chargeback_wave",
                category=EventCategory.REPUTATION_INCIDENT,
                title="Marketplace Chargeback Wave",
                triggered_turn=14,
                resolved_turn=14,
                selected_option_id="fund_chargeback_ops",
                selected_option_label="Fund chargeback ops",
                result_text="Marketplace billing still needed harder dispute control.",
            )
        ],
        current_turn=16,
        cash_on_hand=Decimal("6600.00"),
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "marketplace_dispute_program"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "fund_dispute_program")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.customer_accounts[0].invoice_risk < state.customer_accounts[0].invoice_risk
    assert (
        outcome.state.customer_accounts[0].failed_payment_risk
        < state.customer_accounts[0].failed_payment_risk
    )
    assert (
        outcome.state.customer_accounts[0].renewal_health
        > state.customer_accounts[0].renewal_health
    )
    assert outcome.history_entry.event_id == "marketplace_dispute_program"


def test_reseller_commitment_review_event_can_fund_reset() -> None:
    product = make_product("Reseller Commitment Core", lifecycle_stage=LifecycleStage.MATURE)
    account = CustomerAccount(
        name="Commitment Account",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("1850.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=56,
        onboarding_health=58,
        support_load=20,
        open_tickets=3,
        renewal_health=48,
        expansion_potential=60,
        renewal_turn=8,
        churn_risk=24,
        status=CustomerAccountStatus.AT_RISK,
    )
    partnership = PartnershipDeal(
        name="Commitment Reseller",
        product_id=product.id,
        channel=PartnerChannel.RESELLER,
        status=PartnershipStatus.STRAINED,
        quality=62,
        risk=54,
        conflict_pressure=52,
        enablement_level=26,
        sourced_revenue=Decimal("2600.00"),
        sourced_users=34,
        rev_share_rate=Decimal("0.1850"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        event_history=[
            EventHistoryEntry(
                event_id="reseller_reference_summit",
                category=EventCategory.MARKET_OPPORTUNITY,
                title="Reseller Reference Summit",
                triggered_turn=15,
                resolved_turn=15,
                selected_option_id="fund_reseller_summit",
                selected_option_label="Fund the reseller summit",
                result_text="Reseller summit still needed a harder commitment review.",
            )
        ],
        current_turn=17,
        cash_on_hand=Decimal("6700.00"),
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "reseller_commitment_review"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "fund_commitment_review")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.partnerships[0].enablement_level > state.partnerships[0].enablement_level
    assert outcome.state.partnerships[0].status is PartnershipStatus.RECOVERY
    assert outcome.state.customer_accounts[0].satisfaction > state.customer_accounts[0].satisfaction
    assert (
        outcome.state.customer_accounts[0].renewal_health
        > state.customer_accounts[0].renewal_health
    )
    assert outcome.history_entry.event_id == "reseller_commitment_review"


def test_reseller_margin_council_event_can_fund_reset() -> None:
    product = make_product("Reseller Margin Council Core", lifecycle_stage=LifecycleStage.MATURE)
    account = CustomerAccount(
        name="Margin Council Account",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("1850.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=56,
        onboarding_health=58,
        support_load=20,
        open_tickets=3,
        renewal_health=48,
        expansion_potential=60,
        renewal_turn=8,
        churn_risk=24,
        status=CustomerAccountStatus.AT_RISK,
    )
    partnership = PartnershipDeal(
        name="Margin Council Reseller",
        product_id=product.id,
        channel=PartnerChannel.RESELLER,
        status=PartnershipStatus.STRAINED,
        quality=62,
        risk=56,
        conflict_pressure=54,
        enablement_level=26,
        sourced_revenue=Decimal("2700.00"),
        sourced_users=35,
        rev_share_rate=Decimal("0.1900"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        event_history=[
            EventHistoryEntry(
                event_id="reseller_commitment_review",
                category=EventCategory.MARKET_OPPORTUNITY,
                title="Reseller Commitment Review",
                triggered_turn=16,
                resolved_turn=16,
                selected_option_id="fund_commitment_review",
                selected_option_label="Fund the commitment review",
                result_text="Commitment review funded.",
            )
        ],
        current_turn=18,
        cash_on_hand=Decimal("6700.00"),
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "reseller_margin_council"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "fund_margin_council")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.partnerships[0].enablement_level > state.partnerships[0].enablement_level
    assert outcome.state.partnerships[0].status is PartnershipStatus.RECOVERY
    assert outcome.state.customer_accounts[0].satisfaction > state.customer_accounts[0].satisfaction
    assert (
        outcome.state.customer_accounts[0].renewal_health
        > state.customer_accounts[0].renewal_health
    )
    assert outcome.history_entry.event_id == "reseller_margin_council"


def test_integration_release_cutline_event_can_staff_review() -> None:
    product = make_product("Integration Cutline Core", lifecycle_stage=LifecycleStage.MATURE)
    account = CustomerAccount(
        name="Cutline Account",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2700.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=56,
        onboarding_health=42,
        support_load=30,
        open_tickets=5,
        renewal_health=52,
        expansion_potential=62,
        renewal_turn=9,
        churn_risk=22,
        status=CustomerAccountStatus.ACTIVE,
    )
    partnership = PartnershipDeal(
        name="Cutline Integration",
        product_id=product.id,
        channel=PartnerChannel.INTEGRATION,
        status=PartnershipStatus.RECOVERY,
        quality=60,
        risk=58,
        conflict_pressure=54,
        enablement_level=28,
        sourced_revenue=Decimal("3300.00"),
        sourced_users=36,
        rev_share_rate=Decimal("0.2100"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        event_history=[
            EventHistoryEntry(
                event_id="integration_cutover_board",
                category=EventCategory.PRODUCT_INCIDENT,
                title="Integration Cutover Board",
                triggered_turn=16,
                resolved_turn=16,
                selected_option_id="fund_cutover_board",
                selected_option_label="Fund the cutover board",
                result_text="Integration board still needed a harder release cutline.",
            )
        ],
        current_turn=18,
        cash_on_hand=Decimal("6800.00"),
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "integration_release_cutline"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "staff_release_cutline")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.partnerships[0].enablement_level > state.partnerships[0].enablement_level
    assert (
        outcome.state.customer_accounts[0].onboarding_health
        > state.customer_accounts[0].onboarding_health
    )
    assert outcome.state.customer_accounts[0].support_load < state.customer_accounts[0].support_load
    assert outcome.history_entry.event_id == "integration_release_cutline"


def test_integration_support_bridge_event_can_fund_bridge() -> None:
    product = make_product("Integration Support Bridge Core", lifecycle_stage=LifecycleStage.MATURE)
    account = CustomerAccount(
        name="Bridge Account",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2700.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=56,
        onboarding_health=42,
        support_load=30,
        open_tickets=5,
        renewal_health=52,
        expansion_potential=62,
        renewal_turn=9,
        churn_risk=22,
        status=CustomerAccountStatus.ACTIVE,
    )
    partnership = PartnershipDeal(
        name="Bridge Integration",
        product_id=product.id,
        channel=PartnerChannel.INTEGRATION,
        status=PartnershipStatus.RECOVERY,
        quality=60,
        risk=58,
        conflict_pressure=56,
        enablement_level=28,
        sourced_revenue=Decimal("3350.00"),
        sourced_users=36,
        rev_share_rate=Decimal("0.2100"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        event_history=[
            EventHistoryEntry(
                event_id="integration_release_cutline",
                category=EventCategory.PRODUCT_INCIDENT,
                title="Integration Release Cutline",
                triggered_turn=17,
                resolved_turn=17,
                selected_option_id="staff_release_cutline",
                selected_option_label="Staff the release cutline",
                result_text="Release cutline staffed.",
            )
        ],
        current_turn=19,
        cash_on_hand=Decimal("6800.00"),
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "integration_support_bridge"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "fund_support_bridge")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.partnerships[0].enablement_level > state.partnerships[0].enablement_level
    assert (
        outcome.state.customer_accounts[0].onboarding_health
        > state.customer_accounts[0].onboarding_health
    )
    assert outcome.state.customer_accounts[0].support_load < state.customer_accounts[0].support_load
    assert outcome.history_entry.event_id == "integration_support_bridge"


def test_marketplace_refund_charter_event_can_fund_reset() -> None:
    product = make_product("Refund Charter Core", lifecycle_stage=LifecycleStage.MATURE)
    account = CustomerAccount(
        name="Refund Charter Account",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("2200.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=54,
        onboarding_health=60,
        support_load=24,
        open_tickets=4,
        renewal_health=48,
        expansion_potential=54,
        renewal_turn=8,
        churn_risk=26,
        invoice_risk=34,
        failed_payment_risk=30,
        status=CustomerAccountStatus.AT_RISK,
    )
    partnership = PartnershipDeal(
        name="Refund Marketplace",
        product_id=product.id,
        channel=PartnerChannel.MARKETPLACE,
        status=PartnershipStatus.STRAINED,
        quality=60,
        risk=54,
        conflict_pressure=48,
        enablement_level=30,
        sourced_revenue=Decimal("2900.00"),
        sourced_users=34,
        rev_share_rate=Decimal("0.2200"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        event_history=[
            EventHistoryEntry(
                event_id="marketplace_dispute_program",
                category=EventCategory.REPUTATION_INCIDENT,
                title="Marketplace Dispute Program",
                triggered_turn=17,
                resolved_turn=17,
                selected_option_id="fund_dispute_program",
                selected_option_label="Fund the dispute program",
                result_text="Marketplace dispute control still needed a harder refund charter.",
            )
        ],
        current_turn=19,
        cash_on_hand=Decimal("6800.00"),
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "marketplace_refund_charter"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "fund_refund_charter")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.customer_accounts[0].invoice_risk < state.customer_accounts[0].invoice_risk
    assert (
        outcome.state.customer_accounts[0].failed_payment_risk
        < state.customer_accounts[0].failed_payment_risk
    )
    assert (
        outcome.state.customer_accounts[0].renewal_health
        > state.customer_accounts[0].renewal_health
    )
    assert outcome.history_entry.event_id == "marketplace_refund_charter"


def test_marketplace_trust_reset_event_can_fund_reset() -> None:
    product = make_product("Marketplace Trust Reset Core", lifecycle_stage=LifecycleStage.MATURE)
    account = CustomerAccount(
        name="Trust Reset Account",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("2200.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=54,
        onboarding_health=60,
        support_load=24,
        open_tickets=4,
        renewal_health=48,
        expansion_potential=54,
        renewal_turn=8,
        churn_risk=26,
        invoice_risk=34,
        failed_payment_risk=30,
        status=CustomerAccountStatus.AT_RISK,
    )
    partnership = PartnershipDeal(
        name="Trust Reset Marketplace",
        product_id=product.id,
        channel=PartnerChannel.MARKETPLACE,
        status=PartnershipStatus.STRAINED,
        quality=60,
        risk=56,
        conflict_pressure=50,
        enablement_level=30,
        sourced_revenue=Decimal("3000.00"),
        sourced_users=35,
        rev_share_rate=Decimal("0.2200"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        event_history=[
            EventHistoryEntry(
                event_id="marketplace_refund_charter",
                category=EventCategory.REPUTATION_INCIDENT,
                title="Marketplace Refund Charter",
                triggered_turn=18,
                resolved_turn=18,
                selected_option_id="fund_refund_charter",
                selected_option_label="Fund the refund charter",
                result_text="Refund charter funded.",
            )
        ],
        current_turn=20,
        cash_on_hand=Decimal("6800.00"),
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "marketplace_trust_reset"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "fund_trust_reset")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.customer_accounts[0].invoice_risk < state.customer_accounts[0].invoice_risk
    assert (
        outcome.state.customer_accounts[0].failed_payment_risk
        < state.customer_accounts[0].failed_payment_risk
    )
    assert (
        outcome.state.customer_accounts[0].renewal_health
        > state.customer_accounts[0].renewal_health
    )
    assert outcome.history_entry.event_id == "marketplace_trust_reset"


def test_ipo_bookbuild_corridor_event_can_fund_corridor() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="ipo_readiness_launchpad",
    )
    product = state.products[0]
    state.company.current_turn = 26
    state.company.cash_on_hand = Decimal("5600.00")
    state.company.reputation = 84
    state.finance.board_confidence = 68
    state.finance.board_score = 62
    state.finance.board_pressure = 32
    state.finance.governance_risk = 48
    state.finance.board_warning_level = 2
    state.event_history.append(
        EventHistoryEntry(
            event_id="ipo_roadshow_lock",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="IPO Roadshow Lock",
            triggered_turn=25,
            resolved_turn=25,
            selected_option_id="fund_roadshow_lock",
            selected_option_label="Fund the roadshow lock",
            result_text="Roadshow lock funded.",
        )
    )
    state.customer_accounts = [
        CustomerAccount(
            name="Bookbuild Anchor",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("3600.00"),
            support_tier=SupportTier.WHITE_GLOVE,
            satisfaction=60,
            onboarding_health=54,
            support_load=30,
            open_tickets=7,
            sla_breach_risk=54,
            renewal_health=50,
            expansion_potential=68,
            renewal_turn=10,
            churn_risk=24,
            status=CustomerAccountStatus.ACTIVE,
        )
    ]
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "ipo_bookbuild_corridor"
    )

    assert definition.is_eligible(state) is True
    state.pending_event = definition.build_pending_event(
        state, FixedRandom(0), definition.cooldown_turns
    )

    outcome = resolve_pending_event(state, "fund_bookbuild_corridor")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.governance_risk < state.finance.governance_risk
    assert outcome.state.customer_accounts[0].support_load < state.customer_accounts[0].support_load
    assert (
        outcome.state.customer_accounts[0].renewal_health
        > state.customer_accounts[0].renewal_health
    )
    assert outcome.history_entry.event_id == "ipo_bookbuild_corridor"


def test_buyer_board_alignment_event_can_staff_alignment() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="acquisition_diligence_sprint",
    )
    product = state.products[0]
    state.company.current_turn = 24
    state.company.cash_on_hand = Decimal("5900.00")
    state.finance.board_confidence = 44
    state.finance.board_score = 40
    state.finance.board_pressure = 30
    state.finance.governance_risk = 24
    state.event_history.append(
        EventHistoryEntry(
            event_id="buyer_close_readiness",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Buyer Close Readiness",
            triggered_turn=23,
            resolved_turn=23,
            selected_option_id="staff_close_readiness",
            selected_option_label="Staff close readiness",
            result_text="Close readiness staffed.",
        )
    )
    state.customer_accounts = [
        CustomerAccount(
            name="Buyer Board Anchor",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("3000.00"),
            support_tier=SupportTier.WHITE_GLOVE,
            satisfaction=60,
            onboarding_health=56,
            support_load=28,
            open_tickets=5,
            sla_breach_risk=40,
            renewal_health=54,
            expansion_potential=64,
            renewal_turn=10,
            churn_risk=22,
            status=CustomerAccountStatus.ACTIVE,
        )
    ]
    state.partnerships = [
        PartnershipDeal(
            name="Buyer Board Integration",
            product_id=product.id,
            channel=PartnerChannel.INTEGRATION,
            status=PartnershipStatus.RECOVERY,
            quality=62,
            risk=58,
            conflict_pressure=54,
            enablement_level=28,
            sourced_revenue=Decimal("3200.00"),
            rev_share_rate=Decimal("0.2200"),
        )
    ]
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "buyer_board_alignment"
    )

    assert definition.is_eligible(state) is True
    state.pending_event = definition.build_pending_event(
        state, FixedRandom(0), definition.cooldown_turns
    )

    outcome = resolve_pending_event(state, "staff_board_alignment")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.partnerships[0].enablement_level > state.partnerships[0].enablement_level
    assert outcome.history_entry.event_id == "buyer_board_alignment"


def test_independence_liquidity_charter_event_can_ratify_charter() -> None:
    product = make_product("Liquidity Charter Core", lifecycle_stage=LifecycleStage.MATURE)
    state = make_state(
        product,
        cash_on_hand=Decimal("3500.00"),
        current_turn=18,
        finance=FinanceState(
            debt_principal=Decimal("3000.00"),
            loan_interest_rate=Decimal("0.0310"),
            investor_pressure=20,
            covenant_risk=22,
            board_confidence=62,
            board_pressure=22,
        ),
        event_history=[
            EventHistoryEntry(
                event_id="independence_cash_command",
                category=EventCategory.FUNDING_OPPORTUNITY,
                title="Independence Cash Command",
                triggered_turn=17,
                resolved_turn=17,
                selected_option_id="ratify_cash_command",
                selected_option_label="Ratify the cash command",
                result_text="Cash command ratified.",
            )
        ],
    )
    state.capital_plan.reserve_target = Decimal("5200.00")
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "independence_liquidity_charter"
    )

    assert definition.is_eligible(state) is True
    state.pending_event = definition.build_pending_event(
        state, FixedRandom(0), definition.cooldown_turns
    )

    outcome = resolve_pending_event(state, "ratify_liquidity_charter")

    assert outcome.state.capital_plan.mode is CapitalPlanMode.CONSERVE
    assert outcome.state.capital_plan.reserve_share > state.capital_plan.reserve_share
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.covenant_risk < state.finance.covenant_risk
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.history_entry.event_id == "independence_liquidity_charter"


def test_reseller_pipeline_cadence_event_can_fund_cadence() -> None:
    product = make_product("Pipeline Cadence Core", lifecycle_stage=LifecycleStage.MATURE)
    account = CustomerAccount(
        name="Cadence Account",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("1800.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=56,
        onboarding_health=58,
        support_load=20,
        open_tickets=3,
        renewal_health=48,
        expansion_potential=60,
        renewal_turn=8,
        churn_risk=24,
        status=CustomerAccountStatus.AT_RISK,
    )
    partnership = PartnershipDeal(
        name="Cadence Reseller",
        product_id=product.id,
        channel=PartnerChannel.RESELLER,
        status=PartnershipStatus.STRAINED,
        quality=62,
        risk=54,
        conflict_pressure=52,
        enablement_level=26,
        sourced_revenue=Decimal("2800.00"),
        sourced_users=36,
        rev_share_rate=Decimal("0.1900"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        event_history=[
            EventHistoryEntry(
                event_id="reseller_margin_council",
                category=EventCategory.MARKET_OPPORTUNITY,
                title="Reseller Margin Council",
                triggered_turn=18,
                resolved_turn=18,
                selected_option_id="fund_margin_council",
                selected_option_label="Fund the margin council",
                result_text="Margin council funded.",
            )
        ],
        current_turn=20,
        cash_on_hand=Decimal("6900.00"),
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "reseller_pipeline_cadence"
    )

    assert definition.is_eligible(state) is True
    state.pending_event = definition.build_pending_event(
        state, FixedRandom(0), definition.cooldown_turns
    )

    outcome = resolve_pending_event(state, "fund_pipeline_cadence")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.partnerships[0].enablement_level > state.partnerships[0].enablement_level
    assert outcome.state.partnerships[0].status is PartnershipStatus.RECOVERY
    assert (
        outcome.state.customer_accounts[0].renewal_health
        > state.customer_accounts[0].renewal_health
    )
    assert outcome.history_entry.event_id == "reseller_pipeline_cadence"


def test_integration_go_live_shield_event_can_fund_shield() -> None:
    product = make_product("Go Live Shield Core", lifecycle_stage=LifecycleStage.MATURE)
    account = CustomerAccount(
        name="Shield Account",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2800.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=56,
        onboarding_health=42,
        support_load=30,
        open_tickets=5,
        renewal_health=52,
        expansion_potential=62,
        renewal_turn=9,
        churn_risk=22,
        status=CustomerAccountStatus.ACTIVE,
    )
    partnership = PartnershipDeal(
        name="Shield Integration",
        product_id=product.id,
        channel=PartnerChannel.INTEGRATION,
        status=PartnershipStatus.RECOVERY,
        quality=60,
        risk=56,
        conflict_pressure=52,
        enablement_level=28,
        sourced_revenue=Decimal("3400.00"),
        sourced_users=38,
        rev_share_rate=Decimal("0.2100"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        event_history=[
            EventHistoryEntry(
                event_id="integration_support_bridge",
                category=EventCategory.PRODUCT_INCIDENT,
                title="Integration Support Bridge",
                triggered_turn=19,
                resolved_turn=19,
                selected_option_id="fund_support_bridge",
                selected_option_label="Fund the support bridge",
                result_text="Support bridge funded.",
            )
        ],
        current_turn=21,
        cash_on_hand=Decimal("7000.00"),
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "integration_go_live_shield"
    )

    assert definition.is_eligible(state) is True
    state.pending_event = definition.build_pending_event(
        state, FixedRandom(0), definition.cooldown_turns
    )

    outcome = resolve_pending_event(state, "fund_go_live_shield")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.partnerships[0].enablement_level > state.partnerships[0].enablement_level
    assert (
        outcome.state.customer_accounts[0].onboarding_health
        > state.customer_accounts[0].onboarding_health
    )
    assert outcome.state.customer_accounts[0].support_load < state.customer_accounts[0].support_load
    assert outcome.history_entry.event_id == "integration_go_live_shield"


def test_marketplace_policy_appeal_event_can_fund_appeal() -> None:
    product = make_product("Policy Appeal Core", lifecycle_stage=LifecycleStage.MATURE)
    account = CustomerAccount(
        name="Policy Appeal Account",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("2200.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=54,
        onboarding_health=60,
        support_load=24,
        open_tickets=4,
        renewal_health=48,
        expansion_potential=54,
        renewal_turn=8,
        churn_risk=26,
        invoice_risk=34,
        failed_payment_risk=30,
        status=CustomerAccountStatus.AT_RISK,
    )
    partnership = PartnershipDeal(
        name="Policy Marketplace",
        product_id=product.id,
        channel=PartnerChannel.MARKETPLACE,
        status=PartnershipStatus.STRAINED,
        quality=60,
        risk=54,
        conflict_pressure=48,
        enablement_level=30,
        sourced_revenue=Decimal("2900.00"),
        sourced_users=34,
        rev_share_rate=Decimal("0.2200"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        event_history=[
            EventHistoryEntry(
                event_id="marketplace_trust_reset",
                category=EventCategory.REPUTATION_INCIDENT,
                title="Marketplace Trust Reset",
                triggered_turn=20,
                resolved_turn=20,
                selected_option_id="fund_trust_reset",
                selected_option_label="Fund the trust reset",
                result_text="Trust reset funded.",
            )
        ],
        current_turn=22,
        cash_on_hand=Decimal("7000.00"),
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "marketplace_policy_appeal"
    )

    assert definition.is_eligible(state) is True
    state.pending_event = definition.build_pending_event(
        state, FixedRandom(0), definition.cooldown_turns
    )

    outcome = resolve_pending_event(state, "fund_policy_appeal")

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.customer_accounts[0].invoice_risk < state.customer_accounts[0].invoice_risk
    assert (
        outcome.state.customer_accounts[0].failed_payment_risk
        < state.customer_accounts[0].failed_payment_risk
    )
    assert (
        outcome.state.customer_accounts[0].renewal_health
        > state.customer_accounts[0].renewal_health
    )
    assert outcome.history_entry.event_id == "marketplace_policy_appeal"


def test_board_reset_trust_vote_event_can_ratify_vote() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="board_recovery_crucible",
    )
    state.company.current_turn = 26
    state.company.cash_on_hand = Decimal("5800.00")
    state.finance.board_pressure = 38
    state.finance.governance_risk = 46
    state.finance.board_confidence = 30
    state.finance.board_score = 28
    state.finance.board_portfolio_focus_score = 34
    state.finance.board_warning_level = 2
    state.finance.restructuring_pressure = 20
    state.finance.board_resolution_due = True
    state.event_history.append(
        EventHistoryEntry(
            event_id="board_reset_balance_sheet_treaty",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Board-Reset Balance-Sheet Treaty",
            triggered_turn=25,
            resolved_turn=25,
            selected_option_id="ratify_balance_sheet_treaty",
            selected_option_label="Ratify the balance-sheet treaty",
            result_text="Balance-sheet treaty ratified.",
        )
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "board_reset_trust_vote"
    )

    assert definition.is_eligible(state) is True
    state.pending_event = definition.build_pending_event(
        state, FixedRandom(0), definition.cooldown_turns
    )

    outcome = resolve_pending_event(state, "ratify_trust_vote")

    assert outcome.state.capital_plan.mode is CapitalPlanMode.CONSERVE
    assert outcome.state.capital_plan.reserve_share > state.capital_plan.reserve_share
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.governance_risk < state.finance.governance_risk
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.board_resolution_due is False
    assert outcome.history_entry.event_id == "board_reset_trust_vote"


def test_ipo_allocation_lock_event_can_fund_lock() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="ipo_readiness_launchpad",
    )
    product = state.products[0]
    state.company.current_turn = 27
    state.company.cash_on_hand = Decimal("5400.00")
    state.company.reputation = 84
    state.finance.board_confidence = 70
    state.finance.board_score = 64
    state.finance.board_pressure = 30
    state.finance.governance_risk = 44
    state.finance.board_warning_level = 2
    state.event_history.append(
        EventHistoryEntry(
            event_id="ipo_bookbuild_corridor",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="IPO Bookbuild Corridor",
            triggered_turn=26,
            resolved_turn=26,
            selected_option_id="fund_bookbuild_corridor",
            selected_option_label="Fund the bookbuild corridor",
            result_text="Bookbuild corridor funded.",
        )
    )
    state.customer_accounts = [
        CustomerAccount(
            name="Allocation Lock Anchor",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("3800.00"),
            support_tier=SupportTier.WHITE_GLOVE,
            satisfaction=62,
            onboarding_health=56,
            support_load=28,
            open_tickets=6,
            sla_breach_risk=50,
            renewal_health=52,
            expansion_potential=70,
            renewal_turn=10,
            churn_risk=22,
            status=CustomerAccountStatus.ACTIVE,
        )
    ]
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "ipo_allocation_lock"
    )

    assert definition.is_eligible(state) is True
    state.pending_event = definition.build_pending_event(
        state, FixedRandom(0), definition.cooldown_turns
    )

    outcome = resolve_pending_event(state, state.pending_event.options[0].id)

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.governance_risk < state.finance.governance_risk
    assert outcome.state.customer_accounts[0].support_load < state.customer_accounts[0].support_load
    assert (
        outcome.state.customer_accounts[0].renewal_health
        > state.customer_accounts[0].renewal_health
    )
    assert outcome.history_entry.event_id == "ipo_allocation_lock"


def test_buyer_close_cadence_event_can_staff_cadence() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="acquisition_diligence_sprint",
    )
    product = state.products[0]
    state.company.current_turn = 25
    state.company.cash_on_hand = Decimal("5800.00")
    state.finance.board_confidence = 46
    state.finance.board_score = 42
    state.finance.board_pressure = 28
    state.finance.governance_risk = 22
    state.event_history.append(
        EventHistoryEntry(
            event_id="buyer_board_alignment",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Buyer Board Alignment",
            triggered_turn=24,
            resolved_turn=24,
            selected_option_id="staff_board_alignment",
            selected_option_label="Staff the board alignment",
            result_text="Board alignment staffed.",
        )
    )
    state.customer_accounts = [
        CustomerAccount(
            name="Close Cadence Anchor",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("3200.00"),
            support_tier=SupportTier.WHITE_GLOVE,
            satisfaction=60,
            onboarding_health=54,
            support_load=26,
            open_tickets=5,
            sla_breach_risk=38,
            renewal_health=56,
            expansion_potential=62,
            renewal_turn=10,
            churn_risk=20,
            status=CustomerAccountStatus.ACTIVE,
        )
    ]
    state.partnerships = [
        PartnershipDeal(
            name="Close Cadence Integration",
            product_id=product.id,
            channel=PartnerChannel.INTEGRATION,
            status=PartnershipStatus.RECOVERY,
            quality=62,
            risk=56,
            conflict_pressure=52,
            enablement_level=30,
            sourced_revenue=Decimal("3300.00"),
            rev_share_rate=Decimal("0.2200"),
        )
    ]
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "buyer_close_cadence"
    )

    assert definition.is_eligible(state) is True
    state.pending_event = definition.build_pending_event(
        state, FixedRandom(0), definition.cooldown_turns
    )

    outcome = resolve_pending_event(state, state.pending_event.options[0].id)

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.partnerships[0].enablement_level > state.partnerships[0].enablement_level
    assert outcome.history_entry.event_id == "buyer_close_cadence"


def test_independence_margin_charter_event_can_ratify_charter() -> None:
    product = make_product("Margin Charter Core", lifecycle_stage=LifecycleStage.MATURE)
    state = make_state(
        product,
        cash_on_hand=Decimal("3300.00"),
        current_turn=19,
        finance=FinanceState(
            debt_principal=Decimal("3200.00"),
            loan_interest_rate=Decimal("0.0310"),
            investor_pressure=22,
            covenant_risk=24,
            board_confidence=60,
            board_pressure=24,
        ),
        event_history=[
            EventHistoryEntry(
                event_id="independence_liquidity_charter",
                category=EventCategory.FUNDING_OPPORTUNITY,
                title="Independence Liquidity Charter",
                triggered_turn=18,
                resolved_turn=18,
                selected_option_id="ratify_liquidity_charter",
                selected_option_label="Ratify the liquidity charter",
                result_text="Liquidity charter ratified.",
            )
        ],
    )
    state.capital_plan.reserve_target = Decimal("5400.00")
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "independence_margin_charter"
    )

    assert definition.is_eligible(state) is True
    state.pending_event = definition.build_pending_event(
        state, FixedRandom(0), definition.cooldown_turns
    )

    outcome = resolve_pending_event(state, state.pending_event.options[0].id)

    assert outcome.state.capital_plan.mode is CapitalPlanMode.CONSERVE
    assert outcome.state.capital_plan.reserve_share > state.capital_plan.reserve_share
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.covenant_risk < state.finance.covenant_risk
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.history_entry.event_id == "independence_margin_charter"


def test_reseller_recovery_compact_event_can_fund_compact() -> None:
    product = make_product("Recovery Compact Core", lifecycle_stage=LifecycleStage.MATURE)
    account = CustomerAccount(
        name="Compact Account",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("1800.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=56,
        onboarding_health=58,
        support_load=20,
        open_tickets=3,
        renewal_health=48,
        expansion_potential=60,
        renewal_turn=8,
        churn_risk=24,
        status=CustomerAccountStatus.AT_RISK,
    )
    partnership = PartnershipDeal(
        name="Compact Reseller",
        product_id=product.id,
        channel=PartnerChannel.RESELLER,
        status=PartnershipStatus.STRAINED,
        quality=62,
        risk=54,
        conflict_pressure=52,
        enablement_level=26,
        sourced_revenue=Decimal("2800.00"),
        sourced_users=36,
        rev_share_rate=Decimal("0.1900"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        event_history=[
            EventHistoryEntry(
                event_id="reseller_pipeline_cadence",
                category=EventCategory.MARKET_OPPORTUNITY,
                title="Reseller Pipeline Cadence",
                triggered_turn=19,
                resolved_turn=19,
                selected_option_id="fund_pipeline_cadence",
                selected_option_label="Fund the pipeline cadence",
                result_text="Pipeline cadence funded.",
            )
        ],
        current_turn=21,
        cash_on_hand=Decimal("6900.00"),
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "reseller_recovery_compact"
    )

    assert definition.is_eligible(state) is True
    state.pending_event = definition.build_pending_event(
        state, FixedRandom(0), definition.cooldown_turns
    )

    outcome = resolve_pending_event(state, state.pending_event.options[0].id)

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.partnerships[0].enablement_level > state.partnerships[0].enablement_level
    assert outcome.state.partnerships[0].status is PartnershipStatus.RECOVERY
    assert (
        outcome.state.customer_accounts[0].renewal_health
        > state.customer_accounts[0].renewal_health
    )
    assert outcome.history_entry.event_id == "reseller_recovery_compact"


def test_integration_cutover_command_event_can_fund_command() -> None:
    product = make_product("Cutover Command Core", lifecycle_stage=LifecycleStage.MATURE)
    account = CustomerAccount(
        name="Command Account",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2800.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=56,
        onboarding_health=42,
        support_load=30,
        open_tickets=5,
        renewal_health=52,
        expansion_potential=62,
        renewal_turn=9,
        churn_risk=22,
        status=CustomerAccountStatus.ACTIVE,
    )
    partnership = PartnershipDeal(
        name="Command Integration",
        product_id=product.id,
        channel=PartnerChannel.INTEGRATION,
        status=PartnershipStatus.RECOVERY,
        quality=60,
        risk=56,
        conflict_pressure=52,
        enablement_level=28,
        sourced_revenue=Decimal("3400.00"),
        sourced_users=38,
        rev_share_rate=Decimal("0.2100"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        event_history=[
            EventHistoryEntry(
                event_id="integration_go_live_shield",
                category=EventCategory.PRODUCT_INCIDENT,
                title="Integration Go-Live Shield",
                triggered_turn=20,
                resolved_turn=20,
                selected_option_id="fund_go_live_shield",
                selected_option_label="Fund the go-live shield",
                result_text="Go-live shield funded.",
            )
        ],
        current_turn=22,
        cash_on_hand=Decimal("7000.00"),
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "integration_cutover_command"
    )

    assert definition.is_eligible(state) is True
    state.pending_event = definition.build_pending_event(
        state, FixedRandom(0), definition.cooldown_turns
    )

    outcome = resolve_pending_event(state, state.pending_event.options[0].id)

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.partnerships[0].enablement_level > state.partnerships[0].enablement_level
    assert (
        outcome.state.customer_accounts[0].onboarding_health
        > state.customer_accounts[0].onboarding_health
    )
    assert outcome.state.customer_accounts[0].support_load < state.customer_accounts[0].support_load
    assert outcome.history_entry.event_id == "integration_cutover_command"


def test_marketplace_penalty_panel_event_can_fund_panel() -> None:
    product = make_product("Penalty Panel Core", lifecycle_stage=LifecycleStage.MATURE)
    account = CustomerAccount(
        name="Penalty Panel Account",
        product_id=product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("2200.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=54,
        onboarding_health=60,
        support_load=24,
        open_tickets=4,
        renewal_health=48,
        expansion_potential=54,
        renewal_turn=8,
        churn_risk=26,
        invoice_risk=34,
        failed_payment_risk=30,
        status=CustomerAccountStatus.AT_RISK,
    )
    partnership = PartnershipDeal(
        name="Penalty Marketplace",
        product_id=product.id,
        channel=PartnerChannel.MARKETPLACE,
        status=PartnershipStatus.STRAINED,
        quality=60,
        risk=54,
        conflict_pressure=48,
        enablement_level=30,
        sourced_revenue=Decimal("2900.00"),
        sourced_users=34,
        rev_share_rate=Decimal("0.2200"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        event_history=[
            EventHistoryEntry(
                event_id="marketplace_policy_appeal",
                category=EventCategory.REPUTATION_INCIDENT,
                title="Marketplace Policy Appeal",
                triggered_turn=21,
                resolved_turn=21,
                selected_option_id="fund_policy_appeal",
                selected_option_label="Fund the policy appeal",
                result_text="Policy appeal funded.",
            )
        ],
        current_turn=23,
        cash_on_hand=Decimal("7000.00"),
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "marketplace_penalty_panel"
    )

    assert definition.is_eligible(state) is True
    state.pending_event = definition.build_pending_event(
        state, FixedRandom(0), definition.cooldown_turns
    )

    outcome = resolve_pending_event(state, state.pending_event.options[0].id)

    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert outcome.state.partnerships[0].risk < state.partnerships[0].risk
    assert outcome.state.partnerships[0].conflict_pressure < state.partnerships[0].conflict_pressure
    assert outcome.state.customer_accounts[0].invoice_risk < state.customer_accounts[0].invoice_risk
    assert (
        outcome.state.customer_accounts[0].failed_payment_risk
        < state.customer_accounts[0].failed_payment_risk
    )
    assert (
        outcome.state.customer_accounts[0].renewal_health
        > state.customer_accounts[0].renewal_health
    )
    assert outcome.history_entry.event_id == "marketplace_penalty_panel"


def test_board_reset_cash_charter_event_can_ratify_charter() -> None:
    state = create_new_game(
        DEFAULT_COMPANY_NAME,
        DEFAULT_PRODUCT_NAME,
        campaign_start_id="board_recovery_crucible",
    )
    state.company.current_turn = 27
    state.company.cash_on_hand = Decimal("5600.00")
    state.finance.board_pressure = 36
    state.finance.governance_risk = 44
    state.finance.board_confidence = 34
    state.finance.board_score = 30
    state.finance.board_portfolio_focus_score = 36
    state.finance.board_warning_level = 2
    state.finance.restructuring_pressure = 22
    state.finance.board_resolution_due = True
    state.event_history.append(
        EventHistoryEntry(
            event_id="board_reset_trust_vote",
            category=EventCategory.FUNDING_OPPORTUNITY,
            title="Board-Reset Trust Vote",
            triggered_turn=26,
            resolved_turn=26,
            selected_option_id="ratify_trust_vote",
            selected_option_label="Ratify the trust vote",
            result_text="Trust vote ratified.",
        )
    )
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "board_reset_cash_charter"
    )

    assert definition.is_eligible(state) is True
    state.pending_event = definition.build_pending_event(
        state, FixedRandom(0), definition.cooldown_turns
    )

    outcome = resolve_pending_event(state, state.pending_event.options[0].id)

    assert outcome.state.capital_plan.mode is CapitalPlanMode.CONSERVE
    assert outcome.state.capital_plan.reserve_share > state.capital_plan.reserve_share
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.governance_risk < state.finance.governance_risk
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.finance.board_score > state.finance.board_score
    assert outcome.state.finance.board_resolution_due is False
    assert outcome.history_entry.event_id == "board_reset_cash_charter"


def test_create_partnership_action_adds_channel_and_cost() -> None:
    product = make_product("Channel Core", target_segment=MarketSegment.ENTERPRISE)
    state = make_state(product, cash_on_hand=Decimal("9000.00"))

    outcome = apply_action(
        state,
        TurnAction.CREATE_PARTNERSHIP,
        context=ActionContext(
            target_product_id=product.id,
            partner_channel=PartnerChannel.RESELLER,
        ),
    )

    assert len(outcome.state.partnerships) == 1
    assert outcome.state.partnerships[0].channel is PartnerChannel.RESELLER
    assert outcome.state.company.cash_on_hand == Decimal("8720.00")


def test_partnership_turn_summary_adds_users_revenue_and_support_pressure() -> None:
    product = make_product(
        "Partner API",
        market_fit=68,
        quality=72,
        bug_level=10,
        user_count=40,
        revenue_per_user=Decimal("32.00"),
    )
    partnership = PartnershipDeal(
        name="Partner API Integration",
        product_id=product.id,
        channel=PartnerChannel.INTEGRATION,
        status=PartnershipStatus.ACTIVE,
        quality=64,
        risk=18,
        enablement_level=46,
        rev_share_rate=Decimal("0.1400"),
    )
    state = make_state(product, partnerships=[partnership], cash_on_hand=Decimal("7000.00"))

    summary = apply_end_of_turn_partnerships(state)

    assert summary.sourced_users > 0
    assert summary.sourced_revenue > Decimal("0.00")
    assert state.support_program.onboarding_ticket_pressure > 0
    assert state.products[0].user_count > 40


def test_partner_breakdown_event_can_push_channel_into_recovery() -> None:
    product = make_product("Recovery Channel", market_fit=64, quality=68, bug_level=12)
    partnership = PartnershipDeal(
        name="Recovery Channel Reseller",
        product_id=product.id,
        channel=PartnerChannel.RESELLER,
        status=PartnershipStatus.STRAINED,
        quality=62,
        risk=54,
        conflict_pressure=57,
        enablement_level=34,
    )
    state = make_state(product, partnerships=[partnership], cash_on_hand=Decimal("6400.00"))
    state.pending_event = PendingEvent(
        event_id="partner_breakdown",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Partner Breakdown",
        description="Test event",
        triggered_turn=state.company.current_turn,
        cooldown_turns=5,
        target_product_id=product.id,
        options=[
            EventOption(id="fund_recovery", label="Recover", description="Recover"),
            EventOption(id="freeze_lane", label="Freeze", description="Freeze"),
        ],
    )

    outcome = resolve_pending_event(state, "fund_recovery")

    assert outcome.state.partnerships[0].status is PartnershipStatus.RECOVERY
    assert outcome.state.partnerships[0].conflict_pressure < partnership.conflict_pressure
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_partner_renegotiation_event_trades_margin_for_stability() -> None:
    product = make_product("Channel Terms", market_fit=66, quality=69, bug_level=14)
    partnership = PartnershipDeal(
        name="Channel Terms Marketplace",
        product_id=product.id,
        channel=PartnerChannel.MARKETPLACE,
        status=PartnershipStatus.STRAINED,
        quality=60,
        risk=48,
        conflict_pressure=44,
        enablement_level=34,
        sourced_revenue=Decimal("1200.00"),
        rev_share_rate=Decimal("0.1600"),
    )
    state = make_state(product, partnerships=[partnership], cash_on_hand=Decimal("6800.00"))
    state.pending_event = PendingEvent(
        event_id="partner_renegotiation",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Partner Renegotiation",
        description="Test event",
        triggered_turn=state.company.current_turn,
        cooldown_turns=5,
        target_product_id=product.id,
        options=[
            EventOption(id="concede_margin", label="Concede", description="Concede"),
            EventOption(id="hold_line", label="Hold", description="Hold"),
        ],
    )

    outcome = resolve_pending_event(state, "concede_margin")

    assert outcome.state.partnerships[0].status is PartnershipStatus.RECOVERY
    assert outcome.state.partnerships[0].rev_share_rate > partnership.rev_share_rate
    assert outcome.state.partnerships[0].conflict_pressure < partnership.conflict_pressure


def test_channel_concentration_crackdown_event_triggers_after_partner_breakdown() -> None:
    product = make_product(
        "Integration Density Core",
        lifecycle_stage=LifecycleStage.MATURE,
        user_count=240,
        quality=74,
        market_fit=72,
    )
    dominant = PartnershipDeal(
        name="Dominant Integration",
        product_id=product.id,
        channel=PartnerChannel.INTEGRATION,
        status=PartnershipStatus.RECOVERY,
        quality=60,
        risk=58,
        conflict_pressure=54,
        enablement_level=28,
        sourced_revenue=Decimal("3600.00"),
        sourced_users=44,
        rev_share_rate=Decimal("0.2200"),
    )
    tail = PartnershipDeal(
        name="Tail Integration",
        product_id=product.id,
        channel=PartnerChannel.INTEGRATION,
        status=PartnershipStatus.ACTIVE,
        quality=58,
        risk=24,
        conflict_pressure=18,
        enablement_level=34,
        sourced_revenue=Decimal("900.00"),
        sourced_users=12,
        rev_share_rate=Decimal("0.1800"),
    )
    account = CustomerAccount(
        name="Implementation Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2800.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=56,
        onboarding_health=38,
        support_load=28,
        open_tickets=5,
        sla_breach_risk=36,
        renewal_health=54,
        expansion_potential=64,
        renewal_turn=8,
        churn_risk=26,
        status=CustomerAccountStatus.ACTIVE,
    )
    state = make_state(
        product,
        partnerships=[dominant, tail],
        customer_accounts=[account],
        cash_on_hand=Decimal("7600.00"),
        current_turn=16,
        event_history=[
            EventHistoryEntry(
                event_id="partner_breakdown",
                category=EventCategory.MARKET_OPPORTUNITY,
                title="Partner Breakdown",
                triggered_turn=15,
                resolved_turn=15,
                selected_option_id="fund_recovery",
                selected_option_label="Recover",
                result_text="Integration lane remained fragile.",
            )
        ],
    )
    state.finance.board_pressure = 14
    definition = next(
        event_definition
        for event_definition in get_event_registry()
        if event_definition.event_id == "channel_concentration_crackdown"
    )

    assert definition.is_eligible(state) is True
    pending_event = definition.build_pending_event(state, FixedRandom(0), definition.cooldown_turns)
    state.pending_event = pending_event

    outcome = resolve_pending_event(state, "fund_firebreak")

    assert outcome.state.partnerships[0].risk < dominant.risk
    assert outcome.state.partnerships[0].status is PartnershipStatus.RECOVERY
    assert outcome.state.customer_accounts[0].onboarding_health > account.onboarding_health
    assert outcome.state.finance.board_pressure <= state.finance.board_pressure
    assert outcome.history_entry.event_id == "channel_concentration_crackdown"


def test_partnership_portfolio_summary_surfaces_status_mix() -> None:
    product = make_product("Partner Hub")
    accounts = [
        CustomerAccount(
            name="Direct Enterprise One",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("1600.00"),
            satisfaction=66,
            expansion_potential=60,
            renewal_turn=6,
            status=CustomerAccountStatus.ACTIVE,
        ),
        CustomerAccount(
            name="Direct Enterprise Two",
            product_id=product.id,
            segment=MarketSegment.ENTERPRISE,
            contract_value=Decimal("1450.00"),
            satisfaction=64,
            expansion_potential=58,
            renewal_turn=7,
            status=CustomerAccountStatus.ACTIVE,
        ),
    ]
    partnerships = [
        PartnershipDeal(
            name="Reseller",
            product_id=product.id,
            channel=PartnerChannel.RESELLER,
            status=PartnershipStatus.ACTIVE,
            sourced_revenue=Decimal("1200.00"),
            sourced_users=18,
            quality=70,
            risk=28,
            rev_share_rate=Decimal("0.1800"),
        ),
        PartnershipDeal(
            name="Marketplace",
            product_id=product.id,
            channel=PartnerChannel.MARKETPLACE,
            status=PartnershipStatus.RECOVERY,
            sourced_revenue=Decimal("820.00"),
            sourced_users=12,
            quality=62,
            risk=46,
            conflict_pressure=42,
            rev_share_rate=Decimal("0.2400"),
        ),
    ]
    state = make_state(product, partnerships=partnerships, customer_accounts=accounts)

    summary = calculate_partnership_portfolio(state)

    assert summary.total_count == 2
    assert summary.active_count == 1
    assert summary.recovery_count == 1
    assert summary.sourced_revenue == Decimal("2020.00")
    assert summary.average_fatigue >= 0
    assert summary.channel_conflict_index >= 0
    assert summary.direct_sales_conflict_accounts == 2
    assert summary.dominant_share_percent >= 50
    assert summary.dominant_channel in {"reseller", "marketplace"}
    assert summary.weighted_rev_share_percent >= 21
    assert summary.strained_revenue_share_percent >= 0
    assert summary.fatigued_revenue_share_percent >= 0
    assert summary.recovery_revenue_share_percent >= 0
    assert summary.volatile_revenue_share_percent >= 0
    assert summary.concentration_risk >= 0
    assert summary.renegotiation_pressure >= 0
    assert summary.rev_share_pressure >= 0
    assert summary.fatigue_hotspot_count >= 0
    assert summary.channel_volatility_index >= 0
    assert summary.commercial_dependency_score >= 0
    assert summary.hotspot_channel in {"reseller", "marketplace"}
    assert summary.channel_mix_note


def test_partnership_portfolio_summary_tracks_dependency_and_renegotiation_risk() -> None:
    product = make_product("Dependency Hub", market_fit=70, quality=72, bug_level=12)
    partnerships = [
        PartnershipDeal(
            name="Primary Reseller",
            product_id=product.id,
            channel=PartnerChannel.RESELLER,
            status=PartnershipStatus.STRAINED,
            sourced_revenue=Decimal("2200.00"),
            sourced_users=30,
            quality=68,
            risk=52,
            conflict_pressure=48,
            enablement_level=38,
        ),
        PartnershipDeal(
            name="Paused Marketplace",
            product_id=product.id,
            channel=PartnerChannel.MARKETPLACE,
            status=PartnershipStatus.PAUSED,
            sourced_revenue=Decimal("900.00"),
            sourced_users=12,
            quality=58,
            risk=60,
            conflict_pressure=54,
            enablement_level=30,
        ),
    ]
    state = make_state(product, partnerships=partnerships, current_turn=6)

    summary = calculate_partnership_portfolio(state)

    assert summary.channel_dependency_risk > 0
    assert summary.paused_revenue_share_percent > 0
    assert summary.renegotiation_ready_count >= 1
    assert summary.weighted_rev_share_percent > 0
    assert summary.rev_share_pressure > 0
    assert summary.strained_revenue_share_percent > 0
    assert summary.volatile_revenue_share_percent > 0
    assert summary.channel_volatility_index > 0
    assert summary.commercial_dependency_score > 0
    assert summary.recovery_drag_score > 0
    assert summary.paused_dependency_score > 0
    assert summary.hotspot_revenue_share_percent > 0
    assert summary.hotspot_channel in {"reseller", "marketplace"}


def test_finance_planner_surfaces_execution_drag_and_action_sequence() -> None:
    product = make_product("Planner Ops Core", user_count=140)
    state = make_state(product, cash_on_hand=Decimal("4200.00"))
    state.capital_plan = CapitalPlan(
        mode=CapitalPlanMode.EXPAND,
        source_preference=CapitalSourcePreference.DEBT,
        planning_horizon_turns=8,
        reserve_target=Decimal("5600.00"),
        product_investment_share=30,
        go_to_market_share=45,
        reserve_share=25,
    )
    state.finance.debt_principal = Decimal("3400.00")
    state.finance.covenant_risk = 22
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=Decimal("-780.00"),
        capital_plan=state.capital_plan,
        support_backlog=22,
        support_escalations=6,
        channel_conflict_index=34,
        channel_dependency_risk=62,
    )

    assert planner.liquidity_risk in {
        "reserve break is imminent",
        "liquidity is fragile",
        "liquidity needs active monitoring",
        "liquidity is controlled",
    }
    assert planner.execution_drag
    assert any("support" in step or "channel" in step for step in planner.action_sequence)


def test_long_run_standard_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int]:
        state = create_new_game(DEFAULT_COMPANY_NAME, DEFAULT_PRODUCT_NAME)
        rng = RandomSource(seed=seed)

        for _ in range(24):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.support_program.backlog_queue,
            len(state.turn_history),
        )

    assert run_once(91) == run_once(91)


def test_forty_turn_founder_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int, int]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="campaign_ladder_climb",
        )
        rng = RandomSource(seed=seed)

        for _ in range(40):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.support_program.backlog_queue,
            len(state.partnerships),
            len(state.turn_history),
        )

    assert run_once(143) == run_once(143)


def test_sixty_turn_late_game_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int, str | None]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="ipo_readiness_launchpad",
        )
        rng = RandomSource(seed=seed)

        for _ in range(60):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            len(state.partnerships),
            len(state.turn_history),
            state.exit_outcome.value if state.exit_outcome is not None else None,
        )

    assert run_once(211) == run_once(211)


def test_eighty_turn_channel_rebuild_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int, int]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="channel_rebuild_marathon",
        )
        rng = RandomSource(seed=seed)

        for _ in range(80):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.support_program.backlog_queue,
            len(state.partnerships),
            len(state.turn_history),
        )

    assert run_once(377) == run_once(377)


def test_ninety_turn_ipo_launchpad_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int, str | None]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="ipo_readiness_launchpad",
        )
        rng = RandomSource(seed=seed)

        for _ in range(90):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.finance.board_pressure,
            len(state.turn_history),
            state.exit_outcome.value if state.exit_outcome is not None else None,
        )

    assert run_once(503) == run_once(503)


def test_hundred_turn_acquisition_diligence_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int, str | None]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="acquisition_diligence_sprint",
        )
        rng = RandomSource(seed=seed)

        for _ in range(100):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.finance.board_pressure,
            len(state.turn_history),
            state.exit_outcome.value if state.exit_outcome is not None else None,
        )

    assert run_once(601) == run_once(601)


def test_hundred_turn_independence_compounder_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int, str | None]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="independence_compounder",
        )
        rng = RandomSource(seed=seed)

        for _ in range(100):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.finance.covenant_risk,
            len(state.turn_history),
            state.exit_outcome.value if state.exit_outcome is not None else None,
        )

    assert run_once(733) == run_once(733)


def test_hundred_turn_board_recovery_crucible_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int, str | None]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="board_recovery_crucible",
        )
        rng = RandomSource(seed=seed)

        for _ in range(100):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.finance.board_pressure,
            state.finance.governance_risk,
            state.exit_outcome.value if state.exit_outcome is not None else None,
        )

    assert run_once(809) == run_once(809)


def test_hundred_ten_turn_channel_rebuild_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int, str | None]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="channel_rebuild_marathon",
        )
        rng = RandomSource(seed=seed)

        for _ in range(110):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.support_program.backlog_queue,
            len(state.partnerships),
            state.exit_outcome.value if state.exit_outcome is not None else None,
        )

    assert run_once(911) == run_once(911)


def test_hundred_twenty_turn_ipo_launchpad_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int, str | None]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="ipo_readiness_launchpad",
        )
        rng = RandomSource(seed=seed)

        for _ in range(120):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.support_program.backlog_queue,
            state.finance.board_pressure,
            state.exit_outcome.value if state.exit_outcome is not None else None,
        )

    assert run_once(1007) == run_once(1007)


def test_hundred_thirty_turn_independence_compounder_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, Decimal, str | None]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="independence_compounder",
        )
        rng = RandomSource(seed=seed)

        for _ in range(130):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.capital_plan.reserve_share,
            state.finance.debt_principal,
            state.exit_outcome.value if state.exit_outcome is not None else None,
        )

    assert run_once(1109) == run_once(1109)


def test_hundred_forty_turn_board_recovery_crucible_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int, str | None]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="board_recovery_crucible",
        )
        rng = RandomSource(seed=seed)

        for _ in range(140):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.finance.board_pressure,
            state.finance.governance_risk,
            state.exit_outcome.value if state.exit_outcome is not None else None,
        )

    assert run_once(1201) == run_once(1201)


def test_hundred_fifty_turn_ipo_launchpad_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int, str | None]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="ipo_readiness_launchpad",
        )
        rng = RandomSource(seed=seed)

        for _ in range(150):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.support_program.backlog_queue,
            state.finance.board_pressure,
            state.exit_outcome.value if state.exit_outcome is not None else None,
        )

    assert run_once(1307) == run_once(1307)


def test_hundred_eighty_turn_ipo_launchpad_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int, str | None]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="ipo_readiness_launchpad",
        )
        rng = RandomSource(seed=seed)

        for _ in range(180):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.support_program.backlog_queue,
            state.finance.board_pressure,
            state.exit_outcome.value if state.exit_outcome is not None else None,
        )

    assert run_once(1501) == run_once(1501)


def test_hundred_seventy_turn_board_recovery_crucible_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int, str | None]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="board_recovery_crucible",
        )
        rng = RandomSource(seed=seed)

        for _ in range(170):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.finance.board_pressure,
            state.finance.board_warning_level,
            state.exit_outcome.value if state.exit_outcome is not None else None,
        )

    assert run_once(1703) == run_once(1703)


def test_hundred_sixty_turn_acquisition_diligence_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int, str | None]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="acquisition_diligence_sprint",
        )
        rng = RandomSource(seed=seed)

        for _ in range(160):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.finance.board_pressure,
            len(state.turn_history),
            state.exit_outcome.value if state.exit_outcome is not None else None,
        )

    assert run_once(1409) == run_once(1409)


def test_hundred_ninety_turn_channel_rebuild_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int, str | None]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="channel_rebuild_marathon",
        )
        rng = RandomSource(seed=seed)

        for _ in range(190):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.finance.board_pressure,
            len(state.partnerships),
            state.exit_outcome.value if state.exit_outcome is not None else None,
        )

    assert run_once(1901) == run_once(1901)


def test_two_hundred_turn_board_recovery_crucible_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int, str | None]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="board_recovery_crucible",
        )
        rng = RandomSource(seed=seed)

        for _ in range(200):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.finance.board_pressure,
            state.finance.governance_risk,
            state.exit_outcome.value if state.exit_outcome is not None else None,
        )

    assert run_once(2003) == run_once(2003)


def test_two_hundred_twenty_turn_board_recovery_crucible_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int, str | None]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="board_recovery_crucible",
        )
        rng = RandomSource(seed=seed)

        for _ in range(220):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.finance.board_pressure,
            state.finance.governance_risk,
            state.exit_outcome.value if state.exit_outcome is not None else None,
        )

    assert run_once(2201) == run_once(2201)


def test_two_hundred_forty_turn_board_recovery_crucible_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int, str | None]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="board_recovery_crucible",
        )
        rng = RandomSource(seed=seed)

        for _ in range(240):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.finance.board_pressure,
            state.finance.governance_risk,
            state.exit_outcome.value if state.exit_outcome is not None else None,
        )

    assert run_once(2401) == run_once(2401)


def test_two_hundred_sixty_turn_board_recovery_crucible_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int, str | None]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="board_recovery_crucible",
        )
        rng = RandomSource(seed=seed)

        for _ in range(260):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.finance.board_pressure,
            state.finance.governance_risk,
            state.exit_outcome.value if state.exit_outcome is not None else None,
        )

    assert run_once(2601) == run_once(2601)


def test_two_hundred_eighty_turn_board_recovery_crucible_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int, str | None]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="board_recovery_crucible",
        )
        rng = RandomSource(seed=seed)

        for _ in range(280):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.finance.board_pressure,
            state.finance.governance_risk,
            state.exit_outcome.value if state.exit_outcome is not None else None,
        )

    assert run_once(2801) == run_once(2801)


def test_three_hundred_turn_board_recovery_crucible_progression_is_seed_stable() -> None:
    def run_once(seed: int) -> tuple[Decimal, int, int, bool, bool, int, int, str | None]:
        state = create_new_game(
            DEFAULT_COMPANY_NAME,
            DEFAULT_PRODUCT_NAME,
            campaign_start_id="board_recovery_crucible",
        )
        rng = RandomSource(seed=seed)

        for _ in range(300):
            resolution = resolve_turn(state, rng)
            state = resolution.state
            if state.pending_event is not None:
                state = resolve_pending_event(state, state.pending_event.options[0].id).state
            if state.company.game_over or state.victory_achieved:
                break

        return (
            state.company.cash_on_hand,
            state.company.reputation,
            state.company.current_turn,
            state.victory_achieved,
            state.company.game_over,
            state.finance.board_pressure,
            state.finance.governance_risk,
            state.exit_outcome.value if state.exit_outcome is not None else None,
        )

    assert run_once(3001) == run_once(3001)


def test_reactivate_partnership_action_recovers_paused_channel() -> None:
    product = make_product("Paused Lane", market_fit=68, quality=72, bug_level=12)
    partnership = PartnershipDeal(
        name="Paused Lane Marketplace",
        product_id=product.id,
        channel=PartnerChannel.MARKETPLACE,
        status=PartnershipStatus.PAUSED,
        quality=60,
        risk=58,
        conflict_pressure=54,
        enablement_level=30,
        last_review_turn=1,
        started_turn=1,
    )
    state = make_state(
        product,
        partnerships=[partnership],
        cash_on_hand=Decimal("7600.00"),
        current_turn=6,
    )

    outcome = apply_action(
        state,
        TurnAction.REACTIVATE_PARTNERSHIP,
        context=ActionContext(partnership_id=partnership.id),
    )

    updated = outcome.state.partnerships[0]
    assert updated.status in {PartnershipStatus.RECOVERY, PartnershipStatus.ACTIVE}
    assert updated.risk < partnership.risk
    assert updated.conflict_pressure < partnership.conflict_pressure
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_pause_partnership_action_reduces_conflict_and_dependency_pressure() -> None:
    product = make_product("Channel Pause Core", user_count=140)
    partnership = PartnershipDeal(
        name="Noisy Integration",
        product_id=product.id,
        channel=PartnerChannel.INTEGRATION,
        status=PartnershipStatus.STRAINED,
        quality=62,
        risk=54,
        conflict_pressure=52,
        enablement_level=30,
        sourced_revenue=Decimal("2600.00"),
        sourced_users=42,
        rev_share_rate=Decimal("0.2200"),
    )
    state = make_state(
        product,
        partnerships=[partnership],
        cash_on_hand=Decimal("7400.00"),
        current_turn=8,
    )
    state.finance.board_pressure = 22
    state.finance.investor_pressure = 18
    state.company.reputation = 68

    outcome = apply_action(
        state,
        TurnAction.PAUSE_PARTNERSHIP,
        context=ActionContext(partnership_id=partnership.id),
    )

    updated = outcome.state.partnerships[0]
    assert updated.status is PartnershipStatus.PAUSED
    assert updated.risk < partnership.risk
    assert updated.conflict_pressure < partnership.conflict_pressure
    assert updated.sourced_revenue < partnership.sourced_revenue
    assert updated.sourced_users < partnership.sourced_users
    assert outcome.state.products[0].user_count < product.user_count
    assert outcome.state.finance.board_pressure < 22
    assert outcome.state.finance.investor_pressure < 18
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_channel_qbr_reduces_hotspot_partner_drag() -> None:
    product = make_product("Channel QBR Core")
    account = CustomerAccount(
        name="Integration Rollout",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("1800.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=60,
        onboarding_health=48,
        support_load=26,
        open_tickets=3,
        expansion_potential=54,
        renewal_health=58,
        renewal_turn=6,
        churn_risk=22,
        status=CustomerAccountStatus.ACTIVE,
    )
    partnership = PartnershipDeal(
        name="Hotspot Integration",
        product_id=product.id,
        channel=PartnerChannel.INTEGRATION,
        status=PartnershipStatus.RECOVERY,
        quality=60,
        risk=52,
        conflict_pressure=49,
        enablement_level=28,
        sourced_revenue=Decimal("2400.00"),
        rev_share_rate=Decimal("0.2000"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        cash_on_hand=Decimal("8200.00"),
        current_turn=8,
    )

    outcome = apply_action(
        state,
        TurnAction.RUN_CHANNEL_QBR,
        context=ActionContext(partnership_id=partnership.id),
    )

    updated_partnership = outcome.state.partnerships[0]
    updated_account = outcome.state.customer_accounts[0]
    assert updated_partnership.enablement_level > partnership.enablement_level
    assert updated_partnership.risk < partnership.risk
    assert updated_partnership.conflict_pressure < partnership.conflict_pressure
    assert updated_partnership.rev_share_rate < partnership.rev_share_rate
    assert updated_account.onboarding_health > account.onboarding_health
    assert updated_account.support_load < account.support_load
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_rebalance_channel_mix_reduces_hotspot_dependency() -> None:
    product = make_product("Channel Mix Core", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Channel Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2200.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=60,
        onboarding_health=54,
        support_load=24,
        open_tickets=3,
        expansion_potential=52,
        renewal_health=56,
        renewal_turn=5,
        churn_risk=20,
        status=CustomerAccountStatus.ACTIVE,
    )
    hotspot = PartnershipDeal(
        name="Hotspot Reseller",
        product_id=product.id,
        channel=PartnerChannel.RESELLER,
        status=PartnershipStatus.ACTIVE,
        quality=64,
        risk=46,
        conflict_pressure=42,
        enablement_level=36,
        sourced_revenue=Decimal("2600.00"),
        sourced_users=28,
        rev_share_rate=Decimal("0.1600"),
    )
    supporting = PartnershipDeal(
        name="Supporting Marketplace",
        product_id=product.id,
        channel=PartnerChannel.MARKETPLACE,
        status=PartnershipStatus.ACTIVE,
        quality=58,
        risk=18,
        conflict_pressure=16,
        enablement_level=24,
        sourced_revenue=Decimal("900.00"),
        sourced_users=12,
        rev_share_rate=Decimal("0.1400"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[hotspot, supporting],
        cash_on_hand=Decimal("7600.00"),
        current_turn=9,
    )
    starting_portfolio = calculate_partnership_portfolio(state)

    outcome = apply_action(
        state,
        TurnAction.REBALANCE_CHANNEL_MIX,
        context=ActionContext(),
    )

    updated_portfolio = calculate_partnership_portfolio(outcome.state)
    assert (
        updated_portfolio.hotspot_revenue_share_percent
        < starting_portfolio.hotspot_revenue_share_percent
    )
    assert outcome.state.partnerships[0].risk < hotspot.risk
    assert outcome.state.partnerships[1].enablement_level > supporting.enablement_level
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_partner_recovery_sprint_restores_strained_channel() -> None:
    product = make_product("Recovery Sprint Core", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Recovery Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2100.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=58,
        onboarding_health=46,
        support_load=22,
        open_tickets=4,
        renewal_health=52,
        expansion_potential=58,
        renewal_turn=5,
        churn_risk=24,
        status=CustomerAccountStatus.ACTIVE,
    )
    partnership = PartnershipDeal(
        name="Recovery Integration",
        product_id=product.id,
        channel=PartnerChannel.INTEGRATION,
        status=PartnershipStatus.RECOVERY,
        quality=58,
        risk=48,
        conflict_pressure=44,
        enablement_level=26,
        sourced_revenue=Decimal("1600.00"),
        rev_share_rate=Decimal("0.1800"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        cash_on_hand=Decimal("7400.00"),
        current_turn=10,
    )

    outcome = apply_action(
        state,
        TurnAction.RUN_PARTNER_RECOVERY_SPRINT,
        context=ActionContext(partnership_id=partnership.id),
    )

    updated_partnership = outcome.state.partnerships[0]
    updated_account = outcome.state.customer_accounts[0]
    assert updated_partnership.enablement_level > partnership.enablement_level
    assert updated_partnership.risk < partnership.risk
    assert updated_partnership.conflict_pressure < partnership.conflict_pressure
    assert updated_account.onboarding_health > account.onboarding_health
    assert updated_account.support_load < account.support_load
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_channel_firebreak_reduces_hotspot_dependency() -> None:
    product = make_product("Channel Firebreak Core", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Firebreak Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2600.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=60,
        onboarding_health=42,
        support_load=24,
        open_tickets=4,
        renewal_health=50,
        expansion_potential=58,
        renewal_turn=6,
        churn_risk=22,
        status=CustomerAccountStatus.ACTIVE,
    )
    partnership = PartnershipDeal(
        name="Firebreak Integration",
        product_id=product.id,
        channel=PartnerChannel.INTEGRATION,
        status=PartnershipStatus.ACTIVE,
        quality=62,
        risk=48,
        conflict_pressure=40,
        enablement_level=30,
        sourced_revenue=Decimal("2200.00"),
        sourced_users=30,
        rev_share_rate=Decimal("0.1800"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        cash_on_hand=Decimal("7800.00"),
        current_turn=12,
    )

    outcome = apply_action(
        state,
        TurnAction.RUN_CHANNEL_FIREBREAK,
        context=ActionContext(partnership_id=partnership.id),
    )

    updated_partnership = outcome.state.partnerships[0]
    updated_account = outcome.state.customer_accounts[0]
    assert updated_partnership.sourced_revenue < partnership.sourced_revenue
    assert updated_partnership.sourced_users < partnership.sourced_users
    assert updated_partnership.risk < partnership.risk
    assert updated_partnership.conflict_pressure < partnership.conflict_pressure
    assert updated_account.onboarding_health > account.onboarding_health
    assert updated_account.support_load < account.support_load
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_channel_conflict_reset_cools_partner_and_account_conflict() -> None:
    product = make_product("Conflict Reset Core", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Conflict Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2400.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=58,
        onboarding_health=44,
        support_load=26,
        open_tickets=4,
        renewal_health=50,
        expansion_potential=60,
        renewal_turn=6,
        churn_risk=24,
        status=CustomerAccountStatus.ACTIVE,
    )
    partnership = PartnershipDeal(
        name="Conflict Integration",
        product_id=product.id,
        channel=PartnerChannel.INTEGRATION,
        status=PartnershipStatus.STRAINED,
        quality=60,
        risk=54,
        conflict_pressure=58,
        enablement_level=28,
        sourced_revenue=Decimal("2600.00"),
        sourced_users=32,
        rev_share_rate=Decimal("0.1900"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        cash_on_hand=Decimal("7600.00"),
        current_turn=11,
    )
    state.finance.board_pressure = 18
    state.finance.investor_pressure = 14

    outcome = apply_action(
        state,
        TurnAction.RUN_CHANNEL_CONFLICT_RESET,
        context=ActionContext(partnership_id=partnership.id),
    )

    updated_partnership = outcome.state.partnerships[0]
    updated_account = outcome.state.customer_accounts[0]
    assert updated_partnership.conflict_pressure < partnership.conflict_pressure
    assert updated_partnership.risk < partnership.risk
    assert updated_partnership.rev_share_rate > partnership.rev_share_rate
    assert updated_account.onboarding_health > account.onboarding_health
    assert updated_account.support_load < account.support_load
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_channel_realignment_cools_hotspot_partner_pressure() -> None:
    product = make_product("Channel Realignment Core", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Realignment Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2500.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=56,
        onboarding_health=40,
        support_load=28,
        open_tickets=4,
        renewal_health=48,
        expansion_potential=58,
        renewal_turn=6,
        churn_risk=26,
        status=CustomerAccountStatus.ACTIVE,
    )
    partnership = PartnershipDeal(
        name="Hotspot Integration",
        product_id=product.id,
        channel=PartnerChannel.INTEGRATION,
        status=PartnershipStatus.STRAINED,
        quality=60,
        risk=54,
        conflict_pressure=56,
        enablement_level=28,
        sourced_revenue=Decimal("2800.00"),
        sourced_users=36,
        rev_share_rate=Decimal("0.2100"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        cash_on_hand=Decimal("7800.00"),
        current_turn=12,
    )
    state.finance.board_pressure = 18
    state.finance.investor_pressure = 16

    outcome = apply_action(
        state,
        TurnAction.RUN_CHANNEL_REALIGNMENT,
        context=ActionContext(partnership_id=partnership.id),
    )

    updated_partnership = outcome.state.partnerships[0]
    updated_account = outcome.state.customer_accounts[0]
    assert updated_partnership.sourced_revenue < partnership.sourced_revenue
    assert updated_partnership.sourced_users < partnership.sourced_users
    assert updated_partnership.risk < partnership.risk
    assert updated_partnership.conflict_pressure < partnership.conflict_pressure
    assert updated_partnership.rev_share_rate > partnership.rev_share_rate
    assert updated_account.onboarding_health > account.onboarding_health
    assert updated_account.support_load < account.support_load
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_channel_synergy_reset_cleans_hotspot_partner_economics() -> None:
    product = make_product("Synergy Reset Core", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Synergy Integration Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2600.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=58,
        onboarding_health=44,
        support_load=32,
        open_tickets=5,
        renewal_health=50,
        expansion_potential=60,
        renewal_turn=7,
        churn_risk=22,
        status=CustomerAccountStatus.ACTIVE,
    )
    partnership = PartnershipDeal(
        name="Synergy Integration",
        product_id=product.id,
        channel=PartnerChannel.INTEGRATION,
        status=PartnershipStatus.STRAINED,
        quality=60,
        risk=54,
        conflict_pressure=58,
        enablement_level=26,
        sourced_revenue=Decimal("3200.00"),
        sourced_users=42,
        rev_share_rate=Decimal("0.2200"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        cash_on_hand=Decimal("7600.00"),
        current_turn=12,
    )
    state.finance.board_pressure = 18
    state.finance.investor_pressure = 15
    state.finance.board_confidence = 42

    outcome = apply_action(
        state,
        TurnAction.RUN_CHANNEL_SYNERGY_RESET,
        context=ActionContext(partnership_id=partnership.id),
    )

    updated_partnership = outcome.state.partnerships[0]
    updated_account = outcome.state.customer_accounts[0]
    assert updated_partnership.sourced_revenue < partnership.sourced_revenue
    assert updated_partnership.sourced_users < partnership.sourced_users
    assert updated_partnership.risk < partnership.risk
    assert updated_partnership.conflict_pressure < partnership.conflict_pressure
    assert updated_partnership.enablement_level > partnership.enablement_level
    assert updated_partnership.quality > partnership.quality
    assert updated_partnership.rev_share_rate < partnership.rev_share_rate
    assert updated_account.onboarding_health > account.onboarding_health
    assert updated_account.support_load < account.support_load
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_integration_cutover_reset_rebuilds_hotspot_lane() -> None:
    product = make_product("Integration Reset Core", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Integration Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2700.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=58,
        onboarding_health=40,
        support_load=30,
        open_tickets=5,
        renewal_health=48,
        expansion_potential=60,
        renewal_turn=7,
        churn_risk=22,
        status=CustomerAccountStatus.ACTIVE,
    )
    partnership = PartnershipDeal(
        name="Cutover Integration",
        product_id=product.id,
        channel=PartnerChannel.INTEGRATION,
        status=PartnershipStatus.STRAINED,
        quality=60,
        risk=56,
        conflict_pressure=58,
        enablement_level=24,
        sourced_revenue=Decimal("3200.00"),
        sourced_users=40,
        rev_share_rate=Decimal("0.2200"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        cash_on_hand=Decimal("7800.00"),
        current_turn=12,
    )
    state.finance.board_pressure = 18
    state.finance.investor_pressure = 15
    state.finance.board_confidence = 42

    outcome = apply_action(
        state,
        TurnAction.RUN_INTEGRATION_CUTOVER_RESET,
        context=ActionContext(partnership_id=partnership.id),
    )

    updated_partnership = outcome.state.partnerships[0]
    updated_account = outcome.state.customer_accounts[0]
    assert updated_partnership.sourced_revenue < partnership.sourced_revenue
    assert updated_partnership.sourced_users < partnership.sourced_users
    assert updated_partnership.risk < partnership.risk
    assert updated_partnership.conflict_pressure < partnership.conflict_pressure
    assert updated_partnership.enablement_level > partnership.enablement_level
    assert updated_partnership.quality > partnership.quality
    assert updated_partnership.rev_share_rate < partnership.rev_share_rate
    assert updated_account.onboarding_health > account.onboarding_health
    assert updated_account.support_load < account.support_load
    assert updated_account.renewal_health > account.renewal_health
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_partner_margin_reset_cleans_hotspot_partner_terms() -> None:
    product = make_product("Margin Reset Core", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Marketplace Margin Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2800.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=56,
        onboarding_health=48,
        support_load=28,
        open_tickets=4,
        renewal_health=46,
        expansion_potential=62,
        renewal_turn=7,
        churn_risk=24,
        invoice_risk=24,
        failed_payment_risk=20,
        status=CustomerAccountStatus.AT_RISK,
    )
    partnership = PartnershipDeal(
        name="Margin Marketplace",
        product_id=product.id,
        channel=PartnerChannel.MARKETPLACE,
        status=PartnershipStatus.STRAINED,
        quality=60,
        risk=54,
        conflict_pressure=56,
        enablement_level=28,
        sourced_revenue=Decimal("3400.00"),
        sourced_users=44,
        rev_share_rate=Decimal("0.2200"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        cash_on_hand=Decimal("7600.00"),
        current_turn=12,
    )
    state.finance.board_pressure = 19
    state.finance.investor_pressure = 16
    state.finance.board_confidence = 40

    outcome = apply_action(
        state,
        TurnAction.RUN_PARTNER_MARGIN_RESET,
        context=ActionContext(partnership_id=partnership.id),
    )

    updated_partnership = outcome.state.partnerships[0]
    updated_account = outcome.state.customer_accounts[0]
    assert updated_partnership.sourced_revenue < partnership.sourced_revenue
    assert updated_partnership.sourced_users < partnership.sourced_users
    assert updated_partnership.risk < partnership.risk
    assert updated_partnership.conflict_pressure < partnership.conflict_pressure
    assert updated_partnership.enablement_level > partnership.enablement_level
    assert updated_partnership.quality > partnership.quality
    assert updated_partnership.rev_share_rate < partnership.rev_share_rate
    assert updated_account.invoice_risk < account.invoice_risk
    assert updated_account.failed_payment_risk < account.failed_payment_risk
    assert updated_account.renewal_health > account.renewal_health
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_channel_stability_reset_cools_hotspot_lane() -> None:
    product = make_product("Channel Stability Core", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Reseller Renewal Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2600.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=54,
        onboarding_health=52,
        support_load=22,
        open_tickets=3,
        renewal_health=44,
        expansion_potential=58,
        renewal_turn=7,
        churn_risk=26,
        status=CustomerAccountStatus.AT_RISK,
    )
    partnership = PartnershipDeal(
        name="Reseller Hotspot",
        product_id=product.id,
        channel=PartnerChannel.RESELLER,
        status=PartnershipStatus.STRAINED,
        quality=60,
        risk=56,
        conflict_pressure=54,
        enablement_level=24,
        sourced_revenue=Decimal("3200.00"),
        sourced_users=40,
        rev_share_rate=Decimal("0.2100"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        cash_on_hand=Decimal("7600.00"),
        current_turn=12,
    )
    state.finance.board_pressure = 20
    state.finance.investor_pressure = 16
    state.finance.board_confidence = 42

    outcome = apply_action(
        state,
        TurnAction.RUN_CHANNEL_STABILITY_RESET,
        context=ActionContext(partnership_id=partnership.id),
    )

    updated_partnership = outcome.state.partnerships[0]
    updated_account = outcome.state.customer_accounts[0]
    assert updated_partnership.sourced_revenue < partnership.sourced_revenue
    assert updated_partnership.sourced_users < partnership.sourced_users
    assert updated_partnership.risk < partnership.risk
    assert updated_partnership.conflict_pressure < partnership.conflict_pressure
    assert updated_partnership.enablement_level > partnership.enablement_level
    assert updated_partnership.quality > partnership.quality
    assert updated_partnership.rev_share_rate < partnership.rev_share_rate
    assert updated_account.satisfaction > account.satisfaction
    assert updated_account.renewal_health > account.renewal_health
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_reseller_enablement_reset_recovers_hotspot_reseller_lane() -> None:
    product = make_product("Reseller Enablement Core", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Reseller Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2200.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=58,
        onboarding_health=50,
        support_load=22,
        open_tickets=3,
        renewal_health=48,
        expansion_potential=56,
        renewal_turn=6,
        churn_risk=24,
        status=CustomerAccountStatus.AT_RISK,
    )
    partnership = PartnershipDeal(
        name="Hotspot Reseller",
        product_id=product.id,
        channel=PartnerChannel.RESELLER,
        status=PartnershipStatus.STRAINED,
        quality=60,
        risk=50,
        conflict_pressure=48,
        enablement_level=24,
        sourced_revenue=Decimal("2600.00"),
        sourced_users=34,
        rev_share_rate=Decimal("0.1800"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        cash_on_hand=Decimal("7600.00"),
        current_turn=12,
    )
    state.finance.board_pressure = 18
    state.finance.investor_pressure = 16
    state.finance.board_confidence = 40

    outcome = apply_action(
        state,
        TurnAction.RUN_RESELLER_ENABLEMENT_RESET,
        context=ActionContext(partnership_id=partnership.id),
    )

    updated_partnership = outcome.state.partnerships[0]
    updated_account = outcome.state.customer_accounts[0]
    assert updated_partnership.sourced_revenue < partnership.sourced_revenue
    assert updated_partnership.sourced_users < partnership.sourced_users
    assert updated_partnership.risk < partnership.risk
    assert updated_partnership.conflict_pressure < partnership.conflict_pressure
    assert updated_partnership.enablement_level > partnership.enablement_level
    assert updated_partnership.quality > partnership.quality
    assert updated_partnership.rev_share_rate < partnership.rev_share_rate
    assert updated_account.satisfaction > account.satisfaction
    assert updated_account.renewal_health > account.renewal_health
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_run_marketplace_chargeback_reset_cools_billing_drift() -> None:
    product = make_product("Chargeback Reset Core", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Marketplace Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2400.00"),
        support_tier=SupportTier.PRIORITY,
        satisfaction=56,
        onboarding_health=48,
        support_load=24,
        open_tickets=4,
        renewal_health=44,
        expansion_potential=58,
        renewal_turn=7,
        churn_risk=24,
        invoice_risk=26,
        failed_payment_risk=20,
        dunning_steps=2,
        status=CustomerAccountStatus.AT_RISK,
    )
    partnership = PartnershipDeal(
        name="Chargeback Marketplace",
        product_id=product.id,
        channel=PartnerChannel.MARKETPLACE,
        status=PartnershipStatus.STRAINED,
        quality=58,
        risk=54,
        conflict_pressure=50,
        enablement_level=24,
        sourced_revenue=Decimal("3000.00"),
        sourced_users=40,
        rev_share_rate=Decimal("0.2200"),
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        cash_on_hand=Decimal("7600.00"),
        current_turn=12,
    )
    state.finance.board_pressure = 18
    state.finance.investor_pressure = 16
    state.finance.board_confidence = 40

    outcome = apply_action(
        state,
        TurnAction.RUN_MARKETPLACE_CHARGEBACK_RESET,
        context=ActionContext(partnership_id=partnership.id),
    )

    updated_partnership = outcome.state.partnerships[0]
    updated_account = outcome.state.customer_accounts[0]
    assert updated_partnership.sourced_revenue < partnership.sourced_revenue
    assert updated_partnership.sourced_users < partnership.sourced_users
    assert updated_partnership.risk < partnership.risk
    assert updated_partnership.conflict_pressure < partnership.conflict_pressure
    assert updated_partnership.enablement_level > partnership.enablement_level
    assert updated_partnership.quality > partnership.quality
    assert updated_partnership.rev_share_rate < partnership.rev_share_rate
    assert updated_account.invoice_risk < account.invoice_risk
    assert updated_account.failed_payment_risk < account.failed_payment_risk
    assert updated_account.dunning_steps < account.dunning_steps
    assert updated_account.renewal_health > account.renewal_health
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand


def test_partnership_neglect_and_channel_crowding_raise_conflict_pressure() -> None:
    product = make_product(
        "Channel Crowd",
        market_fit=70,
        quality=72,
        bug_level=10,
        user_count=80,
    )
    partnerships = [
        PartnershipDeal(
            name="Crowd Reseller",
            product_id=product.id,
            channel=PartnerChannel.RESELLER,
            status=PartnershipStatus.ACTIVE,
            quality=66,
            risk=20,
            enablement_level=42,
            conflict_pressure=18,
            started_turn=1,
            last_review_turn=1,
        ),
        PartnershipDeal(
            name="Crowd Marketplace",
            product_id=product.id,
            channel=PartnerChannel.MARKETPLACE,
            status=PartnershipStatus.ACTIVE,
            quality=62,
            risk=18,
            enablement_level=40,
            conflict_pressure=16,
            started_turn=1,
            last_review_turn=1,
        ),
    ]
    state = make_state(
        product,
        partnerships=partnerships,
        current_turn=5,
        capital_plan=CapitalPlan(
            mode=CapitalPlanMode.EXPAND,
            source_preference=CapitalSourcePreference.VENTURE,
        ),
    )

    apply_end_of_turn_partnerships(state)

    assert state.partnerships[0].conflict_pressure > 18
    assert state.partnerships[1].risk > 18
    assert calculate_partnership_fatigue(state, state.partnerships[0]) > 0


def test_renegotiate_partnership_action_trades_margin_for_stability() -> None:
    product = make_product("Lane Terms", market_fit=67, quality=70, bug_level=12)
    partnership = PartnershipDeal(
        name="Lane Terms Reseller",
        product_id=product.id,
        channel=PartnerChannel.RESELLER,
        status=PartnershipStatus.STRAINED,
        quality=63,
        risk=46,
        conflict_pressure=43,
        enablement_level=36,
        rev_share_rate=Decimal("0.1400"),
    )
    state = make_state(product, partnerships=[partnership], cash_on_hand=Decimal("7200.00"))

    outcome = apply_action(
        state,
        TurnAction.RENEGOTIATE_PARTNERSHIP,
        context=ActionContext(partnership_id=partnership.id),
    )

    assert outcome.state.partnerships[0].rev_share_rate > Decimal("0.1400")
    assert outcome.state.partnerships[0].conflict_pressure < 43
    assert outcome.state.company.cash_on_hand < Decimal("7200.00")


def test_set_capital_plan_action_updates_state() -> None:
    product = make_product("Capital Core")
    state = make_state(product)

    outcome = apply_action(
        state,
        TurnAction.SET_CAPITAL_PLAN,
        context=ActionContext(
            capital_plan_mode=CapitalPlanMode.EXPAND,
            capital_source_preference=CapitalSourcePreference.VENTURE,
        ),
    )

    assert outcome.state.capital_plan.mode is CapitalPlanMode.EXPAND
    assert outcome.state.capital_plan.source_preference is CapitalSourcePreference.VENTURE
    assert outcome.state.capital_plan.reserve_target == Decimal("1800.00")


def test_set_capital_plan_action_accepts_custom_allocations() -> None:
    product = make_product("Capital Tuning Core")
    state = make_state(product)

    outcome = apply_action(
        state,
        TurnAction.SET_CAPITAL_PLAN,
        context=ActionContext(
            capital_plan_mode=CapitalPlanMode.BALANCED,
            capital_source_preference=CapitalSourcePreference.ANGEL,
            capital_plan_horizon_turns=9,
            capital_plan_reserve_target=Decimal("4200.00"),
            capital_plan_product_share=42,
            capital_plan_go_to_market_share=28,
            capital_plan_reserve_share=30,
        ),
    )

    assert outcome.state.capital_plan.mode is CapitalPlanMode.BALANCED
    assert outcome.state.capital_plan.source_preference is CapitalSourcePreference.ANGEL
    assert outcome.state.capital_plan.planning_horizon_turns == 9
    assert outcome.state.capital_plan.reserve_target == Decimal("4200.00")
    assert outcome.state.capital_plan.product_investment_share == 42
    assert outcome.state.capital_plan.go_to_market_share == 28
    assert outcome.state.capital_plan.reserve_share == 30
    assert "Allocation P 42% / GTM 28% / Reserve 30%" in outcome.message


def test_rebalance_capital_action_shifts_allocation_toward_resilience() -> None:
    product = make_product("Capital Rebalance Core", target_segment=MarketSegment.ENTERPRISE)
    account = CustomerAccount(
        name="Hotspot Enterprise",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("2400.00"),
        support_tier=SupportTier.WHITE_GLOVE,
        satisfaction=48,
        open_tickets=7,
        sla_breach_risk=22,
        ticket_queue_age=4,
        expansion_potential=55,
        renewal_health=40,
        renewal_turn=5,
        churn_risk=46,
        status=CustomerAccountStatus.AT_RISK,
    )
    partnership = PartnershipDeal(
        name="Concentrated Integration",
        product_id=product.id,
        channel=PartnerChannel.INTEGRATION,
        status=PartnershipStatus.RECOVERY,
        quality=60,
        risk=52,
        conflict_pressure=44,
        enablement_level=32,
        sourced_revenue=Decimal("2400.00"),
        rev_share_rate=Decimal("0.2200"),
    )
    capital_plan = CapitalPlan(
        mode=CapitalPlanMode.EXPAND,
        source_preference=CapitalSourcePreference.DEBT,
        planning_horizon_turns=7,
        reserve_target=Decimal("4200.00"),
        product_investment_share=30,
        go_to_market_share=45,
        reserve_share=25,
    )
    state = make_state(
        product,
        customer_accounts=[account],
        partnerships=[partnership],
        capital_plan=capital_plan,
        cash_on_hand=Decimal("2600.00"),
    )
    state.finance.covenant_risk = 22
    state.finance.board_pressure = 28
    state.finance.active_board_ask = BoardAsk.RELIABILITY

    outcome = apply_action(state, TurnAction.REBALANCE_CAPITAL, context=ActionContext())

    updated_plan = outcome.state.capital_plan
    assert updated_plan.mode is CapitalPlanMode.CONSERVE
    assert updated_plan.reserve_target > capital_plan.reserve_target
    assert updated_plan.product_investment_share >= capital_plan.product_investment_share
    assert updated_plan.go_to_market_share < capital_plan.go_to_market_share
    assert updated_plan.reserve_share > capital_plan.reserve_share
    assert (
        updated_plan.product_investment_share
        + updated_plan.go_to_market_share
        + updated_plan.reserve_share
        == 100
    )
    assert "Capital was rebalanced" in outcome.message


def test_raise_reserve_target_action_increases_target_and_reserve_share() -> None:
    product = make_product("Reserve Raise Core")
    capital_plan = CapitalPlan(
        mode=CapitalPlanMode.EXPAND,
        source_preference=CapitalSourcePreference.VENTURE,
        planning_horizon_turns=4,
        reserve_target=Decimal("1800.00"),
        product_investment_share=45,
        go_to_market_share=40,
        reserve_share=15,
    )
    state = make_state(product, capital_plan=capital_plan)

    outcome = apply_action(state, TurnAction.RAISE_RESERVE_TARGET, context=ActionContext())

    updated_plan = outcome.state.capital_plan
    assert updated_plan.mode is CapitalPlanMode.BALANCED
    assert updated_plan.reserve_target > capital_plan.reserve_target
    assert updated_plan.planning_horizon_turns > capital_plan.planning_horizon_turns
    assert updated_plan.reserve_share > capital_plan.reserve_share
    assert updated_plan.go_to_market_share < capital_plan.go_to_market_share
    assert (
        updated_plan.product_investment_share
        + updated_plan.go_to_market_share
        + updated_plan.reserve_share
        == 100
    )
    assert "Reserve target raised" in outcome.message


def test_step_up_reserve_discipline_shifts_plan_toward_resilience() -> None:
    product = make_product("Reserve Discipline Core")
    capital_plan = CapitalPlan(
        mode=CapitalPlanMode.BALANCED,
        source_preference=CapitalSourcePreference.DEBT,
        planning_horizon_turns=6,
        reserve_target=Decimal("3600.00"),
        product_investment_share=35,
        go_to_market_share=42,
        reserve_share=23,
    )
    state = make_state(product, capital_plan=capital_plan)
    state.finance.board_pressure = 19
    state.finance.covenant_risk = 17
    state.finance.investor_pressure = 15
    state.finance.board_confidence = 42

    outcome = apply_action(
        state,
        TurnAction.STEP_UP_RESERVE_DISCIPLINE,
        context=ActionContext(),
    )

    updated_plan = outcome.state.capital_plan
    assert updated_plan.mode is CapitalPlanMode.CONSERVE
    assert updated_plan.reserve_target > capital_plan.reserve_target
    assert updated_plan.planning_horizon_turns > capital_plan.planning_horizon_turns
    assert updated_plan.reserve_share > capital_plan.reserve_share
    assert updated_plan.go_to_market_share < capital_plan.go_to_market_share
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.covenant_risk < state.finance.covenant_risk
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert "Stepped up reserve discipline" in outcome.message


def test_harden_financing_posture_shifts_source_and_reserve() -> None:
    product = make_product("Financing Hardening Core")
    capital_plan = CapitalPlan(
        mode=CapitalPlanMode.EXPAND,
        source_preference=CapitalSourcePreference.DEBT,
        planning_horizon_turns=6,
        reserve_target=Decimal("3600.00"),
        product_investment_share=35,
        go_to_market_share=42,
        reserve_share=23,
    )
    state = make_state(
        product,
        capital_plan=capital_plan,
        cash_on_hand=Decimal("4200.00"),
    )
    state.finance.debt_principal = Decimal("2800.00")
    state.finance.loan_interest_rate = Decimal("0.0280")
    state.finance.board_pressure = 18
    state.finance.covenant_risk = 16
    state.finance.investor_pressure = 14
    state.finance.board_confidence = 40

    outcome = apply_action(
        state,
        TurnAction.HARDEN_FINANCING_POSTURE,
        context=ActionContext(),
    )

    updated_plan = outcome.state.capital_plan
    assert updated_plan.mode is CapitalPlanMode.CONSERVE
    assert updated_plan.source_preference is CapitalSourcePreference.BOOTSTRAP
    assert updated_plan.reserve_target > capital_plan.reserve_target
    assert updated_plan.planning_horizon_turns > capital_plan.planning_horizon_turns
    assert updated_plan.reserve_share > capital_plan.reserve_share
    assert updated_plan.go_to_market_share < capital_plan.go_to_market_share
    assert updated_plan.product_investment_share < capital_plan.product_investment_share
    assert outcome.state.finance.loan_interest_rate < state.finance.loan_interest_rate
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.covenant_risk < state.finance.covenant_risk
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert "Hardened financing posture" in outcome.message


def test_lock_capital_buffer_shifts_plan_toward_durability() -> None:
    product = make_product("Capital Buffer Core")
    capital_plan = CapitalPlan(
        mode=CapitalPlanMode.EXPAND,
        source_preference=CapitalSourcePreference.DEBT,
        planning_horizon_turns=6,
        reserve_target=Decimal("3600.00"),
        product_investment_share=36,
        go_to_market_share=41,
        reserve_share=23,
    )
    state = make_state(
        product,
        capital_plan=capital_plan,
        cash_on_hand=Decimal("5200.00"),
    )
    state.finance.board_pressure = 20
    state.finance.covenant_risk = 18
    state.finance.investor_pressure = 16
    state.finance.board_confidence = 40

    outcome = apply_action(
        state,
        TurnAction.LOCK_CAPITAL_BUFFER,
        context=ActionContext(),
    )

    updated_plan = outcome.state.capital_plan
    assert updated_plan.mode is CapitalPlanMode.CONSERVE
    assert updated_plan.source_preference is CapitalSourcePreference.ANGEL
    assert updated_plan.reserve_target > capital_plan.reserve_target
    assert updated_plan.planning_horizon_turns > capital_plan.planning_horizon_turns
    assert updated_plan.reserve_share > capital_plan.reserve_share
    assert updated_plan.go_to_market_share < capital_plan.go_to_market_share
    assert updated_plan.product_investment_share <= capital_plan.product_investment_share
    assert (
        updated_plan.product_investment_share
        + updated_plan.go_to_market_share
        + updated_plan.reserve_share
        == 100
    )
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.covenant_risk < state.finance.covenant_risk
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert "Locked a capital buffer" in outcome.message


def test_set_refinancing_posture_shifts_plan_toward_calm_rollover() -> None:
    product = make_product("Refinancing Posture Core")
    capital_plan = CapitalPlan(
        mode=CapitalPlanMode.EXPAND,
        source_preference=CapitalSourcePreference.DEBT,
        planning_horizon_turns=6,
        reserve_target=Decimal("3600.00"),
        product_investment_share=36,
        go_to_market_share=41,
        reserve_share=23,
    )
    state = make_state(
        product,
        capital_plan=capital_plan,
        cash_on_hand=Decimal("5100.00"),
    )
    state.finance.debt_principal = Decimal("3300.00")
    state.finance.loan_interest_rate = Decimal("0.0280")
    state.finance.board_pressure = 18
    state.finance.covenant_risk = 17
    state.finance.investor_pressure = 15
    state.finance.board_confidence = 42

    outcome = apply_action(
        state,
        TurnAction.SET_REFINANCING_POSTURE,
        context=ActionContext(),
    )

    updated_plan = outcome.state.capital_plan
    assert updated_plan.mode is CapitalPlanMode.CONSERVE
    assert updated_plan.source_preference is CapitalSourcePreference.ANGEL
    assert updated_plan.reserve_target > capital_plan.reserve_target
    assert updated_plan.planning_horizon_turns > capital_plan.planning_horizon_turns
    assert updated_plan.reserve_share > capital_plan.reserve_share
    assert updated_plan.go_to_market_share < capital_plan.go_to_market_share
    assert updated_plan.product_investment_share < capital_plan.product_investment_share
    assert outcome.state.finance.loan_interest_rate < state.finance.loan_interest_rate
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.covenant_risk < state.finance.covenant_risk
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert "Set a refinancing posture" in outcome.message


def test_set_covenant_firewall_shifts_plan_toward_reserve_discipline() -> None:
    product = make_product("Covenant Firewall Core")
    capital_plan = CapitalPlan(
        mode=CapitalPlanMode.EXPAND,
        source_preference=CapitalSourcePreference.DEBT,
        planning_horizon_turns=6,
        reserve_target=Decimal("3800.00"),
        product_investment_share=36,
        go_to_market_share=41,
        reserve_share=23,
    )
    state = make_state(
        product,
        capital_plan=capital_plan,
        cash_on_hand=Decimal("5400.00"),
    )
    state.finance.debt_principal = Decimal("3600.00")
    state.finance.loan_interest_rate = Decimal("0.0300")
    state.finance.board_pressure = 28
    state.finance.covenant_risk = 20
    state.finance.investor_pressure = 16
    state.finance.board_confidence = 38

    outcome = apply_action(
        state,
        TurnAction.SET_COVENANT_FIREWALL,
        context=ActionContext(),
    )

    updated_plan = outcome.state.capital_plan
    assert updated_plan.mode is CapitalPlanMode.CONSERVE
    assert updated_plan.source_preference is CapitalSourcePreference.ANGEL
    assert updated_plan.reserve_target > capital_plan.reserve_target
    assert updated_plan.planning_horizon_turns > capital_plan.planning_horizon_turns
    assert updated_plan.reserve_share > capital_plan.reserve_share
    assert updated_plan.go_to_market_share < capital_plan.go_to_market_share
    assert updated_plan.product_investment_share < capital_plan.product_investment_share
    assert outcome.state.finance.loan_interest_rate < state.finance.loan_interest_rate
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.covenant_risk < state.finance.covenant_risk
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert "Set a covenant firewall" in outcome.message


def test_set_debt_strategy_shifts_plan_toward_lower_debt_exposure() -> None:
    product = make_product("Debt Strategy Core")
    capital_plan = CapitalPlan(
        mode=CapitalPlanMode.EXPAND,
        source_preference=CapitalSourcePreference.DEBT,
        planning_horizon_turns=6,
        reserve_target=Decimal("3800.00"),
        product_investment_share=36,
        go_to_market_share=41,
        reserve_share=23,
    )
    state = make_state(
        product,
        capital_plan=capital_plan,
        cash_on_hand=Decimal("5400.00"),
    )
    state.finance.debt_principal = Decimal("3600.00")
    state.finance.loan_interest_rate = Decimal("0.0300")
    state.finance.board_pressure = 28
    state.finance.covenant_risk = 20
    state.finance.investor_pressure = 16
    state.finance.board_confidence = 38

    outcome = apply_action(
        state,
        TurnAction.SET_DEBT_STRATEGY,
        context=ActionContext(),
    )

    updated_plan = outcome.state.capital_plan
    assert updated_plan.mode is CapitalPlanMode.CONSERVE
    assert updated_plan.source_preference is CapitalSourcePreference.BOOTSTRAP
    assert updated_plan.reserve_target > capital_plan.reserve_target
    assert updated_plan.planning_horizon_turns > capital_plan.planning_horizon_turns
    assert updated_plan.reserve_share > capital_plan.reserve_share
    assert updated_plan.go_to_market_share < capital_plan.go_to_market_share
    assert updated_plan.product_investment_share < capital_plan.product_investment_share
    assert outcome.state.finance.debt_principal < state.finance.debt_principal
    assert outcome.state.finance.loan_interest_rate < state.finance.loan_interest_rate
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.covenant_risk < state.finance.covenant_risk
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert "Set a debt strategy" in outcome.message


def test_set_growth_firebreak_shifts_plan_toward_resilience() -> None:
    product = make_product("Growth Firebreak Core")
    capital_plan = CapitalPlan(
        mode=CapitalPlanMode.EXPAND,
        source_preference=CapitalSourcePreference.DEBT,
        planning_horizon_turns=6,
        reserve_target=Decimal("3900.00"),
        product_investment_share=36,
        go_to_market_share=41,
        reserve_share=23,
    )
    state = make_state(
        product,
        capital_plan=capital_plan,
        cash_on_hand=Decimal("5600.00"),
    )
    state.finance.board_pressure = 30
    state.finance.governance_risk = 52
    state.finance.investor_pressure = 16
    state.finance.board_confidence = 38
    state.support_program.backlog_queue = 12
    state.support_program.escalation_queue = 4

    outcome = apply_action(
        state,
        TurnAction.SET_GROWTH_FIREBREAK,
        context=ActionContext(),
    )

    updated_plan = outcome.state.capital_plan
    assert updated_plan.mode in {CapitalPlanMode.BALANCED, CapitalPlanMode.CONSERVE}
    assert updated_plan.source_preference is CapitalSourcePreference.BOOTSTRAP
    assert updated_plan.reserve_target > capital_plan.reserve_target
    assert updated_plan.planning_horizon_turns > capital_plan.planning_horizon_turns
    assert updated_plan.reserve_share > capital_plan.reserve_share
    assert updated_plan.go_to_market_share < capital_plan.go_to_market_share
    assert updated_plan.product_investment_share < capital_plan.product_investment_share
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.governance_risk < state.finance.governance_risk
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert "Set a growth firebreak" in outcome.message


def test_set_path_capital_posture_aligns_plan_to_current_route() -> None:
    product = make_product("Path Capital Posture Core")
    capital_plan = CapitalPlan(
        mode=CapitalPlanMode.EXPAND,
        source_preference=CapitalSourcePreference.DEBT,
        planning_horizon_turns=6,
        reserve_target=Decimal("3900.00"),
        product_investment_share=36,
        go_to_market_share=41,
        reserve_share=23,
    )
    state = make_state(
        product,
        capital_plan=capital_plan,
        cash_on_hand=Decimal("5600.00"),
    )
    state.finance.board_pressure = 28
    state.finance.governance_risk = 48
    state.finance.investor_pressure = 16
    state.finance.board_confidence = 38
    state.company.reputation = 74
    state.products[0].user_count = 220
    account = CustomerAccount(
        name="Enterprise Flagship",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("3200.00"),
        support_tier=SupportTier.WHITE_GLOVE,
        satisfaction=56,
        onboarding_health=54,
        support_load=28,
        open_tickets=6,
        sla_breach_risk=48,
        renewal_health=48,
        expansion_potential=66,
        renewal_turn=8,
        churn_risk=24,
        status=CustomerAccountStatus.AT_RISK,
    )
    partnership = PartnershipDeal(
        name="Hotspot Reseller",
        product_id=product.id,
        channel=PartnerChannel.RESELLER,
        status=PartnershipStatus.RECOVERY,
        quality=60,
        risk=52,
        conflict_pressure=48,
        enablement_level=28,
        sourced_revenue=Decimal("3000.00"),
        sourced_users=40,
        rev_share_rate=Decimal("0.1900"),
    )
    state.customer_accounts = [account]
    state.partnerships = [partnership]

    outcome = apply_action(
        state,
        TurnAction.SET_PATH_CAPITAL_POSTURE,
        context=ActionContext(),
    )

    updated_plan = outcome.state.capital_plan
    assert updated_plan.mode in {CapitalPlanMode.BALANCED, CapitalPlanMode.CONSERVE}
    assert updated_plan.source_preference in {
        CapitalSourcePreference.ANGEL,
        CapitalSourcePreference.BOOTSTRAP,
    }
    assert updated_plan.reserve_target > capital_plan.reserve_target
    assert updated_plan.planning_horizon_turns > capital_plan.planning_horizon_turns
    assert updated_plan.reserve_share > capital_plan.reserve_share
    assert updated_plan.go_to_market_share < capital_plan.go_to_market_share
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.governance_risk < state.finance.governance_risk
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert "capital posture" in outcome.message


def test_set_endgame_capital_map_realigns_plan_for_board_reset_heat() -> None:
    product = make_product("Endgame Capital Map Core")
    capital_plan = CapitalPlan(
        mode=CapitalPlanMode.EXPAND,
        source_preference=CapitalSourcePreference.DEBT,
        planning_horizon_turns=6,
        reserve_target=Decimal("3900.00"),
        product_investment_share=36,
        go_to_market_share=41,
        reserve_share=23,
    )
    account = CustomerAccount(
        name="Board Reset Queue Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("3600.00"),
        support_tier=SupportTier.WHITE_GLOVE,
        satisfaction=54,
        onboarding_health=50,
        support_load=34,
        open_tickets=8,
        sla_breach_risk=58,
        renewal_health=48,
        expansion_potential=62,
        renewal_turn=7,
        churn_risk=28,
        status=CustomerAccountStatus.AT_RISK,
    )
    partnership = PartnershipDeal(
        name="Board Reset Hotspot Reseller",
        product_id=product.id,
        channel=PartnerChannel.RESELLER,
        status=PartnershipStatus.RECOVERY,
        quality=60,
        risk=54,
        conflict_pressure=50,
        enablement_level=28,
        sourced_revenue=Decimal("3200.00"),
        sourced_users=42,
        rev_share_rate=Decimal("0.2000"),
    )
    state = make_state(
        product,
        capital_plan=capital_plan,
        customer_accounts=[account],
        partnerships=[partnership],
        cash_on_hand=Decimal("5800.00"),
    )
    state.finance.board_pressure = 32
    state.finance.governance_risk = 56
    state.finance.investor_pressure = 18
    state.finance.covenant_risk = 14
    state.finance.board_confidence = 34
    state.finance.board_warning_level = 2
    state.finance.restructuring_pressure = 16
    state.support_program.backlog_queue = 12
    state.support_program.escalation_queue = 4

    outcome = apply_action(
        state,
        TurnAction.SET_ENDGAME_CAPITAL_MAP,
        context=ActionContext(),
    )

    updated_plan = outcome.state.capital_plan
    assert updated_plan.mode is CapitalPlanMode.CONSERVE
    assert updated_plan.source_preference is CapitalSourcePreference.BOOTSTRAP
    assert updated_plan.reserve_target > capital_plan.reserve_target
    assert updated_plan.planning_horizon_turns > capital_plan.planning_horizon_turns
    assert updated_plan.reserve_share > capital_plan.reserve_share
    assert updated_plan.go_to_market_share < capital_plan.go_to_market_share
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.governance_risk < state.finance.governance_risk
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.covenant_risk < state.finance.covenant_risk
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert "endgame capital map" in outcome.message


def test_set_exit_readiness_buffer_realigns_plan_for_board_reset_heat() -> None:
    product = make_product("Exit Readiness Buffer Core")
    capital_plan = CapitalPlan(
        mode=CapitalPlanMode.EXPAND,
        source_preference=CapitalSourcePreference.DEBT,
        planning_horizon_turns=6,
        reserve_target=Decimal("4000.00"),
        product_investment_share=36,
        go_to_market_share=41,
        reserve_share=23,
    )
    account = CustomerAccount(
        name="Exit Buffer Anchor",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("3400.00"),
        support_tier=SupportTier.WHITE_GLOVE,
        satisfaction=54,
        onboarding_health=48,
        support_load=32,
        open_tickets=7,
        sla_breach_risk=52,
        renewal_health=46,
        expansion_potential=60,
        renewal_turn=7,
        churn_risk=26,
        status=CustomerAccountStatus.AT_RISK,
    )
    partnership = PartnershipDeal(
        name="Exit Buffer Hotspot Reseller",
        product_id=product.id,
        channel=PartnerChannel.RESELLER,
        status=PartnershipStatus.RECOVERY,
        quality=60,
        risk=54,
        conflict_pressure=50,
        enablement_level=26,
        sourced_revenue=Decimal("3100.00"),
        sourced_users=40,
        rev_share_rate=Decimal("0.2000"),
    )
    state = make_state(
        product,
        capital_plan=capital_plan,
        customer_accounts=[account],
        partnerships=[partnership],
        cash_on_hand=Decimal("5900.00"),
    )
    state.finance.board_pressure = 30
    state.finance.governance_risk = 54
    state.finance.investor_pressure = 18
    state.finance.covenant_risk = 16
    state.finance.board_confidence = 34
    state.finance.restructuring_pressure = 16
    state.support_program.backlog_queue = 12
    state.support_program.escalation_queue = 4

    outcome = apply_action(
        state,
        TurnAction.SET_EXIT_READINESS_BUFFER,
        context=ActionContext(),
    )

    updated_plan = outcome.state.capital_plan
    assert updated_plan.mode is CapitalPlanMode.CONSERVE
    assert updated_plan.source_preference is CapitalSourcePreference.BOOTSTRAP
    assert updated_plan.reserve_target > capital_plan.reserve_target
    assert updated_plan.planning_horizon_turns > capital_plan.planning_horizon_turns
    assert updated_plan.reserve_share > capital_plan.reserve_share
    assert updated_plan.go_to_market_share < capital_plan.go_to_market_share
    assert outcome.state.finance.board_pressure < state.finance.board_pressure
    assert outcome.state.finance.governance_risk < state.finance.governance_risk
    assert outcome.state.finance.investor_pressure < state.finance.investor_pressure
    assert outcome.state.finance.covenant_risk < state.finance.covenant_risk
    assert outcome.state.finance.board_confidence > state.finance.board_confidence
    assert outcome.state.company.cash_on_hand < state.company.cash_on_hand
    assert "exit-readiness buffer" in outcome.message


def test_debt_rollover_action_reduces_covenant_pressure_without_new_cash() -> None:
    product = make_product("Debt Rollover Core")
    state = make_state(product, cash_on_hand=Decimal("4200.00"))
    state.finance.debt_principal = Decimal("3200.00")
    state.finance.loan_interest_rate = Decimal("0.0280")
    state.finance.covenant_risk = 18
    state.finance.investor_pressure = 16
    state.finance.board_confidence = 68

    outcome = apply_action(state, TurnAction.DEBT_ROLLOVER, context=ActionContext())

    assert outcome.state.company.cash_on_hand == Decimal("4200.00")
    assert outcome.state.finance.debt_principal > Decimal("3200.00")
    assert outcome.state.finance.loan_interest_rate > Decimal("0.0280")
    assert outcome.state.finance.covenant_risk < 18
    assert outcome.state.finance.investor_pressure < 16
    assert outcome.state.finance.board_confidence < 68
    assert "Rolled debt forward" in outcome.message


def test_finance_drift_penalizes_misaligned_capital_plan() -> None:
    finance = FinanceState(
        debt_principal=Decimal("5400.00"),
        loan_interest_rate=Decimal("0.0300"),
        investor_pressure=14,
        board_confidence=62,
        equity_dilution=Decimal("0.2400"),
    )
    company = Company(
        name="Capital Stress",
        cash_on_hand=Decimal("1700.00"),
        reputation=54,
    )
    capital_plan = CapitalPlan(
        mode=CapitalPlanMode.EXPAND,
        source_preference=CapitalSourcePreference.VENTURE,
    )

    summary = apply_end_of_turn_finance_drift(
        finance,
        company,
        capital_plan=capital_plan,
        net_cash_flow=Decimal("-950.00"),
        turn_history=[],
        technical_debt_load=68,
        active_channels=0,
        support_backlog=28,
    )

    assert finance.investor_pressure > 14
    assert finance.covenant_risk > 0
    assert finance.board_confidence < 62
    assert summary.forecast_net_cash_flow < Decimal("0.00")


def test_deeper_catalog_softens_price_increase_account_shock() -> None:
    shallow_product = make_product(
        "Shallow Suite",
        quality=72,
        revenue_per_user=Decimal("50.00"),
        pricing_tier=PricingTier.PREMIUM,
        packaging_strategy=PackagingStrategy.SUITE,
        target_segment=MarketSegment.ENTERPRISE,
        package_catalog_depth=0,
        add_on_catalog_depth=0,
    )
    deep_product = shallow_product.model_copy(
        update={
            "id": UUID("00000000-0000-0000-0000-000000000111"),
            "name": "Deep Suite",
            "package_catalog_depth": 3,
            "add_on_catalog_depth": 2,
        }
    )
    shallow_account = CustomerAccount(
        name="Shallow Anchor",
        product_id=shallow_product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("1200.00"),
        plan_tier=PricingTier.PREMIUM,
        subscription_package=SubscriptionPackage.GROWTH,
        annual_prepay=True,
        satisfaction=78,
        expansion_potential=68,
        renewal_turn=6,
        churn_risk=16,
        status=CustomerAccountStatus.ACTIVE,
    )
    deep_account = shallow_account.model_copy(
        update={
            "id": UUID("00000000-0000-0000-0000-000000000222"),
            "name": "Deep Anchor",
            "product_id": deep_product.id,
        }
    )

    shallow_state = make_state(shallow_product, customer_accounts=[shallow_account])
    deep_state = make_state(deep_product, customer_accounts=[deep_account])

    shallow_outcome = apply_action(
        shallow_state,
        TurnAction.RUN_PRICE_INCREASE,
        context=ActionContext(target_product_id=shallow_product.id),
    )
    deep_outcome = apply_action(
        deep_state,
        TurnAction.RUN_PRICE_INCREASE,
        context=ActionContext(target_product_id=deep_product.id),
    )

    shallow_invoice_gain = (
        shallow_outcome.state.customer_accounts[0].invoice_risk - shallow_account.invoice_risk
    )
    deep_invoice_gain = (
        deep_outcome.state.customer_accounts[0].invoice_risk - deep_account.invoice_risk
    )

    assert deep_invoice_gain < shallow_invoice_gain


def test_run_badges_capture_channel_builder_when_partnerships_scale() -> None:
    product = make_product("Channel One", lifecycle_stage=LifecycleStage.MATURE, user_count=120)
    partnerships = [
        PartnershipDeal(
            name="Channel One Reseller",
            product_id=product.id,
            channel=PartnerChannel.RESELLER,
            status=PartnershipStatus.ACTIVE,
            sourced_revenue=Decimal("1200.00"),
            sourced_users=20,
        ),
        PartnershipDeal(
            name="Channel One Marketplace",
            product_id=product.id,
            channel=PartnerChannel.MARKETPLACE,
            status=PartnershipStatus.ACTIVE,
            sourced_revenue=Decimal("980.00"),
            sourced_users=24,
        ),
    ]
    state = make_state(product, partnerships=partnerships, cash_on_hand=Decimal("11000.00"))

    badges = calculate_run_badges(state, calculate_run_score(state))

    assert "channel_builder" in badges


def test_meta_progression_summary_derives_unlocks_from_archives() -> None:
    archives = [
        RunArchiveSummary(
            archive_key="run-1",
            slot_name="active",
            company_name="NEXUS TECH",
            scenario_title="Founder Journey",
            completed_turn=12,
            victory_achieved=True,
            game_over=False,
            exit_outcome="strategic_acquisition",
            total_score=212,
            score_tier="strong",
            campaign_grade="A",
            estimated_valuation=Decimal("52000.00"),
            achievement_badges=("board_trusted", "channel_builder"),
            strategic_outlook="strategic_acquisition",
            offer_value=Decimal("61000.00"),
            final_cash=Decimal("14000.00"),
            final_reputation=68,
            archived_at="2026-04-29T00:00:00+00:00",
        )
    ]

    summary = summarize_meta_progression(archives)

    assert summary.total_runs == 1
    assert summary.victories == 1
    assert "first_victory" in summary.unlocked_achievements
    assert "channel_builder" in summary.unlocked_achievements
    assert summary.campaign_stage in {"operator", "institutional"}
    assert "core achievements" in summary.achievement_progress
    assert summary.outcome_coverage_progress
    assert summary.reward_mix
    assert summary.campaign_ladder
    assert summary.unlocked_rewards
    assert summary.archive_highlights
    assert summary.campaign_tier in {"silver", "gold"}
    assert summary.next_reward


def test_unlock_catalog_surfaces_exact_reward_metadata() -> None:
    archives = [
        RunArchiveSummary(
            archive_key="run-1",
            slot_name="active",
            company_name="NEXUS TECH",
            scenario_title="Founder Journey",
            completed_turn=12,
            victory_achieved=True,
            game_over=False,
            exit_outcome="ipo_ready",
            total_score=236,
            score_tier="strong",
            campaign_grade="S",
            estimated_valuation=Decimal("72000.00"),
            achievement_badges=("board_trusted", "channel_builder", "monetization_architect"),
            strategic_outlook="ipo_ready",
            offer_value=Decimal("88000.00"),
            final_cash=Decimal("18000.00"),
            final_reputation=74,
            archived_at="2026-04-30T00:00:00+00:00",
        )
    ]

    catalog = build_unlock_catalog(archives)

    assert catalog.total_rewards >= 11
    assert catalog.unlocked_rewards >= 4
    assert any(entry.reward_type == "scenario" for entry in catalog.entries if entry.unlocked)
    assert any(
        entry.reward_id == "board_command_cloud" for entry in catalog.entries if entry.unlocked
    )
    assert catalog.next_unlock_label


def test_reward_unlocks_gate_progression_content_ids() -> None:
    locked_without_archives = is_reward_unlocked(
        [],
        reward_type="scenario",
        reward_id="campaign_ladder_climb",
    )
    unlocked_baseline_content = is_reward_unlocked(
        [],
        reward_type="scenario",
        reward_id="bootstrap_studio",
    )
    unlocked_with_victory_archive = is_reward_unlocked(
        [
            RunArchiveSummary(
                archive_key="run-1",
                slot_name="active",
                company_name="NEXUS TECH",
                scenario_title="Founder Journey",
                completed_turn=12,
                victory_achieved=True,
                game_over=False,
                exit_outcome="strategic_acquisition",
                total_score=212,
                score_tier="strong",
                campaign_grade="A",
                estimated_valuation=Decimal("52000.00"),
                achievement_badges=("board_trusted",),
                strategic_outlook="strategic_acquisition",
                offer_value=Decimal("61000.00"),
                final_cash=Decimal("14000.00"),
                final_reputation=68,
                archived_at="2026-04-29T00:00:00+00:00",
            )
        ],
        reward_type="scenario",
        reward_id="campaign_ladder_climb",
    )

    assert locked_without_archives is False
    assert unlocked_baseline_content is True
    assert unlocked_with_victory_archive is True


def test_reward_unlocks_gate_campaign_start_ids() -> None:
    locked_without_archives = is_reward_unlocked(
        [],
        reward_type="campaign_start",
        reward_id="ipo_readiness_launchpad",
    )
    unlocked_with_ipo_archive = is_reward_unlocked(
        [
            RunArchiveSummary(
                archive_key="run-ipo",
                slot_name="active",
                company_name="NEXUS TECH",
                scenario_title="Founder Journey",
                completed_turn=18,
                victory_achieved=True,
                game_over=False,
                exit_outcome="ipo_ready",
                total_score=244,
                score_tier="elite",
                campaign_grade="S",
                estimated_valuation=Decimal("98000.00"),
                achievement_badges=("board_trusted", "capital_disciplined"),
                strategic_outlook="ipo_ready",
                offer_value=Decimal("104000.00"),
                final_cash=Decimal("22000.00"),
                final_reputation=78,
                archived_at="2026-05-06T00:00:00+00:00",
            )
        ],
        reward_type="campaign_start",
        reward_id="ipo_readiness_launchpad",
    )
    unlocked_with_acquisition_archive = is_reward_unlocked(
        [
            RunArchiveSummary(
                archive_key="run-acq",
                slot_name="active",
                company_name="NEXUS TECH",
                scenario_title="Founder Journey",
                completed_turn=19,
                victory_achieved=True,
                game_over=False,
                exit_outcome="strategic_acquisition",
                total_score=246,
                score_tier="elite",
                campaign_grade="S",
                estimated_valuation=Decimal("93000.00"),
                achievement_badges=("board_trusted", "channel_builder"),
                strategic_outlook="strategic_acquisition",
                offer_value=Decimal("88000.00"),
                final_cash=Decimal("19400.00"),
                final_reputation=76,
                archived_at="2026-05-06T00:00:00+00:00",
            )
        ],
        reward_type="campaign_start",
        reward_id="acquisition_diligence_sprint",
    )
    unlocked_with_independence_archive = is_reward_unlocked(
        [
            RunArchiveSummary(
                archive_key="run-indie",
                slot_name="active",
                company_name="NEXUS TECH",
                scenario_title="Founder Journey",
                completed_turn=20,
                victory_achieved=True,
                game_over=False,
                exit_outcome="profitable_independence",
                total_score=234,
                score_tier="elite",
                campaign_grade="S",
                estimated_valuation=Decimal("76000.00"),
                achievement_badges=("capital_disciplined", "board_trusted"),
                strategic_outlook="profitable_independence",
                offer_value=Decimal("52000.00"),
                final_cash=Decimal("18600.00"),
                final_reputation=74,
                archived_at="2026-05-06T00:00:00+00:00",
            )
        ],
        reward_type="campaign_start",
        reward_id="independence_compounder",
    )

    assert locked_without_archives is False
    assert unlocked_with_ipo_archive is True
    assert unlocked_with_acquisition_archive is True
    assert unlocked_with_independence_archive is True


def test_archive_comparison_summary_surfaces_archive_leaders() -> None:
    archives = [
        RunArchiveSummary(
            archive_key="run-1",
            slot_name="active",
            company_name="NEXUS TECH",
            scenario_title="Founder Journey",
            completed_turn=12,
            victory_achieved=True,
            game_over=False,
            exit_outcome="strategic_acquisition",
            total_score=212,
            score_tier="strong",
            campaign_grade="A",
            estimated_valuation=Decimal("52000.00"),
            achievement_badges=("board_trusted", "channel_builder"),
            strategic_outlook="strategic_acquisition",
            offer_value=Decimal("61000.00"),
            final_cash=Decimal("14000.00"),
            final_reputation=68,
            archived_at="2026-04-29T00:00:00+00:00",
        ),
        RunArchiveSummary(
            archive_key="run-2",
            slot_name="active",
            company_name="Signal Forge",
            scenario_title="Reserve Discipline Run",
            completed_turn=15,
            victory_achieved=True,
            game_over=False,
            exit_outcome="profitable_independence",
            total_score=196,
            score_tier="strong",
            campaign_grade="A",
            estimated_valuation=Decimal("48000.00"),
            achievement_badges=("capital_disciplined",),
            strategic_outlook="profitable_independence",
            offer_value=Decimal("38000.00"),
            final_cash=Decimal("18800.00"),
            final_reputation=72,
            archived_at="2026-04-30T00:00:00+00:00",
        ),
    ]

    comparison = build_archive_comparison(archives)

    assert comparison.compared_runs == 2
    assert comparison.average_score > 0
    assert "Signal Forge" in comparison.strongest_cash_label
    assert "NEXUS TECH" in comparison.best_offer_label
    assert comparison.outcome_mix == ("profitable_independence", "strategic_acquisition")
    assert comparison.missing_outcomes == ("ipo_ready",)
    assert comparison.best_acquisition_label != "-"
    assert comparison.best_independence_label != "-"
    assert comparison.best_restructure_label == "-"
    assert comparison.path_balance_note
    assert comparison.next_gap
