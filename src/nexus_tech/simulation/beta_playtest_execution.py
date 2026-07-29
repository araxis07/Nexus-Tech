"""Privacy-safe execution planning for the six-session human beta gate."""

from __future__ import annotations

import shlex
from dataclasses import dataclass

from nexus_tech.artifact_path_safety import (
    normalize_local_path,
    protected_sqlite_artifact_paths,
)
from nexus_tech.persistence.beta_playtest_repository import BetaPlaytestSession
from nexus_tech.simulation.beta_playtest import (
    BetaPlaytestStatus,
    BetaPlaytestTarget,
    beta_playtest_session_needs_retest,
    build_beta_playtest_status,
    select_beta_playtest_target,
)


@dataclass(frozen=True)
class BetaPlaytestExecutionLane:
    """One campaign lane without free-form evidence or personal information."""

    order: int
    track_label: str
    scenario_id: str
    active_sessions: int
    unique_testers: int
    state: str
    follow_up: str


@dataclass(frozen=True)
class BetaPlaytestExecutionPlan:
    """A current evidence snapshot and one safe next operator action."""

    status: BetaPlaytestStatus
    target: BetaPlaytestTarget
    lanes: tuple[BetaPlaytestExecutionLane, ...]
    command_prefix: str
    evidence_database_path: str
    packet_output_path: str
    plan_output_path: str

    @property
    def owner_rehearsal_required(self) -> bool:
        return self.status.session_count == 0 and self.target.kind != "review"

    @property
    def prepare_command(self) -> str:
        if self.target.kind == "review":
            return ""
        return _command(
            self.command_prefix,
            "prepare-beta-playtest-session",
            "--command-prefix",
            self.command_prefix,
            "--db-path",
            self.evidence_database_path,
            "--output",
            self.packet_output_path,
        )

    @property
    def status_command(self) -> str:
        return _command(
            self.command_prefix,
            "beta-playtest-status",
            "--db-path",
            self.evidence_database_path,
        )

    @property
    def review_gate_command(self) -> str:
        return _command(
            self.command_prefix,
            "beta-playtest-status",
            "--db-path",
            self.evidence_database_path,
            "--require-review-ready",
        )

    @property
    def refresh_plan_command(self) -> str:
        return _command(
            self.command_prefix,
            "beta-playtest-plan",
            "--command-prefix",
            self.command_prefix,
            "--db-path",
            self.evidence_database_path,
            "--packet-output",
            self.packet_output_path,
            "--output",
            self.plan_output_path,
        )


def build_beta_playtest_execution_plan(
    sessions: list[BetaPlaytestSession],
    *,
    game_version: str,
    command_prefix: str,
    evidence_database_path: str,
    packet_output_path: str,
    plan_output_path: str,
) -> BetaPlaytestExecutionPlan:
    """Build all campaign lanes while selecting only one session for preparation."""

    _validate_execution_input(
        command_prefix=command_prefix,
        evidence_database_path=evidence_database_path,
        packet_output_path=packet_output_path,
        plan_output_path=plan_output_path,
    )
    status = build_beta_playtest_status(sessions, game_version=game_version)
    target = select_beta_playtest_target(status)
    lanes = tuple(
        _build_execution_lane(
            status,
            target,
            order=index,
            scenario_id=lane.scenario_id,
            track_label=lane.track_label,
            active_sessions=lane.sessions,
            unique_testers=lane.unique_testers,
        )
        for index, lane in enumerate(status.lanes, start=1)
    )
    return BetaPlaytestExecutionPlan(
        status=status,
        target=target,
        lanes=lanes,
        command_prefix=command_prefix.strip(),
        evidence_database_path=evidence_database_path.strip(),
        packet_output_path=packet_output_path.strip(),
        plan_output_path=plan_output_path.strip(),
    )


def _build_execution_lane(
    status: BetaPlaytestStatus,
    target: BetaPlaytestTarget,
    *,
    order: int,
    scenario_id: str,
    track_label: str,
    active_sessions: int,
    unique_testers: int,
) -> BetaPlaytestExecutionLane:
    lane_sessions = tuple(
        session for session in status.sessions if session.scenario_id == scenario_id
    )
    unresolved = tuple(
        session.session_key
        for session in lane_sessions
        if beta_playtest_session_needs_retest(session)
    )
    is_target = target.lane is not None and target.lane.scenario_id == scenario_id
    if is_target and target.kind == "retest" and target.retest_of is not None:
        state = "NEXT RETEST"
        follow_up = (
            f"Fix the observed gate, then supersede {target.retest_of.session_key} "
            "with a new first-time tester."
        )
    elif is_target and target.kind in {"coverage", "additional"}:
        state = "NEXT SESSION"
        follow_up = target.reason
    elif not active_sessions:
        state = "QUEUED"
        follow_up = "Prepare only after the current next-session packet is recorded."
    elif unresolved and not status.review_ready:
        state = "RETEST QUEUED"
        follow_up = f"Keep unresolved active row(s): {', '.join(unresolved)}."
    else:
        state = "COVERED"
        follow_up = "Active evidence covers this campaign lane."
    return BetaPlaytestExecutionLane(
        order=order,
        track_label=track_label,
        scenario_id=scenario_id,
        active_sessions=active_sessions,
        unique_testers=unique_testers,
        state=state,
        follow_up=follow_up,
    )


def _validate_execution_input(
    *,
    command_prefix: str,
    evidence_database_path: str,
    packet_output_path: str,
    plan_output_path: str,
) -> None:
    values = (
        ("Command prefix", command_prefix),
        ("Evidence database path", evidence_database_path),
        ("Packet output path", packet_output_path),
        ("Plan output path", plan_output_path),
    )
    for label, value in values:
        if not value.strip() or "\n" in value or "\r" in value:
            raise ValueError(f"{label} must be a non-empty single line.")
    shell_controls = (";", "|", "&", "`", "$(", ">", "<")
    if any(control in command_prefix for control in shell_controls):
        raise ValueError("Command prefix must not contain shell control operators.")
    try:
        shlex.split(command_prefix)
    except ValueError as error:
        raise ValueError("Command prefix must contain valid shell quoting.") from error
    normalized_packet_output = normalize_local_path(packet_output_path)
    normalized_plan_output = normalize_local_path(plan_output_path)
    if normalized_packet_output == normalized_plan_output:
        raise ValueError("Packet and execution-plan output paths must be distinct.")
    protected_evidence_artifacts = protected_sqlite_artifact_paths(evidence_database_path)
    if {normalized_packet_output, normalized_plan_output} & protected_evidence_artifacts:
        raise ValueError(
            "Packet and execution-plan outputs must not overwrite the evidence database "
            "or its SQLite sidecars."
        )


def _command(prefix: str, *arguments: object) -> str:
    suffix = " ".join(shlex.quote(str(argument)) for argument in arguments)
    return f"{prefix.strip()} {suffix}"
