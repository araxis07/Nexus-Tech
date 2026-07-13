"""Persistent decision points for the six featured campaign journeys."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import (
    EventCategory,
    EventOption,
    GameState,
    PendingEvent,
    Product,
)
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.campaign_journey import CampaignActId
from nexus_tech.simulation.product_progression import infer_lifecycle_stage
from nexus_tech.simulation.support import clamp_int, clamp_rate


@dataclass(frozen=True)
class CampaignChoiceEffect:
    """Declarative, save-compatible mutations applied by one campaign choice."""

    result_text: str
    cash_delta: Decimal = Decimal("0.00")
    reputation_delta: int = 0
    board_confidence_delta: int = 0
    board_pressure_delta: int = 0
    board_score_delta: int = 0
    investor_pressure_delta: int = 0
    governance_risk_delta: int = 0
    covenant_risk_delta: int = 0
    debt_delta: Decimal = Decimal("0.00")
    interest_rate_delta: Decimal = Decimal("0.0000")
    equity_dilution_delta: Decimal = Decimal("0.0000")
    support_backlog_delta: int = 0
    employee_morale_delta: int = 0
    employee_energy_delta: int = 0
    quality_delta: int = 0
    bug_delta: int = 0
    market_fit_delta: int = 0
    technical_debt_delta: int = 0
    users_delta: int = 0
    revenue_per_user_delta: Decimal = Decimal("0.00")
    maintenance_cost_delta: Decimal = Decimal("0.00")
    acquisition_rate_delta: Decimal = Decimal("0.0000")
    churn_rate_delta: Decimal = Decimal("0.0000")
    all_active_products: bool = False


@dataclass(frozen=True)
class CampaignDecisionOption:
    """One authored option and its persistent mechanical consequence."""

    option_id: str
    label: str
    description: str
    effect: CampaignChoiceEffect


@dataclass(frozen=True)
class CampaignDecisionDefinition:
    """A mandatory decision that opens the next act of one campaign."""

    scenario_id: str
    act_id: CampaignActId
    trigger_after_turn: int
    event_id: str
    category: EventCategory
    title: str
    description: str
    options: tuple[CampaignDecisionOption, CampaignDecisionOption]

    @property
    def chain_stage(self) -> int:
        return 1 if self.act_id is CampaignActId.COMMITMENT else 2


def _effect(result_text: str, **changes: object) -> CampaignChoiceEffect:
    return CampaignChoiceEffect(result_text=result_text, **changes)


def _option(
    option_id: str,
    label: str,
    description: str,
    effect: CampaignChoiceEffect,
) -> CampaignDecisionOption:
    return CampaignDecisionOption(option_id, label, description, effect)


_CAMPAIGN_DECISIONS = (
    CampaignDecisionDefinition(
        "founder_journey",
        CampaignActId.COMMITMENT,
        4,
        "campaign_founder_commitment",
        EventCategory.MARKET_OPPORTUNITY,
        "Founder Commitment: Pick the Pressure",
        "The foundation is stable enough to choose what the company will optimize for next.",
        (
            _option(
                "sharpen_focus",
                "Sharpen the Flagship",
                "Trade short-term speed for quality, fit, and lower technical debt.",
                _effect(
                    "The flagship became the operating center: quality +5, fit +3, debt -4.",
                    cash_delta=Decimal("-900.00"),
                    board_confidence_delta=2,
                    quality_delta=5,
                    market_fit_delta=3,
                    technical_debt_delta=-4,
                ),
            ),
            _option(
                "accelerate_demand",
                "Accelerate Demand",
                "Buy faster adoption while accepting more support and board pressure.",
                _effect(
                    "Demand accelerated: users +90 and acquisition improved, with more pressure.",
                    cash_delta=Decimal("-1200.00"),
                    board_pressure_delta=3,
                    support_backlog_delta=2,
                    users_delta=90,
                    acquisition_rate_delta=Decimal("0.0120"),
                ),
            ),
        ),
    ),
    CampaignDecisionDefinition(
        "founder_journey",
        CampaignActId.CONSEQUENCE,
        9,
        "campaign_founder_consequence",
        EventCategory.FUNDING_OPPORTUNITY,
        "Founder Consequence: Define Control",
        "The company can defend independence or exchange control for a larger capital cushion.",
        (
            _option(
                "defend_control",
                "Defend Control",
                "Spend reserves on credibility and keep investor pressure low.",
                _effect(
                    "Control stayed with the company: reputation +4 and board confidence +4.",
                    cash_delta=Decimal("-1600.00"),
                    reputation_delta=4,
                    board_confidence_delta=4,
                    investor_pressure_delta=-5,
                ),
            ),
            _option(
                "accept_growth_capital",
                "Accept Growth Capital",
                "Add runway and demand, but accept dilution and investor pressure.",
                _effect(
                    "Growth capital landed: cash +12000, dilution +3%, investor pressure +8.",
                    cash_delta=Decimal("12000.00"),
                    investor_pressure_delta=8,
                    equity_dilution_delta=Decimal("0.0300"),
                    acquisition_rate_delta=Decimal("0.0100"),
                ),
            ),
        ),
    ),
    CampaignDecisionDefinition(
        "bootstrap_studio",
        CampaignActId.COMMITMENT,
        4,
        "campaign_bootstrap_commitment",
        EventCategory.MARKET_OPPORTUNITY,
        "Bootstrap Commitment: Margin or Volume",
        "The studio must choose whether repeatability comes from pricing discipline or reach.",
        (
            _option(
                "protect_margin",
                "Protect Margin",
                "Improve monetization and retention without adding delivery load.",
                _effect(
                    "Margin discipline held: revenue per user +0.30 and churn improved.",
                    board_confidence_delta=2,
                    revenue_per_user_delta=Decimal("0.30"),
                    churn_rate_delta=Decimal("-0.0060"),
                ),
            ),
            _option(
                "buy_volume",
                "Buy Volume",
                "Fund acquisition now and carry a larger support queue.",
                _effect(
                    "Volume expanded: users +75 and acquisition improved, backlog +2.",
                    cash_delta=Decimal("-1000.00"),
                    support_backlog_delta=2,
                    users_delta=75,
                    acquisition_rate_delta=Decimal("0.0110"),
                ),
            ),
        ),
    ),
    CampaignDecisionDefinition(
        "bootstrap_studio",
        CampaignActId.CONSEQUENCE,
        9,
        "campaign_bootstrap_consequence",
        EventCategory.FUNDING_OPPORTUNITY,
        "Bootstrap Consequence: Use the Surplus",
        "The late-game surplus can become a reserve moat or a final product-quality push.",
        (
            _option(
                "build_reserve_moat",
                "Build a Reserve Moat",
                "Cut recurring maintenance and bank a stronger liquidity buffer.",
                _effect(
                    "The reserve moat strengthened: cash +2500 and maintenance cost fell.",
                    cash_delta=Decimal("2500.00"),
                    board_confidence_delta=4,
                    maintenance_cost_delta=Decimal("-180.00"),
                ),
            ),
            _option(
                "compound_product",
                "Compound the Product",
                "Reinvest in quality, fit, and pricing power before the final gates.",
                _effect(
                    "The product compounded: quality +4, fit +3, revenue per user +0.20.",
                    cash_delta=Decimal("-1800.00"),
                    quality_delta=4,
                    market_fit_delta=3,
                    revenue_per_user_delta=Decimal("0.20"),
                ),
            ),
        ),
    ),
    CampaignDecisionDefinition(
        "technical_rebuild",
        CampaignActId.COMMITMENT,
        4,
        "campaign_rebuild_commitment",
        EventCategory.PRODUCT_INCIDENT,
        "Rebuild Commitment: Set the Repair Cadence",
        "Recovery needs a deliberate trade-off between a hard freeze and staged delivery.",
        (
            _option(
                "freeze_for_rebuild",
                "Freeze for Rebuild",
                "Take the larger commercial pause to remove incidents and debt quickly.",
                _effect(
                    "The hard freeze worked: bugs -10, debt -10, and team energy -4.",
                    cash_delta=Decimal("-1500.00"),
                    board_confidence_delta=3,
                    employee_morale_delta=-3,
                    employee_energy_delta=-4,
                    bug_delta=-10,
                    technical_debt_delta=-10,
                    acquisition_rate_delta=Decimal("-0.0040"),
                ),
            ),
            _option(
                "phase_the_rebuild",
                "Phase the Rebuild",
                "Keep shipping while reducing debt more gradually.",
                _effect(
                    (
                        "The phased rebuild balanced repair and delivery: "
                        "quality +3, bugs -5, debt -6, and morale +2."
                    ),
                    cash_delta=Decimal("-800.00"),
                    employee_morale_delta=2,
                    employee_energy_delta=-2,
                    quality_delta=3,
                    bug_delta=-5,
                    technical_debt_delta=-6,
                    support_backlog_delta=-1,
                ),
            ),
        ),
    ),
    CampaignDecisionDefinition(
        "technical_rebuild",
        CampaignActId.CONSEQUENCE,
        9,
        "campaign_rebuild_consequence",
        EventCategory.REPUTATION_INCIDENT,
        "Rebuild Consequence: Prove the Recovery",
        "The platform is healthier; customers now need evidence or a visible velocity promise.",
        (
            _option(
                "publish_reliability_proof",
                "Publish Reliability Proof",
                "Convert technical health into trust and lower churn.",
                _effect(
                    "Reliability proof rebuilt trust: reputation +6 and churn improved.",
                    cash_delta=Decimal("-900.00"),
                    reputation_delta=6,
                    quality_delta=2,
                    churn_rate_delta=Decimal("-0.0080"),
                ),
            ),
            _option(
                "promise_velocity",
                "Promise New Velocity",
                "Push adoption immediately while accepting fresh bug and board pressure.",
                _effect(
                    "The velocity promise grew demand: users +100, with bugs +4 and pressure +3.",
                    users_delta=100,
                    acquisition_rate_delta=Decimal("0.0140"),
                    bug_delta=4,
                    board_pressure_delta=3,
                ),
            ),
        ),
    ),
    CampaignDecisionDefinition(
        "portfolio_machine",
        CampaignActId.COMMITMENT,
        4,
        "campaign_portfolio_commitment",
        EventCategory.PRODUCT_INCIDENT,
        "Portfolio Commitment: Choose the Operating Model",
        "The second engine needs either a shared platform or deliberate product autonomy.",
        (
            _option(
                "share_the_platform",
                "Share the Platform",
                "Reduce debt and maintenance across every active product.",
                _effect(
                    "Shared systems lowered portfolio drag: quality +2, debt -4, maintenance down.",
                    cash_delta=Decimal("-1700.00"),
                    quality_delta=2,
                    technical_debt_delta=-4,
                    maintenance_cost_delta=Decimal("-120.00"),
                    all_active_products=True,
                ),
            ),
            _option(
                "preserve_autonomy",
                "Preserve Product Autonomy",
                "Improve fit and acquisition while carrying duplicate operating cost.",
                _effect(
                    "Autonomous products found sharper markets: fit +3 and acquisition improved.",
                    market_fit_delta=3,
                    acquisition_rate_delta=Decimal("0.0050"),
                    maintenance_cost_delta=Decimal("90.00"),
                    all_active_products=True,
                ),
            ),
        ),
    ),
    CampaignDecisionDefinition(
        "portfolio_machine",
        CampaignActId.CONSEQUENCE,
        9,
        "campaign_portfolio_consequence",
        EventCategory.MARKET_OPPORTUNITY,
        "Portfolio Consequence: Control the Sprawl",
        "Capital can be consolidated around coherence or left distributed for broader growth.",
        (
            _option(
                "consolidate_capital",
                "Consolidate Capital",
                "Tighten every product and reduce the board's concern about sprawl.",
                _effect(
                    "Capital was consolidated: cash +2200, quality +2, board confidence +4.",
                    cash_delta=Decimal("2200.00"),
                    board_confidence_delta=4,
                    board_pressure_delta=-3,
                    quality_delta=2,
                    all_active_products=True,
                ),
            ),
            _option(
                "fund_the_portfolio",
                "Fund the Full Portfolio",
                "Keep every growth loop active while accepting coordination pressure.",
                _effect(
                    (
                        "The full portfolio kept growing: fit +2 and acquisition improved, "
                        "pressure +4."
                    ),
                    cash_delta=Decimal("-1600.00"),
                    board_pressure_delta=4,
                    support_backlog_delta=2,
                    market_fit_delta=2,
                    acquisition_rate_delta=Decimal("0.0040"),
                    all_active_products=True,
                ),
            ),
        ),
    ),
    CampaignDecisionDefinition(
        "debt_crunch",
        CampaignActId.COMMITMENT,
        4,
        "campaign_debt_commitment",
        EventCategory.FUNDING_OPPORTUNITY,
        "Debt Commitment: Repair or Outgrow",
        "The capital stack demands either an operating restructure or a riskier growth escape.",
        (
            _option(
                "restructure_operations",
                "Restructure Operations",
                "Reduce principal and covenant risk before chasing more demand.",
                _effect(
                    "Operations were restructured: debt -2500, covenant risk -8, morale -5.",
                    cash_delta=Decimal("-800.00"),
                    debt_delta=Decimal("-2500.00"),
                    covenant_risk_delta=-8,
                    board_confidence_delta=4,
                    employee_morale_delta=-5,
                    employee_energy_delta=-2,
                    acquisition_rate_delta=Decimal("-0.0030"),
                ),
            ),
            _option(
                "outgrow_the_debt",
                "Outgrow the Debt",
                "Buy demand now and carry tighter covenants into the next act.",
                _effect(
                    "The company chased growth: users +120, risk +5, and team energy -4.",
                    cash_delta=Decimal("-1200.00"),
                    users_delta=120,
                    acquisition_rate_delta=Decimal("0.0150"),
                    covenant_risk_delta=5,
                    employee_morale_delta=2,
                    employee_energy_delta=-4,
                ),
            ),
        ),
    ),
    CampaignDecisionDefinition(
        "debt_crunch",
        CampaignActId.CONSEQUENCE,
        9,
        "campaign_debt_consequence",
        EventCategory.FUNDING_OPPORTUNITY,
        "Debt Consequence: Lock the Capital Path",
        "The final solvency path is a direct paydown or a refinance that preserves liquidity.",
        (
            _option(
                "pay_down_principal",
                "Pay Down Principal",
                "Spend cash to cut debt, covenant risk, and board pressure now.",
                _effect(
                    "Principal was paid down: cash -3000, debt -3000, covenant risk -12.",
                    cash_delta=Decimal("-3000.00"),
                    debt_delta=Decimal("-3000.00"),
                    covenant_risk_delta=-12,
                    board_pressure_delta=-5,
                ),
            ),
            _option(
                "refinance_for_time",
                "Refinance for Time",
                "Add liquidity and lower near-term risk, but accept more debt and interest.",
                _effect(
                    "The refinance bought time: cash +3500, debt +1500, investor pressure +4.",
                    cash_delta=Decimal("3500.00"),
                    debt_delta=Decimal("1500.00"),
                    interest_rate_delta=Decimal("0.0050"),
                    covenant_risk_delta=-5,
                    investor_pressure_delta=4,
                ),
            ),
        ),
    ),
    CampaignDecisionDefinition(
        "public_market_countdown",
        CampaignActId.COMMITMENT,
        4,
        "campaign_public_market_commitment",
        EventCategory.REPUTATION_INCIDENT,
        "Market Commitment: Choose the Listing Story",
        "Public-market credibility can lead with clean controls or visible growth momentum.",
        (
            _option(
                "lead_with_controls",
                "Lead with Controls",
                "Fund governance readiness and reduce the risks diligence will expose.",
                _effect(
                    "Controls led the story: governance risk -10, board confidence +6, energy -3.",
                    cash_delta=Decimal("-1800.00"),
                    reputation_delta=2,
                    board_confidence_delta=6,
                    board_score_delta=4,
                    governance_risk_delta=-10,
                    employee_energy_delta=-3,
                ),
            ),
            _option(
                "lead_with_growth",
                "Lead with Growth",
                "Create visible momentum while accepting board and support pressure.",
                _effect(
                    "Growth led the story: users +150 and reputation +4, pressure +6.",
                    users_delta=150,
                    reputation_delta=4,
                    acquisition_rate_delta=Decimal("0.0120"),
                    board_pressure_delta=6,
                    support_backlog_delta=2,
                ),
            ),
        ),
    ),
    CampaignDecisionDefinition(
        "public_market_countdown",
        CampaignActId.CONSEQUENCE,
        9,
        "campaign_public_market_consequence",
        EventCategory.REPUTATION_INCIDENT,
        "Market Consequence: Defend the Outcome",
        "The final act needs either a listing defense or explicit strategic optionality.",
        (
            _option(
                "defend_the_listing",
                "Defend the Listing",
                "Spend for final controls, trust, and board readiness.",
                _effect(
                    "The listing was defended: governance risk -8, board score +6, reputation +4.",
                    cash_delta=Decimal("-2400.00"),
                    reputation_delta=4,
                    board_confidence_delta=5,
                    board_score_delta=6,
                    governance_risk_delta=-8,
                ),
            ),
            _option(
                "preserve_optionality",
                "Preserve Optionality",
                "Lower external pressure and improve the product instead of forcing the window.",
                _effect(
                    "Optionality stayed open: pressure eased, morale +3, and quality +3.",
                    investor_pressure_delta=-6,
                    board_pressure_delta=-4,
                    employee_morale_delta=3,
                    quality_delta=3,
                    technical_debt_delta=-3,
                ),
            ),
        ),
    ),
)

_DECISIONS_BY_EVENT_ID = {definition.event_id: definition for definition in _CAMPAIGN_DECISIONS}


def list_campaign_decisions() -> tuple[CampaignDecisionDefinition, ...]:
    """Return every authored campaign decision in deterministic order."""

    return _CAMPAIGN_DECISIONS


def is_campaign_decision_event(event_id: str) -> bool:
    """Return whether an event belongs to the featured campaign decision system."""

    return event_id in _DECISIONS_BY_EVENT_ID


def build_due_campaign_decision_event(state: GameState) -> PendingEvent | None:
    """Build the earliest unresolved campaign decision due for this state."""

    if state.pending_event is not None or state.company.game_over or state.victory_achieved:
        return None
    resolved_event_ids = {entry.event_id for entry in state.event_history}
    for definition in _CAMPAIGN_DECISIONS:
        if definition.scenario_id != state.scenario_id:
            continue
        if state.company.current_turn < definition.trigger_after_turn:
            continue
        if definition.event_id in resolved_event_ids:
            continue
        return PendingEvent(
            event_id=definition.event_id,
            category=definition.category,
            title=definition.title,
            description=definition.description,
            triggered_turn=state.company.current_turn,
            cooldown_turns=999,
            chain_id=f"campaign:{state.scenario_id}",
            chain_stage=definition.chain_stage,
            options=[
                EventOption(
                    id=option.option_id,
                    label=option.label,
                    description=option.description,
                )
                for option in definition.options
            ],
        )
    return None


def apply_campaign_decision_choice(
    state: GameState,
    event: PendingEvent,
    option_id: str,
) -> str:
    """Apply an authored campaign option to existing persistent state fields."""

    definition = _DECISIONS_BY_EVENT_ID.get(event.event_id)
    if definition is None or definition.scenario_id != state.scenario_id:
        raise ValueError(f"Unsupported campaign event {event.event_id}.")
    selected = next(
        (option for option in definition.options if option.option_id == option_id),
        None,
    )
    if selected is None:
        raise ValueError(f"Unsupported option {option_id} for {event.event_id}.")

    effect = selected.effect
    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand + effect.cash_delta)
    state.company.reputation = clamp_int(state.company.reputation + effect.reputation_delta)
    state.finance.board_confidence = clamp_int(
        state.finance.board_confidence + effect.board_confidence_delta
    )
    state.finance.board_pressure = clamp_int(
        state.finance.board_pressure + effect.board_pressure_delta
    )
    state.finance.board_score = clamp_int(state.finance.board_score + effect.board_score_delta)
    state.finance.investor_pressure = clamp_int(
        state.finance.investor_pressure + effect.investor_pressure_delta
    )
    state.finance.governance_risk = clamp_int(
        state.finance.governance_risk + effect.governance_risk_delta
    )
    state.finance.covenant_risk = clamp_int(
        state.finance.covenant_risk + effect.covenant_risk_delta
    )
    state.finance.debt_principal = quantize_money(
        max(Decimal("0.00"), state.finance.debt_principal + effect.debt_delta)
    )
    state.finance.loan_interest_rate = clamp_rate(
        state.finance.loan_interest_rate + effect.interest_rate_delta
    )
    state.finance.equity_dilution = clamp_rate(
        state.finance.equity_dilution + effect.equity_dilution_delta
    )
    state.support_program.backlog_queue = max(
        0,
        state.support_program.backlog_queue + effect.support_backlog_delta,
    )
    for employee in state.employees:
        employee.morale = clamp_int(employee.morale + effect.employee_morale_delta)
        employee.energy = clamp_int(employee.energy + effect.employee_energy_delta)
    for product in _effect_products(state, effect):
        _apply_product_effect(product, effect)
    return effect.result_text


def get_campaign_choice_label(state: GameState, act_id: CampaignActId) -> str | None:
    """Return the recorded player-facing label for one campaign act decision."""

    definition = next(
        (
            item
            for item in _CAMPAIGN_DECISIONS
            if item.scenario_id == state.scenario_id and item.act_id is act_id
        ),
        None,
    )
    if definition is None:
        return None
    for entry in reversed(state.event_history):
        if entry.event_id == definition.event_id:
            return entry.selected_option_label
    return None


def get_campaign_path_labels(state: GameState) -> tuple[str, ...]:
    """Return compact recorded labels for the campaign path taken so far."""

    labels: list[str] = []
    for act_id, prefix in (
        (CampaignActId.COMMITMENT, "Act 2"),
        (CampaignActId.CONSEQUENCE, "Act 3"),
    ):
        label = get_campaign_choice_label(state, act_id)
        if label is not None:
            labels.append(f"{prefix}: {label}")
    return tuple(labels)


def _effect_products(state: GameState, effect: CampaignChoiceEffect) -> list[Product]:
    active_products = [product for product in state.products if product.is_active]
    if not active_products:
        return []
    if effect.all_active_products:
        return active_products
    return [
        max(
            active_products,
            key=lambda product: (
                product.user_count + product.market_fit + product.quality,
                -product.bug_level,
            ),
        )
    ]


def _apply_product_effect(product: Product, effect: CampaignChoiceEffect) -> None:
    product.quality = clamp_int(product.quality + effect.quality_delta)
    product.bug_level = clamp_int(product.bug_level + effect.bug_delta)
    product.market_fit = clamp_int(product.market_fit + effect.market_fit_delta)
    product.technical_debt = clamp_int(product.technical_debt + effect.technical_debt_delta)
    product.user_count = max(0, product.user_count + effect.users_delta)
    product.revenue_per_user = quantize_money(
        max(Decimal("0.00"), product.revenue_per_user + effect.revenue_per_user_delta)
    )
    product.maintenance_cost = quantize_money(
        max(Decimal("0.00"), product.maintenance_cost + effect.maintenance_cost_delta)
    )
    product.acquisition_rate = clamp_rate(product.acquisition_rate + effect.acquisition_rate_delta)
    product.churn_rate = clamp_rate(product.churn_rate + effect.churn_rate_delta)
    product.lifecycle_stage = infer_lifecycle_stage(product)
