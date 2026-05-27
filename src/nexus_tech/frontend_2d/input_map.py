"""Keyboard bindings for the lightweight 2D frontend."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class FrontendIntent(Enum):
    """Supported high-level 2D frontend intents."""

    NEXT_PRODUCT = auto()
    PREVIOUS_PRODUCT = auto()
    PRIMARY_COACH = auto()
    IMPROVE_QUALITY = auto()
    ADD_FEATURE = auto()
    MARKET_PRODUCT = auto()
    REDUCE_TECHNICAL_DEBT = auto()
    HIRE_EMPLOYEE = auto()
    ASSIGN_EMPLOYEE = auto()
    TAKE_LOAN = auto()
    RAISE_ANGEL = auto()
    CREATE_PARTNERSHIP = auto()
    END_TURN = auto()
    SAVE_GAME = auto()
    QUIT = auto()


@dataclass(frozen=True)
class InputBinding:
    """One user-facing keyboard binding."""

    key_hint: str
    label: str
    description: str
    intent: FrontendIntent


DEFAULT_BINDINGS: tuple[InputBinding, ...] = (
    InputBinding(
        "Tab",
        "Next Product",
        "Cycle the highlighted product card.",
        FrontendIntent.NEXT_PRODUCT,
    ),
    InputBinding(
        "Shift+Tab",
        "Prev Product",
        "Move the highlight backward through the product strip.",
        FrontendIntent.PREVIOUS_PRODUCT,
    ),
    InputBinding(
        "C",
        "Coach Move",
        "Try the primary Turn Coach command when it fits the simple 2D input layer.",
        FrontendIntent.PRIMARY_COACH,
    ),
    InputBinding(
        "Q",
        "Improve",
        "Invest one action in product quality.",
        FrontendIntent.IMPROVE_QUALITY,
    ),
    InputBinding(
        "F",
        "Feature",
        "Add one feature to the selected product.",
        FrontendIntent.ADD_FEATURE,
    ),
    InputBinding(
        "M",
        "Market",
        "Buy demand for the selected product.",
        FrontendIntent.MARKET_PRODUCT,
    ),
    InputBinding(
        "D",
        "Debt Down",
        "Reduce technical debt on the selected product.",
        FrontendIntent.REDUCE_TECHNICAL_DEBT,
    ),
    InputBinding(
        "H",
        "Hire",
        "Hire one mid-level engineer.",
        FrontendIntent.HIRE_EMPLOYEE,
    ),
    InputBinding(
        "A",
        "Assign",
        "Assign the first idle employee to the selected product.",
        FrontendIntent.ASSIGN_EMPLOYEE,
    ),
    InputBinding(
        "L",
        "Loan",
        "Take a loan when runway is tightening.",
        FrontendIntent.TAKE_LOAN,
    ),
    InputBinding(
        "G",
        "Angel",
        "Raise an angel round when traction allows it.",
        FrontendIntent.RAISE_ANGEL,
    ),
    InputBinding(
        "P",
        "Partner",
        "Open a reseller partnership on the selected product.",
        FrontendIntent.CREATE_PARTNERSHIP,
    ),
    InputBinding(
        "Space",
        "End Turn",
        "Resolve the turn with the preview and warning gate.",
        FrontendIntent.END_TURN,
    ),
    InputBinding(
        "S",
        "Save",
        "Write the current run back to SQLite.",
        FrontendIntent.SAVE_GAME,
    ),
    InputBinding("Esc", "Quit", "Close the 2D frontend.", FrontendIntent.QUIT),
)


def pending_event_bindings(option_count: int) -> tuple[InputBinding, ...]:
    """Return a compact legend for event resolution overlays."""

    return tuple(
        InputBinding(
            str(index + 1),
            f"Option {index + 1}",
            "Resolve the pending event with this option.",
            FrontendIntent.END_TURN,
        )
        for index in range(option_count)
    ) + (
        InputBinding(
            "S",
            "Save",
            "Write the current run back to SQLite.",
            FrontendIntent.SAVE_GAME,
        ),
        InputBinding("Esc", "Quit", "Close the 2D frontend.", FrontendIntent.QUIT),
    )
