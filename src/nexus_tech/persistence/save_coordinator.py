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
    CapitalPlan,
    CapitalPlanMode,
    CapitalSourcePreference,
    CompetitorIntelEntry,
    CompetitorMove,
    ContractBillingModel,
    DifficultyMode,
    EventCategory,
    EventHistoryEntry,
    EventOption,
    ExitOutcome,
    FinanceState,
    FunctionalBudget,
    FunctionalBudgetPreset,
    GameState,
    HiringCandidate,
    HiringCandidateStage,
    MarketCycle,
    MarketSegment,
    MilestoneEntry,
    MilestoneId,
    PartnerChannel,
    PartnershipDeal,
    PartnershipStatus,
    PendingEvent,
    PricingTier,
    ProductReleasePlan,
    ProductReleaseStatus,
    ProductReleaseType,
    RoadmapFocus,
    RoadmapProject,
    RoadmapProjectStatus,
    RoadmapProjectType,
    SalesDeal,
    SalesDealStage,
    ScenarioObjectiveMetric,
    SubscriptionPackage,
    SupportLaneFocus,
    SupportProgram,
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
from nexus_tech.simulation.endgame import evaluate_exit_outcome
from nexus_tech.simulation.postmortem import build_run_postmortem
from nexus_tech.simulation.randomness import RandomSource
from nexus_tech.simulation.reporting import calculate_run_badges
from nexus_tech.user_preferences import FrontendPreferences

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


