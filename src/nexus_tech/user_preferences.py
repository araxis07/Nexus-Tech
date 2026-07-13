"""Local player-facing preferences shared by launchers, scenes, and persistence."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import TypeVar

PreferenceEnum = TypeVar("PreferenceEnum", bound=StrEnum)


class UiScale(StrEnum):
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


class ContrastMode(StrEnum):
    """Supported 2D color-contrast profiles."""

    STANDARD = "standard"
    HIGH = "high"


class MotionMode(StrEnum):
    """User-selectable 2D motion intensity mode."""

    FULL = "full"
    REDUCED = "reduced"
    OFF = "off"

    @property
    def pulse_scale(self) -> float:
        """Return the multiplier applied to highlight pulse intensity."""

        if self is MotionMode.FULL:
            return 1.0
        if self is MotionMode.REDUCED:
            return 0.38
        return 0.0


def normalize_ui_scale(value: UiScale | str) -> UiScale:
    """Normalize a CLI, persisted, or API UI-scale value."""

    if isinstance(value, UiScale):
        return value
    try:
        return UiScale(value.strip().lower())
    except ValueError as error:
        allowed = ", ".join(mode.value for mode in UiScale)
        raise ValueError(f"Unknown UI scale '{value}'. Choose one of: {allowed}.") from error


def normalize_contrast_mode(value: ContrastMode | str) -> ContrastMode:
    """Normalize a CLI, persisted, or API contrast-mode value."""

    if isinstance(value, ContrastMode):
        return value
    try:
        return ContrastMode(value.strip().lower())
    except ValueError as error:
        allowed = ", ".join(mode.value for mode in ContrastMode)
        raise ValueError(f"Unknown contrast mode '{value}'. Choose one of: {allowed}.") from error


def normalize_motion_mode(value: MotionMode | str | None) -> MotionMode:
    """Normalize API, CLI, or persisted values into a supported motion mode."""

    if value is None:
        return MotionMode.FULL
    if isinstance(value, MotionMode):
        return value
    try:
        return MotionMode(str(value).lower())
    except ValueError as error:
        valid_values = ", ".join(mode.value for mode in MotionMode)
        raise ValueError(f"motion mode must be one of: {valid_values}") from error


@dataclass(frozen=True)
class FrontendPreferences:
    """One persistent local profile for 2D readability and motion."""

    ui_scale: UiScale = UiScale.STANDARD
    contrast_mode: ContrastMode = ContrastMode.STANDARD
    motion_mode: MotionMode = MotionMode.FULL

    @classmethod
    def from_values(
        cls,
        *,
        ui_scale: UiScale | str = UiScale.STANDARD,
        contrast_mode: ContrastMode | str = ContrastMode.STANDARD,
        motion_mode: MotionMode | str | None = MotionMode.FULL,
    ) -> FrontendPreferences:
        """Build a normalized preference profile from external values."""

        return cls(
            ui_scale=normalize_ui_scale(ui_scale),
            contrast_mode=normalize_contrast_mode(contrast_mode),
            motion_mode=normalize_motion_mode(motion_mode),
        )

    def with_overrides(
        self,
        *,
        ui_scale: UiScale | str | None = None,
        contrast_mode: ContrastMode | str | None = None,
        motion_mode: MotionMode | str | None = None,
    ) -> FrontendPreferences:
        """Return a copy with non-null launch overrides applied."""

        return FrontendPreferences(
            ui_scale=self.ui_scale if ui_scale is None else normalize_ui_scale(ui_scale),
            contrast_mode=(
                self.contrast_mode
                if contrast_mode is None
                else normalize_contrast_mode(contrast_mode)
            ),
            motion_mode=(
                self.motion_mode if motion_mode is None else normalize_motion_mode(motion_mode)
            ),
        )

    def cycle(self, field: str) -> FrontendPreferences:
        """Advance one supported setting to its next value."""

        if field == "ui_scale":
            return replace(self, ui_scale=_next_enum_value(UiScale, self.ui_scale))
        if field == "contrast_mode":
            return replace(
                self,
                contrast_mode=_next_enum_value(ContrastMode, self.contrast_mode),
            )
        if field == "motion_mode":
            return replace(self, motion_mode=_next_enum_value(MotionMode, self.motion_mode))
        raise ValueError(f"Unknown frontend preference field: {field}")


def _next_enum_value(
    enum_type: type[PreferenceEnum],
    current: PreferenceEnum,
) -> PreferenceEnum:
    values = tuple(enum_type)
    return values[(values.index(current) + 1) % len(values)]
