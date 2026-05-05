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
    price_increase_base_multiplier: Decimal = Decimal("1.08")
    price_increase_premium_bonus: Decimal = Decimal("0.02")
    price_increase_budget_penalty: Decimal = Decimal("-0.01")
    price_increase_suite_bonus: Decimal = Decimal("0.02")
    price_increase_market_fit_penalty_by_segment: dict[str, int] = field(
        default_factory=lambda: {
            "indie": 4,
            "startup": 3,
            "smb": 2,
            "enterprise": 1,
        }
    )
    price_increase_packaging_relief: dict[str, int] = field(
        default_factory=lambda: {
            "streamlined": 0,
            "modular": 1,
            "suite": 2,
        }
    )
    price_increase_quality_relief_divisor: int = 24
    price_increase_churn_rate_gain: Decimal = Decimal("0.0040")
    price_increase_account_value_multiplier: Decimal = Decimal("1.05")
    price_increase_catalog_protection_divisor: int = 2
    price_increase_account_satisfaction_loss_by_segment: dict[str, int] = field(
        default_factory=lambda: {
            "indie": 5,
            "startup": 4,
            "smb": 3,
            "enterprise": 2,
        }
    )
    price_increase_account_renewal_health_loss: int = 5
    price_increase_account_invoice_risk_gain: int = 4
    price_increase_account_churn_risk_gain: int = 4
    add_on_campaign_contract_gain: Decimal = Decimal("70.00")
    add_on_campaign_add_on_gain: int = 1
    add_on_campaign_support_load_gain: int = 2
    add_on_campaign_ticket_gain: int = 1
    add_on_campaign_debt_gain: int = 2
    package_catalog_expand_cost: Decimal = Decimal("140.00")
    package_catalog_expand_depth_gain: int = 1
    package_catalog_expand_market_fit_gain: int = 2
    add_on_catalog_expand_cost: Decimal = Decimal("125.00")
    add_on_catalog_expand_depth_gain: int = 1
    add_on_catalog_expand_debt_gain: int = 2
    packaging_catalog_contract_gain_per_depth: Decimal = Decimal("30.00")
    add_on_catalog_contract_gain_per_depth: Decimal = Decimal("22.00")
    packaging_catalog_revenue_multiplier_step: Decimal = Decimal("0.0200")
    add_on_catalog_revenue_multiplier_step: Decimal = Decimal("0.0100")
    packaging_migration_upgrade_contract_gain: Decimal = Decimal("110.00")
    packaging_migration_downgrade_contract_loss: Decimal = Decimal("85.00")
    packaging_migration_add_on_gain: int = 1
    packaging_migration_ticket_relief: int = 2
    packaging_migration_churn_relief: int = 4
    packaging_migration_upgrade_renewal_health_gain: int = 6
    packaging_migration_upgrade_invoice_risk_gain: int = 3
    packaging_migration_downgrade_invoice_risk_relief: int = 5
    packaging_migration_downgrade_support_load_relief: int = 3
    package_catalog_expand_account_health_gain: int = 3
    package_catalog_expand_account_expansion_gain: int = 4
    add_on_catalog_expand_account_expansion_gain: int = 3
    add_on_catalog_expand_account_support_load_gain: int = 1
    packaging_revenue_multiplier: dict[str, Decimal] = field(
        default_factory=lambda: {
            "streamlined": Decimal("1.00"),
            "modular": Decimal("1.05"),
            "suite": Decimal("1.12"),
        }
    )
    packaging_acquisition_bonus: dict[str, int] = field(
        default_factory=lambda: {
            "streamlined": 0,
            "modular": 0,
            "suite": -1,
        }
    )
    packaging_churn_modifier: dict[str, Decimal] = field(
        default_factory=lambda: {
            "streamlined": Decimal("0.0000"),
            "modular": Decimal("0.0010"),
            "suite": Decimal("-0.0040"),
        }
    )
    packaging_support_cost_multiplier: dict[str, Decimal] = field(
        default_factory=lambda: {
            "streamlined": Decimal("1.00"),
            "modular": Decimal("1.00"),
            "suite": Decimal("1.10"),
        }
    )
    packaging_add_on_bonus: dict[str, int] = field(
        default_factory=lambda: {
            "streamlined": 0,
            "modular": 2,
            "suite": 3,
        }
    )
    packaging_enterprise_probability_bonus: dict[str, int] = field(
        default_factory=lambda: {
            "streamlined": 0,
            "modular": 1,
            "suite": 3,
        }
    )
    packaging_market_fit_shift_by_segment: dict[str, dict[str, int]] = field(
        default_factory=lambda: {
            "streamlined": {"indie": 2, "startup": 1, "smb": 0, "enterprise": -2},
            "modular": {"indie": 0, "startup": 1, "smb": 1, "enterprise": 1},
            "suite": {"indie": -2, "startup": -1, "smb": 1, "enterprise": 2},
        }
    )
    packaging_support_cost_depth_step: Decimal = Decimal("0.0100")
    packaging_catalog_acquisition_depth_divisor: int = 2
    add_on_catalog_acquisition_depth_divisor: int = 3
    packaging_churn_relief_depth_divisor: int = 2
    package_catalog_enterprise_upgrade_threshold: int = 3
    add_on_catalog_growth_upgrade_threshold: int = 2
    add_on_campaign_min_catalog_depth: int = 1
    packaging_expansion_interval: int = 3
    packaging_expansion_satisfaction_threshold: int = 74
    packaging_expansion_onboarding_threshold: int = 68
    packaging_expansion_ticket_threshold: int = 6
    packaging_expansion_add_on_gain: int = 1
    packaging_expansion_contract_gain: Decimal = Decimal("90.00")
    packaging_expansion_package_depth_bonus_divisor: int = 2
    packaging_expansion_add_on_depth_bonus_divisor: int = 2
    packaging_expansion_enterprise_seat_gain: int = 2
    packaging_expansion_usage_gain: int = 4

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
    employee_trait_salary_multiplier: dict[str, Decimal] = field(
        default_factory=lambda: {
            "steady_operator": Decimal("1.00"),
            "fast_learner": Decimal("0.94"),
            "expensive_expert": Decimal("1.28"),
            "burnout_risk": Decimal("0.90"),
        }
    )
    employee_trait_productivity_bonus: dict[str, int] = field(
        default_factory=lambda: {
            "steady_operator": 0,
            "fast_learner": 2,
            "expensive_expert": 8,
            "burnout_risk": 5,
        }
    )
    employee_training_cost: Decimal = Decimal("180.00")
    employee_training_experience_gain: int = 12
    employee_training_readiness_gain: int = 16
    employee_training_productivity_gain: int = 3
    employee_training_morale_gain: int = 4
    employee_training_attrition_relief: int = 8
    employee_training_performance_gain: int = 5
    employee_progression_energy_threshold: int = 60
    employee_assigned_experience_gain: int = 6
    employee_unassigned_experience_gain: int = 2
    employee_promotion_readiness_threshold: int = 70
    employee_promotion_readiness_reset: int = 18
    employee_promotion_salary_multiplier: dict[str, Decimal] = field(
        default_factory=lambda: {
            "mid": Decimal("1.12"),
            "senior": Decimal("1.18"),
        }
    )
    employee_promotion_productivity_gain: dict[str, int] = field(
        default_factory=lambda: {
            "mid": 5,
            "senior": 7,
        }
    )
    employee_promotion_morale_gain: int = 8
    employee_promotion_attrition_relief: int = 14
    employee_promotion_performance_gain: int = 6
    employee_attrition_morale_risk_gain: int = 7
    employee_attrition_energy_risk_gain: int = 9
    employee_attrition_negative_cash_flow_risk_gain: int = 4
    employee_attrition_recovery_relief: int = 6
    employee_high_attrition_risk_threshold: int = 65
    employee_starting_performance_rating: int = 62
    employee_performance_good_threshold: int = 70
    employee_performance_low_threshold: int = 42
    employee_performance_energy_bonus_threshold: int = 68
    employee_performance_morale_bonus_threshold: int = 68
    employee_performance_gain: int = 3
    employee_performance_loss: int = 4
    employee_performance_recovery_gain: int = 2
    employee_underperformance_streak_warning: int = 2
    employee_underperformance_attrition_gain: int = 3
    employee_underperformance_morale_loss: int = 1
    employee_promotion_pressure_tenure_threshold: int = 4
    employee_promotion_pressure_attrition_gain: int = 5
    employee_promotion_pressure_morale_loss: int = 1
    employee_compensation_pressure_tenure_threshold: int = 4
    employee_compensation_pressure_salary_ratio_floor: Decimal = Decimal("0.9200")
    employee_compensation_pressure_attrition_gain: int = 4
    employee_compensation_pressure_morale_loss: int = 2
    employee_comp_review_min_cash_buffer: Decimal = Decimal("600.00")
    employee_comp_review_min_raise: Decimal = Decimal("60.00")
    employee_comp_review_salary_ratio_target: Decimal = Decimal("1.0000")
    employee_comp_review_morale_gain: int = 6
    employee_comp_review_attrition_relief: int = 12
    employee_comp_review_performance_gain: int = 2
    employee_resignation_attrition_threshold: int = 82
    employee_resignation_morale_threshold: int = 38
    employee_resignation_energy_threshold: int = 32
    employee_resignation_chance_floor: int = 18
    employee_resignation_attrition_weight_divisor: int = 2
    employee_resignation_streak_bonus: int = 6
    team_build_bonus_divisor: int = 44
    team_stability_bonus_divisor: int = 48
    team_market_fit_bonus_divisor: int = 52
    team_acquisition_bonus_divisor: int = 45
    team_reputation_bonus_divisor: int = 75
    team_debt_bonus_divisor: int = 38
    team_coordination_bonus_divisor: int = 36
    team_burnout_protection_divisor: int = 55
    management_product_manager_capacity: int = 4
    management_senior_capacity: int = 3
    management_leadership_divisor: int = 25
    management_coordination_bonus_per_managed_pair: int = 1
    management_same_product_bonus_divisor: int = 2
    management_overload_coordination_penalty_divisor: int = 2
    management_unmanaged_energy_penalty: int = 1
    management_unmanaged_morale_penalty: int = 1
    management_attrition_relief: int = 5
    management_org_drag_threshold: int = 2
    management_reorg_cost: Decimal = Decimal("160.00")
    management_reorg_attrition_relief: int = 8
    management_reorg_energy_gain: int = 4
    management_reorg_morale_penalty: int = 1
    management_team_lead_capacity: int = 2
    management_team_lead_leadership_threshold: int = 60
    management_team_lead_coordination_bonus: int = 1
    management_team_lead_overload_relief: int = 1
    management_succession_high_risk_threshold: int = 12
    management_succession_energy_threshold: int = 45
    management_succession_morale_threshold: int = 45
    management_succession_attrition_threshold: int = 55
    management_overload_report_energy_penalty: int = 1
    management_succession_report_energy_penalty: int = 1
    management_succession_report_morale_penalty: int = 1
    management_succession_manager_energy_penalty: int = 1
    management_succession_manager_morale_penalty: int = 1
    management_layer_drag_threshold: int = 2
    management_layer_drag_per_layer: int = 2
    management_span_soft_cap: int = 4
    management_succession_review_cost: Decimal = Decimal("190.00")
    management_succession_review_direct_report_min: int = 2
    management_succession_review_backup_leadership_threshold: int = 54
    management_succession_review_leadership_gain: int = 8
    management_succession_review_morale_gain: int = 4
    management_succession_review_energy_gain: int = 3
    management_succession_review_attrition_relief: int = 8
    management_succession_review_report_morale_gain: int = 2
    management_succession_review_report_attrition_relief: int = 3
    management_succession_review_backup_morale_gain: int = 3

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
    roadmap_ai_trust_quality_bonus: int = 1
    roadmap_ai_trust_market_fit_bonus: int = 2
    roadmap_ai_trust_debt_bonus: int = 3
    roadmap_ai_trust_reputation_bonus: int = 2
    roadmap_ai_trust_operating_cost_modifier: Decimal = Decimal("65.00")
    roadmap_ai_trust_competitor_relief: int = 2
    roadmap_community_growth_acquisition_bonus: int = 3
    roadmap_community_growth_market_fit_bonus: int = 1
    roadmap_community_growth_reputation_bonus: int = 1
    roadmap_community_growth_feature_risk_modifier: int = 1
    roadmap_community_growth_operating_cost_modifier: Decimal = Decimal("55.00")
    roadmap_enterprise_sales_quality_bonus: int = 1
    roadmap_enterprise_sales_market_fit_bonus: int = 3
    roadmap_enterprise_sales_acquisition_bonus: int = -1
    roadmap_enterprise_sales_reputation_bonus: int = 1
    roadmap_enterprise_sales_operating_cost_modifier: Decimal = Decimal("120.00")
    roadmap_enterprise_sales_competitor_relief: int = 2

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
    operations_ticket_load_divisor: int = 18
    operations_sla_risk_load_bonus: int = 2
    operations_account_ticket_penalty: int = 2
    operations_account_sla_penalty: int = 4
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
            "ai_fast_follower": 1,
            "governance_giant": 2,
            "ecosystem_broker": 1,
            "open_source_challenger": 1,
            "regulatory_incumbent": 2,
            "platform_consolidator": 2,
            "enterprise_sales_machine": 2,
            "data_quality_native": 2,
            "release_velocity_chaser": 1,
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
            "ai_fast_follower": {"feature_sprint": 3, "hold": -1},
            "governance_giant": {"hold": 2, "feature_sprint": 1, "discount_push": -1},
            "ecosystem_broker": {"discount_push": 1, "feature_sprint": 2},
            "open_source_challenger": {"feature_sprint": 2, "discount_push": 1, "hold": -1},
            "regulatory_incumbent": {"hold": 3, "retrench": -1},
            "platform_consolidator": {"discount_push": 2, "feature_sprint": 1},
            "enterprise_sales_machine": {"hold": 2, "discount_push": 1},
            "data_quality_native": {"feature_sprint": 2, "hold": 1},
            "release_velocity_chaser": {"feature_sprint": 3, "hold": -1},
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
            "ai_fast_follower": -2,
            "governance_giant": 4,
            "ecosystem_broker": -3,
            "open_source_challenger": -2,
            "regulatory_incumbent": 5,
            "platform_consolidator": -2,
            "enterprise_sales_machine": 2,
            "data_quality_native": 3,
            "release_velocity_chaser": -3,
        }
    )

    quarter_plan_revenue_growth_by_roadmap: dict[str, Decimal] = field(
        default_factory=lambda: {
            "balanced_execution": Decimal("1.08"),
            "growth_push": Decimal("1.16"),
            "platform_rebuild": Decimal("1.04"),
            "premium_expansion": Decimal("1.10"),
            "portfolio_consolidation": Decimal("1.05"),
            "ai_trust_program": Decimal("1.09"),
            "community_growth": Decimal("1.13"),
            "enterprise_sales_push": Decimal("1.12"),
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
    finance_refinance_min_debt: Decimal = Decimal("1800.00")
    finance_refinance_cash_infusion: Decimal = Decimal("1200.00")
    finance_refinance_interest_rate_gain: Decimal = Decimal("0.0075")
    finance_refinance_covenant_relief: int = 8
    finance_refinance_pressure_gain: int = 2
    finance_refinance_board_confidence_loss: int = 2
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
    finance_board_runway_target: int = 8
    finance_forecast_history_window: int = 3
    finance_forecast_conservative_drag: Decimal = Decimal("0.18")
    finance_forecast_aggressive_relief: Decimal = Decimal("0.15")
    finance_covenant_risk_debt_threshold: Decimal = Decimal("5200.00")
    finance_covenant_risk_cash_buffer: Decimal = Decimal("2600.00")
    finance_covenant_risk_gain: int = 8
    finance_covenant_risk_relief: int = 5
    finance_board_target_miss_gain: int = 1
    finance_board_target_relief: int = 1
    finance_board_covenant_confidence_penalty_divisor: int = 16
    finance_board_miss_confidence_penalty: int = 1
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
    competitor_intel_limit: int = 12

    release_stability_required_progress: int = 4
    release_minor_required_progress: int = 6
    release_major_required_progress: int = 9
    release_work_base_progress: int = 3
    release_stability_cash_cost: Decimal = Decimal("180.00")
    release_minor_cash_cost: Decimal = Decimal("260.00")
    release_major_cash_cost: Decimal = Decimal("520.00")

    sales_deal_base_value: Decimal = Decimal("950.00")
    sales_deal_action_cost: Decimal = Decimal("160.00")
    sales_deal_probability_gain: int = 16
    sales_deal_close_probability_threshold: int = 62
    sales_deal_customer_satisfaction: int = 66
    sales_deal_customer_expansion: int = 54
    sales_deal_default_add_on_commitment_by_segment: dict[str, int] = field(
        default_factory=lambda: {
            "indie": 0,
            "startup": 1,
            "smb": 2,
            "enterprise": 3,
        }
    )
    sales_deal_default_discount_rate_by_segment: dict[str, Decimal] = field(
        default_factory=lambda: {
            "indie": Decimal("0.0000"),
            "startup": Decimal("0.0200"),
            "smb": Decimal("0.0300"),
            "enterprise": Decimal("0.0400"),
        }
    )
    sales_deal_billing_model_by_segment: dict[str, str] = field(
        default_factory=lambda: {
            "indie": "flat",
            "startup": "usage_based",
            "smb": "seat_based",
            "enterprise": "seat_based",
        }
    )
    sales_deal_default_seat_commitment_by_segment: dict[str, int] = field(
        default_factory=lambda: {
            "indie": 0,
            "startup": 0,
            "smb": 12,
            "enterprise": 24,
        }
    )
    sales_deal_default_usage_commitment_by_segment: dict[str, int] = field(
        default_factory=lambda: {
            "indie": 12,
            "startup": 32,
            "smb": 18,
            "enterprise": 10,
        }
    )
    sales_deal_user_gain_by_segment: dict[str, int] = field(
        default_factory=lambda: {
            "indie": 9,
            "startup": 7,
            "smb": 5,
            "enterprise": 3,
        }
    )

    roadmap_project_required_progress: int = 8
    roadmap_project_work_progress: int = 3
    roadmap_project_work_cost: Decimal = Decimal("220.00")
    roadmap_project_required_progress_by_type: dict[str, int] = field(
        default_factory=lambda: {
            "platform_rebuild": 8,
            "enterprise_certification": 10,
            "marketplace_launch": 7,
            "sales_playbook": 6,
        }
    )
    roadmap_project_epic_count_by_type: dict[str, int] = field(
        default_factory=lambda: {
            "platform_rebuild": 3,
            "enterprise_certification": 4,
            "marketplace_launch": 3,
            "sales_playbook": 2,
        }
    )
    roadmap_project_deadline_turns_by_type: dict[str, int] = field(
        default_factory=lambda: {
            "platform_rebuild": 3,
            "enterprise_certification": 4,
            "marketplace_launch": 3,
            "sales_playbook": 2,
        }
    )
    roadmap_project_delivery_risk_by_type: dict[str, int] = field(
        default_factory=lambda: {
            "platform_rebuild": 26,
            "enterprise_certification": 32,
            "marketplace_launch": 24,
            "sales_playbook": 18,
        }
    )
    roadmap_project_dependency_by_type: dict[str, str] = field(
        default_factory=lambda: {
            "platform_rebuild": "",
            "enterprise_certification": "platform_rebuild",
            "marketplace_launch": "platform_rebuild",
            "sales_playbook": "",
        }
    )
    roadmap_project_late_progress_penalty: int = 1
    roadmap_project_deadline_miss_risk_gain: int = 8
    roadmap_project_deadline_miss_reputation_penalty: int = 1
    roadmap_project_deadline_miss_board_penalty: int = 2

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
    event_key_account_expansion_weight: int = 4
    event_key_account_expansion_cooldown: int = 5
    event_key_account_expansion_satisfaction_threshold: int = 66
    event_key_account_expansion_potential_threshold: int = 55
    event_key_account_success_plan_cost: Decimal = Decimal("260.00")
    event_key_account_success_plan_contract_gain: Decimal = Decimal("180.00")
    event_key_account_success_plan_satisfaction_gain: int = 6
    event_key_account_referral_user_gain: int = 9
    event_key_account_referral_reputation_gain: int = 1
    event_key_account_referral_satisfaction_loss: int = 3
    event_security_audit_weight: int = 4
    event_security_audit_cooldown: int = 5
    event_security_audit_user_threshold: int = 35
    event_security_audit_debt_threshold: int = 24
    event_security_audit_fund_cost: Decimal = Decimal("360.00")
    event_security_audit_debt_reduction: int = 7
    event_security_audit_bug_reduction: int = 4
    event_security_audit_reputation_gain: int = 2
    event_security_audit_board_gain: int = 3
    event_security_audit_defer_reputation_loss: int = 2
    event_security_audit_defer_churn_increase: Decimal = Decimal("0.0050")
    event_security_audit_defer_account_risk_gain: int = 8
    event_enterprise_sales_cycle_weight: int = 4
    event_enterprise_sales_cycle_cooldown: int = 5
    event_enterprise_sales_turn_threshold: int = 4
    event_enterprise_sales_fit_threshold: int = 54
    event_enterprise_sales_user_threshold: int = 24
    event_enterprise_poc_cost: Decimal = Decimal("420.00")
    event_enterprise_poc_user_gain: int = 10
    event_enterprise_poc_fit_gain: int = 3
    event_enterprise_poc_revenue_gain: Decimal = Decimal("4.00")
    event_enterprise_poc_energy_loss: int = 5
    event_enterprise_walkaway_reputation_gain: int = 1
    event_enterprise_walkaway_board_gain: int = 2
    event_product_launch_window_weight: int = 5
    event_product_launch_window_cooldown: int = 4
    event_product_launch_quality_threshold: int = 60
    event_product_launch_fit_threshold: int = 50
    event_product_launch_feature_threshold: int = 3
    event_product_launch_campaign_cost: Decimal = Decimal("300.00")
    event_product_launch_user_gain: int = 14
    event_product_launch_acquisition_gain: Decimal = Decimal("0.0060")
    event_product_launch_bug_increase: int = 2
    event_product_launch_soft_user_gain: int = 5
    event_product_launch_soft_quality_gain: int = 1
    event_platform_outage_weight: int = 5
    event_platform_outage_cooldown: int = 5
    event_platform_outage_user_threshold: int = 120
    event_platform_outage_bug_threshold: int = 30
    event_platform_outage_debt_threshold: int = 30
    event_platform_outage_response_cost: Decimal = Decimal("420.00")
    event_platform_outage_bug_reduction: int = 8
    event_platform_outage_reputation_loss: int = 1
    event_platform_outage_energy_loss: int = 10
    event_platform_outage_delay_user_loss: int = 9
    event_platform_outage_delay_bug_gain: int = 5
    event_platform_outage_delay_reputation_loss: int = 4
    event_competitor_acquisition_weight: int = 3
    event_competitor_acquisition_cooldown: int = 6
    event_competitor_acquisition_turn_threshold: int = 5
    event_competitor_acquisition_funding_threshold: int = 2
    event_competitor_acquisition_momentum_threshold: int = 72
    event_competitor_acquisition_differentiate_cost: Decimal = Decimal("280.00")
    event_competitor_acquisition_quality_gain: int = 2
    event_competitor_acquisition_fit_gain: int = 2
    event_competitor_acquisition_partner_user_gain: int = 6
    event_competitor_acquisition_partner_reputation_gain: int = 1
    event_regulatory_shift_weight: int = 4
    event_regulatory_shift_cooldown: int = 6
    event_regulatory_shift_turn_threshold: int = 6
    event_regulatory_shift_cost: Decimal = Decimal("340.00")
    event_regulatory_shift_debt_reduction: int = 5
    event_regulatory_shift_fit_gain: int = 2
    event_regulatory_shift_reputation_gain: int = 2
    event_regulatory_shift_board_gain: int = 2
    event_regulatory_shift_wait_reputation_loss: int = 1
    event_regulatory_shift_wait_churn_increase: Decimal = Decimal("0.0040")
    event_regulatory_shift_wait_account_risk_gain: int = 6
    event_chain_recent_window_turns: int = 4
    event_audit_followup_weight: int = 3
    event_audit_followup_cooldown: int = 6
    event_audit_followup_cost: Decimal = Decimal("260.00")
    event_audit_followup_debt_reduction: int = 4
    event_audit_followup_reputation_gain: int = 2
    event_audit_followup_board_gain: int = 2
    event_audit_followup_defer_risk_gain: int = 5
    event_launch_aftershock_weight: int = 3
    event_launch_aftershock_cooldown: int = 5
    event_launch_aftershock_stabilize_cost: Decimal = Decimal("240.00")
    event_launch_aftershock_bug_reduction: int = 3
    event_launch_aftershock_quality_gain: int = 1
    event_launch_aftershock_chase_user_gain: int = 8
    event_launch_aftershock_chase_bug_gain: int = 4
    event_launch_aftershock_chase_energy_loss: int = 4
    event_procurement_delay_weight: int = 3
    event_procurement_delay_cooldown: int = 6
    event_procurement_delay_proof_cost: Decimal = Decimal("300.00")
    event_procurement_delay_user_gain: int = 5
    event_procurement_delay_revenue_gain: Decimal = Decimal("3.00")
    event_procurement_delay_wait_reputation_loss: int = 1
    event_procurement_delay_wait_account_risk_gain: int = 5
    event_support_meltdown_weight: int = 3
    event_support_meltdown_cooldown: int = 6
    event_support_meltdown_backlog_threshold: int = 18
    event_support_meltdown_escalation_threshold: int = 4
    event_support_meltdown_staff_cost: Decimal = Decimal("240.00")
    event_support_meltdown_staffing_gain: int = 1
    event_support_meltdown_backlog_relief: int = 8
    event_support_meltdown_escalation_relief: int = 2
    event_support_meltdown_morale_loss: int = 1
    event_support_meltdown_ration_reputation_loss: int = 2
    event_support_meltdown_ration_account_risk_gain: int = 6
    event_support_meltdown_ration_queue_gain: int = 4
    event_board_reckoning_weight: int = 3
    event_board_reckoning_cooldown: int = 6
    event_board_reckoning_pressure_threshold: int = 30
    event_board_reckoning_cut_cost: Decimal = Decimal("160.00")
    event_board_reckoning_cut_pressure_relief: int = 4
    event_board_reckoning_cut_confidence_gain: int = 3
    event_board_reckoning_cut_growth_penalty: Decimal = Decimal("0.0030")
    event_board_reckoning_defend_cash_gain: Decimal = Decimal("220.00")
    event_board_reckoning_defend_pressure_gain: int = 3
    event_board_reckoning_defend_confidence_loss: int = 2
    event_board_reckoning_defend_growth_gain: Decimal = Decimal("0.0030")
    event_partner_qbr_weight: int = 3
    event_partner_qbr_cooldown: int = 5
    event_partner_qbr_enablement_cost: Decimal = Decimal("180.00")
    event_partner_qbr_quality_gain: int = 3
    event_partner_qbr_risk_relief: int = 5
    event_partner_qbr_conflict_relief: int = 6
    event_partner_qbr_user_gain: int = 5
    event_partner_qbr_pause_user_loss: int = 4
    event_partner_qbr_pause_conflict_relief: int = 8
    event_partner_qbr_pause_pressure_relief: int = 2
    event_partner_breakdown_weight: int = 3
    event_partner_breakdown_cooldown: int = 6
    event_partner_breakdown_fatigue_threshold: int = 36
    event_partner_breakdown_recovery_cost: Decimal = Decimal("220.00")
    event_partner_breakdown_conflict_relief: int = 8
    event_partner_breakdown_risk_relief: int = 6
    event_partner_breakdown_quality_gain: int = 2
    event_partner_breakdown_pause_user_loss: int = 6
    event_partner_breakdown_pause_pressure_relief: int = 3
    event_board_recovery_window_weight: int = 3
    event_board_recovery_window_cooldown: int = 6
    event_board_recovery_window_cash_cost: Decimal = Decimal("260.00")
    event_board_recovery_window_confidence_gain: int = 4
    event_board_recovery_window_score_gain: int = 5
    event_board_recovery_window_risk_relief: int = 4
    event_board_recovery_window_scope_pressure_relief: int = 4
    event_board_recovery_window_scope_reputation_loss: int = 1
    event_board_recovery_window_scope_focus_gain: int = 5
    event_capital_market_freeze_weight: int = 3
    event_capital_market_freeze_cooldown: int = 6
    event_capital_market_freeze_pressure_threshold: int = 26
    event_capital_market_freeze_cash_gain: Decimal = Decimal("1600.00")
    event_capital_market_freeze_dilution: Decimal = Decimal("0.0300")
    event_capital_market_freeze_pressure_relief: int = 2
    event_capital_market_freeze_freeze_morale_loss: int = 2
    event_capital_market_freeze_freeze_covenant_relief: int = 1
    event_succession_gap_weight: int = 3
    event_succession_gap_cooldown: int = 6
    event_succession_gap_risk_threshold: int = 12
    event_succession_gap_leadership_gain: int = 6
    event_succession_gap_attrition_relief: int = 8
    event_succession_gap_morale_gain: int = 5
    event_succession_gap_wait_attrition_gain: int = 6
    event_succession_gap_wait_morale_loss: int = 4
    event_partner_renegotiation_weight: int = 3
    event_partner_renegotiation_cooldown: int = 6
    event_partner_renegotiation_fatigue_threshold: int = 30
    event_partner_renegotiation_rev_share_penalty: Decimal = Decimal("0.0200")
    event_partner_renegotiation_conflict_relief: int = 9
    event_partner_renegotiation_risk_relief: int = 7
    event_partner_renegotiation_quality_gain: int = 2
    event_partner_renegotiation_hold_line_user_loss: int = 5
    event_partner_renegotiation_hold_line_pressure_gain: int = 2
    event_strategic_crossroads_weight: int = 3
    event_strategic_crossroads_cooldown: int = 6
    event_strategic_crossroads_readiness_threshold: int = 62
    event_strategic_crossroads_process_cost: Decimal = Decimal("320.00")
    event_strategic_crossroads_process_confidence_gain: int = 4
    event_strategic_crossroads_process_score_gain: int = 4
    event_strategic_crossroads_process_pressure_gain: int = 2
    event_strategic_crossroads_independence_reputation_gain: int = 2
    event_strategic_crossroads_independence_pressure_relief: int = 3
    event_strategic_crossroads_independence_team_gain: int = 4

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

    key_account_user_threshold: int = 90
    key_account_enterprise_user_threshold: int = 18
    key_account_contract_user_divisor: int = 3
    key_account_min_contract_value: Decimal = Decimal("280.00")
    key_account_max_contract_value: Decimal = Decimal("1800.00")
    key_account_base_satisfaction: int = 58
    key_account_quality_divisor: int = 8
    key_account_bug_divisor: int = 10
    key_account_debt_divisor: int = 15
    key_account_renewal_interval: int = 4
    key_account_monthly_renewal_interval: int = 2
    key_account_satisfaction_good_threshold: int = 68
    key_account_satisfaction_bad_threshold: int = 42
    key_account_churn_threshold: int = 78
    key_account_expansion_contract_gain: Decimal = Decimal("140.00")
    key_account_renewal_churn_user_loss: int = 8
    key_account_status_at_risk_threshold: int = 55
    key_account_satisfaction_delta_cap: int = 5
    key_account_churn_risk_relief: int = 7
    key_account_churn_risk_gain: int = 9
    key_account_discount_risk_divisor: Decimal = Decimal("0.0200")
    key_account_support_load_bug_divisor: int = 12
    key_account_support_load_quality_relief_divisor: int = 18
    key_account_support_load_cs_relief: int = 2
    key_account_support_load_cap: int = 8
    key_account_onboarding_good_threshold: int = 70
    key_account_onboarding_bad_threshold: int = 45
    contract_add_on_unit_revenue_by_plan: dict[str, Decimal] = field(
        default_factory=lambda: {
            "budget": Decimal("18.00"),
            "standard": Decimal("28.00"),
            "premium": Decimal("40.00"),
        }
    )
    subscription_default_package_by_segment: dict[str, str] = field(
        default_factory=lambda: {
            "indie": "starter",
            "startup": "starter",
            "smb": "growth",
            "enterprise": "enterprise_suite",
        }
    )
    subscription_package_recurring_bonus: dict[str, Decimal] = field(
        default_factory=lambda: {
            "starter": Decimal("0.00"),
            "growth": Decimal("55.00"),
            "enterprise_suite": Decimal("140.00"),
        }
    )
    subscription_package_support_burden: dict[str, int] = field(
        default_factory=lambda: {
            "starter": 0,
            "growth": 2,
            "enterprise_suite": 4,
        }
    )
    contract_default_add_on_commitment_by_segment: dict[str, int] = field(
        default_factory=lambda: {
            "indie": 0,
            "startup": 1,
            "smb": 2,
            "enterprise": 3,
        }
    )
    contract_invoice_risk_monthly_gain: int = 4
    contract_invoice_risk_discount_gain_divisor: Decimal = Decimal("0.0200")
    contract_invoice_risk_ticket_divisor: int = 5
    contract_invoice_risk_prepay_relief: int = 5
    contract_invoice_risk_onboarding_relief_divisor: int = 18
    contract_invoice_risk_threshold: int = 58
    contract_invoice_risk_severe_threshold: int = 78
    contract_invoice_risk_churn_gain: int = 5
    contract_invoice_risk_satisfaction_loss: int = 2
    contract_failed_payment_monthly_gain: int = 4
    contract_failed_payment_invoice_divisor: int = 18
    contract_failed_payment_discount_divisor: Decimal = Decimal("0.0300")
    contract_failed_payment_health_relief_divisor: int = 16
    contract_failed_payment_prepay_relief: int = 6
    contract_failed_payment_threshold: int = 60
    contract_failed_payment_dunning_limit: int = 3
    contract_failed_payment_dunning_satisfaction_loss: int = 3
    contract_failed_payment_churn_gain: int = 6
    contract_add_on_expansion_gain: int = 1
    contract_add_on_downgrade_loss: int = 1
    contract_seat_unit_revenue: Decimal = Decimal("18.00")
    contract_usage_unit_revenue: Decimal = Decimal("4.00")
    contract_default_billing_model_by_segment: dict[str, str] = field(
        default_factory=lambda: {
            "indie": "flat",
            "startup": "usage_based",
            "smb": "seat_based",
            "enterprise": "seat_based",
        }
    )
    contract_default_seat_commitment_by_segment: dict[str, int] = field(
        default_factory=lambda: {
            "indie": 0,
            "startup": 0,
            "smb": 10,
            "enterprise": 20,
        }
    )
    contract_default_usage_commitment_by_segment: dict[str, int] = field(
        default_factory=lambda: {
            "indie": 14,
            "startup": 28,
            "smb": 12,
            "enterprise": 8,
        }
    )
    contract_ticket_bug_divisor: int = 10
    contract_ticket_quality_relief_divisor: int = 22
    contract_ticket_close_base_relief: int = 2
    contract_sla_ticket_divisor: int = 8
    contract_sla_support_divisor: int = 16
    contract_sla_onboarding_relief_divisor: int = 18
    contract_sla_risk_threshold: int = 55
    contract_sla_severe_threshold: int = 75
    contract_sla_breach_churn_risk_gain: int = 6
    contract_sla_breach_satisfaction_loss: int = 3
    contract_seat_expansion_gain: int = 4
    contract_usage_expansion_gain: int = 8
    contract_seat_downgrade_loss: int = 3
    contract_usage_downgrade_loss: int = 6
    contract_downgrade_satisfaction_threshold: int = 48
    contract_flat_expansion_contract_gain: Decimal = Decimal("95.00")
    contract_flat_downgrade_contract_loss: Decimal = Decimal("70.00")
    customer_success_investment_cost: Decimal = Decimal("240.00")
    customer_success_onboarding_gain: int = 8
    customer_success_satisfaction_gain: int = 6
    customer_success_support_relief: int = 5
    customer_success_churn_risk_relief: int = 8
    customer_success_ticket_relief: int = 4
    customer_success_sla_relief: int = 8
    customer_success_knowledge_base_gain: int = 5
    customer_success_automation_gain: int = 3
    retention_play_cost: Decimal = Decimal("180.00")
    retention_discount_rate_increase: Decimal = Decimal("0.0200")
    retention_satisfaction_gain: int = 9
    retention_onboarding_gain: int = 6
    retention_support_relief: int = 6
    retention_churn_risk_relief: int = 14
    retention_ticket_relief: int = 6
    retention_sla_relief: int = 10
    key_account_score_value_divisor: Decimal = Decimal("250.00")
    key_account_valuation_multiplier: Decimal = Decimal("2.50")

    board_confidence_positive_cashflow_gain: int = 2
    board_confidence_negative_cashflow_loss: int = 2
    board_confidence_pressure_divisor: int = 18
    board_confidence_low_threshold: int = 32
    board_confidence_high_threshold: int = 72
    board_confidence_score_divisor: int = 10
    board_review_interval: int = 4
    board_review_pressure_gain: int = 5
    board_review_confidence_gain: int = 3
    board_review_confidence_loss: int = 4
    board_pressure_warning_threshold: int = 48
    governance_risk_warning_threshold: int = 44
    governance_risk_relief: int = 3
    board_pressure_relief: int = 4
    board_warning_level_two_pressure_threshold: int = 62
    board_warning_level_three_pressure_threshold: int = 78
    board_warning_level_two_risk_threshold: int = 58
    board_warning_level_three_risk_threshold: int = 74
    board_warning_level_two_confidence_threshold: int = 24
    board_warning_level_one_confidence_threshold: int = 38
    board_ask_miss_penalty: int = 1
    board_ask_hit_relief: int = 1
    board_score_profitability_target: int = 62
    board_score_reliability_target: int = 62
    board_score_team_health_target: int = 62
    board_score_portfolio_focus_target: int = 58
    board_recovery_plan_cost: Decimal = Decimal("220.00")
    board_recovery_turns: int = 3
    board_recovery_pressure_relief: int = 4
    board_recovery_governance_relief: int = 3
    board_recovery_confidence_gain: int = 2
    board_recovery_miss_penalty: int = 2
    board_resolution_window_turns: int = 2
    board_resolution_expiry_pressure_gain: int = 4
    board_resolution_expiry_risk_gain: int = 3
    board_resolution_expiry_confidence_loss: int = 2
    governance_crisis_level_two_miss_threshold: int = 2
    governance_crisis_level_three_miss_threshold: int = 4
    governance_crisis_pressure_gain_per_level: int = 2
    governance_crisis_risk_gain_per_level: int = 2
    governance_crisis_confidence_loss_per_level: int = 1
    board_response_min_pressure_threshold: int = 28
    board_response_confidence_gain: int = 2
    board_response_governance_relief: int = 3
    board_response_profitability_cash_gain: Decimal = Decimal("180.00")
    board_response_profitability_growth_penalty: Decimal = Decimal("0.0040")
    board_response_profitability_morale_loss: int = 1
    board_response_profitability_pressure_relief: int = 5
    board_response_reliability_cost: Decimal = Decimal("220.00")
    board_response_reliability_backlog_relief: int = 8
    board_response_reliability_escalation_relief: int = 3
    board_response_reliability_bug_relief: int = 3
    board_response_team_health_cost: Decimal = Decimal("180.00")
    board_response_team_health_energy_gain: int = 8
    board_response_team_health_morale_gain: int = 6
    board_response_team_health_attrition_relief: int = 10
    board_response_portfolio_focus_pressure_relief: int = 6
    board_response_portfolio_focus_reputation_loss: int = 1
    board_resolution_restructure_pressure_gain: int = 6
    board_resolution_reset_pressure_gain: int = 2
    board_resolution_growth_pressure_relief: int = 3
    board_tradeoff_pressure_relief: int = 1
    board_tradeoff_confidence_gain: int = 1
    board_tradeoff_profitability_growth_penalty: Decimal = Decimal("0.0030")
    board_tradeoff_reliability_growth_penalty: Decimal = Decimal("0.0020")
    board_tradeoff_reliability_backlog_relief: int = 3
    board_tradeoff_reliability_escalation_relief: int = 1
    board_tradeoff_reliability_bug_relief: int = 2
    board_tradeoff_team_health_energy_gain: int = 4
    board_tradeoff_team_health_morale_gain: int = 4
    board_tradeoff_team_health_attrition_relief: int = 4
    board_tradeoff_team_health_growth_penalty: Decimal = Decimal("0.0015")
    board_tradeoff_portfolio_focus_quality_gain: int = 2
    board_tradeoff_portfolio_focus_debt_relief: int = 2
    board_tradeoff_portfolio_focus_secondary_fit_penalty: int = 2
    board_tradeoff_portfolio_focus_secondary_growth_penalty: Decimal = Decimal("0.0020")
    board_scorecard_severe_gap_threshold: int = 10
    board_scorecard_profitability_growth_penalty: Decimal = Decimal("0.0030")
    board_scorecard_profitability_pressure_gain: int = 2
    board_scorecard_reliability_backlog_penalty: int = 4
    board_scorecard_reliability_escalation_penalty: int = 1
    board_scorecard_team_energy_loss: int = 3
    board_scorecard_team_morale_loss: int = 3
    board_scorecard_team_attrition_gain: int = 4
    board_scorecard_portfolio_fit_penalty: int = 2
    board_scorecard_portfolio_growth_penalty: Decimal = Decimal("0.0020")
    board_recovery_plan_reliability_automation_gain: int = 4
    board_recovery_plan_reliability_knowledge_gain: int = 4
    board_recovery_plan_reliability_sla_gain: int = 4
    board_recovery_plan_team_energy_gain: int = 4
    board_recovery_plan_team_morale_gain: int = 4
    board_recovery_plan_team_attrition_relief: int = 5
    board_restructure_min_pressure: int = 10
    board_restructure_severance_per_employee: Decimal = Decimal("140.00")
    board_restructure_pressure_relief: int = 8
    board_restructure_governance_relief: int = 5
    board_restructure_board_pressure_relief: int = 6
    board_restructure_morale_loss: int = 4
    board_restructure_reputation_loss: int = 1
    finance_burn_multiple_warning: Decimal = Decimal("1.30")
    finance_burn_multiple_severe: Decimal = Decimal("1.80")
    finance_burn_multiple_pressure_gain: int = 4
    finance_governance_pressure_gain: int = 3

    support_program_base_capacity: int = 6
    support_program_knowledge_base_divisor: int = 12
    support_program_automation_divisor: int = 10
    support_program_customer_success_capacity_bonus: int = 2
    support_program_staff_capacity_unit: int = 2
    support_program_staff_capacity_engineer_relief_divisor: int = 2
    support_program_budget_capacity_divisor: int = 10
    support_program_backlog_ticket_divisor: int = 6
    support_program_queue_relief_divisor: int = 8
    support_program_escalation_ticket_threshold: int = 14
    support_program_escalation_sla_threshold: int = 62
    support_program_escalation_queue_divisor: int = 2
    support_program_staffing_investment_cost: Decimal = Decimal("190.00")
    support_program_staffing_level_gain: int = 2
    support_program_staffing_capacity_unit: int = 3
    support_program_service_cost_per_ticket: Decimal = Decimal("7.00")
    support_program_service_cost_per_escalation: Decimal = Decimal("22.00")
    support_program_service_cost_per_staffing_level: Decimal = Decimal("28.00")
    support_program_service_cost_per_queue_age: Decimal = Decimal("5.00")
    support_program_service_cost_per_priority_account: Decimal = Decimal("18.00")
    support_program_service_cost_per_white_glove_account: Decimal = Decimal("36.00")
    support_program_onboarding_health_pressure_threshold: int = 64
    support_program_billing_pressure_invoice_divisor: int = 14
    support_program_billing_pressure_failed_payment_divisor: int = 12
    support_program_billing_pressure_dunning_weight: int = 3
    support_program_focus_ticket_relief_divisor: int = 2
    support_program_focus_onboarding_bonus: int = 2
    support_program_focus_enterprise_bonus: int = 2
    support_program_focus_billing_bonus: int = 2
    support_program_focus_lane_capacity_bonus: int = 6
    support_program_lane_staffing_weight_unit: int = 3
    support_program_focus_mismatch_divisor: int = 8
    support_program_focus_mismatch_backlog_cap: int = 3
    support_program_lane_overflow_divisor: int = 5
    support_program_service_cost_per_lane_overflow: Decimal = Decimal("4.00")
    support_program_lane_overflow_reputation_threshold: int = 8
    support_program_lane_overflow_reputation_loss: int = 1
    support_program_queue_age_threshold: int = 3
    support_program_queue_age_satisfaction_loss: int = 2
    support_program_queue_age_churn_gain: int = 4
    support_program_queue_age_renewal_health_loss: int = 3
    support_program_queue_age_expansion_loss: int = 2
    support_program_revenue_at_risk_contract_threshold: Decimal = Decimal("900.00")
    support_program_renewal_pressure_health_threshold: int = 54
    support_program_renewal_pressure_churn_threshold: int = 38
    support_program_role_capacity: dict[str, int] = field(
        default_factory=lambda: {
            "engineer": 1,
            "designer": 1,
            "marketer": 0,
            "product_manager": 2,
        }
    )
    support_program_segment_ticket_weight: dict[str, int] = field(
        default_factory=lambda: {
            "indie": 1,
            "startup": 1,
            "smb": 2,
            "enterprise": 3,
        }
    )
    support_tier_ticket_relief: dict[str, int] = field(
        default_factory=lambda: {
            "standard": 0,
            "priority": 1,
            "white_glove": 2,
        }
    )
    support_tier_sla_relief: dict[str, int] = field(
        default_factory=lambda: {
            "standard": 0,
            "priority": 1,
            "white_glove": 3,
        }
    )
    support_tier_capacity_cost: dict[str, int] = field(
        default_factory=lambda: {
            "standard": 0,
            "priority": 1,
            "white_glove": 2,
        }
    )
    support_program_backlog_reputation_threshold: int = 24
    support_program_backlog_reputation_loss: int = 1
    support_program_backlog_morale_penalty_threshold: int = 18
    support_program_backlog_morale_penalty: int = 1
    support_program_staffing_gap_reputation_threshold: int = 4
    support_program_staffing_gap_morale_penalty: int = 1
    support_program_route_escalation_cost: Decimal = Decimal("95.00")
    support_program_route_ticket_relief: int = 5
    support_program_route_sla_relief: int = 8
    support_program_route_churn_relief: int = 6
    support_program_route_enterprise_ticket_relief_bonus: int = 2
    support_program_route_enterprise_sla_relief_bonus: int = 2
    support_program_route_onboarding_health_gain: int = 8
    support_program_route_onboarding_satisfaction_gain: int = 5
    support_program_route_onboarding_support_load_relief: int = 3
    support_program_route_billing_invoice_relief: int = 14
    support_program_route_billing_payment_relief: int = 16
    support_program_route_billing_dunning_relief: int = 1
    support_program_route_billing_renewal_health_gain: int = 6
    support_program_triage_cost: Decimal = Decimal("150.00")
    support_program_triage_backlog_relief: int = 10
    support_program_triage_escalation_relief: int = 3
    support_program_triage_ticket_relief: int = 4
    support_program_triage_sla_relief: int = 6
    support_program_upgrade_cost: Decimal = Decimal("170.00")
    support_program_upgrade_knowledge_gain: int = 10
    support_program_upgrade_automation_gain: int = 10
    support_program_upgrade_sla_gain: int = 8
    support_program_upgrade_backlog_relief: int = 4
    support_program_upgrade_escalation_relief: int = 1
    renewal_offer_cost: Decimal = Decimal("110.00")
    renewal_offer_discount_increase: Decimal = Decimal("0.0100")
    renewal_offer_health_gain: int = 8
    renewal_offer_satisfaction_gain: int = 4
    renewal_offer_risk_relief: int = 7
    renewal_offer_turn_window: int = 2
    renewal_offer_light_discount_extra: Decimal = Decimal("0.0100")
    renewal_offer_bundle_add_on_gain: int = 1
    renewal_offer_bundle_health_gain: int = 5
    renewal_offer_term_extension_risk_relief: int = 10
    renewal_offer_term_extension_health_gain: int = 7
    win_back_play_cost: Decimal = Decimal("150.00")
    win_back_contract_multiplier: Decimal = Decimal("0.80")
    win_back_satisfaction_reset: int = 58
    win_back_onboarding_reset: int = 56
    win_back_support_load_reset: int = 18
    win_back_churn_risk_reset: int = 28
    win_back_renewal_health_reset: int = 54
    win_back_open_ticket_relief: int = 4

    hiring_source_cost: Decimal = Decimal("120.00")
    hiring_screen_cost: Decimal = Decimal("55.00")
    hiring_interview_cost: Decimal = Decimal("90.00")
    hiring_offer_cash_buffer_multiplier: Decimal = Decimal("2.50")
    hiring_pipeline_candidate_limit: int = 6
    hiring_pipeline_candidate_ttl: int = 4
    hiring_acceptance_base: int = 44
    hiring_acceptance_reputation_divisor: int = 3
    hiring_acceptance_cash_buffer_divisor: Decimal = Decimal("900.00")
    hiring_acceptance_interview_divisor: int = 2
    hiring_acceptance_offer_threshold: int = 68
    hiring_acceptance_negotiate_threshold: int = 60
    hiring_screen_score_gain: int = 8
    hiring_screen_acceptance_gain: int = 6
    hiring_interview_score_gain: int = 18
    hiring_interview_score_cap: int = 92
    hiring_decline_reputation_loss: int = 1
    hiring_salary_pressure_gain: int = 4
    hiring_negotiation_salary_step: Decimal = Decimal("45.00")

    partnership_creation_cost_by_channel: dict[str, Decimal] = field(
        default_factory=lambda: {
            "reseller": Decimal("280.00"),
            "integration": Decimal("230.00"),
            "marketplace": Decimal("180.00"),
        }
    )
    partnership_base_quality_by_channel: dict[str, int] = field(
        default_factory=lambda: {
            "reseller": 58,
            "integration": 62,
            "marketplace": 54,
        }
    )
    partnership_base_risk_by_channel: dict[str, int] = field(
        default_factory=lambda: {
            "reseller": 26,
            "integration": 22,
            "marketplace": 30,
        }
    )
    partnership_base_enablement_by_channel: dict[str, int] = field(
        default_factory=lambda: {
            "reseller": 32,
            "integration": 28,
            "marketplace": 36,
        }
    )
    partnership_base_rev_share_by_channel: dict[str, Decimal] = field(
        default_factory=lambda: {
            "reseller": Decimal("0.1800"),
            "integration": Decimal("0.1400"),
            "marketplace": Decimal("0.2200"),
        }
    )
    partnership_base_user_gain_by_channel: dict[str, int] = field(
        default_factory=lambda: {
            "reseller": 4,
            "integration": 3,
            "marketplace": 5,
        }
    )
    partnership_support_cost_per_user_by_channel: dict[str, Decimal] = field(
        default_factory=lambda: {
            "reseller": Decimal("1.40"),
            "integration": Decimal("1.10"),
            "marketplace": Decimal("0.95"),
        }
    )
    partnership_lane_pressure_by_channel: dict[str, str] = field(
        default_factory=lambda: {
            "reseller": "enterprise",
            "integration": "onboarding",
            "marketplace": "billing",
        }
    )
    partnership_enablement_cost: Decimal = Decimal("140.00")
    partnership_enablement_gain: int = 12
    partnership_enablement_quality_gain: int = 5
    partnership_enablement_risk_relief: int = 6
    partnership_enablement_conflict_relief: int = 5
    partnership_enablement_summary_horizon: int = 3
    partnership_market_fit_user_bonus_divisor: int = 18
    partnership_quality_user_bonus_divisor: int = 22
    partnership_enablement_user_bonus_divisor: int = 16
    partnership_bug_user_penalty_divisor: int = 24
    partnership_bug_risk_divisor: int = 12
    partnership_debt_risk_divisor: int = 14
    partnership_quality_risk_relief_divisor: int = 20
    partnership_channel_conflict_gain: dict[str, int] = field(
        default_factory=lambda: {
            "reseller": 4,
            "integration": 2,
            "marketplace": 5,
        }
    )
    partnership_packaging_conflict_bonus: dict[str, int] = field(
        default_factory=lambda: {
            "streamlined": 0,
            "modular": 1,
            "suite": 2,
        }
    )
    partnership_premium_conflict_bonus: int = 2
    partnership_strained_user_penalty: int = 2
    partnership_strained_reputation_loss: int = 1
    partnership_neglect_turn_threshold: int = 2
    partnership_neglect_user_penalty: int = 3
    partnership_neglect_risk_gain: int = 3
    partnership_neglect_conflict_gain: int = 2
    partnership_fatigue_neglect_turn_threshold: int = 2
    partnership_fatigue_neglect_gain: int = 4
    partnership_fatigue_multi_channel_gain: int = 3
    partnership_fatigue_expand_mode_gain: int = 2
    partnership_fatigue_risk_divisor: int = 2
    partnership_fatigue_conflict_divisor: int = 2
    partnership_fatigue_recovery_penalty: int = 4
    partnership_fatigue_strained_threshold: int = 28
    partnership_fatigue_pause_threshold: int = 46
    partnership_recovery_conflict_relief: int = 4
    partnership_recovery_risk_relief: int = 3
    partnership_recovery_user_penalty: int = 3
    partnership_recovery_resume_threshold: int = 18
    partnership_enablement_fatigue_relief: int = 8
    partnership_renegotiation_cost: Decimal = Decimal("180.00")
    partnership_renegotiation_enablement_gain: int = 5
    partnership_renegotiation_risk_relief: int = 8
    partnership_renegotiation_conflict_relief: int = 10
    partnership_renegotiation_rev_share_penalty: Decimal = Decimal("0.0150")
    partnership_reactivation_cost: Decimal = Decimal("220.00")
    partnership_reactivation_enablement_gain: int = 8
    partnership_reactivation_quality_gain: int = 2
    partnership_reactivation_risk_relief: int = 12
    partnership_reactivation_conflict_relief: int = 14
    partnership_renegotiation_ready_fatigue_threshold: int = 30
    partnership_dependency_risk_strained_bonus: int = 8
    partnership_dependency_risk_paused_bonus: int = 14
    partnership_multi_channel_conflict_bonus: int = 2
    partnership_expand_mode_user_bonus: int = 2
    partnership_gtm_share_user_divisor: int = 20
    partnership_product_share_risk_relief_divisor: int = 20
    partnership_enablement_rev_share_relief: Decimal = Decimal("0.0100")
    partnership_min_rev_share_by_channel: dict[str, Decimal] = field(
        default_factory=lambda: {
            "reseller": Decimal("0.1200"),
            "integration": Decimal("0.1000"),
            "marketplace": Decimal("0.1400"),
        }
    )
    partnership_max_rev_share_by_channel: dict[str, Decimal] = field(
        default_factory=lambda: {
            "reseller": Decimal("0.2600"),
            "integration": Decimal("0.2200"),
            "marketplace": Decimal("0.2800"),
        }
    )
    partnership_maturity_quality_gain_threshold: int = 12
    partnership_revenue_milestone_rev_share_threshold: Decimal = Decimal("1600.00")
    partnership_maturity_quality_gain: int = 1
    partnership_risk_strained_threshold: int = 55
    partnership_conflict_strained_threshold: int = 52
    partnership_pause_threshold: int = 78
    partnership_cooldown_conflict_relief: int = 4
    partnership_cooldown_risk_relief: int = 3
    partnership_resume_threshold: int = 42

    capital_plan_reserve_target_by_mode: dict[str, Decimal] = field(
        default_factory=lambda: {
            "conserve": Decimal("5200.00"),
            "balanced": Decimal("3200.00"),
            "expand": Decimal("1800.00"),
        }
    )
    capital_plan_horizon_by_mode: dict[str, int] = field(
        default_factory=lambda: {
            "conserve": 8,
            "balanced": 6,
            "expand": 4,
        }
    )
    capital_plan_product_share_by_mode: dict[str, int] = field(
        default_factory=lambda: {
            "conserve": 25,
            "balanced": 35,
            "expand": 45,
        }
    )
    capital_plan_go_to_market_share_by_mode: dict[str, int] = field(
        default_factory=lambda: {
            "conserve": 20,
            "balanced": 35,
            "expand": 40,
        }
    )
    capital_plan_reserve_share_by_mode: dict[str, int] = field(
        default_factory=lambda: {
            "conserve": 55,
            "balanced": 30,
            "expand": 15,
        }
    )
    capital_plan_runway_target_modifier_by_mode: dict[str, int] = field(
        default_factory=lambda: {
            "conserve": -1,
            "balanced": 0,
            "expand": 1,
        }
    )
    capital_plan_negative_cash_pressure_by_mode: dict[str, int] = field(
        default_factory=lambda: {
            "conserve": 0,
            "balanced": 1,
            "expand": 2,
        }
    )
    capital_plan_reserve_shortfall_pressure_by_mode: dict[str, int] = field(
        default_factory=lambda: {
            "conserve": 2,
            "balanced": 1,
            "expand": 1,
        }
    )
    capital_plan_reserve_surplus_confidence_bonus_by_mode: dict[str, int] = field(
        default_factory=lambda: {
            "conserve": 2,
            "balanced": 1,
            "expand": 0,
        }
    )
    capital_plan_bootstrap_confidence_bonus: int = 1
    capital_plan_bootstrap_pressure_relief: int = 1
    capital_plan_debt_covenant_penalty: int = 2
    capital_plan_angel_pressure_relief: int = 1
    capital_plan_venture_pressure_relief: int = 2
    capital_plan_expand_confidence_penalty: int = 1
    capital_plan_conserve_covenant_relief: int = 1
    capital_plan_expand_investor_pressure_relief_cash_threshold: Decimal = Decimal("1200.00")
    capital_plan_low_product_share_threshold: int = 30
    capital_plan_high_gtm_share_threshold: int = 40
    capital_plan_low_reserve_share_threshold: int = 25
    capital_plan_gtm_without_channels_pressure_gain: int = 1
    capital_plan_low_product_share_confidence_penalty: int = 1
    capital_plan_support_reserve_covenant_penalty: int = 1
    capital_plan_dilution_warning_threshold: Decimal = Decimal("0.2200")
    capital_plan_venture_dilution_confidence_penalty: int = 2
    capital_plan_expand_execution_bonus: int = 1
    capital_plan_conserve_execution_bonus: int = 1

    finance_forecast_conservative_expand_extra_drag: Decimal = Decimal("0.0600")
    finance_forecast_conservative_conserve_relief: Decimal = Decimal("0.0300")
    finance_forecast_aggressive_expand_bonus: Decimal = Decimal("0.0500")
    finance_forecast_aggressive_conserve_penalty: Decimal = Decimal("0.0200")
    finance_forecast_venture_volatility_drag: Decimal = Decimal("0.0300")

    event_bridge_round_weight: int = 10
    event_bridge_round_cooldown: int = 7
    event_bridge_round_turn_threshold: int = 8
    event_bridge_round_cash_threshold: Decimal = Decimal("2200.00")
    event_bridge_round_take_cash_gain: Decimal = Decimal("2600.00")
    event_bridge_round_take_dilution_gain: Decimal = Decimal("0.0300")
    event_bridge_round_take_pressure_gain: int = 6
    event_bridge_round_cut_burn_cost: Decimal = Decimal("180.00")
    event_bridge_round_cut_burn_confidence_gain: int = 2
    event_bridge_round_cut_burn_morale_loss: int = 2

    event_exit_interest_weight: int = 8
    event_exit_interest_cooldown: int = 8
    event_exit_interest_turn_threshold: int = 10
    event_exit_interest_readiness_threshold: int = 62
    event_exit_interest_confidence_gain: int = 4
    event_exit_interest_pressure_gain: int = 4
    event_exit_interest_cash_gain: Decimal = Decimal("450.00")
    event_exit_interest_reputation_gain: int = 2
    event_exit_interest_independence_confidence_gain: int = 2
    event_exit_interest_independence_pressure_relief: int = 2

    event_channel_conflict_weight: int = 10
    event_channel_conflict_cooldown: int = 6
    event_channel_conflict_conflict_threshold: int = 58
    event_channel_conflict_direct_relief: int = 12
    event_channel_conflict_direct_user_loss: int = 5
    event_channel_conflict_partner_user_gain: int = 8
    event_channel_conflict_partner_conflict_gain: int = 8
    event_channel_conflict_partner_pressure_gain: int = 4
    event_public_market_scrutiny_weight: int = 7
    event_public_market_scrutiny_cooldown: int = 7
    event_public_market_scrutiny_pressure_threshold: int = 58
    event_public_market_scrutiny_control_cost: Decimal = Decimal("260.00")
    event_public_market_scrutiny_confidence_gain: int = 4
    event_public_market_scrutiny_score_gain: int = 3
    event_public_market_scrutiny_risk_relief: int = 4
    event_public_market_scrutiny_story_reputation_gain: int = 3
    event_public_market_scrutiny_story_pressure_gain: int = 4
    event_public_market_scrutiny_story_backlog_gain: int = 3
    event_acquirer_diligence_weight: int = 7
    event_acquirer_diligence_cooldown: int = 7
    event_acquirer_diligence_pressure_threshold: int = 56
    event_acquirer_diligence_data_room_cost: Decimal = Decimal("220.00")
    event_acquirer_diligence_confidence_gain: int = 3
    event_acquirer_diligence_score_gain: int = 2
    event_acquirer_diligence_partner_risk_relief: int = 5
    event_acquirer_diligence_optionality_reputation_gain: int = 2
    event_acquirer_diligence_optionality_pressure_relief: int = 3
    event_independence_reckoning_weight: int = 7
    event_independence_reckoning_cooldown: int = 7
    event_independence_reckoning_pressure_threshold: int = 56
    event_independence_reckoning_efficiency_pressure_relief: int = 3
    event_independence_reckoning_efficiency_covenant_relief: int = 4
    event_independence_reckoning_efficiency_reputation_gain: int = 2
    event_independence_reckoning_bridge_cash_gain: Decimal = Decimal("900.00")
    event_independence_reckoning_bridge_debt_gain: Decimal = Decimal("900.00")
    event_independence_reckoning_bridge_interest_gain: Decimal = Decimal("0.0050")
    event_independence_reckoning_bridge_pressure_gain: int = 4

    exit_acquisition_score_threshold: int = 170
    exit_acquisition_value_multiplier: Decimal = Decimal("1.15")
    exit_ipo_score_threshold: int = 250
    exit_ipo_value_multiplier: Decimal = Decimal("1.45")
    exit_independence_cash_threshold: Decimal = Decimal("14000.00")
    exit_restructure_cash_threshold: Decimal = Decimal("2500.00")
    exit_max_restructuring_pressure_for_win: int = 18
    exit_ipo_governance_risk_cap: int = 26
    exit_readiness_score_cap: int = 100
    exit_ipo_board_score_divisor: int = 2
    exit_ipo_key_account_bonus: int = 6
    exit_acquisition_revenue_divisor: Decimal = Decimal("150.00")
    exit_acquisition_key_account_bonus: int = 8
    exit_acquisition_support_penalty_divisor: int = 3
    exit_independence_cash_divisor: Decimal = Decimal("250.00")
    exit_independence_debt_divisor: Decimal = Decimal("220.00")

    game_over_cash_threshold: Decimal = Decimal("0.00")


BALANCE = BalanceConfig()
