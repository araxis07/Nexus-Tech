"""Scenario and template-driven game bootstrap helpers."""

from __future__ import annotations

from nexus_tech.config import DEFAULT_PRODUCT_TEMPLATE_ID
from nexus_tech.content.loader import (
    get_product_template,
    get_scenario,
    list_product_templates,
    list_scenarios,
)
from nexus_tech.content.models import (
    ProductTemplateDefinition,
    ScenarioCompetitorSeed,
    ScenarioDefinition,
    ScenarioEmployeeSeed,
    ScenarioProductSeed,
)
from nexus_tech.domain.models import Company, Competitor, Employee, GameState, Product
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.competition import create_competitor
from nexus_tech.simulation.planning import build_quarter_plan
from nexus_tech.simulation.product_progression import create_product
from nexus_tech.simulation.team import create_employee


def create_game_state_from_scenario(
    scenario_id: str,
    *,
    company_name: str | None = None,
    primary_product_name: str | None = None,
) -> GameState:
    """Build a validated game state from one scenario definition."""

    scenario = get_scenario(scenario_id)
    company = Company(
        name=(company_name or scenario.company_name).strip(),
        cash_on_hand=scenario.cash_on_hand,
        reputation=scenario.reputation,
        strategy=scenario.company_strategy,
    )
    products = _build_scenario_products(scenario, primary_product_name=primary_product_name)
    employees = _build_scenario_employees(scenario, products)
    competitors = _build_scenario_competitors(scenario, products)
    state = GameState(
        company=company,
        products=products,
        employees=employees,
        competitors=competitors,
        roadmap_focus=scenario.roadmap_focus,
        roadmap_set_turn=1,
        market_cycle=scenario.market_cycle,
        market_cycle_turns_remaining=scenario.market_cycle_turns_remaining,
        scenario_id=scenario.scenario_id,
        scenario_title=scenario.title,
        action_points_remaining=BALANCE.actions_per_turn,
    )
    state.quarter_plan = build_quarter_plan(state, budget_stance=scenario.budget_stance)
    return state


def create_product_from_template(
    name: str,
    existing_products: list[Product],
    *,
    template_id: str = DEFAULT_PRODUCT_TEMPLATE_ID,
) -> tuple[Product, ProductTemplateDefinition]:
    """Create a product using one of the content-defined templates."""

    template = get_product_template(template_id)
    product = _instantiate_template_product(
        name=name,
        existing_products=existing_products,
        template=template,
    )
    return product, template


def get_available_scenarios() -> tuple[ScenarioDefinition, ...]:
    """Return all scenario definitions for CLI presentation."""

    return list_scenarios()


def get_available_product_templates() -> tuple[ProductTemplateDefinition, ...]:
    """Return all product templates for CLI presentation."""

    return list_product_templates()


def _build_scenario_products(
    scenario: ScenarioDefinition,
    *,
    primary_product_name: str | None,
) -> list[Product]:
    products: list[Product] = []
    for index, seed in enumerate(scenario.products):
        template = get_product_template(seed.template_id)
        product_name = primary_product_name if index == 0 and primary_product_name else seed.name
        product = _instantiate_template_product(
            name=product_name,
            existing_products=products,
            template=template,
            seed=seed,
        )
        products.append(product)
    return products


def _build_scenario_employees(
    scenario: ScenarioDefinition,
    products: list[Product],
) -> list[Employee]:
    employees: list[Employee] = []
    if len(scenario.products) != len(products):
        raise ValueError("Scenario product bootstrap produced mismatched product counts.")

    product_ids_by_key = {
        seed.key: products[index].id for index, seed in enumerate(scenario.products)
    }
    for employee_seed in scenario.employees:
        employee = _instantiate_scenario_employee(
            employee_seed,
            existing_employees=employees,
            product_ids_by_key=product_ids_by_key,
        )
        employees.append(employee)
    return employees


def _build_scenario_competitors(
    scenario: ScenarioDefinition,
    products: list[Product],
) -> list[Competitor]:
    competitors: list[Competitor] = []
    if scenario.competitors:
        for competitor_seed in scenario.competitors:
            competitors.append(_instantiate_scenario_competitor(competitor_seed))
        return competitors

    for product in products[:2]:
        competitors.append(
            create_competitor(
                name=f"{product.name} Rival",
                focus_segment=product.target_segment,
                strength=max(35, product.quality - 4),
                aggression=48,
                pricing_tier=product.pricing_tier,
                active_product_count=1,
            )
        )
    return competitors


def _instantiate_template_product(
    *,
    name: str,
    existing_products: list[Product],
    template: ProductTemplateDefinition,
    seed: ScenarioProductSeed | None = None,
) -> Product:
    product = create_product(
        name,
        existing_products,
        lifecycle_stage=template.lifecycle_stage,
        quality=template.quality,
        bug_level=template.bug_level,
        market_fit=template.market_fit,
        technical_debt=template.technical_debt,
        user_count=template.user_count,
        revenue_per_user=template.revenue_per_user,
        feature_count=template.feature_count,
        maintenance_cost=template.maintenance_cost,
        acquisition_rate=template.acquisition_rate,
        churn_rate=template.churn_rate,
        pricing_tier=template.pricing_tier,
        target_segment=template.target_segment,
    )
    if seed is None:
        return product

    if seed.lifecycle_stage is not None:
        product.lifecycle_stage = seed.lifecycle_stage
    if seed.quality is not None:
        product.quality = seed.quality
    if seed.bug_level is not None:
        product.bug_level = seed.bug_level
    if seed.market_fit is not None:
        product.market_fit = seed.market_fit
    if seed.technical_debt is not None:
        product.technical_debt = seed.technical_debt
    if seed.user_count is not None:
        product.user_count = seed.user_count
    if seed.revenue_per_user is not None:
        product.revenue_per_user = seed.revenue_per_user
    if seed.feature_count is not None:
        product.feature_count = seed.feature_count
    if seed.maintenance_cost is not None:
        product.maintenance_cost = seed.maintenance_cost
    if seed.acquisition_rate is not None:
        product.acquisition_rate = seed.acquisition_rate
    if seed.churn_rate is not None:
        product.churn_rate = seed.churn_rate
    if seed.pricing_tier is not None:
        product.pricing_tier = seed.pricing_tier
    if seed.target_segment is not None:
        product.target_segment = seed.target_segment
    product.is_active = seed.is_active
    return product


def _instantiate_scenario_employee(
    seed: ScenarioEmployeeSeed,
    *,
    existing_employees: list[Employee],
    product_ids_by_key: dict[str, object],
) -> Employee:
    employee = create_employee(
        full_name=seed.full_name,
        role=seed.role,
        seniority=seed.seniority,
        specialization=seed.specialization,
        existing_employees=existing_employees,
    )
    if seed.energy is not None:
        employee.energy = seed.energy
    if seed.morale is not None:
        employee.morale = seed.morale
    if seed.productivity is not None:
        employee.productivity = seed.productivity
    if seed.assigned_product_key is not None:
        if seed.assigned_product_key not in product_ids_by_key:
            raise ValueError(
                f"Scenario employee '{seed.full_name}' references unknown product key "
                f"'{seed.assigned_product_key}'."
            )
        employee.assigned_product_id = product_ids_by_key[seed.assigned_product_key]
    return employee


def _instantiate_scenario_competitor(seed: ScenarioCompetitorSeed) -> Competitor:
    return create_competitor(
        name=seed.name,
        focus_segment=seed.focus_segment,
        strength=seed.strength,
        aggression=seed.aggression,
        pricing_tier=seed.pricing_tier,
        active_product_count=seed.active_product_count,
    )
