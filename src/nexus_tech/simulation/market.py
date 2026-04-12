"""Market cycle simulation and demand modifiers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import MarketCycle, MarketSegment
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.randomness import RandomLike


@dataclass(frozen=True)
class MarketProfile:
    """Demand profile implied by one market cycle."""

    acquisition_bonus: int
    churn_modifier: Decimal
    competitor_pressure_modifier: int
    segment_bonus: dict[MarketSegment, int]
    description: str


_MARKET_PROFILES = {
    MarketCycle.COOLING: MarketProfile(
        acquisition_bonus=BALANCE.market_cycle_acquisition_bonus["cooling"],
        churn_modifier=BALANCE.market_cycle_churn_modifier["cooling"],
        competitor_pressure_modifier=BALANCE.market_cycle_competitor_pressure_modifier["cooling"],
        segment_bonus={
            MarketSegment(segment): bonus
            for segment, bonus in BALANCE.market_cycle_segment_bonus["cooling"].items()
        },
        description="Demand is tighter. Buyers move slower and stability matters more.",
    ),
    MarketCycle.STEADY: MarketProfile(
        acquisition_bonus=BALANCE.market_cycle_acquisition_bonus["steady"],
        churn_modifier=BALANCE.market_cycle_churn_modifier["steady"],
        competitor_pressure_modifier=BALANCE.market_cycle_competitor_pressure_modifier["steady"],
        segment_bonus={
            MarketSegment(segment): bonus
            for segment, bonus in BALANCE.market_cycle_segment_bonus["steady"].items()
        },
        description="The market is stable. Execution quality matters more than timing.",
    ),
    MarketCycle.EXPANDING: MarketProfile(
        acquisition_bonus=BALANCE.market_cycle_acquisition_bonus["expanding"],
        churn_modifier=BALANCE.market_cycle_churn_modifier["expanding"],
        competitor_pressure_modifier=BALANCE.market_cycle_competitor_pressure_modifier["expanding"],
        segment_bonus={
            MarketSegment(segment): bonus
            for segment, bonus in BALANCE.market_cycle_segment_bonus["expanding"].items()
        },
        description="Demand is expanding. Good products can compound more easily.",
    ),
    MarketCycle.FROTHY: MarketProfile(
        acquisition_bonus=BALANCE.market_cycle_acquisition_bonus["frothy"],
        churn_modifier=BALANCE.market_cycle_churn_modifier["frothy"],
        competitor_pressure_modifier=BALANCE.market_cycle_competitor_pressure_modifier["frothy"],
        segment_bonus={
            MarketSegment(segment): bonus
            for segment, bonus in BALANCE.market_cycle_segment_bonus["frothy"].items()
        },
        description="Attention is hot, but the market is crowded and noisy.",
    ),
}


def get_market_profile(cycle: MarketCycle) -> MarketProfile:
    """Return the effective profile for a market cycle."""

    return _MARKET_PROFILES[cycle]


def advance_market_cycle(
    cycle: MarketCycle,
    turns_remaining: int,
    rng: RandomLike,
) -> tuple[MarketCycle, int, bool]:
    """Advance the market clock and transition cycles when a phase expires."""

    if turns_remaining > 1:
        return cycle, turns_remaining - 1, False

    next_cycle = _pick_next_cycle(cycle, rng)
    duration = rng.randint(
        BALANCE.market_cycle_min_duration,
        BALANCE.market_cycle_max_duration,
    )
    return next_cycle, duration, next_cycle is not cycle


def _pick_next_cycle(current_cycle: MarketCycle, rng: RandomLike) -> MarketCycle:
    weights = BALANCE.market_cycle_transition_weights[current_cycle.value]
    total_weight = sum(weight for weight in weights.values() if weight > 0)
    roll = rng.randint(1, total_weight)
    cursor = 0
    for cycle_name, weight in weights.items():
        if weight <= 0:
            continue
        cursor += weight
        if roll <= cursor:
            return MarketCycle(cycle_name)
    return current_cycle
