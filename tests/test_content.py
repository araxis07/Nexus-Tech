from __future__ import annotations

from decimal import Decimal

from nexus_tech.config import DEFAULT_SCENARIO_ID
from nexus_tech.content.loader import get_competitor_archetype, get_product_template
from nexus_tech.domain.models import (
    BudgetStance,
    CampaignGoalId,
    CompanyStrategy,
    DifficultyMode,
    EmployeeRole,
    MarketCycle,
    PricingTier,
    RoadmapFocus,
    TurnAction,
)
from nexus_tech.simulation.catalog_validation import validate_content_catalogs
from nexus_tech.simulation.engine import ActionContext, apply_action, create_new_game
from nexus_tech.simulation.scenarios import (
    create_product_from_template,
    get_available_competitor_archetypes,
    get_available_scenarios,
)


def test_scenario_catalog_exposes_expected_default_entry() -> None:
    scenarios = get_available_scenarios()
    scenario_ids = [scenario.scenario_id for scenario in scenarios]

    assert any(scenario.scenario_id == DEFAULT_SCENARIO_ID for scenario in scenarios)
    assert any(scenario.scenario_id == "agency_pivot" for scenario in scenarios)
    assert any(scenario.scenario_id == "debt_crunch" for scenario in scenarios)
    assert any(scenario.scenario_id == "market_shock" for scenario in scenarios)
    assert any(scenario.scenario_id == "portfolio_machine" for scenario in scenarios)
    assert any(scenario.scenario_id == "ops_overload" for scenario in scenarios)
    assert any(scenario.scenario_id == "price_war" for scenario in scenarios)
    assert any(scenario.scenario_id == "enterprise_scaleup" for scenario in scenarios)
    assert any(scenario.scenario_id == "renewal_crunch" for scenario in scenarios)
    assert any(scenario.scenario_id == "channel_landgrab" for scenario in scenarios)
    assert any(scenario.scenario_id == "flagship_risk" for scenario in scenarios)
    assert any(scenario.scenario_id == "talent_race" for scenario in scenarios)
    assert any(scenario.scenario_id == "moat_builder" for scenario in scenarios)
    assert any(scenario.scenario_id == "board_tension" for scenario in scenarios)
    assert any(scenario.scenario_id == "channel_defense" for scenario in scenarios)
    assert any(scenario.scenario_id == "late_scale_drag" for scenario in scenarios)
    assert any(scenario.scenario_id == "ai_governance_window" for scenario in scenarios)
    assert any(scenario.scenario_id == "ecosystem_flywheel" for scenario in scenarios)
    assert any(scenario.scenario_id == "customer_health_firefight" for scenario in scenarios)
    assert any(scenario.scenario_id == "incident_trust_rebuild" for scenario in scenarios)
    assert any(scenario.scenario_id == "open_source_commercialization" for scenario in scenarios)
    assert any(scenario.scenario_id == "regulated_ai_scale" for scenario in scenarios)
    assert any(scenario.scenario_id == "platform_ecosystem_push" for scenario in scenarios)
    assert any(scenario.scenario_id == "enterprise_rescue" for scenario in scenarios)
    assert len(scenario_ids) == len(set(scenario_ids))


def test_content_catalog_validation_passes_for_packaged_data() -> None:
    report = validate_content_catalogs()

    assert report.ok is True
    assert report.scenario_count >= 20
    assert report.template_count >= 20
    assert report.rival_count >= 10
    assert report.event_count >= 20
    assert report.issues == ()


