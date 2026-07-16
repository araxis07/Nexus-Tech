# NEXUS TECH Release Checklist

Use this checklist before tagging or presenting a release.

## Version And Notes

- Update `pyproject.toml`.
- Update `src/nexus_tech/__init__.py`.
- Add a dated entry to `CHANGELOG.md`.
- Confirm the README lists any new commands, systems, or content.

## Local Verification

```bash
uv sync --extra dev
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest -q
uv run pytest -q tests/test_beta_convergence.py
uv run nexus-tech --version
uv run nexus-tech doctor
uv run nexus-tech validate-content
uv run nexus-tech beta-evidence
uv run nexus-tech beta-playtest-status
uv run nexus-tech prepare-beta-playtest-session --output /tmp/nexus-tech-beta-playtest-next.md
uv run nexus-tech campaign-readiness --runs 3 --turns 20 --seed-base 28500 --output /tmp/nexus-tech-campaign-readiness.md
uv run nexus-tech play-2d --scenario founder_journey --seed 7 --headless --max-frames 2 --motion-mode reduced
uv run nexus-tech play-2d --scenario founder_journey --seed 283 --headless --max-frames 2 --window-size 820x620 --motion-mode reduced --ui-scale large --contrast-mode high
uv run nexus-tech menu-2d --headless --max-frames 2 --motion-mode reduced
uv run nexus-tech menu-2d --headless --max-frames 2 --window-size 820x620 --ui-scale large --contrast-mode high
uv run nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 2
uv run nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 1 --motion-mode reduced
uv run nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 1 --motion-mode off
uv run nexus-tech audit-2d-visual --scenario founder_journey --seed 7 --viewport 820x620 --viewport 960x640 --viewport 1440x900
uv run nexus-tech audit-2d-visual --scenario founder_journey --seed 7 --motion-mode off --viewport 820x620 --viewport 960x640 --viewport 1440x900
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
uv run nexus-tech animation-playtest-recorder-next /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech animation-playtest-route-batches /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md --output /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech validate-animation-playtest-route-batches /tmp/nexus-tech-animation-route-batches.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech validate-animation-playtest-plan /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md
uv run nexus-tech prepare-animation-playtest-session --prefill-automated-gates --plan-output /tmp/nexus-tech-animation-playtest-plan.md --recorder-output /tmp/nexus-tech-animation-recorder-queue.md --route-batches-output /tmp/nexus-tech-animation-route-batches.md --triage-output /tmp/nexus-tech-animation-ui-triage.md --release-gate-output /tmp/nexus-tech-animation-release-gate.md --progress-output /tmp/nexus-tech-animation-progress.md --execution-guide-output /tmp/nexus-tech-animation-execution-guide.md --issue-backlog-output /tmp/nexus-tech-animation-issues.md --sprint-output /tmp/nexus-tech-animation-sprint.md --handoff-output /tmp/nexus-tech-animation-handoff.md
uv run nexus-tech validate-animation-playtest-session /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md --route-batches /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech animation-playtest-handoff /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md --route-batches /tmp/nexus-tech-animation-route-batches.md --output /tmp/nexus-tech-animation-handoff.md
uv run nexus-tech animation-playtest-ui-triage /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md --route-batches /tmp/nexus-tech-animation-route-batches.md --output /tmp/nexus-tech-animation-ui-triage.md
uv run nexus-tech validate-animation-playtest-ui-triage /tmp/nexus-tech-animation-ui-triage.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md --route-batches /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech animation-playtest-release-gate /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --output /tmp/nexus-tech-animation-release-gate.md
uv run nexus-tech validate-animation-playtest-release-gate /tmp/nexus-tech-animation-release-gate.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech animation-playtest-progress /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --output /tmp/nexus-tech-animation-progress.md
uv run nexus-tech validate-animation-playtest-progress /tmp/nexus-tech-animation-progress.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech animation-playtest-execution-guide /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --progress-path /tmp/nexus-tech-animation-progress.md --output /tmp/nexus-tech-animation-execution-guide.md
uv run nexus-tech validate-animation-playtest-execution-guide /tmp/nexus-tech-animation-execution-guide.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --progress-path /tmp/nexus-tech-animation-progress.md
uv run nexus-tech animation-playtest-issue-backlog /tmp/nexus-tech-animation-playtest-report.md --output /tmp/nexus-tech-animation-issues.md
uv run nexus-tech validate-animation-playtest-issue-backlog /tmp/nexus-tech-animation-issues.md /tmp/nexus-tech-animation-playtest-report.md
uv run nexus-tech animation-playtest-sprint /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --progress-path /tmp/nexus-tech-animation-progress.md --execution-guide-path /tmp/nexus-tech-animation-execution-guide.md --issue-backlog-path /tmp/nexus-tech-animation-issues.md --output /tmp/nexus-tech-animation-sprint.md
uv run nexus-tech validate-animation-playtest-sprint /tmp/nexus-tech-animation-sprint.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --progress-path /tmp/nexus-tech-animation-progress.md --execution-guide-path /tmp/nexus-tech-animation-execution-guide.md --issue-backlog-path /tmp/nexus-tech-animation-issues.md
uv run nexus-tech balance-audit --scenario founder_journey --scenario debt_crunch --runs 1 --turns 6 --seed-base 7
uv run nexus-tech balance-audit --scenario founder_journey --scenario bootstrap_studio --scenario technical_rebuild --scenario portfolio_machine --scenario debt_crunch --scenario public_market_countdown --runs 1 --turns 12 --seed-base 28300
uv run nexus-tech simulate-balance --scenario founder_journey --difficulty founder --runs 2 --turns 10 --seed-base 700
# After the manual report is filled:
uv run nexus-tech validate-animation-playtest-report /tmp/nexus-tech-animation-playtest-report.md
```

