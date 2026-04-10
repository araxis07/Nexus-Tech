from decimal import Decimal

from nexus_tech.domain.models import Company, GameState, Product, TurnAction
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.engine import (
    apply_action,
    calculate_revenue,
    calculate_user_delta,
    create_new_game,
    resolve_turn,
)


class FixedRandom:
    def __init__(self, value: int) -> None:
        self.value = value

    def randint(self, start: int, end: int) -> int:
        return self.value


def make_state(
    *,
    cash_on_hand: Decimal = Decimal("5000.00"),
    reputation: int = 50,
    quality: int = 55,
    bug_level: int = 20,
    user_count: int = 35,
    revenue_per_user: Decimal = Decimal("30.00"),
    feature_count: int = 1,
) -> GameState:
    return GameState(
        company=Company(name="NEXUS TECH", cash_on_hand=cash_on_hand, reputation=reputation),
        product=Product(
            name="Nexus One",
            quality=quality,
            bug_level=bug_level,
            user_count=user_count,
            revenue_per_user=revenue_per_user,
            feature_count=feature_count,
        ),
        action_points_remaining=BALANCE.actions_per_turn,
    )


def test_calculate_revenue_uses_decimal_money() -> None:
    state = make_state(user_count=12, revenue_per_user=Decimal("19.99"))

    revenue = calculate_revenue(state.product)

    assert revenue == Decimal("239.88")


def test_user_delta_grows_for_healthy_product_and_declines_for_unhealthy_product() -> None:
    healthy_state = make_state(reputation=70, quality=80, bug_level=5, feature_count=3)
    unhealthy_state = make_state(reputation=20, quality=30, bug_level=40, user_count=25)
    rng = FixedRandom(0)

    healthy_delta = calculate_user_delta(healthy_state.company, healthy_state.product, rng)
    unhealthy_delta = calculate_user_delta(unhealthy_state.company, unhealthy_state.product, rng)

    assert healthy_delta > 0
    assert unhealthy_delta < 0


def test_resolve_turn_sets_game_over_when_cash_drops_below_zero() -> None:
    state = make_state(
        cash_on_hand=Decimal("100.00"),
        reputation=10,
        quality=25,
        bug_level=40,
        user_count=0,
        revenue_per_user=Decimal("0.00"),
    )

    resolution = resolve_turn(state, FixedRandom(0))

    assert resolution.state.company.game_over is True
    assert resolution.state.company.cash_on_hand < Decimal("0.00")
    assert resolution.state.company.current_turn == 1


def test_build_feature_increases_quality_bugs_and_feature_count() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")

    outcome = apply_action(state, TurnAction.BUILD_FEATURE)

    assert outcome.state.product.feature_count == state.product.feature_count + 1
    assert (
        outcome.state.product.quality == state.product.quality + BALANCE.build_feature_quality_gain
    )
    assert (
        outcome.state.product.bug_level
        == state.product.bug_level + BALANCE.build_feature_bug_increase
    )
    assert outcome.state.action_points_remaining == BALANCE.actions_per_turn - 1


def test_fix_bugs_reduces_bug_level_and_improves_quality() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")

    outcome = apply_action(state, TurnAction.FIX_BUGS)

    assert (
        outcome.state.product.bug_level == state.product.bug_level - BALANCE.fix_bugs_bug_reduction
    )
    assert outcome.state.product.quality == state.product.quality + BALANCE.fix_bugs_quality_gain
    assert outcome.state.action_points_remaining == BALANCE.actions_per_turn - 1
