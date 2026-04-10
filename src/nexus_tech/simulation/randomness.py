"""Seedable randomness for deterministic tests."""

import base64
import pickle
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

    def export_state(self) -> str:
        """Serialize the internal RNG state to a portable string."""

        raw_state = pickle.dumps(self._random.getstate())
        return base64.b64encode(raw_state).decode("ascii")

    @classmethod
    def from_state(
        cls,
        seed: Optional[int] = None,
        exported_state: Optional[str] = None,
    ) -> "RandomSource":
        """Restore an RNG from a serialized state token."""

        rng = cls(seed=seed)
        if exported_state is None:
            return rng

        try:
            decoded_state = base64.b64decode(exported_state.encode("ascii"))
            restored_state = pickle.loads(decoded_state)
        except (ValueError, pickle.PickleError) as error:
            raise ValueError("Invalid RNG state.") from error

        rng._random.setstate(restored_state)
        return rng
