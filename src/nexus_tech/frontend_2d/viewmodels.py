"""View-model adapters for the lightweight 2D frontend."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import GameState, PendingEvent, Product, TurnAction
from nexus_tech.domain.money import format_money
from nexus_tech.persistence.save_coordinator import RunArchiveSummary, SaveSlotSummary
from nexus_tech.simulation.action_catalog import (
    get_action_label,
    get_action_presentation,
    humanize_action_text,
)
from nexus_tech.simulation.campaign_decisions import (
    build_campaign_path_legacy,
    build_campaign_path_legacy_from_labels,
    get_campaign_path_labels,
    get_campaign_path_outlook,
)
from nexus_tech.simulation.campaign_journey import get_campaign_journey_progress
from nexus_tech.simulation.decision_patterns import build_decision_pattern
from nexus_tech.simulation.difficulty import get_difficulty_profile
from nexus_tech.simulation.end_turn_preview import build_end_turn_preview
from nexus_tech.simulation.endgame import (
    calculate_endgame_pressure,
    calculate_endgame_readiness,
    evaluate_exit_outcome,
)
from nexus_tech.simulation.engine import TurnResolution
from nexus_tech.simulation.first_archive_mission import build_first_archive_mission
from nexus_tech.simulation.postmortem import build_run_postmortem
from nexus_tech.simulation.reporting import calculate_run_score
from nexus_tech.simulation.risk_forecast import build_risk_forecast
from nexus_tech.simulation.run_phase import get_run_phase
from nexus_tech.simulation.strategic_rhythm import StrategicRhythm, build_strategic_rhythm
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
    label: str
    family_label: str
    source: str
    detail: str
    consequence: str
    urgency_label: str


@dataclass(frozen=True)
class DecisionBriefViewModel:
    """One ordered objective-to-resolution route for the live run."""

    objective_label: str
    objective: str
    plan_label: str
    plan_progress_label: str
    plan_detail: str
    plan_progress: float
    plan_tone: str
    command: str
    command_label: str
    command_effect: str
    command_source: str
    command_detail: str
    command_consequence: str
    urgency_label: str
    end_turn_label: str
    end_turn_detail: str
    end_turn_tone: str
    end_turn_enabled: bool
    later_label: str
    later_detail: str


@dataclass(frozen=True)
class RunJourneyViewModel:
    """Compact first-run journey state for the live 2D HUD."""

    step_label: str
    step_title: str
    progress_label: str
    progress: float
    next_action: str


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
class DeepDiveInspectorItemViewModel:
    """One compact record rendered inside a detailed 2D inspector."""

    title: str
    detail_lines: tuple[str, ...]
    tone: str
    payload: str = ""
    actions: tuple[DeepDiveActionViewModel, ...] = ()


@dataclass(frozen=True)
class DeepDiveInspectorSectionViewModel:
    """One logical section in a detailed 2D inspector overlay."""

    key: str
    title: str
    tone: str
    items: tuple[DeepDiveInspectorItemViewModel, ...]


@dataclass(frozen=True)
class DeepDivePanelViewModel:
    """One operational deep-dive panel."""

    key: str
    title: str
    summary: str
    metrics: tuple[DeepDiveMetricViewModel, ...]
    detail_lines: tuple[str, ...]
    actions: tuple[DeepDiveActionViewModel, ...]
    inspectors: tuple[DeepDiveInspectorSectionViewModel, ...] = ()


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
    phase_labels: tuple[str, ...]
    strategic_headline: str
    cause_lines: tuple[str, ...]
    strategic_lines: tuple[str, ...]
    focus_command: str
    focus_label: str
    focus_detail: str
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
    campaign_legacy_title: str
    campaign_legacy_detail: str
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
    phase_label: str
    campaign_chapter_label: str
    campaign_objective: str
    campaign_lens: str
    score_label: str
    market_label: str
    roadmap_label: str
    budget_label: str
    action_points_label: str
    watch_for: str
    header_note: str
    stats: tuple[GaugeViewModel, ...]
    snapshot_chips: tuple[SnapshotChipViewModel, ...]
    run_journey: RunJourneyViewModel
    products: tuple[ProductCardViewModel, ...]
    coach_lines: tuple[CoachLineViewModel, ...]
    decision_brief: DecisionBriefViewModel
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
    phase = get_run_phase(state.company.current_turn)
    journey_progress = get_campaign_journey_progress(
        state.scenario_id,
        state.company.current_turn,
    )
    coach = build_turn_coach(state)
    forecast = build_risk_forecast(state)
    preview = build_end_turn_preview(state)
    rhythm = build_strategic_rhythm(
        state,
        coach=coach,
        forecast=forecast,
        preview=preview,
    )
    first_archive = build_first_archive_mission(state)
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
        SnapshotChipViewModel(
            "Journey",
            first_archive.step_label,
            "success" if first_archive.complete else "info",
        ),
        SnapshotChipViewModel(
            "Plan",
            rhythm.plan_progress_label.split(" | ", maxsplit=1)[0],
            rhythm.plan_tone,
        ),
        SnapshotChipViewModel("Team", str(len(state.employees)), "info"),
        SnapshotChipViewModel(
            "Idle",
            str(sum(1 for employee in state.employees if employee.assigned_product_id is None)),
            "warning",
        ),
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
            label=get_action_presentation(recommendation.command).label,
            family_label=get_action_presentation(recommendation.command).family_label,
            source=recommendation.source,
            detail=humanize_action_text(recommendation.rationale),
            consequence=humanize_action_text(recommendation.consequence),
            urgency_label=_recommendation_urgency_label(
                recommendation.urgency,
                recommendation.horizon_turns,
            ),
        )
        for recommendation in coach.recommendations[:3]
    )
    deferred_lines = tuple(
        f"{get_action_presentation(action.command).label}: {action.reason}"
        for action in coach.deferred_actions[:2]
    ) or ("No deferred actions are flashing right now.",)
    risk_lines = tuple(
        f"{item.area}: {get_action_presentation(item.command).label} ({item.severity})"
        for item in forecast.items[:3]
    ) or ("No elevated operating risk is flashing right now.",)
    campaign_chapter_label = (
        journey_progress.act_label if journey_progress is not None else phase.title
    )
    campaign_objective = (
        journey_progress.chapter.objective if journey_progress is not None else phase.objective
    )
    base_campaign_lens = (
        journey_progress.chapter.decision_lens
        if journey_progress is not None
        else difficulty.watch_for
    )
    campaign_path_labels = get_campaign_path_labels(state)
    campaign_path_outlook = get_campaign_path_outlook(state)
    campaign_lens = (
        f"{campaign_path_labels[-1]} | {campaign_path_outlook or base_campaign_lens}"
        if campaign_path_labels
        else base_campaign_lens
    )
    decision_brief = _build_decision_brief(rhythm)
    decision_timing = decision_brief.urgency_label.split("/", maxsplit=1)[0].strip()
    header_note = (
        f"Next: {decision_brief.command_label} | Due: {decision_timing} | "
        f"End Turn: {decision_brief.end_turn_label}"
    )
    return GameViewModel(
        company_name=state.company.name,
        scenario_title=state.scenario_title,
        difficulty_label=state.difficulty_mode.value,
        difficulty_summary=difficulty.summary,
        turn_label=f"Turn {state.company.current_turn}",
        phase_label=f"{phase.title} / {phase.turn_window}",
        campaign_chapter_label=campaign_chapter_label,
        campaign_objective=campaign_objective,
        campaign_lens=campaign_lens,
        score_label=f"{score.total_score} ({score.score_tier})",
        market_label=state.market_cycle.value.replace("_", " ").title(),
        roadmap_label=state.roadmap_focus.value.replace("_", " ").title(),
        budget_label=state.quarter_plan.budget_stance.value.replace("_", " ").title(),
        action_points_label=str(state.action_points_remaining),
        watch_for=difficulty.watch_for,
        header_note=header_note,
        stats=stats,
        snapshot_chips=snapshot_chips,
        run_journey=RunJourneyViewModel(
            step_label=first_archive.step_label,
            step_title=first_archive.current_step.title,
            progress_label=first_archive.progress_label,
            progress=first_archive.progress,
            next_action=first_archive.next_action,
        ),
        products=products,
        coach_lines=coach_lines,
        decision_brief=decision_brief,
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
    support_delta = (
        resolution.state.support_program.backlog_queue
        - previous_state.support_program.backlog_queue
    )
    previous_readiness = calculate_endgame_readiness(previous_state)
    current_readiness = calculate_endgame_readiness(resolution.state, resolution.run_score)
    previous_pressure = calculate_endgame_pressure(previous_state, previous_readiness)
    current_pressure = calculate_endgame_pressure(resolution.state, current_readiness)
    previous_blocked_paths = sum(
        1 for gate in previous_pressure.path_outcome_gates if "blocked" in gate.lower()
    )
    current_blocked_paths = sum(
        1 for gate in current_pressure.path_outcome_gates if "blocked" in gate.lower()
    )
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
            key="support",
            label="Support Queue",
            value_text=_signed_int(support_delta),
            detail=f"Backlog now {resolution.state.support_program.backlog_queue}",
            ratio=_scaled_ratio(abs(support_delta), ceiling=8),
            tone="danger" if support_delta > 0 else "success",
        ),
        TurnMetricViewModel(
            key="gates",
            label="Blocked Gates",
            value_text=str(current_blocked_paths),
            detail=f"Was {previous_blocked_paths} | gap {current_pressure.path_gap}",
            ratio=_scaled_ratio(current_blocked_paths, ceiling=4),
            tone=(
                "danger"
                if current_blocked_paths >= 3
                else "warning"
                if current_blocked_paths >= 1
                else "success"
            ),
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
    ipo_delta = _signed_int(
        current_readiness.ipo_readiness_score - previous_readiness.ipo_readiness_score
    )
    acquisition_delta = _signed_int(
        current_readiness.acquisition_interest_score - previous_readiness.acquisition_interest_score
    )
    independence_delta = _signed_int(
        current_readiness.independence_score - previous_readiness.independence_score
    )
    reset_risk_delta = _signed_int(
        current_pressure.board_reset_risk - previous_pressure.board_reset_risk
    )
    next_rhythm = build_strategic_rhythm(resolution.state)
    product_cause = (
        (
            f"{product_lines[0].name}: {product_lines[0].detail}; "
            f"revenue {product_lines[0].revenue_text}."
        )
        if product_lines
        else "No active product generated an operating result this turn."
    )
    return TurnSummaryViewModel(
        title=f"Turn {resolution.resolved_turn} Resolved",
        headline=resolution.scale_pressure_summary,
        narrative=resolution.narrative,
        footer=footer,
        phase_labels=("Cash + Demand", "Operating Pressure", "Strategic Outlook"),
        strategic_headline=(
            f"{next_rhythm.objective_label} | Plan {next_rhythm.plan_progress_label}"
        ),
        cause_lines=(
            (
                f"Cash: revenue {format_money(resolution.total_revenue)} minus cost "
                f"{format_money(resolution.total_operating_cost)} produced "
                f"{format_money(resolution.net_cash_flow)} net."
            ),
            (
                f"Demand: users moved {_signed_int(total_user_delta)} in a "
                f"{resolution.market_cycle.value} market; reputation moved "
                f"{_signed_int(resolution.reputation_delta)}."
            ),
            (
                f"Pressure: board {_signed_int(board_delta)}, support "
                f"{_signed_int(support_delta)}, blocked gates "
                f"{previous_blocked_paths} -> {current_blocked_paths}."
            ),
            product_cause,
        ),
        strategic_lines=(
            (
                f"Readiness delta: IPO {ipo_delta} | M&A {acquisition_delta} | "
                f"Ind {independence_delta}"
            ),
            (
                f"Blocked gates {previous_blocked_paths} -> {current_blocked_paths} | "
                f"board reset risk {reset_risk_delta}"
            ),
            f"Next move: {next_rhythm.command_label} ({next_rhythm.urgency_label})",
            f"Later: {next_rhythm.later_label} | {next_rhythm.later_detail}",
        ),
        focus_command=next_rhythm.command,
        focus_label=next_rhythm.command_label,
        focus_detail=next_rhythm.command_detail,
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
    decision_pattern = build_decision_pattern(state.decision_history)
    endgame_readiness = calculate_endgame_readiness(state, run_score)
    endgame_pressure = calculate_endgame_pressure(state, endgame_readiness)
    endgame_evaluation = evaluate_exit_outcome(state, run_score)
    product_by_id = {product.id: product for product in state.products}
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
            DeepDiveActionViewModel(
                "review_team",
                "Team Review",
                "Open the full staffing and hiring inspector.",
                "info",
            ),
        ),
        inspectors=_build_team_inspectors(state, product_by_id=product_by_id),
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
                "review_finance",
                "Finance Review",
                "Open the full finance and forecast inspector.",
                "info",
            ),
            DeepDiveActionViewModel(
                "review_board",
                "Board Review",
                "Open governance status without leaving 2D.",
                "info",
            ),
        ),
        inspectors=_build_finance_inspectors(state),
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
        inspectors=_build_customer_inspectors(state, product_by_id=product_by_id),
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
        inspectors=_build_partnership_inspectors(state, product_by_id=product_by_id),
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
        inspectors=_build_board_inspectors(state),
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
        inspectors=_build_pipeline_inspectors(state, product_by_id=product_by_id),
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
            DeepDiveMetricViewModel("Decisions", str(len(state.decision_history)), "info"),
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
            (
                f"Decision pattern: {decision_pattern.style_label} | "
                f"{decision_pattern.dominant_family_count}/"
                f"{decision_pattern.operating_decisions} in the largest family share"
                if decision_pattern.operating_decisions
                else "Decision pattern: waiting for the first operating choice."
            ),
            (
                f"Latest decision: {state.decision_history[-1].label} | "
                f"{state.decision_history[-1].impact_summary}"
                if state.decision_history
                else "No state-changing decisions recorded yet."
            ),
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
        inspectors=_build_report_inspectors(state),
    )
    endgame_panel = _build_endgame_panel(
        state,
        readiness=endgame_readiness,
        pressure=endgame_pressure,
        evaluation=endgame_evaluation,
    )
    return (
        team_panel,
        finance_panel,
        customers_panel,
        partnerships_panel,
        board_panel,
        pipeline_panel,
        report_panel,
        endgame_panel,
    )


def _build_endgame_panel(
    state: GameState,
    *,
    readiness,
    pressure,
    evaluation,
) -> DeepDivePanelViewModel:
    path_labels = ("IPO", "M&A", "Independence", "Reset")
    blocked_paths = sum(1 for gate in pressure.path_outcome_gates if "blocked" in gate.lower())
    gate_command_tone = "danger" if blocked_paths >= 2 else "warning" if blocked_paths else "info"
    hotspot_command, hotspot_label, hotspot_detail, hotspot_tone = _endgame_hotspot_review_spec(
        pressure
    )
    gate_action_label = get_action_label(pressure.path_gate_command_alert)
    return DeepDivePanelViewModel(
        key="endgame",
        title="Endgame / Exit Board",
        summary=(
            "Readiness is scored /100; lower Reset Risk is safer. Start with Recommended Fix."
        ),
        metrics=(
            DeepDiveMetricViewModel(
                "IPO Ready",
                f"{readiness.ipo_readiness_score}/100",
                _attribute_tone(readiness.ipo_readiness_score),
            ),
            DeepDiveMetricViewModel(
                "M&A Ready",
                f"{readiness.acquisition_interest_score}/100",
                _attribute_tone(readiness.acquisition_interest_score),
            ),
            DeepDiveMetricViewModel(
                "Independence",
                f"{readiness.independence_score}/100",
                _attribute_tone(readiness.independence_score),
            ),
            DeepDiveMetricViewModel(
                "Reset Risk (low)",
                f"{pressure.board_reset_risk}/100",
                _attribute_tone(100 - pressure.board_reset_risk),
            ),
        ),
        detail_lines=(
            (
                f"Projected path: {evaluation.title} | grade {evaluation.grade} | "
                f"offer {format_money(evaluation.offer_value)}"
            ),
            (
                f"Clarity: {pressure.strategic_clarity} | durability "
                f"{pressure.operating_durability} | dominant "
                f"{pressure.dominant_pressure.replace('_', ' ')}"
            ),
            (
                f"Blocked paths: {blocked_paths}/4 | hotspot {hotspot_label.lower()} | "
                f"next {gate_action_label}"
            ),
            f"Next move: {gate_action_label} | {humanize_action_text(pressure.path_gate_alert)}",
            f"Recommendation: {humanize_action_text(pressure.recommendation)}",
        ),
        actions=tuple(
            [
                DeepDiveActionViewModel(
                    pressure.path_gate_command_alert,
                    "Recommended Fix",
                    f"{gate_action_label} clears the nearest exit gate.",
                    gate_command_tone,
                ),
                DeepDiveActionViewModel(
                    hotspot_command,
                    "Review Main Risk",
                    hotspot_detail,
                    hotspot_tone,
                ),
                *(
                    DeepDiveActionViewModel(
                        pressure.path_gate_commands[index],
                        f"{path_labels[index]} Fix",
                        pressure.path_gate_actions[index],
                        (
                            "success"
                            if "open" in pressure.path_outcome_gates[index].lower()
                            else "warning"
                        ),
                    )
                    for index in range(4)
                ),
                DeepDiveActionViewModel(
                    TurnAction.REVIEW_BOARD.value,
                    "Board Review",
                    "Refresh governance and reset pressure.",
                    "warning",
                ),
                DeepDiveActionViewModel(
                    TurnAction.REVIEW_FINANCE.value,
                    "Finance Review",
                    "Refresh reserve, debt, and capital posture.",
                    "warning",
                ),
                DeepDiveActionViewModel(
                    TurnAction.REVIEW_PARTNERSHIPS.value,
                    "Partner Review",
                    "Refresh diligence and channel concentration.",
                    "info",
                ),
                DeepDiveActionViewModel(
                    TurnAction.VIEW_REPORT.value,
                    "Full Report",
                    "Open the broader scorecard and archive-ready summary.",
                    "info",
                ),
            ]
        ),
        inspectors=_build_endgame_inspectors(
            state,
            readiness=readiness,
            pressure=pressure,
            evaluation=evaluation,
        ),
    )


def build_endgame_cockpit_actions(
    state: GameState,
    *,
    selected_product_id: str | None = None,
) -> tuple[DeepDiveActionViewModel, ...]:
    """Expose the live cockpit actions for tests and richer 2D routing."""

    panel = next(
        panel
        for panel in build_deep_dive_panel_view_models(
            state,
            selected_product_id=selected_product_id,
        )
        if panel.key == "endgame"
    )
    return panel.actions


def _endgame_hotspot_review_spec(pressure) -> tuple[str, str, str, str]:
    if pressure.dominant_pressure == "public_market_scrutiny":
        return (
            TurnAction.REVIEW_CUSTOMERS.value,
            "Customer Hotspot",
            "Inspect enterprise retention risk before an IPO.",
            "warning",
        )
    if pressure.dominant_pressure == "acquirer_diligence":
        return (
            TurnAction.REVIEW_PARTNERSHIPS.value,
            "Channel Hotspot",
            "Inspect partner concentration risk before M&A.",
            "warning",
        )
    if pressure.dominant_pressure == "independence_discipline":
        return (
            TurnAction.REVIEW_FINANCE.value,
            "Capital Hotspot",
            "Inspect reserve, debt, and billing risk.",
            "warning",
        )
    return (
        TurnAction.REVIEW_BOARD.value,
        "Reset Hotspot",
        "Inspect governance risk before a forced reset.",
        "danger",
    )


def build_run_review_view_model(state: GameState) -> RunReviewViewModel:
    """Build the review scene for one completed live run."""

    score = calculate_run_score(state)
    postmortem = build_run_postmortem(state)
    legacy = build_campaign_path_legacy(state)
    decision_pattern = build_decision_pattern(state.decision_history)
    outcome_label = (
        state.exit_outcome.value if state.exit_outcome is not None else "in_progress"
    ).replace("_", " ")
    summary_line = (
        f"Turn {state.company.current_turn} | score {score.total_score} ({score.score_tier}) | "
        f"cash {format_money(state.company.cash_on_hand)} | grade {score.campaign_grade}"
    )
    badges = (
        f"Style: {decision_pattern.style_label}",
        f"Outcome: {outcome_label.title()}",
        f"Difficulty: {state.difficulty_mode.value.replace('_', ' ').title()}",
        *get_campaign_path_labels(state),
    )
    findings = tuple(
        ReviewFindingViewModel(
            rank_label=f"#{finding.rank}",
            area=finding.area,
            severity=finding.severity,
            summary=finding.summary,
            command=get_action_label(finding.command),
            lesson=finding.lesson,
        )
        for finding in postmortem.findings
    )
    return RunReviewViewModel(
        title=postmortem.title,
        headline=postmortem.headline,
        summary_line=summary_line,
        next_focus=get_action_label(postmortem.next_run_focus),
        campaign_legacy_title=legacy.route_label if legacy is not None else "",
        campaign_legacy_detail=(
            f"{legacy.pressure_line} {legacy.mandate}" if legacy is not None else ""
        ),
        badges=badges,
        findings=findings,
    )


def build_archive_review_view_model(summary: RunArchiveSummary) -> RunReviewViewModel:
    """Build a compact review scene from one archived run summary."""

    findings: list[ReviewFindingViewModel] = []
    next_focus = get_action_label(summary.review_next_focus or TurnAction.VIEW_REPORT.value)
    legacy = build_campaign_path_legacy_from_labels(summary.scenario_id, summary.campaign_path)
    if summary.review_primary_area:
        findings.append(
            ReviewFindingViewModel(
                rank_label="#1",
                area=summary.review_primary_area,
                severity="watch",
                summary=summary.review_primary_summary or "Primary archive lesson captured.",
                command=next_focus,
                lesson=f"Start the next run with {next_focus} before taking on more risk.",
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
            command=next_focus,
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
        next_focus=next_focus,
        campaign_legacy_title=legacy.route_label if legacy is not None else "",
        campaign_legacy_detail=(
            f"{legacy.pressure_line} {legacy.mandate}" if legacy is not None else ""
        ),
        badges=tuple(
            dict.fromkeys(
                (
                    *summary.achievement_badges,
                    summary.difficulty_mode,
                    *summary.campaign_path,
                    summary.exit_outcome,
                    summary.score_tier,
                    summary.campaign_grade,
                )
            )
        ),
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
                    f"{summary.scenario_title} | {summary.difficulty_mode}",
                    (
                        f"turn {summary.completed_turn} | exit {summary.exit_outcome} | "
                        f"cash {format_money(summary.final_cash)}"
                    ),
                    (
                        " > ".join(summary.campaign_path)
                        or summary.review_primary_summary
                        or summary.strategic_outlook.replace("_", " ")
                    ),
                ),
                tone=tone,
            )
        )
    return tuple(cards)


def _build_team_inspectors(
    state: GameState,
    *,
    product_by_id: dict,
) -> tuple[DeepDiveInspectorSectionViewModel, ...]:
    roster_items = tuple(
        DeepDiveInspectorItemViewModel(
            title=employee.full_name,
            detail_lines=(
                (
                    f"{employee.role.value.replace('_', ' ')} | "
                    f"{employee.seniority.value} | "
                    f"{_product_name(product_by_id, employee.assigned_product_id) or 'bench'}"
                ),
                (
                    f"morale {employee.morale} | energy {employee.energy} | "
                    f"perf {employee.performance_rating}"
                ),
            ),
            tone=_attribute_tone((employee.morale + employee.energy) // 2),
            payload=employee.id.hex,
            actions=tuple(
                action
                for action in (
                    DeepDiveActionViewModel(
                        "assign_employee",
                        "Assign",
                        "Assign to the selected product.",
                        "success",
                    )
                    if employee.assigned_product_id is None
                    else None,
                    DeepDiveActionViewModel(
                        "train_employee",
                        "Train",
                        "Raise this teammate's output.",
                        "info",
                    ),
                    DeepDiveActionViewModel(
                        "promote_employee",
                        "Promote",
                        "Advance this teammate if they are ready.",
                        "warning",
                    ),
                )
                if action is not None
            ),
        )
        for employee in state.employees[:3]
    ) or (_placeholder_item("No Team Yet", "Hire the first teammate to unlock staffing depth."),)
    candidate_items = tuple(
        DeepDiveInspectorItemViewModel(
            title=candidate.full_name,
            detail_lines=(
                (
                    f"{candidate.role.value.replace('_', ' ')} | "
                    f"{candidate.seniority.value} | {candidate.stage.value}"
                ),
                (
                    f"salary {format_money(candidate.salary_expectation)} | "
                    f"prod {candidate.expected_productivity} | expires t{candidate.expires_turn}"
                ),
            ),
            tone="warning" if candidate.expires_turn <= state.company.current_turn + 1 else "info",
            payload=candidate.id.hex,
            actions=tuple(
                action
                for action in (
                    DeepDiveActionViewModel(
                        "screen_candidate",
                        "Screen",
                        "Move this sourced candidate forward.",
                        "info",
                    )
                    if candidate.stage.value == "sourced"
                    else None,
                    DeepDiveActionViewModel(
                        "interview_candidate",
                        "Interview",
                        "Interview this screened candidate.",
                        "warning",
                    )
                    if candidate.stage.value == "screened"
                    else None,
                    DeepDiveActionViewModel(
                        "make_hiring_offer",
                        "Offer",
                        "Make the hiring offer now.",
                        "success",
                    )
                    if candidate.stage.value == "interviewed"
                    else None,
                )
                if action is not None
            ),
        )
        for candidate in state.hiring_candidates
    ) or (
        _placeholder_item(
            "Hiring Funnel Empty",
            "Source candidates before screening or interviewing.",
            tone="warning",
        ),
    )
    return (
        DeepDiveInspectorSectionViewModel(
            key="roster",
            title="Roster",
            tone="info",
            items=roster_items,
        ),
        DeepDiveInspectorSectionViewModel(
            key="candidates",
            title="Hiring Funnel",
            tone="warning",
            items=candidate_items,
        ),
    )


def _build_finance_inspectors(state: GameState) -> tuple[DeepDiveInspectorSectionViewModel, ...]:
    runway_text = (
        f"{state.finance.forecast_runway_turns} turns"
        if state.finance.forecast_runway_turns is not None
        else "unknown"
    )
    capital_items = (
        DeepDiveInspectorItemViewModel(
            title="Liquidity",
            detail_lines=(
                (
                    f"cash {format_money(state.company.cash_on_hand)} | "
                    f"forecast {format_money(state.finance.forecast_net_cash_flow)}"
                ),
                f"runway {runway_text} | burn multiple {state.finance.burn_multiple}",
            ),
            tone=_cash_tone(state.company.cash_on_hand),
            actions=(
                DeepDiveActionViewModel(
                    "take_loan",
                    "Loan",
                    "Extend liquidity immediately.",
                    "warning",
                ),
                DeepDiveActionViewModel(
                    "raise_angel",
                    "Angel",
                    "Raise equity against traction.",
                    "info",
                ),
            ),
        ),
        DeepDiveInspectorItemViewModel(
            title="Leverage",
            detail_lines=(
                (
                    f"debt {format_money(state.finance.debt_principal)} | "
                    f"raised {format_money(state.finance.total_raised)}"
                ),
                (
                    f"dilution {state.finance.equity_dilution} | "
                    f"covenant {state.finance.covenant_risk}"
                ),
            ),
            tone="warning" if state.finance.debt_principal > Decimal("0.00") else "success",
            actions=(
                DeepDiveActionViewModel(
                    "set_capital_plan",
                    "Capital Plan",
                    "Reframe funding posture.",
                    "warning",
                ),
            ),
        ),
    )
    planning_items = (
        DeepDiveInspectorItemViewModel(
            title="Capital Plan",
            detail_lines=(
                (
                    f"{state.capital_plan.mode.value.replace('_', ' ')} | "
                    f"{state.capital_plan.source_preference.value.replace('_', ' ')}"
                ),
                (
                    f"reserve {format_money(state.capital_plan.reserve_target)} | "
                    f"horizon {state.capital_plan.planning_horizon_turns} turns"
                ),
            ),
            tone="info",
            actions=(
                DeepDiveActionViewModel(
                    "set_capital_plan",
                    "Edit Plan",
                    "Choose a new capital posture.",
                    "warning",
                ),
            ),
        ),
        DeepDiveInspectorItemViewModel(
            title="Quarter Plan",
            detail_lines=(
                (
                    f"budget {state.quarter_plan.budget_stance.value} | "
                    f"target turn {state.quarter_plan.target_turn}"
                ),
                (
                    f"rev {format_money(state.quarter_plan.revenue_target)} | "
                    f"cash {format_money(state.quarter_plan.cash_reserve_target)}"
                ),
            ),
            tone="warning",
            actions=(
                DeepDiveActionViewModel(
                    "set_functional_budget",
                    "Function Budget",
                    "Rebalance operating allocation.",
                    "warning",
                ),
            ),
        ),
    )
    return (
        DeepDiveInspectorSectionViewModel(
            key="capital",
            title="Capital Posture",
            tone="warning",
            items=capital_items,
        ),
        DeepDiveInspectorSectionViewModel(
            key="planning",
            title="Plans",
            tone="info",
            items=planning_items,
        ),
    )


def _build_customer_inspectors(
    state: GameState,
    *,
    product_by_id: dict,
) -> tuple[DeepDiveInspectorSectionViewModel, ...]:
    active_accounts = [
        account for account in state.customer_accounts if account.status.value != "churned"
    ]
    hotspot_accounts = sorted(
        active_accounts,
        key=lambda account: (
            account.churn_risk + account.sla_breach_risk + account.invoice_risk,
            account.contract_value,
        ),
        reverse=True,
    )
    account_items = tuple(
        DeepDiveInspectorItemViewModel(
            title=account.name,
            detail_lines=(
                (
                    f"{_product_name(product_by_id, account.product_id) or 'unknown'} | "
                    f"{account.segment.value} | {account.plan_tier.value}"
                ),
                (
                    f"renewal {account.renewal_health} | churn {account.churn_risk} | "
                    f"tickets {account.open_tickets}"
                ),
            ),
            tone="danger" if account.churn_risk >= 65 else "warning",
            actions=(
                DeepDiveActionViewModel(
                    "adjust_pricing",
                    "Pricing",
                    "Retune monetization on the selected product.",
                    "warning",
                ),
                DeepDiveActionViewModel(
                    "set_target_segment",
                    "Segment",
                    "Reposition the selected product.",
                    "info",
                ),
            ),
        )
        for account in hotspot_accounts
    ) or (
        _placeholder_item(
            "No Key Accounts",
            "Land more traction before customer-account pressure starts stacking up.",
        ),
    )
    support_items = (
        DeepDiveInspectorItemViewModel(
            title="Support Control",
            detail_lines=(
                (
                    f"lane {state.support_program.lane_focus.value.replace('_', ' ')} | "
                    f"backlog {state.support_program.backlog_queue}"
                ),
                (
                    f"enterprise {state.support_program.enterprise_ticket_pressure} | "
                    f"onboarding {state.support_program.onboarding_ticket_pressure} | "
                    f"billing {state.support_program.billing_ticket_pressure}"
                ),
            ),
            tone=("danger" if state.support_program.escalation_queue >= 3 else "warning"),
            actions=(
                DeepDiveActionViewModel(
                    "set_support_lane_focus",
                    "Lane Focus",
                    "Reallocate service attention.",
                    "warning",
                ),
                DeepDiveActionViewModel(
                    "triage_support_backlog",
                    "Triage",
                    "Clear the support queue faster.",
                    "warning",
                ),
            ),
        ),
    )
    return (
        DeepDiveInspectorSectionViewModel(
            key="accounts",
            title="Hot Accounts",
            tone="warning",
            items=account_items,
        ),
        DeepDiveInspectorSectionViewModel(
            key="support",
            title="Support Lanes",
            tone="danger" if state.support_program.escalation_queue >= 3 else "warning",
            items=support_items,
        ),
    )


def _build_partnership_inspectors(
    state: GameState,
    *,
    product_by_id: dict,
) -> tuple[DeepDiveInspectorSectionViewModel, ...]:
    active_partnerships = sum(1 for item in state.partnerships if item.status.value == "active")
    recovery_partnerships = sum(
        1 for item in state.partnerships if item.status.value in {"strained", "recovery", "paused"}
    )
    total_sourced_revenue = format_money(sum(item.sourced_revenue for item in state.partnerships))
    partner_items = tuple(
        DeepDiveInspectorItemViewModel(
            title=partnership.name,
            detail_lines=(
                (
                    f"{partnership.channel.value} | {partnership.status.value} | "
                    f"{_product_name(product_by_id, partnership.product_id) or 'unknown'}"
                ),
                (
                    f"risk {partnership.risk} | conflict {partnership.conflict_pressure} | "
                    f"revenue {format_money(partnership.sourced_revenue)}"
                ),
            ),
            tone="danger" if partnership.risk >= 65 else "warning",
            payload=partnership.id.hex,
            actions=(
                DeepDiveActionViewModel(
                    "renegotiate_partnership",
                    "Renegotiate",
                    "Repair this channel relationship.",
                    "warning",
                ),
                DeepDiveActionViewModel(
                    "run_partner_recovery_sprint",
                    "Recovery Sprint",
                    "Reduce immediate partner strain.",
                    "warning",
                ),
            ),
        )
        for partnership in sorted(
            state.partnerships,
            key=lambda item: (item.risk, item.conflict_pressure, item.sourced_revenue),
            reverse=True,
        )
    ) or (
        _placeholder_item(
            "No Live Channels",
            "Open a reseller, integration, or marketplace lane to inspect channel depth.",
        ),
    )
    mix_items = (
        DeepDiveInspectorItemViewModel(
            title="Exposure Mix",
            detail_lines=(
                (f"active {active_partnerships} | recovery {recovery_partnerships}"),
                (
                    f"users {sum(item.sourced_users for item in state.partnerships)} | "
                    f"sourced revenue {total_sourced_revenue}"
                ),
            ),
            tone="info",
            actions=(
                DeepDiveActionViewModel(
                    "rebalance_channel_mix",
                    "Rebalance",
                    "Reduce channel concentration risk.",
                    "info",
                ),
            ),
        ),
    )
    return (
        DeepDiveInspectorSectionViewModel(
            key="partners",
            title="Live Channels",
            tone="warning",
            items=partner_items,
        ),
        DeepDiveInspectorSectionViewModel(
            key="mix",
            title="Exposure Mix",
            tone="info",
            items=mix_items,
        ),
    )


def _build_board_inspectors(state: GameState) -> tuple[DeepDiveInspectorSectionViewModel, ...]:
    resolution_items = (
        DeepDiveInspectorItemViewModel(
            title=state.finance.board_resolution.value.replace("_", " ").title(),
            detail_lines=(
                (
                    f"directive {state.finance.board_directive.value.replace('_', ' ')} | "
                    f"ask {state.finance.active_board_ask.value.replace('_', ' ')}"
                ),
                (
                    "response due now"
                    if state.finance.board_resolution_due
                    else f"window {state.finance.board_resolution_window} turns"
                ),
            ),
            tone="danger" if state.finance.board_resolution_due else "warning",
            actions=(
                DeepDiveActionViewModel(
                    "execute_board_response",
                    "Board Response",
                    "Answer the current board ask.",
                    "warning",
                ),
                DeepDiveActionViewModel(
                    "start_board_recovery_plan",
                    "Recovery Plan",
                    "Reset governance posture.",
                    "warning",
                ),
            ),
        ),
    )
    scorecard_items = (
        DeepDiveInspectorItemViewModel(
            title="Commercial Scorecard",
            detail_lines=(
                f"profitability {state.finance.board_profitability_score}",
                f"reliability {state.finance.board_reliability_score}",
            ),
            tone=_attribute_tone(
                (state.finance.board_profitability_score + state.finance.board_reliability_score)
                // 2
            ),
            actions=(
                DeepDiveActionViewModel(
                    "review_board",
                    "Refresh",
                    "Refresh governance status.",
                    "info",
                ),
            ),
        ),
        DeepDiveInspectorItemViewModel(
            title="Operating Scorecard",
            detail_lines=(
                f"team health {state.finance.board_team_health_score}",
                f"portfolio focus {state.finance.board_portfolio_focus_score}",
            ),
            tone=_attribute_tone(
                (state.finance.board_team_health_score + state.finance.board_portfolio_focus_score)
                // 2
            ),
            actions=(
                DeepDiveActionViewModel(
                    "execute_restructure_plan",
                    "Restructure",
                    "Escalate to restructure if needed.",
                    "danger",
                ),
            ),
        ),
    )
    alert_items = (
        DeepDiveInspectorItemViewModel(
            title="Warning Ladder",
            detail_lines=(
                (
                    f"warnings {state.finance.board_warning_level} | "
                    f"miss streak {state.finance.board_resolution_miss_streak}"
                ),
                (
                    f"crisis {state.finance.governance_crisis_level} | "
                    f"recovery {state.finance.board_recovery_turns_remaining} turns"
                ),
            ),
            tone="danger" if state.finance.governance_crisis_active else "warning",
            actions=(
                DeepDiveActionViewModel(
                    "start_board_recovery_plan",
                    "Recovery Plan",
                    "Address the governance alert.",
                    "warning",
                ),
            ),
        ),
    )
    return (
        DeepDiveInspectorSectionViewModel(
            key="resolution",
            title="Resolution Loop",
            tone="warning",
            items=resolution_items,
        ),
        DeepDiveInspectorSectionViewModel(
            key="scorecard",
            title="Scorecard",
            tone="info",
            items=scorecard_items,
        ),
        DeepDiveInspectorSectionViewModel(
            key="alerts",
            title="Alerts",
            tone="danger" if state.finance.governance_crisis_active else "warning",
            items=alert_items,
        ),
    )


def _build_pipeline_inspectors(
    state: GameState,
    *,
    product_by_id: dict,
) -> tuple[DeepDiveInspectorSectionViewModel, ...]:
    deal_items = tuple(
        DeepDiveInspectorItemViewModel(
            title=deal.name,
            detail_lines=(
                (
                    f"{deal.stage.value} | {deal.segment.value} | "
                    f"{_product_name(product_by_id, deal.product_id) or 'unknown'}"
                ),
                (
                    f"prob {deal.probability} | value {format_money(deal.value)} | "
                    f"{deal.plan_tier.value}"
                ),
            ),
            tone="success" if deal.probability >= 65 else "warning",
            payload=deal.id.hex,
            actions=(
                DeepDiveActionViewModel(
                    "advance_sales_deal",
                    "Advance Deal",
                    "Move this opportunity forward.",
                    "warning",
                ),
            ),
        )
        for deal in state.sales_deals
    ) or (
        _placeholder_item(
            "No Sales Deals",
            "Create a deal before trying to advance the enterprise pipeline.",
        ),
    )
    release_items = tuple(
        DeepDiveInspectorItemViewModel(
            title=release.release_type.value.replace("_", " ").title(),
            detail_lines=(
                (
                    f"{_product_name(product_by_id, release.product_id) or 'unknown'} | "
                    f"{release.status.value} | scheduled t{release.scheduled_turn}"
                ),
                (f"progress {release.progress}/{release.required_progress} | risk {release.risk}"),
            ),
            tone="danger" if release.risk >= 65 else "info",
            payload=release.id.hex,
            actions=(
                DeepDiveActionViewModel(
                    "work_release",
                    "Work Release",
                    "Spend execution time here.",
                    "success",
                ),
            ),
        )
        for release in state.product_releases
    ) or (
        _placeholder_item(
            "No Planned Releases",
            "Plan a release before trying to spend delivery work.",
            tone="warning",
        ),
    )
    project_items = tuple(
        DeepDiveInspectorItemViewModel(
            title=project.project_type.value.replace("_", " ").title(),
            detail_lines=(
                (
                    f"{project.status.value} | "
                    f"{_product_name(product_by_id, project.target_product_id) or 'company-wide'}"
                ),
                (
                    f"progress {project.progress}/{project.required_progress} | "
                    f"deadline t{project.deadline_turn}"
                ),
            ),
            tone="danger" if project.delivery_risk >= 65 else "warning",
            payload=project.id.hex,
            actions=(
                DeepDiveActionViewModel(
                    "work_roadmap_project",
                    "Work Project",
                    "Advance this roadmap project.",
                    "warning",
                ),
            ),
        )
        for project in state.roadmap_projects
    ) or (
        _placeholder_item(
            "No Roadmap Projects",
            "Start a roadmap project before trying to work one.",
        ),
    )
    candidate_items = tuple(
        DeepDiveInspectorItemViewModel(
            title=candidate.full_name,
            detail_lines=(
                (
                    f"{candidate.stage.value} | {candidate.role.value.replace('_', ' ')} | "
                    f"{candidate.seniority.value}"
                ),
                (
                    f"salary {format_money(candidate.salary_expectation)} | "
                    f"score {candidate.interview_score} | accept {candidate.acceptance_chance}"
                ),
            ),
            tone="warning" if candidate.stage.value == "interviewed" else "info",
            payload=candidate.id.hex,
            actions=tuple(
                action
                for action in (
                    DeepDiveActionViewModel(
                        "screen_candidate",
                        "Screen",
                        "Screen this sourced candidate.",
                        "info",
                    )
                    if candidate.stage.value == "sourced"
                    else None,
                    DeepDiveActionViewModel(
                        "interview_candidate",
                        "Interview",
                        "Interview this screened candidate.",
                        "warning",
                    )
                    if candidate.stage.value == "screened"
                    else None,
                    DeepDiveActionViewModel(
                        "make_hiring_offer",
                        "Offer",
                        "Make the offer now.",
                        "success",
                    )
                    if candidate.stage.value == "interviewed"
                    else None,
                )
                if action is not None
            ),
        )
        for candidate in state.hiring_candidates
    ) or (
        _placeholder_item(
            "No Candidates",
            "Source candidates before the funnel can move forward.",
            tone="warning",
        ),
    )
    return (
        DeepDiveInspectorSectionViewModel(
            key="deals",
            title="Sales Deals",
            tone="info",
            items=deal_items,
        ),
        DeepDiveInspectorSectionViewModel(
            key="releases",
            title="Releases",
            tone="warning",
            items=release_items,
        ),
        DeepDiveInspectorSectionViewModel(
            key="projects",
            title="Roadmap Projects",
            tone="warning",
            items=project_items,
        ),
        DeepDiveInspectorSectionViewModel(
            key="candidates",
            title="Candidates",
            tone="info",
            items=candidate_items,
        ),
    )


def _build_report_inspectors(state: GameState) -> tuple[DeepDiveInspectorSectionViewModel, ...]:
    decision_pattern = build_decision_pattern(state.decision_history)
    pattern_items = (
        DeepDiveInspectorItemViewModel(
            title=decision_pattern.style_label,
            detail_lines=(
                decision_pattern.diversity_line,
                decision_pattern.family_mix_line,
                decision_pattern.repetition_line,
            ),
            tone="warning" if decision_pattern.repetition_watch else "info",
            actions=(
                DeepDiveActionViewModel(
                    "view_report",
                    "Report",
                    "Refresh the decision pattern and full run reporting.",
                    "info",
                ),
            ),
        ),
    )
    decision_items = tuple(
        DeepDiveInspectorItemViewModel(
            title=f"Turn {entry.turn} | {entry.label}",
            detail_lines=(entry.impact_summary, entry.summary, entry.timing),
            tone=(
                "warning" if entry.family in {"Finance", "Board / Exit", "Operations"} else "info"
            ),
            actions=(
                DeepDiveActionViewModel(
                    "view_report",
                    "Report",
                    "Refresh the decision ledger and full run reporting.",
                    "info",
                ),
            ),
        )
        for entry in reversed(state.decision_history)
    ) or (
        _placeholder_item(
            "No Decisions Yet",
            "Take a state-changing action to record its impact and follow-on timing.",
        ),
    )
    latest_turn_items = tuple(
        DeepDiveInspectorItemViewModel(
            title=f"Turn {entry.turn}",
            detail_lines=(
                (
                    f"revenue {format_money(entry.total_revenue)} | "
                    f"net {format_money(entry.net_cash_flow)}"
                ),
                (
                    f"cash {format_money(entry.cash_on_hand)} | users {entry.total_users} | "
                    f"headcount {entry.headcount}"
                ),
            ),
            tone="success" if entry.net_cash_flow >= Decimal("0.00") else "warning",
            actions=(
                DeepDiveActionViewModel(
                    "view_report",
                    "Report",
                    "Refresh full run reporting.",
                    "info",
                ),
            ),
        )
        for entry in reversed(state.turn_history)
    ) or (
        _placeholder_item(
            "No Turn Ledger",
            "End at least one turn to populate report history.",
        ),
    )
    funding_items = tuple(
        DeepDiveInspectorItemViewModel(
            title=funding.funding_type.value.replace("_", " ").title(),
            detail_lines=(
                f"turn {funding.turn} | amount {format_money(funding.amount)}",
                funding.summary,
            ),
            tone="warning" if funding.funding_type.value == "loan" else "info",
            actions=(
                DeepDiveActionViewModel(
                    "review_finance",
                    "Finance",
                    "Refresh funding and cash review.",
                    "info",
                ),
            ),
        )
        for funding in reversed(state.funding_history)
    ) or (
        _placeholder_item(
            "No Funding Events",
            "Debt and equity moves will appear here once the run raises capital.",
        ),
    )
    milestone_items = tuple(
        DeepDiveInspectorItemViewModel(
            title=milestone.title,
            detail_lines=(f"turn {milestone.unlocked_turn}", milestone.reward_text),
            tone="success",
            actions=(
                DeepDiveActionViewModel(
                    "view_report",
                    "Report",
                    "Refresh milestone reporting.",
                    "info",
                ),
            ),
        )
        for milestone in reversed(state.milestone_history)
    ) or (
        _placeholder_item(
            "No Milestones Yet",
            "Growth, resilience, and portfolio milestones will collect here.",
        ),
    )
    event_items = tuple(
        DeepDiveInspectorItemViewModel(
            title=event.title,
            detail_lines=(
                f"turn {event.resolved_turn} | {event.selected_option_label}",
                event.result_text,
            ),
            tone="warning" if event.category.value == "reputation" else "info",
            actions=(
                DeepDiveActionViewModel(
                    "view_report",
                    "Report",
                    "Refresh event and run reporting.",
                    "info",
                ),
            ),
        )
        for event in reversed(state.event_history)
    ) or (
        _placeholder_item(
            "No Event History",
            "Resolved events will show their last outcome here.",
        ),
    )
    return (
        DeepDiveInspectorSectionViewModel(
            key="patterns",
            title="Decision Pattern",
            tone="warning" if decision_pattern.repetition_watch else "info",
            items=pattern_items,
        ),
        DeepDiveInspectorSectionViewModel(
            key="decisions",
            title="Decision Ledger",
            tone="info",
            items=decision_items,
        ),
        DeepDiveInspectorSectionViewModel(
            key="turns",
            title="Latest Turns",
            tone="info",
            items=latest_turn_items,
        ),
        DeepDiveInspectorSectionViewModel(
            key="funding",
            title="Funding",
            tone="warning",
            items=funding_items,
        ),
        DeepDiveInspectorSectionViewModel(
            key="milestones",
            title="Milestones",
            tone="success",
            items=milestone_items,
        ),
        DeepDiveInspectorSectionViewModel(
            key="events",
            title="Events",
            tone="info",
            items=event_items,
        ),
    )


def _build_endgame_inspectors(
    state: GameState,
    *,
    readiness,
    pressure,
    evaluation,
) -> tuple[DeepDiveInspectorSectionViewModel, ...]:
    path_labels = ("IPO", "M&A", "Independence", "Reset")
    hotspot_command, hotspot_label, hotspot_detail, hotspot_tone = _endgame_hotspot_review_spec(
        pressure
    )
    review_actions = (
        (
            TurnAction.REVIEW_BOARD.value,
            "Board Review",
            "Refresh governance and enterprise proof.",
        ),
        (
            TurnAction.REVIEW_PARTNERSHIPS.value,
            "Partner Review",
            "Refresh diligence and channel concentration.",
        ),
        (
            TurnAction.REVIEW_FINANCE.value,
            "Finance Review",
            "Refresh reserve, debt, and renewal posture.",
        ),
        (
            TurnAction.REVIEW_BOARD.value,
            "Board Review",
            "Refresh reset credibility and governance controls.",
        ),
    )
    path_payloads = ("ipo", "ma", "independence", "reset")
    path_scores = (
        readiness.ipo_readiness_score,
        readiness.acquisition_interest_score,
        readiness.independence_score,
        max(0, 100 - pressure.board_reset_risk),
    )
    path_items = tuple(
        DeepDiveInspectorItemViewModel(
            title=path_labels[index],
            detail_lines=(
                pressure.path_scorecard[index],
                pressure.path_outcome_gates[index],
            ),
            tone=(
                "success"
                if "open" in pressure.path_outcome_gates[index].lower()
                else _attribute_tone(path_scores[index])
            ),
            payload=path_payloads[index],
            actions=(
                DeepDiveActionViewModel(
                    pressure.path_gate_commands[index],
                    "Gate Command",
                    pressure.path_gate_actions[index],
                    (
                        "success"
                        if "open" in pressure.path_outcome_gates[index].lower()
                        else "warning"
                    ),
                ),
                DeepDiveActionViewModel(
                    review_actions[index][0],
                    review_actions[index][1],
                    review_actions[index][2],
                    "info",
                ),
            ),
        )
        for index in range(4)
    )
    watchlist_items = tuple(
        DeepDiveInspectorItemViewModel(
            title=f"{path_labels[index]} Watch",
            detail_lines=(
                pressure.path_watchlist[index],
                pressure.path_gate_actions[index],
            ),
            tone="warning" if "blocked" in pressure.path_outcome_gates[index].lower() else "info",
            payload=path_payloads[index],
            actions=(
                DeepDiveActionViewModel(
                    pressure.path_gate_commands[index],
                    "Run Fix",
                    "Run the primary gate-unblocker for this path.",
                    "warning"
                    if "blocked" in pressure.path_outcome_gates[index].lower()
                    else "info",
                ),
                DeepDiveActionViewModel(
                    review_actions[index][0],
                    review_actions[index][1],
                    review_actions[index][2],
                    "info",
                ),
            ),
        )
        for index in range(4)
    )
    projection_items = (
        DeepDiveInspectorItemViewModel(
            title=evaluation.title,
            detail_lines=(
                (
                    f"{evaluation.ending_variant} | grade {evaluation.grade} | "
                    f"offer {format_money(evaluation.offer_value)}"
                ),
                f"Next chapter: {evaluation.next_chapter}",
                f"Tags: {', '.join(evaluation.outcome_tags)}",
            ),
            tone=_attribute_tone(max(path_scores[:3])),
            payload="projection",
            actions=(
                DeepDiveActionViewModel(
                    TurnAction.VIEW_REPORT.value,
                    "Full Report",
                    "Open the full scorecard and archive-facing report.",
                    "info",
                ),
                DeepDiveActionViewModel(
                    pressure.path_gate_command_alert,
                    "Next Command",
                    "Run the top late-game unblocker across all exit paths.",
                    "warning",
                ),
            ),
        ),
        DeepDiveInspectorItemViewModel(
            title="Pressure Profile",
            detail_lines=(
                f"{pressure.summary}",
                (
                    f"Dominant {pressure.dominant_pressure.replace('_', ' ')} | "
                    f"clarity {pressure.strategic_clarity} | durability "
                    f"{pressure.operating_durability}"
                ),
                pressure.recommendation,
            ),
            tone=(
                "danger"
                if pressure.board_reset_risk >= 70
                else "warning"
                if pressure.board_reset_risk >= 50
                else "info"
            ),
            payload="pressure",
            actions=(
                DeepDiveActionViewModel(
                    pressure.path_gate_command_alert,
                    "Gate Command",
                    pressure.path_gate_alert,
                    "warning",
                ),
                DeepDiveActionViewModel(
                    hotspot_command,
                    "Hotspot Review",
                    hotspot_detail,
                    hotspot_tone,
                ),
            ),
        ),
        DeepDiveInspectorItemViewModel(
            title="Cockpit Route",
            detail_lines=(
                (
                    f"Hotspot {hotspot_label.lower()} | next "
                    f"{get_action_label(pressure.path_gate_command_alert)}"
                ),
                pressure.path_gate_alert,
                pressure.recommendation,
            ),
            tone=hotspot_tone,
            payload="cockpit",
            actions=(
                DeepDiveActionViewModel(
                    pressure.path_gate_command_alert,
                    "Run Gate Command",
                    "Launch the current late-game unblocker from the cockpit.",
                    "warning",
                ),
                DeepDiveActionViewModel(
                    hotspot_command,
                    "Review Hotspot",
                    hotspot_detail,
                    hotspot_tone,
                ),
            ),
        ),
    )
    _ = state
    return (
        DeepDiveInspectorSectionViewModel(
            key="paths",
            title="Exit Paths",
            tone="info",
            items=path_items,
        ),
        DeepDiveInspectorSectionViewModel(
            key="watchlist",
            title="Path Watchlist",
            tone="warning",
            items=watchlist_items,
        ),
        DeepDiveInspectorSectionViewModel(
            key="projection",
            title="Projection",
            tone="info",
            items=projection_items,
        ),
    )


def _placeholder_item(
    title: str,
    detail: str,
    *,
    tone: str = "info",
) -> DeepDiveInspectorItemViewModel:
    return DeepDiveInspectorItemViewModel(
        title=title,
        detail_lines=(detail,),
        tone=tone,
    )


def _product_name(product_by_id: dict, product_id) -> str | None:
    if product_id is None:
        return None
    product = product_by_id.get(product_id)
    return product.name if product is not None else None


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
    if runway_metric.projected == "cashflow+":
        return 1.0
    match = re.search(r"(\d+)", runway_metric.projected)
    runway = int(match.group(1)) if match is not None else None
    if runway is None:
        return 0.15
    return max(0.0, min(1.0, runway / 8))


def _preview_tone(warning_level: str) -> str:
    if warning_level in {"blocked", "critical", "high"}:
        return "danger"
    if warning_level in {"elevated", "warning"}:
        return "warning"
    return "success"


def _recommendation_urgency_label(urgency: int, horizon_turns: int) -> str:
    if urgency >= 85:
        priority = "Act now"
    elif urgency >= 65:
        priority = "This turn"
    elif urgency >= 45:
        priority = "Plan next"
    else:
        priority = "Monitor"
    turn_label = "turn" if horizon_turns == 1 else "turns"
    return f"{priority} / {horizon_turns} {turn_label}"


def _build_decision_brief(rhythm: StrategicRhythm) -> DecisionBriefViewModel:
    return DecisionBriefViewModel(
        objective_label=rhythm.objective_label,
        objective=rhythm.objective,
        plan_label=rhythm.plan_label,
        plan_progress_label=rhythm.plan_progress_label,
        plan_detail=rhythm.plan_detail,
        plan_progress=rhythm.plan_progress,
        plan_tone=rhythm.plan_tone,
        command=rhythm.command,
        command_label=rhythm.command_label,
        command_effect=rhythm.command_effect,
        command_source=rhythm.command_source,
        command_detail=rhythm.command_detail,
        command_consequence=rhythm.command_consequence,
        urgency_label=rhythm.urgency_label,
        end_turn_label=rhythm.end_turn_label,
        end_turn_detail=rhythm.end_turn_detail,
        end_turn_tone=rhythm.end_turn_tone,
        end_turn_enabled=rhythm.end_turn_enabled,
        later_label=rhythm.later_label,
        later_detail=rhythm.later_detail,
    )


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
