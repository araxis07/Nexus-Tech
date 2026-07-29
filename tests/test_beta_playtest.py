from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

import nexus_tech.cli_command_prefix as command_prefix_module
from nexus_tech import __version__
from nexus_tech.cli import app
from nexus_tech.persistence.beta_playtest_repository import (
    BetaPlaytestInterface,
    BetaPlaytestRepository,
    BetaPlaytestSession,
    is_substantive_beta_playtest_note,
)
from nexus_tech.persistence.errors import PersistenceError
from nexus_tech.simulation.beta_playtest import build_beta_playtest_status
from nexus_tech.simulation.beta_playtest_execution import (
    build_beta_playtest_execution_plan,
)
from nexus_tech.simulation.beta_playtest_preparation import (
    build_beta_playtest_preparation,
)
from nexus_tech.simulation.campaign_journey import list_featured_campaign_journeys
from nexus_tech.user_preferences import MotionMode

runner = CliRunner()


def make_session(
    index: int,
    scenario_id: str,
    *,
    game_version: str = __version__,
    blocker_found: bool = False,
    notes: str = "Tester found the controls and explained both campaign trade-offs clearly.",
    retest_of: str | None = None,
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
        retest_of=retest_of,
    )


def test_beta_playtest_repository_round_trip_and_schema_28(tmp_path: Path) -> None:
    db_path = tmp_path / "beta.db"
    repository = BetaPlaytestRepository(db_path)
    session = make_session(1, "founder_journey")

    repository.save_session(session)

    assert repository.list_sessions() == [session]
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 28


def test_beta_playtest_repository_migrates_schema_27_without_losing_evidence(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "schema-27-beta.db"
    session = make_session(1, "founder_journey")
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                session.notes,
                session.game_version,
                session.recorded_at,
            ),
        )
        connection.execute("PRAGMA user_version = 27")

    assert BetaPlaytestRepository(db_path).list_sessions() == [session]
    with sqlite3.connect(db_path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(beta_playtest_sessions)").fetchall()
        }
        assert "retest_of" in columns
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 28


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


def test_beta_playtest_repository_requires_new_current_version_tester(
    tmp_path: Path,
) -> None:
    repository = BetaPlaytestRepository(tmp_path / "beta.db")
    repository.save_session(make_session(1, "founder_journey"))
    duplicate_tester = BetaPlaytestSession(
        **{
            **make_session(2, "bootstrap_studio").__dict__,
            "tester_code": "T01",
        }
    )

    with pytest.raises(PersistenceError, match="new anonymous first-time tester"):
        repository.save_session(duplicate_tester)


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


def test_beta_playtest_execution_plan_queues_six_lanes_one_session_at_a_time() -> None:
    plan = build_beta_playtest_execution_plan(
        [],
        game_version=__version__,
        command_prefix=".venv313/bin/nexus-tech",
        evidence_database_path="nexus-tech.db",
        packet_output_path="/tmp/nexus-tech-beta-playtest-next.md",
        plan_output_path="/tmp/nexus-tech-beta-playtest-plan.md",
    )

    assert plan.owner_rehearsal_required
    assert len(plan.lanes) == 6
    assert plan.lanes[0].scenario_id == "founder_journey"
    assert plan.lanes[0].state == "NEXT SESSION"
    assert all(lane.state == "QUEUED" for lane in plan.lanes[1:])
    assert "prepare-beta-playtest-session" in plan.prepare_command
    assert "--command-prefix .venv313/bin/nexus-tech" in plan.prepare_command
    assert "--require-review-ready" in plan.review_gate_command


