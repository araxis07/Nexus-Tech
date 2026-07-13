# UX and Gameplay Clarity - 2026-07-14

## Release Scope

Version 0.281.0 reduces decision friction without changing the save format. Internal action ids remain stable for routing, persistence, automation, and audits. Presentation layers now translate those ids into a smaller vocabulary before the player sees them, while a targeted Debt Crunch tune keeps its opening pressure inside the intended difficulty envelope.

## Player-Facing Changes

- The 194 internal action routes resolve to 99 visible concepts. Repeated enterprise, billing, onboarding, white-glove, channel, partner, and capital ladders appear as stable programs while retaining a stage label for diagnostics.
- Founder Journey, Bootstrap Studio, Technical Rebuild, Portfolio Machine, Debt Crunch, and Public Market Countdown each have three authored acts: Foundation on turns 1-4, Commitment on turns 5-9, and Consequence from turn 10 onward.
- The live header shows the active act, objective, decision lens, and next move. Compact layouts keep cash, runway, users, and action points visible even while first-turn guidance is active.
- The title menu gives Continue and New Game primary visual weight. Guides, saves, archives, and progression are secondary, and Quit remains isolated.
- The action footer displays no more than 12 controls. All keyboard routes remain available even when a direct button is not currently visible.
- Turn summaries explain the cash equation, demand movement, board/support pressure, and leading product result before presenting the next strategic move.
- Guided Opening, Coach, risk forecast, end-turn warnings, postmortems, events, endgame panels, and terminal dashboards share the same readable action labels.
- Debt Crunch starts with a slightly healthier demand base and its deterministic recovery policy repairs product drag before repaying debt; cash and principal remain unchanged so debt service still shapes every turn.

## Automated Gates

Run the focused clarity and convergence checks with:

```bash
uv run pytest -q tests/test_ux_clarity.py
uv run pytest -q tests/test_gameplay_convergence.py
```

The UX clarity gate verifies action-program consolidation, command humanization, all six three-act journeys, live HUD campaign context, and causal turn summaries. The convergence gate also runs Debt Crunch for 20 turns across Builder, Standard, and Founder so a future unavoidable opening collapse fails visibly.

The existing visual, layout, animation, content, balance, doctor, and full test gates remain required before release.

The motion gate reports average, P99, and absolute peak frame time. Pass/fail uses P99 to detect sustained jank while isolated operating-system scheduling pauses remain visible as peak advisories.

## Manual Evidence Boundary

Automated screenshots can prove containment, text fitting, route coverage, and deterministic rendering. They cannot prove that a new player understands the first turn, notices pause/back controls, or makes an endgame choice without explanation.

The following work therefore remains open until observed in real windows by a human:

1. Complete the onboarding evidence matrix at 820x620, 1280x720, and 1440x900.
2. Record first-turn comprehension, pause/back discoverability, and turn-summary comprehension.
3. Validate the tuned Debt Crunch path with specialist human sessions beyond turn 10 and compare those observations with the deterministic envelope.
4. Promote the product from late alpha to beta only after representative players finish runs without operator guidance.

No automated command in this release marks those manual observations complete.
