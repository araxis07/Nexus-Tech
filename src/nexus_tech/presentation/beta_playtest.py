"""Rich views for structured human beta playtest evidence."""

from __future__ import annotations

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from nexus_tech.simulation.beta_playtest import BetaPlaytestStatus
from nexus_tech.simulation.beta_playtest_preparation import (
    BetaPlaytestPacketManifest,
    BetaPlaytestPreparation,
)


def render_beta_playtest_preparation(
    console: Console,
    preparation: BetaPlaytestPreparation,
) -> None:
    """Render the next human-only session packet without observation notes."""

    overview = Table.grid(padding=(0, 2))
    overview.add_column(style="bold")
    overview.add_column()
    overview.add_row("Game Version", preparation.game_version)
    overview.add_row("Evidence Status", preparation.evidence_status)
    overview.add_row("Session Progress", preparation.session_progress)
    overview.add_row("Target", preparation.target_track_label)
    overview.add_row("Scenario", preparation.target_scenario_id or "manual release review")
    overview.add_row("Reason", preparation.target_reason)
    console.print(
        Panel(
            overview,
            title="Next Human Beta Session",
            subtitle="Preparation only; this command never records evidence",
            border_style="cyan" if preparation.requires_session else "green",
            expand=True,
        )
    )

    if not preparation.requires_session:
        console.print(
            Panel(
                Group(
                    _folded_command(preparation.review_gate_command),
                    Text(""),
                    Text(
                        "A zero exit confirms evidence is ready for review, not that "
                        "release has been approved.",
                        overflow="fold",
                        no_wrap=False,
                    ),
                ),
                title="Manual Review Gate",
                border_style="green",
                expand=True,
            )
        )
        return

    profile_boundary = Table.grid(padding=(0, 2))
    profile_boundary.add_column(style="bold")
    profile_boundary.add_column(overflow="fold")
    if preparation.owner_rehearsal_required:
        profile_boundary.add_row("Rehearsal Profile", preparation.owner_rehearsal_database_path)
    profile_boundary.add_row("Tester Profile", preparation.session_database_path)
    profile_boundary.add_row("Evidence Store", preparation.evidence_database_path)
    console.print(
        Panel(
            Group(
                Text(
                    "Gameplay profiles are fresh and isolated. Never replace their "
                    "--db-path with the evidence store or reuse one for another tester.",
                    overflow="fold",
                    no_wrap=False,
                ),
                Text(""),
                profile_boundary,
            ),
            title="Profile Isolation",
            border_style="cyan",
            expand=True,
        )
    )

    if preparation.owner_rehearsal_required:
        rehearsal = Table(box=box.SIMPLE, expand=True)
        rehearsal.add_column("Step", justify="right", style="bold yellow")
        rehearsal.add_column("Verify")
        for index, item in enumerate(preparation.owner_rehearsal_checklist, start=1):
            rehearsal.add_row(str(index), item)
        console.print(
            Panel(
                Group(
                    Text(
                        "Run this once before the first observed session. It must never "
                        "be entered with record-beta-playtest-session.",
                        overflow="fold",
                        no_wrap=False,
                    ),
                    Text(""),
                    _folded_command(preparation.owner_rehearsal_launch_command),
                    Text(""),
                    rehearsal,
                ),
                title="0. Owner Rehearsal Gate",
                subtitle="Visible preparation only; human evidence remains unchanged",
                border_style="yellow",
                expand=True,
            )
        )

    console.print(
        Panel(
            Group(
                _folded_command(preparation.launch_command),
                Text(""),
                Text(preparation.selection_instruction),
            ),
            title="1. Launch And Select",
            border_style="cyan",
            expand=True,
        )
    )
    checklist = Table(box=box.SIMPLE, expand=True)
    checklist.add_column("Step", justify="right", style="bold cyan")
    checklist.add_column("Observe")
    for index, item in enumerate(preparation.checklist, start=1):
        checklist.add_row(str(index), item)
    console.print(Panel(checklist, title="2. Human Observation Checklist", expand=True))

    triage = Table(box=box.SIMPLE, expand=True)
    triage.add_column("Priority", justify="center", style="bold")
    triage.add_column("Classify", overflow="fold")
    triage.add_column("Operator Response", overflow="fold")
    priority_styles = {"P0": "bold red", "P1": "bold yellow", "P2": "bold cyan"}
    for rule in preparation.triage_rules:
        triage.add_row(
            Text(rule.priority, style=priority_styles[rule.priority]),
            f"{rule.label}: {rule.trigger}",
            rule.response,
        )
    console.print(
        Panel(
            triage,
            title="3. Defect Triage / Stop Conditions",
            subtitle="Classify only what was actually observed",
            border_style="yellow",
            expand=True,
        )
    )
    console.print(
        Panel(
            Group(
                Text("Template only. Replace every ALL_CAPS value after the observed session."),
                Text(""),
                _folded_command(preparation.record_command),
            ),
            title="4. Record After Session",
            border_style="yellow",
            expand=True,
        )
    )
    console.print(
        Panel(
            Group(
                _folded_command(preparation.status_command),
                _folded_command(preparation.archive_command),
            ),
            title="5. Refresh Evidence",
            border_style="cyan",
            expand=True,
        )
    )
    console.print(
        Panel(
            Group(
                _folded_command(preparation.review_gate_command),
                Text(""),
                Text(
                    "This command exits non-zero until all current-version human "
                    "criteria are ready. Reviewer approval remains manual.",
                    overflow="fold",
                    no_wrap=False,
                ),
            ),
            title="6. Review Readiness Guard",
            border_style="yellow",
            expand=True,
        )
    )


