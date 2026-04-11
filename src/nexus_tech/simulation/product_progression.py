"""Product actions and passive progression rules."""

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.constants import ZERO_MONEY, ZERO_RATE
from nexus_tech.domain.models import Company, LifecycleStage, Product
from nexus_tech.domain.money import quantize_money, quantize_rate
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.pricing import get_pricing_acquisition_bonus
from nexus_tech.simulation.randomness import RandomLike
from nexus_tech.simulation.strategy import StrategyProfile, get_strategy_profile
from nexus_tech.simulation.support import clamp_int, clamp_rate
from nexus_tech.simulation.team import ProductTeamModifier


@dataclass(frozen=True)
class ProductActionSummary:
    """Summarize the direct effect of one product action."""

    message: str


@dataclass(frozen=True)
class ProductDrift:
    """Passive product progression applied at end of turn."""

    quality_delta: int
    bug_delta: int
    lifecycle_stage: LifecycleStage


def create_product(name: str, existing_products: list[Product]) -> Product:
    """Validate and create a new prototype product."""

    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Product name cannot be empty.")

    existing_names = {product.name.casefold() for product in existing_products}
    if normalized_name.casefold() in existing_names:
        raise ValueError("A product with that name already exists.")

    return Product(
        name=normalized_name,
        lifecycle_stage=LifecycleStage.PROTOTYPE,
        quality=BALANCE.new_product_quality,
        bug_level=BALANCE.new_product_bug_level,
        market_fit=BALANCE.new_product_market_fit,
        technical_debt=BALANCE.new_product_technical_debt,
        user_count=BALANCE.new_product_users,
        revenue_per_user=BALANCE.new_product_revenue_per_user,
        feature_count=BALANCE.new_product_feature_count,
        maintenance_cost=BALANCE.new_product_maintenance_cost,
        acquisition_rate=BALANCE.new_product_acquisition_rate,
        churn_rate=BALANCE.new_product_churn_rate,
    )


