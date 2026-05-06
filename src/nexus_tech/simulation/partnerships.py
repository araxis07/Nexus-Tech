"""Partnership and channel-scale simulation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from nexus_tech.domain.constants import ZERO_MONEY
from nexus_tech.domain.models import (
    CapitalPlanMode,
    GameState,
    PartnerChannel,
    PartnershipDeal,
    PartnershipStatus,
    Product,
)
from nexus_tech.domain.money import format_money, quantize_money, quantize_rate
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


@dataclass(frozen=True)
class PartnershipPortfolioSummary:
    """Aggregated channel-health summary for dashboards and reports."""

    total_count: int
    active_count: int
    strained_count: int
    recovery_count: int
    paused_count: int
    dominant_channel: str
    sourced_revenue: Decimal
    sourced_users: int
    average_quality: int
    average_risk: int
    average_fatigue: int
    fatigued_count: int
    neglected_count: int
    recovery_ready_count: int
    renegotiation_ready_count: int
    channel_conflict_index: int
    dominant_share_percent: int
    paused_revenue_share_percent: int
    channel_dependency_risk: int
    direct_sales_conflict_accounts: int
    weighted_rev_share_percent: int
    fatigued_revenue_share_percent: int
    recovery_revenue_share_percent: int
    volatile_revenue_share_percent: int
    concentration_risk: int
    renegotiation_pressure: int
    rev_share_pressure: int
    fatigue_hotspot_count: int
    commercial_dependency_score: int
    hotspot_channel: str
    channel_mix_note: str
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
        last_review_turn=state.company.current_turn,
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
    minimum_rev_share = BALANCE.partnership_min_rev_share_by_channel[partnership.channel.value]
    partnership.rev_share_rate = max(
        minimum_rev_share,
        quantize_rate(partnership.rev_share_rate - BALANCE.partnership_enablement_rev_share_relief),
    )
    partnership.risk = clamp_int(partnership.risk - BALANCE.partnership_enablement_risk_relief)
    partnership.conflict_pressure = clamp_int(
        partnership.conflict_pressure - BALANCE.partnership_enablement_conflict_relief
    )
    partnership.last_review_turn = state.company.current_turn
    fatigue = calculate_partnership_fatigue(state, partnership)
    if fatigue <= BALANCE.partnership_recovery_resume_threshold and (
        partnership.risk <= BALANCE.partnership_resume_threshold
        and partnership.conflict_pressure <= BALANCE.partnership_resume_threshold
    ):
        partnership.status = PartnershipStatus.ACTIVE
    elif partnership.status in {PartnershipStatus.PAUSED, PartnershipStatus.RECOVERY}:
        partnership.status = PartnershipStatus.RECOVERY
    return PartnershipActionSummary(
        message=(
            f"Invested in {partnership.name}. Cash -{BALANCE.partnership_enablement_cost}, "
            f"enablement +{BALANCE.partnership_enablement_gain}."
        )
    )


def renegotiate_partnership(
    state: GameState,
    partnership_id: UUID,
) -> PartnershipActionSummary:
    """Trade economics for a calmer partner relationship."""

    partnership = get_partnership_by_id(state.partnerships, partnership_id)
    if state.company.cash_on_hand < BALANCE.partnership_renegotiation_cost:
        raise ValueError("Not enough cash to renegotiate this partnership.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.partnership_renegotiation_cost
    )
    partnership.rev_share_rate = min(
        BALANCE.partnership_max_rev_share_by_channel[partnership.channel.value],
        quantize_rate(
            partnership.rev_share_rate + BALANCE.partnership_renegotiation_rev_share_penalty
        ),
    )
    partnership.enablement_level = clamp_int(
        partnership.enablement_level + BALANCE.partnership_renegotiation_enablement_gain
    )
    partnership.risk = clamp_int(partnership.risk - BALANCE.partnership_renegotiation_risk_relief)
    partnership.conflict_pressure = clamp_int(
        partnership.conflict_pressure - BALANCE.partnership_renegotiation_conflict_relief
    )
    partnership.last_review_turn = state.company.current_turn
    fatigue = calculate_partnership_fatigue(state, partnership)
    if partnership.status is PartnershipStatus.PAUSED:
        partnership.status = PartnershipStatus.RECOVERY
    elif fatigue <= BALANCE.partnership_recovery_resume_threshold:
        partnership.status = PartnershipStatus.ACTIVE
    else:
        partnership.status = PartnershipStatus.RECOVERY
    partnership.summary = (
        f"{partnership.name} was renegotiated. Rev-share is now "
        f"{partnership.rev_share_rate:.2%}, risk {partnership.risk}, conflict "
        f"{partnership.conflict_pressure}."
    )
    return PartnershipActionSummary(
        message=(
            f"Renegotiated {partnership.name}. Cash -{BALANCE.partnership_renegotiation_cost}, "
            f"rev-share now {partnership.rev_share_rate:.2%}."
        )
    )


def reactivate_partnership(
    state: GameState,
    partnership_id: UUID,
) -> PartnershipActionSummary:
    """Spend directly to recover or resume a paused/strained channel."""

    partnership = get_partnership_by_id(state.partnerships, partnership_id)
    if state.company.cash_on_hand < BALANCE.partnership_reactivation_cost:
        raise ValueError("Not enough cash to run a channel recovery plan.")

    fatigue = calculate_partnership_fatigue(state, partnership)
    if (
        partnership.status is PartnershipStatus.ACTIVE
        and fatigue < BALANCE.partnership_fatigue_strained_threshold
    ):
        raise ValueError("This partnership does not currently need a recovery plan.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.partnership_reactivation_cost
    )
    partnership.enablement_level = clamp_int(
        partnership.enablement_level + BALANCE.partnership_reactivation_enablement_gain
    )
    partnership.quality = clamp_int(
        partnership.quality + BALANCE.partnership_reactivation_quality_gain
    )
    partnership.risk = clamp_int(partnership.risk - BALANCE.partnership_reactivation_risk_relief)
    partnership.conflict_pressure = clamp_int(
        partnership.conflict_pressure - BALANCE.partnership_reactivation_conflict_relief
    )
    partnership.last_review_turn = state.company.current_turn
    updated_fatigue = calculate_partnership_fatigue(state, partnership)
    if (
        partnership.risk < BALANCE.partnership_resume_threshold
        and partnership.conflict_pressure < BALANCE.partnership_resume_threshold
        and updated_fatigue <= BALANCE.partnership_recovery_resume_threshold
    ):
        partnership.status = PartnershipStatus.ACTIVE
    else:
        partnership.status = PartnershipStatus.RECOVERY
    partnership.summary = (
        f"{partnership.name} entered {partnership.status.value} after a channel recovery plan. "
        f"Risk {partnership.risk}, conflict {partnership.conflict_pressure}, fatigue "
        f"{updated_fatigue}."
    )
    return PartnershipActionSummary(
        message=(
            f"Ran channel recovery for {partnership.name}. "
            f"Cash -{BALANCE.partnership_reactivation_cost}."
        )
    )


def apply_end_of_turn_partnerships(state: GameState) -> PartnershipTurnSummary:
    """Apply channel-driven user, support, and revenue effects."""

    sourced_revenue = ZERO_MONEY
    sourced_users = 0
    service_cost = ZERO_MONEY
    reputation_delta = 0
    active_channel_count_by_product = {
        product.id: sum(
            1
            for partnership in state.partnerships
            if partnership.product_id == product.id
            and partnership.status is not PartnershipStatus.PAUSED
        )
        for product in state.products
    }
    active_accounts_by_product = {
        product.id: sum(
            1
            for account in state.customer_accounts
            if account.product_id == product.id and account.status.value != "churned"
        )
        for product in state.products
    }

    for partnership in state.partnerships:
        product = _get_product_by_id(state.products, partnership.product_id)
        neglected_turns = state.company.current_turn - (
            partnership.last_review_turn or partnership.started_turn
        )

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
                calculate_partnership_fatigue(state, partnership)
                <= BALANCE.partnership_resume_threshold
            ):
                partnership.status = PartnershipStatus.RECOVERY
            continue

        capital_bonus = 0
        if state.capital_plan.mode is CapitalPlanMode.EXPAND:
            capital_bonus += BALANCE.partnership_expand_mode_user_bonus
        capital_bonus += (
            state.capital_plan.go_to_market_share // BALANCE.partnership_gtm_share_user_divisor
        )
        opening_fatigue = calculate_partnership_fatigue(state, partnership)
        user_gain = max(
            0,
            BALANCE.partnership_base_user_gain_by_channel[partnership.channel.value]
            + (partnership.enablement_level // BALANCE.partnership_enablement_user_bonus_divisor)
            + (product.market_fit // BALANCE.partnership_market_fit_user_bonus_divisor)
            + (product.quality // BALANCE.partnership_quality_user_bonus_divisor)
            + capital_bonus
            - (product.bug_level // BALANCE.partnership_bug_user_penalty_divisor)
            - (partnership.conflict_pressure // 25),
        )
        user_gain = max(
            0,
            user_gain - (opening_fatigue // BALANCE.partnership_fatigue_user_penalty_divisor),
        )
        if neglected_turns > BALANCE.partnership_neglect_turn_threshold:
            user_gain = max(
                0,
                user_gain
                - (
                    (neglected_turns - BALANCE.partnership_neglect_turn_threshold)
                    * BALANCE.partnership_neglect_user_penalty
                ),
            )
        if partnership.status is PartnershipStatus.STRAINED:
            user_gain = max(0, user_gain - BALANCE.partnership_strained_user_penalty)
        if partnership.status is PartnershipStatus.RECOVERY:
            user_gain = max(0, user_gain - BALANCE.partnership_recovery_user_penalty)
            partnership.conflict_pressure = clamp_int(
                partnership.conflict_pressure - BALANCE.partnership_recovery_conflict_relief
            )
            partnership.risk = clamp_int(
                partnership.risk - BALANCE.partnership_recovery_risk_relief
            )

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
            - (
                state.capital_plan.product_investment_share
                // BALANCE.partnership_product_share_risk_relief_divisor
            )
        )
        conflict_delta = BALANCE.partnership_channel_conflict_gain[partnership.channel.value]
        if product.pricing_tier.value == "premium":
            conflict_delta += BALANCE.partnership_premium_conflict_bonus
        conflict_delta += BALANCE.partnership_packaging_conflict_bonus[
            product.packaging_strategy.value
        ]
        direct_sales_conflict = (
            active_accounts_by_product.get(product.id, 0)
            // BALANCE.partnership_direct_sales_conflict_account_divisor
        ) + (
            state.capital_plan.go_to_market_share
            // BALANCE.partnership_direct_sales_conflict_gtm_share_divisor
        )
        if any(
            account.product_id == product.id and account.segment.value == "enterprise"
            for account in state.customer_accounts
            if account.status.value != "churned"
        ):
            direct_sales_conflict += BALANCE.partnership_direct_sales_conflict_enterprise_bonus
        conflict_delta += direct_sales_conflict
        conflict_delta += (
            max(
                0,
                active_channel_count_by_product.get(product.id, 1) - 1,
            )
            * BALANCE.partnership_multi_channel_conflict_bonus
        )
        if neglected_turns > BALANCE.partnership_neglect_turn_threshold:
            risk_delta += (
                neglected_turns - BALANCE.partnership_neglect_turn_threshold
            ) * BALANCE.partnership_neglect_risk_gain
            conflict_delta += (
                neglected_turns - BALANCE.partnership_neglect_turn_threshold
            ) * BALANCE.partnership_neglect_conflict_gain
        if partnership.status is PartnershipStatus.STRAINED:
            conflict_delta += 1

        partnership.risk = clamp_int(partnership.risk + risk_delta)
        partnership.conflict_pressure = clamp_int(partnership.conflict_pressure + conflict_delta)
        if (
            user_gain >= BALANCE.partnership_maturity_quality_gain_threshold
            and partnership.risk < BALANCE.partnership_risk_strained_threshold
            and partnership.conflict_pressure < BALANCE.partnership_conflict_strained_threshold
        ):
            partnership.quality = clamp_int(
                partnership.quality + BALANCE.partnership_maturity_quality_gain
            )
        if (
            partnership.sourced_revenue >= BALANCE.partnership_revenue_milestone_rev_share_threshold
            and partnership.rev_share_rate
            > BALANCE.partnership_min_rev_share_by_channel[partnership.channel.value]
        ):
            partnership.rev_share_rate = max(
                BALANCE.partnership_min_rev_share_by_channel[partnership.channel.value],
                quantize_rate(
                    partnership.rev_share_rate - BALANCE.partnership_enablement_rev_share_relief
                ),
            )
        previous_status = partnership.status
        fatigue = calculate_partnership_fatigue(state, partnership)
        if fatigue >= BALANCE.partnership_fatigue_strained_threshold:
            partnership.enablement_level = clamp_int(
                partnership.enablement_level - BALANCE.partnership_high_fatigue_enablement_decay
            )
            partnership.rev_share_rate = min(
                BALANCE.partnership_max_rev_share_by_channel[partnership.channel.value],
                quantize_rate(
                    partnership.rev_share_rate + BALANCE.partnership_high_fatigue_rev_share_creep
                ),
            )
        if fatigue >= BALANCE.partnership_fatigue_pause_threshold:
            partnership.conflict_pressure = clamp_int(
                partnership.conflict_pressure + BALANCE.partnership_high_fatigue_conflict_gain
            )
        if partnership.status is PartnershipStatus.RECOVERY:
            partnership.rev_share_rate = max(
                BALANCE.partnership_min_rev_share_by_channel[partnership.channel.value],
                quantize_rate(
                    partnership.rev_share_rate - BALANCE.partnership_recovery_rev_share_relief
                ),
            )
            if fatigue <= BALANCE.partnership_recovery_resume_threshold:
                partnership.quality = clamp_int(partnership.quality + 1)
        if (
            partnership.risk >= BALANCE.partnership_pause_threshold
            or partnership.conflict_pressure >= BALANCE.partnership_pause_threshold
            or fatigue >= BALANCE.partnership_fatigue_pause_threshold
        ):
            partnership.status = PartnershipStatus.PAUSED
        elif previous_status is PartnershipStatus.RECOVERY:
            if (
                fatigue <= BALANCE.partnership_recovery_resume_threshold
                and partnership.risk < BALANCE.partnership_resume_threshold
                and partnership.conflict_pressure < BALANCE.partnership_resume_threshold
            ):
                partnership.status = PartnershipStatus.ACTIVE
            else:
                partnership.status = PartnershipStatus.RECOVERY
        elif (
            partnership.risk >= BALANCE.partnership_risk_strained_threshold
            or partnership.conflict_pressure >= BALANCE.partnership_conflict_strained_threshold
            or fatigue >= BALANCE.partnership_fatigue_strained_threshold
        ):
            partnership.status = PartnershipStatus.STRAINED
        else:
            partnership.status = PartnershipStatus.ACTIVE

        if (
            partnership.status is PartnershipStatus.STRAINED
            and fatigue >= BALANCE.partnership_fatigue_strained_threshold
        ):
            partnership.quality = clamp_int(partnership.quality - 1)

        if partnership.status is PartnershipStatus.STRAINED:
            reputation_delta -= BALANCE.partnership_strained_reputation_loss
        if previous_status is not partnership.status:
            partnership.summary = (
                f"{partnership.name} is now {partnership.status.value} after conflict "
                f"{partnership.conflict_pressure}, risk {partnership.risk}, "
                f"and fatigue {fatigue}."
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


def calculate_partnership_portfolio(state: GameState) -> PartnershipPortfolioSummary:
    """Summarize channel-health and sourced contribution across active deals."""

    if not state.partnerships:
        return PartnershipPortfolioSummary(
            total_count=0,
            active_count=0,
            strained_count=0,
            recovery_count=0,
            paused_count=0,
            dominant_channel="-",
            sourced_revenue=ZERO_MONEY,
            sourced_users=0,
            average_quality=0,
            average_risk=0,
            average_fatigue=0,
            fatigued_count=0,
            neglected_count=0,
            recovery_ready_count=0,
            renegotiation_ready_count=0,
            channel_conflict_index=0,
            dominant_share_percent=0,
            paused_revenue_share_percent=0,
            channel_dependency_risk=0,
            direct_sales_conflict_accounts=0,
            weighted_rev_share_percent=0,
            fatigued_revenue_share_percent=0,
            recovery_revenue_share_percent=0,
            volatile_revenue_share_percent=0,
            concentration_risk=0,
            renegotiation_pressure=0,
            rev_share_pressure=0,
            fatigue_hotspot_count=0,
            commercial_dependency_score=0,
            hotspot_channel="-",
            channel_mix_note="No active channel portfolio yet.",
            summary="No active channel portfolio yet.",
        )

    channel_counts: dict[str, int] = {}
    for partnership in state.partnerships:
        channel_counts[partnership.channel.value] = (
            channel_counts.get(partnership.channel.value, 0) + 1
        )
    dominant_channel = max(channel_counts.items(), key=lambda item: item[1])[0]
    sourced_revenue = quantize_money(
        sum((partnership.sourced_revenue for partnership in state.partnerships), ZERO_MONEY)
    )
    sourced_users = sum(partnership.sourced_users for partnership in state.partnerships)
    active_count = sum(
        1 for partnership in state.partnerships if partnership.status is PartnershipStatus.ACTIVE
    )
    strained_count = sum(
        1 for partnership in state.partnerships if partnership.status is PartnershipStatus.STRAINED
    )
    recovery_count = sum(
        1 for partnership in state.partnerships if partnership.status is PartnershipStatus.RECOVERY
    )
    paused_count = sum(
        1 for partnership in state.partnerships if partnership.status is PartnershipStatus.PAUSED
    )
    fatigue_scores = [
        calculate_partnership_fatigue(state, partnership) for partnership in state.partnerships
    ]
    average_quality = sum(partnership.quality for partnership in state.partnerships) // len(
        state.partnerships
    )
    average_risk = sum(partnership.risk for partnership in state.partnerships) // len(
        state.partnerships
    )
    average_fatigue = sum(fatigue_scores) // len(fatigue_scores)
    neglected_count = sum(
        1
        for partnership in state.partnerships
        if state.company.current_turn - (partnership.last_review_turn or partnership.started_turn)
        > BALANCE.partnership_neglect_turn_threshold
    )
    recovery_ready_count = sum(
        1
        for partnership, fatigue in zip(state.partnerships, fatigue_scores, strict=False)
        if partnership.status in {PartnershipStatus.PAUSED, PartnershipStatus.RECOVERY}
        and partnership.risk < BALANCE.partnership_resume_threshold
        and partnership.conflict_pressure < BALANCE.partnership_resume_threshold
        and fatigue <= BALANCE.partnership_recovery_resume_threshold
    )
    renegotiation_ready_count = sum(
        1
        for partnership, fatigue in zip(state.partnerships, fatigue_scores, strict=False)
        if partnership.status is not PartnershipStatus.PAUSED
        and partnership.sourced_revenue > ZERO_MONEY
        and fatigue >= BALANCE.partnership_renegotiation_ready_fatigue_threshold
    )
    fatigued_count = sum(
        1 for fatigue in fatigue_scores if fatigue >= BALANCE.partnership_fatigue_strained_threshold
    )
    channel_conflict_index = sum(
        partnership.conflict_pressure for partnership in state.partnerships
    ) // len(state.partnerships)
    dominant_share_percent = int(
        ((channel_counts.get(dominant_channel, 0) / max(1, len(state.partnerships))) * 100)
    )
    paused_revenue = quantize_money(
        sum(
            (
                partnership.sourced_revenue
                for partnership in state.partnerships
                if partnership.status is PartnershipStatus.PAUSED
            ),
            ZERO_MONEY,
        )
    )
    paused_revenue_share_percent = (
        int((paused_revenue / sourced_revenue * Decimal("100")).to_integral_value())
        if sourced_revenue > ZERO_MONEY
        else 0
    )
    fatigued_revenue = quantize_money(
        sum(
            (
                partnership.sourced_revenue
                for partnership, fatigue in zip(state.partnerships, fatigue_scores, strict=False)
                if fatigue >= BALANCE.partnership_fatigue_strained_threshold
            ),
            ZERO_MONEY,
        )
    )
    fatigued_revenue_share_percent = (
        int((fatigued_revenue / sourced_revenue * Decimal("100")).to_integral_value())
        if sourced_revenue > ZERO_MONEY
        else 0
    )
    recovery_revenue = quantize_money(
        sum(
            (
                partnership.sourced_revenue
                for partnership in state.partnerships
                if partnership.status in {PartnershipStatus.RECOVERY, PartnershipStatus.PAUSED}
            ),
            ZERO_MONEY,
        )
    )
    recovery_revenue_share_percent = (
        int((recovery_revenue / sourced_revenue * Decimal("100")).to_integral_value())
        if sourced_revenue > ZERO_MONEY
        else 0
    )
    volatile_revenue = quantize_money(
        sum(
            (
                partnership.sourced_revenue
                for partnership, fatigue in zip(state.partnerships, fatigue_scores, strict=False)
                if partnership.status in {PartnershipStatus.STRAINED, PartnershipStatus.RECOVERY}
                or fatigue >= BALANCE.partnership_fatigue_strained_threshold
            ),
            ZERO_MONEY,
        )
    )
    volatile_revenue_share_percent = (
        int((volatile_revenue / sourced_revenue * Decimal("100")).to_integral_value())
        if sourced_revenue > ZERO_MONEY
        else 0
    )
    direct_sales_conflict_accounts = sum(
        1
        for account in state.customer_accounts
        if account.status.value != "churned"
        and any(
            partnership.product_id == account.product_id
            and partnership.status is not PartnershipStatus.PAUSED
            for partnership in state.partnerships
        )
    )
    weighted_rev_share_percent = (
        int(
            (
                sum(
                    partnership.rev_share_rate * Decimal("100")
                    for partnership in state.partnerships
                )
                / Decimal(len(state.partnerships))
            ).to_integral_value()
        )
        if state.partnerships
        else 0
    )
    fatigue_hotspot_count = sum(
        1
        for partnership, fatigue in zip(state.partnerships, fatigue_scores, strict=False)
        if partnership.sourced_revenue > ZERO_MONEY
        and fatigue >= BALANCE.partnership_fatigue_strained_threshold
    )
    channel_scores = {
        channel: 0 for channel in {partnership.channel.value for partnership in state.partnerships}
    }
    for partnership, fatigue in zip(state.partnerships, fatigue_scores, strict=False):
        channel_scores[partnership.channel.value] += (
            partnership.conflict_pressure
            + partnership.risk
            + fatigue
            + int((partnership.rev_share_rate * Decimal("100")).to_integral_value())
        )
    hotspot_channel = max(channel_scores.items(), key=lambda item: item[1])[0]
    channel_dependency_risk = clamp_int(
        (dominant_share_percent // 2)
        + (channel_conflict_index // 2)
        + (average_risk // 3)
        + (strained_count * BALANCE.partnership_dependency_risk_strained_bonus)
        + (paused_count * BALANCE.partnership_dependency_risk_paused_bonus)
        + (direct_sales_conflict_accounts // 2)
    )
    concentration_risk = clamp_int(
        (dominant_share_percent // BALANCE.partnership_concentration_share_divisor)
        + direct_sales_conflict_accounts
        + (
            fatigued_revenue_share_percent
            // BALANCE.partnership_concentration_fatigued_share_divisor
        )
        + (paused_revenue_share_percent // 2)
    )
    renegotiation_pressure = clamp_int(
        (average_fatigue // BALANCE.partnership_renegotiation_pressure_fatigue_divisor)
        + renegotiation_ready_count
        + (
            weighted_rev_share_percent
            // BALANCE.partnership_renegotiation_pressure_rev_share_divisor
        )
        + (channel_conflict_index // BALANCE.partnership_renegotiation_pressure_conflict_divisor)
    )
    rev_share_pressure = clamp_int(
        (weighted_rev_share_percent // BALANCE.partnership_rev_share_pressure_divisor)
        + renegotiation_ready_count
        + (fatigued_revenue_share_percent // 10)
    )
    commercial_dependency_score = clamp_int(
        channel_dependency_risk
        + (concentration_risk // 2)
        + (rev_share_pressure // BALANCE.partnership_commercial_dependency_rev_share_divisor)
        + (volatile_revenue_share_percent // BALANCE.partnership_channel_volatility_share_divisor)
        + (fatigue_hotspot_count * BALANCE.partnership_channel_volatility_hotspot_bonus)
    )
    if hotspot_channel == "marketplace":
        channel_mix_note = (
            "Marketplace exposure is the sharpest source of current channel friction."
        )
    elif hotspot_channel == "integration":
        channel_mix_note = "Integration commitments are the main source of channel execution drag."
    else:
        channel_mix_note = "Reseller overlap is now the main commercial pressure inside channels."
    if commercial_dependency_score >= 70:
        summary = (
            "Channel economics are now concentrated enough to threaten the whole go-to-market mix."
        )
    elif volatile_revenue_share_percent >= 40:
        summary = (
            "A large share of partner revenue now sits inside strained or recovering channels."
        )
    elif paused_count > 0:
        summary = "Some channels are paused and need deliberate recovery before they can scale."
    elif concentration_risk >= 60:
        summary = "Channel revenue is getting concentrated and direct-sales overlap is rising."
    elif renegotiation_pressure >= 28:
        summary = "Partner economics are getting strained enough to demand active renegotiation."
    elif recovery_count > 0:
        summary = "At least one channel is recovering. Near-term growth is cleaner but slower."
    elif strained_count > 0:
        summary = "The partner portfolio is producing demand, but at least one lane is strained."
    else:
        summary = "The partner portfolio is contributing without visible channel distress."
    return PartnershipPortfolioSummary(
        total_count=len(state.partnerships),
        active_count=active_count,
        strained_count=strained_count,
        recovery_count=recovery_count,
        paused_count=paused_count,
        dominant_channel=dominant_channel,
        sourced_revenue=sourced_revenue,
        sourced_users=sourced_users,
        average_quality=average_quality,
        average_risk=average_risk,
        average_fatigue=average_fatigue,
        fatigued_count=fatigued_count,
        neglected_count=neglected_count,
        recovery_ready_count=recovery_ready_count,
        renegotiation_ready_count=renegotiation_ready_count,
        channel_conflict_index=channel_conflict_index,
        dominant_share_percent=dominant_share_percent,
        paused_revenue_share_percent=paused_revenue_share_percent,
        channel_dependency_risk=channel_dependency_risk,
        direct_sales_conflict_accounts=direct_sales_conflict_accounts,
        weighted_rev_share_percent=weighted_rev_share_percent,
        fatigued_revenue_share_percent=fatigued_revenue_share_percent,
        recovery_revenue_share_percent=recovery_revenue_share_percent,
        volatile_revenue_share_percent=volatile_revenue_share_percent,
        concentration_risk=concentration_risk,
        renegotiation_pressure=renegotiation_pressure,
        rev_share_pressure=rev_share_pressure,
        fatigue_hotspot_count=fatigue_hotspot_count,
        commercial_dependency_score=commercial_dependency_score,
        hotspot_channel=hotspot_channel,
        channel_mix_note=channel_mix_note,
        summary=summary,
    )


def calculate_partnership_fatigue(state: GameState, partnership: PartnershipDeal) -> int:
    """Estimate partner fatigue from neglect, overlap, risk, and channel friction."""

    product = _get_product_by_id(state.products, partnership.product_id)
    neglected_turns = state.company.current_turn - (
        partnership.last_review_turn or partnership.started_turn
    )
    active_channel_count = sum(
        1
        for candidate in state.partnerships
        if candidate.product_id == partnership.product_id
        and candidate.status is not PartnershipStatus.PAUSED
    )
    fatigue = (
        partnership.risk // BALANCE.partnership_fatigue_risk_divisor
        + partnership.conflict_pressure // BALANCE.partnership_fatigue_conflict_divisor
    )
    if neglected_turns > BALANCE.partnership_fatigue_neglect_turn_threshold:
        fatigue += (
            neglected_turns - BALANCE.partnership_fatigue_neglect_turn_threshold
        ) * BALANCE.partnership_fatigue_neglect_gain
    fatigue += max(0, active_channel_count - 1) * BALANCE.partnership_fatigue_multi_channel_gain
    if state.capital_plan.mode is CapitalPlanMode.EXPAND:
        fatigue += BALANCE.partnership_fatigue_expand_mode_gain
    if partnership.status is PartnershipStatus.RECOVERY:
        fatigue += BALANCE.partnership_fatigue_recovery_penalty
    if partnership.channel is PartnerChannel.INTEGRATION and product.technical_debt >= 40:
        fatigue += 3
    if partnership.channel is PartnerChannel.MARKETPLACE and product.add_on_catalog_depth < 2:
        fatigue += 2
    if partnership.channel is PartnerChannel.RESELLER and product.pricing_tier.value == "budget":
        fatigue += 2
    if product.packaging_strategy.value == "suite":
        fatigue += 2
    if partnership.rev_share_rate >= BALANCE.partnership_high_rev_share_fatigue_threshold:
        fatigue += BALANCE.partnership_high_rev_share_fatigue_gain
    return clamp_int(fatigue)


def _get_product_by_id(products: list[Product], product_id: UUID) -> Product:
    for product in products:
        if product.id == product_id:
            return product
    raise ValueError("Selected product was not found.")
