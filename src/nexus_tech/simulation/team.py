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
    managed_headcount: int
    manager_headcount: int
    team_lead_count: int
    management_capacity: int
    management_layers: int
    max_span: int
    span_risk: int
    org_drag: int
    overloaded_manager_count: int
    overloaded_report_count: int
    high_succession_risk_count: int
    total_salary_cost: Decimal
    average_energy: int
    average_morale: int
    burned_out_count: int


@dataclass(frozen=True)
class OrgStructureSummary:
    """Management coverage and organization drag across the current roster."""

    manager_ids: tuple[UUID, ...]
    managed_headcount: int
    unmanaged_headcount: int
    manager_headcount: int
    team_lead_count: int
    management_capacity: int
    management_layers: int
    max_span: int
    span_risk: int
    org_drag: int
    overloaded_manager_count: int
    overloaded_report_count: int


@dataclass(frozen=True)
class OrgReorgSummary:
    """Summary of a team reorg action."""

    reassigned_reports: int
    unmanaged_before: int
    unmanaged_after: int
    overloaded_reports_before: int
    overloaded_reports_after: int
    message: str


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
        leadership_score=_calculate_leadership_score(role, seniority, trait),
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


def _calculate_leadership_score(
    role: EmployeeRole,
    seniority: Seniority,
    trait: CandidateTrait,
) -> int:
    leadership_score = 42
    if role is EmployeeRole.PRODUCT_MANAGER:
        leadership_score += 18
    if seniority is Seniority.MID:
        leadership_score += 6
    elif seniority is Seniority.SENIOR:
        leadership_score += 14
    if trait is CandidateTrait.FAST_LEARNER:
        leadership_score += 4
    elif trait is CandidateTrait.EXPENSIVE_EXPERT:
        leadership_score += 6
    elif trait is CandidateTrait.BURNOUT_RISK:
        leadership_score -= 4
    return clamp_int(leadership_score)


def is_eligible_manager(employee: Employee) -> bool:
    """Return whether an employee can manage others."""

    return (
        employee.role is EmployeeRole.PRODUCT_MANAGER
        or employee.seniority is Seniority.SENIOR
        or employee.is_team_lead
        or employee.leadership_score >= 68
    )


