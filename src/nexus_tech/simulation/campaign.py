"""Campaign-style run goals for broader replayability and alternate win paths."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.domain.models import CampaignGoalId, GameState, LifecycleStage
from nexus_tech.simulation.balance import BALANCE


@dataclass(frozen=True)
class CampaignGoalDefinition:
    """One named campaign goal available to the player."""

    goal_id: CampaignGoalId
    title: str
    description: str
    success_text: str


@dataclass(frozen=True)
class CampaignGoalProgress:
    """Compact progress summary used in the dashboard and reports."""

    goal_id: CampaignGoalId
    title: str
    description: str
    progress_lines: tuple[str, ...]
    completed: bool


_CAMPAIGN_GOALS = {
    CampaignGoalId.PROFIT_MACHINE: CampaignGoalDefinition(
        goal_id=CampaignGoalId.PROFIT_MACHINE,
        title="Profit Machine",
        description=(
            "Build a resilient company that can stack profitable turns without "
            "fragile financing."
        ),
        success_text=(
            "You turned the company into a profit machine with repeatable cash flow "
            "and enough discipline to survive beyond founder luck."
        ),
    ),
    CampaignGoalId.PORTFOLIO_EMPIRE: CampaignGoalDefinition(
        goal_id=CampaignGoalId.PORTFOLIO_EMPIRE,
        title="Portfolio Empire",
        description="Scale into a true multi-product company across multiple customer segments.",
        success_text=(
            "You built a real portfolio business with enough products, users, and reach "
            "to count as a category-level platform."
        ),
    ),
    CampaignGoalId.CATEGORY_LEADER: CampaignGoalDefinition(
        goal_id=CampaignGoalId.CATEGORY_LEADER,
        title="Category Leader",
        description=(
            "Win on trust and product quality until the company becomes a market "
            "reference point."
        ),
        success_text=(
            "You earned category-leader status through product quality, mature offerings, "
            "and a brand the market now trusts."
        ),
    ),
}


def get_campaign_goal(goal_id: CampaignGoalId) -> CampaignGoalDefinition:
    """Return the definition for one campaign goal."""

    return _CAMPAIGN_GOALS[goal_id]


def list_campaign_goals() -> tuple[CampaignGoalDefinition, ...]:
    """Return all supported campaign goals for CLI presentation."""

    return tuple(_CAMPAIGN_GOALS.values())


def evaluate_campaign_goal(state: GameState) -> CampaignGoalProgress:
    """Compute progress against the current run goal."""

    definition = get_campaign_goal(state.campaign_goal_id)
    if state.campaign_goal_id is CampaignGoalId.PROFIT_MACHINE:
        return _evaluate_profit_machine(state, definition)
    if state.campaign_goal_id is CampaignGoalId.PORTFOLIO_EMPIRE:
        return _evaluate_portfolio_empire(state, definition)
    return _evaluate_category_leader(state, definition)


def check_campaign_goal_victory(state: GameState) -> str | None:
    """Return a victory reason when the active campaign goal is complete."""

    progress = evaluate_campaign_goal(state)
    if progress.completed:
        return get_campaign_goal(progress.goal_id).success_text
    return None


def _evaluate_profit_machine(
    state: GameState,
    definition: CampaignGoalDefinition,
) -> CampaignGoalProgress:
    profitable_streak = _get_profitable_streak(state)
    completed = (
        state.company.current_turn >= BALANCE.campaign_goal_profit_machine_min_turn
        and profitable_streak >= BALANCE.campaign_goal_profit_machine_streak_target
        and state.company.cash_on_hand >= BALANCE.campaign_goal_profit_machine_cash_target
        and state.finance.debt_principal <= BALANCE.campaign_goal_profit_machine_debt_cap
    )
    return CampaignGoalProgress(
        goal_id=definition.goal_id,
        title=definition.title,
        description=definition.description,
        progress_lines=(
            (
                "Profitable streak: "
                f"{profitable_streak}/{BALANCE.campaign_goal_profit_machine_streak_target}"
            ),
            (
                "Cash: "
                f"{state.company.cash_on_hand}/{BALANCE.campaign_goal_profit_machine_cash_target}"
            ),
            (
                "Debt: "
                f"{state.finance.debt_principal}/{BALANCE.campaign_goal_profit_machine_debt_cap}"
            ),
        ),
        completed=completed,
    )


def _evaluate_portfolio_empire(
    state: GameState,
    definition: CampaignGoalDefinition,
) -> CampaignGoalProgress:
    active_products = [product for product in state.products if product.is_active]
    total_users = sum(product.user_count for product in active_products)
    segment_count = len({product.target_segment for product in active_products})
    completed = (
        state.company.current_turn >= BALANCE.campaign_goal_portfolio_empire_min_turn
        and len(active_products) >= BALANCE.campaign_goal_portfolio_empire_product_target
        and total_users >= BALANCE.campaign_goal_portfolio_empire_user_target
        and segment_count >= BALANCE.campaign_goal_portfolio_empire_segment_target
    )
    return CampaignGoalProgress(
        goal_id=definition.goal_id,
        title=definition.title,
        description=definition.description,
        progress_lines=(
            (
                "Active products: "
                f"{len(active_products)}/{BALANCE.campaign_goal_portfolio_empire_product_target}"
            ),
            (
                "Portfolio users: "
                f"{total_users}/{BALANCE.campaign_goal_portfolio_empire_user_target}"
            ),
            (
                "Segments reached: "
                f"{segment_count}/{BALANCE.campaign_goal_portfolio_empire_segment_target}"
            ),
        ),
        completed=completed,
    )


def _evaluate_category_leader(
    state: GameState,
    definition: CampaignGoalDefinition,
) -> CampaignGoalProgress:
    active_products = [product for product in state.products if product.is_active]
    mature_products = sum(
        1 for product in active_products if product.lifecycle_stage is LifecycleStage.MATURE
    )
    average_quality = (
        sum(product.quality for product in active_products) // len(active_products)
        if active_products
        else 0
    )
    completed = (
        state.company.current_turn >= BALANCE.campaign_goal_category_leader_min_turn
        and state.company.reputation >= BALANCE.campaign_goal_category_leader_reputation_target
        and mature_products >= BALANCE.campaign_goal_category_leader_mature_product_target
        and average_quality >= BALANCE.campaign_goal_category_leader_quality_target
    )
    return CampaignGoalProgress(
        goal_id=definition.goal_id,
        title=definition.title,
        description=definition.description,
        progress_lines=(
            (
                "Reputation: "
                f"{state.company.reputation}/{BALANCE.campaign_goal_category_leader_reputation_target}"
            ),
            (
                "Mature products: "
                f"{mature_products}/{BALANCE.campaign_goal_category_leader_mature_product_target}"
            ),
            (
                "Avg quality: "
                f"{average_quality}/{BALANCE.campaign_goal_category_leader_quality_target}"
            ),
        ),
        completed=completed,
    )


def _get_profitable_streak(state: GameState) -> int:
    streak = 0
    for entry in reversed(state.turn_history):
        if entry.net_cash_flow > 0:
            streak += 1
            continue
        break
    return streak
