# Beta Execution Audit - 2026-07-28

## Scope

This audit covers NEXUS TECH 0.320.0. It validates the evidence-preserving
run-clarity refinement across compact and desktop 2D layouts without changing
gameplay balance, fixed controls, save schema 28, frozen catalogs, or the
human-playtest evidence boundary.

## Decision

- Automated readiness: `pass`
- Product position: late-alpha beta candidate, approximately `83%`
- Human readiness: `manual-required`
- Human beta evidence: `0/6 current-version sessions`
- Archive route evidence: `0/24 authored routes`
- Release decision: `do not tag yet`
- Expansion decision: keep the feature freeze until the human gate closes

## Current Slice

The live run header now answers three questions in order: the current campaign
goal, the next move and timing, and the End Turn state. Score and market
diagnostics remain available in the existing Report surfaces instead of
competing with the decision loop.

Focus actions now lead with their player-facing names and place fixed shortcuts
in separate right-aligned badges. The wide six-action row omits redundant
button detail because the complete cost, timing, expected outcome, and skip
risk remain immediately below it in the decision preview.

Endgame readiness values now expose their `/100` scale, distinguish IPO and
acquisition readiness from Reset Risk, and state that lower Reset Risk is
safer. Exit calculations and command routes are unchanged.

Completed-run Review now labels each finding as Cause and Lesson, identifies
the first move for the next run, and presents Style, Outcome, Difficulty, and
route context as wrapping traits instead of full-width button-like rows.
Responsive finding cards use the available vertical budget to preserve
complete compact copy.

## Automated Evidence

| Area | Result | Evidence |
| --- | --- | --- |
| Full test suite | pass | 1210 tests |
| Formatting and lint | pass | 149 files formatted; Ruff reported no issues |
| Content catalog | pass | 49 scenarios, 49 templates, 32 rivals, 202 events, 0 issues |
| Onboarding flow | pass | 5/5 checks |
| Campaign readiness | pass | 18/18 campaign and difficulty cells; 72/72 authored route executions; no shutdowns |
| Decision quality | pass with advisory watches | All 54 heuristic runs recorded operating decisions; 13 cells still require comparison with human notes |
| Accessible 2D smoke | pass | Large text, high contrast, reduced motion, and 820x620 headless launch |
| Responsive visual matrix | pass | 60 full-motion captures at `60:cffce15f`; 60 motion-off captures at `60:45f7e700` |
| Focused visual review | pass | 15 compact captures at `15:0b5f32ae`; Run, Endgame, and Review PNGs inspected manually |
| 2D motion | pass | Full, reduced, and off modes across three viewports; 44 commands and 89 inspector actions |
| Animation completeness | pass | Automated baseline `45:1a09ab00`; manual read speed remains advisory |
| Broad animation matrix | pass | 21/21 scenario and seed cells |
| Human-beta handoff | pass | 0.320.0 execution plan, isolated session packet, and manifest validation; evidence remained 0 rows |
| Package smoke | pass | Wheel contains 141 files; installed-artifact version 0.320.0, schema 28 doctor, and headless 2D launch passed |

## Repository Hygiene

- No tracked or packaged filename matches environment, credential, private-key,
  certificate, keystore, database, or package-registry secret patterns.
- Current tracked content, package content, and all 360 existing commits contain
  no recognized private-key, GitHub, OpenAI-style, Slack, AWS, Google, or Stripe
  credential signatures.
- No current or historical content contains this machine's personal workspace
  path or personal email pattern.
- Local databases, virtual environments, caches, Headroom files, Node
  dependencies, and package-manager files remain ignored and unstaged.
- The 0.320.0 wheel contains 141 expected package files and no risky local
  artifact.

## Required Human Work

1. Run the generated owner rehearsal at 820x620 without recording it as human evidence.
2. Observe six first-time sessions, one per featured campaign, using fresh isolated profiles and anonymous tester codes.
3. Require at least 80% unaided turn-one completion, 100% Pause/Back/Menu recovery, at least 80% trade-off recall, at least 80% Act 3 reach, and zero blocker sessions.
4. Fix each observed P0/P1 issue, then use the generated `--retest-of` command with a new first-time tester.
5. Compare real notes with the 13 advisory decision-quality watches before changing commands or balance.
6. Complete visible archive-route evidence and animation read-speed/control-feel signoff.
7. Run `beta-playtest-status --require-review-ready` and promote to beta only after it passes and a reviewer approves the release.

Audio, arbitrary key remapping or controller support, localization, richer
visual assets, and new campaign content remain post-beta work.
