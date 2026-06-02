# 2D Visual UX Audit

Date: `2026-06-03`
Version under audit: `0.106.0`

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

## Fix Summary

- The live run header now renders score as compact `value (tier)` metadata and keeps the product/coach note short enough to stay within one wrapped line.
- The action-bar footer now renders exactly one status line plus one watch-or-hover hint line inside a dedicated footer band, removing the extra stacked watch row that was colliding with controls.
- Endgame and deep-panel button details now use a tighter compacting pass so command context stays readable without overrunning button bounds.
- Empty inspector results now show an explicit recovery hint telling the player to cycle filters or refocus with `A` / `H`.
- The title/meta board now collapses into a compact stacked layout on narrow windows instead of pushing archive/progression controls into the sidebar region.
- Small-window inspectors now tighten per-page density with adaptive paging, shorter action-detail copy, and stricter line limits for narrow cards.
- The turn-summary focus command now truncates to the command label instead of pushing a long detail sentence through a shallow button slot.

## Verification Snapshot

- `tests/test_frontend_2d.py`: passed with new coverage for compact score labels, overlay-detail compaction, footer-band metrics, adaptive inspector paging, compact meta-board summaries, and summary-command copy
- `play-2d --headless --max-frames 4`: passed
- `menu-2d --headless --max-frames 4`: passed

## Remaining Risk

- This is still a deterministic visual audit over captured frames, not a freeform human session over a long late-game run.
- Motion density, pacing, and card hierarchy still need to be judged in a real open-window session before calling the 2D frontend beta-ready.
