"""Endgame and exit evaluation for completed runs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import CapitalPlanMode, ExitOutcome, GameState
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.customers import calculate_account_revenue
from nexus_tech.simulation.partnerships import calculate_partnership_portfolio
from nexus_tech.simulation.reporting import RunScore, calculate_run_score
from nexus_tech.simulation.support_program import (
    calculate_support_account_risk_counts,
    calculate_support_account_risk_values,
    calculate_support_lane_snapshots,
    calculate_support_queue_exposure,
)


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
    support_fragility: int
    channel_fragility: int
    commercial_fragility: int
    capital_fragility: int
    board_reset_risk: int
    dominant_pressure: str
    active_pressures: tuple[str, ...]
    path_scorecard: tuple[str, ...]
    path_watchlist: tuple[str, ...]
    path_gap: int
    strategic_clarity: str
    operating_durability: str
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
    pressure_readout: str
    path_scorecard: tuple[str, ...]
    strategic_clarity: str
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
    portfolio = calculate_partnership_portfolio(state)
    revenue_at_risk_accounts, _ = calculate_support_account_risk_counts(state)
    revenue_at_risk_value, renewal_pressure_value = calculate_support_account_risk_values(state)
    queue_exposure = calculate_support_queue_exposure(state)
    lane_overflow_pressure = sum(
        snapshot.overflow for snapshot in calculate_support_lane_snapshots(state).values()
    )
    premium_breach_weight = sum(
        1
        for account in state.customer_accounts
        if account.support_tier.value in {"priority", "white_glove"}
        and account.sla_breach_risk >= state.support_program.sla_target
    )
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
    reserve_share_shortfall = max(
        0,
        BALANCE.capital_plan_low_reserve_share_threshold - state.capital_plan.reserve_share,
    )
    support_fragility = _clamp_readiness(
        (revenue_at_risk_accounts * 4)
        + (state.support_program.sla_breaches_last_turn * 3)
        + lane_overflow_pressure
        + queue_exposure.focus_alignment_gap
        + (
            int(
                (
                    renewal_pressure_value / BALANCE.exit_support_fragility_value_divisor
                ).to_integral_value()
            )
        )
        + (state.support_program.queue_age_pressure // BALANCE.support_program_queue_age_threshold)
        + (
            (
                state.support_program.sla_breaches_last_turn
                + max(0, state.support_program.escalation_queue // 2)
            )
            if state.support_program.escalation_queue > 0
            else 0
        )
        + (premium_breach_weight * BALANCE.exit_support_fragility_premium_breach_weight)
        + int(
            (
                queue_exposure.enterprise_queue_exposure_value
                / BALANCE.exit_support_fragility_value_divisor
            ).to_integral_value()
        )
        + queue_exposure.white_glove_queue_risk_accounts
        + queue_exposure.hotspot_lane_account_count
        + (queue_exposure.lane_saturation_index // BALANCE.support_program_queue_age_threshold)
    )
    channel_fragility = _clamp_readiness(
        portfolio.average_fatigue
        + portfolio.channel_dependency_risk
        + portfolio.renegotiation_pressure
        + (portfolio.direct_sales_conflict_accounts * 2)
        + (
            portfolio.fatigued_revenue_share_percent
            // BALANCE.exit_channel_fragility_revenue_share_divisor
        )
        + (
            BALANCE.exit_channel_fragility_dependency_bonus
            if portfolio.paused_revenue_share_percent
            >= BALANCE.commercial_pressure_paused_share_threshold
            else 0
        )
        + (
            portfolio.rev_share_pressure
            // BALANCE.exit_channel_fragility_rev_share_pressure_divisor
        )
        + portfolio.recovery_drag_score
        + (
            portfolio.paused_dependency_score
            // BALANCE.exit_channel_fragility_rev_share_pressure_divisor
        )
        + (
            portfolio.hotspot_revenue_share_percent
            // BALANCE.exit_channel_fragility_revenue_share_divisor
        )
    )
    board_reset_risk = _clamp_readiness(
        (state.finance.restructuring_pressure * 4)
        + (state.finance.governance_crisis_level * 12)
        + (state.finance.board_warning_level * BALANCE.exit_board_reset_warning_weight)
        + (support_fragility // 2)
        + (channel_fragility // 3)
        + (8 if state.finance.board_resolution_due else 0)
    )
    public_market_scrutiny = _clamp_readiness(
        max(0, readiness.ipo_readiness_score - 35)
        + state.finance.governance_risk
        + (state.finance.board_pressure // 2)
        + state.support_program.sla_breaches_last_turn
        + (support_fragility // 4)
        + (queue_exposure.lane_saturation_index // BALANCE.support_program_queue_age_threshold)
        + (
            queue_exposure.hotspot_lane_overflow
            if queue_exposure.hotspot_lane.value == "enterprise"
            else 0
        )
        + (
            queue_exposure.focus_alignment_gap // BALANCE.exit_public_market_focus_mismatch_divisor
            if queue_exposure.hotspot_lane.value == "enterprise"
            else 0
        )
        + (queue_exposure.enterprise_queue_risk_accounts * 2)
    )
    acquirer_diligence = _clamp_readiness(
        max(0, readiness.acquisition_interest_score - 35)
        + average_channel_conflict
        + state.support_program.escalation_queue
        + (revenue_at_risk_accounts * 3)
        + (6 if state.finance.board_resolution_due else 0)
        + (channel_fragility // 4)
        + (
            portfolio.paused_dependency_score
            // BALANCE.exit_channel_fragility_revenue_share_divisor
        )
        + (
            portfolio.hotspot_revenue_share_percent
            // BALANCE.exit_channel_fragility_revenue_share_divisor
        )
        + (
            portfolio.hotspot_dependency_score
            // BALANCE.exit_channel_fragility_revenue_share_divisor
        )
        + (portfolio.paused_count * BALANCE.exit_acquirer_paused_channel_weight)
        + (portfolio.direct_sales_conflict_accounts // 2)
    )
    if portfolio.hotspot_channel == "integration":
        acquirer_diligence = _clamp_readiness(
            acquirer_diligence
            + (
                portfolio.recovery_drag_score
                // BALANCE.exit_channel_fragility_rev_share_pressure_divisor
            )
        )
    elif portfolio.hotspot_channel == "reseller":
        acquirer_diligence = _clamp_readiness(
            acquirer_diligence + portfolio.direct_sales_conflict_accounts
        )
    elif portfolio.hotspot_channel == "marketplace":
        acquirer_diligence = _clamp_readiness(
            acquirer_diligence
            + (
                portfolio.rev_share_pressure
                // BALANCE.exit_channel_fragility_rev_share_pressure_divisor
            )
        )
    independence_discipline = _clamp_readiness(
        max(0, readiness.independence_score - 35)
        + state.finance.covenant_risk
        + state.finance.investor_pressure
        + reserve_gap_units
        + (reserve_share_shortfall * BALANCE.exit_independence_low_reserve_share_weight)
        + (4 if state.finance.debt_principal > Decimal("0.00") and reserve_gap_units > 0 else 0)
        + (
            3
            if (
                state.finance.debt_principal >= BALANCE.finance_debt_rollover_min_debt
                and state.finance.covenant_risk >= 12
            )
            else 0
        )
        + (support_fragility // 5)
        + int(
            (
                queue_exposure.renewal_queue_exposure_value
                / BALANCE.exit_support_fragility_value_divisor
            ).to_integral_value()
        )
        + (
            queue_exposure.hotspot_lane_overflow
            if queue_exposure.hotspot_lane.value == "billing"
            else 0
        )
        + (
            queue_exposure.focus_alignment_gap
            if queue_exposure.hotspot_lane.value == "billing"
            else 0
        )
    )
    restructure_heat = _clamp_readiness(
        (state.finance.restructuring_pressure * 4)
        + (state.finance.governance_crisis_level * 10)
        + (state.support_program.backlog_queue // 2)
        + (6 if state.finance.board_resolution_due else 0)
        + (board_reset_risk // 3)
    )
    commercial_fragility = _clamp_readiness(
        (support_fragility // BALANCE.exit_commercial_fragility_support_divisor)
        + (channel_fragility // BALANCE.exit_commercial_fragility_channel_divisor)
        + (revenue_at_risk_accounts * 2)
        + (portfolio.volatile_revenue_share_percent // 6)
        + int(
            (
                queue_exposure.renewal_queue_exposure_value
                / BALANCE.exit_support_fragility_value_divisor
            ).to_integral_value()
        )
        + (portfolio.recovery_drag_score // BALANCE.exit_commercial_fragility_channel_divisor)
    )
    capital_fragility = _clamp_readiness(
        independence_discipline
        + (board_reset_risk // BALANCE.exit_capital_fragility_pressure_divisor)
        + int(
            (
                state.finance.debt_principal / BALANCE.exit_capital_fragility_debt_divisor
            ).to_integral_value()
        )
        + reserve_gap_units
    )
    pressure_scores = {
        "public_market_scrutiny": public_market_scrutiny,
        "acquirer_diligence": acquirer_diligence,
        "independence_discipline": independence_discipline,
        "restructure_heat": restructure_heat,
    }
    sorted_readiness = sorted(
        (
            ("ipo_ready", readiness.ipo_readiness_score),
            ("strategic_acquisition", readiness.acquisition_interest_score),
            ("profitable_independence", readiness.independence_score),
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    path_gap = sorted_readiness[0][1] - sorted_readiness[1][1]
    if path_gap >= BALANCE.exit_path_clarity_gap_threshold and commercial_fragility <= 34:
        strategic_clarity = "clear path"
    elif path_gap >= BALANCE.exit_path_clarity_gap_threshold:
        strategic_clarity = "clear but stressed"
    else:
        strategic_clarity = "contested"
    max_fragility = max(commercial_fragility, capital_fragility, board_reset_risk)
    if max_fragility <= BALANCE.exit_operating_durability_resilient_threshold:
        operating_durability = "resilient"
    elif max_fragility <= BALANCE.exit_operating_durability_stretched_threshold:
        operating_durability = "stretched"
    else:
        operating_durability = "fragile"
    dominant_pressure = max(pressure_scores, key=pressure_scores.get)
    active_pressures = tuple(
        pressure_name
        for pressure_name, score in pressure_scores.items()
        if score >= BALANCE.event_strategic_crossroads_readiness_threshold
    )
    reset_lane_label = {
        "enterprise": "enterprise proof and white-glove service",
        "billing": "billing collections and renewal cash",
        "onboarding": "onboarding go-live drag",
        "balanced": "general operating drag",
    }[queue_exposure.hotspot_lane.value]
    reset_channel_note = (
        f" and de-risk the {portfolio.hotspot_channel} channel"
        if portfolio.hotspot_channel != "-"
        else ""
    )
    path_watchlist = (
        (
            "IPO: run enterprise assurance, an enterprise queue reset, white-glove recovery, "
            "a reference rescue, onboarding fast track or lane recovery on implementation drag, "
            "and a renewal sweep on enterprise revenue before inviting more scrutiny."
            if (
                public_market_scrutiny >= 56
                or support_fragility >= 32
                or queue_exposure.hotspot_lane.value == "enterprise"
            )
            else "IPO: institutional controls currently look serviceable."
        ),
        (
            (
                f"M&A: calm {portfolio.hotspot_channel} concentration, "
                "run a channel QBR, conflict reset, synergy reset, partner margin reset, "
                "realignment, firebreak, recovery sprint, or rebalance the mix, and calm "
                "renewal risk before diligence deepens."
            )
            if (
                acquirer_diligence >= 56
                or channel_fragility >= 40
                or portfolio.hotspot_revenue_share_percent >= 35
            )
            else "M&A: buyer diligence pressure is currently contained."
        ),
        (
            (
                "Independence: raise the reserve target, step up reserve discipline, harden "
                "financing posture, lock a capital buffer, roll debt forward if needed, and run "
                "billing stabilization before compounding harder."
            )
            if (
                independence_discipline >= 56
                or capital_fragility >= 40
                or queue_exposure.hotspot_lane.value == "billing"
            )
            else "Independence: capital discipline is currently holding."
        ),
        (
            (
                f"Reset: protect {reset_lane_label}, hold reserve share at "
                f"{state.capital_plan.reserve_share}%, close the pending board resolution"
                f"{reset_channel_note}, and only reopen growth after the reset queue is calm."
            )
            if board_reset_risk >= 60 or restructure_heat >= 56
            else (
                f"Reset: restructure pressure is real, but {reset_lane_label} has not forced "
                "a full board reset yet."
            )
        ),
    )
    if board_reset_risk >= 70:
        reset_watch_action = {
            "enterprise": "run an enterprise reference watch or white-glove retention watch",
            "billing": "run a billing renewal watch",
            "onboarding": "run an onboarding go-live watch",
            "balanced": "run the highest-risk account watch",
        }[queue_exposure.hotspot_lane.value]
        recommendation = (
            f"Board reset risk is high. {reset_watch_action} on the hotspot account, use lane "
            "meshes where pressure is broad, force a path cash waterfall, add a board-reset "
            "contingency buffer, de-risk the hotspot channel, and prepare to accept a tighter "
            "reset plan before the board forces one."
        )
        summary = "Governance and operating strain are now close to forcing a board-led reset."
    elif commercial_fragility >= 70:
        recommendation = (
            "Commercial fragility is now the main late-game constraint. "
            "Run a renewal sweep, use enterprise, onboarding, or billing recovery where needed, "
            "and de-risk channel revenue with a firebreak before scaling again."
        )
        summary = (
            "Late-game pressure is now being driven by service and channel fragility together."
        )
    elif capital_fragility >= 66:
        recommendation = (
            "Capital fragility is now the main late-game constraint. "
            "Tighten reserve discipline, lock a capital buffer, and harden financing posture "
            "before pursuing another scale step."
        )
        summary = "Late-game pressure is now driven by cash discipline, debt, and board heat."
    elif dominant_pressure == "public_market_scrutiny":
        recommendation = (
            "Tighten controls, reporting, and enterprise support quality "
            "before telling a bigger story."
        )
        if (
            queue_exposure.focus_alignment_gap > 0
            and queue_exposure.hotspot_lane.value == "enterprise"
        ):
            recommendation = (
                "Run enterprise assurance, an enterprise lane mesh, an enterprise reference "
                "watch, white-glove recovery, or a white-glove retention watch, add a reference "
                "rescue or enterprise queue reset if the flagship lane is still clogged, tighten "
                "controls, and prove reliability before telling a bigger story."
            )
        summary = "The run is leaning toward public-market scrutiny before it is fully ready."
    elif dominant_pressure == "acquirer_diligence":
        recommendation = (
            "Calm partner conflict, hotspot concentration, and customer risk "
            "before buyers price in execution drag."
        )
        if (
            portfolio.hotspot_dependency_score
            >= BALANCE.finance_planner_reactivate_dependency_threshold
        ):
            recommendation = (
                "Run a channel QBR, conflict reset, synergy reset, partner margin reset, "
                "realignment, or firebreak, then rebalance, pause, or renegotiate the hotspot "
                "channel before buyers price in execution drag."
            )
        summary = (
            "Acquirer interest is real, but diligence risk is climbing "
            "with channel and support noise."
        )
    elif dominant_pressure == "independence_discipline":
        recommendation = (
            "Protect reserves, manage debt, and keep billing or renewal pressure "
            "from breaking independence."
        )
        if (
            queue_exposure.hotspot_lane.value == "billing"
            and queue_exposure.focus_alignment_gap > 0
        ):
            recommendation = (
                "Move support focus into billing, run a billing lane mesh or billing renewal "
                "watch, raise the reserve target, step up reserve discipline, harden financing "
                "posture, lock a capital buffer, roll debt forward if needed, and keep renewal "
                "pressure from breaking independence."
            )
        summary = "The independent path is viable only if capital discipline stays credible."
    else:
        recommendation = (
            "Narrow scope, stabilize operations, and reduce governance heat before scaling again."
        )
        summary = "Operating complexity is now creating visible restructure pressure."
    if board_reset_risk >= 60 or restructure_heat >= 56:
        path_watchlist = (
            path_watchlist[0],
            path_watchlist[1],
            path_watchlist[2],
            (
                f"Reset: force a path cash waterfall, add a board-reset contingency buffer, "
                f"protect {reset_lane_label}, use targeted watches where one account still "
                f"dominates{reset_channel_note}, and ratify reset controls before another board "
                "cycle hardens the reset."
            ),
        )
    path_scorecard = (
        f"IPO {readiness.ipo_readiness_score} / scrutiny {public_market_scrutiny}",
        f"M&A {readiness.acquisition_interest_score} / diligence {acquirer_diligence}",
        f"Ind {readiness.independence_score} / discipline {independence_discipline}",
        (
            f"Reset {restructure_heat} / board risk {board_reset_risk} / reserve "
            f"{state.capital_plan.reserve_share}% / {queue_exposure.hotspot_lane.value} lane / "
            f"{'resolution due' if state.finance.board_resolution_due else 'resolution buffered'}"
        ),
    )
    return EndgamePressureSummary(
        public_market_scrutiny=public_market_scrutiny,
        acquirer_diligence=acquirer_diligence,
        independence_discipline=independence_discipline,
        restructure_heat=restructure_heat,
        support_fragility=support_fragility,
        channel_fragility=channel_fragility,
        board_reset_risk=board_reset_risk,
        dominant_pressure=dominant_pressure,
        active_pressures=active_pressures,
        path_scorecard=path_scorecard,
        path_watchlist=path_watchlist,
        path_gap=path_gap,
        strategic_clarity=strategic_clarity,
        operating_durability=operating_durability,
        recommendation=recommendation,
        summary=summary,
        commercial_fragility=commercial_fragility,
        capital_fragility=capital_fragility,
    )


def evaluate_exit_outcome(state: GameState, score: RunScore | None = None) -> ExitEvaluation:
    """Classify the most plausible endgame path for the company."""

    score = score or calculate_run_score(state)
    account_revenue = calculate_account_revenue(state.customer_accounts)
    adjusted_value = quantize_money(score.estimated_valuation + account_revenue * Decimal("4.00"))
    grade = _calculate_grade(score.total_score, state.finance.board_confidence)
    readiness = calculate_endgame_readiness(state, score)
    pressure = calculate_endgame_pressure(state, readiness)
    active_partnerships = [deal for deal in state.partnerships if deal.status.value != "paused"]
    portfolio = calculate_partnership_portfolio(state)
    queue_exposure = calculate_support_queue_exposure(state)
    revenue_at_risk_accounts, renewal_pressure_accounts = calculate_support_account_risk_counts(
        state
    )
    unique_channels = {deal.channel.value for deal in active_partnerships}
    reserve_target_met = state.company.cash_on_hand >= state.capital_plan.reserve_target
    pressure_readout = f"{pressure.dominant_pressure.replace('_', ' ')}: {pressure.recommendation}"

    if (
        score.total_score >= BALANCE.exit_ipo_score_threshold
        and state.finance.board_confidence >= BALANCE.board_confidence_high_threshold
        and state.finance.governance_risk <= BALANCE.exit_ipo_governance_risk_cap
        and state.finance.restructuring_pressure <= BALANCE.exit_max_restructuring_pressure_for_win
    ):
        offer_value = quantize_money(adjusted_value * BALANCE.exit_ipo_value_multiplier)
        if (
            pressure.commercial_fragility <= 18
            and pressure.capital_fragility <= 16
            and pressure.path_gap >= BALANCE.exit_path_clarity_gap_threshold
        ):
            ending_variant = "Institutional Quality Listing"
            board_readout = (
                "The board sees a public-market story backed by clean "
                "commercial execution and capital control."
            )
            next_chapter = (
                "Protect institutional discipline while scaling without "
                "letting support or channels drift."
            )
            outcome_tags = ("ipo", "institutional", "capital")
        elif (
            pressure.support_fragility <= 16
            and state.finance.board_reliability_score >= 78
            and score.key_accounts >= 2
        ):
            ending_variant = "Customer-Trust Listing"
            board_readout = (
                "The board believes enterprise trust held up strongly enough to support a listing."
            )
            next_chapter = (
                "Protect flagship reliability and support discipline "
                "while public expectations harden."
            )
            outcome_tags = ("ipo", "customer_trust", "enterprise")
        elif (
            queue_exposure.hotspot_lane.value == "enterprise"
            and state.support_program.lane_focus.value == "enterprise"
            and pressure.support_fragility <= 22
            and queue_exposure.focus_alignment_gap == 0
        ):
            ending_variant = "Enterprise-Control Listing"
            board_readout = (
                "The board sees a listing story supported by disciplined enterprise operations."
            )
            next_chapter = (
                "Hold enterprise reliability and support focus while scrutiny intensifies."
            )
            outcome_tags = ("ipo", "enterprise", "controls")
        elif (
            pressure.public_market_scrutiny >= 70
            and pressure.support_fragility <= 28
            and state.finance.governance_risk <= 16
        ):
            ending_variant = "Scrutiny-Tested Listing"
            board_readout = (
                "The board believes the company can survive scrutiny "
                "because operations stayed tight."
            )
            next_chapter = (
                "Hold support quality and reporting discipline while public expectations rise."
            )
            outcome_tags = ("ipo", "scrutiny", "operations")
        elif state.finance.board_score >= 74 and state.finance.governance_risk <= 12:
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
            pressure_readout=pressure_readout,
            path_scorecard=pressure.path_scorecard,
            strategic_clarity=pressure.strategic_clarity,
            next_chapter=next_chapter,
            outcome_tags=outcome_tags,
            readiness=readiness,
        )

    if score.total_score >= BALANCE.exit_acquisition_score_threshold:
        offer_value = quantize_money(adjusted_value * BALANCE.exit_acquisition_value_multiplier)
        if (
            pressure.operating_durability == "resilient"
            and pressure.path_gap >= BALANCE.exit_path_clarity_gap_threshold
            and portfolio.channel_volatility_index <= 42
        ):
            ending_variant = "Synergy Premium Acquisition"
            board_readout = (
                "Buyer interest carries a premium because the channel stack "
                "and support operations both survived scale cleanly."
            )
            next_chapter = (
                "Protect diligence quality and integration readiness so the premium holds."
            )
            outcome_tags = ("acquisition", "premium", "synergy")
        elif pressure.channel_fragility >= 62:
            ending_variant = "Diligence-Discounted Acquisition"
            board_readout = (
                "Buyer interest is credible, but channel and support noise "
                "are now trimming the premium."
            )
            next_chapter = (
                "Calm partner fatigue and renewal stress before taking the company back to market."
            )
            outcome_tags = ("acquisition", "diligence", "discounted")
        elif (
            portfolio.hotspot_channel == "integration"
            and portfolio.hotspot_dependency_score < 64
            and pressure.channel_fragility <= 42
        ):
            ending_variant = "Integration-Leverage Acquisition"
            board_readout = (
                "Buyers would pay for integration depth because the hottest channel still held."
            )
            next_chapter = (
                "Keep integration partners stable and reduce dependency before full diligence."
            )
            outcome_tags = ("acquisition", "integration", "leverage")
        elif (
            portfolio.hotspot_channel != "-"
            and portfolio.sourced_revenue >= Decimal("2500.00")
            and pressure.channel_fragility <= 44
        ):
            ending_variant = "Distribution-Led Acquisition"
            board_readout = (
                "Buyers would pay for the distribution machine because "
                "the channel stack stayed usable."
            )
            next_chapter = (
                "Protect partner economics and renewal health so "
                "channel leverage keeps its premium."
            )
            outcome_tags = ("acquisition", "distribution", portfolio.hotspot_channel)
        elif len(unique_channels) >= 2 and score.active_products >= 2:
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
            outcome_tags = (
                "acquisition",
                "product",
                "renewals" if renewal_pressure_accounts > 0 else "accounts",
            )
        return ExitEvaluation(
            outcome=ExitOutcome.STRATEGIC_ACQUISITION,
            title="Strategic Acquisition",
            summary="A larger platform could justify acquiring the portfolio and customer base.",
            ending_variant=ending_variant,
            grade=grade,
            offer_value=offer_value,
            board_readout=board_readout,
            pressure_readout=pressure_readout,
            path_scorecard=pressure.path_scorecard,
            strategic_clarity=pressure.strategic_clarity,
            next_chapter=next_chapter,
            outcome_tags=outcome_tags,
            readiness=readiness,
        )

    if state.finance.restructuring_pressure > BALANCE.exit_max_restructuring_pressure_for_win:
        restructure_value = quantize_money(
            max(Decimal("0.00"), adjusted_value - BALANCE.exit_restructure_cash_threshold)
        )
        if (
            pressure.board_reset_risk >= 72
            and state.capital_plan.mode is CapitalPlanMode.CONSERVE
            and state.capital_plan.reserve_share >= 34
            and not state.finance.board_resolution_due
        ):
            ending_variant = "Controlled Recovery Reset"
            board_readout = (
                "Directors forced a reset, but the company answered with a credible recovery "
                "perimeter around cash, lane pressure, and governance."
            )
            next_chapter = (
                "Keep reserve share high, defend the hotspot lane, and reopen growth only after "
                "the reset path stays quiet for several turns."
            )
            outcome_tags = ("restructure", "board", "recovery")
        elif pressure.capital_fragility >= 72:
            ending_variant = "Liquidity Containment Reset"
            board_readout = (
                "Directors now see cash discipline and operating strain "
                "as one linked reset problem."
            )
            next_chapter = (
                "Shrink burn, protect renewals, and rebuild the balance "
                "sheet before chasing scale again."
            )
            outcome_tags = ("restructure", "liquidity", "containment")
        elif pressure.board_reset_risk >= 72:
            ending_variant = "Board Reset Mandate"
            board_readout = (
                "Directors have moved from warnings to reset logic "
                "because pressure now spans the whole system."
            )
            next_chapter = (
                "Protect cash, narrow the company shape, and rebuild trust before reopening growth."
            )
            outcome_tags = ("restructure", "board", "mandate")
        elif state.finance.governance_crisis_active or state.finance.board_warning_level >= 3:
            ending_variant = "Board-Led Reset"
            board_readout = "The board is no longer underwriting the current operating shape."
            next_chapter = (
                "Stabilize cash, cut drag, and narrow the portfolio before growing again."
            )
            outcome_tags = ("restructure", "board", "reset")
        elif pressure.support_fragility >= 60 or pressure.channel_fragility >= 60:
            ending_variant = "Commercial Containment Reset"
            board_readout = (
                "The board sees support and channel strain bleeding into the whole company shape."
            )
            next_chapter = (
                "Contain renewals, simplify support promises, and shrink fragile channel exposure."
            )
            outcome_tags = ("restructure", "commercial", "containment")
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
            pressure_readout=pressure_readout,
            path_scorecard=pressure.path_scorecard,
            strategic_clarity=pressure.strategic_clarity,
            next_chapter=next_chapter,
            outcome_tags=outcome_tags,
            readiness=readiness,
        )

    if state.company.cash_on_hand >= BALANCE.exit_independence_cash_threshold:
        if (
            pressure.capital_fragility <= 18
            and pressure.path_gap >= BALANCE.exit_path_clarity_gap_threshold
            and reserve_target_met
        ):
            ending_variant = "Capital-Disciplined Compounder"
            board_readout = (
                "Leadership earned independence by pairing reserve control "
                "with a clean strategic path."
            )
            next_chapter = (
                "Compound the strongest customer motions without letting capital posture drift."
            )
            outcome_tags = ("independence", "capital", "clarity")
        elif (
            queue_exposure.hotspot_lane.value == "billing"
            and queue_exposure.focus_alignment_gap == 0
            and pressure.capital_fragility <= 22
            and reserve_target_met
        ):
            ending_variant = "Collections-Disciplined Compounder"
            board_readout = (
                "Leadership earned independence by keeping billing and reserves under control."
            )
            next_chapter = (
                "Keep billing discipline tight while compounding only the healthiest renewals."
            )
            outcome_tags = ("independence", "billing", "discipline")
        elif (
            pressure.operating_durability == "resilient"
            and pressure.commercial_fragility <= 22
            and revenue_at_risk_accounts == 0
        ):
            ending_variant = "Trust-Backed Compounder"
            board_readout = (
                "Leadership earned independence through unusually clean customer operations."
            )
            next_chapter = (
                "Keep renewals clean, service promises credible, "
                "and scale only along healthy lanes."
            )
            outcome_tags = ("independence", "trust", "operations")
        elif (
            reserve_target_met
            and state.finance.debt_principal <= Decimal("0.00")
            and state.finance.equity_dilution <= Decimal("0.1200")
            and pressure.support_fragility <= 24
        ):
            ending_variant = "Reserve-Backed Compounder"
            board_readout = (
                "Leadership has earned an independent path with unusual capital discipline."
            )
            next_chapter = (
                "Compound renewals, protect reserves, and expand only where execution stays clean."
            )
            outcome_tags = ("independence", "capital", "reserves")
        elif pressure.support_fragility <= 18 and score.key_accounts >= 2:
            ending_variant = "Service-Led Compounder"
            board_readout = (
                "The company earned independence by keeping support trust "
                "and renewals unusually clean."
            )
            next_chapter = (
                "Keep service quality high while expanding only the healthiest customer motions."
            )
            outcome_tags = ("independence", "service", "retention")
        elif pressure.independence_discipline >= 68:
            ending_variant = "Discipline Under Load"
            board_readout = (
                "The company stayed independent even while debt, reserves, "
                "and delivery stayed in tension."
            )
            next_chapter = (
                "Turn discipline into a cleaner operating model before reopening the pace of bets."
            )
            outcome_tags = ("independence", "discipline", "pressure")
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
            pressure_readout=pressure_readout,
            path_scorecard=pressure.path_scorecard,
            strategic_clarity=pressure.strategic_clarity,
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
        pressure_readout=pressure_readout,
        path_scorecard=pressure.path_scorecard,
        strategic_clarity=pressure.strategic_clarity,
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