@pytest.mark.parametrize(
    ("packet_name", "plan_name", "message"),
    (
        (
            "artifacts/../execution-plan.md",
            "execution-plan.md",
            "Packet and execution-plan output paths must be distinct",
        ),
        (
            "next-session.md",
            "evidence.db",
            "must not overwrite the evidence database",
        ),
        (
            "next-session.md",
            "evidence.db-wal",
            "must not overwrite the evidence database",
        ),
        (
            "evidence.db-shm",
            "execution-plan.md",
            "must not overwrite the evidence database",
        ),
    ),
)
def test_beta_playtest_execution_plan_rejects_normalized_artifact_collisions(
    tmp_path: Path,
    packet_name: str,
    plan_name: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        build_beta_playtest_execution_plan(
            [],
            game_version=__version__,
            command_prefix="nexus-tech",
            evidence_database_path=str(tmp_path / "evidence.db"),
            packet_output_path=str(tmp_path / packet_name),
            plan_output_path=str(tmp_path / plan_name),
        )


@pytest.mark.parametrize("sidecar_base", ("alias", "target"))
def test_beta_playtest_execution_plan_rejects_symlinked_evidence_sidecars(
    tmp_path: Path,
    sidecar_base: str,
) -> None:
    evidence_target = tmp_path / "evidence-target.db"
    evidence_target.touch()
    evidence_alias = tmp_path / "evidence-alias.db"
    evidence_alias.symlink_to(evidence_target)
    bases = {
        "alias": evidence_alias,
        "target": evidence_target,
    }

    with pytest.raises(ValueError, match="must not overwrite the evidence database"):
        build_beta_playtest_execution_plan(
            [],
            game_version=__version__,
            command_prefix="nexus-tech",
            evidence_database_path=str(evidence_alias),
            packet_output_path=f"{bases[sidecar_base]}-wal",
            plan_output_path=str(tmp_path / "execution-plan.md"),
        )


def test_beta_playtest_execution_plan_targets_active_retest_without_copying_notes() -> None:
    sessions = [
        make_session(
            index,
            journey.scenario_id,
            blocker_found=index == 1,
        )
        for index, journey in enumerate(list_featured_campaign_journeys(), start=1)
    ]

    plan = build_beta_playtest_execution_plan(
        sessions,
        game_version=__version__,
        command_prefix="nexus-tech",
        evidence_database_path="nexus-tech.db",
        packet_output_path="/tmp/next.md",
        plan_output_path="/tmp/plan.md",
    )

    assert plan.target.kind == "retest"
    assert plan.target.retest_of is not None
    assert plan.target.retest_of.session_key == "beta-001"
    assert plan.lanes[0].state == "NEXT RETEST"
    assert plan.lanes[0].follow_up.endswith("with a new first-time tester.")
    assert all(session.notes not in plan.lanes[0].follow_up for session in sessions)


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


def test_beta_playtest_retest_preserves_history_and_closes_resolved_blocker(
    tmp_path: Path,
) -> None:
    journeys = list_featured_campaign_journeys()
    repository = BetaPlaytestRepository(tmp_path / "beta.db")
    blocked = make_session(1, journeys[0].scenario_id, blocker_found=True)
    repository.save_session(blocked)
    for index, journey in enumerate(journeys[1:], start=2):
        repository.save_session(make_session(index, journey.scenario_id))
    retest = make_session(
        7,
        journeys[0].scenario_id,
        notes="A new tester completed the repaired recovery route without operator help.",
        retest_of=blocked.session_key,
    )
    repository.save_session(retest)

    stored = repository.list_sessions()
    status = build_beta_playtest_status(stored, game_version=__version__)

    assert len(stored) == 7
    assert stored[0] == blocked
    assert stored[-1] == retest
    assert status.superseded_sessions == 1
    assert status.session_count == 6
    assert status.blocker_sessions == 0
    assert status.review_ready
    assert blocked not in status.sessions
    assert retest in status.sessions


@pytest.mark.parametrize(
    ("scenario_id", "tester_code", "retest_of", "message"),
    (
        ("bootstrap_studio", "T02", "beta-001", "same featured campaign"),
        ("founder_journey", "T01", "beta-001", "new anonymous first-time tester"),
        ("founder_journey", "T02", "beta-999", "does not exist"),
    ),
)
def test_beta_playtest_repository_rejects_invalid_retest_relationship(
    tmp_path: Path,
    scenario_id: str,
    tester_code: str,
    retest_of: str,
    message: str,
) -> None:
    repository = BetaPlaytestRepository(tmp_path / "beta.db")
    repository.save_session(make_session(1, "founder_journey", blocker_found=True))
    candidate = make_session(
        2,
        scenario_id,
        retest_of=retest_of,
    )
    candidate = BetaPlaytestSession(**{**candidate.__dict__, "tester_code": tester_code})

    with pytest.raises(PersistenceError, match=message):
        repository.save_session(candidate)


def test_beta_playtest_repository_rejects_retesting_a_passing_session(
    tmp_path: Path,
) -> None:
    repository = BetaPlaytestRepository(tmp_path / "beta.db")
    repository.save_session(make_session(1, "founder_journey"))

    with pytest.raises(PersistenceError, match="does not require a retest"):
        repository.save_session(make_session(2, "founder_journey", retest_of="beta-001"))


def test_beta_playtest_repository_rejects_second_direct_retest_child(
    tmp_path: Path,
) -> None:
    repository = BetaPlaytestRepository(tmp_path / "beta.db")
    repository.save_session(make_session(1, "founder_journey", blocker_found=True))
    repository.save_session(make_session(2, "founder_journey", retest_of="beta-001"))

    with pytest.raises(PersistenceError, match="already superseded by 'beta-002'"):
        repository.save_session(make_session(3, "founder_journey", retest_of="beta-001"))


def test_beta_playtest_status_evaluates_only_leaf_of_multi_stage_retest_chain(
    tmp_path: Path,
) -> None:
    repository = BetaPlaytestRepository(tmp_path / "beta.db")
    original = make_session(1, "founder_journey", blocker_found=True)
    failed_retest = make_session(
        2,
        "founder_journey",
        blocker_found=True,
        retest_of=original.session_key,
    )
    passing_retest = make_session(
        3,
        "founder_journey",
        retest_of=failed_retest.session_key,
    )
    repository.save_session(original)
    repository.save_session(failed_retest)
    repository.save_session(passing_retest)

    status = build_beta_playtest_status(repository.list_sessions(), game_version=__version__)

    assert status.sessions == (passing_retest,)
    assert status.superseded_sessions == 2
    assert status.blocker_sessions == 0


def test_beta_playtest_repository_correction_cannot_change_retest_lineage(
    tmp_path: Path,
) -> None:
    repository = BetaPlaytestRepository(tmp_path / "beta.db")
    repository.save_session(make_session(1, "founder_journey", blocker_found=True))
    retest = make_session(2, "founder_journey", retest_of="beta-001")
    repository.save_session(retest)
    changed_lineage = BetaPlaytestSession(**{**retest.__dict__, "retest_of": None})

    with pytest.raises(PersistenceError, match="cannot change.*retest relationship"):
        repository.save_session(changed_lineage, replace=True)


def test_beta_playtest_repository_allows_retest_of_legacy_placeholder_note(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "beta.db"
    repository = BetaPlaytestRepository(db_path)
    repository.save_session(make_session(1, "founder_journey"))
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE beta_playtest_sessions SET notes = 'placeholder' WHERE session_key = ?",
            ("beta-001",),
        )

    retest = make_session(
        2,
        "founder_journey",
        notes="A new tester supplied a concrete observation for the repaired evidence lane.",
        retest_of="beta-001",
    )
    repository.save_session(retest)

    assert repository.list_sessions()[-1] == retest


def test_beta_playtest_status_excludes_stale_version_evidence() -> None:
    stale = make_session(1, "founder_journey", game_version="0.287.0")

    status = build_beta_playtest_status([stale], game_version="0.288.0")

    assert status.session_count == 0
    assert status.stale_sessions == 1
    assert status.status == "human-sessions-needed"


def test_beta_playtest_preparation_targets_first_missing_campaign_safely() -> None:
    preparation = build_beta_playtest_preparation(
        [],
        game_version=__version__,
        interface_mode=BetaPlaytestInterface.TWO_D,
        viewport="820x620",
        motion_mode=MotionMode.FULL,
        command_prefix=".venv313/bin/nexus-tech",
        packet_output_path="/tmp/nexus-tech-beta-001.md",
        evidence_database_path="nexus-tech.db",
        session_database_path="/tmp/nexus-tech-beta-001-session.db",
        owner_rehearsal_database_path="/tmp/nexus-tech-beta-001-rehearsal.db",
    )

    assert preparation.requires_session
    assert preparation.target_scenario_id == "founder_journey"
    assert preparation.target_track_label == "Learn"
    assert preparation.session_key == "beta-001"
    assert preparation.tester_code == "T01"
    assert preparation.owner_rehearsal_required
    assert preparation.retest_of_session_key is None
    rehearsal = " ".join(preparation.owner_rehearsal_checklist)
    assert "Save & Archive" in rehearsal
    assert "Route Atlas" in rehearsal
    assert "never run the human-session recorder" in rehearsal
    assert [rule.priority for rule in preparation.triage_rules] == ["P0", "P1", "P2"]
    p0, p1, p2 = preparation.triage_rules
    assert "loses or corrupts save/archive data" in p0.trigger
    assert "record blocker FOUND" in p0.response
    assert "Observe without coaching first" in p1.response
    assert "only when progress is blocked" in p1.response
    assert "comprehension and progress remain possible" in p2.trigger
    assert "Keep blocker NONE" in p2.response
    assert "menu-2d" in preparation.launch_command
    assert "nexus-tech-beta-001-session.db" in preparation.launch_command
    assert "nexus-tech-beta-001-rehearsal.db" not in preparation.launch_command
    assert "nexus-tech-beta-001-rehearsal.db" in preparation.owner_rehearsal_launch_command
    assert "nexus-tech-beta-001-session.db" not in preparation.owner_rehearsal_launch_command
    assert "--window-size 820x620" in preparation.launch_command
    assert "--scenario founder_journey" in preparation.record_command
    assert "--db-path nexus-tech.db" in preparation.record_command
    assert "--require-review-ready" in preparation.review_gate_command
    assert "validate-beta-playtest-session-packet" in preparation.validation_command
    assert "--input /tmp/nexus-tech-beta-001.md" in preparation.validation_command
    placeholder = "REPLACE with a concrete observation from the real session"
    assert placeholder in preparation.record_command
    assert not is_substantive_beta_playtest_note(placeholder)


def test_beta_playtest_preparation_advances_without_reusing_identifiers() -> None:
    existing = make_session(1, "founder_journey")

    preparation = build_beta_playtest_preparation(
        [existing],
        game_version=__version__,
        interface_mode=BetaPlaytestInterface.TERMINAL,
        viewport="120x40",
        motion_mode=MotionMode.OFF,
        command_prefix="uv run nexus-tech",
        packet_output_path="/tmp/nexus-tech-beta-002.md",
        evidence_database_path="nexus-tech.db",
        session_database_path="/tmp/nexus-tech-beta-002-session.db",
        owner_rehearsal_database_path="/tmp/nexus-tech-beta-owner-rehearsal.db",
    )

    assert preparation.target_scenario_id == "bootstrap_studio"
    assert preparation.session_key == "beta-002"
    assert preparation.tester_code == "T02"
    assert not preparation.owner_rehearsal_required
    assert "new-game --scenario bootstrap_studio" in preparation.launch_command
    assert "--motion-mode" not in preparation.launch_command


def test_beta_playtest_preparation_retests_an_unresolved_human_gate() -> None:
    sessions = [
        make_session(
            index,
            journey.scenario_id,
            blocker_found=index == 1,
        )
        for index, journey in enumerate(list_featured_campaign_journeys(), start=1)
    ]

    preparation = build_beta_playtest_preparation(
        sessions,
        game_version=__version__,
        interface_mode=BetaPlaytestInterface.TWO_D,
        viewport="1280x720",
        motion_mode=MotionMode.REDUCED,
        command_prefix="nexus-tech",
        packet_output_path="/tmp/nexus-tech-beta-007.md",
        evidence_database_path="nexus-tech.db",
        session_database_path="/tmp/nexus-tech-beta-007-session.db",
        owner_rehearsal_database_path="/tmp/nexus-tech-beta-owner-rehearsal.db",
    )

    assert preparation.target_scenario_id == "founder_journey"
    assert preparation.session_key == "beta-007"
    assert preparation.tester_code == "T07"
    assert preparation.retest_of_session_key == "beta-001"
    assert "--retest-of beta-001" in preparation.record_command
    assert "unresolved human gate" in preparation.target_reason


def test_beta_playtest_preparation_stops_when_manual_review_is_ready() -> None:
    sessions = [
        make_session(index, journey.scenario_id)
        for index, journey in enumerate(list_featured_campaign_journeys(), start=1)
    ]

    preparation = build_beta_playtest_preparation(
        sessions,
        game_version=__version__,
        interface_mode=BetaPlaytestInterface.TWO_D,
        viewport="820x620",
        motion_mode=MotionMode.FULL,
        command_prefix="nexus-tech",
        packet_output_path="/tmp/nexus-tech-beta-review.md",
        evidence_database_path="nexus-tech.db",
        session_database_path="/tmp/nexus-tech-beta-review-session.db",
        owner_rehearsal_database_path="/tmp/nexus-tech-beta-review-rehearsal.db",
    )

    assert not preparation.requires_session
    assert not preparation.owner_rehearsal_required
    assert preparation.target_scenario_id is None
    assert preparation.launch_command == ""
    assert preparation.record_command == ""
    assert "manual release review" in preparation.target_reason


@pytest.mark.parametrize(
    ("viewport", "command_prefix", "database_path", "message"),
    (
        ("wide", "nexus-tech", "nexus-tech.db", "Viewport must use"),
        ("820x620", "nexus-tech; echo unsafe", "nexus-tech.db", "shell control"),
        ("820x620", "'nexus-tech", "nexus-tech.db", "valid shell quoting"),
        ("820x620", "nexus-tech", "bad\npath.db", "single line"),
    ),
)
def test_beta_playtest_preparation_rejects_unsafe_packet_inputs(
    viewport: str,
    command_prefix: str,
    database_path: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        build_beta_playtest_preparation(
            [],
            game_version=__version__,
            interface_mode=BetaPlaytestInterface.TWO_D,
            viewport=viewport,
            motion_mode=MotionMode.FULL,
            command_prefix=command_prefix,
            packet_output_path="/tmp/nexus-tech-beta-session.md",
            evidence_database_path=database_path,
            session_database_path="/tmp/nexus-tech-beta-session.db",
            owner_rehearsal_database_path="/tmp/nexus-tech-beta-rehearsal.db",
        )


def test_beta_playtest_preparation_requires_three_distinct_databases() -> None:
    with pytest.raises(ValueError, match="must be distinct"):
        build_beta_playtest_preparation(
            [],
            game_version=__version__,
            interface_mode=BetaPlaytestInterface.TWO_D,
            viewport="820x620",
            motion_mode=MotionMode.FULL,
            command_prefix="nexus-tech",
            packet_output_path="/tmp/nexus-tech-beta-session.md",
            evidence_database_path="nexus-tech.db",
            session_database_path="nexus-tech.db",
            owner_rehearsal_database_path="/tmp/nexus-tech-beta-rehearsal.db",
        )


@pytest.mark.parametrize(
    "database_path",
    (
        "/tmp/nexus-tech-beta-evidence.db",
        "/tmp/nexus-tech-beta-evidence.db-wal",
        "/tmp/nexus-tech-beta-session.db",
        "/tmp/nexus-tech-beta-session.db-shm",
        "/tmp/nexus-tech-beta-rehearsal.db",
        "/tmp/nexus-tech-beta-rehearsal.db-journal",
    ),
)
def test_beta_playtest_preparation_keeps_packet_outside_database_paths(
    database_path: str,
) -> None:
    with pytest.raises(ValueError, match="Packet output.*database paths must be distinct"):
        build_beta_playtest_preparation(
            [],
            game_version=__version__,
            interface_mode=BetaPlaytestInterface.TWO_D,
            viewport="820x620",
            motion_mode=MotionMode.FULL,
            command_prefix="nexus-tech",
            packet_output_path=database_path,
            evidence_database_path="/tmp/nexus-tech-beta-evidence.db",
            session_database_path="/tmp/nexus-tech-beta-session.db",
            owner_rehearsal_database_path="/tmp/nexus-tech-beta-rehearsal.db",
        )


def test_prepare_beta_playtest_cli_writes_private_local_packet_only(tmp_path: Path) -> None:
    db_path = tmp_path / "beta.db"
    output = tmp_path / "next-session.md"
    session_db_path = tmp_path / "tester-profile.db"
    rehearsal_db_path = tmp_path / "rehearsal-profile.db"
    existing = make_session(1, "founder_journey")
    BetaPlaytestRepository(db_path).save_session(existing)

    result = runner.invoke(
        app,
        [
            "prepare-beta-playtest-session",
            "--viewport",
            "820x620",
            "--motion-mode",
            "reduced",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--output",
            str(output),
            "--db-path",
            str(db_path),
            "--session-db-path",
            str(session_db_path),
            "--rehearsal-db-path",
            str(rehearsal_db_path),
        ],
    )

    assert result.exit_code == 0
    assert "Next Human Beta Session" in result.output
    assert "bootstrap_studio" in result.output
    assert "Preparation only" in result.output
    assert "Owner Rehearsal Gate" not in result.output
    assert "Defect Triage / Stop Conditions" in result.output
    assert all(priority in result.output for priority in ("P0", "P1", "P2"))
    assert "--confirm-human-session" in result.output
    markdown = output.read_text(encoding="utf-8")
    assert "Human-Only Boundary" in markdown
    assert "Owner Rehearsal Gate" not in markdown
    assert "bootstrap_studio" in markdown
    assert "Isolated Profile Boundary" in markdown
    assert "Defect Triage And Stop Conditions" in markdown
    assert "### P0 - Release blocker" in markdown
    assert "### P1 - Usability blocker" in markdown
    assert "### P2 - Polish defect" in markdown
    assert "Record After The Session" in markdown
    assert "Required Packet Preflight" in markdown
    assert "validate-beta-playtest-session-packet" in markdown
    assert f"--input {output}" in markdown
    assert str(session_db_path) in markdown
    assert str(rehearsal_db_path) not in markdown
    assert f"--db-path {db_path}" in markdown
    assert not session_db_path.exists()
    assert not rehearsal_db_path.exists()
    assert existing.notes not in markdown
    assert BetaPlaytestRepository(db_path).list_sessions() == [existing]


def test_beta_playtest_plan_cli_writes_note_free_six_lane_artifact(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "evidence.db"
    output = tmp_path / "execution-plan.md"
    packet_output = tmp_path / "next-session.md"
    existing = make_session(1, "founder_journey")
    BetaPlaytestRepository(db_path).save_session(existing)

    result = runner.invoke(
        app,
        [
            "beta-playtest-plan",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--output",
            str(output),
            "--packet-output",
            str(packet_output),
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 0
    assert "Human Beta Execution Plan" in result.output
    assert "Six-Campaign Queue" in result.output
    assert "Next Operator Action" in result.output
    markdown = output.read_text(encoding="utf-8")
    assert "Six-Campaign Queue" in markdown
    assert "`NEXT SESSION`" in markdown
    assert all(
        f"`{journey.scenario_id}`" in markdown for journey in list_featured_campaign_journeys()
    )
    assert "Never prepare all six tester profiles in advance." in markdown
    assert "prepare-beta-playtest-session" in markdown
    assert "beta-playtest-plan" in markdown
    assert existing.notes not in markdown
    assert not packet_output.exists()


@pytest.mark.parametrize(
    ("option", "database_suffix"),
    (
        ("--output", ""),
        ("--output", "-journal"),
        ("--packet-output", "-shm"),
    ),
)
def test_beta_playtest_plan_cli_preserves_evidence_on_artifact_collision(
    tmp_path: Path,
    option: str,
    database_suffix: str,
) -> None:
    db_path = tmp_path / "evidence.db"
    existing = make_session(1, "founder_journey")
    repository = BetaPlaytestRepository(db_path)
    repository.save_session(existing)
    arguments = [
        "beta-playtest-plan",
        "--output",
        str(tmp_path / "execution-plan.md"),
        "--packet-output",
        str(tmp_path / "next-session.md"),
        "--db-path",
        str(db_path),
    ]
    arguments[arguments.index(option) + 1] = f"{db_path}{database_suffix}"

    result = runner.invoke(app, arguments)

    assert result.exit_code == 1
    assert "must not overwrite the evidence database" in result.output
    assert "SQLite sidecars" in result.output
    assert repository.list_sessions() == [existing]


def test_prepare_beta_playtest_cli_defaults_to_current_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "next-session.md"
    session_db_path = tmp_path / "tester-profile.db"
    rehearsal_db_path = tmp_path / "rehearsal-profile.db"
    monkeypatch.setattr(
        command_prefix_module.sys,
        "argv",
        [".venv313/bin/nexus-tech"],
    )

    result = runner.invoke(
        app,
        [
            "prepare-beta-playtest-session",
            "--output",
            str(output),
            "--db-path",
            str(tmp_path / "beta.db"),
            "--session-db-path",
            str(session_db_path),
            "--rehearsal-db-path",
            str(rehearsal_db_path),
        ],
    )

    assert result.exit_code == 0
    markdown = output.read_text(encoding="utf-8")
    assert "Owner Rehearsal Gate" in result.output
    assert "Visible preparation only" in result.output
    assert "It must never be entered" in result.output
    assert "with record-beta-playtest-session." in result.output
    assert "Owner Rehearsal Gate" in markdown
    assert "must never be entered" in markdown
    assert "Save & Archive" in markdown
    assert "Route Atlas" in markdown
    assert "Review Readiness Guard" in markdown
    assert "--require-review-ready" in markdown
    assert ".venv313/bin/nexus-tech menu-2d" in markdown
    assert f"--db-path {rehearsal_db_path}" in markdown
    assert f"--db-path {session_db_path}" in markdown
    assert "uv run nexus-tech" not in markdown


def test_prepare_beta_playtest_cli_allocates_fresh_default_gameplay_profiles(
    tmp_path: Path,
) -> None:
    output = tmp_path / "next-session.md"
    evidence_db_path = tmp_path / "evidence.db"

    result = runner.invoke(
        app,
        [
            "prepare-beta-playtest-session",
            "--output",
            str(output),
            "--db-path",
            str(evidence_db_path),
        ],
    )

    assert result.exit_code == 0
    lines = output.read_text(encoding="utf-8").splitlines()
    rehearsal_line = next(line for line in lines if line.startswith("- Owner rehearsal profile:"))
    session_line = next(line for line in lines if line.startswith("- Tester gameplay profile:"))
    rehearsal_path = Path(rehearsal_line.split("`")[1])
    session_path = Path(session_line.split("`")[1])
    assert rehearsal_path != session_path
    assert rehearsal_path != evidence_db_path
    assert session_path != evidence_db_path
    assert rehearsal_path.name.startswith("nexus-tech-beta-rehearsal-")
    assert session_path.name.startswith("nexus-tech-beta-session-")
    assert not rehearsal_path.exists()
    assert not session_path.exists()


def test_validate_beta_playtest_packet_accepts_current_isolated_packet(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "evidence.db"
    output = tmp_path / "next-session.md"
    session_db_path = tmp_path / "tester-profile.db"
    rehearsal_db_path = tmp_path / "rehearsal-profile.db"
    prepare_result = runner.invoke(
        app,
        [
            "prepare-beta-playtest-session",
            "--output",
            str(output),
            "--db-path",
            str(db_path),
            "--session-db-path",
            str(session_db_path),
            "--rehearsal-db-path",
            str(rehearsal_db_path),
        ],
    )

    result = runner.invoke(
        app,
        [
            "validate-beta-playtest-session-packet",
            "--input",
            str(output),
            "--db-path",
            str(db_path),
        ],
    )

    assert prepare_result.exit_code == 0
    assert result.exit_code == 0
    assert "Beta Packet Validated" in result.output
    assert "human-sessions-needed" in result.output
    assert "founder_journey" in result.output


@pytest.mark.parametrize("mutation", ("edited", "manifest-removed"))
def test_validate_beta_playtest_packet_rejects_modified_artifact(
    tmp_path: Path,
    mutation: str,
) -> None:
    db_path = tmp_path / "evidence.db"
    output = tmp_path / "next-session.md"
    prepare_result = runner.invoke(
        app,
        [
            "prepare-beta-playtest-session",
            "--output",
            str(output),
            "--db-path",
            str(db_path),
            "--session-db-path",
            str(tmp_path / "tester-profile.db"),
            "--rehearsal-db-path",
            str(tmp_path / "rehearsal-profile.db"),
        ],
    )
    assert prepare_result.exit_code == 0
    markdown = output.read_text(encoding="utf-8")
    if mutation == "edited":
        markdown = markdown.replace(
            "Choose New Game, then Learn / founder_journey.",
            "Choose any campaign.",
        )
    else:
        markdown = "\n".join(
            line
            for line in markdown.splitlines()
            if not line.startswith("<!-- nexus-tech-beta-packet-v3 ")
        )
    output.write_text(markdown, encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "validate-beta-playtest-session-packet",
            "--input",
            str(output),
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 1
    assert "Beta Packet Validation Failed" in result.output
    if mutation == "edited":
        assert "modified after generation" in result.output
    else:
        assert "exactly one valid" in result.output


def test_validate_beta_playtest_packet_rejects_stale_evidence_snapshot(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "evidence.db"
    output = tmp_path / "next-session.md"
    prepare_result = runner.invoke(
        app,
        [
            "prepare-beta-playtest-session",
            "--output",
            str(output),
            "--db-path",
            str(db_path),
            "--session-db-path",
            str(tmp_path / "tester-profile.db"),
            "--rehearsal-db-path",
            str(tmp_path / "rehearsal-profile.db"),
        ],
    )
    assert prepare_result.exit_code == 0
    BetaPlaytestRepository(db_path).save_session(make_session(1, "founder_journey"))

    result = runner.invoke(
        app,
        [
            "validate-beta-playtest-session-packet",
            "--input",
            str(output),
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 1
    assert "evidence snapshot is stale" in result.output


def test_validate_beta_playtest_packet_rejects_mismatched_evidence_store(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "evidence.db"
    output = tmp_path / "next-session.md"
    prepare_result = runner.invoke(
        app,
        [
            "prepare-beta-playtest-session",
            "--output",
            str(output),
            "--db-path",
            str(db_path),
            "--session-db-path",
            str(tmp_path / "tester-profile.db"),
            "--rehearsal-db-path",
            str(tmp_path / "rehearsal-profile.db"),
        ],
    )
    assert prepare_result.exit_code == 0

    result = runner.invoke(
        app,
        [
            "validate-beta-playtest-session-packet",
            "--input",
            str(output),
            "--db-path",
            str(tmp_path / "wrong-evidence.db"),
        ],
    )

    assert result.exit_code == 1
    assert "does not match --db-path" in result.output


def test_validate_beta_playtest_packet_rejects_moved_packet(tmp_path: Path) -> None:
    db_path = tmp_path / "evidence.db"
    output = tmp_path / "next-session.md"
    moved_output = tmp_path / "moved-session.md"
    prepare_result = runner.invoke(
        app,
        [
            "prepare-beta-playtest-session",
            "--output",
            str(output),
            "--db-path",
            str(db_path),
            "--session-db-path",
            str(tmp_path / "tester-profile.db"),
            "--rehearsal-db-path",
            str(tmp_path / "rehearsal-profile.db"),
        ],
    )
    assert prepare_result.exit_code == 0
    moved_output.write_text(output.read_text(encoding="utf-8"), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "validate-beta-playtest-session-packet",
            "--input",
            str(moved_output),
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 1
    assert "Packet path does not match --input" in result.output


def test_validate_beta_playtest_packet_detects_same_status_evidence_correction(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "evidence.db"
    output = tmp_path / "next-session.md"
    repository = BetaPlaytestRepository(db_path)
    session = make_session(1, "founder_journey")
    repository.save_session(session)
    prepare_result = runner.invoke(
        app,
        [
            "prepare-beta-playtest-session",
            "--output",
            str(output),
            "--db-path",
            str(db_path),
            "--session-db-path",
            str(tmp_path / "tester-profile.db"),
            "--rehearsal-db-path",
            str(tmp_path / "rehearsal-profile.db"),
        ],
    )
    assert prepare_result.exit_code == 0
    corrected = BetaPlaytestSession(
        **{
            **session.__dict__,
            "notes": "Corrected observation retains every aggregate beta gate result.",
        }
    )
    repository.save_session(corrected, replace=True)

    result = runner.invoke(
        app,
        [
            "validate-beta-playtest-session-packet",
            "--input",
            str(output),
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 1
    assert "evidence snapshot is stale" in result.output


def test_prepare_and_validate_beta_playtest_retest_packet(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "evidence.db"
    output = tmp_path / "retest-session.md"
    repository = BetaPlaytestRepository(db_path)
    for index, journey in enumerate(list_featured_campaign_journeys(), start=1):
        repository.save_session(
            make_session(
                index,
                journey.scenario_id,
                blocker_found=index == 1,
            )
        )

    prepare_result = runner.invoke(
        app,
        [
            "prepare-beta-playtest-session",
            "--output",
            str(output),
            "--db-path",
            str(db_path),
            "--session-db-path",
            str(tmp_path / "retest-profile.db"),
            "--rehearsal-db-path",
            str(tmp_path / "unused-rehearsal.db"),
        ],
    )
    validation_result = runner.invoke(
        app,
        [
            "validate-beta-playtest-session-packet",
            "--input",
            str(output),
            "--db-path",
            str(db_path),
        ],
    )

    assert prepare_result.exit_code == 0
    assert validation_result.exit_code == 0
    assert "Retest Of" in prepare_result.output
    markdown = output.read_text(encoding="utf-8")
    assert "- Retest of: `beta-001`" in markdown
    assert "--retest-of beta-001" in markdown
    assert "Target: founder_journey" in validation_result.output


def test_validate_beta_playtest_packet_rejects_consumed_gameplay_profile(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "evidence.db"
    output = tmp_path / "next-session.md"
    session_db_path = tmp_path / "tester-profile.db"
    prepare_result = runner.invoke(
        app,
        [
            "prepare-beta-playtest-session",
            "--output",
            str(output),
            "--db-path",
            str(db_path),
            "--session-db-path",
            str(session_db_path),
            "--rehearsal-db-path",
            str(tmp_path / "rehearsal-profile.db"),
        ],
    )
    assert prepare_result.exit_code == 0
    session_db_path.write_text("used profile", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "validate-beta-playtest-session-packet",
            "--input",
            str(output),
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 1
    assert "Tester gameplay profile must not already exist" in result.output


def test_prepare_beta_playtest_cli_hands_review_ready_evidence_to_fail_closed_gate(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "evidence.db"
    output = tmp_path / "manual-review.md"
    repository = BetaPlaytestRepository(db_path)
    for index, journey in enumerate(list_featured_campaign_journeys(), start=1):
        repository.save_session(make_session(index, journey.scenario_id))

    result = runner.invoke(
        app,
        [
            "prepare-beta-playtest-session",
            "--output",
            str(output),
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 0
    assert "Manual Review Gate" in result.output
    assert "--require-review-ready" in result.output
    assert "Launch And Select" not in result.output
    markdown = output.read_text(encoding="utf-8")
    assert "Review Readiness Guard" in markdown
    assert "--require-review-ready" in markdown
    validation_result = runner.invoke(
        app,
        [
            "validate-beta-playtest-session-packet",
            "--input",
            str(output),
            "--db-path",
            str(db_path),
        ],
    )
    assert validation_result.exit_code == 0
    assert "manual release review" in validation_result.output


@pytest.mark.parametrize("artifact_suffix", ("", "-journal", "-wal", "-shm"))
def test_prepare_beta_playtest_cli_rejects_reused_gameplay_profile(
    tmp_path: Path,
    artifact_suffix: str,
) -> None:
    session_profile = tmp_path / "used-profile.db"
    existing_artifact = Path(f"{session_profile}{artifact_suffix}")
    existing_artifact.write_text("already used", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "prepare-beta-playtest-session",
            "--output",
            str(tmp_path / "next-session.md"),
            "--db-path",
            str(tmp_path / "evidence.db"),
            "--session-db-path",
            str(session_profile),
            "--rehearsal-db-path",
            str(tmp_path / "fresh-rehearsal.db"),
        ],
    )

    assert result.exit_code == 1
    assert "Tester gameplay profile must not already exist" in result.output


def test_prepare_beta_playtest_cli_rejects_missing_profile_parent(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "prepare-beta-playtest-session",
            "--output",
            str(tmp_path / "next-session.md"),
            "--db-path",
            str(tmp_path / "evidence.db"),
            "--session-db-path",
            str(tmp_path / "missing" / "tester.db"),
            "--rehearsal-db-path",
            str(tmp_path / "fresh-rehearsal.db"),
        ],
    )

    assert result.exit_code == 1
    assert "Tester gameplay profile parent directory must already exist" in result.output


@pytest.mark.parametrize("output_target", ("evidence", "session", "rehearsal-wal"))
def test_prepare_beta_playtest_cli_rejects_packet_database_collision(
    tmp_path: Path,
    output_target: str,
) -> None:
    evidence_path = tmp_path / "evidence.db"
    session_path = tmp_path / "session.db"
    rehearsal_path = tmp_path / "rehearsal.db"
    outputs = {
        "evidence": evidence_path,
        "session": session_path,
        "rehearsal-wal": Path(f"{rehearsal_path}-wal"),
    }

    result = runner.invoke(
        app,
        [
            "prepare-beta-playtest-session",
            "--output",
            str(outputs[output_target]),
            "--db-path",
            str(evidence_path),
            "--session-db-path",
            str(session_path),
            "--rehearsal-db-path",
            str(rehearsal_path),
        ],
    )

    assert result.exit_code == 1
    assert "Packet output and gameplay/evidence database paths must be distinct" in result.output


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


def test_beta_playtest_status_review_guard_fails_closed_without_human_evidence(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "beta.db"

    result = runner.invoke(
        app,
        [
            "beta-playtest-status",
            "--db-path",
            str(db_path),
            "--require-review-ready",
        ],
    )

    assert result.exit_code == 1
    assert "human-sessions-needed" in result.output
    assert "Record 6 more current-version session(s)." in result.output


def test_beta_playtest_status_review_guard_passes_only_review_ready_evidence(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "beta.db"
    repository = BetaPlaytestRepository(db_path)
    for index, journey in enumerate(list_featured_campaign_journeys(), start=1):
        repository.save_session(make_session(index, journey.scenario_id))

    result = runner.invoke(
        app,
        [
            "beta-playtest-status",
            "--db-path",
            str(db_path),
            "--require-review-ready",
        ],
    )

    assert result.exit_code == 0
    assert "human-evidence-ready-for-review" in result.output
    assert "a human reviewer must still approve release" in result.output


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
