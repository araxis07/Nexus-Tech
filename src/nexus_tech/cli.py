"""Typer CLI entrypoint for NEXUS TECH."""

from __future__ import annotations

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
from nexus_tech.presentation.dashboard import (
    render_dashboard,
    render_event_result,
    render_game_over,
    render_intro,
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

PRODUCT_TARGETED_ACTIONS = {
    TurnAction.IMPROVE_QUALITY,
    TurnAction.ADD_FEATURE,
    TurnAction.REDUCE_TECHNICAL_DEBT,
    TurnAction.MARKET_PRODUCT,
    TurnAction.SUNSET_PRODUCT,
}


@app.command()
def play(
    company_name: str = typer.Option("NEXUS TECH", "--company-name", help="Company display name."),
    product_name: str = typer.Option("Nexus One", "--product-name", help="Initial product name."),
    seed: Optional[int] = typer.Option(None, "--seed", help="Seed for reproducible simulation."),
) -> None:
    """Start a new local game."""

    state = create_new_game(company_name=company_name, product_name=product_name)
    rng = RandomSource(seed=seed)

    render_intro(console, company_name=company_name, seed=seed)

    try:
        while not state.company.game_over:
            render_dashboard(console, state)
            turn_ended = False

            while not turn_ended and not state.company.game_over:
                choice = Prompt.ask("Choose an action", choices=list(ACTION_KEYS), default="15")
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

            if state.pending_event is not None:
                state = handle_pending_event(state)

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


def main() -> None:
    """CLI wrapper used by `python -m` and console scripts."""

    app()


if __name__ == "__main__":
    main()
