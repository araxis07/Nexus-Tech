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
    employee.underperformance_streak = 0
    return EmployeeProgressionSummary(
        message=(
            f"Promoted {employee.full_name} from {previous_seniority.value} "
            f"to {next_seniority.value}. Salary burn increased to {employee.salary}."
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

        if employee.performance_rating <= BALANCE.employee_performance_low_threshold:
            employee.underperformance_streak += 1
            underperforming_count += 1
        else:
            employee.underperformance_streak = max(0, employee.underperformance_streak - 1)

        if _should_resign(employee, rng):
            resigned_employees.append(employee.full_name)
            continue

        retained_employees.append(employee)
        if employee.promotion_readiness >= BALANCE.employee_promotion_readiness_threshold:
            promotion_ready_count += 1
        if employee.attrition_risk >= BALANCE.employee_high_attrition_risk_threshold:
            high_attrition_risk_count += 1

    employees[:] = retained_employees

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
