from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest

from nexus_tech.domain.models import (
    BoardAsk,
    BudgetStance,
    CampaignGoalId,
    CandidateTrait,
    Company,
    CompanyStrategy,
    Competitor,
    CompetitorIntelEntry,
    CompetitorMove,
    ContractBillingModel,
    ContractCadence,
    CustomerAccount,
    CustomerAccountStatus,
    DifficultyMode,
    Employee,
    EmployeeRole,
    EventCategory,
    EventHistoryEntry,
    EventOption,
    ExitOutcome,
    FinanceState,
    FunctionalBudget,
    FunctionalBudgetPreset,
    FundingHistoryEntry,
    FundingType,
    GameState,
    HiringCandidate,
    HiringCandidateStage,
    LifecycleStage,
    MarketCycle,
    MarketSegment,
    MilestoneEntry,
    MilestoneId,
    PackagingStrategy,
    PendingEvent,
    PricingTier,
    Product,
    ProductReleasePlan,
    ProductReleaseStatus,
    ProductReleaseType,
    QuarterPlan,
    RoadmapFocus,
    RoadmapProject,
    RoadmapProjectStatus,
    RoadmapProjectType,
    SalesDeal,
    SalesDealStage,
    ScenarioObjectiveMetric,
    Seniority,
    SubscriptionPackage,
    SupportProgram,
    TurnLedgerEntry,
)
from nexus_tech.persistence.database import DatabaseManager
from nexus_tech.persistence.errors import CorruptSaveError, SaveNotFoundError
from nexus_tech.persistence.save_coordinator import DEFAULT_SAVE_SLOT, SaveLoadCoordinator
from nexus_tech.simulation.randomness import RandomSource


