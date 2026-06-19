# Animation Playtest Report Template

Use this template when completing the open-window animation pass. Prefer generating a fresh strict draft first:

```bash
uv run nexus-tech draft-animation-playtest-report --prefill-automated-gates --output /tmp/nexus-tech-animation-playtest-report.md
uv run nexus-tech animation-playtest-status /tmp/nexus-tech-animation-playtest-report.md
uv run nexus-tech animation-playtest-commands --output /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech validate-animation-playtest-commands /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech animation-playtest-plan /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md --output /tmp/nexus-tech-animation-playtest-plan.md
uv run nexus-tech prepare-animation-playtest-session --prefill-automated-gates
```

Keep completed reports as dated copies only when they contain real tester observations.
Use visible `menu-2d` and `play-2d` runs with the exact `--window-size` listed in
each row before filling the window matrix.
The exported command queue is a tester aid only and does not count as manual
signoff evidence by itself.
Validate the exported queue before handoff so missing command rows are fixed
before anyone starts the visible-window pass.
Run the playtest plan command after queue validation to see the remaining manual
areas and signoff fields without digging through raw validator findings. Use
`--output` when the current grouped plan should be attached to the handoff.
The session setup command creates both files together but still leaves manual
rows incomplete until real observations are entered.

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
| `audit-2d-animation` |  | Confirm `Actor State Coverage`, `Action Feedback Clarity`, `Scene Transition Handoff`, `Control Affordance Coverage`, `Control Replay Safety`, `UI Layout Safety`, `Typography Safety`, `Readability Guard`, `Scene Motion Profile`, `Animation Pacing Budget`, `Motion Mode Differentiation`, `Long Session Motion Stress`, `Long Session Visual Readiness`, `Visual Fatigue Budget`, `actor-pose-depth`, and `actor-readability` pass |
| `audit-2d-animation-matrix --output` |  | Confirm the seven-scenario, three-seed, three-window local or CI readiness artifact passes before manual timing review |
| `prepare-2d-animation-playtest --output` |  | Confirm the generated window/motion checklist marks manual result as not completed by automation |
| Balance / long-session preflight |  | Run the balance commands listed in the playtest prep artifact and record whether warnings are intentional pressure or fixes |
| `validate-animation-playtest-report` |  | Run this on the completed report and require PASS before presentation signoff |
| Headless `menu-2d` / `play-2d` |  |  |
| Open-window `menu-2d` / `play-2d` smoke |  |  |

## Window Matrix

| Window | Full | Reduced | Off | Notes |
| --- | --- | --- | --- | --- |
| `820x620` |  |  |  |  |
| `960x640` |  |  |  |  |
| `1440x900` |  |  |  |  |

## Control Clarity Results

| Control Area | Result | Notes | Follow-up |
| --- | --- | --- | --- |
| Pause / Resume |  |  |  |
| Back / Escape |  |  |  |
| Menu Return |  |  |  |
| Help / Hover |  |  |  |
| Control Replay Safety |  |  |  |
| Control Affordance Coverage |  |  |  |
| UI Layout Safety |  |  |  |
| Typography Safety |  |  |  |
| Motion Modes |  |  |  |

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
| Scene Handoffs |  |  |  |  |

## Game Feel Results

| Feedback Area | Result | Notes | Follow-up |
| --- | --- | --- | --- |
| Success Feedback |  |  |  |
| Blocked Feedback |  |  |  |
| Impact Values |  |  |  |
| Actor + Feedback Match |  |  |  |

## Release Blockers

- Hidden primary actions:
- Unreadable disabled reasons:
- Actor, tooltip, footer, modal, or button collisions:
- Missing or unclear actor state reactions:
- Unclear pause, back, help, save, or menu behavior:
- Motion-mode regressions:
- CI artifact anomalies:
- `visual-audit-summary.md` anomalies:
- `animation-readiness-matrix.md` anomalies:
- Balance preflight warnings:

## Decision

- Release decision: `pass` / `watch` / `fail`
- Required fixes before presenting:
- Nice-to-have polish:
- Validator result:

Run `validate-animation-playtest-report` only after every automated gate, window/motion cell, control row, scene row, and game-feel row is filled with real evidence. For a `pass` release decision, validator expects these rows to be `pass`; use `watch` or `fail` only when the build is not being cleared for presentation.
