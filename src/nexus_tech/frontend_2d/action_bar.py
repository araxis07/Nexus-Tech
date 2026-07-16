"""Pure action-bar catalog and loadout policy for the lightweight 2D frontend."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.domain.models import TurnAction
from nexus_tech.frontend_2d.widgets import DANGER, GOOD, INFO, WARN
from nexus_tech.user_preferences import ActionLoadout

__all__ = ["ACTION_LOADOUT_COMMANDS", "RUN_ACTION_BUTTONS", "ActionButtonSpec"]


@dataclass(frozen=True)
class ActionButtonSpec:
    """One visible action button in the 2D action bar."""

    key_hint: str
    title: str
    detail: str
    accent: tuple[int, int, int]
    kind: str
    payload: str


RUN_ACTION_BUTTONS: tuple[ActionButtonSpec, ...] = (
    ActionButtonSpec("C", "Coach", "Run the top mission-board command.", INFO, "coach", ""),
    ActionButtonSpec(
        "N",
        "New Product",
        "Name and create one product.",
        INFO,
        "text_command",
        TurnAction.CREATE_PRODUCT.value,
    ),
    ActionButtonSpec("1", "Team", "Open team staffing panel.", GOOD, "panel", "team"),
    ActionButtonSpec("2", "Finance", "Open finance and capital panel.", WARN, "panel", "finance"),
    ActionButtonSpec(
        "3",
        "Customers",
        "Open pricing, segment, and support panel.",
        INFO,
        "panel",
        "customers",
    ),
    ActionButtonSpec(
        "4",
        "Partners",
        "Open channel and partner panel.",
        INFO,
        "panel",
        "partnerships",
    ),
    ActionButtonSpec("5", "Board", "Open board and governance panel.", WARN, "panel", "board"),
    ActionButtonSpec(
        "6",
        "Pipeline",
        "Open delivery, deals, and hiring panel.",
        INFO,
        "panel",
        "pipeline",
    ),
    ActionButtonSpec(
        "7",
        "Report",
        "Open run-summary and reporting panel.",
        INFO,
        "panel",
        "report",
    ),
    ActionButtonSpec(
        "8",
        "Endgame",
        "Open exit readiness and late-game gate board.",
        WARN,
        "panel",
        "endgame",
    ),
    ActionButtonSpec(
        "Q",
        "Improve",
        "Invest in product quality.",
        GOOD,
        "command",
        TurnAction.IMPROVE_QUALITY.value,
    ),
    ActionButtonSpec(
        "F",
        "Feature",
        "Add one feature to the selected product.",
        INFO,
        "command",
        TurnAction.ADD_FEATURE.value,
    ),
    ActionButtonSpec(
        "M",
        "Market",
        "Push demand for the selected product.",
        INFO,
        "command",
        TurnAction.MARKET_PRODUCT.value,
    ),
    ActionButtonSpec(
        "D",
        "Debt Down",
        "Reduce technical debt on the selected product.",
        WARN,
        "command",
        TurnAction.REDUCE_TECHNICAL_DEBT.value,
    ),
    ActionButtonSpec(
        "H",
        "Hire",
        "Pick the next role to add.",
        INFO,
        "command",
        TurnAction.HIRE_EMPLOYEE.value,
    ),
    ActionButtonSpec(
        "A",
        "Assign",
        "Pick an idle teammate for the selected product.",
        GOOD,
        "command",
        TurnAction.ASSIGN_EMPLOYEE.value,
    ),
    ActionButtonSpec(
        "Y",
        "Strategy",
        "Choose the company posture.",
        INFO,
        "command",
        TurnAction.SET_COMPANY_STRATEGY.value,
    ),
    ActionButtonSpec(
        "R",
        "Roadmap",
        "Choose the multi-turn focus.",
        INFO,
        "command",
        TurnAction.SET_ROADMAP.value,
    ),
    ActionButtonSpec(
        "B",
        "Budget",
        "Choose quarter spending posture.",
        WARN,
        "command",
        TurnAction.SET_BUDGET_STANCE.value,
    ),
    ActionButtonSpec(
        "U",
        "Support",
        "Choose the service lane focus.",
        WARN,
        "command",
        TurnAction.SET_SUPPORT_LANE_FOCUS.value,
    ),
    ActionButtonSpec(
        "O",
        "Partner",
        "Open a partner channel for the selected product.",
        INFO,
        "command",
        TurnAction.CREATE_PARTNERSHIP.value,
    ),
    ActionButtonSpec(
        "L",
        "Loan",
        "Take debt if runway is tightening.",
        WARN,
        "command",
        TurnAction.TAKE_LOAN.value,
    ),
    ActionButtonSpec(
        "G",
        "Angel",
        "Raise an angel round if traction supports it.",
        INFO,
        "command",
        TurnAction.RAISE_ANGEL.value,
    ),
    ActionButtonSpec("S", "Save", "Persist the active run.", INFO, "save", ""),
    ActionButtonSpec(
        "Space",
        "End Turn",
        "Resolve the turn with preview and warning gate.",
        DANGER,
        "command",
        TurnAction.END_TURN.value,
    ),
)


ACTION_LOADOUT_COMMANDS: dict[ActionLoadout, tuple[str, ...]] = {
    ActionLoadout.CONTEXTUAL: (),
    ActionLoadout.PRODUCT: (
        TurnAction.IMPROVE_QUALITY.value,
        TurnAction.ADD_FEATURE.value,
    ),
    ActionLoadout.GROWTH: (
        TurnAction.MARKET_PRODUCT.value,
        TurnAction.CREATE_PARTNERSHIP.value,
    ),
    ActionLoadout.RESILIENCE: (
        TurnAction.REDUCE_TECHNICAL_DEBT.value,
        TurnAction.SET_SUPPORT_LANE_FOCUS.value,
    ),
}
