"""Shared support tooling and backlog management."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import (
    CustomerAccount,
    CustomerAccountStatus,
    EmployeeRole,
    GameState,
    MarketSegment,
    SupportInvestmentFocus,
    SupportLaneFocus,
    SupportProgram,
    SupportTier,
)
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.support import clamp_int


@dataclass(frozen=True)
class SupportProgramSummary:
    """Company-wide support-system snapshot for one turn."""

    total_open_tickets: int
    effective_capacity: int
    deflected_tickets: int
    backlog_queue: int
    escalation_queue: int
    sla_breaches: int
    resolved_tickets: int
    deflection_score: int
    weighted_ticket_pressure: int
    staffing_gap: int
    queue_age_pressure: int
    onboarding_ticket_pressure: int
    enterprise_ticket_pressure: int
    billing_ticket_pressure: int
    revenue_at_risk_accounts: int
    revenue_at_risk_value: Decimal
    enterprise_revenue_at_risk_value: Decimal
    premium_revenue_at_risk_value: Decimal
    white_glove_revenue_at_risk_value: Decimal
    premium_queue_exposure_value: Decimal
    enterprise_queue_exposure_value: Decimal
    renewal_queue_exposure_value: Decimal
    premium_queue_risk_accounts: int
    enterprise_queue_risk_accounts: int
    renewal_queue_risk_accounts: int
    high_value_risk_accounts: int
    renewal_pressure_accounts: int
    renewal_pressure_value: Decimal
    priority_breach_accounts: int
    white_glove_breach_accounts: int
    white_glove_queue_risk_accounts: int
    severe_queue_accounts: int
    account_queue_risk_score: int
    lane_saturation_index: int
    hotspot_lane: SupportLaneFocus
    hotspot_lane_overflow: int
    hotspot_lane_account_count: int
    focus_alignment_gap: int
    recovery_ready_accounts: int
    sla_credit_cost: Decimal
    service_tier_pressure: int
    commercial_breach_pressure: int
    dominant_lane: SupportLaneFocus
    focus_mismatch_penalty: int
    lane_overflow_pressure: int
    service_cost: Decimal
    reputation_delta: int
    morale_penalty: int
    summary: str


@dataclass(frozen=True)
class SupportLaneSnapshot:
    """Lane-specific pressure versus staffed capacity."""

    lane: SupportLaneFocus
    pressure: int
    capacity: int
    overflow: int
    account_count: int


@dataclass(frozen=True)
class SupportQueueExposure:
    """Account-level support exposure that matters to financing and governance."""

    premium_queue_exposure_value: Decimal
    enterprise_queue_exposure_value: Decimal
    renewal_queue_exposure_value: Decimal
    premium_queue_risk_accounts: int
    enterprise_queue_risk_accounts: int
    renewal_queue_risk_accounts: int
    white_glove_queue_risk_accounts: int
    severe_queue_accounts: int
    lane_saturation_index: int
    hotspot_lane: SupportLaneFocus
    hotspot_lane_overflow: int
    hotspot_lane_account_count: int
    focus_alignment_gap: int


@dataclass(frozen=True)
class SupportOpsActionSummary:
    """Summary of an explicit support-ops intervention."""

    message: str


def calculate_support_account_risk_counts(state: GameState) -> tuple[int, int]:
    """Return account counts currently under commercial stress from support issues."""

    active_accounts = [
        account
        for account in state.customer_accounts
        if account.status is not CustomerAccountStatus.CHURNED
    ]
    revenue_at_risk_accounts = 0
    renewal_pressure_accounts = 0
    for account in active_accounts:
        if _is_revenue_at_risk_account(account, sla_target=state.support_program.sla_target):
            revenue_at_risk_accounts += 1
        if _is_renewal_pressure_account(account):
            renewal_pressure_accounts += 1
    return revenue_at_risk_accounts, renewal_pressure_accounts


def calculate_support_account_risk_values(state: GameState) -> tuple[Decimal, Decimal]:
    """Return contract value currently under support and renewal pressure."""

    active_accounts = [
        account
        for account in state.customer_accounts
        if account.status is not CustomerAccountStatus.CHURNED
    ]
    revenue_at_risk_value = Decimal("0.00")
    renewal_pressure_value = Decimal("0.00")
    for account in active_accounts:
        if _is_revenue_at_risk_account(account, sla_target=state.support_program.sla_target):
            revenue_at_risk_value += account.contract_value
        if _is_renewal_pressure_account(account):
            renewal_pressure_value += account.contract_value
    return quantize_money(revenue_at_risk_value), quantize_money(renewal_pressure_value)


def calculate_support_queue_exposure(state: GameState) -> SupportQueueExposure:
    """Return queue-exposure signals for higher-touch accounts and pressured lanes."""

    active_accounts = [
        account
        for account in state.customer_accounts
        if account.status is not CustomerAccountStatus.CHURNED
    ]
    severe_accounts = [
        account
        for account in active_accounts
        if _is_severe_queue_account(
            account,
            queue_age_threshold=BALANCE.support_program_queue_age_threshold,
            sla_target=state.support_program.sla_target,
        )
    ]
    premium_queue_exposure_value = quantize_money(
        sum(
            (
                account.contract_value
                for account in severe_accounts
                if account.support_tier in {SupportTier.PRIORITY, SupportTier.WHITE_GLOVE}
            ),
            Decimal("0.00"),
        )
    )
    enterprise_queue_exposure_value = quantize_money(
        sum(
            (
                account.contract_value
                for account in severe_accounts
                if account.segment.value == "enterprise"
            ),
            Decimal("0.00"),
        )
    )
    renewal_queue_exposure_value = quantize_money(
        sum(
            (
                account.contract_value
                for account in severe_accounts
                if _is_renewal_pressure_account(account)
            ),
            Decimal("0.00"),
        )
    )
    white_glove_queue_risk_accounts = sum(
        1 for account in severe_accounts if account.support_tier is SupportTier.WHITE_GLOVE
    )
    premium_queue_risk_accounts = sum(
        1
        for account in severe_accounts
        if account.support_tier in {SupportTier.PRIORITY, SupportTier.WHITE_GLOVE}
    )
    enterprise_queue_risk_accounts = sum(
        1 for account in severe_accounts if account.segment.value == "enterprise"
    )
    renewal_queue_risk_accounts = sum(
        1 for account in severe_accounts if _is_renewal_pressure_account(account)
    )
    lane_snapshots = calculate_support_lane_snapshots(state)
    lane_overflow_pressure = sum(snapshot.overflow for snapshot in lane_snapshots.values())
    hotspot_lane = max(
        lane_snapshots.values(),
        key=lambda snapshot: (snapshot.overflow, snapshot.pressure, snapshot.account_count),
    ).lane
    hotspot_lane_overflow = lane_snapshots[hotspot_lane].overflow
    hotspot_lane_account_count = lane_snapshots[hotspot_lane].account_count
    focus_alignment_gap = 0
    if state.support_program.lane_focus is not hotspot_lane and hotspot_lane_overflow > 0:
        focus_alignment_gap = clamp_int(hotspot_lane_overflow + max(0, hotspot_lane_account_count))
    lane_saturation_index = clamp_int(
        lane_overflow_pressure
        + state.support_program.escalation_queue
        + (state.support_program.backlog_queue // BALANCE.support_program_focus_mismatch_divisor)
        + (state.support_program.queue_age_pressure // BALANCE.support_program_queue_age_threshold)
    )
    return SupportQueueExposure(
        premium_queue_exposure_value=premium_queue_exposure_value,
        enterprise_queue_exposure_value=enterprise_queue_exposure_value,
        renewal_queue_exposure_value=renewal_queue_exposure_value,
        premium_queue_risk_accounts=premium_queue_risk_accounts,
        enterprise_queue_risk_accounts=enterprise_queue_risk_accounts,
        renewal_queue_risk_accounts=renewal_queue_risk_accounts,
        white_glove_queue_risk_accounts=white_glove_queue_risk_accounts,
        severe_queue_accounts=len(severe_accounts),
        lane_saturation_index=lane_saturation_index,
        hotspot_lane=hotspot_lane,
        hotspot_lane_overflow=hotspot_lane_overflow,
        hotspot_lane_account_count=hotspot_lane_account_count,
        focus_alignment_gap=focus_alignment_gap,
    )


def calculate_support_lane_staffing_plan(state: GameState) -> dict[SupportLaneFocus, int]:
    """Distribute available staffing intent across support lanes."""

    active_accounts = [
        account
        for account in state.customer_accounts
        if account.status is not CustomerAccountStatus.CHURNED
    ]
    weights = {
        SupportLaneFocus.ONBOARDING: 1,
        SupportLaneFocus.ENTERPRISE: 1,
        SupportLaneFocus.BILLING: 1,
    }
    for account in active_accounts:
        lane = classify_account_support_lane(account)
        if lane is SupportLaneFocus.BALANCED:
            continue
        weights[lane] += 2
        if account.support_tier is SupportTier.PRIORITY:
            weights[lane] += 1
        elif account.support_tier is SupportTier.WHITE_GLOVE:
            weights[lane] += 2
        if lane is SupportLaneFocus.BILLING and (
            account.failed_payment_risk > 0 or account.dunning_steps > 0
        ):
            weights[lane] += 1
    if state.support_program.lane_focus is not SupportLaneFocus.BALANCED:
        weights[state.support_program.lane_focus] += 2

    planning_units = max(
        1,
        state.support_program.staffing_level
        + max(1, state.functional_budget.customer_success_share // 20),
    )
    weight_total = sum(weights.values())
    remaining_units = planning_units
    allocations: dict[SupportLaneFocus, int] = {}
    ordered_lanes = sorted(weights, key=lambda lane: weights[lane], reverse=True)
    for index, lane in enumerate(ordered_lanes):
        if index == len(ordered_lanes) - 1:
            lane_units = remaining_units
        else:
            lane_units = int((planning_units * weights[lane]) / max(1, weight_total))
            if weights[lane] > 1:
                lane_units = max(1, lane_units)
            lane_units = min(remaining_units, lane_units)
        remaining_units = max(0, remaining_units - lane_units)
        allocations[lane] = lane_units
    return allocations


def calculate_support_program_relief(
    support_program: SupportProgram,
    *,
    customer_success_bonus: int = 0,
) -> tuple[int, int]:
    """Return ticket and SLA relief created by support tooling."""

    ticket_relief = (
        (support_program.knowledge_base_level // BALANCE.support_program_knowledge_base_divisor)
        + (support_program.automation_level // BALANCE.support_program_automation_divisor)
        + (customer_success_bonus * BALANCE.support_program_customer_success_capacity_bonus)
    )
    sla_relief = max(0, (ticket_relief // 2) + (support_program.automation_level // 20))
    return ticket_relief, sla_relief


def apply_end_of_turn_support_program(
    state: GameState,
    *,
    customer_success_bonus: int = 0,
) -> SupportProgramSummary:
    """Update shared backlog and support tooling outcomes after customer drift resolves."""

    active_accounts = [
        account
        for account in state.customer_accounts
        if account.status is not CustomerAccountStatus.CHURNED
    ]
    queue_age_pressure = 0
    for account in active_accounts:
        if account.open_tickets > 0 or account.sla_breach_risk > 0:
            account.ticket_queue_age += 1
            if (
                account.segment.value == "enterprise"
                or account.support_tier is SupportTier.WHITE_GLOVE
            ):
                account.ticket_queue_age += 1
        else:
            account.ticket_queue_age = max(0, account.ticket_queue_age - 1)
        queue_age_pressure += max(0, account.ticket_queue_age - 1)
    total_open_tickets = sum(account.open_tickets for account in active_accounts)
    onboarding_ticket_pressure = sum(
        account.open_tickets
        + max(
            0,
            (
                BALANCE.support_program_onboarding_health_pressure_threshold
                - account.onboarding_health
            ),
        )
        // 10
        for account in active_accounts
        if account.segment.value != "enterprise"
    )
    enterprise_ticket_pressure = sum(
        account.open_tickets
        + BALANCE.support_tier_capacity_cost[account.support_tier.value]
        + (1 if account.segment.value == "enterprise" else 0)
        for account in active_accounts
        if account.segment.value == "enterprise" or account.support_tier is SupportTier.WHITE_GLOVE
    )
    billing_ticket_pressure = sum(
        (account.invoice_risk // BALANCE.support_program_billing_pressure_invoice_divisor)
        + (
            account.failed_payment_risk
            // BALANCE.support_program_billing_pressure_failed_payment_divisor
        )
        + (account.dunning_steps * BALANCE.support_program_billing_pressure_dunning_weight)
        + (account.open_tickets // 2)
        for account in active_accounts
        if (
            account.invoice_risk > 0 or account.failed_payment_risk > 0 or account.dunning_steps > 0
        )
    )
    dominant_lane = _get_dominant_pressure_lane(
        onboarding_ticket_pressure=onboarding_ticket_pressure,
        enterprise_ticket_pressure=enterprise_ticket_pressure,
        billing_ticket_pressure=billing_ticket_pressure,
    )
    weighted_ticket_pressure = total_open_tickets + sum(
        max(0, BALANCE.support_program_segment_ticket_weight[account.segment.value] - 1)
        for account in active_accounts
        if account.open_tickets > 0
    )
    weighted_ticket_pressure += queue_age_pressure
    weighted_ticket_pressure += sum(
        BALANCE.support_tier_capacity_cost[account.support_tier.value]
        for account in active_accounts
    )
    focus_mismatch_penalty = _calculate_focus_mismatch_penalty(
        state.support_program.lane_focus,
        onboarding_ticket_pressure=onboarding_ticket_pressure,
        enterprise_ticket_pressure=enterprise_ticket_pressure,
        billing_ticket_pressure=billing_ticket_pressure,
    )
    weighted_ticket_pressure += focus_mismatch_penalty
    sla_breaches = sum(
        1
        for account in active_accounts
        if account.sla_breach_risk >= state.support_program.sla_target
    )
    ticket_relief, _ = calculate_support_program_relief(
        state.support_program,
        customer_success_bonus=customer_success_bonus,
    )
    deflection_score = clamp_int(
        ticket_relief
        + state.support_program.knowledge_base_level // 2
        + state.support_program.automation_level // 2
        + _calculate_support_focus_bonus(active_accounts, state.support_program.lane_focus)
    )
    effective_capacity = (
        BALANCE.support_program_base_capacity
        + ticket_relief
        + calculate_support_staff_capacity(state)
    )
    lane_snapshots = calculate_support_lane_snapshots(
        state,
        customer_success_bonus=customer_success_bonus,
        total_capacity=effective_capacity,
    )
    lane_overflow_pressure = sum(snapshot.overflow for snapshot in lane_snapshots.values())
    incoming_ticket_pressure = weighted_ticket_pressure + state.support_program.backlog_queue
    incoming_ticket_pressure += (
        lane_overflow_pressure // BALANCE.support_program_lane_overflow_divisor
    )
    resolved_tickets = min(incoming_ticket_pressure, effective_capacity)
    deflected_tickets = min(total_open_tickets, ticket_relief + resolved_tickets)
    queue_increase = max(0, incoming_ticket_pressure - resolved_tickets)
    queue_relief = (
        state.support_program.automation_level // BALANCE.support_program_queue_relief_divisor
    )
    state.support_program.backlog_queue = max(
        0,
        queue_increase - queue_relief,
    )
    severe_accounts = count_escalating_accounts(active_accounts)
    account_queue_risk_score = clamp_int(
        sum(
            _calculate_account_support_severity(account)
            for account in active_accounts
            if (
                account.open_tickets > 0
                or account.sla_breach_risk > 0
                or account.escalation_count > 0
            )
        )
        // BALANCE.support_program_account_queue_risk_divisor
    )
    enterprise_pressure = sum(
        1 for account in active_accounts if account.segment.value == "enterprise"
    )
    staffing_gap = max(
        0,
        severe_accounts + enterprise_pressure - max(1, effective_capacity // 3),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        + severe_accounts
        + staffing_gap
        - (resolved_tickets // BALANCE.support_program_escalation_queue_divisor),
    )
    state.support_program.resolved_last_turn = resolved_tickets
    state.support_program.deflection_score = deflection_score
    state.support_program.sla_breaches_last_turn = sla_breaches
    state.support_program.queue_age_pressure = queue_age_pressure
    state.support_program.onboarding_ticket_pressure = onboarding_ticket_pressure
    state.support_program.enterprise_ticket_pressure = enterprise_ticket_pressure
    state.support_program.billing_ticket_pressure = billing_ticket_pressure
    base_service_cost = quantize_money(
        (Decimal(total_open_tickets) * BALANCE.support_program_service_cost_per_ticket)
        + (
            Decimal(state.support_program.escalation_queue)
            * BALANCE.support_program_service_cost_per_escalation
        )
        + (
            Decimal(state.support_program.staffing_level)
            * BALANCE.support_program_service_cost_per_staffing_level
        )
        + (Decimal(queue_age_pressure) * BALANCE.support_program_service_cost_per_queue_age)
        + (Decimal(focus_mismatch_penalty) * BALANCE.support_program_service_cost_per_queue_age)
        + (Decimal(lane_overflow_pressure) * BALANCE.support_program_service_cost_per_lane_overflow)
        + (
            Decimal(
                sum(
                    1 for account in active_accounts if account.support_tier is SupportTier.PRIORITY
                )
            )
            * BALANCE.support_program_service_cost_per_priority_account
        )
        + (
            Decimal(
                sum(
                    1
                    for account in active_accounts
                    if account.support_tier is SupportTier.WHITE_GLOVE
                )
            )
            * BALANCE.support_program_service_cost_per_white_glove_account
        )
    )

    reputation_delta = 0
    morale_penalty = 0
    if (
        state.support_program.backlog_queue >= BALANCE.support_program_backlog_reputation_threshold
        or state.support_program.escalation_queue
        >= BALANCE.support_program_triage_escalation_relief * 2
    ):
        reputation_delta = -BALANCE.support_program_backlog_reputation_loss
    if lane_overflow_pressure >= BALANCE.support_program_lane_overflow_reputation_threshold:
        reputation_delta -= BALANCE.support_program_lane_overflow_reputation_loss
    if staffing_gap >= BALANCE.support_program_staffing_gap_reputation_threshold:
        reputation_delta -= 1
    if queue_age_pressure >= BALANCE.support_program_queue_age_threshold:
        for account in active_accounts:
            if account.ticket_queue_age >= BALANCE.support_program_queue_age_threshold:
                account.satisfaction = clamp_int(
                    account.satisfaction - BALANCE.support_program_queue_age_satisfaction_loss
                )
                account.churn_risk = clamp_int(
                    account.churn_risk + BALANCE.support_program_queue_age_churn_gain
                )
                account.renewal_health = clamp_int(
                    account.renewal_health - BALANCE.support_program_queue_age_renewal_health_loss
                )
                account.expansion_potential = clamp_int(
                    account.expansion_potential - BALANCE.support_program_queue_age_expansion_loss
                )
                if account.support_tier is SupportTier.PRIORITY:
                    account.churn_risk = clamp_int(
                        account.churn_risk + BALANCE.support_program_priority_queue_age_churn_gain
                    )
                    account.renewal_health = clamp_int(
                        account.renewal_health
                        - BALANCE.support_program_priority_queue_age_renewal_health_loss
                    )
                elif account.support_tier is SupportTier.WHITE_GLOVE:
                    account.churn_risk = clamp_int(
                        account.churn_risk
                        + BALANCE.support_program_white_glove_queue_age_churn_gain
                    )
                    account.renewal_health = clamp_int(
                        account.renewal_health
                        - BALANCE.support_program_white_glove_queue_age_renewal_health_loss
                    )
    for account in active_accounts:
        stressed_account = (
            account.ticket_queue_age >= BALANCE.support_program_queue_age_threshold
            or account.open_tickets >= BALANCE.support_program_escalation_ticket_threshold
            or account.sla_breach_risk >= state.support_program.sla_target
        )
        if (
            stressed_account
            and lane_overflow_pressure > 0
            and classify_account_support_lane(account) is dominant_lane
        ):
            account.renewal_health = clamp_int(account.renewal_health - 1)
            account.expansion_potential = clamp_int(account.expansion_potential - 1)
    revenue_at_risk_accounts, renewal_pressure_accounts = calculate_support_account_risk_counts(
        state
    )
    revenue_at_risk_value, renewal_pressure_value = calculate_support_account_risk_values(state)
    enterprise_revenue_at_risk_value = quantize_money(
        sum(
            (
                account.contract_value
                for account in active_accounts
                if account.segment.value == "enterprise"
                and _is_revenue_at_risk_account(
                    account,
                    sla_target=state.support_program.sla_target,
                )
            ),
            Decimal("0.00"),
        )
    )
    premium_revenue_at_risk_value = quantize_money(
        sum(
            (
                account.contract_value
                for account in active_accounts
                if account.support_tier in {SupportTier.PRIORITY, SupportTier.WHITE_GLOVE}
                and _is_revenue_at_risk_account(
                    account,
                    sla_target=state.support_program.sla_target,
                )
            ),
            Decimal("0.00"),
        )
    )
    white_glove_revenue_at_risk_value = quantize_money(
        sum(
            (
                account.contract_value
                for account in active_accounts
                if account.support_tier is SupportTier.WHITE_GLOVE
                and _is_revenue_at_risk_account(
                    account,
                    sla_target=state.support_program.sla_target,
                )
            ),
            Decimal("0.00"),
        )
    )
    priority_breach_accounts = sum(
        1
        for account in active_accounts
        if account.support_tier is SupportTier.PRIORITY
        and account.sla_breach_risk >= state.support_program.sla_target
    )
    white_glove_breach_accounts = sum(
        1
        for account in active_accounts
        if account.support_tier is SupportTier.WHITE_GLOVE
        and account.sla_breach_risk >= state.support_program.sla_target
    )
    recovery_ready_accounts = 0
    service_tier_pressure = 0
    commercial_breach_pressure = (
        priority_breach_accounts * BALANCE.support_program_priority_breach_pressure_gain
        + white_glove_breach_accounts * BALANCE.support_program_white_glove_breach_pressure_gain
    )
    if priority_breach_accounts > 0 or white_glove_breach_accounts > 0:
        for account in active_accounts:
            if account.sla_breach_risk < state.support_program.sla_target:
                continue
            if account.support_tier is SupportTier.PRIORITY:
                account.satisfaction = clamp_int(
                    account.satisfaction - BALANCE.support_program_priority_breach_satisfaction_loss
                )
                if _is_severe_queue_account(
                    account,
                    queue_age_threshold=BALANCE.support_program_queue_age_threshold,
                    sla_target=state.support_program.sla_target,
                ):
                    account.churn_risk = clamp_int(
                        account.churn_risk
                        + BALANCE.support_program_priority_severe_queue_churn_gain
                    )
                    account.renewal_health = clamp_int(
                        account.renewal_health
                        - BALANCE.support_program_priority_severe_queue_renewal_loss
                    )
            elif account.support_tier is SupportTier.WHITE_GLOVE:
                account.satisfaction = clamp_int(
                    account.satisfaction
                    - BALANCE.support_program_white_glove_breach_satisfaction_loss
                )
                account.renewal_health = clamp_int(account.renewal_health - 1)
                account.expansion_potential = clamp_int(account.expansion_potential - 1)
                if _is_severe_queue_account(
                    account,
                    queue_age_threshold=BALANCE.support_program_queue_age_threshold,
                    sla_target=state.support_program.sla_target,
                ):
                    account.churn_risk = clamp_int(
                        account.churn_risk
                        + BALANCE.support_program_white_glove_severe_queue_churn_gain
                    )
                    account.renewal_health = clamp_int(
                        account.renewal_health
                        - BALANCE.support_program_white_glove_severe_queue_renewal_loss
                    )
                    account.expansion_potential = clamp_int(
                        account.expansion_potential
                        - BALANCE.support_program_white_glove_severe_queue_expansion_loss
                    )
    support_recovery_window = (
        focus_mismatch_penalty == 0
        and lane_overflow_pressure == 0
        and state.support_program.backlog_queue
        <= BALANCE.support_program_recovery_backlog_threshold
    )
    if support_recovery_window:
        for account in active_accounts:
            if not _is_support_recovery_ready_account(
                account,
                sla_target=state.support_program.sla_target,
            ):
                continue
            recovery_ready_accounts += 1
            account.satisfaction = clamp_int(
                account.satisfaction + BALANCE.support_program_recovery_satisfaction_gain
            )
            account.renewal_health = clamp_int(
                account.renewal_health + BALANCE.support_program_recovery_renewal_health_gain
            )
            account.churn_risk = clamp_int(
                account.churn_risk - BALANCE.support_program_recovery_churn_relief
            )
            account.ticket_queue_age = max(0, account.ticket_queue_age - 1)
            if account.support_tier in {SupportTier.PRIORITY, SupportTier.WHITE_GLOVE}:
                account.expansion_potential = clamp_int(
                    account.expansion_potential + BALANCE.support_program_recovery_expansion_gain
                )
    else:
        recovery_ready_accounts = sum(
            1
            for account in active_accounts
            if _is_support_recovery_ready_account(
                account,
                sla_target=state.support_program.sla_target,
            )
        )
    queue_exposure = calculate_support_queue_exposure(state)
    service_tier_pressure = (
        priority_breach_accounts
        + (white_glove_breach_accounts * 2)
        + queue_exposure.severe_queue_accounts
    )
    revenue_at_risk_accounts, renewal_pressure_accounts = calculate_support_account_risk_counts(
        state
    )
    revenue_at_risk_value, renewal_pressure_value = calculate_support_account_risk_values(state)
    high_value_risk_accounts = sum(
        1
        for account in active_accounts
        if account.contract_value >= BALANCE.support_program_high_value_contract_threshold
        and _is_revenue_at_risk_account(
            account,
            sla_target=state.support_program.sla_target,
        )
    )
    sla_credit_cost = quantize_money(
        (
            Decimal(priority_breach_accounts)
            * BALANCE.support_program_service_cost_per_priority_sla_credit
        )
        + (
            Decimal(white_glove_breach_accounts)
            * BALANCE.support_program_service_cost_per_white_glove_sla_credit
        )
        + (
            Decimal(account_queue_risk_score)
            * BALANCE.support_program_service_cost_per_queue_risk_point
        )
    )
    service_cost = quantize_money(base_service_cost + sla_credit_cost)
    state.support_program.service_cost_last_turn = service_cost
    if white_glove_breach_accounts > 0:
        reputation_delta -= BALANCE.support_program_white_glove_breach_reputation_loss
    if (
        state.support_program.backlog_queue
        >= BALANCE.support_program_backlog_morale_penalty_threshold
    ):
        morale_penalty = BALANCE.support_program_backlog_morale_penalty
    if staffing_gap > 0:
        morale_penalty += BALANCE.support_program_staffing_gap_morale_penalty
    if focus_mismatch_penalty > 0:
        state.support_program.backlog_queue += focus_mismatch_penalty
        state.support_program.escalation_queue += max(0, focus_mismatch_penalty - 1)

    if not active_accounts:
        summary = "Support tooling is idle."
    elif (
        queue_exposure.enterprise_queue_exposure_value
        >= BALANCE.support_program_high_value_contract_threshold
    ):
        summary = (
            "Enterprise queue exposure is now large enough to threaten renewals and board trust, "
            f"with {queue_exposure.enterprise_queue_risk_accounts} critical account(s) "
            "concentrated "
            f"in {queue_exposure.hotspot_lane.value} support."
        )
    elif (
        queue_exposure.lane_saturation_index
        >= BALANCE.support_program_backlog_reputation_threshold // 2
    ):
        summary = (
            "Support lanes are saturated enough that backlog relief now matters more than new "
            "load, "
            f"especially in {queue_exposure.hotspot_lane.value} support."
        )
    elif state.support_program.backlog_queue == 0:
        summary = "Support tooling is keeping ticket flow under control."
    elif focus_mismatch_penalty > 0:
        summary = (
            "Support lanes are mismatched with demand and "
            f"{dominant_lane.value} pressure is waiting too long."
        )
    elif dominant_lane is SupportLaneFocus.BILLING:
        summary = "Support is stable, but billing queues are now the main post-sale pressure."
    elif recovery_ready_accounts > 0 and support_recovery_window:
        summary = (
            f"Support recovery is rebuilding trust across {recovery_ready_accounts} account(s)."
        )
    elif queue_exposure.severe_queue_accounts > 0:
        summary = (
            "High-touch accounts are waiting too long. Support promises are now "
            "creating visible commercial risk."
        )
    elif lane_overflow_pressure > 0:
        summary = (
            f"{dominant_lane.value} support demand is outrunning lane capacity and queues "
            "are compounding."
        )
    elif staffing_gap > 0:
        summary = "Support demand is outrunning staffed capacity and enterprise pressure is rising."
    else:
        summary = "Support backlog is creating visible delivery and customer pressure."

    return SupportProgramSummary(
        total_open_tickets=total_open_tickets,
        effective_capacity=effective_capacity,
        deflected_tickets=deflected_tickets,
        backlog_queue=state.support_program.backlog_queue,
        escalation_queue=state.support_program.escalation_queue,
        sla_breaches=sla_breaches,
        resolved_tickets=resolved_tickets,
        deflection_score=deflection_score,
        weighted_ticket_pressure=weighted_ticket_pressure,
        staffing_gap=staffing_gap,
        queue_age_pressure=queue_age_pressure,
        onboarding_ticket_pressure=onboarding_ticket_pressure,
        enterprise_ticket_pressure=enterprise_ticket_pressure,
        billing_ticket_pressure=billing_ticket_pressure,
        revenue_at_risk_accounts=revenue_at_risk_accounts,
        revenue_at_risk_value=revenue_at_risk_value,
        enterprise_revenue_at_risk_value=enterprise_revenue_at_risk_value,
        premium_revenue_at_risk_value=premium_revenue_at_risk_value,
        white_glove_revenue_at_risk_value=white_glove_revenue_at_risk_value,
        premium_queue_exposure_value=queue_exposure.premium_queue_exposure_value,
        enterprise_queue_exposure_value=queue_exposure.enterprise_queue_exposure_value,
        renewal_queue_exposure_value=queue_exposure.renewal_queue_exposure_value,
        premium_queue_risk_accounts=queue_exposure.premium_queue_risk_accounts,
        enterprise_queue_risk_accounts=queue_exposure.enterprise_queue_risk_accounts,
        renewal_queue_risk_accounts=queue_exposure.renewal_queue_risk_accounts,
        high_value_risk_accounts=high_value_risk_accounts,
        renewal_pressure_accounts=renewal_pressure_accounts,
        renewal_pressure_value=renewal_pressure_value,
        priority_breach_accounts=priority_breach_accounts,
        white_glove_breach_accounts=white_glove_breach_accounts,
        white_glove_queue_risk_accounts=queue_exposure.white_glove_queue_risk_accounts,
        severe_queue_accounts=queue_exposure.severe_queue_accounts,
        account_queue_risk_score=account_queue_risk_score,
        lane_saturation_index=queue_exposure.lane_saturation_index,
        hotspot_lane=queue_exposure.hotspot_lane,
        hotspot_lane_overflow=queue_exposure.hotspot_lane_overflow,
        hotspot_lane_account_count=queue_exposure.hotspot_lane_account_count,
        focus_alignment_gap=queue_exposure.focus_alignment_gap,
        recovery_ready_accounts=recovery_ready_accounts,
        sla_credit_cost=sla_credit_cost,
        service_tier_pressure=service_tier_pressure,
        commercial_breach_pressure=commercial_breach_pressure,
        dominant_lane=dominant_lane,
        focus_mismatch_penalty=focus_mismatch_penalty,
        lane_overflow_pressure=lane_overflow_pressure,
        service_cost=service_cost,
        reputation_delta=reputation_delta,
        morale_penalty=morale_penalty,
        summary=summary,
    )


def improve_support_program(
    support_program: SupportProgram,
    *,
    knowledge_base_gain: int,
    automation_gain: int,
) -> None:
    """Improve reusable support tooling through explicit investment."""

    support_program.knowledge_base_level = clamp_int(
        support_program.knowledge_base_level + knowledge_base_gain
    )
    support_program.automation_level = clamp_int(support_program.automation_level + automation_gain)


def triage_support_backlog(state: GameState) -> SupportOpsActionSummary:
    """Spend cash and attention to manually reduce support pressure."""

    if (
        state.support_program.backlog_queue <= 0
        and state.support_program.escalation_queue <= 0
        and not any(account.open_tickets > 0 for account in state.customer_accounts)
    ):
        raise ValueError("Support pressure is already under control.")
    if state.company.cash_on_hand < BALANCE.support_program_triage_cost:
        raise ValueError("Not enough cash to run a support triage sprint this turn.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_triage_cost
    )
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue - BALANCE.support_program_triage_backlog_relief,
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue - BALANCE.support_program_triage_escalation_relief,
    )
    accounts = [
        account
        for account in sorted(
            state.customer_accounts,
            key=lambda account: (
                _calculate_account_support_severity(account),
                account.ticket_queue_age,
                account.churn_risk,
            ),
            reverse=True,
        )
        if account.status is not CustomerAccountStatus.CHURNED
    ]
    improved_accounts = 0
    lane_relief = {
        SupportLaneFocus.ONBOARDING: 0,
        SupportLaneFocus.ENTERPRISE: 0,
        SupportLaneFocus.BILLING: 0,
    }
    for account in accounts[:3]:
        if account.open_tickets <= 0 and account.sla_breach_risk <= 0:
            continue
        lane = classify_account_support_lane(account)
        account.open_tickets = max(
            0,
            account.open_tickets - BALANCE.support_program_triage_ticket_relief,
        )
        account.sla_breach_risk = clamp_int(
            account.sla_breach_risk - BALANCE.support_program_triage_sla_relief
        )
        account.failed_payment_risk = clamp_int(
            account.failed_payment_risk - (BALANCE.support_program_triage_sla_relief // 2)
        )
        account.renewal_health = clamp_int(
            account.renewal_health + BALANCE.support_program_triage_renewal_health_gain
        )
        account.satisfaction = clamp_int(
            account.satisfaction + BALANCE.support_program_triage_satisfaction_gain
        )
        account.ticket_queue_age = max(
            0,
            account.ticket_queue_age - BALANCE.support_program_triage_queue_age_relief,
        )
        account.churn_risk = clamp_int(
            account.churn_risk - BALANCE.support_program_triage_satisfaction_gain
        )
        account.escalation_count = max(0, account.escalation_count - 1)
        if lane is not SupportLaneFocus.BALANCED:
            lane_relief[lane] += 1
        improved_accounts += 1

    for lane, relieved_accounts in lane_relief.items():
        if relieved_accounts <= 0:
            continue
        _apply_lane_program_relief(
            state.support_program,
            lane,
            relieved_accounts * 2,
        )

    return SupportOpsActionSummary(
        message=(
            f"Ran a support triage sprint for {improved_accounts} account(s). "
            f"Cash -{BALANCE.support_program_triage_cost}, "
            f"backlog {state.support_program.backlog_queue}, "
            f"escalations {state.support_program.escalation_queue}."
        )
    )


def upgrade_support_program(
    state: GameState,
    focus: SupportInvestmentFocus,
) -> SupportOpsActionSummary:
    """Spend cash on reusable support leverage instead of one-off triage."""

    if state.company.cash_on_hand < BALANCE.support_program_upgrade_cost:
        raise ValueError("Not enough cash to upgrade the support program this turn.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_upgrade_cost
    )
    if focus is SupportInvestmentFocus.KNOWLEDGE_BASE:
        improve_support_program(
            state.support_program,
            knowledge_base_gain=BALANCE.support_program_upgrade_knowledge_gain,
            automation_gain=0,
        )
    elif focus is SupportInvestmentFocus.AUTOMATION:
        improve_support_program(
            state.support_program,
            knowledge_base_gain=0,
            automation_gain=BALANCE.support_program_upgrade_automation_gain,
        )
    else:
        state.support_program.sla_target = clamp_int(
            state.support_program.sla_target + BALANCE.support_program_upgrade_sla_gain
        )

    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue - BALANCE.support_program_upgrade_backlog_relief,
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue - BALANCE.support_program_upgrade_escalation_relief,
    )
    return SupportOpsActionSummary(
        message=(
            f"Upgraded support via {focus.value}. "
            f"Cash -{BALANCE.support_program_upgrade_cost}, "
            f"KB {state.support_program.knowledge_base_level}, "
            f"automation {state.support_program.automation_level}, "
            f"SLA target {state.support_program.sla_target}."
        )
    )


def invest_in_support_staffing(state: GameState) -> SupportOpsActionSummary:
    """Spend cash on more durable support staffing capacity."""

    if state.company.cash_on_hand < BALANCE.support_program_staffing_investment_cost:
        raise ValueError("Not enough cash to expand support staffing this turn.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_staffing_investment_cost
    )
    state.support_program.staffing_level = clamp_int(
        state.support_program.staffing_level + BALANCE.support_program_staffing_level_gain,
        0,
        20,
    )
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue - BALANCE.support_program_upgrade_backlog_relief,
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue - BALANCE.support_program_upgrade_escalation_relief,
    )
    return SupportOpsActionSummary(
        message=(
            "Expanded support staffing. "
            f"Cash -{BALANCE.support_program_staffing_investment_cost}, "
            f"staffing level {state.support_program.staffing_level}."
        )
    )


def set_support_lane_focus(
    state: GameState,
    focus: SupportLaneFocus,
) -> SupportOpsActionSummary:
    """Change the company-wide support lane emphasis."""

    if state.support_program.lane_focus is focus:
        raise ValueError(f"Support is already focused on {focus.value}.")
    queue_exposure = calculate_support_queue_exposure(state)
    state.support_program.lane_focus = focus
    backlog_relief = 1
    escalation_relief = 0
    improved_accounts = 0
    if queue_exposure.hotspot_lane is focus and queue_exposure.hotspot_lane_overflow > 0:
        backlog_relief += min(2, queue_exposure.hotspot_lane_overflow)
        escalation_relief = min(
            2,
            max(1, queue_exposure.hotspot_lane_overflow // 2),
        )
        target_accounts = [
            account
            for account in sorted(
                state.customer_accounts,
                key=lambda account: (
                    classify_account_support_lane(account) is focus,
                    _calculate_account_support_severity(account),
                    account.ticket_queue_age,
                    account.open_tickets,
                ),
                reverse=True,
            )
            if account.status is not CustomerAccountStatus.CHURNED
            and classify_account_support_lane(account) is focus
        ]
        for account in target_accounts[:2]:
            account.open_tickets = max(
                0,
                account.open_tickets - max(1, BALANCE.support_program_triage_ticket_relief // 2),
            )
            account.sla_breach_risk = clamp_int(
                account.sla_breach_risk - max(2, BALANCE.support_program_triage_sla_relief // 2)
            )
            account.ticket_queue_age = max(
                0,
                account.ticket_queue_age - max(1, BALANCE.support_program_triage_queue_age_relief),
            )
            account.churn_risk = clamp_int(account.churn_risk - 1)
            if focus is SupportLaneFocus.ENTERPRISE:
                account.satisfaction = clamp_int(
                    account.satisfaction
                    + BALANCE.support_program_route_onboarding_satisfaction_gain
                )
                account.renewal_health = clamp_int(
                    account.renewal_health + BALANCE.support_program_triage_renewal_health_gain
                )
            elif focus is SupportLaneFocus.BILLING:
                account.invoice_risk = clamp_int(
                    account.invoice_risk
                    - max(4, BALANCE.support_program_route_billing_invoice_relief // 2)
                )
                account.failed_payment_risk = clamp_int(
                    account.failed_payment_risk
                    - max(4, BALANCE.support_program_route_billing_payment_relief // 2)
                )
                account.renewal_health = clamp_int(
                    account.renewal_health
                    + BALANCE.support_program_route_billing_renewal_health_gain
                )
            elif focus is SupportLaneFocus.ONBOARDING:
                account.onboarding_health = clamp_int(
                    account.onboarding_health + BALANCE.support_program_route_onboarding_health_gain
                )
                account.satisfaction = clamp_int(
                    account.satisfaction
                    + BALANCE.support_program_route_onboarding_satisfaction_gain
                )
            improved_accounts += 1
        _apply_lane_program_relief(
            state.support_program,
            focus,
            max(2, queue_exposure.hotspot_lane_overflow + improved_accounts),
        )
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue - backlog_relief,
    )
    if escalation_relief > 0:
        state.support_program.escalation_queue = max(
            0,
            state.support_program.escalation_queue - escalation_relief,
        )
    return SupportOpsActionSummary(
        message=(
            f"Support lane focus shifted to {focus.value}. "
            f"Backlog now {state.support_program.backlog_queue}, "
            f"escalations {state.support_program.escalation_queue}, "
            f"accounts stabilized {improved_accounts}."
        )
    )


def route_support_escalation(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Route one account into a higher-touch support response."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if account.open_tickets <= 0 and account.sla_breach_risk <= 0 and account.escalation_count <= 0:
        raise ValueError("That account does not need escalation routing right now.")
    if state.company.cash_on_hand < BALANCE.support_program_route_escalation_cost:
        raise ValueError("Not enough cash to route this escalation.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_route_escalation_cost
    )
    lane = classify_account_support_lane(account)
    lane_label = lane.value
    if lane is SupportLaneFocus.BILLING:
        account.invoice_risk = clamp_int(
            account.invoice_risk - BALANCE.support_program_route_billing_invoice_relief
        )
        account.failed_payment_risk = clamp_int(
            account.failed_payment_risk - BALANCE.support_program_route_billing_payment_relief
        )
        account.dunning_steps = max(
            0,
            account.dunning_steps - BALANCE.support_program_route_billing_dunning_relief,
        )
        account.open_tickets = max(
            0,
            account.open_tickets - max(1, BALANCE.support_program_route_ticket_relief // 2),
        )
        account.sla_breach_risk = clamp_int(
            account.sla_breach_risk - max(2, BALANCE.support_program_route_sla_relief // 2)
        )
        account.renewal_health = clamp_int(
            account.renewal_health + BALANCE.support_program_route_billing_renewal_health_gain
        )
        if account.support_tier is SupportTier.STANDARD and account.open_tickets > 6:
            account.support_tier = SupportTier.PRIORITY
        _apply_lane_program_relief(state.support_program, SupportLaneFocus.BILLING, 4)
    elif lane is SupportLaneFocus.ENTERPRISE:
        if account.support_tier is SupportTier.STANDARD:
            account.support_tier = SupportTier.PRIORITY
        elif account.support_tier is SupportTier.PRIORITY:
            account.support_tier = SupportTier.WHITE_GLOVE
        account.open_tickets = max(
            0,
            account.open_tickets
            - (
                BALANCE.support_program_route_ticket_relief
                + BALANCE.support_program_route_enterprise_ticket_relief_bonus
            ),
        )
        account.sla_breach_risk = clamp_int(
            account.sla_breach_risk
            - (
                BALANCE.support_program_route_sla_relief
                + BALANCE.support_program_route_enterprise_sla_relief_bonus
            )
        )
        account.failed_payment_risk = clamp_int(
            account.failed_payment_risk - (BALANCE.support_program_route_sla_relief // 2)
        )
        account.renewal_health = clamp_int(account.renewal_health + 4)
        _apply_lane_program_relief(state.support_program, SupportLaneFocus.ENTERPRISE, 4)
    else:
        account.open_tickets = max(
            0,
            account.open_tickets - BALANCE.support_program_route_ticket_relief,
        )
        account.sla_breach_risk = clamp_int(
            account.sla_breach_risk - BALANCE.support_program_route_sla_relief
        )
        account.support_load = clamp_int(
            account.support_load - BALANCE.support_program_route_onboarding_support_load_relief
        )
        account.onboarding_health = clamp_int(
            account.onboarding_health + BALANCE.support_program_route_onboarding_health_gain
        )
        account.satisfaction = clamp_int(
            account.satisfaction + BALANCE.support_program_route_onboarding_satisfaction_gain
        )
        _apply_lane_program_relief(state.support_program, SupportLaneFocus.ONBOARDING, 4)
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk - (BALANCE.support_program_route_sla_relief // 2)
    )
    account.support_load = clamp_int(account.support_load - 2)
    account.churn_risk = clamp_int(account.churn_risk - BALANCE.support_program_route_churn_relief)
    account.renewal_health = clamp_int(
        account.renewal_health + (BALANCE.support_program_route_churn_relief // 2)
    )
    account.satisfaction = clamp_int(
        account.satisfaction + BALANCE.support_program_triage_satisfaction_gain
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    account.ticket_queue_age = max(0, account.ticket_queue_age - 2)
    state.support_program.escalation_queue = max(0, state.support_program.escalation_queue - 1)

    return SupportOpsActionSummary(
        message=(
            f"Routed {lane_label} escalation for {account.name}. "
            f"Tier {account.support_tier.value}, cash -"
            f"{BALANCE.support_program_route_escalation_cost}."
        )
    )


def run_account_rescue(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run a heavier one-account rescue for the most commercially exposed support issue."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if (
        account.open_tickets <= 0
        and account.sla_breach_risk <= 0
        and account.ticket_queue_age <= 0
        and account.failed_payment_risk <= 0
        and account.invoice_risk <= 0
        and account.churn_risk <= 4
        and account.renewal_health >= 76
    ):
        raise ValueError("That account does not need a rescue play right now.")
    if state.company.cash_on_hand < BALANCE.support_program_account_rescue_cost:
        raise ValueError("Not enough cash to run an account rescue this turn.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_account_rescue_cost
    )
    lane = classify_account_support_lane(account)
    lane_label = lane.value
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue - BALANCE.support_program_account_rescue_backlog_relief,
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - BALANCE.support_program_account_rescue_escalation_relief,
    )
    account.open_tickets = max(
        0,
        account.open_tickets - BALANCE.support_program_account_rescue_ticket_relief,
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk - BALANCE.support_program_account_rescue_sla_relief
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age - BALANCE.support_program_account_rescue_queue_age_relief,
    )
    account.support_load = clamp_int(
        account.support_load - BALANCE.support_program_account_rescue_support_load_relief
    )
    account.renewal_health = clamp_int(
        account.renewal_health + BALANCE.support_program_account_rescue_renewal_health_gain
    )
    account.satisfaction = clamp_int(
        account.satisfaction + BALANCE.support_program_account_rescue_satisfaction_gain
    )
    account.churn_risk = clamp_int(
        account.churn_risk - BALANCE.support_program_account_rescue_churn_relief
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk - (BALANCE.support_program_account_rescue_sla_relief // 2)
    )
    account.escalation_count = max(0, account.escalation_count - 1)

    if lane is SupportLaneFocus.BILLING:
        account.invoice_risk = clamp_int(
            account.invoice_risk - BALANCE.support_program_account_rescue_billing_invoice_relief
        )
        account.failed_payment_risk = clamp_int(
            account.failed_payment_risk
            - BALANCE.support_program_account_rescue_billing_payment_relief
        )
        account.dunning_steps = max(
            0,
            account.dunning_steps - BALANCE.support_program_account_rescue_billing_dunning_relief,
        )
        account.renewal_health = clamp_int(
            account.renewal_health + BALANCE.support_program_route_billing_renewal_health_gain
        )
        _apply_lane_program_relief(
            state.support_program,
            SupportLaneFocus.BILLING,
            BALANCE.support_program_account_rescue_lane_relief,
        )
    elif lane is SupportLaneFocus.ENTERPRISE:
        if account.support_tier is SupportTier.STANDARD:
            account.support_tier = SupportTier.PRIORITY
        account.renewal_health = clamp_int(
            account.renewal_health
            + (BALANCE.support_program_account_rescue_renewal_health_gain // 2)
        )
        account.satisfaction = clamp_int(
            account.satisfaction + BALANCE.support_program_route_onboarding_satisfaction_gain
        )
        _apply_lane_program_relief(
            state.support_program,
            SupportLaneFocus.ENTERPRISE,
            BALANCE.support_program_account_rescue_lane_relief,
        )
    elif lane is SupportLaneFocus.ONBOARDING:
        account.onboarding_health = clamp_int(
            account.onboarding_health
            + BALANCE.support_program_account_rescue_onboarding_health_gain
        )
        account.satisfaction = clamp_int(
            account.satisfaction + BALANCE.support_program_route_onboarding_satisfaction_gain
        )
        _apply_lane_program_relief(
            state.support_program,
            SupportLaneFocus.ONBOARDING,
            BALANCE.support_program_account_rescue_lane_relief,
        )

    return SupportOpsActionSummary(
        message=(
            f"Ran a {lane_label} rescue for {account.name}. "
            f"Cash -{BALANCE.support_program_account_rescue_cost}, "
            f"tickets {account.open_tickets}, renewal health {account.renewal_health}."
        )
    )


def run_lane_recovery(
    state: GameState,
    focus: SupportLaneFocus,
) -> SupportOpsActionSummary:
    """Spend directly on one lane to relieve hotspot pressure and stabilize key accounts."""

    if focus is SupportLaneFocus.BALANCED:
        raise ValueError("Lane recovery requires choosing onboarding, enterprise, or billing.")
    if state.company.cash_on_hand < BALANCE.support_program_lane_recovery_cost:
        raise ValueError("Not enough cash to run a lane recovery plan this turn.")

    accounts = [
        account
        for account in sorted(
            state.customer_accounts,
            key=lambda account: (
                classify_account_support_lane(account) is focus,
                _calculate_account_support_severity(account),
                account.ticket_queue_age,
                account.open_tickets,
            ),
            reverse=True,
        )
        if account.status is not CustomerAccountStatus.CHURNED
        and classify_account_support_lane(account) is focus
    ]
    if not accounts and state.support_program.lane_focus is focus:
        raise ValueError(f"There is no immediate {focus.value} lane pressure to recover.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_lane_recovery_cost
    )
    state.support_program.lane_focus = focus
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue - BALANCE.support_program_lane_recovery_backlog_relief,
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - BALANCE.support_program_lane_recovery_escalation_relief,
    )

    stabilized_accounts = 0
    for account in accounts[:3]:
        account.open_tickets = max(
            0,
            account.open_tickets - BALANCE.support_program_lane_recovery_ticket_relief,
        )
        account.sla_breach_risk = clamp_int(
            account.sla_breach_risk - BALANCE.support_program_lane_recovery_sla_relief
        )
        account.ticket_queue_age = max(
            0,
            account.ticket_queue_age - BALANCE.support_program_lane_recovery_queue_age_relief,
        )
        account.support_load = clamp_int(
            account.support_load - BALANCE.support_program_lane_recovery_support_load_relief
        )
        account.renewal_health = clamp_int(
            account.renewal_health + BALANCE.support_program_lane_recovery_renewal_health_gain
        )
        account.satisfaction = clamp_int(
            account.satisfaction + BALANCE.support_program_lane_recovery_satisfaction_gain
        )
        account.churn_risk = clamp_int(
            account.churn_risk - BALANCE.support_program_lane_recovery_churn_relief
        )
        if focus is SupportLaneFocus.BILLING:
            account.invoice_risk = clamp_int(
                account.invoice_risk - BALANCE.support_program_lane_recovery_billing_invoice_relief
            )
            account.failed_payment_risk = clamp_int(
                account.failed_payment_risk
                - BALANCE.support_program_lane_recovery_billing_payment_relief
            )
            account.dunning_steps = max(
                0,
                account.dunning_steps
                - BALANCE.support_program_lane_recovery_billing_dunning_relief,
            )
        elif focus is SupportLaneFocus.ONBOARDING:
            account.onboarding_health = clamp_int(
                account.onboarding_health
                + BALANCE.support_program_lane_recovery_onboarding_health_gain
            )
        elif focus is SupportLaneFocus.ENTERPRISE and account.support_tier is SupportTier.STANDARD:
            account.support_tier = SupportTier.PRIORITY
        stabilized_accounts += 1

    _apply_lane_program_relief(
        state.support_program,
        focus,
        BALANCE.support_program_lane_recovery_lane_relief + stabilized_accounts,
    )

    return SupportOpsActionSummary(
        message=(
            f"Ran a {focus.value} lane recovery. "
            f"Cash -{BALANCE.support_program_lane_recovery_cost}, "
            "accounts stabilized "
            f"{stabilized_accounts}, backlog {state.support_program.backlog_queue}."
        )
    )


def run_renewal_sweep(state: GameState) -> SupportOpsActionSummary:
    """Stabilize the next renewal wave before support or billing issues compound."""

    if state.company.cash_on_hand < BALANCE.support_program_renewal_sweep_cost:
        raise ValueError("Not enough cash to run a renewal sweep this turn.")

    accounts = [
        account
        for account in sorted(
            state.customer_accounts,
            key=lambda account: (
                _is_renewal_pressure_account(account),
                account.renewal_turn <= BALANCE.renewal_offer_turn_window + 2,
                account.contract_value,
                _calculate_account_support_severity(account),
            ),
            reverse=True,
        )
        if account.status is not CustomerAccountStatus.CHURNED
        and (
            _is_renewal_pressure_account(account)
            or account.renewal_turn <= BALANCE.renewal_offer_turn_window + 2
        )
    ]
    if not accounts:
        raise ValueError("No near-term renewals need a sweep right now.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_renewal_sweep_cost
    )
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue - BALANCE.support_program_renewal_sweep_backlog_relief,
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - BALANCE.support_program_renewal_sweep_escalation_relief,
    )

    stabilized_accounts = 0
    for account in accounts[: BALANCE.support_program_renewal_sweep_account_limit]:
        account.open_tickets = max(
            0,
            account.open_tickets - BALANCE.support_program_renewal_sweep_ticket_relief,
        )
        account.sla_breach_risk = clamp_int(
            account.sla_breach_risk - BALANCE.support_program_renewal_sweep_sla_relief
        )
        account.ticket_queue_age = max(
            0,
            account.ticket_queue_age - BALANCE.support_program_renewal_sweep_queue_age_relief,
        )
        account.support_load = clamp_int(
            account.support_load - BALANCE.support_program_renewal_sweep_support_load_relief
        )
        account.renewal_health = clamp_int(
            account.renewal_health + BALANCE.support_program_renewal_sweep_renewal_health_gain
        )
        account.satisfaction = clamp_int(
            account.satisfaction + BALANCE.support_program_renewal_sweep_satisfaction_gain
        )
        account.churn_risk = clamp_int(
            account.churn_risk - BALANCE.support_program_renewal_sweep_churn_relief
        )
        lane = classify_account_support_lane(account)
        if lane is SupportLaneFocus.BILLING:
            account.invoice_risk = clamp_int(
                account.invoice_risk - BALANCE.support_program_renewal_sweep_billing_invoice_relief
            )
            account.failed_payment_risk = clamp_int(
                account.failed_payment_risk
                - BALANCE.support_program_renewal_sweep_billing_payment_relief
            )
            account.dunning_steps = max(
                0,
                account.dunning_steps
                - BALANCE.support_program_renewal_sweep_billing_dunning_relief,
            )
        elif lane is SupportLaneFocus.ONBOARDING:
            account.onboarding_health = clamp_int(
                account.onboarding_health
                + BALANCE.support_program_renewal_sweep_onboarding_health_gain
            )
        _apply_lane_program_relief(
            state.support_program,
            lane,
            BALANCE.support_program_renewal_sweep_lane_relief,
        )
        stabilized_accounts += 1

    return SupportOpsActionSummary(
        message=(
            f"Ran a renewal sweep across {stabilized_accounts} accounts. "
            f"Cash -{BALANCE.support_program_renewal_sweep_cost}, "
            f"escalations now {state.support_program.escalation_queue}."
        )
    )


def run_enterprise_assurance(state: GameState) -> SupportOpsActionSummary:
    """Stabilize enterprise accounts before public-market or board pressure compounds."""

    if state.company.cash_on_hand < BALANCE.support_program_enterprise_assurance_cost:
        raise ValueError("Not enough cash to run enterprise assurance this turn.")

    accounts = [
        account
        for account in sorted(
            state.customer_accounts,
            key=lambda account: (
                account.contract_value,
                _calculate_account_support_severity(account),
            ),
            reverse=True,
        )
        if account.status is not CustomerAccountStatus.CHURNED
        and account.segment.value == "enterprise"
    ]
    if not accounts:
        raise ValueError("No enterprise accounts need assurance right now.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_enterprise_assurance_cost
    )
    state.support_program.lane_focus = SupportLaneFocus.ENTERPRISE
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - BALANCE.support_program_enterprise_assurance_backlog_relief,
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - BALANCE.support_program_enterprise_assurance_escalation_relief,
    )

    stabilized_accounts = 0
    for account in accounts[: BALANCE.support_program_enterprise_assurance_account_limit]:
        account.open_tickets = max(
            0,
            account.open_tickets - BALANCE.support_program_enterprise_assurance_ticket_relief,
        )
        account.sla_breach_risk = clamp_int(
            account.sla_breach_risk - BALANCE.support_program_enterprise_assurance_sla_relief
        )
        account.ticket_queue_age = max(
            0,
            account.ticket_queue_age
            - BALANCE.support_program_enterprise_assurance_queue_age_relief,
        )
        account.support_load = clamp_int(
            account.support_load - BALANCE.support_program_enterprise_assurance_support_load_relief
        )
        account.renewal_health = clamp_int(
            account.renewal_health
            + BALANCE.support_program_enterprise_assurance_renewal_health_gain
        )
        account.satisfaction = clamp_int(
            account.satisfaction + BALANCE.support_program_enterprise_assurance_satisfaction_gain
        )
        account.churn_risk = clamp_int(
            account.churn_risk - BALANCE.support_program_enterprise_assurance_churn_relief
        )
        if account.support_tier is SupportTier.STANDARD:
            account.support_tier = SupportTier.PRIORITY
        _apply_lane_program_relief(
            state.support_program,
            SupportLaneFocus.ENTERPRISE,
            BALANCE.support_program_enterprise_assurance_lane_relief,
        )
        stabilized_accounts += 1

    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - BALANCE.support_program_enterprise_assurance_board_pressure_relief
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran enterprise assurance across {stabilized_accounts} account(s). "
            f"Cash -{BALANCE.support_program_enterprise_assurance_cost}, "
            f"backlog now {state.support_program.backlog_queue}."
        )
    )


def run_billing_stabilization(state: GameState) -> SupportOpsActionSummary:
    """Cool the billing lane before renewals and covenant stress compound."""

    if state.company.cash_on_hand < BALANCE.support_program_billing_stabilization_cost:
        raise ValueError("Not enough cash to run billing stabilization this turn.")

    accounts = [
        account
        for account in sorted(
            state.customer_accounts,
            key=lambda account: (
                _is_renewal_pressure_account(account),
                account.failed_payment_risk + account.invoice_risk,
                account.contract_value,
            ),
            reverse=True,
        )
        if account.status is not CustomerAccountStatus.CHURNED
        and (
            classify_account_support_lane(account) is SupportLaneFocus.BILLING
            or _is_renewal_pressure_account(account)
        )
    ]
    if not accounts:
        raise ValueError("No billing-heavy accounts need stabilization right now.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_billing_stabilization_cost
    )
    state.support_program.lane_focus = SupportLaneFocus.BILLING
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - BALANCE.support_program_billing_stabilization_backlog_relief,
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - BALANCE.support_program_billing_stabilization_escalation_relief,
    )

    stabilized_accounts = 0
    for account in accounts[: BALANCE.support_program_billing_stabilization_account_limit]:
        account.open_tickets = max(
            0,
            account.open_tickets - BALANCE.support_program_billing_stabilization_ticket_relief,
        )
        account.sla_breach_risk = clamp_int(
            account.sla_breach_risk - BALANCE.support_program_billing_stabilization_sla_relief
        )
        account.ticket_queue_age = max(
            0,
            account.ticket_queue_age
            - BALANCE.support_program_billing_stabilization_queue_age_relief,
        )
        account.support_load = clamp_int(
            account.support_load - BALANCE.support_program_billing_stabilization_support_load_relief
        )
        account.invoice_risk = clamp_int(
            account.invoice_risk - BALANCE.support_program_billing_stabilization_invoice_relief
        )
        account.failed_payment_risk = clamp_int(
            account.failed_payment_risk
            - BALANCE.support_program_billing_stabilization_payment_relief
        )
        account.dunning_steps = max(
            0,
            account.dunning_steps - BALANCE.support_program_billing_stabilization_dunning_relief,
        )
        account.renewal_health = clamp_int(
            account.renewal_health
            + BALANCE.support_program_billing_stabilization_renewal_health_gain
        )
        account.satisfaction = clamp_int(
            account.satisfaction + BALANCE.support_program_billing_stabilization_satisfaction_gain
        )
        account.churn_risk = clamp_int(
            account.churn_risk - BALANCE.support_program_billing_stabilization_churn_relief
        )
        _apply_lane_program_relief(
            state.support_program,
            SupportLaneFocus.BILLING,
            BALANCE.support_program_billing_stabilization_lane_relief,
        )
        stabilized_accounts += 1

    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - BALANCE.support_program_billing_stabilization_board_pressure_relief
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - BALANCE.support_program_billing_stabilization_investor_pressure_relief
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran billing stabilization across {stabilized_accounts} account(s). "
            f"Cash -{BALANCE.support_program_billing_stabilization_cost}, "
            f"billing queue now {state.support_program.escalation_queue}."
        )
    )


def run_onboarding_recovery(state: GameState) -> SupportOpsActionSummary:
    """Rebuild onboarding-heavy accounts before implementation drag reshapes growth."""

    if state.company.cash_on_hand < BALANCE.support_program_onboarding_recovery_cost:
        raise ValueError("Not enough cash to run onboarding recovery this turn.")

    accounts = [
        account
        for account in sorted(
            state.customer_accounts,
            key=lambda account: (
                classify_account_support_lane(account) is SupportLaneFocus.ONBOARDING,
                100 - account.onboarding_health,
                account.support_load,
                account.contract_value,
            ),
            reverse=True,
        )
        if account.status is not CustomerAccountStatus.CHURNED
        and classify_account_support_lane(account) is SupportLaneFocus.ONBOARDING
    ]
    if not accounts:
        raise ValueError("No onboarding-heavy accounts need recovery right now.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_onboarding_recovery_cost
    )
    state.support_program.lane_focus = SupportLaneFocus.ONBOARDING
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - BALANCE.support_program_onboarding_recovery_backlog_relief,
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - BALANCE.support_program_onboarding_recovery_escalation_relief,
    )

    stabilized_accounts = 0
    for account in accounts[: BALANCE.support_program_onboarding_recovery_account_limit]:
        account.open_tickets = max(
            0,
            account.open_tickets - BALANCE.support_program_onboarding_recovery_ticket_relief,
        )
        account.sla_breach_risk = clamp_int(
            account.sla_breach_risk - BALANCE.support_program_onboarding_recovery_sla_relief
        )
        account.ticket_queue_age = max(
            0,
            account.ticket_queue_age - BALANCE.support_program_onboarding_recovery_queue_age_relief,
        )
        account.support_load = clamp_int(
            account.support_load - BALANCE.support_program_onboarding_recovery_support_load_relief
        )
        account.onboarding_health = clamp_int(
            account.onboarding_health
            + BALANCE.support_program_onboarding_recovery_onboarding_health_gain
        )
        account.satisfaction = clamp_int(
            account.satisfaction + BALANCE.support_program_onboarding_recovery_satisfaction_gain
        )
        account.renewal_health = clamp_int(
            account.renewal_health + BALANCE.support_program_onboarding_recovery_renewal_health_gain
        )
        account.churn_risk = clamp_int(
            account.churn_risk - BALANCE.support_program_onboarding_recovery_churn_relief
        )
        _apply_lane_program_relief(
            state.support_program,
            SupportLaneFocus.ONBOARDING,
            BALANCE.support_program_onboarding_recovery_lane_relief,
        )
        stabilized_accounts += 1

    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - BALANCE.support_program_onboarding_recovery_board_pressure_relief
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran onboarding recovery across {stabilized_accounts} account(s). "
            f"Cash -{BALANCE.support_program_onboarding_recovery_cost}, "
            f"onboarding queue now {state.support_program.backlog_queue}."
        )
    )


def run_onboarding_fast_track(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Push one onboarding-heavy account through a more aggressive recovery lane."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < BALANCE.support_program_onboarding_fast_track_cost:
        raise ValueError("Not enough cash to run an onboarding fast track this turn.")
    if (
        classify_account_support_lane(account) is not SupportLaneFocus.ONBOARDING
        and account.onboarding_health >= 60
        and account.support_load <= 18
        and account.open_tickets <= 1
    ):
        raise ValueError("That account does not need an onboarding fast track right now.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_onboarding_fast_track_cost
    )
    state.support_program.lane_focus = SupportLaneFocus.ONBOARDING
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - BALANCE.support_program_onboarding_fast_track_backlog_relief,
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - BALANCE.support_program_onboarding_fast_track_escalation_relief,
    )
    account.open_tickets = max(
        0,
        account.open_tickets - BALANCE.support_program_onboarding_fast_track_ticket_relief,
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk - BALANCE.support_program_onboarding_fast_track_sla_relief
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age - BALANCE.support_program_onboarding_fast_track_queue_age_relief,
    )
    account.support_load = clamp_int(
        account.support_load - BALANCE.support_program_onboarding_fast_track_support_load_relief
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + BALANCE.support_program_onboarding_fast_track_onboarding_health_gain
    )
    account.satisfaction = clamp_int(
        account.satisfaction + BALANCE.support_program_onboarding_fast_track_satisfaction_gain
    )
    account.renewal_health = clamp_int(
        account.renewal_health + BALANCE.support_program_onboarding_fast_track_renewal_health_gain
    )
    account.churn_risk = clamp_int(
        account.churn_risk - BALANCE.support_program_onboarding_fast_track_churn_relief
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    if account.support_tier is SupportTier.STANDARD:
        account.support_tier = SupportTier.PRIORITY
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ONBOARDING,
        BALANCE.support_program_onboarding_fast_track_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - BALANCE.support_program_onboarding_fast_track_board_pressure_relief
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran an onboarding fast track for {account.name}. "
            f"Cash -{BALANCE.support_program_onboarding_fast_track_cost}, "
            f"onboarding health now {account.onboarding_health}."
        )
    )


def run_onboarding_control_tower(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run a deeper onboarding follow-up pass for one implementation-heavy account."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    cost = quantize_money(
        BALANCE.support_program_onboarding_recovery_cost
        + BALANCE.support_program_onboarding_fast_track_cost
    )
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < cost:
        raise ValueError("Not enough cash to run an onboarding control tower this turn.")
    if (
        classify_account_support_lane(account) is not SupportLaneFocus.ONBOARDING
        and account.onboarding_health >= 64
        and account.support_load <= 18
        and account.open_tickets <= 1
        and account.sla_breach_risk <= 10
    ):
        raise ValueError("That account does not need an onboarding control tower right now.")

    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - cost)
    state.support_program.lane_focus = SupportLaneFocus.ONBOARDING
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_onboarding_recovery_backlog_relief
            + BALANCE.support_program_onboarding_fast_track_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_onboarding_recovery_escalation_relief
            + BALANCE.support_program_onboarding_fast_track_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_onboarding_recovery_ticket_relief
            + BALANCE.support_program_onboarding_fast_track_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_onboarding_recovery_sla_relief
            + BALANCE.support_program_onboarding_fast_track_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_onboarding_recovery_queue_age_relief
            + BALANCE.support_program_onboarding_fast_track_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_onboarding_recovery_support_load_relief
            + BALANCE.support_program_onboarding_fast_track_support_load_relief
        )
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + (
            BALANCE.support_program_onboarding_recovery_onboarding_health_gain
            + BALANCE.support_program_onboarding_fast_track_onboarding_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_onboarding_recovery_satisfaction_gain
            + BALANCE.support_program_onboarding_fast_track_satisfaction_gain
        )
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_onboarding_recovery_renewal_health_gain
            + BALANCE.support_program_onboarding_fast_track_renewal_health_gain
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_onboarding_recovery_churn_relief
            + BALANCE.support_program_onboarding_fast_track_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    if account.support_tier is SupportTier.STANDARD:
        account.support_tier = SupportTier.PRIORITY
    elif account.support_tier is SupportTier.PRIORITY:
        account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ONBOARDING,
        BALANCE.support_program_onboarding_recovery_lane_relief
        + BALANCE.support_program_onboarding_fast_track_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_onboarding_recovery_board_pressure_relief
            + BALANCE.support_program_onboarding_fast_track_board_pressure_relief
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran an onboarding control tower for {account.name}. Cash -{cost}, "
            f"onboarding health now {account.onboarding_health}."
        )
    )


def run_onboarding_launch_cell(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the deepest onboarding follow-up before implementation drag hardens."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    cost = quantize_money(
        BALANCE.support_program_onboarding_recovery_cost
        + BALANCE.support_program_onboarding_fast_track_cost
        + BALANCE.support_program_onboarding_recovery_cost
    )
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < cost:
        raise ValueError("Not enough cash to run an onboarding launch cell this turn.")
    if (
        classify_account_support_lane(account) is not SupportLaneFocus.ONBOARDING
        and account.onboarding_health >= 68
        and account.support_load <= 16
        and account.open_tickets <= 1
        and account.sla_breach_risk <= 10
        and account.renewal_health >= 74
    ):
        raise ValueError("That account does not need an onboarding launch cell right now.")

    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - cost)
    state.support_program.lane_focus = SupportLaneFocus.ONBOARDING
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_onboarding_recovery_backlog_relief * 2
            + BALANCE.support_program_onboarding_fast_track_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_onboarding_recovery_escalation_relief * 2
            + BALANCE.support_program_onboarding_fast_track_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_onboarding_recovery_ticket_relief * 2
            + BALANCE.support_program_onboarding_fast_track_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_onboarding_recovery_sla_relief * 2
            + BALANCE.support_program_onboarding_fast_track_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_onboarding_recovery_queue_age_relief * 2
            + BALANCE.support_program_onboarding_fast_track_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_onboarding_recovery_support_load_relief * 2
            + BALANCE.support_program_onboarding_fast_track_support_load_relief
        )
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + (
            BALANCE.support_program_onboarding_recovery_onboarding_health_gain * 2
            + BALANCE.support_program_onboarding_fast_track_onboarding_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_onboarding_recovery_satisfaction_gain * 2
            + BALANCE.support_program_onboarding_fast_track_satisfaction_gain
        )
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_onboarding_recovery_renewal_health_gain * 2
            + BALANCE.support_program_onboarding_fast_track_renewal_health_gain
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_onboarding_recovery_churn_relief * 2
            + BALANCE.support_program_onboarding_fast_track_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    if account.support_tier is SupportTier.STANDARD:
        account.support_tier = SupportTier.PRIORITY
    else:
        account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ONBOARDING,
        BALANCE.support_program_onboarding_recovery_lane_relief * 2
        + BALANCE.support_program_onboarding_fast_track_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_onboarding_recovery_board_pressure_relief * 2
            + BALANCE.support_program_onboarding_fast_track_board_pressure_relief
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran an onboarding launch cell for {account.name}. Cash -{cost}, "
            f"onboarding health now {account.onboarding_health}."
        )
    )


def run_onboarding_adoption_hub(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the deepest onboarding follow-up when implementation drag is defining the run."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    cost = quantize_money(
        BALANCE.support_program_onboarding_recovery_cost * 3
        + BALANCE.support_program_onboarding_fast_track_cost * 2
    )
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < cost:
        raise ValueError("Not enough cash to run an onboarding adoption hub this turn.")
    if (
        classify_account_support_lane(account) is not SupportLaneFocus.ONBOARDING
        and account.onboarding_health >= 72
        and account.support_load <= 14
        and account.open_tickets <= 1
        and account.sla_breach_risk <= 10
        and account.renewal_health >= 78
    ):
        raise ValueError("That account does not need an onboarding adoption hub right now.")

    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - cost)
    state.support_program.lane_focus = SupportLaneFocus.ONBOARDING
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_onboarding_recovery_backlog_relief * 3
            + BALANCE.support_program_onboarding_fast_track_backlog_relief * 2
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_onboarding_recovery_escalation_relief * 3
            + BALANCE.support_program_onboarding_fast_track_escalation_relief * 2
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_onboarding_recovery_ticket_relief * 3
            + BALANCE.support_program_onboarding_fast_track_ticket_relief * 2
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_onboarding_recovery_sla_relief * 3
            + BALANCE.support_program_onboarding_fast_track_sla_relief * 2
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_onboarding_recovery_queue_age_relief * 3
            + BALANCE.support_program_onboarding_fast_track_queue_age_relief * 2
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_onboarding_recovery_support_load_relief * 3
            + BALANCE.support_program_onboarding_fast_track_support_load_relief * 2
        )
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + (
            BALANCE.support_program_onboarding_recovery_onboarding_health_gain * 3
            + BALANCE.support_program_onboarding_fast_track_onboarding_health_gain * 2
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_onboarding_recovery_satisfaction_gain * 3
            + BALANCE.support_program_onboarding_fast_track_satisfaction_gain * 2
        )
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_onboarding_recovery_renewal_health_gain * 3
            + BALANCE.support_program_onboarding_fast_track_renewal_health_gain * 2
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_onboarding_recovery_churn_relief * 3
            + BALANCE.support_program_onboarding_fast_track_churn_relief * 2
        )
    )
    account.escalation_count = max(0, account.escalation_count - 2)
    if account.support_tier is SupportTier.STANDARD:
        account.support_tier = SupportTier.PRIORITY
    else:
        account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ONBOARDING,
        BALANCE.support_program_onboarding_recovery_lane_relief * 3
        + BALANCE.support_program_onboarding_fast_track_lane_relief * 2,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_onboarding_recovery_board_pressure_relief * 3
            + BALANCE.support_program_onboarding_fast_track_board_pressure_relief * 2
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran an onboarding adoption hub for {account.name}. Cash -{cost}, "
            f"onboarding health now {account.onboarding_health}."
        )
    )


def run_onboarding_stability_board(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the heaviest onboarding follow-up when implementation drag is now a board issue."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    cost = quantize_money(
        BALANCE.support_program_onboarding_recovery_cost * 4
        + BALANCE.support_program_onboarding_fast_track_cost * 3
    )
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < cost:
        raise ValueError("Not enough cash to run an onboarding stability board this turn.")
    if (
        classify_account_support_lane(account) is not SupportLaneFocus.ONBOARDING
        and account.onboarding_health >= 76
        and account.support_load <= 12
        and account.open_tickets <= 1
        and account.sla_breach_risk <= 8
        and account.renewal_health >= 82
    ):
        raise ValueError("That account does not need an onboarding stability board right now.")

    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - cost)
    state.support_program.lane_focus = SupportLaneFocus.ONBOARDING
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_onboarding_recovery_backlog_relief * 4
            + BALANCE.support_program_onboarding_fast_track_backlog_relief * 3
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_onboarding_recovery_escalation_relief * 4
            + BALANCE.support_program_onboarding_fast_track_escalation_relief * 3
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_onboarding_recovery_ticket_relief * 4
            + BALANCE.support_program_onboarding_fast_track_ticket_relief * 3
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_onboarding_recovery_sla_relief * 4
            + BALANCE.support_program_onboarding_fast_track_sla_relief * 3
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_onboarding_recovery_queue_age_relief * 4
            + BALANCE.support_program_onboarding_fast_track_queue_age_relief * 3
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_onboarding_recovery_support_load_relief * 4
            + BALANCE.support_program_onboarding_fast_track_support_load_relief * 3
        )
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + (
            BALANCE.support_program_onboarding_recovery_onboarding_health_gain * 4
            + BALANCE.support_program_onboarding_fast_track_onboarding_health_gain * 3
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_onboarding_recovery_satisfaction_gain * 4
            + BALANCE.support_program_onboarding_fast_track_satisfaction_gain * 3
        )
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_onboarding_recovery_renewal_health_gain * 4
            + BALANCE.support_program_onboarding_fast_track_renewal_health_gain * 3
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_onboarding_recovery_churn_relief * 4
            + BALANCE.support_program_onboarding_fast_track_churn_relief * 3
        )
    )
    account.escalation_count = max(0, account.escalation_count - 2)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ONBOARDING,
        BALANCE.support_program_onboarding_recovery_lane_relief * 4
        + BALANCE.support_program_onboarding_fast_track_lane_relief * 3,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_onboarding_recovery_board_pressure_relief * 4
            + BALANCE.support_program_onboarding_fast_track_board_pressure_relief * 3
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran an onboarding stability board for {account.name}. Cash -{cost}, "
            f"onboarding health now {account.onboarding_health}."
        )
    )


def run_onboarding_retention_mesh(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the hardest onboarding follow-up when implementation drag is already hitting renewals."""

    base_cost = quantize_money(
        BALANCE.support_program_onboarding_recovery_cost * 4
        + BALANCE.support_program_onboarding_fast_track_cost * 3
    )
    extra_cost = quantize_money(
        BALANCE.support_program_onboarding_recovery_cost
        + BALANCE.support_program_onboarding_fast_track_cost
    )
    total_cost = quantize_money(base_cost + extra_cost)
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to run an onboarding retention mesh this turn.")

    run_onboarding_stability_board(state, account_id)
    account = _get_account_by_id(state.customer_accounts, account_id)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_onboarding_recovery_backlog_relief
            + BALANCE.support_program_onboarding_fast_track_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_onboarding_recovery_escalation_relief
            + BALANCE.support_program_onboarding_fast_track_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_onboarding_recovery_ticket_relief
            + BALANCE.support_program_onboarding_fast_track_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_onboarding_recovery_sla_relief
            + BALANCE.support_program_onboarding_fast_track_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_onboarding_recovery_queue_age_relief
            + BALANCE.support_program_onboarding_fast_track_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_onboarding_recovery_support_load_relief
            + BALANCE.support_program_onboarding_fast_track_support_load_relief
        )
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + (
            BALANCE.support_program_onboarding_recovery_onboarding_health_gain
            + BALANCE.support_program_onboarding_fast_track_onboarding_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_onboarding_recovery_satisfaction_gain
            + BALANCE.support_program_onboarding_fast_track_satisfaction_gain
        )
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_onboarding_recovery_renewal_health_gain
            + BALANCE.support_program_onboarding_fast_track_renewal_health_gain
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_onboarding_recovery_churn_relief
            + BALANCE.support_program_onboarding_fast_track_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ONBOARDING,
        BALANCE.support_program_onboarding_recovery_lane_relief
        + BALANCE.support_program_onboarding_fast_track_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_onboarding_recovery_board_pressure_relief
            + BALANCE.support_program_onboarding_fast_track_board_pressure_relief
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran an onboarding retention mesh for {account.name}. Cash -{total_cost}, "
            f"onboarding health now {account.onboarding_health}."
        )
    )


