# 2D Flow Audit - 2026-06-02

This pass closed the gap between isolated UI motion and full turn flow choreography.

## Scope

- Added action-specific choreography events for the most common product, hiring, pipeline, pricing, and partnership commands.
- Added animated overlay emphasis for deep panels, inspectors, pickers, text input, help, and pending-event layers.
- Added turn-summary handoff back to the live run so the next-focus command seeds both the event feed and the matching workspace panel.

## Practical outcome

- `RunScene` now reacts before and after commands instead of only after state diffs land.
- `TurnSummaryScene` no longer feels detached from the live dashboard; it returns the player to the panel most relevant to the next command.
- Regression coverage now locks the choreography cards, overlay motion triggers, and turn-summary return focus.

## Remaining gaps

- More action-specific choreography can still be added for advanced board, recovery, and enterprise flows.
- Title-scene overlays still use a simpler transition model than the in-run shell.
- Manual playtests are still needed to tune animation timing and noise across long runs.
