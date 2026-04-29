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
class EndgameReadiness:
    """Relative strength of the company across plausible exit paths."""

    ipo_readiness_score: int
    acquisition_interest_score: int
    independence_score: int
    strategic_outlook: str
    summary: str


@dataclass(frozen=True)
class ExitEvaluation:
    """Human-readable classification of a completed run."""

    outcome: ExitOutcome
    title: str
    summary: str
    grade: str
    offer_value: Decimal
    readiness: EndgameReadiness


def calculate_endgame_readiness(
    state: GameState,
    score: RunScore | None = None,
) -> EndgameReadiness:
    """Estimate how the company currently maps to major endgame paths."""

    score = score or calculate_run_score(state)
    account_revenue = calculate_account_revenue(state.customer_accounts)
    ipo_readiness_score = _clamp_readiness(
        (score.total_score // 3)
        + (state.finance.board_confidence // BALANCE.exit_ipo_board_score_divisor)
        + (state.finance.board_score // BALANCE.exit_ipo_board_score_divisor)
        + (score.key_accounts * BALANCE.exit_ipo_key_account_bonus)
        - (state.finance.governance_risk // 2)
        - (state.finance.restructuring_pressure * 3)
    )
    acquisition_interest_score = _clamp_readiness(
        int(
            (score.total_score // 4)
            + (account_revenue / BALANCE.exit_acquisition_revenue_divisor).to_integral_value()
        )
        + (score.key_accounts * BALANCE.exit_acquisition_key_account_bonus)
        + (score.active_products * 4)
        - (
            state.support_program.escalation_queue
            * BALANCE.exit_acquisition_support_penalty_divisor
        )
        - (state.finance.governance_crisis_level * 8)
    )
    independence_score = _clamp_readiness(
        int(
            (
                state.company.cash_on_hand / BALANCE.exit_independence_cash_divisor
            ).to_integral_value()
            - (
                state.finance.debt_principal / BALANCE.exit_independence_debt_divisor
            ).to_integral_value()
        )
        + (state.company.reputation // 2)
        + (state.finance.board_team_health_score // 3)
        - state.finance.investor_pressure
        - (state.finance.missed_board_targets * 4)
    )

    outlook_pairs = {
        "ipo_ready": ipo_readiness_score,
        "strategic_acquisition": acquisition_interest_score,
        "profitable_independence": independence_score,
    }
    strategic_outlook = max(outlook_pairs, key=outlook_pairs.get)
    if strategic_outlook == "ipo_ready":
        summary = (
            "Governance quality and company scale are starting to resemble a public-market story."
        )
    elif strategic_outlook == "strategic_acquisition":
        summary = "Portfolio assets and account revenue now look increasingly acquirable."
    else:
        summary = "The company currently looks strongest as an independent durable operator."

    return EndgameReadiness(
        ipo_readiness_score=ipo_readiness_score,
        acquisition_interest_score=acquisition_interest_score,
        independence_score=independence_score,
        strategic_outlook=strategic_outlook,
        summary=summary,
    )


def evaluate_exit_outcome(state: GameState, score: RunScore | None = None) -> ExitEvaluation:
    """Classify the most plausible endgame path for the company."""

    score = score or calculate_run_score(state)
    account_revenue = calculate_account_revenue(state.customer_accounts)
    adjusted_value = quantize_money(score.estimated_valuation + account_revenue * Decimal("4.00"))
    grade = _calculate_grade(score.total_score, state.finance.board_confidence)
    readiness = calculate_endgame_readiness(state, score)

    if (
        score.total_score >= BALANCE.exit_ipo_score_threshold
        and state.finance.board_confidence >= BALANCE.board_confidence_high_threshold
        and state.finance.governance_risk <= BALANCE.exit_ipo_governance_risk_cap
        and state.finance.restructuring_pressure <= BALANCE.exit_max_restructuring_pressure_for_win
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
            readiness=readiness,
        )

    if score.total_score >= BALANCE.exit_acquisition_score_threshold:
        offer_value = quantize_money(adjusted_value * BALANCE.exit_acquisition_value_multiplier)
        return ExitEvaluation(
            outcome=ExitOutcome.STRATEGIC_ACQUISITION,
            title="Strategic Acquisition",
            summary="A larger platform could justify acquiring the portfolio and customer base.",
            grade=grade,
            offer_value=offer_value,
            readiness=readiness,
        )

    if state.finance.restructuring_pressure > BALANCE.exit_max_restructuring_pressure_for_win:
        restructure_value = quantize_money(
            max(Decimal("0.00"), adjusted_value - BALANCE.exit_restructure_cash_threshold)
        )
        return ExitEvaluation(
            outcome=ExitOutcome.RESTRUCTURE,
            title="Board-Led Restructure",
            summary=(
                "The company still has assets, but governance pressure now points toward a "
                "forced reset before durable scale can continue."
            ),
            grade=grade,
            offer_value=restructure_value,
            readiness=readiness,
        )

    if state.company.cash_on_hand >= BALANCE.exit_independence_cash_threshold:
        return ExitEvaluation(
            outcome=ExitOutcome.PROFITABLE_INDEPENDENCE,
            title="Profitable Independence",
            summary="The company is not a breakout yet, but it can keep operating independently.",
            grade=grade,
            offer_value=adjusted_value,
            readiness=readiness,
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
        readiness=readiness,
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


def _clamp_readiness(score: int) -> int:
    return max(0, min(BALANCE.exit_readiness_score_cap, score))
