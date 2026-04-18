from __future__ import annotations

from decimal import Decimal

from nexus_tech.config import DEFAULT_SCENARIO_ID
from nexus_tech.content.loader import get_product_template
from nexus_tech.domain.models import (
    BudgetStance,
    CampaignGoalId,
    CompanyStrategy,
    DifficultyMode,
    EmployeeRole,
    MarketCycle,
    PricingTier,
    TurnAction,
)
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
    assert len(scenario_ids) == len(set(scenario_ids))


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


def test_competitor_archetype_catalog_is_available() -> None:
    archetypes = get_available_competitor_archetypes()
    archetype_ids = {archetype.archetype_id for archetype in archetypes}

    assert {"price_raider", "platform_bulwark", "feature_blitzer"}.issubset(archetype_ids)


def test_archetype_backed_scenario_bootstraps_competitors() -> None:
    state = create_new_game(scenario_id="talent_race")

    assert any(competitor.name == "Deal Current" for competitor in state.competitors)
    assert any(competitor.focus_segment.value == "startup" for competitor in state.competitors)
