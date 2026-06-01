"""Frontend event stream helpers for lightweight 2D animations."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.domain.models import GameState
from nexus_tech.domain.money import format_money
from nexus_tech.simulation.endgame import (
    calculate_endgame_pressure,
    calculate_endgame_readiness,
    evaluate_exit_outcome,
)
from nexus_tech.simulation.engine import TurnResolution


@dataclass(frozen=True)
class FrontendEvent:
    """One short-lived event card shown in the 2D frontend."""

    title: str
    detail: str
    severity: str = "info"
    ttl: float = 4.5
    motion: str = "pulse"
    targets: tuple[str, ...] = ()


def build_action_events(
    previous_state: GameState,
    current_state: GameState,
    *,
    action_label: str,
    message: str,
) -> tuple[FrontendEvent, ...]:
    """Summarize one action into lightweight UI events."""

    events: list[FrontendEvent] = [
        FrontendEvent(
            title=action_label.replace("_", " ").title(),
            detail=message,
            severity="info",
            ttl=4.0,
            motion="slide",
            targets=("feed",) + _action_workspace_targets(action_label),
        )
    ]
    events.extend(_build_action_choreography_events(previous_state, current_state, action_label))
    events.extend(_build_delta_events(previous_state, current_state))
    return tuple(events)


def build_turn_resolution_events(
    previous_state: GameState,
    resolution: TurnResolution,
) -> tuple[FrontendEvent, ...]:
    """Summarize one resolved turn into lightweight UI events."""

    current_state = resolution.state
    severity = "danger" if resolution.net_cash_flow < 0 else "success"
    summary = FrontendEvent(
        title=f"Turn {resolution.resolved_turn} Resolved",
        detail=(
            f"Net {format_money(resolution.net_cash_flow)} | revenue "
            f"{format_money(resolution.total_revenue)} | cost "
            f"{format_money(resolution.total_operating_cost)}"
        ),
        severity=severity,
        ttl=5.5,
        motion="slide",
        targets=("feed", "summary:timeline", "summary:metrics", "stat:cash"),
    )
    events = [summary]
    total_user_delta = sum(
        summary_item.net_user_delta for summary_item in resolution.product_summaries
    )
    if total_user_delta:
        tone = "success" if total_user_delta > 0 else "warning"
        events.append(
            FrontendEvent(
                title="Users Shifted",
                detail=f"Net users {'+' if total_user_delta > 0 else ''}{total_user_delta}.",
                severity=tone,
                targets=("stat:users", "summary:metrics"),
            )
        )
    previous_readiness = calculate_endgame_readiness(previous_state)
    current_readiness = calculate_endgame_readiness(current_state, resolution.run_score)
    previous_pressure = calculate_endgame_pressure(previous_state, previous_readiness)
    current_pressure = calculate_endgame_pressure(current_state, current_readiness)
    previous_outcome = evaluate_exit_outcome(previous_state)
    current_outcome = evaluate_exit_outcome(current_state, resolution.run_score)
    previous_blocked_paths = sum(
        1 for gate in previous_pressure.path_outcome_gates if "blocked" in gate.lower()
    )
    current_blocked_paths = sum(
        1 for gate in current_pressure.path_outcome_gates if "blocked" in gate.lower()
    )
    events.append(
        FrontendEvent(
            title="Gate Command",
            detail=(
                f"{current_pressure.path_gate_command_alert}: {current_pressure.path_gate_alert}"
            ),
            severity="warning" if current_blocked_paths else "info",
            ttl=5.0,
            motion="flash" if current_blocked_paths else "pulse",
            targets=("panel:endgame", "summary:timeline"),
        )
    )
    if (
        current_outcome.title != previous_outcome.title
        or current_pressure.dominant_pressure != previous_pressure.dominant_pressure
    ):
        events.append(
            FrontendEvent(
                title="Strategic Outlook",
                detail=(
                    f"{previous_outcome.title} -> {current_outcome.title} | "
                    f"{current_pressure.dominant_pressure.replace('_', ' ')}"
                ),
                severity="info",
                ttl=5.0,
                targets=("panel:endgame", "panel:report", "summary:timeline"),
            )
        )
    if current_blocked_paths != previous_blocked_paths:
        events.append(
            FrontendEvent(
                title="Exit Gates",
                detail=f"{previous_blocked_paths} -> {current_blocked_paths} blocked paths.",
                severity=(
                    "danger"
                    if current_blocked_paths > previous_blocked_paths
                    else "success"
                    if current_blocked_paths < previous_blocked_paths
                    else "warning"
                ),
                motion="flash",
                targets=("panel:endgame", "summary:timeline"),
            )
        )
    events.extend(_build_delta_events(previous_state, current_state))
    return tuple(events)


def _build_delta_events(previous_state: GameState, current_state: GameState) -> list[FrontendEvent]:
    events: list[FrontendEvent] = []

    cash_delta = current_state.company.cash_on_hand - previous_state.company.cash_on_hand
    if cash_delta:
        events.append(
            FrontendEvent(
                title="Cash Changed",
                detail=f"{'+' if cash_delta > 0 else ''}{format_money(cash_delta)}",
                severity="success" if cash_delta > 0 else "warning",
                targets=("stat:cash", "summary:metrics"),
            )
        )

    reputation_delta = current_state.company.reputation - previous_state.company.reputation
    if reputation_delta:
        events.append(
            FrontendEvent(
                title="Reputation Shifted",
                detail=f"{'+' if reputation_delta > 0 else ''}{reputation_delta} reputation.",
                severity="success" if reputation_delta > 0 else "warning",
                targets=("stat:reputation", "summary:metrics"),
            )
        )

    board_delta = current_state.finance.board_pressure - previous_state.finance.board_pressure
    if board_delta:
        events.append(
            FrontendEvent(
                title="Board Pressure",
                detail=f"{'+' if board_delta > 0 else ''}{board_delta} board pressure.",
                severity="danger" if board_delta > 0 else "success",
                motion="flash" if board_delta > 0 else "pulse",
                targets=("stat:board_pressure", "panel:board", "summary:metrics"),
            )
        )

    previous_products = {product.id: product for product in previous_state.products}
    for product in current_state.products:
        previous_product = previous_products.get(product.id)
        if previous_product is None:
            continue
        _append_product_delta_events(events, previous_product, product)

    if current_state.pending_event is not None and (
        previous_state.pending_event is None
        or previous_state.pending_event.event_id != current_state.pending_event.event_id
    ):
        events.append(
            FrontendEvent(
                title=current_state.pending_event.title,
                detail=current_state.pending_event.description,
                severity="warning",
                ttl=6.0,
                motion="slide",
                targets=("feed", "panel:report", "overlay:pending"),
            )
        )

    if current_state.victory_achieved and not previous_state.victory_achieved:
        events.append(
            FrontendEvent(
                title="Victory Achieved",
                detail=current_state.victory_reason or "The company reached a winning end state.",
                severity="success",
                ttl=7.0,
                motion="flash",
                targets=("panel:endgame", "panel:report", "feed"),
            )
        )
    if current_state.company.game_over and not previous_state.company.game_over:
        events.append(
            FrontendEvent(
                title="Company Shutdown",
                detail="Cash or governance pressure broke the run.",
                severity="danger",
                ttl=7.0,
                motion="flash",
                targets=("panel:endgame", "panel:board", "feed"),
            )
        )

    return events


def _append_product_delta_events(
    events: list[FrontendEvent], previous_product, current_product
) -> None:
    quality_delta = current_product.quality - previous_product.quality
    if quality_delta:
        events.append(
            FrontendEvent(
                title=f"{current_product.name} Quality",
                detail=f"{'+' if quality_delta > 0 else ''}{quality_delta} quality.",
                severity="success" if quality_delta > 0 else "warning",
                targets=(
                    f"product:{current_product.id.hex}",
                    f"product:{current_product.id.hex}:quality",
                ),
            )
        )

    bug_delta = current_product.bug_level - previous_product.bug_level
    if bug_delta:
        events.append(
            FrontendEvent(
                title=f"{current_product.name} Bugs",
                detail=f"{'+' if bug_delta > 0 else ''}{bug_delta} bug pressure.",
                severity="danger" if bug_delta > 0 else "success",
                motion="flash" if bug_delta > 0 else "pulse",
                targets=(
                    f"product:{current_product.id.hex}",
                    f"product:{current_product.id.hex}:bugs",
                ),
            )
        )

    user_delta = current_product.user_count - previous_product.user_count
    if user_delta:
        events.append(
            FrontendEvent(
                title=f"{current_product.name} Users",
                detail=f"{'+' if user_delta > 0 else ''}{user_delta} users.",
                severity="success" if user_delta > 0 else "warning",
                targets=(
                    "stat:users",
                    f"product:{current_product.id.hex}",
                ),
            )
        )


def _build_action_choreography_events(
    previous_state: GameState,
    current_state: GameState,
    action_label: str,
) -> tuple[FrontendEvent, ...]:
    primary_product_targets = _primary_product_targets(previous_state, current_state)
    choreography_map = {
        "improve_quality": FrontendEvent(
            title="Quality Sprint",
            detail="Polish work is landing on the active product lane.",
            severity="success",
            motion="slide",
            targets=primary_product_targets + ("panel:products",),
        ),
        "add_feature": FrontendEvent(
            title="Feature Scope",
            detail="The product roadmap is absorbing net-new scope.",
            severity="info",
            motion="slide",
            targets=primary_product_targets + ("panel:products", "panel:pipeline"),
        ),
        "market_product": FrontendEvent(
            title="Demand Push",
            detail="Marketing pressure is now chasing user and revenue lift.",
            severity="info",
            motion="slide",
            targets=primary_product_targets + ("stat:users", "panel:customers"),
        ),
        "reduce_technical_debt": FrontendEvent(
            title="Debt Burn",
            detail="Engineering focus is paying down accumulated technical drag.",
            severity="success",
            motion="slide",
            targets=primary_product_targets + ("panel:products",),
        ),
        "hire_employee": FrontendEvent(
            title="Team Added",
            detail="A new teammate has entered the operating system.",
            severity="success",
            motion="slide",
            targets=("panel:team", "stat:actions"),
        ),
        "assign_employee": FrontendEvent(
            title="Assignment Locked",
            detail="Execution capacity has been routed into a live workstream.",
            severity="info",
            motion="slide",
            targets=("panel:team",) + primary_product_targets,
        ),
        "plan_release": FrontendEvent(
            title="Release Framed",
            detail="The delivery pipeline now has a committed release plan.",
            severity="info",
            motion="slide",
            targets=("panel:pipeline",) + primary_product_targets,
        ),
        "advance_sales_deal": FrontendEvent(
            title="Pipeline Advanced",
            detail="A sales opportunity moved one step closer to closing.",
            severity="success",
            motion="slide",
            targets=("panel:pipeline", "panel:customers"),
        ),
        "adjust_pricing": FrontendEvent(
            title="Pricing Shift",
            detail="The revenue model changed and customer pressure is repricing around it.",
            severity="warning",
            motion="slide",
            targets=("panel:customers", "stat:cash"),
        ),
        "create_partnership": FrontendEvent(
            title="Channel Activated",
            detail="A new partner lane is now part of the growth mix.",
            severity="success",
            motion="slide",
            targets=("panel:partnerships", "stat:users"),
        ),
    }
    event = choreography_map.get(action_label)
    return (event,) if event is not None else ()


def _primary_product_targets(
    previous_state: GameState,
    current_state: GameState,
) -> tuple[str, ...]:
    previous_products = {product.id: product for product in previous_state.products}
    best_product = None
    best_score = -1
    for product in current_state.products:
        previous_product = previous_products.get(product.id)
        if previous_product is None:
            continue
        score = (
            abs(product.quality - previous_product.quality)
            + abs(product.bug_level - previous_product.bug_level)
            + abs(product.user_count - previous_product.user_count)
        )
        if score > best_score:
            best_score = score
            best_product = product
    if best_product is None:
        return ("panel:products",)
    return (
        f"product:{best_product.id.hex}",
        f"product:{best_product.id.hex}:quality",
        f"product:{best_product.id.hex}:bugs",
        f"product:{best_product.id.hex}:fit",
        f"product:{best_product.id.hex}:debt",
    )


def _action_workspace_targets(action_label: str) -> tuple[str, ...]:
    if action_label.startswith(
        (
            "improve_quality",
            "add_feature",
            "market_product",
            "reduce_technical_debt",
            "create_product",
        )
    ):
        return ("panel:products",)
    if action_label.startswith(
        (
            "take_loan",
            "raise_",
            "repay_debt",
            "refinance_debt",
            "debt_rollover",
            "rebalance_capital",
            "raise_reserve_target",
            "set_capital_",
            "set_refinancing_",
            "set_covenant_",
            "set_debt_",
            "set_growth_firebreak",
            "set_path_",
            "set_endgame_capital_",
            "set_exit_readiness_",
            "set_terminal_",
            "step_up_reserve_",
            "harden_financing_",
            "lock_capital_",
        )
    ):
        return ("panel:finance",)
    if action_label.startswith(
        (
            "hire_",
            "fire_",
            "assign_",
            "unassign_",
            "rest_",
            "train_",
            "promote_",
            "run_comp_",
            "run_succession_",
            "appoint_",
            "clear_manager",
            "reorg_",
        )
    ):
        return ("panel:team",)
    if action_label.startswith(
        (
            "plan_release",
            "work_release",
            "create_sales_deal",
            "advance_sales_deal",
            "start_roadmap_project",
            "work_roadmap_project",
            "source_candidates",
            "screen_candidate",
            "interview_candidate",
            "make_hiring_offer",
        )
    ):
        return ("panel:pipeline",)
    if action_label.startswith(
        (
            "adjust_pricing",
            "set_packaging_strategy",
            "set_target_segment",
            "invest_in_customer_success",
            "run_retention_",
            "make_renewal_",
            "run_win_back_",
            "route_support_",
            "run_account_",
            "run_lane_",
            "run_renewal_",
            "run_enterprise_",
            "run_billing_",
            "run_onboarding_",
            "run_white_glove_",
            "run_reference_",
            "triage_support_",
            "invest_in_support_",
            "set_support_",
            "upgrade_support_",
        )
    ):
        return ("panel:customers",)
    if action_label.startswith(
        (
            "create_partnership",
            "invest_in_partner_",
            "run_channel_",
            "run_partner_",
            "run_reseller_",
            "run_integration_",
            "run_marketplace_",
            "rebalance_channel_",
            "renegotiate_partnership",
            "reactivate_partnership",
            "pause_partnership",
        )
    ):
        return ("panel:partnerships",)
    if action_label.startswith(("execute_board_", "start_board_", "execute_restructure_")):
        return ("panel:board",)
    if action_label.startswith(("review_", "view_report")):
        return ("feed",)
    return ()
