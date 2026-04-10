"""Money helpers for Decimal-safe calculations."""

from decimal import ROUND_HALF_UP, Decimal
from typing import Union

MoneyInput = Union[Decimal, int, float, str]
MONEY_PLACES = Decimal("0.01")


def quantize_money(value: MoneyInput) -> Decimal:
    """Normalize a numeric value into a 2-decimal money representation."""

    return Decimal(str(value)).quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def format_money(value: Decimal) -> str:
    """Render money for terminal output."""

    return f"${quantize_money(value):,.2f}"
