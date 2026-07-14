"""Deterministic branch coverage for the six featured campaign journeys."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from itertools import product

from nexus_tech.domain.models import CampaignGoalId, DifficultyMode, GameState
from nexus_tech.simulation.balance_lab import run_autoplay
from nexus_tech.simulation.campaign_decisions import (
    get_campaign_path_labels,
    list_campaign_decisions,
)
from nexus_tech.simulation.campaign_journey import list_featured_campaign_journeys
from nexus_tech.simulation.engine import create_new_game
from nexus_tech.simulation.randomness import RandomSource
from nexus_tech.simulation.reporting import calculate_run_score

CAMPAIGN_ROUTE_SCORE_SPREAD_WATCH = 45.0


@dataclass(frozen=True)
class CampaignRouteDefinition:
    """One commitment/consequence combination for a featured campaign."""

    scenario_id: str
    route_id: str
    route_label: str
    choices: tuple[tuple[str, str], ...]
    option_labels: tuple[str, ...]

    @property
    def event_option_overrides(self) -> dict[str, str]:
        """Return event choices in the shape expected by the deterministic autoplayer."""

        return dict(self.choices)


@dataclass(frozen=True)
class CampaignRouteOutcome:
    """Aggregate mechanical outcome for one route on one difficulty."""

    route_id: str
    route_label: str
    runs: int
    full_path_runs: int
    act_three_survivors: int
    shutdowns: int
    victories: int
    average_turns: float
    average_score: float
    average_cash: Decimal

    @property
    def mechanically_ready(self) -> bool:
        """Return whether every run reached both choices and one survived Act 3."""

        return self.full_path_runs == self.runs and self.act_three_survivors > 0


@dataclass(frozen=True)
class CampaignReadinessCell:
    """All four authored routes for one scenario and difficulty."""

    scenario_id: str
    difficulty_mode: DifficultyMode
    routes: tuple[CampaignRouteOutcome, ...]

    @property
    def ready_routes(self) -> int:
        return sum(route.mechanically_ready for route in self.routes)

    @property
    def shutdowns(self) -> int:
        return sum(route.shutdowns for route in self.routes)

    @property
    def total_runs(self) -> int:
        return sum(route.runs for route in self.routes)

    @property
    def runs_per_route(self) -> int:
        return min((route.runs for route in self.routes), default=0)

    @property
    def score_spread(self) -> float:
        if not self.routes:
            return 0.0
        scores = [route.average_score for route in self.routes]
        return max(scores) - min(scores)


@dataclass(frozen=True)
class CampaignReadinessEvaluation:
    """Pass/watch/fail result for one campaign/difficulty branch cell."""

    status: str
    summary: str


@dataclass(frozen=True)
class CampaignReadinessMatrix:
    """Automated branch evidence that does not replace human playtest signoff."""

    campaign_goal_id: CampaignGoalId
    runs_per_route: int
    turns: int
    seed_base: int
    cells: tuple[CampaignReadinessCell, ...]
    manual_signoff_required: bool = True

    @property
    def route_count(self) -> int:
        return sum(len(cell.routes) for cell in self.cells)

    @property
    def automated_gate_passed(self) -> bool:
        return bool(self.cells) and all(
            evaluate_campaign_readiness_cell(cell).status != "fail" for cell in self.cells
        )


def list_campaign_routes(scenario_id: str) -> tuple[CampaignRouteDefinition, ...]:
    """Return every authored two-choice path for one featured campaign."""

    decisions = sorted(
        (decision for decision in list_campaign_decisions() if decision.scenario_id == scenario_id),
        key=lambda decision: decision.trigger_after_turn,
    )
    if len(decisions) != 2:
        return ()

    routes: list[CampaignRouteDefinition] = []
    for selected_options in product(*(decision.options for decision in decisions)):
        option_ids = tuple(option.option_id for option in selected_options)
        option_labels = tuple(option.label for option in selected_options)
        routes.append(
            CampaignRouteDefinition(
                scenario_id=scenario_id,
                route_id="__".join(option_ids),
                route_label=" -> ".join(option_labels),
                choices=tuple(
                    (decision.event_id, option.option_id)
                    for decision, option in zip(decisions, selected_options, strict=True)
                ),
                option_labels=option_labels,
            )
        )
    return tuple(routes)


def run_campaign_readiness_matrix(
    *,
    scenario_ids: list[str] | None = None,
    campaign_goal_id: CampaignGoalId = CampaignGoalId.PROFIT_MACHINE,
    runs_per_route: int = 1,
    turns: int = 12,
    seed_base: int = 28500,
) -> CampaignReadinessMatrix:
    """Exercise all four campaign paths across every supported difficulty."""

    if runs_per_route < 1:
        raise ValueError("runs_per_route must be at least 1.")
    if turns < 9:
        raise ValueError("turns must be at least 9 to reach the Act 3 campaign decision.")

    selected_scenarios = scenario_ids or [
        journey.scenario_id for journey in list_featured_campaign_journeys()
    ]
    cells: list[CampaignReadinessCell] = []
    seed_offset = 0
    for scenario_id in selected_scenarios:
        routes = list_campaign_routes(scenario_id)
        if not routes:
            raise ValueError(f"Scenario {scenario_id!r} is not a featured two-decision campaign.")
        for difficulty_mode in DifficultyMode:
            outcomes: list[CampaignRouteOutcome] = []
            cell_seed_base = seed_base + seed_offset
            for route in routes:
                states = []
                for run_index in range(runs_per_route):
                    state = create_new_game(
                        scenario_id=scenario_id,
                        difficulty_mode=difficulty_mode,
                        campaign_goal_id=campaign_goal_id,
                    )
                    state = run_autoplay(
                        state,
                        RandomSource(seed=cell_seed_base + run_index),
                        max_turns=turns,
                        event_option_overrides=route.event_option_overrides,
                    )
                    states.append(state)
                full_path_runs = sum(
                    _matches_route_path(state, route.option_labels) for state in states
                )
                act_three_survivors = sum(
                    _matches_route_path(state, route.option_labels) and not state.company.game_over
                    for state in states
                )
                scores = [calculate_run_score(state).total_score for state in states]
                outcomes.append(
                    CampaignRouteOutcome(
                        route_id=route.route_id,
                        route_label=route.route_label,
                        runs=runs_per_route,
                        full_path_runs=full_path_runs,
                        act_three_survivors=act_three_survivors,
                        shutdowns=sum(state.company.game_over for state in states),
                        victories=sum(state.victory_achieved for state in states),
                        average_turns=(
                            sum(state.company.current_turn for state in states) / len(states)
                        ),
                        average_score=sum(scores) / len(scores),
                        average_cash=(
                            sum(
                                (state.company.cash_on_hand for state in states),
                                Decimal("0.00"),
                            )
                            / Decimal(len(states))
                        ),
                    )
                )
            seed_offset += max(1, runs_per_route) * 100
            cells.append(
                CampaignReadinessCell(
                    scenario_id=scenario_id,
                    difficulty_mode=difficulty_mode,
                    routes=tuple(outcomes),
                )
            )
    return CampaignReadinessMatrix(
        campaign_goal_id=campaign_goal_id,
        runs_per_route=runs_per_route,
        turns=turns,
        seed_base=seed_base,
        cells=tuple(cells),
    )


def evaluate_campaign_readiness_cell(
    cell: CampaignReadinessCell,
) -> CampaignReadinessEvaluation:
    """Evaluate route reachability before any human comprehension claim is made."""

    if len(cell.routes) != 4:
        return CampaignReadinessEvaluation(
            "fail",
            f"Expected four campaign routes but exercised {len(cell.routes)}.",
        )
    incomplete = [route for route in cell.routes if route.full_path_runs < route.runs]
    if incomplete:
        return CampaignReadinessEvaluation(
            "fail",
            f"{len(incomplete)} route(s) did not record both campaign decisions.",
        )
    blocked = [route for route in cell.routes if route.act_three_survivors == 0]
    if blocked:
        return CampaignReadinessEvaluation(
            "fail",
            f"{len(blocked)} route(s) reached Act 3 with no surviving run.",
        )
    if cell.shutdowns:
        return CampaignReadinessEvaluation(
            "watch",
            f"All routes reached Act 3, but {cell.shutdowns}/{cell.total_runs} run(s) shut down.",
        )
    if cell.runs_per_route >= 3 and cell.score_spread > CAMPAIGN_ROUTE_SCORE_SPREAD_WATCH:
        return CampaignReadinessEvaluation(
            "watch",
            (
                f"All routes are reachable; score spread {cell.score_spread:.1f} exceeds the "
                f"{CAMPAIGN_ROUTE_SCORE_SPREAD_WATCH:.1f} review threshold."
            ),
        )
    return CampaignReadinessEvaluation(
        "pass",
        "All four routes recorded both decisions and survived through Act 3.",
    )


def format_campaign_readiness_markdown(matrix: CampaignReadinessMatrix) -> str:
    """Serialize automated branch evidence for release review."""

    evaluations = [evaluate_campaign_readiness_cell(cell) for cell in matrix.cells]
    lines = [
        "# NEXUS TECH Campaign Readiness",
        "",
        f"- Goal: `{matrix.campaign_goal_id.value}`",
        f"- Runs per route: `{matrix.runs_per_route}`",
        f"- Max turns: `{matrix.turns}`",
        f"- Seed base: `{matrix.seed_base}`",
        f"- Campaign/difficulty cells: `{len(matrix.cells)}`",
        f"- Authored routes exercised: `{matrix.route_count}`",
        f"- Automated gate: `{'pass' if matrix.automated_gate_passed else 'fail'}`",
        "- Human playtest signoff: `required`",
        "",
        "## Cell Summary",
        "",
        "| Scenario | Difficulty | Status | Ready Routes | Shutdowns | Score Spread | Summary |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for cell, evaluation in zip(matrix.cells, evaluations, strict=True):
        lines.append(
            "| "
            f"{cell.scenario_id} | {cell.difficulty_mode.value} | {evaluation.status} | "
            f"{cell.ready_routes}/{len(cell.routes)} | {cell.shutdowns}/{cell.total_runs} | "
            f"{cell.score_spread:.1f} | {evaluation.summary} |"
        )

    lines.extend(
        [
            "",
            "## Route Detail",
            "",
            (
                "| Scenario | Difficulty | Route | Full Paths | Act 3 Survivors | "
                "Shutdowns | Avg Score | Avg Cash |"
            ),
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for cell in matrix.cells:
        for route in cell.routes:
            lines.append(
                "| "
                f"{cell.scenario_id} | {cell.difficulty_mode.value} | {route.route_label} | "
                f"{route.full_path_runs}/{route.runs} | {route.act_three_survivors}/{route.runs} | "
                f"{route.shutdowns} | {route.average_score:.1f} | {route.average_cash} |"
            )

    lines.extend(
        [
            "",
            "## Evidence Boundary",
            "",
            (
                "This matrix proves deterministic route reachability and highlights mechanical "
                "outliers. It does not prove that players understand the choices, enjoy the "
                "pacing, or can navigate the interface without help."
            ),
            (
                "Use at least three runs per route before treating score spread as a tuning "
                "signal; one-run release checks are reachability gates only."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def _matches_route_path(state: GameState, option_labels: tuple[str, ...]) -> bool:
    path_labels = get_campaign_path_labels(state)
    return len(path_labels) == len(option_labels) and all(
        path_label.endswith(option_label)
        for path_label, option_label in zip(path_labels, option_labels, strict=True)
    )