def apply_improve_quality(
    product: Product,
    team_modifier: ProductTeamModifier,
    strategy_profile: StrategyProfile,
) -> ProductActionSummary:
    """Invest in product polish and reliability."""

    debt_penalty = calculate_delivery_penalty(product)
    quality_gain = max(
        BALANCE.improve_quality_min_gain,
        BALANCE.improve_quality_quality_gain
        - debt_penalty
        + team_modifier.build_speed_bonus
        + strategy_profile.quality_bonus,
    )
    bug_reduction = max(
        BALANCE.improve_quality_min_bug_reduction,
        BALANCE.improve_quality_bug_reduction
        - (debt_penalty // 2)
        + team_modifier.stability_bonus
        + strategy_profile.stability_bonus,
    )
    market_fit_gain = BALANCE.improve_quality_market_fit_gain + team_modifier.market_fit_bonus

    product.quality = clamp_int(product.quality + quality_gain)
    product.bug_level = clamp_int(product.bug_level - bug_reduction)
    product.market_fit = clamp_int(product.market_fit + market_fit_gain)
    product.lifecycle_stage = infer_lifecycle_stage(product)

    return ProductActionSummary(
        message=(
            f"Improved {product.name}. Quality +{quality_gain}, "
            f"bugs -{bug_reduction}, market fit +{market_fit_gain}."
        )
    )


def apply_add_feature(
    product: Product,
    team_modifier: ProductTeamModifier,
    strategy_profile: StrategyProfile,
) -> ProductActionSummary:
    """Ship a feature and accept the complexity it adds."""

    debt_penalty = calculate_delivery_penalty(product)
    quality_gain = max(
        1,
        BALANCE.add_feature_quality_gain
        - debt_penalty
        + (team_modifier.build_speed_bonus // 2)
        + max(0, strategy_profile.quality_bonus // 2),
    )
    market_fit_gain = max(
        1,
        BALANCE.add_feature_market_fit_gain
        - (1 if product.user_count > 75 else 0)
        + team_modifier.market_fit_bonus,
    )
    bug_increase = max(
        1,
        BALANCE.add_feature_bug_increase
        + (product.technical_debt // BALANCE.add_feature_bug_debt_divisor)
        + strategy_profile.feature_risk_modifier
        - team_modifier.stability_bonus
        - (team_modifier.coordination_bonus // 2),
    )
    debt_increase = max(
        2,
        BALANCE.add_feature_debt_increase
        - (team_modifier.debt_reduction_bonus // 2)
        - strategy_profile.debt_reduction_bonus,
    )
    acquisition_rate_gain = BALANCE.add_feature_acquisition_rate_gain + quantize_rate(
        Decimal(team_modifier.acquisition_bonus) / Decimal("1000")
    )

    product.feature_count += BALANCE.add_feature_feature_gain
    product.quality = clamp_int(product.quality + quality_gain)
    product.market_fit = clamp_int(product.market_fit + market_fit_gain)
    product.bug_level = clamp_int(product.bug_level + bug_increase)
    product.technical_debt = clamp_int(product.technical_debt + debt_increase)
    product.maintenance_cost = quantize_money(
        product.maintenance_cost + BALANCE.add_feature_maintenance_increase
    )
    product.acquisition_rate = clamp_rate(
        product.acquisition_rate + acquisition_rate_gain
    )
    product.churn_rate = clamp_rate(
        product.churn_rate
        + max(
            ZERO_RATE,
            BALANCE.add_feature_churn_rate_increase
            - quantize_rate(Decimal(team_modifier.stability_bonus) / Decimal("1000")),
        )
    )
    product.lifecycle_stage = infer_lifecycle_stage(product)

    return ProductActionSummary(
        message=(
            f"Added a feature to {product.name}. Features +1, fit +{market_fit_gain}, "
            f"quality +{quality_gain}, bugs +{bug_increase}, "
            f"debt +{debt_increase}."
        )
    )


def apply_reduce_technical_debt(
    product: Product,
    team_modifier: ProductTeamModifier,
    strategy_profile: StrategyProfile,
) -> ProductActionSummary:
    """Stabilize the codebase and lower future drag."""

    debt_reduction = min(
        product.technical_debt,
        BALANCE.reduce_debt_amount
        + team_modifier.debt_reduction_bonus
        + strategy_profile.debt_reduction_bonus,
    )
    bug_reduction = min(
        product.bug_level,
        BALANCE.reduce_debt_bug_reduction
        + team_modifier.stability_bonus
        + strategy_profile.stability_bonus,
    )
    quality_gain = (
        BALANCE.reduce_debt_quality_gain
        + (team_modifier.build_speed_bonus // 2)
        + max(0, strategy_profile.quality_bonus // 2)
    )

    product.technical_debt = clamp_int(product.technical_debt - debt_reduction)
    product.bug_level = clamp_int(product.bug_level - bug_reduction)
    product.quality = clamp_int(product.quality + quality_gain)
    product.maintenance_cost = quantize_money(
        max(
            ZERO_MONEY,
            product.maintenance_cost - BALANCE.reduce_debt_maintenance_reduction,
        )
    )
    product.lifecycle_stage = infer_lifecycle_stage(product)

    return ProductActionSummary(
        message=(
            f"Reduced technical debt in {product.name}. Debt -{debt_reduction}, "
            f"bugs -{bug_reduction}, quality +{quality_gain}."
        )
    )


def apply_marketing(
    company: Company,
    product: Product,
    team_modifier: ProductTeamModifier,
) -> ProductActionSummary:
    """Spend money to improve awareness and short-term adoption."""

    strategy_profile = get_strategy_profile(company.strategy)
    quality_signal = max(0, product.quality - product.bug_level - product.technical_debt)
    immediate_users = (
        BALANCE.marketing_base_user_gain
        + (product.market_fit // BALANCE.marketing_market_fit_divisor)
        + (quality_signal // BALANCE.marketing_quality_signal_divisor)
        - (product.bug_level // BALANCE.marketing_bug_penalty_divisor)
        + team_modifier.acquisition_bonus
        + get_pricing_acquisition_bonus(product)
        + strategy_profile.marketing_user_bonus
    )
    immediate_users = max(1, immediate_users)
    reputation_gain = (
        BALANCE.marketing_reputation_gain
        + team_modifier.reputation_bonus
        + max(0, strategy_profile.reputation_bonus)
    )

    company.cash_on_hand = quantize_money(company.cash_on_hand - BALANCE.marketing_cost)
    company.reputation = clamp_int(company.reputation + reputation_gain)
    product.user_count = max(0, product.user_count + immediate_users)
    product.acquisition_rate = clamp_rate(
        product.acquisition_rate
        + BALANCE.marketing_acquisition_rate_gain
        + quantize_rate(Decimal(team_modifier.acquisition_bonus) / Decimal("1000"))
    )
    product.lifecycle_stage = infer_lifecycle_stage(product)

    return ProductActionSummary(
        message=(
            f"Marketed {product.name}. Cash -{BALANCE.marketing_cost}, "
            f"users +{immediate_users}, reputation +{reputation_gain}."
        )
    )


def apply_sunset_product(product: Product) -> ProductActionSummary:
    """Shut a product down and stop carrying it in the active portfolio."""

    product.is_active = False
    product.lifecycle_stage = LifecycleStage.SUNSET
    product.user_count = 0
    product.maintenance_cost = ZERO_MONEY
    product.acquisition_rate = ZERO_RATE
    product.churn_rate = ZERO_RATE

    return ProductActionSummary(
        message=f"Sunset {product.name}. It no longer earns revenue or adds maintenance cost."
    )


def apply_end_of_turn_progression(
    product: Product,
    rng: RandomLike,
    team_modifier: ProductTeamModifier,
    strategy_profile: StrategyProfile,
) -> ProductDrift:
    """Apply passive wear-and-tear after the action phase."""

    if not product.is_active:
        product.lifecycle_stage = LifecycleStage.SUNSET
        return ProductDrift(
            quality_delta=0,
            bug_delta=0,
            lifecycle_stage=product.lifecycle_stage,
        )

    bug_delta = 0
    if product.technical_debt >= BALANCE.debt_bug_risk_threshold:
        bug_delta += 1 + (
            (product.technical_debt - BALANCE.debt_bug_risk_threshold)
            // BALANCE.debt_bug_risk_divisor
        )
    if product.technical_debt >= BALANCE.debt_bug_extra_threshold:
        bug_delta += rng.randint(0, BALANCE.debt_bug_random_high)
    bug_delta = max(
        0,
        bug_delta
        + strategy_profile.feature_risk_modifier
        - team_modifier.stability_bonus,
    )

    product.bug_level = clamp_int(product.bug_level + bug_delta)

    if (
        product.bug_level >= BALANCE.severe_bug_threshold
        or product.technical_debt >= BALANCE.severe_debt_threshold
    ):
        quality_delta = -2
    elif (
        product.bug_level >= BALANCE.moderate_bug_threshold
        or product.technical_debt >= BALANCE.moderate_debt_threshold
    ):
        quality_delta = -1
    elif (
        product.bug_level <= BALANCE.polished_bug_threshold
        and product.technical_debt <= BALANCE.polished_debt_threshold
        and product.market_fit >= BALANCE.polished_market_fit_threshold
    ):
        quality_delta = 1 + min(1, team_modifier.build_speed_bonus)
    else:
        quality_delta = 0

    quality_delta += max(0, strategy_profile.quality_bonus // 2)

    product.quality = clamp_int(product.quality + quality_delta)
    product.lifecycle_stage = infer_lifecycle_stage(product)

    return ProductDrift(
        quality_delta=quality_delta,
        bug_delta=bug_delta,
        lifecycle_stage=product.lifecycle_stage,
    )


def calculate_delivery_penalty(product: Product) -> int:
    """Technical debt slows execution on every product action."""

    return product.technical_debt // BALANCE.debt_efficiency_divisor


def infer_lifecycle_stage(product: Product) -> LifecycleStage:
    """Infer lifecycle stage from current product health and traction."""

    if not product.is_active:
        return LifecycleStage.SUNSET
    if (
        product.user_count > 0
        and (
            product.bug_level >= BALANCE.declining_bug_threshold
            or product.technical_debt >= BALANCE.declining_debt_threshold
            or product.market_fit <= BALANCE.declining_market_fit_threshold
        )
    ):
        return LifecycleStage.DECLINING
    if (
        product.user_count >= BALANCE.mature_user_threshold
        and product.market_fit >= BALANCE.mature_market_fit_threshold
    ):
        return LifecycleStage.MATURE
    if (
        product.user_count >= BALANCE.growth_user_threshold
        and product.market_fit >= BALANCE.growth_market_fit_threshold
    ):
        return LifecycleStage.GROWTH
    return LifecycleStage.PROTOTYPE
