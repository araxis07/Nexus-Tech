"""Rich views for structured human beta playtest evidence."""

from __future__ import annotations

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from nexus_tech.simulation.beta_owner_rehearsal import BetaOwnerRehearsalStatus
from nexus_tech.simulation.beta_playtest import BetaPlaytestStatus
from nexus_tech.simulation.beta_playtest_execution import BetaPlaytestExecutionPlan
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
    if preparation.retest_of_session_key is not None:
        overview.add_row("Retest Of", preparation.retest_of_session_key)
    console.print(
        Panel(
            overview,
            title="Next Human Beta Session",
            subtitle="Preparation only; this command never records evidence",
            border_style="cyan" if preparation.requires_session else "green",
            expand=True,
        )
    )

    console.print(
        Panel(
            Group(
                _folded_command(preparation.validation_command),
                Text(""),
                Text(
                    "Run immediately before opening either gameplay profile. Stop if "
                    "validation fails; regenerate the packet instead of editing or moving it.",
                    overflow="fold",
                    no_wrap=False,
                ),
            ),
            title="Required Packet Preflight",
            border_style="yellow",
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
                        "Use the guarded command below before the first observed session. "
                        "It performs packet preflight, opens the exact visible profile, "
                        "and checks the archive after the window closes.",
                        overflow="fold",
                        no_wrap=False,
                    ),
                    Text("It must never be entered with record-beta-playtest-session."),
                    Text(""),
                    _folded_command(preparation.owner_rehearsal_run_command),
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
                    Text("Manual equivalent:", style="bold"),
                    _folded_command(preparation.owner_rehearsal_launch_command),
                    Text(""),
                    _folded_command(preparation.owner_rehearsal_validation_command),
                    Text(""),
                    Text(
                        "The post-gate verifies the exact scenario and both campaign "
                        "choices. The visible recovery and Route Atlas checks remain the "
                        "owner's manual responsibility in both workflows.",
                        overflow="fold",
                        no_wrap=False,
                    ),
                ),
                title="0B. Required Post-Rehearsal Gate",
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
        *(
            (f"- Retest of: `{preparation.retest_of_session_key}`",)
            if preparation.retest_of_session_key is not None
            else ()
        ),
        "",
        "## Human-Only Boundary",
        "",
        "This packet prepares a session but never records or approves evidence. Only an "
        "observed real-person session may be entered with `--confirm-human-session`. Owner "
        "rehearsals, headless runs, tests, and generated screenshots do not count.",
        "",
        "## Required Packet Preflight",
        "",
        "Run this immediately before opening either gameplay profile. Stop if it fails; "
        "regenerate the packet instead of editing or moving it.",
        "",
        "```bash",
        preparation.validation_command,
        "```",
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
                    "Run this guarded visible workflow once before inviting the first "
                    "tester. It performs packet preflight, opens the exact rehearsal "
                    "profile, and checks the archive after the window closes. The "
                    "rehearsal must never be entered with "
                    "`record-beta-playtest-session`.",
                    "",
                    "```bash",
                    preparation.owner_rehearsal_run_command,
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
                    "### Required Post-Rehearsal Gate",
                    "",
                    "The guarded command above runs these commands in order and supports "
                    "resuming its existing rehearsal profile after an incomplete window "
                    "close. Use this manual equivalent only when diagnosing launch behavior:",
                    "",
                    "```bash",
                    preparation.owner_rehearsal_launch_command,
                    preparation.owner_rehearsal_validation_command,
                    "```",
                    "",
                    "The post-gate verifies an archived route for the exact target "
                    "scenario with both campaign choices. Pause, Back, Menu, Continue, "
                    "Endgame switching, and Route Atlas visibility remain manual "
                    "checklist observations.",
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


