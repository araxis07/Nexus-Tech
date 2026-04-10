"""Decimal-safe helpers for money and rates."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Union

from nexus_tech.domain.constants import PERCENT_SCALE

NumberInput = Union[Decimal, int, float, str]  # noqa: UP007
MONEY_PLACES = Decimal("0.01")
RATE_PLACES = Decimal("0.0001")


def quantize_money(value: NumberInput) -> Decimal:
    """Normalize a numeric value into a 2-decimal money representation."""

    return Decimal(str(value)).quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def quantize_rate(value: NumberInput) -> Decimal:
    """Normalize a numeric value into a compact fractional rate."""

    return Decimal(str(value)).quantize(RATE_PLACES, rounding=ROUND_HALF_UP)


def format_money(value: Decimal) -> str:
    """Render money for terminal output."""

    return f"${quantize_money(value):,.2f}"


def format_rate(value: Decimal) -> str:
    """Render a Decimal rate as a percentage string."""

    percentage = quantize_rate(value) * PERCENT_SCALE
    return f"{percentage:.1f}%"
