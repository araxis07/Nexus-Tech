from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from typer.testing import CliRunner

from nexus_tech.cli import app
from nexus_tech.domain.models import EventCategory, EventHistoryEntry
from nexus_tech.persistence.beta_playtest_repository import BetaPlaytestRepository
from nexus_tech.persistence.save_coordinator import RunArchiveSummary, SaveLoadCoordinator
from nexus_tech.simulation.beta_owner_rehearsal import (
    build_beta_owner_rehearsal_status,
)
from nexus_tech.simulation.engine import create_new_game
from nexus_tech.simulation.randomness import RandomSource

runner = CliRunner()


def _archive(
    scenario_id: str,
    *,
    commitment: str = "",
    consequence: str = "",
) -> RunArchiveSummary:
    return RunArchiveSummary(
        archive_key=f"archive-{scenario_id}-{commitment}-{consequence}",
        slot_name="owner-rehearsal",
        company_name="NEXUS TECH",
        scenario_title=scenario_id,
        completed_turn=12,
        victory_achieved=True,
        game_over=False,
        exit_outcome="none",
        total_score=500,
        score_tier="stable",
        campaign_grade="B",
        estimated_valuation=Decimal("1000000"),
        achievement_badges=(),
        strategic_outlook="profitable_independence",
        offer_value=Decimal("0"),
        final_cash=Decimal("250000"),
        final_reputation=60,
        archived_at="2026-07-29T00:00:00+00:00",
        scenario_id=scenario_id,
        campaign_commitment_choice=commitment,
        campaign_consequence_choice=consequence,
    )


def _prepare_first_packet(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    evidence_path = tmp_path / "evidence.db"
    packet_path = tmp_path / "session.md"
    tester_path = tmp_path / "tester.db"
    rehearsal_path = tmp_path / "rehearsal.db"
    result = runner.invoke(
        app,
        [
            "prepare-beta-playtest-session",
            "--command-prefix",
            "nexus-tech",
            "--output",
            str(packet_path),
            "--db-path",
            str(evidence_path),
            "--session-db-path",
            str(tester_path),
            "--rehearsal-db-path",
            str(rehearsal_path),
        ],
    )
    assert result.exit_code == 0
    return evidence_path, packet_path, tester_path, rehearsal_path


def _persist_completed_founder_archive(path: Path) -> None:
    state = create_new_game(
        "NEXUS TECH",
        "Nexus One",
        scenario_id="founder_journey",
    )
    state.company.current_turn = 12
    state.event_history.extend(
        (
            EventHistoryEntry(
                event_id="campaign_founder_commitment",
                category=EventCategory.MARKET_OPPORTUNITY,
                title="Campaign Decision",
                triggered_turn=4,
                resolved_turn=4,
                chain_id="campaign:founder_journey",
                chain_stage=1,
                selected_option_id="sharpen_focus",
                selected_option_label="Sharpen the Flagship",
                result_text="The owner rehearsal recorded its commitment.",
            ),
            EventHistoryEntry(
                event_id="campaign_founder_consequence",
                category=EventCategory.MARKET_OPPORTUNITY,
                title="Campaign Decision",
                triggered_turn=9,
                resolved_turn=9,
                chain_id="campaign:founder_journey",
                chain_stage=2,
                selected_option_id="defend_control",
                selected_option_label="Defend Control",
                result_text="The owner rehearsal recorded its consequence.",
            ),
        )
    )
    state.victory_achieved = True
    state.victory_reason = "The owner rehearsal completed the target route."
    SaveLoadCoordinator(path).save_game(
        "owner-rehearsal",
        state,
        RandomSource(seed=3221),
    )


def test_owner_rehearsal_status_fails_closed_without_profile() -> None:
    status = build_beta_owner_rehearsal_status(
        [],
        database_path="/tmp/missing-rehearsal.db",
        database_exists=False,
        target_scenario_id="founder_journey",
    )

    assert not status.completed
    assert status.archive_count == 0
    assert "does not exist" in status.message


def test_owner_rehearsal_status_requires_exact_full_target_route() -> None:
    status = build_beta_owner_rehearsal_status(
        [
            _archive(
                "bootstrap_studio",
                commitment="Bootstrap Deliberately",
                consequence="Protect The Core",
            ),
            _archive("founder_journey", commitment="Sharpen the Flagship"),
        ],
        database_path="/tmp/rehearsal.db",
        database_exists=True,
        target_scenario_id="founder_journey",
    )

    assert not status.completed
    assert status.archive_count == 2
    assert status.target_archive_count == 1
    assert status.full_path_archive_count == 0
    assert "missing Commitment or Consequence" in status.message


def test_owner_rehearsal_status_accepts_complete_target_route() -> None:
    status = build_beta_owner_rehearsal_status(
        [
            _archive(
                "founder_journey",
                commitment="Sharpen the Flagship",
                consequence="Defend Control",
            )
        ],
        database_path="/tmp/rehearsal.db",
        database_exists=True,
        target_scenario_id="founder_journey",
    )

    assert status.completed
    assert status.full_path_archive_count == 1
    assert status.target_routes == ("Sharpen the Flagship > Defend Control",)
    assert "manual responsibility" not in status.message
    assert "owner must still confirm" in status.message


def test_owner_rehearsal_cli_fails_closed_before_archive_without_recording_evidence(
    tmp_path: Path,
) -> None:
    evidence_path, packet_path, _, _ = _prepare_first_packet(tmp_path)

    result = runner.invoke(
        app,
        [
            "validate-beta-owner-rehearsal",
            "--input",
            str(packet_path),
            "--db-path",
            str(evidence_path),
        ],
    )

    assert result.exit_code == 1
    assert "Owner Rehearsal Incomplete" in result.output
    assert "profile does not exist" in result.output
    assert BetaPlaytestRepository(evidence_path).list_sessions() == []


def test_owner_rehearsal_cli_accepts_archived_target_and_preserves_tester_profile(
    tmp_path: Path,
) -> None:
    evidence_path, packet_path, tester_path, rehearsal_path = _prepare_first_packet(tmp_path)
    _persist_completed_founder_archive(rehearsal_path)

    result = runner.invoke(
        app,
        [
            "validate-beta-owner-rehearsal",
            "--input",
            str(packet_path),
            "--db-path",
            str(evidence_path),
        ],
    )

    assert result.exit_code == 0
    assert "Owner Rehearsal Validated" in result.output
    assert "Complete Target Paths" in result.output
    assert "Sharpen the Flagship > Defend Control" in result.output
    assert not tester_path.exists()
    assert BetaPlaytestRepository(evidence_path).list_sessions() == []


def test_owner_rehearsal_cli_rejects_consumed_tester_profile(
    tmp_path: Path,
) -> None:
    evidence_path, packet_path, tester_path, rehearsal_path = _prepare_first_packet(tmp_path)
    _persist_completed_founder_archive(rehearsal_path)
    tester_path.write_text("already consumed", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "validate-beta-owner-rehearsal",
            "--input",
            str(packet_path),
            "--db-path",
            str(evidence_path),
        ],
    )

    assert result.exit_code == 1
    assert "Owner Rehearsal Validation Failed" in result.output
    assert "Tester gameplay profile must not already exist" in result.output
