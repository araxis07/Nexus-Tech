"""Archive-derived discovery and outcome evidence for authored campaign routes."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from nexus_tech.persistence.save_coordinator import RunArchiveSummary
from nexus_tech.simulation.campaign_decisions import list_campaign_decisions
from nexus_tech.simulation.campaign_journey import list_featured_campaign_journeys


@dataclass(frozen=True)
class CampaignRoutePerformance:
    """Observed archive outcomes for one authored two-decision route."""

    route_label: str
    runs: int
    victories: int
    shutdowns: int
    average_score: int
    average_turn: int

    @property
    def discovered(self) -> bool:
        return self.runs > 0


@dataclass(frozen=True)
class CampaignRouteMasteryLane:
    """Route discovery state for one featured campaign."""

    scenario_id: str
    track_label: str
    discovered_routes: int
    required_routes: int
    full_path_runs: int
    victories: int
    shutdowns: int
    unmapped_runs: int
    routes: tuple[CampaignRoutePerformance, ...]
    next_route_label: str

    @property
    def mastered(self) -> bool:
        return self.discovered_routes == self.required_routes

    @property
    def status(self) -> str:
        if self.mastered:
            return "mastered"
        if self.discovered_routes:
            return "exploring"
        return "unstarted"


@dataclass(frozen=True)
class CampaignRouteMasterySummary:
    """Cross-campaign route discovery that never substitutes for human evidence."""

    discovered_routes: int
    required_routes: int
    mastered_campaigns: int
    required_campaigns: int
    full_path_runs: int
    victories: int
    shutdowns: int
    lanes: tuple[CampaignRouteMasteryLane, ...]
    next_route: str

    @property
    def complete(self) -> bool:
        return self.discovered_routes == self.required_routes

    @property
    def discovery_progress(self) -> str:
        return f"{self.discovered_routes}/{self.required_routes} authored routes"

    @property
    def mastery_progress(self) -> str:
        return f"{self.mastered_campaigns}/{self.required_campaigns} campaigns mastered"


def build_campaign_route_mastery(
    archives: list[RunArchiveSummary],
) -> CampaignRouteMasterySummary:
    """Measure authored route discovery and outcomes from local completed-run archives."""

    lanes: list[CampaignRouteMasteryLane] = []
    for journey in list_featured_campaign_journeys():
        expected_routes = _expected_route_labels(journey.scenario_id)
        matching_archives = [
            archive
            for archive in archives
            if archive.scenario_id == journey.scenario_id and len(archive.campaign_path) == 2
        ]
        archives_by_route = {
            route_label: [
                archive
                for archive in matching_archives
                if _archive_route_label(archive) == route_label
            ]
            for route_label in expected_routes
        }
        route_performance = tuple(
            _build_route_performance(route_label, archives_by_route[route_label])
            for route_label in expected_routes
        )
        discovered_routes = sum(route.discovered for route in route_performance)
        next_route = next(
            (route.route_label for route in route_performance if not route.discovered),
            "All authored routes discovered.",
        )
        mapped_runs = sum(route.runs for route in route_performance)
        lanes.append(
            CampaignRouteMasteryLane(
                scenario_id=journey.scenario_id,
                track_label=journey.track_label,
                discovered_routes=discovered_routes,
                required_routes=len(expected_routes),
                full_path_runs=len(matching_archives),
                victories=sum(archive.victory_achieved for archive in matching_archives),
                shutdowns=sum(archive.game_over for archive in matching_archives),
                unmapped_runs=max(0, len(matching_archives) - mapped_runs),
                routes=route_performance,
                next_route_label=next_route,
            )
        )

    next_lane = next((lane for lane in lanes if not lane.mastered), None)
    next_route = (
        f"{next_lane.track_label} / {next_lane.scenario_id}: {next_lane.next_route_label}"
        if next_lane is not None
        else "All featured campaign routes are archived."
    )
    return CampaignRouteMasterySummary(
        discovered_routes=sum(lane.discovered_routes for lane in lanes),
        required_routes=sum(lane.required_routes for lane in lanes),
        mastered_campaigns=sum(lane.mastered for lane in lanes),
        required_campaigns=len(lanes),
        full_path_runs=sum(lane.full_path_runs for lane in lanes),
        victories=sum(lane.victories for lane in lanes),
        shutdowns=sum(lane.shutdowns for lane in lanes),
        lanes=tuple(lanes),
        next_route=next_route,
    )


def _expected_route_labels(scenario_id: str) -> tuple[str, ...]:
    decisions = sorted(
        (decision for decision in list_campaign_decisions() if decision.scenario_id == scenario_id),
        key=lambda decision: decision.trigger_after_turn,
    )
    if len(decisions) != 2:
        return ()
    return tuple(
        " -> ".join(option.label for option in selected_options)
        for selected_options in product(*(decision.options for decision in decisions))
    )


def _archive_route_label(archive: RunArchiveSummary) -> str:
    return " -> ".join(archive.campaign_path)


def _build_route_performance(
    route_label: str,
    archives: list[RunArchiveSummary],
) -> CampaignRoutePerformance:
    run_count = len(archives)
    return CampaignRoutePerformance(
        route_label=route_label,
        runs=run_count,
        victories=sum(archive.victory_achieved for archive in archives),
        shutdowns=sum(archive.game_over for archive in archives),
        average_score=(
            sum(archive.total_score for archive in archives) // run_count if run_count else 0
        ),
        average_turn=(
            sum(archive.completed_turn for archive in archives) // run_count if run_count else 0
        ),
    )
