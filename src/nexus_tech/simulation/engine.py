"""Turn resolution and action handling for Phase 1."""

import logging
from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import Company, GameState, Product, TurnAction
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.randomness import RandomLike

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ActionOutcome:
    """Result of a single player action."""

    state: GameState
    message: str
    turn_should_end: bool = False


@dataclass(frozen=True)
class TurnResolution:
    """Summary of what happened when a turn was simulated."""

    state: GameState
    resolved_turn: int
    revenue: Decimal
    operating_cost: Decimal
    net_cash_flow: Decimal
    user_delta: int
    reputation_delta: int
    quality_delta: int
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
        quality=BALANCE.starting_quality,
        bug_level=BALANCE.starting_bug_level,
        user_count=BALANCE.starting_users,
        revenue_per_user=BALANCE.starting_revenue_per_user,
        feature_count=BALANCE.starting_feature_count,
    )
    return GameState(
        company=company,
        product=product,
        action_points_remaining=BALANCE.actions_per_turn,
    )


def calculate_revenue(product: Product) -> Decimal:
    """Revenue earned from the current user base."""

    return quantize_money(Decimal(product.user_count) * product.revenue_per_user)


def calculate_operating_cost(product: Product) -> Decimal:
    """Recurring cost of keeping the company running for one turn."""

    feature_cost = Decimal(product.feature_count) * BALANCE.per_feature_cost
    support_cost = Decimal(product.user_count) * BALANCE.per_user_support_cost
    return quantize_money(BALANCE.base_operating_cost + feature_cost + support_cost)


