"""Validated content models for scenarios and product templates."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from nexus_tech.domain.constants import ATTRIBUTE_MAX, ATTRIBUTE_MIN
from nexus_tech.domain.models import (
    BudgetStance,
    CampaignGoalId,
    CompanyStrategy,
    CompetitorMove,
    DifficultyMode,
    EmployeeRole,
    LifecycleStage,
    MarketCycle,
    MarketSegment,
    PricingTier,
    RoadmapFocus,
    Seniority,
)
from nexus_tech.domain.money import quantize_money, quantize_rate


class ProductTemplateDefinition(BaseModel):
    """Data-driven starting blueprint for a product."""

    model_config = ConfigDict(validate_assignment=True)

    template_id: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=200)
    lifecycle_stage: LifecycleStage = LifecycleStage.PROTOTYPE
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

    @field_validator("revenue_per_user", "maintenance_cost", mode="before")
    @classmethod
    def _normalize_money(cls, value: Decimal) -> Decimal:
        return quantize_money(value)

    @field_validator("acquisition_rate", "churn_rate", mode="before")
    @classmethod
    def _normalize_rate(cls, value: Decimal) -> Decimal:
        return quantize_rate(value)


class ScenarioProductSeed(BaseModel):
    """One starting product entry inside a scenario definition."""

    model_config = ConfigDict(validate_assignment=True)

    key: str = Field(min_length=1, max_length=40)
    template_id: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=80)
    lifecycle_stage: Optional[LifecycleStage] = None  # noqa: UP045
    quality: Optional[int] = Field(default=None, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)  # noqa: UP045
    bug_level: Optional[int] = Field(default=None, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)  # noqa: UP045
    market_fit: Optional[int] = Field(default=None, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)  # noqa: UP045
    technical_debt: Optional[int] = Field(default=None, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)  # noqa: UP045
    user_count: Optional[int] = Field(default=None, ge=0)  # noqa: UP045
    revenue_per_user: Optional[Decimal] = None  # noqa: UP045
    feature_count: Optional[int] = Field(default=None, ge=0)  # noqa: UP045
    maintenance_cost: Optional[Decimal] = None  # noqa: UP045
    acquisition_rate: Optional[Decimal] = None  # noqa: UP045
    churn_rate: Optional[Decimal] = None  # noqa: UP045
    pricing_tier: Optional[PricingTier] = None  # noqa: UP045
    target_segment: Optional[MarketSegment] = None  # noqa: UP045
    is_active: bool = True

    @field_validator("revenue_per_user", "maintenance_cost", mode="before")
    @classmethod
    def _normalize_optional_money(cls, value: Optional[Decimal]) -> Optional[Decimal]:  # noqa: UP045
        if value is None:
            return None
        return quantize_money(value)

    @field_validator("acquisition_rate", "churn_rate", mode="before")
    @classmethod
    def _normalize_optional_rate(cls, value: Optional[Decimal]) -> Optional[Decimal]:  # noqa: UP045
        if value is None:
            return None
        return quantize_rate(value)


class ScenarioEmployeeSeed(BaseModel):
    """One starting employee inside a scenario definition."""

    model_config = ConfigDict(validate_assignment=True)

    full_name: str = Field(min_length=1, max_length=80)
    role: EmployeeRole
    seniority: Seniority
    specialization: Optional[str] = Field(default=None, min_length=1, max_length=40)  # noqa: UP045
    assigned_product_key: Optional[str] = Field(default=None, min_length=1, max_length=40)  # noqa: UP045
    energy: Optional[int] = Field(default=None, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)  # noqa: UP045
    morale: Optional[int] = Field(default=None, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)  # noqa: UP045
    productivity: Optional[int] = Field(default=None, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)  # noqa: UP045


class ScenarioCompetitorSeed(BaseModel):
    """One starting competitor defined inside a scenario."""

    model_config = ConfigDict(validate_assignment=True)

    name: str = Field(min_length=1, max_length=80)
    archetype_id: Optional[str] = Field(default=None, min_length=1, max_length=40)  # noqa: UP045
    focus_segment: Optional[MarketSegment] = None  # noqa: UP045
    strength: Optional[int] = Field(default=None, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)  # noqa: UP045
    aggression: Optional[int] = Field(default=None, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)  # noqa: UP045
    pricing_tier: Optional[PricingTier] = None  # noqa: UP045
    active_product_count: Optional[int] = Field(default=None, ge=1, le=6)  # noqa: UP045
    current_move: Optional[CompetitorMove] = None  # noqa: UP045
    momentum: Optional[int] = Field(default=None, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)  # noqa: UP045

    @model_validator(mode="after")
    def _validate_competitor_source(self) -> ScenarioCompetitorSeed:
        if self.archetype_id is not None:
            return self
        if self.focus_segment is None or self.strength is None or self.aggression is None:
            raise ValueError(
                "Scenario competitors must define focus_segment, strength, and aggression "
                "unless an archetype_id is provided."
            )
        return self


class CompetitorArchetypeDefinition(BaseModel):
    """Data-driven rival blueprint used to expand scenario content cleanly."""

    model_config = ConfigDict(validate_assignment=True)

    archetype_id: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=200)
    focus_segment: MarketSegment
    strength: int = Field(ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    aggression: int = Field(ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    pricing_tier: PricingTier = PricingTier.STANDARD
    active_product_count: int = Field(default=1, ge=1, le=6)
    current_move: CompetitorMove = CompetitorMove.HOLD
    momentum: int = Field(default=50, ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)


class ScenarioFinanceSeed(BaseModel):
    """Optional starting finance posture for a scenario."""

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

    @field_validator("debt_principal", "total_raised", mode="before")
    @classmethod
    def _normalize_finance_money(cls, value: Decimal) -> Decimal:
        return quantize_money(value)

    @field_validator("loan_interest_rate", "equity_dilution", mode="before")
    @classmethod
    def _normalize_finance_rate(cls, value: Decimal) -> Decimal:
        return quantize_rate(value)


class ScenarioDefinition(BaseModel):
    """Scenario definition for a full starting run."""

    model_config = ConfigDict(validate_assignment=True)

    scenario_id: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=240)
    company_name: str = Field(min_length=1, max_length=80)
    company_strategy: CompanyStrategy = CompanyStrategy.BALANCED
    difficulty_mode: DifficultyMode = DifficultyMode.STANDARD
    campaign_goal_id: CampaignGoalId = CampaignGoalId.PROFIT_MACHINE
    roadmap_focus: RoadmapFocus = RoadmapFocus.BALANCED_EXECUTION
    budget_stance: BudgetStance = BudgetStance.BALANCED
    market_cycle: MarketCycle = MarketCycle.STEADY
    market_cycle_turns_remaining: int = Field(default=3, ge=1)
    cash_on_hand: Decimal
    reputation: int = Field(ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)
    products: list[ScenarioProductSeed] = Field(min_length=1)
    employees: list[ScenarioEmployeeSeed] = Field(default_factory=list)
    competitors: list[ScenarioCompetitorSeed] = Field(default_factory=list)
    finance: Optional[ScenarioFinanceSeed] = None  # noqa: UP045

    @field_validator("cash_on_hand", mode="before")
    @classmethod
    def _normalize_cash(cls, value: Decimal) -> Decimal:
        return quantize_money(value)
