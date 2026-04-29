"""Meta-progression summaries derived from archived runs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.money import quantize_money
from nexus_tech.persistence.save_coordinator import RunArchiveSummary


@dataclass(frozen=True)
class MetaProgressionSummary:
    """Compact meta-layer view derived from archived runs."""

    total_runs: int
    victories: int
    best_score: int
    best_grade: str
    average_offer_value: Decimal
    unique_outcomes: tuple[str, ...]
    unlocked_achievements: tuple[str, ...]
    campaign_tier: str
    next_goal: str


def summarize_meta_progression(
    archives: list[RunArchiveSummary],
) -> MetaProgressionSummary:
    """Collapse archived completed runs into one progression summary."""

    if not archives:
        return MetaProgressionSummary(
            total_runs=0,
            victories=0,
            best_score=0,
            best_grade="-",
            average_offer_value=Decimal("0.00"),
            unique_outcomes=tuple(),
            unlocked_achievements=("first_archive_pending",),
            campaign_tier="unranked",
            next_goal="Finish and archive one run to unlock campaign progression.",
        )

    victories = sum(1 for archive in archives if archive.victory_achieved)
    best_archive = max(archives, key=lambda archive: archive.total_score)
    unique_outcomes = tuple(
        sorted({archive.exit_outcome for archive in archives if archive.exit_outcome})
    )
    badge_pool = {badge for archive in archives for badge in archive.achievement_badges}
    average_offer_value = quantize_money(
        sum((archive.offer_value for archive in archives), Decimal("0.00")) / Decimal(len(archives))
    )

    unlocks: list[str] = ["first_archive"]
    if victories >= 1:
        unlocks.append("first_victory")
    if len(archives) >= 3:
        unlocks.append("repeat_operator")
    if "board_trusted" in badge_pool:
        unlocks.append("board_steward")
    if "channel_builder" in badge_pool:
        unlocks.append("channel_builder")
    if "monetization_architect" in badge_pool:
        unlocks.append("monetization_architect")
    if "governance_survivor" in badge_pool:
        unlocks.append("governance_survivor")
    if "ipo_ready" in unique_outcomes:
        unlocks.append("ipo_pathfinder")
    if "strategic_acquisition" in unique_outcomes:
        unlocks.append("strategic_closer")
    if "profitable_independence" in unique_outcomes:
        unlocks.append("independent_operator")

    campaign_tier = "bronze"
    if best_archive.total_score >= 180 or victories >= 2:
        campaign_tier = "silver"
    if best_archive.total_score >= 230 or "ipo_ready" in unique_outcomes:
        campaign_tier = "gold"
    if best_archive.total_score >= 280 and victories >= 3:
        campaign_tier = "platinum"

    if victories == 0:
        next_goal = "Push one run to a victory state to unlock the next campaign tier."
    elif "ipo_ready" not in unique_outcomes:
        next_goal = "Reach an IPO-ready ending to complete the public-market ladder."
    elif len(unlocks) < 6:
        next_goal = "Diversify outcomes and badges across more completed runs."
    else:
        next_goal = "The archive already covers the core campaign ladder."

    return MetaProgressionSummary(
        total_runs=len(archives),
        victories=victories,
        best_score=best_archive.total_score,
        best_grade=best_archive.campaign_grade,
        average_offer_value=average_offer_value,
        unique_outcomes=unique_outcomes,
        unlocked_achievements=tuple(unlocks),
        campaign_tier=campaign_tier,
        next_goal=next_goal,
    )
