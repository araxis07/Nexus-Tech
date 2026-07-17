"""Transient state shared by the lightweight 2D scenes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from nexus_tech.frontend_2d.event_queue import FrontendEvent

__all__ = [
    "ActionFeedbackCue",
    "ActorSpriteBounds",
    "ActorSpriteClip",
    "ClickTarget",
    "FirstTurnGuideStep",
    "ImpactCue",
    "InspectorMemoryState",
    "LateGameChoreographyCue",
    "NewGameWizardState",
    "OverlayExitCue",
    "PendingChoiceCue",
    "TextInputModalState",
    "TimedFrontendEvent",
]


@dataclass(frozen=True)
class ClickTarget:
    """One clickable hitbox registered during the last draw pass."""

    kind: str
    payload: str
    rect: object


@dataclass(frozen=True)
class FirstTurnGuideStep:
    """One compact onboarding checkpoint rendered inside the live run dashboard."""

    label: str
    detail: str
    done: bool
    accent: tuple[int, int, int]


@dataclass
class TimedFrontendEvent:
    """Mutable event card with time remaining."""

    payload: FrontendEvent
    time_left: float


@dataclass(frozen=True)
class ActionFeedbackCue:
    """Short-lived command-specific animation feedback."""

    command: str
    label: str
    family: str
    accent: tuple[int, int, int]
    targets: tuple[str, ...]
    time_left: float
    duration: float
    outcome: str = "success"
    detail: str = ""


@dataclass(frozen=True)
class ImpactCue:
    """Short-lived visible delta feedback after state-changing actions."""

    label: str
    value_text: str
    tone: str
    accent: tuple[int, int, int]
    targets: tuple[str, ...]
    time_left: float
    duration: float


@dataclass(frozen=True)
class OverlayExitCue:
    """Short exit shimmer after a modal overlay closes."""

    key: str
    label: str
    accent: tuple[int, int, int]
    time_left: float
    duration: float


@dataclass(frozen=True)
class PendingChoiceCue:
    """Short consequence flash after resolving a pending event choice."""

    label: str
    detail: str
    accent: tuple[int, int, int]
    time_left: float
    duration: float


@dataclass(frozen=True)
class LateGameChoreographyCue:
    """Short late-game command cue tied to cockpit, capital, and board lanes."""

    command: str
    label: str
    detail: str
    family: str
    accent: tuple[int, int, int]
    targets: tuple[str, ...]
    time_left: float
    duration: float


_ACTOR_STATE_POSES: dict[str, str] = {
    "idle": "steady",
    "build": "build",
    "handoff": "handoff",
    "shipping": "handoff",
    "success": "win",
    "celebrating": "win",
    "coaching": "coach",
    "negotiating": "deal",
    "risk": "warn",
    "alert": "warn",
    "blocked": "block",
    "firefighting": "fire",
}


def _actor_pose_key(state: str, pose: str | None = None) -> str:
    return pose or _ACTOR_STATE_POSES.get(state, "steady")


@dataclass(frozen=True)
class ActorSpriteClip:
    """One deterministic shape-sprite actor beat rendered by the 2D frontend."""

    key: str
    label: str
    role: str
    state: str
    accent: tuple[int, int, int]
    lane: str
    delay: float = 0.0
    phase_offset: float = 0.0
    pose: str | None = None

    @property
    def pose_key(self) -> str:
        """Return the readable pose cue used by the lightweight sprite renderer."""

        return _actor_pose_key(self.state, self.pose)


@dataclass(frozen=True)
class ActorSpriteBounds:
    """One actor sprite footprint from the last draw pass."""

    key: str
    lane: str
    left: int
    top: int
    width: int
    height: int


@dataclass
class TextInputModalState:
    """One live text-input modal used by the 2D frontend."""

    title: str
    description: str
    severity: str
    submit_title: str
    submit_detail: str
    text: str
    placeholder: str
    on_submit: Callable[[str], None]


@dataclass
class NewGameWizardState:
    """Mutable configuration used by the 2D new-game wizard."""

    scenario_index: int
    difficulty_index: int
    campaign_start_index: int
    goal_index: int
    company_name: str
    product_name: str
    slot_name: str
    seed_text: str = ""


@dataclass(frozen=True)
class InspectorMemoryState:
    """Remember one panel's last inspector focus so reopening is less noisy."""

    section_key: str
    page: int
    item_index: int
    sort_mode_index: int
    filter_mode_index: int