def run_onboarding_assurance_grid(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the final onboarding recovery loop for terminal implementation drag."""

    base_cost = quantize_money(
        BALANCE.support_program_onboarding_recovery_cost * 5
        + BALANCE.support_program_onboarding_fast_track_cost * 4
    )
    extra_cost = quantize_money(
        BALANCE.support_program_onboarding_recovery_cost
        + BALANCE.support_program_onboarding_fast_track_cost
    )
    total_cost = quantize_money(base_cost + extra_cost)
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to run an onboarding assurance grid this turn.")

    run_onboarding_retention_mesh(state, account_id)
    account = _get_account_by_id(state.customer_accounts, account_id)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_onboarding_recovery_backlog_relief
            + BALANCE.support_program_onboarding_fast_track_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_onboarding_recovery_escalation_relief
            + BALANCE.support_program_onboarding_fast_track_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_onboarding_recovery_ticket_relief
            + BALANCE.support_program_onboarding_fast_track_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_onboarding_recovery_sla_relief
            + BALANCE.support_program_onboarding_fast_track_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_onboarding_recovery_queue_age_relief
            + BALANCE.support_program_onboarding_fast_track_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_onboarding_recovery_support_load_relief
            + BALANCE.support_program_onboarding_fast_track_support_load_relief
        )
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + (
            BALANCE.support_program_onboarding_recovery_onboarding_health_gain
            + BALANCE.support_program_onboarding_fast_track_onboarding_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_onboarding_recovery_satisfaction_gain
            + BALANCE.support_program_onboarding_fast_track_satisfaction_gain
        )
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_onboarding_recovery_renewal_health_gain
            + BALANCE.support_program_onboarding_fast_track_renewal_health_gain
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_onboarding_recovery_churn_relief
            + BALANCE.support_program_onboarding_fast_track_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ONBOARDING,
        BALANCE.support_program_onboarding_recovery_lane_relief
        + BALANCE.support_program_onboarding_fast_track_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_onboarding_recovery_board_pressure_relief
            + BALANCE.support_program_onboarding_fast_track_board_pressure_relief
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran an onboarding assurance grid for {account.name}. Cash -{total_cost}, "
            f"onboarding health now {account.onboarding_health}."
        )
    )


def run_onboarding_durability_mesh(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the final onboarding durability loop when implementation drag is still active."""

    base_cost = quantize_money(
        BALANCE.support_program_onboarding_recovery_cost * 5
        + BALANCE.support_program_onboarding_fast_track_cost * 4
    )
    extra_cost = quantize_money(
        BALANCE.support_program_onboarding_recovery_cost * 2
        + BALANCE.support_program_onboarding_fast_track_cost
    )
    total_cost = quantize_money(base_cost + extra_cost)
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to run an onboarding durability mesh this turn.")

    run_onboarding_assurance_grid(state, account_id)
    account = _get_account_by_id(state.customer_accounts, account_id)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_onboarding_recovery_backlog_relief * 2
            + BALANCE.support_program_onboarding_fast_track_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_onboarding_recovery_escalation_relief * 2
            + BALANCE.support_program_onboarding_fast_track_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_onboarding_recovery_ticket_relief * 2
            + BALANCE.support_program_onboarding_fast_track_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_onboarding_recovery_sla_relief * 2
            + BALANCE.support_program_onboarding_fast_track_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_onboarding_recovery_queue_age_relief * 2
            + BALANCE.support_program_onboarding_fast_track_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_onboarding_recovery_support_load_relief * 2
            + BALANCE.support_program_onboarding_fast_track_support_load_relief
        )
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + (
            BALANCE.support_program_onboarding_recovery_onboarding_health_gain * 2
            + BALANCE.support_program_onboarding_fast_track_onboarding_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_onboarding_recovery_satisfaction_gain * 2
            + BALANCE.support_program_onboarding_fast_track_satisfaction_gain
        )
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_onboarding_recovery_renewal_health_gain * 2
            + BALANCE.support_program_onboarding_fast_track_renewal_health_gain
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_onboarding_recovery_churn_relief * 2
            + BALANCE.support_program_onboarding_fast_track_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ONBOARDING,
        BALANCE.support_program_onboarding_recovery_lane_relief * 2
        + BALANCE.support_program_onboarding_fast_track_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_onboarding_recovery_board_pressure_relief * 2
            + BALANCE.support_program_onboarding_fast_track_board_pressure_relief
        )
    )
    state.finance.board_confidence = clamp_int(state.finance.board_confidence + 2)
    state.company.reputation = clamp_int(state.company.reputation + 1)
    return SupportOpsActionSummary(
        message=(
            f"Ran an onboarding durability mesh for {account.name}. Cash -{total_cost}, "
            f"onboarding health now {account.onboarding_health}."
        )
    )


