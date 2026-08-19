from __future__ import annotations

from nexus_tech.domain.models import CampaignGoalId, DifficultyMode
from nexus_tech.simulation.balance_lab import AutoplayDecisionReason
from nexus_tech.simulation.decision_quality import (
    DecisionQualityCell,
    DecisionQualityMatrix,
    DecisionQualityRun,
    evaluate_decision_quality_cell,
    format_decision_quality_markdown,
    run_decision_quality_audit,
)


def _run(
    seed: int,
    *,
    operating_decisions: int = 20,
    unique_commands: int = 9,
    family_count: int = 5,
    repeated_label: str = "Grow Demand",
    repeated_count: int = 5,
    repetition_watch: bool = False,
    reason_breakdown: tuple[tuple[str, int], ...] = (),
    fallback_count: int = 0,
) -> DecisionQualityRun:
    return DecisionQualityRun(
        seed=seed,
        turns_played=12,
        game_over=False,
        operating_decisions=operating_decisions,
        unique_commands=unique_commands,
        family_count=family_count,
        repeated_label=repeated_label,
        repeated_count=repeated_count,
        repeat_share=(repeated_count / operating_decisions if operating_decisions else 0.0),
        repetition_watch=repetition_watch,
        repeated_command="market_product",
        reason_breakdown=reason_breakdown,
        fallback_count=fallback_count,
        fallback_share=(fallback_count / repeated_count if repeated_count else 0.0),
    )


def _cell(*runs: DecisionQualityRun) -> DecisionQualityCell:
    return DecisionQualityCell(
        scenario_id="founder_journey",
        difficulty_mode=DifficultyMode.STANDARD,
        campaign_goal_id=CampaignGoalId.PROFIT_MACHINE,
        runs=tuple(runs),
    )


def test_decision_quality_evaluation_separates_coverage_failures_from_watches() -> None:
    missing = _cell(_run(1, operating_decisions=0, repeated_count=0))
    repetitive = _cell(
        _run(1, repeated_count=10, repetition_watch=True),
        _run(2, repeated_count=9, repetition_watch=True),
        _run(3),
    )
    low_variety = _cell(
        _run(1, unique_commands=5, family_count=3),
        _run(2, unique_commands=6, family_count=3),
        _run(3, unique_commands=6, family_count=4),
    )
    varied = _cell(_run(1), _run(2), _run(3))

    assert evaluate_decision_quality_cell(missing).status == "fail"
    assert evaluate_decision_quality_cell(repetitive).status == "watch"
    assert "2/3 heuristic runs" in evaluate_decision_quality_cell(repetitive).summary
    assert "Possible gameplay candidate" in evaluate_decision_quality_cell(repetitive).summary
    assert repetitive.leading_repeat_label == "Grow Demand"
    assert evaluate_decision_quality_cell(low_variety).status == "watch"
    assert "Average variety" in evaluate_decision_quality_cell(low_variety).summary
    assert evaluate_decision_quality_cell(varied).status == "pass"


def test_decision_quality_markdown_preserves_human_tuning_boundary() -> None:
    pass_cell = _cell(_run(1), _run(2), _run(3))
    watch_cell = _cell(
        _run(4, repeated_count=10, repetition_watch=True),
        _run(5, repeated_count=9, repetition_watch=True),
        _run(6),
    )
    matrix = DecisionQualityMatrix(
        runs_per_cell=3,
        turns=12,
        seed_base=28600,
        cells=(pass_cell, watch_cell),
    )

    report = format_decision_quality_markdown(matrix)

    assert matrix.automated_gate_passed
    assert matrix.watch_count == 1
    assert "Automated ledger gate: `pass`" in report
    assert "Human tuning confirmation: `required`" in report
    assert "This audit measures the deterministic autoplay policy" in report
    assert "Do not remove, consolidate, or retune a command" in report


def test_decision_quality_separates_fallback_dominated_policy_watches() -> None:
    reasons = (
        (AutoplayDecisionReason.DEFAULT_GROWTH_FALLBACK.value, 8),
        (AutoplayDecisionReason.GROWTH_STABILIZATION.value, 2),
    )
    policy_watch = _cell(
        _run(
            1,
            repeated_count=10,
            repetition_watch=True,
            reason_breakdown=reasons,
            fallback_count=8,
        ),
        _run(
            2,
            repeated_count=10,
            repetition_watch=True,
            reason_breakdown=reasons,
            fallback_count=8,
        ),
    )
    matrix = DecisionQualityMatrix(
        runs_per_cell=2,
        turns=12,
        seed_base=28600,
        cells=(policy_watch,),
    )

    evaluation = evaluate_decision_quality_cell(policy_watch)
    report = format_decision_quality_markdown(matrix)

    assert evaluation.status == "watch"
    assert evaluation.summary.startswith("Autoplay-policy watch")
    assert policy_watch.average_fallback_share == 0.8
    assert policy_watch.leading_repeat_reason == "default_growth_fallback"
    assert "### Autoplay Policy Watches" in report
    assert "fallback `80%`" in report
    assert "Default Growth Fallback 16" in report
    assert "### Possible Gameplay Candidates" in report


def test_decision_quality_audit_uses_native_goal_and_shared_difficulty_seeds() -> None:
    matrix = run_decision_quality_audit(
        scenario_ids=["founder_journey"],
        runs_per_cell=1,
        turns=3,
        seed_base=28700,
    )

    assert len(matrix.cells) == 3
    assert matrix.run_count == 3
    assert matrix.scenario_count == 1
    assert matrix.automated_gate_passed
    assert all(cell.campaign_goal_id is CampaignGoalId.PROFIT_MACHINE for cell in matrix.cells)
    assert {cell.runs[0].seed for cell in matrix.cells} == {28700}
    assert all(cell.runs[0].operating_decisions > 0 for cell in matrix.cells)
    assert all(cell.runs[0].repeated_command for cell in matrix.cells)
    assert all(cell.runs[0].reason_breakdown for cell in matrix.cells)
    assert all(
        sum(count for _, count in cell.runs[0].reason_breakdown) == cell.runs[0].repeated_count
        for cell in matrix.cells
    )
