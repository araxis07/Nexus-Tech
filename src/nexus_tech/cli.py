"""Typer CLI entrypoint for NEXUS TECH."""

from __future__ import annotations

import logging
import re
import textwrap
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional
from uuid import UUID

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.traceback import install as install_rich_traceback

from nexus_tech import __version__
from nexus_tech.config import (
    DEFAULT_DATABASE_PATH,
    DEFAULT_SCENARIO_ID,
    DEMO_SEED_EXAMPLE,
)
from nexus_tech.content.models import ProductTemplateDefinition
from nexus_tech.domain.models import (
    BudgetStance,
    CampaignGoalId,
    CandidateTrait,
    CapitalPlanMode,
    CapitalSourcePreference,
    CompanyStrategy,
    DifficultyMode,
    Employee,
    EmployeeRole,
    FunctionalBudgetPreset,
    GameState,
    HiringCandidateStage,
    MarketSegment,
    PackagingStrategy,
    PartnerChannel,
    PendingEvent,
    PricingTier,
    Product,
    ProductReleaseStatus,
    ProductReleaseType,
    RenewalOfferType,
    RoadmapFocus,
    RoadmapProjectStatus,
    RoadmapProjectType,
    SalesDealStage,
    Seniority,
    SupportInvestmentFocus,
    SupportLaneFocus,
    TurnAction,
)
from nexus_tech.frontend_2d import (
    DEFAULT_ANIMATION_MATRIX_SCENARIOS,
    DEFAULT_ANIMATION_MATRIX_SEEDS,
    AnimationPlaytestCommand,
    AnimationPlaytestReadinessPlan,
    AnimationPlaytestRecorderHint,
    AnimationPlaytestReportValidation,
    Frontend2DUnavailableError,
    MotionMode,
    animation_playtest_route_batch_copy_commands,
    animation_playtest_sprint_blocker_dependency,
    animation_playtest_sprint_blocker_next_action,
    animation_playtest_sprint_blocker_phase,
    build_2d_animation_playtest_command_queue,
    build_2d_animation_playtest_execution_guide,
    build_2d_animation_playtest_handoff,
    build_2d_animation_playtest_issue_backlog,
    build_2d_animation_playtest_prep_report,
    build_2d_animation_playtest_progress_board,
    build_2d_animation_playtest_readiness_plan,
    build_2d_animation_playtest_recorder_hint,
    build_2d_animation_playtest_recorder_queue,
    build_2d_animation_playtest_release_gate,
    build_2d_animation_playtest_route_batch_plan,
    build_2d_animation_playtest_sprint_packet,
    build_2d_animation_playtest_ui_triage_plan,
    launch_2d_frontend,
    launch_2d_menu,
    record_2d_animation_playtest_control_evidence,
    record_2d_animation_playtest_feedback_evidence,
    record_2d_animation_playtest_field,
    record_2d_animation_playtest_route_evidence,
    record_2d_animation_playtest_scene_evidence,
    record_2d_animation_playtest_window_evidence,
    run_2d_animation_audit,
    run_2d_animation_matrix_audit,
    run_2d_motion_audit,
    run_2d_visual_audit,
    summarize_2d_animation_playtest_report,
    validate_2d_animation_playtest_command_queue,
    validate_2d_animation_playtest_execution_guide,
    validate_2d_animation_playtest_issue_backlog,
    validate_2d_animation_playtest_progress_board,
    validate_2d_animation_playtest_readiness_plan,
    validate_2d_animation_playtest_recorder_queue,
    validate_2d_animation_playtest_release_gate,
    validate_2d_animation_playtest_report,
    validate_2d_animation_playtest_route_batch_plan,
    validate_2d_animation_playtest_session,
    validate_2d_animation_playtest_sprint_packet,
    validate_2d_animation_playtest_ui_triage_plan,
    write_2d_animation_matrix_report,
    write_2d_animation_playtest_command_queue,
    write_2d_animation_playtest_execution_guide,
    write_2d_animation_playtest_handoff,
    write_2d_animation_playtest_issue_backlog,
    write_2d_animation_playtest_prep_report,
    write_2d_animation_playtest_progress_board,
    write_2d_animation_playtest_readiness_plan,
    write_2d_animation_playtest_recorder_queue,
    write_2d_animation_playtest_release_gate,
    write_2d_animation_playtest_report_template,
    write_2d_animation_playtest_route_batch_plan,
    write_2d_animation_playtest_sprint_packet,
    write_2d_animation_playtest_ui_triage_plan,
)
from nexus_tech.persistence.errors import PersistenceError
from nexus_tech.persistence.save_coordinator import (
    DEFAULT_SAVE_SLOT,
    RunArchiveSummary,
    SaveLoadCoordinator,
)
from nexus_tech.presentation.dashboard import (
    render_action_feedback,
    render_archive_comparison,
    render_balance_audit,
    render_balance_comparison,
    render_balance_lab,
    render_balance_matrix,
    render_balance_profile_catalog,
    render_board_view,
    render_campaign_goal_catalog,
    render_campaign_start_catalog,
    render_candidate_pool,
    render_competitor_archetype_catalog,
    render_content_health,
    render_customer_view,
    render_dashboard,
    render_employee_picker,
    render_event_catalog,
    render_event_result,
    render_game_over,
    render_glossary,
    render_intro,
    render_meta_progression,
    render_partnership_view,
    render_pending_event,
    render_pipeline_view,
    render_product_picker,
    render_product_template_catalog,
    render_product_template_picker,
    render_quick_guide,
    render_report,
    render_roadmap_catalog,
    render_run_archive_catalog,
    render_save_slot_catalog,
    render_scenario_catalog,
    render_segment_catalog,
    render_team_view,
    render_turn_resolution,
    render_tutorial,
    render_unlock_catalog,
    render_victory,
)
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.balance_lab import (
    format_balance_matrix_csv,
    format_balance_report_markdown,
    run_balance_audit,
    run_balance_batch,
    run_balance_comparison,
    run_balance_matrix,
)
from nexus_tech.simulation.balance_profiles import list_balance_profiles
from nexus_tech.simulation.campaign import get_campaign_goal, list_campaign_goals
from nexus_tech.simulation.campaign_starts import (
    STANDARD_CAMPAIGN_START_ID,
    get_campaign_start_definition,
    list_campaign_starts,
)
from nexus_tech.simulation.capital_planning import get_capital_plan_profile
from nexus_tech.simulation.catalog_validation import validate_content_catalogs
from nexus_tech.simulation.end_turn_preview import build_end_turn_preview
from nexus_tech.simulation.engine import (
    ActionContext,
    apply_action,
    create_new_game,
    get_customer_choices,
    get_employee_choices,
    get_partnership_choices,
    get_product_choices,
    resolve_turn,
)
from nexus_tech.simulation.event_registry import get_event_registry
from nexus_tech.simulation.events import resolve_pending_event
from nexus_tech.simulation.hiring import generate_candidate_pool
from nexus_tech.simulation.meta_progression import (
    build_unlock_catalog,
    get_locked_reward_ids,
    is_reward_unlocked,
    summarize_meta_progression,
)
from nexus_tech.simulation.randomness import RandomSource
from nexus_tech.simulation.roadmap import get_roadmap_profile
from nexus_tech.simulation.scenarios import (
    get_available_competitor_archetypes,
    get_available_product_templates,
    get_available_scenarios,
)
from nexus_tech.simulation.segments import get_market_segment_profile

logger = logging.getLogger(__name__)

app = typer.Typer(
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    help=(
        "NEXUS TECH terminal management simulation.\n\n"
        "Start a new run, resume a local SQLite save, and play entirely from the terminal."
    ),
    rich_markup_mode="rich",
)
console = Console(highlight=False, soft_wrap=True)
DEBUG_MODE = False
DEFAULT_DB_PATH = DEFAULT_DATABASE_PATH


def show_version_callback(value: bool) -> None:
    """Print the current package version and exit immediately."""

    if not value:
        return
    console.print(f"NEXUS TECH {__version__}")
    raise typer.Exit()


DB_PATH_OPTION = typer.Option(
    DEFAULT_DB_PATH,
    "--db-path",
    help="SQLite database path used for save, load, and continue commands.",
)
SCENARIO_OPTION = typer.Option(
    DEFAULT_SCENARIO_ID,
    "--scenario",
    help="Starting scenario id. Use 'list-scenarios' to inspect the available catalog.",
)
COMPARE_SCENARIOS_OPTION = typer.Option(
    None,
    "--scenario",
    help=(
        "Scenario ids to compare. Repeat the option to compare multiple scenarios. "
        "Defaults to all scenarios."
    ),
)
ANIMATION_MATRIX_SCENARIOS_OPTION = typer.Option(
    None,
    "--scenario",
    help=(
        "Scenario ids for broad animation readiness. Repeat to include multiple scenarios. "
        f"Defaults to {', '.join(DEFAULT_ANIMATION_MATRIX_SCENARIOS)}."
    ),
)
DIFFICULTY_OPTION = typer.Option(
    None,
    "--difficulty",
    help="Optional run difficulty override: builder, standard, or founder.",
)
GOAL_OPTION = typer.Option(
    None,
    "--goal",
    help="Optional campaign goal override. Use 'list-goals' to inspect the catalog.",
)
CAMPAIGN_START_OPTION = typer.Option(
    STANDARD_CAMPAIGN_START_ID,
    "--campaign-start",
    help="Campaign start modifier id. Use 'list-campaign-starts' to inspect the catalog.",
)
BALANCE_DIFFICULTY_OPTION = typer.Option(
    DifficultyMode.STANDARD,
    "--difficulty",
    help="Difficulty profile to use for the balance run batch.",
)
BALANCE_GOAL_OPTION = typer.Option(
    CampaignGoalId.PROFIT_MACHINE,
    "--goal",
    help="Campaign goal used during the balance run batch.",
)
CSV_OUTPUT_OPTION = typer.Option(..., "--output", help="CSV path to write.")
BALANCE_REPORT_OUTPUT_OPTION = typer.Option(..., "--output", help="Markdown path to write.")
HEADLESS_2D_OPTION = typer.Option(
    False,
    "--headless",
    help="Run the 2D frontend with SDL dummy drivers and no visible window.",
)
DEFAULT_2D_WINDOW_SIZE = (1440, 900)
DEFAULT_2D_WINDOW_SIZE_TEXT = f"{DEFAULT_2D_WINDOW_SIZE[0]}x{DEFAULT_2D_WINDOW_SIZE[1]}"
WINDOW_SIZE_2D_OPTION = typer.Option(
    DEFAULT_2D_WINDOW_SIZE_TEXT,
    "--window-size",
    help="Visible 2D window size as WIDTHxHEIGHT, for example 820x620.",
)
MAX_FRAMES_2D_OPTION = typer.Option(
    None,
    "--max-frames",
    help="Optional frame cap used for smoke tests and automated verification.",
)
MOTION_MODE_2D_OPTION = typer.Option(
    MotionMode.FULL,
    "--motion-mode",
    help="2D animation intensity mode: full, reduced, or off.",
)
VISUAL_AUDIT_OUTPUT_DIR_OPTION = typer.Option(
    None,
    "--output-dir",
    help="Optional directory for PNG captures. Omit to keep the audit in-memory only.",
)
VISUAL_AUDIT_VIEWPORT_OPTION = typer.Option(
    None,
    "--viewport",
    help=(
        "Optional visual-audit viewport as WIDTHxHEIGHT. Repeat to audit a focused "
        "subset; omit to run the full matrix."
    ),
)
ANIMATION_MATRIX_SEED_OPTION = typer.Option(
    None,
    "--seed",
    help=(
        "Seed for broad animation readiness. Repeat to include multiple seeds. "
        f"Defaults to {', '.join(str(seed) for seed in DEFAULT_ANIMATION_MATRIX_SEEDS)}."
    ),
)
ANIMATION_MATRIX_OUTPUT_OPTION = typer.Option(
    None,
    "--output",
    help="Optional Markdown path for the broad animation readiness matrix artifact.",
)
ANIMATION_PLAYTEST_PREP_OUTPUT_OPTION = typer.Option(
    Path("/tmp/nexus-tech-animation-playtest-prep.md"),
    "--output",
    help="Markdown path for the open-window animation playtest prep artifact.",
)
ANIMATION_PLAYTEST_COMMANDS_OUTPUT_OPTION = typer.Option(
    None,
    "--output",
    help="Optional Markdown path for the manual animation playtest command queue.",
)
ANIMATION_PLAYTEST_RECORDER_QUEUE_OUTPUT_OPTION = typer.Option(
    None,
    "--output",
    help="Optional Markdown path for the manual animation recorder queue.",
)
ANIMATION_PLAYTEST_HANDOFF_OUTPUT_OPTION = typer.Option(
    None,
    "--output",
    help="Optional Markdown path for the manual animation handoff sheet.",
)
ANIMATION_PLAYTEST_ROUTE_BATCH_OUTPUT_OPTION = typer.Option(
    None,
    "--output",
    help="Optional Markdown path for the manual visible-route batch plan.",
)
ANIMATION_PLAYTEST_RECORDER_QUEUE_PATH_ARGUMENT = typer.Argument(
    ...,
    exists=True,
    dir_okay=False,
    help="Manual animation recorder queue Markdown file.",
)
ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT = typer.Argument(
    ...,
    exists=True,
    dir_okay=False,
    help="Manual animation playtest command queue Markdown file.",
)
ANIMATION_PLAYTEST_SESSION_REPORT_OUTPUT_OPTION = typer.Option(
    Path("/tmp/nexus-tech-animation-playtest-report.md"),
    "--report-output",
    help="Markdown path for the strict manual animation playtest report draft.",
)
ANIMATION_PLAYTEST_SESSION_COMMANDS_OUTPUT_OPTION = typer.Option(
    Path("/tmp/nexus-tech-animation-playtest-commands.md"),
    "--commands-output",
    help="Markdown path for the manual animation playtest command queue.",
)
ANIMATION_PLAYTEST_SESSION_PLAN_OUTPUT_OPTION = typer.Option(
    Path("/tmp/nexus-tech-animation-playtest-plan.md"),
    "--plan-output",
    help="Markdown path for the grouped manual animation playtest plan.",
)
ANIMATION_PLAYTEST_SESSION_RECORDER_OUTPUT_OPTION = typer.Option(
    Path("/tmp/nexus-tech-animation-recorder-queue.md"),
    "--recorder-output",
    help="Markdown path for the manual animation recorder queue.",
)
ANIMATION_PLAYTEST_SESSION_ROUTE_BATCH_OUTPUT_OPTION = typer.Option(
    Path("/tmp/nexus-tech-animation-route-batches.md"),
    "--route-batches-output",
    help="Markdown path for the manual visible-route batch plan.",
)
ANIMATION_PLAYTEST_SESSION_TRIAGE_OUTPUT_OPTION = typer.Option(
    Path("/tmp/nexus-tech-animation-ui-triage.md"),
    "--triage-output",
    help="Markdown path for the manual UI/animation triage backlog.",
)
ANIMATION_PLAYTEST_SESSION_RELEASE_GATE_OUTPUT_OPTION = typer.Option(
    Path("/tmp/nexus-tech-animation-release-gate.md"),
    "--release-gate-output",
    help="Markdown path for the manual animation release gate.",
)
ANIMATION_PLAYTEST_SESSION_PROGRESS_OUTPUT_OPTION = typer.Option(
    Path("/tmp/nexus-tech-animation-progress.md"),
    "--progress-output",
    help="Markdown path for the manual animation QA progress board.",
)
ANIMATION_PLAYTEST_SESSION_EXECUTION_GUIDE_OUTPUT_OPTION = typer.Option(
    Path("/tmp/nexus-tech-animation-execution-guide.md"),
    "--execution-guide-output",
    help="Markdown path for the manual animation QA execution guide.",
)
ANIMATION_PLAYTEST_SESSION_ISSUE_BACKLOG_OUTPUT_OPTION = typer.Option(
    Path("/tmp/nexus-tech-animation-issues.md"),
    "--issue-backlog-output",
    help="Markdown path for the manual animation issue backlog.",
)
ANIMATION_PLAYTEST_SESSION_SPRINT_OUTPUT_OPTION = typer.Option(
    Path("/tmp/nexus-tech-animation-sprint.md"),
    "--sprint-output",
    help="Markdown path for the focused manual animation sprint packet.",
)
ANIMATION_PLAYTEST_SESSION_HANDOFF_OUTPUT_OPTION = typer.Option(
    Path("/tmp/nexus-tech-animation-handoff.md"),
    "--handoff-output",
    help="Markdown path for the manual animation handoff sheet.",
)
ANIMATION_PLAYTEST_REPORT_OUTPUT_OPTION = typer.Option(
    Path("/tmp/nexus-tech-animation-playtest-report.md"),
    "--output",
    help="Markdown path for the strict manual animation playtest report draft.",
)
ANIMATION_PLAYTEST_REPORT_METADATA_OPTION = typer.Option(
    "",
    help="Optional metadata value to prefill in the manual animation playtest report draft.",
)
ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT = typer.Argument(
    ...,
    exists=True,
    dir_okay=False,
    help="Completed manual animation playtest report Markdown file.",
)
ANIMATION_PLAYTEST_STATUS_FAIL_OPTION = typer.Option(
    False,
    "--fail-on-incomplete",
    help="Exit with code 1 when the report is not fully signed off.",
)
ANIMATION_PLAYTEST_PLAN_FAIL_OPTION = typer.Option(
    False,
    "--fail-on-incomplete",
    help="Exit with code 1 when the queue or report still has open items.",
)
ANIMATION_PLAYTEST_PLAN_OUTPUT_OPTION = typer.Option(
    None,
    "--output",
    help="Optional Markdown path for the grouped animation playtest plan.",
)
ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION = typer.Option(
    "uv run nexus-tech",
    "--command-prefix",
    help=(
        "Command prefix used in generated manual animation commands. "
        "Use .venv313/bin/nexus-tech when uv is not installed."
    ),
)
ANIMATION_PLAYTEST_PLAN_PATH_ARGUMENT = typer.Argument(
    ...,
    exists=True,
    dir_okay=False,
    help="Exported animation playtest plan Markdown file.",
)
ANIMATION_PLAYTEST_ROUTE_BATCH_PATH_ARGUMENT = typer.Argument(
    ...,
    exists=True,
    dir_okay=False,
    help="Exported animation visible-route batch Markdown file.",
)
ANIMATION_PLAYTEST_ROUTE_BATCH_PATH_OPTION = typer.Option(
    None,
    "--route-batches",
    exists=True,
    dir_okay=False,
    help="Optional exported animation visible-route batch Markdown file.",
)
ANIMATION_PLAYTEST_TRIAGE_PATH_ARGUMENT = typer.Argument(
    ...,
    exists=True,
    dir_okay=False,
    help="Exported animation UI triage Markdown file.",
)
ANIMATION_PLAYTEST_TRIAGE_OUTPUT_OPTION = typer.Option(
    None,
    "--output",
    help="Optional Markdown path for the animation UI triage backlog.",
)
ANIMATION_PLAYTEST_RELEASE_GATE_PATH_ARGUMENT = typer.Argument(
    ...,
    exists=True,
    dir_okay=False,
    help="Exported animation release-gate Markdown file.",
)
ANIMATION_PLAYTEST_RELEASE_GATE_OUTPUT_OPTION = typer.Option(
    None,
    "--output",
    help="Optional Markdown path for the animation release gate.",
)
ANIMATION_PLAYTEST_PROGRESS_PATH_ARGUMENT = typer.Argument(
    ...,
    exists=True,
    dir_okay=False,
    help="Exported animation progress board Markdown file.",
)
ANIMATION_PLAYTEST_PROGRESS_OUTPUT_OPTION = typer.Option(
    None,
    "--output",
    help="Optional Markdown path for the animation progress board.",
)
ANIMATION_PLAYTEST_PROGRESS_PATH_OPTION = typer.Option(
    Path("/tmp/nexus-tech-animation-progress.md"),
    "--progress-path",
    help="Animation progress board path referenced by the execution guide.",
)
ANIMATION_PLAYTEST_EXECUTION_GUIDE_PATH_ARGUMENT = typer.Argument(
    ...,
    exists=True,
    dir_okay=False,
    help="Exported animation execution guide Markdown file.",
)
ANIMATION_PLAYTEST_EXECUTION_GUIDE_OUTPUT_OPTION = typer.Option(
    None,
    "--output",
    help="Optional Markdown path for the animation execution guide.",
)
ANIMATION_PLAYTEST_EXECUTION_GUIDE_PATH_OPTION = typer.Option(
    Path("/tmp/nexus-tech-animation-execution-guide.md"),
    "--execution-guide-path",
    help="Animation execution guide path referenced by the sprint packet.",
)
ANIMATION_PLAYTEST_ISSUE_BACKLOG_PATH_ARGUMENT = typer.Argument(
    ...,
    exists=True,
    dir_okay=False,
    help="Exported animation issue backlog Markdown file.",
)
ANIMATION_PLAYTEST_ISSUE_BACKLOG_OUTPUT_OPTION = typer.Option(
    None,
    "--output",
    help="Optional Markdown path for the animation issue backlog.",
)
ANIMATION_PLAYTEST_ISSUE_BACKLOG_PATH_OPTION = typer.Option(
    Path("/tmp/nexus-tech-animation-issues.md"),
    "--issue-backlog-path",
    help="Animation issue backlog path referenced by the sprint packet.",
)
ANIMATION_PLAYTEST_SPRINT_PATH_ARGUMENT = typer.Argument(
    ...,
    exists=True,
    dir_okay=False,
    help="Exported animation sprint packet Markdown file.",
)
ANIMATION_PLAYTEST_SPRINT_OUTPUT_OPTION = typer.Option(
    None,
    "--output",
    help="Optional Markdown path for the animation sprint packet.",
)
ANIMATION_PLAYTEST_SPRINT_MAX_STEPS_OPTION = typer.Option(
    12,
    "--max-observation-steps",
    min=1,
    help="Maximum open observation rows to include in one sprint packet.",
)
ANIMATION_PLAYTEST_ROUTE_STEP_ARGUMENT = typer.Argument(
    ...,
    min=1,
    help="Visible route step number from the manual animation playtest report.",
)
ANIMATION_PLAYTEST_WINDOW_ARGUMENT = typer.Argument(
    ...,
    help="Window matrix row to update, for example 820x620.",
)
ANIMATION_PLAYTEST_ROW_LABEL_ARGUMENT = typer.Argument(
    ...,
    help="Manual report row label to update, for example 'Pause / Resume'.",
)
ANIMATION_PLAYTEST_FIELD_NAME_ARGUMENT = typer.Argument(
    ...,
    help="Build, release-blocker, or decision field to update.",
)
ANIMATION_PLAYTEST_RESULT_OPTION = typer.Option(
    "pass",
    "--result",
    help="Manual result to record for one route row: pass, watch, or fail.",
)
ANIMATION_PLAYTEST_FULL_RESULT_OPTION = typer.Option(
    "pass",
    "--full",
    help="Manual result for the full-motion window cell: pass, watch, or fail.",
)
ANIMATION_PLAYTEST_REDUCED_RESULT_OPTION = typer.Option(
    "pass",
    "--reduced",
    help="Manual result for the reduced-motion window cell: pass, watch, or fail.",
)
ANIMATION_PLAYTEST_OFF_RESULT_OPTION = typer.Option(
    "pass",
    "--off",
    help="Manual result for the motion-off window cell: pass, watch, or fail.",
)
ANIMATION_PLAYTEST_EVIDENCE_NOTES_OPTION = typer.Option(
    ...,
    "--notes",
    help="Observed manual evidence notes. Generic/template notes are rejected.",
)
ANIMATION_PLAYTEST_READABILITY_NOTES_OPTION = typer.Option(
    ...,
    "--readability-notes",
    help="Observed scene readability notes. Required scene terms are enforced.",
)
ANIMATION_PLAYTEST_MOTION_NOTES_OPTION = typer.Option(
    ...,
    "--motion-notes",
    help="Observed scene motion notes. Required scene motion terms are enforced.",
)
ANIMATION_PLAYTEST_FOLLOW_UP_OPTION = typer.Option(
    "none",
    "--follow-up",
    help="Follow-up owner/date note for non-pass items, or none.",
)
ANIMATION_PLAYTEST_FIELD_VALUE_OPTION = typer.Option(
    ...,
    "--value",
    help="Manual field value to record. Blank/todo/template values are rejected.",
)


def parse_2d_window_size(value: str) -> tuple[int, int]:
    """Parse a WIDTHxHEIGHT string into a safe 2D frontend window size."""

    normalized = value.strip().lower()
    parts = normalized.split("x")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise ValueError("Use WIDTHxHEIGHT, for example 820x620.")
    width, height = (int(parts[0]), int(parts[1]))
    if width < 640 or height < 480:
        raise ValueError("2D window size must be at least 640x480.")
    return (width, height)


