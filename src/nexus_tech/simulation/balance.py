"""Central tuning values for Phase 1."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class BalanceConfig:
    """Gameplay constants kept in one place for easy tuning."""

    actions_per_turn: int = 2

    starting_cash: Decimal = Decimal("7500.00")
    starting_reputation: int = 50

    starting_quality: int = 55
    starting_bug_level: int = 20
    starting_users: int = 35
    starting_revenue_per_user: Decimal = Decimal("30.00")
    starting_feature_count: int = 1

    build_feature_quality_gain: int = 5
    build_feature_bug_increase: int = 4
    build_feature_feature_gain: int = 1

    fix_bugs_bug_reduction: int = 7
    fix_bugs_quality_gain: int = 2

    marketing_cost: Decimal = Decimal("300.00")
    marketing_reputation_gain: int = 3
    marketing_user_gain: int = 6

    base_operating_cost: Decimal = Decimal("920.00")
    per_feature_cost: Decimal = Decimal("55.00")
    per_user_support_cost: Decimal = Decimal("1.50")

    traction_baseline: int = 55
    user_growth_divisor: int = 12
    user_random_swing: int = 2

    strong_reputation_threshold: int = 60
    positive_reputation_threshold: int = 40
    bad_reputation_threshold: int = 10
    soft_bad_reputation_threshold: int = 25

    severe_bug_threshold: int = 35
    moderate_bug_threshold: int = 18
    polished_bug_threshold: int = 5

    game_over_cash_threshold: Decimal = Decimal("0.00")


BALANCE = BalanceConfig()
