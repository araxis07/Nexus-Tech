"""Deterministic decision-variety audit over existing autoplay ledgers."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from math import ceil

from nexus_tech.content.loader import get_scenario
from nexus_tech.domain.models import CampaignGoalId, DifficultyMode
from nexus_tech.simulation.balance_lab import run_autoplay
from nexus_tech.simulation.campaign_journey import list_featured_campaign_journeys
from nexus_tech.simulation.decision_patterns import build_decision_pattern
from nexus_tech.simulation.engine import create_new_game
from nexus_tech.simulation.randomness import RandomSource

MIN_AVERAGE_UNIQUE_COMMANDS = 7.0
MIN_AVERAGE_FAMILIES = 4.0


@dataclass(frozen=True)
class DecisionQualityRun:
    """One deterministic run summarized without retaining gameplay state."""

    seed: int
    turns_played: int
    game_over: bool
    operating_decisions: int
    unique_commands: int
    family_count: int
    repeated_label: str
    repeated_count: int
    repeat_share: float
    repetition_watch: bool


@dataclass(frozen=True)
class DecisionQualityCell:
    """Decision-variety evidence for one scenario and difficulty."""

    scenario_id: str
    difficulty_mode: DifficultyMode
    campaign_goal_id: CampaignGoalId
    runs: tuple[DecisionQualityRun, ...]

    @property
    def run_count(self) -> int:
        return len(self.runs)

    @property
    def average_operating_decisions(self) -> float:
        return _average(run.operating_decisions for run in self.runs)

    @property
    def average_unique_commands(self) -> float:
        return _average(run.unique_commands for run in self.runs)

    @property
    def average_family_count(self) -> float:
        return _average(run.family_count for run in self.runs)

    @property
    def average_repeat_share(self) -> float:
        return _average(run.repeat_share for run in self.runs)

    @property
    def repetition_watch_runs(self) -> int:
        return sum(run.repetition_watch for run in self.runs)

    @property
    def shutdowns(self) -> int:
        return sum(run.game_over for run in self.runs)

    @property
    def leading_repeat_label(self) -> str:
        counts = _repeat_label_counts(self.runs)
        if not counts:
            return "No repeated choice"
        return min(counts.items(), key=lambda item: (-item[1], item[0].casefold()))[0]


@dataclass(frozen=True)
class DecisionQualityEvaluation:
    """Pass, watch, or fail result for one deterministic audit cell."""

    status: str
    summary: str


@dataclass(frozen=True)
class DecisionQualityMatrix:
    """Cross-campaign decision-variety evidence with a human-review boundary."""

    runs_per_cell: int
    turns: int
    seed_base: int
    cells: tuple[DecisionQualityCell, ...]
    human_confirmation_required: bool = True

    @property
    def scenario_count(self) -> int:
        return len({cell.scenario_id for cell in self.cells})

    @property
    def run_count(self) -> int:
        return sum(cell.run_count for cell in self.cells)

    @property
    def automated_gate_passed(self) -> bool:
        return bool(self.cells) and all(
            evaluate_decision_quality_cell(cell).status != "fail" for cell in self.cells
        )

    @property
    def watch_count(self) -> int:
        return sum(evaluate_decision_quality_cell(cell).status == "watch" for cell in self.cells)


def run_decision_quality_audit(
    *,
    scenario_ids: list[str] | None = None,
    runs_per_cell: int = 3,
    turns: int = 12,
    seed_base: int = 28600,
) -> DecisionQualityMatrix:
    """Audit deterministic autoplay variety across scenarios and difficulties."""

    if runs_per_cell < 1:
        raise ValueError("runs_per_cell must be at least 1.")
    if turns < 1:
        raise ValueError("turns must be at least 1.")

    selected_scenarios = scenario_ids or [
        journey.scenario_id for journey in list_featured_campaign_journeys()
    ]
    cells: list[DecisionQualityCell] = []
    for scenario_index, scenario_id in enumerate(selected_scenarios):
        campaign_goal_id = get_scenario(scenario_id).campaign_goal_id
        scenario_seed_base = seed_base + (scenario_index * runs_per_cell * 100)
        for difficulty_mode in DifficultyMode:
            run_results: list[DecisionQualityRun] = []
            for run_index in range(runs_per_cell):
                seed = scenario_seed_base + run_index
                state = create_new_game(
                    scenario_id=scenario_id,
                    difficulty_mode=difficulty_mode,
                    campaign_goal_id=campaign_goal_id,
                )
                state = run_autoplay(
                    state,
                    RandomSource(seed=seed),
                    max_turns=turns,
                )
                pattern = build_decision_pattern(state.decision_history)
                run_results.append(
                    DecisionQualityRun(
                        seed=seed,
                        turns_played=state.company.current_turn,
                        game_over=state.company.game_over,
                        operating_decisions=pattern.operating_decisions,
                        unique_commands=pattern.unique_commands,
                        family_count=pattern.family_count,
                        repeated_label=pattern.most_repeated_label,
                        repeated_count=pattern.most_repeated_count,
                        repeat_share=(
                            pattern.most_repeated_count / pattern.operating_decisions
                            if pattern.operating_decisions
                            else 0.0
                        ),
                        repetition_watch=pattern.repetition_watch,
                    )
                )
            cells.append(
                DecisionQualityCell(
                    scenario_id=scenario_id,
                    difficulty_mode=difficulty_mode,
                    campaign_goal_id=campaign_goal_id,
                    runs=tuple(run_results),
                )
            )
    return DecisionQualityMatrix(
        runs_per_cell=runs_per_cell,
        turns=turns,
        seed_base=seed_base,
        cells=tuple(cells),
    )


def evaluate_decision_quality_cell(
    cell: DecisionQualityCell,
) -> DecisionQualityEvaluation:
    """Flag heuristic repetition candidates without authorizing gameplay tuning."""

    if not cell.runs:
        return DecisionQualityEvaluation("fail", "No deterministic runs were recorded.")
    empty_ledgers = sum(run.operating_decisions == 0 for run in cell.runs)
    if empty_ledgers:
        return DecisionQualityEvaluation(
            "fail",
            f"{empty_ledgers}/{cell.run_count} run(s) recorded no operating decisions.",
        )

    watch_threshold = ceil(cell.run_count / 2)
    if cell.repetition_watch_runs >= watch_threshold:
        return DecisionQualityEvaluation(
            "watch",
            (
                f"{cell.repetition_watch_runs}/{cell.run_count} heuristic runs repeated "
                f"{cell.leading_repeat_label}; confirm distinct player intent before tuning."
            ),
        )
    if (
        cell.average_unique_commands < MIN_AVERAGE_UNIQUE_COMMANDS
        or cell.average_family_count < MIN_AVERAGE_FAMILIES
    ):
        return DecisionQualityEvaluation(
            "watch",
            (
                f"Average variety is {cell.average_unique_commands:.1f} commands across "
                f"{cell.average_family_count:.1f} families; compare with real player notes."
            ),
        )
    return DecisionQualityEvaluation(
        "pass",
        "Heuristic runs retained broad command and operating-family variety.",
    )


def format_decision_quality_markdown(matrix: DecisionQualityMatrix) -> str:
    """Serialize deterministic variety candidates without claiming player evidence."""

    evaluations = tuple(evaluate_decision_quality_cell(cell) for cell in matrix.cells)
    lines = [
        "# NEXUS TECH Decision Quality Audit",
        "",
        f"- Scenarios: `{matrix.scenario_count}`",
        f"- Scenario/difficulty cells: `{len(matrix.cells)}`",
        f"- Runs per cell: `{matrix.runs_per_cell}`",
        f"- Heuristic runs: `{matrix.run_count}`",
        f"- Max turns: `{matrix.turns}`",
        f"- Seed base: `{matrix.seed_base}`",
        f"- Advisory watch cells: `{matrix.watch_count}`",
        f"- Automated ledger gate: `{'pass' if matrix.automated_gate_passed else 'fail'}`",
        "- Human tuning confirmation: `required`",
        "",
        "## Cell Summary",
        "",
        (
            "| Scenario | Goal | Difficulty | Status | Runs | Avg Decisions | Avg Unique | "
            "Avg Families | Repeat Watches | Avg Repeat Share | Leading Repeat | Summary |"
        ),
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for cell, evaluation in zip(matrix.cells, evaluations, strict=True):
        lines.append(
            "| "
            f"{cell.scenario_id} | "
            f"{cell.campaign_goal_id.value} | "
            f"{cell.difficulty_mode.value} | "
            f"{evaluation.status} | "
            f"{cell.run_count} | "
            f"{cell.average_operating_decisions:.1f} | "
            f"{cell.average_unique_commands:.1f} | "
            f"{cell.average_family_count:.1f} | "
            f"{cell.repetition_watch_runs} | "
            f"{cell.average_repeat_share:.0%} | "
            f"{cell.leading_repeat_label} | "
            f"{evaluation.summary} |"
        )

    candidates = Counter(
        cell.leading_repeat_label
        for cell, evaluation in zip(matrix.cells, evaluations, strict=True)
        if evaluation.status == "watch" and cell.leading_repeat_label != "No repeated choice"
    )
    lines.extend(["", "## Candidate Review", ""])
    if not candidates:
        lines.append("- No cross-cell repetition candidate was detected by this heuristic pass.")
    else:
        for label, count in sorted(
            candidates.items(), key=lambda item: (-item[1], item[0].casefold())
        ):
            lines.append(f"- `{label}` led repetition in `{count}` advisory watch cell(s).")

    lines.extend(
        [
            "",
            "## Evidence Boundary",
            "",
            "- This audit measures the deterministic autoplay policy, not player behavior.",
            (
                "- A watch result identifies a candidate for observed playtest review; "
                "it is not a failure."
            ),
            "- Do not remove, consolidate, or retune a command without matching real-player notes.",
            (
                "- Forced campaign decisions and systemic event choices remain excluded "
                "by Decision Pattern."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def _repeat_label_counts(runs: tuple[DecisionQualityRun, ...]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for run in runs:
        if run.repeated_count > 1:
            counts[run.repeated_label] += run.repeated_count
    return counts


def _average(values: Iterable[int | float]) -> float:
    items = tuple(values)
    return sum(items) / len(items) if items else 0.0
