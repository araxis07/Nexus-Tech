# 2D Visual UX Audit

Date: `2026-06-03`
Version under audit: `0.114.0`

## Scope

- `pytest -q tests/test_frontend_2d.py`
- direct `RunScene` inspection of footer state, cockpit tooltip wording, inspector focus summaries, and header/detail density
- `nexus_tech.cli play-2d --headless --max-frames 4 --scenario founder_journey --seed 11`
- `nexus_tech.cli menu-2d --headless --max-frames 4`
- captured scene frames from `/tmp/nexus-tech-visual-audit`, `/tmp/nexus-tech-visual-audit-2`, `/tmp/nexus-tech-visual-audit-3`, and follow-up narrow-window verification renders

## Friction Findings

1. The live run header rendered score metadata as a raw `RunScore(...)` string, which overflowed the second line and competed with product/coach context.
2. Dense late-game scenes stacked footer watch text, status text, and hint text on top of the bottom control row, creating visible overlap in captured frames.
3. Endgame and deep-panel action buttons carried detail copy that was too long for narrow button widths, especially in smaller overlays.
4. Strict inspector filters could produce an empty detail pane with no clear next step beyond trial-and-error key presses.
5. Follow-up narrow-window renders still showed stacked meta-board copy in the title flow, overly dense endgame inspector rows, and turn-summary command copy that was too long for a shallow action slot.
6. Even after the compact-layout pass, feed-heavy scenes and staged summaries could still feel visually busy on smaller windows because card counts and reveal cadence did not adapt strongly enough to available height.
7. Captured `820x620` and `960x640` endgame inspectors still let the selected-record focus note collide with pager and item-action rows, especially when a hotspot row carried a long primary-action summary.
8. Captured narrow turn summaries could still starve the timeline lane entirely, while short summary/footer buttons and compact metric cards were letting secondary detail copy spill into adjacent content bands.

## Fix Summary

- The live run header now renders score as compact `value (tier)` metadata and keeps the product/coach note short enough to stay within one wrapped line.
- The action-bar footer now renders exactly one status line plus one watch-or-hover hint line inside a dedicated footer band, removing the extra stacked watch row that was colliding with controls.
- Endgame and deep-panel button details now use a tighter compacting pass so command context stays readable without overrunning button bounds.
- Empty inspector results now show an explicit recovery hint telling the player to cycle filters or refocus with `A` / `H`.
- The title/meta board now collapses into a compact stacked layout on narrow windows instead of pushing archive/progression controls into the sidebar region.
- Small-window inspectors now tighten per-page density with adaptive paging, shorter action-detail copy, and stricter line limits for narrow cards.
- The turn-summary focus command now truncates to the command label instead of pushing a long detail sentence through a shallow button slot.
- Title and live-run feeds now cap visible cards by available height, with overlay-heavy run states dropping to a tighter queue instead of showing the full default stack.
- Turn-summary timeline events now reveal more slowly on narrower windows and cap the visible card count by panel height so post-turn animation reads as a sequence instead of a pileup.
- Small-window inspector footers now reserve more breathing room below the active cards before drawing page controls and row actions.
- Late-game gate commands now emit path-specific choreography cards and targets, so `board recovery`, `channel firebreak`, `cash waterfall`, `covenant firewall`, `renewal watch`, and `reset buffer` reads feel distinct instead of collapsing into generic family motion.
- Turn-resolution events now prioritize exit gates, gate commands, and strategic outlook ahead of lower-signal deltas, which keeps late-game summaries readable when narrow panels can only show one to three timeline cards.
- The compact endgame footer now shortens gate and hotspot command labels on sub-1000px layouts so the cockpit line keeps the next repair route visible without flooding the footer band with raw command ids.
- Low-severity live-run events now shorten their TTL under dense queues, overlay-heavy states, and narrow windows so the feed clears itself faster instead of layering long-lived informational cards over active repair loops.
- Very narrow or overlay-heavy run states can now collapse the visible event queue down to a single card, reducing motion clutter when the screen is already carrying a deep panel, inspector, or pending-event overlay.
- Turn-summary reveal cadence now slows further when the summary carries a heavier event list, and `Next Focus` handoffs escalate into warning/flash cues when the return lane is a repair-heavy finance, board, customer, or partnership workspace.
- When the retained live queue must shrink, backlog trimming now keeps higher-priority late-game cards such as `Gate Command`, `Endgame Cockpit`, and `Next Focus` ahead of low-signal info cards instead of dropping them by recency alone.
- Hover tooltips now clamp against all window edges, shrink on narrow layouts, and flip above the cursor when the default placement would push the hint below the visible surface.
- Short action buttons now suppress detail copy automatically and vertically center their primary label, which removes the most obvious text-bleed in compact inspector rows, summary footer controls, and other 38-40px button strips.
- Compact endgame inspectors now drop the extra focus-note line before it can collide with pager/action rows, relying on the selected-row highlight plus `READY` / `BLOCKED` chips as the primary cue on tight layouts.
- Narrow turn summaries now reserve a dedicated timeline lane by shrinking the upper metrics band more aggressively, using a responsive strategy-panel height, compacting metric-card copy earlier, and blanking footer button details before they start clipping.

## Verification Snapshot

- `tests/test_frontend_2d.py`: passed with new coverage for title/live feed pacing, queue-tightened TTL behavior, compact cockpit footer copy, late-game command choreography, and summary reveal / handoff behavior
- `tests/test_frontend_2d.py`: passed with added coverage for compact inspector focus summaries and narrow summary layout helpers
- `play-2d --headless --max-frames 4`: passed
- `menu-2d --headless --max-frames 4`: passed
- captured follow-up frames from `/tmp/nexus-tech-visual-pass-2` and `/tmp/nexus-tech-visual-pass-3` confirmed that the narrow summary timeline is back on-screen and compact inspector controls no longer leak overlapping detail copy
- follow-up motion-pressure tuning now also dampens low-signal feed and summary cues when the pulse bank is already dense, reducing the risk that long sessions drift back toward noisy overlay/feed stacking

## Remaining Risk

- This is still a deterministic visual audit over captured frames, not a freeform human session over a long late-game run.
- Motion density, pacing, and card hierarchy still need to be judged in a real open-window session before calling the 2D frontend beta-ready.
