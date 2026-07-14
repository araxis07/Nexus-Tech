# Beta Convergence - 2026-07-14

## Current Level

NEXUS TECH 0.288.0 is a late-alpha beta candidate with a complete vertical slice. The six featured campaigns have real three-act progression, and every combination of their Commitment and Consequence decisions now has deterministic native-goal evidence across all three difficulties. Archived endings derive discovery and mastery across all 24 authored routes, while live and archived reviews synthesize both choices into a Campaign Legacy. Terminal and 2D progression now show the complete six-campaign Route Atlas. The 2D shell has persistent local display/motion Settings, shared responsive frame geometry, one numbered decision route from objective to turn resolution, and an explicit Save & Archive ending action. Schema 26 adds isolated structured human-session evidence while migrating older saves additively.

The project is approximately 82% of the way to a defensible beta. Core simulation, persistence, navigation, responsive 2D presentation, campaign progression, deterministic testing, archive replay guidance, and release automation exist. The remaining gap is observed usability with representative players, not another content expansion.

## Release Changes

- Campaign decisions have priority over random events after turns 4 and 9 for Founder Journey, Bootstrap Studio, Technical Rebuild, Portfolio Machine, Debt Crunch, and Public Market Countdown.
- All 24 campaign options affect product, cash, debt, team, support, or governance values and apply a bounded long-run event-category bias.
- Campaign history is retained when old systemic events are pruned, and the selected path appears in the live HUD and run review.
- Completed-run archives now retain scenario, difficulty, both campaign choices, and terminal reason; `beta-evidence` reports local coverage while keeping manual signoff open.
- `record-beta-playtest-session` stores observed human-session evidence locally with anonymous tester codes, explicit real-session attestation, current-version isolation, duplicate protection, and sensitive-note rejection; `beta-playtest-status` evaluates the six manual gates without granting release approval.
- Archive evidence and meta progression derive route discovery, victories, shutdowns, average performance, and the next unexplored route across all 24 authored paths without changing saved rows or closing the manual gate.
- Terminal and 2D progression expose all six campaign route lanes together instead of showing only aggregate mastery or one next route.
- Live and archived reviews combine both decisions into one Campaign Legacy with a route label, accumulated event pressure, and final-act mandate.
- Completed-run review now separates `Save & Archive` from `Exit Unsaved`, making progression intent explicit.
- Focus View is the default run surface. It presents one decision hierarchy with at most six controls and keeps the full ten-control dashboard available with `0` on windows at least 940 pixels wide.
- Focus View now numbers Objective, Recommended Move, and End Turn Check; the recommendation includes urgency and skipped-action consequence, while the final card launches the existing preview/confirmation flow directly.
- Featured campaign goals cannot end a run before both authored campaign decisions are recorded, preventing economically strong branches from skipping Act 3.
- `campaign-readiness` defaults to each scenario's native goal, exercises four authored paths per campaign across Builder, Standard, and Founder with shared seeds, and reports goal completion/progress beside generic score and cash.
- Portfolio Machine now starts on a viable three-product footing, declares Portfolio Empire as its native goal, and survives the 20-turn three-seed route matrix on every difficulty.
- Bootstrap Studio and Portfolio Machine choices now expose clearer liquidity-versus-growth trade-offs; the current three-seed matrix reports pass for all 18 campaign/difficulty cells, all 72 routes, and zero shutdowns.
- Debt Crunch has an additional 24-turn, three-run-per-route regression across every difficulty to protect long-session recovery viability.
- Category Leader now measures one established Growth-or-Mature offering with reputation and quality, so focused Technical Rebuild and Public Market runs can complete their native goal without building an unrelated portfolio.
- Root CLI help now stays player-facing; `developer-tools` indexes hidden balance, audit, CI, and manual-QA commands while preserving direct invocation.
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
uv run nexus-tech beta-playtest-status
uv run nexus-tech campaign-readiness --runs 3 --turns 20 --seed-base 28500 --output /tmp/nexus-tech-campaign-readiness.md
uv run nexus-tech play-2d --scenario founder_journey --seed 283 --headless --max-frames 2 --window-size 820x620 --motion-mode reduced --ui-scale large --contrast-mode high
uv run nexus-tech balance-audit --scenario founder_journey --scenario bootstrap_studio --scenario technical_rebuild --scenario portfolio_machine --scenario debt_crunch --scenario public_market_countdown --runs 1 --turns 12 --seed-base 28300
uv run nexus-tech audit-2d-visual --scenario founder_journey --seed 282 --viewport 820x620 --viewport 1280x720 --viewport 1440x900
```

Automated coverage verifies campaign boundaries and delayed effects, event priority, all 72 campaign-route/difficulty cells, early-victory prevention, path retention, route-mastery derivation, Campaign Legacy synthesis, Save & Archive copy, additive migration through schema 26, archive evidence, structured-session validation, preference persistence/fallback, the 6-by-3 balance matrix, the long-session Debt Crunch envelope, catalog ceilings, Focus View layout, Settings typography, Pause recovery, accessibility-profile launch, and responsive containment.

## Human Evidence Still Required

Automation does not complete these gates:

1. Run at least six first-time sessions, with every featured campaign represented.
2. Confirm at least 80% complete turn one without operator help.
3. Confirm every tester can pause, back out, and return to the title menu unaided.
4. Confirm at least 80% can explain both campaign trade-offs after choosing.
5. Record zero blocker-level clipping, overlap, or unreadable controls in real windows.
6. Confirm representative sessions reach Act 3 without decision fatigue blocking progress.

No test or generated report should mark these observations complete without a human session.

The repository baseline is currently `0/6` current-version human sessions. Run `beta-playtest-status` before and after each real session. Only use `record-beta-playtest-session --confirm-human-session ...` after observing the session; the local SQLite row is evidence input, not automatic release approval.

Arbitrary key remapping is not part of 0.288.0. Keyboard-only control remains available through the documented bindings, but remapping and assistive-technology compatibility require separate design and real-device validation.

## Next Steps

1. Conduct the six-session usability pass and record each actual observation with `record-beta-playtest-session`; current automation and archive metrics do not count as these sessions.
2. Fix any observed navigation, copy, clipping, overlap, or control blocker before expanding gameplay.
3. Compare real player choice comprehension and pacing against Campaign Legacy and route-mastery guidance; tune only where observed behavior contradicts the intended trade-off.
4. Consolidate low-value actions only when playtest evidence shows repeated confusion.
5. Re-run the release-candidate matrix after any observed fix, then promote to beta only after all manual gates pass.
