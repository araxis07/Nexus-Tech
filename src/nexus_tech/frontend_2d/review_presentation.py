"""Pure responsive presentation policy for post-run finding cards."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ReviewFindingCardLayout", "build_review_finding_card_layout"]

_CARD_GAP = 10
_MIN_READABLE_CARD_HEIGHT = 100
_MAX_CARD_HEIGHT = 112
_REMAINING_LABEL_HEIGHT = 18


@dataclass(frozen=True)
class ReviewFindingCardLayout:
    """Vertical budget for the visible finding cards and overflow label."""

    visible_count: int
    card_height: int
    card_gap: int
    remaining_label_height: int


def build_review_finding_card_layout(
    *,
    available_height: int,
    finding_count: int,
    minimum_card_height: int = _MIN_READABLE_CARD_HEIGHT,
    maximum_card_height: int = _MAX_CARD_HEIGHT,
) -> ReviewFindingCardLayout:
    """Give each visible finding enough room for a two-line cause and lesson."""

    safe_height = max(0, available_height)
    safe_count = max(0, finding_count)
    safe_minimum = max(1, minimum_card_height)
    safe_maximum = max(safe_minimum, maximum_card_height)
    if safe_count == 0:
        return ReviewFindingCardLayout(0, 0, _CARD_GAP, 0)

    readable_capacity = max(
        1,
        (safe_height + _CARD_GAP) // (safe_minimum + _CARD_GAP),
    )
    visible_count = min(safe_count, readable_capacity)
    remaining_label_height = _REMAINING_LABEL_HEIGHT if visible_count < safe_count else 0
    card_budget = max(
        1,
        safe_height - remaining_label_height - _CARD_GAP * max(0, visible_count - 1),
    )
    card_height = min(safe_maximum, max(1, card_budget // visible_count))
    return ReviewFindingCardLayout(
        visible_count=visible_count,
        card_height=card_height,
        card_gap=_CARD_GAP,
        remaining_label_height=remaining_label_height,
    )