def make_state() -> GameState:
    product = Product(
        name="Nexus One",
        lifecycle_stage=LifecycleStage.GROWTH,
        quality=61,
        bug_level=17,
        market_fit=56,
        technical_debt=24,
        user_count=42,
        revenue_per_user=Decimal("31.00"),
        feature_count=2,
        maintenance_cost=Decimal("280.00"),
        acquisition_rate=Decimal("0.0720"),
        churn_rate=Decimal("0.0480"),
        pricing_tier=PricingTier.PREMIUM,
        packaging_strategy=PackagingStrategy.SUITE,
        target_segment=MarketSegment.ENTERPRISE,
        is_active=True,
    )
    manager = Employee(
        full_name="Jules Park",
        role=EmployeeRole.PRODUCT_MANAGER,
        seniority=Seniority.SENIOR,
        salary=Decimal("980.00"),
        energy=76,
        morale=74,
        productivity=66,
        specialization="delivery",
        experience_points=48,
        promotion_readiness=63,
        attrition_risk=9,
        performance_rating=71,
        tenure_turns=8,
        underperformance_streak=0,
        leadership_score=82,
        assigned_product_id=product.id,
    )
    employee = Employee(
        full_name="Ada Wong",
        role=EmployeeRole.ENGINEER,
        seniority=Seniority.MID,
        salary=Decimal("720.00"),
        energy=73,
        morale=71,
        productivity=68,
        specialization="platform",
        experience_points=24,
        promotion_readiness=48,
        attrition_risk=14,
        performance_rating=67,
        tenure_turns=5,
        underperformance_streak=1,
        leadership_score=58,
        assigned_product_id=product.id,
        manager_id=manager.id,
    )
    pending_event = PendingEvent(
        event_id="competitor_pressure",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Competitor Pressure",
        description="A rival is putting pressure on your flagship.",
        triggered_turn=4,
        cooldown_turns=4,
        target_product_id=product.id,
        target_employee_id=employee.id,
        options=[
            EventOption(
                id="rush_countermove",
                label="Rush a counter-move",
                description="Move fast and accept technical stress.",
            ),
            EventOption(
                id="differentiate",
                label="Differentiate on quality",
                description="Protect the brand through product quality.",
            ),
        ],
    )
    event_history = [
        EventHistoryEntry(
            event_id="sudden_press_mention",
            category=EventCategory.REPUTATION_INCIDENT,
            title="Sudden Press Mention",
            triggered_turn=3,
            resolved_turn=3,
            selected_option_id="ride_the_wave",
            selected_option_label="Ride the wave",
            result_text="Users jumped and reputation improved.",
        )
    ]
    milestone_history = [
        MilestoneEntry(
            milestone_id=MilestoneId.FIRST_100_USERS,
            title="First 100 Users",
            description="Your portfolio reached its first meaningful usage milestone.",
            unlocked_turn=4,
            reward_text="Reputation +2 from visible early traction.",
        )
    ]
    turn_history = [
        TurnLedgerEntry(
            turn=3,
            total_revenue=Decimal("930.00"),
            total_operating_cost=Decimal("1610.00"),
            net_cash_flow=Decimal("-680.00"),
            cash_on_hand=Decimal("7630.50"),
            reputation=57,
            total_users=42,
            headcount=2,
            roadmap_focus=RoadmapFocus.GROWTH_PUSH,
        )
    ]
    competitor = Competitor(
        name="Atlas Cloud",
        archetype_id="trust_monolith",
        focus_segment=MarketSegment.ENTERPRISE,
        strength=67,
        aggression=61,
        pricing_tier=PricingTier.PREMIUM,
        active_product_count=2,
        funding_level=2,
    )
    customer_account = CustomerAccount(
        name="Enterprise Anchor: Nexus One",
        product_id=product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("850.00"),
        plan_tier=PricingTier.PREMIUM,
        contract_cadence=ContractCadence.ANNUAL,
        billing_model=ContractBillingModel.SEAT_BASED,
        seat_count=26,
        usage_units=9,
        add_on_count=2,
        annual_prepay=True,
        discount_rate=Decimal("0.0300"),
        satisfaction=72,
        onboarding_health=74,
        support_load=18,
        open_tickets=5,
        sla_breach_risk=13,
        invoice_risk=17,
        failed_payment_risk=12,
        dunning_steps=1,
        escalation_count=1,
        expansion_potential=66,
        renewal_health=70,
        renewal_turn=6,
        churn_risk=18,
        status=CustomerAccountStatus.ACTIVE,
    )
    finance = FinanceState(
        debt_principal=Decimal("3200.00"),
        loan_interest_rate=Decimal("0.0350"),
        equity_dilution=Decimal("0.0800"),
        investor_pressure=9,
        board_confidence=64,
        covenant_risk=11,
        missed_board_targets=1,
        total_raised=Decimal("7400.00"),
        forecast_net_cash_flow=Decimal("-420.00"),
        forecast_runway_turns=18,
        burn_multiple=Decimal("0.54"),
        governance_risk=16,
        board_pressure=21,
        board_directive="prove_reliability",
        active_board_ask=BoardAsk.RELIABILITY,
        board_warning_active=True,
        board_warning_level=2,
        last_board_review_turn=4,
        last_funding_turn=3,
    )
    funding_history = [
        FundingHistoryEntry(
            funding_type=FundingType.ANGEL,
            turn=3,
            amount=Decimal("4200.00"),
            dilution_added=Decimal("0.0800"),
            debt_added=Decimal("0.00"),
            summary="Closed an angel round to extend runway.",
        ),
        FundingHistoryEntry(
            funding_type=FundingType.LOAN,
            turn=4,
            amount=Decimal("3200.00"),
            dilution_added=Decimal("0.0000"),
            debt_added=Decimal("3200.00"),
            summary="Added debt to stabilise the quarter plan.",
        ),
    ]
    quarter_plan = QuarterPlan(
        budget_stance=BudgetStance.AGGRESSIVE,
        set_turn=4,
        target_turn=6,
        revenue_target=Decimal("1400.00"),
        user_target=60,
        cash_reserve_target=Decimal("9000.00"),
        headcount_cap=3,
    )
    product_release = ProductReleasePlan(
        product_id=product.id,
        release_type=ProductReleaseType.MINOR_RELEASE,
        status=ProductReleaseStatus.PLANNED,
        progress=2,
        required_progress=6,
        risk=34,
        scheduled_turn=4,
        summary="Minor release planned.",
    )
    sales_deal = SalesDeal(
        product_id=product.id,
        name="Enterprise buyer: Nexus One",
        segment=MarketSegment.ENTERPRISE,
        stage=SalesDealStage.DEMO,
        plan_tier=PricingTier.PREMIUM,
        subscription_package=SubscriptionPackage.ENTERPRISE_SUITE,
        billing_model=ContractBillingModel.SEAT_BASED,
        seat_commitment=30,
        usage_commitment=12,
        add_on_commitment=2,
        annual_prepay_offer=True,
        value=Decimal("1300.00"),
        proposed_discount_rate=Decimal("0.0400"),
        probability=52,
        created_turn=4,
        updated_turn=4,
    )
    roadmap_project = RoadmapProject(
        project_type=RoadmapProjectType.ENTERPRISE_CERTIFICATION,
        status=RoadmapProjectStatus.ACTIVE,
        target_product_id=product.id,
        progress=3,
        required_progress=8,
        epic_count=4,
        epics_completed=1,
        started_turn=4,
        deadline_turn=7,
        dependency_project_type=RoadmapProjectType.PLATFORM_REBUILD,
        delivery_risk=34,
        summary="Enterprise certification started.",
    )
    competitor_intel = CompetitorIntelEntry(
        turn=4,
        competitor_name="Atlas Cloud",
        move=CompetitorMove.FEATURE_SPRINT,
        summary="Atlas Cloud accelerated a feature sprint.",
    )
    hiring_candidate = HiringCandidate(
        full_name="Riley Shaw",
        role=EmployeeRole.MARKETER,
        seniority=Seniority.MID,
        specialization="growth",
        trait=CandidateTrait.FAST_LEARNER,
        salary_expectation=Decimal("840.00"),
        expected_productivity=72,
        stage=HiringCandidateStage.INTERVIEWED,
        sourced_turn=3,
        expires_turn=6,
        offer_deadline_turn=5,
        interview_score=64,
        acceptance_chance=71,
        market_salary_pressure=12,
        negotiation_rounds=1,
    )
    return GameState(
        company=Company(
            name="NEXUS TECH",
            cash_on_hand=Decimal("7630.50"),
            reputation=57,
            strategy=CompanyStrategy.QUALITY,
            current_turn=4,
        ),
        products=[product],
        employees=[manager, employee],
        finance=finance,
        competitors=[competitor],
        customer_accounts=[customer_account],
        product_releases=[product_release],
        sales_deals=[sales_deal],
        roadmap_projects=[roadmap_project],
        competitor_intel=[competitor_intel],
        quarter_plan=quarter_plan,
        functional_budget=FunctionalBudget(
            preset=FunctionalBudgetPreset.CUSTOMER_TRUST,
            engineering_share=25,
            marketing_share=18,
            customer_success_share=37,
            g_and_a_share=20,
        ),
        support_program=SupportProgram(
            knowledge_base_level=38,
            automation_level=29,
            sla_target=56,
            backlog_queue=7,
            escalation_queue=3,
            resolved_last_turn=8,
            deflection_score=41,
            sla_breaches_last_turn=1,
        ),
        difficulty_mode=DifficultyMode.FOUNDER,
        campaign_goal_id=CampaignGoalId.CATEGORY_LEADER,
        pending_event=pending_event,
        event_history=event_history,
        milestone_history=milestone_history,
        funding_history=funding_history,
        hiring_candidates=[hiring_candidate],
        roadmap_focus=RoadmapFocus.GROWTH_PUSH,
        roadmap_set_turn=3,
        market_cycle=MarketCycle.EXPANDING,
        market_cycle_turns_remaining=2,
        turn_history=turn_history,
        victory_achieved=True,
        victory_reason="You built a durable software company.",
        exit_outcome=ExitOutcome.STRATEGIC_ACQUISITION,
        exit_summary="Strategic Acquisition: A larger platform wants the customer base.",
        scenario_id="vc_sprint",
        scenario_title="VC Sprint",
        scenario_objective="Close one enterprise deal.",
        scenario_objective_metric=ScenarioObjectiveMetric.CLOSED_DEALS,
        scenario_objective_target=1,
        action_points_remaining=1,
    )


