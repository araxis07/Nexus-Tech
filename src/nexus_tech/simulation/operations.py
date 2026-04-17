"""Operational load and support-pressure rules for later-stage company runs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from nexus_tech.domain.constants import ZERO_MONEY
from nexus_tech.domain.models import Employee, EmployeeRole, GameState, Product
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.support import clamp_int
from nexus_tech.simulation.team import calculate_product_team_modifier


@dataclass(frozen=True)
class ProductOperationsRisk:
    """Operational burden carried by a single product."""

    product_id: UUID
    product_name: str
    load: int
    capacity: int
    overload: int


@dataclass(frozen=True)
class OperationsSummary:
    """Company-wide support and coordination pressure snapshot."""

    total_load: int
    total_capacity: int
    overload: int
    added_cost: Decimal
    team_energy_penalty: int
    team_morale_penalty: int
    reputation_delta: int
    product_risks: tuple[ProductOperationsRisk, ...]
    summary: str


def calculate_operations_summary(
    products: list[Product],
    employees: list[Employee],
    *,
    current_turn: int,
) -> OperationsSummary:
    """Estimate operational pressure from support, complexity, and coordination."""

    active_products = [product for product in products if product.is_active]
    if not active_products:
        return OperationsSummary(
            total_load=0,
            total_capacity=0,
            overload=0,
            added_cost=ZERO_MONEY,
            team_energy_penalty=0,
            team_morale_penalty=0,
            reputation_delta=0,
            product_risks=(),
            summary="No active operations load.",
        )

    product_risks = tuple(
        _calculate_product_operations_risk(product, products, employees)
        for product in active_products
    )
    portfolio_load = sum(risk.load for risk in product_risks)
    portfolio_capacity = sum(risk.capacity for risk in product_risks)

    company_overhead = (
        len(active_products) * BALANCE.operations_active_product_overhead
        + max(0, len(active_products) - 2)
        + max(0, current_turn - BALANCE.operations_late_turn_threshold)
        // BALANCE.operations_turn_load_divisor
    )
    company_capacity = _calculate_company_operations_capacity(employees)
    total_load = portfolio_load + company_overhead
    total_capacity = portfolio_capacity + company_capacity
    overload = max(0, total_load - total_capacity)

    if overload == 0:
        summary = "Operational load is under control."
    elif overload >= BALANCE.operations_severe_overload_threshold:
        summary = "Support and coordination are straining the company."
    elif overload >= BALANCE.operations_moderate_overload_threshold:
        summary = "Operations pressure is starting to tax delivery."
    else:
        summary = "Operations pressure is visible but still manageable."

    team_energy_penalty = min(
        BALANCE.operations_max_energy_penalty,
        0 if overload == 0 else 1 + (overload // BALANCE.operations_energy_penalty_divisor),
    )
    team_morale_penalty = min(
        BALANCE.operations_max_morale_penalty,
        0 if overload == 0 else 1 + (overload // BALANCE.operations_morale_penalty_divisor),
    )
    reputation_delta = (
        -1 if overload >= BALANCE.operations_reputation_penalty_threshold else 0
    )
    added_cost = quantize_money(
        Decimal(overload) * BALANCE.operations_overload_cost_per_point
    )

    return OperationsSummary(
        total_load=total_load,
        total_capacity=total_capacity,
        overload=overload,
        added_cost=added_cost,
        team_energy_penalty=team_energy_penalty,
        team_morale_penalty=team_morale_penalty,
        reputation_delta=reputation_delta,
        product_risks=product_risks,
        summary=summary,
    )


def apply_end_of_turn_operations(
    state: GameState,
    *,
    current_turn: int,
) -> OperationsSummary:
    """Apply light operational strain to products, morale, and reputation."""

    summary = calculate_operations_summary(
        state.products,
        state.employees,
        current_turn=current_turn,
    )
    if summary.overload == 0:
        return summary

    overloaded_product_ids = {
        risk.product_id
        for risk in sorted(
            summary.product_risks,
            key=lambda risk: (risk.overload, risk.load),
            reverse=True,
        )[: BALANCE.operations_affected_product_limit]
        if risk.overload > 0
    }

    for employee in state.employees:
        if employee.assigned_product_id is None and summary.overload < 2:
            continue
        employee.energy = clamp_int(employee.energy - summary.team_energy_penalty)
        employee.morale = clamp_int(employee.morale - summary.team_morale_penalty)

    for product in state.products:
        if product.id not in overloaded_product_ids:
            continue
        if summary.overload >= BALANCE.operations_bug_penalty_threshold:
            product.bug_level = clamp_int(
                product.bug_level + BALANCE.operations_bug_penalty,
            )
        if summary.overload >= BALANCE.operations_quality_penalty_threshold:
            product.quality = clamp_int(
                product.quality - BALANCE.operations_quality_penalty,
            )

    if summary.reputation_delta != 0:
        state.company.reputation = clamp_int(
            state.company.reputation + summary.reputation_delta,
        )

    return summary


def _calculate_product_operations_risk(
    product: Product,
    products: list[Product],
    employees: list[Employee],
) -> ProductOperationsRisk:
    """Estimate support and execution load for one product."""

    team_modifier = calculate_product_team_modifier(employees, product.id)
    load = (
        max(1, product.user_count // BALANCE.operations_user_load_divisor)
        + (product.bug_level // BALANCE.operations_bug_load_divisor)
        + (product.technical_debt // BALANCE.operations_debt_load_divisor)
        + max(0, product.feature_count - 2)
        // BALANCE.operations_feature_load_divisor
        + BALANCE.operations_segment_load_bonus[product.target_segment.value]
        + BALANCE.operations_stage_load_bonus[product.lifecycle_stage.value]
    )
    if product.user_count >= BALANCE.operations_large_user_base_threshold:
        load += 1
    capacity = max(
        1,
        (team_modifier.assigned_headcount * BALANCE.operations_assigned_capacity_per_person)
        + team_modifier.coordination_bonus
        + team_modifier.stability_bonus
        + (team_modifier.market_fit_bonus // 2)
        + (team_modifier.acquisition_bonus // 2),
    )

    adjacent_count = sum(
        1
        for candidate in products
        if candidate.is_active
        and candidate.id != product.id
        and candidate.target_segment is product.target_segment
    )
    overload = max(
        0,
        load
        + (
            adjacent_count * BALANCE.operations_same_segment_overlap_penalty
        )
        - capacity,
    )
    return ProductOperationsRisk(
        product_id=product.id,
        product_name=product.name,
        load=load,
        capacity=capacity,
        overload=overload,
    )


def _calculate_company_operations_capacity(employees: list[Employee]) -> int:
    """Estimate shared operational relief from the broader team."""

    if not employees:
        return 0

    unassigned_count = sum(1 for employee in employees if employee.assigned_product_id is None)
    pm_count = sum(1 for employee in employees if employee.role is EmployeeRole.PRODUCT_MANAGER)
    designer_count = sum(1 for employee in employees if employee.role is EmployeeRole.DESIGNER)
    marketer_count = sum(1 for employee in employees if employee.role is EmployeeRole.MARKETER)
    return (
        len(employees) * BALANCE.operations_company_headcount_capacity
        + (unassigned_count * BALANCE.operations_unassigned_capacity_per_person)
        + (pm_count * BALANCE.operations_product_manager_capacity_bonus)
        + (designer_count * BALANCE.operations_designer_capacity_bonus)
        + (marketer_count * BALANCE.operations_marketer_capacity_bonus)
    )
