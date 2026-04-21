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

    segment_base_acquisition_bonus: dict[str, int] = field(
        default_factory=lambda: {
            "indie": 2,
            "startup": 1,
            "smb": 0,
            "enterprise": -2,
        }
    )
    segment_base_churn_modifier: dict[str, Decimal] = field(
        default_factory=lambda: {
            "indie": Decimal("-0.0060"),
            "startup": Decimal("0.0000"),
            "smb": Decimal("0.0060"),
            "enterprise": Decimal("0.0120"),
        }
    )
    segment_support_cost_multiplier: dict[str, Decimal] = field(
        default_factory=lambda: {
            "indie": Decimal("0.85"),
            "startup": Decimal("1.00"),
            "smb": Decimal("1.15"),
            "enterprise": Decimal("1.40"),
        }
    )
    segment_price_sensitivity_multiplier: dict[str, Decimal] = field(
        default_factory=lambda: {
            "indie": Decimal("1.35"),
            "startup": Decimal("1.10"),
            "smb": Decimal("0.90"),
            "enterprise": Decimal("0.60"),
        }
    )
    segment_market_fit_threshold: dict[str, int] = field(
        default_factory=lambda: {
            "indie": 38,
            "startup": 46,
            "smb": 54,
            "enterprise": 64,
        }
    )
    segment_quality_threshold: dict[str, int] = field(
        default_factory=lambda: {
            "indie": 40,
            "startup": 48,
            "smb": 58,
            "enterprise": 70,
        }
    )
    segment_bug_tolerance_divisor: dict[str, int] = field(
        default_factory=lambda: {
            "indie": 22,
            "startup": 18,
            "smb": 14,
            "enterprise": 10,
        }
    )
    segment_fit_bonus_divisor: dict[str, int] = field(
        default_factory=lambda: {
            "indie": 16,
            "startup": 18,
            "smb": 20,
            "enterprise": 24,
        }
    )
    competitor_pressure_base: dict[str, int] = field(
        default_factory=lambda: {
            "indie": 1,
            "startup": 2,
            "smb": 3,
            "enterprise": 4,
        }
    )
    competitor_pressure_turn_divisor: int = 4
    competitor_pressure_user_divisor: int = 45
    competitor_pressure_cap: int = 8
    competitor_pressure_growth_penalty_divisor: int = 2
    competitor_pressure_churn_modifier_divisor: int = 100

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

    roadmap_duration_turns: int = 4
    roadmap_growth_acquisition_bonus: int = 2
    roadmap_growth_operating_cost_modifier: Decimal = Decimal("90.00")
    roadmap_growth_feature_risk_modifier: int = 2
    roadmap_growth_competitor_relief: int = 0
    roadmap_platform_quality_bonus: int = 2
    roadmap_platform_debt_bonus: int = 5
    roadmap_platform_operating_cost_modifier: Decimal = Decimal("40.00")
    roadmap_platform_competitor_relief: int = 2
    roadmap_premium_quality_bonus: int = 2
    roadmap_premium_market_fit_bonus: int = 2
    roadmap_premium_reputation_bonus: int = 1
    roadmap_premium_acquisition_penalty: int = -1
    roadmap_premium_competitor_relief: int = 1
    roadmap_portfolio_efficiency_bonus: int = 2
    roadmap_portfolio_operating_cost_modifier: Decimal = Decimal("-80.00")
    roadmap_portfolio_acquisition_penalty: int = -1
    roadmap_portfolio_competitor_relief: int = 1

    budget_lean_operating_cost_modifier: Decimal = Decimal("-90.00")
    budget_lean_marketing_cost_multiplier: Decimal = Decimal("0.80")
    budget_lean_marketing_bonus: int = -1
    budget_lean_burnout_modifier: int = -1
    budget_lean_headcount_cap_bonus: int = 0
    budget_balanced_operating_cost_modifier: Decimal = Decimal("0.00")
    budget_balanced_marketing_cost_multiplier: Decimal = Decimal("1.00")
    budget_balanced_marketing_bonus: int = 0
    budget_balanced_burnout_modifier: int = 0
    budget_balanced_headcount_cap_bonus: int = 1
    budget_aggressive_operating_cost_modifier: Decimal = Decimal("80.00")
    budget_aggressive_marketing_cost_multiplier: Decimal = Decimal("1.20")
    budget_aggressive_marketing_bonus: int = 2
    budget_aggressive_burnout_modifier: int = 1
    budget_aggressive_headcount_cap_bonus: int = 2

    market_cycle_min_duration: int = 2
    market_cycle_max_duration: int = 4
    market_cycle_acquisition_bonus: dict[str, int] = field(
        default_factory=lambda: {
            "cooling": -2,
            "steady": 0,
            "expanding": 1,
            "frothy": 2,
        }
    )
    market_cycle_churn_modifier: dict[str, Decimal] = field(
        default_factory=lambda: {
            "cooling": Decimal("0.0100"),
            "steady": Decimal("0.0000"),
            "expanding": Decimal("-0.0060"),
            "frothy": Decimal("0.0030"),
        }
    )
    market_cycle_competitor_pressure_modifier: dict[str, int] = field(
        default_factory=lambda: {
            "cooling": 1,
            "steady": 0,
            "expanding": 0,
            "frothy": 1,
        }
    )
    market_cycle_segment_bonus: dict[str, dict[str, int]] = field(
        default_factory=lambda: {
            "cooling": {"indie": 0, "startup": -1, "smb": 1, "enterprise": 1},
            "steady": {"indie": 0, "startup": 0, "smb": 0, "enterprise": 0},
            "expanding": {"indie": 1, "startup": 1, "smb": 0, "enterprise": 0},
            "frothy": {"indie": 1, "startup": 2, "smb": 0, "enterprise": -1},
        }
    )
    market_cycle_transition_weights: dict[str, dict[str, int]] = field(
        default_factory=lambda: {
            "cooling": {"cooling": 3, "steady": 5, "expanding": 1, "frothy": 0},
            "steady": {"cooling": 2, "steady": 4, "expanding": 3, "frothy": 1},
            "expanding": {"cooling": 0, "steady": 3, "expanding": 4, "frothy": 3},
            "frothy": {"cooling": 1, "steady": 3, "expanding": 3, "frothy": 2},
        }
    )

    difficulty_builder_acquisition_bonus: int = 1
    difficulty_standard_acquisition_bonus: int = 0
    difficulty_founder_acquisition_bonus: int = -1
    difficulty_builder_churn_modifier: Decimal = Decimal("-0.0060")
    difficulty_standard_churn_modifier: Decimal = Decimal("0.0000")
    difficulty_founder_churn_modifier: Decimal = Decimal("0.0080")
    difficulty_builder_operating_cost_multiplier: Decimal = Decimal("0.94")
    difficulty_standard_operating_cost_multiplier: Decimal = Decimal("1.00")
    difficulty_founder_operating_cost_multiplier: Decimal = Decimal("1.08")
    difficulty_builder_burnout_modifier: int = -1
    difficulty_standard_burnout_modifier: int = 0
    difficulty_founder_burnout_modifier: int = 1
    difficulty_builder_score_modifier: int = -12
    difficulty_standard_score_modifier: int = 0
    difficulty_founder_score_modifier: int = 16

    scale_late_game_turn_threshold: int = 8
    scale_turn_pressure_divisor: int = 4
    scale_feature_pressure_divisor: int = 6
    scale_maintenance_multiplier_divisor: int = 18
    scale_feature_maintenance_divisor: int = 24
    scale_cannibalization_same_segment_penalty: int = 1
    scale_cannibalization_price_match_penalty: int = 1
    scale_coordination_headcount_factor: int = 2
    scale_coordination_relief_base: int = 1
    scale_coordination_churn_divisor: int = 200
    scale_segment_saturation_threshold: dict[str, int] = field(
        default_factory=lambda: {
            "indie": 120,
            "startup": 170,
            "smb": 135,
            "enterprise": 90,
        }
    )
    scale_segment_saturation_divisor: dict[str, int] = field(
        default_factory=lambda: {
            "indie": 60,
            "startup": 70,
            "smb": 55,
            "enterprise": 35,
        }
    )
    operations_user_load_divisor: int = 28
    operations_bug_load_divisor: int = 18
    operations_debt_load_divisor: int = 24
    operations_feature_load_divisor: int = 2
    operations_active_product_overhead: int = 1
    operations_late_turn_threshold: int = 8
    operations_turn_load_divisor: int = 4
    operations_assigned_capacity_per_person: int = 3
    operations_unassigned_capacity_per_person: int = 2
    operations_company_headcount_capacity: int = 1
    operations_product_manager_capacity_bonus: int = 2
    operations_designer_capacity_bonus: int = 1
    operations_marketer_capacity_bonus: int = 1
    operations_same_segment_overlap_penalty: int = 1
    operations_large_user_base_threshold: int = 120
    operations_overload_cost_per_point: Decimal = Decimal("85.00")
    operations_energy_penalty_divisor: int = 3
    operations_morale_penalty_divisor: int = 4
    operations_max_energy_penalty: int = 4
    operations_max_morale_penalty: int = 3
    operations_moderate_overload_threshold: int = 3
    operations_severe_overload_threshold: int = 6
    operations_reputation_penalty_threshold: int = 5
    operations_bug_penalty_threshold: int = 3
    operations_quality_penalty_threshold: int = 5
    operations_bug_penalty: int = 2
    operations_quality_penalty: int = 1
    operations_affected_product_limit: int = 2
    operations_segment_load_bonus: dict[str, int] = field(
        default_factory=lambda: {
            "indie": 0,
            "startup": 1,
            "smb": 2,
            "enterprise": 3,
        }
    )
    operations_stage_load_bonus: dict[str, int] = field(
        default_factory=lambda: {
            "prototype": 0,
            "growth": 1,
            "mature": 2,
            "declining": 2,
            "sunset": 0,
        }
    )
    late_game_turn_threshold: int = 10
    late_game_total_user_threshold: int = 180
    late_game_concentration_share_threshold: int = 58
    late_game_concentration_divisor: int = 8
    late_game_large_product_user_threshold: int = 95
    late_game_renewal_user_divisor: int = 70
    late_game_bug_threshold: int = 26
    late_game_bug_divisor: int = 16
    late_game_debt_threshold: int = 32
    late_game_debt_divisor: int = 18
    late_game_declining_stage_legacy_bonus: int = 2
    late_game_feature_overhang_threshold: int = 4
    late_game_feature_overhang_divisor: int = 3
    late_game_org_drag_product_threshold: int = 3
    late_game_org_drag_headcount_threshold: int = 6
    late_game_org_drag_divisor: int = 2
    late_game_maintenance_crisis_cost_threshold: Decimal = Decimal("1150.00")
    late_game_maintenance_crisis_cost_divisor: Decimal = Decimal("260.00")
    late_game_maintenance_crisis_mature_threshold: int = 2
    late_game_innovation_gap_mature_threshold: int = 2
    late_game_innovation_gap_growth_product_cap: int = 0
    late_game_innovation_gap_debt_threshold: int = 28
    late_game_cost_per_point: Decimal = Decimal("110.00")
    late_game_burnout_divisor: int = 4
    late_game_max_burnout_modifier: int = 3
    late_game_reputation_penalty_threshold: int = 4
    late_game_reputation_penalty: int = 1
    late_game_market_fit_penalty_threshold: int = 3
    late_game_market_fit_penalty: int = 1
    late_game_quality_penalty_threshold: int = 4
    late_game_quality_penalty: int = 1
    late_game_max_user_loss_per_product: int = 8

    competitor_strength_drift_max: int = 3
    competitor_aggression_drift_max: int = 3
    competitor_segment_match_bonus: int = 2
    competitor_strength_divisor: int = 18
    competitor_aggression_divisor: int = 20
    competitor_product_count_bonus: int = 1
    competitor_price_match_bonus: int = 1
    competitor_pressure_cap_total: int = 12
    competitor_move_pressure_bonus: dict[str, int] = field(
        default_factory=lambda: {
            "hold": 0,
            "discount_push": 2,
            "feature_sprint": 3,
            "retrench": -2,
        }
    )
    competitor_momentum_divisor: int = 18
    competitor_move_hold_weight: int = 3
    competitor_move_discount_weight: int = 3
    competitor_move_feature_weight: int = 3
    competitor_move_retrench_weight: int = 2
    competitor_discount_extra_aggression: int = 4
    competitor_feature_extra_strength: int = 4
    competitor_retrench_strength_loss: int = 2
    competitor_retrench_aggression_loss: int = 3
    competitor_momentum_change_on_discount: int = 4
    competitor_momentum_change_on_feature: int = 5
    competitor_momentum_change_on_hold: int = 1
    competitor_momentum_change_on_retrench: int = -5
    competitor_discount_expansion_momentum_threshold: int = 54
    competitor_feature_expansion_momentum_threshold: int = 60
    competitor_move_summary_limit: int = 3
    competitor_focus_pivot_threshold: int = 58
    competitor_focus_pivot_bonus_strength: int = 2
    competitor_focus_pivot_bonus_aggression: int = 2
    competitor_archetype_pressure_bonus: dict[str, int] = field(
        default_factory=lambda: {
            "price_raider": 1,
            "platform_bulwark": 2,
            "feature_blitzer": 1,
            "niche_defender": 1,
            "retreating_incumbent": -1,
            "channel_aggregator": 1,
            "trust_monolith": 2,
            "vertical_specialist": 1,
        }
    )
    competitor_archetype_move_bias: dict[str, dict[str, int]] = field(
        default_factory=lambda: {
            "price_raider": {"discount_push": 3, "feature_sprint": -1},
            "platform_bulwark": {"hold": 2, "feature_sprint": 1, "retrench": -1},
            "feature_blitzer": {"feature_sprint": 3, "hold": -1},
            "niche_defender": {"hold": 2, "discount_push": -1},
            "retreating_incumbent": {"retrench": 3, "discount_push": -1},
            "channel_aggregator": {"discount_push": 1, "feature_sprint": 2},
            "trust_monolith": {"hold": 3, "retrench": -1},
            "vertical_specialist": {"feature_sprint": 1, "hold": 1},
        }
    )
    competitor_archetype_pivot_threshold_bonus: dict[str, int] = field(
        default_factory=lambda: {
            "price_raider": -4,
            "platform_bulwark": 3,
            "feature_blitzer": -2,
            "niche_defender": 8,
            "retreating_incumbent": 6,
            "channel_aggregator": -3,
            "trust_monolith": 5,
            "vertical_specialist": 2,
        }
    )

    quarter_plan_revenue_growth_by_roadmap: dict[str, Decimal] = field(
        default_factory=lambda: {
            "balanced_execution": Decimal("1.08"),
            "growth_push": Decimal("1.16"),
            "platform_rebuild": Decimal("1.04"),
            "premium_expansion": Decimal("1.10"),
            "portfolio_consolidation": Decimal("1.05"),
        }
    )
    quarter_plan_user_growth_by_budget: dict[str, int] = field(
        default_factory=lambda: {
            "lean": 8,
            "balanced": 14,
            "aggressive": 22,
        }
    )
    quarter_plan_cash_buffer_by_budget: dict[str, Decimal] = field(
        default_factory=lambda: {
            "lean": Decimal("1200.00"),
            "balanced": Decimal("800.00"),
            "aggressive": Decimal("300.00"),
        }
    )

    finance_loan_amount: Decimal = Decimal("2500.00")
    finance_max_total_debt: Decimal = Decimal("9000.00")
    finance_loan_interest_rate: Decimal = Decimal("0.0350")
    finance_loan_pressure_gain: int = 3
    finance_repayment_chunk: Decimal = Decimal("1800.00")
    finance_repayment_min_cash_buffer: Decimal = Decimal("1200.00")
    finance_repayment_pressure_relief: int = 2
    finance_angel_raise_amount: Decimal = Decimal("4200.00")
    finance_angel_dilution: Decimal = Decimal("0.0800")
    finance_angel_pressure_gain: int = 7
    finance_angel_round_limit: int = 2
    finance_angel_reputation_threshold: int = 46
    finance_angel_user_threshold: int = 24
    finance_vc_raise_amount: Decimal = Decimal("9600.00")
    finance_vc_dilution: Decimal = Decimal("0.1500")
    finance_vc_pressure_gain: int = 14
    finance_vc_round_limit: int = 1
    finance_vc_reputation_threshold: int = 58
    finance_vc_user_threshold: int = 140
    finance_pressure_cost_divisor: int = 10
    finance_pressure_operating_cost_unit: Decimal = Decimal("18.00")
    finance_debt_distress_threshold: Decimal = Decimal("6000.00")
    finance_pressure_increase_on_negative_cash_flow: int = 2
    finance_pressure_increase_on_high_debt: int = 1
    finance_pressure_relief_on_stability: int = 1
    finance_pressure_relief_cash_threshold: Decimal = Decimal("7000.00")
    finance_score_debt_divisor: Decimal = Decimal("600.00")
    finance_score_pressure_divisor: int = 6
    finance_score_dilution_multiplier: int = 80
    finance_valuation_debt_multiplier: Decimal = Decimal("1.00")
    finance_valuation_dilution_penalty_multiplier: Decimal = Decimal("0.50")

    score_cash_divisor: Decimal = Decimal("500.00")
    score_users_divisor: int = 6
    score_reputation_multiplier: int = 2
    score_headcount_multiplier: int = 3
    score_mature_product_bonus: int = 20
    score_active_product_bonus: int = 8
    score_milestone_bonus: int = 10
    score_campaign_goal_bonus: dict[str, int] = field(
        default_factory=lambda: {
            "profit_machine": 24,
            "portfolio_empire": 32,
            "category_leader": 28,
        }
    )
    valuation_cash_multiplier: Decimal = Decimal("1.00")
    valuation_revenue_multiplier: Decimal = Decimal("12.00")
    valuation_user_multiplier: Decimal = Decimal("14.00")
    victory_min_turn: int = 10
    victory_score_threshold: int = 190
    victory_cash_threshold: Decimal = Decimal("12000.00")
    victory_users_threshold: int = 180
    victory_reputation_threshold: int = 62
    victory_max_debt_threshold: Decimal = Decimal("3000.00")
    victory_max_investor_pressure: int = 45
    campaign_goal_profit_machine_min_turn: int = 8
    campaign_goal_profit_machine_cash_target: Decimal = Decimal("12000.00")
    campaign_goal_profit_machine_streak_target: int = 3
    campaign_goal_profit_machine_debt_cap: Decimal = Decimal("4500.00")
    campaign_goal_portfolio_empire_min_turn: int = 10
    campaign_goal_portfolio_empire_product_target: int = 3
    campaign_goal_portfolio_empire_user_target: int = 260
    campaign_goal_portfolio_empire_segment_target: int = 3
    campaign_goal_category_leader_min_turn: int = 10
    campaign_goal_category_leader_reputation_target: int = 76
    campaign_goal_category_leader_quality_target: int = 68
    campaign_goal_category_leader_mature_product_target: int = 2

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

    event_referral_wave_weight: int = 5
    event_referral_wave_cooldown: int = 4
    event_referral_quality_threshold: int = 68
    event_referral_bug_threshold: int = 14
    event_referral_market_fit_threshold: int = 56
    event_referral_support_cost: Decimal = Decimal("220.00")
    event_referral_big_user_gain: int = 10
    event_referral_small_user_gain: int = 5
    event_referral_acquisition_gain: Decimal = Decimal("0.0060")
    event_referral_churn_relief: Decimal = Decimal("0.0040")
    event_referral_quality_gain: int = 1
    event_referral_team_morale_gain: int = 1

    event_compliance_review_weight: int = 4
    event_compliance_review_cooldown: int = 5
    event_compliance_target_user_threshold: int = 18
    event_compliance_market_fit_threshold: int = 58
    event_compliance_debt_threshold: int = 34
    event_compliance_fund_cost: Decimal = Decimal("280.00")
    event_compliance_debt_reduction: int = 6
    event_compliance_market_fit_gain: int = 3
    event_compliance_reputation_gain: int = 2
    event_compliance_delay_user_loss: int = 4
    event_compliance_delay_reputation_loss: int = 2
    event_compliance_delay_churn_increase: Decimal = Decimal("0.0060")

    event_support_backlog_weight: int = 5
    event_support_backlog_cooldown: int = 4
    event_support_backlog_user_threshold: int = 120
    event_support_backlog_bug_threshold: int = 24
    event_support_backlog_fix_cost: Decimal = Decimal("260.00")
    event_support_backlog_fix_bug_reduction: int = 4
    event_support_backlog_fix_morale_gain: int = 2
    event_support_backlog_fix_churn_relief: Decimal = Decimal("0.0040")
    event_support_backlog_push_quality_loss: int = 2
    event_support_backlog_push_reputation_loss: int = 2
    event_support_backlog_push_user_loss: int = 5

    event_board_scrutiny_weight: int = 4
    event_board_scrutiny_cooldown: int = 5
    event_board_scrutiny_turn_threshold: int = 6
    event_board_scrutiny_pressure_threshold: int = 24
    event_board_scrutiny_debt_threshold: Decimal = Decimal("5000.00")
    event_board_scrutiny_plan_cost: Decimal = Decimal("180.00")
    event_board_scrutiny_plan_pressure_relief: int = 5
    event_board_scrutiny_plan_morale_loss: int = 1
    event_board_scrutiny_growth_cash_gain: Decimal = Decimal("450.00")
    event_board_scrutiny_growth_pressure_gain: int = 4
    event_board_scrutiny_growth_morale_loss: int = 2

    event_renewal_risk_weight: int = 4
    event_renewal_risk_cooldown: int = 5
    event_renewal_risk_turn_threshold: int = 8
    event_renewal_risk_user_threshold: int = 95
    event_renewal_risk_bug_threshold: int = 26
    event_renewal_risk_debt_threshold: int = 34
    event_renewal_stabilize_cost: Decimal = Decimal("320.00")
    event_renewal_stabilize_bug_reduction: int = 5
    event_renewal_stabilize_fit_gain: int = 2
    event_renewal_stabilize_reputation_gain: int = 1
    event_renewal_discount_user_relief: int = 6
    event_renewal_discount_revenue_penalty: Decimal = Decimal("2.00")
    event_renewal_discount_reputation_loss: int = 1

    event_partner_offer_weight: int = 4
    event_partner_offer_cooldown: int = 4
    event_partner_offer_turn_threshold: int = 5
    event_partner_offer_market_fit_threshold: int = 56
    event_partner_offer_quality_threshold: int = 58
    event_partner_offer_cash_gain: Decimal = Decimal("380.00")
    event_partner_offer_user_gain: int = 7
    event_partner_offer_acquisition_gain: Decimal = Decimal("0.0050")
    event_partner_offer_morale_gain: int = 1
    event_partner_offer_focus_quality_gain: int = 1
    event_partner_offer_focus_fit_gain: int = 2

    event_talent_bidding_war_weight: int = 4
    event_talent_bidding_war_cooldown: int = 5
    event_talent_bidding_war_turn_threshold: int = 5
    event_talent_bidding_war_headcount_threshold: int = 2
    event_talent_bidding_war_retain_cost: Decimal = Decimal("280.00")
    event_talent_bidding_war_retain_morale_gain: int = 3
    event_talent_bidding_war_hold_line_morale_loss: int = 2
    event_talent_bidding_war_hold_line_energy_loss: int = 3

    event_platform_breakthrough_weight: int = 4
    event_platform_breakthrough_cooldown: int = 4
    event_platform_breakthrough_quality_threshold: int = 64
    event_platform_breakthrough_debt_threshold: int = 22
    event_platform_breakthrough_productize_cost: Decimal = Decimal("220.00")
    event_platform_breakthrough_quality_gain: int = 2
    event_platform_breakthrough_fit_gain: int = 2
    event_platform_breakthrough_acquisition_gain: Decimal = Decimal("0.0040")
    event_platform_breakthrough_bug_reduction: int = 2
    event_platform_breakthrough_debt_reduction: int = 4
    event_loan_covenant_weight: int = 4
    event_loan_covenant_cooldown: int = 5
    event_loan_covenant_debt_threshold: Decimal = Decimal("6500.00")
    event_loan_covenant_cash_threshold: Decimal = Decimal("4200.00")
    event_loan_covenant_paydown_amount: Decimal = Decimal("1400.00")
    event_loan_covenant_paydown_pressure_relief: int = 3
    event_loan_covenant_renegotiate_cash_gain: Decimal = Decimal("300.00")
    event_loan_covenant_renegotiate_interest_gain: Decimal = Decimal("0.0040")
    event_loan_covenant_renegotiate_pressure_gain: int = 3
    event_down_round_pressure_weight: int = 4
    event_down_round_pressure_cooldown: int = 6
    event_down_round_pressure_turn_threshold: int = 7
    event_down_round_pressure_cash_threshold: Decimal = Decimal("4800.00")
    event_down_round_pressure_investor_threshold: int = 24
    event_down_round_bridge_cash_gain: Decimal = Decimal("2800.00")
    event_down_round_bridge_dilution: Decimal = Decimal("0.0500")
    event_down_round_bridge_pressure_gain: int = 4
    event_down_round_independent_morale_gain: int = 1
    event_down_round_independent_reputation_loss: int = 1

    cash_reserve_milestone_threshold: Decimal = Decimal("12000.00")
    team_growth_milestone_headcount: int = 4
    active_products_milestone_threshold: int = 3
    profitable_streak_turns: int = 3
    multi_segment_milestone_threshold: int = 3
    operations_machine_user_threshold: int = 180
    operations_machine_headcount_threshold: int = 4
    enterprise_footing_user_threshold: int = 65
    debt_free_operator_cash_threshold: Decimal = Decimal("10000.00")
    category_moat_user_threshold: int = 140
    category_moat_quality_threshold: int = 70
    category_moat_market_fit_threshold: int = 68
    talent_bench_headcount_threshold: int = 6
    talent_bench_morale_threshold: int = 70
    platform_credibility_quality_threshold: int = 72
    platform_credibility_debt_threshold: int = 12
    capital_discipline_cash_threshold: Decimal = Decimal("12000.00")
    capital_discipline_debt_cap: Decimal = Decimal("1500.00")
    capital_discipline_dilution_cap: Decimal = Decimal("0.1500")
    rival_resilience_competitor_threshold: int = 3
    rival_resilience_user_threshold: int = 200
    rival_resilience_reputation_threshold: int = 62
    milestone_first_100_users_reputation_gain: int = 2
    milestone_cash_reserve_reputation_gain: int = 1
    milestone_team_growth_reputation_gain: int = 1
    milestone_team_growth_morale_gain: int = 2
    milestone_active_products_reputation_gain: int = 2
    milestone_first_mature_product_cash_gain: Decimal = Decimal("450.00")
    milestone_first_mature_product_reputation_gain: int = 1
    milestone_profitable_streak_reputation_gain: int = 2
    milestone_profitable_streak_morale_gain: int = 2
    milestone_multi_segment_reputation_gain: int = 2
    milestone_operations_machine_reputation_gain: int = 2
    milestone_operations_machine_cash_gain: Decimal = Decimal("350.00")
    milestone_enterprise_footing_reputation_gain: int = 2
    milestone_debt_free_operator_reputation_gain: int = 2
    milestone_debt_free_operator_cash_gain: Decimal = Decimal("300.00")
    milestone_category_moat_reputation_gain: int = 3
    milestone_talent_bench_reputation_gain: int = 2
    milestone_talent_bench_morale_gain: int = 2
    milestone_platform_credibility_reputation_gain: int = 2
    milestone_capital_discipline_reputation_gain: int = 2
    milestone_capital_discipline_cash_gain: Decimal = Decimal("250.00")
    milestone_rival_resilience_reputation_gain: int = 3

    game_over_cash_threshold: Decimal = Decimal("0.00")


BALANCE = BalanceConfig()
