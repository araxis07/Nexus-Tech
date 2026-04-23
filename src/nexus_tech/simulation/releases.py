"""Product release planning and execution rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from nexus_tech.domain.models import (
    GameState,
    Product,
    ProductReleasePlan,
    ProductReleaseStatus,
    ProductReleaseType,
)
from nexus_tech.domain.money import format_money, quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.product_progression import infer_lifecycle_stage
from nexus_tech.simulation.support import clamp_int, clamp_rate


@dataclass(frozen=True)
class ReleaseActionSummary:
    """Summary text for release actions."""

    message: str


def plan_product_release(
    state: GameState,
    product: Product,
    release_type: ProductReleaseType,
) -> ReleaseActionSummary:
    """Create a new release plan for a product."""

    if any(
        release.product_id == product.id and release.status is ProductReleaseStatus.PLANNED
        for release in state.product_releases
    ):
        raise ValueError(f"{product.name} already has a planned release.")

    required_progress = _required_progress(release_type)
    risk = _release_risk(product, release_type)
    release = ProductReleasePlan(
        product_id=product.id,
        release_type=release_type,
        required_progress=required_progress,
        risk=risk,
        scheduled_turn=state.company.current_turn,
        summary=f"{release_type.value} planned for {product.name}.",
    )
    state.product_releases.append(release)
    return ReleaseActionSummary(
        message=(
            f"Planned {release_type.value} for {product.name}. "
            f"Progress target {required_progress}, risk {risk}."
        )
    )


def work_product_release(state: GameState, release_id: UUID) -> ReleaseActionSummary:
    """Advance one planned release and ship it when ready."""

    release = next(
        (
            release
            for release in state.product_releases
            if release.id == release_id and release.status is ProductReleaseStatus.PLANNED
        ),
        None,
    )
    if release is None:
        raise ValueError("Selected release plan is not active.")

    product = next(
        (product for product in state.products if product.id == release.product_id), None
    )
    if product is None or not product.is_active:
        raise ValueError("Release product is no longer active.")

    cost = _release_cost(release.release_type)
    if state.company.cash_on_hand < cost:
        raise ValueError(f"Not enough cash to work this release. Need {format_money(cost)}.")

    state.company.cash_on_hand = quantize_money(state.company.cash_on_hand - cost)
    release.progress = min(
        release.required_progress,
        release.progress + _release_progress_gain(state, product),
    )
    if release.progress < release.required_progress:
        return ReleaseActionSummary(
            message=(
                f"Advanced {release.release_type.value} for {product.name}. "
                f"Progress {release.progress}/{release.required_progress}, cash -{cost}."
            )
        )

    _ship_release(state, product, release)
    return ReleaseActionSummary(
        message=(
            f"Shipped {release.release_type.value} for {product.name}. "
            f"{release.summary} Cash -{cost}."
        )
    )


def _required_progress(release_type: ProductReleaseType) -> int:
    if release_type is ProductReleaseType.STABILITY_PATCH:
        return BALANCE.release_stability_required_progress
    if release_type is ProductReleaseType.MINOR_RELEASE:
        return BALANCE.release_minor_required_progress
    return BALANCE.release_major_required_progress


def _release_cost(release_type: ProductReleaseType) -> Decimal:
    if release_type is ProductReleaseType.STABILITY_PATCH:
        return BALANCE.release_stability_cash_cost
    if release_type is ProductReleaseType.MINOR_RELEASE:
        return BALANCE.release_minor_cash_cost
    return BALANCE.release_major_cash_cost


def _release_risk(product: Product, release_type: ProductReleaseType) -> int:
    base = product.bug_level + (product.technical_debt // 2)
    if release_type is ProductReleaseType.STABILITY_PATCH:
        base -= 10
    if release_type is ProductReleaseType.MAJOR_LAUNCH:
        base += 14
    return clamp_int(base, 0, 100)


def _release_progress_gain(state: GameState, product: Product) -> int:
    assigned = sum(1 for employee in state.employees if employee.assigned_product_id == product.id)
    return BALANCE.release_work_base_progress + assigned


def _ship_release(
    state: GameState,
    product: Product,
    release: ProductReleasePlan,
) -> None:
    release.status = ProductReleaseStatus.SHIPPED
    release.shipped_turn = state.company.current_turn
    if release.release_type is ProductReleaseType.STABILITY_PATCH:
        product.quality = clamp_int(product.quality + 2, 0, 100)
        product.bug_level = clamp_int(product.bug_level - 7, 0, 100)
        product.technical_debt = clamp_int(product.technical_debt - 4, 0, 100)
        state.company.reputation = clamp_int(state.company.reputation + 1, 0, 100)
        release.summary = "Quality improved, bugs dropped, and trust recovered."
    elif release.release_type is ProductReleaseType.MINOR_RELEASE:
        product.feature_count += 1
        product.market_fit = clamp_int(product.market_fit + 2, 0, 100)
        product.bug_level = clamp_int(product.bug_level + 2, 0, 100)
        product.technical_debt = clamp_int(product.technical_debt + 2, 0, 100)
        product.acquisition_rate = clamp_rate(
            product.acquisition_rate + BALANCE.event_press_acquisition_gain
        )
        release.summary = "A focused feature release improved fit but added some upkeep."
    else:
        product.feature_count += 2
        product.market_fit = clamp_int(product.market_fit + 4, 0, 100)
        product.user_count += 12
        product.bug_level = clamp_int(product.bug_level + 5, 0, 100)
        product.technical_debt = clamp_int(product.technical_debt + 6, 0, 100)
        state.company.reputation = clamp_int(state.company.reputation + 2, 0, 100)
        release.summary = "The launch created demand and reputation, with real delivery risk."
    product.lifecycle_stage = infer_lifecycle_stage(product)
