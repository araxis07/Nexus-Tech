"""Turn orchestration for Phase 2."""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import UUID

from nexus_tech.domain.models import Company, GameState, LifecycleStage, Product, TurnAction
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.economy import (
    calculate_product_operating_cost,
    calculate_product_revenue,
    calculate_total_operating_cost,
    calculate_total_product_operating_cost,
    calculate_total_revenue,
    is_game_over,
)
from nexus_tech.simulation.growth import calculate_company_reputation_delta, resolve_growth
from nexus_tech.simulation.product_progression import (
    ProductDrift,
    apply_add_feature,
    apply_end_of_turn_progression,
    apply_improve_quality,
    apply_marketing,
    apply_reduce_technical_debt,
    apply_sunset_product,
    create_product,
    infer_lifecycle_stage,
)
from nexus_tech.simulation.randomness import RandomLike

logger = logging.getLogger(__name__)


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


@dataclass(frozen=True)
class TurnResolution:
    """Summary of what happened when a turn was simulated."""

    state: GameState
    resolved_turn: int
    total_revenue: Decimal
    baseline_operating_cost: Decimal
    total_product_operating_cost: Decimal
    total_operating_cost: Decimal
    net_cash_flow: Decimal
    reputation_delta: int
    product_summaries: list[ProductTurnSummary]
    narrative: str


def create_new_game(company_name: str, product_name: str) -> GameState:
    """Create the initial playable game state."""

    company = Company(
        name=company_name,
        cash_on_hand=BALANCE.starting_cash,
        reputation=BALANCE.starting_reputation,
    )
    product = Product(
        name=product_name,
        lifecycle_stage=LifecycleStage.GROWTH,
        quality=BALANCE.starting_quality,
        bug_level=BALANCE.starting_bug_level,
        market_fit=BALANCE.starting_market_fit,
        technical_debt=BALANCE.starting_technical_debt,
        user_count=BALANCE.starting_users,
        revenue_per_user=BALANCE.starting_revenue_per_user,
        feature_count=BALANCE.starting_feature_count,
        maintenance_cost=BALANCE.starting_maintenance_cost,
        acquisition_rate=BALANCE.starting_acquisition_rate,
        churn_rate=BALANCE.starting_churn_rate,
    )
    product.lifecycle_stage = infer_lifecycle_stage(product)
    return GameState(
        company=company,
        products=[product],
        action_points_remaining=BALANCE.actions_per_turn,
    )


