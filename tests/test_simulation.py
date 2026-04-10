from __future__ import annotations

from decimal import Decimal

import pytest

from nexus_tech.domain.models import (
    Company,
    Employee,
    EmployeeRole,
    GameState,
    LifecycleStage,
    Product,
    Seniority,
    TurnAction,
)
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.economy import (
    calculate_total_operating_cost,
    calculate_total_revenue,
    calculate_total_salary_cost,
)
from nexus_tech.simulation.engine import ActionContext, apply_action, create_new_game, resolve_turn
from nexus_tech.simulation.growth import calculate_churned_users
from nexus_tech.simulation.product_progression import calculate_delivery_penalty
from nexus_tech.simulation.team import calculate_effective_productivity


class FixedRandom:
    def __init__(self, value: int) -> None:
        self.value = value

    def randint(self, start: int, end: int) -> int:
        return self.value


def make_product(
    name: str,
    *,
    lifecycle_stage: LifecycleStage = LifecycleStage.GROWTH,
    quality: int = 58,
    bug_level: int = 18,
    market_fit: int = 52,
    technical_debt: int = 14,
    user_count: int = 35,
    revenue_per_user: Decimal = Decimal("30.00"),
    feature_count: int = 1,
    maintenance_cost: Decimal = Decimal("260.00"),
    acquisition_rate: Decimal = Decimal("0.0600"),
    churn_rate: Decimal = Decimal("0.0500"),
    is_active: bool = True,
) -> Product:
    return Product(
        name=name,
        lifecycle_stage=lifecycle_stage,
        quality=quality,
        bug_level=bug_level,
        market_fit=market_fit,
        technical_debt=technical_debt,
        user_count=user_count,
        revenue_per_user=revenue_per_user,
        feature_count=feature_count,
        maintenance_cost=maintenance_cost,
        acquisition_rate=acquisition_rate,
        churn_rate=churn_rate,
        is_active=is_active,
    )


def make_employee(
    full_name: str,
    role: EmployeeRole,
    *,
    seniority: Seniority = Seniority.MID,
    salary: Decimal | None = None,
    energy: int = 82,
    morale: int = 76,
    productivity: int | None = None,
    specialization: str = "generalist",
    assigned_product_id=None,
) -> Employee:
    return Employee(
        full_name=full_name,
        role=role,
        seniority=seniority,
        salary=salary or Decimal("800.00"),
        energy=energy,
        morale=morale,
        productivity=productivity or 64,
        specialization=specialization,
        assigned_product_id=assigned_product_id,
    )


def make_state(
    *products: Product,
    employees: list[Employee] | None = None,
    cash_on_hand: Decimal = Decimal("6000.00"),
) -> GameState:
    return GameState(
        company=Company(name="NEXUS TECH", cash_on_hand=cash_on_hand, reputation=50),
        products=list(products),
        employees=employees or [],
        action_points_remaining=BALANCE.actions_per_turn,
    )


def test_multi_product_revenue_aggregates_only_active_products() -> None:
    state = make_state(
        make_product("Core", user_count=20, revenue_per_user=Decimal("25.00")),
        make_product("Cloud", user_count=10, revenue_per_user=Decimal("40.00")),
        make_product(
            "Legacy",
            user_count=99,
            revenue_per_user=Decimal("99.00"),
            is_active=False,
        ),
    )

    revenue = calculate_total_revenue(state.products)

    assert revenue == Decimal("900.00")


def test_churn_behavior_is_higher_for_bad_product_health() -> None:
    bad_product = make_product(
        "Buggy",
        lifecycle_stage=LifecycleStage.DECLINING,
        quality=25,
        bug_level=65,
        market_fit=20,
        technical_debt=70,
        user_count=100,
        churn_rate=Decimal("0.1200"),
    )
    healthy_product = make_product(
        "Healthy",
        quality=80,
        bug_level=5,
        market_fit=75,
        technical_debt=8,
        user_count=100,
        churn_rate=Decimal("0.0400"),
    )

    bad_churn = calculate_churned_users(bad_product, FixedRandom(0))
    healthy_churn = calculate_churned_users(healthy_product, FixedRandom(0))

    assert bad_churn > healthy_churn


