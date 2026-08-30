# NEXUS TECH Project Status

## Current Classification

- Version: 0.329.0
- Status: Stable Alpha
- Operating mode: bounded Empire Mode preview
- Persistence schema: 28
- Scope: Standard baseline frozen; Empire vertical slice open for validation

Version 0.329.0 retains the complete local vertical slice and adds an optional long-form `Founder Empire` scenario. Players can start a guided, full, or Empire run, make turn-based operating decisions, pause and recover navigation, save and continue, reach guided or full endgame, archive a completed run, and inspect campaign progress and the Route Atlas. The terminal and 2D interfaces use the same simulation and SQLite persistence model.

Stable Alpha is the highest defensible classification today. Automated checks establish implementation health, but they do not establish that a person completed and understood the full owner journey or the new Turn 25 Empire pacing.

## Empire Mode Preview - 2026-08-31

- `empire_founder_journey` is a separate opt-in scenario; Standard scenarios retain their original pacing and victory rules.
- The five Empire eras are Foundation (1-5), Growth (6-10), Scale (11-16), Expansion (17-24), and Legacy (25+).
- The selected campaign goal becomes an Operating Flywheel, Platform Ecosystem, or Category Standard Scale Thesis.
- Territory control is derived from existing products, users, accounts, partners, and competitors across the four existing customer segments.
- Rivals counter the strongest territory on a deterministic late-run cadence, while platform, market, and leadership state can surface one dominant crisis.
- Empire state requires no schema migration. Save/load persists the existing source state and reconstructs the strategy layer deterministically.
- Empire automated gates do not count as human evidence. Its pacing, comprehension, and Turn 25 completion path remain manually unverified.

### 0.329.0 Automated Verification

| Gate | Result | Evidence |
| --- | --- | --- |
| Ruff lint and format | PASS | 157 Python files; no lint or format findings |
| Full test suite | PASS | 1,296 tests with warnings treated as errors |
| Content catalog | PASS | 50 total scenarios, 49 templates, 32 rivals, 202 events, 0 issues |
| Frozen Beta catalog | PASS | Original 49-scenario Beta ceiling remains unchanged; Empire is an explicit preview lane |
| Persistence | PASS | Installed-wheel Empire save; schema 28, SQLite integrity, and foreign keys healthy |
| Responsive Empire layout | PASS | 117/117 captures across 820x620, 960x640, and 1440x900; large text 39/39 at 820x620 |
| Empire animation | PASS WITH ADVISORY | Automated animation gate passed; human timing and control feel remain unverified |
| Long-run stability | PASS WITH ADVISORY | Three deterministic 30-turn runs survived without crash or shutdown; autoplay did not complete the portfolio goal |
| Package build | PASS | 0.329.0 source distribution and wheel built; installed-wheel version, content, 2D launch, and save health passed |
| Secret and file scan | PASS | No database, environment file, credential, private key, token, personal path, or generated capture is included |
| Empire human completion | NOT VERIFIED | No owner or tester has completed the Turn 25 Empire path |

The long-run batch is a stability check only. It does not establish that the
Empire economy is well paced, that the objective is easy to understand, or that
a human can complete the selected Scale Thesis without decision fatigue.

## Implemented And Automated

- Six featured campaigns, 24 authored routes, three difficulties, and three campaign phases
- Turn simulation, trade-offs, events, teams, products, finance, endgame, review, and archive progression
- Local SQLite saves, schema migration, integrity checks, save slots, continuation, and archive records
- Pause, Back, Menu, Continue, Help, Guided/Full Endgame, Save & Archive, Progress, and Route Atlas flows
- Responsive 2D layout coverage across 39 surfaces, supported viewports, text scales, contrast profiles, and motion modes
- Deterministic gameplay, content, persistence, layout, visual, animation, package-build, and CI gates
- Optional Empire scenario, era pacing, Scale Thesis, territory map, rival response, and save-compatible derived strategy state

The closure sprint reruns these gates on the final commit. Their result must be reported with the commit and CI link; this document does not replace executable evidence.

## Closure Sprint Evidence - 2026-08-09

| Gate | Result | Evidence |
| --- | --- | --- |
| Ruff lint and format | PASS | 154 files formatted; no lint findings |
| Full test suite | PASS | 1,260 tests |
| Content catalog | PASS | 49 scenarios, 49 templates, 32 rivals, 202 events, 0 issues |
| Persistence | PASS | Schema 28; SQLite integrity and foreign keys healthy |
| Campaign readiness | PASS | 18/18 cells and 72 authored route exercises |
| Decision ledger | PASS WITH ADVISORY | 54 heuristic runs; 13 watch cells still require human confirmation |
| Responsive layout matrix | PASS | 702/702 CI-profile captures; 0 layout or typography violations |
| Animation matrix | PASS | 21/21 scenario/seed cells on the isolated serial rerun |
| Package build | PASS | Version 0.328.0 source distribution and wheel built locally |
| Secret and file scan | PASS | No tracked database, environment file, credential, key, token, or generated capture |
| Owner Rehearsal | INCOMPLETE | 0 target archives and 0 complete target paths |
| Human beta evidence | INCOMPLETE | 0/6 sessions and 0/6 featured campaigns |

