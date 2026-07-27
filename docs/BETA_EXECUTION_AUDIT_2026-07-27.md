# Beta Execution Audit - 2026-07-27

## Scope

This audit covers NEXUS TECH 0.319.0. It validates the human-beta retest
workflow, the six-campaign execution queue, schema 28 migration, and the 2D
motion-mode gate correction without treating automation, generated packets, or
owner rehearsal as human evidence.

## Decision

- Automated readiness: `pass`
- Product position: late-alpha beta candidate, approximately `83%`
- Human readiness: `manual-required`
- Human beta evidence: `0/6 current-version sessions`
- Archive route evidence: `0/24 authored routes`
- Review-readiness command: `blocked as expected`
- Release decision: `do not tag yet`
- Expansion decision: keep the feature freeze until the human gate closes

## Current Slice

Schema 28 adds an append-only `retest_of` relationship to structured beta
evidence. A failed active row remains in history, while one guarded retest from
a new first-time tester can become the active row. The relationship requires
the same campaign and game version, rejects a passing parent, rejects reused
tester codes, and permits only one direct child.

`beta-playtest-plan` exposes all six featured campaign lanes but selects only
one next session or retest. It allocates no tester code, copies no free-form
note, creates no gameplay profile, records no evidence, and cannot approve a
release. The generated session packet remains the only place that allocates the
next anonymous session and isolated gameplay profiles.

The motion-mode differentiation gate now checks animation density and disabled
state independently from transient reduced-mode timing watches. Genuine
reduced-mode stability failures still block through the dedicated performance
gates.

## Automated Evidence

| Area | Result | Evidence |
| --- | --- | --- |
| Full test suite | pass | 1210 tests |
| Formatting and lint | pass | 149 files formatted; Ruff reported no issues |
| Content catalog | pass | 49 scenarios, 49 templates, 32 rivals, 202 events, 0 issues |
| Human-beta guard | pass | Schema 27 migration, retest lineage, note-free plan, packet validation, and fail-closed review regressions |
| Human evidence boundary | pass | Plan and packet generation left the isolated evidence store at 0 rows |
| Campaign readiness | pass | 18/18 campaign and difficulty cells; 72/72 authored routes; no shutdowns |
| Decision quality | pass with advisory watches | All 54 heuristic runs recorded operating decisions; 13 cells require comparison with human notes |
| Onboarding flow | pass | 5/5 checks |
| 2D runtime smoke | pass | Standard and accessible 820x620 menu/play launches |
| Responsive layout | pass | 90 captures across two viewports and three motion modes; 0 layout and 0 typography violations |
| 2D visual audit | pass | 60 full-motion captures at `60:6317dffa`; 60 motion-off captures at `60:fde7e647` |
| 2D motion | pass | Full, reduced, and off modes across three viewports; 44 commands and 89 inspector actions |
| Animation completeness | pass | Automated baseline `45:47c2a961`; manual read speed remains advisory |
| Broad animation matrix | pass | 21/21 scenario and seed cells |
| Package smoke | pass | Wheel contains 141 files; installed-artifact version, schema 28 doctor, headless 2D launch, and dependency check passed |

## Repository Hygiene

- No tracked or packaged filename matches environment, credential, private-key,
  certificate, keystore, database, or package-registry secret patterns.
- Current non-ignored content, package content, and all 359 existing commits
  contain no recognized private-key, GitHub, OpenAI-style, Slack, AWS, Google,
  or Stripe credential signatures.
- No current or historical content contains this machine's personal path or
  configured email.
- Local databases, virtual environments, caches, Headroom files, Node
  dependencies, and package-manager files remain ignored and unstaged.
- The wheel and sdist contain the new execution-plan module and no risky local
  artifact.

## Required Human Work

1. Run the generated owner rehearsal at 820x620 without recording it as human evidence.
2. Observe six first-time sessions, one per featured campaign, using fresh isolated profiles and anonymous tester codes.
3. Require at least 80% unaided turn-one completion, 100% Pause/Back/Menu recovery, at least 80% trade-off recall, at least 80% Act 3 reach, and zero blocker sessions.
4. Fix each P0/P1 issue, then use the generated `--retest-of` command with a new first-time tester; never delete the original observation.
5. Compare real notes with the 13 advisory decision-quality watches before changing commands or balance.
6. Complete visible archive-route evidence and animation read-speed/control-feel signoff.
7. Run `beta-playtest-status --require-review-ready` and promote to beta only after it passes and a reviewer approves the release.

Audio, arbitrary key remapping or controller support, localization, richer
visual assets, and new campaign content remain post-beta work.
