"""Decision-mix summaries derived from the existing bounded ledger."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from nexus_tech.domain.models import DecisionLedgerEntry

_NON_OPERATING_FAMILIES = frozenset({"Campaign Decision", "Event Choice"})


@dataclass(frozen=True)
class DecisionPatternSummary:
    """Compact run identity and repetition signals without changing gameplay state."""

    total_decisions: int
    operating_decisions: int
    unique_commands: int
    family_count: int
    dominant_family: str
    dominant_family_count: int
    most_repeated_label: str
    most_repeated_count: int
    repetition_watch: bool
    style_label: str
    family_breakdown: tuple[str, ...]

    @property
    def diversity_line(self) -> str:
        if not self.operating_decisions:
            return "No operating decisions recorded yet."
        return (
            f"{self.operating_decisions} operating decisions | "
            f"{self.family_count} families | {self.unique_commands} unique choices"
        )

    @property
    def family_mix_line(self) -> str:
        if not self.family_breakdown:
            return "Mix: waiting for the first state-changing action."
        return f"Mix: {', '.join(self.family_breakdown)}"

    @property
    def repetition_line(self) -> str:
        if not self.operating_decisions:
            return "No repeat signal yet."
        if self.most_repeated_count <= 1:
            return "No operating choice repeated."
        prefix = "Repetition watch" if self.repetition_watch else "Most repeated"
        suffix = "; confirm each use solved a distinct problem." if self.repetition_watch else "."
        return f"{prefix}: {self.most_repeated_label} x{self.most_repeated_count}{suffix}"


def build_decision_pattern(
    entries: Sequence[DecisionLedgerEntry],
) -> DecisionPatternSummary:
    """Summarize voluntary operating choices while excluding forced event responses."""

    operating_entries = tuple(
        entry for entry in entries if entry.family not in _NON_OPERATING_FAMILIES
    )
    family_counts = Counter(entry.family for entry in operating_entries)
    command_counts = Counter(entry.command for entry in operating_entries)
    labels_by_command = {entry.command: entry.label for entry in operating_entries}
    operating_count = len(operating_entries)

    ordered_families = sorted(
        family_counts.items(),
        key=lambda item: (-item[1], item[0].lower()),
    )
    dominant_family, dominant_count = (
        ordered_families[0] if ordered_families else ("No operating pattern", 0)
    )
    runner_up_count = ordered_families[1][1] if len(ordered_families) > 1 else 0
    repeated_command, repeated_count = (
        min(command_counts.items(), key=lambda item: (-item[1], item[0]))
        if command_counts
        else ("", 0)
    )
    repeated_label = labels_by_command.get(repeated_command, "No repeated choice")
    repetition_watch = bool(
        operating_count and repeated_count >= 3 and repeated_count / operating_count >= 0.4
    )

    return DecisionPatternSummary(
        total_decisions=len(entries),
        operating_decisions=operating_count,
        unique_commands=len(command_counts),
        family_count=len(family_counts),
        dominant_family=dominant_family,
        dominant_family_count=dominant_count,
        most_repeated_label=repeated_label,
        most_repeated_count=repeated_count,
        repetition_watch=repetition_watch,
        style_label=_style_label(
            operating_count=operating_count,
            family_count=len(family_counts),
            dominant_family=dominant_family,
            dominant_count=dominant_count,
            runner_up_count=runner_up_count,
        ),
        family_breakdown=tuple(f"{family} {count}" for family, count in ordered_families[:3]),
    )


def _style_label(
    *,
    operating_count: int,
    family_count: int,
    dominant_family: str,
    dominant_count: int,
    runner_up_count: int,
) -> str:
    if not operating_count:
        return "No Operating Pattern"
    if operating_count < 3:
        return f"Emerging {dominant_family}"
    dominant_share = dominant_count / operating_count
    if family_count == 2 and dominant_count == runner_up_count:
        return "Dual-Focus Operator"
    if family_count >= 3 and dominant_share <= 0.45:
        return "Balanced Operator"
    if dominant_share >= 0.6:
        return f"{dominant_family}-Led"
    return f"{dominant_family}-Weighted"
