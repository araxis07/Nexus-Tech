"""Scene objects for the lightweight 2D frontend."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.domain.models import (
    CandidateTrait,
    EmployeeRole,
    GameState,
    PartnerChannel,
    Seniority,
    TurnAction,
)
from nexus_tech.frontend_2d.event_queue import (
    FrontendEvent,
    build_action_events,
    build_turn_resolution_events,
)
from nexus_tech.frontend_2d.input_map import (
    DEFAULT_BINDINGS,
    FrontendIntent,
    pending_event_bindings,
)
from nexus_tech.frontend_2d.tween import TweenBank
from nexus_tech.frontend_2d.viewmodels import build_game_view_model
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
    draw_grid,
    draw_keycap,
    draw_panel,
    draw_progress_bar,
    draw_wrapped_text,
    tone_color,
)
from nexus_tech.simulation.end_turn_preview import build_end_turn_preview
from nexus_tech.simulation.engine import ActionContext, apply_action, resolve_turn
from nexus_tech.simulation.randomness import RandomSource


@dataclass
class TimedFrontendEvent:
    """Mutable event card with time remaining."""

    payload: FrontendEvent
    time_left: float


class MainGameScene:
    """Single-screen 2D dashboard scene."""

    def __init__(
        self,
        *,
        pygame,
        fonts: FontPack,
        state: GameState,
        rng: RandomSource,
        slot_name: str,
        save_callback,
    ) -> None:
        self.pygame = pygame
        self.fonts = fonts
        self.state = state
        self.rng = rng
        self.slot_name = slot_name
        self._save_callback = save_callback
        self._product_index = 0
        self._events: list[TimedFrontendEvent] = []
        self._pending_end_turn_confirmation = False
        self._tweens = TweenBank(speed=9.0)
        self._dirty = False
        self.should_exit = False
        self.exit_reason = "quit"
        self._view_model = build_game_view_model(
            self.state, selected_product_id=self.selected_product.id.hex
        )
        self._sync_tweens()
        self.push_event(
            FrontendEvent(
                title="2D Frontend Ready",
                detail="Space resolves the turn. Tab changes product. Esc closes the window.",
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
        remaining_events: list[TimedFrontendEvent] = []
        for event in self._events:
            event.time_left -= dt
            if event.time_left > 0:
                remaining_events.append(event)
        self._events = remaining_events

    def handle_event(self, event) -> None:
        """Handle one pygame event."""

        if event.type == self.pygame.QUIT:
            self.should_exit = True
            self.exit_reason = "quit"
            return

        if event.type != self.pygame.KEYDOWN:
            return

        if event.key == self.pygame.K_ESCAPE:
            self.should_exit = True
            self.exit_reason = "quit"
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
        self._pending_end_turn_confirmation = False
        self._handle_intent(intent)

    def maybe_save_on_exit(self) -> bool:
        """Persist the run if the scene dirtied the state."""

        if not self._dirty:
            return False
        self._save_current_run(push_feedback=False)
        return True

    def draw(self, surface) -> None:
        """Draw the complete frame."""

        pygame = self.pygame
        draw_grid(surface, pygame)
        width, height = surface.get_size()
        margin = 20
        gap = 16
        header_rect = pygame.Rect(margin, margin, width - margin * 2, 90)
        footer_height = 96
        footer_rect = pygame.Rect(
            margin, height - footer_height - margin, width - margin * 2, footer_height
        )
        content_top = header_rect.bottom + gap
        content_height = footer_rect.top - gap - content_top
        left_width = int((width - margin * 2 - gap * 2) * 0.28)
        center_width = int((width - margin * 2 - gap * 2) * 0.39)
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
        elif self.state.company.game_over or self.state.victory_achieved:
            self._draw_outcome_overlay(surface)

    def push_event(self, payload: FrontendEvent) -> None:
        """Add one transient UI event card."""

        self._events.insert(0, TimedFrontendEvent(payload=payload, time_left=payload.ttl))
        self._events = self._events[:6]

    def push_events(self, payloads: tuple[FrontendEvent, ...]) -> None:
        """Add multiple transient event cards."""

        for payload in reversed(payloads):
            self.push_event(payload)

    def _handle_pending_event_key(self, event) -> None:
        if event.key == self.pygame.K_s:
            self._save_current_run()
            return
        key_map = {
            self.pygame.K_1: 0,
            self.pygame.K_2: 1,
            self.pygame.K_3: 2,
        }
        option_index = key_map.get(event.key)
        if option_index is None:
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
            pygame.K_SPACE: FrontendIntent.END_TURN,
        }
        return mapping.get(key)

    def _handle_intent(self, intent: FrontendIntent) -> None:
        if self.state.company.game_over or self.state.victory_achieved:
            return
        if intent is FrontendIntent.PRIMARY_COACH:
            self._run_primary_coach_action()
            return
        if intent is FrontendIntent.END_TURN:
            self._end_turn()
            return

        action_context = self._build_action_context(intent)
        if action_context is None:
            return
        action, context = action_context
        self._apply_simple_action(action, context)

    def _run_primary_coach_action(self) -> None:
        command = self._view_model.coach_lines[0].command if self._view_model.coach_lines else ""
        command_map = {
            TurnAction.IMPROVE_QUALITY.value: FrontendIntent.IMPROVE_QUALITY,
            TurnAction.ADD_FEATURE.value: FrontendIntent.ADD_FEATURE,
            TurnAction.MARKET_PRODUCT.value: FrontendIntent.MARKET_PRODUCT,
            TurnAction.REDUCE_TECHNICAL_DEBT.value: FrontendIntent.REDUCE_TECHNICAL_DEBT,
            TurnAction.HIRE_EMPLOYEE.value: FrontendIntent.HIRE_EMPLOYEE,
            TurnAction.ASSIGN_EMPLOYEE.value: FrontendIntent.ASSIGN_EMPLOYEE,
            TurnAction.TAKE_LOAN.value: FrontendIntent.TAKE_LOAN,
            TurnAction.RAISE_ANGEL.value: FrontendIntent.RAISE_ANGEL,
            TurnAction.CREATE_PARTNERSHIP.value: FrontendIntent.CREATE_PARTNERSHIP,
            TurnAction.END_TURN.value: FrontendIntent.END_TURN,
        }
        intent = command_map.get(command)
        if intent is None:
            self.push_event(
                FrontendEvent(
                    title="Coach Needs Full CLI Context",
                    detail=(
                        f"`{command}` is valid, but the first 2D shell does not collect its deeper "
                        "context yet."
                    ),
                    severity="warning",
                )
            )
            return
        self._handle_intent(intent)

    def _build_action_context(
        self,
        intent: FrontendIntent,
    ) -> tuple[TurnAction, ActionContext] | None:
        selected_product = self.selected_product

        if intent is FrontendIntent.IMPROVE_QUALITY:
            return TurnAction.IMPROVE_QUALITY, ActionContext(target_product_id=selected_product.id)
        if intent is FrontendIntent.ADD_FEATURE:
            return TurnAction.ADD_FEATURE, ActionContext(target_product_id=selected_product.id)
        if intent is FrontendIntent.MARKET_PRODUCT:
            return TurnAction.MARKET_PRODUCT, ActionContext(target_product_id=selected_product.id)
        if intent is FrontendIntent.REDUCE_TECHNICAL_DEBT:
            return TurnAction.REDUCE_TECHNICAL_DEBT, ActionContext(
                target_product_id=selected_product.id
            )
        if intent is FrontendIntent.HIRE_EMPLOYEE:
            hire_number = len(self.state.employees) + 1
            return (
                TurnAction.HIRE_EMPLOYEE,
                ActionContext(
                    hire_full_name=f"2D Hire {hire_number}",
                    hire_role=EmployeeRole.ENGINEER,
                    hire_seniority=Seniority.MID,
                    hire_specialization="product",
                    hire_trait=CandidateTrait.STEADY_OPERATOR,
                ),
            )
        if intent is FrontendIntent.ASSIGN_EMPLOYEE:
            unassigned_employee = next(
                (
                    employee
                    for employee in self.state.employees
                    if employee.assigned_product_id is None
                ),
                None,
            )
            if unassigned_employee is None:
                self.push_event(
                    FrontendEvent(
                        title="No Idle Employee",
                        detail="Every employee is already assigned to a product.",
                        severity="warning",
                    )
                )
                return None
            return (
                TurnAction.ASSIGN_EMPLOYEE,
                ActionContext(
                    employee_id=unassigned_employee.id,
                    target_product_id=selected_product.id,
                ),
            )
        if intent is FrontendIntent.TAKE_LOAN:
            return TurnAction.TAKE_LOAN, ActionContext()
        if intent is FrontendIntent.RAISE_ANGEL:
            return TurnAction.RAISE_ANGEL, ActionContext()
        if intent is FrontendIntent.CREATE_PARTNERSHIP:
            return (
                TurnAction.CREATE_PARTNERSHIP,
                ActionContext(
                    target_product_id=selected_product.id,
                    partner_channel=PartnerChannel.RESELLER,
                ),
            )
        return None

    def _apply_simple_action(self, action: TurnAction, context: ActionContext) -> None:
        previous_state = self.state.model_copy(deep=True)
        try:
            outcome = apply_action(self.state, action, context=context)
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
                action_label=action.value,
                message=outcome.message,
            )
        )
        self._refresh_view_model()

    def _end_turn(self) -> None:
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

        if preview.requires_confirmation and not self._pending_end_turn_confirmation:
            self._pending_end_turn_confirmation = True
            self.push_event(
                FrontendEvent(
                    title="End Turn Needs Confirmation",
                    detail=preview.confirmation_reason,
                    severity="danger" if preview.warning_level == "critical" else "warning",
                    ttl=6.0,
                )
            )
            return

        self._pending_end_turn_confirmation = False
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
        self.push_events(build_turn_resolution_events(previous_state, resolution))
        self._refresh_view_model()

    def _save_current_run(self, *, push_feedback: bool = True) -> None:
        self._save_callback(self.state, self.rng, self.slot_name)
        self._dirty = False
        if push_feedback:
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
        surface.blit(title_surface, (inner.left, inner.top - 26))
        meta_text = (
            f"{self._view_model.scenario_title} | difficulty {self._view_model.difficulty_label} | "
            f"score {self._view_model.score_label} | market {self._view_model.market_label}"
        )
        meta_surface = self.fonts.body.render(meta_text, True, MUTED)
        surface.blit(meta_surface, (inner.left, inner.top + 4))
        note_surface = self.fonts.small.render(self._view_model.header_note, True, TEXT)
        surface.blit(note_surface, (inner.left, inner.top + 28))
        profile_surface = self.fonts.small.render(
            self._view_model.difficulty_summary,
            True,
            MUTED,
        )
        surface.blit(profile_surface, (inner.left, inner.top + 50))

    def _draw_left_column(self, surface, rect) -> None:
        pygame = self.pygame
        stats_height = int(rect.height * 0.46)
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
        gauge_height = 48
        for index, gauge in enumerate(self._view_model.stats):
            top = inner.top + index * gauge_height
            title_surface = self.fonts.small.render(gauge.title.upper(), True, MUTED)
            value_surface = self.fonts.mono.render(gauge.value_text, True, TEXT)
            surface.blit(title_surface, (inner.left, top))
            surface.blit(value_surface, (inner.right - value_surface.get_width(), top))
            bar_rect = pygame.Rect(inner.left, top + 20, inner.width, 14)
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
                preview_inner.height - 72,
            ),
            line_height=17,
            max_lines=7,
        )

    def _draw_center_column(self, surface, rect) -> None:
        pygame = self.pygame
        inner = draw_panel(surface, pygame, rect, title="Products", accent=SELECTION)
        title_surface = self.fonts.heading.render("Selected Product Strip", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 24))
        available_height = inner.height
        card_height = max(
            120,
            int(
                (available_height - 12 * (len(self._view_model.products) - 1))
                / max(1, len(self._view_model.products))
            ),
        )
        top = inner.top
        for product in self._view_model.products:
            card_rect = pygame.Rect(inner.left, top, inner.width, card_height)
            self._draw_product_card(surface, card_rect, product)
            top += card_height + 12

    def _draw_right_column(self, surface, rect) -> None:
        pygame = self.pygame
        coach_height = int(rect.height * 0.48)
        coach_rect = pygame.Rect(rect.left, rect.top, rect.width, coach_height)
        event_rect = pygame.Rect(
            rect.left,
            coach_rect.bottom + 12,
            rect.width,
            rect.height - coach_height - 12,
        )

        coach_inner = draw_panel(surface, pygame, coach_rect, title="Coach", accent=INFO)
        title_surface = self.fonts.heading.render("Turn Coach / Risk", True, TEXT)
        surface.blit(title_surface, (coach_inner.left, coach_inner.top - 24))
        top = coach_inner.top
        for line in self._view_model.coach_lines:
            command_surface = self.fonts.body.render(line.command, True, TEXT)
            source_surface = self.fonts.small.render(line.source, True, INFO)
            surface.blit(command_surface, (coach_inner.left, top))
            surface.blit(source_surface, (coach_inner.right - source_surface.get_width(), top + 2))
            used_height = draw_wrapped_text(
                surface,
                self.fonts.small,
                line.detail,
                MUTED,
                pygame.Rect(coach_inner.left, top + 22, coach_inner.width, 34),
                line_height=16,
                max_lines=2,
            )
            top += max(54, used_height + 28)

        divider_y = top + 6
        pygame.draw.line(
            surface,
            BORDER,
            (coach_inner.left, divider_y),
            (coach_inner.right, divider_y),
            1,
        )
        deferred_title = self.fonts.small.render("Not Now", True, WARN)
        surface.blit(deferred_title, (coach_inner.left, divider_y + 10))
        deferred_top = divider_y + 32
        for deferred_line in self._view_model.deferred_lines[:2]:
            consumed = draw_wrapped_text(
                surface,
                self.fonts.small,
                deferred_line,
                MUTED,
                pygame.Rect(coach_inner.left, deferred_top, coach_inner.width, 38),
                line_height=16,
                max_lines=2,
            )
            deferred_top += max(24, consumed)
        risk_top = max(deferred_top + 8, coach_inner.bottom - 84)
        risk_title = self.fonts.small.render("Risk Forecast", True, DANGER)
        surface.blit(risk_title, (coach_inner.left, risk_top))
        for index, risk_line in enumerate(self._view_model.risk_lines[:2]):
            draw_wrapped_text(
                surface,
                self.fonts.small,
                risk_line,
                MUTED,
                pygame.Rect(coach_inner.left, risk_top + 18 + index * 24, coach_inner.width, 22),
                line_height=16,
                max_lines=1,
            )

        event_inner = draw_panel(surface, pygame, event_rect, title="Event Log", accent=GOOD)
        event_title = self.fonts.heading.render("Animated Event Queue", True, TEXT)
        surface.blit(event_title, (event_inner.left, event_inner.top - 24))
        if not self._events:
            idle_surface = self.fonts.body.render("No transient events yet.", True, MUTED)
            surface.blit(idle_surface, (event_inner.left, event_inner.top))
            return
        event_top = event_inner.top
        for timed_event in self._events[:4]:
            card_height = 64
            card_rect = pygame.Rect(event_inner.left, event_top, event_inner.width, card_height)
            self._draw_event_card(surface, card_rect, timed_event)
            event_top += card_height + 10

    def _draw_footer(self, surface, rect) -> None:
        pygame = self.pygame
        inner = draw_panel(surface, pygame, rect, title="Controls", accent=INFO)
        title_surface = self.fonts.heading.render("Keyboard Controls", True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 24))
        bindings = (
            pending_event_bindings(len(self.state.pending_event.options))
            if self.state.pending_event is not None
            else DEFAULT_BINDINGS
        )
        chip_width = max(150, int((inner.width - 12 * 4) / 5))
        chip_height = 34
        top = inner.top
        left = inner.left
        for index, binding in enumerate(bindings[:10]):
            if index > 0 and index % 5 == 0:
                top += chip_height + 10
                left = inner.left
            chip_rect = pygame.Rect(left, top, chip_width, chip_height)
            draw_keycap(
                surface,
                pygame,
                self.fonts.small,
                rect=chip_rect,
                key_text=binding.key_hint,
                label=binding.label,
            )
            left += chip_width + 12
        watch_text = self.fonts.small.render(self._view_model.watch_for, True, MUTED)
        surface.blit(watch_text, (inner.left, inner.bottom - 6))

    def _draw_product_card(self, surface, rect, product) -> None:
        pygame = self.pygame
        fill = (33, 48, 68) if product.selected else (24, 35, 50)
        border = SELECTION if product.selected else BORDER
        pygame.draw.rect(surface, fill, rect, border_radius=16)
        pygame.draw.rect(
            surface, border, rect, width=2 if product.selected else 1, border_radius=16
        )
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
        for option in event_model.options:
            option_rect = pygame.Rect(inner.left, top, inner.width, 52)
            pygame.draw.rect(surface, (28, 42, 61), option_rect, border_radius=12)
            pygame.draw.rect(surface, BORDER, option_rect, width=1, border_radius=12)
            key_surface = self.fonts.body.render(option.key_hint, True, WARN)
            label_surface = self.fonts.body.render(option.label, True, TEXT)
            surface.blit(key_surface, (option_rect.left + 12, option_rect.top + 10))
            surface.blit(label_surface, (option_rect.left + 42, option_rect.top + 10))
            draw_wrapped_text(
                surface,
                self.fonts.small,
                option.description,
                MUTED,
                pygame.Rect(
                    option_rect.left + 42,
                    option_rect.top + 28,
                    option_rect.width - 54,
                    18,
                ),
                line_height=14,
                max_lines=1,
            )
            top += 62

    def _draw_outcome_overlay(self, surface) -> None:
        pygame = self.pygame
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(OVERLAY)
        surface.blit(overlay, (0, 0))
        width, height = surface.get_size()
        modal_rect = pygame.Rect(width // 2 - 240, height // 2 - 120, 480, 240)
        accent = GOOD if self.state.victory_achieved else DANGER
        inner = draw_panel(surface, pygame, modal_rect, title="Run Complete", accent=accent)
        title = "Victory Achieved" if self.state.victory_achieved else "Company Shutdown"
        title_surface = self.fonts.title.render(title, True, TEXT)
        surface.blit(title_surface, (inner.left, inner.top - 26))
        detail = (
            self.state.victory_reason
            or self.state.exit_summary
            or "Press Esc to close the frontend."
        )
        draw_wrapped_text(
            surface,
            self.fonts.body,
            detail,
            MUTED,
            pygame.Rect(inner.left, inner.top + 8, inner.width, 92),
            line_height=18,
            max_lines=4,
        )
        footer_surface = self.fonts.small.render(
            "Press S to save or Esc to close.",
            True,
            TEXT,
        )
        surface.blit(footer_surface, (inner.left, inner.bottom - 8))
