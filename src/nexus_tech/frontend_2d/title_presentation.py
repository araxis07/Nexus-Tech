"""Pure first-run presentation policy for the 2D title shell."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "TitleActionPresentation",
    "TitleHeaderLayout",
    "TitleMenuPresentation",
    "build_quick_start_actions",
    "build_title_menu_presentation",
    "resolve_title_header_layout",
]


@dataclass(frozen=True)
class TitleActionPresentation:
    """One title-shell action with availability separate from routing."""

    title: str
    detail: str
    payload: str
    tone: str
    enabled: bool = True


@dataclass(frozen=True)
class TitleHeaderLayout:
    """Vertical lanes for title-shell subtitle and archive progress copy."""

    subtitle_offset: int
    subtitle_height: int
    subtitle_max_lines: int
    mission_offset: int
    mission_height: int


@dataclass(frozen=True)
class TitleMenuPresentation:
    """Ordered title actions and guidance derived from local progress."""

    primary_actions: tuple[TitleActionPresentation, ...]
    secondary_actions: tuple[TitleActionPresentation, ...]
    quit_action: TitleActionPresentation
    footer_line: str


def resolve_title_header_layout(*, panel_height: int) -> TitleHeaderLayout:
    """Keep compact archive progress above the title panel's bottom border."""

    if panel_height <= 96:
        return TitleHeaderLayout(
            subtitle_offset=0,
            subtitle_height=18,
            subtitle_max_lines=1,
            mission_offset=22,
            mission_height=16,
        )
    return TitleHeaderLayout(
        subtitle_offset=0,
        subtitle_height=36,
        subtitle_max_lines=2,
        mission_offset=38,
        mission_height=16,
    )


def build_title_menu_presentation(
    *,
    has_saves: bool,
    current_step_title: str,
    current_step_label: str,
    progress_label: str,
) -> TitleMenuPresentation:
    """Lead first-time players to New Game and returning players to Continue."""

    step_title = " ".join(current_step_title.split()) or "Guided Opening"
    step_label = " ".join(current_step_label.split()) or "1/6"
    safe_progress = " ".join(progress_label.split()) or "0/6 complete"
    if has_saves:
        continue_action = TitleActionPresentation(
            title="1 Continue Last",
            detail=f"Resume {step_title} ({step_label}).",
            payload="continue",
            tone="success",
        )
        new_game_action = TitleActionPresentation(
            title="2 New Game",
            detail="Start another guided campaign.",
            payload="new_wizard",
            tone="info",
        )
        footer_line = (
            "Menu: 1 continue, 2 new, 3 guide, 4 saves, 5 archives, 6 progress, 7 settings, 8 quit."
        )
    else:
        continue_action = TitleActionPresentation(
            title="1 Continue Last",
            detail="Unavailable until the first run is saved.",
            payload="continue",
            tone="muted",
            enabled=False,
        )
        new_game_action = TitleActionPresentation(
            title="2 New Game",
            detail="Start here: launch the guided first campaign.",
            payload="new_wizard",
            tone="success",
        )
        footer_line = (
            "Start: 2 new game, 3 guide, 4 saves, 5 archives, 6 progress, 7 settings, 8 quit."
        )

    return TitleMenuPresentation(
        primary_actions=(continue_action, new_game_action),
        secondary_actions=(
            TitleActionPresentation(
                "3 How to Play",
                "Goal, controls, and first turn.",
                "guide",
                "info",
            ),
            TitleActionPresentation(
                "4 Manage Saves",
                "Load, rename, copy, or delete.",
                "load_slots",
                "info",
            ),
            TitleActionPresentation(
                "5 Run Archives",
                "Completed runs and lessons.",
                "archives",
                "warning",
            ),
            TitleActionPresentation(
                "6 Progress",
                f"First archive {safe_progress}; routes and rewards.",
                "meta",
                "selection",
            ),
            TitleActionPresentation(
                "7 Settings",
                "Text, contrast, and motion.",
                "settings",
                "info",
            ),
        ),
        quit_action=TitleActionPresentation(
            "8 Quit",
            "Leave NEXUS TECH.",
            "quit",
            "danger",
        ),
        footer_line=footer_line,
    )


def build_quick_start_actions(
    *,
    has_saves: bool,
) -> tuple[tuple[TitleActionPresentation, ...], str]:
    """Keep Quick Start aligned with the action that can actually advance play."""

    continue_action = TitleActionPresentation(
        title="1 Continue",
        detail="Resume newest save." if has_saves else "Unavailable until a run is saved.",
        payload="continue",
        tone="success" if has_saves else "muted",
        enabled=has_saves,
    )
    new_game_action = TitleActionPresentation(
        title="2 New Game",
        detail="Open wizard.",
        payload="new_wizard",
        tone="info" if has_saves else "success",
    )
    back_action = TitleActionPresentation(
        title="9 Back",
        detail="Return to menu.",
        payload="menu",
        tone="muted",
    )
    footer_line = (
        "Quick Start: 1 continues, 2 opens wizard, 9 or Esc returns to menu."
        if has_saves
        else "Quick Start: 2 opens the first-game wizard; 9 or Esc returns to menu."
    )
    return (new_game_action, continue_action, back_action), footer_line
