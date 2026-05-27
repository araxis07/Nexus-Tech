"""Scene objects for the lightweight 2D frontend."""

from __future__ import annotations

from dataclasses import dataclass
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
    explain_command_unavailable,
)
from nexus_tech.frontend_2d.event_queue import (
    FrontendEvent,
    build_action_events,
    build_turn_resolution_events,
)
from nexus_tech.frontend_2d.input_map import FrontendIntent
from nexus_tech.frontend_2d.tween import TweenBank
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
    draw_button,
    draw_grid,
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
    ) -> None:
        self.pygame = pygame
        self.fonts = fonts
        self.state = state
        self.rng = rng
        self.slot_name = slot_name
        self._save_callback = save_callback
        self._dirty = dirty
        self.should_exit = False
        self.exit_reason = "quit"
        self._next_scene: BaseScene | None = None

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
    ) -> None:
        super().__init__(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=rng,
            slot_name=slot_name,
            save_callback=save_callback,
            dirty=False,
        )
        self.coordinator = coordinator
        self._mode = initial_mode
        self._click_targets: list[ClickTarget] = []
        self._events: list[TimedFrontendEvent] = []
        self._text_input: TextInputModalState | None = None
        self._save_cards: tuple[SaveSlotCardViewModel, ...] = ()
        self._archive_cards: tuple[ArchiveCardViewModel, ...] = ()
        self._save_summaries_by_slot: dict[str, SaveSlotSummary] = {}
        self._archives_by_key: dict[str, RunArchiveSummary] = {}
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
        self._events = [
            TimedFrontendEvent(payload=event.payload, time_left=event.time_left - dt)
            for event in self._events
            if event.time_left - dt > 0
        ]

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
                self._text_input = None
                return
            self._handle_text_input_key(event)
            return
        if self._confirm_delete_slot_name is not None:
            if event.key == self.pygame.K_ESCAPE:
                self._confirm_delete_slot_name = None
            elif event.key in (self.pygame.K_RETURN, self.pygame.K_KP_ENTER):
                self._delete_selected_slot()
            return
        if event.key == self.pygame.K_ESCAPE:
            if self._mode != "menu":
                self._mode = "slots" if self._mode == "slot_detail" else "menu"
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
        left_width = int((width - margin * 2 - gap) * 0.62)
        right_width = width - margin * 2 - gap - left_width
        left_rect = pygame.Rect(margin, content_top, left_width, content_height)
        right_rect = pygame.Rect(left_rect.right + gap, content_top, right_width, content_height)

        self._draw_title_header(surface, header_rect)
        if self._mode == "menu":
            self._draw_title_menu(surface, left_rect)
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

    def push_event(self, payload: FrontendEvent) -> None:
        self._events.insert(0, TimedFrontendEvent(payload=payload, time_left=payload.ttl))
        self._events = self._events[:5]

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
            self._mode = "menu"
            return
        if target.kind == "confirm_delete":
            self._delete_selected_slot()
            return
        if target.kind == "cancel_delete":
            self._confirm_delete_slot_name = None
            return
        if target.kind == "submit_text":
            self._submit_text_modal()
            return
        if target.kind == "cancel_text":
            self._text_input = None
            return

    def _handle_digit_shortcut(self, digit: int) -> None:
        if self._mode == "menu":
            self._handle_menu_action(
                {
                    1: "continue",
                    2: "load_slots",
                    3: "archives",
                    4: "new_wizard",
                    5: "quit",
                }.get(digit, "")
            )
            return
        if self._mode == "slots":
            if digit == 9:
                self._mode = "menu"
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
                self._mode = "menu"
                return
            index = digit - 1
            if 0 <= index < len(self._archive_cards):
                self._open_archive_review(self._archive_cards[index].archive_key)
            return
        if self._mode == "wizard":
            if digit == 8:
                self._mode = "menu"
            elif digit == 9:
                self._launch_wizard_run()

    def _handle_menu_action(self, action: str) -> None:
        if action == "continue":
            self._continue_last_save()
            return
        if action == "load_slots":
            self._mode = "slots"
            return
        if action == "archives":
            self._mode = "archives"
            return
        if action == "new_wizard":
            self._mode = "wizard"
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
        )

    def _open_slot_detail(self, slot_name: str) -> None:
        if slot_name not in self._save_summaries_by_slot:
            return
        self._selected_slot_name = slot_name
        self._mode = "slot_detail"

    def _spawn_scene(self, mode: str) -> "TitleScene":
        return TitleScene(
            pygame=self.pygame,
            fonts=self.fonts,
            state=self.state,
            rng=self.rng,
            slot_name=self.slot_name,
            save_callback=self._save_callback,
            coordinator=self.coordinator,
            initial_mode=mode,
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
            self._mode = "slots"
            return
        slot_name = self._selected_slot_name
        if slot_name is None:
            return
        if action == "load":
            self._load_slot(slot_name)
            return
        if action == "rename":
            self._text_input = TextInputModalState(
                title="Rename Save Slot",
                description=f"Enter the new name for `{slot_name}`.",
                severity="warning",
                submit_title="Enter Rename",
                submit_detail="Rename the selected save slot.",
                text=slot_name,
                placeholder="Save slot name",
                on_submit=self._rename_selected_slot,
            )
            return
        if action == "duplicate":
            self._text_input = TextInputModalState(
                title="Duplicate Save Slot",
                description=f"Enter the name for the duplicate of `{slot_name}`.",
                severity="info",
                submit_title="Enter Duplicate",
                submit_detail="Create another save slot with the same run.",
                text=f"{slot_name}-copy",
                placeholder="Save slot name",
                on_submit=self._duplicate_selected_slot,
            )
            return
        if action == "delete":
            self._confirm_delete_slot_name = slot_name

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
        self._confirm_delete_slot_name = None
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
        self._mode = "slots"
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
        self._text_input = TextInputModalState(
            title=title,
            description=description,
            severity="info",
            submit_title="Enter Apply",
            submit_detail="Apply this value to the new-run wizard.",
            text=text,
            placeholder=placeholder,
            on_submit=callback,
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
        self._text_input = None
        modal.on_submit(modal.text.strip())

    def _draw_title_header(self, surface, rect) -> None:
        pygame = self.pygame
        inner = draw_panel(surface, pygame, rect, title="Title", accent=INFO)
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
        inner = draw_panel(surface, pygame, rect, title="Menu", accent=GOOD)
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
                "4 New Game Wizard",
                "Choose scenario, difficulty, start, goal, names, slot, and seed.",
                "new_wizard",
                INFO,
            ),
            ("5 Quit", "Leave the frontend shell.", "quit", DANGER),
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
        inner = draw_panel(surface, pygame, rect, title=title, accent=SELECTION)
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
        inner = draw_panel(surface, pygame, rect, title="Save Slot", accent=GOOD)
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
        inner = draw_panel(surface, pygame, rect, title="New Game", accent=INFO)
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
        summary_rect = pygame.Rect(rect.left, rect.top, rect.width, int(rect.height * 0.36))
        events_rect = pygame.Rect(
            rect.left,
            summary_rect.bottom + 12,
            rect.width,
            rect.height - summary_rect.height - 12,
        )
        inner = draw_panel(surface, pygame, summary_rect, title="Status", accent=WARN)
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

        event_inner = draw_panel(surface, pygame, events_rect, title="Feed", accent=INFO)
        event_title = self.fonts.heading.render("Frontend Feed", True, TEXT)
        surface.blit(event_title, (event_inner.left, event_inner.top - 24))
        if not self._events:
            idle_surface = self.fonts.body.render("No menu events yet.", True, MUTED)
            surface.blit(idle_surface, (event_inner.left, event_inner.top))
            return
        top = event_inner.top
        for timed_event in self._events[:4]:
            card_rect = pygame.Rect(event_inner.left, top, event_inner.width, 70)
            self._draw_event_card(surface, card_rect, timed_event)
            top += 80

    def _draw_title_footer(self, surface, rect) -> None:
        pygame = self.pygame
        inner = draw_panel(surface, pygame, rect, title="Guide", accent=INFO)
        if self._mode == "menu":
            message = "Menu: 1 continue, 2 saves, 3 archives, 4 wizard, 5 quit."
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
            )
        if self._mode == "slot_detail":
            summary = self._save_summaries_by_slot.get(self._selected_slot_name or "")
            if summary is not None:
                return (
                    f"Loaded save slot focus: {summary.company_name}",
                    f"Scenario: {summary.scenario_title}",
                    f"Version {summary.saved_with_version} | schema {summary.schema_version}",
                )
        return (
            "Menu mode keeps SQLite save slots and archived runs inside the 2D shell.",
            "Load any live slot to jump straight into the animated dashboard.",
            "Archive review scenes surface final score, exit type, and the saved lesson.",
        )

    def _draw_delete_confirmation_overlay(self, surface) -> None:
        pygame = self.pygame
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(OVERLAY)
        surface.blit(overlay, (0, 0))
        width, height = surface.get_size()
        slot_name = self._confirm_delete_slot_name or "selected slot"
        modal_rect = pygame.Rect(width // 2 - 270, height // 2 - 100, 540, 200)
        inner = draw_panel(surface, pygame, modal_rect, title="Delete Save", accent=DANGER)
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
        overlay.fill(OVERLAY)
        surface.blit(overlay, (0, 0))
        width, height = surface.get_size()
        modal_rect = pygame.Rect(width // 2 - 300, height // 2 - 140, 600, 280)
        inner = draw_panel(
            surface,
            pygame,
            modal_rect,
            title="Text Input",
            accent=tone_color(modal.severity),
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
        pygame.draw.rect(surface, (26, 38, 55), rect, border_radius=14)
        pygame.draw.rect(surface, color, rect, width=1, border_radius=14)
        title_surface = self.fonts.body.render(timed_event.payload.title, True, TEXT)
        surface.blit(title_surface, (rect.left + 12, rect.top + 10))
        draw_wrapped_text(
            surface,
            self.fonts.small,
            timed_event.payload.detail,
            MUTED,
            pygame.Rect(rect.left + 12, rect.top + 30, rect.width - 24, rect.height - 36),
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
    ) -> None:
        super().__init__(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=rng,
            slot_name=slot_name,
            save_callback=save_callback,
            dirty=dirty,
        )
        self._view_model = view_model
        self._accent = accent
        self._primary_title = primary_title
        self._primary_detail = primary_detail
        self._return_scene_factory = return_scene_factory
        self._allow_save = allow_save
        self._click_targets: list[ClickTarget] = []

    def update(self, dt: float) -> None:
        _ = dt

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
        inner = draw_panel(surface, pygame, rect, title="Review", accent=self._accent)
        title_surface = self.fonts.title.render(self._view_model.title, True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 28))
        headline_surface = self.fonts.body.render(self._view_model.headline, True, TEXT)
        surface.blit(headline_surface, (inner.left, inner.top))
        summary_surface = self.fonts.small.render(self._view_model.summary_line, True, MUTED)
        surface.blit(summary_surface, (inner.left, inner.top + 26))

    def _draw_review_findings(self, surface, rect) -> None:
        pygame = self.pygame
        inner = draw_panel(surface, pygame, rect, title="Findings", accent=self._accent)
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
            pygame.draw.rect(surface, (26, 38, 55), card_rect, border_radius=16)
            pygame.draw.rect(surface, accent, card_rect, width=1, border_radius=16)
            title_surface = self.fonts.body.render(
                f"{finding.rank_label} {finding.area} | {finding.command}",
                True,
                TEXT,
            )
            surface.blit(title_surface, (card_rect.left + 12, card_rect.top + 10))
            draw_wrapped_text(
                surface,
                self.fonts.small,
                finding.summary,
                MUTED,
                pygame.Rect(card_rect.left + 12, card_rect.top + 32, card_rect.width - 24, 28),
                line_height=15,
                max_lines=2,
            )
            draw_wrapped_text(
                surface,
                self.fonts.small,
                finding.lesson,
                tone_color(finding.severity),
                pygame.Rect(card_rect.left + 12, card_rect.top + 62, card_rect.width - 24, 20),
                line_height=15,
                max_lines=1,
            )
            top += 110

    def _draw_review_sidebar(self, surface, rect) -> None:
        pygame = self.pygame
        inner = draw_panel(surface, pygame, rect, title="Summary", accent=INFO)
        title_surface = self.fonts.heading.render("Next Focus", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 24))
        focus_surface = self.fonts.body.render(self._view_model.next_focus, True, INFO)
        surface.blit(focus_surface, (inner.left, inner.top))
        badges_title = self.fonts.small.render("Badges", True, MUTED)
        surface.blit(badges_title, (inner.left, inner.top + 30))
        top = inner.top + 52
        for badge in self._view_model.badges[:6]:
            chip_rect = pygame.Rect(inner.left, top, inner.width, 28)
            pygame.draw.rect(surface, (24, 35, 50), chip_rect, border_radius=12)
            pygame.draw.rect(surface, BORDER, chip_rect, width=1, border_radius=12)
            badge_surface = self.fonts.small.render(badge.replace("_", " "), True, TEXT)
            surface.blit(badge_surface, (chip_rect.left + 10, chip_rect.top + 7))
            top += 36

    def _draw_review_footer(self, surface, rect) -> None:
        pygame = self.pygame
        inner = draw_panel(surface, pygame, rect, title="Actions", accent=self._accent)
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
        seed_events: tuple[FrontendEvent, ...] = (),
        dirty: bool = False,
        show_ready_event: bool = True,
    ) -> None:
        super().__init__(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=rng,
            slot_name=slot_name,
            save_callback=save_callback,
            dirty=dirty,
        )
        self._events: list[TimedFrontendEvent] = []
        self._click_targets: list[ClickTarget] = []
        self._context_picker: ContextPicker | None = None
        self._text_input: TextInputModalState | None = None
        self._deep_panel_key: str | None = None
        self._inspector_panel_key: str | None = None
        self._product_index = 0
        self._tweens = TweenBank(speed=9.0)
        self._set_selected_product(selected_product_id)
        self._view_model = build_game_view_model(
            self.state,
            selected_product_id=self.selected_product.id.hex,
        )
        self._sync_tweens()
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

    def update(self, dt: float) -> None:
        """Advance animations and expire transient event cards."""

        self._tweens.update(dt)
        self._events = [
            TimedFrontendEvent(payload=event.payload, time_left=event.time_left - dt)
            for event in self._events
            if event.time_left - dt > 0
        ]

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

        if event.key == self.pygame.K_ESCAPE:
            if self._text_input is not None:
                self._text_input = None
                return
            if self._context_picker is not None:
                self._context_picker = None
                return
            if self._inspector_panel_key is not None:
                self._inspector_panel_key = None
                return
            if self._deep_panel_key is not None:
                self._deep_panel_key = None
                return
            self.should_exit = True
            self.exit_reason = "quit"
            return

        if self._text_input is not None:
            self._handle_text_input_key(event)
            return

        if self._context_picker is not None:
            self._handle_picker_key(event)
            return

        if self._inspector_panel_key is not None:
            if event.key == self.pygame.K_s:
                self._save_current_run()
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
            self._deep_panel_key = "team"
            return
        if event.key == self.pygame.K_2:
            self._deep_panel_key = "finance"
            return
        if event.key == self.pygame.K_3:
            self._deep_panel_key = "customers"
            return
        if event.key == self.pygame.K_4:
            self._deep_panel_key = "partnerships"
            return
        if event.key == self.pygame.K_5:
            self._deep_panel_key = "board"
            return
        if event.key == self.pygame.K_6:
            self._deep_panel_key = "pipeline"
            return
        if event.key == self.pygame.K_7:
            self._deep_panel_key = "report"
            return
        if event.key == self.pygame.K_n:
            self._open_create_product_modal()
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
        footer_height = 332
        footer_rect = pygame.Rect(
            margin,
            height - footer_height - margin,
            width - margin * 2,
            footer_height,
        )
        content_top = header_rect.bottom + gap
        content_height = footer_rect.top - gap - content_top
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
        if self.state.company.game_over or self.state.victory_achieved:
            self._draw_outcome_overlay(surface)

    def push_event(self, payload: FrontendEvent) -> None:
        """Add one transient UI event card."""

        self._events.insert(0, TimedFrontendEvent(payload=payload, time_left=payload.ttl))
        self._events = self._events[:6]

    def push_events(self, payloads: tuple[FrontendEvent, ...]) -> None:
        """Add multiple transient event cards."""

        for payload in reversed(payloads):
            self.push_event(payload)

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
            self._deep_panel_key = target.payload
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
            self._context_picker = None
            return
        if target.kind == "panel_action":
            reason = self._command_disabled_reason(target.payload)
            if reason is not None:
                self._push_action_blocked_event(target.payload, reason)
                return
            self._run_command(target.payload)
            return
        if target.kind == "close_panel":
            self._deep_panel_key = None
            return
        if target.kind == "close_inspector":
            self._inspector_panel_key = None
            return
        if target.kind == "submit_text":
            self._submit_text_modal()
            return
        if target.kind == "cancel_text":
            self._text_input = None
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
        self._context_picker = None
        self._apply_action_request(request)

    def _resolve_pending_event(self, option_id: str) -> str:
        from nexus_tech.simulation.events import resolve_pending_event

        outcome = resolve_pending_event(self.state, option_id)
        self.state = outcome.state
        return outcome.message

    def _open_create_product_modal(self) -> None:
        default_name = f"New Venture {len(self.state.products) + 1}"
        self._text_input = TextInputModalState(
            title="Create Product",
            description="Type the new product name and press Enter to create it.",
            severity="info",
            submit_title="Enter Create",
            submit_detail="Launch the new product into the portfolio.",
            text=default_name,
            placeholder="Product name",
            on_submit=self._submit_create_product_name,
        )

    def _submit_text_modal(self) -> None:
        modal = self._text_input
        if modal is None:
            return
        self._text_input = None
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

    def _run_command(self, command: str) -> None:
        if command == TurnAction.END_TURN.value:
            self._attempt_end_turn()
            return
        inspector_key = self._inspector_key_for_command(command)
        if inspector_key is not None:
            self._inspector_panel_key = inspector_key
            return
        reason = self._command_disabled_reason(command)
        if reason is not None:
            self._push_action_blocked_event(command, reason)
            return
        if command == TurnAction.CREATE_PRODUCT.value:
            self._open_create_product_modal()
            return
        request = build_command_request(
            self.state,
            command=command,
            selected_product_id=self.selected_product.id.hex,
        )
        if isinstance(request, ActionRequest):
            self._apply_action_request(request)
            return
        if isinstance(request, ContextPicker):
            self._context_picker = request
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
            self._context_picker = ContextPicker(
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
            return

        self._resolve_end_turn()

    def _resolve_end_turn(self) -> None:
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
        meta_surface = self.fonts.body.render(meta_text, True, MUTED)
        surface.blit(meta_surface, (inner.left, inner.top))
        note_surface = self.fonts.small.render(self._view_model.header_note, True, TEXT)
        surface.blit(note_surface, (inner.left, inner.top + 22))
        profile_surface = self.fonts.small.render(
            self._view_model.difficulty_summary,
            True,
            MUTED,
        )
        surface.blit(profile_surface, (inner.left, inner.top + 42))
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

        inner = draw_panel(surface, pygame, stats_rect, title="Stats", accent=GOOD)
        header_surface = self.fonts.heading.render("Company Stats", True, TEXT)
        surface.blit(header_surface, (inner.left, inner.top - 24))
        gauge_height = 44
        for index, gauge in enumerate(self._view_model.stats):
            top = inner.top + index * gauge_height
            title_surface = self.fonts.small.render(gauge.title.upper(), True, MUTED)
            value_surface = self.fonts.mono.render(gauge.value_text, True, TEXT)
            surface.blit(title_surface, (inner.left, top))
            surface.blit(value_surface, (inner.right - value_surface.get_width(), top))
            bar_rect = pygame.Rect(inner.left, top + 18, inner.width, 14)
            draw_progress_bar(
                surface,
                pygame,
                bar_rect,
                ratio=self._tweens.get(gauge.key, gauge.ratio),
                color=tone_color(gauge.tone),
            )

        preview_inner = draw_panel(surface, pygame, preview_rect, title="Preview", accent=WARN)
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
        inner = draw_panel(surface, pygame, rect, title="Products", accent=SELECTION)
        title_surface = self.fonts.heading.render("Product Strip", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 24))
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

        coach_inner = draw_panel(surface, pygame, coach_rect, title="Coach", accent=INFO)
        title_surface = self.fonts.heading.render("Turn Coach / Control Tower", True, TEXT)
        surface.blit(title_surface, (coach_inner.left, coach_inner.top - 24))
        top = coach_inner.top
        for line in self._view_model.coach_lines:
            card_rect = pygame.Rect(coach_inner.left, top, coach_inner.width, 66)
            draw_button(
                surface,
                pygame,
                rect=card_rect,
                title=line.command,
                detail=line.source,
                accent=INFO,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
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

        event_inner = draw_panel(surface, pygame, event_rect, title="Event Log", accent=GOOD)
        event_title = self.fonts.heading.render("Animated Event Queue", True, TEXT)
        surface.blit(event_title, (event_inner.left, event_inner.top - 24))
        if not self._events:
            idle_surface = self.fonts.body.render("No transient events yet.", True, MUTED)
            surface.blit(idle_surface, (event_inner.left, event_inner.top))
            return
        event_top = event_inner.top
        for timed_event in self._events[:4]:
            card_rect = pygame.Rect(event_inner.left, event_top, event_inner.width, 66)
            self._draw_event_card(surface, card_rect, timed_event)
            event_top += 76

    def _draw_footer(self, surface, rect) -> None:
        pygame = self.pygame
        inner = draw_panel(surface, pygame, rect, title="Actions", accent=INFO)
        title_surface = self.fonts.heading.render("Action Bar", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 24))
        button_cols = 6 if inner.width < 1120 else 7
        button_gap = 10
        button_width = int((inner.width - button_gap * (button_cols - 1)) / button_cols)
        button_height = 62
        top = inner.top
        left = inner.left
        for index, button in enumerate(_ACTION_BUTTONS):
            if index and index % button_cols == 0:
                top += button_height + 10
                left = inner.left
            button_rect = pygame.Rect(left, top, button_width, button_height)
            enabled = self._button_is_enabled(button)
            draw_button(
                surface,
                pygame,
                rect=button_rect,
                title=f"{button.key_hint} {button.title}",
                detail=self._button_detail(
                    button.payload if button.kind in {"command", "text_command"} else None,
                    button.detail,
                    enabled=enabled,
                ),
                accent=button.accent,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
                enabled=enabled,
            )
            self._click_targets.append(ClickTarget(button.kind, button.payload, button_rect))
            left += button_width + button_gap
        watch_text = self.fonts.small.render(self._view_model.watch_for, True, MUTED)
        hint_text = self.fonts.small.render(
            "Hotkeys: 1-7 panels | N new product | disabled buttons explain why when clicked.",
            True,
            MUTED,
        )
        surface.blit(watch_text, (inner.left, inner.bottom - 22))
        surface.blit(hint_text, (inner.left, inner.bottom - 4))

    def _button_is_enabled(self, button: ActionButtonSpec) -> bool:
        if button.kind in {"save", "panel"}:
            return True
        if button.kind in {"command", "panel_action", "text_command"}:
            return self._command_disabled_reason(button.payload) is None
        return not self.state.company.game_over

    def _draw_product_card(self, surface, rect, product) -> None:
        pygame = self.pygame
        fill = (33, 48, 68) if product.selected else (24, 35, 50)
        border = SELECTION if product.selected else BORDER
        pygame.draw.rect(surface, fill, rect, border_radius=16)
        pygame.draw.rect(
            surface, border, rect, width=2 if product.selected else 1, border_radius=16
        )
        self._click_targets.append(ClickTarget("select_product", product.id, rect))
        title_surface = self.fonts.heading.render(product.name, True, TEXT)
        subtitle_surface = self.fonts.small.render(
            f"{product.stage} | {product.segment} | users {product.users_text}",
            True,
            MUTED,
        )
        revenue_surface = self.fonts.small.render(product.revenue_text, True, INFO)
        surface.blit(title_surface, (rect.left + 14, rect.top + 12))
        surface.blit(subtitle_surface, (rect.left + 14, rect.top + 36))
        surface.blit(
            revenue_surface,
            (rect.right - revenue_surface.get_width() - 14, rect.top + 14),
        )
        metrics = (
            (
                "Quality",
                self._tweens.get(f"{product.id}:quality", product.quality_ratio),
                GOOD,
            ),
            ("Bugs", self._tweens.get(f"{product.id}:bugs", product.bug_ratio), DANGER),
            ("Fit", self._tweens.get(f"{product.id}:fit", product.fit_ratio), INFO),
            ("Debt", self._tweens.get(f"{product.id}:debt", product.debt_ratio), WARN),
        )
        start_y = rect.top + 68
        for index, (label, ratio, color) in enumerate(metrics):
            label_surface = self.fonts.small.render(label, True, MUTED)
            surface.blit(label_surface, (rect.left + 14, start_y + index * 20))
            bar_rect = pygame.Rect(
                rect.left + 78,
                start_y + 2 + index * 20,
                rect.width - 92,
                12,
            )
            draw_progress_bar(surface, pygame, bar_rect, ratio=ratio, color=color)

    def _draw_event_card(self, surface, rect, timed_event: TimedFrontendEvent) -> None:
        pygame = self.pygame
        color = tone_color(timed_event.payload.severity)
        pygame.draw.rect(surface, (26, 38, 55), rect, border_radius=14)
        pygame.draw.rect(surface, color, rect, width=1, border_radius=14)
        title_surface = self.fonts.body.render(timed_event.payload.title, True, TEXT)
        surface.blit(title_surface, (rect.left + 12, rect.top + 10))
        draw_wrapped_text(
            surface,
            self.fonts.small,
            timed_event.payload.detail,
            MUTED,
            pygame.Rect(
                rect.left + 12,
                rect.top + 30,
                rect.width - 24,
                rect.height - 36,
            ),
            line_height=15,
            max_lines=2,
        )
        ttl_ratio = timed_event.time_left / timed_event.payload.ttl
        draw_progress_bar(
            surface,
            pygame,
            pygame.Rect(rect.left + 12, rect.bottom - 10, rect.width - 24, 5),
            ratio=ttl_ratio,
            color=color,
        )

    def _draw_pending_event_overlay(self, surface) -> None:
        pygame = self.pygame
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(OVERLAY)
        surface.blit(overlay, (0, 0))
        width, height = surface.get_size()
        modal_rect = pygame.Rect(width // 2 - 280, height // 2 - 180, 560, 360)
        inner = draw_panel(surface, pygame, modal_rect, title="Pending Event", accent=WARN)
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
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(OVERLAY)
        surface.blit(overlay, (0, 0))
        width, height = surface.get_size()
        modal_height = min(height - 120, 180 + len(picker.options) * 64)
        modal_rect = pygame.Rect(
            width // 2 - 300,
            height // 2 - modal_height // 2,
            600,
            modal_height,
        )
        inner = draw_panel(
            surface,
            pygame,
            modal_rect,
            title="Action Picker",
            accent=tone_color(picker.severity),
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
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(OVERLAY)
        surface.blit(overlay, (0, 0))
        width, height = surface.get_size()
        modal_rect = pygame.Rect(width // 2 - 300, height // 2 - 140, 600, 280)
        inner = draw_panel(
            surface,
            pygame,
            modal_rect,
            title="Text Input",
            accent=tone_color(modal.severity),
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
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(OVERLAY)
        surface.blit(overlay, (0, 0))
        width, height = surface.get_size()
        modal_rect = pygame.Rect(width // 2 - 470, height // 2 - 280, 940, 560)
        inner = draw_panel(surface, pygame, modal_rect, title=panel.title, accent=INFO)
        title_surface = self.fonts.title.render(panel.title, True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 28))
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
                detail=self._button_detail(action.command, action.detail, enabled=enabled),
                accent=tone_color(action.tone),
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
                enabled=enabled,
            )
            self._click_targets.append(ClickTarget("panel_action", action.command, button_rect))
            left += button_width + button_gap

        close_rect = pygame.Rect(action_rect.left, modal_rect.bottom - 56, 160, 34)
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
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(OVERLAY)
        surface.blit(overlay, (0, 0))
        width, height = surface.get_size()
        modal_rect = pygame.Rect(width // 2 - 520, height // 2 - 300, 1040, 600)
        inner = draw_panel(surface, pygame, modal_rect, title=panel.title, accent=SELECTION)
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

        sections = panel.inspectors
        if not sections:
            sections = ()
        section_top = metric_top + 72
        section_rect = pygame.Rect(
            inner.left,
            section_top,
            inner.width,
            inner.bottom - section_top - 56,
        )
        section_title = self.fonts.heading.render("Detailed Inspectors", True, TEXT)
        surface.blit(section_title, (section_rect.left, section_rect.top - 24))
        if sections:
            cols = 1 if len(sections) == 1 else 2
            rows = max(1, (len(sections) + cols - 1) // cols)
            col_gap = 14
            row_gap = 14
            card_width = int((section_rect.width - col_gap * (cols - 1)) / cols)
            card_height = int((section_rect.height - row_gap * (rows - 1)) / rows)
            for index, section in enumerate(sections):
                row = index // cols
                col = index % cols
                card_rect = pygame.Rect(
                    section_rect.left + col * (card_width + col_gap),
                    section_rect.top + row * (card_height + row_gap),
                    card_width,
                    card_height,
                )
                self._draw_inspector_section(surface, card_rect, section)
        else:
            note_rect = pygame.Rect(section_rect.left, section_rect.top, section_rect.width, 48)
            draw_wrapped_text(
                surface,
                self.fonts.body,
                "No detailed inspector sections are populated for this panel yet.",
                MUTED,
                note_rect,
                line_height=18,
                max_lines=2,
            )

        close_rect = pygame.Rect(inner.left, modal_rect.bottom - 56, 180, 34)
        draw_button(
            surface,
            pygame,
            rect=close_rect,
            title="Esc Back To Panel",
            detail="Return to the action panel.",
            accent=BORDER,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        self._click_targets.append(ClickTarget("close_inspector", "", close_rect))

    def _draw_inspector_section(self, surface, rect, section) -> None:
        pygame = self.pygame
        pygame.draw.rect(surface, (20, 29, 42), rect, border_radius=16)
        pygame.draw.rect(
            surface,
            tone_color(section.tone),
            rect,
            width=1,
            border_radius=16,
        )
        title_surface = self.fonts.heading.render(section.title, True, TEXT)
        surface.blit(title_surface, (rect.left + 12, rect.top + 12))
        top = rect.top + 42
        item_height = max(
            54,
            int((rect.height - 54 - 10 * (len(section.items) - 1)) / max(1, len(section.items))),
        )
        for item in section.items[:3]:
            item_rect = pygame.Rect(rect.left + 12, top, rect.width - 24, item_height)
            pygame.draw.rect(surface, (26, 38, 55), item_rect, border_radius=12)
            pygame.draw.rect(
                surface,
                tone_color(item.tone),
                item_rect,
                width=1,
                border_radius=12,
            )
            item_title = self.fonts.small.render(item.title, True, TEXT)
            surface.blit(item_title, (item_rect.left + 10, item_rect.top + 8))
            line_top = item_rect.top + 26
            for line in item.detail_lines[:2]:
                consumed = draw_wrapped_text(
                    surface,
                    self.fonts.small,
                    line,
                    MUTED,
                    pygame.Rect(item_rect.left + 10, line_top, item_rect.width - 20, 18),
                    line_height=14,
                    max_lines=1,
                )
                line_top += max(14, consumed)
            top += item_height + 10

    def _draw_outcome_overlay(self, surface) -> None:
        pygame = self.pygame
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(OVERLAY)
        surface.blit(overlay, (0, 0))
        width, height = surface.get_size()
        modal_rect = pygame.Rect(width // 2 - 260, height // 2 - 132, 520, 264)
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
        pygame.draw.rect(surface, (24, 35, 50), rect, border_radius=12)
        pygame.draw.rect(surface, BORDER, rect, width=1, border_radius=12)
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

    def _compact_button_detail(self, detail: str) -> str:
        compact = detail.strip().replace("`", "")
        if len(compact) <= 44:
            return compact
        return f"{compact[:41].rstrip()}..."


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
    ) -> None:
        super().__init__(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=rng,
            slot_name=slot_name,
            save_callback=save_callback,
            dirty=dirty,
        )
        self._previous_state = previous_state
        self._resolution = resolution
        self._selected_product_id = selected_product_id
        self._click_targets: list[ClickTarget] = []
        self._events = build_turn_resolution_events(previous_state, resolution)
        self._visible_event_count = 1
        self._elapsed = 0.0
        self._tweens = TweenBank(speed=8.0)
        self._view_model: TurnSummaryViewModel = build_turn_summary_view_model(
            previous_state,
            resolution,
        )
        self._tweens.sync_targets({metric.key: metric.ratio for metric in self._view_model.metrics})

    def update(self, dt: float) -> None:
        self._elapsed += dt
        self._tweens.update(dt)
        reveal_count = min(len(self._events), 1 + int(self._elapsed / 0.45))
        self._visible_event_count = max(self._visible_event_count, reveal_count)

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
        left_width = int((width - margin * 2 - gap) * 0.55)
        right_width = width - margin * 2 - gap - left_width
        left_rect = pygame.Rect(margin, content_top, left_width, content_height)
        right_rect = pygame.Rect(left_rect.right + gap, content_top, right_width, content_height)

        self._draw_summary_header(surface, header_rect)
        self._draw_summary_main(surface, left_rect)
        self._draw_summary_timeline(surface, right_rect)
        self._draw_summary_footer(surface, footer_rect)

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
            )
            return
        self._next_scene = RunScene(
            pygame=self.pygame,
            fonts=self.fonts,
            state=self.state,
            rng=self.rng,
            slot_name=self.slot_name,
            save_callback=self._save_callback,
            selected_product_id=self._selected_product_id,
            seed_events=self._events,
            dirty=self._dirty,
            show_ready_event=False,
        )

    def _draw_summary_header(self, surface, rect) -> None:
        pygame = self.pygame
        inner = draw_panel(surface, pygame, rect, title="Turn Summary", accent=INFO)
        title_surface = self.fonts.title.render(self._view_model.title, True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 28))
        headline_surface = self.fonts.body.render(self._view_model.headline, True, INFO)
        surface.blit(headline_surface, (inner.left, inner.top))
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
        metrics_height = 220
        metrics_rect = pygame.Rect(rect.left, rect.top, rect.width, metrics_height)
        products_rect = pygame.Rect(
            rect.left,
            metrics_rect.bottom + 12,
            rect.width,
            rect.height - metrics_height - 12,
        )
        inner = draw_panel(surface, pygame, metrics_rect, title="Metrics", accent=GOOD)
        title_surface = self.fonts.heading.render("Resolution Delta", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 24))
        cols = 3
        card_gap = 10
        card_width = int((inner.width - card_gap * (cols - 1)) / cols)
        card_height = 74
        top = inner.top
        left = inner.left
        for index, metric in enumerate(self._view_model.metrics):
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
        )
        product_title = self.fonts.heading.render("Product Outcomes", True, TEXT)
        surface.blit(product_title, (product_inner.left, product_inner.top - 24))
        top = product_inner.top
        for product_line in self._view_model.product_lines:
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

    def _draw_summary_timeline(self, surface, rect) -> None:
        pygame = self.pygame
        inner = draw_panel(surface, pygame, rect, title="Timeline", accent=WARN)
        title_surface = self.fonts.heading.render("Turn Resolution Timeline", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 24))
        if not self._events:
            idle_surface = self.fonts.body.render("No timeline events.", True, MUTED)
            surface.blit(idle_surface, (inner.left, inner.top))
            return
        top = inner.top
        for event in self._events[: self._visible_event_count]:
            card_rect = pygame.Rect(inner.left, top, inner.width, 70)
            self._draw_summary_event(surface, card_rect, event)
            top += 80

    def _draw_summary_footer(self, surface, rect) -> None:
        pygame = self.pygame
        inner = draw_panel(surface, pygame, rect, title="Continue", accent=INFO)
        footer_surface = self.fonts.small.render(self._view_model.footer, True, TEXT)
        surface.blit(footer_surface, (inner.left, inner.top - 2))
        continue_rect = pygame.Rect(inner.left, inner.top + 24, 200, 38)
        save_rect = pygame.Rect(inner.left + 216, inner.top + 24, 170, 38)
        close_rect = pygame.Rect(inner.left + 402, inner.top + 24, 170, 38)
        draw_button(
            surface,
            pygame,
            rect=continue_rect,
            title="Space Continue",
            detail="Return to the live run.",
            accent=INFO,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        draw_button(
            surface,
            pygame,
            rect=save_rect,
            title="S Save",
            detail="Persist before leaving this scene.",
            accent=GOOD,
            title_font=self.fonts.small,
            detail_font=self.fonts.small,
        )
        draw_button(
            surface,
            pygame,
            rect=close_rect,
            title="Esc Close",
            detail="Exit the 2D shell now.",
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
        pygame.draw.rect(surface, (26, 38, 55), rect, border_radius=14)
        pygame.draw.rect(surface, color, rect, width=1, border_radius=14)
        label_surface = self.fonts.small.render(metric.label.upper(), True, MUTED)
        value_surface = self.fonts.body.render(metric.value_text, True, TEXT)
        surface.blit(label_surface, (rect.left + 12, rect.top + 10))
        surface.blit(value_surface, (rect.left + 12, rect.top + 28))
        draw_wrapped_text(
            surface,
            self.fonts.small,
            metric.detail,
            MUTED,
            pygame.Rect(rect.left + 90, rect.top + 12, rect.width - 102, 20),
            line_height=14,
            max_lines=2,
        )
        draw_progress_bar(
            surface,
            pygame,
            pygame.Rect(rect.left + 12, rect.top + 52, rect.width - 24, 10),
            ratio=self._tweens.get(metric.key, metric.ratio),
            color=color,
        )

    def _draw_summary_event(self, surface, rect, event: FrontendEvent) -> None:
        pygame = self.pygame
        color = tone_color(event.severity)
        pygame.draw.rect(surface, (26, 38, 55), rect, border_radius=14)
        pygame.draw.rect(surface, color, rect, width=1, border_radius=14)
        title_surface = self.fonts.body.render(event.title, True, TEXT)
        surface.blit(title_surface, (rect.left + 12, rect.top + 10))
        draw_wrapped_text(
            surface,
            self.fonts.small,
            event.detail,
            MUTED,
            pygame.Rect(rect.left + 12, rect.top + 32, rect.width - 24, 26),
            line_height=15,
            max_lines=2,
        )


MainGameScene = RunScene
