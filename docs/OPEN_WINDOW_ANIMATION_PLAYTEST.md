# Open-Window Animation Playtest

Use this framework after headless CI gates pass. The goal is to judge motion feel, text readability, and control clarity that automated captures cannot fully score.

## Required Preflight

Run these first and stop if any command fails:

```bash
uv run nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 2
uv run nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 1 --motion-mode reduced
uv run nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 1 --motion-mode off
uv run nexus-tech audit-2d-visual --scenario founder_journey --seed 7 --output-dir /tmp/nexus-tech-visual-audit/full
uv run nexus-tech audit-2d-visual --scenario founder_journey --seed 7 --motion-mode off --output-dir /tmp/nexus-tech-visual-audit/off
uv run nexus-tech audit-2d-animation --scenario founder_journey --seed 7 --frames 1
uv run nexus-tech audit-2d-animation-matrix --frames 1 --output /tmp/nexus-tech-animation-matrix.md
uv run nexus-tech prepare-2d-animation-playtest --frames 1 --output /tmp/nexus-tech-animation-playtest-prep.md
```

Do not commit generated PNG captures or local readiness reports. Use `/tmp/nexus-tech-visual-audit`, `/tmp/nexus-tech-animation-matrix.md`, and `/tmp/nexus-tech-animation-playtest-prep.md` locally or the `nexus-tech-2d-visual-audit`, `nexus-tech-2d-animation-matrix`, and `nexus-tech-2d-animation-playtest-prep` GitHub Actions artifacts for review. Start with `visual-audit-summary.md`, the animation matrix Markdown, and the playtest prep report before opening individual PNG captures.

The generated playtest prep report also lists balance and long-session preflight commands. Run those before the visible-window pass; any balance `watch` or `fail` should be fixed or explicitly named as intentional scenario pressure before adding more animation layers.

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
| Title/Menu | Wizard, save slots, archives, meta board, and title actors never hide copy or actions |
| Live Dashboard | Founder/team/customer/board/product actors do not cover stat chips, product cards, or action buttons |
| Action Picker | Picker cards, late-game choreography, and action feedback do not compete for the same focal point |
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
- Any missing/unclear scene handoff transition or transition active in motion-mode off is a release blocker.
- Any unclear pause, back, help, save, or menu behavior is a release blocker.
- Any `Actor State Coverage`, `Action Feedback Clarity`, `Scene Transition Handoff`, `Control Affordance Coverage`, `Control Replay Safety`, `UI Layout Safety`, `Typography Safety`, `Readability Guard`, `Animation Pacing Budget`, `Motion Mode Differentiation`, `Long Session Motion Stress`, `Long Session Visual Readiness`, `Scene Motion Profile`, `Visual Fatigue Budget`, `actor-pose-depth`, or `actor-readability` audit failure is a release blocker.
- Any `audit-2d-animation-matrix` failure in the default seven-scenario, three-seed presentation set is a release blocker.
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
