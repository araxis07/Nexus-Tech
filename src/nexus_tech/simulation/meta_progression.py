"""Meta-progression summaries derived from archived runs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.money import format_money, quantize_money
from nexus_tech.persistence.save_coordinator import RunArchiveSummary


@dataclass(frozen=True)
class AchievementDefinition:
    """Static archive-driven achievement and reward metadata."""

    achievement_id: str
    title: str
    description: str
    reward_label: str


@dataclass(frozen=True)
class ArchiveComparisonSummary:
    """Cross-run comparison view used for archive review commands."""

    compared_runs: int
    latest_label: str
    best_score_label: str
    best_offer_label: str
    strongest_cash_label: str
    strongest_reputation_label: str
    average_score: int
    average_offer_value: Decimal
    average_final_cash: Decimal
    outcome_mix: tuple[str, ...]
    grade_mix: tuple[str, ...]
    recommendation: str


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
    campaign_ladder: tuple[str, ...]
    unlocked_rewards: tuple[str, ...]
    unlocks_remaining: tuple[str, ...]
    archive_highlights: tuple[str, ...]
    next_goal: str
    next_reward: str


def get_achievement_definitions() -> tuple[AchievementDefinition, ...]:
    """Return the ordered archive-progression achievement definitions."""

    return (
        AchievementDefinition(
            achievement_id="first_archive",
            title="Archive Analyst",
            description="Finish and archive the first completed run.",
            reward_label="Unlock: archive comparison review",
        ),
        AchievementDefinition(
            achievement_id="first_victory",
            title="First Victory",
            description="Reach any victory outcome.",
            reward_label="Unlock: campaign_ladder_climb scenario",
        ),
        AchievementDefinition(
            achievement_id="repeat_operator",
            title="Repeat Operator",
            description="Archive at least three completed runs.",
            reward_label="Unlock: archive_governance_studio template",
        ),
        AchievementDefinition(
            achievement_id="board_steward",
            title="Board Steward",
            description="Earn the board_trusted badge in any archived run.",
            reward_label="Unlock: board_recovery_crucible scenario",
        ),
        AchievementDefinition(
            achievement_id="channel_builder",
            title="Channel Builder",
            description="Earn the channel_builder badge in any archived run.",
            reward_label="Unlock: partner_recovery_cloud template",
        ),
        AchievementDefinition(
            achievement_id="monetization_architect",
            title="Monetization Architect",
            description="Earn the monetization_architect badge in any archived run.",
            reward_label="Unlock: archive_scale_operator rival archetype",
        ),
        AchievementDefinition(
            achievement_id="support_resilient",
            title="Support Resilient",
            description="Earn the support_resilient badge in any archived run.",
            reward_label="Unlock: channel_rebuild_marathon scenario",
        ),
        AchievementDefinition(
            achievement_id="people_stable",
            title="People Stable",
            description="Earn the people_stable badge in any archived run.",
            reward_label="Unlock: partner_fatigue_broker rival archetype",
        ),
        AchievementDefinition(
            achievement_id="ipo_pathfinder",
            title="IPO Pathfinder",
            description="Reach at least one IPO-ready archive outcome.",
            reward_label="Unlock: board_command_cloud endgame track",
        ),
        AchievementDefinition(
            achievement_id="strategic_closer",
            title="Strategic Closer",
            description="Reach at least one strategic acquisition archive outcome.",
            reward_label="Unlock: acquisition-comparison insight",
        ),
        AchievementDefinition(
            achievement_id="independent_operator",
            title="Independent Operator",
            description="Reach at least one profitable independence archive outcome.",
            reward_label="Unlock: independence-comparison insight",
        ),
    )


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
            unlocked_achievements=tuple(),
            campaign_tier="unranked",
            campaign_stage="foundation",
            achievement_progress="0/11 core achievements",
            campaign_ladder=(
                "1. foundation [pending]",
                "2. portfolio [pending]",
                "3. operator [pending]",
                "4. institutional [pending]",
                "5. franchise [pending]",
            ),
            unlocked_rewards=tuple(),
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
            next_reward="Unlock: archive comparison review",
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
    achievement_definitions = get_achievement_definitions()
    unlocks = [name for name, unlocked in achievement_checks if unlocked]
    unlock_status = {name: unlocked for name, unlocked in achievement_checks}
    unlocks_remaining = tuple(name for name, unlocked in achievement_checks if not unlocked)
    unlocked_rewards = tuple(
        definition.reward_label
        for definition in achievement_definitions
        if unlock_status.get(definition.achievement_id, False)
    )

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
    campaign_ladder = (
        _format_ladder_step("foundation", len(unlocks) >= 1, 1),
        _format_ladder_step(
            "portfolio",
            campaign_stage in {"portfolio", "operator", "institutional", "franchise"},
            2,
        ),
        _format_ladder_step(
            "operator",
            campaign_stage in {"operator", "institutional", "franchise"},
            3,
        ),
        _format_ladder_step(
            "institutional",
            campaign_stage in {"institutional", "franchise"},
            4,
        ),
        _format_ladder_step("franchise", campaign_stage == "franchise", 5),
    )

    if victories == 0:
        next_goal = "Push one run to a victory state to unlock the next campaign tier."
    elif unlocks_remaining:
        next_goal = f"Next unlock target: {unlocks_remaining[0]}."
    elif "ipo_ready" not in unique_outcomes:
        next_goal = "Reach an IPO-ready ending to complete the public-market ladder."
    else:
        next_goal = "The archive already covers the core campaign ladder."
    next_reward = next(
        (
            definition.reward_label
            for definition in achievement_definitions
            if not unlock_status.get(definition.achievement_id, False)
        ),
        "All archive-driven rewards are unlocked.",
    )

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
        campaign_ladder=campaign_ladder,
        unlocked_rewards=unlocked_rewards,
        unlocks_remaining=unlocks_remaining,
        archive_highlights=archive_highlights,
        next_goal=next_goal,
        next_reward=next_reward,
    )


def build_archive_comparison(archives: list[RunArchiveSummary]) -> ArchiveComparisonSummary:
    """Compare archived runs through score, cash, offer, and coverage lenses."""

    if not archives:
        return ArchiveComparisonSummary(
            compared_runs=0,
            latest_label="-",
            best_score_label="-",
            best_offer_label="-",
            strongest_cash_label="-",
            strongest_reputation_label="-",
            average_score=0,
            average_offer_value=Decimal("0.00"),
            average_final_cash=Decimal("0.00"),
            outcome_mix=tuple(),
            grade_mix=tuple(),
            recommendation="Archive at least one completed run before comparing outcomes.",
        )

    latest_archive = max(archives, key=lambda archive: archive.archived_at)
    best_score_archive = max(archives, key=lambda archive: archive.total_score)
    best_offer_archive = max(archives, key=lambda archive: archive.offer_value)
    strongest_cash_archive = max(archives, key=lambda archive: archive.final_cash)
    strongest_reputation_archive = max(archives, key=lambda archive: archive.final_reputation)
    average_score = sum(archive.total_score for archive in archives) // len(archives)
    average_offer_value = quantize_money(
        sum((archive.offer_value for archive in archives), Decimal("0.00")) / Decimal(len(archives))
    )
    average_final_cash = quantize_money(
        sum((archive.final_cash for archive in archives), Decimal("0.00")) / Decimal(len(archives))
    )
    outcome_mix = tuple(
        sorted({archive.exit_outcome for archive in archives if archive.exit_outcome})
    )
    grade_mix = tuple(
        sorted({archive.campaign_grade for archive in archives if archive.campaign_grade})
    )

    if len(outcome_mix) == 1:
        recommendation = (
            "Archive a different ending path next. The current history is consistent, "
            "but outcome diversity is still narrow."
        )
    elif best_offer_archive.offer_value > strongest_cash_archive.final_cash * Decimal("4.00"):
        recommendation = (
            "M&A-style runs are paying up more than independent cash discipline. "
            "Decide whether to optimize for exits or durability."
        )
    else:
        recommendation = (
            "The archive already shows multiple viable paths. Compare score, cash, "
            "and offer quality before deciding the next campaign target."
        )

    return ArchiveComparisonSummary(
        compared_runs=len(archives),
        latest_label=(
            f"{latest_archive.exit_outcome} / turn {latest_archive.completed_turn} / "
            f"{latest_archive.campaign_grade}"
        ),
        best_score_label=(
            f"{best_score_archive.company_name} / {best_score_archive.total_score} / "
            f"{best_score_archive.exit_outcome}"
        ),
        best_offer_label=(
            f"{best_offer_archive.company_name} / {format_money(best_offer_archive.offer_value)}"
        ),
        strongest_cash_label=(
            f"{strongest_cash_archive.company_name} / "
            f"{format_money(strongest_cash_archive.final_cash)}"
        ),
        strongest_reputation_label=(
            f"{strongest_reputation_archive.company_name} / "
            f"{strongest_reputation_archive.final_reputation}"
        ),
        average_score=average_score,
        average_offer_value=average_offer_value,
        average_final_cash=average_final_cash,
        outcome_mix=outcome_mix,
        grade_mix=grade_mix,
        recommendation=recommendation,
    )


def _format_ladder_step(label: str, complete: bool, step: int) -> str:
    status = "done" if complete else "pending"
    return f"{step}. {label} [{status}]"