def test_technical_debt_penalty_reduces_quality_improvement_efficiency() -> None:
    low_debt_state = make_state(make_product("Low Debt", technical_debt=10))
    high_debt_state = make_state(make_product("High Debt", technical_debt=80))

    low_outcome = apply_action(
        low_debt_state,
        TurnAction.IMPROVE_QUALITY,
        context=ActionContext(target_product_id=low_debt_state.products[0].id),
    )
    high_outcome = apply_action(
        high_debt_state,
        TurnAction.IMPROVE_QUALITY,
        context=ActionContext(target_product_id=high_debt_state.products[0].id),
    )

    low_gain = low_outcome.state.products[0].quality - low_debt_state.products[0].quality
    high_gain = high_outcome.state.products[0].quality - high_debt_state.products[0].quality

    assert calculate_delivery_penalty(high_debt_state.products[0]) > calculate_delivery_penalty(
        low_debt_state.products[0]
    )
    assert low_gain > high_gain


def test_sunsetting_product_removes_it_from_active_economy() -> None:
    state = make_state(make_product("Analytics"))

    outcome = apply_action(
        state,
        TurnAction.SUNSET_PRODUCT,
        context=ActionContext(target_product_id=state.products[0].id),
    )

    sunset_product = outcome.state.products[0]
    assert sunset_product.is_active is False
    assert sunset_product.lifecycle_stage is LifecycleStage.SUNSET
    assert sunset_product.user_count == 0
    assert calculate_total_revenue(outcome.state.products) == Decimal("0.00")


def test_create_product_validation_rejects_duplicate_names() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")

    with pytest.raises(ValueError, match="already exists"):
        apply_action(
            state,
            TurnAction.CREATE_PRODUCT,
            context=ActionContext(new_product_name="Nexus One"),
        )


def test_resolve_turn_sets_game_over_when_portfolio_burn_exceeds_cash() -> None:
    state = make_state(
        make_product(
            "Burner",
            user_count=0,
            revenue_per_user=Decimal("0.00"),
            maintenance_cost=Decimal("500.00"),
            technical_debt=80,
        ),
        cash_on_hand=Decimal("100.00"),
    )

    resolution = resolve_turn(state, FixedRandom(0))

    assert resolution.state.company.game_over is True
    assert resolution.state.company.cash_on_hand < Decimal("0.00")


def test_hiring_and_firing_change_salary_burden() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")

    hired = apply_action(
        state,
        TurnAction.HIRE_EMPLOYEE,
        context=ActionContext(
            hire_full_name="Ada Wong",
            hire_role=EmployeeRole.ENGINEER,
            hire_seniority=Seniority.MID,
            hire_specialization="platform",
        ),
    )

    assert calculate_total_salary_cost(hired.state.employees) > Decimal("0.00")
    assert calculate_total_operating_cost(hired.state.products, hired.state.employees) > (
        calculate_total_operating_cost(state.products, state.employees)
    )

    employee_id = hired.state.employees[0].id
    fired = apply_action(
        hired.state,
        TurnAction.FIRE_EMPLOYEE,
        context=ActionContext(employee_id=employee_id),
    )

    assert calculate_total_salary_cost(fired.state.employees) == Decimal("0.00")


