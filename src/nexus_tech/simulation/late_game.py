"""Late-game portfolio pressure rules for renewal risk and legacy drag."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from nexus_tech.domain.models import LifecycleStage, Product
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.support import clamp_int


@dataclass(frozen=True)
class LateGameProductRisk:
    """Per-product late-game risks applied after a turn resolves."""

    product_id: UUID
    product_name: str
    renewal_risk: int
    legacy_drag: int
    user_loss: int


@dataclass(frozen=True)
class LateGameSummary:
    """Aggregate late-game drag across a larger portfolio."""

    total_risk: int
    concentration_risk: int
    renewal_risk: int
    legacy_drag: int
    org_drag: int
    maintenance_crisis: int
    innovation_gap: int
    added_cost: Decimal
    reputation_delta: int
    burnout_modifier: int
    summary: str
    product_risks: list[LateGameProductRisk]


def calculate_late_game_summary(
    products: list[Product],
    *,
    current_turn: int,
    headcount: int = 0,
) -> LateGameSummary:
    """Summarize late-game pressure once a portfolio reaches durable scale."""

    active_products = [product for product in products if product.is_active]
    if not active_products:
        return LateGameSummary(
            total_risk=0,
            concentration_risk=0,
            renewal_risk=0,
            legacy_drag=0,
            org_drag=0,
            maintenance_crisis=0,
            innovation_gap=0,
            added_cost=Decimal("0.00"),
            reputation_delta=0,
            burnout_modifier=0,
            summary="No late-game pressure is active yet.",
            product_risks=[],
        )

    total_users = sum(product.user_count for product in active_products)
    if (
        current_turn < BALANCE.late_game_turn_threshold
        or total_users < BALANCE.late_game_total_user_threshold
    ):
        return LateGameSummary(
            total_risk=0,
            concentration_risk=0,
            renewal_risk=0,
            legacy_drag=0,
            org_drag=0,
            maintenance_crisis=0,
            innovation_gap=0,
            added_cost=Decimal("0.00"),
            reputation_delta=0,
            burnout_modifier=0,
            summary="Late-game pressure has not fully arrived yet.",
            product_risks=[],
        )

    lead_product_users = max(product.user_count for product in active_products)
    lead_share = (lead_product_users * 100) // max(1, total_users)
    mature_products = [
        product
        for product in active_products
        if product.lifecycle_stage in {LifecycleStage.MATURE, LifecycleStage.DECLINING}
    ]
    growth_products = [
        product
        for product in active_products
        if product.lifecycle_stage in {LifecycleStage.PROTOTYPE, LifecycleStage.GROWTH}
    ]
    maintenance_total = sum(
        (product.maintenance_cost for product in active_products),
        Decimal("0.00"),
    )
    concentration_risk = max(
        0,
        lead_share - BALANCE.late_game_concentration_share_threshold,
    ) // BALANCE.late_game_concentration_divisor
    org_drag = max(
        0,
        len(active_products) - BALANCE.late_game_org_drag_product_threshold,
    ) + max(
        0,
        headcount - BALANCE.late_game_org_drag_headcount_threshold,
    ) // BALANCE.late_game_org_drag_divisor
    maintenance_crisis = max(
        0,
        int(
            (
                max(
                    Decimal("0.00"),
                    maintenance_total - BALANCE.late_game_maintenance_crisis_cost_threshold,
                )
                / BALANCE.late_game_maintenance_crisis_cost_divisor
            )
        ),
    )
    if len(mature_products) >= BALANCE.late_game_maintenance_crisis_mature_threshold:
        maintenance_crisis += 1
    innovation_gap = 0
    if (
        len(mature_products) >= BALANCE.late_game_innovation_gap_mature_threshold
        and len(growth_products) <= BALANCE.late_game_innovation_gap_growth_product_cap
    ):
        innovation_gap += 2
    if mature_products and all(
        product.technical_debt >= BALANCE.late_game_innovation_gap_debt_threshold
        for product in mature_products
    ):
        innovation_gap += 1

    product_risks: list[LateGameProductRisk] = []
    renewal_risk_total = 0
    legacy_drag_total = 0

    for product in active_products:
        renewal_risk = 0
        legacy_drag = 0

        if product.lifecycle_stage in {LifecycleStage.MATURE, LifecycleStage.DECLINING}:
            renewal_risk += max(
                0,
                product.user_count - BALANCE.late_game_large_product_user_threshold,
            ) // BALANCE.late_game_renewal_user_divisor
            if product.target_segment.value == "enterprise":
                renewal_risk += 1

        if product.bug_level >= BALANCE.late_game_bug_threshold:
            renewal_risk += 1 + (
                (product.bug_level - BALANCE.late_game_bug_threshold)
                // BALANCE.late_game_bug_divisor
            )
        if product.technical_debt >= BALANCE.late_game_debt_threshold:
            renewal_risk += 1 + (
                (product.technical_debt - BALANCE.late_game_debt_threshold)
                // BALANCE.late_game_debt_divisor
            )

        if product.lifecycle_stage is LifecycleStage.DECLINING:
            legacy_drag += BALANCE.late_game_declining_stage_legacy_bonus
        if product.feature_count > BALANCE.late_game_feature_overhang_threshold:
            legacy_drag += (
                product.feature_count - BALANCE.late_game_feature_overhang_threshold
            ) // BALANCE.late_game_feature_overhang_divisor
        if product.user_count >= BALANCE.late_game_large_product_user_threshold and (
            product.market_fit <= BALANCE.low_market_fit_threshold
        ):
            legacy_drag += 1

        user_loss = min(
            product.user_count,
            renewal_risk + min(2, legacy_drag),
            BALANCE.late_game_max_user_loss_per_product,
        )
        if renewal_risk > 0 or legacy_drag > 0:
            product_risks.append(
                LateGameProductRisk(
                    product_id=product.id,
                    product_name=product.name,
                    renewal_risk=renewal_risk,
                    legacy_drag=legacy_drag,
                    user_loss=user_loss,
                )
            )
        renewal_risk_total += renewal_risk
        legacy_drag_total += legacy_drag

    total_risk = (
        concentration_risk
        + renewal_risk_total
        + legacy_drag_total
        + org_drag
        + maintenance_crisis
        + innovation_gap
    )
    added_cost = quantize_money(Decimal(total_risk) * BALANCE.late_game_cost_per_point)
    reputation_delta = (
        -BALANCE.late_game_reputation_penalty
        if total_risk >= BALANCE.late_game_reputation_penalty_threshold
        else 0
    )
    burnout_modifier = min(
        BALANCE.late_game_max_burnout_modifier,
        total_risk // BALANCE.late_game_burnout_divisor,
    )

    if maintenance_crisis >= 3:
        summary = "Maintenance burden is starting to outgrow the portfolio."
    elif org_drag >= 3:
        summary = "Company coordination load is now slowing execution."
    elif innovation_gap >= 2:
        summary = "The portfolio is maturing faster than the next product bets are forming."
    elif total_risk >= 8:
        summary = "Renewal risk and legacy drag are now taxing the portfolio."
    elif concentration_risk > 0:
        summary = "One flagship is carrying too much of the company."
    elif renewal_risk_total > 0:
        summary = "Mature customers are asking more from the product portfolio."
    elif legacy_drag_total > 0:
        summary = "Legacy product drag is starting to slow the company down."
    else:
        summary = "Late-game pressure is under control."

    return LateGameSummary(
        total_risk=total_risk,
        concentration_risk=concentration_risk,
        renewal_risk=renewal_risk_total,
        legacy_drag=legacy_drag_total,
        org_drag=org_drag,
        maintenance_crisis=maintenance_crisis,
        innovation_gap=innovation_gap,
        added_cost=added_cost,
        reputation_delta=reputation_delta,
        burnout_modifier=burnout_modifier,
        summary=summary,
        product_risks=product_risks,
    )


def apply_end_of_turn_late_game(
    products: list[Product],
    *,
    current_turn: int,
    headcount: int = 0,
) -> LateGameSummary:
    """Apply late-game user and quality penalties after the main turn resolves."""

    summary = calculate_late_game_summary(
        products,
        current_turn=current_turn,
        headcount=headcount,
    )
    if summary.total_risk == 0:
        return summary

    product_map = {product.id: product for product in products}
    for product_risk in summary.product_risks:
        product = product_map.get(product_risk.product_id)
        if product is None:
            continue
        if product_risk.user_loss > 0:
            product.user_count = max(0, product.user_count - product_risk.user_loss)
        if product_risk.renewal_risk >= BALANCE.late_game_market_fit_penalty_threshold:
            product.market_fit = clamp_int(
                product.market_fit - BALANCE.late_game_market_fit_penalty
            )
        if product_risk.legacy_drag >= BALANCE.late_game_quality_penalty_threshold:
            product.quality = clamp_int(product.quality - BALANCE.late_game_quality_penalty)

    return summary