If `uv` is not available in the release shell, keep the same manual animation
workflow but add `--command-prefix .venv313/bin/nexus-tech` to
`animation-playtest-commands`, `validate-animation-playtest-commands`,
`animation-playtest-plan`, `animation-playtest-recorder-queue`,
`validate-animation-playtest-recorder-queue`, `animation-playtest-recorder-next`,
`animation-playtest-route-batches`, `validate-animation-playtest-route-batches`,
`animation-playtest-ui-triage`, `validate-animation-playtest-ui-triage`,
`animation-playtest-release-gate`, `validate-animation-playtest-release-gate`,
`animation-playtest-progress`, `validate-animation-playtest-progress`,
`animation-playtest-execution-guide`, `validate-animation-playtest-execution-guide`,
`animation-playtest-issue-backlog`, `validate-animation-playtest-issue-backlog`,
`animation-playtest-sprint`, `validate-animation-playtest-sprint`,
`validate-animation-playtest-plan`, `prepare-animation-playtest-session`,
`validate-animation-playtest-session`, and `animation-playtest-handoff`.
The command queue, grouped plan, recorder queue, recorder hints, and validators
must all use the same launcher prefix.

Run `animation-playtest-status` while the manual pass is in progress to see the
remaining grouped rows. Add `--fail-on-incomplete` only when the status command
is being used as a release gate.
Run `animation-playtest-commands` to export the exact visible-window queue before
the manual pass, including the evidence prompt each row must record; keep the
generated queue in `/tmp` unless it contains real release notes.
Run `validate-animation-playtest-commands` after any queue export or edit so no
required visible-window run or evidence prompt is skipped before handoff.
Run `animation-playtest-plan` after queue validation to see whether the handoff
is queue-blocked, still manual-required, or complete. Use `--output` to save the
grouped plan, manual evidence checklist, and 18-step visible test route beside
the report and command queue. The plan also includes a validated manual runbook
for artifact refresh, visible-window execution, evidence-fill, and final
validator exit criteria.
Run `validate-animation-playtest-plan` after writing the grouped plan so stale
status, open-item counts, visible-route evidence prompts, or manual evidence
checklist/runbook rows are blocked before handoff.
Run `animation-playtest-recorder-queue` before handing the report to a tester
when you need a full Markdown queue of every currently incomplete recorder
command. `prepare-animation-playtest-session` also writes this queue with the
default recorder output path, and the exported queue still uses placeholders and
does not complete manual signoff.
Run `validate-animation-playtest-recorder-queue` after exporting the recorder
queue so stale row counts, evidence prompts, visible commands, required terms, or
recorder commands fail before manual evidence collection starts.
Run `animation-playtest-recorder-next` during the visible pass when the tester
needs the next safe recorder command. It prints the matching visible-window
command, required evidence terms, and a recorder command with placeholders that
must be replaced by real observations before signoff.
Run `animation-playtest-route-batches` before a longer visible pass when the
tester needs all 18 menu/play route commands grouped by target window with the
matching recorder commands in the same artifact.
Run `validate-animation-playtest-route-batches` after writing the route-batch
artifact so stale visible commands, required terms, or recorder commands fail
before the tester follows the batch plan.
Run `animation-playtest-ui-triage` after session validation so layout,
typography, control, scene, motion-feedback, and signoff gaps are split into
P0/P1/P2 lanes before the next UI polish pass. Run
`validate-animation-playtest-ui-triage` after editing the backlog.
Run `animation-playtest-release-gate` after UI triage validation so release
review has one go/no-go artifact across session artifacts, UI triage, P0/P1
lanes, and final manual signoff. Run
`validate-animation-playtest-release-gate` before treating the gate as current.
Use the gate's `Next Manual Action` section to continue the visible-window pass
with the next command and matching recorder command.
Run `animation-playtest-progress` when release review needs a completion
percentage, open manual lanes, P0/P1 status, and the same next manual action in
one board. The progress board is advisory and does not record tester evidence.
Run `animation-playtest-execution-guide` when a tester needs one validated
operator artifact for the current pass. It pairs every remaining visible command
with required evidence terms and recorder commands without completing evidence.
Run `animation-playtest-issue-backlog` after report edits to turn current
fail/watch results and missing-evidence rows into a validated P0/P1/P2 queue for
the next fix pass.
Run `animation-playtest-sprint` when the next QA loop needs a focused work
packet. It pulls the next visible observation rows from the execution guide and
the current P0/P1 blockers from the issue backlog, labels report-field
placeholders as post-observation signoff work, includes the manual observation
checklist plus execution batches and defect intake, a layout repair pass for
responsive frames, button grids, text containment, navigation affordance, and
motion separation,
layout recording map rows with the exact window/control recorder commands,
navigation recovery drills for pause, resume, back/escape, menu return, and
help/hover paths, a navigation recording map with the exact control recorder
commands, exit criteria, evidence capture prompts, and note templates, then
`validate-animation-playtest-sprint` verifies both sources still match.
The CLI output prints the execution batch table too, so release review can see
the next artifact refresh, layout, recovery, motion, and closure steps without
opening the sprint Markdown file. It also prints the next visible command and
matching recorder command as `Sprint Next Action`, keeping the handoff anchored
to the first real observation step. The `Next Sprint Copy Commands` panel keeps
the full command text visible for copy-paste while preserving placeholder notes
until a tester records real evidence.
The route-batch artifact and CLI now surface per-window evidence checklists,
result decision guidance, defect-trigger checklists, and copy commands for the
next incomplete batch, keeping pass/watch/fail decisions and visible route
commands ahead of recorder placeholders during release review. Keep `--result
pass` only when no defect trigger applies; switch to `watch` or `fail` before
recording when the visible window shows a follow-up risk or blocker, then name
the layout, navigation, motion, feedback, or evidence-quality trigger. When an
output artifact path is provided, the CLI also prints post-recording refresh
commands for validating route batches and checking report status after observed
evidence is recorded.
Run `prepare-animation-playtest-session` when preparing a handoff package for a
tester; it creates the report draft, command queue, grouped plan artifact,
recorder queue artifact, route-batch artifact, UI triage backlog, release gate,
progress board, execution guide, issue backlog, handoff sheet, and current artifact validation without
completing manual signoff.
Run `validate-animation-playtest-session` after preparing or editing handoff
artifacts so stale command queues, grouped plans, recorder queues, or optional
route-batch artifacts fail before the tester starts the open-window pass. A
clean package can still be `manual-required` until real evidence is recorded.
Run `animation-playtest-handoff` after session validation when the tester needs
one concise sheet with the artifact status, next visible command, and matching
recorder command.
The completed report must retain all 18 `Visible Route Evidence` rows generated
from the queue and mark each row `pass` with observed notes before signoff.
Route evidence notes must cover the required target-specific terms: menu rows
cover title/wizard/save/archive/meta/hover/text, and play rows cover
dashboard/action/pending/inspector/endgame/summary/pause/motion.
Use `record-animation-playtest-route` and `record-animation-playtest-window`
during the visible pass when you want safer row updates than hand-editing
Markdown tables. Use `record-animation-playtest-control`,
`record-animation-playtest-scene`, `record-animation-playtest-feedback`, and
`record-animation-playtest-field` for the remaining manual rows and signoff
fields. These commands print the remaining grouped manual gaps, enforce required
evidence terms, and still require real tester observations.
Final report notes must contain observed evidence. Generic notes such as `ok`,
`clear`, `readable`, or `stable` fail validation because they do not prove which
window, control path, scene, or motion cue was checked.
The final report validator also requires target-specific observed terms for
window matrix, control, scene, and game-feel rows before animation signoff can
pass.
Generated report drafts include the same required-term prompts in each affected
manual row, but those prompts must be replaced with observed notes before final
validation; leftover prompt text is treated as missing evidence.
For a `pass` release decision, all release-blocker fields and `Required fixes
before presenting` must be clear, and `Validator result` must be pass.
The completed manual report must preserve all generated section headings so the
signoff artifact can be audited after release.
Remove any leftover draft warning paragraph or `owner/date if not pass`
placeholder before final validation.

