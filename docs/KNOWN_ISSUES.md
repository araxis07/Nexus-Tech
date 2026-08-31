# NEXUS TECH Known Issues

## Release Blockers

- Owner Rehearsal has not yet completed the path from a fresh `founder_journey` start through Save & Archive and Progress/Route Atlas.
- Structured human evidence remains 0/6 sessions and 0/6 represented featured campaigns. Version 0.329.0 must not be described as Beta Ready.
- `Founder Empire` has automated regression coverage but has not been completed by a human through its Turn 25 victory gate; its pacing and balance remain preview quality.
- Readability, pacing, decision comprehension, recovery controls, and motion comfort have automated coverage but still require direct human observation.

The 2026-08-23 through 2026-08-25 operator attempts used validated isolated profiles but closed with 0 companies, 0 saves, and 0 archives. They confirm neither a gameplay pass nor a defect; all unobserved owner checks remain `NOT VERIFIED`.

The 2026-08-28 rehearsal progressed further and left a valid `founder_journey` save at Turn 3, but it still produced no archive. The resumable save is operational progress, not manual evidence or proof that the visible owner checklist passed.

The 2026-09-01 Empire validation attempt used an isolated `empire_founder_journey` profile and produced no archive. Its first close left an active Turn 3 save; its second close left the same slot active at Turn 1. Without a direct report of whether New Game or Continue was selected, this difference is an unresolved observation rather than a reproducible defect. Empire Victory, Save & Archive, Progress, Route Atlas, pacing, and visible controls remain unverified.

These are evidence gaps, not proof of a software defect. If rehearsal exposes a reproducible P0 or P1, record the exact route and fix only that defect with regression coverage.

## Known Constraints

- Keyboard bindings are fixed. Arbitrary remapping and controller support are not included.
- The supported 2D viewport begins at 820x620. Larger Retina and ultrawide windows intentionally center a 1440x900 maximum design canvas instead of stretching every panel.
- Saves are local SQLite files. Cloud sync, multiplayer, and cross-device account recovery are not included.
- The game is English-only and terminal/shape-art first; recorded voice, a full audio layer, and production illustration assets are outside the closed scope.
- Automated decision-quality audits retain 13 advisory watch cells led by `Grow Demand`. Reason attribution classifies all three `portfolio_machine` cells as 100% default-fallback autoplay-policy watches and leaves ten cells as possible gameplay candidates, with `public_market_countdown` showing the highest raw repetition. Neither classification authorizes rebalancing without matching human observations; see the [Gameplay Validation Backlog](GAMEPLAY_VALIDATION_BACKLOG_2026-08-19.md).
- Specialist human confirmation for the later `debt_crunch` campaign remains outstanding even though deterministic regression coverage protects its supported recovery envelope.
- Empire Mode derives its strategy state from existing save fields. This preserves schema compatibility, but there is no separate historical Empire ledger beyond normal turn, decision, event, competitor-intel, and archive records.

## Severity Policy

- P0: crash, save corruption or loss, blocked core loop, security exposure, or an impossible required archive path
- P1: reproducible failure of navigation, controls, endgame, archive, progression, or supported-layout readability that prevents normal completion
- P2: cosmetic asymmetry, optional polish, preference requests, or advisory balance observations that do not block completion

Standard Mode accepts P0/P1 fixes. Empire pacing or clarity changes require reproducible evidence; broad redesign remains deferred.
