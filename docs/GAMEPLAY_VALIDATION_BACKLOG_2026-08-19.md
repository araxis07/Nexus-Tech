# Gameplay Validation Backlog - 2026-08-19

## Purpose

This backlog records the next defensible gameplay work without reopening the
Stable Alpha by accident. It is a planning artifact only. Version 0.328.1
remains in maintenance mode, and none of the items below authorize a gameplay,
balance, content, persistence, control, or animation change before its entry
criteria pass.

## Current Baseline

- Product status: Stable Alpha, maintenance mode
- Featured campaigns: 6
- Authored campaign routes: 24
- Owner Rehearsal: incomplete; no completed `founder_journey` archive
- Human beta evidence: 0/6 current-version sessions
- Decision-quality audit: automated ledger gate passed across 54 heuristic runs
- Advisory result: 13/18 scenario/difficulty cells repeated `Grow Demand`
- Autoplay-policy attribution: 3/13 watches are 100% default-fallback
  `portfolio_machine` cells; 10/13 remain possible gameplay candidates
- Highest observed autoplay repetition: `public_market_countdown`, 60-65%

The advisory result measures the deterministic autoplay policy, not player
behavior. It is a candidate for observation, not a balance defect.

## Change-Control Rules

1. Finish the Owner Rehearsal through Save & Archive and Progress/Route Atlas.
2. Do not tune an action unless matching real-player notes identify the same
   decision as mandatory, unclear, or low-value.
3. Change one gameplay hypothesis per batch so a regression has one plausible
   cause.
4. Prefer clearer costs, constraints, rewards, and consequences for existing
   actions over new commands or systems.
5. Preserve schema 28 and save compatibility unless a separately approved
   migration is unavoidable.
6. Never count autoplay, generated packets, or owner rehearsal as human-session
   evidence.

## Prioritized Stories

### GV-001 - Complete The Owner Route

**Priority:** Gate

**Size:** Operational, no production-code estimate

**Status:** Ready for manual execution

As the release owner, I need to complete the visible `founder_journey` route so
that later gameplay decisions are based on an observed end-to-end experience.

Acceptance criteria:

- Given a validated isolated rehearsal profile, when the owner starts a new
  `founder_journey`, then no tester save or evidence database is modified.
- Given an active run, when Help, Pause, Back, Menu, and Continue are exercised,
  then the run remains recoverable without data loss.
- Given both campaign choices and Endgame are complete, when Save & Archive is
  selected, then the exact route appears in Progress and Route Atlas.
- Given the window closes, when the archive gate runs, then it reports one
  complete target path and does not record a human session.

### GV-002 - Confirm Decision Variety Before Tuning

**Priority:** High after GV-001

**Size:** 3 points for discovery; implementation estimated separately

**Status:** Blocked by human evidence

The audit-only attribution prerequisite is complete. Every autoplay action now
has an explicit in-memory policy reason, and the report separates
fallback-dominated policy watches from possible gameplay candidates without
changing game state, saves, balance, content, or human evidence. This does not
complete GV-002: only observed player notes can open a tuning story.

As a strategy player, I want operating choices to represent distinct trade-offs
so that one repeated action does not feel mandatory across unrelated campaigns.

Acceptance criteria:

- Given a real observed session, when a tester explains repeated operating
  choices, then the note records whether repetition was intentional, mandatory,
  or caused by unclear alternatives.
- Given the current advisory baseline, when human notes are reviewed, then no
  tuning story opens unless the notes independently match the `Grow Demand`
  candidate.
- Given no matching human observation, when the review closes, then balance and
  command availability remain unchanged.

### GV-003 - Tune A Confirmed Repetition Candidate

**Priority:** Conditional

**Size:** 5 points

**Status:** Blocked by GV-002

As a returning player, I want scenario-native alternatives to remain viable so
that campaign identity comes from meaningful choices rather than extra buttons.

Initial review order is `public_market_countdown`, `portfolio_machine`, then
`technical_rebuild`. This order is advisory until human evidence confirms it.

Acceptance criteria:

- Given matching human and decision-audit evidence, when tuning begins, then the
  batch changes only one documented cost, constraint, reward, or consequence
  hypothesis.
- Given the tuned scenario, when deterministic gameplay and balance matrices
  run, then supported routes remain completable on all three difficulties.
- Given the full regression suite, when the batch is validated, then content,
  save, layout, animation, and package gates still pass.
- Given a new first-time tester, when the affected choice is retested, then the
  original observation is resolved without operator coaching.

### GV-004 - Validate Debt Crunch Late-Game Pacing

**Priority:** Conditional

**Size:** 5 points

**Status:** Blocked by specialist human review

As a debt-recovery player, I want turns 11-20 to preserve a viable but pressured
recovery path so that late-game difficulty does not become either trivial or
unrecoverable.

Acceptance criteria:

- Given a specialist playtest, when the run passes turn 10, then the tester can
  identify the debt, cash, and operating trade-off without source knowledge.
- Given a reported blocker, when it is reproduced, then the exact scenario,
  difficulty, seed, turn, and action sequence are captured before tuning.
- Given no reproducible blocker, when the review closes, then no late-game
  constants change.
- Given an approved fix, when the debt-specific and representative Founder gates
  run, then the fix does not flatten the supported Founder difficulty envelope.

## Post-Beta Capability Order

These are deferred product slices, not current maintenance tasks:

1. Audio feedback for decisions, warnings, and outcomes
2. Key remapping and controller support
3. Localization infrastructure and the first translated language
4. Richer production visual assets
5. New campaign content

Each slice requires its own accessibility, save-compatibility, package, and
manual acceptance plan. Cloud sync, multiplayer, and account systems remain
outside this backlog.

## Test Batching Policy

### Batch A - Planning And Read-Only Audits

Documentation, backlog refinement, and read-only audit exports may be grouped.
They do not change gameplay and require documentation checks, repository safety
checks, and the normal CI gate before merge.

### Batch B - One Gameplay Hypothesis

One related gameplay hypothesis may include implementation and focused
regressions. Run focused tests during development, then run the full automated
release matrix once at the end of that batch. Do not combine balance, controls,
UI redesign, content expansion, and persistence changes in one batch.

### Batch C - Manual Evidence

Run one complete Owner Rehearsal after the candidate build is stable. The six
human beta sessions remain six distinct observed sessions and cannot be replaced
by one long owner test.

## Definition Of Done For A Gameplay Batch

- Entry evidence is cited and the hypothesis is singular.
- Acceptance criteria and focused regressions pass.
- Full tests, Ruff, content, save, layout, animation, and package gates pass.
- No database, environment file, credential, token, key, or generated capture is
  tracked.
- Human retest is recorded only when a real tester completed it.
- Documentation, changelog, commit, remote branch, and GitHub CI agree.
