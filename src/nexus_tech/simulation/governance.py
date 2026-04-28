"""Board and governance pressure layered on top of finance outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.constants import ZERO_MONEY
from nexus_tech.domain.models import (
    BoardAsk,
    BoardDirective,
    BoardResolution,
    GameState,
    LifecycleStage,
)
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.customers import CustomerTurnSummary
from nexus_tech.simulation.operations import OperationsSummary
from nexus_tech.simulation.support import clamp_int, clamp_rate
from nexus_tech.simulation.team import (
    clear_manager_links,
    sanitize_management_links,
    unassign_employees_from_product,
)


@dataclass(frozen=True)
class GovernanceSummary:
    """Governance and board outcomes created at end of turn."""

    burn_multiple: Decimal
    board_pressure_delta: int
    governance_risk_delta: int
    board_review_happened: bool
    board_warning_active: bool
    board_warning_level: int
    board_score: int
    board_directive: BoardDirective
    active_board_ask: BoardAsk
    board_ask_met: bool
    board_review_grade: str
    board_resolution: BoardResolution
    board_resolution_due: bool
    board_resolution_window: int
    quarterly_review_count: int
    restructuring_pressure: int
    board_recovery_turns_remaining: int
    summary: str


@dataclass(frozen=True)
class BoardResponseSummary:
    """Summary of an explicit board-response action."""

    message: str


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
    finance.board_score = _calculate_board_score(
        state,
        burn_multiple=burn_multiple,
        customer_summary=customer_summary,
        operations_summary=operations_summary,
    )

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
    board_resolution_triggered = False
    if finance.board_recovery_turns_remaining > 0:
        recovery_met = _board_ask_met(state, finance.board_recovery_focus, burn_multiple)
        if recovery_met:
            finance.board_confidence = clamp_int(
                finance.board_confidence + BALANCE.board_recovery_confidence_gain
            )
            board_pressure_delta -= BALANCE.board_recovery_pressure_relief
            governance_risk_delta -= BALANCE.board_recovery_governance_relief
        else:
            finance.missed_board_targets += BALANCE.board_recovery_miss_penalty
        finance.board_recovery_turns_remaining = max(
            0,
            finance.board_recovery_turns_remaining - 1,
        )
    if board_review_happened:
        finance.last_board_review_turn = resolved_turn
        finance.quarterly_review_count += 1
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
        finance.board_resolution = _select_board_resolution(state, burn_multiple, board_ask_met)
        if finance.board_resolution is BoardResolution.RESTRUCTURE_NOW:
            finance.restructuring_pressure = clamp_int(
                finance.restructuring_pressure + BALANCE.board_resolution_restructure_pressure_gain
            )
            board_resolution_triggered = True
        elif finance.board_resolution is BoardResolution.TARGETED_RESET:
            finance.restructuring_pressure = clamp_int(
                finance.restructuring_pressure + BALANCE.board_resolution_reset_pressure_gain
            )
            board_resolution_triggered = True
        elif finance.board_resolution is BoardResolution.BACK_GROWTH:
            finance.restructuring_pressure = clamp_int(
                finance.restructuring_pressure - BALANCE.board_resolution_growth_pressure_relief
            )
        else:
            finance.restructuring_pressure = clamp_int(finance.restructuring_pressure - 1)

    finance.board_pressure = clamp_int(finance.board_pressure + board_pressure_delta)
    finance.governance_risk = clamp_int(finance.governance_risk + governance_risk_delta)
    finance.board_directive = _select_board_directive(state, burn_multiple, customer_summary)
    finance.active_board_ask = _select_board_ask(state, burn_multiple, customer_summary)
    finance.board_warning_level = _calculate_board_warning_level(finance)
    finance.board_warning_active = finance.board_warning_level > 0
    if finance.board_warning_level >= 2 or finance.missed_board_targets >= 2:
        finance.restructuring_pressure = clamp_int(finance.restructuring_pressure + 1)
        board_resolution_triggered = True

    if finance.board_warning_active and finance.board_directive is BoardDirective.STABILIZE_CASH:
        finance.investor_pressure = clamp_int(finance.investor_pressure + 1)

    if board_review_happened and board_resolution_triggered:
        finance.board_resolution_due = True
        finance.board_resolution_window = BALANCE.board_resolution_window_turns
    elif finance.board_resolution_due and finance.board_resolution_window > 0:
        finance.board_resolution_window -= 1
        if finance.board_resolution_window == 0:
            finance.board_pressure = clamp_int(
                finance.board_pressure + BALANCE.board_resolution_expiry_pressure_gain
            )
            finance.governance_risk = clamp_int(
                finance.governance_risk + BALANCE.board_resolution_expiry_risk_gain
            )
            finance.board_confidence = clamp_int(
                finance.board_confidence - BALANCE.board_resolution_expiry_confidence_loss
            )
            finance.board_resolution_window = BALANCE.board_resolution_window_turns

    return GovernanceSummary(
        burn_multiple=burn_multiple,
        board_pressure_delta=board_pressure_delta,
        governance_risk_delta=governance_risk_delta,
        board_review_happened=board_review_happened,
        board_warning_active=finance.board_warning_active,
        board_warning_level=finance.board_warning_level,
        board_score=finance.board_score,
        board_directive=finance.board_directive,
        active_board_ask=finance.active_board_ask,
        board_ask_met=board_ask_met,
        board_review_grade=_calculate_board_review_grade(finance, burn_multiple, board_ask_met),
        board_resolution=finance.board_resolution,
        board_resolution_due=finance.board_resolution_due,
        board_resolution_window=finance.board_resolution_window,
        quarterly_review_count=finance.quarterly_review_count,
        restructuring_pressure=finance.restructuring_pressure,
        board_recovery_turns_remaining=finance.board_recovery_turns_remaining,
        summary=_build_governance_summary(
            board_review_happened=board_review_happened,
            warning_active=finance.board_warning_active,
            warning_level=finance.board_warning_level,
            board_score=finance.board_score,
            directive=finance.board_directive,
            active_board_ask=finance.active_board_ask,
            board_ask_met=board_ask_met,
            board_resolution=finance.board_resolution,
            board_resolution_due=finance.board_resolution_due,
            board_resolution_window=finance.board_resolution_window,
            recovery_focus=finance.board_recovery_focus,
            recovery_turns_remaining=finance.board_recovery_turns_remaining,
        ),
    )


def execute_board_response(state: GameState) -> BoardResponseSummary:
    """Take a direct response aligned with the current board ask."""

    finance = state.finance
    if (
        finance.board_pressure < BALANCE.board_response_min_pressure_threshold
        and not finance.board_warning_active
        and finance.missed_board_targets == 0
    ):
        raise ValueError("Board pressure is not high enough to justify a formal response.")

    ask = finance.active_board_ask
    message_suffix = ""
    if ask is BoardAsk.PROFITABILITY:
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand + BALANCE.board_response_profitability_cash_gain
        )
        for product in state.products:
            if not product.is_active:
                continue
            product.acquisition_rate = clamp_rate(
                product.acquisition_rate - BALANCE.board_response_profitability_growth_penalty
            )
        for employee in state.employees:
            employee.morale = clamp_int(
                employee.morale - BALANCE.board_response_profitability_morale_loss
            )
        finance.board_pressure = clamp_int(
            finance.board_pressure - BALANCE.board_response_profitability_pressure_relief
        )
        message_suffix = (
            f"Cash +{BALANCE.board_response_profitability_cash_gain} and growth pace cooled."
        )
    elif ask is BoardAsk.RELIABILITY:
        if state.company.cash_on_hand < BALANCE.board_response_reliability_cost:
            raise ValueError("Not enough cash to execute the reliability reset.")
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.board_response_reliability_cost
        )
        state.support_program.backlog_queue = max(
            0,
            state.support_program.backlog_queue - BALANCE.board_response_reliability_backlog_relief,
        )
        state.support_program.escalation_queue = max(
            0,
            state.support_program.escalation_queue
            - BALANCE.board_response_reliability_escalation_relief,
        )
        riskiest_product = max(
            (product for product in state.products if product.is_active),
            key=lambda product: (product.bug_level, product.technical_debt),
            default=None,
        )
        if riskiest_product is not None:
            riskiest_product.bug_level = clamp_int(
                riskiest_product.bug_level - BALANCE.board_response_reliability_bug_relief
            )
        finance.board_pressure = clamp_int(
            finance.board_pressure - BALANCE.board_response_profitability_pressure_relief
        )
        message_suffix = (
            f"Cash -{BALANCE.board_response_reliability_cost}; "
            "support queues and product risk eased."
        )
    elif ask is BoardAsk.TEAM_HEALTH:
        if state.company.cash_on_hand < BALANCE.board_response_team_health_cost:
            raise ValueError("Not enough cash to execute the team-health reset.")
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.board_response_team_health_cost
        )
        for employee in state.employees:
            employee.energy = clamp_int(
                employee.energy + BALANCE.board_response_team_health_energy_gain
            )
            employee.morale = clamp_int(
                employee.morale + BALANCE.board_response_team_health_morale_gain
            )
            employee.attrition_risk = clamp_int(
                employee.attrition_risk - BALANCE.board_response_team_health_attrition_relief
            )
        finance.board_pressure = clamp_int(
            finance.board_pressure - BALANCE.board_response_profitability_pressure_relief
        )
        message_suffix = (
            f"Cash -{BALANCE.board_response_team_health_cost}; team energy and morale recovered."
        )
    else:
        active_products = [product for product in state.products if product.is_active]
        if not active_products:
            raise ValueError("No active products remain for a portfolio-focus response.")
        weakest_product = min(
            active_products,
            key=lambda product: (product.user_count, product.market_fit, product.quality),
        )
        unassigned_count = 0
        if len(active_products) >= 2:
            weakest_product.is_active = False
            weakest_product.lifecycle_stage = LifecycleStage.SUNSET
            unassigned_count = unassign_employees_from_product(state.employees, weakest_product.id)
            state.company.reputation = clamp_int(
                state.company.reputation - BALANCE.board_response_portfolio_focus_reputation_loss
            )
            message_suffix = (
                f"Trimmed {weakest_product.name} and unassigned {unassigned_count} teammate(s)."
            )
        else:
            weakest_product.technical_debt = clamp_int(weakest_product.technical_debt - 6)
            weakest_product.market_fit = clamp_int(weakest_product.market_fit + 1)
            message_suffix = f"Focused the portfolio around {weakest_product.name}."
        finance.board_pressure = clamp_int(
            finance.board_pressure - BALANCE.board_response_portfolio_focus_pressure_relief
        )

    finance.governance_risk = clamp_int(
        finance.governance_risk - BALANCE.board_response_governance_relief
    )
    finance.board_confidence = clamp_int(
        finance.board_confidence + BALANCE.board_response_confidence_gain
    )
    finance.missed_board_targets = max(0, finance.missed_board_targets - 1)
    finance.board_resolution_due = False
    finance.board_resolution_window = 0
    finance.board_warning_level = _calculate_board_warning_level(finance)
    finance.board_warning_active = finance.board_warning_level > 0
    return BoardResponseSummary(
        message=(f"Executed a board response for {ask.value.replace('_', ' ')}. {message_suffix}")
    )


def execute_restructure_plan(state: GameState) -> BoardResponseSummary:
    """Run a board-backed restructuring response that shrinks payroll and pressure."""

    finance = state.finance
    if finance.restructuring_pressure < BALANCE.board_restructure_min_pressure:
        raise ValueError("Restructuring pressure is not high enough to justify a formal plan.")
    if not state.employees:
        raise ValueError("There is no team to restructure.")

    restructure_candidates = sorted(
        state.employees,
        key=lambda employee: (
            employee.assigned_product_id is not None,
            employee.is_team_lead,
            employee.manager_id is not None,
            employee.performance_rating,
            -employee.attrition_risk,
            employee.morale,
        ),
    )
    target_count = 2 if len(state.employees) >= 6 else 1
    removed = restructure_candidates[:target_count]
    severance_cost = quantize_money(
        BALANCE.board_restructure_severance_per_employee * Decimal(len(removed))
    )
    if state.company.cash_on_hand < severance_cost:
        raise ValueError("Not enough cash to cover restructuring severance.")

    remaining = [
        employee for employee in state.employees if employee.id not in {r.id for r in removed}
    ]
    for removed_employee in removed:
        clear_manager_links(remaining, removed_employee.id)
    sanitize_management_links(remaining)
    state.employees = remaining
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - severance_cost)
    state.company.reputation = clamp_int(
        state.company.reputation - BALANCE.board_restructure_reputation_loss
    )
    finance.restructuring_pressure = clamp_int(
        finance.restructuring_pressure - BALANCE.board_restructure_pressure_relief
    )
    finance.board_pressure = clamp_int(
        finance.board_pressure - BALANCE.board_restructure_board_pressure_relief
    )
    finance.governance_risk = clamp_int(
        finance.governance_risk - BALANCE.board_restructure_governance_relief
    )
    finance.board_resolution = BoardResolution.TARGETED_RESET
    finance.board_resolution_due = False
    finance.board_resolution_window = 0
    finance.board_warning_level = _calculate_board_warning_level(finance)
    finance.board_warning_active = finance.board_warning_level > 0

    for employee in state.employees:
        employee.morale = clamp_int(employee.morale - BALANCE.board_restructure_morale_loss)

    removed_names = ", ".join(employee.full_name for employee in removed)
    return BoardResponseSummary(
        message=(
            f"Executed a restructure plan. Removed {len(removed)} role(s): {removed_names}. "
            f"Severance -{severance_cost}."
        )
    )


def start_board_recovery_plan(state: GameState) -> BoardResponseSummary:
    """Start a short board-recovery plan focused on the current ask."""

    finance = state.finance
    if (
        finance.board_pressure < BALANCE.board_response_min_pressure_threshold
        and not finance.board_warning_active
        and finance.governance_risk < BALANCE.governance_risk_warning_threshold
    ):
        raise ValueError("Board pressure is not high enough to justify a recovery plan.")
    if finance.board_recovery_turns_remaining > 0:
        raise ValueError("A board recovery plan is already active.")
    if state.company.cash_on_hand < BALANCE.board_recovery_plan_cost:
        raise ValueError("Not enough cash to start a board recovery plan.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.board_recovery_plan_cost
    )
    finance.board_recovery_focus = finance.active_board_ask
    finance.board_recovery_turns_remaining = BALANCE.board_recovery_turns
    finance.board_pressure = clamp_int(
        finance.board_pressure - BALANCE.board_recovery_pressure_relief
    )
    finance.governance_risk = clamp_int(
        finance.governance_risk - BALANCE.board_recovery_governance_relief
    )
    finance.board_confidence = clamp_int(
        finance.board_confidence + BALANCE.board_recovery_confidence_gain
    )
    finance.board_resolution_due = False
    finance.board_resolution_window = 0
    finance.board_warning_level = _calculate_board_warning_level(finance)
    finance.board_warning_active = finance.board_warning_level > 0
    return BoardResponseSummary(
        message=(
            "Started a board recovery plan focused on "
            f"{finance.board_recovery_focus.value.replace('_', ' ')}. "
            f"Cash -{BALANCE.board_recovery_plan_cost}, "
            f"{finance.board_recovery_turns_remaining} turns committed."
        )
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


def _calculate_board_score(
    state: GameState,
    *,
    burn_multiple: Decimal,
    customer_summary: CustomerTurnSummary,
    operations_summary: OperationsSummary,
) -> int:
    finance = state.finance
    team_size = max(1, len(state.employees))
    active_products = max(1, sum(1 for product in state.products if product.is_active))
    average_energy = sum(employee.energy for employee in state.employees) // team_size
    average_morale = sum(employee.morale for employee in state.employees) // team_size
    high_attrition = sum(
        1
        for employee in state.employees
        if employee.attrition_risk >= BALANCE.employee_high_attrition_risk_threshold
    )
    profitability_score = 72
    if finance.forecast_runway_turns is not None:
        profitability_score += min(8, finance.forecast_runway_turns // 3)
    profitability_score -= int(burn_multiple * Decimal("14"))
    profitability_score -= finance.missed_board_targets * 3

    reliability_score = (
        75
        - min(28, state.support_program.backlog_queue)
        - min(18, state.support_program.escalation_queue * 3)
        - min(16, customer_summary.at_risk_accounts * 2)
        - min(12, operations_summary.support_backlog // 3)
    )
    team_health_score = (
        ((average_energy + average_morale) // 2)
        - min(18, high_attrition * 4)
        - min(12, finance.restructuring_pressure)
    )
    portfolio_focus_score = (
        74
        - max(0, active_products - max(2, team_size // 2))
        - min(14, finance.governance_risk // 4)
    )
    focus_score = {
        BoardAsk.PROFITABILITY: profitability_score,
        BoardAsk.RELIABILITY: reliability_score,
        BoardAsk.TEAM_HEALTH: team_health_score,
        BoardAsk.PORTFOLIO_FOCUS: portfolio_focus_score,
    }[finance.active_board_ask]
    blended_score = (
        profitability_score + reliability_score + team_health_score + portfolio_focus_score
    ) // 4
    return clamp_int(((focus_score * 2) + blended_score) // 3)


def _calculate_board_review_grade(
    finance,
    burn_multiple: Decimal,
    board_ask_met: bool,
) -> str:
    if finance.board_confidence >= BALANCE.board_confidence_high_threshold and board_ask_met:
        return "A"
    if burn_multiple < BALANCE.finance_burn_multiple_warning and board_ask_met:
        return "B"
    if finance.board_warning_active or finance.missed_board_targets > 0:
        return "D"
    return "C"


def _select_board_resolution(
    state: GameState,
    burn_multiple: Decimal,
    board_ask_met: bool,
) -> BoardResolution:
    finance = state.finance
    if (
        finance.board_warning_level >= 2
        or finance.missed_board_targets >= 2
        or finance.forecast_runway_turns is not None
        and finance.forecast_runway_turns < BALANCE.finance_board_runway_target
        or burn_multiple >= BALANCE.finance_burn_multiple_severe
    ):
        return BoardResolution.RESTRUCTURE_NOW
    if not board_ask_met or finance.board_pressure >= BALANCE.board_pressure_warning_threshold:
        return BoardResolution.TARGETED_RESET
    if (
        board_ask_met
        and finance.board_confidence >= BALANCE.board_confidence_high_threshold
        and burn_multiple < BALANCE.finance_burn_multiple_warning
    ):
        return BoardResolution.BACK_GROWTH
    return BoardResolution.HOLD_COURSE


def _build_governance_summary(
    *,
    board_review_happened: bool,
    warning_active: bool,
    warning_level: int,
    board_score: int,
    directive: BoardDirective,
    active_board_ask: BoardAsk,
    board_ask_met: bool,
    board_resolution: BoardResolution,
    board_resolution_due: bool,
    board_resolution_window: int,
    recovery_focus: BoardAsk,
    recovery_turns_remaining: int,
) -> str:
    recovery_summary = ""
    if recovery_turns_remaining > 0:
        recovery_summary = (
            f" Recovery plan: {recovery_focus.value.replace('_', ' ')} "
            f"for {recovery_turns_remaining} more turn(s)."
        )
    resolution_summary = ""
    if board_resolution_due:
        resolution_summary = f" Formal response due in {board_resolution_window} turn(s)."
    if warning_active:
        return (
            f"Board warning L{warning_level} active. "
            f"Score {board_score}. "
            f"Ask: {active_board_ask.value.replace('_', ' ')}, "
            f"directive: {directive.value.replace('_', ' ')}, "
            f"resolution: {board_resolution.value.replace('_', ' ')}."
            f"{resolution_summary}"
            f"{recovery_summary}"
        )
    if board_review_happened:
        ask_result = "met" if board_ask_met else "missed"
        return (
            f"Board review completed. Score {board_score}; prior ask {ask_result}; "
            f"new ask: {active_board_ask.value.replace('_', ' ')}; "
            f"resolution: {board_resolution.value.replace('_', ' ')}."
            f"{resolution_summary}"
            f"{recovery_summary}"
        )
    return (
        f"Board score {board_score}. Ask remains {active_board_ask.value.replace('_', ' ')}. "
        f"Directive: {directive.value.replace('_', ' ')}. "
        f"Resolution: {board_resolution.value.replace('_', ' ')}."
        f"{resolution_summary}"
        f"{recovery_summary}"
    )
