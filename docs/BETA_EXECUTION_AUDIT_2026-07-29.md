# Beta Execution Audit - 2026-07-29

## Scope

This audit covers NEXUS TECH 0.321.0. It validates the fail-closed human-beta
packet handoff without changing gameplay balance, controls, frozen catalogs,
save schema 28, archive progression, or the human-evidence boundary.

## Decision

- Automated readiness: `pass`
- Product position: late-alpha beta candidate, approximately `83%`
- Human readiness: `manual-required`
- Human beta evidence: `0/6 current-version sessions`
- Archive route evidence: `0/24 authored routes`
- Release decision: `do not tag yet`
- Expansion decision: keep the feature freeze until the human gate closes

## Current Slice

Every generated human-beta packet now embeds its own required preflight command.
Manifest schema 3 binds the packet to its intended output path, current build,
evidence snapshot, command prefix, evidence store, tester profile, and owner
rehearsal profile. Validation rejects moved, edited, stale, or
profile-contaminated handoffs before either visible launch.

Preparation also rejects a packet output path that aliases the evidence, tester,
or rehearsal SQLite database. The same boundary covers each database's
`-journal`, `-wal`, and `-shm` sidecars so packet generation cannot overwrite
live evidence or gameplay state.

These guards do not record owner rehearsal, automated runs, screenshots, or
generated artifacts as human evidence. The first real target remains Learn /
`founder_journey`.

## Automated Evidence

| Area | Result | Evidence |
| --- | --- | --- |
| Full test suite | pass | 1220 tests |
| Formatting and lint | pass | 149 files formatted; Ruff reported no issues |
| Focused beta contracts | pass | 86 beta-playtest and beta-convergence tests |
| Content catalog | pass | 49 scenarios, 49 templates, 32 rivals, 202 events, 0 issues |
| Human-beta packet | pass | Manifest schema 3, embedded preflight, path binding, profile isolation, and collision guards |
| Human-beta gate | expected blocked | Fail-closed review command returned non-zero at truthful evidence `0/6` |
| Campaign readiness | pass | 18/18 campaign and difficulty cells; 72/72 authored route executions; no shutdowns |
| Decision quality | pass with advisory watches | 54 heuristic runs recorded operating decisions; 13 cells still require comparison with human notes |
| Accessible 2D smoke | pass | Large text, high contrast, reduced motion, and 820x620 headless menu/run launch |
| Responsive visual matrix | pass | 45 full-motion captures at `45:dea8ab4e`; 45 motion-off captures at `45:ee0bac1d` |
| 2D motion | pass | Reduced motion across three viewports; 44 commands and 89 inspector actions |
| Animation completeness | pass | Automated baseline `45:dea8ab4e`; manual read speed remains advisory |
| Package smoke | pass | Wheel contains 141 files; installed-artifact version and embedded packet preflight passed |

## Repository Hygiene

- No tracked filename matches environment, credential, private-key,
  certificate, keystore, database, or package-registry secret patterns.
- Current tracked content and existing Git history contain no recognized
  private-key, GitHub, OpenAI-style, Slack, AWS, Google, Stripe, personal
  workspace path, or personal email signature.
- Local databases, virtual environments, caches, Headroom files, Node
  dependencies, and package-manager files remain ignored and unstaged.
- The 0.321.0 wheel contains 141 expected package files and no risky local
  artifact.

## Required Human Work

1. Run the packet's embedded preflight immediately before the visible owner rehearsal.
2. Complete the owner rehearsal at 820x620 without recording it as human evidence.
3. Observe six first-time sessions, one per featured campaign, using fresh isolated profiles and anonymous tester codes.
4. Require at least 80% unaided turn-one completion, 100% Pause/Back/Menu recovery, at least 80% trade-off recall, at least 80% Act 3 reach, and zero blocker sessions.
5. Fix each observed P0/P1 issue, then use the generated `--retest-of` command with a new first-time tester.
6. Compare real notes with the 13 advisory decision-quality watches before changing commands or balance.
7. Complete visible archive-route evidence and animation read-speed/control-feel signoff.
8. Run `beta-playtest-status --require-review-ready` and promote to beta only after it passes and a reviewer approves the release.

Audio, arbitrary key remapping or controller support, localization, richer
visual assets, and new campaign content remain post-beta work.
