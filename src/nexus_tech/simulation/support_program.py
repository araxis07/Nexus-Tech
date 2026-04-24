"""Shared support tooling and backlog management."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.domain.models import (
    CustomerAccount,
    CustomerAccountStatus,
    EmployeeRole,
    GameState,
    SupportInvestmentFocus,
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
    reputation_delta: int
    morale_penalty: int
    summary: str


@dataclass(frozen=True)
class SupportOpsActionSummary:
    """Summary of an explicit support-ops intervention."""

    message: str


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
    total_open_tickets = sum(account.open_tickets for account in active_accounts)
    weighted_ticket_pressure = total_open_tickets + sum(
        max(0, BALANCE.support_program_segment_ticket_weight[account.segment.value] - 1)
        for account in active_accounts
        if account.open_tickets > 0
    )
    weighted_ticket_pressure += sum(
        BALANCE.support_tier_capacity_cost[account.support_tier.value]
        for account in active_accounts
    )
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
    )
    effective_capacity = (
        BALANCE.support_program_base_capacity
        + ticket_relief
        + calculate_support_staff_capacity(state)
    )
    incoming_ticket_pressure = weighted_ticket_pressure + state.support_program.backlog_queue
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

    reputation_delta = 0
    morale_penalty = 0
    if (
        state.support_program.backlog_queue >= BALANCE.support_program_backlog_reputation_threshold
        or state.support_program.escalation_queue
        >= BALANCE.support_program_triage_escalation_relief * 2
    ):
        reputation_delta = -BALANCE.support_program_backlog_reputation_loss
    if staffing_gap >= BALANCE.support_program_staffing_gap_reputation_threshold:
        reputation_delta -= 1
    if (
        state.support_program.backlog_queue
        >= BALANCE.support_program_backlog_morale_penalty_threshold
    ):
        morale_penalty = BALANCE.support_program_backlog_morale_penalty
    if staffing_gap > 0:
        morale_penalty += BALANCE.support_program_staffing_gap_morale_penalty

    if not active_accounts:
        summary = "Support tooling is idle."
    elif state.support_program.backlog_queue == 0:
        summary = "Support tooling is keeping ticket flow under control."
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
                account.escalation_count,
                account.open_tickets,
                account.sla_breach_risk,
            ),
            reverse=True,
        )
        if account.status is not CustomerAccountStatus.CHURNED
    ]
    improved_accounts = 0
    for account in accounts[:3]:
        if account.open_tickets <= 0 and account.sla_breach_risk <= 0:
            continue
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
        account.escalation_count = max(0, account.escalation_count - 1)
        improved_accounts += 1

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
    if account.support_tier is SupportTier.STANDARD:
        account.support_tier = SupportTier.PRIORITY
    elif account.support_tier is SupportTier.PRIORITY and account.segment.value == "enterprise":
        account.support_tier = SupportTier.WHITE_GLOVE
    account.open_tickets = max(
        0, account.open_tickets - BALANCE.support_program_route_ticket_relief
    )
    account.sla_breach_risk = clamp_int(
        account.sla_breach_risk - BALANCE.support_program_route_sla_relief
    )
    account.failed_payment_risk = clamp_int(
        account.failed_payment_risk - (BALANCE.support_program_route_sla_relief // 2)
    )
    account.support_load = clamp_int(account.support_load - 2)
    account.churn_risk = clamp_int(account.churn_risk - BALANCE.support_program_route_churn_relief)
    account.renewal_health = clamp_int(account.renewal_health + 4)
    account.escalation_count = max(0, account.escalation_count - 1)
    state.support_program.escalation_queue = max(0, state.support_program.escalation_queue - 1)

    return SupportOpsActionSummary(
        message=(
            f"Routed escalation for {account.name}. "
            f"Tier {account.support_tier.value}, cash -"
            f"{BALANCE.support_program_route_escalation_cost}."
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
        + engineer_relief
        + team_lead_bonus
        + budget_capacity
    )


def _get_account_by_id(accounts: list[CustomerAccount], account_id) -> CustomerAccount:
    for account in accounts:
        if account.id == account_id:
            return account
    raise ValueError("Selected customer account was not found.")
