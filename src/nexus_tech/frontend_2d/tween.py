"""Small tween helpers for the lightweight 2D frontend."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import exp


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


def normalize_motion_mode(value: MotionMode | str | None) -> MotionMode:
    """Normalize API/CLI values into a supported motion mode."""

    if value is None:
        return MotionMode.FULL
    if isinstance(value, MotionMode):
        return value
    try:
        return MotionMode(str(value).lower())
    except ValueError as error:
        valid_values = ", ".join(mode.value for mode in MotionMode)
        raise ValueError(f"motion mode must be one of: {valid_values}") from error


@dataclass
class TweenValue:
    """One smoothly animated scalar."""

    value: float
    target: float
    speed: float = 8.0

    def update(self, dt: float) -> None:
        """Move the current value toward its target."""

        if dt <= 0 or self.value == self.target:
            return
        blend = 1.0 - exp(-self.speed * dt)
        self.value += (self.target - self.value) * blend
        if abs(self.target - self.value) < 0.001:
            self.value = self.target

    def retarget(self, target: float) -> None:
        """Set a new destination while keeping the current position."""

        self.target = target

    def snap(self, target: float) -> None:
        """Jump to the target immediately."""

        self.value = target
        self.target = target


class TweenBank:
    """Store multiple named tween values."""

    def __init__(self, *, speed: float = 8.0) -> None:
        self._speed = speed
        self._values: dict[str, TweenValue] = {}

    def sync_targets(self, targets: dict[str, float]) -> None:
        """Synchronize a target map into the tween bank."""

        current_keys = set(self._values)
        incoming_keys = set(targets)
        for key, target in targets.items():
            if key not in self._values:
                self._values[key] = TweenValue(target, target, self._speed)
                continue
            self._values[key].retarget(target)
        for stale_key in current_keys - incoming_keys:
            self._values.pop(stale_key, None)

    def update(self, dt: float) -> None:
        """Advance all tweens one frame."""

        for tween in self._values.values():
            tween.update(dt)

    def get(self, key: str, fallback: float = 0.0) -> float:
        """Read the current tween value if present."""

        tween = self._values.get(key)
        return tween.value if tween is not None else fallback


@dataclass
class PulseValue:
    """One short-lived highlight pulse."""

    value: float
    decay: float

    def update(self, dt: float) -> None:
        """Fade the pulse back toward zero."""

        if dt <= 0 or self.value <= 0:
            return
        self.value = max(0.0, self.value - dt * self.decay)


class PulseBank:
    """Store multiple named highlight pulses."""

    def __init__(self, *, decay: float = 1.8, intensity_scale: float = 1.0) -> None:
        self._decay = decay
        self._intensity_scale = max(0.0, min(1.0, intensity_scale))
        self._values: dict[str, PulseValue] = {}

    @property
    def intensity_scale(self) -> float:
        """Return the configured intensity multiplier for new pulses."""

        return self._intensity_scale

    def trigger(self, key: str, *, intensity: float = 1.0, decay: float | None = None) -> None:
        """Start or refresh one pulse."""

        clamped = max(0.0, min(1.0, intensity)) * self._intensity_scale
        if clamped <= 0:
            return
        pulse = self._values.get(key)
        if pulse is None:
            self._values[key] = PulseValue(clamped, decay or self._decay)
            return
        pulse.value = max(pulse.value, clamped)
        pulse.decay = decay or pulse.decay

    def update(self, dt: float) -> None:
        """Advance all live pulses one frame."""

        stale_keys: list[str] = []
        for key, pulse in self._values.items():
            pulse.update(dt)
            if pulse.value <= 0:
                stale_keys.append(key)
        for key in stale_keys:
            self._values.pop(key, None)

    def live_count(self) -> int:
        """Return the number of active pulse keys."""

        return len(self._values)

    def total_intensity(self) -> float:
        """Return the summed intensity of all active pulses."""

        return sum(pulse.value for pulse in self._values.values())

    def prune(
        self,
        *,
        max_count: int,
        min_value: float = 0.0,
        protected_prefixes: tuple[str, ...] = (),
    ) -> int:
        """Drop the weakest unprotected pulses when the bank gets too crowded."""

        if len(self._values) <= max_count:
            return 0

        protected_keys = {
            key
            for key in self._values
            if any(key.startswith(prefix) for prefix in protected_prefixes)
        }
        removable = [
            (key, pulse.value)
            for key, pulse in self._values.items()
            if key not in protected_keys and pulse.value <= max(0.0, min_value)
        ]
        removable.sort(key=lambda item: item[1])
        removed = 0
        for key, _value in removable:
            if len(self._values) <= max_count:
                break
            self._values.pop(key, None)
            removed += 1

        if len(self._values) <= max_count:
            return removed

        removable = [
            (key, pulse.value) for key, pulse in self._values.items() if key not in protected_keys
        ]
        removable.sort(key=lambda item: item[1])
        for key, _value in removable:
            if len(self._values) <= max_count:
                break
            self._values.pop(key, None)
            removed += 1
        return removed

    def get(self, key: str, fallback: float = 0.0) -> float:
        """Read the live pulse value if present."""

        pulse = self._values.get(key)
        return pulse.value if pulse is not None else fallback