def run_onboarding_continuity_lattice(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the deepest onboarding continuity loop when implementation drag still dominates."""

    base_cost = quantize_money(
        BALANCE.support_program_onboarding_recovery_cost * 7
        + BALANCE.support_program_onboarding_fast_track_cost * 5
    )
    extra_cost = quantize_money(
        BALANCE.support_program_onboarding_recovery_cost * 2
        + BALANCE.support_program_onboarding_fast_track_cost * 2
    )
    total_cost = quantize_money(base_cost + extra_cost)
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to run an onboarding continuity lattice this turn.")

    run_onboarding_durability_mesh(state, account_id)
    account = _get_account_by_id(state.customer_accounts, account_id)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_onboarding_recovery_backlog_relief * 2
            + BALANCE.support_program_onboarding_fast_track_backlog_relief * 2
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_onboarding_recovery_escalation_relief * 2
            + BALANCE.support_program_onboarding_fast_track_escalation_relief * 2
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_onboarding_recovery_ticket_relief * 2
            + BALANCE.support_program_onboarding_fast_track_ticket_relief * 2
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_onboarding_recovery_sla_relief * 2
            + BALANCE.support_program_onboarding_fast_track_sla_relief * 2
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_onboarding_recovery_queue_age_relief * 2
            + BALANCE.support_program_onboarding_fast_track_queue_age_relief * 2
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_onboarding_recovery_support_load_relief * 2
            + BALANCE.support_program_onboarding_fast_track_support_load_relief * 2
        )
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + (
            BALANCE.support_program_onboarding_recovery_onboarding_health_gain * 2
            + BALANCE.support_program_onboarding_fast_track_onboarding_health_gain * 2
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_onboarding_recovery_satisfaction_gain * 2
            + BALANCE.support_program_onboarding_fast_track_satisfaction_gain * 2
        )
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_onboarding_recovery_renewal_health_gain * 2
            + BALANCE.support_program_onboarding_fast_track_renewal_health_gain * 2
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_onboarding_recovery_churn_relief * 2
            + BALANCE.support_program_onboarding_fast_track_churn_relief * 2
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ONBOARDING,
        BALANCE.support_program_onboarding_recovery_lane_relief * 2
        + BALANCE.support_program_onboarding_fast_track_lane_relief * 2,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_onboarding_recovery_board_pressure_relief * 2
            + BALANCE.support_program_onboarding_fast_track_board_pressure_relief * 2
        )
    )
    state.finance.board_confidence = clamp_int(state.finance.board_confidence + 2)
    state.company.reputation = clamp_int(state.company.reputation + 1)
    return SupportOpsActionSummary(
        message=(
            f"Ran an onboarding continuity lattice for {account.name}. Cash -{total_cost}, "
            f"onboarding health now {account.onboarding_health}."
        )
    )


def run_onboarding_continuity_bureau(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the final onboarding follow-up when continuity still needs one more control loop."""

    base_cost = quantize_money(
        BALANCE.support_program_onboarding_recovery_cost * 9
        + BALANCE.support_program_onboarding_fast_track_cost * 7
    )
    extra_cost = quantize_money(
        BALANCE.support_program_onboarding_recovery_cost * 2
        + BALANCE.support_program_onboarding_fast_track_cost * 2
    )
    total_cost = quantize_money(base_cost + extra_cost)
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to run an onboarding continuity bureau this turn.")

    run_onboarding_continuity_lattice(state, account_id)
    account = _get_account_by_id(state.customer_accounts, account_id)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_onboarding_recovery_backlog_relief * 2
            + BALANCE.support_program_onboarding_fast_track_backlog_relief * 2
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_onboarding_recovery_escalation_relief * 2
            + BALANCE.support_program_onboarding_fast_track_escalation_relief * 2
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_onboarding_recovery_ticket_relief * 2
            + BALANCE.support_program_onboarding_fast_track_ticket_relief * 2
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_onboarding_recovery_sla_relief * 2
            + BALANCE.support_program_onboarding_fast_track_sla_relief * 2
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_onboarding_recovery_queue_age_relief * 2
            + BALANCE.support_program_onboarding_fast_track_queue_age_relief * 2
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_onboarding_recovery_support_load_relief * 2
            + BALANCE.support_program_onboarding_fast_track_support_load_relief * 2
        )
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + (
            BALANCE.support_program_onboarding_recovery_onboarding_health_gain * 2
            + BALANCE.support_program_onboarding_fast_track_onboarding_health_gain * 2
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_onboarding_recovery_satisfaction_gain * 2
            + BALANCE.support_program_onboarding_fast_track_satisfaction_gain * 2
        )
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_onboarding_recovery_renewal_health_gain * 2
            + BALANCE.support_program_onboarding_fast_track_renewal_health_gain * 2
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_onboarding_recovery_churn_relief * 2
            + BALANCE.support_program_onboarding_fast_track_churn_relief * 2
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ONBOARDING,
        BALANCE.support_program_onboarding_recovery_lane_relief * 2
        + BALANCE.support_program_onboarding_fast_track_lane_relief * 2,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_onboarding_recovery_board_pressure_relief * 2
            + BALANCE.support_program_onboarding_fast_track_board_pressure_relief * 2
        )
    )
    state.finance.board_confidence = clamp_int(state.finance.board_confidence + 2)
    state.company.reputation = clamp_int(state.company.reputation + 1)
    return SupportOpsActionSummary(
        message=(
            f"Ran an onboarding continuity bureau for {account.name}. Cash -{total_cost}, "
            f"onboarding health now {account.onboarding_health}."
        )
    )


