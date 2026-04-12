"""Validated domain entities for the game."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class CompetitorMove(StrEnum):
    """Current tactical posture used by a competitor this turn."""

    HOLD = "hold"
    DISCOUNT_PUSH = "discount_push"
    FEATURE_SPRINT = "feature_sprint"
    RETRENCH = "retrench"


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


class MilestoneId(StrEnum):
    """Supported one-time business milestones."""

    FIRST_100_USERS = "first_100_users"
    CASH_RESERVE_12000 = "cash_reserve_12000"
    TEAM_OF_4 = "team_of_4"
    THREE_ACTIVE_PRODUCTS = "three_active_products"
    FIRST_MATURE_PRODUCT = "first_mature_product"


class FundingType(StrEnum):
    """Capital source recorded in the company finance history."""

    ANGEL = "angel"
    VENTURE = "venture"
    LOAN = "loan"


class TurnAction(StrEnum):
    """Actions the player can take during a turn."""

    CREATE_PRODUCT = "create_product"
    IMPROVE_QUALITY = "improve_quality"
    ADD_FEATURE = "add_feature"
    REDUCE_TECHNICAL_DEBT = "reduce_technical_debt"
    MARKET_PRODUCT = "market_product"
    ADJUST_PRICING = "adjust_pricing"
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
    assigned_product_id: Optional[UUID] = None  # noqa: UP045

    @field_validator("salary", mode="before")
    @classmethod
    def _normalize_salary(cls, value: Decimal) -> Decimal:
        return quantize_money(value)


class Competitor(BaseModel):
    """A lightweight rival company competing in one segment."""

    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=80)
    focus_segment: MarketSegment
    strength: int = Field(ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    aggression: int = Field(ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    pricing_tier: PricingTier = PricingTier.STANDARD
    active_product_count: int = Field(default=1, ge=1, le=6)
    current_move: CompetitorMove = CompetitorMove.HOLD
    momentum: int = Field(default=50, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)


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
    total_raised: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    last_funding_turn: Optional[int] = Field(default=None, ge=1)  # noqa: UP045

    @field_validator("debt_principal", "total_raised", mode="before")
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


class GameState(BaseModel):
    """Current in-memory game state."""

    model_config = ConfigDict(validate_assignment=True)

    company: Company
    products: list[Product] = Field(min_length=1)
    employees: list[Employee] = Field(default_factory=list)
    finance: FinanceState = Field(default_factory=FinanceState)
    pending_event: Optional[PendingEvent] = None  # noqa: UP045
    event_history: list[EventHistoryEntry] = Field(default_factory=list)
    milestone_history: list[MilestoneEntry] = Field(default_factory=list)
    funding_history: list[FundingHistoryEntry] = Field(default_factory=list)
    roadmap_focus: RoadmapFocus = RoadmapFocus.BALANCED_EXECUTION
    roadmap_set_turn: int = Field(default=1, ge=1)
    market_cycle: MarketCycle = MarketCycle.STEADY
    market_cycle_turns_remaining: int = Field(default=3, ge=1)
    competitors: list[Competitor] = Field(default_factory=list)
    quarter_plan: QuarterPlan = Field(default_factory=QuarterPlan)
    turn_history: list[TurnLedgerEntry] = Field(default_factory=list)
    victory_achieved: bool = False
    victory_reason: Optional[str] = Field(default=None, max_length=240)  # noqa: UP045
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
    action_points_remaining: int = Field(ge=0)
