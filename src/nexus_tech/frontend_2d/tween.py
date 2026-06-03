"""Small tween helpers for the lightweight 2D frontend."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp


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

    def __init__(self, *, decay: float = 1.8) -> None:
        self._decay = decay
        self._values: dict[str, PulseValue] = {}

    def trigger(self, key: str, *, intensity: float = 1.0, decay: float | None = None) -> None:
        """Start or refresh one pulse."""

        clamped = max(0.0, min(1.0, intensity))
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

    def get(self, key: str, fallback: float = 0.0) -> float:
        """Read the live pulse value if present."""

        pulse = self._values.get(key)
        return pulse.value if pulse is not None else fallback
