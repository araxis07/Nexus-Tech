# Performance Audit - 2026-06-04

Version: `0.116.0`

## Scope

- Added a deterministic `audit-2d-motion` CLI gate for the animated 2D frontend.
- The audit stresses the live run and staged turn summary with dense pulse banks across `820x620`, `960x640`, and `1280x720` viewports.
- Each viewport reports pulse-bank cooldown before/after counts and average draw/update frame time.

## Stability Budgets

- Live run target: cool residual pulse banks to `<= 18` live pulses.
- Turn summary target: cool residual pulse banks to `<= 12` live pulses.
- Frame target: average fixed-step update/draw time at or below `24 ms`.
- Watch threshold: up to `33 ms` or slightly elevated pulse banks without failing the release gate.

## Verification Commands

- `nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 2`
- `pytest -q tests/test_frontend_2d.py -k "motion_audit or audit_2d_motion"`

## Result

The new audit makes long-session animation stability repeatable in CI/local release checks instead of relying only on manual visual playtesting.
