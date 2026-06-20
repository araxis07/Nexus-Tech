# Animation Playtest Checklist - 2026-06-06

Use this checklist for the manual open-window pass that headless audits cannot judge.

## Build Under Review

- Version: `0.171.0`
- Focus: 2D actor/sprite timeline, archive/meta comparison motion, path-specific late-game repair cues, actor-state coverage, actor-pose-depth, action feedback clarity, scene transition handoffs, control-affordance coverage, control replay safety, UI layout safety, typography safety, blocked-action feedback, CI-backed animation gates, automated actor-readability, readability guard, visual-fatigue, animation-pacing, long-session stress, balance preflight evidence, strict manual signoff validation, scenario/seed matrix readiness, and scene motion-profile guards, scene pacing, overlay readability, and motion-mode behavior.
- Status guard: `animation-playtest-status` groups remaining manual rows while the report is incomplete; use `--fail-on-incomplete` only for release gate checks.
- Window guard: visible `menu-2d` and `play-2d` runs support `--window-size 820x620`, `--window-size 960x640`, and `--window-size 1440x900` so the manual matrix starts at the exact target dimensions.
- Command queue guard: `animation-playtest-commands --output /tmp/nexus-tech-animation-playtest-commands.md` exports every required visible-window command while keeping manual signoff incomplete.
- Command queue validation guard: `validate-animation-playtest-commands /tmp/nexus-tech-animation-playtest-commands.md` fails when any required menu/play window or motion mode is missing.
- Plan guard: `animation-playtest-plan /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md --output /tmp/nexus-tech-animation-playtest-plan.md` combines queue status and report gaps into one next-step handoff artifact.
- Plan validation guard: `validate-animation-playtest-plan /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md` fails when the exported plan is stale.
- Session guard: `prepare-animation-playtest-session --prefill-automated-gates` creates the strict report draft, visible command queue, and grouped status summary together without completing manual signoff.

## Commands

```bash
nexus-tech menu-2d --window-size 820x620 --motion-mode full
nexus-tech play-2d --scenario founder_journey --seed 7 --window-size 820x620 --motion-mode full
nexus-tech play-2d --scenario founder_journey --seed 7 --window-size 960x640 --motion-mode reduced
nexus-tech play-2d --scenario founder_journey --seed 7 --window-size 1440x900 --motion-mode off
```

## Required Checks

