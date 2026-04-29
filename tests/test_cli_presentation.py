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
from nexus_tech.simulation.catalog_validation import CatalogValidationReport
from nexus_tech.simulation.engine import create_new_game, resolve_turn
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
    assert "founder" in result.output


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


def test_version_option_prints_installed_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert f"NEXUS TECH {__version__}" in result.output


def test_guide_command_renders_quick_start() -> None:
    result = runner.invoke(app, ["guide"])

    assert result.exit_code == 0
    assert "Quick Guide" in result.output


def test_tutorial_command_renders_first_run_path() -> None:
    result = runner.invoke(app, ["tutorial"])

    assert result.exit_code == 0
    assert "First Run Tutorial" in result.output
    assert "new-game" in result.output


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
    result = runner.invoke(app, ["list-saves", "--db-path", str(db_path)])

    assert result.exit_code == 0
    assert captured["db_path"] == db_path
    assert "Save Slots" in result.output
    assert "active" in result.output


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
        )
    ]

    class FakeCoordinator:
        def __init__(self, db_path: Path) -> None:
            captured["db_path"] = db_path

        def list_run_archives(self) -> list[RunArchiveSummary]:
            return archives

    monkeypatch.setattr(cli_module, "SaveLoadCoordinator", FakeCoordinator)

    db_path = tmp_path / "archives.db"
    result = runner.invoke(app, ["list-archives", "--db-path", str(db_path)])

    assert result.exit_code == 0
    assert captured["db_path"] == db_path
    assert "Run Archives" in result.output


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
    assert "Board / Governance" in output
    assert "Key Accounts" in output
    assert "Strategy" in output
    assert "Price" in output
    assert "Roadmap" in output
    assert "Segment" in output
    assert "Onboarding" in output


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
    assert "Turn History" in output
    assert "Quarter Plan" in output
    assert "Finance" in output
    assert "Competitor Watch" in output
    assert "Estimated Value" in output
    assert "Exit Outlook" in output
    assert "Key Accounts" in output


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
    console = Console(record=True, width=120)

    render_quick_guide(console)
    output = console.export_text()

    assert "Quick Guide" in output
    assert "Opening flow" in output


def test_tutorial_rendering_contains_safe_first_actions() -> None:
    console = Console(record=True, width=120)

    render_tutorial(console)
    output = console.export_text()

    assert "First Run Tutorial" in output
    assert "hire_employee" in output
    assert "End the turn" in output


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
