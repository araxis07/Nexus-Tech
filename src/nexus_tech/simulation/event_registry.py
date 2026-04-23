"""Registry and selection metadata for dynamic business events."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from nexus_tech.domain.models import (
    CustomerAccountStatus,
    Employee,
    EmployeeRole,
    EventCategory,
    EventOption,
    FundingType,
    GameState,
    MarketSegment,
    PendingEvent,
    Product,
)
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.finance import count_funding_rounds
from nexus_tech.simulation.operations import calculate_operations_summary
from nexus_tech.simulation.randomness import RandomLike
from nexus_tech.simulation.team import calculate_effective_productivity


@dataclass(frozen=True)
class EventDefinition:
    """Static event metadata used by the event engine."""

    event_id: str
    category: EventCategory
    weight: int
    cooldown_turns: int
    is_eligible: Callable[[GameState], bool]
    build_pending_event: Callable[[GameState, RandomLike, int], PendingEvent]


def get_event_registry() -> tuple[EventDefinition, ...]:
    """Return the full registry of supported events."""

    return (
        EventDefinition(
            event_id="severe_bug_incident",
            category=EventCategory.PRODUCT_INCIDENT,
            weight=BALANCE.event_bug_incident_weight,
            cooldown_turns=BALANCE.event_bug_incident_cooldown,
            is_eligible=_is_bug_incident_eligible,
            build_pending_event=_build_bug_incident_event,
        ),
        EventDefinition(
            event_id="favorable_market_trend",
            category=EventCategory.MARKET_OPPORTUNITY,
            weight=BALANCE.event_market_trend_weight,
            cooldown_turns=BALANCE.event_market_trend_cooldown,
            is_eligible=_is_market_trend_eligible,
            build_pending_event=_build_market_trend_event,
        ),
        EventDefinition(
            event_id="investor_outreach",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_investor_outreach_weight,
            cooldown_turns=BALANCE.event_investor_outreach_cooldown,
            is_eligible=_is_investor_outreach_eligible,
            build_pending_event=_build_investor_outreach_event,
        ),
        EventDefinition(
            event_id="sudden_press_mention",
            category=EventCategory.REPUTATION_INCIDENT,
            weight=BALANCE.event_press_mention_weight,
            cooldown_turns=BALANCE.event_press_mention_cooldown,
            is_eligible=_is_press_mention_eligible,
            build_pending_event=_build_press_mention_event,
        ),
        EventDefinition(
            event_id="team_burnout_spike",
            category=EventCategory.EMPLOYEE_ISSUE,
            weight=BALANCE.event_burnout_spike_weight,
            cooldown_turns=BALANCE.event_burnout_spike_cooldown,
            is_eligible=_is_burnout_spike_eligible,
            build_pending_event=_build_burnout_spike_event,
        ),
        EventDefinition(
            event_id="competitor_pressure",
            category=EventCategory.MARKET_OPPORTUNITY,
            weight=BALANCE.event_competitor_pressure_weight,
            cooldown_turns=BALANCE.event_competitor_pressure_cooldown,
            is_eligible=_is_competitor_pressure_eligible,
            build_pending_event=_build_competitor_pressure_event,
        ),
        EventDefinition(
            event_id="referral_wave",
            category=EventCategory.MARKET_OPPORTUNITY,
            weight=BALANCE.event_referral_wave_weight,
            cooldown_turns=BALANCE.event_referral_wave_cooldown,
            is_eligible=_is_referral_wave_eligible,
            build_pending_event=_build_referral_wave_event,
        ),
        EventDefinition(
            event_id="compliance_review",
            category=EventCategory.REPUTATION_INCIDENT,
            weight=BALANCE.event_compliance_review_weight,
            cooldown_turns=BALANCE.event_compliance_review_cooldown,
            is_eligible=_is_compliance_review_eligible,
            build_pending_event=_build_compliance_review_event,
        ),
        EventDefinition(
            event_id="support_backlog",
            category=EventCategory.PRODUCT_INCIDENT,
            weight=BALANCE.event_support_backlog_weight,
            cooldown_turns=BALANCE.event_support_backlog_cooldown,
            is_eligible=_is_support_backlog_eligible,
            build_pending_event=_build_support_backlog_event,
        ),
        EventDefinition(
            event_id="board_scrutiny",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_board_scrutiny_weight,
            cooldown_turns=BALANCE.event_board_scrutiny_cooldown,
            is_eligible=_is_board_scrutiny_eligible,
            build_pending_event=_build_board_scrutiny_event,
        ),
        EventDefinition(
            event_id="renewal_risk",
            category=EventCategory.PRODUCT_INCIDENT,
            weight=BALANCE.event_renewal_risk_weight,
            cooldown_turns=BALANCE.event_renewal_risk_cooldown,
            is_eligible=_is_renewal_risk_eligible,
            build_pending_event=_build_renewal_risk_event,
        ),
        EventDefinition(
            event_id="partner_offer",
            category=EventCategory.MARKET_OPPORTUNITY,
            weight=BALANCE.event_partner_offer_weight,
            cooldown_turns=BALANCE.event_partner_offer_cooldown,
            is_eligible=_is_partner_offer_eligible,
            build_pending_event=_build_partner_offer_event,
        ),
        EventDefinition(
            event_id="talent_bidding_war",
            category=EventCategory.EMPLOYEE_ISSUE,
            weight=BALANCE.event_talent_bidding_war_weight,
            cooldown_turns=BALANCE.event_talent_bidding_war_cooldown,
            is_eligible=_is_talent_bidding_war_eligible,
            build_pending_event=_build_talent_bidding_war_event,
        ),
        EventDefinition(
            event_id="platform_breakthrough",
            category=EventCategory.MARKET_OPPORTUNITY,
            weight=BALANCE.event_platform_breakthrough_weight,
            cooldown_turns=BALANCE.event_platform_breakthrough_cooldown,
            is_eligible=_is_platform_breakthrough_eligible,
            build_pending_event=_build_platform_breakthrough_event,
        ),
        EventDefinition(
            event_id="loan_covenant",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_loan_covenant_weight,
            cooldown_turns=BALANCE.event_loan_covenant_cooldown,
            is_eligible=_is_loan_covenant_eligible,
            build_pending_event=_build_loan_covenant_event,
        ),
        EventDefinition(
            event_id="down_round_pressure",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_down_round_pressure_weight,
            cooldown_turns=BALANCE.event_down_round_pressure_cooldown,
            is_eligible=_is_down_round_pressure_eligible,
            build_pending_event=_build_down_round_pressure_event,
        ),
        EventDefinition(
            event_id="key_account_expansion",
            category=EventCategory.MARKET_OPPORTUNITY,
            weight=BALANCE.event_key_account_expansion_weight,
            cooldown_turns=BALANCE.event_key_account_expansion_cooldown,
            is_eligible=_is_key_account_expansion_eligible,
            build_pending_event=_build_key_account_expansion_event,
        ),
        EventDefinition(
            event_id="security_audit",
            category=EventCategory.REPUTATION_INCIDENT,
            weight=BALANCE.event_security_audit_weight,
            cooldown_turns=BALANCE.event_security_audit_cooldown,
            is_eligible=_is_security_audit_eligible,
            build_pending_event=_build_security_audit_event,
        ),
        EventDefinition(
            event_id="enterprise_sales_cycle",
            category=EventCategory.MARKET_OPPORTUNITY,
            weight=BALANCE.event_enterprise_sales_cycle_weight,
            cooldown_turns=BALANCE.event_enterprise_sales_cycle_cooldown,
            is_eligible=_is_enterprise_sales_cycle_eligible,
            build_pending_event=_build_enterprise_sales_cycle_event,
        ),
        EventDefinition(
            event_id="product_launch_window",
            category=EventCategory.MARKET_OPPORTUNITY,
            weight=BALANCE.event_product_launch_window_weight,
            cooldown_turns=BALANCE.event_product_launch_window_cooldown,
            is_eligible=_is_product_launch_window_eligible,
            build_pending_event=_build_product_launch_window_event,
        ),
        EventDefinition(
            event_id="platform_outage",
            category=EventCategory.PRODUCT_INCIDENT,
            weight=BALANCE.event_platform_outage_weight,
            cooldown_turns=BALANCE.event_platform_outage_cooldown,
            is_eligible=_is_platform_outage_eligible,
            build_pending_event=_build_platform_outage_event,
        ),
        EventDefinition(
            event_id="competitor_acquisition",
            category=EventCategory.MARKET_OPPORTUNITY,
            weight=BALANCE.event_competitor_acquisition_weight,
            cooldown_turns=BALANCE.event_competitor_acquisition_cooldown,
            is_eligible=_is_competitor_acquisition_eligible,
            build_pending_event=_build_competitor_acquisition_event,
        ),
        EventDefinition(
            event_id="regulatory_shift",
            category=EventCategory.REPUTATION_INCIDENT,
            weight=BALANCE.event_regulatory_shift_weight,
            cooldown_turns=BALANCE.event_regulatory_shift_cooldown,
            is_eligible=_is_regulatory_shift_eligible,
            build_pending_event=_build_regulatory_shift_event,
        ),
        EventDefinition(
            event_id="audit_followup_review",
            category=EventCategory.REPUTATION_INCIDENT,
            weight=BALANCE.event_audit_followup_weight,
            cooldown_turns=BALANCE.event_audit_followup_cooldown,
            is_eligible=_is_audit_followup_review_eligible,
            build_pending_event=_build_audit_followup_review_event,
        ),
        EventDefinition(
            event_id="launch_aftershock",
            category=EventCategory.MARKET_OPPORTUNITY,
            weight=BALANCE.event_launch_aftershock_weight,
            cooldown_turns=BALANCE.event_launch_aftershock_cooldown,
            is_eligible=_is_launch_aftershock_eligible,
            build_pending_event=_build_launch_aftershock_event,
        ),
        EventDefinition(
            event_id="enterprise_procurement_delay",
            category=EventCategory.MARKET_OPPORTUNITY,
            weight=BALANCE.event_procurement_delay_weight,
            cooldown_turns=BALANCE.event_procurement_delay_cooldown,
            is_eligible=_is_enterprise_procurement_delay_eligible,
            build_pending_event=_build_enterprise_procurement_delay_event,
        ),
    )


def _is_bug_incident_eligible(state: GameState) -> bool:
    return any(
        product.is_active
        and (
            product.bug_level >= BALANCE.event_bug_incident_bug_threshold
            or product.technical_debt >= BALANCE.event_bug_incident_debt_threshold
        )
        for product in state.products
    )


def _build_bug_incident_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [
            product
            for product in state.products
            if product.is_active
            and (
                product.bug_level >= BALANCE.event_bug_incident_bug_threshold
                or product.technical_debt >= BALANCE.event_bug_incident_debt_threshold
            )
        ],
        rng,
        score=lambda product: product.bug_level + product.technical_debt,
    )
    return PendingEvent(
        event_id="severe_bug_incident",
        category=EventCategory.PRODUCT_INCIDENT,
        title="Severe Bug Incident",
        description=(
            f"{target.name} is taking heat from a visible defect spike. "
            "You can pay for a fast containment push or absorb the public damage."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        target_product_id=target.id,
        options=[
            EventOption(
                id="hotfix",
                label="Fund an emergency hotfix",
                description="Pay cash, burn team energy, and contain the damage.",
            ),
            EventOption(
                id="delay",
                label="Delay and manage the fallout",
                description="Save cash now, but let users and reputation take the hit.",
            ),
        ],
    )


def _is_market_trend_eligible(state: GameState) -> bool:
    return any(
        product.is_active and product.market_fit >= BALANCE.event_market_trend_fit_threshold
        for product in state.products
    )


def _build_market_trend_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [
            product
            for product in state.products
            if product.is_active and product.market_fit >= BALANCE.event_market_trend_fit_threshold
        ],
        rng,
        score=lambda product: product.market_fit + (product.user_count // 8),
    )
    return PendingEvent(
        event_id="favorable_market_trend",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Favorable Market Trend",
        description=(
            f"Demand is rising around {target.name}. "
            "You can lean into the moment or take a smaller win without straining the team."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        target_product_id=target.id,
        options=[
            EventOption(
                id="lean_in",
                label="Lean into the trend",
                description="Spend cash for a stronger user spike and better acquisition.",
            ),
            EventOption(
                id="bank_it",
                label="Take the lighter win",
                description="Capture some upside without extra cost or pressure.",
            ),
        ],
    )


def _is_investor_outreach_eligible(state: GameState) -> bool:
    return (
        state.company.current_turn >= 3
        and count_funding_rounds(state.funding_history, FundingType.ANGEL)
        < BALANCE.finance_angel_round_limit
        and (
            state.company.reputation >= BALANCE.event_investor_reputation_threshold
            or state.company.cash_on_hand <= BALANCE.event_investor_cash_threshold
        )
    )


def _build_investor_outreach_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    return PendingEvent(
        event_id="investor_outreach",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Investor Outreach",
        description=(
            "A small investor wants to talk after seeing your recent traction. "
            "Fresh cash is available, but it will also add pressure to the team."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        options=[
            EventOption(
                id="take_capital",
                label="Take the meeting and close fast",
                description="Increase cash now, but the team feels the added pressure.",
            ),
            EventOption(
                id="stay_bootstrapped",
                label="Stay bootstrapped",
                description="Skip the cash and keep the team focused and calmer.",
            ),
        ],
    )


def _is_press_mention_eligible(state: GameState) -> bool:
    return any(
        product.is_active
        and (
            product.market_fit >= BALANCE.event_press_market_fit_threshold
            or product.user_count >= BALANCE.event_competitor_pressure_user_threshold
        )
        for product in state.products
    )


def _build_press_mention_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [
            product
            for product in state.products
            if product.is_active
            and (
                product.market_fit >= BALANCE.event_press_market_fit_threshold
                or product.user_count >= BALANCE.event_competitor_pressure_user_threshold
            )
        ],
        rng,
        score=lambda product: product.market_fit + (product.user_count // 10),
    )
    return PendingEvent(
        event_id="sudden_press_mention",
        category=EventCategory.REPUTATION_INCIDENT,
        title="Sudden Press Mention",
        description=(
            f"A niche outlet picked up {target.name}. "
            "The attention should convert into curiosity right away."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="launch_chain",
        chain_stage=1,
        target_product_id=target.id,
        options=[
            EventOption(
                id="ride_the_wave",
                label="Ride the wave",
                description="Take the lift in reputation and incoming traffic.",
            )
        ],
    )


def _is_burnout_spike_eligible(state: GameState) -> bool:
    return any(
        employee.energy <= BALANCE.event_burnout_spike_energy_threshold
        or employee.morale <= BALANCE.event_burnout_spike_morale_threshold
        for employee in state.employees
    )


def _build_burnout_spike_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_employee(
        [
            employee
            for employee in state.employees
            if employee.energy <= BALANCE.event_burnout_spike_energy_threshold
            or employee.morale <= BALANCE.event_burnout_spike_morale_threshold
        ],
        rng,
        score=lambda employee: -(employee.energy + employee.morale),
    )
    return PendingEvent(
        event_id="team_burnout_spike",
        category=EventCategory.EMPLOYEE_ISSUE,
        title="Team Burnout Spike",
        description=(
            f"{target.full_name} is close to burning out, and the tension is visible. "
            "You can intervene now or squeeze a little more output and accept the risk."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        target_employee_id=target.id,
        target_product_id=target.assigned_product_id,
        options=[
            EventOption(
                id="cool_off",
                label="Fund recovery time",
                description="Spend cash to restore energy and morale.",
            ),
            EventOption(
                id="push_through",
                label="Push through the crunch",
                description="Save cash, but risk product quality and team condition.",
            ),
        ],
    )


def _is_competitor_pressure_eligible(state: GameState) -> bool:
    return any(
        product.is_active and product.user_count >= BALANCE.event_competitor_pressure_user_threshold
        for product in state.products
    )


def _build_competitor_pressure_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [
            product
            for product in state.products
            if product.is_active
            and product.user_count >= BALANCE.event_competitor_pressure_user_threshold
        ],
        rng,
        score=lambda product: product.user_count + product.market_fit,
    )
    return PendingEvent(
        event_id="competitor_pressure",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Competitor Pressure",
        description=(
            f"A rival is making noise in {target.name}'s lane. "
            "You can rush a response or sharpen the product and defend the brand."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        target_product_id=target.id,
        options=[
            EventOption(
                id="rush_countermove",
                label="Rush a counter-move",
                description="Ship faster, but accept more bugs, debt, and team strain.",
            ),
            EventOption(
                id="differentiate",
                label="Differentiate on quality",
                description="Defend the brand with product quality, even if growth pauses.",
            ),
        ],
    )


def _is_referral_wave_eligible(state: GameState) -> bool:
    return any(
        product.is_active
        and product.quality >= BALANCE.event_referral_quality_threshold
        and product.bug_level <= BALANCE.event_referral_bug_threshold
        and product.market_fit >= BALANCE.event_referral_market_fit_threshold
        for product in state.products
    )


def _build_referral_wave_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [
            product
            for product in state.products
            if product.is_active
            and product.quality >= BALANCE.event_referral_quality_threshold
            and product.bug_level <= BALANCE.event_referral_bug_threshold
            and product.market_fit >= BALANCE.event_referral_market_fit_threshold
        ],
        rng,
        score=lambda product: product.quality + product.market_fit + (product.user_count // 10),
    )
    return PendingEvent(
        event_id="referral_wave",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Customer Referral Wave",
        description=(
            f"Happy customers are starting to refer {target.name}. "
            "You can staff the wave for a stronger conversion bump or protect service levels "
            "and take a smaller, cleaner gain."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        target_product_id=target.id,
        options=[
            EventOption(
                id="staff_referrals",
                label="Staff the referral wave",
                description="Spend cash to support the influx and convert more users quickly.",
            ),
            EventOption(
                id="protect_service",
                label="Protect service quality",
                description="Take a smaller gain while improving product stability for retention.",
            ),
        ],
    )


def _is_compliance_review_eligible(state: GameState) -> bool:
    return any(
        product.is_active
        and product.target_segment.value == "enterprise"
        and (
            product.user_count >= BALANCE.event_compliance_target_user_threshold
            or product.market_fit >= BALANCE.event_compliance_market_fit_threshold
        )
        and product.technical_debt >= BALANCE.event_compliance_debt_threshold
        for product in state.products
    )


def _build_compliance_review_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [
            product
            for product in state.products
            if product.is_active
            and product.target_segment.value == "enterprise"
            and (
                product.user_count >= BALANCE.event_compliance_target_user_threshold
                or product.market_fit >= BALANCE.event_compliance_market_fit_threshold
            )
            and product.technical_debt >= BALANCE.event_compliance_debt_threshold
        ],
        rng,
        score=lambda product: product.technical_debt + product.market_fit + product.user_count,
    )
    return PendingEvent(
        event_id="compliance_review",
        category=EventCategory.REPUTATION_INCIDENT,
        title="Compliance Review Request",
        description=(
            f"A larger buyer is asking hard questions about {target.name}. "
            "You can fund a focused compliance sprint now or defer the work "
            "and absorb the trust hit."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        target_product_id=target.id,
        options=[
            EventOption(
                id="fund_review",
                label="Fund a compliance sprint",
                description="Spend cash to reduce debt, improve fit, and build enterprise trust.",
            ),
            EventOption(
                id="defer_review",
                label="Defer and keep shipping",
                description="Save cash now, but risk user loss and weaker market confidence.",
            ),
        ],
    )


def _is_support_backlog_eligible(state: GameState) -> bool:
    summary = calculate_operations_summary(
        state.products,
        state.employees,
        current_turn=state.company.current_turn,
    )
    return summary.overload >= BALANCE.operations_moderate_overload_threshold and any(
        product.is_active
        and product.user_count >= BALANCE.event_support_backlog_user_threshold
        and product.bug_level >= BALANCE.event_support_backlog_bug_threshold
        for product in state.products
    )


def _build_support_backlog_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [
            product
            for product in state.products
            if product.is_active
            and product.user_count >= BALANCE.event_support_backlog_user_threshold
            and product.bug_level >= BALANCE.event_support_backlog_bug_threshold
        ],
        rng,
        score=lambda product: product.user_count + product.bug_level + product.technical_debt,
    )
    return PendingEvent(
        event_id="support_backlog",
        category=EventCategory.PRODUCT_INCIDENT,
        title="Support Backlog Surge",
        description=(
            f"{target.name} is building a visible support backlog. "
            "You can fund a focused cleanup sprint or keep pushing features and absorb the drag."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        target_product_id=target.id,
        options=[
            EventOption(
                id="stabilize_ops",
                label="Fund the support cleanup",
                description="Spend cash to stabilize churn, morale, and bug pressure.",
            ),
            EventOption(
                id="keep_shipping",
                label="Keep shipping through it",
                description="Save cash now, but accept reputation and user loss.",
            ),
        ],
    )


def _is_board_scrutiny_eligible(state: GameState) -> bool:
    return state.company.current_turn >= BALANCE.event_board_scrutiny_turn_threshold and (
        state.finance.investor_pressure >= BALANCE.event_board_scrutiny_pressure_threshold
        or state.finance.debt_principal >= BALANCE.event_board_scrutiny_debt_threshold
    )


def _build_board_scrutiny_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    return PendingEvent(
        event_id="board_scrutiny",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Board Scrutiny",
        description=(
            "Investors want a cleaner story around execution and capital discipline. "
            "You can present a reset plan or overpromise growth and accept the added pressure."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        options=[
            EventOption(
                id="publish_plan",
                label="Publish a disciplined reset plan",
                description="Spend some cash now to reduce pressure and steady the team.",
            ),
            EventOption(
                id="promise_growth",
                label="Promise faster growth",
                description="Bring in a small cash bump, but investors will expect more.",
            ),
        ],
    )


def _is_renewal_risk_eligible(state: GameState) -> bool:
    return state.company.current_turn >= BALANCE.event_renewal_risk_turn_threshold and any(
        product.is_active
        and product.user_count >= BALANCE.event_renewal_risk_user_threshold
        and (
            product.bug_level >= BALANCE.event_renewal_risk_bug_threshold
            or product.technical_debt >= BALANCE.event_renewal_risk_debt_threshold
        )
        for product in state.products
    )


def _build_renewal_risk_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [
            product
            for product in state.products
            if product.is_active
            and product.user_count >= BALANCE.event_renewal_risk_user_threshold
            and (
                product.bug_level >= BALANCE.event_renewal_risk_bug_threshold
                or product.technical_debt >= BALANCE.event_renewal_risk_debt_threshold
            )
        ],
        rng,
        score=lambda product: product.user_count + product.bug_level + product.technical_debt,
    )
    return PendingEvent(
        event_id="renewal_risk",
        category=EventCategory.PRODUCT_INCIDENT,
        title="Renewal Risk",
        description=(
            f"A larger block of {target.name} customers is approaching renewal. "
            "You can fund a reliability push now or keep most of them with short-term discounts."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        target_product_id=target.id,
        options=[
            EventOption(
                id="stabilize_renewals",
                label="Fund a reliability push",
                description="Spend cash to clean up the renewal story and reduce product drag.",
            ),
            EventOption(
                id="offer_discounts",
                label="Offer renewal discounts",
                description="Save the account volume now, but weaken revenue quality.",
            ),
        ],
    )


def _is_partner_offer_eligible(state: GameState) -> bool:
    return state.company.current_turn >= BALANCE.event_partner_offer_turn_threshold and any(
        product.is_active
        and product.market_fit >= BALANCE.event_partner_offer_market_fit_threshold
        and product.quality >= BALANCE.event_partner_offer_quality_threshold
        for product in state.products
    )


def _build_partner_offer_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [
            product
            for product in state.products
            if product.is_active
            and product.market_fit >= BALANCE.event_partner_offer_market_fit_threshold
            and product.quality >= BALANCE.event_partner_offer_quality_threshold
        ],
        rng,
        score=lambda product: product.market_fit + product.quality + product.user_count,
    )
    return PendingEvent(
        event_id="partner_offer",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Channel Partner Offer",
        description=(
            f"A reseller wants to take {target.name} into a new set of accounts. "
            "You can sign the channel deal for immediate expansion or stay direct "
            "and sharpen the product."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        target_product_id=target.id,
        options=[
            EventOption(
                id="sign_partner",
                label="Sign the partner deal",
                description=(
                    "Take cash, users, and acquisition lift at the cost of more operating noise."
                ),
            ),
            EventOption(
                id="stay_direct",
                label="Stay direct and focused",
                description=(
                    "Skip the channel bump and invest the attention back into product depth."
                ),
            ),
        ],
    )


def _is_talent_bidding_war_eligible(state: GameState) -> bool:
    return (
        state.company.current_turn >= BALANCE.event_talent_bidding_war_turn_threshold
        and len(state.employees) >= BALANCE.event_talent_bidding_war_headcount_threshold
    )


def _build_talent_bidding_war_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_employee(
        state.employees,
        rng,
        score=lambda employee: calculate_effective_productivity(employee) + employee.morale,
    )
    return PendingEvent(
        event_id="talent_bidding_war",
        category=EventCategory.EMPLOYEE_ISSUE,
        title="Talent Bidding War",
        description=(
            f"A competitor is trying to poach {target.full_name}. "
            "You can pay to retain the team mood or hold the line and accept some morale drag."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        target_employee_id=target.id,
        options=[
            EventOption(
                id="retain_team",
                label="Spend to retain the team",
                description="Pay cash to steady morale and reduce the temperature.",
            ),
            EventOption(
                id="hold_line",
                label="Hold the line",
                description="Keep cash now, but accept an energy and morale hit across the team.",
            ),
        ],
    )


def _is_platform_breakthrough_eligible(state: GameState) -> bool:
    return any(
        product.is_active
        and product.quality >= BALANCE.event_platform_breakthrough_quality_threshold
        and product.technical_debt <= BALANCE.event_platform_breakthrough_debt_threshold
        for product in state.products
    )


def _build_platform_breakthrough_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [
            product
            for product in state.products
            if product.is_active
            and product.quality >= BALANCE.event_platform_breakthrough_quality_threshold
            and product.technical_debt <= BALANCE.event_platform_breakthrough_debt_threshold
        ],
        rng,
        score=lambda product: product.quality + product.market_fit - product.technical_debt,
    )
    return PendingEvent(
        event_id="platform_breakthrough",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Platform Breakthrough",
        description=(
            f"The team uncovered a cleaner platform improvement path inside {target.name}. "
            "You can productize it now for a market payoff "
            "or keep it internal and reduce future drag."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        target_product_id=target.id,
        options=[
            EventOption(
                id="productize_breakthrough",
                label="Productize the breakthrough",
                description=(
                    "Spend cash now to turn the internal gain into product and growth leverage."
                ),
            ),
            EventOption(
                id="bank_the_gain",
                label="Keep the gain internal",
                description="Use the improvement to quietly reduce bugs and debt instead.",
            ),
        ],
    )


def _is_loan_covenant_eligible(state: GameState) -> bool:
    return (
        state.finance.debt_principal >= BALANCE.event_loan_covenant_debt_threshold
        and state.company.cash_on_hand <= BALANCE.event_loan_covenant_cash_threshold
    )


def _build_loan_covenant_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    return PendingEvent(
        event_id="loan_covenant",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Loan Covenant Pressure",
        description=(
            "Your lender wants more discipline around the current debt load. "
            "You can pay debt down now or renegotiate and accept a worse capital posture."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        options=[
            EventOption(
                id="paydown_now",
                label="Pay debt down now",
                description="Spend cash to reduce debt and calm covenant pressure.",
            ),
            EventOption(
                id="renegotiate_terms",
                label="Renegotiate the loan",
                description="Keep more cash now, but accept higher interest and pressure.",
            ),
        ],
    )


def _is_down_round_pressure_eligible(state: GameState) -> bool:
    return (
        state.company.current_turn >= BALANCE.event_down_round_pressure_turn_threshold
        and state.company.cash_on_hand <= BALANCE.event_down_round_pressure_cash_threshold
        and state.finance.investor_pressure >= BALANCE.event_down_round_pressure_investor_threshold
        and (
            count_funding_rounds(state.funding_history, FundingType.ANGEL) > 0
            or count_funding_rounds(state.funding_history, FundingType.VENTURE) > 0
        )
    )


def _build_down_round_pressure_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    return PendingEvent(
        event_id="down_round_pressure",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Down Round Pressure",
        description=(
            "Existing investors think the company needs a bridge round. "
            "You can accept the dilution or stay independent and defend the story."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        options=[
            EventOption(
                id="take_bridge",
                label="Take the bridge round",
                description="Add cash quickly, but take dilution and more investor pressure.",
            ),
            EventOption(
                id="stay_independent",
                label="Stay independent",
                description="Protect the cap table, but accept some narrative damage.",
            ),
        ],
    )


def _is_key_account_expansion_eligible(state: GameState) -> bool:
    return any(
        account.status is not CustomerAccountStatus.CHURNED
        and account.satisfaction >= BALANCE.event_key_account_expansion_satisfaction_threshold
        and account.expansion_potential >= BALANCE.event_key_account_expansion_potential_threshold
        and _get_product_by_id(state.products, account.product_id) is not None
        for account in state.customer_accounts
    )


def _build_key_account_expansion_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    eligible_accounts = [
        account
        for account in state.customer_accounts
        if account.status is not CustomerAccountStatus.CHURNED
        and account.satisfaction >= BALANCE.event_key_account_expansion_satisfaction_threshold
        and account.expansion_potential >= BALANCE.event_key_account_expansion_potential_threshold
        and _get_product_by_id(state.products, account.product_id) is not None
    ]
    best_score = max(
        account.satisfaction + account.expansion_potential for account in eligible_accounts
    )
    candidates = [
        account
        for account in eligible_accounts
        if account.satisfaction + account.expansion_potential == best_score
    ]
    account = candidates[rng.randint(0, len(candidates) - 1)]
    product = _get_product_by_id(state.products, account.product_id)
    if product is None:
        raise ValueError("Key account expansion expected a product target.")

    return PendingEvent(
        event_id="key_account_expansion",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Key Account Expansion",
        description=(
            f"{account.name} wants more value from {product.name}. "
            "You can fund a success plan or push for referrals while the account is warm."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        target_product_id=product.id,
        options=[
            EventOption(
                id="build_success_plan",
                label="Build a success plan",
                description="Spend cash to expand the contract and protect satisfaction.",
            ),
            EventOption(
                id="ask_for_referral",
                label="Ask for a referral",
                description="Turn customer warmth into growth, with some relationship strain.",
            ),
        ],
    )


def _is_security_audit_eligible(state: GameState) -> bool:
    return any(
        product.is_active
        and product.target_segment is MarketSegment.ENTERPRISE
        and (
            product.user_count >= BALANCE.event_security_audit_user_threshold
            or product.technical_debt >= BALANCE.event_security_audit_debt_threshold
        )
        for product in state.products
    )


def _build_security_audit_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [
            product
            for product in state.products
            if product.is_active
            and product.target_segment is MarketSegment.ENTERPRISE
            and (
                product.user_count >= BALANCE.event_security_audit_user_threshold
                or product.technical_debt >= BALANCE.event_security_audit_debt_threshold
            )
        ],
        rng,
        score=lambda product: product.user_count + product.technical_debt + product.bug_level,
    )
    return PendingEvent(
        event_id="security_audit",
        category=EventCategory.REPUTATION_INCIDENT,
        title="Security Audit Request",
        description=(
            f"Enterprise buyers want stronger security evidence for {target.name}. "
            "You can fund the audit or defer and absorb trust damage."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="trust_chain",
        chain_stage=1,
        target_product_id=target.id,
        options=[
            EventOption(
                id="fund_audit",
                label="Fund the audit",
                description="Spend cash to lower risk and improve enterprise trust.",
            ),
            EventOption(
                id="defer_audit",
                label="Defer the audit",
                description="Save cash now, but increase churn and renewal risk.",
            ),
        ],
    )


def _is_enterprise_sales_cycle_eligible(state: GameState) -> bool:
    return state.company.current_turn >= BALANCE.event_enterprise_sales_turn_threshold and any(
        product.is_active
        and product.target_segment is MarketSegment.ENTERPRISE
        and product.market_fit >= BALANCE.event_enterprise_sales_fit_threshold
        and product.user_count >= BALANCE.event_enterprise_sales_user_threshold
        for product in state.products
    )


def _build_enterprise_sales_cycle_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [
            product
            for product in state.products
            if product.is_active
            and product.target_segment is MarketSegment.ENTERPRISE
            and product.market_fit >= BALANCE.event_enterprise_sales_fit_threshold
            and product.user_count >= BALANCE.event_enterprise_sales_user_threshold
        ],
        rng,
        score=lambda product: product.market_fit + product.quality + product.user_count,
    )
    return PendingEvent(
        event_id="enterprise_sales_cycle",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Enterprise Sales Cycle",
        description=(
            f"A serious enterprise buyer wants a proof-of-concept for {target.name}. "
            "You can fund the cycle or walk away to protect focus."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="enterprise_sales_chain",
        chain_stage=1,
        target_product_id=target.id,
        options=[
            EventOption(
                id="fund_poc",
                label="Fund the proof-of-concept",
                description="Spend cash and team energy for users, contract value, and fit.",
            ),
            EventOption(
                id="walk_away",
                label="Walk away",
                description="Protect focus and board trust, but skip the growth moment.",
            ),
        ],
    )


def _is_product_launch_window_eligible(state: GameState) -> bool:
    return any(
        product.is_active
        and product.quality >= BALANCE.event_product_launch_quality_threshold
        and product.market_fit >= BALANCE.event_product_launch_fit_threshold
        and product.feature_count >= BALANCE.event_product_launch_feature_threshold
        for product in state.products
    )


def _build_product_launch_window_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [
            product
            for product in state.products
            if product.is_active
            and product.quality >= BALANCE.event_product_launch_quality_threshold
            and product.market_fit >= BALANCE.event_product_launch_fit_threshold
            and product.feature_count >= BALANCE.event_product_launch_feature_threshold
        ],
        rng,
        score=lambda product: product.quality + product.market_fit + product.feature_count,
    )
    return PendingEvent(
        event_id="product_launch_window",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Product Launch Window",
        description=(
            f"{target.name} has enough readiness for a launch moment. "
            "You can push a full campaign or soft-launch to protect quality."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="launch_chain",
        chain_stage=1,
        target_product_id=target.id,
        options=[
            EventOption(
                id="launch_campaign",
                label="Launch hard",
                description="Spend cash for demand, but accept a little operational noise.",
            ),
            EventOption(
                id="soft_launch",
                label="Soft-launch",
                description="Take a smaller user bump while improving quality signal.",
            ),
        ],
    )


def _is_platform_outage_eligible(state: GameState) -> bool:
    return any(
        product.is_active
        and (
            product.user_count >= BALANCE.event_platform_outage_user_threshold
            or (
                product.bug_level >= BALANCE.event_platform_outage_bug_threshold
                and product.technical_debt >= BALANCE.event_platform_outage_debt_threshold
            )
        )
        for product in state.products
    )


def _build_platform_outage_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [
            product
            for product in state.products
            if product.is_active
            and (
                product.user_count >= BALANCE.event_platform_outage_user_threshold
                or (
                    product.bug_level >= BALANCE.event_platform_outage_bug_threshold
                    and product.technical_debt >= BALANCE.event_platform_outage_debt_threshold
                )
            )
        ],
        rng,
        score=lambda product: product.user_count + product.bug_level + product.technical_debt,
    )
    return PendingEvent(
        event_id="platform_outage",
        category=EventCategory.PRODUCT_INCIDENT,
        title="Platform Outage",
        description=(
            f"{target.name} suffered reliability trouble. "
            "You can run a costly response or minimize spend and absorb trust damage."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        target_product_id=target.id,
        options=[
            EventOption(
                id="all_hands_recovery",
                label="All-hands recovery",
                description="Spend cash and energy to reduce bugs and contain reputation loss.",
            ),
            EventOption(
                id="minimize_cost",
                label="Minimize cost",
                description="Save cash now, but lose users and worsen trust.",
            ),
        ],
    )


def _is_competitor_acquisition_eligible(state: GameState) -> bool:
    return (
        state.company.current_turn >= BALANCE.event_competitor_acquisition_turn_threshold
        and any(product.is_active for product in state.products)
        and bool(state.competitors)
        and any(
            competitor.funding_level >= BALANCE.event_competitor_acquisition_funding_threshold
            or competitor.momentum >= BALANCE.event_competitor_acquisition_momentum_threshold
            for competitor in state.competitors
        )
    )


def _build_competitor_acquisition_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    rival = max(
        state.competitors,
        key=lambda competitor: competitor.funding_level + competitor.momentum + competitor.strength,
    )
    return PendingEvent(
        event_id="competitor_acquisition",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Competitor Acquisition",
        description=(
            f"{rival.name} was pulled into a larger platform. "
            "The market is noisier, but their integration risk creates an opening."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        options=[
            EventOption(
                id="differentiate_against_stack",
                label="Differentiate against the stack",
                description="Spend cash to sharpen product positioning against the new bundle.",
            ),
            EventOption(
                id="seek_distribution_partner",
                label="Seek a distribution partner",
                description="Gain users and reputation, but accept more rival capital pressure.",
            ),
        ],
    )


def _is_regulatory_shift_eligible(state: GameState) -> bool:
    return state.company.current_turn >= BALANCE.event_regulatory_shift_turn_threshold and any(
        product.is_active and product.target_segment is MarketSegment.ENTERPRISE
        for product in state.products
    )


def _build_regulatory_shift_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [
            product
            for product in state.products
            if product.is_active and product.target_segment is MarketSegment.ENTERPRISE
        ],
        rng,
        score=lambda product: product.user_count + product.market_fit + product.technical_debt,
    )
    return PendingEvent(
        event_id="regulatory_shift",
        category=EventCategory.REPUTATION_INCIDENT,
        title="Regulatory Shift",
        description=(
            f"New buyer requirements landed around {target.name}. "
            "You can invest early controls or wait for clarity."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="trust_chain",
        chain_stage=1,
        target_product_id=target.id,
        options=[
            EventOption(
                id="proactive_controls",
                label="Invest in controls",
                description="Spend cash to improve trust, fit, and board confidence.",
            ),
            EventOption(
                id="wait_for_clarity",
                label="Wait for clarity",
                description="Avoid immediate spend but increase churn and account risk.",
            ),
        ],
    )


def _is_audit_followup_review_eligible(state: GameState) -> bool:
    return _has_recent_event(
        state,
        {"security_audit", "regulatory_shift"},
        BALANCE.event_chain_recent_window_turns,
    ) and any(
        product.is_active and product.target_segment is MarketSegment.ENTERPRISE
        for product in state.products
    )


def _build_audit_followup_review_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [
            product
            for product in state.products
            if product.is_active and product.target_segment is MarketSegment.ENTERPRISE
        ],
        rng,
        score=lambda product: product.market_fit + product.quality - product.technical_debt,
    )
    return PendingEvent(
        event_id="audit_followup_review",
        category=EventCategory.REPUTATION_INCIDENT,
        title="Audit Follow-up Review",
        description=(
            f"Enterprise buyers want proof that {target.name} can sustain recent control work. "
            "You can package evidence now or defer and accept more renewal risk."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="trust_chain",
        chain_stage=2,
        target_product_id=target.id,
        options=[
            EventOption(
                id="package_evidence",
                label="Package audit evidence",
                description="Spend cash for trust, board confidence, and lower technical debt.",
            ),
            EventOption(
                id="defer_followup",
                label="Defer the follow-up",
                description="Avoid spend, but key accounts become more nervous.",
            ),
        ],
    )


def _is_launch_aftershock_eligible(state: GameState) -> bool:
    return _has_recent_event(
        state,
        {"product_launch_window", "sudden_press_mention"},
        BALANCE.event_chain_recent_window_turns,
    ) and any(product.is_active and product.user_count >= 20 for product in state.products)


def _build_launch_aftershock_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [product for product in state.products if product.is_active and product.user_count >= 20],
        rng,
        score=lambda product: product.user_count + product.market_fit,
    )
    return PendingEvent(
        event_id="launch_aftershock",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Launch Aftershock",
        description=(
            f"Attention around {target.name} is still moving. "
            "You can stabilize the experience or chase a second wave of demand."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="launch_chain",
        chain_stage=2,
        target_product_id=target.id,
        options=[
            EventOption(
                id="stabilize_experience",
                label="Stabilize the experience",
                description="Spend cash to improve quality and reduce bug risk.",
            ),
            EventOption(
                id="chase_second_wave",
                label="Chase the second wave",
                description="Gain users quickly, but add bugs and team strain.",
            ),
        ],
    )


def _is_enterprise_procurement_delay_eligible(state: GameState) -> bool:
    return _has_recent_event(
        state,
        {"enterprise_sales_cycle", "key_account_expansion"},
        BALANCE.event_chain_recent_window_turns,
    ) and any(
        product.is_active and product.target_segment is MarketSegment.ENTERPRISE
        for product in state.products
    )


def _build_enterprise_procurement_delay_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [
            product
            for product in state.products
            if product.is_active and product.target_segment is MarketSegment.ENTERPRISE
        ],
        rng,
        score=lambda product: product.market_fit + product.user_count,
    )
    return PendingEvent(
        event_id="enterprise_procurement_delay",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Enterprise Procurement Delay",
        description=(
            f"A large buyer likes {target.name}, but procurement is slowing the deal. "
            "You can fund proof artifacts or wait out the process."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="enterprise_sales_chain",
        chain_stage=2,
        target_product_id=target.id,
        options=[
            EventOption(
                id="fund_proof",
                label="Fund proof artifacts",
                description="Spend cash to convert part of the pipeline into users and ARPU.",
            ),
            EventOption(
                id="wait_out_process",
                label="Wait out the process",
                description="Protect cash, but reputation and account confidence slip.",
            ),
        ],
    )


def _get_product_by_id(products: list[Product], product_id: UUID) -> Product | None:
    return next((product for product in products if product.id == product_id), None)


def _has_recent_event(state: GameState, event_ids: set[str], window_turns: int) -> bool:
    oldest_turn = state.company.current_turn - window_turns
    return any(
        entry.event_id in event_ids and entry.resolved_turn >= oldest_turn
        for entry in state.event_history
    )


def _pick_best_product(
    products: list[Product],
    rng: RandomLike,
    score: Callable[[Product], int],
) -> Product:
    best_score = max(score(product) for product in products)
    candidates = [product for product in products if score(product) == best_score]
    return candidates[rng.randint(0, len(candidates) - 1)]


def _pick_best_employee(
    employees: list[Employee],
    rng: RandomLike,
    score: Callable[[Employee], int],
) -> Employee:
    best_score = max(score(employee) for employee in employees)
    candidates = [employee for employee in employees if score(employee) == best_score]
    return candidates[rng.randint(0, len(candidates) - 1)]


def get_designer_or_marketer_support(
    employees: list[Employee],
    product_id: UUID,
) -> list[Employee]:
    """Return comms-facing employees assigned to a product."""

    return [
        employee
        for employee in employees
        if employee.assigned_product_id == product_id
        and employee.role in {EmployeeRole.DESIGNER, EmployeeRole.MARKETER}
        and calculate_effective_productivity(employee) > 0
    ]
