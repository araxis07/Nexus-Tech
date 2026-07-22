"""Pure action-ownership policy for shared 2D scene chrome."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "SceneActionOwner",
    "SceneChromePolicy",
    "resolve_review_scene_chrome",
    "resolve_run_scene_chrome",
    "resolve_title_scene_chrome",
    "resolve_turn_summary_scene_chrome",
]


class SceneActionOwner(StrEnum):
    """The single visible region responsible for a scene's contextual actions."""

    CONTENT = "content"
    FOOTER = "footer"
    NAVIGATION = "navigation"
    OVERLAY = "overlay"


@dataclass(frozen=True)
class SceneChromePolicy:
    """Shared frame policy derived without pygame or gameplay state."""

    action_owner: SceneActionOwner

    @property
    def navigation_visible(self) -> bool:
        """Reserve and render the navigation rail only when it owns the actions."""

        return self.action_owner is SceneActionOwner.NAVIGATION


def resolve_title_scene_chrome(
    *,
    mode: str,
    blocking_overlay_visible: bool,
) -> SceneChromePolicy:
    """Keep menu actions in content and submode recovery in navigation."""

    if blocking_overlay_visible:
        return SceneChromePolicy(SceneActionOwner.OVERLAY)
    if mode == "menu":
        return SceneChromePolicy(SceneActionOwner.CONTENT)
    return SceneChromePolicy(SceneActionOwner.NAVIGATION)


def resolve_run_scene_chrome(*, pause_overlay_visible: bool) -> SceneChromePolicy:
    """Give Pause exclusive ownership while retaining live-run recovery navigation."""

    owner = SceneActionOwner.OVERLAY if pause_overlay_visible else SceneActionOwner.NAVIGATION
    return SceneChromePolicy(owner)


def resolve_review_scene_chrome() -> SceneChromePolicy:
    """Keep completed-run actions in the review footer."""

    return SceneChromePolicy(SceneActionOwner.FOOTER)


def resolve_turn_summary_scene_chrome() -> SceneChromePolicy:
    """Keep Continue, Save, and Close in the turn-summary footer."""

    return SceneChromePolicy(SceneActionOwner.FOOTER)