def format_beta_playtest_preparation_markdown(
    preparation: BetaPlaytestPreparation,
) -> str:
    """Format a local handoff packet that contains no recorded free-form notes."""

    lines = [
        "# NEXUS TECH Human Beta Session Packet",
        "",
        BetaPlaytestPacketManifest.from_preparation(preparation).encode(),
        "",
        f"- Game version: `{preparation.game_version}`",
        f"- Evidence status: `{preparation.evidence_status}`",
        f"- Session progress: `{preparation.session_progress}`",
        f"- Target track: `{preparation.target_track_label}`",
        (
            f"- Target scenario: `{preparation.target_scenario_id}`"
            if preparation.target_scenario_id is not None
            else "- Target scenario: `manual release review`"
        ),
        f"- Reason: {preparation.target_reason}",
        "",
        "## Human-Only Boundary",
        "",
        "This packet prepares a session but never records or approves evidence. Only an "
        "observed real-person session may be entered with `--confirm-human-session`. Owner "
        "rehearsals, headless runs, tests, and generated screenshots do not count.",
        "",
    ]
    if preparation.requires_session:
        lines.extend(
            (
                "## Isolated Profile Boundary",
                "",
                (
                    "Owner rehearsal and tester gameplay use separate fresh SQLite profiles. "
                    if preparation.owner_rehearsal_required
                    else "Tester gameplay uses a fresh SQLite profile. "
                )
                + "The recorder and status commands use the persistent evidence store. Never "
                "replace a launch `--db-path` with the evidence store or reuse a gameplay "
                "profile for another tester.",
                "",
                *(
                    (f"- Owner rehearsal profile: `{preparation.owner_rehearsal_database_path}`",)
                    if preparation.owner_rehearsal_required
                    else ()
                ),
                f"- Tester gameplay profile: `{preparation.session_database_path}`",
                f"- Structured evidence store: `{preparation.evidence_database_path}`",
                "",
            )
        )
        if preparation.owner_rehearsal_required:
            lines.extend(
                (
                    "## Owner Rehearsal Gate",
                    "",
                    "Run this visible route once before inviting the first tester. The "
                    "rehearsal must never be entered with "
                    "`record-beta-playtest-session`.",
                    "",
                    "```bash",
                    preparation.owner_rehearsal_launch_command,
                    "```",
                    "",
                    *(
                        f"{index}. {item}"
                        for index, item in enumerate(
                            preparation.owner_rehearsal_checklist,
                            1,
                        )
                    ),
                    "",
                )
            )
        lines.extend(
            (
                "## Launch",
                "",
                "```bash",
                preparation.launch_command,
                "```",
                "",
                preparation.selection_instruction,
                "",
                "## Observation Checklist",
                "",
                *(f"{index}. {item}" for index, item in enumerate(preparation.checklist, 1)),
                "",
                "## Defect Triage And Stop Conditions",
                "",
                "Classify only what was actually observed before completing the recorder.",
                "",
                *(
                    line
                    for rule in preparation.triage_rules
                    for line in (
                        f"### {rule.priority} - {rule.label}",
                        "",
                        f"- Trigger: {rule.trigger}",
                        f"- Response: {rule.response}",
                        "",
                    )
                ),
                "## Record After The Session",
                "",
                "Replace every ALL_CAPS value. The unchanged template must fail validation.",
                "",
                "```bash",
                preparation.record_command,
                "```",
                "",
            )
        )
    lines.extend(
        (
            "## Refresh Evidence",
            "",
            "```bash",
            preparation.status_command,
            preparation.archive_command,
            "```",
            "",
            "## Review Readiness Guard",
            "",
            "```bash",
            preparation.review_gate_command,
            "```",
            "",
            "This command exits non-zero until every current-version human criterion "
            "is ready. A zero exit still requires an explicit reviewer release decision.",
            "",
        )
    )
    return "\n".join(lines)


