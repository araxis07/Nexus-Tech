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
        scenario_id TEXT NOT NULL DEFAULT 'founder_journey',
        scenario_title TEXT NOT NULL DEFAULT 'Founder Journey',
        roadmap_focus TEXT NOT NULL DEFAULT 'balanced_execution',
        roadmap_set_turn INTEGER NOT NULL DEFAULT 1,
        victory_achieved INTEGER NOT NULL DEFAULT 0,
        victory_reason TEXT,
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
        strategy TEXT NOT NULL DEFAULT 'balanced',
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
        pricing_tier TEXT NOT NULL DEFAULT 'standard',
        target_segment TEXT NOT NULL DEFAULT 'startup',
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
    """
    CREATE TABLE IF NOT EXISTS milestone_history (
        slot_name TEXT NOT NULL
            REFERENCES save_slots(slot_name) ON DELETE CASCADE,
        entry_index INTEGER NOT NULL,
        milestone_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        unlocked_turn INTEGER NOT NULL,
        reward_text TEXT NOT NULL,
        PRIMARY KEY (slot_name, entry_index)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS turn_history (
        slot_name TEXT NOT NULL
            REFERENCES save_slots(slot_name) ON DELETE CASCADE,
        entry_index INTEGER NOT NULL,
        turn INTEGER NOT NULL,
        total_revenue TEXT NOT NULL,
        total_operating_cost TEXT NOT NULL,
        net_cash_flow TEXT NOT NULL,
        cash_on_hand TEXT NOT NULL,
        reputation INTEGER NOT NULL,
        total_users INTEGER NOT NULL,
        headcount INTEGER NOT NULL,
        roadmap_focus TEXT NOT NULL,
        PRIMARY KEY (slot_name, entry_index)
    )
    """,
)


def initialize_schema(connection: sqlite3.Connection) -> None:
    """Create all tables required for local save files."""

    connection.execute("PRAGMA foreign_keys = ON")
    for statement in SCHEMA_STATEMENTS:
        connection.execute(statement)
    _ensure_column(
        connection,
        table_name="companies",
        column_name="strategy",
        column_definition="TEXT NOT NULL DEFAULT 'balanced'",
    )
    _ensure_column(
        connection,
        table_name="products",
        column_name="pricing_tier",
        column_definition="TEXT NOT NULL DEFAULT 'standard'",
    )
    _ensure_column(
        connection,
        table_name="products",
        column_name="target_segment",
        column_definition="TEXT NOT NULL DEFAULT 'startup'",
    )
    _ensure_column(
        connection,
        table_name="save_slots",
        column_name="scenario_id",
        column_definition="TEXT NOT NULL DEFAULT 'founder_journey'",
    )
    _ensure_column(
        connection,
        table_name="save_slots",
        column_name="scenario_title",
        column_definition="TEXT NOT NULL DEFAULT 'Founder Journey'",
    )
    _ensure_column(
        connection,
        table_name="save_slots",
        column_name="roadmap_focus",
        column_definition="TEXT NOT NULL DEFAULT 'balanced_execution'",
    )
    _ensure_column(
        connection,
        table_name="save_slots",
        column_name="roadmap_set_turn",
        column_definition="INTEGER NOT NULL DEFAULT 1",
    )
    _ensure_column(
        connection,
        table_name="save_slots",
        column_name="victory_achieved",
        column_definition="INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        table_name="save_slots",
        column_name="victory_reason",
        column_definition="TEXT",
    )
    connection.execute("PRAGMA user_version = 4")


def _ensure_column(
    connection: sqlite3.Connection,
    *,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()}
    if column_name in columns:
        return

    connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
