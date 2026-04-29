"""Pricing and packaging effects for product monetization and growth."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import (
    Company,
    CustomerAccount,
    CustomerAccountStatus,
    PackagingStrategy,
    PricingTier,
    Product,
    SubscriptionPackage,
    SupportTier,
)
from nexus_tech.domain.money import format_money, quantize_money, quantize_rate
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.support import clamp_int, clamp_rate


@dataclass(frozen=True)
class PricingActionSummary:
    """Summary of changing a product pricing tier."""

    message: str


@dataclass(frozen=True)
class PricingProfile:
    """Modifiers implied by one pricing tier."""

    revenue_multiplier: Decimal
    acquisition_bonus: int
    churn_modifier: Decimal


@dataclass(frozen=True)
class PackagingProfile:
    """Modifiers implied by one packaging strategy."""

    revenue_multiplier: Decimal
    acquisition_bonus: int
    churn_modifier: Decimal
    support_cost_multiplier: Decimal
    add_on_bonus: int
    enterprise_probability_bonus: int


@dataclass(frozen=True)
class PackagingActionSummary:
    """Summary of changing a product packaging strategy."""

    message: str


@dataclass(frozen=True)
class PriceIncreaseSummary:
    """Summary of an explicit price increase decision."""

    message: str


@dataclass(frozen=True)
class AddOnCampaignSummary:
    """Summary of an explicit add-on monetization push."""

    message: str


@dataclass(frozen=True)
class PackagingMigrationSummary:
    """Summary of an account migration between packages."""

    message: str


@dataclass(frozen=True)
class CatalogExpansionSummary:
    """Summary of expanding monetization surface on one product."""

    message: str


_PRICING_PROFILES = {
    PricingTier.BUDGET: PricingProfile(
        revenue_multiplier=BALANCE.pricing_budget_revenue_multiplier,
        acquisition_bonus=BALANCE.pricing_budget_acquisition_bonus,
        churn_modifier=BALANCE.pricing_budget_churn_modifier,
    ),
    PricingTier.STANDARD: PricingProfile(
        revenue_multiplier=Decimal("1.00"),
        acquisition_bonus=0,
        churn_modifier=Decimal("0.0000"),
    ),
    PricingTier.PREMIUM: PricingProfile(
        revenue_multiplier=BALANCE.pricing_premium_revenue_multiplier,
        acquisition_bonus=BALANCE.pricing_premium_acquisition_bonus,
        churn_modifier=BALANCE.pricing_premium_churn_modifier,
    ),
}

_PACKAGING_PROFILES = {
    PackagingStrategy.STREAMLINED: PackagingProfile(
        revenue_multiplier=BALANCE.packaging_revenue_multiplier["streamlined"],
        acquisition_bonus=BALANCE.packaging_acquisition_bonus["streamlined"],
        churn_modifier=BALANCE.packaging_churn_modifier["streamlined"],
        support_cost_multiplier=BALANCE.packaging_support_cost_multiplier["streamlined"],
        add_on_bonus=BALANCE.packaging_add_on_bonus["streamlined"],
        enterprise_probability_bonus=BALANCE.packaging_enterprise_probability_bonus["streamlined"],
    ),
    PackagingStrategy.MODULAR: PackagingProfile(
        revenue_multiplier=BALANCE.packaging_revenue_multiplier["modular"],
        acquisition_bonus=BALANCE.packaging_acquisition_bonus["modular"],
        churn_modifier=BALANCE.packaging_churn_modifier["modular"],
        support_cost_multiplier=BALANCE.packaging_support_cost_multiplier["modular"],
        add_on_bonus=BALANCE.packaging_add_on_bonus["modular"],
        enterprise_probability_bonus=BALANCE.packaging_enterprise_probability_bonus["modular"],
    ),
    PackagingStrategy.SUITE: PackagingProfile(
        revenue_multiplier=BALANCE.packaging_revenue_multiplier["suite"],
        acquisition_bonus=BALANCE.packaging_acquisition_bonus["suite"],
        churn_modifier=BALANCE.packaging_churn_modifier["suite"],
        support_cost_multiplier=BALANCE.packaging_support_cost_multiplier["suite"],
        add_on_bonus=BALANCE.packaging_add_on_bonus["suite"],
        enterprise_probability_bonus=BALANCE.packaging_enterprise_probability_bonus["suite"],
    ),
}


def get_pricing_profile(pricing_tier: PricingTier) -> PricingProfile:
    """Return the effective profile for a pricing tier."""

    return _PRICING_PROFILES[pricing_tier]


def get_packaging_profile(packaging_strategy: PackagingStrategy) -> PackagingProfile:
    """Return the effective profile for a packaging strategy."""

    return _PACKAGING_PROFILES[packaging_strategy]


def calculate_catalog_revenue_multiplier(product: Product) -> Decimal:
    """Return the revenue lift created by package and add-on catalog depth."""

    return quantize_rate(
        Decimal("1.0000")
        + (
            Decimal(product.package_catalog_depth)
            * BALANCE.packaging_catalog_revenue_multiplier_step
        )
        + (Decimal(product.add_on_catalog_depth) * BALANCE.add_on_catalog_revenue_multiplier_step)
    )


def calculate_catalog_protection_score(product: Product) -> int:
    """Return how much packaging depth protects against pricing and churn shock."""

    return (product.package_catalog_depth // BALANCE.price_increase_catalog_protection_divisor) + (
        product.add_on_catalog_depth // BALANCE.price_increase_catalog_protection_divisor
    )


def calculate_catalog_complexity_penalty(product: Product) -> Decimal:
    """Return the support-cost drag created by a deeper monetization surface."""

    depth = product.package_catalog_depth + product.add_on_catalog_depth
    return quantize_rate(
        Decimal("1.0000") + (Decimal(depth) * BALANCE.packaging_support_cost_depth_step)
    )


def calculate_effective_revenue_per_user(product: Product) -> Decimal:
    """Return revenue per user after pricing-tier modifiers."""

    pricing_profile = get_pricing_profile(product.pricing_tier)
    packaging_profile = get_packaging_profile(product.packaging_strategy)
    catalog_multiplier = calculate_catalog_revenue_multiplier(product)
    return quantize_money(
        product.revenue_per_user
        * pricing_profile.revenue_multiplier
        * packaging_profile.revenue_multiplier
        * catalog_multiplier
    )


def get_pricing_acquisition_bonus(product: Product) -> int:
    """Return the acquisition bonus or penalty from the current pricing tier."""

    pricing_profile = get_pricing_profile(product.pricing_tier)
    packaging_profile = get_packaging_profile(product.packaging_strategy)
    return (
        pricing_profile.acquisition_bonus
        + packaging_profile.acquisition_bonus
        + (product.package_catalog_depth // BALANCE.packaging_catalog_acquisition_depth_divisor)
        + (product.add_on_catalog_depth // BALANCE.add_on_catalog_acquisition_depth_divisor)
    )


def get_pricing_churn_modifier(product: Product) -> Decimal:
    """Return the churn modifier from the current pricing tier."""

    pricing_profile = get_pricing_profile(product.pricing_tier)
    packaging_profile = get_packaging_profile(product.packaging_strategy)
    churn_relief = Decimal(
        product.package_catalog_depth // BALANCE.packaging_churn_relief_depth_divisor
    ) * Decimal("0.0010")
    return quantize_rate(
        pricing_profile.churn_modifier + packaging_profile.churn_modifier - churn_relief
    )


def get_packaging_support_cost_multiplier(product: Product) -> Decimal:
    """Return the operating-cost multiplier created by packaging complexity."""

    return quantize_rate(
        get_packaging_profile(product.packaging_strategy).support_cost_multiplier
        * calculate_catalog_complexity_penalty(product)
    )


def get_packaging_add_on_bonus(product: Product) -> int:
    """Return add-on depth created by the chosen packaging strategy."""

    return get_packaging_profile(product.packaging_strategy).add_on_bonus + (
        product.add_on_catalog_depth
    )


def get_packaging_enterprise_probability_bonus(product: Product) -> int:
    """Return enterprise pipeline lift implied by the packaging strategy."""

    return get_packaging_profile(product.packaging_strategy).enterprise_probability_bonus + (
        product.package_catalog_depth
    )


def get_default_subscription_package(product: Product) -> SubscriptionPackage:
    """Return the default contract package implied by segment and packaging posture."""

    if product.packaging_strategy is PackagingStrategy.SUITE:
        if product.target_segment.value == "enterprise":
            return SubscriptionPackage.ENTERPRISE_SUITE
        return SubscriptionPackage.GROWTH
    if product.packaging_strategy is PackagingStrategy.MODULAR:
        return SubscriptionPackage.GROWTH
    return SubscriptionPackage.STARTER


def determine_target_subscription_package(
    product: Product,
    account: CustomerAccount,
) -> SubscriptionPackage:
    """Return the best-fit package for one account under the current catalog depth."""

    package_readiness = (
        product.package_catalog_depth
        + (product.add_on_catalog_depth // 2)
        + (1 if account.plan_tier is PricingTier.PREMIUM else 0)
        + (1 if account.expansion_potential >= 65 else 0)
        + (1 if account.renewal_health >= 68 else 0)
    )
    if product.packaging_strategy is PackagingStrategy.SUITE:
        if (
            account.segment.value == "enterprise"
            or account.support_tier is not SupportTier.STANDARD
            or product.package_catalog_depth >= BALANCE.package_catalog_enterprise_upgrade_threshold
            or package_readiness >= 4
        ):
            return SubscriptionPackage.ENTERPRISE_SUITE
        return SubscriptionPackage.GROWTH
    if product.packaging_strategy is PackagingStrategy.MODULAR:
        if product.package_catalog_depth >= 2 and (
            account.segment.value == "enterprise"
            or account.plan_tier is PricingTier.PREMIUM
            or account.add_on_count >= 2
            or package_readiness >= 4
        ):
            return SubscriptionPackage.ENTERPRISE_SUITE
        if (
            product.add_on_catalog_depth >= BALANCE.add_on_catalog_growth_upgrade_threshold
            or account.plan_tier is not PricingTier.BUDGET
            or package_readiness >= 2
        ):
            return SubscriptionPackage.GROWTH
        return SubscriptionPackage.STARTER
    if account.segment.value == "enterprise" and product.package_catalog_depth >= 2:
        return SubscriptionPackage.GROWTH
    return SubscriptionPackage.STARTER


def apply_adjust_pricing(
    product: Product,
    pricing_tier: PricingTier,
) -> PricingActionSummary:
    """Change a product pricing tier and apply a light market-fit response."""

    if product.pricing_tier is pricing_tier:
        raise ValueError(f"{product.name} is already on {pricing_tier.value} pricing.")

    product.pricing_tier = pricing_tier
    fit_delta = 0

    if pricing_tier is PricingTier.BUDGET:
        fit_delta = BALANCE.pricing_budget_market_fit_bonus
    elif pricing_tier is PricingTier.PREMIUM:
        if product.quality >= BALANCE.pricing_premium_quality_threshold:
            fit_delta = BALANCE.pricing_premium_market_fit_bonus
        else:
            fit_delta = -BALANCE.pricing_premium_market_fit_penalty

    product.market_fit = clamp_int(product.market_fit + fit_delta)
    product.acquisition_rate = clamp_rate(product.acquisition_rate)
    product.churn_rate = clamp_rate(product.churn_rate)

    effective_rpu = calculate_effective_revenue_per_user(product)
    return PricingActionSummary(
        message=(
            f"{product.name} moved to {pricing_tier.value} pricing. "
            f"Effective revenue per user is now {format_money(effective_rpu)}"
            f" and market fit changed by {fit_delta:+d}."
        )
    )


def apply_set_packaging_strategy(
    product: Product,
    packaging_strategy: PackagingStrategy,
) -> PackagingActionSummary:
    """Change a product packaging strategy and re-center market fit expectations."""

    if product.packaging_strategy is packaging_strategy:
        raise ValueError(f"{product.name} is already using {packaging_strategy.value} packaging.")

    product.packaging_strategy = packaging_strategy
    fit_delta = BALANCE.packaging_market_fit_shift_by_segment[packaging_strategy.value][
        product.target_segment.value
    ]
    product.market_fit = clamp_int(product.market_fit + fit_delta)
    product.acquisition_rate = clamp_rate(product.acquisition_rate)
    product.churn_rate = clamp_rate(product.churn_rate)
    effective_rpu = calculate_effective_revenue_per_user(product)
    add_on_bonus = get_packaging_add_on_bonus(product)
    return PackagingActionSummary(
        message=(
            f"{product.name} shifted to {packaging_strategy.value} packaging. "
            f"Effective revenue per user is now {format_money(effective_rpu)}, "
            f"market fit {fit_delta:+d}, add-on depth {add_on_bonus:+d}."
        )
    )


def apply_run_price_increase(
    product: Product,
    customer_accounts: list[CustomerAccount],
) -> PriceIncreaseSummary:
    """Raise product monetization and let account tension absorb part of the shock."""

    multiplier = BALANCE.price_increase_base_multiplier
    if product.pricing_tier is PricingTier.PREMIUM:
        multiplier += BALANCE.price_increase_premium_bonus
    elif product.pricing_tier is PricingTier.BUDGET:
        multiplier += BALANCE.price_increase_budget_penalty
    if product.packaging_strategy is PackagingStrategy.SUITE:
        multiplier += BALANCE.price_increase_suite_bonus

    product.revenue_per_user = quantize_money(product.revenue_per_user * multiplier)
    catalog_protection = calculate_catalog_protection_score(product)
    market_fit_penalty = max(
        1,
        BALANCE.price_increase_market_fit_penalty_by_segment[product.target_segment.value]
        - (product.quality // BALANCE.price_increase_quality_relief_divisor)
        - BALANCE.price_increase_packaging_relief[product.packaging_strategy.value],
    )
    product.market_fit = clamp_int(product.market_fit - market_fit_penalty)
    product.churn_rate = clamp_rate(product.churn_rate + BALANCE.price_increase_churn_rate_gain)

    adjusted_accounts = 0
    for account in customer_accounts:
        if account.product_id != product.id or account.status is CustomerAccountStatus.CHURNED:
            continue
        adjusted_accounts += 1
        account.contract_value = quantize_money(
            account.contract_value * BALANCE.price_increase_account_value_multiplier
        )
        satisfaction_loss = max(
            1,
            BALANCE.price_increase_account_satisfaction_loss_by_segment[account.segment.value]
            - (1 if account.annual_prepay else 0)
            - (1 if product.packaging_strategy is PackagingStrategy.SUITE else 0)
            - catalog_protection,
        )
        account.satisfaction = clamp_int(account.satisfaction - satisfaction_loss)
        account.renewal_health = clamp_int(
            account.renewal_health
            - max(
                1,
                BALANCE.price_increase_account_renewal_health_loss - catalog_protection,
            )
        )
        account.invoice_risk = clamp_int(
            account.invoice_risk
            + max(1, BALANCE.price_increase_account_invoice_risk_gain - catalog_protection)
        )
        account.churn_risk = clamp_int(
            account.churn_risk
            + max(1, BALANCE.price_increase_account_churn_risk_gain - catalog_protection)
        )

    return PriceIncreaseSummary(
        message=(
            f"Raised pricing on {product.name}. Base ARPU is now "
            f"{format_money(product.revenue_per_user)} with market fit "
            f"-{market_fit_penalty}, catalog protection {catalog_protection}, "
            f"and {adjusted_accounts} account(s) repriced."
        )
    )


def apply_run_add_on_campaign(
    product: Product,
    customer_accounts: list[CustomerAccount],
) -> AddOnCampaignSummary:
    """Push add-on monetization across one product's active account base."""

    if product.packaging_strategy is PackagingStrategy.STREAMLINED:
        raise ValueError("Streamlined products do not have enough add-on surface for a campaign.")
    existing_surface = any(
        account.product_id == product.id
        and account.status is not CustomerAccountStatus.CHURNED
        and account.add_on_count > 0
        for account in customer_accounts
    )
    if (
        product.add_on_catalog_depth < BALANCE.add_on_campaign_min_catalog_depth
        and not existing_surface
    ):
        raise ValueError("Expand the add-on catalog before running a broader add-on campaign.")

    converted_accounts = 0
    contract_gain = quantize_money(
        BALANCE.add_on_campaign_contract_gain
        + (Decimal(product.add_on_catalog_depth) * BALANCE.add_on_catalog_contract_gain_per_depth)
    )
    for account in customer_accounts:
        if account.product_id != product.id or account.status is CustomerAccountStatus.CHURNED:
            continue
        if account.satisfaction < 60 or account.expansion_potential < 40:
            continue
        account.add_on_count += BALANCE.add_on_campaign_add_on_gain
        account.contract_value = quantize_money(account.contract_value + contract_gain)
        account.support_load = clamp_int(
            account.support_load + BALANCE.add_on_campaign_support_load_gain
        )
        account.open_tickets += BALANCE.add_on_campaign_ticket_gain
        account.expansion_potential = clamp_int(account.expansion_potential - 3)
        converted_accounts += 1

    if converted_accounts == 0:
        raise ValueError("No active accounts are healthy enough for an add-on campaign.")

    product.technical_debt = clamp_int(
        product.technical_debt
        + BALANCE.add_on_campaign_debt_gain
        + max(0, product.add_on_catalog_depth - 1)
    )
    product.market_fit = clamp_int(product.market_fit + 1)
    return AddOnCampaignSummary(
        message=(
            f"Ran an add-on campaign for {product.name}. "
            f"{converted_accounts} account(s) expanded and debt +"
            f"{BALANCE.add_on_campaign_debt_gain}."
        )
    )


