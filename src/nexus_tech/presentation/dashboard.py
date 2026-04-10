"""Rich-powered terminal presentation for the game."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from rich import box
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table

from nexus_tech.domain.models import (
    Employee,
    EventHistoryEntry,
    GameState,
    PendingEvent,
    Product,
)
from nexus_tech.domain.money import format_money, format_rate
from nexus_tech.simulation.engine import TurnResolution, get_total_users
from nexus_tech.simulation.team import calculate_effective_productivity, calculate_team_condition


def render_intro(console: Console, company_name: str, seed: int | None) -> None:
    """Print the opening game banner."""

    seed_text = f"Seed: {seed}" if seed is not None else "Seed: random"
    console.print(
        Panel.fit(
            (
                f"[bold cyan]NEXUS TECH[/bold cyan]\n"
                f"Company: [bold]{company_name}[/bold]\n"
                f"{seed_text}\n\n"
                "Run a focused local software company from the terminal.\n"
                "Build products, manage the team, react to events, and keep cash alive."
            ),
            title="Phase 7 Hardened Build",
            border_style="cyan",
        )
    )


def render_dashboard(console: Console, state: GameState) -> None:
    """Render the main per-turn dashboard."""

    console.print(_build_turn_header_panel(state))
    console.print(
        Columns(
            [
                _build_company_panel(state),
                _build_totals_panel(state),
                _build_team_summary_panel(state),
            ],
            equal=True,
            expand=True,
        )
    )
    console.print(
        Panel(
            _build_portfolio_table(state),
            title="Product Portfolio",
            border_style="yellow",
            expand=True,
        )
    )
    console.print(_build_dashboard_team_panel(state))
    console.print(
        Columns(
            [
                _build_action_menu_panel(),
                _build_event_notification_panel(state),
            ],
            equal=True,
            expand=True,
        )
    )


def render_team_view(console: Console, state: GameState) -> None:
    """Render the dedicated team review table."""

    console.print(
        Columns(
            [
                _build_team_summary_panel(state),
                _build_team_detail_panel(state),
            ],
            equal=False,
            expand=True,
        )
    )


def render_turn_resolution(console: Console, resolution: TurnResolution) -> None:
    """Render the end-of-turn summary."""

    console.print(_build_turn_summary_panel(resolution))
    console.print(
        Panel(
            _build_turn_product_table(resolution),
            title="Portfolio Results",
            border_style="blue",
            expand=True,
        )
    )
    if resolution.event_history_entry is not None:
        console.print(_build_event_result_panel(resolution.event_history_entry))
    if resolution.pending_event is not None:
        console.print(_build_pending_event_panel(resolution.pending_event))
    console.print(Panel(resolution.narrative, title="Outlook", border_style="green"))


def render_pending_event(console: Console, pending_event: PendingEvent) -> None:
    """Render a pending event with its available responses."""

    console.print(_build_pending_event_panel(pending_event))


def render_event_result(console: Console, history_entry: EventHistoryEntry) -> None:
    """Render the outcome of a resolved event."""

    console.print(_build_event_result_panel(history_entry))


def render_action_feedback(
    console: Console,
    *,
    action_label: str,
    message: str,
    state: GameState,
) -> None:
    """Render a concise action result panel."""

    summary = Table.grid(padding=(0, 1))
    summary.add_row("Action", action_label.replace("_", " "))
    summary.add_row("Result", message)
    summary.add_row(
        "State",
        (
            f"Actions left {state.action_points_remaining} | "
            f"Cash {format_money(state.company.cash_on_hand)} | "
            f"Reputation {state.company.reputation}"
        ),
    )
    console.print(Panel(summary, title="Action Summary", border_style="cyan"))


def render_product_picker(console: Console, products: list[Product], action_label: str) -> None:
    """Render a compact product selection table before prompting."""

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("#", justify="center", style="bold cyan")
    table.add_column("Product", style="bold")
    table.add_column("Stage")
    table.add_column("Users", justify="right")
    table.add_column("Q", justify="right")
    table.add_column("B", justify="right")
    table.add_column("Fit", justify="right")
    table.add_column("Debt", justify="right")

    for index, product in enumerate(products, start=1):
        table.add_row(
            str(index),
            product.name,
            product.lifecycle_stage.value,
            str(product.user_count),
            str(product.quality),
            str(product.bug_level),
            str(product.market_fit),
            str(product.technical_debt),
        )

    console.print(
        Panel(
            table,
            title=f"Product Target: {action_label.replace('_', ' ')}",
            border_style="blue",
            expand=True,
        )
    )


def render_employee_picker(
    console: Console,
    employees: list[Employee],
    products: list[Product],
    action_label: str,
) -> None:
    """Render a compact employee selection table before prompting."""

    product_names = {product.id: product.name for product in products}
    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("#", justify="center", style="bold cyan")
    table.add_column("Employee", style="bold")
    table.add_column("Role")
    table.add_column("Assignment")
    table.add_column("Energy", justify="right")
    table.add_column("Morale", justify="right")
    table.add_column("Eff", justify="right")

    for index, employee in enumerate(employees, start=1):
        table.add_row(
            str(index),
            employee.full_name,
            employee.role.value,
            product_names.get(employee.assigned_product_id, "unassigned"),
            str(employee.energy),
            str(employee.morale),
            str(calculate_effective_productivity(employee)),
        )

    console.print(
        Panel(
            table,
            title=f"Employee Target: {action_label.replace('_', ' ')}",
            border_style="blue",
            expand=True,
        )
    )


def render_game_over(console: Console, state: GameState) -> None:
    """Render the losing state."""

    team_condition = calculate_team_condition(state.employees)
    console.print(
        Panel.fit(
            (
                "[bold red]Game Over[/bold red]\n"
                f"Cash on hand: {format_money(state.company.cash_on_hand)}\n"
                f"Reputation: {state.company.reputation}\n"
                f"Active users: {get_total_users(state)}\n"
                f"Headcount: {team_condition.headcount}"
            ),
            title="Company Shutdown",
            border_style="red",
        )
    )


def _build_turn_header_panel(state: GameState) -> Panel:
    body = (
        f"[bold white]Turn {state.company.current_turn}[/bold white]\n"
        f"[cyan]Actions Left:[/cyan] {state.action_points_remaining}\n"
        "Use the action menu below, then end the turn when you are ready to simulate."
    )
    return Panel.fit(body, title="Turn Control", border_style="blue")


def _build_company_panel(state: GameState) -> Panel:
    table = Table.grid(padding=(0, 1))
    table.add_row("Name", state.company.name)
    table.add_row("Cash", format_money(state.company.cash_on_hand))
    table.add_row("Reputation", str(state.company.reputation))
    table.add_row("Status", "Game Over" if state.company.game_over else "Operating")
    return Panel(table, title="Company Overview", border_style="magenta", expand=True)


def _build_totals_panel(state: GameState) -> Panel:
    active_products = [product for product in state.products if product.is_active]
    table = Table.grid(padding=(0, 1))
    table.add_row("Active Products", str(len(active_products)))
    table.add_row("Portfolio Users", str(get_total_users(state)))
    table.add_row("Sunset Products", str(len(state.products) - len(active_products)))
    return Panel(table, title="Portfolio Summary", border_style="yellow", expand=True)


def _build_team_summary_panel(state: GameState) -> Panel:
    team_condition = calculate_team_condition(state.employees)
    average_energy = "-" if team_condition.headcount == 0 else str(team_condition.average_energy)
    average_morale = "-" if team_condition.headcount == 0 else str(team_condition.average_morale)
    table = Table.grid(padding=(0, 1))
    table.add_row("Headcount", str(team_condition.headcount))
    table.add_row("Assigned", str(team_condition.assigned_headcount))
    table.add_row("Salary Burn", format_money(team_condition.total_salary_cost))
    table.add_row("Avg Energy", average_energy)
    table.add_row("Avg Morale", average_morale)
    table.add_row("Burned Out", str(team_condition.burned_out_count))
    return Panel(table, title="Team Summary", border_style="cyan", expand=True)


def _build_portfolio_table(state: GameState) -> Table:
    assignment_counts = _count_assignments_by_product(state)
    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("#", justify="center", style="bold cyan")
    table.add_column("Product", style="bold")
    table.add_column("Stage")
    table.add_column("Status")
    table.add_column("Users", justify="right")
    table.add_column("Team", justify="right")
    table.add_column("Q", justify="right")
    table.add_column("B", justify="right")
    table.add_column("Fit", justify="right")
    table.add_column("Debt", justify="right")
    table.add_column("Maint", justify="right")
    table.add_column("Aq", justify="right")
    table.add_column("Ch", justify="right")

    for index, product in enumerate(state.products, start=1):
        table.add_row(
            str(index),
            product.name,
            product.lifecycle_stage.value,
            "active" if product.is_active else "sunset",
            str(product.user_count),
            str(assignment_counts.get(product.id, 0)),
            str(product.quality),
            str(product.bug_level),
            str(product.market_fit),
            str(product.technical_debt),
            format_money(product.maintenance_cost),
            format_rate(product.acquisition_rate),
            format_rate(product.churn_rate),
        )

    return table


def _build_dashboard_team_panel(state: GameState) -> Panel:
    if not state.employees:
        return Panel(
            "No employees hired yet. Use [bold]7[/bold] to start building the team.",
            title="Team Table",
            border_style="cyan",
            expand=True,
        )

    return Panel(
        _build_team_table(state, compact=True),
        title="Team Table",
        border_style="cyan",
        expand=True,
    )


def _build_team_detail_panel(state: GameState) -> Panel:
    if not state.employees:
        return Panel(
            "No employees hired yet.",
            title="Team Review",
            border_style="cyan",
            expand=True,
        )

    return Panel(
        _build_team_table(state, compact=False),
        title="Team Review",
        border_style="cyan",
        expand=True,
    )


def _build_team_table(state: GameState, *, compact: bool) -> Table:
    product_names = {product.id: product.name for product in state.products}
    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("#", justify="center", style="bold cyan")
    table.add_column("Employee", style="bold")
    table.add_column("Role")
    table.add_column("Assignment")
    table.add_column("Energy", justify="right")
    table.add_column("Morale", justify="right")
    table.add_column("Eff", justify="right")

    if not compact:
        table.add_column("Seniority")
        table.add_column("Spec")
        table.add_column("Salary", justify="right")

    for index, employee in enumerate(state.employees, start=1):
        assignment_name = product_names.get(employee.assigned_product_id, "unassigned")
        row = [
            str(index),
            employee.full_name,
            employee.role.value,
            assignment_name,
            str(employee.energy),
            str(employee.morale),
            str(calculate_effective_productivity(employee)),
        ]
        if not compact:
            row.extend(
                [
                    employee.seniority.value,
                    employee.specialization,
                    format_money(employee.salary),
                ]
            )
        table.add_row(*row)

    return table


def _build_action_menu_panel() -> Panel:
    primary_actions = Table(box=box.SIMPLE_HEAVY, expand=True)
    primary_actions.add_column("Key", justify="center", style="bold cyan")
    primary_actions.add_column("Action", style="bold")
    primary_actions.add_column("Effect")
    primary_actions.add_row("1", "create_product", "Launch a new prototype.")
    primary_actions.add_row("2", "improve_quality", "Improve product quality.")
    primary_actions.add_row("3", "add_feature", "Ship faster and risk new bugs.")
    primary_actions.add_row("4", "reduce_technical_debt", "Stabilise future delivery.")
    primary_actions.add_row("5", "market_product", "Spend cash for acquisition.")
    primary_actions.add_row("6", "sunset_product", "Retire a weak product.")
    primary_actions.add_row("7", "hire_employee", "Add capability and salary burn.")
    primary_actions.add_row("8", "fire_employee", "Remove salary burden.")
    primary_actions.add_row("9", "assign_employee", "Put someone on a product.")
    primary_actions.add_row("10", "unassign_employee", "Pull someone off product work.")
    primary_actions.add_row("11", "rest_team", "Recover energy and morale.")
    primary_actions.add_row("12", "review_team", "Open the detailed team view.")
    primary_actions.add_row("13", "wait", "Hold position for this action.")
    primary_actions.add_row("14", "view_status", "Refresh the dashboard.")
    primary_actions.add_row("15", "end_turn", "Run the simulation tick.")

    utility_actions = Table(box=box.SIMPLE_HEAVY, expand=True)
    utility_actions.add_column("Key", justify="center", style="bold cyan")
    utility_actions.add_column("Utility", style="bold")
    utility_actions.add_column("Purpose")
    utility_actions.add_row("16", "save_game", "Write the current run to SQLite.")
    utility_actions.add_row("17", "load_game", "Resume a saved slot from SQLite.")

    content = Group(
        "[bold]Turn Actions[/bold]",
        primary_actions,
        "",
        "[bold]Run Controls[/bold]",
        utility_actions,
    )
    return Panel(content, title="Action Menu", border_style="blue", expand=True)


def _build_event_notification_panel(state: GameState) -> Panel:
    if state.pending_event is not None:
        body = (
            f"[bold]{state.pending_event.title}[/bold]\n"
            f"{state.pending_event.description}\n"
            "Resolve it before taking more actions."
        )
        return Panel(body, title="Event Notification", border_style="yellow", expand=True)

    if not state.event_history:
        return Panel(
            "No major business events have fired yet.",
            title="Event Notification",
            border_style="yellow",
            expand=True,
        )

    recent_history = state.event_history[-3:]
    body = "\n\n".join(
        f"[bold]{entry.title}[/bold] ({entry.selected_option_label})\n{entry.result_text}"
        for entry in reversed(recent_history)
    )
    return Panel(body, title="Event Notification", border_style="yellow", expand=True)


def _build_turn_summary_panel(resolution: TurnResolution) -> Panel:
    content = Columns(
        [
            _build_turn_finance_table(resolution),
            _build_turn_operating_table(resolution),
        ],
        equal=True,
        expand=True,
    )
    return Panel(
        content,
        title=f"Turn {resolution.resolved_turn} Summary",
        border_style="green",
        expand=True,
    )


def _build_turn_finance_table(resolution: TurnResolution) -> Table:
    table = Table.grid(padding=(0, 1))
    table.add_row("Total Revenue", format_money(resolution.total_revenue))
    table.add_row("Baseline Cost", format_money(resolution.baseline_operating_cost))
    table.add_row("Product Costs", format_money(resolution.total_product_operating_cost))
    table.add_row("Salary Cost", format_money(resolution.total_salary_cost))
    table.add_row("Total Operating Cost", format_money(resolution.total_operating_cost))
    table.add_row("Net Cash Flow", format_signed_money(resolution.net_cash_flow))
    return table


def _build_turn_operating_table(resolution: TurnResolution) -> Table:
    table = Table.grid(padding=(0, 1))
    table.add_row("Reputation", format_signed_int(resolution.reputation_delta))
    table.add_row("Avg Energy", str(resolution.team_condition.average_energy))
    table.add_row("Avg Morale", str(resolution.team_condition.average_morale))
    table.add_row("Burned Out", str(resolution.team_condition.burned_out_count))
    table.add_row("Pending Event", "yes" if resolution.pending_event is not None else "no")
    table.add_row(
        "Resolved Event",
        "yes" if resolution.event_history_entry is not None else "no",
    )
    return table


def _build_turn_product_table(resolution: TurnResolution) -> Table:
    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Product", style="bold")
    table.add_column("Stage")
    table.add_column("Rev", justify="right")
    table.add_column("Cost", justify="right")
    table.add_column("+Users", justify="right")
    table.add_column("Churn", justify="right")
    table.add_column("Net", justify="right")
    table.add_column("Q", justify="right")
    table.add_column("B", justify="right")

    for summary in resolution.product_summaries:
        table.add_row(
            summary.product_name,
            summary.lifecycle_stage.value,
            format_money(summary.revenue),
            format_money(summary.operating_cost),
            str(summary.acquired_users),
            str(summary.churned_users),
            format_signed_int(summary.net_user_delta),
            format_signed_int(summary.quality_delta),
            format_signed_int(summary.bug_delta),
        )

    return table


def _build_pending_event_panel(pending_event: PendingEvent) -> Panel:
    options_table = Table(box=box.SIMPLE_HEAVY, expand=True)
    options_table.add_column("#", justify="center", style="bold cyan")
    options_table.add_column("Response", style="bold")
    options_table.add_column("Trade-Off")

    for index, option in enumerate(pending_event.options, start=1):
        options_table.add_row(str(index), option.label, option.description)

    panel_body = Group(
        f"[bold]{pending_event.category.value}[/bold]",
        pending_event.description,
        options_table,
    )
    return Panel(panel_body, title=pending_event.title, border_style="yellow", expand=True)


def _build_event_result_panel(history_entry: EventHistoryEntry) -> Panel:
    body = (
        f"[bold]{history_entry.title}[/bold]\n"
        f"Response: {history_entry.selected_option_label}\n"
        f"{history_entry.result_text}"
    )
    return Panel(body, title="Event Result", border_style="yellow", expand=True)


def _count_assignments_by_product(state: GameState) -> dict[UUID, int]:
    counts: dict[UUID, int] = {}
    for employee in state.employees:
        if employee.assigned_product_id is None:
            continue
        counts[employee.assigned_product_id] = counts.get(employee.assigned_product_id, 0) + 1
    return counts


def format_signed_int(value: int) -> str:
    """Render signed integers for summaries."""

    style = "green" if value > 0 else "red" if value < 0 else "white"
    return f"[{style}]{value:+d}[/{style}]"


def format_signed_money(value: Decimal) -> str:
    """Render signed currency values for summaries."""

    style = "green" if value > 0 else "red" if value < 0 else "white"
    return f"[{style}]{format_money(value)}[/{style}]"
