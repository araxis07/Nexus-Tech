"""Meta-progression summaries derived from archived runs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.money import format_money, quantize_money
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
    campaign_stage: str
    achievement_progress: str
    unlocks_remaining: tuple[str, ...]
    archive_highlights: tuple[str, ...]
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
            campaign_stage="foundation",
            achievement_progress="0/11 core achievements",
            unlocks_remaining=(
                "first_archive",
                "first_victory",
                "repeat_operator",
                "board_steward",
                "channel_builder",
                "monetization_architect",
                "support_resilient",
                "people_stable",
                "ipo_pathfinder",
                "strategic_closer",
                "independent_operator",
            ),
            archive_highlights=("No archived runs yet.",),
            next_goal="Finish and archive one run to unlock campaign progression.",
        )

    victories = sum(1 for archive in archives if archive.victory_achieved)
    best_archive = max(archives, key=lambda archive: archive.total_score)
    latest_archive = max(archives, key=lambda archive: archive.archived_at)
    unique_outcomes = tuple(
        sorted({archive.exit_outcome for archive in archives if archive.exit_outcome})
    )
    badge_pool = {badge for archive in archives for badge in archive.achievement_badges}
    best_offer = max(archives, key=lambda archive: archive.offer_value)
    average_offer_value = quantize_money(
        sum((archive.offer_value for archive in archives), Decimal("0.00")) / Decimal(len(archives))
    )

    achievement_checks = (
        ("first_archive", True),
        ("first_victory", victories >= 1),
        ("repeat_operator", len(archives) >= 3),
        ("board_steward", "board_trusted" in badge_pool),
        ("channel_builder", "channel_builder" in badge_pool),
        ("monetization_architect", "monetization_architect" in badge_pool),
        ("support_resilient", "support_resilient" in badge_pool),
        ("people_stable", "people_stable" in badge_pool),
        ("ipo_pathfinder", "ipo_ready" in unique_outcomes),
        ("strategic_closer", "strategic_acquisition" in unique_outcomes),
        ("independent_operator", "profitable_independence" in unique_outcomes),
    )
    unlocks = [name for name, unlocked in achievement_checks if unlocked]
    unlocks_remaining = tuple(name for name, unlocked in achievement_checks if not unlocked)

    campaign_tier = "bronze"
    if best_archive.total_score >= 180 or victories >= 2:
        campaign_tier = "silver"
    if best_archive.total_score >= 230 or "ipo_ready" in unique_outcomes:
        campaign_tier = "gold"
    if best_archive.total_score >= 280 and victories >= 3:
        campaign_tier = "platinum"

    campaign_stage = "foundation"
    if len(unlocks) >= 3 or best_archive.total_score >= 140:
        campaign_stage = "portfolio"
    if len(unlocks) >= 5 or victories >= 1:
        campaign_stage = "operator"
    if len(unlocks) >= 8 or "ipo_ready" in unique_outcomes:
        campaign_stage = "institutional"
    if len(unlocks) >= 10 and victories >= 2:
        campaign_stage = "franchise"

    archive_highlights = (
        f"Latest archive: {latest_archive.exit_outcome} on turn {latest_archive.completed_turn}.",
        (f"Best offer: {format_money(best_offer.offer_value)} from {best_offer.exit_outcome}."),
        (
            f"Outcome coverage: {len(unique_outcomes)} path(s) across "
            f"{len({archive.campaign_grade for archive in archives})} grade tier(s)."
        ),
    )
    achievement_progress = f"{len(unlocks)}/{len(achievement_checks)} core achievements"

    if victories == 0:
        next_goal = "Push one run to a victory state to unlock the next campaign tier."
    elif unlocks_remaining:
        next_goal = f"Next unlock target: {unlocks_remaining[0]}."
    elif "ipo_ready" not in unique_outcomes:
        next_goal = "Reach an IPO-ready ending to complete the public-market ladder."
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
        campaign_stage=campaign_stage,
        achievement_progress=achievement_progress,
        unlocks_remaining=unlocks_remaining,
        archive_highlights=archive_highlights,
        next_goal=next_goal,
    )