def apply_run_package_migration(
    product: Product,
    customer_accounts: list[CustomerAccount],
) -> PackagingMigrationSummary:
    """Migrate linked accounts toward the product's current package posture."""

    migrated_accounts = 0
    upgraded_accounts = 0
    downgraded_accounts = 0
    for account in customer_accounts:
        if account.product_id != product.id or account.status is CustomerAccountStatus.CHURNED:
            continue
        target_package = determine_target_subscription_package(product, account)
        if account.subscription_package is target_package:
            continue
        migrated_accounts += 1
        rank_delta = _package_rank(target_package) - _package_rank(account.subscription_package)
        upgrade_gain = quantize_money(
            (
                BALANCE.packaging_migration_upgrade_contract_gain
                + (
                    Decimal(product.package_catalog_depth)
                    * BALANCE.packaging_catalog_contract_gain_per_depth
                )
            )
            * Decimal(max(1, abs(rank_delta)))
        )
        if rank_delta > 0:
            upgraded_accounts += 1
            account.contract_value = quantize_money(account.contract_value + upgrade_gain)
            account.add_on_count += BALANCE.packaging_migration_add_on_gain + max(
                0, product.add_on_catalog_depth // 2
            )
            account.satisfaction = clamp_int(account.satisfaction - 1)
            account.support_load = clamp_int(account.support_load + 1)
            account.invoice_risk = clamp_int(
                account.invoice_risk + BALANCE.packaging_migration_upgrade_invoice_risk_gain
            )
            account.renewal_health = clamp_int(
                account.renewal_health + BALANCE.packaging_migration_upgrade_renewal_health_gain
            )
            if target_package is SubscriptionPackage.ENTERPRISE_SUITE:
                account.plan_tier = PricingTier.PREMIUM
                account.annual_prepay = True
        else:
            downgraded_accounts += 1
            account.contract_value = quantize_money(
                max(
                    Decimal("0.00"),
                    account.contract_value - BALANCE.packaging_migration_downgrade_contract_loss,
                )
            )
            account.open_tickets = max(
                0,
                account.open_tickets - BALANCE.packaging_migration_ticket_relief,
            )
            account.churn_risk = clamp_int(
                account.churn_risk - BALANCE.packaging_migration_churn_relief
            )
            account.invoice_risk = clamp_int(
                account.invoice_risk - BALANCE.packaging_migration_downgrade_invoice_risk_relief
            )
            account.support_load = clamp_int(
                account.support_load - BALANCE.packaging_migration_downgrade_support_load_relief
            )
        account.subscription_package = target_package

    if migrated_accounts == 0:
        raise ValueError("Linked accounts are already aligned with this package posture.")

    return PackagingMigrationSummary(
        message=(
            f"Migrated {migrated_accounts} account(s) for {product.name}: "
            f"{upgraded_accounts} upgraded, {downgraded_accounts} simplified."
        )
    )


