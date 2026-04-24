"""Turn history, scoring, and endgame evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.constants import ZERO_MONEY
from nexus_tech.domain.models import GameState, RoadmapFocus, TurnLedgerEntry
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.campaign import check_campaign_goal_victory, evaluate_campaign_goal
from nexus_tech.simulation.customers import calculate_account_revenue
from nexus_tech.simulation.difficulty import get_difficulty_profile


@dataclass(frozen=True)
class RunScore:
    """Computed score summary for one run."""

    total_score: int
    score_tier: str
    estimated_valuation: Decimal
    active_products: int
    mature_products: int
    total_users: int
    key_accounts: int
    campaign_grade: str


def append_turn_history(
    state: GameState,
    *,
    resolved_turn: int,
    total_revenue: Decimal,
    total_operating_cost: Decimal,
    net_cash_flow: Decimal,
    roadmap_focus: RoadmapFocus,
) -> None:
    """Append one compact turn ledger entry to the game state."""

    state.turn_history.append(
        TurnLedgerEntry(
            turn=resolved_turn,
            total_revenue=total_revenue,
            total_operating_cost=total_operating_cost,
            net_cash_flow=net_cash_flow,
            cash_on_hand=state.company.cash_on_hand,
            reputation=state.company.reputation,
            total_users=get_total_users(state),
            headcount=len(state.employees),
            roadmap_focus=roadmap_focus,
        )
    )


def calculate_run_score(state: GameState) -> RunScore:
    """Score the current run using durable business signals."""

    active_products = sum(1 for product in state.products if product.is_active)
    mature_products = sum(
        1
        for product in state.products
        if product.is_active and product.lifecycle_stage.value == "mature"
    )
    total_users = get_total_users(state)
    active_key_accounts = sum(
        1 for account in state.customer_accounts if account.status.value != "churned"
    )
    account_revenue = calculate_account_revenue(state.customer_accounts)
    total_score = (
        int((state.company.cash_on_hand / BALANCE.score_cash_divisor).to_integral_value())
        + (total_users // BALANCE.score_users_divisor)
        + (state.company.reputation * BALANCE.score_reputation_multiplier)
        + (len(state.employees) * BALANCE.score_headcount_multiplier)
        + (mature_products * BALANCE.score_mature_product_bonus)
        + (active_products * BALANCE.score_active_product_bonus)
        + (len(state.milestone_history) * BALANCE.score_milestone_bonus)
        + int((account_revenue / BALANCE.key_account_score_value_divisor).to_integral_value())
        + (state.finance.board_confidence // BALANCE.board_confidence_score_divisor)
        + get_difficulty_profile(state.difficulty_mode).score_modifier
        - int(
            (state.finance.debt_principal / BALANCE.finance_score_debt_divisor).to_integral_value()
        )
        - (state.finance.investor_pressure // BALANCE.finance_score_pressure_divisor)
        - int(
            (
                state.finance.equity_dilution * Decimal(BALANCE.finance_score_dilution_multiplier)
            ).to_integral_value()
        )
    )
    if evaluate_campaign_goal(state).completed:
        total_score += BALANCE.score_campaign_goal_bonus[state.campaign_goal_id.value]
    campaign_grade = _calculate_campaign_grade(total_score)
    if total_score >= 220:
        score_tier = "breakout"
    elif total_score >= 170:
        score_tier = "strong"
    elif total_score >= 120:
        score_tier = "stable"
    else:
        score_tier = "fragile"

    recent_revenue = state.turn_history[-1].total_revenue if state.turn_history else ZERO_MONEY
    estimated_valuation = quantize_money(
        (state.company.cash_on_hand * BALANCE.valuation_cash_multiplier)
        + (recent_revenue * BALANCE.valuation_revenue_multiplier)
        + (Decimal(total_users) * BALANCE.valuation_user_multiplier)
        + (account_revenue * BALANCE.key_account_valuation_multiplier)
        - (state.finance.debt_principal * BALANCE.finance_valuation_debt_multiplier)
    )
    estimated_valuation = quantize_money(
        estimated_valuation
        * (
            Decimal("1.00")
            - (
                state.finance.equity_dilution
                * BALANCE.finance_valuation_dilution_penalty_multiplier
            )
        )
    )
    return RunScore(
        total_score=total_score,
        score_tier=score_tier,
        estimated_valuation=estimated_valuation,
        active_products=active_products,
        mature_products=mature_products,
        total_users=total_users,
        key_accounts=active_key_accounts,
        campaign_grade=campaign_grade,
    )


def check_victory(state: GameState) -> str | None:
    """Return a victory reason when the company has reached durable scale."""

    if state.company.current_turn < BALANCE.victory_min_turn:
        return check_campaign_goal_victory(state)

    score = calculate_run_score(state)
    if (
        score.total_score >= BALANCE.victory_score_threshold
        and state.company.cash_on_hand >= BALANCE.victory_cash_threshold
        and score.total_users >= BALANCE.victory_users_threshold
        and state.company.reputation >= BALANCE.victory_reputation_threshold
        and score.active_products >= 2
        and state.finance.debt_principal <= BALANCE.victory_max_debt_threshold
        and state.finance.investor_pressure <= BALANCE.victory_max_investor_pressure
        and state.finance.restructuring_pressure <= BALANCE.exit_max_restructuring_pressure_for_win
    ):
        return (
            "You built a durable software company with enough traction, runway, "
            "and portfolio depth to count as a real winner."
        )
    return check_campaign_goal_victory(state)


def get_total_users(state: GameState) -> int:
    """Return total active users across active products."""

    return sum(product.user_count for product in state.products if product.is_active)


def _calculate_campaign_grade(total_score: int) -> str:
    if total_score >= 270:
        return "S"
    if total_score >= 220:
        return "A"
    if total_score >= 170:
        return "B"
    if total_score >= 120:
        return "C"
    return "D"
