"""SQLite schema initialization for save files."""

from __future__ import annotations

import sqlite3

SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS save_slots (
        slot_name TEXT PRIMARY KEY,
        action_points_remaining INTEGER NOT NULL,
        rng_seed INTEGER,
        rng_state TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS companies (
        slot_name TEXT PRIMARY KEY
            REFERENCES save_slots(slot_name) ON DELETE CASCADE,
        company_id TEXT NOT NULL,
        name TEXT NOT NULL,
        cash_on_hand TEXT NOT NULL,
        reputation INTEGER NOT NULL,
        current_turn INTEGER NOT NULL,
        game_over INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS products (
        slot_name TEXT NOT NULL
            REFERENCES save_slots(slot_name) ON DELETE CASCADE,
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
        PRIMARY KEY (slot_name, product_id),
        UNIQUE (slot_name, display_order)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS employees (
        slot_name TEXT NOT NULL
            REFERENCES save_slots(slot_name) ON DELETE CASCADE,
        employee_id TEXT NOT NULL,
        display_order INTEGER NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL,
        seniority TEXT NOT NULL,
        salary TEXT NOT NULL,
        energy INTEGER NOT NULL,
        morale INTEGER NOT NULL,
        productivity INTEGER NOT NULL,
        specialization TEXT NOT NULL,
        assigned_product_id TEXT,
        PRIMARY KEY (slot_name, employee_id),
        UNIQUE (slot_name, display_order),
        FOREIGN KEY (slot_name, assigned_product_id)
            REFERENCES products(slot_name, product_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pending_events (
        slot_name TEXT PRIMARY KEY
            REFERENCES save_slots(slot_name) ON DELETE CASCADE,
        event_id TEXT NOT NULL,
        category TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        triggered_turn INTEGER NOT NULL,
        cooldown_turns INTEGER NOT NULL,
        target_product_id TEXT,
        target_employee_id TEXT,
        FOREIGN KEY (slot_name, target_product_id)
            REFERENCES products(slot_name, product_id),
        FOREIGN KEY (slot_name, target_employee_id)
            REFERENCES employees(slot_name, employee_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pending_event_options (
        slot_name TEXT NOT NULL
            REFERENCES pending_events(slot_name) ON DELETE CASCADE,
        option_index INTEGER NOT NULL,
        option_id TEXT NOT NULL,
        label TEXT NOT NULL,
        description TEXT NOT NULL,
        PRIMARY KEY (slot_name, option_index)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS event_history (
        slot_name TEXT NOT NULL
            REFERENCES save_slots(slot_name) ON DELETE CASCADE,
        entry_index INTEGER NOT NULL,
        event_id TEXT NOT NULL,
        category TEXT NOT NULL,
        title TEXT NOT NULL,
        triggered_turn INTEGER NOT NULL,
        resolved_turn INTEGER NOT NULL,
        selected_option_id TEXT NOT NULL,
        selected_option_label TEXT NOT NULL,
        result_text TEXT NOT NULL,
        PRIMARY KEY (slot_name, entry_index)
    )
    """,
)


def initialize_schema(connection: sqlite3.Connection) -> None:
    """Create all tables required for local save files."""

    connection.execute("PRAGMA foreign_keys = ON")
    for statement in SCHEMA_STATEMENTS:
        connection.execute(statement)
    connection.execute("PRAGMA user_version = 1")
