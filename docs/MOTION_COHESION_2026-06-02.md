# 2D Motion Cohesion Notes - 2026-06-02

This pass extended the animated frontend beyond the run scene so the 2D shell reads as one system instead of a stack of unrelated screens.

## Scope

- Expanded action choreography coverage for capital, board, customer/support, partner/channel, pipeline, roadmap, and hiring command families.
- Added motion emphasis to `TitleScene` and `ReviewScene`, including mode transitions, feed emphasis, and overlay transitions for text input and delete confirmation.
- Tightened run-scene pre-action choreography so finance, board, report, customer, and pipeline commands pulse the most relevant stats and late-game panels before the state update lands.

## Outcome

- Core 2D actions now feel less front-loaded around product work only; finance, recovery, and governance moves now surface motion in the same language.
- Title, archive, wizard, and review flows no longer drop back to static panels when the player leaves the live run.
- Regression coverage now checks finance-family choreography, board-command motion routing, title-scene overlay motion, and review-scene motion initialization.

## Remaining gaps

- Advanced archive comparison screens still use lighter motion than the live run.
- Some late-game repair commands can still use more specific per-command choreography instead of family-level cues.
- Manual playtests are still needed to trim noise and confirm that the expanded motion pass stays readable over long sessions.
