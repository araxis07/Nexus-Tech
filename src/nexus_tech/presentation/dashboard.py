"""Rich-powered terminal presentation for the game."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from rich import box
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table

from nexus_tech.content.models import (
    CompetitorArchetypeDefinition,
    ProductTemplateDefinition,
    ScenarioDefinition,
)
from nexus_tech.domain.models import (
    Employee,
    EventHistoryEntry,
    FundingHistoryEntry,
    GameState,
    MilestoneEntry,
    PendingEvent,
    Product,
)
from nexus_tech.domain.money import format_money, format_rate
from nexus_tech.persistence.save_coordinator import SaveSlotSummary
from nexus_tech.simulation.balance_lab import (
    BalanceBatchResult,
    BalanceComparisonResult,
    BalanceMatrixResult,
)
from nexus_tech.simulation.campaign import CampaignGoalDefinition, evaluate_campaign_goal
from nexus_tech.simulation.engine import TurnResolution, get_total_users
from nexus_tech.simulation.finance import estimate_runway
from nexus_tech.simulation.late_game import calculate_late_game_summary
from nexus_tech.simulation.market import get_market_profile
from nexus_tech.simulation.operations import calculate_operations_summary
from nexus_tech.simulation.planning import evaluate_quarter_plan, is_quarter_plan_due
from nexus_tech.simulation.reporting import calculate_run_score
from nexus_tech.simulation.roadmap import (
    get_effective_roadmap_focus,
    get_roadmap_turns_remaining,
    is_roadmap_due,
)
from nexus_tech.simulation.scaling import calculate_company_scale_pressure
from nexus_tech.simulation.team import calculate_effective_productivity, calculate_team_condition


def render_intro(
    console: Console,
    *,
    company_name: str,
    scenario_title: str,
    difficulty_label: str,
    campaign_goal_title: str,
    seed: int | None,
) -> None:
    """Print the opening game banner."""

    seed_text = f"Seed: {seed}" if seed is not None else "Seed: random"
    console.print(
        Panel.fit(
            (
                f"[bold cyan]NEXUS TECH[/bold cyan]\n"
                f"Company: [bold]{company_name}[/bold]\n"
                f"Scenario: {scenario_title}\n"
                f"Difficulty: {difficulty_label}\n"
                f"Campaign Goal: {campaign_goal_title}\n"
                f"{seed_text}\n\n"
                "Run a focused local software company from the terminal.\n"
                "Build products, manage the team, react to events, and keep cash alive."
            ),
            title="Terminal Management Simulation",
            border_style="cyan",
        )
    )


def render_scenario_catalog(console: Console, scenarios: tuple[ScenarioDefinition, ...]) -> None:
    """Render the available starting scenarios."""

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Scenario", style="bold")
    table.add_column("Company")
    table.add_column("Strategy")
    table.add_column("Difficulty")
    table.add_column("Goal")
    table.add_column("Products", justify="right")
    table.add_column("Team", justify="right")
    table.add_column("Description")

    for scenario in scenarios:
        table.add_row(
            f"{scenario.title}\n[dim]{scenario.scenario_id}[/dim]",
            scenario.company_name,
            scenario.company_strategy.value,
            scenario.difficulty_mode.value,
            scenario.campaign_goal_id.value,
            str(len(scenario.products)),
            str(len(scenario.employees)),
            scenario.description,
        )

    scenario_ids = ", ".join(f"{scenario.scenario_id} ({scenario.title})" for scenario in scenarios)
    content = Group(
        table,
        "",
        f"[dim]Use --scenario <id>. Available ids: {scenario_ids}[/dim]",
    )
    console.print(Panel(content, title="Scenario Catalog", border_style="cyan", expand=True))


def render_product_template_catalog(
    console: Console,
    templates: tuple[ProductTemplateDefinition, ...],
) -> None:
    """Render the available product templates."""

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Template", style="bold")
    table.add_column("Stage")
    table.add_column("Segment")
    table.add_column("Price")
    table.add_column("Q", justify="right")
    table.add_column("B", justify="right")
    table.add_column("Fit", justify="right")
    table.add_column("Debt", justify="right")
    table.add_column("Description")

    for template in templates:
        table.add_row(
            f"{template.title}\n[dim]{template.template_id}[/dim]",
            template.lifecycle_stage.value,
            template.target_segment.value,
            template.pricing_tier.value,
            str(template.quality),
            str(template.bug_level),
            str(template.market_fit),
            str(template.technical_debt),
            template.description,
        )

    template_ids = ", ".join(
        f"{template.template_id} ({template.title})" for template in templates
    )
    content = Group(
        table,
        "",
        f"[dim]Template ids: {template_ids}[/dim]",
    )
    console.print(
        Panel(
            content,
            title="Product Template Catalog",
            border_style="cyan",
            expand=True,
        )
    )


def render_campaign_goal_catalog(
    console: Console,
    goals: tuple[CampaignGoalDefinition, ...],
) -> None:
    """Render all available campaign goals."""

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Goal", style="bold")
    table.add_column("Description")
    table.add_column("Outcome")

    for goal in goals:
        table.add_row(
            f"{goal.title}\n[dim]{goal.goal_id.value}[/dim]",
            goal.description,
            goal.success_text,
        )

    console.print(
        Panel(
            table,
            title="Campaign Goals",
            border_style="cyan",
            expand=True,
        )
    )


def render_competitor_archetype_catalog(
    console: Console,
    archetypes: tuple[CompetitorArchetypeDefinition, ...],
) -> None:
    """Render the available competitor archetypes."""

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Archetype", style="bold")
    table.add_column("Segment")
    table.add_column("Price")
    table.add_column("Move")
    table.add_column("Strength", justify="right")
    table.add_column("Aggro", justify="right")
    table.add_column("Products", justify="right")
    table.add_column("Description")

    for archetype in archetypes:
        table.add_row(
            f"{archetype.title}\n[dim]{archetype.archetype_id}[/dim]",
            archetype.focus_segment.value,
            archetype.pricing_tier.value,
            archetype.current_move.value,
            str(archetype.strength),
            str(archetype.aggression),
            str(archetype.active_product_count),
            archetype.description,
        )

    archetype_ids = ", ".join(
        f"{archetype.archetype_id} ({archetype.title})" for archetype in archetypes
    )
    content = Group(
        table,
        "",
        f"[dim]Archetype ids: {archetype_ids}[/dim]",
    )
    console.print(
        Panel(
            content,
            title="Competitor Archetypes",
            border_style="red",
            expand=True,
        )
    )


def render_save_slot_catalog(
    console: Console,
    save_slots: list[SaveSlotSummary],
) -> None:
    """Render available save slots with compact run metadata."""

    if not save_slots:
        console.print(
            Panel(
                "No save slots were found yet. Start a run and use save_game first.",
                title="Save Slots",
                border_style="green",
                expand=True,
            )
        )
        return

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Slot", style="bold")
    table.add_column("Company")
    table.add_column("Scenario")
    table.add_column("Turn", justify="right")
    table.add_column("Cash", justify="right")
    table.add_column("Rep", justify="right")
    table.add_column("Products", justify="right")
    table.add_column("Team", justify="right")
    table.add_column("Status")
    table.add_column("Build")
    table.add_column("Schema", justify="right")
    table.add_column("Updated")

    for slot in save_slots:
        if slot.victory_achieved:
            status = "victory"
        elif slot.game_over:
            status = "shutdown"
        else:
            status = "active"
        table.add_row(
            slot.slot_name,
            slot.company_name,
            slot.scenario_title,
            str(slot.current_turn),
            format_money(slot.cash_on_hand),
            str(slot.reputation),
            str(slot.active_products),
            str(slot.headcount),
            status,
            slot.saved_with_version,
            str(slot.schema_version),
            slot.updated_at,
        )

    slot_names = ", ".join(slot.slot_name for slot in save_slots)
    content = Group(
        table,
        "",
        f"[dim]Available slots: {slot_names}[/dim]",
    )
    console.print(Panel(content, title="Save Slots", border_style="green", expand=True))


def render_quick_guide(console: Console) -> None:
    """Render a concise onboarding guide for first-time players."""

    content = Group(
        "[bold]Opening flow[/bold]",
        "1. Review the flagship product and current runway.",
        "2. Spend early actions on quality, marketing, or one key hire.",
        "3. End the turn and watch revenue, churn, burnout, and rival pressure.",
        "",
        "[bold]Useful commands[/bold]",
        (
            "`nexus-tech guide`, `list-scenarios`, `list-templates`, "
            "`list-rivals`, `list-saves`, `check-saves`"
        ),
        "",
        "[bold]Strong first turns[/bold]",
        (
            "Protect quality before bugs compound, keep cash above runway risk, "
            "and avoid over-hiring before the first clear growth signal."
        ),
    )
    console.print(Panel(content, title="Quick Guide", border_style="blue", expand=True))


def render_balance_lab(console: Console, batch: BalanceBatchResult) -> None:
    """Render aggregate batch-simulation output for tuning work."""

    overview = Table.grid(padding=(0, 1))
    overview.add_row("Scenario", batch.scenario_id)
    overview.add_row("Difficulty", batch.difficulty_mode.value)
    overview.add_row("Goal", batch.campaign_goal_id.value)
    overview.add_row("Runs", str(batch.runs))
    overview.add_row("Turns", str(batch.turns))
    overview.add_row("Seed Base", str(batch.seed_base))
    overview.add_row("Victories", str(batch.victories))
    overview.add_row("Shutdowns", str(batch.shutdowns))
    overview.add_row("Avg Turns", f"{batch.average_turns:.1f}")
    overview.add_row("Avg Score", f"{batch.average_score:.1f}")

    runs_table = Table(box=box.SIMPLE_HEAVY, expand=True)
    runs_table.add_column("Seed", justify="right", style="bold cyan")
    runs_table.add_column("Outcome")
    runs_table.add_column("Turn", justify="right")
    runs_table.add_column("Cash", justify="right")
    runs_table.add_column("Users", justify="right")
    runs_table.add_column("Products", justify="right")
    runs_table.add_column("Score", justify="right")

    for result in batch.results:
        if result.victory_achieved:
            outcome = "victory"
        elif result.game_over:
            outcome = "shutdown"
        else:
            outcome = "active"
        runs_table.add_row(
            str(result.seed),
            outcome,
            str(result.turns_played),
            format_money(result.final_cash),
            str(result.total_users),
            str(result.active_products),
            str(result.run_score),
        )

    console.print(
        Columns(
            [
                Panel(overview, title="Balance Lab", border_style="cyan", expand=True),
                Panel(runs_table, title="Run Results", border_style="green", expand=True),
            ],
            equal=False,
            expand=True,
        )
    )


def render_balance_comparison(console: Console, comparison: BalanceComparisonResult) -> None:
    """Render side-by-side scenario comparison output for tuning work."""

    overview = Table.grid(padding=(0, 1))
    overview.add_row("Difficulty", comparison.difficulty_mode.value)
    overview.add_row("Goal", comparison.campaign_goal_id.value)
    overview.add_row("Runs / Scenario", str(comparison.runs))
    overview.add_row("Turns", str(comparison.turns))
    overview.add_row("Seed Base", str(comparison.seed_base))
    overview.add_row("Scenarios", str(len(comparison.comparisons)))

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Scenario", style="bold")
    table.add_column("Avg Score", justify="right")
    table.add_column("Avg Cash", justify="right")
    table.add_column("Avg Users", justify="right")
    table.add_column("Victories", justify="right")
    table.add_column("Shutdowns", justify="right")

    for entry in comparison.comparisons:
        table.add_row(
            entry.scenario_id,
            f"{entry.average_score:.1f}",
            format_money(entry.average_cash),
            f"{entry.average_users:.1f}",
            str(entry.victories),
            str(entry.shutdowns),
        )

    console.print(
        Columns(
            [
                Panel(overview, title="Balance Compare", border_style="cyan", expand=True),
                Panel(table, title="Scenario Ranking", border_style="green", expand=True),
            ],
            equal=False,
            expand=True,
        )
    )


def render_balance_matrix(console: Console, matrix: BalanceMatrixResult) -> None:
    """Render a scenario-versus-difficulty tuning matrix."""

    overview = Table.grid(padding=(0, 1))
    overview.add_row("Goal", matrix.campaign_goal_id.value)
    overview.add_row("Runs / Cell", str(matrix.runs))
    overview.add_row("Turns", str(matrix.turns))
    overview.add_row("Seed Base", str(matrix.seed_base))
    overview.add_row("Cells", str(len(matrix.cells)))

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Scenario", style="bold")
    table.add_column("Difficulty")
    table.add_column("Avg Score", justify="right")
    table.add_column("Avg Cash", justify="right")
    table.add_column("Avg Users", justify="right")
    table.add_column("Victories", justify="right")
    table.add_column("Shutdowns", justify="right")

    for cell in matrix.cells:
        table.add_row(
            cell.scenario_id,
            cell.difficulty_mode.value,
            f"{cell.average_score:.1f}",
            format_money(cell.average_cash),
            f"{cell.average_users:.1f}",
            str(cell.victories),
            str(cell.shutdowns),
        )

    console.print(
        Columns(
            [
                Panel(overview, title="Balance Matrix", border_style="cyan", expand=True),
                Panel(table, title="Scenario x Difficulty", border_style="green", expand=True),
            ],
            equal=False,
            expand=True,
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
    console.print(
        Columns(
            [
                _build_dashboard_team_panel(state),
                _build_market_watch_panel(state),
                _build_operations_panel(state),
                _build_late_game_panel(state),
                _build_finance_panel(state),
            ],
            equal=False,
            expand=True,
        )
    )
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
    onboarding_panel = _build_onboarding_panel(state)
    if onboarding_panel is not None:
        console.print(onboarding_panel)


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


def render_report(console: Console, state: GameState) -> None:
    """Render a compact run report with score and turn history."""

    run_score = calculate_run_score(state)
    history_panel = (
        Panel(
            _build_turn_history_table(state),
            title="Turn History",
            border_style="green",
            expand=True,
        )
        if state.turn_history
        else Panel(
            "No resolved turns yet. End at least one turn to build a report history.",
            title="Turn History",
            border_style="green",
            expand=True,
        )
    )
    console.print(
        Columns(
            [
                _build_report_overview_panel(state, run_score.total_score, run_score.score_tier),
                _build_report_score_panel(state),
                _build_report_quarter_plan_panel(state),
            ],
            equal=True,
            expand=True,
        )
    )
    console.print(
        Columns(
            [
                _build_finance_panel(state),
                _build_operations_panel(state),
                _build_late_game_panel(state),
                Panel(
                    _build_competitor_table(state),
                    title="Competitor Watch",
                    border_style="red",
                    expand=True,
                ),
            ],
            equal=True,
            expand=True,
        )
    )
    console.print(
        Columns(
            [
                _build_funding_history_panel(state),
                _build_recent_events_panel(state),
                _build_milestone_history_panel(state),
            ],
            equal=True,
            expand=True,
        )
    )
    console.print(history_panel)


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
    if resolution.unlocked_milestones:
        console.print(_build_milestone_panel(resolution.unlocked_milestones))
    console.print(Panel(resolution.narrative, title="Outlook", border_style="green"))


def render_victory(console: Console, state: GameState) -> None:
    """Render the winning state."""

    run_score = calculate_run_score(state)
    content = Table.grid(padding=(0, 1))
    content.add_row("Outcome", state.victory_reason or "The company reached durable scale.")
    content.add_row("Run Score", f"{run_score.total_score} ({run_score.score_tier})")
    content.add_row("Estimated Value", format_money(run_score.estimated_valuation))
    content.add_row("Portfolio Users", str(run_score.total_users))
    content.add_row("Active Products", str(run_score.active_products))
    content.add_row("Mature Products", str(run_score.mature_products))
    content.add_row("Headcount", str(len(state.employees)))
    content.add_row("Cash On Hand", format_money(state.company.cash_on_hand))
    content.add_row("Reputation", str(state.company.reputation))
    console.print(Panel(content, title="Victory", border_style="green", expand=True))


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

    effective_roadmap = get_effective_roadmap_focus(
        state.roadmap_focus,
        roadmap_set_turn=state.roadmap_set_turn,
        current_turn=state.company.current_turn,
    )
    summary = Table.grid(padding=(0, 1))
    summary.add_row("Action", action_label.replace("_", " "))
    summary.add_row("Result", message)
    summary.add_row(
        "State",
        (
            f"Actions left {state.action_points_remaining} | "
            f"Cash {format_money(state.company.cash_on_hand)} | "
            f"Reputation {state.company.reputation} | "
            f"Strategy {state.company.strategy.value} | "
            f"Roadmap {effective_roadmap.value}"
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
    table.add_column("Segment")
    table.add_column("Price")

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
            product.target_segment.value,
            product.pricing_tier.value,
        )

    console.print(
        Panel(
            table,
            title=f"Product Target: {action_label.replace('_', ' ')}",
            border_style="blue",
            expand=True,
        )
    )


def render_product_template_picker(
    console: Console,
    templates: list[ProductTemplateDefinition],
    action_label: str,
) -> None:
    """Render a compact template selection table before prompting."""

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("#", justify="center", style="bold cyan")
    table.add_column("Template", style="bold")
    table.add_column("Stage")
    table.add_column("Q", justify="right")
    table.add_column("B", justify="right")
    table.add_column("Fit", justify="right")
    table.add_column("Debt", justify="right")
    table.add_column("Segment")
    table.add_column("Price")
    table.add_column("Description")

    for index, template in enumerate(templates, start=1):
        table.add_row(
            str(index),
            template.title,
            template.lifecycle_stage.value,
            str(template.quality),
            str(template.bug_level),
            str(template.market_fit),
            str(template.technical_debt),
            template.target_segment.value,
            template.pricing_tier.value,
            template.description,
        )

    console.print(
        Panel(
            table,
            title=f"Product Template: {action_label.replace('_', ' ')}",
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
    effective_roadmap = get_effective_roadmap_focus(
        state.roadmap_focus,
        roadmap_set_turn=state.roadmap_set_turn,
        current_turn=state.company.current_turn,
    )
    roadmap_due = is_roadmap_due(
        roadmap_set_turn=state.roadmap_set_turn,
        current_turn=state.company.current_turn,
    )
    turns_remaining = get_roadmap_turns_remaining(
        roadmap_set_turn=state.roadmap_set_turn,
        current_turn=state.company.current_turn,
    )
    roadmap_status = (
        "due now"
        if roadmap_due
        else f"{turns_remaining} turns left"
    )
    body = (
        f"[bold white]Turn {state.company.current_turn}[/bold white]\n"
        f"[cyan]Scenario:[/cyan] {state.scenario_title}\n"
        f"[cyan]Actions Left:[/cyan] {state.action_points_remaining}\n"
        f"[cyan]Roadmap:[/cyan] {effective_roadmap.value} ({roadmap_status})\n"
        f"[cyan]Market:[/cyan] {state.market_cycle.value} | "
        f"[cyan]Budget:[/cyan] {state.quarter_plan.budget_stance.value}\n"
        "Use the action menu below, then end the turn when you are ready to simulate."
    )
    return Panel.fit(body, title="Turn Control", border_style="blue")


def _build_company_panel(state: GameState) -> Panel:
    effective_roadmap = get_effective_roadmap_focus(
        state.roadmap_focus,
        roadmap_set_turn=state.roadmap_set_turn,
        current_turn=state.company.current_turn,
    )
    goal_progress = evaluate_campaign_goal(state)
    table = Table.grid(padding=(0, 1))
    table.add_row("Name", state.company.name)
    table.add_row("Scenario", state.scenario_title)
    table.add_row("Difficulty", state.difficulty_mode.value)
    table.add_row("Goal", goal_progress.title)
    table.add_row("Cash", format_money(state.company.cash_on_hand))
    table.add_row("Reputation", str(state.company.reputation))
    table.add_row("Strategy", state.company.strategy.value)
    table.add_row("Roadmap", effective_roadmap.value)
    table.add_row("Budget", state.quarter_plan.budget_stance.value)
    table.add_row("Market", state.market_cycle.value)
    table.add_row("Debt", format_money(state.finance.debt_principal))
    table.add_row("Dilution", format_rate(state.finance.equity_dilution))
    table.add_row("Status", "Game Over" if state.company.game_over else "Operating")
    return Panel(table, title="Company Overview", border_style="magenta", expand=True)


def _build_totals_panel(state: GameState) -> Panel:
    active_products = [product for product in state.products if product.is_active]
    run_score = calculate_run_score(state)
    scale_pressure = calculate_company_scale_pressure(
        state.products,
        headcount=len(state.employees),
        current_turn=state.company.current_turn,
    )
    table = Table.grid(padding=(0, 1))
    table.add_row("Active Products", str(len(active_products)))
    table.add_row("Portfolio Users", str(get_total_users(state)))
    table.add_row("Sunset Products", str(len(state.products) - len(active_products)))
    table.add_row("Run Score", f"{run_score.total_score} ({run_score.score_tier})")
    table.add_row("Estimated Value", format_money(run_score.estimated_valuation))
    runway = estimate_runway(state.company.cash_on_hand, _latest_net_cash_flow(state))
    table.add_row("Runway", "cashflow+" if runway is None else f"{runway} turns")
    table.add_row("Competitors", str(len(state.competitors)))
    table.add_row("Scale Drag", str(scale_pressure.coordination_drag))
    operations = calculate_operations_summary(
        state.products,
        state.employees,
        current_turn=state.company.current_turn,
    )
    table.add_row("Ops Load", f"{operations.total_load}/{operations.total_capacity}")
    table.add_row("Ops Cost", format_money(operations.added_cost))
    table.add_row("Scale State", scale_pressure.summary)
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
    table.add_column("Segment")
    table.add_column("Users", justify="right")
    table.add_column("Team", justify="right")
    table.add_column("Q", justify="right")
    table.add_column("B", justify="right")
    table.add_column("Fit", justify="right")
    table.add_column("Debt", justify="right")
    table.add_column("Maint", justify="right")
    table.add_column("Price")
    table.add_column("Aq", justify="right")
    table.add_column("Ch", justify="right")

    for index, product in enumerate(state.products, start=1):
        table.add_row(
            str(index),
            product.name,
            product.lifecycle_stage.value,
            "active" if product.is_active else "sunset",
            product.target_segment.value,
            str(product.user_count),
            str(assignment_counts.get(product.id, 0)),
            str(product.quality),
            str(product.bug_level),
            str(product.market_fit),
            str(product.technical_debt),
            format_money(product.maintenance_cost),
            product.pricing_tier.value,
            format_rate(product.acquisition_rate),
            format_rate(product.churn_rate),
        )

    return table


def _build_dashboard_team_panel(state: GameState) -> Panel:
    if not state.employees:
        return Panel(
            "No employees hired yet. Use [bold]17[/bold] to start building the team.",
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
    primary_actions.add_row("6", "adjust_pricing", "Change pricing and growth trade-offs.")
    primary_actions.add_row("7", "set_target_segment", "Retarget a product's customer segment.")
    primary_actions.add_row("8", "sunset_product", "Retire a weak product.")
    primary_actions.add_row("9", "set_company_strategy", "Shift company-wide focus.")
    primary_actions.add_row("10", "set_roadmap", "Pick the quarter's execution plan.")
    primary_actions.add_row("11", "set_budget_stance", "Change the quarter's spend posture.")
    primary_actions.add_row("12", "take_loan", "Trade future burn for runway.")
    primary_actions.add_row("13", "raise_angel", "Take smaller capital with dilution.")
    primary_actions.add_row("14", "raise_vc", "Raise a larger round once traction is real.")
    primary_actions.add_row("15", "repay_debt", "Reduce interest and capital pressure.")
    primary_actions.add_row("16", "review_finance", "Open the capital and runway view.")
    primary_actions.add_row("17", "hire_employee", "Add capability and salary burn.")
    primary_actions.add_row("18", "fire_employee", "Remove salary burden.")
    primary_actions.add_row("19", "assign_employee", "Put someone on a product.")
    primary_actions.add_row("20", "unassign_employee", "Pull someone off product work.")
    primary_actions.add_row("21", "rest_team", "Recover energy and morale.")
    primary_actions.add_row("22", "review_team", "Open the detailed team view.")
    primary_actions.add_row("23", "view_report", "Open the score, plan, and rival report.")
    primary_actions.add_row("24", "wait", "Hold position for this action.")
    primary_actions.add_row("25", "view_status", "Refresh the dashboard.")
    primary_actions.add_row("26", "end_turn", "Run the simulation tick.")

    utility_actions = Table(box=box.SIMPLE_HEAVY, expand=True)
    utility_actions.add_column("Key", justify="center", style="bold cyan")
    utility_actions.add_column("Utility", style="bold")
    utility_actions.add_column("Purpose")
    utility_actions.add_row("27", "save_game", "Write the current run to SQLite.")
    utility_actions.add_row("28", "load_game", "Resume a saved slot from SQLite.")
    utility_actions.add_row("29", "show_guide", "Show a compact how-to-play guide.")

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


def _build_onboarding_panel(state: GameState) -> Panel | None:
    if state.company.current_turn > 3 and state.turn_history:
        return None

    suggestions: list[str] = []
    if not state.employees:
        suggestions.append(
            "Use [bold]17[/bold] to hire the first team member once runway is safe."
        )
    elif any(employee.assigned_product_id is None for employee in state.employees):
        suggestions.append(
            "Use [bold]19[/bold] to assign unallocated teammates to the product that matters most."
        )
    else:
        suggestions.append(
            "Keep assignments focused. Too much portfolio spread will dilute throughput."
        )

    if any(product.bug_level >= 25 for product in state.products if product.is_active):
        suggestions.append(
            "Use [bold]2[/bold] or [bold]4[/bold] before bugs start dragging growth down."
        )
    else:
        suggestions.append(
            "Use [bold]2[/bold] to raise quality or [bold]5[/bold] "
            "to buy demand on the flagship product."
        )

    if state.company.current_turn == 1:
        suggestions.append("Use [bold]29[/bold] any time if you want the compact guide again.")
    if state.company.current_turn >= 2:
        suggestions.append(
            "Check [bold]23[/bold] after a turn resolves to read the run report "
            "and rival pressure."
        )

    body = "\n".join(f"- {line}" for line in suggestions)
    return Panel(body, title="Onboarding", border_style="blue", expand=True)


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
    table.add_row("Operations Cost", format_money(resolution.total_operations_cost))
    table.add_row("Late-Game Cost", format_money(resolution.total_late_game_cost))
    table.add_row("Salary Cost", format_money(resolution.total_salary_cost))
    table.add_row("Finance Cost", format_money(resolution.total_finance_cost))
    table.add_row("Total Operating Cost", format_money(resolution.total_operating_cost))
    table.add_row("Net Cash Flow", format_signed_money(resolution.net_cash_flow))
    table.add_row("Cash On Hand", format_money(resolution.state.company.cash_on_hand))
    return table


def _build_turn_operating_table(resolution: TurnResolution) -> Table:
    table = Table.grid(padding=(0, 1))
    table.add_row("Reputation", format_signed_int(resolution.reputation_delta))
    table.add_row(
        "Avg Energy",
        "-"
        if resolution.team_condition.headcount == 0
        else str(resolution.team_condition.average_energy),
    )
    table.add_row(
        "Avg Morale",
        "-"
        if resolution.team_condition.headcount == 0
        else str(resolution.team_condition.average_morale),
    )
    table.add_row("Burned Out", str(resolution.team_condition.burned_out_count))
    table.add_row("Strategy", resolution.state.company.strategy.value)
    table.add_row("Difficulty", resolution.state.difficulty_mode.value)
    table.add_row("Budget", resolution.state.quarter_plan.budget_stance.value)
    table.add_row("Roadmap", resolution.roadmap_focus.value)
    table.add_row("Market", resolution.market_cycle.value)
    table.add_row("Goal", resolution.campaign_goal_progress.title)
    table.add_row(
        "Goal State",
        "complete" if resolution.campaign_goal_progress.completed else "in progress",
    )
    table.add_row(
        "Ops Load",
        (
            f"{resolution.operations_summary.total_load}/"
            f"{resolution.operations_summary.total_capacity}"
        ),
    )
    table.add_row("Ops State", resolution.operations_summary.summary)
    table.add_row("Late State", resolution.late_game_summary.summary)
    table.add_row("Scale State", resolution.scale_pressure_summary)
    table.add_row(
        "Pressure Δ",
        format_signed_int(resolution.finance_summary.investor_pressure_delta),
    )
    table.add_row(
        "Run Score", f"{resolution.run_score.total_score} ({resolution.run_score.score_tier})"
    )
    table.add_row("Est. Value", format_money(resolution.run_score.estimated_valuation))
    table.add_row("Pending Event", "yes" if resolution.pending_event is not None else "no")
    table.add_row(
        "Resolved Event",
        "yes" if resolution.event_history_entry is not None else "no",
    )
    table.add_row("Milestones", str(len(resolution.unlocked_milestones)))
    table.add_row("Roadmap Due", "yes" if resolution.roadmap_due else "no")
    table.add_row("Quarter Due", "yes" if resolution.quarter_plan_due else "no")
    return table


def _build_turn_product_table(resolution: TurnResolution) -> Table:
    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Product", style="bold")
    table.add_column("Stage")
    table.add_column("Segment")
    table.add_column("Rev", justify="right")
    table.add_column("Cost", justify="right")
    table.add_column("+Users", justify="right")
    table.add_column("Churn", justify="right")
    table.add_column("Net", justify="right")
    table.add_column("Q", justify="right")
    table.add_column("B", justify="right")
    table.add_column("Pressure", justify="right")

    for summary in resolution.product_summaries:
        table.add_row(
            summary.product_name,
            summary.lifecycle_stage.value,
            summary.target_segment.value,
            format_money(summary.revenue),
            format_money(summary.operating_cost),
            str(summary.acquired_users),
            str(summary.churned_users),
            format_signed_int(summary.net_user_delta),
            format_signed_int(summary.quality_delta),
            format_signed_int(summary.bug_delta),
            str(summary.competitor_pressure),
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


def _build_milestone_panel(milestones: list[MilestoneEntry]) -> Panel:
    body = "\n\n".join(
        (f"[bold]{entry.title}[/bold]\n{entry.description}\nReward: {entry.reward_text}")
        for entry in milestones
    )
    return Panel(body, title="Milestones Unlocked", border_style="magenta", expand=True)


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


def _build_report_overview_panel(state: GameState, total_score: int, score_tier: str) -> Panel:
    goal_progress = evaluate_campaign_goal(state)
    effective_roadmap = get_effective_roadmap_focus(
        state.roadmap_focus,
        roadmap_set_turn=state.roadmap_set_turn,
        current_turn=state.company.current_turn,
    )
    roadmap_due = is_roadmap_due(
        roadmap_set_turn=state.roadmap_set_turn,
        current_turn=state.company.current_turn,
    )
    turns_left = get_roadmap_turns_remaining(
        roadmap_set_turn=state.roadmap_set_turn,
        current_turn=state.company.current_turn,
    )
    table = Table.grid(padding=(0, 1))
    table.add_row("Company", state.company.name)
    table.add_row("Scenario", state.scenario_title)
    table.add_row("Difficulty", state.difficulty_mode.value)
    table.add_row("Goal", goal_progress.title)
    table.add_row("Turn", str(state.company.current_turn))
    table.add_row("Cash", format_money(state.company.cash_on_hand))
    table.add_row("Reputation", str(state.company.reputation))
    table.add_row("Roadmap", effective_roadmap.value)
    table.add_row("Roadmap State", "due now" if roadmap_due else f"{turns_left} turns left")
    table.add_row("Budget", state.quarter_plan.budget_stance.value)
    table.add_row("Market", state.market_cycle.value)
    table.add_row("Run Score", f"{total_score} ({score_tier})")
    table.add_row("Goal State", "complete" if goal_progress.completed else "in progress")
    return Panel(table, title="Run Overview", border_style="magenta", expand=True)


def _build_report_score_panel(state: GameState) -> Panel:
    run_score = calculate_run_score(state)
    active_segments = sorted(
        {product.target_segment.value for product in state.products if product.is_active}
    )
    table = Table.grid(padding=(0, 1))
    table.add_row("Estimated Value", format_money(run_score.estimated_valuation))
    table.add_row("Active Products", str(run_score.active_products))
    table.add_row("Mature Products", str(run_score.mature_products))
    table.add_row("Portfolio Users", str(run_score.total_users))
    table.add_row("Headcount", str(len(state.employees)))
    table.add_row("Milestones", str(len(state.milestone_history)))
    table.add_row("Segments", ", ".join(active_segments) if active_segments else "-")
    return Panel(table, title="Scorecard", border_style="yellow", expand=True)


def _build_report_quarter_plan_panel(state: GameState) -> Panel:
    plan = state.quarter_plan
    progress = evaluate_quarter_plan(state)
    goal_progress = evaluate_campaign_goal(state)
    table = Table.grid(padding=(0, 1))
    table.add_row("Target Turn", str(plan.target_turn))
    table.add_row("Revenue Target", format_money(plan.revenue_target))
    table.add_row("User Target", str(plan.user_target))
    table.add_row("Cash Target", format_money(plan.cash_reserve_target))
    table.add_row("Headcount Cap", str(plan.headcount_cap))
    table.add_row("Revenue Progress", _format_progress(progress.revenue_progress))
    table.add_row("User Progress", _format_progress(progress.user_progress))
    table.add_row("Cash Progress", _format_progress(progress.cash_progress))
    table.add_row("Headcount OK", "yes" if progress.headcount_within_cap else "no")
    table.add_row("Plan Due", "yes" if is_quarter_plan_due(state) else "no")
    for index, line in enumerate(goal_progress.progress_lines, start=1):
        table.add_row(f"Goal {index}", line)
    return Panel(table, title="Quarter Plan", border_style="cyan", expand=True)


def _build_market_watch_panel(state: GameState) -> Panel:
    market_profile = get_market_profile(state.market_cycle)
    scale_pressure = calculate_company_scale_pressure(
        state.products,
        headcount=len(state.employees),
        current_turn=state.company.current_turn,
    )
    table = Table.grid(padding=(0, 1))
    table.add_row("Cycle", state.market_cycle.value)
    table.add_row("Turns Left", str(state.market_cycle_turns_remaining))
    table.add_row("Competitors", str(len(state.competitors)))
    table.add_row("Plan Due", "yes" if is_quarter_plan_due(state) else "no")
    table.add_row("Scale Drag", str(scale_pressure.coordination_drag))
    table.add_row("Summary", market_profile.description)
    return Panel(table, title="Market Watch", border_style="red", expand=True)


def _build_operations_panel(state: GameState) -> Panel:
    operations = calculate_operations_summary(
        state.products,
        state.employees,
        current_turn=state.company.current_turn,
    )
    overloaded_products = [
        risk.product_name for risk in operations.product_risks if risk.overload > 0
    ]
    table = Table.grid(padding=(0, 1))
    table.add_row("Load", str(operations.total_load))
    table.add_row("Capacity", str(operations.total_capacity))
    table.add_row("Overload", str(operations.overload))
    table.add_row("Ops Cost", format_money(operations.added_cost))
    table.add_row("Energy Drag", str(operations.team_energy_penalty))
    table.add_row("Morale Drag", str(operations.team_morale_penalty))
    table.add_row("Hot Spots", ", ".join(overloaded_products[:2]) if overloaded_products else "-")
    table.add_row("State", operations.summary)
    return Panel(table, title="Operations", border_style="yellow", expand=True)


def _build_late_game_panel(state: GameState) -> Panel:
    late_game = calculate_late_game_summary(
        state.products,
        current_turn=state.company.current_turn,
    )
    risk_names = [risk.product_name for risk in late_game.product_risks if risk.user_loss > 0]
    table = Table.grid(padding=(0, 1))
    table.add_row("Risk", str(late_game.total_risk))
    table.add_row("Concentration", str(late_game.concentration_risk))
    table.add_row("Renewal", str(late_game.renewal_risk))
    table.add_row("Legacy Drag", str(late_game.legacy_drag))
    table.add_row("Late Cost", format_money(late_game.added_cost))
    table.add_row("Burnout Mod", str(late_game.burnout_modifier))
    table.add_row("At Risk", ", ".join(risk_names[:2]) if risk_names else "-")
    table.add_row("State", late_game.summary)
    return Panel(table, title="Late-Game", border_style="magenta", expand=True)


def _build_finance_panel(state: GameState) -> Panel:
    runway = estimate_runway(state.company.cash_on_hand, _latest_net_cash_flow(state))
    turn_interest = (
        state.finance.debt_principal * state.finance.loan_interest_rate
        if state.finance.debt_principal > Decimal("0")
        else Decimal("0.00")
    )
    table = Table.grid(padding=(0, 1))
    table.add_row("Debt", format_money(state.finance.debt_principal))
    table.add_row("Dilution", format_rate(state.finance.equity_dilution))
    table.add_row("Investor Pressure", str(state.finance.investor_pressure))
    table.add_row("Capital Raised", format_money(state.finance.total_raised))
    table.add_row("Funding Entries", str(len(state.funding_history)))
    table.add_row("Turn Interest", format_money(turn_interest))
    table.add_row("Runway", "cashflow+" if runway is None else f"{runway} turns")
    return Panel(table, title="Finance", border_style="cyan", expand=True)


def _build_competitor_table(state: GameState) -> Table:
    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("#", justify="center", style="bold cyan")
    table.add_column("Competitor", style="bold")
    table.add_column("Segment")
    table.add_column("Strength", justify="right")
    table.add_column("Agg", justify="right")
    table.add_column("Move")
    table.add_column("Mom", justify="right")
    table.add_column("Products", justify="right")
    table.add_column("Price")

    for index, competitor in enumerate(state.competitors, start=1):
        table.add_row(
            str(index),
            competitor.name,
            competitor.focus_segment.value,
            str(competitor.strength),
            str(competitor.aggression),
            competitor.current_move.value,
            str(competitor.momentum),
            str(competitor.active_product_count),
            competitor.pricing_tier.value,
        )
    return table


def _latest_net_cash_flow(state: GameState) -> Decimal:
    if not state.turn_history:
        return Decimal("0.00")
    return state.turn_history[-1].net_cash_flow


def _build_turn_history_table(state: GameState) -> Table:
    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Turn", justify="right", style="bold cyan")
    table.add_column("Revenue", justify="right")
    table.add_column("Cost", justify="right")
    table.add_column("Net", justify="right")
    table.add_column("Cash", justify="right")
    table.add_column("Users", justify="right")
    table.add_column("Rep", justify="right")
    table.add_column("Headcount", justify="right")
    table.add_column("Roadmap")

    for entry in state.turn_history[-8:]:
        table.add_row(
            str(entry.turn),
            format_money(entry.total_revenue),
            format_money(entry.total_operating_cost),
            format_signed_money(entry.net_cash_flow),
            format_money(entry.cash_on_hand),
            str(entry.total_users),
            str(entry.reputation),
            str(entry.headcount),
            entry.roadmap_focus.value,
        )
    return table


def _build_funding_history_panel(state: GameState) -> Panel:
    if not state.funding_history:
        return Panel(
            "No funding actions recorded yet.",
            title="Funding History",
            border_style="green",
            expand=True,
        )

    return Panel(
        _build_funding_history_table(state.funding_history),
        title="Funding History",
        border_style="green",
        expand=True,
    )


def _build_recent_events_panel(state: GameState) -> Panel:
    if not state.event_history:
        return Panel(
            "No resolved events yet.",
            title="Recent Events",
            border_style="yellow",
            expand=True,
        )

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Turn", justify="right", style="bold cyan")
    table.add_column("Event", style="bold")
    table.add_column("Choice")
    table.add_column("Outcome")

    for entry in reversed(state.event_history[-5:]):
        table.add_row(
            str(entry.resolved_turn),
            entry.title,
            entry.selected_option_label,
            entry.result_text,
        )

    return Panel(table, title="Recent Events", border_style="yellow", expand=True)


def _build_milestone_history_panel(state: GameState) -> Panel:
    if not state.milestone_history:
        return Panel(
            "No milestones unlocked yet.",
            title="Milestones",
            border_style="magenta",
            expand=True,
        )

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Turn", justify="right", style="bold cyan")
    table.add_column("Milestone", style="bold")
    table.add_column("Reward")

    for entry in reversed(state.milestone_history[-5:]):
        table.add_row(
            str(entry.unlocked_turn),
            entry.title,
            entry.reward_text,
        )

    return Panel(table, title="Milestones", border_style="magenta", expand=True)


def _build_funding_history_table(entries: list[FundingHistoryEntry]) -> Table:
    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Turn", justify="right", style="bold cyan")
    table.add_column("Type", style="bold")
    table.add_column("Amount", justify="right")
    table.add_column("Dilution", justify="right")
    table.add_column("Debt", justify="right")
    table.add_column("Summary")

    for entry in reversed(entries[-5:]):
        table.add_row(
            str(entry.turn),
            entry.funding_type.value,
            format_money(entry.amount),
            format_rate(entry.dilution_added),
            format_money(entry.debt_added),
            entry.summary,
        )

    return table


def _format_progress(value: float) -> str:
    return f"{min(999, int(value * 100))}%"
