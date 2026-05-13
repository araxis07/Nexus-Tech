"""Effect application for pending business events."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from nexus_tech.domain.models import (
    CapitalPlanMode,
    CustomerAccount,
    CustomerAccountStatus,
    Employee,
    EventHistoryEntry,
    GameState,
    PartnerChannel,
    PartnershipStatus,
    PendingEvent,
    Product,
)
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.capital_planning import get_capital_plan_profile
from nexus_tech.simulation.economy import is_game_over
from nexus_tech.simulation.event_registry import get_designer_or_marketer_support
from nexus_tech.simulation.finance import apply_raise_angel
from nexus_tech.simulation.partnerships import (
    calculate_partnership_fatigue,
    create_partnership,
)
from nexus_tech.simulation.product_progression import infer_lifecycle_stage
from nexus_tech.simulation.support import clamp_int, clamp_rate


@dataclass(frozen=True)
class EventApplicationOutcome:
    """Result of applying one event option."""

    state: GameState
    history_entry: EventHistoryEntry


def apply_pending_event_choice(
    state: GameState,
    option_id: str,
) -> EventApplicationOutcome:
    """Apply one option for the currently pending event."""

    if state.pending_event is None:
        raise ValueError("There is no pending event to resolve.")

    option = next(
        (
            event_option
            for event_option in state.pending_event.options
            if event_option.id == option_id
        ),
        None,
    )
    if option is None:
        raise ValueError("Selected event option was not found.")

    next_state = state.model_copy(deep=True)
    pending_event = next_state.pending_event
    if pending_event is None:
        raise ValueError("There is no pending event to resolve.")

    handler = EVENT_EFFECT_HANDLERS.get(pending_event.event_id)
    if handler is None:
        raise ValueError(f"No handler registered for event {pending_event.event_id}.")

    result_text = handler(next_state, pending_event, option_id)
    next_state.company.game_over = is_game_over(next_state.company)
    next_state.pending_event = None
    if next_state.turn_history and next_state.turn_history[-1].turn == pending_event.triggered_turn:
        latest_entry = next_state.turn_history[-1]
        latest_entry.cash_on_hand = next_state.company.cash_on_hand
        latest_entry.reputation = next_state.company.reputation
        latest_entry.total_users = sum(product.user_count for product in next_state.products)
        latest_entry.headcount = len(next_state.employees)

    history_entry = EventHistoryEntry(
        event_id=pending_event.event_id,
        category=pending_event.category,
        title=pending_event.title,
        triggered_turn=pending_event.triggered_turn,
        resolved_turn=pending_event.triggered_turn,
        chain_id=pending_event.chain_id,
        chain_stage=pending_event.chain_stage,
        selected_option_id=option.id,
        selected_option_label=option.label,
        result_text=result_text,
    )
    next_state.event_history.append(history_entry)
    if len(next_state.event_history) > BALANCE.event_history_limit:
        next_state.event_history = next_state.event_history[-BALANCE.event_history_limit :]

    return EventApplicationOutcome(
        state=next_state,
        history_entry=history_entry,
    )


def _apply_severe_bug_incident(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)
    affected_employees = _get_assigned_employees(state, product.id)

    if option_id == "hotfix":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_bug_hotfix_cost
        )
        product.bug_level = clamp_int(
            product.bug_level - BALANCE.event_bug_hotfix_bug_reduction,
            0,
            100,
        )
        product.quality = clamp_int(
            product.quality - BALANCE.event_bug_hotfix_quality_loss,
            0,
            100,
        )
        state.company.reputation = clamp_int(
            state.company.reputation - BALANCE.event_bug_hotfix_reputation_loss,
            0,
            100,
        )
        for employee in affected_employees:
            employee.energy = clamp_int(
                employee.energy - BALANCE.event_bug_hotfix_energy_loss,
                0,
                100,
            )
            employee.morale = clamp_int(
                employee.morale - BALANCE.event_bug_hotfix_morale_loss,
                0,
                100,
            )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"Emergency patch funded for {product.name}. Cash -{BALANCE.event_bug_hotfix_cost}, "
            f"bugs -{BALANCE.event_bug_hotfix_bug_reduction}, reputation "
            f"-{BALANCE.event_bug_hotfix_reputation_loss}."
        )

    if option_id == "delay":
        user_loss = min(
            product.user_count,
            max(
                BALANCE.event_bug_delay_min_user_loss,
                product.user_count // BALANCE.event_bug_delay_user_loss_divisor,
            ),
        )
        product.bug_level = clamp_int(
            product.bug_level + BALANCE.event_bug_delay_bug_increase,
            0,
            100,
        )
        product.user_count = max(0, product.user_count - user_loss)
        state.company.reputation = clamp_int(
            state.company.reputation - BALANCE.event_bug_delay_reputation_loss,
            0,
            100,
        )
        for employee in affected_employees:
            employee.energy = clamp_int(
                employee.energy - BALANCE.event_bug_delay_energy_loss,
                0,
                100,
            )
            employee.morale = clamp_int(
                employee.morale - BALANCE.event_bug_delay_morale_loss,
                0,
                100,
            )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"{product.name} took visible damage. Users -{user_loss}, "
            f"bugs +{BALANCE.event_bug_delay_bug_increase}, reputation "
            f"-{BALANCE.event_bug_delay_reputation_loss}."
        )

    raise ValueError(f"Unsupported option {option_id} for severe bug incident.")


def _apply_favorable_market_trend(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)
    affected_employees = _get_assigned_employees(state, product.id)

    if option_id == "lean_in":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_market_trend_invest_cost
        )
        product.user_count += BALANCE.event_market_trend_big_user_gain
        product.acquisition_rate = clamp_rate(
            product.acquisition_rate + BALANCE.event_market_trend_acquisition_gain
        )
        state.company.reputation = clamp_int(
            state.company.reputation + BALANCE.event_market_trend_reputation_gain,
            0,
            100,
        )
        for employee in affected_employees:
            employee.energy = clamp_int(
                employee.energy - BALANCE.event_market_trend_energy_loss,
                0,
                100,
            )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You leaned into the market trend around {product.name}. "
            f"Cash -{BALANCE.event_market_trend_invest_cost}, users "
            f"+{BALANCE.event_market_trend_big_user_gain}."
        )

    if option_id == "bank_it":
        product.user_count += BALANCE.event_market_trend_small_user_gain
        state.company.reputation = clamp_int(
            state.company.reputation + BALANCE.event_market_trend_reputation_gain,
            0,
            100,
        )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You banked a lighter win for {product.name}. "
            f"Users +{BALANCE.event_market_trend_small_user_gain}, reputation "
            f"+{BALANCE.event_market_trend_reputation_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for favorable market trend.")


def _apply_investor_outreach(state: GameState, event: PendingEvent, option_id: str) -> str:
    del event

    if option_id == "take_capital":
        summary = apply_raise_angel(
            state.company,
            state.finance,
            state.funding_history,
            current_turn=state.company.current_turn,
            reputation=state.company.reputation,
            total_users=sum(product.user_count for product in state.products if product.is_active),
        )
        state.funding_history.append(summary.history_entry)
        state.company.reputation = clamp_int(
            state.company.reputation + BALANCE.event_investor_reputation_gain,
            0,
            100,
        )
        for employee in state.employees:
            employee.morale = clamp_int(
                employee.morale - BALANCE.event_investor_team_morale_penalty,
                0,
                100,
            )
        return (
            f"The investor round closed quickly. Cash +{BALANCE.finance_angel_raise_amount}, "
            f"reputation +{BALANCE.event_investor_reputation_gain}, team morale "
            f"-{BALANCE.event_investor_team_morale_penalty}."
        )

    if option_id == "stay_bootstrapped":
        state.company.reputation = clamp_int(
            state.company.reputation + BALANCE.event_bootstrap_reputation_gain,
            0,
            100,
        )
        for employee in state.employees:
            employee.morale = clamp_int(
                employee.morale + BALANCE.event_bootstrap_team_morale_gain,
                0,
                100,
            )
        state.finance.investor_pressure = clamp_int(
            state.finance.investor_pressure - 1,
            0,
            100,
        )
        return (
            f"You stayed bootstrapped. Reputation +{BALANCE.event_bootstrap_reputation_gain}, "
            f"team morale +{BALANCE.event_bootstrap_team_morale_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for investor outreach.")


def _apply_sudden_press_mention(state: GameState, event: PendingEvent, option_id: str) -> str:
    if option_id != "ride_the_wave":
        raise ValueError(f"Unsupported option {option_id} for sudden press mention.")

    product = _get_target_product(state, event)
    gained_users = max(
        BALANCE.event_press_min_user_gain,
        product.user_count // BALANCE.event_press_user_gain_divisor,
    )
    product.user_count += gained_users
    product.acquisition_rate = clamp_rate(
        product.acquisition_rate + BALANCE.event_press_acquisition_gain
    )
    state.company.reputation = clamp_int(
        state.company.reputation + BALANCE.event_press_reputation_gain,
        0,
        100,
    )
    for employee in get_designer_or_marketer_support(state.employees, product.id):
        employee.morale = clamp_int(
            employee.morale + BALANCE.event_press_marketer_morale_gain,
            0,
            100,
        )
    product.lifecycle_stage = infer_lifecycle_stage(product)
    return (
        f"{product.name} caught a press bump. Users +{gained_users}, reputation "
        f"+{BALANCE.event_press_reputation_gain}."
    )


def _apply_team_burnout_spike(state: GameState, event: PendingEvent, option_id: str) -> str:
    employee = _get_target_employee(state, event)

    if option_id == "cool_off":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_burnout_relief_cost
        )
        employee.energy = clamp_int(
            employee.energy + BALANCE.event_burnout_relief_energy_gain,
            0,
            100,
        )
        employee.morale = clamp_int(
            employee.morale + BALANCE.event_burnout_relief_morale_gain,
            0,
            100,
        )
        for teammate in state.employees:
            if teammate.id == employee.id:
                continue
            teammate.morale = clamp_int(
                teammate.morale + BALANCE.event_burnout_relief_team_morale_gain,
                0,
                100,
            )
        return (
            f"You funded recovery time for {employee.full_name}. Cash "
            f"-{BALANCE.event_burnout_relief_cost}, energy "
            f"+{BALANCE.event_burnout_relief_energy_gain}."
        )

    if option_id == "push_through":
        employee.energy = clamp_int(
            employee.energy - BALANCE.event_burnout_push_energy_loss,
            0,
            100,
        )
        employee.morale = clamp_int(
            employee.morale - BALANCE.event_burnout_push_morale_loss,
            0,
            100,
        )
        state.company.reputation = clamp_int(
            state.company.reputation - BALANCE.event_burnout_push_reputation_loss,
            0,
            100,
        )
        if employee.assigned_product_id is not None:
            product = _get_product_by_id(state, employee.assigned_product_id)
            product.quality = clamp_int(
                product.quality - BALANCE.event_burnout_push_quality_loss,
                0,
                100,
            )
            product.lifecycle_stage = infer_lifecycle_stage(product)
            return (
                f"You pushed {employee.full_name} through the crunch. "
                f"{product.name} quality -{BALANCE.event_burnout_push_quality_loss}, "
                f"reputation -{BALANCE.event_burnout_push_reputation_loss}."
            )
        return (
            f"You pushed {employee.full_name} through the crunch. "
            f"Reputation -{BALANCE.event_burnout_push_reputation_loss}."
        )

    raise ValueError(f"Unsupported option {option_id} for team burnout spike.")


def _apply_competitor_pressure(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)
    affected_employees = _get_assigned_employees(state, product.id)

    if option_id == "rush_countermove":
        product.feature_count += BALANCE.event_competitor_rush_feature_gain
        product.market_fit = clamp_int(
            product.market_fit + BALANCE.event_competitor_rush_market_fit_gain,
            0,
            100,
        )
        product.bug_level = clamp_int(
            product.bug_level + BALANCE.event_competitor_rush_bug_increase,
            0,
            100,
        )
        product.technical_debt = clamp_int(
            product.technical_debt + BALANCE.event_competitor_rush_debt_increase,
            0,
            100,
        )
        for employee in affected_employees:
            employee.energy = clamp_int(
                employee.energy - BALANCE.event_competitor_rush_energy_loss,
                0,
                100,
            )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You rushed a response for {product.name}. Features "
            f"+{BALANCE.event_competitor_rush_feature_gain}, bugs "
            f"+{BALANCE.event_competitor_rush_bug_increase}, debt "
            f"+{BALANCE.event_competitor_rush_debt_increase}."
        )

    if option_id == "differentiate":
        user_loss = min(product.user_count, BALANCE.event_competitor_focus_user_loss)
        product.quality = clamp_int(
            product.quality + BALANCE.event_competitor_focus_quality_gain,
            0,
            100,
        )
        product.bug_level = clamp_int(
            product.bug_level - BALANCE.event_competitor_focus_bug_reduction,
            0,
            100,
        )
        product.market_fit = clamp_int(
            product.market_fit + BALANCE.event_competitor_focus_market_fit_gain,
            0,
            100,
        )
        product.user_count = max(0, product.user_count - user_loss)
        state.company.reputation = clamp_int(
            state.company.reputation + BALANCE.event_competitor_focus_reputation_gain,
            0,
            100,
        )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You defended {product.name} with quality. Users -{user_loss}, quality "
            f"+{BALANCE.event_competitor_focus_quality_gain}, reputation "
            f"+{BALANCE.event_competitor_focus_reputation_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for competitor pressure.")


def _apply_referral_wave(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)
    support_employees = get_designer_or_marketer_support(state.employees, product.id)

    if option_id == "staff_referrals":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_referral_support_cost
        )
        product.user_count += BALANCE.event_referral_big_user_gain
        product.acquisition_rate = clamp_rate(
            product.acquisition_rate + BALANCE.event_referral_acquisition_gain
        )
        for employee in support_employees:
            employee.morale = clamp_int(
                employee.morale + BALANCE.event_referral_team_morale_gain,
                0,
                100,
            )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You staffed the referral wave around {product.name}. Cash "
            f"-{BALANCE.event_referral_support_cost}, users "
            f"+{BALANCE.event_referral_big_user_gain}."
        )

    if option_id == "protect_service":
        product.user_count += BALANCE.event_referral_small_user_gain
        product.quality = clamp_int(
            product.quality + BALANCE.event_referral_quality_gain,
            0,
            100,
        )
        product.churn_rate = clamp_rate(product.churn_rate - BALANCE.event_referral_churn_relief)
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You protected service quality for {product.name}. Users "
            f"+{BALANCE.event_referral_small_user_gain}, quality "
            f"+{BALANCE.event_referral_quality_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for referral wave.")


def _apply_compliance_review(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)

    if option_id == "fund_review":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_compliance_fund_cost
        )
        product.technical_debt = clamp_int(
            product.technical_debt - BALANCE.event_compliance_debt_reduction,
            0,
            100,
        )
        product.market_fit = clamp_int(
            product.market_fit + BALANCE.event_compliance_market_fit_gain,
            0,
            100,
        )
        state.company.reputation = clamp_int(
            state.company.reputation + BALANCE.event_compliance_reputation_gain,
            0,
            100,
        )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You funded a compliance sprint for {product.name}. Cash "
            f"-{BALANCE.event_compliance_fund_cost}, debt "
            f"-{BALANCE.event_compliance_debt_reduction}, reputation "
            f"+{BALANCE.event_compliance_reputation_gain}."
        )

    if option_id == "defer_review":
        user_loss = min(product.user_count, BALANCE.event_compliance_delay_user_loss)
        product.user_count = max(0, product.user_count - user_loss)
        state.company.reputation = clamp_int(
            state.company.reputation - BALANCE.event_compliance_delay_reputation_loss,
            0,
            100,
        )
        product.churn_rate = clamp_rate(
            product.churn_rate + BALANCE.event_compliance_delay_churn_increase
        )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You deferred the review for {product.name}. Users -{user_loss}, reputation "
            f"-{BALANCE.event_compliance_delay_reputation_loss}."
        )

    raise ValueError(f"Unsupported option {option_id} for compliance review.")


def _apply_support_backlog(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)
    affected_employees = _get_assigned_employees(state, product.id)

    if option_id == "stabilize_ops":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_support_backlog_fix_cost
        )
        product.bug_level = clamp_int(
            product.bug_level - BALANCE.event_support_backlog_fix_bug_reduction,
            0,
            100,
        )
        product.churn_rate = clamp_rate(
            product.churn_rate - BALANCE.event_support_backlog_fix_churn_relief
        )
        for employee in affected_employees:
            employee.morale = clamp_int(
                employee.morale + BALANCE.event_support_backlog_fix_morale_gain,
                0,
                100,
            )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You stabilized the support backlog for {product.name}. Cash "
            f"-{BALANCE.event_support_backlog_fix_cost}, bugs "
            f"-{BALANCE.event_support_backlog_fix_bug_reduction}."
        )

    if option_id == "keep_shipping":
        user_loss = min(product.user_count, BALANCE.event_support_backlog_push_user_loss)
        product.user_count = max(0, product.user_count - user_loss)
        product.quality = clamp_int(
            product.quality - BALANCE.event_support_backlog_push_quality_loss,
            0,
            100,
        )
        state.company.reputation = clamp_int(
            state.company.reputation - BALANCE.event_support_backlog_push_reputation_loss,
            0,
            100,
        )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"The backlog spilled into the product experience for {product.name}. Users "
            f"-{user_loss}, reputation -{BALANCE.event_support_backlog_push_reputation_loss}."
        )

    raise ValueError(f"Unsupported option {option_id} for support backlog.")


def _apply_board_scrutiny(state: GameState, event: PendingEvent, option_id: str) -> str:
    del event

    if option_id == "publish_plan":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_board_scrutiny_plan_cost
        )
        state.finance.investor_pressure = clamp_int(
            state.finance.investor_pressure - BALANCE.event_board_scrutiny_plan_pressure_relief,
            0,
            100,
        )
        state.finance.board_confidence = clamp_int(state.finance.board_confidence + 4, 0, 100)
        for employee in state.employees:
            employee.morale = clamp_int(
                employee.morale - BALANCE.event_board_scrutiny_plan_morale_loss,
                0,
                100,
            )
        return (
            "You published a disciplined operating plan. Cash "
            f"-{BALANCE.event_board_scrutiny_plan_cost}, investor pressure "
            f"-{BALANCE.event_board_scrutiny_plan_pressure_relief}."
        )

    if option_id == "promise_growth":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand + BALANCE.event_board_scrutiny_growth_cash_gain
        )
        state.finance.investor_pressure = clamp_int(
            state.finance.investor_pressure + BALANCE.event_board_scrutiny_growth_pressure_gain,
            0,
            100,
        )
        state.finance.board_confidence = clamp_int(state.finance.board_confidence - 3, 0, 100)
        for employee in state.employees:
            employee.morale = clamp_int(
                employee.morale - BALANCE.event_board_scrutiny_growth_morale_loss,
                0,
                100,
            )
        return (
            "You bought time with a stronger growth promise. Cash "
            f"+{BALANCE.event_board_scrutiny_growth_cash_gain}, investor pressure "
            f"+{BALANCE.event_board_scrutiny_growth_pressure_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for board scrutiny.")


def _apply_renewal_risk(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)

    if option_id == "stabilize_renewals":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_renewal_stabilize_cost
        )
        product.bug_level = clamp_int(
            product.bug_level - BALANCE.event_renewal_stabilize_bug_reduction,
            0,
            100,
        )
        product.market_fit = clamp_int(
            product.market_fit + BALANCE.event_renewal_stabilize_fit_gain,
            0,
            100,
        )
        state.company.reputation = clamp_int(
            state.company.reputation + BALANCE.event_renewal_stabilize_reputation_gain,
            0,
            100,
        )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You funded a renewal push for {product.name}. Cash "
            f"-{BALANCE.event_renewal_stabilize_cost}, bugs "
            f"-{BALANCE.event_renewal_stabilize_bug_reduction}, reputation "
            f"+{BALANCE.event_renewal_stabilize_reputation_gain}."
        )

    if option_id == "offer_discounts":
        product.user_count += BALANCE.event_renewal_discount_user_relief
        product.revenue_per_user = quantize_money(
            product.revenue_per_user - BALANCE.event_renewal_discount_revenue_penalty
        )
        state.company.reputation = clamp_int(
            state.company.reputation - BALANCE.event_renewal_discount_reputation_loss,
            0,
            100,
        )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You protected renewals for {product.name} with pricing. Users "
            f"+{BALANCE.event_renewal_discount_user_relief}, revenue per user "
            f"-{BALANCE.event_renewal_discount_revenue_penalty}."
        )

    raise ValueError(f"Unsupported option {option_id} for renewal risk.")


def _apply_partner_offer(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)

    if option_id == "sign_partner":
        if not any(
            partnership.product_id == product.id and partnership.channel is PartnerChannel.RESELLER
            for partnership in state.partnerships
        ):
            create_partnership(state, product.id, PartnerChannel.RESELLER)
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand + BALANCE.event_partner_offer_cash_gain
        )
        product.user_count += BALANCE.event_partner_offer_user_gain
        product.acquisition_rate = clamp_rate(
            product.acquisition_rate + BALANCE.event_partner_offer_acquisition_gain
        )
        for employee in get_designer_or_marketer_support(state.employees, product.id):
            employee.morale = clamp_int(
                employee.morale + BALANCE.event_partner_offer_morale_gain,
                0,
                100,
            )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You signed a partner deal for {product.name}. Cash "
            f"+{BALANCE.event_partner_offer_cash_gain}, users "
            f"+{BALANCE.event_partner_offer_user_gain}."
        )

    if option_id == "stay_direct":
        product.quality = clamp_int(
            product.quality + BALANCE.event_partner_offer_focus_quality_gain,
            0,
            100,
        )
        product.market_fit = clamp_int(
            product.market_fit + BALANCE.event_partner_offer_focus_fit_gain,
            0,
            100,
        )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You stayed direct and sharpened {product.name}. Quality "
            f"+{BALANCE.event_partner_offer_focus_quality_gain}, market fit "
            f"+{BALANCE.event_partner_offer_focus_fit_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for partner offer.")


def _apply_talent_bidding_war(state: GameState, event: PendingEvent, option_id: str) -> str:
    target = _get_target_employee(state, event)

    if option_id == "retain_team":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_talent_bidding_war_retain_cost
        )
        for employee in state.employees:
            employee.morale = clamp_int(
                employee.morale + BALANCE.event_talent_bidding_war_retain_morale_gain,
                0,
                100,
            )
        return (
            f"You paid to steady the team around {target.full_name}. Cash "
            f"-{BALANCE.event_talent_bidding_war_retain_cost}, morale "
            f"+{BALANCE.event_talent_bidding_war_retain_morale_gain}."
        )

    if option_id == "hold_line":
        for employee in state.employees:
            employee.morale = clamp_int(
                employee.morale - BALANCE.event_talent_bidding_war_hold_line_morale_loss,
                0,
                100,
            )
            employee.energy = clamp_int(
                employee.energy - BALANCE.event_talent_bidding_war_hold_line_energy_loss,
                0,
                100,
            )
        return (
            "You held the line on compensation. Team morale "
            f"-{BALANCE.event_talent_bidding_war_hold_line_morale_loss}, energy "
            f"-{BALANCE.event_talent_bidding_war_hold_line_energy_loss}."
        )

    raise ValueError(f"Unsupported option {option_id} for talent bidding war.")


def _apply_platform_breakthrough(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)

    if option_id == "productize_breakthrough":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_platform_breakthrough_productize_cost
        )
        product.quality = clamp_int(
            product.quality + BALANCE.event_platform_breakthrough_quality_gain,
            0,
            100,
        )
        product.market_fit = clamp_int(
            product.market_fit + BALANCE.event_platform_breakthrough_fit_gain,
            0,
            100,
        )
        product.acquisition_rate = clamp_rate(
            product.acquisition_rate + BALANCE.event_platform_breakthrough_acquisition_gain
        )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You productized the breakthrough in {product.name}. Cash "
            f"-{BALANCE.event_platform_breakthrough_productize_cost}, quality "
            f"+{BALANCE.event_platform_breakthrough_quality_gain}, market fit "
            f"+{BALANCE.event_platform_breakthrough_fit_gain}."
        )

    if option_id == "bank_the_gain":
        product.bug_level = clamp_int(
            product.bug_level - BALANCE.event_platform_breakthrough_bug_reduction,
            0,
            100,
        )
        product.technical_debt = clamp_int(
            product.technical_debt - BALANCE.event_platform_breakthrough_debt_reduction,
            0,
            100,
        )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You banked the platform gain inside {product.name}. Bugs "
            f"-{BALANCE.event_platform_breakthrough_bug_reduction}, debt "
            f"-{BALANCE.event_platform_breakthrough_debt_reduction}."
        )

    raise ValueError(f"Unsupported option {option_id} for platform breakthrough.")


def _apply_loan_covenant(state: GameState, event: PendingEvent, option_id: str) -> str:
    del event

    if option_id == "paydown_now":
        payment = min(
            state.finance.debt_principal,
            BALANCE.event_loan_covenant_paydown_amount,
        )
        state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - payment)
        state.finance.debt_principal = quantize_money(state.finance.debt_principal - payment)
        state.finance.investor_pressure = clamp_int(
            state.finance.investor_pressure - BALANCE.event_loan_covenant_paydown_pressure_relief,
            0,
            100,
        )
        state.finance.board_confidence = clamp_int(state.finance.board_confidence + 2, 0, 100)
        return (
            f"You paid down the covenant pressure. Cash -{payment}, debt -{payment}, "
            f"investor pressure -{BALANCE.event_loan_covenant_paydown_pressure_relief}."
        )

    if option_id == "renegotiate_terms":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand + BALANCE.event_loan_covenant_renegotiate_cash_gain
        )
        state.finance.loan_interest_rate = clamp_rate(
            state.finance.loan_interest_rate + BALANCE.event_loan_covenant_renegotiate_interest_gain
        )
        state.finance.investor_pressure = clamp_int(
            state.finance.investor_pressure + BALANCE.event_loan_covenant_renegotiate_pressure_gain,
            0,
            100,
        )
        state.finance.board_confidence = clamp_int(state.finance.board_confidence - 2, 0, 100)
        return (
            "You renegotiated the loan. Cash "
            f"+{BALANCE.event_loan_covenant_renegotiate_cash_gain}, interest rate "
            f"+{BALANCE.event_loan_covenant_renegotiate_interest_gain}, investor pressure "
            f"+{BALANCE.event_loan_covenant_renegotiate_pressure_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for loan covenant.")


def _apply_down_round_pressure(state: GameState, event: PendingEvent, option_id: str) -> str:
    del event

    if option_id == "take_bridge":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand + BALANCE.event_down_round_bridge_cash_gain
        )
        state.finance.total_raised = quantize_money(
            state.finance.total_raised + BALANCE.event_down_round_bridge_cash_gain
        )
        state.finance.equity_dilution = clamp_rate(
            state.finance.equity_dilution + BALANCE.event_down_round_bridge_dilution
        )
        state.finance.investor_pressure = clamp_int(
            state.finance.investor_pressure + BALANCE.event_down_round_bridge_pressure_gain,
            0,
            100,
        )
        state.finance.board_confidence = clamp_int(state.finance.board_confidence - 4, 0, 100)
        return (
            "You accepted the bridge round. Cash "
            f"+{BALANCE.event_down_round_bridge_cash_gain}, dilution "
            f"+{BALANCE.event_down_round_bridge_dilution}, investor pressure "
            f"+{BALANCE.event_down_round_bridge_pressure_gain}."
        )

    if option_id == "stay_independent":
        state.company.reputation = clamp_int(
            state.company.reputation - BALANCE.event_down_round_independent_reputation_loss,
            0,
            100,
        )
        state.finance.investor_pressure = clamp_int(state.finance.investor_pressure - 1, 0, 100)
        state.finance.board_confidence = clamp_int(state.finance.board_confidence + 2, 0, 100)
        for employee in state.employees:
            employee.morale = clamp_int(
                employee.morale + BALANCE.event_down_round_independent_morale_gain,
                0,
                100,
            )
        return (
            "You stayed independent. Reputation "
            f"-{BALANCE.event_down_round_independent_reputation_loss}, team morale "
            f"+{BALANCE.event_down_round_independent_morale_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for down round pressure.")


def _apply_bridge_round(state: GameState, event: PendingEvent, option_id: str) -> str:
    del event

    if option_id == "take_bridge":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand + BALANCE.event_bridge_round_take_cash_gain
        )
        state.finance.total_raised = quantize_money(
            state.finance.total_raised + BALANCE.event_bridge_round_take_cash_gain
        )
        state.finance.equity_dilution = clamp_rate(
            state.finance.equity_dilution + BALANCE.event_bridge_round_take_dilution_gain
        )
        state.finance.investor_pressure = clamp_int(
            state.finance.investor_pressure + BALANCE.event_bridge_round_take_pressure_gain,
            0,
            100,
        )
        state.finance.board_confidence = clamp_int(state.finance.board_confidence - 2, 0, 100)
        return (
            f"You took bridge capital. Cash +{BALANCE.event_bridge_round_take_cash_gain}, "
            f"dilution +{BALANCE.event_bridge_round_take_dilution_gain}, investor pressure "
            f"+{BALANCE.event_bridge_round_take_pressure_gain}."
        )

    if option_id == "cut_burn":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_bridge_round_cut_burn_cost
        )
        state.finance.board_confidence = clamp_int(
            state.finance.board_confidence + BALANCE.event_bridge_round_cut_burn_confidence_gain,
            0,
            100,
        )
        state.finance.investor_pressure = clamp_int(state.finance.investor_pressure - 1, 0, 100)
        for employee in state.employees:
            employee.morale = clamp_int(
                employee.morale - BALANCE.event_bridge_round_cut_burn_morale_loss,
                0,
                100,
            )
        return (
            f"You cut burn instead of raising. Cash -{BALANCE.event_bridge_round_cut_burn_cost}, "
            f"board confidence +{BALANCE.event_bridge_round_cut_burn_confidence_gain}, morale "
            f"-{BALANCE.event_bridge_round_cut_burn_morale_loss}."
        )

    raise ValueError(f"Unsupported option {option_id} for bridge round.")


def _apply_key_account_expansion(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)
    account = _get_best_active_account_for_product(state, product.id)

    if option_id == "build_success_plan":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_key_account_success_plan_cost
        )
        account.contract_value = quantize_money(
            account.contract_value + BALANCE.event_key_account_success_plan_contract_gain
        )
        account.satisfaction = clamp_int(
            account.satisfaction + BALANCE.event_key_account_success_plan_satisfaction_gain,
            0,
            100,
        )
        account.expansion_potential = clamp_int(account.expansion_potential - 8, 0, 100)
        product.market_fit = clamp_int(product.market_fit + 1, 0, 100)
        state.finance.board_confidence = clamp_int(state.finance.board_confidence + 1, 0, 100)
        return (
            f"You expanded {account.name}. Cash "
            f"-{BALANCE.event_key_account_success_plan_cost}, contract "
            f"+{BALANCE.event_key_account_success_plan_contract_gain}, satisfaction "
            f"+{BALANCE.event_key_account_success_plan_satisfaction_gain}."
        )

    if option_id == "ask_for_referral":
        product.user_count += BALANCE.event_key_account_referral_user_gain
        state.company.reputation = clamp_int(
            state.company.reputation + BALANCE.event_key_account_referral_reputation_gain,
            0,
            100,
        )
        account.satisfaction = clamp_int(
            account.satisfaction - BALANCE.event_key_account_referral_satisfaction_loss,
            0,
            100,
        )
        account.expansion_potential = clamp_int(account.expansion_potential - 4, 0, 100)
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"{account.name} referred new demand to {product.name}. Users "
            f"+{BALANCE.event_key_account_referral_user_gain}, reputation "
            f"+{BALANCE.event_key_account_referral_reputation_gain}, satisfaction "
            f"-{BALANCE.event_key_account_referral_satisfaction_loss}."
        )

    raise ValueError(f"Unsupported option {option_id} for key account expansion.")


def _apply_security_audit(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)
    accounts = _get_active_accounts_for_product(state, product.id)

    if option_id == "fund_audit":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_security_audit_fund_cost
        )
        product.technical_debt = clamp_int(
            product.technical_debt - BALANCE.event_security_audit_debt_reduction,
            0,
            100,
        )
        product.bug_level = clamp_int(
            product.bug_level - BALANCE.event_security_audit_bug_reduction,
            0,
            100,
        )
        state.company.reputation = clamp_int(
            state.company.reputation + BALANCE.event_security_audit_reputation_gain,
            0,
            100,
        )
        state.finance.board_confidence = clamp_int(
            state.finance.board_confidence + BALANCE.event_security_audit_board_gain,
            0,
            100,
        )
        for account in accounts:
            account.satisfaction = clamp_int(account.satisfaction + 2, 0, 100)
            account.churn_risk = clamp_int(account.churn_risk - 5, 0, 100)
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You funded the security audit for {product.name}. Cash "
            f"-{BALANCE.event_security_audit_fund_cost}, debt "
            f"-{BALANCE.event_security_audit_debt_reduction}, reputation "
            f"+{BALANCE.event_security_audit_reputation_gain}."
        )

    if option_id == "defer_audit":
        product.churn_rate = clamp_rate(
            product.churn_rate + BALANCE.event_security_audit_defer_churn_increase
        )
        state.company.reputation = clamp_int(
            state.company.reputation - BALANCE.event_security_audit_defer_reputation_loss,
            0,
            100,
        )
        for account in accounts:
            account.churn_risk = clamp_int(
                account.churn_risk + BALANCE.event_security_audit_defer_account_risk_gain,
                0,
                100,
            )
            if account.churn_risk >= BALANCE.key_account_status_at_risk_threshold:
                account.status = CustomerAccountStatus.AT_RISK
        return (
            f"You deferred the security audit for {product.name}. Churn rate "
            f"+{BALANCE.event_security_audit_defer_churn_increase}, reputation "
            f"-{BALANCE.event_security_audit_defer_reputation_loss}."
        )

    raise ValueError(f"Unsupported option {option_id} for security audit.")


def _apply_enterprise_sales_cycle(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)
    affected_employees = _get_assigned_employees(state, product.id)

    if option_id == "fund_poc":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_enterprise_poc_cost
        )
        product.user_count += BALANCE.event_enterprise_poc_user_gain
        product.market_fit = clamp_int(
            product.market_fit + BALANCE.event_enterprise_poc_fit_gain,
            0,
            100,
        )
        product.revenue_per_user = quantize_money(
            product.revenue_per_user + BALANCE.event_enterprise_poc_revenue_gain
        )
        for employee in affected_employees:
            employee.energy = clamp_int(
                employee.energy - BALANCE.event_enterprise_poc_energy_loss,
                0,
                100,
            )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You funded the enterprise proof-of-concept for {product.name}. Cash "
            f"-{BALANCE.event_enterprise_poc_cost}, users "
            f"+{BALANCE.event_enterprise_poc_user_gain}, revenue per user "
            f"+{BALANCE.event_enterprise_poc_revenue_gain}."
        )

    if option_id == "walk_away":
        state.company.reputation = clamp_int(
            state.company.reputation + BALANCE.event_enterprise_walkaway_reputation_gain,
            0,
            100,
        )
        state.finance.board_confidence = clamp_int(
            state.finance.board_confidence + BALANCE.event_enterprise_walkaway_board_gain,
            0,
            100,
        )
        return (
            "You walked away from the enterprise cycle and protected focus. Reputation "
            f"+{BALANCE.event_enterprise_walkaway_reputation_gain}, board confidence "
            f"+{BALANCE.event_enterprise_walkaway_board_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for enterprise sales cycle.")


def _apply_product_launch_window(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)

    if option_id == "launch_campaign":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_product_launch_campaign_cost
        )
        product.user_count += BALANCE.event_product_launch_user_gain
        product.acquisition_rate = clamp_rate(
            product.acquisition_rate + BALANCE.event_product_launch_acquisition_gain
        )
        product.bug_level = clamp_int(
            product.bug_level + BALANCE.event_product_launch_bug_increase,
            0,
            100,
        )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You pushed a launch campaign for {product.name}. Cash "
            f"-{BALANCE.event_product_launch_campaign_cost}, users "
            f"+{BALANCE.event_product_launch_user_gain}, bugs "
            f"+{BALANCE.event_product_launch_bug_increase}."
        )

    if option_id == "soft_launch":
        product.user_count += BALANCE.event_product_launch_soft_user_gain
        product.quality = clamp_int(
            product.quality + BALANCE.event_product_launch_soft_quality_gain,
            0,
            100,
        )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You soft-launched {product.name}. Users "
            f"+{BALANCE.event_product_launch_soft_user_gain}, quality "
            f"+{BALANCE.event_product_launch_soft_quality_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for product launch window.")


def _apply_platform_outage(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)
    affected_employees = _get_assigned_employees(state, product.id)
    accounts = _get_active_accounts_for_product(state, product.id)

    if option_id == "all_hands_recovery":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_platform_outage_response_cost
        )
        product.bug_level = clamp_int(
            product.bug_level - BALANCE.event_platform_outage_bug_reduction,
            0,
            100,
        )
        state.company.reputation = clamp_int(
            state.company.reputation - BALANCE.event_platform_outage_reputation_loss,
            0,
            100,
        )
        state.finance.board_confidence = clamp_int(state.finance.board_confidence + 1, 0, 100)
        for employee in affected_employees:
            employee.energy = clamp_int(
                employee.energy - BALANCE.event_platform_outage_energy_loss,
                0,
                100,
            )
        for account in accounts:
            account.churn_risk = clamp_int(account.churn_risk + 2, 0, 100)
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You ran an all-hands recovery for {product.name}. Cash "
            f"-{BALANCE.event_platform_outage_response_cost}, bugs "
            f"-{BALANCE.event_platform_outage_bug_reduction}, reputation "
            f"-{BALANCE.event_platform_outage_reputation_loss}."
        )

    if option_id == "minimize_cost":
        user_loss = min(product.user_count, BALANCE.event_platform_outage_delay_user_loss)
        product.user_count = max(0, product.user_count - user_loss)
        product.bug_level = clamp_int(
            product.bug_level + BALANCE.event_platform_outage_delay_bug_gain,
            0,
            100,
        )
        state.company.reputation = clamp_int(
            state.company.reputation - BALANCE.event_platform_outage_delay_reputation_loss,
            0,
            100,
        )
        for account in accounts:
            account.churn_risk = clamp_int(account.churn_risk + 5, 0, 100)
            if account.churn_risk >= BALANCE.key_account_status_at_risk_threshold:
                account.status = CustomerAccountStatus.AT_RISK
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You minimized the outage response for {product.name}. Users -{user_loss}, bugs "
            f"+{BALANCE.event_platform_outage_delay_bug_gain}, reputation "
            f"-{BALANCE.event_platform_outage_delay_reputation_loss}."
        )

    raise ValueError(f"Unsupported option {option_id} for platform outage.")


def _apply_competitor_acquisition(state: GameState, event: PendingEvent, option_id: str) -> str:
    del event
    product = _get_primary_active_product(state)

    if option_id == "differentiate_against_stack":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_competitor_acquisition_differentiate_cost
        )
        product.quality = clamp_int(
            product.quality + BALANCE.event_competitor_acquisition_quality_gain,
            0,
            100,
        )
        product.market_fit = clamp_int(
            product.market_fit + BALANCE.event_competitor_acquisition_fit_gain,
            0,
            100,
        )
        for competitor in state.competitors:
            competitor.aggression = clamp_int(competitor.aggression + 1, 0, 100)
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You differentiated {product.name} against the larger rival bundle. Cash "
            f"-{BALANCE.event_competitor_acquisition_differentiate_cost}, quality "
            f"+{BALANCE.event_competitor_acquisition_quality_gain}, market fit "
            f"+{BALANCE.event_competitor_acquisition_fit_gain}."
        )

    if option_id == "seek_distribution_partner":
        product.user_count += BALANCE.event_competitor_acquisition_partner_user_gain
        state.company.reputation = clamp_int(
            state.company.reputation + BALANCE.event_competitor_acquisition_partner_reputation_gain,
            0,
            100,
        )
        for competitor in state.competitors:
            competitor.funding_level = clamp_int(competitor.funding_level + 1, 0, 5)
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You found distribution for {product.name}. Users "
            f"+{BALANCE.event_competitor_acquisition_partner_user_gain}, reputation "
            f"+{BALANCE.event_competitor_acquisition_partner_reputation_gain}, "
            "but rival funding pressure rose."
        )

    raise ValueError(f"Unsupported option {option_id} for competitor acquisition.")


def _apply_regulatory_shift(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)
    accounts = _get_active_accounts_for_product(state, product.id)

    if option_id == "proactive_controls":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_regulatory_shift_cost
        )
        product.technical_debt = clamp_int(
            product.technical_debt - BALANCE.event_regulatory_shift_debt_reduction,
            0,
            100,
        )
        product.market_fit = clamp_int(
            product.market_fit + BALANCE.event_regulatory_shift_fit_gain,
            0,
            100,
        )
        state.company.reputation = clamp_int(
            state.company.reputation + BALANCE.event_regulatory_shift_reputation_gain,
            0,
            100,
        )
        state.finance.board_confidence = clamp_int(
            state.finance.board_confidence + BALANCE.event_regulatory_shift_board_gain,
            0,
            100,
        )
        for account in accounts:
            account.churn_risk = clamp_int(account.churn_risk - 4, 0, 100)
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You invested in controls for {product.name}. Cash "
            f"-{BALANCE.event_regulatory_shift_cost}, debt "
            f"-{BALANCE.event_regulatory_shift_debt_reduction}, reputation "
            f"+{BALANCE.event_regulatory_shift_reputation_gain}."
        )

    if option_id == "wait_for_clarity":
        product.churn_rate = clamp_rate(
            product.churn_rate + BALANCE.event_regulatory_shift_wait_churn_increase
        )
        state.company.reputation = clamp_int(
            state.company.reputation - BALANCE.event_regulatory_shift_wait_reputation_loss,
            0,
            100,
        )
        for account in accounts:
            account.churn_risk = clamp_int(
                account.churn_risk + BALANCE.event_regulatory_shift_wait_account_risk_gain,
                0,
                100,
            )
            if account.churn_risk >= BALANCE.key_account_status_at_risk_threshold:
                account.status = CustomerAccountStatus.AT_RISK
        return (
            f"You waited on the regulatory shift for {product.name}. Churn rate "
            f"+{BALANCE.event_regulatory_shift_wait_churn_increase}, reputation "
            f"-{BALANCE.event_regulatory_shift_wait_reputation_loss}."
        )

    raise ValueError(f"Unsupported option {option_id} for regulatory shift.")


def _apply_audit_followup_review(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)
    accounts = _get_active_accounts_for_product(state, product.id)

    if option_id == "package_evidence":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_audit_followup_cost
        )
        product.technical_debt = clamp_int(
            product.technical_debt - BALANCE.event_audit_followup_debt_reduction,
            0,
            100,
        )
        state.company.reputation = clamp_int(
            state.company.reputation + BALANCE.event_audit_followup_reputation_gain,
            0,
            100,
        )
        state.finance.board_confidence = clamp_int(
            state.finance.board_confidence + BALANCE.event_audit_followup_board_gain,
            0,
            100,
        )
        for account in accounts:
            account.churn_risk = clamp_int(account.churn_risk - 3, 0, 100)
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You packaged audit evidence for {product.name}. Cash "
            f"-{BALANCE.event_audit_followup_cost}, debt "
            f"-{BALANCE.event_audit_followup_debt_reduction}, reputation "
            f"+{BALANCE.event_audit_followup_reputation_gain}."
        )

    if option_id == "defer_followup":
        state.company.reputation = clamp_int(state.company.reputation - 1, 0, 100)
        for account in accounts:
            account.churn_risk = clamp_int(
                account.churn_risk + BALANCE.event_audit_followup_defer_risk_gain,
                0,
                100,
            )
            if account.churn_risk >= BALANCE.key_account_status_at_risk_threshold:
                account.status = CustomerAccountStatus.AT_RISK
        return (
            f"You deferred audit follow-up for {product.name}. Reputation -1, account risk "
            f"+{BALANCE.event_audit_followup_defer_risk_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for audit follow-up review.")


def _apply_launch_aftershock(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)
    affected_employees = _get_assigned_employees(state, product.id)

    if option_id == "stabilize_experience":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_launch_aftershock_stabilize_cost
        )
        product.bug_level = clamp_int(
            product.bug_level - BALANCE.event_launch_aftershock_bug_reduction,
            0,
            100,
        )
        product.quality = clamp_int(
            product.quality + BALANCE.event_launch_aftershock_quality_gain,
            0,
            100,
        )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You stabilized {product.name} after launch. Cash "
            f"-{BALANCE.event_launch_aftershock_stabilize_cost}, bugs "
            f"-{BALANCE.event_launch_aftershock_bug_reduction}, quality "
            f"+{BALANCE.event_launch_aftershock_quality_gain}."
        )

    if option_id == "chase_second_wave":
        product.user_count += BALANCE.event_launch_aftershock_chase_user_gain
        product.bug_level = clamp_int(
            product.bug_level + BALANCE.event_launch_aftershock_chase_bug_gain,
            0,
            100,
        )
        for employee in affected_employees:
            employee.energy = clamp_int(
                employee.energy - BALANCE.event_launch_aftershock_chase_energy_loss,
                0,
                100,
            )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You chased a second launch wave for {product.name}. Users "
            f"+{BALANCE.event_launch_aftershock_chase_user_gain}, bugs "
            f"+{BALANCE.event_launch_aftershock_chase_bug_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for launch aftershock.")


def _apply_enterprise_procurement_delay(
    state: GameState,
    event: PendingEvent,
    option_id: str,
) -> str:
    product = _get_target_product(state, event)
    accounts = _get_active_accounts_for_product(state, product.id)

    if option_id == "fund_proof":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_procurement_delay_proof_cost
        )
        product.user_count += BALANCE.event_procurement_delay_user_gain
        product.revenue_per_user = quantize_money(
            product.revenue_per_user + BALANCE.event_procurement_delay_revenue_gain
        )
        product.market_fit = clamp_int(product.market_fit + 1, 0, 100)
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You funded proof artifacts for {product.name}. Cash "
            f"-{BALANCE.event_procurement_delay_proof_cost}, users "
            f"+{BALANCE.event_procurement_delay_user_gain}, revenue per user "
            f"+{BALANCE.event_procurement_delay_revenue_gain}."
        )

    if option_id == "wait_out_process":
        state.company.reputation = clamp_int(
            state.company.reputation - BALANCE.event_procurement_delay_wait_reputation_loss,
            0,
            100,
        )
        for account in accounts:
            account.churn_risk = clamp_int(
                account.churn_risk + BALANCE.event_procurement_delay_wait_account_risk_gain,
                0,
                100,
            )
            if account.churn_risk >= BALANCE.key_account_status_at_risk_threshold:
                account.status = CustomerAccountStatus.AT_RISK
        return (
            f"You waited out procurement for {product.name}. Reputation "
            f"-{BALANCE.event_procurement_delay_wait_reputation_loss}, account risk "
            f"+{BALANCE.event_procurement_delay_wait_account_risk_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for enterprise procurement delay.")


def _apply_support_meltdown(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)
    stressed_accounts = _get_most_stressed_accounts(state, limit=3)

    if option_id == "staff_emergency":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_support_meltdown_staff_cost
        )
        state.support_program.staffing_level = clamp_int(
            state.support_program.staffing_level + BALANCE.event_support_meltdown_staffing_gain,
            0,
            20,
        )
        state.support_program.backlog_queue = max(
            0,
            state.support_program.backlog_queue - BALANCE.event_support_meltdown_backlog_relief,
        )
        state.support_program.escalation_queue = max(
            0,
            state.support_program.escalation_queue
            - BALANCE.event_support_meltdown_escalation_relief,
        )
        for employee in state.employees:
            employee.morale = clamp_int(
                employee.morale - BALANCE.event_support_meltdown_morale_loss,
                0,
                100,
            )
        for account in stressed_accounts:
            account.open_tickets = max(0, account.open_tickets - 4)
            account.sla_breach_risk = clamp_int(account.sla_breach_risk - 6, 0, 100)
            account.churn_risk = clamp_int(account.churn_risk - 4, 0, 100)
        return (
            f"You staffed an emergency response around {product.name}. Cash "
            f"-{BALANCE.event_support_meltdown_staff_cost}, backlog "
            f"-{BALANCE.event_support_meltdown_backlog_relief}."
        )

    if option_id == "ration_support":
        state.support_program.backlog_queue += BALANCE.event_support_meltdown_ration_queue_gain
        state.company.reputation = clamp_int(
            state.company.reputation - BALANCE.event_support_meltdown_ration_reputation_loss,
            0,
            100,
        )
        for account in stressed_accounts:
            account.churn_risk = clamp_int(
                account.churn_risk + BALANCE.event_support_meltdown_ration_account_risk_gain,
                0,
                100,
            )
            account.ticket_queue_age += 1
            if account.churn_risk >= BALANCE.key_account_status_at_risk_threshold:
                account.status = CustomerAccountStatus.AT_RISK
        return (
            f"You rationed support around {product.name}. Reputation "
            f"-{BALANCE.event_support_meltdown_ration_reputation_loss}, backlog "
            f"+{BALANCE.event_support_meltdown_ration_queue_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for support meltdown.")


def _apply_board_reckoning(state: GameState, event: PendingEvent, option_id: str) -> str:
    del event

    if option_id == "reset_plan":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_board_reckoning_cut_cost
        )
        state.capital_plan = get_capital_plan_profile(
            CapitalPlanMode.CONSERVE,
            state.capital_plan.source_preference,
        )
        state.finance.board_pressure = clamp_int(
            state.finance.board_pressure - BALANCE.event_board_reckoning_cut_pressure_relief,
            0,
            100,
        )
        state.finance.board_confidence = clamp_int(
            state.finance.board_confidence + BALANCE.event_board_reckoning_cut_confidence_gain,
            0,
            100,
        )
        state.finance.board_resolution_due = False
        state.finance.board_resolution_window = 0
        for product in state.products:
            if product.is_active:
                product.acquisition_rate = clamp_rate(
                    product.acquisition_rate - BALANCE.event_board_reckoning_cut_growth_penalty
                )
        return (
            f"You reset the plan for the board. Cash "
            f"-{BALANCE.event_board_reckoning_cut_cost}, board pressure "
            f"-{BALANCE.event_board_reckoning_cut_pressure_relief}."
        )

    if option_id == "defend_growth":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand + BALANCE.event_board_reckoning_defend_cash_gain
        )
        state.finance.board_pressure = clamp_int(
            state.finance.board_pressure + BALANCE.event_board_reckoning_defend_pressure_gain,
            0,
            100,
        )
        state.finance.board_confidence = clamp_int(
            state.finance.board_confidence - BALANCE.event_board_reckoning_defend_confidence_loss,
            0,
            100,
        )
        for product in state.products:
            if product.is_active:
                product.acquisition_rate = clamp_rate(
                    product.acquisition_rate + BALANCE.event_board_reckoning_defend_growth_gain
                )
        return (
            f"You defended the aggressive plan. Cash "
            f"+{BALANCE.event_board_reckoning_defend_cash_gain}, board pressure "
            f"+{BALANCE.event_board_reckoning_defend_pressure_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for board reckoning.")


def _apply_partner_qbr(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)
    partnership = _get_most_conflicted_partnership(state, product.id)

    if option_id == "double_enablement":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_partner_qbr_enablement_cost
        )
        partnership.enablement_level = clamp_int(partnership.enablement_level + 8, 0, 100)
        partnership.quality = clamp_int(
            partnership.quality + BALANCE.event_partner_qbr_quality_gain,
            0,
            100,
        )
        partnership.risk = clamp_int(
            partnership.risk - BALANCE.event_partner_qbr_risk_relief,
            0,
            100,
        )
        partnership.conflict_pressure = clamp_int(
            partnership.conflict_pressure - BALANCE.event_partner_qbr_conflict_relief,
            0,
            100,
        )
        partnership.last_review_turn = state.company.current_turn
        product.user_count += BALANCE.event_partner_qbr_user_gain
        partnership.sourced_users += BALANCE.event_partner_qbr_user_gain
        state.support_program.backlog_queue += 2
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You deepened channel enablement for {product.name}. Cash "
            f"-{BALANCE.event_partner_qbr_enablement_cost}, users "
            f"+{BALANCE.event_partner_qbr_user_gain}."
        )

    if option_id == "pause_channel":
        partnership.status = PartnershipStatus.PAUSED
        partnership.conflict_pressure = clamp_int(
            partnership.conflict_pressure - BALANCE.event_partner_qbr_pause_conflict_relief,
            0,
            100,
        )
        partnership.risk = clamp_int(partnership.risk - 4, 0, 100)
        state.finance.board_pressure = clamp_int(
            state.finance.board_pressure - BALANCE.event_partner_qbr_pause_pressure_relief,
            0,
            100,
        )
        product.user_count = max(0, product.user_count - BALANCE.event_partner_qbr_pause_user_loss)
        return (
            f"You paused channel expansion for {product.name}. Users "
            f"-{BALANCE.event_partner_qbr_pause_user_loss}, board pressure "
            f"-{BALANCE.event_partner_qbr_pause_pressure_relief}."
        )

    raise ValueError(f"Unsupported option {option_id} for partner QBR.")


def _apply_partner_breakdown(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)
    partnership = _get_most_stressed_partnership(state, product.id)

    if option_id == "fund_recovery":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_partner_breakdown_recovery_cost
        )
        partnership.status = PartnershipStatus.RECOVERY
        partnership.conflict_pressure = clamp_int(
            partnership.conflict_pressure - BALANCE.event_partner_breakdown_conflict_relief,
            0,
            100,
        )
        partnership.risk = clamp_int(
            partnership.risk - BALANCE.event_partner_breakdown_risk_relief,
            0,
            100,
        )
        partnership.quality = clamp_int(
            partnership.quality + BALANCE.event_partner_breakdown_quality_gain,
            0,
            100,
        )
        partnership.last_review_turn = state.company.current_turn
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You funded channel recovery for {product.name}. Cash "
            f"-{BALANCE.event_partner_breakdown_recovery_cost}, conflict "
            f"-{BALANCE.event_partner_breakdown_conflict_relief}."
        )

    if option_id == "freeze_lane":
        partnership.status = PartnershipStatus.PAUSED
        partnership.conflict_pressure = clamp_int(partnership.conflict_pressure - 6, 0, 100)
        partnership.risk = clamp_int(partnership.risk - 3, 0, 100)
        state.finance.board_pressure = clamp_int(
            state.finance.board_pressure - BALANCE.event_partner_breakdown_pause_pressure_relief,
            0,
            100,
        )
        product.user_count = max(
            0, product.user_count - BALANCE.event_partner_breakdown_pause_user_loss
        )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You froze the channel for {product.name}. Users "
            f"-{BALANCE.event_partner_breakdown_pause_user_loss}, board pressure "
            f"-{BALANCE.event_partner_breakdown_pause_pressure_relief}."
        )

    raise ValueError(f"Unsupported option {option_id} for partner breakdown.")


def _apply_partner_renegotiation(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)
    partnership = _get_most_stressed_partnership(state, product.id)

    if option_id == "concede_margin":
        partnership.rev_share_rate = clamp_rate(
            partnership.rev_share_rate + BALANCE.event_partner_renegotiation_rev_share_penalty
        )
        partnership.conflict_pressure = clamp_int(
            partnership.conflict_pressure - BALANCE.event_partner_renegotiation_conflict_relief,
            0,
            100,
        )
        partnership.risk = clamp_int(
            partnership.risk - BALANCE.event_partner_renegotiation_risk_relief,
            0,
            100,
        )
        partnership.quality = clamp_int(
            partnership.quality + BALANCE.event_partner_renegotiation_quality_gain,
            0,
            100,
        )
        partnership.last_review_turn = state.company.current_turn
        partnership.status = PartnershipStatus.RECOVERY
        return (
            f"You conceded economics for {partnership.name}. Rev-share "
            f"+{BALANCE.event_partner_renegotiation_rev_share_penalty:.2%}, conflict "
            f"-{BALANCE.event_partner_renegotiation_conflict_relief}."
        )

    if option_id == "hold_line":
        product.user_count = max(
            0,
            product.user_count - BALANCE.event_partner_renegotiation_hold_line_user_loss,
        )
        partnership.conflict_pressure = clamp_int(partnership.conflict_pressure + 4, 0, 100)
        state.finance.board_pressure = clamp_int(
            state.finance.board_pressure
            + BALANCE.event_partner_renegotiation_hold_line_pressure_gain,
            0,
            100,
        )
        product.lifecycle_stage = infer_lifecycle_stage(product)
        return (
            f"You held the line on {partnership.name}. Users "
            f"-{BALANCE.event_partner_renegotiation_hold_line_user_loss}, board pressure "
            f"+{BALANCE.event_partner_renegotiation_hold_line_pressure_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for partner renegotiation.")


def _apply_board_recovery_window(state: GameState, event: PendingEvent, option_id: str) -> str:
    del event

    if option_id == "fund_control_room":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_board_recovery_window_cash_cost
        )
        state.finance.board_confidence = clamp_int(
            state.finance.board_confidence + BALANCE.event_board_recovery_window_confidence_gain,
            0,
            100,
        )
        state.finance.board_score = clamp_int(
            state.finance.board_score + BALANCE.event_board_recovery_window_score_gain,
            0,
            100,
        )
        state.finance.governance_risk = clamp_int(
            state.finance.governance_risk - BALANCE.event_board_recovery_window_risk_relief,
            0,
            100,
        )
        state.finance.board_recovery_turns_remaining = max(
            0,
            state.finance.board_recovery_turns_remaining - 1,
        )
        return (
            f"You funded a board recovery control room. Cash "
            f"-{BALANCE.event_board_recovery_window_cash_cost}, board confidence "
            f"+{BALANCE.event_board_recovery_window_confidence_gain}."
        )

    if option_id == "narrow_scope":
        state.finance.board_pressure = clamp_int(
            state.finance.board_pressure
            - BALANCE.event_board_recovery_window_scope_pressure_relief,
            0,
            100,
        )
        state.finance.board_portfolio_focus_score = clamp_int(
            state.finance.board_portfolio_focus_score
            + BALANCE.event_board_recovery_window_scope_focus_gain,
            0,
            100,
        )
        state.company.reputation = clamp_int(
            state.company.reputation - BALANCE.event_board_recovery_window_scope_reputation_loss,
            0,
            100,
        )
        state.finance.board_recovery_turns_remaining = max(
            0,
            state.finance.board_recovery_turns_remaining - 1,
        )
        return (
            f"You narrowed scope to satisfy the board. Board pressure "
            f"-{BALANCE.event_board_recovery_window_scope_pressure_relief}, reputation "
            f"-{BALANCE.event_board_recovery_window_scope_reputation_loss}."
        )

    raise ValueError(f"Unsupported option {option_id} for board recovery window.")


def _apply_capital_market_freeze(state: GameState, event: PendingEvent, option_id: str) -> str:
    del event

    if option_id == "freeze_hiring":
        state.capital_plan = get_capital_plan_profile(
            CapitalPlanMode.CONSERVE,
            state.capital_plan.source_preference,
        )
        state.finance.covenant_risk = clamp_int(
            state.finance.covenant_risk
            - BALANCE.event_capital_market_freeze_freeze_covenant_relief,
            0,
            100,
        )
        state.finance.investor_pressure = clamp_int(
            state.finance.investor_pressure - BALANCE.event_capital_market_freeze_pressure_relief,
            0,
            100,
        )
        for employee in state.employees:
            employee.morale = clamp_int(
                employee.morale - BALANCE.event_capital_market_freeze_freeze_morale_loss,
                0,
                100,
            )
        return (
            "You froze hiring and protected runway. "
            f"Investor pressure -{BALANCE.event_capital_market_freeze_pressure_relief}."
        )

    if option_id == "accept_bridge_terms":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand + BALANCE.event_capital_market_freeze_cash_gain
        )
        state.finance.total_raised = quantize_money(
            state.finance.total_raised + BALANCE.event_capital_market_freeze_cash_gain
        )
        state.finance.equity_dilution = clamp_rate(
            state.finance.equity_dilution + BALANCE.event_capital_market_freeze_dilution
        )
        state.finance.board_pressure = clamp_int(state.finance.board_pressure + 2, 0, 100)
        state.finance.board_confidence = clamp_int(state.finance.board_confidence - 1, 0, 100)
        return (
            "You accepted expensive bridge terms. Cash "
            f"+{BALANCE.event_capital_market_freeze_cash_gain}, dilution "
            f"+{BALANCE.event_capital_market_freeze_dilution}."
        )

    raise ValueError(f"Unsupported option {option_id} for capital market freeze.")


def _apply_succession_gap(state: GameState, event: PendingEvent, option_id: str) -> str:
    employee = _get_target_employee(state, event)

    if option_id == "promote_internal_lead":
        employee.is_team_lead = True
        employee.leadership_score = clamp_int(
            employee.leadership_score + BALANCE.event_succession_gap_leadership_gain,
            0,
            100,
        )
        employee.succession_risk = clamp_int(
            employee.succession_risk - BALANCE.event_succession_gap_attrition_relief,
            0,
            100,
        )
        employee.attrition_risk = clamp_int(
            employee.attrition_risk - BALANCE.event_succession_gap_attrition_relief,
            0,
            100,
        )
        employee.morale = clamp_int(
            employee.morale + BALANCE.event_succession_gap_morale_gain,
            0,
            100,
        )
        state.finance.board_team_health_score = clamp_int(
            state.finance.board_team_health_score + 2,
            0,
            100,
        )
        return (
            f"You elevated backup leadership around {employee.full_name}. "
            f"Morale +{BALANCE.event_succession_gap_morale_gain}, attrition risk "
            f"-{BALANCE.event_succession_gap_attrition_relief}."
        )

    if option_id == "wait_and_hope":
        employee.attrition_risk = clamp_int(
            employee.attrition_risk + BALANCE.event_succession_gap_wait_attrition_gain,
            0,
            100,
        )
        employee.morale = clamp_int(
            employee.morale - BALANCE.event_succession_gap_wait_morale_loss,
            0,
            100,
        )
        state.finance.board_team_health_score = clamp_int(
            state.finance.board_team_health_score - 2,
            0,
            100,
        )
        state.finance.board_pressure = clamp_int(state.finance.board_pressure + 1, 0, 100)
        return (
            f"You deferred succession work around {employee.full_name}. Attrition risk "
            f"+{BALANCE.event_succession_gap_wait_attrition_gain}, morale "
            f"-{BALANCE.event_succession_gap_wait_morale_loss}."
        )

    raise ValueError(f"Unsupported option {option_id} for succession gap.")


def _apply_channel_conflict(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)
    partnership = _get_most_conflicted_partnership(state, product.id)

    if option_id == "protect_direct":
        user_loss = min(product.user_count, BALANCE.event_channel_conflict_direct_user_loss)
        product.user_count = max(0, product.user_count - user_loss)
        partnership.conflict_pressure = clamp_int(
            partnership.conflict_pressure - BALANCE.event_channel_conflict_direct_relief,
            0,
            100,
        )
        partnership.risk = clamp_int(partnership.risk - 4, 0, 100)
        return (
            f"You protected direct sales for {product.name}. Users -{user_loss}, conflict "
            f"-{BALANCE.event_channel_conflict_direct_relief}."
        )

    if option_id == "lean_partner":
        product.user_count += BALANCE.event_channel_conflict_partner_user_gain
        partnership.sourced_users += BALANCE.event_channel_conflict_partner_user_gain
        partnership.conflict_pressure = clamp_int(
            partnership.conflict_pressure + BALANCE.event_channel_conflict_partner_conflict_gain,
            0,
            100,
        )
        state.finance.board_pressure = clamp_int(
            state.finance.board_pressure + BALANCE.event_channel_conflict_partner_pressure_gain,
            0,
            100,
        )
        return (
            f"You leaned into the partner for {product.name}. Users "
            f"+{BALANCE.event_channel_conflict_partner_user_gain}, board pressure "
            f"+{BALANCE.event_channel_conflict_partner_pressure_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for channel conflict.")


def _apply_exit_interest(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)

    if option_id == "explore_interest":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand + BALANCE.event_exit_interest_cash_gain
        )
        state.company.reputation = clamp_int(
            state.company.reputation + BALANCE.event_exit_interest_reputation_gain,
            0,
            100,
        )
        state.finance.board_confidence = clamp_int(
            state.finance.board_confidence + BALANCE.event_exit_interest_confidence_gain,
            0,
            100,
        )
        state.finance.board_pressure = clamp_int(
            state.finance.board_pressure + BALANCE.event_exit_interest_pressure_gain,
            0,
            100,
        )
        return (
            f"You explored exit interest around {product.name}. Cash "
            f"+{BALANCE.event_exit_interest_cash_gain}, reputation "
            f"+{BALANCE.event_exit_interest_reputation_gain}."
        )

    if option_id == "stay_independent":
        state.finance.board_confidence = clamp_int(
            state.finance.board_confidence
            + BALANCE.event_exit_interest_independence_confidence_gain,
            0,
            100,
        )
        state.finance.investor_pressure = clamp_int(
            state.finance.investor_pressure
            - BALANCE.event_exit_interest_independence_pressure_relief,
            0,
            100,
        )
        return (
            f"You stayed independent around {product.name}. Board confidence "
            f"+{BALANCE.event_exit_interest_independence_confidence_gain}, investor pressure "
            f"-{BALANCE.event_exit_interest_independence_pressure_relief}."
        )

    raise ValueError(f"Unsupported option {option_id} for exit interest.")


def _apply_public_market_scrutiny(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)

    if option_id == "tighten_controls":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_public_market_scrutiny_control_cost
        )
        state.finance.board_confidence = clamp_int(
            state.finance.board_confidence + BALANCE.event_public_market_scrutiny_confidence_gain,
            0,
            100,
        )
        state.finance.board_score = clamp_int(
            state.finance.board_score + BALANCE.event_public_market_scrutiny_score_gain,
            0,
            100,
        )
        state.finance.governance_risk = clamp_int(
            state.finance.governance_risk - BALANCE.event_public_market_scrutiny_risk_relief,
            0,
            100,
        )
        state.support_program.backlog_queue = max(0, state.support_program.backlog_queue - 2)
        return (
            f"You tightened controls around {product.name}. Cash "
            f"-{BALANCE.event_public_market_scrutiny_control_cost}, board confidence "
            f"+{BALANCE.event_public_market_scrutiny_confidence_gain}."
        )

    if option_id == "sell_story":
        state.company.reputation = clamp_int(
            state.company.reputation + BALANCE.event_public_market_scrutiny_story_reputation_gain,
            0,
            100,
        )
        state.finance.board_pressure = clamp_int(
            state.finance.board_pressure + BALANCE.event_public_market_scrutiny_story_pressure_gain,
            0,
            100,
        )
        state.support_program.backlog_queue += (
            BALANCE.event_public_market_scrutiny_story_backlog_gain
        )
        return (
            f"You sold a bigger story around {product.name}. Reputation "
            f"+{BALANCE.event_public_market_scrutiny_story_reputation_gain}, board pressure "
            f"+{BALANCE.event_public_market_scrutiny_story_pressure_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for public market scrutiny.")


def _apply_ipo_audit_committee(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)

    if option_id == "fund_audit_readiness":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_ipo_audit_committee_fund_cost
        )
        state.finance.board_confidence = clamp_int(
            state.finance.board_confidence + BALANCE.event_ipo_audit_committee_confidence_gain,
            0,
            100,
        )
        state.finance.board_score = clamp_int(
            state.finance.board_score + BALANCE.event_ipo_audit_committee_score_gain,
            0,
            100,
        )
        state.finance.governance_risk = clamp_int(
            state.finance.governance_risk - BALANCE.event_ipo_audit_committee_risk_relief,
            0,
            100,
        )
        state.support_program.backlog_queue = max(
            0,
            state.support_program.backlog_queue - BALANCE.event_ipo_audit_committee_backlog_relief,
        )
        for account in _get_active_accounts_for_product(state, product.id):
            if account.segment.value != "enterprise":
                continue
            account.sla_breach_risk = clamp_int(account.sla_breach_risk - 4, 0, 100)
            account.ticket_queue_age = max(0, account.ticket_queue_age - 1)
        return (
            f"You funded audit readiness around {product.name}. Cash "
            f"-{BALANCE.event_ipo_audit_committee_fund_cost}, board confidence "
            f"+{BALANCE.event_ipo_audit_committee_confidence_gain}."
        )

    if option_id == "delay_committee":
        state.finance.board_pressure = clamp_int(
            state.finance.board_pressure + BALANCE.event_ipo_audit_committee_delay_pressure_gain,
            0,
            100,
        )
        state.finance.governance_risk = clamp_int(
            state.finance.governance_risk + BALANCE.event_ipo_audit_committee_delay_risk_gain,
            0,
            100,
        )
        state.support_program.backlog_queue += BALANCE.event_ipo_audit_committee_delay_queue_gain
        return (
            "You delayed the audit committee. Board pressure "
            f"+{BALANCE.event_ipo_audit_committee_delay_pressure_gain}, governance risk "
            f"+{BALANCE.event_ipo_audit_committee_delay_risk_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for IPO audit committee.")


def _apply_acquirer_diligence(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)

    if option_id == "open_data_room":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_acquirer_diligence_data_room_cost
        )
        state.finance.board_confidence = clamp_int(
            state.finance.board_confidence + BALANCE.event_acquirer_diligence_confidence_gain,
            0,
            100,
        )
        state.finance.board_score = clamp_int(
            state.finance.board_score + BALANCE.event_acquirer_diligence_score_gain,
            0,
            100,
        )
        for partnership in state.partnerships:
            if partnership.product_id == product.id and partnership.status.value != "paused":
                partnership.risk = clamp_int(
                    partnership.risk - BALANCE.event_acquirer_diligence_partner_risk_relief,
                    0,
                    100,
                )
                partnership.conflict_pressure = clamp_int(
                    partnership.conflict_pressure
                    - (BALANCE.event_acquirer_diligence_partner_risk_relief // 2),
                    0,
                    100,
                )
        return (
            f"You opened diligence around {product.name}. Cash "
            f"-{BALANCE.event_acquirer_diligence_data_room_cost}, board confidence "
            f"+{BALANCE.event_acquirer_diligence_confidence_gain}."
        )

    if option_id == "protect_optionality":
        state.company.reputation = clamp_int(
            state.company.reputation + BALANCE.event_acquirer_diligence_optionality_reputation_gain,
            0,
            100,
        )
        state.finance.investor_pressure = clamp_int(
            state.finance.investor_pressure
            - BALANCE.event_acquirer_diligence_optionality_pressure_relief,
            0,
            100,
        )
        for account in _get_active_accounts_for_product(state, product.id)[:2]:
            account.renewal_health = clamp_int(account.renewal_health + 2, 0, 100)
        return (
            f"You protected optionality around {product.name}. Reputation "
            f"+{BALANCE.event_acquirer_diligence_optionality_reputation_gain}, investor pressure "
            f"-{BALANCE.event_acquirer_diligence_optionality_pressure_relief}."
        )

    raise ValueError(f"Unsupported option {option_id} for acquirer diligence.")


def _apply_buyer_reference_check(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)

    if option_id == "fund_reference_program":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_buyer_reference_check_fund_cost
        )
        state.finance.board_confidence = clamp_int(
            state.finance.board_confidence + BALANCE.event_buyer_reference_check_confidence_gain,
            0,
            100,
        )
        for partnership in state.partnerships:
            if partnership.product_id != product.id:
                continue
            partnership.risk = clamp_int(
                partnership.risk - BALANCE.event_buyer_reference_check_partner_risk_relief,
                0,
                100,
            )
            partnership.conflict_pressure = clamp_int(
                partnership.conflict_pressure
                - BALANCE.event_buyer_reference_check_partner_conflict_relief,
                0,
                100,
            )
        for account in _get_active_accounts_for_product(state, product.id)[:2]:
            account.renewal_health = clamp_int(
                account.renewal_health + BALANCE.event_buyer_reference_check_account_health_gain,
                0,
                100,
            )
            account.satisfaction = clamp_int(
                account.satisfaction + BALANCE.event_buyer_reference_check_account_health_gain,
                0,
                100,
            )
        return (
            f"You funded buyer references around {product.name}. Cash "
            f"-{BALANCE.event_buyer_reference_check_fund_cost}, board confidence "
            f"+{BALANCE.event_buyer_reference_check_confidence_gain}."
        )

    if option_id == "protect_optionality":
        state.company.reputation = clamp_int(
            state.company.reputation
            + BALANCE.event_buyer_reference_check_optionality_reputation_gain,
            0,
            100,
        )
        for partnership in state.partnerships:
            if partnership.product_id != product.id:
                continue
            partnership.conflict_pressure = clamp_int(
                partnership.conflict_pressure
                + BALANCE.event_buyer_reference_check_optionality_conflict_gain,
                0,
                100,
            )
        return (
            f"You protected optionality around {product.name}. Reputation "
            f"+{BALANCE.event_buyer_reference_check_optionality_reputation_gain}, "
            "but partner friction rose."
        )

    raise ValueError(f"Unsupported option {option_id} for buyer reference check.")


def _apply_independence_reckoning(state: GameState, event: PendingEvent, option_id: str) -> str:
    del event

    if option_id == "double_down_efficiency":
        state.finance.investor_pressure = clamp_int(
            state.finance.investor_pressure
            - BALANCE.event_independence_reckoning_efficiency_pressure_relief,
            0,
            100,
        )
        state.finance.covenant_risk = clamp_int(
            state.finance.covenant_risk
            - BALANCE.event_independence_reckoning_efficiency_covenant_relief,
            0,
            100,
        )
        state.company.reputation = clamp_int(
            state.company.reputation
            + BALANCE.event_independence_reckoning_efficiency_reputation_gain,
            0,
            100,
        )
        product_shift = min(3, state.capital_plan.product_investment_share)
        gtm_shift = min(2, state.capital_plan.go_to_market_share)
        state.capital_plan = state.capital_plan.model_copy(
            update={
                "product_investment_share": (
                    state.capital_plan.product_investment_share - product_shift
                ),
                "go_to_market_share": state.capital_plan.go_to_market_share - gtm_shift,
                "reserve_share": (state.capital_plan.reserve_share + product_shift + gtm_shift),
            }
        )
        return (
            "You doubled down on independence discipline. Investor pressure "
            f"-{BALANCE.event_independence_reckoning_efficiency_pressure_relief}, covenant risk "
            f"-{BALANCE.event_independence_reckoning_efficiency_covenant_relief}."
        )

    if option_id == "take_bridge_flex":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand + BALANCE.event_independence_reckoning_bridge_cash_gain
        )
        state.finance.debt_principal = quantize_money(
            state.finance.debt_principal + BALANCE.event_independence_reckoning_bridge_debt_gain
        )
        state.finance.loan_interest_rate = clamp_rate(
            state.finance.loan_interest_rate
            + BALANCE.event_independence_reckoning_bridge_interest_gain
        )
        state.finance.investor_pressure = clamp_int(
            state.finance.investor_pressure
            + BALANCE.event_independence_reckoning_bridge_pressure_gain,
            0,
            100,
        )
        return (
            "You took a flexibility bridge. Cash "
            f"+{BALANCE.event_independence_reckoning_bridge_cash_gain}, debt "
            f"+{BALANCE.event_independence_reckoning_bridge_debt_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for independence reckoning.")


def _apply_independence_cash_crunch(state: GameState, event: PendingEvent, option_id: str) -> str:
    del event

    if option_id == "cut_to_reserve":
        shift = min(
            BALANCE.event_independence_cash_crunch_reserve_share_gain,
            state.capital_plan.go_to_market_share,
        )
        state.capital_plan = state.capital_plan.model_copy(
            update={
                "go_to_market_share": state.capital_plan.go_to_market_share - shift,
                "reserve_share": state.capital_plan.reserve_share + shift,
                "mode": CapitalPlanMode.CONSERVE,
            }
        )
        state.finance.board_pressure = clamp_int(
            state.finance.board_pressure
            - BALANCE.event_independence_cash_crunch_cut_pressure_relief,
            0,
            100,
        )
        state.finance.investor_pressure = clamp_int(
            state.finance.investor_pressure
            - BALANCE.event_independence_cash_crunch_cut_investor_relief,
            0,
            100,
        )
        state.company.reputation = clamp_int(
            state.company.reputation - BALANCE.event_independence_cash_crunch_cut_reputation_loss,
            0,
            100,
        )
        return (
            "You cut harder to reserve discipline. Reserve share "
            "+"
            f"{shift}, board pressure "
            f"-{BALANCE.event_independence_cash_crunch_cut_pressure_relief}."
        )

    if option_id == "roll_forward":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand + BALANCE.event_independence_cash_crunch_roll_cash_gain
        )
        state.finance.debt_principal = quantize_money(
            state.finance.debt_principal + BALANCE.event_independence_cash_crunch_roll_debt_gain
        )
        state.finance.loan_interest_rate = clamp_rate(
            state.finance.loan_interest_rate
            + BALANCE.event_independence_cash_crunch_roll_interest_gain
        )
        state.finance.investor_pressure = clamp_int(
            state.finance.investor_pressure
            + BALANCE.event_independence_cash_crunch_roll_pressure_gain,
            0,
            100,
        )
        return (
            "You rolled the cash crunch forward. Cash "
            f"+{BALANCE.event_independence_cash_crunch_roll_cash_gain}, debt "
            f"+{BALANCE.event_independence_cash_crunch_roll_debt_gain}."
        )

    raise ValueError(f"Unsupported option {option_id} for independence cash crunch.")


def _apply_strategic_crossroads(state: GameState, event: PendingEvent, option_id: str) -> str:
    product = _get_target_product(state, event)

    if option_id == "formalize_process":
        state.company.cash_on_hand = quantize_money(
            state.company.cash_on_hand - BALANCE.event_strategic_crossroads_process_cost
        )
        state.finance.board_confidence = clamp_int(
            state.finance.board_confidence
            + BALANCE.event_strategic_crossroads_process_confidence_gain,
            0,
            100,
        )
        state.finance.board_score = clamp_int(
            state.finance.board_score + BALANCE.event_strategic_crossroads_process_score_gain,
            0,
            100,
        )
        state.finance.investor_pressure = clamp_int(
            state.finance.investor_pressure
            + BALANCE.event_strategic_crossroads_process_pressure_gain,
            0,
            100,
        )
        return (
            f"You formalized the strategic path around {product.name}. Cash "
            f"-{BALANCE.event_strategic_crossroads_process_cost}, board confidence "
            f"+{BALANCE.event_strategic_crossroads_process_confidence_gain}."
        )

    if option_id == "defend_independence":
        state.company.reputation = clamp_int(
            state.company.reputation
            + BALANCE.event_strategic_crossroads_independence_reputation_gain,
            0,
            100,
        )
        state.finance.investor_pressure = clamp_int(
            state.finance.investor_pressure
            - BALANCE.event_strategic_crossroads_independence_pressure_relief,
            0,
            100,
        )
        state.finance.board_team_health_score = clamp_int(
            state.finance.board_team_health_score
            + BALANCE.event_strategic_crossroads_independence_team_gain,
            0,
            100,
        )
        return (
            f"You defended independence around {product.name}. Reputation "
            f"+{BALANCE.event_strategic_crossroads_independence_reputation_gain}, "
            "investor pressure "
            f"-{BALANCE.event_strategic_crossroads_independence_pressure_relief}."
        )

    raise ValueError(f"Unsupported option {option_id} for strategic crossroads.")


def _get_target_product(state: GameState, event: PendingEvent) -> Product:
    if event.target_product_id is None:
        raise ValueError("This event expected a product target.")
    return _get_product_by_id(state, event.target_product_id)


def _get_product_by_id(state: GameState, product_id: UUID) -> Product:
    for product in state.products:
        if product.id == product_id:
            return product
    raise ValueError("Event product target was not found.")


def _get_target_employee(state: GameState, event: PendingEvent) -> Employee:
    if event.target_employee_id is None:
        raise ValueError("This event expected an employee target.")
    for employee in state.employees:
        if employee.id == event.target_employee_id:
            return employee
    raise ValueError("Event employee target was not found.")


def _get_assigned_employees(state: GameState, product_id: UUID) -> list[Employee]:
    return [employee for employee in state.employees if employee.assigned_product_id == product_id]


def _get_active_accounts_for_product(state: GameState, product_id: UUID) -> list[CustomerAccount]:
    return [
        account
        for account in state.customer_accounts
        if account.product_id == product_id and account.status is not CustomerAccountStatus.CHURNED
    ]


def _get_most_conflicted_partnership(state: GameState, product_id: UUID):
    partnerships = [
        partnership
        for partnership in state.partnerships
        if partnership.product_id == product_id and partnership.status.value != "paused"
    ]
    if not partnerships:
        raise ValueError("This event expected an active partnership.")
    return max(
        partnerships,
        key=lambda partnership: partnership.conflict_pressure + partnership.risk,
    )


def _get_most_stressed_partnership(state: GameState, product_id: UUID):
    partnerships = [
        partnership
        for partnership in state.partnerships
        if partnership.product_id == product_id and partnership.status.value != "paused"
    ]
    if not partnerships:
        raise ValueError("This event expected an active partnership.")
    return max(
        partnerships,
        key=lambda partnership: calculate_partnership_fatigue(state, partnership),
    )


def _get_best_active_account_for_product(state: GameState, product_id: UUID) -> CustomerAccount:
    accounts = _get_active_accounts_for_product(state, product_id)
    if not accounts:
        raise ValueError("This event expected an active key account.")
    return max(accounts, key=lambda account: account.satisfaction + account.expansion_potential)


def _get_most_stressed_accounts(state: GameState, *, limit: int) -> list[CustomerAccount]:
    accounts = [
        account
        for account in state.customer_accounts
        if account.status is not CustomerAccountStatus.CHURNED
    ]
    return sorted(
        accounts,
        key=lambda account: (
            account.open_tickets
            + account.sla_breach_risk
            + account.ticket_queue_age
            + account.failed_payment_risk
            + account.escalation_count
        ),
        reverse=True,
    )[:limit]


def _get_primary_active_product(state: GameState) -> Product:
    active_products = [product for product in state.products if product.is_active]
    if not active_products:
        raise ValueError("This event expected at least one active product.")
    return max(
        active_products,
        key=lambda product: (
            product.user_count + product.market_fit + product.quality,
            -product.bug_level,
        ),
    )


EVENT_EFFECT_HANDLERS = {
    "severe_bug_incident": _apply_severe_bug_incident,
    "favorable_market_trend": _apply_favorable_market_trend,
    "investor_outreach": _apply_investor_outreach,
    "sudden_press_mention": _apply_sudden_press_mention,
    "team_burnout_spike": _apply_team_burnout_spike,
    "competitor_pressure": _apply_competitor_pressure,
    "referral_wave": _apply_referral_wave,
    "compliance_review": _apply_compliance_review,
    "support_backlog": _apply_support_backlog,
    "board_scrutiny": _apply_board_scrutiny,
    "renewal_risk": _apply_renewal_risk,
    "partner_offer": _apply_partner_offer,
    "channel_conflict": _apply_channel_conflict,
    "talent_bidding_war": _apply_talent_bidding_war,
    "platform_breakthrough": _apply_platform_breakthrough,
    "loan_covenant": _apply_loan_covenant,
    "down_round_pressure": _apply_down_round_pressure,
    "bridge_round": _apply_bridge_round,
    "key_account_expansion": _apply_key_account_expansion,
    "security_audit": _apply_security_audit,
    "enterprise_sales_cycle": _apply_enterprise_sales_cycle,
    "product_launch_window": _apply_product_launch_window,
    "platform_outage": _apply_platform_outage,
    "competitor_acquisition": _apply_competitor_acquisition,
    "regulatory_shift": _apply_regulatory_shift,
    "audit_followup_review": _apply_audit_followup_review,
    "launch_aftershock": _apply_launch_aftershock,
    "exit_interest": _apply_exit_interest,
    "public_market_scrutiny": _apply_public_market_scrutiny,
    "ipo_audit_committee": _apply_ipo_audit_committee,
    "acquirer_diligence": _apply_acquirer_diligence,
    "buyer_reference_check": _apply_buyer_reference_check,
    "independence_reckoning": _apply_independence_reckoning,
    "independence_cash_crunch": _apply_independence_cash_crunch,
    "enterprise_procurement_delay": _apply_enterprise_procurement_delay,
    "support_meltdown": _apply_support_meltdown,
    "board_reckoning": _apply_board_reckoning,
    "partner_qbr": _apply_partner_qbr,
    "partner_breakdown": _apply_partner_breakdown,
    "partner_renegotiation": _apply_partner_renegotiation,
    "board_recovery_window": _apply_board_recovery_window,
    "capital_market_freeze": _apply_capital_market_freeze,
    "succession_gap": _apply_succession_gap,
    "strategic_crossroads": _apply_strategic_crossroads,
}
