# Strategic Rhythm - 2026-07-16

## Purpose

Strategic Rhythm gives terminal and 2D players one derived sequence:

`Goal > Plan > Move > Resolve > Later`

It combines existing campaign, Quarter Plan, Turn Coach, Risk Forecast, End-Turn Preview, and Decision Ledger state. It does not add a command, content entry, balance modifier, save field, or release approval signal.

## Surface Contract

1. Goal shows the active campaign act and objective.
2. Plan shows roadmap, budget, completed Quarter Plan targets, deadline, and weakest target.
3. Move shows one executable recommendation, urgency, rationale, and skipped-action trade-off.
4. Resolve shows whether End Turn is ready, risky, blocked, or complete.
5. Later shows the current turn's latest decision follow-on, otherwise the next distinct forecast or Coach horizon.

Guided Opening is authoritative before Act 3. Endgame-gate advice may appear from turn 10 onward, but it must not displace the first-run operating loop on opening turns.

## Presentation Contract

- The live terminal dashboard uses one Strategic Rhythm panel; detailed Coach, Risk Forecast, and End-Turn Preview panels remain in the Run Report.
- Focus View keeps its existing three-card geometry and six-control ceiling. Plan progress is folded into the Objective card and snapshot lane; delayed follow-on is folded into End Turn and hover guidance.
- Turn summaries use the next Strategic Rhythm move instead of presenting a premature exit-gate command.
- Internal command identifiers remain available for routing and diagnostics but do not appear in actionable hover copy.

## Evidence Boundary

Automated tests can verify derivation, command validity, act ordering, text safety, and responsive containment. They cannot prove comprehension or decision fatigue. The six-session human beta gate remains required and currently starts from `0/6` current-version sessions.
