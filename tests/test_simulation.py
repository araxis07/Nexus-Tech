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
    assert "board_recovery_window" in registry_ids
    assert "capital_market_freeze" in registry_ids
    assert "succession_gap" in registry_ids
    assert "strategic_crossroads" in registry_ids
    assert "public_market_scrutiny" in registry_ids
    assert "acquirer_diligence" in registry_ids
    assert "independence_reckoning" in registry_ids


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
    backup_count = sum(1 for employee in outcome.state.employees if employee.is_team_lead)
    assert updated_manager.leadership_score > manager.leadership_score
    assert backup_count >= 1
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

    assert summary.revenue_at_risk_accounts >= 1
    assert summary.renewal_pressure_accounts >= 1
    assert revenue_at_risk_accounts >= 1
    assert renewal_pressure_accounts >= 1
    assert state.customer_accounts[0].renewal_health < 46


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

    outcome = apply_action(
        state,
        TurnAction.SET_SUPPORT_LANE_FOCUS,
        context=ActionContext(support_lane_focus=SupportLaneFocus.ENTERPRISE),
    )

    assert outcome.state.support_program.lane_focus is SupportLaneFocus.ENTERPRISE
    assert outcome.state.support_program.backlog_queue == 4


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
    assert len(planner.scenario_compare) == 3
    assert planner.capital_alert
    assert planner.summary


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


def test_partnership_portfolio_summary_surfaces_status_mix() -> None:
    product = make_product("Partner Hub")
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
        ),
    ]
    state = make_state(product, partnerships=partnerships)

    summary = calculate_partnership_portfolio(state)

    assert summary.total_count == 2
    assert summary.active_count == 1
    assert summary.recovery_count == 1
    assert summary.sourced_revenue == Decimal("2020.00")
    assert summary.average_fatigue >= 0
    assert summary.channel_conflict_index >= 0
    assert summary.dominant_share_percent >= 50
    assert summary.dominant_channel in {"reseller", "marketplace"}


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
    assert comparison.next_gap