def run_onboarding_continuity_secretariat(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the terminal onboarding follow-up when bureau-level continuity still is not enough."""

    base_cost = quantize_money(
        BALANCE.support_program_onboarding_recovery_cost * 11
        + BALANCE.support_program_onboarding_fast_track_cost * 9
    )
    extra_cost = quantize_money(
        BALANCE.support_program_onboarding_recovery_cost * 2
        + BALANCE.support_program_onboarding_fast_track_cost * 2
    )
    total_cost = quantize_money(base_cost + extra_cost)
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to run an onboarding continuity secretariat this turn.")

    run_onboarding_continuity_bureau(state, account_id)
    account = _get_account_by_id(state.customer_accounts, account_id)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_onboarding_recovery_backlog_relief * 2
            + BALANCE.support_program_onboarding_fast_track_backlog_relief * 2
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_onboarding_recovery_escalation_relief * 2
            + BALANCE.support_program_onboarding_fast_track_escalation_relief * 2
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_onboarding_recovery_ticket_relief * 2
            + BALANCE.support_program_onboarding_fast_track_ticket_relief * 2
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_onboarding_recovery_sla_relief * 2
            + BALANCE.support_program_onboarding_fast_track_sla_relief * 2
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_onboarding_recovery_queue_age_relief * 2
            + BALANCE.support_program_onboarding_fast_track_queue_age_relief * 2
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_onboarding_recovery_support_load_relief * 2
            + BALANCE.support_program_onboarding_fast_track_support_load_relief * 2
        )
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + (
            BALANCE.support_program_onboarding_recovery_onboarding_health_gain * 2
            + BALANCE.support_program_onboarding_fast_track_onboarding_health_gain * 2
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_onboarding_recovery_satisfaction_gain * 2
            + BALANCE.support_program_onboarding_fast_track_satisfaction_gain * 2
        )
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_onboarding_recovery_renewal_health_gain * 2
            + BALANCE.support_program_onboarding_fast_track_renewal_health_gain * 2
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_onboarding_recovery_churn_relief * 2
            + BALANCE.support_program_onboarding_fast_track_churn_relief * 2
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ONBOARDING,
        BALANCE.support_program_onboarding_recovery_lane_relief * 2
        + BALANCE.support_program_onboarding_fast_track_lane_relief * 2,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_onboarding_recovery_board_pressure_relief * 2
            + BALANCE.support_program_onboarding_fast_track_board_pressure_relief * 2
        )
    )
    state.finance.board_confidence = clamp_int(state.finance.board_confidence + 2)
    state.company.reputation = clamp_int(state.company.reputation + 1)
    return SupportOpsActionSummary(
        message=(
            f"Ran an onboarding continuity secretariat for {account.name}. Cash -{total_cost}, "
            f"onboarding health now {account.onboarding_health}."
        )
    )


def run_onboarding_continuity_authority(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the deepest onboarding continuity loop after the secretariat tier saturates."""

    base_cost = quantize_money(
        BALANCE.support_program_onboarding_recovery_cost * 13
        + BALANCE.support_program_onboarding_fast_track_cost * 11
    )
    extra_cost = quantize_money(
        BALANCE.support_program_onboarding_recovery_cost * 2
        + BALANCE.support_program_onboarding_fast_track_cost * 2
    )
    total_cost = quantize_money(base_cost + extra_cost)
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to run an onboarding continuity authority this turn.")

    run_onboarding_continuity_secretariat(state, account_id)
    account = _get_account_by_id(state.customer_accounts, account_id)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_onboarding_recovery_backlog_relief * 2
            + BALANCE.support_program_onboarding_fast_track_backlog_relief * 2
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_onboarding_recovery_escalation_relief * 2
            + BALANCE.support_program_onboarding_fast_track_escalation_relief * 2
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_onboarding_recovery_ticket_relief * 2
            + BALANCE.support_program_onboarding_fast_track_ticket_relief * 2
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_onboarding_recovery_sla_relief * 2
            + BALANCE.support_program_onboarding_fast_track_sla_relief * 2
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_onboarding_recovery_queue_age_relief * 2
            + BALANCE.support_program_onboarding_fast_track_queue_age_relief * 2
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_onboarding_recovery_support_load_relief * 2
            + BALANCE.support_program_onboarding_fast_track_support_load_relief * 2
        )
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + (
            BALANCE.support_program_onboarding_recovery_onboarding_health_gain * 2
            + BALANCE.support_program_onboarding_fast_track_onboarding_health_gain * 2
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_onboarding_recovery_satisfaction_gain * 2
            + BALANCE.support_program_onboarding_fast_track_satisfaction_gain * 2
        )
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_onboarding_recovery_renewal_health_gain * 2
            + BALANCE.support_program_onboarding_fast_track_renewal_health_gain * 2
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_onboarding_recovery_churn_relief * 2
            + BALANCE.support_program_onboarding_fast_track_churn_relief * 2
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ONBOARDING,
        BALANCE.support_program_onboarding_recovery_lane_relief * 2
        + BALANCE.support_program_onboarding_fast_track_lane_relief * 2,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_onboarding_recovery_board_pressure_relief * 2
            + BALANCE.support_program_onboarding_fast_track_board_pressure_relief * 2
        )
    )
    state.finance.board_confidence = clamp_int(state.finance.board_confidence + 2)
    state.company.reputation = clamp_int(state.company.reputation + 1)
    return SupportOpsActionSummary(
        message=(
            f"Ran an onboarding continuity authority for {account.name}. Cash -{total_cost}, "
            f"onboarding health now {account.onboarding_health}."
        )
    )


def run_enterprise_queue_reset(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run a heavier queue reset for one enterprise-facing hotspot account."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < BALANCE.support_program_enterprise_queue_reset_cost:
        raise ValueError("Not enough cash to run an enterprise queue reset this turn.")
    if (
        account.segment is not MarketSegment.ENTERPRISE
        and account.support_tier is SupportTier.STANDARD
        and account.contract_value < Decimal("1800.00")
    ):
        raise ValueError("That account is not enterprise-exposed enough for a queue reset.")
    if (
        account.open_tickets <= 1
        and account.sla_breach_risk <= 18
        and account.ticket_queue_age <= 1
        and account.support_load <= 18
    ):
        raise ValueError("That account does not need an enterprise queue reset right now.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_enterprise_queue_reset_cost
    )
    state.support_program.lane_focus = SupportLaneFocus.ENTERPRISE
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - BALANCE.support_program_enterprise_queue_reset_backlog_relief,
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - BALANCE.support_program_enterprise_queue_reset_escalation_relief,
    )
    account.open_tickets = max(
        0,
        account.open_tickets - BALANCE.support_program_enterprise_queue_reset_ticket_relief,
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk - BALANCE.support_program_enterprise_queue_reset_sla_relief
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age - BALANCE.support_program_enterprise_queue_reset_queue_age_relief,
    )
    account.support_load = clamp_int(
        account.support_load - BALANCE.support_program_enterprise_queue_reset_support_load_relief
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + BALANCE.support_program_enterprise_queue_reset_onboarding_health_gain
    )
    account.renewal_health = clamp_int(
        account.renewal_health + BALANCE.support_program_enterprise_queue_reset_renewal_health_gain
    )
    account.satisfaction = clamp_int(
        account.satisfaction + BALANCE.support_program_enterprise_queue_reset_satisfaction_gain
    )
    account.churn_risk = clamp_int(
        account.churn_risk - BALANCE.support_program_enterprise_queue_reset_churn_relief
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    if account.support_tier is SupportTier.STANDARD:
        account.support_tier = SupportTier.PRIORITY
    else:
        account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ENTERPRISE,
        BALANCE.support_program_enterprise_queue_reset_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - BALANCE.support_program_enterprise_queue_reset_board_pressure_relief
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + BALANCE.support_program_enterprise_queue_reset_board_confidence_gain
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran an enterprise queue reset for {account.name}. "
            f"Cash -{BALANCE.support_program_enterprise_queue_reset_cost}, "
            f"SLA risk now {account.sla_breach_risk}."
        )
    )


def run_white_glove_recovery(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Stabilize one premium account before high-touch support pressure defines the run."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < BALANCE.support_program_white_glove_recovery_cost:
        raise ValueError("Not enough cash to run a white-glove recovery this turn.")
    if (
        account.support_tier is SupportTier.STANDARD
        and account.contract_value < Decimal("2000.00")
        and account.segment is not MarketSegment.ENTERPRISE
    ):
        raise ValueError("That account is not premium enough for a white-glove recovery.")
    if (
        account.open_tickets <= 1
        and account.sla_breach_risk <= 18
        and account.ticket_queue_age <= 1
        and account.support_load <= 18
        and account.invoice_risk <= 10
        and account.failed_payment_risk <= 10
    ):
        raise ValueError("That account does not need white-glove recovery right now.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_white_glove_recovery_cost
    )
    lane = classify_account_support_lane(account)
    if lane is not SupportLaneFocus.BALANCED:
        state.support_program.lane_focus = lane
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - BALANCE.support_program_white_glove_recovery_backlog_relief,
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - BALANCE.support_program_white_glove_recovery_escalation_relief,
    )
    account.open_tickets = max(
        0,
        account.open_tickets - BALANCE.support_program_white_glove_recovery_ticket_relief,
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk - BALANCE.support_program_white_glove_recovery_sla_relief
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age - BALANCE.support_program_white_glove_recovery_queue_age_relief,
    )
    account.support_load = clamp_int(
        account.support_load - BALANCE.support_program_white_glove_recovery_support_load_relief
    )
    account.invoice_risk = clamp_int(
        account.invoice_risk - BALANCE.support_program_white_glove_recovery_invoice_relief
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk - BALANCE.support_program_white_glove_recovery_payment_relief
    )
    account.satisfaction = clamp_int(
        account.satisfaction + BALANCE.support_program_white_glove_recovery_satisfaction_gain
    )
    account.renewal_health = clamp_int(
        account.renewal_health + BALANCE.support_program_white_glove_recovery_renewal_health_gain
    )
    account.churn_risk = clamp_int(
        account.churn_risk - BALANCE.support_program_white_glove_recovery_churn_relief
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    account.support_tier = SupportTier.WHITE_GLOVE
    if lane is not SupportLaneFocus.BALANCED:
        _apply_lane_program_relief(
            state.support_program,
            lane,
            BALANCE.support_program_white_glove_recovery_lane_relief,
        )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - BALANCE.support_program_white_glove_recovery_board_pressure_relief
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + BALANCE.support_program_white_glove_recovery_board_confidence_gain
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a white-glove recovery for {account.name}. "
            f"Cash -{BALANCE.support_program_white_glove_recovery_cost}, "
            f"SLA risk now {account.sla_breach_risk}."
        )
    )


def run_reference_rescue(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Protect one flagship account before diligence or IPO pressure compounds."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < BALANCE.support_program_reference_rescue_cost:
        raise ValueError("Not enough cash to run a reference rescue this turn.")
    if (
        account.open_tickets <= 0
        and account.sla_breach_risk <= 0
        and account.ticket_queue_age <= 0
        and account.support_load <= 18
        and account.invoice_risk <= 0
        and account.failed_payment_risk <= 0
        and account.renewal_health >= 74
        and account.satisfaction >= 74
    ):
        raise ValueError("That account does not need a reference rescue right now.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_reference_rescue_cost
    )
    lane = classify_account_support_lane(account)
    lane_focus = SupportLaneFocus.ENTERPRISE if lane is SupportLaneFocus.BALANCED else lane
    state.support_program.lane_focus = lane_focus
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - BALANCE.support_program_reference_rescue_backlog_relief,
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - BALANCE.support_program_reference_rescue_escalation_relief,
    )
    account.open_tickets = max(
        0,
        account.open_tickets - BALANCE.support_program_reference_rescue_ticket_relief,
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk - BALANCE.support_program_reference_rescue_sla_relief
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age - BALANCE.support_program_reference_rescue_queue_age_relief,
    )
    account.support_load = clamp_int(
        account.support_load - BALANCE.support_program_reference_rescue_support_load_relief
    )
    account.renewal_health = clamp_int(
        account.renewal_health + BALANCE.support_program_reference_rescue_renewal_health_gain
    )
    account.satisfaction = clamp_int(
        account.satisfaction + BALANCE.support_program_reference_rescue_satisfaction_gain
    )
    account.churn_risk = clamp_int(
        account.churn_risk - BALANCE.support_program_reference_rescue_churn_relief
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    if account.support_tier is SupportTier.STANDARD:
        account.support_tier = SupportTier.PRIORITY
    elif account.support_tier is SupportTier.PRIORITY:
        account.support_tier = SupportTier.WHITE_GLOVE

    if lane is SupportLaneFocus.ONBOARDING:
        account.onboarding_health = clamp_int(
            account.onboarding_health
            + BALANCE.support_program_reference_rescue_onboarding_health_gain
        )
    elif lane is SupportLaneFocus.BILLING:
        account.invoice_risk = clamp_int(
            account.invoice_risk - BALANCE.support_program_reference_rescue_invoice_relief
        )
        account.failed_payment_risk = clamp_int(
            account.failed_payment_risk - BALANCE.support_program_reference_rescue_payment_relief
        )
    _apply_lane_program_relief(
        state.support_program,
        lane_focus,
        BALANCE.support_program_reference_rescue_lane_relief,
    )

    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - BALANCE.support_program_reference_rescue_board_pressure_relief
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + BALANCE.support_program_reference_rescue_board_confidence_gain
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - BALANCE.support_program_reference_rescue_investor_pressure_relief
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a reference rescue for {account.name}. "
            f"Cash -{BALANCE.support_program_reference_rescue_cost}, "
            f"SLA risk now {account.sla_breach_risk}."
        )
    )


def run_white_glove_backstop(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run a higher-cost premium recovery pass for one flagship high-touch account."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < BALANCE.support_program_white_glove_backstop_cost:
        raise ValueError("Not enough cash to run a white-glove backstop this turn.")
    if (
        account.support_tier is SupportTier.STANDARD
        and account.contract_value < Decimal("2200.00")
        and account.segment is not MarketSegment.ENTERPRISE
    ):
        raise ValueError("That account is not exposed enough for a white-glove backstop.")
    if (
        account.open_tickets <= 1
        and account.sla_breach_risk <= 10
        and account.ticket_queue_age <= 0
        and account.support_load <= 18
        and account.renewal_health >= 76
        and account.satisfaction >= 78
    ):
        raise ValueError("That account does not need a white-glove backstop right now.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_white_glove_backstop_cost
    )
    state.support_program.lane_focus = SupportLaneFocus.ENTERPRISE
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - BALANCE.support_program_white_glove_backstop_backlog_relief,
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - BALANCE.support_program_white_glove_backstop_escalation_relief,
    )
    account.open_tickets = max(
        0,
        account.open_tickets - BALANCE.support_program_white_glove_backstop_ticket_relief,
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk - BALANCE.support_program_white_glove_backstop_sla_relief
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age - BALANCE.support_program_white_glove_backstop_queue_age_relief,
    )
    account.support_load = clamp_int(
        account.support_load - BALANCE.support_program_white_glove_backstop_support_load_relief
    )
    account.renewal_health = clamp_int(
        account.renewal_health + BALANCE.support_program_white_glove_backstop_renewal_health_gain
    )
    account.satisfaction = clamp_int(
        account.satisfaction + BALANCE.support_program_white_glove_backstop_satisfaction_gain
    )
    account.churn_risk = clamp_int(
        account.churn_risk - BALANCE.support_program_white_glove_backstop_churn_relief
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ENTERPRISE,
        BALANCE.support_program_white_glove_backstop_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - BALANCE.support_program_white_glove_backstop_board_pressure_relief
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + BALANCE.support_program_white_glove_backstop_board_confidence_gain
    )
    state.company.reputation = clamp_int(
        state.company.reputation + BALANCE.support_program_white_glove_backstop_reputation_gain
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a white-glove backstop for {account.name}. "
            f"Cash -{BALANCE.support_program_white_glove_backstop_cost}, "
            f"renewal health now {account.renewal_health}."
        )
    )


def run_white_glove_renewal_guard(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run a renewal-first premium recovery pass for one flagship white-glove account."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < BALANCE.support_program_white_glove_renewal_guard_cost:
        raise ValueError("Not enough cash to run a white-glove renewal guard this turn.")
    if (
        account.support_tier is SupportTier.STANDARD
        and account.contract_value < Decimal("2400.00")
        and account.segment is not MarketSegment.ENTERPRISE
    ):
        raise ValueError("That account is not exposed enough for a white-glove renewal guard.")
    if (
        account.renewal_health >= 78
        and account.churn_risk <= 16
        and account.invoice_risk <= 8
        and account.failed_payment_risk <= 8
        and account.support_load <= 18
        and account.sla_breach_risk <= 12
    ):
        raise ValueError("That account does not need a white-glove renewal guard right now.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_white_glove_renewal_guard_cost
    )
    state.support_program.lane_focus = SupportLaneFocus.ENTERPRISE
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - BALANCE.support_program_white_glove_renewal_guard_backlog_relief,
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - BALANCE.support_program_white_glove_renewal_guard_escalation_relief,
    )
    account.open_tickets = max(
        0,
        account.open_tickets - BALANCE.support_program_white_glove_renewal_guard_ticket_relief,
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk - BALANCE.support_program_white_glove_renewal_guard_sla_relief
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - BALANCE.support_program_white_glove_renewal_guard_queue_age_relief,
    )
    account.support_load = clamp_int(
        account.support_load - BALANCE.support_program_white_glove_renewal_guard_support_load_relief
    )
    account.invoice_risk = clamp_int(
        account.invoice_risk - BALANCE.support_program_white_glove_renewal_guard_invoice_relief
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk
        - BALANCE.support_program_white_glove_renewal_guard_payment_relief
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + BALANCE.support_program_white_glove_renewal_guard_renewal_health_gain
    )
    account.satisfaction = clamp_int(
        account.satisfaction + BALANCE.support_program_white_glove_renewal_guard_satisfaction_gain
    )
    account.churn_risk = clamp_int(
        account.churn_risk - BALANCE.support_program_white_glove_renewal_guard_churn_relief
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ENTERPRISE,
        BALANCE.support_program_white_glove_renewal_guard_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - BALANCE.support_program_white_glove_renewal_guard_board_pressure_relief
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + BALANCE.support_program_white_glove_renewal_guard_board_confidence_gain
    )
    state.company.reputation = clamp_int(
        state.company.reputation + BALANCE.support_program_white_glove_renewal_guard_reputation_gain
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a white-glove renewal guard for {account.name}. "
            f"Cash -{BALANCE.support_program_white_glove_renewal_guard_cost}, "
            f"renewal health now {account.renewal_health}."
        )
    )


def run_white_glove_reference_ring(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Rebuild one premium reference account before white-glove fragility leaks into the path."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < BALANCE.support_program_white_glove_reference_ring_cost:
        raise ValueError("Not enough cash to run a white-glove reference ring this turn.")
    if (
        account.support_tier is SupportTier.STANDARD
        and account.contract_value < Decimal("2600.00")
        and account.segment is not MarketSegment.ENTERPRISE
    ):
        raise ValueError("That account is not exposed enough for a white-glove reference ring.")
    if (
        account.open_tickets <= 0
        and account.sla_breach_risk <= 10
        and account.ticket_queue_age <= 0
        and account.support_load <= 16
        and account.renewal_health >= 80
        and account.satisfaction >= 80
    ):
        raise ValueError("That account does not need a white-glove reference ring right now.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_white_glove_reference_ring_cost
    )
    state.support_program.lane_focus = SupportLaneFocus.ENTERPRISE
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - BALANCE.support_program_white_glove_reference_ring_backlog_relief,
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - BALANCE.support_program_white_glove_reference_ring_escalation_relief,
    )
    account.open_tickets = max(
        0,
        account.open_tickets - BALANCE.support_program_white_glove_reference_ring_ticket_relief,
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk - BALANCE.support_program_white_glove_reference_ring_sla_relief
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - BALANCE.support_program_white_glove_reference_ring_queue_age_relief,
    )
    account.support_load = clamp_int(
        account.support_load
        - BALANCE.support_program_white_glove_reference_ring_support_load_relief
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + BALANCE.support_program_white_glove_reference_ring_onboarding_health_gain
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + BALANCE.support_program_white_glove_reference_ring_renewal_health_gain
    )
    account.satisfaction = clamp_int(
        account.satisfaction + BALANCE.support_program_white_glove_reference_ring_satisfaction_gain
    )
    account.expansion_potential = clamp_int(
        account.expansion_potential
        + BALANCE.support_program_white_glove_reference_ring_expansion_gain
    )
    account.churn_risk = clamp_int(
        account.churn_risk - BALANCE.support_program_white_glove_reference_ring_churn_relief
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ENTERPRISE,
        BALANCE.support_program_white_glove_reference_ring_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - BALANCE.support_program_white_glove_reference_ring_board_pressure_relief
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + BALANCE.support_program_white_glove_reference_ring_board_confidence_gain
    )
    state.finance.board_score = clamp_int(
        state.finance.board_score
        + BALANCE.support_program_white_glove_reference_ring_board_score_gain
    )
    state.company.reputation = clamp_int(
        state.company.reputation
        + BALANCE.support_program_white_glove_reference_ring_reputation_gain
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a white-glove reference ring for {account.name}. "
            f"Cash -{BALANCE.support_program_white_glove_reference_ring_cost}, "
            f"renewal health now {account.renewal_health}."
        )
    )


