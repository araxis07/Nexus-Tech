"""Readiness evaluation for structured, real-human beta playtest sessions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import ceil

from nexus_tech.persistence.beta_playtest_repository import (
    BetaPlaytestSession,
    is_substantive_beta_playtest_note,
)
from nexus_tech.simulation.campaign_journey import list_featured_campaign_journeys


class BetaObservationResult(StrEnum):
    """Explicit result accepted by beta evidence recording commands."""

    PASS = "pass"
    FAIL = "fail"


class BetaBlockerResult(StrEnum):
    """Explicit blocker result accepted by beta evidence recording commands."""

    NONE = "none"
    FOUND = "found"


@dataclass(frozen=True)
class BetaPlaytestCampaignLane:
    """Current-version human-session coverage for one featured campaign."""

    scenario_id: str
    track_label: str
    sessions: int
    unique_testers: int

    @property
    def covered(self) -> bool:
        return self.sessions > 0

    @property
    def status(self) -> str:
        return "covered" if self.covered else "needed"


@dataclass(frozen=True)
class BetaPlaytestTarget:
    """One next human-only action selected from the active evidence snapshot."""

    kind: str
    lane: BetaPlaytestCampaignLane | None
    reason: str
    retest_of: BetaPlaytestSession | None = None


@dataclass(frozen=True)
class BetaPlaytestStatus:
    """Release-facing summary that keeps automation separate from human evidence."""

    game_version: str
    sessions: tuple[BetaPlaytestSession, ...]
    lanes: tuple[BetaPlaytestCampaignLane, ...]
    stale_sessions: int
    ignored_sessions: int
    superseded_sessions: int
    required_sessions: int
    required_campaigns: int
    unique_testers: int
    unaided_turn_one: int
    pause_back_successes: int
    tradeoff_explanations: int
    act_three_reaches: int
    blocker_sessions: int
    invalid_note_sessions: int
    average_first_turn_seconds: int

    @property
    def session_count(self) -> int:
        return len(self.sessions)

    @property
    def covered_campaigns(self) -> int:
        return sum(lane.covered for lane in self.lanes)

    @property
    def required_eighty_percent(self) -> int:
        return ceil(self.session_count * 0.8)

    @property
    def review_ready(self) -> bool:
        return not self.gate_failures

    @property
    def status(self) -> str:
        if self.session_count < self.required_sessions or self.covered_campaigns < len(self.lanes):
            return "human-sessions-needed"
        if self.gate_failures:
            return "human-gate-failed"
        return "human-evidence-ready-for-review"

    @property
    def gate_failures(self) -> tuple[str, ...]:
        failures: list[str] = []
        if self.session_count < self.required_sessions:
            missing_sessions = self.required_sessions - self.session_count
            failures.append(f"Record {missing_sessions} more current-version session(s).")
        if self.unique_testers < self.required_sessions:
            failures.append(
                f"Use {self.required_sessions - self.unique_testers} more anonymous tester code(s)."
            )
        if self.covered_campaigns < self.required_campaigns:
            missing_campaigns = self.required_campaigns - self.covered_campaigns
            failures.append(f"Cover {missing_campaigns} more featured campaign(s).")
        required_successes = self.required_eighty_percent
        if self.unaided_turn_one < required_successes:
            failures.append("At least 80% must complete turn one without operator help.")
        if self.pause_back_successes < self.session_count:
            failures.append("Every current session must pass Pause, Back, and Menu recovery.")
        if self.tradeoff_explanations < required_successes:
            failures.append("At least 80% must explain both campaign trade-offs.")
        if self.act_three_reaches < required_successes:
            failures.append("At least 80% must reach Act 3 without pacing blocking progress.")
        if self.blocker_sessions:
            failures.append("Resolve and re-test every blocker-level readability or control issue.")
        if self.invalid_note_sessions:
            failures.append("Replace placeholder evidence with concrete real-session observations.")
        return tuple(failures)

    @property
    def next_action(self) -> str:
        target = select_beta_playtest_target(self)
        if target.kind == "review":
            return "Review the recorded evidence and make the manual beta release decision."
        if target.kind == "coverage" and target.lane is not None:
            return (
                f"Run a first-time session for {target.lane.track_label} / "
                f"{target.lane.scenario_id}."
            )
        if target.kind == "retest" and target.lane is not None and target.retest_of is not None:
            return (
                f"Fix and re-test {target.lane.track_label} / {target.lane.scenario_id}, "
                f"superseding {target.retest_of.session_key} with a new first-time tester."
            )
        return "Record another independent first-time current-version session."

    @property
    def session_progress(self) -> str:
        return f"{self.session_count}/{self.required_sessions} current-version sessions"

    def rate_label(self, successes: int) -> str:
        if not self.session_count:
            return "0/0 (0%)"
        percent = round(successes * 100 / self.session_count)
        return f"{successes}/{self.session_count} ({percent}%)"


def build_beta_playtest_status(
    sessions: list[BetaPlaytestSession],
    *,
    game_version: str,
) -> BetaPlaytestStatus:
    """Evaluate only evidence recorded against the current release version."""

    featured_journeys = list_featured_campaign_journeys()
    featured_ids = {journey.scenario_id for journey in featured_journeys}
    current_evidence = tuple(
        session
        for session in sessions
        if session.game_version == game_version and session.scenario_id in featured_ids
    )
    superseded_keys = {
        session.retest_of for session in current_evidence if session.retest_of is not None
    }
    current_sessions = tuple(
        session for session in current_evidence if session.session_key not in superseded_keys
    )
    lanes = tuple(
        BetaPlaytestCampaignLane(
            scenario_id=journey.scenario_id,
            track_label=journey.track_label,
            sessions=sum(
                session.scenario_id == journey.scenario_id for session in current_sessions
            ),
            unique_testers=len(
                {
                    session.tester_code
                    for session in current_sessions
                    if session.scenario_id == journey.scenario_id
                }
            ),
        )
        for journey in featured_journeys
    )
    session_count = len(current_sessions)
    return BetaPlaytestStatus(
        game_version=game_version,
        sessions=current_sessions,
        lanes=lanes,
        stale_sessions=sum(session.game_version != game_version for session in sessions),
        ignored_sessions=sum(session.scenario_id not in featured_ids for session in sessions),
        superseded_sessions=len(current_evidence) - len(current_sessions),
        required_sessions=6,
        required_campaigns=len(featured_journeys),
        unique_testers=len({session.tester_code for session in current_sessions}),
        unaided_turn_one=sum(session.turn_one_unaided for session in current_sessions),
        pause_back_successes=sum(session.pause_back_success for session in current_sessions),
        tradeoff_explanations=sum(session.tradeoff_explained for session in current_sessions),
        act_three_reaches=sum(session.reached_act_three for session in current_sessions),
        blocker_sessions=sum(session.blocker_found for session in current_sessions),
        invalid_note_sessions=sum(
            not is_substantive_beta_playtest_note(session.notes) for session in current_sessions
        ),
        average_first_turn_seconds=(
            sum(session.first_turn_seconds for session in current_sessions) // session_count
            if session_count
            else 0
        ),
    )


def beta_playtest_session_needs_retest(session: BetaPlaytestSession) -> bool:
    """Return whether an active human observation still blocks its campaign lane."""

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


def select_beta_playtest_target(status: BetaPlaytestStatus) -> BetaPlaytestTarget:
    """Select one next lane without allocating evidence or tester identities."""

    if status.review_ready:
        return BetaPlaytestTarget(
            kind="review",
            lane=None,
            reason="Automated human-evidence criteria are ready for manual release review.",
        )

    missing_lane = next((lane for lane in status.lanes if not lane.covered), None)
    if missing_lane is not None:
        return BetaPlaytestTarget(
            kind="coverage",
            lane=missing_lane,
            reason="Cover the next featured campaign missing current-version evidence.",
        )

    failed_session = next(
        (session for session in status.sessions if beta_playtest_session_needs_retest(session)),
        None,
    )
    if failed_session is not None:
        lane = next(lane for lane in status.lanes if lane.scenario_id == failed_session.scenario_id)
        return BetaPlaytestTarget(
            kind="retest",
            lane=lane,
            reason="Re-test the first campaign with an unresolved human gate.",
            retest_of=failed_session,
        )

    return BetaPlaytestTarget(
        kind="additional",
        lane=min(status.lanes, key=lambda lane: (lane.sessions, lane.scenario_id)),
        reason="Add an independent tester to close the remaining aggregate human gate.",
    )