The first animation-matrix attempt ran concurrently with the layout matrix and reported one `Motion Off Gate` failure. The exact cell passed in isolation, and the complete 21-cell matrix then passed when rerun serially like CI. The failure was not reproducible and did not justify a product change.

### Owner Rehearsal Checklist

| Check | Result |
| --- | --- |
| Packet preflight and isolated fresh profile | PASS |
| First turn | NOT VERIFIED |
| Pause and Back | NOT VERIFIED |
| Menu and Continue | NOT VERIFIED |
| Help | NOT VERIFIED |
| Campaign trade-offs | NOT VERIFIED |
| Guided and Full Endgame | NOT VERIFIED |
| Save & Archive | FAIL - no archive was created |
| Progress and Route Atlas | NOT VERIFIED |

`NOT VERIFIED` means no truthful owner observation was available. It is not recorded as a product defect and cannot be promoted to `PASS` by an automated test.

### Follow-up Owner Rehearsal - 2026-08-10

- Baseline commit `aae1ad480d397cf3822ce164f350e694b2e9d58f` was clean, matched `origin/main`, and had a successful GitHub CI run before launch.
- The new packet passed preflight and used separate fresh rehearsal, tester, and evidence database paths.
- The visible window closed with reason `quit`; the rehearsal profile contained 0 saves, 0 archives, 0 complete target paths, and no recorded route.
- Packet isolation passed, Save & Archive failed, and First Turn, Help, Pause/Back, Menu/Continue, both trade-offs, Guided/Full Endgame, Progress, and Route Atlas remain `NOT VERIFIED` without a direct owner report.
- Human evidence remained 0/6 sessions and 0/6 represented campaigns. The rehearsal was not recorded as a human session.
- Ruff, 1,260 tests, content and save validation, 702 layout captures, and all 21 animation cells passed after the window closed.
- No reproducible P0/P1 was reported. The release remains Stable Alpha in maintenance mode.

### Maintenance Patch 0.328.1 - 2026-08-11

- SQLite transactions now close their underlying connections explicitly after success or rollback instead of waiting for garbage collection.
- Persistence, beta evidence, and Owner Rehearsal regressions run cleanly with warnings treated as errors.
- CI installs the built wheel into an isolated environment and exercises version, content, diagnostics, headless 2D launch, and save health outside the source tree.
- Persistence schema 28, gameplay, balance, controls, UI, animation, content, archive evidence, and human evidence are unchanged.

## Manual Evidence Still Required

- Owner Rehearsal: incomplete
- Valid human playtest sessions: 0/6
- Featured campaigns represented by valid human sessions: 0/6
- Owner archive and Route Atlas handoff: not yet observed
- Human confirmation of readability, pacing, decision comprehension, and motion comfort: not yet established

Owner Rehearsal is an operator preflight only. It must never be inserted into the human evidence database or counted toward the six sessions.

## Gameplay Change Control - 2026-08-19

The 0.328.1 decision-quality baseline passed its automated ledger gate across 54
heuristic runs. Thirteen of 18 scenario/difficulty cells retained an advisory
watch, all led by repeated `Grow Demand`. In-memory policy attribution identifies
the three `portfolio_machine` cells as 100% default-fallback autoplay-policy
watches; the other ten remain possible gameplay candidates, with the highest raw
repetition in `public_market_countdown`. Neither class is a gameplay failure or
authorizes balance work without matching real-player observations.

Future gameplay discovery, conditional tuning, Debt Crunch late-game review, and
post-beta capability order are bounded in the
[Gameplay Validation Backlog](GAMEPLAY_VALIDATION_BACKLOG_2026-08-19.md). The
backlog did not reopen maintenance scope. The owner explicitly reopened a separate,
bounded Empire vertical slice on 2026-08-31; it does not change the promotion rules below.

### Follow-up Owner Rehearsal - 2026-08-20

- Baseline commit `6385a0f0200b4491cff67f4f4edbf7198210aee8` was clean, matched `origin/main`, and had a successful GitHub CI run before launch.
- A new 0.328.1 packet passed preflight at 1280x720 with full motion and allocated separate fresh rehearsal, tester, and evidence database paths.
- The visible window closed with reason `quit`; the rehearsal profile contained 0 archives, 0 complete target paths, and no recorded route.
- From clean baseline `50d5947f5009e1692a0e5e0cc19594ed6ec5dc9c` with successful CI run `32279625682`, a second fresh 0.328.1 packet passed preflight with new isolated profiles. Its visible window closed with reason `quit`, and post-close diagnostics confirmed schema 28 integrity with 0 save slots, 0 archives, 0 complete target paths, and no recorded route.
- The second attempt did not establish a reproducible product failure; it established only that the owner route was not started or saved in that isolated profile.
- Save & Archive failed. First Turn, Help, Pause/Back, Menu/Continue, both trade-offs, Guided/Full Endgame, Progress, and Route Atlas remain `NOT VERIFIED` because no direct owner observations were supplied.
- Human evidence remained 0/6 sessions and 0/6 represented campaigns. The rehearsal did not write a human-session row.
- Post-close verification passed Ruff across 155 files, 1,271 tests, content validation, schema 28 save integrity, all 18 campaign-readiness cells and 72 route exercises, all 702 responsive layout captures, all 21 animation-matrix cells, and the 0.328.1 package build and tracked-file safety scan.
- The 54-run decision ledger gate passed with the same 13 advisory watch cells. Those watches still require matching real-player observations before any balance work.
- No reproducible P0/P1 was reported or inferred from the incomplete run. The release remains Stable Alpha in maintenance mode.

