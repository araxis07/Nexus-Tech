"""Local, privacy-conscious storage for real beta playtest observations."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from nexus_tech.persistence.database import DatabaseManager
from nexus_tech.persistence.errors import PersistenceError


class BetaPlaytestInterface(StrEnum):
    """Supported interfaces for one observed human playtest session."""

    TERMINAL = "terminal"
    TWO_D = "2d"


@dataclass(frozen=True)
class BetaPlaytestSession:
    """One structured observation recorded after a real human session."""

    session_key: str
    tester_code: str
    scenario_id: str
    interface_mode: BetaPlaytestInterface
    viewport: str
    first_turn_seconds: int
    turn_one_unaided: bool
    pause_back_success: bool
    tradeoff_explained: bool
    reached_act_three: bool
    blocker_found: bool
    notes: str
    game_version: str
    recorded_at: str


class BetaPlaytestRepository:
    """Persist human evidence separately from gameplay saves and run archives."""

    def __init__(self, db_path: Path) -> None:
        self.database = DatabaseManager(db_path)

    def save_session(
        self,
        session: BetaPlaytestSession,
        *,
        replace: bool = False,
    ) -> None:
        """Insert one session, requiring explicit replacement for an existing key."""

        validate_beta_playtest_session(session)
        try:
            self.database.initialize()
            with self.database.connect() as connection:
                existing = connection.execute(
                    "SELECT 1 FROM beta_playtest_sessions WHERE session_key = ?",
                    (session.session_key,),
                ).fetchone()
                if existing is not None and not replace:
                    raise PersistenceError(
                        f"Beta playtest session '{session.session_key}' already exists. "
                        "Use explicit replacement only when correcting that observation."
                    )
                connection.execute(
                    """
                    INSERT INTO beta_playtest_sessions (
                        session_key,
                        tester_code,
                        scenario_id,
                        interface_mode,
                        viewport,
                        first_turn_seconds,
                        turn_one_unaided,
                        pause_back_success,
                        tradeoff_explained,
                        reached_act_three,
                        blocker_found,
                        notes,
                        game_version,
                        recorded_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_key) DO UPDATE SET
                        tester_code = excluded.tester_code,
                        scenario_id = excluded.scenario_id,
                        interface_mode = excluded.interface_mode,
                        viewport = excluded.viewport,
                        first_turn_seconds = excluded.first_turn_seconds,
                        turn_one_unaided = excluded.turn_one_unaided,
                        pause_back_success = excluded.pause_back_success,
                        tradeoff_explained = excluded.tradeoff_explained,
                        reached_act_three = excluded.reached_act_three,
                        blocker_found = excluded.blocker_found,
                        notes = excluded.notes,
                        game_version = excluded.game_version,
                        recorded_at = excluded.recorded_at
                    """,
                    (
                        session.session_key,
                        session.tester_code,
                        session.scenario_id,
                        session.interface_mode.value,
                        session.viewport,
                        session.first_turn_seconds,
                        int(session.turn_one_unaided),
                        int(session.pause_back_success),
                        int(session.tradeoff_explained),
                        int(session.reached_act_three),
                        int(session.blocker_found),
                        session.notes.strip(),
                        session.game_version,
                        session.recorded_at,
                    ),
                )
        except PersistenceError:
            raise
        except sqlite3.DatabaseError as error:
            raise PersistenceError(f"Failed to save beta playtest evidence: {error}") from error

    def list_sessions(self) -> list[BetaPlaytestSession]:
        """Return recorded observations in stable chronological order."""

        try:
            self.database.initialize()
            with self.database.connect() as connection:
                rows = connection.execute(
                    """
                    SELECT
                        session_key,
                        tester_code,
                        scenario_id,
                        interface_mode,
                        viewport,
                        first_turn_seconds,
                        turn_one_unaided,
                        pause_back_success,
                        tradeoff_explained,
                        reached_act_three,
                        blocker_found,
                        notes,
                        game_version,
                        recorded_at
                    FROM beta_playtest_sessions
                    ORDER BY recorded_at, session_key
                    """
                ).fetchall()
        except sqlite3.DatabaseError as error:
            raise PersistenceError(f"Failed to read beta playtest evidence: {error}") from error

        try:
            return [
                BetaPlaytestSession(
                    session_key=row["session_key"],
                    tester_code=row["tester_code"],
                    scenario_id=row["scenario_id"],
                    interface_mode=BetaPlaytestInterface(row["interface_mode"]),
                    viewport=row["viewport"],
                    first_turn_seconds=row["first_turn_seconds"],
                    turn_one_unaided=bool(row["turn_one_unaided"]),
                    pause_back_success=bool(row["pause_back_success"]),
                    tradeoff_explained=bool(row["tradeoff_explained"]),
                    reached_act_three=bool(row["reached_act_three"]),
                    blocker_found=bool(row["blocker_found"]),
                    notes=row["notes"],
                    game_version=row["game_version"],
                    recorded_at=row["recorded_at"],
                )
                for row in rows
            ]
        except (TypeError, ValueError) as error:
            raise PersistenceError(
                f"Beta playtest evidence contains an invalid stored value: {error}"
            ) from error


def validate_beta_playtest_session(session: BetaPlaytestSession) -> None:
    """Reject malformed, identifying, or placeholder evidence before persistence."""

    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{1,39}", session.session_key) is None:
        raise ValueError("Session key must be 2-40 letters, numbers, underscores, or hyphens.")
    if re.fullmatch(r"T[0-9]{2,6}", session.tester_code) is None:
        raise ValueError(
            "Tester code must use anonymous format T plus 2-6 digits, for example T01."
        )
    if not session.scenario_id.strip():
        raise ValueError("Scenario id is required.")
    if not isinstance(session.interface_mode, BetaPlaytestInterface):
        raise ValueError("Interface mode must be terminal or 2d.")
    if re.fullmatch(r"[0-9]{2,4}x[0-9]{2,4}", session.viewport) is None:
        raise ValueError("Viewport must use WIDTHxHEIGHT, for example 1280x720 or 120x40.")
    if not 1 <= session.first_turn_seconds <= 3600:
        raise ValueError("First-turn timing must be between 1 and 3600 seconds.")
    if not is_substantive_beta_playtest_note(session.notes):
        raise ValueError(
            "Evidence notes must contain a concrete real-session observation of at least 20 "
            "characters; placeholders and automated claims are rejected."
        )
    if _contains_sensitive_note_content(session.notes):
        raise ValueError(
            "Evidence notes must not contain email addresses, local paths, tokens, or secrets."
        )
    if not session.game_version.strip() or not session.recorded_at.strip():
        raise ValueError("Game version and recorded timestamp are required.")


def is_substantive_beta_playtest_note(notes: str) -> bool:
    """Return whether notes look like concrete observations rather than placeholders."""

    normalized = " ".join(notes.strip().lower().split())
    if len(normalized) < 20:
        return False
    placeholders = {
        "automated",
        "automation passed",
        "manual required",
        "n/a",
        "none",
        "pass",
        "placeholder",
        "todo",
    }
    rejected_prefixes = ("automated ", "replace ")
    return normalized not in placeholders and not normalized.startswith(rejected_prefixes)


def _contains_sensitive_note_content(notes: str) -> bool:
    normalized = notes.strip().lower()
    sensitive_patterns = (
        r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b",
        r"(?:^|\s)/(?:users|home|private|tmp)/",
        r"\b(?:api[_-]?key|access[_-]?token|secret|password)\s*[:=]",
        r"\b(?:ghp|github_pat|sk)-?[a-z0-9_-]{8,}\b",
    )
    return any(re.search(pattern, normalized) for pattern in sensitive_patterns)
