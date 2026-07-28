"""Safe preparation for the next observed human beta session."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import shlex
from dataclasses import dataclass
from pathlib import Path

from nexus_tech.persistence.beta_playtest_repository import (
    BetaPlaytestInterface,
    BetaPlaytestSession,
)
from nexus_tech.simulation.beta_playtest import (
    build_beta_playtest_status,
    select_beta_playtest_target,
)
from nexus_tech.user_preferences import MotionMode

_PACKET_MANIFEST_PREFIX = "<!-- nexus-tech-beta-packet-v3 "
_PACKET_MANIFEST_SUFFIX = " -->"
_PACKET_MANIFEST_PATTERN = re.compile(
    rf"^{re.escape(_PACKET_MANIFEST_PREFIX)}([A-Za-z0-9_-]+)"
    rf"{re.escape(_PACKET_MANIFEST_SUFFIX)}$",
    re.MULTILINE,
)
_PACKET_MANIFEST_SCHEMA_VERSION = 3

_SESSION_CHECKLIST = (
    "Confirm the isolated tester profile opens with Continue unavailable and no prior "
    "archive progress, then start timing; do not point to controls.",
    "Confirm the tester chooses New Game and the target campaign without help.",
    "Record whether Turn 1 is completed without operator guidance.",
    "Ask the tester to use Pause, Back, and return to Menu without hints.",
    "After both campaign choices, ask the tester to explain each trade-off.",
    "Continue until Act 3 or a blocker stops progress; note the exact screen and control.",
    "At the ending, use Save & Archive and confirm the route appears in Progress.",
    "Record one anonymous concrete observation only after the real session ends.",
)

_OWNER_REHEARSAL_CHECKLIST = (
    "Confirm the dedicated rehearsal profile has no prior save or archive, then run the "
    "visible route yourself; do not count this rehearsal as human evidence.",
    "Choose New Game and complete Guided Opening without using developer tools or "
    "source-code knowledge.",
    "Use Pause, Back, Menu, and Continue so every recovery route is visible and the run "
    "returns without accidental loss.",
    "Complete Commitment and Consequence, then switch between guided and full Endgame "
    "while checking the recommended fix and main risk.",
    "Finish the run, use Save & Archive, open Progress, and confirm the archived route "
    "appears in the Route Atlas.",
    "Record only defects actually observed; never run the human-session recorder for "
    "this owner rehearsal.",
)

_SESSION_TRIAGE_RULES = (
    (
        "P0",
        "Release blocker",
        "The game crashes, loses or corrupts save/archive data, hard-locks, or leaves "
        "no visible recovery or return route.",
        "Stop immediately and do not coach around the failure. Capture the exact scene "
        "and control. For a real observed tester, record blocker FOUND; never record an "
        "owner rehearsal as human evidence.",
    ),
    (
        "P1",
        "Usability blocker",
        "The tester cannot identify a required primary action, use Pause/Back/Menu "
        "recovery, read a required choice, or explain the choice without a hint.",
        "Observe without coaching first and mark the matching check FAIL. Stop only if "
        "the tester cannot continue; record blocker FOUND only when progress is blocked.",
    ),
    (
        "P2",
        "Polish defect",
        "A cosmetic alignment, motion, feedback, or wording defect is visible while "
        "comprehension and progress remain possible.",
        "Continue the session and record one concrete anonymous observation afterward. "
        "Keep blocker NONE unless the issue escalates or prevents progress.",
    ),
)


@dataclass(frozen=True)
class BetaPlaytestTriageRule:
    """One deterministic severity and operator-response rule."""

    priority: str
    label: str
    trigger: str
    response: str


_DEFAULT_SESSION_TRIAGE_RULES = tuple(
    BetaPlaytestTriageRule(*rule) for rule in _SESSION_TRIAGE_RULES
)


@dataclass(frozen=True)
class BetaPlaytestPreparation:
    """A privacy-safe packet for one next human session or release review."""

    game_version: str
    evidence_status: str
    session_progress: str
    evidence_fingerprint: str
    target_scenario_id: str | None
    target_track_label: str
    target_reason: str
    retest_of_session_key: str | None
    session_key: str
    tester_code: str
    interface_mode: BetaPlaytestInterface
    viewport: str
    motion_mode: MotionMode
    command_prefix: str
    packet_output_path: str
    evidence_database_path: str
    session_database_path: str
    owner_rehearsal_database_path: str
    owner_rehearsal_required: bool
    checklist: tuple[str, ...] = _SESSION_CHECKLIST
    owner_rehearsal_checklist: tuple[str, ...] = _OWNER_REHEARSAL_CHECKLIST
    triage_rules: tuple[BetaPlaytestTriageRule, ...] = _DEFAULT_SESSION_TRIAGE_RULES

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
        """Launch one tester against an isolated, disposable gameplay profile."""

        return self._launch_command(self.session_database_path)

    @property
    def owner_rehearsal_launch_command(self) -> str:
        """Launch owner rehearsal without contaminating the tester or evidence database."""

        return self._launch_command(self.owner_rehearsal_database_path)

    def _launch_command(self, database_path: str) -> str:
        if not self.requires_session:
            return ""
        if self.interface_mode is BetaPlaytestInterface.TWO_D:
            return _command(
                self.command_prefix,
                "menu-2d",
                "--db-path",
                database_path,
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
            database_path,
        )

    @property
    def record_command(self) -> str:
        if not self.requires_session:
            return ""
        arguments: list[object] = [
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
            self.evidence_database_path,
        ]
        if self.retest_of_session_key is not None:
            arguments.extend(("--retest-of", self.retest_of_session_key))
        return _command(self.command_prefix, *arguments)

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
    def archive_command(self) -> str:
        return _command(
            self.command_prefix,
            "beta-evidence",
            "--db-path",
            self.evidence_database_path,
        )

    @property
    def validation_command(self) -> str:
        return _command(
            self.command_prefix,
            "validate-beta-playtest-session-packet",
            "--input",
            self.packet_output_path,
            "--db-path",
            self.evidence_database_path,
        )


@dataclass(frozen=True)
class BetaPlaytestPacketManifest:
    """Deterministic reconstruction inputs and evidence snapshot embedded in a packet."""

    schema_version: int
    game_version: str
    evidence_status: str
    session_progress: str
    evidence_fingerprint: str
    target_scenario_id: str | None
    target_track_label: str
    target_reason: str
    retest_of_session_key: str | None
    session_key: str
    tester_code: str
    interface_mode: BetaPlaytestInterface
    viewport: str
    motion_mode: MotionMode
    command_prefix: str
    packet_output_path: str
    evidence_database_path: str
    session_database_path: str
    owner_rehearsal_database_path: str
    owner_rehearsal_required: bool

    @classmethod
    def from_preparation(
        cls,
        preparation: BetaPlaytestPreparation,
    ) -> BetaPlaytestPacketManifest:
        return cls(
            schema_version=_PACKET_MANIFEST_SCHEMA_VERSION,
            game_version=preparation.game_version,
            evidence_status=preparation.evidence_status,
            session_progress=preparation.session_progress,
            evidence_fingerprint=preparation.evidence_fingerprint,
            target_scenario_id=preparation.target_scenario_id,
            target_track_label=preparation.target_track_label,
            target_reason=preparation.target_reason,
            retest_of_session_key=preparation.retest_of_session_key,
            session_key=preparation.session_key,
            tester_code=preparation.tester_code,
            interface_mode=preparation.interface_mode,
            viewport=preparation.viewport,
            motion_mode=preparation.motion_mode,
            command_prefix=preparation.command_prefix,
            packet_output_path=preparation.packet_output_path,
            evidence_database_path=preparation.evidence_database_path,
            session_database_path=preparation.session_database_path,
            owner_rehearsal_database_path=preparation.owner_rehearsal_database_path,
            owner_rehearsal_required=preparation.owner_rehearsal_required,
        )

    def encode(self) -> str:
        payload = {
            "command_prefix": self.command_prefix,
            "evidence_database_path": self.evidence_database_path,
            "evidence_fingerprint": self.evidence_fingerprint,
            "evidence_status": self.evidence_status,
            "game_version": self.game_version,
            "interface_mode": self.interface_mode.value,
            "motion_mode": self.motion_mode.value,
            "owner_rehearsal_database_path": self.owner_rehearsal_database_path,
            "owner_rehearsal_required": self.owner_rehearsal_required,
            "packet_output_path": self.packet_output_path,
            "retest_of_session_key": self.retest_of_session_key,
            "schema_version": self.schema_version,
            "session_database_path": self.session_database_path,
            "session_key": self.session_key,
            "session_progress": self.session_progress,
            "target_reason": self.target_reason,
            "target_scenario_id": self.target_scenario_id,
            "target_track_label": self.target_track_label,
            "tester_code": self.tester_code,
            "viewport": self.viewport,
        }
        encoded = base64.urlsafe_b64encode(
            json.dumps(
                payload,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).decode("ascii")
        return f"{_PACKET_MANIFEST_PREFIX}{encoded.rstrip('=')}{_PACKET_MANIFEST_SUFFIX}"


def decode_beta_playtest_packet_manifest(markdown: str) -> BetaPlaytestPacketManifest:
    """Decode exactly one manifest while rejecting malformed or ambiguous packets."""

    matches = _PACKET_MANIFEST_PATTERN.findall(markdown)
    if len(matches) != 1:
        raise ValueError("Packet must contain exactly one valid NEXUS TECH beta packet manifest.")
    encoded = matches[0]
    padded = encoded + ("=" * (-len(encoded) % 4))
    try:
        decoded = base64.b64decode(padded, altchars=b"-_", validate=True)
        raw_manifest = json.loads(decoded.decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Packet manifest is malformed; regenerate the packet.") from error
    if not isinstance(raw_manifest, dict):
        raise ValueError("Packet manifest must decode to an object.")

    expected_keys = {
        "command_prefix",
        "evidence_database_path",
        "evidence_fingerprint",
        "evidence_status",
        "game_version",
        "interface_mode",
        "motion_mode",
        "owner_rehearsal_database_path",
        "owner_rehearsal_required",
        "packet_output_path",
        "retest_of_session_key",
        "schema_version",
        "session_database_path",
        "session_key",
        "session_progress",
        "target_reason",
        "target_scenario_id",
        "target_track_label",
        "tester_code",
        "viewport",
    }
    if set(raw_manifest) != expected_keys:
        raise ValueError("Packet manifest fields are invalid; regenerate the packet.")
    if (
        type(raw_manifest["schema_version"]) is not int
        or raw_manifest["schema_version"] != _PACKET_MANIFEST_SCHEMA_VERSION
    ):
        raise ValueError("Packet manifest schema is unsupported; regenerate the packet.")

    string_fields = expected_keys - {
        "owner_rehearsal_required",
        "retest_of_session_key",
        "schema_version",
        "target_scenario_id",
    }
    if any(
        not isinstance(raw_manifest[field], str) or not raw_manifest[field]
        for field in string_fields
    ):
        raise ValueError("Packet manifest contains an invalid text field.")
    if re.fullmatch(r"[0-9a-f]{64}", raw_manifest["evidence_fingerprint"]) is None:
        raise ValueError("Packet manifest contains an invalid evidence fingerprint.")
    target_scenario_id = raw_manifest["target_scenario_id"]
    if target_scenario_id is not None and (
        not isinstance(target_scenario_id, str) or not target_scenario_id
    ):
        raise ValueError("Packet manifest contains an invalid target scenario.")
    retest_of_session_key = raw_manifest["retest_of_session_key"]
    if retest_of_session_key is not None and (
        not isinstance(retest_of_session_key, str) or not retest_of_session_key
    ):
        raise ValueError("Packet manifest contains an invalid retest session key.")
    if not isinstance(raw_manifest["owner_rehearsal_required"], bool):
        raise ValueError("Packet manifest contains an invalid rehearsal flag.")

    try:
        interface_mode = BetaPlaytestInterface(raw_manifest["interface_mode"])
    except ValueError as error:
        raise ValueError("Packet manifest contains an unsupported interface mode.") from error
    try:
        motion_mode = MotionMode(raw_manifest["motion_mode"])
    except ValueError as error:
        raise ValueError("Packet manifest contains an unsupported motion mode.") from error

    return BetaPlaytestPacketManifest(
        schema_version=raw_manifest["schema_version"],
        game_version=raw_manifest["game_version"],
        evidence_status=raw_manifest["evidence_status"],
        session_progress=raw_manifest["session_progress"],
        evidence_fingerprint=raw_manifest["evidence_fingerprint"],
        target_scenario_id=target_scenario_id,
        target_track_label=raw_manifest["target_track_label"],
        target_reason=raw_manifest["target_reason"],
        retest_of_session_key=retest_of_session_key,
        session_key=raw_manifest["session_key"],
        tester_code=raw_manifest["tester_code"],
        interface_mode=interface_mode,
        viewport=raw_manifest["viewport"],
        motion_mode=motion_mode,
        command_prefix=raw_manifest["command_prefix"],
        packet_output_path=raw_manifest["packet_output_path"],
        evidence_database_path=raw_manifest["evidence_database_path"],
        session_database_path=raw_manifest["session_database_path"],
        owner_rehearsal_database_path=raw_manifest["owner_rehearsal_database_path"],
        owner_rehearsal_required=raw_manifest["owner_rehearsal_required"],
    )


def build_beta_playtest_preparation(
    sessions: list[BetaPlaytestSession],
    *,
    game_version: str,
    interface_mode: BetaPlaytestInterface,
    viewport: str,
    motion_mode: MotionMode,
    command_prefix: str,
    packet_output_path: str,
    evidence_database_path: str,
    session_database_path: str,
    owner_rehearsal_database_path: str,
) -> BetaPlaytestPreparation:
    """Select the next honest session target without copying observation notes."""

    if not isinstance(interface_mode, BetaPlaytestInterface):
        raise ValueError("Interface mode must be terminal or 2d.")
    if not isinstance(motion_mode, MotionMode):
        raise ValueError("Motion mode must be full, reduced, or off.")
    _validate_packet_input(
        viewport=viewport,
        command_prefix=command_prefix,
        packet_output_path=packet_output_path,
        evidence_database_path=evidence_database_path,
        session_database_path=session_database_path,
        owner_rehearsal_database_path=owner_rehearsal_database_path,
    )
    status = build_beta_playtest_status(sessions, game_version=game_version)
    target = select_beta_playtest_target(status)
    return BetaPlaytestPreparation(
        game_version=game_version,
        evidence_status=status.status,
        session_progress=status.session_progress,
        evidence_fingerprint=_beta_evidence_fingerprint(sessions),
        target_scenario_id=(target.lane.scenario_id if target.lane is not None else None),
        target_track_label=(target.lane.track_label if target.lane is not None else "Review"),
        target_reason=target.reason,
        retest_of_session_key=(
            target.retest_of.session_key if target.retest_of is not None else None
        ),
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
        packet_output_path=packet_output_path.strip(),
        evidence_database_path=evidence_database_path.strip(),
        session_database_path=session_database_path.strip(),
        owner_rehearsal_database_path=owner_rehearsal_database_path.strip(),
        owner_rehearsal_required=status.session_count == 0 and target.lane is not None,
    )


def _beta_evidence_fingerprint(sessions: list[BetaPlaytestSession]) -> str:
    rows = []
    for session in sessions:
        row = {
            "act_three": session.reached_act_three,
            "blocker": session.blocker_found,
            "first_turn_seconds": session.first_turn_seconds,
            "game_version": session.game_version,
            "interface": session.interface_mode.value,
            "notes": session.notes,
            "pause_back": session.pause_back_success,
            "recorded_at": session.recorded_at,
            "retest_of": session.retest_of,
            "scenario_id": session.scenario_id,
            "session_key": session.session_key,
            "tester_code": session.tester_code,
            "tradeoff": session.tradeoff_explained,
            "turn_one": session.turn_one_unaided,
            "viewport": session.viewport,
        }
        rows.append(json.dumps(row, ensure_ascii=True, separators=(",", ":"), sort_keys=True))
    canonical = f"[{','.join(sorted(rows))}]".encode()
    return hashlib.sha256(canonical).hexdigest()


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
    packet_output_path: str,
    evidence_database_path: str,
    session_database_path: str,
    owner_rehearsal_database_path: str,
) -> None:
    if re.fullmatch(r"[0-9]{2,4}x[0-9]{2,4}", viewport) is None:
        raise ValueError("Viewport must use WIDTHxHEIGHT, for example 820x620 or 120x40.")
    for label, value in (
        ("Command prefix", command_prefix),
        ("Packet output path", packet_output_path),
        ("Evidence database path", evidence_database_path),
        ("Session database path", session_database_path),
        ("Owner rehearsal database path", owner_rehearsal_database_path),
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
    normalized_database_paths = {
        _normalized_path(evidence_database_path),
        _normalized_path(session_database_path),
        _normalized_path(owner_rehearsal_database_path),
    }
    if len(normalized_database_paths) != 3:
        raise ValueError("Evidence, session, and owner rehearsal database paths must be distinct.")
    protected_database_artifacts = {
        _normalized_path(f"{database_path}{suffix}")
        for database_path in (
            evidence_database_path,
            session_database_path,
            owner_rehearsal_database_path,
        )
        for suffix in ("", "-journal", "-wal", "-shm")
    }
    if _normalized_path(packet_output_path) in protected_database_artifacts:
        raise ValueError("Packet output and gameplay/evidence database paths must be distinct.")


def _normalized_path(value: str) -> Path:
    return Path(value.strip()).expanduser().resolve(strict=False)


def _command(prefix: str, *arguments: object) -> str:
    suffix = " ".join(shlex.quote(str(argument)) for argument in arguments)
    return f"{prefix.strip()} {suffix}"
