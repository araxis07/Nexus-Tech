"""Pure pause-menu presentation policy for the 2D run shell."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "PauseActionPresentation",
    "PauseMenuPresentation",
    "build_pause_menu_presentation",
]


@dataclass(frozen=True)
class PauseActionPresentation:
    """One pause action with availability separate from input routing."""

    title: str
    detail: str
    target_kind: str
    payload: str
    tone: str
    enabled: bool = True


@dataclass(frozen=True)
class PauseMenuPresentation:
    """Pause status, guidance, and ordered recovery actions."""

    status_line: str
    guidance: str
    actions: tuple[PauseActionPresentation, ...]


def build_pause_menu_presentation(
    *,
    current_turn: int,
    action_points_remaining: int,
    slot_name: str,
    menu_available: bool,
) -> PauseMenuPresentation:
    """Describe pause recovery without mutating or saving the active run."""

    if menu_available:
        guidance = (
            "Use P or Esc to resume. Save before returning to the title menu if you "
            "want to keep the current run state."
        )
        menu_action = PauseActionPresentation(
            title="M Menu",
            detail="Save and return to title.",
            target_kind="pause_menu",
            payload="",
            tone="warning",
        )
    else:
        guidance = (
            "Use P or Esc to resume. This direct-play run has no title menu route; "
            "save before closing the 2D shell to keep progress."
        )
        menu_action = PauseActionPresentation(
            title="Menu Unavailable",
            detail="Direct play has no title shell.",
            target_kind="pause_menu",
            payload="",
            tone="warning",
            enabled=False,
        )

    return PauseMenuPresentation(
        status_line=(
            f"Turn {current_turn} | Actions left {action_points_remaining} | Slot {slot_name}"
        ),
        guidance=guidance,
        actions=(
            PauseActionPresentation(
                "Resume",
                "Return to the run.",
                "pause_resume",
                "",
                "success",
            ),
            PauseActionPresentation(
                "S Save",
                "Persist the run.",
                "pause_save",
                "",
                "info",
            ),
            menu_action,
            PauseActionPresentation(
                "T Settings",
                "Display, motion, and controls.",
                "pause_settings",
                "",
                "selection",
            ),
            PauseActionPresentation(
                "F1 Player Guide",
                "Lessons plus shortcut reference.",
                "pause_help",
                "",
                "info",
            ),
            PauseActionPresentation(
                "Q Quit",
                "Close the 2D shell.",
                "pause_quit",
                "",
                "danger",
            ),
        ),
    )
