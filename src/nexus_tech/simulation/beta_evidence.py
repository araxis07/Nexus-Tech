"""Local archive evidence for beta playtest preparation and review."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.domain.models import DifficultyMode
from nexus_tech.persistence.save_coordinator import RunArchiveSummary
from nexus_tech.simulation.campaign_journey import list_featured_campaign_journeys
from nexus_tech.simulation.campaign_mastery import (
    CampaignRouteMasterySummary,
    build_campaign_route_mastery,
)


@dataclass(frozen=True)
class CampaignEvidenceLane:
    """Archive coverage for one featured campaign."""

    scenario_id: str
    track_label: str
    run_count: int
    full_path_count: int
    discovered_routes: int
    required_routes: int
    victories: int
    shutdowns: int
    difficulties: tuple[str, ...]
    next_route_label: str

    @property
    def covered(self) -> bool:
        """Return whether at least one full three-act run was archived."""

        return self.full_path_count > 0


@dataclass(frozen=True)
class BetaArchiveEvidence:
    """Measured local run evidence that never substitutes for human signoff."""

    total_archives: int
    featured_archives: int
    full_path_archives: int
    covered_campaigns: int
    required_campaigns: int
    covered_difficulties: tuple[str, ...]
    missing_campaigns: tuple[str, ...]
    lanes: tuple[CampaignEvidenceLane, ...]
    route_mastery: CampaignRouteMasterySummary
    minimum_session_target: int = 6
    manual_signoff_required: bool = True

    @property
    def ready_for_manual_review(self) -> bool:
        """Return whether local archives cover every featured three-act path once."""

        return (
            self.total_archives >= self.minimum_session_target
            and self.covered_campaigns == self.required_campaigns
            and self.full_path_archives >= self.required_campaigns
        )

    @property
    def status(self) -> str:
        """Return a concise non-fabricating readiness label."""

        if self.ready_for_manual_review:
            return "ready-for-manual-review"
        return "archive-evidence-needed"

    @property
    def next_action(self) -> str:
        """Return the next concrete evidence collection action."""

        if self.missing_campaigns:
            return f"Complete and archive {self.missing_campaigns[0]}."
        if self.total_archives < self.minimum_session_target:
            remaining = self.minimum_session_target - self.total_archives
            return f"Complete {remaining} more archived playtest run(s)."
        return "Record real tester observations; archives alone do not complete manual signoff."

    @property
    def next_route_action(self) -> str:
        """Return the next optional replay route without changing the manual beta gate."""

        return self.route_mastery.next_route


def build_beta_archive_evidence(
    archives: list[RunArchiveSummary],
) -> BetaArchiveEvidence:
    """Summarize local archive coverage across featured campaigns and difficulties."""

    journeys = list_featured_campaign_journeys()
    featured_ids = {journey.scenario_id for journey in journeys}
    route_mastery = build_campaign_route_mastery(archives)
    mastery_by_scenario = {lane.scenario_id: lane for lane in route_mastery.lanes}
    lanes: list[CampaignEvidenceLane] = []
    for journey in journeys:
        matching = [archive for archive in archives if archive.scenario_id == journey.scenario_id]
        full_path_count = sum(len(archive.campaign_path) == 2 for archive in matching)
        mastery_lane = mastery_by_scenario[journey.scenario_id]
        lanes.append(
            CampaignEvidenceLane(
                scenario_id=journey.scenario_id,
                track_label=journey.track_label,
                run_count=len(matching),
                full_path_count=full_path_count,
                discovered_routes=mastery_lane.discovered_routes,
                required_routes=mastery_lane.required_routes,
                victories=mastery_lane.victories,
                shutdowns=mastery_lane.shutdowns,
                difficulties=tuple(
                    mode.value
                    for mode in DifficultyMode
                    if any(archive.difficulty_mode == mode.value for archive in matching)
                ),
                next_route_label=mastery_lane.next_route_label,
            )
        )

    featured_archives = [archive for archive in archives if archive.scenario_id in featured_ids]
    covered_difficulties = tuple(
        mode.value
        for mode in DifficultyMode
        if any(archive.difficulty_mode == mode.value for archive in featured_archives)
    )
    missing_campaigns = tuple(lane.scenario_id for lane in lanes if not lane.covered)
    return BetaArchiveEvidence(
        total_archives=len(archives),
        featured_archives=len(featured_archives),
        full_path_archives=sum(len(archive.campaign_path) == 2 for archive in featured_archives),
        covered_campaigns=sum(lane.covered for lane in lanes),
        required_campaigns=len(lanes),
        covered_difficulties=covered_difficulties,
        missing_campaigns=missing_campaigns,
        lanes=tuple(lanes),
        route_mastery=route_mastery,
    )
