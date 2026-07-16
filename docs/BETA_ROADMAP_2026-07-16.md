# Beta Roadmap - 2026-07-16

## Product Position

NEXUS TECH 0.300.0 remains a late-alpha beta candidate at approximately 83% of a defensible beta. The vertical slice, six featured campaigns, 24 authored campaign routes, three difficulties, persistence, archive progression, endgame, responsive 2D shell, and automated release gates exist. The release blocker is observed usability, not missing content.

## Current Engineering Slice

The current convergence slice removes a concrete duplicate route from the six-slot Focus View after the deterministic 820x620 owner audit while retaining the executable next-session packet:

- `Choose This Turn` now presents one green `Recommended` route, two distinct alternatives, Report, Save, and End Turn;
- the primary command and its workspace are excluded from alternatives while preference, Coach, and stable fallback order remain deterministic;
- Coach execution, direct keyboard commands, AP costs, simulation state, balance, persistence, and schema 27 are unchanged;
- Endgame actor cards now use one measured header lane that reserves title and summary width at compact viewports;
- the redundant Endgame entity strip is suppressed while actor cards are active, and Quick Start identifies its actor as `Guide`;
- compact layout regressions protect actor-to-copy separation at 820x620;
- the 25-button run action catalog and four local loadout policies now live in a pure module instead of the pygame scene renderer;
- a direct catalog contract protects key order, unique titles, valid command payloads, and complete loadout routing;
- completed-run title, cause, progression, and metric policy now live in a pure module instead of the pygame scene renderer;
- shutdown, victory, and archived-ending branches have direct regression coverage while Cash, Score, and Last Turn remain visible;
- compact Help content now lives in a pure module and retains complete labels without ellipsis at the large text scale;
- `scenes.py` remains responsible for availability, contextual selection, layout, input routing, and rendering rather than owning those catalog decisions;
- `prepare-beta-playtest-session` selects the next uncovered campaign or unresolved human gate;
- the packet includes one visible launch command, an eight-step observation checklist, a deliberately invalid recorder template, and evidence-refresh commands;
- stored observation notes never enter the packet, generated artifacts default to `/tmp`, and preparation never writes a session row;
- no save migration, new catalog entry, control binding, or balance adjustment is introduced.

## Path To Beta

1. Run `prepare-beta-playtest-session`, then complete one owner rehearsal from New Game through `Save & Archive` at 820x620 and record only defects actually observed; do not count the owner rehearsal as first-time human evidence.
2. Observe six first-time sessions across all six featured campaigns using anonymous tester codes and the structured local evidence command.
3. Require at least 80% unaided turn-one completion, 100% Pause/Back/Menu recovery, at least 80% trade-off recall, at least 80% Act 3 reach, and zero blocker sessions.
4. Use Decision Pattern only to identify candidate repetition or low action diversity; do not remove or retune a command without matching player notes.
5. Fix P0/P1 navigation, readability, wording, or pacing defects before any feature expansion.
6. Re-run gameplay, balance, campaign, save, visual, layout, motion, animation, package, and security gates after every observed blocker fix.
7. Promote to beta only after the human gates pass and a reviewer makes the release decision.

## Post-Beta Order

The preferred expansion order is audio feedback, key remapping/controller support, localization, richer visual assets, then new campaign content. Each addition must ship as one bounded vertical slice with save compatibility and the existing responsive/accessibility matrices. None of these features should enter the beta-candidate branch before the six-session evidence gate closes.

## Evidence Boundary

Automation may verify deterministic behavior, containment, navigation routes, report consistency, and packet safety. It cannot claim that a first-time player understood a choice, enjoyed the pacing, or completed a visible session. Human evidence remains `0/6` until real observed sessions are recorded with explicit attestation; generating a preparation packet does not change that count.
