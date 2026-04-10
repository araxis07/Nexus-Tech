from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest

from nexus_tech.domain.models import (
    Company,
    Employee,
    EmployeeRole,
    EventCategory,
    EventHistoryEntry,
    EventOption,
    GameState,
    LifecycleStage,
    PendingEvent,
    Product,
    Seniority,
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
    return GameState(
        company=Company(
            name="NEXUS TECH",
            cash_on_hand=Decimal("7630.50"),
            reputation=57,
            current_turn=4,
        ),
        products=[product],
        employees=[employee],
        pending_event=pending_event,
        event_history=event_history,
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
        "pending_events",
        "pending_event_options",
        "event_history",
    }.issubset(table_names)


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