def test_create_new_game_uses_selected_scenario_defaults() -> None:
    state = create_new_game(scenario_id="agency_pivot")

    assert state.scenario_id == "agency_pivot"
    assert state.scenario_title == "Agency Pivot"
    assert state.company.name == "Northline Studio"
    assert state.company.strategy is CompanyStrategy.BALANCED
    assert len(state.products) == 2
    assert len(state.employees) == 2
    assert len(state.competitors) >= 1
    assert state.market_cycle is MarketCycle.EXPANDING
    assert state.difficulty_mode is DifficultyMode.STANDARD
    assert state.campaign_goal_id is CampaignGoalId.PORTFOLIO_EMPIRE
    assert state.quarter_plan.budget_stance is BudgetStance.BALANCED
    assert state.products[0].name == "OpsBoard"
    assert state.products[1].pricing_tier is PricingTier.BUDGET
    assert state.employees[0].role is EmployeeRole.ENGINEER
    assert state.employees[0].assigned_product_id == state.products[1].id


def test_create_new_game_applies_company_and_primary_product_overrides() -> None:
    state = create_new_game(
        company_name="Custom Labs",
        product_name="Custom Flagship",
        scenario_id="technical_rebuild",
        difficulty_mode=DifficultyMode.BUILDER,
        campaign_goal_id=CampaignGoalId.PROFIT_MACHINE,
    )

    assert state.company.name == "Custom Labs"
    assert state.products[0].name == "Custom Flagship"
    assert state.scenario_title == "Technical Rebuild"
    assert state.difficulty_mode is DifficultyMode.BUILDER
    assert state.campaign_goal_id is CampaignGoalId.PROFIT_MACHINE


def test_create_product_from_template_uses_template_metrics() -> None:
    template = get_product_template("developer_platform")
    product, selected_template = create_product_from_template(
        "Forge API",
        [],
        template_id="developer_platform",
    )

    assert selected_template.template_id == "developer_platform"
    assert product.pricing_tier is PricingTier.PREMIUM
    assert product.revenue_per_user == template.revenue_per_user
    assert product.maintenance_cost == template.maintenance_cost
    assert product.acquisition_rate == template.acquisition_rate


def test_create_product_action_uses_selected_template() -> None:
    state = create_new_game()

    outcome = apply_action(
        state,
        TurnAction.CREATE_PRODUCT,
        context=ActionContext(
            new_product_name="Forge API",
            new_product_template_id="developer_platform",
        ),
    )

    product = next(product for product in outcome.state.products if product.name == "Forge API")

    assert product.pricing_tier is PricingTier.PREMIUM
    assert product.revenue_per_user == get_product_template("developer_platform").revenue_per_user


def test_finance_seed_is_loaded_from_scenario_content() -> None:
    state = create_new_game(scenario_id="debt_crunch")

    assert state.finance.debt_principal == Decimal("4200.00")
    assert state.finance.loan_interest_rate == Decimal("0.0350")
    assert state.finance.investor_pressure == 8


def test_board_confidence_seed_is_loaded_from_scenario_content() -> None:
    state = create_new_game(scenario_id="ai_governance_window")

    assert state.finance.board_confidence == 67
    assert state.finance.equity_dilution == Decimal("0.1000")


def test_new_template_catalog_entries_are_available() -> None:
    template = get_product_template("ai_copilot")

    assert template.title == "AI Copilot"
    assert template.pricing_tier is PricingTier.PREMIUM


def test_additional_template_catalog_entries_are_available() -> None:
    analytics = get_product_template("analytics_cloud")
    support = get_product_template("support_ops")
    security = get_product_template("security_center")
    revops = get_product_template("revops_console")
    automation = get_product_template("automation_mesh")

    assert analytics.title == "Analytics Cloud"
    assert analytics.target_segment.value == "smb"
    assert support.title == "Support Ops"
    assert support.pricing_tier is PricingTier.PREMIUM
    assert security.target_segment.value == "enterprise"
    assert revops.title == "RevOps Console"
    assert automation.target_segment.value == "startup"


def test_latest_template_catalog_entries_are_available() -> None:
    portal = get_product_template("customer_portal")
    renewal = get_product_template("renewal_cloud")
    ops = get_product_template("ops_intelligence")

    assert portal.target_segment.value == "smb"
    assert renewal.pricing_tier is PricingTier.PREMIUM
    assert ops.title == "Ops Intelligence"


