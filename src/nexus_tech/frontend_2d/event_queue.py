"""Frontend event stream helpers for lightweight 2D animations."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.domain.models import GameState
from nexus_tech.domain.money import format_money
from nexus_tech.simulation.endgame import (
    calculate_endgame_pressure,
    calculate_endgame_readiness,
    evaluate_exit_outcome,
)
from nexus_tech.simulation.engine import TurnResolution


@dataclass(frozen=True)
class FrontendEvent:
    """One short-lived event card shown in the 2D frontend."""

    title: str
    detail: str
    severity: str = "info"
    ttl: float = 4.5


def build_action_events(
    previous_state: GameState,
    current_state: GameState,
    *,
    action_label: str,
    message: str,
) -> tuple[FrontendEvent, ...]:
    """Summarize one action into lightweight UI events."""

    events: list[FrontendEvent] = [
        FrontendEvent(
            title=action_label.replace("_", " ").title(),
            detail=message,
            severity="info",
            ttl=4.0,
        )
    ]
    events.extend(_build_delta_events(previous_state, current_state))
    return tuple(events)


def build_turn_resolution_events(
    previous_state: GameState,
    resolution: TurnResolution,
) -> tuple[FrontendEvent, ...]:
    """Summarize one resolved turn into lightweight UI events."""

    current_state = resolution.state
    severity = "danger" if resolution.net_cash_flow < 0 else "success"
    summary = FrontendEvent(
        title=f"Turn {resolution.resolved_turn} Resolved",
        detail=(
            f"Net {format_money(resolution.net_cash_flow)} | revenue "
            f"{format_money(resolution.total_revenue)} | cost "
            f"{format_money(resolution.total_operating_cost)}"
        ),
        severity=severity,
        ttl=5.5,
    )
    events = [summary]
    total_user_delta = sum(
        summary_item.net_user_delta for summary_item in resolution.product_summaries
    )
    if total_user_delta:
        tone = "success" if total_user_delta > 0 else "warning"
        events.append(
            FrontendEvent(
                title="Users Shifted",
                detail=f"Net users {'+' if total_user_delta > 0 else ''}{total_user_delta}.",
                severity=tone,
            )
        )
    previous_readiness = calculate_endgame_readiness(previous_state)
    current_readiness = calculate_endgame_readiness(current_state, resolution.run_score)
    previous_pressure = calculate_endgame_pressure(previous_state, previous_readiness)
    current_pressure = calculate_endgame_pressure(current_state, current_readiness)
    previous_outcome = evaluate_exit_outcome(previous_state)
    current_outcome = evaluate_exit_outcome(current_state, resolution.run_score)
    previous_blocked_paths = sum(
        1 for gate in previous_pressure.path_outcome_gates if "blocked" in gate.lower()
    )
    current_blocked_paths = sum(
        1 for gate in current_pressure.path_outcome_gates if "blocked" in gate.lower()
    )
    events.append(
        FrontendEvent(
            title="Gate Command",
            detail=(
                f"{current_pressure.path_gate_command_alert}: {current_pressure.path_gate_alert}"
            ),
            severity="warning" if current_blocked_paths else "info",
            ttl=5.0,
        )
    )
    if (
        current_outcome.title != previous_outcome.title
        or current_pressure.dominant_pressure != previous_pressure.dominant_pressure
    ):
        events.append(
            FrontendEvent(
                title="Strategic Outlook",
                detail=(
                    f"{previous_outcome.title} -> {current_outcome.title} | "
                    f"{current_pressure.dominant_pressure.replace('_', ' ')}"
                ),
                severity="info",
                ttl=5.0,
            )
        )
    if current_blocked_paths != previous_blocked_paths:
        events.append(
            FrontendEvent(
                title="Exit Gates",
                detail=f"{previous_blocked_paths} -> {current_blocked_paths} blocked paths.",
                severity=(
                    "danger"
                    if current_blocked_paths > previous_blocked_paths
                    else "success"
                    if current_blocked_paths < previous_blocked_paths
                    else "warning"
                ),
            )
        )
    events.extend(_build_delta_events(previous_state, current_state))
    return tuple(events)


def _build_delta_events(previous_state: GameState, current_state: GameState) -> list[FrontendEvent]:
    events: list[FrontendEvent] = []

    cash_delta = current_state.company.cash_on_hand - previous_state.company.cash_on_hand
    if cash_delta:
        events.append(
            FrontendEvent(
                title="Cash Changed",
                detail=f"{'+' if cash_delta > 0 else ''}{format_money(cash_delta)}",
                severity="success" if cash_delta > 0 else "warning",
            )
        )

    reputation_delta = current_state.company.reputation - previous_state.company.reputation
    if reputation_delta:
        events.append(
            FrontendEvent(
                title="Reputation Shifted",
                detail=f"{'+' if reputation_delta > 0 else ''}{reputation_delta} reputation.",
                severity="success" if reputation_delta > 0 else "warning",
            )
        )

    board_delta = current_state.finance.board_pressure - previous_state.finance.board_pressure
    if board_delta:
        events.append(
            FrontendEvent(
                title="Board Pressure",
                detail=f"{'+' if board_delta > 0 else ''}{board_delta} board pressure.",
                severity="danger" if board_delta > 0 else "success",
            )
        )

    previous_products = {product.id: product for product in previous_state.products}
    for product in current_state.products:
        previous_product = previous_products.get(product.id)
        if previous_product is None:
            continue
        _append_product_delta_events(events, previous_product, product)

    if current_state.pending_event is not None and (
        previous_state.pending_event is None
        or previous_state.pending_event.event_id != current_state.pending_event.event_id
    ):
        events.append(
            FrontendEvent(
                title=current_state.pending_event.title,
                detail=current_state.pending_event.description,
                severity="warning",
                ttl=6.0,
            )
        )

    if current_state.victory_achieved and not previous_state.victory_achieved:
        events.append(
            FrontendEvent(
                title="Victory Achieved",
                detail=current_state.victory_reason or "The company reached a winning end state.",
                severity="success",
                ttl=7.0,
            )
        )
    if current_state.company.game_over and not previous_state.company.game_over:
        events.append(
            FrontendEvent(
                title="Company Shutdown",
                detail="Cash or governance pressure broke the run.",
                severity="danger",
                ttl=7.0,
            )
        )

    return events


def _append_product_delta_events(
    events: list[FrontendEvent], previous_product, current_product
) -> None:
    quality_delta = current_product.quality - previous_product.quality
    if quality_delta:
        events.append(
            FrontendEvent(
                title=f"{current_product.name} Quality",
                detail=f"{'+' if quality_delta > 0 else ''}{quality_delta} quality.",
                severity="success" if quality_delta > 0 else "warning",
            )
        )

    bug_delta = current_product.bug_level - previous_product.bug_level
    if bug_delta:
        events.append(
            FrontendEvent(
                title=f"{current_product.name} Bugs",
                detail=f"{'+' if bug_delta > 0 else ''}{bug_delta} bug pressure.",
                severity="danger" if bug_delta > 0 else "success",
            )
        )

    user_delta = current_product.user_count - previous_product.user_count
    if user_delta:
        events.append(
            FrontendEvent(
                title=f"{current_product.name} Users",
                detail=f"{'+' if user_delta > 0 else ''}{user_delta} users.",
                severity="success" if user_delta > 0 else "warning",
            )
        )
