"""Endgame and exit evaluation for completed runs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import ExitOutcome, GameState
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.customers import calculate_account_revenue
from nexus_tech.simulation.reporting import RunScore, calculate_run_score


@dataclass(frozen=True)
class ExitEvaluation:
    """Human-readable classification of a completed run."""

    outcome: ExitOutcome
    title: str
    summary: str
    grade: str
    offer_value: Decimal


def evaluate_exit_outcome(state: GameState, score: RunScore | None = None) -> ExitEvaluation:
    """Classify the most plausible endgame path for the company."""

    score = score or calculate_run_score(state)
    account_revenue = calculate_account_revenue(state.customer_accounts)
    adjusted_value = quantize_money(score.estimated_valuation + account_revenue * Decimal("4.00"))
    grade = _calculate_grade(score.total_score, state.finance.board_confidence)

    if (
        score.total_score >= BALANCE.exit_ipo_score_threshold
        and state.finance.board_confidence >= BALANCE.board_confidence_high_threshold
    ):
        offer_value = quantize_money(adjusted_value * BALANCE.exit_ipo_value_multiplier)
        return ExitEvaluation(
            outcome=ExitOutcome.IPO_READY,
            title="IPO-Ready Operator",
            summary=(
                "The company has enough scale, governance confidence, "
                "and durable revenue to look public-market ready."
            ),
            grade=grade,
            offer_value=offer_value,
        )

    if score.total_score >= BALANCE.exit_acquisition_score_threshold:
        offer_value = quantize_money(adjusted_value * BALANCE.exit_acquisition_value_multiplier)
        return ExitEvaluation(
            outcome=ExitOutcome.STRATEGIC_ACQUISITION,
            title="Strategic Acquisition",
            summary="A larger platform could justify acquiring the portfolio and customer base.",
            grade=grade,
            offer_value=offer_value,
        )

    if state.company.cash_on_hand >= BALANCE.exit_independence_cash_threshold:
        return ExitEvaluation(
            outcome=ExitOutcome.PROFITABLE_INDEPENDENCE,
            title="Profitable Independence",
            summary="The company is not a breakout yet, but it can keep operating independently.",
            grade=grade,
            offer_value=adjusted_value,
        )

    restructure_value = quantize_money(
        max(Decimal("0.00"), adjusted_value - BALANCE.exit_restructure_cash_threshold)
    )
    return ExitEvaluation(
        outcome=ExitOutcome.RESTRUCTURE,
        title="Restructure Candidate",
        summary=(
            "The company has assets, but the run points toward consolidation or a painful reset."
        ),
        grade=grade,
        offer_value=restructure_value,
    )


def apply_exit_outcome(state: GameState) -> ExitEvaluation:
    """Evaluate and store the current run's exit classification."""

    evaluation = evaluate_exit_outcome(state)
    state.exit_outcome = evaluation.outcome
    state.exit_summary = f"{evaluation.title}: {evaluation.summary}"
    return evaluation


def _calculate_grade(total_score: int, board_confidence: int) -> str:
    adjusted_score = total_score + (board_confidence // BALANCE.board_confidence_score_divisor)
    if adjusted_score >= 270:
        return "S"
    if adjusted_score >= 220:
        return "A"
    if adjusted_score >= 170:
        return "B"
    if adjusted_score >= 120:
        return "C"
    return "D"
