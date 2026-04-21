"""High-level save/load orchestration for local SQLite persistence."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from nexus_tech import __version__
from nexus_tech.domain.models import (
    CampaignGoalId,
    DifficultyMode,
    EventCategory,
    EventHistoryEntry,
    EventOption,
    ExitOutcome,
    FinanceState,
    GameState,
    MarketCycle,
    MilestoneEntry,
    MilestoneId,
    PendingEvent,
    RoadmapFocus,
    TurnLedgerEntry,
)
from nexus_tech.persistence.company_repository import CompanyRepository
from nexus_tech.persistence.competitor_repository import CompetitorRepository
from nexus_tech.persistence.customer_repository import CustomerAccountRepository
from nexus_tech.persistence.database import DatabaseManager
from nexus_tech.persistence.employee_repository import EmployeeRepository
from nexus_tech.persistence.errors import CorruptSaveError, PersistenceError, SaveNotFoundError
from nexus_tech.persistence.finance_repository import FinanceRepository
from nexus_tech.persistence.product_repository import ProductRepository
from nexus_tech.persistence.quarter_plan_repository import QuarterPlanRepository
from nexus_tech.persistence.schema import CURRENT_SCHEMA_VERSION
from nexus_tech.simulation.randomness import RandomSource

try:
    UTC = datetime.UTC
except AttributeError:  # pragma: no cover - fallback for local verification on Python < 3.11
    UTC = timezone.utc

DEFAULT_SAVE_SLOT = "active"


@dataclass(frozen=True)
class LoadedGame:
    """A fully reconstructed local game session."""

    slot_name: str
    state: GameState
    rng: RandomSource


@dataclass(frozen=True)
class SaveSlotSummary:
    """Compact metadata used for save-slot listing and management."""

    slot_name: str
    company_name: str
    scenario_title: str
    current_turn: int
    cash_on_hand: Decimal
    reputation: int
    active_products: int
    headcount: int
    updated_at: str
    victory_achieved: bool
    game_over: bool
    saved_with_version: str
    schema_version: int


@dataclass(frozen=True)
class SaveHealthReport:
    """Compact save-database health summary used by CLI diagnostics."""

    integrity_ok: bool
    foreign_key_ok: bool
    slot_count: int
    schema_version: int
    message: str


class SaveLoadCoordinator:
    """Coordinate repositories and schema initialization for save/load."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.database = DatabaseManager(db_path)
        self.company_repository = CompanyRepository()
        self.product_repository = ProductRepository()
        self.employee_repository = EmployeeRepository()
        self.competitor_repository = CompetitorRepository()
        self.customer_repository = CustomerAccountRepository()
        self.finance_repository = FinanceRepository()
        self.quarter_plan_repository = QuarterPlanRepository()

    def initialize(self) -> None:
        """Create the database and schema if needed."""

        self.database.initialize()

    def save_game(self, slot_name: str, state: GameState, rng: RandomSource) -> None:
        """Persist a full game session into one save slot."""

        try:
            self.initialize()
            timestamp = utc_now()
            with self.database.connect() as connection:
                self._upsert_slot_row(
                    connection,
                    slot_name=slot_name,
                    action_points_remaining=state.action_points_remaining,
                    rng_seed=rng.seed,
                    rng_state=rng.export_state(),
                    scenario_id=state.scenario_id,
                    scenario_title=state.scenario_title,
                    difficulty_mode=state.difficulty_mode,
                    campaign_goal_id=state.campaign_goal_id,
                    roadmap_focus=state.roadmap_focus,
                    roadmap_set_turn=state.roadmap_set_turn,
                    market_cycle=state.market_cycle,
                    market_cycle_turns_remaining=state.market_cycle_turns_remaining,
                    victory_achieved=state.victory_achieved,
                    victory_reason=state.victory_reason,
                    exit_outcome=state.exit_outcome,
                    exit_summary=state.exit_summary,
                    saved_with_version=__version__,
                    schema_version=CURRENT_SCHEMA_VERSION,
                    timestamp=timestamp,
                )
                self.company_repository.save(connection, slot_name, state.company)
                self.product_repository.save_all(connection, slot_name, state.products)
                self.employee_repository.save_all(connection, slot_name, state.employees)
                self.competitor_repository.save_all(connection, slot_name, state.competitors)
                self.customer_repository.save_all(
                    connection,
                    slot_name,
                    state.customer_accounts,
                )
                self.finance_repository.save(connection, slot_name, state.finance)
                self.finance_repository.save_history(connection, slot_name, state.funding_history)
                self.quarter_plan_repository.save(connection, slot_name, state.quarter_plan)
                self._save_pending_event(connection, slot_name, state.pending_event)
                self._save_event_history(connection, slot_name, state.event_history)
                self._save_milestone_history(connection, slot_name, state.milestone_history)
                self._save_turn_history(connection, slot_name, state.turn_history)
        except sqlite3.DatabaseError as error:
            raise PersistenceError(f"Failed to save game: {error}") from error

    def load_game(self, slot_name: str) -> LoadedGame:
        """Load a full game session from one save slot."""

        if not self.database.exists():
            raise SaveNotFoundError("No save database was found yet.")

        try:
            self.initialize()
            with self.database.connect() as connection:
                slot_row = connection.execute(
                    """
                    SELECT
                        action_points_remaining,
                        rng_seed,
                        rng_state,
                        scenario_id,
                        scenario_title,
                        difficulty_mode,
                        campaign_goal_id,
                        roadmap_focus,
                        roadmap_set_turn,
                        market_cycle,
                        market_cycle_turns_remaining,
                        victory_achieved,
                        victory_reason,
                        exit_outcome,
                        exit_summary
                    FROM save_slots
                    WHERE slot_name = ?
                    """,
                    (slot_name,),
                ).fetchone()
                if slot_row is None:
                    raise SaveNotFoundError(f"Save slot '{slot_name}' was not found.")

                try:
                    company = self.company_repository.load(connection, slot_name)
                    if company is None:
                        raise CorruptSaveError("Save slot is missing company state.")

                    products = self.product_repository.load_all(connection, slot_name)
                    if not products:
                        raise CorruptSaveError("Save slot is missing product state.")

                    employees = self.employee_repository.load_all(connection, slot_name)
                    competitors = self.competitor_repository.load_all(connection, slot_name)
                    customer_accounts = self.customer_repository.load_all(connection, slot_name)
                    finance = self.finance_repository.load(connection, slot_name) or FinanceState()
                    funding_history = self.finance_repository.load_history(connection, slot_name)
                    quarter_plan = self.quarter_plan_repository.load(connection, slot_name)
                    if quarter_plan is None:
                        raise CorruptSaveError("Save slot is missing quarter plan state.")
                    pending_event = self._load_pending_event(connection, slot_name)
                    event_history = self._load_event_history(connection, slot_name)
                    milestone_history = self._load_milestone_history(connection, slot_name)
                    turn_history = self._load_turn_history(connection, slot_name)
                    rng = RandomSource.from_state(
                        seed=slot_row["rng_seed"],
                        exported_state=slot_row["rng_state"],
                    )
                except CorruptSaveError:
                    raise
                except (ValueError, TypeError, AttributeError) as error:
                    raise CorruptSaveError(
                        "Saved state contains invalid structured data."
                    ) from error

                try:
                    state = GameState(
                        company=company,
                        products=products,
                        employees=employees,
                        finance=finance,
                        competitors=competitors,
                        customer_accounts=customer_accounts,
                        quarter_plan=quarter_plan,
                        pending_event=pending_event,
                        event_history=event_history,
                        milestone_history=milestone_history,
                        funding_history=funding_history,
                        roadmap_focus=RoadmapFocus(slot_row["roadmap_focus"]),
                        roadmap_set_turn=slot_row["roadmap_set_turn"],
                        market_cycle=MarketCycle(slot_row["market_cycle"]),
                        market_cycle_turns_remaining=slot_row["market_cycle_turns_remaining"],
                        turn_history=turn_history,
                        victory_achieved=bool(slot_row["victory_achieved"]),
                        victory_reason=slot_row["victory_reason"],
                        exit_outcome=(
                            ExitOutcome(slot_row["exit_outcome"])
                            if slot_row["exit_outcome"]
                            else None
                        ),
                        exit_summary=slot_row["exit_summary"],
                        scenario_id=slot_row["scenario_id"],
                        scenario_title=slot_row["scenario_title"],
                        difficulty_mode=DifficultyMode(slot_row["difficulty_mode"]),
                        campaign_goal_id=CampaignGoalId(slot_row["campaign_goal_id"]),
                        action_points_remaining=slot_row["action_points_remaining"],
                    )
                except (ValueError, TypeError) as error:
                    raise CorruptSaveError("Saved state could not be reconstructed.") from error
                return LoadedGame(slot_name=slot_name, state=state, rng=rng)
        except sqlite3.DatabaseError as error:
            if isinstance(error, PersistenceError):
                raise
            raise PersistenceError(f"Failed to load game: {error}") from error

    def continue_last_game(self) -> LoadedGame:
        """Load the most recently updated save slot."""

        if not self.database.exists():
            raise SaveNotFoundError("No save database was found yet.")

        try:
            with self.database.connect() as connection:
                row = connection.execute(
                    """
                    SELECT slot_name
                    FROM save_slots
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """
                ).fetchone()
                if row is None:
                    raise SaveNotFoundError("No save slots were found.")
        except sqlite3.DatabaseError as error:
            raise PersistenceError(f"Failed to inspect save slots: {error}") from error

        return self.load_game(row["slot_name"])

    def list_save_slots(self) -> list[SaveSlotSummary]:
        """Return all available save slots ordered by last update time."""

        if not self.database.exists():
            return []

        try:
            self.initialize()
            with self.database.connect() as connection:
                rows = connection.execute(
                    """
                    SELECT
                        slots.slot_name,
                        slots.scenario_title,
                        slots.updated_at,
                        slots.victory_achieved,
                        slots.saved_with_version,
                        slots.schema_version,
                        companies.name AS company_name,
                        companies.current_turn,
                        companies.cash_on_hand,
                        companies.reputation,
                        companies.game_over,
                        COALESCE((
                            SELECT COUNT(*)
                            FROM products
                            WHERE slot_name = slots.slot_name
                            AND is_active = 1
                        ), 0) AS active_products,
                        COALESCE((
                            SELECT COUNT(*)
                            FROM employees
                            WHERE slot_name = slots.slot_name
                        ), 0) AS headcount
                    FROM save_slots AS slots
                    LEFT JOIN companies ON companies.slot_name = slots.slot_name
                    ORDER BY slots.updated_at DESC
                    """
                ).fetchall()
        except sqlite3.DatabaseError as error:
            raise PersistenceError(f"Failed to inspect save slots: {error}") from error

        return [
            SaveSlotSummary(
                slot_name=row["slot_name"],
                company_name=row["company_name"] or "(missing company)",
                scenario_title=row["scenario_title"],
                current_turn=row["current_turn"] or 0,
                cash_on_hand=Decimal(row["cash_on_hand"] or "0.00"),
                reputation=row["reputation"] or 0,
                active_products=row["active_products"],
                headcount=row["headcount"],
                updated_at=row["updated_at"],
                victory_achieved=bool(row["victory_achieved"]),
                game_over=bool(row["game_over"]) if row["game_over"] is not None else False,
                saved_with_version=row["saved_with_version"] or "unknown",
                schema_version=row["schema_version"] or 0,
            )
            for row in rows
        ]

    def check_save_health(self) -> SaveHealthReport:
        """Run lightweight integrity checks against the local save database."""

        if not self.database.exists():
            raise SaveNotFoundError("No save database was found yet.")

        try:
            self.initialize()
            with self.database.connect() as connection:
                integrity_rows = connection.execute("PRAGMA integrity_check").fetchall()
                foreign_key_rows = connection.execute("PRAGMA foreign_key_check").fetchall()
                slot_count = connection.execute(
                    "SELECT COUNT(*) FROM save_slots"
                ).fetchone()[0]
                schema_version = connection.execute("PRAGMA user_version").fetchone()[0]
        except sqlite3.DatabaseError as error:
            raise PersistenceError(f"Failed to inspect save health: {error}") from error

        integrity_ok = all(row[0] == "ok" for row in integrity_rows)
        foreign_key_ok = len(foreign_key_rows) == 0
        if integrity_ok and foreign_key_ok:
            message = "SQLite integrity and foreign keys are healthy."
        elif not integrity_ok and not foreign_key_ok:
            message = "Integrity check and foreign key validation both failed."
        elif not integrity_ok:
            message = "Integrity check failed. The database file may be damaged."
        else:
            message = "Foreign key validation failed. Some saved rows are inconsistent."

        return SaveHealthReport(
            integrity_ok=integrity_ok,
            foreign_key_ok=foreign_key_ok,
            slot_count=slot_count,
            schema_version=schema_version,
            message=message,
        )

    def delete_save(self, slot_name: str) -> None:
        """Delete one save slot and all related rows."""

        if not self.database.exists():
            raise SaveNotFoundError("No save database was found yet.")

        try:
            self.initialize()
            with self.database.connect() as connection:
                cursor = connection.execute(
                    "DELETE FROM save_slots WHERE slot_name = ?",
                    (slot_name,),
                )
                if cursor.rowcount == 0:
                    raise SaveNotFoundError(f"Save slot '{slot_name}' was not found.")
        except sqlite3.DatabaseError as error:
            if isinstance(error, PersistenceError):
                raise
            raise PersistenceError(f"Failed to delete save slot: {error}") from error

    def rename_save(self, from_slot_name: str, to_slot_name: str) -> None:
        """Rename one save slot by copying its state and removing the old slot."""

        source_name = from_slot_name.strip()
        target_name = to_slot_name.strip()
        if not source_name or not target_name:
            raise PersistenceError("Save slot names must not be empty.")
        if source_name == target_name:
            raise PersistenceError("Source and target save slot names must be different.")

        if not self.database.exists():
            raise SaveNotFoundError("No save database was found yet.")

        try:
            self.initialize()
            with self.database.connect() as connection:
                if not self._slot_exists(connection, source_name):
                    raise SaveNotFoundError(f"Save slot '{source_name}' was not found.")
                if self._slot_exists(connection, target_name):
                    raise PersistenceError(f"Save slot '{target_name}' already exists.")
        except sqlite3.DatabaseError as error:
            if isinstance(error, PersistenceError):
                raise
            raise PersistenceError(f"Failed to inspect save slots: {error}") from error

        loaded = self.load_game(source_name)
        self.save_game(target_name, loaded.state, loaded.rng)
        self.delete_save(source_name)

    def _upsert_slot_row(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
        action_points_remaining: int,
        rng_seed: int | None,
        rng_state: str,
        scenario_id: str,
        scenario_title: str,
        difficulty_mode: DifficultyMode,
        campaign_goal_id: CampaignGoalId,
        roadmap_focus: RoadmapFocus,
        roadmap_set_turn: int,
        market_cycle: MarketCycle,
        market_cycle_turns_remaining: int,
        victory_achieved: bool,
        victory_reason: str | None,
        exit_outcome: ExitOutcome | None,
        exit_summary: str | None,
        saved_with_version: str,
        schema_version: int,
        timestamp: str,
    ) -> None:
        existing = connection.execute(
            "SELECT created_at FROM save_slots WHERE slot_name = ?",
            (slot_name,),
        ).fetchone()
        if existing is None:
            connection.execute(
                """
                INSERT INTO save_slots (
                    slot_name,
                    action_points_remaining,
                    rng_seed,
                    rng_state,
                    scenario_id,
                    scenario_title,
                    difficulty_mode,
                    campaign_goal_id,
                    roadmap_focus,
                    roadmap_set_turn,
                    market_cycle,
                    market_cycle_turns_remaining,
                    victory_achieved,
                    victory_reason,
                    exit_outcome,
                    exit_summary,
                    saved_with_version,
                    schema_version,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    slot_name,
                    action_points_remaining,
                    rng_seed,
                    rng_state,
                    scenario_id,
                    scenario_title,
                    difficulty_mode.value,
                    campaign_goal_id.value,
                    roadmap_focus.value,
                    roadmap_set_turn,
                    market_cycle.value,
                    market_cycle_turns_remaining,
                    int(victory_achieved),
                    victory_reason,
                    exit_outcome.value if exit_outcome is not None else None,
                    exit_summary,
                    saved_with_version,
                    schema_version,
                    timestamp,
                    timestamp,
                ),
            )
            return

        connection.execute(
            """
            UPDATE save_slots
            SET action_points_remaining = ?,
                rng_seed = ?,
                rng_state = ?,
                scenario_id = ?,
                scenario_title = ?,
                difficulty_mode = ?,
                campaign_goal_id = ?,
                roadmap_focus = ?,
                roadmap_set_turn = ?,
                market_cycle = ?,
                market_cycle_turns_remaining = ?,
                victory_achieved = ?,
                victory_reason = ?,
                exit_outcome = ?,
                exit_summary = ?,
                saved_with_version = ?,
                schema_version = ?,
                updated_at = ?
            WHERE slot_name = ?
            """,
            (
                action_points_remaining,
                rng_seed,
                rng_state,
                scenario_id,
                scenario_title,
                difficulty_mode.value,
                campaign_goal_id.value,
                roadmap_focus.value,
                roadmap_set_turn,
                market_cycle.value,
                market_cycle_turns_remaining,
                int(victory_achieved),
                victory_reason,
                exit_outcome.value if exit_outcome is not None else None,
                exit_summary,
                saved_with_version,
                schema_version,
                timestamp,
                slot_name,
            ),
        )

    def _slot_exists(self, connection: sqlite3.Connection, slot_name: str) -> bool:
        row = connection.execute(
            "SELECT 1 FROM save_slots WHERE slot_name = ?",
            (slot_name,),
        ).fetchone()
        return row is not None

    def _save_pending_event(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
        pending_event: PendingEvent | None,
    ) -> None:
        connection.execute(
            "DELETE FROM pending_event_options WHERE slot_name = ?",
            (slot_name,),
        )
        connection.execute(
            "DELETE FROM pending_events WHERE slot_name = ?",
            (slot_name,),
        )
        if pending_event is None:
            return

        connection.execute(
            """
            INSERT INTO pending_events (
                slot_name,
                event_id,
                category,
                title,
                description,
                triggered_turn,
                cooldown_turns,
                target_product_id,
                target_employee_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                slot_name,
                pending_event.event_id,
                pending_event.category.value,
                pending_event.title,
                pending_event.description,
                pending_event.triggered_turn,
                pending_event.cooldown_turns,
                str(pending_event.target_product_id)
                if pending_event.target_product_id is not None
                else None,
                str(pending_event.target_employee_id)
                if pending_event.target_employee_id is not None
                else None,
            ),
        )
        connection.executemany(
            """
            INSERT INTO pending_event_options (
                slot_name,
                option_index,
                option_id,
                label,
                description
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    slot_name,
                    index,
                    option.id,
                    option.label,
                    option.description,
                )
                for index, option in enumerate(pending_event.options)
            ],
        )

    def _save_event_history(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
        event_history: list[EventHistoryEntry],
    ) -> None:
        connection.execute("DELETE FROM event_history WHERE slot_name = ?", (slot_name,))
        connection.executemany(
            """
            INSERT INTO event_history (
                slot_name,
                entry_index,
                event_id,
                category,
                title,
                triggered_turn,
                resolved_turn,
                selected_option_id,
                selected_option_label,
                result_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    slot_name,
                    index,
                    entry.event_id,
                    entry.category.value,
                    entry.title,
                    entry.triggered_turn,
                    entry.resolved_turn,
                    entry.selected_option_id,
                    entry.selected_option_label,
                    entry.result_text,
                )
                for index, entry in enumerate(event_history)
            ],
        )

    def _load_pending_event(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
    ) -> PendingEvent | None:
        row = connection.execute(
            """
            SELECT
                event_id,
                category,
                title,
                description,
                triggered_turn,
                cooldown_turns,
                target_product_id,
                target_employee_id
            FROM pending_events
            WHERE slot_name = ?
            """,
            (slot_name,),
        ).fetchone()
        if row is None:
            return None

        option_rows = connection.execute(
            """
            SELECT option_id, label, description
            FROM pending_event_options
            WHERE slot_name = ?
            ORDER BY option_index ASC
            """,
            (slot_name,),
        ).fetchall()
        if not option_rows:
            raise CorruptSaveError("Pending event is missing its response options.")

        return PendingEvent(
            event_id=row["event_id"],
            category=EventCategory(row["category"]),
            title=row["title"],
            description=row["description"],
            triggered_turn=row["triggered_turn"],
            cooldown_turns=row["cooldown_turns"],
            target_product_id=UUID(row["target_product_id"])
            if row["target_product_id"] is not None
            else None,
            target_employee_id=UUID(row["target_employee_id"])
            if row["target_employee_id"] is not None
            else None,
            options=[
                EventOption(
                    id=option_row["option_id"],
                    label=option_row["label"],
                    description=option_row["description"],
                )
                for option_row in option_rows
            ],
        )

    def _load_event_history(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
    ) -> list[EventHistoryEntry]:
        rows = connection.execute(
            """
            SELECT
                event_id,
                category,
                title,
                triggered_turn,
                resolved_turn,
                selected_option_id,
                selected_option_label,
                result_text
            FROM event_history
            WHERE slot_name = ?
            ORDER BY entry_index ASC
            """,
            (slot_name,),
        ).fetchall()
        return [
            EventHistoryEntry(
                event_id=row["event_id"],
                category=EventCategory(row["category"]),
                title=row["title"],
                triggered_turn=row["triggered_turn"],
                resolved_turn=row["resolved_turn"],
                selected_option_id=row["selected_option_id"],
                selected_option_label=row["selected_option_label"],
                result_text=row["result_text"],
            )
            for row in rows
        ]

    def _save_milestone_history(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
        milestone_history: list[MilestoneEntry],
    ) -> None:
        connection.execute("DELETE FROM milestone_history WHERE slot_name = ?", (slot_name,))
        connection.executemany(
            """
            INSERT INTO milestone_history (
                slot_name,
                entry_index,
                milestone_id,
                title,
                description,
                unlocked_turn,
                reward_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    slot_name,
                    index,
                    entry.milestone_id.value,
                    entry.title,
                    entry.description,
                    entry.unlocked_turn,
                    entry.reward_text,
                )
                for index, entry in enumerate(milestone_history)
            ],
        )

    def _load_milestone_history(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
    ) -> list[MilestoneEntry]:
        rows = connection.execute(
            """
            SELECT milestone_id, title, description, unlocked_turn, reward_text
            FROM milestone_history
            WHERE slot_name = ?
            ORDER BY entry_index ASC
            """,
            (slot_name,),
        ).fetchall()
        return [
            MilestoneEntry(
                milestone_id=MilestoneId(row["milestone_id"]),
                title=row["title"],
                description=row["description"],
                unlocked_turn=row["unlocked_turn"],
                reward_text=row["reward_text"],
            )
            for row in rows
        ]

    def _save_turn_history(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
        turn_history: list[TurnLedgerEntry],
    ) -> None:
        connection.execute("DELETE FROM turn_history WHERE slot_name = ?", (slot_name,))
        connection.executemany(
            """
            INSERT INTO turn_history (
                slot_name,
                entry_index,
                turn,
                total_revenue,
                total_operating_cost,
                net_cash_flow,
                cash_on_hand,
                reputation,
                total_users,
                headcount,
                roadmap_focus
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    slot_name,
                    index,
                    entry.turn,
                    str(entry.total_revenue),
                    str(entry.total_operating_cost),
                    str(entry.net_cash_flow),
                    str(entry.cash_on_hand),
                    entry.reputation,
                    entry.total_users,
                    entry.headcount,
                    entry.roadmap_focus.value,
                )
                for index, entry in enumerate(turn_history)
            ],
        )

    def _load_turn_history(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
    ) -> list[TurnLedgerEntry]:
        rows = connection.execute(
            """
            SELECT
                turn,
                total_revenue,
                total_operating_cost,
                net_cash_flow,
                cash_on_hand,
                reputation,
                total_users,
                headcount,
                roadmap_focus
            FROM turn_history
            WHERE slot_name = ?
            ORDER BY entry_index ASC
            """,
            (slot_name,),
        ).fetchall()
        return [
            TurnLedgerEntry(
                turn=row["turn"],
                total_revenue=row["total_revenue"],
                total_operating_cost=row["total_operating_cost"],
                net_cash_flow=row["net_cash_flow"],
                cash_on_hand=row["cash_on_hand"],
                reputation=row["reputation"],
                total_users=row["total_users"],
                headcount=row["headcount"],
                roadmap_focus=RoadmapFocus(row["roadmap_focus"]),
            )
            for row in rows
        ]


def utc_now() -> str:
    """Return a UTC ISO timestamp for save metadata."""

    return datetime.now(UTC).isoformat()
