"""Rich-powered terminal presentation for the game."""

from __future__ import annotations

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from nexus_tech.domain.models import EventHistoryEntry, GameState, PendingEvent
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
                "Goal: manage products, teams, and dynamic business events without losing control."
            ),
            title="Phase 4 Event Engine",
            border_style="cyan",
        )
    )


def render_dashboard(console: Console, state: GameState) -> None:
    """Render the main per-turn dashboard."""

    console.print(
        Panel.fit(
            f"[bold white]Turn {state.company.current_turn}[/bold white]  "
            f"[cyan]Actions Left:[/cyan] {state.action_points_remaining}",
            border_style="blue",
        )
    )
    console.print(
        Columns(
            [
                _build_company_panel(state),
                _build_totals_panel(state),
                _build_team_summary_panel(state),
            ]
        )
    )
    console.print(_build_portfolio_table(state))
    console.print(_build_action_table(), justify="center")
    console.print(_build_recent_event_panel(state))


def render_team_view(console: Console, state: GameState) -> None:
    """Render the dedicated team review table."""

    console.print(_build_team_table(state))


def render_turn_resolution(console: Console, resolution: TurnResolution) -> None:
    """Render the end-of-turn summary."""

    table = Table(title=f"Turn {resolution.resolved_turn} Summary", expand=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_row("Total Revenue", format_money(resolution.total_revenue))
    table.add_row("Baseline Cost", format_money(resolution.baseline_operating_cost))
    table.add_row("Product Costs", format_money(resolution.total_product_operating_cost))
    table.add_row("Salary Cost", format_money(resolution.total_salary_cost))
    table.add_row("Total Operating Cost", format_money(resolution.total_operating_cost))
    table.add_row("Net Cash Flow", format_money(resolution.net_cash_flow))
    table.add_row("Reputation", format_signed_int(resolution.reputation_delta))
    table.add_row("Avg Energy", str(resolution.team_condition.average_energy))
    table.add_row("Avg Morale", str(resolution.team_condition.average_morale))
    table.add_row("Burned Out", str(resolution.team_condition.burned_out_count))

    product_table = Table(title="Per-Product Results", expand=True)
    product_table.add_column("Product", style="bold")
    product_table.add_column("Stage")
    product_table.add_column("Rev", justify="right")
    product_table.add_column("Cost", justify="right")
    product_table.add_column("+Users", justify="right")
    product_table.add_column("Churn", justify="right")
    product_table.add_column("Net", justify="right")
    product_table.add_column("Q", justify="right")
    product_table.add_column("B", justify="right")

    for summary in resolution.product_summaries:
        product_table.add_row(
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

    console.print(table)
    console.print(product_table)
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


def _build_company_panel(state: GameState) -> Panel:
    table = Table.grid(padding=(0, 1))
    table.add_row("Name", state.company.name)
    table.add_row("Cash", format_money(state.company.cash_on_hand))
    table.add_row("Reputation", str(state.company.reputation))
    table.add_row("Status", "Game Over" if state.company.game_over else "Operating")
    return Panel(table, title="Company", border_style="magenta", expand=True)


def _build_totals_panel(state: GameState) -> Panel:
    active_products = [product for product in state.products if product.is_active]
    table = Table.grid(padding=(0, 1))
    table.add_row("Active Products", str(len(active_products)))
    table.add_row("Portfolio Users", str(get_total_users(state)))
    table.add_row("Sunset Products", str(len(state.products) - len(active_products)))
    return Panel(table, title="Portfolio", border_style="yellow", expand=True)


def _build_team_summary_panel(state: GameState) -> Panel:
    team_condition = calculate_team_condition(state.employees)
    table = Table.grid(padding=(0, 1))
    table.add_row("Headcount", str(team_condition.headcount))
    table.add_row("Assigned", str(team_condition.assigned_headcount))
    table.add_row("Salary Burn", format_money(team_condition.total_salary_cost))
    table.add_row("Avg Energy", str(team_condition.average_energy))
    table.add_row("Avg Morale", str(team_condition.average_morale))
    return Panel(table, title="Team", border_style="cyan", expand=True)


def _build_portfolio_table(state: GameState) -> Table:
    assignment_counts = _count_assignments_by_product(state)

    table = Table(title="Portfolio", expand=True)
    table.add_column("#", justify="center", style="bold cyan")
    table.add_column("Product", style="bold")
    table.add_column("Stage")
    table.add_column("On")
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


def _build_team_table(state: GameState) -> Panel:
    if not state.employees:
        return Panel.fit(
            "No employees hired yet.",
            title="Team Review",
            border_style="cyan",
        )

    product_names = {product.id: product.name for product in state.products}

    table = Table(title="Team Review", expand=True)
    table.add_column("#", justify="center", style="bold cyan")
    table.add_column("Employee", style="bold")
    table.add_column("Role")
    table.add_column("Seniority")
    table.add_column("Assignment")
    table.add_column("Spec")
    table.add_column("Salary", justify="right")
    table.add_column("Energy", justify="right")
    table.add_column("Morale", justify="right")
    table.add_column("Eff", justify="right")

    for index, employee in enumerate(state.employees, start=1):
        assignment_name = product_names.get(employee.assigned_product_id, "unassigned")
        table.add_row(
            str(index),
            employee.full_name,
            employee.role.value,
            employee.seniority.value,
            assignment_name,
            employee.specialization,
            format_money(employee.salary),
            str(employee.energy),
            str(employee.morale),
            str(calculate_effective_productivity(employee)),
        )

    return Panel(table, border_style="cyan")


def _build_action_table() -> Table:
    table = Table(title="Action Menu", expand=True)
    table.add_column("Key", justify="center", style="bold cyan")
    table.add_column("Action", style="bold")
    table.add_column("Target")
    table.add_column("Effect")
    table.add_row("1", "create_product", "no", "Launch a new prototype.")
    table.add_row("2", "improve_quality", "product", "Improve quality with assigned team help.")
    table.add_row("3", "add_feature", "product", "Ship faster, but risk bugs and debt.")
    table.add_row("4", "reduce_technical_debt", "product", "Lower debt and stabilise delivery.")
    table.add_row("5", "market_product", "product", "Spend cash for acquisition.")
    table.add_row("6", "sunset_product", "product", "Retire a weak product.")
    table.add_row("7", "hire_employee", "no", "Add salary burden and capability.")
    table.add_row("8", "fire_employee", "employee", "Remove salary burden.")
    table.add_row("9", "assign_employee", "employee+product", "Put someone on product work.")
    table.add_row("10", "unassign_employee", "employee", "Pull someone off product work.")
    table.add_row("11", "rest_team", "no", "Recover energy and morale.")
    table.add_row("12", "review_team", "no", "Open the team view.")
    table.add_row("13", "wait", "no", "Spend no cash and do no work.")
    table.add_row("14", "view_status", "no", "Refresh the dashboard.")
    table.add_row("15", "end_turn", "no", "Run the simulation tick.")
    return table


def _build_recent_event_panel(state: GameState) -> Panel:
    if state.pending_event is not None:
        body = (
            f"[bold]{state.pending_event.title}[/bold]\n"
            f"{state.pending_event.description}\n"
            "Resolve it before taking the next turn."
        )
        return Panel(body, title="Pending Event", border_style="yellow")

    if not state.event_history:
        return Panel(
            "No major business events have fired yet.",
            title="Recent Events",
            border_style="yellow",
        )

    recent_history = state.event_history[-3:]
    body = "\n".join(
        f"[bold]{entry.title}[/bold] ({entry.selected_option_label})\n{entry.result_text}"
        for entry in reversed(recent_history)
    )
    return Panel(body, title="Recent Events", border_style="yellow")


def _build_pending_event_panel(pending_event: PendingEvent) -> Panel:
    options_table = Table.grid(padding=(0, 1))
    for index, option in enumerate(pending_event.options, start=1):
        options_table.add_row(f"{index}.", f"{option.label} - {option.description}")

    panel_body = Table.grid(padding=(0, 1))
    panel_body.add_row(f"[bold]{pending_event.category.value}[/bold]")
    panel_body.add_row(pending_event.description)
    panel_body.add_row(options_table)
    return Panel(panel_body, title=pending_event.title, border_style="yellow")


def _build_event_result_panel(history_entry: EventHistoryEntry) -> Panel:
    body = (
        f"[bold]{history_entry.title}[/bold]\n"
        f"Response: {history_entry.selected_option_label}\n"
        f"{history_entry.result_text}"
    )
    return Panel(body, title="Event Result", border_style="yellow")


def _count_assignments_by_product(state: GameState) -> dict:
    counts = {}
    for employee in state.employees:
        if employee.assigned_product_id is None:
            continue
        counts[employee.assigned_product_id] = counts.get(employee.assigned_product_id, 0) + 1
    return counts


def format_signed_int(value: int) -> str:
    """Render signed integers for summaries."""

    return f"{value:+d}"