def apply_expand_package_catalog(
    company: Company,
    product: Product,
    customer_accounts: list[CustomerAccount],
) -> CatalogExpansionSummary:
    """Spend cash to improve package depth and enterprise-ready packaging."""

    if product.package_catalog_depth >= 10:
        raise ValueError(f"{product.name} already has a deep package catalog.")
    if company.cash_on_hand < BALANCE.package_catalog_expand_cost:
        raise ValueError("Not enough cash to expand the package catalog.")

    company.cash_on_hand = quantize_money(
        company.cash_on_hand - BALANCE.package_catalog_expand_cost
    )
    product.package_catalog_depth += BALANCE.package_catalog_expand_depth_gain
    product.market_fit = clamp_int(
        product.market_fit + BALANCE.package_catalog_expand_market_fit_gain
    )
    prepared_accounts = 0
    for account in customer_accounts:
        if account.product_id != product.id or account.status is CustomerAccountStatus.CHURNED:
            continue
        account.renewal_health = clamp_int(
            account.renewal_health + BALANCE.package_catalog_expand_account_health_gain
        )
        account.expansion_potential = clamp_int(
            account.expansion_potential + BALANCE.package_catalog_expand_account_expansion_gain
        )
        prepared_accounts += 1
    return CatalogExpansionSummary(
        message=(
            f"Expanded package catalog for {product.name}. "
            f"Depth {product.package_catalog_depth}, prepared {prepared_accounts} account(s), "
            f"cash -{BALANCE.package_catalog_expand_cost}."
        )
    )


