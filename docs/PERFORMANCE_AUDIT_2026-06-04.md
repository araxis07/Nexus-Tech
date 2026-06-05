# Performance Audit - 2026-06-04

Version: `0.125.0`

## Scope

- Added a deterministic `audit-2d-motion` CLI gate for the animated 2D frontend.
- The audit stresses the live run and staged turn summary with dense pulse banks across `820x620`, `960x640`, and `1280x720` viewports.
- The audit also exercises title/menu motion, save-slot detail, rename/delete overlays, archive/meta/wizard subflows, review-scene motion, inspector overlays, picker overlays, and 2D request-path coverage.
- Inspector interactions now have explicit section, item, page, sort, filter, actionable-focus, and hotspot-focus pulse lanes.
- The 2D shell now supports `--motion-mode full|reduced|off` for launchers and `audit-2d-motion`, with reduced/off modes preserving gameplay while lowering or disabling highlight pulses.
- Scene entry transitions now cover boot, title-to-run, title-to-review, run-to-summary, run-to-review, summary-to-run, summary-to-review, and review-to-title flows.
- Shape-based entity motion now covers stat lanes, product cards, and active deep-panel strips without adding external sprite assets.
- Command-specific action feedback cues now cover successful commands, picker launches, create-product modals, inspector opens, and end-turn confirmation while respecting reduced/off motion modes.
- State-delta impact cue cards now cover successful action results for cash, users, reputation, board pressure, and product metrics while respecting reduced/off motion modes.
- Modal overlay enter/exit transitions now cover pending events, action pickers, text modals, deep panels, inspectors, help, and outcome dialogs.
- Turn summaries now include a cinematic rail that sequences resolution phases before returning to the live run.
- `audit-2d-visual` now renders title, meta, live run, picker/action-feedback, inspector, turn-summary, and review captures to verify non-empty frames plus expected active visual layers before manual review.
- Each viewport reports pulse-bank cooldown before/after counts, transition active/disabled telemetry, entity-motion active/disabled telemetry, action-feedback active/disabled telemetry, impact-cue active/disabled telemetry, overlay-transition telemetry, summary-cinematic telemetry, average frame time, and max frame spike.

## Stability Budgets

- Live run target: cool residual pulse banks to `<= 18` live pulses.
- Turn summary target: cool residual pulse banks to `<= 12` live pulses.
- Title/menu target: keep multi-subflow title and wizard overlay pulse banks to `<= 14` live pulses.
- Review target: keep post-run review pulse banks to `<= 6` live pulses.
- Inspector target: keep interaction pulse banks to `<= 12` live pulses.
- Long-run pressure target: cool repeated dense highlight banks to `<= 18` live pulses.
- Frame target: average fixed-step update/draw time at or below `24 ms`.
- Max frame target: avoid spikes above `50 ms`.
- Watch threshold: up to `33 ms` or slightly elevated pulse banks without failing the release gate.
- Flow target: every surfaced 2D command and inspector item action must either build a request path or return a concrete disabled explanation.

## Verification Commands

- `nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 2`
- `nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 1 --motion-mode reduced`
- `nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 1 --motion-mode off`
- `nexus-tech audit-2d-visual --scenario founder_journey --seed 7`
- `pytest -q tests/test_frontend_2d.py -k "motion_audit or audit_2d_motion or visual_audit or audit_2d_visual"`

## Result

The audit makes animation stability and runtime 2D request coverage repeatable in CI/local release checks instead of relying only on manual visual playtesting.
