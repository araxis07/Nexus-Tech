"""Company-wide strategy settings and their simulation effects."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.constants import ZERO_MONEY
from nexus_tech.domain.models import Company, CompanyStrategy


@dataclass(frozen=True)
class StrategyActionSummary:
    """Summary of changing the current company strategy."""

    message: str


@dataclass(frozen=True)
class StrategyProfile:
    """Named modifiers applied by the current company strategy."""

    acquisition_bonus: int = 0
    marketing_user_bonus: int = 0
    quality_bonus: int = 0
    stability_bonus: int = 0
    operating_cost_modifier: Decimal = ZERO_MONEY
    burnout_relief: int = 0
    reputation_bonus: int = 0
    debt_reduction_bonus: int = 0
    feature_risk_modifier: int = 0


_STRATEGY_PROFILES = {
    CompanyStrategy.BALANCED: StrategyProfile(),
    CompanyStrategy.GROWTH: StrategyProfile(
        acquisition_bonus=2,
        marketing_user_bonus=2,
        operating_cost_modifier=Decimal("70.00"),
        burnout_relief=-1,
        feature_risk_modifier=1,
    ),
    CompanyStrategy.QUALITY: StrategyProfile(
        acquisition_bonus=-1,
        marketing_user_bonus=-1,
        quality_bonus=2,
        stability_bonus=2,
        operating_cost_modifier=Decimal("40.00"),
        reputation_bonus=1,
        debt_reduction_bonus=1,
        feature_risk_modifier=-1,
    ),
    CompanyStrategy.EFFICIENCY: StrategyProfile(
        acquisition_bonus=-1,
        marketing_user_bonus=-1,
        stability_bonus=1,
        operating_cost_modifier=Decimal("-120.00"),
        burnout_relief=2,
        debt_reduction_bonus=1,
    ),
}


def get_strategy_profile(strategy: CompanyStrategy) -> StrategyProfile:
    """Return the configured modifier profile for a strategy."""

    return _STRATEGY_PROFILES[strategy]


def apply_set_company_strategy(
    company: Company,
    strategy: CompanyStrategy,
) -> StrategyActionSummary:
    """Change the active company strategy."""

    if company.strategy is strategy:
        raise ValueError(f"The company is already running a {strategy.value} strategy.")

    company.strategy = strategy
    return StrategyActionSummary(
        message=(
            f"Company strategy set to {strategy.value}. "
            "Future growth, cost, and execution rules will adapt immediately."
        )
    )
