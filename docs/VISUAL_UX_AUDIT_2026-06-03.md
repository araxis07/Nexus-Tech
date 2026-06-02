# 2D Visual UX Audit

Date: `2026-06-03`
Version under audit: `0.104.0`

## Scope

- `pytest -q tests/test_frontend_2d.py`
- direct `RunScene` inspection of footer state, cockpit tooltip wording, and inspector focus summaries
- `nexus_tech.cli play-2d --headless --max-frames 4 --scenario founder_journey --seed 11`
- `nexus_tech.cli menu-2d --headless --max-frames 4`

## Friction Findings

1. Late-game players still had to infer the current gate and hotspot command from the endgame panel body instead of getting that context directly in the footer status line.
2. Cockpit button hover text still said only “run command” and did not clearly explain where the action would hand off next.
3. Inspector focus improved with the `ACTIVE` badge, but the player still had to infer whether the selected row’s primary action was immediately usable or blocked.

## Fix Summary

- Endgame footer context now surfaces both the current gate command and hotspot command directly in the action-bar status line.
- Cockpit hover hints now explicitly name the workspace that the action will hand off into.
- Selected inspector rows now show a `READY` or `BLOCKED` chip for the primary action, and the focus note/status line now includes the next action or blocked prerequisite.

## Verification Snapshot

- `tests/test_frontend_2d.py`: passed with new coverage for endgame footer context, cockpit tooltip routing, and inspector primary-action summaries
- `play-2d --headless --max-frames 4`: passed
- `menu-2d --headless --max-frames 4`: passed

## Remaining Risk

- This is still a deterministic scene audit, not a freeform human visual test over a long late-game run.
- Motion density, pacing, and card hierarchy should still be judged in a real open-window session before calling the 2D frontend beta-ready.
