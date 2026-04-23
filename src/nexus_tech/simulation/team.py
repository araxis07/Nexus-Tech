"""Employee and team simulation rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from nexus_tech.domain.constants import ZERO_MONEY
from nexus_tech.domain.models import (
    CandidateTrait,
    CompanyStrategy,
    Employee,
    EmployeeRole,
    Product,
    Seniority,
)
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.strategy import get_strategy_profile
from nexus_tech.simulation.support import clamp_int


@dataclass(frozen=True)
class TeamActionSummary:
    """Summary of a team management action."""

    message: str


@dataclass(frozen=True)
class ProductTeamModifier:
    """Role contributions assigned to a single product."""

    assigned_headcount: int = 0
    engineer_power: int = 0
    designer_power: int = 0
    marketer_power: int = 0
    product_manager_power: int = 0
    build_speed_bonus: int = 0
    stability_bonus: int = 0
    market_fit_bonus: int = 0
    acquisition_bonus: int = 0
    reputation_bonus: int = 0
    debt_reduction_bonus: int = 0
    coordination_bonus: int = 0
    burnout_protection: int = 0


@dataclass(frozen=True)
class TeamCondition:
    """High-level team condition for UI and turn summaries."""

    headcount: int
    assigned_headcount: int
    total_salary_cost: Decimal
    average_energy: int
    average_morale: int
    burned_out_count: int


def create_employee(
    full_name: str,
    role: EmployeeRole,
    seniority: Seniority,
    specialization: str | None,
    existing_employees: list[Employee],
    trait: CandidateTrait = CandidateTrait.STEADY_OPERATOR,
) -> Employee:
    """Validate and create a new employee."""

    normalized_name = full_name.strip()
    if not normalized_name:
        raise ValueError("Employee name cannot be empty.")

    existing_names = {employee.full_name.casefold() for employee in existing_employees}
    if normalized_name.casefold() in existing_names:
        raise ValueError("An employee with that name already exists.")

    normalized_specialization = (specialization or "").strip()
    if not normalized_specialization:
        normalized_specialization = BALANCE.employee_default_specializations[role.value]

    salary = calculate_trait_salary(calculate_salary(role, seniority), trait)
    productivity = calculate_trait_productivity(calculate_base_productivity(role, seniority), trait)
    return Employee(
        full_name=normalized_name,
        role=role,
        seniority=seniority,
        salary=salary,
        energy=BALANCE.employee_starting_energy,
        morale=BALANCE.employee_starting_morale,
        productivity=productivity,
        specialization=normalized_specialization,
        trait=trait,
        performance_rating=BALANCE.employee_starting_performance_rating,
    )


def calculate_salary(role: EmployeeRole, seniority: Seniority) -> Decimal:
    """Calculate recurring salary cost for one employee."""

    role_salary = BALANCE.employee_role_base_salary[role.value]
    multiplier = BALANCE.employee_seniority_salary_multiplier[seniority.value]
    return quantize_money(role_salary * multiplier)


def calculate_base_productivity(role: EmployeeRole, seniority: Seniority) -> int:
    """Calculate starting productivity for one employee."""

    base_productivity = BALANCE.employee_role_base_productivity[role.value]
    bonus = BALANCE.employee_seniority_productivity_bonus[seniority.value]
    return clamp_int(base_productivity + bonus, minimum=1)


def calculate_trait_salary(base_salary: Decimal, trait: CandidateTrait) -> Decimal:
    """Adjust salary by hiring-market trait."""

    multiplier = BALANCE.employee_trait_salary_multiplier[trait.value]
    return quantize_money(base_salary * multiplier)


def calculate_trait_productivity(base_productivity: int, trait: CandidateTrait) -> int:
    """Adjust base productivity by hiring-market trait."""

    return clamp_int(base_productivity + BALANCE.employee_trait_productivity_bonus[trait.value])


def calculate_effective_productivity(employee: Employee) -> int:
    """Effective productivity after morale and energy modifiers."""

    energy_factor = Decimal("0.50") + (Decimal(employee.energy) / Decimal("200"))
    morale_factor = Decimal("0.50") + (Decimal(employee.morale) / Decimal("200"))
    attrition_factor = Decimal("1.00") - (Decimal(employee.attrition_risk) / Decimal("300"))
    performance_factor = Decimal("0.70") + (Decimal(employee.performance_rating) / Decimal("250"))
    effective = (
        Decimal(employee.productivity)
        * energy_factor
        * morale_factor
        * attrition_factor
        * performance_factor
    )
    return clamp_int(int(effective.to_integral_value()))


def calculate_product_team_modifier(
    employees: list[Employee],
    product_id: UUID,
) -> ProductTeamModifier:
    """Aggregate assigned team effects for one product."""

    assigned_employees = [
        employee for employee in employees if employee.assigned_product_id == product_id
    ]
    engineer_power = sum(
        calculate_effective_productivity(employee)
        for employee in assigned_employees
        if employee.role is EmployeeRole.ENGINEER
    )
    designer_power = sum(
        calculate_effective_productivity(employee)
        for employee in assigned_employees
        if employee.role is EmployeeRole.DESIGNER
    )
    marketer_power = sum(
        calculate_effective_productivity(employee)
        for employee in assigned_employees
        if employee.role is EmployeeRole.MARKETER
    )
    product_manager_power = sum(
        calculate_effective_productivity(employee)
        for employee in assigned_employees
        if employee.role is EmployeeRole.PRODUCT_MANAGER
    )

    coordination_bonus = (
        product_manager_power // BALANCE.team_coordination_bonus_divisor
        if len(assigned_employees) >= 2
        else product_manager_power // (BALANCE.team_coordination_bonus_divisor + 12)
    )

    return ProductTeamModifier(
        assigned_headcount=len(assigned_employees),
        engineer_power=engineer_power,
        designer_power=designer_power,
        marketer_power=marketer_power,
        product_manager_power=product_manager_power,
        build_speed_bonus=(engineer_power // BALANCE.team_build_bonus_divisor) + coordination_bonus,
        stability_bonus=(engineer_power // BALANCE.team_stability_bonus_divisor)
        + coordination_bonus,
        market_fit_bonus=(designer_power // BALANCE.team_market_fit_bonus_divisor)
        + (coordination_bonus // 2),
        acquisition_bonus=(marketer_power // BALANCE.team_acquisition_bonus_divisor)
        + (coordination_bonus // 2),
        reputation_bonus=designer_power // BALANCE.team_reputation_bonus_divisor,
        debt_reduction_bonus=(engineer_power // BALANCE.team_debt_bonus_divisor)
        + (coordination_bonus // 2),
        coordination_bonus=coordination_bonus,
        burnout_protection=product_manager_power // BALANCE.team_burnout_protection_divisor,
    )


def calculate_team_condition(employees: list[Employee]) -> TeamCondition:
    """Compute headcount, salary burden, and average team condition."""

    headcount = len(employees)
    assigned_headcount = sum(
        1 for employee in employees if employee.assigned_product_id is not None
    )
    total_salary_cost = sum((employee.salary for employee in employees), ZERO_MONEY)

    if not employees:
        return TeamCondition(
            headcount=0,
            assigned_headcount=0,
            total_salary_cost=ZERO_MONEY,
            average_energy=0,
            average_morale=0,
            burned_out_count=0,
        )

    average_energy = sum(employee.energy for employee in employees) // headcount
    average_morale = sum(employee.morale for employee in employees) // headcount
    burned_out_count = sum(
        1 for employee in employees if employee.energy <= BALANCE.employee_burnout_energy_threshold
    )
    return TeamCondition(
        headcount=headcount,
        assigned_headcount=assigned_headcount,
        total_salary_cost=quantize_money(total_salary_cost),
        average_energy=average_energy,
        average_morale=average_morale,
        burned_out_count=burned_out_count,
    )


def apply_rest_team(employees: list[Employee]) -> TeamActionSummary:
    """Recover energy and morale for the entire team."""

    if not employees:
        raise ValueError("You do not have a team to rest yet.")

    for employee in employees:
        employee.energy = clamp_int(
            employee.energy + BALANCE.employee_rest_energy_gain,
        )
        employee.morale = clamp_int(
            employee.morale + BALANCE.employee_rest_morale_gain,
        )

    condition = calculate_team_condition(employees)
    return TeamActionSummary(
        message=(
            f"The team took a breather. Avg energy {condition.average_energy}, "
            f"avg morale {condition.average_morale}."
        )
    )


def assign_employee(employee: Employee, product_id: UUID) -> TeamActionSummary:
    """Assign an employee to a product."""

    employee.assigned_product_id = product_id
    return TeamActionSummary(message=f"Assigned {employee.full_name} to the selected product.")


def unassign_employee(employee: Employee) -> TeamActionSummary:
    """Remove an employee from product work."""

    employee.assigned_product_id = None
    return TeamActionSummary(message=f"Unassigned {employee.full_name} from product work.")


def unassign_employees_from_product(employees: list[Employee], product_id: UUID) -> int:
    """Remove all product assignments for a sunset product."""

    unassigned_count = 0
    for employee in employees:
        if employee.assigned_product_id == product_id:
            employee.assigned_product_id = None
            unassigned_count += 1
    return unassigned_count


def apply_end_of_turn_team_drift(
    employees: list[Employee],
    products: list[Product],
    net_cash_flow: Decimal,
    company_strategy: CompanyStrategy,
    *,
    budget_burnout_modifier: int = 0,
    coordination_burnout_modifier: int = 0,
) -> TeamCondition:
    """Apply burnout and recovery after the turn resolves."""

    product_map = {product.id: product for product in products}
    strategy_profile = get_strategy_profile(company_strategy)

    for employee in employees:
        if employee.assigned_product_id is None:
            employee.energy = clamp_int(
                employee.energy + BALANCE.employee_unassigned_energy_recovery,
            )
            employee.morale = clamp_int(
                employee.morale + BALANCE.employee_unassigned_morale_recovery,
            )
            continue

        product = product_map.get(employee.assigned_product_id)
        pressure = 0
        burnout_protection = 0
        if product is not None:
            pressure += product.bug_level // BALANCE.employee_pressure_bug_divisor
            pressure += product.technical_debt // BALANCE.employee_pressure_debt_divisor
            burnout_protection = calculate_product_team_modifier(
                employees,
                product.id,
            ).burnout_protection

        energy_loss = max(
            1,
            BALANCE.employee_assigned_energy_loss
            + pressure
            + budget_burnout_modifier
            + coordination_burnout_modifier
            - burnout_protection
            - strategy_profile.burnout_relief,
        )
        morale_loss = BALANCE.employee_assigned_morale_loss
        if net_cash_flow < ZERO_MONEY:
            morale_loss += BALANCE.employee_negative_cash_flow_morale_penalty

        employee.energy = clamp_int(employee.energy - energy_loss)
        employee.morale = clamp_int(employee.morale - morale_loss)

        if employee.energy <= BALANCE.employee_burnout_energy_threshold:
            employee.morale = clamp_int(
                employee.morale - BALANCE.employee_burnout_morale_penalty,
            )

    return calculate_team_condition(employees)


def get_employee_by_id(employees: list[Employee], employee_id: UUID | None) -> Employee:
    """Resolve a target employee by id."""

    if employee_id is None:
        raise ValueError("This action requires selecting an employee.")

    for employee in employees:
        if employee.id == employee_id:
            return employee

    raise ValueError("Selected employee was not found.")
