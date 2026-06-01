# 2D Interaction Audit

Date: `2026-06-02`
Version under audit: `0.98.0`

## Scope

- `pytest -q tests/test_frontend_2d.py`
- `play-2d --headless --max-frames 4 --scenario founder_journey --seed 11`
- `menu-2d --headless --max-frames 4`
- direct `RunScene` interaction checks for inspector reopen behavior, actionable/hotspot focus hotkeys, and command-to-workspace routing

## Friction Findings Addressed In 0.98.0

- Reopening an inspector used to reset section, page, row focus, and sort/filter state every time. This made pipeline, board, and report review loops noisier than necessary in larger runs.
- Major 2D commands could launch valid pickers without first bringing the related deep panel into focus, which made late-game cockpit and coach actions feel detached from the workspace they were modifying.
- Inspectors already had sort and filter controls, but there was no one-step path to "show me actionable rows" or "show me the highest-risk hotspot now".

## Fix Summary

- Added per-panel inspector memory so reopening a panel restores the previous section, page, selected row, sort mode, and filter mode.
- Added `A Actionable` and `H Hotspot` inspector shortcuts, exposed both as hotkeys and clickable controls in the inspector sidebar.
- Added workspace routing so finance, customer, partnership, team, board, pipeline, and report commands now preselect the matching deep panel before opening a picker, inspector, or direct action flow.

## Verification Snapshot

- `tests/test_frontend_2d.py`: passed with new coverage for inspector memory restore, actionable/hotspot focus hotkeys, and finance workspace routing.
- Remaining full-suite verification is handled in the standard release pass for the same version bump.

## Remaining Risk

- This audit is scripted and headless, not a human visual play session.
- A real manual 2D playtest is still needed to judge click discoverability, reading speed in the staged turn summary, and how obvious the new inspector shortcuts feel without prior explanation.
