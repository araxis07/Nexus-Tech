"""Partnership and channel-scale simulation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from nexus_tech.domain.constants import ZERO_MONEY
from nexus_tech.domain.models import (
    GameState,
    PartnerChannel,
    PartnershipDeal,
    PartnershipStatus,
    Product,
)
from nexus_tech.domain.money import format_money, quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.product_progression import infer_lifecycle_stage
from nexus_tech.simulation.support import clamp_int


@dataclass(frozen=True)
class PartnershipActionSummary:
    """Human-readable outcome for one partnership action."""

    message: str


@dataclass(frozen=True)
class PartnershipTurnSummary:
    """Compact end-of-turn partnership summary."""

    sourced_revenue: Decimal
    sourced_users: int
    service_cost: Decimal
    reputation_delta: int
    summary: str


def get_partnership_by_id(
    partnerships: list[PartnershipDeal],
    partnership_id: UUID | None,
) -> PartnershipDeal:
    """Resolve one persisted partnership by identifier."""

    if partnership_id is None:
        raise ValueError("This action requires selecting a partnership.")
    for partnership in partnerships:
        if partnership.id == partnership_id:
            return partnership
    raise ValueError("Selected partnership was not found.")


def get_partnership_choices(
    state: GameState,
    *,
    actionable_only: bool = False,
) -> list[PartnershipDeal]:
    """Return partnerships available for review or enablement."""

    if not actionable_only:
        return list(state.partnerships)
    return [
        partnership
        for partnership in state.partnerships
        if partnership.status is not PartnershipStatus.PAUSED
    ]


def create_partnership(
    state: GameState,
    product_id: UUID,
    channel: PartnerChannel,
) -> PartnershipActionSummary:
    """Create one durable partnership for an active product."""

    product = _get_product_by_id(state.products, product_id)
    if not product.is_active:
        raise ValueError("Only active products can open new partnerships.")
    if any(
        partnership.product_id == product_id and partnership.channel is channel
        for partnership in state.partnerships
    ):
        raise ValueError(f"{product.name} already has a {channel.value} partnership.")

    creation_cost = BALANCE.partnership_creation_cost_by_channel[channel.value]
    if state.company.cash_on_hand < creation_cost:
        raise ValueError("Not enough cash to open this partnership.")

    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - creation_cost)
    partnership = PartnershipDeal(
        name=f"{product.name} {channel.value.replace('_', ' ').title()} Channel",
        product_id=product.id,
        channel=channel,
        quality=clamp_int(
            BALANCE.partnership_base_quality_by_channel[channel.value] + (product.market_fit // 12),
        ),
        risk=clamp_int(
            BALANCE.partnership_base_risk_by_channel[channel.value]
            + (product.bug_level // BALANCE.partnership_bug_risk_divisor),
        ),
        enablement_level=clamp_int(BALANCE.partnership_base_enablement_by_channel[channel.value]),
        rev_share_rate=BALANCE.partnership_base_rev_share_by_channel[channel.value],
        started_turn=state.company.current_turn,
        summary=f"Opened from {product.name} into the {channel.value} channel.",
    )
    state.partnerships.append(partnership)
    return PartnershipActionSummary(
        message=(f"Opened {channel.value} channel for {product.name}. Cash -{creation_cost}.")
    )


def invest_in_partner_enablement(
    state: GameState,
    partnership_id: UUID,
) -> PartnershipActionSummary:
    """Improve one partner relationship through enablement work."""

    partnership = get_partnership_by_id(state.partnerships, partnership_id)
    if state.company.cash_on_hand < BALANCE.partnership_enablement_cost:
        raise ValueError("Not enough cash to invest in partner enablement.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.partnership_enablement_cost
    )
    partnership.enablement_level = clamp_int(
        partnership.enablement_level + BALANCE.partnership_enablement_gain
    )
    partnership.quality = clamp_int(
        partnership.quality + BALANCE.partnership_enablement_quality_gain
    )
    partnership.risk = clamp_int(partnership.risk - BALANCE.partnership_enablement_risk_relief)
    partnership.conflict_pressure = clamp_int(
        partnership.conflict_pressure - BALANCE.partnership_enablement_conflict_relief
    )
    partnership.last_review_turn = state.company.current_turn
    if (
        partnership.status is PartnershipStatus.PAUSED
        and partnership.risk <= BALANCE.partnership_resume_threshold
        and partnership.conflict_pressure <= BALANCE.partnership_resume_threshold
    ) or (
        partnership.risk < BALANCE.partnership_risk_strained_threshold
        and partnership.conflict_pressure < BALANCE.partnership_conflict_strained_threshold
    ):
        partnership.status = PartnershipStatus.ACTIVE
    return PartnershipActionSummary(
        message=(
            f"Invested in {partnership.name}. Cash -{BALANCE.partnership_enablement_cost}, "
            f"enablement +{BALANCE.partnership_enablement_gain}."
        )
    )


def apply_end_of_turn_partnerships(state: GameState) -> PartnershipTurnSummary:
    """Apply channel-driven user, support, and revenue effects."""

    sourced_revenue = ZERO_MONEY
    sourced_users = 0
    service_cost = ZERO_MONEY
    reputation_delta = 0

    for partnership in state.partnerships:
        product = _get_product_by_id(state.products, partnership.product_id)
        partnership.last_review_turn = state.company.current_turn

        if not product.is_active:
            partnership.status = PartnershipStatus.PAUSED
            partnership.conflict_pressure = clamp_int(
                partnership.conflict_pressure - BALANCE.partnership_cooldown_conflict_relief
            )
            partnership.risk = clamp_int(
                partnership.risk - BALANCE.partnership_cooldown_risk_relief
            )
            continue

        if partnership.status is PartnershipStatus.PAUSED:
            partnership.conflict_pressure = clamp_int(
                partnership.conflict_pressure - BALANCE.partnership_cooldown_conflict_relief
            )
            partnership.risk = clamp_int(
                partnership.risk - BALANCE.partnership_cooldown_risk_relief
            )
            if (
                partnership.risk <= BALANCE.partnership_resume_threshold
                and partnership.conflict_pressure <= BALANCE.partnership_resume_threshold
            ):
                partnership.status = PartnershipStatus.STRAINED
            continue

        user_gain = max(
            0,
            BALANCE.partnership_base_user_gain_by_channel[partnership.channel.value]
            + (partnership.enablement_level // BALANCE.partnership_enablement_user_bonus_divisor)
            + (product.market_fit // BALANCE.partnership_market_fit_user_bonus_divisor)
            + (product.quality // BALANCE.partnership_quality_user_bonus_divisor)
            - (product.bug_level // BALANCE.partnership_bug_user_penalty_divisor)
            - (partnership.conflict_pressure // 25),
        )
        if partnership.status is PartnershipStatus.STRAINED:
            user_gain = max(0, user_gain - BALANCE.partnership_strained_user_penalty)

        gross_revenue = quantize_money(Decimal(user_gain) * product.revenue_per_user)
        net_revenue = quantize_money(
            gross_revenue * (Decimal("1.0000") - partnership.rev_share_rate)
        )
        partner_service_cost = quantize_money(
            Decimal(user_gain)
            * BALANCE.partnership_support_cost_per_user_by_channel[partnership.channel.value]
        )

        product.user_count += user_gain
        product.lifecycle_stage = infer_lifecycle_stage(product)
        partnership.sourced_users += user_gain
        partnership.sourced_revenue = quantize_money(partnership.sourced_revenue + net_revenue)

        lane_pressure = max(0, user_gain // 4)
        lane = BALANCE.partnership_lane_pressure_by_channel[partnership.channel.value]
        state.support_program.backlog_queue += lane_pressure
        if lane == "enterprise":
            state.support_program.enterprise_ticket_pressure += lane_pressure
        elif lane == "onboarding":
            state.support_program.onboarding_ticket_pressure += lane_pressure
        else:
            state.support_program.billing_ticket_pressure += lane_pressure

        risk_delta = (
            product.bug_level // BALANCE.partnership_bug_risk_divisor
            + product.technical_debt // BALANCE.partnership_debt_risk_divisor
            - product.quality // BALANCE.partnership_quality_risk_relief_divisor
            - partnership.enablement_level // 30
        )
        conflict_delta = BALANCE.partnership_channel_conflict_gain[partnership.channel.value]
        if product.pricing_tier.value == "premium":
            conflict_delta += BALANCE.partnership_premium_conflict_bonus
        conflict_delta += BALANCE.partnership_packaging_conflict_bonus[
            product.packaging_strategy.value
        ]
        if partnership.status is PartnershipStatus.STRAINED:
            conflict_delta += 1

        partnership.risk = clamp_int(partnership.risk + risk_delta)
        partnership.conflict_pressure = clamp_int(partnership.conflict_pressure + conflict_delta)
        previous_status = partnership.status
        if (
            partnership.risk >= BALANCE.partnership_pause_threshold
            or partnership.conflict_pressure >= BALANCE.partnership_pause_threshold
        ):
            partnership.status = PartnershipStatus.PAUSED
        elif (
            partnership.risk >= BALANCE.partnership_risk_strained_threshold
            or partnership.conflict_pressure >= BALANCE.partnership_conflict_strained_threshold
        ):
            partnership.status = PartnershipStatus.STRAINED
        else:
            partnership.status = PartnershipStatus.ACTIVE

        if partnership.status is PartnershipStatus.STRAINED:
            reputation_delta -= BALANCE.partnership_strained_reputation_loss
        if previous_status is not partnership.status:
            partnership.summary = (
                f"{partnership.name} is now {partnership.status.value} after conflict "
                f"{partnership.conflict_pressure} and risk {partnership.risk}."
            )

        sourced_users += user_gain
        sourced_revenue = quantize_money(sourced_revenue + net_revenue)
        service_cost = quantize_money(service_cost + partner_service_cost)

    summary = (
        "No active partner contribution this turn."
        if sourced_users == 0 and sourced_revenue <= ZERO_MONEY
        else (
            f"Partners sourced {sourced_users} users and {format_money(sourced_revenue)} net "
            f"revenue."
        )
    )
    return PartnershipTurnSummary(
        sourced_revenue=sourced_revenue,
        sourced_users=sourced_users,
        service_cost=service_cost,
        reputation_delta=reputation_delta,
        summary=summary,
    )


def _get_product_by_id(products: list[Product], product_id: UUID) -> Product:
    for product in products:
        if product.id == product_id:
            return product
    raise ValueError("Selected product was not found.")
