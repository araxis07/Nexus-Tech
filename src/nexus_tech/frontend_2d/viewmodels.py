"""View-model adapters for the lightweight 2D frontend."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import GameState, PendingEvent, Product
from nexus_tech.domain.money import format_money
from nexus_tech.persistence.save_coordinator import RunArchiveSummary, SaveSlotSummary
from nexus_tech.simulation.difficulty import get_difficulty_profile
from nexus_tech.simulation.end_turn_preview import build_end_turn_preview
from nexus_tech.simulation.engine import TurnResolution
from nexus_tech.simulation.postmortem import build_run_postmortem
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
class SnapshotChipViewModel:
    """One terse operational snapshot chip for the 2D header."""

    label: str
    value_text: str
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
class DeepDiveMetricViewModel:
    """One metric shown inside a deep-dive operational panel."""

    label: str
    value_text: str
    tone: str


@dataclass(frozen=True)
class DeepDiveActionViewModel:
    """One actionable command surfaced from a deep-dive panel."""

    command: str
    label: str
    detail: str
    tone: str


@dataclass(frozen=True)
class DeepDivePanelViewModel:
    """One operational deep-dive panel."""

    key: str
    title: str
    summary: str
    metrics: tuple[DeepDiveMetricViewModel, ...]
    detail_lines: tuple[str, ...]
    actions: tuple[DeepDiveActionViewModel, ...]


@dataclass(frozen=True)
class TurnMetricViewModel:
    """One metric tile shown in the turn-resolution scene."""

    key: str
    label: str
    value_text: str
    detail: str
    ratio: float
    tone: str


@dataclass(frozen=True)
class TurnProductSummaryViewModel:
    """One compact product outcome line in the turn-resolution scene."""

    name: str
    detail: str
    revenue_text: str
    cost_text: str
    tone: str


@dataclass(frozen=True)
class TurnSummaryViewModel:
    """Top-level turn-resolution state for the animated summary scene."""

    title: str
    headline: str
    narrative: str
    footer: str
    metrics: tuple[TurnMetricViewModel, ...]
    product_lines: tuple[TurnProductSummaryViewModel, ...]


@dataclass(frozen=True)
class ReviewFindingViewModel:
    """One finding surfaced in a review or archive scene."""

    rank_label: str
    area: str
    severity: str
    summary: str
    command: str
    lesson: str


@dataclass(frozen=True)
class RunReviewViewModel:
    """Renderable summary for completed-run or archive review scenes."""

    title: str
    headline: str
    summary_line: str
    next_focus: str
    badges: tuple[str, ...]
    findings: tuple[ReviewFindingViewModel, ...]


@dataclass(frozen=True)
class SaveSlotCardViewModel:
    """One save slot surfaced in the 2D title scene."""

    slot_name: str
    headline: str
    detail_lines: tuple[str, ...]
    tone: str


@dataclass(frozen=True)
class ArchiveCardViewModel:
    """One archive card surfaced in the 2D title scene."""

    archive_key: str
    headline: str
    detail_lines: tuple[str, ...]
    tone: str


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
    snapshot_chips: tuple[SnapshotChipViewModel, ...]
    products: tuple[ProductCardViewModel, ...]
    coach_lines: tuple[CoachLineViewModel, ...]
    deferred_lines: tuple[str, ...]
    risk_lines: tuple[str, ...]
    preview_warning: str
    preview_reason: str
    preview_outcome: str
    pending_event: PendingEventViewModel | None
    deep_panels: tuple[DeepDivePanelViewModel, ...]


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
    snapshot_chips = (
        SnapshotChipViewModel("Team", str(len(state.employees)), "info"),
        SnapshotChipViewModel(
            "Idle",
            str(sum(1 for employee in state.employees if employee.assigned_product_id is None)),
            "warning",
        ),
        SnapshotChipViewModel("Partners", str(len(state.partnerships)), "info"),
        SnapshotChipViewModel(
            "Backlog",
            str(state.support_program.backlog_queue),
            "danger" if state.support_program.backlog_queue >= 8 else "warning",
        ),
        SnapshotChipViewModel(
            "Lane",
            state.support_program.lane_focus.value.replace("_", " "),
            "info",
        ),
        SnapshotChipViewModel(
            "Board Ask",
            state.finance.active_board_ask.value.replace("_", " "),
            "warning",
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
        snapshot_chips=snapshot_chips,
        products=products,
        coach_lines=coach_lines,
        deferred_lines=deferred_lines,
        risk_lines=risk_lines,
        preview_warning=preview.warning_level,
        preview_reason=preview.confirmation_reason or preview.note,
        preview_outcome=preview.projected_outcome,
        pending_event=_build_pending_event_view_model(state.pending_event),
        deep_panels=build_deep_dive_panel_view_models(
            state,
            selected_product_id=selected_product.id.hex,
        ),
    )


def build_turn_summary_view_model(
    previous_state: GameState,
    resolution: TurnResolution,
) -> TurnSummaryViewModel:
    """Build the animated post-resolution summary scene state."""

    total_user_delta = sum(item.net_user_delta for item in resolution.product_summaries)
    board_delta = resolution.state.finance.board_pressure - previous_state.finance.board_pressure
    footer = "Press Space or click Continue to return to the run."
    if resolution.pending_event is not None:
        footer = f"Pending event unlocked: {resolution.pending_event.title}."
    elif resolution.state.victory_achieved:
        footer = resolution.state.victory_reason or "Victory achieved."
    elif resolution.state.company.game_over:
        footer = resolution.state.exit_summary or "The company shut down."
    metrics = (
        TurnMetricViewModel(
            key="net_cash",
            label="Net Cash",
            value_text=format_money(resolution.net_cash_flow),
            detail=f"Revenue {format_money(resolution.total_revenue)}",
            ratio=_money_ratio(abs(resolution.net_cash_flow), ceiling=Decimal("3200.00")),
            tone="success" if resolution.net_cash_flow >= 0 else "danger",
        ),
        TurnMetricViewModel(
            key="cost",
            label="Operating Cost",
            value_text=format_money(resolution.total_operating_cost),
            detail=f"Salaries {format_money(resolution.total_salary_cost)}",
            ratio=_money_ratio(resolution.total_operating_cost, ceiling=Decimal("3600.00")),
            tone="warning",
        ),
        TurnMetricViewModel(
            key="users",
            label="User Delta",
            value_text=_signed_int(total_user_delta),
            detail=f"Market cycle {resolution.market_cycle.value}",
            ratio=_scaled_ratio(abs(total_user_delta), ceiling=40),
            tone="success" if total_user_delta >= 0 else "warning",
        ),
        TurnMetricViewModel(
            key="reputation",
            label="Reputation",
            value_text=_signed_int(resolution.reputation_delta),
            detail=f"Score {resolution.run_score.total_score}",
            ratio=_scaled_ratio(abs(resolution.reputation_delta), ceiling=10),
            tone="success" if resolution.reputation_delta >= 0 else "warning",
        ),
        TurnMetricViewModel(
            key="board",
            label="Board Delta",
            value_text=_signed_int(board_delta),
            detail=f"Pressure now {resolution.state.finance.board_pressure}",
            ratio=_scaled_ratio(abs(board_delta), ceiling=12),
            tone="danger" if board_delta > 0 else "success",
        ),
        TurnMetricViewModel(
            key="actions_reset",
            label="Next Turn AP",
            value_text=str(resolution.state.action_points_remaining),
            detail=resolution.commercial_pressure_summary,
            ratio=min(1.0, resolution.state.action_points_remaining / 2),
            tone="info",
        ),
    )
    product_lines = tuple(
        TurnProductSummaryViewModel(
            name=summary.product_name,
            detail=(
                f"{_signed_int(summary.net_user_delta)} users | "
                f"{_signed_int(summary.quality_delta)} quality | "
                f"{_signed_int(summary.bug_delta)} bugs"
            ),
            revenue_text=format_money(summary.revenue),
            cost_text=format_money(summary.operating_cost),
            tone="success" if summary.net_user_delta >= 0 else "warning",
        )
        for summary in resolution.product_summaries[:4]
    )
    return TurnSummaryViewModel(
        title=f"Turn {resolution.resolved_turn} Resolved",
        headline=resolution.scale_pressure_summary,
        narrative=resolution.narrative,
        footer=footer,
        metrics=metrics,
        product_lines=product_lines,
    )


def build_deep_dive_panel_view_models(
    state: GameState,
    *,
    selected_product_id: str | None = None,
) -> tuple[DeepDivePanelViewModel, ...]:
    """Build the operational side panels used by the 2D frontend."""
    selected_product = _pick_selected_product(state.products, selected_product_id)
    avg_morale = (
        sum(employee.morale for employee in state.employees) // len(state.employees)
        if state.employees
        else 0
    )
    avg_energy = (
        sum(employee.energy for employee in state.employees) // len(state.employees)
        if state.employees
        else 0
    )
    active_accounts = [
        account for account in state.customer_accounts if account.status.value != "churned"
    ]
    hotspot_account = max(
        active_accounts,
        key=lambda account: (
            account.churn_risk + account.sla_breach_risk + account.invoice_risk,
            account.contract_value,
        ),
        default=None,
    )
    top_partner = max(
        state.partnerships,
        key=lambda partnership: (
            partnership.risk,
            partnership.conflict_pressure,
            partnership.sourced_revenue,
        ),
        default=None,
    )
    top_deal = max(
        state.sales_deals,
        key=lambda deal: (deal.probability, deal.value),
        default=None,
    )
    top_release = next(
        (release for release in state.product_releases if release.status.value == "planned"),
        None,
    )
    top_project = next(
        (project for project in state.roadmap_projects if project.status.value == "active"),
        None,
    )
    top_candidate = next(
        (
            candidate
            for candidate in state.hiring_candidates
            if candidate.stage.value in {"sourced", "screened", "interviewed"}
        ),
        None,
    )
    latest_turn = state.turn_history[-1] if state.turn_history else None
    run_score = calculate_run_score(state)
    customer_summary = (
        f"{selected_product.name} is currently aimed at "
        f"{selected_product.target_segment.value.replace('_', ' ')} buyers."
        if selected_product is not None
        else "No active product is selected."
    )
    partner_summary = (
        f"Hotspot partner: {top_partner.name}."
        if top_partner is not None
        else "No live partner channel exists yet."
    )
    team_panel = DeepDivePanelViewModel(
        key="team",
        title="Team Control Room",
        summary="Inspect staffing load, morale, and where idle capacity should go next.",
        metrics=(
            DeepDiveMetricViewModel("Headcount", str(len(state.employees)), "info"),
            DeepDiveMetricViewModel(
                "Idle",
                str(sum(1 for employee in state.employees if employee.assigned_product_id is None)),
                "warning",
            ),
            DeepDiveMetricViewModel("Morale", str(avg_morale), _attribute_tone(avg_morale)),
            DeepDiveMetricViewModel("Energy", str(avg_energy), _attribute_tone(avg_energy)),
        ),
        detail_lines=tuple(
            (
                f"{employee.full_name} | {employee.role.value.replace('_', ' ')} | "
                f"morale {employee.morale} | energy {employee.energy}"
            )
            for employee in state.employees[:4]
        )
        or ("No employees yet. Hiring is still the next staffing move.",),
        actions=(
            DeepDiveActionViewModel("hire_employee", "Hire", "Add the next team role.", "info"),
            DeepDiveActionViewModel(
                "assign_employee",
                "Assign",
                "Point idle capacity at the selected product.",
                "success",
            ),
            DeepDiveActionViewModel(
                "train_employee",
                "Train",
                "Lift productivity on one teammate.",
                "info",
            ),
            DeepDiveActionViewModel(
                "reorg_team",
                "Reorg",
                "Rebalance load if morale or focus drifts.",
                "warning",
            ),
            DeepDiveActionViewModel(
                "source_candidates",
                "Source",
                "Open the hiring funnel for the next seat.",
                "info",
            ),
            DeepDiveActionViewModel(
                "screen_candidate",
                "Screen",
                "Move the best sourced candidate forward.",
                "info",
            ),
            DeepDiveActionViewModel(
                "interview_candidate",
                "Interview",
                "Deepen evaluation for screened candidates.",
                "warning",
            ),
            DeepDiveActionViewModel(
                "make_hiring_offer",
                "Offer",
                "Close on the most advanced candidate.",
                "success",
            ),
        ),
    )
    finance_panel = DeepDivePanelViewModel(
        key="finance",
        title="Finance Command",
        summary="Monitor runway, debt posture, and board pressure before liquidity tightens.",
        metrics=(
            DeepDiveMetricViewModel(
                "Cash",
                format_money(state.company.cash_on_hand),
                _cash_tone(state.company.cash_on_hand),
            ),
            DeepDiveMetricViewModel(
                "Debt",
                format_money(state.finance.debt_principal),
                "warning" if state.finance.debt_principal > Decimal("0.00") else "success",
            ),
            DeepDiveMetricViewModel(
                "Board",
                str(state.finance.board_pressure),
                _attribute_tone(100 - state.finance.board_pressure),
            ),
            DeepDiveMetricViewModel(
                "Confidence",
                str(state.finance.board_confidence),
                _attribute_tone(state.finance.board_confidence),
            ),
        ),
        detail_lines=(
            f"Directive: {state.finance.board_directive.value.replace('_', ' ')}",
            f"Board ask: {state.finance.active_board_ask.value.replace('_', ' ')}",
            (
                "Board resolution is due now."
                if state.finance.board_resolution_due
                else "No active board resolution deadline is flashing."
            ),
            f"Budget preset: {state.functional_budget.preset.value.replace('_', ' ')}",
        ),
        actions=(
            DeepDiveActionViewModel(
                "set_capital_plan",
                "Capital Plan",
                "Choose the multi-turn funding posture.",
                "warning",
            ),
            DeepDiveActionViewModel(
                "set_functional_budget",
                "Function Budget",
                "Rebalance engineering, GTM, and CS spend.",
                "warning",
            ),
            DeepDiveActionViewModel(
                "take_loan",
                "Loan",
                "Extend liquidity when runway is shrinking.",
                "warning",
            ),
            DeepDiveActionViewModel(
                "raise_angel",
                "Angel",
                "Bring outside capital in if traction supports it.",
                "info",
            ),
            DeepDiveActionViewModel(
                "review_board",
                "Board Review",
                "Open governance status without leaving 2D.",
                "info",
            ),
        ),
    )
    customers_panel = DeepDivePanelViewModel(
        key="customers",
        title="Customer / Product Desk",
        summary="Steer pricing, packaging, segment, and support around the live product mix.",
        metrics=(
            DeepDiveMetricViewModel("Accounts", str(len(active_accounts)), "info"),
            DeepDiveMetricViewModel(
                "Backlog",
                str(state.support_program.backlog_queue),
                "danger" if state.support_program.backlog_queue >= 8 else "warning",
            ),
            DeepDiveMetricViewModel(
                "Escalations",
                str(state.support_program.escalation_queue),
                "danger" if state.support_program.escalation_queue >= 3 else "warning",
            ),
            DeepDiveMetricViewModel(
                "Selected",
                selected_product.name if selected_product is not None else "n/a",
                "info",
            ),
        ),
        detail_lines=(
            customer_summary,
            (
                f"Pricing {selected_product.pricing_tier.value} | "
                f"packaging {selected_product.packaging_strategy.value.replace('_', ' ')}"
                if selected_product is not None
                else "No product selected."
            ),
            (
                f"Hotspot account: {hotspot_account.name} | churn {hotspot_account.churn_risk} | "
                f"tickets {hotspot_account.open_tickets}"
                if hotspot_account is not None
                else "No active key account is flashing right now."
            ),
            f"Support lane focus: {state.support_program.lane_focus.value.replace('_', ' ')}",
        ),
        actions=(
            DeepDiveActionViewModel(
                "create_product",
                "New Product",
                "Spin up a named product through the text input modal.",
                "info",
            ),
            DeepDiveActionViewModel(
                "adjust_pricing",
                "Pricing",
                "Shift monetization on the selected product.",
                "warning",
            ),
            DeepDiveActionViewModel(
                "set_packaging_strategy",
                "Packaging",
                "Repackage the selected product.",
                "info",
            ),
            DeepDiveActionViewModel(
                "set_target_segment",
                "Segment",
                "Reposition the selected product.",
                "info",
            ),
            DeepDiveActionViewModel(
                "review_customers",
                "Customer Review",
                "Refresh the customer/account perspective.",
                "info",
            ),
        ),
    )
    partnerships_panel = DeepDivePanelViewModel(
        key="partnerships",
        title="Channel / Partnerships Desk",
        summary="Track channel quality, partner strain, and recovery moves on the live portfolio.",
        metrics=(
            DeepDiveMetricViewModel("Partners", str(len(state.partnerships)), "info"),
            DeepDiveMetricViewModel(
                "Active",
                str(
                    sum(
                        1
                        for partnership in state.partnerships
                        if partnership.status.value == "active"
                    )
                ),
                "success",
            ),
            DeepDiveMetricViewModel(
                "Recovery",
                str(
                    sum(
                        1
                        for partnership in state.partnerships
                        if partnership.status.value in {"strained", "recovery", "paused"}
                    )
                ),
                "warning",
            ),
            DeepDiveMetricViewModel(
                "Hotspot Risk",
                str(top_partner.risk if top_partner is not None else 0),
                _attribute_tone(100 - (top_partner.risk if top_partner is not None else 0)),
            ),
        ),
        detail_lines=tuple(
            (
                f"{partnership.name} | {partnership.channel.value} | {partnership.status.value} | "
                f"risk {partnership.risk}"
            )
            for partnership in state.partnerships[:4]
        )
        or (partner_summary,),
        actions=(
            DeepDiveActionViewModel(
                "create_partnership",
                "New Channel",
                "Open a new reseller, integration, or marketplace lane.",
                "info",
            ),
            DeepDiveActionViewModel(
                "renegotiate_partnership",
                "Renegotiate",
                "Repair one strained relationship.",
                "warning",
            ),
            DeepDiveActionViewModel(
                "run_partner_recovery_sprint",
                "Recovery Sprint",
                "Stabilize the hottest partner lane.",
                "warning",
            ),
            DeepDiveActionViewModel(
                "rebalance_channel_mix",
                "Rebalance Mix",
                "Reduce dependency on one noisy partner lane.",
                "info",
            ),
            DeepDiveActionViewModel(
                "review_partnerships",
                "Portfolio Review",
                "Refresh partner-state reporting.",
                "info",
            ),
        ),
    )
    board_panel = DeepDivePanelViewModel(
        key="board",
        title="Board / Governance Desk",
        summary=(
            "Track board trust, governance heat, and recovery posture before the review loop bites."
        ),
        metrics=(
            DeepDiveMetricViewModel(
                "Pressure",
                str(state.finance.board_pressure),
                _attribute_tone(100 - state.finance.board_pressure),
            ),
            DeepDiveMetricViewModel(
                "Confidence",
                str(state.finance.board_confidence),
                _attribute_tone(state.finance.board_confidence),
            ),
            DeepDiveMetricViewModel(
                "Governance",
                str(state.finance.governance_risk),
                _attribute_tone(100 - state.finance.governance_risk),
            ),
            DeepDiveMetricViewModel(
                "Warnings",
                str(state.finance.board_warning_level),
                "danger" if state.finance.board_warning_level >= 2 else "warning",
            ),
        ),
        detail_lines=(
            f"Directive: {state.finance.board_directive.value.replace('_', ' ')}",
            f"Active ask: {state.finance.active_board_ask.value.replace('_', ' ')}",
            (
                f"Recovery focus: {state.finance.board_recovery_focus.value.replace('_', ' ')} "
                f"for {state.finance.board_recovery_turns_remaining} turns."
            ),
            (
                "Board response is due right now."
                if state.finance.board_resolution_due
                else "No board response deadline is active this turn."
            ),
        ),
        actions=(
            DeepDiveActionViewModel(
                "review_board",
                "Review Board",
                "Refresh the governance panel from inside 2D.",
                "info",
            ),
            DeepDiveActionViewModel(
                "execute_board_response",
                "Board Response",
                "Answer the active board ask.",
                "warning",
            ),
            DeepDiveActionViewModel(
                "start_board_recovery_plan",
                "Recovery Plan",
                "Reset governance control before pressure spikes.",
                "warning",
            ),
            DeepDiveActionViewModel(
                "execute_restructure_plan",
                "Restructure",
                "Use only when the governance loop is already breaking.",
                "danger",
            ),
        ),
    )
    pipeline_panel = DeepDivePanelViewModel(
        key="pipeline",
        title="Pipeline / Delivery Desk",
        summary="Drive delivery, deals, roadmap projects, and the hiring funnel from one panel.",
        metrics=(
            DeepDiveMetricViewModel("Deals", str(len(state.sales_deals)), "info"),
            DeepDiveMetricViewModel("Releases", str(len(state.product_releases)), "info"),
            DeepDiveMetricViewModel("Projects", str(len(state.roadmap_projects)), "info"),
            DeepDiveMetricViewModel("Candidates", str(len(state.hiring_candidates)), "info"),
        ),
        detail_lines=(
            (
                f"Top deal: {top_deal.name} | {top_deal.stage.value} | "
                f"prob {top_deal.probability} | {format_money(top_deal.value)}"
                if top_deal is not None
                else "No active sales deal exists yet."
            ),
            (
                f"Next release: {top_release.release_type.value} | progress "
                f"{top_release.progress}/{top_release.required_progress}"
                if top_release is not None
                else "No planned release is waiting for delivery work."
            ),
            (
                f"Roadmap: {top_project.project_type.value} | progress "
                f"{top_project.progress}/{top_project.required_progress}"
                if top_project is not None
                else "No active roadmap project is open."
            ),
            (
                f"Candidate: {top_candidate.full_name} | {top_candidate.stage.value} | "
                f"{top_candidate.role.value.replace('_', ' ')}"
                if top_candidate is not None
                else "No live hiring candidate is in the funnel."
            ),
        ),
        actions=(
            DeepDiveActionViewModel(
                "review_pipeline",
                "Pipeline Review",
                "Refresh the deal and delivery status lens.",
                "info",
            ),
            DeepDiveActionViewModel(
                "create_sales_deal",
                "New Deal",
                "Open a fresh sales opportunity for the selected product.",
                "info",
            ),
            DeepDiveActionViewModel(
                "advance_sales_deal",
                "Advance Deal",
                "Push the most relevant deal forward.",
                "warning",
            ),
            DeepDiveActionViewModel(
                "plan_release",
                "Plan Release",
                "Schedule the next selected-product release.",
                "info",
            ),
            DeepDiveActionViewModel(
                "work_release",
                "Work Release",
                "Spend execution effort on the hottest release.",
                "success",
            ),
            DeepDiveActionViewModel(
                "start_roadmap_project",
                "Start Project",
                "Launch a strategic roadmap project.",
                "info",
            ),
            DeepDiveActionViewModel(
                "work_roadmap_project",
                "Work Project",
                "Push the active roadmap project forward.",
                "warning",
            ),
        ),
    )
    report_panel = DeepDivePanelViewModel(
        key="report",
        title="Report / Run Summary Desk",
        summary="Read the current run at a higher level before you commit the next turn.",
        metrics=(
            DeepDiveMetricViewModel("Score", str(run_score.total_score), "info"),
            DeepDiveMetricViewModel(
                "Tier",
                run_score.score_tier,
                "success" if run_score.total_score >= 170 else "warning",
            ),
            DeepDiveMetricViewModel(
                "Valuation",
                format_money(run_score.estimated_valuation),
                "info",
            ),
            DeepDiveMetricViewModel("History", str(len(state.turn_history)), "info"),
        ),
        detail_lines=(
            f"Scenario objective: {state.scenario_objective or 'None set.'}",
            f"Campaign goal: {state.campaign_goal_id.value.replace('_', ' ')}",
            (
                f"Latest turn: revenue {format_money(latest_turn.total_revenue)} | "
                f"net {format_money(latest_turn.net_cash_flow)} | users {latest_turn.total_users}"
                if latest_turn is not None
                else "No turn ledger exists yet."
            ),
            f"Milestones unlocked: {len(state.milestone_history)}",
        ),
        actions=(
            DeepDiveActionViewModel(
                "view_report",
                "Full Report",
                "Open the broad run report in the 2D event flow.",
                "info",
            ),
            DeepDiveActionViewModel(
                "review_finance",
                "Finance Review",
                "Refresh finance-specific reporting.",
                "info",
            ),
            DeepDiveActionViewModel(
                "review_customers",
                "Customer Review",
                "Refresh account and retention reporting.",
                "info",
            ),
            DeepDiveActionViewModel(
                "review_partnerships",
                "Partner Review",
                "Refresh partnership reporting.",
                "info",
            ),
        ),
    )
    return (
        team_panel,
        finance_panel,
        customers_panel,
        partnerships_panel,
        board_panel,
        pipeline_panel,
        report_panel,
    )


def build_run_review_view_model(state: GameState) -> RunReviewViewModel:
    """Build the review scene for one completed live run."""

    score = calculate_run_score(state)
    postmortem = build_run_postmortem(state)
    summary_line = (
        f"Turn {state.company.current_turn} | score {score.total_score} ({score.score_tier}) | "
        f"cash {format_money(state.company.cash_on_hand)} | grade {score.campaign_grade}"
    )
    badges = (
        score.score_tier,
        state.exit_outcome.value if state.exit_outcome is not None else "in_progress",
        state.difficulty_mode.value,
    )
    findings = tuple(
        ReviewFindingViewModel(
            rank_label=f"#{finding.rank}",
            area=finding.area,
            severity=finding.severity,
            summary=finding.summary,
            command=finding.command,
            lesson=finding.lesson,
        )
        for finding in postmortem.findings
    )
    return RunReviewViewModel(
        title=postmortem.title,
        headline=postmortem.headline,
        summary_line=summary_line,
        next_focus=postmortem.next_run_focus,
        badges=badges,
        findings=findings,
    )


def build_archive_review_view_model(summary: RunArchiveSummary) -> RunReviewViewModel:
    """Build a compact review scene from one archived run summary."""

    findings: list[ReviewFindingViewModel] = []
    if summary.review_primary_area:
        findings.append(
            ReviewFindingViewModel(
                rank_label="#1",
                area=summary.review_primary_area,
                severity="watch",
                summary=summary.review_primary_summary or "Primary archive lesson captured.",
                command=summary.review_next_focus or "view_report",
                lesson=summary.review_next_focus or "Review the archived run details.",
            )
        )
    findings.append(
        ReviewFindingViewModel(
            rank_label=f"#{len(findings) + 1}",
            area="outcome",
            severity="high" if summary.game_over else "watch",
            summary=(
                f"Exit {summary.exit_outcome} at turn {summary.completed_turn} with "
                f"score tier {summary.score_tier}."
            ),
            command=summary.review_next_focus or "view_report",
            lesson=summary.strategic_outlook.replace("_", " "),
        )
    )
    return RunReviewViewModel(
        title=summary.review_title or "Archived Run Review",
        headline=f"{summary.company_name} | {summary.scenario_title}",
        summary_line=(
            f"Turn {summary.completed_turn} | score {summary.total_score} ({summary.score_tier}) | "
            f"grade {summary.campaign_grade} | cash {format_money(summary.final_cash)}"
        ),
        next_focus=summary.review_next_focus or "view_report",
        badges=summary.achievement_badges
        or (summary.exit_outcome, summary.score_tier, summary.campaign_grade),
        findings=tuple(findings[:3]),
    )


def build_save_slot_card_view_models(
    summaries: list[SaveSlotSummary],
) -> tuple[SaveSlotCardViewModel, ...]:
    """Build compact save-slot cards for the title scene."""

    cards = []
    for summary in summaries:
        tone = "info"
        if summary.game_over:
            tone = "danger"
        elif summary.victory_achieved:
            tone = "success"
        cards.append(
            SaveSlotCardViewModel(
                slot_name=summary.slot_name,
                headline=f"{summary.company_name} | Turn {summary.current_turn}",
                detail_lines=(
                    summary.scenario_title,
                    (
                        f"cash {format_money(summary.cash_on_hand)} | "
                        f"rep {summary.reputation} | team {summary.headcount}"
                    ),
                    (
                        f"updated {summary.updated_at[:19].replace('T', ' ')} | "
                        f"v{summary.saved_with_version}"
                    ),
                ),
                tone=tone,
            )
        )
    return tuple(cards)


def build_archive_card_view_models(
    summaries: list[RunArchiveSummary],
) -> tuple[ArchiveCardViewModel, ...]:
    """Build archive cards for the title scene."""

    cards = []
    for summary in summaries:
        tone = "danger" if summary.game_over else "success" if summary.victory_achieved else "info"
        cards.append(
            ArchiveCardViewModel(
                archive_key=summary.archive_key,
                headline=(
                    f"{summary.company_name} | {summary.total_score} | {summary.campaign_grade}"
                ),
                detail_lines=(
                    summary.scenario_title,
                    (
                        f"turn {summary.completed_turn} | exit {summary.exit_outcome} | "
                        f"cash {format_money(summary.final_cash)}"
                    ),
                    (summary.review_primary_summary or summary.strategic_outlook.replace("_", " ")),
                ),
                tone=tone,
            )
        )
    return tuple(cards)


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
    if ceiling <= 0:
        return 0.0
    return max(0.0, min(1.0, value / ceiling))


def _cash_ratio(cash: Decimal) -> float:
    if cash <= Decimal("0.00"):
        return 0.0
    return min(1.0, float(cash / Decimal("12000.00")))


def _money_ratio(value: Decimal, *, ceiling: Decimal) -> float:
    if value <= Decimal("0.00"):
        return 0.0
    return min(1.0, float(value / ceiling))


def _cash_tone(cash: Decimal) -> str:
    if cash >= Decimal("7000.00"):
        return "success"
    if cash >= Decimal("2500.00"):
        return "warning"
    return "danger"


def _runway_label(preview) -> str:
    runway_metric = _preview_metric(preview, "Runway")
    return runway_metric.projected if runway_metric is not None else "n/a"


def _runway_ratio(preview) -> float:
    runway_metric = _preview_metric(preview, "Runway")
    if runway_metric is None:
        return 0.15
    match = re.search(r"(\d+)", runway_metric.projected)
    runway = int(match.group(1)) if match is not None else None
    if runway is None:
        return 0.15
    return max(0.0, min(1.0, runway / 8))


def _preview_tone(warning_level: str) -> str:
    if warning_level == "critical":
        return "danger"
    if warning_level == "warning":
        return "warning"
    return "success"


def _signed_int(value: int) -> str:
    return f"{value:+d}"


def _preview_metric(preview, label: str):
    for metric in preview.metrics:
        if metric.label == label:
            return metric
    return None


def _attribute_tone(value: int) -> str:
    if value >= 65:
        return "success"
    if value >= 45:
        return "warning"
    return "danger"
