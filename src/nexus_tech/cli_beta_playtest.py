"""CLI registration for structured, local human beta evidence."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from nexus_tech import __version__
from nexus_tech.cli_command_prefix import resolve_cli_command_prefix
from nexus_tech.config import DEFAULT_DATABASE_PATH
from nexus_tech.persistence.beta_playtest_repository import (
    BetaPlaytestInterface,
    BetaPlaytestRepository,
    BetaPlaytestSession,
)
from nexus_tech.persistence.errors import PersistenceError
from nexus_tech.presentation.beta_playtest import (
    format_beta_playtest_preparation_markdown,
    render_beta_playtest_preparation,
    render_beta_playtest_status,
)
from nexus_tech.simulation.beta_playtest import (
    BetaBlockerResult,
    BetaObservationResult,
    build_beta_playtest_status,
)
from nexus_tech.simulation.beta_playtest_preparation import (
    build_beta_playtest_preparation,
)
from nexus_tech.simulation.campaign_journey import list_featured_campaign_journeys
from nexus_tech.user_preferences import MotionMode

BETA_INTERFACE_OPTION = typer.Option(
    ...,
    "--interface",
    help="Observed interface: terminal or 2d.",
)
BETA_TURN_ONE_OPTION = typer.Option(
    ...,
    "--turn-one",
    help="Whether turn one was completed without operator help.",
)
BETA_PAUSE_BACK_OPTION = typer.Option(
    ...,
    "--pause-back",
    help="Whether Pause, Back, and return-to-menu recovery all worked.",
)
BETA_TRADEOFF_OPTION = typer.Option(
    ...,
    "--tradeoff",
    help="Whether the tester could explain both campaign trade-offs.",
)
BETA_ACT_THREE_OPTION = typer.Option(
    ...,
    "--act-three",
    help="Whether the tester reached Act 3 without a pacing blocker.",
)
BETA_BLOCKER_OPTION = typer.Option(
    ...,
    "--blocker",
    help="Whether a blocker-level readability or control issue was observed.",
)
BETA_DB_PATH_OPTION = typer.Option(
    DEFAULT_DATABASE_PATH,
    "--db-path",
    help="Local ignored SQLite database used for structured beta evidence.",
)
BETA_PREPARATION_INTERFACE_OPTION = typer.Option(
    BetaPlaytestInterface.TWO_D,
    "--interface",
    help="Interface prepared for the next observed session: terminal or 2d.",
)
BETA_PREPARATION_OUTPUT_OPTION = typer.Option(
    Path("/tmp/nexus-tech-beta-playtest-next.md"),
    "--output",
    help="Local Markdown path for the next-session packet.",
)
BETA_PREPARATION_VIEWPORT_OPTION = typer.Option(
    "820x620",
    "--viewport",
    help="Observed terminal/window size as WIDTHxHEIGHT.",
)
BETA_PREPARATION_MOTION_OPTION = typer.Option(
    MotionMode.FULL,
    "--motion-mode",
    help="2D motion mode embedded in the launch command.",
)
BETA_COMMAND_PREFIX_OPTION = typer.Option(
    None,
    "--command-prefix",
    callback=resolve_cli_command_prefix,
    help=(
        "Command prefix embedded in the packet. Defaults to the current nexus-tech "
        "executable; override it when the packet will run in another environment."
    ),
)


def register_beta_playtest_commands(
    app: typer.Typer,
    get_console: Callable[[], Console],
) -> None:
    """Register release-only beta evidence commands on the main application."""

    @app.command("prepare-beta-playtest-session")
    def prepare_beta_playtest_session_command(
        interface_mode: BetaPlaytestInterface = BETA_PREPARATION_INTERFACE_OPTION,
        viewport: str = BETA_PREPARATION_VIEWPORT_OPTION,
        motion_mode: MotionMode = BETA_PREPARATION_MOTION_OPTION,
        command_prefix: str = BETA_COMMAND_PREFIX_OPTION,
        output: Path = BETA_PREPARATION_OUTPUT_OPTION,
        db_path: Path = BETA_DB_PATH_OPTION,
    ) -> None:
        """Prepare the next human session without recording evidence."""

        console = get_console()
        repository = BetaPlaytestRepository(db_path)
        try:
            sessions = repository.list_sessions()
            preparation = build_beta_playtest_preparation(
                sessions,
                game_version=__version__,
                interface_mode=interface_mode,
                viewport=viewport,
                motion_mode=motion_mode,
                command_prefix=command_prefix,
                database_path=str(db_path),
            )
            output.write_text(
                format_beta_playtest_preparation_markdown(preparation),
                encoding="utf-8",
            )
        except (OSError, PersistenceError, ValueError) as error:
            _exit_with_error(console, "Beta Session Preparation Failed", str(error))
        render_beta_playtest_preparation(console, preparation)
        console.print(
            Panel(
                Text(
                    f"Human beta session packet written to {output}",
                    overflow="fold",
                    no_wrap=False,
                ),
                title="Local Session Artifact",
                border_style="cyan",
                expand=True,
            )
        )

    @app.command("record-beta-playtest-session")
    def record_beta_playtest_session_command(
        session_key: str = typer.Option(
            ...,
            "--session-key",
            help="Stable anonymous session key, for example beta-001.",
        ),
        tester_code: str = typer.Option(
            ...,
            "--tester-code",
            help="Anonymous tester code only; never enter a name or email address.",
        ),
        scenario_id: str = typer.Option(
            ...,
            "--scenario",
            help="One of the six featured campaign scenario ids.",
        ),
        interface_mode: BetaPlaytestInterface = BETA_INTERFACE_OPTION,
        viewport: str = typer.Option(
            ...,
            "--viewport",
            help="Observed terminal/window size as WIDTHxHEIGHT.",
        ),
        first_turn_seconds: int = typer.Option(
            ...,
            "--first-turn-seconds",
            min=1,
            max=3600,
            help="Elapsed seconds until the tester completed turn one.",
        ),
        turn_one: BetaObservationResult = BETA_TURN_ONE_OPTION,
        pause_back: BetaObservationResult = BETA_PAUSE_BACK_OPTION,
        tradeoff: BetaObservationResult = BETA_TRADEOFF_OPTION,
        act_three: BetaObservationResult = BETA_ACT_THREE_OPTION,
        blocker: BetaBlockerResult = BETA_BLOCKER_OPTION,
        notes: str = typer.Option(
            ...,
            "--notes",
            help="Concrete observation only; never include names, emails, paths, or secrets.",
        ),
        confirm_human_session: bool = typer.Option(
            False,
            "--confirm-human-session",
            help="Attest that this row came from an observed real-human play session.",
        ),
        db_path: Path = BETA_DB_PATH_OPTION,
        replace: bool = typer.Option(
            False,
            "--replace",
            help="Explicitly replace an existing session key when correcting evidence.",
        ),
    ) -> None:
        """Record one observed real-human beta session in the local database."""

        console = get_console()
        if not confirm_human_session:
            _exit_with_error(
                console,
                "Human Session Confirmation Required",
                "Re-run with --confirm-human-session only after observing a real person play.",
            )
        featured_ids = {journey.scenario_id for journey in list_featured_campaign_journeys()}
        if scenario_id not in featured_ids:
            available = ", ".join(sorted(featured_ids))
            _exit_with_error(
                console,
                "Featured Campaign Required",
                f"Unknown featured scenario '{scenario_id}'. Available: {available}",
            )

        repository = BetaPlaytestRepository(db_path)
        session = BetaPlaytestSession(
            session_key=session_key,
            tester_code=tester_code,
            scenario_id=scenario_id,
            interface_mode=interface_mode,
            viewport=viewport,
            first_turn_seconds=first_turn_seconds,
            turn_one_unaided=turn_one is BetaObservationResult.PASS,
            pause_back_success=pause_back is BetaObservationResult.PASS,
            tradeoff_explained=tradeoff is BetaObservationResult.PASS,
            reached_act_three=act_three is BetaObservationResult.PASS,
            blocker_found=blocker is BetaBlockerResult.FOUND,
            notes=notes,
            game_version=__version__,
            recorded_at=datetime.now(UTC).isoformat(),
        )
        try:
            repository.save_session(session, replace=replace)
            sessions = repository.list_sessions()
        except (PersistenceError, ValueError) as error:
            _exit_with_error(console, "Beta Evidence Write Failed", str(error))
        render_beta_playtest_status(
            console,
            build_beta_playtest_status(sessions, game_version=__version__),
        )

    @app.command("beta-playtest-status")
    def beta_playtest_status_command(
        db_path: Path = BETA_DB_PATH_OPTION,
    ) -> None:
        """Review current-version human beta coverage and unresolved gates."""

        console = get_console()
        repository = BetaPlaytestRepository(db_path)
        try:
            sessions = repository.list_sessions()
        except PersistenceError as error:
            _exit_with_error(console, "Beta Evidence Read Failed", str(error))
        render_beta_playtest_status(
            console,
            build_beta_playtest_status(sessions, game_version=__version__),
        )


def _exit_with_error(console: Console, title: str, message: str) -> None:
    console.print(Panel.fit(message, title=title, border_style="red"))
    raise typer.Exit(code=1)
