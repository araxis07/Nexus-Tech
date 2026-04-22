"""Deterministic candidate pool generation for hiring decisions."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.domain.models import EmployeeRole, Seniority
from nexus_tech.simulation.randomness import RandomLike


@dataclass(frozen=True)
class CandidateProfile:
    """Lightweight candidate preview shown before hiring."""

    full_name: str
    role: EmployeeRole
    seniority: Seniority
    specialization: str
    pitch: str


_FIRST_NAMES = (
    "Ari",
    "Blair",
    "Casey",
    "Devon",
    "Eden",
    "Finley",
    "Harper",
    "Jordan",
    "Kai",
    "Morgan",
    "Quinn",
    "Riley",
)
_LAST_NAMES = (
    "Stone",
    "Vale",
    "Reed",
    "Park",
    "West",
    "Shaw",
    "Lane",
    "Cross",
    "Hayes",
    "Kline",
    "Morrow",
    "Chen",
)

_ROLE_SPECIALIZATIONS = {
    EmployeeRole.ENGINEER: ("platform", "reliability", "developer_tools", "systems"),
    EmployeeRole.DESIGNER: ("ux", "research", "enterprise_workflows", "service_design"),
    EmployeeRole.MARKETER: ("growth", "community", "field_marketing", "positioning"),
    EmployeeRole.PRODUCT_MANAGER: ("delivery", "enterprise_discovery", "pricing", "strategy"),
}

_PITCHES = {
    EmployeeRole.ENGINEER: (
        "Can reduce delivery risk on complex product work.",
        "Best fit when technical debt is becoming visible.",
    ),
    EmployeeRole.DESIGNER: (
        "Can sharpen market fit and improve buyer confidence.",
        "Useful when products need clearer workflow quality.",
    ),
    EmployeeRole.MARKETER: (
        "Can turn product momentum into more acquisition.",
        "Useful when the company needs demand without a new product.",
    ),
    EmployeeRole.PRODUCT_MANAGER: (
        "Can improve coordination across assigned work.",
        "Best fit when the portfolio has multiple active bets.",
    ),
}


def generate_candidate_pool(
    rng: RandomLike,
    *,
    count: int = 3,
) -> tuple[CandidateProfile, ...]:
    """Generate a compact, seedable candidate pool."""

    candidates: list[CandidateProfile] = []
    used_names: set[str] = set()
    roles = tuple(EmployeeRole)
    seniorities = (Seniority.JUNIOR, Seniority.MID, Seniority.SENIOR)

    while len(candidates) < count:
        full_name = _build_candidate_name(rng)
        if full_name in used_names:
            continue
        used_names.add(full_name)

        role = roles[rng.randint(0, len(roles) - 1)]
        seniority = seniorities[rng.randint(0, len(seniorities) - 1)]
        specializations = _ROLE_SPECIALIZATIONS[role]
        pitches = _PITCHES[role]

        candidates.append(
            CandidateProfile(
                full_name=full_name,
                role=role,
                seniority=seniority,
                specialization=specializations[rng.randint(0, len(specializations) - 1)],
                pitch=pitches[rng.randint(0, len(pitches) - 1)],
            )
        )

    return tuple(candidates)


def _build_candidate_name(rng: RandomLike) -> str:
    first_name = _FIRST_NAMES[rng.randint(0, len(_FIRST_NAMES) - 1)]
    last_name = _LAST_NAMES[rng.randint(0, len(_LAST_NAMES) - 1)]
    return f"{first_name} {last_name}"
