# Beta Convergence - 2026-07-14

## Current Level

NEXUS TECH 0.284.0 is a late-alpha beta candidate with a complete vertical slice. The six featured campaigns have real three-act progression, and the 2D shell now has persistent local display/motion Settings plus shared responsive frame geometry. Schema 25 adds frontend preferences independently of save slots while preserving the schema-24 archive migration and older saves.

The project is approximately 80% of the way to a defensible beta. Core simulation, persistence, navigation, responsive 2D presentation, campaign progression, deterministic testing, and release automation exist. The remaining gap is observed usability and tuning with representative players, not another content expansion.

## Release Changes

- Campaign decisions have priority over random events after turns 4 and 9 for Founder Journey, Bootstrap Studio, Technical Rebuild, Portfolio Machine, Debt Crunch, and Public Market Countdown.
- All 24 campaign options affect product, cash, debt, team, support, or governance values and apply a bounded long-run event-category bias.
- Campaign history is retained when old systemic events are pruned, and the selected path appears in the live HUD and run review.
- Completed-run archives now retain scenario, difficulty, both campaign choices, and terminal reason; `beta-evidence` reports local coverage while keeping manual signoff open.
- Focus View is the default run surface. It presents one decision hierarchy with at most six controls and keeps the full ten-control dashboard available with `0` on windows at least 940 pixels wide.
- All 2D launch paths support `--ui-scale compact|standard|large` and `--contrast-mode standard|high` in addition to motion controls.
- Title shortcuts now follow their visible order: `1` Continue, `2` New Game, `3` Guide, `4` Saves, `5` Archives, `6` Progress, `7` Settings, and `8` Quit.
- Title and Pause Settings apply text scale, contrast, and motion live, persist locally, and follow scene transitions without altering gameplay save slots.
- Title, Run, Review, and Turn Summary use shared responsive frame profiles that reserve navigation, header, content, and footer regions.
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
uv run nexus-tech beta-evidence
uv run nexus-tech play-2d --scenario founder_journey --seed 283 --headless --max-frames 2 --window-size 820x620 --motion-mode reduced --ui-scale large --contrast-mode high
uv run nexus-tech balance-audit --scenario founder_journey --scenario bootstrap_studio --scenario technical_rebuild --scenario portfolio_machine --scenario debt_crunch --scenario public_market_countdown --runs 1 --turns 12 --seed-base 28300
uv run nexus-tech audit-2d-visual --scenario founder_journey --seed 282 --viewport 820x620 --viewport 1280x720 --viewport 1440x900
```

Automated coverage verifies campaign boundaries and delayed effects, event priority, path retention, schema-24-to-25 migration, archive evidence, preference persistence/fallback, the 6-by-3 balance matrix, catalog ceilings, Focus View layout, Settings typography, Pause recovery, accessibility-profile launch, and responsive containment.

## Human Evidence Still Required

Automation does not complete these gates:

1. Run at least six first-time sessions, with every featured campaign represented.
2. Confirm at least 80% complete turn one without operator help.
3. Confirm every tester can pause, back out, and return to the title menu unaided.
4. Confirm at least 80% can explain both campaign trade-offs after choosing.
5. Record zero blocker-level clipping, overlap, or unreadable controls in real windows.
6. Confirm representative sessions reach Act 3 without decision fatigue blocking progress.

No test or generated report should mark these observations complete without a human session.

Arbitrary key remapping is not part of 0.284.0. Keyboard-only control remains available through the documented bindings, but remapping and assistive-technology compatibility require separate design and real-device validation.

## Next Steps

1. Run `beta-evidence`, then conduct the six-session usability pass and record actual observations in the existing onboarding and animation evidence workflow.
2. Fix any navigation, copy, or layout blocker before adjusting balance.
3. Compare each campaign option's pick rate and Act 3 survival outcome; tune effects that are dominant or misleading.
4. Consolidate low-value actions only when playtest evidence shows repeated confusion.
5. Run a final release-candidate matrix across all three difficulty modes, then promote to beta only after the manual gates pass.
