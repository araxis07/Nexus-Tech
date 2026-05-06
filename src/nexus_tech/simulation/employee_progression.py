"""Employee progression, performance, and attrition rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.constants import ZERO_MONEY
from nexus_tech.domain.models import Company, Employee, Seniority
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.randomness import RandomLike
from nexus_tech.simulation.support import clamp_int
from nexus_tech.simulation.team import (
    calculate_manager_capacity,
    calculate_org_structure,
    calculate_salary,
    is_eligible_manager,
    sanitize_management_links,
)


@dataclass(frozen=True)
class EmployeeProgressionSummary:
    """Summary of one explicit progression action."""

    message: str


@dataclass(frozen=True)
class EmployeeProgressionTurnSummary:
    """End-of-turn progression summary for UI and tests."""

    promotion_ready_count: int
    high_attrition_risk_count: int
    underperforming_count: int
    resigned_employees: tuple[str, ...]


_NEXT_SENIORITY = {
    Seniority.JUNIOR: Seniority.MID,
    Seniority.MID: Seniority.SENIOR,
}


def train_employee(company: Company, employee: Employee) -> EmployeeProgressionSummary:
    """Invest cash into one employee to improve readiness and output."""

    if company.cash_on_hand < BALANCE.employee_training_cost:
        raise ValueError("Not enough cash to fund training this turn.")

    company.cash_on_hand = quantize_money(company.cash_on_hand - BALANCE.employee_training_cost)
    employee.experience_points += BALANCE.employee_training_experience_gain
    employee.promotion_readiness = clamp_int(
        employee.promotion_readiness + BALANCE.employee_training_readiness_gain
    )
    employee.productivity = clamp_int(
        employee.productivity + BALANCE.employee_training_productivity_gain
    )
    employee.morale = clamp_int(employee.morale + BALANCE.employee_training_morale_gain)
    employee.attrition_risk = clamp_int(
        employee.attrition_risk - BALANCE.employee_training_attrition_relief
    )
    employee.performance_rating = clamp_int(
        employee.performance_rating + BALANCE.employee_training_performance_gain
    )
    employee.underperformance_streak = max(0, employee.underperformance_streak - 1)
    return EmployeeProgressionSummary(
        message=(
            f"Trained {employee.full_name}. Productivity +"
            f"{BALANCE.employee_training_productivity_gain}, "
            f"readiness +{BALANCE.employee_training_readiness_gain}, "
            f"cash -{BALANCE.employee_training_cost}."
        )
    )


def promote_employee(employee: Employee) -> EmployeeProgressionSummary:
    """Promote one employee to the next seniority band."""

    if employee.seniority is Seniority.SENIOR:
        raise ValueError(f"{employee.full_name} is already senior.")
    if employee.promotion_readiness < BALANCE.employee_promotion_readiness_threshold:
        raise ValueError(f"{employee.full_name} is not ready for promotion yet.")

    next_seniority = _NEXT_SENIORITY[employee.seniority]
    previous_seniority = employee.seniority
    employee.seniority = next_seniority
    employee.salary = quantize_money(
        employee.salary * BALANCE.employee_promotion_salary_multiplier[next_seniority.value]
    )
    employee.productivity = clamp_int(
        employee.productivity + BALANCE.employee_promotion_productivity_gain[next_seniority.value]
    )
    employee.morale = clamp_int(employee.morale + BALANCE.employee_promotion_morale_gain)
    employee.promotion_readiness = BALANCE.employee_promotion_readiness_reset
    employee.attrition_risk = clamp_int(
        employee.attrition_risk - BALANCE.employee_promotion_attrition_relief
    )
    employee.performance_rating = clamp_int(
        employee.performance_rating + BALANCE.employee_promotion_performance_gain
    )
    employee.leadership_score = clamp_int(
        employee.leadership_score + BALANCE.employee_promotion_leadership_gain[next_seniority.value]
    )
    employee.underperformance_streak = 0
    return EmployeeProgressionSummary(
        message=(
            f"Promoted {employee.full_name} from {previous_seniority.value} "
            f"to {next_seniority.value}. Salary burn increased to {employee.salary}."
        )
    )


def run_comp_review(company: Company, employee: Employee) -> EmployeeProgressionSummary:
    """Raise compensation to reduce attrition and reinforce top performers."""

    benchmark_salary = quantize_money(
        calculate_salary(employee.role, employee.seniority)
        * BALANCE.employee_comp_review_salary_ratio_target
    )
    target_salary = benchmark_salary
    if employee.salary >= benchmark_salary:
        target_salary = quantize_money(employee.salary + BALANCE.employee_comp_review_min_raise)
    additional_burn = max(ZERO_MONEY, quantize_money(target_salary - employee.salary))
    if company.cash_on_hand - additional_burn < BALANCE.employee_comp_review_min_cash_buffer:
        raise ValueError("Not enough cash buffer to commit to a compensation review safely.")

    employee.salary = target_salary
    employee.morale = clamp_int(employee.morale + BALANCE.employee_comp_review_morale_gain)
    employee.attrition_risk = clamp_int(
        employee.attrition_risk - BALANCE.employee_comp_review_attrition_relief
    )
    employee.performance_rating = clamp_int(
        employee.performance_rating + BALANCE.employee_comp_review_performance_gain
    )
    if is_eligible_manager(employee):
        employee.succession_risk = clamp_int(
            employee.succession_risk - BALANCE.management_comp_review_succession_relief
        )
    employee.underperformance_streak = max(0, employee.underperformance_streak - 1)
    return EmployeeProgressionSummary(
        message=(
            f"Ran a compensation review for {employee.full_name}. "
            f"Recurring salary +{additional_burn} to {employee.salary}."
        )
    )


def apply_end_of_turn_employee_progression(
    employees: list[Employee],
    *,
    net_cash_flow: Decimal,
    burnout_relief: int = 0,
    rng: RandomLike | None = None,
) -> EmployeeProgressionTurnSummary:
    """Advance progression readiness, performance, and attrition pressure."""

    org_structure = calculate_org_structure(employees)
    employee_map = {employee.id: employee for employee in employees}
    manager_report_counts: dict = {}
    for employee in employees:
        if employee.manager_id is None:
            continue
        manager_report_counts[employee.manager_id] = (
            manager_report_counts.get(employee.manager_id, 0) + 1
        )

    promotion_ready_count = 0
    high_attrition_risk_count = 0
    underperforming_count = 0
    resigned_employees: list[str] = []
    retained_employees: list[Employee] = []

    for employee in employees:
        employee.tenure_turns += 1
        readiness_gain = (
            BALANCE.employee_assigned_experience_gain
            if employee.assigned_product_id is not None
            else BALANCE.employee_unassigned_experience_gain
        )
        employee.experience_points += readiness_gain
        if employee.energy >= BALANCE.employee_progression_energy_threshold:
            employee.promotion_readiness = clamp_int(
                employee.promotion_readiness + readiness_gain // 2
            )

        _apply_performance_drift(employee)

        if employee.morale <= BALANCE.employee_low_morale_threshold:
            employee.attrition_risk = clamp_int(
                employee.attrition_risk + BALANCE.employee_attrition_morale_risk_gain
            )
        if employee.energy <= BALANCE.employee_burnout_energy_threshold:
            employee.attrition_risk = clamp_int(
                employee.attrition_risk + BALANCE.employee_attrition_energy_risk_gain
            )
        if net_cash_flow < ZERO_MONEY:
            employee.attrition_risk = clamp_int(
                employee.attrition_risk + BALANCE.employee_attrition_negative_cash_flow_risk_gain
            )
        employee.attrition_risk = clamp_int(employee.attrition_risk - burnout_relief)
        if (
            employee.morale >= BALANCE.employee_performance_morale_bonus_threshold
            and employee.energy >= BALANCE.employee_performance_energy_bonus_threshold
        ):
            employee.attrition_risk = clamp_int(
                employee.attrition_risk - BALANCE.employee_attrition_recovery_relief
            )
        if employee.manager_id is not None:
            employee.attrition_risk = clamp_int(
                employee.attrition_risk - BALANCE.management_attrition_relief
            )
        elif employee.assigned_product_id is not None and org_structure.unmanaged_headcount > 0:
            employee.attrition_risk = clamp_int(
                employee.attrition_risk + BALANCE.management_unmanaged_attrition_gain
            )

        manager = employee_map.get(employee.manager_id)
        if manager is not None:
            overload = max(
                0,
                manager_report_counts.get(manager.id, 0) - calculate_manager_capacity(manager),
            )
            if overload > 0:
                employee.attrition_risk = clamp_int(
                    employee.attrition_risk + BALANCE.management_overload_attrition_gain
                )
            if manager.succession_risk >= BALANCE.management_succession_high_risk_threshold:
                employee.attrition_risk = clamp_int(
                    employee.attrition_risk
                    + BALANCE.management_succession_blind_spot_attrition_gain
                )

        if is_eligible_manager(employee):
            direct_reports = manager_report_counts.get(employee.id, 0)
            overload = max(0, direct_reports - calculate_manager_capacity(employee))
            if overload > 0:
                employee.attrition_risk = clamp_int(
                    employee.attrition_risk
                    + BALANCE.management_manager_overload_attrition_gain
                    + (
                        org_structure.span_risk
                        // BALANCE.management_span_risk_attrition_gain_divisor
                    )
                )
                employee.performance_rating = clamp_int(
                    employee.performance_rating
                    - BALANCE.management_manager_overload_performance_loss
                )

        if org_structure.org_drag > BALANCE.management_org_drag_threshold:
            employee.attrition_risk = clamp_int(
                employee.attrition_risk
                + (org_structure.org_drag // BALANCE.employee_org_drag_attrition_gain_divisor)
            )
            employee.performance_rating = clamp_int(
                employee.performance_rating
                - (org_structure.org_drag // BALANCE.employee_org_drag_performance_loss_divisor)
            )
            employee.morale = clamp_int(
                employee.morale
                - (org_structure.org_drag // BALANCE.employee_org_drag_morale_loss_divisor)
            )

        if employee.performance_rating <= BALANCE.employee_performance_low_threshold:
            employee.underperformance_streak += 1
            underperforming_count += 1
        else:
            employee.underperformance_streak = max(0, employee.underperformance_streak - 1)
        _apply_career_pressure(employee)

        if _should_resign(employee, rng):
            resigned_employees.append(employee.full_name)
            continue

        retained_employees.append(employee)
        if employee.promotion_readiness >= BALANCE.employee_promotion_readiness_threshold:
            promotion_ready_count += 1
        if employee.attrition_risk >= BALANCE.employee_high_attrition_risk_threshold:
            high_attrition_risk_count += 1

    employees[:] = retained_employees
    sanitize_management_links(employees)

    return EmployeeProgressionTurnSummary(
        promotion_ready_count=promotion_ready_count,
        high_attrition_risk_count=high_attrition_risk_count,
        underperforming_count=underperforming_count,
        resigned_employees=tuple(resigned_employees),
    )


def _apply_performance_drift(employee: Employee) -> None:
    performance_delta = 0
    if (
        employee.energy >= BALANCE.employee_performance_energy_bonus_threshold
        and employee.morale >= BALANCE.employee_performance_morale_bonus_threshold
    ):
        performance_delta += BALANCE.employee_performance_gain
    if employee.energy <= BALANCE.employee_burnout_energy_threshold:
        performance_delta -= BALANCE.employee_performance_loss
    if employee.morale <= BALANCE.employee_low_morale_threshold:
        performance_delta -= BALANCE.employee_performance_loss
    if employee.assigned_product_id is not None and performance_delta >= 0:
        performance_delta += BALANCE.employee_performance_recovery_gain
    employee.performance_rating = clamp_int(employee.performance_rating + performance_delta)


def _apply_career_pressure(employee: Employee) -> None:
    benchmark_salary = calculate_salary(employee.role, employee.seniority)
    under_market = employee.salary < quantize_money(
        benchmark_salary * BALANCE.employee_compensation_pressure_salary_ratio_floor
    )

    if (
        employee.promotion_readiness >= BALANCE.employee_promotion_readiness_threshold
        and employee.performance_rating >= BALANCE.employee_performance_good_threshold
        and employee.tenure_turns >= BALANCE.employee_promotion_pressure_tenure_threshold
    ):
        employee.attrition_risk = clamp_int(
            employee.attrition_risk + BALANCE.employee_promotion_pressure_attrition_gain
        )
        employee.morale = clamp_int(
            employee.morale - BALANCE.employee_promotion_pressure_morale_loss
        )

    if (
        under_market
        and employee.performance_rating >= BALANCE.employee_performance_good_threshold
        and employee.tenure_turns >= BALANCE.employee_compensation_pressure_tenure_threshold
    ):
        employee.attrition_risk = clamp_int(
            employee.attrition_risk + BALANCE.employee_compensation_pressure_attrition_gain
        )
        employee.morale = clamp_int(
            employee.morale - BALANCE.employee_compensation_pressure_morale_loss
        )

    if employee.underperformance_streak >= BALANCE.employee_underperformance_streak_warning:
        employee.attrition_risk = clamp_int(
            employee.attrition_risk + BALANCE.employee_underperformance_attrition_gain
        )
        employee.morale = clamp_int(employee.morale - BALANCE.employee_underperformance_morale_loss)


def _should_resign(employee: Employee, rng: RandomLike | None) -> bool:
    if employee.attrition_risk < BALANCE.employee_resignation_attrition_threshold:
        return False
    if employee.morale > BALANCE.employee_resignation_morale_threshold:
        return False
    if employee.energy > BALANCE.employee_resignation_energy_threshold:
        return False

    resignation_chance = clamp_int(
        BALANCE.employee_resignation_chance_floor
        + (employee.attrition_risk - BALANCE.employee_resignation_attrition_threshold)
        // BALANCE.employee_resignation_attrition_weight_divisor
        + max(0, employee.underperformance_streak) * BALANCE.employee_resignation_streak_bonus,
        0,
        100,
    )
    if rng is None:
        return resignation_chance >= 100
    return rng.randint(1, 100) <= resignation_chance
