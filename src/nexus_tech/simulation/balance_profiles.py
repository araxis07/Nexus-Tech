"""Named balance presets for demos and tuning."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.domain.models import BalanceProfileId, DifficultyMode


@dataclass(frozen=True)
class BalanceProfile:
    """Recommended balance-lab settings."""

    profile_id: BalanceProfileId
    difficulty_mode: DifficultyMode
    runs: int
    turns: int
    description: str


_BALANCE_PROFILES = {
    BalanceProfileId.DEMO: BalanceProfile(
        profile_id=BalanceProfileId.DEMO,
        difficulty_mode=DifficultyMode.BUILDER,
        runs=2,
        turns=6,
        description="Short, low-pressure checks for live demos.",
    ),
    BalanceProfileId.STANDARD: BalanceProfile(
        profile_id=BalanceProfileId.STANDARD,
        difficulty_mode=DifficultyMode.STANDARD,
        runs=4,
        turns=10,
        description="Default balance review across mid-length runs.",
    ),
    BalanceProfileId.HARD: BalanceProfile(
        profile_id=BalanceProfileId.HARD,
        difficulty_mode=DifficultyMode.FOUNDER,
        runs=5,
        turns=12,
        description="Founder-pressure checks for harsher economy tuning.",
    ),
    BalanceProfileId.LONG_RUN: BalanceProfile(
        profile_id=BalanceProfileId.LONG_RUN,
        difficulty_mode=DifficultyMode.STANDARD,
        runs=3,
        turns=18,
        description="Longer runs that expose late-game scale pressure.",
    ),
}


def list_balance_profiles() -> tuple[BalanceProfile, ...]:
    """Return named balance profiles."""

    return tuple(_BALANCE_PROFILES.values())


def get_balance_profile(profile_id: BalanceProfileId) -> BalanceProfile:
    """Return one balance profile."""

    return _BALANCE_PROFILES[profile_id]
