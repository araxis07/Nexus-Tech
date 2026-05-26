"""Deterministic next-turn preview for dashboard and reporting surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import GameState, TurnAction
from nexus_tech.simulation.engine import get_total_users, resolve_turn
from nexus_tech.simulation.finance import estimate_runway
from nexus_tech.simulation.partnerships import calculate_partnership_portfolio
from nexus_tech.simulation.randomness import RandomSource
from nexus_tech.simulation.risk_forecast import build_risk_forecast


@dataclass(frozen=True)
class EndTurnPreviewMetric:
    """One projected delta if the player ends the turn now."""

    label: str
    current: str
    projected: str
    delta: str
    trend: str


@dataclass(frozen=True)
class EndTurnPreviewSummary:
    """Deterministic sample of the next turn from the current state."""

    blocked: bool
    headline: str
    note: str
    top_command: str
    risk_shift: str
    projected_outcome: str
    warning_level: str
    requires_confirmation: bool
    confirmation_reason: str
    metrics: tuple[EndTurnPreviewMetric, ...]
    warnings: tuple[str, ...]


def build_end_turn_preview(state: GameState) -> EndTurnPreviewSummary:
    """Project the next turn from the current state using a stable preview seed."""

    if state.company.game_over:
        return EndTurnPreviewSummary(
            blocked=True,
            headline="This run has already shut down.",
            note="No next-turn preview is available after a terminal failure.",
            top_command=TurnAction.VIEW_REPORT.value,
            risk_shift="-",
            projected_outcome="terminal",
            warning_level="blocked",
            requires_confirmation=False,
            confirmation_reason="",
            metrics=(),
            warnings=(),
        )
    if state.victory_achieved:
        return EndTurnPreviewSummary(
            blocked=True,
            headline="This run already reached victory.",
            note="No next-turn preview is needed after a winning state.",
            top_command=TurnAction.VIEW_REPORT.value,
            risk_shift="-",
            projected_outcome="victory",
            warning_level="blocked",
            requires_confirmation=False,
            confirmation_reason="",
            metrics=(),
            warnings=(),
        )
    if state.pending_event is not None:
        return EndTurnPreviewSummary(
            blocked=True,
            headline="Resolve the pending event before ending the turn.",
            note=(
                f"Event `{state.pending_event.event_id}` is still waiting for a choice, so the "
                "preview is blocked."
            ),
            top_command=TurnAction.VIEW_STATUS.value,
            risk_shift="-",
            projected_outcome="blocked",
            warning_level="blocked",
            requires_confirmation=False,
            confirmation_reason="",
            metrics=(),
            warnings=(state.pending_event.description,),
        )

    current_forecast = build_risk_forecast(state)
    preview_rng = RandomSource(seed=_build_preview_seed(state))
    preview_resolution = resolve_turn(state.model_copy(deep=True), preview_rng)
    projected_state = preview_resolution.state
    projected_forecast = build_risk_forecast(projected_state)
    current_portfolio = calculate_partnership_portfolio(state)
    projected_portfolio = calculate_partnership_portfolio(projected_state)

    current_users = get_total_users(state)
    projected_users = get_total_users(projected_state)
    current_runway = estimate_runway(state.company.cash_on_hand, _latest_net_cash_flow(state))
    projected_runway = estimate_runway(
        projected_state.company.cash_on_hand,
        preview_resolution.net_cash_flow,
    )

    metrics = (
        EndTurnPreviewMetric(
            label="Cash",
            current=_format_money(state.company.cash_on_hand),
            projected=_format_money(projected_state.company.cash_on_hand),
            delta=_format_money_delta(
                projected_state.company.cash_on_hand - state.company.cash_on_hand
            ),
            trend=_direction_label(
                before=state.company.cash_on_hand,
                after=projected_state.company.cash_on_hand,
                higher_is_better=True,
            ),
        ),
        EndTurnPreviewMetric(
            label="Runway",
            current=_format_runway(current_runway),
            projected=_format_runway(projected_runway),
            delta=_format_runway_delta(current_runway, projected_runway),
            trend=_runway_trend(current_runway, projected_runway),
        ),
        EndTurnPreviewMetric(
            label="Reputation",
            current=str(state.company.reputation),
            projected=str(projected_state.company.reputation),
            delta=_format_int_delta(projected_state.company.reputation - state.company.reputation),
            trend=_direction_label(
                before=state.company.reputation,
                after=projected_state.company.reputation,
                higher_is_better=True,
            ),
        ),
        EndTurnPreviewMetric(
            label="Users",
            current=str(current_users),
            projected=str(projected_users),
            delta=_format_int_delta(projected_users - current_users),
            trend=_direction_label(
                before=current_users,
                after=projected_users,
                higher_is_better=True,
            ),
        ),
        EndTurnPreviewMetric(
            label="Board Pressure",
            current=str(state.finance.board_pressure),
            projected=str(projected_state.finance.board_pressure),
            delta=_format_int_delta(
                projected_state.finance.board_pressure - state.finance.board_pressure
            ),
            trend=_direction_label(
                before=state.finance.board_pressure,
                after=projected_state.finance.board_pressure,
                higher_is_better=False,
            ),
        ),
        EndTurnPreviewMetric(
            label="Support Backlog",
            current=str(state.support_program.backlog_queue),
            projected=str(projected_state.support_program.backlog_queue),
            delta=_format_int_delta(
                projected_state.support_program.backlog_queue - state.support_program.backlog_queue
            ),
            trend=_direction_label(
                before=state.support_program.backlog_queue,
                after=projected_state.support_program.backlog_queue,
                higher_is_better=False,
            ),
        ),
        EndTurnPreviewMetric(
            label="Channel Dependency",
            current=str(current_portfolio.channel_dependency_risk),
            projected=str(projected_portfolio.channel_dependency_risk),
            delta=_format_int_delta(
                projected_portfolio.channel_dependency_risk
                - current_portfolio.channel_dependency_risk
            ),
            trend=_direction_label(
                before=current_portfolio.channel_dependency_risk,
                after=projected_portfolio.channel_dependency_risk,
                higher_is_better=False,
            ),
        ),
    )
    warnings = _build_warnings(current_forecast, projected_forecast, preview_resolution)
    warning_level, requires_confirmation, confirmation_reason = _evaluate_confirmation(
        current_forecast=current_forecast,
        projected_forecast=projected_forecast,
        current_runway=current_runway,
        projected_runway=projected_runway,
        projected_state=projected_state,
        current_board_pressure=state.finance.board_pressure,
        projected_board_pressure=projected_state.finance.board_pressure,
    )
    return EndTurnPreviewSummary(
        blocked=False,
        headline=(
            "Estimated if you end the turn now. This uses a deterministic preview seed, so live "
            "event outcomes may still vary."
        ),
        note=preview_resolution.narrative,
        top_command=current_forecast.top_command,
        risk_shift=f"{current_forecast.overall_risk} -> {projected_forecast.overall_risk}",
        projected_outcome=_projected_outcome_label(projected_state),
        warning_level=warning_level,
        requires_confirmation=requires_confirmation,
        confirmation_reason=confirmation_reason,
        metrics=metrics,
        warnings=warnings,
    )


def _build_preview_seed(state: GameState) -> int:
    cash_units = int((state.company.cash_on_hand / Decimal("10.00")).to_integral_value())
    return (
        (state.company.current_turn * 1009)
        + (len(state.products) * 131)
        + (len(state.turn_history) * 17)
        + cash_units
    )


def _build_warnings(current_forecast, projected_forecast, preview_resolution) -> tuple[str, ...]:
    warnings: list[str] = [preview_resolution.narrative]
    if projected_forecast.items:
        warnings.extend(
            f"Projected {item.area}: {item.summary}" for item in projected_forecast.items[:2]
        )
    elif current_forecast.items:
        warnings.append(f"Current top preventive move stays `{current_forecast.top_command}`.")
    return tuple(dict.fromkeys(warnings))


def _projected_outcome_label(projected_state: GameState) -> str:
    if projected_state.company.game_over:
        return "sample shutdown risk"
    if projected_state.victory_achieved:
        return "sample victory path"
    return "sample operating turn"


def _evaluate_confirmation(
    *,
    current_forecast,
    projected_forecast,
    current_runway: int | None,
    projected_runway: int | None,
    projected_state,
    current_board_pressure: int,
    projected_board_pressure: int,
) -> tuple[str, bool, str]:
    preventive_command = (
        projected_forecast.top_command
        if projected_forecast.top_command != TurnAction.VIEW_STATUS.value
        else current_forecast.top_command
    )
    if projected_state.company.game_over:
        return (
            "critical",
            True,
            f"Preview shows a sample shutdown. Run `{preventive_command}` before ending the turn.",
        )
    if projected_forecast.overall_risk == "critical":
        return (
            "critical",
            True,
            (
                f"Projected risk rises to critical. Run `{preventive_command}` before locking in "
                "the next turn."
            ),
        )
    if projected_runway is not None and projected_runway <= 2:
        return (
            "high",
            True,
            (
                f"Projected runway falls to {projected_runway} turn(s). "
                f"`{preventive_command}` should happen first."
            ),
        )
    if projected_board_pressure - current_board_pressure >= 8:
        return (
            "high",
            True,
            (
                "Board pressure is projected to jump by "
                f"{projected_board_pressure - current_board_pressure}. "
                f"Run `{preventive_command}` before ending the turn."
            ),
        )
    if (
        current_runway is not None
        and projected_runway is not None
        and projected_runway < current_runway
        and projected_forecast.overall_risk in {"high", "elevated"}
    ):
        return (
            "elevated",
            False,
            f"Runway is tightening. `{preventive_command}` is still the safer move first.",
        )
    if projected_forecast.overall_risk == "high":
        return (
            "high",
            False,
            f"`{preventive_command}` is recommended before ending the turn.",
        )
    if projected_forecast.overall_risk == "elevated":
        return (
            "elevated",
            False,
            f"`{preventive_command}` would reduce the projected next-turn pressure.",
        )
    return ("controlled", False, "No elevated end-turn warning is active.")


def _format_money(value: Decimal) -> str:
    rounded = value.quantize(Decimal("0.01"))
    return f"${rounded:,.2f}"


def _format_money_delta(value: Decimal) -> str:
    rounded = value.quantize(Decimal("0.01"))
    sign = "+" if rounded >= Decimal("0.00") else ""
    return f"{sign}${rounded:,.2f}"


def _format_int_delta(value: int) -> str:
    return f"{value:+d}"


def _format_runway(value: int | None) -> str:
    return "cashflow+" if value is None else f"{value}t"


def _format_runway_delta(before: int | None, after: int | None) -> str:
    if before is None and after is None:
        return "stable+"
    if before is None and after is not None:
        return f"to {after}t"
    if before is not None and after is None:
        return "to cashflow+"
    assert before is not None
    assert after is not None
    return f"{after - before:+d}t"


def _runway_trend(before: int | None, after: int | None) -> str:
    if before is None and after is None:
        return "stable"
    if before is None:
        return "tighter"
    if after is None:
        return "stronger"
    return _direction_label(before=before, after=after, higher_is_better=True)


def _direction_label(*, before: int | Decimal, after: int | Decimal, higher_is_better: bool) -> str:
    if after == before:
        return "stable"
    improving = after > before if higher_is_better else after < before
    return "improving" if improving else "worsening"


def _latest_net_cash_flow(state: GameState) -> Decimal:
    if not state.turn_history:
        return Decimal("0.00")
    return state.turn_history[-1].net_cash_flow
