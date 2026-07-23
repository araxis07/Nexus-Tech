"""Shared action-point cost policy for turn actions."""

from __future__ import annotations

from nexus_tech.domain.models import TurnAction

__all__ = ["get_action_point_cost"]


_FREE_ACTIONS = frozenset(
    {
        TurnAction.VIEW_STATUS,
        TurnAction.REVIEW_TEAM,
        TurnAction.REVIEW_FINANCE,
        TurnAction.REVIEW_CUSTOMERS,
        TurnAction.REVIEW_PIPELINE,
        TurnAction.REVIEW_BOARD,
        TurnAction.REVIEW_PARTNERSHIPS,
        TurnAction.VIEW_REPORT,
        TurnAction.END_TURN,
    }
)


def get_action_point_cost(action: TurnAction | str) -> int:
    """Return the existing AP cost for one recognized turn action."""

    resolved = action if isinstance(action, TurnAction) else TurnAction(action)
    return 0 if resolved in _FREE_ACTIONS else 1
