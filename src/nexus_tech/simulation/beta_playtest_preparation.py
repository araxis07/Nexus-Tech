"""Safe preparation for the next observed human beta session."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass

from nexus_tech.persistence.beta_playtest_repository import (
    BetaPlaytestInterface,
    BetaPlaytestSession,
    is_substantive_beta_playtest_note,
)
from nexus_tech.simulation.beta_playtest import (
    BetaPlaytestCampaignLane,
    BetaPlaytestStatus,
    build_beta_playtest_status,
)
from nexus_tech.user_preferences import MotionMode

_SESSION_CHECKLIST = (
    "Start timing when the title menu appears; do not point to controls.",
    "Confirm the tester chooses New Game and the target campaign without help.",
    "Record whether Turn 1 is completed without operator guidance.",
    "Ask the tester to use Pause, Back, and return to Menu without hints.",
    "After both campaign choices, ask the tester to explain each trade-off.",
    "Continue until Act 3 or a blocker stops progress; note the exact screen and control.",
    "At the ending, use Save & Archive and confirm the route appears in Progress.",
    "Record one anonymous concrete observation only after the real session ends.",
)


@dataclass(frozen=True)
class BetaPlaytestPreparation:
    """A privacy-safe packet for one next human session or release review."""

    game_version: str
    evidence_status: str
    session_progress: str
    target_scenario_id: str | None
    target_track_label: str
    target_reason: str
    session_key: str
    tester_code: str
    interface_mode: BetaPlaytestInterface
    viewport: str
    motion_mode: MotionMode
    command_prefix: str
    database_path: str
    checklist: tuple[str, ...] = _SESSION_CHECKLIST

    @property
    def requires_session(self) -> bool:
        return self.target_scenario_id is not None

    @property
    def selection_instruction(self) -> str:
        if not self.requires_session:
            return "No additional session is selected; review the current human evidence."
        if self.interface_mode is BetaPlaytestInterface.TWO_D:
            return f"Choose New Game, then {self.target_track_label} / {self.target_scenario_id}."
        return f"Start the {self.target_track_label} / {self.target_scenario_id} campaign."

    @property
    def launch_command(self) -> str:
        if not self.requires_session:
            return ""
        if self.interface_mode is BetaPlaytestInterface.TWO_D:
            return _command(
                self.command_prefix,
                "menu-2d",
                "--db-path",
                self.database_path,
                "--window-size",
                self.viewport,
                "--motion-mode",
                self.motion_mode.value,
            )
        return _command(
            self.command_prefix,
            "new-game",
            "--scenario",
            self.target_scenario_id,
            "--db-path",
            self.database_path,
        )

    @property
    def record_command(self) -> str:
        if not self.requires_session:
            return ""
        return _command(
            self.command_prefix,
            "record-beta-playtest-session",
            "--session-key",
            self.session_key,
            "--tester-code",
            self.tester_code,
            "--scenario",
            self.target_scenario_id,
            "--interface",
            self.interface_mode.value,
            "--viewport",
            self.viewport,
            "--first-turn-seconds",
            "FIRST_TURN_SECONDS",
            "--turn-one",
            "PASS_OR_FAIL",
            "--pause-back",
            "PASS_OR_FAIL",
            "--tradeoff",
            "PASS_OR_FAIL",
            "--act-three",
            "PASS_OR_FAIL",
            "--blocker",
            "NONE_OR_FOUND",
            "--notes",
            "REPLACE with a concrete observation from the real session",
            "--confirm-human-session",
            "--db-path",
            self.database_path,
        )

    @property
    def status_command(self) -> str:
        return _command(
            self.command_prefix,
            "beta-playtest-status",
            "--db-path",
            self.database_path,
        )

    @property
    def archive_command(self) -> str:
        return _command(
            self.command_prefix,
            "beta-evidence",
            "--db-path",
            self.database_path,
        )


def build_beta_playtest_preparation(
    sessions: list[BetaPlaytestSession],
    *,
    game_version: str,
    interface_mode: BetaPlaytestInterface,
    viewport: str,
    motion_mode: MotionMode,
    command_prefix: str,
    database_path: str,
) -> BetaPlaytestPreparation:
    """Select the next honest session target without copying observation notes."""

    if not isinstance(interface_mode, BetaPlaytestInterface):
        raise ValueError("Interface mode must be terminal or 2d.")
    if not isinstance(motion_mode, MotionMode):
        raise ValueError("Motion mode must be full, reduced, or off.")
    _validate_packet_input(
        viewport=viewport,
        command_prefix=command_prefix,
        database_path=database_path,
    )
    status = build_beta_playtest_status(sessions, game_version=game_version)
    target_lane, target_reason = _select_target(status)
    return BetaPlaytestPreparation(
        game_version=game_version,
        evidence_status=status.status,
        session_progress=status.session_progress,
        target_scenario_id=(target_lane.scenario_id if target_lane is not None else None),
        target_track_label=(target_lane.track_label if target_lane is not None else "Review"),
        target_reason=target_reason,
        session_key=_next_identifier(
            {session.session_key for session in sessions},
            prefix="beta-",
            minimum_width=3,
        ),
        tester_code=_next_identifier(
            {session.tester_code for session in sessions},
            prefix="T",
            minimum_width=2,
        ),
        interface_mode=interface_mode,
        viewport=viewport,
        motion_mode=motion_mode,
        command_prefix=command_prefix.strip(),
        database_path=database_path.strip(),
    )


def _select_target(
    status: BetaPlaytestStatus,
) -> tuple[BetaPlaytestCampaignLane | None, str]:
    if status.review_ready:
        return None, "Automated human-evidence criteria are ready for manual release review."

    missing_lane = next((lane for lane in status.lanes if not lane.covered), None)
    if missing_lane is not None:
        return missing_lane, "Cover the next featured campaign missing current-version evidence."

    failed_session = next(
        (session for session in status.sessions if _session_needs_retest(session)),
        None,
    )
    if failed_session is not None:
        lane = next(lane for lane in status.lanes if lane.scenario_id == failed_session.scenario_id)
        return lane, "Re-test the first campaign with an unresolved human gate."

    least_observed = min(status.lanes, key=lambda lane: (lane.sessions, lane.scenario_id))
    return least_observed, "Add an independent tester to close the remaining human gate."


def _session_needs_retest(session: BetaPlaytestSession) -> bool:
    return not all(
        (
            session.turn_one_unaided,
            session.pause_back_success,
            session.tradeoff_explained,
            session.reached_act_three,
            not session.blocker_found,
            is_substantive_beta_playtest_note(session.notes),
        )
    )


def _next_identifier(
    used: set[str],
    *,
    prefix: str,
    minimum_width: int,
) -> str:
    for index in range(1, 1_000_000):
        candidate = f"{prefix}{index:0{minimum_width}d}"
        if candidate not in used:
            return candidate
    raise ValueError(f"Unable to allocate another {prefix} identifier.")


def _validate_packet_input(
    *,
    viewport: str,
    command_prefix: str,
    database_path: str,
) -> None:
    if re.fullmatch(r"[0-9]{2,4}x[0-9]{2,4}", viewport) is None:
        raise ValueError("Viewport must use WIDTHxHEIGHT, for example 820x620 or 120x40.")
    for label, value in (
        ("Command prefix", command_prefix),
        ("Database path", database_path),
    ):
        if not value.strip() or "\n" in value or "\r" in value:
            raise ValueError(f"{label} must be a non-empty single line.")
    shell_controls = (";", "|", "&", "`", "$(", ">", "<")
    if any(control in command_prefix for control in shell_controls):
        raise ValueError("Command prefix must not contain shell control operators.")
    try:
        shlex.split(command_prefix)
    except ValueError as error:
        raise ValueError("Command prefix must contain valid shell quoting.") from error


def _command(prefix: str, *arguments: object) -> str:
    suffix = " ".join(shlex.quote(str(argument)) for argument in arguments)
    return f"{prefix.strip()} {suffix}"
