"""Context builders for the lightweight 2D frontend."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.domain.models import (
    BudgetStance,
    CandidateTrait,
    CapitalPlanMode,
    CapitalSourcePreference,
    CompanyStrategy,
    EmployeeRole,
    FunctionalBudgetPreset,
    GameState,
    MarketSegment,
    PackagingStrategy,
    PartnerChannel,
    PricingTier,
    ProductReleaseType,
    RoadmapFocus,
    RoadmapProjectType,
    Seniority,
    SupportLaneFocus,
    TurnAction,
)
from nexus_tech.simulation.engine import ActionContext


@dataclass(frozen=True)
class ActionRequest:
    """One actionable request emitted by a 2D context picker."""

    action: TurnAction
    context: ActionContext
    label: str


@dataclass(frozen=True)
class PickerOption:
    """One visible option inside a 2D context picker."""

    key_hint: str
    title: str
    description: str
    request: ActionRequest


@dataclass(frozen=True)
class ContextPicker:
    """A compact modal state that asks the player to choose one option."""

    title: str
    description: str
    severity: str
    options: tuple[PickerOption, ...]


_DIRECT_ACTIONS = {
    TurnAction.END_TURN,
    TurnAction.VIEW_STATUS,
    TurnAction.REVIEW_TEAM,
    TurnAction.REVIEW_FINANCE,
    TurnAction.REVIEW_CUSTOMERS,
    TurnAction.REVIEW_PIPELINE,
    TurnAction.REVIEW_BOARD,
    TurnAction.REVIEW_PARTNERSHIPS,
    TurnAction.VIEW_REPORT,
    TurnAction.TAKE_LOAN,
    TurnAction.RAISE_ANGEL,
    TurnAction.RAISE_VC,
    TurnAction.REPAY_DEBT,
    TurnAction.REFINANCE_DEBT,
    TurnAction.DEBT_ROLLOVER,
    TurnAction.REBALANCE_CAPITAL,
    TurnAction.RAISE_RESERVE_TARGET,
    TurnAction.STEP_UP_RESERVE_DISCIPLINE,
    TurnAction.HARDEN_FINANCING_POSTURE,
    TurnAction.SET_REFINANCING_POSTURE,
    TurnAction.SET_COVENANT_FIREWALL,
    TurnAction.SET_DEBT_STRATEGY,
    TurnAction.SET_GROWTH_FIREBREAK,
    TurnAction.SET_PATH_CAPITAL_POSTURE,
    TurnAction.SET_PATH_CASH_WATERFALL,
    TurnAction.SET_BOARD_RESET_CONTINGENCY_BUFFER,
    TurnAction.SET_ENDGAME_CAPITAL_MAP,
    TurnAction.SET_EXIT_READINESS_BUFFER,
    TurnAction.SET_TERMINAL_LIQUIDITY_CONTROLS,
    TurnAction.SET_CAPITAL_REALLOCATION_GRID,
    TurnAction.SET_PATH_CONTROL_MATRIX,
    TurnAction.SET_PATH_RESILIENCE_GRID,
    TurnAction.SET_BALANCE_SHEET_RECOVERY_MESH,
    TurnAction.SET_TERMINAL_RECOVERY_LATTICE,
    TurnAction.SET_TERMINAL_CONTINUITY_MATRIX,
    TurnAction.SET_TERMINAL_RESILIENCE_COVENANT,
    TurnAction.SET_TERMINAL_SOLVENCY_STATUTE,
    TurnAction.SET_TERMINAL_SOLVENCY_MANDATE,
    TurnAction.SET_TERMINAL_SOLVENCY_COMMISSION,
    TurnAction.SET_TERMINAL_SOLVENCY_OVERSIGHT,
    TurnAction.SET_TERMINAL_SOLVENCY_COUNCIL,
    TurnAction.LOCK_CAPITAL_BUFFER,
    TurnAction.EXECUTE_BOARD_RESPONSE,
    TurnAction.START_BOARD_RECOVERY_PLAN,
    TurnAction.EXECUTE_RESTRUCTURE_PLAN,
    TurnAction.REST_TEAM,
    TurnAction.REORG_TEAM,
    TurnAction.SOURCE_CANDIDATES,
    TurnAction.TRIAGE_SUPPORT_BACKLOG,
    TurnAction.UPGRADE_SUPPORT_PROGRAM,
    TurnAction.INVEST_IN_SUPPORT_STAFFING,
    TurnAction.RUN_RENEWAL_SWEEP,
    TurnAction.RUN_ENTERPRISE_ASSURANCE,
    TurnAction.RUN_BILLING_STABILIZATION,
    TurnAction.RUN_ONBOARDING_RECOVERY,
    TurnAction.RUN_ONBOARDING_FAST_TRACK,
    TurnAction.RUN_ENTERPRISE_QUEUE_RESET,
    TurnAction.RUN_WHITE_GLOVE_RECOVERY,
    TurnAction.RUN_WHITE_GLOVE_BACKSTOP,
    TurnAction.RUN_WHITE_GLOVE_RENEWAL_GUARD,
    TurnAction.RUN_WHITE_GLOVE_REFERENCE_RING,
    TurnAction.RUN_WHITE_GLOVE_REFERENCE_COMMITTEE,
    TurnAction.RUN_WHITE_GLOVE_ESCALATION_CELL,
    TurnAction.RUN_WHITE_GLOVE_REFERENCE_BUREAU,
    TurnAction.RUN_WHITE_GLOVE_REFERENCE_EXCHANGE,
    TurnAction.RUN_REFERENCE_RESCUE,
    TurnAction.RUN_ENTERPRISE_REFERENCE_CYCLE,
    TurnAction.RUN_ENTERPRISE_RENEWAL_CABINET,
    TurnAction.RUN_ENTERPRISE_COMMITMENT_BOARD,
    TurnAction.RUN_ENTERPRISE_REFERENCE_CHAMBER,
    TurnAction.RUN_ENTERPRISE_REFERENCE_FORUM,
    TurnAction.RUN_ENTERPRISE_REFERENCE_LATTICE,
    TurnAction.RUN_ENTERPRISE_REFERENCE_SUMMIT,
    TurnAction.RUN_ENTERPRISE_REFERENCE_DIRECTORATE,
    TurnAction.RUN_ENTERPRISE_REFERENCE_SECRETARIAT,
    TurnAction.RUN_ENTERPRISE_REFERENCE_AUTHORITY,
    TurnAction.RUN_ENTERPRISE_REFERENCE_COMMISSION,
    TurnAction.RUN_ENTERPRISE_REFERENCE_OVERSIGHT,
    TurnAction.RUN_ENTERPRISE_REFERENCE_COUNCIL,
    TurnAction.RUN_BILLING_RETENTION_RESET,
    TurnAction.RUN_BILLING_COVENANT_RESET,
    TurnAction.RUN_BILLING_DISPUTE_DESK,
    TurnAction.RUN_BILLING_DISPUTE_CABINET,
    TurnAction.RUN_BILLING_COLLECTION_BRIDGE,
    TurnAction.RUN_BILLING_COLLECTION_OFFICE,
    TurnAction.RUN_BILLING_SETTLEMENT_BOARD,
    TurnAction.RUN_BILLING_CASH_WAR_ROOM,
    TurnAction.RUN_BILLING_LIQUIDITY_COMMAND,
    TurnAction.RUN_BILLING_LIQUIDITY_SUMMIT,
    TurnAction.RUN_BILLING_LIQUIDITY_DIRECTORATE,
    TurnAction.RUN_BILLING_LIQUIDITY_SECRETARIAT,
    TurnAction.RUN_BILLING_LIQUIDITY_AUTHORITY,
    TurnAction.RUN_BILLING_LIQUIDITY_COMMISSION,
    TurnAction.RUN_BILLING_LIQUIDITY_OVERSIGHT,
    TurnAction.RUN_BILLING_LIQUIDITY_COUNCIL,
    TurnAction.RUN_ONBOARDING_CONTROL_TOWER,
    TurnAction.RUN_ONBOARDING_LAUNCH_CELL,
    TurnAction.RUN_ONBOARDING_ADOPTION_HUB,
    TurnAction.RUN_ONBOARDING_STABILITY_BOARD,
    TurnAction.RUN_ONBOARDING_RETENTION_MESH,
    TurnAction.RUN_ONBOARDING_ASSURANCE_GRID,
    TurnAction.RUN_ONBOARDING_DURABILITY_MESH,
    TurnAction.RUN_ONBOARDING_CONTINUITY_LATTICE,
    TurnAction.RUN_ONBOARDING_CONTINUITY_BUREAU,
    TurnAction.RUN_ONBOARDING_CONTINUITY_SECRETARIAT,
    TurnAction.RUN_ONBOARDING_CONTINUITY_AUTHORITY,
    TurnAction.RUN_ONBOARDING_CONTINUITY_COMMISSION,
    TurnAction.RUN_ONBOARDING_CONTINUITY_OVERSIGHT,
    TurnAction.RUN_ONBOARDING_CONTINUITY_COUNCIL,
    TurnAction.RUN_ENTERPRISE_LANE_MESH,
    TurnAction.RUN_BILLING_LANE_MESH,
    TurnAction.RUN_ONBOARDING_LANE_MESH,
    TurnAction.RUN_WHITE_GLOVE_LANE_MESH,
    TurnAction.RUN_ENTERPRISE_REFERENCE_WATCH,
    TurnAction.RUN_BILLING_RENEWAL_WATCH,
    TurnAction.RUN_ONBOARDING_GO_LIVE_WATCH,
    TurnAction.RUN_WHITE_GLOVE_RETENTION_WATCH,
    TurnAction.REBALANCE_CHANNEL_MIX,
    TurnAction.WAIT,
}

_PRODUCT_ACTIONS = {
    TurnAction.IMPROVE_QUALITY,
    TurnAction.ADD_FEATURE,
    TurnAction.REDUCE_TECHNICAL_DEBT,
    TurnAction.MARKET_PRODUCT,
}

_PARTNERSHIP_ACTIONS = {
    TurnAction.INVEST_IN_PARTNER_ENABLEMENT,
    TurnAction.RUN_CHANNEL_QBR,
    TurnAction.RUN_PARTNER_RECOVERY_SPRINT,
    TurnAction.RUN_CHANNEL_FIREBREAK,
    TurnAction.RUN_CHANNEL_CONFLICT_RESET,
    TurnAction.RUN_CHANNEL_REALIGNMENT,
    TurnAction.RUN_CHANNEL_SYNERGY_RESET,
    TurnAction.RUN_PARTNER_MARGIN_RESET,
    TurnAction.RUN_CHANNEL_STABILITY_RESET,
    TurnAction.RUN_CHANNEL_DEPENDENCY_RESET,
    TurnAction.RUN_CHANNEL_CONFIDENCE_FIREWALL,
    TurnAction.RUN_CHANNEL_DURABILITY_MESH,
    TurnAction.RUN_CHANNEL_CONFLICT_LATTICE,
    TurnAction.RUN_CHANNEL_RESILIENCE_GRID,
    TurnAction.RUN_CHANNEL_CONTINUITY_MATRIX,
    TurnAction.RUN_CHANNEL_ASSURANCE_COVENANT,
    TurnAction.RUN_CHANNEL_DURABILITY_STATUTE,
    TurnAction.RUN_CHANNEL_DURABILITY_MANDATE,
    TurnAction.RUN_CHANNEL_DURABILITY_COMMISSION,
    TurnAction.RUN_CHANNEL_DURABILITY_OVERSIGHT,
    TurnAction.RUN_CHANNEL_DURABILITY_COUNCIL,
    TurnAction.RUN_RESELLER_ENABLEMENT_RESET,
    TurnAction.RUN_INTEGRATION_CUTOVER_RESET,
    TurnAction.RUN_MARKETPLACE_CHARGEBACK_RESET,
    TurnAction.RENEGOTIATE_PARTNERSHIP,
    TurnAction.REACTIVATE_PARTNERSHIP,
    TurnAction.PAUSE_PARTNERSHIP,
}


def build_command_request(
    state: GameState,
    *,
    command: str,
    selected_product_id: str | None = None,
) -> ActionRequest | ContextPicker | None:
    """Build either a direct action request or a picker for one command id."""

    try:
        action = TurnAction(command)
    except ValueError:
        return None

    if action is TurnAction.CREATE_PRODUCT:
        product_number = len(state.products) + 1
        return ActionRequest(
            action=action,
            context=ActionContext(new_product_name=f"New Venture {product_number}"),
            label=action.value,
        )

    if action in _DIRECT_ACTIONS:
        return ActionRequest(action=action, context=ActionContext(), label=action.value)

    product = _pick_selected_product(state, selected_product_id)
    if action in _PRODUCT_ACTIONS and product is not None:
        return ActionRequest(
            action=action,
            context=ActionContext(target_product_id=product.id),
            label=action.value,
        )

    if action is TurnAction.CREATE_PARTNERSHIP and product is not None:
        return _picker(
            title="Choose Partner Channel",
            description=f"Open a new partner motion for {product.name}.",
            severity="info",
            options=tuple(
                PickerOption(
                    key_hint=str(index + 1),
                    title=_label(channel.value),
                    description=f"Create a {channel.value} partner lane for {product.name}.",
                    request=ActionRequest(
                        action=action,
                        context=ActionContext(
                            target_product_id=product.id,
                            partner_channel=channel,
                        ),
                        label=f"{action.value}:{channel.value}",
                    ),
                )
                for index, channel in enumerate(PartnerChannel)
            ),
        )

    if action is TurnAction.ADJUST_PRICING and product is not None:
        return _enum_picker(
            title="Choose Pricing Tier",
            description=f"Change the pricing posture for {product.name}.",
            severity="warning",
            action=action,
            values=PricingTier,
            context_builder=lambda tier: ActionContext(
                target_product_id=product.id,
                pricing_tier=tier,
            ),
        )

    if action is TurnAction.SET_PACKAGING_STRATEGY and product is not None:
        return _enum_picker(
            title="Choose Packaging Strategy",
            description=f"Change how {product.name} packages value.",
            severity="info",
            action=action,
            values=PackagingStrategy,
            context_builder=lambda strategy: ActionContext(
                target_product_id=product.id,
                packaging_strategy=strategy,
            ),
        )

    if action is TurnAction.SET_TARGET_SEGMENT and product is not None:
        return _enum_picker(
            title="Choose Target Segment",
            description=f"Reposition {product.name} toward a different market segment.",
            severity="info",
            action=action,
            values=MarketSegment,
            context_builder=lambda segment: ActionContext(
                target_product_id=product.id,
                target_segment=segment,
            ),
        )

    if action is TurnAction.HIRE_EMPLOYEE:
        hire_number = len(state.employees) + 1
        options = (
            ("Engineer", EmployeeRole.ENGINEER, Seniority.MID, "product"),
            ("Designer", EmployeeRole.DESIGNER, Seniority.MID, "ux"),
            ("Marketer", EmployeeRole.MARKETER, Seniority.MID, "demand"),
            ("PM", EmployeeRole.PRODUCT_MANAGER, Seniority.MID, "roadmap"),
        )
        return _picker(
            title="Choose Hiring Track",
            description="Pick the next role to add to the team.",
            severity="info",
            options=tuple(
                PickerOption(
                    key_hint=str(index + 1),
                    title=title,
                    description=f"Hire one {role.value.replace('_', ' ')} into the next open seat.",
                    request=ActionRequest(
                        action=action,
                        context=ActionContext(
                            hire_full_name=f"2D {title} {hire_number}",
                            hire_role=role,
                            hire_seniority=seniority,
                            hire_specialization=specialization,
                            hire_trait=CandidateTrait.STEADY_OPERATOR,
                        ),
                        label=f"{action.value}:{role.value}",
                    ),
                )
                for index, (title, role, seniority, specialization) in enumerate(options)
            ),
        )

    if action in {
        TurnAction.ASSIGN_EMPLOYEE,
        TurnAction.TRAIN_EMPLOYEE,
        TurnAction.PROMOTE_EMPLOYEE,
        TurnAction.RUN_COMP_REVIEW,
        TurnAction.RUN_SUCCESSION_REVIEW,
        TurnAction.APPOINT_TEAM_LEAD,
        TurnAction.FIRE_EMPLOYEE,
        TurnAction.CLEAR_MANAGER,
        TurnAction.UNASSIGN_EMPLOYEE,
    }:
        if not state.employees:
            return None
        employees = list(state.employees)
        if action is TurnAction.ASSIGN_EMPLOYEE:
            employees = [employee for employee in employees if employee.assigned_product_id is None]
        options: list[PickerOption] = []
        for index, employee in enumerate(employees[:9]):
            description = (
                f"{employee.role.value.replace('_', ' ')} | "
                f"{employee.seniority.value} | morale {employee.morale}"
            )
            context = ActionContext(employee_id=employee.id)
            if action is TurnAction.ASSIGN_EMPLOYEE and product is not None:
                context = ActionContext(
                    employee_id=employee.id,
                    target_product_id=product.id,
                )
                description = f"{description} -> {product.name}"
            options.append(
                PickerOption(
                    key_hint=str(index + 1),
                    title=employee.full_name,
                    description=description,
                    request=ActionRequest(
                        action=action,
                        context=context,
                        label=f"{action.value}:{employee.full_name}",
                    ),
                )
            )
        return _picker(
            title=_label(action.value),
            description="Choose the employee to apply this action to.",
            severity="info",
            options=tuple(options),
        )

    if action is TurnAction.SCREEN_CANDIDATE:
        return _candidate_picker(
            state,
            action=action,
            title="Screen Candidate",
            description="Choose a sourced candidate to screen.",
            stage_filter={"sourced"},
        )

    if action is TurnAction.INTERVIEW_CANDIDATE:
        return _candidate_picker(
            state,
            action=action,
            title="Interview Candidate",
            description="Choose a screened candidate to interview.",
            stage_filter={"screened"},
        )

    if action is TurnAction.MAKE_HIRING_OFFER:
        return _candidate_picker(
            state,
            action=action,
            title="Make Hiring Offer",
            description="Choose an interviewed candidate to receive an offer.",
            stage_filter={"interviewed"},
        )

    if action is TurnAction.SET_COMPANY_STRATEGY:
        return _enum_picker(
            title="Choose Company Strategy",
            description="Shift the company-wide operating posture.",
            severity="info",
            action=action,
            values=CompanyStrategy,
            context_builder=lambda strategy: ActionContext(strategy=strategy),
        )

    if action is TurnAction.SET_ROADMAP:
        return _enum_picker(
            title="Choose Roadmap Focus",
            description="Set the next few turns of product emphasis.",
            severity="info",
            action=action,
            values=RoadmapFocus,
            context_builder=lambda focus: ActionContext(roadmap_focus=focus),
        )

    if action is TurnAction.SET_BUDGET_STANCE:
        return _enum_picker(
            title="Choose Budget Stance",
            description="Decide how hard to spend against the quarter plan.",
            severity="warning",
            action=action,
            values=BudgetStance,
            context_builder=lambda stance: ActionContext(budget_stance=stance),
        )

    if action is TurnAction.SET_FUNCTIONAL_BUDGET:
        return _enum_picker(
            title="Choose Functional Budget",
            description="Apply one preset for engineering, GTM, and customer-success spend.",
            severity="warning",
            action=action,
            values=FunctionalBudgetPreset,
            context_builder=lambda preset: ActionContext(functional_budget_preset=preset),
        )

    if action is TurnAction.SET_SUPPORT_LANE_FOCUS:
        return _enum_picker(
            title="Choose Support Lane Focus",
            description="Concentrate support relief on the hottest service lane.",
            severity="warning",
            action=action,
            values=SupportLaneFocus,
            context_builder=lambda lane: ActionContext(support_lane_focus=lane),
        )

    if action is TurnAction.SET_CAPITAL_PLAN:
        capital_presets = (
            (
                "Conserve / Bootstrap",
                "Slow expansion and protect reserves with internal cash first.",
                CapitalPlanMode.CONSERVE,
                CapitalSourcePreference.BOOTSTRAP,
            ),
            (
                "Balanced / Debt",
                "Keep a neutral plan and allow loans if runway tightens.",
                CapitalPlanMode.BALANCED,
                CapitalSourcePreference.DEBT,
            ),
            (
                "Expand / Angel",
                "Lean into growth with moderate outside capital.",
                CapitalPlanMode.EXPAND,
                CapitalSourcePreference.ANGEL,
            ),
            (
                "Expand / Venture",
                "Open the most aggressive growth posture and prefer venture funding.",
                CapitalPlanMode.EXPAND,
                CapitalSourcePreference.VENTURE,
            ),
        )
        return _picker(
            title="Choose Capital Plan",
            description="Pick a capital posture and preferred funding source.",
            severity="warning",
            options=tuple(
                PickerOption(
                    key_hint=str(index + 1),
                    title=title,
                    description=description,
                    request=ActionRequest(
                        action=action,
                        context=ActionContext(
                            capital_plan_mode=mode,
                            capital_source_preference=source,
                        ),
                        label=f"{action.value}:{mode.value}:{source.value}",
                    ),
                )
                for index, (title, description, mode, source) in enumerate(capital_presets)
            ),
        )

    if action is TurnAction.PLAN_RELEASE and product is not None:
        return _enum_picker(
            title="Choose Release Type",
            description=f"Plan a new release for {product.name}.",
            severity="info",
            action=action,
            values=ProductReleaseType,
            context_builder=lambda release_type: ActionContext(
                target_product_id=product.id,
                release_type=release_type,
            ),
        )

    if action is TurnAction.WORK_RELEASE:
        if not state.product_releases:
            return None
        return _picker(
            title="Work Release",
            description="Choose which planned release should get execution time.",
            severity="info",
            options=tuple(
                PickerOption(
                    key_hint=str(index + 1),
                    title=f"{release.release_type.value.replace('_', ' ')}",
                    description=(
                        f"Progress {release.progress}/{release.required_progress} | "
                        f"risk {release.risk}"
                    ),
                    request=ActionRequest(
                        action=action,
                        context=ActionContext(release_id=release.id),
                        label=f"{action.value}:{release.id}",
                    ),
                )
                for index, release in enumerate(state.product_releases[:9])
            ),
        )

    if action is TurnAction.CREATE_SALES_DEAL and product is not None:
        return ActionRequest(
            action=action,
            context=ActionContext(target_product_id=product.id),
            label=f"{action.value}:{product.name}",
        )

    if action is TurnAction.ADVANCE_SALES_DEAL:
        if not state.sales_deals:
            return None
        return _picker(
            title="Advance Sales Deal",
            description="Choose which active deal should move forward.",
            severity="info",
            options=tuple(
                PickerOption(
                    key_hint=str(index + 1),
                    title=deal.name,
                    description=(
                        f"{deal.stage.value} | prob {deal.probability} | {deal.plan_tier.value}"
                    ),
                    request=ActionRequest(
                        action=action,
                        context=ActionContext(sales_deal_id=deal.id),
                        label=f"{action.value}:{deal.name}",
                    ),
                )
                for index, deal in enumerate(state.sales_deals[:9])
            ),
        )

    if action is TurnAction.START_ROADMAP_PROJECT:
        return _enum_picker(
            title="Choose Roadmap Project",
            description="Launch one strategic roadmap project.",
            severity="info",
            action=action,
            values=RoadmapProjectType,
            context_builder=lambda project_type: ActionContext(
                target_product_id=product.id if product is not None else None,
                roadmap_project_type=project_type,
            ),
        )

    if action is TurnAction.WORK_ROADMAP_PROJECT:
        if not state.roadmap_projects:
            return None
        return _picker(
            title="Work Roadmap Project",
            description="Choose the project that should get execution time.",
            severity="info",
            options=tuple(
                PickerOption(
                    key_hint=str(index + 1),
                    title=project.project_type.value.replace("_", " ").title(),
                    description=(
                        f"{project.status.value} | progress {project.progress}/"
                        f"{project.required_progress} | risk {project.delivery_risk}"
                    ),
                    request=ActionRequest(
                        action=action,
                        context=ActionContext(roadmap_project_id=project.id),
                        label=f"{action.value}:{project.project_type.value}",
                    ),
                )
                for index, project in enumerate(state.roadmap_projects[:9])
            ),
        )

    if action in _PARTNERSHIP_ACTIONS:
        if not state.partnerships:
            return None
        return _picker(
            title=_label(action.value),
            description="Choose which partner relationship should get this intervention.",
            severity="warning",
            options=tuple(
                PickerOption(
                    key_hint=str(index + 1),
                    title=partnership.name,
                    description=(
                        f"{partnership.channel.value} | {partnership.status.value} | "
                        f"risk {partnership.risk}"
                    ),
                    request=ActionRequest(
                        action=action,
                        context=ActionContext(partnership_id=partnership.id),
                        label=f"{action.value}:{partnership.name}",
                    ),
                )
                for index, partnership in enumerate(state.partnerships[:9])
            ),
        )

    return None


def explain_command_unavailable(
    state: GameState,
    *,
    command: str,
    selected_product_id: str | None = None,
) -> str | None:
    """Return a concrete reason when the 2D frontend should block one command."""

    try:
        action = TurnAction(command)
    except ValueError:
        return "This command id is not recognized by the game."

    product = _pick_selected_product(state, selected_product_id)
    if state.pending_event is not None and action not in _DIRECT_ACTIONS:
        return "Resolve the pending event before taking new operating actions."
    if action in _PRODUCT_ACTIONS and product is None:
        return "Select an active product first."
    if (
        action
        in {
            TurnAction.CREATE_PARTNERSHIP,
            TurnAction.ADJUST_PRICING,
            TurnAction.SET_PACKAGING_STRATEGY,
            TurnAction.SET_TARGET_SEGMENT,
            TurnAction.PLAN_RELEASE,
            TurnAction.CREATE_SALES_DEAL,
        }
        and product is None
    ):
        return "You need an active product before running this command."
    if action is TurnAction.ASSIGN_EMPLOYEE and not state.employees:
        return "Hire someone first. There is no employee to assign yet."
    if action is TurnAction.ASSIGN_EMPLOYEE and not any(
        employee.assigned_product_id is None for employee in state.employees
    ):
        return "Every teammate is already assigned. Unassign or hire before reassigning."
    if (
        action
        in {
            TurnAction.TRAIN_EMPLOYEE,
            TurnAction.PROMOTE_EMPLOYEE,
            TurnAction.RUN_COMP_REVIEW,
            TurnAction.RUN_SUCCESSION_REVIEW,
            TurnAction.APPOINT_TEAM_LEAD,
            TurnAction.FIRE_EMPLOYEE,
            TurnAction.CLEAR_MANAGER,
            TurnAction.UNASSIGN_EMPLOYEE,
        }
        and not state.employees
    ):
        return "There is no employee available for this action yet."
    if (
        action
        in {
            TurnAction.SCREEN_CANDIDATE,
            TurnAction.INTERVIEW_CANDIDATE,
            TurnAction.MAKE_HIRING_OFFER,
        }
        and not state.hiring_candidates
    ):
        return "Source candidates first. The hiring funnel is empty."
    if action is TurnAction.SCREEN_CANDIDATE and not any(
        candidate.stage.value == "sourced" for candidate in state.hiring_candidates
    ):
        return "No sourced candidate is ready to screen."
    if action is TurnAction.INTERVIEW_CANDIDATE and not any(
        candidate.stage.value == "screened" for candidate in state.hiring_candidates
    ):
        return "No screened candidate is ready for an interview."
    if action is TurnAction.MAKE_HIRING_OFFER and not any(
        candidate.stage.value == "interviewed" for candidate in state.hiring_candidates
    ):
        return "No interviewed candidate is ready for an offer."
    if action is TurnAction.WORK_RELEASE and not state.product_releases:
        return "Plan a release first. There is nothing to work yet."
    if action is TurnAction.ADVANCE_SALES_DEAL and not state.sales_deals:
        return "Create a sales deal first. The pipeline is empty."
    if action is TurnAction.WORK_ROADMAP_PROJECT and not state.roadmap_projects:
        return "Start a roadmap project first."
    if action in _PARTNERSHIP_ACTIONS and not state.partnerships:
        return "Open a partnership first. There is no live channel to target."
    if action is TurnAction.END_TURN and state.pending_event is not None:
        return "Resolve the pending event before ending the turn."
    return None


def _enum_picker(
    *,
    title: str,
    description: str,
    severity: str,
    action: TurnAction,
    values,
    context_builder,
) -> ContextPicker:
    options = tuple(
        PickerOption(
            key_hint=str(index + 1),
            title=_label(value.value),
            description=f"Set {title.lower()} to {_label(value.value).lower()}.",
            request=ActionRequest(
                action=action,
                context=context_builder(value),
                label=f"{action.value}:{value.value}",
            ),
        )
        for index, value in enumerate(values)
    )
    return _picker(
        title=title,
        description=description,
        severity=severity,
        options=options,
    )


def _picker(
    *,
    title: str,
    description: str,
    severity: str,
    options: tuple[PickerOption, ...],
) -> ContextPicker | None:
    if not options:
        return None
    return ContextPicker(
        title=title,
        description=description,
        severity=severity,
        options=options,
    )


def _candidate_picker(
    state: GameState,
    *,
    action: TurnAction,
    title: str,
    description: str,
    stage_filter: set[str],
) -> ContextPicker | None:
    candidates = [
        candidate for candidate in state.hiring_candidates if candidate.stage.value in stage_filter
    ]
    if not candidates:
        return None
    return _picker(
        title=title,
        description=description,
        severity="info",
        options=tuple(
            PickerOption(
                key_hint=str(index + 1),
                title=candidate.full_name,
                description=(
                    f"{candidate.role.value.replace('_', ' ')} | "
                    f"{candidate.stage.value} | productivity {candidate.expected_productivity}"
                ),
                request=ActionRequest(
                    action=action,
                    context=ActionContext(hiring_candidate_id=candidate.id),
                    label=f"{action.value}:{candidate.full_name}",
                ),
            )
            for index, candidate in enumerate(candidates[:9])
        ),
    )


def _pick_selected_product(state: GameState, selected_product_id: str | None):
    active_products = [product for product in state.products if product.is_active]
    products = active_products or state.products
    if not products:
        return None
    if selected_product_id is not None:
        for product in products:
            if product.id.hex == selected_product_id:
                return product
    return products[0]


def _label(value: str) -> str:
    return value.replace("_", " ").title()
