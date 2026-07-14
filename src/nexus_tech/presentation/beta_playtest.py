"""Rich views for structured human beta playtest evidence."""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from nexus_tech.simulation.beta_playtest import BetaPlaytestStatus


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
