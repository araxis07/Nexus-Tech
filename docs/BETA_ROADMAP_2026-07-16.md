# Beta Roadmap - 2026-07-16

## Product Position

NEXUS TECH 0.322.1 remains a late-alpha beta candidate at approximately 83% of a defensible beta. The vertical slice, six featured campaigns, 24 authored campaign routes, three difficulties, persistence, archive progression, endgame, responsive 2D shell, and automated release gates exist. The release blocker is observed usability, not missing content.

The latest automated execution record is
[Beta Execution Audit - 2026-07-29](BETA_EXECUTION_AUDIT_2026-07-29.md).

## Current Engineering Slice

The current beta candidate protects the complete owner-flow contract while retaining the executable next-session packet:

- every generated session packet now embeds its own required preflight command and binds manifest schema 3 to the intended packet path;
- preparation rejects packet output that aliases an evidence, tester, or rehearsal database or any SQLite journal, WAL, or shared-memory sidecar;
- execution-plan generation normalizes its packet and plan outputs, rejects aliases between them, and refuses to overwrite the evidence database or any SQLite sidecar;
- packet preparation, packet validation, and execution planning now share one local-path safety policy instead of maintaining independent normalization rules;
- validation rejects moved packets in addition to stale evidence, changed content, mismatched stores, and consumed profiles, keeping the handoff fail-closed before either visible launch;
- the live run header now prioritizes campaign goal, next-move timing, and End Turn state while leaving score and market diagnostics in Report;
- Focus action names now lead each button while fixed shortcuts use separate badges, and wide rows avoid duplicating the decision preview inside every button;
- Endgame readiness exposes a consistent `/100` scale and states that lower Reset Risk is safer without changing exit calculations;
- completed Review findings separate Cause from Lesson, identify the next run's first move, and wrap semantic run traits without hiding compact learning copy;
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
- the default Focus footer now separates `NEXT / COST / WHEN`, expected outcome, and skip risk into three measured lines instead of merging recommendation context into generic prose;
- compact risk cues remain complete at 820x620, while hover adds consequence context and the Recommended button shows AP cost plus urgency;
- the engine and 2D availability checks now share the existing zero-AP review/end-turn and one-AP operating-action policy, so Recommended disables when the current move cannot be afforded;
- the primary command and its workspace are excluded from alternatives while preference, Coach, and stable fallback order remain deterministic;
- Coach execution, direct keyboard commands, AP costs, simulation state, and balance are unchanged; schema 28 adds only human-beta retest lineage;
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
- `beta-playtest-plan` exposes all six campaign lanes while allowing only one fresh packet to be generated before the plan is refreshed;
- unresolved P0/P1 rows remain stored as history, while a guarded `--retest-of` session from a new first-time tester becomes the active gate row instead of leaving release readiness permanently blocked;
- while current-version evidence is `0/6`, that packet opens with a separate owner-only rehearsal gate covering recovery, campaign, Endgame, archive, and Progress routes without placing the human recorder inside the rehearsal gate;
- owner rehearsal, tester gameplay, and structured evidence now use three distinct database paths so prior saves, Continue state, and archives cannot contaminate a first-time observation;
- preparation allocates unique temporary gameplay profiles by default, rejects explicit profiles that already exist, and leaves the persistent evidence store only in recorder/status commands;
- the first packet includes isolated rehearsal and tester launches; later packets retain one fresh tester launch, the eight-step observation checklist, a deliberately invalid recorder template, and evidence-refresh commands;
- every active session packet defines deterministic `P0` release-blocker, `P1` usability-blocker, and `P2` polish classifications with explicit stop and recording responses;
- stored observation notes never enter the packet, generated artifacts default to `/tmp`, and preparation never writes a session row;
- every generated packet now carries a deterministic manifest, and `validate-beta-playtest-session-packet` rejects changed content, stale build/evidence state, a mismatched evidence store, or an already-used gameplay profile before handoff;
- the first packet now embeds `validate-beta-owner-rehearsal`, which revalidates the packet and evidence snapshot after visible play, keeps the tester profile fresh, and fails until the rehearsal database contains the exact target scenario with both campaign choices archived;
- the post-rehearsal gate explicitly leaves Pause, Back, Menu, Continue, Endgame switching, Progress, and Route Atlas confirmation as manual owner checks and never writes human-session evidence;
- motion-mode differentiation now evaluates animation density and disabled-state behavior independently from transient reduced-mode timing watches, while genuine reduced-mode stability failures remain blocking;
- `decision-quality-audit` compares operating-choice variety across the six campaigns and three difficulties, failing only missing ledger coverage while exporting repetition and low-variety candidates for human review;
- `beta-playtest-status --require-review-ready` now exits non-zero until all current-version human criteria pass, preventing release scripts from confusing an informative status report with a successful gate while retaining the final manual reviewer decision;
- no save migration, new catalog entry, control binding, or balance adjustment is introduced.

## Path To Beta

1. Run `prepare-beta-playtest-session` and keep its isolated rehearsal/tester/evidence database paths unchanged.
2. Run `validate-beta-playtest-session-packet` immediately before the rehearsal, follow the visible route from New Game through `Save & Archive` and `6 Open Progress` at 820x620, then run the packet's `validate-beta-owner-rehearsal` gate before opening the tester profile; record only defects actually observed and never run the human-session recorder for the rehearsal.
3. Observe six first-time sessions across all six featured campaigns using anonymous tester codes, classify each issue with the packet's `P0`/`P1`/`P2` policy, and use the structured local evidence command only after each real session. Regenerate `beta-playtest-plan` after every row rather than pre-allocating later testers.
4. Require at least 80% unaided turn-one completion, 100% Pause/Back/Menu recovery, at least 80% trade-off recall, at least 80% Act 3 reach, and zero blocker sessions.
5. Run the decision-quality matrix and compare its advisory candidates with actual session notes; do not remove or retune a command unless both sources identify the same problem.
6. Fix P0/P1 navigation, readability, wording, or pacing defects before any feature expansion, then use the generated `--retest-of` relationship with a new first-time tester so the original failure remains auditable.
7. Re-run gameplay, balance, campaign, save, visual, layout, motion, animation, package, and security gates after every observed blocker fix.
8. Run `beta-playtest-status --require-review-ready`, then promote to beta only after its fail-closed gate passes and a reviewer makes the release decision.

## Post-Beta Order

The preferred expansion order is audio feedback, key remapping/controller support, localization, richer visual assets, then new campaign content. Each addition must ship as one bounded vertical slice with save compatibility and the existing responsive/accessibility matrices. None of these features should enter the beta-candidate branch before the six-session evidence gate closes.

## Evidence Boundary

Automation may verify deterministic behavior, containment, navigation routes, report consistency, and packet safety. It cannot claim that a first-time player understood a choice, enjoyed the pacing, or completed a visible session. Human evidence remains `0/6` until real observed sessions are recorded with explicit attestation; generating a preparation packet does not change that count.
