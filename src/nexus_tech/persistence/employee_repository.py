"""Repository for persisted employees."""

from __future__ import annotations

import sqlite3
from decimal import Decimal
from uuid import UUID

from nexus_tech.domain.models import CandidateTrait, Employee, EmployeeRole, Seniority


class EmployeeRepository:
    """Save and load employees for a slot."""

    def save_all(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
        employees: list[Employee],
    ) -> None:
        """Replace the employee roster for one slot."""

        connection.execute("DELETE FROM employees WHERE slot_name = ?", (slot_name,))
        connection.executemany(
            """
            INSERT INTO employees (
                slot_name,
                employee_id,
                display_order,
                full_name,
                role,
                seniority,
                salary,
                energy,
                morale,
                productivity,
                specialization,
                trait,
                experience_points,
                promotion_readiness,
                attrition_risk,
                performance_rating,
                tenure_turns,
                underperformance_streak,
                assigned_product_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    slot_name,
                    str(employee.id),
                    index,
                    employee.full_name,
                    employee.role.value,
                    employee.seniority.value,
                    str(employee.salary),
                    employee.energy,
                    employee.morale,
                    employee.productivity,
                    employee.specialization,
                    employee.trait.value,
                    employee.experience_points,
                    employee.promotion_readiness,
                    employee.attrition_risk,
                    employee.performance_rating,
                    employee.tenure_turns,
                    employee.underperformance_streak,
                    str(employee.assigned_product_id)
                    if employee.assigned_product_id is not None
                    else None,
                )
                for index, employee in enumerate(employees)
            ],
        )

    def load_all(self, connection: sqlite3.Connection, slot_name: str) -> list[Employee]:
        """Load employees for one slot."""

        rows = connection.execute(
            """
            SELECT
                employee_id,
                full_name,
                role,
                seniority,
                salary,
                energy,
                morale,
                productivity,
                specialization,
                trait,
                experience_points,
                promotion_readiness,
                attrition_risk,
                performance_rating,
                tenure_turns,
                underperformance_streak,
                assigned_product_id
            FROM employees
            WHERE slot_name = ?
            ORDER BY display_order ASC
            """,
            (slot_name,),
        ).fetchall()

        return [
            Employee(
                id=UUID(row["employee_id"]),
                full_name=row["full_name"],
                role=EmployeeRole(row["role"]),
                seniority=Seniority(row["seniority"]),
                salary=Decimal(row["salary"]),
                energy=row["energy"],
                morale=row["morale"],
                productivity=row["productivity"],
                specialization=row["specialization"],
                trait=CandidateTrait(row["trait"]),
                experience_points=row["experience_points"] or 0,
                promotion_readiness=row["promotion_readiness"] or 0,
                attrition_risk=row["attrition_risk"] or 0,
                performance_rating=row["performance_rating"] or 62,
                tenure_turns=row["tenure_turns"] or 0,
                underperformance_streak=row["underperformance_streak"] or 0,
                assigned_product_id=UUID(row["assigned_product_id"])
                if row["assigned_product_id"] is not None
                else None,
            )
            for row in rows
        ]
