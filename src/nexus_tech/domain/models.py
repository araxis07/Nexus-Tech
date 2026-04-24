"""Validated domain entities for the game."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from nexus_tech.config import DEFAULT_SCENARIO_ID, DEFAULT_SCENARIO_TITLE
from nexus_tech.domain.constants import ATTRIBUTE_MAX, ATTRIBUTE_MIN
from nexus_tech.domain.money import quantize_money, quantize_rate

try:
    from enum import StrEnum
except ImportError:  # pragma: no cover - fallback for local verification on Python < 3.11

    class StrEnum(str, Enum):  # noqa: UP042
        """Compatibility fallback for runtimes without `enum.StrEnum`."""


class LifecycleStage(StrEnum):
    """Product lifecycle stage used by growth and UX."""

    PROTOTYPE = "prototype"
    GROWTH = "growth"
    MATURE = "mature"
    DECLINING = "declining"
    SUNSET = "sunset"


class EmployeeRole(StrEnum):
    """Supported employee roles in the company."""

    ENGINEER = "engineer"
    DESIGNER = "designer"
    MARKETER = "marketer"
    PRODUCT_MANAGER = "product_manager"


class CompanyStrategy(StrEnum):
    """Company-level strategic posture."""

    BALANCED = "balanced"
    GROWTH = "growth"
    QUALITY = "quality"
    EFFICIENCY = "efficiency"


class PricingTier(StrEnum):
    """Product pricing posture used by economy and growth systems."""

    BUDGET = "budget"
    STANDARD = "standard"
    PREMIUM = "premium"


class PackagingStrategy(StrEnum):
    """Product packaging posture used by monetization and account depth systems."""

    STREAMLINED = "streamlined"
    MODULAR = "modular"
    SUITE = "suite"


class MarketSegment(StrEnum):
    """Primary customer segment targeted by a product."""

    INDIE = "indie"
    STARTUP = "startup"
    SMB = "smb"
    ENTERPRISE = "enterprise"


class RoadmapFocus(StrEnum):
    """Quarter-scale planning posture for the company."""

    BALANCED_EXECUTION = "balanced_execution"
    GROWTH_PUSH = "growth_push"
    PLATFORM_REBUILD = "platform_rebuild"
    PREMIUM_EXPANSION = "premium_expansion"
    PORTFOLIO_CONSOLIDATION = "portfolio_consolidation"
    AI_TRUST_PROGRAM = "ai_trust_program"
    COMMUNITY_GROWTH = "community_growth"
    ENTERPRISE_SALES_PUSH = "enterprise_sales_push"


class BudgetStance(StrEnum):
    """Budget posture for the current quarter plan."""

    LEAN = "lean"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class MarketCycle(StrEnum):
    """Current market environment affecting demand and churn."""

    COOLING = "cooling"
    STEADY = "steady"
    EXPANDING = "expanding"
    FROTHY = "frothy"


class DifficultyMode(StrEnum):
    """Run difficulty profile used to tune pressure and pacing."""

    BUILDER = "builder"
    STANDARD = "standard"
    FOUNDER = "founder"


class CompetitorMove(StrEnum):
    """Current tactical posture used by a competitor this turn."""

    HOLD = "hold"
    DISCOUNT_PUSH = "discount_push"
    FEATURE_SPRINT = "feature_sprint"
    RETRENCH = "retrench"


class CustomerAccountStatus(StrEnum):
    """Lifecycle state for a key customer account."""

    ACTIVE = "active"
    AT_RISK = "at_risk"
    CHURNED = "churned"


class ContractCadence(StrEnum):
    """Commercial renewal cadence for a customer account."""

    MONTHLY = "monthly"
    ANNUAL = "annual"


class ContractBillingModel(StrEnum):
    """Commercial billing model used by enterprise-style customer accounts."""

    FLAT = "flat"
    SEAT_BASED = "seat_based"
    USAGE_BASED = "usage_based"


class SubscriptionPackage(StrEnum):
    """Commercial package that shapes account monetization depth."""

    STARTER = "starter"
    GROWTH = "growth"
    ENTERPRISE_SUITE = "enterprise_suite"


class FunctionalBudgetPreset(StrEnum):
    """Named operating-allocation presets for cross-functional spend."""

    BALANCED = "balanced"
    PRODUCT_PUSH = "product_push"
    GROWTH_PUSH = "growth_push"
    CUSTOMER_TRUST = "customer_trust"
    CASH_GUARD = "cash_guard"


class ExitOutcome(StrEnum):
    """Endgame classification for a completed run."""

    PROFITABLE_INDEPENDENCE = "profitable_independence"
    STRATEGIC_ACQUISITION = "strategic_acquisition"
    IPO_READY = "ipo_ready"
    RESTRUCTURE = "restructure"


class EventCategory(StrEnum):
    """Supported event categories for the dynamic event engine."""

    PRODUCT_INCIDENT = "product_incident"
    MARKET_OPPORTUNITY = "market_opportunity"
    FUNDING_OPPORTUNITY = "funding_opportunity"
    REPUTATION_INCIDENT = "reputation_incident"
    EMPLOYEE_ISSUE = "employee_issue"


class Seniority(StrEnum):
    """Seniority band for an employee."""

    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"


class CandidateTrait(StrEnum):
    """Hiring-market trait that slightly changes employee economics."""

    STEADY_OPERATOR = "steady_operator"
    FAST_LEARNER = "fast_learner"
    EXPENSIVE_EXPERT = "expensive_expert"
    BURNOUT_RISK = "burnout_risk"


class MilestoneId(StrEnum):
    """Supported one-time business milestones."""

    FIRST_100_USERS = "first_100_users"
    CASH_RESERVE_12000 = "cash_reserve_12000"
    TEAM_OF_4 = "team_of_4"
    THREE_ACTIVE_PRODUCTS = "three_active_products"
    FIRST_MATURE_PRODUCT = "first_mature_product"
    PROFITABLE_STREAK = "profitable_streak"
    MULTI_SEGMENT_REACH = "multi_segment_reach"
    OPERATIONS_MACHINE = "operations_machine"
    ENTERPRISE_FOOTING = "enterprise_footing"
    DEBT_FREE_OPERATOR = "debt_free_operator"
    CATEGORY_MOAT = "category_moat"
    TALENT_BENCH = "talent_bench"
    PLATFORM_CREDIBILITY = "platform_credibility"
    CAPITAL_DISCIPLINE = "capital_discipline"
    RIVAL_RESILIENCE = "rival_resilience"


class FundingType(StrEnum):
    """Capital source recorded in the company finance history."""

    ANGEL = "angel"
    VENTURE = "venture"
    LOAN = "loan"


class CampaignGoalId(StrEnum):
    """Optional long-form company objective for one run."""

    PROFIT_MACHINE = "profit_machine"
    PORTFOLIO_EMPIRE = "portfolio_empire"
    CATEGORY_LEADER = "category_leader"


class ScenarioObjectiveMetric(StrEnum):
    """Content-driven scenario objective progress metric."""

    NONE = "none"
    CASH = "cash"
    USERS = "users"
    REPUTATION = "reputation"
    ACTIVE_PRODUCTS = "active_products"
    ENTERPRISE_USERS = "enterprise_users"
    ACTIVE_DEALS = "active_deals"
    CLOSED_DEALS = "closed_deals"


class ProductReleaseType(StrEnum):
    """Types of product releases the player can plan."""

    STABILITY_PATCH = "stability_patch"
    MINOR_RELEASE = "minor_release"
    MAJOR_LAUNCH = "major_launch"


class ProductReleaseStatus(StrEnum):
    """Lifecycle for a product release plan."""

    PLANNED = "planned"
    SHIPPED = "shipped"


class SalesDealStage(StrEnum):
    """Simplified enterprise sales pipeline stage."""

    LEAD = "lead"
    DEMO = "demo"
    PILOT = "pilot"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class HiringCandidateStage(StrEnum):
    """Lifecycle stage for a persisted hiring-pipeline candidate."""

    SOURCED = "sourced"
    SCREENED = "screened"
    INTERVIEWED = "interviewed"
    DECLINED = "declined"
    EXPIRED = "expired"


class RoadmapProjectType(StrEnum):
    """Multi-turn strategic projects beyond the active roadmap modifier."""

    PLATFORM_REBUILD = "platform_rebuild"
    ENTERPRISE_CERTIFICATION = "enterprise_certification"
    MARKETPLACE_LAUNCH = "marketplace_launch"
    SALES_PLAYBOOK = "sales_playbook"


class RoadmapProjectStatus(StrEnum):
    """Lifecycle for a roadmap project."""

    ACTIVE = "active"
    COMPLETED = "completed"


class BalanceProfileId(StrEnum):
    """Named balance presets for tuning and demos."""

    DEMO = "demo"
    STANDARD = "standard"
    HARD = "hard"
    LONG_RUN = "long_run"


class BoardDirective(StrEnum):
    """Current board ask used to communicate governance pressure."""

    STABILIZE_CASH = "stabilize_cash"
    PROVE_RELIABILITY = "prove_reliability"
    ACCELERATE_GROWTH = "accelerate_growth"


class BoardAsk(StrEnum):
    """Current board-level operating ask tracked across review cycles."""

    PROFITABILITY = "profitability"
    RELIABILITY = "reliability"
    TEAM_HEALTH = "team_health"
    PORTFOLIO_FOCUS = "portfolio_focus"


class SupportInvestmentFocus(StrEnum):
    """Explicit support-system investment focus."""

    KNOWLEDGE_BASE = "knowledge_base"
    AUTOMATION = "automation"
    SLA_PROGRAM = "sla_program"


class TurnAction(StrEnum):
    """Actions the player can take during a turn."""

    CREATE_PRODUCT = "create_product"
    IMPROVE_QUALITY = "improve_quality"
    ADD_FEATURE = "add_feature"
    REDUCE_TECHNICAL_DEBT = "reduce_technical_debt"
    MARKET_PRODUCT = "market_product"
    ADJUST_PRICING = "adjust_pricing"
    RUN_PRICE_INCREASE = "run_price_increase"
    SET_PACKAGING_STRATEGY = "set_packaging_strategy"
    SET_TARGET_SEGMENT = "set_target_segment"
    SUNSET_PRODUCT = "sunset_product"
    SET_COMPANY_STRATEGY = "set_company_strategy"
    SET_ROADMAP = "set_roadmap"
    SET_BUDGET_STANCE = "set_budget_stance"
    TAKE_LOAN = "take_loan"
    RAISE_ANGEL = "raise_angel"
    RAISE_VC = "raise_vc"
    REPAY_DEBT = "repay_debt"
    REVIEW_FINANCE = "review_finance"
    HIRE_EMPLOYEE = "hire_employee"
    FIRE_EMPLOYEE = "fire_employee"
    ASSIGN_EMPLOYEE = "assign_employee"
    UNASSIGN_EMPLOYEE = "unassign_employee"
    REST_TEAM = "rest_team"
    REVIEW_TEAM = "review_team"
    REVIEW_CUSTOMERS = "review_customers"
    INVEST_IN_CUSTOMER_SUCCESS = "invest_in_customer_success"
    RUN_RETENTION_PLAY = "run_retention_play"
    TRAIN_EMPLOYEE = "train_employee"
    PROMOTE_EMPLOYEE = "promote_employee"
    SOURCE_CANDIDATES = "source_candidates"
    SCREEN_CANDIDATE = "screen_candidate"
    INTERVIEW_CANDIDATE = "interview_candidate"
    MAKE_HIRING_OFFER = "make_hiring_offer"
    TRIAGE_SUPPORT_BACKLOG = "triage_support_backlog"
    UPGRADE_SUPPORT_PROGRAM = "upgrade_support_program"
    SET_FUNCTIONAL_BUDGET = "set_functional_budget"
    ASSIGN_MANAGER = "assign_manager"
    CLEAR_MANAGER = "clear_manager"
    REORG_TEAM = "reorg_team"
    PLAN_RELEASE = "plan_release"
    WORK_RELEASE = "work_release"
    CREATE_SALES_DEAL = "create_sales_deal"
    ADVANCE_SALES_DEAL = "advance_sales_deal"
    START_ROADMAP_PROJECT = "start_roadmap_project"
    WORK_ROADMAP_PROJECT = "work_roadmap_project"
    REVIEW_PIPELINE = "review_pipeline"
    REVIEW_BOARD = "review_board"
    EXECUTE_BOARD_RESPONSE = "execute_board_response"
    VIEW_REPORT = "view_report"
    WAIT = "wait"
    VIEW_STATUS = "view_status"
    END_TURN = "end_turn"


class Company(BaseModel):
    """High-level company state."""

    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=80)
    cash_on_hand: Decimal
    reputation: int = Field(ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    strategy: CompanyStrategy = CompanyStrategy.BALANCED
    current_turn: int = Field(default=1, ge=1)
    game_over: bool = False

    @field_validator("cash_on_hand", mode="before")
    @classmethod
    def _normalize_cash(cls, value: Decimal) -> Decimal:
        return quantize_money(value)


class Product(BaseModel):
    """A single software product in the company portfolio."""

    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=80)
    lifecycle_stage: LifecycleStage
    quality: int = Field(ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    bug_level: int = Field(ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    market_fit: int = Field(ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    technical_debt: int = Field(ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    user_count: int = Field(ge=0)
    revenue_per_user: Decimal = Field(ge=Decimal("0"))
    feature_count: int = Field(ge=0)
    maintenance_cost: Decimal = Field(ge=Decimal("0"))
    acquisition_rate: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    churn_rate: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    pricing_tier: PricingTier = PricingTier.STANDARD
    packaging_strategy: PackagingStrategy = PackagingStrategy.STREAMLINED
    target_segment: MarketSegment = MarketSegment.STARTUP
    is_active: bool = True

    @field_validator("revenue_per_user", "maintenance_cost", mode="before")
    @classmethod
    def _normalize_money_fields(cls, value: Decimal) -> Decimal:
        return quantize_money(value)

    @field_validator("acquisition_rate", "churn_rate", mode="before")
    @classmethod
    def _normalize_rate_fields(cls, value: Decimal) -> Decimal:
        return quantize_rate(value)


class Employee(BaseModel):
    """A single employee in the company."""

    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(default_factory=uuid4)
    full_name: str = Field(min_length=1, max_length=80)
    role: EmployeeRole
    seniority: Seniority
    salary: Decimal = Field(ge=Decimal("0"))
    energy: int = Field(ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    morale: int = Field(ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    productivity: int = Field(ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    specialization: str = Field(min_length=1, max_length=40)
    trait: CandidateTrait = CandidateTrait.STEADY_OPERATOR
    experience_points: int = Field(default=0, ge=0)
    promotion_readiness: int = Field(default=0, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    attrition_risk: int = Field(default=0, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    performance_rating: int = Field(default=62, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    tenure_turns: int = Field(default=0, ge=0)
    underperformance_streak: int = Field(default=0, ge=0)
    leadership_score: int = Field(default=55, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    assigned_product_id: Optional[UUID] = None  # noqa: UP045
    manager_id: Optional[UUID] = None  # noqa: UP045

    @field_validator("salary", mode="before")
    @classmethod
    def _normalize_salary(cls, value: Decimal) -> Decimal:
        return quantize_money(value)


class Competitor(BaseModel):
    """A lightweight rival company competing in one segment."""

    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=80)
    archetype_id: Optional[str] = Field(default=None, min_length=1, max_length=40)  # noqa: UP045
    focus_segment: MarketSegment
    strength: int = Field(ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    aggression: int = Field(ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    pricing_tier: PricingTier = PricingTier.STANDARD
    active_product_count: int = Field(default=1, ge=1, le=6)
    current_move: CompetitorMove = CompetitorMove.HOLD
    momentum: int = Field(default=50, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    funding_level: int = Field(default=0, ge=0, le=5)


class FinanceState(BaseModel):
    """Financing posture for the current company run."""

    model_config = ConfigDict(validate_assignment=True)

    debt_principal: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    loan_interest_rate: Decimal = Field(
        default=Decimal("0.0000"),
        ge=Decimal("0"),
        le=Decimal("1"),
    )
    equity_dilution: Decimal = Field(
        default=Decimal("0.0000"),
        ge=Decimal("0"),
        le=Decimal("1"),
    )
    investor_pressure: int = Field(default=0, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    board_confidence: int = Field(default=55, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    covenant_risk: int = Field(default=0, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    missed_board_targets: int = Field(default=0, ge=0)
    total_raised: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    forecast_net_cash_flow: Decimal = Field(default=Decimal("0.00"))
    forecast_runway_turns: Optional[int] = Field(default=None, ge=0)  # noqa: UP045
    burn_multiple: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    governance_risk: int = Field(default=0, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    board_pressure: int = Field(default=0, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    board_directive: BoardDirective = BoardDirective.ACCELERATE_GROWTH
    active_board_ask: BoardAsk = BoardAsk.PROFITABILITY
    board_warning_active: bool = False
    board_warning_level: int = Field(default=0, ge=0, le=3)
    last_board_review_turn: Optional[int] = Field(default=None, ge=1)  # noqa: UP045
    last_funding_turn: Optional[int] = Field(default=None, ge=1)  # noqa: UP045

    @field_validator(
        "debt_principal",
        "total_raised",
        "forecast_net_cash_flow",
        "burn_multiple",
        mode="before",
    )
    @classmethod
    def _normalize_finance_money(cls, value: Decimal) -> Decimal:
        return quantize_money(value)

    @field_validator("loan_interest_rate", "equity_dilution", mode="before")
    @classmethod
    def _normalize_finance_rate(cls, value: Decimal) -> Decimal:
        return quantize_rate(value)


class QuarterPlan(BaseModel):
    """Quarter-scale operating plan with targets and spending posture."""

    model_config = ConfigDict(validate_assignment=True)

    budget_stance: BudgetStance = BudgetStance.BALANCED
    set_turn: int = Field(default=1, ge=1)
    target_turn: int = Field(default=4, ge=1)
    revenue_target: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    user_target: int = Field(default=0, ge=0)
    cash_reserve_target: Decimal = Field(default=Decimal("0.00"))
    headcount_cap: int = Field(default=0, ge=0)

    @field_validator("revenue_target", "cash_reserve_target", mode="before")
    @classmethod
    def _normalize_plan_money(cls, value: Decimal) -> Decimal:
        return quantize_money(value)


class FunctionalBudget(BaseModel):
    """Cross-functional operating allocation used by efficiency systems."""

    model_config = ConfigDict(validate_assignment=True)

    preset: FunctionalBudgetPreset = FunctionalBudgetPreset.BALANCED
    engineering_share: int = Field(default=30, ge=0, le=100)
    marketing_share: int = Field(default=25, ge=0, le=100)
    customer_success_share: int = Field(default=25, ge=0, le=100)
    g_and_a_share: int = Field(default=20, ge=0, le=100)

    @model_validator(mode="after")
    def _validate_total_share(self) -> "FunctionalBudget":
        total_share = (
            self.engineering_share
            + self.marketing_share
            + self.customer_success_share
            + self.g_and_a_share
        )
        if total_share != 100:
            raise ValueError("Functional budget shares must total 100.")
        return self


class SupportProgram(BaseModel):
    """Shared customer-support tooling and deflection state."""

    model_config = ConfigDict(validate_assignment=True)

    knowledge_base_level: int = Field(default=22, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    automation_level: int = Field(default=16, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    sla_target: int = Field(default=58, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    backlog_queue: int = Field(default=0, ge=0)
    escalation_queue: int = Field(default=0, ge=0)
    resolved_last_turn: int = Field(default=0, ge=0)
    deflection_score: int = Field(default=0, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    sla_breaches_last_turn: int = Field(default=0, ge=0)


class CustomerAccount(BaseModel):
    """A key account that creates renewal and concentration pressure."""

    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=80)
    product_id: UUID
    segment: MarketSegment
    contract_value: Decimal = Field(ge=Decimal("0"))
    plan_tier: PricingTier = PricingTier.STANDARD
    subscription_package: SubscriptionPackage = SubscriptionPackage.GROWTH
    contract_cadence: ContractCadence = ContractCadence.ANNUAL
    billing_model: ContractBillingModel = ContractBillingModel.FLAT
    seat_count: int = Field(default=0, ge=0)
    usage_units: int = Field(default=0, ge=0)
    add_on_count: int = Field(default=0, ge=0)
    annual_prepay: bool = False
    discount_rate: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0"), le=Decimal("1"))
    satisfaction: int = Field(ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    onboarding_health: int = Field(default=60, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    support_load: int = Field(default=20, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    open_tickets: int = Field(default=0, ge=0)
    sla_breach_risk: int = Field(default=0, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    invoice_risk: int = Field(default=0, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    failed_payment_risk: int = Field(default=0, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    dunning_steps: int = Field(default=0, ge=0)
    escalation_count: int = Field(default=0, ge=0)
    expansion_potential: int = Field(ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    renewal_health: int = Field(default=60, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    renewal_turn: int = Field(ge=1)
    churn_risk: int = Field(default=0, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    status: CustomerAccountStatus = CustomerAccountStatus.ACTIVE

    @field_validator("contract_value", mode="before")
    @classmethod
    def _normalize_contract_value(cls, value: Decimal) -> Decimal:
        return quantize_money(value)

    @field_validator("discount_rate", mode="before")
    @classmethod
    def _normalize_discount_rate(cls, value: Decimal) -> Decimal:
        return quantize_rate(value)


class EventOption(BaseModel):
    """A single response option for a triggered event."""

    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=200)


class PendingEvent(BaseModel):
    """An unresolved event waiting for automatic or player-driven resolution."""

    model_config = ConfigDict(validate_assignment=True)

    event_id: str = Field(min_length=1, max_length=60)
    category: EventCategory
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=320)
    triggered_turn: int = Field(ge=1)
    cooldown_turns: int = Field(ge=0)
    chain_id: Optional[str] = Field(default=None, min_length=1, max_length=60)  # noqa: UP045
    chain_stage: int = Field(default=0, ge=0)
    target_product_id: Optional[UUID] = None  # noqa: UP045
    target_employee_id: Optional[UUID] = None  # noqa: UP045
    options: list[EventOption] = Field(min_length=1, max_length=3)


class EventHistoryEntry(BaseModel):
    """A resolved event kept in in-memory history."""

    model_config = ConfigDict(validate_assignment=True)

    event_id: str = Field(min_length=1, max_length=60)
    category: EventCategory
    title: str = Field(min_length=1, max_length=120)
    triggered_turn: int = Field(ge=1)
    resolved_turn: int = Field(ge=1)
    chain_id: Optional[str] = Field(default=None, min_length=1, max_length=60)  # noqa: UP045
    chain_stage: int = Field(default=0, ge=0)
    selected_option_id: str = Field(min_length=1, max_length=40)
    selected_option_label: str = Field(min_length=1, max_length=80)
    result_text: str = Field(min_length=1, max_length=240)


class MilestoneEntry(BaseModel):
    """A one-time company milestone unlocked during a run."""

    model_config = ConfigDict(validate_assignment=True)

    milestone_id: MilestoneId
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=240)
    unlocked_turn: int = Field(ge=1)
    reward_text: str = Field(min_length=1, max_length=240)


class FundingHistoryEntry(BaseModel):
    """One financing decision recorded in the run history."""

    model_config = ConfigDict(validate_assignment=True)

    funding_type: FundingType
    turn: int = Field(ge=1)
    amount: Decimal = Field(ge=Decimal("0"))
    dilution_added: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0"), le=Decimal("1"))
    debt_added: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    summary: str = Field(min_length=1, max_length=240)

    @field_validator("amount", "debt_added", mode="before")
    @classmethod
    def _normalize_funding_money(cls, value: Decimal) -> Decimal:
        return quantize_money(value)

    @field_validator("dilution_added", mode="before")
    @classmethod
    def _normalize_funding_rate(cls, value: Decimal) -> Decimal:
        return quantize_rate(value)


class TurnLedgerEntry(BaseModel):
    """Compact turn history snapshot for reporting and scoring."""

    model_config = ConfigDict(validate_assignment=True)

    turn: int = Field(ge=1)
    total_revenue: Decimal
    total_operating_cost: Decimal
    net_cash_flow: Decimal
    cash_on_hand: Decimal
    reputation: int = Field(ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    total_users: int = Field(ge=0)
    headcount: int = Field(ge=0)
    roadmap_focus: RoadmapFocus

    @field_validator(
        "total_revenue",
        "total_operating_cost",
        "net_cash_flow",
        "cash_on_hand",
        mode="before",
    )
    @classmethod
    def _normalize_turn_money(cls, value: Decimal) -> Decimal:
        return quantize_money(value)


class ProductReleasePlan(BaseModel):
    """A planned product release that can be worked over multiple actions."""

    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(default_factory=uuid4)
    product_id: UUID
    release_type: ProductReleaseType
    status: ProductReleaseStatus = ProductReleaseStatus.PLANNED
    progress: int = Field(default=0, ge=0)
    required_progress: int = Field(default=6, ge=1)
    risk: int = Field(default=0, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    scheduled_turn: int = Field(ge=1)
    shipped_turn: Optional[int] = Field(default=None, ge=1)  # noqa: UP045
    summary: str = Field(default="", max_length=240)


class SalesDeal(BaseModel):
    """A lightweight enterprise sales opportunity."""

    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(default_factory=uuid4)
    product_id: UUID
    name: str = Field(min_length=1, max_length=80)
    segment: MarketSegment = MarketSegment.ENTERPRISE
    stage: SalesDealStage = SalesDealStage.LEAD
    plan_tier: PricingTier = PricingTier.STANDARD
    subscription_package: SubscriptionPackage = SubscriptionPackage.GROWTH
    billing_model: ContractBillingModel = ContractBillingModel.FLAT
    seat_commitment: int = Field(default=0, ge=0)
    usage_commitment: int = Field(default=0, ge=0)
    add_on_commitment: int = Field(default=0, ge=0)
    annual_prepay_offer: bool = False
    value: Decimal = Field(ge=Decimal("0"))
    proposed_discount_rate: Decimal = Field(
        default=Decimal("0.0000"),
        ge=Decimal("0"),
        le=Decimal("1"),
    )
    probability: int = Field(default=30, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    created_turn: int = Field(ge=1)
    updated_turn: int = Field(ge=1)

    @field_validator("value", mode="before")
    @classmethod
    def _normalize_deal_value(cls, value: Decimal) -> Decimal:
        return quantize_money(value)

    @field_validator("proposed_discount_rate", mode="before")
    @classmethod
    def _normalize_deal_discount(cls, value: Decimal) -> Decimal:
        return quantize_rate(value)


class HiringCandidate(BaseModel):
    """A persisted candidate moving through the hiring pipeline."""

    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(default_factory=uuid4)
    full_name: str = Field(min_length=1, max_length=80)
    role: EmployeeRole
    seniority: Seniority
    specialization: str = Field(min_length=1, max_length=40)
    trait: CandidateTrait = CandidateTrait.STEADY_OPERATOR
    salary_expectation: Decimal = Field(ge=Decimal("0"))
    expected_productivity: int = Field(ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    stage: HiringCandidateStage = HiringCandidateStage.SOURCED
    sourced_turn: int = Field(ge=1)
    expires_turn: int = Field(ge=1)
    offer_deadline_turn: int = Field(default=1, ge=1)
    interview_score: int = Field(default=0, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    acceptance_chance: int = Field(default=50, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    market_salary_pressure: int = Field(default=0, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    negotiation_rounds: int = Field(default=0, ge=0)

    @field_validator("salary_expectation", mode="before")
    @classmethod
    def _normalize_candidate_salary(cls, value: Decimal) -> Decimal:
        return quantize_money(value)


class RoadmapProject(BaseModel):
    """A multi-action strategic project with completion effects."""

    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(default_factory=uuid4)
    project_type: RoadmapProjectType
    status: RoadmapProjectStatus = RoadmapProjectStatus.ACTIVE
    target_product_id: Optional[UUID] = None  # noqa: UP045
    progress: int = Field(default=0, ge=0)
    required_progress: int = Field(default=8, ge=1)
    epic_count: int = Field(default=3, ge=1)
    epics_completed: int = Field(default=0, ge=0)
    started_turn: int = Field(ge=1)
    deadline_turn: int = Field(default=1, ge=1)
    dependency_project_type: Optional[RoadmapProjectType] = None  # noqa: UP045
    delivery_risk: int = Field(default=0, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    completed_turn: Optional[int] = Field(default=None, ge=1)  # noqa: UP045
    summary: str = Field(default="", max_length=240)


class CompetitorIntelEntry(BaseModel):
    """One compact competitor intelligence note."""

    model_config = ConfigDict(validate_assignment=True)

    turn: int = Field(ge=1)
    competitor_name: str = Field(min_length=1, max_length=80)
    move: CompetitorMove
    summary: str = Field(min_length=1, max_length=240)


class GameState(BaseModel):
    """Current in-memory game state."""

    model_config = ConfigDict(validate_assignment=True)

    company: Company
    products: list[Product] = Field(min_length=1)
    employees: list[Employee] = Field(default_factory=list)
    finance: FinanceState = Field(default_factory=FinanceState)
    support_program: SupportProgram = Field(default_factory=SupportProgram)
    pending_event: Optional[PendingEvent] = None  # noqa: UP045
    event_history: list[EventHistoryEntry] = Field(default_factory=list)
    milestone_history: list[MilestoneEntry] = Field(default_factory=list)
    funding_history: list[FundingHistoryEntry] = Field(default_factory=list)
    roadmap_focus: RoadmapFocus = RoadmapFocus.BALANCED_EXECUTION
    roadmap_set_turn: int = Field(default=1, ge=1)
    market_cycle: MarketCycle = MarketCycle.STEADY
    market_cycle_turns_remaining: int = Field(default=3, ge=1)
    difficulty_mode: DifficultyMode = DifficultyMode.STANDARD
    campaign_goal_id: CampaignGoalId = CampaignGoalId.PROFIT_MACHINE
    competitors: list[Competitor] = Field(default_factory=list)
    customer_accounts: list[CustomerAccount] = Field(default_factory=list)
    hiring_candidates: list[HiringCandidate] = Field(default_factory=list)
    product_releases: list[ProductReleasePlan] = Field(default_factory=list)
    sales_deals: list[SalesDeal] = Field(default_factory=list)
    roadmap_projects: list[RoadmapProject] = Field(default_factory=list)
    competitor_intel: list[CompetitorIntelEntry] = Field(default_factory=list)
    quarter_plan: QuarterPlan = Field(default_factory=QuarterPlan)
    functional_budget: FunctionalBudget = Field(default_factory=FunctionalBudget)
    turn_history: list[TurnLedgerEntry] = Field(default_factory=list)
    victory_achieved: bool = False
    victory_reason: Optional[str] = Field(default=None, max_length=240)  # noqa: UP045
    exit_outcome: Optional[ExitOutcome] = None  # noqa: UP045
    exit_summary: Optional[str] = Field(default=None, max_length=240)  # noqa: UP045
    scenario_id: str = Field(
        default=DEFAULT_SCENARIO_ID,
        min_length=1,
        max_length=40,
    )
    scenario_title: str = Field(
        default=DEFAULT_SCENARIO_TITLE,
        min_length=1,
        max_length=80,
    )
    scenario_objective: str = Field(default="", max_length=220)
    scenario_objective_metric: ScenarioObjectiveMetric = ScenarioObjectiveMetric.NONE
    scenario_objective_target: int = Field(default=0, ge=0)
    action_points_remaining: int = Field(ge=0)
