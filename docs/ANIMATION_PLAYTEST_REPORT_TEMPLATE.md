# Animation Playtest Report Template

Use this template when completing the open-window animation pass. Prefer generating a fresh strict draft first:

```bash
uv run nexus-tech draft-animation-playtest-report --prefill-automated-gates --output /tmp/nexus-tech-animation-playtest-report.md
uv run nexus-tech animation-playtest-status /tmp/nexus-tech-animation-playtest-report.md
uv run nexus-tech animation-playtest-commands --output /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech validate-animation-playtest-commands /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech animation-playtest-plan /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md --output /tmp/nexus-tech-animation-playtest-plan.md
uv run nexus-tech animation-playtest-recorder-queue /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md --output /tmp/nexus-tech-animation-recorder-queue.md
uv run nexus-tech validate-animation-playtest-recorder-queue /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech animation-playtest-route-batches /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md --output /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech validate-animation-playtest-route-batches /tmp/nexus-tech-animation-route-batches.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech validate-animation-playtest-plan /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md
uv run nexus-tech prepare-animation-playtest-session --prefill-automated-gates --plan-output /tmp/nexus-tech-animation-playtest-plan.md --recorder-output /tmp/nexus-tech-animation-recorder-queue.md --route-batches-output /tmp/nexus-tech-animation-route-batches.md --triage-output /tmp/nexus-tech-animation-ui-triage.md --handoff-output /tmp/nexus-tech-animation-handoff.md
uv run nexus-tech validate-animation-playtest-session /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md --route-batches /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech animation-playtest-handoff /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md --route-batches /tmp/nexus-tech-animation-route-batches.md --output /tmp/nexus-tech-animation-handoff.md
uv run nexus-tech animation-playtest-ui-triage /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md --route-batches /tmp/nexus-tech-animation-route-batches.md --output /tmp/nexus-tech-animation-ui-triage.md
uv run nexus-tech validate-animation-playtest-ui-triage /tmp/nexus-tech-animation-ui-triage.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md --route-batches /tmp/nexus-tech-animation-route-batches.md
```

If the tester shell does not have `uv`, add
`--command-prefix .venv313/bin/nexus-tech` to the command queue, command
validation, plan, recorder queue, route-batches, route-batch validation, UI
triage, UI triage validation, plan validation, session setup, session
validation, and handoff commands so the exported visible-window route uses the
same launcher the tester can actually run.

Use the UI triage artifact to keep layout, typography, control, scene, motion,
and signoff issues separated into P0/P1/P2 lanes before the next polish pass.

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
The exported plan includes a validated `Visible Test Route` so testers know
which menu/play window and motion runs map to which evidence notes.
It also includes a validated `Manual Runbook` so testers keep the artifact
refresh, visible-window execution, evidence-fill, and final validation order.
Validate the exported plan after writing it so the attached plan cannot drift
from the current report or command queue.
Export and validate the recorder queue before handoff so every open manual row
has a safe recorder command with observation placeholders.
The session setup command creates the report, command queue, grouped plan, and
recorder queue together, plus a handoff sheet that points at the next visible
command and recorder command. It still leaves manual rows incomplete until real
observations are entered.
Run session validation after setup or edits so stale package artifacts fail
before a tester starts the visible-window pass.
The final report must keep the generated `Visible Route Evidence` table and fill
all 18 menu/play rows with `pass` plus observed notes from the matching window
and motion mode.
Prefer `record-animation-playtest-route` after each visible route and
`record-animation-playtest-window` after each three-mode window pass so the
report table format stays valid. Use `record-animation-playtest-control`,
`record-animation-playtest-scene`, `record-animation-playtest-feedback`, and
`record-animation-playtest-field` for the remaining manual rows and signoff
fields. The commands update only the selected row or field, reject generic
notes, and enforce the required evidence terms checked by final validation.
Run those recorder commands sequentially for one report file; do not update the
same report from multiple terminals at once.
Do not replace route notes with generic summaries. Menu rows must mention title,
wizard, save, archive, meta, hover, and text observations; play rows must
mention dashboard, action, pending, inspector, endgame, summary, pause, and
motion observations.
The final validator rejects generic evidence notes such as `ok`, `clear`,
`readable`, `stable`, or `none` in gate, window, control, scene, and game-feel
evidence cells. Record concise observed facts instead, such as which window,
control path, scene element, or motion cue was checked.
It also checks target-specific observed terms for window matrix, control, scene,
and game-feel evidence rows, so completed reports must name the actual UI,
motion, control, or feedback behavior verified in that row.
Generated report drafts include `Pass notes must mention: ...` prompts in those
manual rows; replace the prompt text with real observations that still include
the required terms before final validation. The validator treats leftover prompt
text as missing evidence, including route-recording prompts and automated-gate
`Record command output...` placeholders.
For a `pass` release decision, release blocker fields and required fixes must
be clear, and `Validator result` must be a passing value.
Keep all generated section headings in the completed report. The validator
requires Build, automated gate, window matrix, visible route, control, scene,
game-feel, release blocker, and decision sections to remain present.
Remove the draft warning paragraph and replace any `owner/date if not pass`
follow-up placeholders before final validation.

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

## Visible Route Evidence

| Step | Target | Window | Motion | Result | Evidence Notes |
| ---: | --- | --- | --- | --- | --- |
| 1-18 |  |  |  |  | Keep the generated rows from `draft-animation-playtest-report` and replace each result/note with real observations |

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

Run `validate-animation-playtest-report` only after every automated gate, window/motion cell, control row, scene row, and game-feel row is filled with real evidence. For a `pass` release decision, validator expects these rows to be `pass` with non-generic evidence notes; use `watch` or `fail` only when the build is not being cleared for presentation.