- Title/menu flow: wizard, save slots, archive/meta, and title transitions remain readable.
- Run dashboard: founder/team/customer/board/product actor clips are visible without covering snapshot chips, stat bars, product cards, or action buttons.
- Automated guard: `audit-2d-animation` reports `actor-readability` for actor scenes before the manual open-window pass.
- Automated guard: `audit-2d-animation` reports `actor-pose-depth` so blocked, warning, build, handoff, coaching, deal, and win poses are visible before the manual pass.
- Automated guard: `audit-2d-animation` reports `Actor State Coverage` so baseline, positive, pressure, and blocked sprite reactions are present before the manual pass.
- Automated guard: `audit-2d-animation` reports `Action Feedback Clarity` so success targets, blocked reasons, impact targets, and impact values are present before the manual pass.
- Automated guard: `audit-2d-animation` reports `Scene Transition Handoff` so boot, run, summary, and review transitions are covered and motion-mode off disables them.
- Automated guard: `audit-2d-animation` reports `Control Affordance Coverage` so title, run, outcome, summary, review, pause, back, help, save, and flow controls are present before the manual pass.
- Automated guard: `audit-2d-animation` reports `Control Replay Safety` so pause, resume, Escape/back, help, hover-copy, save, and title-menu return regressions fail before manual control-feel review.
- Automated guard: `audit-2d-animation` reports `UI Layout Safety` so click targets stay in-bounds, large enough, non-overlapping, and clear of actor sprites before the manual pass.
- Automated guard: `audit-2d-animation` reports `Typography Safety` so severe button-title fitting, hidden lines, and wrapped-text clamps are visible before the manual pass.
- Automated guard: `audit-2d-animation` reports `Visual Fatigue Budget` so clutter and bright-pixel pressure stay within deterministic limits before the manual pass.
- Automated guard: `audit-2d-animation` reports `Animation Pacing Budget` so active motion density, pulse cooldown, and frame timing stay within release limits before the manual pass.
- Automated guard: `audit-2d-animation` reports `Motion Mode Differentiation` so full, reduced, and off motion behavior cannot silently collapse into the same mode before the manual pass.
- Automated guard: `audit-2d-animation` reports `Long Session Motion Stress` so dense long-run pulse banks cool down before the manual pass.
- Automated guard: `audit-2d-animation` reports `Long Session Visual Readiness` so late-session dashboard, inspector, endgame, summary, and review scenes stay compact-readable before the manual pass.
- Automated guard: `audit-2d-animation` reports `Scene Motion Profile` so new scenes cannot ship without explicit motion-layer budgets.
- Automated guard: `audit-2d-animation` reports `Readability Guard` so compact captures, actor-readable scenes, overlay density, and visual pass status are verified before the manual pass.
- Automated guard: `audit-2d-animation` reports `Archive/Meta Comparison Motion` so the meta board and archive comparison rail stay visible before the manual archive pass.
- Matrix guard: `audit-2d-animation-matrix --output /tmp/nexus-tech-animation-matrix.md` passes across the default seven-scenario, three-seed, three-window presentation matrix before relying on the single founder seed.
- Playtest prep guard: `prepare-2d-animation-playtest --output /tmp/nexus-tech-animation-playtest-prep.md` writes the window/motion checklist from the same matrix evidence before the human pass starts.
- Command queue guard: `animation-playtest-commands --output /tmp/nexus-tech-animation-playtest-commands.md` lists every visible `menu-2d` and `play-2d` command for the required window/motion matrix.
- Command queue validation guard: `validate-animation-playtest-commands /tmp/nexus-tech-animation-playtest-commands.md` passes before a tester uses an exported queue.
- Playtest plan guard: `animation-playtest-plan /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md --output /tmp/nexus-tech-animation-playtest-plan.md` reports whether the handoff is blocked by the queue, still manual-required, or ready for signoff.
- Playtest plan validation guard: `validate-animation-playtest-plan /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md` passes before the plan is attached to handoff notes.
- Session setup guard: `prepare-animation-playtest-session --prefill-automated-gates` refreshes the report draft, command queue, and grouped open-item summary for handoff.
- Report draft guard: `draft-animation-playtest-report --prefill-automated-gates --output /tmp/nexus-tech-animation-playtest-report.md` writes the validator-required manual report rows and prefilled automated gate evidence before the human pass starts.
- Signoff guard: `validate-animation-playtest-report /tmp/nexus-tech-animation-playtest-report.md` passes before calling the manual animation pass complete; every automated gate row, window/motion cell, control row, scene row, game-feel row, release-blocker field, and decision field must be filled.
- Balance preflight: run the balance/long-session commands listed in the playtest prep artifact and either fix any `balance-audit` warning or name it as intentional pressure before adding more animation layers.
- CI guard: GitHub Actions runs headless 2D smoke checks plus motion, visual, animation-completeness, broad animation-matrix, and playtest-prep gates before the manual pass, then uploads `nexus-tech-2d-visual-audit`, `nexus-tech-2d-animation-matrix`, and `nexus-tech-2d-animation-playtest-prep` for review.
- Blocked commands: disabled or rejected actions show a distinct blocked card, warning pulse, and matching actor state instead of looking like a successful command.
- Title/menu: founder/save/archive/coach actor clips and archive comparison signals do not hide menu copy, save metadata, archive cards, or wizard rows.
- Pending event: option preview motion stays readable and actor clips do not distract from choice text.
- Action picker: picker, path-specific late-game choreography, and actor clips do not stack into unreadable motion; IPO, M&A, independence, and reset repair cues point at the correct panel/stat.
- Turn summary: founder/finance/customer/board/gate actor clips support the metric reveal instead of hiding timeline cards.
- Inspector/endgame/review: actor clips clarify record routing, exit-gate pressure, and postmortem handoff without hiding primary actions.
- Outcome overlay: outcome cinematic remains the dominant final-state animation.
- Compact window: repeat the run and summary checks around `820x620`.
- Reduced motion: animation is present but calmer than full mode.
- Off motion: actor timeline, sprite clips, pulses, cinematic rails, and overlay transitions are disabled while gameplay controls still work.

## Pass Criteria

- No important text is hidden by actor clips, tooltips, modals, or footer controls.
- A new player can identify the next intended action within five seconds on the run dashboard.
- Summary and outcome screens can be read without waiting for excessive animation.
- Full mode feels alive; reduced mode feels calmer; off mode is static enough for motion-sensitive players.
