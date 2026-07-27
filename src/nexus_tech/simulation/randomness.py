"""Seedable randomness for deterministic tests."""

from __future__ import annotations

import base64
import binascii
import io
import json
import pickle
import random
from typing import Protocol

_STATE_PREFIX = "json-v1:"
_MAX_EXPORTED_STATE_LENGTH = 65_536


class RandomLike(Protocol):
    """Minimal random protocol used by the simulation."""

    def randint(self, start: int, end: int) -> int:
        """Return an integer in the inclusive range."""


class RandomSource:
    """Thin wrapper around `random.Random` to make seeding explicit."""

    def __init__(self, seed: int | None = None) -> None:
        self.seed = seed
        self._random = random.Random(seed)

    def randint(self, start: int, end: int) -> int:
        return self._random.randint(start, end)

    def export_state(self) -> str:
        """Serialize the internal RNG state to a portable string."""

        raw_state = json.dumps(
            self._random.getstate(),
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
        encoded_state = base64.urlsafe_b64encode(raw_state).decode("ascii")
        return f"{_STATE_PREFIX}{encoded_state}"

    @classmethod
    def from_state(
        cls,
        seed: int | None = None,
        exported_state: str | None = None,
    ) -> RandomSource:
        """Restore an RNG from a serialized state token."""

        rng = cls(seed=seed)
        if exported_state is None:
            return rng

        try:
            restored_state = _decode_state(exported_state)
            rng._random.setstate(restored_state)
        except (
            binascii.Error,
            EOFError,
            json.JSONDecodeError,
            pickle.PickleError,
            TypeError,
            UnicodeError,
            ValueError,
        ) as error:
            raise ValueError("Invalid RNG state.") from error

        return rng


class _RestrictedStateUnpickler(pickle.Unpickler):
    """Read primitive legacy RNG tuples without permitting global object loading."""

    def find_class(self, module: str, name: str) -> object:
        raise pickle.UnpicklingError(
            f"Global object loading is forbidden in RNG state: {module}.{name}"
        )


def _decode_state(exported_state: str) -> tuple[object, ...]:
    if len(exported_state) > _MAX_EXPORTED_STATE_LENGTH:
        raise ValueError("RNG state exceeds the maximum encoded size.")

    if exported_state.startswith(_STATE_PREFIX):
        encoded_state = exported_state.removeprefix(_STATE_PREFIX)
        decoded_state = base64.b64decode(
            encoded_state.encode("ascii"),
            altchars=b"-_",
            validate=True,
        )
        restored_state = _tuple_tree(json.loads(decoded_state.decode("utf-8")))
    else:
        decoded_state = base64.b64decode(exported_state.encode("ascii"), validate=True)
        stream = io.BytesIO(decoded_state)
        restored_state = _RestrictedStateUnpickler(stream).load()
        if stream.read(1):
            raise pickle.UnpicklingError("Legacy RNG state contains trailing data.")

    _validate_state_shape(restored_state)
    return restored_state


def _tuple_tree(value: object) -> object:
    if isinstance(value, list):
        return tuple(_tuple_tree(item) for item in value)
    return value


def _validate_state_shape(state: object) -> None:
    if not isinstance(state, tuple) or len(state) != 3:
        raise ValueError("RNG state must be a three-part tuple.")

    version, internal_state, gaussian_cache = state
    if type(version) is not int or version not in (2, 3):
        raise ValueError("RNG state version is unsupported.")
    if (
        not isinstance(internal_state, tuple)
        or len(internal_state) != 625
        or any(type(value) is not int for value in internal_state)
    ):
        raise ValueError("RNG internal state is invalid.")
    if gaussian_cache is not None and type(gaussian_cache) not in (int, float):
        raise ValueError("RNG Gaussian cache is invalid.")