def apply_expand_add_on_catalog(
    company: Company,
    product: Product,
    customer_accounts: list[CustomerAccount],
) -> CatalogExpansionSummary:
    """Spend cash to deepen add-on surface for one product."""

    if product.add_on_catalog_depth >= 10:
        raise ValueError(f"{product.name} already has a deep add-on catalog.")
    if company.cash_on_hand < BALANCE.add_on_catalog_expand_cost:
        raise ValueError("Not enough cash to expand the add-on catalog.")

    company.cash_on_hand = quantize_money(company.cash_on_hand - BALANCE.add_on_catalog_expand_cost)
    product.add_on_catalog_depth += BALANCE.add_on_catalog_expand_depth_gain
    product.technical_debt = clamp_int(
        product.technical_debt + BALANCE.add_on_catalog_expand_debt_gain
    )
    primed_accounts = 0
    for account in customer_accounts:
        if account.product_id != product.id or account.status is CustomerAccountStatus.CHURNED:
            continue
        account.expansion_potential = clamp_int(
            account.expansion_potential + BALANCE.add_on_catalog_expand_account_expansion_gain
        )
        account.support_load = clamp_int(
            account.support_load + BALANCE.add_on_catalog_expand_account_support_load_gain
        )
        primed_accounts += 1
    return CatalogExpansionSummary(
        message=(
            f"Expanded add-on catalog for {product.name}. "
            f"Depth {product.add_on_catalog_depth}, primed {primed_accounts} account(s), "
            f"cash -{BALANCE.add_on_catalog_expand_cost}."
        )
    )


def _package_rank(package: SubscriptionPackage) -> int:
    if package is SubscriptionPackage.STARTER:
        return 0
    if package is SubscriptionPackage.GROWTH:
        return 1
    return 2
