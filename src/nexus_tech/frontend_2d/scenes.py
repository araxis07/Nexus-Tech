"""Scene objects for the lightweight 2D frontend."""

from __future__ import annotations

import re
from dataclasses import dataclass
from math import sin
from typing import Callable

from nexus_tech.domain.models import GameState, TurnAction
from nexus_tech.domain.money import format_money
from nexus_tech.frontend_2d.catalog import (
    CampaignGoalChoice,
    CampaignStartChoice,
    DifficultyChoice,
    ScenarioChoice,
    list_campaign_goal_choices,
    list_campaign_start_choices,
    list_difficulty_choices,
    list_scenario_choices,
)
from nexus_tech.frontend_2d.context import (
    ActionRequest,
    ContextPicker,
    PickerOption,
    build_command_request,
    build_inspector_action_request,
    explain_command_unavailable,
    explain_inspector_action_unavailable,
)
from nexus_tech.frontend_2d.control_guide import RUN_HELP_KEYCAPS
from nexus_tech.frontend_2d.event_queue import (
    FrontendEvent,
    build_action_events,
    build_turn_resolution_events,
)
from nexus_tech.frontend_2d.input_map import FrontendIntent
from nexus_tech.frontend_2d.layout import build_frame_layout, resolve_layout_profile
from nexus_tech.frontend_2d.outcome_presentation import build_outcome_overlay_view_model
from nexus_tech.frontend_2d.panel_disclosure import build_panel_disclosure
from nexus_tech.frontend_2d.tween import MotionMode, PulseBank, TweenBank, normalize_motion_mode
from nexus_tech.frontend_2d.viewmodels import (
    ArchiveCardViewModel,
    DeepDivePanelViewModel,
    RunReviewViewModel,
    SaveSlotCardViewModel,
    TurnSummaryViewModel,
    build_archive_card_view_models,
    build_archive_review_view_model,
    build_game_view_model,
    build_run_review_view_model,
    build_save_slot_card_view_models,
    build_turn_summary_view_model,
)
from nexus_tech.frontend_2d.widgets import (
    BACKGROUND,
    BORDER,
    DANGER,
    GOOD,
    INFO,
    MUTED,
    PANEL,
    SELECTION,
    TEXT,
    WARN,
    FontPack,
    blend_color,
    draw_button,
    draw_grid,
    draw_keycap,
    draw_panel,
    draw_progress_bar,
    draw_text_line,
    draw_wrapped_text,
    fit_text_line,
    tone_color,
)
from nexus_tech.persistence.errors import PersistenceError
from nexus_tech.persistence.save_coordinator import (
    RunArchiveSummary,
    SaveLoadCoordinator,
    SaveSlotSummary,
)
from nexus_tech.simulation.action_catalog import get_action_label
from nexus_tech.simulation.end_turn_preview import build_end_turn_preview
from nexus_tech.simulation.engine import ActionContext, apply_action, create_new_game, resolve_turn
from nexus_tech.simulation.first_archive_mission import (
    FirstArchiveMission,
    build_first_archive_mission,
)
from nexus_tech.simulation.meta_progression import (
    ArchiveComparisonSummary,
    MetaProgressionSummary,
    build_archive_comparison,
    summarize_meta_progression,
)
from nexus_tech.simulation.opening_guide import build_guided_opening
from nexus_tech.simulation.randomness import RandomSource
from nexus_tech.user_preferences import ActionLoadout, FrontendPreferences


@dataclass(frozen=True)
class ClickTarget:
    """One clickable hitbox registered during the last draw pass."""

    kind: str
    payload: str
    rect: object


@dataclass(frozen=True)
class ActionButtonSpec:
    """One visible action button in the 2D action bar."""

    key_hint: str
    title: str
    detail: str
    accent: tuple[int, int, int]
    kind: str
    payload: str


@dataclass(frozen=True)
class FirstTurnGuideStep:
    """One compact onboarding checkpoint rendered inside the live run dashboard."""

    label: str
    detail: str
    done: bool
    accent: tuple[int, int, int]


@dataclass
class TimedFrontendEvent:
    """Mutable event card with time remaining."""

    payload: FrontendEvent
    time_left: float


@dataclass(frozen=True)
class ActionFeedbackCue:
    """Short-lived command-specific animation feedback."""

    command: str
    label: str
    family: str
    accent: tuple[int, int, int]
    targets: tuple[str, ...]
    time_left: float
    duration: float
    outcome: str = "success"
    detail: str = ""


@dataclass(frozen=True)
class ImpactCue:
    """Short-lived visible delta feedback after state-changing actions."""

    label: str
    value_text: str
    tone: str
    accent: tuple[int, int, int]
    targets: tuple[str, ...]
    time_left: float
    duration: float


@dataclass(frozen=True)
class OverlayExitCue:
    """Short exit shimmer after a modal overlay closes."""

    key: str
    label: str
    accent: tuple[int, int, int]
    time_left: float
    duration: float


@dataclass(frozen=True)
class PendingChoiceCue:
    """Short consequence flash after resolving a pending event choice."""

    label: str
    detail: str
    accent: tuple[int, int, int]
    time_left: float
    duration: float


@dataclass(frozen=True)
class LateGameChoreographyCue:
    """Short late-game command cue tied to cockpit, capital, and board lanes."""

    command: str
    label: str
    detail: str
    family: str
    accent: tuple[int, int, int]
    targets: tuple[str, ...]
    time_left: float
    duration: float


@dataclass(frozen=True)
class ActorSpriteClip:
    """One deterministic shape-sprite actor beat rendered by the 2D frontend."""

    key: str
    label: str
    role: str
    state: str
    accent: tuple[int, int, int]
    lane: str
    delay: float = 0.0
    phase_offset: float = 0.0
    pose: str | None = None

    @property
    def pose_key(self) -> str:
        """Return the readable pose cue used by the lightweight sprite renderer."""

        return _actor_pose_key(self.state, self.pose)


@dataclass(frozen=True)
class ActorSpriteBounds:
    """One actor sprite footprint from the last draw pass."""

    key: str
    lane: str
    left: int
    top: int
    width: int
    height: int


@dataclass
class TextInputModalState:
    """One live text-input modal used by the 2D frontend."""

    title: str
    description: str
    severity: str
    submit_title: str
    submit_detail: str
    text: str
    placeholder: str
    on_submit: Callable[[str], None]


@dataclass
class NewGameWizardState:
    """Mutable configuration used by the 2D new-game wizard."""

    scenario_index: int
    difficulty_index: int
    campaign_start_index: int
    goal_index: int
    company_name: str
    product_name: str
    slot_name: str
    seed_text: str = ""


@dataclass(frozen=True)
class InspectorMemoryState:
    """Remember one panel's last inspector focus so reopening is less noisy."""

    section_key: str
    page: int
    item_index: int
    sort_mode_index: int
    filter_mode_index: int


def _fit_modal_rect(pygame, surface, *, width: int, height: int, margin: int = 24):
    """Clamp a centered modal rect so it stays inside smaller windows."""

    window_width, window_height = surface.get_size()
    safe_width = min(width, max(320, window_width - margin * 2))
    safe_height = min(height, max(240, window_height - margin * 2))
    return pygame.Rect(
        window_width // 2 - safe_width // 2,
        window_height // 2 - safe_height // 2,
        safe_width,
        safe_height,
    )


def _fit_nav_safe_modal_rect(
    pygame,
    surface,
    *,
    width: int,
    height: int,
    margin: int = 24,
    nav_bottom: int = 60,
):
    """Fit a tall modal inside the workspace below the persistent navigation rail."""

    window_width, window_height = surface.get_size()
    safe_width = min(width, max(320, window_width - margin * 2))
    usable_height = max(240, window_height - margin - nav_bottom)
    safe_height = min(height, usable_height)
    top = nav_bottom + max(0, (usable_height - safe_height) // 2)
    return pygame.Rect(
        window_width // 2 - safe_width // 2,
        top,
        safe_width,
        safe_height,
    )


_ACTION_BUTTONS: tuple[ActionButtonSpec, ...] = (
    ActionButtonSpec("C", "Coach", "Run the top mission-board command.", INFO, "coach", ""),
    ActionButtonSpec(
        "N",
        "New Product",
        "Name and create one product.",
        INFO,
        "text_command",
        TurnAction.CREATE_PRODUCT.value,
    ),
    ActionButtonSpec("1", "Team", "Open team staffing panel.", GOOD, "panel", "team"),
    ActionButtonSpec("2", "Finance", "Open finance and capital panel.", WARN, "panel", "finance"),
    ActionButtonSpec(
        "3",
        "Customers",
        "Open pricing, segment, and support panel.",
        INFO,
        "panel",
        "customers",
    ),
    ActionButtonSpec(
        "4",
        "Partners",
        "Open channel and partner panel.",
        INFO,
        "panel",
        "partnerships",
    ),
    ActionButtonSpec("5", "Board", "Open board and governance panel.", WARN, "panel", "board"),
    ActionButtonSpec(
        "6",
        "Pipeline",
        "Open delivery, deals, and hiring panel.",
        INFO,
        "panel",
        "pipeline",
    ),
    ActionButtonSpec(
        "7",
        "Report",
        "Open run-summary and reporting panel.",
        INFO,
        "panel",
        "report",
    ),
    ActionButtonSpec(
        "8",
        "Endgame",
        "Open exit readiness and late-game gate board.",
        WARN,
        "panel",
        "endgame",
    ),
    ActionButtonSpec(
        "Q",
        "Improve",
        "Invest in product quality.",
        GOOD,
        "command",
        TurnAction.IMPROVE_QUALITY.value,
    ),
    ActionButtonSpec(
        "F",
        "Feature",
        "Add one feature to the selected product.",
        INFO,
        "command",
        TurnAction.ADD_FEATURE.value,
    ),
    ActionButtonSpec(
        "M",
        "Market",
        "Push demand for the selected product.",
        INFO,
        "command",
        TurnAction.MARKET_PRODUCT.value,
    ),
    ActionButtonSpec(
        "D",
        "Debt Down",
        "Reduce technical debt on the selected product.",
        WARN,
        "command",
        TurnAction.REDUCE_TECHNICAL_DEBT.value,
    ),
    ActionButtonSpec(
        "H",
        "Hire",
        "Pick the next role to add.",
        INFO,
        "command",
        TurnAction.HIRE_EMPLOYEE.value,
    ),
    ActionButtonSpec(
        "A",
        "Assign",
        "Pick an idle teammate for the selected product.",
        GOOD,
        "command",
        TurnAction.ASSIGN_EMPLOYEE.value,
    ),
    ActionButtonSpec(
        "Y",
        "Strategy",
        "Choose the company posture.",
        INFO,
        "command",
        TurnAction.SET_COMPANY_STRATEGY.value,
    ),
    ActionButtonSpec(
        "R",
        "Roadmap",
        "Choose the multi-turn focus.",
        INFO,
        "command",
        TurnAction.SET_ROADMAP.value,
    ),
    ActionButtonSpec(
        "B",
        "Budget",
        "Choose quarter spending posture.",
        WARN,
        "command",
        TurnAction.SET_BUDGET_STANCE.value,
    ),
    ActionButtonSpec(
        "U",
        "Support",
        "Choose the service lane focus.",
        WARN,
        "command",
        TurnAction.SET_SUPPORT_LANE_FOCUS.value,
    ),
    ActionButtonSpec(
        "O",
        "Partner",
        "Open a partner channel for the selected product.",
        INFO,
        "command",
        TurnAction.CREATE_PARTNERSHIP.value,
    ),
    ActionButtonSpec(
        "L",
        "Loan",
        "Take debt if runway is tightening.",
        WARN,
        "command",
        TurnAction.TAKE_LOAN.value,
    ),
    ActionButtonSpec(
        "G",
        "Angel",
        "Raise an angel round if traction supports it.",
        INFO,
        "command",
        TurnAction.RAISE_ANGEL.value,
    ),
    ActionButtonSpec("S", "Save", "Persist the active run.", INFO, "save", ""),
    ActionButtonSpec(
        "Space",
        "End Turn",
        "Resolve the turn with preview and warning gate.",
        DANGER,
        "command",
        TurnAction.END_TURN.value,
    ),
)

_ACTION_LOADOUT_COMMANDS: dict[ActionLoadout, tuple[str, ...]] = {
    ActionLoadout.CONTEXTUAL: (),
    ActionLoadout.PRODUCT: (
        TurnAction.IMPROVE_QUALITY.value,
        TurnAction.ADD_FEATURE.value,
    ),
    ActionLoadout.GROWTH: (
        TurnAction.MARKET_PRODUCT.value,
        TurnAction.CREATE_PARTNERSHIP.value,
    ),
    ActionLoadout.RESILIENCE: (
        TurnAction.REDUCE_TECHNICAL_DEBT.value,
        TurnAction.SET_SUPPORT_LANE_FOCUS.value,
    ),
}

_INSPECTOR_SORT_MODES: tuple[str, ...] = ("default", "risk", "value", "stalled")
_INSPECTOR_FILTER_MODES: tuple[str, ...] = ("all", "actionable", "attention")
_TONE_PRIORITY = {"danger": 3, "warning": 2, "info": 1, "success": 0}
_MOTION_INTENSITY = {"success": 0.55, "info": 0.42, "warning": 0.75, "danger": 1.0}
_SCENE_TRANSITION_LABELS = {
    "boot_title": ("Title Boot", INFO),
    "boot_run": ("Run Boot", INFO),
    "title_to_run": ("Entering Run", GOOD),
    "run_to_title": ("Back To Menu", INFO),
    "title_to_review": ("Archive Review", INFO),
    "review_to_title": ("Back To Archives", INFO),
    "run_to_summary": ("Resolving Turn", WARN),
    "run_to_review": ("Run Review", DANGER),
    "summary_to_run": ("Return Focus", GOOD),
    "summary_to_review": ("Final Review", DANGER),
}
_FINANCE_PANEL_COMMANDS = {
    TurnAction.REVIEW_FINANCE.value,
    TurnAction.TAKE_LOAN.value,
    TurnAction.RAISE_ANGEL.value,
    TurnAction.RAISE_VC.value,
    TurnAction.REPAY_DEBT.value,
    TurnAction.REFINANCE_DEBT.value,
    TurnAction.DEBT_ROLLOVER.value,
    TurnAction.REBALANCE_CAPITAL.value,
    TurnAction.RAISE_RESERVE_TARGET.value,
    TurnAction.SET_CAPITAL_PLAN.value,
    TurnAction.SET_REFINANCING_POSTURE.value,
    TurnAction.SET_COVENANT_FIREWALL.value,
    TurnAction.SET_DEBT_STRATEGY.value,
    TurnAction.SET_GROWTH_FIREBREAK.value,
    TurnAction.SET_PATH_CAPITAL_POSTURE.value,
    TurnAction.SET_ENDGAME_CAPITAL_MAP.value,
    TurnAction.SET_EXIT_READINESS_BUFFER.value,
    TurnAction.SET_TERMINAL_LIQUIDITY_CONTROLS.value,
    TurnAction.SET_CAPITAL_REALLOCATION_GRID.value,
    TurnAction.SET_PATH_CONTROL_MATRIX.value,
    TurnAction.SET_PATH_RESILIENCE_GRID.value,
    TurnAction.SET_BALANCE_SHEET_RECOVERY_MESH.value,
    TurnAction.SET_TERMINAL_RECOVERY_LATTICE.value,
    TurnAction.SET_TERMINAL_CONTINUITY_MATRIX.value,
    TurnAction.SET_TERMINAL_RESILIENCE_COVENANT.value,
    TurnAction.SET_TERMINAL_SOLVENCY_STATUTE.value,
    TurnAction.SET_TERMINAL_SOLVENCY_MANDATE.value,
    TurnAction.SET_TERMINAL_SOLVENCY_COMMISSION.value,
    TurnAction.SET_TERMINAL_SOLVENCY_OVERSIGHT.value,
    TurnAction.SET_TERMINAL_SOLVENCY_COUNCIL.value,
    TurnAction.SET_PATH_CASH_WATERFALL.value,
    TurnAction.SET_BOARD_RESET_CONTINGENCY_BUFFER.value,
    TurnAction.STEP_UP_RESERVE_DISCIPLINE.value,
    TurnAction.HARDEN_FINANCING_POSTURE.value,
    TurnAction.LOCK_CAPITAL_BUFFER.value,
}
_TEAM_PANEL_COMMANDS = {
    TurnAction.REVIEW_TEAM.value,
    TurnAction.HIRE_EMPLOYEE.value,
    TurnAction.FIRE_EMPLOYEE.value,
    TurnAction.ASSIGN_EMPLOYEE.value,
    TurnAction.UNASSIGN_EMPLOYEE.value,
    TurnAction.REST_TEAM.value,
    TurnAction.TRAIN_EMPLOYEE.value,
    TurnAction.PROMOTE_EMPLOYEE.value,
    TurnAction.RUN_COMP_REVIEW.value,
    TurnAction.RUN_SUCCESSION_REVIEW.value,
    TurnAction.APPOINT_TEAM_LEAD.value,
    TurnAction.ASSIGN_MANAGER.value,
    TurnAction.CLEAR_MANAGER.value,
    TurnAction.REORG_TEAM.value,
}
_PIPELINE_PANEL_COMMANDS = {
    TurnAction.REVIEW_PIPELINE.value,
    TurnAction.PLAN_RELEASE.value,
    TurnAction.WORK_RELEASE.value,
    TurnAction.CREATE_SALES_DEAL.value,
    TurnAction.ADVANCE_SALES_DEAL.value,
    TurnAction.START_ROADMAP_PROJECT.value,
    TurnAction.WORK_ROADMAP_PROJECT.value,
    TurnAction.SOURCE_CANDIDATES.value,
    TurnAction.SCREEN_CANDIDATE.value,
    TurnAction.INTERVIEW_CANDIDATE.value,
    TurnAction.MAKE_HIRING_OFFER.value,
}
_BOARD_PANEL_COMMANDS = {
    TurnAction.REVIEW_BOARD.value,
    TurnAction.EXECUTE_BOARD_RESPONSE.value,
    TurnAction.START_BOARD_RECOVERY_PLAN.value,
    TurnAction.EXECUTE_RESTRUCTURE_PLAN.value,
}
_CUSTOMER_PANEL_COMMANDS = {
    TurnAction.REVIEW_CUSTOMERS.value,
    TurnAction.ADJUST_PRICING.value,
    TurnAction.SET_PACKAGING_STRATEGY.value,
    TurnAction.SET_TARGET_SEGMENT.value,
    TurnAction.INVEST_IN_CUSTOMER_SUCCESS.value,
    TurnAction.RUN_RETENTION_PLAY.value,
    TurnAction.MAKE_RENEWAL_OFFER.value,
    TurnAction.RUN_WIN_BACK_PLAY.value,
    TurnAction.ROUTE_SUPPORT_ESCALATION.value,
    TurnAction.RUN_ACCOUNT_RESCUE.value,
    TurnAction.RUN_LANE_RECOVERY.value,
    TurnAction.RUN_RENEWAL_SWEEP.value,
    TurnAction.RUN_ENTERPRISE_ASSURANCE.value,
    TurnAction.RUN_BILLING_STABILIZATION.value,
    TurnAction.RUN_ONBOARDING_RECOVERY.value,
    TurnAction.RUN_ONBOARDING_FAST_TRACK.value,
    TurnAction.TRIAGE_SUPPORT_BACKLOG.value,
    TurnAction.INVEST_IN_SUPPORT_STAFFING.value,
    TurnAction.SET_SUPPORT_LANE_FOCUS.value,
    TurnAction.UPGRADE_SUPPORT_PROGRAM.value,
}
_PARTNERSHIP_PANEL_COMMANDS = {
    TurnAction.CREATE_PARTNERSHIP.value,
    TurnAction.INVEST_IN_PARTNER_ENABLEMENT.value,
    TurnAction.RUN_CHANNEL_QBR.value,
    TurnAction.REBALANCE_CHANNEL_MIX.value,
    TurnAction.RENEGOTIATE_PARTNERSHIP.value,
    TurnAction.REACTIVATE_PARTNERSHIP.value,
    TurnAction.PAUSE_PARTNERSHIP.value,
    TurnAction.REVIEW_PARTNERSHIPS.value,
}


def _workspace_panel_key_for_command(command: str) -> str | None:
    if command in _TEAM_PANEL_COMMANDS:
        return "team"
    if command in _FINANCE_PANEL_COMMANDS:
        return "finance"
    if command in _PIPELINE_PANEL_COMMANDS:
        return "pipeline"
    if command in _BOARD_PANEL_COMMANDS:
        return "board"
    if command in _CUSTOMER_PANEL_COMMANDS:
        return "customers"
    if command in _PARTNERSHIP_PANEL_COMMANDS:
        return "partnerships"
    if command == TurnAction.VIEW_REPORT.value:
        return "report"
    if command.startswith(
        (
            "run_enterprise_",
            "run_billing_",
            "run_onboarding_",
            "run_white_glove_",
            "run_reference_",
        )
    ):
        return "customers"
    if command.startswith(
        (
            "run_channel_",
            "run_partner_",
            "run_reseller_",
            "run_integration_",
            "run_marketplace_",
        )
    ):
        return "partnerships"
    return None


def _short_actor_text(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[: max(1, max_length - 1)]}."


def _fit_actor_caption(font: object, clip: ActorSpriteClip, max_width: int) -> str:
    """Keep the actor's role readable before falling back to its lane."""

    candidates = (f"{clip.role} / {clip.lane}", clip.role, clip.lane)
    for candidate in candidates:
        if font.size(candidate)[0] <= max_width:
            return candidate
    return fit_text_line(font, clip.role, max_width)


def _actor_state_badge(state: str) -> str:
    return {
        "alert": "!",
        "risk": "!",
        "success": "+",
        "handoff": ">",
        "build": "#",
        "blocked": "x",
        "coaching": "?",
        "negotiating": "$",
        "shipping": ">",
        "firefighting": "!",
        "celebrating": "+",
    }.get(state, ".")


_ACTOR_STATE_POSES: dict[str, str] = {
    "idle": "steady",
    "build": "build",
    "handoff": "handoff",
    "shipping": "handoff",
    "success": "win",
    "celebrating": "win",
    "coaching": "coach",
    "negotiating": "deal",
    "risk": "warn",
    "alert": "warn",
    "blocked": "block",
    "firefighting": "fire",
}

_ACTOR_POSE_BADGES: dict[str, str] = {
    "steady": "I",
    "build": "B",
    "handoff": ">",
    "win": "+",
    "coach": "?",
    "deal": "$",
    "warn": "!",
    "block": "X",
    "fire": "!",
}


def _actor_pose_key(state: str, pose: str | None = None) -> str:
    return pose or _ACTOR_STATE_POSES.get(state, "steady")


def _actor_pose_badge(pose: str) -> str:
    return _ACTOR_POSE_BADGES.get(pose, ".")


def _actor_pose_color(pose: str, accent: tuple[int, int, int]) -> tuple[int, int, int]:
    if pose in {"warn", "fire", "block"}:
        return DANGER if pose == "block" else WARN
    if pose == "win":
        return GOOD
    return blend_color(accent, INFO if pose in {"coach", "handoff"} else TEXT, 0.22)


def _draw_actor_sprite_clip(
    *,
    pygame,
    fonts: FontPack,
    surface,
    rect,
    clip: ActorSpriteClip,
    elapsed: float,
    intensity: float,
) -> None:
    """Draw one lightweight actor sprite without external image assets."""

    if intensity <= 0 or rect.width < 72 or rect.height < 40:
        return
    enter = 1.0
    if clip.delay > 0:
        enter = max(0.0, min(1.0, (elapsed - clip.delay) / 0.32))
        enter = 1.0 - (1.0 - enter) * (1.0 - enter)
    if enter <= 0:
        return
    local = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    local_rect = local.get_rect()
    alpha = int((138 + intensity * 72) * enter)
    panel_color = blend_color((8, 13, 22), clip.accent, 0.12 + intensity * 0.08)
    pygame.draw.rect(local, (*panel_color, alpha), local_rect, border_radius=14)
    pygame.draw.rect(
        local,
        (*blend_color(BORDER, clip.accent, 0.38), min(230, alpha + 28)),
        local_rect,
        width=1,
        border_radius=14,
    )

    phase = elapsed * (2.0 + intensity * 0.8) + clip.phase_offset
    bob = sin(phase) * 4.0 * intensity
    slide = int((1.0 - enter) * 12)
    center_x = 24 + slide
    feet_y = int(local_rect.bottom - 9 + bob * 0.2)
    torso_y = int(feet_y - 20 + bob)
    head_y = int(torso_y - 10)
    accent = clip.accent
    pose = clip.pose_key
    shadow_rect = pygame.Rect(center_x - 13, local_rect.bottom - 11, 28, 5)
    pygame.draw.ellipse(local, (*blend_color(BACKGROUND, accent, 0.18), 130), shadow_rect)
    pygame.draw.circle(local, (*blend_color(TEXT, accent, 0.18), 235), (center_x, head_y), 7)
    pygame.draw.circle(local, (*BACKGROUND, 210), (center_x + 2, head_y - 1), 2)
    body_rect = pygame.Rect(center_x - 7, torso_y - 1, 14, 18)
    pygame.draw.rect(local, (*accent, 220), body_rect, border_radius=6)
    arm_swing = sin(phase + 0.8) * 5 * intensity
    left_arm_end = (int(center_x - 15), int(torso_y + 12 + arm_swing))
    right_arm_end = (int(center_x + 15), int(torso_y + 12 - arm_swing))
    if pose in {"warn", "fire", "win"}:
        left_arm_end = (center_x - 13, int(torso_y - 5))
        right_arm_end = (center_x + 13, int(torso_y - 5))
    elif pose in {"handoff", "deal"}:
        right_arm_end = (center_x + 19, int(torso_y + 4))
    elif pose == "coach":
        right_arm_end = (center_x + 12, int(torso_y - 4))
    elif pose == "build":
        right_arm_end = (center_x + 16, int(torso_y + 14))
    elif pose == "block":
        left_arm_end = (center_x + 10, int(torso_y + 13))
        right_arm_end = (center_x - 10, int(torso_y + 13))
    pygame.draw.line(
        local,
        (*blend_color(TEXT, accent, 0.2), 220),
        (center_x - 7, torso_y + 5),
        left_arm_end,
        2,
    )
    pygame.draw.line(
        local,
        (*blend_color(TEXT, accent, 0.2), 220),
        (center_x + 7, torso_y + 5),
        right_arm_end,
        2,
    )
    if pose == "block":
        pygame.draw.line(
            local,
            (*DANGER, 230),
            (center_x - 9, torso_y + 2),
            (center_x + 9, torso_y + 17),
            2,
        )
        pygame.draw.line(
            local,
            (*DANGER, 230),
            (center_x + 9, torso_y + 2),
            (center_x - 9, torso_y + 17),
            2,
        )
    elif pose == "build":
        pygame.draw.circle(local, (*blend_color(WARN, accent, 0.18), 220), right_arm_end, 3)
    elif pose == "deal":
        pygame.draw.circle(local, (*WARN, 220), right_arm_end, 3)
    leg_swing = sin(phase + 1.7) * 4 * intensity
    pygame.draw.line(
        local,
        (*blend_color(TEXT, accent, 0.22), 220),
        (center_x - 4, torso_y + 16),
        (int(center_x - 9 - leg_swing), feet_y),
        2,
    )
    pygame.draw.line(
        local,
        (*blend_color(TEXT, accent, 0.22), 220),
        (center_x + 4, torso_y + 16),
        (int(center_x + 9 + leg_swing), feet_y),
        2,
    )

    badge_radius = 8
    badge_center = (local_rect.right - 14, 14)
    badge_color = (
        DANGER if clip.state in {"alert", "risk"} else GOOD if clip.state == "success" else accent
    )
    pygame.draw.circle(local, (*badge_color, 225), badge_center, badge_radius)
    badge = fonts.small.render(_actor_state_badge(clip.state), True, BACKGROUND)
    local.blit(
        badge,
        (
            badge_center[0] - badge.get_width() // 2,
            badge_center[1] - badge.get_height() // 2,
        ),
    )

    pose_color = _actor_pose_color(pose, accent)
    pose_center = (38, max(15, local_rect.bottom - 13))
    pose_rect = pygame.Rect(pose_center[0] - 6, pose_center[1] - 6, 12, 12)
    pygame.draw.rect(
        local, (*blend_color(BACKGROUND, pose_color, 0.18), 235), pose_rect, border_radius=4
    )
    pygame.draw.rect(local, (*pose_color, 235), pose_rect, width=1, border_radius=4)
    pose_badge = fonts.small.render(_actor_pose_badge(pose), True, pose_color)
    local.blit(
        pose_badge,
        (
            pose_center[0] - pose_badge.get_width() // 2,
            pose_center[1] - pose_badge.get_height() // 2,
        ),
    )

    text_left = 48
    draw_text_line(
        local,
        fonts.small,
        _short_actor_text(clip.label, 18),
        TEXT,
        pygame.Rect(text_left, 8, local_rect.width - text_left - 12, 18),
        valign="top",
    )
    caption_rect = pygame.Rect(text_left, 27, local_rect.width - text_left - 12, 18)
    draw_text_line(
        local,
        fonts.small,
        _fit_actor_caption(fonts.small, clip, caption_rect.width),
        blend_color(MUTED, accent, 0.45),
        caption_rect,
        valign="top",
    )
    surface.blit(local, rect.topleft)


class BaseScene:
    """Shared save, exit, and scene-switch mechanics."""

    def __init__(
        self,
        *,
        pygame,
        fonts: FontPack,
        state: GameState,
        rng: RandomSource,
        slot_name: str,
        save_callback: Callable[[GameState, RandomSource, str], None],
        dirty: bool = False,
        motion_mode: MotionMode | str = MotionMode.FULL,
        entry_transition: str = "boot_run",
        preferences: FrontendPreferences | None = None,
        preference_callback: Callable[[FrontendPreferences], FontPack] | None = None,
        preference_provider: Callable[[], FrontendPreferences] | None = None,
    ) -> None:
        self.pygame = pygame
        self.fonts = fonts
        self.state = state
        self.rng = rng
        self.slot_name = slot_name
        self._save_callback = save_callback
        self._dirty = dirty
        self.preferences = preferences or FrontendPreferences.from_values(
            motion_mode=motion_mode,
        )
        self.motion_mode = normalize_motion_mode(self.preferences.motion_mode)
        self._preference_callback = preference_callback
        self._preference_provider = preference_provider
        self._preference_status = "Changes are stored locally for future 2D sessions."
        self.should_exit = False
        self.exit_reason = "quit"
        self._next_scene: BaseScene | None = None
        self._scene_transition_key = entry_transition
        self._scene_transition_elapsed = 0.0
        self._scene_transition_duration = self._entry_transition_duration(entry_transition)
        self._actor_sprite_bounds: list[ActorSpriteBounds] = []
        self._layout_separation_guards: list[tuple[str, object, object]] = []

    def _current_frontend_preferences(self) -> FrontendPreferences:
        if self._preference_provider is not None:
            return self._preference_provider()
        return self.preferences

    def _apply_frontend_preferences(self, preferences: FrontendPreferences) -> bool:
        """Apply one settings change live and persist it through the app bridge."""

        try:
            fonts = (
                self._preference_callback(preferences)
                if self._preference_callback is not None
                else None
            )
        except PersistenceError as error:
            self._preference_status = f"Could not save settings: {error}"
            return False

        if fonts is not None:
            self.fonts = fonts
        self.preferences = preferences
        self.motion_mode = preferences.motion_mode
        motion_pulses = getattr(self, "_motion_pulses", None)
        if motion_pulses is not None:
            motion_pulses.configure_intensity_scale(
                self.motion_mode.pulse_scale,
                clear=self.motion_mode is MotionMode.OFF,
            )
        if self.motion_mode is MotionMode.OFF:
            self._scene_transition_duration = 0.0
            self._scene_transition_elapsed = 0.0
        self._preference_status = "Saved locally and applied to every 2D scene."
        return True

    def _cycle_frontend_preference(self, field: str) -> bool:
        return self._apply_frontend_preferences(self._current_frontend_preferences().cycle(field))

    def _reset_frontend_preferences(self) -> bool:
        return self._apply_frontend_preferences(FrontendPreferences())

    def _synchronize_frontend_preferences(self) -> None:
        current = self._current_frontend_preferences()
        if current != self.preferences:
            self._apply_frontend_preferences(current)

    def _draw_frontend_settings_panel(
        self,
        surface,
        rect,
        *,
        target_prefix: str,
        back_kind: str,
        back_payload: str = "",
        panel_title: str = "Settings",
    ) -> None:
        """Draw the shared responsive display and motion controls."""

        pygame = self.pygame
        preferences = self._current_frontend_preferences()
        inner = draw_panel(
            surface,
            pygame,
            rect,
            title=panel_title,
            accent=SELECTION,
        )
        draw_text_line(
            surface,
            self.fonts.heading,
            "Display & Decisions",
            TEXT,
            pygame.Rect(inner.left, inner.top - 28, inner.width, 24),
            valign="top",
        )
        draw_text_line(
            surface,
            self.fonts.small,
            self._preference_status,
            MUTED,
            pygame.Rect(inner.left, inner.top, inner.width, 20),
            valign="top",
        )
        controls = (
            (
                f"1 Text: {preferences.ui_scale.value.title()}",
                "Cycle compact, standard, and large type.",
                f"{target_prefix}_cycle",
                "ui_scale",
                INFO,
            ),
            (
                f"2 Contrast: {preferences.contrast_mode.value.title()}",
                "Switch between standard and high contrast.",
                f"{target_prefix}_cycle",
                "contrast_mode",
                WARN,
            ),
            (
                f"3 Motion: {preferences.motion_mode.value.title()}",
                "Choose full, reduced, or motion off.",
                f"{target_prefix}_cycle",
                "motion_mode",
                GOOD,
            ),
            (
                f"4 Loadout: {preferences.action_loadout.value.title()}",
                "Prioritize contextual, product, growth, or resilience actions.",
                f"{target_prefix}_cycle",
                "action_loadout",
                SELECTION,
            ),
            (
                "R / 8 Reset",
                "Restore standard display, motion, and contextual actions.",
                f"{target_prefix}_reset",
                "",
                DANGER,
            ),
            (
                "B / 9 Back",
                "Return without losing the applied settings.",
                back_kind,
                back_payload,
                BORDER,
            ),
        )
        gap = 10
        columns = 3 if inner.height < 190 and inner.width >= 700 else 2 if inner.width >= 560 else 1
        rows = (len(controls) + columns - 1) // columns
        button_top = inner.top + 38
        available_height = max(40, inner.bottom - button_top)
        button_height = max(
            40,
            min(56, int((available_height - gap * max(0, rows - 1)) / rows)),
        )
        button_width = int((inner.width - gap * max(0, columns - 1)) / columns)
        for index, (title, detail, kind, payload, accent) in enumerate(controls):
            row = index // columns
            col = index % columns
            left = inner.left + col * (button_width + gap)
            if index == len(controls) - 1 and len(controls) % columns:
                left = inner.centerx - button_width // 2
            button_rect = pygame.Rect(
                left,
                button_top + row * (button_height + gap),
                button_width,
                button_height,
            )
            draw_button(
                surface,
                pygame,
                rect=button_rect,
                title=title,
                detail=detail,
                accent=accent,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
            )
            self._click_targets.append(ClickTarget(kind, payload, button_rect))

    @property
    def scene_transition_key(self) -> str:
        """Return the active entry-transition identifier."""

        return self._scene_transition_key

    def scene_transition_progress(self) -> float:
        """Return normalized transition progress from 0.0 to 1.0."""

        if self._scene_transition_duration <= 0:
            return 1.0
        return min(1.0, self._scene_transition_elapsed / self._scene_transition_duration)

    def scene_transition_active(self) -> bool:
        """Return whether the scene entry transition is still visible."""

        return self._scene_transition_duration > 0 and self.scene_transition_progress() < 1.0

    def maybe_save_on_exit(self) -> bool:
        """Persist the run if the scene dirtied the state."""

        if not self._dirty:
            return False
        self._persist_current_run()
        return True

    def pop_next_scene(self) -> BaseScene | None:
        """Return the queued scene transition, if any."""

        next_scene = self._next_scene
        self._next_scene = None
        return next_scene

    def _persist_current_run(self) -> None:
        self._save_callback(self.state, self.rng, self.slot_name)
        self._dirty = False

    def _entry_transition_duration(self, entry_transition: str) -> float:
        if not entry_transition or self.motion_mode is MotionMode.OFF:
            return 0.0
        return 0.26 if self.motion_mode is MotionMode.REDUCED else 0.42

    def _transition_intensity(self) -> float:
        if self.motion_mode is MotionMode.OFF:
            return 0.0
        return 0.45 if self.motion_mode is MotionMode.REDUCED else 1.0

    def _update_scene_transition(self, dt: float) -> None:
        if self._scene_transition_duration <= 0:
            return
        self._scene_transition_elapsed = min(
            self._scene_transition_duration,
            self._scene_transition_elapsed + max(0.0, dt),
        )

    def _reset_actor_sprite_bounds(self) -> None:
        self._actor_sprite_bounds = []

    def _reset_layout_separation_guards(self) -> None:
        self._layout_separation_guards = []

    def _record_layout_separation(self, key: str, first_rect, second_rect) -> None:
        self._layout_separation_guards.append(
            (key, self.pygame.Rect(first_rect), self.pygame.Rect(second_rect))
        )

    def layout_safety_violations(self) -> tuple[str, ...]:
        """Return named content regions that overlap in the most recent frame."""

        return tuple(
            f"{key}:overlap"
            for key, first_rect, second_rect in self._layout_separation_guards
            if first_rect.colliderect(second_rect)
        )

    def _record_actor_sprite_bounds(self, clip: ActorSpriteClip, rect) -> None:
        self._actor_sprite_bounds.append(
            ActorSpriteBounds(
                key=clip.key,
                lane=clip.lane,
                left=int(rect.left),
                top=int(rect.top),
                width=int(rect.width),
                height=int(rect.height),
            )
        )

    def actor_sprite_bounds(self) -> tuple[ActorSpriteBounds, ...]:
        """Return actor sprite footprints from the most recent draw pass."""

        return tuple(self._actor_sprite_bounds)

    def actor_readability_clear(self) -> bool:
        """Return whether actor sprites avoid viewport and click-target collisions."""

        return bool(self._actor_sprite_bounds) and not self.actor_readability_violations()

    def actor_readability_violations(self) -> tuple[str, ...]:
        surface = self.pygame.display.get_surface()
        if surface is None:
            return ()
        width, height = surface.get_size()
        violations: list[str] = []
        for bounds in self._actor_sprite_bounds:
            if (
                bounds.left < 0
                or bounds.top < 0
                or bounds.left + bounds.width > width
                or bounds.top + bounds.height > height
            ):
                violations.append(f"{bounds.key}:viewport")
            actor_rect = self.pygame.Rect(bounds.left, bounds.top, bounds.width, bounds.height)
            for target in getattr(self, "_click_targets", ()):
                if actor_rect.colliderect(target.rect):
                    violations.append(f"{bounds.key}:{target.kind}")
        return tuple(violations)

    def _draw_nav_rail(self, surface, items: tuple[tuple[str, str, str, str, object], ...]) -> None:
        """Draw persistent top-left navigation pills and register click targets."""

        if not items:
            return
        pygame = self.pygame
        left = 24
        top = 12
        gap = 8
        height = 34
        for title, detail, kind, payload, accent in items:
            width = min(190, max(104, self.fonts.small.size(title)[0] + 42))
            rect = pygame.Rect(left, top, width, height)
            draw_button(
                surface,
                pygame,
                rect=rect,
                title=title,
                detail=detail,
                accent=accent,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
            )
            click_targets = getattr(self, "_click_targets", None)
            if click_targets is not None:
                click_targets.append(ClickTarget(kind, payload, rect))
            left += width + gap

    def _hover_target_for_position(self, position: tuple[int, int]) -> ClickTarget | None:
        for target in reversed(getattr(self, "_click_targets", ())):
            if target.rect.collidepoint(position):
                return target
        return None

    def _sync_mouse_cursor(self) -> None:
        pygame_error = getattr(self.pygame, "error", RuntimeError)
        try:
            target = self._hover_target_for_position(self.pygame.mouse.get_pos())
            cursor = (
                self.pygame.SYSTEM_CURSOR_HAND
                if target is not None
                else self.pygame.SYSTEM_CURSOR_ARROW
            )
            self.pygame.mouse.set_cursor(cursor)
        except (AttributeError, pygame_error):
            return

    def _draw_scene_transition_overlay(self, surface) -> None:
        if not self.scene_transition_active():
            return
        pygame = self.pygame
        width, height = surface.get_size()
        progress = self.scene_transition_progress()
        eased = 1.0 - (1.0 - progress) * (1.0 - progress)
        intensity = self._transition_intensity()
        label, accent = _SCENE_TRANSITION_LABELS.get(
            self._scene_transition_key,
            ("Scene Shift", INFO),
        )

        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        fade_alpha = int((1.0 - eased) * 62 * intensity)
        if fade_alpha > 0:
            overlay.fill((3, 6, 12, fade_alpha))

        sweep_width = max(80, int(width * 0.24))
        sweep_x = int(eased * max(1, width - sweep_width))
        sweep_alpha = int(max(0.0, 1.0 - abs(progress - 0.48) * 2.1) * 42 * intensity)
        if sweep_alpha > 0:
            sweep_rect = pygame.Rect(sweep_x, 4, sweep_width, 5)
            pygame.draw.rect(overlay, (*accent, sweep_alpha), sweep_rect)
            edge_rect = pygame.Rect(sweep_rect.right - 18, sweep_rect.top, 18, sweep_rect.height)
            pygame.draw.rect(overlay, (*TEXT, min(120, sweep_alpha + 20)), edge_rect)

        line_gap = 26 if self.motion_mode is MotionMode.FULL else 38
        line_alpha = int((1.0 - progress) * 18 * intensity)
        if line_alpha > 0:
            for y in range(0, height, line_gap):
                pygame.draw.line(overlay, (*accent, line_alpha), (0, y), (width, y), 1)

        surface.blit(overlay, (0, 0))
        badge_rect = self._scene_transition_badge_rect(surface)
        if badge_rect is not None:
            pad = 9
            panel_rect = pygame.Rect(
                badge_rect.left,
                badge_rect.top,
                badge_rect.width,
                badge_rect.height,
            )
            pygame.draw.rect(surface, (8, 13, 22), panel_rect, border_radius=12)
            pygame.draw.rect(surface, accent, panel_rect, width=1, border_radius=12)
            draw_text_line(
                surface,
                self.fonts.small,
                label,
                TEXT,
                pygame.Rect(
                    panel_rect.left + pad, panel_rect.top + 2, panel_rect.width - pad * 2, 20
                ),
            )

    def _scene_transition_badge_rect(self, surface):
        if not self.scene_transition_active():
            return None
        if self.scene_transition_progress() >= 0.62 or self._transition_intensity() <= 0.5:
            return None
        width, _height = surface.get_size()
        label, _accent = _SCENE_TRANSITION_LABELS.get(
            self._scene_transition_key,
            ("Scene Shift", INFO),
        )
        badge_width = min(140, max(80, self.fonts.small.size(label)[0] + 18))
        return self.pygame.Rect(width - badge_width - 28, 28, badge_width, 24)


class TitleScene(BaseScene):
    """Main 2D title and save/load scene."""

    def __init__(
        self,
        *,
        pygame,
        fonts: FontPack,
        state: GameState,
        rng: RandomSource,
        slot_name: str,
        save_callback,
        coordinator: SaveLoadCoordinator,
        initial_mode: str = "menu",
        info_message: str | None = None,
        motion_mode: MotionMode | str = MotionMode.FULL,
        entry_transition: str = "boot_title",
        preferences: FrontendPreferences | None = None,
        preference_callback: Callable[[FrontendPreferences], FontPack] | None = None,
        preference_provider: Callable[[], FrontendPreferences] | None = None,
    ) -> None:
        super().__init__(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=rng,
            slot_name=slot_name,
            save_callback=save_callback,
            dirty=False,
            motion_mode=motion_mode,
            entry_transition=entry_transition,
            preferences=preferences,
            preference_callback=preference_callback,
            preference_provider=preference_provider,
        )
        self.coordinator = coordinator
        self._mode = initial_mode
        self._click_targets: list[ClickTarget] = []
        self._events: list[TimedFrontendEvent] = []
        self._motion_elapsed = 0.0
        self._motion_pulses = PulseBank(
            decay=1.9,
            intensity_scale=self.motion_mode.pulse_scale,
        )
        self._text_input: TextInputModalState | None = None
        self._save_cards: tuple[SaveSlotCardViewModel, ...] = ()
        self._archive_cards: tuple[ArchiveCardViewModel, ...] = ()
        self._save_summaries_by_slot: dict[str, SaveSlotSummary] = {}
        self._archives_by_key: dict[str, RunArchiveSummary] = {}
        self._meta_progression: MetaProgressionSummary = summarize_meta_progression([])
        self._archive_comparison: ArchiveComparisonSummary = build_archive_comparison([])
        self._first_archive_mission: FirstArchiveMission = build_first_archive_mission(state)
        self._selected_slot_name: str | None = None
        self._confirm_delete_slot_name: str | None = None
        self._scenario_choices: tuple[ScenarioChoice, ...] = ()
        self._difficulty_choices: tuple[DifficultyChoice, ...] = list_difficulty_choices()
        self._campaign_start_choices: tuple[CampaignStartChoice, ...] = ()
        self._campaign_goal_choices: tuple[CampaignGoalChoice, ...] = list_campaign_goal_choices()
        self._wizard_state = NewGameWizardState(
            scenario_index=0,
            difficulty_index=0,
            campaign_start_index=0,
            goal_index=0,
            company_name="NEXUS TECH",
            product_name="Nexus One",
            slot_name="active",
        )
        self._refresh_lists()
        self._refresh_wizard_catalog()
        self._trigger_title_motion("header", intensity=0.5)
        self._trigger_mode_motion(initial_mode, intensity=0.72)
        if info_message:
            self.push_event(
                FrontendEvent(
                    title="2D Menu Ready",
                    detail=info_message,
                    severity="info",
                    ttl=5.5,
                )
            )

    def update(self, dt: float) -> None:
        self._motion_elapsed += max(0.0, dt)
        self._update_scene_transition(dt)
        self._motion_pulses.update(dt)
        self._events = [
            TimedFrontendEvent(payload=event.payload, time_left=event.time_left - dt)
            for event in self._events
            if event.time_left - dt > 0
        ]

    def _motion_level(self, *keys: str) -> float:
        if not keys:
            return 0.0
        return max(self._motion_pulses.get(key) for key in keys)

    def _overlay_motion_level(self, overlay_key: str) -> float:
        return self._motion_level(f"title:overlay:{overlay_key}")

    def _overlay_fill(self, overlay_key: str) -> tuple[int, int, int, int]:
        pulse = self._overlay_motion_level(overlay_key)
        alpha = min(224, 180 + int(pulse * 36))
        return (8, 10, 14, alpha)

    def _title_actor_sprite_strength(self) -> float:
        if self.motion_mode is MotionMode.OFF:
            return 0.0
        base = 0.14 if self.motion_mode is MotionMode.REDUCED else 0.32
        scale = 0.58 if self.motion_mode is MotionMode.REDUCED else 1.0
        pulse = self._motion_level(
            "title:header",
            "title:content",
            "title:feed",
            "title:archive:comparison",
            f"title:mode:{self._mode}",
        )
        return min(1.0, (base + pulse * 0.34) * scale)

    def actor_timeline_active(self) -> bool:
        """Return whether title/menu actor timelines should be animated."""

        return self._title_actor_sprite_strength() > 0 and bool(self._title_actor_sprite_clips())

    def sprite_clips_active(self) -> bool:
        """Return whether title/menu shape sprite clips are visible."""

        return self.actor_timeline_active()

    def title_actor_active(self) -> bool:
        """Return whether title/menu-specific actor clips are visible."""

        return self.actor_timeline_active()

    def archive_comparison_active(self) -> bool:
        """Return whether archive/meta comparison motion should be visible."""

        return self.motion_mode is not MotionMode.OFF and self._mode in {"archives", "meta"}

    def _title_actor_sprite_clips(self) -> tuple[ActorSpriteClip, ...]:
        mode_label = {
            "menu": "Menu",
            "meta": "Meta",
            "slots": "Saves",
            "slot_detail": "Slot",
            "wizard": "Wizard",
            "archives": "Archive",
            "settings": "Settings",
        }.get(self._mode, "Archive")
        mode_state = {
            "menu": "handoff",
            "meta": "success",
            "slots": "build",
            "slot_detail": "build",
            "wizard": "success",
            "archives": "handoff",
            "settings": "handoff",
        }.get(self._mode, "handoff")
        archive_state = "success" if self._archive_cards else "idle"
        save_state = "success" if self._save_cards else "build"
        return (
            ActorSpriteClip(
                key="title-founder",
                label="Founder",
                role=mode_label,
                state=mode_state,
                accent=SELECTION,
                lane="start",
                delay=0.0,
                phase_offset=0.3,
            ),
            ActorSpriteClip(
                key="title-save",
                label="Saves",
                role="Slots",
                state=save_state,
                accent=GOOD,
                lane="load",
                delay=0.08,
                phase_offset=1.2,
            ),
            ActorSpriteClip(
                key="title-archive",
                label="Archive",
                role="Meta",
                state=archive_state,
                accent=WARN,
                lane="review",
                delay=0.16,
                phase_offset=2.1,
            ),
            ActorSpriteClip(
                key="title-coach",
                label="Coach",
                role="Guide",
                state="handoff",
                accent=INFO,
                lane="next",
                delay=0.24,
                phase_offset=3.0,
            ),
        )

    def _draw_title_actor_sprite_layer(self, surface, anchor_rect) -> None:
        strength = self._title_actor_sprite_strength()
        if strength <= 0:
            return
        clips = self._title_actor_sprite_clips()
        if not clips:
            return
        pygame = self.pygame
        width, _height = surface.get_size()
        visible_count = 1 if width < 900 else 3
        visible_clips = clips[:visible_count]
        gap = 8
        clip_height = 44
        clip_width = 128 if width >= 1060 else 118
        total_width = clip_width * len(visible_clips) + gap * (len(visible_clips) - 1)
        left = max(anchor_rect.left + 10, anchor_rect.right - total_width - 12)
        top = anchor_rect.bottom - clip_height - 8
        for index, clip in enumerate(visible_clips):
            clip_rect = pygame.Rect(left + index * (clip_width + gap), top, clip_width, clip_height)
            self._record_actor_sprite_bounds(clip, clip_rect)
            _draw_actor_sprite_clip(
                pygame=pygame,
                fonts=self.fonts,
                surface=surface,
                rect=clip_rect,
                clip=clip,
                elapsed=self._motion_elapsed,
                intensity=strength,
            )

    def _trigger_title_motion(self, section_key: str, *, intensity: float = 0.6) -> None:
        self._motion_pulses.trigger(f"title:{section_key}", intensity=intensity, decay=2.1)

    def _trigger_mode_motion(self, mode: str, *, intensity: float = 0.72) -> None:
        self._motion_pulses.trigger(f"title:mode:{mode}", intensity=intensity, decay=2.4)
        self._trigger_title_motion("content", intensity=max(0.44, intensity * 0.7))
        self._trigger_title_motion("footer", intensity=max(0.32, intensity * 0.5))
        if mode in {"archives", "meta"}:
            self._motion_pulses.trigger(
                "title:archive:comparison",
                intensity=max(0.4, intensity * 0.86),
                decay=2.6,
            )
            self._motion_pulses.trigger(
                "title:archive:coverage",
                intensity=max(0.32, intensity * 0.62),
                decay=2.4,
            )

    def _trigger_overlay_motion(self, overlay_key: str, *, intensity: float = 0.76) -> None:
        self._motion_pulses.trigger(
            f"title:overlay:{overlay_key}",
            intensity=intensity,
            decay=2.2,
        )

    def _set_mode(self, mode: str) -> None:
        if mode == self._mode:
            return
        self._mode = mode
        self._trigger_mode_motion(mode)

    def _set_text_input(self, modal: TextInputModalState | None) -> None:
        self._text_input = modal
        if modal is not None:
            self._trigger_overlay_motion("text_input")

    def _set_confirm_delete_slot_name(self, slot_name: str | None) -> None:
        self._confirm_delete_slot_name = slot_name
        if slot_name is not None:
            self._trigger_overlay_motion("delete")

    def handle_event(self, event) -> None:
        if event.type == self.pygame.QUIT:
            self.should_exit = True
            self.exit_reason = "quit"
            return
        if event.type == self.pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_mouse_click(event.pos)
            return
        if event.type != self.pygame.KEYDOWN:
            return
        if self._text_input is not None:
            if event.key == self.pygame.K_ESCAPE:
                self._set_text_input(None)
                return
            self._handle_text_input_key(event)
            return
        if self._confirm_delete_slot_name is not None:
            if event.key == self.pygame.K_ESCAPE:
                self._set_confirm_delete_slot_name(None)
            elif event.key in (self.pygame.K_RETURN, self.pygame.K_KP_ENTER):
                self._delete_selected_slot()
            return
        if event.key == self.pygame.K_ESCAPE:
            if self._mode != "menu":
                self._set_mode("slots" if self._mode == "slot_detail" else "menu")
                return
            self.should_exit = True
            self.exit_reason = "quit"
            return
        if self._mode == "settings":
            if event.key == self.pygame.K_r:
                self._reset_frontend_preferences()
                return
            if event.key == self.pygame.K_b:
                self._set_mode("menu")
                return
        if self._mode == "wizard" and event.key in (
            self.pygame.K_RETURN,
            self.pygame.K_KP_ENTER,
            self.pygame.K_SPACE,
        ):
            self._launch_wizard_run()
            return
        if event.unicode and event.unicode in {"1", "2", "3", "4", "5", "6", "7", "8", "9"}:
            self._handle_digit_shortcut(int(event.unicode))

    def draw(self, surface) -> None:
        pygame = self.pygame
        self._click_targets = []
        self._reset_actor_sprite_bounds()
        self._reset_layout_separation_guards()
        draw_grid(surface, pygame)
        width, height = surface.get_size()
        profile = resolve_layout_profile(width, height)
        nav_visible = self._text_input is None and self._confirm_delete_slot_name is None
        frame = build_frame_layout(
            width,
            height,
            header_height=profile.title_header_height,
            footer_height=profile.title_footer_height,
            nav_visible=nav_visible,
            profile=profile,
        )
        margin = profile.margin
        gap = profile.gap
        header_rect = pygame.Rect(frame.header.as_tuple())
        footer_rect = pygame.Rect(frame.footer.as_tuple())
        content_top = frame.content.top
        content_height = frame.content.height
        if width < 980:
            left_rect = pygame.Rect(margin, content_top, width - margin * 2, content_height)
            right_rect = pygame.Rect(0, 0, 0, 0)
        elif width < 1180:
            left_share = 0.68 if self._mode == "menu" else 0.62 if self._mode == "meta" else 0.6
            left_rect = pygame.Rect(
                margin,
                content_top,
                width - margin * 2,
                int(content_height * left_share),
            )
            right_rect = pygame.Rect(
                margin,
                left_rect.bottom + gap,
                width - margin * 2,
                content_top + content_height - left_rect.bottom - gap,
            )
        else:
            left_width = int((width - margin * 2 - gap) * 0.62)
            right_width = width - margin * 2 - gap - left_width
            left_rect = pygame.Rect(margin, content_top, left_width, content_height)
            right_rect = pygame.Rect(
                left_rect.right + gap,
                content_top,
                right_width,
                content_height,
            )

        self._draw_title_header(surface, header_rect)
        self._draw_title_actor_sprite_layer(surface, header_rect)
        if self._mode == "menu":
            self._draw_title_menu(surface, left_rect)
        elif self._mode == "guide":
            self._draw_quick_start_guide(surface, left_rect)
        elif self._mode == "meta":
            self._draw_meta_board(surface, left_rect)
        elif self._mode == "slots":
            self._draw_save_slot_browser(surface, left_rect)
        elif self._mode == "slot_detail":
            self._draw_slot_detail(surface, left_rect)
        elif self._mode == "wizard":
            self._draw_new_game_wizard(surface, left_rect)
        elif self._mode == "settings":
            self._draw_title_settings(surface, left_rect)
        else:
            self._draw_archive_browser(surface, left_rect)
        if right_rect.width > 0 and right_rect.height > 0:
            self._draw_title_sidebar(surface, right_rect)
        self._draw_title_footer(surface, footer_rect)
        if self._text_input is None and self._confirm_delete_slot_name is None:
            self._draw_nav_rail(
                surface,
                (
                    (
                        "Esc Quit" if self._mode == "menu" else "Back Menu",
                        "Close the shell." if self._mode == "menu" else "Return to title menu.",
                        "menu",
                        "quit" if self._mode == "menu" else "menu",
                        DANGER if self._mode == "menu" else INFO,
                    ),
                ),
            )
        if self._confirm_delete_slot_name is not None:
            self._draw_delete_confirmation_overlay(surface)
        if self._text_input is not None:
            self._draw_text_input_overlay(surface)
        self._sync_mouse_cursor()
        self._draw_scene_transition_overlay(surface)

    def push_event(self, payload: FrontendEvent) -> None:
        self._events.insert(0, TimedFrontendEvent(payload=payload, time_left=payload.ttl))
        self._events = self._events[:5]
        intensity = _MOTION_INTENSITY.get(payload.severity, 0.42)
        self._trigger_title_motion("feed", intensity=max(0.3, intensity * 0.72))
        self._trigger_title_motion("status", intensity=max(0.24, intensity * 0.5))
        self._motion_pulses.trigger(
            f"title:mode:{self._mode}",
            intensity=max(0.22, intensity * 0.4),
            decay=2.0,
        )

    def _refresh_lists(self) -> None:
        try:
            save_summaries = self.coordinator.list_save_slots()
            archive_summaries = self.coordinator.list_run_archives()
        except PersistenceError as error:
            save_summaries = []
            archive_summaries = []
            self.push_event(
                FrontendEvent(
                    title="Persistence Error",
                    detail=str(error),
                    severity="warning",
                    ttl=6.0,
                )
            )
        self._save_cards = build_save_slot_card_view_models(save_summaries)
        self._archive_cards = build_archive_card_view_models(archive_summaries)
        self._save_summaries_by_slot = {summary.slot_name: summary for summary in save_summaries}
        self._archives_by_key = {summary.archive_key: summary for summary in archive_summaries}
        self._meta_progression = summarize_meta_progression(archive_summaries)
        self._archive_comparison = build_archive_comparison(archive_summaries)
        self._first_archive_mission = build_first_archive_mission(
            self.state,
            archive_count=len(archive_summaries),
        )
        if self._selected_slot_name not in self._save_summaries_by_slot:
            self._selected_slot_name = None
        if self._wizard_state.slot_name in self._save_summaries_by_slot:
            self._wizard_state.slot_name = self._suggest_new_slot_name()

    def _handle_mouse_click(self, position: tuple[int, int]) -> None:
        for target in reversed(self._click_targets):
            if target.rect.collidepoint(position):
                self._dispatch_click_target(target)
                return

    def _dispatch_click_target(self, target: ClickTarget) -> None:
        if target.kind == "menu":
            self._handle_menu_action(target.payload)
            return
        if target.kind == "title_settings_cycle":
            self._cycle_frontend_preference(target.payload)
            return
        if target.kind == "title_settings_reset":
            self._reset_frontend_preferences()
            return
        if target.kind == "slot":
            self._open_slot_detail(target.payload)
            return
        if target.kind == "archive":
            self._open_archive_review(target.payload)
            return
        if target.kind == "slot_action":
            self._handle_slot_action(target.payload)
            return
        if target.kind == "wizard_cycle":
            self._cycle_wizard_field(target.payload)
            return
        if target.kind == "wizard_text":
            self._open_wizard_text_modal(target.payload)
            return
        if target.kind == "wizard_launch":
            self._launch_wizard_run()
            return
        if target.kind == "wizard_back":
            self._set_mode("menu")
            return
        if target.kind == "confirm_delete":
            self._delete_selected_slot()
            return
        if target.kind == "cancel_delete":
            self._set_confirm_delete_slot_name(None)
            return
        if target.kind == "submit_text":
            self._submit_text_modal()
            return
        if target.kind == "cancel_text":
            self._set_text_input(None)
            return

    def _handle_digit_shortcut(self, digit: int) -> None:
        if self._mode == "menu":
            self._handle_menu_action(
                {
                    1: "continue",
                    2: "new_wizard",
                    3: "guide",
                    4: "load_slots",
                    5: "archives",
                    6: "meta",
                    7: "settings",
                    8: "quit",
                }.get(digit, "")
            )
            return
        if self._mode == "guide":
            guide_actions = {
                1: "continue",
                2: "new_wizard",
                9: "menu",
            }
            action = guide_actions.get(digit)
            if action:
                self._handle_menu_action(action)
            return
        if self._mode == "meta":
            meta_actions = {
                1: "archives",
                2: "load_slots",
                3: "new_wizard",
                9: "menu",
            }
            action = meta_actions.get(digit)
            if action:
                self._handle_menu_action(action)
            return
        if self._mode == "slots":
            if digit == 9:
                self._set_mode("menu")
                return
            index = digit - 1
            if 0 <= index < len(self._save_cards):
                self._open_slot_detail(self._save_cards[index].slot_name)
            return
        if self._mode == "slot_detail":
            slot_actions = {
                1: "load",
                2: "rename",
                3: "duplicate",
                4: "delete",
                9: "back",
            }
            action = slot_actions.get(digit)
            if action is not None:
                self._handle_slot_action(action)
            return
        if self._mode == "archives":
            if digit == 9:
                self._set_mode("menu")
                return
            index = digit - 1
            if 0 <= index < len(self._archive_cards):
                self._open_archive_review(self._archive_cards[index].archive_key)
            return
        if self._mode == "wizard":
            if digit == 8:
                self._set_mode("menu")
            elif digit == 9:
                self._launch_wizard_run()
            return
        if self._mode == "settings":
            field = {
                1: "ui_scale",
                2: "contrast_mode",
                3: "motion_mode",
                4: "action_loadout",
            }.get(digit)
            if field is not None:
                self._cycle_frontend_preference(field)
            elif digit == 8:
                self._reset_frontend_preferences()
            elif digit == 9:
                self._set_mode("menu")

    def _handle_menu_action(self, action: str) -> None:
        if action == "menu":
            self._set_mode("menu")
            return
        if action == "continue":
            self._continue_last_save()
            return
        if action == "load_slots":
            self._set_mode("slots")
            return
        if action == "archives":
            self._set_mode("archives")
            return
        if action == "meta":
            self._set_mode("meta")
            return
        if action == "guide":
            self._set_mode("guide")
            return
        if action == "new_wizard":
            self._set_mode("wizard")
            return
        if action == "settings":
            self._set_mode("settings")
            return
        if action == "quit":
            self.should_exit = True
            self.exit_reason = "quit"

    def _continue_last_save(self) -> None:
        try:
            loaded = self.coordinator.continue_last_game()
        except PersistenceError as error:
            self.push_event(
                FrontendEvent(
                    title="No Continue Slot",
                    detail=str(error),
                    severity="warning",
                    ttl=5.5,
                )
            )
            return
        self._open_loaded_game(loaded.state, loaded.rng, loaded.slot_name)

    def _load_slot(self, slot_name: str) -> None:
        try:
            loaded = self.coordinator.load_game(slot_name)
        except PersistenceError as error:
            self.push_event(
                FrontendEvent(
                    title="Load Failed",
                    detail=str(error),
                    severity="warning",
                    ttl=5.5,
                )
            )
            return
        self._open_loaded_game(loaded.state, loaded.rng, loaded.slot_name)

    def _open_loaded_game(self, state: GameState, rng: RandomSource, slot_name: str) -> None:
        self._next_scene = RunScene(
            pygame=self.pygame,
            fonts=self.fonts,
            state=state,
            rng=rng,
            slot_name=slot_name,
            save_callback=self._save_callback,
            motion_mode=self.motion_mode,
            preferences=self._current_frontend_preferences(),
            preference_callback=self._preference_callback,
            preference_provider=self._preference_provider,
            entry_transition="title_to_run",
            return_scene_factory=lambda: self._spawn_scene(
                "menu",
                entry_transition="run_to_title",
            ),
        )

    def _open_archive_review(self, archive_key: str) -> None:
        summary = self._archives_by_key.get(archive_key)
        if summary is None:
            return
        self._next_scene = ReviewScene(
            pygame=self.pygame,
            fonts=self.fonts,
            state=self.state,
            rng=self.rng,
            slot_name=self.slot_name,
            save_callback=self._save_callback,
            view_model=build_archive_review_view_model(summary),
            accent=INFO,
            primary_title="Back to Archives",
            primary_detail="Return to the archive browser.",
            return_scene_factory=lambda: self._spawn_scene("archives"),
            allow_save=False,
            dirty=False,
            motion_mode=self.motion_mode,
            preferences=self._current_frontend_preferences(),
            preference_callback=self._preference_callback,
            preference_provider=self._preference_provider,
            entry_transition="title_to_review",
        )

    def _open_slot_detail(self, slot_name: str) -> None:
        if slot_name not in self._save_summaries_by_slot:
            return
        self._selected_slot_name = slot_name
        self._set_mode("slot_detail")

    def _spawn_scene(self, mode: str, *, entry_transition: str = "review_to_title") -> "TitleScene":
        self._synchronize_frontend_preferences()
        return TitleScene(
            pygame=self.pygame,
            fonts=self.fonts,
            state=self.state,
            rng=self.rng,
            slot_name=self.slot_name,
            save_callback=self._save_callback,
            coordinator=self.coordinator,
            initial_mode=mode,
            motion_mode=self.motion_mode,
            preferences=self._current_frontend_preferences(),
            preference_callback=self._preference_callback,
            preference_provider=self._preference_provider,
            entry_transition=entry_transition,
        )

    def _refresh_wizard_catalog(self) -> None:
        previous_scenario = (
            self.selected_scenario_choice.scenario_id if self._scenario_choices else None
        )
        previous_start = (
            self.selected_campaign_start_choice.start_id if self._campaign_start_choices else None
        )
        self._scenario_choices = list_scenario_choices(self.coordinator.db_path)
        self._campaign_start_choices = list_campaign_start_choices(self.coordinator.db_path)
        if not self._scenario_choices or not self._campaign_start_choices:
            return
        self._wizard_state = self._build_wizard_state(
            scenario_id=previous_scenario,
            campaign_start_id=previous_start,
        )

    @property
    def selected_scenario_choice(self) -> ScenarioChoice:
        return self._scenario_choices[self._wizard_state.scenario_index]

    @property
    def selected_difficulty_choice(self) -> DifficultyChoice:
        return self._difficulty_choices[self._wizard_state.difficulty_index]

    @property
    def selected_campaign_start_choice(self) -> CampaignStartChoice:
        return self._campaign_start_choices[self._wizard_state.campaign_start_index]

    @property
    def selected_goal_choice(self) -> CampaignGoalChoice:
        return self._campaign_goal_choices[self._wizard_state.goal_index]

    def _build_wizard_state(
        self,
        *,
        scenario_id: str | None = None,
        campaign_start_id: str | None = None,
    ) -> NewGameWizardState:
        scenario_index = self._find_choice_index(
            [entry.scenario_id for entry in self._scenario_choices],
            scenario_id,
        )
        scenario_choice = self._scenario_choices[scenario_index]
        difficulty_index = self._find_choice_index(
            [entry.mode.value for entry in self._difficulty_choices],
            scenario_choice.default_difficulty.value,
        )
        goal_index = self._find_choice_index(
            [entry.goal_id.value for entry in self._campaign_goal_choices],
            scenario_choice.default_goal_id.value,
        )
        campaign_start_index = self._find_choice_index(
            [entry.start_id for entry in self._campaign_start_choices],
            campaign_start_id or "standard",
        )
        return NewGameWizardState(
            scenario_index=scenario_index,
            difficulty_index=difficulty_index,
            campaign_start_index=campaign_start_index,
            goal_index=goal_index,
            company_name="NEXUS TECH",
            product_name="Nexus One",
            slot_name=self._suggest_new_slot_name(),
        )

    def _find_choice_index(self, values: list[str], wanted: str | None) -> int:
        if wanted is not None and wanted in values:
            return values.index(wanted)
        return 0

    def _suggest_new_slot_name(self) -> str:
        existing = set(self._save_summaries_by_slot)
        if "active" not in existing:
            return "active"
        counter = 1
        while f"run-{counter}" in existing:
            counter += 1
        return f"run-{counter}"

    def _handle_slot_action(self, action: str) -> None:
        if action == "back":
            self._set_mode("slots")
            return
        slot_name = self._selected_slot_name
        if slot_name is None:
            return
        if action == "load":
            self._load_slot(slot_name)
            return
        if action == "rename":
            self._set_text_input(
                TextInputModalState(
                    title="Rename Save Slot",
                    description=f"Enter the new name for `{slot_name}`.",
                    severity="warning",
                    submit_title="Enter Rename",
                    submit_detail="Rename the selected save slot.",
                    text=slot_name,
                    placeholder="Save slot name",
                    on_submit=self._rename_selected_slot,
                )
            )
            return
        if action == "duplicate":
            self._set_text_input(
                TextInputModalState(
                    title="Duplicate Save Slot",
                    description=f"Enter the name for the duplicate of `{slot_name}`.",
                    severity="info",
                    submit_title="Enter Duplicate",
                    submit_detail="Create another save slot with the same run.",
                    text=f"{slot_name}-copy",
                    placeholder="Save slot name",
                    on_submit=self._duplicate_selected_slot,
                )
            )
            return
        if action == "delete":
            self._set_confirm_delete_slot_name(slot_name)

    def _rename_selected_slot(self, new_name: str) -> None:
        slot_name = self._selected_slot_name
        target_name = new_name.strip()
        if slot_name is None or not target_name:
            self.push_event(
                FrontendEvent(
                    title="Rename Rejected",
                    detail="Save slot names must not be empty.",
                    severity="warning",
                    ttl=5.0,
                )
            )
            return
        try:
            self.coordinator.rename_save(slot_name, target_name)
        except PersistenceError as error:
            self.push_event(
                FrontendEvent(
                    title="Rename Failed",
                    detail=str(error),
                    severity="warning",
                    ttl=5.5,
                )
            )
            return
        self._selected_slot_name = target_name
        self._refresh_lists()
        self.push_event(
            FrontendEvent(
                title="Save Slot Renamed",
                detail=f"`{slot_name}` is now `{target_name}`.",
                severity="success",
                ttl=5.0,
            )
        )

    def _duplicate_selected_slot(self, new_name: str) -> None:
        slot_name = self._selected_slot_name
        target_name = new_name.strip()
        if slot_name is None or not target_name:
            self.push_event(
                FrontendEvent(
                    title="Duplicate Rejected",
                    detail="Duplicate slot names must not be empty.",
                    severity="warning",
                    ttl=5.0,
                )
            )
            return
        if target_name in self._save_summaries_by_slot:
            self.push_event(
                FrontendEvent(
                    title="Duplicate Rejected",
                    detail=f"Save slot `{target_name}` already exists.",
                    severity="warning",
                    ttl=5.0,
                )
            )
            return
        try:
            loaded = self.coordinator.load_game(slot_name)
            self.coordinator.save_game(target_name, loaded.state, loaded.rng)
        except PersistenceError as error:
            self.push_event(
                FrontendEvent(
                    title="Duplicate Failed",
                    detail=str(error),
                    severity="warning",
                    ttl=5.5,
                )
            )
            return
        self._selected_slot_name = target_name
        self._refresh_lists()
        self.push_event(
            FrontendEvent(
                title="Save Slot Duplicated",
                detail=f"Created `{target_name}` from `{slot_name}`.",
                severity="success",
                ttl=5.0,
            )
        )

    def _delete_selected_slot(self) -> None:
        slot_name = self._confirm_delete_slot_name
        self._set_confirm_delete_slot_name(None)
        if slot_name is None:
            return
        try:
            self.coordinator.delete_save(slot_name)
        except PersistenceError as error:
            self.push_event(
                FrontendEvent(
                    title="Delete Failed",
                    detail=str(error),
                    severity="warning",
                    ttl=5.5,
                )
            )
            return
        self._selected_slot_name = None
        self._set_mode("slots")
        self._refresh_lists()
        self.push_event(
            FrontendEvent(
                title="Save Slot Deleted",
                detail=f"Removed `{slot_name}` from local saves.",
                severity="success",
                ttl=5.0,
            )
        )

    def _cycle_wizard_field(self, field: str) -> None:
        if field == "scenario":
            self._wizard_state.scenario_index = (self._wizard_state.scenario_index + 1) % len(
                self._scenario_choices
            )
            scenario_choice = self.selected_scenario_choice
            self._wizard_state.difficulty_index = self._find_choice_index(
                [entry.mode.value for entry in self._difficulty_choices],
                scenario_choice.default_difficulty.value,
            )
            self._wizard_state.goal_index = self._find_choice_index(
                [entry.goal_id.value for entry in self._campaign_goal_choices],
                scenario_choice.default_goal_id.value,
            )
            return
        if field == "difficulty":
            self._wizard_state.difficulty_index = (self._wizard_state.difficulty_index + 1) % len(
                self._difficulty_choices
            )
            return
        if field == "campaign_start":
            self._wizard_state.campaign_start_index = (
                self._wizard_state.campaign_start_index + 1
            ) % len(self._campaign_start_choices)
            return
        if field == "goal":
            self._wizard_state.goal_index = (self._wizard_state.goal_index + 1) % len(
                self._campaign_goal_choices
            )

    def _open_wizard_text_modal(self, field: str) -> None:
        field_map = {
            "company": (
                "Company Name",
                "Set the company name for the next run.",
                self._wizard_state.company_name,
                "Company name",
                self._set_wizard_company_name,
            ),
            "product": (
                "Product Name",
                "Set the first product name for the next run.",
                self._wizard_state.product_name,
                "Product name",
                self._set_wizard_product_name,
            ),
            "slot": (
                "Save Slot",
                "Choose the save slot name for this run.",
                self._wizard_state.slot_name,
                "Save slot name",
                self._set_wizard_slot_name,
            ),
            "seed": (
                "Seed",
                "Optional deterministic RNG seed. Leave blank for a fresh random run.",
                self._wizard_state.seed_text,
                "Seed",
                self._set_wizard_seed,
            ),
        }
        entry = field_map.get(field)
        if entry is None:
            return
        title, description, text, placeholder, callback = entry
        self._set_text_input(
            TextInputModalState(
                title=title,
                description=description,
                severity="info",
                submit_title="Enter Apply",
                submit_detail="Apply this value to the new-run wizard.",
                text=text,
                placeholder=placeholder,
                on_submit=callback,
            )
        )

    def _set_wizard_company_name(self, value: str) -> None:
        self._wizard_state.company_name = value.strip() or "NEXUS TECH"

    def _set_wizard_product_name(self, value: str) -> None:
        self._wizard_state.product_name = value.strip() or "Nexus One"

    def _set_wizard_slot_name(self, value: str) -> None:
        self._wizard_state.slot_name = value.strip() or self._suggest_new_slot_name()

    def _set_wizard_seed(self, value: str) -> None:
        self._wizard_state.seed_text = value.strip()

    def _launch_wizard_run(self) -> None:
        scenario = self.selected_scenario_choice
        campaign_start = self.selected_campaign_start_choice
        if scenario.locked:
            self.push_event(
                FrontendEvent(
                    title="Scenario Locked",
                    detail=scenario.lock_reason,
                    severity="warning",
                    ttl=5.5,
                )
            )
            return
        if campaign_start.locked:
            self.push_event(
                FrontendEvent(
                    title="Campaign Start Locked",
                    detail=campaign_start.lock_reason,
                    severity="warning",
                    ttl=5.5,
                )
            )
            return
        slot_name = self._wizard_state.slot_name.strip()
        if not slot_name:
            self.push_event(
                FrontendEvent(
                    title="Save Slot Needed",
                    detail="Choose a non-empty save slot name before launching the run.",
                    severity="warning",
                    ttl=5.0,
                )
            )
            return
        if slot_name in self._save_summaries_by_slot:
            self.push_event(
                FrontendEvent(
                    title="Save Slot In Use",
                    detail=(
                        f"Save slot `{slot_name}` already exists. Rename, delete, or choose "
                        "another slot before launching."
                    ),
                    severity="warning",
                    ttl=6.0,
                )
            )
            return
        seed_text = self._wizard_state.seed_text.strip()
        if seed_text and not seed_text.lstrip("-").isdigit():
            self.push_event(
                FrontendEvent(
                    title="Invalid Seed",
                    detail="Seed must be blank or a whole number.",
                    severity="warning",
                    ttl=5.0,
                )
            )
            return
        seed = int(seed_text) if seed_text else None
        state = create_new_game(
            self._wizard_state.company_name.strip() or None,
            self._wizard_state.product_name.strip() or None,
            scenario_id=scenario.scenario_id,
            difficulty_mode=self.selected_difficulty_choice.mode,
            campaign_goal_id=self.selected_goal_choice.goal_id,
            campaign_start_id=campaign_start.start_id,
        )
        self._open_loaded_game(state, RandomSource(seed=seed), slot_name)

    def _handle_text_input_key(self, event) -> None:
        modal = self._text_input
        if modal is None:
            return
        if event.key in (self.pygame.K_RETURN, self.pygame.K_KP_ENTER):
            self._submit_text_modal()
            return
        if event.key == self.pygame.K_BACKSPACE:
            modal.text = modal.text[:-1]
            return
        if event.key == self.pygame.K_TAB:
            return
        if event.unicode and event.unicode.isprintable() and len(modal.text) < 48:
            modal.text += event.unicode

    def _submit_text_modal(self) -> None:
        modal = self._text_input
        if modal is None:
            return
        self._set_text_input(None)
        modal.on_submit(modal.text.strip())

    def _draw_title_header(self, surface, rect) -> None:
        pygame = self.pygame
        width, _height = surface.get_size()
        header_motion = self._motion_level("title:header", f"title:mode:{self._mode}")
        inner = draw_panel(
            surface,
            pygame,
            rect,
            title="Title",
            accent=INFO,
            emphasis=header_motion,
            lift=int(header_motion * 3),
        )
        actor_reserve = 150 if width < 900 and self.motion_mode is not MotionMode.OFF else 0
        copy_width = max(220, inner.width - actor_reserve)
        draw_text_line(
            surface,
            self.fonts.title,
            "NEXUS TECH 2D",
            TEXT,
            pygame.Rect(inner.left, inner.top - 32, copy_width, 30),
            valign="top",
        )
        subtitle = "Build, survive, choose an exit, then archive the run to unlock new routes."
        draw_wrapped_text(
            surface,
            self.fonts.body,
            subtitle,
            MUTED,
            pygame.Rect(inner.left, inner.top, copy_width, 36),
            line_height=18,
            max_lines=2,
        )
        archive_mission_label = (
            "First archive complete"
            if self._first_archive_mission.complete
            else (
                f"First archive {self._first_archive_mission.step_label}: "
                f"{self._first_archive_mission.current_step.title}"
            )
        )
        draw_text_line(
            surface,
            self.fonts.small,
            (
                f"Saves {len(self._save_cards)} | archives {len(self._archive_cards)} | "
                f"{archive_mission_label}"
            ),
            TEXT,
            pygame.Rect(inner.left, inner.top + 38, copy_width, 18),
            valign="top",
        )

    def _draw_title_menu(self, surface, rect) -> None:
        pygame = self.pygame
        menu_motion = self._motion_level("title:mode:menu", "title:content")
        inner = draw_panel(
            surface,
            pygame,
            rect,
            title="Menu",
            accent=GOOD,
            emphasis=menu_motion,
            lift=int(menu_motion * 3),
        )
        draw_text_line(
            surface,
            self.fonts.heading,
            "Title Menu",
            TEXT,
            pygame.Rect(inner.left, inner.top - 28, inner.width, 24),
            valign="top",
        )
        continue_detail = (
            f"Resume {self._first_archive_mission.current_step.title} "
            f"({self._first_archive_mission.step_label})."
            if self._save_cards
            else "No save yet; start a guided campaign."
        )
        primary_buttons = (
            ("1 Continue Last", continue_detail, "continue", GOOD),
            ("2 New Game", "Start a guided campaign.", "new_wizard", INFO),
        )
        secondary_buttons = (
            ("3 How to Play", "Goal, controls, and first turn.", "guide", GOOD),
            ("4 Manage Saves", "Load, rename, copy, or delete.", "load_slots", INFO),
            ("5 Run Archives", "Completed runs and lessons.", "archives", WARN),
            (
                "6 Progress",
                f"First archive {self._first_archive_mission.progress_label}; routes and rewards.",
                "meta",
                SELECTION,
            ),
            ("7 Settings", "Text, contrast, and motion.", "settings", INFO),
        )
        quit_button = ("8 Quit", "Leave NEXUS TECH.", "quit", DANGER)
        gap = 8 if inner.height < 250 else 10
        primary_height = max(46, min(68, int(inner.height * 0.22)))
        quit_height = max(36, min(44, int(inner.height * 0.14)))
        secondary_columns = 3 if inner.height < 250 and inner.width >= 700 else 2
        secondary_rows = (len(secondary_buttons) + secondary_columns - 1) // secondary_columns
        fixed_gaps = gap * (secondary_rows + 1)
        secondary_area = max(
            secondary_rows * 36,
            inner.height - primary_height - quit_height - fixed_gaps,
        )
        secondary_height = max(
            36,
            min(
                54,
                int((secondary_area - gap * max(0, secondary_rows - 1)) / secondary_rows),
            ),
        )
        column_width = int((inner.width - gap) / 2)

        def draw_menu_button(button, button_rect) -> None:
            title, detail, payload, accent = button
            draw_button(
                surface,
                pygame,
                rect=button_rect,
                title=title,
                detail=detail,
                accent=accent,
                title_font=self.fonts.body,
                detail_font=self.fonts.small,
            )
            self._click_targets.append(ClickTarget("menu", payload, button_rect))

        for index, button in enumerate(primary_buttons):
            draw_menu_button(
                button,
                pygame.Rect(
                    inner.left + index * (column_width + gap),
                    inner.top,
                    column_width,
                    primary_height,
                ),
            )
        secondary_top = inner.top + primary_height + gap
        for index, button in enumerate(secondary_buttons):
            secondary_width = int((inner.width - gap * (secondary_columns - 1)) / secondary_columns)
            column = index % secondary_columns
            row = index // secondary_columns
            left = inner.left + column * (secondary_width + gap)
            if index == len(secondary_buttons) - 1 and len(secondary_buttons) % secondary_columns:
                left = inner.centerx - secondary_width // 2
            draw_menu_button(
                button,
                pygame.Rect(
                    left,
                    secondary_top + row * (secondary_height + gap),
                    secondary_width,
                    secondary_height,
                ),
            )
        quit_width = min(column_width, max(220, int(inner.width * 0.46)))
        draw_menu_button(
            quit_button,
            pygame.Rect(
                inner.centerx - quit_width // 2,
                inner.bottom - quit_height,
                quit_width,
                quit_height,
            ),
        )

    def _draw_title_settings(self, surface, rect) -> None:
        self._draw_frontend_settings_panel(
            surface,
            rect,
            target_prefix="title_settings",
            back_kind="menu",
            back_payload="menu",
        )

    def _draw_meta_board(self, surface, rect) -> None:
        pygame = self.pygame
        compact = self._meta_board_compact_layout(rect)
        meta_motion = self._motion_level(
            "title:mode:meta",
            "title:content",
            "title:archive:comparison",
        )
        inner = draw_panel(
            surface,
            pygame,
            rect,
            title="Meta Board",
            accent=SELECTION,
            emphasis=meta_motion,
            lift=int(meta_motion * 3),
        )
        title_surface = self.fonts.heading.render("Archive / Progression Board", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 24))

        left_width = int(inner.width * 0.56)
        summary_rect = pygame.Rect(inner.left, inner.top, left_width, inner.height - 66)
        action_rect = pygame.Rect(
            summary_rect.right + 20,
            inner.top,
            inner.right - summary_rect.right - 20,
            inner.height - 66,
        )

        summary_lines = self._meta_board_summary_lines(compact)
        top = summary_rect.top
        for line in summary_lines:
            consumed = draw_wrapped_text(
                surface,
                self.fonts.small,
                line,
                MUTED if ":" in line else TEXT,
                pygame.Rect(summary_rect.left, top, summary_rect.width, 34),
                line_height=16,
                max_lines=2,
            )
            top += max(22, consumed)
        if not compact:
            atlas_title = self.fonts.small.render("Route Atlas", True, INFO)
            surface.blit(atlas_title, (summary_rect.left, top + 6))
            top += 28
            for lane in self._meta_progression.route_mastery.lanes:
                route_line = (
                    f"{lane.track_label}: {lane.discovered_routes}/{lane.required_routes} "
                    f"routes | {lane.status}"
                )
                consumed = draw_wrapped_text(
                    surface,
                    self.fonts.small,
                    route_line,
                    TEXT,
                    pygame.Rect(summary_rect.left, top, summary_rect.width, 22),
                    line_height=15,
                    max_lines=1,
                )
                top += max(18, consumed)
        if not compact and self.archive_comparison_active():
            self._draw_archive_comparison_strip(
                surface,
                pygame.Rect(summary_rect.left, inner.bottom - 56, summary_rect.width, 46),
                compact=compact,
            )

        buttons = (
            ("1 Open Archives", "Jump into completed-run reviews.", "archives", WARN),
            ("2 Manage Saves", "Browse current save slots.", "load_slots", GOOD),
            ("3 New Wizard", "Start the next campaign from the 2D wizard.", "new_wizard", INFO),
            ("9 Back", "Return to the title menu.", "menu", BORDER),
        )
        if compact:
            button_gap = 10
            button_width = int((action_rect.width - button_gap) / 2)
            button_height = 46
            for index, (title, detail, payload, accent) in enumerate(buttons):
                row = index // 2
                col = index % 2
                button_rect = pygame.Rect(
                    action_rect.left + col * (button_width + button_gap),
                    action_rect.top + row * (button_height + button_gap),
                    button_width,
                    button_height,
                )
                draw_button(
                    surface,
                    pygame,
                    rect=button_rect,
                    title=title,
                    detail=self._compact_text(detail, 30),
                    accent=accent,
                    title_font=self.fonts.small,
                    detail_font=self.fonts.small,
                )
                self._click_targets.append(ClickTarget("menu", payload, button_rect))
            guide_top = max(top + 8, action_rect.top + button_height * 2 + button_gap + 14)
            guide_height = min(96, max(0, inner.bottom - guide_top))
            if guide_height >= 52:
                self._draw_meta_compact_guides(
                    surface,
                    pygame.Rect(inner.left, guide_top, inner.width, guide_height),
                )
        else:
            top = action_rect.top
            for title, detail, payload, accent in buttons:
                button_rect = pygame.Rect(action_rect.left, top, action_rect.width, 58)
                draw_button(
                    surface,
                    pygame,
                    rect=button_rect,
                    title=title,
                    detail=detail,
                    accent=accent,
                    title_font=self.fonts.small,
                    detail_font=self.fonts.small,
                )
                self._click_targets.append(ClickTarget("menu", payload, button_rect))
                top += 70

    def _draw_meta_compact_guides(self, surface, rect) -> None:
        pygame = self.pygame
        journey_detail = (
            "First archive complete"
            if self._first_archive_mission.complete
            else (
                f"Step {self._first_archive_mission.step_label} "
                f"{self._first_archive_mission.current_step.title}"
            )
        )
        cards = (
            ("Journey", journey_detail, INFO),
            ("Archive", f"{len(self._archive_cards)} runs reviewed", GOOD),
            ("Next", self._compact_text(self._meta_progression.next_reward, 34), WARN),
        )
        gap = 10
        card_width = int((rect.width - gap * (len(cards) - 1)) / len(cards))
        left = rect.left
        for title, detail, accent in cards:
            card_rect = pygame.Rect(left, rect.top, card_width, rect.height)
            pygame.draw.rect(surface, (22, 34, 52), card_rect, border_radius=12)
            pygame.draw.rect(surface, accent, card_rect, width=1, border_radius=12)
            pygame.draw.rect(
                surface,
                accent,
                (card_rect.left + 1, card_rect.top + 1, card_rect.width - 2, 4),
                border_radius=4,
            )
            draw_text_line(
                surface,
                self.fonts.small,
                title,
                TEXT,
                pygame.Rect(card_rect.left + 10, card_rect.top + 10, card_rect.width - 20, 16),
                valign="top",
            )
            draw_wrapped_text(
                surface,
                self.fonts.small,
                detail,
                MUTED,
                pygame.Rect(card_rect.left + 10, card_rect.top + 28, card_rect.width - 20, 36),
                line_height=14,
                max_lines=2,
            )
            left += card_width + gap

    def _draw_quick_start_guide(self, surface, rect) -> None:
        pygame = self.pygame
        guide_motion = self._motion_level("title:mode:guide", "title:content")
        inner = draw_panel(
            surface,
            pygame,
            rect,
            title="Quick Start",
            accent=GOOD,
            emphasis=guide_motion,
            lift=int(guide_motion * 3),
        )
        draw_text_line(
            surface,
            self.fonts.heading,
            "Quick Start Guide",
            TEXT,
            pygame.Rect(inner.left, inner.top - 28, inner.width, 24),
            valign="top",
        )
        cards = (
            (
                "1. Goal",
                (
                    "Build enough durable traction to reach IPO, acquisition, or "
                    "independence before cash, board, or market pressure breaks the company."
                ),
                GOOD,
            ),
            (
                "2. First Turn",
                (
                    "Start in New Game Wizard, open the live run, then use Coach and the "
                    "highlighted panels before spending actions."
                ),
                INFO,
            ),
            (
                "3. Read The HUD",
                (
                    "Watch cash, runway, reputation, board pressure, selected product, "
                    "action points, and the footer hint before ending the turn."
                ),
                WARN,
            ),
            (
                "4. Recovery",
                (
                    "Use P for Pause, Esc for Back, F1 for Help, S to Save, and Space to "
                    "resolve only after warnings are clear."
                ),
                SELECTION,
            ),
        )
        action_height = 46
        gap = 10
        grid_bottom = inner.bottom - action_height - 14
        card_area_height = max(120, grid_bottom - inner.top)
        single_column_height = int((card_area_height - gap * (len(cards) - 1)) / len(cards))
        cols = 1 if inner.width < 620 and single_column_height >= 58 else 2
        rows = max(1, (len(cards) + cols - 1) // cols)
        card_width = int((inner.width - gap * max(0, cols - 1)) / cols)
        card_height = max(58, int((card_area_height - gap * max(0, rows - 1)) / rows))
        card_rects = []
        card_fill = blend_color(PANEL, TEXT, 0.08)
        for index, (title, detail, accent) in enumerate(cards):
            row = index // cols
            col = index % cols
            card_rect = pygame.Rect(
                inner.left + col * (card_width + gap),
                inner.top + row * (card_height + gap),
                card_width,
                card_height,
            )
            card_rects.append(card_rect)
            pygame.draw.rect(surface, card_fill, card_rect, border_radius=14)
            pygame.draw.rect(surface, accent, card_rect, width=1, border_radius=14)
            pygame.draw.rect(
                surface,
                accent,
                (card_rect.left + 1, card_rect.top + 1, card_rect.width - 2, 4),
                border_radius=4,
            )
            draw_text_line(
                surface,
                self.fonts.body if card_height >= 76 else self.fonts.small,
                title,
                TEXT,
                pygame.Rect(card_rect.left + 12, card_rect.top + 10, card_rect.width - 24, 22),
                valign="top",
            )
            draw_wrapped_text(
                surface,
                self.fonts.small,
                detail,
                MUTED,
                pygame.Rect(
                    card_rect.left + 12,
                    card_rect.top + 34,
                    card_rect.width - 24,
                    max(20, card_rect.height - 42),
                ),
                line_height=15,
                max_lines=3 if card_height >= 82 else 2,
            )

        button_width = int((inner.width - gap * 2) / 3)
        buttons = (
            ("2 New Game", "Open wizard.", "new_wizard", INFO),
            ("1 Continue", "Resume newest save.", "continue", GOOD),
            ("9 Back", "Return to menu.", "menu", BORDER),
        )
        left = inner.left
        button_rects = []
        for title, detail, payload, accent in buttons:
            button_rect = pygame.Rect(
                left, inner.bottom - action_height, button_width, action_height
            )
            button_rects.append(button_rect)
            draw_button(
                surface,
                pygame,
                rect=button_rect,
                title=title,
                detail=detail,
                accent=accent,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
            )
            self._click_targets.append(ClickTarget("menu", payload, button_rect))
            left += button_width + gap
        if card_rects and button_rects:
            self._record_layout_separation(
                "quick-start-cards-vs-actions",
                card_rects[0].unionall(card_rects[1:]),
                button_rects[0].unionall(button_rects[1:]),
            )

    def _draw_archive_comparison_strip(self, surface, rect, *, compact: bool) -> None:
        if rect.width < 220 or rect.height < 38:
            return
        pygame = self.pygame
        comparison = self._archive_comparison
        pulse = self._motion_level("title:archive:comparison", "title:archive:coverage")
        strength = 0.28 + pulse * (0.44 if self.motion_mode is MotionMode.REDUCED else 0.72)
        fill = blend_color((12, 18, 30), WARN, min(0.28, 0.08 + pulse * 0.16))
        pygame.draw.rect(surface, fill, rect, border_radius=14)
        pygame.draw.rect(
            surface,
            blend_color(BORDER, WARN, min(0.85, 0.32 + pulse * 0.42)),
            rect,
            width=1,
            border_radius=14,
        )
        self._draw_title_entity_nodes(
            surface,
            pygame.Rect(rect.left + 10, rect.top + 10, 58, rect.height - 20),
            accent=WARN,
            strength=min(1.0, strength),
            count=3,
            offset=float(comparison.compared_runs),
        )
        label = "Archive Signal" if not compact else "Archive"
        detail = (
            f"{comparison.compared_runs} runs | {comparison.dominant_path} | "
            f"{self._compact_text(comparison.next_gap, 28)}"
        )
        draw_text_line(
            surface,
            self.fonts.small,
            label,
            TEXT,
            pygame.Rect(rect.left + 78, rect.top + 7, rect.width - 92, 16),
            valign="top",
        )
        draw_text_line(
            surface,
            self.fonts.small,
            self._compact_text(detail, 56 if not compact else 42),
            MUTED,
            pygame.Rect(rect.left + 78, rect.top + 24, rect.width - 92, 16),
            valign="top",
        )

    def _draw_title_entity_nodes(
        self,
        surface,
        rect,
        *,
        accent: tuple[int, int, int],
        strength: float,
        count: int = 3,
        offset: float = 0.0,
    ) -> None:
        if strength <= 0 or rect.width <= 20 or rect.height <= 10:
            return
        phase = self._motion_elapsed * 1.7 + offset
        for index in range(count):
            ratio = (index + 1) / (count + 1)
            bob = sin(phase + index * 1.8) * 4 * strength
            node_x = rect.left + int(rect.width * ratio)
            node_y = rect.centery + int(bob)
            radius = max(2, int(3 + strength * 3))
            alpha = min(210, int(88 + strength * 110))
            self.pygame.draw.circle(surface, (*accent, alpha), (node_x, node_y), radius)
            self.pygame.draw.circle(
                surface,
                blend_color(accent, TEXT, 0.18),
                (node_x, node_y),
                radius,
                1,
            )

    def _draw_save_slot_browser(self, surface, rect) -> None:
        self._draw_card_browser(
            surface,
            rect,
            title="Save Slot Browser",
            cards=self._save_cards,
            click_kind="slot",
            back_detail="Click one save slot to open load/rename/duplicate/delete actions.",
        )

    def _draw_archive_browser(self, surface, rect) -> None:
        self._draw_card_browser(
            surface,
            rect,
            title="Archive Browser",
            cards=self._archive_cards,
            click_kind="archive",
            back_detail="Press 9 or Esc to return to the title menu.",
        )

    def _draw_card_browser(
        self, surface, rect, *, title: str, cards, click_kind: str, back_detail: str
    ) -> None:
        pygame = self.pygame
        mode_key = "archives" if click_kind == "archive" else "slots"
        browser_motion = self._motion_level(
            f"title:mode:{mode_key}",
            "title:content",
            "title:archive:comparison" if click_kind == "archive" else "title:content",
        )
        inner = draw_panel(
            surface,
            pygame,
            rect,
            title=title,
            accent=SELECTION,
            emphasis=browser_motion,
            lift=int(browser_motion * 3),
        )
        title_surface = self.fonts.heading.render(title, True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 24))
        if click_kind == "archive" and self.archive_comparison_active() and inner.height >= 170:
            self._draw_archive_comparison_strip(
                surface,
                pygame.Rect(inner.left, inner.top, inner.width, 44),
                compact=inner.width < 620,
            )
            inner = pygame.Rect(inner.left, inner.top + 54, inner.width, inner.height - 54)
        if not cards:
            draw_text_line(
                surface,
                self.fonts.body,
                "Nothing is stored here yet.",
                MUTED,
                pygame.Rect(inner.left, inner.top, inner.width, 24),
                valign="top",
            )
            draw_wrapped_text(
                surface,
                self.fonts.small,
                back_detail,
                MUTED,
                pygame.Rect(inner.left, inner.top + 28, inner.width, 42),
                line_height=16,
                max_lines=2,
            )
            return
        top = inner.top
        footer_note_height = 28
        gap = 8
        card_height = 64 if inner.height < 360 else 74
        visible_limit = max(1, int((inner.height - footer_note_height + gap) / (card_height + gap)))
        for index, card in enumerate(cards[: min(8, visible_limit)]):
            card_rect = pygame.Rect(inner.left, top, inner.width, card_height)
            accent = tone_color(card.tone)
            draw_button(
                surface,
                pygame,
                rect=card_rect,
                title=f"{index + 1} {card.headline}",
                detail=card.detail_lines[0],
                accent=accent,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
            )
            if card_height >= 70:
                draw_wrapped_text(
                    surface,
                    self.fonts.small,
                    " | ".join(card.detail_lines[1:]),
                    MUTED,
                    pygame.Rect(card_rect.left + 12, card_rect.top + 34, card_rect.width - 24, 28),
                    line_height=14,
                    max_lines=2,
                )
            payload = card.slot_name if hasattr(card, "slot_name") else card.archive_key
            self._click_targets.append(ClickTarget(click_kind, payload, card_rect))
            top += card_height + gap
        remaining = max(0, len(cards) - min(8, visible_limit))
        note = back_detail if remaining == 0 else f"{back_detail} {remaining} more stored."
        draw_text_line(
            surface,
            self.fonts.small,
            note,
            MUTED,
            pygame.Rect(inner.left, inner.bottom - 20, inner.width, 18),
            valign="top",
        )

    def _draw_slot_detail(self, surface, rect) -> None:
        pygame = self.pygame
        summary = self._save_summaries_by_slot.get(self._selected_slot_name or "")
        detail_motion = self._motion_level("title:mode:slot_detail", "title:content")
        inner = draw_panel(
            surface,
            pygame,
            rect,
            title="Save Slot",
            accent=GOOD,
            emphasis=detail_motion,
            lift=int(detail_motion * 3),
        )
        title_surface = self.fonts.heading.render("Save Slot Actions", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 24))
        if summary is None:
            draw_text_line(
                surface,
                self.fonts.body,
                "Select a save slot first.",
                MUTED,
                pygame.Rect(inner.left, inner.top, inner.width, 24),
                valign="top",
            )
            return
        lines = (
            f"Slot: {summary.slot_name}",
            f"Company: {summary.company_name}",
            f"Scenario: {summary.scenario_title}",
            (
                f"Turn {summary.current_turn} | cash {summary.cash_on_hand} | "
                f"rep {summary.reputation} | team {summary.headcount}"
            ),
            (
                f"Products {summary.active_products} | updated "
                f"{summary.updated_at[:19].replace('T', ' ')}"
            ),
        )
        top = inner.top
        for line in lines:
            consumed = draw_wrapped_text(
                surface,
                self.fonts.small,
                line,
                TEXT if line.startswith("Slot:") else MUTED,
                pygame.Rect(inner.left, top, inner.width, 24),
                line_height=16,
                max_lines=2,
            )
            top += max(22, consumed)
        buttons = (
            ("1 Load Save", "Resume this run in the live 2D dashboard.", "load", INFO),
            ("2 Rename", "Rename the selected save slot.", "rename", WARN),
            ("3 Duplicate", "Clone this run into another slot.", "duplicate", INFO),
            ("4 Delete", "Remove this save slot permanently.", "delete", DANGER),
            ("9 Back", "Return to the save-slot browser.", "back", BORDER),
        )
        top += 10
        available = max(44, inner.bottom - top)
        button_gap = 8
        compact_grid = inner.width >= 640 and available < 320
        cols = 2 if compact_grid else 1
        rows_count = max(1, (len(buttons) + cols - 1) // cols)
        button_height = max(
            40,
            min(54, int((available - button_gap * max(0, rows_count - 1)) / rows_count)),
        )
        button_width = int((inner.width - button_gap * max(0, cols - 1)) / cols)
        for index, (title, detail, payload, accent) in enumerate(buttons):
            row = index // cols
            col = index % cols
            button_rect = pygame.Rect(
                inner.left + col * (button_width + button_gap),
                top + row * (button_height + button_gap),
                button_width,
                button_height,
            )
            draw_button(
                surface,
                pygame,
                rect=button_rect,
                title=title,
                detail=self._compact_text(detail, 38 if compact_grid else 56),
                accent=accent,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
            )
            self._click_targets.append(ClickTarget("slot_action", payload, button_rect))

    def _draw_new_game_wizard(self, surface, rect) -> None:
        pygame = self.pygame
        wizard_motion = self._motion_level("title:mode:wizard", "title:content")
        inner = draw_panel(
            surface,
            pygame,
            rect,
            title="New Game",
            accent=INFO,
            emphasis=wizard_motion,
            lift=int(wizard_motion * 3),
        )
        title_surface = self.fonts.heading.render("New Game Wizard", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 24))
        scenario = self.selected_scenario_choice
        difficulty = self.selected_difficulty_choice
        campaign_start = self.selected_campaign_start_choice
        goal = self.selected_goal_choice
        rows = (
            (
                "Scenario",
                f"[{scenario.track_label}] {scenario.title}",
                f"{scenario.stage_hint} Acts: {scenario.act_preview}",
                "scenario",
                "wizard_cycle",
                DANGER if scenario.locked else INFO,
            ),
            (
                "Difficulty",
                difficulty.title,
                difficulty.summary,
                "difficulty",
                "wizard_cycle",
                WARN,
            ),
            (
                "Campaign Start",
                campaign_start.title,
                campaign_start.description,
                "campaign_start",
                "wizard_cycle",
                DANGER if campaign_start.locked else INFO,
            ),
            (
                "Campaign Goal",
                goal.title,
                goal.description,
                "goal",
                "wizard_cycle",
                GOOD,
            ),
            (
                "Company Name",
                self._wizard_state.company_name,
                "Click to edit the company name.",
                "company",
                "wizard_text",
                INFO,
            ),
            (
                "Product Name",
                self._wizard_state.product_name,
                "Click to edit the first product name.",
                "product",
                "wizard_text",
                INFO,
            ),
            (
                "Save Slot",
                self._wizard_state.slot_name,
                "Choose the save slot for this run.",
                "slot",
                "wizard_text",
                WARN if self._wizard_state.slot_name in self._save_summaries_by_slot else GOOD,
            ),
            (
                "Seed",
                self._wizard_state.seed_text or "random",
                "Optional deterministic seed. Blank means fresh randomness.",
                "seed",
                "wizard_text",
                INFO,
            ),
        )
        launch_height = 44
        launch_gap = 12
        grid_gap = 8
        compact_grid = inner.width >= 700 and inner.height < 540
        cols = 2 if compact_grid else 1
        row_count = max(1, (len(rows) + cols - 1) // cols)
        grid_height = max(44, inner.height - launch_height - launch_gap)
        button_height = max(
            42,
            min(56, int((grid_height - grid_gap * max(0, row_count - 1)) / row_count)),
        )
        button_width = int((inner.width - grid_gap * max(0, cols - 1)) / cols)
        for index, (label, value, detail, payload, kind, accent) in enumerate(rows):
            row = index // cols
            col = index % cols
            button_rect = pygame.Rect(
                inner.left + col * (button_width + grid_gap),
                inner.top + row * (button_height + grid_gap),
                button_width,
                button_height,
            )
            draw_button(
                surface,
                pygame,
                rect=button_rect,
                title=f"{label}: {value}",
                detail=self._compact_text(detail, 40 if compact_grid else 58),
                accent=accent,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
            )
            self._click_targets.append(ClickTarget(kind, payload, button_rect))
        launch_top = inner.bottom - launch_height
        launch_rect = pygame.Rect(inner.left, launch_top, inner.width // 2 - 8, launch_height)
        back_rect = pygame.Rect(
            launch_rect.right + 16,
            launch_top,
            inner.width // 2 - 8,
            launch_height,
        )
        draw_button(
            surface,
            pygame,
            rect=launch_rect,
            title="Enter Launch Run",
            detail="Create and open the selected run.",
            accent=GOOD,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        draw_button(
            surface,
            pygame,
            rect=back_rect,
            title="Esc Back",
            detail="Return to the title menu.",
            accent=BORDER,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        self._click_targets.append(ClickTarget("wizard_launch", "", launch_rect))
        self._click_targets.append(ClickTarget("wizard_back", "", back_rect))

    def _draw_title_sidebar(self, surface, rect) -> None:
        pygame = self.pygame
        summary_share = 0.56 if self._mode == "meta" else 0.36
        summary_rect = pygame.Rect(
            rect.left, rect.top, rect.width, int(rect.height * summary_share)
        )
        events_rect = pygame.Rect(
            rect.left,
            summary_rect.bottom + 12,
            rect.width,
            rect.height - summary_rect.height - 12,
        )
        status_motion = self._motion_level("title:status", f"title:mode:{self._mode}")
        inner = draw_panel(
            surface,
            pygame,
            summary_rect,
            title="Status",
            accent=WARN,
            emphasis=status_motion,
            lift=int(status_motion * 2),
        )
        title_surface = self.fonts.heading.render("2D Frontend Status", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 24))
        lines = self._title_sidebar_lines()
        top = inner.top
        for line in lines:
            consumed = draw_wrapped_text(
                surface,
                self.fonts.small,
                line,
                MUTED,
                pygame.Rect(inner.left, top, inner.width, 36),
                line_height=15,
                max_lines=2,
            )
            top += max(24, consumed)

        feed_motion = self._motion_level("title:feed")
        event_inner = draw_panel(
            surface,
            pygame,
            events_rect,
            title="Feed",
            accent=INFO,
            emphasis=feed_motion,
            lift=int(feed_motion * 2),
        )
        event_title = self.fonts.heading.render("Frontend Feed", True, TEXT)
        surface.blit(event_title, (event_inner.left, event_inner.top - 24))
        if not self._events:
            idle_surface = self.fonts.body.render("No menu events yet.", True, MUTED)
            surface.blit(idle_surface, (event_inner.left, event_inner.top))
            return
        top = event_inner.top
        for timed_event in self._events[: self._title_feed_visible_count(events_rect.height)]:
            card_rect = pygame.Rect(event_inner.left, top, event_inner.width, 70)
            self._draw_event_card(surface, card_rect, timed_event)
            top += 80

    def _draw_title_footer(self, surface, rect) -> None:
        pygame = self.pygame
        footer_motion = self._motion_level("title:footer", f"title:mode:{self._mode}")
        inner = draw_panel(
            surface,
            pygame,
            rect,
            title="Guide",
            accent=INFO,
            emphasis=footer_motion,
            lift=int(footer_motion * 2),
        )
        if self._mode == "menu":
            message = (
                "Menu: 1 continue, 2 new, 3 guide, 4 saves, 5 archives, 6 progress, "
                "7 settings, 8 quit."
            )
        elif self._mode == "guide":
            message = "Quick Start: 2 opens wizard, 1 continues, 9 or Esc returns to menu."
        elif self._mode == "meta":
            message = "Meta board: 1 archives, 2 saves, 3 wizard, 9 back."
        elif self._mode == "slots":
            message = "Saves: click a card to manage it. Press 9 or Esc to return."
        elif self._mode == "slot_detail":
            message = "Slot: 1 load, 2 rename, 3 duplicate, 4 delete, 9 back."
        elif self._mode == "wizard":
            message = "Wizard: click rows to cycle/edit. Enter launches. Esc returns to menu."
        elif self._mode == "settings":
            message = "Settings: 1-4 cycle, 8 resets, 9 or Esc returns. Changes persist locally."
        else:
            message = "Archives: click a card to inspect it. Press 9 or Esc to return."
        draw_text_line(
            surface,
            self.fonts.small,
            message,
            TEXT,
            pygame.Rect(inner.left, inner.top + 8, inner.width, 20),
            valign="top",
        )

    def _title_sidebar_lines(self) -> tuple[str, ...]:
        meta = self._meta_progression
        comparison = self._archive_comparison
        if self._mode == "wizard":
            scenario = self.selected_scenario_choice
            campaign_start = self.selected_campaign_start_choice
            difficulty = self.selected_difficulty_choice
            return (
                f"Scenario: [{scenario.track_label}] {scenario.title}",
                (
                    f"Featured campaign {scenario.featured_rank}/6: {scenario.stage_hint}"
                    if scenario.featured_rank is not None
                    else f"Challenge catalog: {scenario.stage_hint}"
                ),
                f"Arc: {scenario.act_preview}",
                (
                    scenario.lock_reason
                    if scenario.locked
                    else f"Difficulty watch: {difficulty.watch_for}"
                ),
                (
                    campaign_start.lock_reason
                    if campaign_start.locked
                    else (
                        f"Start hint: {campaign_start.turn_hint} / {campaign_start.pressure_hint}"
                    )
                ),
            )
        if self._mode == "guide":
            return (
                "Goal: survive pressure and reach IPO, acquisition, or independence.",
                "First turn: use Coach, inspect panels, then spend action points.",
                "Controls: P pause, Esc back, F1 help, S save, Space end turn.",
                f"Next reward: {meta.next_reward}",
            )
        if self._mode == "settings":
            preferences = self._current_frontend_preferences()
            return (
                f"Text scale: {preferences.ui_scale.value}",
                f"Contrast: {preferences.contrast_mode.value}",
                f"Motion: {preferences.motion_mode.value}",
                f"Action loadout: {preferences.action_loadout.value}",
                "Stored only in the local SQLite profile.",
            )
        if self._mode == "meta":
            return (
                (
                    "First archive: complete"
                    if self._first_archive_mission.complete
                    else (
                        f"First archive: {self._first_archive_mission.step_label} "
                        f"{self._first_archive_mission.current_step.title}"
                    )
                ),
                f"Best: IPO {comparison.best_ipo_label} | M&A {comparison.best_acquisition_label}",
                f"Ind {comparison.best_independence_label} | Focus {comparison.common_next_focus}",
            )
        if self._mode == "archives":
            return (
                (
                    f"Archive runs: {comparison.compared_runs} | dominant path: "
                    f"{comparison.dominant_path}"
                ),
                f"Coverage gap: {comparison.next_gap}",
                comparison.recommendation,
                f"Common next focus: {comparison.common_next_focus}",
            )
        if self._mode == "slot_detail":
            summary = self._save_summaries_by_slot.get(self._selected_slot_name or "")
            if summary is not None:
                return (
                    f"Loaded save slot focus: {summary.company_name}",
                    f"Scenario: {summary.scenario_title}",
                    f"Version {summary.saved_with_version} | schema {summary.schema_version}",
                    f"Archive tier: {meta.campaign_tier} / {meta.campaign_stage}",
                )
        return (
            f"Campaign tier: {meta.campaign_tier} | stage: {meta.campaign_stage}",
            (
                "First archive: complete"
                if self._first_archive_mission.complete
                else (
                    f"First archive: {self._first_archive_mission.step_label} "
                    f"{self._first_archive_mission.current_step.title}"
                )
            ),
            (f"Archive: {meta.achievement_progress} | routes {meta.route_discovery_progress}"),
            f"Next reward: {meta.next_reward}",
        )

    def _title_feed_visible_count(self, event_height: int) -> int:
        if event_height < 170:
            return 2
        if event_height < 260:
            return 3
        return 4

    def _meta_board_compact_layout(self, rect) -> bool:
        return rect.height < 280 or rect.width < 900

    def _meta_board_summary_lines(self, compact: bool) -> tuple[str, ...]:
        meta = self._meta_progression
        comparison = self._archive_comparison
        mission_line = (
            "First archive: complete"
            if self._first_archive_mission.complete
            else (
                f"First archive: Step {self._first_archive_mission.step_label} | "
                f"{self._first_archive_mission.current_step.title}"
            )
        )
        if compact:
            route_rows = tuple(
                "Atlas: "
                + " | ".join(
                    f"{lane.track_label} {lane.discovered_routes}/{lane.required_routes}"
                    for lane in meta.route_mastery.lanes[index : index + 2]
                )
                for index in range(0, len(meta.route_mastery.lanes), 2)
            )
            compact_mission = (
                "first archive complete"
                if self._first_archive_mission.complete
                else f"first archive {self._first_archive_mission.step_label}"
            )
            return (
                (f"Campaign: {meta.campaign_tier} / {meta.campaign_stage} | {compact_mission}"),
                (
                    f"Runs {meta.total_runs} | victories {meta.victories} | "
                    f"best score {meta.best_score}"
                ),
                *route_rows,
            )
        return (
            f"Campaign tier: {meta.campaign_tier} | stage: {meta.campaign_stage}",
            mission_line,
            (
                f"Runs: {meta.total_runs} | victories: {meta.victories} | "
                f"best score: {meta.best_score}"
            ),
            f"Next goal: {meta.next_goal}",
            f"Next reward: {meta.next_reward}",
            f"Route discovery: {meta.route_discovery_progress}",
            f"Next route: {meta.next_route}",
            f"Dominant path: {comparison.dominant_path}",
            f"Coverage gap: {comparison.next_gap}",
        )

    def _compact_text(self, value: str, max_length: int) -> str:
        compact = value.strip().replace("`", "")
        if len(compact) <= max_length:
            return compact
        return f"{compact[: max_length - 3].rstrip()}..."

    def _draw_delete_confirmation_overlay(self, surface) -> None:
        pygame = self.pygame
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay_motion = self._overlay_motion_level("delete")
        overlay.fill(self._overlay_fill("delete"))
        surface.blit(overlay, (0, 0))
        slot_name = self._confirm_delete_slot_name or "selected slot"
        modal_rect = _fit_modal_rect(pygame, surface, width=540, height=200, margin=24)
        inner = draw_panel(
            surface,
            pygame,
            modal_rect,
            title="Delete Save",
            accent=DANGER,
            emphasis=overlay_motion,
            lift=int(overlay_motion * 5),
        )
        title_surface = self.fonts.title.render("Delete Save Slot?", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 28))
        draw_wrapped_text(
            surface,
            self.fonts.body,
            f"This permanently removes `{slot_name}` from local saves.",
            MUTED,
            pygame.Rect(inner.left, inner.top, inner.width, 40),
            line_height=18,
            max_lines=2,
        )
        confirm_rect = pygame.Rect(inner.left, inner.top + 74, 220, 40)
        cancel_rect = pygame.Rect(inner.left + 236, inner.top + 74, 180, 40)
        draw_button(
            surface,
            pygame,
            rect=confirm_rect,
            title="Confirm Delete",
            detail="Remove the save slot now.",
            accent=DANGER,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        draw_button(
            surface,
            pygame,
            rect=cancel_rect,
            title="Esc Cancel",
            detail="Keep the save slot.",
            accent=BORDER,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        self._click_targets.append(ClickTarget("confirm_delete", "", confirm_rect))
        self._click_targets.append(ClickTarget("cancel_delete", "", cancel_rect))

    def _draw_text_input_overlay(self, surface) -> None:
        pygame = self.pygame
        modal = self._text_input
        if modal is None:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay_motion = self._overlay_motion_level("text_input")
        overlay.fill(self._overlay_fill("text_input"))
        surface.blit(overlay, (0, 0))
        modal_rect = _fit_modal_rect(pygame, surface, width=600, height=280, margin=24)
        inner = draw_panel(
            surface,
            pygame,
            modal_rect,
            title="Text Input",
            accent=tone_color(modal.severity),
            emphasis=overlay_motion,
            lift=int(overlay_motion * 5),
        )
        title_surface = self.fonts.title.render(modal.title, True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 28))
        draw_wrapped_text(
            surface,
            self.fonts.body,
            modal.description,
            MUTED,
            pygame.Rect(inner.left, inner.top, inner.width, 40),
            line_height=18,
            max_lines=2,
        )
        input_rect = pygame.Rect(inner.left, inner.top + 60, inner.width, 48)
        pygame.draw.rect(surface, (24, 35, 50), input_rect, border_radius=14)
        pygame.draw.rect(
            surface,
            tone_color(modal.severity),
            input_rect,
            width=1,
            border_radius=14,
        )
        input_text = modal.text or modal.placeholder
        input_color = TEXT if modal.text else MUTED
        input_surface = self.fonts.body.render(input_text, True, input_color)
        surface.blit(input_surface, (input_rect.left + 12, input_rect.top + 14))
        cursor_x = input_rect.left + 12 + input_surface.get_width() + 2
        pygame.draw.line(
            surface,
            tone_color(modal.severity),
            (cursor_x, input_rect.top + 10),
            (cursor_x, input_rect.bottom - 10),
            2,
        )
        submit_rect = pygame.Rect(inner.left, inner.top + 134, 220, 40)
        cancel_rect = pygame.Rect(inner.left + 236, inner.top + 134, 180, 40)
        draw_button(
            surface,
            pygame,
            rect=submit_rect,
            title=modal.submit_title,
            detail=modal.submit_detail,
            accent=tone_color(modal.severity),
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        draw_button(
            surface,
            pygame,
            rect=cancel_rect,
            title="Esc Cancel",
            detail="Close without applying changes.",
            accent=BORDER,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        self._click_targets.append(ClickTarget("submit_text", "", submit_rect))
        self._click_targets.append(ClickTarget("cancel_text", "", cancel_rect))

    def _draw_event_card(self, surface, rect, timed_event: TimedFrontendEvent) -> None:
        pygame = self.pygame
        color = tone_color(timed_event.payload.severity)
        event_motion = self._motion_level("title:feed")
        enter_duration = 0.3 if timed_event.payload.motion == "slide" else 0.2
        enter_ratio = min(1.0, max(0.0, timed_event.time_left / max(0.01, enter_duration)))
        animated_rect = pygame.Rect(
            rect.left,
            rect.top - int((1.0 - enter_ratio) * 5 + event_motion * 2),
            rect.width,
            rect.height,
        )
        fill = blend_color((26, 38, 55), color, min(0.22, event_motion * 0.16))
        border = blend_color(color, TEXT, event_motion * 0.1)
        pygame.draw.rect(surface, fill, animated_rect, border_radius=14)
        pygame.draw.rect(
            surface,
            border,
            animated_rect,
            width=2 if event_motion >= 0.4 else 1,
            border_radius=14,
        )
        draw_text_line(
            surface,
            self.fonts.body,
            timed_event.payload.title,
            TEXT,
            pygame.Rect(
                animated_rect.left + 12, animated_rect.top + 8, animated_rect.width - 24, 22
            ),
            valign="top",
        )
        draw_wrapped_text(
            surface,
            self.fonts.small,
            timed_event.payload.detail,
            MUTED,
            pygame.Rect(
                animated_rect.left + 12,
                animated_rect.top + 30,
                animated_rect.width - 24,
                animated_rect.height - 36,
            ),
            line_height=15,
            max_lines=2,
        )


class ReviewScene(BaseScene):
    """Review scene used for completed runs and archive summaries."""

    def __init__(
        self,
        *,
        pygame,
        fonts: FontPack,
        state: GameState,
        rng: RandomSource,
        slot_name: str,
        save_callback,
        view_model: RunReviewViewModel,
        accent: tuple[int, int, int],
        primary_title: str,
        primary_detail: str,
        return_scene_factory: Callable[[], BaseScene] | None,
        allow_save: bool,
        dirty: bool,
        motion_mode: MotionMode | str = MotionMode.FULL,
        entry_transition: str = "run_to_review",
        preferences: FrontendPreferences | None = None,
        preference_callback: Callable[[FrontendPreferences], FontPack] | None = None,
        preference_provider: Callable[[], FrontendPreferences] | None = None,
    ) -> None:
        super().__init__(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=rng,
            slot_name=slot_name,
            save_callback=save_callback,
            dirty=dirty,
            motion_mode=motion_mode,
            entry_transition=entry_transition,
            preferences=preferences,
            preference_callback=preference_callback,
            preference_provider=preference_provider,
        )
        self._view_model = view_model
        self._accent = accent
        self._primary_title = primary_title
        self._primary_detail = primary_detail
        self._return_scene_factory = return_scene_factory
        self._allow_save = allow_save
        self._click_targets: list[ClickTarget] = []
        self._motion_elapsed = 0.0
        self._motion_pulses = PulseBank(
            decay=1.9,
            intensity_scale=self.motion_mode.pulse_scale,
        )
        self._trigger_review_motion("header", intensity=0.58)
        self._trigger_review_motion("findings", intensity=0.72 if view_model.findings else 0.4)
        self._trigger_review_motion("sidebar", intensity=0.52)
        self._trigger_review_motion("footer", intensity=0.5)

    def update(self, dt: float) -> None:
        self._motion_elapsed += max(0.0, dt)
        self._update_scene_transition(dt)
        self._motion_pulses.update(dt)

    def _trigger_review_motion(self, section_key: str, *, intensity: float = 0.6) -> None:
        self._motion_pulses.trigger(f"review:{section_key}", intensity=intensity, decay=2.2)

    def _motion_level(self, *keys: str) -> float:
        if not keys:
            return 0.0
        return max(self._motion_pulses.get(key) for key in keys)

    def _review_actor_sprite_strength(self) -> float:
        if self.motion_mode is MotionMode.OFF:
            return 0.0
        base = 0.16 if self.motion_mode is MotionMode.REDUCED else 0.34
        scale = 0.58 if self.motion_mode is MotionMode.REDUCED else 1.0
        pulse = self._motion_level(
            "review:header",
            "review:findings",
            "review:sidebar",
            "review:footer",
        )
        return min(1.0, (base + pulse * 0.3) * scale)

    def actor_timeline_active(self) -> bool:
        """Return whether review actor timelines should be animated."""

        return self._review_actor_sprite_strength() > 0 and bool(self._review_actor_sprite_clips())

    def sprite_clips_active(self) -> bool:
        """Return whether review shape sprite clips are visible."""

        return self.actor_timeline_active()

    def review_actor_active(self) -> bool:
        """Return whether review-specific actor clips are visible."""

        return self.actor_timeline_active()

    def _review_actor_sprite_clips(self) -> tuple[ActorSpriteClip, ...]:
        finding_state = "alert" if self._view_model.findings else "success"
        outcome_state = "success" if self.state.victory_achieved else "risk"
        return (
            ActorSpriteClip(
                key="review-founder",
                label="Founder",
                role="Postmortem",
                state=outcome_state,
                accent=self._accent,
                lane="result",
                delay=0.0,
                phase_offset=0.5,
            ),
            ActorSpriteClip(
                key="review-analyst",
                label="Analyst",
                role="Findings",
                state=finding_state,
                accent=WARN if finding_state == "alert" else GOOD,
                lane="learn",
                delay=0.08,
                phase_offset=1.4,
            ),
            ActorSpriteClip(
                key="review-coach",
                label="Coach",
                role="Next Focus",
                state="handoff",
                accent=INFO,
                lane="next",
                delay=0.16,
                phase_offset=2.3,
            ),
        )

    def _draw_review_actor_sprite_layer(self, surface, anchor_rect) -> None:
        strength = self._review_actor_sprite_strength()
        if strength <= 0:
            return
        clips = self._review_actor_sprite_clips()
        if not clips:
            return
        pygame = self.pygame
        width, _height = surface.get_size()
        visible_count = 1 if width < 960 else 3
        visible_clips = clips[:visible_count]
        gap = 8
        clip_height = 44
        clip_width = 128 if width >= 1080 else 118
        total_width = clip_width * len(visible_clips) + gap * (len(visible_clips) - 1)
        left = max(anchor_rect.left + 10, anchor_rect.right - total_width - 12)
        top = anchor_rect.bottom - clip_height - 8
        for index, clip in enumerate(visible_clips):
            clip_rect = pygame.Rect(left + index * (clip_width + gap), top, clip_width, clip_height)
            self._record_actor_sprite_bounds(clip, clip_rect)
            _draw_actor_sprite_clip(
                pygame=pygame,
                fonts=self.fonts,
                surface=surface,
                rect=clip_rect,
                clip=clip,
                elapsed=self._motion_elapsed,
                intensity=strength,
            )

    def handle_event(self, event) -> None:
        if event.type == self.pygame.QUIT:
            self.should_exit = True
            self.exit_reason = "quit"
            return
        if event.type == self.pygame.MOUSEBUTTONDOWN and event.button == 1:
            for target in reversed(self._click_targets):
                if target.rect.collidepoint(event.pos):
                    self._dispatch_click_target(target)
                    return
        if event.type != self.pygame.KEYDOWN:
            return
        if event.key == self.pygame.K_s and self._allow_save:
            self._save_review_archive()
            return
        if event.key in (
            self.pygame.K_ESCAPE,
            self.pygame.K_SPACE,
            self.pygame.K_RETURN,
            self.pygame.K_KP_ENTER,
        ):
            self._primary_action()

    def draw(self, surface) -> None:
        pygame = self.pygame
        self._click_targets = []
        self._reset_actor_sprite_bounds()
        draw_grid(surface, pygame)
        width, height = surface.get_size()
        profile = resolve_layout_profile(width, height)
        footer_height = 116 if height < 700 else 104
        frame = build_frame_layout(
            width,
            height,
            header_height=104,
            footer_height=footer_height,
            nav_visible=True,
            profile=profile,
        )
        gap = profile.gap
        header_rect = pygame.Rect(frame.header.as_tuple())
        footer_rect = pygame.Rect(frame.footer.as_tuple())
        content_rect = pygame.Rect(frame.content.as_tuple())
        left_width = int((content_rect.width - gap) * 0.58)
        right_width = content_rect.width - gap - left_width
        left_rect = pygame.Rect(
            content_rect.left, content_rect.top, left_width, content_rect.height
        )
        right_rect = pygame.Rect(
            left_rect.right + gap, content_rect.top, right_width, content_rect.height
        )

        self._draw_review_header(surface, header_rect)
        self._draw_review_actor_sprite_layer(surface, header_rect)
        self._draw_review_findings(surface, left_rect)
        self._draw_review_sidebar(surface, right_rect)
        self._draw_review_footer(surface, footer_rect)
        items = [
            (
                "Back",
                "Return to the previous screen.",
                "review_primary",
                "",
                self._accent,
            )
        ]
        if self._allow_save:
            items.append(
                (
                    "S Save & Archive",
                    "Record this ending for progression.",
                    "review_save",
                    "",
                    GOOD,
                )
            )
        self._draw_nav_rail(surface, tuple(items))
        self._sync_mouse_cursor()
        self._draw_scene_transition_overlay(surface)

    def _dispatch_click_target(self, target: ClickTarget) -> None:
        if target.kind == "review_primary":
            self._primary_action()
            return
        if target.kind == "review_save" and self._allow_save:
            self._save_review_archive()

    def _save_review_archive(self) -> None:
        self._persist_current_run()
        self._allow_save = False
        self._primary_detail = "Archive recorded. Return to the menu and open Progress."
        self._trigger_review_motion("footer", intensity=0.72)

    def _primary_action(self) -> None:
        if self._return_scene_factory is not None:
            self._next_scene = self._return_scene_factory()
            return
        self.should_exit = True
        self.exit_reason = "quit"

    def _draw_review_header(self, surface, rect) -> None:
        pygame = self.pygame
        width, _height = surface.get_size()
        header_motion = self._motion_level("review:header")
        inner = draw_panel(
            surface,
            pygame,
            rect,
            title="Review",
            accent=self._accent,
            emphasis=header_motion,
            lift=int(header_motion * 3),
        )
        actor_reserve = 150 if width < 960 and self.motion_mode is not MotionMode.OFF else 0
        copy_width = max(220, inner.width - actor_reserve)
        draw_text_line(
            surface,
            self.fonts.title,
            self._view_model.title,
            TEXT,
            pygame.Rect(inner.left, inner.top - 30, copy_width, 30),
            valign="top",
        )
        draw_text_line(
            surface,
            self.fonts.body,
            self._view_model.headline,
            TEXT,
            pygame.Rect(inner.left, inner.top, copy_width, 22),
            valign="top",
        )
        draw_text_line(
            surface,
            self.fonts.small,
            self._view_model.summary_line,
            MUTED,
            pygame.Rect(inner.left, inner.top + 26, copy_width, 18),
            valign="top",
        )

    def _draw_review_findings(self, surface, rect) -> None:
        pygame = self.pygame
        findings_motion = self._motion_level("review:findings")
        inner = draw_panel(
            surface,
            pygame,
            rect,
            title="Findings",
            accent=self._accent,
            emphasis=findings_motion,
            lift=int(findings_motion * 3),
        )
        title_surface = self.fonts.heading.render("Top Findings", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 24))
        if not self._view_model.findings:
            idle_surface = self.fonts.body.render("No findings were recorded.", True, MUTED)
            surface.blit(idle_surface, (inner.left, inner.top))
            return
        top = inner.top
        card_gap = 10
        card_height = 92 if inner.height < 300 else 98
        visible_limit = max(1, int((inner.height + card_gap) / (card_height + card_gap)))
        visible_findings = self._view_model.findings[:visible_limit]
        for finding in visible_findings:
            card_rect = pygame.Rect(inner.left, top, inner.width, card_height)
            accent = tone_color(finding.severity)
            finding_motion = max(
                findings_motion * 0.65, 0.18 if finding.rank_label == "#1" else 0.0
            )
            animated_rect = pygame.Rect(
                card_rect.left,
                card_rect.top - int(finding_motion * 4),
                card_rect.width,
                card_rect.height,
            )
            pygame.draw.rect(
                surface,
                blend_color((26, 38, 55), accent, finding_motion * 0.12),
                animated_rect,
                border_radius=16,
            )
            pygame.draw.rect(
                surface,
                blend_color(accent, TEXT, finding_motion * 0.08),
                animated_rect,
                width=2 if finding_motion >= 0.42 else 1,
                border_radius=16,
            )
            draw_text_line(
                surface,
                self.fonts.body,
                f"{finding.rank_label} {finding.area} | {finding.command}",
                TEXT,
                pygame.Rect(
                    animated_rect.left + 12,
                    animated_rect.top + 10,
                    animated_rect.width - 24,
                    22,
                ),
                valign="top",
            )
            draw_wrapped_text(
                surface,
                self.fonts.small,
                finding.summary,
                MUTED,
                pygame.Rect(
                    animated_rect.left + 12,
                    animated_rect.top + 32,
                    animated_rect.width - 24,
                    28,
                ),
                line_height=15,
                max_lines=2,
            )
            draw_wrapped_text(
                surface,
                self.fonts.small,
                finding.lesson,
                tone_color(finding.severity),
                pygame.Rect(
                    animated_rect.left + 12,
                    animated_rect.top + 62,
                    animated_rect.width - 24,
                    20,
                ),
                line_height=15,
                max_lines=1,
            )
            top += card_height + card_gap
        remaining = len(self._view_model.findings) - len(visible_findings)
        if remaining > 0:
            draw_text_line(
                surface,
                self.fonts.small,
                f"{remaining} more finding(s) available in larger layouts.",
                MUTED,
                pygame.Rect(inner.left, inner.bottom - 18, inner.width, 18),
                valign="top",
            )

    def _draw_review_sidebar(self, surface, rect) -> None:
        pygame = self.pygame
        sidebar_motion = self._motion_level("review:sidebar")
        inner = draw_panel(
            surface,
            pygame,
            rect,
            title="Summary",
            accent=INFO,
            emphasis=sidebar_motion,
            lift=int(sidebar_motion * 2),
        )
        title_surface = self.fonts.heading.render("Next Focus", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 24))
        draw_text_line(
            surface,
            self.fonts.body,
            self._view_model.next_focus,
            INFO,
            pygame.Rect(inner.left, inner.top, inner.width, 22),
            valign="top",
        )
        badge_label_top = inner.top + 30
        badge_top = inner.top + 52
        badge_limit = 6
        if self._view_model.campaign_legacy_title:
            draw_text_line(
                surface,
                self.fonts.small,
                "Campaign Legacy",
                MUTED,
                pygame.Rect(inner.left, inner.top + 30, inner.width, 18),
                valign="top",
            )
            draw_text_line(
                surface,
                self.fonts.small,
                self._view_model.campaign_legacy_title,
                TEXT,
                pygame.Rect(inner.left, inner.top + 50, inner.width, 18),
                valign="top",
            )
            draw_wrapped_text(
                surface,
                self.fonts.small,
                self._view_model.campaign_legacy_detail,
                INFO,
                pygame.Rect(inner.left, inner.top + 70, inner.width, 36),
                line_height=15,
                max_lines=2,
            )
            badge_label_top = inner.top + 112
            badge_top = inner.top + 134
            badge_limit = 4
        draw_text_line(
            surface,
            self.fonts.small,
            "Badges",
            MUTED,
            pygame.Rect(inner.left, badge_label_top, inner.width, 18),
            valign="top",
        )
        top = badge_top
        for badge in self._view_model.badges[:badge_limit]:
            chip_rect = pygame.Rect(inner.left, top, inner.width, 28)
            pygame.draw.rect(
                surface,
                blend_color((24, 35, 50), INFO, sidebar_motion * 0.08),
                chip_rect,
                border_radius=12,
            )
            pygame.draw.rect(
                surface,
                blend_color(BORDER, INFO, sidebar_motion * 0.12),
                chip_rect,
                width=1,
                border_radius=12,
            )
            draw_text_line(
                surface,
                self.fonts.small,
                badge.replace("_", " "),
                TEXT,
                pygame.Rect(chip_rect.left + 10, chip_rect.top + 5, chip_rect.width - 20, 18),
            )
            top += 36

    def _draw_review_footer(self, surface, rect) -> None:
        pygame = self.pygame
        footer_motion = self._motion_level("review:footer")
        inner = draw_panel(
            surface,
            pygame,
            rect,
            title="Actions",
            accent=self._accent,
            emphasis=footer_motion,
            lift=int(footer_motion * 2),
        )
        actions = [(self._primary_title, self._primary_detail, self._accent, "review_primary")]
        if self._allow_save:
            actions.append(
                (
                    "S Save & Archive",
                    "Record this ending for progression.",
                    GOOD,
                    "review_save",
                )
            )
        gap = 12
        button_count = len(actions)
        max_button_width = 300 if button_count == 1 else 260
        button_width = min(
            max_button_width,
            int((inner.width - gap * max(0, button_count - 1)) / button_count),
        )
        total_width = button_width * button_count + gap * max(0, button_count - 1)
        left = inner.left + max(0, (inner.width - total_width) // 2)
        top = inner.top + max(8, (inner.height - 40) // 2)
        for index, (title, detail, accent, kind) in enumerate(actions):
            button_rect = pygame.Rect(left + index * (button_width + gap), top, button_width, 40)
            draw_button(
                surface,
                pygame,
                rect=button_rect,
                title=title,
                detail=detail,
                accent=accent,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
            )
            self._click_targets.append(ClickTarget(kind, "", button_rect))


class RunScene(BaseScene):
    """Main playable dashboard scene."""

    def __init__(
        self,
        *,
        pygame,
        fonts: FontPack,
        state: GameState,
        rng: RandomSource,
        slot_name: str,
        save_callback,
        selected_product_id: str | None = None,
        initial_panel_key: str | None = None,
        seed_events: tuple[FrontendEvent, ...] = (),
        dirty: bool = False,
        show_ready_event: bool = True,
        motion_mode: MotionMode | str = MotionMode.FULL,
        entry_transition: str = "boot_run",
        return_scene_factory: Callable[[], BaseScene] | None = None,
        preferences: FrontendPreferences | None = None,
        preference_callback: Callable[[FrontendPreferences], FontPack] | None = None,
        preference_provider: Callable[[], FrontendPreferences] | None = None,
    ) -> None:
        super().__init__(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=rng,
            slot_name=slot_name,
            save_callback=save_callback,
            dirty=dirty,
            motion_mode=motion_mode,
            entry_transition=entry_transition,
            preferences=preferences,
            preference_callback=preference_callback,
            preference_provider=preference_provider,
        )
        self._events: list[TimedFrontendEvent] = []
        self._action_feedback_cues: list[ActionFeedbackCue] = []
        self._impact_cues: list[ImpactCue] = []
        self._overlay_enter_elapsed: dict[str, float] = {}
        self._overlay_exit_cues: list[OverlayExitCue] = []
        self._pending_choice_cues: list[PendingChoiceCue] = []
        self._late_game_choreography_cues: list[LateGameChoreographyCue] = []
        self._click_targets: list[ClickTarget] = []
        self._context_picker: ContextPicker | None = None
        self._text_input: TextInputModalState | None = None
        self._deep_panel_key: str | None = None
        self._inspector_panel_key: str | None = None
        self._inspector_section_index = 0
        self._inspector_page = 0
        self._inspector_item_index = 0
        self._inspector_sort_mode_index = 0
        self._inspector_filter_mode_index = 0
        self._inspector_memory: dict[str, InspectorMemoryState] = {}
        self._help_overlay_visible = False
        self._pause_overlay_visible = False
        self._pause_settings_visible = False
        self._focus_mode = True
        self._endgame_actions_expanded = False
        self._return_scene_factory = return_scene_factory
        self._terminal_archive_saved = False
        self._first_turn_guide_visible = False
        self._product_index = 0
        self._motion_elapsed = 0.0
        self._tweens = TweenBank(speed=9.0)
        self._motion_pulses = PulseBank(
            decay=1.8,
            intensity_scale=self.motion_mode.pulse_scale,
        )
        self._set_selected_product(selected_product_id)
        self._view_model = build_game_view_model(
            self.state,
            selected_product_id=self.selected_product.id.hex,
        )
        self._sync_tweens()
        self._set_deep_panel(initial_panel_key)
        self.push_events(seed_events)
        if show_ready_event:
            self.push_event(
                FrontendEvent(
                    title="2D Frontend Ready",
                    detail=(
                        "Use mouse or keys. Click coach cards, products, or action buttons to play."
                    ),
                    severity="info",
                    ttl=6.0,
                )
            )

    @property
    def selected_product(self):
        products = self._product_choices()
        self._product_index = min(self._product_index, len(products) - 1)
        return products[self._product_index]

    @property
    def deep_panel(self) -> DeepDivePanelViewModel | None:
        if self._deep_panel_key is None:
            return None
        for panel in self._view_model.deep_panels:
            if panel.key == self._deep_panel_key:
                return panel
        return None

    @property
    def inspector_panel(self) -> DeepDivePanelViewModel | None:
        if self._inspector_panel_key is None:
            return None
        for panel in self._view_model.deep_panels:
            if panel.key == self._inspector_panel_key:
                return panel
        return None

    def _overlay_motion_level(self, overlay_key: str) -> float:
        return self._motion_level(f"overlay:{overlay_key}")

    def _trigger_overlay_motion(self, overlay_key: str, *, intensity: float = 0.7) -> None:
        self._motion_pulses.trigger(f"overlay:{overlay_key}", intensity=intensity, decay=2.2)

    def _overlay_transition_duration(self) -> float:
        if self.motion_mode is MotionMode.OFF:
            return 0.0
        return 0.18 if self.motion_mode is MotionMode.REDUCED else 0.3

    def _active_overlay_keys(self) -> set[str]:
        keys: set[str] = set()
        if self.state.pending_event is not None:
            keys.add("pending")
        if self._context_picker is not None:
            keys.add("picker")
        if self._text_input is not None:
            keys.add("text_input")
        if self._deep_panel_key is not None:
            keys.add("panel")
        if self._inspector_panel_key is not None:
            keys.add("inspector")
        if self._help_overlay_visible:
            keys.add("help")
        if self._pause_overlay_visible:
            keys.add("pause")
        if self._pause_settings_visible:
            keys.add("pause_settings")
        if self.state.company.game_over or self.state.victory_achieved:
            keys.add("outcome")
        return keys

    def _sync_overlay_transitions(self, dt: float) -> None:
        active_keys = self._active_overlay_keys()
        for key in tuple(self._overlay_enter_elapsed):
            if key not in active_keys:
                self._overlay_enter_elapsed.pop(key, None)
        for key in active_keys:
            if key not in self._overlay_enter_elapsed:
                self._overlay_enter_elapsed[key] = 0.0
                if key in {"pending", "outcome"}:
                    self._trigger_overlay_motion(key, intensity=0.76)
                    if key == "pending" and self.state.pending_event is not None:
                        for index, _option in enumerate(self.state.pending_event.options[:3]):
                            self._motion_pulses.trigger(
                                f"pending:option:{index}",
                                intensity=max(0.36, 0.68 - index * 0.08),
                                decay=2.0,
                            )
            else:
                self._overlay_enter_elapsed[key] += dt

    def _overlay_enter_progress(self, overlay_key: str) -> float:
        duration = self._overlay_transition_duration()
        if duration <= 0:
            return 1.0
        elapsed = (
            self._overlay_enter_elapsed.get(overlay_key, 0.0)
            if overlay_key in self._active_overlay_keys()
            else duration
        )
        ratio = max(0.0, min(1.0, elapsed / duration))
        return 1.0 - (1.0 - ratio) * (1.0 - ratio)

    def overlay_transition_active(self) -> bool:
        """Return whether a modal overlay enter/exit animation is visible."""

        if self.motion_mode is MotionMode.OFF:
            return False
        if self._overlay_exit_cues:
            return True
        return any(self._overlay_enter_progress(key) < 1.0 for key in self._active_overlay_keys())

    def product_drama_active(self) -> bool:
        """Return whether product-card status animation should be visible."""

        if self.motion_mode is MotionMode.OFF:
            return False
        return any(
            product.selected
            or product.quality_ratio >= 0.72
            or product.bug_ratio >= 0.35
            or product.debt_ratio >= 0.45
            or product.fit_ratio >= 0.7
            for product in self._view_model.products
        )

    def risk_drama_active(self) -> bool:
        """Return whether finance/board/endgame risk drama should be visible."""

        if self.motion_mode is MotionMode.OFF:
            return False
        return any(
            gauge.key in {"cash", "runway", "board_pressure"}
            and (gauge.tone in {"warning", "danger"} or gauge.ratio <= 0.28)
            for gauge in self._view_model.stats
        )

    def pending_choice_active(self) -> bool:
        """Return whether a pending-choice consequence cue is visible."""

        return self.motion_mode is not MotionMode.OFF and bool(self._pending_choice_cues)

    def outcome_cinematic_active(self) -> bool:
        """Return whether the victory/shutdown outcome cinematic layer is visible."""

        return self.motion_mode is not MotionMode.OFF and (
            self.state.company.game_over or self.state.victory_achieved
        )

    def pending_choice_preview_active(self) -> bool:
        """Return whether pending-event options should expose animated previews."""

        return self.motion_mode is not MotionMode.OFF and self.state.pending_event is not None

    def late_game_choreography_active(self) -> bool:
        """Return whether a late-game command choreography card is visible."""

        return self.motion_mode is not MotionMode.OFF and bool(self._late_game_choreography_cues)

    def _animated_overlay_rect(self, rect, overlay_key: str, *, shift: int = 34):
        if self.motion_mode is MotionMode.OFF:
            return rect
        progress = self._overlay_enter_progress(overlay_key)
        direction = -1 if overlay_key in {"pending", "outcome"} else 1
        offset = int((1.0 - progress) * shift * direction)
        return self.pygame.Rect(rect.left, rect.top + offset, rect.width, rect.height)

    def _trigger_overlay_exit(self, overlay_key: str) -> None:
        if self.motion_mode is MotionMode.OFF:
            return
        duration = 0.26 if self.motion_mode is MotionMode.REDUCED else 0.42
        accent = {
            "pending": WARN,
            "picker": INFO,
            "text_input": SELECTION,
            "panel": INFO,
            "inspector": SELECTION,
            "help": INFO,
            "pause": WARN,
            "outcome": DANGER,
        }.get(overlay_key, INFO)
        label = {
            "pending": "Pending Closed",
            "picker": "Picker Closed",
            "text_input": "Text Closed",
            "panel": "Panel Closed",
            "inspector": "Inspector Closed",
            "help": "Help Closed",
            "pause": "Pause Closed",
            "outcome": "Outcome Closed",
        }.get(overlay_key, "Overlay Closed")
        self._overlay_exit_cues.insert(
            0,
            OverlayExitCue(
                key=overlay_key,
                label=label,
                accent=accent,
                time_left=duration,
                duration=duration,
            ),
        )
        self._overlay_exit_cues = self._overlay_exit_cues[:3]
        self._motion_pulses.trigger("overlay:exit", intensity=0.5, decay=1.4)

    def _trigger_inspector_motion(self, lane_key: str, *, intensity: float = 0.55) -> None:
        self._trigger_overlay_motion("inspector", intensity=max(0.42, intensity * 0.72))
        self._motion_pulses.trigger(f"inspector:{lane_key}", intensity=intensity, decay=2.0)

    def _set_deep_panel(self, panel_key: str | None) -> None:
        if panel_key == self._deep_panel_key:
            return
        previous_key = self._deep_panel_key
        self._deep_panel_key = panel_key
        if panel_key == "endgame":
            self._endgame_actions_expanded = False
        if panel_key is not None:
            self._trigger_overlay_motion("panel", intensity=0.75)
            self._motion_pulses.trigger(f"panel:{panel_key}", intensity=0.7, decay=2.0)
            if panel_key == "endgame":
                self._announce_endgame_cockpit()
        elif previous_key is not None:
            self._trigger_overlay_exit("panel")

    def _toggle_endgame_actions(self) -> None:
        if self._deep_panel_key != "endgame" or self.deep_panel is None:
            return
        self._endgame_actions_expanded = not self._endgame_actions_expanded
        self._trigger_overlay_motion("panel", intensity=0.56)
        self._motion_pulses.trigger("panel:endgame", intensity=0.62, decay=1.8)

    def _announce_endgame_cockpit(self) -> None:
        panel = self.deep_panel
        if panel is None or panel.key != "endgame":
            return
        blocked_line = next(
            (line for line in panel.detail_lines if line.lower().startswith("blocked paths:")),
            panel.detail_lines[0] if panel.detail_lines else panel.summary,
        )
        gate_action = next(
            (action for action in panel.actions if action.label == "Recommended Fix"), None
        )
        detail = blocked_line
        if gate_action is not None:
            detail = f"{detail} | {gate_action.detail}"
        self.push_event(
            FrontendEvent(
                title="Endgame Cockpit",
                detail=detail,
                severity="warning",
                ttl=5.2,
                motion="slide",
                targets=("feed", "panel:endgame"),
            )
        )

    def _panel_display_name(self, panel_key: str) -> str:
        panel = next(
            (entry for entry in self._view_model.deep_panels if entry.key == panel_key), None
        )
        if panel is not None:
            return panel.title
        return panel_key.replace("_", " ").title()

    def _push_workspace_handoff_event(
        self,
        command: str,
        *,
        source_panel_key: str | None,
        target_panel_key: str | None,
        overlay_key: str | None = None,
    ) -> None:
        if (
            source_panel_key is None
            or target_panel_key is None
            or source_panel_key == target_panel_key
        ):
            return
        source_title = self._panel_display_name(source_panel_key)
        target_title = self._panel_display_name(target_panel_key)
        detail = f"`{command}` moved focus from {source_title} to {target_title}."
        targets = ("feed", f"panel:{source_panel_key}", f"panel:{target_panel_key}")
        if overlay_key == "inspector":
            detail = f"{detail} Inspector opened on the late-game hotspot."
            targets = targets + ("overlay:inspector",)
        elif overlay_key == "picker":
            detail = f"{detail} Choose the follow-up option in the picker."
            targets = targets + ("overlay:picker",)
        elif overlay_key == "text":
            detail = f"{detail} Finish the context in the text modal."
            targets = targets + ("overlay:text",)
        self.push_event(
            FrontendEvent(
                title="Cockpit Handoff" if source_panel_key == "endgame" else "Workspace Handoff",
                detail=detail,
                severity="warning" if source_panel_key == "endgame" else "info",
                ttl=5.2,
                motion="slide",
                targets=targets,
            )
        )

    def _set_context_picker(self, picker: ContextPicker | None) -> None:
        previous_picker = self._context_picker
        self._context_picker = picker
        if picker is not None:
            self._trigger_overlay_motion("picker", intensity=0.78)
        elif previous_picker is not None:
            self._trigger_overlay_exit("picker")

    def _set_text_input(self, modal: TextInputModalState | None) -> None:
        previous_modal = self._text_input
        self._text_input = modal
        if modal is not None:
            self._trigger_overlay_motion("text_input", intensity=0.78)
        elif previous_modal is not None:
            self._trigger_overlay_exit("text_input")

    def _set_help_overlay_visible(self, visible: bool) -> None:
        previous_visible = self._help_overlay_visible
        self._help_overlay_visible = visible
        if visible:
            self._pause_overlay_visible = False
            self._pause_settings_visible = False
            self._trigger_overlay_motion("help", intensity=0.7)
        elif previous_visible:
            self._trigger_overlay_exit("help")

    def _set_pause_overlay_visible(self, visible: bool) -> None:
        previous_visible = self._pause_overlay_visible
        self._pause_overlay_visible = visible
        if visible:
            self._help_overlay_visible = False
            self._trigger_overlay_motion("pause", intensity=0.76)
        elif previous_visible:
            self._pause_settings_visible = False
            self._trigger_overlay_exit("pause")

    def _set_pause_settings_visible(self, visible: bool) -> None:
        previous_visible = self._pause_settings_visible
        self._pause_settings_visible = visible and self._pause_overlay_visible
        if self._pause_settings_visible:
            self._trigger_overlay_motion("pause_settings", intensity=0.72)
        elif previous_visible:
            self._trigger_overlay_exit("pause_settings")

    def _open_inspector(self, panel_key: str) -> None:
        self._trigger_overlay_motion("inspector", intensity=0.82)
        self._motion_pulses.trigger(f"panel:{panel_key}", intensity=0.72, decay=2.0)
        self._inspector_panel_key = panel_key
        memory = self._inspector_memory.get(panel_key)
        if memory is None:
            self._inspector_section_index = 0
            self._inspector_page = 0
            self._inspector_item_index = 0
            self._inspector_sort_mode_index = 0
            self._inspector_filter_mode_index = 0
        else:
            self._inspector_page = memory.page
            self._inspector_item_index = memory.item_index
            self._inspector_sort_mode_index = memory.sort_mode_index
            self._inspector_filter_mode_index = memory.filter_mode_index
            panel = self.inspector_panel
            if panel is None or not panel.inspectors:
                self._inspector_section_index = 0
            else:
                self._inspector_section_index = next(
                    (
                        index
                        for index, section in enumerate(panel.inspectors)
                        if section.key == memory.section_key
                    ),
                    0,
                )
        self._sync_inspector_selection()
        if self._inspector_panel_key == panel_key:
            self._queue_action_feedback(f"inspect_{panel_key}")

    def _close_inspector(self) -> None:
        if self._inspector_panel_key is None:
            return
        self._inspector_panel_key = None
        self._trigger_overlay_exit("inspector")

    def _selected_inspector_section(self):
        panel = self.inspector_panel
        if panel is None or not panel.inspectors:
            return None
        return panel.inspectors[self._inspector_section_index]

    def _selected_inspector_item(self):
        section = self._selected_inspector_section()
        if section is None:
            return None
        page_items = self._current_inspector_page_items()
        if not page_items:
            return None
        return page_items[self._inspector_item_index]

    def update(self, dt: float) -> None:
        """Advance animations and expire transient event cards."""

        safe_dt = max(0.0, dt)
        self._motion_elapsed += safe_dt
        self._sync_overlay_transitions(safe_dt)
        self._tweens.update(dt)
        self._update_scene_transition(dt)
        if self._pause_overlay_visible:
            return
        self._motion_pulses.update(dt)
        self._stabilize_motion_bank()
        self._events = [
            TimedFrontendEvent(payload=event.payload, time_left=event.time_left - dt)
            for event in self._events
            if event.time_left - dt > 0
        ]
        self._action_feedback_cues = [
            ActionFeedbackCue(
                command=cue.command,
                label=cue.label,
                family=cue.family,
                accent=cue.accent,
                targets=cue.targets,
                time_left=cue.time_left - dt,
                duration=cue.duration,
                outcome=cue.outcome,
                detail=cue.detail,
            )
            for cue in self._action_feedback_cues
            if cue.time_left - dt > 0
        ]
        self._impact_cues = [
            ImpactCue(
                label=cue.label,
                value_text=cue.value_text,
                tone=cue.tone,
                accent=cue.accent,
                targets=cue.targets,
                time_left=cue.time_left - dt,
                duration=cue.duration,
            )
            for cue in self._impact_cues
            if cue.time_left - dt > 0
        ]
        self._overlay_exit_cues = [
            OverlayExitCue(
                key=cue.key,
                label=cue.label,
                accent=cue.accent,
                time_left=cue.time_left - dt,
                duration=cue.duration,
            )
            for cue in self._overlay_exit_cues
            if cue.time_left - dt > 0
        ]
        self._pending_choice_cues = [
            PendingChoiceCue(
                label=cue.label,
                detail=cue.detail,
                accent=cue.accent,
                time_left=cue.time_left - dt,
                duration=cue.duration,
            )
            for cue in self._pending_choice_cues
            if cue.time_left - dt > 0
        ]
        self._late_game_choreography_cues = [
            LateGameChoreographyCue(
                command=cue.command,
                label=cue.label,
                detail=cue.detail,
                family=cue.family,
                accent=cue.accent,
                targets=cue.targets,
                time_left=cue.time_left - dt,
                duration=cue.duration,
            )
            for cue in self._late_game_choreography_cues
            if cue.time_left - dt > 0
        ]

    def _stabilize_motion_bank(self) -> None:
        if self._motion_pulses.live_count() <= 18:
            return
        max_count = 14 if self._window_width() < 960 or self._overlay_or_pending_active() else 18
        protected_prefixes = ["feed", "footer", "overlay:"]
        if self._deep_panel_key is not None:
            protected_prefixes.append(f"panel:{self._deep_panel_key}")
        if self._inspector_panel_key is not None:
            protected_prefixes.append(f"panel:{self._inspector_panel_key}")
        self._motion_pulses.prune(
            max_count=max_count,
            min_value=0.18,
            protected_prefixes=tuple(protected_prefixes),
        )

    def handle_event(self, event) -> None:
        """Handle one pygame event."""

        if event.type == self.pygame.QUIT:
            self.should_exit = True
            self.exit_reason = "quit"
            return

        if event.type == self.pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_mouse_click(event.pos)
            return

        if event.type != self.pygame.KEYDOWN:
            return

        if event.key == self.pygame.K_p and self._text_input is None:
            self._set_pause_overlay_visible(not self._pause_overlay_visible)
            return

        if event.key == self.pygame.K_F1 or event.unicode == "?":
            self._set_help_overlay_visible(not self._help_overlay_visible)
            return

        if event.key == self.pygame.K_ESCAPE:
            if self._help_overlay_visible:
                self._set_help_overlay_visible(False)
                return
            if self._pause_overlay_visible:
                if self._pause_settings_visible:
                    self._set_pause_settings_visible(False)
                    return
                self._set_pause_overlay_visible(False)
                return
            if self._text_input is not None:
                self._set_text_input(None)
                return
            if self._context_picker is not None:
                self._set_context_picker(None)
                return
            if self._inspector_panel_key is not None:
                self._close_inspector()
                return
            if self._deep_panel_key is not None:
                self._set_deep_panel(None)
                return
            self._set_pause_overlay_visible(True)
            return

        if self._pause_overlay_visible:
            if self._pause_settings_visible:
                if event.key == self.pygame.K_1:
                    self._cycle_frontend_preference("ui_scale")
                elif event.key == self.pygame.K_2:
                    self._cycle_frontend_preference("contrast_mode")
                elif event.key == self.pygame.K_3:
                    self._cycle_frontend_preference("motion_mode")
                elif event.key == self.pygame.K_4:
                    self._cycle_frontend_preference("action_loadout")
                elif event.key == self.pygame.K_r:
                    self._reset_frontend_preferences()
                elif event.key == self.pygame.K_b:
                    self._set_pause_settings_visible(False)
                return
            if event.key == self.pygame.K_s:
                self._save_current_run()
            elif event.key == self.pygame.K_t:
                self._set_pause_settings_visible(True)
            elif event.key == self.pygame.K_m:
                self._return_to_menu_or_quit()
            elif event.key == self.pygame.K_q:
                self.should_exit = True
                self.exit_reason = "quit"
            return

        if self._help_overlay_visible:
            return

        if self._text_input is not None:
            self._handle_text_input_key(event)
            return

        if self._context_picker is not None:
            self._handle_picker_key(event)
            return

        if self._inspector_panel_key is not None:
            if event.key == self.pygame.K_TAB:
                direction = -1 if event.mod & self.pygame.KMOD_SHIFT else 1
                self._change_inspector_section(direction)
                return
            if event.key == self.pygame.K_LEFT:
                self._change_inspector_section(-1)
                return
            if event.key == self.pygame.K_RIGHT:
                self._change_inspector_section(1)
                return
            if event.key == self.pygame.K_UP:
                self._change_inspector_item(-1)
                return
            if event.key == self.pygame.K_DOWN:
                self._change_inspector_item(1)
                return
            if event.key == self.pygame.K_PAGEUP:
                self._change_inspector_page(-1)
                return
            if event.key == self.pygame.K_PAGEDOWN:
                self._change_inspector_page(1)
                return
            if event.key == self.pygame.K_z:
                self._cycle_inspector_sort_mode()
                return
            if event.key == self.pygame.K_x:
                self._cycle_inspector_filter_mode()
                return
            if event.key == self.pygame.K_a:
                self._focus_inspector_actionable()
                return
            if event.key == self.pygame.K_h:
                self._focus_inspector_hotspot()
                return
            if event.key in (self.pygame.K_RETURN, self.pygame.K_KP_ENTER):
                self._run_selected_inspector_primary_action()
                return
            if event.key == self.pygame.K_s:
                self._save_current_run()
                return
            digit_index = self._digit_index(event)
            if digit_index is not None:
                self._run_selected_inspector_action(digit_index)
            return

        if self.state.company.game_over or self.state.victory_achieved:
            if event.key == self.pygame.K_s:
                self._save_current_run()
            elif event.key in (
                self.pygame.K_r,
                self.pygame.K_SPACE,
                self.pygame.K_RETURN,
                self.pygame.K_KP_ENTER,
            ):
                self._open_review_scene()
            return

        if self.state.pending_event is not None:
            self._handle_pending_event_key(event)
            return

        if self._deep_panel_key == "endgame" and event.key == self.pygame.K_v:
            self._toggle_endgame_actions()
            return

        if event.key == self.pygame.K_s:
            self._save_current_run()
            return

        if event.key == self.pygame.K_0:
            self._toggle_focus_mode()
            return

        if event.key == self.pygame.K_1:
            self._set_deep_panel("team")
            return
        if event.key == self.pygame.K_2:
            self._set_deep_panel("finance")
            return
        if event.key == self.pygame.K_3:
            self._set_deep_panel("customers")
            return
        if event.key == self.pygame.K_4:
            self._set_deep_panel("partnerships")
            return
        if event.key == self.pygame.K_5:
            self._set_deep_panel("board")
            return
        if event.key == self.pygame.K_6:
            self._set_deep_panel("pipeline")
            return
        if event.key == self.pygame.K_7:
            self._set_deep_panel("report")
            return
        if event.key == self.pygame.K_8:
            self._set_deep_panel("endgame")
            return
        if event.key == self.pygame.K_n:
            self._open_create_product_modal()
            return
        if (
            event.key == self.pygame.K_i
            and self._deep_panel_key is not None
            and self.deep_panel is not None
            and self.deep_panel.inspectors
        ):
            self._open_inspector(self._deep_panel_key)
            return

        if event.key == self.pygame.K_TAB:
            direction = -1 if event.mod & self.pygame.KMOD_SHIFT else 1
            self._cycle_product(direction)
            return

        intent = self._intent_for_key(event.key)
        if intent is None:
            return
        self._handle_intent(intent)

    def draw(self, surface) -> None:
        """Draw the complete frame."""

        pygame = self.pygame
        self._click_targets = []
        self._first_turn_guide_visible = False
        self._reset_actor_sprite_bounds()
        self._reset_layout_separation_guards()
        draw_grid(surface, pygame)
        width, height = surface.get_size()
        profile = resolve_layout_profile(width, height)
        footer_height = self._footer_outer_height(width, height)
        frame = build_frame_layout(
            width,
            height,
            header_height=profile.run_header_height,
            footer_height=footer_height,
            nav_visible=not self._pause_overlay_visible,
            profile=profile,
        )
        margin = profile.margin
        gap = profile.gap
        header_rect = pygame.Rect(frame.header.as_tuple())
        footer_rect = pygame.Rect(frame.footer.as_tuple())
        content_top = frame.content.top
        content_height = frame.content.height
        content_rect = pygame.Rect(
            margin,
            content_top,
            width - margin * 2,
            content_height,
        )
        use_compact_focus = self._use_compact_run_focus(width, content_rect.height)
        if use_compact_focus:
            left_rect = content_rect
            center_rect = pygame.Rect(0, 0, 0, 0)
            right_rect = pygame.Rect(0, 0, 0, 0)
        elif width < 940:
            section_height = int((content_height - gap * 2) / 3)
            left_rect = pygame.Rect(margin, content_top, width - margin * 2, section_height)
            center_rect = pygame.Rect(
                margin,
                left_rect.bottom + gap,
                width - margin * 2,
                section_height,
            )
            right_rect = pygame.Rect(
                margin,
                center_rect.bottom + gap,
                width - margin * 2,
                content_top + content_height - center_rect.bottom - gap,
            )
        elif width < 1260:
            top_height = int((content_height - gap) * 0.52)
            left_width = int((width - margin * 2 - gap) * 0.42)
            center_width = width - margin * 2 - gap - left_width
            left_rect = pygame.Rect(margin, content_top, left_width, top_height)
            center_rect = pygame.Rect(
                left_rect.right + gap,
                content_top,
                center_width,
                top_height,
            )
            right_rect = pygame.Rect(
                margin,
                left_rect.bottom + gap,
                width - margin * 2,
                content_top + content_height - left_rect.bottom - gap,
            )
        else:
            left_width = int((width - margin * 2 - gap * 2) * 0.27)
            center_width = int((width - margin * 2 - gap * 2) * 0.36)
            right_width = width - margin * 2 - gap * 2 - left_width - center_width
            left_rect = pygame.Rect(margin, content_top, left_width, content_height)
            center_rect = pygame.Rect(
                left_rect.right + gap,
                content_top,
                center_width,
                content_height,
            )
            right_rect = pygame.Rect(
                center_rect.right + gap,
                content_top,
                right_width,
                content_height,
            )

        self._draw_header(surface, header_rect)
        self._draw_actor_sprite_layer(surface, header_rect)
        if use_compact_focus:
            self._draw_compact_run_focus(surface, content_rect)
        else:
            self._draw_left_column(surface, left_rect)
            self._draw_center_column(surface, center_rect)
            self._draw_right_column(surface, right_rect)
        self._draw_footer(surface, footer_rect)

        if self.state.pending_event is not None:
            self._draw_pending_event_overlay(surface)
        if self._context_picker is not None:
            self._draw_context_picker_overlay(surface)
        if self._text_input is not None:
            self._draw_text_input_overlay(surface)
        if self._deep_panel_key is not None:
            self._draw_deep_panel_overlay(surface)
        if self._inspector_panel_key is not None:
            self._draw_inspector_overlay(surface)
        if self._help_overlay_visible:
            self._draw_help_overlay(surface)
        if self.state.company.game_over or self.state.victory_achieved:
            self._draw_outcome_overlay(surface)
        self._draw_overlay_exit_cues(surface)
        self._draw_pending_choice_cues(surface)
        self._draw_late_game_choreography_cues(surface)
        self._draw_impact_cues(surface)
        self._draw_action_feedback_cues(surface)
        if not self._pause_overlay_visible:
            nav_items = [
                ("P Pause", "Open pause, save, and menu controls.", "pause_toggle", "", WARN),
                ("Esc Back", "Close overlay or open pause.", "run_back", "", INFO),
            ]
            if width >= 940:
                nav_items.append(
                    (
                        "0 More" if self._focus_mode else "0 Focus",
                        "Open all actions or return to the guided decision view.",
                        "focus_toggle",
                        "",
                        GOOD,
                    )
                )
            nav_items.append(("F1 Help", "Show the controls guide.", "open_help", "", SELECTION))
            self._draw_nav_rail(
                surface,
                tuple(nav_items),
            )
        if self._pause_overlay_visible:
            if self._pause_settings_visible:
                self._draw_pause_settings_overlay(surface)
            else:
                self._draw_pause_overlay(surface)
        self._sync_mouse_cursor()
        self._draw_hover_tooltip(surface)
        self._draw_scene_transition_overlay(surface)

    def push_event(self, payload: FrontendEvent) -> None:
        """Add one transient UI event card."""

        payload = self._normalized_event_payload(payload)
        for index, timed_event in enumerate(self._events):
            if (
                timed_event.payload.title == payload.title
                and timed_event.payload.detail == payload.detail
                and timed_event.payload.severity == payload.severity
            ):
                self._events.pop(index)
                break
        self._events.insert(0, TimedFrontendEvent(payload=payload, time_left=payload.ttl))
        self._trim_event_backlog()
        self._trigger_event_motion(payload)

    def push_events(self, payloads: tuple[FrontendEvent, ...]) -> None:
        """Add multiple transient event cards."""

        for payload in reversed(payloads):
            self.push_event(payload)

    def _overlay_or_pending_active(self) -> bool:
        return (
            self._deep_panel_key is not None
            or self._inspector_panel_key is not None
            or self._context_picker is not None
            or self._text_input is not None
            or self._pause_overlay_visible
            or self.state.pending_event is not None
        )

    def first_turn_guide_active(self) -> bool:
        """Return whether the compact live-run onboarding guide is visible."""

        return self._first_turn_guide_visible

    def _first_turn_guide_active(self) -> bool:
        if self.state.company.game_over or self.state.victory_achieved:
            return False
        if self._overlay_or_pending_active():
            return False
        return build_guided_opening(self.state).active

    def _first_turn_guide_steps(self) -> tuple[FirstTurnGuideStep, ...]:
        opening = build_guided_opening(self.state)
        first_step_done = bool(opening.steps and opening.steps[0].status == "done")
        resolved_once = bool(self.state.turn_history) or self.state.company.current_turn > 1
        spent_actions = first_step_done and (
            self.state.action_points_remaining <= 0 or resolved_once
        )
        finished_turn = spent_actions and resolved_once
        ap_label = f"{max(0, self.state.action_points_remaining)} AP left"
        command_label = self._compact_button_detail(
            get_action_label(opening.current_command),
            max_length=24,
        )
        return (
            FirstTurnGuideStep(
                "1 Coach Move",
                f"C / click runs {command_label}",
                first_step_done,
                INFO,
            ),
            FirstTurnGuideStep(
                "2 Spend AP",
                ap_label,
                spent_actions,
                GOOD,
            ),
            FirstTurnGuideStep(
                "3 End Turn",
                "Space after spending AP",
                finished_turn,
                SELECTION,
            ),
        )

    def _motion_pressure_ratio(self) -> float:
        live_count = self._motion_pulses.live_count()
        total_intensity = self._motion_pulses.total_intensity()
        pressure = max(0.0, live_count - 10) * 0.015
        pressure += max(0.0, total_intensity - 5.0) * 0.01
        return min(0.32, pressure)

    def _normalized_event_payload(self, payload: FrontendEvent) -> FrontendEvent:
        ttl = payload.ttl
        pressure = self._motion_pressure_ratio()
        if payload.severity in {"info", "success"}:
            if self._window_width() < 920:
                ttl *= 0.9
            if self._overlay_or_pending_active():
                ttl *= 0.84
            if len(self._events) >= 4:
                ttl *= 0.82
            if pressure > 0:
                ttl *= 1.0 - pressure * 0.65
            ttl = max(3.2, min(payload.ttl, ttl))
        elif payload.severity == "warning":
            if self._overlay_or_pending_active() and len(self._events) >= 4:
                ttl = max(4.0, min(payload.ttl, payload.ttl * 0.92))
            if pressure > 0:
                ttl = max(4.0, min(ttl, ttl * (1.0 - pressure * 0.28)))
        if abs(ttl - payload.ttl) < 0.01:
            return payload
        return FrontendEvent(
            title=payload.title,
            detail=payload.detail,
            severity=payload.severity,
            ttl=round(ttl, 2),
            motion=payload.motion,
            targets=payload.targets,
        )

    def _event_retention_limit(self) -> int:
        limit = 6
        if self._window_width() < 920:
            limit = 5
        if self._overlay_or_pending_active():
            limit = min(limit, 4)
        return limit

    def _event_backlog_score(
        self,
        timed_event: TimedFrontendEvent,
        index: int,
    ) -> tuple[int, int, int]:
        payload = timed_event.payload
        severity = _TONE_PRIORITY.get(payload.severity, 0)
        title_boost = 0
        if payload.title in {
            "Company Shutdown",
            "Victory Achieved",
            "Exit Gates",
            "Gate Command",
            "Endgame Cockpit",
            "Cockpit Handoff",
            "Next Focus",
        }:
            title_boost += 3
        if payload.motion == "flash":
            title_boost += 1
        workspace_targets = sum(
            1
            for target in payload.targets
            if target.startswith("panel:") or target.startswith("stat:")
        )
        return (severity + title_boost, workspace_targets, -index)

    def _trim_event_backlog(self) -> None:
        limit = self._event_retention_limit()
        if len(self._events) <= limit:
            return
        keep_indices = {0}
        ranked = sorted(
            range(1, len(self._events)),
            key=lambda index: self._event_backlog_score(self._events[index], index),
            reverse=True,
        )
        keep_indices.update(ranked[: max(0, limit - 1)])
        self._events = [event for index, event in enumerate(self._events) if index in keep_indices]

    def _trigger_event_motion(self, payload: FrontendEvent) -> None:
        intensity = _MOTION_INTENSITY.get(payload.severity, 0.42)
        pressure = self._motion_pressure_ratio()
        if self._window_width() < 920 and payload.severity in {"info", "success"}:
            intensity *= 0.9
        if len(self._events) >= 4 and payload.severity != "danger":
            intensity *= 0.9
        if pressure > 0:
            intensity *= max(0.72, 1.0 - pressure * 0.55)
        feed_intensity = max(0.24, intensity * 0.68)
        if self._overlay_or_pending_active():
            feed_intensity *= 0.88
        if len(self._events) >= 4:
            feed_intensity *= 0.86
        if pressure > 0:
            feed_intensity *= max(0.55, 1.0 - pressure * 1.05)
        self._motion_pulses.trigger(
            "feed",
            intensity=min(1.0, feed_intensity),
            decay=2.4 if payload.motion == "slide" else 1.8,
        )
        for target in payload.targets:
            self._trigger_motion_target(target, intensity=intensity, motion=payload.motion)

    def _trigger_motion_target(self, target: str, *, intensity: float, motion: str) -> None:
        decay = 2.8 if motion == "flash" else 2.2 if motion == "slide" else 1.8
        self._motion_pulses.trigger(target, intensity=intensity, decay=decay)
        if target.startswith("stat:"):
            self._motion_pulses.trigger(
                "panel:stats",
                intensity=max(0.22, intensity * 0.55),
                decay=decay,
            )
        elif target.startswith("product:"):
            self._motion_pulses.trigger(
                "panel:products",
                intensity=max(0.22, intensity * 0.6),
                decay=decay,
            )
        elif target.startswith("panel:"):
            self._motion_pulses.trigger(
                "footer",
                intensity=max(0.2, intensity * 0.45),
                decay=decay,
            )
        elif target.startswith("summary:"):
            self._motion_pulses.trigger(target, intensity=intensity, decay=decay)

    def _motion_level(self, *keys: str) -> float:
        if not keys:
            return 0.0
        return max(self._motion_pulses.get(key) for key in keys)

    def _entity_motion_strength(self, *keys: str) -> float:
        """Return idle gameplay-entity motion strength for the current motion mode."""

        if self.motion_mode is MotionMode.OFF:
            return 0.0
        pulse = self._motion_level(*keys) if keys else 0.0
        idle = 0.12 if self.motion_mode is MotionMode.REDUCED else 0.28
        scale = 0.45 if self.motion_mode is MotionMode.REDUCED else 1.0
        return min(1.0, (idle + pulse * 0.58) * scale)

    def _entity_motion_phase(self, *, offset: float = 0.0, speed: float = 1.0) -> float:
        """Return a deterministic wave phase for shape-based entity animation."""

        if self.motion_mode is MotionMode.OFF:
            return 0.0
        return self._motion_elapsed * speed + offset

    def _draw_entity_nodes(
        self,
        surface,
        rect,
        *,
        accent: tuple[int, int, int],
        strength: float,
        count: int = 3,
        offset: float = 0.0,
    ) -> None:
        if strength <= 0 or rect.width <= 20 or rect.height <= 10:
            return
        pygame = self.pygame
        phase = self._entity_motion_phase(offset=offset, speed=1.7)
        for index in range(count):
            ratio = (index + 1) / (count + 1)
            bob = sin(phase + index * 1.8) * 4 * strength
            node_x = rect.left + int(rect.width * ratio)
            node_y = rect.centery + int(bob)
            radius = max(2, int(3 + strength * 3))
            alpha = min(210, int(88 + strength * 110))
            pygame.draw.circle(surface, (*accent, alpha), (node_x, node_y), radius)
            pygame.draw.circle(
                surface, blend_color(accent, TEXT, 0.18), (node_x, node_y), radius, 1
            )

    def _draw_panel_entity_strip(
        self,
        surface,
        rect,
        *,
        panel_key: str,
        strength: float,
    ) -> None:
        if strength <= 0:
            return
        pygame = self.pygame
        accent = {
            "team": GOOD,
            "finance": WARN,
            "customers": INFO,
            "partnerships": INFO,
            "board": WARN,
            "pipeline": SELECTION,
            "report": INFO,
            "endgame": DANGER,
            "products": SELECTION,
            "stats": GOOD,
        }.get(panel_key, INFO)
        strip_rect = pygame.Rect(rect.left, rect.top, rect.width, min(32, rect.height))
        pygame.draw.rect(
            surface,
            blend_color((13, 22, 34), accent, strength * 0.18),
            strip_rect,
            border_radius=14,
        )
        pygame.draw.rect(
            surface,
            blend_color(BORDER, accent, strength * 0.3),
            strip_rect,
            width=1,
            border_radius=14,
        )
        self._draw_entity_nodes(
            surface,
            pygame.Rect(strip_rect.left + 8, strip_rect.top + 4, strip_rect.width - 16, 22),
            accent=accent,
            strength=strength,
            count=4 if panel_key in {"pipeline", "endgame"} else 3,
            offset=float(len(panel_key)),
        )
        draw_text_line(
            surface,
            self.fonts.small,
            panel_key.upper(),
            blend_color(MUTED, accent, 0.7),
            pygame.Rect(strip_rect.left + 10, strip_rect.top + 6, strip_rect.width - 20, 20),
        )

    def _actor_sprite_strength(self, *keys: str) -> float:
        if self.motion_mode is MotionMode.OFF:
            return 0.0
        base = 0.18 if self.motion_mode is MotionMode.REDUCED else 0.36
        scale = 0.62 if self.motion_mode is MotionMode.REDUCED else 1.0
        pulse_keys = keys or ("panel:products", "panel:stats", "footer", "overlay:outcome")
        pulse = self._motion_level(*pulse_keys)
        return min(1.0, (base + pulse * 0.28) * scale)

    def actor_timeline_active(self) -> bool:
        """Return whether run-scene actor timelines should be animated."""

        return self._actor_sprite_strength() > 0 and bool(self._run_actor_sprite_clips())

    def sprite_clips_active(self) -> bool:
        """Return whether run-scene shape sprite clips are visible."""

        return self.actor_timeline_active()

    def inspector_actor_active(self) -> bool:
        """Return whether inspector-specific actor clips are visible."""

        return (
            self.motion_mode is not MotionMode.OFF
            and self._inspector_panel_key is not None
            and self.inspector_panel is not None
        )

    def endgame_actor_active(self) -> bool:
        """Return whether endgame-board actor clips are visible."""

        return (
            self.motion_mode is not MotionMode.OFF
            and self._deep_panel_key == "endgame"
            and self.deep_panel is not None
        )

    def _run_actor_sprite_clips(self) -> tuple[ActorSpriteClip, ...]:
        selected_product = self.selected_product
        board_pressure = self.state.finance.board_pressure
        total_users = sum(product.user_count for product in self.state.products)
        founder_state = "risk" if self.state.company.cash_on_hand <= 1000 else "handoff"
        product_state = (
            "alert"
            if selected_product.bug_level >= 55 or selected_product.technical_debt >= 70
            else "success"
            if selected_product.market_fit >= 70 or selected_product.quality >= 78
            else "build"
        )
        team_state = "alert" if self.state.action_points_remaining <= 0 else "build"
        board_state = "risk" if board_pressure >= 70 else "handoff"
        customer_state = "success" if total_users >= 120 else "idle"
        if self._action_feedback_cues:
            cue = self._action_feedback_cues[0]
            targets = cue.targets
            if cue.outcome == "blocked":
                founder_state = "blocked"
                if cue.family in {"product", "pipeline"} or any(
                    target.startswith(("product:", "panel:products", "panel:pipeline"))
                    for target in targets
                ):
                    product_state = "blocked"
                if cue.family == "team" or "panel:team" in targets:
                    team_state = "blocked"
                if cue.family in {"customers", "partners"} or any(
                    target in {"panel:customers", "panel:partnerships", "stat:users"}
                    for target in targets
                ):
                    customer_state = "blocked"
                if cue.family in {"board", "endgame"} or any(
                    target in {"panel:board", "panel:endgame", "stat:board_pressure"}
                    for target in targets
                ):
                    board_state = "blocked"
            else:
                founder_state = "coaching"
                if cue.family in {"product", "pipeline"} or any(
                    target.startswith(("product:", "panel:pipeline")) for target in targets
                ):
                    product_state = "shipping"
                if cue.family == "team" or "panel:team" in targets:
                    team_state = "coaching"
                if cue.family == "finance" or any(
                    target in {"panel:finance", "stat:cash", "stat:runway"} for target in targets
                ):
                    founder_state = "negotiating"
                if cue.family in {"customers", "partners"} or any(
                    target in {"panel:customers", "panel:partnerships", "stat:users"}
                    for target in targets
                ):
                    customer_state = "negotiating"
                if cue.family in {"board", "endgame"} or any(
                    target in {"panel:board", "panel:endgame", "stat:board_pressure"}
                    for target in targets
                ):
                    board_state = "blocked" if board_pressure >= 70 else "negotiating"
                    founder_state = "firefighting" if board_pressure >= 70 else "negotiating"

        critical_targets = tuple(
            target
            for cue in self._impact_cues[:3]
            if cue.tone == "danger"
            or (
                cue.tone == "warning"
                and any(target.startswith("product:") for target in cue.targets)
            )
            for target in cue.targets
        )
        if critical_targets:
            founder_state = "firefighting"
            if any(
                target.startswith("product:") or target in {"panel:products", "panel:pipeline"}
                for target in critical_targets
            ):
                product_state = "firefighting"
            if any(target in {"panel:team", "stat:employees"} for target in critical_targets):
                team_state = "firefighting"
            if any(
                target in {"panel:customers", "panel:partnerships", "stat:users"}
                for target in critical_targets
            ):
                customer_state = "firefighting"
            if any(
                target in {"panel:board", "panel:endgame", "stat:board_pressure"}
                for target in critical_targets
            ):
                board_state = "firefighting"
        return (
            ActorSpriteClip(
                key="founder",
                label="Founder",
                role="Strategy",
                state=founder_state,
                accent=(
                    DANGER if founder_state in {"blocked", "firefighting", "risk"} else SELECTION
                ),
                lane="command",
                delay=0.0,
                phase_offset=0.2,
            ),
            ActorSpriteClip(
                key="team",
                label="Team",
                role="Build",
                state=team_state,
                accent=DANGER if team_state in {"alert", "blocked", "firefighting"} else GOOD,
                lane="ops",
                delay=0.06,
                phase_offset=1.1,
            ),
            ActorSpriteClip(
                key="customer",
                label="Customer",
                role="Adoption",
                state=customer_state,
                accent=(
                    DANGER
                    if customer_state in {"blocked", "firefighting"}
                    else WARN
                    if customer_state == "negotiating"
                    else INFO
                ),
                lane="market",
                delay=0.12,
                phase_offset=2.0,
            ),
            ActorSpriteClip(
                key="board",
                label="Board",
                role="Governance",
                state=board_state,
                accent=DANGER if board_state in {"risk", "blocked", "firefighting"} else WARN,
                lane="risk",
                delay=0.18,
                phase_offset=2.9,
            ),
            ActorSpriteClip(
                key="product",
                label=_short_actor_text(selected_product.name, 14),
                role="Product",
                state=product_state,
                accent=(
                    GOOD
                    if product_state == "success"
                    else DANGER
                    if product_state in {"alert", "blocked", "firefighting"}
                    else SELECTION
                    if product_state == "shipping"
                    else WARN
                ),
                lane="ship",
                delay=0.24,
                phase_offset=3.8,
            ),
        )

    def _draw_actor_sprite_layer(self, surface, anchor_rect) -> None:
        strength = self._actor_sprite_strength()
        if strength <= 0:
            return
        clips = self._run_actor_sprite_clips()
        if not clips:
            return
        pygame = self.pygame
        width, _height = surface.get_size()
        visible_count = 1 if width < 980 else 2
        visible_clips = clips[:visible_count]
        gap = 8
        clip_height = 42
        available = min(330, max(120, anchor_rect.width - 26))
        clip_width = min(142, max(98, int((available - gap * (visible_count - 1)) / visible_count)))
        total_width = clip_width * len(visible_clips) + gap * (len(visible_clips) - 1)
        left = max(anchor_rect.left + 12, anchor_rect.right - total_width - 12)
        top = min(anchor_rect.top + 52, anchor_rect.bottom - clip_height - 42)
        stage_rect = pygame.Rect(left - 8, top - 6, total_width + 16, clip_height + 12)
        stage = pygame.Surface((stage_rect.width, stage_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(
            stage,
            (*blend_color((8, 13, 22), SELECTION, 0.08), int(70 + strength * 46)),
            stage.get_rect(),
            border_radius=16,
        )
        surface.blit(stage, stage_rect.topleft)
        for index, clip in enumerate(visible_clips):
            clip_rect = pygame.Rect(left + index * (clip_width + gap), top, clip_width, clip_height)
            self._record_actor_sprite_bounds(clip, clip_rect)
            _draw_actor_sprite_clip(
                pygame=pygame,
                fonts=self.fonts,
                surface=surface,
                rect=clip_rect,
                clip=clip,
                elapsed=self._motion_elapsed,
                intensity=strength,
            )

    def _inspector_actor_sprite_clips(self) -> tuple[ActorSpriteClip, ...]:
        panel = self.inspector_panel
        section = self._selected_inspector_section()
        item = self._selected_inspector_item()
        panel_label = panel.title if panel is not None else "Inspector"
        section_label = section.title if section is not None else "Records"
        action_state = "idle"
        action_accent = INFO
        if item is not None:
            badge = self._inspector_item_action_badge(item)
            if badge is not None:
                label, action_accent = badge
                action_state = "success" if label == "READY" else "alert"
        return (
            ActorSpriteClip(
                key="inspector-analyst",
                label="Analyst",
                role=_short_actor_text(panel_label, 12),
                state="handoff",
                accent=SELECTION,
                lane="records",
                delay=0.0,
                phase_offset=0.7,
            ),
            ActorSpriteClip(
                key="inspector-router",
                label="Router",
                role=_short_actor_text(section_label, 12),
                state=action_state,
                accent=action_accent,
                lane="action",
                delay=0.08,
                phase_offset=1.6,
            ),
            ActorSpriteClip(
                key="inspector-hotspot",
                label="Hotspot",
                role="Risk",
                state="alert" if self._inspector_filter_mode_label() == "attention" else "build",
                accent=DANGER,
                lane="focus",
                delay=0.16,
                phase_offset=2.5,
            ),
        )

    def _endgame_actor_sprite_clips(self) -> tuple[ActorSpriteClip, ...]:
        board_state = "risk" if self.state.finance.board_pressure >= 70 else "handoff"
        cash_state = "risk" if self.state.company.cash_on_hand <= 1200 else "success"
        gate_state = "alert" if self.state.finance.board_pressure >= 70 else "build"
        return (
            ActorSpriteClip(
                key="endgame-cockpit",
                label="Cockpit",
                role="Exit",
                state=gate_state,
                accent=SELECTION,
                lane="path",
                delay=0.0,
                phase_offset=0.9,
            ),
            ActorSpriteClip(
                key="endgame-board",
                label="Board",
                role="Gates",
                state=board_state,
                accent=DANGER if board_state == "risk" else WARN,
                lane="pressure",
                delay=0.08,
                phase_offset=1.8,
            ),
            ActorSpriteClip(
                key="endgame-capital",
                label="Capital",
                role="Runway",
                state=cash_state,
                accent=GOOD if cash_state == "success" else DANGER,
                lane="cash",
                delay=0.16,
                phase_offset=2.7,
            ),
        )

    def _draw_overlay_actor_sprite_layer(
        self,
        surface,
        anchor_rect,
        *,
        clips: tuple[ActorSpriteClip, ...],
        strength: float,
        max_count: int = 3,
    ) -> None:
        if strength <= 0 or not clips:
            return
        pygame = self.pygame
        width, _height = surface.get_size()
        visible_count = min(max_count, 2 if width < 940 else 3, len(clips))
        visible_clips = clips[:visible_count]
        gap = 8
        clip_height = 42
        clip_width = 124 if width >= 1040 else 108
        total_width = clip_width * len(visible_clips) + gap * (len(visible_clips) - 1)
        left = max(anchor_rect.left + 12, anchor_rect.right - total_width - 10)
        # Leave a clear vertical lane between overlay actors and header summaries.
        top = max(anchor_rect.top - 44, 18)
        for index, clip in enumerate(visible_clips):
            clip_rect = pygame.Rect(left + index * (clip_width + gap), top, clip_width, clip_height)
            self._record_actor_sprite_bounds(clip, clip_rect)
            _draw_actor_sprite_clip(
                pygame=pygame,
                fonts=self.fonts,
                surface=surface,
                rect=clip_rect,
                clip=clip,
                elapsed=self._motion_elapsed,
                intensity=strength,
            )

    def _impact_cue_duration(self) -> float:
        if self.motion_mode is MotionMode.OFF:
            return 0.0
        return 0.72 if self.motion_mode is MotionMode.REDUCED else 1.1

    def _queue_impact_cues(self, previous_state: GameState, current_state: GameState) -> None:
        duration = self._impact_cue_duration()
        if duration <= 0:
            return
        cues = self._build_impact_cues(previous_state, current_state, duration=duration)
        if not cues:
            return
        for cue in reversed(cues):
            self._impact_cues.insert(0, cue)
            intensity = 0.5 if cue.tone in {"warning", "danger"} else 0.38
            motion = "flash" if cue.tone in {"warning", "danger"} else "pulse"
            for target in cue.targets[:3]:
                self._trigger_motion_target(target, intensity=intensity, motion=motion)
        self._impact_cues = self._impact_cues[:4]

    def _build_impact_cues(
        self,
        previous_state: GameState,
        current_state: GameState,
        *,
        duration: float,
    ) -> list[ImpactCue]:
        cues: list[ImpactCue] = []

        cash_delta = current_state.company.cash_on_hand - previous_state.company.cash_on_hand
        if cash_delta:
            cues.append(
                self._make_impact_cue(
                    label="Cash",
                    value_text=f"{'+' if cash_delta > 0 else ''}{format_money(cash_delta)}",
                    tone="success" if cash_delta > 0 else "warning",
                    targets=("stat:cash", "panel:finance"),
                    duration=duration,
                )
            )

        user_delta = self._total_users(current_state) - self._total_users(previous_state)
        if user_delta:
            cues.append(
                self._make_impact_cue(
                    label="Users",
                    value_text=self._format_signed_int(user_delta, suffix=" users"),
                    tone="success" if user_delta > 0 else "warning",
                    targets=("stat:users", "panel:customers"),
                    duration=duration,
                )
            )

        reputation_delta = current_state.company.reputation - previous_state.company.reputation
        if reputation_delta:
            cues.append(
                self._make_impact_cue(
                    label="Reputation",
                    value_text=self._format_signed_int(reputation_delta, suffix=" rep"),
                    tone="success" if reputation_delta > 0 else "warning",
                    targets=("stat:reputation", "panel:report"),
                    duration=duration,
                )
            )

        board_delta = current_state.finance.board_pressure - previous_state.finance.board_pressure
        if board_delta:
            cues.append(
                self._make_impact_cue(
                    label="Board",
                    value_text=self._format_signed_int(board_delta, suffix=" pressure"),
                    tone="danger" if board_delta > 0 else "success",
                    targets=("stat:board_pressure", "panel:board", "panel:endgame"),
                    duration=duration,
                )
            )

        previous_products = {product.id: product for product in previous_state.products}
        for product in current_state.products:
            previous_product = previous_products.get(product.id)
            if previous_product is None:
                continue
            cues.extend(self._build_product_impact_cues(previous_product, product, duration))

        return cues[:4]

    def _build_product_impact_cues(
        self,
        previous_product,
        current_product,
        duration: float,
    ) -> list[ImpactCue]:
        product_key = f"product:{current_product.id.hex}"
        product_name = current_product.name
        product_cues: list[ImpactCue] = []
        metric_specs = (
            (
                "Quality",
                current_product.quality - previous_product.quality,
                " quality",
                "success",
                "warning",
                f"{product_key}:quality",
            ),
            (
                "Bugs",
                current_product.bug_level - previous_product.bug_level,
                " bugs",
                "danger",
                "success",
                f"{product_key}:bugs",
            ),
            (
                "Fit",
                current_product.market_fit - previous_product.market_fit,
                " fit",
                "success",
                "warning",
                f"{product_key}:fit",
            ),
            (
                "Debt",
                current_product.technical_debt - previous_product.technical_debt,
                " debt",
                "warning",
                "success",
                f"{product_key}:debt",
            ),
            (
                "Features",
                current_product.feature_count - previous_product.feature_count,
                " features",
                "success",
                "warning",
                product_key,
            ),
            (
                "Product Users",
                current_product.user_count - previous_product.user_count,
                " users",
                "success",
                "warning",
                product_key,
            ),
        )
        for label, delta, suffix, positive_tone, negative_tone, target in metric_specs:
            if not delta:
                continue
            tone = positive_tone if delta > 0 else negative_tone
            product_cues.append(
                self._make_impact_cue(
                    label=f"{product_name} {label}",
                    value_text=self._format_signed_int(delta, suffix=suffix),
                    tone=tone,
                    targets=(product_key, target),
                    duration=duration,
                )
            )
        return product_cues[:2]

    def _make_impact_cue(
        self,
        *,
        label: str,
        value_text: str,
        tone: str,
        targets: tuple[str, ...],
        duration: float,
    ) -> ImpactCue:
        accent = tone_color(tone)
        return ImpactCue(
            label=label,
            value_text=value_text,
            tone=tone,
            accent=accent,
            targets=targets,
            time_left=duration,
            duration=duration,
        )

    def _pending_choice_duration(self) -> float:
        if self.motion_mode is MotionMode.OFF:
            return 0.0
        return 0.72 if self.motion_mode is MotionMode.REDUCED else 1.05

    def _queue_pending_choice_cue(self, label: str, detail: str) -> None:
        duration = self._pending_choice_duration()
        if duration <= 0:
            return
        self._pending_choice_cues.insert(
            0,
            PendingChoiceCue(
                label=label,
                detail=detail,
                accent=WARN,
                time_left=duration,
                duration=duration,
            ),
        )
        self._pending_choice_cues = self._pending_choice_cues[:2]
        self._motion_pulses.trigger("overlay:pending_choice", intensity=0.76, decay=1.6)
        self._motion_pulses.trigger("feed", intensity=0.42, decay=1.6)

    @staticmethod
    def _pending_option_tone(label: str, description: str) -> str:
        text = f"{label} {description}".lower()
        if any(
            token in text
            for token in (
                "risk",
                "debt",
                "cost",
                "pressure",
                "delay",
                "stretch",
                "accept",
                "cut",
            )
        ):
            return "warning"
        if any(
            token in text
            for token in (
                "stabilize",
                "protect",
                "recover",
                "quality",
                "trust",
                "success",
                "safe",
            )
        ):
            return "success"
        return "info"

    @staticmethod
    def _pending_option_badge(tone: str) -> str:
        if tone == "warning":
            return "RISK"
        if tone == "success":
            return "SAFE"
        return "INFO"

    def _draw_pending_option_preview(
        self,
        surface,
        rect,
        *,
        tone: str,
        strength: float,
        index: int,
    ) -> None:
        if self.motion_mode is MotionMode.OFF or strength <= 0:
            return
        pygame = self.pygame
        accent = tone_color(tone)
        preview_rect = pygame.Rect(rect.right - 102, rect.top + 10, 82, rect.height - 20)
        pygame.draw.rect(
            surface,
            blend_color((13, 22, 34), accent, min(0.2, strength * 0.18)),
            preview_rect,
            border_radius=12,
        )
        pygame.draw.rect(
            surface,
            blend_color(BORDER, accent, min(0.5, strength * 0.42)),
            preview_rect,
            width=1,
            border_radius=12,
        )
        phase = self._entity_motion_phase(offset=index * 0.9, speed=1.8)
        y_mid = preview_rect.centery
        points: list[tuple[int, int]] = []
        for step in range(4):
            ratio = step / 3
            x = preview_rect.left + 10 + int((preview_rect.width - 20) * ratio)
            direction = -1 if tone == "success" else 1 if tone == "warning" else 0
            y = y_mid + int((ratio - 0.5) * 14 * direction)
            y += int(sin(phase + step * 0.7) * 3 * strength)
            points.append((x, y))
        if len(points) >= 2:
            pygame.draw.lines(surface, blend_color(accent, TEXT, 0.12), False, points, 2)
        for step, point in enumerate(points):
            radius = 3 + int(strength * 2)
            pygame.draw.circle(surface, accent, point, radius)
            if step == len(points) - 1:
                pygame.draw.circle(surface, blend_color(TEXT, accent, 0.35), point, radius + 2, 1)
        badge = self.fonts.small.render(self._pending_option_badge(tone), True, accent)
        surface.blit(badge, (preview_rect.left + 8, preview_rect.bottom - 17))

    @staticmethod
    def _format_signed_int(value: int, *, suffix: str = "") -> str:
        return f"{'+' if value > 0 else ''}{value}{suffix}"

    @staticmethod
    def _total_users(state: GameState) -> int:
        return sum(product.user_count for product in state.products)

    def _action_feedback_duration(self) -> float:
        if self.motion_mode is MotionMode.OFF:
            return 0.0
        return 0.56 if self.motion_mode is MotionMode.REDUCED else 0.9

    def _action_feedback_profile(
        self,
        command: str,
    ) -> tuple[str, str, tuple[int, int, int], tuple[str, ...]]:
        if command.startswith("inspect_"):
            panel_key = command.removeprefix("inspect_")
            return (
                f"{self._panel_display_name(panel_key)} Inspector",
                "inspect",
                SELECTION,
                (f"panel:{panel_key}", "overlay:inspector"),
            )
        if command == TurnAction.END_TURN.value:
            return (
                "Turn Resolve",
                "turn",
                DANGER,
                ("summary:timeline", "stat:cash", "stat:runway"),
            )
        if command in {
            TurnAction.IMPROVE_QUALITY.value,
            TurnAction.ADD_FEATURE.value,
            TurnAction.MARKET_PRODUCT.value,
            TurnAction.REDUCE_TECHNICAL_DEBT.value,
            TurnAction.CREATE_PRODUCT.value,
        }:
            return (
                "Product Work",
                "product",
                SELECTION if command != TurnAction.REDUCE_TECHNICAL_DEBT.value else WARN,
                ("panel:products", f"product:{self.selected_product.id.hex}"),
            )

        panel_key = self._workspace_panel_key_for_command(command)
        if command == TurnAction.SET_COMPANY_STRATEGY.value:
            return ("Strategy Choice", "strategy", INFO, ("panel:report", "panel:team"))
        if command == TurnAction.SET_ROADMAP.value:
            return (
                "Roadmap Choice",
                "pipeline",
                SELECTION,
                ("panel:pipeline", "panel:products"),
            )
        if command == TurnAction.SET_BUDGET_STANCE.value:
            return (
                "Budget Choice",
                "finance",
                WARN,
                ("panel:finance", "stat:cash"),
            )
        if command == TurnAction.SET_SUPPORT_LANE_FOCUS.value:
            return (
                "Support Choice",
                "customers",
                INFO,
                ("panel:customers", "stat:users"),
            )
        if command in _FINANCE_PANEL_COMMANDS or panel_key == "finance":
            return (
                "Capital Move",
                "finance",
                WARN,
                ("panel:finance", "stat:cash", "stat:runway"),
            )
        if command in _TEAM_PANEL_COMMANDS or panel_key == "team":
            return ("Team Move", "team", GOOD, ("panel:team",))
        if command in _PIPELINE_PANEL_COMMANDS or panel_key == "pipeline":
            return (
                "Pipeline Move",
                "pipeline",
                SELECTION,
                ("panel:pipeline", "panel:products"),
            )
        if command in _BOARD_PANEL_COMMANDS or panel_key == "board":
            return (
                "Board Impact",
                "board",
                DANGER,
                ("panel:board", "panel:endgame", "stat:board_pressure"),
            )
        if command in _CUSTOMER_PANEL_COMMANDS or panel_key == "customers":
            return ("Market Signal", "customers", INFO, ("panel:customers", "stat:users"))
        if command in _PARTNERSHIP_PANEL_COMMANDS or panel_key == "partnerships":
            return (
                "Partner Signal",
                "partners",
                INFO,
                ("panel:partnerships", "stat:users"),
            )
        if (
            panel_key == "endgame"
            or command.startswith("set_endgame_")
            or command.startswith("set_exit_")
            or command.startswith("set_terminal_")
        ):
            return (
                "Endgame Gate",
                "endgame",
                DANGER,
                ("panel:endgame", "stat:board_pressure"),
            )
        if panel_key is not None:
            return (
                f"{self._panel_display_name(panel_key)} Move",
                "workspace",
                INFO,
                (f"panel:{panel_key}",),
            )
        return ("Command Cue", "workspace", INFO, ("feed",))

    def _queue_action_feedback(self, command: str) -> None:
        duration = self._action_feedback_duration()
        if duration <= 0:
            return
        label, family, accent, targets = self._action_feedback_profile(command)
        self._action_feedback_cues.insert(
            0,
            ActionFeedbackCue(
                command=command,
                label=label,
                family=family,
                accent=accent,
                targets=targets,
                time_left=duration,
                duration=duration,
            ),
        )
        self._action_feedback_cues = self._action_feedback_cues[:3]

    def _queue_blocked_action_feedback(self, command: str, reason: str) -> None:
        duration = self._action_feedback_duration()
        if duration <= 0:
            return
        label, family, _accent, targets = self._action_feedback_profile(command)
        blocked_targets = ("feed", *targets)
        self._action_feedback_cues.insert(
            0,
            ActionFeedbackCue(
                command=command,
                label=f"Blocked: {label}",
                family=family,
                accent=DANGER,
                targets=blocked_targets,
                time_left=duration,
                duration=duration,
                outcome="blocked",
                detail=reason,
            ),
        )
        self._action_feedback_cues = self._action_feedback_cues[:3]
        for target in blocked_targets[:3]:
            self._trigger_motion_target(target, intensity=0.64, motion="flash")

    def _late_game_choreography_duration(self) -> float:
        if self.motion_mode is MotionMode.OFF:
            return 0.0
        return 0.78 if self.motion_mode is MotionMode.REDUCED else 1.22

    def _late_game_choreography_profile(
        self,
        command: str,
    ) -> tuple[str, str, str, tuple[int, int, int], tuple[str, ...]] | None:
        normalized = command.lower()
        path_specific_profiles = {
            TurnAction.SET_PATH_CONTROL_MATRIX.value: (
                "IPO Controls",
                "ipo",
                "Lock operating controls, reference proof, and public-market readiness.",
                INFO,
                ("panel:endgame", "panel:customers", "stat:reputation"),
            ),
            TurnAction.SET_PATH_RESILIENCE_GRID.value: (
                "M&A Resilience",
                "m&a",
                "Stabilize partner exposure and resilience before buyer diligence tightens.",
                SELECTION,
                ("panel:endgame", "panel:partnerships", "stat:users"),
            ),
            TurnAction.SET_PATH_CASH_WATERFALL.value: (
                "Independence Cash",
                "cash",
                "Route reserve, runway, and renewal pressure into the independent path.",
                WARN,
                ("panel:endgame", "panel:finance", "stat:cash"),
            ),
            TurnAction.SET_BALANCE_SHEET_RECOVERY_MESH.value: (
                "Reset Recovery",
                "reset",
                "Bind reset controls to board pressure, cash repair, and recovery timing.",
                DANGER,
                ("panel:endgame", "panel:board", "stat:board_pressure"),
            ),
            TurnAction.SET_BOARD_RESET_CONTINGENCY_BUFFER.value: (
                "Reset Buffer",
                "reset",
                "Raise reserves before board reset risk blocks the recovery lane.",
                DANGER,
                ("panel:endgame", "panel:finance", "stat:board_pressure"),
            ),
        }
        if command in path_specific_profiles:
            return path_specific_profiles[command]
        if normalized.startswith(("set_terminal_", "set_exit_", "set_endgame_")):
            return (
                "Terminal Gate",
                "endgame",
                "Route pressure through exit, continuity, and solvency lanes.",
                DANGER,
                ("panel:endgame", "stat:board_pressure", "stat:runway"),
            )
        if command in {
            TurnAction.SET_PATH_CASH_WATERFALL.value,
            TurnAction.SET_PATH_CONTROL_MATRIX.value,
            TurnAction.SET_PATH_RESILIENCE_GRID.value,
            TurnAction.SET_BALANCE_SHEET_RECOVERY_MESH.value,
            TurnAction.SET_BOARD_RESET_CONTINGENCY_BUFFER.value,
        }:
            return (
                "Path Repair",
                "endgame",
                "Tie the active path gap back to capital, board, and recovery controls.",
                WARN,
                ("panel:endgame", "panel:finance", "stat:board_pressure"),
            )
        if (
            command in _BOARD_PANEL_COMMANDS
            or "board_reset" in normalized
            or normalized.startswith("start_board_")
            or normalized.startswith("execute_board_")
        ):
            return (
                "Board Recovery",
                "board",
                "Pull governance heat into the board lane before reset pressure compounds.",
                DANGER,
                ("panel:board", "panel:endgame", "stat:board_pressure"),
            )
        if command in _FINANCE_PANEL_COMMANDS or any(
            token in normalized
            for token in (
                "capital",
                "cash",
                "debt",
                "liquidity",
                "reserve",
                "solvency",
                "financing",
            )
        ):
            return (
                "Capital Control",
                "finance",
                "Stage runway, cash, and debt signals before the next gate decision.",
                WARN,
                ("panel:finance", "stat:cash", "stat:runway"),
            )
        if command in _PIPELINE_PANEL_COMMANDS or any(
            token in normalized for token in ("roadmap", "release", "pipeline")
        ):
            return (
                "Path Build",
                "pipeline",
                "Connect delivery work back to product readiness and path momentum.",
                SELECTION,
                ("panel:pipeline", "panel:products"),
            )
        return None

    def _queue_late_game_choreography(self, command: str) -> None:
        duration = self._late_game_choreography_duration()
        if duration <= 0:
            return
        profile = self._late_game_choreography_profile(command)
        if profile is None:
            return
        label, family, detail, accent, targets = profile
        self._late_game_choreography_cues.insert(
            0,
            LateGameChoreographyCue(
                command=command,
                label=label,
                detail=detail,
                family=family,
                accent=accent,
                targets=targets,
                time_left=duration,
                duration=duration,
            ),
        )
        self._late_game_choreography_cues = self._late_game_choreography_cues[:2]
        for target in targets[:3]:
            self._trigger_motion_target(target, intensity=0.58, motion="slide")
        self._motion_pulses.trigger("late_game:choreography", intensity=0.72, decay=1.8)

    def _draw_overlay_exit_cues(self, surface) -> None:
        if not self._overlay_exit_cues or self.motion_mode is MotionMode.OFF:
            return
        pygame = self.pygame
        width, _height = surface.get_size()
        for index, cue in enumerate(self._overlay_exit_cues[:3]):
            if cue.duration <= 0:
                continue
            progress = 1.0 - max(0.0, min(1.0, cue.time_left / cue.duration))
            eased = 1.0 - (1.0 - progress) * (1.0 - progress)
            alpha = int((1.0 - progress) * 76)
            if alpha <= 0:
                continue
            y = 104 + index * 34
            sweep_width = max(150, int(width * 0.24))
            sweep_x = int(eased * (width + sweep_width)) - sweep_width
            sweep_rect = pygame.Rect(sweep_x, y, sweep_width, 8)
            pygame.draw.rect(surface, (*cue.accent, alpha), sweep_rect, border_radius=4)
            badge = self.fonts.small.render(
                cue.label.upper(),
                True,
                blend_color(MUTED, cue.accent, 0.8),
            )
            badge_rect = pygame.Rect(24, y - 9, badge.get_width() + 18, 24)
            pygame.draw.rect(
                surface,
                (*blend_color((13, 22, 34), cue.accent, 0.18), min(210, alpha + 130)),
                badge_rect,
                border_radius=12,
            )
            pygame.draw.rect(
                surface,
                (*blend_color(BORDER, cue.accent, 0.42), min(230, alpha + 120)),
                badge_rect,
                width=1,
                border_radius=12,
            )
            surface.blit(badge, (badge_rect.left + 9, badge_rect.top + 6))

    def _draw_pending_choice_cues(self, surface) -> None:
        if not self._pending_choice_cues or self.motion_mode is MotionMode.OFF:
            return
        pygame = self.pygame
        width, height = surface.get_size()
        card_width = min(460, width - 48)
        left = int((width - card_width) / 2)
        top = max(24, int(height * 0.18))
        for index, cue in enumerate(self._pending_choice_cues[:2]):
            if cue.duration <= 0:
                continue
            age = max(0.0, cue.duration - cue.time_left)
            enter = min(1.0, age / 0.18)
            ttl_ratio = max(0.0, min(1.0, cue.time_left / cue.duration))
            intensity = ttl_ratio * (0.58 if self.motion_mode is MotionMode.REDUCED else 1.0)
            rect = pygame.Rect(
                left,
                top + index * 58 - int((1.0 - enter) * 18),
                card_width,
                48,
            )
            fill = blend_color((15, 23, 34), cue.accent, 0.16 + intensity * 0.12)
            panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(panel, (*fill, 226), panel.get_rect(), border_radius=16)
            pygame.draw.rect(
                panel,
                (*blend_color(BORDER, cue.accent, 0.5), 235),
                panel.get_rect(),
                width=1,
                border_radius=16,
            )
            surface.blit(panel, rect.topleft)
            self._draw_entity_nodes(
                surface,
                pygame.Rect(rect.left + 12, rect.top + 10, 54, 24),
                accent=cue.accent,
                strength=min(1.0, 0.32 + intensity * 0.68),
                count=2,
                offset=index + len(cue.label),
            )
            text_rect = pygame.Rect(rect.left + 76, rect.top + 6, rect.width - 88, 20)
            draw_text_line(
                surface,
                self.fonts.small,
                f"CHOICE: {cue.label}",
                blend_color(TEXT, cue.accent, 0.18),
                text_rect,
                valign="top",
            )
            draw_text_line(
                surface,
                self.fonts.small,
                cue.detail,
                MUTED,
                pygame.Rect(rect.left + 76, rect.top + 24, rect.width - 88, 18),
                valign="top",
            )
            progress_rect = pygame.Rect(rect.left + 76, rect.bottom - 6, rect.width - 92, 4)
            pygame.draw.rect(surface, blend_color(BORDER, cue.accent, 0.22), progress_rect)
            pygame.draw.rect(
                surface,
                cue.accent,
                pygame.Rect(
                    progress_rect.left,
                    progress_rect.top,
                    int(progress_rect.width * ttl_ratio),
                    progress_rect.height,
                ),
            )

    def _draw_impact_cues(self, surface) -> None:
        if not self._impact_cues or self.motion_mode is MotionMode.OFF:
            return
        pygame = self.pygame
        width, height = surface.get_size()
        compact = width < 920
        card_width = min(300, max(190, width - 40))
        card_height = 42 if compact else 48
        gap = 8
        left = 24
        top = 112 if height < 680 else 146
        if self._text_input is not None or self._context_picker is not None:
            top = 24
        for index, cue in enumerate(self._impact_cues[:4]):
            if cue.duration <= 0:
                continue
            age = max(0.0, cue.duration - cue.time_left)
            enter_ratio = min(1.0, age / 0.2)
            ttl_ratio = max(0.0, min(1.0, cue.time_left / cue.duration))
            intensity = ttl_ratio * (0.55 if self.motion_mode is MotionMode.REDUCED else 1.0)
            slide_x = int((1.0 - enter_ratio) * -24)
            wave = sin(self._entity_motion_phase(offset=index * 0.9, speed=2.8)) * 3 * intensity
            rect = pygame.Rect(
                left + slide_x,
                int(top + index * (card_height + gap) + wave),
                card_width,
                card_height,
            )
            panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            fill = blend_color((13, 22, 34), cue.accent, 0.18 + intensity * 0.12)
            pygame.draw.rect(panel, (*fill, 224), panel.get_rect(), border_radius=16)
            pygame.draw.rect(
                panel,
                (*blend_color(BORDER, cue.accent, 0.46), 230),
                panel.get_rect(),
                width=1,
                border_radius=16,
            )
            surface.blit(panel, rect.topleft)
            node_rect = pygame.Rect(rect.left + 10, rect.top + 8, 44, rect.height - 16)
            self._draw_entity_nodes(
                surface,
                node_rect,
                accent=cue.accent,
                strength=min(1.0, 0.3 + intensity * 0.65),
                count=2,
                offset=index + len(cue.label),
            )
            target_text = " / ".join(
                target.removeprefix("panel:")
                .removeprefix("stat:")
                .removeprefix("product:")
                .split(":")[-1]
                for target in cue.targets[:2]
            )
            value_width = min(96, max(54, rect.width // 3))
            draw_text_line(
                surface,
                self.fonts.small,
                cue.label,
                TEXT,
                pygame.Rect(rect.left + 58, rect.top + 6, rect.width - value_width - 78, 18),
                valign="top",
            )
            draw_text_line(
                surface,
                self.fonts.heading,
                cue.value_text,
                cue.accent,
                pygame.Rect(rect.right - value_width - 14, rect.top + 4, value_width, 22),
                align="right",
                valign="top",
            )
            draw_text_line(
                surface,
                self.fonts.small,
                target_text,
                blend_color(MUTED, cue.accent, 0.55),
                pygame.Rect(rect.left + 58, rect.top + card_height - 21, rect.width - 72, 16),
                valign="top",
            )
            progress_rect = pygame.Rect(rect.left + 58, rect.bottom - 7, rect.width - 72, 4)
            pygame.draw.rect(surface, blend_color(BORDER, cue.accent, 0.18), progress_rect)
            pygame.draw.rect(
                surface,
                cue.accent,
                pygame.Rect(
                    progress_rect.left,
                    progress_rect.top,
                    int(progress_rect.width * ttl_ratio),
                    progress_rect.height,
                ),
            )

    def _draw_action_feedback_cues(self, surface) -> None:
        if not self._action_feedback_cues or self.motion_mode is MotionMode.OFF:
            return
        pygame = self.pygame
        width, height = surface.get_size()
        compact = width < 920
        card_width = min(330, max(180, width - 40))
        card_height = 40 if compact else 46
        gap = 8
        left = max(20, width - card_width - 24)
        top = 112 if height < 680 else 146
        transition_badge_rect = self._scene_transition_badge_rect(surface)
        modal_overlay_active = self._text_input is not None or self._context_picker is not None
        tall_overlay_top_lane = (
            self._deep_panel_key is not None
            or self._inspector_panel_key is not None
            or self._help_overlay_visible
        )
        max_visible = 3
        if tall_overlay_top_lane:
            # The left side of this lane belongs to Pause/Back/Help, while the far
            # right may hold the transition badge. Keep one cue between both.
            lane_left = 360
            lane_right = (
                transition_badge_rect.left - 42 if transition_badge_rect is not None else width - 26
            )
            card_width = min(330, max(140, lane_right - lane_left))
            left = max(lane_left, lane_right - card_width)
            top = 12
            max_visible = 1
        elif modal_overlay_active:
            top = 62 if transition_badge_rect is not None else 24
            max_visible = 1
            if transition_badge_rect is not None:
                left = min(left, max(20, transition_badge_rect.left - card_width - 24))
        for index, cue in enumerate(self._action_feedback_cues[:max_visible]):
            if cue.duration <= 0:
                continue
            age = max(0.0, cue.duration - cue.time_left)
            enter_ratio = min(1.0, age / 0.18)
            ttl_ratio = max(0.0, min(1.0, cue.time_left / cue.duration))
            intensity = ttl_ratio * (0.62 if self.motion_mode is MotionMode.REDUCED else 1.0)
            blocked = cue.outcome == "blocked"
            slide_x = int((1.0 - enter_ratio) * 26)
            if blocked:
                slide_x += int(sin(self._entity_motion_phase(offset=index + 0.35, speed=7.2)) * 5)
            wave = sin(self._entity_motion_phase(offset=index * 0.8, speed=2.4)) * 3 * intensity
            rect = pygame.Rect(
                left + slide_x,
                top + index * (card_height + gap) - int(wave),
                card_width,
                card_height,
            )
            if tall_overlay_top_lane:
                self._record_layout_separation(
                    "action-feedback-vs-nav",
                    rect,
                    pygame.Rect(0, 0, 360, 54),
                )
                self._record_layout_separation(
                    "action-feedback-vs-overlay",
                    rect,
                    pygame.Rect(0, 60, width, max(0, height - 60)),
                )
            if transition_badge_rect is not None:
                self._record_layout_separation(
                    "action-feedback-vs-transition-badge",
                    rect,
                    transition_badge_rect.inflate(10, 10),
                )
            layer = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            layer_rect = layer.get_rect()
            fill = blend_color(
                (8, 13, 22),
                cue.accent,
                (0.2 if blocked else 0.14) + intensity * 0.08,
            )
            border = DANGER if blocked else blend_color(cue.accent, TEXT, 0.12)
            alpha = int(min(210, 112 + ttl_ratio * 100))
            pygame.draw.rect(layer, (*fill, alpha), layer_rect, border_radius=14)
            pygame.draw.rect(
                layer,
                (*border, int(86 + intensity * 110)),
                layer_rect,
                width=2 if blocked or intensity >= 0.6 else 1,
                border_radius=14,
            )
            pygame.draw.rect(
                layer,
                (*cue.accent, int(88 + intensity * 116)),
                pygame.Rect(0, 0, 7 if blocked else 5, rect.height),
                border_radius=3,
            )
            self._draw_entity_nodes(
                layer,
                pygame.Rect(94, rect.height - 16, max(24, rect.width - 118), 10),
                accent=cue.accent,
                strength=(0.48 if blocked else 0.36) * intensity,
                count=2 if blocked else 3,
                offset=float(index) * 1.3,
            )
            if blocked:
                notch_width = max(20, int(rect.width * 0.18 * ttl_ratio))
                pygame.draw.rect(
                    layer,
                    (*DANGER, int(80 + intensity * 80)),
                    pygame.Rect(rect.right - rect.left - notch_width - 10, 7, notch_width, 4),
                    border_radius=2,
                )
            surface.blit(layer, rect.topleft)

            family_text = "BLOCKED" if blocked else cue.family.upper()
            if blocked and cue.detail:
                target_text = cue.detail
            else:
                target_text = " / ".join(
                    target.removeprefix("panel:")
                    .removeprefix("stat:")
                    .removeprefix("summary:")
                    .removeprefix("overlay:")
                    for target in cue.targets[:2]
                )
            family_width = min(86, max(62, rect.width // 4))
            draw_text_line(
                surface,
                self.fonts.small,
                cue.label,
                TEXT,
                pygame.Rect(rect.left + 14, rect.top + 6, rect.width - family_width - 36, 18),
                valign="top",
            )
            draw_text_line(
                surface,
                self.fonts.small,
                family_text,
                blend_color(MUTED, cue.accent, 0.82),
                pygame.Rect(rect.right - family_width - 14, rect.top + 6, family_width, 18),
                align="right",
                valign="top",
            )
            draw_text_line(
                surface,
                self.fonts.small,
                target_text,
                blend_color(MUTED, DANGER, 0.55) if blocked else MUTED,
                pygame.Rect(rect.left + 14, rect.top + 23, rect.width - 28, 16),
                valign="top",
            )
            progress_rect = pygame.Rect(rect.left + 14, rect.bottom - 7, rect.width - 28, 4)
            pygame.draw.rect(surface, blend_color(BORDER, cue.accent, 0.2), progress_rect)
            pygame.draw.rect(
                surface,
                cue.accent,
                pygame.Rect(
                    progress_rect.left,
                    progress_rect.top,
                    int(progress_rect.width * ttl_ratio),
                    progress_rect.height,
                ),
            )

    def _draw_late_game_choreography_cues(self, surface) -> None:
        if not self._late_game_choreography_cues or self.motion_mode is MotionMode.OFF:
            return
        pygame = self.pygame
        width, height = surface.get_size()
        card_width = min(440, max(240, width - 48))
        card_height = 56
        left = max(24, (width - card_width) // 2)
        top = 76 if height < 680 else 100
        max_visible = 2
        modal_overlay_active = self._context_picker is not None or self._text_input is not None
        if modal_overlay_active:
            top = max(72, height - card_height - 54)
            max_visible = 1
        for index, cue in enumerate(self._late_game_choreography_cues[:max_visible]):
            if cue.duration <= 0:
                continue
            age = max(0.0, cue.duration - cue.time_left)
            enter_ratio = min(1.0, age / 0.2)
            ttl_ratio = max(0.0, min(1.0, cue.time_left / cue.duration))
            intensity = ttl_ratio * (0.56 if self.motion_mode is MotionMode.REDUCED else 1.0)
            lift = 0 if modal_overlay_active else int((1.0 - enter_ratio) * 22)
            wave = (
                0
                if modal_overlay_active
                else sin(self._entity_motion_phase(offset=index * 1.2, speed=2.0)) * 3 * intensity
            )
            rect = pygame.Rect(
                left,
                int(top + index * (card_height + 8) - lift + wave),
                card_width,
                card_height,
            )
            if modal_overlay_active:
                self._record_layout_separation(
                    "late-game-choreography-vs-modal-controls",
                    rect,
                    pygame.Rect(0, height - 54, width, 54),
                )
            layer = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            layer_rect = layer.get_rect()
            fill = blend_color((8, 13, 22), cue.accent, 0.18 + intensity * 0.12)
            pygame.draw.rect(layer, (*fill, 226), layer_rect, border_radius=18)
            pygame.draw.rect(
                layer,
                (*blend_color(BORDER, cue.accent, 0.55), 235),
                layer_rect,
                width=2 if intensity >= 0.55 else 1,
                border_radius=18,
            )
            rail_rect = pygame.Rect(14, layer_rect.bottom - 9, layer_rect.width - 28, 4)
            pygame.draw.rect(layer, (*blend_color(BORDER, cue.accent, 0.2), 190), rail_rect)
            pygame.draw.rect(
                layer,
                (*cue.accent, int(120 + intensity * 95)),
                pygame.Rect(
                    rail_rect.left,
                    rail_rect.top,
                    int(rail_rect.width * ttl_ratio),
                    rail_rect.height,
                ),
            )
            self._draw_entity_nodes(
                layer,
                pygame.Rect(16, 15, 70, 24),
                accent=cue.accent,
                strength=min(1.0, 0.32 + intensity * 0.68),
                count=3,
                offset=float(index) + len(cue.family),
            )
            surface.blit(layer, rect.topleft)
            label_surface = self.fonts.small.render(cue.label.upper(), True, TEXT)
            family_surface = self.fonts.small.render(
                cue.family.upper(),
                True,
                blend_color(MUTED, cue.accent, 0.78),
            )
            detail_surface = self.fonts.small.render(
                self._compact_button_detail(cue.detail, max_length=56),
                True,
                MUTED,
            )
            target_text = " -> ".join(
                target.removeprefix("panel:").removeprefix("stat:").removeprefix("summary:")
                for target in cue.targets[:3]
            )
            target_surface = self.fonts.small.render(
                self._compact_button_detail(target_text, max_length=42),
                True,
                blend_color(TEXT, cue.accent, 0.2),
            )
            surface.blit(label_surface, (rect.left + 96, rect.top + 9))
            surface.blit(
                family_surface, (rect.right - family_surface.get_width() - 14, rect.top + 9)
            )
            surface.blit(detail_surface, (rect.left + 96, rect.top + 27))
            surface.blit(target_surface, (rect.left + 14, rect.bottom - 22))

    def _overlay_fill(self, overlay_key: str) -> tuple[int, int, int, int]:
        pulse = self._overlay_motion_level(overlay_key)
        enter = self._overlay_enter_progress(overlay_key)
        alpha = min(224, 180 + int(pulse * 36))
        alpha = int(alpha * (0.55 + enter * 0.45))
        return (8, 10, 14, alpha)

    def _handle_mouse_click(self, position: tuple[int, int]) -> None:
        for target in reversed(self._click_targets):
            if target.rect.collidepoint(position):
                if self._pause_overlay_visible and not target.kind.startswith("pause_"):
                    return
                self._dispatch_click_target(target)
                return

    def _dispatch_click_target(self, target: ClickTarget) -> None:
        if target.kind == "pause_toggle":
            self._set_pause_overlay_visible(True)
            return
        if target.kind == "run_back":
            self._handle_back_navigation()
            return
        if target.kind == "open_help":
            self._set_help_overlay_visible(True)
            return
        if target.kind == "focus_toggle":
            self._toggle_focus_mode()
            return
        if target.kind == "pause_resume":
            self._set_pause_overlay_visible(False)
            return
        if target.kind == "pause_save":
            self._save_current_run()
            return
        if target.kind == "pause_settings":
            self._set_pause_settings_visible(True)
            return
        if target.kind == "pause_settings_cycle":
            self._cycle_frontend_preference(target.payload)
            return
        if target.kind == "pause_settings_reset":
            self._reset_frontend_preferences()
            return
        if target.kind == "pause_settings_back":
            self._set_pause_settings_visible(False)
            return
        if target.kind == "pause_menu":
            self._return_to_menu_or_quit()
            return
        if target.kind == "pause_quit":
            self.should_exit = True
            self.exit_reason = "quit"
            return
        if target.kind == "select_product":
            self._set_selected_product(target.payload)
            self._refresh_view_model()
            return
        if target.kind == "command":
            reason = self._command_disabled_reason(target.payload)
            if reason is not None:
                self._push_action_blocked_event(target.payload, reason)
                return
            self._run_command(target.payload)
            return
        if target.kind == "coach":
            self._run_primary_coach_action()
            return
        if target.kind == "save":
            self._save_current_run()
            return
        if target.kind == "panel":
            self._set_deep_panel(target.payload)
            return
        if target.kind == "open_panel_inspector":
            self._open_inspector(target.payload)
            return
        if target.kind == "text_command":
            reason = self._command_disabled_reason(target.payload)
            if reason is not None:
                self._push_action_blocked_event(target.payload, reason)
                return
            if target.payload == TurnAction.CREATE_PRODUCT.value:
                self._open_create_product_modal()
            return
        if target.kind == "picker_option":
            self._apply_picker_index(int(target.payload))
            return
        if target.kind == "close_picker":
            self._set_context_picker(None)
            return
        if target.kind == "panel_action":
            reason = self._command_disabled_reason(target.payload)
            if reason is not None:
                self._push_action_blocked_event(target.payload, reason)
                return
            if self._deep_panel_key == "endgame":
                self._run_endgame_cockpit_command(target.payload)
                return
            self._run_command(target.payload)
            return
        if target.kind == "endgame_actions_toggle":
            self._toggle_endgame_actions()
            return
        if target.kind == "close_panel":
            self._set_deep_panel(None)
            return
        if target.kind == "close_inspector":
            self._close_inspector()
            return
        if target.kind == "inspector_section":
            self._select_inspector_section(target.payload)
            return
        if target.kind == "inspector_item":
            self._select_inspector_item(target.payload)
            return
        if target.kind == "inspector_prev_page":
            self._change_inspector_page(-1)
            return
        if target.kind == "inspector_next_page":
            self._change_inspector_page(1)
            return
        if target.kind == "inspector_cycle_sort":
            self._cycle_inspector_sort_mode()
            return
        if target.kind == "inspector_cycle_filter":
            self._cycle_inspector_filter_mode()
            return
        if target.kind == "inspector_focus_actionable":
            self._focus_inspector_actionable()
            return
        if target.kind == "inspector_focus_hotspot":
            self._focus_inspector_hotspot()
            return
        if target.kind == "inspector_item_action":
            self._run_selected_inspector_action(int(target.payload))
            return
        if target.kind == "submit_text":
            self._submit_text_modal()
            return
        if target.kind == "cancel_text":
            self._set_text_input(None)
            return
        if target.kind == "pending_option":
            self._resolve_pending_event_choice(int(target.payload))
            return
        if target.kind == "open_review":
            self._open_review_scene()
            return
        if target.kind == "close_outcome":
            self.should_exit = True
            self.exit_reason = "quit"
            return
        if target.kind == "close_help":
            self._set_help_overlay_visible(False)
            return

    def _handle_back_navigation(self) -> None:
        if self._help_overlay_visible:
            self._set_help_overlay_visible(False)
            return
        if self._pause_overlay_visible:
            self._set_pause_overlay_visible(False)
            return
        if self._text_input is not None:
            self._set_text_input(None)
            return
        if self._context_picker is not None:
            self._set_context_picker(None)
            return
        if self._inspector_panel_key is not None:
            self._close_inspector()
            return
        if self._deep_panel_key is not None:
            self._set_deep_panel(None)
            return
        self._set_pause_overlay_visible(True)

    def _return_to_menu_or_quit(self) -> None:
        if self._return_scene_factory is None:
            self.should_exit = True
            self.exit_reason = "quit"
            return
        if self._dirty:
            self._persist_current_run()
        self._next_scene = self._return_scene_factory()

    def _command_disabled_reason(self, command: str) -> str | None:
        if self.state.company.game_over or self.state.victory_achieved:
            return "This run is already complete."
        return explain_command_unavailable(
            self.state,
            command=command,
            selected_product_id=self.selected_product.id.hex,
        )

    def _push_action_blocked_event(self, command: str, reason: str) -> None:
        self._queue_blocked_action_feedback(command, reason)
        self.push_event(
            FrontendEvent(
                title="Action Not Ready",
                detail=f"`{command}` is blocked right now: {reason}",
                severity="warning",
                ttl=5.5,
            )
        )

    def _handle_pending_event_key(self, event) -> None:
        if event.key == self.pygame.K_s:
            self._save_current_run()
            return
        self._resolve_pending_event_choice(self._digit_index(event))

    def _handle_picker_key(self, event) -> None:
        if event.key in (self.pygame.K_RETURN, self.pygame.K_KP_ENTER):
            self._apply_picker_index(0)
            return
        self._apply_picker_index(self._digit_index(event))

    def _handle_text_input_key(self, event) -> None:
        modal = self._text_input
        if modal is None:
            return
        if event.key in (self.pygame.K_RETURN, self.pygame.K_KP_ENTER):
            self._submit_text_modal()
            return
        if event.key == self.pygame.K_BACKSPACE:
            modal.text = modal.text[:-1]
            return
        if event.key == self.pygame.K_TAB:
            return
        if event.unicode and event.unicode.isprintable() and len(modal.text) < 40:
            modal.text += event.unicode

    def _resolve_pending_event_choice(self, option_index: int | None) -> None:
        if option_index is None or self.state.pending_event is None:
            return
        if option_index >= len(self.state.pending_event.options):
            return
        option = self.state.pending_event.options[option_index]
        previous_state = self.state.model_copy(deep=True)
        resolution = self._resolve_pending_event(option.id)
        self._queue_pending_choice_cue(option.label, resolution)
        self._queue_impact_cues(previous_state, self.state)
        self.push_events(
            build_action_events(
                previous_state,
                self.state,
                action_label=option.label,
                message=resolution,
            )
        )
        self._dirty = True
        self._refresh_view_model()

    def _apply_picker_index(self, option_index: int | None) -> None:
        if option_index is None or self._context_picker is None:
            return
        if option_index >= len(self._context_picker.options):
            return
        request = self._context_picker.options[option_index].request
        self._set_context_picker(None)
        self._apply_action_request(request)

    def _resolve_pending_event(self, option_id: str) -> str:
        from nexus_tech.simulation.events import resolve_pending_event

        outcome = resolve_pending_event(self.state, option_id)
        self.state = outcome.state
        return outcome.message

    def _open_create_product_modal(self) -> None:
        default_name = f"New Venture {len(self.state.products) + 1}"
        self._trigger_command_choreography(TurnAction.CREATE_PRODUCT.value)
        self._queue_action_feedback(TurnAction.CREATE_PRODUCT.value)
        self._set_text_input(
            TextInputModalState(
                title="Create Product",
                description="Type the new product name and press Enter to create it.",
                severity="info",
                submit_title="Enter Create",
                submit_detail="Launch the new product into the portfolio.",
                text=default_name,
                placeholder="Product name",
                on_submit=self._submit_create_product_name,
            )
        )

    def _submit_text_modal(self) -> None:
        modal = self._text_input
        if modal is None:
            return
        self._set_text_input(None)
        modal.on_submit(modal.text.strip())

    def _submit_create_product_name(self, value: str) -> None:
        product_name = value or f"New Venture {len(self.state.products) + 1}"
        request = ActionRequest(
            action=TurnAction.CREATE_PRODUCT,
            context=ActionContext(new_product_name=product_name),
            label=f"{TurnAction.CREATE_PRODUCT.value}:{product_name}",
        )
        self._apply_action_request(request)

    def _cycle_product(self, direction: int) -> None:
        products = self._product_choices()
        self._product_index = (self._product_index + direction) % len(products)
        self._refresh_view_model()

    def _product_choices(self) -> list:
        return [
            product for product in self.state.products if product.is_active
        ] or self.state.products

    def _set_selected_product(self, selected_product_id: str | None) -> None:
        products = self._product_choices()
        if not products:
            self._product_index = 0
            return
        if selected_product_id is None:
            self._product_index = min(self._product_index, len(products) - 1)
            return
        for index, product in enumerate(products):
            if product.id.hex == selected_product_id:
                self._product_index = index
                return
        self._product_index = 0

    def _intent_for_key(self, key: int):
        pygame = self.pygame
        mapping = {
            pygame.K_c: FrontendIntent.PRIMARY_COACH,
            pygame.K_q: FrontendIntent.IMPROVE_QUALITY,
            pygame.K_f: FrontendIntent.ADD_FEATURE,
            pygame.K_m: FrontendIntent.MARKET_PRODUCT,
            pygame.K_d: FrontendIntent.REDUCE_TECHNICAL_DEBT,
            pygame.K_h: FrontendIntent.HIRE_EMPLOYEE,
            pygame.K_a: FrontendIntent.ASSIGN_EMPLOYEE,
            pygame.K_l: FrontendIntent.TAKE_LOAN,
            pygame.K_g: FrontendIntent.RAISE_ANGEL,
            pygame.K_o: FrontendIntent.CREATE_PARTNERSHIP,
            pygame.K_y: FrontendIntent.OPEN_STRATEGY,
            pygame.K_r: FrontendIntent.OPEN_ROADMAP,
            pygame.K_b: FrontendIntent.OPEN_BUDGET,
            pygame.K_u: FrontendIntent.OPEN_SUPPORT,
            pygame.K_SPACE: FrontendIntent.END_TURN,
        }
        return mapping.get(key)

    def _handle_intent(self, intent: FrontendIntent) -> None:
        if self.state.company.game_over or self.state.victory_achieved:
            return
        if intent is FrontendIntent.PRIMARY_COACH:
            self._run_primary_coach_action()
            return
        command_map = {
            FrontendIntent.IMPROVE_QUALITY: TurnAction.IMPROVE_QUALITY.value,
            FrontendIntent.ADD_FEATURE: TurnAction.ADD_FEATURE.value,
            FrontendIntent.MARKET_PRODUCT: TurnAction.MARKET_PRODUCT.value,
            FrontendIntent.REDUCE_TECHNICAL_DEBT: TurnAction.REDUCE_TECHNICAL_DEBT.value,
            FrontendIntent.HIRE_EMPLOYEE: TurnAction.HIRE_EMPLOYEE.value,
            FrontendIntent.ASSIGN_EMPLOYEE: TurnAction.ASSIGN_EMPLOYEE.value,
            FrontendIntent.TAKE_LOAN: TurnAction.TAKE_LOAN.value,
            FrontendIntent.RAISE_ANGEL: TurnAction.RAISE_ANGEL.value,
            FrontendIntent.CREATE_PARTNERSHIP: TurnAction.CREATE_PARTNERSHIP.value,
            FrontendIntent.OPEN_STRATEGY: TurnAction.SET_COMPANY_STRATEGY.value,
            FrontendIntent.OPEN_ROADMAP: TurnAction.SET_ROADMAP.value,
            FrontendIntent.OPEN_BUDGET: TurnAction.SET_BUDGET_STANCE.value,
            FrontendIntent.OPEN_SUPPORT: TurnAction.SET_SUPPORT_LANE_FOCUS.value,
            FrontendIntent.END_TURN: TurnAction.END_TURN.value,
        }
        command = command_map.get(intent)
        if command is not None:
            self._run_command(command)

    def _run_primary_coach_action(self) -> None:
        command = self._view_model.coach_lines[0].command if self._view_model.coach_lines else ""
        if not command:
            return
        self._run_command(command)

    def _trigger_command_choreography(self, command: str) -> None:
        panel_key = _workspace_panel_key_for_command(command)
        if panel_key is not None:
            self._motion_pulses.trigger(f"panel:{panel_key}", intensity=0.65, decay=1.8)
            self._motion_pulses.trigger("footer", intensity=0.32, decay=1.6)
        if panel_key == "finance":
            self._motion_pulses.trigger("stat:cash", intensity=0.52, decay=1.7)
            self._motion_pulses.trigger("stat:runway", intensity=0.44, decay=1.7)
        elif panel_key == "customers":
            self._motion_pulses.trigger("stat:users", intensity=0.5, decay=1.7)
        elif panel_key == "partnerships":
            self._motion_pulses.trigger("stat:users", intensity=0.42, decay=1.7)
        elif panel_key == "board":
            self._motion_pulses.trigger("stat:board_pressure", intensity=0.58, decay=1.8)
            self._motion_pulses.trigger("panel:endgame", intensity=0.4, decay=1.8)
        elif panel_key == "report":
            self._motion_pulses.trigger("panel:endgame", intensity=0.34, decay=1.6)
        if command in {
            TurnAction.IMPROVE_QUALITY.value,
            TurnAction.ADD_FEATURE.value,
            TurnAction.MARKET_PRODUCT.value,
            TurnAction.REDUCE_TECHNICAL_DEBT.value,
            TurnAction.CREATE_PRODUCT.value,
        }:
            product_key = f"product:{self.selected_product.id.hex}"
            self._motion_pulses.trigger(product_key, intensity=0.75, decay=1.9)
            self._motion_pulses.trigger("panel:products", intensity=0.65, decay=1.8)
        if command == TurnAction.HIRE_EMPLOYEE.value:
            self._motion_pulses.trigger("panel:team", intensity=0.7, decay=1.8)
        if command in {
            TurnAction.PLAN_RELEASE.value,
            TurnAction.WORK_RELEASE.value,
            TurnAction.START_ROADMAP_PROJECT.value,
            TurnAction.WORK_ROADMAP_PROJECT.value,
            TurnAction.CREATE_SALES_DEAL.value,
            TurnAction.ADVANCE_SALES_DEAL.value,
        }:
            self._motion_pulses.trigger("panel:pipeline", intensity=0.68, decay=1.8)
            self._motion_pulses.trigger("panel:products", intensity=0.4, decay=1.8)
        if command in {
            TurnAction.EXECUTE_BOARD_RESPONSE.value,
            TurnAction.START_BOARD_RECOVERY_PLAN.value,
            TurnAction.EXECUTE_RESTRUCTURE_PLAN.value,
        }:
            self._motion_pulses.trigger("panel:board", intensity=0.75, decay=1.9)
            self._motion_pulses.trigger("stat:board_pressure", intensity=0.62, decay=1.9)
            self._motion_pulses.trigger("panel:endgame", intensity=0.45, decay=1.9)
        if command == TurnAction.END_TURN.value:
            self._motion_pulses.trigger("summary:timeline", intensity=0.6, decay=1.4)
            self._motion_pulses.trigger("stat:cash", intensity=0.45, decay=1.4)

    def _run_command(self, command: str) -> None:
        self._execute_command(command)

    def _run_endgame_cockpit_command(self, command: str) -> None:
        self._execute_command(command, handoff_source_panel_key="endgame")

    def _execute_command(
        self,
        command: str,
        *,
        handoff_source_panel_key: str | None = None,
    ) -> None:
        if command == TurnAction.END_TURN.value:
            self._attempt_end_turn()
            return
        self._focus_workspace_for_command(command)
        inspector_key = self._inspector_key_for_command(command)
        if inspector_key is not None:
            self._queue_late_game_choreography(command)
            self._set_deep_panel(inspector_key)
            self._open_inspector(inspector_key)
            self._push_workspace_handoff_event(
                command,
                source_panel_key=handoff_source_panel_key,
                target_panel_key=inspector_key,
                overlay_key="inspector",
            )
            return
        self._trigger_command_choreography(command)
        reason = self._command_disabled_reason(command)
        if reason is not None:
            self._push_action_blocked_event(command, reason)
            return
        if command == TurnAction.CREATE_PRODUCT.value:
            self._open_create_product_modal()
            self._push_workspace_handoff_event(
                command,
                source_panel_key=handoff_source_panel_key,
                target_panel_key="pipeline",
                overlay_key="text",
            )
            return
        request = build_command_request(
            self.state,
            command=command,
            selected_product_id=self.selected_product.id.hex,
        )
        if isinstance(request, ActionRequest):
            self._apply_action_request(request)
            self._push_workspace_handoff_event(
                command,
                source_panel_key=handoff_source_panel_key,
                target_panel_key=self._workspace_panel_key_for_command(command),
            )
            return
        if isinstance(request, ContextPicker):
            self._queue_late_game_choreography(command)
            self._set_context_picker(request)
            self._queue_action_feedback(command)
            self._push_workspace_handoff_event(
                command,
                source_panel_key=handoff_source_panel_key,
                target_panel_key=self._workspace_panel_key_for_command(command),
                overlay_key="picker",
            )
            return
        self.push_event(
            FrontendEvent(
                title="Action Needs More 2D Coverage",
                detail=f"`{command}` is valid, but the 2D shell still needs a picker for it.",
                severity="warning",
                ttl=5.5,
            )
        )

    def _apply_action_request(self, request: ActionRequest) -> None:
        if request.action is TurnAction.END_TURN:
            self._resolve_end_turn()
            return
        self._trigger_command_choreography(request.action.value)
        previous_state = self.state.model_copy(deep=True)
        try:
            outcome = apply_action(self.state, request.action, context=request.context)
        except ValueError as error:
            self._queue_blocked_action_feedback(request.action.value, str(error))
            self.push_event(
                FrontendEvent(
                    title="Action Rejected",
                    detail=str(error),
                    severity="warning",
                    ttl=5.5,
                )
            )
            return

        self._queue_late_game_choreography(request.action.value)
        self._queue_action_feedback(request.action.value)
        self.state = outcome.state
        self._queue_impact_cues(previous_state, self.state)
        self._dirty = True
        self.push_events(
            build_action_events(
                previous_state,
                self.state,
                action_label=request.action.value,
                message=outcome.message,
            )
        )
        self._refresh_view_model()

    def _attempt_end_turn(self) -> None:
        if self.state.pending_event is not None:
            self.push_event(
                FrontendEvent(
                    title="Resolve Pending Event",
                    detail="Pick one event option before ending the turn.",
                    severity="warning",
                )
            )
            return

        preview = build_end_turn_preview(self.state)
        if preview.blocked:
            self.push_event(
                FrontendEvent(
                    title="Turn Preview Blocked",
                    detail=preview.note,
                    severity="warning",
                    ttl=5.0,
                )
            )
            return

        if preview.requires_confirmation:
            confirmation = ActionRequest(
                action=TurnAction.END_TURN,
                context=ActionContext(),
                label=TurnAction.END_TURN.value,
            )
            self._set_context_picker(
                ContextPicker(
                    title="Confirm Turn Resolve",
                    description=preview.confirmation_reason,
                    severity="danger" if preview.warning_level == "critical" else "warning",
                    options=(
                        PickerOption(
                            "1",
                            "Confirm End Turn",
                            f"Resolve now. Forecast: {preview.projected_outcome}.",
                            confirmation,
                        ),
                    ),
                )
            )
            self._queue_action_feedback(TurnAction.END_TURN.value)
            return

        self._resolve_end_turn()

    def _resolve_end_turn(self) -> None:
        self._trigger_command_choreography(TurnAction.END_TURN.value)
        self._queue_action_feedback(TurnAction.END_TURN.value)
        previous_state = self.state.model_copy(deep=True)
        try:
            outcome = apply_action(self.state, TurnAction.END_TURN, context=ActionContext())
        except ValueError as error:
            self.push_event(
                FrontendEvent(
                    title="End Turn Rejected",
                    detail=str(error),
                    severity="warning",
                    ttl=5.5,
                )
            )
            return

        self.state = outcome.state
        resolution = resolve_turn(self.state, self.rng)
        self.state = resolution.state
        self._dirty = True
        self._next_scene = TurnSummaryScene(
            pygame=self.pygame,
            fonts=self.fonts,
            state=self.state,
            rng=self.rng,
            slot_name=self.slot_name,
            save_callback=self._save_callback,
            previous_state=previous_state,
            resolution=resolution,
            selected_product_id=self.selected_product.id.hex,
            dirty=True,
            motion_mode=self.motion_mode,
            preferences=self._current_frontend_preferences(),
            preference_callback=self._preference_callback,
            preference_provider=self._preference_provider,
            entry_transition="run_to_summary",
            return_scene_factory=self._return_scene_factory,
        )

    def _save_current_run(self) -> None:
        terminal = self.state.company.game_over or self.state.victory_achieved
        if terminal and self._terminal_archive_saved:
            return
        self._persist_current_run()
        if terminal:
            self._terminal_archive_saved = True
        self.push_event(
            FrontendEvent(
                title="Run Archived" if terminal else "Game Saved",
                detail=(
                    "Ending recorded for progression. Return to the menu and open Progress."
                    if terminal
                    else f"Saved the 2D run back to slot `{self.slot_name}`."
                ),
                severity="success",
            )
        )

    def _open_review_scene(self) -> None:
        self._next_scene = ReviewScene(
            pygame=self.pygame,
            fonts=self.fonts,
            state=self.state,
            rng=self.rng,
            slot_name=self.slot_name,
            save_callback=self._save_callback,
            view_model=build_run_review_view_model(self.state),
            accent=GOOD if self.state.victory_achieved else DANGER,
            primary_title="Back to Menu" if self._return_scene_factory is not None else "Esc Close",
            primary_detail=(
                "Return to the title menu."
                if self._return_scene_factory is not None
                else "Leave the 2D shell."
            ),
            return_scene_factory=self._return_scene_factory,
            allow_save=not self._terminal_archive_saved,
            dirty=self._dirty,
            motion_mode=self.motion_mode,
            preferences=self._current_frontend_preferences(),
            preference_callback=self._preference_callback,
            preference_provider=self._preference_provider,
            entry_transition="run_to_review",
        )

    def _select_inspector_section(self, payload: str) -> None:
        panel = self.inspector_panel
        if panel is None:
            return
        for index, section in enumerate(panel.inspectors):
            if section.key == payload:
                self._inspector_section_index = index
                self._inspector_page = 0
                self._inspector_item_index = 0
                self._trigger_inspector_motion("section", intensity=0.62)
                self._sync_inspector_selection()
                return

    def _select_inspector_item(self, payload: str) -> None:
        try:
            absolute_index = int(payload)
        except ValueError:
            return
        section_items = self._filtered_sorted_inspector_items()
        if not section_items:
            return
        absolute_index = max(0, min(absolute_index, len(section_items) - 1))
        items_per_page = self._inspector_items_per_page()
        self._inspector_page = absolute_index // items_per_page
        self._inspector_item_index = absolute_index % items_per_page
        self._trigger_inspector_motion("item", intensity=0.5)
        self._sync_inspector_selection()

    def _change_inspector_section(self, direction: int) -> None:
        panel = self.inspector_panel
        if panel is None or not panel.inspectors:
            return
        self._inspector_section_index = (self._inspector_section_index + direction) % len(
            panel.inspectors
        )
        self._inspector_page = 0
        self._inspector_item_index = 0
        self._trigger_inspector_motion("section", intensity=0.58)
        self._sync_inspector_selection()

    def _change_inspector_page(self, direction: int) -> None:
        total_pages = self._inspector_total_pages()
        if total_pages <= 1:
            return
        self._inspector_page = (self._inspector_page + direction) % total_pages
        self._inspector_item_index = 0
        self._trigger_inspector_motion("page", intensity=0.54)
        self._sync_inspector_selection()

    def _change_inspector_item(self, direction: int) -> None:
        page_items = self._current_inspector_page_items()
        if not page_items:
            return
        self._inspector_item_index = (self._inspector_item_index + direction) % len(page_items)
        self._trigger_inspector_motion("item", intensity=0.46)
        self._remember_inspector_state()

    def _cycle_inspector_sort_mode(self) -> None:
        self._inspector_sort_mode_index = (self._inspector_sort_mode_index + 1) % len(
            _INSPECTOR_SORT_MODES
        )
        self._inspector_page = 0
        self._inspector_item_index = 0
        self._trigger_inspector_motion("sort", intensity=0.58)
        self._sync_inspector_selection()

    def _cycle_inspector_filter_mode(self) -> None:
        self._inspector_filter_mode_index = (self._inspector_filter_mode_index + 1) % len(
            _INSPECTOR_FILTER_MODES
        )
        self._inspector_page = 0
        self._inspector_item_index = 0
        self._trigger_inspector_motion("filter", intensity=0.58)
        self._sync_inspector_selection()

    def _sync_inspector_selection(self) -> None:
        panel = self.inspector_panel
        if panel is None or not panel.inspectors:
            self._inspector_panel_key = None
            self._inspector_section_index = 0
            self._inspector_page = 0
            self._inspector_item_index = 0
            return
        self._inspector_section_index = max(
            0,
            min(self._inspector_section_index, len(panel.inspectors) - 1),
        )
        if not self._filtered_sorted_inspector_items():
            self._inspector_page = 0
            self._inspector_item_index = 0
            return
        total_pages = self._inspector_total_pages()
        self._inspector_page = max(0, min(self._inspector_page, total_pages - 1))
        page_items = self._current_inspector_page_items()
        if not page_items:
            self._inspector_page = 0
            page_items = self._current_inspector_page_items()
        self._inspector_item_index = max(0, min(self._inspector_item_index, len(page_items) - 1))
        self._remember_inspector_state()

    def _remember_inspector_state(self) -> None:
        panel = self.inspector_panel
        section = self._selected_inspector_section()
        if panel is None or section is None:
            return
        self._inspector_memory[panel.key] = InspectorMemoryState(
            section_key=section.key,
            page=self._inspector_page,
            item_index=self._inspector_item_index,
            sort_mode_index=self._inspector_sort_mode_index,
            filter_mode_index=self._inspector_filter_mode_index,
        )

    def _set_inspector_sort_mode(self, mode: str) -> None:
        if mode not in _INSPECTOR_SORT_MODES:
            return
        self._inspector_sort_mode_index = _INSPECTOR_SORT_MODES.index(mode)
        self._inspector_page = 0
        self._inspector_item_index = 0
        self._sync_inspector_selection()

    def _set_inspector_filter_mode(self, mode: str) -> None:
        if mode not in _INSPECTOR_FILTER_MODES:
            return
        self._inspector_filter_mode_index = _INSPECTOR_FILTER_MODES.index(mode)
        self._inspector_page = 0
        self._inspector_item_index = 0
        self._sync_inspector_selection()

    def _focus_inspector_actionable(self) -> None:
        self._trigger_inspector_motion("actionable", intensity=0.64)
        self._set_inspector_filter_mode("actionable")

    def _focus_inspector_hotspot(self) -> None:
        self._trigger_inspector_motion("hotspot", intensity=0.68)
        self._set_inspector_sort_mode("risk")
        self._set_inspector_filter_mode("attention")

    def _inspector_items_per_page(self) -> int:
        surface = self.pygame.display.get_surface()
        if surface is None:
            return 4
        width, height = surface.get_size()
        if width < 900:
            return 2
        if height < 700:
            return 3
        return 4

    def _current_inspector_page_start(self) -> int:
        return self._inspector_page * self._inspector_items_per_page()

    def _current_inspector_page_items(self):
        section_items = self._filtered_sorted_inspector_items()
        start = self._current_inspector_page_start()
        end = start + self._inspector_items_per_page()
        return section_items[start:end]

    def _inspector_total_pages(self) -> int:
        section_items = self._filtered_sorted_inspector_items()
        if not section_items:
            return 1
        return max(
            1,
            (len(section_items) + self._inspector_items_per_page() - 1)
            // self._inspector_items_per_page(),
        )

    def _filtered_sorted_inspector_items(self):
        section = self._selected_inspector_section()
        if section is None:
            return ()
        items = list(section.items)
        filter_mode = _INSPECTOR_FILTER_MODES[self._inspector_filter_mode_index]
        if filter_mode == "actionable":
            items = [item for item in items if item.actions]
        elif filter_mode == "attention":
            items = [
                item
                for item in items
                if item.tone in {"danger", "warning"} or self._item_has_attention_signal(item)
            ]
        sort_mode = _INSPECTOR_SORT_MODES[self._inspector_sort_mode_index]
        if sort_mode != "default":
            items = sorted(
                items,
                key=lambda item: self._inspector_sort_key(item, sort_mode),
                reverse=True,
            )
        return tuple(items)

    def _inspector_sort_key(self, item, sort_mode: str) -> tuple[int, int, int, int]:
        tone_score = _TONE_PRIORITY.get(item.tone, 0)
        risk_score = self._extract_named_number(item, "risk")
        value_score = self._extract_money_score(item)
        stalled_score = self._extract_progress_gap(item)
        if sort_mode == "risk":
            return (risk_score, tone_score, stalled_score, value_score)
        if sort_mode == "value":
            return (value_score, risk_score, tone_score, stalled_score)
        if sort_mode == "stalled":
            return (stalled_score, risk_score, tone_score, value_score)
        return (tone_score, risk_score, value_score, stalled_score)

    def _item_has_attention_signal(self, item) -> bool:
        text = " ".join(item.detail_lines).lower()
        return any(
            marker in text
            for marker in ("risk ", "hotspot", "strained", "paused", "warning", "overdue")
        )

    def _extract_named_number(self, item, label: str) -> int:
        text = " ".join(item.detail_lines).lower()
        match = re.search(rf"{re.escape(label.lower())}\\s+(\\d+)", text)
        if match:
            return int(match.group(1))
        return 0

    def _extract_money_score(self, item) -> int:
        text = " ".join(item.detail_lines)
        money_matches = re.findall(r"\\$([0-9,]+(?:\\.\\d+)?)", text)
        if not money_matches:
            return 0
        normalized = money_matches[0].replace(",", "")
        return int(float(normalized))

    def _extract_progress_gap(self, item) -> int:
        text = " ".join(item.detail_lines).lower()
        match = re.search(r"progress\\s+(\\d+)/(\\d+)", text)
        if match:
            current, total = int(match.group(1)), int(match.group(2))
            return max(0, total - current)
        return 0

    def _run_selected_inspector_primary_action(self) -> None:
        self._run_selected_inspector_action(0)

    def _run_selected_inspector_action(self, action_index: int) -> None:
        item = self._selected_inspector_item()
        section = self._selected_inspector_section()
        panel = self.inspector_panel
        if item is None or section is None or panel is None or action_index >= len(item.actions):
            return
        action = item.actions[action_index]
        if panel.key == "endgame":
            self._run_endgame_cockpit_command(action.command)
            return
        inspector_key = self._inspector_key_for_command(action.command)
        if inspector_key is not None:
            self._set_deep_panel(inspector_key)
            self._open_inspector(inspector_key)
            return
        self._trigger_command_choreography(action.command)
        reason = self._inspector_item_action_reason(action.command, item.payload)
        if reason is not None:
            self._push_action_blocked_event(action.command, reason)
            return
        request = build_inspector_action_request(
            self.state,
            panel_key=panel.key,
            section_key=section.key,
            command=action.command,
            payload=item.payload,
            selected_product_id=self.selected_product.id.hex,
        )
        if isinstance(request, ActionRequest):
            self._apply_action_request(request)
            return
        if isinstance(request, ContextPicker):
            self._set_context_picker(request)
            self._queue_action_feedback(action.command)
            return
        self.push_event(
            FrontendEvent(
                title="Inspector Action Missing",
                detail=(
                    f"{get_action_label(action.command)} still needs a 2D request path "
                    "for this item."
                ),
                severity="warning",
                ttl=5.5,
            )
        )

    def _inspector_item_action_reason(self, command: str, payload: str) -> str | None:
        if self.state.company.game_over or self.state.victory_achieved:
            return "This run is already complete."
        section = self._selected_inspector_section()
        panel = self.inspector_panel
        if section is None or panel is None:
            return "No inspector selection is active."
        return explain_inspector_action_unavailable(
            self.state,
            panel_key=panel.key,
            section_key=section.key,
            command=command,
            payload=payload,
            selected_product_id=self.selected_product.id.hex,
        )

    def _refresh_view_model(self) -> None:
        self._view_model = build_game_view_model(
            self.state,
            selected_product_id=self.selected_product.id.hex,
        )
        if self._deep_panel_key is not None and self.deep_panel is None:
            self._deep_panel_key = None
        if self._inspector_panel_key is not None and self.inspector_panel is None:
            self._inspector_panel_key = None
        self._sync_inspector_selection()
        self._sync_tweens()

    def _sync_tweens(self) -> None:
        targets = {gauge.key: gauge.ratio for gauge in self._view_model.stats}
        for product in self._view_model.products:
            targets[f"{product.id}:quality"] = product.quality_ratio
            targets[f"{product.id}:bugs"] = product.bug_ratio
            targets[f"{product.id}:fit"] = product.fit_ratio
            targets[f"{product.id}:debt"] = product.debt_ratio
        self._tweens.sync_targets(targets)

    def _draw_header(self, surface, rect) -> None:
        pygame = self.pygame
        width, _height = surface.get_size()
        inner = draw_panel(surface, pygame, rect, title="Run Header", accent=INFO)
        compact = rect.height < 130 or inner.width < 760
        actor_reserve = 156 if width < 980 and self.motion_mode is not MotionMode.OFF else 0
        copy_width = max(240, inner.width - actor_reserve)
        draw_text_line(
            surface,
            self.fonts.title,
            f"{self._view_model.company_name} | {self._view_model.turn_label}",
            TEXT,
            pygame.Rect(inner.left, inner.top - 32, copy_width, 30),
            valign="top",
        )
        meta_text = (
            f"{self._view_model.campaign_chapter_label} | {self._view_model.scenario_title} | "
            f"score {self._view_model.score_label} | market {self._view_model.market_label}"
        )
        draw_wrapped_text(
            surface,
            self.fonts.body,
            meta_text,
            MUTED,
            pygame.Rect(inner.left, inner.top, copy_width, 20),
            line_height=18,
            max_lines=1,
        )
        draw_wrapped_text(
            surface,
            self.fonts.small,
            self._view_model.header_note,
            TEXT,
            pygame.Rect(inner.left, inner.top + 22, copy_width, 18),
            line_height=15,
            max_lines=1,
        )
        header_guide_rect = pygame.Rect(inner.left, inner.top + 42, copy_width, 28)
        if (
            compact
            and width < 980
            and self._draw_first_turn_header_strip(surface, header_guide_rect)
        ):
            return
        if not compact:
            draw_wrapped_text(
                surface,
                self.fonts.small,
                (
                    f"Lens: {self._view_model.campaign_lens} | "
                    f"Difficulty: {self._view_model.difficulty_summary}"
                ),
                MUTED,
                pygame.Rect(inner.left, inner.top + 42, copy_width, 18),
                line_height=15,
                max_lines=1,
            )
        chip_width = int((inner.width - 24) / 3)
        chip_height = 24 if compact else 28
        top = min(
            inner.top + (58 if compact else 66),
            rect.bottom - chip_height - 10,
        )
        if top <= inner.top + 42:
            return
        left = inner.left
        for index, chip in enumerate(self._view_model.snapshot_chips):
            if index and index % 3 == 0:
                top += chip_height + 8
                left = inner.left
            if top + chip_height > rect.bottom - 8:
                break
            chip_rect = pygame.Rect(left, top, chip_width, chip_height)
            self._draw_snapshot_chip(surface, chip_rect, chip.label, chip.value_text, chip.tone)
            left += chip_width + 12

    def _draw_first_turn_header_strip(self, surface, rect) -> bool:
        if not self._first_turn_guide_active() or rect.width < 320 or rect.height < 24:
            return False
        pygame = self.pygame
        opening = build_guided_opening(self.state)
        shimmer = (
            0.0
            if self.motion_mode is MotionMode.OFF
            else 0.5 + 0.5 * sin(self._motion_elapsed * 2.4)
        )
        pygame.draw.rect(
            surface,
            blend_color((18, 29, 44), INFO, 0.14 + shimmer * 0.04),
            rect,
            border_radius=12,
        )
        pygame.draw.rect(
            surface,
            blend_color(BORDER, SELECTION, 0.34 + shimmer * 0.16),
            rect,
            width=1,
            border_radius=12,
        )
        self._first_turn_guide_visible = True
        self._click_targets.append(ClickTarget("coach", "", rect))
        line = (
            f"Opening {self._view_model.run_journey.step_label} | "
            f"C Coach: {get_action_label(opening.current_command)} | "
            f"AP {max(0, self.state.action_points_remaining)} | "
            "P Pause | S Save | Space End"
        )
        draw_text_line(
            surface,
            self.fonts.small,
            line,
            TEXT,
            pygame.Rect(rect.left + 10, rect.top + 5, rect.width - 20, rect.height - 10),
        )
        return True

    def _draw_left_column(self, surface, rect) -> None:
        pygame = self.pygame
        stats_height = int(rect.height * 0.5)
        stats_rect = pygame.Rect(rect.left, rect.top, rect.width, stats_height)
        preview_rect = pygame.Rect(
            rect.left,
            stats_rect.bottom + 12,
            rect.width,
            rect.height - stats_height - 12,
        )

        stats_motion = self._motion_level("panel:stats")
        inner = draw_panel(
            surface,
            pygame,
            stats_rect,
            title="Stats",
            accent=GOOD,
            emphasis=stats_motion,
            lift=int(stats_motion * 3),
        )
        draw_text_line(
            surface,
            self.fonts.heading,
            "Company Stats",
            TEXT,
            pygame.Rect(inner.left, inner.top - 28, max(120, inner.width - 166), 24),
            valign="top",
        )
        stats_entity_strength = self._entity_motion_strength("panel:stats")
        self._draw_panel_entity_strip(
            surface,
            pygame.Rect(inner.right - 156, inner.top - 30, 156, 28),
            panel_key="stats",
            strength=stats_entity_strength,
        )
        gauge_height = 44
        for index, gauge in enumerate(self._view_model.stats):
            top = inner.top + index * gauge_height
            gauge_motion = self._motion_level(f"stat:{gauge.key}")
            entity_strength = self._entity_motion_strength("panel:stats", f"stat:{gauge.key}")
            value_width = min(120, max(72, inner.width // 2))
            draw_text_line(
                surface,
                self.fonts.small,
                gauge.title.upper(),
                blend_color(MUTED, tone_color(gauge.tone), gauge_motion * 0.7),
                pygame.Rect(inner.left, top - 1, inner.width - value_width - 8, 18),
                valign="top",
            )
            draw_text_line(
                surface,
                self.fonts.mono,
                gauge.value_text,
                blend_color(TEXT, tone_color(gauge.tone), gauge_motion * 0.18),
                pygame.Rect(inner.right - value_width, top - 1, value_width, 18),
                align="right",
                valign="top",
            )
            bar_rect = pygame.Rect(inner.left, top + 18, inner.width, 14)
            if gauge_motion >= 0.08:
                lane_rect = pygame.Rect(inner.left - 6, top - 4, inner.width + 12, 36)
                pygame.draw.rect(
                    surface,
                    blend_color(BORDER, tone_color(gauge.tone), gauge_motion * 0.55),
                    lane_rect,
                    width=1,
                    border_radius=10,
                )
            draw_progress_bar(
                surface,
                pygame,
                bar_rect,
                ratio=self._tweens.get(gauge.key, gauge.ratio),
                color=tone_color(gauge.tone),
                emphasis=gauge_motion,
            )
            self._draw_stat_drama_effect(surface, gauge, bar_rect, gauge_motion, index)
            self._draw_entity_nodes(
                surface,
                pygame.Rect(bar_rect.left, bar_rect.top - 2, int(bar_rect.width * gauge.ratio), 18),
                accent=tone_color(gauge.tone),
                strength=entity_strength,
                count=2 if gauge.key == "board_pressure" else 3,
                offset=float(index) * 0.7,
            )

        preview_motion = self._motion_level("stat:runway", "stat:board_pressure")
        preview_inner = draw_panel(
            surface,
            pygame,
            preview_rect,
            title="Preview",
            accent=WARN,
            emphasis=preview_motion,
            lift=int(preview_motion * 2),
        )
        draw_text_line(
            surface,
            self.fonts.heading,
            "End-Turn Preview",
            TEXT,
            pygame.Rect(preview_inner.left, preview_inner.top - 28, preview_inner.width, 24),
            valign="top",
        )
        draw_text_line(
            surface,
            self.fonts.body,
            f"Warning: {self._view_model.preview_warning}",
            tone_color("danger" if self._view_model.preview_warning == "critical" else "warning"),
            pygame.Rect(preview_inner.left, preview_inner.top, preview_inner.width, 20),
            valign="top",
        )
        draw_text_line(
            surface,
            self.fonts.small,
            f"Outcome: {self._view_model.preview_outcome}",
            TEXT,
            pygame.Rect(preview_inner.left, preview_inner.top + 24, preview_inner.width, 18),
            valign="top",
        )
        draw_wrapped_text(
            surface,
            self.fonts.small,
            self._view_model.preview_reason,
            MUTED,
            pygame.Rect(
                preview_inner.left,
                preview_inner.top + 48,
                preview_inner.width,
                preview_inner.height - 70,
            ),
            line_height=17,
            max_lines=8,
        )

    def _draw_center_column(self, surface, rect) -> None:
        pygame = self.pygame
        products_motion = self._motion_level("panel:products")
        inner = draw_panel(
            surface,
            pygame,
            rect,
            title="Products",
            accent=SELECTION,
            emphasis=products_motion,
            lift=int(products_motion * 3),
        )
        draw_text_line(
            surface,
            self.fonts.heading,
            "Product Strip",
            TEXT,
            pygame.Rect(inner.left, inner.top - 28, max(130, inner.width - 180), 24),
            valign="top",
        )
        self._draw_panel_entity_strip(
            surface,
            pygame.Rect(inner.right - 170, inner.top - 30, 170, 28),
            panel_key="products",
            strength=self._entity_motion_strength("panel:products"),
        )
        available_height = inner.height
        spacing = 12
        card_height = max(
            108,
            int(
                (available_height - spacing * (len(self._view_model.products) - 1))
                / max(1, len(self._view_model.products))
            ),
        )
        top = inner.top
        for product in self._view_model.products:
            card_rect = pygame.Rect(inner.left, top, inner.width, card_height)
            self._draw_product_card(surface, card_rect, product)
            top += card_height + spacing

    def _draw_right_column(self, surface, rect) -> None:
        pygame = self.pygame
        guide_requested = self._first_turn_guide_active()
        coach_ratio = 0.62 if guide_requested else 0.5
        coach_height = int(rect.height * coach_ratio)
        if guide_requested and rect.height >= 260:
            coach_height = min(coach_height, rect.height - 96)
        coach_rect = pygame.Rect(rect.left, rect.top, rect.width, coach_height)
        event_rect = pygame.Rect(
            rect.left,
            coach_rect.bottom + 12,
            rect.width,
            rect.height - coach_height - 12,
        )

        coach_motion = self._motion_level("panel:coach")
        coach_inner = draw_panel(
            surface,
            pygame,
            coach_rect,
            title="Coach",
            accent=INFO,
            emphasis=coach_motion,
            lift=int(coach_motion * 2),
        )
        draw_text_line(
            surface,
            self.fonts.heading,
            "Turn Coach / Control Tower",
            TEXT,
            pygame.Rect(coach_inner.left, coach_inner.top - 28, coach_inner.width, 24),
            valign="top",
        )
        top = coach_inner.top
        if guide_requested and coach_inner.height >= 100:
            guide_height = min(82, max(58, int(coach_inner.height * 0.42)))
            guide_rect = pygame.Rect(coach_inner.left, top, coach_inner.width, guide_height)
            if self._draw_first_turn_guide_card(surface, guide_rect):
                top += guide_height + 10

        for line in self._view_model.coach_lines:
            if top + 66 > coach_inner.bottom - 76:
                break
            card_rect = pygame.Rect(coach_inner.left, top, coach_inner.width, 66)
            line_panel = self._workspace_panel_key_for_command(line.command)
            line_motion = (
                self._motion_level(f"panel:{line_panel}") if line_panel is not None else 0.0
            )
            draw_button(
                surface,
                pygame,
                rect=card_rect,
                title=line.label,
                detail=f"{line.family_label} / {line.source}",
                accent=INFO,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
                emphasis=line_motion,
                lift=int(line_motion * 2),
            )
            self._click_targets.append(ClickTarget("command", line.command, card_rect))
            draw_wrapped_text(
                surface,
                self.fonts.small,
                line.detail,
                MUTED,
                pygame.Rect(card_rect.left + 12, card_rect.top + 34, card_rect.width - 24, 24),
                line_height=15,
                max_lines=2,
            )
            top += 76

        if top + 46 <= coach_inner.bottom:
            draw_text_line(
                surface,
                self.fonts.small,
                "Not Now",
                WARN,
                pygame.Rect(coach_inner.left, top + 2, coach_inner.width, 18),
                valign="top",
            )
            deferred_top = top + 24
            for deferred_line in self._view_model.deferred_lines[:2]:
                consumed = draw_wrapped_text(
                    surface,
                    self.fonts.small,
                    deferred_line,
                    MUTED,
                    pygame.Rect(coach_inner.left, deferred_top, coach_inner.width, 34),
                    line_height=16,
                    max_lines=2,
                )
                deferred_top += max(22, consumed)
                if deferred_top + 48 > coach_inner.bottom:
                    break
            if deferred_top + 46 <= coach_inner.bottom:
                draw_text_line(
                    surface,
                    self.fonts.small,
                    "Risk Forecast",
                    DANGER,
                    pygame.Rect(coach_inner.left, deferred_top + 6, coach_inner.width, 18),
                    valign="top",
                )
                risk_top = deferred_top + 28
                for risk_line in self._view_model.risk_lines[:2]:
                    consumed = draw_wrapped_text(
                        surface,
                        self.fonts.small,
                        risk_line,
                        MUTED,
                        pygame.Rect(coach_inner.left, risk_top, coach_inner.width, 22),
                        line_height=16,
                        max_lines=1,
                    )
                    risk_top += max(20, consumed)
                    if risk_top > coach_inner.bottom:
                        break

        feed_motion = self._motion_level("feed")
        event_inner = draw_panel(
            surface,
            pygame,
            event_rect,
            title="Event Log",
            accent=GOOD,
            emphasis=feed_motion,
            lift=int(feed_motion * 2),
        )
        draw_text_line(
            surface,
            self.fonts.heading,
            "Animated Event Queue",
            TEXT,
            pygame.Rect(event_inner.left, event_inner.top - 28, event_inner.width, 24),
            valign="top",
        )
        if not self._events:
            draw_text_line(
                surface,
                self.fonts.body,
                "No transient events yet.",
                MUTED,
                pygame.Rect(event_inner.left, event_inner.top, event_inner.width, 22),
                valign="top",
            )
            return
        event_top = event_inner.top
        for timed_event in self._events[: self._event_queue_visible_count(event_rect.height)]:
            card_rect = pygame.Rect(event_inner.left, event_top, event_inner.width, 66)
            self._draw_event_card(surface, card_rect, timed_event)
            event_top += 76

    def _draw_compact_run_focus(self, surface, rect) -> None:
        if rect.height <= 0:
            return
        pygame = self.pygame
        focus_motion = self._motion_level("panel:coach", "panel:products", "panel:stats")
        inner = draw_panel(
            surface,
            pygame,
            rect,
            title="Run Focus",
            accent=SELECTION,
            emphasis=focus_motion,
            lift=int(focus_motion * 2),
        )
        draw_text_line(
            surface,
            self.fonts.heading,
            "Current Focus",
            TEXT,
            pygame.Rect(inner.left, inner.top - 28, inner.width, 24),
            valign="top",
        )
        focus_line = self._compact_vital_line()
        draw_text_line(
            surface,
            self.fonts.body,
            focus_line,
            TEXT,
            pygame.Rect(inner.left, inner.top, inner.width, 22),
            valign="top",
        )
        note_top = inner.top + 28
        chip_top = inner.bottom - 28
        chips = self._view_model.snapshot_chips[: 4 if inner.width >= 900 else 3]
        body_bottom = chip_top - 10
        body_height = body_bottom - note_top

        if inner.width < 620 or body_height < 92:
            guide_rect = pygame.Rect(inner.left, note_top, inner.width, max(18, body_height))
            if not self._draw_first_turn_guide_card(surface, guide_rect):
                brief = self._view_model.decision_brief
                draw_wrapped_text(
                    surface,
                    self.fonts.small,
                    (
                        f"1 Objective: {brief.objective} "
                        f"(Plan {brief.plan_progress_label.split(' | ', maxsplit=1)[0]}) | "
                        f"2 Next: {brief.command_label} ({brief.urgency_label}) | "
                        f"3 End Turn: {brief.end_turn_label}"
                    ),
                    TEXT,
                    guide_rect,
                    line_height=16,
                    max_lines=3,
                )
        else:
            if self._first_turn_guide_active() and body_height < 150:
                guide_rect = pygame.Rect(inner.left, note_top, inner.width, body_height)
                self._draw_first_turn_guide_card(surface, guide_rect)
                return
            guide_height = 88 if self._first_turn_guide_active() and body_height >= 150 else 0
            if guide_height:
                guide_rect = pygame.Rect(inner.left, note_top, inner.width, guide_height)
                self._draw_first_turn_guide_card(surface, guide_rect)
                note_top = guide_rect.bottom + 10
                body_height = body_bottom - note_top

            self._draw_focus_decision_cards(
                surface,
                left=inner.left,
                top=note_top,
                width=inner.width,
                body_height=body_height,
                body_bottom=body_bottom,
            )

        if chip_top <= note_top + 20 or not chips:
            return
        gap = 8
        chip_width = int((inner.width - gap * (len(chips) - 1)) / len(chips))
        left = inner.left
        for chip in chips:
            chip_rect = pygame.Rect(left, chip_top, chip_width, 26)
            self._draw_snapshot_chip(surface, chip_rect, chip.label, chip.value_text, chip.tone)
            left += chip_width + gap

    def _draw_focus_decision_cards(
        self,
        surface,
        *,
        left: int,
        top: int,
        width: int,
        body_height: int,
        body_bottom: int,
    ) -> None:
        pygame = self.pygame
        brief = self._view_model.decision_brief
        gap = 10
        wide_route = width >= 960
        if wide_route:
            card_height = min(220, max(66, body_height))
            card_width = int((width - gap * 2) / 3)
            objective_rect = pygame.Rect(left, top, card_width, card_height)
            next_rect = pygame.Rect(objective_rect.right + gap, top, card_width, card_height)
            risk_rect = pygame.Rect(
                next_rect.right + gap,
                top,
                left + width - next_rect.right - gap,
                card_height,
            )
        else:
            card_height = min(92, max(66, body_height if body_height < 132 else 82))
            card_width = int((width - gap) / 2)
            objective_rect = pygame.Rect(left, top, card_width, card_height)
            next_rect = pygame.Rect(objective_rect.right + gap, top, card_width, card_height)
            risk_top = objective_rect.bottom + gap
            risk_height = body_bottom - risk_top
            risk_rect = pygame.Rect(left, risk_top, width, risk_height)

        self._draw_focus_card(
            surface,
            objective_rect,
            eyebrow="1 / ACT OBJECTIVE",
            headline=brief.objective_label,
            detail=f"{brief.objective} Plan: {brief.plan_progress_label}.",
            accent=SELECTION,
        )
        self._draw_focus_card(
            surface,
            next_rect,
            eyebrow="2 / RECOMMENDED MOVE",
            headline=brief.command_label,
            detail=f"{brief.urgency_label}. {brief.command_detail}",
            accent=GOOD,
            click_kind="coach",
        )
        if risk_rect.height >= 48:
            self._draw_focus_card(
                surface,
                risk_rect,
                eyebrow="3 / END TURN CHECK",
                headline=brief.end_turn_label,
                detail=f"{brief.end_turn_detail} Later: {brief.later_label}.",
                accent=tone_color(brief.end_turn_tone),
                click_kind="command" if brief.end_turn_enabled else None,
                click_payload=(TurnAction.END_TURN.value if brief.end_turn_enabled else ""),
                compact=True,
            )

    def _draw_focus_card(
        self,
        surface,
        rect,
        *,
        eyebrow: str,
        headline: str,
        detail: str,
        accent,
        click_kind: str | None = None,
        click_payload: str = "",
        compact: bool = False,
    ) -> None:
        pygame = self.pygame
        pygame.draw.rect(
            surface,
            blend_color((18, 29, 44), accent, 0.12),
            rect,
            border_radius=14,
        )
        pygame.draw.rect(
            surface,
            blend_color(BORDER, accent, 0.3),
            rect,
            width=1,
            border_radius=14,
        )
        draw_text_line(
            surface,
            self.fonts.small,
            eyebrow,
            accent,
            pygame.Rect(rect.left + 12, rect.top + 8, rect.width - 24, 14),
            valign="top",
        )
        draw_text_line(
            surface,
            self.fonts.small if compact else self.fonts.body,
            headline,
            TEXT,
            pygame.Rect(rect.left + 12, rect.top + 25, rect.width - 24, 20),
            valign="top",
        )
        detail_top = rect.top + (43 if compact else 45)
        detail_height = rect.bottom - detail_top - 6
        if detail_height >= 15:
            draw_wrapped_text(
                surface,
                self.fonts.small,
                detail,
                MUTED,
                pygame.Rect(
                    rect.left + 12,
                    detail_top,
                    rect.width - 24,
                    detail_height,
                ),
                line_height=15,
                max_lines=2,
            )
        if click_kind is not None:
            self._click_targets.append(ClickTarget(click_kind, click_payload, rect))

    def _use_compact_run_focus(self, width: int, content_height: int) -> bool:
        if self._focus_mode:
            return True
        if content_height < 200:
            return True
        if width < 940:
            section_height = int((content_height - 24) / 3)
            return section_height < 180
        return False

    def _toggle_focus_mode(self) -> None:
        if self._window_width() < 940:
            self.push_event(
                FrontendEvent(
                    title="Compact View Locked",
                    detail="This window keeps Focus View active to prevent overlap.",
                    severity="info",
                    ttl=3.5,
                )
            )
            return
        self._focus_mode = not self._focus_mode
        self._motion_pulses.trigger("panel:coach", intensity=0.62, decay=1.8)
        self.push_event(
            FrontendEvent(
                title="Focus View" if self._focus_mode else "Full Workspace",
                detail=(
                    "Showing the guided decision hierarchy."
                    if self._focus_mode
                    else "Showing all dashboard columns. Press 0 to return to Focus View."
                ),
                severity="success" if self._focus_mode else "info",
                ttl=3.5,
            )
        )

    def _compact_vital_line(self) -> str:
        stats = {stat.key: stat.value_text for stat in self._view_model.stats}
        return (
            f"Cash {stats.get('cash', '-')} | Runway {stats.get('runway', '-')} | "
            f"Users {stats.get('users', '-')} | AP {stats.get('actions', '-')} | "
            f"Journey {self._view_model.run_journey.step_label}"
        )

    def _draw_first_turn_guide_card(self, surface, rect) -> bool:
        if not self._first_turn_guide_active() or rect.width < 320 or rect.height < 58:
            return False
        pygame = self.pygame
        steps = self._first_turn_guide_steps()
        shimmer = (
            0.0
            if self.motion_mode is MotionMode.OFF
            else 0.5 + 0.5 * sin(self._motion_elapsed * 2.6)
        )
        card_rect = pygame.Rect(rect.left, rect.top, rect.width, min(rect.height, 88))
        self._first_turn_guide_visible = True
        pygame.draw.rect(
            surface,
            blend_color((18, 29, 44), INFO, 0.12 + shimmer * 0.04),
            card_rect,
            border_radius=14,
        )
        pygame.draw.rect(
            surface,
            blend_color(BORDER, SELECTION, 0.28 + shimmer * 0.18),
            card_rect,
            width=1,
            border_radius=14,
        )
        self._click_targets.append(ClickTarget("coach", "", card_rect))
        title = (
            f"Guided Opening | Journey {self._view_model.run_journey.step_label} | "
            "Follow the 3-step checklist"
        )
        detail = "Coach executes the recommendation. P pause | S save | Space end turn."
        draw_text_line(
            surface,
            self.fonts.small,
            title,
            TEXT,
            pygame.Rect(card_rect.left + 12, card_rect.top + 7, card_rect.width - 24, 18),
            valign="top",
        )
        draw_text_line(
            surface,
            self.fonts.small,
            detail,
            MUTED,
            pygame.Rect(card_rect.left + 12, card_rect.top + 24, card_rect.width - 24, 16),
            valign="top",
        )
        chip_top = card_rect.top + 44
        chip_height = max(24, card_rect.bottom - chip_top - 8)
        chip_gap = 6
        chip_width = int((card_rect.width - chip_gap * (len(steps) - 1)) / len(steps))
        left = card_rect.left
        pending_seen = False
        for step in steps:
            if step.done:
                status = "DONE"
                fill_ratio = 0.22
                border_ratio = 0.42
            elif not pending_seen:
                status = "NEXT"
                fill_ratio = 0.16 + shimmer * 0.06
                border_ratio = 0.52
                pending_seen = True
            else:
                status = "LATER"
                fill_ratio = 0.07
                border_ratio = 0.22
            chip_rect = pygame.Rect(left, chip_top, chip_width, chip_height)
            pygame.draw.rect(
                surface,
                blend_color((24, 36, 52), step.accent, fill_ratio),
                chip_rect,
                border_radius=11,
            )
            pygame.draw.rect(
                surface,
                blend_color(BORDER, step.accent, border_ratio),
                chip_rect,
                width=1,
                border_radius=11,
            )
            draw_text_line(
                surface,
                self.fonts.small,
                f"{status} {step.label}",
                TEXT if step.done or status == "NEXT" else MUTED,
                pygame.Rect(chip_rect.left + 8, chip_rect.top + 4, chip_rect.width - 16, 14),
                valign="top",
            )
            if chip_rect.height >= 30:
                draw_text_line(
                    surface,
                    self.fonts.small,
                    step.detail,
                    MUTED,
                    pygame.Rect(
                        chip_rect.left + 8,
                        chip_rect.top + 19,
                        chip_rect.width - 16,
                        chip_rect.height - 21,
                    ),
                    valign="top",
                )
            left += chip_width + chip_gap
        return True

    def _draw_footer(self, surface, rect) -> None:
        pygame = self.pygame
        footer_motion = self._motion_level("footer")
        inner = draw_panel(
            surface,
            pygame,
            rect,
            title="Decisions" if self._focus_mode else "Actions",
            accent=INFO,
            emphasis=footer_motion,
            lift=int(footer_motion * 2),
        )
        draw_text_line(
            surface,
            self.fonts.heading,
            "Decision Bar" if self._focus_mode else "Action Bar",
            TEXT,
            pygame.Rect(inner.left, inner.top - 28, inner.width, 24),
            valign="top",
        )
        buttons = self._footer_action_buttons()
        button_cols, button_height, footer_band_height = self._footer_layout_metrics(
            inner.width,
            inner.height,
            button_count=len(buttons),
        )
        button_gap = 10
        button_width = int((inner.width - button_gap * (button_cols - 1)) / button_cols)
        top = inner.top
        for index, button in enumerate(buttons):
            if index % button_cols == 0:
                if index:
                    top += button_height + button_gap
                row_count = min(button_cols, len(buttons) - index)
                row_width = row_count * button_width + (row_count - 1) * button_gap
                left = inner.centerx - row_width // 2
            button_rect = pygame.Rect(left, top, button_width, button_height)
            enabled = self._button_is_enabled(button)
            selected = button.kind == "panel" and button.payload == self._active_panel_key()
            button_motion = (
                self._motion_level(f"panel:{button.payload}") if button.kind == "panel" else 0.0
            )
            draw_button(
                surface,
                pygame,
                rect=button_rect,
                title=self._footer_button_title(button, button_cols=button_cols),
                detail=self._footer_button_detail(
                    button,
                    enabled=enabled,
                    button_cols=button_cols,
                ),
                accent=button.accent,
                title_font=self.fonts.body if button_cols <= 5 else self.fonts.small,
                detail_font=self.fonts.small,
                enabled=enabled,
                selected=selected,
                emphasis=button_motion,
                lift=int(button_motion * 2),
            )
            self._click_targets.append(ClickTarget(button.kind, button.payload, button_rect))
            left += button_width + button_gap
        footer_top = inner.bottom - footer_band_height + 6
        status_line, hint_line = self._footer_status_lines(max_width=inner.width)
        draw_wrapped_text(
            surface,
            self.fonts.small,
            status_line,
            TEXT,
            pygame.Rect(inner.left, footer_top, inner.width, 16),
            line_height=14,
            max_lines=1,
        )
        draw_wrapped_text(
            surface,
            self.fonts.small,
            hint_line,
            MUTED,
            pygame.Rect(inner.left, footer_top + 18, inner.width, 16),
            line_height=14,
            max_lines=1,
        )

    def _footer_outer_height(self, width: int, height: int) -> int:
        usable_width = width - 40 - 32
        button_cols = self._footer_button_columns(usable_width)
        rows = max(1, (len(self._footer_action_buttons()) + button_cols - 1) // button_cols)
        button_gap = 10
        button_height = 34 if height < 700 else 40 if button_cols <= 5 else 44
        footer_band_height = 38 if height < 700 else 46
        panel_chrome = 60
        return (
            panel_chrome + rows * button_height + button_gap * max(0, rows - 1) + footer_band_height
        )

    def _footer_layout_metrics(
        self,
        inner_width: int,
        inner_height: int,
        *,
        button_count: int | None = None,
    ) -> tuple[int, int, int]:
        button_cols = self._footer_button_columns(inner_width)
        visible_count = (
            button_count if button_count is not None else len(self._footer_action_buttons())
        )
        rows = max(1, (visible_count + button_cols - 1) // button_cols)
        footer_band_height = 42 if inner_height < 300 else 48 if button_cols >= 5 else 52
        button_gap = 10
        button_area_height = max(
            36,
            inner_height - footer_band_height - button_gap * max(0, rows - 1),
        )
        available_per_row = int(button_area_height / rows)
        min_button_height = 34 if inner_height < 300 else 38 if button_cols <= 5 else 42
        if available_per_row < min_button_height:
            button_height = max(30, available_per_row)
        else:
            button_height = min(58, max(min_button_height, available_per_row))
        return button_cols, button_height, footer_band_height

    def _footer_action_buttons(self) -> tuple[ActionButtonSpec, ...]:
        """Keep the live action bar focused while preserving every keyboard route."""

        if self._focus_mode:
            return self._focus_footer_action_buttons()

        core_titles = {"Coach", "Team", "Finance", "Customers", "Report"}
        final_titles = {"Save", "End Turn"}
        buttons = [button for button in _ACTION_BUTTONS if button.title in core_titles]
        loadout_buttons = list(self._loadout_action_buttons())
        if not loadout_buttons:
            loadout_buttons = [
                button for button in _ACTION_BUTTONS if button.title in {"Improve", "Market"}
            ]
        buttons.extend(button for button in loadout_buttons if button not in buttons)

        contextual_panel_titles: list[str] = []
        if self.state.company.current_turn >= 10 or self.state.victory_achieved:
            contextual_panel_titles.append("Endgame")
        if (
            self.state.finance.board_pressure >= 20
            or self.state.finance.board_warning_active
            or self.state.company.current_turn >= 6
        ):
            contextual_panel_titles.append("Board")
        if self.state.partnerships or self.state.company.current_turn >= 5:
            contextual_panel_titles.append("Partners")
        contextual_panels = [
            button
            for title in contextual_panel_titles
            for button in _ACTION_BUTTONS
            if button.title == title and button not in buttons
        ]

        contextual_commands = [line.command for line in self._view_model.coach_lines[:3]]
        if not self.state.employees:
            contextual_commands.append(TurnAction.HIRE_EMPLOYEE.value)
        elif any(employee.assigned_product_id is None for employee in self.state.employees):
            contextual_commands.append(TurnAction.ASSIGN_EMPLOYEE.value)
        if (
            self.state.campaign_goal_id.value == "portfolio_empire"
            and self.state.company.current_turn >= 4
        ):
            contextual_commands.append(TurnAction.CREATE_PRODUCT.value)

        contextual_buttons = [
            button
            for command in dict.fromkeys(contextual_commands)
            for button in _ACTION_BUTTONS
            if button.payload == command and button not in buttons
        ]
        contextual_budget = max(0, 10 - len(buttons) - len(final_titles))
        buttons.extend((contextual_panels + contextual_buttons)[:contextual_budget])
        buttons.extend(button for button in _ACTION_BUTTONS if button.title in final_titles)
        return tuple(buttons)

    def _focus_footer_action_buttons(self) -> tuple[ActionButtonSpec, ...]:
        """Expose one guided route, two alternatives, review, save, and resolution."""

        coach_button = next(button for button in _ACTION_BUTTONS if button.title == "Coach")
        report_button = next(button for button in _ACTION_BUTTONS if button.title == "Report")
        final_buttons = tuple(
            button for button in _ACTION_BUTTONS if button.title in {"Save", "End Turn"}
        )
        recommended: list[ActionButtonSpec] = list(self._loadout_action_buttons())
        for line in self._view_model.coach_lines[:3]:
            candidate = next(
                (
                    button
                    for button in _ACTION_BUTTONS
                    if button.payload == line.command and button.title not in {"Save", "End Turn"}
                ),
                None,
            )
            if candidate is None:
                panel_key = self._workspace_panel_key_for_command(line.command)
                candidate = next(
                    (
                        button
                        for button in _ACTION_BUTTONS
                        if button.kind == "panel" and button.payload == panel_key
                    ),
                    None,
                )
            if candidate is not None and candidate not in recommended:
                recommended.append(candidate)
            if len(recommended) == 2:
                break

        if not recommended:
            recommended.extend(
                button for button in _ACTION_BUTTONS if button.title in {"Improve", "Market"}
            )
        return (coach_button, *recommended[:2], report_button, *final_buttons)

    def _loadout_action_buttons(self) -> tuple[ActionButtonSpec, ...]:
        """Return enabled action buttons emphasized by the local player profile."""

        loadout = self._current_frontend_preferences().action_loadout
        commands = _ACTION_LOADOUT_COMMANDS[loadout]
        return tuple(
            button
            for command in commands
            for button in _ACTION_BUTTONS
            if button.payload == command and self._button_is_enabled(button)
        )

    def _footer_button_columns(self, available_width: int) -> int:
        if available_width < 620:
            return 4
        if available_width < 860:
            return 5
        return 7

    def _footer_button_title(self, button: ActionButtonSpec, *, button_cols: int) -> str:
        if button_cols < 7:
            return f"{button.key_hint} {button.title}"
        compact_titles = {
            "New Product": "Product",
            "Customers": "Cust",
            "Partners": "Partner",
            "Pipeline": "Pipe",
            "Endgame": "Exit",
            "Debt Down": "Debt",
            "Strategy": "Strat",
            "Roadmap": "Map",
            "End Turn": "End",
        }
        key_hint = "Sp" if button.key_hint == "Space" else button.key_hint
        title = compact_titles.get(button.title, button.title)
        return f"{key_hint} {title}"

    def _footer_button_detail(
        self,
        button: ActionButtonSpec,
        *,
        enabled: bool,
        button_cols: int,
    ) -> str:
        detail = self._button_detail(
            button.payload if button.kind in {"command", "text_command"} else None,
            button.detail,
            enabled=enabled,
        )
        max_length = 24 if button_cols <= 4 else 28 if button_cols == 5 else 36
        return self._compact_button_detail(detail, max_length=max_length)

    def _footer_status_lines(self, *, max_width: int | None = None) -> tuple[str, str]:
        workspace_key = self._active_panel_key()
        workspace_title = (
            self._panel_display_name(workspace_key) if workspace_key is not None else "Core HUD"
        )
        hover_hint = self._hover_hint_line()
        hint = hover_hint or f"Watch: {self._view_model.watch_for}"
        if self._inspector_panel_key is not None and self.inspector_panel is not None:
            section = self._selected_inspector_section()
            section_title = section.title if section is not None else "Records"
            action_summary = self._selected_inspector_primary_action_summary()
            primary = (
                f"Inspector: {self.inspector_panel.title} | {section_title} | "
                f"page {self._inspector_page + 1}/{self._inspector_total_pages()}"
            )
            if action_summary:
                primary = f"{primary} | {action_summary}"
        elif self._context_picker is not None:
            primary = (
                f"Picker: {self._context_picker.title} | {len(self._context_picker.options)} "
                f"options | workspace {workspace_title}"
            )
        elif self._text_input is not None:
            primary = f"Input: {self._text_input.title} | workspace {workspace_title}"
        elif self.state.pending_event is not None:
            primary = (
                f"Pending Event: {self.state.pending_event.title} | resolve before more actions"
            )
        elif self._deep_panel_key == "endgame":
            primary = self._endgame_cockpit_status_line()
            panel = self.deep_panel
            if panel is not None:
                disclosure = build_panel_disclosure(
                    panel,
                    expanded=self._endgame_actions_expanded,
                )
                hint = (
                    "V Guided View | I Inspector | Esc Close"
                    if self._endgame_actions_expanded
                    else (f"V Show {disclosure.hidden_action_count} More | I Inspector | Esc Close")
                )
        elif self._focus_mode:
            brief = self._view_model.decision_brief
            primary = (
                f"Recommended: {brief.command_label} | {brief.urgency_label} | "
                f"Actions Left: {self.state.action_points_remaining}"
            )
            more_hint = " | 0 More opens every action" if self._window_width() >= 940 else ""
            hint = (
                f"Why: {brief.command_detail} | End Turn: {brief.end_turn_label} | "
                f"Later: {brief.later_label}{more_hint}"
            )
        else:
            primary = (
                f"Workspace: {workspace_title} | Product: {self.selected_product.name} | "
                f"Actions Left: {self.state.action_points_remaining}"
            )
        if hover_hint:
            hint = hover_hint
        if max_width is not None and max_width < 760:
            if (
                self._focus_mode
                and self._deep_panel_key is None
                and self._inspector_panel_key is None
                and self._context_picker is None
                and self._text_input is None
                and self.state.pending_event is None
                and not hover_hint
            ):
                brief = self._view_model.decision_brief
                primary = (
                    f"Next: {brief.command_label} | {brief.urgency_label} | "
                    f"AP: {self.state.action_points_remaining}"
                )
                hint = (
                    f"End Turn: {brief.end_turn_label} | Later: {brief.later_label} | "
                    "Hover C Coach for why"
                )
            primary = self._compact_footer_status_line(primary)
            hint = self._compact_footer_hint_line(hint)
        return primary, hint

    def _compact_footer_status_line(self, line: str) -> str:
        compact = line
        replacements = (
            ("Workspace: ", "WS: "),
            ("Inspector: ", "Inspect: "),
            ("Pending Event: ", "Event: "),
            ("Actions Left: ", "AP: "),
            ("Product: ", "Prod: "),
            ("options", "opts"),
            ("workspace ", "ws "),
            ("resolve before more actions", "resolve first"),
        )
        for source, target in replacements:
            compact = compact.replace(source, target)
        return self._compact_button_detail(compact, max_length=92)

    def _compact_footer_hint_line(self, line: str) -> str:
        compact = line
        replacements = (
            ("Click ", "Tap "),
            ("Control: ", "Ctrl: "),
            (" because ", ": "),
            (" currently ", " "),
            ("hover over controls", "hover controls"),
        )
        for source, target in replacements:
            compact = compact.replace(source, target)
        return self._compact_button_detail(compact, max_length=96)

    def _event_queue_visible_count(self, event_height: int) -> int:
        visible = 2 if event_height < 180 else 3 if event_height < 280 else 4
        if self._overlay_or_pending_active():
            visible = min(visible, 2)
        if self._window_width() < 920:
            visible = max(1, visible - 1)
        if self._overlay_or_pending_active() and len(self._events) >= 4:
            visible = max(1, visible - 1)
        return visible

    def _endgame_cockpit_status_line(self) -> str:
        panel = self.deep_panel
        compact = self._window_width() < 1000
        workspace_title = (
            self._panel_display_name(self._deep_panel_key)
            if self._deep_panel_key is not None
            else "Endgame / Exit Board"
        )
        if panel is None:
            return f"{'Endgame' if compact else 'Workspace'}: {workspace_title}"
        gate_action = next(
            (action for action in panel.actions if action.label == "Recommended Fix"),
            None,
        )
        hotspot_action = next(
            (action for action in panel.actions if action.label == "Review Main Risk"),
            None,
        )
        segments = [f"{'Endgame' if compact else 'Workspace'}: {workspace_title}"]
        if gate_action is not None:
            segments.append(
                f"Next: {self._compact_command_token(gate_action.command, compact=compact)}"
            )
        if hotspot_action is not None:
            segments.append(
                f"Risk: {self._compact_command_token(hotspot_action.command, compact=compact)}"
            )
        segments.append(f"Actions Left: {self.state.action_points_remaining}")
        return " | ".join(segments)

    def _window_width(self) -> int:
        surface = self.pygame.display.get_surface()
        if surface is None:
            return 1280
        return surface.get_size()[0]

    def _compact_command_token(self, command: str, *, compact: bool) -> str:
        label = get_action_label(command)
        if not compact:
            return label
        return self._compact_button_detail(label, max_length=24)

    def _selected_inspector_primary_action_summary(self) -> str:
        item = self._selected_inspector_item()
        if item is None or not item.actions:
            return ""
        action = item.actions[0]
        reason = self._inspector_item_action_reason(action.command, item.payload)
        if reason is None:
            return f"Next: 1 {action.label}"
        return f"Blocked: {self._compact_button_detail(reason)}"

    def _button_is_enabled(self, button: ActionButtonSpec) -> bool:
        if button.kind in {"save", "panel"}:
            return True
        if button.kind in {"command", "panel_action", "text_command"}:
            return self._command_disabled_reason(button.payload) is None
        return not self.state.company.game_over

    def _hover_hint_line(self) -> str:
        target = self._hover_target()
        if target is None:
            return ""
        return self._describe_click_target(target)

    def _active_panel_key(self) -> str | None:
        return self._inspector_panel_key or self._deep_panel_key

    def _hover_target(self) -> ClickTarget | None:
        return self._hover_target_for_position(self.pygame.mouse.get_pos())

    def _draw_hover_tooltip(self, surface) -> None:
        if self._help_overlay_visible or self._text_input is not None:
            return
        target = self._hover_target()
        if target is None:
            return
        description = self._describe_click_target(target)
        if not description:
            return
        pygame = self.pygame
        mouse_x, mouse_y = pygame.mouse.get_pos()
        tooltip_width = (
            360 if surface.get_width() >= 1024 else 320 if surface.get_width() >= 900 else 280
        )
        tooltip_height = 88 if surface.get_width() >= 900 else 80
        tooltip_rect = self._hover_tooltip_rect(
            surface,
            mouse_x=mouse_x,
            mouse_y=mouse_y,
            width=tooltip_width,
            height=tooltip_height,
        )
        inner = draw_panel(surface, pygame, tooltip_rect, title="Hint", accent=INFO)
        draw_wrapped_text(
            surface,
            self.fonts.small,
            description,
            TEXT,
            pygame.Rect(inner.left, inner.top, inner.width, inner.height - 4),
            line_height=16,
            max_lines=4 if tooltip_width >= 320 else 3,
        )

    def _hover_tooltip_rect(
        self,
        surface,
        *,
        mouse_x: int,
        mouse_y: int,
        width: int,
        height: int,
    ):
        pygame = self.pygame
        margin = 16
        rect = pygame.Rect(mouse_x + 16, mouse_y + 16, width, height)
        if rect.right > surface.get_width() - margin:
            rect.left = surface.get_width() - rect.width - margin
        if rect.bottom > surface.get_height() - margin:
            rect.top = mouse_y - rect.height - 12
        rect.left = max(margin, rect.left)
        rect.top = max(margin, rect.top)
        return rect

    def _describe_click_target(self, target: ClickTarget) -> str:
        if target.kind == "select_product":
            for product in self._view_model.products:
                if product.id == target.payload:
                    return f"Hover: focus {product.name} and route product actions there."
        if target.kind in {"command", "panel_action", "text_command"}:
            reason = self._command_disabled_reason(target.payload)
            command_label = get_action_label(target.payload)
            if reason is not None:
                return f"Hover: {command_label} is blocked because {reason}"
            if target.payload == TurnAction.END_TURN.value:
                brief = self._view_model.decision_brief
                return (
                    f"Hover: {brief.end_turn_label}. {brief.end_turn_detail} "
                    f"Later: {brief.later_label} - {brief.later_detail}"
                )
            if target.kind == "panel_action" and self._deep_panel_key == "endgame":
                workspace_key = self._workspace_panel_key_for_command(target.payload)
                inspector_key = self._inspector_key_for_command(target.payload)
                destination = inspector_key or workspace_key
                if destination is not None:
                    return (
                        f"Hover: run {command_label} from the cockpit and hand off into "
                        f"{self._panel_display_name(destination)}."
                    )
            return f"Hover: run {command_label} now."
        if target.kind == "endgame_actions_toggle":
            return (
                "Hover: return to the recommended fix and main risk."
                if self._endgame_actions_expanded
                else "Hover: reveal exit-path fixes and specialist reviews."
            )
        if target.kind == "panel":
            return f"Hover: open the {target.payload} deep-dive panel."
        if target.kind == "open_panel_inspector":
            return f"Hover: inspect the `{target.payload}` panel in full detail."
        if target.kind == "coach":
            brief = self._view_model.decision_brief
            consequence = self._compact_button_detail(
                brief.command_consequence,
                max_length=120,
            )
            return (
                f"Hover: run {brief.command_label} ({brief.urgency_label}). "
                f"If skipped: {consequence}"
            )
        if target.kind == "inspector_section":
            return f"Hover: focus the `{target.payload}` inspector section."
        if target.kind == "inspector_item_action":
            item = self._selected_inspector_item()
            if item is None:
                return "Hover: run the selected inspector action."
            action_index = int(target.payload)
            if action_index < len(item.actions):
                action = item.actions[action_index]
                return f"Hover: {action.label} on {item.title}."
        if target.kind == "inspector_item":
            return "Hover: focus this record and expose item-level actions."
        if target.kind == "save":
            return "Hover: persist the current run to the active slot."
        if target.kind == "continue":
            return "Hover: continue from the summary back into the live run."
        if target.kind == "close_summary":
            return "Hover: close the 2D shell from the turn summary."
        if target.kind == "pause_toggle":
            return "Hover: open Pause for resume, save, settings, menu, or quit controls."
        if target.kind == "run_back":
            return "Hover: close the current overlay first; with no overlay open, show Pause."
        if target.kind == "open_help":
            return "Hover: open the control guide for keyboard, mouse, pause, and inspector hints."
        if target.kind == "focus_toggle":
            return "Hover: open every action or return to the guided decision view."
        if target.kind == "pause_resume":
            return "Hover: resume the run without changing the current state."
        if target.kind == "pause_save":
            return "Hover: save the current run to the active slot and stay paused."
        if target.kind == "pause_settings":
            return "Hover: adjust text scale, contrast, and motion while the run stays paused."
        if target.kind == "pause_settings_cycle":
            return f"Hover: cycle the saved `{target.payload}` preference."
        if target.kind == "pause_settings_reset":
            return "Hover: restore the default 2D display and motion profile."
        if target.kind == "pause_settings_back":
            return "Hover: return to the main Pause controls."
        if target.kind == "pause_menu":
            return "Hover: save and return to the 2D title menu when this run has a title shell."
        if target.kind == "pause_quit":
            return "Hover: close the 2D shell after saving dirty run state on exit."
        if target.kind == "close_help":
            return "Hover: close Help and return to the current run screen."
        if target.kind == "close_picker":
            return "Hover: close this picker without running an option."
        if target.kind in {"close_panel", "close_inspector"}:
            return "Hover: close this detail view and return to the live dashboard."
        if target.kind == "open_review":
            return "Hover: open the post-run review with final findings and next-focus notes."
        if target.kind == "close_outcome":
            return "Hover: close the outcome overlay and return to the run shell."
        if target.kind == "pending_option":
            return "Hover: resolve the pending event with this option."
        return ""

    def _overlay_button_detail(
        self,
        command: str | None,
        default_detail: str,
        *,
        enabled: bool,
    ) -> str:
        detail = self._button_detail(command, default_detail, enabled=enabled)
        return self._compact_button_detail(detail, max_length=32)

    def _draw_product_card(self, surface, rect, product) -> None:
        pygame = self.pygame
        product_motion = self._motion_level(
            f"product:{product.id}",
            f"product:{product.id}:quality",
            f"product:{product.id}:bugs",
            f"product:{product.id}:fit",
            f"product:{product.id}:debt",
        )
        visual_rect = pygame.Rect(
            rect.left, rect.top - int(product_motion * 5), rect.width, rect.height
        )
        fill_seed = (33, 48, 68) if product.selected else (24, 35, 50)
        fill = blend_color(
            fill_seed, SELECTION if product.selected else INFO, product_motion * 0.16
        )
        border_seed = SELECTION if product.selected else BORDER
        border = blend_color(border_seed, tone_color("info"), product_motion * 0.4)
        pygame.draw.rect(surface, fill, visual_rect, border_radius=16)
        pygame.draw.rect(
            surface,
            border,
            visual_rect,
            width=2 if product.selected or product_motion >= 0.35 else 1,
            border_radius=16,
        )
        self._click_targets.append(ClickTarget("select_product", product.id, rect))
        if product_motion >= 0.08:
            pygame.draw.rect(
                surface,
                blend_color(INFO, TEXT, product_motion * 0.1),
                (visual_rect.left + 1, visual_rect.top + 1, visual_rect.width - 2, 4),
                border_radius=4,
            )
        self._draw_product_drama_effects(surface, visual_rect, product, product_motion)
        entity_strength = self._entity_motion_strength(
            "panel:products",
            f"product:{product.id}",
            f"product:{product.id}:quality",
            f"product:{product.id}:bugs",
            f"product:{product.id}:fit",
            f"product:{product.id}:debt",
        )
        self._draw_entity_nodes(
            surface,
            pygame.Rect(
                visual_rect.left + 18,
                visual_rect.bottom - 28,
                min(180, visual_rect.width - 36),
                18,
            ),
            accent=SELECTION if product.selected else INFO,
            strength=entity_strength,
            count=4,
            offset=float(sum(ord(char) for char in product.id[:6])) * 0.03,
        )
        if product.selected:
            badge_rect = pygame.Rect(visual_rect.right - 84, visual_rect.top + 10, 70, 18)
            pygame.draw.rect(surface, SELECTION, badge_rect, border_radius=9)
            badge_surface = self.fonts.small.render("ACTIVE", True, BACKGROUND)
            surface.blit(badge_surface, (badge_rect.left + 10, badge_rect.top + 3))
        revenue_width = min(132, max(80, visual_rect.width // 3))
        title_width = max(80, visual_rect.width - revenue_width - 42)
        draw_text_line(
            surface,
            self.fonts.heading,
            product.name,
            TEXT,
            pygame.Rect(visual_rect.left + 14, visual_rect.top + 10, title_width, 24),
            valign="top",
        )
        draw_text_line(
            surface,
            self.fonts.small,
            f"{product.stage} | {product.segment} | users {product.users_text}",
            blend_color(MUTED, INFO, product_motion * 0.22),
            pygame.Rect(visual_rect.left + 14, visual_rect.top + 36, visual_rect.width - 28, 18),
            valign="top",
        )
        draw_text_line(
            surface,
            self.fonts.small,
            product.revenue_text,
            blend_color(INFO, TEXT, product_motion * 0.18),
            pygame.Rect(
                visual_rect.right - revenue_width - 14, visual_rect.top + 12, revenue_width, 20
            ),
            align="right",
            valign="top",
        )
        metrics = (
            (
                "Quality",
                self._tweens.get(f"{product.id}:quality", product.quality_ratio),
                GOOD,
                self._motion_level(f"product:{product.id}:quality", f"product:{product.id}"),
            ),
            (
                "Bugs",
                self._tweens.get(f"{product.id}:bugs", product.bug_ratio),
                DANGER,
                self._motion_level(f"product:{product.id}:bugs", f"product:{product.id}"),
            ),
            (
                "Fit",
                self._tweens.get(f"{product.id}:fit", product.fit_ratio),
                INFO,
                self._motion_level(f"product:{product.id}:fit", f"product:{product.id}"),
            ),
            (
                "Debt",
                self._tweens.get(f"{product.id}:debt", product.debt_ratio),
                WARN,
                self._motion_level(f"product:{product.id}:debt", f"product:{product.id}"),
            ),
        )
        start_y = visual_rect.top + 68
        for index, (label, ratio, color, emphasis) in enumerate(metrics):
            draw_text_line(
                surface,
                self.fonts.small,
                label,
                blend_color(MUTED, color, emphasis * 0.5),
                pygame.Rect(visual_rect.left + 14, start_y + index * 20 - 1, 58, 16),
                valign="top",
            )
            bar_rect = pygame.Rect(
                visual_rect.left + 78,
                start_y + 2 + index * 20,
                visual_rect.width - 92,
                12,
            )
            draw_progress_bar(
                surface, pygame, bar_rect, ratio=ratio, color=color, emphasis=emphasis
            )

    def _draw_product_drama_effects(self, surface, rect, product, product_motion: float) -> None:
        if self.motion_mode is MotionMode.OFF:
            return
        pygame = self.pygame
        phase = self._entity_motion_phase(
            offset=float(sum(ord(char) for char in product.id[:8])) * 0.02,
            speed=1.9,
        )
        quality_strength = max(0.0, product.quality_ratio - 0.58) + product_motion * 0.26
        fit_strength = max(0.0, product.fit_ratio - 0.62) + product_motion * 0.2
        if quality_strength > 0.04 or fit_strength > 0.04:
            shimmer = min(1.0, quality_strength + fit_strength)
            sweep_x = rect.left + int(((phase * 42) % max(1, rect.width + 80)) - 70)
            for offset in range(0, 46, 12):
                start = (sweep_x + offset, rect.top + 8)
                end = (sweep_x + offset + 34, rect.bottom - 10)
                pygame.draw.line(
                    surface,
                    blend_color(SELECTION, TEXT, shimmer * 0.2),
                    start,
                    end,
                    max(1, int(1 + shimmer * 2)),
                )
        if product.bug_ratio >= 0.34:
            bug_strength = min(1.0, product.bug_ratio + product_motion * 0.35)
            blink = 0.55 + ((sin(phase * 2.4) + 1.0) / 2.0) * 0.45
            for index in range(3):
                marker_x = rect.right - 34 - index * 18
                marker_y = rect.bottom - 26 + int(sin(phase + index) * 2)
                marker_rect = pygame.Rect(marker_x, marker_y, 10, 10)
                pygame.draw.rect(
                    surface,
                    blend_color(DANGER, TEXT, bug_strength * 0.14 * blink),
                    marker_rect,
                    border_radius=3,
                )
                pygame.draw.rect(surface, DANGER, marker_rect, width=1, border_radius=3)
        if product.debt_ratio >= 0.45:
            debt_strength = min(1.0, product.debt_ratio + product_motion * 0.3)
            crack_left = rect.right - int(rect.width * 0.28)
            crack_top = rect.top + 48
            points = [
                (crack_left, crack_top),
                (crack_left + 14, crack_top + 10),
                (crack_left + 6, crack_top + 22),
                (crack_left + 24, crack_top + 36),
                (crack_left + 16, crack_top + 50),
            ]
            pygame.draw.lines(
                surface,
                blend_color(WARN, TEXT, debt_strength * 0.16),
                False,
                points,
                2 if debt_strength > 0.75 else 1,
            )
        user_count = int(product.users_text.replace(",", "")) if product.users_text else 0
        if user_count > 0:
            flow_strength = min(1.0, 0.2 + min(user_count, 250) / 250 + product_motion * 0.25)
            flow_rect = pygame.Rect(rect.left + 14, rect.bottom - 18, max(34, rect.width - 96), 8)
            for index in range(5):
                ratio = ((phase * 0.28) + index / 5) % 1.0
                node_x = flow_rect.left + int(flow_rect.width * ratio)
                node_y = flow_rect.centery + int(sin(phase + index * 0.7) * 2)
                pygame.draw.circle(
                    surface,
                    blend_color(INFO, GOOD, flow_strength * 0.5),
                    (node_x, node_y),
                    2,
                )

    def _draw_stat_drama_effect(
        self,
        surface,
        gauge,
        bar_rect,
        gauge_motion: float,
        index: int,
    ) -> None:
        if self.motion_mode is MotionMode.OFF:
            return
        if gauge.key not in {"cash", "runway", "board_pressure"}:
            return
        risk_active = gauge.tone in {"warning", "danger"} or gauge.ratio <= 0.28
        if not risk_active:
            return
        pygame = self.pygame
        color = tone_color("danger" if gauge.tone == "danger" else "warning")
        phase = self._entity_motion_phase(offset=index * 1.3, speed=2.7)
        beacon = (sin(phase) + 1.0) / 2.0
        strength = 0.34 + beacon * 0.42 + min(0.28, gauge_motion * 0.28)
        alert_rect = pygame.Rect(
            bar_rect.left - 6,
            bar_rect.top - 6,
            bar_rect.width + 12,
            bar_rect.height + 12,
        )
        pygame.draw.rect(
            surface,
            blend_color(BORDER, color, strength * 0.65),
            alert_rect,
            width=2,
            border_radius=10,
        )
        for marker_index in range(3):
            marker_x = bar_rect.right - 8 - marker_index * 14
            marker_y = bar_rect.top - 5 + int(sin(phase + marker_index * 0.9) * 2)
            points = (
                (marker_x, marker_y),
                (marker_x + 7, marker_y + 11),
                (marker_x - 7, marker_y + 11),
            )
            pygame.draw.polygon(surface, blend_color(color, TEXT, strength * 0.18), points)

    def _draw_event_card(self, surface, rect, timed_event: TimedFrontendEvent) -> None:
        pygame = self.pygame
        color = tone_color(timed_event.payload.severity)
        event_motion = self._motion_level("feed", *timed_event.payload.targets)
        event_age = max(0.0, timed_event.payload.ttl - timed_event.time_left)
        enter_duration = 0.3 if timed_event.payload.motion == "slide" else 0.2
        enter_ratio = min(1.0, event_age / enter_duration) if enter_duration > 0 else 1.0
        slide_x = int((1.0 - enter_ratio) * 18)
        lift = int((1.0 - enter_ratio) * 5 + event_motion * 2)
        visual_rect = pygame.Rect(rect.left + slide_x, rect.top - lift, rect.width, rect.height)
        fill = blend_color((26, 38, 55), color, min(0.22, event_motion * 0.18))
        border = blend_color(color, TEXT, event_motion * 0.16)
        pygame.draw.rect(surface, fill, visual_rect, border_radius=14)
        pygame.draw.rect(
            surface,
            border,
            visual_rect,
            width=2 if event_motion >= 0.45 else 1,
            border_radius=14,
        )
        draw_text_line(
            surface,
            self.fonts.body,
            timed_event.payload.title,
            TEXT,
            pygame.Rect(visual_rect.left + 12, visual_rect.top + 8, visual_rect.width - 24, 22),
            valign="top",
        )
        draw_wrapped_text(
            surface,
            self.fonts.small,
            timed_event.payload.detail,
            MUTED,
            pygame.Rect(
                visual_rect.left + 12,
                visual_rect.top + 30,
                visual_rect.width - 24,
                visual_rect.height - 36,
            ),
            line_height=15,
            max_lines=1 if visual_rect.width < 320 else 2,
        )
        ttl_ratio = timed_event.time_left / timed_event.payload.ttl
        draw_progress_bar(
            surface,
            pygame,
            pygame.Rect(visual_rect.left + 12, visual_rect.bottom - 10, visual_rect.width - 24, 5),
            ratio=ttl_ratio,
            color=color,
            emphasis=event_motion,
        )

    def _draw_pending_event_overlay(self, surface) -> None:
        pygame = self.pygame
        event_model = self._view_model.pending_event
        if event_model is None:
            return
        overlay_motion = self._overlay_motion_level("pending")
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(self._overlay_fill("pending"))
        surface.blit(overlay, (0, 0))
        modal_height = min(360, max(284, 170 + len(event_model.options) * 64))
        modal_rect = _fit_modal_rect(pygame, surface, width=560, height=modal_height, margin=24)
        modal_rect = self._animated_overlay_rect(modal_rect, "pending", shift=28)
        inner = draw_panel(
            surface,
            pygame,
            modal_rect,
            title="Pending Event",
            accent=WARN,
            emphasis=overlay_motion,
            lift=int(overlay_motion * 5),
        )
        title_surface = self.fonts.title.render(event_model.title, True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 26))
        draw_wrapped_text(
            surface,
            self.fonts.body,
            event_model.description,
            MUTED,
            pygame.Rect(inner.left, inner.top, inner.width, 72),
            line_height=18,
            max_lines=4,
        )
        top = inner.top + 92
        for index, option in enumerate(event_model.options):
            option_rect = pygame.Rect(inner.left, top, inner.width, 54)
            option_tone = self._pending_option_tone(option.label, option.description)
            option_accent = tone_color(option_tone)
            option_motion = self._motion_level("overlay:pending", f"pending:option:{index}")
            draw_button(
                surface,
                pygame,
                rect=option_rect,
                title=f"{option.key_hint} {option.label}",
                detail=option.description,
                accent=option_accent,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
                selected=index == 0,
                emphasis=option_motion,
            )
            self._draw_pending_option_preview(
                surface,
                option_rect,
                tone=option_tone,
                strength=max(0.22, option_motion),
                index=index,
            )
            self._click_targets.append(ClickTarget("pending_option", str(index), option_rect))
            top += 64

    def _draw_context_picker_overlay(self, surface) -> None:
        pygame = self.pygame
        picker = self._context_picker
        if picker is None:
            return
        overlay_motion = self._overlay_motion_level("picker")
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(self._overlay_fill("picker"))
        surface.blit(overlay, (0, 0))
        modal_height = 180 + len(picker.options) * 64
        modal_rect = _fit_modal_rect(pygame, surface, width=600, height=modal_height, margin=24)
        modal_rect = self._animated_overlay_rect(modal_rect, "picker")
        inner = draw_panel(
            surface,
            pygame,
            modal_rect,
            title="Action Picker",
            accent=tone_color(picker.severity),
            emphasis=overlay_motion,
            lift=int(overlay_motion * 5),
        )
        title_surface = self.fonts.title.render(picker.title, True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 28))
        draw_wrapped_text(
            surface,
            self.fonts.body,
            picker.description,
            MUTED,
            pygame.Rect(inner.left, inner.top, inner.width, 54),
            line_height=18,
            max_lines=3,
        )
        top = inner.top + 68
        for index, option in enumerate(picker.options):
            option_rect = pygame.Rect(inner.left, top, inner.width, 54)
            draw_button(
                surface,
                pygame,
                rect=option_rect,
                title=f"{option.key_hint} {option.title}",
                detail=option.description,
                accent=tone_color(picker.severity),
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
            )
            self._click_targets.append(ClickTarget("picker_option", str(index), option_rect))
            top += 64
        close_rect = pygame.Rect(inner.left, modal_rect.bottom - 54, 140, 34)
        draw_button(
            surface,
            pygame,
            rect=close_rect,
            title="Esc Close",
            detail="Back to the run.",
            accent=BORDER,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        self._click_targets.append(ClickTarget("close_picker", "", close_rect))

    def _draw_text_input_overlay(self, surface) -> None:
        pygame = self.pygame
        modal = self._text_input
        if modal is None:
            return
        overlay_motion = self._overlay_motion_level("text_input")
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(self._overlay_fill("text_input"))
        surface.blit(overlay, (0, 0))
        modal_rect = _fit_modal_rect(pygame, surface, width=600, height=280, margin=24)
        modal_rect = self._animated_overlay_rect(modal_rect, "text_input")
        inner = draw_panel(
            surface,
            pygame,
            modal_rect,
            title="Text Input",
            accent=tone_color(modal.severity),
            emphasis=overlay_motion,
            lift=int(overlay_motion * 5),
        )
        title_surface = self.fonts.title.render(modal.title, True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 28))
        draw_wrapped_text(
            surface,
            self.fonts.body,
            modal.description,
            MUTED,
            pygame.Rect(inner.left, inner.top, inner.width, 40),
            line_height=18,
            max_lines=2,
        )
        input_rect = pygame.Rect(inner.left, inner.top + 60, inner.width, 48)
        pygame.draw.rect(surface, (24, 35, 50), input_rect, border_radius=14)
        pygame.draw.rect(surface, tone_color(modal.severity), input_rect, width=1, border_radius=14)
        input_text = modal.text or modal.placeholder
        input_color = TEXT if modal.text else MUTED
        input_surface = self.fonts.body.render(input_text, True, input_color)
        surface.blit(input_surface, (input_rect.left + 12, input_rect.top + 14))
        cursor_x = input_rect.left + 12 + input_surface.get_width() + 2
        pygame.draw.line(
            surface,
            tone_color(modal.severity),
            (cursor_x, input_rect.top + 10),
            (cursor_x, input_rect.bottom - 10),
            2,
        )
        submit_rect = pygame.Rect(inner.left, inner.top + 134, 220, 40)
        cancel_rect = pygame.Rect(inner.left + 236, inner.top + 134, 180, 40)
        draw_button(
            surface,
            pygame,
            rect=submit_rect,
            title=modal.submit_title,
            detail=modal.submit_detail,
            accent=tone_color(modal.severity),
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        draw_button(
            surface,
            pygame,
            rect=cancel_rect,
            title="Esc Cancel",
            detail="Close without applying changes.",
            accent=BORDER,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        self._click_targets.append(ClickTarget("submit_text", "", submit_rect))
        self._click_targets.append(ClickTarget("cancel_text", "", cancel_rect))

    def _draw_deep_panel_overlay(self, surface) -> None:
        pygame = self.pygame
        panel = self.deep_panel
        if panel is None:
            return
        disclosure = build_panel_disclosure(
            panel,
            expanded=self._endgame_actions_expanded,
        )
        guided_endgame = panel.key == "endgame" and not self._endgame_actions_expanded
        overlay_motion = self._overlay_motion_level("panel")
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(self._overlay_fill("panel"))
        surface.blit(overlay, (0, 0))
        modal_rect = _fit_nav_safe_modal_rect(
            pygame,
            surface,
            width=940,
            height=500 if guided_endgame else 560,
            margin=24,
        )
        modal_rect = self._animated_overlay_rect(modal_rect, "panel", shift=38)
        panel_motion = self._motion_level(f"panel:{panel.key}")
        inner = draw_panel(
            surface,
            pygame,
            modal_rect,
            title=panel.title,
            accent=INFO,
            emphasis=max(panel_motion, overlay_motion),
            lift=int(max(panel_motion, overlay_motion) * 5),
        )
        title_rect = pygame.Rect(
            inner.left,
            inner.top - 28,
            inner.width,
            self.fonts.title.get_height(),
        )
        title_surface = self.fonts.title.render(panel.title, True, TEXT)
        surface.blit(title_surface, title_rect.topleft)
        self._record_layout_separation(
            "deep-panel-title-vs-nav",
            title_rect,
            pygame.Rect(0, 0, surface.get_width(), 54),
        )
        self._draw_panel_entity_strip(
            surface,
            pygame.Rect(inner.right - 190, inner.top - 30, 190, 28),
            panel_key=panel.key,
            strength=self._entity_motion_strength(f"panel:{panel.key}", "overlay:panel"),
        )
        if panel.key == "endgame":
            self._draw_overlay_actor_sprite_layer(
                surface,
                inner,
                clips=self._endgame_actor_sprite_clips(),
                strength=self._actor_sprite_strength("panel:endgame", "overlay:panel"),
            )
        draw_wrapped_text(
            surface,
            self.fonts.body,
            panel.summary,
            MUTED,
            pygame.Rect(inner.left, inner.top, inner.width, 40),
            line_height=18,
            max_lines=2,
        )
        metric_top = inner.top + 54
        metric_width = int((inner.width - 24) / 2)
        metric_card_rects = []
        for index, metric in enumerate(panel.metrics[:4]):
            row = index // 2
            col = index % 2
            card_rect = pygame.Rect(
                inner.left + col * (metric_width + 12),
                metric_top + row * 54,
                metric_width,
                42,
            )
            metric_card_rects.append(card_rect)
            pygame.draw.rect(surface, (26, 38, 55), card_rect, border_radius=12)
            pygame.draw.rect(
                surface,
                tone_color(metric.tone),
                card_rect,
                width=1,
                border_radius=12,
            )
            label_surface = self.fonts.small.render(metric.label.upper(), True, MUTED)
            value_surface = self.fonts.body.render(metric.value_text, True, TEXT)
            surface.blit(label_surface, (card_rect.left + 10, card_rect.top + 6))
            surface.blit(value_surface, (card_rect.left + 10, card_rect.top + 20))

        metric_bottom = (
            max(card_rect.bottom for card_rect in metric_card_rects)
            if metric_card_rects
            else metric_top
        )
        heading_top = metric_bottom + 10
        heading_height = 24
        content_top = heading_top + heading_height
        footer_top = inner.bottom - 40
        content_bottom = footer_top - 12
        content_height = max(80, content_bottom - content_top)
        detail_rect = pygame.Rect(
            inner.left,
            content_top,
            int(inner.width * 0.54),
            content_height,
        )
        action_rect = pygame.Rect(
            detail_rect.right + 20,
            content_top,
            inner.right - detail_rect.right - 20,
            content_height,
        )
        detail_title_rect = pygame.Rect(
            detail_rect.left,
            heading_top,
            detail_rect.width,
            heading_height,
        )
        detail_title = self.fonts.heading.render("Live Notes", True, TEXT)
        surface.blit(detail_title, detail_title_rect.topleft)
        top = detail_rect.top
        for line in disclosure.detail_lines:
            consumed = draw_wrapped_text(
                surface,
                self.fonts.small,
                line,
                MUTED,
                pygame.Rect(detail_rect.left, top, detail_rect.width, 38),
                line_height=16,
                max_lines=2,
            )
            top += max(26, consumed)

        action_title_rect = pygame.Rect(
            action_rect.left,
            heading_top,
            action_rect.width,
            heading_height,
        )
        action_title = self.fonts.heading.render(disclosure.action_heading, True, TEXT)
        surface.blit(action_title, action_title_rect.topleft)
        if metric_card_rects:
            self._record_layout_separation(
                "panel-metrics-vs-section-headings",
                metric_card_rects[0].unionall(metric_card_rects[1:]),
                detail_title_rect.union(action_title_rect),
            )
        cols = 1 if guided_endgame else 2
        button_gap = 10
        button_width = int((action_rect.width - button_gap * (cols - 1)) / cols)
        action_rows = max(1, (len(disclosure.actions) + cols - 1) // cols)
        button_height = min(
            68 if guided_endgame else 54,
            max(
                34,
                int((action_rect.height - button_gap * (action_rows - 1)) / action_rows),
            ),
        )
        top = action_rect.top
        left = action_rect.left
        action_button_rects = []
        for index, action in enumerate(disclosure.actions):
            if index and index % cols == 0:
                top += button_height + button_gap
                left = action_rect.left
            button_left = left
            if index == len(disclosure.actions) - 1 and len(disclosure.actions) % cols:
                button_left = action_rect.centerx - button_width // 2
            button_rect = pygame.Rect(button_left, top, button_width, button_height)
            action_button_rects.append(button_rect)
            enabled = self._command_disabled_reason(action.command) is None
            draw_button(
                surface,
                pygame,
                rect=button_rect,
                title=action.label,
                detail=self._overlay_button_detail(action.command, action.detail, enabled=enabled),
                accent=tone_color(action.tone),
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
                enabled=enabled,
            )
            self._click_targets.append(ClickTarget("panel_action", action.command, button_rect))
            left += button_width + button_gap

        footer_gap = 8
        footer_controls: list[tuple[str, str, str, str, tuple[int, int, int]]] = []
        if disclosure.toggle_label:
            footer_controls.append(
                (
                    "endgame_actions_toggle",
                    "",
                    disclosure.toggle_label,
                    disclosure.toggle_detail,
                    WARN if not self._endgame_actions_expanded else INFO,
                )
            )
        if panel.inspectors:
            footer_controls.append(
                (
                    "open_panel_inspector",
                    panel.key,
                    "I Inspector",
                    "Inspect this panel in detail.",
                    SELECTION,
                )
            )
        footer_controls.append(("close_panel", "", "Esc Close", "Return to the run.", BORDER))
        footer_button_rects = []
        footer_button_width = int(
            (action_rect.width - footer_gap * (len(footer_controls) - 1)) / len(footer_controls)
        )
        footer_left = action_rect.left
        for index, (kind, payload, title, detail, accent) in enumerate(footer_controls):
            width = (
                action_rect.right - footer_left
                if index == len(footer_controls) - 1
                else footer_button_width
            )
            footer_rect = pygame.Rect(footer_left, footer_top, width, 34)
            footer_button_rects.append(footer_rect)
            draw_button(
                surface,
                pygame,
                rect=footer_rect,
                title=title,
                detail=detail,
                accent=accent,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
            )
            self._click_targets.append(ClickTarget(kind, payload, footer_rect))
            footer_left = footer_rect.right + footer_gap
        if action_button_rects:
            self._record_layout_separation(
                "panel-actions-vs-footer",
                action_button_rects[0].unionall(action_button_rects[1:]),
                footer_button_rects[0].unionall(footer_button_rects[1:]),
            )

    def _draw_inspector_overlay(self, surface) -> None:
        pygame = self.pygame
        panel = self.inspector_panel
        if panel is None:
            return
        overlay_motion = self._overlay_motion_level("inspector")
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(self._overlay_fill("inspector"))
        surface.blit(overlay, (0, 0))
        modal_rect = _fit_nav_safe_modal_rect(
            pygame,
            surface,
            width=1040,
            height=600,
            margin=24,
        )
        modal_rect = self._animated_overlay_rect(modal_rect, "inspector", shift=42)
        panel_motion = self._motion_level(f"panel:{panel.key}")
        inspector_motion = self._motion_level(
            "inspector:section",
            "inspector:item",
            "inspector:page",
            "inspector:sort",
            "inspector:filter",
            "inspector:actionable",
            "inspector:hotspot",
        )
        inner = draw_panel(
            surface,
            pygame,
            modal_rect,
            title=panel.title,
            accent=SELECTION,
            emphasis=max(panel_motion, overlay_motion, inspector_motion),
            lift=int(max(panel_motion, overlay_motion, inspector_motion) * 5),
        )
        viewport_width, _viewport_height = surface.get_size()
        actor_reserve = 0
        if self.inspector_actor_active():
            actor_width = 124 if viewport_width >= 1040 else 108
            # Keep header copy out of the actor chip's visual lane on compact overlays.
            actor_reserve = actor_width + 20
        header_text_width = max(220, inner.width - actor_reserve)
        title_rect = pygame.Rect(
            inner.left,
            inner.top - 28,
            header_text_width,
            self.fonts.title.get_height(),
        )
        title_surface = self.fonts.title.render(
            fit_text_line(self.fonts.title, f"{panel.title} Inspector", header_text_width),
            True,
            TEXT,
        )
        surface.blit(title_surface, title_rect.topleft)
        self._record_layout_separation(
            "inspector-title-vs-nav",
            title_rect,
            pygame.Rect(0, 0, surface.get_width(), 54),
        )
        self._draw_overlay_actor_sprite_layer(
            surface,
            inner,
            clips=self._inspector_actor_sprite_clips(),
            strength=self._actor_sprite_strength(f"panel:{panel.key}", "overlay:inspector"),
        )
        draw_wrapped_text(
            surface,
            self.fonts.body,
            panel.summary,
            MUTED,
            pygame.Rect(inner.left, inner.top, header_text_width, 42),
            line_height=18,
            max_lines=2,
        )
        metric_top = inner.top + 58
        metric_width = int((inner.width - 36) / 4)
        for index, metric in enumerate(panel.metrics[:4]):
            card_rect = pygame.Rect(
                inner.left + index * (metric_width + 12),
                metric_top,
                metric_width,
                52,
            )
            pygame.draw.rect(surface, (26, 38, 55), card_rect, border_radius=12)
            pygame.draw.rect(
                surface,
                tone_color(metric.tone),
                card_rect,
                width=1,
                border_radius=12,
            )
            label_surface = self.fonts.small.render(metric.label.upper(), True, MUTED)
            value_surface = self.fonts.body.render(metric.value_text, True, TEXT)
            surface.blit(label_surface, (card_rect.left + 10, card_rect.top + 8))
            surface.blit(value_surface, (card_rect.left + 10, card_rect.top + 26))

        nav_top = metric_top + 76
        nav_width = 250
        nav_rect = pygame.Rect(inner.left, nav_top, nav_width, inner.bottom - nav_top)
        focus_rect = pygame.Rect(
            nav_rect.right + 18,
            nav_top,
            inner.right - nav_rect.right - 18,
            inner.bottom - nav_top - 56,
        )
        self._draw_inspector_section_nav(surface, nav_rect, panel)
        self._draw_inspector_focus(surface, focus_rect)

        close_rect = pygame.Rect(inner.right - 180, modal_rect.bottom - 56, 180, 34)
        draw_button(
            surface,
            pygame,
            rect=close_rect,
            title="Esc Close Inspector",
            detail=self._inspector_hint_line(),
            accent=BORDER,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        self._click_targets.append(ClickTarget("close_inspector", "", close_rect))

    def _draw_inspector_section_nav(self, surface, rect, panel: DeepDivePanelViewModel) -> None:
        pygame = self.pygame
        nav_inner = draw_panel(surface, pygame, rect, title="Sections", accent=INFO)
        title_surface = self.fonts.heading.render("Sections", True, TEXT)
        surface.blit(title_surface, (nav_inner.left, nav_inner.top - 24))
        compact_nav = nav_inner.height < 300
        control_height = 34 if compact_nav else 40
        control_gap = 8
        sort_rect = pygame.Rect(
            nav_inner.left,
            nav_inner.top,
            nav_inner.width,
            control_height,
        )
        filter_rect = pygame.Rect(
            nav_inner.left,
            sort_rect.bottom + control_gap,
            nav_inner.width,
            control_height,
        )
        draw_button(
            surface,
            pygame,
            rect=sort_rect,
            title=f"Z Sort: {self._inspector_sort_mode_label()}",
            detail="Cycle ranking for the current section.",
            accent=INFO,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        draw_button(
            surface,
            pygame,
            rect=filter_rect,
            title=f"X Filter: {self._inspector_filter_mode_label()}",
            detail="Cycle between all, actionable, and attention items.",
            accent=WARN,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        self._click_targets.append(ClickTarget("inspector_cycle_sort", "", sort_rect))
        self._click_targets.append(ClickTarget("inspector_cycle_filter", "", filter_rect))
        action_width = int((nav_inner.width - 10) / 2)
        actionable_rect = pygame.Rect(
            nav_inner.left,
            filter_rect.bottom + control_gap,
            action_width,
            control_height,
        )
        hotspot_rect = pygame.Rect(
            actionable_rect.right + 10,
            actionable_rect.top,
            nav_inner.width - action_width - 10,
            control_height,
        )
        draw_button(
            surface,
            pygame,
            rect=actionable_rect,
            title="A Actionable",
            detail="Jump to rows with ready actions.",
            accent=GOOD,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        draw_button(
            surface,
            pygame,
            rect=hotspot_rect,
            title="H Hotspot",
            detail="Focus the highest-risk attention rows.",
            accent=DANGER,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        self._click_targets.append(ClickTarget("inspector_focus_actionable", "", actionable_rect))
        self._click_targets.append(ClickTarget("inspector_focus_hotspot", "", hotspot_rect))
        top = actionable_rect.bottom + (10 if compact_nav else 12)
        section_count = max(1, len(panel.inspectors))
        section_area_height = max(0, nav_inner.bottom - top)
        section_gap = 0
        if section_count > 1:
            available_gap = max(0, section_area_height - section_count * 32)
            section_gap = min(8 if compact_nav else 10, available_gap // (section_count - 1))
        section_height = max(
            32,
            min(
                56,
                int(
                    (section_area_height - section_gap * max(0, section_count - 1)) / section_count
                ),
            ),
        )
        compact_sections = section_height < 44
        for index, section in enumerate(panel.inspectors):
            button_rect = pygame.Rect(nav_inner.left, top, nav_inner.width, section_height)
            selected = index == self._inspector_section_index
            accent = SELECTION if selected else tone_color(section.tone)
            draw_button(
                surface,
                pygame,
                rect=button_rect,
                title=section.title,
                detail=(
                    ""
                    if compact_sections
                    else self._section_button_detail(section, selected=selected)
                ),
                accent=accent,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
            )
            self._click_targets.append(ClickTarget("inspector_section", section.key, button_rect))
            top += section_height + section_gap

    def _draw_inspector_focus(self, surface, rect) -> None:
        pygame = self.pygame
        section = self._selected_inspector_section()
        focus_inner = draw_panel(
            surface,
            pygame,
            rect,
            title="Records",
            accent=SELECTION if section is not None else BORDER,
        )
        if section is None:
            idle_surface = self.fonts.body.render("No inspector section selected.", True, MUTED)
            surface.blit(idle_surface, (focus_inner.left, focus_inner.top))
            return
        filtered_items = self._filtered_sorted_inspector_items()
        if not filtered_items:
            draw_wrapped_text(
                surface,
                self.fonts.body,
                "No records match this filter. Press X to cycle filters or A/H to refocus.",
                MUTED,
                pygame.Rect(focus_inner.left, focus_inner.top, focus_inner.width, 54),
                line_height=18,
                max_lines=3,
            )
            return

        title_surface = self.fonts.heading.render(section.title, True, TEXT)
        surface.blit(title_surface, (focus_inner.left, focus_inner.top - 24))
        page_items = self._current_inspector_page_items()
        page_start = self._current_inspector_page_start()
        page_total = self._inspector_total_pages()
        header_rect = pygame.Rect(focus_inner.left, focus_inner.top, focus_inner.width, 24)
        draw_wrapped_text(
            surface,
            self.fonts.small,
            (
                f"Page {self._inspector_page + 1}/{page_total} | "
                f"items {page_start + 1}-{page_start + len(page_items)} of {len(filtered_items)}"
            ),
            MUTED,
            header_rect,
            line_height=16,
            max_lines=1,
        )
        compact_footer = focus_inner.width < 560
        item_area_height = focus_inner.height - (224 if compact_footer else 172)
        item_gap = 10
        item_height = max(
            72,
            int(
                (item_area_height - item_gap * max(0, len(page_items) - 1))
                / max(1, len(page_items))
            ),
        )
        top = focus_inner.top + 30
        for relative_index, item in enumerate(page_items):
            absolute_index = page_start + relative_index
            selected = relative_index == self._inspector_item_index
            item_rect = pygame.Rect(focus_inner.left, top, focus_inner.width, item_height)
            detail_line_limit = self._inspector_item_line_limit(item_height, focus_inner.width)
            fill = (
                blend_color((26, 38, 55), tone_color(item.tone), 0.18) if selected else (26, 38, 55)
            )
            pygame.draw.rect(surface, fill, item_rect, border_radius=12)
            pygame.draw.rect(
                surface,
                SELECTION if selected else tone_color(item.tone),
                item_rect,
                width=2 if selected else 1,
                border_radius=12,
            )
            self._click_targets.append(
                ClickTarget("inspector_item", str(absolute_index), item_rect)
            )
            item_title = self.fonts.small.render(
                f"{absolute_index + 1}. {item.title}",
                True,
                TEXT,
            )
            surface.blit(item_title, (item_rect.left + 10, item_rect.top + 8))
            if selected:
                badge_rect = pygame.Rect(item_rect.right - 82, item_rect.top + 8, 72, 18)
                pygame.draw.rect(surface, (30, 54, 76), badge_rect, border_radius=9)
                pygame.draw.rect(surface, SELECTION, badge_rect, width=1, border_radius=9)
                badge_surface = self.fonts.small.render("ACTIVE", True, SELECTION)
                surface.blit(badge_surface, (badge_rect.left + 10, badge_rect.top + 2))
                action_badge = self._inspector_item_action_badge(item)
                if action_badge is not None:
                    label, accent = action_badge
                    status_rect = pygame.Rect(item_rect.right - 170, item_rect.top + 8, 78, 18)
                    pygame.draw.rect(
                        surface,
                        blend_color((24, 35, 50), accent, 0.2),
                        status_rect,
                        border_radius=9,
                    )
                    pygame.draw.rect(surface, accent, status_rect, width=1, border_radius=9)
                    status_surface = self.fonts.small.render(label, True, accent)
                    surface.blit(status_surface, (status_rect.left + 8, status_rect.top + 2))
            line_top = item_rect.top + 28
            for line in item.detail_lines[:detail_line_limit]:
                consumed = draw_wrapped_text(
                    surface,
                    self.fonts.small,
                    line,
                    MUTED,
                    pygame.Rect(item_rect.left + 10, line_top, item_rect.width - 20, 18),
                    line_height=14,
                    max_lines=1,
                )
                line_top += max(16, consumed)
            if selected and item.actions and item_height >= 86:
                action_summary = " | ".join(
                    f"{index + 1}:{action.label}" for index, action in enumerate(item.actions[:4])
                )
                summary_surface = self.fonts.small.render(action_summary, True, INFO)
                surface.blit(summary_surface, (item_rect.left + 10, item_rect.bottom - 18))
            top += item_height + item_gap

        selected_item = self._selected_inspector_item()
        footer_top = rect.bottom - (108 if compact_footer else 72)
        focus_note_height = 18 if compact_footer else 30
        focus_note_rect = pygame.Rect(
            focus_inner.left,
            footer_top - focus_note_height - 10,
            focus_inner.width,
            focus_note_height,
        )
        if selected_item is not None and not compact_footer:
            draw_wrapped_text(
                surface,
                self.fonts.small,
                self._inspector_focus_summary_text(selected_item, compact=False),
                MUTED,
                focus_note_rect,
                line_height=15,
                max_lines=2,
            )
        footer_rect = pygame.Rect(
            focus_inner.left,
            footer_top,
            focus_inner.width,
            94 if compact_footer else 62,
        )
        action_left = footer_rect.left
        if page_total > 1:
            prev_rect = pygame.Rect(footer_rect.left, footer_rect.top, 120, 36)
            next_rect = pygame.Rect(footer_rect.left + 132, footer_rect.top, 120, 36)
            draw_button(
                surface,
                pygame,
                rect=prev_rect,
                title="PgUp Prev",
                detail="" if compact_footer else "Previous page.",
                accent=BORDER,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
            )
            draw_button(
                surface,
                pygame,
                rect=next_rect,
                title="PgDn Next",
                detail="" if compact_footer else "Next page.",
                accent=BORDER,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
            )
            self._click_targets.append(ClickTarget("inspector_prev_page", "", prev_rect))
            self._click_targets.append(ClickTarget("inspector_next_page", "", next_rect))
            action_left = next_rect.right + 16
        if selected_item is None or not selected_item.actions:
            note_surface = self.fonts.small.render(
                "No item-level actions are wired for this record.",
                True,
                MUTED,
            )
            surface.blit(note_surface, (action_left, footer_rect.top + 10))
            return

        action_count = min(3, len(selected_item.actions))
        available_width = footer_rect.right - action_left
        action_width = int((available_width - 12 * max(0, action_count - 1)) / action_count)
        left = action_left
        for index, action in enumerate(selected_item.actions[:3]):
            button_rect = pygame.Rect(left, footer_rect.top, action_width, 40)
            enabled = (
                self._inspector_item_action_reason(action.command, selected_item.payload) is None
            )
            draw_button(
                surface,
                pygame,
                rect=button_rect,
                title=f"{index + 1} {action.label}",
                detail=(
                    ""
                    if compact_footer
                    else self._item_action_detail(
                        action.command,
                        selected_item.payload,
                        action.detail,
                        enabled=enabled,
                    )
                ),
                accent=tone_color(action.tone),
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
                enabled=enabled,
            )
            self._click_targets.append(
                ClickTarget("inspector_item_action", str(index), button_rect)
            )
            left += action_width + 12

    def _section_button_detail(self, section, *, selected: bool) -> str:
        state = "active focus" if selected else "click to focus"
        return f"{len(section.items)} records | {state}"

    def _inspector_item_action_badge(self, item) -> tuple[str, tuple[int, int, int]] | None:
        if not item.actions:
            return None
        action = item.actions[0]
        reason = self._inspector_item_action_reason(action.command, item.payload)
        if reason is None:
            return ("READY", GOOD)
        return ("BLOCKED", WARN)

    def _inspector_sort_mode_label(self) -> str:
        labels = {
            "default": "Default",
            "risk": "Highest Risk",
            "value": "Biggest Value",
            "stalled": "Most Stalled",
        }
        return labels[_INSPECTOR_SORT_MODES[self._inspector_sort_mode_index]]

    def _inspector_filter_mode_label(self) -> str:
        labels = {
            "all": "All",
            "actionable": "Actionable",
            "attention": "Attention",
        }
        return labels[_INSPECTOR_FILTER_MODES[self._inspector_filter_mode_index]]

    def _item_action_detail(
        self,
        command: str,
        payload: str,
        default_detail: str,
        *,
        enabled: bool,
    ) -> str:
        if enabled:
            return self._compact_button_detail(default_detail, max_length=26)
        reason = self._inspector_item_action_reason(command, payload)
        if reason is None:
            return self._compact_button_detail(default_detail, max_length=26)
        return self._compact_button_detail(reason, max_length=26)

    def _inspector_item_line_limit(self, item_height: int, focus_width: int) -> int:
        if item_height < 80 or focus_width < 500:
            return 1
        if item_height < 84 or focus_width < 560:
            return 2
        return 3

    def _inspector_focus_summary_text(self, item, *, compact: bool) -> str:
        detail_count = 1 if compact else 2
        focus_line = " | ".join(item.detail_lines[:detail_count]) or "No detail lines captured."
        next_line = self._selected_inspector_primary_action_summary()
        if next_line:
            focus_line = f"{focus_line} | {next_line}"
        if compact:
            focus_line = self._compact_button_detail(focus_line, max_length=88)
        return f"Focus: {item.title} | {focus_line}"

    def _inspector_hint_line(self) -> str:
        return "Tab/Arrows move | Z/X sort-filter | A/H focus | PgUp/PgDn page | Enter action"

    def _draw_pause_overlay(self, surface) -> None:
        pygame = self.pygame
        overlay_motion = self._overlay_motion_level("pause")
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(self._overlay_fill("pause"))
        surface.blit(overlay, (0, 0))
        modal_rect = _fit_modal_rect(pygame, surface, width=560, height=388, margin=26)
        modal_rect = self._animated_overlay_rect(modal_rect, "pause", shift=24)
        inner = draw_panel(
            surface,
            pygame,
            modal_rect,
            title="Pause",
            accent=WARN,
            emphasis=overlay_motion,
            lift=int(overlay_motion * 4),
        )
        draw_text_line(
            surface,
            self.fonts.title,
            "Game Paused",
            TEXT,
            pygame.Rect(inner.left, inner.top - 30, inner.width, 30),
            valign="top",
        )
        menu_available = self._return_scene_factory is not None
        detail = (
            f"Turn {self.state.company.current_turn} | Actions left "
            f"{self.state.action_points_remaining} | Slot {self.slot_name}"
        )
        draw_wrapped_text(
            surface,
            self.fonts.body,
            detail,
            MUTED,
            pygame.Rect(inner.left, inner.top, inner.width, 24),
            line_height=18,
            max_lines=1,
        )
        draw_wrapped_text(
            surface,
            self.fonts.small,
            (
                "Use P or Esc to resume. Save before leaving if you want to keep the current "
                "run state. Menu is available when the run was launched from the 2D title shell."
            ),
            TEXT,
            pygame.Rect(inner.left, inner.top + 34, inner.width, 52),
            line_height=17,
            max_lines=3,
        )
        button_top = inner.top + 106
        button_gap = 12
        button_height = 46
        button_width = int((inner.width - button_gap) / 2)
        buttons = (
            ("Resume", "Return to the run.", "pause_resume", "", GOOD, True),
            ("S Save", "Persist the run.", "pause_save", "", INFO, True),
            (
                "M Menu" if menu_available else "Menu Unavailable",
                "Save and return to title."
                if menu_available
                else "Direct play has no title shell.",
                "pause_menu",
                "",
                WARN,
                menu_available,
            ),
            (
                "T Settings",
                "Text, contrast, motion, and action loadout.",
                "pause_settings",
                "",
                SELECTION,
                True,
            ),
            ("Q Quit", "Close the 2D shell.", "pause_quit", "", DANGER, True),
        )
        for index, (title, button_detail, kind, payload, accent, enabled) in enumerate(buttons):
            row = index // 2
            col = index % 2
            left = inner.left + col * (button_width + button_gap)
            if index == len(buttons) - 1 and len(buttons) % 2:
                left = inner.centerx - button_width // 2
            rect = pygame.Rect(
                left,
                button_top + row * (button_height + button_gap),
                button_width,
                button_height,
            )
            draw_button(
                surface,
                pygame,
                rect=rect,
                title=title,
                detail=button_detail,
                accent=accent,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
                enabled=enabled,
            )
            if enabled:
                self._click_targets.append(ClickTarget(kind, payload, rect))

    def _draw_pause_settings_overlay(self, surface) -> None:
        pygame = self.pygame
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(self._overlay_fill("pause_settings"))
        surface.blit(overlay, (0, 0))
        modal_rect = _fit_modal_rect(pygame, surface, width=560, height=440, margin=26)
        modal_rect = self._animated_overlay_rect(modal_rect, "pause_settings", shift=24)
        self._draw_frontend_settings_panel(
            surface,
            modal_rect,
            target_prefix="pause_settings",
            back_kind="pause_settings_back",
            panel_title="Paused Settings",
        )

    def _draw_help_overlay(self, surface) -> None:
        pygame = self.pygame
        overlay_motion = self._overlay_motion_level("help")
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay_fill = self._overlay_fill("help")
        # Dim the live header without making the motion-off backdrop unreadably dark.
        overlay.fill((*overlay_fill[:3], max(206, overlay_fill[3])))
        surface.blit(overlay, (0, 0))
        modal_rect = _fit_nav_safe_modal_rect(
            pygame,
            surface,
            width=860,
            height=580,
            margin=28,
        )
        modal_rect = self._animated_overlay_rect(modal_rect, "help", shift=30)
        inner = draw_panel(
            surface,
            pygame,
            modal_rect,
            title="Help",
            accent=INFO,
            emphasis=overlay_motion,
            lift=int(overlay_motion * 5),
        )
        title_rect = pygame.Rect(
            inner.left,
            inner.top - 28,
            inner.width,
            self.fonts.title.get_height(),
        )
        title_surface = self.fonts.title.render("2D Control Guide", True, TEXT)
        surface.blit(title_surface, title_rect.topleft)
        self._record_layout_separation(
            "help-title-vs-nav",
            title_rect,
            pygame.Rect(0, 0, surface.get_width(), 54),
        )
        draw_wrapped_text(
            surface,
            self.fonts.body,
            (
                "This frontend is now self-contained for the main run loop. "
                "Use these controls to move between products, panels, inspectors, pause/menu, "
                "the endgame board, and turn resolution without dropping back to the CLI."
            ),
            MUTED,
            pygame.Rect(inner.left, inner.top, inner.width, 54),
            line_height=18,
            max_lines=3,
        )
        close_rect = pygame.Rect(inner.left, modal_rect.bottom - 56, 180, 36)
        keycap_top = inner.top + 76
        keycap_bottom = close_rect.top - 14
        keycap_height = 25
        two_columns = inner.width >= 620
        if two_columns:
            col_gap = 14
            rows = (len(RUN_HELP_KEYCAPS) + 1) // 2
            row_gap = max(5, min(8, (keycap_bottom - keycap_top - keycap_height * rows) // rows))
            col_width = int((inner.width - col_gap) / 2)
            for index, (key_text, label) in enumerate(RUN_HELP_KEYCAPS):
                col = index // rows
                row = index % rows
                keycap_rect = pygame.Rect(
                    inner.left + col * (col_width + col_gap),
                    keycap_top + row * (keycap_height + row_gap),
                    col_width,
                    keycap_height,
                )
                draw_keycap(
                    surface,
                    pygame,
                    self.fonts.small,
                    rect=keycap_rect,
                    key_text=key_text,
                    label=label,
                )
        else:
            row_gap = max(
                2,
                min(
                    6,
                    (keycap_bottom - keycap_top - keycap_height * len(RUN_HELP_KEYCAPS))
                    // max(1, len(RUN_HELP_KEYCAPS) - 1),
                ),
            )
            for index, (key_text, label) in enumerate(RUN_HELP_KEYCAPS):
                keycap_rect = pygame.Rect(
                    inner.left,
                    keycap_top + index * (keycap_height + row_gap),
                    inner.width,
                    keycap_height,
                )
                draw_keycap(
                    surface,
                    pygame,
                    self.fonts.small,
                    rect=keycap_rect,
                    key_text=key_text,
                    label=label,
                )
        draw_button(
            surface,
            pygame,
            rect=close_rect,
            title="Esc Close Help",
            detail="Return to the run dashboard.",
            accent=BORDER,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        self._click_targets.append(ClickTarget("close_help", "", close_rect))

    def _draw_outcome_overlay(self, surface) -> None:
        pygame = self.pygame
        overlay_motion = self._overlay_motion_level("outcome")
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(self._overlay_fill("outcome"))
        surface.blit(overlay, (0, 0))
        modal_rect = _fit_modal_rect(pygame, surface, width=560, height=300, margin=24)
        modal_rect = self._animated_overlay_rect(modal_rect, "outcome", shift=26)
        accent = GOOD if self.state.victory_achieved else DANGER
        self._draw_outcome_cinematic_backdrop(surface, modal_rect, accent)
        inner = draw_panel(
            surface,
            pygame,
            modal_rect,
            title="Run Complete",
            accent=accent,
            emphasis=max(0.32, overlay_motion),
            lift=int(overlay_motion * 4),
        )
        outcome = build_outcome_overlay_view_model(
            self.state,
            self._view_model,
            archive_saved=self._terminal_archive_saved,
        )
        title_surface = self.fonts.title.render(outcome.title, True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 26))
        draw_text_line(
            surface,
            self.fonts.small,
            outcome.eyebrow,
            accent,
            pygame.Rect(inner.left, inner.top + 4, inner.width, 16),
            valign="top",
        )
        draw_wrapped_text(
            surface,
            self.fonts.body,
            outcome.detail,
            MUTED,
            pygame.Rect(inner.left, inner.top + 24, inner.width, 54),
            line_height=18,
            max_lines=3,
        )
        metric_gap = 8
        metric_width = (inner.width - metric_gap * 2) // 3
        metric_top = inner.top + 104
        for index, metric in enumerate(outcome.metrics):
            metric_rect = pygame.Rect(
                inner.left + index * (metric_width + metric_gap),
                metric_top,
                metric_width,
                42,
            )
            metric_accent = tone_color(metric.tone)
            pygame.draw.rect(surface, PANEL, metric_rect, border_radius=12)
            pygame.draw.rect(surface, metric_accent, metric_rect, width=1, border_radius=12)
            draw_text_line(
                surface,
                self.fonts.small,
                metric.label,
                MUTED,
                pygame.Rect(metric_rect.left + 10, metric_rect.top + 4, metric_rect.width - 20, 14),
                valign="top",
            )
            draw_text_line(
                surface,
                self.fonts.body,
                metric.value,
                TEXT,
                pygame.Rect(
                    metric_rect.left + 10,
                    metric_rect.top + 20,
                    metric_rect.width - 20,
                    18,
                ),
                valign="top",
            )
        draw_text_line(
            surface,
            self.fonts.small,
            outcome.progression,
            GOOD,
            pygame.Rect(inner.left, inner.bottom - 72, inner.width, 18),
            valign="top",
        )
        review_rect = pygame.Rect(inner.left, inner.bottom - 46, 160, 36)
        save_rect = pygame.Rect(inner.left + 176, inner.bottom - 46, 160, 36)
        close_rect = pygame.Rect(inner.left + 352, inner.bottom - 46, 140, 36)
        draw_button(
            surface,
            pygame,
            rect=review_rect,
            title="Review Run",
            detail="Open the after-action scene.",
            accent=INFO,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        draw_button(
            surface,
            pygame,
            rect=save_rect,
            title="Archived" if self._terminal_archive_saved else "S Save & Archive",
            detail=(
                "Ending recorded for progression."
                if self._terminal_archive_saved
                else "Record this ending for progression."
            ),
            accent=BORDER if self._terminal_archive_saved else GOOD,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        draw_button(
            surface,
            pygame,
            rect=close_rect,
            title="Esc Exit" if self._terminal_archive_saved else "Esc Exit Unsaved",
            detail=(
                "Leave after the archive is recorded."
                if self._terminal_archive_saved
                else "Leave without archive progress."
            ),
            accent=INFO if self._terminal_archive_saved else accent,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        self._click_targets.append(ClickTarget("open_review", "", review_rect))
        if not self._terminal_archive_saved:
            self._click_targets.append(ClickTarget("save", "", save_rect))
        self._click_targets.append(ClickTarget("close_outcome", "", close_rect))

    def _draw_outcome_cinematic_backdrop(
        self,
        surface,
        modal_rect,
        accent: tuple[int, int, int],
    ) -> None:
        if not self.outcome_cinematic_active():
            return
        pygame = self.pygame
        width, height = surface.get_size()
        intensity = 0.52 if self.motion_mode is MotionMode.REDUCED else 1.0
        phase = self._entity_motion_phase(speed=1.4)
        rail_alpha = int(50 + intensity * 60)
        rail_top = max(24, modal_rect.top - 46)
        rail_bottom = min(height - 24, modal_rect.bottom + 46)
        left = max(24, modal_rect.left - 82)
        right = min(width - 24, modal_rect.right + 82)
        for index, y in enumerate((rail_top, rail_bottom)):
            progress = (sin(phase + index * 1.7) + 1.0) / 2
            sweep_width = max(70, int((right - left) * (0.2 + progress * 0.24)))
            sweep_x = left + int(((right - left) - sweep_width) * progress)
            base_rect = pygame.Rect(left, y, right - left, 5)
            sweep_rect = pygame.Rect(sweep_x, y, sweep_width, 5)
            pygame.draw.rect(
                surface,
                (*blend_color(BORDER, accent, 0.22), max(28, rail_alpha // 2)),
                base_rect,
                border_radius=4,
            )
            pygame.draw.rect(
                surface,
                (*accent, rail_alpha),
                sweep_rect,
                border_radius=4,
            )
        node_count = 5 if self.motion_mode is MotionMode.FULL else 3
        for index in range(node_count):
            ratio = (index + 1) / (node_count + 1)
            x = left + int((right - left) * ratio)
            drift = sin(phase * 1.3 + index * 0.9) * 8 * intensity
            y = modal_rect.centery + int(drift)
            radius = 3 + int(intensity * 2)
            pygame.draw.circle(
                surface,
                (*blend_color(accent, TEXT, 0.16), int(95 + intensity * 80)),
                (x, y),
                radius,
            )
            pygame.draw.circle(surface, (*accent, int(120 + intensity * 70)), (x, y), radius + 3, 1)
        status_text = "VICTORY PATH LOCKED" if self.state.victory_achieved else "SHUTDOWN REVIEW"
        badge = self.fonts.small.render(status_text, True, blend_color(TEXT, accent, 0.16))
        badge_rect = pygame.Rect(
            modal_rect.centerx - badge.get_width() // 2 - 12,
            max(18, modal_rect.top - 34),
            badge.get_width() + 24,
            24,
        )
        pygame.draw.rect(
            surface,
            (*blend_color((13, 22, 34), accent, 0.18), 220),
            badge_rect,
            border_radius=12,
        )
        pygame.draw.rect(surface, accent, badge_rect, width=1, border_radius=12)
        surface.blit(badge, (badge_rect.left + 12, badge_rect.top + 6))

    def _draw_snapshot_chip(self, surface, rect, label: str, value: str, tone: str) -> None:
        pygame = self.pygame
        color = tone_color(tone)
        chip_motion = self._motion_level("panel:stats")
        pygame.draw.rect(
            surface,
            blend_color((24, 35, 50), color, chip_motion * 0.08),
            rect,
            border_radius=12,
        )
        pygame.draw.rect(
            surface,
            blend_color(BORDER, color, chip_motion * 0.2),
            rect,
            width=1,
            border_radius=12,
        )
        pygame.draw.rect(
            surface,
            color,
            (rect.left + 1, rect.top + 1, rect.width - 2, 4),
            border_radius=4,
        )
        label_width = max(46, int(rect.width * 0.42))
        draw_text_line(
            surface,
            self.fonts.small,
            label.upper(),
            MUTED,
            pygame.Rect(rect.left + 10, rect.top + 5, label_width, rect.height - 10),
        )
        draw_text_line(
            surface,
            self.fonts.small,
            value,
            TEXT,
            pygame.Rect(
                rect.left + label_width + 12,
                rect.top + 5,
                rect.width - label_width - 22,
                rect.height - 10,
            ),
            align="right",
        )

    def _digit_index(self, event) -> int | None:
        if event.unicode and event.unicode.isdigit():
            digit = int(event.unicode)
            if 1 <= digit <= 9:
                return digit - 1
        key_map = {
            self.pygame.K_1: 0,
            self.pygame.K_2: 1,
            self.pygame.K_3: 2,
            self.pygame.K_4: 3,
            self.pygame.K_5: 4,
            self.pygame.K_6: 5,
            self.pygame.K_7: 6,
            self.pygame.K_8: 7,
            self.pygame.K_9: 8,
        }
        return key_map.get(event.key)

    def _inspector_key_for_command(self, command: str) -> str | None:
        return {
            TurnAction.REVIEW_TEAM.value: "team",
            TurnAction.REVIEW_FINANCE.value: "finance",
            TurnAction.REVIEW_CUSTOMERS.value: "customers",
            TurnAction.REVIEW_PARTNERSHIPS.value: "partnerships",
            TurnAction.REVIEW_BOARD.value: "board",
            TurnAction.REVIEW_PIPELINE.value: "pipeline",
            TurnAction.VIEW_REPORT.value: "report",
        }.get(command)

    def _focus_workspace_for_command(self, command: str) -> None:
        panel_key = self._workspace_panel_key_for_command(command)
        if panel_key is None:
            return
        self._set_deep_panel(panel_key)

    def _workspace_panel_key_for_command(self, command: str) -> str | None:
        return _workspace_panel_key_for_command(command)

    def _button_detail(
        self,
        command: str | None,
        default_detail: str,
        *,
        enabled: bool,
    ) -> str:
        if enabled or command is None:
            return default_detail
        reason = self._command_disabled_reason(command)
        if reason is None:
            return default_detail
        return self._compact_button_detail(reason)

    def _compact_button_detail(self, detail: str, *, max_length: int = 44) -> str:
        compact = detail.strip().replace("`", "")
        if len(compact) <= max_length:
            return compact
        return f"{compact[: max_length - 3].rstrip()}..."


class TurnSummaryScene(BaseScene):
    """Animated turn-resolution scene shown after each resolved turn."""

    def __init__(
        self,
        *,
        pygame,
        fonts: FontPack,
        state: GameState,
        rng: RandomSource,
        slot_name: str,
        save_callback,
        previous_state: GameState,
        resolution,
        selected_product_id: str,
        dirty: bool,
        motion_mode: MotionMode | str = MotionMode.FULL,
        entry_transition: str = "run_to_summary",
        return_scene_factory: Callable[[], BaseScene] | None = None,
        preferences: FrontendPreferences | None = None,
        preference_callback: Callable[[FrontendPreferences], FontPack] | None = None,
        preference_provider: Callable[[], FrontendPreferences] | None = None,
    ) -> None:
        super().__init__(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=rng,
            slot_name=slot_name,
            save_callback=save_callback,
            dirty=dirty,
            motion_mode=motion_mode,
            entry_transition=entry_transition,
            preferences=preferences,
            preference_callback=preference_callback,
            preference_provider=preference_provider,
        )
        self._previous_state = previous_state
        self._resolution = resolution
        self._selected_product_id = selected_product_id
        self._return_scene_factory = return_scene_factory
        self._click_targets: list[ClickTarget] = []
        self._events = build_turn_resolution_events(previous_state, resolution)
        self._visible_event_count = 1
        self._elapsed = 0.0
        self._tweens = TweenBank(speed=8.0)
        self._motion_pulses = PulseBank(
            decay=1.9,
            intensity_scale=self.motion_mode.pulse_scale,
        )
        self._view_model: TurnSummaryViewModel = build_turn_summary_view_model(
            previous_state,
            resolution,
        )
        self._tweens.sync_targets({metric.key: metric.ratio for metric in self._view_model.metrics})
        self._motion_pulses.trigger("summary:metrics", intensity=0.55, decay=1.2)
        if self._events:
            self._trigger_summary_event_motion(self._events[0])

    def update(self, dt: float) -> None:
        self._elapsed += dt
        self._update_scene_transition(dt)
        self._tweens.update(dt)
        self._motion_pulses.update(dt)
        self._stabilize_motion_bank()
        previous_visible = self._visible_event_count
        reveal_count = min(
            len(self._events),
            1 + int(self._elapsed / self._summary_event_reveal_interval()),
        )
        if reveal_count > previous_visible:
            for event in self._events[previous_visible:reveal_count]:
                self._trigger_summary_event_motion(event)
        self._visible_event_count = max(self._visible_event_count, reveal_count)

    def _stabilize_motion_bank(self) -> None:
        if self._motion_pulses.live_count() <= 14:
            return
        self._motion_pulses.prune(
            max_count=12,
            min_value=0.2,
            protected_prefixes=("summary:timeline", "summary:metrics", "panel:endgame"),
        )

    def _phase_index(self) -> int:
        return min(len(self._view_model.phase_labels) - 1, int(self._elapsed / 0.85))

    def _visible_metric_count(self) -> int:
        return min(len(self._view_model.metrics), 2 + self._phase_index() * 3)

    def _visible_product_count(self) -> int:
        return min(len(self._view_model.product_lines), 1 + self._phase_index())

    def _summary_metric_reveal_progress(self, index: int) -> float:
        if self.motion_mode is MotionMode.OFF:
            return 1.0
        start = 0.18 + index * (0.1 if self.motion_mode is MotionMode.REDUCED else 0.13)
        duration = 0.24 if self.motion_mode is MotionMode.REDUCED else 0.34
        ratio = max(0.0, min(1.0, (self._elapsed - start) / duration))
        return 1.0 - (1.0 - ratio) * (1.0 - ratio)

    def _summary_product_reveal_progress(self, index: int) -> float:
        if self.motion_mode is MotionMode.OFF:
            return 1.0
        start = 0.48 + index * (0.14 if self.motion_mode is MotionMode.REDUCED else 0.2)
        duration = 0.26 if self.motion_mode is MotionMode.REDUCED else 0.38
        ratio = max(0.0, min(1.0, (self._elapsed - start) / duration))
        return 1.0 - (1.0 - ratio) * (1.0 - ratio)

    def summary_metric_sequence_active(self) -> bool:
        """Return whether staged summary metric/product reveal animation is active."""

        if self.motion_mode is MotionMode.OFF:
            return False
        metric_count = max(1, len(self._view_model.metrics))
        product_count = max(1, len(self._view_model.product_lines))
        sequence_end = 0.48 + product_count * 0.2 + metric_count * 0.05
        return self._elapsed < sequence_end

    def _summary_outcome_lanes_duration(self) -> float:
        if self.motion_mode is MotionMode.OFF:
            return 0.0
        return 1.35 if self.motion_mode is MotionMode.REDUCED else 2.1

    def summary_outcome_lanes_active(self) -> bool:
        """Return whether the compact outcome lanes should animate."""

        duration = self._summary_outcome_lanes_duration()
        return duration > 0 and self._elapsed < duration

    def _summary_actor_sprite_strength(self) -> float:
        if self.motion_mode is MotionMode.OFF:
            return 0.0
        base = 0.16 if self.motion_mode is MotionMode.REDUCED else 0.34
        scale = 0.58 if self.motion_mode is MotionMode.REDUCED else 1.0
        pulse = self._summary_motion_level("summary:timeline", "summary:metrics")
        return min(1.0, (base + pulse * 0.3) * scale)

    def actor_timeline_active(self) -> bool:
        """Return whether turn-summary actor timelines should be animated."""

        return self._summary_actor_sprite_strength() > 0 and bool(
            self._summary_actor_sprite_clips()
        )

    def sprite_clips_active(self) -> bool:
        """Return whether turn-summary shape sprite clips are visible."""

        return self.actor_timeline_active()

    def _summary_actor_sprite_clips(self) -> tuple[ActorSpriteClip, ...]:
        metrics = {metric.key: metric for metric in self._view_model.metrics}
        net_cash = metrics.get("net_cash")
        users = metrics.get("users")
        board = metrics.get("board")
        gates = metrics.get("gates")
        cash_state = "success" if net_cash is not None and net_cash.tone == "success" else "risk"
        user_state = "success" if users is not None and users.tone == "success" else "handoff"
        board_state = "risk" if board is not None and board.tone == "danger" else "handoff"
        gate_state = (
            "alert" if gates is not None and gates.tone in {"danger", "warning"} else "build"
        )
        return (
            ActorSpriteClip(
                key="founder-summary",
                label="Founder",
                role="Decide",
                state="handoff",
                accent=SELECTION,
                lane="next",
                delay=0.0,
                phase_offset=0.4,
            ),
            ActorSpriteClip(
                key="finance-summary",
                label="Finance",
                role="Cash",
                state=cash_state,
                accent=GOOD if cash_state == "success" else DANGER,
                lane="flow",
                delay=0.08,
                phase_offset=1.3,
            ),
            ActorSpriteClip(
                key="customer-summary",
                label="Customer",
                role="Users",
                state=user_state,
                accent=INFO,
                lane="market",
                delay=0.16,
                phase_offset=2.2,
            ),
            ActorSpriteClip(
                key="board-summary",
                label="Board",
                role="Pressure",
                state=board_state,
                accent=DANGER if board_state == "risk" else WARN,
                lane="risk",
                delay=0.24,
                phase_offset=3.1,
            ),
            ActorSpriteClip(
                key="gate-summary",
                label="Gates",
                role="Exit",
                state=gate_state,
                accent=WARN if gate_state == "alert" else SELECTION,
                lane="path",
                delay=0.32,
                phase_offset=4.0,
            ),
        )

    def _summary_outcome_lane_progress(self, index: int) -> float:
        if self.motion_mode is MotionMode.OFF:
            return 1.0
        start = 0.12 + index * (0.08 if self.motion_mode is MotionMode.REDUCED else 0.12)
        duration = 0.42 if self.motion_mode is MotionMode.REDUCED else 0.58
        ratio = max(0.0, min(1.0, (self._elapsed - start) / duration))
        return 1.0 - (1.0 - ratio) * (1.0 - ratio)

    def _draw_summary_actor_sprite_layer(self, surface, anchor_rect) -> None:
        strength = self._summary_actor_sprite_strength()
        if strength <= 0:
            return
        clips = self._summary_actor_sprite_clips()
        if not clips:
            return
        pygame = self.pygame
        width, _height = surface.get_size()
        visible_count = 1 if width < 940 else 4
        visible_clips = clips[:visible_count]
        gap = 8
        clip_height = 46
        available = max(120, anchor_rect.width - 24)
        clip_width = min(
            138, max(118, int((available - gap * (visible_count - 1)) / visible_count))
        )
        total_width = clip_width * len(visible_clips) + gap * (len(visible_clips) - 1)
        left = max(anchor_rect.left + 12, anchor_rect.right - total_width - 12)
        top = max(anchor_rect.top + 42, anchor_rect.bottom - clip_height - 8)
        stage_rect = pygame.Rect(left - 8, top - 6, total_width + 16, clip_height + 12)
        stage = pygame.Surface((stage_rect.width, stage_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(
            stage,
            (*blend_color((8, 13, 22), INFO, 0.08), int(66 + strength * 42)),
            stage.get_rect(),
            border_radius=16,
        )
        surface.blit(stage, stage_rect.topleft)
        for index, clip in enumerate(visible_clips):
            clip_rect = pygame.Rect(left + index * (clip_width + gap), top, clip_width, clip_height)
            self._record_actor_sprite_bounds(clip, clip_rect)
            _draw_actor_sprite_clip(
                pygame=pygame,
                fonts=self.fonts,
                surface=surface,
                rect=clip_rect,
                clip=clip,
                elapsed=self._elapsed,
                intensity=strength,
            )

    def _summary_top_section_ratio(self, width: int) -> float:
        if width < 900:
            return 0.5 if len(self._events) >= 4 else 0.52
        if width < 1040:
            return 0.54
        return 0.58

    def _summary_motion_pressure_ratio(self) -> float:
        live_count = self._motion_pulses.live_count()
        total_intensity = self._motion_pulses.total_intensity()
        pressure = max(0.0, live_count - 8) * 0.02
        pressure += max(0.0, total_intensity - 4.0) * 0.015
        return min(0.28, pressure)

    def _summary_event_reveal_interval(self) -> float:
        surface = self.pygame.display.get_surface()
        if surface is None:
            return 0.35
        width, _height = surface.get_size()
        base = 0.45 if width < 1000 else 0.35
        if len(self._events) >= 4:
            base += 0.05
        if len(self._events) >= 6:
            base += 0.03
        pressure = self._summary_motion_pressure_ratio()
        if pressure > 0:
            base += pressure * 0.18
        return base

    def handle_event(self, event) -> None:
        if event.type == self.pygame.QUIT:
            self.should_exit = True
            self.exit_reason = "quit"
            return
        if event.type == self.pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_mouse_click(event.pos)
            return
        if event.type != self.pygame.KEYDOWN:
            return
        if event.key == self.pygame.K_ESCAPE:
            self.should_exit = True
            self.exit_reason = "quit"
            return
        if event.key == self.pygame.K_s:
            self._persist_current_run()
            return
        if event.key in (self.pygame.K_SPACE, self.pygame.K_RETURN, self.pygame.K_KP_ENTER):
            self._continue_to_run()

    def draw(self, surface) -> None:
        pygame = self.pygame
        self._click_targets = []
        self._reset_actor_sprite_bounds()
        draw_grid(surface, pygame)
        width, height = surface.get_size()
        profile = resolve_layout_profile(width, height)
        footer_height = 118 if height < 700 else 94
        frame = build_frame_layout(
            width,
            height,
            header_height=self._summary_header_height(height),
            footer_height=footer_height,
            nav_visible=True,
            profile=profile,
        )
        margin = profile.margin
        gap = profile.gap
        header_rect = pygame.Rect(frame.header.as_tuple())
        footer_rect = pygame.Rect(frame.footer.as_tuple())
        content_top = frame.content.top
        content_height = frame.content.height
        if width < 1100:
            top_height = int((content_height - gap) * self._summary_top_section_ratio(width))
            left_rect = pygame.Rect(margin, content_top, width - margin * 2, top_height)
            right_rect = pygame.Rect(
                margin,
                left_rect.bottom + gap,
                width - margin * 2,
                content_top + content_height - left_rect.bottom - gap,
            )
        else:
            left_width = int((width - margin * 2 - gap) * 0.55)
            right_width = width - margin * 2 - gap - left_width
            left_rect = pygame.Rect(margin, content_top, left_width, content_height)
            right_rect = pygame.Rect(
                left_rect.right + gap,
                content_top,
                right_width,
                content_height,
            )

        self._draw_summary_header(surface, header_rect)
        self._draw_summary_actor_sprite_layer(surface, header_rect)
        self._draw_summary_main(surface, left_rect)
        self._draw_summary_timeline(surface, right_rect)
        self._draw_summary_footer(surface, footer_rect)
        self._draw_nav_rail(
            surface,
            (
                ("Space Continue", "Return to the live run.", "continue", "", GOOD),
                ("S Save", "Persist the run.", "save", "", INFO),
                ("Esc Close", "Leave the 2D shell.", "close_summary", "", DANGER),
            ),
        )
        self._draw_summary_outcome_lanes(surface)
        self._draw_summary_cinematic_overlay(surface)
        self._sync_mouse_cursor()
        self._draw_scene_transition_overlay(surface)

    def _handle_mouse_click(self, position: tuple[int, int]) -> None:
        for target in reversed(self._click_targets):
            if target.rect.collidepoint(position):
                if target.kind == "continue":
                    self._continue_to_run()
                    return
                if target.kind == "save":
                    self._persist_current_run()
                    return
                if target.kind == "close_summary":
                    self.should_exit = True
                    self.exit_reason = "quit"
                    return

    def _continue_to_run(self) -> None:
        if self.state.company.game_over or self.state.victory_achieved:
            self._next_scene = ReviewScene(
                pygame=self.pygame,
                fonts=self.fonts,
                state=self.state,
                rng=self.rng,
                slot_name=self.slot_name,
                save_callback=self._save_callback,
                view_model=build_run_review_view_model(self.state),
                accent=GOOD if self.state.victory_achieved else DANGER,
                primary_title=(
                    "Back to Menu" if self._return_scene_factory is not None else "Esc Close"
                ),
                primary_detail=(
                    "Return to the title menu."
                    if self._return_scene_factory is not None
                    else "Leave the 2D shell."
                ),
                return_scene_factory=self._return_scene_factory,
                allow_save=True,
                dirty=self._dirty,
                motion_mode=self.motion_mode,
                preferences=self._current_frontend_preferences(),
                preference_callback=self._preference_callback,
                preference_provider=self._preference_provider,
                entry_transition="summary_to_review",
            )
            return
        focus_panel_key = _workspace_panel_key_for_command(self._view_model.focus_command)
        seed_events = self._events[:6]
        handoff_event = self._build_return_focus_event(focus_panel_key)
        if handoff_event is not None:
            seed_events = (handoff_event,) + self._events[:5]
        self._next_scene = RunScene(
            pygame=self.pygame,
            fonts=self.fonts,
            state=self.state,
            rng=self.rng,
            slot_name=self.slot_name,
            save_callback=self._save_callback,
            selected_product_id=self._selected_product_id,
            initial_panel_key=focus_panel_key,
            seed_events=seed_events,
            dirty=self._dirty,
            show_ready_event=False,
            motion_mode=self.motion_mode,
            preferences=self._current_frontend_preferences(),
            preference_callback=self._preference_callback,
            preference_provider=self._preference_provider,
            entry_transition="summary_to_run",
            return_scene_factory=self._return_scene_factory,
        )

    def _trigger_summary_event_motion(self, event: FrontendEvent) -> None:
        intensity = _MOTION_INTENSITY.get(event.severity, 0.42)
        pressure = self._summary_motion_pressure_ratio()
        surface = self.pygame.display.get_surface()
        width = surface.get_size()[0] if surface is not None else 1280
        if width < 1000 and event.severity in {"info", "success"}:
            intensity *= 0.88
        if len(self._events) >= 4 and event.severity != "danger":
            intensity *= 0.9
        if pressure > 0:
            intensity *= max(0.72, 1.0 - pressure * 0.52)
        self._motion_pulses.trigger("summary:timeline", intensity=max(0.24, intensity * 0.72))
        for target in event.targets:
            self._motion_pulses.trigger(target, intensity=intensity)

    def _summary_motion_level(self, *keys: str) -> float:
        if not keys:
            return 0.0
        return max(self._motion_pulses.get(key) for key in keys)

    def _summary_cinematic_duration(self) -> float:
        if self.motion_mode is MotionMode.OFF:
            return 0.0
        return 1.25 if self.motion_mode is MotionMode.REDUCED else 1.9

    def summary_cinematic_active(self) -> bool:
        """Return whether the turn-summary cinematic rail should be visible."""

        duration = self._summary_cinematic_duration()
        return duration > 0 and self._elapsed < duration

    def _summary_cinematic_progress(self) -> float:
        duration = self._summary_cinematic_duration()
        if duration <= 0:
            return 1.0
        return max(0.0, min(1.0, self._elapsed / duration))

    def _draw_summary_outcome_lanes(self, surface) -> None:
        if not self.summary_outcome_lanes_active():
            return
        pygame = self.pygame
        width, height = surface.get_size()
        metrics_by_key = {metric.key: metric for metric in self._view_model.metrics}
        lane_metrics = tuple(
            metric
            for key in ("net_cash", "users", "board", "gates")
            if (metric := metrics_by_key.get(key)) is not None
        )
        if not lane_metrics:
            return
        lane_height = 18
        lane_gap = 6
        panel_width = min(620, max(420, int(width * 0.5)))
        left = 36
        header_bottom = (20 if width < 900 else 24) + 46 + self._summary_header_height(height)
        top = header_bottom - lane_height - 8
        lane_width = int((panel_width - lane_gap * (len(lane_metrics) - 1)) / len(lane_metrics))
        for index, metric in enumerate(lane_metrics):
            progress = self._summary_outcome_lane_progress(index)
            if progress <= 0:
                continue
            accent = tone_color(metric.tone)
            lane_rect = pygame.Rect(
                left + index * (lane_width + lane_gap),
                top,
                lane_width,
                lane_height,
            )
            fill_alpha = int(46 + progress * 76)
            pygame.draw.rect(
                surface,
                (*blend_color((13, 22, 34), accent, 0.12), fill_alpha),
                lane_rect,
                border_radius=lane_height // 2,
            )
            pygame.draw.rect(
                surface,
                (*blend_color(BORDER, accent, 0.35), min(210, fill_alpha + 70)),
                lane_rect,
                width=1,
                border_radius=lane_height // 2,
            )
            fill_width = max(6, int(lane_rect.width * metric.ratio * progress))
            pygame.draw.rect(
                surface,
                (*accent, min(190, fill_alpha + 70)),
                pygame.Rect(lane_rect.left, lane_rect.top, fill_width, lane_rect.height),
                border_radius=lane_height // 2,
            )
            label = self.fonts.small.render(
                self._compact_summary_text(metric.label, max_length=9),
                True,
                TEXT,
            )
            value = self.fonts.small.render(metric.value_text, True, TEXT)
            surface.blit(label, (lane_rect.left + 7, lane_rect.top + 3))
            surface.blit(
                value,
                (lane_rect.right - value.get_width() - 7, lane_rect.top + 3),
            )

    def _draw_summary_cinematic_overlay(self, surface) -> None:
        if not self.summary_cinematic_active():
            return
        pygame = self.pygame
        width, height = surface.get_size()
        progress = self._summary_cinematic_progress()
        eased = 1.0 - (1.0 - progress) * (1.0 - progress)
        intensity = 0.56 if self.motion_mode is MotionMode.REDUCED else 1.0
        margin = 20 if width < 900 else 24
        gap = 12 if height < 700 else 16
        header_bottom = margin + 46 + self._summary_header_height(height)
        rail_top = header_bottom + max(2, int((gap - 8) / 2))
        rail_rect = pygame.Rect(36, rail_top, width - 72, 8)
        fill_alpha = int((1.0 - progress * 0.55) * 78 * intensity)
        pygame.draw.rect(
            surface,
            (*blend_color((13, 22, 34), INFO, 0.2), fill_alpha),
            rail_rect,
            border_radius=5,
        )
        filled_rect = pygame.Rect(
            rail_rect.left,
            rail_rect.top,
            max(8, int(rail_rect.width * eased)),
            rail_rect.height,
        )
        pygame.draw.rect(
            surface,
            (*SELECTION, min(180, fill_alpha + 70)),
            filled_rect,
            border_radius=5,
        )
        phase_labels = self._view_model.phase_labels or ("Input", "Impact", "Next")
        for index, _label in enumerate(phase_labels):
            marker_ratio = index / max(1, len(phase_labels) - 1)
            marker_x = rail_rect.left + int(rail_rect.width * marker_ratio)
            active = progress >= marker_ratio * 0.82
            color = SELECTION if active else BORDER
            pygame.draw.circle(
                surface,
                (*color, min(220, fill_alpha + 100)),
                (marker_x, rail_rect.centery),
                6,
            )

    def _summary_header_height(self, _height: int) -> int:
        return 118

    def _build_return_focus_event(self, panel_key: str | None) -> FrontendEvent | None:
        if not self._view_model.focus_command:
            return None
        targets = ("feed", "summary:timeline")
        if panel_key is not None:
            targets = targets + (f"panel:{panel_key}",)
        warning_panels = {"finance", "board", "customers", "partnerships"}
        severity = "warning" if panel_key in warning_panels else "info"
        return FrontendEvent(
            title="Next Focus",
            detail=f"{self._view_model.focus_label}: {self._view_model.focus_detail}",
            severity=severity,
            ttl=5.2 if severity == "warning" else 4.8,
            motion="flash" if severity == "warning" else "slide",
            targets=targets,
        )

    def _draw_summary_header(self, surface, rect) -> None:
        pygame = self.pygame
        width, _height = surface.get_size()
        inner = draw_panel(surface, pygame, rect, title="Turn Summary", accent=INFO)
        actor_reserve = 156 if width < 940 and self.motion_mode is not MotionMode.OFF else 0
        phase_left = (
            inner.right if width < 940 else inner.right - 310 if inner.width >= 620 else inner.right
        )
        copy_width = max(220, min(phase_left - inner.left - 12, inner.width - actor_reserve))
        draw_text_line(
            surface,
            self.fonts.title,
            self._view_model.title,
            TEXT,
            pygame.Rect(inner.left, inner.top - 30, copy_width, 30),
            valign="top",
        )
        draw_text_line(
            surface,
            self.fonts.body,
            self._view_model.headline,
            INFO,
            pygame.Rect(inner.left, inner.top, copy_width, 22),
            valign="top",
        )
        for index, label in enumerate(self._view_model.phase_labels):
            if width < 940 or inner.width < 620:
                break
            chip_rect = pygame.Rect(phase_left + index * 100, inner.top, 92, 20)
            color = SELECTION if index <= self._phase_index() else BORDER
            fill = (34, 47, 66) if index <= self._phase_index() else (24, 35, 50)
            pygame.draw.rect(surface, fill, chip_rect, border_radius=10)
            pygame.draw.rect(surface, color, chip_rect, width=1, border_radius=10)
            chip_text_color = TEXT if index <= self._phase_index() else MUTED
            draw_text_line(
                surface,
                self.fonts.small,
                label,
                chip_text_color,
                pygame.Rect(chip_rect.left + 8, chip_rect.top + 3, chip_rect.width - 16, 16),
            )
        draw_wrapped_text(
            surface,
            self.fonts.small,
            self._view_model.narrative,
            MUTED,
            pygame.Rect(inner.left, inner.top + 24, copy_width, 40),
            line_height=16,
            max_lines=2,
        )

    def _draw_summary_main(self, surface, rect) -> None:
        if rect.height < 240:
            self._draw_summary_compact_main(surface, rect)
            return
        pygame = self.pygame
        visible_metrics = self._view_model.metrics[: self._visible_metric_count()]
        metric_rows = max(1, (len(visible_metrics) + 2) // 3)
        metrics_height = 94 + metric_rows * 86
        metrics_rect = pygame.Rect(rect.left, rect.top, rect.width, metrics_height)
        products_rect = pygame.Rect(
            rect.left,
            metrics_rect.bottom + 12,
            rect.width,
            rect.height - metrics_height - 12,
        )
        metrics_motion = self._summary_motion_level("summary:metrics")
        inner = draw_panel(
            surface,
            pygame,
            metrics_rect,
            title="Metrics",
            accent=GOOD,
            emphasis=metrics_motion,
            lift=int(metrics_motion * 3),
        )
        title_surface = self.fonts.heading.render("Resolution Delta", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 24))
        cols = 3
        card_gap = 10
        card_width = int((inner.width - card_gap * (cols - 1)) / cols)
        card_height = 74
        top = inner.top
        left = inner.left
        for index, metric in enumerate(visible_metrics):
            if index and index % cols == 0:
                top += card_height + 12
                left = inner.left
            reveal = self._summary_metric_reveal_progress(index)
            card_rect = pygame.Rect(
                left + int((1.0 - reveal) * 20),
                top,
                card_width,
                card_height,
            )
            self._draw_metric_card(surface, card_rect, metric, reveal_ratio=reveal)
            left += card_width + card_gap

        product_inner = draw_panel(
            surface,
            pygame,
            products_rect,
            title="Products",
            accent=SELECTION,
            emphasis=self._summary_motion_level("summary:metrics"),
            lift=int(self._summary_motion_level("summary:metrics") * 2),
        )
        product_title = self.fonts.heading.render("Product Outcomes", True, TEXT)
        surface.blit(product_title, (product_inner.left, product_inner.top - 24))
        top = product_inner.top
        visible_products = self._view_model.product_lines[: self._visible_product_count()]
        for index, product_line in enumerate(visible_products):
            reveal = self._summary_product_reveal_progress(index)
            line_rect = pygame.Rect(
                product_inner.left + int((1.0 - reveal) * 22),
                top,
                product_inner.width,
                56,
            )
            color = tone_color(product_line.tone)
            pygame.draw.rect(
                surface,
                blend_color((26, 38, 55), color, (1.0 - reveal) * 0.08),
                line_rect,
                border_radius=14,
            )
            pygame.draw.rect(
                surface,
                blend_color(color, TEXT, (1.0 - reveal) * 0.12),
                line_rect,
                width=2 if reveal < 1.0 else 1,
                border_radius=14,
            )
            title_surface = self.fonts.body.render(product_line.name, True, TEXT)
            revenue_surface = self.fonts.small.render(product_line.revenue_text, True, INFO)
            cost_surface = self.fonts.small.render(f"cost {product_line.cost_text}", True, MUTED)
            surface.blit(title_surface, (line_rect.left + 12, line_rect.top + 10))
            surface.blit(
                revenue_surface,
                (line_rect.right - revenue_surface.get_width() - 12, line_rect.top + 10),
            )
            draw_wrapped_text(
                surface,
                self.fonts.small,
                product_line.detail,
                MUTED,
                pygame.Rect(line_rect.left + 12, line_rect.top + 30, line_rect.width - 120, 18),
                line_height=14,
                max_lines=1,
            )
            surface.blit(
                cost_surface,
                (line_rect.right - cost_surface.get_width() - 12, line_rect.top + 32),
            )
            top += 66
        if not visible_products:
            idle_surface = self.fonts.body.render("No live product delta surfaced.", True, MUTED)
            surface.blit(idle_surface, (product_inner.left, product_inner.top))

    def _draw_summary_compact_main(self, surface, rect) -> None:
        pygame = self.pygame
        metrics_motion = self._summary_motion_level("summary:metrics")
        inner = draw_panel(
            surface,
            pygame,
            rect,
            title="Metrics",
            accent=GOOD,
            emphasis=metrics_motion,
            lift=int(metrics_motion * 2),
        )
        draw_text_line(
            surface,
            self.fonts.heading,
            "Resolution Delta",
            TEXT,
            pygame.Rect(inner.left, inner.top - 28, inner.width, 24),
            valign="top",
        )
        visible_metrics = self._view_model.metrics[:2]
        if not visible_metrics:
            draw_text_line(
                surface,
                self.fonts.body,
                "No metric delta surfaced.",
                MUTED,
                pygame.Rect(inner.left, inner.top, inner.width, 22),
                valign="top",
            )
            return
        gap = 10
        cols = 2 if inner.width >= 520 and len(visible_metrics) > 1 else 1
        card_width = int((inner.width - gap * (cols - 1)) / cols)
        card_height = max(48, min(64, inner.height - 6))
        for index, metric in enumerate(visible_metrics):
            row = index // cols
            col = index % cols
            card_rect = pygame.Rect(
                inner.left + col * (card_width + gap),
                inner.top + row * (card_height + gap),
                card_width,
                card_height,
            )
            color = tone_color(metric.tone)
            pygame.draw.rect(
                surface,
                blend_color((26, 38, 55), color, metrics_motion * 0.14),
                card_rect,
                border_radius=14,
            )
            pygame.draw.rect(surface, color, card_rect, width=1, border_radius=14)
            draw_text_line(
                surface,
                self.fonts.small,
                metric.label.upper(),
                blend_color(MUTED, color, metrics_motion * 0.45),
                pygame.Rect(card_rect.left + 12, card_rect.top + 8, card_rect.width - 24, 16),
                valign="top",
            )
            draw_text_line(
                surface,
                self.fonts.body,
                metric.value_text,
                TEXT,
                pygame.Rect(card_rect.left + 12, card_rect.top + 26, card_rect.width - 24, 20),
                valign="top",
            )
            if card_rect.height >= 58:
                draw_progress_bar(
                    surface,
                    pygame,
                    pygame.Rect(
                        card_rect.left + 12,
                        card_rect.bottom - 12,
                        card_rect.width - 24,
                        8,
                    ),
                    ratio=self._tweens.get(metric.key, metric.ratio),
                    color=color,
                    emphasis=metrics_motion,
                )

    def _draw_summary_timeline(self, surface, rect) -> None:
        if rect.height < 220:
            self._draw_summary_compact_timeline(surface, rect)
            return
        pygame = self.pygame
        strategy_height = self._summary_strategy_height(rect.height)
        strategy_rect = pygame.Rect(rect.left, rect.top, rect.width, strategy_height)
        timeline_rect = pygame.Rect(
            rect.left,
            strategy_rect.bottom + 12,
            rect.width,
            rect.height - strategy_height - 12,
        )
        self._draw_summary_strategy(surface, strategy_rect)
        timeline_motion = self._summary_motion_level("summary:timeline")
        inner = draw_panel(
            surface,
            pygame,
            timeline_rect,
            title="Timeline",
            accent=WARN,
            emphasis=timeline_motion,
            lift=int(timeline_motion * 3),
        )
        title_surface = self.fonts.heading.render("Turn Resolution Timeline", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 24))
        if not self._events:
            idle_surface = self.fonts.body.render("No timeline events.", True, MUTED)
            surface.blit(idle_surface, (inner.left, inner.top))
            return
        top = inner.top
        visible_event_cap = self._summary_timeline_visible_count(inner.height)
        for event in self._events[: min(self._visible_event_count, visible_event_cap)]:
            card_rect = pygame.Rect(inner.left, top, inner.width, 70)
            self._draw_summary_event(surface, card_rect, event)
            top += 80
            if top + 70 > inner.bottom:
                break

    def _draw_summary_compact_timeline(self, surface, rect) -> None:
        pygame = self.pygame
        timeline_motion = self._summary_motion_level("summary:timeline")
        inner = draw_panel(
            surface,
            pygame,
            rect,
            title="Next",
            accent=WARN,
            emphasis=timeline_motion,
            lift=int(timeline_motion * 2),
        )
        draw_text_line(
            surface,
            self.fonts.heading,
            "Next Step",
            TEXT,
            pygame.Rect(inner.left, inner.top - 28, inner.width, 24),
            valign="top",
        )
        draw_text_line(
            surface,
            self.fonts.body,
            self._summary_focus_command_title(max_length=26),
            INFO,
            pygame.Rect(inner.left, inner.top, inner.width, 22),
            valign="top",
        )
        event_text = self._summary_compact_explanation()
        draw_wrapped_text(
            surface,
            self.fonts.small,
            event_text,
            MUTED,
            pygame.Rect(inner.left, inner.top + 26, inner.width, max(20, inner.height - 30)),
            line_height=15,
            max_lines=2,
        )

    def _summary_compact_explanation(self) -> str:
        if self._view_model.cause_lines:
            return self._view_model.cause_lines[0]
        if self._events:
            return self._events[0].detail
        return self._view_model.strategic_headline or self._view_model.footer

    def _summary_strategy_height(self, total_height: int) -> int:
        if total_height < 220:
            return max(72, total_height - 96)
        if total_height < 300:
            return 116
        return 176 if total_height >= 360 else 156

    def _draw_summary_strategy(self, surface, rect) -> None:
        pygame = self.pygame
        strategy_motion = self._summary_motion_level("panel:endgame", "panel:report")
        inner = draw_panel(
            surface,
            pygame,
            rect,
            title="Strategy",
            accent=INFO,
            emphasis=strategy_motion,
            lift=int(strategy_motion * 2),
        )
        title_surface = self.fonts.heading.render("Strategic Delta", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 24))
        compact = rect.height < 150 or rect.width < 520
        draw_wrapped_text(
            surface,
            self.fonts.body,
            self._view_model.strategic_headline,
            INFO,
            pygame.Rect(inner.left, inner.top, inner.width, 24 if compact else 34),
            line_height=18,
            max_lines=1 if compact else 2,
        )
        command_rect = pygame.Rect(
            inner.left,
            inner.top + (28 if compact else 34),
            inner.width,
            38 if compact else 42,
        )
        draw_button(
            surface,
            pygame,
            rect=command_rect,
            title=self._summary_focus_command_title(max_length=22 if compact else 28),
            detail=self._summary_focus_command_detail(),
            accent=WARN,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
            selected=self._phase_index() >= 2,
        )
        top = command_rect.bottom + 12
        available_lines = max(0, (inner.bottom - top) // 20)
        line_limit = min(2 if compact else 3, available_lines)
        visible_lines = (self._view_model.cause_lines + self._view_model.strategic_lines)[
            :line_limit
        ]
        for line in visible_lines:
            draw_wrapped_text(
                surface,
                self.fonts.small,
                line,
                MUTED,
                pygame.Rect(inner.left, top, inner.width, min(18, inner.bottom - top)),
                line_height=15,
                max_lines=1,
            )
            top += 20

    def _summary_focus_command_title(self, *, max_length: int = 28) -> str:
        command = self._compact_summary_text(
            self._view_model.focus_label,
            max_length=max_length,
        )
        return f"Next {command}"

    def _summary_focus_command_detail(self) -> str:
        return self._compact_summary_text(self._view_model.focus_detail, max_length=48)

    def _compact_summary_text(self, detail: str, *, max_length: int) -> str:
        compact = detail.strip().replace("`", "")
        if len(compact) <= max_length:
            return compact
        return f"{compact[: max_length - 3].rstrip()}..."

    def _summary_timeline_visible_count(self, timeline_height: int) -> int:
        if timeline_height < 140:
            return 1
        if timeline_height < 220:
            return 2
        return 3

    def _draw_summary_footer(self, surface, rect) -> None:
        pygame = self.pygame
        inner = draw_panel(surface, pygame, rect, title="Continue", accent=INFO)
        compact = rect.width < 760
        draw_text_line(
            surface,
            self.fonts.small,
            "Press Space or click Continue." if compact else self._view_model.footer,
            TEXT,
            pygame.Rect(inner.left, inner.top - 2, inner.width, 18),
            valign="top",
        )
        button_gap = 10
        button_top = inner.top + 24
        available_width = inner.width
        button_width = int((available_width - button_gap * 2) / 3)
        continue_rect = pygame.Rect(inner.left, button_top, button_width, 38)
        save_rect = pygame.Rect(continue_rect.right + button_gap, button_top, button_width, 38)
        close_rect = pygame.Rect(save_rect.right + button_gap, button_top, button_width, 38)
        draw_button(
            surface,
            pygame,
            rect=continue_rect,
            title="Space Continue",
            detail="" if compact else "Return to the live run.",
            accent=INFO,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        draw_button(
            surface,
            pygame,
            rect=save_rect,
            title="S Save",
            detail="" if compact else "Persist before leaving this scene.",
            accent=GOOD,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        draw_button(
            surface,
            pygame,
            rect=close_rect,
            title="Esc Close",
            detail="" if compact else "Exit the 2D shell now.",
            accent=WARN,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        self._click_targets.append(ClickTarget("continue", "", continue_rect))
        self._click_targets.append(ClickTarget("save", "", save_rect))
        self._click_targets.append(ClickTarget("close_summary", "", close_rect))

    def _draw_metric_card(self, surface, rect, metric, *, reveal_ratio: float = 1.0) -> None:
        pygame = self.pygame
        color = tone_color(metric.tone)
        metric_motion = self._summary_motion_level("summary:metrics", metric.key)
        safe_reveal = max(0.0, min(1.0, reveal_ratio))
        reveal_emphasis = (1.0 - safe_reveal) * 0.35
        visual_rect = pygame.Rect(
            rect.left, rect.top - int(metric_motion * 3), rect.width, rect.height
        )
        pygame.draw.rect(
            surface,
            blend_color(
                (26, 38, 55),
                color,
                min(0.28, metric_motion * 0.14 + reveal_emphasis),
            ),
            visual_rect,
            border_radius=14,
        )
        pygame.draw.rect(
            surface,
            blend_color(color, TEXT, metric_motion * 0.12),
            visual_rect,
            width=2 if metric_motion >= 0.4 or safe_reveal < 1.0 else 1,
            border_radius=14,
        )
        label_surface = self.fonts.small.render(
            metric.label.upper(),
            True,
            blend_color(MUTED, color, metric_motion * 0.45),
        )
        value_surface = self.fonts.body.render(
            metric.value_text,
            True,
            blend_color(TEXT, color, metric_motion * 0.12),
        )
        compact = visual_rect.width < 320
        surface.blit(label_surface, (visual_rect.left + 12, visual_rect.top + 10))
        if compact:
            detail_text = self._compact_summary_text(metric.detail, max_length=24)
            draw_wrapped_text(
                surface,
                self.fonts.small,
                detail_text,
                MUTED,
                pygame.Rect(
                    visual_rect.left + 12,
                    visual_rect.top + 24,
                    visual_rect.width - 24,
                    16,
                ),
                line_height=14,
                max_lines=1,
            )
            surface.blit(value_surface, (visual_rect.left + 12, visual_rect.top + 40))
        else:
            surface.blit(value_surface, (visual_rect.left + 12, visual_rect.top + 28))
            draw_wrapped_text(
                surface,
                self.fonts.small,
                metric.detail,
                MUTED,
                pygame.Rect(
                    visual_rect.left + 90,
                    visual_rect.top + 12,
                    visual_rect.width - 102,
                    20,
                ),
                line_height=14,
                max_lines=2,
            )
        draw_progress_bar(
            surface,
            pygame,
            pygame.Rect(visual_rect.left + 12, visual_rect.top + 52, visual_rect.width - 24, 10),
            ratio=self._tweens.get(metric.key, metric.ratio),
            color=color,
            emphasis=metric_motion,
        )

    def _draw_summary_event(self, surface, rect, event: FrontendEvent) -> None:
        pygame = self.pygame
        color = tone_color(event.severity)
        event_motion = self._summary_motion_level("summary:timeline", *event.targets)
        visual_rect = pygame.Rect(
            rect.left, rect.top - int(event_motion * 3), rect.width, rect.height
        )
        pygame.draw.rect(
            surface,
            blend_color((26, 38, 55), color, event_motion * 0.15),
            visual_rect,
            border_radius=14,
        )
        pygame.draw.rect(
            surface,
            blend_color(color, TEXT, event_motion * 0.1),
            visual_rect,
            width=2 if event_motion >= 0.4 else 1,
            border_radius=14,
        )
        title_surface = self.fonts.body.render(event.title, True, TEXT)
        surface.blit(title_surface, (visual_rect.left + 12, visual_rect.top + 10))
        draw_wrapped_text(
            surface,
            self.fonts.small,
            event.detail,
            MUTED,
            pygame.Rect(visual_rect.left + 12, visual_rect.top + 32, visual_rect.width - 24, 26),
            line_height=15,
            max_lines=2,
        )


MainGameScene = RunScene
