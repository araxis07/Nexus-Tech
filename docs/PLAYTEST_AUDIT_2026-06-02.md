# 2D Playtest Audit

Date: `2026-06-02`  
Version under audit: `0.103.0`

## Scope

- `pytest -q tests/test_frontend_2d.py`
- `nexus_tech.cli play-2d --headless --max-frames 4 --scenario founder_journey --seed 11`
- `nexus_tech.cli menu-2d --headless --max-frames 4`
- code-level review of `RunScene` event-feed, footer, and inspector focus behavior

## Friction Findings

1. Reopening late-game panels and replaying similar cockpit moves could stack identical event cards, which made the feed noisier than the underlying decision change.
2. The action-bar footer still leaned too heavily on static hotkey text and did not explain the current workspace or modal layer clearly enough during picker, inspector, and pending-event flows.
3. Inspector row selection worked functionally, but the selected record still blended too easily into the surrounding list during longer sessions.

## Fix Summary

- Duplicate frontend events with the same title, detail, and severity now refresh in place instead of stacking repeatedly in the feed.
- The footer now exposes contextual status lines for workspace, picker, inspector, text-input, and pending-event states before it falls back to the generic hotkey legend.
- Selected inspector rows now get a stronger fill treatment plus an `ACTIVE` badge to improve scanning speed during larger board, pipeline, and endgame inspections.

## Verification Snapshot

- `tests/test_frontend_2d.py`: passed with new coverage for duplicate-event coalescing and contextual footer status lines
- `play-2d --headless --max-frames 4`: passed
- `menu-2d --headless --max-frames 4`: passed

## Remaining Risk

- This is still a scripted/headless audit, not a human visual session with freeform clicking.
- Motion density in very long late-game sessions may still need one more tuning pass after real human play.
