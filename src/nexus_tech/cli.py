"""Typer CLI entrypoint for NEXUS TECH."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.traceback import install as install_rich_traceback

from nexus_tech import __version__
from nexus_tech.config import (
    DEFAULT_DATABASE_PATH,
    DEFAULT_SCENARIO_ID,
    DEMO_SEED_EXAMPLE,
)
from nexus_tech.content.models import ProductTemplateDefinition
from nexus_tech.domain.models import (
    BudgetStance,
    CampaignGoalId,
    CompanyStrategy,
    DifficultyMode,
    Employee,
    EmployeeRole,
    GameState,
    MarketSegment,
    PendingEvent,
    PricingTier,
    Product,
    RoadmapFocus,
    Seniority,
    TurnAction,
)
from nexus_tech.persistence.errors import PersistenceError
from nexus_tech.persistence.save_coordinator import DEFAULT_SAVE_SLOT, SaveLoadCoordinator
from nexus_tech.presentation.dashboard import (
    render_action_feedback,
    render_balance_audit,
    render_balance_comparison,
    render_balance_lab,
    render_balance_matrix,
    render_campaign_goal_catalog,
    render_candidate_pool,
    render_competitor_archetype_catalog,
    render_content_health,
    render_customer_view,
    render_dashboard,
    render_employee_picker,
    render_event_catalog,
    render_event_result,
    render_game_over,
    render_glossary,
    render_intro,
    render_pending_event,
    render_product_picker,
    render_product_template_catalog,
    render_product_template_picker,
    render_quick_guide,
    render_report,
    render_roadmap_catalog,
    render_save_slot_catalog,
    render_scenario_catalog,
    render_segment_catalog,
    render_team_view,
    render_turn_resolution,
    render_tutorial,
    render_victory,
)
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.balance_lab import (
    format_balance_matrix_csv,
    format_balance_report_markdown,
    run_balance_audit,
    run_balance_batch,
    run_balance_comparison,
    run_balance_matrix,
)
from nexus_tech.simulation.campaign import get_campaign_goal, list_campaign_goals
from nexus_tech.simulation.catalog_validation import validate_content_catalogs
from nexus_tech.simulation.engine import (
    ActionContext,
    apply_action,
    create_new_game,
    get_employee_choices,
    get_product_choices,
    resolve_turn,
)
from nexus_tech.simulation.event_registry import get_event_registry
from nexus_tech.simulation.events import resolve_pending_event
from nexus_tech.simulation.hiring import generate_candidate_pool
from nexus_tech.simulation.randomness import RandomSource
from nexus_tech.simulation.roadmap import get_roadmap_profile
from nexus_tech.simulation.scenarios import (
    get_available_competitor_archetypes,
    get_available_product_templates,
    get_available_scenarios,
)
from nexus_tech.simulation.segments import get_market_segment_profile

logger = logging.getLogger(__name__)

app = typer.Typer(
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    help=(
        "NEXUS TECH terminal management simulation.\n\n"
        "Start a new run, resume a local SQLite save, and play entirely from the terminal."
    ),
    rich_markup_mode="rich",
)
console = Console(highlight=False, soft_wrap=True)
DEBUG_MODE = False
DEFAULT_DB_PATH = DEFAULT_DATABASE_PATH


def show_version_callback(value: bool) -> None:
    """Print the current package version and exit immediately."""

    if not value:
        return
    console.print(f"NEXUS TECH {__version__}")
    raise typer.Exit()


DB_PATH_OPTION = typer.Option(
    DEFAULT_DB_PATH,
    "--db-path",
    help="SQLite database path used for save, load, and continue commands.",
)
SCENARIO_OPTION = typer.Option(
    DEFAULT_SCENARIO_ID,
    "--scenario",
    help="Starting scenario id. Use 'list-scenarios' to inspect the available catalog.",
)
COMPARE_SCENARIOS_OPTION = typer.Option(
    None,
    "--scenario",
    help=(
        "Scenario ids to compare. Repeat the option to compare multiple scenarios. "
        "Defaults to all scenarios."
    ),
)
DIFFICULTY_OPTION = typer.Option(
    None,
    "--difficulty",
    help="Optional run difficulty override: builder, standard, or founder.",
)
GOAL_OPTION = typer.Option(
    None,
    "--goal",
    help="Optional campaign goal override. Use 'list-goals' to inspect the catalog.",
)
BALANCE_DIFFICULTY_OPTION = typer.Option(
    DifficultyMode.STANDARD,
    "--difficulty",
    help="Difficulty profile to use for the balance run batch.",
)
BALANCE_GOAL_OPTION = typer.Option(
    CampaignGoalId.PROFIT_MACHINE,
    "--goal",
    help="Campaign goal used during the balance run batch.",
)
CSV_OUTPUT_OPTION = typer.Option(..., "--output", help="CSV path to write.")
BALANCE_REPORT_OUTPUT_OPTION = typer.Option(..., "--output", help="Markdown path to write.")

ACTION_KEYS = {
    "1": TurnAction.CREATE_PRODUCT,
    "2": TurnAction.IMPROVE_QUALITY,
    "3": TurnAction.ADD_FEATURE,
    "4": TurnAction.REDUCE_TECHNICAL_DEBT,
    "5": TurnAction.MARKET_PRODUCT,
    "6": TurnAction.ADJUST_PRICING,
    "7": TurnAction.SET_TARGET_SEGMENT,
    "8": TurnAction.SUNSET_PRODUCT,
    "9": TurnAction.SET_COMPANY_STRATEGY,
    "10": TurnAction.SET_ROADMAP,
    "11": TurnAction.SET_BUDGET_STANCE,
    "12": TurnAction.TAKE_LOAN,
    "13": TurnAction.RAISE_ANGEL,
    "14": TurnAction.RAISE_VC,
    "15": TurnAction.REPAY_DEBT,
    "16": TurnAction.REVIEW_FINANCE,
    "17": TurnAction.HIRE_EMPLOYEE,
    "18": TurnAction.FIRE_EMPLOYEE,
    "19": TurnAction.ASSIGN_EMPLOYEE,
    "20": TurnAction.UNASSIGN_EMPLOYEE,
    "21": TurnAction.REST_TEAM,
    "22": TurnAction.REVIEW_TEAM,
    "23": TurnAction.REVIEW_CUSTOMERS,
    "24": TurnAction.VIEW_REPORT,
    "25": TurnAction.WAIT,
    "26": TurnAction.VIEW_STATUS,
    "27": TurnAction.END_TURN,
}
UTILITY_ACTION_KEYS = {
    "28": "save_game",
    "29": "load_game",
    "30": "show_guide",
    "31": "show_glossary",
    "32": "show_tutorial",
}
ALL_MENU_KEYS = list(ACTION_KEYS) + list(UTILITY_ACTION_KEYS)

PRODUCT_TARGETED_ACTIONS = {
    TurnAction.IMPROVE_QUALITY,
    TurnAction.ADD_FEATURE,
    TurnAction.REDUCE_TECHNICAL_DEBT,
    TurnAction.MARKET_PRODUCT,
    TurnAction.ADJUST_PRICING,
    TurnAction.SET_TARGET_SEGMENT,
    TurnAction.SUNSET_PRODUCT,
}


@app.callback(invoke_without_command=True)
def root(
    ctx: typer.Context,
    company_name: Optional[str] = typer.Option(  # noqa: UP045
        None,
        "--company-name",
        help="Company display name override. Defaults to the scenario's company name.",
    ),
    product_name: Optional[str] = typer.Option(  # noqa: UP045
        None,
        "--product-name",
        help="Primary product name override. Applies to the first scenario product.",
    ),
    scenario: str = SCENARIO_OPTION,
    difficulty: DifficultyMode | None = DIFFICULTY_OPTION,
    goal: CampaignGoalId | None = GOAL_OPTION,
    seed: Optional[int] = typer.Option(  # noqa: UP045
        None,
        "--seed",
        help=f"Seed for reproducible simulation and demo runs, for example {DEMO_SEED_EXAMPLE}.",
    ),
    db_path: Path = DB_PATH_OPTION,
    slot: str = typer.Option(DEFAULT_SAVE_SLOT, "--slot", help="Default save slot name."),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug logging and rich tracebacks for development runs.",
    ),
    version: bool = typer.Option(  # noqa: FBT001
        False,
        "--version",
        callback=show_version_callback,
        is_eager=True,
        help="Show the installed NEXUS TECH version and exit.",
    ),
) -> None:
    """Start a new local game when no subcommand is given."""

    configure_cli(debug=debug)
    ctx.obj = {"debug": debug}

    if ctx.invoked_subcommand is not None:
        return
    start_new_game(
        company_name=company_name,
        product_name=product_name,
        scenario_id=scenario,
        difficulty_mode=difficulty,
        campaign_goal_id=goal,
        seed=seed,
        db_path=db_path,
        slot_name=slot,
    )


@app.command("new-game")
def new_game_command(
    company_name: Optional[str] = typer.Option(  # noqa: UP045
        None,
        "--company-name",
        help="Company display name override. Defaults to the scenario's company name.",
    ),
    product_name: Optional[str] = typer.Option(  # noqa: UP045
        None,
        "--product-name",
        help="Primary product name override. Applies to the first scenario product.",
    ),
    scenario: str = SCENARIO_OPTION,
    difficulty: DifficultyMode | None = DIFFICULTY_OPTION,
    goal: CampaignGoalId | None = GOAL_OPTION,
    seed: Optional[int] = typer.Option(  # noqa: UP045
        None,
        "--seed",
        help=f"Seed for reproducible simulation and demo runs, for example {DEMO_SEED_EXAMPLE}.",
    ),
    db_path: Path = DB_PATH_OPTION,
    slot: str = typer.Option(DEFAULT_SAVE_SLOT, "--slot", help="Default save slot name."),
) -> None:
    """Start a brand new local game."""

    start_new_game(
        company_name=company_name,
        product_name=product_name,
        scenario_id=scenario,
        difficulty_mode=difficulty,
        campaign_goal_id=goal,
        seed=seed,
        db_path=db_path,
        slot_name=slot,
    )


@app.command("play", hidden=True)
def play_alias(
    company_name: Optional[str] = typer.Option(  # noqa: UP045
        None,
        "--company-name",
        help="Company display name override. Defaults to the scenario's company name.",
    ),
    product_name: Optional[str] = typer.Option(  # noqa: UP045
        None,
        "--product-name",
        help="Primary product name override. Applies to the first scenario product.",
    ),
    scenario: str = SCENARIO_OPTION,
    difficulty: DifficultyMode | None = DIFFICULTY_OPTION,
    goal: CampaignGoalId | None = GOAL_OPTION,
    seed: Optional[int] = typer.Option(  # noqa: UP045
        None,
        "--seed",
        help=f"Seed for reproducible simulation and demo runs, for example {DEMO_SEED_EXAMPLE}.",
    ),
    db_path: Path = DB_PATH_OPTION,
    slot: str = typer.Option(DEFAULT_SAVE_SLOT, "--slot", help="Default save slot name."),
) -> None:
    """Backward-compatible alias for starting a new game."""

    start_new_game(
        company_name=company_name,
        product_name=product_name,
        scenario_id=scenario,
        difficulty_mode=difficulty,
        campaign_goal_id=goal,
        seed=seed,
        db_path=db_path,
        slot_name=slot,
    )


@app.command("list-scenarios")
def list_scenarios_command() -> None:
    """Print the available starting scenarios."""

    render_scenario_catalog(console, get_available_scenarios())


@app.command("list-templates")
def list_templates_command() -> None:
    """Print the available product templates."""

    render_product_template_catalog(console, get_available_product_templates())


@app.command("list-goals")
def list_goals_command() -> None:
    """Print the available campaign goals."""

    render_campaign_goal_catalog(console, list_campaign_goals())


@app.command("list-rivals")
def list_rivals_command() -> None:
    """Print the available competitor archetypes."""

    render_competitor_archetype_catalog(console, get_available_competitor_archetypes())


@app.command("list-events")
def list_events_command() -> None:
    """Print the supported dynamic event catalog."""

    render_event_catalog(console, get_event_registry())


@app.command("list-candidates")
def list_candidates_command(
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed used to generate a deterministic hiring pool.",
    ),
    count: int = typer.Option(3, "--count", min=1, max=6, help="Number of candidates to show."),
) -> None:
    """Print a deterministic sample hiring candidate pool."""

    render_candidate_pool(console, generate_candidate_pool(RandomSource(seed=seed), count=count))


@app.command("list-segments")
def list_segments_command() -> None:
    """Print customer segment trade-offs used by growth and churn formulas."""

    profiles = tuple((segment, get_market_segment_profile(segment)) for segment in MarketSegment)
    render_segment_catalog(console, profiles)


@app.command("list-roadmaps")
def list_roadmaps_command() -> None:
    """Print available quarter-scale roadmap initiatives."""

    profiles = tuple(
        (
            focus.value,
            get_roadmap_profile(focus, roadmap_set_turn=1, current_turn=1).summary,
        )
        for focus in RoadmapFocus
    )
    render_roadmap_catalog(console, profiles)


@app.command("list-initiatives", hidden=True)
def list_initiatives_alias() -> None:
    """Backward-compatible alias for roadmap initiative discovery."""

    list_roadmaps_command()


@app.command("simulate-balance")
def simulate_balance_command(
    scenario: str = SCENARIO_OPTION,
    difficulty: DifficultyMode = BALANCE_DIFFICULTY_OPTION,
    goal: CampaignGoalId = BALANCE_GOAL_OPTION,
    runs: int = typer.Option(5, "--runs", min=1, help="Number of deterministic runs."),
    turns: int = typer.Option(10, "--turns", min=1, help="Maximum turns per run."),
    seed_base: int = typer.Option(
        100,
        "--seed-base",
        help="Base seed. Each run increments from this value.",
    ),
) -> None:
    """Run a deterministic batch of autoplay simulations for balance checks."""

    validate_scenario_id(scenario)
    batch = run_balance_batch(
        scenario_id=scenario,
        difficulty_mode=difficulty,
        campaign_goal_id=goal,
        runs=runs,
        turns=turns,
        seed_base=seed_base,
    )
    render_balance_lab(console, batch)


@app.command("compare-balance")
def compare_balance_command(
    scenario: Optional[list[str]] = COMPARE_SCENARIOS_OPTION,
    difficulty: DifficultyMode = BALANCE_DIFFICULTY_OPTION,
    goal: CampaignGoalId = BALANCE_GOAL_OPTION,
    runs: int = typer.Option(3, "--runs", min=1, help="Number of deterministic runs."),
    turns: int = typer.Option(10, "--turns", min=1, help="Maximum turns per run."),
    seed_base: int = typer.Option(
        100,
        "--seed-base",
        help="Base seed. Each scenario gets a deterministic seed range from this value.",
    ),
) -> None:
    """Compare multiple scenarios side by side using deterministic autoplay."""

    scenario_ids = resolve_scenario_ids(scenario)
    comparison = run_balance_comparison(
        scenario_ids=scenario_ids,
        difficulty_mode=difficulty,
        campaign_goal_id=goal,
        runs=runs,
        turns=turns,
        seed_base=seed_base,
    )
    render_balance_comparison(console, comparison)


@app.command("balance-matrix")
def balance_matrix_command(
    scenario: Optional[list[str]] = COMPARE_SCENARIOS_OPTION,
    goal: CampaignGoalId = BALANCE_GOAL_OPTION,
    runs: int = typer.Option(2, "--runs", min=1, help="Number of deterministic runs."),
    turns: int = typer.Option(10, "--turns", min=1, help="Maximum turns per run."),
    seed_base: int = typer.Option(
        100,
        "--seed-base",
        help="Base seed. Each matrix cell gets a deterministic seed range from this value.",
    ),
) -> None:
    """Compare multiple scenarios across all supported difficulty modes."""

    scenario_ids = resolve_scenario_ids(scenario)
    matrix = run_balance_matrix(
        scenario_ids=scenario_ids,
        campaign_goal_id=goal,
        runs=runs,
        turns=turns,
        seed_base=seed_base,
    )
    render_balance_matrix(console, matrix)


@app.command("balance-audit")
def balance_audit_command(
    scenario: Optional[list[str]] = COMPARE_SCENARIOS_OPTION,
    goal: CampaignGoalId = BALANCE_GOAL_OPTION,
    runs: int = typer.Option(2, "--runs", min=1, help="Number of deterministic runs."),
    turns: int = typer.Option(10, "--turns", min=1, help="Maximum turns per run."),
    seed_base: int = typer.Option(
        100,
        "--seed-base",
        help="Base seed. Each matrix cell gets a deterministic seed range from this value.",
    ),
) -> None:
    """Flag rough balance cells across scenarios and supported difficulties."""

    scenario_ids = resolve_scenario_ids(scenario)
    audit = run_balance_audit(
        scenario_ids=scenario_ids,
        campaign_goal_id=goal,
        runs=runs,
        turns=turns,
        seed_base=seed_base,
    )
    render_balance_audit(console, audit)


@app.command("export-balance-csv")
def export_balance_csv_command(
    output: Path = CSV_OUTPUT_OPTION,
    scenario: Optional[list[str]] = COMPARE_SCENARIOS_OPTION,
    goal: CampaignGoalId = BALANCE_GOAL_OPTION,
    runs: int = typer.Option(2, "--runs", min=1, help="Number of deterministic runs."),
    turns: int = typer.Option(10, "--turns", min=1, help="Maximum turns per run."),
    seed_base: int = typer.Option(
        100,
        "--seed-base",
        help="Base seed. Each matrix cell gets a deterministic seed range from this value.",
    ),
) -> None:
    """Export a scenario-versus-difficulty balance matrix to CSV."""

    scenario_ids = resolve_scenario_ids(scenario)
    matrix = run_balance_matrix(
        scenario_ids=scenario_ids,
        campaign_goal_id=goal,
        runs=runs,
        turns=turns,
        seed_base=seed_base,
    )
    output.write_text(format_balance_matrix_csv(matrix), encoding="utf-8")
    console.print(
        Panel.fit(
            f"Wrote balance CSV to {output}",
            title="Balance Export",
            border_style="green",
        )
    )


@app.command("balance-report")
def balance_report_command(
    output: Path = BALANCE_REPORT_OUTPUT_OPTION,
    scenario: Optional[list[str]] = COMPARE_SCENARIOS_OPTION,
    goal: CampaignGoalId = BALANCE_GOAL_OPTION,
    runs: int = typer.Option(2, "--runs", min=1, help="Number of deterministic runs."),
    turns: int = typer.Option(10, "--turns", min=1, help="Maximum turns per run."),
    seed_base: int = typer.Option(
        100,
        "--seed-base",
        help="Base seed. Each matrix cell gets a deterministic seed range from this value.",
    ),
) -> None:
    """Export a Markdown balance matrix plus audit findings."""

    scenario_ids = resolve_scenario_ids(scenario)
    matrix = run_balance_matrix(
        scenario_ids=scenario_ids,
        campaign_goal_id=goal,
        runs=runs,
        turns=turns,
        seed_base=seed_base,
    )
    audit = run_balance_audit(
        scenario_ids=scenario_ids,
        campaign_goal_id=goal,
        runs=runs,
        turns=turns,
        seed_base=seed_base,
    )
    output.write_text(format_balance_report_markdown(matrix, audit), encoding="utf-8")
    console.print(
        Panel.fit(
            f"Wrote balance report to {output}",
            title="Balance Report",
            border_style="green",
        )
    )


@app.command("guide")
def guide_command() -> None:
    """Print a compact quick-start guide."""

    render_quick_guide(console)


@app.command("tutorial")
def tutorial_command() -> None:
    """Print a first-run tutorial path for demos and new players."""

    render_tutorial(console)


@app.command("glossary")
def glossary_command() -> None:
    """Explain core stats, systems, and decision families."""

    render_glossary(console)


@app.command("validate-content")
def validate_content_command() -> None:
    """Validate content catalogs and event registry wiring."""

    report = validate_content_catalogs()
    render_content_health(console, report)
    if not report.ok:
        raise typer.Exit(code=1) from None


@app.command("list-saves")
def list_saves_command(
    db_path: Path = DB_PATH_OPTION,
) -> None:
    """List all local save slots with compact metadata."""

    coordinator = SaveLoadCoordinator(db_path)
    try:
        save_slots = coordinator.list_save_slots()
    except PersistenceError as error:
        raise_cli_persistence_error("Save List Failed", error)
    render_save_slot_catalog(console, save_slots)


@app.command("check-saves")
def check_saves_command(
    db_path: Path = DB_PATH_OPTION,
) -> None:
    """Run SQLite integrity and foreign-key checks against local saves."""

    coordinator = SaveLoadCoordinator(db_path)
    try:
        report = coordinator.check_save_health()
    except PersistenceError as error:
        raise_cli_persistence_error("Save Health Check Failed", error)

    lines = [
        f"Integrity: {'ok' if report.integrity_ok else 'failed'}",
        f"Foreign Keys: {'ok' if report.foreign_key_ok else 'failed'}",
        f"Slots: {report.slot_count}",
        f"Schema Version: {report.schema_version}",
        "",
        report.message,
    ]
    console.print(
        Panel.fit(
            "\n".join(lines),
            title="Save Health",
            border_style="green" if report.integrity_ok and report.foreign_key_ok else "red",
        )
    )


@app.command("doctor")
def doctor_command(
    db_path: Path = DB_PATH_OPTION,
) -> None:
    """Print release, content, and save diagnostics for the local install."""

    save_status = "No save database found yet."
    slot_count = 0
    schema_version = "-"
    if db_path.exists():
        coordinator = SaveLoadCoordinator(db_path)
        try:
            health = coordinator.check_save_health()
        except PersistenceError as error:
            raise_cli_persistence_error("Doctor Failed", error)
        save_status = health.message
        slot_count = health.slot_count
        schema_version = str(health.schema_version)

    table = Table.grid(padding=(0, 1))
    table.add_row("Version", __version__)
    table.add_row("DB Path", str(db_path))
    table.add_row("DB Exists", "yes" if db_path.exists() else "no")
    table.add_row("Schema", schema_version)
    table.add_row("Save Slots", str(slot_count))
    table.add_row("Scenarios", str(len(get_available_scenarios())))
    table.add_row("Templates", str(len(get_available_product_templates())))
    table.add_row("Rivals", str(len(get_available_competitor_archetypes())))
    table.add_row("Events", str(len(get_event_registry())))
    table.add_row("Save Status", save_status)

    console.print(
        Panel(
            table,
            title="NEXUS TECH Doctor",
            border_style="cyan",
            expand=True,
        )
    )


@app.command("rename-save")
def rename_save_command(
    slot: str = typer.Option(..., "--slot", help="Existing save slot name."),
    to_slot: str = typer.Option(..., "--to-slot", help="New save slot name."),
    db_path: Path = DB_PATH_OPTION,
) -> None:
    """Rename one local save slot."""

    coordinator = SaveLoadCoordinator(db_path)
    try:
        coordinator.rename_save(slot, to_slot)
    except PersistenceError as error:
        raise_cli_persistence_error("Rename Failed", error)

    console.print(
        Panel.fit(
            f"Renamed save slot '{slot}' to '{to_slot}'.",
            title="Rename Complete",
            border_style="green",
        )
    )


@app.command("delete-save")
def delete_save_command(
    slot: str = typer.Option(..., "--slot", help="Save slot name to remove."),
    db_path: Path = DB_PATH_OPTION,
    yes: bool = typer.Option(
        False,
        "--yes",
        help="Delete without asking for confirmation.",
    ),
) -> None:
    """Delete one local save slot."""

    if not yes and not typer.confirm(f"Delete save slot '{slot}'?"):
        console.print(
            Panel.fit(
                "Delete cancelled.",
                title="No Changes",
                border_style="yellow",
            )
        )
        raise typer.Exit()

    coordinator = SaveLoadCoordinator(db_path)
    try:
        coordinator.delete_save(slot)
    except PersistenceError as error:
        raise_cli_persistence_error("Delete Failed", error)

    console.print(
        Panel.fit(
            f"Deleted save slot '{slot}'.",
            title="Delete Complete",
            border_style="green",
        )
    )


@app.command("load-game")
def load_game_command(
    db_path: Path = DB_PATH_OPTION,
    slot: str = typer.Option(DEFAULT_SAVE_SLOT, "--slot", help="Save slot name."),
) -> None:
    """Load one named save slot and continue playing."""

    coordinator = SaveLoadCoordinator(db_path)
    try:
        loaded_game = coordinator.load_game(slot)
    except PersistenceError as error:
        raise_cli_persistence_error("Load Failed", error)

    logger.debug("Loaded save slot %s from %s.", loaded_game.slot_name, db_path)
    announce_loaded_game(
        db_path=db_path,
        slot_name=loaded_game.slot_name,
        seed=loaded_game.rng.seed,
        scenario_title=loaded_game.state.scenario_title,
    )
    run_game_loop(
        state=loaded_game.state,
        rng=loaded_game.rng,
        db_path=db_path,
        slot_name=loaded_game.slot_name,
    )


@app.command("continue-last-game")
def continue_last_game_command(
    db_path: Path = DB_PATH_OPTION,
) -> None:
    """Load the most recently updated save slot."""

    coordinator = SaveLoadCoordinator(db_path)
    try:
        loaded_game = coordinator.continue_last_game()
    except PersistenceError as error:
        raise_cli_persistence_error("Load Failed", error)

    logger.debug("Continuing last save slot %s from %s.", loaded_game.slot_name, db_path)
    announce_loaded_game(
        db_path=db_path,
        slot_name=loaded_game.slot_name,
        seed=loaded_game.rng.seed,
        scenario_title=loaded_game.state.scenario_title,
    )
    run_game_loop(
        state=loaded_game.state,
        rng=loaded_game.rng,
        db_path=db_path,
        slot_name=loaded_game.slot_name,
    )


def start_new_game(
    company_name: str | None,
    product_name: str | None,
    scenario_id: str,
    difficulty_mode: DifficultyMode | None,
    campaign_goal_id: CampaignGoalId | None,
    seed: int | None,
    db_path: Path,
    slot_name: str,
) -> None:
    """Create a brand new run and enter the interactive loop."""

    validate_scenario_id(scenario_id)
    state = create_new_game(
        company_name=company_name,
        product_name=product_name,
        scenario_id=scenario_id,
        difficulty_mode=difficulty_mode,
        campaign_goal_id=campaign_goal_id,
    )
    rng = RandomSource(seed=seed)
    logger.debug(
        "Starting new game scenario=%s company=%s product=%s seed=%s slot=%s.",
        scenario_id,
        state.company.name,
        state.products[0].name,
        seed,
        slot_name,
    )
    render_intro(
        console,
        company_name=state.company.name,
        scenario_title=state.scenario_title,
        difficulty_label=state.difficulty_mode.value,
        campaign_goal_title=get_campaign_goal(state.campaign_goal_id).title,
        seed=seed,
    )
    run_game_loop(state=state, rng=rng, db_path=db_path, slot_name=slot_name)


def run_game_loop(
    state: GameState,
    rng: RandomSource,
    db_path: Path,
    slot_name: str,
) -> None:
    """Run the terminal session until the company shuts down or the user exits."""

    try:
        while not state.company.game_over and not state.victory_achieved:
            if state.pending_event is not None:
                state = handle_pending_event(state)

            render_dashboard(console, state)
            turn_ended = False

            while not turn_ended and not state.company.game_over and not state.victory_achieved:
                choice = ask_choice_input(
                    "Choose an action",
                    choices=ALL_MENU_KEYS,
                    default="26",
                    show_choices=False,
                )

                if choice in UTILITY_ACTION_KEYS:
                    state, rng, slot_name = handle_utility_action(
                        action_name=UTILITY_ACTION_KEYS[choice],
                        state=state,
                        rng=rng,
                        db_path=db_path,
                        current_slot_name=slot_name,
                    )
                    if state.pending_event is not None:
                        state = handle_pending_event(state)
                    continue

                action = ACTION_KEYS[choice]

                try:
                    context = collect_action_context(state, action)
                    if context is None:
                        continue

                    outcome = apply_action(state, action, context=context)
                except ValueError as error:
                    console.print(Panel.fit(str(error), title="Action Error", border_style="red"))
                    continue

                state = outcome.state

                if action is TurnAction.VIEW_STATUS:
                    render_dashboard(console, state)
                    continue

                if action is TurnAction.REVIEW_TEAM:
                    render_team_view(console, state)
                    continue

                if action is TurnAction.REVIEW_FINANCE:
                    render_report(console, state)
                    continue

                if action is TurnAction.REVIEW_CUSTOMERS:
                    render_customer_view(console, state)
                    continue

                if action is TurnAction.VIEW_REPORT:
                    render_report(console, state)
                    continue

                render_action_feedback(
                    console,
                    action_label=action.value,
                    message=outcome.message,
                    state=state,
                )
                turn_ended = outcome.turn_should_end

            if state.company.game_over or state.victory_achieved:
                break

            resolution = resolve_turn(state, rng)
            state = resolution.state
            render_turn_resolution(console, resolution)

        if state.victory_achieved:
            render_victory(console, state)
        else:
            render_game_over(console, state)
    except KeyboardInterrupt as error:
        console.print("\n[bold yellow]Session interrupted.[/bold yellow]")
        raise typer.Exit(code=130) from error


def collect_action_context(state: GameState, action: TurnAction) -> ActionContext | None:
    """Collect the optional context needed for a chosen action."""

    if action in (
        TurnAction.VIEW_STATUS,
        TurnAction.REVIEW_TEAM,
        TurnAction.REVIEW_FINANCE,
        TurnAction.REVIEW_CUSTOMERS,
        TurnAction.VIEW_REPORT,
        TurnAction.END_TURN,
        TurnAction.WAIT,
    ):
        return ActionContext()

    if action is TurnAction.REST_TEAM:
        if not state.employees:
            console.print(
                Panel.fit(
                    "No team has been hired yet.",
                    title="Selection Error",
                    border_style="red",
                )
            )
            return None
        return ActionContext()

    if action is TurnAction.CREATE_PRODUCT:
        product_template = choose_product_template(action)
        if product_template is None:
            return None
        return ActionContext(
            new_product_name=ask_text_input("New product name", default=product_template.title),
            new_product_template_id=product_template.template_id,
        )

    if action is TurnAction.SET_COMPANY_STRATEGY:
        strategy_key = ask_choice_input(
            "Company strategy",
            choices=["balanced", "growth", "quality", "efficiency"],
            default=state.company.strategy.value,
            show_choices=False,
            case_sensitive=False,
        )
        return ActionContext(strategy=CompanyStrategy(strategy_key))

    if action is TurnAction.SET_ROADMAP:
        roadmap_key = ask_choice_input(
            "Roadmap focus",
            choices=[
                "balanced_execution",
                "growth_push",
                "platform_rebuild",
                "premium_expansion",
                "portfolio_consolidation",
                "ai_trust_program",
                "community_growth",
                "enterprise_sales_push",
            ],
            default=state.roadmap_focus.value,
            show_choices=False,
            case_sensitive=False,
        )
        return ActionContext(roadmap_focus=RoadmapFocus(roadmap_key))

    if action is TurnAction.SET_BUDGET_STANCE:
        budget_key = ask_choice_input(
            "Budget stance",
            choices=["lean", "balanced", "aggressive"],
            default=state.quarter_plan.budget_stance.value,
            show_choices=False,
            case_sensitive=False,
        )
        return ActionContext(budget_stance=BudgetStance(budget_key))

    if action is TurnAction.HIRE_EMPLOYEE:
        candidate_seed = (state.company.current_turn * 101) + (len(state.employees) * 17)
        candidates = generate_candidate_pool(RandomSource(seed=candidate_seed))
        render_candidate_pool(console, candidates)
        candidate_choices = [str(index) for index in range(1, len(candidates) + 1)]
        selected_candidate = ask_choice_input(
            "Candidate number or custom",
            choices=[*candidate_choices, "custom"],
            default="1",
            show_choices=False,
            case_sensitive=False,
        )
        if selected_candidate != "custom":
            candidate = candidates[int(selected_candidate) - 1]
            return ActionContext(
                hire_full_name=candidate.full_name,
                hire_role=candidate.role,
                hire_seniority=candidate.seniority,
                hire_specialization=candidate.specialization,
            )

        full_name = ask_text_input("Employee full name")
        role_key = ask_choice_input(
            "Role",
            choices=["engineer", "designer", "marketer", "product_manager"],
            default="engineer",
            case_sensitive=False,
        )
        seniority_key = ask_choice_input(
            "Seniority",
            choices=["junior", "mid", "senior"],
            default="mid",
            case_sensitive=False,
        )
        default_specialization = BALANCE.employee_default_specializations[role_key]
        specialization = ask_text_input(
            "Specialization",
            default=default_specialization,
        )
        return ActionContext(
            hire_full_name=full_name,
            hire_role=EmployeeRole(role_key),
            hire_seniority=Seniority(seniority_key),
            hire_specialization=specialization,
        )

    if action is TurnAction.FIRE_EMPLOYEE:
        employee_id = choose_employee_id(state, action)
        if employee_id is None:
            return None
        return ActionContext(employee_id=employee_id)

    if action is TurnAction.UNASSIGN_EMPLOYEE:
        employee_id = choose_employee_id(state, action, assigned_only=True)
        if employee_id is None:
            return None
        return ActionContext(employee_id=employee_id)

    if action is TurnAction.ASSIGN_EMPLOYEE:
        employee_id = choose_employee_id(state, action)
        if employee_id is None:
            return None
        product_id = choose_product_id(state, action)
        if product_id is None:
            return None
        return ActionContext(employee_id=employee_id, target_product_id=product_id)

    if action in PRODUCT_TARGETED_ACTIONS:
        product_id = choose_product_id(state, action)
        if product_id is None:
            return None
        if action is TurnAction.ADJUST_PRICING:
            pricing_key = ask_choice_input(
                "Pricing tier",
                choices=["budget", "standard", "premium"],
                default="standard",
                show_choices=False,
                case_sensitive=False,
            )
            return ActionContext(
                target_product_id=product_id,
                pricing_tier=PricingTier(pricing_key),
            )
        if action is TurnAction.SET_TARGET_SEGMENT:
            product = next(product for product in state.products if product.id == product_id)
            segment_key = ask_choice_input(
                "Target segment",
                choices=["indie", "startup", "smb", "enterprise"],
                default=product.target_segment.value,
                show_choices=False,
                case_sensitive=False,
            )
            return ActionContext(
                target_product_id=product_id,
                target_segment=MarketSegment(segment_key),
            )
        return ActionContext(target_product_id=product_id)

    return ActionContext()


def choose_product_id(state: GameState, action: TurnAction) -> UUID | None:
    """Prompt the user to select a product for an action."""

    products = get_product_choices(state, active_only=True)
    if not products:
        console.print(
            Panel.fit(
                "No active products are available. Create a product first.",
                title="Selection Error",
                border_style="red",
            )
        )
        return None

    product_choices = {str(index): product for index, product in enumerate(products, start=1)}
    label = action.value.replace("_", " ")
    render_product_picker(console, products, action_label=action.value)
    selected_key = ask_choice_input(
        f"Select a product for {label}",
        choices=list(product_choices),
        default="1",
        show_choices=False,
    )
    product = product_choices[selected_key]
    logger.debug("Selected product %s for action %s.", product.name, action.value)
    console.print(
        Panel.fit(
            build_product_selection_summary(product),
            title="Target Selected",
            border_style="blue",
        )
    )
    return product.id


def choose_product_template(action: TurnAction) -> ProductTemplateDefinition | None:
    """Prompt the user to select a product template for creation."""

    templates = list(get_available_product_templates())
    if not templates:
        console.print(
            Panel.fit(
                "No product templates are available.",
                title="Selection Error",
                border_style="red",
            )
        )
        return None

    template_choices = {str(index): template for index, template in enumerate(templates, start=1)}
    render_product_template_picker(console, templates, action_label=action.value)
    selected_key = ask_choice_input(
        "Select a product template",
        choices=list(template_choices),
        default="1",
        show_choices=False,
    )
    template = template_choices[selected_key]
    logger.debug("Selected product template %s.", template.template_id)
    console.print(
        Panel.fit(
            build_product_template_summary(template),
            title="Template Selected",
            border_style="blue",
        )
    )
    return template


def choose_employee_id(
    state: GameState,
    action: TurnAction,
    assigned_only: bool | None = None,
) -> UUID | None:
    """Prompt the user to select an employee for an action."""

    employees = get_employee_choices(state, assigned_only=assigned_only)
    if not employees:
        console.print(
            Panel.fit(
                "No matching employees are available for that action.",
                title="Selection Error",
                border_style="red",
            )
        )
        return None

    employee_choices = {str(index): employee for index, employee in enumerate(employees, start=1)}
    label = action.value.replace("_", " ")
    render_employee_picker(console, employees, state.products, action_label=action.value)
    selected_key = ask_choice_input(
        f"Select an employee for {label}",
        choices=list(employee_choices),
        default="1",
        show_choices=False,
    )
    employee = employee_choices[selected_key]
    logger.debug("Selected employee %s for action %s.", employee.full_name, action.value)
    console.print(
        Panel.fit(
            build_employee_selection_summary(employee, state.products),
            title="Target Selected",
            border_style="blue",
        )
    )
    return employee.id


def handle_pending_event(state: GameState) -> GameState:
    """Prompt for an event choice and apply its effect immediately."""

    pending_event = state.pending_event
    if pending_event is None:
        return state

    render_pending_event(console, pending_event)
    option_id = choose_event_option_id(pending_event)
    outcome = resolve_pending_event(state, option_id)
    render_event_result(console, outcome.history_entry)
    return outcome.state


def choose_event_option_id(pending_event: PendingEvent) -> str:
    """Prompt for a response to a pending event."""

    option_choices = {
        str(index): option for index, option in enumerate(pending_event.options, start=1)
    }
    selected_key = ask_choice_input(
        "Choose an event response",
        choices=list(option_choices),
        default="1",
        show_choices=False,
    )
    return option_choices[selected_key].id


def ask_choice_input(
    prompt: str,
    *,
    choices: list[str],
    default: str,
    show_choices: bool,
    case_sensitive: bool = True,
) -> str:
    """Ask for a constrained choice and exit cleanly if the session input closes."""

    try:
        return Prompt.ask(
            prompt,
            console=console,
            choices=choices,
            default=default,
            show_choices=show_choices,
            case_sensitive=case_sensitive,
        )
    except EOFError as error:
        handle_prompt_abort("Input stream closed. Ending the session.", error, exit_code=1)
    except KeyboardInterrupt as error:
        handle_prompt_abort("Session interrupted.", error, exit_code=130)


def ask_text_input(prompt: str, *, default: str | None = None) -> str:
    """Ask for free-form text and keep retrying until a non-empty value is given."""

    while True:
        try:
            if default is None:
                value = Prompt.ask(
                    prompt,
                    console=console,
                    show_default=False,
                    show_choices=False,
                )
            else:
                value = Prompt.ask(
                    prompt,
                    console=console,
                    default=default,
                    show_choices=False,
                )
        except EOFError as error:
            handle_prompt_abort("Input stream closed. Ending the session.", error, exit_code=1)
        except KeyboardInterrupt as error:
            handle_prompt_abort("Session interrupted.", error, exit_code=130)

        cleaned_value = value.strip()
        if cleaned_value:
            return cleaned_value

        console.print(
            Panel.fit(
                "Enter a value before continuing.",
                title="Input Needed",
                border_style="yellow",
            )
        )


def handle_prompt_abort(message: str, error: BaseException, *, exit_code: int) -> None:
    """Render a clean prompt-abort message and stop the CLI."""

    console.print(Panel.fit(message, title="Session Ended", border_style="yellow"))
    raise typer.Exit(code=exit_code) from error


def build_product_selection_summary(product: Product) -> str:
    """Show concise per-product stats before an action."""

    return (
        f"{product.name}\n"
        f"Stage: {product.lifecycle_stage.value} | Users: {product.user_count} | "
        f"Quality: {product.quality} | Bugs: {product.bug_level} | "
        f"Fit: {product.market_fit} | Debt: {product.technical_debt} | "
        f"Segment: {product.target_segment.value} | Pricing: {product.pricing_tier.value}"
    )


def build_product_template_summary(template: ProductTemplateDefinition) -> str:
    """Show concise template stats before creating a product."""

    return (
        f"{template.title}\n"
        f"{template.description}\n"
        f"Stage: {template.lifecycle_stage.value} | Quality: {template.quality} | "
        f"Bugs: {template.bug_level} | Fit: {template.market_fit} | "
        f"Debt: {template.technical_debt} | Segment: {template.target_segment.value} | "
        f"Pricing: {template.pricing_tier.value}"
    )


def build_employee_selection_summary(
    employee: Employee,
    products: list[Product],
) -> str:
    """Show concise employee stats before an action."""

    product_names = {product.id: product.name for product in products}
    assignment_name = product_names.get(employee.assigned_product_id, "unassigned")
    return (
        f"{employee.full_name}\n"
        f"Role: {employee.role.value} | Seniority: {employee.seniority.value} | "
        f"Energy: {employee.energy} | Morale: {employee.morale} | "
        f"Assignment: {assignment_name}"
    )


def handle_utility_action(
    action_name: str,
    state: GameState,
    rng: RandomSource,
    db_path: Path,
    current_slot_name: str,
) -> tuple[GameState, RandomSource, str]:
    """Handle non-simulation utility actions from the CLI menu."""

    coordinator = SaveLoadCoordinator(db_path)

    if action_name == "save_game":
        slot_name = ask_text_input("Save slot", default=current_slot_name)
        try:
            coordinator.save_game(slot_name=slot_name, state=state, rng=rng)
        except PersistenceError as error:
            console.print(Panel.fit(str(error), title="Save Failed", border_style="red"))
            return state, rng, current_slot_name

        logger.debug("Saved game to slot %s at %s.", slot_name, db_path)
        console.print(
            Panel.fit(
                f"Saved game to slot '{slot_name}' at {db_path}.",
                title="Save Complete",
                border_style="green",
            )
        )
        return state, rng, slot_name

    if action_name == "load_game":
        slot_name = ask_text_input("Load slot", default=current_slot_name)
        try:
            loaded_game = coordinator.load_game(slot_name)
        except PersistenceError as error:
            console.print(Panel.fit(str(error), title="Load Failed", border_style="red"))
            return state, rng, current_slot_name

        logger.debug("Loaded game from slot %s at %s.", loaded_game.slot_name, db_path)
        console.print(
            Panel.fit(
                f"Loaded slot '{loaded_game.slot_name}' from {db_path}.",
                title="Load Complete",
                border_style="green",
            )
        )
        return loaded_game.state, loaded_game.rng, loaded_game.slot_name

    if action_name == "show_guide":
        render_quick_guide(console)
        return state, rng, current_slot_name

    if action_name == "show_glossary":
        render_glossary(console)
        return state, rng, current_slot_name

    if action_name == "show_tutorial":
        render_tutorial(console)
        return state, rng, current_slot_name

    raise ValueError(f"Unsupported utility action: {action_name}")


def announce_loaded_game(
    db_path: Path,
    slot_name: str,
    seed: int | None,
    scenario_title: str,
) -> None:
    """Print a concise load banner before entering the loop."""

    seed_text = seed if seed is not None else "random"
    console.print(
        Panel.fit(
            (
                f"Loaded slot '{slot_name}' from {db_path}\n"
                f"Scenario: {scenario_title}\n"
                f"Seed: {seed_text}"
            ),
            title="Continue Game",
            border_style="green",
        )
    )


def configure_cli(debug: bool) -> None:
    """Configure console logging and traceback behavior for the CLI session."""

    global console, DEBUG_MODE

    console = Console(highlight=False, soft_wrap=True)
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.WARNING,
        format="%(message)s",
        handlers=[
            RichHandler(
                console=console,
                show_time=False,
                show_path=debug,
                markup=True,
                rich_tracebacks=debug,
                tracebacks_show_locals=debug,
            )
        ],
        force=True,
    )
    DEBUG_MODE = debug
    if debug:
        install_rich_traceback(console=console, show_locals=True)
        logger.debug("Debug mode enabled.")


def raise_cli_persistence_error(title: str, error: PersistenceError) -> None:
    """Render a persistence failure and exit the command."""

    logger.error("%s: %s", title, error)
    console.print(Panel.fit(str(error), title=title, border_style="red"))
    raise typer.Exit(code=1)


def validate_scenario_id(scenario_id: str) -> None:
    """Exit cleanly when a requested scenario id is unknown."""

    available_ids = {scenario.scenario_id for scenario in get_available_scenarios()}
    if scenario_id in available_ids:
        return
    examples = "\n".join(f"- {scenario_id}" for scenario_id in sorted(available_ids)[:6])
    console.print(
        Panel.fit(
            (
                f"Unknown scenario '{scenario_id}'.\n"
                f"Example scenario ids:\n{examples}\n"
                "Run `nexus-tech list-scenarios` to inspect the full catalog."
            ),
            title="Invalid Scenario",
            border_style="red",
        )
    )
    raise typer.Exit(code=1)


def resolve_scenario_ids(scenario_ids: list[str] | None) -> list[str]:
    """Resolve optional scenario CLI input and validate all ids."""

    if scenario_ids is None:
        return [entry.scenario_id for entry in get_available_scenarios()]
    for scenario_id in scenario_ids:
        validate_scenario_id(scenario_id)
    return scenario_ids


def main() -> None:
    """CLI wrapper used by `python -m` and console scripts."""

    try:
        app()
    except typer.Exit:
        raise
    except Exception as error:
        if DEBUG_MODE:
            console.print_exception(show_locals=True)
        else:
            console.print(
                Panel.fit(
                    f"{type(error).__name__}: {error}",
                    title="Unexpected Error",
                    border_style="red",
                )
            )
        raise typer.Exit(code=1) from None


if __name__ == "__main__":
    main()
