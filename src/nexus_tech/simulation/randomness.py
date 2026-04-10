"""Seedable randomness for deterministic tests."""

import random
from typing import Optional, Protocol


class RandomLike(Protocol):
    """Minimal random protocol used by the simulation."""

    def randint(self, start: int, end: int) -> int:
        """Return an integer in the inclusive range."""


class RandomSource:
    """Thin wrapper around `random.Random` to make seeding explicit."""

    def __init__(self, seed: Optional[int] = None) -> None:
        self.seed = seed
        self._random = random.Random(seed)

    def randint(self, start: int, end: int) -> int:
        return self._random.randint(start, end)
