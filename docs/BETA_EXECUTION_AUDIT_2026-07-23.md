# Beta Execution Audit - 2026-07-23

## Scope

This audit covers NEXUS TECH 0.314.0 at source baseline
`692acd82278df0601a8645682331a2627eb7a82a`. It validates the automated
beta-candidate baseline and prepares the next real session. It does not count
headless execution, generated artifacts, or owner rehearsal as human evidence.

## Decision

- Automated readiness: `pass`
- Human readiness: `manual-required`
- Human beta evidence: `0/6 current-version sessions`
- Featured campaign coverage: `0/6`
- Release decision: `do not tag yet`
- Expansion decision: keep the feature freeze until the human gate closes

## Automated Evidence

| Area | Result | Evidence |
| --- | --- | --- |
| Session preparation | pass | Fresh rehearsal and tester profiles are separate from the persistent evidence store |
| Recorder guard | pass | The unchanged recorder template is rejected before evidence can be written |
| Focused beta regressions | pass | 63 tests across beta preparation, First Archive Mission, convergence, UX clarity, decision quality, and scene chrome |
| Full test suite | pass | 1167 tests |
| Formatting and lint | pass | 143 files formatted; Ruff reported no issues |
| Content catalog | pass | 49 scenarios, 49 templates, 32 rivals, 202 events, 0 issues |
| Onboarding flow | pass | 5/5 checks |
| Campaign readiness | pass | 18/18 campaign and difficulty cells; 72/72 authored routes; no shutdowns |
| Decision quality | pass with advisory watches | All 54 heuristic runs recorded operating decisions; 13 cells need comparison with human notes |
| 2D motion | pass | Full, reduced, and off modes across three viewports; 44 commands and 89 inspector actions |
| 2D visual audit | pass | 60 full-motion captures at `60:3428ded2`; 60 motion-off captures at `60:c30ae657` |
| Responsive layout | pass | 180 captures; 0 layout and 0 typography violations |
| Animation completeness | pass | Automated baseline `45:a118a78b`; manual read speed remains advisory |
| Broad animation matrix | pass | 21/21 scenario and seed cells |
| Accessibility smoke | pass | 820x620, reduced motion, large text, and high contrast |
| Package smoke | pass | Wheel version and doctor run from the installed wheel, not the source tree |

The built wheel is `nexus_tech-0.314.0-py3-none-any.whl` with SHA-256
`619d4c0ce2c9f829a21453cf2425f9e171e2fab597f455df8b583d3df9427c54`.
The wheel includes the scene-chrome policy and reports version 0.314.0.

## Visual Review

The 820x620 full-motion captures for Title Menu, Run Dashboard, Help, Endgame,
Turn Summary, and Review showed no overlapping text, clipped controls, or
actions outside their panels. Automated geometry confirms containment, but
still images do not prove that a first-time player understands the hierarchy or
can read it at the intended pace.

## Decision-Quality Boundary

The automated decision-quality matrix produced 13 advisory watch cells. The
common candidate was `Grow Demand`, indicating a possible repeated preference
in autoplay. This is not sufficient evidence to remove actions or retune
balance. Compare the watch cells with observed player explanations and pacing
notes before changing the action catalog.

## Audit Execution Note

Run SDL-heavy layout and animation matrices sequentially, as CI does. One local
matrix run executed concurrently with layout and headless-window audits and
reported a transient Motion Mode Differentiation failure for
`enterprise_compliance` seed 13. The same cell passed alone with baseline
`45:13d9a7ff`, and the complete sequential matrix then passed 21/21. No
threshold or gameplay change was made for the non-reproducible contention
signal.

## Repository Hygiene

- No tracked or historical filename matched environment, database,
  credential, secret, private-key, or certificate patterns.
- Current tracked content and Git history contained no recognized private-key,
  GitHub, OpenAI-style, Slack, AWS, or Google credential patterns.
- No tracked personal filesystem path or personal email was found.
- Local databases, virtual environments, Headroom files, Node files, generated
  packets, screenshots, reports, and wheels remain ignored or outside the
  repository.
- The only tracked file above 1 MiB is ASCII Python test source.

## Required Human Work

1. Generate the current session packet:

   ```bash
   .venv313/bin/nexus-tech prepare-beta-playtest-session \
     --output /tmp/nexus-tech-beta-playtest-next.md
   ```

2. Complete the visible owner rehearsal from New Game through Pause recovery,
   both campaign decisions, Endgame, Save & Archive, and Progress. Do not record
   it as human beta evidence.
3. Observe six first-time sessions, one per featured campaign, using a fresh
   tester profile and anonymous tester code for each session.
4. Require at least 80% unaided turn-one completion, 100% Pause/Back/Menu
   recovery, at least 80% trade-off recall, at least 80% Act 3 reach, and zero
   blocker sessions.
5. Fix only observed P0/P1 navigation, readability, wording, pacing, or gameplay
   defects, then rerun the complete release matrix.

Audio, arbitrary key remapping or controller support, localization, richer
visual assets, and new campaign content remain post-beta work.
