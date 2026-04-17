"""One-time milestone progression for long-form business runs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from nexus_tech.domain.models import GameState, MilestoneEntry, MilestoneId
from nexus_tech.domain.money import format_money, quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.operations import calculate_operations_summary
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
        MilestoneDefinition(
            milestone_id=MilestoneId.PROFITABLE_STREAK,
            title="Profitable Streak",
            description="The company posted several positive turns in a row.",
            is_unlocked=_has_profitable_streak,
            apply_reward=_reward_profitable_streak,
        ),
        MilestoneDefinition(
            milestone_id=MilestoneId.MULTI_SEGMENT_REACH,
            title="Multi-Segment Reach",
            description="The portfolio is now competing across multiple customer segments.",
            is_unlocked=lambda state: (
                len(_get_active_segments(state)) >= BALANCE.multi_segment_milestone_threshold
            ),
            apply_reward=_reward_multi_segment_reach,
        ),
        MilestoneDefinition(
            milestone_id=MilestoneId.OPERATIONS_MACHINE,
            title="Operations Machine",
            description="The company kept support pressure under control while scaling.",
            is_unlocked=_has_operations_machine,
            apply_reward=_reward_operations_machine,
        ),
        MilestoneDefinition(
            milestone_id=MilestoneId.ENTERPRISE_FOOTING,
            title="Enterprise Footing",
            description="An enterprise product has become a meaningful part of the company.",
            is_unlocked=_has_enterprise_footing,
            apply_reward=_reward_enterprise_footing,
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


def _reward_profitable_streak(state: GameState) -> str:
    state.company.reputation = clamp_int(
        state.company.reputation + BALANCE.milestone_profitable_streak_reputation_gain
    )
    for employee in state.employees:
        employee.morale = clamp_int(
            employee.morale + BALANCE.milestone_profitable_streak_morale_gain
        )
    return (
        f"Reputation +{BALANCE.milestone_profitable_streak_reputation_gain}, "
        f"team morale +{BALANCE.milestone_profitable_streak_morale_gain} for sustained execution."
    )


def _reward_multi_segment_reach(state: GameState) -> str:
    state.company.reputation = clamp_int(
        state.company.reputation + BALANCE.milestone_multi_segment_reputation_gain
    )
    return (
        f"Reputation +{BALANCE.milestone_multi_segment_reputation_gain} "
        "for proving the portfolio can reach multiple customer segments."
    )


def _reward_operations_machine(state: GameState) -> str:
    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand + BALANCE.milestone_operations_machine_cash_gain
    )
    state.company.reputation = clamp_int(
        state.company.reputation + BALANCE.milestone_operations_machine_reputation_gain
    )
    return (
        f"Cash +{format_money(BALANCE.milestone_operations_machine_cash_gain)}, "
        f"reputation +{BALANCE.milestone_operations_machine_reputation_gain} "
        "for running a cleaner operating machine."
    )


def _reward_enterprise_footing(state: GameState) -> str:
    state.company.reputation = clamp_int(
        state.company.reputation + BALANCE.milestone_enterprise_footing_reputation_gain
    )
    return (
        f"Reputation +{BALANCE.milestone_enterprise_footing_reputation_gain} "
        "for proving the company can hold enterprise demand."
    )


def _get_total_users(state: GameState) -> int:
    return sum(product.user_count for product in state.products if product.is_active)


def _has_profitable_streak(state: GameState) -> bool:
    recent_turns = state.turn_history[-BALANCE.profitable_streak_turns :]
    return (
        len(recent_turns) == BALANCE.profitable_streak_turns
        and all(entry.net_cash_flow > 0 for entry in recent_turns)
    )


def _get_active_segments(state: GameState) -> set[str]:
    return {product.target_segment.value for product in state.products if product.is_active}


def _has_operations_machine(state: GameState) -> bool:
    if _get_total_users(state) < BALANCE.operations_machine_user_threshold:
        return False
    if len(state.employees) < BALANCE.operations_machine_headcount_threshold:
        return False
    summary = calculate_operations_summary(
        state.products,
        state.employees,
        current_turn=state.company.current_turn,
    )
    return summary.overload <= 1


def _has_enterprise_footing(state: GameState) -> bool:
    return any(
        product.is_active
        and product.target_segment.value == "enterprise"
        and product.user_count >= BALANCE.enterprise_footing_user_threshold
        for product in state.products
    )
