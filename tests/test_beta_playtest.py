from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from nexus_tech import __version__
from nexus_tech.cli import app
from nexus_tech.persistence.beta_playtest_repository import (
    BetaPlaytestInterface,
    BetaPlaytestRepository,
    BetaPlaytestSession,
)
from nexus_tech.persistence.errors import PersistenceError
from nexus_tech.simulation.beta_playtest import build_beta_playtest_status
from nexus_tech.simulation.campaign_journey import list_featured_campaign_journeys

runner = CliRunner()


def make_session(
    index: int,
    scenario_id: str,
    *,
    game_version: str = __version__,
    blocker_found: bool = False,
    notes: str = "Tester found the controls and explained both campaign trade-offs clearly.",
) -> BetaPlaytestSession:
    return BetaPlaytestSession(
        session_key=f"beta-{index:03d}",
        tester_code=f"T{index:02d}",
        scenario_id=scenario_id,
        interface_mode=(
            BetaPlaytestInterface.TERMINAL if index % 2 else BetaPlaytestInterface.TWO_D
        ),
        viewport="1280x720",
        first_turn_seconds=90 + index,
        turn_one_unaided=True,
        pause_back_success=True,
        tradeoff_explained=True,
        reached_act_three=True,
        blocker_found=blocker_found,
        notes=notes,
        game_version=game_version,
        recorded_at=f"2026-07-15T00:0{index}:00+00:00",
    )


def test_beta_playtest_repository_round_trip_and_schema_26(tmp_path: Path) -> None:
    db_path = tmp_path / "beta.db"
    repository = BetaPlaytestRepository(db_path)
    session = make_session(1, "founder_journey")

    repository.save_session(session)

    assert repository.list_sessions() == [session]
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 26


def test_beta_playtest_repository_requires_explicit_replace(tmp_path: Path) -> None:
    repository = BetaPlaytestRepository(tmp_path / "beta.db")
    session = make_session(1, "founder_journey")
    repository.save_session(session)

    with pytest.raises(PersistenceError, match="already exists"):
        repository.save_session(session)

    replacement = BetaPlaytestSession(
        **{
            **session.__dict__,
            "first_turn_seconds": 77,
            "notes": "Corrected timing from the same observed human playtest session.",
        }
    )
    repository.save_session(replacement, replace=True)

    assert repository.list_sessions() == [replacement]