def test_assignment_increases_engineer_effect_on_quality_work() -> None:
    product = make_product("Core")
    assigned_engineer = make_employee(
        "Rin Dev",
        EmployeeRole.ENGINEER,
        assigned_product_id=product.id,
        productivity=72,
    )
    unassigned_engineer = make_employee(
        "Rin Dev",
        EmployeeRole.ENGINEER,
        assigned_product_id=None,
        productivity=72,
    )
    assigned_state = make_state(product.model_copy(deep=True), employees=[assigned_engineer])
    unassigned_state = make_state(product.model_copy(deep=True), employees=[unassigned_engineer])

    assigned_outcome = apply_action(
        assigned_state,
        TurnAction.IMPROVE_QUALITY,
        context=ActionContext(target_product_id=assigned_state.products[0].id),
    )
    unassigned_outcome = apply_action(
        unassigned_state,
        TurnAction.IMPROVE_QUALITY,
        context=ActionContext(target_product_id=unassigned_state.products[0].id),
    )

    assigned_gain = assigned_outcome.state.products[0].quality - assigned_state.products[0].quality
    unassigned_gain = (
        unassigned_outcome.state.products[0].quality
        - unassigned_state.products[0].quality
    )

    assert assigned_gain > unassigned_gain


def test_burnout_reduces_effective_productivity_and_rest_team_recovers() -> None:
    product = make_product("Core", bug_level=50, technical_debt=70)
    employee = make_employee(
        "Tired Dev",
        EmployeeRole.ENGINEER,
        assigned_product_id=product.id,
        energy=42,
        morale=60,
        productivity=70,
    )
    state = make_state(product, employees=[employee])

    before_productivity = calculate_effective_productivity(state.employees[0])
    resolution = resolve_turn(state, FixedRandom(0))
    after_turn_productivity = calculate_effective_productivity(resolution.state.employees[0])

    rested = apply_action(
        resolution.state,
        TurnAction.REST_TEAM,
        context=ActionContext(),
    )
    after_rest_productivity = calculate_effective_productivity(rested.state.employees[0])

    assert resolution.state.employees[0].energy < employee.energy
    assert after_turn_productivity < before_productivity
    assert after_rest_productivity > after_turn_productivity


def test_role_specific_contributions_are_visible_in_outcomes() -> None:
    base_product = make_product("LaunchPad", market_fit=45, bug_level=12)

    engineer = make_employee(
        "Eli Engineer",
        EmployeeRole.ENGINEER,
        assigned_product_id=base_product.id,
        productivity=74,
    )
    marketer = make_employee(
        "Mara Marketer",
        EmployeeRole.MARKETER,
        assigned_product_id=base_product.id,
        productivity=74,
    )

    engineer_quality_state = make_state(base_product.model_copy(deep=True), employees=[engineer])
    marketer_quality_state = make_state(base_product.model_copy(deep=True), employees=[marketer])

    engineer_quality = apply_action(
        engineer_quality_state,
        TurnAction.IMPROVE_QUALITY,
        context=ActionContext(target_product_id=engineer_quality_state.products[0].id),
    )
    marketer_quality = apply_action(
        marketer_quality_state,
        TurnAction.IMPROVE_QUALITY,
        context=ActionContext(target_product_id=marketer_quality_state.products[0].id),
    )

    engineer_marketing_state = make_state(
        base_product.model_copy(deep=True),
        employees=[engineer.model_copy(deep=True)],
    )
    marketer_marketing_state = make_state(
        base_product.model_copy(deep=True),
        employees=[marketer.model_copy(deep=True)],
    )

    engineer_marketing = apply_action(
        engineer_marketing_state,
        TurnAction.MARKET_PRODUCT,
        context=ActionContext(target_product_id=engineer_marketing_state.products[0].id),
    )
    marketer_marketing = apply_action(
        marketer_marketing_state,
        TurnAction.MARKET_PRODUCT,
        context=ActionContext(target_product_id=marketer_marketing_state.products[0].id),
    )

    engineer_quality_gain = (
        engineer_quality.state.products[0].quality - engineer_quality_state.products[0].quality
    )
    marketer_quality_gain = (
        marketer_quality.state.products[0].quality - marketer_quality_state.products[0].quality
    )
    engineer_user_gain = (
        engineer_marketing.state.products[0].user_count
        - engineer_marketing_state.products[0].user_count
    )
    marketer_user_gain = (
        marketer_marketing.state.products[0].user_count
        - marketer_marketing_state.products[0].user_count
    )

    assert engineer_quality_gain > marketer_quality_gain
    assert marketer_user_gain > engineer_user_gain
