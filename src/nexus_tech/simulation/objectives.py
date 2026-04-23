"""Scenario-specific objective progress helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import GameState, SalesDealStage, ScenarioObjectiveMetric


@dataclass(frozen=True)
class ScenarioObjectiveProgress:
    """Resolved progress for a scenario objective."""

    description: str
    metric: ScenarioObjectiveMetric
    current_value: int
    target_value: int

    @property
    def percent(self) -> int:
        if self.target_value <= 0:
            return 0
        return min(100, int((Decimal(self.current_value) / Decimal(self.target_value)) * 100))

    @property
    def complete(self) -> bool:
        return self.target_value > 0 and self.current_value >= self.target_value


def evaluate_scenario_objective(state: GameState) -> ScenarioObjectiveProgress:
    """Evaluate the content-defined scenario objective."""

    metric = state.scenario_objective_metric
    current_value = _current_metric_value(state, metric)
    return ScenarioObjectiveProgress(
        description=state.scenario_objective,
        metric=metric,
        current_value=current_value,
        target_value=state.scenario_objective_target,
    )


def _current_metric_value(state: GameState, metric: ScenarioObjectiveMetric) -> int:
    if metric is ScenarioObjectiveMetric.CASH:
        return max(0, int(state.company.cash_on_hand))
    if metric is ScenarioObjectiveMetric.USERS:
        return sum(product.user_count for product in state.products if product.is_active)
    if metric is ScenarioObjectiveMetric.REPUTATION:
        return state.company.reputation
    if metric is ScenarioObjectiveMetric.ACTIVE_PRODUCTS:
        return sum(1 for product in state.products if product.is_active)
    if metric is ScenarioObjectiveMetric.ENTERPRISE_USERS:
        return sum(
            product.user_count
            for product in state.products
            if product.is_active and product.target_segment.value == "enterprise"
        )
    if metric is ScenarioObjectiveMetric.ACTIVE_DEALS:
        return sum(
            1
            for deal in state.sales_deals
            if deal.stage not in {SalesDealStage.CLOSED_LOST, SalesDealStage.CLOSED_WON}
        )
    if metric is ScenarioObjectiveMetric.CLOSED_DEALS:
        return sum(1 for deal in state.sales_deals if deal.stage is SalesDealStage.CLOSED_WON)
    return 0
