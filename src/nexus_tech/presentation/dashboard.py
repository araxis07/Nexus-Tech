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
    CustomerAccountStatus,
    Employee,
    EventHistoryEntry,
    FundingHistoryEntry,
    GameState,
    HiringCandidateStage,
    MarketSegment,
    MilestoneEntry,
    PendingEvent,
    Product,
    ProductReleaseStatus,
    RoadmapProjectStatus,
    SalesDealStage,
    SupportLaneFocus,
    SupportTier,
)
from nexus_tech.domain.money import format_money, format_rate
from nexus_tech.persistence.save_coordinator import RunArchiveSummary, SaveSlotSummary
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.balance_lab import (
    BalanceAuditResult,
    BalanceBatchResult,
    BalanceComparisonResult,
    BalanceMatrixResult,
)
from nexus_tech.simulation.balance_profiles import BalanceProfile
from nexus_tech.simulation.campaign import CampaignGoalDefinition, evaluate_campaign_goal
from nexus_tech.simulation.campaign_starts import CampaignStartDefinition
from nexus_tech.simulation.capital_planning import evaluate_capital_plan
from nexus_tech.simulation.catalog_validation import CatalogValidationReport
from nexus_tech.simulation.customers import calculate_account_revenue
from nexus_tech.simulation.endgame import (
    calculate_endgame_pressure,
    calculate_endgame_readiness,
    evaluate_exit_outcome,
)
from nexus_tech.simulation.engine import TurnResolution, get_total_users
from nexus_tech.simulation.event_registry import EventDefinition
from nexus_tech.simulation.finance import (
    build_finance_planner,
    calculate_cash_flow_forecast_scenarios,
    estimate_runway,
)
from nexus_tech.simulation.functional_budgeting import get_functional_budget_profile
from nexus_tech.simulation.governance import get_governance_tradeoff_focus
from nexus_tech.simulation.hiring import CandidateProfile
from nexus_tech.simulation.late_game import calculate_late_game_summary
from nexus_tech.simulation.market import get_market_profile
from nexus_tech.simulation.meta_progression import (
    ArchiveComparisonSummary,
    MetaProgressionSummary,
    UnlockCatalogSummary,
    build_archive_comparison,
)
from nexus_tech.simulation.objectives import evaluate_scenario_objective
from nexus_tech.simulation.operations import calculate_operations_summary
from nexus_tech.simulation.partnerships import (
    calculate_partnership_fatigue,
    calculate_partnership_portfolio,
)
from nexus_tech.simulation.planning import evaluate_quarter_plan, is_quarter_plan_due
from nexus_tech.simulation.reporting import calculate_run_badges, calculate_run_score
from nexus_tech.simulation.roadmap import (
    get_effective_roadmap_focus,
    get_roadmap_turns_remaining,
    is_roadmap_due,
)
from nexus_tech.simulation.scaling import calculate_company_scale_pressure
from nexus_tech.simulation.segments import MarketSegmentProfile
from nexus_tech.simulation.support_program import (
    calculate_support_account_risk_counts,
    calculate_support_account_risk_values,
    calculate_support_lane_snapshots,
    calculate_support_lane_staffing_plan,
    calculate_support_queue_exposure,
    calculate_support_staff_capacity,
    classify_account_support_lane,
    count_escalating_accounts,
)
from nexus_tech.simulation.team import (
    TeamCondition,
    calculate_effective_productivity,
    calculate_team_condition,
)


def render_intro(
    console: Console,
    *,
    company_name: str,
    scenario_title: str,
    campaign_start_title: str,
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
                f"Campaign Start: {campaign_start_title}\n"
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


def render_campaign_start_catalog(
    console: Console,
    starts: tuple[CampaignStartDefinition, ...],
    *,
    locked_ids: set[str] | None = None,
) -> None:
    """Render the available campaign-start modifiers."""

    locked_ids = locked_ids or set()
    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Campaign Start", style="bold")
    table.add_column("Status")
    table.add_column("Unlock")
    table.add_column("Turn")
    table.add_column("Pressure")
    table.add_column("Description")

    for start in starts:
        table.add_row(
            f"{start.title}\n[dim]{start.start_id}[/dim]",
            "locked" if start.start_id in locked_ids else "unlocked",
            (
                f"{start.unlock_reward_type}:{start.unlock_reward_id}"
                if start.unlock_reward_id and start.unlock_reward_type
                else "baseline"
            ),
            start.turn_hint,
            start.pressure_hint,
            start.description,
        )

    start_ids = ", ".join(f"{start.start_id} ({start.title})" for start in starts)
    content = Group(
        table,
        "",
        f"[dim]Use --campaign-start <id>. Available ids: {start_ids}[/dim]",
    )
    console.print(Panel(content, title="Campaign Start Catalog", border_style="cyan", expand=True))


def render_scenario_catalog(
    console: Console,
    scenarios: tuple[ScenarioDefinition, ...],
    *,
    locked_ids: set[str] | None = None,
) -> None:
    """Render the available starting scenarios."""

    locked_ids = locked_ids or set()
    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Scenario", style="bold")
    table.add_column("Status")
    table.add_column("Company")
    table.add_column("Strategy")
    table.add_column("Difficulty")
    table.add_column("Goal")
    table.add_column("Products", justify="right")
    table.add_column("Team", justify="right")
    table.add_column("Description")

    for scenario in scenarios:
        description = scenario.description
        if scenario.objective:
            objective = scenario.objective
            if scenario.objective_target > 0:
                objective = (
                    f"{objective} ({scenario.objective_metric.value} {scenario.objective_target})"
                )
            description = f"{description}\n[dim]Objective: {objective}[/dim]"
        table.add_row(
            f"{scenario.title}\n[dim]{scenario.scenario_id}[/dim]",
            "locked" if scenario.scenario_id in locked_ids else "unlocked",
            scenario.company_name,
            scenario.company_strategy.value,
            scenario.difficulty_mode.value,
            scenario.campaign_goal_id.value,
            str(len(scenario.products)),
            str(len(scenario.employees)),
            description,
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
    *,
    locked_ids: set[str] | None = None,
) -> None:
    """Render the available product templates."""

    locked_ids = locked_ids or set()
    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Template", style="bold")
    table.add_column("Status")
    table.add_column("Stage")
    table.add_column("Segment")
    table.add_column("Price")
    table.add_column("Pack")
    table.add_column("Q", justify="right")
    table.add_column("B", justify="right")
    table.add_column("Fit", justify="right")
    table.add_column("Debt", justify="right")
    table.add_column("Description")

    for template in templates:
        table.add_row(
            f"{template.title}\n[dim]{template.template_id}[/dim]",
            "locked" if template.template_id in locked_ids else "unlocked",
            template.lifecycle_stage.value,
            template.target_segment.value,
            template.pricing_tier.value,
            template.packaging_strategy.value,
            str(template.quality),
            str(template.bug_level),
            str(template.market_fit),
            str(template.technical_debt),
            template.description,
        )

    template_ids = ", ".join(f"{template.template_id} ({template.title})" for template in templates)
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


def render_candidate_pool(
    console: Console,
    candidates: tuple[CandidateProfile, ...],
) -> None:
    """Render generated hiring candidates."""

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("#", justify="right")
    table.add_column("Candidate", style="bold")
    table.add_column("Role")
    table.add_column("Seniority")
    table.add_column("Trait")
    table.add_column("Specialization")
    table.add_column("Salary", justify="right")
    table.add_column("Prod", justify="right")
    table.add_column("Why They Matter")

    for index, candidate in enumerate(candidates, start=1):
        table.add_row(
            str(index),
            candidate.full_name,
            candidate.role.value,
            candidate.seniority.value,
            candidate.trait.value,
            candidate.specialization,
            format_money(candidate.salary_expectation),
            str(candidate.expected_productivity),
            candidate.pitch,
        )

    console.print(Panel(table, title="Hiring Candidate Pool", border_style="cyan", expand=True))


def render_segment_catalog(
    console: Console,
    profiles: tuple[tuple[MarketSegment, MarketSegmentProfile], ...],
) -> None:
    """Render customer segment behavior for strategy decisions."""

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Segment", style="bold", no_wrap=True)
    table.add_column("Acquisition", justify="right")
    table.add_column("Churn Mod", justify="right")
    table.add_column("Support Cost", justify="right")
    table.add_column("Price Sens.", justify="right")
    table.add_column("Fit Need", justify="right")
    table.add_column("Quality Need", justify="right")
    table.add_column("Competitive Base", justify="right")

    for segment, profile in profiles:
        table.add_row(
            segment.value,
            f"{profile.acquisition_bonus:+d}",
            format_rate(profile.base_churn_modifier),
            f"x{profile.support_cost_multiplier}",
            f"x{profile.price_sensitivity_multiplier}",
            str(profile.market_fit_threshold),
            str(profile.quality_threshold),
            str(profile.competitor_pressure_base),
        )

    console.print(Panel(table, title="Customer Segment Profiles", border_style="cyan", expand=True))


def render_roadmap_catalog(
    console: Console,
    profiles: tuple[tuple[str, str], ...],
) -> None:
    """Render roadmap/initiative profiles available to the player."""

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Roadmap Focus", style="bold")
    table.add_column("Strategic Trade-off")

    for focus, summary in profiles:
        table.add_row(focus, summary)

    console.print(Panel(table, title="Roadmap Initiatives", border_style="cyan", expand=True))


def render_balance_profile_catalog(
    console: Console,
    profiles: tuple[BalanceProfile, ...],
) -> None:
    """Render recommended deterministic balance-lab profiles."""

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Profile", style="bold")
    table.add_column("Difficulty")
    table.add_column("Runs", justify="right")
    table.add_column("Turns", justify="right")
    table.add_column("Use Case")

    for profile in profiles:
        table.add_row(
            profile.profile_id.value,
            profile.difficulty_mode.value,
            str(profile.runs),
            str(profile.turns),
            profile.description,
        )

    console.print(Panel(table, title="Balance Profiles", border_style="cyan", expand=True))


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
    *,
    locked_ids: set[str] | None = None,
) -> None:
    """Render the available competitor archetypes."""

    locked_ids = locked_ids or set()
    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Archetype", style="bold")
    table.add_column("Status")
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
            "locked" if archetype.archetype_id in locked_ids else "unlocked",
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


