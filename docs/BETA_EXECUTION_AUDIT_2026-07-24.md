# Beta Execution Audit - 2026-07-24

## Scope

This audit covers NEXUS TECH 0.316.0 at source baseline
`7167b9be2af55e840d9e142d4c3b15f5055e416a`. It validates the fail-closed
human-beta review-readiness guard without treating automated execution,
generated packets, or owner rehearsal as human evidence.

## Decision

- Automated readiness: `pass`
- Human readiness: `manual-required`
- Human beta evidence: `0/6 current-version sessions`
- Archive route evidence: `0/24 authored routes`
- Review-readiness command: `blocked as expected`
- Release decision: `do not tag yet`
- Expansion decision: keep the feature freeze until the human gate closes

## Human-Evidence Guard

`beta-playtest-status` remains an informative command with a successful exit
while evidence is incomplete. Adding `--require-review-ready` now returns exit
code `1` at `0/6`, prints every unresolved criterion, and returns success only
for six distinct current-version testers covering all six featured campaigns
with the required outcomes and no blockers. A successful guard still says that
explicit reviewer approval is required.

The generated 0.316.0 session packet includes this guard after evidence refresh
and uses a separate fail-closed command when evidence becomes ready for manual
review. Preparation allocated distinct temporary rehearsal and tester profiles,
wrote only to `/tmp`, and did not create a human-session row.

## Automated Evidence

| Area | Result | Evidence |
| --- | --- | --- |
| Human-beta guard regressions | pass | 35 focused tests cover preparation, profile isolation, blocked evidence, review-ready evidence, and manual handoff |
| Full test suite | pass | 1184 tests |
| Formatting and lint | pass | 146 files formatted; Ruff reported no issues |
| Content catalog | pass | 49 scenarios, 49 templates, 32 rivals, 202 events, 0 issues |
| Onboarding flow | pass | 5/5 checks |
| Campaign readiness | pass | 18/18 campaign and difficulty cells; 72/72 authored routes; no shutdowns |
| Decision quality | pass with advisory watches | All 54 heuristic runs recorded operating decisions; 13 cells still need comparison with human notes |
| 2D motion | pass | Full, reduced, and off modes across three viewports; 44 commands and 89 inspector actions |
| 2D visual audit | pass | 60 full-motion captures at `60:6317dffa`; 60 motion-off captures at `60:fde7e647` |
| Responsive layout | pass | 180 captures across four viewports and three motion modes; 0 layout and 0 typography violations |
| Animation completeness | pass | Automated baseline `45:47c2a961`; manual read speed remains advisory |
| Broad animation matrix | pass | 21/21 scenario and seed cells |
| Accessibility smoke | pass | 820x620, reduced motion, large text, and high contrast |
| Package smoke | pass | Installed-wheel version, doctor, and headless 2D launch passed |

The built wheel is `nexus_tech-0.316.0-py3-none-any.whl` with SHA-256
`0063aa121a0c0e6cc055a484cb7f589e957092255914e9bddaf451bd7ddff89f`.
It contains 139 files and reports version 0.316.0. `pip check` reported no
broken requirements.

## Gameplay Boundary

This slice changes release tooling only. It does not add commands to the game,
change action outcomes, alter AP costs, retune balance, modify content catalogs,
or change persistence schema 27. The 13 decision-quality watches remain
advisory; `Grow Demand` must not be changed from autoplay evidence alone.

## Repository Hygiene

- The current tree contains 183 tracked files and no unexpected untracked file.
- No current or historical filename matched environment, credential,
  private-key, certificate, keystore, database, or package-registry secret
  patterns.
- Current tracked content and all 355 commits contained no recognized
  private-key, GitHub, OpenAI-style, Slack, AWS, Google, or Stripe credential
  signatures.
- No tracked current or historical content contained this machine's personal
  path or configured personal email.
- The installed wheel contained no risky filename, credential signature, or
  personal path.
- The local `nexus-tech.db` remains ignored and was not staged.
- The only tracked file above 1 MiB is ASCII Python test source.

## Required Human Work

1. Run the generated 0.316.0 owner rehearsal at 820x620 without recording it as
   human evidence.
2. Confirm the decision preview and review-readiness wording at normal play
   speed, not only in automated output.
3. Observe six first-time sessions, one per featured campaign, using fresh
   isolated tester profiles and anonymous tester codes.
4. Require at least 80% unaided turn-one completion, 100% Pause/Back/Menu
   recovery, at least 80% trade-off recall, at least 80% Act 3 reach, and zero
   blocker sessions.
5. Compare real notes with the 13 advisory decision-quality watches before
   considering any command or balance change.
6. Run `beta-playtest-status --require-review-ready` and promote to beta only
   after it passes and a reviewer makes the release decision.

Audio, arbitrary key remapping or controller support, localization, richer
visual assets, and new campaign content remain post-beta work.