def resolve_2d_window_size(value: str) -> tuple[int, int]:
    """Return a parsed 2D window size or exit with a user-facing error."""

    try:
        return parse_2d_window_size(value)
    except ValueError as error:
        console.print(
            Panel.fit(
                str(error),
                title="Invalid 2D Window Size",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from error


def resolve_2d_visual_audit_viewports(
    values: list[str] | None,
) -> tuple[tuple[int, int], ...] | None:
    """Parse optional visual-audit viewport overrides without changing the default matrix."""

    if not values:
        return None
    try:
        return tuple(parse_2d_window_size(value) for value in values)
    except ValueError as error:
        console.print(
            Panel.fit(
                str(error),
                title="Invalid Visual Audit Viewport",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from error


ACTION_KEYS = {
    "1": TurnAction.CREATE_PRODUCT,
    "2": TurnAction.IMPROVE_QUALITY,
    "3": TurnAction.ADD_FEATURE,
    "4": TurnAction.REDUCE_TECHNICAL_DEBT,
    "5": TurnAction.MARKET_PRODUCT,
    "6": TurnAction.ADJUST_PRICING,
    "7": TurnAction.SET_PACKAGING_STRATEGY,
    "8": TurnAction.SET_TARGET_SEGMENT,
    "9": TurnAction.SUNSET_PRODUCT,
    "10": TurnAction.SET_COMPANY_STRATEGY,
    "11": TurnAction.SET_ROADMAP,
    "12": TurnAction.SET_BUDGET_STANCE,
    "13": TurnAction.TAKE_LOAN,
    "14": TurnAction.RAISE_ANGEL,
    "15": TurnAction.RAISE_VC,
    "16": TurnAction.REPAY_DEBT,
    "17": TurnAction.REVIEW_FINANCE,
    "78": TurnAction.REFINANCE_DEBT,
    "84": TurnAction.DEBT_ROLLOVER,
    "80": TurnAction.REBALANCE_CAPITAL,
    "83": TurnAction.RAISE_RESERVE_TARGET,
    "97": TurnAction.STEP_UP_RESERVE_DISCIPLINE,
    "100": TurnAction.HARDEN_FINANCING_POSTURE,
    "103": TurnAction.LOCK_CAPITAL_BUFFER,
    "18": TurnAction.HIRE_EMPLOYEE,
    "19": TurnAction.FIRE_EMPLOYEE,
    "20": TurnAction.ASSIGN_EMPLOYEE,
    "21": TurnAction.UNASSIGN_EMPLOYEE,
    "22": TurnAction.ASSIGN_MANAGER,
    "23": TurnAction.CLEAR_MANAGER,
    "24": TurnAction.REST_TEAM,
    "25": TurnAction.REVIEW_TEAM,
    "26": TurnAction.REVIEW_CUSTOMERS,
    "27": TurnAction.INVEST_IN_CUSTOMER_SUCCESS,
    "28": TurnAction.RUN_RETENTION_PLAY,
    "29": TurnAction.TRAIN_EMPLOYEE,
    "30": TurnAction.PROMOTE_EMPLOYEE,
    "31": TurnAction.APPOINT_TEAM_LEAD,
    "75": TurnAction.RUN_COMP_REVIEW,
    "76": TurnAction.RUN_SUCCESSION_REVIEW,
    "32": TurnAction.ROUTE_SUPPORT_ESCALATION,
    "79": TurnAction.RUN_ACCOUNT_RESCUE,
    "81": TurnAction.RUN_LANE_RECOVERY,
    "85": TurnAction.RUN_RENEWAL_SWEEP,
    "87": TurnAction.RUN_ENTERPRISE_ASSURANCE,
    "89": TurnAction.RUN_BILLING_STABILIZATION,
    "91": TurnAction.RUN_ONBOARDING_RECOVERY,
    "93": TurnAction.RUN_REFERENCE_RESCUE,
    "95": TurnAction.RUN_ONBOARDING_FAST_TRACK,
    "98": TurnAction.RUN_ENTERPRISE_QUEUE_RESET,
    "101": TurnAction.RUN_WHITE_GLOVE_RECOVERY,
    "108": TurnAction.RUN_WHITE_GLOVE_BACKSTOP,
    "112": TurnAction.RUN_WHITE_GLOVE_RENEWAL_GUARD,
    "117": TurnAction.RUN_WHITE_GLOVE_REFERENCE_RING,
    "119": TurnAction.RUN_WHITE_GLOVE_REFERENCE_COMMITTEE,
    "122": TurnAction.RUN_WHITE_GLOVE_ESCALATION_CELL,
    "126": TurnAction.RUN_WHITE_GLOVE_REFERENCE_BUREAU,
    "130": TurnAction.RUN_ENTERPRISE_COMMITMENT_BOARD,
    "135": TurnAction.RUN_ENTERPRISE_REFERENCE_CHAMBER,
    "140": TurnAction.RUN_ENTERPRISE_REFERENCE_FORUM,
    "145": TurnAction.RUN_WHITE_GLOVE_REFERENCE_EXCHANGE,
    "150": TurnAction.RUN_ENTERPRISE_REFERENCE_LATTICE,
    "155": TurnAction.RUN_ENTERPRISE_REFERENCE_SUMMIT,
    "160": TurnAction.RUN_ENTERPRISE_REFERENCE_DIRECTORATE,
    "165": TurnAction.RUN_ENTERPRISE_REFERENCE_SECRETARIAT,
    "170": TurnAction.RUN_ENTERPRISE_REFERENCE_AUTHORITY,
    "175": TurnAction.RUN_ENTERPRISE_REFERENCE_COMMISSION,
    "180": TurnAction.RUN_ENTERPRISE_REFERENCE_OVERSIGHT,
    "185": TurnAction.RUN_ENTERPRISE_REFERENCE_COUNCIL,
    "190": TurnAction.RUN_ENTERPRISE_LANE_MESH,
    "104": TurnAction.RUN_ENTERPRISE_REFERENCE_CYCLE,
    "115": TurnAction.RUN_ENTERPRISE_RENEWAL_CABINET,
    "105": TurnAction.RUN_BILLING_RETENTION_RESET,
    "120": TurnAction.RUN_BILLING_COVENANT_RESET,
    "123": TurnAction.RUN_BILLING_DISPUTE_DESK,
    "127": TurnAction.RUN_BILLING_DISPUTE_CABINET,
    "131": TurnAction.RUN_BILLING_COLLECTION_BRIDGE,
    "136": TurnAction.RUN_BILLING_COLLECTION_OFFICE,
    "141": TurnAction.RUN_BILLING_SETTLEMENT_BOARD,
    "146": TurnAction.RUN_BILLING_CASH_WAR_ROOM,
    "151": TurnAction.RUN_BILLING_LIQUIDITY_COMMAND,
    "156": TurnAction.RUN_BILLING_LIQUIDITY_SUMMIT,
    "161": TurnAction.RUN_BILLING_LIQUIDITY_DIRECTORATE,
    "166": TurnAction.RUN_BILLING_LIQUIDITY_SECRETARIAT,
    "171": TurnAction.RUN_BILLING_LIQUIDITY_AUTHORITY,
    "176": TurnAction.RUN_BILLING_LIQUIDITY_COMMISSION,
    "181": TurnAction.RUN_BILLING_LIQUIDITY_OVERSIGHT,
    "186": TurnAction.RUN_BILLING_LIQUIDITY_COUNCIL,
    "191": TurnAction.RUN_BILLING_LANE_MESH,
    "124": TurnAction.RUN_ONBOARDING_CONTROL_TOWER,
    "128": TurnAction.RUN_ONBOARDING_LAUNCH_CELL,
    "132": TurnAction.RUN_ONBOARDING_ADOPTION_HUB,
    "137": TurnAction.RUN_ONBOARDING_STABILITY_BOARD,
    "142": TurnAction.RUN_ONBOARDING_RETENTION_MESH,
    "147": TurnAction.RUN_ONBOARDING_ASSURANCE_GRID,
    "152": TurnAction.RUN_ONBOARDING_DURABILITY_MESH,
    "157": TurnAction.RUN_ONBOARDING_CONTINUITY_LATTICE,
    "162": TurnAction.RUN_ONBOARDING_CONTINUITY_BUREAU,
    "167": TurnAction.RUN_ONBOARDING_CONTINUITY_SECRETARIAT,
    "172": TurnAction.RUN_ONBOARDING_CONTINUITY_AUTHORITY,
    "177": TurnAction.RUN_ONBOARDING_CONTINUITY_COMMISSION,
    "182": TurnAction.RUN_ONBOARDING_CONTINUITY_OVERSIGHT,
    "187": TurnAction.RUN_ONBOARDING_CONTINUITY_COUNCIL,
    "192": TurnAction.RUN_ONBOARDING_LANE_MESH,
    "33": TurnAction.RUN_ADD_ON_CAMPAIGN,
    "34": TurnAction.RUN_PACKAGE_MIGRATION,
    "35": TurnAction.EXECUTE_RESTRUCTURE_PLAN,
    "36": TurnAction.SET_FUNCTIONAL_BUDGET,
    "37": TurnAction.UPGRADE_SUPPORT_PROGRAM,
    "38": TurnAction.PLAN_RELEASE,
    "39": TurnAction.WORK_RELEASE,
    "40": TurnAction.CREATE_SALES_DEAL,
    "41": TurnAction.ADVANCE_SALES_DEAL,
    "42": TurnAction.START_ROADMAP_PROJECT,
    "43": TurnAction.WORK_ROADMAP_PROJECT,
    "44": TurnAction.REVIEW_PIPELINE,
    "45": TurnAction.VIEW_REPORT,
    "46": TurnAction.WAIT,
    "47": TurnAction.VIEW_STATUS,
    "48": TurnAction.END_TURN,
    "49": TurnAction.SOURCE_CANDIDATES,
    "50": TurnAction.SCREEN_CANDIDATE,
    "51": TurnAction.INTERVIEW_CANDIDATE,
    "52": TurnAction.MAKE_HIRING_OFFER,
    "53": TurnAction.TRIAGE_SUPPORT_BACKLOG,
    "54": TurnAction.REVIEW_BOARD,
    "55": TurnAction.RUN_PRICE_INCREASE,
    "56": TurnAction.REORG_TEAM,
    "57": TurnAction.EXECUTE_BOARD_RESPONSE,
    "58": TurnAction.START_BOARD_RECOVERY_PLAN,
    "59": TurnAction.INVEST_IN_SUPPORT_STAFFING,
    "60": TurnAction.EXPAND_PACKAGE_CATALOG,
    "61": TurnAction.EXPAND_ADD_ON_CATALOG,
    "62": TurnAction.MAKE_RENEWAL_OFFER,
    "63": TurnAction.RUN_WIN_BACK_PLAY,
    "64": TurnAction.SET_SUPPORT_LANE_FOCUS,
    "70": TurnAction.CREATE_PARTNERSHIP,
    "71": TurnAction.INVEST_IN_PARTNER_ENABLEMENT,
    "86": TurnAction.RUN_CHANNEL_QBR,
    "88": TurnAction.REBALANCE_CHANNEL_MIX,
    "90": TurnAction.RUN_PARTNER_RECOVERY_SPRINT,
    "92": TurnAction.RUN_CHANNEL_FIREBREAK,
    "94": TurnAction.RUN_CHANNEL_CONFLICT_RESET,
    "96": TurnAction.RUN_CHANNEL_REALIGNMENT,
    "99": TurnAction.RUN_CHANNEL_SYNERGY_RESET,
    "102": TurnAction.RUN_PARTNER_MARGIN_RESET,
    "106": TurnAction.RUN_CHANNEL_STABILITY_RESET,
    "133": TurnAction.RUN_CHANNEL_DEPENDENCY_RESET,
    "138": TurnAction.RUN_CHANNEL_CONFIDENCE_FIREWALL,
    "143": TurnAction.RUN_CHANNEL_DURABILITY_MESH,
    "148": TurnAction.RUN_CHANNEL_CONFLICT_LATTICE,
    "153": TurnAction.RUN_CHANNEL_RESILIENCE_GRID,
    "158": TurnAction.RUN_CHANNEL_CONTINUITY_MATRIX,
    "163": TurnAction.RUN_CHANNEL_ASSURANCE_COVENANT,
    "168": TurnAction.RUN_CHANNEL_DURABILITY_STATUTE,
    "173": TurnAction.RUN_CHANNEL_DURABILITY_MANDATE,
    "178": TurnAction.RUN_CHANNEL_DURABILITY_COMMISSION,
    "183": TurnAction.RUN_CHANNEL_DURABILITY_OVERSIGHT,
    "188": TurnAction.RUN_CHANNEL_DURABILITY_COUNCIL,
    "193": TurnAction.RUN_WHITE_GLOVE_LANE_MESH,
    "109": TurnAction.RUN_RESELLER_ENABLEMENT_RESET,
    "113": TurnAction.RUN_INTEGRATION_CUTOVER_RESET,
    "110": TurnAction.RUN_MARKETPLACE_CHARGEBACK_RESET,
    "72": TurnAction.REVIEW_PARTNERSHIPS,
    "73": TurnAction.SET_CAPITAL_PLAN,
    "107": TurnAction.SET_REFINANCING_POSTURE,
    "111": TurnAction.SET_COVENANT_FIREWALL,
    "114": TurnAction.SET_DEBT_STRATEGY,
    "116": TurnAction.SET_GROWTH_FIREBREAK,
    "118": TurnAction.SET_PATH_CAPITAL_POSTURE,
    "121": TurnAction.SET_ENDGAME_CAPITAL_MAP,
    "125": TurnAction.SET_EXIT_READINESS_BUFFER,
    "129": TurnAction.SET_TERMINAL_LIQUIDITY_CONTROLS,
    "134": TurnAction.SET_CAPITAL_REALLOCATION_GRID,
    "139": TurnAction.SET_PATH_CONTROL_MATRIX,
    "144": TurnAction.SET_PATH_RESILIENCE_GRID,
    "149": TurnAction.SET_BALANCE_SHEET_RECOVERY_MESH,
    "154": TurnAction.SET_TERMINAL_RECOVERY_LATTICE,
    "159": TurnAction.SET_TERMINAL_CONTINUITY_MATRIX,
    "164": TurnAction.SET_TERMINAL_RESILIENCE_COVENANT,
    "169": TurnAction.SET_TERMINAL_SOLVENCY_STATUTE,
    "174": TurnAction.SET_TERMINAL_SOLVENCY_MANDATE,
    "179": TurnAction.SET_TERMINAL_SOLVENCY_COMMISSION,
    "184": TurnAction.SET_TERMINAL_SOLVENCY_OVERSIGHT,
    "189": TurnAction.SET_TERMINAL_SOLVENCY_COUNCIL,
    "194": TurnAction.SET_PATH_CASH_WATERFALL,
    "195": TurnAction.RUN_ENTERPRISE_REFERENCE_WATCH,
    "196": TurnAction.RUN_BILLING_RENEWAL_WATCH,
    "197": TurnAction.RUN_ONBOARDING_GO_LIVE_WATCH,
    "198": TurnAction.RUN_WHITE_GLOVE_RETENTION_WATCH,
    "199": TurnAction.SET_BOARD_RESET_CONTINGENCY_BUFFER,
    "74": TurnAction.RENEGOTIATE_PARTNERSHIP,
    "77": TurnAction.REACTIVATE_PARTNERSHIP,
    "82": TurnAction.PAUSE_PARTNERSHIP,
}
UTILITY_ACTION_KEYS = {
    "65": "save_game",
    "66": "load_game",
    "67": "show_guide",
    "68": "show_glossary",
    "69": "show_tutorial",
}
ALL_MENU_KEYS = list(ACTION_KEYS) + list(UTILITY_ACTION_KEYS)

PRODUCT_TARGETED_ACTIONS = {
    TurnAction.IMPROVE_QUALITY,
    TurnAction.ADD_FEATURE,
    TurnAction.REDUCE_TECHNICAL_DEBT,
    TurnAction.MARKET_PRODUCT,
    TurnAction.ADJUST_PRICING,
    TurnAction.RUN_PRICE_INCREASE,
    TurnAction.EXPAND_PACKAGE_CATALOG,
    TurnAction.EXPAND_ADD_ON_CATALOG,
    TurnAction.RUN_ADD_ON_CAMPAIGN,
    TurnAction.RUN_PACKAGE_MIGRATION,
    TurnAction.SET_PACKAGING_STRATEGY,
    TurnAction.SET_TARGET_SEGMENT,
    TurnAction.SUNSET_PRODUCT,
}


@app.callback(invoke_without_command=True)
def root(
    ctx: typer.Context,
    company_name: Optional[str] = typer.Option(  # noqa: UP045
        None,
        "--company-name",
        help="Company display name override. Defaults to the scenario's company name.",
    ),
    product_name: Optional[str] = typer.Option(  # noqa: UP045
        None,
        "--product-name",
        help="Primary product name override. Applies to the first scenario product.",
    ),
    scenario: str = SCENARIO_OPTION,
    campaign_start: str = CAMPAIGN_START_OPTION,
    difficulty: DifficultyMode | None = DIFFICULTY_OPTION,
    goal: CampaignGoalId | None = GOAL_OPTION,
    seed: Optional[int] = typer.Option(  # noqa: UP045
        None,
        "--seed",
        help=f"Seed for reproducible simulation and demo runs, for example {DEMO_SEED_EXAMPLE}.",
    ),
    db_path: Path = DB_PATH_OPTION,
    slot: str = typer.Option(DEFAULT_SAVE_SLOT, "--slot", help="Default save slot name."),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug logging and rich tracebacks for development runs.",
    ),
    version: bool = typer.Option(  # noqa: FBT001
        False,
        "--version",
        callback=show_version_callback,
        is_eager=True,
        help="Show the installed NEXUS TECH version and exit.",
    ),
) -> None:
    """Start a new local game when no subcommand is given."""

    configure_cli(debug=debug)
    ctx.obj = {"debug": debug}

    if ctx.invoked_subcommand is not None:
        return
    start_new_game(
        company_name=company_name,
        product_name=product_name,
        scenario_id=scenario,
        campaign_start_id=campaign_start,
        difficulty_mode=difficulty,
        campaign_goal_id=goal,
        seed=seed,
        db_path=db_path,
        slot_name=slot,
    )


@app.command("new-game")
def new_game_command(
    company_name: Optional[str] = typer.Option(  # noqa: UP045
        None,
        "--company-name",
        help="Company display name override. Defaults to the scenario's company name.",
    ),
    product_name: Optional[str] = typer.Option(  # noqa: UP045
        None,
        "--product-name",
        help="Primary product name override. Applies to the first scenario product.",
    ),
    scenario: str = SCENARIO_OPTION,
    campaign_start: str = CAMPAIGN_START_OPTION,
    difficulty: DifficultyMode | None = DIFFICULTY_OPTION,
    goal: CampaignGoalId | None = GOAL_OPTION,
    seed: Optional[int] = typer.Option(  # noqa: UP045
        None,
        "--seed",
        help=f"Seed for reproducible simulation and demo runs, for example {DEMO_SEED_EXAMPLE}.",
    ),
    db_path: Path = DB_PATH_OPTION,
    slot: str = typer.Option(DEFAULT_SAVE_SLOT, "--slot", help="Default save slot name."),
) -> None:
    """Start a brand new local game."""

    start_new_game(
        company_name=company_name,
        product_name=product_name,
        scenario_id=scenario,
        campaign_start_id=campaign_start,
        difficulty_mode=difficulty,
        campaign_goal_id=goal,
        seed=seed,
        db_path=db_path,
        slot_name=slot,
    )


@app.command("play", hidden=True)
def play_alias(
    company_name: Optional[str] = typer.Option(  # noqa: UP045
        None,
        "--company-name",
        help="Company display name override. Defaults to the scenario's company name.",
    ),
    product_name: Optional[str] = typer.Option(  # noqa: UP045
        None,
        "--product-name",
        help="Primary product name override. Applies to the first scenario product.",
    ),
    scenario: str = SCENARIO_OPTION,
    campaign_start: str = CAMPAIGN_START_OPTION,
    difficulty: DifficultyMode | None = DIFFICULTY_OPTION,
    goal: CampaignGoalId | None = GOAL_OPTION,
    seed: Optional[int] = typer.Option(  # noqa: UP045
        None,
        "--seed",
        help=f"Seed for reproducible simulation and demo runs, for example {DEMO_SEED_EXAMPLE}.",
    ),
    db_path: Path = DB_PATH_OPTION,
    slot: str = typer.Option(DEFAULT_SAVE_SLOT, "--slot", help="Default save slot name."),
) -> None:
    """Backward-compatible alias for starting a new game."""

    start_new_game(
        company_name=company_name,
        product_name=product_name,
        scenario_id=scenario,
        campaign_start_id=campaign_start,
        difficulty_mode=difficulty,
        campaign_goal_id=goal,
        seed=seed,
        db_path=db_path,
        slot_name=slot,
    )


@app.command("play-2d")
def play_2d_command(
    company_name: Optional[str] = typer.Option(  # noqa: UP045
        None,
        "--company-name",
        help="Company display name override. Defaults to the scenario's company name.",
    ),
    product_name: Optional[str] = typer.Option(  # noqa: UP045
        None,
        "--product-name",
        help="Primary product name override. Applies to the first scenario product.",
    ),
    scenario: str = SCENARIO_OPTION,
    campaign_start: str = CAMPAIGN_START_OPTION,
    difficulty: DifficultyMode | None = DIFFICULTY_OPTION,
    goal: CampaignGoalId | None = GOAL_OPTION,
    seed: Optional[int] = typer.Option(  # noqa: UP045
        None,
        "--seed",
        help=f"Seed for reproducible simulation and demo runs, for example {DEMO_SEED_EXAMPLE}.",
    ),
    db_path: Path = DB_PATH_OPTION,
    slot: str = typer.Option(DEFAULT_SAVE_SLOT, "--slot", help="Default save slot name."),
    headless: bool = HEADLESS_2D_OPTION,
    window_size: str = WINDOW_SIZE_2D_OPTION,
    max_frames: int | None = MAX_FRAMES_2D_OPTION,
    motion_mode: MotionMode = MOTION_MODE_2D_OPTION,
) -> None:
    """Launch the lightweight 2D dashboard frontend for a new run."""

    start_new_game_2d(
        company_name=company_name,
        product_name=product_name,
        scenario_id=scenario,
        campaign_start_id=campaign_start,
        difficulty_mode=difficulty,
        campaign_goal_id=goal,
        seed=seed,
        db_path=db_path,
        slot_name=slot,
        headless=headless,
        window_size=resolve_2d_window_size(window_size),
        max_frames=max_frames,
        motion_mode=motion_mode,
    )


@app.command("audit-2d-motion")
def audit_2d_motion_command(
    scenario: str = SCENARIO_OPTION,
    difficulty: DifficultyMode | None = DIFFICULTY_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed for deterministic 2D motion audit setup.",
    ),
    frames: int = typer.Option(
        90,
        "--frames",
        min=1,
        help="Number of fixed-timestep frames to render per scene and viewport.",
    ),
    motion_mode: MotionMode = MOTION_MODE_2D_OPTION,
) -> None:
    """Run a deterministic headless 2D animation stability audit."""

    try:
        report = run_2d_motion_audit(
            scenario_id=scenario,
            difficulty_mode=difficulty,
            seed=seed,
            frames=frames,
            motion_mode=motion_mode,
        )
    except Frontend2DUnavailableError as error:
        console.print(
            Panel.fit(
                str(error),
                title="2D Frontend Unavailable",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from error

    table = Table(
        title=(
            "2D Motion Audit | "
            f"{report.scenario_id} | {report.difficulty} | "
            f"seed {report.seed} | motion {report.motion_mode}"
        )
    )
    table.add_column("Viewport", style="cyan")
    table.add_column("Run Pulses", justify="right")
    table.add_column("Summary Pulses", justify="right")
    table.add_column("Title/Review", justify="right")
    table.add_column("Inspector/Long", justify="right")
    table.add_column("Avg Frame", justify="right")
    table.add_column("Max Frame", justify="right")
    table.add_column("Status", justify="center")
    table.add_column("Notes")
    for cell in report.cells:
        table.add_row(
            f"{cell.width}x{cell.height}",
            f"{cell.run_before_pulses} -> {cell.run_after_pulses}",
            f"{cell.summary_before_pulses} -> {cell.summary_after_pulses}",
            (
                f"T {cell.title_before_pulses}->{cell.title_after_pulses} / "
                f"R {cell.review_before_pulses}->{cell.review_after_pulses}"
            ),
            (
                f"I {cell.inspector_before_pulses}->{cell.inspector_after_pulses} / "
                f"L {cell.long_run_before_pulses}->{cell.long_run_after_pulses}"
            ),
            f"{cell.average_frame_ms:.2f} ms",
            f"{cell.max_frame_ms:.2f} ms",
            cell.status.upper(),
            cell.notes,
        )
    console.print(table)

    flow = report.flow_report
    if flow.findings:
        flow_table = Table(title="2D Flow Request Path Findings")
        flow_table.add_column("Surface", style="cyan")
        flow_table.add_column("Command")
        flow_table.add_column("Detail")
        for finding in flow.findings[:12]:
            flow_table.add_row(finding.surface, finding.command, finding.detail)
        console.print(flow_table)
    else:
        console.print(
            Panel.fit(
                (
                    "2D flow request paths: PASS "
                    f"({flow.command_count} commands, "
                    f"{flow.inspector_action_count} inspector actions)."
                ),
                title="2D Flow Audit",
                border_style="green",
            )
        )

    border_style = "green" if report.status == "pass" else "yellow"
    if report.status == "fail":
        border_style = "red"
    console.print(
        Panel.fit(
            f"Motion audit status: {report.status.upper()} across {len(report.cells)} viewports.",
            title="2D Motion Audit",
            border_style=border_style,
        )
    )
    if report.status == "fail":
        raise typer.Exit(code=1)


@app.command("audit-2d-visual")
def audit_2d_visual_command(
    scenario: str = SCENARIO_OPTION,
    difficulty: DifficultyMode | None = DIFFICULTY_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed for deterministic 2D visual audit setup.",
    ),
    motion_mode: MotionMode = MOTION_MODE_2D_OPTION,
    output_dir: Path | None = VISUAL_AUDIT_OUTPUT_DIR_OPTION,
    viewport: list[str] | None = VISUAL_AUDIT_VIEWPORT_OPTION,
) -> None:
    """Capture deterministic 2D scene frames and verify visual/motion layers."""

    sizes = resolve_2d_visual_audit_viewports(viewport)
    try:
        audit_kwargs = dict(
            scenario_id=scenario,
            difficulty_mode=difficulty,
            seed=seed,
            motion_mode=motion_mode,
            output_dir=output_dir,
        )
        if sizes is not None:
            audit_kwargs["sizes"] = sizes
        report = run_2d_visual_audit(**audit_kwargs)
    except Frontend2DUnavailableError as error:
        console.print(
            Panel.fit(
                str(error),
                title="2D Frontend Unavailable",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from error

    table = Table(
        title=(
            "2D Visual Audit | "
            f"{report.scenario_id} | {report.difficulty} | "
            f"seed {report.seed} | motion {report.motion_mode}"
        )
    )
    table.add_column("Scene", style="cyan")
    table.add_column("Viewport", justify="right")
    table.add_column("Checksum", justify="right")
    table.add_column("Colors", justify="right")
    table.add_column("Contrast", justify="right")
    table.add_column("Clutter", justify="right")
    table.add_column("Bright", justify="right")
    table.add_column("Layers")
    table.add_column("Status", justify="center")
    table.add_column("Notes")
    for cell in report.cells:
        table.add_row(
            cell.scene_key,
            f"{cell.width}x{cell.height}",
            str(cell.checksum),
            str(cell.unique_color_samples),
            str(cell.luminance_spread),
            f"{cell.edge_density:.2f}",
            f"{cell.bright_ratio:.2f}",
            ",".join(cell.active_layers),
            cell.status.upper(),
            cell.notes,
        )
    console.print(table)
    if report.output_dir is not None:
        console.print(
            Panel.fit(
                f"PNG captures and viewport contact sheets written to {report.output_dir}",
                title="2D Visual Captures",
                border_style="cyan",
            )
        )

    border_style = "green" if report.status == "pass" else "red"
    console.print(
        Panel.fit(
            (
                f"Visual audit status: {report.status.upper()} across "
                f"{len(report.cells)} captures. Baseline {report.baseline_signature}."
            ),
            title="2D Visual Audit",
            border_style=border_style,
        )
    )
    if report.status == "fail":
        raise typer.Exit(code=1)


@app.command("audit-2d-animation")
def audit_2d_animation_command(
    scenario: str = SCENARIO_OPTION,
    difficulty: DifficultyMode | None = DIFFICULTY_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed for deterministic 2D animation completeness audit setup.",
    ),
    frames: int = typer.Option(
        1,
        "--frames",
        min=1,
        help="Number of fixed-timestep frames for the embedded motion gates.",
    ),
) -> None:
    """Run the combined 2D animation completeness gate."""

    try:
        report = run_2d_animation_audit(
            scenario_id=scenario,
            difficulty_mode=difficulty,
            seed=seed,
            frames=frames,
        )
    except Frontend2DUnavailableError as error:
        console.print(
            Panel.fit(
                str(error),
                title="2D Frontend Unavailable",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from error

    table = Table(
        title=(
            f"2D Animation Audit | {report.scenario_id} | {report.difficulty} | seed {report.seed}"
        )
    )
    table.add_column("Area", style="cyan", no_wrap=True)
    table.add_column("Required")
    table.add_column("Active")
    table.add_column("Status", justify="center")
    table.add_column("Notes")
    for cell in report.cells:
        status_text = cell.status.upper()
        table.add_row(
            cell.area,
            ",".join(cell.required_layers),
            ",".join(cell.active_layers),
            status_text,
            cell.notes,
        )
    console.print(table)

    if report.advisory_gaps:
        console.print(
            Panel.fit(
                "\n".join(f"- {gap}" for gap in report.advisory_gaps),
                title="Animation Advisory Gaps",
                border_style="yellow",
            )
        )

    border_style = "green" if report.status == "pass" else "red"
    console.print(
        Panel.fit(
            (
                f"Animation audit status: {report.status.upper()}. "
                f"Visual baseline {report.visual_report.baseline_signature}."
            ),
            title="2D Animation Audit",
            border_style=border_style,
        )
    )
    if report.status == "fail":
        raise typer.Exit(code=1)


@app.command("audit-2d-animation-matrix")
def audit_2d_animation_matrix_command(
    scenario: Optional[list[str]] = ANIMATION_MATRIX_SCENARIOS_OPTION,
    difficulty: DifficultyMode | None = DIFFICULTY_OPTION,
    seed: Optional[list[int]] = ANIMATION_MATRIX_SEED_OPTION,
    output: Path | None = ANIMATION_MATRIX_OUTPUT_OPTION,
    frames: int = typer.Option(
        1,
        "--frames",
        min=1,
        help="Number of fixed-timestep frames for each embedded motion gate.",
    ),
) -> None:
    """Run broad 2D animation readiness across multiple scenarios and seeds."""

    scenario_ids = tuple(scenario) if scenario is not None else DEFAULT_ANIMATION_MATRIX_SCENARIOS
    for scenario_id in scenario_ids:
        validate_scenario_id(scenario_id)
    seeds = tuple(seed) if seed is not None else DEFAULT_ANIMATION_MATRIX_SEEDS
    try:
        report = run_2d_animation_matrix_audit(
            scenario_ids=scenario_ids,
            difficulty_mode=difficulty,
            seeds=seeds,
            frames=frames,
        )
    except Frontend2DUnavailableError as error:
        console.print(
            Panel.fit(
                str(error),
                title="2D Frontend Unavailable",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from error

    table = Table(
        title=(
            "2D Animation Matrix | "
            f"{len(report.scenario_ids)} scenarios | {len(report.seeds)} seeds | "
            f"{report.difficulty}"
        )
    )
    table.add_column("Scenario", style="cyan")
    table.add_column("Seed", justify="right")
    table.add_column("Baseline")
    table.add_column("Status", justify="center")
    table.add_column("Failed Areas")
    table.add_column("Advisory")
    for cell in report.cells:
        table.add_row(
            cell.scenario_id,
            str(cell.seed),
            cell.visual_baseline,
            cell.status.upper(),
            ", ".join(cell.failed_areas) if cell.failed_areas else "-",
            str(len(cell.advisory_gaps)),
        )
    console.print(table)

    border_style = "green" if report.status == "pass" else "red"
    console.print(
        Panel.fit(
            (
                f"Animation matrix status: {report.status.upper()} across "
                f"{len(report.cells)} scenario/seed cells."
            ),
            title="2D Animation Matrix",
            border_style=border_style,
        )
    )
    if output is not None:
        write_2d_animation_matrix_report(report, output)
        console.print(
            Panel.fit(
                f"Animation matrix report written to {output}",
                title="2D Animation Matrix Artifact",
                border_style="cyan",
            )
        )
    if report.status == "fail":
        raise typer.Exit(code=1)


@app.command("prepare-2d-animation-playtest")
def prepare_2d_animation_playtest_command(
    scenario: Optional[list[str]] = ANIMATION_MATRIX_SCENARIOS_OPTION,
    difficulty: DifficultyMode | None = DIFFICULTY_OPTION,
    seed: Optional[list[int]] = ANIMATION_MATRIX_SEED_OPTION,
    output: Path = ANIMATION_PLAYTEST_PREP_OUTPUT_OPTION,
    frames: int = typer.Option(
        1,
        "--frames",
        min=1,
        help="Number of fixed-timestep frames for each embedded matrix gate.",
    ),
) -> None:
    """Prepare the automated evidence and checklist for manual 2D animation playtest."""

    scenario_ids = tuple(scenario) if scenario is not None else DEFAULT_ANIMATION_MATRIX_SCENARIOS
    for scenario_id in scenario_ids:
        validate_scenario_id(scenario_id)
    seeds = tuple(seed) if seed is not None else DEFAULT_ANIMATION_MATRIX_SEEDS
    try:
        matrix_report = run_2d_animation_matrix_audit(
            scenario_ids=scenario_ids,
            difficulty_mode=difficulty,
            seeds=seeds,
            frames=frames,
        )
    except Frontend2DUnavailableError as error:
        console.print(
            Panel.fit(
                str(error),
                title="2D Frontend Unavailable",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from error

    prep_report = build_2d_animation_playtest_prep_report(
        version=__version__,
        matrix_report=matrix_report,
    )
    write_2d_animation_playtest_prep_report(prep_report, output)
    passed = sum(1 for cell in matrix_report.cells if cell.status == "pass")

    table = Table(title="2D Animation Playtest Prep")
    table.add_column("Window", style="cyan")
    table.add_column("Full")
    table.add_column("Reduced")
    table.add_column("Off")
    for width, height in prep_report.windows:
        table.add_row(f"{width}x{height}", "todo", "todo", "todo")
    console.print(table)

    controls_table = Table(title="Manual Control Clarity Gate")
    controls_table.add_column("Control", style="cyan")
    controls_table.add_column("Required Check")
    controls_table.add_column("Result", justify="center")
    for area, required_check in prep_report.control_checks:
        controls_table.add_row(area, required_check, "todo")
    console.print(controls_table)

    scenes_table = Table(title="Manual Scene Animation Gate")
    scenes_table.add_column("Scene", style="cyan")
    scenes_table.add_column("Required Check")
    scenes_table.add_column("Result", justify="center")
    for scene, required_check in prep_report.scene_checks:
        scenes_table.add_row(scene, required_check, "todo")
    console.print(scenes_table)

    feedback_table = Table(title="Manual Game Feel Gate")
    feedback_table.add_column("Feedback", style="cyan")
    feedback_table.add_column("Required Check")
    feedback_table.add_column("Result", justify="center")
    for area, required_check in prep_report.feedback_checks:
        feedback_table.add_row(area, required_check, "todo")
    console.print(feedback_table)

    border_style = "green" if prep_report.status == "ready" else "red"
    console.print(
        Panel.fit(
            (
                f"Status {prep_report.status.upper()} | Matrix {matrix_report.status.upper()} "
                f"| {passed}/{len(matrix_report.cells)} pass | Manual signoff required"
            ),
            title="2D Animation Playtest Prep",
            border_style=border_style,
        )
    )
    console.print(
        Panel.fit(
            "Finish the checklist before marking animation complete.",
            title="Manual Signoff Required",
            border_style="yellow",
        )
    )
    console.print(
        Panel.fit(
            f"Animation playtest prep report written to {output}",
            title="2D Animation Playtest Artifact",
            border_style="cyan",
        )
    )
    if prep_report.status != "ready":
        raise typer.Exit(code=1)


@app.command("draft-animation-playtest-report")
def draft_animation_playtest_report_command(
    output: Path = ANIMATION_PLAYTEST_REPORT_OUTPUT_OPTION,
    commit: str = ANIMATION_PLAYTEST_REPORT_METADATA_OPTION,
    tester: str = ANIMATION_PLAYTEST_REPORT_METADATA_OPTION,
    platform: str = ANIMATION_PLAYTEST_REPORT_METADATA_OPTION,
    date: str = ANIMATION_PLAYTEST_REPORT_METADATA_OPTION,
    prefill_automated_gates: bool = typer.Option(
        False,
        "--prefill-automated-gates",
        help=(
            "Mark automated gate rows as pass after local/CI preflight has already passed; "
            "manual playtest rows remain todo."
        ),
    ),
) -> None:
    """Write the strict manual 2D animation playtest report draft."""

    write_2d_animation_playtest_report_template(
        output,
        version=__version__,
        commit=commit,
        tester=tester,
        platform=platform,
        date=date,
        prefill_automated_gates=prefill_automated_gates,
    )
    console.print(
        Panel.fit(
            (
                f"Animation playtest report draft written to {output}\n"
                "Replace every `todo` and `fill-me`, then validate before signoff."
            ),
            title="Animation Playtest Report Draft",
            border_style="cyan",
        )
    )


@app.command("validate-animation-playtest-report")
def validate_animation_playtest_report_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
) -> None:
    """Validate that a manual animation playtest report is complete and signed off."""

    validation = validate_2d_animation_playtest_report(report_path)
    table = Table(title="Animation Playtest Report Validation")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Report", validation.path)
    table.add_row("Release Decision", validation.release_decision or "-")
    table.add_row("Status", validation.status.upper())
    console.print(table)

    if validation.findings:
        findings_table = Table(title="Validation Findings")
        findings_table.add_column("Finding", style="yellow")
        for finding in validation.findings:
            findings_table.add_row(finding)
        console.print(findings_table)
        console.print(
            Panel.fit(
                "Manual animation signoff is incomplete.",
                title="Animation Playtest Report",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            "Manual animation signoff report is complete.",
            title="Animation Playtest Report",
            border_style="green",
        )
    )


@app.command("animation-playtest-status")
def animation_playtest_status_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    fail_on_incomplete: bool = ANIMATION_PLAYTEST_STATUS_FAIL_OPTION,
) -> None:
    """Show grouped manual animation playtest report progress without hiding details."""

    validation = validate_2d_animation_playtest_report(report_path)
    print_animation_playtest_status(validation)
    if fail_on_incomplete and validation.status != "pass":
        raise typer.Exit(code=1)


def print_animation_playtest_status(validation: AnimationPlaytestReportValidation) -> None:
    """Print grouped manual animation report status for CLI commands."""

    summary = summarize_2d_animation_playtest_report(validation)

    table = Table(title="Animation Playtest Status")
    table.add_column("Area", style="cyan")
    table.add_column("Open Items", justify="right")
    table.add_column("Next Step")
    if summary:
        for area in summary:
            table.add_row(area.area, str(area.incomplete_count), area.next_step)
    else:
        table.add_row("Complete", "0", "Report is ready for presentation signoff.")
    console.print(table)

    border_style = "green" if validation.status == "pass" else "yellow"
    console.print(
        Panel.fit(
            (
                f"Status {validation.status.upper()} | "
                f"{len(validation.findings)} open validation item(s)"
            ),
            title="Animation Playtest Status",
            border_style=border_style,
        )
    )


@app.command("animation-playtest-commands")
def animation_playtest_commands_command(
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed used for the visible play-2d manual animation pass.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
    output: Path | None = ANIMATION_PLAYTEST_COMMANDS_OUTPUT_OPTION,
) -> None:
    """Print the visible-window command queue for manual 2D animation QA."""

    validate_scenario_id(scenario)
    queue = build_2d_animation_playtest_command_queue(
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )

    table = Table(title="Animation Playtest Command Queue")
    table.add_column("Step", justify="right")
    table.add_column("Target", style="cyan")
    table.add_column("Window")
    table.add_column("Motion")
    table.add_column("Command")
    for index, item in enumerate(queue, start=1):
        table.add_row(
            str(index),
            item.target,
            item.window_size,
            item.motion_mode,
            item.command,
        )
    console.print(table)

    if output is not None:
        write_2d_animation_playtest_command_queue(queue, output)
        console.print(
            Panel.fit(
                f"Animation playtest command queue written to {output}",
                title="Animation Playtest Commands",
                border_style="cyan",
            )
        )

    console.print(
        Panel.fit(
            (
                f"{len(queue)} command(s) queued. "
                "Run them in a visible window and fill the manual report; "
                "this does not mark animation signoff complete."
            ),
            title="Animation Playtest Commands",
            border_style="yellow",
        )
    )


@app.command("validate-animation-playtest-commands")
def validate_animation_playtest_commands_command(
    command_path: Path = ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed expected in the visible play-2d command queue.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
) -> None:
    """Validate that the manual animation command queue covers every required run."""

    validate_scenario_id(scenario)
    validation = validate_2d_animation_playtest_command_queue(
        command_path,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )

    table = Table(title="Animation Playtest Command Validation")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Commands", validation.path)
    table.add_row("Expected Commands", str(validation.expected_count))
    table.add_row("Status", validation.status.upper())
    console.print(table)

    if validation.findings:
        findings_table = Table(title="Command Queue Findings")
        findings_table.add_column("Finding", style="yellow")
        for finding in validation.findings:
            findings_table.add_row(finding)
        console.print(findings_table)
        console.print(
            Panel.fit(
                "Manual animation command queue is incomplete.",
                title="Animation Playtest Commands",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            "Manual animation command queue covers every required visible-window run.",
            title="Animation Playtest Commands",
            border_style="green",
        )
    )


@app.command("animation-playtest-plan")
def animation_playtest_plan_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    command_path: Path = ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed expected in the visible play-2d command queue.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
    output: Path | None = ANIMATION_PLAYTEST_PLAN_OUTPUT_OPTION,
    fail_on_incomplete: bool = ANIMATION_PLAYTEST_PLAN_FAIL_OPTION,
) -> None:
    """Show the next manual animation QA steps from the current artifacts."""

    validate_scenario_id(scenario)
    plan = build_2d_animation_playtest_readiness_plan(
        report_path,
        command_path,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )

    table = Table(title="Animation Playtest Plan")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Report Path", plan.report.path)
    table.add_row("Commands Path", plan.commands.path)
    table.add_row("Command Queue Status", plan.commands.status.upper())
    table.add_row("Report Status", plan.report.status.upper())
    table.add_row("Status", plan.status.upper())
    table.add_row("Open Items", str(plan.open_item_count))
    console.print(table)

    steps_table = Table(title="Next Animation QA Steps")
    steps_table.add_column("Area", style="cyan")
    steps_table.add_column("Status")
    steps_table.add_column("Open Items", justify="right")
    steps_table.add_column("Next Step")
    for step in plan.steps:
        steps_table.add_row(
            step.area,
            step.status.upper(),
            str(step.open_items),
            step.next_step,
        )
    console.print(steps_table)

    border_style = "green" if plan.status == "pass" else "yellow"
    console.print(
        Panel.fit(
            (
                f"Animation playtest plan status: {plan.status.upper()} "
                f"({plan.open_item_count} open item(s))."
            ),
            title="Animation Playtest Plan",
            border_style=border_style,
        )
    )
    if output is not None:
        write_2d_animation_playtest_readiness_plan(plan, output)
        console.print(
            Panel.fit(
                f"Animation playtest plan written to {output}",
                title="Animation Playtest Plan",
                border_style="cyan",
            )
        )
    if fail_on_incomplete and plan.status != "pass":
        raise typer.Exit(code=1)


@app.command("animation-playtest-next")
def animation_playtest_next_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    command_path: Path = ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed expected in the visible play-2d command queue.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
    fail_on_incomplete: bool = ANIMATION_PLAYTEST_PLAN_FAIL_OPTION,
) -> None:
    """Show the single next manual animation QA action to run or fill."""

    validate_scenario_id(scenario)
    plan = build_2d_animation_playtest_readiness_plan(
        report_path,
        command_path,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )
    next_step = plan.steps[0]
    route_item = _next_animation_playtest_route_item(plan)

    table = Table(title="Animation Playtest Next Action")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Status", plan.status.upper())
    table.add_row("Open Items", str(plan.open_item_count))
    table.add_row("Next Area", next_step.area)
    table.add_row("Next Step", next_step.next_step)
    console.print(table)

    if route_item is not None:
        route_index = plan.visible_route.index(route_item) + 1
        evidence_prompt = _animation_playtest_route_prompt(
            route_item.target,
            route_item.window_size,
            route_item.motion_mode,
        )
        route_table = Table(title="Next Visible-Window Command")
        route_table.add_column("Step", justify="right")
        route_table.add_column("Target", style="cyan")
        route_table.add_column("Window")
        route_table.add_column("Motion")
        route_table.add_column("Evidence To Record")
        route_table.add_column("Command")
        route_table.add_row(
            str(route_index),
            route_item.target,
            route_item.window_size,
            route_item.motion_mode,
            evidence_prompt,
            route_item.command,
        )
        console.print(route_table)
        console.print(
            Panel.fit(
                evidence_prompt,
                title="Evidence To Record",
                border_style="yellow",
            )
        )
        console.print(
            Panel.fit(
                route_item.command,
                title="Run Next Visible Command",
                border_style="cyan",
            )
        )
    elif plan.commands.status != "pass":
        console.print(
            Panel.fit(
                "Regenerate and validate the command queue before opening visible windows.",
                title="Animation Playtest Next Action",
                border_style="red",
            )
        )
    elif plan.status == "pass":
        console.print(
            Panel.fit(
                "Manual animation signoff is complete. Attach the passing report before release.",
                title="Animation Playtest Next Action",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel.fit(
                "No visible-window command is next; fill the next report evidence area above.",
                title="Animation Playtest Next Action",
                border_style="yellow",
            )
        )

    if fail_on_incomplete and plan.status != "pass":
        raise typer.Exit(code=1)


@app.command("animation-playtest-recorder-next")
def animation_playtest_recorder_next_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    command_path: Path = ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed expected in the visible play-2d command queue.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
    fail_on_incomplete: bool = ANIMATION_PLAYTEST_PLAN_FAIL_OPTION,
) -> None:
    """Show the next safe recorder command for manual animation QA."""

    validate_scenario_id(scenario)
    hint = build_2d_animation_playtest_recorder_hint(
        report_path,
        command_path,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )

    _print_animation_playtest_recorder_hint(hint)

    if fail_on_incomplete and hint.status != "pass":
        raise typer.Exit(code=1)


@app.command("animation-playtest-recorder-queue")
def animation_playtest_recorder_queue_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    command_path: Path = ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed expected in the visible play-2d command queue.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
    output: Path | None = ANIMATION_PLAYTEST_RECORDER_QUEUE_OUTPUT_OPTION,
    fail_on_incomplete: bool = ANIMATION_PLAYTEST_PLAN_FAIL_OPTION,
) -> None:
    """Show all safe recorder commands for currently incomplete manual QA rows."""

    validate_scenario_id(scenario)
    hints = build_2d_animation_playtest_recorder_queue(
        report_path,
        command_path,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )

    _print_animation_playtest_recorder_queue(hints)
    if output is not None:
        write_2d_animation_playtest_recorder_queue(hints, output)
        console.print(
            Panel.fit(
                f"Animation playtest recorder queue written to {output}",
                title="Animation Playtest Recorder Queue",
                border_style="cyan",
            )
        )

    if fail_on_incomplete and any(hint.status != "pass" for hint in hints):
        raise typer.Exit(code=1)


@app.command("validate-animation-playtest-recorder-queue")
def validate_animation_playtest_recorder_queue_command(
    recorder_queue_path: Path = ANIMATION_PLAYTEST_RECORDER_QUEUE_PATH_ARGUMENT,
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    command_path: Path = ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed expected in the visible play-2d command queue.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
) -> None:
    """Validate that a recorder queue artifact matches current manual QA gaps."""

    validate_scenario_id(scenario)
    validation = validate_2d_animation_playtest_recorder_queue(
        recorder_queue_path,
        report_path,
        command_path,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )

    table = Table(title="Animation Playtest Recorder Queue Validation")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Recorder Queue", validation.path)
    table.add_row("Expected Rows", str(validation.expected_count))
    table.add_row("Status", validation.status.upper())
    console.print(table)

    if validation.findings:
        findings_table = Table(title="Recorder Queue Findings")
        findings_table.add_column("Finding", style="yellow")
        for finding in validation.findings:
            findings_table.add_row(finding)
        console.print(findings_table)
        console.print(
            Panel.fit(
                "Animation recorder queue is stale or incomplete.",
                title="Animation Playtest Recorder Queue",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            "Animation recorder queue matches the current report and command queue.",
            title="Animation Playtest Recorder Queue",
            border_style="green",
        )
    )


@app.command("validate-animation-playtest-session")
def validate_animation_playtest_session_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    command_path: Path = ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT,
    plan_path: Path = ANIMATION_PLAYTEST_PLAN_PATH_ARGUMENT,
    recorder_queue_path: Path = ANIMATION_PLAYTEST_RECORDER_QUEUE_PATH_ARGUMENT,
    route_batch_path: Path | None = ANIMATION_PLAYTEST_ROUTE_BATCH_PATH_OPTION,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed expected in the visible play-2d command queue.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
) -> None:
    """Validate the complete manual animation handoff package."""

    validate_scenario_id(scenario)
    validation = validate_2d_animation_playtest_session(
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        route_batch_path,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )

    table = Table(title="Animation Playtest Session Validation")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Report", validation.report.path)
    table.add_row("Commands", validation.commands.path)
    table.add_row("Plan", validation.plan.path)
    table.add_row("Recorder Queue", validation.recorder_queue.path)
    if validation.route_batches is not None:
        table.add_row("Route Batches", validation.route_batches.path)
    table.add_row("Command Queue", validation.commands.status.upper())
    table.add_row("Plan Artifact", validation.plan.status.upper())
    table.add_row("Recorder Artifact", validation.recorder_queue.status.upper())
    if validation.route_batches is not None:
        table.add_row("Route Batch Artifact", validation.route_batches.status.upper())
    table.add_row("Artifact Status", validation.artifact_status.upper())
    table.add_row("Handoff Status", validation.handoff_status.upper())
    table.add_row("Report Open Items", str(len(validation.report.findings)))
    table.add_row("Recorder Queue Rows", str(validation.recorder_queue.expected_count))
    console.print(table)

    if validation.findings:
        findings_table = Table(title="Animation Session Artifact Findings")
        findings_table.add_column("Finding", style="yellow")
        for finding in validation.findings:
            findings_table.add_row(finding)
        console.print(findings_table)
        console.print(
            Panel.fit(
                "Animation playtest session artifacts are stale or incomplete.",
                title="Animation Playtest Session",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    border_style = "green" if validation.handoff_status == "pass" else "yellow"
    console.print(
        Panel.fit(
            (
                "Animation playtest session artifacts are current. "
                f"Handoff status: {validation.handoff_status.upper()}."
            ),
            title="Animation Playtest Session",
            border_style=border_style,
        )
    )


@app.command("animation-playtest-handoff")
def animation_playtest_handoff_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    command_path: Path = ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT,
    plan_path: Path = ANIMATION_PLAYTEST_PLAN_PATH_ARGUMENT,
    recorder_queue_path: Path = ANIMATION_PLAYTEST_RECORDER_QUEUE_PATH_ARGUMENT,
    route_batch_path: Path | None = ANIMATION_PLAYTEST_ROUTE_BATCH_PATH_OPTION,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed expected in the visible play-2d command queue.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
    output: Path | None = ANIMATION_PLAYTEST_HANDOFF_OUTPUT_OPTION,
    fail_on_incomplete: bool = ANIMATION_PLAYTEST_PLAN_FAIL_OPTION,
) -> None:
    """Show the next visible command and recorder command for manual animation QA."""

    validate_scenario_id(scenario)
    handoff = build_2d_animation_playtest_handoff(
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        route_batch_path,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )
    next_step = handoff.plan.steps[0]

    table = Table(title="Animation Playtest Manual Handoff")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Artifact Status", handoff.session.artifact_status.upper())
    table.add_row("Handoff Status", handoff.status.upper())
    table.add_row("Report Open Items", str(len(handoff.session.report.findings)))
    table.add_row("Recorder Queue Rows", str(handoff.session.recorder_queue.expected_count))
    if handoff.session.route_batches is not None:
        table.add_row("Route Batch Artifact", handoff.session.route_batches.status.upper())
    table.add_row("Next Area", next_step.area)
    table.add_row("Next Open Items", str(next_step.open_items))
    table.add_row("Next Step", next_step.next_step)
    console.print(table)

    if handoff.session.findings:
        findings_table = Table(title="Animation Handoff Artifact Findings")
        findings_table.add_column("Finding", style="yellow")
        for finding in handoff.session.findings:
            findings_table.add_row(finding)
        console.print(findings_table)
        console.print(
            Panel.fit(
                "Fix stale session artifacts before starting the visible-window pass.",
                title="Animation Playtest Handoff",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    _print_animation_playtest_recorder_hint(handoff.recorder_hint)

    if output is not None:
        write_2d_animation_playtest_handoff(handoff, output)
        console.print(
            Panel.fit(
                f"Animation playtest handoff written to {output}",
                title="Animation Playtest Handoff",
                border_style="cyan",
            )
        )

    if fail_on_incomplete and handoff.status != "pass":
        raise typer.Exit(code=1)


@app.command("animation-playtest-route-batches")
def animation_playtest_route_batches_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    command_path: Path = ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed expected in the visible play-2d command queue.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
    output: Path | None = ANIMATION_PLAYTEST_ROUTE_BATCH_OUTPUT_OPTION,
    fail_on_incomplete: bool = ANIMATION_PLAYTEST_PLAN_FAIL_OPTION,
) -> None:
    """Group manual visible-window route work into window-sized batches."""

    validate_scenario_id(scenario)
    batch_plan = build_2d_animation_playtest_route_batch_plan(
        report_path,
        command_path,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )

    summary_table = Table(title="Animation Playtest Route Batches")
    summary_table.add_column("Batch", justify="right")
    summary_table.add_column("Window", style="cyan")
    summary_table.add_column("Status")
    summary_table.add_column("Open Items", justify="right")
    summary_table.add_column("Visible Commands", justify="right")
    summary_table.add_column("Next Visible Command")
    for batch in batch_plan.batches:
        next_item = next((item for item in batch.items if item.status != "pass"), None)
        next_command = next_item.visible_command if next_item is not None else "-"
        summary_table.add_row(
            str(batch.batch_number),
            batch.window_size,
            batch.status.upper(),
            str(batch.open_items),
            str(len(batch.items)),
            next_command,
        )
    console.print(summary_table)

    next_batch = next((batch for batch in batch_plan.batches if batch.open_items), None)
    if next_batch is not None:
        console.print("[bold cyan]Route Batch Copy Commands[/bold cyan]")
        console.print(f"Batch {next_batch.batch_number}: {next_batch.window_size}")
        for line in animation_playtest_route_batch_copy_commands(next_batch):
            console.print(line)

    if batch_plan.commands.findings:
        findings_table = Table(title="Route Batch Command Findings")
        findings_table.add_column("Finding", style="yellow")
        for finding in batch_plan.commands.findings:
            findings_table.add_row(finding)
        console.print(findings_table)

    border_style = "green" if batch_plan.status == "pass" else "yellow"
    console.print(
        Panel.fit(
            (
                f"Route batch status: {batch_plan.status.upper()} | "
                f"{batch_plan.route_open_items} route/window item(s), "
                f"{batch_plan.open_item_count} total report/queue item(s)."
            ),
            title="Animation Playtest Route Batches",
            border_style=border_style,
        )
    )

    if output is not None:
        write_2d_animation_playtest_route_batch_plan(batch_plan, output)
        console.print(
            Panel.fit(
                f"Animation route batch plan written to {output}",
                title="Animation Playtest Route Batches",
                border_style="cyan",
            )
        )

    if fail_on_incomplete and batch_plan.status != "pass":
        raise typer.Exit(code=1)


@app.command("validate-animation-playtest-route-batches")
def validate_animation_playtest_route_batches_command(
    batch_path: Path = ANIMATION_PLAYTEST_ROUTE_BATCH_PATH_ARGUMENT,
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    command_path: Path = ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed expected in the visible play-2d command queue.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
) -> None:
    """Validate that a visible-route batch artifact matches current QA gaps."""

    validate_scenario_id(scenario)
    validation = validate_2d_animation_playtest_route_batch_plan(
        batch_path,
        report_path,
        command_path,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )

    table = Table(title="Animation Playtest Route Batch Validation")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Route Batches", validation.path)
    table.add_row("Expected Batches", str(validation.expected_batches))
    table.add_row("Expected Route Rows", str(validation.expected_route_rows))
    table.add_row("Status", validation.status.upper())
    console.print(table)

    if validation.findings:
        findings_table = Table(title="Route Batch Findings")
        findings_table.add_column("Finding", style="yellow")
        for finding in validation.findings:
            findings_table.add_row(finding)
        console.print(findings_table)
        console.print(
            Panel.fit(
                "Animation route batch artifact is stale or incomplete.",
                title="Animation Playtest Route Batches",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            "Animation route batch artifact matches the current report and command queue.",
            title="Animation Playtest Route Batches",
            border_style="green",
        )
    )


@app.command("animation-playtest-ui-triage")
def animation_playtest_ui_triage_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    command_path: Path = ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT,
    plan_path: Path = ANIMATION_PLAYTEST_PLAN_PATH_ARGUMENT,
    recorder_queue_path: Path = ANIMATION_PLAYTEST_RECORDER_QUEUE_PATH_ARGUMENT,
    route_batch_path: Path | None = ANIMATION_PLAYTEST_ROUTE_BATCH_PATH_OPTION,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed expected in the visible play-2d command queue.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
    output: Path | None = ANIMATION_PLAYTEST_TRIAGE_OUTPUT_OPTION,
    fail_on_incomplete: bool = ANIMATION_PLAYTEST_PLAN_FAIL_OPTION,
) -> None:
    """Show the manual UI/animation issue triage backlog."""

    validate_scenario_id(scenario)
    triage = build_2d_animation_playtest_ui_triage_plan(
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        route_batch_path,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )

    table = Table(title="Animation Playtest UI Triage")
    table.add_column("Step", justify="right")
    table.add_column("Priority")
    table.add_column("Area", style="cyan")
    table.add_column("Lane")
    table.add_column("Status")
    table.add_column("Open", justify="right")
    for item in triage.items:
        table.add_row(
            str(item.step),
            item.priority,
            item.area,
            item.lane,
            item.status.upper(),
            str(item.open_items),
        )
    console.print(table)
    console.print(
        Panel.fit(
            (
                f"UI triage status: {triage.status.upper()} | "
                f"{triage.open_item_count} open item(s), "
                f"{triage.blocker_count} P0/P1 lane(s)."
            ),
            title="Animation Playtest UI Triage",
            border_style="green" if triage.status == "pass" else "yellow",
        )
    )

    if output is not None:
        write_2d_animation_playtest_ui_triage_plan(triage, output)
        console.print(
            Panel.fit(
                f"Animation UI triage written to {output}",
                title="Animation Playtest UI Triage",
                border_style="cyan",
            )
        )

    if fail_on_incomplete and triage.status != "pass":
        raise typer.Exit(code=1)


@app.command("validate-animation-playtest-ui-triage")
def validate_animation_playtest_ui_triage_command(
    triage_path: Path = ANIMATION_PLAYTEST_TRIAGE_PATH_ARGUMENT,
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    command_path: Path = ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT,
    plan_path: Path = ANIMATION_PLAYTEST_PLAN_PATH_ARGUMENT,
    recorder_queue_path: Path = ANIMATION_PLAYTEST_RECORDER_QUEUE_PATH_ARGUMENT,
    route_batch_path: Path | None = ANIMATION_PLAYTEST_ROUTE_BATCH_PATH_OPTION,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed expected in the visible play-2d command queue.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
) -> None:
    """Validate that the UI triage artifact matches current handoff artifacts."""

    validate_scenario_id(scenario)
    validation = validate_2d_animation_playtest_ui_triage_plan(
        triage_path,
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        route_batch_path,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )

    table = Table(title="Animation Playtest UI Triage Validation")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("UI Triage", validation.path)
    table.add_row("Expected Rows", str(validation.expected_count))
    table.add_row("Status", validation.status.upper())
    console.print(table)

    if validation.findings:
        findings_table = Table(title="UI Triage Findings")
        findings_table.add_column("Finding", style="yellow")
        for finding in validation.findings:
            findings_table.add_row(finding)
        console.print(findings_table)
        console.print(
            Panel.fit(
                "Animation UI triage artifact is stale or incomplete.",
                title="Animation Playtest UI Triage",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            "Animation UI triage artifact matches the current handoff package.",
            title="Animation Playtest UI Triage",
            border_style="green",
        )
    )


@app.command("animation-playtest-release-gate")
def animation_playtest_release_gate_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    command_path: Path = ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT,
    plan_path: Path = ANIMATION_PLAYTEST_PLAN_PATH_ARGUMENT,
    recorder_queue_path: Path = ANIMATION_PLAYTEST_RECORDER_QUEUE_PATH_ARGUMENT,
    triage_path: Path = ANIMATION_PLAYTEST_TRIAGE_PATH_ARGUMENT,
    route_batch_path: Path | None = ANIMATION_PLAYTEST_ROUTE_BATCH_PATH_OPTION,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed expected in the visible play-2d command queue.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
    output: Path | None = ANIMATION_PLAYTEST_RELEASE_GATE_OUTPUT_OPTION,
    fail_on_incomplete: bool = ANIMATION_PLAYTEST_PLAN_FAIL_OPTION,
) -> None:
    """Show the final animation go/no-go gate without completing manual signoff."""

    validate_scenario_id(scenario)
    gate = build_2d_animation_playtest_release_gate(
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        triage_path,
        route_batch_path,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )

    table = Table(title="Animation Playtest Release Gate")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Status", gate.status.upper())
    table.add_row("Artifact Status", gate.artifact_status.upper())
    table.add_row("Manual Result", gate.manual_result)
    table.add_row("Handoff Status", gate.session.handoff_status.upper())
    table.add_row("Report Status", gate.session.report.status.upper())
    table.add_row("UI Triage Artifact", gate.triage_validation.status.upper())
    table.add_row("Open Report Items", str(len(gate.session.report.findings)))
    table.add_row("Open UI Triage Items", str(gate.triage.open_item_count))
    table.add_row("P0/P1 Lanes", str(gate.triage.blocker_count))
    table.add_row("Blocking Checks", str(gate.blocking_check_count))
    console.print(table)

    checks_table = Table(title="Release Gate Checks")
    checks_table.add_column("Check", style="cyan")
    checks_table.add_column("Status")
    checks_table.add_column("Blockers", justify="right")
    checks_table.add_column("Next Action")
    for check in gate.checks:
        checks_table.add_row(
            check.name,
            check.status.upper(),
            str(check.blocker_count),
            check.next_action,
        )
    console.print(checks_table)

    hint = gate.recorder_hint
    required_terms = ", ".join(hint.required_terms) if hint.required_terms else "-"
    visible_command = hint.visible_command or "-"
    next_table = Table(title="Next Manual Action")
    next_table.add_column("Field", style="cyan")
    next_table.add_column("Value")
    next_table.add_row("Area", hint.area)
    next_table.add_row("Target", hint.target)
    next_table.add_row("Status", hint.status.upper())
    next_table.add_row("Required Terms", required_terms)
    next_table.add_row("Evidence Prompt", hint.evidence_prompt)
    next_table.add_row("Visible Command", visible_command)
    next_table.add_row("Recorder Command", hint.recorder_command)
    console.print(next_table)

    console.print(
        Panel.fit(
            (
                f"Release gate status: {gate.status.upper()} | "
                f"{gate.blocking_check_count} blocking check(s)."
            ),
            title="Animation Playtest Release Gate",
            border_style="green" if gate.status == "pass" else "yellow",
        )
    )

    if output is not None:
        write_2d_animation_playtest_release_gate(gate, output)
        console.print(
            Panel.fit(
                f"Animation release gate written to {output}",
                title="Animation Playtest Release Gate",
                border_style="cyan",
            )
        )

    if fail_on_incomplete and gate.status != "pass":
        raise typer.Exit(code=1)


@app.command("validate-animation-playtest-release-gate")
def validate_animation_playtest_release_gate_command(
    gate_path: Path = ANIMATION_PLAYTEST_RELEASE_GATE_PATH_ARGUMENT,
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    command_path: Path = ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT,
    plan_path: Path = ANIMATION_PLAYTEST_PLAN_PATH_ARGUMENT,
    recorder_queue_path: Path = ANIMATION_PLAYTEST_RECORDER_QUEUE_PATH_ARGUMENT,
    triage_path: Path = ANIMATION_PLAYTEST_TRIAGE_PATH_ARGUMENT,
    route_batch_path: Path | None = ANIMATION_PLAYTEST_ROUTE_BATCH_PATH_OPTION,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed expected in the visible play-2d command queue.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
) -> None:
    """Validate that the animation release gate matches current QA artifacts."""

    validate_scenario_id(scenario)
    validation = validate_2d_animation_playtest_release_gate(
        gate_path,
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        triage_path,
        route_batch_path,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )

    table = Table(title="Animation Playtest Release Gate Validation")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Release Gate", validation.path)
    table.add_row("Expected Checks", str(validation.expected_count))
    table.add_row("Status", validation.status.upper())
    console.print(table)

    if validation.findings:
        findings_table = Table(title="Release Gate Findings")
        findings_table.add_column("Finding", style="yellow")
        for finding in validation.findings:
            findings_table.add_row(finding)
        console.print(findings_table)
        console.print(
            Panel.fit(
                "Animation release gate artifact is stale or incomplete.",
                title="Animation Playtest Release Gate",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            "Animation release gate artifact matches the current QA package.",
            title="Animation Playtest Release Gate",
            border_style="green",
        )
    )


@app.command("animation-playtest-progress")
def animation_playtest_progress_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    command_path: Path = ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT,
    plan_path: Path = ANIMATION_PLAYTEST_PLAN_PATH_ARGUMENT,
    recorder_queue_path: Path = ANIMATION_PLAYTEST_RECORDER_QUEUE_PATH_ARGUMENT,
    triage_path: Path = ANIMATION_PLAYTEST_TRIAGE_PATH_ARGUMENT,
    route_batch_path: Path | None = ANIMATION_PLAYTEST_ROUTE_BATCH_PATH_OPTION,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed expected in the visible play-2d command queue.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
    output: Path | None = ANIMATION_PLAYTEST_PROGRESS_OUTPUT_OPTION,
    fail_on_incomplete: bool = ANIMATION_PLAYTEST_PLAN_FAIL_OPTION,
) -> None:
    """Show manual animation QA progress without recording tester evidence."""

    validate_scenario_id(scenario)
    board = build_2d_animation_playtest_progress_board(
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        triage_path,
        route_batch_path,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )

    summary_table = Table(title="Animation Playtest Progress")
    summary_table.add_column("Field", style="cyan")
    summary_table.add_column("Value")
    summary_table.add_row("Status", board.status.upper())
    summary_table.add_row("Completion", f"{board.completion_percent}%")
    summary_table.add_row("Completed Items", str(board.completed_item_count))
    summary_table.add_row("Open Work Items", str(board.open_item_count))
    summary_table.add_row("Total Tracked Items", str(board.total_item_count))
    summary_table.add_row("Release Gate", board.release_gate.status.upper())
    summary_table.add_row("Manual Result", board.release_gate.manual_result)
    console.print(summary_table)

    lanes_table = Table(title="Progress Lanes")
    lanes_table.add_column("Lane", style="cyan")
    lanes_table.add_column("Status")
    lanes_table.add_column("Done", justify="right")
    lanes_table.add_column("Open", justify="right")
    lanes_table.add_column("Completion", justify="right")
    lanes_table.add_column("Next Action")
    for lane in board.lanes:
        lanes_table.add_row(
            lane.area,
            lane.status.upper(),
            f"{lane.completed_items}/{lane.total_items}",
            str(lane.open_items),
            f"{lane.completion_percent}%",
            lane.next_action,
        )
    console.print(lanes_table)

    hint = board.release_gate.recorder_hint
    required_terms = ", ".join(hint.required_terms) if hint.required_terms else "-"
    visible_command = hint.visible_command or "-"
    next_table = Table(title="Next Manual Action")
    next_table.add_column("Field", style="cyan")
    next_table.add_column("Value")
    next_table.add_row("Area", hint.area)
    next_table.add_row("Target", hint.target)
    next_table.add_row("Status", hint.status.upper())
    next_table.add_row("Required Terms", required_terms)
    next_table.add_row("Evidence Prompt", hint.evidence_prompt)
    next_table.add_row("Visible Command", visible_command)
    next_table.add_row("Recorder Command", hint.recorder_command)
    console.print(next_table)

    console.print(
        Panel.fit(
            (
                f"Manual animation progress: {board.completion_percent}% complete | "
                f"{board.open_item_count} open work item(s)."
            ),
            title="Animation Playtest Progress",
            border_style="green" if board.status == "pass" else "yellow",
        )
    )

    if output is not None:
        write_2d_animation_playtest_progress_board(board, output)
        console.print(
            Panel.fit(
                f"Animation progress board written to {output}",
                title="Animation Playtest Progress",
                border_style="cyan",
            )
        )

    if fail_on_incomplete and board.status != "pass":
        raise typer.Exit(code=1)


@app.command("validate-animation-playtest-progress")
def validate_animation_playtest_progress_command(
    progress_path: Path = ANIMATION_PLAYTEST_PROGRESS_PATH_ARGUMENT,
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    command_path: Path = ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT,
    plan_path: Path = ANIMATION_PLAYTEST_PLAN_PATH_ARGUMENT,
    recorder_queue_path: Path = ANIMATION_PLAYTEST_RECORDER_QUEUE_PATH_ARGUMENT,
    triage_path: Path = ANIMATION_PLAYTEST_TRIAGE_PATH_ARGUMENT,
    route_batch_path: Path | None = ANIMATION_PLAYTEST_ROUTE_BATCH_PATH_OPTION,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed expected in the visible play-2d command queue.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
) -> None:
    """Validate that the animation progress board matches current QA artifacts."""

    validate_scenario_id(scenario)
    validation = validate_2d_animation_playtest_progress_board(
        progress_path,
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        triage_path,
        route_batch_path,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )

    table = Table(title="Animation Playtest Progress Validation")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Progress Board", validation.path)
    table.add_row("Expected Lanes", str(validation.expected_count))
    table.add_row("Status", validation.status.upper())
    console.print(table)

    if validation.findings:
        findings_table = Table(title="Progress Board Findings")
        findings_table.add_column("Finding", style="yellow")
        for finding in validation.findings:
            findings_table.add_row(finding)
        console.print(findings_table)
        console.print(
            Panel.fit(
                "Animation progress board artifact is stale or incomplete.",
                title="Animation Playtest Progress",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            "Animation progress board matches the current QA package.",
            title="Animation Playtest Progress",
            border_style="green",
        )
    )


@app.command("animation-playtest-execution-guide")
def animation_playtest_execution_guide_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    command_path: Path = ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT,
    plan_path: Path = ANIMATION_PLAYTEST_PLAN_PATH_ARGUMENT,
    recorder_queue_path: Path = ANIMATION_PLAYTEST_RECORDER_QUEUE_PATH_ARGUMENT,
    triage_path: Path = ANIMATION_PLAYTEST_TRIAGE_PATH_ARGUMENT,
    route_batch_path: Path | None = ANIMATION_PLAYTEST_ROUTE_BATCH_PATH_OPTION,
    progress_path: Path = ANIMATION_PLAYTEST_PROGRESS_PATH_OPTION,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed expected in the visible play-2d command queue.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
    output: Path | None = ANIMATION_PLAYTEST_EXECUTION_GUIDE_OUTPUT_OPTION,
    fail_on_incomplete: bool = ANIMATION_PLAYTEST_PLAN_FAIL_OPTION,
) -> None:
    """Show a step-by-step manual animation QA execution guide."""

    validate_scenario_id(scenario)
    guide = build_2d_animation_playtest_execution_guide(
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        triage_path,
        route_batch_path,
        progress_path=progress_path,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )

    summary_table = Table(title="Animation Playtest Execution Guide")
    summary_table.add_column("Field", style="cyan")
    summary_table.add_column("Value")
    summary_table.add_row("Status", guide.status.upper())
    summary_table.add_row("Completion", f"{guide.progress.completion_percent}%")
    summary_table.add_row("Open Progress Items", str(guide.progress.open_item_count))
    summary_table.add_row("Open Recorder Steps", str(guide.open_step_count))
    summary_table.add_row("Manual Result", guide.progress.release_gate.manual_result)
    summary_table.add_row("Progress Board", guide.progress_path)
    console.print(summary_table)

    queue_table = Table(title="Execution Queue")
    queue_table.add_column("Step", justify="right")
    queue_table.add_column("Status")
    queue_table.add_column("Area", style="cyan")
    queue_table.add_column("Target")
    queue_table.add_column("Visible")
    queue_table.add_column("Terms", justify="right")
    for index, hint in enumerate(guide.recorder_steps, start=1):
        queue_table.add_row(
            str(index),
            hint.status.upper(),
            hint.area,
            hint.target,
            "yes" if hint.visible_command else "-",
            str(len(hint.required_terms)),
        )
    console.print(queue_table)

    if output is not None:
        write_2d_animation_playtest_execution_guide(guide, output)
        console.print(
            Panel.fit(
                f"Animation execution guide written to {output}",
                title="Animation Playtest Execution Guide",
                border_style="cyan",
            )
        )

    if fail_on_incomplete and guide.status != "pass":
        raise typer.Exit(code=1)


@app.command("validate-animation-playtest-execution-guide")
def validate_animation_playtest_execution_guide_command(
    guide_path: Path = ANIMATION_PLAYTEST_EXECUTION_GUIDE_PATH_ARGUMENT,
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    command_path: Path = ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT,
    plan_path: Path = ANIMATION_PLAYTEST_PLAN_PATH_ARGUMENT,
    recorder_queue_path: Path = ANIMATION_PLAYTEST_RECORDER_QUEUE_PATH_ARGUMENT,
    triage_path: Path = ANIMATION_PLAYTEST_TRIAGE_PATH_ARGUMENT,
    route_batch_path: Path | None = ANIMATION_PLAYTEST_ROUTE_BATCH_PATH_OPTION,
    progress_path: Path = ANIMATION_PLAYTEST_PROGRESS_PATH_OPTION,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed expected in the visible play-2d command queue.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
) -> None:
    """Validate that the execution guide matches current QA artifacts."""

    validate_scenario_id(scenario)
    validation = validate_2d_animation_playtest_execution_guide(
        guide_path,
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        triage_path,
        route_batch_path,
        progress_path=progress_path,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )

    table = Table(title="Animation Playtest Execution Guide Validation")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Execution Guide", validation.path)
    table.add_row("Expected Steps", str(validation.expected_count))
    table.add_row("Status", validation.status.upper())
    console.print(table)

    if validation.findings:
        findings_table = Table(title="Execution Guide Findings")
        findings_table.add_column("Finding", style="yellow")
        for finding in validation.findings:
            findings_table.add_row(finding)
        console.print(findings_table)
        console.print(
            Panel.fit(
                "Animation execution guide artifact is stale or incomplete.",
                title="Animation Playtest Execution Guide",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            "Animation execution guide matches the current QA package.",
            title="Animation Playtest Execution Guide",
            border_style="green",
        )
    )


@app.command("animation-playtest-issue-backlog")
def animation_playtest_issue_backlog_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    output: Path | None = ANIMATION_PLAYTEST_ISSUE_BACKLOG_OUTPUT_OPTION,
    fail_on_incomplete: bool = ANIMATION_PLAYTEST_PLAN_FAIL_OPTION,
) -> None:
    """Show the fix/evidence backlog from a manual animation report."""

    backlog = build_2d_animation_playtest_issue_backlog(report_path)

    summary_table = Table(title="Animation Playtest Issue Backlog")
    summary_table.add_column("Field", style="cyan")
    summary_table.add_column("Value")
    summary_table.add_row("Status", backlog.status.upper())
    summary_table.add_row("Report", backlog.report.path)
    summary_table.add_row("Report Validation", backlog.report.status.upper())
    summary_table.add_row("Release Decision", backlog.report.release_decision or "-")
    summary_table.add_row("Total Issues", str(backlog.issue_count))
    summary_table.add_row("P0", str(backlog.p0_count))
    summary_table.add_row("P1", str(backlog.p1_count))
    summary_table.add_row("P2", str(backlog.p2_count))
    console.print(summary_table)

    issue_table = Table(title="Issue Queue")
    issue_table.add_column("Priority")
    issue_table.add_column("Status")
    issue_table.add_column("Area", style="cyan")
    issue_table.add_column("Target")
    issue_table.add_column("Result")
    issue_table.add_column("Next Action")
    for issue in backlog.issues:
        issue_table.add_row(
            issue.priority,
            issue.status.upper(),
            issue.area,
            issue.target,
            issue.result,
            issue.next_action,
        )
    console.print(issue_table)

    if output is not None:
        write_2d_animation_playtest_issue_backlog(backlog, output)
        console.print(
            Panel.fit(
                f"Animation issue backlog written to {output}",
                title="Animation Playtest Issue Backlog",
                border_style="cyan",
            )
        )

    if fail_on_incomplete and backlog.status != "pass":
        raise typer.Exit(code=1)


@app.command("validate-animation-playtest-issue-backlog")
def validate_animation_playtest_issue_backlog_command(
    backlog_path: Path = ANIMATION_PLAYTEST_ISSUE_BACKLOG_PATH_ARGUMENT,
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
) -> None:
    """Validate that the animation issue backlog matches the current report."""

    validation = validate_2d_animation_playtest_issue_backlog(backlog_path, report_path)

    table = Table(title="Animation Playtest Issue Backlog Validation")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Issue Backlog", validation.path)
    table.add_row("Expected Issues", str(validation.expected_count))
    table.add_row("Status", validation.status.upper())
    console.print(table)

    if validation.findings:
        findings_table = Table(title="Issue Backlog Findings")
        findings_table.add_column("Finding", style="yellow")
        for finding in validation.findings:
            findings_table.add_row(finding)
        console.print(findings_table)
        console.print(
            Panel.fit(
                "Animation issue backlog artifact is stale or incomplete.",
                title="Animation Playtest Issue Backlog",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            "Animation issue backlog matches the current manual report.",
            title="Animation Playtest Issue Backlog",
            border_style="green",
        )
    )


@app.command("animation-playtest-sprint")
def animation_playtest_sprint_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    command_path: Path = ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT,
    plan_path: Path = ANIMATION_PLAYTEST_PLAN_PATH_ARGUMENT,
    recorder_queue_path: Path = ANIMATION_PLAYTEST_RECORDER_QUEUE_PATH_ARGUMENT,
    triage_path: Path = ANIMATION_PLAYTEST_TRIAGE_PATH_ARGUMENT,
    route_batch_path: Path | None = ANIMATION_PLAYTEST_ROUTE_BATCH_PATH_OPTION,
    progress_path: Path = ANIMATION_PLAYTEST_PROGRESS_PATH_OPTION,
    execution_guide_path: Path = ANIMATION_PLAYTEST_EXECUTION_GUIDE_PATH_OPTION,
    issue_backlog_path: Path = ANIMATION_PLAYTEST_ISSUE_BACKLOG_PATH_OPTION,
    output: Path | None = ANIMATION_PLAYTEST_SPRINT_OUTPUT_OPTION,
    max_observation_steps: int = ANIMATION_PLAYTEST_SPRINT_MAX_STEPS_OPTION,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed expected in the visible play-2d command queue.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
    fail_on_incomplete: bool = ANIMATION_PLAYTEST_PLAN_FAIL_OPTION,
) -> None:
    """Show a focused manual animation QA sprint packet."""

    validate_scenario_id(scenario)
    sprint = build_2d_animation_playtest_sprint_packet(
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        triage_path,
        route_batch_path,
        progress_path=progress_path,
        execution_guide_path=execution_guide_path,
        issue_backlog_path=issue_backlog_path,
        max_observation_steps=max_observation_steps,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )

    summary_table = Table(title="Animation Playtest Sprint")
    summary_table.add_column("Field", style="cyan")
    summary_table.add_column("Value")
    summary_table.add_row("Status", sprint.status.upper())
    summary_table.add_row("Completion", f"{sprint.execution_guide.progress.completion_percent}%")
    summary_table.add_row("Report", sprint.issue_backlog.report.path)
    summary_table.add_row("Execution Guide", sprint.execution_guide_path)
    summary_table.add_row("Issue Backlog", sprint.issue_backlog_path)
    summary_table.add_row("Observation Steps", str(sprint.open_observation_count))
    summary_table.add_row("Checklist Items", str(sprint.checklist_count))
    summary_table.add_row("Execution Batches", str(sprint.execution_batch_count))
    summary_table.add_row("Layout Repair Checks", str(sprint.layout_repair_count))
    summary_table.add_row("Layout Recording Rows", str(sprint.layout_recording_count))
    summary_table.add_row("Navigation Recovery Drills", str(sprint.navigation_drill_count))
    summary_table.add_row("Navigation Recording Rows", str(sprint.navigation_recording_count))
    summary_table.add_row("Defect Intake Rows", str(sprint.defect_intake_count))
    summary_table.add_row("Exit Criteria", str(sprint.exit_criteria_count))
    summary_table.add_row("Evidence Capture Rows", str(sprint.evidence_capture_count))
    summary_table.add_row("Evidence Note Templates", str(sprint.evidence_template_count))
    summary_table.add_row("P0/P1 Blockers", str(sprint.blocker_count))
    summary_table.add_row(
        "Post-observation Signoff",
        str(
            sum(
                1
                for issue in sprint.blocker_issues
                if animation_playtest_sprint_blocker_phase(issue) == "post-observation signoff"
            )
        ),
    )
    summary_table.add_row(
        "Fix-before-release",
        str(
            sum(
                1
                for issue in sprint.blocker_issues
                if animation_playtest_sprint_blocker_phase(issue) == "fix-before-release"
            )
        ),
    )
    summary_table.add_row("Backlog Status", sprint.issue_backlog.status.upper())
    console.print(summary_table)

    if sprint.next_observation is not None:
        hint = sprint.next_observation
        next_table = Table(title="Sprint Next Action")
        next_table.add_column("Area", style="cyan")
        next_table.add_column("Target")
        next_table.add_column("Visible Command")
        next_table.add_column("Required Terms", justify="right")
        next_table.add_column("Recorder Command")
        next_table.add_row(
            hint.area,
            hint.target,
            hint.visible_command or "-",
            str(len(hint.required_terms)),
            hint.recorder_command,
        )
        console.print(next_table)
        console.print("[bold cyan]Sprint Next Copy Commands[/bold cyan]")
        console.print("Visible command:")
        console.print(hint.visible_command or "-")
        console.print("Recorder command after observation:")
        console.print(hint.recorder_command)

    batch_table = Table(title="Sprint Execution Batches")
    batch_table.add_column("Batch", style="cyan", no_wrap=True)
    batch_table.add_column("Visible Scope")
    batch_table.add_column("Record After")
    batch_table.add_column("Stop / Escalate If")
    for name, visible_scope, record_after, stop_condition in sprint.execution_batches:
        batch_table.add_row(name, visible_scope, record_after, stop_condition)
    console.print(batch_table)

    observation_table = Table(title="Sprint Observation Queue")
    observation_table.add_column("Step", justify="right")
    observation_table.add_column("Status")
    observation_table.add_column("Area", style="cyan")
    observation_table.add_column("Target")
    observation_table.add_column("Visible")
    observation_table.add_column("Terms", justify="right")
    for index, hint in enumerate(sprint.observation_steps, start=1):
        observation_table.add_row(
            str(index),
            hint.status.upper(),
            hint.area,
            hint.target,
            "yes" if hint.visible_command else "-",
            str(len(hint.required_terms)),
        )
    console.print(observation_table)

    blocker_table = Table(title="Sprint P0/P1 Blockers")
    blocker_table.add_column("Priority")
    blocker_table.add_column("Status")
    blocker_table.add_column("Phase")
    blocker_table.add_column("Area", style="cyan")
    blocker_table.add_column("Target")
    blocker_table.add_column("Dependency")
    blocker_table.add_column("Next Action")
    for issue in sprint.blocker_issues:
        blocker_table.add_row(
            issue.priority,
            issue.status.upper(),
            animation_playtest_sprint_blocker_phase(issue),
            issue.area,
            issue.target,
            animation_playtest_sprint_blocker_dependency(issue),
            animation_playtest_sprint_blocker_next_action(issue),
        )
    console.print(blocker_table)

    if output is not None:
        write_2d_animation_playtest_sprint_packet(sprint, output)
        console.print(
            Panel.fit(
                f"Animation sprint packet written to {output}",
                title="Animation Playtest Sprint",
                border_style="cyan",
            )
        )

    if fail_on_incomplete and sprint.status != "pass":
        raise typer.Exit(code=1)


