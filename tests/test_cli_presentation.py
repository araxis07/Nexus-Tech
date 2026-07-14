from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from _pytest.monkeypatch import MonkeyPatch
from rich.console import Console
from typer.main import get_command
from typer.testing import CliRunner

import nexus_tech.cli as cli_module
from nexus_tech import __version__
from nexus_tech.cli import app
from nexus_tech.content.models import ScenarioDefinition, ScenarioProductSeed
from nexus_tech.domain.models import (
    BudgetStance,
    CampaignGoalId,
    Company,
    CompanyStrategy,
    Competitor,
    ContractBillingModel,
    ContractCadence,
    CustomerAccount,
    CustomerAccountStatus,
    DifficultyMode,
    Employee,
    EmployeeRole,
    EventCategory,
    EventOption,
    ExitOutcome,
    FunctionalBudget,
    FunctionalBudgetPreset,
    GameState,
    LifecycleStage,
    MarketCycle,
    MarketSegment,
    PendingEvent,
    PricingTier,
    Product,
    QuarterPlan,
    RoadmapFocus,
    Seniority,
    TurnLedgerEntry,
)
from nexus_tech.persistence.save_coordinator import RunArchiveSummary, SaveSlotSummary
from nexus_tech.presentation.dashboard import (
    render_competitor_archetype_catalog,
    render_content_health,
    render_dashboard,
    render_game_over,
    render_glossary,
    render_product_template_catalog,
    render_quick_guide,
    render_report,
    render_turn_resolution,
    render_tutorial,
    render_victory,
)
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.balance_lab import (
    BalanceAuditFinding,
    BalanceAuditResult,
    BalanceBatchResult,
    BalanceComparisonResult,
    BalanceMatrixCell,
    BalanceMatrixResult,
    BalanceRunResult,
    BalanceScenarioComparison,
)
from nexus_tech.simulation.campaign_readiness import (
    CampaignReadinessCell,
    CampaignReadinessMatrix,
    CampaignRouteOutcome,
)
from nexus_tech.simulation.catalog_validation import CatalogValidationReport
from nexus_tech.simulation.end_turn_preview import EndTurnPreviewSummary
from nexus_tech.simulation.engine import create_new_game, resolve_turn
from nexus_tech.simulation.onboarding_flow import (
    OnboardingFlowAuditCheck,
    OnboardingFlowAuditReport,
)
from nexus_tech.simulation.randomness import RandomSource

runner = CliRunner()


def make_demo_state(*, include_pending_event: bool = False) -> GameState:
    primary_product = Product(
        name="Nexus One",
        lifecycle_stage=LifecycleStage.GROWTH,
        quality=66,
        bug_level=14,
        market_fit=58,
        technical_debt=20,
        user_count=48,
        revenue_per_user=Decimal("31.00"),
        feature_count=2,
        maintenance_cost=Decimal("320.00"),
        acquisition_rate=Decimal("0.0650"),
        churn_rate=Decimal("0.0460"),
        target_segment=MarketSegment.STARTUP,
    )
    secondary_product = Product(
        name="Nexus Flow",
        lifecycle_stage=LifecycleStage.PROTOTYPE,
        quality=49,
        bug_level=24,
        market_fit=41,
        technical_debt=28,
        user_count=11,
        revenue_per_user=Decimal("18.00"),
        feature_count=1,
        maintenance_cost=Decimal("180.00"),
        acquisition_rate=Decimal("0.0410"),
        churn_rate=Decimal("0.0530"),
        target_segment=MarketSegment.SMB,
    )
    employee = Employee(
        full_name="Ada Wong",
        role=EmployeeRole.ENGINEER,
        seniority=Seniority.MID,
        salary=Decimal("780.00"),
        energy=77,
        morale=73,
        productivity=69,
        specialization="platform",
        experience_points=18,
        promotion_readiness=44,
        attrition_risk=12,
        performance_rating=66,
        tenure_turns=4,
        underperformance_streak=0,
        assigned_product_id=primary_product.id,
    )
    pending_event = None
    if include_pending_event:
        pending_event = PendingEvent(
            event_id="competitor_pressure",
            category=EventCategory.MARKET_OPPORTUNITY,
            title="Competitor Pressure",
            description="A rival launched a comparable feature this morning.",
            triggered_turn=3,
            cooldown_turns=4,
            target_product_id=primary_product.id,
            options=[
                EventOption(
                    id="counter_launch",
                    label="Counter-launch",
                    description="Push a fast response with some delivery risk.",
                )
            ],
        )
    turn_history = [
        TurnLedgerEntry(
            turn=2,
            total_revenue=Decimal("1180.00"),
            total_operating_cost=Decimal("1690.00"),
            net_cash_flow=Decimal("-510.00"),
            cash_on_hand=Decimal("8120.00"),
            reputation=56,
            total_users=59,
            headcount=1,
            roadmap_focus=RoadmapFocus.GROWTH_PUSH,
        )
    ]
    competitor = Competitor(
        name="Atlas Rival",
        focus_segment=MarketSegment.STARTUP,
        strength=63,
        aggression=59,
        pricing_tier=PricingTier.STANDARD,
        active_product_count=2,
        funding_level=1,
    )
    customer_account = CustomerAccount(
        name="Startup Anchor: Nexus One",
        product_id=primary_product.id,
        segment=MarketSegment.STARTUP,
        contract_value=Decimal("620.00"),
        contract_cadence=ContractCadence.MONTHLY,
        billing_model=ContractBillingModel.USAGE_BASED,
        seat_count=0,
        usage_units=34,
        discount_rate=Decimal("0.0200"),
        satisfaction=71,
        onboarding_health=75,
        support_load=21,
        open_tickets=6,
        sla_breach_risk=12,
        expansion_potential=59,
        renewal_turn=5,
        churn_risk=14,
        status=CustomerAccountStatus.ACTIVE,
    )
    quarter_plan = QuarterPlan(
        budget_stance=BudgetStance.BALANCED,
        set_turn=2,
        target_turn=4,
        revenue_target=Decimal("1400.00"),
        user_target=75,
        cash_reserve_target=Decimal("9000.00"),
        headcount_cap=3,
    )
    return GameState(
        company=Company(
            name="NEXUS TECH",
            cash_on_hand=Decimal("8120.00"),
            reputation=56,
            current_turn=3,
        ),
        products=[primary_product, secondary_product],
        employees=[employee],
        competitors=[competitor],
        customer_accounts=[customer_account],
        quarter_plan=quarter_plan,
        functional_budget=FunctionalBudget(
            preset=FunctionalBudgetPreset.GROWTH_PUSH,
            engineering_share=24,
            marketing_share=40,
            customer_success_share=16,
            g_and_a_share=20,
        ),
        pending_event=pending_event,
        roadmap_focus=RoadmapFocus.GROWTH_PUSH,
        roadmap_set_turn=2,
        market_cycle=MarketCycle.EXPANDING,
        market_cycle_turns_remaining=2,
        turn_history=turn_history,
        action_points_remaining=BALANCE.actions_per_turn,
    )


def test_cli_help_lists_core_commands_and_debug_flag() -> None:
    command = get_command(app)
    option_names = {opt for parameter in command.params for opt in parameter.opts}
    command_names = set(command.commands.keys())

    assert {
        "new-game",
        "load-game",
        "continue-last-game",
        "list-templates",
        "list-goals",
        "list-rivals",
        "list-events",
        "list-candidates",
        "list-segments",
        "list-roadmaps",
        "list-balance-profiles",
        "simulate-balance",
        "compare-balance",
        "balance-matrix",
        "balance-audit",
        "export-balance-csv",
        "balance-report",
        "tutorial",
        "audit-onboarding-flow",
        "onboarding-visible-playtest-packet",
        "validate-onboarding-visible-playtest-packet",
        "onboarding-visible-playtest-report",
        "record-onboarding-visible-playtest-route",
        "validate-onboarding-visible-playtest-report",
        "onboarding-visible-playtest-status",
        "onboarding-visible-playtest-next",
        "validate-onboarding-visible-playtest-next",
        "onboarding-visible-playtest-batch-packet",
        "validate-onboarding-visible-playtest-batch-packet",
        "onboarding-visible-playtest-batch-preflight",
        "onboarding-visible-terminal-batch",
        "validate-onboarding-visible-terminal-batch",
        "onboarding-visible-terminal-evidence-sheet",
        "validate-onboarding-visible-terminal-evidence-sheet",
        "onboarding-visible-window-evidence-sheet",
        "validate-onboarding-visible-window-evidence-sheet",
        "onboarding-visible-evidence-matrix",
        "validate-onboarding-visible-evidence-matrix",
        "onboarding-visible-manual-session",
        "validate-onboarding-visible-manual-session",
        "onboarding-visible-ux-issue-intake",
        "validate-onboarding-visible-ux-issue-intake",
        "record-onboarding-visible-ux-issue",
        "onboarding-visible-ux-fix-plan",
        "validate-onboarding-visible-ux-fix-plan",
        "onboarding-visible-ux-triage-sprint",
        "validate-onboarding-visible-ux-triage-sprint",
        "onboarding-visible-ux-triage-next",
        "validate-onboarding-visible-ux-triage-next",
        "onboarding-visible-ux-recording-queue",
        "validate-onboarding-visible-ux-recording-queue",
        "onboarding-visible-ux-progress",
        "validate-onboarding-visible-ux-progress",
        "onboarding-visible-ux-batch-packet",
        "validate-onboarding-visible-ux-batch-packet",
        "onboarding-visible-ux-batch-closeout",
        "validate-onboarding-visible-ux-batch-closeout",
        "onboarding-visible-window-preflight",
        "validate-content",
        "list-saves",
        "check-saves",
        "doctor",
        "rename-save",
        "delete-save",
        "guide",
        "glossary",
    }.issubset(command_names)
    assert "--debug" in option_names
    assert "--version" in option_names