def calculate_user_delta(company: Company, product: Product, rng: RandomLike) -> int:
    """Estimate how the player base moves this turn."""

    traction_score = product.quality + company.reputation - (product.bug_level * 2)
    traction_score -= BALANCE.traction_baseline

    delta = (traction_score // BALANCE.user_growth_divisor) + rng.randint(
        -BALANCE.user_random_swing,
        BALANCE.user_random_swing,
    )
    if delta > 0 and product.feature_count >= 3:
        delta += 1

    max_gain = max(3, (product.user_count // 4) + 3)
    max_loss = product.user_count
    return max(-max_loss, min(max_gain, delta))


def calculate_reputation_delta(company: Company, product: Product, rng: RandomLike) -> int:
    """Move reputation based on product health plus light randomness."""

    condition_score = product.quality - product.bug_level
    if condition_score >= BALANCE.strong_reputation_threshold:
        base_delta = 2
    elif condition_score >= BALANCE.positive_reputation_threshold:
        base_delta = 1
    elif condition_score <= BALANCE.bad_reputation_threshold:
        base_delta = -2
    elif condition_score <= BALANCE.soft_bad_reputation_threshold:
        base_delta = -1
    else:
        base_delta = 0

    return clamp_int(base_delta + rng.randint(-1, 1), -2, 2)


def calculate_quality_delta(product: Product) -> int:
    """Shift quality slightly as bugs accumulate or stay controlled."""

    if product.bug_level >= BALANCE.severe_bug_threshold:
        return -2
    if product.bug_level >= BALANCE.moderate_bug_threshold:
        return -1
    if product.bug_level <= BALANCE.polished_bug_threshold and product.feature_count >= 2:
        return 1
    return 0


def is_game_over(company: Company) -> bool:
    """Check the loss condition for the company."""

    return company.cash_on_hand < BALANCE.game_over_cash_threshold


def apply_action(state: GameState, action: TurnAction) -> ActionOutcome:
    """Apply a player action without running the end-of-turn simulation."""

    if state.company.game_over:
        return ActionOutcome(
            state=state, message="The company has already shut down.", turn_should_end=True
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

    if action is TurnAction.BUILD_FEATURE:
        next_state.product.feature_count += BALANCE.build_feature_feature_gain
        next_state.product.quality = clamp_int(
            next_state.product.quality + BALANCE.build_feature_quality_gain,
            0,
            100,
        )
        next_state.product.bug_level = clamp_int(
            next_state.product.bug_level + BALANCE.build_feature_bug_increase,
            0,
            100,
        )
        logger.debug("Applied build_feature action.")
        return ActionOutcome(
            state=next_state,
            message=(
                "You shipped a compact feature set. "
                f"Quality +{BALANCE.build_feature_quality_gain}, "
                f"bugs +{BALANCE.build_feature_bug_increase}."
            ),
        )

    if action is TurnAction.FIX_BUGS:
        next_state.product.bug_level = clamp_int(
            next_state.product.bug_level - BALANCE.fix_bugs_bug_reduction,
            0,
            100,
        )
        next_state.product.quality = clamp_int(
            next_state.product.quality + BALANCE.fix_bugs_quality_gain,
            0,
            100,
        )
        logger.debug("Applied fix_bugs action.")
        return ActionOutcome(
            state=next_state,
            message=(
                "You ran a stability pass. "
                f"Bugs -{BALANCE.fix_bugs_bug_reduction}, "
                f"quality +{BALANCE.fix_bugs_quality_gain}."
            ),
        )

    if action is TurnAction.MARKET_PRODUCT:
        next_state.company.cash_on_hand = quantize_money(
            next_state.company.cash_on_hand - BALANCE.marketing_cost
        )
        next_state.company.reputation = clamp_int(
            next_state.company.reputation + BALANCE.marketing_reputation_gain,
            0,
            100,
        )
        next_state.product.user_count = max(
            0,
            next_state.product.user_count + BALANCE.marketing_user_gain,
        )
        next_state.company.game_over = is_game_over(next_state.company)
        logger.debug("Applied market_product action.")
        return ActionOutcome(
            state=next_state,
            message=(
                "You ran a lean campaign. "
                f"Cash -{BALANCE.marketing_cost}, "
                f"users +{BALANCE.marketing_user_gain}, "
                f"reputation +{BALANCE.marketing_reputation_gain}."
            ),
            turn_should_end=next_state.company.game_over,
        )

    logger.debug("Applied wait action.")
    return ActionOutcome(
        state=next_state,
        message="You waited, watched the metrics, and preserved focus.",
    )


def resolve_turn(state: GameState, rng: RandomLike) -> TurnResolution:
    """Run the end-of-turn simulation tick."""

    resolved_turn = state.company.current_turn
    next_state = state.model_copy(deep=True)

    revenue = calculate_revenue(next_state.product)
    operating_cost = calculate_operating_cost(next_state.product)
    net_cash_flow = quantize_money(revenue - operating_cost)

    next_state.company.cash_on_hand = quantize_money(
        next_state.company.cash_on_hand + net_cash_flow
    )

    user_delta = calculate_user_delta(next_state.company, next_state.product, rng)
    next_state.product.user_count = max(0, next_state.product.user_count + user_delta)

    reputation_delta = calculate_reputation_delta(next_state.company, next_state.product, rng)
    next_state.company.reputation = clamp_int(
        next_state.company.reputation + reputation_delta, 0, 100
    )

    quality_delta = calculate_quality_delta(next_state.product)
    next_state.product.quality = clamp_int(next_state.product.quality + quality_delta, 0, 100)

    next_state.company.game_over = is_game_over(next_state.company)
    if not next_state.company.game_over:
        next_state.company.current_turn += 1
        next_state.action_points_remaining = BALANCE.actions_per_turn

    narrative = build_turn_narrative(
        net_cash_flow, user_delta, reputation_delta, next_state.company.game_over
    )
    logger.debug("Resolved turn %s.", resolved_turn)

    return TurnResolution(
        state=next_state,
        resolved_turn=resolved_turn,
        revenue=revenue,
        operating_cost=operating_cost,
        net_cash_flow=net_cash_flow,
        user_delta=user_delta,
        reputation_delta=reputation_delta,
        quality_delta=quality_delta,
        narrative=narrative,
    )


def build_turn_narrative(
    net_cash_flow: Decimal,
    user_delta: int,
    reputation_delta: int,
    game_over: bool,
) -> str:
    """Generate a concise story beat for the turn summary."""

    if game_over:
        return "The company ran out of cash. The board closes the doors."
    if net_cash_flow > 0 and user_delta > 0:
        return "Momentum is building. The product is starting to look real."
    if user_delta < 0 and reputation_delta < 0:
        return "Customers are slipping away and the market is noticing."
    if net_cash_flow < 0:
        return "You bought time, but the burn is starting to matter."
    return "The business held steady this turn."


def clamp_int(value: int, minimum: int, maximum: int) -> int:
    """Clamp an integer between two bounds."""

    return max(minimum, min(maximum, value))