def run_white_glove_reference_committee(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run a final flagship premium-account recovery pass before the path hardens."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < BALANCE.support_program_white_glove_reference_committee_cost:
        raise ValueError("Not enough cash to run a white-glove reference committee this turn.")
    if (
        account.support_tier is SupportTier.STANDARD
        and account.contract_value < Decimal("2800.00")
        and account.segment is not MarketSegment.ENTERPRISE
    ):
        raise ValueError(
            "That account is not exposed enough for a white-glove reference committee."
        )
    if (
        account.open_tickets <= 1
        and account.sla_breach_risk <= 10
        and account.ticket_queue_age <= 0
        and account.support_load <= 16
        and account.renewal_health >= 82
        and account.satisfaction >= 82
        and account.churn_risk <= 14
    ):
        raise ValueError("That account does not need a white-glove reference committee right now.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_white_glove_reference_committee_cost
    )
    state.support_program.lane_focus = SupportLaneFocus.ENTERPRISE
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - BALANCE.support_program_white_glove_reference_committee_backlog_relief,
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - BALANCE.support_program_white_glove_reference_committee_escalation_relief,
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - BALANCE.support_program_white_glove_reference_committee_ticket_relief,
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk - BALANCE.support_program_white_glove_reference_committee_sla_relief
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - BALANCE.support_program_white_glove_reference_committee_queue_age_relief,
    )
    account.support_load = clamp_int(
        account.support_load
        - BALANCE.support_program_white_glove_reference_committee_support_load_relief
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + BALANCE.support_program_white_glove_reference_committee_renewal_health_gain
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + BALANCE.support_program_white_glove_reference_committee_satisfaction_gain
    )
    account.expansion_potential = clamp_int(
        account.expansion_potential
        + BALANCE.support_program_white_glove_reference_committee_expansion_gain
    )
    account.churn_risk = clamp_int(
        account.churn_risk - BALANCE.support_program_white_glove_reference_committee_churn_relief
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ENTERPRISE,
        BALANCE.support_program_white_glove_reference_committee_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - BALANCE.support_program_white_glove_reference_committee_board_pressure_relief
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + BALANCE.support_program_white_glove_reference_committee_board_confidence_gain
    )
    state.finance.board_score = clamp_int(
        state.finance.board_score
        + BALANCE.support_program_white_glove_reference_committee_board_score_gain
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - BALANCE.support_program_white_glove_reference_committee_investor_pressure_relief
    )
    state.company.reputation = clamp_int(
        state.company.reputation
        + BALANCE.support_program_white_glove_reference_committee_reputation_gain
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a white-glove reference committee for {account.name}. "
            f"Cash -{BALANCE.support_program_white_glove_reference_committee_cost}, "
            f"renewal health now {account.renewal_health}."
        )
    )


def run_white_glove_escalation_cell(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the deepest premium follow-up pass for a flagship high-touch account."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    cost = quantize_money(
        BALANCE.support_program_white_glove_backstop_cost
        + BALANCE.support_program_white_glove_reference_committee_cost
    )
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < cost:
        raise ValueError("Not enough cash to run a white-glove escalation cell this turn.")
    if (
        account.support_tier is SupportTier.STANDARD
        and account.contract_value < Decimal("3400.00")
        and account.segment is not MarketSegment.ENTERPRISE
    ):
        raise ValueError("That account is not exposed enough for a white-glove escalation cell.")
    if (
        account.open_tickets <= 1
        and account.sla_breach_risk <= 10
        and account.ticket_queue_age <= 0
        and account.support_load <= 16
        and account.renewal_health >= 84
        and account.satisfaction >= 84
        and account.churn_risk <= 12
    ):
        raise ValueError("That account does not need a white-glove escalation cell right now.")

    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - cost)
    state.support_program.lane_focus = SupportLaneFocus.ENTERPRISE
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_white_glove_backstop_backlog_relief
            + BALANCE.support_program_white_glove_reference_committee_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_white_glove_backstop_escalation_relief
            + BALANCE.support_program_white_glove_reference_committee_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_white_glove_backstop_ticket_relief
            + BALANCE.support_program_white_glove_reference_committee_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_white_glove_backstop_sla_relief
            + BALANCE.support_program_white_glove_reference_committee_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_white_glove_backstop_queue_age_relief
            + BALANCE.support_program_white_glove_reference_committee_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_white_glove_backstop_support_load_relief
            + BALANCE.support_program_white_glove_reference_committee_support_load_relief
        )
    )
    account.invoice_risk = clamp_int(
        account.invoice_risk - BALANCE.support_program_white_glove_renewal_guard_invoice_relief
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk
        - BALANCE.support_program_white_glove_renewal_guard_payment_relief
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_white_glove_backstop_renewal_health_gain
            + BALANCE.support_program_white_glove_reference_committee_renewal_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_white_glove_backstop_satisfaction_gain
            + BALANCE.support_program_white_glove_reference_committee_satisfaction_gain
        )
    )
    account.expansion_potential = clamp_int(
        account.expansion_potential
        + BALANCE.support_program_white_glove_reference_committee_expansion_gain
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_white_glove_backstop_churn_relief
            + BALANCE.support_program_white_glove_reference_committee_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 2)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ENTERPRISE,
        BALANCE.support_program_white_glove_backstop_lane_relief
        + BALANCE.support_program_white_glove_reference_committee_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_white_glove_backstop_board_pressure_relief
            + BALANCE.support_program_white_glove_reference_committee_board_pressure_relief
        )
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_white_glove_backstop_board_confidence_gain
            + BALANCE.support_program_white_glove_reference_committee_board_confidence_gain
        )
    )
    state.finance.board_score = clamp_int(
        state.finance.board_score
        + BALANCE.support_program_white_glove_reference_committee_board_score_gain
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - BALANCE.support_program_white_glove_reference_committee_investor_pressure_relief
    )
    state.company.reputation = clamp_int(
        state.company.reputation
        + (
            BALANCE.support_program_white_glove_backstop_reputation_gain
            + BALANCE.support_program_white_glove_reference_committee_reputation_gain
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a white-glove escalation cell for {account.name}. Cash -{cost}, "
            f"renewal health now {account.renewal_health}."
        )
    )


def run_white_glove_reference_bureau(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the deepest premium reference follow-up before exit pressure hardens."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    cost = quantize_money(
        BALANCE.support_program_white_glove_backstop_cost
        + BALANCE.support_program_white_glove_reference_committee_cost
        + BALANCE.support_program_enterprise_reference_cycle_cost
    )
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < cost:
        raise ValueError("Not enough cash to run a white-glove reference bureau this turn.")
    if (
        account.support_tier is SupportTier.STANDARD
        and account.contract_value < Decimal("3600.00")
        and account.segment is not MarketSegment.ENTERPRISE
    ):
        raise ValueError("That account is not exposed enough for a white-glove reference bureau.")
    if (
        account.open_tickets <= 1
        and account.sla_breach_risk <= 10
        and account.ticket_queue_age <= 0
        and account.support_load <= 14
        and account.renewal_health >= 86
        and account.satisfaction >= 86
        and account.churn_risk <= 10
    ):
        raise ValueError("That account does not need a white-glove reference bureau right now.")

    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - cost)
    state.support_program.lane_focus = SupportLaneFocus.ENTERPRISE
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_white_glove_backstop_backlog_relief
            + BALANCE.support_program_white_glove_reference_committee_backlog_relief
            + BALANCE.support_program_enterprise_reference_cycle_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_white_glove_backstop_escalation_relief
            + BALANCE.support_program_white_glove_reference_committee_escalation_relief
            + BALANCE.support_program_enterprise_reference_cycle_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_white_glove_backstop_ticket_relief
            + BALANCE.support_program_white_glove_reference_committee_ticket_relief
            + BALANCE.support_program_enterprise_reference_cycle_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_white_glove_backstop_sla_relief
            + BALANCE.support_program_white_glove_reference_committee_sla_relief
            + BALANCE.support_program_enterprise_reference_cycle_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_white_glove_backstop_queue_age_relief
            + BALANCE.support_program_white_glove_reference_committee_queue_age_relief
            + BALANCE.support_program_enterprise_reference_cycle_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_white_glove_backstop_support_load_relief
            + BALANCE.support_program_white_glove_reference_committee_support_load_relief
            + BALANCE.support_program_enterprise_reference_cycle_support_load_relief
        )
    )
    account.invoice_risk = clamp_int(
        account.invoice_risk - BALANCE.support_program_white_glove_renewal_guard_invoice_relief
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk
        - BALANCE.support_program_white_glove_renewal_guard_payment_relief
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + BALANCE.support_program_enterprise_reference_cycle_onboarding_health_gain
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_white_glove_backstop_renewal_health_gain
            + BALANCE.support_program_white_glove_reference_committee_renewal_health_gain
            + BALANCE.support_program_enterprise_reference_cycle_renewal_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_white_glove_backstop_satisfaction_gain
            + BALANCE.support_program_white_glove_reference_committee_satisfaction_gain
            + BALANCE.support_program_enterprise_reference_cycle_satisfaction_gain
        )
    )
    account.expansion_potential = clamp_int(
        account.expansion_potential
        + (
            BALANCE.support_program_white_glove_reference_committee_expansion_gain
            + BALANCE.support_program_enterprise_reference_cycle_expansion_gain
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_white_glove_backstop_churn_relief
            + BALANCE.support_program_white_glove_reference_committee_churn_relief
            + BALANCE.support_program_enterprise_reference_cycle_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 2)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ENTERPRISE,
        BALANCE.support_program_white_glove_backstop_lane_relief
        + BALANCE.support_program_white_glove_reference_committee_lane_relief
        + BALANCE.support_program_enterprise_reference_cycle_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_white_glove_backstop_board_pressure_relief
            + BALANCE.support_program_white_glove_reference_committee_board_pressure_relief
            + BALANCE.support_program_enterprise_reference_cycle_board_pressure_relief
        )
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_white_glove_backstop_board_confidence_gain
            + BALANCE.support_program_white_glove_reference_committee_board_confidence_gain
            + BALANCE.support_program_enterprise_reference_cycle_board_confidence_gain
        )
    )
    state.finance.board_score = clamp_int(
        state.finance.board_score
        + (
            BALANCE.support_program_white_glove_reference_committee_board_score_gain
            + BALANCE.support_program_enterprise_reference_cycle_score_gain
        )
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - BALANCE.support_program_white_glove_reference_committee_investor_pressure_relief
    )
    state.company.reputation = clamp_int(
        state.company.reputation
        + (
            BALANCE.support_program_white_glove_backstop_reputation_gain
            + BALANCE.support_program_white_glove_reference_committee_reputation_gain
            + BALANCE.support_program_enterprise_reference_cycle_reputation_gain
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a white-glove reference bureau for {account.name}. Cash -{cost}, "
            f"renewal health now {account.renewal_health}."
        )
    )


def run_white_glove_reference_exchange(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the final premium proof loop when one flagship account anchors exit trust."""

    base_cost = quantize_money(
        BALANCE.support_program_white_glove_backstop_cost
        + BALANCE.support_program_white_glove_reference_committee_cost
        + BALANCE.support_program_enterprise_reference_cycle_cost
    )
    extra_cost = quantize_money(
        BALANCE.support_program_white_glove_reference_committee_cost
        + BALANCE.support_program_enterprise_reference_cycle_cost
    )
    total_cost = quantize_money(base_cost + extra_cost)
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to run a white-glove reference exchange this turn.")

    run_white_glove_reference_bureau(state, account_id)
    account = _get_account_by_id(state.customer_accounts, account_id)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_white_glove_reference_committee_backlog_relief
            + BALANCE.support_program_enterprise_reference_cycle_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_white_glove_reference_committee_escalation_relief
            + BALANCE.support_program_enterprise_reference_cycle_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_white_glove_reference_committee_ticket_relief
            + BALANCE.support_program_enterprise_reference_cycle_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_white_glove_reference_committee_sla_relief
            + BALANCE.support_program_enterprise_reference_cycle_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_white_glove_reference_committee_queue_age_relief
            + BALANCE.support_program_enterprise_reference_cycle_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_white_glove_reference_committee_support_load_relief
            + BALANCE.support_program_enterprise_reference_cycle_support_load_relief
        )
    )
    account.invoice_risk = clamp_int(
        account.invoice_risk - BALANCE.support_program_white_glove_renewal_guard_invoice_relief
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk
        - BALANCE.support_program_white_glove_renewal_guard_payment_relief
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + BALANCE.support_program_enterprise_reference_cycle_onboarding_health_gain
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_white_glove_reference_committee_renewal_health_gain
            + BALANCE.support_program_enterprise_reference_cycle_renewal_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_white_glove_reference_committee_satisfaction_gain
            + BALANCE.support_program_enterprise_reference_cycle_satisfaction_gain
        )
    )
    account.expansion_potential = clamp_int(
        account.expansion_potential
        + (
            BALANCE.support_program_white_glove_reference_committee_expansion_gain
            + BALANCE.support_program_enterprise_reference_cycle_expansion_gain
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_white_glove_reference_committee_churn_relief
            + BALANCE.support_program_enterprise_reference_cycle_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ENTERPRISE,
        BALANCE.support_program_white_glove_reference_committee_lane_relief
        + BALANCE.support_program_enterprise_reference_cycle_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_white_glove_reference_committee_board_pressure_relief
            + BALANCE.support_program_enterprise_reference_cycle_board_pressure_relief
        )
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_white_glove_reference_committee_board_confidence_gain
            + BALANCE.support_program_enterprise_reference_cycle_board_confidence_gain
        )
    )
    state.finance.board_score = clamp_int(
        state.finance.board_score
        + (
            BALANCE.support_program_white_glove_reference_committee_board_score_gain
            + BALANCE.support_program_enterprise_reference_cycle_score_gain
        )
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - BALANCE.support_program_white_glove_reference_committee_investor_pressure_relief
    )
    state.company.reputation = clamp_int(
        state.company.reputation
        + (
            BALANCE.support_program_white_glove_reference_committee_reputation_gain
            + BALANCE.support_program_enterprise_reference_cycle_reputation_gain
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a white-glove reference exchange for {account.name}. Cash -{total_cost}, "
            f"renewal health now {account.renewal_health}."
        )
    )


def run_enterprise_reference_cycle(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Deepen a flagship enterprise reference relationship before IPO or diligence hardens."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < BALANCE.support_program_enterprise_reference_cycle_cost:
        raise ValueError("Not enough cash to run an enterprise reference cycle this turn.")
    if (
        account.segment is not MarketSegment.ENTERPRISE
        and account.support_tier is SupportTier.STANDARD
        and account.contract_value < Decimal("2200.00")
    ):
        raise ValueError("That account is not enterprise-exposed enough for a reference cycle.")
    if (
        account.open_tickets <= 0
        and account.sla_breach_risk <= 10
        and account.ticket_queue_age <= 0
        and account.support_load <= 16
        and account.renewal_health >= 78
        and account.satisfaction >= 78
    ):
        raise ValueError("That account does not need an enterprise reference cycle right now.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_enterprise_reference_cycle_cost
    )
    state.support_program.lane_focus = SupportLaneFocus.ENTERPRISE
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - BALANCE.support_program_enterprise_reference_cycle_backlog_relief,
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - BALANCE.support_program_enterprise_reference_cycle_escalation_relief,
    )
    account.open_tickets = max(
        0,
        account.open_tickets - BALANCE.support_program_enterprise_reference_cycle_ticket_relief,
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk - BALANCE.support_program_enterprise_reference_cycle_sla_relief
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - BALANCE.support_program_enterprise_reference_cycle_queue_age_relief,
    )
    account.support_load = clamp_int(
        account.support_load
        - BALANCE.support_program_enterprise_reference_cycle_support_load_relief
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + BALANCE.support_program_enterprise_reference_cycle_onboarding_health_gain
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + BALANCE.support_program_enterprise_reference_cycle_renewal_health_gain
    )
    account.satisfaction = clamp_int(
        account.satisfaction + BALANCE.support_program_enterprise_reference_cycle_satisfaction_gain
    )
    account.expansion_potential = clamp_int(
        account.expansion_potential
        + BALANCE.support_program_enterprise_reference_cycle_expansion_gain
    )
    account.churn_risk = clamp_int(
        account.churn_risk - BALANCE.support_program_enterprise_reference_cycle_churn_relief
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    if account.support_tier is SupportTier.STANDARD:
        account.support_tier = SupportTier.PRIORITY
    else:
        account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ENTERPRISE,
        BALANCE.support_program_enterprise_reference_cycle_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - BALANCE.support_program_enterprise_reference_cycle_board_pressure_relief
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + BALANCE.support_program_enterprise_reference_cycle_board_confidence_gain
    )
    state.finance.board_score = clamp_int(
        state.finance.board_score + BALANCE.support_program_enterprise_reference_cycle_score_gain
    )
    state.company.reputation = clamp_int(
        state.company.reputation
        + BALANCE.support_program_enterprise_reference_cycle_reputation_gain
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran an enterprise reference cycle for {account.name}. "
            f"Cash -{BALANCE.support_program_enterprise_reference_cycle_cost}, "
            f"renewal health now {account.renewal_health}."
        )
    )


def run_enterprise_renewal_cabinet(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Stabilize one exposed enterprise renewal before IPO or diligence pressure compounds."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < BALANCE.support_program_enterprise_renewal_cabinet_cost:
        raise ValueError("Not enough cash to run an enterprise renewal cabinet this turn.")
    if (
        account.segment is not MarketSegment.ENTERPRISE
        and account.support_tier is SupportTier.STANDARD
        and account.contract_value < Decimal("2400.00")
    ):
        raise ValueError("That account is not exposed enough for an enterprise renewal cabinet.")
    if (
        account.renewal_health >= 80
        and account.churn_risk <= 16
        and account.support_load <= 16
        and account.sla_breach_risk <= 10
        and account.open_tickets <= 1
    ):
        raise ValueError("That account does not need an enterprise renewal cabinet right now.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_enterprise_renewal_cabinet_cost
    )
    state.support_program.lane_focus = SupportLaneFocus.ENTERPRISE
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - BALANCE.support_program_enterprise_renewal_cabinet_backlog_relief,
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - BALANCE.support_program_enterprise_renewal_cabinet_escalation_relief,
    )
    account.open_tickets = max(
        0,
        account.open_tickets - BALANCE.support_program_enterprise_renewal_cabinet_ticket_relief,
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk - BALANCE.support_program_enterprise_renewal_cabinet_sla_relief
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - BALANCE.support_program_enterprise_renewal_cabinet_queue_age_relief,
    )
    account.support_load = clamp_int(
        account.support_load
        - BALANCE.support_program_enterprise_renewal_cabinet_support_load_relief
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + BALANCE.support_program_enterprise_renewal_cabinet_onboarding_health_gain
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + BALANCE.support_program_enterprise_renewal_cabinet_renewal_health_gain
    )
    account.satisfaction = clamp_int(
        account.satisfaction + BALANCE.support_program_enterprise_renewal_cabinet_satisfaction_gain
    )
    account.expansion_potential = clamp_int(
        account.expansion_potential
        + BALANCE.support_program_enterprise_renewal_cabinet_expansion_gain
    )
    account.churn_risk = clamp_int(
        account.churn_risk - BALANCE.support_program_enterprise_renewal_cabinet_churn_relief
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    if account.support_tier is SupportTier.STANDARD:
        account.support_tier = SupportTier.PRIORITY
    else:
        account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ENTERPRISE,
        BALANCE.support_program_enterprise_renewal_cabinet_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - BALANCE.support_program_enterprise_renewal_cabinet_board_pressure_relief
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + BALANCE.support_program_enterprise_renewal_cabinet_board_confidence_gain
    )
    state.finance.board_score = clamp_int(
        state.finance.board_score
        + BALANCE.support_program_enterprise_renewal_cabinet_board_score_gain
    )
    state.company.reputation = clamp_int(
        state.company.reputation
        + BALANCE.support_program_enterprise_renewal_cabinet_reputation_gain
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran an enterprise renewal cabinet for {account.name}. "
            f"Cash -{BALANCE.support_program_enterprise_renewal_cabinet_cost}, "
            f"renewal health now {account.renewal_health}."
        )
    )


def run_enterprise_commitment_board(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the deepest enterprise follow-up when renewal, reference, and board heat align."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    cost = quantize_money(
        BALANCE.support_program_enterprise_reference_cycle_cost
        + BALANCE.support_program_enterprise_renewal_cabinet_cost
        + BALANCE.support_program_white_glove_reference_committee_cost
    )
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < cost:
        raise ValueError("Not enough cash to run an enterprise commitment board this turn.")
    if (
        account.segment is not MarketSegment.ENTERPRISE
        and account.support_tier is SupportTier.STANDARD
        and account.contract_value < Decimal("2800.00")
    ):
        raise ValueError("That account is not exposed enough for an enterprise commitment board.")
    if (
        account.renewal_health >= 84
        and account.churn_risk <= 14
        and account.support_load <= 14
        and account.sla_breach_risk <= 10
        and account.open_tickets <= 1
        and account.ticket_queue_age <= 0
    ):
        raise ValueError("That account does not need an enterprise commitment board right now.")

    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - cost)
    state.support_program.lane_focus = SupportLaneFocus.ENTERPRISE
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_enterprise_reference_cycle_backlog_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_backlog_relief
            + BALANCE.support_program_white_glove_reference_committee_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_enterprise_reference_cycle_escalation_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_escalation_relief
            + BALANCE.support_program_white_glove_reference_committee_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_enterprise_reference_cycle_ticket_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_ticket_relief
            + BALANCE.support_program_white_glove_reference_committee_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_enterprise_reference_cycle_sla_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_sla_relief
            + BALANCE.support_program_white_glove_reference_committee_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_enterprise_reference_cycle_queue_age_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_queue_age_relief
            + BALANCE.support_program_white_glove_reference_committee_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_enterprise_reference_cycle_support_load_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_support_load_relief
            + BALANCE.support_program_white_glove_reference_committee_support_load_relief
        )
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + (
            BALANCE.support_program_enterprise_reference_cycle_onboarding_health_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_onboarding_health_gain
        )
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_enterprise_reference_cycle_renewal_health_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_renewal_health_gain
            + BALANCE.support_program_white_glove_reference_committee_renewal_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_enterprise_reference_cycle_satisfaction_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_satisfaction_gain
            + BALANCE.support_program_white_glove_reference_committee_satisfaction_gain
        )
    )
    account.expansion_potential = clamp_int(
        account.expansion_potential
        + (
            BALANCE.support_program_enterprise_reference_cycle_expansion_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_expansion_gain
            + BALANCE.support_program_white_glove_reference_committee_expansion_gain
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_enterprise_reference_cycle_churn_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_churn_relief
            + BALANCE.support_program_white_glove_reference_committee_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 2)
    if account.support_tier is SupportTier.STANDARD:
        account.support_tier = SupportTier.PRIORITY
    else:
        account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ENTERPRISE,
        BALANCE.support_program_enterprise_reference_cycle_lane_relief
        + BALANCE.support_program_enterprise_renewal_cabinet_lane_relief
        + BALANCE.support_program_white_glove_reference_committee_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_enterprise_reference_cycle_board_pressure_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_board_pressure_relief
            + BALANCE.support_program_white_glove_reference_committee_board_pressure_relief
        )
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_enterprise_reference_cycle_board_confidence_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_board_confidence_gain
            + BALANCE.support_program_white_glove_reference_committee_board_confidence_gain
        )
    )
    state.finance.board_score = clamp_int(
        state.finance.board_score
        + (
            BALANCE.support_program_enterprise_reference_cycle_score_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_board_score_gain
            + BALANCE.support_program_white_glove_reference_committee_board_score_gain
        )
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - BALANCE.support_program_white_glove_reference_committee_investor_pressure_relief
    )
    state.company.reputation = clamp_int(
        state.company.reputation
        + (
            BALANCE.support_program_enterprise_reference_cycle_reputation_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_reputation_gain
            + BALANCE.support_program_white_glove_reference_committee_reputation_gain
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran an enterprise commitment board for {account.name}. Cash -{cost}, "
            f"renewal health now {account.renewal_health}."
        )
    )


def run_enterprise_reference_chamber(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the deepest enterprise follow-up.

    Use this when flagship proof and renewal stability both matter.
    """

    account = _get_account_by_id(state.customer_accounts, account_id)
    cost = quantize_money(
        BALANCE.support_program_white_glove_backstop_cost
        + BALANCE.support_program_white_glove_reference_committee_cost
        + BALANCE.support_program_enterprise_reference_cycle_cost
        + BALANCE.support_program_enterprise_renewal_cabinet_cost
    )
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < cost:
        raise ValueError("Not enough cash to run an enterprise reference chamber this turn.")
    if (
        account.segment is not MarketSegment.ENTERPRISE
        and account.support_tier is SupportTier.STANDARD
        and account.contract_value < Decimal("3400.00")
    ):
        raise ValueError("That account is not exposed enough for an enterprise reference chamber.")
    if (
        account.renewal_health >= 88
        and account.churn_risk <= 10
        and account.support_load <= 10
        and account.sla_breach_risk <= 8
        and account.open_tickets <= 1
        and account.ticket_queue_age <= 0
    ):
        raise ValueError("That account does not need an enterprise reference chamber right now.")

    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - cost)
    state.support_program.lane_focus = SupportLaneFocus.ENTERPRISE
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_white_glove_backstop_backlog_relief
            + BALANCE.support_program_white_glove_reference_committee_backlog_relief
            + BALANCE.support_program_enterprise_reference_cycle_backlog_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_white_glove_backstop_escalation_relief
            + BALANCE.support_program_white_glove_reference_committee_escalation_relief
            + BALANCE.support_program_enterprise_reference_cycle_escalation_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_white_glove_backstop_ticket_relief
            + BALANCE.support_program_white_glove_reference_committee_ticket_relief
            + BALANCE.support_program_enterprise_reference_cycle_ticket_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_white_glove_backstop_sla_relief
            + BALANCE.support_program_white_glove_reference_committee_sla_relief
            + BALANCE.support_program_enterprise_reference_cycle_sla_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_white_glove_backstop_queue_age_relief
            + BALANCE.support_program_white_glove_reference_committee_queue_age_relief
            + BALANCE.support_program_enterprise_reference_cycle_queue_age_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_white_glove_backstop_support_load_relief
            + BALANCE.support_program_white_glove_reference_committee_support_load_relief
            + BALANCE.support_program_enterprise_reference_cycle_support_load_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_support_load_relief
        )
    )
    account.invoice_risk = clamp_int(
        account.invoice_risk - BALANCE.support_program_white_glove_renewal_guard_invoice_relief
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk
        - BALANCE.support_program_white_glove_renewal_guard_payment_relief
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + (
            BALANCE.support_program_enterprise_reference_cycle_onboarding_health_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_onboarding_health_gain
        )
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_white_glove_backstop_renewal_health_gain
            + BALANCE.support_program_white_glove_reference_committee_renewal_health_gain
            + BALANCE.support_program_enterprise_reference_cycle_renewal_health_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_renewal_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_white_glove_backstop_satisfaction_gain
            + BALANCE.support_program_white_glove_reference_committee_satisfaction_gain
            + BALANCE.support_program_enterprise_reference_cycle_satisfaction_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_satisfaction_gain
        )
    )
    account.expansion_potential = clamp_int(
        account.expansion_potential
        + (
            BALANCE.support_program_white_glove_reference_committee_expansion_gain
            + BALANCE.support_program_enterprise_reference_cycle_expansion_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_expansion_gain
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_white_glove_backstop_churn_relief
            + BALANCE.support_program_white_glove_reference_committee_churn_relief
            + BALANCE.support_program_enterprise_reference_cycle_churn_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 2)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ENTERPRISE,
        BALANCE.support_program_white_glove_backstop_lane_relief
        + BALANCE.support_program_white_glove_reference_committee_lane_relief
        + BALANCE.support_program_enterprise_reference_cycle_lane_relief
        + BALANCE.support_program_enterprise_renewal_cabinet_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_white_glove_backstop_board_pressure_relief
            + BALANCE.support_program_white_glove_reference_committee_board_pressure_relief
            + BALANCE.support_program_enterprise_reference_cycle_board_pressure_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_board_pressure_relief
        )
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_white_glove_backstop_board_confidence_gain
            + BALANCE.support_program_white_glove_reference_committee_board_confidence_gain
            + BALANCE.support_program_enterprise_reference_cycle_board_confidence_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_board_confidence_gain
        )
    )
    state.finance.board_score = clamp_int(
        state.finance.board_score
        + (
            BALANCE.support_program_white_glove_reference_committee_board_score_gain
            + BALANCE.support_program_enterprise_reference_cycle_score_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_board_score_gain
        )
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - BALANCE.support_program_white_glove_reference_committee_investor_pressure_relief
    )
    state.company.reputation = clamp_int(
        state.company.reputation
        + (
            BALANCE.support_program_white_glove_backstop_reputation_gain
            + BALANCE.support_program_white_glove_reference_committee_reputation_gain
            + BALANCE.support_program_enterprise_reference_cycle_reputation_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_reputation_gain
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran an enterprise reference chamber for {account.name}. Cash -{cost}, "
            f"renewal health now {account.renewal_health}."
        )
    )


