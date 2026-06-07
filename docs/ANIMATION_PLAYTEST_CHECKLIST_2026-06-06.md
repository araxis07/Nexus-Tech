# Animation Playtest Checklist - 2026-06-06

Use this checklist for the manual open-window pass that headless audits cannot judge.

## Build Under Review

- Version: `0.133.0`
- Focus: 2D actor/sprite timeline, blocked-action feedback, automated actor-readability and visual-fatigue guards, scene pacing, overlay readability, and motion-mode behavior.

## Commands

```bash
nexus-tech menu-2d --motion-mode full
nexus-tech play-2d --scenario founder_journey --seed 7 --motion-mode full
nexus-tech play-2d --scenario founder_journey --seed 7 --motion-mode reduced
nexus-tech play-2d --scenario founder_journey --seed 7 --motion-mode off
```

## Required Checks

- Title/menu flow: wizard, save slots, archive/meta, and title transitions remain readable.
- Run dashboard: founder/team/customer/board/product actor clips are visible without covering snapshot chips, stat bars, product cards, or action buttons.
- Automated guard: `audit-2d-animation` reports `actor-readability` for actor scenes before the manual open-window pass.
- Automated guard: `audit-2d-animation` reports `Visual Fatigue Budget` so clutter and bright-pixel pressure stay within deterministic limits before the manual pass.
- Blocked commands: disabled or rejected actions show a distinct blocked card, warning pulse, and matching actor state instead of looking like a successful command.
- Title/menu: founder/save/archive/coach actor clips do not hide menu copy, save metadata, or wizard rows.
- Pending event: option preview motion stays readable and actor clips do not distract from choice text.
- Action picker: picker, late-game choreography, and actor clips do not stack into unreadable motion.
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
