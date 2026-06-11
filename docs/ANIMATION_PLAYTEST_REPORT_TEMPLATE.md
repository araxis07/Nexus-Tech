# Animation Playtest Report Template

Use this template when completing the open-window animation pass. Keep completed reports as dated copies only when they contain real tester observations.

## Build

- Version:
- Commit:
- Tester:
- Date:
- Platform:

## Automated Gate Summary

| Gate | Result | Notes |
| --- | --- | --- |
| `ruff check src tests` |  |  |
| `pytest tests/test_frontend_2d.py -q` |  |  |
| `pytest -q` |  |  |
| `audit-2d-motion` full/reduced/off |  |  |
| `audit-2d-visual` full/off |  |  |
| `audit-2d-animation` |  | Confirm `Actor State Coverage`, `Readability Guard`, `Scene Motion Profile`, `Animation Pacing Budget`, `Long Session Motion Stress`, `Visual Fatigue Budget`, and `actor-readability` pass |
| `audit-2d-animation-matrix --output` |  | Confirm the seven-scenario, three-seed local or CI readiness artifact passes before manual timing review |
| Headless `menu-2d` / `play-2d` |  |  |
| Open-window `menu-2d` / `play-2d` smoke |  |  |

## Window Matrix

| Window | Full | Reduced | Off | Notes |
| --- | --- | --- | --- | --- |
| `820x620` |  |  |  |  |
| `960x640` |  |  |  |  |
| `1440x900` |  |  |  |  |

## Scene Results

| Scene | Result | Readability Notes | Motion Notes | Follow-up |
| --- | --- | --- | --- | --- |
| Title/Menu |  |  |  |  |
| Live Dashboard |  |  |  |  |
| Action Picker |  |  |  |  |
| Pending Event |  |  |  |  |
| Inspector |  |  |  |  |
| Endgame Board |  |  |  |  |
| Turn Summary |  |  |  |  |
| Outcome/Review |  |  |  |  |

## Release Blockers

- Hidden primary actions:
- Unreadable disabled reasons:
- Actor, tooltip, footer, modal, or button collisions:
- Missing or unclear actor state reactions:
- Motion-mode regressions:
- CI artifact anomalies:
- `visual-audit-summary.md` anomalies:
- `animation-readiness-matrix.md` anomalies:

## Decision

- Release decision: `pass` / `watch` / `fail`
- Required fixes before presenting:
- Nice-to-have polish:
