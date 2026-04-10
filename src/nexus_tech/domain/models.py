"""Validated domain entities for the game."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class TurnAction(StrEnum):
    """Actions the player can take during a turn."""

    CREATE_PRODUCT = "create_product"
    IMPROVE_QUALITY = "improve_quality"
    ADD_FEATURE = "add_feature"
    REDUCE_TECHNICAL_DEBT = "reduce_technical_debt"
    MARKET_PRODUCT = "market_product"
    SUNSET_PRODUCT = "sunset_product"
    HIRE_EMPLOYEE = "hire_employee"
    FIRE_EMPLOYEE = "fire_employee"
    ASSIGN_EMPLOYEE = "assign_employee"
    UNASSIGN_EMPLOYEE = "unassign_employee"
    REST_TEAM = "rest_team"
    REVIEW_TEAM = "review_team"
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


class GameState(BaseModel):
    """Current in-memory game state."""

    model_config = ConfigDict(validate_assignment=True)

    company: Company
    products: list[Product] = Field(min_length=1)
    employees: list[Employee] = Field(default_factory=list)
    pending_event: Optional[PendingEvent] = None  # noqa: UP045
    event_history: list[EventHistoryEntry] = Field(default_factory=list)
    action_points_remaining: int = Field(ge=0)
