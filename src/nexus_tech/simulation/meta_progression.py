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
    reward_type: str
    reward_id: str
    reward_name: str

    @property
    def reward_label(self) -> str:
        return f"Unlock {self.reward_type}: {self.reward_name} [{self.reward_id}]"


@dataclass(frozen=True)
class UnlockCatalogEntry:
    """One archive-driven unlock entry with explicit reward metadata."""

    achievement_id: str
    title: str
    description: str
    reward_type: str
    reward_id: str
    reward_name: str
    reward_label: str
    unlocked: bool


@dataclass(frozen=True)
class UnlockCatalogSummary:
    """Full reward catalog derived from archived runs."""

    total_rewards: int
    unlocked_rewards: int
    reward_mix: tuple[str, ...]
    entries: tuple[UnlockCatalogEntry, ...]
    next_unlock_label: str


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
    missing_outcomes: tuple[str, ...]
    grade_mix: tuple[str, ...]
    dominant_path: str
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
            reward_type="tool",
            reward_id="compare_archives",
            reward_name="Archive Comparison Review",
        ),
        AchievementDefinition(
            achievement_id="first_victory",
            title="First Victory",
            description="Reach any victory outcome.",
            reward_type="scenario",
            reward_id="campaign_ladder_climb",
            reward_name="Campaign Ladder Climb",
        ),
        AchievementDefinition(
            achievement_id="repeat_operator",
            title="Repeat Operator",
            description="Archive at least three completed runs.",
            reward_type="template",
            reward_id="archive_governance_studio",
            reward_name="Archive Governance Studio",
        ),
        AchievementDefinition(
            achievement_id="board_steward",
            title="Board Steward",
            description="Earn the board_trusted badge in any archived run.",
            reward_type="scenario",
            reward_id="board_recovery_crucible",
            reward_name="Board Recovery Crucible",
        ),
        AchievementDefinition(
            achievement_id="channel_builder",
            title="Channel Builder",
            description="Earn the channel_builder badge in any archived run.",
            reward_type="template",
            reward_id="partner_recovery_cloud",
            reward_name="Partner Recovery Cloud",
        ),
        AchievementDefinition(
            achievement_id="monetization_architect",
            title="Monetization Architect",
            description="Earn the monetization_architect badge in any archived run.",
            reward_type="rival",
            reward_id="archive_scale_operator",
            reward_name="Archive Scale Operator",
        ),
        AchievementDefinition(
            achievement_id="support_resilient",
            title="Support Resilient",
            description="Earn the support_resilient badge in any archived run.",
            reward_type="scenario",
            reward_id="channel_rebuild_marathon",
            reward_name="Channel Rebuild Marathon",
        ),
        AchievementDefinition(
            achievement_id="people_stable",
            title="People Stable",
            description="Earn the people_stable badge in any archived run.",
            reward_type="rival",
            reward_id="partner_fatigue_broker",
            reward_name="Partner Fatigue Broker",
        ),
        AchievementDefinition(
            achievement_id="ipo_pathfinder",
            title="IPO Pathfinder",
            description="Reach at least one IPO-ready archive outcome.",
            reward_type="template",
            reward_id="board_command_cloud",
            reward_name="Board Command Cloud",
        ),
        AchievementDefinition(
            achievement_id="strategic_closer",
            title="Strategic Closer",
            description="Reach at least one strategic acquisition archive outcome.",
            reward_type="insight",
            reward_id="acquisition_compare",
            reward_name="Acquisition Comparison Lens",
        ),
        AchievementDefinition(
            achievement_id="independent_operator",
            title="Independent Operator",
            description="Reach at least one profitable independence archive outcome.",
            reward_type="insight",
            reward_id="independence_compare",
            reward_name="Independence Comparison Lens",
        ),
    )


def build_unlock_catalog(archives: list[RunArchiveSummary]) -> UnlockCatalogSummary:
    """Resolve the explicit unlock catalog from archived runs."""

    definitions = get_achievement_definitions()
    unlock_status = _compute_unlock_status(archives)
    entries = tuple(
        UnlockCatalogEntry(
            achievement_id=definition.achievement_id,
            title=definition.title,
            description=definition.description,
            reward_type=definition.reward_type,
            reward_id=definition.reward_id,
            reward_name=definition.reward_name,
            reward_label=definition.reward_label,
            unlocked=unlock_status.get(definition.achievement_id, False),
        )
        for definition in definitions
    )
    reward_type_counts: dict[str, int] = {}
    for entry in entries:
        reward_type_counts[entry.reward_type] = reward_type_counts.get(entry.reward_type, 0) + 1
    reward_mix = tuple(
        f"{reward_type}:{count}"
        for reward_type, count in sorted(reward_type_counts.items(), key=lambda item: item[0])
    )
    next_unlock_label = next(
        (entry.reward_label for entry in entries if not entry.unlocked),
        "All archive rewards are already unlocked.",
    )
    return UnlockCatalogSummary(
        total_rewards=len(entries),
        unlocked_rewards=sum(1 for entry in entries if entry.unlocked),
        reward_mix=reward_mix,
        entries=entries,
        next_unlock_label=next_unlock_label,
    )