def run_enterprise_reference_forum(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the hardest enterprise follow-up when one account now carries the exit proof burden."""

    base_cost = quantize_money(
        BALANCE.support_program_white_glove_backstop_cost
        + BALANCE.support_program_white_glove_reference_committee_cost
        + BALANCE.support_program_enterprise_reference_cycle_cost
        + BALANCE.support_program_enterprise_renewal_cabinet_cost
    )
    extra_cost = quantize_money(
        BALANCE.support_program_white_glove_reference_committee_cost
        + BALANCE.support_program_enterprise_reference_cycle_cost
    )
    total_cost = quantize_money(base_cost + extra_cost)
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to run an enterprise reference forum this turn.")

    run_enterprise_reference_chamber(state, account_id)
    account = _get_account_by_id(state.customer_accounts, account_id)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_white_glove_reference_committee_backlog_relief
            + BALANCE.support_program_enterprise_reference_cycle_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_white_glove_reference_committee_escalation_relief
            + BALANCE.support_program_enterprise_reference_cycle_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_white_glove_reference_committee_ticket_relief
            + BALANCE.support_program_enterprise_reference_cycle_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_white_glove_reference_committee_sla_relief
            + BALANCE.support_program_enterprise_reference_cycle_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_white_glove_reference_committee_queue_age_relief
            + BALANCE.support_program_enterprise_reference_cycle_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_white_glove_reference_committee_support_load_relief
            + BALANCE.support_program_enterprise_reference_cycle_support_load_relief
        )
    )
    account.invoice_risk = clamp_int(
        account.invoice_risk - BALANCE.support_program_white_glove_renewal_guard_invoice_relief
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk
        - BALANCE.support_program_white_glove_renewal_guard_payment_relief
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + BALANCE.support_program_enterprise_reference_cycle_onboarding_health_gain
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_white_glove_reference_committee_renewal_health_gain
            + BALANCE.support_program_enterprise_reference_cycle_renewal_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_white_glove_reference_committee_satisfaction_gain
            + BALANCE.support_program_enterprise_reference_cycle_satisfaction_gain
        )
    )
    account.expansion_potential = clamp_int(
        account.expansion_potential
        + (
            BALANCE.support_program_white_glove_reference_committee_expansion_gain
            + BALANCE.support_program_enterprise_reference_cycle_expansion_gain
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_white_glove_reference_committee_churn_relief
            + BALANCE.support_program_enterprise_reference_cycle_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ENTERPRISE,
        BALANCE.support_program_white_glove_reference_committee_lane_relief
        + BALANCE.support_program_enterprise_reference_cycle_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_white_glove_reference_committee_board_pressure_relief
            + BALANCE.support_program_enterprise_reference_cycle_board_pressure_relief
        )
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_white_glove_reference_committee_board_confidence_gain
            + BALANCE.support_program_enterprise_reference_cycle_board_confidence_gain
        )
    )
    state.finance.board_score = clamp_int(
        state.finance.board_score
        + (
            BALANCE.support_program_white_glove_reference_committee_board_score_gain
            + BALANCE.support_program_enterprise_reference_cycle_score_gain
        )
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - BALANCE.support_program_white_glove_reference_committee_investor_pressure_relief
    )
    state.company.reputation = clamp_int(
        state.company.reputation
        + (
            BALANCE.support_program_white_glove_reference_committee_reputation_gain
            + BALANCE.support_program_enterprise_reference_cycle_reputation_gain
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran an enterprise reference forum for {account.name}. Cash -{total_cost}, "
            f"renewal health now {account.renewal_health}."
        )
    )


def run_enterprise_reference_lattice(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the final enterprise proof loop when one account carries terminal trust."""

    base_cost = quantize_money(
        BALANCE.support_program_white_glove_backstop_cost
        + BALANCE.support_program_white_glove_reference_committee_cost
        + BALANCE.support_program_enterprise_reference_cycle_cost
        + BALANCE.support_program_enterprise_renewal_cabinet_cost
    )
    extra_cost = quantize_money(
        BALANCE.support_program_white_glove_reference_committee_cost
        + BALANCE.support_program_enterprise_reference_cycle_cost
        + BALANCE.support_program_enterprise_renewal_cabinet_cost
    )
    total_cost = quantize_money(base_cost + extra_cost)
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to run an enterprise reference lattice this turn.")

    run_enterprise_reference_forum(state, account_id)
    account = _get_account_by_id(state.customer_accounts, account_id)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_white_glove_reference_committee_backlog_relief
            + BALANCE.support_program_enterprise_reference_cycle_backlog_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_white_glove_reference_committee_escalation_relief
            + BALANCE.support_program_enterprise_reference_cycle_escalation_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_white_glove_reference_committee_ticket_relief
            + BALANCE.support_program_enterprise_reference_cycle_ticket_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_white_glove_reference_committee_sla_relief
            + BALANCE.support_program_enterprise_reference_cycle_sla_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_white_glove_reference_committee_queue_age_relief
            + BALANCE.support_program_enterprise_reference_cycle_queue_age_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_white_glove_reference_committee_support_load_relief
            + BALANCE.support_program_enterprise_reference_cycle_support_load_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_support_load_relief
        )
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + BALANCE.support_program_enterprise_reference_cycle_onboarding_health_gain
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_white_glove_reference_committee_renewal_health_gain
            + BALANCE.support_program_enterprise_reference_cycle_renewal_health_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_renewal_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_white_glove_reference_committee_satisfaction_gain
            + BALANCE.support_program_enterprise_reference_cycle_satisfaction_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_satisfaction_gain
        )
    )
    account.expansion_potential = clamp_int(
        account.expansion_potential
        + (
            BALANCE.support_program_white_glove_reference_committee_expansion_gain
            + BALANCE.support_program_enterprise_reference_cycle_expansion_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_expansion_gain
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_white_glove_reference_committee_churn_relief
            + BALANCE.support_program_enterprise_reference_cycle_churn_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ENTERPRISE,
        BALANCE.support_program_white_glove_reference_committee_lane_relief
        + BALANCE.support_program_enterprise_reference_cycle_lane_relief
        + BALANCE.support_program_enterprise_renewal_cabinet_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_white_glove_reference_committee_board_pressure_relief
            + BALANCE.support_program_enterprise_reference_cycle_board_pressure_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_board_pressure_relief
        )
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_white_glove_reference_committee_board_confidence_gain
            + BALANCE.support_program_enterprise_reference_cycle_board_confidence_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_board_confidence_gain
        )
    )
    state.finance.board_score = clamp_int(
        state.finance.board_score
        + (
            BALANCE.support_program_white_glove_reference_committee_board_score_gain
            + BALANCE.support_program_enterprise_reference_cycle_score_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_board_score_gain
        )
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - BALANCE.support_program_white_glove_reference_committee_investor_pressure_relief
    )
    state.company.reputation = clamp_int(
        state.company.reputation
        + (
            BALANCE.support_program_white_glove_reference_committee_reputation_gain
            + BALANCE.support_program_enterprise_reference_cycle_reputation_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_reputation_gain
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran an enterprise reference lattice for {account.name}. Cash -{total_cost}, "
            f"renewal health now {account.renewal_health}."
        )
    )


def run_enterprise_reference_summit(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the last flagship-proof loop when enterprise trust still shapes the exit path."""

    base_cost = quantize_money(
        BALANCE.support_program_white_glove_backstop_cost
        + BALANCE.support_program_white_glove_reference_committee_cost * 2
        + BALANCE.support_program_enterprise_reference_cycle_cost * 2
        + BALANCE.support_program_enterprise_renewal_cabinet_cost
    )
    extra_cost = quantize_money(
        BALANCE.support_program_white_glove_reference_committee_cost
        + BALANCE.support_program_enterprise_reference_cycle_cost
        + BALANCE.support_program_enterprise_renewal_cabinet_cost
    )
    total_cost = quantize_money(base_cost + extra_cost)
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to run an enterprise reference summit this turn.")

    run_enterprise_reference_lattice(state, account_id)
    account = _get_account_by_id(state.customer_accounts, account_id)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_white_glove_reference_committee_backlog_relief
            + BALANCE.support_program_enterprise_reference_cycle_backlog_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_white_glove_reference_committee_escalation_relief
            + BALANCE.support_program_enterprise_reference_cycle_escalation_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_white_glove_reference_committee_ticket_relief
            + BALANCE.support_program_enterprise_reference_cycle_ticket_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_white_glove_reference_committee_sla_relief
            + BALANCE.support_program_enterprise_reference_cycle_sla_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_white_glove_reference_committee_queue_age_relief
            + BALANCE.support_program_enterprise_reference_cycle_queue_age_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_white_glove_reference_committee_support_load_relief
            + BALANCE.support_program_enterprise_reference_cycle_support_load_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_support_load_relief
        )
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + (
            BALANCE.support_program_enterprise_reference_cycle_onboarding_health_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_onboarding_health_gain
        )
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_white_glove_reference_committee_renewal_health_gain
            + BALANCE.support_program_enterprise_reference_cycle_renewal_health_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_renewal_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_white_glove_reference_committee_satisfaction_gain
            + BALANCE.support_program_enterprise_reference_cycle_satisfaction_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_satisfaction_gain
        )
    )
    account.expansion_potential = clamp_int(
        account.expansion_potential
        + (
            BALANCE.support_program_white_glove_reference_committee_expansion_gain
            + BALANCE.support_program_enterprise_reference_cycle_expansion_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_expansion_gain
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_white_glove_reference_committee_churn_relief
            + BALANCE.support_program_enterprise_reference_cycle_churn_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ENTERPRISE,
        BALANCE.support_program_white_glove_reference_committee_lane_relief
        + BALANCE.support_program_enterprise_reference_cycle_lane_relief
        + BALANCE.support_program_enterprise_renewal_cabinet_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_white_glove_reference_committee_board_pressure_relief
            + BALANCE.support_program_enterprise_reference_cycle_board_pressure_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_board_pressure_relief
        )
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_white_glove_reference_committee_board_confidence_gain
            + BALANCE.support_program_enterprise_reference_cycle_board_confidence_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_board_confidence_gain
        )
    )
    state.finance.board_score = clamp_int(
        state.finance.board_score
        + (
            BALANCE.support_program_white_glove_reference_committee_board_score_gain
            + BALANCE.support_program_enterprise_reference_cycle_score_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_board_score_gain
        )
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - BALANCE.support_program_white_glove_reference_committee_investor_pressure_relief
    )
    state.company.reputation = clamp_int(
        state.company.reputation
        + (
            BALANCE.support_program_white_glove_reference_committee_reputation_gain
            + BALANCE.support_program_enterprise_reference_cycle_reputation_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_reputation_gain
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran an enterprise reference summit for {account.name}. Cash -{total_cost}, "
            f"renewal health now {account.renewal_health}."
        )
    )


def run_enterprise_reference_directorate(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the final enterprise proof loop when summit-level trust still is not enough."""

    base_cost = quantize_money(
        BALANCE.support_program_white_glove_backstop_cost
        + BALANCE.support_program_white_glove_reference_committee_cost * 3
        + BALANCE.support_program_enterprise_reference_cycle_cost * 3
        + BALANCE.support_program_enterprise_renewal_cabinet_cost * 2
    )
    extra_cost = quantize_money(
        BALANCE.support_program_white_glove_reference_committee_cost
        + BALANCE.support_program_enterprise_reference_cycle_cost
        + BALANCE.support_program_enterprise_renewal_cabinet_cost
    )
    total_cost = quantize_money(base_cost + extra_cost)
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to run an enterprise reference directorate this turn.")

    run_enterprise_reference_summit(state, account_id)
    account = _get_account_by_id(state.customer_accounts, account_id)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_white_glove_reference_committee_backlog_relief
            + BALANCE.support_program_enterprise_reference_cycle_backlog_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_white_glove_reference_committee_escalation_relief
            + BALANCE.support_program_enterprise_reference_cycle_escalation_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_white_glove_reference_committee_ticket_relief
            + BALANCE.support_program_enterprise_reference_cycle_ticket_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_white_glove_reference_committee_sla_relief
            + BALANCE.support_program_enterprise_reference_cycle_sla_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_white_glove_reference_committee_queue_age_relief
            + BALANCE.support_program_enterprise_reference_cycle_queue_age_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_white_glove_reference_committee_support_load_relief
            + BALANCE.support_program_enterprise_reference_cycle_support_load_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_support_load_relief
        )
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + (
            BALANCE.support_program_enterprise_reference_cycle_onboarding_health_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_onboarding_health_gain
        )
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_white_glove_reference_committee_renewal_health_gain
            + BALANCE.support_program_enterprise_reference_cycle_renewal_health_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_renewal_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_white_glove_reference_committee_satisfaction_gain
            + BALANCE.support_program_enterprise_reference_cycle_satisfaction_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_satisfaction_gain
        )
    )
    account.expansion_potential = clamp_int(
        account.expansion_potential
        + (
            BALANCE.support_program_white_glove_reference_committee_expansion_gain
            + BALANCE.support_program_enterprise_reference_cycle_expansion_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_expansion_gain
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_white_glove_reference_committee_churn_relief
            + BALANCE.support_program_enterprise_reference_cycle_churn_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ENTERPRISE,
        BALANCE.support_program_white_glove_reference_committee_lane_relief
        + BALANCE.support_program_enterprise_reference_cycle_lane_relief
        + BALANCE.support_program_enterprise_renewal_cabinet_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_white_glove_reference_committee_board_pressure_relief
            + BALANCE.support_program_enterprise_reference_cycle_board_pressure_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_board_pressure_relief
        )
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_white_glove_reference_committee_board_confidence_gain
            + BALANCE.support_program_enterprise_reference_cycle_board_confidence_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_board_confidence_gain
        )
    )
    state.finance.board_score = clamp_int(
        state.finance.board_score
        + (
            BALANCE.support_program_white_glove_reference_committee_board_score_gain
            + BALANCE.support_program_enterprise_reference_cycle_score_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_board_score_gain
        )
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - BALANCE.support_program_white_glove_reference_committee_investor_pressure_relief
    )
    state.company.reputation = clamp_int(
        state.company.reputation
        + (
            BALANCE.support_program_white_glove_reference_committee_reputation_gain
            + BALANCE.support_program_enterprise_reference_cycle_reputation_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_reputation_gain
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran an enterprise reference directorate for {account.name}. Cash -{total_cost}, "
            f"renewal health now {account.renewal_health}."
        )
    )


def run_enterprise_reference_secretariat(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the terminal enterprise proof loop when directorate-level control still is not enough."""

    base_cost = quantize_money(
        BALANCE.support_program_white_glove_backstop_cost
        + BALANCE.support_program_white_glove_reference_committee_cost * 4
        + BALANCE.support_program_enterprise_reference_cycle_cost * 4
        + BALANCE.support_program_enterprise_renewal_cabinet_cost * 3
    )
    extra_cost = quantize_money(
        BALANCE.support_program_white_glove_reference_committee_cost
        + BALANCE.support_program_enterprise_reference_cycle_cost
        + BALANCE.support_program_enterprise_renewal_cabinet_cost
    )
    total_cost = quantize_money(base_cost + extra_cost)
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to run an enterprise reference secretariat this turn.")

    run_enterprise_reference_directorate(state, account_id)
    account = _get_account_by_id(state.customer_accounts, account_id)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_white_glove_reference_committee_backlog_relief
            + BALANCE.support_program_enterprise_reference_cycle_backlog_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_white_glove_reference_committee_escalation_relief
            + BALANCE.support_program_enterprise_reference_cycle_escalation_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_white_glove_reference_committee_ticket_relief
            + BALANCE.support_program_enterprise_reference_cycle_ticket_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_white_glove_reference_committee_sla_relief
            + BALANCE.support_program_enterprise_reference_cycle_sla_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_white_glove_reference_committee_queue_age_relief
            + BALANCE.support_program_enterprise_reference_cycle_queue_age_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_white_glove_reference_committee_support_load_relief
            + BALANCE.support_program_enterprise_reference_cycle_support_load_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_support_load_relief
        )
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + (
            BALANCE.support_program_enterprise_reference_cycle_onboarding_health_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_onboarding_health_gain
        )
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_white_glove_reference_committee_renewal_health_gain
            + BALANCE.support_program_enterprise_reference_cycle_renewal_health_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_renewal_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_white_glove_reference_committee_satisfaction_gain
            + BALANCE.support_program_enterprise_reference_cycle_satisfaction_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_satisfaction_gain
        )
    )
    account.expansion_potential = clamp_int(
        account.expansion_potential
        + (
            BALANCE.support_program_white_glove_reference_committee_expansion_gain
            + BALANCE.support_program_enterprise_reference_cycle_expansion_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_expansion_gain
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_white_glove_reference_committee_churn_relief
            + BALANCE.support_program_enterprise_reference_cycle_churn_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ENTERPRISE,
        BALANCE.support_program_white_glove_reference_committee_lane_relief
        + BALANCE.support_program_enterprise_reference_cycle_lane_relief
        + BALANCE.support_program_enterprise_renewal_cabinet_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_white_glove_reference_committee_board_pressure_relief
            + BALANCE.support_program_enterprise_reference_cycle_board_pressure_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_board_pressure_relief
        )
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_white_glove_reference_committee_board_confidence_gain
            + BALANCE.support_program_enterprise_reference_cycle_board_confidence_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_board_confidence_gain
        )
    )
    state.finance.board_score = clamp_int(
        state.finance.board_score
        + (
            BALANCE.support_program_white_glove_reference_committee_board_score_gain
            + BALANCE.support_program_enterprise_reference_cycle_score_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_board_score_gain
        )
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - BALANCE.support_program_white_glove_reference_committee_investor_pressure_relief
    )
    state.company.reputation = clamp_int(
        state.company.reputation
        + (
            BALANCE.support_program_white_glove_reference_committee_reputation_gain
            + BALANCE.support_program_enterprise_reference_cycle_reputation_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_reputation_gain
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran an enterprise reference secretariat for {account.name}. Cash -{total_cost}, "
            f"renewal health now {account.renewal_health}."
        )
    )


def run_enterprise_reference_authority(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the deepest enterprise proof loop after the secretariat tier saturates."""

    base_cost = quantize_money(
        BALANCE.support_program_white_glove_backstop_cost
        + BALANCE.support_program_white_glove_reference_committee_cost * 5
        + BALANCE.support_program_enterprise_reference_cycle_cost * 5
        + BALANCE.support_program_enterprise_renewal_cabinet_cost * 4
    )
    extra_cost = quantize_money(
        BALANCE.support_program_white_glove_reference_committee_cost
        + BALANCE.support_program_enterprise_reference_cycle_cost
        + BALANCE.support_program_enterprise_renewal_cabinet_cost
    )
    total_cost = quantize_money(base_cost + extra_cost)
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to run an enterprise reference authority this turn.")

    run_enterprise_reference_secretariat(state, account_id)
    account = _get_account_by_id(state.customer_accounts, account_id)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_white_glove_reference_committee_backlog_relief
            + BALANCE.support_program_enterprise_reference_cycle_backlog_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_white_glove_reference_committee_escalation_relief
            + BALANCE.support_program_enterprise_reference_cycle_escalation_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_white_glove_reference_committee_ticket_relief
            + BALANCE.support_program_enterprise_reference_cycle_ticket_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_white_glove_reference_committee_sla_relief
            + BALANCE.support_program_enterprise_reference_cycle_sla_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_white_glove_reference_committee_queue_age_relief
            + BALANCE.support_program_enterprise_reference_cycle_queue_age_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_white_glove_reference_committee_support_load_relief
            + BALANCE.support_program_enterprise_reference_cycle_support_load_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_support_load_relief
        )
    )
    account.onboarding_health = clamp_int(
        account.onboarding_health
        + (
            BALANCE.support_program_enterprise_reference_cycle_onboarding_health_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_onboarding_health_gain
        )
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_white_glove_reference_committee_renewal_health_gain
            + BALANCE.support_program_enterprise_reference_cycle_renewal_health_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_renewal_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_white_glove_reference_committee_satisfaction_gain
            + BALANCE.support_program_enterprise_reference_cycle_satisfaction_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_satisfaction_gain
        )
    )
    account.expansion_potential = clamp_int(
        account.expansion_potential
        + (
            BALANCE.support_program_white_glove_reference_committee_expansion_gain
            + BALANCE.support_program_enterprise_reference_cycle_expansion_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_expansion_gain
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_white_glove_reference_committee_churn_relief
            + BALANCE.support_program_enterprise_reference_cycle_churn_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    account.support_tier = SupportTier.WHITE_GLOVE
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.ENTERPRISE,
        BALANCE.support_program_white_glove_reference_committee_lane_relief
        + BALANCE.support_program_enterprise_reference_cycle_lane_relief
        + BALANCE.support_program_enterprise_renewal_cabinet_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_white_glove_reference_committee_board_pressure_relief
            + BALANCE.support_program_enterprise_reference_cycle_board_pressure_relief
            + BALANCE.support_program_enterprise_renewal_cabinet_board_pressure_relief
        )
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_white_glove_reference_committee_board_confidence_gain
            + BALANCE.support_program_enterprise_reference_cycle_board_confidence_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_board_confidence_gain
        )
    )
    state.finance.board_score = clamp_int(
        state.finance.board_score
        + (
            BALANCE.support_program_white_glove_reference_committee_board_score_gain
            + BALANCE.support_program_enterprise_reference_cycle_score_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_board_score_gain
        )
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - BALANCE.support_program_white_glove_reference_committee_investor_pressure_relief
    )
    state.company.reputation = clamp_int(
        state.company.reputation
        + (
            BALANCE.support_program_white_glove_reference_committee_reputation_gain
            + BALANCE.support_program_enterprise_reference_cycle_reputation_gain
            + BALANCE.support_program_enterprise_renewal_cabinet_reputation_gain
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran an enterprise reference authority for {account.name}. Cash -{total_cost}, "
            f"renewal health now {account.renewal_health}."
        )
    )


def run_billing_retention_reset(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Deep-reset one billing-heavy account before payment drag turns into renewal loss."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < BALANCE.support_program_billing_retention_reset_cost:
        raise ValueError("Not enough cash to run a billing retention reset this turn.")
    if (
        classify_account_support_lane(account) is not SupportLaneFocus.BILLING
        and account.invoice_risk <= 10
        and account.failed_payment_risk <= 10
        and account.dunning_steps <= 0
        and account.renewal_health >= 70
    ):
        raise ValueError("That account does not need a billing retention reset right now.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_billing_retention_reset_cost
    )
    state.support_program.lane_focus = SupportLaneFocus.BILLING
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - BALANCE.support_program_billing_retention_reset_backlog_relief,
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - BALANCE.support_program_billing_retention_reset_escalation_relief,
    )
    account.open_tickets = max(
        0,
        account.open_tickets - BALANCE.support_program_billing_retention_reset_ticket_relief,
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk - BALANCE.support_program_billing_retention_reset_sla_relief
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age - BALANCE.support_program_billing_retention_reset_queue_age_relief,
    )
    account.support_load = clamp_int(
        account.support_load - BALANCE.support_program_billing_retention_reset_support_load_relief
    )
    account.invoice_risk = clamp_int(
        account.invoice_risk - BALANCE.support_program_billing_retention_reset_invoice_relief
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk - BALANCE.support_program_billing_retention_reset_payment_relief
    )
    account.dunning_steps = max(
        0,
        account.dunning_steps - BALANCE.support_program_billing_retention_reset_dunning_relief,
    )
    account.renewal_health = clamp_int(
        account.renewal_health + BALANCE.support_program_billing_retention_reset_renewal_health_gain
    )
    account.satisfaction = clamp_int(
        account.satisfaction + BALANCE.support_program_billing_retention_reset_satisfaction_gain
    )
    account.churn_risk = clamp_int(
        account.churn_risk - BALANCE.support_program_billing_retention_reset_churn_relief
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.BILLING,
        BALANCE.support_program_billing_retention_reset_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - BALANCE.support_program_billing_retention_reset_board_pressure_relief
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - BALANCE.support_program_billing_retention_reset_investor_pressure_relief
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + BALANCE.support_program_billing_retention_reset_board_confidence_gain
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a billing retention reset for {account.name}. "
            f"Cash -{BALANCE.support_program_billing_retention_reset_cost}, "
            f"invoice risk now {account.invoice_risk}."
        )
    )


