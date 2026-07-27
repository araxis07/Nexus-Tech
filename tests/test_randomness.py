from __future__ import annotations

import base64
import pickle
import random

import pytest

from nexus_tech.simulation.randomness import RandomSource


def test_random_source_exports_json_state_and_restores_next_roll() -> None:
    source = RandomSource(seed=17)
    source.randint(1, 100)

    exported_state = source.export_state()
    expected_next_roll = source.randint(1, 100)
    restored = RandomSource.from_state(seed=17, exported_state=exported_state)

    assert exported_state.startswith("json-v1:")
    assert restored.randint(1, 100) == expected_next_roll


def test_random_source_restores_primitive_legacy_pickle_state() -> None:
    legacy_random = random.Random(41)
    legacy_random.randint(1, 100)
    exported_state = base64.b64encode(pickle.dumps(legacy_random.getstate())).decode("ascii")
    expected_next_roll = legacy_random.randint(1, 100)

    restored = RandomSource.from_state(seed=41, exported_state=exported_state)

    assert restored.randint(1, 100) == expected_next_roll


def test_random_source_rejects_legacy_pickle_global_lookup() -> None:
    exported_state = base64.b64encode(pickle.dumps(len)).decode("ascii")

    with pytest.raises(ValueError, match="Invalid RNG state"):
        RandomSource.from_state(seed=7, exported_state=exported_state)


def test_random_source_rejects_oversized_state_before_decoding() -> None:
    exported_state = "json-v1:" + ("A" * 65_536)

    with pytest.raises(ValueError, match="Invalid RNG state"):
        RandomSource.from_state(seed=7, exported_state=exported_state)