def render_beta_owner_rehearsal_status(
    console: Console,
    status: BetaOwnerRehearsalStatus,
) -> None:
    """Render the archive-backed portion of the owner-rehearsal gate."""

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column(overflow="fold")
    summary.add_row("Rehearsal Profile", status.database_path)
    summary.add_row("Target Scenario", status.target_scenario_id)
    summary.add_row("All Archives", str(status.archive_count))
    summary.add_row("Target Archives", str(status.target_archive_count))
    summary.add_row("Complete Target Paths", str(status.full_path_archive_count))
    summary.add_row(
        "Recorded Routes",
        "; ".join(status.target_routes) if status.target_routes else "none",
    )
    console.print(
        Panel(
            Group(summary, Text(""), Text(status.message, overflow="fold", no_wrap=False)),
            title=(
                "Owner Rehearsal Validated" if status.completed else "Owner Rehearsal Incomplete"
            ),
            subtitle="This command never records human-session evidence",
            border_style="green" if status.completed else "red",
            expand=True,
        )
    )


def render_beta_owner_rehearsal_briefing(
    console: Console,
    preparation: BetaPlaytestPreparation,
    *,
    profile_exists: bool,
    saved_scenario_id: str | None,
) -> None:
    """Render the exact visible route before the guarded rehearsal launch."""

    target_scenario_id = preparation.target_scenario_id or ""
    if saved_scenario_id == target_scenario_id:
        launch_mode = "Continue existing save"
        selection_instruction = (
            f"Choose Continue, then finish "
            f"{preparation.target_track_label} / {preparation.target_scenario_id}."
        )
        first_check = (
            "Confirm this is the dedicated rehearsal profile, choose Continue, and "
            "resume the visible route without counting it as human evidence."
        )
    elif saved_scenario_id:
        launch_mode = "New Game required"
        selection_instruction = (
            f"The newest save is {saved_scenario_id}, not {target_scenario_id}. "
            f"Choose New Game, then {preparation.target_track_label} / "
            f"{target_scenario_id}; do not choose Continue."
        )
        first_check = (
            f"Confirm the saved {saved_scenario_id} run does not match the rehearsal "
            f"target {target_scenario_id}, then choose New Game without counting this "
            "rehearsal as human evidence."
        )
    elif profile_exists:
        launch_mode = "Retry existing profile"
        selection_instruction = preparation.selection_instruction
        first_check = (
            "The prior window close created no save or archive. Confirm this is the "
            "dedicated rehearsal profile, then choose New Game; do not count it as "
            "human evidence."
        )
    else:
        launch_mode = "Fresh rehearsal"
        selection_instruction = preparation.selection_instruction
        first_check = preparation.owner_rehearsal_checklist[0]

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column(overflow="fold")
    summary.add_row(
        "Target", f"{preparation.target_track_label} / {preparation.target_scenario_id}"
    )
    summary.add_row("Window", preparation.viewport)
    summary.add_row("Motion", preparation.motion_mode.value)
    summary.add_row("Profile", preparation.owner_rehearsal_database_path)
    summary.add_row("Launch Mode", launch_mode)

    checklist = Table(box=box.SIMPLE, expand=True)
    checklist.add_column("Step", justify="right", style="bold yellow")
    checklist.add_column("Verify")
    for index, item in enumerate(preparation.owner_rehearsal_checklist, start=1):
        checklist.add_row(str(index), first_check if index == 1 else item)

    console.print(
        Panel(
            Group(
                summary,
                Text(""),
                Text(
                    selection_instruction,
                    style="bold",
                    overflow="fold",
                    no_wrap=False,
                ),
                Text(""),
                checklist,
            ),
            title="Owner Rehearsal Ready",
            subtitle="Closing the window triggers the archive gate; no human evidence is written",
            border_style="yellow",
            expand=True,
        )
    )