def run_billing_covenant_reset(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Reset a billing-heavy account before payment drag spreads into covenant heat."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < BALANCE.support_program_billing_covenant_reset_cost:
        raise ValueError("Not enough cash to run a billing covenant reset this turn.")
    if (
        classify_account_support_lane(account) is not SupportLaneFocus.BILLING
        and account.invoice_risk <= 12
        and account.failed_payment_risk <= 12
        and account.dunning_steps <= 0
        and account.renewal_health >= 74
        and account.churn_risk <= 16
    ):
        raise ValueError("That account does not need a billing covenant reset right now.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.support_program_billing_covenant_reset_cost
    )
    state.support_program.lane_focus = SupportLaneFocus.BILLING
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - BALANCE.support_program_billing_covenant_reset_backlog_relief,
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - BALANCE.support_program_billing_covenant_reset_escalation_relief,
    )
    account.open_tickets = max(
        0,
        account.open_tickets - BALANCE.support_program_billing_covenant_reset_ticket_relief,
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk - BALANCE.support_program_billing_covenant_reset_sla_relief
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age - BALANCE.support_program_billing_covenant_reset_queue_age_relief,
    )
    account.support_load = clamp_int(
        account.support_load - BALANCE.support_program_billing_covenant_reset_support_load_relief
    )
    account.invoice_risk = clamp_int(
        account.invoice_risk - BALANCE.support_program_billing_covenant_reset_invoice_relief
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk - BALANCE.support_program_billing_covenant_reset_payment_relief
    )
    account.dunning_steps = max(
        0,
        account.dunning_steps - BALANCE.support_program_billing_covenant_reset_dunning_relief,
    )
    account.renewal_health = clamp_int(
        account.renewal_health + BALANCE.support_program_billing_covenant_reset_renewal_health_gain
    )
    account.satisfaction = clamp_int(
        account.satisfaction + BALANCE.support_program_billing_covenant_reset_satisfaction_gain
    )
    account.churn_risk = clamp_int(
        account.churn_risk - BALANCE.support_program_billing_covenant_reset_churn_relief
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.BILLING,
        BALANCE.support_program_billing_covenant_reset_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - BALANCE.support_program_billing_covenant_reset_board_pressure_relief
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - BALANCE.support_program_billing_covenant_reset_investor_pressure_relief
    )
    state.finance.covenant_risk = clamp_int(
        state.finance.covenant_risk - BALANCE.support_program_billing_covenant_reset_covenant_relief
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + BALANCE.support_program_billing_covenant_reset_board_confidence_gain
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a billing covenant reset for {account.name}. "
            f"Cash -{BALANCE.support_program_billing_covenant_reset_cost}, "
            f"invoice risk now {account.invoice_risk}."
        )
    )


def run_billing_dispute_desk(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run a deeper billing follow-up pass before disputes become the capital story."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    cost = quantize_money(
        BALANCE.support_program_billing_retention_reset_cost
        + BALANCE.support_program_billing_covenant_reset_cost
    )
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < cost:
        raise ValueError("Not enough cash to run a billing dispute desk this turn.")
    if (
        classify_account_support_lane(account) is not SupportLaneFocus.BILLING
        and account.invoice_risk <= 14
        and account.failed_payment_risk <= 14
        and account.dunning_steps <= 0
        and account.renewal_health >= 76
        and account.churn_risk <= 16
    ):
        raise ValueError("That account does not need a billing dispute desk right now.")

    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - cost)
    state.support_program.lane_focus = SupportLaneFocus.BILLING
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_billing_retention_reset_backlog_relief
            + BALANCE.support_program_billing_covenant_reset_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_billing_retention_reset_escalation_relief
            + BALANCE.support_program_billing_covenant_reset_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_billing_retention_reset_ticket_relief
            + BALANCE.support_program_billing_covenant_reset_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_billing_retention_reset_sla_relief
            + BALANCE.support_program_billing_covenant_reset_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_billing_retention_reset_queue_age_relief
            + BALANCE.support_program_billing_covenant_reset_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_billing_retention_reset_support_load_relief
            + BALANCE.support_program_billing_covenant_reset_support_load_relief
        )
    )
    account.invoice_risk = clamp_int(
        account.invoice_risk
        - (
            BALANCE.support_program_billing_retention_reset_invoice_relief
            + BALANCE.support_program_billing_covenant_reset_invoice_relief
        )
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk
        - (
            BALANCE.support_program_billing_retention_reset_payment_relief
            + BALANCE.support_program_billing_covenant_reset_payment_relief
        )
    )
    account.dunning_steps = max(
        0,
        account.dunning_steps
        - (
            BALANCE.support_program_billing_retention_reset_dunning_relief
            + BALANCE.support_program_billing_covenant_reset_dunning_relief
        ),
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_billing_retention_reset_renewal_health_gain
            + BALANCE.support_program_billing_covenant_reset_renewal_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_billing_retention_reset_satisfaction_gain
            + BALANCE.support_program_billing_covenant_reset_satisfaction_gain
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_billing_retention_reset_churn_relief
            + BALANCE.support_program_billing_covenant_reset_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.BILLING,
        BALANCE.support_program_billing_retention_reset_lane_relief
        + BALANCE.support_program_billing_covenant_reset_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_billing_retention_reset_board_pressure_relief
            + BALANCE.support_program_billing_covenant_reset_board_pressure_relief
        )
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - (
            BALANCE.support_program_billing_retention_reset_investor_pressure_relief
            + BALANCE.support_program_billing_covenant_reset_investor_pressure_relief
        )
    )
    state.finance.covenant_risk = clamp_int(
        state.finance.covenant_risk - BALANCE.support_program_billing_covenant_reset_covenant_relief
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_billing_retention_reset_board_confidence_gain
            + BALANCE.support_program_billing_covenant_reset_board_confidence_gain
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a billing dispute desk for {account.name}. Cash -{cost}, "
            f"invoice risk now {account.invoice_risk}."
        )
    )


def run_billing_dispute_cabinet(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the deepest billing reset before disputes and covenant heat define the run."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    cost = quantize_money(
        BALANCE.support_program_billing_stabilization_cost
        + BALANCE.support_program_billing_retention_reset_cost
        + BALANCE.support_program_billing_covenant_reset_cost
    )
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < cost:
        raise ValueError("Not enough cash to run a billing dispute cabinet this turn.")
    if (
        classify_account_support_lane(account) is not SupportLaneFocus.BILLING
        and account.invoice_risk <= 16
        and account.failed_payment_risk <= 16
        and account.dunning_steps <= 0
        and account.renewal_health >= 78
        and account.churn_risk <= 14
    ):
        raise ValueError("That account does not need a billing dispute cabinet right now.")

    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - cost)
    state.support_program.lane_focus = SupportLaneFocus.BILLING
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_billing_stabilization_backlog_relief
            + BALANCE.support_program_billing_retention_reset_backlog_relief
            + BALANCE.support_program_billing_covenant_reset_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_billing_stabilization_escalation_relief
            + BALANCE.support_program_billing_retention_reset_escalation_relief
            + BALANCE.support_program_billing_covenant_reset_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_billing_stabilization_ticket_relief
            + BALANCE.support_program_billing_retention_reset_ticket_relief
            + BALANCE.support_program_billing_covenant_reset_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_billing_stabilization_sla_relief
            + BALANCE.support_program_billing_retention_reset_sla_relief
            + BALANCE.support_program_billing_covenant_reset_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_billing_stabilization_queue_age_relief
            + BALANCE.support_program_billing_retention_reset_queue_age_relief
            + BALANCE.support_program_billing_covenant_reset_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_billing_stabilization_support_load_relief
            + BALANCE.support_program_billing_retention_reset_support_load_relief
            + BALANCE.support_program_billing_covenant_reset_support_load_relief
        )
    )
    account.invoice_risk = clamp_int(
        account.invoice_risk
        - (
            BALANCE.support_program_billing_stabilization_invoice_relief
            + BALANCE.support_program_billing_retention_reset_invoice_relief
            + BALANCE.support_program_billing_covenant_reset_invoice_relief
        )
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk
        - (
            BALANCE.support_program_billing_stabilization_payment_relief
            + BALANCE.support_program_billing_retention_reset_payment_relief
            + BALANCE.support_program_billing_covenant_reset_payment_relief
        )
    )
    account.dunning_steps = max(
        0,
        account.dunning_steps
        - (
            BALANCE.support_program_billing_stabilization_dunning_relief
            + BALANCE.support_program_billing_retention_reset_dunning_relief
            + BALANCE.support_program_billing_covenant_reset_dunning_relief
        ),
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_billing_stabilization_renewal_health_gain
            + BALANCE.support_program_billing_retention_reset_renewal_health_gain
            + BALANCE.support_program_billing_covenant_reset_renewal_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_billing_stabilization_satisfaction_gain
            + BALANCE.support_program_billing_retention_reset_satisfaction_gain
            + BALANCE.support_program_billing_covenant_reset_satisfaction_gain
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_billing_stabilization_churn_relief
            + BALANCE.support_program_billing_retention_reset_churn_relief
            + BALANCE.support_program_billing_covenant_reset_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.BILLING,
        BALANCE.support_program_billing_stabilization_lane_relief
        + BALANCE.support_program_billing_retention_reset_lane_relief
        + BALANCE.support_program_billing_covenant_reset_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_billing_stabilization_board_pressure_relief
            + BALANCE.support_program_billing_retention_reset_board_pressure_relief
            + BALANCE.support_program_billing_covenant_reset_board_pressure_relief
        )
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - (
            BALANCE.support_program_billing_stabilization_investor_pressure_relief
            + BALANCE.support_program_billing_retention_reset_investor_pressure_relief
            + BALANCE.support_program_billing_covenant_reset_investor_pressure_relief
        )
    )
    state.finance.covenant_risk = clamp_int(
        state.finance.covenant_risk - BALANCE.support_program_billing_covenant_reset_covenant_relief
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_billing_retention_reset_board_confidence_gain
            + BALANCE.support_program_billing_covenant_reset_board_confidence_gain
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a billing dispute cabinet for {account.name}. Cash -{cost}, "
            f"invoice risk now {account.invoice_risk}."
        )
    )


def run_billing_collection_bridge(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the deepest billing follow-up before disputes become the capital story."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    cost = quantize_money(
        BALANCE.support_program_billing_stabilization_cost
        + BALANCE.support_program_billing_retention_reset_cost * 2
        + BALANCE.support_program_billing_covenant_reset_cost
    )
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < cost:
        raise ValueError("Not enough cash to run a billing collection bridge this turn.")
    if (
        classify_account_support_lane(account) is not SupportLaneFocus.BILLING
        and account.invoice_risk <= 18
        and account.failed_payment_risk <= 18
        and account.dunning_steps <= 0
        and account.renewal_health >= 80
        and account.churn_risk <= 14
    ):
        raise ValueError("That account does not need a billing collection bridge right now.")

    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - cost)
    state.support_program.lane_focus = SupportLaneFocus.BILLING
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_billing_stabilization_backlog_relief
            + BALANCE.support_program_billing_retention_reset_backlog_relief * 2
            + BALANCE.support_program_billing_covenant_reset_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_billing_stabilization_escalation_relief
            + BALANCE.support_program_billing_retention_reset_escalation_relief * 2
            + BALANCE.support_program_billing_covenant_reset_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_billing_stabilization_ticket_relief
            + BALANCE.support_program_billing_retention_reset_ticket_relief * 2
            + BALANCE.support_program_billing_covenant_reset_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_billing_stabilization_sla_relief
            + BALANCE.support_program_billing_retention_reset_sla_relief * 2
            + BALANCE.support_program_billing_covenant_reset_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_billing_stabilization_queue_age_relief
            + BALANCE.support_program_billing_retention_reset_queue_age_relief * 2
            + BALANCE.support_program_billing_covenant_reset_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_billing_stabilization_support_load_relief
            + BALANCE.support_program_billing_retention_reset_support_load_relief * 2
            + BALANCE.support_program_billing_covenant_reset_support_load_relief
        )
    )
    account.invoice_risk = clamp_int(
        account.invoice_risk
        - (
            BALANCE.support_program_billing_stabilization_invoice_relief
            + BALANCE.support_program_billing_retention_reset_invoice_relief * 2
            + BALANCE.support_program_billing_covenant_reset_invoice_relief
        )
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk
        - (
            BALANCE.support_program_billing_stabilization_payment_relief
            + BALANCE.support_program_billing_retention_reset_payment_relief * 2
            + BALANCE.support_program_billing_covenant_reset_payment_relief
        )
    )
    account.dunning_steps = max(
        0,
        account.dunning_steps
        - (
            BALANCE.support_program_billing_stabilization_dunning_relief
            + BALANCE.support_program_billing_retention_reset_dunning_relief * 2
            + BALANCE.support_program_billing_covenant_reset_dunning_relief
        ),
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_billing_stabilization_renewal_health_gain
            + BALANCE.support_program_billing_retention_reset_renewal_health_gain * 2
            + BALANCE.support_program_billing_covenant_reset_renewal_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_billing_stabilization_satisfaction_gain
            + BALANCE.support_program_billing_retention_reset_satisfaction_gain * 2
            + BALANCE.support_program_billing_covenant_reset_satisfaction_gain
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_billing_stabilization_churn_relief
            + BALANCE.support_program_billing_retention_reset_churn_relief * 2
            + BALANCE.support_program_billing_covenant_reset_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 2)
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.BILLING,
        BALANCE.support_program_billing_stabilization_lane_relief
        + BALANCE.support_program_billing_retention_reset_lane_relief * 2
        + BALANCE.support_program_billing_covenant_reset_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_billing_stabilization_board_pressure_relief
            + BALANCE.support_program_billing_retention_reset_board_pressure_relief * 2
            + BALANCE.support_program_billing_covenant_reset_board_pressure_relief
        )
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - (
            BALANCE.support_program_billing_stabilization_investor_pressure_relief
            + BALANCE.support_program_billing_retention_reset_investor_pressure_relief * 2
            + BALANCE.support_program_billing_covenant_reset_investor_pressure_relief
        )
    )
    state.finance.covenant_risk = clamp_int(
        state.finance.covenant_risk - BALANCE.support_program_billing_covenant_reset_covenant_relief
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_billing_retention_reset_board_confidence_gain * 2
            + BALANCE.support_program_billing_covenant_reset_board_confidence_gain
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a billing collection bridge for {account.name}. Cash -{cost}, "
            f"invoice risk now {account.invoice_risk}."
        )
    )


def run_billing_collection_office(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the deepest billing follow-up when disputes, covenants, and renewals are converging."""

    account = _get_account_by_id(state.customer_accounts, account_id)
    cost = quantize_money(
        BALANCE.support_program_billing_stabilization_cost
        + BALANCE.support_program_billing_retention_reset_cost * 3
        + BALANCE.support_program_billing_covenant_reset_cost * 2
    )
    if account.status is CustomerAccountStatus.CHURNED:
        raise ValueError("That account has already churned.")
    if state.company.cash_on_hand < cost:
        raise ValueError("Not enough cash to run a billing collection office this turn.")
    if (
        classify_account_support_lane(account) is not SupportLaneFocus.BILLING
        and account.invoice_risk <= 20
        and account.failed_payment_risk <= 20
        and account.dunning_steps <= 0
        and account.renewal_health >= 82
        and account.churn_risk <= 12
    ):
        raise ValueError("That account does not need a billing collection office right now.")

    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - cost)
    state.support_program.lane_focus = SupportLaneFocus.BILLING
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_billing_stabilization_backlog_relief
            + BALANCE.support_program_billing_retention_reset_backlog_relief * 3
            + BALANCE.support_program_billing_covenant_reset_backlog_relief * 2
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_billing_stabilization_escalation_relief
            + BALANCE.support_program_billing_retention_reset_escalation_relief * 3
            + BALANCE.support_program_billing_covenant_reset_escalation_relief * 2
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_billing_stabilization_ticket_relief
            + BALANCE.support_program_billing_retention_reset_ticket_relief * 3
            + BALANCE.support_program_billing_covenant_reset_ticket_relief * 2
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_billing_stabilization_sla_relief
            + BALANCE.support_program_billing_retention_reset_sla_relief * 3
            + BALANCE.support_program_billing_covenant_reset_sla_relief * 2
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_billing_stabilization_queue_age_relief
            + BALANCE.support_program_billing_retention_reset_queue_age_relief * 3
            + BALANCE.support_program_billing_covenant_reset_queue_age_relief * 2
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_billing_stabilization_support_load_relief
            + BALANCE.support_program_billing_retention_reset_support_load_relief * 3
            + BALANCE.support_program_billing_covenant_reset_support_load_relief * 2
        )
    )
    account.invoice_risk = clamp_int(
        account.invoice_risk
        - (
            BALANCE.support_program_billing_stabilization_invoice_relief
            + BALANCE.support_program_billing_retention_reset_invoice_relief * 3
            + BALANCE.support_program_billing_covenant_reset_invoice_relief * 2
        )
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk
        - (
            BALANCE.support_program_billing_stabilization_payment_relief
            + BALANCE.support_program_billing_retention_reset_payment_relief * 3
            + BALANCE.support_program_billing_covenant_reset_payment_relief * 2
        )
    )
    account.dunning_steps = max(
        0,
        account.dunning_steps
        - (
            BALANCE.support_program_billing_stabilization_dunning_relief
            + BALANCE.support_program_billing_retention_reset_dunning_relief * 3
            + BALANCE.support_program_billing_covenant_reset_dunning_relief * 2
        ),
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_billing_stabilization_renewal_health_gain
            + BALANCE.support_program_billing_retention_reset_renewal_health_gain * 3
            + BALANCE.support_program_billing_covenant_reset_renewal_health_gain * 2
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_billing_stabilization_satisfaction_gain
            + BALANCE.support_program_billing_retention_reset_satisfaction_gain * 3
            + BALANCE.support_program_billing_covenant_reset_satisfaction_gain * 2
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_billing_stabilization_churn_relief
            + BALANCE.support_program_billing_retention_reset_churn_relief * 3
            + BALANCE.support_program_billing_covenant_reset_churn_relief * 2
        )
    )
    account.escalation_count = max(0, account.escalation_count - 2)
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.BILLING,
        BALANCE.support_program_billing_stabilization_lane_relief
        + BALANCE.support_program_billing_retention_reset_lane_relief * 3
        + BALANCE.support_program_billing_covenant_reset_lane_relief * 2,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_billing_stabilization_board_pressure_relief
            + BALANCE.support_program_billing_retention_reset_board_pressure_relief * 3
            + BALANCE.support_program_billing_covenant_reset_board_pressure_relief * 2
        )
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - (
            BALANCE.support_program_billing_stabilization_investor_pressure_relief
            + BALANCE.support_program_billing_retention_reset_investor_pressure_relief * 3
            + BALANCE.support_program_billing_covenant_reset_investor_pressure_relief * 2
        )
    )
    state.finance.covenant_risk = clamp_int(
        state.finance.covenant_risk
        - BALANCE.support_program_billing_covenant_reset_covenant_relief * 2
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_billing_retention_reset_board_confidence_gain * 3
            + BALANCE.support_program_billing_covenant_reset_board_confidence_gain * 2
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a billing collection office for {account.name}. Cash -{cost}, "
            f"invoice risk now {account.invoice_risk}."
        )
    )


def run_billing_settlement_board(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the hardest billing follow-up when collections, covenants, and renewals all matter."""

    base_cost = quantize_money(
        BALANCE.support_program_billing_stabilization_cost
        + BALANCE.support_program_billing_retention_reset_cost * 3
        + BALANCE.support_program_billing_covenant_reset_cost * 2
    )
    extra_cost = quantize_money(
        BALANCE.support_program_billing_retention_reset_cost
        + BALANCE.support_program_billing_covenant_reset_cost
    )
    total_cost = quantize_money(base_cost + extra_cost)
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to run a billing settlement board this turn.")

    run_billing_collection_office(state, account_id)
    account = _get_account_by_id(state.customer_accounts, account_id)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_billing_retention_reset_backlog_relief
            + BALANCE.support_program_billing_covenant_reset_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_billing_retention_reset_escalation_relief
            + BALANCE.support_program_billing_covenant_reset_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_billing_retention_reset_ticket_relief
            + BALANCE.support_program_billing_covenant_reset_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_billing_retention_reset_sla_relief
            + BALANCE.support_program_billing_covenant_reset_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_billing_retention_reset_queue_age_relief
            + BALANCE.support_program_billing_covenant_reset_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_billing_retention_reset_support_load_relief
            + BALANCE.support_program_billing_covenant_reset_support_load_relief
        )
    )
    account.invoice_risk = clamp_int(
        account.invoice_risk
        - (
            BALANCE.support_program_billing_retention_reset_invoice_relief
            + BALANCE.support_program_billing_covenant_reset_invoice_relief
        )
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk
        - (
            BALANCE.support_program_billing_retention_reset_payment_relief
            + BALANCE.support_program_billing_covenant_reset_payment_relief
        )
    )
    account.dunning_steps = max(
        0,
        account.dunning_steps
        - (
            BALANCE.support_program_billing_retention_reset_dunning_relief
            + BALANCE.support_program_billing_covenant_reset_dunning_relief
        ),
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_billing_retention_reset_renewal_health_gain
            + BALANCE.support_program_billing_covenant_reset_renewal_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_billing_retention_reset_satisfaction_gain
            + BALANCE.support_program_billing_covenant_reset_satisfaction_gain
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_billing_retention_reset_churn_relief
            + BALANCE.support_program_billing_covenant_reset_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.BILLING,
        BALANCE.support_program_billing_retention_reset_lane_relief
        + BALANCE.support_program_billing_covenant_reset_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_billing_retention_reset_board_pressure_relief
            + BALANCE.support_program_billing_covenant_reset_board_pressure_relief
        )
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - (
            BALANCE.support_program_billing_retention_reset_investor_pressure_relief
            + BALANCE.support_program_billing_covenant_reset_investor_pressure_relief
        )
    )
    state.finance.covenant_risk = clamp_int(
        state.finance.covenant_risk - BALANCE.support_program_billing_covenant_reset_covenant_relief
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_billing_retention_reset_board_confidence_gain
            + BALANCE.support_program_billing_covenant_reset_board_confidence_gain
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a billing settlement board for {account.name}. Cash -{total_cost}, "
            f"invoice risk now {account.invoice_risk}."
        )
    )


def run_billing_cash_war_room(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the final billing recovery loop once collections and covenants dominate the story."""

    base_cost = quantize_money(
        BALANCE.support_program_billing_stabilization_cost
        + BALANCE.support_program_billing_retention_reset_cost * 4
        + BALANCE.support_program_billing_covenant_reset_cost * 3
    )
    extra_cost = quantize_money(
        BALANCE.support_program_billing_retention_reset_cost
        + BALANCE.support_program_billing_covenant_reset_cost
    )
    total_cost = quantize_money(base_cost + extra_cost)
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to run a billing cash war room this turn.")

    run_billing_settlement_board(state, account_id)
    account = _get_account_by_id(state.customer_accounts, account_id)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_billing_retention_reset_backlog_relief
            + BALANCE.support_program_billing_covenant_reset_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_billing_retention_reset_escalation_relief
            + BALANCE.support_program_billing_covenant_reset_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_billing_retention_reset_ticket_relief
            + BALANCE.support_program_billing_covenant_reset_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_billing_retention_reset_sla_relief
            + BALANCE.support_program_billing_covenant_reset_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_billing_retention_reset_queue_age_relief
            + BALANCE.support_program_billing_covenant_reset_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_billing_retention_reset_support_load_relief
            + BALANCE.support_program_billing_covenant_reset_support_load_relief
        )
    )
    account.invoice_risk = clamp_int(
        account.invoice_risk
        - (
            BALANCE.support_program_billing_retention_reset_invoice_relief
            + BALANCE.support_program_billing_covenant_reset_invoice_relief
        )
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk
        - (
            BALANCE.support_program_billing_retention_reset_payment_relief
            + BALANCE.support_program_billing_covenant_reset_payment_relief
        )
    )
    account.dunning_steps = max(
        0,
        account.dunning_steps
        - (
            BALANCE.support_program_billing_retention_reset_dunning_relief
            + BALANCE.support_program_billing_covenant_reset_dunning_relief
        ),
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_billing_retention_reset_renewal_health_gain
            + BALANCE.support_program_billing_covenant_reset_renewal_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_billing_retention_reset_satisfaction_gain
            + BALANCE.support_program_billing_covenant_reset_satisfaction_gain
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_billing_retention_reset_churn_relief
            + BALANCE.support_program_billing_covenant_reset_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.BILLING,
        BALANCE.support_program_billing_retention_reset_lane_relief
        + BALANCE.support_program_billing_covenant_reset_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_billing_retention_reset_board_pressure_relief
            + BALANCE.support_program_billing_covenant_reset_board_pressure_relief
        )
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - (
            BALANCE.support_program_billing_retention_reset_investor_pressure_relief
            + BALANCE.support_program_billing_covenant_reset_investor_pressure_relief
        )
    )
    state.finance.covenant_risk = clamp_int(
        state.finance.covenant_risk - BALANCE.support_program_billing_covenant_reset_covenant_relief
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_billing_retention_reset_board_confidence_gain
            + BALANCE.support_program_billing_covenant_reset_board_confidence_gain
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a billing cash war room for {account.name}. Cash -{total_cost}, "
            f"invoice risk now {account.invoice_risk}."
        )
    )


def run_billing_liquidity_command(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the final billing liquidity loop when collections drag still shapes the run."""

    base_cost = quantize_money(
        BALANCE.support_program_billing_stabilization_cost
        + BALANCE.support_program_billing_retention_reset_cost * 4
        + BALANCE.support_program_billing_covenant_reset_cost * 3
    )
    extra_cost = quantize_money(
        BALANCE.support_program_billing_retention_reset_cost * 2
        + BALANCE.support_program_billing_covenant_reset_cost
    )
    total_cost = quantize_money(base_cost + extra_cost)
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to run a billing liquidity command this turn.")

    run_billing_cash_war_room(state, account_id)
    account = _get_account_by_id(state.customer_accounts, account_id)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_billing_retention_reset_backlog_relief * 2
            + BALANCE.support_program_billing_covenant_reset_backlog_relief
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_billing_retention_reset_escalation_relief * 2
            + BALANCE.support_program_billing_covenant_reset_escalation_relief
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_billing_retention_reset_ticket_relief * 2
            + BALANCE.support_program_billing_covenant_reset_ticket_relief
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_billing_retention_reset_sla_relief * 2
            + BALANCE.support_program_billing_covenant_reset_sla_relief
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_billing_retention_reset_queue_age_relief * 2
            + BALANCE.support_program_billing_covenant_reset_queue_age_relief
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_billing_retention_reset_support_load_relief * 2
            + BALANCE.support_program_billing_covenant_reset_support_load_relief
        )
    )
    account.invoice_risk = clamp_int(
        account.invoice_risk
        - (
            BALANCE.support_program_billing_retention_reset_invoice_relief * 2
            + BALANCE.support_program_billing_covenant_reset_invoice_relief
        )
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk
        - (
            BALANCE.support_program_billing_retention_reset_payment_relief * 2
            + BALANCE.support_program_billing_covenant_reset_payment_relief
        )
    )
    account.dunning_steps = max(
        0,
        account.dunning_steps
        - (
            BALANCE.support_program_billing_retention_reset_dunning_relief * 2
            + BALANCE.support_program_billing_covenant_reset_dunning_relief
        ),
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_billing_retention_reset_renewal_health_gain * 2
            + BALANCE.support_program_billing_covenant_reset_renewal_health_gain
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_billing_retention_reset_satisfaction_gain * 2
            + BALANCE.support_program_billing_covenant_reset_satisfaction_gain
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_billing_retention_reset_churn_relief * 2
            + BALANCE.support_program_billing_covenant_reset_churn_relief
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.BILLING,
        BALANCE.support_program_billing_retention_reset_lane_relief * 2
        + BALANCE.support_program_billing_covenant_reset_lane_relief,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_billing_retention_reset_board_pressure_relief * 2
            + BALANCE.support_program_billing_covenant_reset_board_pressure_relief
        )
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - (
            BALANCE.support_program_billing_retention_reset_investor_pressure_relief * 2
            + BALANCE.support_program_billing_covenant_reset_investor_pressure_relief
        )
    )
    state.finance.covenant_risk = clamp_int(
        state.finance.covenant_risk
        - (BALANCE.support_program_billing_covenant_reset_covenant_relief + 2)
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_billing_retention_reset_board_confidence_gain * 2
            + BALANCE.support_program_billing_covenant_reset_board_confidence_gain
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a billing liquidity command for {account.name}. Cash -{total_cost}, "
            f"invoice risk now {account.invoice_risk}."
        )
    )


