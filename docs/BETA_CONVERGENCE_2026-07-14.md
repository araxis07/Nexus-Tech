# Beta Convergence - 2026-07-14

## Current Level

NEXUS TECH 0.282.0 is a late-alpha beta candidate with a complete vertical slice. The six featured campaigns now have real three-act progression: Foundation establishes the run, a mandatory Commitment decision opens Act 2, and a mandatory Consequence decision opens Act 3. Each choice changes existing simulation state and survives save/load without a schema migration.

The project is approximately 80% of the way to a defensible beta. Core simulation, persistence, navigation, responsive 2D presentation, campaign progression, deterministic testing, and release automation exist. The remaining gap is observed usability and tuning with representative players, not another content expansion.

## Release Changes

- Campaign decisions have priority over random events after turns 4 and 9 for Founder Journey, Bootstrap Studio, Technical Rebuild, Portfolio Machine, Debt Crunch, and Public Market Countdown.
- All 24 campaign options affect product, cash, debt, team, support, or governance values already covered by SQLite persistence.
- Campaign history is retained when old systemic events are pruned, and the selected path appears in the live HUD and run review.
- Focus View is the default run surface. It presents one decision hierarchy and keeps the full dashboard available with `0` on windows at least 940 pixels wide.
- The visible action bar is capped at 10 controls. Every existing command remains reachable through deep-panel keys, Coach, or inspectors.
- Title shortcuts now follow their visible order: `1` Continue, `2` New Game, `3` Guide, `4` Saves, `5` Archives, `6` Progress, and `7` Quit.
- Repeated saves now preserve parent product rows while dependent account, employee, pipeline, partnership, and event rows are replaced safely.

## Feature Freeze

The beta ceiling is fixed at:

- 49 scenarios
- 49 product templates
- 32 rival archetypes
- 194 internal turn actions
- 99 player-facing programs
- 202 systemic events

`tests/test_beta_convergence.py` fails if any lane grows beyond this ceiling. Campaign depth, balance, readability, bug fixes, and removal or consolidation remain allowed. New catalog entries require an explicit post-beta decision.

## Automated Evidence

The release must pass:

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest -q
uv run pytest -q tests/test_beta_convergence.py
uv run nexus-tech validate-content
uv run nexus-tech audit-2d-visual --scenario founder_journey --seed 282 --viewport 820x620 --viewport 1280x720 --viewport 1440x900
```

Automated coverage verifies campaign boundaries and effects, event priority, path retention, SQLite round trips, catalog ceilings, Focus View layout, action-bar limits, and responsive containment.

## Human Evidence Still Required

Automation does not complete these gates:

1. Run at least six first-time sessions, with every featured campaign represented.
2. Confirm at least 80% complete turn one without operator help.
3. Confirm every tester can pause, back out, and return to the title menu unaided.
4. Confirm at least 80% can explain both campaign trade-offs after choosing.
5. Record zero blocker-level clipping, overlap, or unreadable controls in real windows.
6. Confirm representative sessions reach Act 3 without decision fatigue blocking progress.

No test or generated report should mark these observations complete without a human session.

## Next Steps

1. Conduct the six-session usability pass and record actual observations in the existing onboarding and animation evidence workflow.
2. Fix any navigation, copy, or layout blocker before adjusting balance.
3. Compare each campaign option's pick rate and Act 3 survival outcome; tune effects that are dominant or misleading.
4. Consolidate low-value actions only when playtest evidence shows repeated confusion.
5. Run a final release-candidate matrix across all three difficulty modes, then promote to beta only after the manual gates pass.
