"""Central tuning values for the simulation."""

from dataclasses import dataclass, field
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

    pricing_budget_revenue_multiplier: Decimal = Decimal("0.85")
    pricing_premium_revenue_multiplier: Decimal = Decimal("1.25")
    pricing_budget_acquisition_bonus: int = 2
    pricing_premium_acquisition_bonus: int = -2
    pricing_budget_churn_modifier: Decimal = Decimal("-0.0120")
    pricing_premium_churn_modifier: Decimal = Decimal("0.0140")
    pricing_budget_market_fit_bonus: int = 1
    pricing_premium_quality_threshold: int = 62
    pricing_premium_market_fit_bonus: int = 1
    pricing_premium_market_fit_penalty: int = 2

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

    employee_starting_energy: int = 82
    employee_starting_morale: int = 76
    employee_rest_energy_gain: int = 22
    employee_rest_morale_gain: int = 14
    employee_assigned_energy_loss: int = 8
    employee_assigned_morale_loss: int = 1
    employee_unassigned_energy_recovery: int = 4
    employee_unassigned_morale_recovery: int = 1
    employee_burnout_energy_threshold: int = 35
    employee_low_morale_threshold: int = 45
    employee_burnout_morale_penalty: int = 2
    employee_negative_cash_flow_morale_penalty: int = 1
    employee_pressure_bug_divisor: int = 18
    employee_pressure_debt_divisor: int = 24
    employee_role_base_salary: dict[str, Decimal] = field(
        default_factory=lambda: {
            "engineer": Decimal("720.00"),
            "designer": Decimal("620.00"),
            "marketer": Decimal("640.00"),
            "product_manager": Decimal("760.00"),
        }
    )
    employee_role_base_productivity: dict[str, int] = field(
        default_factory=lambda: {
            "engineer": 66,
            "designer": 58,
            "marketer": 62,
            "product_manager": 60,
        }
    )
    employee_seniority_salary_multiplier: dict[str, Decimal] = field(
        default_factory=lambda: {
            "junior": Decimal("0.85"),
            "mid": Decimal("1.00"),
            "senior": Decimal("1.25"),
        }
    )
    employee_seniority_productivity_bonus: dict[str, int] = field(
        default_factory=lambda: {
            "junior": -4,
            "mid": 0,
            "senior": 8,
        }
    )
    employee_default_specializations: dict[str, str] = field(
        default_factory=lambda: {
            "engineer": "platform",
            "designer": "ux",
            "marketer": "growth",
            "product_manager": "delivery",
        }
    )
    team_build_bonus_divisor: int = 44
    team_stability_bonus_divisor: int = 48
    team_market_fit_bonus_divisor: int = 52
    team_acquisition_bonus_divisor: int = 45
    team_reputation_bonus_divisor: int = 75
    team_debt_bonus_divisor: int = 38
    team_coordination_bonus_divisor: int = 36
    team_burnout_protection_divisor: int = 55

    event_trigger_min_turn: int = 2
    event_trigger_chance_percent: int = 42
    event_history_limit: int = 16

    event_bug_incident_weight: int = 8
    event_bug_incident_cooldown: int = 4
    event_bug_incident_bug_threshold: int = 32
    event_bug_incident_debt_threshold: int = 48
    event_bug_hotfix_cost: Decimal = Decimal("260.00")
    event_bug_hotfix_bug_reduction: int = 12
    event_bug_hotfix_quality_loss: int = 1
    event_bug_hotfix_reputation_loss: int = 1
    event_bug_hotfix_energy_loss: int = 10
    event_bug_hotfix_morale_loss: int = 2
    event_bug_delay_bug_increase: int = 8
    event_bug_delay_reputation_loss: int = 3
    event_bug_delay_user_loss_divisor: int = 6
    event_bug_delay_min_user_loss: int = 3
    event_bug_delay_energy_loss: int = 2
    event_bug_delay_morale_loss: int = 3

    event_press_mention_weight: int = 5
    event_press_mention_cooldown: int = 3
    event_press_market_fit_threshold: int = 46
    event_press_min_user_gain: int = 3
    event_press_user_gain_divisor: int = 12
    event_press_reputation_gain: int = 2
    event_press_acquisition_gain: Decimal = Decimal("0.0040")
    event_press_marketer_morale_gain: int = 2

    event_investor_outreach_weight: int = 5
    event_investor_outreach_cooldown: int = 5
    event_investor_reputation_threshold: int = 48
    event_investor_cash_threshold: Decimal = Decimal("3200.00")
    event_investor_cash_gain: Decimal = Decimal("2400.00")
    event_investor_reputation_gain: int = 1
    event_investor_team_morale_penalty: int = 2
    event_bootstrap_team_morale_gain: int = 2
    event_bootstrap_reputation_gain: int = 1

    event_burnout_spike_weight: int = 7
    event_burnout_spike_cooldown: int = 3
    event_burnout_spike_energy_threshold: int = 55
    event_burnout_spike_morale_threshold: int = 50
    event_burnout_relief_cost: Decimal = Decimal("180.00")
    event_burnout_relief_energy_gain: int = 18
    event_burnout_relief_morale_gain: int = 10
    event_burnout_relief_team_morale_gain: int = 1
    event_burnout_push_energy_loss: int = 12
    event_burnout_push_morale_loss: int = 8
    event_burnout_push_quality_loss: int = 2
    event_burnout_push_reputation_loss: int = 1

    event_market_trend_weight: int = 6
    event_market_trend_cooldown: int = 4
    event_market_trend_fit_threshold: int = 50
    event_market_trend_invest_cost: Decimal = Decimal("200.00")
    event_market_trend_big_user_gain: int = 8
    event_market_trend_small_user_gain: int = 3
    event_market_trend_acquisition_gain: Decimal = Decimal("0.0070")
    event_market_trend_reputation_gain: int = 1
    event_market_trend_energy_loss: int = 4

    event_competitor_pressure_weight: int = 6
    event_competitor_pressure_cooldown: int = 4
    event_competitor_pressure_user_threshold: int = 24
    event_competitor_rush_feature_gain: int = 1
    event_competitor_rush_market_fit_gain: int = 2
    event_competitor_rush_bug_increase: int = 6
    event_competitor_rush_debt_increase: int = 7
    event_competitor_rush_energy_loss: int = 8
    event_competitor_focus_quality_gain: int = 3
    event_competitor_focus_bug_reduction: int = 2
    event_competitor_focus_market_fit_gain: int = 2
    event_competitor_focus_user_loss: int = 3
    event_competitor_focus_reputation_gain: int = 1

    cash_reserve_milestone_threshold: Decimal = Decimal("12000.00")
    team_growth_milestone_headcount: int = 4
    active_products_milestone_threshold: int = 3
    milestone_first_100_users_reputation_gain: int = 2
    milestone_cash_reserve_reputation_gain: int = 1
    milestone_team_growth_reputation_gain: int = 1
    milestone_team_growth_morale_gain: int = 2
    milestone_active_products_reputation_gain: int = 2
    milestone_first_mature_product_cash_gain: Decimal = Decimal("450.00")
    milestone_first_mature_product_reputation_gain: int = 1

    game_over_cash_threshold: Decimal = Decimal("0.00")


BALANCE = BalanceConfig()