@dataclass(frozen=True)
class RunArchiveSummary:
    """Compact history row for completed runs."""

    archive_key: str
    slot_name: str
    company_name: str
    scenario_title: str
    completed_turn: int
    victory_achieved: bool
    game_over: bool
    exit_outcome: str
    total_score: int
    score_tier: str
    campaign_grade: str
    estimated_valuation: Decimal
    achievement_badges: tuple[str, ...]
    strategic_outlook: str
    offer_value: Decimal
    final_cash: Decimal
    final_reputation: int
    archived_at: str
    review_title: str = ""
    review_primary_area: str = ""
    review_primary_summary: str = ""
    review_next_focus: str = ""
    scenario_id: str = ""
    difficulty_mode: str = "standard"
    campaign_commitment_choice: str = ""
    campaign_consequence_choice: str = ""
    terminal_reason: str = ""

    @property
    def campaign_path(self) -> tuple[str, ...]:
        """Return the recorded campaign choices in act order."""

        return tuple(
            label
            for label in (
                self.campaign_commitment_choice,
                self.campaign_consequence_choice,
            )
            if label
        )


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

    def load_frontend_preferences(self) -> FrontendPreferences:
        """Load the local 2D display profile, falling back safely if it is malformed."""

        try:
            self.initialize()
            with self.database.connect() as connection:
                row = connection.execute(
                    """
                    SELECT ui_scale, contrast_mode, motion_mode
                    FROM frontend_preferences
                    WHERE profile_key = 'default'
                    """
                ).fetchone()
        except sqlite3.DatabaseError as error:
            raise PersistenceError(f"Failed to load frontend preferences: {error}") from error

        if row is None:
            return FrontendPreferences()
        try:
            return FrontendPreferences.from_values(
                ui_scale=row["ui_scale"],
                contrast_mode=row["contrast_mode"],
                motion_mode=row["motion_mode"],
            )
        except (AttributeError, ValueError):
            return FrontendPreferences()

    def save_frontend_preferences(self, preferences: FrontendPreferences) -> None:
        """Persist the single local 2D display profile independently of save slots."""

        try:
            self.initialize()
            with self.database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO frontend_preferences (
                        profile_key,
                        ui_scale,
                        contrast_mode,
                        motion_mode,
                        updated_at
                    )
                    VALUES ('default', ?, ?, ?, ?)
                    ON CONFLICT(profile_key) DO UPDATE SET
                        ui_scale = excluded.ui_scale,
                        contrast_mode = excluded.contrast_mode,
                        motion_mode = excluded.motion_mode,
                        updated_at = excluded.updated_at
                    """,
                    (
                        preferences.ui_scale.value,
                        preferences.contrast_mode.value,
                        preferences.motion_mode.value,
                        utc_now(),
                    ),
                )
        except sqlite3.DatabaseError as error:
            raise PersistenceError(f"Failed to save frontend preferences: {error}") from error

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
                    scenario_objective=state.scenario_objective,
                    scenario_objective_metric=state.scenario_objective_metric,
                    scenario_objective_target=state.scenario_objective_target,
                    difficulty_mode=state.difficulty_mode,
                    campaign_goal_id=state.campaign_goal_id,
                    roadmap_focus=state.roadmap_focus,
                    roadmap_set_turn=state.roadmap_set_turn,
                    functional_budget=state.functional_budget,
                    support_program=state.support_program,
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
                # Remove old event targets before replacing employee/product graph rows.
                self._save_pending_event(connection, slot_name, None)
                self.company_repository.save(connection, slot_name, state.company)
                self.product_repository.save_all(connection, slot_name, state.products)
                self.employee_repository.save_all(connection, slot_name, state.employees)
                self.competitor_repository.save_all(connection, slot_name, state.competitors)
                self.customer_repository.save_all(
                    connection,
                    slot_name,
                    state.customer_accounts,
                )
                self._save_product_releases(connection, slot_name, state.product_releases)
                self._save_sales_deals(connection, slot_name, state.sales_deals)
                self._save_hiring_candidates(connection, slot_name, state.hiring_candidates)
                self._save_roadmap_projects(connection, slot_name, state.roadmap_projects)
                self._save_competitor_intel(connection, slot_name, state.competitor_intel)
                self._save_partnerships(connection, slot_name, state.partnerships)
                self._save_capital_plan(connection, slot_name, state.capital_plan)
                self.finance_repository.save(connection, slot_name, state.finance)
                self.finance_repository.save_history(connection, slot_name, state.funding_history)
                self.quarter_plan_repository.save(connection, slot_name, state.quarter_plan)
                self._save_pending_event(connection, slot_name, state.pending_event)
                self._save_event_history(connection, slot_name, state.event_history)
                self._save_milestone_history(connection, slot_name, state.milestone_history)
                self._save_turn_history(connection, slot_name, state.turn_history)
                self.product_repository.delete_missing(connection, slot_name, state.products)
                self._archive_completed_run(connection, slot_name, state, timestamp)
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
                        scenario_objective,
                        scenario_objective_metric,
                        scenario_objective_target,
                        difficulty_mode,
                        campaign_goal_id,
                        roadmap_focus,
                        roadmap_set_turn,
                        functional_budget_preset,
                        budget_engineering_share,
                        budget_marketing_share,
                        budget_customer_success_share,
                        budget_g_and_a_share,
                        support_knowledge_base_level,
                        support_automation_level,
                        support_sla_target,
                        support_lane_focus,
                        support_backlog_queue,
                        support_escalation_queue,
                        support_staffing_level,
                        support_resolved_last_turn,
                        support_deflection_score,
                        support_sla_breaches_last_turn,
                        support_queue_age_pressure,
                        support_onboarding_ticket_pressure,
                        support_enterprise_ticket_pressure,
                        support_billing_ticket_pressure,
                        support_service_cost_last_turn,
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
                    product_releases = self._load_product_releases(connection, slot_name)
                    sales_deals = self._load_sales_deals(connection, slot_name)
                    hiring_candidates = self._load_hiring_candidates(connection, slot_name)
                    roadmap_projects = self._load_roadmap_projects(connection, slot_name)
                    competitor_intel = self._load_competitor_intel(connection, slot_name)
                    partnerships = self._load_partnerships(connection, slot_name)
                    capital_plan = self._load_capital_plan(connection, slot_name)
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
                        product_releases=product_releases,
                        sales_deals=sales_deals,
                        hiring_candidates=hiring_candidates,
                        roadmap_projects=roadmap_projects,
                        competitor_intel=competitor_intel,
                        partnerships=partnerships,
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
                        scenario_objective=slot_row["scenario_objective"],
                        scenario_objective_metric=ScenarioObjectiveMetric(
                            slot_row["scenario_objective_metric"]
                        ),
                        scenario_objective_target=slot_row["scenario_objective_target"],
                        difficulty_mode=DifficultyMode(slot_row["difficulty_mode"]),
                        campaign_goal_id=CampaignGoalId(slot_row["campaign_goal_id"]),
                        capital_plan=capital_plan,
                        functional_budget=FunctionalBudget(
                            preset=FunctionalBudgetPreset(
                                slot_row["functional_budget_preset"] or "balanced"
                            ),
                            engineering_share=slot_row["budget_engineering_share"] or 30,
                            marketing_share=slot_row["budget_marketing_share"] or 25,
                            customer_success_share=(
                                slot_row["budget_customer_success_share"] or 25
                            ),
                            g_and_a_share=slot_row["budget_g_and_a_share"] or 20,
                        ),
                        support_program=SupportProgram(
                            knowledge_base_level=slot_row["support_knowledge_base_level"] or 22,
                            automation_level=slot_row["support_automation_level"] or 16,
                            sla_target=slot_row["support_sla_target"] or 58,
                            lane_focus=SupportLaneFocus(
                                slot_row["support_lane_focus"] or "balanced"
                            ),
                            backlog_queue=slot_row["support_backlog_queue"] or 0,
                            escalation_queue=slot_row["support_escalation_queue"] or 0,
                            staffing_level=slot_row["support_staffing_level"] or 0,
                            resolved_last_turn=slot_row["support_resolved_last_turn"] or 0,
                            deflection_score=slot_row["support_deflection_score"] or 0,
                            sla_breaches_last_turn=(
                                slot_row["support_sla_breaches_last_turn"] or 0
                            ),
                            queue_age_pressure=slot_row["support_queue_age_pressure"] or 0,
                            onboarding_ticket_pressure=(
                                slot_row["support_onboarding_ticket_pressure"] or 0
                            ),
                            enterprise_ticket_pressure=(
                                slot_row["support_enterprise_ticket_pressure"] or 0
                            ),
                            billing_ticket_pressure=(
                                slot_row["support_billing_ticket_pressure"] or 0
                            ),
                            service_cost_last_turn=Decimal(
                                slot_row["support_service_cost_last_turn"] or "0.00"
                            ),
                        ),
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

    def list_run_archives(self) -> list[RunArchiveSummary]:
        """Return archived completed runs ordered by most recent archive time."""

        if not self.database.exists():
            return []

        try:
            self.initialize()
            with self.database.connect() as connection:
                rows = connection.execute(
                    """
                    SELECT
                        archive_key,
                        slot_name,
                        company_name,
                        scenario_id,
                        scenario_title,
                        difficulty_mode,
                        campaign_commitment_choice,
                        campaign_consequence_choice,
                        terminal_reason,
                        completed_turn,
                        victory_achieved,
                        game_over,
                        exit_outcome,
                        total_score,
                        score_tier,
                        campaign_grade,
                        estimated_valuation,
                        achievement_badges,
                        strategic_outlook,
                        offer_value,
                        final_cash,
                        final_reputation,
                        archived_at,
                        review_title,
                        review_primary_area,
                        review_primary_summary,
                        review_next_focus
                    FROM run_archives
                    ORDER BY archived_at DESC
                    """
                ).fetchall()
        except sqlite3.DatabaseError as error:
            raise PersistenceError(f"Failed to inspect run archives: {error}") from error

        return [
            RunArchiveSummary(
                archive_key=row["archive_key"],
                slot_name=row["slot_name"],
                company_name=row["company_name"],
                scenario_id=row["scenario_id"] or "",
                scenario_title=row["scenario_title"] or "Unknown scenario",
                difficulty_mode=row["difficulty_mode"] or "standard",
                campaign_commitment_choice=row["campaign_commitment_choice"] or "",
                campaign_consequence_choice=row["campaign_consequence_choice"] or "",
                terminal_reason=row["terminal_reason"] or "",
                completed_turn=row["completed_turn"] or 0,
                victory_achieved=bool(row["victory_achieved"]),
                game_over=bool(row["game_over"]),
                exit_outcome=row["exit_outcome"] or "none",
                total_score=row["total_score"] or 0,
                score_tier=row["score_tier"] or "fragile",
                campaign_grade=row["campaign_grade"] or "D",
                estimated_valuation=Decimal(row["estimated_valuation"] or "0.00"),
                achievement_badges=tuple(
                    badge for badge in (row["achievement_badges"] or "").split(",") if badge
                ),
                strategic_outlook=row["strategic_outlook"] or "profitable_independence",
                offer_value=Decimal(row["offer_value"] or "0.00"),
                final_cash=Decimal(row["final_cash"] or "0.00"),
                final_reputation=row["final_reputation"] or 0,
                archived_at=row["archived_at"],
                review_title=row["review_title"] or "",
                review_primary_area=row["review_primary_area"] or "",
                review_primary_summary=row["review_primary_summary"] or "",
                review_next_focus=row["review_next_focus"] or "",
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
                slot_count = connection.execute("SELECT COUNT(*) FROM save_slots").fetchone()[0]
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
        scenario_objective: str,
        scenario_objective_metric: ScenarioObjectiveMetric,
        scenario_objective_target: int,
        difficulty_mode: DifficultyMode,
        campaign_goal_id: CampaignGoalId,
        roadmap_focus: RoadmapFocus,
        roadmap_set_turn: int,
        functional_budget: FunctionalBudget,
        support_program: SupportProgram,
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
            insert_values = (
                slot_name,
                action_points_remaining,
                rng_seed,
                rng_state,
                scenario_id,
                scenario_title,
                scenario_objective,
                scenario_objective_metric.value,
                scenario_objective_target,
                difficulty_mode.value,
                campaign_goal_id.value,
                roadmap_focus.value,
                roadmap_set_turn,
                functional_budget.preset.value,
                functional_budget.engineering_share,
                functional_budget.marketing_share,
                functional_budget.customer_success_share,
                functional_budget.g_and_a_share,
                support_program.knowledge_base_level,
                support_program.automation_level,
                support_program.sla_target,
                support_program.lane_focus.value,
                support_program.backlog_queue,
                support_program.escalation_queue,
                support_program.staffing_level,
                support_program.resolved_last_turn,
                support_program.deflection_score,
                support_program.sla_breaches_last_turn,
                support_program.queue_age_pressure,
                support_program.onboarding_ticket_pressure,
                support_program.enterprise_ticket_pressure,
                support_program.billing_ticket_pressure,
                str(support_program.service_cost_last_turn),
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
            )
            placeholders = ", ".join(["?"] * len(insert_values))
            connection.execute(
                f"""
                INSERT INTO save_slots (
                    slot_name,
                    action_points_remaining,
                    rng_seed,
                    rng_state,
                    scenario_id,
                    scenario_title,
                    scenario_objective,
                    scenario_objective_metric,
                    scenario_objective_target,
                    difficulty_mode,
                    campaign_goal_id,
                    roadmap_focus,
                    roadmap_set_turn,
                    functional_budget_preset,
                    budget_engineering_share,
                    budget_marketing_share,
                    budget_customer_success_share,
                    budget_g_and_a_share,
                    support_knowledge_base_level,
                    support_automation_level,
                    support_sla_target,
                    support_lane_focus,
                    support_backlog_queue,
                    support_escalation_queue,
                    support_staffing_level,
                    support_resolved_last_turn,
                    support_deflection_score,
                    support_sla_breaches_last_turn,
                    support_queue_age_pressure,
                    support_onboarding_ticket_pressure,
                    support_enterprise_ticket_pressure,
                    support_billing_ticket_pressure,
                    support_service_cost_last_turn,
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
                VALUES ({placeholders})
                """,
                insert_values,
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
                scenario_objective = ?,
                scenario_objective_metric = ?,
                scenario_objective_target = ?,
                difficulty_mode = ?,
                campaign_goal_id = ?,
                roadmap_focus = ?,
                roadmap_set_turn = ?,
                functional_budget_preset = ?,
                budget_engineering_share = ?,
                budget_marketing_share = ?,
                budget_customer_success_share = ?,
                budget_g_and_a_share = ?,
                support_knowledge_base_level = ?,
                support_automation_level = ?,
                support_sla_target = ?,
                support_lane_focus = ?,
                support_backlog_queue = ?,
                support_escalation_queue = ?,
                support_staffing_level = ?,
                support_resolved_last_turn = ?,
                support_deflection_score = ?,
                support_sla_breaches_last_turn = ?,
                support_queue_age_pressure = ?,
                support_onboarding_ticket_pressure = ?,
                support_enterprise_ticket_pressure = ?,
                support_billing_ticket_pressure = ?,
                support_service_cost_last_turn = ?,
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
                scenario_objective,
                scenario_objective_metric.value,
                scenario_objective_target,
                difficulty_mode.value,
                campaign_goal_id.value,
                roadmap_focus.value,
                roadmap_set_turn,
                functional_budget.preset.value,
                functional_budget.engineering_share,
                functional_budget.marketing_share,
                functional_budget.customer_success_share,
                functional_budget.g_and_a_share,
                support_program.knowledge_base_level,
                support_program.automation_level,
                support_program.sla_target,
                support_program.lane_focus.value,
                support_program.backlog_queue,
                support_program.escalation_queue,
                support_program.staffing_level,
                support_program.resolved_last_turn,
                support_program.deflection_score,
                support_program.sla_breaches_last_turn,
                support_program.queue_age_pressure,
                support_program.onboarding_ticket_pressure,
                support_program.enterprise_ticket_pressure,
                support_program.billing_ticket_pressure,
                str(support_program.service_cost_last_turn),
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

    def _archive_completed_run(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
        state: GameState,
        timestamp: str,
    ) -> None:
        if not state.victory_achieved and not state.company.game_over:
            return

        archive_key = (
            f"{slot_name}:{state.company.current_turn}:"
            f"{state.exit_outcome.value if state.exit_outcome is not None else 'none'}"
        )
        from nexus_tech.simulation.campaign_decisions import get_campaign_choice_label
        from nexus_tech.simulation.campaign_journey import CampaignActId
        from nexus_tech.simulation.reporting import calculate_run_score

        run_score = calculate_run_score(state)
        exit_evaluation = evaluate_exit_outcome(state, run_score)
        postmortem = build_run_postmortem(state)
        primary_finding = postmortem.findings[0] if postmortem.findings else None
        commitment_choice = get_campaign_choice_label(state, CampaignActId.COMMITMENT) or ""
        consequence_choice = get_campaign_choice_label(state, CampaignActId.CONSEQUENCE) or ""
        terminal_reason = (
            state.victory_reason
            or state.exit_summary
            or ("Company shutdown" if state.company.game_over else "Run completed")
        )
        connection.execute(
            """
            INSERT OR REPLACE INTO run_archives (
                archive_key,
                slot_name,
                company_name,
                scenario_id,
                scenario_title,
                difficulty_mode,
                campaign_commitment_choice,
                campaign_consequence_choice,
                terminal_reason,
                completed_turn,
                victory_achieved,
                game_over,
                exit_outcome,
                exit_summary,
                total_score,
                score_tier,
                campaign_grade,
                estimated_valuation,
                achievement_badges,
                strategic_outlook,
                offer_value,
                final_cash,
                final_reputation,
                archived_at,
                review_title,
                review_primary_area,
                review_primary_summary,
                review_next_focus
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                archive_key,
                slot_name,
                state.company.name,
                state.scenario_id,
                state.scenario_title,
                state.difficulty_mode.value,
                commitment_choice,
                consequence_choice,
                terminal_reason,
                state.company.current_turn,
                int(state.victory_achieved),
                int(state.company.game_over),
                state.exit_outcome.value if state.exit_outcome is not None else "none",
                state.exit_summary,
                run_score.total_score,
                run_score.score_tier,
                run_score.campaign_grade,
                str(run_score.estimated_valuation),
                ",".join(calculate_run_badges(state, run_score)),
                exit_evaluation.readiness.strategic_outlook,
                str(exit_evaluation.offer_value),
                str(state.company.cash_on_hand),
                state.company.reputation,
                timestamp,
                postmortem.title,
                primary_finding.area if primary_finding is not None else "",
                primary_finding.summary if primary_finding is not None else postmortem.headline,
                postmortem.next_run_focus,
            ),
        )

    def _slot_exists(self, connection: sqlite3.Connection, slot_name: str) -> bool:
        row = connection.execute(
            "SELECT 1 FROM save_slots WHERE slot_name = ?",
            (slot_name,),
        ).fetchone()
        return row is not None

    def _save_product_releases(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
        product_releases: list[ProductReleasePlan],
    ) -> None:
        connection.execute("DELETE FROM product_releases WHERE slot_name = ?", (slot_name,))
        connection.executemany(
            """
            INSERT INTO product_releases (
                slot_name,
                release_id,
                display_order,
                product_id,
                release_type,
                status,
                progress,
                required_progress,
                risk,
                scheduled_turn,
                shipped_turn,
                summary
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    slot_name,
                    str(release.id),
                    index,
                    str(release.product_id),
                    release.release_type.value,
                    release.status.value,
                    release.progress,
                    release.required_progress,
                    release.risk,
                    release.scheduled_turn,
                    release.shipped_turn,
                    release.summary,
                )
                for index, release in enumerate(product_releases)
            ],
        )

    def _load_product_releases(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
    ) -> list[ProductReleasePlan]:
        rows = connection.execute(
            """
            SELECT
                release_id,
                product_id,
                release_type,
                status,
                progress,
                required_progress,
                risk,
                scheduled_turn,
                shipped_turn,
                summary
            FROM product_releases
            WHERE slot_name = ?
            ORDER BY display_order ASC
            """,
            (slot_name,),
        ).fetchall()
        return [
            ProductReleasePlan(
                id=UUID(row["release_id"]),
                product_id=UUID(row["product_id"]),
                release_type=ProductReleaseType(row["release_type"]),
                status=ProductReleaseStatus(row["status"]),
                progress=row["progress"],
                required_progress=row["required_progress"],
                risk=row["risk"],
                scheduled_turn=row["scheduled_turn"],
                shipped_turn=row["shipped_turn"],
                summary=row["summary"],
            )
            for row in rows
        ]

    def _save_sales_deals(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
        sales_deals: list[SalesDeal],
    ) -> None:
        connection.execute("DELETE FROM sales_deals WHERE slot_name = ?", (slot_name,))
        connection.executemany(
            """
            INSERT INTO sales_deals (
                slot_name,
                deal_id,
                display_order,
                product_id,
                name,
                segment,
                stage,
                plan_tier,
                subscription_package,
                billing_model,
                seat_commitment,
                usage_commitment,
                add_on_commitment,
                annual_prepay_offer,
                value,
                proposed_discount_rate,
                probability,
                created_turn,
                updated_turn
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    slot_name,
                    str(deal.id),
                    index,
                    str(deal.product_id),
                    deal.name,
                    deal.segment.value,
                    deal.stage.value,
                    deal.plan_tier.value,
                    deal.subscription_package.value,
                    deal.billing_model.value,
                    deal.seat_commitment,
                    deal.usage_commitment,
                    deal.add_on_commitment,
                    int(deal.annual_prepay_offer),
                    str(deal.value),
                    str(deal.proposed_discount_rate),
                    deal.probability,
                    deal.created_turn,
                    deal.updated_turn,
                )
                for index, deal in enumerate(sales_deals)
            ],
        )

    def _load_sales_deals(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
    ) -> list[SalesDeal]:
        rows = connection.execute(
            """
            SELECT
                deal_id,
                product_id,
                name,
                segment,
                stage,
                plan_tier,
                subscription_package,
                billing_model,
                seat_commitment,
                usage_commitment,
                add_on_commitment,
                annual_prepay_offer,
                value,
                proposed_discount_rate,
                probability,
                created_turn,
                updated_turn
            FROM sales_deals
            WHERE slot_name = ?
            ORDER BY display_order ASC
            """,
            (slot_name,),
        ).fetchall()
        return [
            SalesDeal(
                id=UUID(row["deal_id"]),
                product_id=UUID(row["product_id"]),
                name=row["name"],
                segment=MarketSegment(row["segment"]),
                stage=SalesDealStage(row["stage"]),
                plan_tier=PricingTier(row["plan_tier"] or "standard"),
                subscription_package=SubscriptionPackage(row["subscription_package"] or "growth"),
                billing_model=ContractBillingModel(row["billing_model"] or "flat"),
                seat_commitment=row["seat_commitment"] or 0,
                usage_commitment=row["usage_commitment"] or 0,
                add_on_commitment=row["add_on_commitment"] or 0,
                annual_prepay_offer=bool(row["annual_prepay_offer"]),
                value=Decimal(row["value"]),
                proposed_discount_rate=Decimal(row["proposed_discount_rate"] or "0.0000"),
                probability=row["probability"],
                created_turn=row["created_turn"],
                updated_turn=row["updated_turn"],
            )
            for row in rows
        ]

    def _save_hiring_candidates(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
        hiring_candidates: list[HiringCandidate],
    ) -> None:
        connection.execute("DELETE FROM hiring_candidates WHERE slot_name = ?", (slot_name,))
        connection.executemany(
            """
            INSERT INTO hiring_candidates (
                slot_name,
                candidate_id,
                display_order,
                full_name,
                role,
                seniority,
                specialization,
                trait,
                salary_expectation,
                expected_productivity,
                stage,
                sourced_turn,
                expires_turn,
                offer_deadline_turn,
                interview_score,
                acceptance_chance,
                market_salary_pressure,
                negotiation_rounds
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    slot_name,
                    str(candidate.id),
                    index,
                    candidate.full_name,
                    candidate.role.value,
                    candidate.seniority.value,
                    candidate.specialization,
                    candidate.trait.value,
                    str(candidate.salary_expectation),
                    candidate.expected_productivity,
                    candidate.stage.value,
                    candidate.sourced_turn,
                    candidate.expires_turn,
                    candidate.offer_deadline_turn,
                    candidate.interview_score,
                    candidate.acceptance_chance,
                    candidate.market_salary_pressure,
                    candidate.negotiation_rounds,
                )
                for index, candidate in enumerate(hiring_candidates)
            ],
        )

    def _load_hiring_candidates(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
    ) -> list[HiringCandidate]:
        rows = connection.execute(
            """
            SELECT
                candidate_id,
                full_name,
                role,
                seniority,
                specialization,
                trait,
                salary_expectation,
                expected_productivity,
                stage,
                sourced_turn,
                expires_turn,
                offer_deadline_turn,
                interview_score,
                acceptance_chance,
                market_salary_pressure,
                negotiation_rounds
            FROM hiring_candidates
            WHERE slot_name = ?
            ORDER BY display_order ASC
            """,
            (slot_name,),
        ).fetchall()
        return [
            HiringCandidate(
                id=UUID(row["candidate_id"]),
                full_name=row["full_name"],
                role=row["role"],
                seniority=row["seniority"],
                specialization=row["specialization"],
                trait=row["trait"],
                salary_expectation=Decimal(row["salary_expectation"]),
                expected_productivity=row["expected_productivity"],
                stage=HiringCandidateStage(row["stage"] or "sourced"),
                sourced_turn=row["sourced_turn"],
                expires_turn=row["expires_turn"],
                offer_deadline_turn=row["offer_deadline_turn"] or row["expires_turn"],
                interview_score=row["interview_score"] or 0,
                acceptance_chance=row["acceptance_chance"] or 50,
                market_salary_pressure=row["market_salary_pressure"] or 0,
                negotiation_rounds=row["negotiation_rounds"] or 0,
            )
            for row in rows
        ]

    def _save_roadmap_projects(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
        roadmap_projects: list[RoadmapProject],
    ) -> None:
        connection.execute("DELETE FROM roadmap_projects WHERE slot_name = ?", (slot_name,))
        connection.executemany(
            """
            INSERT INTO roadmap_projects (
                slot_name,
                project_id,
                display_order,
                project_type,
                status,
                target_product_id,
                progress,
                required_progress,
                epic_count,
                epics_completed,
                started_turn,
                deadline_turn,
                dependency_project_type,
                delivery_risk,
                completed_turn,
                summary
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    slot_name,
                    str(project.id),
                    index,
                    project.project_type.value,
                    project.status.value,
                    str(project.target_product_id)
                    if project.target_product_id is not None
                    else None,
                    project.progress,
                    project.required_progress,
                    project.epic_count,
                    project.epics_completed,
                    project.started_turn,
                    project.deadline_turn,
                    project.dependency_project_type.value
                    if project.dependency_project_type is not None
                    else None,
                    project.delivery_risk,
                    project.completed_turn,
                    project.summary,
                )
                for index, project in enumerate(roadmap_projects)
            ],
        )

    def _load_roadmap_projects(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
    ) -> list[RoadmapProject]:
        rows = connection.execute(
            """
            SELECT
                project_id,
                project_type,
                status,
                target_product_id,
                progress,
                required_progress,
                epic_count,
                epics_completed,
                started_turn,
                deadline_turn,
                dependency_project_type,
                delivery_risk,
                completed_turn,
                summary
            FROM roadmap_projects
            WHERE slot_name = ?
            ORDER BY display_order ASC
            """,
            (slot_name,),
        ).fetchall()
        return [
            RoadmapProject(
                id=UUID(row["project_id"]),
                project_type=RoadmapProjectType(row["project_type"]),
                status=RoadmapProjectStatus(row["status"]),
                target_product_id=UUID(row["target_product_id"])
                if row["target_product_id"] is not None
                else None,
                progress=row["progress"],
                required_progress=row["required_progress"],
                epic_count=row["epic_count"] or 3,
                epics_completed=row["epics_completed"] or 0,
                started_turn=row["started_turn"],
                deadline_turn=row["deadline_turn"] or row["started_turn"],
                dependency_project_type=RoadmapProjectType(row["dependency_project_type"])
                if row["dependency_project_type"] is not None
                else None,
                delivery_risk=row["delivery_risk"] or 0,
                completed_turn=row["completed_turn"],
                summary=row["summary"],
            )
            for row in rows
        ]

    def _save_competitor_intel(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
        competitor_intel: list[CompetitorIntelEntry],
    ) -> None:
        connection.execute("DELETE FROM competitor_intel WHERE slot_name = ?", (slot_name,))
        connection.executemany(
            """
            INSERT INTO competitor_intel (
                slot_name,
                entry_index,
                turn,
                competitor_name,
                move,
                summary
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    slot_name,
                    index,
                    entry.turn,
                    entry.competitor_name,
                    entry.move.value,
                    entry.summary,
                )
                for index, entry in enumerate(competitor_intel)
            ],
        )

    def _load_competitor_intel(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
    ) -> list[CompetitorIntelEntry]:
        rows = connection.execute(
            """
            SELECT turn, competitor_name, move, summary
            FROM competitor_intel
            WHERE slot_name = ?
            ORDER BY entry_index ASC
            """,
            (slot_name,),
        ).fetchall()
        return [
            CompetitorIntelEntry(
                turn=row["turn"],
                competitor_name=row["competitor_name"],
                move=CompetitorMove(row["move"]),
                summary=row["summary"],
            )
            for row in rows
        ]

    def _save_partnerships(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
        partnerships: list[PartnershipDeal],
    ) -> None:
        connection.execute("DELETE FROM partnerships WHERE slot_name = ?", (slot_name,))
        connection.executemany(
            """
            INSERT INTO partnerships (
                slot_name,
                partnership_id,
                display_order,
                name,
                product_id,
                channel,
                status,
                quality,
                risk,
                enablement_level,
                rev_share_rate,
                sourced_revenue,
                sourced_users,
                conflict_pressure,
                started_turn,
                last_review_turn,
                summary
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    slot_name,
                    str(partnership.id),
                    index,
                    partnership.name,
                    str(partnership.product_id),
                    partnership.channel.value,
                    partnership.status.value,
                    partnership.quality,
                    partnership.risk,
                    partnership.enablement_level,
                    str(partnership.rev_share_rate),
                    str(partnership.sourced_revenue),
                    partnership.sourced_users,
                    partnership.conflict_pressure,
                    partnership.started_turn,
                    partnership.last_review_turn,
                    partnership.summary,
                )
                for index, partnership in enumerate(partnerships)
            ],
        )

    def _load_partnerships(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
    ) -> list[PartnershipDeal]:
        rows = connection.execute(
            """
            SELECT
                partnership_id,
                name,
                product_id,
                channel,
                status,
                quality,
                risk,
                enablement_level,
                rev_share_rate,
                sourced_revenue,
                sourced_users,
                conflict_pressure,
                started_turn,
                last_review_turn,
                summary
            FROM partnerships
            WHERE slot_name = ?
            ORDER BY display_order ASC
            """,
            (slot_name,),
        ).fetchall()
        return [
            PartnershipDeal(
                id=UUID(row["partnership_id"]),
                name=row["name"],
                product_id=UUID(row["product_id"]),
                channel=PartnerChannel(row["channel"]),
                status=PartnershipStatus(row["status"]),
                quality=row["quality"],
                risk=row["risk"],
                enablement_level=row["enablement_level"],
                rev_share_rate=row["rev_share_rate"],
                sourced_revenue=row["sourced_revenue"],
                sourced_users=row["sourced_users"],
                conflict_pressure=row["conflict_pressure"],
                started_turn=row["started_turn"],
                last_review_turn=row["last_review_turn"],
                summary=row["summary"],
            )
            for row in rows
        ]

    def _save_capital_plan(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
        capital_plan: CapitalPlan,
    ) -> None:
        connection.execute(
            """
            INSERT OR REPLACE INTO capital_plan (
                slot_name,
                mode,
                source_preference,
                planning_horizon_turns,
                reserve_target,
                product_investment_share,
                go_to_market_share,
                reserve_share
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                slot_name,
                capital_plan.mode.value,
                capital_plan.source_preference.value,
                capital_plan.planning_horizon_turns,
                str(capital_plan.reserve_target),
                capital_plan.product_investment_share,
                capital_plan.go_to_market_share,
                capital_plan.reserve_share,
            ),
        )

    def _load_capital_plan(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
    ) -> CapitalPlan:
        row = connection.execute(
            """
            SELECT
                mode,
                source_preference,
                planning_horizon_turns,
                reserve_target,
                product_investment_share,
                go_to_market_share,
                reserve_share
            FROM capital_plan
            WHERE slot_name = ?
            """,
            (slot_name,),
        ).fetchone()
        if row is None:
            return CapitalPlan()
        return CapitalPlan(
            mode=CapitalPlanMode(row["mode"]),
            source_preference=CapitalSourcePreference(row["source_preference"]),
            planning_horizon_turns=row["planning_horizon_turns"],
            reserve_target=row["reserve_target"],
            product_investment_share=row["product_investment_share"],
            go_to_market_share=row["go_to_market_share"],
            reserve_share=row["reserve_share"],
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
                chain_id,
                chain_stage,
                target_product_id,
                target_employee_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                slot_name,
                pending_event.event_id,
                pending_event.category.value,
                pending_event.title,
                pending_event.description,
                pending_event.triggered_turn,
                pending_event.cooldown_turns,
                pending_event.chain_id,
                pending_event.chain_stage,
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
                chain_id,
                chain_stage,
                selected_option_id,
                selected_option_label,
                result_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    entry.chain_id,
                    entry.chain_stage,
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
                chain_id,
                chain_stage,
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
            chain_id=row["chain_id"],
            chain_stage=row["chain_stage"],
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
                chain_id,
                chain_stage,
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
                chain_id=row["chain_id"],
                chain_stage=row["chain_stage"],
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