def apply_action(
    state: GameState,
    action: TurnAction,
    target_product_id: Optional[UUID] = None,
    new_product_name: Optional[str] = None,
) -> ActionOutcome:
    """Apply a player action without running the end-of-turn simulation."""

    if state.company.game_over:
        return ActionOutcome(
            state=state,
            message="The company has already shut down.",
            turn_should_end=True,
        )

    if action in (TurnAction.VIEW_STATUS, TurnAction.END_TURN):
        if action is TurnAction.VIEW_STATUS:
            return ActionOutcome(state=state, message="Status refreshed.")
        return ActionOutcome(state=state, message="Ending turn.", turn_should_end=True)

    if state.action_points_remaining <= 0:
        return ActionOutcome(
            state=state,
            message="No action points remaining. View status or end the turn.",
        )

    next_state = state.model_copy(deep=True)
    next_state.action_points_remaining -= 1

    if action is TurnAction.CREATE_PRODUCT:
        if new_product_name is None:
            raise ValueError("A name is required to create a product.")
        if next_state.company.cash_on_hand < BALANCE.create_product_cost:
            raise ValueError("Not enough cash to create a new product.")

        product = create_product(new_product_name, next_state.products)
        next_state.company.cash_on_hand = quantize_money(
            next_state.company.cash_on_hand - BALANCE.create_product_cost
        )
        next_state.products.append(product)
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Created product %s.", product.name)
        return ActionOutcome(
            state=next_state,
            message=(
                f"Created {product.name}. Cash -{BALANCE.create_product_cost}. "
                "It enters the portfolio as a prototype."
            ),
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.WAIT:
        logger.debug("Applied wait action.")
        return ActionOutcome(
            state=next_state,
            message="You held position and let the portfolio breathe for a turn.",
        )

    product = get_target_product(next_state, target_product_id)

    if action is TurnAction.IMPROVE_QUALITY:
        summary = apply_improve_quality(product)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.ADD_FEATURE:
        summary = apply_add_feature(product)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.REDUCE_TECHNICAL_DEBT:
        summary = apply_reduce_technical_debt(product)
        return ActionOutcome(state=next_state, message=summary.message)

    if action is TurnAction.MARKET_PRODUCT:
        summary = apply_marketing(next_state.company, product)
        next_state.company.game_over = is_game_over(next_state.company)
        return ActionOutcome(
            state=next_state,
            message=summary.message,
            turn_should_end=next_state.company.game_over,
        )

    if action is TurnAction.SUNSET_PRODUCT:
        summary = apply_sunset_product(product)
        return ActionOutcome(state=next_state, message=summary.message)

    raise ValueError(f"Unsupported action: {action.value}")


def resolve_turn(state: GameState, rng: RandomLike) -> TurnResolution:
    """Run the end-of-turn simulation tick across the portfolio."""

    resolved_turn = state.company.current_turn
    next_state = state.model_copy(deep=True)
    product_summaries: list[ProductTurnSummary] = []

    total_revenue = calculate_total_revenue(next_state.products)
    total_product_operating_cost = calculate_total_product_operating_cost(next_state.products)
    total_operating_cost = calculate_total_operating_cost(next_state.products)
    net_cash_flow = quantize_money(total_revenue - total_operating_cost)

    next_state.company.cash_on_hand = quantize_money(
        next_state.company.cash_on_hand + net_cash_flow
    )

    for product in next_state.products:
        revenue = calculate_product_revenue(product)
        operating_cost = calculate_product_operating_cost(product)

        growth_result = resolve_growth(next_state.company, product, rng)
        product.user_count = max(0, product.user_count + growth_result.net_user_delta)

        drift: ProductDrift = apply_end_of_turn_progression(product, rng)

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
            )
        )

    reputation_delta = calculate_company_reputation_delta(
        next_state.company,
        next_state.products,
        rng,
    )
    next_state.company.reputation = clamp_int(
        next_state.company.reputation + reputation_delta,
        0,
        100,
    )

    next_state.company.game_over = is_game_over(next_state.company)
    if not next_state.company.game_over:
        next_state.company.current_turn += 1
        next_state.action_points_remaining = BALANCE.actions_per_turn

    narrative = build_turn_narrative(
        net_cash_flow=net_cash_flow,
        reputation_delta=reputation_delta,
        product_summaries=product_summaries,
        game_over=next_state.company.game_over,
    )
    logger.debug("Resolved turn %s.", resolved_turn)

    return TurnResolution(
        state=next_state,
        resolved_turn=resolved_turn,
        total_revenue=total_revenue,
        baseline_operating_cost=BALANCE.base_operating_cost,
        total_product_operating_cost=total_product_operating_cost,
        total_operating_cost=total_operating_cost,
        net_cash_flow=net_cash_flow,
        reputation_delta=reputation_delta,
        product_summaries=product_summaries,
        narrative=narrative,
    )


def get_product_choices(state: GameState, active_only: bool = True) -> list[Product]:
    """Return products available for CLI target selection."""

    if active_only:
        return [product for product in state.products if product.is_active]
    return list(state.products)


def get_target_product(state: GameState, product_id: Optional[UUID]) -> Product:
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
    game_over: bool,
) -> str:
    """Generate a concise story beat for the turn summary."""

    if game_over:
        return "The company ran out of cash. The portfolio could not carry the burn."

    total_user_delta = sum(summary.net_user_delta for summary in product_summaries)
    declining_products = [
        summary for summary in product_summaries if summary.net_user_delta < 0
    ]
    expanding_products = [
        summary for summary in product_summaries if summary.net_user_delta > 0
    ]

    if net_cash_flow > 0 and len(expanding_products) >= 2:
        return "The portfolio is compounding. More than one product is pulling its weight."
    if declining_products and reputation_delta < 0:
        return "Weak products are dragging the company brand down."
    if total_user_delta > 0 and net_cash_flow > 0:
        return "Your strategy is landing. Growth and cash flow moved in the right direction."
    if net_cash_flow < 0:
        return "The company is still buying time. Burn discipline matters this turn."
    return "The portfolio held steady this turn."


def clamp_int(value: int, minimum: int, maximum: int) -> int:
    """Clamp an integer between two bounds."""

    return max(minimum, min(maximum, value))
