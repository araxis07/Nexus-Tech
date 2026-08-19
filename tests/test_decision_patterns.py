from __future__ import annotations

from nexus_tech.domain.models import DecisionLedgerEntry
from nexus_tech.simulation.decision_patterns import build_decision_pattern


def _entry(
    command: str,
    label: str,
    family: str,
    *,
    turn: int = 1,
) -> DecisionLedgerEntry:
    return DecisionLedgerEntry(
        turn=turn,
        command=command,
        label=label,
        family=family,
        summary="Decision applied during the test run.",
        impact_summary="Strategic state updated.",
        timing="Downstream effects resolve at end of turn.",
    )


def test_decision_pattern_handles_an_empty_ledger() -> None:
    pattern = build_decision_pattern(())

    assert pattern.total_decisions == 0
    assert pattern.operating_decisions == 0
    assert pattern.style_label == "No Operating Pattern"
    assert pattern.diversity_line == "No operating decisions recorded yet."
    assert pattern.family_mix_line == "Mix: waiting for the first state-changing action."
    assert pattern.repetition_line == "No repeat signal yet."


def test_decision_pattern_excludes_forced_event_responses_from_operating_mix() -> None:
    entries = (
        _entry("improve_quality", "Improve Quality", "Product"),
        _entry("repay_debt", "Repay Debt", "Finance"),
        _entry("hire_employee", "Hire Teammate", "Team"),
        _entry("triage_support_backlog", "Triage Support", "Operations"),
        _entry("event:campaign_choice", "Defend Control", "Campaign Decision"),
        _entry("event:market_shock", "Protect Cash", "Event Choice"),
    )

    pattern = build_decision_pattern(entries)

    assert pattern.total_decisions == 6
    assert pattern.operating_decisions == 4
    assert pattern.unique_commands == 4
    assert pattern.family_count == 4
    assert pattern.style_label == "Balanced Operator"
    assert pattern.most_repeated_command == "hire_employee"
    assert pattern.most_repeated_count == 1
    assert not pattern.repetition_watch


def test_decision_pattern_names_an_even_two_family_mix_without_alphabetical_bias() -> None:
    entries = (
        _entry("improve_quality", "Improve Quality", "Product", turn=1),
        _entry("add_feature", "Ship Feature", "Product", turn=2),
        _entry("repay_debt", "Repay Debt", "Finance", turn=3),
        _entry("raise_funding", "Raise Funding", "Finance", turn=4),
    )

    pattern = build_decision_pattern(entries)

    assert pattern.style_label == "Dual-Focus Operator"
    assert pattern.family_count == 2
    assert pattern.dominant_family_count == 2


def test_decision_pattern_flags_concentrated_repetition_without_changing_state() -> None:
    entries = (
        _entry("improve_quality", "Improve Quality", "Product", turn=1),
        _entry("improve_quality", "Improve Quality", "Product", turn=2),
        _entry("improve_quality", "Improve Quality", "Product", turn=3),
        _entry("add_feature", "Ship Feature", "Product", turn=4),
        _entry("repay_debt", "Repay Debt", "Finance", turn=5),
    )

    pattern = build_decision_pattern(entries)

    assert pattern.style_label == "Product-Led"
    assert pattern.dominant_family == "Product"
    assert pattern.dominant_family_count == 4
    assert pattern.most_repeated_command == "improve_quality"
    assert pattern.most_repeated_label == "Improve Quality"
    assert pattern.most_repeated_count == 3
    assert pattern.repetition_watch
    assert pattern.repetition_line.startswith("Repetition watch: Improve Quality x3")
