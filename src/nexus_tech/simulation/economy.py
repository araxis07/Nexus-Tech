"""Economy rules for revenue, maintenance, and company burn."""

from decimal import Decimal

from nexus_tech.domain.models import Company, Product
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE


def iter_active_products(products: list[Product]) -> list[Product]:
    """Return only products that still contribute to the business."""

    return [product for product in products if product.is_active]


def calculate_product_revenue(product: Product) -> Decimal:
    """Revenue earned by one active product during a turn."""

    if not product.is_active:
        return Decimal("0.00")
    return quantize_money(Decimal(product.user_count) * product.revenue_per_user)


def calculate_product_operating_cost(product: Product) -> Decimal:
    """Maintenance and support cost carried by one active product."""

    if not product.is_active:
        return Decimal("0.00")

    support_cost = Decimal(product.user_count) * BALANCE.per_user_support_cost
    debt_cost = Decimal(product.technical_debt) * BALANCE.per_debt_operating_cost
    return quantize_money(product.maintenance_cost + support_cost + debt_cost)


def calculate_total_revenue(products: list[Product]) -> Decimal:
    """Aggregate revenue across all active products."""

    total = sum((calculate_product_revenue(product) for product in products), Decimal("0.00"))
    return quantize_money(total)


def calculate_total_product_operating_cost(products: list[Product]) -> Decimal:
    """Aggregate product-level costs across the portfolio."""

    total = sum(
        (calculate_product_operating_cost(product) for product in products),
        Decimal("0.00"),
    )
    return quantize_money(total)


def calculate_total_operating_cost(products: list[Product]) -> Decimal:
    """Company burn including baseline cost and active product load."""

    return quantize_money(
        BALANCE.base_operating_cost + calculate_total_product_operating_cost(products)
    )


def is_game_over(company: Company) -> bool:
    """Check the loss condition for the company."""

    return company.cash_on_hand < BALANCE.game_over_cash_threshold