@app.command("validate-animation-playtest-sprint")
def validate_animation_playtest_sprint_command(
    sprint_path: Path = ANIMATION_PLAYTEST_SPRINT_PATH_ARGUMENT,
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    command_path: Path = ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT,
    plan_path: Path = ANIMATION_PLAYTEST_PLAN_PATH_ARGUMENT,
    recorder_queue_path: Path = ANIMATION_PLAYTEST_RECORDER_QUEUE_PATH_ARGUMENT,
    triage_path: Path = ANIMATION_PLAYTEST_TRIAGE_PATH_ARGUMENT,
    route_batch_path: Path | None = ANIMATION_PLAYTEST_ROUTE_BATCH_PATH_OPTION,
    progress_path: Path = ANIMATION_PLAYTEST_PROGRESS_PATH_OPTION,
    execution_guide_path: Path = ANIMATION_PLAYTEST_EXECUTION_GUIDE_PATH_OPTION,
    issue_backlog_path: Path = ANIMATION_PLAYTEST_ISSUE_BACKLOG_PATH_OPTION,
    max_observation_steps: int = ANIMATION_PLAYTEST_SPRINT_MAX_STEPS_OPTION,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed expected in the visible play-2d command queue.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
) -> None:
    """Validate that the animation sprint packet matches current artifacts."""

    validate_scenario_id(scenario)
    validation = validate_2d_animation_playtest_sprint_packet(
        sprint_path,
        report_path,
        command_path,
        plan_path,
        recorder_queue_path,
        triage_path,
        route_batch_path,
        progress_path=progress_path,
        execution_guide_path=execution_guide_path,
        issue_backlog_path=issue_backlog_path,
        max_observation_steps=max_observation_steps,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )

    table = Table(title="Animation Playtest Sprint Validation")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Sprint", validation.path)
    table.add_row("Expected Observation Rows", str(validation.expected_observation_count))
    table.add_row("Expected P0/P1 Blockers", str(validation.expected_blocker_count))
    table.add_row("Status", validation.status.upper())
    console.print(table)

    if validation.findings:
        findings_table = Table(title="Sprint Findings")
        findings_table.add_column("Finding", style="yellow")
        for finding in validation.findings:
            findings_table.add_row(finding)
        console.print(findings_table)
        console.print(
            Panel.fit(
                "Animation sprint packet is stale or incomplete.",
                title="Animation Playtest Sprint",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            "Animation sprint packet matches the current QA package.",
            title="Animation Playtest Sprint",
            border_style="green",
        )
    )


