"""Economy rules for revenue, maintenance, pricing, salary, and company burn."""

from decimal import Decimal

from nexus_tech.domain.constants import ZERO_MONEY
from nexus_tech.domain.models import Company, Employee, Product
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.pricing import calculate_effective_revenue_per_user
from nexus_tech.simulation.strategy import get_strategy_profile


def calculate_product_revenue(product: Product) -> Decimal:
    """Revenue earned by one active product during a turn."""

    if not product.is_active:
        return ZERO_MONEY
    return quantize_money(
        Decimal(product.user_count) * calculate_effective_revenue_per_user(product)
    )


def calculate_product_operating_cost(product: Product) -> Decimal:
    """Maintenance and support cost carried by one active product."""

    if not product.is_active:
        return ZERO_MONEY

    support_cost = Decimal(product.user_count) * BALANCE.per_user_support_cost
    debt_cost = Decimal(product.technical_debt) * BALANCE.per_debt_operating_cost
    return quantize_money(product.maintenance_cost + support_cost + debt_cost)


def calculate_total_revenue(products: list[Product]) -> Decimal:
    """Aggregate revenue across all active products."""

    total = sum((calculate_product_revenue(product) for product in products), ZERO_MONEY)
    return quantize_money(total)


def calculate_total_product_operating_cost(products: list[Product]) -> Decimal:
    """Aggregate product-level costs across the portfolio."""

    total = sum(
        (calculate_product_operating_cost(product) for product in products),
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
) -> Decimal:
    """Company burn including baseline cost, product load, and salaries."""

    strategy_profile = get_strategy_profile(company.strategy)
    return quantize_money(
        BALANCE.base_operating_cost
        + strategy_profile.operating_cost_modifier
        + calculate_total_product_operating_cost(products)
        + calculate_total_salary_cost(employees)
    )


def is_game_over(company: Company) -> bool:
    """Check the loss condition for the company."""

    return company.cash_on_hand < BALANCE.game_over_cash_threshold
