from __future__ import annotations

from nexus_tech.config import DEFAULT_SCENARIO_ID
from nexus_tech.content.loader import get_product_template
from nexus_tech.domain.models import (
    BudgetStance,
    CompanyStrategy,
    EmployeeRole,
    MarketCycle,
    PricingTier,
    TurnAction,
)
from nexus_tech.simulation.engine import ActionContext, apply_action, create_new_game
from nexus_tech.simulation.scenarios import (
    create_product_from_template,
    get_available_scenarios,
)


def test_scenario_catalog_exposes_expected_default_entry() -> None:
    scenarios = get_available_scenarios()

    assert any(scenario.scenario_id == DEFAULT_SCENARIO_ID for scenario in scenarios)
    assert any(scenario.scenario_id == "agency_pivot" for scenario in scenarios)


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
    )

    assert state.company.name == "Custom Labs"
    assert state.products[0].name == "Custom Flagship"
    assert state.scenario_title == "Technical Rebuild"


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
