"""Fail-closed validation for generated human beta session packets."""

from __future__ import annotations

from pathlib import Path

from nexus_tech.persistence.beta_playtest_repository import BetaPlaytestSession
from nexus_tech.presentation.beta_playtest import (
    format_beta_playtest_preparation_markdown,
)
from nexus_tech.simulation.beta_playtest_preparation import (
    BetaPlaytestPacketManifest,
    BetaPlaytestPreparation,
    build_beta_playtest_preparation,
    decode_beta_playtest_packet_manifest,
)


def validate_beta_playtest_session_packet(
    markdown: str,
    sessions: list[BetaPlaytestSession],
    *,
    game_version: str,
    evidence_database_path: str,
) -> BetaPlaytestPreparation:
    """Return the current packet plan or reject stale and modified artifacts."""

    manifest = decode_beta_playtest_packet_manifest(markdown)
    if manifest.game_version != game_version:
        raise ValueError("Packet game version does not match this build; regenerate the packet.")
    if _normalized_database_path(manifest.evidence_database_path) != _normalized_database_path(
        evidence_database_path
    ):
        raise ValueError(
            "Packet evidence database does not match --db-path; use the intended "
            "evidence store or regenerate the packet."
        )

    current_preparation = build_beta_playtest_preparation(
        sessions,
        game_version=game_version,
        interface_mode=manifest.interface_mode,
        viewport=manifest.viewport,
        motion_mode=manifest.motion_mode,
        command_prefix=manifest.command_prefix,
        evidence_database_path=manifest.evidence_database_path,
        session_database_path=manifest.session_database_path,
        owner_rehearsal_database_path=manifest.owner_rehearsal_database_path,
    )
    current_manifest = BetaPlaytestPacketManifest.from_preparation(current_preparation)
    if current_manifest != manifest:
        raise ValueError(
            "Packet evidence snapshot is stale; regenerate it from the current evidence store."
        )

    expected_markdown = format_beta_playtest_preparation_markdown(current_preparation)
    if markdown != expected_markdown:
        raise ValueError(
            "Packet content was modified after generation; regenerate it instead of editing it."
        )
    return current_preparation


def _normalized_database_path(database_path: str) -> Path:
    return Path(database_path.strip()).expanduser().resolve(strict=False)
