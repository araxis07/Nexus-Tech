"""Board and governance pressure layered on top of finance outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.constants import ZERO_MONEY
from nexus_tech.domain.models import BoardAsk, BoardDirective, GameState
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.customers import CustomerTurnSummary
from nexus_tech.simulation.operations import OperationsSummary
from nexus_tech.simulation.support import clamp_int


@dataclass(frozen=True)
class GovernanceSummary:
    """Governance and board outcomes created at end of turn."""

    burn_multiple: Decimal
    board_pressure_delta: int
    governance_risk_delta: int
    board_review_happened: bool
    board_warning_active: bool
    board_warning_level: int
    board_directive: BoardDirective
    active_board_ask: BoardAsk
    board_ask_met: bool
    summary: str


def calculate_burn_multiple(total_revenue: Decimal, net_cash_flow: Decimal) -> Decimal:
    """Return a simple burn multiple for operating discipline review."""

    if total_revenue <= ZERO_MONEY or net_cash_flow >= ZERO_MONEY:
        return Decimal("0.00")
    return quantize_money(abs(net_cash_flow) / total_revenue)


def apply_end_of_turn_governance(
    state: GameState,
    *,
    resolved_turn: int,
    total_revenue: Decimal,
    net_cash_flow: Decimal,
    customer_summary: CustomerTurnSummary,
    operations_summary: OperationsSummary,
) -> GovernanceSummary:
    """Apply governance pressure after finance, customer, and ops signals are known."""

    finance = state.finance
    burn_multiple = calculate_burn_multiple(total_revenue, net_cash_flow)
    finance.burn_multiple = burn_multiple

    board_pressure_delta = 0
    governance_risk_delta = 0
    if burn_multiple >= BALANCE.finance_burn_multiple_warning:
        board_pressure_delta += BALANCE.finance_burn_multiple_pressure_gain
    if burn_multiple >= BALANCE.finance_burn_multiple_severe:
        governance_risk_delta += BALANCE.finance_governance_pressure_gain
    if customer_summary.at_risk_accounts > 0:
        board_pressure_delta += min(4, customer_summary.at_risk_accounts)
    if operations_summary.support_backlog >= BALANCE.support_program_backlog_reputation_threshold:
        governance_risk_delta += BALANCE.finance_governance_pressure_gain

    board_review_happened = resolved_turn % BALANCE.board_review_interval == 0
    board_ask_met = _board_ask_met(state, finance.active_board_ask, burn_multiple)
    if board_review_happened:
        finance.last_board_review_turn = resolved_turn
        if board_ask_met:
            finance.missed_board_targets = max(
                0,
                finance.missed_board_targets - BALANCE.board_ask_hit_relief,
            )
            finance.board_confidence = clamp_int(finance.board_confidence + 1)
        else:
            finance.missed_board_targets += BALANCE.board_ask_miss_penalty
            finance.board_confidence = clamp_int(finance.board_confidence - 1)
        if _board_review_failed(state, burn_multiple):
            finance.board_confidence = clamp_int(
                finance.board_confidence - BALANCE.board_review_confidence_loss
            )
            board_pressure_delta += BALANCE.board_review_pressure_gain
            governance_risk_delta += BALANCE.finance_governance_pressure_gain
        else:
            finance.board_confidence = clamp_int(
                finance.board_confidence + BALANCE.board_review_confidence_gain
            )
            board_pressure_delta -= BALANCE.board_pressure_relief
            governance_risk_delta -= BALANCE.governance_risk_relief

    finance.board_pressure = clamp_int(finance.board_pressure + board_pressure_delta)
    finance.governance_risk = clamp_int(finance.governance_risk + governance_risk_delta)
    finance.board_directive = _select_board_directive(state, burn_multiple, customer_summary)
    finance.active_board_ask = _select_board_ask(state, burn_multiple, customer_summary)
    finance.board_warning_level = _calculate_board_warning_level(finance)
    finance.board_warning_active = finance.board_warning_level > 0

    if finance.board_warning_active and finance.board_directive is BoardDirective.STABILIZE_CASH:
        finance.investor_pressure = clamp_int(finance.investor_pressure + 1)

    return GovernanceSummary(
        burn_multiple=burn_multiple,
        board_pressure_delta=board_pressure_delta,
        governance_risk_delta=governance_risk_delta,
        board_review_happened=board_review_happened,
        board_warning_active=finance.board_warning_active,
        board_warning_level=finance.board_warning_level,
        board_directive=finance.board_directive,
        active_board_ask=finance.active_board_ask,
        board_ask_met=board_ask_met,
        summary=_build_governance_summary(
            board_review_happened=board_review_happened,
            warning_active=finance.board_warning_active,
            warning_level=finance.board_warning_level,
            directive=finance.board_directive,
            active_board_ask=finance.active_board_ask,
            board_ask_met=board_ask_met,
        ),
    )


def _board_review_failed(state: GameState, burn_multiple: Decimal) -> bool:
    finance = state.finance
    support_program = state.support_program
    if finance.forecast_runway_turns is not None and (
        finance.forecast_runway_turns < BALANCE.finance_board_runway_target
    ):
        return True
    if finance.missed_board_targets > 0:
        return True
    if burn_multiple >= BALANCE.finance_burn_multiple_warning:
        return True
    return support_program.escalation_queue >= BALANCE.support_program_triage_escalation_relief * 2


def _select_board_directive(
    state: GameState,
    burn_multiple: Decimal,
    customer_summary: CustomerTurnSummary,
) -> BoardDirective:
    finance = state.finance
    if (
        finance.forecast_runway_turns is not None
        and finance.forecast_runway_turns < BALANCE.finance_board_runway_target
    ) or burn_multiple >= BALANCE.finance_burn_multiple_warning:
        return BoardDirective.STABILIZE_CASH
    if (
        state.support_program.backlog_queue >= BALANCE.support_program_backlog_reputation_threshold
        or customer_summary.at_risk_accounts > 0
    ):
        return BoardDirective.PROVE_RELIABILITY
    return BoardDirective.ACCELERATE_GROWTH


def _select_board_ask(
    state: GameState,
    burn_multiple: Decimal,
    customer_summary: CustomerTurnSummary,
) -> BoardAsk:
    finance = state.finance
    if (
        finance.forecast_runway_turns is not None
        and finance.forecast_runway_turns < BALANCE.finance_board_runway_target
    ) or burn_multiple >= BALANCE.finance_burn_multiple_warning:
        return BoardAsk.PROFITABILITY
    if (
        state.support_program.backlog_queue >= BALANCE.support_program_backlog_reputation_threshold
        or customer_summary.at_risk_accounts > 0
    ):
        return BoardAsk.RELIABILITY
    if any(
        employee.attrition_risk >= BALANCE.employee_high_attrition_risk_threshold
        for employee in state.employees
    ):
        return BoardAsk.TEAM_HEALTH
    return BoardAsk.PORTFOLIO_FOCUS


def _board_ask_met(
    state: GameState,
    board_ask: BoardAsk,
    burn_multiple: Decimal,
) -> bool:
    if board_ask is BoardAsk.PROFITABILITY:
        return (
            state.finance.forecast_runway_turns is None
            or state.finance.forecast_runway_turns >= BALANCE.finance_board_runway_target
        ) and burn_multiple < BALANCE.finance_burn_multiple_warning
    if board_ask is BoardAsk.RELIABILITY:
        return (
            state.support_program.backlog_queue
            < BALANCE.support_program_backlog_reputation_threshold
            and state.support_program.escalation_queue
            < BALANCE.support_program_triage_escalation_relief * 2
        )
    if board_ask is BoardAsk.TEAM_HEALTH:
        return not any(
            employee.attrition_risk >= BALANCE.employee_high_attrition_risk_threshold
            or employee.energy <= BALANCE.employee_burnout_energy_threshold
            for employee in state.employees
        )
    return sum(1 for product in state.products if product.is_active) <= max(2, len(state.employees))


def _calculate_board_warning_level(finance) -> int:
    if (
        finance.board_confidence <= BALANCE.board_warning_level_two_confidence_threshold
        or finance.board_pressure >= BALANCE.board_warning_level_three_pressure_threshold
        or finance.governance_risk >= BALANCE.board_warning_level_three_risk_threshold
    ):
        return 3
    if (
        finance.board_confidence <= BALANCE.board_confidence_low_threshold
        or finance.board_pressure >= BALANCE.board_warning_level_two_pressure_threshold
        or finance.governance_risk >= BALANCE.board_warning_level_two_risk_threshold
    ):
        return 2
    if (
        finance.board_confidence <= BALANCE.board_warning_level_one_confidence_threshold
        or finance.board_pressure >= BALANCE.board_pressure_warning_threshold
        or finance.governance_risk >= BALANCE.governance_risk_warning_threshold
    ):
        return 1
    return 0


def _build_governance_summary(
    *,
    board_review_happened: bool,
    warning_active: bool,
    warning_level: int,
    directive: BoardDirective,
    active_board_ask: BoardAsk,
    board_ask_met: bool,
) -> str:
    if warning_active:
        return (
            f"Board warning L{warning_level} active. "
            f"Ask: {active_board_ask.value.replace('_', ' ')}, "
            f"directive: {directive.value.replace('_', ' ')}."
        )
    if board_review_happened:
        ask_result = "met" if board_ask_met else "missed"
        return (
            f"Board review completed. Prior ask {ask_result}; "
            f"new ask: {active_board_ask.value.replace('_', ' ')}."
        )
    return (
        f"Board ask remains {active_board_ask.value.replace('_', ' ')}. "
        f"Directive: {directive.value.replace('_', ' ')}."
    )