def render_beta_playtest_execution_plan(
    console: Console,
    plan: BetaPlaytestExecutionPlan,
) -> None:
    """Render the six campaign lanes and exactly one safe next action."""

    overview = Table.grid(padding=(0, 2))
    overview.add_column(style="bold")
    overview.add_column()
    overview.add_row("Game Version", plan.status.game_version)
    overview.add_row("Evidence Status", plan.status.status)
    overview.add_row("Active Sessions", plan.status.session_progress)
    overview.add_row(
        "Campaign Coverage",
        f"{plan.status.covered_campaigns}/{plan.status.required_campaigns}",
    )
    overview.add_row("Superseded Retest Rows", str(plan.status.superseded_sessions))
    overview.add_row(
        "Owner Rehearsal",
        (
            "required once before the first tester; never record it"
            if plan.owner_rehearsal_required
            else "not part of the next evidence action"
        ),
    )
    console.print(
        Panel(
            overview,
            title="Human Beta Execution Plan",
            subtitle="One fresh packet and one real session at a time",
            border_style="green" if plan.status.review_ready else "cyan",
            expand=True,
        )
    )

    lane_table = Table(box=box.SIMPLE_HEAVY, expand=True)
    lane_table.add_column("#", justify="right")
    lane_table.add_column("Track", style="bold cyan")
    lane_table.add_column("Scenario")
    lane_table.add_column("Sessions", justify="right")
    lane_table.add_column("Testers", justify="right")
    lane_table.add_column("State", style="bold")
    for lane in plan.lanes:
        lane_table.add_row(
            str(lane.order),
            lane.track_label,
            lane.scenario_id,
            str(lane.active_sessions),
            str(lane.unique_testers),
            lane.state,
        )
    console.print(Panel(lane_table, title="Six-Campaign Queue", expand=True))

    if plan.target.kind == "review":
        next_command = plan.review_gate_command
        next_copy = plan.target.reason
    else:
        next_command = plan.prepare_command
        next_copy = (
            f"{plan.target.reason} Generate and validate only this packet. "
            "Regenerate the plan after the real session is recorded."
        )
    console.print(
        Panel(
            Group(
                Text(next_copy, overflow="fold", no_wrap=False),
                Text(""),
                _folded_command(next_command),
                Text(""),
                Text(
                    "Do not pre-allocate later tester codes or copy free-form observations "
                    "into this plan.",
                    overflow="fold",
                    no_wrap=False,
                ),
            ),
            title="Next Operator Action",
            border_style="yellow" if not plan.status.review_ready else "green",
            expand=True,
        )
    )


def format_beta_playtest_execution_plan_markdown(
    plan: BetaPlaytestExecutionPlan,
) -> str:
    """Format a note-free six-lane plan that is safe for local handoff."""

    rehearsal = (
        "required once before the first tester; never record it as human evidence"
        if plan.owner_rehearsal_required
        else "not part of the next evidence action"
    )
    lines = [
        "# NEXUS TECH Human Beta Execution Plan",
        "",
        f"- Game version: `{plan.status.game_version}`",
        f"- Evidence status: `{plan.status.status}`",
        f"- Active sessions: `{plan.status.session_progress}`",
        (
            f"- Campaign coverage: "
            f"`{plan.status.covered_campaigns}/{plan.status.required_campaigns}`"
        ),
        f"- Unique active testers: `{plan.status.unique_testers}`",
        f"- Superseded retest rows retained as history: `{plan.status.superseded_sessions}`",
        f"- Owner rehearsal: {rehearsal}",
        "",
        "## Evidence Boundary",
        "",
        "This plan allocates no tester code, records no observation, stores no free-form "
        "note, and cannot approve release. Generate only the next packet, observe one real "
        "first-time tester, record that session with explicit attestation, then regenerate "
        "this plan from the updated local evidence store.",
        "",
        "## Six-Campaign Queue",
        "",
        "| # | Track | Scenario | Active sessions | Testers | State | Follow-up |",
        "|---:|---|---|---:|---:|---|---|",
        *(
            (
                f"| {lane.order} | {lane.track_label} | `{lane.scenario_id}` | "
                f"{lane.active_sessions} | {lane.unique_testers} | `{lane.state}` | "
                f"{lane.follow_up} |"
            )
            for lane in plan.lanes
        ),
        "",
        "## Next Operator Action",
        "",
        plan.target.reason,
        "",
        "```bash",
        (plan.review_gate_command if plan.target.kind == "review" else plan.prepare_command),
        "```",
        "",
        "For a session packet, run its embedded validator immediately before handoff. "
        "Never prepare all six tester profiles in advance.",
        "",
        "## Refresh After Each Real Session",
        "",
        "```bash",
        plan.status_command,
        plan.refresh_plan_command,
        "```",
        "",
        "## Final Fail-Closed Gate",
        "",
        "```bash",
        plan.review_gate_command,
        "```",
        "",
        "A zero exit means ready for manual review, not automatically approved.",
        "",
    ]
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
    overview.add_row("Superseded Retest Rows", str(status.superseded_sessions))

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
        session_table.add_column("Retest Of")
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
                session.retest_of or "-",
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
