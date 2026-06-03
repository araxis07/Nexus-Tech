# 2D Action Motion Audit

Date: `2026-06-03`
Version under audit: `0.111.0`

## Scope

- surfaced commands from `Guided Opening`
- surfaced commands from `Turn Coach`
- surfaced commands from `Risk Forecast`
- path-gate and exit commands from endgame pressure / outcome evaluation
- deep-panel action commands exposed by the 2D frontend

## Coverage Snapshot

- actionable surfaced commands audited: `43`
- `specific` choreography coverage: `43`
- `family` choreography coverage: `0`
- uncovered `none` commands: `0`

## Specific Coverage Highlights

- review/report lane: `review_board`, `review_finance`, `review_customers`, `review_partnerships`, `review_pipeline`, `review_team`, `view_report`
- late-game gate lane: `start_board_recovery_plan`, `set_board_reset_contingency_buffer`, `set_path_cash_waterfall`, `execute_board_response`
- build / product lane: `create_product`, `improve_quality`, `reduce_technical_debt`, `plan_release`, `work_release`, `start_roadmap_project`, `work_roadmap_project`
- hiring lane: `source_candidates`, `screen_candidate`, `interview_candidate`, `make_hiring_offer`, `hire_employee`, `assign_employee`, `train_employee`, `reorg_team`
- commercial / pricing lane: `create_sales_deal`, `advance_sales_deal`, `adjust_pricing`, `set_packaging_strategy`, `set_target_segment`
- finance / budget lane: `set_capital_plan`, `set_functional_budget`
- funding / restructure lane: `take_loan`, `raise_angel`, `repay_debt`, `execute_restructure_plan`
- channel recovery lane: `rebalance_channel_mix`, `renegotiate_partnership`, `run_partner_recovery_sprint`, `run_billing_stabilization`

## Surfaced Coverage Status

All currently surfaced 2D commands now resolve to `specific` choreography.

Family motion still exists as a fallback for deeper or currently unsurfaced commands, but the main player-facing control surface no longer depends on it.

## Regression Guardrails

- `tests/test_frontend_2d.py::test_surfaced_2d_commands_have_motion_coverage`
- `tests/test_frontend_2d.py::test_high_priority_2d_commands_use_specific_motion_profiles`
- `tests/test_frontend_2d.py::test_build_action_events_emit_remaining_family_choreography_cards`

These tests keep surfaced commands from silently dropping back to `family` or `none`, while still preserving a verified family-motion fallback for deeper commands that are not yet surfaced in the main 2D loop.

Turn-summary `Gate Command` and `Next Focus` handoffs now also route motion into the concrete workspace lane they reference, so command-specific choreography survives the post-turn summary path instead of collapsing back into generic endgame-only emphasis.
