"""Central tuning values for Phase 2."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class BalanceConfig:
    """Gameplay constants kept in one place for easy tuning."""

    actions_per_turn: int = 2

    starting_cash: Decimal = Decimal("8500.00")
    starting_reputation: int = 50

    starting_quality: int = 58
    starting_bug_level: int = 18
    starting_market_fit: int = 52
    starting_technical_debt: int = 14
    starting_users: int = 35
    starting_revenue_per_user: Decimal = Decimal("30.00")
    starting_feature_count: int = 1
    starting_maintenance_cost: Decimal = Decimal("260.00")
    starting_acquisition_rate: Decimal = Decimal("0.0600")
    starting_churn_rate: Decimal = Decimal("0.0500")

    new_product_quality: int = 42
    new_product_bug_level: int = 16
    new_product_market_fit: int = 30
    new_product_technical_debt: int = 18
    new_product_users: int = 0
    new_product_revenue_per_user: Decimal = Decimal("24.00")
    new_product_feature_count: int = 0
    new_product_maintenance_cost: Decimal = Decimal("190.00")
    new_product_acquisition_rate: Decimal = Decimal("0.0400")
    new_product_churn_rate: Decimal = Decimal("0.0900")
    create_product_cost: Decimal = Decimal("1400.00")

    improve_quality_quality_gain: int = 6
    improve_quality_min_gain: int = 2
    improve_quality_bug_reduction: int = 7
    improve_quality_min_bug_reduction: int = 3
    improve_quality_market_fit_gain: int = 1

    add_feature_quality_gain: int = 3
    add_feature_market_fit_gain: int = 4
    add_feature_bug_increase: int = 5
    add_feature_bug_debt_divisor: int = 25
    add_feature_debt_increase: int = 8
    add_feature_feature_gain: int = 1
    add_feature_maintenance_increase: Decimal = Decimal("45.00")
    add_feature_acquisition_rate_gain: Decimal = Decimal("0.0060")
    add_feature_churn_rate_increase: Decimal = Decimal("0.0040")

    reduce_debt_amount: int = 14
    reduce_debt_bug_reduction: int = 3
    reduce_debt_quality_gain: int = 1
    reduce_debt_maintenance_reduction: Decimal = Decimal("25.00")

    marketing_cost: Decimal = Decimal("320.00")
    marketing_reputation_gain: int = 1
    marketing_base_user_gain: int = 4
    marketing_market_fit_divisor: int = 25
    marketing_quality_signal_divisor: int = 30
    marketing_bug_penalty_divisor: int = 25
    marketing_acquisition_rate_gain: Decimal = Decimal("0.0100")

    base_operating_cost: Decimal = Decimal("850.00")
    per_user_support_cost: Decimal = Decimal("1.20")
    per_debt_operating_cost: Decimal = Decimal("3.00")

    acquisition_signal_baseline: int = 150
    acquisition_signal_divisor: int = 20
    acquisition_cap_base: int = 4
    acquisition_cap_divisor: int = 6
    acquisition_random_swing: int = 1
    discovery_market_fit_threshold: int = 35

    min_churn_rate: Decimal = Decimal("0.0200")
    max_churn_rate: Decimal = Decimal("0.3500")
    churn_bug_divisor: int = 12
    churn_debt_divisor: int = 14
    churn_quality_relief_divisor: int = 25
    low_market_fit_threshold: int = 40
    low_market_fit_churn_penalty: int = 2
    churn_random_swing: int = 1

    reputation_strong_threshold: int = 65
    reputation_positive_threshold: int = 50
    reputation_soft_bad_threshold: int = 28
    reputation_bad_threshold: int = 14

    debt_efficiency_divisor: int = 20
    debt_bug_risk_threshold: int = 30
    debt_bug_risk_divisor: int = 25
    debt_bug_extra_threshold: int = 65
    debt_bug_random_high: int = 1
    severe_bug_threshold: int = 35
    moderate_bug_threshold: int = 22
    severe_debt_threshold: int = 60
    moderate_debt_threshold: int = 35
    polished_bug_threshold: int = 8
    polished_debt_threshold: int = 12
    polished_market_fit_threshold: int = 55

    growth_user_threshold: int = 25
    mature_user_threshold: int = 80
    growth_market_fit_threshold: int = 50
    mature_market_fit_threshold: int = 72
    declining_bug_threshold: int = 42
    declining_debt_threshold: int = 55
    declining_market_fit_threshold: int = 28

    game_over_cash_threshold: Decimal = Decimal("0.00")


BALANCE = BalanceConfig()
