"""SQLite schema initialization for save files."""

from __future__ import annotations

import sqlite3

CURRENT_SCHEMA_VERSION = 13

SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS save_slots (
        slot_name TEXT PRIMARY KEY,
        action_points_remaining INTEGER NOT NULL,
        rng_seed INTEGER,
        rng_state TEXT,
        scenario_id TEXT NOT NULL DEFAULT 'founder_journey',
        scenario_title TEXT NOT NULL DEFAULT 'Founder Journey',
        scenario_objective TEXT NOT NULL DEFAULT '',
        scenario_objective_metric TEXT NOT NULL DEFAULT 'none',
        scenario_objective_target INTEGER NOT NULL DEFAULT 0,
        difficulty_mode TEXT NOT NULL DEFAULT 'standard',
        campaign_goal_id TEXT NOT NULL DEFAULT 'profit_machine',
        roadmap_focus TEXT NOT NULL DEFAULT 'balanced_execution',
        roadmap_set_turn INTEGER NOT NULL DEFAULT 1,
        functional_budget_preset TEXT NOT NULL DEFAULT 'balanced',
        budget_engineering_share INTEGER NOT NULL DEFAULT 30,
        budget_marketing_share INTEGER NOT NULL DEFAULT 25,
        budget_customer_success_share INTEGER NOT NULL DEFAULT 25,
        budget_g_and_a_share INTEGER NOT NULL DEFAULT 20,
        market_cycle TEXT NOT NULL DEFAULT 'steady',
        market_cycle_turns_remaining INTEGER NOT NULL DEFAULT 3,
        victory_achieved INTEGER NOT NULL DEFAULT 0,
        victory_reason TEXT,
        exit_outcome TEXT,
        exit_summary TEXT,
        saved_with_version TEXT NOT NULL DEFAULT 'unknown',
        schema_version INTEGER NOT NULL DEFAULT 12,
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
        trait TEXT NOT NULL DEFAULT 'steady_operator',
        experience_points INTEGER NOT NULL DEFAULT 0,
        promotion_readiness INTEGER NOT NULL DEFAULT 0,
        attrition_risk INTEGER NOT NULL DEFAULT 0,
        performance_rating INTEGER NOT NULL DEFAULT 62,
        tenure_turns INTEGER NOT NULL DEFAULT 0,
        underperformance_streak INTEGER NOT NULL DEFAULT 0,
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
        chain_id TEXT,
        chain_stage INTEGER NOT NULL DEFAULT 0,
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
        chain_id TEXT,
        chain_stage INTEGER NOT NULL DEFAULT 0,
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
    CREATE TABLE IF NOT EXISTS finance_state (
        slot_name TEXT PRIMARY KEY
            REFERENCES save_slots(slot_name) ON DELETE CASCADE,
        debt_principal TEXT NOT NULL,
        loan_interest_rate TEXT NOT NULL,
        equity_dilution TEXT NOT NULL,
        investor_pressure INTEGER NOT NULL,
        board_confidence INTEGER NOT NULL DEFAULT 55,
        total_raised TEXT NOT NULL,
        last_funding_turn INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS funding_history (
        slot_name TEXT NOT NULL
            REFERENCES save_slots(slot_name) ON DELETE CASCADE,
        entry_index INTEGER NOT NULL,
        funding_type TEXT NOT NULL,
        turn INTEGER NOT NULL,
        amount TEXT NOT NULL,
        dilution_added TEXT NOT NULL,
        debt_added TEXT NOT NULL,
        summary TEXT NOT NULL,
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
    """
    CREATE TABLE IF NOT EXISTS quarter_plan (
        slot_name TEXT PRIMARY KEY
            REFERENCES save_slots(slot_name) ON DELETE CASCADE,
        budget_stance TEXT NOT NULL,
        set_turn INTEGER NOT NULL,
        target_turn INTEGER NOT NULL,
        revenue_target TEXT NOT NULL,
        user_target INTEGER NOT NULL,
        cash_reserve_target TEXT NOT NULL,
        headcount_cap INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS competitors (
        slot_name TEXT NOT NULL
            REFERENCES save_slots(slot_name) ON DELETE CASCADE,
        competitor_id TEXT NOT NULL,
        display_order INTEGER NOT NULL,
        name TEXT NOT NULL,
        archetype_id TEXT,
        focus_segment TEXT NOT NULL,
        strength INTEGER NOT NULL,
        aggression INTEGER NOT NULL,
        pricing_tier TEXT NOT NULL,
        active_product_count INTEGER NOT NULL,
        current_move TEXT NOT NULL DEFAULT 'hold',
        momentum INTEGER NOT NULL DEFAULT 50,
        funding_level INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (slot_name, competitor_id),
        UNIQUE (slot_name, display_order)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS customer_accounts (
        slot_name TEXT NOT NULL
            REFERENCES save_slots(slot_name) ON DELETE CASCADE,
        account_id TEXT NOT NULL,
        display_order INTEGER NOT NULL,
        name TEXT NOT NULL,
        product_id TEXT NOT NULL,
        segment TEXT NOT NULL,
        contract_value TEXT NOT NULL,
        contract_cadence TEXT NOT NULL DEFAULT 'annual',
        billing_model TEXT NOT NULL DEFAULT 'flat',
        seat_count INTEGER NOT NULL DEFAULT 0,
        usage_units INTEGER NOT NULL DEFAULT 0,
        discount_rate TEXT NOT NULL DEFAULT '0.0000',
        satisfaction INTEGER NOT NULL,
        onboarding_health INTEGER NOT NULL DEFAULT 60,
        support_load INTEGER NOT NULL DEFAULT 20,
        open_tickets INTEGER NOT NULL DEFAULT 0,
        sla_breach_risk INTEGER NOT NULL DEFAULT 0,
        expansion_potential INTEGER NOT NULL,
        renewal_turn INTEGER NOT NULL,
        churn_risk INTEGER NOT NULL,
        status TEXT NOT NULL,
        PRIMARY KEY (slot_name, account_id),
        UNIQUE (slot_name, display_order),
        FOREIGN KEY (slot_name, product_id)
            REFERENCES products(slot_name, product_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS product_releases (
        slot_name TEXT NOT NULL
            REFERENCES save_slots(slot_name) ON DELETE CASCADE,
        release_id TEXT NOT NULL,
        display_order INTEGER NOT NULL,
        product_id TEXT NOT NULL,
        release_type TEXT NOT NULL,
        status TEXT NOT NULL,
        progress INTEGER NOT NULL,
        required_progress INTEGER NOT NULL,
        risk INTEGER NOT NULL,
        scheduled_turn INTEGER NOT NULL,
        shipped_turn INTEGER,
        summary TEXT NOT NULL,
        PRIMARY KEY (slot_name, release_id),
        UNIQUE (slot_name, display_order),
        FOREIGN KEY (slot_name, product_id)
            REFERENCES products(slot_name, product_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sales_deals (
        slot_name TEXT NOT NULL
            REFERENCES save_slots(slot_name) ON DELETE CASCADE,
        deal_id TEXT NOT NULL,
        display_order INTEGER NOT NULL,
        product_id TEXT NOT NULL,
        name TEXT NOT NULL,
        segment TEXT NOT NULL,
        stage TEXT NOT NULL,
        billing_model TEXT NOT NULL DEFAULT 'flat',
        seat_commitment INTEGER NOT NULL DEFAULT 0,
        usage_commitment INTEGER NOT NULL DEFAULT 0,
        value TEXT NOT NULL,
        probability INTEGER NOT NULL,
        created_turn INTEGER NOT NULL,
        updated_turn INTEGER NOT NULL,
        PRIMARY KEY (slot_name, deal_id),
        UNIQUE (slot_name, display_order),
        FOREIGN KEY (slot_name, product_id)
            REFERENCES products(slot_name, product_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS roadmap_projects (
        slot_name TEXT NOT NULL
            REFERENCES save_slots(slot_name) ON DELETE CASCADE,
        project_id TEXT NOT NULL,
        display_order INTEGER NOT NULL,
        project_type TEXT NOT NULL,
        status TEXT NOT NULL,
        target_product_id TEXT,
        progress INTEGER NOT NULL,
        required_progress INTEGER NOT NULL,
        epic_count INTEGER NOT NULL DEFAULT 3,
        epics_completed INTEGER NOT NULL DEFAULT 0,
        started_turn INTEGER NOT NULL,
        deadline_turn INTEGER NOT NULL DEFAULT 1,
        dependency_project_type TEXT,
        delivery_risk INTEGER NOT NULL DEFAULT 0,
        completed_turn INTEGER,
        summary TEXT NOT NULL,
        PRIMARY KEY (slot_name, project_id),
        UNIQUE (slot_name, display_order),
        FOREIGN KEY (slot_name, target_product_id)
            REFERENCES products(slot_name, product_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS competitor_intel (
        slot_name TEXT NOT NULL
            REFERENCES save_slots(slot_name) ON DELETE CASCADE,
        entry_index INTEGER NOT NULL,
        turn INTEGER NOT NULL,
        competitor_name TEXT NOT NULL,
        move TEXT NOT NULL,
        summary TEXT NOT NULL,
        PRIMARY KEY (slot_name, entry_index)
    )
    """,
)


def initialize_schema(connection: sqlite3.Connection) -> None:
    """Create all tables required for local save files."""

    connection.execute("PRAGMA foreign_keys = ON")
    for statement in SCHEMA_STATEMENTS:
        connection.execute(statement)
    current_version = connection.execute("PRAGMA user_version").fetchone()[0]
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
        column_name="scenario_objective",
        column_definition="TEXT NOT NULL DEFAULT ''",
    )
    _ensure_column(
        connection,
        table_name="save_slots",
        column_name="scenario_objective_metric",
        column_definition="TEXT NOT NULL DEFAULT 'none'",
    )
    _ensure_column(
        connection,
        table_name="save_slots",
        column_name="scenario_objective_target",
        column_definition="INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        table_name="save_slots",
        column_name="difficulty_mode",
        column_definition="TEXT NOT NULL DEFAULT 'standard'",
    )
    _ensure_column(
        connection,
        table_name="save_slots",
        column_name="campaign_goal_id",
        column_definition="TEXT NOT NULL DEFAULT 'profit_machine'",
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
        column_name="functional_budget_preset",
        column_definition="TEXT NOT NULL DEFAULT 'balanced'",
    )
    _ensure_column(
        connection,
        table_name="save_slots",
        column_name="budget_engineering_share",
        column_definition="INTEGER NOT NULL DEFAULT 30",
    )
    _ensure_column(
        connection,
        table_name="save_slots",
        column_name="budget_marketing_share",
        column_definition="INTEGER NOT NULL DEFAULT 25",
    )
    _ensure_column(
        connection,
        table_name="save_slots",
        column_name="budget_customer_success_share",
        column_definition="INTEGER NOT NULL DEFAULT 25",
    )
    _ensure_column(
        connection,
        table_name="save_slots",
        column_name="budget_g_and_a_share",
        column_definition="INTEGER NOT NULL DEFAULT 20",
    )
    _ensure_column(
        connection,
        table_name="save_slots",
        column_name="market_cycle",
        column_definition="TEXT NOT NULL DEFAULT 'steady'",
    )
    _ensure_column(
        connection,
        table_name="save_slots",
        column_name="market_cycle_turns_remaining",
        column_definition="INTEGER NOT NULL DEFAULT 3",
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
    _ensure_column(
        connection,
        table_name="save_slots",
        column_name="exit_outcome",
        column_definition="TEXT",
    )
    _ensure_column(
        connection,
        table_name="save_slots",
        column_name="exit_summary",
        column_definition="TEXT",
    )
    _ensure_column(
        connection,
        table_name="save_slots",
        column_name="saved_with_version",
        column_definition="TEXT NOT NULL DEFAULT 'unknown'",
    )
    _ensure_column(
        connection,
        table_name="save_slots",
        column_name="schema_version",
        column_definition=f"INTEGER NOT NULL DEFAULT {CURRENT_SCHEMA_VERSION}",
    )
    _ensure_column(
        connection,
        table_name="competitors",
        column_name="funding_level",
        column_definition="INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        table_name="finance_state",
        column_name="board_confidence",
        column_definition="INTEGER NOT NULL DEFAULT 55",
    )
    _ensure_column(
        connection,
        table_name="employees",
        column_name="trait",
        column_definition="TEXT NOT NULL DEFAULT 'steady_operator'",
    )
    _ensure_column(
        connection,
        table_name="employees",
        column_name="experience_points",
        column_definition="INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        table_name="employees",
        column_name="promotion_readiness",
        column_definition="INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        table_name="employees",
        column_name="attrition_risk",
        column_definition="INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        table_name="employees",
        column_name="performance_rating",
        column_definition="INTEGER NOT NULL DEFAULT 62",
    )
    _ensure_column(
        connection,
        table_name="employees",
        column_name="tenure_turns",
        column_definition="INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        table_name="employees",
        column_name="underperformance_streak",
        column_definition="INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        table_name="customer_accounts",
        column_name="contract_cadence",
        column_definition="TEXT NOT NULL DEFAULT 'annual'",
    )
    _ensure_column(
        connection,
        table_name="customer_accounts",
        column_name="billing_model",
        column_definition="TEXT NOT NULL DEFAULT 'flat'",
    )
    _ensure_column(
        connection,
        table_name="customer_accounts",
        column_name="seat_count",
        column_definition="INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        table_name="customer_accounts",
        column_name="usage_units",
        column_definition="INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        table_name="customer_accounts",
        column_name="discount_rate",
        column_definition="TEXT NOT NULL DEFAULT '0.0000'",
    )
    _ensure_column(
        connection,
        table_name="customer_accounts",
        column_name="onboarding_health",
        column_definition="INTEGER NOT NULL DEFAULT 60",
    )
    _ensure_column(
        connection,
        table_name="customer_accounts",
        column_name="support_load",
        column_definition="INTEGER NOT NULL DEFAULT 20",
    )
    _ensure_column(
        connection,
        table_name="customer_accounts",
        column_name="open_tickets",
        column_definition="INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        table_name="customer_accounts",
        column_name="sla_breach_risk",
        column_definition="INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        table_name="sales_deals",
        column_name="billing_model",
        column_definition="TEXT NOT NULL DEFAULT 'flat'",
    )
    _ensure_column(
        connection,
        table_name="sales_deals",
        column_name="seat_commitment",
        column_definition="INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        table_name="sales_deals",
        column_name="usage_commitment",
        column_definition="INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        table_name="roadmap_projects",
        column_name="epic_count",
        column_definition="INTEGER NOT NULL DEFAULT 3",
    )
    _ensure_column(
        connection,
        table_name="roadmap_projects",
        column_name="epics_completed",
        column_definition="INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        table_name="roadmap_projects",
        column_name="deadline_turn",
        column_definition="INTEGER NOT NULL DEFAULT 1",
    )
    _ensure_column(
        connection,
        table_name="roadmap_projects",
        column_name="dependency_project_type",
        column_definition="TEXT",
    )
    _ensure_column(
        connection,
        table_name="roadmap_projects",
        column_name="delivery_risk",
        column_definition="INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        table_name="pending_events",
        column_name="chain_id",
        column_definition="TEXT",
    )
    _ensure_column(
        connection,
        table_name="pending_events",
        column_name="chain_stage",
        column_definition="INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        table_name="event_history",
        column_name="chain_id",
        column_definition="TEXT",
    )
    _ensure_column(
        connection,
        table_name="event_history",
        column_name="chain_stage",
        column_definition="INTEGER NOT NULL DEFAULT 0",
    )
    if current_version < 6:
        _apply_version_6_migration(connection)
    connection.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION}")


def _apply_version_6_migration(connection: sqlite3.Connection) -> None:
    """Upgrade older save files with finance and deeper competitor state."""

    _ensure_column(
        connection,
        table_name="competitors",
        column_name="archetype_id",
        column_definition="TEXT",
    )
    _ensure_column(
        connection,
        table_name="competitors",
        column_name="funding_level",
        column_definition="INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        table_name="finance_state",
        column_name="board_confidence",
        column_definition="INTEGER NOT NULL DEFAULT 55",
    )
    _ensure_column(
        connection,
        table_name="competitors",
        column_name="current_move",
        column_definition="TEXT NOT NULL DEFAULT 'hold'",
    )
    _ensure_column(
        connection,
        table_name="competitors",
        column_name="momentum",
        column_definition="INTEGER NOT NULL DEFAULT 50",
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS finance_state (
            slot_name TEXT PRIMARY KEY
                REFERENCES save_slots(slot_name) ON DELETE CASCADE,
            debt_principal TEXT NOT NULL,
            loan_interest_rate TEXT NOT NULL,
            equity_dilution TEXT NOT NULL,
            investor_pressure INTEGER NOT NULL,
            total_raised TEXT NOT NULL,
            last_funding_turn INTEGER
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS funding_history (
            slot_name TEXT NOT NULL
                REFERENCES save_slots(slot_name) ON DELETE CASCADE,
            entry_index INTEGER NOT NULL,
            funding_type TEXT NOT NULL,
            turn INTEGER NOT NULL,
            amount TEXT NOT NULL,
            dilution_added TEXT NOT NULL,
            debt_added TEXT NOT NULL,
            summary TEXT NOT NULL,
            PRIMARY KEY (slot_name, entry_index)
        )
        """
    )


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
