# Beta Execution Audit - 2026-07-30

## Scope

This audit covers NEXUS TECH 0.323.0. It validates the guarded visible
owner-rehearsal runner without changing gameplay outcomes, balance, controls,
frozen content catalogs, persistence schema 28, packet manifest schema 3,
archive progression, or the human-evidence boundary.

## Decision

- Automated readiness: `pass`
- Product position: late-alpha beta candidate, approximately `83%`
- Human readiness: `manual-required`
- Human beta evidence: `0/6 current-version sessions`
- Archive route evidence: `0/24 authored routes`
- Release decision: `do not tag yet`
- Expansion decision: keep the feature freeze until the human gate closes

## Current Slice

`run-beta-owner-rehearsal` now owns the safe operator sequence for the first
human-beta packet:

1. Revalidate the packet path, content, build, and evidence snapshot.
2. Require the isolated tester profile to remain unused.
3. Open the exact packet-bound 2D rehearsal profile, viewport, and motion mode.
4. Run the archive-backed target-route gate when the visible window closes.
5. Fail closed with the same retry command when no complete archive exists.

The command can resume its existing incomplete owner-only profile, preventing an
early close from forcing operators to reconstruct the launch manually. A
complete target archive skips an unnecessary relaunch. The separate visible
launch and `validate-beta-owner-rehearsal` commands remain in the packet for
diagnostics.

The runner never opens the tester profile, records a human-session row, or
claims that Pause, Back, Menu, Continue, Endgame switching, Progress, or Route
Atlas were observed. Those checks remain the owner's visible responsibility.

## Automated Evidence

| Area | Result | Evidence |
| --- | --- | --- |
| Full test suite | pass | 1,241 tests |
| Focused rehearsal and packet contracts | pass | 88 tests |
| Formatting and lint | pass | 152 files formatted; Ruff reported no issues |
| Content catalog | pass | 49 scenarios, 49 templates, 32 rivals, 202 events, 0 issues |
| Guarded fresh close | pass | Incomplete visible close returned non-zero and printed the exact resume action |
| Guarded completed close | pass | Complete target archive passed without touching tester or human evidence |
| Guarded retry and resume | pass | Existing empty profile reopened New Game; existing save reopened Continue and accepted a later complete archive |
| Already-complete route | pass | Archive gate passed without reopening the visible window |
| Packet smoke | pass | Generated 0.323.0 packet contained guarded and manual workflows and passed preflight |
| Package smoke | pass | Wheel contained 143 expected files; isolated install reported 0.323.0 and validated a generated packet |
| Repository hygiene | pass | No tracked risky filename or recognized high-confidence credential pattern |

## Required Human Work

1. Run the generated packet's `run-beta-owner-rehearsal` command.
2. Complete Learn / `founder_journey`, use Save & Archive, open Progress, and
   confirm the archived route in Route Atlas.
3. Require the automatic post-window archive gate to pass.
4. Observe six first-time sessions across the six featured campaigns with fresh
   tester profiles and anonymous tester codes.
5. Fix only P0/P1 defects observed in those sessions, then retest with a new
   first-time player.
6. Run `beta-playtest-status --require-review-ready` and promote to beta only
   after the gate passes and a reviewer approves release.

Audio, arbitrary key remapping or controller support, localization, richer
visual assets, and new campaign content remain post-beta work.