def render_event_catalog(console: Console, event_definitions: tuple[EventDefinition, ...]) -> None:
    """Render the supported event registry for demo and debugging use."""

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Event", style="bold")
    table.add_column("Category")
    table.add_column("Weight", justify="right")
    table.add_column("Cooldown", justify="right")

    for definition in event_definitions:
        table.add_row(
            definition.event_id,
            definition.category.value,
            str(definition.weight),
            str(definition.cooldown_turns),
        )

    console.print(
        Panel(
            table,
            title="Event Catalog",
            border_style="cyan",
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


def render_run_archive_catalog(
    console: Console,
    archives: list[RunArchiveSummary],
) -> None:
    """Render archived completed runs with compact end-state metadata."""

    if not archives:
        console.print(
            Panel(
                "No completed runs have been archived yet.",
                title="Run Archives",
                border_style="green",
                expand=True,
            )
        )
        return

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Archive", style="bold")
    table.add_column("Company")
    table.add_column("Scenario")
    table.add_column("Turn", justify="right")
    table.add_column("Outcome")
    table.add_column("Score", justify="right")
    table.add_column("Tier")
    table.add_column("Grade")
    table.add_column("Badges")
    table.add_column("Outlook")
    table.add_column("Offer", justify="right")
    table.add_column("Value", justify="right")
    table.add_column("Cash", justify="right")
    table.add_column("Rep", justify="right")
    table.add_column("Saved")

    for archive in archives:
        status = "victory" if archive.victory_achieved else "shutdown" if archive.game_over else "-"
        table.add_row(
            archive.slot_name,
            archive.company_name,
            archive.scenario_title,
            str(archive.completed_turn),
            f"{archive.exit_outcome} / {status}",
            str(archive.total_score),
            archive.score_tier,
            archive.campaign_grade,
            ", ".join(archive.achievement_badges) if archive.achievement_badges else "-",
            archive.strategic_outlook.replace("_", " "),
            format_money(archive.offer_value),
            format_money(archive.estimated_valuation),
            format_money(archive.final_cash),
            str(archive.final_reputation),
            archive.archived_at,
        )

    best_archive = max(archives, key=lambda archive: archive.total_score)
    latest_archive = archives[0]
    outcome_count = len({archive.exit_outcome for archive in archives if archive.exit_outcome})
    summary_table = Table.grid(padding=(0, 1))
    summary_table.add_row("Runs", str(len(archives)))
    summary_table.add_row(
        "Latest", f"{latest_archive.exit_outcome} / turn {latest_archive.completed_turn}"
    )
    summary_table.add_row(
        "Best Score", f"{best_archive.total_score} ({best_archive.campaign_grade})"
    )
    summary_table.add_row(
        "Best Offer", format_money(max(archive.offer_value for archive in archives))
    )
    summary_table.add_row("Outcome Coverage", str(outcome_count))
    console.print(
        Columns(
            [
                Panel(summary_table, title="Archive Benchmarks", border_style="green", expand=True),
                Panel(table, title="Run Archives", border_style="green", expand=True),
            ],
            equal=False,
            expand=True,
        )
    )


def render_archive_comparison(console: Console, archives: list[RunArchiveSummary]) -> None:
    """Render cross-run comparison for archived completed runs."""

    if not archives:
        console.print(
            Panel(
                "No completed runs have been archived yet.",
                title="Archive Comparison",
                border_style="yellow",
                expand=True,
            )
        )
        return

    _render_archive_comparison_summary(console, build_archive_comparison(archives))


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
            "`nexus-tech tutorial`, `guide`, `glossary`, `list-scenarios`, "
            "`list-events`, `validate-content`, `doctor`"
        ),
        "",
        "[bold]Strong first turns[/bold]",
        (
            "Protect quality before bugs compound, keep cash above runway risk, "
            "and avoid over-hiring before the first clear growth signal."
        ),
    )
    console.print(Panel(content, title="Quick Guide", border_style="blue", expand=True))


def render_tutorial(console: Console) -> None:
    """Render a first-run tutorial path without starting an interactive session."""

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Step", justify="right", style="bold cyan")
    table.add_column("Player Action", style="bold")
    table.add_column("Why It Matters")
    table.add_row(
        "1",
        "Run `nexus-tech new-game --scenario founder_journey --seed 7`.",
        "Starts a repeatable demo with the default founder scenario.",
    )
    table.add_row(
        "2",
        "Review Company Overview, Product Portfolio, Finance, and Market Watch.",
        "These panels show runway, product health, pressure, and growth context.",
    )
    table.add_row(
        "3",
        "Use `hire_employee`, then assign that employee to the flagship product.",
        "A small team improves execution, but salary burn now matters.",
    )
    table.add_row(
        "4",
        "Choose either `improve_quality` or `market_product`.",
        "Quality protects retention; marketing is better once product health is stable.",
    )
    table.add_row(
        "5",
        "End the turn and read the Turn Summary.",
        "Revenue, operating cost, churn, growth, events, and team pressure resolve here.",
    )
    table.add_row(
        "6",
        "Use `view_report`, `review_customers`, and `save_game` after a few turns.",
        "Reports explain score and risk; saves prove the run can be resumed.",
    )

    console.print(
        Panel(
            table,
            title="First Run Tutorial",
            border_style="green",
            expand=True,
        )
    )


def render_glossary(console: Console) -> None:
    """Render stat explanations for players learning the simulation."""

    systems = Table(box=box.SIMPLE_HEAVY, expand=True)
    systems.add_column("System", style="bold cyan")
    systems.add_column("What It Means")
    systems.add_row("Cash", "Company runway. Below zero ends the run.")
    systems.add_row(
        "Reputation",
        "Brand trust. Helps growth, events, funding, and victory quality.",
    )
    systems.add_row(
        "Board Confidence",
        "Governance trust. Rewards disciplined capital and execution.",
    )
    systems.add_row(
        "Investor Pressure",
        "Capital-market stress. Raises finance cost and lowers score.",
    )
    systems.add_row(
        "Quality",
        "Product reliability and perceived value. Helps growth and key accounts.",
    )
    systems.add_row(
        "Bugs",
        "Visible product defects. Raises churn, incidents, and renewal pressure.",
    )
    systems.add_row(
        "Market Fit",
        "How well a product matches its segment. Helps acquisition and accounts.",
    )
    systems.add_row(
        "Technical Debt",
        "Future drag. Raises bugs, costs, churn, and delivery penalties.",
    )
    systems.add_row(
        "Key Accounts",
        "High-value customers with satisfaction, renewal risk, and expansion upside.",
    )
    systems.add_row(
        "Competitor Funding",
        "Rival capital pressure. Funded rivals become harder to ignore.",
    )

    actions = Table(box=box.SIMPLE_HEAVY, expand=True)
    actions.add_column("Action Family", style="bold cyan")
    actions.add_column("Use It When")
    actions.add_row(
        "Quality / Bugs / Debt",
        "Retention, renewals, and reputation are starting to weaken.",
    )
    actions.add_row("Marketing / Launch", "The product is healthy enough to convert new users.")
    actions.add_row(
        "Pricing / Segment",
        "You need to trade growth speed for revenue or enterprise trust.",
    )
    actions.add_row("Hiring / Assignment", "Execution bottlenecks are limiting product outcomes.")
    actions.add_row(
        "Finance",
        "Cash pressure is urgent, but dilution, debt, and board trust matter.",
    )
    actions.add_row(
        "Roadmap / Budget",
        "The company needs a multi-turn posture rather than one-off actions.",
    )

    console.print(
        Columns(
            [
                Panel(systems, title="Glossary", border_style="cyan", expand=True),
                Panel(actions, title="Decision Guide", border_style="blue", expand=True),
            ],
            equal=True,
            expand=True,
        )
    )


def render_content_health(console: Console, report: CatalogValidationReport) -> None:
    """Render data catalog and event wiring validation status."""

    overview = Table.grid(padding=(0, 1))
    overview.add_row("Status", "ok" if report.ok else "failed")
    overview.add_row("Scenarios", str(report.scenario_count))
    overview.add_row("Templates", str(report.template_count))
    overview.add_row("Rivals", str(report.rival_count))
    overview.add_row("Events", str(report.event_count))
    overview.add_row("Issues", str(len(report.issues)))

    issues = Table(box=box.SIMPLE_HEAVY, expand=True)
    issues.add_column("Issue", style="bold red" if report.issues else "green")
    if report.issues:
        for issue in report.issues:
            issues.add_row(issue)
    else:
        issues.add_row("All catalog references and event handlers are wired.")

    console.print(
        Columns(
            [
                Panel(overview, title="Content Health", border_style="cyan", expand=True),
                Panel(
                    issues,
                    title="Validation",
                    border_style="green" if report.ok else "red",
                    expand=True,
                ),
            ],
            equal=False,
            expand=True,
        )
    )


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


def render_balance_audit(console: Console, audit: BalanceAuditResult) -> None:
    """Render actionable balance warnings from a deterministic audit pass."""

    overview = Table.grid(padding=(0, 1))
    overview.add_row("Goal", audit.campaign_goal_id.value)
    overview.add_row("Runs / Cell", str(audit.runs))
    overview.add_row("Turns", str(audit.turns))
    overview.add_row("Seed Base", str(audit.seed_base))
    overview.add_row("Findings", str(len(audit.findings)))

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Severity")
    table.add_column("Scenario", style="bold")
    table.add_column("Difficulty")
    table.add_column("Issue")
    table.add_column("Avg Score", justify="right")
    table.add_column("Avg Cash", justify="right")
    table.add_column("Shutdowns", justify="right")
    table.add_column("Victories", justify="right")

    if not audit.findings:
        table.add_row("-", "-", "-", "No obvious balance risks were flagged.", "-", "-", "-", "-")
    else:
        for finding in audit.findings:
            table.add_row(
                finding.severity,
                finding.scenario_id,
                finding.difficulty_mode.value,
                finding.summary,
                f"{finding.average_score:.1f}",
                format_money(finding.average_cash),
                str(finding.shutdowns),
                str(finding.victories),
            )

    console.print(
        Columns(
            [
                Panel(overview, title="Balance Audit", border_style="cyan", expand=True),
                Panel(table, title="Tuning Findings", border_style="yellow", expand=True),
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
                _build_customer_accounts_panel(state),
                _build_operations_panel(state),
                _build_late_game_panel(state),
                _build_finance_panel(state),
                _build_capital_plan_panel(state),
                _build_governance_panel(state),
                _build_partnership_panel(state),
                _build_pipeline_summary_panel(state),
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
                _build_hiring_pipeline_panel(state),
            ],
            equal=False,
            expand=True,
        )
    )


def render_customer_view(console: Console, state: GameState) -> None:
    """Render the dedicated key-account review panel."""

    console.print(
        Columns(
            [
                _build_customer_accounts_panel(state, compact=False),
                _build_support_program_panel(state),
            ],
            equal=False,
            expand=True,
        )
    )


def render_board_view(console: Console, state: GameState) -> None:
    """Render the dedicated board and governance review panel."""

    console.print(
        Columns(
            [
                _build_finance_panel(state),
                _build_capital_plan_panel(state),
                _build_governance_panel(state),
                _build_objective_panel(state),
                _build_late_game_panel(state),
            ],
            equal=False,
            expand=True,
        )
    )


def render_partnership_view(console: Console, state: GameState) -> None:
    """Render the dedicated partnership and capital allocation view."""

    console.print(
        Columns(
            [
                _build_partnership_panel(state, compact=False),
                _build_capital_plan_panel(state),
                _build_finance_panel(state),
            ],
            equal=False,
            expand=True,
        )
    )


def render_pipeline_view(console: Console, state: GameState) -> None:
    """Render release, sales, and project execution pipeline."""

    console.print(
        Columns(
            [
                _build_release_pipeline_panel(state),
                _build_sales_pipeline_panel(state),
                _build_roadmap_project_panel(state),
                _build_hiring_pipeline_panel(state),
            ],
            equal=True,
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
                _build_objective_panel(state),
            ],
            equal=True,
            expand=True,
        )
    )
    console.print(
        Columns(
            [
                _build_finance_panel(state),
                _build_capital_plan_panel(state),
                _build_governance_panel(state),
                _build_partnership_panel(state),
                _build_customer_accounts_panel(state),
                _build_support_program_panel(state),
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
                _build_competitor_intel_panel(state),
            ],
            equal=True,
            expand=True,
        )
    )
    console.print(history_panel)
    render_pipeline_view(console, state)


