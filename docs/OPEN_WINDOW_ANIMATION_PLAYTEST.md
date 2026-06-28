# Open-Window Animation Playtest

Use this framework after headless CI gates pass. The goal is to judge motion feel, text readability, and control clarity that automated captures cannot fully score.

## Required Preflight

Run these first and stop if any command fails:

```bash
uv run nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 2
uv run nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 1 --motion-mode reduced
uv run nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 1 --motion-mode off
uv run nexus-tech audit-2d-visual --scenario founder_journey --seed 7 --viewport 820x620 --viewport 960x640 --viewport 1440x900 --output-dir /tmp/nexus-tech-visual-audit/full
uv run nexus-tech audit-2d-visual --scenario founder_journey --seed 7 --motion-mode off --viewport 820x620 --viewport 960x640 --viewport 1440x900 --output-dir /tmp/nexus-tech-visual-audit/off
uv run nexus-tech audit-2d-animation --scenario founder_journey --seed 7 --frames 1
uv run nexus-tech audit-2d-animation-matrix --frames 1 --output /tmp/nexus-tech-animation-matrix.md
uv run nexus-tech prepare-2d-animation-playtest --frames 1 --output /tmp/nexus-tech-animation-playtest-prep.md
uv run nexus-tech draft-animation-playtest-report --prefill-automated-gates --output /tmp/nexus-tech-animation-playtest-report.md
uv run nexus-tech animation-playtest-status /tmp/nexus-tech-animation-playtest-report.md
uv run nexus-tech animation-playtest-commands --output /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech validate-animation-playtest-commands /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech animation-playtest-plan /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md --output /tmp/nexus-tech-animation-playtest-plan.md
uv run nexus-tech animation-playtest-recorder-queue /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md --output /tmp/nexus-tech-animation-recorder-queue.md
uv run nexus-tech validate-animation-playtest-recorder-queue /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech animation-playtest-next /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech animation-playtest-recorder-next /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech animation-playtest-route-batches /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md --output /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech validate-animation-playtest-plan /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md
uv run nexus-tech prepare-animation-playtest-session --prefill-automated-gates --plan-output /tmp/nexus-tech-animation-playtest-plan.md --recorder-output /tmp/nexus-tech-animation-recorder-queue.md --handoff-output /tmp/nexus-tech-animation-handoff.md
uv run nexus-tech validate-animation-playtest-session /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md
uv run nexus-tech animation-playtest-handoff /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md --output /tmp/nexus-tech-animation-handoff.md
```

If the shell does not have `uv`, add `--command-prefix .venv313/bin/nexus-tech`
to `animation-playtest-commands`, `validate-animation-playtest-commands`,
`animation-playtest-plan`, `animation-playtest-next`,
`animation-playtest-recorder-queue`, `validate-animation-playtest-recorder-queue`,
`animation-playtest-recorder-next`,
`animation-playtest-route-batches`, `validate-animation-playtest-plan`,
`prepare-animation-playtest-session`, and `validate-animation-playtest-session`,
and `animation-playtest-handoff`.
The command queue and validators must use the same prefix.

Do not commit generated PNG captures or local readiness reports. Use `/tmp/nexus-tech-visual-audit`, `/tmp/nexus-tech-animation-matrix.md`, and `/tmp/nexus-tech-animation-playtest-prep.md` locally or the `nexus-tech-2d-visual-audit`, `nexus-tech-2d-animation-matrix`, and `nexus-tech-2d-animation-playtest-prep` GitHub Actions artifacts for review. Start with each `visual-audit-contact-sheet-WIDTHxHEIGHT.png`, then use `visual-audit-summary.md`, the animation matrix Markdown, and the playtest prep report before opening individual PNG captures.

The generated playtest prep report also lists balance and long-session preflight commands. Run those before the visible-window pass; any balance `watch` or `fail` should be fixed or explicitly named as intentional scenario pressure before adding more animation layers.

After filling the generated manual report draft, validate it before calling animation complete:

```bash
uv run nexus-tech validate-animation-playtest-report /tmp/nexus-tech-animation-playtest-report.md
```

