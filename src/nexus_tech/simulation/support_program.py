"""Shared support tooling and backlog management."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.domain.models import (
    CustomerAccount,
    CustomerAccountStatus,
    GameState,
    SupportProgram,
)
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.support import clamp_int


@dataclass(frozen=True)
class SupportProgramSummary:
    """Company-wide support-system snapshot for one turn."""

    total_open_tickets: int
    effective_capacity: int
    deflected_tickets: int
    backlog_queue: int
    sla_breaches: int
    reputation_delta: int
    morale_penalty: int
    summary: str


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
    sla_breaches = sum(
        1
        for account in active_accounts
        if account.sla_breach_risk >= BALANCE.support_program_escalation_sla_threshold
    )
    ticket_relief, _ = calculate_support_program_relief(
        state.support_program,
        customer_success_bonus=customer_success_bonus,
    )
    effective_capacity = BALANCE.support_program_base_capacity + ticket_relief
    deflected_tickets = min(total_open_tickets, effective_capacity)
    queue_increase = max(0, total_open_tickets - deflected_tickets)
    queue_relief = (
        state.support_program.automation_level // BALANCE.support_program_queue_relief_divisor
    )
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue + queue_increase - queue_relief,
    )
    state.support_program.sla_breaches_last_turn = sla_breaches

    reputation_delta = 0
    morale_penalty = 0
    if state.support_program.backlog_queue >= BALANCE.support_program_backlog_reputation_threshold:
        reputation_delta = -BALANCE.support_program_backlog_reputation_loss
    if (
        state.support_program.backlog_queue
        >= BALANCE.support_program_backlog_morale_penalty_threshold
    ):
        morale_penalty = BALANCE.support_program_backlog_morale_penalty

    if not active_accounts:
        summary = "Support tooling is idle."
    elif state.support_program.backlog_queue == 0:
        summary = "Support tooling is keeping ticket flow under control."
    else:
        summary = "Support backlog is creating visible delivery and customer pressure."

    return SupportProgramSummary(
        total_open_tickets=total_open_tickets,
        effective_capacity=effective_capacity,
        deflected_tickets=deflected_tickets,
        backlog_queue=state.support_program.backlog_queue,
        sla_breaches=sla_breaches,
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