def run_billing_liquidity_summit(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the last billing containment loop when collections still shape the path."""

    base_cost = quantize_money(
        BALANCE.support_program_billing_stabilization_cost
        + BALANCE.support_program_billing_retention_reset_cost * 6
        + BALANCE.support_program_billing_covenant_reset_cost * 4
    )
    extra_cost = quantize_money(
        BALANCE.support_program_billing_retention_reset_cost * 2
        + BALANCE.support_program_billing_covenant_reset_cost * 2
    )
    total_cost = quantize_money(base_cost + extra_cost)
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to run a billing liquidity summit this turn.")

    run_billing_liquidity_command(state, account_id)
    account = _get_account_by_id(state.customer_accounts, account_id)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_billing_retention_reset_backlog_relief * 2
            + BALANCE.support_program_billing_covenant_reset_backlog_relief * 2
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_billing_retention_reset_escalation_relief * 2
            + BALANCE.support_program_billing_covenant_reset_escalation_relief * 2
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_billing_retention_reset_ticket_relief * 2
            + BALANCE.support_program_billing_covenant_reset_ticket_relief * 2
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_billing_retention_reset_sla_relief * 2
            + BALANCE.support_program_billing_covenant_reset_sla_relief * 2
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_billing_retention_reset_queue_age_relief * 2
            + BALANCE.support_program_billing_covenant_reset_queue_age_relief * 2
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_billing_retention_reset_support_load_relief * 2
            + BALANCE.support_program_billing_covenant_reset_support_load_relief * 2
        )
    )
    account.invoice_risk = clamp_int(
        account.invoice_risk
        - (
            BALANCE.support_program_billing_retention_reset_invoice_relief * 2
            + BALANCE.support_program_billing_covenant_reset_invoice_relief * 2
        )
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk
        - (
            BALANCE.support_program_billing_retention_reset_payment_relief * 2
            + BALANCE.support_program_billing_covenant_reset_payment_relief * 2
        )
    )
    account.dunning_steps = max(
        0,
        account.dunning_steps
        - (
            BALANCE.support_program_billing_retention_reset_dunning_relief * 2
            + BALANCE.support_program_billing_covenant_reset_dunning_relief * 2
        ),
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_billing_retention_reset_renewal_health_gain * 2
            + BALANCE.support_program_billing_covenant_reset_renewal_health_gain * 2
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_billing_retention_reset_satisfaction_gain * 2
            + BALANCE.support_program_billing_covenant_reset_satisfaction_gain * 2
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_billing_retention_reset_churn_relief * 2
            + BALANCE.support_program_billing_covenant_reset_churn_relief * 2
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.BILLING,
        BALANCE.support_program_billing_retention_reset_lane_relief * 2
        + BALANCE.support_program_billing_covenant_reset_lane_relief * 2,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_billing_retention_reset_board_pressure_relief * 2
            + BALANCE.support_program_billing_covenant_reset_board_pressure_relief * 2
        )
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - (
            BALANCE.support_program_billing_retention_reset_investor_pressure_relief * 2
            + BALANCE.support_program_billing_covenant_reset_investor_pressure_relief * 2
        )
    )
    state.finance.covenant_risk = clamp_int(
        state.finance.covenant_risk - BALANCE.support_program_billing_covenant_reset_covenant_relief
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_billing_retention_reset_board_confidence_gain * 2
            + BALANCE.support_program_billing_covenant_reset_board_confidence_gain * 2
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a billing liquidity summit for {account.name}. Cash -{total_cost}, "
            f"invoice risk now {account.invoice_risk}."
        )
    )


def run_billing_liquidity_directorate(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the final billing containment loop when summit-level control still is not enough."""

    base_cost = quantize_money(
        BALANCE.support_program_billing_stabilization_cost
        + BALANCE.support_program_billing_retention_reset_cost * 8
        + BALANCE.support_program_billing_covenant_reset_cost * 6
    )
    extra_cost = quantize_money(
        BALANCE.support_program_billing_retention_reset_cost * 2
        + BALANCE.support_program_billing_covenant_reset_cost * 2
    )
    total_cost = quantize_money(base_cost + extra_cost)
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to run a billing liquidity directorate this turn.")

    run_billing_liquidity_summit(state, account_id)
    account = _get_account_by_id(state.customer_accounts, account_id)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_billing_retention_reset_backlog_relief * 2
            + BALANCE.support_program_billing_covenant_reset_backlog_relief * 2
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_billing_retention_reset_escalation_relief * 2
            + BALANCE.support_program_billing_covenant_reset_escalation_relief * 2
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_billing_retention_reset_ticket_relief * 2
            + BALANCE.support_program_billing_covenant_reset_ticket_relief * 2
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_billing_retention_reset_sla_relief * 2
            + BALANCE.support_program_billing_covenant_reset_sla_relief * 2
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_billing_retention_reset_queue_age_relief * 2
            + BALANCE.support_program_billing_covenant_reset_queue_age_relief * 2
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_billing_retention_reset_support_load_relief * 2
            + BALANCE.support_program_billing_covenant_reset_support_load_relief * 2
        )
    )
    account.invoice_risk = clamp_int(
        account.invoice_risk
        - (
            BALANCE.support_program_billing_retention_reset_invoice_relief * 2
            + BALANCE.support_program_billing_covenant_reset_invoice_relief * 2
        )
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk
        - (
            BALANCE.support_program_billing_retention_reset_payment_relief * 2
            + BALANCE.support_program_billing_covenant_reset_payment_relief * 2
        )
    )
    account.dunning_steps = max(
        0,
        account.dunning_steps
        - (
            BALANCE.support_program_billing_retention_reset_dunning_relief * 2
            + BALANCE.support_program_billing_covenant_reset_dunning_relief * 2
        ),
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_billing_retention_reset_renewal_health_gain * 2
            + BALANCE.support_program_billing_covenant_reset_renewal_health_gain * 2
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_billing_retention_reset_satisfaction_gain * 2
            + BALANCE.support_program_billing_covenant_reset_satisfaction_gain * 2
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_billing_retention_reset_churn_relief * 2
            + BALANCE.support_program_billing_covenant_reset_churn_relief * 2
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.BILLING,
        BALANCE.support_program_billing_retention_reset_lane_relief * 2
        + BALANCE.support_program_billing_covenant_reset_lane_relief * 2,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_billing_retention_reset_board_pressure_relief * 2
            + BALANCE.support_program_billing_covenant_reset_board_pressure_relief * 2
        )
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - (
            BALANCE.support_program_billing_retention_reset_investor_pressure_relief * 2
            + BALANCE.support_program_billing_covenant_reset_investor_pressure_relief * 2
        )
    )
    state.finance.covenant_risk = clamp_int(
        state.finance.covenant_risk - BALANCE.support_program_billing_covenant_reset_covenant_relief
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_billing_retention_reset_board_confidence_gain * 2
            + BALANCE.support_program_billing_covenant_reset_board_confidence_gain * 2
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a billing liquidity directorate for {account.name}. Cash -{total_cost}, "
            f"invoice risk now {account.invoice_risk}."
        )
    )


def run_billing_liquidity_secretariat(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run a deeper billing containment loop after the directorate tier saturates."""

    base_cost = quantize_money(
        BALANCE.support_program_billing_stabilization_cost
        + BALANCE.support_program_billing_retention_reset_cost * 10
        + BALANCE.support_program_billing_covenant_reset_cost * 8
    )
    extra_cost = quantize_money(
        BALANCE.support_program_billing_retention_reset_cost * 2
        + BALANCE.support_program_billing_covenant_reset_cost * 2
    )
    total_cost = quantize_money(base_cost + extra_cost)
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to run a billing liquidity secretariat this turn.")

    run_billing_liquidity_directorate(state, account_id)
    account = _get_account_by_id(state.customer_accounts, account_id)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_billing_retention_reset_backlog_relief * 2
            + BALANCE.support_program_billing_covenant_reset_backlog_relief * 2
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_billing_retention_reset_escalation_relief * 2
            + BALANCE.support_program_billing_covenant_reset_escalation_relief * 2
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_billing_retention_reset_ticket_relief * 2
            + BALANCE.support_program_billing_covenant_reset_ticket_relief * 2
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_billing_retention_reset_sla_relief * 2
            + BALANCE.support_program_billing_covenant_reset_sla_relief * 2
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_billing_retention_reset_queue_age_relief * 2
            + BALANCE.support_program_billing_covenant_reset_queue_age_relief * 2
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_billing_retention_reset_support_load_relief * 2
            + BALANCE.support_program_billing_covenant_reset_support_load_relief * 2
        )
    )
    account.invoice_risk = clamp_int(
        account.invoice_risk
        - (
            BALANCE.support_program_billing_retention_reset_invoice_relief * 2
            + BALANCE.support_program_billing_covenant_reset_invoice_relief * 2
        )
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk
        - (
            BALANCE.support_program_billing_retention_reset_payment_relief * 2
            + BALANCE.support_program_billing_covenant_reset_payment_relief * 2
        )
    )
    account.dunning_steps = max(
        0,
        account.dunning_steps
        - (
            BALANCE.support_program_billing_retention_reset_dunning_relief * 2
            + BALANCE.support_program_billing_covenant_reset_dunning_relief * 2
        ),
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_billing_retention_reset_renewal_health_gain * 2
            + BALANCE.support_program_billing_covenant_reset_renewal_health_gain * 2
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_billing_retention_reset_satisfaction_gain * 2
            + BALANCE.support_program_billing_covenant_reset_satisfaction_gain * 2
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_billing_retention_reset_churn_relief * 2
            + BALANCE.support_program_billing_covenant_reset_churn_relief * 2
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.BILLING,
        BALANCE.support_program_billing_retention_reset_lane_relief * 2
        + BALANCE.support_program_billing_covenant_reset_lane_relief * 2,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_billing_retention_reset_board_pressure_relief * 2
            + BALANCE.support_program_billing_covenant_reset_board_pressure_relief * 2
        )
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - (
            BALANCE.support_program_billing_retention_reset_investor_pressure_relief * 2
            + BALANCE.support_program_billing_covenant_reset_investor_pressure_relief * 2
        )
    )
    state.finance.covenant_risk = clamp_int(
        state.finance.covenant_risk - BALANCE.support_program_billing_covenant_reset_covenant_relief
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_billing_retention_reset_board_confidence_gain * 2
            + BALANCE.support_program_billing_covenant_reset_board_confidence_gain * 2
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a billing liquidity secretariat for {account.name}. Cash -{total_cost}, "
            f"invoice risk now {account.invoice_risk}."
        )
    )


def run_billing_liquidity_authority(
    state: GameState,
    account_id,
) -> SupportOpsActionSummary:
    """Run the deepest billing containment loop after the secretariat tier saturates."""

    base_cost = quantize_money(
        BALANCE.support_program_billing_stabilization_cost
        + BALANCE.support_program_billing_retention_reset_cost * 12
        + BALANCE.support_program_billing_covenant_reset_cost * 10
    )
    extra_cost = quantize_money(
        BALANCE.support_program_billing_retention_reset_cost * 2
        + BALANCE.support_program_billing_covenant_reset_cost * 2
    )
    total_cost = quantize_money(base_cost + extra_cost)
    if state.company.cash_on_hand < total_cost:
        raise ValueError("Not enough cash to run a billing liquidity authority this turn.")

    run_billing_liquidity_secretariat(state, account_id)
    account = _get_account_by_id(state.customer_accounts, account_id)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - extra_cost)
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue
        - (
            BALANCE.support_program_billing_retention_reset_backlog_relief * 2
            + BALANCE.support_program_billing_covenant_reset_backlog_relief * 2
        ),
    )
    state.support_program.escalation_queue = max(
        0,
        state.support_program.escalation_queue
        - (
            BALANCE.support_program_billing_retention_reset_escalation_relief * 2
            + BALANCE.support_program_billing_covenant_reset_escalation_relief * 2
        ),
    )
    account.open_tickets = max(
        0,
        account.open_tickets
        - (
            BALANCE.support_program_billing_retention_reset_ticket_relief * 2
            + BALANCE.support_program_billing_covenant_reset_ticket_relief * 2
        ),
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk
        - (
            BALANCE.support_program_billing_retention_reset_sla_relief * 2
            + BALANCE.support_program_billing_covenant_reset_sla_relief * 2
        )
    )
    account.ticket_queue_age = max(
        0,
        account.ticket_queue_age
        - (
            BALANCE.support_program_billing_retention_reset_queue_age_relief * 2
            + BALANCE.support_program_billing_covenant_reset_queue_age_relief * 2
        ),
    )
    account.support_load = clamp_int(
        account.support_load
        - (
            BALANCE.support_program_billing_retention_reset_support_load_relief * 2
            + BALANCE.support_program_billing_covenant_reset_support_load_relief * 2
        )
    )
    account.invoice_risk = clamp_int(
        account.invoice_risk
        - (
            BALANCE.support_program_billing_retention_reset_invoice_relief * 2
            + BALANCE.support_program_billing_covenant_reset_invoice_relief * 2
        )
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk
        - (
            BALANCE.support_program_billing_retention_reset_payment_relief * 2
            + BALANCE.support_program_billing_covenant_reset_payment_relief * 2
        )
    )
    account.dunning_steps = max(
        0,
        account.dunning_steps
        - (
            BALANCE.support_program_billing_retention_reset_dunning_relief * 2
            + BALANCE.support_program_billing_covenant_reset_dunning_relief * 2
        ),
    )
    account.renewal_health = clamp_int(
        account.renewal_health
        + (
            BALANCE.support_program_billing_retention_reset_renewal_health_gain * 2
            + BALANCE.support_program_billing_covenant_reset_renewal_health_gain * 2
        )
    )
    account.satisfaction = clamp_int(
        account.satisfaction
        + (
            BALANCE.support_program_billing_retention_reset_satisfaction_gain * 2
            + BALANCE.support_program_billing_covenant_reset_satisfaction_gain * 2
        )
    )
    account.churn_risk = clamp_int(
        account.churn_risk
        - (
            BALANCE.support_program_billing_retention_reset_churn_relief * 2
            + BALANCE.support_program_billing_covenant_reset_churn_relief * 2
        )
    )
    account.escalation_count = max(0, account.escalation_count - 1)
    _apply_lane_program_relief(
        state.support_program,
        SupportLaneFocus.BILLING,
        BALANCE.support_program_billing_retention_reset_lane_relief * 2
        + BALANCE.support_program_billing_covenant_reset_lane_relief * 2,
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure
        - (
            BALANCE.support_program_billing_retention_reset_board_pressure_relief * 2
            + BALANCE.support_program_billing_covenant_reset_board_pressure_relief * 2
        )
    )
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure
        - (
            BALANCE.support_program_billing_retention_reset_investor_pressure_relief * 2
            + BALANCE.support_program_billing_covenant_reset_investor_pressure_relief * 2
        )
    )
    state.finance.covenant_risk = clamp_int(
        state.finance.covenant_risk - BALANCE.support_program_billing_covenant_reset_covenant_relief
    )
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence
        + (
            BALANCE.support_program_billing_retention_reset_board_confidence_gain * 2
            + BALANCE.support_program_billing_covenant_reset_board_confidence_gain * 2
        )
    )
    return SupportOpsActionSummary(
        message=(
            f"Ran a billing liquidity authority for {account.name}. Cash -{total_cost}, "
            f"invoice risk now {account.invoice_risk}."
        )
    )


def count_escalating_accounts(accounts: list[CustomerAccount]) -> int:
    """Return the number of accounts with severe support pressure."""

    return sum(
        1
        for account in accounts
        if account.status is not CustomerAccountStatus.CHURNED
        and (
            account.open_tickets >= BALANCE.support_program_escalation_ticket_threshold
            or account.sla_breach_risk >= BALANCE.support_program_escalation_sla_threshold
        )
    )


def _is_revenue_at_risk_account(account: CustomerAccount, *, sla_target: int) -> bool:
    stressed_account = (
        account.ticket_queue_age >= BALANCE.support_program_queue_age_threshold
        or account.open_tickets >= BALANCE.support_program_escalation_ticket_threshold
        or account.sla_breach_risk >= sla_target
    )
    return (
        stressed_account
        and (
            account.contract_value >= BALANCE.support_program_revenue_at_risk_contract_threshold
            or account.segment.value == "enterprise"
        )
    ) or account.failed_payment_risk >= BALANCE.support_program_queue_age_threshold * 10


def _is_renewal_pressure_account(account: CustomerAccount) -> bool:
    return (
        account.renewal_health <= BALANCE.support_program_renewal_pressure_health_threshold
        or account.churn_risk >= BALANCE.support_program_renewal_pressure_churn_threshold
        or account.renewal_offer_active
    )


def _is_severe_queue_account(
    account: CustomerAccount,
    *,
    queue_age_threshold: int,
    sla_target: int,
) -> bool:
    return account.support_tier in {SupportTier.PRIORITY, SupportTier.WHITE_GLOVE} and (
        account.ticket_queue_age >= queue_age_threshold + 1
        or account.open_tickets >= BALANCE.support_program_escalation_ticket_threshold
        or account.sla_breach_risk >= sla_target
    )


def _is_support_recovery_ready_account(account: CustomerAccount, *, sla_target: int) -> bool:
    return (
        account.open_tickets == 0
        and account.sla_breach_risk < max(1, sla_target // 2)
        and account.ticket_queue_age <= BALANCE.support_program_recovery_queue_age_max
        and (account.satisfaction < 78 or account.renewal_health < 78 or account.churn_risk > 0)
    )


def calculate_support_staff_capacity(state: GameState) -> int:
    support_roles = sum(
        BALANCE.support_program_role_capacity[employee.role.value] for employee in state.employees
    )
    engineer_relief = (
        sum(
            1
            for employee in state.employees
            if employee.role is EmployeeRole.ENGINEER and employee.assigned_product_id is None
        )
        // BALANCE.support_program_staff_capacity_engineer_relief_divisor
    )
    team_lead_bonus = sum(1 for employee in state.employees if employee.is_team_lead)
    budget_capacity = state.functional_budget.customer_success_share // (
        BALANCE.support_program_budget_capacity_divisor
    )
    return (
        (support_roles * BALANCE.support_program_staff_capacity_unit)
        + (state.support_program.staffing_level * BALANCE.support_program_staffing_capacity_unit)
        + _focus_capacity_bonus(state)
        + engineer_relief
        + team_lead_bonus
        + budget_capacity
    )


def calculate_support_lane_snapshots(
    state: GameState,
    *,
    customer_success_bonus: int = 0,
    total_capacity: int | None = None,
) -> dict[SupportLaneFocus, SupportLaneSnapshot]:
    """Return lane-specific pressure, capacity, and overflow for dashboard and simulation."""

    active_accounts = [
        account
        for account in state.customer_accounts
        if account.status is not CustomerAccountStatus.CHURNED
    ]
    lane_pressures = {
        SupportLaneFocus.ONBOARDING: 0,
        SupportLaneFocus.ENTERPRISE: 0,
        SupportLaneFocus.BILLING: 0,
    }
    lane_counts = {
        SupportLaneFocus.ONBOARDING: 0,
        SupportLaneFocus.ENTERPRISE: 0,
        SupportLaneFocus.BILLING: 0,
    }
    for account in active_accounts:
        pressures = _build_account_lane_pressures(account)
        for lane, pressure in pressures.items():
            lane_pressures[lane] += pressure
        dominant_lane = classify_account_support_lane(account)
        if dominant_lane is not SupportLaneFocus.BALANCED:
            lane_counts[dominant_lane] += 1

    if total_capacity is None:
        ticket_relief, _ = calculate_support_program_relief(
            state.support_program,
            customer_success_bonus=customer_success_bonus,
        )
        total_capacity = (
            BALANCE.support_program_base_capacity
            + ticket_relief
            + calculate_support_staff_capacity(state)
        )

    weights: dict[SupportLaneFocus, int] = {}
    staffing_plan = calculate_support_lane_staffing_plan(state)
    for lane in lane_pressures:
        weights[lane] = max(1, lane_pressures[lane] + (lane_counts[lane] * 2))
        weights[lane] += (
            staffing_plan.get(lane, 0) * BALANCE.support_program_lane_staffing_weight_unit
        )
    if state.support_program.lane_focus is not SupportLaneFocus.BALANCED:
        weights[state.support_program.lane_focus] += (
            BALANCE.support_program_focus_lane_capacity_bonus
        )

    weight_total = sum(weights.values())
    remaining_capacity = max(0, total_capacity)
    snapshots: dict[SupportLaneFocus, SupportLaneSnapshot] = {}
    ordered_lanes = sorted(
        weights,
        key=lambda lane: (weights[lane], lane_pressures[lane], lane_counts[lane]),
        reverse=True,
    )
    for index, lane in enumerate(ordered_lanes):
        if index == len(ordered_lanes) - 1:
            lane_capacity = remaining_capacity
        else:
            lane_capacity = int((total_capacity * weights[lane]) / max(1, weight_total))
            if lane_counts[lane] > 0 and total_capacity > 0:
                lane_capacity = max(1, lane_capacity)
            lane_capacity = min(remaining_capacity, lane_capacity)
        remaining_capacity = max(0, remaining_capacity - lane_capacity)
        snapshots[lane] = SupportLaneSnapshot(
            lane=lane,
            pressure=lane_pressures[lane],
            capacity=lane_capacity,
            overflow=max(0, lane_pressures[lane] - lane_capacity),
            account_count=lane_counts[lane],
        )
    return snapshots


def _focus_capacity_bonus(state: GameState) -> int:
    focus = state.support_program.lane_focus
    if focus is SupportLaneFocus.BALANCED:
        return 0
    targeted_accounts = 0
    for account in state.customer_accounts:
        if account.status is CustomerAccountStatus.CHURNED:
            continue
        if classify_account_support_lane(account) is focus:
            targeted_accounts += 1
    return targeted_accounts // BALANCE.support_program_focus_ticket_relief_divisor


def _calculate_support_focus_bonus(
    accounts: list[CustomerAccount],
    focus: SupportLaneFocus,
) -> int:
    if focus is SupportLaneFocus.BALANCED:
        return 0
    focus_bonus = 0
    for account in accounts:
        account_lane = classify_account_support_lane(account)
        if account_lane is focus and focus is SupportLaneFocus.ENTERPRISE:
            focus_bonus += BALANCE.support_program_focus_enterprise_bonus
        elif account_lane is focus and focus is SupportLaneFocus.ONBOARDING:
            focus_bonus += BALANCE.support_program_focus_onboarding_bonus
        elif account_lane is focus and focus is SupportLaneFocus.BILLING:
            focus_bonus += BALANCE.support_program_focus_billing_bonus
    return focus_bonus


def _apply_lane_program_relief(
    support_program: SupportProgram,
    lane: SupportLaneFocus,
    relief: int,
) -> None:
    if lane is SupportLaneFocus.ONBOARDING:
        support_program.onboarding_ticket_pressure = max(
            0,
            support_program.onboarding_ticket_pressure - relief,
        )
    elif lane is SupportLaneFocus.ENTERPRISE:
        support_program.enterprise_ticket_pressure = max(
            0,
            support_program.enterprise_ticket_pressure - relief,
        )
    elif lane is SupportLaneFocus.BILLING:
        support_program.billing_ticket_pressure = max(
            0,
            support_program.billing_ticket_pressure - relief,
        )
    support_program.backlog_queue = max(0, support_program.backlog_queue - max(1, relief // 2))


def _calculate_focus_mismatch_penalty(
    focus: SupportLaneFocus,
    *,
    onboarding_ticket_pressure: int,
    enterprise_ticket_pressure: int,
    billing_ticket_pressure: int,
) -> int:
    if focus is SupportLaneFocus.BALANCED:
        return 0
    pressures = {
        SupportLaneFocus.ONBOARDING: onboarding_ticket_pressure,
        SupportLaneFocus.ENTERPRISE: enterprise_ticket_pressure,
        SupportLaneFocus.BILLING: billing_ticket_pressure,
    }
    focus_pressure = pressures[focus]
    highest_other_pressure = max(
        pressure for lane, pressure in pressures.items() if lane is not focus
    )
    pressure_gap = highest_other_pressure - focus_pressure
    if pressure_gap <= 0:
        return 0
    return min(
        BALANCE.support_program_focus_mismatch_backlog_cap,
        pressure_gap // BALANCE.support_program_focus_mismatch_divisor,
    )


def _get_account_by_id(accounts: list[CustomerAccount], account_id) -> CustomerAccount:
    for account in accounts:
        if account.id == account_id:
            return account
    raise ValueError("Selected customer account was not found.")


def classify_account_support_lane(account: CustomerAccount) -> SupportLaneFocus:
    """Classify the dominant lane creating pressure for one account."""

    lane_pressures = _build_account_lane_pressures(account)
    lane, pressure = max(lane_pressures.items(), key=lambda item: item[1])
    if pressure <= 0:
        return SupportLaneFocus.BALANCED
    return lane


def _build_account_lane_pressures(account: CustomerAccount) -> dict[SupportLaneFocus, int]:
    billing_pressure = (
        (account.invoice_risk // BALANCE.support_program_billing_pressure_invoice_divisor)
        + (
            account.failed_payment_risk
            // BALANCE.support_program_billing_pressure_failed_payment_divisor
        )
        + (account.dunning_steps * BALANCE.support_program_billing_pressure_dunning_weight)
        + (account.open_tickets // 2)
    )
    enterprise_pressure = 0
    if account.segment.value == "enterprise" or account.support_tier is SupportTier.WHITE_GLOVE:
        enterprise_pressure = (
            account.open_tickets
            + (account.sla_breach_risk // 8)
            + BALANCE.support_tier_capacity_cost[account.support_tier.value]
        )
    onboarding_pressure = (
        account.open_tickets
        + max(
            0,
            (
                BALANCE.support_program_onboarding_health_pressure_threshold
                - account.onboarding_health
            ),
        )
        // 10
        + max(0, account.support_load - 22) // 6
    )
    return {
        SupportLaneFocus.BILLING: billing_pressure,
        SupportLaneFocus.ENTERPRISE: enterprise_pressure,
        SupportLaneFocus.ONBOARDING: onboarding_pressure,
    }


def _calculate_account_support_severity(account: CustomerAccount) -> int:
    lane = classify_account_support_lane(account)
    lane_bias = {
        SupportLaneFocus.BILLING: account.failed_payment_risk + (account.dunning_steps * 8),
        SupportLaneFocus.ENTERPRISE: account.sla_breach_risk + (account.ticket_queue_age * 4),
        SupportLaneFocus.ONBOARDING: account.open_tickets + (account.support_load * 2),
        SupportLaneFocus.BALANCED: 0,
    }[lane]
    return (
        (account.escalation_count * 12)
        + account.open_tickets
        + account.sla_breach_risk
        + lane_bias
        + (account.churn_risk // 2)
    )


def _get_dominant_pressure_lane(
    *,
    onboarding_ticket_pressure: int,
    enterprise_ticket_pressure: int,
    billing_ticket_pressure: int,
) -> SupportLaneFocus:
    lane, pressure = max(
        {
            SupportLaneFocus.ONBOARDING: onboarding_ticket_pressure,
            SupportLaneFocus.ENTERPRISE: enterprise_ticket_pressure,
            SupportLaneFocus.BILLING: billing_ticket_pressure,
        }.items(),
        key=lambda item: item[1],
    )
    if pressure <= 0:
        return SupportLaneFocus.BALANCED
    return lane