The completed report must include `Visible Route Evidence` for all 18 menu/play
launches from the command queue. Each route row must be `pass` with observed
notes naming what was checked in that window and motion mode.
Menu route notes must explicitly cover title/menu, wizard, save-slot, archive,
meta-board, hover, and text-fit observations. Play route notes must explicitly
cover dashboard, action picker, pending event, inspector, endgame, summary,
pause/back, and motion-feel observations.

Use `animation-playtest-status` during the manual pass to group remaining work
without failing by default. Use `validate-animation-playtest-report` as the final
blocking gate after the visible-window rows and signoff fields are filled.
Use `animation-playtest-commands` to print or export the exact visible-window
command queue with the evidence prompt each row must record; it does not mark
any manual row complete.
Use `validate-animation-playtest-commands` before handoff so an edited queue
cannot silently skip a window size, motion mode, menu run, play run, or route
evidence prompt.
Use `animation-playtest-plan` after validating the queue to combine the current
report gaps and command queue status into one grouped next-step plan. The plan
also includes a validated `Visible Test Route` with all 18 menu/play window and
motion runs plus the evidence each step should record, and a validated
`Manual Evidence Checklist` for window, route, control, scene, game-feel, and
signoff evidence. It also includes a validated `Manual Runbook` for artifact
refresh, visible-window execution, evidence-fill, and final validator exit
criteria. Add `--output /tmp/nexus-tech-animation-playtest-plan.md` when you
need a handoff artifact.
Use `animation-playtest-next` when you need the shortest possible next action:
it reads the current report and command queue, then prints the next evidence
area and first visible-window command still called out by validation. It does not
mark manual signoff complete.
Use `animation-playtest-recorder-queue` before handoff or during long manual
passes to refresh every currently incomplete recorder command with visible
commands, required evidence terms, and placeholders that must be replaced by real
tester observations. `prepare-animation-playtest-session` also generates this
recorder queue when `--recorder-output` is supplied or left at its default.
Use `validate-animation-playtest-recorder-queue` after exporting the recorder
queue so stale row counts, visible commands, required terms, prompts, or recorder
commands fail before the tester starts recording evidence.
Use `animation-playtest-recorder-next` after a visible-window run to print the
safe recorder command for the next incomplete report row. The generated recorder
command intentionally contains a notes placeholder that must be replaced with
real observed evidence before it can be used as signoff.
Use `animation-playtest-route-batches` before or during the visible pass when a
tester needs the 18 menu/play route commands grouped by target window with each
matching recorder command beside it. The exported batch plan is a runner aid, not
signoff evidence.
After running a visible command, use the recorder commands to update the report
without hand-editing table pipes:

```bash
uv run nexus-tech record-animation-playtest-route /tmp/nexus-tech-animation-playtest-report.md 1 --result pass --notes "Observed title wizard save archive meta hover and text behavior at 820x620 full without clipped labels."
uv run nexus-tech record-animation-playtest-window /tmp/nexus-tech-animation-playtest-report.md 820x620 --full pass --reduced pass --off pass --notes "Observed menu and play primary controls with disabled-state labels; layout remained clean and motion stayed readable."
uv run nexus-tech record-animation-playtest-control /tmp/nexus-tech-animation-playtest-report.md "Pause / Resume" --result pass --notes "Observed pause modal opens from the run and resume returns to the same run state."
uv run nexus-tech record-animation-playtest-scene /tmp/nexus-tech-animation-playtest-report.md "Title/Menu" --result pass --readability-notes "Observed wizard and save controls stayed visible on the title menu." --motion-notes "Observed title actor motion and label emphasis stayed readable."
uv run nexus-tech record-animation-playtest-feedback /tmp/nexus-tech-animation-playtest-report.md "Success Feedback" --result pass --notes "Observed success feedback names the target and changed metric before fading."
uv run nexus-tech record-animation-playtest-field /tmp/nexus-tech-animation-playtest-report.md "Commit" --value "$(git rev-parse --short HEAD)"
```

