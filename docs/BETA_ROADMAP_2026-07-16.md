# Beta Roadmap - 2026-07-16

## Product Position

NEXUS TECH 0.314.0 remains a late-alpha beta candidate at approximately 83% of a defensible beta. The vertical slice, six featured campaigns, 24 authored campaign routes, three difficulties, persistence, archive progression, endgame, responsive 2D shell, and automated release gates exist. The release blocker is observed usability, not missing content.

## Current Engineering Slice

The current convergence slice reduces 2D scene coupling and protects the complete owner-flow contract while retaining the executable next-session packet:

- generated human-beta, onboarding visible-window, and animation manual-QA artifacts now reuse the executable that created them instead of assuming `uv` exists in the operator shell;
- project-local absolute executables collapse to shell-safe relative launchers, while `--command-prefix` remains available for a deliberate cross-environment handoff;
- Pause now distinguishes title-shell recovery from direct play, keeps unavailable Menu actions non-interactive, and prevents direct-play `M` from closing an unsaved run;
- one pure pause-presentation policy owns status, guidance, action order, tone, and availability without saving, quitting, or mutating a run;
- action and impact feedback now translate product targets into stable names and metrics instead of exposing random internal identifiers;
- Title Menu and Quick Start now emphasize New Game when no save exists, render Continue as explicitly unavailable, and restore Continue as the primary route for returning players;
- compact title headers now reserve separate subtitle and archive-progress lanes so local progression never crosses the lower panel frame;
- one pure scene-chrome policy keeps Title, Run, Turn Summary, and Review action ownership mutually exclusive across content, footer, navigation, and blocking overlays while preserving the live-run recovery rail;
- one pure title-presentation policy owns first-run action availability, tone, copy, and footer guidance without loading or mutating a run;
- compact Focus View now uses two balanced rows of three actions instead of placing End Turn alone beneath five peer controls, while wider layouts retain one six-action row;
- Recommended remains visibly primary with motion disabled, and Guided Opening teaches `NEXT` then `LATER` without duplicating shortcuts already visible in navigation and actions;
- one pure focus-presentation policy owns responsive grid, opening copy, and primary-emphasis decisions without changing command availability or gameplay;
- that policy now also owns first-turn visibility, checkpoint progress, semantic tones, and width-aware short copy, while pygame retains measurement, drawing, and input routing;
- the 320px first-turn card contract renders every instruction without fitted, hidden, or ellipsized text;
- guided Endgame fix and risk cards now use complete compact instructions instead of artificial 32-character ellipses;
- responsive Review finding cards preserve complete cause and lesson copy at 820x620, including the large-text profile, while moving additional findings behind an explicit larger-layout notice;
- one pure review-presentation policy owns the card count and height budget without changing postmortem data;
- completed reviews reached from the title shell preserve Back/Menu and add a direct `6 Open Progress` route after archiving;
- one pure review-navigation policy owns post-run action order and availability across the footer and navigation rail;
- optional Progress routing crosses title, run, summary, and review scenes without changing direct-launch behavior or persistence;
- campaign identity contracts protect unique chapter language, mechanically distinct decision options, and broad state-dimension coverage;
- transient scene records now live in `frontend_2d.scene_state` without changing scene construction or audit imports;
- `frontend_2d.workspace_routing` is the single command-owner policy for navigation, feedback, and choreography;
- a temporary-database contract persists one completed featured campaign, verifies its archive fields, and closes First Archive Mission 6/6 without writing to the player's database;
- automated owner-flow coverage does not count as visible-window rehearsal or human beta evidence;
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
- while current-version evidence is `0/6`, that packet opens with a separate owner-only rehearsal gate covering recovery, campaign, Endgame, archive, and Progress routes without placing the human recorder inside the rehearsal gate;
- owner rehearsal, tester gameplay, and structured evidence now use three distinct database paths so prior saves, Continue state, and archives cannot contaminate a first-time observation;
- preparation allocates unique temporary gameplay profiles by default, rejects explicit profiles that already exist, and leaves the persistent evidence store only in recorder/status commands;
- the first packet includes isolated rehearsal and tester launches; later packets retain one fresh tester launch, the eight-step observation checklist, a deliberately invalid recorder template, and evidence-refresh commands;
- stored observation notes never enter the packet, generated artifacts default to `/tmp`, and preparation never writes a session row;
- `decision-quality-audit` compares operating-choice variety across the six campaigns and three difficulties, failing only missing ledger coverage while exporting repetition and low-variety candidates for human review;
- no save migration, new catalog entry, control binding, or balance adjustment is introduced.

## Path To Beta

1. Run `prepare-beta-playtest-session`, keep its isolated rehearsal/tester/evidence database paths unchanged, follow the Owner Rehearsal Gate from New Game through `Save & Archive` and `6 Open Progress` at 820x620, and record only defects actually observed; never run the human-session recorder for the rehearsal.
2. Observe six first-time sessions across all six featured campaigns using anonymous tester codes and the structured local evidence command.
3. Require at least 80% unaided turn-one completion, 100% Pause/Back/Menu recovery, at least 80% trade-off recall, at least 80% Act 3 reach, and zero blocker sessions.
4. Run the decision-quality matrix and compare its advisory candidates with actual session notes; do not remove or retune a command unless both sources identify the same problem.
5. Fix P0/P1 navigation, readability, wording, or pacing defects before any feature expansion.
6. Re-run gameplay, balance, campaign, save, visual, layout, motion, animation, package, and security gates after every observed blocker fix.
7. Promote to beta only after the human gates pass and a reviewer makes the release decision.

## Post-Beta Order

The preferred expansion order is audio feedback, key remapping/controller support, localization, richer visual assets, then new campaign content. Each addition must ship as one bounded vertical slice with save compatibility and the existing responsive/accessibility matrices. None of these features should enter the beta-candidate branch before the six-session evidence gate closes.

## Evidence Boundary

Automation may verify deterministic behavior, containment, navigation routes, report consistency, and packet safety. It cannot claim that a first-time player understood a choice, enjoyed the pacing, or completed a visible session. Human evidence remains `0/6` until real observed sessions are recorded with explicit attestation; generating a preparation packet does not change that count.
