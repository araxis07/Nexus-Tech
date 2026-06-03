# 2D Action Motion Audit

Date: `2026-06-03`
Version under audit: `0.109.0`

## Scope

- surfaced commands from `Guided Opening`
- surfaced commands from `Turn Coach`
- surfaced commands from `Risk Forecast`
- path-gate and exit commands from endgame pressure / outcome evaluation
- deep-panel action commands exposed by the 2D frontend

## Coverage Snapshot

- actionable surfaced commands audited: `43`
- `specific` choreography coverage: `35`
- `family` choreography coverage: `8`
- uncovered `none` commands: `0`

## Specific Coverage Highlights

- review/report lane: `review_board`, `review_finance`, `review_customers`, `review_partnerships`, `review_pipeline`, `review_team`, `view_report`
- late-game gate lane: `start_board_recovery_plan`, `set_board_reset_contingency_buffer`, `set_path_cash_waterfall`, `execute_board_response`
- build / product lane: `create_product`, `improve_quality`, `reduce_technical_debt`, `plan_release`, `work_release`, `start_roadmap_project`, `work_roadmap_project`
- hiring lane: `source_candidates`, `screen_candidate`, `interview_candidate`, `make_hiring_offer`, `hire_employee`, `assign_employee`, `train_employee`, `reorg_team`
- commercial / pricing lane: `create_sales_deal`, `advance_sales_deal`, `adjust_pricing`, `set_packaging_strategy`, `set_target_segment`
- finance / budget lane: `set_capital_plan`, `set_functional_budget`

## Family Coverage Still In Use

- funding / capital family: `take_loan`, `raise_angel`, `repay_debt`
- restructure / partner family: `execute_restructure_plan`, `rebalance_channel_mix`, `renegotiate_partnership`, `run_partner_recovery_sprint`
- customer-support family: `run_billing_stabilization`

These commands already animate through focused family motion and panel targets, but they are still candidates for future command-specific choreography if the playtest shows they need a more distinct visual signature.

## Regression Guardrails

- `tests/test_frontend_2d.py::test_surfaced_2d_commands_have_motion_coverage`
- `tests/test_frontend_2d.py::test_high_priority_2d_commands_use_specific_motion_profiles`

These tests keep surfaced commands from silently dropping back to `none` coverage and keep the late-game / review / finance lane from regressing to generic-only motion.
