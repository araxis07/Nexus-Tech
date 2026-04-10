"""User acquisition, churn, and portfolio reputation movement."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from nexus_tech.domain.models import Company, Employee, LifecycleStage, Product
from nexus_tech.domain.money import quantize_rate
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.randomness import RandomLike
from nexus_tech.simulation.team import ProductTeamModifier, calculate_product_team_modifier


@dataclass(frozen=True)
class GrowthResult:
    """Net user movement for one product on one turn."""

    acquired_users: int
    churned_users: int
    net_user_delta: int


STAGE_ACQUISITION_MODIFIER = {
    LifecycleStage.PROTOTYPE: -1,
    LifecycleStage.GROWTH: 2,
    LifecycleStage.MATURE: 1,
    LifecycleStage.DECLINING: -2,
    LifecycleStage.SUNSET: -99,
}

STAGE_CHURN_MODIFIER = {
    LifecycleStage.PROTOTYPE: 2,
    LifecycleStage.GROWTH: 0,
    LifecycleStage.MATURE: 1,
    LifecycleStage.DECLINING: 4,
    LifecycleStage.SUNSET: 20,
}


def calculate_acquired_users(
    company: Company,
    product: Product,
    rng: RandomLike,
    team_modifier: ProductTeamModifier,
) -> int:
    """Estimate new users joining a product this turn."""

    if not product.is_active:
        return 0

    base_from_rate = int(Decimal(product.user_count) * product.acquisition_rate)
    if product.user_count == 0 and product.market_fit >= BALANCE.discovery_market_fit_threshold:
        base_from_rate += 1

    acquisition_signal = (
        product.quality
        + product.market_fit
        + company.reputation
        - product.bug_level
        - product.technical_debt
        - BALANCE.acquisition_signal_baseline
    ) // BALANCE.acquisition_signal_divisor

    acquisition = (
        base_from_rate
        + acquisition_signal
        + STAGE_ACQUISITION_MODIFIER[product.lifecycle_stage]
        + team_modifier.acquisition_bonus
        + rng.randint(-BALANCE.acquisition_random_swing, BALANCE.acquisition_random_swing)
    )
    acquisition_cap = max(
        BALANCE.acquisition_cap_base,
        (product.user_count // BALANCE.acquisition_cap_divisor)
        + BALANCE.acquisition_cap_base
        + team_modifier.acquisition_bonus,
    )
    return max(0, min(acquisition_cap, acquisition))


def calculate_effective_churn_rate(product: Product) -> Decimal:
    """Build a churn rate that reflects product health."""

    churn_rate = product.churn_rate
    churn_rate += Decimal(product.bug_level // BALANCE.churn_bug_divisor) / Decimal("100")
    churn_rate += Decimal(product.technical_debt // BALANCE.churn_debt_divisor) / Decimal("100")
    churn_rate += Decimal(STAGE_CHURN_MODIFIER[product.lifecycle_stage]) / Decimal("100")
    churn_rate -= Decimal(product.quality // BALANCE.churn_quality_relief_divisor) / Decimal("100")

    if product.market_fit < BALANCE.low_market_fit_threshold:
        churn_rate += Decimal(BALANCE.low_market_fit_churn_penalty) / Decimal("100")

    churn_rate = max(BALANCE.min_churn_rate, min(BALANCE.max_churn_rate, churn_rate))
    return quantize_rate(churn_rate)


def calculate_churned_users(product: Product, rng: RandomLike) -> int:
    """Estimate users leaving a product this turn."""

    if not product.is_active or product.user_count == 0:
        return 0

    effective_rate = calculate_effective_churn_rate(product)
    raw_churn = Decimal(product.user_count) * effective_rate
    churned_users = int(raw_churn.to_integral_value(rounding=ROUND_HALF_UP))
    if churned_users == 0:
        churned_users = 1

    churned_users += rng.randint(0, BALANCE.churn_random_swing)
    return max(0, min(product.user_count, churned_users))


def resolve_growth(
    company: Company,
    product: Product,
    rng: RandomLike,
    team_modifier: ProductTeamModifier,
) -> GrowthResult:
    """Resolve both acquisition and churn for one product."""

    acquired_users = calculate_acquired_users(company, product, rng, team_modifier)
    churned_users = calculate_churned_users(product, rng)
    net_user_delta = acquired_users - churned_users
    return GrowthResult(
        acquired_users=acquired_users,
        churned_users=churned_users,
        net_user_delta=net_user_delta,
    )


def calculate_company_reputation_delta(
    company: Company,
    products: list[Product],
    employees: list[Employee],
    rng: RandomLike,
) -> int:
    """Move company reputation based on portfolio health."""

    active_products = [product for product in products if product.is_active]
    if not active_products:
        base_delta = -1
    else:
        total_weight = sum(max(1, product.user_count) for product in active_products)
        weighted_health = sum(
            (
                product.quality
                + product.market_fit
                - product.bug_level
                - product.technical_debt
            )
            * max(1, product.user_count)
            for product in active_products
        ) // total_weight

        if weighted_health >= BALANCE.reputation_strong_threshold:
            base_delta = 2
        elif weighted_health >= BALANCE.reputation_positive_threshold:
            base_delta = 1
        elif weighted_health <= BALANCE.reputation_bad_threshold:
            base_delta = -2
        elif weighted_health <= BALANCE.reputation_soft_bad_threshold:
            base_delta = -1
        else:
            base_delta = 0

    reputation_support = sum(
        calculate_product_team_modifier(employees, product.id).reputation_bonus
        for product in active_products
    )
    designer_bonus = min(1, reputation_support)
    delta = base_delta + designer_bonus + rng.randint(-1, 1)
    return max(-2, min(3, delta))
