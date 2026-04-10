"""Rich-powered terminal presentation for the game."""

from typing import Optional

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from nexus_tech.domain.models import GameState
from nexus_tech.domain.money import format_money, format_rate
from nexus_tech.simulation.engine import TurnResolution, get_total_users


def render_intro(console: Console, company_name: str, seed: Optional[int]) -> None:
    """Print the opening game banner."""

    seed_text = f"Seed: {seed}" if seed is not None else "Seed: random"
    console.print(
        Panel.fit(
            (
                f"[bold cyan]NEXUS TECH[/bold cyan]\n"
                f"Company: [bold]{company_name}[/bold]\n"
                f"{seed_text}\n\n"
                "Goal: manage a portfolio of products, control burn, and compound growth."
            ),
            title="Phase 2 Portfolio Loop",
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
    console.print(Columns([_build_company_panel(state), _build_totals_panel(state)]))
    console.print(_build_portfolio_table(state))
    console.print(_build_action_table(), justify="center")


def render_turn_resolution(console: Console, resolution: TurnResolution) -> None:
    """Render the end-of-turn summary."""

    table = Table(title=f"Turn {resolution.resolved_turn} Summary", expand=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_row("Total Revenue", format_money(resolution.total_revenue))
    table.add_row("Baseline Cost", format_money(resolution.baseline_operating_cost))
    table.add_row("Product Costs", format_money(resolution.total_product_operating_cost))
    table.add_row("Total Operating Cost", format_money(resolution.total_operating_cost))
    table.add_row("Net Cash Flow", format_money(resolution.net_cash_flow))
    table.add_row("Reputation", format_signed_int(resolution.reputation_delta))

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
    console.print(Panel(resolution.narrative, title="Outlook", border_style="green"))


def render_game_over(console: Console, state: GameState) -> None:
    """Render the losing state."""

    console.print(
        Panel.fit(
            (
                "[bold red]Game Over[/bold red]\n"
                f"Cash on hand: {format_money(state.company.cash_on_hand)}\n"
                f"Reputation: {state.company.reputation}\n"
                f"Active users: {get_total_users(state)}"
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
    return Panel(table, title="Portfolio Totals", border_style="yellow", expand=True)


def _build_portfolio_table(state: GameState) -> Table:
    table = Table(title="Portfolio", expand=True)
    table.add_column("#", justify="center", style="bold cyan")
    table.add_column("Product", style="bold")
    table.add_column("Stage")
    table.add_column("On")
    table.add_column("Users", justify="right")
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
            str(product.quality),
            str(product.bug_level),
            str(product.market_fit),
            str(product.technical_debt),
            format_money(product.maintenance_cost),
            format_rate(product.acquisition_rate),
            format_rate(product.churn_rate),
        )

    return table


def _build_action_table() -> Table:
    table = Table(title="Action Menu", expand=True)
    table.add_column("Key", justify="center", style="bold cyan")
    table.add_column("Action", style="bold")
    table.add_column("Target")
    table.add_column("Effect")
    table.add_row("1", "create_product", "no", "Launch a new prototype and pay the setup cost.")
    table.add_row(
        "2",
        "improve_quality",
        "yes",
        "Raise quality and cut bugs, slower when debt is high.",
    )
    table.add_row(
        "3",
        "add_feature",
        "yes",
        "Raise fit and growth, but add bugs, debt, and maintenance.",
    )
    table.add_row(
        "4",
        "reduce_technical_debt",
        "yes",
        "Lower debt and future drag on a product.",
    )
    table.add_row(
        "5",
        "market_product",
        "yes",
        "Spend cash for users and awareness on one product.",
    )
    table.add_row(
        "6",
        "sunset_product",
        "yes",
        "Stop carrying a weak product in the active portfolio.",
    )
    table.add_row("7", "wait", "no", "Preserve optionality and spend no cash.")
    table.add_row("8", "view_status", "no", "Refresh the dashboard.")
    table.add_row("9", "end_turn", "no", "Run the simulation tick.")
    return table


def format_signed_int(value: int) -> str:
    """Render signed integers for summaries."""

    return f"{value:+d}"