def summarize_meta_progression(
    archives: list[RunArchiveSummary],
) -> MetaProgressionSummary:
    """Collapse archived completed runs into one progression summary."""

    if not archives:
        unlock_catalog = build_unlock_catalog(archives)
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
            achievement_progress=f"0/{len(get_achievement_definitions())} core achievements",
            campaign_ladder=(
                "1. foundation [pending]",
                "2. portfolio [pending]",
                "3. operator [pending]",
                "4. institutional [pending]",
                "5. franchise [pending]",
            ),
            unlocked_rewards=tuple(
                entry.reward_label for entry in unlock_catalog.entries if entry.unlocked
            ),
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
            next_reward=unlock_catalog.next_unlock_label,
        )

    victories = sum(1 for archive in archives if archive.victory_achieved)
    best_archive = max(archives, key=lambda archive: archive.total_score)
    latest_archive = max(archives, key=lambda archive: archive.archived_at)
    unique_outcomes = tuple(
        sorted({archive.exit_outcome for archive in archives if archive.exit_outcome})
    )
    best_offer = max(archives, key=lambda archive: archive.offer_value)
    average_offer_value = quantize_money(
        sum((archive.offer_value for archive in archives), Decimal("0.00")) / Decimal(len(archives))
    )

    achievement_definitions = get_achievement_definitions()
    unlock_status = _compute_unlock_status(archives)
    unlocks = [
        definition.achievement_id
        for definition in achievement_definitions
        if unlock_status.get(definition.achievement_id, False)
    ]
    unlocks_remaining = tuple(
        definition.achievement_id
        for definition in achievement_definitions
        if not unlock_status.get(definition.achievement_id, False)
    )
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
    achievement_progress = f"{len(unlocks)}/{len(achievement_definitions)} core achievements"
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
            missing_outcomes=("ipo_ready", "strategic_acquisition", "profitable_independence"),
            grade_mix=tuple(),
            dominant_path="-",
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
    missing_outcomes = tuple(
        outcome
        for outcome in ("ipo_ready", "strategic_acquisition", "profitable_independence")
        if outcome not in outcome_mix
    )
    grade_mix = tuple(
        sorted({archive.campaign_grade for archive in archives if archive.campaign_grade})
    )
    dominant_path = max(
        (
            ("ipo_ready", sum(1 for archive in archives if archive.exit_outcome == "ipo_ready")),
            (
                "strategic_acquisition",
                sum(1 for archive in archives if archive.exit_outcome == "strategic_acquisition"),
            ),
            (
                "profitable_independence",
                sum(1 for archive in archives if archive.exit_outcome == "profitable_independence"),
            ),
            (
                "restructure",
                sum(1 for archive in archives if archive.exit_outcome == "restructure"),
            ),
        ),
        key=lambda item: item[1],
    )[0]

    if missing_outcomes:
        recommendation = (
            "Coverage is still narrow. Next archive target: "
            f"{missing_outcomes[0].replace('_', ' ')}."
        )
    elif len(outcome_mix) == 1:
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
        missing_outcomes=missing_outcomes,
        grade_mix=grade_mix,
        dominant_path=dominant_path,
        recommendation=recommendation,
    )


def _compute_unlock_status(archives: list[RunArchiveSummary]) -> dict[str, bool]:
    definitions = get_achievement_definitions()
    if not archives:
        return {definition.achievement_id: False for definition in definitions}

    victories = sum(1 for archive in archives if archive.victory_achieved)
    unique_outcomes = {
        archive.exit_outcome
        for archive in archives
        if archive.exit_outcome and archive.exit_outcome
    }
    badge_pool = {badge for archive in archives for badge in archive.achievement_badges}
    return {
        "first_archive": True,
        "first_victory": victories >= 1,
        "repeat_operator": len(archives) >= 3,
        "board_steward": "board_trusted" in badge_pool,
        "channel_builder": "channel_builder" in badge_pool,
        "monetization_architect": "monetization_architect" in badge_pool,
        "support_resilient": "support_resilient" in badge_pool,
        "people_stable": "people_stable" in badge_pool,
        "ipo_pathfinder": "ipo_ready" in unique_outcomes,
        "strategic_closer": "strategic_acquisition" in unique_outcomes,
        "independent_operator": "profitable_independence" in unique_outcomes,
    }


def _format_ladder_step(label: str, complete: bool, step: int) -> str:
    status = "done" if complete else "pending"
    return f"{step}. {label} [{status}]"
