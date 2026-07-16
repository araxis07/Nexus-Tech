"""Progressive-disclosure policy for dense 2D deep-dive panels."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.frontend_2d.viewmodels import (
    DeepDiveActionViewModel,
    DeepDivePanelViewModel,
)

_ENDGAME_PRIMARY_ACTION_LABELS = ("Recommended Fix", "Review Main Risk")
_ENDGAME_GUIDED_DETAIL_PREFIXES = ("Projected path:", "Blocked paths:", "Next move:")


@dataclass(frozen=True)
class PanelDisclosure:
    """Visible panel content plus an optional local detail toggle."""

    action_heading: str
    actions: tuple[DeepDiveActionViewModel, ...]
    detail_lines: tuple[str, ...]
    hidden_action_count: int = 0
    toggle_label: str = ""
    toggle_detail: str = ""


def build_panel_disclosure(
    panel: DeepDivePanelViewModel,
    *,
    expanded: bool = False,
) -> PanelDisclosure:
    """Keep endgame choices guided by default without removing any command route."""

    if panel.key != "endgame":
        return PanelDisclosure(
            action_heading="Panel Actions",
            actions=panel.actions,
            detail_lines=panel.detail_lines,
        )

    primary_actions = tuple(
        action
        for label in _ENDGAME_PRIMARY_ACTION_LABELS
        for action in panel.actions
        if action.label == label
    )
    if not primary_actions:
        primary_actions = panel.actions[:2]
    hidden_action_count = max(0, len(panel.actions) - len(primary_actions))

    if expanded or hidden_action_count == 0:
        return PanelDisclosure(
            action_heading="All Endgame Actions",
            actions=panel.actions,
            detail_lines=panel.detail_lines,
            toggle_label="V Guided" if hidden_action_count else "",
            toggle_detail=(
                "Return to the recommended fix and main risk." if hidden_action_count else ""
            ),
        )

    guided_details = tuple(
        line
        for prefix in _ENDGAME_GUIDED_DETAIL_PREFIXES
        for line in panel.detail_lines
        if line.startswith(prefix)
    )
    return PanelDisclosure(
        action_heading="Start Here",
        actions=primary_actions,
        detail_lines=guided_details or panel.detail_lines[:3],
        hidden_action_count=hidden_action_count,
        toggle_label=f"V More ({hidden_action_count})",
        toggle_detail="Reveal exit-path fixes and specialist reviews.",
    )
