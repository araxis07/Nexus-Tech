"""Deterministic batch simulation helpers for tuning and regression checks."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import (
    BudgetStance,
    CampaignGoalId,
    CompanyStrategy,
    DifficultyMode,
    EmployeeRole,
    GameState,
    MarketSegment,
    PricingTier,
    Product,
    RoadmapFocus,
    Seniority,
    TurnAction,
)
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.engine import ActionContext, apply_action, create_new_game, resolve_turn
from nexus_tech.simulation.events import resolve_pending_event
from nexus_tech.simulation.operations import calculate_operations_summary
from nexus_tech.simulation.planning import is_quarter_plan_due
from nexus_tech.simulation.randomness import RandomSource
from nexus_tech.simulation.reporting import calculate_run_score
from nexus_tech.simulation.scenarios import get_available_product_templates


@dataclass(frozen=True)
class BalanceRunResult:
    """One deterministic autoplayer result."""

    seed: int
    turns_played: int
    game_over: bool
    victory_achieved: bool
    final_cash: Decimal
    total_users: int
    active_products: int
    run_score: int


@dataclass(frozen=True)
class BalanceBatchResult:
    """Aggregate view over multiple autoplayer runs."""

    scenario_id: str
    difficulty_mode: DifficultyMode
    campaign_goal_id: CampaignGoalId
    runs: int
    turns: int
    seed_base: int
    results: tuple[BalanceRunResult, ...]

    @property
    def victories(self) -> int:
        return sum(1 for result in self.results if result.victory_achieved)

    @property
    def shutdowns(self) -> int:
        return sum(1 for result in self.results if result.game_over)

    @property
    def average_turns(self) -> float:
        return sum(result.turns_played for result in self.results) / max(1, len(self.results))

    @property
    def average_score(self) -> float:
        return sum(result.run_score for result in self.results) / max(1, len(self.results))

    @property
    def average_cash(self) -> Decimal:
        if not self.results:
            return Decimal("0.00")
        total = sum((result.final_cash for result in self.results), Decimal("0.00"))
        return total / Decimal(len(self.results))

    @property
    def average_users(self) -> float:
        return sum(result.total_users for result in self.results) / max(1, len(self.results))


@dataclass(frozen=True)
class BalanceScenarioComparison:
    """One scenario summary inside a cross-scenario comparison."""

    scenario_id: str
    average_score: float
    average_cash: Decimal
    average_users: float
    victories: int
    shutdowns: int


@dataclass(frozen=True)
class BalanceComparisonResult:
    """Deterministic comparison across multiple scenarios."""

    difficulty_mode: DifficultyMode
    campaign_goal_id: CampaignGoalId
    runs: int
    turns: int
    seed_base: int
    comparisons: tuple[BalanceScenarioComparison, ...]


@dataclass(frozen=True)
class BalanceMatrixCell:
    """One scenario/difficulty aggregate inside a balance matrix run."""

    scenario_id: str
    difficulty_mode: DifficultyMode
    average_score: float
    average_cash: Decimal
    average_users: float
    victories: int
    shutdowns: int


@dataclass(frozen=True)
class BalanceMatrixResult:
    """Deterministic scenario-versus-difficulty comparison grid."""

    campaign_goal_id: CampaignGoalId
    runs: int
    turns: int
    seed_base: int
    cells: tuple[BalanceMatrixCell, ...]


@dataclass(frozen=True)
class BalanceAuditFinding:
    """One tuning warning surfaced from a balance audit pass."""

    severity: str
    scenario_id: str
    difficulty_mode: DifficultyMode
    summary: str
    average_score: float
    average_cash: Decimal
    shutdowns: int
    victories: int


@dataclass(frozen=True)
class BalanceAuditResult:
    """Actionable findings generated from a deterministic balance sweep."""

    campaign_goal_id: CampaignGoalId
    runs: int
    turns: int
    seed_base: int
    findings: tuple[BalanceAuditFinding, ...]


def run_balance_batch(
    *,
    scenario_id: str,
    difficulty_mode: DifficultyMode,
    campaign_goal_id: CampaignGoalId,
    runs: int,
    turns: int,
    seed_base: int,
) -> BalanceBatchResult:
    """Run a batch of deterministic autoplayer simulations."""

    results: list[BalanceRunResult] = []
    for offset in range(runs):
        seed = seed_base + offset
        rng = RandomSource(seed=seed)
        state = create_new_game(
            scenario_id=scenario_id,
            difficulty_mode=difficulty_mode,
            campaign_goal_id=campaign_goal_id,
        )
        state = run_autoplay(state, rng, max_turns=turns)
        run_score = calculate_run_score(state)
        total_users = sum(product.user_count for product in state.products if product.is_active)
        active_products = sum(1 for product in state.products if product.is_active)
        results.append(
            BalanceRunResult(
                seed=seed,
                turns_played=state.company.current_turn,
                game_over=state.company.game_over,
                victory_achieved=state.victory_achieved,
                final_cash=state.company.cash_on_hand,
                total_users=total_users,
                active_products=active_products,
                run_score=run_score.total_score,
            )
        )
    return BalanceBatchResult(
        scenario_id=scenario_id,
        difficulty_mode=difficulty_mode,
        campaign_goal_id=campaign_goal_id,
        runs=runs,
        turns=turns,
        seed_base=seed_base,
        results=tuple(results),
    )


def run_autoplay(state: GameState, rng: RandomSource, *, max_turns: int) -> GameState:
    """Advance one run using simple deterministic heuristics."""

    while (
        not state.company.game_over
        and not state.victory_achieved
        and state.company.current_turn <= max_turns
    ):
        if state.pending_event is not None:
            state = _resolve_pending_event_with_policy(state)

        while state.action_points_remaining > 0:
            planned_action = _choose_action(state)
            outcome = apply_action(state, planned_action.action, context=planned_action.context)
            state = outcome.state
            if state.pending_event is not None:
                state = _resolve_pending_event_with_policy(state)
            if outcome.turn_should_end:
                break

        if state.company.game_over or state.victory_achieved:
            break
        state = resolve_turn(state, rng).state

    return state


def run_balance_comparison(
    *,
    scenario_ids: list[str],
    difficulty_mode: DifficultyMode,
    campaign_goal_id: CampaignGoalId,
    runs: int,
    turns: int,
    seed_base: int,
) -> BalanceComparisonResult:
    """Run one deterministic balance batch per scenario for side-by-side comparison."""

    comparisons: list[BalanceScenarioComparison] = []
    for index, scenario_id in enumerate(scenario_ids):
        batch = run_balance_batch(
            scenario_id=scenario_id,
            difficulty_mode=difficulty_mode,
            campaign_goal_id=campaign_goal_id,
            runs=runs,
            turns=turns,
            seed_base=seed_base + (index * max(1, runs) * 100),
        )
        comparisons.append(
            BalanceScenarioComparison(
                scenario_id=scenario_id,
                average_score=batch.average_score,
                average_cash=batch.average_cash,
                average_users=batch.average_users,
                victories=batch.victories,
                shutdowns=batch.shutdowns,
            )
        )
    comparisons.sort(
        key=lambda comparison: (
            comparison.average_score,
            float(comparison.average_cash),
            comparison.average_users,
        ),
        reverse=True,
    )
    return BalanceComparisonResult(
        difficulty_mode=difficulty_mode,
        campaign_goal_id=campaign_goal_id,
        runs=runs,
        turns=turns,
        seed_base=seed_base,
        comparisons=tuple(comparisons),
    )


def run_balance_matrix(
    *,
    scenario_ids: list[str],
    campaign_goal_id: CampaignGoalId,
    runs: int,
    turns: int,
    seed_base: int,
) -> BalanceMatrixResult:
    """Run deterministic comparisons across scenarios and all difficulty modes."""

    cells: list[BalanceMatrixCell] = []
    seed_offset = 0
    for scenario_id in scenario_ids:
        for difficulty_mode in DifficultyMode:
            batch = run_balance_batch(
                scenario_id=scenario_id,
                difficulty_mode=difficulty_mode,
                campaign_goal_id=campaign_goal_id,
                runs=runs,
                turns=turns,
                seed_base=seed_base + seed_offset,
            )
            seed_offset += max(1, runs) * 100
            cells.append(
                BalanceMatrixCell(
                    scenario_id=scenario_id,
                    difficulty_mode=difficulty_mode,
                    average_score=batch.average_score,
                    average_cash=batch.average_cash,
                    average_users=batch.average_users,
                    victories=batch.victories,
                    shutdowns=batch.shutdowns,
                )
            )
    cells.sort(key=lambda cell: (cell.scenario_id, cell.difficulty_mode.value))
    return BalanceMatrixResult(
        campaign_goal_id=campaign_goal_id,
        runs=runs,
        turns=turns,
        seed_base=seed_base,
        cells=tuple(cells),
    )


def run_balance_audit(
    *,
    scenario_ids: list[str],
    campaign_goal_id: CampaignGoalId,
    runs: int,
    turns: int,
    seed_base: int,
) -> BalanceAuditResult:
    """Generate actionable tuning findings across scenarios and difficulties."""

    matrix = run_balance_matrix(
        scenario_ids=scenario_ids,
        campaign_goal_id=campaign_goal_id,
        runs=runs,
        turns=turns,
        seed_base=seed_base,
    )
    findings: list[BalanceAuditFinding] = []
    cash_warning_threshold = calculate_cash_warning_threshold(turns)
    for cell in matrix.cells:
        if cell.shutdowns >= runs:
            findings.append(
                BalanceAuditFinding(
                    severity="high",
                    scenario_id=cell.scenario_id,
                    difficulty_mode=cell.difficulty_mode,
                    summary="Every audited run shut down before stabilizing.",
                    average_score=cell.average_score,
                    average_cash=cell.average_cash,
                    shutdowns=cell.shutdowns,
                    victories=cell.victories,
                )
            )
            continue
        if cell.shutdowns >= max(1, runs // 2):
            findings.append(
                BalanceAuditFinding(
                    severity="medium",
                    scenario_id=cell.scenario_id,
                    difficulty_mode=cell.difficulty_mode,
                    summary="Shutdowns are common enough that the opening may be too punishing.",
                    average_score=cell.average_score,
                    average_cash=cell.average_cash,
                    shutdowns=cell.shutdowns,
                    victories=cell.victories,
                )
            )
        elif cell.average_cash < cash_warning_threshold:
            findings.append(
                BalanceAuditFinding(
                    severity="low",
                    scenario_id=cell.scenario_id,
                    difficulty_mode=cell.difficulty_mode,
                    summary="Average closing cash is thin and leaves little strategic room.",
                    average_score=cell.average_score,
                    average_cash=cell.average_cash,
                    shutdowns=cell.shutdowns,
                    victories=cell.victories,
                )
            )

    findings.sort(
        key=lambda finding: (
            {"high": 0, "medium": 1, "low": 2}[finding.severity],
            finding.scenario_id,
            finding.difficulty_mode.value,
        )
    )
    return BalanceAuditResult(
        campaign_goal_id=campaign_goal_id,
        runs=runs,
        turns=turns,
        seed_base=seed_base,
        findings=tuple(findings),
    )


def calculate_cash_warning_threshold(turns: int) -> Decimal:
    """Return a cash-warning threshold scaled to audit horizon length."""

    scaled_buffer = BALANCE.base_operating_cost * Decimal(max(1, turns // 3))
    default_buffer = BALANCE.finance_pressure_relief_cash_threshold / Decimal("2")
    return min(default_buffer, scaled_buffer)


def format_balance_matrix_csv(matrix: BalanceMatrixResult) -> str:
    """Serialize a balance matrix to CSV for external tuning review."""

    lines = ["scenario_id,difficulty,average_score,average_cash,average_users,victories,shutdowns"]
    for cell in matrix.cells:
        lines.append(
            ",".join(
                [
                    cell.scenario_id,
                    cell.difficulty_mode.value,
                    f"{cell.average_score:.1f}",
                    str(cell.average_cash),
                    f"{cell.average_users:.1f}",
                    str(cell.victories),
                    str(cell.shutdowns),
                ]
            )
        )
    return "\n".join(lines) + "\n"


def format_balance_report_markdown(
    matrix: BalanceMatrixResult,
    audit: BalanceAuditResult,
) -> str:
    """Serialize balance matrix and audit findings as a compact Markdown report."""

    lines = [
        "# NEXUS TECH Balance Report",
        "",
        f"- Campaign goal: `{matrix.campaign_goal_id.value}`",
        f"- Runs per cell: `{matrix.runs}`",
        f"- Max turns: `{matrix.turns}`",
        f"- Seed base: `{matrix.seed_base}`",
        f"- Matrix cells: `{len(matrix.cells)}`",
        f"- Audit findings: `{len(audit.findings)}`",
        "",
        "## Matrix",
        "",
        "| Scenario | Difficulty | Avg Score | Avg Cash | Avg Users | Victories | Shutdowns |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for cell in matrix.cells:
        lines.append(
            "| "
            f"{cell.scenario_id} | "
            f"{cell.difficulty_mode.value} | "
            f"{cell.average_score:.1f} | "
            f"{cell.average_cash} | "
            f"{cell.average_users:.1f} | "
            f"{cell.victories} | "
            f"{cell.shutdowns} |"
        )

    lines.extend(["", "## Audit Findings", ""])
    if not audit.findings:
        lines.append("No high-signal balance risks were detected in this run.")
    else:
        lines.append(
            "| Severity | Scenario | Difficulty | Summary | Avg Score | Avg Cash | Shutdowns |"
        )
        lines.append("| --- | --- | --- | --- | ---: | ---: | ---: |")
        for finding in audit.findings:
            lines.append(
                "| "
                f"{finding.severity} | "
                f"{finding.scenario_id} | "
                f"{finding.difficulty_mode.value} | "
                f"{finding.summary} | "
                f"{finding.average_score:.1f} | "
                f"{finding.average_cash} | "
                f"{finding.shutdowns} |"
            )

    lines.extend(["", "## Tuning Priorities", ""])
    if not audit.findings:
        lines.append(
            "- No audit hotspots were detected. Re-run this report after changing events, "
            "constants, or scenario content."
        )
    else:
        critical_count = sum(1 for finding in audit.findings if finding.severity == "critical")
        high_count = sum(1 for finding in audit.findings if finding.severity == "high")
        lines.append(f"- Critical findings: `{critical_count}`")
        lines.append(f"- High findings: `{high_count}`")
        lines.append("- Highest-signal cells to retest next:")
        for finding in audit.findings[:3]:
            lines.append(
                f"  - `{finding.scenario_id}` on `{finding.difficulty_mode.value}`: "
                f"{finding.summary}"
            )

    lines.extend(
        [
            "",
            "## Reading The Report",
            "",
            "- Builder should be survivable with room for experimentation.",
            "- Standard should reward disciplined play without requiring perfect choices.",
            "- Founder should create visible pressure without making most openings impossible.",
            "- Re-run this report after changing constants, events, or scenario content.",
        ]
    )
    return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class PlannedAction:
    action: TurnAction
    context: ActionContext


def _choose_action(state: GameState) -> PlannedAction:
    active_products = [product for product in state.products if product.is_active]
    if not active_products:
        return PlannedAction(TurnAction.WAIT, ActionContext())

    if state.pending_event is not None:
        return PlannedAction(TurnAction.VIEW_STATUS, ActionContext())

    if not state.employees and state.company.cash_on_hand >= BALANCE.finance_loan_amount:
        return PlannedAction(
            TurnAction.HIRE_EMPLOYEE,
            ActionContext(
                hire_full_name=f"Autohire {state.company.current_turn}",
                hire_role=EmployeeRole.ENGINEER,
                hire_seniority=Seniority.MID,
                hire_specialization="platform",
            ),
        )

    unassigned_employee = next(
        (employee for employee in state.employees if employee.assigned_product_id is None),
        None,
    )
    if unassigned_employee is not None:
        target = _pick_primary_product(state)
        return PlannedAction(
            TurnAction.ASSIGN_EMPLOYEE,
            ActionContext(
                employee_id=unassigned_employee.id,
                target_product_id=target.id,
            ),
        )

    if is_quarter_plan_due(state):
        return PlannedAction(
            TurnAction.SET_BUDGET_STANCE,
            ActionContext(budget_stance=_choose_budget_stance(state)),
        )

    if state.company.current_turn >= state.roadmap_set_turn + 4:
        return PlannedAction(
            TurnAction.SET_ROADMAP,
            ActionContext(roadmap_focus=_choose_roadmap_focus(state)),
        )

    if (
        state.company.cash_on_hand <= BALANCE.event_investor_cash_threshold
        and state.finance.debt_principal < BALANCE.finance_max_total_debt
    ):
        return PlannedAction(TurnAction.TAKE_LOAN, ActionContext())

    if (
        state.finance.debt_principal > 0
        and state.company.cash_on_hand >= BALANCE.finance_repayment_min_cash_buffer * 3
    ):
        return PlannedAction(TurnAction.REPAY_DEBT, ActionContext())

    if _should_create_product(state):
        template_id = _choose_next_template_id(state)
        return PlannedAction(
            TurnAction.CREATE_PRODUCT,
            ActionContext(
                new_product_name=_build_product_name(state),
                new_product_template_id=template_id,
            ),
        )

    worst_product = _pick_worst_product(state)
    strongest_product = _pick_primary_product(state)
    operations = calculate_operations_summary(
        state.products,
        state.employees,
        current_turn=state.company.current_turn,
        customer_accounts=state.customer_accounts,
    )

    if worst_product.bug_level >= 28 or worst_product.quality <= 42:
        return PlannedAction(
            TurnAction.IMPROVE_QUALITY,
            ActionContext(target_product_id=worst_product.id),
        )
    if worst_product.technical_debt >= 42 or operations.overload >= 4:
        return PlannedAction(
            TurnAction.REDUCE_TECHNICAL_DEBT,
            ActionContext(target_product_id=worst_product.id),
        )
    if worst_product.market_fit < 44 or worst_product.feature_count < 2:
        return PlannedAction(
            TurnAction.ADD_FEATURE,
            ActionContext(target_product_id=worst_product.id),
        )
    if len(state.employees) < 4 and state.company.cash_on_hand >= BALANCE.create_product_cost * 4:
        return PlannedAction(
            TurnAction.HIRE_EMPLOYEE,
            ActionContext(
                hire_full_name=f"Autohire {len(state.employees) + state.company.current_turn}",
                hire_role=_choose_hire_role(state),
                hire_seniority=Seniority.MID,
                hire_specialization="generalist",
            ),
        )
    target_pricing_tier = _choose_pricing_tier(strongest_product)
    if target_pricing_tier is not strongest_product.pricing_tier:
        return PlannedAction(
            TurnAction.ADJUST_PRICING,
            ActionContext(
                target_product_id=strongest_product.id,
                pricing_tier=target_pricing_tier,
            ),
        )
    if (
        strongest_product.target_segment is MarketSegment.STARTUP
        and strongest_product.quality >= 64
    ):
        return PlannedAction(
            TurnAction.SET_TARGET_SEGMENT,
            ActionContext(
                target_product_id=strongest_product.id,
                target_segment=MarketSegment.SMB,
            ),
        )
    if state.company.strategy is CompanyStrategy.BALANCED and state.company.current_turn >= 5:
        return PlannedAction(
            TurnAction.SET_COMPANY_STRATEGY,
            ActionContext(strategy=_choose_company_strategy(state)),
        )
    return PlannedAction(
        TurnAction.MARKET_PRODUCT,
        ActionContext(target_product_id=strongest_product.id),
    )


def _resolve_pending_event_with_policy(state: GameState) -> GameState:
    event = state.pending_event
    if event is None:
        return state

    if event.event_id == "severe_bug_incident":
        option_id = (
            "hotfix" if state.company.cash_on_hand > BALANCE.event_bug_hotfix_cost else "delay"
        )
    elif event.event_id == "favorable_market_trend":
        option_id = (
            "lean_in"
            if state.company.cash_on_hand > BALANCE.event_market_trend_invest_cost * 2
            else "bank_it"
        )
    elif event.event_id == "investor_outreach":
        option_id = (
            "take_capital"
            if state.company.cash_on_hand <= BALANCE.event_investor_cash_threshold
            else "stay_bootstrapped"
        )
    elif event.event_id == "team_burnout_spike":
        option_id = (
            "cool_off"
            if state.company.cash_on_hand > BALANCE.event_burnout_relief_cost * 2
            else "push_through"
        )
    elif event.event_id == "competitor_pressure":
        option_id = (
            "differentiate"
            if any(product.quality >= 58 for product in state.products if product.is_active)
            else "rush_countermove"
        )
    elif event.event_id == "referral_wave":
        option_id = (
            "staff_referrals"
            if state.company.cash_on_hand > BALANCE.event_referral_support_cost * 2
            else "protect_service"
        )
    elif event.event_id == "compliance_review":
        option_id = (
            "fund_review"
            if state.company.cash_on_hand > BALANCE.event_compliance_fund_cost * 2
            else "defer_review"
        )
    elif event.event_id == "support_backlog":
        option_id = (
            "stabilize_ops"
            if state.company.cash_on_hand > BALANCE.event_support_backlog_fix_cost * 2
            else "keep_shipping"
        )
    elif event.event_id == "board_scrutiny":
        option_id = (
            "publish_plan"
            if state.company.cash_on_hand > BALANCE.event_board_scrutiny_plan_cost * 2
            else "promise_growth"
        )
    elif event.event_id == "renewal_risk":
        option_id = (
            "stabilize_renewals"
            if state.company.cash_on_hand > BALANCE.event_renewal_stabilize_cost * 2
            else "offer_discounts"
        )
    elif event.event_id == "partner_offer":
        option_id = (
            "sign_partner"
            if state.company.cash_on_hand < BALANCE.cash_reserve_milestone_threshold
            else "stay_direct"
        )
    elif event.event_id == "talent_bidding_war":
        option_id = (
            "retain_team"
            if state.company.cash_on_hand > BALANCE.event_talent_bidding_war_retain_cost * 2
            else "hold_line"
        )
    elif event.event_id == "platform_breakthrough":
        option_id = (
            "productize_breakthrough"
            if state.company.cash_on_hand > BALANCE.event_platform_breakthrough_productize_cost * 2
            else "bank_the_gain"
        )
    elif event.event_id == "loan_covenant":
        option_id = (
            "paydown_now"
            if state.company.cash_on_hand > BALANCE.event_loan_covenant_paydown_amount * 2
            else "renegotiate_terms"
        )
    elif event.event_id == "down_round_pressure":
        option_id = (
            "take_bridge"
            if state.company.cash_on_hand <= BALANCE.event_down_round_pressure_cash_threshold
            else "stay_independent"
        )
    elif event.event_id == "key_account_expansion":
        option_id = (
            "build_success_plan"
            if state.company.cash_on_hand > BALANCE.event_key_account_success_plan_cost * 2
            else "ask_for_referral"
        )
    elif event.event_id == "security_audit":
        option_id = (
            "fund_audit"
            if state.company.cash_on_hand > BALANCE.event_security_audit_fund_cost * 2
            else "defer_audit"
        )
    elif event.event_id == "enterprise_sales_cycle":
        option_id = (
            "fund_poc"
            if state.company.cash_on_hand > BALANCE.event_enterprise_poc_cost * 2
            else "walk_away"
        )
    elif event.event_id == "product_launch_window":
        option_id = (
            "launch_campaign"
            if state.company.cash_on_hand > BALANCE.event_product_launch_campaign_cost * 2
            else "soft_launch"
        )
    elif event.event_id == "platform_outage":
        option_id = (
            "all_hands_recovery"
            if state.company.cash_on_hand > BALANCE.event_platform_outage_response_cost * 2
            else "minimize_cost"
        )
    elif event.event_id == "competitor_acquisition":
        option_id = (
            "differentiate_against_stack"
            if state.company.cash_on_hand
            > BALANCE.event_competitor_acquisition_differentiate_cost * 2
            else "seek_distribution_partner"
        )
    elif event.event_id == "regulatory_shift":
        option_id = (
            "proactive_controls"
            if state.company.cash_on_hand > BALANCE.event_regulatory_shift_cost * 2
            else "wait_for_clarity"
        )
    elif event.event_id == "audit_followup_review":
        option_id = (
            "package_evidence"
            if state.company.cash_on_hand > BALANCE.event_audit_followup_cost * 2
            else "defer_followup"
        )
    elif event.event_id == "launch_aftershock":
        option_id = (
            "stabilize_experience"
            if state.company.cash_on_hand > BALANCE.event_launch_aftershock_stabilize_cost * 2
            else "chase_second_wave"
        )
    elif event.event_id == "enterprise_procurement_delay":
        option_id = (
            "fund_proof"
            if state.company.cash_on_hand > BALANCE.event_procurement_delay_proof_cost * 2
            else "wait_out_process"
        )
    else:
        option_id = event.options[0].id

    return resolve_pending_event(state, option_id).state


def _pick_worst_product(state: GameState) -> Product:
    active_products = [product for product in state.products if product.is_active]
    return max(
        active_products,
        key=lambda product: (
            product.bug_level + product.technical_debt - product.quality - product.market_fit,
            product.user_count,
        ),
    )


def _pick_primary_product(state: GameState) -> Product:
    active_products = [product for product in state.products if product.is_active]
    return max(
        active_products,
        key=lambda product: (
            product.user_count + product.market_fit + product.quality,
            -product.bug_level,
        ),
    )


def _choose_hire_role(state: GameState) -> EmployeeRole:
    role_counts = {role: 0 for role in EmployeeRole}
    for employee in state.employees:
        role_counts[employee.role] += 1
    if role_counts[EmployeeRole.ENGINEER] == 0:
        return EmployeeRole.ENGINEER
    if role_counts[EmployeeRole.MARKETER] == 0:
        return EmployeeRole.MARKETER
    if (
        len([product for product in state.products if product.is_active]) >= 2
        and role_counts[EmployeeRole.PRODUCT_MANAGER] == 0
    ):
        return EmployeeRole.PRODUCT_MANAGER
    if role_counts[EmployeeRole.DESIGNER] == 0:
        return EmployeeRole.DESIGNER
    return EmployeeRole.ENGINEER


def _should_create_product(state: GameState) -> bool:
    active_products = sum(1 for product in state.products if product.is_active)
    return (
        state.company.current_turn >= 4
        and active_products < 3
        and state.company.cash_on_hand >= BALANCE.create_product_cost * 3
    )


def _choose_next_template_id(state: GameState) -> str:
    existing_segments = {product.target_segment for product in state.products if product.is_active}
    templates = list(get_available_product_templates())
    for preferred_segment in (
        MarketSegment.SMB,
        MarketSegment.ENTERPRISE,
        MarketSegment.STARTUP,
        MarketSegment.INDIE,
    ):
        if preferred_segment in existing_segments:
            continue
        for template in templates:
            if template.target_segment is preferred_segment:
                return template.template_id
    return templates[0].template_id


def _build_product_name(state: GameState) -> str:
    return f"Nexus {len(state.products) + 1}"


def _choose_budget_stance(state: GameState):
    if state.company.cash_on_hand < BALANCE.finance_pressure_relief_cash_threshold:
        return BudgetStance.LEAN
    if sum(product.user_count for product in state.products if product.is_active) > 180:
        return BudgetStance.AGGRESSIVE
    return BudgetStance.BALANCED


def _choose_roadmap_focus(state: GameState) -> RoadmapFocus:
    worst_product = _pick_worst_product(state)
    if any(
        product.target_segment is MarketSegment.ENTERPRISE and product.market_fit >= 56
        for product in state.products
        if product.is_active
    ):
        return RoadmapFocus.ENTERPRISE_SALES_PUSH
    if worst_product.technical_debt >= 40:
        return RoadmapFocus.PLATFORM_REBUILD
    if any(product.target_segment is MarketSegment.ENTERPRISE for product in state.products):
        return RoadmapFocus.AI_TRUST_PROGRAM
    if sum(1 for product in state.products if product.is_active) >= 3:
        return RoadmapFocus.PORTFOLIO_CONSOLIDATION
    if state.company.cash_on_hand > BALANCE.cash_reserve_milestone_threshold:
        return RoadmapFocus.GROWTH_PUSH
    if any(product.target_segment is MarketSegment.INDIE for product in state.products):
        return RoadmapFocus.COMMUNITY_GROWTH
    return RoadmapFocus.BALANCED_EXECUTION


def _choose_pricing_tier(product: Product):
    if product.target_segment is MarketSegment.ENTERPRISE:
        return PricingTier.PREMIUM
    if product.quality >= 72 and product.market_fit >= 62:
        return PricingTier.STANDARD
    return PricingTier.BUDGET


def _choose_company_strategy(state: GameState) -> CompanyStrategy:
    if state.company.cash_on_hand < BALANCE.finance_pressure_relief_cash_threshold:
        return CompanyStrategy.EFFICIENCY
    if any(product.technical_debt >= 40 for product in state.products if product.is_active):
        return CompanyStrategy.QUALITY
    return CompanyStrategy.GROWTH
