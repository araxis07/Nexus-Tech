"""Shared numeric helpers for the simulation layer."""

from decimal import Decimal

from nexus_tech.domain.constants import ATTRIBUTE_MAX, ATTRIBUTE_MIN, ONE_RATE, ZERO_RATE
from nexus_tech.domain.money import quantize_rate


def clamp_int(
    value: int,
    minimum: int = ATTRIBUTE_MIN,
    maximum: int = ATTRIBUTE_MAX,
) -> int:
    """Clamp an integer between the provided bounds."""

    return max(minimum, min(maximum, value))


def clamp_rate(value: Decimal) -> Decimal:
    """Clamp a Decimal rate to the inclusive 0..1 range."""

    return quantize_rate(max(ZERO_RATE, min(ONE_RATE, value)))