These recorder commands only update the selected row and then print grouped
remaining work. They reject generic notes such as `ok` and also enforce the
required evidence terms that the final validator checks.
Run recorder commands sequentially for a single report file; do not update the
same report from multiple terminals at once.
Use the same `--command-prefix` value across queue generation, validation,
planning, and next-action commands when the visible-window commands should use a
local launcher such as `.venv313/bin/nexus-tech` instead of `uv run nexus-tech`.
Use `validate-animation-playtest-plan` after writing the plan artifact so stale
status, open-item counts, missing visible-route rows, missing checklist rows, or
missing runbook/manual-result guards are caught before handoff.
Use `prepare-animation-playtest-session` when you want the strict report draft,
command queue, grouped plan artifact, recorder queue, and artifact validation
created together before handing the manual pass to a tester. It also writes a
handoff sheet when `--handoff-output` is supplied or left at its default.
Use `validate-animation-playtest-session` immediately before handoff or after
editing artifacts so the report, command queue, grouped plan, and recorder queue
are checked as one package. A fresh incomplete manual report can still return a
manual-required handoff status; only stale or missing artifacts block the session
validator.
Use `animation-playtest-handoff` to print or write the current handoff sheet with
artifact status, the next manual area, the next visible command, and the matching
recorder command. It still uses placeholders and does not complete signoff.
Report notes must be observed evidence, not generic placeholders. The validator
rejects broad notes like `ok`, `clear`, `readable`, or `stable` in evidence
cells because those do not prove which window, control path, scene, or motion cue
was actually checked.
The final report validator also requires target-specific observed terms in
window matrix, control, scene, and game-feel evidence rows, not only the visible
route table.
The generated report draft prints `Pass notes must mention: ...` in those rows;
use it as a checklist, then replace it with actual observed evidence. Final
validation treats leftover prompt text or `Record ...` placeholders as missing
evidence.
For a final `pass`, all release-blocker fields must be clear, `Required fixes
before presenting` must be clear, and `Validator result` must be pass.
Do not delete generated report sections while filling observations; final
validation requires the build, gate, window, route, control, scene, game-feel,
blocker, and decision sections to remain present.
Remove draft warning text and `owner/date if not pass` placeholders before final
validation.

Use `--window-size` instead of hand-resizing windows during the manual pass:

```bash
uv run nexus-tech menu-2d --window-size 820x620 --motion-mode full
uv run nexus-tech play-2d --scenario founder_journey --seed 7 --window-size 820x620 --motion-mode full
uv run nexus-tech play-2d --scenario founder_journey --seed 7 --window-size 960x640 --motion-mode reduced
uv run nexus-tech play-2d --scenario founder_journey --seed 7 --window-size 1440x900 --motion-mode off
```

The draft command can prefill automated gate rows only after local or CI preflight
has passed. The validator is strict for presentation signoff: every window/motion
cell, every control row, every scene row, every game-feel row, and every
release-blocker field still needs real tester input. A `pass` release decision
requires those rows to be `pass`; use `watch` or `fail` when any item still needs
owner follow-up.
Generic evidence notes such as `ok`, `clear`, `readable`, `stable`, or `none`
are blockers for presentation signoff.

## Window Matrix

Test these windows before presenting the 2D build:

| Window | Purpose | Required Result |
| --- | --- | --- |
| `820x620` | Minimum compact layout pressure | No actor, tooltip, footer, modal, or button text collision |
| `960x640` | Small laptop / demo window | Dense scenes remain readable without waiting for motion to settle |
| `1440x900` | Default large-window presentation | Motion feels intentional and does not leave empty dead zones |

## Motion-Mode Matrix

Run the open-window flows in each mode:

```bash
uv run nexus-tech menu-2d --motion-mode full
uv run nexus-tech play-2d --scenario founder_journey --seed 7 --motion-mode full
uv run nexus-tech play-2d --scenario founder_journey --seed 7 --motion-mode reduced
uv run nexus-tech play-2d --scenario founder_journey --seed 7 --motion-mode off
```

| Mode | Required Result |
| --- | --- |
| `full` | Feels alive, but every primary action and next-step hint is readable within five seconds |
| `reduced` | Still communicates state changes, with calmer pulses and less visual competition |
| `off` | Removes actor timeline, sprite clips, pulses, transitions, cinematic lanes, and action feedback motion while controls still work |

## Scene Checks

Record `pass`, `watch`, or `fail` for each scene:

