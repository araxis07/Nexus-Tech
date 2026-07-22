"""Pure post-run navigation policy for the 2D review scene."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "ReviewNavigationAction",
    "ReviewNavigationPolicy",
    "build_review_navigation_policy",
]


@dataclass(frozen=True)
class ReviewNavigationAction:
    """One footer-owned action exposed by a review scene."""

    title: str
    detail: str
    kind: str
    tone: str


@dataclass(frozen=True)
class ReviewNavigationPolicy:
    """Ordered review actions derived without rendering or persistence access."""

    actions: tuple[ReviewNavigationAction, ...]


def build_review_navigation_policy(
    *,
    primary_title: str,
    primary_detail: str,
    allow_save: bool,
    archive_saved: bool,
    progress_available: bool,
) -> ReviewNavigationPolicy:
    """Keep the existing return route while exposing the next replay step."""

    actions = [
        ReviewNavigationAction(
            title=primary_title,
            detail=primary_detail,
            kind="review_primary",
            tone="primary",
        )
    ]
    if allow_save and not archive_saved:
        actions.append(
            ReviewNavigationAction(
                title="S Save & Archive",
                detail="Record this ending for progression.",
                kind="review_save",
                tone="success",
            )
        )
    elif archive_saved and progress_available:
        actions.append(
            ReviewNavigationAction(
                title="6 Open Progress",
                detail="Review route mastery and choose the next route.",
                kind="review_progress",
                tone="info",
            )
        )
    return ReviewNavigationPolicy(actions=tuple(actions))
