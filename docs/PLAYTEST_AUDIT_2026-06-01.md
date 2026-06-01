# 2D Playtest And Balance Audit

Date: `2026-06-01`
Version under audit: `0.97.0`

## Scope

- `doctor`
- `play-2d --headless --max-frames 4 --scenario founder_journey --seed 11`
- `menu-2d --headless --max-frames 4`
- `simulate-balance --scenario founder_journey --difficulty founder --runs 8 --turns 10 --seed-base 700`
- `simulate-balance --scenario debt_crunch --difficulty founder --runs 8 --turns 10 --seed-base 700`
- `balance-audit --scenario founder_journey --scenario debt_crunch --runs 6 --turns 10 --seed-base 700`
- `balance-audit --scenario founder_journey --scenario debt_crunch --scenario agency_pivot --scenario enterprise_compliance --scenario bootstrap_studio --runs 2 --turns 8 --seed-base 300`
- `balance-report --output /tmp/nexus-balance-2d-2026-06-01.md` with the same scenario set

## Release Diagnostics

- `doctor` passed on `0.97.0` with no save database present and healthy catalog counts: `49 scenarios`, `49 templates`, `32 rivals`, and `202 events`.
- Both 2D headless smokes closed cleanly with reason `max_frames` and no autosave requirement.

## Friction Findings Addressed In 0.97.0

- The endgame board previously surfaced only one global gate command. It now exposes direct path-fix buttons for `IPO`, `M&A`, `Independence`, and `Reset`, so late-game repair can start from the cockpit itself.
- Late-game cockpit coverage is now explicit in regression tests instead of being checked only indirectly through deeper panel availability.
- Release verification now explicitly includes `doctor`, 2D headless smokes, and `balance-audit`, reducing the chance that frontend or tuning regressions slip through a version bump.
- Founder-pressure balance sweeps no longer waste turns on invalid angel-round attempts once the cap is exhausted.
- Profit-machine openings now keep viable `standard` pricing instead of mechanically collapsing to `budget`, improving cash realism in tuning runs.
- Cash stress now shifts autoplay into `cash_guard`, `conserve`, and support-focus actions earlier, which closes the previous founder cash-floor watches without changing the core economy constants.

## Balance Snapshot

Scenario set:
- `founder_journey`
- `debt_crunch`
- `agency_pivot`
- `enterprise_compliance`
- `bootstrap_studio`

Summary:
- Matrix cells: `15`
- Audit findings: `0`
- Critical findings: `0`
- High findings: `0`
- Passing cells: `15 / 15`

Interpretation:
- All audited cells in the five-scenario matrix passed after the founder retune.
- `builder` and `standard` remained stable while the founder-focused opening fixes landed.
- `agency_pivot`, `bootstrap_studio`, and `enterprise_compliance` stayed inside the expected envelope while the founder-opening policy changed.

## Founder Stress Snapshot

Long founder batch results:
- `founder_journey` on `founder`, `8 runs / 10 turns`: `0 shutdowns`, average score `178.4`
- `debt_crunch` on `founder`, `8 runs / 10 turns`: `0 shutdowns`, average score `146.4`

Interpretation:
- The previous founder cash-floor watches are closed in the longer retest sample instead of merely downgraded.
- The fix came from tighter autoplay finance/execution policy, not from softening the global founder economy constants.

## Recommended Next Tuning Pass

- Keep rerunning the founder long batch after changes to finance, support, or autoplayer sequencing.
- Keep `builder` and `standard` stable unless future audits surface new `watch` cells.
- Use manual 2D playtests to validate that the stronger cash-survival policy still feels like sensible play, not only good batch math.

## Release Readiness

Current assessment:
- `2D frontend`: ready for broader internal playtesting
- `late-game cockpit`: materially stronger than `0.95.0`
- `balance state`: acceptable for continued alpha iteration, with the prior founder watch cells cleared in the current audit set
