"""Typer CLI entrypoint for NEXUS TECH."""

from typing import Dict, Optional
from uuid import UUID

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from nexus_tech.domain.models import GameState, Product, TurnAction
from nexus_tech.presentation.dashboard import (
    render_dashboard,
    render_game_over,
    render_intro,
    render_turn_resolution,
)
from nexus_tech.simulation.engine import (
    apply_action,
    create_new_game,
    get_product_choices,
    resolve_turn,
)
from nexus_tech.simulation.randomness import RandomSource

app = typer.Typer(add_completion=False, help="NEXUS TECH terminal management simulation.")
console = Console()

ACTION_KEYS: Dict[str, TurnAction] = {
    "1": TurnAction.CREATE_PRODUCT,
    "2": TurnAction.IMPROVE_QUALITY,
    "3": TurnAction.ADD_FEATURE,
    "4": TurnAction.REDUCE_TECHNICAL_DEBT,
    "5": TurnAction.MARKET_PRODUCT,
    "6": TurnAction.SUNSET_PRODUCT,
    "7": TurnAction.WAIT,
    "8": TurnAction.VIEW_STATUS,
    "9": TurnAction.END_TURN,
}

TARGETED_ACTIONS = {
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
                choice = Prompt.ask("Choose an action", choices=list(ACTION_KEYS), default="9")
                action = ACTION_KEYS[choice]

                try:
                    target_product_id = None
                    new_product_name = None

                    if action in TARGETED_ACTIONS:
                        target_product_id = choose_target_product_id(state, action)
                        if target_product_id is None:
                            continue
                    elif action is TurnAction.CREATE_PRODUCT:
                        new_product_name = Prompt.ask("New product name").strip()

                    outcome = apply_action(
                        state,
                        action,
                        target_product_id=target_product_id,
                        new_product_name=new_product_name,
                    )
                except ValueError as error:
                    console.print(Panel.fit(str(error), title="Action Error", border_style="red"))
                    continue

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


def choose_target_product_id(state: GameState, action: TurnAction) -> Optional[UUID]:
    """Prompt the user to select a target product for an action."""

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


def build_product_selection_summary(product: Product) -> str:
    """Show concise per-product stats before an action."""

    return (
        f"{product.name}\n"
        f"Stage: {product.lifecycle_stage.value} | Users: {product.user_count} | "
        f"Quality: {product.quality} | Bugs: {product.bug_level} | "
        f"Fit: {product.market_fit} | Debt: {product.technical_debt}"
    )


def main() -> None:
    """CLI wrapper used by `python -m` and console scripts."""

    app()


if __name__ == "__main__":
    main()
