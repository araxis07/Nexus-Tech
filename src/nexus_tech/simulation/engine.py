"""Turn orchestration for the simulation loop."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from decimal import Decimal
from uuid import UUID

from nexus_tech.config import DEFAULT_PRODUCT_TEMPLATE_ID, DEFAULT_SCENARIO_ID
from nexus_tech.domain.constants import ZERO_MONEY
from nexus_tech.domain.models import (
    BudgetStance,
    CampaignGoalId,
    CandidateTrait,
    CapitalPlanMode,
    CapitalSourcePreference,
    CompanyStrategy,
    Competitor,
    DifficultyMode,
    Employee,
    EmployeeRole,
    EventHistoryEntry,
    FunctionalBudgetPreset,
    GameState,
    LifecycleStage,
    MarketCycle,
    MarketSegment,
    MilestoneEntry,
    PackagingStrategy,
    PartnerChannel,
    PendingEvent,
    PricingTier,
    Product,
    ProductReleaseType,
    RenewalOfferType,
    RoadmapFocus,
    RoadmapProjectType,
    Seniority,
    SupportInvestmentFocus,
    SupportLaneFocus,
    TurnAction,
)
from nexus_tech.domain.money import format_money, quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.campaign import (
    CampaignGoalProgress,
    evaluate_campaign_goal,
)
from nexus_tech.simulation.capital_planning import apply_set_capital_plan
from nexus_tech.simulation.competition import advance_competitors, summarize_competitor_moves
from nexus_tech.simulation.competitor_intel import record_competitor_intel
from nexus_tech.simulation.customer_success import (
    get_customer_account_by_id,
    invest_in_customer_success,
    make_renewal_offer,
    run_retention_play,
    run_win_back_play,
)
from nexus_tech.simulation.customers import CustomerTurnSummary, apply_end_of_turn_customers
from nexus_tech.simulation.difficulty import get_difficulty_profile
from nexus_tech.simulation.economy import (
    calculate_product_operating_cost,
    calculate_product_revenue,
    calculate_total_operating_cost,
    calculate_total_product_operating_cost,
    calculate_total_revenue,
    calculate_total_salary_cost,
    is_game_over,
)
from nexus_tech.simulation.employee_progression import (
    apply_end_of_turn_employee_progression,
    promote_employee,
    run_comp_review,
    train_employee,
)
from nexus_tech.simulation.endgame import apply_exit_outcome
from nexus_tech.simulation.events import EventTurnOutcome, resolve_turn_event
from nexus_tech.simulation.finance import (
    FinanceTurnSummary,
    apply_end_of_turn_finance_drift,
    apply_raise_angel,
    apply_raise_vc,
    apply_repay_debt,
    apply_take_loan,
)
from nexus_tech.simulation.functional_budgeting import (
    apply_set_functional_budget,
    get_functional_budget_profile,
)
from nexus_tech.simulation.governance import (
    GovernanceSummary,
    apply_end_of_turn_governance,
    execute_board_response,
    execute_restructure_plan,
    start_board_recovery_plan,
)
from nexus_tech.simulation.growth import calculate_company_reputation_delta, resolve_growth
from nexus_tech.simulation.hiring_pipeline import (
    age_hiring_candidates,
    interview_candidate,
    make_hiring_offer,
    screen_candidate,
    source_candidates,
)
from nexus_tech.simulation.late_game import LateGameSummary, apply_end_of_turn_late_game
from nexus_tech.simulation.market import advance_market_cycle
from nexus_tech.simulation.milestones import resolve_new_milestones
from nexus_tech.simulation.operations import OperationsSummary, apply_end_of_turn_operations
from nexus_tech.simulation.partnerships import (
    apply_end_of_turn_partnerships,
    create_partnership,
    get_partnership_by_id,
    invest_in_partner_enablement,
    reactivate_partnership,
    renegotiate_partnership,
)
from nexus_tech.simulation.planning import (
    build_quarter_plan,
    get_budget_profile,
    is_quarter_plan_due,
)
from nexus_tech.simulation.pricing import (
    apply_adjust_pricing,
    apply_expand_add_on_catalog,
    apply_expand_package_catalog,
    apply_run_add_on_campaign,
    apply_run_package_migration,
    apply_run_price_increase,
    apply_set_packaging_strategy,
)
from nexus_tech.simulation.product_progression import (
    ProductDrift,
    apply_add_feature,
    apply_end_of_turn_progression,
    apply_improve_quality,
    apply_marketing,
    apply_reduce_technical_debt,
    apply_sunset_product,
)
from nexus_tech.simulation.randomness import RandomLike
from nexus_tech.simulation.releases import plan_product_release, work_product_release
from nexus_tech.simulation.reporting import (
    RunScore,
    append_turn_history,
    calculate_run_score,
    check_victory,
)
from nexus_tech.simulation.roadmap import (
    get_effective_roadmap_focus,
    get_roadmap_profile,
    is_roadmap_due,
)
from nexus_tech.simulation.roadmap_projects import (
    start_roadmap_project,
    work_roadmap_project,
)
from nexus_tech.simulation.sales import advance_sales_deal, age_sales_pipeline, create_sales_deal
from nexus_tech.simulation.scaling import calculate_company_scale_pressure
from nexus_tech.simulation.scenarios import (
    create_game_state_from_scenario,
    create_product_from_template,
)
from nexus_tech.simulation.segments import calculate_competitor_pressure
from nexus_tech.simulation.strategy import apply_set_company_strategy, get_strategy_profile
from nexus_tech.simulation.support import clamp_int
from nexus_tech.simulation.support_program import (
    apply_end_of_turn_support_program,
    invest_in_support_staffing,
    route_support_escalation,
    set_support_lane_focus,
    triage_support_backlog,
    upgrade_support_program,
)
from nexus_tech.simulation.team import (
    TeamCondition,
    apply_end_of_turn_team_drift,
    apply_rest_team,
    appoint_team_lead,
    assign_employee,
    assign_manager,
    calculate_product_team_modifier,
    calculate_team_condition,
    clear_manager_assignment,
    clear_manager_links,
    create_employee,
    get_employee_by_id,
    run_org_reorg,
    run_succession_review,
    sanitize_management_links,
    unassign_employee,
    unassign_employees_from_product,
    update_succession_risk,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ActionContext:
    """Optional inputs attached to a player action."""

    target_product_id: UUID | None = None
    employee_id: UUID | None = None
    new_product_name: str | None = None
    new_product_template_id: str | None = None
    hire_full_name: str | None = None
    hire_role: EmployeeRole | None = None
    hire_seniority: Seniority | None = None
    hire_specialization: str | None = None
    hire_trait: CandidateTrait | None = None
    strategy: CompanyStrategy | None = None
    pricing_tier: PricingTier | None = None
    packaging_strategy: PackagingStrategy | None = None
    target_segment: MarketSegment | None = None
    support_investment_focus: SupportInvestmentFocus | None = None
    roadmap_focus: RoadmapFocus | None = None
    budget_stance: BudgetStance | None = None
    release_type: ProductReleaseType | None = None
    release_id: UUID | None = None
    sales_deal_id: UUID | None = None
    roadmap_project_type: RoadmapProjectType | None = None
    roadmap_project_id: UUID | None = None
    customer_account_id: UUID | None = None
    functional_budget_preset: FunctionalBudgetPreset | None = None
    hiring_candidate_id: UUID | None = None
    manager_id: UUID | None = None
    support_lane_focus: SupportLaneFocus | None = None
    renewal_offer_type: RenewalOfferType | None = None
    partner_channel: PartnerChannel | None = None
    partnership_id: UUID | None = None
    capital_plan_mode: CapitalPlanMode | None = None
    capital_source_preference: CapitalSourcePreference | None = None


@dataclass(frozen=True)
class ActionOutcome:
    """Result of a single player action."""

    state: GameState
    message: str
    turn_should_end: bool = False


@dataclass(frozen=True)
class ProductTurnSummary:
    """Per-product outcome for the turn summary UI."""

    product_id: UUID
    product_name: str
    lifecycle_stage: LifecycleStage
    revenue: Decimal
    operating_cost: Decimal
    acquired_users: int
    churned_users: int
    net_user_delta: int
    quality_delta: int
    bug_delta: int
    target_segment: MarketSegment
    competitor_pressure: int


@dataclass(frozen=True)
class TurnResolution:
    """Summary of what happened when a turn was simulated."""

    state: GameState
    resolved_turn: int
    total_revenue: Decimal
    baseline_operating_cost: Decimal
    total_product_operating_cost: Decimal
    total_operations_cost: Decimal
    total_late_game_cost: Decimal
    total_salary_cost: Decimal
    total_finance_cost: Decimal
    total_operating_cost: Decimal
    net_cash_flow: Decimal
    customer_summary: CustomerTurnSummary
    reputation_delta: int
    product_summaries: list[ProductTurnSummary]
    team_condition: TeamCondition
    finance_summary: FinanceTurnSummary
    governance_summary: GovernanceSummary
    pending_event: PendingEvent | None
    event_history_entry: EventHistoryEntry | None
    unlocked_milestones: list[MilestoneEntry]
    run_score: RunScore
    operations_summary: OperationsSummary
    late_game_summary: LateGameSummary
    roadmap_due: bool
    roadmap_focus: RoadmapFocus
    quarter_plan_due: bool
    market_cycle: MarketCycle
    market_cycle_changed: bool
    campaign_goal_progress: CampaignGoalProgress
    scale_pressure_summary: str
    victory_reason: str | None
    narrative: str


def create_new_game(
    company_name: str | None = None,
    product_name: str | None = None,
    *,
    scenario_id: str = DEFAULT_SCENARIO_ID,
    difficulty_mode: DifficultyMode | None = None,
    campaign_goal_id: CampaignGoalId | None = None,
) -> GameState:
    """Create the initial playable game state from a selected scenario."""

    state = create_game_state_from_scenario(
        scenario_id,
        company_name=company_name,
        primary_product_name=product_name,
    )
    if difficulty_mode is not None:
        state.difficulty_mode = difficulty_mode
    if campaign_goal_id is not None:
        state.campaign_goal_id = campaign_goal_id
    return state


def apply_action(
    state: GameState,
    action: TurnAction,
    context: ActionContext | None = None,
) -> ActionOutcome:
    """Apply a player action without running the end-of-turn simulation."""

    context = context or ActionContext()

    if state.company.game_over:
        return ActionOutcome(
            state=state,
            message="The company has already shut down.",
            turn_should_end=True,
        )

    if state.pending_event is not None and action not in (
        TurnAction.VIEW_STATUS,
        TurnAction.REVIEW_TEAM,
        TurnAction.REVIEW_FINANCE,
        TurnAction.REVIEW_CUSTOMERS,
        TurnAction.REVIEW_PIPELINE,
        TurnAction.REVIEW_BOARD,
        TurnAction.REVIEW_PARTNERSHIPS,
        TurnAction.VIEW_REPORT,
    ):
        return ActionOutcome(
            state=state,
            message="Resolve the pending event before taking new actions.",
        )

    if action in (
        TurnAction.VIEW_STATUS,
        TurnAction.REVIEW_TEAM,
        TurnAction.REVIEW_FINANCE,
        TurnAction.REVIEW_CUSTOMERS,
        TurnAction.REVIEW_PIPELINE,
        TurnAction.REVIEW_BOARD,
        TurnAction.VIEW_REPORT,
        TurnAction.END_TURN,
    ):
        if action is TurnAction.VIEW_STATUS:
            return ActionOutcome(state=state, message="Status refreshed.")
        if action is TurnAction.REVIEW_TEAM:
            return ActionOutcome(state=state, message="Team review refreshed.")
        if action is TurnAction.REVIEW_FINANCE:
            return ActionOutcome(state=state, message="Finance review refreshed.")
        if action is TurnAction.REVIEW_CUSTOMERS:
            return ActionOutcome(state=state, message="Customer account review refreshed.")
        if action is TurnAction.REVIEW_PIPELINE:
            return ActionOutcome(state=state, message="Pipeline review refreshed.")
        if action is TurnAction.REVIEW_BOARD:
            return ActionOutcome(state=state, message="Board and governance review refreshed.")
        if action is TurnAction.REVIEW_PARTNERSHIPS:
            return ActionOutcome(state=state, message="Partnership and capital review refreshed.")
        if action is TurnAction.VIEW_REPORT:
            return ActionOutcome(state=state, message="Run report refreshed.")
        return ActionOutcome(state=state, message="Ending turn.", turn_should_end=True)

    if state.action_points_remaining <= 0:
        return ActionOutcome(
            state=state,
            message="No action points remaining. Review status or end the turn.",
        )

    next_state = state.model_copy(deep=True)
    next_state.action_points_remaining -= 1

    if action is TurnAction.EXECUTE_BOARD_RESPONSE:
        summary = execute_board_response(next_state)
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug(
            "Executed board response for ask %s.",
            next_state.finance.active_board_ask.value,
        )
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.START_BOARD_RECOVERY_PLAN:
        summary = start_board_recovery_plan(next_state)
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Started board recovery plan.")
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.EXECUTE_RESTRUCTURE_PLAN:
        summary = execute_restructure_plan(next_state)
        update_succession_risk(next_state.employees)
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Executed restructure plan.")
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.CREATE_PRODUCT:
        if context.new_product_name is None:
            raise ValueError("A name is required to create a product.")
        if next_state.company.cash_on_hand < BALANCE.create_product_cost:
            raise ValueError("Not enough cash to create a new product.")

        template_id = context.new_product_template_id or DEFAULT_PRODUCT_TEMPLATE_ID
        product, template = create_product_from_template(
            context.new_product_name,
            next_state.products,
            template_id=template_id,
        )
        next_state.company.cash_on_hand = quantize_money(
            next_state.company.cash_on_hand - BALANCE.create_product_cost
        )
        next_state.products.append(product)
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Created product %s from template %s.", product.name, template.template_id)
        return ActionOutcome(
            state=next_state,
            message=(
                f"Created {product.name} from {template.title}. "
                f"Cash -{BALANCE.create_product_cost}. "
                "It enters the portfolio as a new product bet."
            ),
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.HIRE_EMPLOYEE:
        if (
            context.hire_full_name is None
            or context.hire_role is None
            or context.hire_seniority is None
        ):
            raise ValueError("Hiring requires a name, role, and seniority.")

        employee = create_employee(
            full_name=context.hire_full_name,
            role=context.hire_role,
            seniority=context.hire_seniority,
            specialization=context.hire_specialization,
            existing_employees=next_state.employees,
            trait=context.hire_trait or CandidateTrait.STEADY_OPERATOR,
        )
        next_state.employees.append(employee)
        update_succession_risk(next_state.employees)
        team_condition = calculate_team_condition(next_state.employees)
        logger.debug("Hired employee %s.", employee.full_name)
        return ActionOutcome(
            state=next_state,
            message=(
                f"Hired {employee.full_name} ({employee.role.value}, {employee.seniority.value}). "
                f"Salary burn is now {format_money(team_condition.total_salary_cost)} per turn."
            ),
        )

    if action is TurnAction.TRAIN_EMPLOYEE:
        employee = get_employee_by_id(next_state.employees, context.employee_id)
        summary = train_employee(next_state.company, employee)
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Trained employee %s.", employee.full_name)
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.PROMOTE_EMPLOYEE:
        employee = get_employee_by_id(next_state.employees, context.employee_id)
        summary = promote_employee(employee)
        logger.debug("Promoted employee %s.", employee.full_name)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.RUN_COMP_REVIEW:
        employee = get_employee_by_id(next_state.employees, context.employee_id)
        summary = run_comp_review(next_state.company, employee)
        logger.debug("Ran compensation review for %s.", employee.full_name)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.RUN_SUCCESSION_REVIEW:
        if context.employee_id is None:
            raise ValueError("Running a succession review requires choosing a manager.")
        summary = run_succession_review(
            next_state.company,
            next_state.employees,
            employee_id=context.employee_id,
        )
        logger.debug("Ran succession review for employee %s.", context.employee_id)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.SOURCE_CANDIDATES:
        summary = source_candidates(next_state)
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Sourced hiring candidates.")
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.SCREEN_CANDIDATE:
        summary = screen_candidate(next_state, context.hiring_candidate_id)
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Screened hiring candidate %s.", context.hiring_candidate_id)
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.INTERVIEW_CANDIDATE:
        summary = interview_candidate(next_state, context.hiring_candidate_id)
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Interviewed hiring candidate %s.", context.hiring_candidate_id)
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.MAKE_HIRING_OFFER:
        summary = make_hiring_offer(next_state, context.hiring_candidate_id)
        logger.debug("Made offer to hiring candidate %s.", context.hiring_candidate_id)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.SET_COMPANY_STRATEGY:
        if context.strategy is None:
            raise ValueError("Selecting a company strategy requires a strategy value.")

        summary = apply_set_company_strategy(next_state.company, context.strategy)
        logger.debug("Changed company strategy to %s.", context.strategy.value)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.SET_ROADMAP:
        if context.roadmap_focus is None:
            raise ValueError("Selecting a roadmap requires a roadmap focus.")

        next_state.roadmap_focus = context.roadmap_focus
        next_state.roadmap_set_turn = next_state.company.current_turn
        next_state.quarter_plan = build_quarter_plan(next_state)
        roadmap_profile = get_roadmap_profile(
            next_state.roadmap_focus,
            roadmap_set_turn=next_state.roadmap_set_turn,
            current_turn=next_state.company.current_turn,
        )
        logger.debug("Changed roadmap focus to %s.", context.roadmap_focus.value)
        return ActionOutcome(
            state=next_state,
            message=(f"Roadmap set to {context.roadmap_focus.value}. {roadmap_profile.summary}"),
        )

    if action is TurnAction.SET_BUDGET_STANCE:
        if context.budget_stance is None:
            raise ValueError("Selecting a budget stance requires a budget value.")

        next_state.quarter_plan = build_quarter_plan(
            next_state,
            budget_stance=context.budget_stance,
        )
        budget_profile = get_budget_profile(context.budget_stance)
        logger.debug("Changed budget stance to %s.", context.budget_stance.value)
        return ActionOutcome(
            state=next_state,
            message=(
                f"Budget stance set to {context.budget_stance.value}. {budget_profile.summary}"
            ),
        )

    if action is TurnAction.SET_FUNCTIONAL_BUDGET:
        if context.functional_budget_preset is None:
            raise ValueError("Selecting a functional budget requires choosing a preset.")

        budget_profile = apply_set_functional_budget(
            next_state,
            context.functional_budget_preset,
        )
        logger.debug(
            "Changed functional budget to %s.",
            context.functional_budget_preset.value,
        )
        return ActionOutcome(
            state=next_state,
            message=(
                f"Functional budget set to {context.functional_budget_preset.value}. "
                f"{budget_profile.summary}"
            ),
        )

    if action is TurnAction.SET_CAPITAL_PLAN:
        if context.capital_plan_mode is None or context.capital_source_preference is None:
            raise ValueError("Selecting a capital plan requires a mode and capital source.")
        summary = apply_set_capital_plan(
            next_state,
            context.capital_plan_mode,
            context.capital_source_preference,
        )
        logger.debug(
            "Changed capital plan to %s / %s.",
            context.capital_plan_mode.value,
            context.capital_source_preference.value,
        )
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.TAKE_LOAN:
        summary = apply_take_loan(
            next_state.company,
            next_state.finance,
            current_turn=next_state.company.current_turn,
        )
        next_state.funding_history.append(summary.history_entry)
        logger.debug("Took a company loan on turn %s.", next_state.company.current_turn)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.RAISE_ANGEL:
        summary = apply_raise_angel(
            next_state.company,
            next_state.finance,
            next_state.funding_history,
            current_turn=next_state.company.current_turn,
            reputation=next_state.company.reputation,
            total_users=get_total_users(next_state),
        )
        next_state.funding_history.append(summary.history_entry)
        logger.debug("Raised angel capital on turn %s.", next_state.company.current_turn)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.RAISE_VC:
        summary = apply_raise_vc(
            next_state.company,
            next_state.finance,
            next_state.funding_history,
            current_turn=next_state.company.current_turn,
            reputation=next_state.company.reputation,
            total_users=get_total_users(next_state),
        )
        next_state.funding_history.append(summary.history_entry)
        logger.debug("Raised venture capital on turn %s.", next_state.company.current_turn)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.REPAY_DEBT:
        summary = apply_repay_debt(
            next_state.company,
            next_state.finance,
            current_turn=next_state.company.current_turn,
        )
        next_state.funding_history.append(summary.history_entry)
        logger.debug("Repaid debt on turn %s.", next_state.company.current_turn)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.FIRE_EMPLOYEE:
        employee = get_employee_by_id(next_state.employees, context.employee_id)
        next_state.employees = [
            team_member for team_member in next_state.employees if team_member.id != employee.id
        ]
        clear_manager_links(next_state.employees, employee.id)
        sanitize_management_links(next_state.employees)
        update_succession_risk(next_state.employees)
        team_condition = calculate_team_condition(next_state.employees)
        logger.debug("Fired employee %s.", employee.full_name)
        return ActionOutcome(
            state=next_state,
            message=(
                f"Fired {employee.full_name}. "
                f"Salary burn is now {format_money(team_condition.total_salary_cost)} per turn."
            ),
        )

    if action is TurnAction.ASSIGN_EMPLOYEE:
        employee = get_employee_by_id(next_state.employees, context.employee_id)
        product = get_target_product(next_state, context.target_product_id)
        summary = assign_employee(employee, product.id)
        logger.debug("Assigned employee %s to %s.", employee.full_name, product.name)
        return ActionOutcome(
            state=next_state,
            message=f"{summary.message} {employee.full_name} -> {product.name}.",
        )

    if action is TurnAction.ASSIGN_MANAGER:
        if context.employee_id is None or context.manager_id is None:
            raise ValueError("Assigning a manager requires choosing a report and a manager.")
        summary = assign_manager(
            next_state.employees,
            report_id=context.employee_id,
            manager_id=context.manager_id,
        )
        update_succession_risk(next_state.employees)
        logger.debug(
            "Assigned manager %s to employee %s.",
            context.manager_id,
            context.employee_id,
        )
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.CLEAR_MANAGER:
        if context.employee_id is None:
            raise ValueError("Clearing a manager requires choosing an employee.")
        summary = clear_manager_assignment(next_state.employees, report_id=context.employee_id)
        update_succession_risk(next_state.employees)
        logger.debug("Cleared manager assignment for employee %s.", context.employee_id)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.APPOINT_TEAM_LEAD:
        if context.employee_id is None:
            raise ValueError("Appointing a team lead requires choosing an employee.")
        summary = appoint_team_lead(next_state.employees, context.employee_id)
        update_succession_risk(next_state.employees)
        logger.debug("Appointed team lead for employee %s.", context.employee_id)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.UNASSIGN_EMPLOYEE:
        employee = get_employee_by_id(next_state.employees, context.employee_id)
        summary = unassign_employee(employee)
        logger.debug("Unassigned employee %s.", employee.full_name)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.REST_TEAM:
        summary = apply_rest_team(next_state.employees)
        logger.debug("Rested the team.")
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.REORG_TEAM:
        if next_state.company.cash_on_hand < BALANCE.management_reorg_cost:
            raise ValueError("Not enough cash to run an org reorg this turn.")
        summary = run_org_reorg(next_state.employees)
        next_state.company.cash_on_hand = quantize_money(
            next_state.company.cash_on_hand - BALANCE.management_reorg_cost
        )
        for employee in next_state.employees:
            employee.attrition_risk = clamp_int(
                employee.attrition_risk - BALANCE.management_reorg_attrition_relief
            )
            if employee.manager_id is not None:
                employee.energy = clamp_int(employee.energy + BALANCE.management_reorg_energy_gain)
            employee.morale = clamp_int(employee.morale - BALANCE.management_reorg_morale_penalty)
        update_succession_risk(next_state.employees)
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Ran org reorg.")
        return ActionOutcome(
            state=next_state,
            message=f"{summary.message} Cash -{BALANCE.management_reorg_cost}.",
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.INVEST_IN_CUSTOMER_SUCCESS:
        product = get_target_product(next_state, context.target_product_id)
        summary = invest_in_customer_success(next_state, product.id)
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Invested in customer success for %s.", product.name)
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.RUN_RETENTION_PLAY:
        account = get_customer_account_by_id(
            next_state.customer_accounts,
            context.customer_account_id,
        )
        summary = run_retention_play(next_state, account.id)
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Ran retention play for %s.", account.name)
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.MAKE_RENEWAL_OFFER:
        account = get_customer_account_by_id(
            next_state.customer_accounts,
            context.customer_account_id,
        )
        summary = make_renewal_offer(
            next_state,
            account.id,
            offer_type=context.renewal_offer_type or RenewalOfferType.LIGHT_DISCOUNT,
        )
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Made renewal offer for %s.", account.name)
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.RUN_WIN_BACK_PLAY:
        account = get_customer_account_by_id(
            next_state.customer_accounts,
            context.customer_account_id,
        )
        summary = run_win_back_play(next_state, account.id)
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Ran win-back play for %s.", account.name)
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.ROUTE_SUPPORT_ESCALATION:
        account = get_customer_account_by_id(
            next_state.customer_accounts,
            context.customer_account_id,
        )
        summary = route_support_escalation(next_state, account.id)
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Routed support escalation for %s.", account.name)
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.CREATE_PARTNERSHIP:
        if context.target_product_id is None or context.partner_channel is None:
            raise ValueError("Creating a partnership requires selecting a product and channel.")
        summary = create_partnership(
            next_state,
            context.target_product_id,
            context.partner_channel,
        )
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug(
            "Created %s partnership for product %s.",
            context.partner_channel.value,
            context.target_product_id,
        )
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.INVEST_IN_PARTNER_ENABLEMENT:
        if context.partnership_id is None:
            raise ValueError("Investing in partner enablement requires selecting a partnership.")
        partnership = get_partnership_by_id(next_state.partnerships, context.partnership_id)
        summary = invest_in_partner_enablement(next_state, partnership.id)
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Invested in partner enablement for %s.", partnership.name)
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.RENEGOTIATE_PARTNERSHIP:
        if context.partnership_id is None:
            raise ValueError("Renegotiating a partnership requires selecting a partnership.")
        partnership = get_partnership_by_id(next_state.partnerships, context.partnership_id)
        summary = renegotiate_partnership(next_state, partnership.id)
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Renegotiated partnership %s.", partnership.name)
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.REACTIVATE_PARTNERSHIP:
        if context.partnership_id is None:
            raise ValueError("Reactivating a partnership requires selecting a partnership.")
        partnership = get_partnership_by_id(next_state.partnerships, context.partnership_id)
        summary = reactivate_partnership(next_state, partnership.id)
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Ran channel recovery for partnership %s.", partnership.name)
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.SET_SUPPORT_LANE_FOCUS:
        if context.support_lane_focus is None:
            raise ValueError("A support lane focus must be selected.")
        summary = set_support_lane_focus(next_state, context.support_lane_focus)
        logger.debug("Set support lane focus to %s.", context.support_lane_focus.value)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.TRIAGE_SUPPORT_BACKLOG:
        summary = triage_support_backlog(next_state)
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Triaged support backlog.")
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.UPGRADE_SUPPORT_PROGRAM:
        if context.support_investment_focus is None:
            raise ValueError("Upgrading support requires choosing an investment focus.")
        summary = upgrade_support_program(next_state, context.support_investment_focus)
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug(
            "Upgraded support program with focus %s.",
            context.support_investment_focus.value,
        )
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.INVEST_IN_SUPPORT_STAFFING:
        summary = invest_in_support_staffing(next_state)
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Expanded support staffing.")
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.PLAN_RELEASE:
        if context.release_type is None:
            raise ValueError("Planning a release requires choosing a release type.")
        product = get_target_product(next_state, context.target_product_id)
        summary = plan_product_release(next_state, product, context.release_type)
        logger.debug("Planned %s release for %s.", context.release_type.value, product.name)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.WORK_RELEASE:
        if context.release_id is None:
            raise ValueError("Working a release requires choosing a release plan.")
        functional_budget_profile = get_functional_budget_profile(next_state.functional_budget)
        summary = work_product_release(
            next_state,
            context.release_id,
            engineering_bonus=functional_budget_profile.engineering_bonus,
        )
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Worked release %s.", context.release_id)
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.CREATE_SALES_DEAL:
        product = get_target_product(next_state, context.target_product_id)
        functional_budget_profile = get_functional_budget_profile(next_state.functional_budget)
        summary = create_sales_deal(
            next_state,
            product,
            marketing_bonus=functional_budget_profile.marketing_bonus,
        )
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Created sales deal for %s.", product.name)
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.ADVANCE_SALES_DEAL:
        if context.sales_deal_id is None:
            raise ValueError("Advancing sales requires choosing a deal.")
        functional_budget_profile = get_functional_budget_profile(next_state.functional_budget)
        summary = advance_sales_deal(
            next_state,
            context.sales_deal_id,
            marketing_bonus=functional_budget_profile.marketing_bonus,
        )
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Advanced sales deal %s.", context.sales_deal_id)
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.START_ROADMAP_PROJECT:
        if context.roadmap_project_type is None:
            raise ValueError("Starting a roadmap project requires choosing a project type.")
        summary = start_roadmap_project(
            next_state,
            context.roadmap_project_type,
            context.target_product_id,
        )
        logger.debug("Started roadmap project %s.", context.roadmap_project_type.value)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.WORK_ROADMAP_PROJECT:
        if context.roadmap_project_id is None:
            raise ValueError("Working a roadmap project requires choosing a project.")
        summary = work_roadmap_project(next_state, context.roadmap_project_id)
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Worked roadmap project %s.", context.roadmap_project_id)
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.WAIT:
        logger.debug("Applied wait action.")
        return ActionOutcome(
            state=next_state,
            message="You held position and let the company breathe for a turn.",
        )

    product = get_target_product(next_state, context.target_product_id)
    functional_budget_profile = get_functional_budget_profile(next_state.functional_budget)
    team_modifier = _apply_functional_budget_to_team_modifier(
        calculate_product_team_modifier(next_state.employees, product.id),
        engineering_bonus=functional_budget_profile.engineering_bonus,
        marketing_bonus=functional_budget_profile.marketing_bonus,
    )
    strategy_profile = get_strategy_profile(next_state.company.strategy)
    roadmap_profile = get_roadmap_profile(
        next_state.roadmap_focus,
        roadmap_set_turn=next_state.roadmap_set_turn,
        current_turn=next_state.company.current_turn,
    )
    budget_profile = get_budget_profile(next_state.quarter_plan.budget_stance)

    if action is TurnAction.IMPROVE_QUALITY:
        summary = apply_improve_quality(
            product,
            team_modifier,
            strategy_profile,
            roadmap_profile,
        )
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.ADD_FEATURE:
        summary = apply_add_feature(
            product,
            team_modifier,
            strategy_profile,
            roadmap_profile,
        )
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.REDUCE_TECHNICAL_DEBT:
        summary = apply_reduce_technical_debt(
            product,
            team_modifier,
            strategy_profile,
            roadmap_profile,
        )
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.MARKET_PRODUCT:
        summary = apply_marketing(
            next_state.company,
            product,
            team_modifier,
            roadmap_profile,
            budget_profile,
        )
        next_state.company.game_over = is_game_over(next_state.company)
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.ADJUST_PRICING:
        if context.pricing_tier is None:
            raise ValueError("Adjusting pricing requires selecting a pricing tier.")

        summary = apply_adjust_pricing(product, context.pricing_tier)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.RUN_PRICE_INCREASE:
        summary = apply_run_price_increase(product, next_state.customer_accounts)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.EXPAND_PACKAGE_CATALOG:
        summary = apply_expand_package_catalog(
            next_state.company,
            product,
            next_state.customer_accounts,
        )
        next_state.company.game_over = is_game_over(next_state.company)
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.EXPAND_ADD_ON_CATALOG:
        summary = apply_expand_add_on_catalog(
            next_state.company,
            product,
            next_state.customer_accounts,
        )
        next_state.company.game_over = is_game_over(next_state.company)
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.RUN_ADD_ON_CAMPAIGN:
        summary = apply_run_add_on_campaign(product, next_state.customer_accounts)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.RUN_PACKAGE_MIGRATION:
        summary = apply_run_package_migration(product, next_state.customer_accounts)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.SET_PACKAGING_STRATEGY:
        if context.packaging_strategy is None:
            raise ValueError("Selecting packaging requires choosing a packaging strategy.")

        summary = apply_set_packaging_strategy(product, context.packaging_strategy)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.SET_TARGET_SEGMENT:
        if context.target_segment is None:
            raise ValueError("Selecting a segment requires choosing a target segment.")
        if product.target_segment is context.target_segment:
            raise ValueError(f"{product.name} is already targeting {context.target_segment.value}.")

        previous_segment = product.target_segment
        product.target_segment = context.target_segment
        product.market_fit = clamp_int(
            product.market_fit
            + (1 if product.pricing_tier is PricingTier.PREMIUM else 0)
            - (1 if context.target_segment is MarketSegment.ENTERPRISE else 0)
        )
        return ActionOutcome(
            state=next_state,
            message=(
                f"{product.name} moved from {previous_segment.value} to "
                f"{context.target_segment.value}. Market fit re-centered around the new customer."
            ),
        )

    if action is TurnAction.SUNSET_PRODUCT:
        summary = apply_sunset_product(product)
        unassigned_count = unassign_employees_from_product(next_state.employees, product.id)
        extra_note = ""
        if unassigned_count > 0:
            extra_note = f" {unassigned_count} team member(s) were moved to unassigned."
        return ActionOutcome(
            state=next_state,
            message=f"{summary.message}{extra_note}",
        )

    raise ValueError(f"Unsupported action: {action.value}")


def resolve_turn(state: GameState, rng: RandomLike) -> TurnResolution:
    """Run the end-of-turn simulation tick across the portfolio and team."""

    resolved_turn = state.company.current_turn
    next_state = state.model_copy(deep=True)
    sanitize_management_links(next_state.employees)
    product_summaries: list[ProductTurnSummary] = []
    unlocked_milestones: list[MilestoneEntry] = []
    company_strategy_profile = get_strategy_profile(next_state.company.strategy)
    budget_profile = get_budget_profile(next_state.quarter_plan.budget_stance)
    active_roadmap_focus = get_effective_roadmap_focus(
        next_state.roadmap_focus,
        roadmap_set_turn=next_state.roadmap_set_turn,
        current_turn=resolved_turn,
    )
    roadmap_profile = get_roadmap_profile(
        next_state.roadmap_focus,
        roadmap_set_turn=next_state.roadmap_set_turn,
        current_turn=resolved_turn,
    )
    roadmap_due = is_roadmap_due(
        roadmap_set_turn=next_state.roadmap_set_turn,
        current_turn=resolved_turn,
    )
    difficulty_profile = get_difficulty_profile(next_state.difficulty_mode)
    functional_budget_profile = get_functional_budget_profile(next_state.functional_budget)
    scale_pressure = calculate_company_scale_pressure(
        next_state.products,
        headcount=len(next_state.employees),
        current_turn=resolved_turn,
    )
    baseline_operating_cost = quantize_money(
        BALANCE.base_operating_cost
        + company_strategy_profile.operating_cost_modifier
        + budget_profile.operating_cost_modifier
        + roadmap_profile.operating_cost_modifier
    )
    baseline_operating_cost = quantize_money(
        baseline_operating_cost * difficulty_profile.operating_cost_multiplier
    )

    total_revenue = calculate_total_revenue(next_state.products)
    total_product_operating_cost = calculate_total_product_operating_cost(
        next_state.products,
        current_turn=resolved_turn,
        roadmap_focus=next_state.roadmap_focus,
        roadmap_set_turn=next_state.roadmap_set_turn,
        headcount=len(next_state.employees),
        difficulty_mode=next_state.difficulty_mode,
    )
    total_salary_cost = calculate_total_salary_cost(next_state.employees)
    total_operating_cost = calculate_total_operating_cost(
        next_state.company,
        next_state.products,
        next_state.employees,
        finance=next_state.finance,
        budget_stance=next_state.quarter_plan.budget_stance,
        roadmap_focus=next_state.roadmap_focus,
        roadmap_set_turn=next_state.roadmap_set_turn,
        difficulty_mode=next_state.difficulty_mode,
    )
    total_finance_cost = total_operating_cost - (
        baseline_operating_cost + total_product_operating_cost + total_salary_cost
    )

    for product in next_state.products:
        revenue = calculate_product_revenue(product)
        operating_cost = calculate_product_operating_cost(
            product,
            current_turn=resolved_turn,
            roadmap_focus=next_state.roadmap_focus,
            roadmap_set_turn=next_state.roadmap_set_turn,
            portfolio_products=next_state.products,
            headcount=len(next_state.employees),
            difficulty_mode=next_state.difficulty_mode,
        )
        team_modifier = _apply_functional_budget_to_team_modifier(
            calculate_product_team_modifier(next_state.employees, product.id),
            engineering_bonus=functional_budget_profile.engineering_bonus,
            marketing_bonus=functional_budget_profile.marketing_bonus,
        )
        growth_result = resolve_growth(
            next_state.company,
            product,
            rng,
            team_modifier,
            market_cycle=next_state.market_cycle,
            competitors=next_state.competitors,
            roadmap_focus=next_state.roadmap_focus,
            roadmap_set_turn=next_state.roadmap_set_turn,
            portfolio_products=next_state.products,
            headcount=len(next_state.employees),
            difficulty_mode=next_state.difficulty_mode,
        )
        product.user_count = max(0, product.user_count + growth_result.net_user_delta)

        drift: ProductDrift = apply_end_of_turn_progression(
            product,
            rng,
            team_modifier,
            company_strategy_profile,
            roadmap_profile,
        )
        competitor_pressure = calculate_competitor_pressure(
            product,
            next_state.competitors,
            market_cycle=next_state.market_cycle,
            current_turn=resolved_turn,
            roadmap_focus=next_state.roadmap_focus,
            roadmap_set_turn=next_state.roadmap_set_turn,
        )

        product_summaries.append(
            ProductTurnSummary(
                product_id=product.id,
                product_name=product.name,
                lifecycle_stage=product.lifecycle_stage,
                revenue=revenue,
                operating_cost=operating_cost,
                acquired_users=growth_result.acquired_users,
                churned_users=growth_result.churned_users,
                net_user_delta=growth_result.net_user_delta,
                quality_delta=drift.quality_delta,
                bug_delta=drift.bug_delta,
                target_segment=product.target_segment,
                competitor_pressure=competitor_pressure,
            )
        )

    reputation_delta = calculate_company_reputation_delta(
        next_state.company,
        next_state.products,
        next_state.employees,
        rng,
        roadmap_focus=next_state.roadmap_focus,
        roadmap_set_turn=next_state.roadmap_set_turn,
    )
    next_state.company.reputation = clamp_int(next_state.company.reputation + reputation_delta)
    customer_summary = apply_end_of_turn_customers(
        next_state.customer_accounts,
        next_state.products,
        current_turn=resolved_turn,
        customer_success_bonus=functional_budget_profile.customer_success_bonus,
        support_program=next_state.support_program,
    )
    total_revenue = quantize_money(total_revenue + customer_summary.account_revenue)
    partnership_summary = apply_end_of_turn_partnerships(next_state)
    total_revenue = quantize_money(total_revenue + partnership_summary.sourced_revenue)
    if partnership_summary.reputation_delta != 0:
        next_state.company.reputation = clamp_int(
            next_state.company.reputation + partnership_summary.reputation_delta
        )
        reputation_delta += partnership_summary.reputation_delta
    support_summary = apply_end_of_turn_support_program(
        next_state,
        customer_success_bonus=functional_budget_profile.customer_success_bonus,
    )
    if support_summary.reputation_delta != 0:
        next_state.company.reputation = clamp_int(
            next_state.company.reputation + support_summary.reputation_delta
        )
        reputation_delta += support_summary.reputation_delta
    if support_summary.morale_penalty > 0:
        for employee in next_state.employees:
            employee.morale = clamp_int(employee.morale - support_summary.morale_penalty)

    operations_summary = apply_end_of_turn_operations(
        next_state,
        current_turn=resolved_turn,
    )
    total_operations_cost = quantize_money(
        operations_summary.added_cost
        + support_summary.service_cost
        + partnership_summary.service_cost
    )
    late_game_summary = apply_end_of_turn_late_game(
        next_state.products,
        current_turn=resolved_turn,
        headcount=len(next_state.employees),
    )
    late_game_user_loss = {
        product_risk.product_id: product_risk.user_loss
        for product_risk in late_game_summary.product_risks
        if product_risk.user_loss > 0
    }
    if late_game_user_loss:
        product_summaries = [
            replace(
                summary,
                churned_users=(
                    summary.churned_users + late_game_user_loss.get(summary.product_id, 0)
                ),
                net_user_delta=(
                    summary.net_user_delta - late_game_user_loss.get(summary.product_id, 0)
                ),
            )
            for summary in product_summaries
        ]
    total_late_game_cost = late_game_summary.added_cost
    next_state.company.reputation = clamp_int(
        next_state.company.reputation + late_game_summary.reputation_delta
    )
    total_operating_cost = quantize_money(total_operating_cost + total_operations_cost)
    total_operating_cost = quantize_money(total_operating_cost + total_late_game_cost)
    net_cash_flow = quantize_money(total_revenue - total_operating_cost)
    reputation_delta += operations_summary.reputation_delta + late_game_summary.reputation_delta

    next_state.company.cash_on_hand = quantize_money(
        next_state.company.cash_on_hand + net_cash_flow
    )
    finance_summary = apply_end_of_turn_finance_drift(
        next_state.finance,
        next_state.company,
        capital_plan=next_state.capital_plan,
        net_cash_flow=net_cash_flow,
        turn_history=next_state.turn_history,
        technical_debt_load=sum(
            product.technical_debt for product in next_state.products if product.is_active
        ),
        active_channels=sum(
            1 for partnership in next_state.partnerships if partnership.status.value != "paused"
        ),
        support_backlog=next_state.support_program.backlog_queue,
    )
    next_state.finance.board_confidence = clamp_int(
        next_state.finance.board_confidence + functional_budget_profile.board_confidence_bonus
    )
    governance_summary = apply_end_of_turn_governance(
        next_state,
        resolved_turn=resolved_turn,
        total_revenue=total_revenue,
        net_cash_flow=net_cash_flow,
        customer_summary=customer_summary,
        operations_summary=operations_summary,
    )

    team_condition = apply_end_of_turn_team_drift(
        next_state.employees,
        next_state.products,
        net_cash_flow,
        next_state.company.strategy,
        budget_burnout_modifier=(
            budget_profile.burnout_modifier
            + operations_summary.team_energy_penalty
            - functional_budget_profile.burnout_relief
        ),
        coordination_burnout_modifier=scale_pressure.coordination_drag
        + late_game_summary.burnout_modifier
        + difficulty_profile.burnout_modifier,
    )
    progression_summary = apply_end_of_turn_employee_progression(
        next_state.employees,
        net_cash_flow=net_cash_flow,
        burnout_relief=functional_budget_profile.burnout_relief,
        rng=rng,
    )
    update_succession_risk(next_state.employees)
    sanitize_management_links(next_state.employees)
    if progression_summary.resigned_employees:
        next_state.company.reputation = clamp_int(next_state.company.reputation - 1)
        next_state.finance.board_confidence = clamp_int(next_state.finance.board_confidence - 1)
        reputation_delta -= 1

    age_sales_pipeline(next_state)
    age_hiring_candidates(next_state)
    event_outcome: EventTurnOutcome = resolve_turn_event(next_state, rng)
    next_state = event_outcome.state
    team_condition = calculate_team_condition(next_state.employees)
    unlocked_milestones = resolve_new_milestones(next_state, unlocked_turn=resolved_turn)
    if unlocked_milestones:
        team_condition = calculate_team_condition(next_state.employees)

    previous_competitors = [
        competitor.model_copy(deep=True) for competitor in next_state.competitors
    ]
    advance_competitors(
        next_state.competitors,
        rng,
        market_cycle=next_state.market_cycle,
        portfolio_products=next_state.products,
    )
    record_competitor_intel(
        next_state,
        previous_competitors,
        current_turn=resolved_turn,
    )
    (
        next_state.market_cycle,
        next_state.market_cycle_turns_remaining,
        market_cycle_changed,
    ) = advance_market_cycle(
        next_state.market_cycle,
        next_state.market_cycle_turns_remaining,
        rng,
    )

    append_turn_history(
        next_state,
        resolved_turn=resolved_turn,
        total_revenue=total_revenue,
        total_operating_cost=total_operating_cost,
        net_cash_flow=net_cash_flow,
        roadmap_focus=active_roadmap_focus,
    )
    run_score = calculate_run_score(next_state)
    victory_reason = check_victory(next_state)
    campaign_goal_progress = evaluate_campaign_goal(next_state)
    next_state.victory_achieved = victory_reason is not None
    next_state.victory_reason = victory_reason
    if next_state.victory_achieved:
        apply_exit_outcome(next_state)
    next_state.company.game_over = is_game_over(next_state.company)
    if not next_state.company.game_over and not next_state.victory_achieved:
        next_state.company.current_turn += 1
        next_state.action_points_remaining = BALANCE.actions_per_turn
    quarter_plan_due = is_quarter_plan_due(next_state)

    narrative = build_turn_narrative(
        net_cash_flow=net_cash_flow,
        reputation_delta=reputation_delta,
        product_summaries=product_summaries,
        team_condition=team_condition,
        finance_summary=finance_summary,
        governance_summary=governance_summary,
        competitors=next_state.competitors,
        game_over=next_state.company.game_over,
        quarter_plan_due=quarter_plan_due,
        market_cycle=next_state.market_cycle,
        market_cycle_changed=market_cycle_changed,
        campaign_goal_progress=campaign_goal_progress,
        scale_pressure_summary=scale_pressure.summary,
        operations_summary=operations_summary.summary,
        partnership_summary=partnership_summary.summary,
        late_game_summary=late_game_summary.summary,
        victory_reason=victory_reason,
        roadmap_due=roadmap_due,
        promotion_ready_count=progression_summary.promotion_ready_count,
        high_attrition_risk_count=progression_summary.high_attrition_risk_count,
        underperforming_count=progression_summary.underperforming_count,
        resigned_employees=progression_summary.resigned_employees,
    )
    logger.debug("Resolved turn %s.", resolved_turn)

    return TurnResolution(
        state=next_state,
        resolved_turn=resolved_turn,
        total_revenue=total_revenue,
        baseline_operating_cost=baseline_operating_cost,
        total_product_operating_cost=total_product_operating_cost,
        total_operations_cost=total_operations_cost,
        total_late_game_cost=total_late_game_cost,
        total_salary_cost=total_salary_cost,
        total_finance_cost=total_finance_cost,
        total_operating_cost=total_operating_cost,
        net_cash_flow=net_cash_flow,
        customer_summary=customer_summary,
        reputation_delta=reputation_delta,
        product_summaries=product_summaries,
        team_condition=team_condition,
        finance_summary=finance_summary,
        governance_summary=governance_summary,
        pending_event=event_outcome.pending_event,
        event_history_entry=event_outcome.history_entry,
        unlocked_milestones=unlocked_milestones,
        run_score=run_score,
        operations_summary=operations_summary,
        late_game_summary=late_game_summary,
        roadmap_due=roadmap_due,
        roadmap_focus=active_roadmap_focus,
        quarter_plan_due=quarter_plan_due,
        market_cycle=next_state.market_cycle,
        market_cycle_changed=market_cycle_changed,
        campaign_goal_progress=campaign_goal_progress,
        scale_pressure_summary=scale_pressure.summary,
        victory_reason=victory_reason,
        narrative=narrative,
    )


def get_product_choices(state: GameState, active_only: bool = True) -> list[Product]:
    """Return products available for CLI target selection."""

    if active_only:
        return [product for product in state.products if product.is_active]
    return list(state.products)


def get_employee_choices(
    state: GameState,
    assigned_only: bool | None = None,
) -> list[Employee]:
    """Return employees available for CLI target selection."""

    if assigned_only is True:
        return [
            employee for employee in state.employees if employee.assigned_product_id is not None
        ]
    if assigned_only is False:
        return [employee for employee in state.employees if employee.assigned_product_id is None]
    return list(state.employees)


def get_customer_choices(
    state: GameState,
    *,
    at_risk_only: bool = False,
    churned_only: bool = False,
):
    """Return customer accounts available for CLI target selection."""

    if churned_only:
        return [account for account in state.customer_accounts if account.status.value == "churned"]
    accounts = [account for account in state.customer_accounts if account.status.value != "churned"]
    if at_risk_only:
        return [account for account in accounts if account.status.value == "at_risk"]
    return accounts


def get_partnership_choices(
    state: GameState,
    *,
    actionable_only: bool = False,
):
    """Return partnerships available for CLI target selection."""

    if actionable_only:
        return [
            partnership
            for partnership in state.partnerships
            if partnership.status.value != "paused"
        ]
    return list(state.partnerships)


def get_target_product(state: GameState, product_id: UUID | None) -> Product:
    """Resolve a target product from the current state."""

    if product_id is None:
        raise ValueError("This action requires selecting a product.")

    for product in state.products:
        if product.id == product_id:
            if not product.is_active:
                raise ValueError("That product has already been sunset.")
            return product

    raise ValueError("Selected product was not found.")


def get_total_users(state: GameState) -> int:
    """Return active users across all active products."""

    return sum(product.user_count for product in state.products if product.is_active)


def build_turn_narrative(
    net_cash_flow: Decimal,
    reputation_delta: int,
    product_summaries: list[ProductTurnSummary],
    team_condition: TeamCondition,
    finance_summary: FinanceTurnSummary,
    governance_summary: GovernanceSummary,
    competitors: list[Competitor],
    game_over: bool,
    quarter_plan_due: bool,
    market_cycle: MarketCycle,
    market_cycle_changed: bool,
    campaign_goal_progress: CampaignGoalProgress,
    scale_pressure_summary: str,
    operations_summary: str,
    partnership_summary: str,
    late_game_summary: str,
    victory_reason: str | None,
    roadmap_due: bool,
    promotion_ready_count: int,
    high_attrition_risk_count: int,
    underperforming_count: int,
    resigned_employees: tuple[str, ...],
) -> str:
    """Generate a concise story beat for the turn summary."""

    if game_over:
        return "The company ran out of cash. Payroll and product burn outpaced the business."
    if victory_reason is not None:
        return victory_reason
    if campaign_goal_progress.completed:
        return f"Campaign goal complete: {campaign_goal_progress.title}."
    if resigned_employees:
        return (
            "Attrition turned real this turn: "
            + ", ".join(resigned_employees[:2])
            + " left the company."
        )
    if high_attrition_risk_count > 0:
        return "Attrition risk is rising. Team sustainability now needs active attention."
    if promotion_ready_count > 0:
        return "The team is maturing. Some people are ready for broader responsibility."
    if underperforming_count > 0:
        return "Some team output is softening. Performance now needs direct management."
    if market_cycle_changed:
        return (
            f"The market shifted to {market_cycle.value}. "
            "Re-check the portfolio before momentum drifts."
        )
    if (
        finance_summary.investor_pressure_delta > 0
        and finance_summary.total_finance_cost > ZERO_MONEY
    ):
        return (
            "Capital pressure increased. Finance burn reached "
            f"{format_money(finance_summary.total_finance_cost)} "
            "and investors will expect cleaner execution."
        )
    if governance_summary.board_warning_active:
        return governance_summary.summary
    if governance_summary.restructuring_pressure >= BALANCE.board_restructure_min_pressure:
        return "Board pressure is now pointing toward a reset, not just tighter execution."
    if partnership_summary != "No active partner contribution this turn.":
        return partnership_summary

    total_user_delta = sum(summary.net_user_delta for summary in product_summaries)
    declining_products = [summary for summary in product_summaries if summary.net_user_delta < 0]
    expanding_products = [summary for summary in product_summaries if summary.net_user_delta > 0]
    competitor_summary = summarize_competitor_moves(competitors)

    if team_condition.burned_out_count > 0 and net_cash_flow < ZERO_MONEY:
        return "Burnout is creeping in while the company is still burning cash."
    if operations_summary.startswith("Support and coordination"):
        return "Operational load is starting to spill into product execution."
    if late_game_summary.startswith("Renewal risk"):
        return "Late-game renewal pressure is starting to tax the portfolio."
    if late_game_summary.startswith("Maintenance burden"):
        return "Portfolio upkeep is starting to crowd out forward motion."
    if late_game_summary.startswith("Company coordination"):
        return "Team coordination and portfolio drag are now part of every decision."
    if declining_products and any(
        summary.competitor_pressure >= 8 for summary in declining_products
    ):
        return f"Rivals are pressing harder: {competitor_summary}."
    if team_condition.burned_out_count > 0 and scale_pressure_summary.startswith("Coordination"):
        return (
            "Scale is starting to drag on execution. Coordination load now needs active management."
        )
    if net_cash_flow > ZERO_MONEY and len(expanding_products) >= 2:
        return "The portfolio and team are compounding together."
    if declining_products and reputation_delta < 0:
        return "Weak products are dragging the brand down despite the team's effort."
    if roadmap_due:
        return "The quarter plan has gone stale. Pick a fresh roadmap before momentum drifts."
    if quarter_plan_due:
        return (
            "The quarter targets are stale. Reset the budget stance "
            "and plan before scaling further."
        )
    if total_user_delta > 0 and net_cash_flow > ZERO_MONEY:
        return "Your team is converting effort into growth and cash flow."
    if net_cash_flow < ZERO_MONEY:
        return "The company is still buying time. Payroll pressure is now part of the puzzle."
    if operations_summary != "Operational load is under control.":
        return operations_summary
    if late_game_summary != "Late-game pressure is under control.":
        return late_game_summary
    return scale_pressure_summary


def _apply_functional_budget_to_team_modifier(
    team_modifier,
    *,
    engineering_bonus: int,
    marketing_bonus: int,
):
    """Apply cross-functional budget priorities to one product team modifier."""

    return replace(
        team_modifier,
        build_speed_bonus=team_modifier.build_speed_bonus + engineering_bonus,
        stability_bonus=team_modifier.stability_bonus + engineering_bonus,
        debt_reduction_bonus=team_modifier.debt_reduction_bonus + engineering_bonus,
        market_fit_bonus=team_modifier.market_fit_bonus + max(0, engineering_bonus // 2),
        acquisition_bonus=team_modifier.acquisition_bonus + marketing_bonus,
        reputation_bonus=team_modifier.reputation_bonus + max(0, marketing_bonus),
    )
