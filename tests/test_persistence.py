from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest

from nexus_tech.domain.models import (
    BudgetStance,
    CampaignGoalId,
    Company,
    CompanyStrategy,
    Competitor,
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
    FundingHistoryEntry,
    FundingType,
    GameState,
    LifecycleStage,
    MarketCycle,
    MarketSegment,
    MilestoneEntry,
    MilestoneId,
    PendingEvent,
    PricingTier,
    Product,
    QuarterPlan,
    RoadmapFocus,
    Seniority,
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
        target_segment=MarketSegment.ENTERPRISE,
        is_active=True,
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
        assigned_product_id=product.id,
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
            headcount=1,
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
        satisfaction=72,
        expansion_potential=66,
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
        total_raised=Decimal("7400.00"),
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
    return GameState(
        company=Company(
            name="NEXUS TECH",
            cash_on_hand=Decimal("7630.50"),
            reputation=57,
            strategy=CompanyStrategy.QUALITY,
            current_turn=4,
        ),
        products=[product],
        employees=[employee],
        finance=finance,
        competitors=[competitor],
        customer_accounts=[customer_account],
        quarter_plan=quarter_plan,
        difficulty_mode=DifficultyMode.FOUNDER,
        campaign_goal_id=CampaignGoalId.CATEGORY_LEADER,
        pending_event=pending_event,
        event_history=event_history,
        milestone_history=milestone_history,
        funding_history=funding_history,
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
    }.issubset(table_names)

    with sqlite3.connect(db_path) as connection:
        save_slot_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(save_slots)").fetchall()
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

    assert {
        "scenario_id",
        "scenario_title",
        "difficulty_mode",
        "campaign_goal_id",
        "roadmap_focus",
        "roadmap_set_turn",
        "market_cycle",
        "market_cycle_turns_remaining",
        "victory_achieved",
        "victory_reason",
        "exit_outcome",
        "exit_summary",
        "saved_with_version",
        "schema_version",
    }.issubset(save_slot_columns)
    assert {"target_segment"}.issubset(product_columns)
    assert {"archetype_id", "current_move", "momentum", "funding_level"}.issubset(
        competitor_columns
    )
    assert {"board_confidence"}.issubset(finance_columns)
    assert user_version >= 10


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

    assert {
        "scenario_id",
        "difficulty_mode",
        "exit_summary",
        "saved_with_version",
        "schema_version",
    }.issubset(save_slot_columns)
    assert {"strategy"}.issubset(company_columns)
    assert {"pricing_tier", "target_segment"}.issubset(product_columns)
    assert {"archetype_id", "current_move", "momentum", "funding_level"}.issubset(
        competitor_columns
    )
    assert {"board_confidence"}.issubset(finance_columns)
    assert user_version >= 10


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
    assert summaries[0].headcount == 1
    assert summaries[0].saved_with_version
    assert summaries[0].schema_version >= 10


def test_check_save_health_reports_healthy_database(tmp_path: Path) -> None:
    db_path = tmp_path / "health.db"
    coordinator = SaveLoadCoordinator(db_path)
    coordinator.save_game("active", make_state(), RandomSource(seed=31))

    report = coordinator.check_save_health()

    assert report.integrity_ok is True
    assert report.foreign_key_ok is True
    assert report.slot_count == 1
    assert report.schema_version >= 10


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
