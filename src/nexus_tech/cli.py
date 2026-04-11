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
from rich.traceback import install as install_rich_traceback

from nexus_tech.config import (
    DEFAULT_DATABASE_PATH,
    DEFAULT_SCENARIO_ID,
    DEMO_SEED_EXAMPLE,
)
from nexus_tech.content.models import ProductTemplateDefinition
from nexus_tech.domain.models import (
    CompanyStrategy,
    Employee,
    EmployeeRole,
    GameState,
    PendingEvent,
    PricingTier,
    Product,
    Seniority,
    TurnAction,
)
from nexus_tech.persistence.errors import PersistenceError
from nexus_tech.persistence.save_coordinator import DEFAULT_SAVE_SLOT, SaveLoadCoordinator
from nexus_tech.presentation.dashboard import (
    render_action_feedback,
    render_dashboard,
    render_employee_picker,
    render_event_result,
    render_game_over,
    render_intro,
    render_pending_event,
    render_product_picker,
    render_product_template_picker,
    render_scenario_catalog,
    render_team_view,
    render_turn_resolution,
)
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.engine import (
    ActionContext,
    apply_action,
    create_new_game,
    get_employee_choices,
    get_product_choices,
    resolve_turn,
)
from nexus_tech.simulation.events import resolve_pending_event
from nexus_tech.simulation.randomness import RandomSource
from nexus_tech.simulation.scenarios import get_available_product_templates, get_available_scenarios

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

ACTION_KEYS = {
    "1": TurnAction.CREATE_PRODUCT,
    "2": TurnAction.IMPROVE_QUALITY,
    "3": TurnAction.ADD_FEATURE,
    "4": TurnAction.REDUCE_TECHNICAL_DEBT,
    "5": TurnAction.MARKET_PRODUCT,
    "6": TurnAction.ADJUST_PRICING,
    "7": TurnAction.SUNSET_PRODUCT,
    "8": TurnAction.SET_COMPANY_STRATEGY,
    "9": TurnAction.HIRE_EMPLOYEE,
    "10": TurnAction.FIRE_EMPLOYEE,
    "11": TurnAction.ASSIGN_EMPLOYEE,
    "12": TurnAction.UNASSIGN_EMPLOYEE,
    "13": TurnAction.REST_TEAM,
    "14": TurnAction.REVIEW_TEAM,
    "15": TurnAction.WAIT,
    "16": TurnAction.VIEW_STATUS,
    "17": TurnAction.END_TURN,
}
UTILITY_ACTION_KEYS = {
    "18": "save_game",
    "19": "load_game",
}
ALL_MENU_KEYS = list(ACTION_KEYS) + list(UTILITY_ACTION_KEYS)

PRODUCT_TARGETED_ACTIONS = {
    TurnAction.IMPROVE_QUALITY,
    TurnAction.ADD_FEATURE,
    TurnAction.REDUCE_TECHNICAL_DEBT,
    TurnAction.MARKET_PRODUCT,
    TurnAction.ADJUST_PRICING,
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
        seed=seed,
        db_path=db_path,
        slot_name=slot,
    )


@app.command("list-scenarios")
def list_scenarios_command() -> None:
    """Print the available starting scenarios."""

    render_scenario_catalog(console, get_available_scenarios())


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
    seed: int | None,
    db_path: Path,
    slot_name: str,
) -> None:
    """Create a brand new run and enter the interactive loop."""

    state = create_new_game(
        company_name=company_name,
        product_name=product_name,
        scenario_id=scenario_id,
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
        while not state.company.game_over:
            if state.pending_event is not None:
                state = handle_pending_event(state)

            render_dashboard(console, state)
            turn_ended = False

            while not turn_ended and not state.company.game_over:
                choice = ask_choice_input(
                    "Choose an action",
                    choices=ALL_MENU_KEYS,
                    default="17",
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

                render_action_feedback(
                    console,
                    action_label=action.value,
                    message=outcome.message,
                    state=state,
                )
                turn_ended = outcome.turn_should_end

            if state.company.game_over:
                break

            resolution = resolve_turn(state, rng)
            state = resolution.state
            render_turn_resolution(console, resolution)

        render_game_over(console, state)
    except KeyboardInterrupt as error:
        console.print("\n[bold yellow]Session interrupted.[/bold yellow]")
        raise typer.Exit(code=130) from error


def collect_action_context(state: GameState, action: TurnAction) -> ActionContext | None:
    """Collect the optional context needed for a chosen action."""

    if action in (
        TurnAction.VIEW_STATUS,
        TurnAction.REVIEW_TEAM,
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

    if action is TurnAction.HIRE_EMPLOYEE:
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

    template_choices = {
        str(index): template for index, template in enumerate(templates, start=1)
    }
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

    employee_choices = {
        str(index): employee for index, employee in enumerate(employees, start=1)
    }
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
        f"Pricing: {product.pricing_tier.value}"
    )


def build_product_template_summary(template: ProductTemplateDefinition) -> str:
    """Show concise template stats before creating a product."""

    return (
        f"{template.title}\n"
        f"{template.description}\n"
        f"Stage: {template.lifecycle_stage.value} | Quality: {template.quality} | "
        f"Bugs: {template.bug_level} | Fit: {template.market_fit} | "
        f"Debt: {template.technical_debt} | Pricing: {template.pricing_tier.value}"
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
        raise typer.Exit(code=1) from error


if __name__ == "__main__":
    main()
