# 2D Motion Audit

Date: `2026-06-02`
Version under audit: `0.99.0`

## Scope

- `pytest -q tests/test_frontend_2d.py`
- `play-2d --headless --max-frames 4 --scenario founder_journey --seed 11`
- `menu-2d --headless --max-frames 4`
- direct frontend checks for action-event motion targeting, run-scene pulse activation, and staged summary emphasis

## Motion Findings Addressed In 0.99.0

- The 2D shell previously animated gauge values and staged turn summaries, but most live actions still landed as silent state changes plus plain event text.
- Run-scene widgets did not share one motion language. Product cards, event cards, panels, and summary cards each moved differently or not at all.
- Action and turn-resolution events had no explicit UI targets, which forced the frontend to infer meaning from text or ignore many state changes visually.

## Fix Summary

- Added a pulse bank for short-lived highlights and wired it into the live run scene plus the staged turn-summary scene.
- Added motion metadata and UI targets to frontend events so stat deltas, product deltas, board/endgame alerts, and summary timeline events can animate the related widgets directly.
- Added shared emphasis styling to panels, buttons, and progress bars so product cards, action-bar panels, event cards, and summary cards now react with the same visual grammar.

## Verification Snapshot

- `tests/test_frontend_2d.py` now covers motion-target emission, endgame timeline targeting, and pulse activation after a live action request.
- Headless 2D smoke runs still close cleanly after the motion changes.

## Remaining Risk

- This pass improves UI/game-feel animation, not character/sprite animation.
- A human playtest is still needed to tune animation speed, stacking behavior during rapid actions, and whether endgame/report emphasis is readable rather than distracting.
