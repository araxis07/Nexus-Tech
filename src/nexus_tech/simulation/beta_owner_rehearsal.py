"""Fail-closed completion status for the visible owner rehearsal."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.persistence.save_coordinator import RunArchiveSummary


@dataclass(frozen=True)
class BetaOwnerRehearsalStatus:
    """Machine-verifiable portion of the owner-rehearsal gate."""

    database_path: str
    database_exists: bool
    target_scenario_id: str
    archive_count: int
    target_archive_count: int
    full_path_archive_count: int
    target_routes: tuple[str, ...]
    completed: bool
    message: str


def build_beta_owner_rehearsal_status(
    archives: list[RunArchiveSummary],
    *,
    database_path: str,
    database_exists: bool,
    target_scenario_id: str,
) -> BetaOwnerRehearsalStatus:
    """Require one archived two-choice route for the packet's exact scenario."""

    if not target_scenario_id.strip():
        raise ValueError("Owner rehearsal requires a target scenario.")

    target_archives = [archive for archive in archives if archive.scenario_id == target_scenario_id]
    full_path_archives = [archive for archive in target_archives if len(archive.campaign_path) == 2]
    target_routes = tuple(
        " > ".join(archive.campaign_path) if archive.campaign_path else "incomplete path"
        for archive in target_archives
    )

    if not database_exists:
        message = (
            "The rehearsal profile does not exist. Launch the owner rehearsal from the "
            "packet and complete Save & Archive before running this gate again."
        )
    elif not archives:
        message = (
            "The rehearsal profile has no completed-run archive. Finish the visible run "
            "and use Save & Archive before tester handoff."
        )
    elif not target_archives:
        message = (
            f"The rehearsal profile has no archive for {target_scenario_id}. Replay the "
            "packet's exact target campaign in this isolated profile."
        )
    elif not full_path_archives:
        message = (
            "The target archive is missing Commitment or Consequence. Complete both "
            "campaign choices, finish the run, and use Save & Archive again."
        )
    else:
        message = (
            "The target scenario has a completed two-choice archive. The owner must still "
            "confirm Pause, Back, Menu, Continue, Endgame switching, and Route Atlas "
            "visibility from the packet checklist."
        )

    return BetaOwnerRehearsalStatus(
        database_path=database_path,
        database_exists=database_exists,
        target_scenario_id=target_scenario_id,
        archive_count=len(archives),
        target_archive_count=len(target_archives),
        full_path_archive_count=len(full_path_archives),
        target_routes=target_routes,
        completed=bool(full_path_archives),
        message=message,
    )