def _print_animation_playtest_recorder_queue(
    hints: tuple[AnimationPlaytestRecorderHint, ...],
) -> None:
    table = Table(title="Animation Playtest Recorder Queue")
    table.add_column("Step", justify="right")
    table.add_column("Status")
    table.add_column("Area", style="cyan")
    table.add_column("Target")
    table.add_column("Visible")
    table.add_column("Terms", justify="right")
    for index, hint in enumerate(hints, start=1):
        table.add_row(
            str(index),
            hint.status.upper(),
            hint.area,
            hint.target,
            "yes" if hint.visible_command else "-",
            str(len(hint.required_terms)),
        )
    console.print(table)
    console.print(
        Panel.fit(
            (
                f"{len(hints)} recorder step(s) queued. "
                "Every placeholder must be replaced with real observed evidence before signoff."
            ),
            title="Animation Playtest Recorder Queue",
            border_style="yellow" if any(hint.status != "pass" for hint in hints) else "green",
        )
    )


def _print_animation_playtest_recorder_hint(hint: AnimationPlaytestRecorderHint) -> None:
    table = Table(title="Animation Playtest Recorder Next")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Status", hint.status.upper())
    table.add_row("Area", hint.area)
    table.add_row("Target", hint.target)
    console.print(table)

    if hint.visible_command:
        console.print(
            Panel.fit(
                _wrap_animation_playtest_hint_text(hint.visible_command),
                title="Run Visible Command First",
                border_style="cyan",
            )
        )

    console.print(
        Panel.fit(
            _wrap_animation_playtest_hint_text(hint.evidence_prompt),
            title="Evidence To Record",
            border_style="yellow" if hint.status != "pass" else "green",
        )
    )

    if hint.required_terms:
        terms_table = Table(title="Required Evidence Terms")
        terms_table.add_column("Term", style="yellow")
        for term in hint.required_terms:
            terms_table.add_row(term)
        console.print(terms_table)

    console.print(
        Panel.fit(
            _wrap_animation_playtest_hint_text(hint.recorder_command),
            title="Recorder Command",
            border_style="cyan" if hint.status != "pass" else "green",
        )
    )


