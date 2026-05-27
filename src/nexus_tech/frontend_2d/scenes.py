"""Scene objects for the lightweight 2D frontend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from nexus_tech.domain.models import GameState, TurnAction
from nexus_tech.frontend_2d.context import (
    ActionRequest,
    ContextPicker,
    PickerOption,
    build_command_request,
)
from nexus_tech.frontend_2d.event_queue import (
    FrontendEvent,
    build_action_events,
    build_turn_resolution_events,
)
from nexus_tech.frontend_2d.input_map import FrontendIntent
from nexus_tech.frontend_2d.tween import TweenBank
from nexus_tech.frontend_2d.viewmodels import (
    TurnSummaryViewModel,
    build_game_view_model,
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
from nexus_tech.simulation.end_turn_preview import build_end_turn_preview
from nexus_tech.simulation.engine import ActionContext, apply_action, resolve_turn
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


_ACTION_BUTTONS: tuple[ActionButtonSpec, ...] = (
    ActionButtonSpec("C", "Coach", "Run the top mission-board command.", INFO, "coach", ""),
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
            if self._context_picker is not None:
                self._context_picker = None
                return
            self.should_exit = True
            self.exit_reason = "quit"
            return

        if self._context_picker is not None:
            self._handle_picker_key(event)
            return

        if self.state.company.game_over or self.state.victory_achieved:
            if event.key == self.pygame.K_s:
                self._save_current_run()
            return

        if self.state.pending_event is not None:
            self._handle_pending_event_key(event)
            return

        if event.key == self.pygame.K_s:
            self._save_current_run()
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
        footer_height = 176
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
            self._run_command(target.payload)
            return
        if target.kind == "coach":
            self._run_primary_coach_action()
            return
        if target.kind == "save":
            self._save_current_run()
            return
        if target.kind == "picker_option":
            self._apply_picker_index(int(target.payload))
            return
        if target.kind == "close_picker":
            self._context_picker = None
            return
        if target.kind == "pending_option":
            self._resolve_pending_event_choice(int(target.payload))
            return
        if target.kind == "close_outcome":
            self.should_exit = True
            self.exit_reason = "quit"
            return

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
                title="Action Needs Deeper UI",
                detail=(
                    f"`{command}` is valid, but this 2D shell still needs a richer picker for it."
                ),
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

    def _refresh_view_model(self) -> None:
        self._view_model = build_game_view_model(
            self.state,
            selected_product_id=self.selected_product.id.hex,
        )
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
            128,
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
        button_cols = 8
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
            draw_button(
                surface,
                pygame,
                rect=button_rect,
                title=f"{button.key_hint} {button.title}",
                detail=button.detail,
                accent=button.accent,
                title_font=self.fonts.small,
                detail_font=self.fonts.small,
                enabled=not self.state.company.game_over,
            )
            self._click_targets.append(ClickTarget(button.kind, button.payload, button_rect))
            left += button_width + button_gap
        watch_text = self.fonts.small.render(self._view_model.watch_for, True, MUTED)
        surface.blit(watch_text, (inner.left, inner.bottom - 4))

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
        save_rect = pygame.Rect(inner.left, inner.bottom - 46, 160, 36)
        close_rect = pygame.Rect(inner.left + 176, inner.bottom - 46, 160, 36)
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