def render_meta_progression(console: Console, summary: MetaProgressionSummary) -> None:
    """Render archive-derived campaign progression."""

    overview = Table(box=None, expand=True)
    overview.add_column("Metric", style="bold")
    overview.add_column("Value")
    overview.add_row("Runs", str(summary.total_runs))
    overview.add_row("Victories", str(summary.victories))
    overview.add_row("Best Score", str(summary.best_score))
    overview.add_row("Best Grade", summary.best_grade)
    overview.add_row("Avg Offer", format_money(summary.average_offer_value))
    overview.add_row("Campaign Tier", summary.campaign_tier)
    overview.add_row("Campaign Stage", summary.campaign_stage)
    overview.add_row("Achievement Prog.", summary.achievement_progress)
    overview.add_row("Outcome Coverage", summary.outcome_coverage_progress)
    overview.add_row("Reward Mix", ", ".join(summary.reward_mix) if summary.reward_mix else "-")
    overview.add_row(
        "Outcomes",
        ", ".join(summary.unique_outcomes) if summary.unique_outcomes else "-",
    )
    overview.add_row(
        "Unlocks",
        ", ".join(summary.unlocked_achievements) if summary.unlocked_achievements else "-",
    )
    overview.add_row(
        "Remaining",
        ", ".join(summary.unlocks_remaining[:3]) if summary.unlocks_remaining else "-",
    )
    highlights = "\n".join(f"- {line}" for line in summary.archive_highlights)
    ladder = "\n".join(summary.campaign_ladder)
    rewards = (
        "\n".join(f"- {reward}" for reward in summary.unlocked_rewards)
        if summary.unlocked_rewards
        else "No archive rewards unlocked yet."
    )
    console.print(
        Columns(
            [
                Panel(overview, title="Meta Progression", border_style="cyan", expand=True),
                Panel(ladder, title="Campaign Ladder", border_style="blue", expand=True),
                Panel(rewards, title="Unlocked Rewards", border_style="yellow", expand=True),
                Panel(highlights, title="Archive Highlights", border_style="magenta", expand=True),
                Panel(
                    f"{summary.next_goal}\n\nNext reward: {summary.next_reward}",
                    title="Next Goal",
                    border_style="green",
                    expand=True,
                ),
            ],
            equal=True,
            expand=True,
        )
    )


def render_unlock_catalog(console: Console, summary: UnlockCatalogSummary) -> None:
    """Render the explicit archive unlock catalog."""

    overview = Table.grid(padding=(0, 1))
    overview.add_row("Rewards", f"{summary.unlocked_rewards}/{summary.total_rewards}")
    overview.add_row("Mix", ", ".join(summary.reward_mix) if summary.reward_mix else "-")
    overview.add_row("Next Unlock", summary.next_unlock_label)

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Status", style="bold")
    table.add_column("Type")
    table.add_column("Reward")
    table.add_column("Reward Id")
    table.add_column("Achievement")
    for entry in summary.entries:
        table.add_row(
            "unlocked" if entry.unlocked else "locked",
            entry.reward_type,
            entry.reward_name,
            entry.reward_id,
            entry.title,
        )

    highlights = (
        "\n".join(f"- {entry.reward_label}" for entry in summary.entries if entry.unlocked)
        or "No archive rewards unlocked yet."
    )
    console.print(
        Columns(
            [
                Panel(overview, title="Unlock Overview", border_style="cyan", expand=True),
                Panel(highlights, title="Unlocked Rewards", border_style="yellow", expand=True),
            ],
            equal=True,
            expand=True,
        )
    )
    console.print(Panel(table, title="Unlock Catalog", border_style="green", expand=True))


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
    if (
        resolution.governance_summary.board_review_happened
        or resolution.governance_summary.board_warning_active
    ):
        console.print(
            Panel(
                resolution.governance_summary.summary,
                title="Board / Governance",
                border_style="magenta",
            )
        )
    if resolution.unlocked_milestones:
        console.print(_build_milestone_panel(resolution.unlocked_milestones))
    if (
        resolution.customer_summary.created_accounts
        or resolution.customer_summary.renewed_accounts
        or resolution.customer_summary.churned_accounts
        or resolution.customer_summary.at_risk_accounts
    ):
        console.print(
            Panel(
                resolution.customer_summary.summary,
                title="Customer Accounts",
                border_style="green",
            )
        )
    console.print(Panel(resolution.narrative, title="Outlook", border_style="green"))


def render_victory(console: Console, state: GameState) -> None:
    """Render the winning state."""

    run_score = calculate_run_score(state)
    readiness = calculate_endgame_readiness(state, run_score)
    pressure = calculate_endgame_pressure(state, readiness)
    content = Table.grid(padding=(0, 1))
    content.add_row("Outcome", state.victory_reason or "The company reached durable scale.")
    content.add_row("Run Score", f"{run_score.total_score} ({run_score.score_tier})")
    content.add_row("Grade", run_score.campaign_grade)
    content.add_row("Badges", ", ".join(calculate_run_badges(state, run_score)))
    content.add_row("Estimated Value", format_money(run_score.estimated_valuation))
    content.add_row("Strategic Outlook", readiness.strategic_outlook.replace("_", " "))
    content.add_row("Pressure Path", pressure.dominant_pressure.replace("_", " "))
    content.add_row("Durability", pressure.operating_durability)
    content.add_row(
        "Readiness",
        (
            f"IPO {readiness.ipo_readiness_score} / "
            f"M&A {readiness.acquisition_interest_score} / "
            f"Ind {readiness.independence_score}"
        ),
    )
    content.add_row("Pressure Note", pressure.summary)
    content.add_row("Watchlist", " | ".join(pressure.path_watchlist[:2]))
    if state.exit_outcome is not None:
        exit_evaluation = evaluate_exit_outcome(state, run_score)
        content.add_row("Exit Path", exit_evaluation.title)
        content.add_row("Exit Variant", exit_evaluation.ending_variant)
        content.add_row("Exit Value", format_money(exit_evaluation.offer_value))
        content.add_row("Exit Tags", ", ".join(exit_evaluation.outcome_tags))
        content.add_row("Board Readout", exit_evaluation.board_readout)
        content.add_row("Pressure Readout", exit_evaluation.pressure_readout)
        content.add_row("Path Scorecard", " | ".join(exit_evaluation.path_scorecard))
        content.add_row("Next Chapter", exit_evaluation.next_chapter)
        content.add_row("Exit Summary", state.exit_summary or exit_evaluation.summary)
    content.add_row("Portfolio Users", str(run_score.total_users))
    content.add_row("Key Accounts", str(run_score.key_accounts))
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
    table.add_column("Manager")
    table.add_column("Lead")
    table.add_column("Energy", justify="right")
    table.add_column("Morale", justify="right")
    table.add_column("Eff", justify="right")

    employee_names = {employee.id: employee.full_name for employee in employees}
    for index, employee in enumerate(employees, start=1):
        table.add_row(
            str(index),
            employee.full_name,
            employee.role.value,
            product_names.get(employee.assigned_product_id, "unassigned"),
            employee_names.get(employee.manager_id, "-"),
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
    roadmap_status = "due now" if roadmap_due else f"{turns_remaining} turns left"
    body = (
        f"[bold white]Turn {state.company.current_turn}[/bold white]\n"
        f"[cyan]Scenario:[/cyan] {state.scenario_title}\n"
        f"[cyan]Actions Left:[/cyan] {state.action_points_remaining}\n"
        f"[cyan]Roadmap:[/cyan] {effective_roadmap.value} ({roadmap_status})\n"
        f"[cyan]Market:[/cyan] {state.market_cycle.value} | "
        f"[cyan]Budget:[/cyan] {state.quarter_plan.budget_stance.value}\n"
        f"[cyan]Org Mix:[/cyan] {state.functional_budget.preset.value}\n"
        "Use the action menu below, then end the turn when you are ready to simulate."
    )
    return Panel.fit(body, title="Turn Control", border_style="blue")


def _build_company_panel(state: GameState) -> Panel:
    effective_roadmap = get_effective_roadmap_focus(
        state.roadmap_focus,
        roadmap_set_turn=state.roadmap_set_turn,
        current_turn=state.company.current_turn,
    )
    functional_budget_profile = get_functional_budget_profile(state.functional_budget)
    goal_progress = evaluate_campaign_goal(state)
    table = Table.grid(padding=(0, 1))
    table.add_row("Name", state.company.name)
    table.add_row("Scenario", state.scenario_title)
    table.add_row("Difficulty", state.difficulty_mode.value)
    table.add_row("Goal", goal_progress.title)
    objective_progress = evaluate_scenario_objective(state)
    if objective_progress.target_value > 0:
        table.add_row(
            "Scenario Obj",
            f"{objective_progress.current_value}/{objective_progress.target_value} "
            f"({objective_progress.percent}%)",
        )
    table.add_row("Cash", format_money(state.company.cash_on_hand))
    table.add_row("Reputation", str(state.company.reputation))
    table.add_row("Strategy", state.company.strategy.value)
    table.add_row("Roadmap", effective_roadmap.value)
    table.add_row("Budget", state.quarter_plan.budget_stance.value)
    table.add_row("Org Mix", state.functional_budget.preset.value)
    table.add_row(
        "Alloc",
        (
            f"E {state.functional_budget.engineering_share}% / "
            f"M {state.functional_budget.marketing_share}% / "
            f"CS {state.functional_budget.customer_success_share}% / "
            f"G&A {state.functional_budget.g_and_a_share}%"
        ),
    )
    table.add_row("Mix State", functional_budget_profile.summary)
    table.add_row("Market", state.market_cycle.value)
    table.add_row("Debt", format_money(state.finance.debt_principal))
    table.add_row("Dilution", format_rate(state.finance.equity_dilution))
    table.add_row("Status", "Game Over" if state.company.game_over else "Operating")
    return Panel(table, title="Company Overview", border_style="magenta", expand=True)


def _build_totals_panel(state: GameState) -> Panel:
    active_products = [product for product in state.products if product.is_active]
    run_score = calculate_run_score(state)
    badges = calculate_run_badges(state, run_score)
    readiness = calculate_endgame_readiness(state, run_score)
    pressure = calculate_endgame_pressure(state, readiness)
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
    table.add_row("Badges", ", ".join(badges))
    table.add_row("Estimated Value", format_money(run_score.estimated_valuation))
    table.add_row("Exit Outlook", readiness.strategic_outlook.replace("_", " "))
    table.add_row("Endgame Pressure", pressure.dominant_pressure.replace("_", " "))
    runway = estimate_runway(state.company.cash_on_hand, _latest_net_cash_flow(state))
    table.add_row("Runway", "cashflow+" if runway is None else f"{runway} turns")
    table.add_row("Competitors", str(len(state.competitors)))
    table.add_row("Scale Drag", str(scale_pressure.coordination_drag))
    operations = calculate_operations_summary(
        state.products,
        state.employees,
        current_turn=state.company.current_turn,
        customer_accounts=state.customer_accounts,
    )
    table.add_row("Ops Load", f"{operations.total_load}/{operations.total_capacity}")
    table.add_row("Ops Cost", format_money(operations.added_cost))
    table.add_row("Ticket Backlog", str(operations.support_backlog))
    table.add_row("Scale State", scale_pressure.summary)
    table.add_row("Durability", pressure.operating_durability)
    table.add_row("Pressure Note", pressure.summary)
    return Panel(table, title="Portfolio Summary", border_style="yellow", expand=True)


def _build_team_summary_panel(state: GameState) -> Panel:
    team_condition = calculate_team_condition(state.employees)
    average_energy = "-" if team_condition.headcount == 0 else str(team_condition.average_energy)
    average_morale = "-" if team_condition.headcount == 0 else str(team_condition.average_morale)
    promotion_ready = sum(1 for employee in state.employees if employee.promotion_readiness >= 70)
    high_attrition_risk = sum(1 for employee in state.employees if employee.attrition_risk >= 65)
    underperforming_count = sum(
        1 for employee in state.employees if employee.performance_rating <= 42
    )
    org_note = _format_team_org_note(team_condition)
    table = Table.grid(padding=(0, 1))
    table.add_row("Headcount", str(team_condition.headcount))
    table.add_row("Assigned", str(team_condition.assigned_headcount))
    table.add_row("Managed", str(team_condition.managed_headcount))
    table.add_row("Managers", str(team_condition.manager_headcount))
    table.add_row("Team Leads", str(team_condition.team_lead_count))
    table.add_row("Mgmt Cap", str(team_condition.management_capacity))
    table.add_row("Mgmt Layers", str(team_condition.management_layers))
    table.add_row("Max Span", str(team_condition.max_span))
    table.add_row("Span Risk", str(team_condition.span_risk))
    table.add_row("Org Drag", str(team_condition.org_drag))
    table.add_row("Overloaded", str(team_condition.overloaded_manager_count))
    table.add_row("Overload Rpts", str(team_condition.overloaded_report_count))
    table.add_row("Succession", str(team_condition.high_succession_risk_count))
    table.add_row("Salary Burn", format_money(team_condition.total_salary_cost))
    table.add_row("Avg Energy", average_energy)
    table.add_row("Avg Morale", average_morale)
    table.add_row("Burned Out", str(team_condition.burned_out_count))
    table.add_row("Ready", str(promotion_ready))
    table.add_row("Attrition", str(high_attrition_risk))
    table.add_row("Underperf", str(underperforming_count))
    table.add_row("Org Note", org_note)
    return Panel(table, title="Team Summary", border_style="cyan", expand=True)


def _format_team_org_note(team_condition: TeamCondition) -> str:
    if team_condition.org_drag == 0 and team_condition.high_succession_risk_count == 0:
        return "stable"
    if (
        team_condition.high_succession_risk_count > 0
        and team_condition.overloaded_manager_count > 0
    ):
        return "succession + manager load"
    if team_condition.overloaded_manager_count > 0:
        return "manager overload"
    if team_condition.high_succession_risk_count > 0:
        return "succession blind spots"
    if team_condition.span_risk > 0:
        return "span pressure"
    return "coordination drag"


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
    table.add_column("Pack")
    table.add_column("Cat", justify="right")
    table.add_column("Add", justify="right")
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
            product.packaging_strategy.value,
            str(product.package_catalog_depth),
            str(product.add_on_catalog_depth),
            format_rate(product.acquisition_rate),
            format_rate(product.churn_rate),
        )

    return table


