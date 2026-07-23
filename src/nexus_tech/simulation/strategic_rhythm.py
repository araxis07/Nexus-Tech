"""One readable plan-to-consequence loop for live gameplay surfaces."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.domain.models import GameState
from nexus_tech.simulation.action_catalog import get_action_label, humanize_action_text
from nexus_tech.simulation.campaign_journey import get_campaign_journey_progress
from nexus_tech.simulation.end_turn_preview import (
    EndTurnPreviewSummary,
    build_end_turn_preview,
)
from nexus_tech.simulation.planning import (
    QuarterPlanProgress,
    evaluate_quarter_plan,
    is_quarter_plan_due,
)
from nexus_tech.simulation.risk_forecast import RiskForecastSummary, build_risk_forecast
from nexus_tech.simulation.run_phase import get_run_phase
from nexus_tech.simulation.turn_coach import TurnCoachSummary, build_turn_coach


@dataclass(frozen=True)
class StrategicRhythm:
    """Derived goal, plan, move, resolution, and follow-on guidance."""

    objective_label: str
    objective: str
    plan_label: str
    plan_progress_label: str
    plan_detail: str
    plan_progress: float
    plan_tone: str
    command: str
    command_label: str
    command_effect: str
    command_source: str
    command_detail: str
    command_consequence: str
    urgency_label: str
    end_turn_label: str
    end_turn_detail: str
    end_turn_tone: str
    end_turn_enabled: bool
    later_label: str
    later_detail: str


def build_strategic_rhythm(
    state: GameState,
    *,
    coach: TurnCoachSummary | None = None,
    forecast: RiskForecastSummary | None = None,
    preview: EndTurnPreviewSummary | None = None,
) -> StrategicRhythm:
    """Unify existing strategic systems without adding persisted gameplay state."""

    coach = coach or build_turn_coach(state)
    forecast = forecast or build_risk_forecast(state)
    preview = preview or build_end_turn_preview(state)
    phase = get_run_phase(state.company.current_turn)
    journey = get_campaign_journey_progress(state.scenario_id, state.company.current_turn)
    objective_label = journey.act_label if journey is not None else phase.title
    objective = journey.chapter.objective if journey is not None else phase.objective

    plan = state.quarter_plan
    plan_progress = evaluate_quarter_plan(state)
    plan_ratio = _quarter_plan_ratio(plan_progress)
    plan_status = _plan_status(state)
    plan_label = f"{_title(state.roadmap_focus.value)} / {_title(plan.budget_stance.value)} budget"
    plan_progress_label = f"{plan_progress.completed_target_count}/4 targets | {plan_status}"
    plan_detail = _plan_detail(state, plan_progress)

    primary = coach.recommendations[0] if coach.recommendations else None
    command = primary.command if primary is not None else coach.primary_command
    command_label = get_action_label(command)
    command_effect = (
        humanize_action_text(primary.title)
        if primary is not None
        else "Refresh the current operating context."
    )
    command_source = primary.source if primary is not None else "review"
    command_detail = (
        humanize_action_text(primary.rationale)
        if primary is not None
        else "Review the current operating report before committing the turn."
    )
    command_consequence = (
        humanize_action_text(primary.consequence)
        if primary is not None
        else "Unreviewed pressure can compound into the next turn."
    )
    urgency_label = (
        _urgency_label(primary.urgency, primary.horizon_turns)
        if primary is not None
        else "Review now / 1 turn"
    )

    end_turn_label = _end_turn_label(preview)
    end_turn_detail = (
        preview.headline if preview.blocked else preview.confirmation_reason or preview.note
    )
    if not end_turn_detail:
        end_turn_detail = f"Projected result: {preview.projected_outcome}."
    later_label, later_detail = _later_follow_on(
        state,
        forecast,
        coach,
        command=command,
    )

    return StrategicRhythm(
        objective_label=objective_label,
        objective=objective,
        plan_label=plan_label,
        plan_progress_label=plan_progress_label,
        plan_detail=plan_detail,
        plan_progress=plan_ratio,
        plan_tone=_plan_tone(state, plan_progress.completed_target_count),
        command=command,
        command_label=command_label,
        command_effect=command_effect,
        command_source=command_source,
        command_detail=command_detail,
        command_consequence=command_consequence,
        urgency_label=urgency_label,
        end_turn_label=end_turn_label,
        end_turn_detail=humanize_action_text(end_turn_detail),
        end_turn_tone=_preview_tone(preview),
        end_turn_enabled=not preview.blocked,
        later_label=later_label,
        later_detail=later_detail,
    )


def _quarter_plan_ratio(progress: QuarterPlanProgress) -> float:
    values = (
        min(1.0, progress.revenue_progress),
        min(1.0, progress.user_progress),
        min(1.0, progress.cash_progress),
        1.0 if progress.headcount_within_cap else 0.0,
    )
    return max(0.0, min(1.0, sum(values) / len(values)))


def _plan_status(state: GameState) -> str:
    target_turn = state.quarter_plan.target_turn
    if is_quarter_plan_due(state):
        return "refresh due"
    if state.company.current_turn == target_turn:
        return "due this turn"
    turns_left = max(1, target_turn - state.company.current_turn)
    turn_label = "turn" if turns_left == 1 else "turns"
    return f"{turns_left} {turn_label} left"


def _plan_detail(state: GameState, progress: QuarterPlanProgress) -> str:
    if progress.completed_target_count == 4:
        return "All four plan targets are currently met; protect the position through resolution."

    metrics = [
        (progress.revenue_progress, "revenue"),
        (progress.user_progress, "users"),
        (progress.cash_progress, "cash reserve"),
    ]
    weakest_ratio, weakest_label = min(metrics, key=lambda item: item[0])
    if not progress.headcount_within_cap:
        weakest_ratio = 0.0
        weakest_label = "headcount cap"
    percentage = max(0, int(round(weakest_ratio * 100)))
    due_note = (
        " Refresh the roadmap before another resolution." if is_quarter_plan_due(state) else ""
    )
    return f"Weakest target: {weakest_label} at {percentage}%.{due_note}"


def _plan_tone(state: GameState, completed_target_count: int) -> str:
    if completed_target_count == 4:
        return "success"
    if is_quarter_plan_due(state) or (
        state.company.current_turn == state.quarter_plan.target_turn and completed_target_count <= 1
    ):
        return "danger"
    if (
        completed_target_count <= 1
        and state.quarter_plan.target_turn - state.company.current_turn <= 1
    ):
        return "warning"
    return "info"


def _urgency_label(urgency: int, horizon_turns: int) -> str:
    if urgency >= 85:
        priority = "Act now"
    elif urgency >= 65:
        priority = "This turn"
    elif urgency >= 45:
        priority = "Plan next"
    else:
        priority = "Monitor"
    turn_label = "turn" if horizon_turns == 1 else "turns"
    return f"{priority} / {horizon_turns} {turn_label}"


def _end_turn_label(preview: EndTurnPreviewSummary) -> str:
    if preview.blocked:
        if preview.projected_outcome in {"terminal", "victory"}:
            return "Run Complete"
        return "Resolve Required"
    if preview.requires_confirmation:
        return "Confirm High Risk"
    if preview.warning_level in {"high", "elevated"}:
        return "Review Risk"
    return "Ready to Resolve"


def _preview_tone(preview: EndTurnPreviewSummary) -> str:
    if preview.blocked and preview.projected_outcome == "victory":
        return "success"
    if preview.warning_level in {"blocked", "critical", "high"}:
        return "danger"
    if preview.warning_level in {"elevated", "warning"}:
        return "warning"
    return "success"


def _later_follow_on(
    state: GameState,
    forecast: RiskForecastSummary,
    coach: TurnCoachSummary,
    *,
    command: str,
) -> tuple[str, str]:
    if state.decision_history and state.decision_history[-1].turn == state.company.current_turn:
        latest = state.decision_history[-1]
        return f"{latest.label} follow-on", latest.timing

    candidate = next(
        (item for item in forecast.items if item.command != command and item.horizon_turns > 1),
        next((item for item in forecast.items if item.command != command), None),
    )
    if candidate is not None:
        turn_label = "turn" if candidate.horizon_turns == 1 else "turns"
        return (
            f"{_title(candidate.area)} / {candidate.horizon_turns} {turn_label}",
            humanize_action_text(candidate.consequence),
        )

    follow_on = next(
        (item for item in coach.recommendations if item.command != command),
        None,
    )
    if follow_on is not None:
        turn_label = "turn" if follow_on.horizon_turns == 1 else "turns"
        return (
            f"{get_action_label(follow_on.command)} / {follow_on.horizon_turns} {turn_label}",
            humanize_action_text(follow_on.consequence),
        )
    return "Risk controlled", "No elevated delayed pressure is flashing right now."


def _title(value: str) -> str:
    return value.replace("_", " ").title()
