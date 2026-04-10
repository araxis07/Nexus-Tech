"""Rich-powered terminal presentation for the game."""

from typing import Optional

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from nexus_tech.domain.models import GameState
from nexus_tech.domain.money import format_money
from nexus_tech.simulation.engine import TurnResolution


def render_intro(
    console: Console,
    company_name: str,
    product_name: str,
    seed: Optional[int],
) -> None:
    """Print the opening game banner."""

    seed_text = f"Seed: {seed}" if seed is not None else "Seed: random"
    console.print(
        Panel.fit(
            (
                f"[bold cyan]NEXUS TECH[/bold cyan]\n"
                f"Company: [bold]{company_name}[/bold]\n"
                f"Product: [bold]{product_name}[/bold]\n"
                f"{seed_text}\n\n"
                "Goal: stay solvent, improve the product, and grow your users."
            ),
            title="Phase 1 Vertical Slice",
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
    console.print(Columns([_build_company_panel(state), _build_product_panel(state)]))
    console.print(_build_action_table(), justify="center")


def render_turn_resolution(console: Console, resolution: TurnResolution) -> None:
    """Render the end-of-turn summary."""

    table = Table(title=f"Turn {resolution.resolved_turn} Summary", expand=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_row("Revenue", format_money(resolution.revenue))
    table.add_row("Operating Cost", format_money(resolution.operating_cost))
    table.add_row("Net Cash Flow", format_money(resolution.net_cash_flow))
    table.add_row("Users", format_signed_int(resolution.user_delta))
    table.add_row("Reputation", format_signed_int(resolution.reputation_delta))
    table.add_row("Quality", format_signed_int(resolution.quality_delta))

    console.print(table)
    console.print(Panel(resolution.narrative, title="Outlook", border_style="green"))


def render_game_over(console: Console, state: GameState) -> None:
    """Render the losing state."""

    console.print(
        Panel.fit(
            (
                "[bold red]Game Over[/bold red]\n"
                f"Cash on hand: {format_money(state.company.cash_on_hand)}\n"
                f"Reputation: {state.company.reputation}\n"
                f"Users: {state.product.user_count}"
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


def _build_product_panel(state: GameState) -> Panel:
    table = Table.grid(padding=(0, 1))
    table.add_row("Product", state.product.name)
    table.add_row("Users", str(state.product.user_count))
    table.add_row("Quality", str(state.product.quality))
    table.add_row("Bug Level", str(state.product.bug_level))
    table.add_row("Features", str(state.product.feature_count))
    table.add_row("Revenue / User", format_money(state.product.revenue_per_user))
    return Panel(table, title="Product", border_style="yellow", expand=True)


def _build_action_table() -> Table:
    table = Table(title="Action Menu", expand=True)
    table.add_column("Key", justify="center", style="bold cyan")
    table.add_column("Action", style="bold")
    table.add_column("Effect")
    table.add_row("1", "build_feature", "Ship product work, raise quality, add some bugs.")
    table.add_row("2", "fix_bugs", "Reduce bug load and slightly improve quality.")
    table.add_row("3", "market_product", "Spend cash to gain users and reputation.")
    table.add_row("4", "wait", "Do nothing and preserve optionality.")
    table.add_row("5", "view_status", "Refresh the dashboard without spending a turn action.")
    table.add_row("6", "end_turn", "Run the simulation tick.")
    return table


def format_signed_int(value: int) -> str:
    """Render signed integers for summaries."""

    return f"{value:+d}"
