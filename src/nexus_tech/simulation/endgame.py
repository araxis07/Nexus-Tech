"""Endgame and exit evaluation for completed runs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import ExitOutcome, GameState
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.customers import calculate_account_revenue
from nexus_tech.simulation.reporting import RunScore, calculate_run_score
from nexus_tech.simulation.support_program import calculate_support_account_risk_counts


@dataclass(frozen=True)
class EndgameReadiness:
    """Relative strength of the company across plausible exit paths."""

    ipo_readiness_score: int
    acquisition_interest_score: int
    independence_score: int
    strategic_outlook: str
    summary: str


@dataclass(frozen=True)
class EndgamePressureSummary:
    """Late-game pressure profile built from exit-readiness plus operating strain."""

    public_market_scrutiny: int
    acquirer_diligence: int
    independence_discipline: int
    restructure_heat: int
    dominant_pressure: str
    active_pressures: tuple[str, ...]
    recommendation: str
    summary: str


@dataclass(frozen=True)
class ExitEvaluation:
    """Human-readable classification of a completed run."""

    outcome: ExitOutcome
    title: str
    ending_variant: str
    summary: str
    grade: str
    offer_value: Decimal
    board_readout: str
    next_chapter: str
    outcome_tags: tuple[str, ...]
    readiness: EndgameReadiness


def calculate_endgame_readiness(
    state: GameState,
    score: RunScore | None = None,
) -> EndgameReadiness:
    """Estimate how the company currently maps to major endgame paths."""

    score = score or calculate_run_score(state)
    account_revenue = calculate_account_revenue(state.customer_accounts)
    active_partnerships = [deal for deal in state.partnerships if deal.status.value != "paused"]
    unique_channels = {deal.channel.value for deal in active_partnerships}
    reserve_target_met = state.company.cash_on_hand >= state.capital_plan.reserve_target
    ipo_readiness_score = _clamp_readiness(
        (score.total_score // 3)
        + (state.finance.board_confidence // BALANCE.exit_ipo_board_score_divisor)
        + (state.finance.board_score // BALANCE.exit_ipo_board_score_divisor)
        + (score.key_accounts * BALANCE.exit_ipo_key_account_bonus)
        + (len(active_partnerships) * 2)
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
        + (len(unique_channels) * 5)
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
        + (4 if reserve_target_met else -3)
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


def calculate_endgame_pressure(
    state: GameState,
    readiness: EndgameReadiness | None = None,
) -> EndgamePressureSummary:
    """Estimate which late-game pressure is currently driving the run."""

    readiness = readiness or calculate_endgame_readiness(state)
    active_partnerships = [
        partnership for partnership in state.partnerships if partnership.status.value != "paused"
    ]
    revenue_at_risk_accounts, _ = calculate_support_account_risk_counts(state)
    average_channel_conflict = (
        sum(partnership.conflict_pressure + partnership.risk for partnership in active_partnerships)
        // len(active_partnerships)
        if active_partnerships
        else 0
    )
    reserve_gap_units = max(
        0,
        int(
            (
                max(Decimal("0.00"), state.capital_plan.reserve_target - state.company.cash_on_hand)
                / Decimal("500.00")
            ).to_integral_value()
        ),
    )
    public_market_scrutiny = _clamp_readiness(
        max(0, readiness.ipo_readiness_score - 35)
        + state.finance.governance_risk
        + (state.finance.board_pressure // 2)
        + state.support_program.sla_breaches_last_turn
    )
    acquirer_diligence = _clamp_readiness(
        max(0, readiness.acquisition_interest_score - 35)
        + average_channel_conflict
        + state.support_program.escalation_queue
        + (revenue_at_risk_accounts * 3)
    )
    independence_discipline = _clamp_readiness(
        max(0, readiness.independence_score - 35)
        + state.finance.covenant_risk
        + state.finance.investor_pressure
        + reserve_gap_units
    )
    restructure_heat = _clamp_readiness(
        (state.finance.restructuring_pressure * 4)
        + (state.finance.governance_crisis_level * 10)
        + (state.support_program.backlog_queue // 2)
    )
    pressure_scores = {
        "public_market_scrutiny": public_market_scrutiny,
        "acquirer_diligence": acquirer_diligence,
        "independence_discipline": independence_discipline,
        "restructure_heat": restructure_heat,
    }
    dominant_pressure = max(pressure_scores, key=pressure_scores.get)
    active_pressures = tuple(
        pressure_name
        for pressure_name, score in pressure_scores.items()
        if score >= BALANCE.event_strategic_crossroads_readiness_threshold
    )
    if dominant_pressure == "public_market_scrutiny":
        recommendation = (
            "Tighten controls, reporting, and support quality before telling a bigger story."
        )
        summary = "The run is leaning toward public-market scrutiny before it is fully ready."
    elif dominant_pressure == "acquirer_diligence":
        recommendation = (
            "Calm partner conflict and customer risk before buyers price in execution drag."
        )
        summary = (
            "Acquirer interest is real, but diligence risk is climbing "
            "with channel and support noise."
        )
    elif dominant_pressure == "independence_discipline":
        recommendation = (
            "Protect reserves, manage debt, and prove the company can stay independent cleanly."
        )
        summary = "The independent path is viable only if capital discipline stays credible."
    else:
        recommendation = (
            "Narrow scope, stabilize operations, and reduce governance heat before scaling again."
        )
        summary = "Operating complexity is now creating visible restructure pressure."
    return EndgamePressureSummary(
        public_market_scrutiny=public_market_scrutiny,
        acquirer_diligence=acquirer_diligence,
        independence_discipline=independence_discipline,
        restructure_heat=restructure_heat,
        dominant_pressure=dominant_pressure,
        active_pressures=active_pressures,
        recommendation=recommendation,
        summary=summary,
    )


def evaluate_exit_outcome(state: GameState, score: RunScore | None = None) -> ExitEvaluation:
    """Classify the most plausible endgame path for the company."""

    score = score or calculate_run_score(state)
    account_revenue = calculate_account_revenue(state.customer_accounts)
    adjusted_value = quantize_money(score.estimated_valuation + account_revenue * Decimal("4.00"))
    grade = _calculate_grade(score.total_score, state.finance.board_confidence)
    readiness = calculate_endgame_readiness(state, score)
    active_partnerships = [deal for deal in state.partnerships if deal.status.value != "paused"]
    unique_channels = {deal.channel.value for deal in active_partnerships}
    reserve_target_met = state.company.cash_on_hand >= state.capital_plan.reserve_target

    if (
        score.total_score >= BALANCE.exit_ipo_score_threshold
        and state.finance.board_confidence >= BALANCE.board_confidence_high_threshold
        and state.finance.governance_risk <= BALANCE.exit_ipo_governance_risk_cap
        and state.finance.restructuring_pressure <= BALANCE.exit_max_restructuring_pressure_for_win
    ):
        offer_value = quantize_money(adjusted_value * BALANCE.exit_ipo_value_multiplier)
        if state.finance.board_score >= 74 and state.finance.governance_risk <= 12:
            ending_variant = "Governance Premium Listing"
            board_readout = (
                "Directors believe the company now looks institutionally credible, not just large."
            )
            next_chapter = (
                "Preserve reporting quality, reliability, and capital discipline into public scale."
            )
            outcome_tags = ("ipo", "governance", "institutional")
        elif len(unique_channels) >= 2 and score.active_products >= 3:
            ending_variant = "Platform Roll-Up Listing"
            board_readout = (
                "The board sees a diversified platform with enough distribution breadth to list."
            )
            next_chapter = (
                "Keep the portfolio coherent, protect channel trust, and reduce integration drag."
            )
            outcome_tags = ("ipo", "portfolio", "distribution")
        else:
            ending_variant = "Flagship Scale Listing"
            board_readout = (
                "The board sees a controlled public-market narrative with room to scale."
            )
            next_chapter = "Invest in durability, reporting discipline, and flagship reliability."
            outcome_tags = ("ipo", "flagship", "scale")
        return ExitEvaluation(
            outcome=ExitOutcome.IPO_READY,
            title="IPO-Ready Operator",
            ending_variant=ending_variant,
            summary=(
                "The company has enough scale, governance confidence, "
                "and durable revenue to look public-market ready."
            ),
            grade=grade,
            offer_value=offer_value,
            board_readout=board_readout,
            next_chapter=next_chapter,
            outcome_tags=outcome_tags,
            readiness=readiness,
        )

    if score.total_score >= BALANCE.exit_acquisition_score_threshold:
        offer_value = quantize_money(adjusted_value * BALANCE.exit_acquisition_value_multiplier)
        if len(unique_channels) >= 2 and score.active_products >= 2:
            ending_variant = "Platform Roll-Up Acquisition"
            board_readout = (
                "Buyers would pay for the portfolio, partner distribution, and account footprint."
            )
            next_chapter = (
                "Increase negotiation leverage by calming support load and strengthening renewals."
            )
            outcome_tags = ("acquisition", "portfolio", "channel")
        elif len(state.employees) >= 6 and state.finance.board_team_health_score >= 68:
            ending_variant = "Talent-and-Execution Acquisition"
            board_readout = (
                "The team itself has become strategic enough to attract platform buyers."
            )
            next_chapter = (
                "Protect team health, reduce attrition exposure, and keep flagship velocity high."
            )
            outcome_tags = ("acquisition", "team", "execution")
        else:
            ending_variant = "Strategic Product Acquisition"
            board_readout = "Directors see strategic optionality and credible buyer interest."
            next_chapter = (
                "Increase negotiation leverage through cleaner revenue and calmer support load."
            )
            outcome_tags = ("acquisition", "product", "accounts")
        return ExitEvaluation(
            outcome=ExitOutcome.STRATEGIC_ACQUISITION,
            title="Strategic Acquisition",
            summary="A larger platform could justify acquiring the portfolio and customer base.",
            ending_variant=ending_variant,
            grade=grade,
            offer_value=offer_value,
            board_readout=board_readout,
            next_chapter=next_chapter,
            outcome_tags=outcome_tags,
            readiness=readiness,
        )

    if state.finance.restructuring_pressure > BALANCE.exit_max_restructuring_pressure_for_win:
        restructure_value = quantize_money(
            max(Decimal("0.00"), adjusted_value - BALANCE.exit_restructure_cash_threshold)
        )
        if state.finance.governance_crisis_active or state.finance.board_warning_level >= 3:
            ending_variant = "Board-Led Reset"
            board_readout = "The board is no longer underwriting the current operating shape."
            next_chapter = (
                "Stabilize cash, cut drag, and narrow the portfolio before growing again."
            )
            outcome_tags = ("restructure", "board", "reset")
        elif state.support_program.escalation_queue >= 6 or len(active_partnerships) >= 3:
            ending_variant = "Operational Restructure"
            board_readout = (
                "Leadership has scale assets, but delivery and service coordination broke first."
            )
            next_chapter = (
                "Reduce channel noise, simplify service promises, and restore execution control."
            )
            outcome_tags = ("restructure", "operations", "coordination")
        else:
            ending_variant = "Portfolio Consolidation"
            board_readout = (
                "The board wants a tighter company shape before it funds another scale phase."
            )
            next_chapter = "Cut weak lines, protect the core, and rebuild investor trust."
            outcome_tags = ("restructure", "portfolio", "focus")
        return ExitEvaluation(
            outcome=ExitOutcome.RESTRUCTURE,
            title="Board-Led Restructure",
            ending_variant=ending_variant,
            summary=(
                "The company still has assets, but governance pressure now points toward a "
                "forced reset before durable scale can continue."
            ),
            grade=grade,
            offer_value=restructure_value,
            board_readout=board_readout,
            next_chapter=next_chapter,
            outcome_tags=outcome_tags,
            readiness=readiness,
        )

    if state.company.cash_on_hand >= BALANCE.exit_independence_cash_threshold:
        if (
            reserve_target_met
            and state.finance.debt_principal <= Decimal("0.00")
            and state.finance.equity_dilution <= Decimal("0.1200")
        ):
            ending_variant = "Capital-Disciplined Compounder"
            board_readout = (
                "Leadership has earned an independent path with unusual capital discipline."
            )
            next_chapter = (
                "Compound renewals, protect reserves, and expand only where execution stays clean."
            )
            outcome_tags = ("independence", "capital", "discipline")
        elif score.active_products == 1:
            ending_variant = "Focused Core Operator"
            board_readout = (
                "The company is still concentrated, but the core business is durably independent."
            )
            next_chapter = (
                "Broaden the moat around the flagship before taking on more portfolio complexity."
            )
            outcome_tags = ("independence", "focus", "flagship")
        else:
            ending_variant = "Independent Portfolio Operator"
            board_readout = "Leadership has earned an independent path with disciplined execution."
            next_chapter = "Compound renewals, broaden the portfolio carefully, and defend margins."
            outcome_tags = ("independence", "portfolio", "durability")
        return ExitEvaluation(
            outcome=ExitOutcome.PROFITABLE_INDEPENDENCE,
            title="Profitable Independence",
            ending_variant=ending_variant,
            summary="The company is not a breakout yet, but it can keep operating independently.",
            grade=grade,
            offer_value=adjusted_value,
            board_readout=board_readout,
            next_chapter=next_chapter,
            outcome_tags=outcome_tags,
            readiness=readiness,
        )

    restructure_value = quantize_money(
        max(Decimal("0.00"), adjusted_value - BALANCE.exit_restructure_cash_threshold)
    )
    ending_variant = (
        "Board Reset Candidate"
        if state.finance.governance_crisis_active
        else "Fragile Consolidation Candidate"
    )
    return ExitEvaluation(
        outcome=ExitOutcome.RESTRUCTURE,
        title="Restructure Candidate",
        ending_variant=ending_variant,
        summary=(
            "The company has assets, but the run points toward consolidation or a painful reset."
        ),
        grade=grade,
        offer_value=restructure_value,
        board_readout=(
            "The company still has value, but current coordination and cash posture are unstable."
        ),
        next_chapter="Reset the operating plan before chasing another scale phase.",
        outcome_tags=("restructure", "fragile", "reset"),
        readiness=readiness,
    )


def apply_exit_outcome(state: GameState) -> ExitEvaluation:
    """Evaluate and store the current run's exit classification."""

    evaluation = evaluate_exit_outcome(state)
    state.exit_outcome = evaluation.outcome
    state.exit_summary = f"{evaluation.title} [{evaluation.ending_variant}]: {evaluation.summary}"
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