### Operator-only Owner Rehearsal Attempts - 2026-08-23 through 2026-08-25

- Baseline commit `c1a7ce317810e2b831885dff3037a57cdbfa2253` was clean, matched `origin/main`, and retained successful GitHub CI run `32516291442` throughout the attempts.
- Three new 0.328.1 packets passed first-launch preflight at 1280x720 with full motion. Each allocated separate rehearsal, tester, and evidence database paths.
- Each visible window later closed with reason `quit`. Read-only post-close inspection found 0 companies, 0 save slots, and 0 archives in every rehearsal profile.
- These attempts establish only packet isolation and fail-closed archive behavior. They do not establish that New Game began, and they provide no direct observation for First Turn, Help, Pause/Back, Menu/Continue, campaign trade-offs, Guided/Full Endgame, Progress, or Route Atlas.
- Save & Archive remains incomplete, but the empty profiles do not establish a reproducible product defect. No P0/P1 was reported or inferred.
- Human evidence remained 0/6 sessions and 0/6 represented campaigns. None of the owner attempts wrote a human-session row.
- No local automated matrix was rerun for these operator-only attempts because runtime code did not change. The previously successful CI result remains the implementation baseline.
- Version 0.328.1 remains a Stable Alpha in maintenance mode.

### Partial Owner Rehearsal - 2026-08-28

- Baseline commit `6bd02f8a1877714a753730ff0c428cdefa5a28b3` was clean, matched `origin/main`, and had successful GitHub CI run `32873625652` before launch.
- A new 0.328.1 packet passed first-launch preflight at 1280x720 with full motion and allocated distinct rehearsal, tester, and evidence database paths.
- The first visible run created an `active` save for the exact `founder_journey` target at Turn 3 with `game_over=0`; no archive or complete target path existed when the window closed.
- The guarded runner correctly offered `Continue existing target save`. The retry window then closed without changing the save, which remained at Turn 3 with 0 archives.
- Database state proves that the target run began and is resumable, but it cannot prove whether First Turn, Help, Pause/Back, Menu/Continue, campaign trade-offs, or any other visible checklist item passed. Those rows remain `NOT VERIFIED` without a direct owner report.
- No reproducible P0/P1 was reported or inferred. Human evidence remained 0/6 sessions, and the owner rehearsal wrote no human-session row.
- The next owner action is to rerun the same guarded command, choose Continue, finish the route, use Save & Archive, confirm Progress/Route Atlas, and then close the window.
- Version 0.328.1 remains a Stable Alpha in maintenance mode.

### Owner Rehearsal Resume Guidance Fix - 2026-08-29

- A subsequent guarded retry opened the correct `founder_journey` Turn 3 save but closed without changing the save or creating an archive.
- The rendered briefing reproducibly showed `Continue existing save` and `Choose Continue` while checklist step 2 still said `Choose New Game`. Those simultaneous instructions were contradictory on the required owner path.
- The resume briefing now replaces the stale New Game checklist row with a saved-route continuation instruction. Fresh, empty-profile, and wrong-scenario launches retain their required New Game guidance.
- Regression coverage requires resume output to contain the continuation instruction and reject the stale New Game instruction while preserving New Game guidance for a non-target save.
- The fix changes operator copy only. Gameplay, balance, content, controls, persistence schema 28, saves, archives, and human evidence remain unchanged.
- Owner Rehearsal still requires a completed archive and direct owner observations; version 0.328.1 remains a Stable Alpha in maintenance mode.

## Promotion Rules

### Beta Candidate

All automated release gates pass, Owner Rehearsal reaches Save & Archive, the Progress/Route Atlas handoff is observed, no P0 is open, and every reproducible P1 found in rehearsal passes a focused retest.

### Beta Ready

Beta Candidate requirements pass, six valid human sessions cover all six featured campaigns, no P0 is open, and every P1 has valid retest evidence. Automated runs, generated packets, and owner-only rehearsal cannot substitute for these sessions.

## Change Policy

Standard Mode remains the compatibility baseline and accepts only reproducible defects, security or dependency compatibility, release infrastructure, and factual documentation. Empire Mode may receive targeted pacing and clarity work only when automated or human playtest evidence identifies a concrete problem. Unbounded systems, campaigns, currencies, workspaces, and animation expansion remain deferred.

See [Known Issues](KNOWN_ISSUES.md) and [Release Checklist](RELEASE_CHECKLIST.md).
