"""One-time milestone progression for long-form business runs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from nexus_tech.domain.models import GameState, MilestoneEntry, MilestoneId
from nexus_tech.domain.money import format_money, quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.support import clamp_int


@dataclass(frozen=True)
class MilestoneDefinition:
    """Static milestone metadata and its unlock logic."""

    milestone_id: MilestoneId
    title: str
    description: str
    is_unlocked: Callable[[GameState], bool]
    apply_reward: Callable[[GameState], str]


def resolve_new_milestones(state: GameState, *, unlocked_turn: int) -> list[MilestoneEntry]:
    """Unlock and apply any newly reached milestones."""

    unlocked_ids = {entry.milestone_id for entry in state.milestone_history}
    new_entries: list[MilestoneEntry] = []

    for definition in get_milestone_registry():
        if definition.milestone_id in unlocked_ids:
            continue
        if not definition.is_unlocked(state):
            continue

        reward_text = definition.apply_reward(state)
        entry = MilestoneEntry(
            milestone_id=definition.milestone_id,
            title=definition.title,
            description=definition.description,
            unlocked_turn=unlocked_turn,
            reward_text=reward_text,
        )
        state.milestone_history.append(entry)
        new_entries.append(entry)

    return new_entries


def get_milestone_registry() -> tuple[MilestoneDefinition, ...]:
    """Return the complete set of supported progression milestones."""

    return (
        MilestoneDefinition(
            milestone_id=MilestoneId.FIRST_100_USERS,
            title="First 100 Users",
            description="Your portfolio reached its first meaningful usage milestone.",
            is_unlocked=lambda state: _get_total_users(state) >= 100,
            apply_reward=_reward_first_100_users,
        ),
        MilestoneDefinition(
            milestone_id=MilestoneId.CASH_RESERVE_12000,
            title="Cash Reserve Built",
            description="The company now has a healthier operating buffer.",
            is_unlocked=lambda state: (
                state.company.cash_on_hand >= BALANCE.cash_reserve_milestone_threshold
            ),
            apply_reward=_reward_cash_reserve,
        ),
        MilestoneDefinition(
            milestone_id=MilestoneId.TEAM_OF_4,
            title="Team Of 4",
            description="The company has grown beyond a tiny founding crew.",
            is_unlocked=lambda state: (
                len(state.employees) >= BALANCE.team_growth_milestone_headcount
            ),
            apply_reward=_reward_team_of_4,
        ),
        MilestoneDefinition(
            milestone_id=MilestoneId.THREE_ACTIVE_PRODUCTS,
            title="Portfolio Expansion",
            description="You are now carrying a meaningful multi-product portfolio.",
            is_unlocked=lambda state: (
                sum(1 for product in state.products if product.is_active)
                >= BALANCE.active_products_milestone_threshold
            ),
            apply_reward=_reward_three_active_products,
        ),
        MilestoneDefinition(
            milestone_id=MilestoneId.FIRST_MATURE_PRODUCT,
            title="First Mature Product",
            description="One of your products has reached a stable mature stage.",
            is_unlocked=lambda state: any(
                product.lifecycle_stage.value == "mature" and product.is_active
                for product in state.products
            ),
            apply_reward=_reward_first_mature_product,
        ),
    )


def _reward_first_100_users(state: GameState) -> str:
    state.company.reputation = clamp_int(
        state.company.reputation + BALANCE.milestone_first_100_users_reputation_gain
    )
    return (
        f"Reputation +{BALANCE.milestone_first_100_users_reputation_gain} "
        "from visible early traction."
    )


def _reward_cash_reserve(state: GameState) -> str:
    state.company.reputation = clamp_int(
        state.company.reputation + BALANCE.milestone_cash_reserve_reputation_gain
    )
    return (
        f"Reputation +{BALANCE.milestone_cash_reserve_reputation_gain} "
        "for building a healthier runway."
    )


def _reward_team_of_4(state: GameState) -> str:
    for employee in state.employees:
        employee.morale = clamp_int(employee.morale + BALANCE.milestone_team_growth_morale_gain)
    state.company.reputation = clamp_int(
        state.company.reputation + BALANCE.milestone_team_growth_reputation_gain
    )
    return (
        f"Reputation +{BALANCE.milestone_team_growth_reputation_gain}, "
        f"team morale +{BALANCE.milestone_team_growth_morale_gain}."
    )


def _reward_three_active_products(state: GameState) -> str:
    state.company.reputation = clamp_int(
        state.company.reputation + BALANCE.milestone_active_products_reputation_gain
    )
    return f"Reputation +{BALANCE.milestone_active_products_reputation_gain} for portfolio breadth."


def _reward_first_mature_product(state: GameState) -> str:
    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand + BALANCE.milestone_first_mature_product_cash_gain
    )
    state.company.reputation = clamp_int(
        state.company.reputation + BALANCE.milestone_first_mature_product_reputation_gain
    )
    return (
        f"Cash +{format_money(BALANCE.milestone_first_mature_product_cash_gain)}, "
        f"reputation +{BALANCE.milestone_first_mature_product_reputation_gain}."
    )


def _get_total_users(state: GameState) -> int:
    return sum(product.user_count for product in state.products if product.is_active)
