"""Turn orchestration for the simulation loop."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from nexus_tech.config import DEFAULT_PRODUCT_TEMPLATE_ID, DEFAULT_SCENARIO_ID
from nexus_tech.domain.constants import ZERO_MONEY
from nexus_tech.domain.models import (
    CompanyStrategy,
    Employee,
    EmployeeRole,
    EventHistoryEntry,
    GameState,
    LifecycleStage,
    MarketSegment,
    MilestoneEntry,
    PendingEvent,
    PricingTier,
    Product,
    RoadmapFocus,
    Seniority,
    TurnAction,
)
from nexus_tech.domain.money import format_money, quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.economy import (
    calculate_product_operating_cost,
    calculate_product_revenue,
    calculate_total_operating_cost,
    calculate_total_product_operating_cost,
    calculate_total_revenue,
    calculate_total_salary_cost,
    is_game_over,
)
from nexus_tech.simulation.events import EventTurnOutcome, resolve_turn_event
from nexus_tech.simulation.growth import calculate_company_reputation_delta, resolve_growth
from nexus_tech.simulation.milestones import resolve_new_milestones
from nexus_tech.simulation.pricing import apply_adjust_pricing
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
from nexus_tech.simulation.scenarios import (
    create_game_state_from_scenario,
    create_product_from_template,
)
from nexus_tech.simulation.segments import calculate_competitor_pressure
from nexus_tech.simulation.strategy import apply_set_company_strategy, get_strategy_profile
from nexus_tech.simulation.support import clamp_int
from nexus_tech.simulation.team import (
    TeamCondition,
    apply_end_of_turn_team_drift,
    apply_rest_team,
    assign_employee,
    calculate_product_team_modifier,
    calculate_team_condition,
    create_employee,
    get_employee_by_id,
    unassign_employee,
    unassign_employees_from_product,
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
    strategy: CompanyStrategy | None = None
    pricing_tier: PricingTier | None = None
    target_segment: MarketSegment | None = None
    roadmap_focus: RoadmapFocus | None = None


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
    total_salary_cost: Decimal
    total_operating_cost: Decimal
    net_cash_flow: Decimal
    reputation_delta: int
    product_summaries: list[ProductTurnSummary]
    team_condition: TeamCondition
    pending_event: PendingEvent | None
    event_history_entry: EventHistoryEntry | None
    unlocked_milestones: list[MilestoneEntry]
    run_score: RunScore
    roadmap_due: bool
    roadmap_focus: RoadmapFocus
    victory_reason: str | None
    narrative: str


def create_new_game(
    company_name: str | None = None,
    product_name: str | None = None,
    *,
    scenario_id: str = DEFAULT_SCENARIO_ID,
) -> GameState:
    """Create the initial playable game state from a selected scenario."""

    return create_game_state_from_scenario(
        scenario_id,
        company_name=company_name,
        primary_product_name=product_name,
    )


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
        TurnAction.VIEW_REPORT,
    ):
        return ActionOutcome(
            state=state,
            message="Resolve the pending event before taking new actions.",
        )

    if action in (
        TurnAction.VIEW_STATUS,
        TurnAction.REVIEW_TEAM,
        TurnAction.VIEW_REPORT,
        TurnAction.END_TURN,
    ):
        if action is TurnAction.VIEW_STATUS:
            return ActionOutcome(state=state, message="Status refreshed.")
        if action is TurnAction.REVIEW_TEAM:
            return ActionOutcome(state=state, message="Team review refreshed.")
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
        )
        next_state.employees.append(employee)
        team_condition = calculate_team_condition(next_state.employees)
        logger.debug("Hired employee %s.", employee.full_name)
        return ActionOutcome(
            state=next_state,
            message=(
                f"Hired {employee.full_name} ({employee.role.value}, {employee.seniority.value}). "
                f"Salary burn is now {format_money(team_condition.total_salary_cost)} per turn."
            ),
        )

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

    if action is TurnAction.FIRE_EMPLOYEE:
        employee = get_employee_by_id(next_state.employees, context.employee_id)
        next_state.employees = [
            team_member for team_member in next_state.employees if team_member.id != employee.id
        ]
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

    if action is TurnAction.UNASSIGN_EMPLOYEE:
        employee = get_employee_by_id(next_state.employees, context.employee_id)
        summary = unassign_employee(employee)
        logger.debug("Unassigned employee %s.", employee.full_name)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.REST_TEAM:
        summary = apply_rest_team(next_state.employees)
        logger.debug("Rested the team.")
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.WAIT:
        logger.debug("Applied wait action.")
        return ActionOutcome(
            state=next_state,
            message="You held position and let the company breathe for a turn.",
        )

    product = get_target_product(next_state, context.target_product_id)
    team_modifier = calculate_product_team_modifier(next_state.employees, product.id)
    strategy_profile = get_strategy_profile(next_state.company.strategy)
    roadmap_profile = get_roadmap_profile(
        next_state.roadmap_focus,
        roadmap_set_turn=next_state.roadmap_set_turn,
        current_turn=next_state.company.current_turn,
    )

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
    product_summaries: list[ProductTurnSummary] = []
    unlocked_milestones: list[MilestoneEntry] = []
    company_strategy_profile = get_strategy_profile(next_state.company.strategy)
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
    baseline_operating_cost = quantize_money(
        BALANCE.base_operating_cost
        + company_strategy_profile.operating_cost_modifier
        + roadmap_profile.operating_cost_modifier
    )

    total_revenue = calculate_total_revenue(next_state.products)
    total_product_operating_cost = calculate_total_product_operating_cost(
        next_state.products,
        current_turn=resolved_turn,
        roadmap_focus=next_state.roadmap_focus,
        roadmap_set_turn=next_state.roadmap_set_turn,
    )
    total_salary_cost = calculate_total_salary_cost(next_state.employees)
    total_operating_cost = calculate_total_operating_cost(
        next_state.company,
        next_state.products,
        next_state.employees,
        roadmap_focus=next_state.roadmap_focus,
        roadmap_set_turn=next_state.roadmap_set_turn,
    )
    net_cash_flow = quantize_money(total_revenue - total_operating_cost)

    next_state.company.cash_on_hand = quantize_money(
        next_state.company.cash_on_hand + net_cash_flow
    )

    for product in next_state.products:
        revenue = calculate_product_revenue(product)
        operating_cost = calculate_product_operating_cost(
            product,
            current_turn=resolved_turn,
            roadmap_focus=next_state.roadmap_focus,
            roadmap_set_turn=next_state.roadmap_set_turn,
        )
        team_modifier = calculate_product_team_modifier(next_state.employees, product.id)
        growth_result = resolve_growth(
            next_state.company,
            product,
            rng,
            team_modifier,
            roadmap_focus=next_state.roadmap_focus,
            roadmap_set_turn=next_state.roadmap_set_turn,
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

    team_condition = apply_end_of_turn_team_drift(
        next_state.employees,
        next_state.products,
        net_cash_flow,
        next_state.company.strategy,
    )

    event_outcome: EventTurnOutcome = resolve_turn_event(next_state, rng)
    next_state = event_outcome.state
    team_condition = calculate_team_condition(next_state.employees)
    unlocked_milestones = resolve_new_milestones(next_state, unlocked_turn=resolved_turn)
    if unlocked_milestones:
        team_condition = calculate_team_condition(next_state.employees)

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
    next_state.victory_achieved = victory_reason is not None
    next_state.victory_reason = victory_reason
    next_state.company.game_over = is_game_over(next_state.company)
    if not next_state.company.game_over and not next_state.victory_achieved:
        next_state.company.current_turn += 1
        next_state.action_points_remaining = BALANCE.actions_per_turn

    narrative = build_turn_narrative(
        net_cash_flow=net_cash_flow,
        reputation_delta=reputation_delta,
        product_summaries=product_summaries,
        team_condition=team_condition,
        game_over=next_state.company.game_over,
        victory_reason=victory_reason,
        roadmap_due=roadmap_due,
    )
    logger.debug("Resolved turn %s.", resolved_turn)

    return TurnResolution(
        state=next_state,
        resolved_turn=resolved_turn,
        total_revenue=total_revenue,
        baseline_operating_cost=baseline_operating_cost,
        total_product_operating_cost=total_product_operating_cost,
        total_salary_cost=total_salary_cost,
        total_operating_cost=total_operating_cost,
        net_cash_flow=net_cash_flow,
        reputation_delta=reputation_delta,
        product_summaries=product_summaries,
        team_condition=team_condition,
        pending_event=event_outcome.pending_event,
        event_history_entry=event_outcome.history_entry,
        unlocked_milestones=unlocked_milestones,
        run_score=run_score,
        roadmap_due=roadmap_due,
        roadmap_focus=active_roadmap_focus,
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
    game_over: bool,
    victory_reason: str | None,
    roadmap_due: bool,
) -> str:
    """Generate a concise story beat for the turn summary."""

    if game_over:
        return "The company ran out of cash. Payroll and product burn outpaced the business."
    if victory_reason is not None:
        return victory_reason

    total_user_delta = sum(summary.net_user_delta for summary in product_summaries)
    declining_products = [summary for summary in product_summaries if summary.net_user_delta < 0]
    expanding_products = [summary for summary in product_summaries if summary.net_user_delta > 0]

    if team_condition.burned_out_count > 0 and net_cash_flow < ZERO_MONEY:
        return "Burnout is creeping in while the company is still burning cash."
    if net_cash_flow > ZERO_MONEY and len(expanding_products) >= 2:
        return "The portfolio and team are compounding together."
    if declining_products and reputation_delta < 0:
        return "Weak products are dragging the brand down despite the team's effort."
    if roadmap_due:
        return "The quarter plan has gone stale. Pick a fresh roadmap before momentum drifts."
    if total_user_delta > 0 and net_cash_flow > ZERO_MONEY:
        return "Your team is converting effort into growth and cash flow."
    if net_cash_flow < ZERO_MONEY:
        return "The company is still buying time. Payroll pressure is now part of the puzzle."
    return "The company held steady this turn."
