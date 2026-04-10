"""Typer CLI entrypoint for NEXUS TECH."""

from typing import Dict, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from nexus_tech.domain.models import TurnAction
from nexus_tech.presentation.dashboard import (
    render_dashboard,
    render_game_over,
    render_intro,
    render_turn_resolution,
)
from nexus_tech.simulation.engine import apply_action, create_new_game, resolve_turn
from nexus_tech.simulation.randomness import RandomSource

app = typer.Typer(add_completion=False, help="NEXUS TECH terminal management simulation.")
console = Console()

ACTION_KEYS: Dict[str, TurnAction] = {
    "1": TurnAction.BUILD_FEATURE,
    "2": TurnAction.FIX_BUGS,
    "3": TurnAction.MARKET_PRODUCT,
    "4": TurnAction.WAIT,
    "5": TurnAction.VIEW_STATUS,
    "6": TurnAction.END_TURN,
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

    render_intro(console, company_name=company_name, product_name=product_name, seed=seed)

    try:
        while not state.company.game_over:
            render_dashboard(console, state)
            turn_ended = False

            while not turn_ended and not state.company.game_over:
                choice = Prompt.ask("Choose an action", choices=list(ACTION_KEYS), default="6")
                action = ACTION_KEYS[choice]
                outcome = apply_action(state, action)
                state = outcome.state

                if action is TurnAction.VIEW_STATUS:
                    render_dashboard(console, state)
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


def main() -> None:
    """CLI wrapper used by `python -m` and console scripts."""

    app()


if __name__ == "__main__":
    main()
