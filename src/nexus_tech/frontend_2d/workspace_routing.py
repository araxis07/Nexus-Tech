"""Pure command-to-workspace routing for the 2D frontend."""

from __future__ import annotations

from nexus_tech.domain.models import TurnAction

__all__ = ["workspace_panel_key_for_command"]


_FINANCE_PANEL_COMMANDS = {
    TurnAction.REVIEW_FINANCE.value,
    TurnAction.TAKE_LOAN.value,
    TurnAction.RAISE_ANGEL.value,
    TurnAction.RAISE_VC.value,
    TurnAction.REPAY_DEBT.value,
    TurnAction.REFINANCE_DEBT.value,
    TurnAction.DEBT_ROLLOVER.value,
    TurnAction.REBALANCE_CAPITAL.value,
    TurnAction.RAISE_RESERVE_TARGET.value,
    TurnAction.SET_CAPITAL_PLAN.value,
    TurnAction.SET_REFINANCING_POSTURE.value,
    TurnAction.SET_COVENANT_FIREWALL.value,
    TurnAction.SET_DEBT_STRATEGY.value,
    TurnAction.SET_GROWTH_FIREBREAK.value,
    TurnAction.SET_PATH_CAPITAL_POSTURE.value,
    TurnAction.SET_ENDGAME_CAPITAL_MAP.value,
    TurnAction.SET_EXIT_READINESS_BUFFER.value,
    TurnAction.SET_TERMINAL_LIQUIDITY_CONTROLS.value,
    TurnAction.SET_CAPITAL_REALLOCATION_GRID.value,
    TurnAction.SET_PATH_CONTROL_MATRIX.value,
    TurnAction.SET_PATH_RESILIENCE_GRID.value,
    TurnAction.SET_BALANCE_SHEET_RECOVERY_MESH.value,
    TurnAction.SET_TERMINAL_RECOVERY_LATTICE.value,
    TurnAction.SET_TERMINAL_CONTINUITY_MATRIX.value,
    TurnAction.SET_TERMINAL_RESILIENCE_COVENANT.value,
    TurnAction.SET_TERMINAL_SOLVENCY_STATUTE.value,
    TurnAction.SET_TERMINAL_SOLVENCY_MANDATE.value,
    TurnAction.SET_TERMINAL_SOLVENCY_COMMISSION.value,
    TurnAction.SET_TERMINAL_SOLVENCY_OVERSIGHT.value,
    TurnAction.SET_TERMINAL_SOLVENCY_COUNCIL.value,
    TurnAction.SET_PATH_CASH_WATERFALL.value,
    TurnAction.SET_BOARD_RESET_CONTINGENCY_BUFFER.value,
    TurnAction.STEP_UP_RESERVE_DISCIPLINE.value,
    TurnAction.HARDEN_FINANCING_POSTURE.value,
    TurnAction.LOCK_CAPITAL_BUFFER.value,
}
_TEAM_PANEL_COMMANDS = {
    TurnAction.REVIEW_TEAM.value,
    TurnAction.HIRE_EMPLOYEE.value,
    TurnAction.FIRE_EMPLOYEE.value,
    TurnAction.ASSIGN_EMPLOYEE.value,
    TurnAction.UNASSIGN_EMPLOYEE.value,
    TurnAction.REST_TEAM.value,
    TurnAction.TRAIN_EMPLOYEE.value,
    TurnAction.PROMOTE_EMPLOYEE.value,
    TurnAction.RUN_COMP_REVIEW.value,
    TurnAction.RUN_SUCCESSION_REVIEW.value,
    TurnAction.APPOINT_TEAM_LEAD.value,
    TurnAction.ASSIGN_MANAGER.value,
    TurnAction.CLEAR_MANAGER.value,
    TurnAction.REORG_TEAM.value,
}
_PIPELINE_PANEL_COMMANDS = {
    TurnAction.REVIEW_PIPELINE.value,
    TurnAction.PLAN_RELEASE.value,
    TurnAction.WORK_RELEASE.value,
    TurnAction.CREATE_SALES_DEAL.value,
    TurnAction.ADVANCE_SALES_DEAL.value,
    TurnAction.START_ROADMAP_PROJECT.value,
    TurnAction.WORK_ROADMAP_PROJECT.value,
    TurnAction.SOURCE_CANDIDATES.value,
    TurnAction.SCREEN_CANDIDATE.value,
    TurnAction.INTERVIEW_CANDIDATE.value,
    TurnAction.MAKE_HIRING_OFFER.value,
}
_BOARD_PANEL_COMMANDS = {
    TurnAction.REVIEW_BOARD.value,
    TurnAction.EXECUTE_BOARD_RESPONSE.value,
    TurnAction.START_BOARD_RECOVERY_PLAN.value,
    TurnAction.EXECUTE_RESTRUCTURE_PLAN.value,
}
_CUSTOMER_PANEL_COMMANDS = {
    TurnAction.REVIEW_CUSTOMERS.value,
    TurnAction.ADJUST_PRICING.value,
    TurnAction.SET_PACKAGING_STRATEGY.value,
    TurnAction.SET_TARGET_SEGMENT.value,
    TurnAction.INVEST_IN_CUSTOMER_SUCCESS.value,
    TurnAction.RUN_RETENTION_PLAY.value,
    TurnAction.MAKE_RENEWAL_OFFER.value,
    TurnAction.RUN_WIN_BACK_PLAY.value,
    TurnAction.ROUTE_SUPPORT_ESCALATION.value,
    TurnAction.RUN_ACCOUNT_RESCUE.value,
    TurnAction.RUN_LANE_RECOVERY.value,
    TurnAction.RUN_RENEWAL_SWEEP.value,
    TurnAction.RUN_ENTERPRISE_ASSURANCE.value,
    TurnAction.RUN_BILLING_STABILIZATION.value,
    TurnAction.RUN_ONBOARDING_RECOVERY.value,
    TurnAction.RUN_ONBOARDING_FAST_TRACK.value,
    TurnAction.TRIAGE_SUPPORT_BACKLOG.value,
    TurnAction.INVEST_IN_SUPPORT_STAFFING.value,
    TurnAction.SET_SUPPORT_LANE_FOCUS.value,
    TurnAction.UPGRADE_SUPPORT_PROGRAM.value,
}
_PARTNERSHIP_PANEL_COMMANDS = {
    TurnAction.CREATE_PARTNERSHIP.value,
    TurnAction.INVEST_IN_PARTNER_ENABLEMENT.value,
    TurnAction.RUN_CHANNEL_QBR.value,
    TurnAction.REBALANCE_CHANNEL_MIX.value,
    TurnAction.RENEGOTIATE_PARTNERSHIP.value,
    TurnAction.REACTIVATE_PARTNERSHIP.value,
    TurnAction.PAUSE_PARTNERSHIP.value,
    TurnAction.REVIEW_PARTNERSHIPS.value,
}


def workspace_panel_key_for_command(command: str) -> str | None:
    """Return the deep-dive workspace that owns a player command."""

    if command in _TEAM_PANEL_COMMANDS:
        return "team"
    if command in _FINANCE_PANEL_COMMANDS:
        return "finance"
    if command in _PIPELINE_PANEL_COMMANDS:
        return "pipeline"
    if command in _BOARD_PANEL_COMMANDS:
        return "board"
    if command in _CUSTOMER_PANEL_COMMANDS:
        return "customers"
    if command in _PARTNERSHIP_PANEL_COMMANDS:
        return "partnerships"
    if command == TurnAction.VIEW_REPORT.value:
        return "report"
    if command.startswith(
        (
            "run_enterprise_",
            "run_billing_",
            "run_onboarding_",
            "run_white_glove_",
            "run_reference_",
        )
    ):
        return "customers"
    if command.startswith(
        (
            "run_channel_",
            "run_partner_",
            "run_reseller_",
            "run_integration_",
            "run_marketplace_",
        )
    ):
        return "partnerships"
    return None
