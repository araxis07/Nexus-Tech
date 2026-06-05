"""Scene objects for the lightweight 2D frontend."""

from __future__ import annotations

import re
from dataclasses import dataclass
from math import sin
from typing import Callable

from nexus_tech.domain.models import GameState, TurnAction
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
from nexus_tech.frontend_2d.event_queue import (
    FrontendEvent,
    build_action_events,
    build_turn_resolution_events,
)
from nexus_tech.frontend_2d.input_map import FrontendIntent
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
    OVERLAY,
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
    draw_wrapped_text,
    tone_color,
)
from nexus_tech.persistence.errors import PersistenceError
from nexus_tech.persistence.save_coordinator import (
    RunArchiveSummary,
    SaveLoadCoordinator,
    SaveSlotSummary,
)
from nexus_tech.simulation.end_turn_preview import build_end_turn_preview
from nexus_tech.simulation.engine import ActionContext, apply_action, create_new_game, resolve_turn
from nexus_tech.simulation.meta_progression import (
    ArchiveComparisonSummary,
    MetaProgressionSummary,
    build_archive_comparison,
    summarize_meta_progression,
)
from nexus_tech.simulation.randomness import RandomSource


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
        "P",
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

_INSPECTOR_SORT_MODES: tuple[str, ...] = ("default", "risk", "value", "stalled")
_INSPECTOR_FILTER_MODES: tuple[str, ...] = ("all", "actionable", "attention")
_TONE_PRIORITY = {"danger": 3, "warning": 2, "info": 1, "success": 0}
_MOTION_INTENSITY = {"success": 0.55, "info": 0.42, "warning": 0.75, "danger": 1.0}
_SCENE_TRANSITION_LABELS = {
    "boot_title": ("Title Boot", INFO),
    "boot_run": ("Run Boot", INFO),
    "title_to_run": ("Entering Run", GOOD),
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
    ) -> None:
        self.pygame = pygame
        self.fonts = fonts
        self.state = state
        self.rng = rng
        self.slot_name = slot_name
        self._save_callback = save_callback
        self._dirty = dirty
        self.motion_mode = normalize_motion_mode(motion_mode)
        self.should_exit = False
        self.exit_reason = "quit"
        self._next_scene: BaseScene | None = None
        self._scene_transition_key = entry_transition
        self._scene_transition_elapsed = 0.0
        self._scene_transition_duration = self._entry_transition_duration(entry_transition)

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
        fade_alpha = int((1.0 - eased) * 150 * intensity)
        if fade_alpha > 0:
            overlay.fill((3, 6, 12, fade_alpha))

        sweep_width = max(80, int(width * 0.14))
        sweep_x = int((eased * (width + sweep_width * 2)) - sweep_width * 1.4)
        sweep_alpha = int(max(0.0, 1.0 - abs(progress - 0.48) * 2.1) * 80 * intensity)
        if sweep_alpha > 0:
            sweep_rect = pygame.Rect(sweep_x, 0, sweep_width, height)
            pygame.draw.rect(overlay, (*accent, sweep_alpha), sweep_rect)
            edge_rect = pygame.Rect(sweep_rect.right - 4, 0, 4, height)
            pygame.draw.rect(overlay, (*TEXT, min(160, sweep_alpha + 36)), edge_rect)

        line_gap = 26 if self.motion_mode is MotionMode.FULL else 38
        line_alpha = int((1.0 - progress) * 42 * intensity)
        if line_alpha > 0:
            for y in range(0, height, line_gap):
                pygame.draw.line(overlay, (*accent, line_alpha), (0, y), (width, y), 1)

        surface.blit(overlay, (0, 0))
        if progress < 0.62 and intensity > 0.5:
            badge = self.fonts.small.render(label, True, TEXT)
            badge_rect = badge.get_rect()
            badge_rect.topright = (width - 28, 28)
            pad = 9
            panel_rect = pygame.Rect(
                badge_rect.left - pad,
                badge_rect.top - 5,
                badge_rect.width + pad * 2,
                badge_rect.height + 10,
            )
            pygame.draw.rect(surface, (8, 13, 22), panel_rect, border_radius=12)
            pygame.draw.rect(surface, accent, panel_rect, width=1, border_radius=12)
            surface.blit(badge, badge_rect)


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
        )
        self.coordinator = coordinator
        self._mode = initial_mode
        self._click_targets: list[ClickTarget] = []
        self._events: list[TimedFrontendEvent] = []
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

    def _trigger_title_motion(self, section_key: str, *, intensity: float = 0.6) -> None:
        self._motion_pulses.trigger(f"title:{section_key}", intensity=intensity, decay=2.1)

    def _trigger_mode_motion(self, mode: str, *, intensity: float = 0.72) -> None:
        self._motion_pulses.trigger(f"title:mode:{mode}", intensity=intensity, decay=2.4)
        self._trigger_title_motion("content", intensity=max(0.44, intensity * 0.7))
        self._trigger_title_motion("footer", intensity=max(0.32, intensity * 0.5))

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
        draw_grid(surface, pygame)
        width, height = surface.get_size()
        margin = 24
        gap = 16
        header_rect = pygame.Rect(margin, margin, width - margin * 2, 104)
        footer_rect = pygame.Rect(margin, height - 92 - margin, width - margin * 2, 92)
        content_top = header_rect.bottom + gap
        content_height = footer_rect.top - gap - content_top
        if width < 1180:
            left_share = 0.62 if self._mode == "meta" else 0.56
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
        if self._mode == "menu":
            self._draw_title_menu(surface, left_rect)
        elif self._mode == "meta":
            self._draw_meta_board(surface, left_rect)
        elif self._mode == "slots":
            self._draw_save_slot_browser(surface, left_rect)
        elif self._mode == "slot_detail":
            self._draw_slot_detail(surface, left_rect)
        elif self._mode == "wizard":
            self._draw_new_game_wizard(surface, left_rect)
        else:
            self._draw_archive_browser(surface, left_rect)
        self._draw_title_sidebar(surface, right_rect)
        self._draw_title_footer(surface, footer_rect)
        if self._confirm_delete_slot_name is not None:
            self._draw_delete_confirmation_overlay(surface)
        if self._text_input is not None:
            self._draw_text_input_overlay(surface)
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
                    2: "load_slots",
                    3: "archives",
                    4: "meta",
                    5: "new_wizard",
                    6: "quit",
                }.get(digit, "")
            )
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
        if action == "new_wizard":
            self._set_mode("wizard")
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
            entry_transition="title_to_run",
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
            entry_transition="title_to_review",
        )

    def _open_slot_detail(self, slot_name: str) -> None:
        if slot_name not in self._save_summaries_by_slot:
            return
        self._selected_slot_name = slot_name
        self._set_mode("slot_detail")

    def _spawn_scene(self, mode: str, *, entry_transition: str = "review_to_title") -> "TitleScene":
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
        title_surface = self.fonts.title.render("NEXUS TECH 2D", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 28))
        subtitle = (
            "Self-contained frontend shell with loadable saves, archive reviews, "
            "and live run handoff."
        )
        draw_wrapped_text(
            surface,
            self.fonts.body,
            subtitle,
            MUTED,
            pygame.Rect(inner.left, inner.top, inner.width, 24),
            line_height=18,
            max_lines=2,
        )
        meta_surface = self.fonts.small.render(
            f"Save slots {len(self._save_cards)} | archives {len(self._archive_cards)}",
            True,
            TEXT,
        )
        surface.blit(meta_surface, (inner.left, inner.top + 38))

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
        title_surface = self.fonts.heading.render("Title Menu", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 24))
        buttons = (
            ("1 Continue Last", "Open the newest save slot directly.", "continue", INFO),
            (
                "2 Manage Saves",
                "Browse, load, rename, duplicate, or delete save slots.",
                "load_slots",
                GOOD,
            ),
            ("3 Review Archives", "Inspect completed runs and postmortems.", "archives", WARN),
            (
                "4 Meta Board",
                "See archive progression, dominant path, and next unlocks.",
                "meta",
                SELECTION,
            ),
            (
                "5 New Game Wizard",
                "Choose scenario, difficulty, start, goal, names, slot, and seed.",
                "new_wizard",
                INFO,
            ),
            ("6 Quit", "Leave the frontend shell.", "quit", DANGER),
        )
        top = inner.top
        for title, detail, payload, accent in buttons:
            button_rect = pygame.Rect(inner.left, top, inner.width, 62)
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
            top += 74

    def _draw_meta_board(self, surface, rect) -> None:
        pygame = self.pygame
        compact = self._meta_board_compact_layout(rect)
        meta_motion = self._motion_level("title:mode:meta", "title:content")
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
            ladder_title = self.fonts.small.render("Campaign Ladder", True, INFO)
            surface.blit(ladder_title, (summary_rect.left, top + 6))
            top += 28
            for step in self._meta_progression.campaign_ladder[:6]:
                consumed = draw_wrapped_text(
                    surface,
                    self.fonts.small,
                    step,
                    TEXT,
                    pygame.Rect(summary_rect.left, top, summary_rect.width, 22),
                    line_height=15,
                    max_lines=1,
                )
                top += max(18, consumed)

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
        browser_motion = self._motion_level(f"title:mode:{mode_key}", "title:content")
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
        if not cards:
            empty_surface = self.fonts.body.render("Nothing is stored here yet.", True, MUTED)
            surface.blit(empty_surface, (inner.left, inner.top))
            note_surface = self.fonts.small.render(back_detail, True, MUTED)
            surface.blit(note_surface, (inner.left, inner.top + 26))
            return
        top = inner.top
        for index, card in enumerate(cards[:8]):
            card_rect = pygame.Rect(inner.left, top, inner.width, 74)
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
            top += 86
        back_surface = self.fonts.small.render(back_detail, True, MUTED)
        surface.blit(back_surface, (inner.left, rect.bottom - 26))

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
            empty_surface = self.fonts.body.render("Select a save slot first.", True, MUTED)
            surface.blit(empty_surface, (inner.left, inner.top))
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
        for title, detail, payload, accent in buttons:
            button_rect = pygame.Rect(inner.left, top, inner.width, 54)
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
            self._click_targets.append(ClickTarget("slot_action", payload, button_rect))
            top += 66

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
                scenario.title,
                scenario.description,
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
        top = inner.top
        for label, value, detail, payload, kind, accent in rows:
            button_rect = pygame.Rect(inner.left, top, inner.width, 56)
            draw_button(
                surface,
                pygame,
                rect=button_rect,
                title=f"{label}: {value}",
                detail=detail,
                accent=accent,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
            )
            self._click_targets.append(ClickTarget(kind, payload, button_rect))
            top += 66
        launch_rect = pygame.Rect(inner.left, rect.bottom - 86, inner.width // 2 - 8, 44)
        back_rect = pygame.Rect(
            launch_rect.right + 16,
            rect.bottom - 86,
            inner.width // 2 - 8,
            44,
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
            message = "Menu: 1 continue, 2 saves, 3 archives, 4 meta board, 5 wizard, 6 quit."
        elif self._mode == "meta":
            message = "Meta board: 1 archives, 2 saves, 3 wizard, 9 back."
        elif self._mode == "slots":
            message = "Saves: click a card to manage it. Press 9 or Esc to return."
        elif self._mode == "slot_detail":
            message = "Slot: 1 load, 2 rename, 3 duplicate, 4 delete, 9 back."
        elif self._mode == "wizard":
            message = "Wizard: click rows to cycle/edit. Enter launches. Esc returns to menu."
        else:
            message = "Archives: click a card to inspect it. Press 9 or Esc to return."
        footer_surface = self.fonts.small.render(message, True, TEXT)
        surface.blit(footer_surface, (inner.left, inner.top + 10))

    def _title_sidebar_lines(self) -> tuple[str, ...]:
        meta = self._meta_progression
        comparison = self._archive_comparison
        if self._mode == "wizard":
            scenario = self.selected_scenario_choice
            campaign_start = self.selected_campaign_start_choice
            difficulty = self.selected_difficulty_choice
            return (
                f"Scenario: {scenario.title}",
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
                f"Meta next reward: {meta.next_reward}",
            )
        if self._mode == "meta":
            return (
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
                f"Archive progress: {meta.achievement_progress} | "
                f"outcomes {meta.outcome_coverage_progress}"
            ),
            f"Next goal: {meta.next_goal}",
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
        if compact:
            return (
                f"Campaign tier: {meta.campaign_tier} | stage: {meta.campaign_stage}",
                (
                    f"Runs {meta.total_runs} | victories {meta.victories} | "
                    f"best score {meta.best_score}"
                ),
                f"Next reward: {meta.next_reward}",
                f"Coverage gap: {comparison.next_gap}",
            )
        return (
            f"Campaign tier: {meta.campaign_tier} | stage: {meta.campaign_stage}",
            (
                f"Runs: {meta.total_runs} | victories: {meta.victories} | "
                f"best score: {meta.best_score}"
            ),
            f"Next goal: {meta.next_goal}",
            f"Next reward: {meta.next_reward}",
            f"Dominant path: {comparison.dominant_path}",
            f"Coverage gap: {comparison.next_gap}",
            f"Recommendation: {comparison.recommendation}",
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
        title_surface = self.fonts.body.render(timed_event.payload.title, True, TEXT)
        surface.blit(title_surface, (animated_rect.left + 12, animated_rect.top + 10))
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
        )
        self._view_model = view_model
        self._accent = accent
        self._primary_title = primary_title
        self._primary_detail = primary_detail
        self._return_scene_factory = return_scene_factory
        self._allow_save = allow_save
        self._click_targets: list[ClickTarget] = []
        self._motion_pulses = PulseBank(
            decay=1.9,
            intensity_scale=self.motion_mode.pulse_scale,
        )
        self._trigger_review_motion("header", intensity=0.58)
        self._trigger_review_motion("findings", intensity=0.72 if view_model.findings else 0.4)
        self._trigger_review_motion("sidebar", intensity=0.52)
        self._trigger_review_motion("footer", intensity=0.5)

    def update(self, dt: float) -> None:
        self._update_scene_transition(dt)
        self._motion_pulses.update(dt)

    def _trigger_review_motion(self, section_key: str, *, intensity: float = 0.6) -> None:
        self._motion_pulses.trigger(f"review:{section_key}", intensity=intensity, decay=2.2)

    def _motion_level(self, *keys: str) -> float:
        if not keys:
            return 0.0
        return max(self._motion_pulses.get(key) for key in keys)

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
            self._persist_current_run()
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
        draw_grid(surface, pygame)
        width, height = surface.get_size()
        margin = 28
        gap = 16
        header_rect = pygame.Rect(margin, margin, width - margin * 2, 104)
        footer_rect = pygame.Rect(margin, height - 104 - margin, width - margin * 2, 104)
        content_rect = pygame.Rect(
            margin,
            header_rect.bottom + gap,
            width - margin * 2,
            footer_rect.top - gap - header_rect.bottom,
        )
        left_width = int((content_rect.width - gap) * 0.58)
        right_width = content_rect.width - gap - left_width
        left_rect = pygame.Rect(
            content_rect.left, content_rect.top, left_width, content_rect.height
        )
        right_rect = pygame.Rect(
            left_rect.right + gap, content_rect.top, right_width, content_rect.height
        )

        self._draw_review_header(surface, header_rect)
        self._draw_review_findings(surface, left_rect)
        self._draw_review_sidebar(surface, right_rect)
        self._draw_review_footer(surface, footer_rect)
        self._draw_scene_transition_overlay(surface)

    def _dispatch_click_target(self, target: ClickTarget) -> None:
        if target.kind == "review_primary":
            self._primary_action()
            return
        if target.kind == "review_save" and self._allow_save:
            self._persist_current_run()

    def _primary_action(self) -> None:
        if self._return_scene_factory is not None:
            self._next_scene = self._return_scene_factory()
            return
        self.should_exit = True
        self.exit_reason = "quit"

    def _draw_review_header(self, surface, rect) -> None:
        pygame = self.pygame
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
        title_surface = self.fonts.title.render(self._view_model.title, True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 28))
        headline_surface = self.fonts.body.render(self._view_model.headline, True, TEXT)
        surface.blit(headline_surface, (inner.left, inner.top))
        summary_surface = self.fonts.small.render(self._view_model.summary_line, True, MUTED)
        surface.blit(summary_surface, (inner.left, inner.top + 26))

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
        for finding in self._view_model.findings:
            card_rect = pygame.Rect(inner.left, top, inner.width, 98)
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
            title_surface = self.fonts.body.render(
                f"{finding.rank_label} {finding.area} | {finding.command}",
                True,
                TEXT,
            )
            surface.blit(title_surface, (animated_rect.left + 12, animated_rect.top + 10))
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
            top += 110

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
        focus_surface = self.fonts.body.render(self._view_model.next_focus, True, INFO)
        surface.blit(focus_surface, (inner.left, inner.top))
        badges_title = self.fonts.small.render("Badges", True, MUTED)
        surface.blit(badges_title, (inner.left, inner.top + 30))
        top = inner.top + 52
        for badge in self._view_model.badges[:6]:
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
            badge_surface = self.fonts.small.render(badge.replace("_", " "), True, TEXT)
            surface.blit(badge_surface, (chip_rect.left + 10, chip_rect.top + 7))
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
        primary_rect = pygame.Rect(inner.left, inner.top + 20, 260, 40)
        draw_button(
            surface,
            pygame,
            rect=primary_rect,
            title=self._primary_title,
            detail=self._primary_detail,
            accent=self._accent,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        self._click_targets.append(ClickTarget("review_primary", "", primary_rect))
        if self._allow_save:
            save_rect = pygame.Rect(inner.left + 276, inner.top + 20, 180, 40)
            draw_button(
                surface,
                pygame,
                rect=save_rect,
                title="S Save Final",
                detail="Persist the finished run.",
                accent=GOOD,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
            )
            self._click_targets.append(ClickTarget("review_save", "", save_rect))


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
        )
        self._events: list[TimedFrontendEvent] = []
        self._action_feedback_cues: list[ActionFeedbackCue] = []
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

    def _trigger_inspector_motion(self, lane_key: str, *, intensity: float = 0.55) -> None:
        self._trigger_overlay_motion("inspector", intensity=max(0.42, intensity * 0.72))
        self._motion_pulses.trigger(f"inspector:{lane_key}", intensity=intensity, decay=2.0)

    def _set_deep_panel(self, panel_key: str | None) -> None:
        if panel_key == self._deep_panel_key:
            return
        self._deep_panel_key = panel_key
        if panel_key is not None:
            self._trigger_overlay_motion("panel", intensity=0.75)
            self._motion_pulses.trigger(f"panel:{panel_key}", intensity=0.7, decay=2.0)
            if panel_key == "endgame":
                self._announce_endgame_cockpit()

    def _announce_endgame_cockpit(self) -> None:
        panel = self.deep_panel
        if panel is None or panel.key != "endgame":
            return
        blocked_line = next(
            (line for line in panel.detail_lines if line.lower().startswith("blocked paths:")),
            panel.detail_lines[0] if panel.detail_lines else panel.summary,
        )
        gate_action = next(
            (action for action in panel.actions if action.label == "Gate Command"), None
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
        self._context_picker = picker
        if picker is not None:
            self._trigger_overlay_motion("picker", intensity=0.78)

    def _set_text_input(self, modal: TextInputModalState | None) -> None:
        self._text_input = modal
        if modal is not None:
            self._trigger_overlay_motion("text_input", intensity=0.78)

    def _set_help_overlay_visible(self, visible: bool) -> None:
        self._help_overlay_visible = visible
        if visible:
            self._trigger_overlay_motion("help", intensity=0.7)

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

        self._motion_elapsed += max(0.0, dt)
        self._tweens.update(dt)
        self._update_scene_transition(dt)
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
            )
            for cue in self._action_feedback_cues
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

        if event.key == self.pygame.K_F1 or event.unicode == "?":
            self._set_help_overlay_visible(not self._help_overlay_visible)
            return

        if event.key == self.pygame.K_ESCAPE:
            if self._help_overlay_visible:
                self._set_help_overlay_visible(False)
                return
            if self._text_input is not None:
                self._set_text_input(None)
                return
            if self._context_picker is not None:
                self._set_context_picker(None)
                return
            if self._inspector_panel_key is not None:
                self._inspector_panel_key = None
                return
            if self._deep_panel_key is not None:
                self._set_deep_panel(None)
                return
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

        if event.key == self.pygame.K_s:
            self._save_current_run()
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
        draw_grid(surface, pygame)
        width, height = surface.get_size()
        margin = 20
        gap = 16
        header_rect = pygame.Rect(margin, margin, width - margin * 2, 118)
        footer_height = 388 if width < 980 else 348 if width < 1180 else 332
        footer_rect = pygame.Rect(
            margin,
            height - footer_height - margin,
            width - margin * 2,
            footer_height,
        )
        content_top = header_rect.bottom + gap
        content_height = footer_rect.top - gap - content_top
        if width < 940:
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
        self._draw_action_feedback_cues(surface)
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
            or self.state.pending_event is not None
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
        label = self.fonts.small.render(panel_key.upper(), True, blend_color(MUTED, accent, 0.7))
        surface.blit(label, (strip_rect.left + 10, strip_rect.top + 9))

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
        if self._text_input is not None or self._context_picker is not None:
            top = 24
        for index, cue in enumerate(self._action_feedback_cues[:3]):
            if cue.duration <= 0:
                continue
            age = max(0.0, cue.duration - cue.time_left)
            enter_ratio = min(1.0, age / 0.18)
            ttl_ratio = max(0.0, min(1.0, cue.time_left / cue.duration))
            intensity = ttl_ratio * (0.62 if self.motion_mode is MotionMode.REDUCED else 1.0)
            slide_x = int((1.0 - enter_ratio) * 26)
            wave = sin(self._entity_motion_phase(offset=index * 0.8, speed=2.4)) * 3 * intensity
            rect = pygame.Rect(
                left + slide_x,
                top + index * (card_height + gap) - int(wave),
                card_width,
                card_height,
            )
            layer = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            layer_rect = layer.get_rect()
            fill = blend_color((8, 13, 22), cue.accent, 0.14 + intensity * 0.08)
            border = blend_color(cue.accent, TEXT, 0.12)
            alpha = int(min(210, 112 + ttl_ratio * 100))
            pygame.draw.rect(layer, (*fill, alpha), layer_rect, border_radius=14)
            pygame.draw.rect(
                layer,
                (*border, int(86 + intensity * 110)),
                layer_rect,
                width=2 if intensity >= 0.6 else 1,
                border_radius=14,
            )
            pygame.draw.rect(
                layer,
                (*cue.accent, int(88 + intensity * 116)),
                pygame.Rect(0, 0, 5, rect.height),
                border_radius=3,
            )
            self._draw_entity_nodes(
                layer,
                pygame.Rect(94, rect.height - 16, max(24, rect.width - 118), 10),
                accent=cue.accent,
                strength=0.36 * intensity,
                count=3,
                offset=float(index) * 1.3,
            )
            surface.blit(layer, rect.topleft)

            label_surface = self.fonts.small.render(cue.label, True, TEXT)
            family_surface = self.fonts.small.render(
                cue.family.upper(),
                True,
                blend_color(MUTED, cue.accent, 0.82),
            )
            target_text = " / ".join(
                target.removeprefix("panel:")
                .removeprefix("stat:")
                .removeprefix("summary:")
                .removeprefix("overlay:")
                for target in cue.targets[:2]
            )
            target_surface = self.fonts.small.render(
                self._compact_button_detail(target_text, max_length=28),
                True,
                MUTED,
            )
            surface.blit(label_surface, (rect.left + 14, rect.top + 8))
            surface.blit(
                family_surface, (rect.right - family_surface.get_width() - 14, rect.top + 8)
            )
            surface.blit(target_surface, (rect.left + 14, rect.top + 24))
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

    def _overlay_fill(self, overlay_key: str) -> tuple[int, int, int, int]:
        pulse = self._overlay_motion_level(overlay_key)
        alpha = min(224, 180 + int(pulse * 36))
        return (8, 10, 14, alpha)

    def _handle_mouse_click(self, position: tuple[int, int]) -> None:
        for target in reversed(self._click_targets):
            if target.rect.collidepoint(position):
                self._dispatch_click_target(target)
                return

    def _dispatch_click_target(self, target: ClickTarget) -> None:
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
        if target.kind == "close_panel":
            self._set_deep_panel(None)
            return
        if target.kind == "close_inspector":
            self._inspector_panel_key = None
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

    def _command_disabled_reason(self, command: str) -> str | None:
        if self.state.company.game_over or self.state.victory_achieved:
            return "This run is already complete."
        return explain_command_unavailable(
            self.state,
            command=command,
            selected_product_id=self.selected_product.id.hex,
        )

    def _push_action_blocked_event(self, command: str, reason: str) -> None:
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
            pygame.K_p: FrontendIntent.CREATE_PARTNERSHIP,
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
            self.push_event(
                FrontendEvent(
                    title="Action Rejected",
                    detail=str(error),
                    severity="warning",
                    ttl=5.5,
                )
            )
            return

        self._queue_action_feedback(request.action.value)
        self.state = outcome.state
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
            entry_transition="run_to_summary",
        )

    def _save_current_run(self) -> None:
        self._persist_current_run()
        self.push_event(
            FrontendEvent(
                title="Game Saved",
                detail=f"Saved the 2D run back to slot `{self.slot_name}`.",
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
            primary_title="Esc Close",
            primary_detail="Leave the 2D shell.",
            return_scene_factory=None,
            allow_save=True,
            dirty=self._dirty,
            motion_mode=self.motion_mode,
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
                detail=f"`{action.command}` still needs a 2D request path for this item.",
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
        inner = draw_panel(surface, pygame, rect, title="Run Header", accent=INFO)
        title_surface = self.fonts.title.render(
            f"{self._view_model.company_name} | {self._view_model.turn_label}",
            True,
            TEXT,
        )
        surface.blit(title_surface, (inner.left, inner.top - 28))
        meta_text = (
            f"{self._view_model.scenario_title} | difficulty {self._view_model.difficulty_label} | "
            f"score {self._view_model.score_label} | market {self._view_model.market_label}"
        )
        draw_wrapped_text(
            surface,
            self.fonts.body,
            meta_text,
            MUTED,
            pygame.Rect(inner.left, inner.top, inner.width, 20),
            line_height=18,
            max_lines=1,
        )
        draw_wrapped_text(
            surface,
            self.fonts.small,
            self._view_model.header_note,
            TEXT,
            pygame.Rect(inner.left, inner.top + 22, inner.width, 18),
            line_height=15,
            max_lines=1,
        )
        draw_wrapped_text(
            surface,
            self.fonts.small,
            self._view_model.difficulty_summary,
            MUTED,
            pygame.Rect(inner.left, inner.top + 42, inner.width, 18),
            line_height=15,
            max_lines=1,
        )
        chip_width = int((inner.width - 24) / 3)
        chip_height = 28
        top = inner.top + 66
        left = inner.left
        for index, chip in enumerate(self._view_model.snapshot_chips):
            if index and index % 3 == 0:
                top += chip_height + 8
                left = inner.left
            chip_rect = pygame.Rect(left, top, chip_width, chip_height)
            self._draw_snapshot_chip(surface, chip_rect, chip.label, chip.value_text, chip.tone)
            left += chip_width + 12

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
        header_surface = self.fonts.heading.render("Company Stats", True, TEXT)
        surface.blit(header_surface, (inner.left, inner.top - 24))
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
            title_surface = self.fonts.small.render(
                gauge.title.upper(),
                True,
                blend_color(MUTED, tone_color(gauge.tone), gauge_motion * 0.7),
            )
            value_surface = self.fonts.mono.render(
                gauge.value_text,
                True,
                blend_color(TEXT, tone_color(gauge.tone), gauge_motion * 0.18),
            )
            surface.blit(title_surface, (inner.left, top))
            surface.blit(value_surface, (inner.right - value_surface.get_width(), top))
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
        preview_header = self.fonts.heading.render("End-Turn Preview", True, TEXT)
        surface.blit(preview_header, (preview_inner.left, preview_inner.top - 24))
        warning_surface = self.fonts.body.render(
            f"Warning: {self._view_model.preview_warning}",
            True,
            tone_color("danger" if self._view_model.preview_warning == "critical" else "warning"),
        )
        surface.blit(warning_surface, (preview_inner.left, preview_inner.top))
        outcome_surface = self.fonts.small.render(
            f"Outcome: {self._view_model.preview_outcome}",
            True,
            TEXT,
        )
        surface.blit(outcome_surface, (preview_inner.left, preview_inner.top + 24))
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
        title_surface = self.fonts.heading.render("Product Strip", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 24))
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
        coach_height = int(rect.height * 0.5)
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
        title_surface = self.fonts.heading.render("Turn Coach / Control Tower", True, TEXT)
        surface.blit(title_surface, (coach_inner.left, coach_inner.top - 24))
        top = coach_inner.top
        for line in self._view_model.coach_lines:
            card_rect = pygame.Rect(coach_inner.left, top, coach_inner.width, 66)
            line_panel = self._workspace_panel_key_for_command(line.command)
            line_motion = (
                self._motion_level(f"panel:{line_panel}") if line_panel is not None else 0.0
            )
            draw_button(
                surface,
                pygame,
                rect=card_rect,
                title=line.command,
                detail=line.source,
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

        deferred_title = self.fonts.small.render("Not Now", True, WARN)
        surface.blit(deferred_title, (coach_inner.left, top + 4))
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
        risk_title = self.fonts.small.render("Risk Forecast", True, DANGER)
        surface.blit(risk_title, (coach_inner.left, deferred_top + 8))
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
        event_title = self.fonts.heading.render("Animated Event Queue", True, TEXT)
        surface.blit(event_title, (event_inner.left, event_inner.top - 24))
        if not self._events:
            idle_surface = self.fonts.body.render("No transient events yet.", True, MUTED)
            surface.blit(idle_surface, (event_inner.left, event_inner.top))
            return
        event_top = event_inner.top
        for timed_event in self._events[: self._event_queue_visible_count(event_rect.height)]:
            card_rect = pygame.Rect(event_inner.left, event_top, event_inner.width, 66)
            self._draw_event_card(surface, card_rect, timed_event)
            event_top += 76

    def _draw_footer(self, surface, rect) -> None:
        pygame = self.pygame
        footer_motion = self._motion_level("footer")
        inner = draw_panel(
            surface,
            pygame,
            rect,
            title="Actions",
            accent=INFO,
            emphasis=footer_motion,
            lift=int(footer_motion * 2),
        )
        title_surface = self.fonts.heading.render("Action Bar", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 24))
        button_cols, button_height, footer_band_height = self._footer_layout_metrics(
            inner.width,
            inner.height,
        )
        button_gap = 10
        button_width = int((inner.width - button_gap * (button_cols - 1)) / button_cols)
        top = inner.top
        left = inner.left
        for index, button in enumerate(_ACTION_BUTTONS):
            if index and index % button_cols == 0:
                top += button_height + 10
                left = inner.left
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
                title=f"{button.key_hint} {button.title}",
                detail=self._footer_button_detail(
                    button,
                    enabled=enabled,
                    button_cols=button_cols,
                ),
                accent=button.accent,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
                enabled=enabled,
                selected=selected,
                emphasis=button_motion,
                lift=int(button_motion * 2),
            )
            self._click_targets.append(ClickTarget(button.kind, button.payload, button_rect))
            left += button_width + button_gap
        footer_top = inner.bottom - footer_band_height + 6
        status_line, hint_line = self._footer_status_lines()
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

    def _footer_layout_metrics(self, inner_width: int, inner_height: int) -> tuple[int, int, int]:
        if inner_width < 860:
            button_cols = 4
        elif inner_width < 1040:
            button_cols = 5
        elif inner_width < 1240:
            button_cols = 6
        else:
            button_cols = 7
        rows = max(1, (len(_ACTION_BUTTONS) + button_cols - 1) // button_cols)
        footer_band_height = 52 if button_cols <= 4 else 48
        button_gap = 10
        button_area_height = max(
            50,
            inner_height - footer_band_height - button_gap * max(0, rows - 1),
        )
        button_height = min(62, max(50, int(button_area_height / rows)))
        return button_cols, button_height, footer_band_height

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
        max_length = 30 if button_cols <= 4 else 34 if button_cols == 5 else 40
        return self._compact_button_detail(detail, max_length=max_length)

    def _footer_status_lines(self) -> tuple[str, str]:
        workspace_key = self._active_panel_key()
        workspace_title = (
            self._panel_display_name(workspace_key) if workspace_key is not None else "Core HUD"
        )
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
        else:
            primary = (
                f"Workspace: {workspace_title} | Product: {self.selected_product.name} | "
                f"Actions Left: {self.state.action_points_remaining}"
            )
        hint = self._hover_hint_line() or f"Watch: {self._view_model.watch_for}"
        return primary, hint

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
            (action for action in panel.actions if action.label == "Gate Command"),
            None,
        )
        hotspot_action = next(
            (action for action in panel.actions if action.label == "Hotspot Review"),
            None,
        )
        segments = [f"{'Endgame' if compact else 'Workspace'}: {workspace_title}"]
        if gate_action is not None:
            segments.append(
                f"Gate: {self._compact_command_token(gate_action.command, compact=compact)}"
            )
        if hotspot_action is not None:
            segments.append(
                f"Hotspot: {self._compact_command_token(hotspot_action.command, compact=compact)}"
            )
        segments.append(f"Actions Left: {self.state.action_points_remaining}")
        return " | ".join(segments)

    def _window_width(self) -> int:
        surface = self.pygame.display.get_surface()
        if surface is None:
            return 1280
        return surface.get_size()[0]

    def _compact_command_token(self, command: str, *, compact: bool) -> str:
        if not compact:
            return command
        command = command.replace("review_", "review:")
        command = command.replace("run_", "")
        command = command.replace("set_", "")
        command = command.replace("execute_", "")
        return self._compact_button_detail(command.replace("_", " "), max_length=24)

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
        mouse_pos = self.pygame.mouse.get_pos()
        for target in reversed(self._click_targets):
            if target.rect.collidepoint(mouse_pos):
                return target
        return None

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
            if reason is not None:
                return f"Hover: `{target.payload}` is blocked because {reason}"
            if target.kind == "panel_action" and self._deep_panel_key == "endgame":
                workspace_key = self._workspace_panel_key_for_command(target.payload)
                inspector_key = self._inspector_key_for_command(target.payload)
                destination = inspector_key or workspace_key
                if destination is not None:
                    return (
                        f"Hover: run `{target.payload}` from the cockpit and hand off into "
                        f"{self._panel_display_name(destination)}."
                    )
            return f"Hover: run `{target.payload}` now."
        if target.kind == "panel":
            return f"Hover: open the {target.payload} deep-dive panel."
        if target.kind == "open_panel_inspector":
            return f"Hover: inspect the `{target.payload}` panel in full detail."
        if target.kind == "coach":
            return "Hover: run the top mission-board recommendation."
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
        title_surface = self.fonts.heading.render(product.name, True, TEXT)
        subtitle_surface = self.fonts.small.render(
            f"{product.stage} | {product.segment} | users {product.users_text}",
            True,
            blend_color(MUTED, INFO, product_motion * 0.22),
        )
        revenue_surface = self.fonts.small.render(
            product.revenue_text,
            True,
            blend_color(INFO, TEXT, product_motion * 0.18),
        )
        surface.blit(title_surface, (visual_rect.left + 14, visual_rect.top + 12))
        surface.blit(subtitle_surface, (visual_rect.left + 14, visual_rect.top + 36))
        surface.blit(
            revenue_surface,
            (visual_rect.right - revenue_surface.get_width() - 14, visual_rect.top + 14),
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
            label_surface = self.fonts.small.render(
                label,
                True,
                blend_color(MUTED, color, emphasis * 0.5),
            )
            surface.blit(label_surface, (visual_rect.left + 14, start_y + index * 20))
            bar_rect = pygame.Rect(
                visual_rect.left + 78,
                start_y + 2 + index * 20,
                visual_rect.width - 92,
                12,
            )
            draw_progress_bar(
                surface, pygame, bar_rect, ratio=ratio, color=color, emphasis=emphasis
            )

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
        title_surface = self.fonts.body.render(timed_event.payload.title, True, TEXT)
        surface.blit(title_surface, (visual_rect.left + 12, visual_rect.top + 10))
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
        overlay_motion = self._overlay_motion_level("pending")
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(self._overlay_fill("pending"))
        surface.blit(overlay, (0, 0))
        modal_rect = _fit_modal_rect(pygame, surface, width=560, height=360, margin=24)
        inner = draw_panel(
            surface,
            pygame,
            modal_rect,
            title="Pending Event",
            accent=WARN,
            emphasis=overlay_motion,
            lift=int(overlay_motion * 5),
        )
        event_model = self._view_model.pending_event
        if event_model is None:
            return
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
            draw_button(
                surface,
                pygame,
                rect=option_rect,
                title=f"{option.key_hint} {option.label}",
                detail=option.description,
                accent=WARN,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
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
        overlay_motion = self._overlay_motion_level("panel")
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(self._overlay_fill("panel"))
        surface.blit(overlay, (0, 0))
        modal_rect = _fit_modal_rect(pygame, surface, width=940, height=560, margin=24)
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
        title_surface = self.fonts.title.render(panel.title, True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 28))
        self._draw_panel_entity_strip(
            surface,
            pygame.Rect(inner.right - 190, inner.top - 30, 190, 28),
            panel_key=panel.key,
            strength=self._entity_motion_strength(f"panel:{panel.key}", "overlay:panel"),
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
        for index, metric in enumerate(panel.metrics[:4]):
            row = index // 2
            col = index % 2
            card_rect = pygame.Rect(
                inner.left + col * (metric_width + 12),
                metric_top + row * 54,
                metric_width,
                42,
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
            surface.blit(label_surface, (card_rect.left + 10, card_rect.top + 6))
            surface.blit(value_surface, (card_rect.left + 10, card_rect.top + 20))

        detail_rect = pygame.Rect(
            inner.left, inner.top + 170, int(inner.width * 0.56), inner.height - 196
        )
        action_rect = pygame.Rect(
            detail_rect.right + 20,
            inner.top + 170,
            inner.right - detail_rect.right - 20,
            inner.height - 196,
        )
        detail_title = self.fonts.heading.render("Live Notes", True, TEXT)
        surface.blit(detail_title, (detail_rect.left, detail_rect.top - 24))
        top = detail_rect.top
        for line in panel.detail_lines:
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

        action_title = self.fonts.heading.render("Panel Actions", True, TEXT)
        surface.blit(action_title, (action_rect.left, action_rect.top - 24))
        cols = 2
        button_gap = 10
        button_width = int((action_rect.width - button_gap * (cols - 1)) / cols)
        button_height = 54
        top = action_rect.top
        left = action_rect.left
        for index, action in enumerate(panel.actions):
            if index and index % cols == 0:
                top += button_height + 10
                left = action_rect.left
            button_rect = pygame.Rect(left, top, button_width, button_height)
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

        inspect_rect = pygame.Rect(action_rect.left, modal_rect.bottom - 56, 170, 34)
        close_rect = pygame.Rect(action_rect.left + 184, modal_rect.bottom - 56, 160, 34)
        if panel.inspectors:
            draw_button(
                surface,
                pygame,
                rect=inspect_rect,
                title="I Open Inspector",
                detail="Inspect this panel in detail.",
                accent=SELECTION,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
            )
            self._click_targets.append(ClickTarget("open_panel_inspector", panel.key, inspect_rect))
        draw_button(
            surface,
            pygame,
            rect=close_rect,
            title="Esc Close",
            detail="Return to the run.",
            accent=BORDER,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        self._click_targets.append(ClickTarget("close_panel", "", close_rect))

    def _draw_inspector_overlay(self, surface) -> None:
        pygame = self.pygame
        panel = self.inspector_panel
        if panel is None:
            return
        overlay_motion = self._overlay_motion_level("inspector")
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(self._overlay_fill("inspector"))
        surface.blit(overlay, (0, 0))
        modal_rect = _fit_modal_rect(pygame, surface, width=1040, height=600, margin=24)
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
        title_surface = self.fonts.title.render(f"{panel.title} Inspector", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 28))
        draw_wrapped_text(
            surface,
            self.fonts.body,
            panel.summary,
            MUTED,
            pygame.Rect(inner.left, inner.top, inner.width, 42),
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
        nav_rect = pygame.Rect(inner.left, nav_top, nav_width, inner.bottom - nav_top - 56)
        focus_rect = pygame.Rect(
            nav_rect.right + 18,
            nav_top,
            inner.right - nav_rect.right - 18,
            inner.bottom - nav_top - 56,
        )
        self._draw_inspector_section_nav(surface, nav_rect, panel)
        self._draw_inspector_focus(surface, focus_rect)

        close_rect = pygame.Rect(inner.left, modal_rect.bottom - 56, 180, 34)
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
        sort_rect = pygame.Rect(nav_inner.left, nav_inner.top, nav_inner.width, 40)
        filter_rect = pygame.Rect(nav_inner.left, nav_inner.top + 48, nav_inner.width, 40)
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
        actionable_rect = pygame.Rect(nav_inner.left, nav_inner.top + 96, action_width, 40)
        hotspot_rect = pygame.Rect(
            actionable_rect.right + 10,
            nav_inner.top + 96,
            nav_inner.width - action_width - 10,
            40,
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
        top = nav_inner.top + 148
        for index, section in enumerate(panel.inspectors):
            button_rect = pygame.Rect(nav_inner.left, top, nav_inner.width, 56)
            selected = index == self._inspector_section_index
            accent = SELECTION if selected else tone_color(section.tone)
            draw_button(
                surface,
                pygame,
                rect=button_rect,
                title=section.title,
                detail=self._section_button_detail(section, selected=selected),
                accent=accent,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
            )
            self._click_targets.append(ClickTarget("inspector_section", section.key, button_rect))
            top += 66

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

    def _draw_help_overlay(self, surface) -> None:
        pygame = self.pygame
        overlay_motion = self._overlay_motion_level("help")
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(self._overlay_fill("help"))
        surface.blit(overlay, (0, 0))
        modal_rect = _fit_modal_rect(pygame, surface, width=860, height=520, margin=28)
        inner = draw_panel(
            surface,
            pygame,
            modal_rect,
            title="Help",
            accent=INFO,
            emphasis=overlay_motion,
            lift=int(overlay_motion * 5),
        )
        title_surface = self.fonts.title.render("2D Control Guide", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 28))
        draw_wrapped_text(
            surface,
            self.fonts.body,
            (
                "This frontend is now self-contained for the main run loop. "
                "Use these controls to move between products, panels, inspectors, "
                "the endgame board, and turn resolution without dropping back to the CLI."
            ),
            MUTED,
            pygame.Rect(inner.left, inner.top, inner.width, 48),
            line_height=18,
            max_lines=3,
        )
        keycaps = (
            ("Tab", "Next product / next inspector section"),
            ("1-8", "Open deep panels"),
            ("I", "Inspect the current deep panel"),
            ("C", "Run primary coach command"),
            ("Q/F/M/D", "Product actions"),
            ("H/A/Y/R/B/U", "Team / strategy / budget / support"),
            ("Space", "End turn"),
            ("Z/X", "Inspector sort / filter"),
            ("A/H", "Inspector actionable / hotspot focus"),
            ("PgUp/PgDn", "Inspector page"),
            ("Enter", "Run selected inspector action"),
            ("F1/?", "Toggle this help"),
        )
        top = inner.top + 72
        for key_text, label in keycaps:
            keycap_rect = pygame.Rect(inner.left, top, inner.width, 28)
            draw_keycap(
                surface,
                pygame,
                self.fonts.small,
                rect=keycap_rect,
                key_text=key_text,
                label=label,
            )
            top += 36
        close_rect = pygame.Rect(inner.left, modal_rect.bottom - 56, 180, 36)
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
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(OVERLAY)
        surface.blit(overlay, (0, 0))
        modal_rect = _fit_modal_rect(pygame, surface, width=520, height=264, margin=24)
        accent = GOOD if self.state.victory_achieved else DANGER
        inner = draw_panel(surface, pygame, modal_rect, title="Run Complete", accent=accent)
        title = "Victory Achieved" if self.state.victory_achieved else "Company Shutdown"
        title_surface = self.fonts.title.render(title, True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 26))
        detail = (
            self.state.victory_reason
            or self.state.exit_summary
            or "Press S to save or Esc to close the frontend."
        )
        draw_wrapped_text(
            surface,
            self.fonts.body,
            detail,
            MUTED,
            pygame.Rect(inner.left, inner.top + 8, inner.width, 90),
            line_height=18,
            max_lines=4,
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
            title="S Save",
            detail="Persist the final run.",
            accent=GOOD,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        draw_button(
            surface,
            pygame,
            rect=close_rect,
            title="Esc Close",
            detail="Leave the 2D shell.",
            accent=accent,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        self._click_targets.append(ClickTarget("open_review", "", review_rect))
        self._click_targets.append(ClickTarget("save", "", save_rect))
        self._click_targets.append(ClickTarget("close_outcome", "", close_rect))

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
        label_surface = self.fonts.small.render(label.upper(), True, MUTED)
        value_surface = self.fonts.small.render(value, True, TEXT)
        surface.blit(label_surface, (rect.left + 10, rect.top + 8))
        surface.blit(value_surface, (rect.right - value_surface.get_width() - 10, rect.top + 8))

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
        )
        self._previous_state = previous_state
        self._resolution = resolution
        self._selected_product_id = selected_product_id
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
        draw_grid(surface, pygame)
        width, height = surface.get_size()
        margin = 24
        gap = 16
        header_rect = pygame.Rect(margin, margin, width - margin * 2, 96)
        footer_rect = pygame.Rect(margin, height - 94 - margin, width - margin * 2, 94)
        content_top = header_rect.bottom + gap
        content_height = footer_rect.top - gap - content_top
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
        self._draw_summary_main(surface, left_rect)
        self._draw_summary_timeline(surface, right_rect)
        self._draw_summary_footer(surface, footer_rect)
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
                primary_title="Esc Close",
                primary_detail="Leave the 2D shell.",
                return_scene_factory=None,
                allow_save=True,
                dirty=self._dirty,
                motion_mode=self.motion_mode,
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
            entry_transition="summary_to_run",
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
            detail=f"{self._view_model.focus_command}: {self._view_model.focus_detail}",
            severity=severity,
            ttl=5.2 if severity == "warning" else 4.8,
            motion="flash" if severity == "warning" else "slide",
            targets=targets,
        )

    def _draw_summary_header(self, surface, rect) -> None:
        pygame = self.pygame
        inner = draw_panel(surface, pygame, rect, title="Turn Summary", accent=INFO)
        title_surface = self.fonts.title.render(self._view_model.title, True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 28))
        headline_surface = self.fonts.body.render(self._view_model.headline, True, INFO)
        surface.blit(headline_surface, (inner.left, inner.top))
        phase_left = inner.right - 310
        for index, label in enumerate(self._view_model.phase_labels):
            chip_rect = pygame.Rect(phase_left + index * 100, inner.top, 92, 20)
            color = SELECTION if index <= self._phase_index() else BORDER
            fill = (34, 47, 66) if index <= self._phase_index() else (24, 35, 50)
            pygame.draw.rect(surface, fill, chip_rect, border_radius=10)
            pygame.draw.rect(surface, color, chip_rect, width=1, border_radius=10)
            chip_text_color = TEXT if index <= self._phase_index() else MUTED
            chip_surface = self.fonts.small.render(label, True, chip_text_color)
            surface.blit(chip_surface, (chip_rect.left + 8, chip_rect.top + 4))
        draw_wrapped_text(
            surface,
            self.fonts.small,
            self._view_model.narrative,
            MUTED,
            pygame.Rect(inner.left, inner.top + 24, inner.width, 40),
            line_height=16,
            max_lines=2,
        )

    def _draw_summary_main(self, surface, rect) -> None:
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
            card_rect = pygame.Rect(left, top, card_width, card_height)
            self._draw_metric_card(surface, card_rect, metric)
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
        for product_line in visible_products:
            line_rect = pygame.Rect(product_inner.left, top, product_inner.width, 56)
            color = tone_color(product_line.tone)
            pygame.draw.rect(surface, (26, 38, 55), line_rect, border_radius=14)
            pygame.draw.rect(surface, color, line_rect, width=1, border_radius=14)
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

    def _draw_summary_timeline(self, surface, rect) -> None:
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
        visible_lines = self._view_model.strategic_lines[: (2 if compact else 3)]
        for line in visible_lines:
            consumed = draw_wrapped_text(
                surface,
                self.fonts.small,
                line,
                MUTED,
                pygame.Rect(inner.left, top, inner.width, 22 if compact else 34),
                line_height=15,
                max_lines=1 if compact else 2,
            )
            top += max(20, consumed)

    def _summary_focus_command_title(self, *, max_length: int = 28) -> str:
        command = self._compact_summary_text(
            self._view_model.focus_command,
            max_length=max_length,
        )
        return f"Next {command}"

    def _summary_focus_command_detail(self) -> str:
        return ""

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
        footer_surface = self.fonts.small.render(
            "Press Space or click Continue." if compact else self._view_model.footer,
            True,
            TEXT,
        )
        surface.blit(footer_surface, (inner.left, inner.top - 2))
        continue_rect = pygame.Rect(inner.left, inner.top + 24, 200, 38)
        save_rect = pygame.Rect(inner.left + 216, inner.top + 24, 170, 38)
        close_rect = pygame.Rect(inner.left + 402, inner.top + 24, 170, 38)
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

    def _draw_metric_card(self, surface, rect, metric) -> None:
        pygame = self.pygame
        color = tone_color(metric.tone)
        metric_motion = self._summary_motion_level("summary:metrics", metric.key)
        visual_rect = pygame.Rect(
            rect.left, rect.top - int(metric_motion * 3), rect.width, rect.height
        )
        pygame.draw.rect(
            surface,
            blend_color((26, 38, 55), color, metric_motion * 0.14),
            visual_rect,
            border_radius=14,
        )
        pygame.draw.rect(
            surface,
            blend_color(color, TEXT, metric_motion * 0.12),
            visual_rect,
            width=2 if metric_motion >= 0.4 else 1,
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
