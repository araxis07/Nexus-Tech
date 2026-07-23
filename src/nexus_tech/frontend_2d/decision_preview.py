"""Pure presentation policy for the live action decision preview."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.simulation.action_points import get_action_point_cost

__all__ = [
    "DecisionPreviewPresentation",
    "build_decision_preview_presentation",
]


_COMPACT_RISK_BY_SOURCE = {
    "opening": "Opening progress stays blocked.",
    "finance": "Runway and reserve pressure can compound.",
    "support": "Backlog and revenue exposure can grow.",
    "channel": "Channel dependency remains exposed.",
    "endgame": "The exposed exit gate can stay blocked.",
    "board": "Board heat can narrow financing options.",
    "review": "Unreviewed pressure can compound next turn.",
}


@dataclass(frozen=True)
class DecisionPreviewPresentation:
    """One cost, outcome, risk, and timing summary for a recommended move."""

    command_label: str
    cost_label: str
    timing_label: str
    expected_effect: str
    skipped_risk: str
    blocked: bool
    primary_line: str
    effect_line: str
    risk_line: str
    tooltip: str


def build_decision_preview_presentation(
    *,
    command: str,
    command_label: str,
    expected_effect: str,
    skipped_consequence: str,
    source: str,
    urgency_label: str,
    action_points_remaining: int,
    compact: bool = False,
) -> DecisionPreviewPresentation:
    """Build bounded decision copy without changing action availability or outcomes."""

    label = _clean_phrase(command_label, fallback="Recommended move")
    effect = _bounded_effect(expected_effect, command_label=label, compact=compact)
    risk_detail = _first_sentence(skipped_consequence)
    risk = _bounded_risk(
        risk_detail,
        source=source,
        compact=compact,
    )
    timing = (
        _compact_timing(urgency_label)
        if compact
        else _clean_phrase(
            urgency_label,
            fallback="This turn",
        )
    )
    safe_actions = max(0, action_points_remaining)
    action_point_cost = get_action_point_cost(command)
    blocked = action_point_cost > safe_actions
    if action_point_cost == 0:
        cost = f"Free / {safe_actions} AP stays"
    elif blocked:
        cost = f"{action_point_cost} AP / blocked at {safe_actions}"
    else:
        suffix = "" if compact else " left"
        cost = f"{action_point_cost} AP -> {safe_actions - action_point_cost}{suffix}"

    primary_line = f"NEXT {label} | COST {cost} | WHEN {timing}"
    effect_line = f"EXPECTED {effect}"
    risk_line = f"IF SKIPPED {risk}"
    tooltip = (
        f"Expected: {effect} Cost: {cost}. Timing: {timing}. "
        f"If skipped: {_tooltip_risk(risk_detail, fallback=risk)}"
    )
    return DecisionPreviewPresentation(
        command_label=label,
        cost_label=cost,
        timing_label=timing,
        expected_effect=effect,
        skipped_risk=risk,
        blocked=blocked,
        primary_line=primary_line,
        effect_line=effect_line,
        risk_line=risk_line,
        tooltip=tooltip,
    )


def _bounded_effect(value: str, *, command_label: str, compact: bool) -> str:
    effect = _first_sentence(value)
    limit = 52 if compact else 76
    if len(effect) <= limit:
        return effect
    return f"Advance {command_label}"


def _bounded_risk(value: str, *, source: str, compact: bool) -> str:
    risk = _first_sentence(value)
    source_key = source.strip().lower()
    if compact and source_key in _COMPACT_RISK_BY_SOURCE:
        return _COMPACT_RISK_BY_SOURCE[source_key]
    limit = 68 if compact else 112
    if len(risk) <= limit:
        return risk
    return _COMPACT_RISK_BY_SOURCE.get(
        source_key,
        "The current operating pressure can compound.",
    )


def _tooltip_risk(value: str, *, fallback: str) -> str:
    return value if len(value) <= 112 else fallback


def _compact_timing(value: str) -> str:
    timing = _clean_phrase(value, fallback="This turn")
    replacements = (
        ("Act now", "Now"),
        ("Plan next", "Next"),
    )
    for source, target in replacements:
        timing = timing.replace(source, target)
    return timing


def _first_sentence(value: str) -> str:
    phrase = _clean_phrase(value, fallback="Current pressure can compound")
    sentence, separator, _remainder = phrase.partition(".")
    if separator:
        return sentence.strip()
    return phrase.rstrip(".!? ")


def _clean_phrase(value: str, *, fallback: str) -> str:
    cleaned = " ".join(value.replace("`", "").split()).strip()
    return cleaned or fallback