def test_beta_playtest_repository_reports_invalid_stored_interface(tmp_path: Path) -> None:
    db_path = tmp_path / "corrupt-beta.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE beta_playtest_sessions (
                session_key TEXT PRIMARY KEY,
                tester_code TEXT NOT NULL,
                scenario_id TEXT NOT NULL,
                interface_mode TEXT NOT NULL,
                viewport TEXT NOT NULL,
                first_turn_seconds INTEGER NOT NULL,
                turn_one_unaided INTEGER NOT NULL,
                pause_back_success INTEGER NOT NULL,
                tradeoff_explained INTEGER NOT NULL,
                reached_act_three INTEGER NOT NULL,
                blocker_found INTEGER NOT NULL,
                notes TEXT NOT NULL,
                game_version TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO beta_playtest_sessions
            VALUES (
                'beta-001', 'T01', 'founder_journey', 'web', '1280x720', 94,
                1, 1, 1, 1, 0, 'Concrete observed session note for corruption testing.',
                '0.288.0', '2026-07-15T00:01:00+00:00'
            )
            """
        )

    with pytest.raises(PersistenceError, match="invalid stored value"):
        BetaPlaytestRepository(db_path).list_sessions()


@pytest.mark.parametrize(
    ("tester_code", "notes", "message"),
    (
        (
            "tester@example.com",
            "Tester completed the observed route with no operator assistance.",
            "anonymous format",
        ),
        (
            "Alice",
            "Tester completed the observed route with no operator assistance.",
            "anonymous format",
        ),
        ("T01", "placeholder", "concrete real-session observation"),
        (
            "T01",
            "REPLACE with a concrete observation from the real session",
            "concrete real-session observation",
        ),
        (
            "T01",
            "Tester contact tester@example.com completed the observed route.",
            "must not contain",
        ),
        (
            "T01",
            "Tester used /Users/example/private-note while completing the route.",
            "must not contain",
        ),
    ),
)
def test_beta_playtest_repository_rejects_identifying_or_placeholder_evidence(
    tmp_path: Path,
    tester_code: str,
    notes: str,
    message: str,
) -> None:
    repository = BetaPlaytestRepository(tmp_path / "beta.db")
    session = make_session(1, "founder_journey", notes=notes)
    invalid_session = BetaPlaytestSession(**{**session.__dict__, "tester_code": tester_code})

    with pytest.raises(ValueError, match=message):
        repository.save_session(invalid_session)


def test_beta_playtest_status_requires_six_current_human_sessions() -> None:
    status = build_beta_playtest_status([], game_version=__version__)

    assert status.status == "human-sessions-needed"
    assert not status.review_ready
    assert status.session_progress == "0/6 current-version sessions"
    assert status.covered_campaigns == 0


def test_beta_playtest_status_reaches_manual_review_with_six_campaigns() -> None:
    sessions = [
        make_session(index, journey.scenario_id)
        for index, journey in enumerate(list_featured_campaign_journeys(), start=1)
    ]

    status = build_beta_playtest_status(sessions, game_version=__version__)

    assert status.status == "human-evidence-ready-for-review"
    assert status.review_ready
    assert status.covered_campaigns == 6
    assert status.unique_testers == 6
    assert not status.gate_failures
    assert "manual beta release decision" in status.next_action


def test_beta_playtest_status_fails_when_a_blocker_is_recorded() -> None:
    sessions = [
        make_session(
            index,
            journey.scenario_id,
            blocker_found=index == 1,
        )
        for index, journey in enumerate(list_featured_campaign_journeys(), start=1)
    ]

    status = build_beta_playtest_status(sessions, game_version=__version__)

    assert status.status == "human-gate-failed"
    assert not status.review_ready
    assert status.blocker_sessions == 1
    assert any("blocker-level" in failure for failure in status.gate_failures)


def test_beta_playtest_status_excludes_stale_version_evidence() -> None:
    stale = make_session(1, "founder_journey", game_version="0.287.0")

    status = build_beta_playtest_status([stale], game_version="0.288.0")

    assert status.session_count == 0
    assert status.stale_sessions == 1
    assert status.status == "human-sessions-needed"


def test_beta_playtest_cli_records_and_reviews_local_evidence(tmp_path: Path) -> None:
    db_path = tmp_path / "beta.db"
    result = runner.invoke(
        app,
        [
            "record-beta-playtest-session",
            "--session-key",
            "beta-001",
            "--tester-code",
            "T01",
            "--scenario",
            "founder_journey",
            "--interface",
            "2d",
            "--viewport",
            "1280x720",
            "--first-turn-seconds",
            "94",
            "--turn-one",
            "pass",
            "--pause-back",
            "pass",
            "--tradeoff",
            "pass",
            "--act-three",
            "pass",
            "--blocker",
            "none",
            "--notes",
            "Tester located Pause and returned to the menu without operator help.",
            "--confirm-human-session",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 0
    assert "Human Beta Evidence" in result.output
    assert "1/6 current-version sessions" in result.output
    assert "beta-001" in result.output
    assert "Tester located Pause" not in result.output

    status_result = runner.invoke(
        app,
        ["beta-playtest-status", "--db-path", str(db_path)],
    )
    assert status_result.exit_code == 0
    assert "Six-Campaign Session Coverage" in status_result.output
    assert "human-sessions-needed" in status_result.output


def test_beta_playtest_cli_requires_explicit_human_attestation(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "record-beta-playtest-session",
            "--session-key",
            "beta-001",
            "--tester-code",
            "T01",
            "--scenario",
            "founder_journey",
            "--interface",
            "terminal",
            "--viewport",
            "120x40",
            "--first-turn-seconds",
            "94",
            "--turn-one",
            "pass",
            "--pause-back",
            "pass",
            "--tradeoff",
            "pass",
            "--act-three",
            "pass",
            "--blocker",
            "none",
            "--notes",
            "Tester completed the observed route without operator assistance.",
            "--db-path",
            str(tmp_path / "beta.db"),
        ],
    )

    assert result.exit_code == 1
    assert "Human Session Confirmation Required" in result.output
    assert not (tmp_path / "beta.db").exists()
