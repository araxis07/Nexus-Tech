"""Validated domain entities for the game."""

from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from nexus_tech.domain.money import quantize_money


class TurnAction(str, Enum):
    """Actions the player can take during a turn."""

    BUILD_FEATURE = "build_feature"
    FIX_BUGS = "fix_bugs"
    MARKET_PRODUCT = "market_product"
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
    """The company's only product in Phase 1."""

    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=80)
    quality: int = Field(ge=0, le=100)
    bug_level: int = Field(ge=0, le=100)
    user_count: int = Field(ge=0)
    revenue_per_user: Decimal = Field(ge=Decimal("0"))
    feature_count: int = Field(ge=0)

    @field_validator("revenue_per_user", mode="before")
    @classmethod
    def _normalize_revenue_per_user(cls, value: Decimal) -> Decimal:
        return quantize_money(value)


class GameState(BaseModel):
    """Current in-memory game state."""

    model_config = ConfigDict(validate_assignment=True)

    company: Company
    product: Product
    action_points_remaining: int = Field(ge=0)
