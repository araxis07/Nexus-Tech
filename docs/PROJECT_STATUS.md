# NEXUS TECH Project Status

## Current Classification

- Version: 0.328.0
- Status: Stable Alpha
- Operating mode: maintenance
- Persistence schema: 28
- Scope: frozen; no new features, systems, campaigns, or animation work

Version 0.328.0 contains a complete local vertical slice. Players can start a guided or full run, make turn-based operating decisions, pause and recover navigation, save and continue, reach guided or full endgame, archive a completed run, and inspect campaign progress and the Route Atlas. The terminal and 2D interfaces use the same simulation and SQLite persistence model.

Stable Alpha is the highest defensible classification today. Automated checks establish implementation health, but they do not establish that a person completed and understood the full owner journey.

## Implemented And Automated

- Six featured campaigns, 24 authored routes, three difficulties, and three campaign phases
- Turn simulation, trade-offs, events, teams, products, finance, endgame, review, and archive progression
- Local SQLite saves, schema migration, integrity checks, save slots, continuation, and archive records
- Pause, Back, Menu, Continue, Help, Guided/Full Endgame, Save & Archive, Progress, and Route Atlas flows
- Responsive 2D layout coverage across 39 surfaces, supported viewports, text scales, contrast profiles, and motion modes
- Deterministic gameplay, content, persistence, layout, visual, animation, package-build, and CI gates

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

## Manual Evidence Still Required

- Owner Rehearsal: incomplete
- Valid human playtest sessions: 0/6
- Featured campaigns represented by valid human sessions: 0/6
- Owner archive and Route Atlas handoff: not yet observed
- Human confirmation of readability, pacing, decision comprehension, and motion comfort: not yet established

Owner Rehearsal is an operator preflight only. It must never be inserted into the human evidence database or counted toward the six sessions.

## Promotion Rules

### Beta Candidate

All automated release gates pass, Owner Rehearsal reaches Save & Archive, the Progress/Route Atlas handoff is observed, no P0 is open, and every reproducible P1 found in rehearsal passes a focused retest.

### Beta Ready

Beta Candidate requirements pass, six valid human sessions cover all six featured campaigns, no P0 is open, and every P1 has valid retest evidence. Automated runs, generated packets, and owner-only rehearsal cannot substitute for these sessions.

## Maintenance Policy

Accepted work is limited to reproducible P0/P1 defects, security or dependency compatibility, release and test infrastructure, and factual documentation. P2 polish, redesigns, balance changes based only on autoplay, new content, and feature expansion remain deferred unless the project is explicitly reopened.

See [Known Issues](KNOWN_ISSUES.md) and [Release Checklist](RELEASE_CHECKLIST.md).
