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
    PartnershipStatus,
    PendingEvent,
    Product,
)
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.endgame import calculate_endgame_pressure, calculate_endgame_readiness
from nexus_tech.simulation.finance import count_funding_rounds
from nexus_tech.simulation.operations import calculate_operations_summary
from nexus_tech.simulation.partnerships import calculate_partnership_portfolio
from nexus_tech.simulation.randomness import RandomLike
from nexus_tech.simulation.support_program import calculate_support_queue_exposure
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
            event_id="channel_conflict",
            category=EventCategory.MARKET_OPPORTUNITY,
            weight=BALANCE.event_channel_conflict_weight,
            cooldown_turns=BALANCE.event_channel_conflict_cooldown,
            is_eligible=_is_channel_conflict_eligible,
            build_pending_event=_build_channel_conflict_event,
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
            event_id="bridge_round",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_bridge_round_weight,
            cooldown_turns=BALANCE.event_bridge_round_cooldown,
            is_eligible=_is_bridge_round_eligible,
            build_pending_event=_build_bridge_round_event,
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
            event_id="exit_interest",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_exit_interest_weight,
            cooldown_turns=BALANCE.event_exit_interest_cooldown,
            is_eligible=_is_exit_interest_eligible,
            build_pending_event=_build_exit_interest_event,
        ),
        EventDefinition(
            event_id="public_market_scrutiny",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_public_market_scrutiny_weight,
            cooldown_turns=BALANCE.event_public_market_scrutiny_cooldown,
            is_eligible=_is_public_market_scrutiny_eligible,
            build_pending_event=_build_public_market_scrutiny_event,
        ),
        EventDefinition(
            event_id="ipo_audit_committee",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_ipo_audit_committee_weight,
            cooldown_turns=BALANCE.event_ipo_audit_committee_cooldown,
            is_eligible=_is_ipo_audit_committee_eligible,
            build_pending_event=_build_ipo_audit_committee_event,
        ),
        EventDefinition(
            event_id="ipo_reference_crack",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_ipo_reference_crack_weight,
            cooldown_turns=BALANCE.event_ipo_reference_crack_cooldown,
            is_eligible=_is_ipo_reference_crack_eligible,
            build_pending_event=_build_ipo_reference_crack_event,
        ),
        EventDefinition(
            event_id="ipo_listing_window",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_ipo_listing_window_weight,
            cooldown_turns=BALANCE.event_ipo_listing_window_cooldown,
            is_eligible=_is_ipo_listing_window_eligible,
            build_pending_event=_build_ipo_listing_window_event,
        ),
        EventDefinition(
            event_id="ipo_governance_lockstep",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_ipo_governance_lockstep_weight,
            cooldown_turns=BALANCE.event_ipo_governance_lockstep_cooldown,
            is_eligible=_is_ipo_governance_lockstep_eligible,
            build_pending_event=_build_ipo_governance_lockstep_event,
        ),
        EventDefinition(
            event_id="ipo_syndicate_commitment",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_ipo_syndicate_commitment_weight,
            cooldown_turns=BALANCE.event_ipo_syndicate_commitment_cooldown,
            is_eligible=_is_ipo_syndicate_commitment_eligible,
            build_pending_event=_build_ipo_syndicate_commitment_event,
        ),
        EventDefinition(
            event_id="ipo_pricing_committee",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_ipo_pricing_committee_weight,
            cooldown_turns=BALANCE.event_ipo_pricing_committee_cooldown,
            is_eligible=_is_ipo_pricing_committee_eligible,
            build_pending_event=_build_ipo_pricing_committee_event,
        ),
        EventDefinition(
            event_id="ipo_reference_committee",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_ipo_reference_committee_weight,
            cooldown_turns=BALANCE.event_ipo_reference_committee_cooldown,
            is_eligible=_is_ipo_reference_committee_eligible,
            build_pending_event=_build_ipo_reference_committee_event,
        ),
        EventDefinition(
            event_id="acquirer_diligence",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_acquirer_diligence_weight,
            cooldown_turns=BALANCE.event_acquirer_diligence_cooldown,
            is_eligible=_is_acquirer_diligence_eligible,
            build_pending_event=_build_acquirer_diligence_event,
        ),
        EventDefinition(
            event_id="buyer_reference_check",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_buyer_reference_check_weight,
            cooldown_turns=BALANCE.event_buyer_reference_check_cooldown,
            is_eligible=_is_buyer_reference_check_eligible,
            build_pending_event=_build_buyer_reference_check_event,
        ),
        EventDefinition(
            event_id="buyer_channel_conflict_review",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_buyer_channel_conflict_review_weight,
            cooldown_turns=BALANCE.event_buyer_channel_conflict_review_cooldown,
            is_eligible=_is_buyer_channel_conflict_review_eligible,
            build_pending_event=_build_buyer_channel_conflict_review_event,
        ),
        EventDefinition(
            event_id="buyer_term_sheet",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_buyer_term_sheet_weight,
            cooldown_turns=BALANCE.event_buyer_term_sheet_cooldown,
            is_eligible=_is_buyer_term_sheet_eligible,
            build_pending_event=_build_buyer_term_sheet_event,
        ),
        EventDefinition(
            event_id="buyer_synergy_map",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_buyer_synergy_map_weight,
            cooldown_turns=BALANCE.event_buyer_synergy_map_cooldown,
            is_eligible=_is_buyer_synergy_map_eligible,
            build_pending_event=_build_buyer_synergy_map_event,
        ),
        EventDefinition(
            event_id="buyer_integration_blueprint",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_buyer_integration_blueprint_weight,
            cooldown_turns=BALANCE.event_buyer_integration_blueprint_cooldown,
            is_eligible=_is_buyer_integration_blueprint_eligible,
            build_pending_event=_build_buyer_integration_blueprint_event,
        ),
        EventDefinition(
            event_id="buyer_operating_memo",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_buyer_operating_memo_weight,
            cooldown_turns=BALANCE.event_buyer_operating_memo_cooldown,
            is_eligible=_is_buyer_operating_memo_eligible,
            build_pending_event=_build_buyer_operating_memo_event,
        ),
        EventDefinition(
            event_id="buyer_signing_committee",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_buyer_signing_committee_weight,
            cooldown_turns=BALANCE.event_buyer_signing_committee_cooldown,
            is_eligible=_is_buyer_signing_committee_eligible,
            build_pending_event=_build_buyer_signing_committee_event,
        ),
        EventDefinition(
            event_id="independence_reckoning",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_independence_reckoning_weight,
            cooldown_turns=BALANCE.event_independence_reckoning_cooldown,
            is_eligible=_is_independence_reckoning_eligible,
            build_pending_event=_build_independence_reckoning_event,
        ),
        EventDefinition(
            event_id="independence_cash_crunch",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_independence_cash_crunch_weight,
            cooldown_turns=BALANCE.event_independence_cash_crunch_cooldown,
            is_eligible=_is_independence_cash_crunch_eligible,
            build_pending_event=_build_independence_cash_crunch_event,
        ),
        EventDefinition(
            event_id="independence_refinancing_wall",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_independence_refinancing_wall_weight,
            cooldown_turns=BALANCE.event_independence_refinancing_wall_cooldown,
            is_eligible=_is_independence_refinancing_wall_eligible,
            build_pending_event=_build_independence_refinancing_wall_event,
        ),
        EventDefinition(
            event_id="independence_profit_floor",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_independence_profit_floor_weight,
            cooldown_turns=BALANCE.event_independence_profit_floor_cooldown,
            is_eligible=_is_independence_profit_floor_eligible,
            build_pending_event=_build_independence_profit_floor_event,
        ),
        EventDefinition(
            event_id="independence_operating_covenant",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_independence_operating_covenant_weight,
            cooldown_turns=BALANCE.event_independence_operating_covenant_cooldown,
            is_eligible=_is_independence_operating_covenant_eligible,
            build_pending_event=_build_independence_operating_covenant_event,
        ),
        EventDefinition(
            event_id="independence_buffer_ratchet",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_independence_buffer_ratchet_weight,
            cooldown_turns=BALANCE.event_independence_buffer_ratchet_cooldown,
            is_eligible=_is_independence_buffer_ratchet_eligible,
            build_pending_event=_build_independence_buffer_ratchet_event,
        ),
        EventDefinition(
            event_id="independence_cash_yield_pact",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_independence_cash_yield_pact_weight,
            cooldown_turns=BALANCE.event_independence_cash_yield_pact_cooldown,
            is_eligible=_is_independence_cash_yield_pact_eligible,
            build_pending_event=_build_independence_cash_yield_pact_event,
        ),
        EventDefinition(
            event_id="independence_treasury_compact",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_independence_treasury_compact_weight,
            cooldown_turns=BALANCE.event_independence_treasury_compact_cooldown,
            is_eligible=_is_independence_treasury_compact_eligible,
            build_pending_event=_build_independence_treasury_compact_event,
        ),
        EventDefinition(
            event_id="enterprise_procurement_delay",
            category=EventCategory.MARKET_OPPORTUNITY,
            weight=BALANCE.event_procurement_delay_weight,
            cooldown_turns=BALANCE.event_procurement_delay_cooldown,
            is_eligible=_is_enterprise_procurement_delay_eligible,
            build_pending_event=_build_enterprise_procurement_delay_event,
        ),
        EventDefinition(
            event_id="support_meltdown",
            category=EventCategory.PRODUCT_INCIDENT,
            weight=BALANCE.event_support_meltdown_weight,
            cooldown_turns=BALANCE.event_support_meltdown_cooldown,
            is_eligible=_is_support_meltdown_eligible,
            build_pending_event=_build_support_meltdown_event,
        ),
        EventDefinition(
            event_id="board_reckoning",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_board_reckoning_weight,
            cooldown_turns=BALANCE.event_board_reckoning_cooldown,
            is_eligible=_is_board_reckoning_eligible,
            build_pending_event=_build_board_reckoning_event,
        ),
        EventDefinition(
            event_id="partner_qbr",
            category=EventCategory.MARKET_OPPORTUNITY,
            weight=BALANCE.event_partner_qbr_weight,
            cooldown_turns=BALANCE.event_partner_qbr_cooldown,
            is_eligible=_is_partner_qbr_eligible,
            build_pending_event=_build_partner_qbr_event,
        ),
        EventDefinition(
            event_id="partner_breakdown",
            category=EventCategory.MARKET_OPPORTUNITY,
            weight=BALANCE.event_partner_breakdown_weight,
            cooldown_turns=BALANCE.event_partner_breakdown_cooldown,
            is_eligible=_is_partner_breakdown_eligible,
            build_pending_event=_build_partner_breakdown_event,
        ),
        EventDefinition(
            event_id="partner_renegotiation",
            category=EventCategory.MARKET_OPPORTUNITY,
            weight=BALANCE.event_partner_renegotiation_weight,
            cooldown_turns=BALANCE.event_partner_renegotiation_cooldown,
            is_eligible=_is_partner_renegotiation_eligible,
            build_pending_event=_build_partner_renegotiation_event,
        ),
        EventDefinition(
            event_id="channel_concentration_crackdown",
            category=EventCategory.MARKET_OPPORTUNITY,
            weight=BALANCE.event_channel_concentration_crackdown_weight,
            cooldown_turns=BALANCE.event_channel_concentration_crackdown_cooldown,
            is_eligible=_is_channel_concentration_crackdown_eligible,
            build_pending_event=_build_channel_concentration_crackdown_event,
        ),
        EventDefinition(
            event_id="reseller_enablement_gap",
            category=EventCategory.MARKET_OPPORTUNITY,
            weight=BALANCE.event_reseller_enablement_gap_weight,
            cooldown_turns=BALANCE.event_reseller_enablement_gap_cooldown,
            is_eligible=_is_reseller_enablement_gap_eligible,
            build_pending_event=_build_reseller_enablement_gap_event,
        ),
        EventDefinition(
            event_id="integration_cutover_risk",
            category=EventCategory.PRODUCT_INCIDENT,
            weight=BALANCE.event_integration_cutover_risk_weight,
            cooldown_turns=BALANCE.event_integration_cutover_risk_cooldown,
            is_eligible=_is_integration_cutover_risk_eligible,
            build_pending_event=_build_integration_cutover_risk_event,
        ),
        EventDefinition(
            event_id="marketplace_chargeback_wave",
            category=EventCategory.REPUTATION_INCIDENT,
            weight=BALANCE.event_marketplace_chargeback_wave_weight,
            cooldown_turns=BALANCE.event_marketplace_chargeback_wave_cooldown,
            is_eligible=_is_marketplace_chargeback_wave_eligible,
            build_pending_event=_build_marketplace_chargeback_wave_event,
        ),
        EventDefinition(
            event_id="reseller_reference_summit",
            category=EventCategory.MARKET_OPPORTUNITY,
            weight=BALANCE.event_reseller_reference_summit_weight,
            cooldown_turns=BALANCE.event_reseller_reference_summit_cooldown,
            is_eligible=_is_reseller_reference_summit_eligible,
            build_pending_event=_build_reseller_reference_summit_event,
        ),
        EventDefinition(
            event_id="integration_cutover_board",
            category=EventCategory.PRODUCT_INCIDENT,
            weight=BALANCE.event_integration_cutover_board_weight,
            cooldown_turns=BALANCE.event_integration_cutover_board_cooldown,
            is_eligible=_is_integration_cutover_board_eligible,
            build_pending_event=_build_integration_cutover_board_event,
        ),
        EventDefinition(
            event_id="marketplace_dispute_program",
            category=EventCategory.REPUTATION_INCIDENT,
            weight=BALANCE.event_marketplace_dispute_program_weight,
            cooldown_turns=BALANCE.event_marketplace_dispute_program_cooldown,
            is_eligible=_is_marketplace_dispute_program_eligible,
            build_pending_event=_build_marketplace_dispute_program_event,
        ),
        EventDefinition(
            event_id="board_recovery_window",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_board_recovery_window_weight,
            cooldown_turns=BALANCE.event_board_recovery_window_cooldown,
            is_eligible=_is_board_recovery_window_eligible,
            build_pending_event=_build_board_recovery_window_event,
        ),
        EventDefinition(
            event_id="board_reset_showdown",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_board_reset_showdown_weight,
            cooldown_turns=BALANCE.event_board_reset_showdown_cooldown,
            is_eligible=_is_board_reset_showdown_eligible,
            build_pending_event=_build_board_reset_showdown_event,
        ),
        EventDefinition(
            event_id="board_reset_execution_plan",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_board_reset_execution_plan_weight,
            cooldown_turns=BALANCE.event_board_reset_execution_plan_cooldown,
            is_eligible=_is_board_reset_execution_plan_eligible,
            build_pending_event=_build_board_reset_execution_plan_event,
        ),
        EventDefinition(
            event_id="board_reset_operating_cadence",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_board_reset_operating_cadence_weight,
            cooldown_turns=BALANCE.event_board_reset_operating_cadence_cooldown,
            is_eligible=_is_board_reset_operating_cadence_eligible,
            build_pending_event=_build_board_reset_operating_cadence_event,
        ),
        EventDefinition(
            event_id="capital_market_freeze",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_capital_market_freeze_weight,
            cooldown_turns=BALANCE.event_capital_market_freeze_cooldown,
            is_eligible=_is_capital_market_freeze_eligible,
            build_pending_event=_build_capital_market_freeze_event,
        ),
        EventDefinition(
            event_id="succession_gap",
            category=EventCategory.EMPLOYEE_ISSUE,
            weight=BALANCE.event_succession_gap_weight,
            cooldown_turns=BALANCE.event_succession_gap_cooldown,
            is_eligible=_is_succession_gap_eligible,
            build_pending_event=_build_succession_gap_event,
        ),
        EventDefinition(
            event_id="strategic_crossroads",
            category=EventCategory.FUNDING_OPPORTUNITY,
            weight=BALANCE.event_strategic_crossroads_weight,
            cooldown_turns=BALANCE.event_strategic_crossroads_cooldown,
            is_eligible=_is_strategic_crossroads_eligible,
            build_pending_event=_build_strategic_crossroads_event,
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
        customer_accounts=state.customer_accounts,
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


def _is_channel_conflict_eligible(state: GameState) -> bool:
    return any(
        partnership.status.value != "paused"
        and partnership.conflict_pressure >= BALANCE.event_channel_conflict_conflict_threshold
        for partnership in state.partnerships
    )


def _build_channel_conflict_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = max(
        (partnership for partnership in state.partnerships if partnership.status.value != "paused"),
        key=lambda partnership: partnership.conflict_pressure + partnership.risk,
    )
    product = _get_product_by_id(state.products, target.product_id)
    product_name = product.name if product is not None else "the flagship product"
    del rng
    return PendingEvent(
        event_id="channel_conflict",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Channel Conflict",
        description=(
            f"The {target.channel.value} channel around {product_name} is colliding with direct "
            "sales. You can protect direct control or lean into the partner and accept more "
            "governance noise."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        target_product_id=target.product_id,
        options=[
            EventOption(
                id="protect_direct",
                label="Protect direct sales",
                description="Reduce conflict now, but slow the channel for a turn.",
            ),
            EventOption(
                id="lean_partner",
                label="Lean into the partner",
                description="Take faster channel demand, but increase board pressure.",
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


def _is_bridge_round_eligible(state: GameState) -> bool:
    return (
        state.company.current_turn >= BALANCE.event_bridge_round_turn_threshold
        and state.company.cash_on_hand <= BALANCE.event_bridge_round_cash_threshold
        and (
            state.capital_plan.source_preference.value != "bootstrap"
            or state.finance.investor_pressure >= 18
        )
    )


def _build_bridge_round_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    return PendingEvent(
        event_id="bridge_round",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Bridge Capital Window",
        description=(
            "A small bridge investor is willing to move fast. You can take the cash to protect "
            "runway or cut burn and preserve more control."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        options=[
            EventOption(
                id="take_bridge",
                label="Take the bridge",
                description="Add cash now, but accept more dilution and investor pressure.",
            ),
            EventOption(
                id="cut_burn",
                label="Cut burn instead",
                description="Preserve control, but ask the team for a harder operating reset.",
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


def _is_exit_interest_eligible(state: GameState) -> bool:
    readiness = calculate_endgame_readiness(state)
    return (
        state.company.current_turn >= BALANCE.event_exit_interest_turn_threshold
        and max(
            readiness.ipo_readiness_score,
            readiness.acquisition_interest_score,
            readiness.independence_score,
        )
        >= BALANCE.event_exit_interest_readiness_threshold
    )


def _is_public_market_scrutiny_eligible(state: GameState) -> bool:
    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    queue_exposure = calculate_support_queue_exposure(state)
    return (
        state.company.current_turn >= BALANCE.event_exit_interest_turn_threshold
        and any(product.is_active for product in state.products)
        and readiness.strategic_outlook == "ipo_ready"
        and pressure.public_market_scrutiny
        >= BALANCE.event_public_market_scrutiny_pressure_threshold
        and (
            pressure.dominant_pressure == "public_market_scrutiny"
            or queue_exposure.enterprise_queue_risk_accounts > 0
            or queue_exposure.enterprise_queue_risk_accounts >= 2
            or (
                queue_exposure.hotspot_lane.value == "enterprise"
                and queue_exposure.hotspot_lane_overflow > 0
            )
            or (
                queue_exposure.hotspot_lane.value == "enterprise"
                and queue_exposure.focus_alignment_gap > 0
            )
        )
        and not _has_recent_event(
            state,
            {"exit_interest", "strategic_crossroads"},
            BALANCE.event_chain_recent_window_turns,
        )
    )


def _build_public_market_scrutiny_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [product for product in state.products if product.is_active],
        rng,
        score=lambda product: product.user_count + product.market_fit + product.quality,
    )
    return PendingEvent(
        event_id="public_market_scrutiny",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Public-Market Scrutiny",
        description=(
            f"Operators and investors are starting to question whether {target.name} can support "
            "a cleaner public-market narrative. You can tighten controls or tell a bigger story "
            "and accept more operating scrutiny."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="endgame_chain",
        chain_stage=2,
        target_product_id=target.id,
        options=[
            EventOption(
                id="tighten_controls",
                label="Tighten controls",
                description="Spend cash to improve governance optics and calm the board.",
            ),
            EventOption(
                id="sell_story",
                label="Sell the bigger story",
                description="Gain narrative momentum, but increase pressure on operations.",
            ),
        ],
    )


def _is_ipo_audit_committee_eligible(state: GameState) -> bool:
    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    queue_exposure = calculate_support_queue_exposure(state)
    return (
        _has_recent_event(
            state,
            {"public_market_scrutiny"},
            BALANCE.event_chain_recent_window_turns,
        )
        and readiness.strategic_outlook == "ipo_ready"
        and pressure.public_market_scrutiny >= BALANCE.event_ipo_audit_committee_pressure_threshold
        and (
            state.finance.board_resolution_due
            or queue_exposure.enterprise_queue_risk_accounts > 0
            or queue_exposure.hotspot_lane.value == "enterprise"
        )
    )


def _build_ipo_audit_committee_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [product for product in state.products if product.is_active],
        rng,
        score=lambda product: product.user_count + product.market_fit + product.quality,
    )
    return PendingEvent(
        event_id="ipo_audit_committee",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="IPO Audit Committee",
        description=(
            f"Directors want a formal audit-readiness pass around {target.name}. "
            "You can fund the control work now or delay and accept more scrutiny."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="endgame_chain",
        chain_stage=3,
        target_product_id=target.id,
        options=[
            EventOption(
                id="fund_audit_readiness",
                label="Fund audit readiness",
                description="Spend cash to improve controls, confidence, and queue discipline.",
            ),
            EventOption(
                id="delay_committee",
                label="Delay the committee",
                description="Protect cash now, but governance and queue pressure worsen.",
            ),
        ],
    )


def _is_ipo_reference_crack_eligible(state: GameState) -> bool:
    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    queue_exposure = calculate_support_queue_exposure(state)
    return (
        _has_recent_event(
            state,
            {"ipo_audit_committee"},
            BALANCE.event_chain_recent_window_turns,
        )
        and readiness.strategic_outlook == "ipo_ready"
        and pressure.public_market_scrutiny >= BALANCE.event_ipo_reference_crack_pressure_threshold
        and (
            queue_exposure.enterprise_queue_risk_accounts > 0
            or queue_exposure.premium_queue_risk_accounts > 0
            or (
                queue_exposure.hotspot_lane.value == "enterprise"
                and queue_exposure.focus_alignment_gap > 0
            )
        )
    )


def _build_ipo_reference_crack_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [product for product in state.products if product.is_active],
        rng,
        score=lambda product: product.user_count + product.market_fit + product.quality,
    )
    return PendingEvent(
        event_id="ipo_reference_crack",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="IPO Reference Crack",
        description=(
            f"Public-market prep around {target.name} now hinges on whether flagship customers "
            "still look referenceable. You can fund a tighter rescue program or accept a delay "
            "and more scrutiny."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="endgame_chain",
        chain_stage=4,
        target_product_id=target.id,
        options=[
            EventOption(
                id="fund_reference_reset",
                label="Fund a reference reset",
                description="Spend cash to calm flagship accounts and restore confidence.",
            ),
            EventOption(
                id="accept_delay",
                label="Accept the delay",
                description="Preserve cash now, but let scrutiny and reputation pressure climb.",
            ),
        ],
    )


def _is_ipo_listing_window_eligible(state: GameState) -> bool:
    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    queue_exposure = calculate_support_queue_exposure(state)
    return (
        _has_recent_event(
            state,
            {"ipo_reference_crack"},
            BALANCE.event_chain_recent_window_turns,
        )
        and readiness.strategic_outlook == "ipo_ready"
        and pressure.public_market_scrutiny >= BALANCE.event_ipo_listing_window_pressure_threshold
        and (
            state.finance.board_confidence >= 55
            or state.finance.board_score >= 55
            or queue_exposure.enterprise_queue_risk_accounts > 0
            or queue_exposure.hotspot_lane.value == "enterprise"
        )
    )


def _build_ipo_listing_window_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [product for product in state.products if product.is_active],
        rng,
        score=lambda product: product.user_count + product.market_fit + product.quality,
    )
    return PendingEvent(
        event_id="ipo_listing_window",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="IPO Listing Window",
        description=(
            f"Bankers think {target.name} has a narrow window to look listing-ready. "
            "You can slow down and certify the operating story or accelerate the roadshow and "
            "accept more fragility."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="endgame_chain",
        chain_stage=5,
        target_product_id=target.id,
        options=[
            EventOption(
                id="slow_and_certify",
                label="Slow down and certify",
                description=(
                    "Spend cash to harden controls and calm scrutiny before the window moves."
                ),
            ),
            EventOption(
                id="accelerate_roadshow",
                label="Accelerate the roadshow",
                description="Push the narrative forward now and absorb more late-game pressure.",
            ),
        ],
    )


def _is_ipo_governance_lockstep_eligible(state: GameState) -> bool:
    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    return (
        _has_recent_event(
            state,
            {"ipo_listing_window"},
            BALANCE.event_chain_recent_window_turns,
        )
        and readiness.strategic_outlook == "ipo_ready"
        and pressure.public_market_scrutiny
        >= BALANCE.event_ipo_governance_lockstep_pressure_threshold
        and (
            state.finance.board_resolution_due
            or state.finance.board_warning_level >= 2
            or state.finance.governance_risk >= 50
        )
    )


def _build_ipo_governance_lockstep_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [product for product in state.products if product.is_active],
        rng,
        score=lambda product: product.user_count + product.market_fit + product.quality,
    )
    return PendingEvent(
        event_id="ipo_governance_lockstep",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="IPO Governance Lockstep",
        description=(
            f"Bankers want {target.name} to move in tighter governance lockstep before the next "
            "listing push. You can formalize the governance path now or stretch the window and "
            "accept more pressure."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="endgame_chain",
        chain_stage=6,
        target_product_id=target.id,
        options=[
            EventOption(
                id="lock_governance_path",
                label="Lock the governance path",
                description="Spend cash now to reduce governance heat before the next IPO step.",
            ),
            EventOption(
                id="stretch_compliance",
                label="Stretch compliance",
                description="Protect cash for one more turn and accept more scrutiny.",
            ),
        ],
    )


def _is_ipo_syndicate_commitment_eligible(state: GameState) -> bool:
    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    queue_exposure = calculate_support_queue_exposure(state)
    return (
        _has_recent_event(
            state,
            {"ipo_governance_lockstep"},
            BALANCE.event_chain_recent_window_turns,
        )
        and readiness.strategic_outlook == "ipo_ready"
        and pressure.public_market_scrutiny
        >= BALANCE.event_ipo_syndicate_commitment_pressure_threshold
        and (
            state.finance.board_confidence >= 56
            or state.finance.board_score >= 54
            or queue_exposure.enterprise_queue_risk_accounts > 0
            or queue_exposure.white_glove_queue_risk_accounts > 0
        )
    )


def _build_ipo_syndicate_commitment_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [product for product in state.products if product.is_active],
        rng,
        score=lambda product: product.user_count + product.market_fit + product.quality,
    )
    return PendingEvent(
        event_id="ipo_syndicate_commitment",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="IPO Syndicate Commitment",
        description=(
            f"The banks want a firmer syndicate around {target.name}. You can anchor the book "
            "now to calm late-stage scrutiny or trim the range and protect cash while "
            "credibility softens."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="endgame_chain",
        chain_stage=7,
        target_product_id=target.id,
        options=[
            EventOption(
                id="anchor_book",
                label="Anchor the syndicate",
                description="Spend cash to lock in stronger late-stage conviction.",
            ),
            EventOption(
                id="trim_range",
                label="Trim the range",
                description="Reduce scrutiny pressure now, but weaken the IPO narrative.",
            ),
        ],
    )


def _is_ipo_pricing_committee_eligible(state: GameState) -> bool:
    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    queue_exposure = calculate_support_queue_exposure(state)
    return (
        _has_recent_event(
            state,
            {"ipo_syndicate_commitment"},
            BALANCE.event_chain_recent_window_turns,
        )
        and readiness.strategic_outlook == "ipo_ready"
        and pressure.public_market_scrutiny
        >= BALANCE.event_ipo_pricing_committee_pressure_threshold
        and (
            state.finance.board_confidence >= 58
            or state.finance.board_score >= 56
            or queue_exposure.white_glove_queue_risk_accounts > 0
            or queue_exposure.enterprise_queue_risk_accounts > 0
        )
    )


def _build_ipo_pricing_committee_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [product for product in state.products if product.is_active],
        rng,
        score=lambda product: product.user_count + product.market_fit + product.quality,
    )
    return PendingEvent(
        event_id="ipo_pricing_committee",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="IPO Pricing Committee",
        description=(
            f"Bankers want a tighter pricing committee around {target.name}. You can lock the "
            "discipline now and calm scrutiny, or defend a richer range and accept hotter "
            "governance pressure."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="endgame_chain",
        chain_stage=8,
        target_product_id=target.id,
        options=[
            EventOption(
                id="lock_pricing_discipline",
                label="Lock pricing discipline",
                description="Spend cash to reduce scrutiny and improve IPO execution optics.",
            ),
            EventOption(
                id="defend_rich_range",
                label="Defend a richer range",
                description="Protect upside and reputation, but accept more IPO heat now.",
            ),
        ],
    )


def _is_ipo_reference_committee_eligible(state: GameState) -> bool:
    pressure = calculate_endgame_pressure(state)
    queue_exposure = calculate_support_queue_exposure(state)
    return (
        _has_recent_event(
            state,
            {"ipo_pricing_committee"},
            BALANCE.event_chain_recent_window_turns,
        )
        and pressure.public_market_scrutiny
        >= BALANCE.event_ipo_reference_committee_pressure_threshold
        and (
            queue_exposure.white_glove_queue_risk_accounts > 0
            or queue_exposure.enterprise_queue_risk_accounts > 0
            or queue_exposure.premium_queue_risk_accounts > 0
            or state.finance.board_warning_level >= 2
        )
    )


def _build_ipo_reference_committee_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [product for product in state.products if product.is_active],
        rng,
        score=lambda product: product.user_count + product.market_fit + product.quality,
    )
    return PendingEvent(
        event_id="ipo_reference_committee",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="IPO Reference Committee",
        description=(
            f"Bankers now want a tighter reference committee around {target.name}. "
            "You can fund the committee and calm premium-account fragility or defer it and "
            "accept more scrutiny."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="endgame_chain",
        chain_stage=10,
        target_product_id=target.id,
        options=[
            EventOption(
                id="fund_reference_committee",
                label="Fund the reference committee",
                description="Spend cash to calm flagship-account strain before the listing push.",
            ),
            EventOption(
                id="defer_committee",
                label="Defer the committee",
                description="Protect cash now, but let scrutiny and governance heat keep rising.",
            ),
        ],
    )


def _is_acquirer_diligence_eligible(state: GameState) -> bool:
    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    portfolio = calculate_partnership_portfolio(state)
    return (
        state.company.current_turn >= BALANCE.event_exit_interest_turn_threshold
        and any(product.is_active for product in state.products)
        and readiness.strategic_outlook == "strategic_acquisition"
        and pressure.acquirer_diligence >= BALANCE.event_acquirer_diligence_pressure_threshold
        and bool(state.customer_accounts)
        and (
            pressure.dominant_pressure == "acquirer_diligence"
            or portfolio.hotspot_revenue_share_percent >= 35
            or portfolio.paused_dependency_score
            >= BALANCE.finance_planner_reactivate_dependency_threshold
            or portfolio.paused_count > 0
            or portfolio.recovery_count > 0
            or portfolio.direct_sales_conflict_accounts > 0
            or portfolio.hotspot_dependency_score
            >= BALANCE.finance_planner_reactivate_dependency_threshold
        )
        and not _has_recent_event(
            state,
            {"partner_breakdown", "partner_renegotiation"},
            BALANCE.event_chain_recent_window_turns,
        )
    )


def _build_acquirer_diligence_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [product for product in state.products if product.is_active],
        rng,
        score=lambda product: product.user_count + product.market_fit + product.quality,
    )
    return PendingEvent(
        event_id="acquirer_diligence",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Acquirer Diligence",
        description=(
            f"Potential buyers are asking harder questions about {target.name}, the support load, "
            "and channel quality. You can open the data room or protect optionality and keep "
            "control of the process."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="endgame_chain",
        chain_stage=2,
        target_product_id=target.id,
        options=[
            EventOption(
                id="open_data_room",
                label="Open the data room",
                description="Spend cash to improve board conviction and calm diligence risk.",
            ),
            EventOption(
                id="protect_optionality",
                label="Protect optionality",
                description="Stay selective, reinforce independence, and relieve some pressure.",
            ),
        ],
    )


def _is_buyer_reference_check_eligible(state: GameState) -> bool:
    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    portfolio = calculate_partnership_portfolio(state)
    return (
        _has_recent_event(
            state,
            {"acquirer_diligence"},
            BALANCE.event_chain_recent_window_turns,
        )
        and readiness.strategic_outlook == "strategic_acquisition"
        and pressure.acquirer_diligence >= BALANCE.event_buyer_reference_check_pressure_threshold
        and (
            portfolio.direct_sales_conflict_accounts > 0
            or portfolio.hotspot_dependency_score
            >= BALANCE.finance_planner_reactivate_dependency_threshold
            or portfolio.recovery_count > 0
        )
    )


def _build_buyer_reference_check_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [product for product in state.products if product.is_active],
        rng,
        score=lambda product: product.user_count + product.market_fit + product.quality,
    )
    return PendingEvent(
        event_id="buyer_reference_check",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Buyer Reference Check",
        description=(
            f"Potential acquirers want customer references around {target.name}. "
            "You can fund the reference program or keep optionality open and accept more noise."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="endgame_chain",
        chain_stage=3,
        target_product_id=target.id,
        options=[
            EventOption(
                id="fund_reference_program",
                label="Fund the reference program",
                description=(
                    "Spend cash to calm customers and partner friction before diligence deepens."
                ),
            ),
            EventOption(
                id="protect_optionality",
                label="Protect optionality",
                description="Hold cash, keep the process open, and accept extra conflict pressure.",
            ),
        ],
    )


def _is_buyer_channel_conflict_review_eligible(state: GameState) -> bool:
    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    portfolio = calculate_partnership_portfolio(state)
    return (
        _has_recent_event(
            state,
            {"buyer_reference_check"},
            BALANCE.event_chain_recent_window_turns,
        )
        and readiness.strategic_outlook == "strategic_acquisition"
        and pressure.acquirer_diligence
        >= BALANCE.event_buyer_channel_conflict_review_pressure_threshold
        and (
            portfolio.direct_sales_conflict_accounts > 0
            or portfolio.hotspot_dependency_score
            >= BALANCE.finance_planner_reactivate_dependency_threshold
            or portfolio.paused_dependency_score
            >= BALANCE.finance_planner_reactivate_dependency_threshold
            or portfolio.hotspot_revenue_share_percent >= 35
        )
    )


def _build_buyer_channel_conflict_review_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [product for product in state.products if product.is_active],
        rng,
        score=lambda product: product.user_count + product.market_fit + product.quality,
    )
    portfolio = calculate_partnership_portfolio(state)
    channel_label = portfolio.hotspot_channel if portfolio.hotspot_channel != "-" else "channel"
    return PendingEvent(
        event_id="buyer_channel_conflict_review",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Buyer Channel Conflict Review",
        description=(
            f"Buyer calls around {target.name} keep circling back to {channel_label} overlap, "
            "partner terms, and direct-sales conflict. You can separate terms now or push "
            "forward and absorb more diligence heat."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="endgame_chain",
        chain_stage=4,
        target_product_id=target.id,
        options=[
            EventOption(
                id="separate_partner_terms",
                label="Separate partner terms",
                description=(
                    "Spend cash and margin to cool conflict before buyers harden their view."
                ),
            ),
            EventOption(
                id="press_forward",
                label="Press forward",
                description="Protect economics now, but let diligence conflict keep climbing.",
            ),
        ],
    )


def _is_buyer_term_sheet_eligible(state: GameState) -> bool:
    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    portfolio = calculate_partnership_portfolio(state)
    return (
        _has_recent_event(
            state,
            {"buyer_channel_conflict_review"},
            BALANCE.event_chain_recent_window_turns,
        )
        and readiness.strategic_outlook == "strategic_acquisition"
        and pressure.acquirer_diligence >= BALANCE.event_buyer_term_sheet_pressure_threshold
        and (
            portfolio.direct_sales_conflict_accounts > 0
            or portfolio.hotspot_dependency_score
            >= BALANCE.finance_planner_reactivate_dependency_threshold
            or portfolio.paused_dependency_score
            >= BALANCE.finance_planner_reactivate_dependency_threshold
            or portfolio.hotspot_revenue_share_percent >= 35
        )
    )


def _build_buyer_term_sheet_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [product for product in state.products if product.is_active],
        rng,
        score=lambda product: product.user_count + product.market_fit + product.quality,
    )
    portfolio = calculate_partnership_portfolio(state)
    channel_label = portfolio.hotspot_channel if portfolio.hotspot_channel != "-" else "channel"
    return PendingEvent(
        event_id="buyer_term_sheet",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Buyer Term Sheet",
        description=(
            f"Acquirers are ready to float terms around {target.name}, but they want cleaner "
            f"{channel_label} economics and less channel overlap. You can sign cleaner terms now "
            "or hold out for a richer story."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="endgame_chain",
        chain_stage=5,
        target_product_id=target.id,
        options=[
            EventOption(
                id="sign_clean_terms",
                label="Sign cleaner terms",
                description=(
                    "Spend cash and margin now to reduce conflict before buyers harden terms."
                ),
            ),
            EventOption(
                id="hold_out_premium",
                label="Hold out for a premium",
                description="Protect economics now, but accept more diligence and customer noise.",
            ),
        ],
    )


def _is_buyer_synergy_map_eligible(state: GameState) -> bool:
    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    portfolio = calculate_partnership_portfolio(state)
    return (
        _has_recent_event(
            state,
            {"buyer_term_sheet"},
            BALANCE.event_chain_recent_window_turns,
        )
        and readiness.strategic_outlook == "strategic_acquisition"
        and pressure.acquirer_diligence >= BALANCE.event_buyer_synergy_map_pressure_threshold
        and (
            portfolio.direct_sales_conflict_accounts > 0
            or portfolio.hotspot_dependency_score
            >= BALANCE.finance_planner_reactivate_dependency_threshold
            or portfolio.hotspot_revenue_share_percent >= 35
        )
    )


def _build_buyer_synergy_map_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [product for product in state.products if product.is_active],
        rng,
        score=lambda product: product.user_count + product.market_fit + product.quality,
    )
    portfolio = calculate_partnership_portfolio(state)
    channel_label = portfolio.hotspot_channel if portfolio.hotspot_channel != "-" else "channel"
    return PendingEvent(
        event_id="buyer_synergy_map",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Buyer Synergy Map",
        description=(
            f"Buyers now want a cleaner synergy map around {target.name}, especially the "
            f"{channel_label} lane. You can publish a cleaner integration plan or keep more "
            "optionality and accept higher diligence friction."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="endgame_chain",
        chain_stage=6,
        target_product_id=target.id,
        options=[
            EventOption(
                id="publish_synergy_map",
                label="Publish the synergy map",
                description="Spend cash now to reduce overlap and make buyer integration easier.",
            ),
            EventOption(
                id="protect_optionality",
                label="Protect optionality",
                description="Keep more room to negotiate later and absorb extra diligence heat.",
            ),
        ],
    )


def _is_buyer_integration_blueprint_eligible(state: GameState) -> bool:
    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    portfolio = calculate_partnership_portfolio(state)
    return (
        _has_recent_event(
            state,
            {"buyer_synergy_map"},
            BALANCE.event_chain_recent_window_turns,
        )
        and readiness.strategic_outlook == "strategic_acquisition"
        and pressure.acquirer_diligence
        >= BALANCE.event_buyer_integration_blueprint_pressure_threshold
        and (
            portfolio.hotspot_dependency_score
            >= BALANCE.finance_planner_reactivate_dependency_threshold
            or portfolio.direct_sales_conflict_accounts > 0
            or portfolio.hotspot_revenue_share_percent >= 35
        )
    )


def _build_buyer_integration_blueprint_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [product for product in state.products if product.is_active],
        rng,
        score=lambda product: product.user_count + product.market_fit + product.quality,
    )
    portfolio = calculate_partnership_portfolio(state)
    channel_label = portfolio.hotspot_channel if portfolio.hotspot_channel != "-" else "channel"
    return PendingEvent(
        event_id="buyer_integration_blueprint",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Buyer Integration Blueprint",
        description=(
            f"Buyers want a cleaner integration blueprint for the {channel_label} lane around "
            f"{target.name}. You can fund the clean-room work now or keep optionality and "
            "accept more acquisition drag."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="endgame_chain",
        chain_stage=8,
        target_product_id=target.id,
        options=[
            EventOption(
                id="fund_clean_room",
                label="Fund the clean room",
                description="Spend cash now to reduce channel overlap and buyer friction.",
            ),
            EventOption(
                id="hold_optionality",
                label="Hold optionality",
                description="Keep leverage for later and accept higher diligence drag now.",
            ),
        ],
    )


def _is_buyer_operating_memo_eligible(state: GameState) -> bool:
    pressure = calculate_endgame_pressure(state)
    portfolio = calculate_partnership_portfolio(state)
    return (
        _has_recent_event(
            state,
            {"buyer_integration_blueprint"},
            BALANCE.event_chain_recent_window_turns,
        )
        and pressure.acquirer_diligence >= BALANCE.event_buyer_operating_memo_pressure_threshold
        and (
            portfolio.hotspot_dependency_score
            >= BALANCE.finance_planner_reactivate_dependency_threshold
            or portfolio.channel_conflict_index >= 28
            or portfolio.recovery_drag_score >= BALANCE.finance_planner_channel_volatility_threshold
        )
    )


def _build_buyer_operating_memo_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [product for product in state.products if product.is_active],
        rng,
        score=lambda product: product.user_count + product.market_fit + product.quality,
    )
    portfolio = calculate_partnership_portfolio(state)
    channel_label = portfolio.hotspot_channel if portfolio.hotspot_channel != "-" else "channel"
    return PendingEvent(
        event_id="buyer_operating_memo",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Buyer Operating Memo",
        description=(
            f"Buyers want a cleaner operating memo for the {channel_label} motion around "
            f"{target.name}. You can publish the memo now or preserve optionality and accept "
            "more diligence drag."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="endgame_chain",
        chain_stage=9,
        target_product_id=target.id,
        options=[
            EventOption(
                id="publish_operating_memo",
                label="Publish the operating memo",
                description="Spend cash to reduce channel overlap and buyer friction.",
            ),
            EventOption(
                id="preserve_optionality",
                label="Preserve optionality",
                description="Keep more negotiating room, but absorb more acquisition drag.",
            ),
        ],
    )


def _is_buyer_signing_committee_eligible(state: GameState) -> bool:
    pressure = calculate_endgame_pressure(state)
    portfolio = calculate_partnership_portfolio(state)
    return (
        _has_recent_event(
            state,
            {"buyer_operating_memo"},
            BALANCE.event_chain_recent_window_turns,
        )
        and pressure.acquirer_diligence >= BALANCE.event_buyer_signing_committee_pressure_threshold
        and (
            portfolio.hotspot_dependency_score
            >= BALANCE.finance_planner_reactivate_dependency_threshold
            or portfolio.channel_conflict_index >= 28
            or portfolio.recovery_drag_score >= BALANCE.finance_planner_channel_volatility_threshold
            or portfolio.direct_sales_conflict_accounts > 0
        )
    )


def _build_buyer_signing_committee_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [product for product in state.products if product.is_active],
        rng,
        score=lambda product: product.user_count + product.market_fit + product.quality,
    )
    portfolio = calculate_partnership_portfolio(state)
    channel_label = portfolio.hotspot_channel if portfolio.hotspot_channel != "-" else "channel"
    return PendingEvent(
        event_id="buyer_signing_committee",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Buyer Signing Committee",
        description=(
            f"Buyers want a tighter signing committee around {target.name}, especially the "
            f"{channel_label} motion. You can staff the committee now or keep optionality and "
            "accept more execution discount."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="endgame_chain",
        chain_stage=10,
        target_product_id=target.id,
        options=[
            EventOption(
                id="staff_signing_committee",
                label="Staff the signing committee",
                description="Spend cash to reduce conflict before the process hardens further.",
            ),
            EventOption(
                id="hold_optionality",
                label="Hold optionality",
                description="Protect economics now, but let diligence friction keep rising.",
            ),
        ],
    )


def _is_independence_reckoning_eligible(state: GameState) -> bool:
    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    queue_exposure = calculate_support_queue_exposure(state)
    return (
        state.company.current_turn >= BALANCE.event_exit_interest_turn_threshold
        and (
            readiness.strategic_outlook == "profitable_independence"
            or pressure.capital_fragility >= BALANCE.event_independence_reckoning_pressure_threshold
        )
        and (
            pressure.independence_discipline
            >= BALANCE.event_independence_reckoning_pressure_threshold
            or pressure.capital_fragility >= BALANCE.event_independence_reckoning_pressure_threshold
            or state.capital_plan.reserve_share < BALANCE.capital_plan_low_reserve_share_threshold
            or (
                state.finance.debt_principal >= BALANCE.finance_debt_rollover_min_debt
                and state.finance.covenant_risk >= 12
            )
            or queue_exposure.renewal_queue_risk_accounts > 0
            or queue_exposure.hotspot_lane.value == "billing"
            or (
                queue_exposure.hotspot_lane.value == "billing"
                and queue_exposure.focus_alignment_gap > 0
            )
        )
        and not _has_recent_event(
            state,
            {"capital_market_freeze", "bridge_round"},
            BALANCE.event_chain_recent_window_turns,
        )
    )


def _build_independence_reckoning_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    return PendingEvent(
        event_id="independence_reckoning",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Independence Reckoning",
        description=(
            "The company can stay independent, but only if capital discipline gets sharper. "
            "You can double down on efficiency or accept a small bridge to protect flexibility."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="capital_chain",
        chain_stage=3,
        options=[
            EventOption(
                id="double_down_efficiency",
                label="Double down on efficiency",
                description="Lower pressure and covenants, but ask for more operating discipline.",
            ),
            EventOption(
                id="take_bridge_flex",
                label="Take a small flexibility bridge",
                description="Add cash now, but debt and outside pressure rise again.",
            ),
        ],
    )


def _is_independence_cash_crunch_eligible(state: GameState) -> bool:
    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    queue_exposure = calculate_support_queue_exposure(state)
    return (
        _has_recent_event(
            state,
            {"independence_reckoning"},
            BALANCE.event_chain_recent_window_turns,
        )
        and readiness.strategic_outlook == "profitable_independence"
        and pressure.independence_discipline
        >= BALANCE.event_independence_cash_crunch_pressure_threshold
        and (
            state.company.cash_on_hand < state.capital_plan.reserve_target
            or (
                state.finance.debt_principal >= BALANCE.finance_debt_rollover_min_debt
                and state.finance.covenant_risk >= 12
            )
            or queue_exposure.renewal_queue_risk_accounts > 0
        )
    )


def _build_independence_cash_crunch_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    return PendingEvent(
        event_id="independence_cash_crunch",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Independence Cash Crunch",
        description=(
            "The independent story is under cash pressure. You can shift harder toward reserves "
            "or roll forward another financing step and accept more outside pressure."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="capital_chain",
        chain_stage=4,
        options=[
            EventOption(
                id="cut_to_reserve",
                label="Cut to reserve",
                description="Lean harder into reserve discipline and accept some growth drag.",
            ),
            EventOption(
                id="roll_forward",
                label="Roll forward",
                description="Take another debt-like step to protect cash now and pay later.",
            ),
        ],
    )


def _is_independence_refinancing_wall_eligible(state: GameState) -> bool:
    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    return (
        _has_recent_event(
            state,
            {"independence_cash_crunch"},
            BALANCE.event_chain_recent_window_turns,
        )
        and readiness.strategic_outlook == "profitable_independence"
        and pressure.independence_discipline
        >= BALANCE.event_independence_refinancing_wall_pressure_threshold
        and state.finance.debt_principal >= BALANCE.finance_debt_rollover_min_debt
        and (
            state.finance.covenant_risk >= 12
            or state.company.cash_on_hand < state.capital_plan.reserve_target
            or state.capital_plan.reserve_share < BALANCE.capital_plan_low_reserve_share_threshold
        )
    )


def _build_independence_refinancing_wall_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    return PendingEvent(
        event_id="independence_refinancing_wall",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Independence Refinancing Wall",
        description=(
            "The independent story now depends on whether debt and reserve discipline can hold at "
            "the same time. You can lock harder into reserve protection or stretch the rollover "
            "again and absorb more financing heat."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="capital_chain",
        chain_stage=5,
        options=[
            EventOption(
                id="lock_reserve_discipline",
                label="Lock reserve discipline",
                description=(
                    "Shift harder into reserve protection and calm covenants at a growth cost."
                ),
            ),
            EventOption(
                id="stretch_rollover",
                label="Stretch the rollover",
                description="Add cash now, but compound debt and financing pressure again.",
            ),
        ],
    )


def _is_independence_profit_floor_eligible(state: GameState) -> bool:
    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    return (
        _has_recent_event(
            state,
            {"independence_refinancing_wall"},
            BALANCE.event_chain_recent_window_turns,
        )
        and readiness.strategic_outlook == "profitable_independence"
        and pressure.independence_discipline
        >= BALANCE.event_independence_profit_floor_pressure_threshold
        and (
            state.company.cash_on_hand < state.capital_plan.reserve_target
            or state.capital_plan.reserve_share < BALANCE.capital_plan_low_reserve_share_threshold
            or state.finance.covenant_risk >= 12
            or state.finance.debt_principal >= BALANCE.finance_debt_rollover_min_debt
        )
    )


def _build_independence_profit_floor_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    return PendingEvent(
        event_id="independence_profit_floor",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Independence Profit Floor",
        description=(
            "The company can keep compounding independently, but only if the next turn locks in "
            "a believable profit floor. You can tighten reserve discipline again or stretch for "
            "one more growth-biased move."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="capital_chain",
        chain_stage=6,
        options=[
            EventOption(
                id="lock_profit_floor",
                label="Lock the profit floor",
                description="Shift harder into reserve durability and accept some commercial drag.",
            ),
            EventOption(
                id="stretch_growth_once_more",
                label="Stretch growth once more",
                description="Buy time with another financing step and accept higher future heat.",
            ),
        ],
    )


def _is_independence_operating_covenant_eligible(state: GameState) -> bool:
    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    return (
        _has_recent_event(
            state,
            {"independence_profit_floor"},
            BALANCE.event_chain_recent_window_turns,
        )
        and readiness.strategic_outlook == "profitable_independence"
        and pressure.independence_discipline
        >= BALANCE.event_independence_operating_covenant_pressure_threshold
        and (
            state.capital_plan.reserve_share < BALANCE.capital_plan_low_reserve_share_threshold + 4
            or state.finance.covenant_risk >= 12
            or state.finance.debt_principal >= BALANCE.finance_debt_rollover_min_debt
            or state.company.cash_on_hand < state.capital_plan.reserve_target
        )
    )


def _build_independence_operating_covenant_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    return PendingEvent(
        event_id="independence_operating_covenant",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Independence Operating Covenant",
        description=(
            "The company now needs an operating covenant that proves it can stay independent "
            "without another financial wobble. You can commit to a harder operating floor or "
            "bridge liquidity one more time."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="capital_chain",
        chain_stage=7,
        options=[
            EventOption(
                id="commit_operating_floor",
                label="Commit the operating floor",
                description="Shift harder into reserve durability and calmer financing posture.",
            ),
            EventOption(
                id="stretch_liquidity_bridge",
                label="Stretch a liquidity bridge",
                description="Add more cash now and accept higher future financing heat.",
            ),
        ],
    )


def _is_independence_buffer_ratchet_eligible(state: GameState) -> bool:
    readiness = calculate_endgame_readiness(state)
    pressure = calculate_endgame_pressure(state)
    return (
        _has_recent_event(
            state,
            {"independence_operating_covenant"},
            BALANCE.event_chain_recent_window_turns,
        )
        and readiness.strategic_outlook == "profitable_independence"
        and pressure.independence_discipline
        >= BALANCE.event_independence_buffer_ratchet_pressure_threshold
        and (
            state.capital_plan.reserve_share < BALANCE.capital_plan_low_reserve_share_threshold + 6
            or state.finance.covenant_risk >= 10
            or state.finance.debt_principal >= BALANCE.finance_debt_rollover_min_debt
            or state.company.cash_on_hand < state.capital_plan.reserve_target
        )
    )


def _build_independence_buffer_ratchet_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    return PendingEvent(
        event_id="independence_buffer_ratchet",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Independence Buffer Ratchet",
        description=(
            "The company can keep compounding independently only if the reserve buffer ratchets "
            "up again. You can harden the buffer now or stretch vendor float and accept more "
            "covenant heat."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="capital_chain",
        chain_stage=8,
        options=[
            EventOption(
                id="ratchet_buffer",
                label="Ratchet the buffer",
                description="Shift harder into reserve durability and calm covenant pressure.",
            ),
            EventOption(
                id="stretch_vendor_float",
                label="Stretch vendor float",
                description="Protect cash now, but make the next covenant turn harsher.",
            ),
        ],
    )


def _is_independence_cash_yield_pact_eligible(state: GameState) -> bool:
    pressure = calculate_endgame_pressure(state)
    return (
        _has_recent_event(
            state,
            {"independence_buffer_ratchet"},
            BALANCE.event_chain_recent_window_turns,
        )
        and pressure.independence_discipline
        >= BALANCE.event_independence_cash_yield_pact_pressure_threshold
        and (
            state.capital_plan.reserve_share < BALANCE.capital_plan_low_reserve_share_threshold + 8
            or state.finance.covenant_risk >= 12
            or state.finance.debt_principal >= BALANCE.finance_debt_rollover_min_debt
            or state.company.cash_on_hand < state.capital_plan.reserve_target
        )
    )


def _build_independence_cash_yield_pact_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    return PendingEvent(
        event_id="independence_cash_yield_pact",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Independence Cash-Yield Pact",
        description=(
            "The company can keep the independence story credible only if reserve yield and "
            "operating discipline rise together. You can ratify the pact now or borrow through "
            "the gap and accept more covenant heat."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="capital_chain",
        chain_stage=9,
        options=[
            EventOption(
                id="ratify_cash_yield_pact",
                label="Ratify the cash-yield pact",
                description="Shift harder into reserve discipline and calm covenant pressure.",
            ),
            EventOption(
                id="borrow_through_gap",
                label="Borrow through the gap",
                description="Protect cash now, but make the next financing turn harsher.",
            ),
        ],
    )


def _build_exit_interest_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [product for product in state.products if product.is_active],
        rng,
        score=lambda product: product.user_count + product.market_fit + product.quality,
    )
    return PendingEvent(
        event_id="exit_interest",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Inbound Exit Interest",
        description=(
            f"A larger platform has started asking questions about {target.name}. "
            "You can explore the signal for credibility and cash or stay independent and keep "
            "the team focused."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        target_product_id=target.id,
        options=[
            EventOption(
                id="explore_interest",
                label="Explore the interest",
                description="Take the signal seriously and accept some new board pressure.",
            ),
            EventOption(
                id="stay_independent",
                label="Stay independent",
                description="Protect focus and reinforce the independent story.",
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


def _is_support_meltdown_eligible(state: GameState) -> bool:
    pressure = calculate_endgame_pressure(state)
    queue_exposure = calculate_support_queue_exposure(state)
    premium_breach_accounts = any(
        account.status is not CustomerAccountStatus.CHURNED
        and account.support_tier.value in {"priority", "white_glove"}
        and (
            account.ticket_queue_age >= BALANCE.support_program_queue_age_threshold + 1
            or account.sla_breach_risk >= state.support_program.sla_target
        )
        for account in state.customer_accounts
    )
    return _has_recent_event(
        state,
        {"support_backlog"},
        BALANCE.event_chain_recent_window_turns,
    ) or (
        state.support_program.backlog_queue >= BALANCE.event_support_meltdown_backlog_threshold
        or state.support_program.escalation_queue
        >= BALANCE.event_support_meltdown_escalation_threshold
        or pressure.support_fragility >= BALANCE.event_support_meltdown_fragility_threshold
        or pressure.commercial_fragility >= BALANCE.event_support_meltdown_fragility_threshold
        or premium_breach_accounts
        or queue_exposure.hotspot_lane_overflow >= 2
        or queue_exposure.premium_queue_risk_accounts > 0
        or queue_exposure.enterprise_queue_risk_accounts > 1
        or queue_exposure.renewal_queue_risk_accounts >= 2
        or queue_exposure.focus_alignment_gap > 0
    )


def _build_support_meltdown_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_product(
        [product for product in state.products if product.is_active],
        rng,
        score=lambda product: product.user_count + product.bug_level + product.technical_debt,
    )
    return PendingEvent(
        event_id="support_meltdown",
        category=EventCategory.PRODUCT_INCIDENT,
        title="Support Meltdown",
        description=(
            f"Ticket queues around {target.name} are spilling into renewals and escalations. "
            "You can staff an emergency response or ration support and accept customer pain."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="support_chain",
        chain_stage=2,
        target_product_id=target.id,
        options=[
            EventOption(
                id="staff_emergency",
                label="Staff an emergency response",
                description="Spend cash to expand staffing and drain queues quickly.",
            ),
            EventOption(
                id="ration_support",
                label="Ration support",
                description="Protect cash, but churn risk and reputation take a visible hit.",
            ),
        ],
    )


def _is_board_reckoning_eligible(state: GameState) -> bool:
    return _has_recent_event(
        state,
        {"board_scrutiny", "exit_interest", "down_round_pressure"},
        BALANCE.event_chain_recent_window_turns,
    ) or (
        state.finance.board_resolution_due
        or state.finance.board_pressure >= BALANCE.event_board_reckoning_pressure_threshold
        or state.finance.governance_crisis_active
    )


def _build_board_reckoning_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    return PendingEvent(
        event_id="board_reckoning",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Board Reckoning",
        description=(
            "Directors want proof that the current plan can either tighten execution or justify "
            "continued growth risk. You can reset toward discipline or defend the aggressive line."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="governance_chain",
        chain_stage=2,
        options=[
            EventOption(
                id="reset_plan",
                label="Reset the plan",
                description="Cut scope, move toward conservation, and buy board confidence.",
            ),
            EventOption(
                id="defend_growth",
                label="Defend growth",
                description="Keep pressing growth and accept higher board pressure.",
            ),
        ],
    )


def _is_partner_qbr_eligible(state: GameState) -> bool:
    return _has_recent_event(
        state,
        {"partner_offer", "channel_conflict"},
        BALANCE.event_chain_recent_window_turns,
    ) and any(
        partnership.status is not PartnershipStatus.PAUSED for partnership in state.partnerships
    )


def _build_partner_qbr_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    partnership = max(
        [deal for deal in state.partnerships if deal.status is not PartnershipStatus.PAUSED],
        key=lambda deal: deal.conflict_pressure + deal.risk + deal.enablement_level,
    )
    target = _get_product_by_id(state.products, partnership.product_id)
    if target is None:
        target = _pick_best_product(
            [product for product in state.products if product.is_active],
            rng,
            score=lambda product: product.user_count + product.market_fit,
        )
    return PendingEvent(
        event_id="partner_qbr",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Channel Partner QBR",
        description=(
            f"Partners selling {target.name} want a clearer joint plan. "
            "You can deepen enablement for more sourced growth or pause the channel and simplify."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="channel_chain",
        chain_stage=2,
        target_product_id=target.id,
        options=[
            EventOption(
                id="double_enablement",
                label="Double down on enablement",
                description="Spend cash to reduce channel risk and add sourced demand.",
            ),
            EventOption(
                id="pause_channel",
                label="Pause the noisiest channel",
                description="Reduce conflict and board pressure, but give up some near-term users.",
            ),
        ],
    )


def _is_partner_breakdown_eligible(state: GameState) -> bool:
    pressure = calculate_endgame_pressure(state)
    portfolio = calculate_partnership_portfolio(state)
    return _has_recent_event(
        state,
        {"partner_qbr", "channel_conflict"},
        BALANCE.event_chain_recent_window_turns,
    ) and any(
        (
            partnership.status in {PartnershipStatus.STRAINED, PartnershipStatus.RECOVERY}
            or partnership.conflict_pressure + partnership.risk
            >= BALANCE.event_partner_breakdown_fatigue_threshold
            or pressure.channel_fragility
            >= BALANCE.event_partner_breakdown_channel_fragility_threshold
            or portfolio.concentration_risk >= 55
            or portfolio.rev_share_pressure >= 28
            or portfolio.commercial_dependency_score >= 68
            or portfolio.volatile_revenue_share_percent >= 40
            or portfolio.channel_volatility_index >= 58
            or portfolio.hotspot_revenue_share_percent >= 45
            or portfolio.recovery_drag_score >= 28
            or portfolio.paused_count > 0
            or portfolio.direct_sales_conflict_accounts > 0
            or portfolio.hotspot_dependency_score
            >= BALANCE.finance_planner_reactivate_dependency_threshold
        )
        for partnership in state.partnerships
    )


def _build_partner_breakdown_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    partnership = max(
        [deal for deal in state.partnerships if deal.status is not PartnershipStatus.PAUSED],
        key=lambda deal: deal.conflict_pressure + deal.risk,
    )
    target = _get_product_by_id(state.products, partnership.product_id)
    if target is None:
        target = _pick_best_product(
            [product for product in state.products if product.is_active],
            rng,
            score=lambda product: product.user_count + product.market_fit,
        )
    return PendingEvent(
        event_id="partner_breakdown",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Partner Breakdown Risk",
        description=(
            f"The channel around {target.name} is close to breaking down. "
            "You can fund a recovery sprint or freeze the lane and protect the core business."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="channel_chain",
        chain_stage=3,
        target_product_id=target.id,
        options=[
            EventOption(
                id="fund_recovery",
                label="Fund recovery",
                description="Spend cash to calm the partner and rebuild channel quality.",
            ),
            EventOption(
                id="freeze_lane",
                label="Freeze the lane",
                description="Pause the lane, protect the core business, and accept user loss.",
            ),
        ],
    )


def _is_partner_renegotiation_eligible(state: GameState) -> bool:
    return any(
        partnership.status is not PartnershipStatus.PAUSED
        and partnership.sourced_revenue > 0
        and partnership.conflict_pressure + partnership.risk
        >= BALANCE.event_partner_renegotiation_fatigue_threshold
        for partnership in state.partnerships
    ) and not _has_recent_event(
        state,
        {"partner_breakdown", "partner_qbr"},
        BALANCE.event_chain_recent_window_turns,
    )


def _build_partner_renegotiation_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    partnership = max(
        [deal for deal in state.partnerships if deal.status is not PartnershipStatus.PAUSED],
        key=lambda deal: deal.conflict_pressure + deal.risk + deal.enablement_level,
    )
    target = _get_product_by_id(state.products, partnership.product_id)
    return PendingEvent(
        event_id="partner_renegotiation",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Partner Renegotiation",
        description=(
            f"{partnership.name} wants cleaner economics before scaling {target.name} further. "
            "You can concede some margin to stabilize the lane or hold the line and risk "
            "slower growth."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="channel_chain",
        chain_stage=3,
        target_product_id=target.id,
        options=[
            EventOption(
                id="concede_margin",
                label="Concede margin",
                description=(
                    "Raise rev-share and calm the relationship before channel damage spreads."
                ),
            ),
            EventOption(
                id="hold_line",
                label="Hold the line",
                description=(
                    "Protect economics now, but accept user loss and higher board scrutiny."
                ),
            ),
        ],
    )


def _is_channel_concentration_crackdown_eligible(state: GameState) -> bool:
    portfolio = calculate_partnership_portfolio(state)
    return (
        portfolio.hotspot_channel != "-"
        and (
            portfolio.hotspot_dependency_score
            >= BALANCE.event_channel_concentration_crackdown_dependency_threshold
            or portfolio.hotspot_revenue_share_percent >= 42
        )
        and _has_recent_event(
            state,
            {"partner_breakdown", "partner_renegotiation", "buyer_reference_check"},
            BALANCE.event_chain_recent_window_turns,
        )
    )


def _build_channel_concentration_crackdown_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    portfolio = calculate_partnership_portfolio(state)
    candidates = [
        partnership
        for partnership in state.partnerships
        if partnership.status is not PartnershipStatus.PAUSED
        and partnership.channel.value == portfolio.hotspot_channel
    ]
    if not candidates:
        candidates = [
            partnership
            for partnership in state.partnerships
            if partnership.status is not PartnershipStatus.PAUSED
        ]
    partnership = max(
        candidates,
        key=lambda deal: (
            int(deal.sourced_revenue) + deal.conflict_pressure + deal.risk,
            deal.enablement_level,
            rng.randint(0, 10),
        ),
    )
    target = _get_product_by_id(state.products, partnership.product_id)
    if target is None:
        raise ValueError("This event expected a product target.")
    if partnership.channel.value == "reseller":
        title = "Reseller Concentration Crackdown"
        description = (
            f"{partnership.name} now drives too much of the reseller story around {target.name}. "
            "You can fund a firebreak to de-risk the lane or accept more commercial drag."
        )
    elif partnership.channel.value == "integration":
        title = "Integration Concentration Crackdown"
        description = (
            f"{partnership.name} is now concentrating too much integration risk around "
            f"{target.name}. "
            "You can fund a firebreak to de-risk implementations or absorb more drag."
        )
    else:
        title = "Marketplace Concentration Crackdown"
        description = (
            f"{partnership.name} now dominates marketplace throughput around {target.name}. "
            "You can fund a firebreak to de-risk billing exposure or accept more drag."
        )
    return PendingEvent(
        event_id="channel_concentration_crackdown",
        category=EventCategory.MARKET_OPPORTUNITY,
        title=title,
        description=description,
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="channel_chain",
        chain_stage=4,
        target_product_id=target.id,
        options=[
            EventOption(
                id="fund_firebreak",
                label="Fund a channel firebreak",
                description="Spend cash to cool dependency before concentration hardens.",
            ),
            EventOption(
                id="accept_drag",
                label="Accept the commercial drag",
                description="Protect cash now, but let concentration keep distorting execution.",
            ),
        ],
    )


def _is_independence_treasury_compact_eligible(state: GameState) -> bool:
    pressure = calculate_endgame_pressure(state)
    return (
        _has_recent_event(
            state,
            {"independence_cash_yield_pact"},
            BALANCE.event_chain_recent_window_turns,
        )
        and pressure.independence_discipline
        >= BALANCE.event_independence_treasury_compact_pressure_threshold
        and (
            state.capital_plan.reserve_share < BALANCE.capital_plan_low_reserve_share_threshold + 10
            or state.finance.covenant_risk >= 12
            or state.finance.debt_principal >= BALANCE.finance_debt_rollover_min_debt
            or state.company.cash_on_hand < state.capital_plan.reserve_target
        )
    )


def _build_independence_treasury_compact_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    return PendingEvent(
        event_id="independence_treasury_compact",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Independence Treasury Compact",
        description=(
            "The company can keep the independence story coherent only if reserve and covenant "
            "discipline move together again. You can ratify the treasury compact now or bridge "
            "the gap and accept more financing heat."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="capital_chain",
        chain_stage=10,
        options=[
            EventOption(
                id="ratify_treasury_compact",
                label="Ratify the treasury compact",
                description="Shift harder into reserve discipline and calmer covenant posture.",
            ),
            EventOption(
                id="bridge_treasury_gap",
                label="Bridge the treasury gap",
                description="Add cash now, but compound debt and covenant heat again.",
            ),
        ],
    )


def _is_reseller_enablement_gap_eligible(state: GameState) -> bool:
    portfolio = calculate_partnership_portfolio(state)
    reseller_partnerships = [
        partnership
        for partnership in state.partnerships
        if partnership.status is not PartnershipStatus.PAUSED
        and partnership.channel.value == "reseller"
    ]
    return bool(reseller_partnerships) and (
        _has_recent_event(
            state,
            {"partner_qbr", "channel_conflict"},
            BALANCE.event_chain_recent_window_turns,
        )
        or portfolio.hotspot_channel == "reseller"
        or any(
            partnership.enablement_level
            <= BALANCE.event_reseller_enablement_gap_enablement_threshold
            or partnership.conflict_pressure >= 44
            or partnership.risk >= 46
            for partnership in reseller_partnerships
        )
    )


def _build_reseller_enablement_gap_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    partnerships = [
        partnership
        for partnership in state.partnerships
        if partnership.status is not PartnershipStatus.PAUSED
        and partnership.channel.value == "reseller"
    ]
    partnership = max(
        partnerships,
        key=lambda deal: (
            deal.conflict_pressure + deal.risk - deal.enablement_level,
            int(deal.sourced_revenue),
            rng.randint(0, 10),
        ),
    )
    target = _get_product_by_id(state.products, partnership.product_id)
    if target is None:
        raise ValueError("This event expected a product target.")
    return PendingEvent(
        event_id="reseller_enablement_gap",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Reseller Enablement Gap",
        description=(
            f"{partnership.name} is slipping on enablement around {target.name}. You can fund a "
            "deeper reseller reset now or let the lane self-heal and accept more channel drag."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="channel_chain",
        chain_stage=5,
        target_product_id=target.id,
        options=[
            EventOption(
                id="fund_enablement_gap",
                label="Fund the enablement reset",
                description="Spend cash to rebuild reseller confidence and calm the lane.",
            ),
            EventOption(
                id="let_lane_self_heal",
                label="Let the lane self-heal",
                description="Protect cash now, but accept more reseller drag and conflict.",
            ),
        ],
    )


def _is_integration_cutover_risk_eligible(state: GameState) -> bool:
    portfolio = calculate_partnership_portfolio(state)
    integration_partnerships = [
        partnership
        for partnership in state.partnerships
        if partnership.status is not PartnershipStatus.PAUSED
        and partnership.channel.value == "integration"
    ]
    return bool(integration_partnerships) and (
        _has_recent_event(
            state,
            {"partner_breakdown", "buyer_operating_memo"},
            BALANCE.event_chain_recent_window_turns,
        )
        or portfolio.hotspot_channel == "integration"
        or any(
            partnership.risk >= BALANCE.event_integration_cutover_risk_risk_threshold
            or partnership.conflict_pressure >= 48
            for partnership in integration_partnerships
        )
    )


def _build_integration_cutover_risk_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    partnerships = [
        partnership
        for partnership in state.partnerships
        if partnership.status is not PartnershipStatus.PAUSED
        and partnership.channel.value == "integration"
    ]
    partnership = max(
        partnerships,
        key=lambda deal: (
            deal.risk + deal.conflict_pressure,
            int(deal.sourced_revenue),
            rng.randint(0, 10),
        ),
    )
    target = _get_product_by_id(state.products, partnership.product_id)
    if target is None:
        raise ValueError("This event expected a product target.")
    return PendingEvent(
        event_id="integration_cutover_risk",
        category=EventCategory.PRODUCT_INCIDENT,
        title="Integration Cutover Risk",
        description=(
            f"{partnership.name} is turning integration cutover risk into customer drag around "
            f"{target.name}. You can staff the cutover team or ship around the problem and "
            "accept more support stress."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="channel_chain",
        chain_stage=5,
        target_product_id=target.id,
        options=[
            EventOption(
                id="staff_cutover_team",
                label="Staff the cutover team",
                description="Spend cash to calm integration friction and onboarding risk.",
            ),
            EventOption(
                id="ship_around_risk",
                label="Ship around the risk",
                description="Protect cash now, but accept more integration drag and support pain.",
            ),
        ],
    )


def _is_marketplace_chargeback_wave_eligible(state: GameState) -> bool:
    portfolio = calculate_partnership_portfolio(state)
    marketplace_partnerships = [
        partnership
        for partnership in state.partnerships
        if partnership.status is not PartnershipStatus.PAUSED
        and partnership.channel.value == "marketplace"
    ]
    return bool(marketplace_partnerships) and (
        _has_recent_event(
            state,
            {"renewal_risk", "channel_concentration_crackdown"},
            BALANCE.event_chain_recent_window_turns,
        )
        or portfolio.hotspot_channel == "marketplace"
        or any(
            account.status is not CustomerAccountStatus.CHURNED
            and (
                account.invoice_risk >= BALANCE.event_marketplace_chargeback_wave_payment_threshold
                or account.failed_payment_risk
                >= BALANCE.event_marketplace_chargeback_wave_payment_threshold
            )
            for account in state.customer_accounts
        )
    )


def _build_marketplace_chargeback_wave_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    partnerships = [
        partnership
        for partnership in state.partnerships
        if partnership.status is not PartnershipStatus.PAUSED
        and partnership.channel.value == "marketplace"
    ]
    partnership = max(
        partnerships,
        key=lambda deal: (
            int(deal.sourced_revenue) + deal.risk + deal.conflict_pressure,
            rng.randint(0, 10),
        ),
    )
    target = _get_product_by_id(state.products, partnership.product_id)
    if target is None:
        raise ValueError("This event expected a product target.")
    return PendingEvent(
        event_id="marketplace_chargeback_wave",
        category=EventCategory.REPUTATION_INCIDENT,
        title="Marketplace Chargeback Wave",
        description=(
            f"{partnership.name} is absorbing a chargeback wave around {target.name}. You can "
            "fund a billing-ops reset now or tighten refund rules and accept more renewal drag."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="channel_chain",
        chain_stage=5,
        target_product_id=target.id,
        options=[
            EventOption(
                id="fund_chargeback_ops",
                label="Fund chargeback ops",
                description="Spend cash to calm billing pressure and repair marketplace trust.",
            ),
            EventOption(
                id="tighten_refund_rules",
                label="Tighten refund rules",
                description=(
                    "Protect cash now, but accept more billing friction and reputation risk."
                ),
            ),
        ],
    )


def _is_reseller_reference_summit_eligible(state: GameState) -> bool:
    portfolio = calculate_partnership_portfolio(state)
    reseller_partnerships = [
        partnership
        for partnership in state.partnerships
        if partnership.status is not PartnershipStatus.PAUSED
        and partnership.channel.value == "reseller"
    ]
    return bool(reseller_partnerships) and (
        _has_recent_event(
            state,
            {"reseller_enablement_gap"},
            BALANCE.event_chain_recent_window_turns,
        )
        or (
            portfolio.hotspot_channel == "reseller"
            and portfolio.hotspot_dependency_score
            >= BALANCE.event_reseller_reference_summit_dependency_threshold
        )
        or any(
            partnership.conflict_pressure >= 46 or partnership.risk >= 48
            for partnership in reseller_partnerships
        )
    )


def _build_reseller_reference_summit_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    partnerships = [
        partnership
        for partnership in state.partnerships
        if partnership.status is not PartnershipStatus.PAUSED
        and partnership.channel.value == "reseller"
    ]
    partnership = max(
        partnerships,
        key=lambda deal: (
            deal.conflict_pressure + deal.risk - deal.enablement_level,
            int(deal.sourced_revenue),
            rng.randint(0, 10),
        ),
    )
    target = _get_product_by_id(state.products, partnership.product_id)
    if target is None:
        raise ValueError("This event expected a product target.")
    return PendingEvent(
        event_id="reseller_reference_summit",
        category=EventCategory.MARKET_OPPORTUNITY,
        title="Reseller Reference Summit",
        description=(
            f"{partnership.name} needs a tighter reference summit around {target.name}. You can "
            "fund the summit now or protect cash and accept more reseller drag."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="channel_chain",
        chain_stage=6,
        target_product_id=target.id,
        options=[
            EventOption(
                id="fund_reseller_summit",
                label="Fund the reseller summit",
                description="Spend cash to rebuild trust and calm reseller dependency.",
            ),
            EventOption(
                id="defer_reseller_summit",
                label="Defer the summit",
                description="Protect cash now, but let reseller drag and conflict keep rising.",
            ),
        ],
    )


def _is_integration_cutover_board_eligible(state: GameState) -> bool:
    portfolio = calculate_partnership_portfolio(state)
    integration_partnerships = [
        partnership
        for partnership in state.partnerships
        if partnership.status is not PartnershipStatus.PAUSED
        and partnership.channel.value == "integration"
    ]
    return bool(integration_partnerships) and (
        _has_recent_event(
            state,
            {"integration_cutover_risk"},
            BALANCE.event_chain_recent_window_turns,
        )
        or (
            portfolio.hotspot_channel == "integration"
            and portfolio.hotspot_dependency_score
            >= BALANCE.event_integration_cutover_board_pressure_threshold
        )
        or any(
            partnership.risk >= BALANCE.event_integration_cutover_board_pressure_threshold
            or partnership.conflict_pressure >= 50
            for partnership in integration_partnerships
        )
    )


def _build_integration_cutover_board_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    partnerships = [
        partnership
        for partnership in state.partnerships
        if partnership.status is not PartnershipStatus.PAUSED
        and partnership.channel.value == "integration"
    ]
    partnership = max(
        partnerships,
        key=lambda deal: (
            deal.risk + deal.conflict_pressure,
            int(deal.sourced_revenue),
            rng.randint(0, 10),
        ),
    )
    target = _get_product_by_id(state.products, partnership.product_id)
    if target is None:
        raise ValueError("This event expected a product target.")
    return PendingEvent(
        event_id="integration_cutover_board",
        category=EventCategory.PRODUCT_INCIDENT,
        title="Integration Cutover Board",
        description=(
            f"{partnership.name} needs a harder cutover board around {target.name}. You can fund "
            "the board now or absorb more implementation drag."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="channel_chain",
        chain_stage=6,
        target_product_id=target.id,
        options=[
            EventOption(
                id="fund_cutover_board",
                label="Fund the cutover board",
                description="Spend cash to calm integration drag and protect onboarding quality.",
            ),
            EventOption(
                id="accept_cutover_drag",
                label="Accept cutover drag",
                description="Protect cash now, but let implementation friction keep spreading.",
            ),
        ],
    )


def _is_marketplace_dispute_program_eligible(state: GameState) -> bool:
    portfolio = calculate_partnership_portfolio(state)
    marketplace_partnerships = [
        partnership
        for partnership in state.partnerships
        if partnership.status is not PartnershipStatus.PAUSED
        and partnership.channel.value == "marketplace"
    ]
    return bool(marketplace_partnerships) and (
        _has_recent_event(
            state,
            {"marketplace_chargeback_wave"},
            BALANCE.event_chain_recent_window_turns,
        )
        or portfolio.hotspot_channel == "marketplace"
        or any(
            account.status is not CustomerAccountStatus.CHURNED
            and (
                account.invoice_risk >= BALANCE.event_marketplace_dispute_program_payment_threshold
                or account.failed_payment_risk
                >= BALANCE.event_marketplace_dispute_program_payment_threshold
            )
            for account in state.customer_accounts
        )
    )


def _build_marketplace_dispute_program_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    partnerships = [
        partnership
        for partnership in state.partnerships
        if partnership.status is not PartnershipStatus.PAUSED
        and partnership.channel.value == "marketplace"
    ]
    partnership = max(
        partnerships,
        key=lambda deal: (
            int(deal.sourced_revenue) + deal.risk + deal.conflict_pressure,
            rng.randint(0, 10),
        ),
    )
    target = _get_product_by_id(state.products, partnership.product_id)
    if target is None:
        raise ValueError("This event expected a product target.")
    return PendingEvent(
        event_id="marketplace_dispute_program",
        category=EventCategory.REPUTATION_INCIDENT,
        title="Marketplace Dispute Program",
        description=(
            f"{partnership.name} needs a harder dispute program around {target.name}. You can "
            "fund it now or absorb more billing and renewal drag."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="channel_chain",
        chain_stage=6,
        target_product_id=target.id,
        options=[
            EventOption(
                id="fund_dispute_program",
                label="Fund the dispute program",
                description="Spend cash to calm marketplace billing pressure and renewal risk.",
            ),
            EventOption(
                id="absorb_dispute_drag",
                label="Absorb the dispute drag",
                description=(
                    "Protect cash now, but let payment friction and trust drag keep rising."
                ),
            ),
        ],
    )


def _is_board_recovery_window_eligible(state: GameState) -> bool:
    pressure = calculate_endgame_pressure(state)
    return _has_recent_event(
        state,
        {"board_reckoning", "board_scrutiny"},
        BALANCE.event_chain_recent_window_turns,
    ) and (
        state.finance.board_recovery_turns_remaining > 0
        or state.finance.governance_crisis_active
        or pressure.board_reset_risk >= BALANCE.event_board_recovery_window_reset_risk_threshold
    )


def _build_board_recovery_window_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    return PendingEvent(
        event_id="board_recovery_window",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Board Recovery Window",
        description=(
            "Directors are giving the company a short window to prove recovery discipline. "
            "You can fund tighter controls or narrow scope and reset expectations."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="governance_chain",
        chain_stage=3,
        options=[
            EventOption(
                id="fund_control_room",
                label="Fund a control room",
                description="Spend cash to improve confidence, score, and governance optics.",
            ),
            EventOption(
                id="narrow_scope",
                label="Narrow scope",
                description="Reduce pressure by cutting scope and leaning into board focus.",
            ),
        ],
    )


def _is_board_reset_showdown_eligible(state: GameState) -> bool:
    pressure = calculate_endgame_pressure(state)
    return (
        _has_recent_event(
            state,
            {"board_recovery_window", "board_reckoning"},
            BALANCE.event_chain_recent_window_turns,
        )
        and pressure.board_reset_risk >= BALANCE.event_board_reset_showdown_pressure_threshold
        and (
            state.finance.governance_crisis_active
            or state.finance.board_warning_level >= 2
            or pressure.restructure_heat >= 60
            or state.finance.board_resolution_due
        )
    )


def _build_board_reset_showdown_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    return PendingEvent(
        event_id="board_reset_showdown",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Board Reset Showdown",
        description=(
            "Directors are now close to forcing a harder reset. You can accept a tighter reset "
            "plan and protect resilience, or defy the reset and absorb more governance heat."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="governance_chain",
        chain_stage=4,
        options=[
            EventOption(
                id="accept_reset_plan",
                label="Accept the reset plan",
                description="Shift toward resilience and calm governance risk at a brand cost.",
            ),
            EventOption(
                id="defy_reset",
                label="Defy the reset",
                description="Protect the current plan now, but board heat compounds sharply.",
            ),
        ],
    )


def _is_board_reset_execution_plan_eligible(state: GameState) -> bool:
    pressure = calculate_endgame_pressure(state)
    return (
        _has_recent_event(
            state,
            {"board_reset_showdown"},
            BALANCE.event_chain_recent_window_turns,
        )
        and pressure.board_reset_risk >= BALANCE.event_board_reset_execution_plan_pressure_threshold
        and (
            state.finance.governance_crisis_active
            or state.finance.board_warning_level >= 2
            or state.finance.board_resolution_due
            or pressure.restructure_heat >= 60
        )
    )


def _build_board_reset_execution_plan_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    return PendingEvent(
        event_id="board_reset_execution_plan",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Board Reset Execution Plan",
        description=(
            "Directors now want proof that the reset will be executed, not just announced. "
            "You can codify the operating reset now or fight for more optionality and absorb "
            "another round of governance heat."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="governance_chain",
        chain_stage=5,
        options=[
            EventOption(
                id="codify_operating_reset",
                label="Codify the operating reset",
                description="Shift further into resilience and calm the board again.",
            ),
            EventOption(
                id="fight_for_optionality",
                label="Fight for optionality",
                description="Protect room to maneuver, but let reset pressure rise again.",
            ),
        ],
    )


def _is_board_reset_operating_cadence_eligible(state: GameState) -> bool:
    pressure = calculate_endgame_pressure(state)
    return (
        _has_recent_event(
            state,
            {"board_reset_execution_plan"},
            BALANCE.event_chain_recent_window_turns,
        )
        and pressure.board_reset_risk
        >= BALANCE.event_board_reset_operating_cadence_pressure_threshold
        and (
            state.finance.board_warning_level >= 1
            or state.finance.governance_crisis_active
            or pressure.restructure_heat >= 55
        )
    )


def _build_board_reset_operating_cadence_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    return PendingEvent(
        event_id="board_reset_operating_cadence",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Board Reset Operating Cadence",
        description=(
            "Directors now want a hard weekly cadence behind the reset. You can install the "
            "cadence now or slip it and accept another round of reset heat."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="governance_chain",
        chain_stage=6,
        options=[
            EventOption(
                id="install_reset_cadence",
                label="Install the reset cadence",
                description=(
                    "Shift harder into resilience and prove the reset is being run tightly."
                ),
            ),
            EventOption(
                id="slip_reset_cadence",
                label="Slip the cadence",
                description=(
                    "Protect optionality now, but let board pressure and restructure heat rise."
                ),
            ),
        ],
    )


def _is_capital_market_freeze_eligible(state: GameState) -> bool:
    return _has_recent_event(
        state,
        {"bridge_round", "down_round_pressure", "loan_covenant"},
        BALANCE.event_chain_recent_window_turns,
    ) or (
        state.finance.investor_pressure >= BALANCE.event_capital_market_freeze_pressure_threshold
        and state.company.cash_on_hand < state.capital_plan.reserve_target
    )


def _build_capital_market_freeze_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    return PendingEvent(
        event_id="capital_market_freeze",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Capital Market Freeze",
        description=(
            "Financing sentiment has tightened. You can freeze hiring and preserve runway or "
            "accept expensive bridge terms to keep the current plan alive."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="capital_chain",
        chain_stage=2,
        options=[
            EventOption(
                id="freeze_hiring",
                label="Freeze hiring and preserve runway",
                description="Protect covenants and cash, but morale slips across the team.",
            ),
            EventOption(
                id="accept_bridge_terms",
                label="Accept bridge terms",
                description="Add cash now, but dilution climbs and the story gets harder.",
            ),
        ],
    )


def _is_succession_gap_eligible(state: GameState) -> bool:
    return any(
        employee.succession_risk >= BALANCE.event_succession_gap_risk_threshold
        for employee in state.employees
        if employee.role
        in {
            EmployeeRole.ENGINEER,
            EmployeeRole.PRODUCT_MANAGER,
            EmployeeRole.DESIGNER,
        }
    )


def _build_succession_gap_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    target = _pick_best_employee(
        [
            employee
            for employee in state.employees
            if employee.succession_risk >= BALANCE.event_succession_gap_risk_threshold
        ],
        rng,
        score=lambda employee: employee.succession_risk + employee.leadership_score,
    )
    return PendingEvent(
        event_id="succession_gap",
        category=EventCategory.EMPLOYEE_ISSUE,
        title="Succession Gap",
        description=(
            f"{target.full_name} is carrying too much of the operating load. "
            "You can elevate internal backup capacity now or accept growing attrition risk."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="org_chain",
        chain_stage=1,
        target_employee_id=target.id,
        options=[
            EventOption(
                id="promote_internal_lead",
                label="Elevate internal backup",
                description="Reduce succession risk and stabilize morale around the team.",
            ),
            EventOption(
                id="wait_and_hope",
                label="Wait and hope",
                description="Spend nothing now, but attrition and team-health pressure rise.",
            ),
        ],
    )


def _is_strategic_crossroads_eligible(state: GameState) -> bool:
    readiness = calculate_endgame_readiness(state)
    return (
        max(
            readiness.ipo_readiness_score,
            readiness.acquisition_interest_score,
            readiness.independence_score,
        )
        >= BALANCE.event_strategic_crossroads_readiness_threshold
        and state.company.current_turn >= 8
        and not _has_recent_event(
            state,
            {"exit_interest", "board_recovery_window", "capital_market_freeze"},
            BALANCE.event_chain_recent_window_turns,
        )
    )


def _build_strategic_crossroads_event(
    state: GameState,
    rng: RandomLike,
    cooldown_turns: int,
) -> PendingEvent:
    del rng
    readiness = calculate_endgame_readiness(state)
    target = _get_primary_product(state.products)
    return PendingEvent(
        event_id="strategic_crossroads",
        category=EventCategory.FUNDING_OPPORTUNITY,
        title="Strategic Crossroads",
        description=(
            f"{target.name} is pulling the company toward a "
            f"{readiness.strategic_outlook.replace('_', ' ')} story. "
            "You can formalize that path for the board or defend independence and tighten "
            "operations."
        ),
        triggered_turn=state.company.current_turn,
        cooldown_turns=cooldown_turns,
        chain_id="endgame_chain",
        chain_stage=1,
        target_product_id=target.id,
        options=[
            EventOption(
                id="formalize_process",
                label="Formalize the process",
                description="Spend cash to sharpen the story and improve board conviction.",
            ),
            EventOption(
                id="defend_independence",
                label="Defend independence",
                description="Relieve outside pressure and strengthen team conviction instead.",
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


def _get_primary_product(products: list[Product]) -> Product:
    active_products = [product for product in products if product.is_active]
    if not active_products:
        raise ValueError("This event expected at least one active product.")
    return max(active_products, key=lambda product: (product.user_count, product.quality))


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
