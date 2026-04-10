"""Typer CLI entrypoint for NEXUS TECH."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from uuid import UUID

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from nexus_tech.domain.models import (
    Employee,
    EmployeeRole,
    GameState,
    PendingEvent,
    Product,
    Seniority,
    TurnAction,
)
from nexus_tech.persistence.errors import PersistenceError
from nexus_tech.persistence.save_coordinator import DEFAULT_SAVE_SLOT, SaveLoadCoordinator
from nexus_tech.presentation.dashboard import (
    render_dashboard,
    render_event_result,
    render_game_over,
    render_intro,
    render_pending_event,
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

app = typer.Typer(add_completion=False, help="NEXUS TECH terminal management simulation.")
console = Console()
DEFAULT_DB_PATH = Path("nexus-tech.db")
DB_PATH_OPTION = typer.Option(DEFAULT_DB_PATH, "--db-path", help="SQLite save file path.")

ACTION_KEYS = {
    "1": TurnAction.CREATE_PRODUCT,
    "2": TurnAction.IMPROVE_QUALITY,
    "3": TurnAction.ADD_FEATURE,
    "4": TurnAction.REDUCE_TECHNICAL_DEBT,
    "5": TurnAction.MARKET_PRODUCT,
    "6": TurnAction.SUNSET_PRODUCT,
    "7": TurnAction.HIRE_EMPLOYEE,
    "8": TurnAction.FIRE_EMPLOYEE,
    "9": TurnAction.ASSIGN_EMPLOYEE,
    "10": TurnAction.UNASSIGN_EMPLOYEE,
    "11": TurnAction.REST_TEAM,
    "12": TurnAction.REVIEW_TEAM,
    "13": TurnAction.WAIT,
    "14": TurnAction.VIEW_STATUS,
    "15": TurnAction.END_TURN,
}
UTILITY_ACTION_KEYS = {
    "16": "save_game",
    "17": "load_game",
}
ALL_MENU_KEYS = list(ACTION_KEYS) + list(UTILITY_ACTION_KEYS)

PRODUCT_TARGETED_ACTIONS = {
    TurnAction.IMPROVE_QUALITY,
    TurnAction.ADD_FEATURE,
    TurnAction.REDUCE_TECHNICAL_DEBT,
    TurnAction.MARKET_PRODUCT,
    TurnAction.SUNSET_PRODUCT,
}


@app.callback(invoke_without_command=True)
def root(
    ctx: typer.Context,
    company_name: str = typer.Option("NEXUS TECH", "--company-name", help="Company display name."),
    product_name: str = typer.Option("Nexus One", "--product-name", help="Initial product name."),
    seed: Optional[int] = typer.Option(None, "--seed", help="Seed for reproducible simulation."),
    db_path: Path = DB_PATH_OPTION,
    slot: str = typer.Option(DEFAULT_SAVE_SLOT, "--slot", help="Default save slot name."),
) -> None:
    """Start a new local game when no subcommand is given."""

    if ctx.invoked_subcommand is not None:
        return
    start_new_game(
        company_name=company_name,
        product_name=product_name,
        seed=seed,
        db_path=db_path,
        slot_name=slot,
    )


@app.command("new-game")
def new_game_command(
    company_name: str = typer.Option("NEXUS TECH", "--company-name", help="Company display name."),
    product_name: str = typer.Option("Nexus One", "--product-name", help="Initial product name."),
    seed: Optional[int] = typer.Option(None, "--seed", help="Seed for reproducible simulation."),
    db_path: Path = DB_PATH_OPTION,
    slot: str = typer.Option(DEFAULT_SAVE_SLOT, "--slot", help="Default save slot name."),
) -> None:
    """Start a brand new local game."""

    start_new_game(
        company_name=company_name,
        product_name=product_name,
        seed=seed,
        db_path=db_path,
        slot_name=slot,
    )


@app.command("play", hidden=True)
def play_alias(
    company_name: str = typer.Option("NEXUS TECH", "--company-name", help="Company display name."),
    product_name: str = typer.Option("Nexus One", "--product-name", help="Initial product name."),
    seed: Optional[int] = typer.Option(None, "--seed", help="Seed for reproducible simulation."),
    db_path: Path = DB_PATH_OPTION,
    slot: str = typer.Option(DEFAULT_SAVE_SLOT, "--slot", help="Default save slot name."),
) -> None:
    """Backward-compatible alias for starting a new game."""

    start_new_game(
        company_name=company_name,
        product_name=product_name,
        seed=seed,
        db_path=db_path,
        slot_name=slot,
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

    announce_loaded_game(
        db_path=db_path,
        slot_name=loaded_game.slot_name,
        seed=loaded_game.rng.seed,
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

    announce_loaded_game(
        db_path=db_path,
        slot_name=loaded_game.slot_name,
        seed=loaded_game.rng.seed,
    )
    run_game_loop(
        state=loaded_game.state,
        rng=loaded_game.rng,
        db_path=db_path,
        slot_name=loaded_game.slot_name,
    )


def start_new_game(
    company_name: str,
    product_name: str,
    seed: Optional[int],
    db_path: Path,
    slot_name: str,
) -> None:
    """Create a brand new run and enter the interactive loop."""

    state = create_new_game(company_name=company_name, product_name=product_name)
    rng = RandomSource(seed=seed)
    render_intro(console, company_name=company_name, seed=seed)
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
                choice = Prompt.ask("Choose an action", choices=ALL_MENU_KEYS, default="15")

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

                console.print(Panel.fit(outcome.message, title="Action", border_style="cyan"))
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


def collect_action_context(state: GameState, action: TurnAction) -> Optional[ActionContext]:
    """Collect the optional context needed for a chosen action."""

    if action in (
        TurnAction.VIEW_STATUS,
        TurnAction.REVIEW_TEAM,
        TurnAction.END_TURN,
        TurnAction.WAIT,
    ):
        return ActionContext()

    if action is TurnAction.CREATE_PRODUCT:
        return ActionContext(new_product_name=Prompt.ask("New product name").strip())

    if action is TurnAction.HIRE_EMPLOYEE:
        full_name = Prompt.ask("Employee full name").strip()
        role_key = Prompt.ask(
            "Role",
            choices=["engineer", "designer", "marketer", "product_manager"],
            default="engineer",
        )
        seniority_key = Prompt.ask(
            "Seniority",
            choices=["junior", "mid", "senior"],
            default="mid",
        )
        default_specialization = BALANCE.employee_default_specializations[role_key]
        specialization = Prompt.ask(
            "Specialization",
            default=default_specialization,
        ).strip()
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
        return ActionContext(target_product_id=product_id)

    if action is TurnAction.REST_TEAM and not state.employees:
        console.print(
            Panel.fit(
                "No team has been hired yet.",
                title="Selection Error",
                border_style="red",
            )
        )
        return None

    return ActionContext()


def choose_product_id(state: GameState, action: TurnAction) -> Optional[UUID]:
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
    selected_key = Prompt.ask(
        f"Select a product for {label}",
        choices=list(product_choices),
        default="1",
    )
    product = product_choices[selected_key]
    console.print(
        Panel.fit(
            build_product_selection_summary(product),
            title="Target Selected",
            border_style="blue",
        )
    )
    return product.id


def choose_employee_id(
    state: GameState,
    action: TurnAction,
    assigned_only: Optional[bool] = None,
) -> Optional[UUID]:
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
    selected_key = Prompt.ask(
        f"Select an employee for {label}",
        choices=list(employee_choices),
        default="1",
    )
    employee = employee_choices[selected_key]
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
    selected_key = Prompt.ask(
        "Choose an event response",
        choices=list(option_choices),
        default="1",
    )
    return option_choices[selected_key].id


def build_product_selection_summary(product: Product) -> str:
    """Show concise per-product stats before an action."""

    return (
        f"{product.name}\n"
        f"Stage: {product.lifecycle_stage.value} | Users: {product.user_count} | "
        f"Quality: {product.quality} | Bugs: {product.bug_level} | "
        f"Fit: {product.market_fit} | Debt: {product.technical_debt}"
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
        slot_name = Prompt.ask("Save slot", default=current_slot_name).strip() or current_slot_name
        try:
            coordinator.save_game(slot_name=slot_name, state=state, rng=rng)
        except PersistenceError as error:
            console.print(Panel.fit(str(error), title="Save Failed", border_style="red"))
            return state, rng, current_slot_name

        console.print(
            Panel.fit(
                f"Saved game to slot '{slot_name}' at {db_path}.",
                title="Save Complete",
                border_style="green",
            )
        )
        return state, rng, slot_name

    if action_name == "load_game":
        slot_name = Prompt.ask("Load slot", default=current_slot_name).strip() or current_slot_name
        try:
            loaded_game = coordinator.load_game(slot_name)
        except PersistenceError as error:
            console.print(Panel.fit(str(error), title="Load Failed", border_style="red"))
            return state, rng, current_slot_name

        console.print(
            Panel.fit(
                f"Loaded slot '{loaded_game.slot_name}' from {db_path}.",
                title="Load Complete",
                border_style="green",
            )
        )
        return loaded_game.state, loaded_game.rng, loaded_game.slot_name

    raise ValueError(f"Unsupported utility action: {action_name}")


def announce_loaded_game(db_path: Path, slot_name: str, seed: Optional[int]) -> None:
    """Print a concise load banner before entering the loop."""

    seed_text = seed if seed is not None else "random"
    console.print(
        Panel.fit(
            f"Loaded slot '{slot_name}' from {db_path}\nSeed: {seed_text}",
            title="Continue Game",
            border_style="green",
        )
    )


def raise_cli_persistence_error(title: str, error: PersistenceError) -> None:
    """Render a persistence failure and exit the command."""

    console.print(Panel.fit(str(error), title=title, border_style="red"))
    raise typer.Exit(code=1)


def main() -> None:
    """CLI wrapper used by `python -m` and console scripts."""

    app()


if __name__ == "__main__":
    main()
