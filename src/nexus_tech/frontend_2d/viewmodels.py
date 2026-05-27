"""View-model adapters for the lightweight 2D frontend."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import GameState, PendingEvent, Product
from nexus_tech.domain.money import format_money
from nexus_tech.simulation.difficulty import get_difficulty_profile
from nexus_tech.simulation.end_turn_preview import build_end_turn_preview
from nexus_tech.simulation.reporting import calculate_run_score
from nexus_tech.simulation.risk_forecast import build_risk_forecast
from nexus_tech.simulation.turn_coach import build_turn_coach


@dataclass(frozen=True)
class GaugeViewModel:
    """One compact stat bar in the 2D HUD."""

    key: str
    title: str
    value_text: str
    ratio: float
    tone: str


@dataclass(frozen=True)
class ProductCardViewModel:
    """Renderable product card state."""

    id: str
    name: str
    stage: str
    segment: str
    selected: bool
    users_text: str
    revenue_text: str
    quality_ratio: float
    bug_ratio: float
    fit_ratio: float
    debt_ratio: float


@dataclass(frozen=True)
class CoachLineViewModel:
    """Compact recommendation line."""

    command: str
    source: str
    detail: str


@dataclass(frozen=True)
class PendingEventOptionViewModel:
    """Renderable event option line."""

    key_hint: str
    label: str
    description: str


@dataclass(frozen=True)
class PendingEventViewModel:
    """Renderable pending event overlay."""

    title: str
    description: str
    options: tuple[PendingEventOptionViewModel, ...]


@dataclass(frozen=True)
class GameViewModel:
    """Top-level 2D HUD state."""

    company_name: str
    scenario_title: str
    difficulty_label: str
    difficulty_summary: str
    turn_label: str
    score_label: str
    market_label: str
    roadmap_label: str
    budget_label: str
    action_points_label: str
    watch_for: str
    header_note: str
    stats: tuple[GaugeViewModel, ...]
    products: tuple[ProductCardViewModel, ...]
    coach_lines: tuple[CoachLineViewModel, ...]
    deferred_lines: tuple[str, ...]
    risk_lines: tuple[str, ...]
    preview_warning: str
    preview_reason: str
    preview_outcome: str
    pending_event: PendingEventViewModel | None


def build_game_view_model(
    state: GameState, *, selected_product_id: str | None = None
) -> GameViewModel:
    """Build the renderable 2D dashboard state from the simulation state."""

    difficulty = get_difficulty_profile(state.difficulty_mode)
    coach = build_turn_coach(state)
    forecast = build_risk_forecast(state)
    preview = build_end_turn_preview(state)
    selected_product = _pick_selected_product(state.products, selected_product_id)
    total_users = sum(product.user_count for product in state.products if product.is_active)
    score = calculate_run_score(state)
    active_products = [product for product in state.products if product.is_active]
    product_source = active_products or state.products
    products = tuple(
        _build_product_card(product, selected_product_id=selected_product.id.hex)
        for product in product_source
    )
    stats = (
        GaugeViewModel(
            key="cash",
            title="Cash",
            value_text=format_money(state.company.cash_on_hand),
            ratio=_cash_ratio(state.company.cash_on_hand),
            tone=_cash_tone(state.company.cash_on_hand),
        ),
        GaugeViewModel(
            key="reputation",
            title="Reputation",
            value_text=str(state.company.reputation),
            ratio=_ratio(state.company.reputation),
            tone="success"
            if state.company.reputation >= 60
            else "warning"
            if state.company.reputation >= 45
            else "danger",
        ),
        GaugeViewModel(
            key="users",
            title="Users",
            value_text=str(total_users),
            ratio=_scaled_ratio(total_users, ceiling=240),
            tone="info",
        ),
        GaugeViewModel(
            key="board_pressure",
            title="Board",
            value_text=str(state.finance.board_pressure),
            ratio=_ratio(state.finance.board_pressure),
            tone="danger"
            if state.finance.board_pressure >= 60
            else "warning"
            if state.finance.board_pressure >= 35
            else "success",
        ),
        GaugeViewModel(
            key="runway",
            title="Runway",
            value_text=_runway_label(preview),
            ratio=_runway_ratio(preview),
            tone=_preview_tone(preview.warning_level),
        ),
        GaugeViewModel(
            key="actions",
            title="Actions",
            value_text=str(state.action_points_remaining),
            ratio=min(1.0, state.action_points_remaining / 2),
            tone="info",
        ),
    )
    coach_lines = tuple(
        CoachLineViewModel(
            command=recommendation.command,
            source=recommendation.source,
            detail=recommendation.rationale,
        )
        for recommendation in coach.recommendations[:3]
    )
    deferred_lines = tuple(
        f"{action.command}: {action.reason}" for action in coach.deferred_actions[:2]
    ) or ("No deferred actions are flashing right now.",)
    risk_lines = tuple(
        f"{item.area}: {item.command} ({item.severity})" for item in forecast.items[:3]
    ) or ("No elevated operating risk is flashing right now.",)
    header_note = (
        f"Selected product: {selected_product.name} | Primary coach: {coach.primary_command}"
    )
    return GameViewModel(
        company_name=state.company.name,
        scenario_title=state.scenario_title,
        difficulty_label=state.difficulty_mode.value,
        difficulty_summary=difficulty.summary,
        turn_label=f"Turn {state.company.current_turn}",
        score_label=str(score),
        market_label=state.market_cycle.value,
        roadmap_label=state.roadmap_focus.value,
        budget_label=state.quarter_plan.budget_stance.value,
        action_points_label=str(state.action_points_remaining),
        watch_for=difficulty.watch_for,
        header_note=header_note,
        stats=stats,
        products=products,
        coach_lines=coach_lines,
        deferred_lines=deferred_lines,
        risk_lines=risk_lines,
        preview_warning=preview.warning_level,
        preview_reason=preview.confirmation_reason or preview.note,
        preview_outcome=preview.projected_outcome,
        pending_event=_build_pending_event_view_model(state.pending_event),
    )


def _build_product_card(product: Product, *, selected_product_id: str) -> ProductCardViewModel:
    return ProductCardViewModel(
        id=product.id.hex,
        name=product.name,
        stage=product.lifecycle_stage.value,
        segment=product.target_segment.value,
        selected=product.id.hex == selected_product_id,
        users_text=str(product.user_count),
        revenue_text=format_money(Decimal(product.user_count) * product.revenue_per_user),
        quality_ratio=_ratio(product.quality),
        bug_ratio=_ratio(product.bug_level),
        fit_ratio=_ratio(product.market_fit),
        debt_ratio=_ratio(product.technical_debt),
    )


def _build_pending_event_view_model(
    pending_event: PendingEvent | None,
) -> PendingEventViewModel | None:
    if pending_event is None:
        return None
    return PendingEventViewModel(
        title=pending_event.title,
        description=pending_event.description,
        options=tuple(
            PendingEventOptionViewModel(
                key_hint=str(index + 1),
                label=option.label,
                description=option.description,
            )
            for index, option in enumerate(pending_event.options)
        ),
    )


def _pick_selected_product(products: list[Product], selected_product_id: str | None) -> Product:
    active_products = [product for product in products if product.is_active]
    candidates = active_products or products
    if selected_product_id is not None:
        for product in candidates:
            if product.id.hex == selected_product_id:
                return product
    return candidates[0]


def _ratio(value: int) -> float:
    return max(0.0, min(1.0, value / 100))


def _scaled_ratio(value: int, *, ceiling: int) -> float:
    return max(0.0, min(1.0, value / ceiling))


def _cash_ratio(value: Decimal) -> float:
    return max(0.0, min(1.0, float(value / Decimal("12000.00"))))


def _cash_tone(value: Decimal) -> str:
    if value >= Decimal("5000.00"):
        return "success"
    if value >= Decimal("2000.00"):
        return "warning"
    return "danger"


def _runway_label(preview) -> str:
    runway_metric = next((metric for metric in preview.metrics if metric.label == "Runway"), None)
    if runway_metric is None:
        return "blocked" if preview.blocked else "stable"
    return runway_metric.current


def _runway_ratio(preview) -> float:
    runway_metric = next((metric for metric in preview.metrics if metric.label == "Runway"), None)
    if runway_metric is None:
        return 0.0 if preview.blocked else 1.0
    match = re.search(r"(\d+)", runway_metric.current)
    if match is None:
        return 1.0 if "stable" in runway_metric.current.lower() else 0.0
    return min(1.0, int(match.group(1)) / 8)


def _preview_tone(warning_level: str) -> str:
    if warning_level in {"critical", "blocked"}:
        return "danger"
    if warning_level in {"high", "elevated"}:
        return "warning"
    return "success"
