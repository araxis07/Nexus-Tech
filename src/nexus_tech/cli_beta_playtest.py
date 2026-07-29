"""CLI registration for structured, local human beta evidence."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

import typer
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

from nexus_tech import __version__
from nexus_tech.beta_playtest_packet import (
    validate_beta_playtest_session_packet,
)
from nexus_tech.cli_command_prefix import resolve_cli_command_prefix
from nexus_tech.config import DEFAULT_DATABASE_PATH
from nexus_tech.persistence.beta_playtest_repository import (
    BetaPlaytestInterface,
    BetaPlaytestRepository,
    BetaPlaytestSession,
)
from nexus_tech.persistence.errors import PersistenceError
from nexus_tech.persistence.save_coordinator import SaveLoadCoordinator
from nexus_tech.presentation.beta_playtest import (
    format_beta_playtest_execution_plan_markdown,
    format_beta_playtest_preparation_markdown,
    render_beta_owner_rehearsal_briefing,
    render_beta_owner_rehearsal_status,
    render_beta_playtest_execution_plan,
    render_beta_playtest_preparation,
    render_beta_playtest_status,
)
from nexus_tech.simulation.beta_owner_rehearsal import (
    BetaOwnerRehearsalStatus,
    build_beta_owner_rehearsal_status,
)
from nexus_tech.simulation.beta_playtest import (
    BetaBlockerResult,
    BetaObservationResult,
    build_beta_playtest_status,
)
from nexus_tech.simulation.beta_playtest_execution import (
    build_beta_playtest_execution_plan,
)
from nexus_tech.simulation.beta_playtest_preparation import (
    BetaPlaytestPreparation,
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
BETA_REQUIRE_REVIEW_READY_OPTION = typer.Option(
    False,
    "--require-review-ready",
    help=(
        "Exit non-zero until current-version human evidence meets every automated "
        "review-readiness criterion. A zero exit still requires reviewer approval."
    ),
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
BETA_EXECUTION_OUTPUT_OPTION = typer.Option(
    Path("/tmp/nexus-tech-beta-playtest-plan.md"),
    "--output",
    help="Local Markdown path for the six-campaign execution plan.",
)
BETA_EXECUTION_PACKET_OUTPUT_OPTION = typer.Option(
    Path("/tmp/nexus-tech-beta-playtest-next.md"),
    "--packet-output",
    help="Local Markdown path used by the plan's next-session preparation command.",
)
BETA_PACKET_INPUT_OPTION = typer.Option(
    Path("/tmp/nexus-tech-beta-playtest-next.md"),
    "--input",
    help="Generated local Markdown session packet to validate before handoff.",
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
BETA_SESSION_DB_PATH_OPTION = typer.Option(
    None,
    "--session-db-path",
    help=(
        "Fresh disposable SQLite gameplay profile for the observed tester. Defaults "
        "to a unique path in the system temporary directory."
    ),
)
BETA_REHEARSAL_DB_PATH_OPTION = typer.Option(
    None,
    "--rehearsal-db-path",
    help=(
        "Fresh disposable SQLite gameplay profile for owner rehearsal. Defaults to "
        "a different unique path in the system temporary directory."
    ),
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

BetaOwnerRehearsalLauncher = Callable[[Path, str, MotionMode], str]


def _require_fresh_gameplay_profile(path: Path, *, label: str) -> None:
    parent = path.parent
    if not parent.is_dir():
        raise ValueError(f"{label} parent directory must already exist: {parent}.")
    profile_artifacts = (path, Path(f"{path}-journal"), Path(f"{path}-wal"), Path(f"{path}-shm"))
    existing_artifact = next(
        (artifact for artifact in profile_artifacts if artifact.exists()), None
    )
    if existing_artifact is not None:
        raise ValueError(
            f"{label} must not already exist: {existing_artifact}. Choose a fresh profile path."
        )


def _load_current_beta_preparation(
    input_path: Path,
    db_path: Path,
) -> BetaPlaytestPreparation:
    markdown = input_path.read_text(encoding="utf-8")
    sessions = BetaPlaytestRepository(db_path).list_sessions()
    return validate_beta_playtest_session_packet(
        markdown,
        sessions,
        game_version=__version__,
        packet_path=str(input_path),
        evidence_database_path=str(db_path),
    )


def _require_owner_rehearsal(preparation: BetaPlaytestPreparation) -> None:
    if not preparation.owner_rehearsal_required:
        raise ValueError(
            "This packet does not require an owner rehearsal; use its normal "
            "packet preflight before tester handoff."
        )


def _build_current_owner_rehearsal_status(
    preparation: BetaPlaytestPreparation,
) -> BetaOwnerRehearsalStatus:
    rehearsal_path = Path(preparation.owner_rehearsal_database_path)
    if rehearsal_path.exists() and not rehearsal_path.is_file():
        raise ValueError(f"Owner rehearsal profile must be a SQLite file: {rehearsal_path}.")
    database_exists = rehearsal_path.is_file()
    archives = SaveLoadCoordinator(rehearsal_path).list_run_archives() if database_exists else []
    return build_beta_owner_rehearsal_status(
        archives,
        database_path=str(rehearsal_path),
        database_exists=database_exists,
        target_scenario_id=preparation.target_scenario_id or "",
    )


def register_beta_playtest_commands(
    app: typer.Typer,
    get_console: Callable[[], Console],
    launch_owner_rehearsal: BetaOwnerRehearsalLauncher | None = None,
) -> None:
    """Register release-only beta evidence commands on the main application."""

    @app.command("beta-playtest-plan")
    def beta_playtest_plan_command(
        command_prefix: str = BETA_COMMAND_PREFIX_OPTION,
        output: Path = BETA_EXECUTION_OUTPUT_OPTION,
        packet_output: Path = BETA_EXECUTION_PACKET_OUTPUT_OPTION,
        db_path: Path = BETA_DB_PATH_OPTION,
    ) -> None:
        """Export all six campaign lanes while selecting only one next session."""

        console = get_console()
        repository = BetaPlaytestRepository(db_path)
        try:
            sessions = repository.list_sessions()
            plan = build_beta_playtest_execution_plan(
                sessions,
                game_version=__version__,
                command_prefix=command_prefix,
                evidence_database_path=str(db_path),
                packet_output_path=str(packet_output),
                plan_output_path=str(output),
            )
            output.write_text(
                format_beta_playtest_execution_plan_markdown(plan),
                encoding="utf-8",
            )
        except (OSError, PersistenceError, ValueError) as error:
            _exit_with_error(console, "Beta Execution Plan Failed", str(error))
        render_beta_playtest_execution_plan(console, plan)
        console.print(
            Panel(
                Text(
                    f"Human beta execution plan written to {output}",
                    overflow="fold",
                    no_wrap=False,
                ),
                title="Local Plan Artifact",
                border_style="cyan",
                expand=True,
            )
        )

    @app.command("prepare-beta-playtest-session")
    def prepare_beta_playtest_session_command(
        interface_mode: BetaPlaytestInterface = BETA_PREPARATION_INTERFACE_OPTION,
        viewport: str = BETA_PREPARATION_VIEWPORT_OPTION,
        motion_mode: MotionMode = BETA_PREPARATION_MOTION_OPTION,
        command_prefix: str = BETA_COMMAND_PREFIX_OPTION,
        output: Path = BETA_PREPARATION_OUTPUT_OPTION,
        db_path: Path = BETA_DB_PATH_OPTION,
        session_db_path: Path | None = BETA_SESSION_DB_PATH_OPTION,
        rehearsal_db_path: Path | None = BETA_REHEARSAL_DB_PATH_OPTION,
    ) -> None:
        """Prepare the next human session without recording evidence."""

        console = get_console()
        repository = BetaPlaytestRepository(db_path)
        try:
            sessions = repository.list_sessions()
            profile_token = uuid4().hex[:12]
            temporary_directory = Path(gettempdir())
            resolved_session_db_path = session_db_path or (
                temporary_directory / f"nexus-tech-beta-session-{profile_token}.db"
            )
            resolved_rehearsal_db_path = rehearsal_db_path or (
                temporary_directory / f"nexus-tech-beta-rehearsal-{profile_token}.db"
            )
            preparation = build_beta_playtest_preparation(
                sessions,
                game_version=__version__,
                interface_mode=interface_mode,
                viewport=viewport,
                motion_mode=motion_mode,
                command_prefix=command_prefix,
                packet_output_path=str(output),
                evidence_database_path=str(db_path),
                session_database_path=str(resolved_session_db_path),
                owner_rehearsal_database_path=str(resolved_rehearsal_db_path),
            )
            if preparation.requires_session:
                _require_fresh_gameplay_profile(
                    resolved_session_db_path,
                    label="Tester gameplay profile",
                )
                if preparation.owner_rehearsal_required:
                    _require_fresh_gameplay_profile(
                        resolved_rehearsal_db_path,
                        label="Owner rehearsal profile",
                    )
            packet_markdown = format_beta_playtest_preparation_markdown(preparation)
            validate_beta_playtest_session_packet(
                packet_markdown,
                sessions,
                game_version=__version__,
                packet_path=str(output),
                evidence_database_path=str(db_path),
            )
            output.write_text(packet_markdown, encoding="utf-8")
        except (OSError, PersistenceError, ValueError) as error:
            _exit_with_error(console, "Beta Session Preparation Failed", str(error))
        render_beta_playtest_preparation(console, preparation)
        console.print(
            Panel(
                Group(
                    Text(
                        f"Human beta session packet written to {output}",
                        overflow="fold",
                        no_wrap=False,
                    ),
                    Text(
                        "Validate immediately before handoff:",
                        style="bold",
                    ),
                    Text(
                        preparation.validation_command,
                        style="cyan",
                        overflow="fold",
                        no_wrap=False,
                    ),
                ),
                title="Local Session Artifact",
                border_style="cyan",
                expand=True,
            )
        )

    @app.command("validate-beta-playtest-session-packet")
    def validate_beta_playtest_session_packet_command(
        input_path: Path = BETA_PACKET_INPUT_OPTION,
        db_path: Path = BETA_DB_PATH_OPTION,
    ) -> None:
        """Reject stale, edited, or profile-contaminated beta session packets."""

        console = get_console()
        repository = BetaPlaytestRepository(db_path)
        try:
            markdown = input_path.read_text(encoding="utf-8")
            sessions = repository.list_sessions()
            preparation = validate_beta_playtest_session_packet(
                markdown,
                sessions,
                game_version=__version__,
                packet_path=str(input_path),
                evidence_database_path=str(db_path),
            )
            if preparation.requires_session:
                _require_fresh_gameplay_profile(
                    Path(preparation.session_database_path),
                    label="Tester gameplay profile",
                )
                if preparation.owner_rehearsal_required:
                    _require_fresh_gameplay_profile(
                        Path(preparation.owner_rehearsal_database_path),
                        label="Owner rehearsal profile",
                    )
        except (OSError, PersistenceError, ValueError) as error:
            _exit_with_error(console, "Beta Packet Validation Failed", str(error))

        target = preparation.target_scenario_id or "manual release review"
        console.print(
            Panel.fit(
                (
                    "Packet matches the current build and evidence snapshot.\n"
                    f"Status: {preparation.evidence_status}\n"
                    f"Target: {target}\n"
                    "Any required gameplay profile paths are fresh and isolated."
                ),
                title="Beta Packet Validated",
                border_style="green",
            )
        )

    @app.command("validate-beta-owner-rehearsal")
    def validate_beta_owner_rehearsal_command(
        input_path: Path = BETA_PACKET_INPUT_OPTION,
        db_path: Path = BETA_DB_PATH_OPTION,
    ) -> None:
        """Require an archived target route before the first tester handoff."""

        console = get_console()
        try:
            preparation = _load_current_beta_preparation(input_path, db_path)
            _require_owner_rehearsal(preparation)
            _require_fresh_gameplay_profile(
                Path(preparation.session_database_path),
                label="Tester gameplay profile",
            )
            status = _build_current_owner_rehearsal_status(preparation)
        except (OSError, PersistenceError, ValueError) as error:
            _exit_with_error(console, "Owner Rehearsal Validation Failed", str(error))

        render_beta_owner_rehearsal_status(console, status)
        if not status.completed:
            raise typer.Exit(code=1)

    @app.command("run-beta-owner-rehearsal")
    def run_beta_owner_rehearsal_command(
        input_path: Path = BETA_PACKET_INPUT_OPTION,
        db_path: Path = BETA_DB_PATH_OPTION,
    ) -> None:
        """Preflight, launch, and validate the visible owner rehearsal."""

        console = get_console()
        try:
            preparation = _load_current_beta_preparation(input_path, db_path)
            _require_owner_rehearsal(preparation)
            if preparation.interface_mode is not BetaPlaytestInterface.TWO_D:
                raise ValueError(
                    "The guarded owner-rehearsal runner requires a 2d packet. "
                    "Use the packet's manual commands for a terminal session."
                )
            _require_fresh_gameplay_profile(
                Path(preparation.session_database_path),
                label="Tester gameplay profile",
            )
            rehearsal_path = Path(preparation.owner_rehearsal_database_path)
            status = _build_current_owner_rehearsal_status(preparation)
            if status.completed:
                render_beta_owner_rehearsal_status(console, status)
                console.print(
                    Panel.fit(
                        "The target route is already archived; "
                        "the visible window was not reopened.",
                        title="Owner Rehearsal Already Complete",
                        border_style="green",
                    )
                )
                return
            profile_exists = rehearsal_path.is_file()
            if not profile_exists:
                _require_fresh_gameplay_profile(
                    rehearsal_path,
                    label="Owner rehearsal profile",
                )
            has_save = (
                bool(SaveLoadCoordinator(rehearsal_path).list_save_slots())
                if profile_exists
                else False
            )
            if launch_owner_rehearsal is None:
                raise ValueError("The visible 2D owner-rehearsal launcher is unavailable.")

            render_beta_owner_rehearsal_briefing(
                console,
                preparation,
                profile_exists=profile_exists,
                has_save=has_save,
            )
            exit_reason = launch_owner_rehearsal(
                rehearsal_path,
                preparation.viewport,
                preparation.motion_mode,
            )
            status = _build_current_owner_rehearsal_status(preparation)
            has_save_after_launch = (
                bool(SaveLoadCoordinator(rehearsal_path).list_save_slots())
                if rehearsal_path.is_file()
                else False
            )
        except (OSError, PersistenceError, ValueError) as error:
            _exit_with_error(console, "Owner Rehearsal Run Failed", str(error))

        console.print(
            Panel.fit(
                f"The visible window closed with reason '{exit_reason}'. Running archive gate now.",
                title="Owner Rehearsal Window Closed",
                border_style="cyan",
            )
        )
        render_beta_owner_rehearsal_status(console, status)
        if not status.completed:
            next_launch = "Continue existing save" if has_save_after_launch else "New Game"
            retry_instruction = (
                "Re-run the guarded command to Continue this rehearsal profile, "
                "then finish the route and choose Save & Archive before closing the window."
                if has_save_after_launch
                else "Re-run the guarded command, choose New Game, then finish the route "
                "and choose Save & Archive before closing the window."
            )
            console.print(
                Panel(
                    Group(
                        Text(f"Next launch: {next_launch}", style="bold"),
                        Text(""),
                        Text(
                            f"No complete target archive was found. {retry_instruction}",
                            overflow="fold",
                            no_wrap=False,
                        ),
                        Text(""),
                        Text(
                            preparation.owner_rehearsal_run_command,
                            style="cyan",
                            overflow="fold",
                            no_wrap=False,
                        ),
                    ),
                    title="Owner Rehearsal Next Action",
                    subtitle="Tester profile and human evidence remain untouched",
                    border_style="yellow",
                    expand=True,
                )
            )
            raise typer.Exit(code=1)

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
        retest_of: str | None = typer.Option(
            None,
            "--retest-of",
            help=(
                "Unresolved prior session superseded by this observed retest. The prior "
                "row remains stored as history."
            ),
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
            retest_of=retest_of,
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
        require_review_ready: bool = BETA_REQUIRE_REVIEW_READY_OPTION,
    ) -> None:
        """Review current-version human beta coverage and unresolved gates."""

        console = get_console()
        repository = BetaPlaytestRepository(db_path)
        try:
            sessions = repository.list_sessions()
        except PersistenceError as error:
            _exit_with_error(console, "Beta Evidence Read Failed", str(error))
        status = build_beta_playtest_status(sessions, game_version=__version__)
        render_beta_playtest_status(console, status)
        if require_review_ready and not status.review_ready:
            raise typer.Exit(code=1)


def _exit_with_error(console: Console, title: str, message: str) -> None:
    console.print(
        Panel(
            Text(message, overflow="fold", no_wrap=False),
            title=title,
            border_style="red",
            expand=True,
        )
    )
    raise typer.Exit(code=1)