def test_schema_initialization_creates_required_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "game.db"

    DatabaseManager(db_path).initialize()

    with sqlite3.connect(db_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert {
        "save_slots",
        "companies",
        "products",
        "employees",
        "finance_state",
        "funding_history",
        "quarter_plan",
        "competitors",
        "pending_events",
        "pending_event_options",
        "event_history",
        "milestone_history",
        "turn_history",
        "customer_accounts",
        "product_releases",
        "sales_deals",
        "roadmap_projects",
        "competitor_intel",
        "hiring_candidates",
    }.issubset(table_names)

    with sqlite3.connect(db_path) as connection:
        save_slot_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(save_slots)").fetchall()
        }
        product_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(products)").fetchall()
        }
        employee_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(employees)").fetchall()
        }
        customer_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(customer_accounts)").fetchall()
        }
        sales_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(sales_deals)").fetchall()
        }
        hiring_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(hiring_candidates)").fetchall()
        }
        roadmap_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(roadmap_projects)").fetchall()
        }
        competitor_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(competitors)").fetchall()
        }
        finance_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(finance_state)").fetchall()
        }
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert {
        "scenario_id",
        "scenario_title",
        "scenario_objective",
        "scenario_objective_metric",
        "scenario_objective_target",
        "difficulty_mode",
        "campaign_goal_id",
        "roadmap_focus",
        "roadmap_set_turn",
        "functional_budget_preset",
        "budget_engineering_share",
        "budget_marketing_share",
        "budget_customer_success_share",
        "budget_g_and_a_share",
        "support_knowledge_base_level",
        "support_automation_level",
        "support_sla_target",
        "support_backlog_queue",
        "support_escalation_queue",
        "support_resolved_last_turn",
        "support_deflection_score",
        "support_sla_breaches_last_turn",
        "market_cycle",
        "market_cycle_turns_remaining",
        "victory_achieved",
        "victory_reason",
        "exit_outcome",
        "exit_summary",
        "saved_with_version",
        "schema_version",
    }.issubset(save_slot_columns)
    assert {"target_segment", "packaging_strategy"}.issubset(product_columns)
    assert {"archetype_id", "current_move", "momentum", "funding_level"}.issubset(
        competitor_columns
    )
    assert {
        "board_confidence",
        "covenant_risk",
        "missed_board_targets",
        "forecast_net_cash_flow",
        "forecast_runway_turns",
        "burn_multiple",
        "governance_risk",
        "board_pressure",
        "board_directive",
        "active_board_ask",
        "board_warning_active",
        "board_warning_level",
        "last_board_review_turn",
    }.issubset(finance_columns)
    assert {
        "performance_rating",
        "tenure_turns",
        "underperformance_streak",
        "leadership_score",
        "manager_id",
    }.issubset(employee_columns)
    assert {
        "billing_model",
        "seat_count",
        "usage_units",
        "plan_tier",
        "subscription_package",
        "add_on_count",
        "annual_prepay",
        "open_tickets",
        "sla_breach_risk",
        "invoice_risk",
        "failed_payment_risk",
        "dunning_steps",
        "escalation_count",
        "renewal_health",
    }.issubset(customer_columns)
    assert {
        "plan_tier",
        "subscription_package",
        "billing_model",
        "seat_commitment",
        "usage_commitment",
        "add_on_commitment",
        "annual_prepay_offer",
        "proposed_discount_rate",
    }.issubset(sales_columns)
    assert {
        "offer_deadline_turn",
        "market_salary_pressure",
        "negotiation_rounds",
    }.issubset(hiring_columns)
    assert {
        "epic_count",
        "epics_completed",
        "deadline_turn",
        "dependency_project_type",
        "delivery_risk",
    }.issubset(roadmap_columns)
    assert user_version >= 16


