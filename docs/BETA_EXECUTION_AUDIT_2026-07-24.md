# Beta Execution Audit - 2026-07-24

## Scope

This audit covers NEXUS TECH 0.315.0 at source baseline
`237282858f4fc95ebaab172ba8eb3f6a73c5677e`. It validates the bounded
decision-preview clarity slice without treating automated execution, generated
artifacts, or owner rehearsal as human evidence.

## Decision

- Automated readiness: `pass`
- Human readiness: `manual-required`
- Human beta evidence: `0/6 current-version sessions`
- Archive route evidence: `0/24 authored routes`
- Release decision: `do not tag yet`
- Expansion decision: keep the feature freeze until the human gate closes

## Automated Evidence

| Area | Result | Evidence |
| --- | --- | --- |
| Decision preview | pass | Focus shows `NEXT / COST / WHEN`, expected outcome, and skip risk as three measured lines |
| AP consistency | pass | Review and resolution actions remain free; operating actions remain one AP; Recommended disables at zero AP |
| Focused beta regressions | pass | 99 tests across beta preparation, First Archive Mission, convergence, decision systems, scene chrome, and UX clarity |
| Full test suite | pass | 1181 tests |
| Formatting and lint | pass | 146 files formatted; Ruff reported no issues |
| Content catalog | pass | 49 scenarios, 49 templates, 32 rivals, 202 events, 0 issues |
| Onboarding flow | pass | 5/5 checks |
| Campaign readiness | pass | 18/18 campaign and difficulty cells; 72/72 authored routes; no shutdowns |
| Decision quality | pass with advisory watches | All 54 heuristic runs recorded operating decisions; 13 cells still need comparison with human notes |
| 2D motion | pass | Full, reduced, and off modes across three viewports; 44 commands and 89 inspector actions |
| 2D visual audit | pass | 60 full-motion captures at `60:6317dffa`; 60 motion-off captures at `60:fde7e647` |
| Responsive layout | pass | 90 CI-target captures; 0 layout and 0 typography violations |
| Animation completeness | pass | Automated baseline `45:47c2a961`; manual read speed remains advisory |
| Broad animation matrix | pass | 21/21 scenario and seed cells |
| Accessibility smoke | pass | 820x620, reduced motion, large text, and high contrast |
| Package smoke | pass | Version, doctor, and headless 2D launch ran from the installed wheel |

The built wheel is `nexus_tech-0.315.0-py3-none-any.whl` with SHA-256
`660cb813c8c3a8c3f99eb0e4777f2953e3a08d5513c927f7c46f0475aad4e058`.
The wheel contains 139 files, includes the decision-preview and shared AP
policies, and reports version 0.315.0.

## Visual Review

The 820x620 Run Dashboard was inspected from the generated full-motion capture.
The six actions remain in two balanced rows. The decision preview stays below
the buttons, uses separate semantic colors for outcome and risk, and fits all
three lines without overlap, hidden text, or ellipsis. Full and motion-off
captures also passed the automated contrast, clutter, containment, and
typography checks.

## Gameplay Boundary

This slice exposes existing Turn Coach and Strategic Rhythm information. It
does not add commands, change action outcomes, alter AP costs, retune balance,
modify content catalogs, or change persistence schema 27. The 13 decision
quality watches remain advisory; `Grow Demand` must not be changed from
autoplay evidence alone.

## Repository Hygiene

- No current or historical filename matched environment, credential, private-key, certificate, keystore, database, or package-registry secret patterns.
- Current tracked content and all 354 commits contained no recognized private-key, GitHub, OpenAI-style, Slack, AWS, Google, or Stripe credential signatures.
- No tracked current or historical content contained this machine's personal path or personal email patterns.
- The local `nexus-tech.db` exists only as an ignored gameplay database and is not tracked or staged.
- Environment, database, virtualenv, Headroom, Node, generated QA, screenshot, report, and wheel outputs remain ignored or outside the repository.
- Certificate, keystore, registry credential, and service-account filename guards were added to `.gitignore`.
- The only tracked file above 1 MiB is ASCII Python test source.

## Required Human Work

1. Run the generated 0.315.0 owner rehearsal at 820x620 without recording it as human evidence.
2. Confirm the new decision preview can be understood at normal play speed, not only in a still capture.
3. Observe six first-time sessions, one per featured campaign, using fresh isolated tester profiles and anonymous tester codes.
4. Require at least 80% unaided turn-one completion, 100% Pause/Back/Menu recovery, at least 80% trade-off recall, at least 80% Act 3 reach, and zero blocker sessions.
5. Compare real notes with the 13 advisory decision-quality watches before considering any command or balance change.
6. Promote to beta only after the human gates pass and a reviewer makes the release decision.

Audio, arbitrary key remapping or controller support, localization, richer
visual assets, and new campaign content remain post-beta work.
