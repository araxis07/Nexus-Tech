"""Accessibility profiles shared by all 2D frontend entry points."""

from __future__ import annotations

from enum import Enum


class UiScale(str, Enum):
    """Supported 2D typography scales."""

    COMPACT = "compact"
    STANDARD = "standard"
    LARGE = "large"

    @property
    def factor(self) -> float:
        """Return the font-size multiplier for this profile."""

        return {
            UiScale.COMPACT: 0.90,
            UiScale.STANDARD: 1.00,
            UiScale.LARGE: 1.12,
        }[self]


class ContrastMode(str, Enum):
    """Supported 2D color-contrast profiles."""

    STANDARD = "standard"
    HIGH = "high"


def normalize_ui_scale(value: UiScale | str) -> UiScale:
    """Normalize a CLI or API UI-scale value."""

    if isinstance(value, UiScale):
        return value
    try:
        return UiScale(value.strip().lower())
    except ValueError as error:
        allowed = ", ".join(mode.value for mode in UiScale)
        raise ValueError(f"Unknown UI scale '{value}'. Choose one of: {allowed}.") from error


def normalize_contrast_mode(value: ContrastMode | str) -> ContrastMode:
    """Normalize a CLI or API contrast-mode value."""

    if isinstance(value, ContrastMode):
        return value
    try:
        return ContrastMode(value.strip().lower())
    except ValueError as error:
        allowed = ", ".join(mode.value for mode in ContrastMode)
        raise ValueError(f"Unknown contrast mode '{value}'. Choose one of: {allowed}.") from error
