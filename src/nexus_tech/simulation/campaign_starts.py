"""Archive-gated campaign start modifiers for replayable runs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import (
    BoardAsk,
    BoardResolution,
    CapitalPlan,
    CapitalPlanMode,
    CapitalSourcePreference,
    ContractBillingModel,
    ContractCadence,
    CustomerAccount,
    CustomerAccountStatus,
    GameState,
    MarketSegment,
    PartnerChannel,
    PartnershipDeal,
    PartnershipStatus,
    SubscriptionPackage,
    SupportLaneFocus,
    SupportTier,
)
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.planning import build_quarter_plan
from nexus_tech.simulation.support import clamp_int

STANDARD_CAMPAIGN_START_ID = "standard"


@dataclass(frozen=True)
class CampaignStartDefinition:
    """One selectable campaign start path surfaced in the CLI."""

    start_id: str
    title: str
    description: str
    unlock_reward_type: str | None
    unlock_reward_id: str | None
    turn_hint: str
    pressure_hint: str


def get_campaign_start_definitions() -> tuple[CampaignStartDefinition, ...]:
    """Return all available campaign start profiles."""

    return (
        CampaignStartDefinition(
            start_id=STANDARD_CAMPAIGN_START_ID,
            title="Standard Opening",
            description="Play the chosen scenario exactly as authored.",
            unlock_reward_type=None,
            unlock_reward_id=None,
            turn_hint="turn 1",
            pressure_hint="low",
        ),
        CampaignStartDefinition(
            start_id="campaign_ladder_climb",
            title="Ladder Climb Start",
            description=(
                "Start several turns into growth with more scale, more cash, and more pressure."
            ),
            unlock_reward_type="scenario",
            unlock_reward_id="campaign_ladder_climb",
            turn_hint="turn 6",
            pressure_hint="medium",
        ),
        CampaignStartDefinition(
            start_id="board_recovery_crucible",
            title="Board Recovery Start",
            description=(
                "Enter a tense late-early run where governance, reliability, and board trust "
                "already need active management."
            ),
            unlock_reward_type="scenario",
            unlock_reward_id="board_recovery_crucible",
            turn_hint="turn 8",
            pressure_hint="high",
        ),
        CampaignStartDefinition(
            start_id="channel_rebuild_marathon",
            title="Channel Rebuild Start",
            description=(
                "Start inside a noisier commercial stack with support pressure and strained "
                "channel relationships already live."
            ),
            unlock_reward_type="scenario",
            unlock_reward_id="channel_rebuild_marathon",
            turn_hint="turn 8",
            pressure_hint="high",
        ),
        CampaignStartDefinition(
            start_id="ipo_readiness_launchpad",
            title="IPO Readiness Launchpad",
            description=(
                "Jump into a later-stage institutional run with stronger governance optics, "
                "larger accounts, and public-market scrutiny already taking shape."
            ),
            unlock_reward_type="campaign_start",
            unlock_reward_id="ipo_readiness_launchpad",
            turn_hint="turn 14",
            pressure_hint="high",
        ),
        CampaignStartDefinition(
            start_id="acquisition_diligence_sprint",
            title="Acquisition Diligence Sprint",
            description=(
                "Start near an M&A-style peak where enterprise accounts, partner revenue, "
                "and diligence risk all matter immediately."
            ),
            unlock_reward_type="campaign_start",
            unlock_reward_id="acquisition_diligence_sprint",
            turn_hint="turn 15",
            pressure_hint="high",
        ),
        CampaignStartDefinition(
            start_id="independence_compounder",
            title="Independence Compounder",
            description=(
                "Begin from a disciplined later-stage company with reserve targets, debt "
                "choices, and independent durability already in play."
            ),
            unlock_reward_type="campaign_start",
            unlock_reward_id="independence_compounder",
            turn_hint="turn 16",
            pressure_hint="medium",
        ),
    )


def get_campaign_start_definition(start_id: str) -> CampaignStartDefinition:
    """Return one campaign start profile by id."""

    for definition in get_campaign_start_definitions():
        if definition.start_id == start_id:
            return definition
    raise ValueError(f"Unknown campaign start '{start_id}'.")


def list_campaign_starts() -> tuple[CampaignStartDefinition, ...]:
    """Return campaign start definitions for CLI presentation."""

    return get_campaign_start_definitions()


def apply_campaign_start(state: GameState, start_id: str) -> str:
    """Mutate a fresh scenario state into one unlocked campaign start variant."""

    if start_id == STANDARD_CAMPAIGN_START_ID:
        return "Standard scenario opening applied."
    if start_id == "campaign_ladder_climb":
        return _apply_campaign_ladder_climb(state)
    if start_id == "board_recovery_crucible":
        return _apply_board_recovery_crucible(state)
    if start_id == "channel_rebuild_marathon":
        return _apply_channel_rebuild_marathon(state)
    if start_id == "ipo_readiness_launchpad":
        return _apply_ipo_readiness_launchpad(state)
    if start_id == "acquisition_diligence_sprint":
        return _apply_acquisition_diligence_sprint(state)
    if start_id == "independence_compounder":
        return _apply_independence_compounder(state)
    raise ValueError(f"Unknown campaign start '{start_id}'.")


def _apply_campaign_ladder_climb(state: GameState) -> str:
    _shift_state_to_turn(state, 6)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand + Decimal("2800.00"))
    state.company.reputation = clamp_int(state.company.reputation + 6)
    state.finance.board_pressure = clamp_int(state.finance.board_pressure + 6)
    state.finance.investor_pressure = clamp_int(state.finance.investor_pressure + 4)
    state.support_program.backlog_queue = max(state.support_program.backlog_queue, 6)
    state.support_program.escalation_queue = max(state.support_program.escalation_queue, 2)

    for index, product in enumerate([product for product in state.products if product.is_active]):
        if index == 0:
            product.user_count += 75
            product.market_fit = clamp_int(product.market_fit + 8)
            product.quality = clamp_int(product.quality + 4)
            product.feature_count += 1
            product.package_catalog_depth += 1
            product.add_on_catalog_depth += 1
        else:
            product.user_count += 20
            product.market_fit = clamp_int(product.market_fit + 3)

    if state.competitors:
        state.competitors[0].momentum = clamp_int(state.competitors[0].momentum + 8)
        state.competitors[0].funding_level = min(5, state.competitors[0].funding_level + 1)

    return "Campaign start applied: ladder climb at turn 6 with early scale and visible pressure."


def _apply_board_recovery_crucible(state: GameState) -> str:
    _shift_state_to_turn(state, 8)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand + Decimal("1800.00"))
    state.company.reputation = clamp_int(state.company.reputation + 3)
    state.finance.board_pressure = max(state.finance.board_pressure, 26)
    state.finance.governance_risk = max(state.finance.governance_risk, 18)
    state.finance.board_confidence = min(state.finance.board_confidence, 50)
    state.finance.active_board_ask = BoardAsk.RELIABILITY
    state.finance.board_recovery_focus = BoardAsk.RELIABILITY
    state.finance.board_recovery_turns_remaining = max(
        state.finance.board_recovery_turns_remaining,
        3,
    )
    state.finance.board_resolution_due = True
    state.finance.board_resolution_window = max(
        state.finance.board_resolution_window,
        BALANCE.board_resolution_window_turns,
    )
    state.finance.board_resolution = BoardResolution.TARGETED_RESET
    state.finance.board_resolution_miss_streak = max(state.finance.board_resolution_miss_streak, 1)
    state.support_program.backlog_queue = max(state.support_program.backlog_queue, 10)
    state.support_program.escalation_queue = max(state.support_program.escalation_queue, 3)
    state.support_program.lane_focus = SupportLaneFocus.ENTERPRISE

    primary_product = _get_primary_product(state)
    primary_product.quality = clamp_int(primary_product.quality + 5)
    primary_product.bug_level = clamp_int(primary_product.bug_level + 7)
    primary_product.market_fit = clamp_int(primary_product.market_fit + 4)

    if not state.customer_accounts:
        state.customer_accounts.append(
            CustomerAccount(
                name="Northwind Risk Office",
                product_id=primary_product.id,
                segment=MarketSegment.ENTERPRISE,
                contract_value=Decimal("1180.00"),
                plan_tier=primary_product.pricing_tier,
                subscription_package=SubscriptionPackage.GROWTH,
                support_tier=SupportTier.WHITE_GLOVE,
                contract_cadence=ContractCadence.ANNUAL,
                billing_model=ContractBillingModel.FLAT,
                satisfaction=60,
                onboarding_health=54,
                support_load=36,
                open_tickets=9,
                sla_breach_risk=44,
                invoice_risk=10,
                failed_payment_risk=6,
                escalation_count=1,
                expansion_potential=66,
                renewal_health=57,
                renewal_turn=state.company.current_turn + 2,
                churn_risk=22,
                status=CustomerAccountStatus.ACTIVE,
            )
        )

    return "Campaign start applied: board recovery crucible with reliability pressure already live."


def _apply_channel_rebuild_marathon(state: GameState) -> str:
    _shift_state_to_turn(state, 8)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand + Decimal("2200.00"))
    state.company.reputation = clamp_int(state.company.reputation + 4)
    state.finance.board_pressure = clamp_int(state.finance.board_pressure + 7)
    state.finance.governance_risk = clamp_int(state.finance.governance_risk + 4)
    state.support_program.backlog_queue = max(state.support_program.backlog_queue, 12)
    state.support_program.escalation_queue = max(state.support_program.escalation_queue, 4)
    state.support_program.lane_focus = SupportLaneFocus.ENTERPRISE

    primary_product = _get_primary_product(state)
    primary_product.market_fit = clamp_int(primary_product.market_fit + 6)
    primary_product.package_catalog_depth += 1
    primary_product.add_on_catalog_depth += 1

    if not state.customer_accounts:
        state.customer_accounts.append(
            CustomerAccount(
                name="Atlas Procurement Group",
                product_id=primary_product.id,
                segment=MarketSegment.ENTERPRISE,
                contract_value=Decimal("1240.00"),
                plan_tier=primary_product.pricing_tier,
                subscription_package=SubscriptionPackage.ENTERPRISE_SUITE,
                support_tier=SupportTier.PRIORITY,
                contract_cadence=ContractCadence.ANNUAL,
                billing_model=ContractBillingModel.SEAT_BASED,
                seat_count=18,
                satisfaction=62,
                onboarding_health=58,
                support_load=34,
                open_tickets=10,
                sla_breach_risk=48,
                invoice_risk=18,
                failed_payment_risk=14,
                dunning_steps=1,
                escalation_count=1,
                expansion_potential=70,
                renewal_health=56,
                renewal_turn=state.company.current_turn + 2,
                churn_risk=24,
                status=CustomerAccountStatus.ACTIVE,
            )
        )

    if not state.partnerships:
        state.partnerships.extend(
            [
                PartnershipDeal(
                    name=f"{primary_product.name} Reseller Network",
                    product_id=primary_product.id,
                    channel=PartnerChannel.RESELLER,
                    status=PartnershipStatus.STRAINED,
                    quality=62,
                    risk=48,
                    enablement_level=34,
                    sourced_revenue=Decimal("1800.00"),
                    sourced_users=28,
                    conflict_pressure=42,
                    started_turn=state.company.current_turn - 2,
                    last_review_turn=state.company.current_turn - 3,
                    summary="Inherited reseller lane now needs cleanup.",
                ),
                PartnershipDeal(
                    name=f"{primary_product.name} Marketplace Edge",
                    product_id=primary_product.id,
                    channel=PartnerChannel.MARKETPLACE,
                    status=PartnershipStatus.RECOVERY,
                    quality=58,
                    risk=44,
                    enablement_level=30,
                    sourced_revenue=Decimal("1120.00"),
                    sourced_users=18,
                    conflict_pressure=36,
                    started_turn=state.company.current_turn - 2,
                    last_review_turn=state.company.current_turn - 2,
                    summary="Marketplace lane is recovering but still fragile.",
                ),
            ]
        )

    return "Campaign start applied: channel rebuild marathon with live partner and support drag."


def _apply_ipo_readiness_launchpad(state: GameState) -> str:
    _shift_state_to_turn(state, 14)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand + Decimal("4800.00"))
    state.company.reputation = clamp_int(state.company.reputation + 10)
    state.finance.board_confidence = max(state.finance.board_confidence, 68)
    state.finance.board_score = max(state.finance.board_score, 66)
    state.finance.board_profitability_score = max(state.finance.board_profitability_score, 64)
    state.finance.board_reliability_score = max(state.finance.board_reliability_score, 67)
    state.finance.board_team_health_score = max(state.finance.board_team_health_score, 61)
    state.finance.board_portfolio_focus_score = max(
        state.finance.board_portfolio_focus_score,
        63,
    )
    state.finance.board_pressure = max(state.finance.board_pressure, 18)
    state.finance.governance_risk = max(state.finance.governance_risk, 10)
    state.finance.investor_pressure = max(state.finance.investor_pressure, 10)
    _replace_capital_plan(
        state,
        mode=CapitalPlanMode.BALANCED,
        source_preference=CapitalSourcePreference.ANGEL,
        reserve_target=Decimal("6500.00"),
        product_investment_share=36,
        go_to_market_share=34,
        reserve_share=30,
    )
    state.support_program.backlog_queue = max(state.support_program.backlog_queue, 8)
    state.support_program.escalation_queue = max(state.support_program.escalation_queue, 3)
    state.support_program.lane_focus = SupportLaneFocus.ENTERPRISE

    primary_product = _get_primary_product(state)
    primary_product.user_count += 170
    primary_product.quality = clamp_int(primary_product.quality + 8)
    primary_product.market_fit = clamp_int(primary_product.market_fit + 10)
    primary_product.feature_count += 1
    primary_product.package_catalog_depth += 1
    primary_product.add_on_catalog_depth += 1

    _ensure_customer_account(
        state,
        name="Institutional Audit Group",
        product_id=primary_product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("1680.00"),
        subscription_package=SubscriptionPackage.ENTERPRISE_SUITE,
        support_tier=SupportTier.WHITE_GLOVE,
        billing_model=ContractBillingModel.SEAT_BASED,
        seat_count=22,
        satisfaction=70,
        onboarding_health=66,
        support_load=38,
        open_tickets=8,
        sla_breach_risk=40,
        invoice_risk=8,
        failed_payment_risk=4,
        escalation_count=1,
        expansion_potential=74,
        renewal_health=64,
        renewal_turn=state.company.current_turn + 2,
        churn_risk=18,
    )
    _ensure_customer_account(
        state,
        name="Regulated Ops Network",
        product_id=primary_product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("1440.00"),
        subscription_package=SubscriptionPackage.GROWTH,
        support_tier=SupportTier.PRIORITY,
        billing_model=ContractBillingModel.FLAT,
        satisfaction=68,
        onboarding_health=63,
        support_load=30,
        open_tickets=6,
        sla_breach_risk=36,
        invoice_risk=6,
        failed_payment_risk=3,
        expansion_potential=68,
        renewal_health=62,
        renewal_turn=state.company.current_turn + 3,
        churn_risk=16,
    )
    return "Campaign start applied: IPO readiness launchpad with institutional pressure live."


def _apply_acquisition_diligence_sprint(state: GameState) -> str:
    _shift_state_to_turn(state, 15)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand + Decimal("4300.00"))
    state.company.reputation = clamp_int(state.company.reputation + 9)
    state.finance.board_pressure = max(state.finance.board_pressure, 20)
    state.finance.governance_risk = max(state.finance.governance_risk, 14)
    state.finance.board_confidence = max(state.finance.board_confidence, 60)
    state.finance.investor_pressure = max(state.finance.investor_pressure, 15)
    _replace_capital_plan(
        state,
        mode=CapitalPlanMode.EXPAND,
        source_preference=CapitalSourcePreference.VENTURE,
        reserve_target=Decimal("5200.00"),
        product_investment_share=32,
        go_to_market_share=43,
        reserve_share=25,
    )
    state.support_program.backlog_queue = max(state.support_program.backlog_queue, 11)
    state.support_program.escalation_queue = max(state.support_program.escalation_queue, 4)
    state.support_program.lane_focus = SupportLaneFocus.ENTERPRISE

    primary_product = _get_primary_product(state)
    primary_product.user_count += 145
    primary_product.market_fit = clamp_int(primary_product.market_fit + 9)
    primary_product.quality = clamp_int(primary_product.quality + 6)
    primary_product.package_catalog_depth += 2
    primary_product.add_on_catalog_depth += 1

    _ensure_customer_account(
        state,
        name="Due Diligence Anchor",
        product_id=primary_product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("1880.00"),
        subscription_package=SubscriptionPackage.ENTERPRISE_SUITE,
        support_tier=SupportTier.WHITE_GLOVE,
        billing_model=ContractBillingModel.SEAT_BASED,
        seat_count=24,
        satisfaction=67,
        onboarding_health=61,
        support_load=40,
        open_tickets=10,
        sla_breach_risk=46,
        invoice_risk=12,
        failed_payment_risk=6,
        escalation_count=1,
        expansion_potential=78,
        renewal_health=58,
        renewal_turn=state.company.current_turn + 2,
        churn_risk=22,
    )
    _ensure_customer_account(
        state,
        name="Channel-Sourced Enterprise",
        product_id=primary_product.id,
        segment=MarketSegment.ENTERPRISE,
        contract_value=Decimal("1540.00"),
        subscription_package=SubscriptionPackage.GROWTH,
        support_tier=SupportTier.PRIORITY,
        billing_model=ContractBillingModel.USAGE_BASED,
        usage_units=42,
        satisfaction=65,
        onboarding_health=58,
        support_load=34,
        open_tickets=9,
        sla_breach_risk=44,
        invoice_risk=18,
        failed_payment_risk=9,
        dunning_steps=1,
        expansion_potential=72,
        renewal_health=56,
        renewal_turn=state.company.current_turn + 2,
        churn_risk=24,
    )
    if not state.partnerships:
        state.partnerships.extend(
            [
                PartnershipDeal(
                    name=f"{primary_product.name} Integration Alliance",
                    product_id=primary_product.id,
                    channel=PartnerChannel.INTEGRATION,
                    status=PartnershipStatus.ACTIVE,
                    quality=66,
                    risk=38,
                    enablement_level=42,
                    sourced_revenue=Decimal("2600.00"),
                    sourced_users=36,
                    conflict_pressure=34,
                    started_turn=state.company.current_turn - 3,
                    last_review_turn=state.company.current_turn - 2,
                    summary="Integration lane is creating revenue but draws diligence scrutiny.",
                ),
                PartnershipDeal(
                    name=f"{primary_product.name} Reseller Frontier",
                    product_id=primary_product.id,
                    channel=PartnerChannel.RESELLER,
                    status=PartnershipStatus.STRAINED,
                    quality=60,
                    risk=44,
                    enablement_level=34,
                    sourced_revenue=Decimal("2100.00"),
                    sourced_users=30,
                    conflict_pressure=41,
                    started_turn=state.company.current_turn - 3,
                    last_review_turn=state.company.current_turn - 3,
                    summary="Reseller lane is useful but margin and conflict both need work.",
                ),
            ]
        )
    return "Campaign start applied: acquisition diligence sprint with live buyer pressure."


def _apply_independence_compounder(state: GameState) -> str:
    _shift_state_to_turn(state, 16)
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand + Decimal("6200.00"))
    state.company.reputation = clamp_int(state.company.reputation + 8)
    state.finance.debt_principal = quantize_money(state.finance.debt_principal * Decimal("0.45"))
    state.finance.board_confidence = max(state.finance.board_confidence, 70)
    state.finance.board_score = max(state.finance.board_score, 64)
    state.finance.investor_pressure = min(state.finance.investor_pressure, 8)
    state.finance.covenant_risk = min(state.finance.covenant_risk, 10)
    state.finance.board_pressure = max(state.finance.board_pressure, 11)
    _replace_capital_plan(
        state,
        mode=CapitalPlanMode.CONSERVE,
        source_preference=CapitalSourcePreference.BOOTSTRAP,
        reserve_target=Decimal("9000.00"),
        product_investment_share=34,
        go_to_market_share=24,
        reserve_share=42,
    )
    state.support_program.backlog_queue = max(state.support_program.backlog_queue, 6)
    state.support_program.escalation_queue = max(state.support_program.escalation_queue, 2)
    state.support_program.lane_focus = SupportLaneFocus.BALANCED

    primary_product = _get_primary_product(state)
    primary_product.user_count += 120
    primary_product.quality = clamp_int(primary_product.quality + 7)
    primary_product.market_fit = clamp_int(primary_product.market_fit + 8)
    primary_product.technical_debt = clamp_int(primary_product.technical_debt - 6)
    primary_product.package_catalog_depth += 1
    primary_product.add_on_catalog_depth += 1

    _ensure_customer_account(
        state,
        name="Compounder Core Account",
        product_id=primary_product.id,
        segment=MarketSegment.SMB,
        contract_value=Decimal("980.00"),
        subscription_package=SubscriptionPackage.GROWTH,
        support_tier=SupportTier.PRIORITY,
        billing_model=ContractBillingModel.FLAT,
        satisfaction=74,
        onboarding_health=72,
        support_load=24,
        open_tickets=5,
        sla_breach_risk=26,
        invoice_risk=6,
        failed_payment_risk=3,
        expansion_potential=70,
        renewal_health=68,
        renewal_turn=state.company.current_turn + 3,
        churn_risk=14,
    )
    return "Campaign start applied: independence compounder with reserve discipline live."


def _shift_state_to_turn(state: GameState, target_turn: int) -> None:
    state.company.current_turn = target_turn
    state.roadmap_set_turn = max(1, target_turn - 1)
    state.action_points_remaining = BALANCE.actions_per_turn
    state.quarter_plan = build_quarter_plan(state, budget_stance=state.quarter_plan.budget_stance)


def _replace_capital_plan(
    state: GameState,
    *,
    mode: CapitalPlanMode,
    source_preference: CapitalSourcePreference,
    reserve_target: Decimal,
    product_investment_share: int,
    go_to_market_share: int,
    reserve_share: int,
) -> None:
    state.capital_plan = CapitalPlan.model_validate(
        {
            **state.capital_plan.model_dump(mode="python"),
            "mode": mode,
            "source_preference": source_preference,
            "reserve_target": reserve_target,
            "product_investment_share": product_investment_share,
            "go_to_market_share": go_to_market_share,
            "reserve_share": reserve_share,
        }
    )


def _get_primary_product(state: GameState):
    active_products = [product for product in state.products if product.is_active]
    if not active_products:
        raise ValueError("Campaign starts require at least one active product.")
    return max(
        active_products,
        key=lambda product: (product.user_count, product.market_fit, product.quality),
    )


def _ensure_customer_account(
    state: GameState,
    *,
    name: str,
    product_id,
    segment: MarketSegment,
    contract_value: Decimal,
    subscription_package: SubscriptionPackage,
    support_tier: SupportTier,
    billing_model: ContractBillingModel,
    satisfaction: int,
    onboarding_health: int,
    support_load: int,
    open_tickets: int,
    sla_breach_risk: int,
    invoice_risk: int,
    failed_payment_risk: int,
    expansion_potential: int,
    renewal_health: int,
    renewal_turn: int,
    churn_risk: int,
    seat_count: int = 0,
    usage_units: int = 0,
    dunning_steps: int = 0,
    escalation_count: int = 0,
) -> None:
    if any(account.name == name for account in state.customer_accounts):
        return
    primary_product = _get_primary_product(state)
    state.customer_accounts.append(
        CustomerAccount(
            name=name,
            product_id=product_id,
            segment=segment,
            contract_value=contract_value,
            plan_tier=primary_product.pricing_tier,
            subscription_package=subscription_package,
            support_tier=support_tier,
            contract_cadence=ContractCadence.ANNUAL,
            billing_model=billing_model,
            seat_count=seat_count,
            usage_units=usage_units,
            satisfaction=satisfaction,
            onboarding_health=onboarding_health,
            support_load=support_load,
            open_tickets=open_tickets,
            sla_breach_risk=sla_breach_risk,
            invoice_risk=invoice_risk,
            failed_payment_risk=failed_payment_risk,
            dunning_steps=dunning_steps,
            escalation_count=escalation_count,
            expansion_potential=expansion_potential,
            renewal_health=renewal_health,
            renewal_turn=renewal_turn,
            churn_risk=churn_risk,
            status=CustomerAccountStatus.ACTIVE,
        )
    )