## Demo Verification

```bash
uv run nexus-tech glossary
uv run nexus-tech tutorial
uv run nexus-tech list-scenarios
uv run nexus-tech list-templates
uv run nexus-tech list-rivals
uv run nexus-tech list-events
uv run nexus-tech simulate-balance --scenario founder_journey --runs 1 --turns 3 --seed-base 7
uv run nexus-tech balance-audit --scenario founder_journey --scenario debt_crunch --runs 1 --turns 6 --seed-base 7
uv run nexus-tech simulate-balance --scenario founder_journey --difficulty founder --runs 2 --turns 10 --seed-base 700
uv run nexus-tech balance-report --output /tmp/nexus-balance-report.md --scenario founder_journey --runs 1 --turns 3 --seed-base 7
```

## Save Verification

```bash
uv run nexus-tech check-saves
uv run nexus-tech list-saves
```

If no save database exists yet, `doctor` should still run cleanly and explain that no save has been created.

## 2D Audit Notes

- Capture the latest internal playtest and balance findings in a repo doc before release so cockpit, friction, and tuning decisions stay attached to the build.
- Verify Decision Pattern excludes Campaign Decision and Event Choice entries from operating mix, remains read-only, and fits the terminal report plus paged 2D Report Inspector without crowding the live run.
- Verify the Endgame Board starts with only Recommended Fix and Review Main Risk, `V` and the More control reveal every existing panel action, and returning to Guided View does not alter gameplay state.
- Run `audit-2d-motion` whenever animation pacing, pulse-bank cooldown, staged-summary motion, or 2D request-path coverage changes.
- Run `audit-2d-animation` whenever a scene, overlay, pending-event, outcome, actor/sprite, or late-game choreography layer changes so required animation coverage and advisory gaps stay explicit.
- Run `audit-2d-animation-matrix --output /tmp/nexus-tech-animation-matrix.md` before presentation builds so actor/state, readability, pacing, and motion gates are checked beyond the single founder seed.
- Run `prepare-2d-animation-playtest --output /tmp/nexus-tech-animation-playtest-prep.md` before the human pass so the window/motion/control checklist starts from the same matrix baselines as CI.
- Use visible `menu-2d` and `play-2d` with `--window-size 820x620`, `--window-size 960x640`, and `--window-size 1440x900` during the human pass instead of hand-resizing windows.
- Run `animation-playtest-commands --output /tmp/nexus-tech-animation-playtest-commands.md` when handing the remaining manual QA to a tester so no required window or motion mode is skipped.
- Run `validate-animation-playtest-commands /tmp/nexus-tech-animation-playtest-commands.md` before handoff so the exported queue has every required menu/play command.
- Run `animation-playtest-plan /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md --output /tmp/nexus-tech-animation-playtest-plan.md` before and during handoff so open manual areas are grouped without treating queue completeness as signoff.
- Run `animation-playtest-recorder-queue /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md --output /tmp/nexus-tech-animation-recorder-queue.md` before longer manual passes so testers can follow every open recorder step without hand-building commands.
- Run `validate-animation-playtest-recorder-queue /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md` after exporting the recorder queue so stale handoff rows fail before manual recording starts.
- Run `animation-playtest-recorder-next /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md` while filling evidence so each visible run is paired with the correct recorder command and required evidence terms.
- Run `animation-playtest-route-batches /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md --output /tmp/nexus-tech-animation-route-batches.md` when testers need one window-sized route batch at a time.
- Run `validate-animation-playtest-route-batches /tmp/nexus-tech-animation-route-batches.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md` after route-batch export so stale batch plans fail before handoff.
- Run `validate-animation-playtest-plan /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md` before attaching the plan artifact to handoff notes.
- Run `prepare-animation-playtest-session --prefill-automated-gates --plan-output /tmp/nexus-tech-animation-playtest-plan.md --recorder-output /tmp/nexus-tech-animation-recorder-queue.md --route-batches-output /tmp/nexus-tech-animation-route-batches.md --triage-output /tmp/nexus-tech-animation-ui-triage.md --release-gate-output /tmp/nexus-tech-animation-release-gate.md --progress-output /tmp/nexus-tech-animation-progress.md --execution-guide-output /tmp/nexus-tech-animation-execution-guide.md --issue-backlog-output /tmp/nexus-tech-animation-issues.md --sprint-output /tmp/nexus-tech-animation-sprint.md --handoff-output /tmp/nexus-tech-animation-handoff.md` for the one-command setup when the report draft, command queue, grouped plan, recorder queue, route batches, UI triage, release gate, progress board, execution guide, issue backlog, sprint packet, and handoff sheet should be regenerated together.
- Run `validate-animation-playtest-session /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md --route-batches /tmp/nexus-tech-animation-route-batches.md` before handoff so the full package is checked together.
- Run `animation-playtest-handoff /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md --route-batches /tmp/nexus-tech-animation-route-batches.md --output /tmp/nexus-tech-animation-handoff.md` when the tester needs the next visible command and recorder command in one sheet.
- Run `animation-playtest-ui-triage /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md --route-batches /tmp/nexus-tech-animation-route-batches.md --output /tmp/nexus-tech-animation-ui-triage.md` when the next pass needs a scoped UI/UX backlog.
- Run `validate-animation-playtest-ui-triage /tmp/nexus-tech-animation-ui-triage.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md --route-batches /tmp/nexus-tech-animation-route-batches.md` before using that backlog for UI polish.
- Run `animation-playtest-release-gate /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --output /tmp/nexus-tech-animation-release-gate.md` before release review so manual-required status is visible in one artifact.
- Run `validate-animation-playtest-release-gate /tmp/nexus-tech-animation-release-gate.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md` before attaching the gate to release notes.
- Run `animation-playtest-progress /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --output /tmp/nexus-tech-animation-progress.md` before release review when the manual QA progress board should be attached beside the gate.
- Run `validate-animation-playtest-progress /tmp/nexus-tech-animation-progress.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md` before using the progress board for status updates.
- Run `animation-playtest-execution-guide /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --progress-path /tmp/nexus-tech-animation-progress.md --output /tmp/nexus-tech-animation-execution-guide.md` when the tester needs the full operator loop in one artifact.
- Run `validate-animation-playtest-execution-guide /tmp/nexus-tech-animation-execution-guide.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --progress-path /tmp/nexus-tech-animation-progress.md` before handing the guide to a tester.
- Run `animation-playtest-issue-backlog /tmp/nexus-tech-animation-playtest-report.md --output /tmp/nexus-tech-animation-issues.md` when the report should become a prioritized fix/evidence queue.
- Run `validate-animation-playtest-issue-backlog /tmp/nexus-tech-animation-issues.md /tmp/nexus-tech-animation-playtest-report.md` before using the backlog for the next fix pass.
- Run `animation-playtest-sprint /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --progress-path /tmp/nexus-tech-animation-progress.md --execution-guide-path /tmp/nexus-tech-animation-execution-guide.md --issue-backlog-path /tmp/nexus-tech-animation-issues.md --output /tmp/nexus-tech-animation-sprint.md` when the tester needs one focused pass packet.
- Run `validate-animation-playtest-sprint /tmp/nexus-tech-animation-sprint.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --progress-path /tmp/nexus-tech-animation-progress.md --execution-guide-path /tmp/nexus-tech-animation-execution-guide.md --issue-backlog-path /tmp/nexus-tech-animation-issues.md` before using the sprint packet for manual QA.
- Add `--command-prefix .venv313/bin/nexus-tech` to the manual animation queue, validation, plan, recorder-queue, recorder-queue validation, recorder-next, route-batches, route-batch validation, UI triage, UI triage validation, release gate, release gate validation, progress board, progress board validation, execution guide, execution guide validation, issue backlog, issue backlog validation, sprint packet, sprint packet validation, session, session validation, and handoff commands when the visible-window tester is using the local virtualenv launcher instead of `uv run nexus-tech`.
- Run `draft-animation-playtest-report --prefill-automated-gates --output /tmp/nexus-tech-animation-playtest-report.md` after automated gates pass so the completed report starts from the same validator-required rows while manual window/control/scene/game-feel rows still require real tester input.
- Run the balance and long-session preflight commands listed in the playtest prep artifact before opening the manual animation pass.
- Run `validate-animation-playtest-report` on the completed manual report before calling animation complete.
- Treat any missing automated gate row, window/motion cell, control row, scene row, game-feel row, release-blocker field, or validator PASS in the manual report as a release blocker.
- Treat missing manual report sections as release blockers even when the rows and fields are still present elsewhere in the file.
- Treat leftover draft warning text or `owner/date if not pass` placeholders as release blockers.
- Treat generic evidence notes such as `ok`, `clear`, `readable`, `stable`, or `none` in required report evidence cells as release blockers.
- Treat missing `actor-readability` layers as release blockers before the remaining open-window readability pass.
- Treat missing `actor-pose-depth` layers as release blockers before presenting new actor/sprite reactions.
- Treat `Actor State Coverage` failures as release blockers before presenting new actor/sprite reactions.
- Treat `Action Feedback Clarity` failures as release blockers before presenting new action, blocked-action, or impact feedback.
- Treat `Scene Transition Handoff` failures as release blockers before presenting scene-to-scene animation polish.
- Treat `Control Affordance Coverage` failures as release blockers before presenting navigation, pause, back, help, save, or summary/outcome flow changes.
- Treat `Control Replay Safety` failures as release blockers before presenting pause, Escape/back, help, save, hover-copy, or menu-return behavior.
- Treat `UI Layout Safety` failures as release blockers before presenting compact layouts, navigation rails, modal buttons, or actor-heavy scenes.
- Treat `Typography Safety` failures as release blockers before presenting compact buttons, modal copy, summary cards, or inspector-heavy scenes.
- Treat `Visual Fatigue Budget` failures as release blockers before adding more animation density.
- Treat `Animation Pacing Budget` failures as release blockers before adding more full-mode motion layers.
- Treat `Motion Mode Differentiation` failures as release blockers before changing full/reduced/off animation behavior.
- Treat `Long Session Motion Stress` failures as release blockers before presenting longer 2D playthroughs.
- Treat `Long Session Visual Readiness` failures as release blockers before presenting longer 2D playthroughs.
- Treat `Scene Motion Profile` failures as release blockers before shipping new scenes or adding denser scene-specific motion.
- Treat `Readability Guard` failures as release blockers before opening the manual playtest pass.
- Treat `Archive/Meta Comparison Motion` failures as release blockers before presenting archive or meta-board progression screens.
- Treat late-game repair cues that do not identify the correct IPO, M&A, independence, or reset target lane as release blockers before presenting endgame/picker polish.
- Treat text clipping, unreadable compact buttons, or local gameplay database files appearing in `git status` as release blockers before presenting the 2D build.
- Treat Settings or beta-evidence values that alter gameplay save-slot rows as release blockers; schema 27 must migrate additively and keep human-session rows isolated.
- Treat missing visible Back/Pause/Menu controls, missing hover/cursor affordance on primary controls, or `Esc` quitting the run without pause confirmation as release blockers before presenting the 2D build.
- Treat 820x620 title/run/summary/review captures with overlapping navigation, cut-off cards, or action buttons spilling outside their panels as release blockers before presenting the 2D build.
- Treat `audit-2d-animation-matrix` failures as release blockers for the default seven-scenario, three-seed presentation matrix.
- Treat any non-clear release-blocker field, required fix before presenting, or non-pass validator result as a release blocker even when the release decision says `pass`.
- Treat missing `blocked-action-feedback` as a release blocker when disabled or rejected command behavior changes.
- Treat a Strategic Rhythm recommendation that conflicts with Guided Opening, First Archive Mission, or the current campaign act as a release blocker; endgame-gate guidance must not lead before Act 3.
- Keep `.github/workflows/ci.yml` aligned with these local gates so animation regressions fail before merge, review the uploaded `nexus-tech-2d-visual-audit` artifact summary before opening individual captures, and review the uploaded `nexus-tech-2d-animation-matrix` and `nexus-tech-2d-animation-playtest-prep` artifacts before manual presentation playtests.
- Use `docs/OPEN_WINDOW_ANIMATION_PLAYTEST.md`, `docs/ANIMATION_PLAYTEST_REPORT_TEMPLATE.md`, and `docs/ANIMATION_PLAYTEST_CHECKLIST_2026-06-06.md` for the remaining open-window readability pass before presenting the 2D build.
- If `balance-audit` still reports `watch` or worse cells, note whether they are intentional difficulty pressure or candidates for retuning before tagging.
- Treat unexplained balance preflight `watch` or `fail` cells as blockers for presentation builds, even when animation gates are green.
- Treat incomplete manual reports, blank result cells, `todo` cells, or missing validator PASS as blockers for presentation builds.
- If founder-pressure openings were retuned, rerun at least one longer `simulate-balance` founder batch so angel-cap, pricing, and cash-guard policies are verified on real seeds instead of only short audits.

## Scope Guardrails

- Keep the game local and offline.
- Do not add GUI, web, cloud, accounts, telemetry, or multiplayer infrastructure.
- Keep simulation logic out of Rich rendering and Typer command handlers.
- Keep SQLite access inside the persistence layer.
- Keep randomness seedable for deterministic tests and demos.