def test_schema_initialization_migrates_older_additive_columns(tmp_path: Path) -> None:
    db_path = tmp_path / "old-save.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE save_slots (
                slot_name TEXT PRIMARY KEY,
                action_points_remaining INTEGER NOT NULL,
                rng_seed INTEGER,
                rng_state TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE companies (
                slot_name TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                name TEXT NOT NULL,
                cash_on_hand TEXT NOT NULL,
                reputation INTEGER NOT NULL,
                current_turn INTEGER NOT NULL,
                game_over INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE products (
                slot_name TEXT NOT NULL,
                product_id TEXT NOT NULL,
                display_order INTEGER NOT NULL,
                name TEXT NOT NULL,
                lifecycle_stage TEXT NOT NULL,
                quality INTEGER NOT NULL,
                bug_level INTEGER NOT NULL,
                market_fit INTEGER NOT NULL,
                technical_debt INTEGER NOT NULL,
                user_count INTEGER NOT NULL,
                revenue_per_user TEXT NOT NULL,
                feature_count INTEGER NOT NULL,
                maintenance_cost TEXT NOT NULL,
                acquisition_rate TEXT NOT NULL,
                churn_rate TEXT NOT NULL,
                is_active INTEGER NOT NULL,
                PRIMARY KEY (slot_name, product_id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE competitors (
                slot_name TEXT NOT NULL,
                competitor_id TEXT NOT NULL,
                display_order INTEGER NOT NULL,
                name TEXT NOT NULL,
                focus_segment TEXT NOT NULL,
                strength INTEGER NOT NULL,
                aggression INTEGER NOT NULL,
                pricing_tier TEXT NOT NULL,
                active_product_count INTEGER NOT NULL,
                PRIMARY KEY (slot_name, competitor_id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE finance_state (
                slot_name TEXT PRIMARY KEY,
                debt_principal TEXT NOT NULL,
                loan_interest_rate TEXT NOT NULL,
                equity_dilution TEXT NOT NULL,
                investor_pressure INTEGER NOT NULL,
                total_raised TEXT NOT NULL,
                last_funding_turn INTEGER
            )
            """
        )
        connection.execute("PRAGMA user_version = 5")

    DatabaseManager(db_path).initialize()

    with sqlite3.connect(db_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        save_slot_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(save_slots)").fetchall()
        }
        company_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(companies)").fetchall()
        }
        product_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(products)").fetchall()
        }
        competitor_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(competitors)").fetchall()
        }
        finance_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(finance_state)").fetchall()
        }
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert "hiring_candidates" in table_names
    assert {
        "scenario_id",
        "difficulty_mode",
        "exit_summary",
        "saved_with_version",
        "schema_version",
        "functional_budget_preset",
        "budget_engineering_share",
        "support_knowledge_base_level",
        "support_sla_target",
    }.issubset(save_slot_columns)
    assert {"strategy"}.issubset(company_columns)
    assert {"pricing_tier", "target_segment", "packaging_strategy"}.issubset(product_columns)
    assert {"archetype_id", "current_move", "momentum", "funding_level"}.issubset(
        competitor_columns
    )
    assert {
        "board_confidence",
        "covenant_risk",
        "missed_board_targets",
        "forecast_net_cash_flow",
        "burn_multiple",
        "board_pressure",
        "board_directive",
        "active_board_ask",
        "board_warning_level",
    }.issubset(finance_columns)
    assert user_version >= 16


def test_save_then_load_round_trip_preserves_full_state_and_rng(tmp_path: Path) -> None:
    db_path = tmp_path / "round-trip.db"
    coordinator = SaveLoadCoordinator(db_path)
    state = make_state()
    rng = RandomSource(seed=17)
    rng.randint(1, 100)

    coordinator.save_game(DEFAULT_SAVE_SLOT, state, rng)
    expected_next_roll = rng.randint(1, 100)

    loaded = coordinator.load_game(DEFAULT_SAVE_SLOT)

    assert loaded.slot_name == DEFAULT_SAVE_SLOT
    assert loaded.state.model_dump() == state.model_dump()
    assert loaded.rng.randint(1, 100) == expected_next_roll


def test_list_save_slots_returns_compact_metadata(tmp_path: Path) -> None:
    db_path = tmp_path / "slots.db"
    coordinator = SaveLoadCoordinator(db_path)

    coordinator.save_game("slot-a", make_state(), RandomSource(seed=11))
    state_b = make_state()
    state_b.company.name = "Atlas Systems"
    state_b.company.current_turn = 6
    coordinator.save_game("slot-b", state_b, RandomSource(seed=17))

    summaries = coordinator.list_save_slots()

    assert len(summaries) == 2
    assert summaries[0].slot_name == "slot-b"
    assert summaries[0].company_name == "Atlas Systems"
    assert summaries[0].active_products == 1
    assert summaries[0].headcount == 2
    assert summaries[0].saved_with_version
    assert summaries[0].schema_version >= 16


def test_check_save_health_reports_healthy_database(tmp_path: Path) -> None:
    db_path = tmp_path / "health.db"
    coordinator = SaveLoadCoordinator(db_path)
    coordinator.save_game("active", make_state(), RandomSource(seed=31))

    report = coordinator.check_save_health()

    assert report.integrity_ok is True
    assert report.foreign_key_ok is True
    assert report.slot_count == 1
    assert report.schema_version >= 16


def test_rename_save_moves_state_to_new_slot(tmp_path: Path) -> None:
    db_path = tmp_path / "rename.db"
    coordinator = SaveLoadCoordinator(db_path)
    state = make_state()

    coordinator.save_game("active", state, RandomSource(seed=13))
    coordinator.rename_save("active", "archive")

    loaded = coordinator.load_game("archive")

    assert loaded.slot_name == "archive"
    assert loaded.state.company.name == state.company.name
    with pytest.raises(SaveNotFoundError, match="active"):
        coordinator.load_game("active")


def test_delete_save_removes_slot(tmp_path: Path) -> None:
    db_path = tmp_path / "delete.db"
    coordinator = SaveLoadCoordinator(db_path)
    coordinator.save_game("active", make_state(), RandomSource(seed=19))

    coordinator.delete_save("active")

    with pytest.raises(SaveNotFoundError, match="active"):
        coordinator.load_game("active")


def test_foreign_key_integrity_rejects_assignment_to_unknown_product(tmp_path: Path) -> None:
    db_path = tmp_path / "integrity.db"
    manager = DatabaseManager(db_path)
    manager.initialize()

    with manager.connect() as connection:
        connection.execute(
            """
            INSERT INTO save_slots (
                slot_name, action_points_remaining, rng_seed, rng_state, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("active", 2, 7, "state", "2026-04-11T00:00:00+00:00", "2026-04-11T00:00:00+00:00"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO employees (
                    slot_name,
                    employee_id,
                    display_order,
                    full_name,
                    role,
                    seniority,
                    salary,
                    energy,
                    morale,
                    productivity,
                    specialization,
                    assigned_product_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "active",
                    "employee-1",
                    0,
                    "Broken Link",
                    "engineer",
                    "mid",
                    "720.00",
                    80,
                    80,
                    65,
                    "platform",
                    "missing-product",
                ),
            )


def test_load_missing_database_raises_clear_error(tmp_path: Path) -> None:
    coordinator = SaveLoadCoordinator(tmp_path / "missing.db")

    with pytest.raises(SaveNotFoundError, match="No save database"):
        coordinator.load_game(DEFAULT_SAVE_SLOT)


def test_load_missing_quarter_plan_raises_clear_error(tmp_path: Path) -> None:
    db_path = tmp_path / "missing-quarter-plan.db"
    manager = DatabaseManager(db_path)
    manager.initialize()

    with manager.connect() as connection:
        connection.execute(
            """
            INSERT INTO save_slots (
                slot_name, action_points_remaining, rng_seed, rng_state, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "active",
                2,
                7,
                RandomSource(seed=7).export_state(),
                "2026-04-11T00:00:00+00:00",
                "2026-04-11T00:00:00+00:00",
            ),
        )
        connection.execute(
            """
            INSERT INTO companies (
                slot_name,
                company_id,
                name,
                cash_on_hand,
                reputation,
                strategy,
                current_turn,
                game_over
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "active",
                "00000000-0000-0000-0000-000000000010",
                "Demo",
                "1000.00",
                50,
                CompanyStrategy.BALANCED.value,
                1,
                0,
            ),
        )
        connection.execute(
            """
            INSERT INTO products (
                slot_name,
                product_id,
                display_order,
                name,
                lifecycle_stage,
                quality,
                bug_level,
                market_fit,
                technical_debt,
                user_count,
                revenue_per_user,
                feature_count,
                maintenance_cost,
                acquisition_rate,
                churn_rate,
                pricing_tier,
                target_segment,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "active",
                "00000000-0000-0000-0000-000000000011",
                0,
                "P1",
                "growth",
                50,
                10,
                50,
                10,
                10,
                "10.00",
                1,
                "10.00",
                "0.0500",
                "0.0500",
                PricingTier.STANDARD.value,
                MarketSegment.STARTUP.value,
                1,
            ),
        )

    with pytest.raises(CorruptSaveError, match="missing quarter plan state"):
        SaveLoadCoordinator(db_path).load_game(DEFAULT_SAVE_SLOT)


def test_partial_state_handling_raises_corrupt_save_error(tmp_path: Path) -> None:
    db_path = tmp_path / "partial.db"
    manager = DatabaseManager(db_path)
    manager.initialize()

    with manager.connect() as connection:
        connection.execute(
            """
            INSERT INTO save_slots (
                slot_name, action_points_remaining, rng_seed, rng_state, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "active",
                2,
                7,
                RandomSource(seed=7).export_state(),
                "2026-04-11T00:00:00+00:00",
                "2026-04-11T00:00:00+00:00",
            ),
        )

    coordinator = SaveLoadCoordinator(db_path)
    with pytest.raises(CorruptSaveError, match="missing company state"):
        coordinator.load_game(DEFAULT_SAVE_SLOT)


def test_invalid_rng_state_raises_corrupt_save_error(tmp_path: Path) -> None:
    db_path = tmp_path / "bad-rng.db"
    manager = DatabaseManager(db_path)
    manager.initialize()

    with manager.connect() as connection:
        connection.execute(
            """
            INSERT INTO save_slots (
                slot_name, action_points_remaining, rng_seed, rng_state, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "active",
                2,
                7,
                "aW52YWxpZA==",
                "2026-04-11T00:00:00+00:00",
                "2026-04-11T00:00:00+00:00",
            ),
        )
        connection.execute(
            """
            INSERT INTO companies (
                slot_name,
                company_id,
                name,
                cash_on_hand,
                reputation,
                strategy,
                current_turn,
                game_over
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "active",
                "00000000-0000-0000-0000-000000000001",
                "Demo",
                "100.00",
                50,
                CompanyStrategy.BALANCED.value,
                1,
                0,
            ),
        )
        connection.execute(
            """
            INSERT INTO products (
                slot_name,
                product_id,
                display_order,
                name,
                lifecycle_stage,
                quality,
                bug_level,
                market_fit,
                technical_debt,
                user_count,
                revenue_per_user,
                feature_count,
                maintenance_cost,
                acquisition_rate,
                churn_rate,
                pricing_tier,
                target_segment,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "active",
                "00000000-0000-0000-0000-000000000002",
                0,
                "P1",
                "growth",
                50,
                10,
                50,
                10,
                10,
                "10.00",
                1,
                "10.00",
                "0.0500",
                "0.0500",
                PricingTier.STANDARD.value,
                MarketSegment.STARTUP.value,
                1,
            ),
        )
        connection.execute(
            """
            INSERT INTO quarter_plan (
                slot_name,
                budget_stance,
                set_turn,
                target_turn,
                revenue_target,
                user_target,
                cash_reserve_target,
                headcount_cap
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "active",
                BudgetStance.BALANCED.value,
                1,
                4,
                "100.00",
                10,
                "100.00",
                2,
            ),
        )

    with pytest.raises(CorruptSaveError, match="invalid structured data"):
        SaveLoadCoordinator(db_path).load_game(DEFAULT_SAVE_SLOT)
