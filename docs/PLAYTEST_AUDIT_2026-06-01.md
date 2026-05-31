# 2D Playtest And Balance Audit

Date: `2026-06-01`
Version under audit: `0.96.0`

## Scope

- `doctor`
- `play-2d --headless --max-frames 4 --scenario founder_journey --seed 11`
- `menu-2d --headless --max-frames 4`
- `balance-audit --scenario founder_journey --scenario debt_crunch --scenario agency_pivot --scenario enterprise_compliance --scenario bootstrap_studio --runs 2 --turns 8 --seed-base 300`
- `balance-report --output /tmp/nexus-balance-2d-2026-06-01.md` with the same scenario set

## Release Diagnostics

- `doctor` passed before the version bump with no save database present and healthy catalog counts: `49 scenarios`, `49 templates`, `32 rivals`, and `202 events`.
- Both 2D headless smokes closed cleanly with reason `max_frames` and no autosave requirement.

## Friction Findings Addressed In 0.96.0

- The endgame board previously surfaced only one global gate command. It now exposes direct path-fix buttons for `IPO`, `M&A`, `Independence`, and `Reset`, so late-game repair can start from the cockpit itself.
- Late-game cockpit coverage is now explicit in regression tests instead of being checked only indirectly through deeper panel availability.
- Release verification now explicitly includes `doctor`, 2D headless smokes, and `balance-audit`, reducing the chance that frontend or tuning regressions slip through a version bump.

## Balance Snapshot

Scenario set:
- `founder_journey`
- `debt_crunch`
- `agency_pivot`
- `enterprise_compliance`
- `bootstrap_studio`

Summary:
- Matrix cells: `15`
- Audit findings: `2`
- Critical findings: `0`
- High findings: `0`
- Passing cells: `13 / 15`

Watch cells:
- `debt_crunch` on `founder`
  - Avg score: `153.5`
  - Avg cash: `-177.01`
  - Shutdowns: `1`
- `founder_journey` on `founder`
  - Avg score: `160.5`
  - Avg cash: `-66.105`
  - Shutdowns: `1`

Interpretation:
- `builder` and `standard` stayed inside the expected envelope for this audit set.
- `founder` still carries two low-severity cash-floor watches, but neither escalated to high or critical severity in this sample.
- `agency_pivot`, `bootstrap_studio`, and `enterprise_compliance` passed across the audited difficulties in this run.

## Recommended Next Tuning Pass

- Re-test `debt_crunch` on `founder` with a larger sample before changing constants.
- Re-test `founder_journey` on `founder` after the next finance or late-game tuning pass.
- Keep `builder` and `standard` stable unless future audits surface new `watch` cells.

## Release Readiness

Current assessment:
- `2D frontend`: ready for broader internal playtesting
- `late-game cockpit`: materially stronger than `0.95.0`
- `balance state`: acceptable for continued alpha iteration, with `founder` pressure still under active observation