def test_content_pack_two_templates_are_available() -> None:
    billing = get_product_template("billing_hub")
    partner = get_product_template("partner_stack")

    assert billing.pricing_tier is PricingTier.PREMIUM
    assert partner.target_segment.value == "startup"


def test_content_pack_three_templates_are_available() -> None:
    data_hub = get_product_template("enterprise_data_hub")
    field_ops = get_product_template("field_service_ops")
    procurement = get_product_template("procurement_cloud")

    assert data_hub.target_segment.value == "enterprise"
    assert field_ops.target_segment.value == "smb"
    assert procurement.pricing_tier is PricingTier.PREMIUM


def test_content_pack_four_templates_are_available() -> None:
    governance = get_product_template("ai_governance_console")
    marketplace = get_product_template("developer_marketplace")
    health = get_product_template("customer_health_engine")
    incident = get_product_template("incident_command_center")

    assert governance.target_segment.value == "enterprise"
    assert marketplace.target_segment.value == "startup"
    assert health.pricing_tier is PricingTier.PREMIUM
    assert incident.revenue_per_user == Decimal("88.00")


def test_content_pack_five_templates_and_objective_scenarios_are_available() -> None:
    open_source = get_product_template("open_source_platform")
    enterprise_ai = get_product_template("enterprise_ai_ops")
    compliance = get_product_template("vertical_compliance_suite")
    marketplace = get_product_template("community_marketplace")
    scenario = next(
        scenario
        for scenario in get_available_scenarios()
        if scenario.scenario_id == "open_source_commercialization"
    )
    state = create_new_game(scenario_id="regulated_ai_scale")

    assert open_source.pricing_tier is PricingTier.BUDGET
    assert enterprise_ai.revenue_per_user == Decimal("128.00")
    assert compliance.target_segment.value == "enterprise"
    assert marketplace.target_segment.value == "startup"
    assert "community adoption" in scenario.objective
    assert state.roadmap_focus is RoadmapFocus.AI_TRUST_PROGRAM
    assert state.scenario_title == "Regulated AI Scale"


def test_competitor_archetype_catalog_is_available() -> None:
    archetypes = get_available_competitor_archetypes()
    archetype_ids = {archetype.archetype_id for archetype in archetypes}

    assert {"price_raider", "platform_bulwark", "feature_blitzer"}.issubset(archetype_ids)
    assert {"channel_aggregator", "trust_monolith", "vertical_specialist"}.issubset(archetype_ids)
    assert {"ai_fast_follower", "governance_giant", "ecosystem_broker"}.issubset(archetype_ids)
    assert {
        "open_source_challenger",
        "regulatory_incumbent",
        "platform_consolidator",
    }.issubset(archetype_ids)


def test_competitor_archetype_funding_level_is_available() -> None:
    archetype = get_competitor_archetype("governance_giant")

    assert archetype.funding_level == 3
    assert archetype.pricing_tier is PricingTier.PREMIUM


def test_archetype_backed_scenario_bootstraps_competitors() -> None:
    state = create_new_game(scenario_id="talent_race")

    assert any(competitor.name == "Deal Current" for competitor in state.competitors)
    assert any(competitor.archetype_id == "price_raider" for competitor in state.competitors)
    assert any(competitor.focus_segment.value == "startup" for competitor in state.competitors)


def test_new_content_pack_scenario_bootstraps_funded_rivals() -> None:
    state = create_new_game(scenario_id="ecosystem_flywheel")

    assert state.scenario_title == "Ecosystem Flywheel"
    assert len(state.products) == 3
    assert any(product.name == "Forge Exchange" for product in state.products)
    assert any(competitor.archetype_id == "ecosystem_broker" for competitor in state.competitors)
    assert any(competitor.funding_level >= 1 for competitor in state.competitors)