def _wrap_animation_playtest_hint_text(value: str) -> str:
    return textwrap.fill(value, width=68, break_long_words=True)


@app.command("record-animation-playtest-window")
def record_animation_playtest_window_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    window_size: str = ANIMATION_PLAYTEST_WINDOW_ARGUMENT,
    full_result: str = ANIMATION_PLAYTEST_FULL_RESULT_OPTION,
    reduced_result: str = ANIMATION_PLAYTEST_REDUCED_RESULT_OPTION,
    off_result: str = ANIMATION_PLAYTEST_OFF_RESULT_OPTION,
    notes: str = ANIMATION_PLAYTEST_EVIDENCE_NOTES_OPTION,
) -> None:
    """Record one manual window-matrix observation in the animation report."""

    try:
        record = record_2d_animation_playtest_window_evidence(
            report_path,
            window_size=window_size,
            full_result=full_result,
            reduced_result=reduced_result,
            off_result=off_result,
            notes=notes,
        )
    except ValueError as error:
        console.print(
            Panel.fit(
                str(error),
                title="Animation Playtest Evidence",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from error

    _print_animation_playtest_record_result(record.section, record.target, record.result)
    print_animation_playtest_status(validate_2d_animation_playtest_report(report_path))


@app.command("record-animation-playtest-route")
def record_animation_playtest_route_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    step: int = ANIMATION_PLAYTEST_ROUTE_STEP_ARGUMENT,
    result: str = ANIMATION_PLAYTEST_RESULT_OPTION,
    notes: str = ANIMATION_PLAYTEST_EVIDENCE_NOTES_OPTION,
) -> None:
    """Record one visible-route manual observation in the animation report."""

    try:
        record = record_2d_animation_playtest_route_evidence(
            report_path,
            step=step,
            result=result,
            notes=notes,
        )
    except ValueError as error:
        console.print(
            Panel.fit(
                str(error),
                title="Animation Playtest Evidence",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from error

    _print_animation_playtest_record_result(record.section, record.target, record.result)
    print_animation_playtest_status(validate_2d_animation_playtest_report(report_path))


@app.command("record-animation-playtest-control")
def record_animation_playtest_control_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    area: str = ANIMATION_PLAYTEST_ROW_LABEL_ARGUMENT,
    result: str = ANIMATION_PLAYTEST_RESULT_OPTION,
    notes: str = ANIMATION_PLAYTEST_EVIDENCE_NOTES_OPTION,
    follow_up: str = ANIMATION_PLAYTEST_FOLLOW_UP_OPTION,
) -> None:
    """Record one manual control-clarity observation in the animation report."""

    try:
        record = record_2d_animation_playtest_control_evidence(
            report_path,
            area=area,
            result=result,
            notes=notes,
            follow_up=follow_up,
        )
    except ValueError as error:
        console.print(
            Panel.fit(
                str(error),
                title="Animation Playtest Evidence",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from error

    _print_animation_playtest_record_result(record.section, record.target, record.result)
    print_animation_playtest_status(validate_2d_animation_playtest_report(report_path))


@app.command("record-animation-playtest-scene")
def record_animation_playtest_scene_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    scene: str = ANIMATION_PLAYTEST_ROW_LABEL_ARGUMENT,
    result: str = ANIMATION_PLAYTEST_RESULT_OPTION,
    readability_notes: str = ANIMATION_PLAYTEST_READABILITY_NOTES_OPTION,
    motion_notes: str = ANIMATION_PLAYTEST_MOTION_NOTES_OPTION,
    follow_up: str = ANIMATION_PLAYTEST_FOLLOW_UP_OPTION,
) -> None:
    """Record one manual scene readability/motion observation in the report."""

    try:
        record = record_2d_animation_playtest_scene_evidence(
            report_path,
            scene=scene,
            result=result,
            readability_notes=readability_notes,
            motion_notes=motion_notes,
            follow_up=follow_up,
        )
    except ValueError as error:
        console.print(
            Panel.fit(
                str(error),
                title="Animation Playtest Evidence",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from error

    _print_animation_playtest_record_result(record.section, record.target, record.result)
    print_animation_playtest_status(validate_2d_animation_playtest_report(report_path))


@app.command("record-animation-playtest-feedback")
def record_animation_playtest_feedback_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    area: str = ANIMATION_PLAYTEST_ROW_LABEL_ARGUMENT,
    result: str = ANIMATION_PLAYTEST_RESULT_OPTION,
    notes: str = ANIMATION_PLAYTEST_EVIDENCE_NOTES_OPTION,
    follow_up: str = ANIMATION_PLAYTEST_FOLLOW_UP_OPTION,
) -> None:
    """Record one manual game-feel feedback observation in the report."""

    try:
        record = record_2d_animation_playtest_feedback_evidence(
            report_path,
            area=area,
            result=result,
            notes=notes,
            follow_up=follow_up,
        )
    except ValueError as error:
        console.print(
            Panel.fit(
                str(error),
                title="Animation Playtest Evidence",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from error

    _print_animation_playtest_record_result(record.section, record.target, record.result)
    print_animation_playtest_status(validate_2d_animation_playtest_report(report_path))


@app.command("record-animation-playtest-field")
def record_animation_playtest_field_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    field_name: str = ANIMATION_PLAYTEST_FIELD_NAME_ARGUMENT,
    value: str = ANIMATION_PLAYTEST_FIELD_VALUE_OPTION,
) -> None:
    """Record one build, blocker, or decision field in the animation report."""

    try:
        record = record_2d_animation_playtest_field(
            report_path,
            field_name=field_name,
            value=value,
        )
    except ValueError as error:
        console.print(
            Panel.fit(
                str(error),
                title="Animation Playtest Evidence",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from error

    _print_animation_playtest_record_result(record.section, record.target, record.result)
    print_animation_playtest_status(validate_2d_animation_playtest_report(report_path))


def _print_animation_playtest_record_result(section: str, target: str, result: str) -> None:
    table = Table(title="Animation Playtest Evidence Recorded")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Section", section)
    table.add_row("Target", target)
    table.add_row("Result", result)
    console.print(table)


def _next_animation_playtest_route_item(
    plan: AnimationPlaytestReadinessPlan,
) -> AnimationPlaytestCommand | None:
    """Return the first visible route command still called out by report validation."""

    if plan.commands.status != "pass":
        return None
    if not any("visible route" in finding.lower() for finding in plan.report.findings):
        return None

    route_index = _first_animation_playtest_route_finding_index(plan.report.findings)
    if route_index is None:
        route_index = 1
    if not 1 <= route_index <= len(plan.visible_route):
        return None
    return plan.visible_route[route_index - 1]


def _first_animation_playtest_route_finding_index(findings: tuple[str, ...]) -> int | None:
    """Extract the first visible-route row index from validator findings."""

    route_patterns = (
        r"visible route evidence row (\d+)",
        r"visible route evidence result: (\d+)",
        r"visible route evidence note: (\d+)",
        r"missing visible route evidence row: (\d+)",
        r"incomplete visible route evidence result: (\d+)",
        r"visible test route row (\d+)",
        r"missing visible test route row: (\d+)",
    )
    route_indexes: list[int] = []
    for finding in findings:
        normalized = finding.lower()
        for pattern in route_patterns:
            match = re.search(pattern, normalized)
            if match is None:
                continue
            route_indexes.append(int(match.group(1)))
            break
    return min(route_indexes) if route_indexes else None


def _animation_playtest_route_prompt(target: str, window_size: str, motion_mode: str) -> str:
    """Return compact evidence copy for one visible-window route command."""

    window_context = f"{window_size} {motion_mode}"
    if target == "menu":
        return (
            "Record title/menu, wizard, save-slot, archive, meta-board, hover, "
            f"and text-fit observations for {window_context}."
        )
    return (
        "Record dashboard, action picker, pending event, inspector, endgame, "
        f"summary, pause/back, and motion-feel observations for {window_context}."
    )


@app.command("validate-animation-playtest-plan")
def validate_animation_playtest_plan_command(
    report_path: Path = ANIMATION_PLAYTEST_REPORT_PATH_ARGUMENT,
    command_path: Path = ANIMATION_PLAYTEST_COMMANDS_PATH_ARGUMENT,
    plan_path: Path = ANIMATION_PLAYTEST_PLAN_PATH_ARGUMENT,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed expected in the visible play-2d command queue.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
) -> None:
    """Validate that an exported animation playtest plan matches current artifacts."""

    validate_scenario_id(scenario)
    validation = validate_2d_animation_playtest_readiness_plan(
        plan_path,
        report_path,
        command_path,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )

    table = Table(title="Animation Playtest Plan Validation")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Plan", validation.path)
    table.add_row("Expected Status", validation.expected_status.upper())
    table.add_row("Status", validation.status.upper())
    console.print(table)

    if validation.findings:
        findings_table = Table(title="Plan Artifact Findings")
        findings_table.add_column("Finding", style="yellow")
        for finding in validation.findings:
            findings_table.add_row(finding)
        console.print(findings_table)
        console.print(
            Panel.fit(
                "Animation playtest plan artifact is stale or incomplete.",
                title="Animation Playtest Plan",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            "Animation playtest plan artifact matches the current report and command queue.",
            title="Animation Playtest Plan",
            border_style="green",
        )
    )


@app.command("prepare-animation-playtest-session")
def prepare_animation_playtest_session_command(
    report_output: Path = ANIMATION_PLAYTEST_SESSION_REPORT_OUTPUT_OPTION,
    commands_output: Path = ANIMATION_PLAYTEST_SESSION_COMMANDS_OUTPUT_OPTION,
    plan_output: Path = ANIMATION_PLAYTEST_SESSION_PLAN_OUTPUT_OPTION,
    recorder_output: Path = ANIMATION_PLAYTEST_SESSION_RECORDER_OUTPUT_OPTION,
    route_batch_output: Path = ANIMATION_PLAYTEST_SESSION_ROUTE_BATCH_OUTPUT_OPTION,
    triage_output: Path = ANIMATION_PLAYTEST_SESSION_TRIAGE_OUTPUT_OPTION,
    release_gate_output: Path = ANIMATION_PLAYTEST_SESSION_RELEASE_GATE_OUTPUT_OPTION,
    progress_output: Path = ANIMATION_PLAYTEST_SESSION_PROGRESS_OUTPUT_OPTION,
    execution_guide_output: Path = ANIMATION_PLAYTEST_SESSION_EXECUTION_GUIDE_OUTPUT_OPTION,
    issue_backlog_output: Path = ANIMATION_PLAYTEST_SESSION_ISSUE_BACKLOG_OUTPUT_OPTION,
    sprint_output: Path = ANIMATION_PLAYTEST_SESSION_SPRINT_OUTPUT_OPTION,
    handoff_output: Path = ANIMATION_PLAYTEST_SESSION_HANDOFF_OUTPUT_OPTION,
    scenario: str = SCENARIO_OPTION,
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed used for the visible play-2d manual animation pass.",
    ),
    command_prefix: str = ANIMATION_PLAYTEST_COMMAND_PREFIX_OPTION,
    commit: str = ANIMATION_PLAYTEST_REPORT_METADATA_OPTION,
    tester: str = ANIMATION_PLAYTEST_REPORT_METADATA_OPTION,
    platform: str = ANIMATION_PLAYTEST_REPORT_METADATA_OPTION,
    date: str = ANIMATION_PLAYTEST_REPORT_METADATA_OPTION,
    prefill_automated_gates: bool = typer.Option(
        False,
        "--prefill-automated-gates",
        help=(
            "Mark automated gate rows as pass after local/CI preflight has already passed; "
            "manual playtest rows remain todo."
        ),
    ),
) -> None:
    """Prepare report, command queue, and plan files for the manual animation playtest."""

    validate_scenario_id(scenario)
    write_2d_animation_playtest_report_template(
        report_output,
        version=__version__,
        commit=commit,
        tester=tester,
        platform=platform,
        date=date,
        prefill_automated_gates=prefill_automated_gates,
    )
    queue = build_2d_animation_playtest_command_queue(
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )
    write_2d_animation_playtest_command_queue(queue, commands_output)
    plan = build_2d_animation_playtest_readiness_plan(
        report_output,
        commands_output,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )
    write_2d_animation_playtest_readiness_plan(plan, plan_output)
    plan_validation = validate_2d_animation_playtest_readiness_plan(
        plan_output,
        report_output,
        commands_output,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )
    recorder_queue = build_2d_animation_playtest_recorder_queue(
        report_output,
        commands_output,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )
    write_2d_animation_playtest_recorder_queue(recorder_queue, recorder_output)
    recorder_validation = validate_2d_animation_playtest_recorder_queue(
        recorder_output,
        report_output,
        commands_output,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )
    route_batch_plan = build_2d_animation_playtest_route_batch_plan(
        report_output,
        commands_output,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )
    write_2d_animation_playtest_route_batch_plan(route_batch_plan, route_batch_output)
    route_batch_validation = validate_2d_animation_playtest_route_batch_plan(
        route_batch_output,
        report_output,
        commands_output,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )
    session_validation = validate_2d_animation_playtest_session(
        report_output,
        commands_output,
        plan_output,
        recorder_output,
        route_batch_output,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )
    handoff = build_2d_animation_playtest_handoff(
        report_output,
        commands_output,
        plan_output,
        recorder_output,
        route_batch_output,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )
    write_2d_animation_playtest_handoff(handoff, handoff_output)
    triage = build_2d_animation_playtest_ui_triage_plan(
        report_output,
        commands_output,
        plan_output,
        recorder_output,
        route_batch_output,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )
    write_2d_animation_playtest_ui_triage_plan(triage, triage_output)
    triage_validation = validate_2d_animation_playtest_ui_triage_plan(
        triage_output,
        report_output,
        commands_output,
        plan_output,
        recorder_output,
        route_batch_output,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )
    release_gate = build_2d_animation_playtest_release_gate(
        report_output,
        commands_output,
        plan_output,
        recorder_output,
        triage_output,
        route_batch_output,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )
    write_2d_animation_playtest_release_gate(release_gate, release_gate_output)
    release_gate_validation = validate_2d_animation_playtest_release_gate(
        release_gate_output,
        report_output,
        commands_output,
        plan_output,
        recorder_output,
        triage_output,
        route_batch_output,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )
    progress_board = build_2d_animation_playtest_progress_board(
        report_output,
        commands_output,
        plan_output,
        recorder_output,
        triage_output,
        route_batch_output,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )
    write_2d_animation_playtest_progress_board(progress_board, progress_output)
    progress_validation = validate_2d_animation_playtest_progress_board(
        progress_output,
        report_output,
        commands_output,
        plan_output,
        recorder_output,
        triage_output,
        route_batch_output,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )
    execution_guide = build_2d_animation_playtest_execution_guide(
        report_output,
        commands_output,
        plan_output,
        recorder_output,
        triage_output,
        route_batch_output,
        progress_path=progress_output,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )
    write_2d_animation_playtest_execution_guide(execution_guide, execution_guide_output)
    execution_guide_validation = validate_2d_animation_playtest_execution_guide(
        execution_guide_output,
        report_output,
        commands_output,
        plan_output,
        recorder_output,
        triage_output,
        route_batch_output,
        progress_path=progress_output,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )
    issue_backlog = build_2d_animation_playtest_issue_backlog(report_output)
    write_2d_animation_playtest_issue_backlog(issue_backlog, issue_backlog_output)
    issue_backlog_validation = validate_2d_animation_playtest_issue_backlog(
        issue_backlog_output,
        report_output,
    )
    sprint_packet = build_2d_animation_playtest_sprint_packet(
        report_output,
        commands_output,
        plan_output,
        recorder_output,
        triage_output,
        route_batch_output,
        progress_path=progress_output,
        execution_guide_path=execution_guide_output,
        issue_backlog_path=issue_backlog_output,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )
    write_2d_animation_playtest_sprint_packet(sprint_packet, sprint_output)
    sprint_validation = validate_2d_animation_playtest_sprint_packet(
        sprint_output,
        report_output,
        commands_output,
        plan_output,
        recorder_output,
        triage_output,
        route_batch_output,
        progress_path=progress_output,
        execution_guide_path=execution_guide_output,
        issue_backlog_path=issue_backlog_output,
        scenario_id=scenario,
        seed=seed,
        command_prefix=command_prefix,
    )

    session_table = Table(title="Animation Playtest Session")
    session_table.add_column("Field", style="cyan")
    session_table.add_column("Value")
    session_table.add_row("Report", str(report_output))
    session_table.add_row("Commands", str(commands_output))
    session_table.add_row("Plan", str(plan_output))
    session_table.add_row("Recorder Queue", str(recorder_output))
    session_table.add_row("Route Batches", str(route_batch_output))
    session_table.add_row("UI Triage", str(triage_output))
    session_table.add_row("Release Gate", str(release_gate_output))
    session_table.add_row("Progress Board", str(progress_output))
    session_table.add_row("Execution Guide", str(execution_guide_output))
    session_table.add_row("Issue Backlog", str(issue_backlog_output))
    session_table.add_row("Sprint Packet", str(sprint_output))
    session_table.add_row("Handoff", str(handoff_output))
    session_table.add_row("Scenario", scenario)
    session_table.add_row("Seed", str(seed))
    session_table.add_row("Command Queue", f"{len(queue)} visible-window command(s)")
    session_table.add_row("Recorder Queue Rows", str(len(recorder_queue)))
    session_table.add_row("Route Batch Open Items", str(route_batch_plan.route_open_items))
    session_table.add_row("UI Triage Items", str(triage.open_item_count))
    session_table.add_row("Release Gate Status", release_gate.status.upper())
    session_table.add_row("Release Gate Artifact", release_gate_validation.status.upper())
    session_table.add_row("Progress", f"{progress_board.completion_percent}%")
    session_table.add_row("Progress Artifact", progress_validation.status.upper())
    session_table.add_row("Progress Open Items", str(progress_board.open_item_count))
    session_table.add_row("Execution Guide Artifact", execution_guide_validation.status.upper())
    session_table.add_row("Execution Guide Steps", str(len(execution_guide.recorder_steps)))
    session_table.add_row("Issue Backlog Artifact", issue_backlog_validation.status.upper())
    session_table.add_row("Issue Backlog Items", str(issue_backlog.issue_count))
    session_table.add_row("Sprint Artifact", sprint_validation.status.upper())
    session_table.add_row("Sprint Observation Steps", str(sprint_packet.open_observation_count))
    session_table.add_row("Sprint Execution Batches", str(sprint_packet.execution_batch_count))
    session_table.add_row("Sprint Layout Repair Checks", str(sprint_packet.layout_repair_count))
    session_table.add_row("Sprint Layout Recording Rows", str(sprint_packet.layout_recording_count))
    session_table.add_row(
        "Sprint Navigation Recovery Drills", str(sprint_packet.navigation_drill_count)
    )
    session_table.add_row(
        "Sprint Navigation Recording Rows", str(sprint_packet.navigation_recording_count)
    )
    session_table.add_row("Sprint P0/P1 Blockers", str(sprint_packet.blocker_count))
    session_table.add_row("Blocking Checks", str(release_gate.blocking_check_count))
    session_table.add_row("Plan Status", plan.status.upper())
    session_table.add_row("Plan Artifact", plan_validation.status.upper())
    session_table.add_row("Recorder Artifact", recorder_validation.status.upper())
    session_table.add_row("Route Batch Artifact", route_batch_validation.status.upper())
    session_table.add_row("UI Triage Artifact", triage_validation.status.upper())
    session_table.add_row("Session Artifacts", session_validation.artifact_status.upper())
    session_table.add_row("Handoff Status", session_validation.handoff_status.upper())
    session_table.add_row("Handoff Sheet", handoff.status.upper())
    session_table.add_row("Open Items", str(plan.open_item_count))
    console.print(session_table)

    validation = validate_2d_animation_playtest_report(report_output)
    print_animation_playtest_status(validation)
    if plan_validation.findings:
        findings_table = Table(title="Animation Playtest Plan Artifact Findings")
        findings_table.add_column("Finding", style="yellow")
        for finding in plan_validation.findings:
            findings_table.add_row(finding)
        console.print(findings_table)
        raise typer.Exit(code=1)
    if recorder_validation.findings:
        findings_table = Table(title="Animation Recorder Queue Artifact Findings")
        findings_table.add_column("Finding", style="yellow")
        for finding in recorder_validation.findings:
            findings_table.add_row(finding)
        console.print(findings_table)
        raise typer.Exit(code=1)
    if route_batch_validation.findings:
        findings_table = Table(title="Animation Route Batch Artifact Findings")
        findings_table.add_column("Finding", style="yellow")
        for finding in route_batch_validation.findings:
            findings_table.add_row(finding)
        console.print(findings_table)
        raise typer.Exit(code=1)
    if triage_validation.findings:
        findings_table = Table(title="Animation UI Triage Artifact Findings")
        findings_table.add_column("Finding", style="yellow")
        for finding in triage_validation.findings:
            findings_table.add_row(finding)
        console.print(findings_table)
        raise typer.Exit(code=1)
    if session_validation.findings:
        findings_table = Table(title="Animation Session Artifact Findings")
        findings_table.add_column("Finding", style="yellow")
        for finding in session_validation.findings:
            findings_table.add_row(finding)
        console.print(findings_table)
        raise typer.Exit(code=1)
    console.print(
        Panel.fit(
            (
                "Manual animation signoff is still incomplete. "
                "Run the visible-window batches, follow the recorder queue, use the UI triage "
                "backlog for layout/control fixes, then validate the report and handoff artifacts."
            ),
            title="Animation Playtest Session",
            border_style="yellow",
        )
    )


@app.command("list-scenarios")
def list_scenarios_command(
    db_path: Path = DB_PATH_OPTION,
) -> None:
    """Print the available starting scenarios."""

    render_scenario_catalog(
        console,
        get_available_scenarios(),
        locked_ids=_build_locked_content_ids(
            reward_type="scenario",
            db_path=db_path,
        ),
    )


@app.command("list-campaign-starts")
def list_campaign_starts_command(
    db_path: Path = DB_PATH_OPTION,
) -> None:
    """Print archive-gated campaign start modifiers for new runs."""

    render_campaign_start_catalog(
        console,
        list_campaign_starts(),
        locked_ids=_build_locked_campaign_start_ids(db_path=db_path),
    )


@app.command("list-templates")
def list_templates_command(
    db_path: Path = DB_PATH_OPTION,
) -> None:
    """Print the available product templates."""

    render_product_template_catalog(
        console,
        get_available_product_templates(),
        locked_ids=_build_locked_content_ids(
            reward_type="template",
            db_path=db_path,
        ),
    )


@app.command("list-goals")
def list_goals_command() -> None:
    """Print the available campaign goals."""

    render_campaign_goal_catalog(console, list_campaign_goals())


@app.command("list-rivals")
def list_rivals_command(
    db_path: Path = DB_PATH_OPTION,
) -> None:
    """Print the available competitor archetypes."""

    render_competitor_archetype_catalog(
        console,
        get_available_competitor_archetypes(),
        locked_ids=_build_locked_content_ids(
            reward_type="rival",
            db_path=db_path,
        ),
    )


@app.command("list-events")
def list_events_command() -> None:
    """Print the supported dynamic event catalog."""

    render_event_catalog(console, get_event_registry())


@app.command("list-candidates")
def list_candidates_command(
    seed: int = typer.Option(
        DEMO_SEED_EXAMPLE,
        "--seed",
        help="Seed used to generate a deterministic hiring pool.",
    ),
    count: int = typer.Option(3, "--count", min=1, max=6, help="Number of candidates to show."),
) -> None:
    """Print a deterministic sample hiring candidate pool."""

    render_candidate_pool(console, generate_candidate_pool(RandomSource(seed=seed), count=count))


@app.command("list-segments")
def list_segments_command() -> None:
    """Print customer segment trade-offs used by growth and churn formulas."""

    profiles = tuple((segment, get_market_segment_profile(segment)) for segment in MarketSegment)
    render_segment_catalog(console, profiles)


@app.command("list-roadmaps")
def list_roadmaps_command() -> None:
    """Print available quarter-scale roadmap initiatives."""

    profiles = tuple(
        (
            focus.value,
            get_roadmap_profile(focus, roadmap_set_turn=1, current_turn=1).summary,
        )
        for focus in RoadmapFocus
    )
    render_roadmap_catalog(console, profiles)


@app.command("list-balance-profiles")
def list_balance_profiles_command() -> None:
    """Print recommended balance-lab presets."""

    render_balance_profile_catalog(console, list_balance_profiles())


@app.command("list-initiatives", hidden=True)
def list_initiatives_alias() -> None:
    """Backward-compatible alias for roadmap initiative discovery."""

    list_roadmaps_command()


@app.command("simulate-balance")
def simulate_balance_command(
    scenario: str = SCENARIO_OPTION,
    difficulty: DifficultyMode = BALANCE_DIFFICULTY_OPTION,
    goal: CampaignGoalId = BALANCE_GOAL_OPTION,
    runs: int = typer.Option(5, "--runs", min=1, help="Number of deterministic runs."),
    turns: int = typer.Option(10, "--turns", min=1, help="Maximum turns per run."),
    seed_base: int = typer.Option(
        100,
        "--seed-base",
        help="Base seed. Each run increments from this value.",
    ),
) -> None:
    """Run a deterministic batch of autoplay simulations for balance checks."""

    validate_scenario_id(scenario)
    batch = run_balance_batch(
        scenario_id=scenario,
        difficulty_mode=difficulty,
        campaign_goal_id=goal,
        runs=runs,
        turns=turns,
        seed_base=seed_base,
    )
    render_balance_lab(console, batch)


@app.command("compare-balance")
def compare_balance_command(
    scenario: Optional[list[str]] = COMPARE_SCENARIOS_OPTION,
    difficulty: DifficultyMode = BALANCE_DIFFICULTY_OPTION,
    goal: CampaignGoalId = BALANCE_GOAL_OPTION,
    runs: int = typer.Option(3, "--runs", min=1, help="Number of deterministic runs."),
    turns: int = typer.Option(10, "--turns", min=1, help="Maximum turns per run."),
    seed_base: int = typer.Option(
        100,
        "--seed-base",
        help="Base seed. Each scenario gets a deterministic seed range from this value.",
    ),
) -> None:
    """Compare multiple scenarios side by side using deterministic autoplay."""

    scenario_ids = resolve_scenario_ids(scenario)
    comparison = run_balance_comparison(
        scenario_ids=scenario_ids,
        difficulty_mode=difficulty,
        campaign_goal_id=goal,
        runs=runs,
        turns=turns,
        seed_base=seed_base,
    )
    render_balance_comparison(console, comparison)


@app.command("balance-matrix")
def balance_matrix_command(
    scenario: Optional[list[str]] = COMPARE_SCENARIOS_OPTION,
    goal: CampaignGoalId = BALANCE_GOAL_OPTION,
    runs: int = typer.Option(2, "--runs", min=1, help="Number of deterministic runs."),
    turns: int = typer.Option(10, "--turns", min=1, help="Maximum turns per run."),
    seed_base: int = typer.Option(
        100,
        "--seed-base",
        help="Base seed. Each matrix cell gets a deterministic seed range from this value.",
    ),
) -> None:
    """Compare multiple scenarios across all supported difficulty modes."""

    scenario_ids = resolve_scenario_ids(scenario)
    matrix = run_balance_matrix(
        scenario_ids=scenario_ids,
        campaign_goal_id=goal,
        runs=runs,
        turns=turns,
        seed_base=seed_base,
    )
    render_balance_matrix(console, matrix)


@app.command("balance-audit")
def balance_audit_command(
    scenario: Optional[list[str]] = COMPARE_SCENARIOS_OPTION,
    goal: CampaignGoalId = BALANCE_GOAL_OPTION,
    runs: int = typer.Option(2, "--runs", min=1, help="Number of deterministic runs."),
    turns: int = typer.Option(10, "--turns", min=1, help="Maximum turns per run."),
    seed_base: int = typer.Option(
        100,
        "--seed-base",
        help="Base seed. Each matrix cell gets a deterministic seed range from this value.",
    ),
) -> None:
    """Flag rough balance cells across scenarios and supported difficulties."""

    scenario_ids = resolve_scenario_ids(scenario)
    audit = run_balance_audit(
        scenario_ids=scenario_ids,
        campaign_goal_id=goal,
        runs=runs,
        turns=turns,
        seed_base=seed_base,
    )
    render_balance_audit(console, audit)


@app.command("export-balance-csv")
def export_balance_csv_command(
    output: Path = CSV_OUTPUT_OPTION,
    scenario: Optional[list[str]] = COMPARE_SCENARIOS_OPTION,
    goal: CampaignGoalId = BALANCE_GOAL_OPTION,
    runs: int = typer.Option(2, "--runs", min=1, help="Number of deterministic runs."),
    turns: int = typer.Option(10, "--turns", min=1, help="Maximum turns per run."),
    seed_base: int = typer.Option(
        100,
        "--seed-base",
        help="Base seed. Each matrix cell gets a deterministic seed range from this value.",
    ),
) -> None:
    """Export a scenario-versus-difficulty balance matrix to CSV."""

    scenario_ids = resolve_scenario_ids(scenario)
    matrix = run_balance_matrix(
        scenario_ids=scenario_ids,
        campaign_goal_id=goal,
        runs=runs,
        turns=turns,
        seed_base=seed_base,
    )
    output.write_text(format_balance_matrix_csv(matrix), encoding="utf-8")
    console.print(
        Panel.fit(
            f"Wrote balance CSV to {output}",
            title="Balance Export",
            border_style="green",
        )
    )


@app.command("balance-report")
def balance_report_command(
    output: Path = BALANCE_REPORT_OUTPUT_OPTION,
    scenario: Optional[list[str]] = COMPARE_SCENARIOS_OPTION,
    goal: CampaignGoalId = BALANCE_GOAL_OPTION,
    runs: int = typer.Option(2, "--runs", min=1, help="Number of deterministic runs."),
    turns: int = typer.Option(10, "--turns", min=1, help="Maximum turns per run."),
    seed_base: int = typer.Option(
        100,
        "--seed-base",
        help="Base seed. Each matrix cell gets a deterministic seed range from this value.",
    ),
) -> None:
    """Export a Markdown balance matrix plus audit findings."""

    scenario_ids = resolve_scenario_ids(scenario)
    matrix = run_balance_matrix(
        scenario_ids=scenario_ids,
        campaign_goal_id=goal,
        runs=runs,
        turns=turns,
        seed_base=seed_base,
    )
    audit = run_balance_audit(
        scenario_ids=scenario_ids,
        campaign_goal_id=goal,
        runs=runs,
        turns=turns,
        seed_base=seed_base,
    )
    output.write_text(format_balance_report_markdown(matrix, audit), encoding="utf-8")
    console.print(
        Panel.fit(
            f"Wrote balance report to {output}",
            title="Balance Report",
            border_style="green",
        )
    )


@app.command("guide")
def guide_command() -> None:
    """Print a compact quick-start guide."""

    render_quick_guide(console)


@app.command("tutorial")
def tutorial_command() -> None:
    """Print a first-run tutorial path for demos and new players."""

    render_tutorial(console)


@app.command("glossary")
def glossary_command() -> None:
    """Explain core stats, systems, and decision families."""

    render_glossary(console)


@app.command("validate-content")
def validate_content_command() -> None:
    """Validate content catalogs and event registry wiring."""

    report = validate_content_catalogs()
    render_content_health(console, report)
    if not report.ok:
        raise typer.Exit(code=1) from None


@app.command("list-saves")
def list_saves_command(
    db_path: Path = DB_PATH_OPTION,
) -> None:
    """List all local save slots with compact metadata."""

    coordinator = SaveLoadCoordinator(db_path)
    try:
        save_slots = coordinator.list_save_slots()
    except PersistenceError as error:
        raise_cli_persistence_error("Save List Failed", error)
    render_save_slot_catalog(console, save_slots)


@app.command("list-archives")
def list_archives_command(
    db_path: Path = DB_PATH_OPTION,
) -> None:
    """List archived completed runs from the local SQLite database."""

    coordinator = SaveLoadCoordinator(db_path)
    try:
        archives = coordinator.list_run_archives()
    except PersistenceError as error:
        raise_cli_persistence_error("Archive List Failed", error)
    render_run_archive_catalog(console, archives)


@app.command("compare-archives")
def compare_archives_command(
    db_path: Path = DB_PATH_OPTION,
) -> None:
    """Compare archived completed runs across score, cash, and exit outcomes."""

    coordinator = SaveLoadCoordinator(db_path)
    try:
        archives = coordinator.list_run_archives()
    except PersistenceError as error:
        raise_cli_persistence_error("Archive Compare Failed", error)
    render_archive_comparison(console, archives)


@app.command("show-progression")
def show_progression_command(
    db_path: Path = DB_PATH_OPTION,
) -> None:
    """Summarize archive-derived meta progression for the local install."""

    coordinator = SaveLoadCoordinator(db_path)
    try:
        archives = coordinator.list_run_archives()
    except PersistenceError as error:
        raise_cli_persistence_error("Progression Read Failed", error)
    render_meta_progression(console, summarize_meta_progression(archives))


@app.command("list-unlocks")
def list_unlocks_command(
    db_path: Path = DB_PATH_OPTION,
) -> None:
    """Render the archive-driven unlock catalog with exact reward ids."""

    coordinator = SaveLoadCoordinator(db_path)
    try:
        archives = coordinator.list_run_archives()
    except PersistenceError as error:
        raise_cli_persistence_error("Unlock Read Failed", error)
    render_unlock_catalog(console, build_unlock_catalog(archives))


@app.command("check-saves")
def check_saves_command(
    db_path: Path = DB_PATH_OPTION,
) -> None:
    """Run SQLite integrity and foreign-key checks against local saves."""

    coordinator = SaveLoadCoordinator(db_path)
    try:
        report = coordinator.check_save_health()
    except PersistenceError as error:
        raise_cli_persistence_error("Save Health Check Failed", error)

    lines = [
        f"Integrity: {'ok' if report.integrity_ok else 'failed'}",
        f"Foreign Keys: {'ok' if report.foreign_key_ok else 'failed'}",
        f"Slots: {report.slot_count}",
        f"Schema Version: {report.schema_version}",
        "",
        report.message,
    ]
    console.print(
        Panel.fit(
            "\n".join(lines),
            title="Save Health",
            border_style="green" if report.integrity_ok and report.foreign_key_ok else "red",
        )
    )


@app.command("doctor")
def doctor_command(
    db_path: Path = DB_PATH_OPTION,
) -> None:
    """Print release, content, and save diagnostics for the local install."""

    save_status = "No save database found yet."
    slot_count = 0
    archive_count = 0
    schema_version = "-"
    if db_path.exists():
        coordinator = SaveLoadCoordinator(db_path)
        try:
            health = coordinator.check_save_health()
            archive_count = len(coordinator.list_run_archives())
        except PersistenceError as error:
            raise_cli_persistence_error("Doctor Failed", error)
        save_status = health.message
        slot_count = health.slot_count
        schema_version = str(health.schema_version)

    table = Table.grid(padding=(0, 1))
    table.add_row("Version", __version__)
    table.add_row("DB Path", str(db_path))
    table.add_row("DB Exists", "yes" if db_path.exists() else "no")
    table.add_row("Schema", schema_version)
    table.add_row("Save Slots", str(slot_count))
    table.add_row("Run Archives", str(archive_count))
    table.add_row("Scenarios", str(len(get_available_scenarios())))
    table.add_row("Templates", str(len(get_available_product_templates())))
    table.add_row("Rivals", str(len(get_available_competitor_archetypes())))
    table.add_row("Events", str(len(get_event_registry())))
    table.add_row("Save Status", save_status)

    console.print(
        Panel(
            table,
            title="NEXUS TECH Doctor",
            border_style="cyan",
            expand=True,
        )
    )


@app.command("rename-save")
def rename_save_command(
    slot: str = typer.Option(..., "--slot", help="Existing save slot name."),
    to_slot: str = typer.Option(..., "--to-slot", help="New save slot name."),
    db_path: Path = DB_PATH_OPTION,
) -> None:
    """Rename one local save slot."""

    coordinator = SaveLoadCoordinator(db_path)
    try:
        coordinator.rename_save(slot, to_slot)
    except PersistenceError as error:
        raise_cli_persistence_error("Rename Failed", error)

    console.print(
        Panel.fit(
            f"Renamed save slot '{slot}' to '{to_slot}'.",
            title="Rename Complete",
            border_style="green",
        )
    )


@app.command("delete-save")
def delete_save_command(
    slot: str = typer.Option(..., "--slot", help="Save slot name to remove."),
    db_path: Path = DB_PATH_OPTION,
    yes: bool = typer.Option(
        False,
        "--yes",
        help="Delete without asking for confirmation.",
    ),
) -> None:
    """Delete one local save slot."""

    if not yes and not typer.confirm(f"Delete save slot '{slot}'?"):
        console.print(
            Panel.fit(
                "Delete cancelled.",
                title="No Changes",
                border_style="yellow",
            )
        )
        raise typer.Exit()

    coordinator = SaveLoadCoordinator(db_path)
    try:
        coordinator.delete_save(slot)
    except PersistenceError as error:
        raise_cli_persistence_error("Delete Failed", error)

    console.print(
        Panel.fit(
            f"Deleted save slot '{slot}'.",
            title="Delete Complete",
            border_style="green",
        )
    )


@app.command("load-game")
def load_game_command(
    db_path: Path = DB_PATH_OPTION,
    slot: str = typer.Option(DEFAULT_SAVE_SLOT, "--slot", help="Save slot name."),
) -> None:
    """Load one named save slot and continue playing."""

    coordinator = SaveLoadCoordinator(db_path)
    try:
        loaded_game = coordinator.load_game(slot)
    except PersistenceError as error:
        raise_cli_persistence_error("Load Failed", error)

    logger.debug("Loaded save slot %s from %s.", loaded_game.slot_name, db_path)
    announce_loaded_game(
        db_path=db_path,
        slot_name=loaded_game.slot_name,
        seed=loaded_game.rng.seed,
        scenario_title=loaded_game.state.scenario_title,
    )
    run_game_loop(
        state=loaded_game.state,
        rng=loaded_game.rng,
        db_path=db_path,
        slot_name=loaded_game.slot_name,
    )


@app.command("load-game-2d")
def load_game_2d_command(
    db_path: Path = DB_PATH_OPTION,
    slot: str = typer.Option(DEFAULT_SAVE_SLOT, "--slot", help="Save slot name."),
    headless: bool = HEADLESS_2D_OPTION,
    window_size: str = WINDOW_SIZE_2D_OPTION,
    max_frames: int | None = MAX_FRAMES_2D_OPTION,
    motion_mode: MotionMode = MOTION_MODE_2D_OPTION,
) -> None:
    """Load one named save slot into the lightweight 2D dashboard."""

    coordinator = SaveLoadCoordinator(db_path)
    try:
        loaded_game = coordinator.load_game(slot)
    except PersistenceError as error:
        raise_cli_persistence_error("Load Failed", error)

    launch_2d_session(
        state=loaded_game.state,
        rng=loaded_game.rng,
        db_path=db_path,
        slot_name=loaded_game.slot_name,
        headless=headless,
        window_size=resolve_2d_window_size(window_size),
        max_frames=max_frames,
        motion_mode=motion_mode,
    )


@app.command("continue-last-game")
def continue_last_game_command(
    db_path: Path = DB_PATH_OPTION,
) -> None:
    """Load the most recently updated save slot."""

    coordinator = SaveLoadCoordinator(db_path)
    try:
        loaded_game = coordinator.continue_last_game()
    except PersistenceError as error:
        raise_cli_persistence_error("Load Failed", error)

    logger.debug("Continuing last save slot %s from %s.", loaded_game.slot_name, db_path)
    announce_loaded_game(
        db_path=db_path,
        slot_name=loaded_game.slot_name,
        seed=loaded_game.rng.seed,
        scenario_title=loaded_game.state.scenario_title,
    )
    run_game_loop(
        state=loaded_game.state,
        rng=loaded_game.rng,
        db_path=db_path,
        slot_name=loaded_game.slot_name,
    )


@app.command("continue-last-game-2d")
def continue_last_game_2d_command(
    db_path: Path = DB_PATH_OPTION,
    headless: bool = HEADLESS_2D_OPTION,
    window_size: str = WINDOW_SIZE_2D_OPTION,
    max_frames: int | None = MAX_FRAMES_2D_OPTION,
    motion_mode: MotionMode = MOTION_MODE_2D_OPTION,
) -> None:
    """Continue the latest save slot in the lightweight 2D dashboard."""

    coordinator = SaveLoadCoordinator(db_path)
    try:
        loaded_game = coordinator.continue_last_game()
    except PersistenceError as error:
        raise_cli_persistence_error("Load Failed", error)

    launch_2d_session(
        state=loaded_game.state,
        rng=loaded_game.rng,
        db_path=db_path,
        slot_name=loaded_game.slot_name,
        headless=headless,
        window_size=resolve_2d_window_size(window_size),
        max_frames=max_frames,
        motion_mode=motion_mode,
    )


@app.command("menu-2d")
def menu_2d_command(
    db_path: Path = DB_PATH_OPTION,
    headless: bool = HEADLESS_2D_OPTION,
    window_size: str = WINDOW_SIZE_2D_OPTION,
    max_frames: int | None = MAX_FRAMES_2D_OPTION,
    motion_mode: MotionMode = MOTION_MODE_2D_OPTION,
) -> None:
    """Open the 2D title scene with save/load and archive review."""

    try:
        result = launch_2d_menu(
            db_path=db_path,
            headless=headless,
            window_size=resolve_2d_window_size(window_size),
            max_frames=max_frames,
            motion_mode=motion_mode,
        )
    except Frontend2DUnavailableError as error:
        console.print(
            Panel.fit(
                str(error),
                title="2D Frontend Unavailable",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from error

    console.print(
        Panel.fit(
            (
                f"2D menu closed with reason '{result.exit_reason}'. "
                f"Slot '{result.slot_name}' remained available."
            ),
            title="2D Menu Closed",
            border_style="cyan",
        )
    )


def start_new_game(
    company_name: str | None,
    product_name: str | None,
    scenario_id: str,
    campaign_start_id: str,
    difficulty_mode: DifficultyMode | None,
    campaign_goal_id: CampaignGoalId | None,
    seed: int | None,
    db_path: Path,
    slot_name: str,
) -> None:
    """Create a brand new run and enter the interactive loop."""

    validate_scenario_id(scenario_id)
    validate_player_scenario_access(scenario_id, db_path=db_path)
    validate_campaign_start_id(campaign_start_id)
    validate_player_campaign_start_access(campaign_start_id, db_path=db_path)
    state = create_new_game(
        company_name=company_name,
        product_name=product_name,
        scenario_id=scenario_id,
        difficulty_mode=difficulty_mode,
        campaign_goal_id=campaign_goal_id,
        campaign_start_id=campaign_start_id,
    )
    campaign_start = get_campaign_start_definition(campaign_start_id)
    rng = RandomSource(seed=seed)
    logger.debug(
        "Starting new game scenario=%s campaign_start=%s company=%s product=%s seed=%s slot=%s.",
        scenario_id,
        campaign_start_id,
        state.company.name,
        state.products[0].name,
        seed,
        slot_name,
    )
    render_intro(
        console,
        company_name=state.company.name,
        scenario_title=state.scenario_title,
        campaign_start_title=campaign_start.title,
        difficulty_mode=state.difficulty_mode,
        campaign_goal_title=get_campaign_goal(state.campaign_goal_id).title,
        seed=seed,
    )
    run_game_loop(state=state, rng=rng, db_path=db_path, slot_name=slot_name)


def start_new_game_2d(
    company_name: str | None,
    product_name: str | None,
    scenario_id: str,
    campaign_start_id: str,
    difficulty_mode: DifficultyMode | None,
    campaign_goal_id: CampaignGoalId | None,
    seed: int | None,
    db_path: Path,
    slot_name: str,
    *,
    headless: bool,
    window_size: tuple[int, int],
    max_frames: int | None,
    motion_mode: MotionMode,
) -> None:
    """Create a brand new run and launch the lightweight 2D dashboard."""

    validate_scenario_id(scenario_id)
    validate_player_scenario_access(scenario_id, db_path=db_path)
    validate_campaign_start_id(campaign_start_id)
    validate_player_campaign_start_access(campaign_start_id, db_path=db_path)
    state = create_new_game(
        company_name=company_name,
        product_name=product_name,
        scenario_id=scenario_id,
        difficulty_mode=difficulty_mode,
        campaign_goal_id=campaign_goal_id,
        campaign_start_id=campaign_start_id,
    )
    rng = RandomSource(seed=seed)
    launch_2d_session(
        state=state,
        rng=rng,
        db_path=db_path,
        slot_name=slot_name,
        headless=headless,
        window_size=window_size,
        max_frames=max_frames,
        motion_mode=motion_mode,
    )


def launch_2d_session(
    *,
    state: GameState,
    rng: RandomSource,
    db_path: Path,
    slot_name: str,
    headless: bool,
    window_size: tuple[int, int],
    max_frames: int | None,
    motion_mode: MotionMode,
) -> None:
    """Launch one 2D dashboard session and print the closing summary."""

    try:
        result = launch_2d_frontend(
            state=state,
            rng=rng,
            db_path=db_path,
            slot_name=slot_name,
            headless=headless,
            window_size=window_size,
            max_frames=max_frames,
            motion_mode=motion_mode,
        )
    except Frontend2DUnavailableError as error:
        console.print(
            Panel.fit(
                str(error),
                title="2D Frontend Unavailable",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from error

    console.print(
        Panel.fit(
            (
                f"Closed 2D frontend ({result.exit_reason}). "
                f"{'Autosaved on exit.' if result.saved_on_exit else 'No autosave was needed.'}"
            ),
            title="2D Session Closed",
            border_style="cyan",
        )
    )


def run_game_loop(
    state: GameState,
    rng: RandomSource,
    db_path: Path,
    slot_name: str,
) -> None:
    """Run the terminal session until the company shuts down or the user exits."""

    try:
        while not state.company.game_over and not state.victory_achieved:
            if state.pending_event is not None:
                state = handle_pending_event(state)

            render_dashboard(console, state)
            turn_ended = False

            while not turn_ended and not state.company.game_over and not state.victory_achieved:
                choice = ask_choice_input(
                    "Choose an action",
                    choices=ALL_MENU_KEYS,
                    default="47",
                    show_choices=False,
                )

                if choice in UTILITY_ACTION_KEYS:
                    state, rng, slot_name = handle_utility_action(
                        action_name=UTILITY_ACTION_KEYS[choice],
                        state=state,
                        rng=rng,
                        db_path=db_path,
                        current_slot_name=slot_name,
                    )
                    if state.pending_event is not None:
                        state = handle_pending_event(state)
                    continue

                action = ACTION_KEYS[choice]

                try:
                    context = collect_action_context(state, action, db_path=db_path)
                    if context is None:
                        continue
                    if action is TurnAction.END_TURN and not confirm_end_turn(state):
                        continue

                    outcome = apply_action(state, action, context=context)
                except ValueError as error:
                    console.print(Panel.fit(str(error), title="Action Error", border_style="red"))
                    continue

                state = outcome.state

                if action is TurnAction.VIEW_STATUS:
                    render_dashboard(console, state)
                    continue

                if action is TurnAction.REVIEW_TEAM:
                    render_team_view(console, state)
                    continue

                if action is TurnAction.REVIEW_FINANCE:
                    render_report(console, state)
                    continue

                if action is TurnAction.REVIEW_CUSTOMERS:
                    render_customer_view(console, state)
                    continue

                if action is TurnAction.REVIEW_PIPELINE:
                    render_pipeline_view(console, state)
                    continue

                if action is TurnAction.REVIEW_BOARD:
                    render_board_view(console, state)
                    continue

                if action is TurnAction.REVIEW_PARTNERSHIPS:
                    render_partnership_view(console, state)
                    continue

                if action is TurnAction.VIEW_REPORT:
                    render_report(console, state)
                    continue

                render_action_feedback(
                    console,
                    action_label=action.value,
                    message=outcome.message,
                    state=state,
                )
                turn_ended = outcome.turn_should_end

            if state.company.game_over or state.victory_achieved:
                break

            resolution = resolve_turn(state, rng)
            state = resolution.state
            render_turn_resolution(console, resolution)

        if state.victory_achieved:
            render_victory(console, state)
        else:
            render_game_over(console, state)
    except KeyboardInterrupt as error:
        console.print("\n[bold yellow]Session interrupted.[/bold yellow]")
        raise typer.Exit(code=130) from error


def collect_action_context(
    state: GameState,
    action: TurnAction,
    *,
    db_path: Path,
) -> ActionContext | None:
    """Collect the optional context needed for a chosen action."""

    if action in (
        TurnAction.VIEW_STATUS,
        TurnAction.REVIEW_TEAM,
        TurnAction.REVIEW_FINANCE,
        TurnAction.REVIEW_CUSTOMERS,
        TurnAction.REVIEW_PIPELINE,
        TurnAction.REVIEW_BOARD,
        TurnAction.REVIEW_PARTNERSHIPS,
        TurnAction.VIEW_REPORT,
        TurnAction.END_TURN,
        TurnAction.WAIT,
        TurnAction.REORG_TEAM,
        TurnAction.EXECUTE_BOARD_RESPONSE,
        TurnAction.EXECUTE_RESTRUCTURE_PLAN,
        TurnAction.START_BOARD_RECOVERY_PLAN,
        TurnAction.INVEST_IN_SUPPORT_STAFFING,
        TurnAction.RUN_RENEWAL_SWEEP,
        TurnAction.RUN_ENTERPRISE_ASSURANCE,
        TurnAction.RUN_BILLING_STABILIZATION,
        TurnAction.RUN_ONBOARDING_RECOVERY,
        TurnAction.DEBT_ROLLOVER,
        TurnAction.STEP_UP_RESERVE_DISCIPLINE,
        TurnAction.HARDEN_FINANCING_POSTURE,
        TurnAction.LOCK_CAPITAL_BUFFER,
        TurnAction.REBALANCE_CHANNEL_MIX,
    ):
        return ActionContext()

    if action is TurnAction.REST_TEAM:
        if not state.employees:
            console.print(
                Panel.fit(
                    "No team has been hired yet.",
                    title="Selection Error",
                    border_style="red",
                )
            )
            return None
        return ActionContext()

    if action is TurnAction.CREATE_PRODUCT:
        product_template = choose_product_template(action, db_path=db_path)
        if product_template is None:
            return None
        return ActionContext(
            new_product_name=ask_text_input("New product name", default=product_template.title),
            new_product_template_id=product_template.template_id,
        )

    if action is TurnAction.SET_COMPANY_STRATEGY:
        strategy_key = ask_choice_input(
            "Company strategy",
            choices=["balanced", "growth", "quality", "efficiency"],
            default=state.company.strategy.value,
            show_choices=False,
            case_sensitive=False,
        )
        return ActionContext(strategy=CompanyStrategy(strategy_key))

    if action is TurnAction.SET_ROADMAP:
        roadmap_key = ask_choice_input(
            "Roadmap focus",
            choices=[
                "balanced_execution",
                "growth_push",
                "platform_rebuild",
                "premium_expansion",
                "portfolio_consolidation",
                "ai_trust_program",
                "community_growth",
                "enterprise_sales_push",
            ],
            default=state.roadmap_focus.value,
            show_choices=False,
            case_sensitive=False,
        )
        return ActionContext(roadmap_focus=RoadmapFocus(roadmap_key))

    if action is TurnAction.SET_BUDGET_STANCE:
        budget_key = ask_choice_input(
            "Budget stance",
            choices=["lean", "balanced", "aggressive"],
            default=state.quarter_plan.budget_stance.value,
            show_choices=False,
            case_sensitive=False,
        )
        return ActionContext(budget_stance=BudgetStance(budget_key))

    if action is TurnAction.SET_FUNCTIONAL_BUDGET:
        budget_key = ask_choice_input(
            "Functional budget",
            choices=[
                "balanced",
                "product_push",
                "growth_push",
                "customer_trust",
                "cash_guard",
            ],
            default=state.functional_budget.preset.value,
            show_choices=False,
            case_sensitive=False,
        )
        return ActionContext(functional_budget_preset=FunctionalBudgetPreset(budget_key))

    if action is TurnAction.SET_CAPITAL_PLAN:
        mode_key = ask_choice_input(
            "Capital plan mode",
            choices=["conserve", "balanced", "expand"],
            default=state.capital_plan.mode.value,
            show_choices=False,
            case_sensitive=False,
        )
        source_key = ask_choice_input(
            "Capital source bias",
            choices=["bootstrap", "debt", "angel", "venture"],
            default=state.capital_plan.source_preference.value,
            show_choices=False,
            case_sensitive=False,
        )
        plan_mode = CapitalPlanMode(mode_key)
        source_preference = CapitalSourcePreference(source_key)
        plan_profile = get_capital_plan_profile(plan_mode, source_preference)
        customization_mode = ask_choice_input(
            "Capital plan shape",
            choices=["profile", "custom"],
            default="profile",
            show_choices=False,
            case_sensitive=False,
        )
        if customization_mode == "profile":
            return ActionContext(
                capital_plan_mode=plan_mode,
                capital_source_preference=source_preference,
            )

        horizon_turns = ask_int_input(
            "Planning horizon (turns)",
            default=plan_profile.planning_horizon_turns,
            minimum=2,
            maximum=12,
        )
        reserve_target = ask_decimal_input(
            "Reserve target",
            default=plan_profile.reserve_target,
            minimum=Decimal("0.00"),
        )
        while True:
            product_share = ask_int_input(
                "Product investment share",
                default=plan_profile.product_investment_share,
                minimum=0,
                maximum=100,
            )
            go_to_market_share = ask_int_input(
                "Go-to-market share",
                default=plan_profile.go_to_market_share,
                minimum=0,
                maximum=100,
            )
            reserve_share = ask_int_input(
                "Reserve share",
                default=plan_profile.reserve_share,
                minimum=0,
                maximum=100,
            )
            total_share = product_share + go_to_market_share + reserve_share
            if total_share == 100:
                break
            console.print(
                Panel.fit(
                    (
                        "Capital allocation shares must total exactly 100.\n"
                        f"Current total: {total_share}"
                    ),
                    title="Allocation Error",
                    border_style="yellow",
                )
            )
        return ActionContext(
            capital_plan_mode=plan_mode,
            capital_source_preference=source_preference,
            capital_plan_horizon_turns=horizon_turns,
            capital_plan_reserve_target=reserve_target,
            capital_plan_product_share=product_share,
            capital_plan_go_to_market_share=go_to_market_share,
            capital_plan_reserve_share=reserve_share,
        )

    if action is TurnAction.HIRE_EMPLOYEE:
        candidate_seed = (state.company.current_turn * 101) + (len(state.employees) * 17)
        candidates = generate_candidate_pool(RandomSource(seed=candidate_seed))
        render_candidate_pool(console, candidates)
        candidate_choices = [str(index) for index in range(1, len(candidates) + 1)]
        selected_candidate = ask_choice_input(
            "Candidate number or custom",
            choices=[*candidate_choices, "custom"],
            default="1",
            show_choices=False,
            case_sensitive=False,
        )
        if selected_candidate != "custom":
            candidate = candidates[int(selected_candidate) - 1]
            return ActionContext(
                hire_full_name=candidate.full_name,
                hire_role=candidate.role,
                hire_seniority=candidate.seniority,
                hire_specialization=candidate.specialization,
                hire_trait=candidate.trait,
            )

        full_name = ask_text_input("Employee full name")
        role_key = ask_choice_input(
            "Role",
            choices=["engineer", "designer", "marketer", "product_manager"],
            default="engineer",
            case_sensitive=False,
        )
        seniority_key = ask_choice_input(
            "Seniority",
            choices=["junior", "mid", "senior"],
            default="mid",
            case_sensitive=False,
        )
        default_specialization = BALANCE.employee_default_specializations[role_key]
        specialization = ask_text_input(
            "Specialization",
            default=default_specialization,
        )
        trait_key = ask_choice_input(
            "Trait",
            choices=["steady_operator", "fast_learner", "expensive_expert", "burnout_risk"],
            default="steady_operator",
            show_choices=False,
            case_sensitive=False,
        )
        return ActionContext(
            hire_full_name=full_name,
            hire_role=EmployeeRole(role_key),
            hire_seniority=Seniority(seniority_key),
            hire_specialization=specialization,
            hire_trait=CandidateTrait(trait_key),
        )

    if action is TurnAction.FIRE_EMPLOYEE:
        employee_id = choose_employee_id(state, action)
        if employee_id is None:
            return None
        return ActionContext(employee_id=employee_id)

    if action in {
        TurnAction.TRAIN_EMPLOYEE,
        TurnAction.PROMOTE_EMPLOYEE,
        TurnAction.RUN_COMP_REVIEW,
        TurnAction.RUN_SUCCESSION_REVIEW,
    }:
        employee_id = choose_employee_id(state, action)
        if employee_id is None:
            return None
        return ActionContext(employee_id=employee_id)

    if action is TurnAction.SOURCE_CANDIDATES:
        return ActionContext()

    if action is TurnAction.SCREEN_CANDIDATE:
        candidate_id = choose_hiring_candidate_id(
            state,
            stage=HiringCandidateStage.SOURCED,
            action_label=action.value,
        )
        if candidate_id is None:
            return None
        return ActionContext(hiring_candidate_id=candidate_id)

    if action is TurnAction.INTERVIEW_CANDIDATE:
        candidate_id = choose_hiring_candidate_id(
            state,
            stage=HiringCandidateStage.SCREENED,
            action_label=action.value,
        )
        if candidate_id is None:
            return None
        return ActionContext(hiring_candidate_id=candidate_id)

    if action is TurnAction.MAKE_HIRING_OFFER:
        candidate_id = choose_hiring_candidate_id(
            state,
            stage=HiringCandidateStage.INTERVIEWED,
            action_label=action.value,
        )
        if candidate_id is None:
            return None
        return ActionContext(hiring_candidate_id=candidate_id)

    if action is TurnAction.TRIAGE_SUPPORT_BACKLOG:
        return ActionContext()

    if action is TurnAction.REBALANCE_CAPITAL:
        return ActionContext()

    if action is TurnAction.RAISE_RESERVE_TARGET:
        return ActionContext()

    if action is TurnAction.SET_SUPPORT_LANE_FOCUS:
        focus_key = ask_choice_input(
            "Support lane focus",
            choices=["balanced", "onboarding", "enterprise", "billing"],
            default=state.support_program.lane_focus.value,
            show_choices=False,
            case_sensitive=False,
        )
        return ActionContext(support_lane_focus=SupportLaneFocus(focus_key))

    if action is TurnAction.UPGRADE_SUPPORT_PROGRAM:
        focus_key = ask_choice_input(
            "Support investment focus",
            choices=["knowledge_base", "automation", "sla_program"],
            default="knowledge_base",
            show_choices=False,
            case_sensitive=False,
        )
        return ActionContext(support_investment_focus=SupportInvestmentFocus(focus_key))

    if action is TurnAction.UNASSIGN_EMPLOYEE:
        employee_id = choose_employee_id(state, action, assigned_only=True)
        if employee_id is None:
            return None
        return ActionContext(employee_id=employee_id)

    if action is TurnAction.ASSIGN_EMPLOYEE:
        employee_id = choose_employee_id(state, action)
        if employee_id is None:
            return None
        product_id = choose_product_id(state, action)
        if product_id is None:
            return None
        return ActionContext(employee_id=employee_id, target_product_id=product_id)

    if action is TurnAction.ASSIGN_MANAGER:
        employee_id = choose_employee_id(state, action)
        if employee_id is None:
            return None
        manager_id = choose_manager_id(state, exclude_employee_id=employee_id)
        if manager_id is None:
            return None
        return ActionContext(employee_id=employee_id, manager_id=manager_id)

    if action is TurnAction.CLEAR_MANAGER:
        managed_employee_id = choose_employee_id(state, action, manager_assigned_only=True)
        if managed_employee_id is None:
            return None
        return ActionContext(employee_id=managed_employee_id)

    if action is TurnAction.APPOINT_TEAM_LEAD:
        employee_id = choose_employee_id(state, action, assigned_only=True)
        if employee_id is None:
            return None
        return ActionContext(employee_id=employee_id)

    if action is TurnAction.INVEST_IN_CUSTOMER_SUCCESS:
        product_id = choose_product_id(state, action)
        if product_id is None:
            return None
        return ActionContext(target_product_id=product_id)

    if action is TurnAction.RUN_RETENTION_PLAY:
        customer_account_id = choose_customer_account_id(state, at_risk_only=True)
        if customer_account_id is None:
            customer_account_id = choose_customer_account_id(state, at_risk_only=False)
            if customer_account_id is None:
                return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.MAKE_RENEWAL_OFFER:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        offer_type_key = ask_choice_input(
            "Renewal offer type",
            choices=["light_discount", "bundle_upgrade", "term_extension"],
            default="light_discount",
            show_choices=False,
            case_sensitive=False,
        )
        return ActionContext(
            customer_account_id=customer_account_id,
            renewal_offer_type=RenewalOfferType(offer_type_key),
        )

    if action is TurnAction.RUN_WIN_BACK_PLAY:
        customer_account_id = choose_customer_account_id(
            state,
            at_risk_only=False,
            churned_only=True,
        )
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.ROUTE_SUPPORT_ESCALATION:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ACCOUNT_RESCUE:
        customer_account_id = choose_customer_account_id(state, at_risk_only=True)
        if customer_account_id is None:
            customer_account_id = choose_customer_account_id(state, at_risk_only=False)
            if customer_account_id is None:
                return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_REFERENCE_RESCUE:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ENTERPRISE_REFERENCE_CYCLE:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ENTERPRISE_RENEWAL_CABINET:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_BILLING_RETENTION_RESET:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_BILLING_COVENANT_RESET:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ONBOARDING_FAST_TRACK:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ENTERPRISE_QUEUE_RESET:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_WHITE_GLOVE_RECOVERY:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_WHITE_GLOVE_BACKSTOP:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_WHITE_GLOVE_RENEWAL_GUARD:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_WHITE_GLOVE_REFERENCE_RING:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_WHITE_GLOVE_REFERENCE_COMMITTEE:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_WHITE_GLOVE_ESCALATION_CELL:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_WHITE_GLOVE_REFERENCE_BUREAU:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ENTERPRISE_COMMITMENT_BOARD:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ENTERPRISE_REFERENCE_CHAMBER:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ENTERPRISE_REFERENCE_FORUM:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ENTERPRISE_REFERENCE_LATTICE:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ENTERPRISE_REFERENCE_SUMMIT:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ENTERPRISE_REFERENCE_DIRECTORATE:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ENTERPRISE_REFERENCE_SECRETARIAT:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ENTERPRISE_REFERENCE_AUTHORITY:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ENTERPRISE_REFERENCE_COMMISSION:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)
    if action is TurnAction.RUN_ENTERPRISE_REFERENCE_OVERSIGHT:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)
    if action is TurnAction.RUN_ENTERPRISE_REFERENCE_COUNCIL:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)
    if action is TurnAction.RUN_ENTERPRISE_REFERENCE_WATCH:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_WHITE_GLOVE_REFERENCE_EXCHANGE:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_BILLING_DISPUTE_DESK:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_BILLING_DISPUTE_CABINET:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_BILLING_COLLECTION_BRIDGE:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_BILLING_COLLECTION_OFFICE:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_BILLING_SETTLEMENT_BOARD:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_BILLING_CASH_WAR_ROOM:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_BILLING_LIQUIDITY_COMMAND:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_BILLING_LIQUIDITY_SUMMIT:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_BILLING_LIQUIDITY_DIRECTORATE:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_BILLING_LIQUIDITY_SECRETARIAT:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_BILLING_LIQUIDITY_AUTHORITY:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_BILLING_LIQUIDITY_COMMISSION:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)
    if action is TurnAction.RUN_BILLING_LIQUIDITY_OVERSIGHT:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)
    if action is TurnAction.RUN_BILLING_LIQUIDITY_COUNCIL:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)
    if action is TurnAction.RUN_BILLING_RENEWAL_WATCH:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ONBOARDING_CONTROL_TOWER:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ONBOARDING_LAUNCH_CELL:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ONBOARDING_ADOPTION_HUB:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ONBOARDING_STABILITY_BOARD:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ONBOARDING_RETENTION_MESH:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ONBOARDING_ASSURANCE_GRID:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ONBOARDING_DURABILITY_MESH:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ONBOARDING_CONTINUITY_LATTICE:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ONBOARDING_CONTINUITY_BUREAU:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ONBOARDING_CONTINUITY_SECRETARIAT:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ONBOARDING_CONTINUITY_AUTHORITY:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_ONBOARDING_CONTINUITY_COMMISSION:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)
    if action is TurnAction.RUN_ONBOARDING_CONTINUITY_OVERSIGHT:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)
    if action is TurnAction.RUN_ONBOARDING_CONTINUITY_COUNCIL:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)
    if action is TurnAction.RUN_ONBOARDING_GO_LIVE_WATCH:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_WHITE_GLOVE_RETENTION_WATCH:
        customer_account_id = choose_customer_account_id(state, at_risk_only=False)
        if customer_account_id is None:
            return None
        return ActionContext(customer_account_id=customer_account_id)

    if action is TurnAction.RUN_LANE_RECOVERY:
        focus_key = ask_choice_input(
            "Recovery lane",
            choices=["onboarding", "enterprise", "billing"],
            default=state.support_program.lane_focus.value
            if state.support_program.lane_focus is not SupportLaneFocus.BALANCED
            else "enterprise",
            show_choices=False,
            case_sensitive=False,
        )
        return ActionContext(support_lane_focus=SupportLaneFocus(focus_key))

    if action is TurnAction.CREATE_PARTNERSHIP:
        product_id = choose_product_id(state, action)
        if product_id is None:
            return None
        channel_key = ask_choice_input(
            "Partner channel",
            choices=["reseller", "integration", "marketplace"],
            default="reseller",
            show_choices=False,
            case_sensitive=False,
        )
        return ActionContext(
            target_product_id=product_id,
            partner_channel=PartnerChannel(channel_key),
        )

    if action is TurnAction.INVEST_IN_PARTNER_ENABLEMENT:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RUN_CHANNEL_QBR:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RUN_PARTNER_RECOVERY_SPRINT:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RUN_CHANNEL_FIREBREAK:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RUN_CHANNEL_CONFLICT_RESET:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RUN_CHANNEL_REALIGNMENT:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RUN_CHANNEL_SYNERGY_RESET:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RUN_PARTNER_MARGIN_RESET:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RUN_CHANNEL_STABILITY_RESET:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RUN_CHANNEL_DEPENDENCY_RESET:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RUN_CHANNEL_CONFIDENCE_FIREWALL:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RUN_CHANNEL_DURABILITY_MESH:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RUN_CHANNEL_CONFLICT_LATTICE:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RUN_CHANNEL_RESILIENCE_GRID:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RUN_CHANNEL_CONTINUITY_MATRIX:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RUN_CHANNEL_ASSURANCE_COVENANT:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RUN_CHANNEL_DURABILITY_STATUTE:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RUN_CHANNEL_DURABILITY_MANDATE:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RUN_CHANNEL_DURABILITY_COMMISSION:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)
    if action is TurnAction.RUN_CHANNEL_DURABILITY_OVERSIGHT:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)
    if action is TurnAction.RUN_CHANNEL_DURABILITY_COUNCIL:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RUN_RESELLER_ENABLEMENT_RESET:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RUN_INTEGRATION_CUTOVER_RESET:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RUN_MARKETPLACE_CHARGEBACK_RESET:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.RENEGOTIATE_PARTNERSHIP:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.REACTIVATE_PARTNERSHIP:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.PAUSE_PARTNERSHIP:
        partnership_id = choose_partnership_id(state)
        if partnership_id is None:
            return None
        return ActionContext(partnership_id=partnership_id)

    if action is TurnAction.PLAN_RELEASE:
        product_id = choose_product_id(state, action)
        if product_id is None:
            return None
        release_type_key = ask_choice_input(
            "Release type",
            choices=["stability_patch", "minor_release", "major_launch"],
            default="minor_release",
            show_choices=False,
            case_sensitive=False,
        )
        return ActionContext(
            target_product_id=product_id,
            release_type=ProductReleaseType(release_type_key),
        )

    if action is TurnAction.WORK_RELEASE:
        release_id = choose_release_id(state)
        if release_id is None:
            return None
        return ActionContext(release_id=release_id)

    if action is TurnAction.CREATE_SALES_DEAL:
        product_id = choose_product_id(state, action)
        if product_id is None:
            return None
        return ActionContext(target_product_id=product_id)

    if action is TurnAction.ADVANCE_SALES_DEAL:
        sales_deal_id = choose_sales_deal_id(state)
        if sales_deal_id is None:
            return None
        return ActionContext(sales_deal_id=sales_deal_id)

    if action is TurnAction.START_ROADMAP_PROJECT:
        project_type_key = ask_choice_input(
            "Roadmap project",
            choices=[
                "platform_rebuild",
                "enterprise_certification",
                "marketplace_launch",
                "sales_playbook",
            ],
            default="platform_rebuild",
            show_choices=False,
            case_sensitive=False,
        )
        project_type = RoadmapProjectType(project_type_key)
        product_id = None
        if project_type is not RoadmapProjectType.SALES_PLAYBOOK:
            product_id = choose_product_id(state, action)
            if product_id is None:
                return None
        return ActionContext(
            roadmap_project_type=project_type,
            target_product_id=product_id,
        )

    if action is TurnAction.WORK_ROADMAP_PROJECT:
        roadmap_project_id = choose_roadmap_project_id(state)
        if roadmap_project_id is None:
            return None
        return ActionContext(roadmap_project_id=roadmap_project_id)

    if action in PRODUCT_TARGETED_ACTIONS:
        product_id = choose_product_id(state, action)
        if product_id is None:
            return None
        if action is TurnAction.ADJUST_PRICING:
            pricing_key = ask_choice_input(
                "Pricing tier",
                choices=["budget", "standard", "premium"],
                default="standard",
                show_choices=False,
                case_sensitive=False,
            )
            return ActionContext(
                target_product_id=product_id,
                pricing_tier=PricingTier(pricing_key),
            )
        if action is TurnAction.SET_PACKAGING_STRATEGY:
            product = next(product for product in state.products if product.id == product_id)
            packaging_key = ask_choice_input(
                "Packaging strategy",
                choices=["streamlined", "modular", "suite"],
                default=product.packaging_strategy.value,
                show_choices=False,
                case_sensitive=False,
            )
            return ActionContext(
                target_product_id=product_id,
                packaging_strategy=PackagingStrategy(packaging_key),
            )
        if action is TurnAction.SET_TARGET_SEGMENT:
            product = next(product for product in state.products if product.id == product_id)
            segment_key = ask_choice_input(
                "Target segment",
                choices=["indie", "startup", "smb", "enterprise"],
                default=product.target_segment.value,
                show_choices=False,
                case_sensitive=False,
            )
            return ActionContext(
                target_product_id=product_id,
                target_segment=MarketSegment(segment_key),
            )
        return ActionContext(target_product_id=product_id)

    return ActionContext()