| Scene | Check |
| --- | --- |
| Title/Menu | Wizard, save slots, archives, meta board, archive comparison signals, and title actors never hide copy or actions |
| Live Dashboard | Founder/team/customer/board/product actors do not cover stat chips, product cards, or action buttons |
| Action Picker | Picker cards, path-specific late-game choreography, and action feedback do not compete for the same focal point |
| Pending Event | Preview motion clarifies the choice instead of distracting from option text |
| Inspector | Selected row, pager, status chips, item action, actor routing, and footer line remain readable |
| Endgame Board | Path-fix buttons and hotspot review remain primary while cockpit motion stays secondary |
| Turn Summary | Timeline cards reveal at a readable pace and actor clips support rather than cover metrics |
| Outcome/Review | Victory/shutdown cinematic reads as the final state and review actors do not hide after-action notes |

## Control Clarity Checks

Record `pass`, `watch`, or `fail` for each control area before calling the animation pass complete:

| Control Area | Check |
| --- | --- |
| Pause / Resume | `P` and the Pause rail open the pause modal; Resume returns to the same run state |
| Back / Escape | `Esc` closes overlays first, then opens pause; it does not accidentally quit live play |
| Menu Return | Pause -> Menu saves and returns to the 2D title shell when the run has a title shell |
| Help / Hover | `F1`, `?`, hover tooltips, and hand cursor feedback make clickable controls obvious |
| Control Affordance Coverage | Visual and animation audits expose title, run, outcome, summary, review, pause, back, help, save, and flow controls from click targets |
| Control Replay Safety | Animation audit replays pause, resume, Escape/back, help, hover-copy, save, and title-menu return paths before human control-feel review |
| UI Layout Safety | Visual and animation audits confirm click targets stay in-bounds, large enough, non-overlapping, and clear of actor sprites |
| Typography Safety | Visual and animation audits flag severe button-title fitting, hidden text lines, and wrapped-text clamps before human readability review |
| Motion Modes | Full, reduced, and off modes keep the same clickable actions and readable labels |
| Actor Poses | Actor cards show distinct blocked, warning, build, handoff, coaching, deal, and win poses without covering card copy |
| Game Feel | Success, blocked, and impact feedback identify the changed target before the cue fades |
| Scene Handoffs | Boot, run, summary, and review transitions orient the player without hiding navigation |

## Failure Rules

- Any hidden primary action is a release blocker.
- Any unreadable disabled reason is a release blocker.
- Any actor/readability collision at `820x620` is a release blocker.
- Any missing/unclear blocked actor state is a release blocker.
- Any missing `actor-pose-depth` cue or unclear actor body-language cue is a release blocker.
- Any unclear success target, blocked reason, impact value, or actor/feedback mismatch is a release blocker.
- Any late-game repair cue that does not identify the correct IPO, M&A, independence, or reset target lane is a release blocker.
- Any missing/unclear scene handoff transition or transition active in motion-mode off is a release blocker.
- Any unclear pause, back, help, save, or menu behavior is a release blocker.
- Any `Actor State Coverage`, `Action Feedback Clarity`, `Scene Transition Handoff`, `Control Affordance Coverage`, `Control Replay Safety`, `UI Layout Safety`, `Typography Safety`, `Readability Guard`, `Animation Pacing Budget`, `Motion Mode Differentiation`, `Long Session Motion Stress`, `Long Session Visual Readiness`, `Scene Motion Profile`, `Visual Fatigue Budget`, `actor-pose-depth`, or `actor-readability` audit failure is a release blocker.
- Any `audit-2d-animation-matrix` failure in the default seven-scenario, three-seed presentation set is a release blocker.
- Any incomplete or unvalidated manual playtest report is a release blocker for presentation builds.
- Any unexplained balance preflight `watch` or `fail` is a release blocker for presentation builds.
- Repeated `watch` notes in the same scene should be fixed before adding more animation layers.

## Result Template

Use `docs/ANIMATION_PLAYTEST_REPORT_TEMPLATE.md` for the full report. The compact template below is only for quick notes during a live pass.

```text
Build:
Commit:
Tester:
Date:

Automated gates: pass/watch/fail
Windows tested: 820x620 / 960x640 / 1440x900
Motion modes tested: full / reduced / off

Scene notes:
- Title/Menu:
- Live Dashboard:
- Action Picker:
- Pending Event:
- Inspector:
- Endgame Board:
- Turn Summary:
- Outcome/Review:

Release decision: pass/watch/fail
Follow-up fixes:
```
