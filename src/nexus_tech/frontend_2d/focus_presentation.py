"""Pure responsive presentation policy for the live-run Focus View."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "FirstTurnGuidePresentation",
    "FirstTurnGuideStepPresentation",
    "GuidedOpeningFocusCopy",
    "build_first_turn_guide_presentation",
    "build_guided_opening_focus_copy",
    "resolve_focus_button_emphasis",
    "resolve_footer_grid_columns",
]


@dataclass(frozen=True)
class GuidedOpeningFocusCopy:
    """Non-redundant guidance shared by compact opening surfaces."""

    header_line: str
    card_title: str
    card_detail: str
    footer_status: str
    footer_hint: str


@dataclass(frozen=True)
class FirstTurnGuideStepPresentation:
    """One compact checkpoint without pygame-specific color values."""

    label: str
    detail: str
    done: bool
    tone: str


@dataclass(frozen=True)
class FirstTurnGuidePresentation:
    """Visibility, copy, and progress for the live first-turn guide."""

    active: bool
    copy: GuidedOpeningFocusCopy
    steps: tuple[FirstTurnGuideStepPresentation, ...]


def build_guided_opening_focus_copy(
    *,
    journey_step_label: str,
    actions_remaining: int,
    compact: bool = False,
) -> GuidedOpeningFocusCopy:
    """Keep opening copy instructional without repeating every shortcut."""

    step_label = " ".join(journey_step_label.split()) or "1/6"
    safe_actions = max(0, actions_remaining)
    if compact:
        return GuidedOpeningFocusCopy(
            header_line=f"Opening {step_label} | NEXT first | AP {safe_actions}",
            card_title="Opening Guide",
            card_detail="NEXT first; LATER unlocks in order.",
            footer_status="Recommended follows NEXT.",
            footer_hint="Hover for details; Space resolves after AP is spent.",
        )
    return GuidedOpeningFocusCopy(
        header_line=(
            f"Opening {step_label} | Follow the highlighted NEXT step | AP {safe_actions}"
        ),
        card_title="Opening Guide",
        card_detail="Do NEXT first. LATER steps become NEXT in order.",
        footer_status="Recommended follows the highlighted NEXT step.",
        footer_hint="Hover an action for details; Space resolves after spending AP.",
    )


def build_first_turn_guide_presentation(
    *,
    opening_active: bool,
    current_command_label: str,
    first_opening_step_done: bool,
    actions_remaining: int,
    current_turn: int,
    resolved_turn_count: int,
    journey_step_label: str,
    run_finished: bool,
    overlay_active: bool,
    compact: bool = False,
) -> FirstTurnGuidePresentation:
    """Build first-turn progress without coupling policy to pygame or scene state."""

    resolved_once = resolved_turn_count > 0 or current_turn > 1
    spent_actions = first_opening_step_done and (actions_remaining <= 0 or resolved_once)
    finished_turn = spent_actions and resolved_once
    safe_actions = max(0, actions_remaining)
    command_label = " ".join(current_command_label.split()) or "Recommended"
    copy = build_guided_opening_focus_copy(
        journey_step_label=journey_step_label,
        actions_remaining=safe_actions,
        compact=compact,
    )
    if compact:
        steps = (
            FirstTurnGuideStepPresentation("1 Coach", "Press C", first_opening_step_done, "info"),
            FirstTurnGuideStepPresentation(
                "2 AP", f"AP {safe_actions} left", spent_actions, "success"
            ),
            FirstTurnGuideStepPresentation("3 End", "Press Space", finished_turn, "selection"),
        )
    else:
        steps = (
            FirstTurnGuideStepPresentation(
                "1 Coach Move",
                f"C / click runs {command_label}",
                first_opening_step_done,
                "info",
            ),
            FirstTurnGuideStepPresentation(
                "2 Spend AP",
                f"{safe_actions} AP left",
                spent_actions,
                "success",
            ),
            FirstTurnGuideStepPresentation(
                "3 End Turn",
                "Space after spending AP",
                finished_turn,
                "selection",
            ),
        )
    return FirstTurnGuidePresentation(
        active=opening_active and not run_finished and not overlay_active,
        copy=copy,
        steps=steps,
    )


def resolve_footer_grid_columns(
    *,
    available_width: int,
    button_count: int,
    focus_mode: bool,
) -> int:
    """Return balanced columns while preserving the denser full workspace."""

    safe_width = max(0, available_width)
    safe_count = max(1, button_count)
    if focus_mode and safe_count == 6:
        if safe_width < 480:
            return 2
        if safe_width < 860:
            return 3
        return 6
    if safe_width < 620:
        return 4
    if safe_width < 860:
        return 5
    return 7


def resolve_focus_button_emphasis(
    *,
    title: str,
    enabled: bool,
    motion_emphasis: float,
) -> float:
    """Keep the recommended route visually primary even when motion is off."""

    safe_motion = max(0.0, min(1.0, motion_emphasis))
    if enabled and title == "Recommended":
        return max(0.52, safe_motion)
    return safe_motion