def test_root_command_dispatches_to_start_new_game(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_start_new_game(
        company_name: str | None,
        product_name: str | None,
        scenario_id: str,
        campaign_start_id: str,
        difficulty_mode: DifficultyMode | None,
        campaign_goal_id: CampaignGoalId | None,
        seed: int | None,
        db_path: Path,
        slot_name: str,
    ) -> None:
        captured.update(
            company_name=company_name,
            product_name=product_name,
            scenario_id=scenario_id,
            campaign_start_id=campaign_start_id,
            difficulty_mode=difficulty_mode,
            campaign_goal_id=campaign_goal_id,
            seed=seed,
            db_path=db_path,
            slot_name=slot_name,
        )

    monkeypatch.setattr(cli_module, "start_new_game", fake_start_new_game)

    db_path = tmp_path / "demo.db"
    result = runner.invoke(
        app,
        [
            "--company-name",
            "Demo Corp",
            "--product-name",
            "Alpha",
            "--scenario",
            "vc_sprint",
            "--campaign-start",
            "channel_rebuild_marathon",
            "--difficulty",
            "founder",
            "--goal",
            "portfolio_empire",
            "--seed",
            "13",
            "--db-path",
            str(db_path),
            "--slot",
            "showcase",
        ],
    )

    assert result.exit_code == 0
    assert captured == {
        "company_name": "Demo Corp",
        "product_name": "Alpha",
        "scenario_id": "vc_sprint",
        "campaign_start_id": "channel_rebuild_marathon",
        "difficulty_mode": DifficultyMode.FOUNDER,
        "campaign_goal_id": CampaignGoalId.PORTFOLIO_EMPIRE,
        "seed": 13,
        "db_path": db_path,
        "slot_name": "showcase",
    }


def test_new_game_command_dispatches_to_start_new_game(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_start_new_game(
        company_name: str | None,
        product_name: str | None,
        scenario_id: str,
        campaign_start_id: str,
        difficulty_mode: DifficultyMode | None,
        campaign_goal_id: CampaignGoalId | None,
        seed: int | None,
        db_path: Path,
        slot_name: str,
    ) -> None:
        captured.update(
            company_name=company_name,
            product_name=product_name,
            scenario_id=scenario_id,
            campaign_start_id=campaign_start_id,
            difficulty_mode=difficulty_mode,
            campaign_goal_id=campaign_goal_id,
            seed=seed,
            db_path=db_path,
            slot_name=slot_name,
        )

    monkeypatch.setattr(cli_module, "start_new_game", fake_start_new_game)

    db_path = tmp_path / "new-game.db"
    result = runner.invoke(
        app,
        [
            "new-game",
            "--company-name",
            "Demo Corp",
            "--product-name",
            "Beta",
            "--scenario",
            "bootstrap_studio",
            "--campaign-start",
            "board_recovery_crucible",
            "--seed",
            "21",
            "--db-path",
            str(db_path),
            "--slot",
            "slot-b",
        ],
    )

    assert result.exit_code == 0
    assert captured["product_name"] == "Beta"
    assert captured["scenario_id"] == "bootstrap_studio"
    assert captured["campaign_start_id"] == "board_recovery_crucible"
    assert captured["difficulty_mode"] is None
    assert captured["campaign_goal_id"] is None
    assert captured["seed"] == 21
    assert captured["db_path"] == db_path
    assert captured["slot_name"] == "slot-b"


def test_list_scenarios_command_renders_catalog(monkeypatch: MonkeyPatch) -> None:
    scenarios = (
        ScenarioDefinition(
            scenario_id="bootstrap_studio",
            title="Bootstrap Studio",
            description="A lean company with a modest runway.",
            company_name="Bootstrap Studio",
            company_strategy=CompanyStrategy.EFFICIENCY,
            cash_on_hand=Decimal("6400.00"),
            reputation=47,
            products=[
                ScenarioProductSeed(
                    key="core",
                    template_id="saas_tool",
                    name="Studio Suite",
                )
            ],
        ),
    )

    monkeypatch.setattr(cli_module, "get_available_scenarios", lambda: scenarios)

    result = runner.invoke(app, ["list-scenarios"])

    assert result.exit_code == 0
    assert "Scenario Catalog" in result.output
    assert "bootstrap_studio" in result.output
    assert "Bootstrap Studio" in result.output


def test_list_scenarios_command_marks_progression_locked_entries(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    scenarios = tuple(
        scenario
        for scenario in cli_module.get_available_scenarios()
        if scenario.scenario_id in {"bootstrap_studio", "campaign_ladder_climb"}
    )
    monkeypatch.setattr(cli_module, "get_available_scenarios", lambda: scenarios)
    db_path = tmp_path / "progression.db"
    console = Console(record=True, width=160)
    monkeypatch.setattr(cli_module, "console", console)

    cli_module.list_scenarios_command(db_path=db_path)
    output = console.export_text()

    assert "Campaign Ladder Climb" in output
    assert "Bootstrap Studio" in output
    assert "locked" in output


def test_list_campaign_starts_command_renders_catalog(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    console = Console(record=True, width=180)
    monkeypatch.setattr(cli_module, "console", console)

    cli_module.list_campaign_starts_command(db_path=tmp_path / "runs.db")
    output = console.export_text()

    assert "Campaign Start Catalog" in output
    assert "standard" in output
    assert "Board Recovery Start" in output
    assert "IPO Readiness Launchpad" in output


def test_list_templates_command_renders_catalog(monkeypatch: MonkeyPatch) -> None:
    templates = cli_module.get_available_product_templates()
    monkeypatch.setattr(cli_module, "get_available_product_templates", lambda: templates[:1])

    result = runner.invoke(app, ["list-templates"])

    assert result.exit_code == 0
    assert "Product Template Catalog" in result.output
    assert templates[0].template_id in result.output
    assert templates[0].title in result.output


def test_list_goals_command_renders_catalog() -> None:
    result = runner.invoke(app, ["list-goals"])

    assert result.exit_code == 0
    assert "Campaign Goals" in result.output
    assert "profit_machine" in result.output
    assert "portfolio_empire" in result.output


def test_list_rivals_command_renders_catalog() -> None:
    result = runner.invoke(app, ["list-rivals"])

    assert result.exit_code == 0
    assert "Competitor Archetypes" in result.output
    assert "price_raider" in result.output


def test_new_game_rejects_locked_progression_scenario(tmp_path: Path) -> None:
    db_path = tmp_path / "progression.db"
    result = runner.invoke(
        app,
        [
            "new-game",
            "--scenario",
            "campaign_ladder_climb",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 1
    assert "Scenario Locked" in result.output
    assert "list-unlocks" in result.output


def test_new_game_rejects_locked_campaign_start(tmp_path: Path) -> None:
    db_path = tmp_path / "progression.db"
    result = runner.invoke(
        app,
        [
            "new-game",
            "--scenario",
            "bootstrap_studio",
            "--campaign-start",
            "board_recovery_crucible",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 1
    assert "Campaign Start Locked" in result.output
    assert "list-unlocks" in result.output


def test_list_events_command_renders_registry() -> None:
    result = runner.invoke(app, ["list-events"])

    assert result.exit_code == 0
    assert "Event Catalog" in result.output
    assert "loan_covenant" in result.output


def test_list_candidates_command_renders_seeded_candidate_pool() -> None:
    result = runner.invoke(app, ["list-candidates", "--seed", "12", "--count", "2"])

    assert result.exit_code == 0
    assert "Hiring Candidate Pool" in result.output
    assert "Trait" in result.output


def test_list_segments_command_renders_customer_segment_profiles() -> None:
    result = runner.invoke(app, ["list-segments"])

    assert result.exit_code == 0
    assert "Customer Segment Profiles" in result.output
    assert "enterprise" in result.output


def test_list_roadmaps_command_renders_initiatives() -> None:
    result = runner.invoke(app, ["list-roadmaps"])

    assert result.exit_code == 0
    assert "Roadmap Initiatives" in result.output
    assert "ai_trust_program" in result.output


def test_list_balance_profiles_command_renders_presets() -> None:
    result = runner.invoke(app, ["list-balance-profiles"])

    assert result.exit_code == 0
    assert "Balance Profiles" in result.output
    assert "long_run" in result.output


def test_simulate_balance_command_renders_batch_summary(monkeypatch: MonkeyPatch) -> None:
    batch = BalanceBatchResult(
        scenario_id="founder_journey",
        difficulty_mode=DifficultyMode.STANDARD,
        campaign_goal_id=CampaignGoalId.PROFIT_MACHINE,
        runs=2,
        turns=6,
        seed_base=50,
        results=(
            BalanceRunResult(
                seed=50,
                turns_played=5,
                game_over=False,
                victory_achieved=False,
                final_cash=Decimal("9100.00"),
                total_users=88,
                active_products=2,
                run_score=144,
            ),
            BalanceRunResult(
                seed=51,
                turns_played=6,
                game_over=True,
                victory_achieved=False,
                final_cash=Decimal("-120.00"),
                total_users=54,
                active_products=1,
                run_score=82,
            ),
        ),
    )
    monkeypatch.setattr(cli_module, "run_balance_batch", lambda **_: batch)

    result = runner.invoke(app, ["simulate-balance", "--runs", "2", "--turns", "6"])

    assert result.exit_code == 0
    assert "Balance Lab" in result.output
    assert "Run Results" in result.output
    assert "founder_journey" in result.output


def test_compare_balance_command_renders_scenario_ranking(monkeypatch: MonkeyPatch) -> None:
    comparison = BalanceComparisonResult(
        difficulty_mode=DifficultyMode.STANDARD,
        campaign_goal_id=CampaignGoalId.PROFIT_MACHINE,
        runs=2,
        turns=6,
        seed_base=50,
        comparisons=(
            BalanceScenarioComparison(
                scenario_id="founder",
                average_score=142.0,
                average_cash=Decimal("9200.00"),
                average_users=88.0,
                victories=0,
                shutdowns=0,
            ),
            BalanceScenarioComparison(
                scenario_id="rebuild",
                average_score=101.0,
                average_cash=Decimal("6100.00"),
                average_users=64.0,
                victories=0,
                shutdowns=1,
            ),
        ),
    )
    monkeypatch.setattr(cli_module, "run_balance_comparison", lambda **_: comparison)

    result = runner.invoke(
        app,
        [
            "compare-balance",
            "--scenario",
            "founder_journey",
            "--scenario",
            "technical_rebuild",
            "--runs",
            "2",
            "--turns",
            "6",
        ],
    )

    assert result.exit_code == 0
    assert "Balance Compare" in result.output
    assert "Scenario Ranking" in result.output
    assert "rebuild" in result.output


def test_balance_matrix_command_renders_grid(monkeypatch: MonkeyPatch) -> None:
    matrix = BalanceMatrixResult(
        campaign_goal_id=CampaignGoalId.PROFIT_MACHINE,
        runs=1,
        turns=6,
        seed_base=50,
        cells=(
            BalanceMatrixCell(
                scenario_id="founder",
                difficulty_mode=DifficultyMode.BUILDER,
                average_score=130.0,
                average_cash=Decimal("9000.00"),
                average_users=90.0,
                victories=0,
                shutdowns=0,
            ),
            BalanceMatrixCell(
                scenario_id="founder",
                difficulty_mode=DifficultyMode.FOUNDER,
                average_score=98.0,
                average_cash=Decimal("6100.00"),
                average_users=64.0,
                victories=0,
                shutdowns=1,
            ),
        ),
    )
    monkeypatch.setattr(cli_module, "run_balance_matrix", lambda **_: matrix)

    result = runner.invoke(app, ["balance-matrix", "--scenario", "founder_journey"])

    assert result.exit_code == 0
    assert "Balance Matrix" in result.output
    assert "Scenario x Difficulty" in result.output
    assert "Status" in result.output
    assert "Status Mix" in result.output


def test_balance_audit_command_renders_findings(monkeypatch: MonkeyPatch) -> None:
    audit = BalanceAuditResult(
        campaign_goal_id=CampaignGoalId.PROFIT_MACHINE,
        runs=1,
        turns=4,
        seed_base=70,
        findings=(
            BalanceAuditFinding(
                severity="low",
                scenario_id="founder_journey",
                difficulty_mode=DifficultyMode.STANDARD,
                summary="Average closing cash is thin.",
                average_score=101.0,
                average_cash=Decimal("1800.00"),
                shutdowns=0,
                victories=0,
            ),
        ),
    )
    monkeypatch.setattr(cli_module, "run_balance_audit", lambda **_: audit)

    result = runner.invoke(app, ["balance-audit", "--scenario", "founder_journey"])

    assert result.exit_code == 0
    assert "Balance Audit" in result.output
    assert "Tuning Findings" in result.output
    assert "low" in result.output


def test_campaign_readiness_command_renders_and_exports_automated_boundary(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    routes = tuple(
        CampaignRouteOutcome(
            route_id=f"route-{index}",
            route_label=f"Commitment {index} -> Consequence {index}",
            runs=1,
            full_path_runs=1,
            act_three_survivors=1,
            shutdowns=0,
            victories=0,
            average_turns=12.0,
            average_score=180.0 + index,
            average_cash=Decimal("12000.00"),
        )
        for index in range(4)
    )
    matrix = CampaignReadinessMatrix(
        campaign_goal_id=CampaignGoalId.PROFIT_MACHINE,
        runs_per_route=1,
        turns=12,
        seed_base=28500,
        cells=(
            CampaignReadinessCell(
                scenario_id="founder_journey",
                difficulty_mode=DifficultyMode.STANDARD,
                routes=routes,
            ),
        ),
    )
    monkeypatch.setattr(cli_module, "run_campaign_readiness_matrix", lambda **_: matrix)
    output = tmp_path / "campaign-readiness.md"

    result = runner.invoke(
        app,
        [
            "campaign-readiness",
            "--scenario",
            "founder_journey",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    assert "Campaign Readiness" in result.output
    assert "Automated route coverage only" in result.output
    assert "Human Signoff" in result.output
    assert output.exists()
    assert "Human playtest signoff: `required`" in output.read_text(encoding="utf-8")


def test_export_balance_csv_command_writes_matrix_file(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    matrix = BalanceMatrixResult(
        campaign_goal_id=CampaignGoalId.PROFIT_MACHINE,
        runs=1,
        turns=6,
        seed_base=50,
        cells=(
            BalanceMatrixCell(
                scenario_id="founder",
                difficulty_mode=DifficultyMode.STANDARD,
                average_score=130.0,
                average_cash=Decimal("9000.00"),
                average_users=90.0,
                victories=0,
                shutdowns=0,
            ),
        ),
    )
    monkeypatch.setattr(cli_module, "run_balance_matrix", lambda **_: matrix)
    output_path = tmp_path / "balance.csv"

    result = runner.invoke(app, ["export-balance-csv", "--output", str(output_path)])

    assert result.exit_code == 0
    assert "Balance Export" in result.output
    assert output_path.read_text(encoding="utf-8").startswith(
        "scenario_id,difficulty,average_score"
    )


def test_balance_report_command_writes_markdown_file(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    matrix = BalanceMatrixResult(
        campaign_goal_id=CampaignGoalId.PROFIT_MACHINE,
        runs=1,
        turns=6,
        seed_base=50,
        cells=(
            BalanceMatrixCell(
                scenario_id="founder",
                difficulty_mode=DifficultyMode.STANDARD,
                average_score=130.0,
                average_cash=Decimal("9000.00"),
                average_users=90.0,
                victories=0,
                shutdowns=0,
            ),
        ),
    )
    audit = BalanceAuditResult(
        campaign_goal_id=CampaignGoalId.PROFIT_MACHINE,
        runs=1,
        turns=6,
        seed_base=50,
        findings=(),
    )
    monkeypatch.setattr(cli_module, "run_balance_matrix", lambda **_: matrix)
    monkeypatch.setattr(cli_module, "run_balance_audit", lambda **_: audit)
    output_path = tmp_path / "balance.md"

    result = runner.invoke(app, ["balance-report", "--output", str(output_path)])

    assert result.exit_code == 0
    assert "Balance Report" in result.output
    assert output_path.read_text(encoding="utf-8").startswith("# NEXUS TECH Balance Report")
    assert "Tuning Priorities" in output_path.read_text(encoding="utf-8")
    assert "Threshold Gates" in output_path.read_text(encoding="utf-8")


def test_version_option_prints_installed_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert f"NEXUS TECH {__version__}" in result.output


def test_guide_command_renders_quick_start() -> None:
    result = runner.invoke(app, ["guide"])

    assert result.exit_code == 0
    assert "Quick Guide" in result.output
    assert "Difficulty cues" in result.output
    assert "or headcount." in result.output
    assert "Founder punishes weak runway" in result.output
    assert "first clean growth signal." in result.output


def test_tutorial_command_renders_first_run_path() -> None:
    result = runner.invoke(app, ["tutorial"])

    assert result.exit_code == 0
    assert "First Run Tutorial" in result.output
    assert "new-game" in result.output
    assert "Risk Forecast" in result.output
    assert "Difficulty Profile" in result.output


def test_audit_onboarding_flow_command_writes_report(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    report = OnboardingFlowAuditReport(
        scenario_id="founder_journey",
        difficulty="builder",
        campaign_start_id="standard",
        checks=(
            OnboardingFlowAuditCheck(
                area="Guided Opening",
                status="pass",
                summary="Opening has a valid current command.",
                evidence=("current:hire_employee", "steps:6"),
            ),
        ),
    )
    calls: dict[str, object] = {}

    def fake_run_onboarding_flow_audit(**kwargs):
        calls.update(kwargs)
        return report

    monkeypatch.setattr(
        cli_module,
        "run_onboarding_flow_audit",
        fake_run_onboarding_flow_audit,
    )
    output_path = tmp_path / "onboarding.md"

    result = runner.invoke(
        app,
        [
            "audit-onboarding-flow",
            "--scenario",
            "founder_journey",
            "--difficulty",
            "builder",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert "Onboarding Flow Audit" in result.output
    assert "Onboarding flow status: PASS" in result.output
    assert calls["scenario_id"] == "founder_journey"
    assert calls["difficulty_mode"] is DifficultyMode.BUILDER
    assert output_path.exists()
    assert "NEXUS TECH Onboarding Flow Audit" in output_path.read_text(encoding="utf-8")


def test_onboarding_visible_playtest_packet_command_writes_packet(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "onboarding-visible.md"

    result = runner.invoke(
        app,
        [
            "onboarding-visible-playtest-packet",
            "--window-size",
            "820x620",
            "--motion-mode",
            "reduced",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert "Onboarding Visible Playtest Packet" in result.output
    text = output_path.read_text(encoding="utf-8")
    assert "menu-2d --window-size 820x620 --motion-mode reduced" in text
    assert "play-2d --scenario founder_journey" in text
    assert "--difficulty builder" in text
    assert "- Status: `manual-required`" in text
    assert "- Manual result: `not completed by automation`" in text


def test_validate_onboarding_visible_playtest_packet_command_passes_current_packet(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "onboarding-visible.md"
    packet_result = runner.invoke(
        app,
        [
            "onboarding-visible-playtest-packet",
            "--window-size",
            "820x620",
            "--motion-mode",
            "reduced",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--output",
            str(output_path),
        ],
    )
    assert packet_result.exit_code == 0

    result = runner.invoke(
        app,
        [
            "validate-onboarding-visible-playtest-packet",
            "--window-size",
            "820x620",
            "--motion-mode",
            "reduced",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--input",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert "Onboarding Visible Packet Validation" in result.output
    assert "PASS" in result.output


def test_onboarding_visible_playtest_report_commands_record_evidence(
    tmp_path: Path,
) -> None:
    packet_path = tmp_path / "onboarding-visible.md"
    report_path = tmp_path / "onboarding-visible-report.md"
    next_path = tmp_path / "onboarding-visible-next.md"
    playtest_batch_path = tmp_path / "onboarding-visible-batch-packet.md"
    batch_path = tmp_path / "onboarding-visible-terminal-batch.md"
    sheet_path = tmp_path / "onboarding-visible-terminal-evidence-sheet.md"
    window_sheet_path = tmp_path / "onboarding-visible-820x620-evidence-sheet.md"
    matrix_path = tmp_path / "onboarding-visible-evidence-matrix.md"
    session_path = tmp_path / "onboarding-visible-manual-session.md"
    intake_path = tmp_path / "onboarding-visible-ux-issue-intake.md"
    fix_plan_path = tmp_path / "onboarding-visible-ux-fix-plan.md"
    sprint_path = tmp_path / "onboarding-visible-ux-triage-sprint.md"
    triage_next_path = tmp_path / "onboarding-visible-ux-triage-next.md"
    recording_queue_path = tmp_path / "onboarding-visible-ux-recording-queue.md"
    progress_path = tmp_path / "onboarding-visible-ux-progress.md"
    ux_batch_path = tmp_path / "onboarding-visible-ux-batch-packet.md"
    ux_batch_closeout_path = tmp_path / "onboarding-visible-ux-batch-closeout.md"
    packet_result = runner.invoke(
        app,
        [
            "onboarding-visible-playtest-packet",
            "--window-size",
            "820x620",
            "--motion-mode",
            "reduced",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--output",
            str(packet_path),
        ],
    )
    assert packet_result.exit_code == 0

    report_result = runner.invoke(
        app,
        [
            "onboarding-visible-playtest-report",
            "--window-size",
            "820x620",
            "--motion-mode",
            "reduced",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--input",
            str(packet_path),
            "--output",
            str(report_path),
        ],
    )
    assert report_result.exit_code == 0
    assert "MANUAL-REQUIRED" in report_result.output

    record_result = runner.invoke(
        app,
        [
            "record-onboarding-visible-playtest-route",
            "--report",
            str(report_path),
            "--rank",
            "4",
            "--result",
            "pass",
            "--notes",
            (
                "Observed the 820x620 title menu in a real window; wizard, help, "
                "and back/menu affordances were readable and separated."
            ),
        ],
    )
    assert record_result.exit_code == 0
    assert "Onboarding Visible Evidence Recorded" in record_result.output

    validation_result = runner.invoke(
        app,
        [
            "validate-onboarding-visible-playtest-report",
            "--window-size",
            "820x620",
            "--motion-mode",
            "reduced",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
        ],
    )
    assert validation_result.exit_code == 0
    assert "Onboarding Visible Report Validation" in validation_result.output
    assert "MANUAL-REQUIRED" in validation_result.output
    assert "Observed the 820x620 title menu" in report_path.read_text(encoding="utf-8")

    status_result = runner.invoke(
        app,
        [
            "onboarding-visible-playtest-status",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
        ],
    )
    assert status_result.exit_code == 0
    assert "Onboarding Visible QA Status" in status_result.output
    assert "Next Visible Command" in status_result.output
    assert "Next Recorder Command" in status_result.output
    assert "record-onboarding-visible-playtest-route" in status_result.output

    next_result = runner.invoke(
        app,
        [
            "onboarding-visible-playtest-next",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--output",
            str(next_path),
        ],
    )
    assert next_result.exit_code == 0
    assert "Onboarding Visible Next Step" in next_result.output
    assert "Next-step handoff written" in next_result.output
    next_text = next_path.read_text(encoding="utf-8")
    assert "# NEXUS TECH Onboarding Visible Next Step" in next_text
    assert ".venv313/bin/nexus-tech guide" in next_text
    assert "record-onboarding-visible-playtest-route --report" in next_text

    next_validation_result = runner.invoke(
        app,
        [
            "validate-onboarding-visible-playtest-next",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--input",
            str(next_path),
        ],
    )
    assert next_validation_result.exit_code == 0
    assert "Onboarding Visible Next-Step Validation" in next_validation_result.output
    assert "PASS" in next_validation_result.output

    playtest_batch_result = runner.invoke(
        app,
        [
            "onboarding-visible-playtest-batch-packet",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--batch-size",
            "2",
            "--output",
            str(playtest_batch_path),
        ],
    )
    assert playtest_batch_result.exit_code == 0
    assert "Onboarding Visible Batch Packet" in playtest_batch_result.output
    assert "Focused batch packet written" in playtest_batch_result.output
    playtest_batch_text = playtest_batch_path.read_text(encoding="utf-8")
    assert "# NEXUS TECH Onboarding Visible Playtest Batch Packet" in playtest_batch_text
    assert ".venv313/bin/nexus-tech guide" in playtest_batch_text
    assert ".venv313/bin/nexus-tech tutorial" in playtest_batch_text
    assert "This packet scopes manual work" in playtest_batch_text

    playtest_batch_validation_result = runner.invoke(
        app,
        [
            "validate-onboarding-visible-playtest-batch-packet",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--batch-size",
            "2",
            "--input",
            str(playtest_batch_path),
        ],
    )
    assert playtest_batch_validation_result.exit_code == 0
    assert "Onboarding Visible Batch Packet Validation" in (playtest_batch_validation_result.output)
    assert "PASS" in playtest_batch_validation_result.output

    batch_result = runner.invoke(
        app,
        [
            "onboarding-visible-terminal-batch",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--output",
            str(batch_path),
        ],
    )
    assert batch_result.exit_code == 0
    assert "Onboarding Visible Terminal Batch" in batch_result.output
    assert "Terminal batch handoff written" in batch_result.output
    batch_text = batch_path.read_text(encoding="utf-8")
    assert "# NEXUS TECH Onboarding Visible Terminal Batch" in batch_text
    assert ".venv313/bin/nexus-tech guide" in batch_text
    assert ".venv313/bin/nexus-tech tutorial" in batch_text

    batch_validation_result = runner.invoke(
        app,
        [
            "validate-onboarding-visible-terminal-batch",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--input",
            str(batch_path),
        ],
    )
    assert batch_validation_result.exit_code == 0
    assert "Onboarding Visible Terminal Batch Validation" in batch_validation_result.output
    assert "PASS" in batch_validation_result.output

    sheet_result = runner.invoke(
        app,
        [
            "onboarding-visible-terminal-evidence-sheet",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--output",
            str(sheet_path),
        ],
    )
    assert sheet_result.exit_code == 0
    assert "Onboarding Visible Terminal Evidence Sheet" in sheet_result.output
    assert "Terminal evidence worksheet written" in sheet_result.output
    sheet_text = sheet_path.read_text(encoding="utf-8")
    assert "# NEXUS TECH Onboarding Visible Terminal Evidence Sheet" in sheet_text
    assert ".venv313/bin/nexus-tech guide" in sheet_text
    assert "Record only after replacing the placeholder" in sheet_text

    sheet_validation_result = runner.invoke(
        app,
        [
            "validate-onboarding-visible-terminal-evidence-sheet",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--input",
            str(sheet_path),
        ],
    )
    assert sheet_validation_result.exit_code == 0
    assert "Onboarding Visible Terminal Evidence Sheet Validation" in sheet_validation_result.output
    assert "PASS" in sheet_validation_result.output

    window_sheet_result = runner.invoke(
        app,
        [
            "onboarding-visible-window-evidence-sheet",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--window",
            "820x620",
            "--output",
            str(window_sheet_path),
        ],
    )
    assert window_sheet_result.exit_code == 0
    assert "Onboarding Visible Window Evidence Sheet" in window_sheet_result.output
    assert "Window evidence worksheet written" in window_sheet_result.output
    window_sheet_text = window_sheet_path.read_text(encoding="utf-8")
    assert "# NEXUS TECH Onboarding Visible Window Evidence Sheet" in window_sheet_text
    assert ".venv313/bin/nexus-tech menu-2d --window-size 820x620" in window_sheet_text
    assert "Text stays inside panels and remains readable at 820x620." in window_sheet_text

    window_sheet_validation_result = runner.invoke(
        app,
        [
            "validate-onboarding-visible-window-evidence-sheet",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--window",
            "820x620",
            "--input",
            str(window_sheet_path),
        ],
    )
    assert window_sheet_validation_result.exit_code == 0
    assert "Onboarding Visible Window Evidence Sheet Validation" in (
        window_sheet_validation_result.output
    )
    assert "PASS" in window_sheet_validation_result.output

    matrix_result = runner.invoke(
        app,
        [
            "onboarding-visible-evidence-matrix",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--output",
            str(matrix_path),
        ],
    )
    assert matrix_result.exit_code == 0
    assert "Onboarding Visible Evidence Matrix" in matrix_result.output
    assert "Evidence matrix written" in matrix_result.output
    matrix_text = matrix_path.read_text(encoding="utf-8")
    assert "# NEXUS TECH Onboarding Visible Evidence Matrix" in matrix_text
    assert "| `terminal` |" in matrix_text
    assert "| `820x620` |" in matrix_text
    assert "record-onboarding-visible-playtest-route --report" in matrix_text

    matrix_validation_result = runner.invoke(
        app,
        [
            "validate-onboarding-visible-evidence-matrix",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--input",
            str(matrix_path),
        ],
    )
    assert matrix_validation_result.exit_code == 0
    assert "Onboarding Visible Evidence Matrix Validation" in (matrix_validation_result.output)
    assert "PASS" in matrix_validation_result.output

    session_result = runner.invoke(
        app,
        [
            "onboarding-visible-manual-session",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--output",
            str(session_path),
        ],
    )
    assert session_result.exit_code == 0
    assert "Onboarding Visible Manual Session" in session_result.output
    assert "Manual session packet written" in session_result.output
    session_text = session_path.read_text(encoding="utf-8")
    assert "# NEXUS TECH Onboarding Visible Manual Session" in session_text
    assert "onboarding-visible-window-preflight --frames 1" in session_text
    assert "record-onboarding-visible-playtest-route --report" in session_text
    assert "This session packet is a checklist, not evidence." in session_text

    session_validation_result = runner.invoke(
        app,
        [
            "validate-onboarding-visible-manual-session",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--input",
            str(session_path),
        ],
    )
    assert session_validation_result.exit_code == 0
    assert "Onboarding Visible Manual Session Validation" in (session_validation_result.output)
    assert "PASS" in session_validation_result.output

    intake_result = runner.invoke(
        app,
        [
            "onboarding-visible-ux-issue-intake",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--output",
            str(intake_path),
        ],
    )
    assert intake_result.exit_code == 0
    assert "Onboarding Visible UX Issue Intake" in intake_result.output
    assert "UX issue intake written" in intake_result.output
    intake_text = intake_path.read_text(encoding="utf-8")
    assert "# NEXUS TECH Onboarding Visible UX Issue Intake" in intake_text
    assert "onboarding-visible-manual-session --report" in intake_text
    assert "onboarding-visible-window-preflight --frames 1" in intake_text
    assert "This intake is not evidence; it only captures observed UX issues." in intake_text

    intake_validation_result = runner.invoke(
        app,
        [
            "validate-onboarding-visible-ux-issue-intake",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--input",
            str(intake_path),
        ],
    )
    assert intake_validation_result.exit_code == 0
    assert "Onboarding Visible UX Issue Intake Validation" in (intake_validation_result.output)
    assert "PASS" in intake_validation_result.output

    ux_record_result = runner.invoke(
        app,
        [
            "record-onboarding-visible-ux-issue",
            "--input",
            str(intake_path),
            "--rank",
            "4",
            "--severity",
            "P1",
            "--issue-notes",
            (
                "Observed the compact title menu in a real window; menu recovery was "
                "readable but pause/back/menu spacing slowed first-time navigation."
            ),
            "--follow-up",
            "UX owner / 2026-07-10",
        ],
    )
    assert ux_record_result.exit_code == 0
    assert "Onboarding Visible UX Issue Recorded" in ux_record_result.output
    assert "UX issue intake updated" in ux_record_result.output
    assert "`P1`" in intake_path.read_text(encoding="utf-8")

    fix_plan_result = runner.invoke(
        app,
        [
            "onboarding-visible-ux-fix-plan",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--input",
            str(intake_path),
            "--output",
            str(fix_plan_path),
        ],
    )
    assert fix_plan_result.exit_code == 0
    assert "Onboarding Visible UX Fix Plan" in fix_plan_result.output
    assert "UX fix plan written" in fix_plan_result.output
    fix_plan_text = fix_plan_path.read_text(encoding="utf-8")
    assert "# NEXUS TECH Onboarding Visible UX Fix Plan" in fix_plan_text
    assert "validate-onboarding-visible-ux-issue-intake" in fix_plan_text
    assert "Observed the compact title menu" in fix_plan_text
    assert "no P0/P1 and no todo severities before UI signoff" in fix_plan_text
    assert "This fix plan is not manual evidence" in fix_plan_text

    fix_plan_validation_result = runner.invoke(
        app,
        [
            "validate-onboarding-visible-ux-fix-plan",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--input",
            str(fix_plan_path),
            "--intake",
            str(intake_path),
        ],
    )
    assert fix_plan_validation_result.exit_code == 0
    assert "Onboarding Visible UX Fix Plan Validation" in (fix_plan_validation_result.output)
    assert "PASS" in fix_plan_validation_result.output

    sprint_result = runner.invoke(
        app,
        [
            "onboarding-visible-ux-triage-sprint",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--intake",
            str(intake_path),
            "--plan",
            str(fix_plan_path),
            "--output",
            str(sprint_path),
        ],
    )
    assert sprint_result.exit_code == 0
    assert "Onboarding Visible UX Triage Sprint" in sprint_result.output
    assert "UX triage sprint written" in sprint_result.output
    sprint_text = sprint_path.read_text(encoding="utf-8")
    assert "# NEXUS TECH Onboarding Visible UX Triage Sprint" in sprint_text
    assert "triage todo rows and close P0/P1 before UI signoff" in sprint_text
    assert "validate-onboarding-visible-ux-fix-plan" in sprint_text
    assert "This sprint packet is not evidence" in sprint_text

    sprint_validation_result = runner.invoke(
        app,
        [
            "validate-onboarding-visible-ux-triage-sprint",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--input",
            str(sprint_path),
            "--intake",
            str(intake_path),
            "--plan",
            str(fix_plan_path),
        ],
    )
    assert sprint_validation_result.exit_code == 0
    assert "Onboarding Visible UX Triage Sprint Validation" in (sprint_validation_result.output)
    assert "PASS" in sprint_validation_result.output

    triage_next_result = runner.invoke(
        app,
        [
            "onboarding-visible-ux-triage-next",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--intake",
            str(intake_path),
            "--plan",
            str(fix_plan_path),
            "--sprint",
            str(sprint_path),
            "--output",
            str(triage_next_path),
        ],
    )
    assert triage_next_result.exit_code == 0
    assert "Onboarding Visible UX Triage Next Step" in triage_next_result.output
    assert "UX triage next-step handoff written" in triage_next_result.output
    triage_next_text = triage_next_path.read_text(encoding="utf-8")
    assert "# NEXUS TECH Onboarding Visible UX Triage Next Step" in triage_next_text
    assert "record-onboarding-visible-playtest-route" in triage_next_text
    assert "record-onboarding-visible-ux-issue" in triage_next_text
    assert "open the route and update intake/report from real observation" in triage_next_text
    assert "This next-step handoff is not evidence" in triage_next_text

    triage_next_validation_result = runner.invoke(
        app,
        [
            "validate-onboarding-visible-ux-triage-next",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--input",
            str(triage_next_path),
            "--intake",
            str(intake_path),
            "--plan",
            str(fix_plan_path),
            "--sprint",
            str(sprint_path),
        ],
    )
    assert triage_next_validation_result.exit_code == 0
    assert "Onboarding Visible UX Triage Next Validation" in (triage_next_validation_result.output)
    assert "PASS" in triage_next_validation_result.output

    recording_queue_result = runner.invoke(
        app,
        [
            "onboarding-visible-ux-recording-queue",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--intake",
            str(intake_path),
            "--plan",
            str(fix_plan_path),
            "--sprint",
            str(sprint_path),
            "--output",
            str(recording_queue_path),
        ],
    )
    assert recording_queue_result.exit_code == 0
    assert "Onboarding Visible UX Recording Queue" in recording_queue_result.output
    assert "UX recording queue written" in recording_queue_result.output
    recording_queue_text = recording_queue_path.read_text(encoding="utf-8")
    assert "# NEXUS TECH Onboarding Visible UX Recording Queue" in recording_queue_text
    assert "record-onboarding-visible-playtest-route" in recording_queue_text
    assert "record-onboarding-visible-ux-issue" in recording_queue_text
    assert "This recording queue is not evidence" in recording_queue_text

    recording_queue_validation_result = runner.invoke(
        app,
        [
            "validate-onboarding-visible-ux-recording-queue",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--input",
            str(recording_queue_path),
            "--intake",
            str(intake_path),
            "--plan",
            str(fix_plan_path),
            "--sprint",
            str(sprint_path),
        ],
    )
    assert recording_queue_validation_result.exit_code == 0
    assert "Onboarding Visible UX Recording Queue Validation" in (
        recording_queue_validation_result.output
    )
    assert "PASS" in recording_queue_validation_result.output

    progress_result = runner.invoke(
        app,
        [
            "onboarding-visible-ux-progress",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--intake",
            str(intake_path),
            "--plan",
            str(fix_plan_path),
            "--sprint",
            str(sprint_path),
            "--queue",
            str(recording_queue_path),
            "--output",
            str(progress_path),
        ],
    )
    assert progress_result.exit_code == 0
    assert "Onboarding Visible UX Progress" in progress_result.output
    assert "UX progress board written" in progress_result.output
    progress_text = progress_path.read_text(encoding="utf-8")
    assert "# NEXUS TECH Onboarding Visible UX Progress" in progress_text
    assert "Progress Lanes" in progress_text
    assert "record-onboarding-visible-ux-issue" in progress_text
    assert "This progress board is not evidence" in progress_text

    progress_validation_result = runner.invoke(
        app,
        [
            "validate-onboarding-visible-ux-progress",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--input",
            str(progress_path),
            "--queue",
            str(recording_queue_path),
            "--intake",
            str(intake_path),
            "--plan",
            str(fix_plan_path),
            "--sprint",
            str(sprint_path),
        ],
    )
    assert progress_validation_result.exit_code == 0
    assert "Onboarding Visible UX Progress Validation" in progress_validation_result.output
    assert "PASS" in progress_validation_result.output

    ux_batch_result = runner.invoke(
        app,
        [
            "onboarding-visible-ux-batch-packet",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--intake",
            str(intake_path),
            "--plan",
            str(fix_plan_path),
            "--sprint",
            str(sprint_path),
            "--queue",
            str(recording_queue_path),
            "--batch-size",
            "2",
            "--output",
            str(ux_batch_path),
        ],
    )
    assert ux_batch_result.exit_code == 0
    assert "Onboarding Visible UX Batch Packet" in ux_batch_result.output
    assert "UX batch packet written" in ux_batch_result.output
    ux_batch_text = ux_batch_path.read_text(encoding="utf-8")
    assert "# NEXUS TECH Onboarding Visible UX Batch Packet" in ux_batch_text
    assert "- Batch Size: `2`" in ux_batch_text
    assert "record-onboarding-visible-playtest-route" in ux_batch_text
    assert "record-onboarding-visible-ux-issue" in ux_batch_text
    assert "This batch packet is not evidence" in ux_batch_text

    ux_batch_validation_result = runner.invoke(
        app,
        [
            "validate-onboarding-visible-ux-batch-packet",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--report",
            str(report_path),
            "--input",
            str(ux_batch_path),
            "--queue",
            str(recording_queue_path),
            "--intake",
            str(intake_path),
            "--plan",
            str(fix_plan_path),
            "--sprint",
            str(sprint_path),
            "--batch-size",
            "2",
        ],
    )
    assert ux_batch_validation_result.exit_code == 0
    assert "Onboarding Visible UX Batch Packet Validation" in ux_batch_validation_result.output
    assert "PASS" in ux_batch_validation_result.output

    ux_batch_closeout_result = runner.invoke(
        app,
        [
            "onboarding-visible-ux-batch-closeout",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--batch",
            str(ux_batch_path),
            "--report",
            str(report_path),
            "--intake",
            str(intake_path),
            "--output",
            str(ux_batch_closeout_path),
        ],
    )
    assert ux_batch_closeout_result.exit_code == 0
    assert "Onboarding Visible UX Batch Closeout" in ux_batch_closeout_result.output
    assert "UX batch closeout written" in ux_batch_closeout_result.output
    ux_batch_closeout_text = ux_batch_closeout_path.read_text(encoding="utf-8")
    assert "# NEXUS TECH Onboarding Visible UX Batch Closeout" in ux_batch_closeout_text
    assert "Refresh Sequence" in ux_batch_closeout_text
    assert "This closeout board reads evidence; it does not create evidence." in (
        ux_batch_closeout_text
    )

    ux_batch_closeout_validation_result = runner.invoke(
        app,
        [
            "validate-onboarding-visible-ux-batch-closeout",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--batch",
            str(ux_batch_path),
            "--report",
            str(report_path),
            "--intake",
            str(intake_path),
            "--input",
            str(ux_batch_closeout_path),
        ],
    )
    assert ux_batch_closeout_validation_result.exit_code == 0
    assert "Onboarding Visible UX Batch Closeout Validation" in (
        ux_batch_closeout_validation_result.output
    )
    assert "PASS" in ux_batch_closeout_validation_result.output


def test_onboarding_visible_window_preflight_runs_focused_headless_routes(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "onboarding-visible-window-preflight.md"
    db_path = tmp_path / "onboarding-visible-window-preflight.db"

    result = runner.invoke(
        app,
        [
            "onboarding-visible-window-preflight",
            "--window-size",
            "820x620",
            "--motion-mode",
            "off",
            "--frames",
            "1",
            "--db-path",
            str(db_path),
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert "Onboarding Visible Window Preflight" in result.output
    text = output_path.read_text(encoding="utf-8")
    assert "# NEXUS TECH Onboarding Visible Window Preflight" in text
    assert "- Status: `pass`" in text
    assert "- Manual result: `not completed by automation`" in text
    assert "manual-required" in text
    assert "preflight never replaces visible-window tester evidence" in text
    assert "title-onboarding" in text
    assert "first-turn-play" in text
    assert "menu-2d --headless --max-frames 1 --window-size 820x620" in text
    assert "play-2d --scenario founder_journey" in text
    assert "--headless --max-frames 1 --window-size 820x620" in text


def test_onboarding_visible_playtest_batch_preflight_runs_current_window_batch(
    tmp_path: Path,
) -> None:
    packet_path = tmp_path / "onboarding-visible.md"
    report_path = tmp_path / "onboarding-visible-report.md"
    output_path = tmp_path / "onboarding-visible-batch-preflight.md"
    db_path = tmp_path / "onboarding-visible-batch-preflight.db"

    packet_result = runner.invoke(
        app,
        [
            "onboarding-visible-playtest-packet",
            "--window-size",
            "820x620",
            "--motion-mode",
            "full",
            "--motion-mode",
            "reduced",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--output",
            str(packet_path),
        ],
    )
    assert packet_result.exit_code == 0

    report_result = runner.invoke(
        app,
        [
            "onboarding-visible-playtest-report",
            "--window-size",
            "820x620",
            "--motion-mode",
            "full",
            "--motion-mode",
            "reduced",
            "--command-prefix",
            ".venv313/bin/nexus-tech",
            "--input",
            str(packet_path),
            "--output",
            str(report_path),
        ],
    )
    assert report_result.exit_code == 0

    for rank, note in (
        (
            "1",
            (
                "Observed terminal guide output directly; Opening flow, Risk Forecast, "
                "and Difficulty cues were readable before the visible window batch."
            ),
        ),
        (
            "2",
            (
                "Observed terminal tutorial output directly; the first-run table "
                "explains command order, finance checks, hiring, and expansion timing."
            ),
        ),
        (
            "3",
            (
                "Observed onboarding audit output directly; all automated clarity "
                "checks passed with concrete command handoff evidence."
            ),
        ),
    ):
        record_result = runner.invoke(
            app,
            [
                "record-onboarding-visible-playtest-route",
                "--report",
                str(report_path),
                "--rank",
                rank,
                "--result",
                "pass",
                "--notes",
                note,
            ],
        )
        assert record_result.exit_code == 0

    result = runner.invoke(
        app,
        [
            "onboarding-visible-playtest-batch-preflight",
            "--report",
            str(report_path),
            "--batch-size",
            "3",
            "--frames",
            "1",
            "--db-path",
            str(db_path),
            "--output",
            str(output_path),
            "--command-prefix",
            ".venv313/bin/nexus-tech",
        ],
    )

    assert result.exit_code == 0
    assert "Onboarding Visible Batch Preflight" in result.output
    text = output_path.read_text(encoding="utf-8")
    assert "# NEXUS TECH Onboarding Visible Batch Preflight" in text
    assert "- Status: `pass`" in text
    assert "- Manual result: `not completed by automation`" in text
    assert "- Batch rows: `3`" in text
    assert "- Preflighted 2D rows: `3`" in text
    assert "- Skipped terminal rows: `0`" in text
    assert "| 4 | `title-onboarding` | `820x620` | `full` | `pass` |" in text
    assert "| 5 | `first-turn-play` | `820x620` | `full` | `pass` |" in text
    assert "| 6 | `title-onboarding` | `820x620` | `reduced` | `pass` |" in text
    assert "menu-2d --headless --max-frames 1 --window-size 820x620" in text
    assert "play-2d --scenario founder_journey" in text
    assert "preflight never replaces visible-window tester evidence" in text


def test_ci_workflow_runs_onboarding_flow_audit_artifact_gate() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert (
        "uv run nexus-tech audit-onboarding-flow --output /tmp/nexus-tech-onboarding-flow-audit.md"
    ) in workflow
    assert "nexus-tech-onboarding-flow-audit" in workflow
    assert "path: /tmp/nexus-tech-onboarding-flow-audit.md" in workflow
    assert "uv run nexus-tech onboarding-visible-playtest-packet" in workflow
    assert "uv run nexus-tech validate-onboarding-visible-playtest-packet" in workflow
    assert "uv run nexus-tech onboarding-visible-playtest-report" in workflow
    assert "uv run nexus-tech validate-onboarding-visible-playtest-report" in workflow
    assert "uv run nexus-tech onboarding-visible-playtest-status" in workflow
    assert "uv run nexus-tech onboarding-visible-playtest-next" in workflow
    assert "uv run nexus-tech validate-onboarding-visible-playtest-next" in workflow
    assert "uv run nexus-tech onboarding-visible-playtest-batch-packet" in workflow
    assert "uv run nexus-tech validate-onboarding-visible-playtest-batch-packet" in workflow
    assert "uv run nexus-tech onboarding-visible-playtest-batch-preflight" in workflow
    assert "uv run nexus-tech onboarding-visible-terminal-batch" in workflow
    assert "uv run nexus-tech validate-onboarding-visible-terminal-batch" in workflow
    assert "uv run nexus-tech onboarding-visible-terminal-evidence-sheet" in workflow
    assert "uv run nexus-tech validate-onboarding-visible-terminal-evidence-sheet" in workflow
    assert "uv run nexus-tech onboarding-visible-window-evidence-sheet" in workflow
    assert "uv run nexus-tech validate-onboarding-visible-window-evidence-sheet" in workflow
    assert "uv run nexus-tech onboarding-visible-evidence-matrix" in workflow
    assert "uv run nexus-tech validate-onboarding-visible-evidence-matrix" in workflow
    assert "uv run nexus-tech onboarding-visible-window-preflight" in workflow
    assert "uv run nexus-tech onboarding-visible-manual-session" in workflow
    assert "uv run nexus-tech validate-onboarding-visible-manual-session" in workflow
    assert "uv run nexus-tech onboarding-visible-ux-issue-intake" in workflow
    assert "uv run nexus-tech validate-onboarding-visible-ux-issue-intake" in workflow
    assert "uv run nexus-tech onboarding-visible-ux-fix-plan" in workflow
    assert "uv run nexus-tech validate-onboarding-visible-ux-fix-plan" in workflow
    assert "uv run nexus-tech onboarding-visible-ux-triage-sprint" in workflow
    assert "uv run nexus-tech validate-onboarding-visible-ux-triage-sprint" in workflow
    assert "uv run nexus-tech onboarding-visible-ux-triage-next" in workflow
    assert "uv run nexus-tech validate-onboarding-visible-ux-triage-next" in workflow
    assert "uv run nexus-tech onboarding-visible-ux-recording-queue" in workflow
    assert "uv run nexus-tech validate-onboarding-visible-ux-recording-queue" in workflow
    assert "uv run nexus-tech onboarding-visible-ux-progress" in workflow
    assert "uv run nexus-tech validate-onboarding-visible-ux-progress" in workflow
    assert "uv run nexus-tech onboarding-visible-ux-batch-packet" in workflow
    assert "uv run nexus-tech validate-onboarding-visible-ux-batch-packet" in workflow
    assert "uv run nexus-tech onboarding-visible-ux-batch-closeout" in workflow
    assert "uv run nexus-tech validate-onboarding-visible-ux-batch-closeout" in workflow
    assert "--window 820x620" in workflow
    assert "--window 1280x720" in workflow
    assert "--window 1440x900" in workflow
    assert "--frames 1" in workflow
    assert "/tmp/nexus-tech-onboarding-visible-playtest.md" in workflow
    assert "/tmp/nexus-tech-onboarding-visible-playtest-report.md" in workflow
    assert "/tmp/nexus-tech-onboarding-visible-playtest-next.md" in workflow
    assert "/tmp/nexus-tech-onboarding-visible-playtest-batch-packet.md" in workflow
    assert "/tmp/nexus-tech-onboarding-visible-batch-preflight.md" in workflow
    assert "/tmp/nexus-tech-onboarding-visible-terminal-batch.md" in workflow
    assert "/tmp/nexus-tech-onboarding-visible-terminal-evidence-sheet.md" in workflow
    assert "/tmp/nexus-tech-onboarding-visible-820x620-evidence-sheet.md" in workflow
    assert "/tmp/nexus-tech-onboarding-visible-1280x720-evidence-sheet.md" in workflow
    assert "/tmp/nexus-tech-onboarding-visible-1440x900-evidence-sheet.md" in workflow
    assert "/tmp/nexus-tech-onboarding-visible-evidence-matrix.md" in workflow
    assert "/tmp/nexus-tech-onboarding-visible-window-preflight.md" in workflow
    assert "/tmp/nexus-tech-onboarding-visible-manual-session.md" in workflow
    assert "/tmp/nexus-tech-onboarding-visible-ux-issue-intake.md" in workflow
    assert "/tmp/nexus-tech-onboarding-visible-ux-fix-plan.md" in workflow
    assert "/tmp/nexus-tech-onboarding-visible-ux-triage-sprint.md" in workflow
    assert "/tmp/nexus-tech-onboarding-visible-ux-triage-next.md" in workflow
    assert "/tmp/nexus-tech-onboarding-visible-ux-recording-queue.md" in workflow
    assert "/tmp/nexus-tech-onboarding-visible-ux-progress.md" in workflow
    assert "/tmp/nexus-tech-onboarding-visible-ux-batch-packet.md" in workflow
    assert "/tmp/nexus-tech-onboarding-visible-ux-batch-closeout.md" in workflow
    assert "nexus-tech-onboarding-visible-playtest" in workflow
    assert "nexus-tech-onboarding-visible-playtest-report" in workflow
    assert "nexus-tech-onboarding-visible-playtest-next" in workflow
    assert "nexus-tech-onboarding-visible-playtest-batch-packet" in workflow
    assert "nexus-tech-onboarding-visible-batch-preflight" in workflow
    assert "nexus-tech-onboarding-visible-terminal-batch" in workflow
    assert "nexus-tech-onboarding-visible-terminal-evidence-sheet" in workflow
    assert "nexus-tech-onboarding-visible-820x620-evidence-sheet" in workflow
    assert "nexus-tech-onboarding-visible-1280x720-evidence-sheet" in workflow
    assert "nexus-tech-onboarding-visible-1440x900-evidence-sheet" in workflow
    assert "nexus-tech-onboarding-visible-evidence-matrix" in workflow
    assert "nexus-tech-onboarding-visible-window-preflight" in workflow
    assert "nexus-tech-onboarding-visible-manual-session" in workflow
    assert "nexus-tech-onboarding-visible-ux-issue-intake" in workflow
    assert "nexus-tech-onboarding-visible-ux-fix-plan" in workflow
    assert "nexus-tech-onboarding-visible-ux-triage-sprint" in workflow
    assert "nexus-tech-onboarding-visible-ux-triage-next" in workflow
    assert "nexus-tech-onboarding-visible-ux-recording-queue" in workflow
    assert "nexus-tech-onboarding-visible-ux-progress" in workflow
    assert "nexus-tech-onboarding-visible-ux-batch-packet" in workflow
    assert "nexus-tech-onboarding-visible-ux-batch-closeout" in workflow


def test_glossary_command_renders_core_stat_help() -> None:
    result = runner.invoke(app, ["glossary"])

    assert result.exit_code == 0
    assert "Glossary" in result.output
    assert "Decision Guide" in result.output


def test_validate_content_command_renders_health(monkeypatch: MonkeyPatch) -> None:
    report = CatalogValidationReport(
        scenario_count=2,
        template_count=3,
        rival_count=1,
        event_count=4,
        issues=(),
    )
    monkeypatch.setattr(cli_module, "validate_content_catalogs", lambda: report)

    result = runner.invoke(app, ["validate-content"])

    assert result.exit_code == 0
    assert "Content Health" in result.output
    assert "All catalog references" in result.output


def test_validate_content_command_exits_when_issues_exist(monkeypatch: MonkeyPatch) -> None:
    report = CatalogValidationReport(
        scenario_count=2,
        template_count=3,
        rival_count=1,
        event_count=4,
        issues=("Event 'broken' is registered but has no effect handler.",),
    )
    monkeypatch.setattr(cli_module, "validate_content_catalogs", lambda: report)

    result = runner.invoke(app, ["validate-content"])

    assert result.exit_code == 1
    assert "broken" in result.output


def test_invalid_balance_scenario_renders_clean_error() -> None:
    result = runner.invoke(app, ["simulate-balance", "--scenario", "missing_scenario"])

    assert result.exit_code == 1
    assert "Invalid Scenario" in result.output
    assert "missing_scenario" in result.output
    assert "Traceback" not in result.output


def test_check_saves_command_renders_health(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    class FakeCoordinator:
        def __init__(self, db_path: Path) -> None:
            captured["db_path"] = db_path

        def check_save_health(self) -> SimpleNamespace:
            return SimpleNamespace(
                integrity_ok=True,
                foreign_key_ok=True,
                slot_count=2,
                schema_version=12,
                message="SQLite integrity and foreign keys are healthy.",
            )

    monkeypatch.setattr(cli_module, "SaveLoadCoordinator", FakeCoordinator)
    db_path = tmp_path / "health.db"
    result = runner.invoke(app, ["check-saves", "--db-path", str(db_path)])

    assert result.exit_code == 0
    assert captured["db_path"] == db_path
    assert "Save Health" in result.output
    assert "Integrity: ok" in result.output
    assert "Foreign Keys: ok" in result.output
    assert "Schema Version: 12" in result.output


def test_doctor_command_renders_local_diagnostics(tmp_path: Path) -> None:
    db_path = tmp_path / "no-save-yet.db"

    result = runner.invoke(app, ["doctor", "--db-path", str(db_path)])

    assert result.exit_code == 0
    assert "NEXUS TECH Doctor" in result.output
    assert "Version" in result.output
    assert __version__ in result.output
    assert "No save database found yet." in result.output


def test_list_saves_command_renders_slot_catalog(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    summaries = [
        SaveSlotSummary(
            slot_name="active",
            company_name="NEXUS TECH",
            scenario_title="Founder Journey",
            current_turn=4,
            cash_on_hand=Decimal("8200.00"),
            reputation=57,
            active_products=2,
            headcount=1,
            updated_at="2026-04-13T01:00:00+00:00",
            victory_achieved=False,
            game_over=False,
            saved_with_version="0.12.0",
            schema_version=12,
        )
    ]

    class FakeCoordinator:
        def __init__(self, db_path: Path) -> None:
            captured["db_path"] = db_path

        def list_save_slots(self) -> list[SaveSlotSummary]:
            return summaries

    monkeypatch.setattr(cli_module, "SaveLoadCoordinator", FakeCoordinator)

    db_path = tmp_path / "saves.db"
    result = runner.invoke(
        app,
        ["list-saves", "--db-path", str(db_path)],
        terminal_width=220,
    )

    assert result.exit_code == 0
    assert captured["db_path"] == db_path
    assert "Save Slots" in result.output
    assert "active" in result.output
    assert "Campaign Path" not in result.output
    assert "Diff" not in result.output


def test_list_archives_command_renders_archive_catalog(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    archives = [
        RunArchiveSummary(
            archive_key="active:8:strategic_acquisition",
            slot_name="active",
            company_name="NEXUS TECH",
            scenario_id="founder_journey",
            scenario_title="Founder Journey",
            difficulty_mode="founder",
            campaign_commitment_choice="Sharpen the Flagship",
            campaign_consequence_choice="Defend Control",
            completed_turn=8,
            victory_achieved=True,
            game_over=False,
            exit_outcome="strategic_acquisition",
            total_score=188,
            score_tier="strong",
            campaign_grade="A",
            estimated_valuation=Decimal("48600.00"),
            achievement_badges=("board_trusted", "enterprise_operator"),
            strategic_outlook="strategic_acquisition",
            offer_value=Decimal("55890.00"),
            final_cash=Decimal("12400.00"),
            final_reputation=64,
            archived_at="2026-04-28T01:00:00+00:00",
            review_title="After-Action Review",
            review_primary_area="finance",
            review_primary_summary="Cash discipline stayed ahead of scale pressure.",
            review_next_focus="review_finance",
        )
    ]

    class FakeCoordinator:
        def __init__(self, db_path: Path) -> None:
            captured["db_path"] = db_path

        def list_run_archives(self) -> list[RunArchiveSummary]:
            return archives

    monkeypatch.setattr(cli_module, "SaveLoadCoordinator", FakeCoordinator)

    db_path = tmp_path / "archives.db"
    result = runner.invoke(
        app,
        ["list-archives", "--db-path", str(db_path)],
        terminal_width=240,
    )

    assert result.exit_code == 0
    assert captured["db_path"] == db_path
    assert "Run Archives" in result.output
    assert "Next Focus" in result.output


def test_beta_evidence_command_reports_archive_coverage_without_manual_signoff(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    archives = [
        RunArchiveSummary(
            archive_key="active:12:none",
            slot_name="active",
            company_name="NEXUS TECH",
            scenario_id="founder_journey",
            scenario_title="Founder Journey",
            difficulty_mode="standard",
            campaign_commitment_choice="Sharpen the Flagship",
            campaign_consequence_choice="Defend Control",
            completed_turn=12,
            victory_achieved=True,
            game_over=False,
            exit_outcome="profitable_independence",
            total_score=188,
            score_tier="strong",
            campaign_grade="A",
            estimated_valuation=Decimal("42000.00"),
            achievement_badges=(),
            strategic_outlook="profitable_independence",
            offer_value=Decimal("0.00"),
            final_cash=Decimal("12400.00"),
            final_reputation=64,
            archived_at="2026-07-14T01:00:00+00:00",
        )
    ]

    class FakeCoordinator:
        def __init__(self, db_path: Path) -> None:
            self.db_path = db_path

        def list_run_archives(self) -> list[RunArchiveSummary]:
            return archives

    monkeypatch.setattr(cli_module, "SaveLoadCoordinator", FakeCoordinator)

    result = runner.invoke(
        app,
        ["beta-evidence", "--db-path", str(tmp_path / "archives.db")],
    )

    assert result.exit_code == 0
    assert "Beta Archive Evidence" in result.output
    assert "archive-evidence-needed" in result.output
    assert "Manual signoff remains required" in result.output
    assert "bootstrap_studio" in result.output


def test_compare_archives_command_renders_archive_comparison(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    archives = [
        RunArchiveSummary(
            archive_key="active:8:strategic_acquisition",
            slot_name="active",
            company_name="NEXUS TECH",
            scenario_title="Founder Journey",
            completed_turn=8,
            victory_achieved=True,
            game_over=False,
            exit_outcome="strategic_acquisition",
            total_score=188,
            score_tier="strong",
            campaign_grade="A",
            estimated_valuation=Decimal("48600.00"),
            achievement_badges=("board_trusted", "enterprise_operator"),
            strategic_outlook="strategic_acquisition",
            offer_value=Decimal("55890.00"),
            final_cash=Decimal("12400.00"),
            final_reputation=64,
            archived_at="2026-04-28T01:00:00+00:00",
            review_title="After-Action Review",
            review_primary_area="finance",
            review_primary_summary="Cash discipline stayed ahead of scale pressure.",
            review_next_focus="review_finance",
        )
    ]

    class FakeCoordinator:
        def __init__(self, db_path: Path) -> None:
            self.db_path = db_path

        def list_run_archives(self) -> list[RunArchiveSummary]:
            return archives

    monkeypatch.setattr(cli_module, "SaveLoadCoordinator", FakeCoordinator)

    db_path = tmp_path / "archives.db"
    result = runner.invoke(app, ["compare-archives", "--db-path", str(db_path)])

    assert result.exit_code == 0
    assert "Archive Comparison" in result.output
    assert "Run Leaders" in result.output
    assert "Next Gap" in result.output
    assert "Review Lane" in result.output


def test_rename_save_command_calls_coordinator(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    class FakeCoordinator:
        def __init__(self, db_path: Path) -> None:
            captured["db_path"] = db_path

        def rename_save(self, from_slot_name: str, to_slot_name: str) -> None:
            captured["from_slot_name"] = from_slot_name
            captured["to_slot_name"] = to_slot_name

    monkeypatch.setattr(cli_module, "SaveLoadCoordinator", FakeCoordinator)

    db_path = tmp_path / "rename.db"
    result = runner.invoke(
        app,
        ["rename-save", "--slot", "active", "--to-slot", "archive", "--db-path", str(db_path)],
    )

    assert result.exit_code == 0
    assert captured["db_path"] == db_path
    assert captured["from_slot_name"] == "active"
    assert captured["to_slot_name"] == "archive"


def test_delete_save_command_calls_coordinator(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    class FakeCoordinator:
        def __init__(self, db_path: Path) -> None:
            captured["db_path"] = db_path

        def delete_save(self, slot_name: str) -> None:
            captured["slot_name"] = slot_name

    monkeypatch.setattr(cli_module, "SaveLoadCoordinator", FakeCoordinator)

    db_path = tmp_path / "delete.db"
    result = runner.invoke(
        app,
        ["delete-save", "--slot", "active", "--yes", "--db-path", str(db_path)],
    )

    assert result.exit_code == 0
    assert captured["db_path"] == db_path
    assert captured["slot_name"] == "active"


def test_load_game_command_resumes_loaded_slot(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = make_demo_state()
    captured: dict[str, object] = {}

    class FakeCoordinator:
        def __init__(self, db_path: Path) -> None:
            captured["db_path"] = db_path

        def load_game(self, slot_name: str) -> SimpleNamespace:
            captured["load_slot"] = slot_name
            return SimpleNamespace(
                slot_name=slot_name,
                state=state,
                rng=RandomSource(seed=11),
            )

    def fake_run_game_loop(
        *,
        state: GameState,
        rng: RandomSource,
        db_path: Path,
        slot_name: str,
    ) -> None:
        captured["loop_state"] = state
        captured["loop_seed"] = rng.seed
        captured["loop_db_path"] = db_path
        captured["loop_slot"] = slot_name

    monkeypatch.setattr(cli_module, "SaveLoadCoordinator", FakeCoordinator)
    monkeypatch.setattr(cli_module, "run_game_loop", fake_run_game_loop)

    db_path = tmp_path / "load.db"
    result = runner.invoke(app, ["load-game", "--db-path", str(db_path), "--slot", "showcase"])

    assert result.exit_code == 0
    assert captured["db_path"] == db_path
    assert captured["load_slot"] == "showcase"
    assert captured["loop_state"] == state
    assert captured["loop_seed"] == 11
    assert captured["loop_db_path"] == db_path
    assert captured["loop_slot"] == "showcase"


def test_continue_last_game_command_resumes_latest_slot(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = make_demo_state()
    captured: dict[str, object] = {}

    class FakeCoordinator:
        def __init__(self, db_path: Path) -> None:
            captured["db_path"] = db_path

        def continue_last_game(self) -> SimpleNamespace:
            return SimpleNamespace(
                slot_name="latest",
                state=state,
                rng=RandomSource(seed=17),
            )

    def fake_run_game_loop(
        *,
        state: GameState,
        rng: RandomSource,
        db_path: Path,
        slot_name: str,
    ) -> None:
        captured["loop_state"] = state
        captured["loop_seed"] = rng.seed
        captured["loop_db_path"] = db_path
        captured["loop_slot"] = slot_name

    monkeypatch.setattr(cli_module, "SaveLoadCoordinator", FakeCoordinator)
    monkeypatch.setattr(cli_module, "run_game_loop", fake_run_game_loop)

    db_path = tmp_path / "continue.db"
    result = runner.invoke(app, ["continue-last-game", "--db-path", str(db_path)])

    assert result.exit_code == 0
    assert captured["db_path"] == db_path
    assert captured["loop_state"] == state
    assert captured["loop_seed"] == 17
    assert captured["loop_db_path"] == db_path
    assert captured["loop_slot"] == "latest"


def test_dashboard_rendering_contains_required_sections() -> None:
    state = make_demo_state(include_pending_event=True)
    console = Console(record=True, width=140)

    render_dashboard(console, state)
    output = console.export_text()

    assert "Company Overview" in output
    assert "Product Portfolio" in output
    assert "Team Table" in output
    assert "Action Menu" in output
    assert "Event Notification" in output
    assert "Market Watch" in output
    assert "Late-Game" in output
    assert "Finance" in output
    assert "Risk Forecast" in output
    assert "End-Turn Preview" in output
    assert "Warning Level" in output
    assert "Board / Governance" in output
    assert "Key Accounts" in output
    assert "Strategy" in output
    assert "Price" in output
    assert "Roadmap" in output
    assert "Segment" in output
    assert "Onboarding" in output
    assert "Guided Opening" in output
    assert "Difficulty Profile" in output
    assert "Trade-off" in output
    assert "Not Now" in output


def test_turn_resolution_rendering_contains_summary_sections() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")
    resolution = resolve_turn(state, RandomSource(seed=5))
    console = Console(record=True, width=140)

    render_turn_resolution(console, resolution)
    output = console.export_text()

    assert f"Turn {resolution.resolved_turn} Summary" in output
    assert "Portfolio Results" in output
    assert "Outlook" in output
    assert "Cash On Hand" in output
    assert "Run Score" in output


def test_report_rendering_contains_score_and_turn_history() -> None:
    state = make_demo_state()
    console = Console(record=True, width=140)

    render_report(console, state)
    output = console.export_text()

    assert "Run Overview" in output
    assert "Scorecard" in output
    assert "Risk Forecast" in output
    assert "End-Turn Preview" in output
    assert "Warning Level" in output
    assert "Turn History" in output
    assert "Quarter Plan" in output
    assert "Finance" in output
    assert "Competitor Watch" in output
    assert "Estimated Value" in output
    assert "Exit Outlook" in output
    assert "Key Accounts" in output
    assert "Lane Mix" in output
    assert "Trade-off" in output
    assert "Capital Plan" in output
    assert "Partnerships" in output
    assert "Difficulty Profile" in output


def test_show_progression_command_renders_meta_summary(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    archives = [
        RunArchiveSummary(
            archive_key="active:8:strategic_acquisition",
            slot_name="active",
            company_name="NEXUS TECH",
            scenario_title="Founder Journey",
            completed_turn=8,
            victory_achieved=True,
            game_over=False,
            exit_outcome="strategic_acquisition",
            total_score=188,
            score_tier="strong",
            campaign_grade="A",
            estimated_valuation=Decimal("48600.00"),
            achievement_badges=("board_trusted", "channel_builder"),
            strategic_outlook="strategic_acquisition",
            offer_value=Decimal("55890.00"),
            final_cash=Decimal("12400.00"),
            final_reputation=64,
            archived_at="2026-04-28T01:00:00+00:00",
        )
    ]

    class FakeCoordinator:
        def __init__(self, db_path: Path) -> None:
            self.db_path = db_path

        def list_run_archives(self) -> list[RunArchiveSummary]:
            return archives

    monkeypatch.setattr(cli_module, "SaveLoadCoordinator", FakeCoordinator)

    db_path = tmp_path / "archives.db"
    result = runner.invoke(app, ["show-progression", "--db-path", str(db_path)])

    assert result.exit_code == 0
    assert "Meta Progression" in result.output
    assert "Campaign Tier" in result.output
    assert "Unlocked Rewards" in result.output
    assert "first_victory" in result.output


def test_list_unlocks_command_renders_unlock_catalog(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    archives = [
        RunArchiveSummary(
            archive_key="active:8:ipo_ready",
            slot_name="active",
            company_name="NEXUS TECH",
            scenario_title="Founder Journey",
            completed_turn=8,
            victory_achieved=True,
            game_over=False,
            exit_outcome="ipo_ready",
            total_score=228,
            score_tier="strong",
            campaign_grade="S",
            estimated_valuation=Decimal("68600.00"),
            achievement_badges=("board_trusted", "channel_builder"),
            strategic_outlook="ipo_ready",
            offer_value=Decimal("80200.00"),
            final_cash=Decimal("16400.00"),
            final_reputation=72,
            archived_at="2026-04-30T01:00:00+00:00",
        )
    ]

    class FakeCoordinator:
        def __init__(self, db_path: Path) -> None:
            self.db_path = db_path

        def list_run_archives(self) -> list[RunArchiveSummary]:
            return archives

    monkeypatch.setattr(cli_module, "SaveLoadCoordinator", FakeCoordinator)

    db_path = tmp_path / "archives.db"
    result = runner.invoke(app, ["list-unlocks", "--db-path", str(db_path)])

    assert result.exit_code == 0
    assert "Unlock Catalog" in result.output
    assert "Reward Id" in result.output
    assert "Next Unlock" in result.output


def test_template_catalog_rendering_contains_catalog_title() -> None:
    templates = cli_module.get_available_product_templates()
    console = Console(record=True, width=140)

    render_product_template_catalog(console, templates[:2])
    output = console.export_text()

    assert "Product Template Catalog" in output
    assert templates[0].title in output
    assert templates[1].title in output


def test_competitor_archetype_catalog_rendering_contains_title() -> None:
    archetypes = cli_module.get_available_competitor_archetypes()
    console = Console(record=True, width=140)

    render_competitor_archetype_catalog(console, archetypes[:2])
    output = console.export_text()

    assert "Competitor Archetypes" in output
    assert archetypes[0].title in output


def test_quick_guide_rendering_contains_opening_flow() -> None:
    console = Console(record=True, width=80, soft_wrap=False)

    render_quick_guide(console)
    output = console.export_text()

    assert "Quick Guide" in output
    assert "Opening flow" in output
    assert "Risk Forecast" in output
    assert "Difficulty cues" in output
    assert "or headcount." in output
    assert "Founder punishes weak runway" in output
    assert "first clean growth signal." in output


def test_tutorial_rendering_contains_safe_first_actions() -> None:
    console = Console(record=True, width=120)

    render_tutorial(console)
    output = console.export_text()

    assert "First Run Tutorial" in output
    assert "hire_employee" in output
    assert "Turn Summary" in output
    assert "Watch For" in output
    assert "--difficulty builder" in output


def test_glossary_rendering_contains_decision_terms() -> None:
    console = Console(record=True, width=120)

    render_glossary(console)
    output = console.export_text()

    assert "Glossary" in output
    assert "Board Confidence" in output
    assert "Decision Guide" in output


def test_content_health_rendering_contains_issues_when_present() -> None:
    console = Console(record=True, width=120)
    report = CatalogValidationReport(
        scenario_count=1,
        template_count=1,
        rival_count=1,
        event_count=1,
        issues=("Broken reference",),
    )

    render_content_health(console, report)
    output = console.export_text()

    assert "Content Health" in output
    assert "failed" in output
    assert "Broken reference" in output


def test_victory_rendering_contains_summary_metrics() -> None:
    state = make_demo_state()
    state.victory_achieved = True
    state.victory_reason = "You built a durable software company."
    state.exit_outcome = ExitOutcome.STRATEGIC_ACQUISITION
    state.exit_summary = "Strategic Acquisition: A platform wants your customer base."
    console = Console(record=True, width=140)

    render_victory(console, state)
    output = console.export_text()

    assert "Victory" in output
    assert "Run Score" in output
    assert "Estimated Value" in output
    assert "Exit Path" in output
    assert "Strategic Outlook" in output
    assert "After-Action Review" in output


def test_game_over_rendering_contains_failure_postmortem() -> None:
    state = make_demo_state()
    state.company.game_over = True
    state.company.cash_on_hand = Decimal("-25.00")
    console = Console(record=True, width=140)

    render_game_over(console, state)
    output = console.export_text()

    assert "Company Shutdown" in output
    assert "Failure Postmortem" in output


def test_confirm_end_turn_rejects_risky_preview(monkeypatch: MonkeyPatch) -> None:
    state = make_demo_state()
    console = Console(record=True, width=120)
    monkeypatch.setattr(cli_module, "console", console)
    monkeypatch.setattr(
        cli_module,
        "build_end_turn_preview",
        lambda _state: EndTurnPreviewSummary(
            blocked=False,
            headline="Risky preview",
            note="Sample shutdown",
            top_command="review_finance",
            risk_shift="high -> critical",
            projected_outcome="sample shutdown risk",
            warning_level="critical",
            requires_confirmation=True,
            confirmation_reason="Preview shows a sample shutdown.",
            metrics=(),
            warnings=("Sample shutdown",),
        ),
    )
    monkeypatch.setattr(cli_module, "ask_confirm_input", lambda *args, **kwargs: False)

    confirmed = cli_module.confirm_end_turn(state)

    assert confirmed is False
    assert "End-Turn Warning" in console.export_text()
