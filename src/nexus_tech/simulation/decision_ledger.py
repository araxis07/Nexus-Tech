"""Readable, bounded history for state-changing player decisions."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from nexus_tech.domain.models import DecisionLedgerEntry, GameState, Product, TurnAction
from nexus_tech.domain.money import format_money
from nexus_tech.simulation.action_catalog import get_action_presentation, humanize_action_text

MAX_DECISION_HISTORY = 80


def record_action_decision(
    previous: GameState,
    current: GameState,
    action: TurnAction,
    message: str,
) -> None:
    """Append one normalized decision entry to the resulting state."""

    presentation = get_action_presentation(action)
    record_named_decision(
        previous,
        current,
        command=presentation.command,
        label=presentation.label,
        family=presentation.family_label,
        summary=message,
        timing=_timing_for_family(presentation.family.value),
    )


def record_named_decision(
    previous: GameState,
    current: GameState,
    *,
    command: str,
    label: str,
    family: str,
    summary: str,
    timing: str,
) -> None:
    """Append a non-action-catalog player choice such as an event response."""

    current.decision_history.append(
        DecisionLedgerEntry(
            turn=previous.company.current_turn,
            command=_truncate(command.strip(), 100),
            label=_truncate(label.strip(), 100),
            family=_truncate(family.strip(), 40),
            summary=_truncate(humanize_action_text(summary).strip(), 320),
            impact_summary=_build_impact_summary(previous, current),
            timing=_truncate(timing.strip(), 180),
        )
    )
    if len(current.decision_history) > MAX_DECISION_HISTORY:
        del current.decision_history[:-MAX_DECISION_HISTORY]


def _build_impact_summary(previous: GameState, current: GameState) -> str:
    deltas: list[str] = []

    _append_money_delta(deltas, "Cash", previous.company.cash_on_hand, current.company.cash_on_hand)
    _append_integer_delta(
        deltas,
        "Action points",
        previous.action_points_remaining,
        current.action_points_remaining,
    )
    _append_integer_delta(
        deltas,
        "Reputation",
        previous.company.reputation,
        current.company.reputation,
    )
    _append_integer_delta(deltas, "Users", _total_users(previous), _total_users(current))
    _append_integer_delta(
        deltas,
        "Product quality",
        _product_total(previous, lambda product: product.quality),
        _product_total(current, lambda product: product.quality),
    )
    _append_integer_delta(
        deltas,
        "Features",
        _product_total(previous, lambda product: product.feature_count),
        _product_total(current, lambda product: product.feature_count),
    )
    _append_integer_delta(
        deltas,
        "Tech debt",
        _product_total(previous, lambda product: product.technical_debt),
        _product_total(current, lambda product: product.technical_debt),
    )
    _append_integer_delta(deltas, "Headcount", len(previous.employees), len(current.employees))
    _append_money_delta(
        deltas,
        "Debt",
        previous.finance.debt_principal,
        current.finance.debt_principal,
    )
    _append_integer_delta(
        deltas,
        "Board pressure",
        previous.finance.board_pressure,
        current.finance.board_pressure,
    )
    _append_integer_delta(
        deltas,
        "Support backlog",
        previous.support_program.backlog_queue,
        current.support_program.backlog_queue,
    )
    _append_integer_delta(
        deltas,
        "Partnerships",
        len(previous.partnerships),
        len(current.partnerships),
    )
    return " | ".join(deltas[:4]) or "Strategic state updated; inspect the linked workspace."


def _timing_for_family(family: str) -> str:
    if family in {"finance", "board_exit"}:
        return "Applied now; runway, governance, and endgame pressure refresh immediately."
    if family in {"product", "market", "customers", "delivery", "partners"}:
        return "Applied now; revenue, retention, and competitive follow-on resolves at end of turn."
    if family in {"team", "operations"}:
        return "Applied now; team capacity and operating follow-on resolves at end of turn."
    return "Applied now; downstream simulation resolves when the turn ends."


def _total_users(state: GameState) -> int:
    return sum(product.user_count for product in state.products if product.is_active)


def _product_total(state: GameState, getter: Callable[[Product], int]) -> int:
    return sum(getter(product) for product in state.products if product.is_active)


def _append_integer_delta(values: list[str], label: str, before: int, after: int) -> None:
    delta = after - before
    if delta:
        values.append(f"{label} {delta:+d}")


def _append_money_delta(
    values: list[str],
    label: str,
    before: Decimal,
    after: Decimal,
) -> None:
    delta = after - before
    if not delta:
        return
    sign = "+" if delta > 0 else "-"
    values.append(f"{label} {sign}{format_money(abs(delta))}")


def _truncate(value: str, limit: int) -> str:
    if not value:
        return "Decision applied."
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3].rstrip()}..."
