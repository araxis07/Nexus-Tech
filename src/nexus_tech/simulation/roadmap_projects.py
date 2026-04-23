"""Multi-turn roadmap project rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from nexus_tech.domain.models import (
    GameState,
    Product,
    RoadmapProject,
    RoadmapProjectStatus,
    RoadmapProjectType,
)
from nexus_tech.domain.money import format_money, quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.support import clamp_int, clamp_rate


@dataclass(frozen=True)
class RoadmapProjectSummary:
    """Summary text for roadmap project actions."""

    message: str


def start_roadmap_project(
    state: GameState,
    project_type: RoadmapProjectType,
    target_product_id: UUID | None,
) -> RoadmapProjectSummary:
    """Start a strategic roadmap project."""

    if any(project.status is RoadmapProjectStatus.ACTIVE for project in state.roadmap_projects):
        raise ValueError("Only one roadmap project can be active at a time.")

    target_product = _resolve_target_product(state, target_product_id, project_type)
    project = RoadmapProject(
        project_type=project_type,
        target_product_id=target_product.id if target_product is not None else None,
        required_progress=BALANCE.roadmap_project_required_progress,
        started_turn=state.company.current_turn,
        summary=f"{project_type.value} started.",
    )
    state.roadmap_projects.append(project)
    target_text = f" for {target_product.name}" if target_product is not None else ""
    return RoadmapProjectSummary(
        message=(
            f"Started roadmap project {project_type.value}{target_text}. "
            f"Progress target {project.required_progress}."
        )
    )


def work_roadmap_project(state: GameState, project_id: UUID) -> RoadmapProjectSummary:
    """Advance and complete one roadmap project."""

    project = next(
        (
            project
            for project in state.roadmap_projects
            if project.id == project_id and project.status is RoadmapProjectStatus.ACTIVE
        ),
        None,
    )
    if project is None:
        raise ValueError("Selected roadmap project is not active.")
    if state.company.cash_on_hand < BALANCE.roadmap_project_work_cost:
        required_cash = format_money(BALANCE.roadmap_project_work_cost)
        raise ValueError(f"Not enough cash to work this project. Need {required_cash}.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.roadmap_project_work_cost
    )
    project.progress = min(
        project.required_progress,
        project.progress + _project_progress_gain(state, project),
    )
    if project.progress < project.required_progress:
        return RoadmapProjectSummary(
            message=(
                f"Advanced {project.project_type.value}. "
                f"Progress {project.progress}/{project.required_progress}, "
                f"cash -{BALANCE.roadmap_project_work_cost}."
            )
        )

    _complete_project(state, project)
    return RoadmapProjectSummary(
        message=(
            f"Completed {project.project_type.value}. {project.summary} "
            f"Cash -{BALANCE.roadmap_project_work_cost}."
        )
    )


def _project_progress_gain(state: GameState, project: RoadmapProject) -> int:
    assigned_bonus = 0
    if project.target_product_id is not None:
        assigned_bonus = sum(
            1
            for employee in state.employees
            if employee.assigned_product_id == project.target_product_id
        )
    pm_bonus = sum(1 for employee in state.employees if employee.role.value == "product_manager")
    return BALANCE.roadmap_project_work_progress + assigned_bonus + pm_bonus


def _complete_project(state: GameState, project: RoadmapProject) -> None:
    project.status = RoadmapProjectStatus.COMPLETED
    project.completed_turn = state.company.current_turn
    product = _get_product(state, project.target_product_id)

    if project.project_type is RoadmapProjectType.PLATFORM_REBUILD and product is not None:
        product.quality = clamp_int(product.quality + 4, 0, 100)
        product.bug_level = clamp_int(product.bug_level - 6, 0, 100)
        product.technical_debt = clamp_int(product.technical_debt - 10, 0, 100)
        project.summary = f"{product.name} is materially more stable."
    elif (
        project.project_type is RoadmapProjectType.ENTERPRISE_CERTIFICATION and product is not None
    ):
        product.market_fit = clamp_int(product.market_fit + 5, 0, 100)
        product.technical_debt = clamp_int(product.technical_debt - 4, 0, 100)
        state.company.reputation = clamp_int(state.company.reputation + 2, 0, 100)
        state.finance.board_confidence = clamp_int(state.finance.board_confidence + 3, 0, 100)
        project.summary = f"{product.name} gained enterprise credibility."
    elif project.project_type is RoadmapProjectType.MARKETPLACE_LAUNCH and product is not None:
        product.feature_count += 1
        product.user_count += 10
        product.acquisition_rate = clamp_rate(product.acquisition_rate + Decimal("0.0060"))
        product.bug_level = clamp_int(product.bug_level + 2, 0, 100)
        project.summary = f"{product.name} gained marketplace distribution."
    else:
        for deal in state.sales_deals:
            if deal.stage.value not in {"closed_won", "closed_lost"}:
                deal.probability = clamp_int(deal.probability + 6, 0, 100)
        state.company.reputation = clamp_int(state.company.reputation + 1, 0, 100)
        project.summary = "Sales execution improved across active pipeline."


def _resolve_target_product(
    state: GameState,
    product_id: UUID | None,
    project_type: RoadmapProjectType,
) -> Product | None:
    if project_type is RoadmapProjectType.SALES_PLAYBOOK:
        return None
    if product_id is None:
        raise ValueError("This roadmap project requires a target product.")
    return _get_product(state, product_id)


def _get_product(state: GameState, product_id: UUID | None) -> Product | None:
    if product_id is None:
        return None
    product = next((product for product in state.products if product.id == product_id), None)
    if product is None or not product.is_active:
        raise ValueError("Roadmap project product is not active.")
    return product
