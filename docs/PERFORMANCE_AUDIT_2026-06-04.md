# Performance Audit - 2026-06-04

Version: `0.138.0`

## Scope

- Added a deterministic `audit-2d-motion` CLI gate for the animated 2D frontend.
- The audit stresses the live run and staged turn summary with dense pulse banks across `820x620`, `960x640`, and `1280x720` viewports.
- The audit also exercises title/menu motion, save-slot detail, rename/delete overlays, archive/meta/wizard subflows, review-scene motion, inspector overlays, picker overlays, and 2D request-path coverage.
- Inspector interactions now have explicit section, item, page, sort, filter, actionable-focus, and hotspot-focus pulse lanes.
- The 2D shell now supports `--motion-mode full|reduced|off` for launchers and `audit-2d-motion`, with reduced/off modes preserving gameplay while lowering or disabling highlight pulses.
- Scene entry transitions now cover boot, title-to-run, title-to-review, run-to-summary, run-to-review, summary-to-run, summary-to-review, and review-to-title flows.
- Shape-based entity motion now covers stat lanes, product cards, and active deep-panel strips without adding external sprite assets.
- Deterministic shape-sprite actor timelines now cover live-run founder/team/customer/board/product beats and turn-summary founder/finance/customer/board/gate beats without adding external image assets.
- Scene-specific actor clips now also cover title/menu guidance, inspector record routing, the endgame cockpit board, and review/postmortem handoffs.
- Actor sprite footprints now feed an automated `actor-readability` layer that checks viewport bounds and click-target collisions across actor scenes before manual playtesting.
- Visual captures now also report edge-density and bright-pixel pressure, giving the audits a deterministic first-pass guard against cluttered or overly flashy animation frames.
- `audit-2d-animation` now includes an `Animation Pacing Budget` cell that gates active animation sample density, pulse cooldown, and frame timing before manual open-window review.
- `audit-2d-animation` now includes a `Long Session Motion Stress` cell that gates dense long-run pulse recovery and frame timing separately from short smoke checks.
- `audit-2d-animation` now includes a `Scene Motion Profile` cell that requires every captured scene to have an explicit motion-layer budget before new scene animation can ship.
- `audit-2d-animation` now includes a `Readability Guard` cell that checks compact captures, actor-readability, overlay density, and visual pass status before manual playtesting.
- Blocked or rejected 2D commands now emit distinct blocked-action feedback cards, targeted flash pulses, and matching actor blocked states instead of sharing the same visual language as successful commands.
- GitHub Actions now runs 2D headless smoke plus motion, visual, and animation-completeness gates and uploads full/off visual captures so local release checks and pull request checks catch animation regressions the same way.
- Command-specific action feedback cues now cover successful commands, picker launches, create-product modals, inspector opens, and end-turn confirmation while respecting reduced/off motion modes.
- State-delta impact cue cards now cover successful action results for cash, users, reputation, board pressure, and product metrics while respecting reduced/off motion modes.
- Modal overlay enter/exit transitions now cover pending events, action pickers, text modals, deep panels, inspectors, help, and outcome dialogs.
- Turn summaries now include a cinematic rail that sequences resolution phases before returning to the live run.
- Product cards now render quality/fit shimmer, bug beacons, debt cracks, and user-flow particles from live product ratios.
- Finance, runway, and board pressure lanes now render risk drama beacons when danger states are active, and pending-event choices produce consequence cues after selection.
- Turn-summary metrics and product outcomes now use staged reveal sequencing in addition to the cinematic phase rail.
- Late-game command choreography cards now cover terminal, path-repair, board, finance, and pipeline commands while reusing panel/stat targets.
- Pending-event options now expose preview motion before selection, and turn summaries now add compact outcome lanes for cash, users, board, and gate shifts.
- Outcome overlays now include a dedicated victory/shutdown cinematic layer for final run states.
- `audit-2d-visual` now renders title, meta, live run, blocked-action feedback, pending preview, picker/action-feedback, inspector, outcome overlay, turn-summary, and review captures to verify non-empty frames plus expected active visual layers before manual review, and writes a Markdown summary next to PNG captures when `--output-dir` is used.
- `audit-2d-animation` now combines visual-layer coverage, actor/sprite coverage, actor-readability checks, visual-fatigue budgets, motion-budget checks, off-mode checks, and advisory gaps into one animation-completeness gate.
- Visual reports now include a deterministic baseline signature so capture sets can be compared without committing generated PNGs.
- Each viewport reports pulse-bank cooldown before/after counts, transition active/disabled telemetry, entity-motion active/disabled telemetry, broader actor-timeline/sprite-clip active/disabled telemetry, action-feedback active/disabled telemetry, impact-cue active/disabled telemetry, overlay-transition telemetry, product/risk drama telemetry, pending-choice and pending-preview telemetry, outcome-cinematic telemetry, late-game choreography telemetry, summary-cinematic/sequence/lane telemetry, average frame time, and max frame spike.

## Stability Budgets

- Live run target: cool residual pulse banks to `<= 18` live pulses.
- Turn summary target: cool residual pulse banks to `<= 12` live pulses.
- Title/menu target: keep multi-subflow title and wizard overlay pulse banks to `<= 14` live pulses.
- Review target: keep post-run review pulse banks to `<= 6` live pulses.
- Inspector target: keep interaction pulse banks to `<= 12` live pulses.
- Long-run pressure target: cool repeated dense highlight banks to `<= 18` live pulses.
- Frame target: average fixed-step update/draw time at or below `24 ms`.
- Max frame target: avoid spikes above `50 ms`.
- Watch threshold: up to `33 ms` or slightly elevated pulse banks without failing the release gate.
- Visual fatigue target: sampled edge density and bright-pixel pressure must stay below the visual audit budgets before open-window playtesting.
- Animation pacing target: full-mode active animation sample density must stay at or below `36` per audit viewport while pulse cooldown and frame budgets stay green.
- Long-session target: dense long-run pulse banks must cool back to `<= 18` pulses while average and max frame budgets remain green.
- Scene profile target: every visual audit scene must be declared in the scene motion-profile map, and each scene must stay within its explicit motion-layer budget.
- Readability target: compact `820px` captures must pass visual health, actor scenes must expose `actor-readability`, and overlay scenes must stay under the compact overlay density budget.
- Blocked feedback target: blocked/rejected command cards must expose `blocked-action-feedback` and stay disabled in `--motion-mode off`.
- Flow target: every surfaced 2D command and inspector item action must either build a request path or return a concrete disabled explanation.

## Verification Commands

- `nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 2`
- `nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 1 --motion-mode reduced`
- `nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 1 --motion-mode off`
- `nexus-tech audit-2d-visual --scenario founder_journey --seed 7`
- `nexus-tech audit-2d-visual --scenario founder_journey --seed 7 --motion-mode off`
- `nexus-tech audit-2d-animation --scenario founder_journey --seed 7 --frames 1`
- `pytest -q tests/test_frontend_2d.py -k "motion_audit or audit_2d_motion or visual_audit or audit_2d_visual"`

## Result

The audit makes animation stability, long-session stress recovery, compact readability, scene-profile coverage, pacing, visual quality, and runtime 2D request coverage repeatable in CI/local release checks instead of relying only on manual visual playtesting.
