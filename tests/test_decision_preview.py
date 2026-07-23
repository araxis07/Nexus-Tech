from __future__ import annotations

import pytest

from nexus_tech.domain.models import TurnAction
from nexus_tech.frontend_2d.decision_preview import (
    build_decision_preview_presentation,
)
from nexus_tech.simulation.action_points import get_action_point_cost
from nexus_tech.simulation.engine import ActionContext, apply_action, create_new_game


@pytest.mark.parametrize(
    "action",
    (
        TurnAction.VIEW_STATUS,
        TurnAction.REVIEW_TEAM,
        TurnAction.REVIEW_FINANCE,
        TurnAction.REVIEW_CUSTOMERS,
        TurnAction.REVIEW_PIPELINE,
        TurnAction.REVIEW_BOARD,
        TurnAction.REVIEW_PARTNERSHIPS,
        TurnAction.VIEW_REPORT,
        TurnAction.END_TURN,
    ),
)
def test_action_point_policy_preserves_free_review_and_resolution_actions(
    action: TurnAction,
) -> None:
    assert get_action_point_cost(action) == 0


def test_action_point_policy_matches_engine_for_operating_and_review_actions() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")
    starting_actions = state.action_points_remaining

    review = apply_action(state, TurnAction.REVIEW_FINANCE)
    operating = apply_action(
        state,
        TurnAction.IMPROVE_QUALITY,
        context=ActionContext(target_product_id=state.products[0].id),
    )

    assert get_action_point_cost(TurnAction.IMPROVE_QUALITY) == 1
    assert review.state is state
    assert review.state.action_points_remaining == starting_actions
    assert operating.state.action_points_remaining == starting_actions - 1


def test_decision_preview_exposes_cost_effect_risk_and_timing() -> None:
    preview = build_decision_preview_presentation(
        command=TurnAction.HIRE_EMPLOYEE.value,
        command_label="Hire Teammate",
        expected_effect="Build the first execution loop.",
        skipped_consequence="The run stays underpowered until the first hire exists.",
        source="opening",
        urgency_label="Act now / 1 turn",
        action_points_remaining=2,
        compact=True,
    )

    assert preview.cost_label == "1 AP -> 1"
    assert preview.timing_label == "Now / 1 turn"
    assert preview.expected_effect == "Build the first execution loop"
    assert preview.skipped_risk == "Opening progress stays blocked."
    assert preview.primary_line == ("NEXT Hire Teammate | COST 1 AP -> 1 | WHEN Now / 1 turn")
    assert preview.effect_line == "EXPECTED Build the first execution loop"
    assert preview.risk_line == "IF SKIPPED Opening progress stays blocked."
    assert not preview.blocked
    assert "..." not in " ".join((preview.primary_line, preview.effect_line, preview.risk_line))


def test_decision_preview_uses_complete_compact_risk_and_blocked_cost_copy() -> None:
    preview = build_decision_preview_presentation(
        command=TurnAction.RUN_WHITE_GLOVE_RECOVERY.value,
        command_label="White-glove Recovery",
        expected_effect=(
            "Stabilize the premium support lane before revenue exposure becomes terminal."
        ),
        skipped_consequence=(
            "Premium support backlog and renewal exposure continue to grow while the "
            "current lane remains saturated and the account team loses recovery time."
        ),
        source="support",
        urgency_label="This turn / 2 turns",
        action_points_remaining=0,
        compact=True,
    )

    assert preview.blocked
    assert preview.cost_label == "1 AP / blocked at 0"
    assert preview.expected_effect == "Advance White-glove Recovery"
    assert preview.skipped_risk == "Backlog and revenue exposure can grow."
    assert "..." not in preview.tooltip


def test_decision_preview_keeps_review_actions_free() -> None:
    preview = build_decision_preview_presentation(
        command=TurnAction.REVIEW_FINANCE.value,
        command_label="Review Finance",
        expected_effect="Refresh the capital plan.",
        skipped_consequence="Unreviewed reserve pressure can compound.",
        source="review",
        urgency_label="Plan next / 2 turns",
        action_points_remaining=1,
    )

    assert preview.cost_label == "Free / 1 AP stays"
    assert not preview.blocked
    assert preview.timing_label == "Plan next / 2 turns"
