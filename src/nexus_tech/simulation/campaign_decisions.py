"""Persistent decision points for the six featured campaign journeys."""

from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal

from nexus_tech.domain.models import (
    EventCategory,
    EventOption,
    GameState,
    PendingEvent,
    Product,
)
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.campaign_journey import CampaignActId, get_campaign_journey
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

    @property
    def mechanical_dimensions(self) -> tuple[str, ...]:
        """Return the state dimensions changed by this authored choice."""

        return tuple(
            field.name
            for field in fields(self)
            if field.name != "result_text" and bool(getattr(self, field.name))
        )


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


@dataclass(frozen=True)
class CampaignEventBias:
    """Long-run event pressure created by a recorded campaign choice."""

    option_id: str
    summary: str
    adjustments: tuple[tuple[EventCategory, int], ...]

    def adjustment_for(self, category: EventCategory) -> int:
        """Return the percentage-point event-weight adjustment for one category."""

        return sum(amount for target, amount in self.adjustments if target is category)


@dataclass(frozen=True)
class CampaignPathLegacy:
    """Player-facing synthesis of both campaign decisions and their lasting pressure."""

    route_label: str
    summary: str
    pressure_line: str
    mandate: str
    option_ids: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return len(self.option_ids) == 2


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
                    "The flagship became the operating center: quality +6, fit +4, debt -6.",
                    cash_delta=Decimal("-700.00"),
                    reputation_delta=3,
                    board_confidence_delta=3,
                    quality_delta=6,
                    market_fit_delta=4,
                    technical_debt_delta=-6,
                    revenue_per_user_delta=Decimal("0.15"),
                    churn_rate_delta=Decimal("-0.0040"),
                ),
            ),
            _option(
                "accelerate_demand",
                "Accelerate Demand",
                "Buy faster adoption while accepting more support and board pressure.",
                _effect(
                    "Demand accelerated: users +60 and acquisition improved, with more pressure.",
                    cash_delta=Decimal("-1400.00"),
                    board_pressure_delta=4,
                    support_backlog_delta=3,
                    users_delta=60,
                    acquisition_rate_delta=Decimal("0.0080"),
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
                    "Control stayed with the company: reputation +5 and board confidence +6.",
                    cash_delta=Decimal("-800.00"),
                    reputation_delta=5,
                    board_confidence_delta=6,
                    investor_pressure_delta=-7,
                    governance_risk_delta=-3,
                ),
            ),
            _option(
                "accept_growth_capital",
                "Accept Growth Capital",
                "Add runway and demand, but accept dilution and investor pressure.",
                _effect(
                    "Growth capital landed: cash +7000, dilution +4.5%, investor pressure +12.",
                    cash_delta=Decimal("7000.00"),
                    board_pressure_delta=4,
                    investor_pressure_delta=12,
                    equity_dilution_delta=Decimal("0.0450"),
                    acquisition_rate_delta=Decimal("0.0050"),
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
                    "Margin discipline held: cash +300, revenue per user +0.40, churn improved.",
                    cash_delta=Decimal("300.00"),
                    board_confidence_delta=4,
                    revenue_per_user_delta=Decimal("0.40"),
                    churn_rate_delta=Decimal("-0.0080"),
                ),
            ),
            _option(
                "buy_volume",
                "Buy Volume",
                "Fund acquisition now and carry a larger support queue.",
                _effect(
                    "Volume expanded: users +60 and acquisition improved, backlog +2.",
                    cash_delta=Decimal("-800.00"),
                    support_backlog_delta=2,
                    users_delta=60,
                    acquisition_rate_delta=Decimal("0.0100"),
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
                    "The reserve moat strengthened: cash +3500 and maintenance cost fell.",
                    cash_delta=Decimal("3500.00"),
                    board_confidence_delta=3,
                    maintenance_cost_delta=Decimal("-180.00"),
                ),
            ),
            _option(
                "compound_product",
                "Compound the Product",
                "Reinvest in quality, fit, and pricing power before the final gates.",
                _effect(
                    (
                        "The product compounded: advocates +42, reputation +12, "
                        "quality +9, and fit +8."
                    ),
                    cash_delta=Decimal("-2200.00"),
                    reputation_delta=12,
                    board_confidence_delta=5,
                    users_delta=42,
                    quality_delta=9,
                    market_fit_delta=8,
                    revenue_per_user_delta=Decimal("0.80"),
                    acquisition_rate_delta=Decimal("0.0060"),
                    churn_rate_delta=Decimal("-0.0080"),
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
                    "Reliability proof rebuilt trust: users +50, reputation +8, quality +4.",
                    cash_delta=Decimal("-500.00"),
                    reputation_delta=8,
                    board_confidence_delta=4,
                    users_delta=50,
                    quality_delta=4,
                    acquisition_rate_delta=Decimal("0.0060"),
                    churn_rate_delta=Decimal("-0.0100"),
                ),
            ),
            _option(
                "promise_velocity",
                "Promise New Velocity",
                "Push adoption immediately while accepting fresh bug and board pressure.",
                _effect(
                    "The velocity promise grew demand: users +65, with measured repair pressure.",
                    cash_delta=Decimal("-200.00"),
                    reputation_delta=2,
                    users_delta=65,
                    acquisition_rate_delta=Decimal("0.0090"),
                    bug_delta=3,
                    technical_debt_delta=3,
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
                    maintenance_cost_delta=Decimal("-160.00"),
                    all_active_products=True,
                ),
            ),
            _option(
                "preserve_autonomy",
                "Preserve Product Autonomy",
                "Improve fit and acquisition while carrying duplicate operating cost.",
                _effect(
                    "Autonomous products found sharper markets: fit +4 and acquisition improved.",
                    market_fit_delta=4,
                    acquisition_rate_delta=Decimal("0.0060"),
                    maintenance_cost_delta=Decimal("60.00"),
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
                "Tighten every product, prune low-fit demand, and reduce board concern.",
                _effect(
                    (
                        "Capital was consolidated: cash +2200, quality +2, board confidence +4, "
                        "and low-fit users -10 each."
                    ),
                    cash_delta=Decimal("2200.00"),
                    board_confidence_delta=4,
                    board_pressure_delta=-3,
                    quality_delta=2,
                    users_delta=-10,
                    acquisition_rate_delta=Decimal("-0.0030"),
                    all_active_products=True,
                ),
            ),
            _option(
                "fund_the_portfolio",
                "Fund the Full Portfolio",
                "Keep every growth loop active while accepting coordination pressure.",
                _effect(
                    (
                        "The full portfolio kept growing: users +36 each, fit +4, "
                        "and acquisition improved, with pressure +4."
                    ),
                    cash_delta=Decimal("-2200.00"),
                    board_pressure_delta=4,
                    support_backlog_delta=2,
                    users_delta=36,
                    market_fit_delta=4,
                    acquisition_rate_delta=Decimal("0.0100"),
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
                    "Operations were restructured: debt -3000, recurring cost fell, morale -3.",
                    debt_delta=Decimal("-3000.00"),
                    covenant_risk_delta=-10,
                    board_confidence_delta=6,
                    employee_morale_delta=-3,
                    employee_energy_delta=-2,
                    maintenance_cost_delta=Decimal("-120.00"),
                    acquisition_rate_delta=Decimal("-0.0010"),
                ),
            ),
            _option(
                "outgrow_the_debt",
                "Outgrow the Debt",
                "Buy demand now and carry tighter covenants into the next act.",
                _effect(
                    "The company chased growth: users +70, risk +7, and team energy -5.",
                    cash_delta=Decimal("-1600.00"),
                    users_delta=70,
                    acquisition_rate_delta=Decimal("0.0090"),
                    covenant_risk_delta=7,
                    employee_energy_delta=-5,
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
                    "Principal was paid down: cash -2200, debt -3000, covenant risk -12.",
                    cash_delta=Decimal("-2200.00"),
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
                    "Controls led the story: governance risk -10, reputation +6, board score +10.",
                    cash_delta=Decimal("-1200.00"),
                    reputation_delta=6,
                    board_confidence_delta=8,
                    board_score_delta=10,
                    governance_risk_delta=-10,
                    employee_energy_delta=-3,
                ),
            ),
            _option(
                "lead_with_growth",
                "Lead with Growth",
                "Create visible momentum while accepting board and support pressure.",
                _effect(
                    "Growth led the story: users +60 and reputation +2, pressure +8.",
                    users_delta=60,
                    reputation_delta=2,
                    acquisition_rate_delta=Decimal("0.0060"),
                    board_pressure_delta=8,
                    governance_risk_delta=5,
                    support_backlog_delta=3,
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

_CAMPAIGN_EVENT_BIASES = {
    bias.option_id: bias
    for bias in (
        CampaignEventBias(
            "sharpen_focus",
            "Fewer product incidents; slightly more market openings.",
            ((EventCategory.PRODUCT_INCIDENT, -25), (EventCategory.MARKET_OPPORTUNITY, 10)),
        ),
        CampaignEventBias(
            "accelerate_demand",
            "More market openings, but support-driven product incidents rise.",
            ((EventCategory.MARKET_OPPORTUNITY, 20), (EventCategory.PRODUCT_INCIDENT, 25)),
        ),
        CampaignEventBias(
            "defend_control",
            "Funding pressure recedes and reputation shocks become less likely.",
            ((EventCategory.FUNDING_OPPORTUNITY, -20), (EventCategory.REPUTATION_INCIDENT, -10)),
        ),
        CampaignEventBias(
            "accept_growth_capital",
            "Funding and market events become more frequent under investor attention.",
            ((EventCategory.FUNDING_OPPORTUNITY, 30), (EventCategory.MARKET_OPPORTUNITY, 10)),
        ),
        CampaignEventBias(
            "protect_margin",
            "Product incidents ease while disciplined market openings improve.",
            ((EventCategory.PRODUCT_INCIDENT, -15), (EventCategory.MARKET_OPPORTUNITY, 10)),
        ),
        CampaignEventBias(
            "buy_volume",
            "Market openings and product-support incidents both become more common.",
            ((EventCategory.MARKET_OPPORTUNITY, 20), (EventCategory.PRODUCT_INCIDENT, 20)),
        ),
        CampaignEventBias(
            "build_reserve_moat",
            "Funding and reputation events cool as the reserve absorbs shocks.",
            ((EventCategory.FUNDING_OPPORTUNITY, -20), (EventCategory.REPUTATION_INCIDENT, -10)),
        ),
        CampaignEventBias(
            "compound_product",
            "Product incidents ease and stronger market openings become more likely.",
            ((EventCategory.PRODUCT_INCIDENT, -20), (EventCategory.MARKET_OPPORTUNITY, 10)),
        ),
        CampaignEventBias(
            "freeze_for_rebuild",
            "Product incidents fall sharply, but employee pressure events rise.",
            ((EventCategory.PRODUCT_INCIDENT, -35), (EventCategory.EMPLOYEE_ISSUE, 15)),
        ),
        CampaignEventBias(
            "phase_the_rebuild",
            "Product incidents ease while measured market openings return.",
            ((EventCategory.PRODUCT_INCIDENT, -20), (EventCategory.MARKET_OPPORTUNITY, 10)),
        ),
        CampaignEventBias(
            "publish_reliability_proof",
            "Reputation shocks fall and trust-led market openings increase.",
            ((EventCategory.REPUTATION_INCIDENT, -25), (EventCategory.MARKET_OPPORTUNITY, 15)),
        ),
        CampaignEventBias(
            "promise_velocity",
            "Market openings rise, alongside a sharp increase in product incidents.",
            ((EventCategory.MARKET_OPPORTUNITY, 20), (EventCategory.PRODUCT_INCIDENT, 30)),
        ),
        CampaignEventBias(
            "share_the_platform",
            "Shared systems reduce product incidents but add team coordination pressure.",
            ((EventCategory.PRODUCT_INCIDENT, -25), (EventCategory.EMPLOYEE_ISSUE, 10)),
        ),
        CampaignEventBias(
            "preserve_autonomy",
            "Market openings increase while independent products create more incidents.",
            ((EventCategory.MARKET_OPPORTUNITY, 20), (EventCategory.PRODUCT_INCIDENT, 15)),
        ),
        CampaignEventBias(
            "consolidate_capital",
            "Funding scrutiny and product incidents both ease.",
            ((EventCategory.FUNDING_OPPORTUNITY, -10), (EventCategory.PRODUCT_INCIDENT, -10)),
        ),
        CampaignEventBias(
            "fund_the_portfolio",
            "Market openings rise with product and employee coordination incidents.",
            (
                (EventCategory.MARKET_OPPORTUNITY, 15),
                (EventCategory.PRODUCT_INCIDENT, 20),
                (EventCategory.EMPLOYEE_ISSUE, 20),
            ),
        ),
        CampaignEventBias(
            "restructure_operations",
            "Funding options improve slightly while operating strain reduces employee issues.",
            ((EventCategory.FUNDING_OPPORTUNITY, 5), (EventCategory.EMPLOYEE_ISSUE, -5)),
        ),
        CampaignEventBias(
            "outgrow_the_debt",
            "Funding and market events accelerate around the growth gamble.",
            ((EventCategory.FUNDING_OPPORTUNITY, 25), (EventCategory.MARKET_OPPORTUNITY, 20)),
        ),
        CampaignEventBias(
            "pay_down_principal",
            "Funding confidence improves slightly while fewer market gambles surface.",
            ((EventCategory.FUNDING_OPPORTUNITY, 5), (EventCategory.MARKET_OPPORTUNITY, -5)),
        ),
        CampaignEventBias(
            "refinance_for_time",
            "Funding events rise sharply while the new capital structure is tested.",
            ((EventCategory.FUNDING_OPPORTUNITY, 35), (EventCategory.MARKET_OPPORTUNITY, 5)),
        ),
        CampaignEventBias(
            "lead_with_controls",
            "Reputation and funding scrutiny events become less frequent.",
            ((EventCategory.REPUTATION_INCIDENT, -25), (EventCategory.FUNDING_OPPORTUNITY, -15)),
        ),
        CampaignEventBias(
            "lead_with_growth",
            "Market momentum rises together with reputation scrutiny.",
            ((EventCategory.MARKET_OPPORTUNITY, 25), (EventCategory.REPUTATION_INCIDENT, 20)),
        ),
        CampaignEventBias(
            "defend_the_listing",
            "Funding and reputation scrutiny both cool after readiness work.",
            ((EventCategory.FUNDING_OPPORTUNITY, -20), (EventCategory.REPUTATION_INCIDENT, -20)),
        ),
        CampaignEventBias(
            "preserve_optionality",
            "Funding pressure falls while selective market openings remain available.",
            ((EventCategory.FUNDING_OPPORTUNITY, -30), (EventCategory.MARKET_OPPORTUNITY, 10)),
        ),
    )
}


def list_campaign_decisions() -> tuple[CampaignDecisionDefinition, ...]:
    """Return every authored campaign decision in deterministic order."""

    return _CAMPAIGN_DECISIONS


def list_campaign_event_biases() -> tuple[CampaignEventBias, ...]:
    """Return every long-run campaign path modifier in deterministic choice order."""

    return tuple(
        _CAMPAIGN_EVENT_BIASES[option.option_id]
        for definition in _CAMPAIGN_DECISIONS
        for option in definition.options
    )


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
                    description=(
                        f"{option.description} Long-run: "
                        f"{_CAMPAIGN_EVENT_BIASES[option.option_id].summary}"
                    ),
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


def build_campaign_path_legacy(state: GameState) -> CampaignPathLegacy | None:
    """Synthesize the route, pressure, and late-game mandate from recorded choices."""

    selected_choices: list[tuple[str, str, CampaignEventBias | None]] = []
    for definition in _scenario_decisions(state.scenario_id):
        entry = next(
            (
                item
                for item in reversed(state.event_history)
                if item.event_id == definition.event_id
            ),
            None,
        )
        if entry is None:
            continue
        selected_choices.append(
            (
                entry.selected_option_id,
                entry.selected_option_label,
                _CAMPAIGN_EVENT_BIASES.get(entry.selected_option_id),
            )
        )
    return _build_campaign_path_legacy(state.scenario_id, tuple(selected_choices))


def build_campaign_path_legacy_from_labels(
    scenario_id: str,
    labels: tuple[str, ...],
) -> CampaignPathLegacy | None:
    """Rebuild a legacy summary from the labels persisted in an archive row."""

    selected_choices: list[tuple[str, str, CampaignEventBias | None]] = []
    for definition, stored_label in zip(_scenario_decisions(scenario_id), labels, strict=False):
        label = _clean_campaign_choice_label(stored_label)
        option = next((item for item in definition.options if item.label == label), None)
        if option is None:
            continue
        selected_choices.append(
            (
                option.option_id,
                option.label,
                _CAMPAIGN_EVENT_BIASES.get(option.option_id),
            )
        )
    return _build_campaign_path_legacy(scenario_id, tuple(selected_choices))


def get_campaign_path_outlook(state: GameState) -> str | None:
    """Return the latest player-facing long-run event outlook for this path."""

    legacy = build_campaign_path_legacy(state)
    if legacy is None:
        return None
    return legacy.pressure_line if legacy.complete else legacy.summary


def campaign_adjusted_event_weight(
    state: GameState,
    category: EventCategory,
    base_weight: int,
) -> int:
    """Apply recorded path pressure to one future systemic-event weight."""

    adjustment = 0
    for entry in state.event_history:
        if not is_campaign_decision_event(entry.event_id):
            continue
        bias = _CAMPAIGN_EVENT_BIASES.get(entry.selected_option_id)
        if bias is not None:
            adjustment += bias.adjustment_for(category)
    bounded_percent = max(40, min(180, 100 + adjustment))
    return max(1, round(base_weight * bounded_percent / 100))


def _scenario_decisions(scenario_id: str) -> tuple[CampaignDecisionDefinition, ...]:
    return tuple(
        sorted(
            (item for item in _CAMPAIGN_DECISIONS if item.scenario_id == scenario_id),
            key=lambda item: item.trigger_after_turn,
        )
    )


def _build_campaign_path_legacy(
    scenario_id: str,
    selected_choices: tuple[tuple[str, str, CampaignEventBias | None], ...],
) -> CampaignPathLegacy | None:
    if not selected_choices:
        return None

    labels = tuple(label for _option_id, label, _bias in selected_choices)
    biases = tuple(bias for _option_id, _label, bias in selected_choices if bias is not None)
    summaries = tuple(dict.fromkeys(bias.summary for bias in biases))
    summary = " ".join(summaries) or "The selected route has no additional event pressure."
    adjustments = {
        category: sum(bias.adjustment_for(category) for bias in biases)
        for category in EventCategory
    }
    positive = max(adjustments.items(), key=lambda item: item[1])
    negative = min(adjustments.items(), key=lambda item: item[1])
    pressure_parts: list[str] = []
    if positive[1] > 0:
        pressure_parts.append(f"more {_campaign_category_label(positive[0])}")
    if negative[1] < 0:
        pressure_parts.append(f"fewer {_campaign_category_label(negative[0])}")
    pressure_line = (
        f"Expect {'; '.join(pressure_parts)}."
        if pressure_parts
        else "Event pressure stays balanced across this route."
    )
    journey = get_campaign_journey(scenario_id)
    if journey is None:
        mandate = "Carry the route trade-offs through the remaining company decisions."
    else:
        final_chapter = journey.chapters[-1]
        mandate = f"{final_chapter.objective} Watch for {final_chapter.primary_risk.lower()}"
    return CampaignPathLegacy(
        route_label=" -> ".join(labels),
        summary=summary,
        pressure_line=pressure_line,
        mandate=mandate,
        option_ids=tuple(option_id for option_id, _label, _bias in selected_choices),
    )


def _clean_campaign_choice_label(label: str) -> str:
    if label.startswith("Act ") and ": " in label:
        return label.split(": ", 1)[1]
    return label


def _campaign_category_label(category: EventCategory) -> str:
    return {
        EventCategory.PRODUCT_INCIDENT: "product incidents",
        EventCategory.MARKET_OPPORTUNITY: "market openings",
        EventCategory.FUNDING_OPPORTUNITY: "funding pressure",
        EventCategory.REPUTATION_INCIDENT: "reputation shocks",
        EventCategory.EMPLOYEE_ISSUE: "team issues",
    }[category]


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