def render_beta_playtest_status(console: Console, status: BetaPlaytestStatus) -> None:
    """Render human-session coverage without exposing free-form observation notes."""

    overview = Table.grid(padding=(0, 2))
    overview.add_column(style="bold")
    overview.add_column()
    overview.add_row("Status", status.status)
    overview.add_row("Game Version", status.game_version)
    overview.add_row("Sessions", status.session_progress)
    overview.add_row("Unique Testers", str(status.unique_testers))
    overview.add_row(
        "Campaign Coverage",
        f"{status.covered_campaigns}/{status.required_campaigns}",
    )
    overview.add_row(
        "Average First Turn",
        f"{status.average_first_turn_seconds}s" if status.session_count else "no evidence",
    )
    overview.add_row("Turn 1 Unaided", status.rate_label(status.unaided_turn_one))
    overview.add_row("Pause / Back", status.rate_label(status.pause_back_successes))
    overview.add_row("Trade-off Recall", status.rate_label(status.tradeoff_explanations))
    overview.add_row("Reached Act 3", status.rate_label(status.act_three_reaches))
    overview.add_row("Blocker Sessions", str(status.blocker_sessions))
    overview.add_row("Stale-Version Rows", str(status.stale_sessions))
    overview.add_row("Ignored Campaign Rows", str(status.ignored_sessions))

    border_style = "green" if status.review_ready else "yellow"
    if status.session_count >= status.required_sessions and status.gate_failures:
        border_style = "red"
    console.print(
        Panel(
            overview,
            title="Human Beta Evidence",
            subtitle="Local structured observations; manual release decision required",
            border_style=border_style,
            expand=True,
        )
    )

    campaign_table = Table(box=box.SIMPLE_HEAVY, expand=True)
    campaign_table.add_column("Track", style="bold cyan")
    campaign_table.add_column("Scenario")
    campaign_table.add_column("Sessions", justify="right")
    campaign_table.add_column("Testers", justify="right")
    campaign_table.add_column("Coverage")
    for lane in status.lanes:
        campaign_table.add_row(
            lane.track_label,
            lane.scenario_id,
            str(lane.sessions),
            str(lane.unique_testers),
            lane.status,
        )
    console.print(Panel(campaign_table, title="Six-Campaign Session Coverage", expand=True))

    if status.sessions:
        session_table = Table(box=box.SIMPLE, expand=True)
        session_table.add_column("Session")
        session_table.add_column("Tester Code")
        session_table.add_column("Campaign")
        session_table.add_column("Mode / Viewport")
        session_table.add_column("Turn 1", justify="right")
        session_table.add_column("U/P/T/A/B", justify="center")
        for session in status.sessions:
            result_marks = "".join(
                (
                    _mark(session.turn_one_unaided),
                    _mark(session.pause_back_success),
                    _mark(session.tradeoff_explained),
                    _mark(session.reached_act_three),
                    _mark(not session.blocker_found),
                )
            )
            session_table.add_row(
                session.session_key,
                session.tester_code,
                session.scenario_id,
                f"{session.interface_mode.value} / {session.viewport}",
                f"{session.first_turn_seconds}s",
                result_marks,
            )
        console.print(
            Panel(
                session_table,
                title="Current-Version Sessions",
                subtitle="U unaided | P pause/back | T trade-off | A Act 3 | B blocker-free",
                expand=True,
            )
        )

    failures = "\n".join(f"- {failure}" for failure in status.gate_failures)
    if not failures:
        failures = "Automated criteria are met; a human reviewer must still approve release."
    console.print(
        Panel(
            f"{failures}\n\nNext: {status.next_action}",
            title="Gate Review",
            border_style=border_style,
            expand=True,
        )
    )


def _mark(passed: bool) -> str:
    return "Y" if passed else "N"


def _folded_command(command: str) -> Text:
    return Text(command, overflow="fold", no_wrap=False)