def choose_product_id(state: GameState, action: TurnAction) -> UUID | None:
    """Prompt the user to select a product for an action."""

    products = get_product_choices(state, active_only=True)
    if not products:
        console.print(
            Panel.fit(
                "No active products are available. Create a product first.",
                title="Selection Error",
                border_style="red",
            )
        )
        return None

    product_choices = {str(index): product for index, product in enumerate(products, start=1)}
    label = action.value.replace("_", " ")
    render_product_picker(console, products, action_label=action.value)
    selected_key = ask_choice_input(
        f"Select a product for {label}",
        choices=list(product_choices),
        default="1",
        show_choices=False,
    )
    product = product_choices[selected_key]
    logger.debug("Selected product %s for action %s.", product.name, action.value)
    console.print(
        Panel.fit(
            build_product_selection_summary(product),
            title="Target Selected",
            border_style="blue",
        )
    )
    return product.id


def choose_product_template(
    action: TurnAction,
    *,
    db_path: Path,
) -> ProductTemplateDefinition | None:
    """Prompt the user to select a product template for creation."""

    templates = [
        template
        for template in get_available_product_templates()
        if _is_content_available(
            reward_type="template",
            reward_id=template.template_id,
            db_path=db_path,
        )
    ]
    if not templates:
        console.print(
            Panel.fit(
                "No unlocked product templates are available in this install yet.",
                title="Selection Error",
                border_style="red",
            )
        )
        return None

    template_choices = {str(index): template for index, template in enumerate(templates, start=1)}
    render_product_template_picker(console, templates, action_label=action.value)
    selected_key = ask_choice_input(
        "Select a product template",
        choices=list(template_choices),
        default="1",
        show_choices=False,
    )
    template = template_choices[selected_key]
    logger.debug("Selected product template %s.", template.template_id)
    console.print(
        Panel.fit(
            build_product_template_summary(template),
            title="Template Selected",
            border_style="blue",
        )
    )
    return template


