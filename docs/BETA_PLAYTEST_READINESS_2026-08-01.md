# Beta Playtest Readiness - 2026-08-01

## Scope

This record covers NEXUS TECH 0.325.0 after the beginner UX redesign. It
captures the truthful handoff state between automated release readiness and the
visible owner and first-time-player sessions required for beta promotion.

## Decision

- Automated readiness: `pass`
- Product position: late-alpha beta candidate, approximately `83%`
- Owner rehearsal: `incomplete`
- Human beta evidence: `0/6 current-version sessions`
- Campaign coverage: `0/6 featured campaigns`
- Archive route evidence: `0/24 authored routes`
- Release decision: `do not tag yet`
- Expansion decision: keep the feature freeze until observed usability passes

## Execution Results

The next-session packet targets Learn / `founder_journey`. Packet generation and
manifest preflight passed against the current 0.325.0 build and evidence
snapshot. Rehearsal and tester profiles remained isolated from the evidence
store.

Two guarded owner-rehearsal launches ended before a save or completed archive
was created. The post-window gate correctly returned non-zero with zero target
archives and retained the same retry action. It did not open the tester profile,
write a human-session row, or claim that any visible recovery route was tested.

The six-campaign execution queue remains ordered as Learn, Profit, Quality,
Portfolio, Debt, and Endgame, with only Learn marked as the next session. The
review-readiness command correctly fails closed while evidence remains `0/6`.

## Decision Quality Evidence

The deterministic decision-quality audit covered six scenarios, three
difficulties, three heuristic runs per cell, and 12 turns:

| Measure | Result |
| --- | --- |
| Difficulty cells | 18 |
| Heuristic runs | 54 |
| Automated ledger gate | pass |
| Advisory watch cells | 13 |
| Repeated candidate | Grow Demand |
| Human confirmation | required |

The advisory cells are not sufficient evidence to consolidate or rebalance a
command. A matching observation from a real first-time session is required
before gameplay tuning.

## Required Next Action

1. Re-run the guarded owner rehearsal and complete Learn / `founder_journey`.
2. Exercise Pause, Back, Menu, Continue, Help, and guided/full Endgame visibly.
3. Finish the route, choose Save & Archive, open Progress, and confirm Route
   Atlas before closing the window.
4. Require the automatic archive gate to pass before opening the tester profile.
5. Observe one real first-time tester without coaching and record only the
   resulting anonymous evidence.
6. Regenerate the plan after each real session until all six campaigns pass.

Generated packets, reports, gameplay databases, and SQLite sidecars remain
local temporary artifacts and are intentionally excluded from Git.
