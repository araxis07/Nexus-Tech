"""Player-facing names, programs, and families for internal turn actions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from nexus_tech.domain.models import TurnAction


class ActionFamily(StrEnum):
    """Stable player-facing action groups used across presentation layers."""

    PRODUCT = "product"
    MARKET = "market"
    TEAM = "team"
    CUSTOMERS = "customers"
    OPERATIONS = "operations"
    FINANCE = "finance"
    BOARD_EXIT = "board_exit"
    PARTNERS = "partners"
    DELIVERY = "delivery"
    STRATEGY = "strategy"
    REVIEW = "review"
    TURN = "turn"


@dataclass(frozen=True)
class ActionPresentation:
    """Readable metadata for one internal action."""

    command: str
    label: str
    family: ActionFamily
    family_label: str
    program_key: str
    program_label: str
    stage_label: str


@dataclass(frozen=True)
class _ActionProgramRule:
    """Collapse implementation-heavy command ladders into one player concept."""

    key: str
    label: str
    stems: tuple[str, ...]


_FAMILY_LABELS = {
    ActionFamily.PRODUCT: "Product",
    ActionFamily.MARKET: "Market",
    ActionFamily.TEAM: "Team",
    ActionFamily.CUSTOMERS: "Customers",
    ActionFamily.OPERATIONS: "Operations",
    ActionFamily.FINANCE: "Finance",
    ActionFamily.BOARD_EXIT: "Board / Exit",
    ActionFamily.PARTNERS: "Partners",
    ActionFamily.DELIVERY: "Delivery",
    ActionFamily.STRATEGY: "Strategy",
    ActionFamily.REVIEW: "Review",
    ActionFamily.TURN: "Turn",
}

_COMMON_LABELS = {
    TurnAction.CREATE_PRODUCT.value: "Create Product",
    TurnAction.IMPROVE_QUALITY.value: "Improve Quality",
    TurnAction.ADD_FEATURE.value: "Ship Feature",
    TurnAction.REDUCE_TECHNICAL_DEBT.value: "Reduce Tech Debt",
    TurnAction.MARKET_PRODUCT.value: "Grow Demand",
    TurnAction.ADJUST_PRICING.value: "Adjust Pricing",
    TurnAction.SET_TARGET_SEGMENT.value: "Choose Segment",
    TurnAction.SET_COMPANY_STRATEGY.value: "Set Strategy",
    TurnAction.SET_ROADMAP.value: "Set Roadmap",
    TurnAction.SET_BUDGET_STANCE.value: "Set Budget",
    TurnAction.HIRE_EMPLOYEE.value: "Hire Teammate",
    TurnAction.ASSIGN_EMPLOYEE.value: "Assign Teammate",
    TurnAction.REST_TEAM.value: "Rest Team",
    TurnAction.TAKE_LOAN.value: "Take Loan",
    TurnAction.RAISE_ANGEL.value: "Raise Angel Round",
    TurnAction.RAISE_VC.value: "Raise VC Round",
    TurnAction.REPAY_DEBT.value: "Repay Debt",
    TurnAction.TRIAGE_SUPPORT_BACKLOG.value: "Triage Support",
    TurnAction.EXECUTE_BOARD_RESPONSE.value: "Answer Board Ask",
    TurnAction.START_BOARD_RECOVERY_PLAN.value: "Start Board Recovery",
    TurnAction.CREATE_PARTNERSHIP.value: "Open Partner Channel",
    TurnAction.REVIEW_FINANCE.value: "Review Finance",
    TurnAction.REVIEW_TEAM.value: "Review Team",
    TurnAction.REVIEW_CUSTOMERS.value: "Review Customers",
    TurnAction.REVIEW_PARTNERSHIPS.value: "Review Partners",
    TurnAction.REVIEW_PIPELINE.value: "Review Pipeline",
    TurnAction.REVIEW_BOARD.value: "Review Board",
    TurnAction.VIEW_REPORT.value: "Open Run Report",
    TurnAction.VIEW_STATUS.value: "Review Status",
    TurnAction.END_TURN.value: "End Turn",
    TurnAction.WAIT.value: "Hold Action",
}

_PROGRAM_RULES = (
    _ActionProgramRule(
        key="enterprise_trust",
        label="Enterprise Trust",
        stems=(
            "run_enterprise_reference_",
            "run_enterprise_renewal_",
            "run_enterprise_commitment_",
        ),
    ),
    _ActionProgramRule(
        key="billing_recovery",
        label="Billing Recovery",
        stems=("run_billing_",),
    ),
    _ActionProgramRule(
        key="onboarding_continuity",
        label="Onboarding Continuity",
        stems=("run_onboarding_",),
    ),
    _ActionProgramRule(
        key="white_glove_recovery",
        label="White-glove Recovery",
        stems=("run_white_glove_",),
    ),
    _ActionProgramRule(
        key="channel_resilience",
        label="Channel Resilience",
        stems=("run_channel_",),
    ),
    _ActionProgramRule(
        key="partner_recovery",
        label="Partner Recovery",
        stems=("run_partner_",),
    ),
    _ActionProgramRule(
        key="capital_resilience",
        label="Capital Resilience",
        stems=(
            "set_terminal_",
            "set_path_",
            "set_endgame_",
            "set_exit_readiness_",
            "set_capital_reallocation_",
            "set_balance_sheet_",
            "set_board_reset_",
        ),
    ),
)

_CAPITAL_RESILIENCE_COMMANDS = {
    TurnAction.STEP_UP_RESERVE_DISCIPLINE.value,
    TurnAction.HARDEN_FINANCING_POSTURE.value,
    TurnAction.LOCK_CAPITAL_BUFFER.value,
}


def get_action_presentation(action: TurnAction | str) -> ActionPresentation:
    """Return readable metadata without exposing raw snake-case commands."""

    command = action.value if isinstance(action, TurnAction) else action
    family = classify_action(command)
    program = _program_for(command)
    label = _action_label(command)
    if program is not None:
        program_key, program_label, stage_label = program
        label = program_label
    else:
        program_key = command
        program_label = label
        stage_label = ""
    return ActionPresentation(
        command=command,
        label=label,
        family=family,
        family_label=_FAMILY_LABELS[family],
        program_key=program_key,
        program_label=program_label,
        stage_label=stage_label,
    )


def get_action_label(action: TurnAction | str, *, include_stage: bool = False) -> str:
    """Return a concise label suitable for buttons, reports, and narrative text."""

    presentation = get_action_presentation(action)
    if include_stage and presentation.stage_label:
        return f"{presentation.label}: {presentation.stage_label}"
    return presentation.label


def humanize_action_text(text: str, *, include_stage: bool = False) -> str:
    """Replace embedded action identifiers without changing non-command prose."""

    result = text
    commands = sorted((action.value for action in TurnAction), key=len, reverse=True)
    for command in commands:
        if command not in result:
            continue
        pattern = rf"(?<![A-Za-z0-9_])`?{re.escape(command)}`?(?![A-Za-z0-9_])"
        result = re.sub(
            pattern,
            get_action_label(command, include_stage=include_stage),
            result,
        )
    return result


def classify_action(action: TurnAction | str) -> ActionFamily:
    """Map every internal action into a small player-facing family."""

    command = action.value if isinstance(action, TurnAction) else action
    if command in {TurnAction.WAIT.value, TurnAction.END_TURN.value}:
        return ActionFamily.TURN
    if command.startswith(("review_", "view_")):
        return ActionFamily.REVIEW
    if command in {
        TurnAction.SET_COMPANY_STRATEGY.value,
        TurnAction.SET_ROADMAP.value,
        TurnAction.SET_BUDGET_STANCE.value,
        TurnAction.SET_FUNCTIONAL_BUDGET.value,
    }:
        return ActionFamily.STRATEGY
    if _contains_any(
        command,
        "employee",
        "team",
        "hiring",
        "candidate",
        "manager",
        "succession",
        "comp_review",
    ):
        return ActionFamily.TEAM
    if _contains_any(command, "release", "roadmap_project", "sales_deal", "pipeline"):
        return ActionFamily.DELIVERY
    if _contains_any(
        command,
        "partner",
        "partnership",
        "channel",
        "reseller",
        "integration",
        "marketplace",
    ):
        return ActionFamily.PARTNERS
    if _contains_any(
        command,
        "board",
        "restructure",
        "endgame",
        "exit_",
        "path_",
        "terminal_",
        "solvency",
    ):
        return ActionFamily.BOARD_EXIT
    if _contains_any(
        command,
        "loan",
        "debt",
        "capital",
        "reserve",
        "angel",
        "raise_vc",
        "financing",
        "covenant",
        "balance_sheet",
        "liquidity",
    ):
        return ActionFamily.FINANCE
    if _contains_any(
        command,
        "support",
        "backlog",
        "lane_",
        "white_glove",
        "onboarding",
        "billing",
        "enterprise_reference",
        "enterprise_renewal",
        "enterprise_commitment",
        "enterprise_queue",
        "enterprise_assurance",
        "reference_rescue",
    ):
        return ActionFamily.OPERATIONS
    if _contains_any(
        command,
        "customer",
        "account",
        "retention",
        "renewal",
        "win_back",
    ):
        return ActionFamily.CUSTOMERS
    if _contains_any(
        command,
        "market_product",
        "pricing",
        "price_increase",
        "target_segment",
        "packaging",
        "package_",
        "add_on",
    ):
        return ActionFamily.MARKET
    return ActionFamily.PRODUCT


def _action_label(command: str) -> str:
    common = _COMMON_LABELS.get(command)
    if common is not None:
        return common
    label = command.replace("_", " ").title()
    replacements = {
        " Ai ": " AI ",
        " Api ": " API ",
        " Ipo ": " IPO ",
        " Qbr": " QBR",
        " Sla ": " SLA ",
        " Vc ": " VC ",
    }
    padded = f" {label} "
    for source, target in replacements.items():
        padded = padded.replace(source, target)
    return padded.strip()


def _program_for(command: str) -> tuple[str, str, str] | None:
    if command in _CAPITAL_RESILIENCE_COMMANDS:
        return ("capital_resilience", "Capital Resilience", _action_label(command))
    for rule in _PROGRAM_RULES:
        for stem in rule.stems:
            if command.startswith(stem):
                suffix = command.removeprefix(stem)
                stage_label = _action_label(suffix) if suffix else ""
                return (rule.key, rule.label, stage_label)
    return None


def _contains_any(command: str, *fragments: str) -> bool:
    return any(fragment in command for fragment in fragments)
