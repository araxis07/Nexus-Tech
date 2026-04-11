"""High-level save/load orchestration for local SQLite persistence."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from nexus_tech.domain.models import (
    EventCategory,
    EventHistoryEntry,
    EventOption,
    GameState,
    MilestoneEntry,
    MilestoneId,
    PendingEvent,
)
from nexus_tech.persistence.company_repository import CompanyRepository
from nexus_tech.persistence.database import DatabaseManager
from nexus_tech.persistence.employee_repository import EmployeeRepository
from nexus_tech.persistence.errors import CorruptSaveError, PersistenceError, SaveNotFoundError
from nexus_tech.persistence.product_repository import ProductRepository
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


class SaveLoadCoordinator:
    """Coordinate repositories and schema initialization for save/load."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.database = DatabaseManager(db_path)
        self.company_repository = CompanyRepository()
        self.product_repository = ProductRepository()
        self.employee_repository = EmployeeRepository()

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
                    timestamp=timestamp,
                )
                self.company_repository.save(connection, slot_name, state.company)
                self.product_repository.save_all(connection, slot_name, state.products)
                self.employee_repository.save_all(connection, slot_name, state.employees)
                self._save_pending_event(connection, slot_name, state.pending_event)
                self._save_event_history(connection, slot_name, state.event_history)
                self._save_milestone_history(connection, slot_name, state.milestone_history)
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
                    SELECT action_points_remaining, rng_seed, rng_state
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
                    pending_event = self._load_pending_event(connection, slot_name)
                    event_history = self._load_event_history(connection, slot_name)
                    milestone_history = self._load_milestone_history(connection, slot_name)
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
                        pending_event=pending_event,
                        event_history=event_history,
                        milestone_history=milestone_history,
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

    def _upsert_slot_row(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
        action_points_remaining: int,
        rng_seed: int | None,
        rng_state: str,
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
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    slot_name,
                    action_points_remaining,
                    rng_seed,
                    rng_state,
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
                updated_at = ?
            WHERE slot_name = ?
            """,
            (
                action_points_remaining,
                rng_seed,
                rng_state,
                timestamp,
                slot_name,
            ),
        )

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


def utc_now() -> str:
    """Return a UTC ISO timestamp for save metadata."""

    return datetime.now(UTC).isoformat()