def calculate_manager_capacity(employee: Employee) -> int:
    """Return how many direct reports one employee can support."""

    if not is_eligible_manager(employee):
        return 0
    base_capacity = (
        BALANCE.management_product_manager_capacity
        if employee.role is EmployeeRole.PRODUCT_MANAGER
        else (
            BALANCE.management_team_lead_capacity
            if employee.is_team_lead
            else BALANCE.management_senior_capacity
        )
    )
    return base_capacity + (employee.leadership_score // BALANCE.management_leadership_divisor)


def sanitize_management_links(employees: list[Employee]) -> None:
    """Clear broken manager references after roster changes."""

    employee_ids = {employee.id for employee in employees}
    for employee in employees:
        if employee.manager_id == employee.id or employee.manager_id not in employee_ids:
            employee.manager_id = None


def calculate_org_structure(employees: list[Employee]) -> OrgStructureSummary:
    """Summarise manager coverage and org drag for the current roster."""

    sanitize_management_links(employees)
    manager_ids = tuple(employee.id for employee in employees if is_eligible_manager(employee))
    team_lead_count = sum(1 for employee in employees if employee.is_team_lead)
    management_capacity = sum(calculate_manager_capacity(employee) for employee in employees)
    report_counts = _build_manager_report_counts(employees)
    managed_headcount = sum(
        1
        for employee in employees
        if employee.manager_id is not None and employee.manager_id in manager_ids
    )
    unmanaged_headcount = max(0, len(employees) - len(manager_ids) - managed_headcount)
    overloaded_reports = sum(
        max(0, report_counts.get(employee.id, 0) - calculate_manager_capacity(employee))
        for employee in employees
        if employee.id in manager_ids
    )
    overloaded_manager_count = sum(
        1
        for employee in employees
        if employee.id in manager_ids
        and report_counts.get(employee.id, 0) > calculate_manager_capacity(employee)
    )
    management_layers = _calculate_management_layers(employees)
    max_span = max(report_counts.values(), default=0)
    span_risk = max(0, max_span - BALANCE.management_span_soft_cap)
    capacity_gap = max(0, unmanaged_headcount - BALANCE.management_org_drag_threshold)
    org_drag = (
        capacity_gap
        + max(0, len(employees) - len(manager_ids) - management_capacity)
        + overloaded_reports
        + max(
            0,
            management_layers - BALANCE.management_layer_drag_threshold,
        )
        * BALANCE.management_layer_drag_per_layer
        + span_risk
    )
    return OrgStructureSummary(
        manager_ids=manager_ids,
        managed_headcount=managed_headcount,
        unmanaged_headcount=unmanaged_headcount,
        manager_headcount=len(manager_ids),
        team_lead_count=team_lead_count,
        management_capacity=management_capacity,
        management_layers=management_layers,
        max_span=max_span,
        span_risk=span_risk,
        org_drag=max(0, org_drag),
        overloaded_manager_count=overloaded_manager_count,
        overloaded_report_count=max(0, overloaded_reports),
    )


def calculate_product_team_modifier(
    employees: list[Employee],
    product_id: UUID,
) -> ProductTeamModifier:
    """Aggregate assigned team effects for one product."""

    assigned_employees = [
        employee for employee in employees if employee.assigned_product_id == product_id
    ]
    org_structure = calculate_org_structure(employees)
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
    managed_assigned = sum(
        1
        for employee in assigned_employees
        if employee.manager_id is not None and employee.manager_id in org_structure.manager_ids
    )
    same_product_management = sum(
        1
        for employee in assigned_employees
        if employee.manager_id is not None
        and any(
            manager.id == employee.manager_id and manager.assigned_product_id == product_id
            for manager in employees
        )
    )
    manager_report_counts = _build_manager_report_counts(employees)
    overloaded_reports = sum(
        max(0, manager_report_counts.get(manager.id, 0) - calculate_manager_capacity(manager))
        for manager in employees
        if manager.assigned_product_id == product_id and is_eligible_manager(manager)
    )
    coordination_bonus += managed_assigned // BALANCE.management_coordination_bonus_per_managed_pair
    coordination_bonus += same_product_management // BALANCE.management_same_product_bonus_divisor
    coordination_bonus += sum(
        BALANCE.management_team_lead_coordination_bonus
        for employee in assigned_employees
        if employee.is_team_lead
    )
    coordination_bonus += sum(
        BALANCE.management_team_lead_overload_relief
        for employee in assigned_employees
        if employee.is_team_lead and employee.manager_id is not None
    )
    coordination_bonus -= (
        overloaded_reports // BALANCE.management_overload_coordination_penalty_divisor
    )
    coordination_bonus = max(0, coordination_bonus)

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

    org_structure = calculate_org_structure(employees)
    headcount = len(employees)
    assigned_headcount = sum(
        1 for employee in employees if employee.assigned_product_id is not None
    )
    total_salary_cost = sum((employee.salary for employee in employees), ZERO_MONEY)

    if not employees:
        return TeamCondition(
            headcount=0,
            assigned_headcount=0,
            managed_headcount=0,
            manager_headcount=0,
            team_lead_count=0,
            management_capacity=0,
            management_layers=0,
            max_span=0,
            span_risk=0,
            org_drag=0,
            overloaded_manager_count=0,
            overloaded_report_count=0,
            high_succession_risk_count=0,
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
    high_succession_risk_count = sum(
        1
        for employee in employees
        if employee.succession_risk >= BALANCE.management_succession_high_risk_threshold
    )
    return TeamCondition(
        headcount=headcount,
        assigned_headcount=assigned_headcount,
        managed_headcount=org_structure.managed_headcount,
        manager_headcount=org_structure.manager_headcount,
        team_lead_count=org_structure.team_lead_count,
        management_capacity=org_structure.management_capacity,
        management_layers=org_structure.management_layers,
        max_span=org_structure.max_span,
        span_risk=org_structure.span_risk,
        org_drag=org_structure.org_drag,
        overloaded_manager_count=org_structure.overloaded_manager_count,
        overloaded_report_count=org_structure.overloaded_report_count,
        high_succession_risk_count=high_succession_risk_count,
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


def appoint_team_lead(employees: list[Employee], employee_id: UUID) -> TeamActionSummary:
    """Promote one employee into a lightweight team-lead role."""

    employee = get_employee_by_id(employees, employee_id)
    if employee.is_team_lead:
        raise ValueError(f"{employee.full_name} is already a team lead.")
    if employee.assigned_product_id is None:
        raise ValueError("Team leads must be assigned to an active product first.")
    if employee.leadership_score < BALANCE.management_team_lead_leadership_threshold:
        raise ValueError(f"{employee.full_name} does not have enough leadership signal yet.")

    employee.is_team_lead = True
    employee.morale = clamp_int(employee.morale + 2)
    employee.performance_rating = clamp_int(employee.performance_rating + 1)
    return TeamActionSummary(message=f"Appointed {employee.full_name} as a team lead.")


def assign_manager(
    employees: list[Employee],
    *,
    report_id: UUID,
    manager_id: UUID,
) -> TeamActionSummary:
    """Assign one employee to a manager."""

    sanitize_management_links(employees)
    report = get_employee_by_id(employees, report_id)
    manager = get_employee_by_id(employees, manager_id)
    if report.id == manager.id:
        raise ValueError("An employee cannot manage themselves.")
    if not is_eligible_manager(manager):
        raise ValueError(f"{manager.full_name} is not eligible to manage other employees.")
    if _creates_manager_cycle(employees, report_id=report.id, manager_id=manager.id):
        raise ValueError("That reporting line would create a management cycle.")

    report.manager_id = manager.id
    return TeamActionSummary(message=f"{manager.full_name} now manages {report.full_name}.")


def clear_manager_assignment(
    employees: list[Employee],
    *,
    report_id: UUID,
) -> TeamActionSummary:
    """Remove one employee from their manager."""

    report = get_employee_by_id(employees, report_id)
    if report.manager_id is None:
        raise ValueError(f"{report.full_name} does not have a manager assigned.")
    report.manager_id = None
    return TeamActionSummary(message=f"Removed manager assignment for {report.full_name}.")


def clear_manager_links(employees: list[Employee], manager_id: UUID) -> int:
    """Remove manager references that point at one deleted employee."""

    cleared = 0
    for employee in employees:
        if employee.manager_id == manager_id:
            employee.manager_id = None
            cleared += 1
    return cleared


def run_org_reorg(employees: list[Employee]) -> OrgReorgSummary:
    """Rebuild reporting lines to reduce unmanaged work and overloaded managers."""

    sanitize_management_links(employees)
    managers = [employee for employee in employees if is_eligible_manager(employee)]
    reports = [employee for employee in employees if employee.id not in {m.id for m in managers}]
    if len(employees) < 2 or not reports:
        raise ValueError("The team is too small to justify a formal reorg.")
    if not managers:
        raise ValueError("No eligible managers are available for a reorg.")

    before = calculate_org_structure(employees)
    for report in reports:
        report.manager_id = None

    manager_loads = {manager.id: 0 for manager in managers}
    reassigned_reports = 0
    for report in sorted(
        reports,
        key=lambda employee: (
            employee.assigned_product_id is None,
            employee.role.value,
            -employee.productivity,
        ),
    ):
        manager = _pick_best_manager(report, managers, manager_loads)
        if manager is None:
            continue
        report.manager_id = manager.id
        manager_loads[manager.id] += 1
        reassigned_reports += 1

    after = calculate_org_structure(employees)
    return OrgReorgSummary(
        reassigned_reports=reassigned_reports,
        unmanaged_before=before.unmanaged_headcount,
        unmanaged_after=after.unmanaged_headcount,
        overloaded_reports_before=before.overloaded_report_count,
        overloaded_reports_after=after.overloaded_report_count,
        message=(
            f"Rebuilt reporting lines for {reassigned_reports} teammate(s). "
            f"Unmanaged {before.unmanaged_headcount}->{after.unmanaged_headcount}, "
            f"overloaded reports {before.overloaded_report_count}->{after.overloaded_report_count}."
        ),
    )


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

    org_structure = calculate_org_structure(employees)
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
        if employee.manager_id is None:
            energy_loss += BALANCE.management_unmanaged_energy_penalty
            morale_loss += BALANCE.management_unmanaged_morale_penalty
        energy_loss += org_structure.org_drag

        employee.energy = clamp_int(employee.energy - energy_loss)
        employee.morale = clamp_int(employee.morale - morale_loss)

        if employee.energy <= BALANCE.employee_burnout_energy_threshold:
            employee.morale = clamp_int(
                employee.morale - BALANCE.employee_burnout_morale_penalty,
            )

    update_succession_risk(employees)
    return calculate_team_condition(employees)


def get_employee_by_id(employees: list[Employee], employee_id: UUID | None) -> Employee:
    """Resolve a target employee by id."""

    if employee_id is None:
        raise ValueError("This action requires selecting an employee.")

    for employee in employees:
        if employee.id == employee_id:
            return employee

    raise ValueError("Selected employee was not found.")


def _build_manager_report_counts(employees: list[Employee]) -> dict[UUID, int]:
    report_counts: dict[UUID, int] = {}
    for employee in employees:
        if employee.manager_id is None:
            continue
        report_counts[employee.manager_id] = report_counts.get(employee.manager_id, 0) + 1
    return report_counts


def _calculate_management_layers(employees: list[Employee]) -> int:
    employee_map = {employee.id: employee for employee in employees}
    max_depth = 0
    for employee in employees:
        depth = 0
        visited: set[UUID] = {employee.id}
        current_manager_id = employee.manager_id
        while current_manager_id is not None and current_manager_id in employee_map:
            if current_manager_id in visited:
                depth += 1
                break
            visited.add(current_manager_id)
            depth += 1
            current_manager_id = employee_map[current_manager_id].manager_id
        max_depth = max(max_depth, depth)
    return max_depth


def _creates_manager_cycle(
    employees: list[Employee],
    *,
    report_id: UUID,
    manager_id: UUID,
) -> bool:
    employee_map = {employee.id: employee for employee in employees}
    visited: set[UUID] = {report_id}
    current_manager_id = manager_id
    while current_manager_id is not None:
        if current_manager_id in visited:
            return True
        visited.add(current_manager_id)
        current_manager = employee_map.get(current_manager_id)
        if current_manager is None:
            return False
        current_manager_id = current_manager.manager_id
    return False


def update_succession_risk(employees: list[Employee]) -> None:
    """Refresh succession pressure for managers and team leads."""

    report_counts = _build_manager_report_counts(employees)
    product_lead_depth: dict[UUID, int] = {}
    for employee in employees:
        if employee.assigned_product_id is None:
            continue
        if is_eligible_manager(employee):
            product_lead_depth[employee.assigned_product_id] = (
                product_lead_depth.get(employee.assigned_product_id, 0) + 1
            )

    for employee in employees:
        if not is_eligible_manager(employee):
            employee.succession_risk = 0
            continue

        direct_reports = report_counts.get(employee.id, 0)
        capacity = max(1, calculate_manager_capacity(employee))
        succession_risk = max(0, direct_reports - capacity)
        if employee.energy <= BALANCE.management_succession_energy_threshold:
            succession_risk += 3
        if employee.morale <= BALANCE.management_succession_morale_threshold:
            succession_risk += 2
        if employee.attrition_risk >= BALANCE.management_succession_attrition_threshold:
            succession_risk += 2
        if employee.assigned_product_id is not None and (
            product_lead_depth.get(employee.assigned_product_id, 0) >= 2
        ):
            succession_risk -= 2
        employee.succession_risk = clamp_int(succession_risk)


def _pick_best_manager(
    report: Employee,
    managers: list[Employee],
    manager_loads: dict[UUID, int],
) -> Employee | None:
    ranked_managers = sorted(
        managers,
        key=lambda manager: (
            report.assigned_product_id != manager.assigned_product_id,
            manager_loads[manager.id] >= calculate_manager_capacity(manager),
            manager_loads[manager.id],
            -manager.leadership_score,
        ),
    )
    return ranked_managers[0] if ranked_managers else None