def _build_dashboard_team_panel(state: GameState) -> Panel:
    if not state.employees:
        return Panel(
            "No employees hired yet. Use [bold]18[/bold] to start building the team.",
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


def _build_hiring_pipeline_panel(state: GameState) -> Panel:
    active_candidates = [
        candidate
        for candidate in state.hiring_candidates
        if candidate.stage is not HiringCandidateStage.EXPIRED
    ]
    if not active_candidates:
        return Panel(
            "No active hiring candidates. Use source_candidates to build a deeper hiring funnel.",
            title="Hiring Pipeline",
            border_style="cyan",
            expand=True,
        )

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Candidate", style="bold")
    table.add_column("Role")
    table.add_column("Stage")
    table.add_column("Accept", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Salary+", justify="right")
    table.add_column("Rounds", justify="right")
    table.add_column("Offer By", justify="right")
    table.add_column("Expiry", justify="right")
    for candidate in active_candidates[-6:]:
        table.add_row(
            candidate.full_name,
            candidate.role.value,
            candidate.stage.value,
            f"{candidate.acceptance_chance}%",
            str(candidate.interview_score),
            str(candidate.market_salary_pressure),
            str(candidate.negotiation_rounds),
            str(candidate.offer_deadline_turn),
            str(candidate.expires_turn),
        )
    return Panel(table, title="Hiring Pipeline", border_style="cyan", expand=True)


def _build_team_table(state: GameState, *, compact: bool) -> Table:
    product_names = {product.id: product.name for product in state.products}
    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("#", justify="center", style="bold cyan")
    table.add_column("Employee", style="bold")
    table.add_column("Role")
    table.add_column("Assignment")
    table.add_column("Manager")
    table.add_column("Energy", justify="right")
    table.add_column("Morale", justify="right")
    table.add_column("Eff", justify="right")

    if not compact:
        table.add_column("Seniority")
        table.add_column("Trait")
        table.add_column("Spec")
        table.add_column("Lead", justify="right")
        table.add_column("Succ", justify="right")
        table.add_column("Perf", justify="right")
        table.add_column("XP", justify="right")
        table.add_column("Ready", justify="right")
        table.add_column("Attr", justify="right")
        table.add_column("Streak", justify="right")
        table.add_column("Salary", justify="right")

    employee_names = {employee.id: employee.full_name for employee in state.employees}
    for index, employee in enumerate(state.employees, start=1):
        assignment_name = product_names.get(employee.assigned_product_id, "unassigned")
        row = [
            str(index),
            employee.full_name,
            employee.role.value,
            assignment_name,
            employee_names.get(employee.manager_id, "-"),
            "yes" if employee.is_team_lead else "-",
            str(employee.energy),
            str(employee.morale),
            str(calculate_effective_productivity(employee)),
        ]
        if not compact:
            row.extend(
                [
                    employee.seniority.value,
                    employee.trait.value,
                    employee.specialization,
                    str(employee.leadership_score),
                    str(employee.succession_risk),
                    str(employee.performance_rating),
                    str(employee.experience_points),
                    str(employee.promotion_readiness),
                    str(employee.attrition_risk),
                    str(employee.underperformance_streak),
                    format_money(employee.salary),
                ]
            )
        table.add_row(*row)

    return table


def _build_objective_panel(state: GameState) -> Panel:
    progress = evaluate_scenario_objective(state)
    if not progress.description:
        body = "No scenario-specific objective is set for this run."
    else:
        body = (
            f"{progress.description}\n"
            f"[cyan]{progress.metric.value}[/cyan]: "
            f"{progress.current_value}/{progress.target_value} ({progress.percent}%)"
        )
        if progress.complete:
            body += "\n[green]Objective complete.[/green]"
    return Panel(body, title="Scenario Objective", border_style="cyan", expand=True)


def _build_pipeline_summary_panel(state: GameState) -> Panel:
    active_releases = sum(
        1 for release in state.product_releases if release.status is ProductReleaseStatus.PLANNED
    )
    active_deals = sum(
        1
        for deal in state.sales_deals
        if deal.stage not in {SalesDealStage.CLOSED_WON, SalesDealStage.CLOSED_LOST}
    )
    active_projects = sum(
        1 for project in state.roadmap_projects if project.status is RoadmapProjectStatus.ACTIVE
    )
    active_candidates = sum(
        1
        for candidate in state.hiring_candidates
        if candidate.stage
        in {
            HiringCandidateStage.SOURCED,
            HiringCandidateStage.SCREENED,
            HiringCandidateStage.INTERVIEWED,
        }
    )
    content = Table.grid(padding=(0, 1))
    content.add_row("Releases", str(active_releases))
    content.add_row("Sales Deals", str(active_deals))
    content.add_row("Projects", str(active_projects))
    content.add_row("Candidates", str(active_candidates))
    content.add_row("Intel Notes", str(len(state.competitor_intel)))
    return Panel(content, title="Execution Pipeline", border_style="cyan", expand=True)


def _build_release_pipeline_panel(state: GameState) -> Panel:
    product_names = {product.id: product.name for product in state.products}
    releases = [
        release
        for release in state.product_releases
        if release.status is ProductReleaseStatus.PLANNED
    ]
    if not releases:
        return Panel(
            "No active release plans. Use plan_release to queue one.",
            title="Release Queue",
            border_style="blue",
            expand=True,
        )

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Product", style="bold")
    table.add_column("Type")
    table.add_column("Progress", justify="right")
    table.add_column("Risk", justify="right")
    for release in releases:
        table.add_row(
            product_names.get(release.product_id, "unknown"),
            release.release_type.value,
            f"{release.progress}/{release.required_progress}",
            str(release.risk),
        )
    return Panel(table, title="Release Queue", border_style="blue", expand=True)


def _build_sales_pipeline_panel(state: GameState) -> Panel:
    product_names = {product.id: product.name for product in state.products}
    if not state.sales_deals:
        return Panel(
            "No sales deals yet. Use create_sales_deal once a product has a clear segment.",
            title="Sales Pipeline",
            border_style="green",
            expand=True,
        )

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Deal", style="bold")
    table.add_column("Product")
    table.add_column("Stage")
    table.add_column("Plan")
    table.add_column("Package")
    table.add_column("Model")
    table.add_column("Value", justify="right")
    table.add_column("Commit", justify="right")
    table.add_column("Add-ons", justify="right")
    table.add_column("Prepay")
    table.add_column("Prob", justify="right")
    for deal in state.sales_deals[-8:]:
        commitment = (
            str(deal.seat_commitment)
            if deal.billing_model.value == "seat_based"
            else str(deal.usage_commitment)
        )
        table.add_row(
            deal.name,
            product_names.get(deal.product_id, "unknown"),
            deal.stage.value,
            deal.plan_tier.value,
            deal.subscription_package.value,
            deal.billing_model.value,
            format_money(deal.value),
            commitment,
            str(deal.add_on_commitment),
            "yes" if deal.annual_prepay_offer else "no",
            f"{deal.probability}%",
        )
    return Panel(table, title="Sales Pipeline", border_style="green", expand=True)


def _build_roadmap_project_panel(state: GameState) -> Panel:
    product_names = {product.id: product.name for product in state.products}
    if not state.roadmap_projects:
        return Panel(
            "No strategic project is active. Use start_roadmap_project for larger bets.",
            title="Roadmap Projects",
            border_style="magenta",
            expand=True,
        )

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Project", style="bold")
    table.add_column("Target")
    table.add_column("Status")
    table.add_column("Progress", justify="right")
    table.add_column("Epics", justify="right")
    table.add_column("Deadline", justify="right")
    table.add_column("Risk", justify="right")
    table.add_column("Depends")
    table.add_column("Summary")
    for project in state.roadmap_projects[-6:]:
        table.add_row(
            project.project_type.value,
            product_names.get(project.target_product_id, "company-wide"),
            project.status.value,
            f"{project.progress}/{project.required_progress}",
            f"{project.epics_completed}/{project.epic_count}",
            str(project.deadline_turn),
            str(project.delivery_risk),
            project.dependency_project_type.value
            if project.dependency_project_type is not None
            else "-",
            project.summary,
        )
    return Panel(table, title="Roadmap Projects", border_style="magenta", expand=True)


def _build_competitor_intel_panel(state: GameState) -> Panel:
    if not state.competitor_intel:
        return Panel(
            "No competitor intel captured yet.",
            title="Competitor Intel",
            border_style="red",
            expand=True,
        )

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Turn", justify="right")
    table.add_column("Rival", style="bold")
    table.add_column("Move")
    table.add_column("Signal")
    for entry in state.competitor_intel[-6:]:
        table.add_row(
            str(entry.turn),
            entry.competitor_name,
            entry.move.value,
            entry.summary,
        )
    return Panel(table, title="Competitor Intel", border_style="red", expand=True)


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
    primary_actions.add_row(
        "7",
        "set_packaging_strategy",
        "Change packaging and monetization depth.",
    )
    primary_actions.add_row("55", "run_price_increase", "Push a direct price increase.")
    primary_actions.add_row("8", "set_target_segment", "Retarget a product's customer segment.")
    primary_actions.add_row("9", "sunset_product", "Retire a weak product.")
    primary_actions.add_row("10", "set_company_strategy", "Shift company-wide focus.")
    primary_actions.add_row("11", "set_roadmap", "Pick the quarter's execution plan.")
    primary_actions.add_row("12", "set_budget_stance", "Change the quarter's spend posture.")
    primary_actions.add_row("13", "take_loan", "Trade future burn for runway.")
    primary_actions.add_row("14", "raise_angel", "Take smaller capital with dilution.")
    primary_actions.add_row("15", "raise_vc", "Raise a larger round once traction is real.")
    primary_actions.add_row("16", "repay_debt", "Reduce interest and capital pressure.")
    primary_actions.add_row("78", "refinance_debt", "Trade pricier debt for calmer covenants.")
    primary_actions.add_row("17", "review_finance", "Open the capital and runway view.")
    primary_actions.add_row("18", "hire_employee", "Add capability and salary burn.")
    primary_actions.add_row("19", "fire_employee", "Remove salary burden.")
    primary_actions.add_row("20", "assign_employee", "Put someone on a product.")
    primary_actions.add_row("21", "unassign_employee", "Pull someone off product work.")
    primary_actions.add_row(
        "22",
        "assign_manager",
        "Create reporting structure and reduce org drag.",
    )
    primary_actions.add_row("23", "clear_manager", "Remove a reporting line.")
    primary_actions.add_row("24", "rest_team", "Recover energy and morale.")
    primary_actions.add_row("31", "appoint_team_lead", "Create a squad lead for one product.")
    primary_actions.add_row("25", "review_team", "Open the detailed team view.")
    primary_actions.add_row("26", "review_customers", "Open key account renewals.")
    primary_actions.add_row("27", "invest_in_customer_success", "Improve onboarding and retention.")
    primary_actions.add_row(
        "28",
        "run_retention_play",
        "Save one at-risk account with concessions.",
    )
    primary_actions.add_row("29", "train_employee", "Increase readiness and productivity.")
    primary_actions.add_row("30", "promote_employee", "Level up a ready team member.")
    primary_actions.add_row(
        "75",
        "run_comp_review",
        "Raise pay on one teammate to cut attrition pressure.",
    )
    primary_actions.add_row(
        "76",
        "run_succession_review",
        "Build backup leadership around one manager or lead.",
    )
    primary_actions.add_row("32", "route_support_escalation", "Escalate one fragile account.")
    primary_actions.add_row(
        "79",
        "run_account_rescue",
        "Stabilize one revenue-critical account with a heavier support play.",
    )
    primary_actions.add_row(
        "81",
        "run_lane_recovery",
        "Spend on one support lane to calm the current hotspot directly.",
    )
    primary_actions.add_row(
        "85",
        "run_renewal_sweep",
        "Stabilize several near-term renewals before queue stress compounds.",
    )
    primary_actions.add_row("33", "run_add_on_campaign", "Push add-on expansion on one product.")
    primary_actions.add_row("34", "run_package_migration", "Align accounts to current packaging.")
    primary_actions.add_row("35", "execute_restructure_plan", "Run a board-backed reset.")
    primary_actions.add_row("36", "set_functional_budget", "Rebalance engineering, growth, and CS.")
    primary_actions.add_row("37", "upgrade_support_program", "Invest in reusable support leverage.")
    primary_actions.add_row("38", "plan_release", "Queue a product release plan.")
    primary_actions.add_row("39", "work_release", "Advance and ship planned releases.")
    primary_actions.add_row("40", "create_sales_deal", "Source a new sales opportunity.")
    primary_actions.add_row("41", "advance_sales_deal", "Move a deal through the pipeline.")
    primary_actions.add_row("42", "start_roadmap_project", "Start a multi-action strategic bet.")
    primary_actions.add_row("43", "work_roadmap_project", "Advance the active strategic project.")
    primary_actions.add_row("44", "review_pipeline", "Open release, sales, and project views.")
    primary_actions.add_row("45", "view_report", "Open the score, plan, and rival report.")
    primary_actions.add_row("46", "wait", "Hold position for this action.")
    primary_actions.add_row("47", "view_status", "Refresh the dashboard.")
    primary_actions.add_row("48", "end_turn", "Run the simulation tick.")
    primary_actions.add_row("49", "source_candidates", "Build a persistent hiring funnel.")
    primary_actions.add_row("50", "screen_candidate", "Run a light screen before interviews.")
    primary_actions.add_row("51", "interview_candidate", "Qualify one screened candidate.")
    primary_actions.add_row("52", "make_hiring_offer", "Convert an interviewed candidate.")
    primary_actions.add_row("53", "triage_support_backlog", "Spend cash to cut support pressure.")
    primary_actions.add_row("54", "review_board", "Open the board and governance view.")
    primary_actions.add_row("55", "run_price_increase", "Raise price on one product.")
    primary_actions.add_row("56", "reorg_team", "Rebuild reporting lines and reduce org drag.")
    primary_actions.add_row("57", "execute_board_response", "Answer the active board ask directly.")
    primary_actions.add_row(
        "58",
        "start_board_recovery_plan",
        "Commit to a short board recovery plan.",
    )
    primary_actions.add_row("59", "invest_in_support_staffing", "Add durable support headcount.")
    primary_actions.add_row(
        "60",
        "expand_package_catalog",
        "Deepen package structure on one product.",
    )
    primary_actions.add_row("61", "expand_add_on_catalog", "Create more monetizable add-ons.")
    primary_actions.add_row(
        "62",
        "make_renewal_offer",
        "Proactively stabilize one account renewal.",
    )
    primary_actions.add_row("63", "run_win_back_play", "Try to recover one churned account.")
    primary_actions.add_row(
        "64",
        "set_support_lane_focus",
        "Bias support toward onboarding, enterprise, billing, or balance.",
    )
    primary_actions.add_row(
        "70",
        "create_partnership",
        "Open one reseller, integration, or marketplace channel.",
    )
    primary_actions.add_row(
        "71",
        "invest_in_partner_enablement",
        "Improve partner quality, readiness, and conflict posture.",
    )
    primary_actions.add_row("72", "review_partnerships", "Open the channel and capital view.")
    primary_actions.add_row(
        "73",
        "set_capital_plan",
        "Change reserve posture and preferred capital source.",
    )
    primary_actions.add_row(
        "83",
        "raise_reserve_target",
        "Raise reserve expectations and shift capital toward resilience.",
    )
    primary_actions.add_row(
        "84",
        "debt_rollover",
        "Push short-term debt pressure forward at a financing cost.",
    )
    primary_actions.add_row(
        "80",
        "rebalance_capital",
        "Auto-tune capital allocation around current support and channel pressure.",
    )
    primary_actions.add_row(
        "74",
        "renegotiate_partnership",
        "Trade some margin for a calmer channel relationship.",
    )
    primary_actions.add_row(
        "77",
        "reactivate_partnership",
        "Spend directly to recover a paused or strained channel.",
    )
    primary_actions.add_row(
        "86",
        "run_channel_qbr",
        "Run a targeted channel review to reduce hotspot partner drag.",
    )
    primary_actions.add_row(
        "82",
        "pause_partnership",
        "Deliberately pause one channel to cut dependency and conflict at a revenue cost.",
    )

    utility_actions = Table(box=box.SIMPLE_HEAVY, expand=True)
    utility_actions.add_column("Key", justify="center", style="bold cyan")
    utility_actions.add_column("Utility", style="bold")
    utility_actions.add_column("Purpose")
    utility_actions.add_row("65", "save_game", "Write the current run to SQLite.")
    utility_actions.add_row("66", "load_game", "Resume a saved slot from SQLite.")
    utility_actions.add_row("67", "show_guide", "Show a compact how-to-play guide.")
    utility_actions.add_row("68", "show_glossary", "Explain stats and decision families.")
    utility_actions.add_row("69", "show_tutorial", "Show a safe first-run action path.")

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
        suggestions.append("Use [bold]18[/bold] to hire the first team member once runway is safe.")
    elif any(employee.assigned_product_id is None for employee in state.employees):
        suggestions.append(
            "Use [bold]20[/bold] to assign unallocated teammates to the product that matters most."
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
        suggestions.append("Use [bold]60[/bold] any time if you want the compact guide again.")
    if state.company.current_turn >= 2:
        suggestions.append(
            "Check [bold]40[/bold] after a turn resolves to read the run report and rival pressure."
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
    table.add_row("Org Mix", resolution.state.functional_budget.preset.value)
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
    table.add_row("Commercial", resolution.commercial_pressure_summary)
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
    table.add_row("Org Mix", state.functional_budget.preset.value)
    table.add_row("Market", state.market_cycle.value)
    table.add_row("Run Score", f"{total_score} ({score_tier})")
    table.add_row("Grade", calculate_run_score(state).campaign_grade)
    table.add_row("Goal State", "complete" if goal_progress.completed else "in progress")
    return Panel(table, title="Run Overview", border_style="magenta", expand=True)


def _build_report_score_panel(state: GameState) -> Panel:
    run_score = calculate_run_score(state)
    badges = calculate_run_badges(state, run_score)
    readiness = calculate_endgame_readiness(state, run_score)
    pressure = calculate_endgame_pressure(state, readiness)
    exit_evaluation = evaluate_exit_outcome(state, run_score)
    active_segments = sorted(
        {product.target_segment.value for product in state.products if product.is_active}
    )
    table = Table.grid(padding=(0, 1))
    table.add_row("Estimated Value", format_money(run_score.estimated_valuation))
    table.add_row("Grade", run_score.campaign_grade)
    table.add_row("Exit Path", exit_evaluation.title)
    table.add_row("Exit Variant", exit_evaluation.ending_variant)
    table.add_row("Exit Outlook", readiness.strategic_outlook.replace("_", " "))
    table.add_row("Exit Value", format_money(exit_evaluation.offer_value))
    table.add_row(
        "Readiness",
        (
            f"IPO {readiness.ipo_readiness_score} / "
            f"M&A {readiness.acquisition_interest_score} / "
            f"Ind {readiness.independence_score}"
        ),
    )
    table.add_row("Active Products", str(run_score.active_products))
    table.add_row("Mature Products", str(run_score.mature_products))
    table.add_row("Portfolio Users", str(run_score.total_users))
    table.add_row("Key Accounts", str(run_score.key_accounts))
    table.add_row("Headcount", str(len(state.employees)))
    table.add_row("Milestones", str(len(state.milestone_history)))
    table.add_row("Badges", ", ".join(badges))
    table.add_row("Exit Tags", ", ".join(exit_evaluation.outcome_tags))
    table.add_row("Segments", ", ".join(active_segments) if active_segments else "-")
    table.add_row("Board Readout", exit_evaluation.board_readout)
    table.add_row("Pressure Readout", exit_evaluation.pressure_readout)
    table.add_row("Path Scorecard", " | ".join(exit_evaluation.path_scorecard))
    table.add_row("Durability", pressure.operating_durability)
    table.add_row("Watchlist", " | ".join(pressure.path_watchlist[:2]))
    table.add_row("Next Chapter", exit_evaluation.next_chapter)
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
        customer_accounts=state.customer_accounts,
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
    table.add_row("Tickets", str(operations.support_backlog))
    table.add_row("SLA Risk", str(operations.sla_risk_accounts))
    table.add_row("Hot Spots", ", ".join(overloaded_products[:2]) if overloaded_products else "-")
    table.add_row("State", operations.summary)
    return Panel(table, title="Operations", border_style="yellow", expand=True)


def _build_customer_accounts_panel(state: GameState, *, compact: bool = True) -> Panel:
    active_accounts = [
        account for account in state.customer_accounts if account.status.value != "churned"
    ]
    if not active_accounts:
        return Panel(
            "No key accounts yet. Grow product usage and market fit to create renewal pressure.",
            title="Key Accounts",
            border_style="green",
            expand=True,
        )

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Account", style="bold")
    table.add_column("Segment")
    table.add_column("Status")
    table.add_column("Value", justify="right")
    table.add_column("Sat", justify="right")
    table.add_column("Risk", justify="right")
    if not compact:
        table.add_column("Renewal", justify="right")
        table.add_column("Expansion", justify="right")
        table.add_column("Plan")
        table.add_column("Tier")
        table.add_column("Cadence")
        table.add_column("Model")
        table.add_column("Seats", justify="right")
        table.add_column("Usage", justify="right")
        table.add_column("Add-ons", justify="right")
        table.add_column("Disc", justify="right")
        table.add_column("Prepay")
        table.add_column("Onboard", justify="right")
        table.add_column("Support", justify="right")
        table.add_column("Tickets", justify="right")
        table.add_column("SLA", justify="right")
        table.add_column("Invoice", justify="right")
        table.add_column("Pay Risk", justify="right")
        table.add_column("Renewal", justify="right")
        table.add_column("Package")
        table.add_column("Dunning", justify="right")
        table.add_column("Esc", justify="right")
        table.add_column("Queue Age", justify="right")
        table.add_column("Lane")
        table.add_column("Offer")

    for account in active_accounts:
        row = [
            account.name,
            account.segment.value,
            account.status.value,
            format_money(account.contract_value),
            str(account.satisfaction),
            str(account.churn_risk),
        ]
        if not compact:
            row.extend(
                [
                    str(account.renewal_turn),
                    str(account.expansion_potential),
                    account.plan_tier.value,
                    account.support_tier.value,
                    account.contract_cadence.value,
                    account.billing_model.value,
                    str(account.seat_count),
                    str(account.usage_units),
                    str(account.add_on_count),
                    format_rate(account.discount_rate),
                    "yes" if account.annual_prepay else "no",
                    str(account.onboarding_health),
                    str(account.support_load),
                    str(account.open_tickets),
                    str(account.sla_breach_risk),
                    str(account.invoice_risk),
                    str(account.failed_payment_risk),
                    str(account.renewal_health),
                    account.subscription_package.value,
                    str(account.dunning_steps),
                    str(account.escalation_count),
                    str(account.ticket_queue_age),
                    classify_account_support_lane(account).value,
                    (
                        account.renewal_offer_type.value
                        if account.renewal_offer_type is not None
                        else "-"
                    ),
                ]
            )
        table.add_row(*row)

    content = Group(
        table,
        "",
        (
            "[dim]Recurring account revenue: "
            f"{format_money(calculate_account_revenue(state.customer_accounts))}[/dim]"
        ),
    )
    return Panel(content, title="Key Accounts", border_style="green", expand=True)


def _build_support_program_panel(state: GameState) -> Panel:
    escalating_accounts = count_escalating_accounts(state.customer_accounts)
    staffing_capacity = calculate_support_staff_capacity(state)
    lane_snapshots = calculate_support_lane_snapshots(state)
    staffing_plan = calculate_support_lane_staffing_plan(state)
    queue_exposure = calculate_support_queue_exposure(state)
    revenue_at_risk_accounts, renewal_pressure_accounts = calculate_support_account_risk_counts(
        state
    )
    revenue_at_risk_value, renewal_pressure_value = calculate_support_account_risk_values(state)
    white_glove_risk_value = sum(
        (
            account.contract_value
            for account in state.customer_accounts
            if account.status is not CustomerAccountStatus.CHURNED
            and account.support_tier is SupportTier.WHITE_GLOVE
            and (
                account.ticket_queue_age >= BALANCE.support_program_queue_age_threshold + 1
                or account.open_tickets >= BALANCE.support_program_escalation_ticket_threshold
                or account.sla_breach_risk >= state.support_program.sla_target
            )
        ),
        Decimal("0.00"),
    )
    priority_breach_accounts = sum(
        1
        for account in state.customer_accounts
        if account.support_tier.value == "priority"
        and account.sla_breach_risk >= state.support_program.sla_target
    )
    white_glove_breach_accounts = sum(
        1
        for account in state.customer_accounts
        if account.support_tier.value == "white_glove"
        and account.sla_breach_risk >= state.support_program.sla_target
    )
    lane_counts = {
        "onboarding": 0,
        "enterprise": 0,
        "billing": 0,
    }
    for account in state.customer_accounts:
        lane = classify_account_support_lane(account)
        if lane.value in lane_counts:
            lane_counts[lane.value] += 1
    staffing_gap = max(
        0,
        escalating_accounts
        + sum(1 for account in state.customer_accounts if account.segment.value == "enterprise")
        - max(1, staffing_capacity // 3),
    )
    table = Table.grid(padding=(0, 1))
    table.add_row("Knowledge Base", str(state.support_program.knowledge_base_level))
    table.add_row("Automation", str(state.support_program.automation_level))
    table.add_row("SLA Target", str(state.support_program.sla_target))
    table.add_row("Lane Focus", state.support_program.lane_focus.value)
    table.add_row("Staffing", str(state.support_program.staffing_level))
    table.add_row("Staff Cap", str(staffing_capacity))
    table.add_row("Staff Gap", str(staffing_gap))
    table.add_row("Backlog Queue", str(state.support_program.backlog_queue))
    table.add_row("Esc Queue", str(state.support_program.escalation_queue))
    table.add_row("Queue Age", str(state.support_program.queue_age_pressure))
    table.add_row("Onboarding Q", str(state.support_program.onboarding_ticket_pressure))
    table.add_row("Enterprise Q", str(state.support_program.enterprise_ticket_pressure))
    table.add_row("Billing Q", str(state.support_program.billing_ticket_pressure))
    table.add_row("Revenue at Risk", str(revenue_at_risk_accounts))
    table.add_row("Risk Value", format_money(revenue_at_risk_value))
    table.add_row(
        "Enterprise Queue $",
        format_money(queue_exposure.enterprise_queue_exposure_value),
    )
    table.add_row(
        "Renewal Queue $",
        format_money(queue_exposure.renewal_queue_exposure_value),
    )
    table.add_row("White-Glove Risk", format_money(white_glove_risk_value))
    table.add_row(
        "Premium Queue $",
        format_money(queue_exposure.premium_queue_exposure_value),
    )
    table.add_row(
        "High-Value Risk",
        str(
            sum(
                1
                for account in state.customer_accounts
                if account.status is not CustomerAccountStatus.CHURNED
                and account.contract_value >= BALANCE.support_program_high_value_contract_threshold
                and (
                    account.ticket_queue_age >= BALANCE.support_program_queue_age_threshold
                    or account.open_tickets >= BALANCE.support_program_escalation_ticket_threshold
                    or account.sla_breach_risk >= state.support_program.sla_target
                )
            )
        ),
    )
    table.add_row("Renewal Pressure", str(renewal_pressure_accounts))
    table.add_row("Renewal Value", format_money(renewal_pressure_value))
    table.add_row("Priority Breach", str(priority_breach_accounts))
    table.add_row("White-Glove Breach", str(white_glove_breach_accounts))
    table.add_row("WG Queue Risk", str(queue_exposure.white_glove_queue_risk_accounts))
    table.add_row("Severe Queue", str(queue_exposure.severe_queue_accounts))
    table.add_row("Lane Saturation", str(queue_exposure.lane_saturation_index))
    table.add_row(
        "Recovery Ready",
        str(
            sum(
                1
                for account in state.customer_accounts
                if account.status is not CustomerAccountStatus.CHURNED
                and account.open_tickets == 0
                and account.sla_breach_risk < max(1, state.support_program.sla_target // 2)
                and account.ticket_queue_age <= BALANCE.support_program_recovery_queue_age_max
                and (
                    account.satisfaction < 78
                    or account.renewal_health < 78
                    or account.churn_risk > 0
                )
            )
        ),
    )
    table.add_row(
        "Lane Cap",
        (
            f"O {lane_snapshots[SupportLaneFocus.ONBOARDING].capacity} / "
            f"E {lane_snapshots[SupportLaneFocus.ENTERPRISE].capacity} / "
            f"B {lane_snapshots[SupportLaneFocus.BILLING].capacity}"
        ),
    )
    table.add_row(
        "Lane Overflow",
        (
            f"O {lane_snapshots[SupportLaneFocus.ONBOARDING].overflow} / "
            f"E {lane_snapshots[SupportLaneFocus.ENTERPRISE].overflow} / "
            f"B {lane_snapshots[SupportLaneFocus.BILLING].overflow}"
        ),
    )
    table.add_row(
        "Lane Staff",
        (
            f"O {staffing_plan[SupportLaneFocus.ONBOARDING]} / "
            f"E {staffing_plan[SupportLaneFocus.ENTERPRISE]} / "
            f"B {staffing_plan[SupportLaneFocus.BILLING]}"
        ),
    )
    table.add_row(
        "Lane Mix",
        (
            f"O {lane_counts['onboarding']} / "
            f"E {lane_counts['enterprise']} / "
            f"B {lane_counts['billing']}"
        ),
    )
    table.add_row("Resolved", str(state.support_program.resolved_last_turn))
    table.add_row("Deflection", str(state.support_program.deflection_score))
    table.add_row("SLA Breaches", str(state.support_program.sla_breaches_last_turn))
    table.add_row(
        "SLA Credit Cost",
        format_money(
            (
                Decimal(priority_breach_accounts)
                * BALANCE.support_program_service_cost_per_priority_sla_credit
            )
            + (
                Decimal(white_glove_breach_accounts)
                * BALANCE.support_program_service_cost_per_white_glove_sla_credit
            )
        ),
    )
    table.add_row("Service Cost", format_money(state.support_program.service_cost_last_turn))
    table.add_row("Escalations", str(escalating_accounts))
    table.add_row("Premium Queue Accts", str(queue_exposure.premium_queue_risk_accounts))
    table.add_row("Ent Queue Accts", str(queue_exposure.enterprise_queue_risk_accounts))
    table.add_row("Ren Queue Accts", str(queue_exposure.renewal_queue_risk_accounts))
    table.add_row("Hotspot Lane", queue_exposure.hotspot_lane.value)
    table.add_row("Hotspot Overflow", str(queue_exposure.hotspot_lane_overflow))
    table.add_row("Hotspot Accts", str(queue_exposure.hotspot_lane_account_count))
    table.add_row("Focus Gap", str(queue_exposure.focus_alignment_gap))
    return Panel(table, title="Support Program", border_style="green", expand=True)


def _build_late_game_panel(state: GameState) -> Panel:
    late_game = calculate_late_game_summary(
        state.products,
        current_turn=state.company.current_turn,
        headcount=len(state.employees),
    )
    pressure = calculate_endgame_pressure(state)
    risk_names = [risk.product_name for risk in late_game.product_risks if risk.user_loss > 0]
    table = Table.grid(padding=(0, 1))
    table.add_row("Risk", str(late_game.total_risk))
    table.add_row("Concentration", str(late_game.concentration_risk))
    table.add_row("Renewal", str(late_game.renewal_risk))
    table.add_row("Legacy Drag", str(late_game.legacy_drag))
    table.add_row("Org Drag", str(late_game.org_drag))
    table.add_row("Maint Crisis", str(late_game.maintenance_crisis))
    table.add_row("Innovation Gap", str(late_game.innovation_gap))
    table.add_row("Late Cost", format_money(late_game.added_cost))
    table.add_row("Burnout Mod", str(late_game.burnout_modifier))
    table.add_row("Support Fragility", str(pressure.support_fragility))
    table.add_row("Channel Fragility", str(pressure.channel_fragility))
    table.add_row("Commercial Frag", str(pressure.commercial_fragility))
    table.add_row("Capital Frag", str(pressure.capital_fragility))
    table.add_row("Reset Risk", str(pressure.board_reset_risk))
    table.add_row("Pressure Path", pressure.dominant_pressure.replace("_", " "))
    table.add_row("Clarity", pressure.strategic_clarity)
    table.add_row("Durability", pressure.operating_durability)
    table.add_row("Path Gap", str(pressure.path_gap))
    table.add_row("Scorecard", " | ".join(pressure.path_scorecard[:2]))
    table.add_row("Watchlist", " | ".join(pressure.path_watchlist[:2]))
    table.add_row("At Risk", ", ".join(risk_names[:2]) if risk_names else "-")
    table.add_row("State", late_game.summary)
    return Panel(table, title="Late-Game", border_style="magenta", expand=True)


def _build_finance_panel(state: GameState) -> Panel:
    runway = estimate_runway(state.company.cash_on_hand, _latest_net_cash_flow(state))
    portfolio = calculate_partnership_portfolio(state)
    queue_exposure = calculate_support_queue_exposure(state)
    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state, readiness)
    revenue_at_risk_value, renewal_pressure_value = calculate_support_account_risk_values(state)
    base_forecast, conservative_forecast, aggressive_forecast = (
        calculate_cash_flow_forecast_scenarios(
            state.company.cash_on_hand,
            state.turn_history,
            latest_net_cash_flow=_latest_net_cash_flow(state),
            finance=state.finance,
            capital_plan=state.capital_plan,
        )
    )
    turn_interest = (
        state.finance.debt_principal * state.finance.loan_interest_rate
        if state.finance.debt_principal > Decimal("0")
        else Decimal("0.00")
    )
    planner = build_finance_planner(
        state.company,
        state.finance,
        state.turn_history,
        latest_net_cash_flow=_latest_net_cash_flow(state),
        capital_plan=state.capital_plan,
        support_backlog=state.support_program.backlog_queue,
        support_escalations=state.support_program.escalation_queue,
        revenue_at_risk_value=revenue_at_risk_value,
        renewal_pressure_value=renewal_pressure_value,
        channel_conflict_index=portfolio.channel_conflict_index,
        channel_dependency_risk=portfolio.channel_dependency_risk,
        commercial_dependency_score=portfolio.commercial_dependency_score,
        volatile_revenue_share_percent=portfolio.volatile_revenue_share_percent,
        enterprise_queue_exposure_value=queue_exposure.enterprise_queue_exposure_value,
        renewal_queue_exposure_value=queue_exposure.renewal_queue_exposure_value,
        enterprise_queue_risk_accounts=queue_exposure.enterprise_queue_risk_accounts,
        renewal_queue_risk_accounts=queue_exposure.renewal_queue_risk_accounts,
        premium_queue_risk_accounts=queue_exposure.premium_queue_risk_accounts,
        support_lane_saturation_index=queue_exposure.lane_saturation_index,
        support_lane_focus=state.support_program.lane_focus,
        support_hotspot_lane=queue_exposure.hotspot_lane,
        support_hotspot_lane_overflow=queue_exposure.hotspot_lane_overflow,
        hotspot_lane_account_count=queue_exposure.hotspot_lane_account_count,
        focus_alignment_gap=queue_exposure.focus_alignment_gap,
        recovery_drag_score=portfolio.recovery_drag_score,
        paused_dependency_score=portfolio.paused_dependency_score,
        paused_revenue_share_percent=portfolio.paused_revenue_share_percent,
        hotspot_dependency_score=portfolio.hotspot_dependency_score,
        hotspot_revenue_share_percent=portfolio.hotspot_revenue_share_percent,
        hotspot_channel=portfolio.hotspot_channel,
        hotspot_status_note=portfolio.hotspot_status_note,
        strategic_outlook=readiness.strategic_outlook,
        dominant_endgame_pressure=pressure.dominant_pressure,
        commercial_fragility=pressure.commercial_fragility,
        capital_fragility=pressure.capital_fragility,
    )
    table = Table.grid(padding=(0, 1))
    table.add_row("Debt", format_money(state.finance.debt_principal))
    table.add_row("Dilution", format_rate(state.finance.equity_dilution))
    table.add_row("Investor Pressure", str(state.finance.investor_pressure))
    table.add_row("Board Confidence", str(state.finance.board_confidence))
    table.add_row("Covenant Risk", str(state.finance.covenant_risk))
    table.add_row("Missed Targets", str(state.finance.missed_board_targets))
    table.add_row("Capital Raised", format_money(state.finance.total_raised))
    table.add_row("Funding Entries", str(len(state.funding_history)))
    table.add_row("Turn Interest", format_money(turn_interest))
    table.add_row("Burn Multiple", f"{state.finance.burn_multiple:.2f}x")
    table.add_row("Runway", "cashflow+" if runway is None else f"{runway} turns")
    table.add_row("Base Forecast", format_money(base_forecast.projected_net_cash_flow))
    table.add_row(
        "Base Runway",
        "cashflow+"
        if base_forecast.projected_runway_turns is None
        else f"{base_forecast.projected_runway_turns} turns",
    )
    table.add_row("Conservative", format_money(conservative_forecast.projected_net_cash_flow))
    table.add_row(
        "Consv Runway",
        "cashflow+"
        if conservative_forecast.projected_runway_turns is None
        else f"{conservative_forecast.projected_runway_turns} turns",
    )
    table.add_row("Aggressive", format_money(aggressive_forecast.projected_net_cash_flow))
    table.add_row(
        "Aggr Runway",
        "cashflow+"
        if aggressive_forecast.projected_runway_turns is None
        else f"{aggressive_forecast.projected_runway_turns} turns",
    )
    table.add_row("Plan Horizon", f"{planner.horizon_turns} turns")
    table.add_row(
        "End Cash",
        (
            f"B {format_money(planner.base_end_cash)} / "
            f"C {format_money(planner.conservative_end_cash)} / "
            f"A {format_money(planner.aggressive_end_cash)}"
        ),
    )
    table.add_row(
        "Reserve Break",
        (
            f"B {planner.reserve_hit_turn_base or '-'} / "
            f"C {planner.reserve_hit_turn_conservative or '-'} / "
            f"A {planner.reserve_hit_turn_aggressive or '-'}"
        ),
    )
    table.add_row("Reserve Gap", format_signed_money(planner.reserve_gap))
    table.add_row("Rec. Posture", planner.recommended_posture)
    table.add_row("Reserve Risk", planner.reserve_break_risk)
    table.add_row("Alloc Signal", planner.allocation_signal)
    table.add_row("Capital Mix", " | ".join(planner.capital_mix))
    table.add_row("Funding Posture", planner.funding_posture)
    table.add_row("Dilution Outlook", planner.dilution_outlook)
    table.add_row("Covenant Outlook", planner.covenant_outlook)
    table.add_row("Reserve Plan", planner.reserve_plan)
    table.add_row("Debt Rollover", planner.debt_rollover_signal)
    table.add_row("Funding Window", planner.funding_window)
    table.add_row(
        "Reserve Recovery",
        "already met"
        if planner.reserve_recovery_turn == 0
        else (
            "-"
            if planner.reserve_recovery_turn is None
            else f"{planner.reserve_recovery_turn} turns"
        ),
    )
    table.add_row("Action Window", planner.capital_action_window)
    table.add_row("Tradeoff", planner.tradeoff_note)
    table.add_row("Liquidity Risk", planner.liquidity_risk)
    table.add_row("Exec Drag", planner.execution_drag)
    table.add_row("Comm Risk", planner.commercial_financing_risk)
    table.add_row("Support Lane", planner.support_lane_signal)
    table.add_row("Channel Recovery", planner.channel_recovery_note)
    table.add_row("Lane Focus Note", planner.lane_focus_note)
    table.add_row("Queue Hotspot", planner.queue_hotspot_note)
    table.add_row("Dependency Hotspot", planner.dependency_hotspot_note)
    table.add_row("Channel Hotspot", planner.channel_hotspot_note)
    table.add_row("Path Bias", planner.path_pressure_bias)
    table.add_row("Rebalance", planner.capital_rebalance_note)
    table.add_row("Priority", planner.capital_priority)
    table.add_row("Funding Resilience", planner.funding_resilience)
    table.add_row("Capital Discipline", str(planner.capital_discipline_index))
    table.add_row("Scenario Compare", " | ".join(planner.scenario_compare))
    table.add_row("Action Seq", " | ".join(planner.action_sequence))
    table.add_row("Alloc Actions", " | ".join(planner.allocation_actions))
    table.add_row("Next Actions", " | ".join(planner.recommended_actions))
    table.add_row("Planner Alert", planner.capital_alert)
    table.add_row("Planner", planner.summary)
    return Panel(table, title="Finance", border_style="cyan", expand=True)


def _build_capital_plan_panel(state: GameState) -> Panel:
    latest_net_cash_flow = _latest_net_cash_flow(state)
    reserve_gap = state.company.cash_on_hand - state.capital_plan.reserve_target
    capital_drift = evaluate_capital_plan(
        state.company,
        state.finance,
        state.capital_plan,
        latest_net_cash_flow=latest_net_cash_flow,
        technical_debt_load=sum(
            product.technical_debt for product in state.products if product.is_active
        ),
        active_channels=sum(
            1 for partnership in state.partnerships if partnership.status.value != "paused"
        ),
        support_backlog=state.support_program.backlog_queue,
    )
    table = Table.grid(padding=(0, 1))
    table.add_row("Mode", state.capital_plan.mode.value)
    table.add_row("Source Bias", state.capital_plan.source_preference.value)
    table.add_row("Horizon", f"{state.capital_plan.planning_horizon_turns} turns")
    table.add_row("Reserve Target", format_money(state.capital_plan.reserve_target))
    table.add_row("Reserve Gap", format_signed_money(reserve_gap))
    table.add_row("Reserve State", capital_drift.reserve_status)
    table.add_row(
        "Allocation",
        (
            f"P {state.capital_plan.product_investment_share}% / "
            f"GTM {state.capital_plan.go_to_market_share}% / "
            f"Reserve {state.capital_plan.reserve_share}%"
        ),
    )
    table.add_row("Latest Cashflow", format_signed_money(latest_net_cash_flow))
    table.add_row("Alignment Score", str(capital_drift.alignment_score))
    table.add_row("Execution", capital_drift.execution_status)
    table.add_row(
        "Plan Drift",
        (
            f"P {capital_drift.investor_pressure_delta:+d} / "
            f"C {capital_drift.covenant_risk_delta:+d} / "
            f"B {capital_drift.board_confidence_delta:+d}"
        ),
    )
    table.add_row("Alignment", capital_drift.summary)
    table.add_row("Recommended", capital_drift.recommended_posture)
    return Panel(table, title="Capital Plan", border_style="bright_cyan", expand=True)


def _build_partnership_panel(state: GameState, *, compact: bool = True) -> Panel:
    if not state.partnerships:
        return Panel(
            "No partnerships yet. Use create_partnership to open channel distribution.",
            title="Partnerships",
            border_style="magenta",
            expand=True,
        )

    product_names = {product.id: product.name for product in state.products}
    portfolio = calculate_partnership_portfolio(state)
    if compact:
        channels = sorted({deal.channel.value for deal in state.partnerships})
        table = Table.grid(padding=(0, 1))
        table.add_row("Count", str(portfolio.total_count))
        table.add_row("Channels", ", ".join(channels))
        table.add_row(
            "Active / Strained / Rec / Paused",
            (
                f"{portfolio.active_count} / {portfolio.strained_count} / "
                f"{portfolio.recovery_count} / {portfolio.paused_count}"
            ),
        )
        table.add_row("Dominant", portfolio.dominant_channel)
        table.add_row("Sourced Users", str(portfolio.sourced_users))
        table.add_row("Sourced Revenue", format_money(portfolio.sourced_revenue))
        table.add_row("Avg Fatigue", str(portfolio.average_fatigue))
        table.add_row("Neglected", str(portfolio.neglected_count))
        table.add_row("Recovery Ready", str(portfolio.recovery_ready_count))
        table.add_row("Renegotiate", str(portfolio.renegotiation_ready_count))
        table.add_row("Conflict", str(portfolio.channel_conflict_index))
        table.add_row("Rev Share", f"{portfolio.weighted_rev_share_percent}%")
        table.add_row("Dominant Share", f"{portfolio.dominant_share_percent}%")
        table.add_row("Paused Rev Share", f"{portfolio.paused_revenue_share_percent}%")
        table.add_row("Strained Rev Share", f"{portfolio.strained_revenue_share_percent}%")
        table.add_row("Direct Conflict", str(portfolio.direct_sales_conflict_accounts))
        table.add_row("Fatigued Rev Share", f"{portfolio.fatigued_revenue_share_percent}%")
        table.add_row("Recovery Rev Share", f"{portfolio.recovery_revenue_share_percent}%")
        table.add_row("Volatile Rev Share", f"{portfolio.volatile_revenue_share_percent}%")
        table.add_row("Volatility", str(portfolio.channel_volatility_index))
        table.add_row("Concentration", str(portfolio.concentration_risk))
        table.add_row("Recovery Drag", str(portfolio.recovery_drag_score))
        table.add_row("Paused Dependency", str(portfolio.paused_dependency_score))
        table.add_row("Renegotiate P", str(portfolio.renegotiation_pressure))
        table.add_row("Rev Share P", str(portfolio.rev_share_pressure))
        table.add_row("Fatigue Hotspots", str(portfolio.fatigue_hotspot_count))
        table.add_row("Hotspot", portfolio.hotspot_channel)
        table.add_row("Hotspot Share", f"{portfolio.hotspot_revenue_share_percent}%")
        table.add_row("Hotspot Dep", str(portfolio.hotspot_dependency_score))
        table.add_row("Dependency Risk", str(portfolio.channel_dependency_risk))
        table.add_row("Comm Dependency", str(portfolio.commercial_dependency_score))
        table.add_row("Hotspot Note", portfolio.hotspot_status_note)
        table.add_row("Mix Note", portfolio.channel_mix_note)
        table.add_row("Health", portfolio.summary)
        return Panel(table, title="Partnerships", border_style="magenta", expand=True)

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Partner", style="bold")
    table.add_column("Product")
    table.add_column("Channel")
    table.add_column("Status")
    table.add_column("Enable", justify="right")
    table.add_column("Risk", justify="right")
    table.add_column("Conflict", justify="right")
    table.add_column("Fatigue", justify="right")
    table.add_column("Rev Share", justify="right")
    table.add_column("Sourced Rev", justify="right")
    for partnership in state.partnerships:
        table.add_row(
            partnership.name,
            product_names.get(partnership.product_id, "unknown"),
            partnership.channel.value,
            partnership.status.value,
            str(partnership.enablement_level),
            str(partnership.risk),
            str(partnership.conflict_pressure),
            str(calculate_partnership_fatigue(state, partnership)),
            format_rate(partnership.rev_share_rate),
            format_money(partnership.sourced_revenue),
        )
    return Panel(table, title="Partnerships", border_style="magenta", expand=True)


def _build_governance_panel(state: GameState) -> Panel:
    directive = state.finance.board_directive.value.replace("_", " ")
    tradeoff_focus = get_governance_tradeoff_focus(state)
    table = Table.grid(padding=(0, 1))
    table.add_row("Board Confidence", str(state.finance.board_confidence))
    table.add_row("Board Score", str(state.finance.board_score))
    table.add_row("Board Pressure", str(state.finance.board_pressure))
    table.add_row("Governance Risk", str(state.finance.governance_risk))
    table.add_row("Directive", directive)
    table.add_row("Resolution", state.finance.board_resolution.value.replace("_", " "))
    table.add_row("Resolution Due", "yes" if state.finance.board_resolution_due else "no")
    table.add_row("Resolution Window", str(state.finance.board_resolution_window))
    table.add_row("Miss Streak", str(state.finance.board_resolution_miss_streak))
    table.add_row("Board Ask", state.finance.active_board_ask.value.replace("_", " "))
    table.add_row(
        "Trade-off",
        tradeoff_focus.value.replace("_", " ") if tradeoff_focus is not None else "-",
    )
    table.add_row(
        "Scorecard",
        (
            f"P {state.finance.board_profitability_score} / "
            f"R {state.finance.board_reliability_score} / "
            f"T {state.finance.board_team_health_score} / "
            f"F {state.finance.board_portfolio_focus_score}"
        ),
    )
    table.add_row("Recovery Focus", state.finance.board_recovery_focus.value.replace("_", " "))
    table.add_row("Recovery Turns", str(state.finance.board_recovery_turns_remaining))
    table.add_row("Warning", "active" if state.finance.board_warning_active else "clear")
    table.add_row("Warn Level", str(state.finance.board_warning_level))
    table.add_row(
        "Crisis",
        (
            f"L{state.finance.governance_crisis_level}"
            if state.finance.governance_crisis_active
            else "clear"
        ),
    )
    table.add_row("Quarterly Reviews", str(state.finance.quarterly_review_count))
    table.add_row("Restructure", str(state.finance.restructuring_pressure))
    table.add_row(
        "Last Review",
        str(state.finance.last_board_review_turn)
        if state.finance.last_board_review_turn is not None
        else "-",
    )
    table.add_row("Covenant Risk", str(state.finance.covenant_risk))
    table.add_row("Missed Targets", str(state.finance.missed_board_targets))
    return Panel(table, title="Board / Governance", border_style="magenta", expand=True)


def _render_archive_comparison_summary(
    console: Console,
    comparison: ArchiveComparisonSummary,
) -> None:
    benchmarks = Table.grid(padding=(0, 1))
    benchmarks.add_row("Runs", str(comparison.compared_runs))
    benchmarks.add_row("Latest", comparison.latest_label)
    benchmarks.add_row("Avg Score", str(comparison.average_score))
    benchmarks.add_row("Avg Offer", format_money(comparison.average_offer_value))
    benchmarks.add_row("Avg Cash", format_money(comparison.average_final_cash))

    leaders = Table.grid(padding=(0, 1))
    leaders.add_row("Best Score", comparison.best_score_label)
    leaders.add_row("Best Offer", comparison.best_offer_label)
    leaders.add_row("Best Cash", comparison.strongest_cash_label)
    leaders.add_row("Best Reputation", comparison.strongest_reputation_label)
    leaders.add_row("Best IPO", comparison.best_ipo_label)
    leaders.add_row("Best M&A", comparison.best_acquisition_label)
    leaders.add_row("Best Independence", comparison.best_independence_label)
    leaders.add_row("Best Reset", comparison.best_restructure_label)

    coverage = Table.grid(padding=(0, 1))
    coverage.add_row(
        "Outcomes",
        ", ".join(comparison.outcome_mix) if comparison.outcome_mix else "-",
    )
    coverage.add_row("Dominant", comparison.dominant_path.replace("_", " "))
    coverage.add_row(
        "Missing",
        ", ".join(path.replace("_", " ") for path in comparison.missing_outcomes)
        if comparison.missing_outcomes
        else "-",
    )
    coverage.add_row(
        "Grades",
        ", ".join(comparison.grade_mix) if comparison.grade_mix else "-",
    )
    coverage.add_row(
        "Badges",
        ", ".join(comparison.badge_coverage) if comparison.badge_coverage else "-",
    )
    coverage.add_row("Path Note", comparison.path_balance_note)
    coverage.add_row("Next Gap", comparison.next_gap)
    coverage.add_row("Recommendation", comparison.recommendation)

    console.print(
        Columns(
            [
                Panel(benchmarks, title="Archive Comparison", border_style="yellow", expand=True),
                Panel(leaders, title="Run Leaders", border_style="cyan", expand=True),
                Panel(coverage, title="Coverage", border_style="magenta", expand=True),
            ],
            equal=True,
            expand=True,
        )
    )


def _build_competitor_table(state: GameState) -> Table:
    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("#", justify="center", style="bold cyan")
    table.add_column("Competitor", style="bold")
    table.add_column("Archetype")
    table.add_column("Segment")
    table.add_column("Strength", justify="right")
    table.add_column("Agg", justify="right")
    table.add_column("Move")
    table.add_column("Mom", justify="right")
    table.add_column("Funding", justify="right")
    table.add_column("Products", justify="right")
    table.add_column("Price")

    for index, competitor in enumerate(state.competitors, start=1):
        table.add_row(
            str(index),
            competitor.name,
            competitor.archetype_id or "-",
            competitor.focus_segment.value,
            str(competitor.strength),
            str(competitor.aggression),
            competitor.current_move.value,
            str(competitor.momentum),
            str(competitor.funding_level),
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
