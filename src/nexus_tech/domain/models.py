"""Validated domain entities for the game."""

from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from nexus_tech.domain.money import quantize_money, quantize_rate


class LifecycleStage(str, Enum):
    """Product lifecycle stage used by growth and UX."""

    PROTOTYPE = "prototype"
    GROWTH = "growth"
    MATURE = "mature"
    DECLINING = "declining"
    SUNSET = "sunset"


class TurnAction(str, Enum):
    """Actions the player can take during a turn."""

    CREATE_PRODUCT = "create_product"
    IMPROVE_QUALITY = "improve_quality"
    ADD_FEATURE = "add_feature"
    REDUCE_TECHNICAL_DEBT = "reduce_technical_debt"
    MARKET_PRODUCT = "market_product"
    SUNSET_PRODUCT = "sunset_product"
    WAIT = "wait"
    VIEW_STATUS = "view_status"
    END_TURN = "end_turn"


class Company(BaseModel):
    """High-level company state."""

    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=80)
    cash_on_hand: Decimal
    reputation: int = Field(ge=0, le=100)
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
    quality: int = Field(ge=0, le=100)
    bug_level: int = Field(ge=0, le=100)
    market_fit: int = Field(ge=0, le=100)
    technical_debt: int = Field(ge=0, le=100)
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


class GameState(BaseModel):
    """Current in-memory game state."""

    model_config = ConfigDict(validate_assignment=True)

    company: Company
    products: list[Product] = Field(min_length=1)
    action_points_remaining: int = Field(ge=0)
