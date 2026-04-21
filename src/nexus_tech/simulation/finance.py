"""Finance and funding systems for company capital decisions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.constants import ZERO_MONEY
from nexus_tech.domain.models import Company, FinanceState, FundingHistoryEntry, FundingType
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.support import clamp_int


@dataclass(frozen=True)
class FinanceActionSummary:
    """Result of one explicit funding or debt action."""

    message: str
    history_entry: FundingHistoryEntry


@dataclass(frozen=True)
class FinanceTurnSummary:
    """End-of-turn finance pressure and cost summary."""

    interest_cost: Decimal
    investor_pressure_cost: Decimal
    total_finance_cost: Decimal
    investor_pressure_delta: int
    runway_turns: int | None


def count_funding_rounds(
    funding_history: list[FundingHistoryEntry],
    funding_type: FundingType,
) -> int:
    """Count previously recorded rounds of one funding type."""

    return sum(1 for entry in funding_history if entry.funding_type is funding_type)


def calculate_interest_cost(finance: FinanceState) -> Decimal:
    """Per-turn debt servicing cost."""

    if finance.debt_principal <= ZERO_MONEY or finance.loan_interest_rate <= Decimal("0"):
        return ZERO_MONEY
    return quantize_money(finance.debt_principal * finance.loan_interest_rate)


def calculate_investor_pressure_cost(finance: FinanceState) -> Decimal:
    """Operating overhead caused by external capital pressure."""

    pressure_units = finance.investor_pressure // BALANCE.finance_pressure_cost_divisor
    return quantize_money(Decimal(pressure_units) * BALANCE.finance_pressure_operating_cost_unit)


def calculate_total_finance_cost(finance: FinanceState) -> Decimal:
    """Total recurring finance burden added to company burn."""

    return quantize_money(
        calculate_interest_cost(finance) + calculate_investor_pressure_cost(finance)
    )


def estimate_runway(cash_on_hand: Decimal, net_cash_flow: Decimal) -> int | None:
    """Estimate runway in turns using current cash and burn."""

    if net_cash_flow >= ZERO_MONEY:
        return None

    burn = abs(net_cash_flow)
    if burn <= ZERO_MONEY:
        return None
    return int(cash_on_hand / burn)


def apply_take_loan(
    company: Company,
    finance: FinanceState,
    *,
    current_turn: int,
) -> FinanceActionSummary:
    """Take a local loan to extend runway at the cost of recurring interest."""

    remaining_capacity = BALANCE.finance_max_total_debt - finance.debt_principal
    if remaining_capacity <= ZERO_MONEY:
        raise ValueError("The company cannot safely take more debt right now.")

    amount = min(BALANCE.finance_loan_amount, remaining_capacity)
    company.cash_on_hand = quantize_money(company.cash_on_hand + amount)
    finance.debt_principal = quantize_money(finance.debt_principal + amount)
    finance.loan_interest_rate = max(
        finance.loan_interest_rate,
        BALANCE.finance_loan_interest_rate,
    )
    finance.total_raised = quantize_money(finance.total_raised + amount)
    finance.last_funding_turn = current_turn
    finance.investor_pressure = clamp_int(
        finance.investor_pressure + BALANCE.finance_loan_pressure_gain
    )
    history_entry = FundingHistoryEntry(
        funding_type=FundingType.LOAN,
        turn=current_turn,
        amount=amount,
        debt_added=amount,
        summary="Extended runway with a local loan.",
    )
    return FinanceActionSummary(
        message=(
            f"Took a loan for {amount}. Debt is now {finance.debt_principal} "
            f"at {finance.loan_interest_rate * Decimal('100')}% turn interest."
        ),
        history_entry=history_entry,
    )


def apply_raise_angel(
    company: Company,
    finance: FinanceState,
    funding_history: list[FundingHistoryEntry],
    *,
    current_turn: int,
    reputation: int,
    total_users: int,
) -> FinanceActionSummary:
    """Raise an angel round when the company has early signal."""

    if (
        count_funding_rounds(funding_history, FundingType.ANGEL)
        >= BALANCE.finance_angel_round_limit
    ):
        raise ValueError("The company has already taken the maximum angel rounds.")
    if (
        reputation < BALANCE.finance_angel_reputation_threshold
        and total_users < BALANCE.finance_angel_user_threshold
    ):
        raise ValueError("The company needs better traction before angel funding makes sense.")

    company.cash_on_hand = quantize_money(company.cash_on_hand + BALANCE.finance_angel_raise_amount)
    finance.total_raised = quantize_money(finance.total_raised + BALANCE.finance_angel_raise_amount)
    finance.equity_dilution = min(
        Decimal("1.0000"),
        finance.equity_dilution + BALANCE.finance_angel_dilution,
    )
    finance.last_funding_turn = current_turn
    finance.investor_pressure = clamp_int(
        finance.investor_pressure + BALANCE.finance_angel_pressure_gain
    )
    history_entry = FundingHistoryEntry(
        funding_type=FundingType.ANGEL,
        turn=current_turn,
        amount=BALANCE.finance_angel_raise_amount,
        dilution_added=BALANCE.finance_angel_dilution,
        summary="Closed an angel round to fund the next growth phase.",
    )
    return FinanceActionSummary(
        message=(
            f"Closed an angel round. Cash +{BALANCE.finance_angel_raise_amount}, "
            f"dilution +{BALANCE.finance_angel_dilution * Decimal('100')}%."
        ),
        history_entry=history_entry,
    )


def apply_raise_vc(
    company: Company,
    finance: FinanceState,
    funding_history: list[FundingHistoryEntry],
    *,
    current_turn: int,
    reputation: int,
    total_users: int,
) -> FinanceActionSummary:
    """Raise a single larger venture round once the run has visible traction."""

    if count_funding_rounds(funding_history, FundingType.VENTURE) >= BALANCE.finance_vc_round_limit:
        raise ValueError("The company is not ready for another venture round.")
    if reputation < BALANCE.finance_vc_reputation_threshold:
        raise ValueError("Venture funding requires a stronger reputation first.")
    if total_users < BALANCE.finance_vc_user_threshold:
        raise ValueError("Venture funding requires a larger user base first.")

    company.cash_on_hand = quantize_money(company.cash_on_hand + BALANCE.finance_vc_raise_amount)
    finance.total_raised = quantize_money(finance.total_raised + BALANCE.finance_vc_raise_amount)
    finance.equity_dilution = min(
        Decimal("1.0000"),
        finance.equity_dilution + BALANCE.finance_vc_dilution,
    )
    finance.last_funding_turn = current_turn
    finance.investor_pressure = clamp_int(
        finance.investor_pressure + BALANCE.finance_vc_pressure_gain
    )
    history_entry = FundingHistoryEntry(
        funding_type=FundingType.VENTURE,
        turn=current_turn,
        amount=BALANCE.finance_vc_raise_amount,
        dilution_added=BALANCE.finance_vc_dilution,
        summary="Closed a venture round to scale the portfolio faster.",
    )
    return FinanceActionSummary(
        message=(
            f"Closed a venture round. Cash +{BALANCE.finance_vc_raise_amount}, "
            f"dilution +{BALANCE.finance_vc_dilution * Decimal('100')}%, "
            "but pressure from investors increases."
        ),
        history_entry=history_entry,
    )


def apply_repay_debt(
    company: Company,
    finance: FinanceState,
    *,
    current_turn: int,
) -> FinanceActionSummary:
    """Repay part of the current debt load."""

    if finance.debt_principal <= ZERO_MONEY:
        raise ValueError("The company does not have outstanding debt to repay.")

    payment = min(finance.debt_principal, BALANCE.finance_repayment_chunk)
    if company.cash_on_hand - payment < BALANCE.finance_repayment_min_cash_buffer:
        raise ValueError("Not enough cash buffer to repay debt safely this turn.")

    company.cash_on_hand = quantize_money(company.cash_on_hand - payment)
    finance.debt_principal = quantize_money(finance.debt_principal - payment)
    if finance.debt_principal == ZERO_MONEY:
        finance.loan_interest_rate = Decimal("0.0000")
    finance.investor_pressure = clamp_int(
        finance.investor_pressure - BALANCE.finance_repayment_pressure_relief
    )
    history_entry = FundingHistoryEntry(
        funding_type=FundingType.LOAN,
        turn=current_turn,
        amount=payment,
        debt_added=Decimal("0.00"),
        summary="Paid down company debt to reduce future burn.",
    )
    return FinanceActionSummary(
        message=(f"Repaid {payment} of company debt. Remaining debt is {finance.debt_principal}."),
        history_entry=history_entry,
    )


def apply_end_of_turn_finance_drift(
    finance: FinanceState,
    company: Company,
    *,
    net_cash_flow: Decimal,
) -> FinanceTurnSummary:
    """Apply passive finance pressure changes after the turn resolves."""

    interest_cost = calculate_interest_cost(finance)
    investor_pressure_cost = calculate_investor_pressure_cost(finance)
    investor_pressure_delta = 0

    if net_cash_flow < ZERO_MONEY:
        investor_pressure_delta += BALANCE.finance_pressure_increase_on_negative_cash_flow
    if finance.debt_principal >= BALANCE.finance_debt_distress_threshold:
        investor_pressure_delta += BALANCE.finance_pressure_increase_on_high_debt
    if (
        company.cash_on_hand >= BALANCE.finance_pressure_relief_cash_threshold
        and net_cash_flow >= ZERO_MONEY
    ):
        investor_pressure_delta -= BALANCE.finance_pressure_relief_on_stability

    finance.investor_pressure = clamp_int(finance.investor_pressure + investor_pressure_delta)
    board_delta = (
        BALANCE.board_confidence_positive_cashflow_gain
        if net_cash_flow >= ZERO_MONEY
        else -BALANCE.board_confidence_negative_cashflow_loss
    )
    board_delta -= finance.investor_pressure // BALANCE.board_confidence_pressure_divisor
    finance.board_confidence = clamp_int(finance.board_confidence + board_delta)

    return FinanceTurnSummary(
        interest_cost=interest_cost,
        investor_pressure_cost=investor_pressure_cost,
        total_finance_cost=quantize_money(interest_cost + investor_pressure_cost),
        investor_pressure_delta=investor_pressure_delta,
        runway_turns=estimate_runway(company.cash_on_hand, net_cash_flow),
    )