def choose_employee_id(
    state: GameState,
    action: TurnAction,
    assigned_only: bool | None = None,
    manager_assigned_only: bool = False,
) -> UUID | None:
    """Prompt the user to select an employee for an action."""

    employees = get_employee_choices(state, assigned_only=assigned_only)
    if manager_assigned_only:
        employees = [employee for employee in employees if employee.manager_id is not None]
    if not employees:
        console.print(
            Panel.fit(
                "No matching employees are available for that action.",
                title="Selection Error",
                border_style="red",
            )
        )
        return None

    employee_choices = {str(index): employee for index, employee in enumerate(employees, start=1)}
    label = action.value.replace("_", " ")
    render_employee_picker(console, employees, state.products, action_label=action.value)
    selected_key = ask_choice_input(
        f"Select an employee for {label}",
        choices=list(employee_choices),
        default="1",
        show_choices=False,
    )
    employee = employee_choices[selected_key]
    logger.debug("Selected employee %s for action %s.", employee.full_name, action.value)
    console.print(
        Panel.fit(
            build_employee_selection_summary(employee, state.products, state.employees),
            title="Target Selected",
            border_style="blue",
        )
    )
    return employee.id


def choose_manager_id(
    state: GameState,
    *,
    exclude_employee_id: UUID,
) -> UUID | None:
    """Prompt the user to select an eligible manager."""

    eligible_managers = [
        employee
        for employee in state.employees
        if employee.id != exclude_employee_id
        and (
            employee.role is EmployeeRole.PRODUCT_MANAGER
            or employee.seniority is Seniority.SENIOR
            or employee.leadership_score >= 68
        )
    ]
    if not eligible_managers:
        console.print(
            Panel.fit(
                "No eligible managers are available yet. Promote someone or hire leadership depth.",
                title="Selection Error",
                border_style="red",
            )
        )
        return None

    employee_choices = {
        str(index): employee for index, employee in enumerate(eligible_managers, start=1)
    }
    render_employee_picker(
        console,
        eligible_managers,
        state.products,
        action_label="assign_manager",
    )
    selected_key = ask_choice_input(
        "Select a manager",
        choices=list(employee_choices),
        default="1",
        show_choices=False,
    )
    manager = employee_choices[selected_key]
    console.print(
        Panel.fit(
            build_employee_selection_summary(manager, state.products, state.employees),
            title="Manager Selected",
            border_style="blue",
        )
    )
    return manager.id


