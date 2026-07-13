"""Player-facing names and families for internal turn actions."""

from __future__ import annotations

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

_TIERED_LABEL_STEMS = {
    "run_enterprise_reference_": "Enterprise Reference",
    "run_billing_liquidity_": "Billing Liquidity",
    "run_onboarding_continuity_": "Onboarding Continuity",
    "run_channel_durability_": "Channel Durability",
    "set_terminal_solvency_": "Terminal Solvency",
    "run_white_glove_reference_": "White-glove Reference",
}


def get_action_presentation(action: TurnAction | str) -> ActionPresentation:
    """Return readable metadata without exposing raw snake-case commands."""

    command = action.value if isinstance(action, TurnAction) else action
    family = classify_action(command)
    return ActionPresentation(
        command=command,
        label=_action_label(command),
        family=family,
        family_label=_FAMILY_LABELS[family],
    )


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
    for stem, title in _TIERED_LABEL_STEMS.items():
        if command.startswith(stem):
            tier = command.removeprefix(stem).replace("_", " ").title()
            return f"{title}: {tier}"
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


def _contains_any(command: str, *fragments: str) -> bool:
    return any(fragment in command for fragment in fragments)
