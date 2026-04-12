"""Economy rules for revenue, maintenance, pricing, salary, and company burn."""

from __future__ import annotations

from decimal import Decimal

from nexus_tech.domain.constants import ZERO_MONEY
from nexus_tech.domain.models import (
    BudgetStance,
    Company,
    Employee,
    FinanceState,
    Product,
    RoadmapFocus,
)
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.finance import calculate_total_finance_cost
from nexus_tech.simulation.planning import get_budget_profile
from nexus_tech.simulation.pricing import calculate_effective_revenue_per_user
from nexus_tech.simulation.roadmap import get_roadmap_profile
from nexus_tech.simulation.segments import resolve_segment_dynamics
from nexus_tech.simulation.strategy import get_strategy_profile


def calculate_product_revenue(product: Product) -> Decimal:
    """Revenue earned by one active product during a turn."""

    if not product.is_active:
        return ZERO_MONEY
    return quantize_money(
        Decimal(product.user_count) * calculate_effective_revenue_per_user(product)
    )


def calculate_product_operating_cost(
    product: Product,
    *,
    current_turn: int = 1,
    roadmap_focus: RoadmapFocus = RoadmapFocus.BALANCED_EXECUTION,
    roadmap_set_turn: int = 1,
) -> Decimal:
    """Maintenance and support cost carried by one active product."""

    if not product.is_active:
        return ZERO_MONEY

    segment_dynamics = resolve_segment_dynamics(
        product,
        current_turn=current_turn,
        roadmap_focus=roadmap_focus,
        roadmap_set_turn=roadmap_set_turn,
        pricing_churn_modifier=Decimal("0.0000"),
    )
    support_cost = (
        Decimal(product.user_count)
        * BALANCE.per_user_support_cost
        * segment_dynamics.support_cost_multiplier
    )
    debt_cost = Decimal(product.technical_debt) * BALANCE.per_debt_operating_cost
    return quantize_money(product.maintenance_cost + support_cost + debt_cost)


def calculate_total_revenue(products: list[Product]) -> Decimal:
    """Aggregate revenue across all active products."""

    total = sum((calculate_product_revenue(product) for product in products), ZERO_MONEY)
    return quantize_money(total)


def calculate_total_product_operating_cost(
    products: list[Product],
    *,
    current_turn: int = 1,
    roadmap_focus: RoadmapFocus = RoadmapFocus.BALANCED_EXECUTION,
    roadmap_set_turn: int = 1,
) -> Decimal:
    """Aggregate product-level costs across the portfolio."""

    total = sum(
        (
            calculate_product_operating_cost(
                product,
                current_turn=current_turn,
                roadmap_focus=roadmap_focus,
                roadmap_set_turn=roadmap_set_turn,
            )
            for product in products
        ),
        ZERO_MONEY,
    )
    return quantize_money(total)


def calculate_total_salary_cost(employees: list[Employee]) -> Decimal:
    """Aggregate recurring salary burden."""

    total = sum((employee.salary for employee in employees), ZERO_MONEY)
    return quantize_money(total)


def calculate_total_operating_cost(
    company: Company,
    products: list[Product],
    employees: list[Employee],
    *,
    finance: FinanceState | None = None,
    budget_stance: BudgetStance = BudgetStance.BALANCED,
    roadmap_focus: RoadmapFocus = RoadmapFocus.BALANCED_EXECUTION,
    roadmap_set_turn: int = 1,
) -> Decimal:
    """Company burn including baseline cost, product load, and salaries."""

    strategy_profile = get_strategy_profile(company.strategy)
    budget_profile = get_budget_profile(budget_stance)
    roadmap_profile = get_roadmap_profile(
        roadmap_focus,
        roadmap_set_turn=roadmap_set_turn,
        current_turn=company.current_turn,
    )
    return quantize_money(
        BALANCE.base_operating_cost
        + strategy_profile.operating_cost_modifier
        + budget_profile.operating_cost_modifier
        + roadmap_profile.operating_cost_modifier
        + calculate_total_product_operating_cost(
            products,
            current_turn=company.current_turn,
            roadmap_focus=roadmap_focus,
            roadmap_set_turn=roadmap_set_turn,
        )
        + calculate_total_salary_cost(employees)
        + calculate_total_finance_cost(finance or FinanceState())
    )


def is_game_over(company: Company) -> bool:
    """Check the loss condition for the company."""

    return company.cash_on_hand < BALANCE.game_over_cash_threshold
