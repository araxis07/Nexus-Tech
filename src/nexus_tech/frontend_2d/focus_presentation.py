"""Pure responsive presentation policy for the live-run Focus View."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "GuidedOpeningFocusCopy",
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


def build_guided_opening_focus_copy(
    *,
    journey_step_label: str,
    actions_remaining: int,
) -> GuidedOpeningFocusCopy:
    """Keep opening copy instructional without repeating every shortcut."""

    step_label = " ".join(journey_step_label.split()) or "1/6"
    safe_actions = max(0, actions_remaining)
    return GuidedOpeningFocusCopy(
        header_line=(
            f"Opening {step_label} | Follow the highlighted NEXT step | AP {safe_actions}"
        ),
        card_title="Opening Guide",
        card_detail="Do NEXT first. LATER steps become NEXT in order.",
        footer_status="Recommended follows the highlighted NEXT step.",
        footer_hint="Hover an action for details; Space resolves after spending AP.",
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