def choose_hiring_candidate_id(
    state: GameState,
    *,
    stage: HiringCandidateStage,
    action_label: str,
) -> UUID | None:
    """Prompt the user to select a hiring candidate for pipeline work."""

    candidates = [candidate for candidate in state.hiring_candidates if candidate.stage is stage]
    if not candidates:
        console.print(
            Panel.fit(
                f"No candidates are in the '{stage.value}' stage right now.",
                title="Selection Error",
                border_style="red",
            )
        )
        return None

    table = Table(box=None, expand=True)
    table.add_column("#", justify="right")
    table.add_column("Candidate", style="bold")
    table.add_column("Role")
    table.add_column("Seniority")
    table.add_column("Stage")
    table.add_column("Accept", justify="right")
    table.add_column("Salary+", justify="right")
    table.add_column("Offer By", justify="right")
    table.add_column("Salary", justify="right")
    for index, candidate in enumerate(candidates, start=1):
        table.add_row(
            str(index),
            candidate.full_name,
            candidate.role.value,
            candidate.seniority.value,
            candidate.stage.value,
            f"{candidate.acceptance_chance}%",
            str(candidate.market_salary_pressure),
            str(candidate.offer_deadline_turn),
            str(candidate.salary_expectation),
        )
    console.print(Panel(table, title="Hiring Pipeline", border_style="cyan", expand=True))
    choices = {str(index): candidate for index, candidate in enumerate(candidates, start=1)}
    selected_key = ask_choice_input(
        f"Select a candidate for {action_label.replace('_', ' ')}",
        choices=list(choices),
        default="1",
        show_choices=False,
    )
    return choices[selected_key].id


def choose_customer_account_id(
    state: GameState,
    *,
    at_risk_only: bool,
    churned_only: bool = False,
) -> UUID | None:
    """Prompt the user to select a customer account for retention work."""

    accounts = get_customer_choices(
        state,
        at_risk_only=at_risk_only,
        churned_only=churned_only,
    )
    if not accounts:
        if at_risk_only or churned_only:
            return None
        console.print(
            Panel.fit(
                "No active customer accounts are available for that action.",
                title="Selection Error",
                border_style="red",
            )
        )
        return None

    table = Table(box=None, expand=True)
    table.add_column("#", justify="right")
    table.add_column("Account", style="bold")
    table.add_column("Status")
    table.add_column("Value", justify="right")
    table.add_column("Risk", justify="right")
    for index, account in enumerate(accounts, start=1):
        table.add_row(
            str(index),
            account.name,
            account.status.value,
            f"${account.contract_value}",
            str(account.churn_risk),
        )
    console.print(Panel(table, title="Customer Accounts", border_style="green", expand=True))
    choices = {str(index): account for index, account in enumerate(accounts, start=1)}
    selected_key = ask_choice_input(
        "Select a customer account",
        choices=list(choices),
        default="1",
        show_choices=False,
    )
    return choices[selected_key].id


def choose_partnership_id(state: GameState) -> UUID | None:
    """Prompt the user to select one active partnership."""

    partnerships = get_partnership_choices(state, actionable_only=True)
    if not partnerships:
        console.print(
            Panel.fit(
                "No active partnerships are available yet. Create one first.",
                title="Selection Error",
                border_style="red",
            )
        )
        return None

    product_names = {product.id: product.name for product in state.products}
    table = Table(box=None, expand=True)
    table.add_column("#", justify="right")
    table.add_column("Partner", style="bold")
    table.add_column("Product")
    table.add_column("Channel")
    table.add_column("Status")
    table.add_column("Enable", justify="right")
    table.add_column("Risk", justify="right")
    for index, partnership in enumerate(partnerships, start=1):
        table.add_row(
            str(index),
            partnership.name,
            product_names.get(partnership.product_id, "unknown"),
            partnership.channel.value,
            partnership.status.value,
            str(partnership.enablement_level),
            str(partnership.risk),
        )
    console.print(Panel(table, title="Partnerships", border_style="magenta", expand=True))
    choices = {str(index): partnership for index, partnership in enumerate(partnerships, start=1)}
    selected_key = ask_choice_input(
        "Select a partnership",
        choices=list(choices),
        default="1",
        show_choices=False,
    )
    return choices[selected_key].id


def choose_release_id(state: GameState) -> UUID | None:
    """Prompt the user to select an active release plan."""

    releases = [
        release
        for release in state.product_releases
        if release.status is ProductReleaseStatus.PLANNED
    ]
    if not releases:
        console.print(
            Panel.fit(
                "No planned releases are active. Plan a release first.",
                title="Selection Error",
                border_style="red",
            )
        )
        return None

    product_names = {product.id: product.name for product in state.products}
    table = Table(box=None, expand=True)
    table.add_column("#", justify="right")
    table.add_column("Product")
    table.add_column("Type")
    table.add_column("Progress", justify="right")
    table.add_column("Risk", justify="right")
    for index, release in enumerate(releases, start=1):
        table.add_row(
            str(index),
            product_names.get(release.product_id, "unknown"),
            release.release_type.value,
            f"{release.progress}/{release.required_progress}",
            str(release.risk),
        )
    console.print(Panel(table, title="Active Releases", border_style="blue", expand=True))
    choices = {str(index): release for index, release in enumerate(releases, start=1)}
    selected_key = ask_choice_input(
        "Select a release",
        choices=list(choices),
        default="1",
        show_choices=False,
    )
    return choices[selected_key].id


def choose_sales_deal_id(state: GameState) -> UUID | None:
    """Prompt the user to select an active sales deal."""

    deals = [
        deal
        for deal in state.sales_deals
        if deal.stage not in {SalesDealStage.CLOSED_WON, SalesDealStage.CLOSED_LOST}
    ]
    if not deals:
        console.print(
            Panel.fit(
                "No active sales deals are available. Create a sales deal first.",
                title="Selection Error",
                border_style="red",
            )
        )
        return None

    product_names = {product.id: product.name for product in state.products}
    table = Table(box=None, expand=True)
    table.add_column("#", justify="right")
    table.add_column("Deal")
    table.add_column("Product")
    table.add_column("Stage")
    table.add_column("Prob", justify="right")
    for index, deal in enumerate(deals, start=1):
        table.add_row(
            str(index),
            deal.name,
            product_names.get(deal.product_id, "unknown"),
            deal.stage.value,
            f"{deal.probability}%",
        )
    console.print(Panel(table, title="Active Sales Deals", border_style="green", expand=True))
    choices = {str(index): deal for index, deal in enumerate(deals, start=1)}
    selected_key = ask_choice_input(
        "Select a sales deal",
        choices=list(choices),
        default="1",
        show_choices=False,
    )
    return choices[selected_key].id


def choose_roadmap_project_id(state: GameState) -> UUID | None:
    """Prompt the user to select an active roadmap project."""

    projects = [
        project
        for project in state.roadmap_projects
        if project.status is RoadmapProjectStatus.ACTIVE
    ]
    if not projects:
        console.print(
            Panel.fit(
                "No active roadmap project exists. Start one first.",
                title="Selection Error",
                border_style="red",
            )
        )
        return None

    product_names = {product.id: product.name for product in state.products}
    table = Table(box=None, expand=True)
    table.add_column("#", justify="right")
    table.add_column("Project")
    table.add_column("Target")
    table.add_column("Progress", justify="right")
    for index, project in enumerate(projects, start=1):
        table.add_row(
            str(index),
            project.project_type.value,
            product_names.get(project.target_product_id, "company-wide"),
            f"{project.progress}/{project.required_progress}",
        )
    console.print(
        Panel(table, title="Active Roadmap Projects", border_style="magenta", expand=True)
    )
    choices = {str(index): project for index, project in enumerate(projects, start=1)}
    selected_key = ask_choice_input(
        "Select a roadmap project",
        choices=list(choices),
        default="1",
        show_choices=False,
    )
    return choices[selected_key].id


def handle_pending_event(state: GameState) -> GameState:
    """Prompt for an event choice and apply its effect immediately."""

    pending_event = state.pending_event
    if pending_event is None:
        return state

    render_pending_event(console, pending_event)
    option_id = choose_event_option_id(pending_event)
    outcome = resolve_pending_event(state, option_id)
    render_event_result(console, outcome.history_entry)
    return outcome.state


def choose_event_option_id(pending_event: PendingEvent) -> str:
    """Prompt for a response to a pending event."""

    option_choices = {
        str(index): option for index, option in enumerate(pending_event.options, start=1)
    }
    selected_key = ask_choice_input(
        "Choose an event response",
        choices=list(option_choices),
        default="1",
        show_choices=False,
    )
    return option_choices[selected_key].id


def ask_choice_input(
    prompt: str,
    *,
    choices: list[str],
    default: str,
    show_choices: bool,
    case_sensitive: bool = True,
) -> str:
    """Ask for a constrained choice and exit cleanly if the session input closes."""

    try:
        return Prompt.ask(
            prompt,
            console=console,
            choices=choices,
            default=default,
            show_choices=show_choices,
            case_sensitive=case_sensitive,
        )
    except EOFError as error:
        handle_prompt_abort("Input stream closed. Ending the session.", error, exit_code=1)
    except KeyboardInterrupt as error:
        handle_prompt_abort("Session interrupted.", error, exit_code=130)


def ask_text_input(prompt: str, *, default: str | None = None) -> str:
    """Ask for free-form text and keep retrying until a non-empty value is given."""

    while True:
        try:
            if default is None:
                value = Prompt.ask(
                    prompt,
                    console=console,
                    show_default=False,
                    show_choices=False,
                )
            else:
                value = Prompt.ask(
                    prompt,
                    console=console,
                    default=default,
                    show_choices=False,
                )
        except EOFError as error:
            handle_prompt_abort("Input stream closed. Ending the session.", error, exit_code=1)
        except KeyboardInterrupt as error:
            handle_prompt_abort("Session interrupted.", error, exit_code=130)

        cleaned_value = value.strip()
        if cleaned_value:
            return cleaned_value

        console.print(
            Panel.fit(
                "Enter a value before continuing.",
                title="Input Needed",
                border_style="yellow",
            )
        )


def ask_confirm_input(prompt: str, *, default: bool) -> bool:
    """Ask for a yes/no confirmation and exit cleanly if input closes."""

    try:
        return Confirm.ask(
            prompt,
            console=console,
            default=default,
            show_choices=False,
        )
    except EOFError as error:
        handle_prompt_abort("Input stream closed. Ending the session.", error, exit_code=1)
    except KeyboardInterrupt as error:
        handle_prompt_abort("Session interrupted.", error, exit_code=130)


def ask_int_input(
    prompt: str,
    *,
    default: int,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """Ask for an integer input with bounded validation."""

    while True:
        raw_value = ask_text_input(prompt, default=str(default))
        try:
            value = int(raw_value)
        except ValueError:
            console.print(
                Panel.fit(
                    "Enter a whole number.",
                    title="Input Needed",
                    border_style="yellow",
                )
            )
            continue

        if minimum is not None and value < minimum:
            console.print(
                Panel.fit(
                    f"Value must be at least {minimum}.",
                    title="Input Needed",
                    border_style="yellow",
                )
            )
            continue
        if maximum is not None and value > maximum:
            console.print(
                Panel.fit(
                    f"Value must be at most {maximum}.",
                    title="Input Needed",
                    border_style="yellow",
                )
            )
            continue
        return value


def ask_decimal_input(
    prompt: str,
    *,
    default: Decimal,
    minimum: Decimal | None = None,
) -> Decimal:
    """Ask for a Decimal input with lightweight validation."""

    while True:
        raw_value = ask_text_input(prompt, default=str(default))
        try:
            value = Decimal(raw_value)
        except InvalidOperation:
            console.print(
                Panel.fit(
                    "Enter a numeric amount.",
                    title="Input Needed",
                    border_style="yellow",
                )
            )
            continue

        if minimum is not None and value < minimum:
            console.print(
                Panel.fit(
                    f"Value must be at least {minimum}.",
                    title="Input Needed",
                    border_style="yellow",
                )
            )
            continue
        return value


def handle_prompt_abort(message: str, error: BaseException, *, exit_code: int) -> None:
    """Render a clean prompt-abort message and stop the CLI."""

    console.print(Panel.fit(message, title="Session Ended", border_style="yellow"))
    raise typer.Exit(code=exit_code) from error


def confirm_end_turn(state: GameState) -> bool:
    """Require explicit confirmation when the preview shows a risky end-turn state."""

    preview = build_end_turn_preview(state)
    if preview.blocked or not preview.requires_confirmation:
        return True

    summary = Table.grid(padding=(0, 1))
    summary.add_row("Warning", preview.warning_level)
    summary.add_row("Risk Shift", preview.risk_shift)
    summary.add_row("Projected Outcome", preview.projected_outcome)
    summary.add_row("Do First", preview.top_command)
    summary.add_row("Reason", preview.confirmation_reason)
    console.print(
        Panel(
            summary,
            title="End-Turn Warning",
            border_style="red" if preview.warning_level == "critical" else "yellow",
            expand=True,
        )
    )
    confirmed = ask_confirm_input("End the turn anyway?", default=False)
    if not confirmed:
        console.print(
            Panel.fit(
                f"Turn held open. Run `{preview.top_command}` first.",
                title="End Turn Cancelled",
                border_style="yellow",
            )
        )
    return confirmed


def build_product_selection_summary(product: Product) -> str:
    """Show concise per-product stats before an action."""

    return (
        f"{product.name}\n"
        f"Stage: {product.lifecycle_stage.value} | Users: {product.user_count} | "
        f"Quality: {product.quality} | Bugs: {product.bug_level} | "
        f"Fit: {product.market_fit} | Debt: {product.technical_debt} | "
        f"Segment: {product.target_segment.value} | Pricing: {product.pricing_tier.value} | "
        f"Packaging: {product.packaging_strategy.value} | "
        f"PackCat: {product.package_catalog_depth} | AddOns: {product.add_on_catalog_depth}"
    )


def build_product_template_summary(template: ProductTemplateDefinition) -> str:
    """Show concise template stats before creating a product."""

    return (
        f"{template.title}\n"
        f"{template.description}\n"
        f"Stage: {template.lifecycle_stage.value} | Quality: {template.quality} | "
        f"Bugs: {template.bug_level} | Fit: {template.market_fit} | "
        f"Debt: {template.technical_debt} | Segment: {template.target_segment.value} | "
        f"Pricing: {template.pricing_tier.value} | Packaging: {template.packaging_strategy.value}"
    )


def build_employee_selection_summary(
    employee: Employee,
    products: list[Product],
    employees: list[Employee],
) -> str:
    """Show concise employee stats before an action."""

    product_names = {product.id: product.name for product in products}
    assignment_name = product_names.get(employee.assigned_product_id, "unassigned")
    manager_name = next(
        (teammate.full_name for teammate in employees if teammate.id == employee.manager_id),
        None,
    )
    return (
        f"{employee.full_name}\n"
        f"Role: {employee.role.value} | Seniority: {employee.seniority.value} | "
        f"Trait: {employee.trait.value} | "
        f"Energy: {employee.energy} | Morale: {employee.morale} | "
        f"Assignment: {assignment_name} | "
        f"Leadership: {employee.leadership_score} | "
        f"Manager: {manager_name or 'none'}"
    )


def handle_utility_action(
    action_name: str,
    state: GameState,
    rng: RandomSource,
    db_path: Path,
    current_slot_name: str,
) -> tuple[GameState, RandomSource, str]:
    """Handle non-simulation utility actions from the CLI menu."""

    coordinator = SaveLoadCoordinator(db_path)

    if action_name == "save_game":
        slot_name = ask_text_input("Save slot", default=current_slot_name)
        try:
            coordinator.save_game(slot_name=slot_name, state=state, rng=rng)
        except PersistenceError as error:
            console.print(Panel.fit(str(error), title="Save Failed", border_style="red"))
            return state, rng, current_slot_name

        logger.debug("Saved game to slot %s at %s.", slot_name, db_path)
        console.print(
            Panel.fit(
                f"Saved game to slot '{slot_name}' at {db_path}.",
                title="Save Complete",
                border_style="green",
            )
        )
        return state, rng, slot_name

    if action_name == "load_game":
        slot_name = ask_text_input("Load slot", default=current_slot_name)
        try:
            loaded_game = coordinator.load_game(slot_name)
        except PersistenceError as error:
            console.print(Panel.fit(str(error), title="Load Failed", border_style="red"))
            return state, rng, current_slot_name

        logger.debug("Loaded game from slot %s at %s.", loaded_game.slot_name, db_path)
        console.print(
            Panel.fit(
                f"Loaded slot '{loaded_game.slot_name}' from {db_path}.",
                title="Load Complete",
                border_style="green",
            )
        )
        return loaded_game.state, loaded_game.rng, loaded_game.slot_name

    if action_name == "show_guide":
        render_quick_guide(console)
        return state, rng, current_slot_name

    if action_name == "show_glossary":
        render_glossary(console)
        return state, rng, current_slot_name

    if action_name == "show_tutorial":
        render_tutorial(console)
        return state, rng, current_slot_name

    raise ValueError(f"Unsupported utility action: {action_name}")


def announce_loaded_game(
    db_path: Path,
    slot_name: str,
    seed: int | None,
    scenario_title: str,
) -> None:
    """Print a concise load banner before entering the loop."""

    seed_text = seed if seed is not None else "random"
    console.print(
        Panel.fit(
            (
                f"Loaded slot '{slot_name}' from {db_path}\n"
                f"Scenario: {scenario_title}\n"
                f"Seed: {seed_text}"
            ),
            title="Continue Game",
            border_style="green",
        )
    )


def configure_cli(debug: bool) -> None:
    """Configure console logging and traceback behavior for the CLI session."""

    global console, DEBUG_MODE

    console = Console(highlight=False, soft_wrap=True)
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.WARNING,
        format="%(message)s",
        handlers=[
            RichHandler(
                console=console,
                show_time=False,
                show_path=debug,
                markup=True,
                rich_tracebacks=debug,
                tracebacks_show_locals=debug,
            )
        ],
        force=True,
    )
    DEBUG_MODE = debug
    if debug:
        install_rich_traceback(console=console, show_locals=True)
        logger.debug("Debug mode enabled.")


def raise_cli_persistence_error(title: str, error: PersistenceError) -> None:
    """Render a persistence failure and exit the command."""

    logger.error("%s: %s", title, error)
    console.print(Panel.fit(str(error), title=title, border_style="red"))
    raise typer.Exit(code=1)


def validate_scenario_id(scenario_id: str) -> None:
    """Exit cleanly when a requested scenario id is unknown."""

    available_ids = {scenario.scenario_id for scenario in get_available_scenarios()}
    if scenario_id in available_ids:
        return
    examples = "\n".join(f"- {scenario_id}" for scenario_id in sorted(available_ids)[:6])
    console.print(
        Panel.fit(
            (
                f"Unknown scenario '{scenario_id}'.\n"
                f"Example scenario ids:\n{examples}\n"
                "Run `nexus-tech list-scenarios` to inspect the full catalog."
            ),
            title="Invalid Scenario",
            border_style="red",
        )
    )
    raise typer.Exit(code=1)


def validate_player_scenario_access(scenario_id: str, *, db_path: Path) -> None:
    """Exit cleanly when a player-targeted scenario is still progression-locked."""

    if _is_content_available(
        reward_type="scenario",
        reward_id=scenario_id,
        db_path=db_path,
    ):
        return
    console.print(
        Panel.fit(
            (
                f"Scenario '{scenario_id}' is still locked for this local profile.\n"
                "Archive more completed runs and review `nexus-tech list-unlocks` "
                "or `nexus-tech show-progression`."
            ),
            title="Scenario Locked",
            border_style="yellow",
        )
    )
    raise typer.Exit(code=1)


def validate_campaign_start_id(campaign_start_id: str) -> None:
    """Exit cleanly when a requested campaign start id is unknown."""

    available_ids = {entry.start_id for entry in list_campaign_starts()}
    if campaign_start_id in available_ids:
        return
    examples = "\n".join(f"- {start_id}" for start_id in sorted(available_ids))
    console.print(
        Panel.fit(
            (
                f"Unknown campaign start '{campaign_start_id}'.\n"
                f"Available campaign start ids:\n{examples}\n"
                "Run `nexus-tech list-campaign-starts` to inspect the full catalog."
            ),
            title="Invalid Campaign Start",
            border_style="red",
        )
    )
    raise typer.Exit(code=1)


def validate_player_campaign_start_access(campaign_start_id: str, *, db_path: Path) -> None:
    """Exit cleanly when a selected campaign start is still progression-locked."""

    definition = get_campaign_start_definition(campaign_start_id)
    if definition.unlock_reward_id is None or definition.unlock_reward_type is None:
        return
    if _is_content_available(
        reward_type=definition.unlock_reward_type,
        reward_id=definition.unlock_reward_id,
        db_path=db_path,
    ):
        return
    console.print(
        Panel.fit(
            (
                f"Campaign start '{campaign_start_id}' is still locked for this local profile.\n"
                "Archive more completed runs and review `nexus-tech list-unlocks` "
                "or `nexus-tech show-progression`."
            ),
            title="Campaign Start Locked",
            border_style="yellow",
        )
    )
    raise typer.Exit(code=1)


def resolve_scenario_ids(scenario_ids: list[str] | None) -> list[str]:
    """Resolve optional scenario CLI input and validate all ids."""

    if scenario_ids is None:
        return [entry.scenario_id for entry in get_available_scenarios()]
    for scenario_id in scenario_ids:
        validate_scenario_id(scenario_id)
    return scenario_ids


def _load_archives_for_progression(db_path: Path) -> list[RunArchiveSummary]:
    """Return archived runs for progression-aware catalog decisions."""

    if not db_path.exists():
        return []
    coordinator = SaveLoadCoordinator(db_path)
    try:
        return coordinator.list_run_archives()
    except PersistenceError:
        return []


def _is_content_available(*, reward_type: str, reward_id: str, db_path: Path) -> bool:
    archives = _load_archives_for_progression(db_path)
    return is_reward_unlocked(
        archives,
        reward_type=reward_type,
        reward_id=reward_id,
    )


def _build_locked_content_ids(*, reward_type: str, db_path: Path) -> set[str]:
    archives = _load_archives_for_progression(db_path)
    return {
        reward_id
        for reward_id in get_locked_reward_ids(reward_type)
        if not is_reward_unlocked(
            archives,
            reward_type=reward_type,
            reward_id=reward_id,
        )
    }


def _build_locked_campaign_start_ids(*, db_path: Path) -> set[str]:
    return {
        definition.start_id
        for definition in list_campaign_starts()
        if definition.unlock_reward_id is not None
        and definition.unlock_reward_type is not None
        and not _is_content_available(
            reward_type=definition.unlock_reward_type,
            reward_id=definition.unlock_reward_id,
            db_path=db_path,
        )
    }


def main() -> None:
    """CLI wrapper used by `python -m` and console scripts."""

    try:
        app()
    except typer.Exit:
        raise
    except Exception as error:
        if DEBUG_MODE:
            console.print_exception(show_locals=True)
        else:
            console.print(
                Panel.fit(
                    f"{type(error).__name__}: {error}",
                    title="Unexpected Error",
                    border_style="red",
                )
            )
        raise typer.Exit(code=1) from None


if __name__ == "__main__":
    main()
