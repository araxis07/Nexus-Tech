# Changelog

## 0.136.0 - 2026-06-07

- Added a `Scene Motion Profile` cell to `audit-2d-animation` so every captured 2D scene must have an explicit motion-layer budget and unprofiled scenes fail the release gate
- Added `docs/OPEN_WINDOW_ANIMATION_PLAYTEST.md`, a manual open-window animation framework for compact, small, and presentation windows across full, reduced, and off motion modes
- Updated release and animation documentation so scene-profile, pacing, visual-fatigue, actor-readability, and manual playtest blockers are reviewed together before presenting the 2D build

## 0.135.0 - 2026-06-07

- Added an `Animation Pacing Budget` cell to `audit-2d-animation` so animation density, residual pulse cooldown, and frame timing are release-gated before manual open-window playtesting
- Added GitHub Actions upload of full/off visual audit PNG captures as a short-retention artifact so CI failures can be reviewed visually without committing generated images
- Updated animation playtest and release documentation to align manual readability checks with the new pacing and CI capture gates

## 0.134.0 - 2026-06-07

- Added GitHub Actions release gates for 2D headless smoke checks, motion audits, visual audits, and animation-completeness audits so actor-readability, visual-fatigue, and blocked-action feedback regressions fail CI
- Added CI runtime checks for package version and doctor output alongside catalog validation and the full test suite
- Updated release documentation so local checks and GitHub checks cover the same 2D animation gates before manual open-window playtesting

## 0.133.0 - 2026-06-07

- Added blocked-action animation feedback cards with a distinct warning outcome, shake treatment, reason detail, and targeted flash pulses so failed/disabled commands no longer look like successful action feedback
- Added `blocked-action-feedback` visual coverage to `audit-2d-visual` and a required `Blocked Action Feedback` cell to `audit-2d-animation`
- Updated actor reactions and regression coverage so blocked product/team/board/customer command families can put the relevant sprites into a `blocked` state

## 0.132.0 - 2026-06-07

- Added deterministic visual-fatigue metrics to `audit-2d-visual`, including edge-density and bright-pixel pressure checks so overly cluttered or flashy 2D captures can fail automatically
- Added a `Visual Fatigue Budget` cell to `audit-2d-animation`, keeping animation completeness tied to both scene/layer coverage and visual health budgets
- Updated CLI output and regression coverage so visual audit captures report clutter/brightness pressure alongside color, contrast, expected layers, and actor-readability gates

## 0.131.0 - 2026-06-06

- Added actor sprite readability footprints and collision checks so title/menu, run, inspector, endgame, summary, and review actors are verified against viewport and click-target overlap
- Added the `actor-readability` layer to visual and animation audits, making actor/sprite readability a required automated gate instead of only a manual playtest note
- Made live-run actor states react to the latest action-feedback and critical impact cues so product, finance, board, customer, team, and founder sprites communicate the current command context

## 0.130.0 - 2026-06-06

- Expanded deterministic shape-sprite actor coverage to title/menu, inspector overlays, the endgame board, and review scenes so major 2D surfaces now have explicit character motion
- Upgraded visual, motion, and animation audits with scene-specific actor layers for title, inspector, endgame, and review surfaces while preserving `--motion-mode off` gates
- Added regression coverage for the broader actor surface matrix and kept manual open-window readability checks as the remaining human QA step

## 0.129.0 - 2026-06-06

- Added a deterministic shape-sprite actor timeline for the live run and turn-summary scenes, covering founder, team, customer, board, finance, product, and exit-gate roles without external image assets
- Promoted the sprite/actor animation gap from advisory to a required `audit-2d-animation` gate with visual-layer coverage, motion telemetry, and `--motion-mode off` validation
- Added regression coverage and playtest checklist documentation for actor/sprite animation while keeping manual open-window readability review explicit

## 0.128.0 - 2026-06-06

- Added an outcome cinematic layer for victory/shutdown overlays so final run states have dedicated 2D motion instead of a static modal only
- Added `audit-2d-animation`, a combined animation-completeness gate that checks required visual layers, motion budgets, off-mode behavior, and advisory gaps
- Extended visual and motion audits with outcome-cinematic coverage and documented the remaining manual playtest and sprite/actor-layer gaps explicitly

## 0.127.0 - 2026-06-06

- Added late-game command choreography cue cards for terminal, path-repair, board, finance, and pipeline commands so cockpit/gate actions read as explicit 2D motion
- Added pending-event option preview motion and turn-summary outcome lanes so choices and post-turn results animate before and after resolution
- Extended visual and motion audits with pending-preview, late-game choreography, summary-lane telemetry, and deterministic visual baseline signatures

## 0.126.0 - 2026-06-06

- Added product-card drama animation with quality/fit shimmer, bug beacons, debt cracks, and user-flow particles so product state reads as live 2D motion
- Added finance/board/runway risk drama and pending-event choice consequence cues so danger states and event decisions leave visible feedback
- Expanded turn-summary metric/product reveal sequencing plus visual and motion audit telemetry for product drama, risk drama, pending-choice cues, and summary sequencing

## 0.125.0 - 2026-06-06

- Added motion-aware enter transitions for run overlays including pending events, action pickers, text modals, deep panels, inspectors, help, and final outcome dialogs
- Added overlay exit shimmer cues so closing panels, pickers, text input, help, and inspectors leaves a short visible handoff instead of disappearing instantly
- Added a turn-summary cinematic rail and audit telemetry for overlay transitions and summary cinematic state while preserving `--motion-mode off`

## 0.124.0 - 2026-06-06

- Added a 2D impact cue layer that turns successful state changes into short visible delta cards for cash, users, reputation, board pressure, and product metrics
- Wired impact cues into direct actions and pending-event resolutions while preserving the existing full/reduced/off motion-mode controls
- Extended visual and motion audits plus regression coverage so impact cues are captured as expected layers and disabled in `--motion-mode off`

## 0.123.0 - 2026-06-05

- Added a deterministic `audit-2d-visual` QA harness that renders title, meta, live run, picker/action-feedback, inspector, turn-summary, and review captures across core viewport sizes
- The visual audit now checks frame checksum, sampled color variance, contrast, non-dark coverage, and expected active layers such as transitions, picker/inspector overlays, action feedback, and summary reveal state
- Added optional PNG export for visual review without committing generated images, plus CLI/reporting coverage and regression tests for the new visual audit path

## 0.122.0 - 2026-06-05

- Added a command-specific action feedback cue layer to the 2D run scene so successful commands, picker launches, create-product modals, end-turn confirmation, and inspector opens now produce short visual feedback cards
- Mapped feedback cues across product, finance, team, customer, partnership, pipeline, board, endgame, inspector, and turn-resolution families while preserving the existing targeted panel/stat/product motion lanes
- Extended motion-audit telemetry and regression coverage so full motion reports active action-feedback samples and `--motion-mode off` proves the new cue layer is disabled

## 0.121.0 - 2026-06-05

- Added deterministic shape-based entity motion to the 2D run HUD, including moving stat beads, product data packets, and active panel strips so the game reads less like a static dashboard
- Wired entity motion strength through `full`, `reduced`, and `off` motion modes, with off mode disabling the new idle entity animation alongside highlight pulses and scene transitions
- Extended motion-audit telemetry and regression coverage so full/reduced modes expose active entity samples and off mode proves entity motion is disabled

## 0.120.0 - 2026-06-05

- Added a shared 2D scene-entry transition layer with fade, sweep, scanline, and scene-label treatment for title, live run, turn summary, and review scenes
- Wired transition keys across boot, title-to-run, title-to-review, run-to-summary, run-to-review, summary-to-run, summary-to-review, and review-to-title flows while preserving `--motion-mode reduced/off`
- Extended motion-audit telemetry and regression coverage so full/reduced modes expose active scene transitions and off mode proves transition animation is disabled

## 0.119.0 - 2026-06-04

- Added a 2D `--motion-mode full|reduced|off` option across play, load, continue, menu, and motion-audit commands so highlight animation intensity can be lowered or disabled without changing gameplay
- Wired motion mode through title, run, review, and turn-summary scene transitions so save loads, wizard launches, archive reviews, post-turn summaries, and final reviews preserve the selected motion setting
- Extended regression coverage and docs for reduced/off pulse behavior, scene propagation, CLI routing, and deterministic audit reporting

## 0.118.0 - 2026-06-04

- Expanded the 2D animation audit into title/save/archive subflows, including save-slot detail, rename text overlays, delete confirmation, archive browsing, meta board, and wizard overlays
- Added explicit inspector interaction motion for section, item, page, sort, filter, actionable focus, and hotspot focus changes, then wired those cues into the inspector overlay emphasis
- Added long-run pulse-pressure coverage to `audit-2d-motion` so dense repeated highlight banks must cool back under budget before release checks pass

## 0.117.0 - 2026-06-04

- Expanded `audit-2d-motion` beyond the live run and turn summary so it now exercises title/menu motion, wizard overlay motion, review-scene motion, inspector overlays, and picker overlays in the same headless audit pass
- Added a 2D flow request-path audit that checks surfaced commands and inspector item actions before they can fall through to runtime `Needs More 2D Coverage` or `Inspector Action Missing` warnings
- Upgraded CLI output, regression coverage, release docs, and package/runtime versioning for the broader animation-completeness gate

## 0.116.0 - 2026-06-04

- Added a deterministic headless `audit-2d-motion` gate that renders stressed live-run and turn-summary animation banks across desktop and compact viewports
- The audit now reports before/after pulse-bank counts plus average frame time so long-session motion cooldown can be checked without manual visual playtesting
- Added regression coverage for the motion audit helper and CLI route, documented the audit in the release notes, and promoted package metadata/runtime versioning to `0.116.0`

## 0.115.0 - 2026-06-04

- Added pulse-bank pruning so crowded 2D scenes can drop the weakest unprotected highlight pulses instead of letting low-value residual motion accumulate across long sessions
- Run-scene stability now prunes dense low-value pulses while preserving feed, overlay, and active panel cues, and turn summaries now do the same for timeline/metrics-heavy states so late-game resolution scenes cool down faster after busy turns
- Extended regression coverage to pulse pruning plus run-scene and summary-scene stabilization helpers, then promoted package metadata and runtime versioning to `0.115.0`

## 0.114.0 - 2026-06-03

- Added pulse-pressure telemetry to the 2D motion layer so live scenes and turn summaries can measure how many highlight pulses are active and how much total intensity is already on screen
- Tuned run-scene event normalization and feed motion so dense pulse banks now shorten low-severity TTLs further and damp live feed intensity before long sessions or overlay-heavy states turn into motion spam
- Tuned turn-summary sequencing under pressure so heavy summary pulse banks slow reveal cadence slightly and reduce target-lane pulse intensity instead of stacking every new cue at full strength
- Added regression coverage for pulse-bank pressure, busy-feed damping, busy-summary damping, and the new reveal-pressure helper, then promoted package metadata and runtime versioning to `0.114.0`

## 0.113.0 - 2026-06-03

- Tightened 2D compact-button rendering by suppressing detail copy on short buttons and vertically centering their primary labels, which stops inspector pagers, summary footer controls, and other compact actions from bleeding text outside their bounds
- Reworked narrow summary stacking so `820x620`-class turn summaries keep a visible timeline lane, shrink strategy height responsively, compact metric-card copy earlier, and drop footer detail text before it starts clipping
- Cleaned up compact endgame inspectors by removing the overlapping focus-note line on tight layouts, shortening pager/action rows, and preserving the selected-row/action badges as the primary cue instead of letting explanatory copy collide with buttons
- Extended 2D regression coverage to the new compact focus-summary and summary-layout helpers, then promoted package metadata and runtime versioning to `0.113.0`

## 0.112.0 - 2026-06-03

- Stabilized 2D live-event retention by ranking backlog cards around severity, workspace targets, and key titles such as `Gate Command`, `Endgame Cockpit`, and `Next Focus`, so narrow or overlay-heavy runs drop low-signal cards before late-game repair cues
- Tightened hover-tooltip layout on the 2D shell with narrower presets, top/bottom clamping, and cursor-flip placement logic so hints stay readable instead of spilling off cramped windows
- Preserved surfaced-command motion coverage at `43 specific / 0 family / 0 none` while extending regression coverage to priority backlog retention and tooltip-bound helpers, then promoted package metadata and runtime versioning to `0.112.0`

## 0.111.0 - 2026-06-03

- Tuned live-run event pacing so low-severity feed cards now shorten their lifetime under dense queues, overlay-heavy states, and narrow windows instead of lingering long enough to create motion noise
- Tightened feed density on smaller layouts by letting narrow-window and dense-overlay states drop to a one-card visible queue when needed, while compacting live event-card detail to one line on tighter card widths
- Smoothed turn-summary sequencing by slowing reveal cadence when more events are present, damping low-severity summary pulses on narrow/dense scenes, and making `Next Focus` handoff cards escalate into warning/flash treatment when they route the player back into finance, board, customer, or partnership repair lanes
- Preserved command-specific motion coverage at `43 specific / 0 family / 0 none` for surfaced 2D commands and extended regression coverage to the new pacing, TTL, and late-game handoff helpers, then promoted package metadata and runtime versioning to `0.111.0`

## 0.110.0 - 2026-06-03

- Completed specific choreography coverage for the last surfaced 2D family commands, including debt bridges, angel funding, debt paydown, restructure execution, channel-mix resets, partner renegotiation, partner recovery sprints, and billing stabilization
- Promoted the surfaced-command motion audit from `35 specific / 8 family / 0 none` to `43 specific / 0 family / 0 none`, so every command currently surfaced by the guided opening, coach, risk forecast, endgame board, and deep panels now has a command-specific choreography card
- Tightened turn-flow cohesion by routing turn-resolution `Gate Command` events into the matching workspace panel as well as the endgame board and timeline, so late-game summaries now pulse the actual repair lane they are pointing at
- Expanded regression coverage to enforce all surfaced commands as `specific` motion profiles, preserve at least one family-motion fallback for deeper unsurfaced commands, and keep gate-command timeline cards tied to a concrete workspace target, then promoted package metadata and runtime versioning to `0.110.0`

## 0.109.0 - 2026-06-03

- Added a 2D motion-coverage audit layer so surfaced commands from the guided opening, coach, risk forecast, endgame board, and deep panels can be classified as `specific`, `family`, or `none` instead of relying on visual spot-checks alone
- Expanded specific choreography coverage across review/report flows, hiring-funnel actions, roadmap/project work, product creation, budget-setting, and other surfaced commands so the 2D shell no longer has any `none`-coverage commands in its main guided/control surfaces
- Tightened review-command workspace routing so `review_*` and `view_report` action cards now pulse the corresponding panel instead of only refreshing the generic feed lane
- Added a dedicated action-motion audit note plus regression coverage that now enforces zero uncovered surfaced commands and promotes key late-game / finance / review commands to `specific` motion profiles, then promoted package metadata and runtime versioning to `0.109.0`

## 0.108.0 - 2026-06-03

- Extended the 2D choreography pass into late-game path work so concrete gate commands such as board recovery, channel firebreaks, covenant firewalls, renewal watches, and reset-buffer setup now emit path-specific motion cards instead of falling back to generic family pulses
- Prioritized turn-resolution timeline cards around exit-gate state, gate commands, and strategic outlook before lower-signal deltas so narrow staged summaries keep the late-game story visible even when only a few cards fit
- Tightened endgame cockpit status copy on smaller windows by compacting gate and hotspot command tokens inside the footer line instead of dumping long raw snake-case command ids across the HUD
- Expanded regression coverage for endgame command choreography, turn-resolution event ordering, compact cockpit footer copy, and the earlier feed/timeline pacing helpers, then promoted package metadata and runtime versioning to `0.108.0`

## 0.107.0 - 2026-06-03

- Ran another 2D motion-and-pacing pass focused on small-window animation readability instead of adding new systems, using fresh rendered audits for the live feed, title feed, endgame inspector, and staged turn summary
- Added adaptive event-feed caps for the title flow and live run so tighter layouts and overlay-heavy states now show fewer transient cards instead of flooding the visible queue
- Slowed turn-summary timeline reveal slightly on narrower windows and capped visible timeline cards by available height so post-turn animation stays readable rather than racing the panel bounds
- Expanded inspector footer breathing room on small windows so paging controls and item-level actions no longer crowd the bottom of endgame and pipeline records as aggressively
- Expanded regression coverage for title-feed pacing, live event-queue pacing, and summary reveal timing, then promoted package metadata and runtime versioning to `0.107.0`

## 0.106.0 - 2026-06-03

- Ran a second frame-backed 2D UX pass focused on narrow-window late-game scenes after `0.105.0`, using captured endgame-inspector, title-meta, and turn-summary frames to close the next spacing and density gaps
- Reserved a dedicated footer band for the live action bar, compacted footer button copy by layout width, and kept the run HUD readable without letting dense bottom-row controls bleed into the status lines
- Added compact meta-board behavior for stacked title layouts so the progression board and sidebar no longer fight for the same vertical space on 960x640-class windows
- Tightened small-window inspector density with adaptive item paging, more aggressive line limits, and shorter item-action detail copy so endgame projection rows stop collapsing into their own action buttons
- Trimmed turn-summary focus-command copy so the strategic handoff card stops dumping long raw command detail into a shallow button slot
- Expanded regression coverage for footer layout compaction, adaptive inspector paging, compact meta-board summaries, and summary-command copy, then promoted package metadata and runtime versioning to `0.106.0`

## 0.105.0 - 2026-06-03

- Ran a frame-backed 2D visual UX pass against captured title, run, inspector, endgame, review, and turn-summary scenes instead of relying only on deterministic test output
- Tightened the live run header so score metadata now renders as a compact `score (tier)` label and no longer spills a raw `RunScore(...)` object across the top bar
- Simplified the action-bar footer down to one status line plus one watch-or-hover hint line so late-game guidance stops colliding with the bottom control row on dense layouts
- Compacted deep-panel and endgame action detail copy so overlay buttons keep their command context without overrunning narrow button bounds
- Improved filtered inspector empty states with an explicit recovery hint, then expanded regression coverage for compact score labels and overlay-detail compaction
- Added a refreshed visual-UX audit note and promoted package metadata and runtime versioning to `0.105.0`

## 0.104.0 - 2026-06-03

- Ran another playtest-driven 2D UX pass centered on late-game clarity rather than adding new systems, focusing on cockpit guidance, inspector scanning, and hover language
- Upgraded the action-bar footer so endgame panels now expose gate and hotspot context directly, while inspectors surface their next primary action or blocked prerequisite in the live status line
- Improved cockpit hover hints so late-game panel buttons now tell the player which workspace they will hand off into instead of only naming the raw command
- Strengthened inspector focus readability with a `READY` / `BLOCKED` status chip on the active row plus a richer focus note, and added regression coverage for endgame footer status, cockpit tooltip routing, and inspector action summaries
- Added a dedicated visual-UX audit note and promoted package metadata and runtime versioning to `0.104.0`

## 0.103.0 - 2026-06-02

- Ran a fresh 2D playtest-driven polish pass focused on late-game cockpit readability, event-feed noise, and inspector discoverability instead of adding more systems
- Coalesced duplicate frontend events so repeated cockpit briefs, handoffs, and similar warnings refresh in place instead of flooding the live feed during heavier late-game loops
- Added contextual footer status lines for workspace, picker, inspector, and pending-event states so the action bar now explains the current layer and next control path more clearly on both wide and narrow layouts
- Strengthened inspector selection affordances with a clearer active-row fill and `ACTIVE` badge, then expanded regression coverage for event coalescing and footer-context state
- Added a dedicated playtest audit note and promoted package metadata and runtime versioning to `0.103.0`

## 0.102.0 - 2026-06-02

- Upgraded the 2D endgame board into a stronger late-game cockpit with a dedicated `Hotspot Review` action, richer blocked-path / hotspot detail lines, and a projection-route inspector item so exit pressure can route directly into the right recovery workspace
- Added cockpit brief and handoff events in the 2D run scene so opening the endgame board now summarizes the current blocked-path state, while cockpit commands visibly hand the player off into the matching finance, board, customer, or partnership workspace with picker / inspector cues
- Expanded regression coverage for cockpit brief emission, hotspot-review routing, and the richer endgame action set to keep late-game 2D usability from regressing as motion and panels evolve
- Added a dedicated cockpit audit note and promoted package metadata and runtime versioning to `0.102.0`

## 0.101.0 - 2026-06-02

- Expanded 2D action choreography coverage beyond core product work so finance, board, customer/support, partner/channel, pipeline, roadmap, and hiring command families now emit motion-aware event cards with focused UI targets
- Added motion consistency to `TitleScene` and `ReviewScene`, including animated mode transitions, feed emphasis, and overlay transitions for text input and delete confirmation instead of leaving those flows visually static
- Tightened run-scene pre-action pulses so finance, board, report, customer, and pipeline commands animate the most relevant stats and late-game panels before their state deltas arrive
- Added regression coverage for finance-family choreography, board-command motion routing, title-scene mode/overlay motion, and review-scene motion initialization
- Promoted package metadata and runtime versioning to `0.101.0`

## 0.100.0 - 2026-06-02

- Added action-specific 2D choreography cards for core product, hiring, pipeline, pricing, and partnership commands so the frontend now shows a distinct motion narrative before the normal delta cards land
- Expanded overlay transitions across deep panels, inspectors, pickers, text input, help, and pending-event layers so the run scene uses one motion language instead of mixing animated widgets with static modal layers
- Added turn-summary handoff back into the live run, including a seeded `Next Focus` event and automatic workspace-panel restore for the summary's recommended command
- Added regression coverage for choreography-card emission, overlay-motion triggering, and summary-to-run focus restoration
- Promoted package metadata and runtime versioning to `0.100.0`

## 0.99.0 - 2026-06-02

- Added a shared 2D motion foundation with reusable panel, button, and progress-bar emphasis states plus a pulse bank for short-lived highlight cues across the animated frontend
- Added targeted frontend event metadata so action and turn-resolution events now carry motion style and UI targets such as stats, products, endgame panels, report panels, and summary channels instead of only free-form event text
- Wired the run scene to react to those event targets with animated stat lanes, pulsing product cards, emphasized action-bar panel buttons, workspace-aware coach emphasis, and sliding event cards in the live feed
- Extended the staged turn-summary scene with the same motion language so strategy, timeline, and metric cards now inherit endgame/report emphasis instead of using a completely separate visual rhythm
- Added regression coverage for motion-target emission, endgame timeline targeting, and run-scene pulse activation after live action requests
- Promoted package metadata and runtime versioning to `0.99.0`

## 0.98.0 - 2026-06-02

- Added 2D inspector memory per deep panel so reopening pipeline, finance, board, customer, and report inspectors restores the last section, page, row focus, and sort/filter state instead of dumping players back at the default section
- Added `A` and `H` inspector focus controls plus matching clickable shortcuts so actionable rows and highest-risk hotspot rows can be surfaced without cycling through every filter and sort combination by hand
- Added workspace routing for major 2D commands so finance, customer, partnership, team, pipeline, board, and report actions now bring the matching deep panel into focus before launching their picker, inspector, or direct action flow
- Expanded regression coverage for inspector-state restore, actionable/hotspot hotkeys, and finance-workspace routing from command launch
- Promoted package metadata and runtime versioning to `0.98.0`

## 0.97.0 - 2026-06-01

- Retuned the deterministic balance autoplayer so founder-pressure openings now respect the angel-round cap, stop downshifting profit-machine scenarios into budget pricing too early, and enter cash-guard / conserve posture sooner under cash, debt, or board stress
- Tightened autoplay sequencing around early feature creep, headcount expansion, and support-lane focus so finance and execution controls are applied before fragile openings burn through runway
- Added regression coverage for the new founder-survival autoplay policy, including angel-cap handling, profit-first pricing preservation, and cash-guard activation
- Re-ran founder-focused and multi-scenario balance audits, closed the previous founder watch cells, and promoted package metadata and runtime versioning to `0.97.0`

## 0.96.0 - 2026-06-01

- Expanded the 2D endgame board into a fuller late-game cockpit with direct path-specific fix buttons for IPO, M&A, independence, and reset recovery instead of only one global gate command
- Added reusable endgame cockpit action coverage so regression tests now assert that the 2D endgame board keeps surfacing all four path-fix buttons as the cockpit evolves
- Ran a fresh internal 2D playtest and balance audit pass, captured the results in repo docs, and tightened the release checklist so `doctor`, 2D headless smokes, and `balance-audit` are part of the baseline release routine
- Promoted package metadata and runtime versioning to `0.96.0`

## 0.95.0 - 2026-05-31

- Added a broader 2D usability polish pass with responsive run-scene layout shifts, active panel highlighting in the action bar, stronger selected-product affordances, and live hover tooltips instead of only footer hints
- Upgraded the 2D turn-resolution scene into a staged post-turn readout that reveals cash and demand, operating pressure, and strategic outlook in sequence instead of dumping a flat event list all at once
- Added strategic delta summaries to the turn-resolution view so late-game readiness, blocked-gate movement, the next endgame command, and dominant pressure shifts are visible before returning to the run
- Expanded turn-resolution events with gate-command and strategic-outlook cards so post-turn animation stays aligned with the endgame board and late-game path guidance
- Expanded regression coverage for the richer turn-summary model, endgame-aware resolution events, small-window drawing, and the new staged summary scene behavior
- Promoted package metadata and runtime versioning to `0.95.0`

## 0.94.0 - 2026-05-31

- Added a dedicated in-run 2D endgame and exit board so late-game readiness, blocked gates, dominant pressure, and the next repair command are visible without dropping back to terminal reporting
- Added structured endgame inspector sections for exit paths, per-path watchlists, and projected outcome summaries so the 2D frontend can drill into late-game posture instead of only surfacing a compact overlay
- Added panel-level inspector access from the 2D shell, including an `I` hotkey and overlay button, so deep panels can open their detailed inspectors directly instead of relying only on command-specific review routes
- Expanded regression coverage for the new endgame panel, endgame inspector action availability, and run-scene inspector access from the deep-panel hotkey flow
- Promoted package metadata and runtime versioning to `0.94.0`

## 0.93.0 - 2026-05-31

- Added a dedicated 2D meta board scene so the title flow now surfaces campaign tier, dominant archive path, next gap, next reward, and campaign ladder progress without leaving the frontend shell
- Upgraded 2D inspectors with sort and filter controls plus a clearer focus strip, making larger candidate, pipeline, and partner lists easier to navigate and act on from inside the frontend
- Added an in-run help overlay, hover-driven footer hints, and safer modal sizing so the 2D frontend is easier to learn and less brittle on smaller windows
- Added parity-audit regression coverage for guided-opening, coach, risk, endgame-gate, and deep-panel commands so surfaced 2D actions stay either executable or explicitly explained
- Promoted package metadata and runtime versioning to `0.93.0`

## 0.92.0 - 2026-05-28

- Turned the 2D inspector overlays into interactive control surfaces with section focus, row selection, page navigation, and item-level actions for live releases, deals, roadmap projects, candidates, teammates, and partner records
- Added item-targeted 2D action routing for employee, candidate, release, sales-deal, roadmap-project, and partnership commands so inspector rows can execute the entity they display instead of falling back to generic top-level pickers
- Added archive comparison and campaign-progression summaries to the 2D title sidebar so menu and archive views now surface campaign tier, next reward, next gap, and dominant archive path without leaving the frontend shell
- Expanded regression coverage for item-targeted inspector requests, interactive inspector paging/action flow, and title-scene meta progression summaries
- Promoted package metadata and runtime versioning to `0.92.0`

## 0.91.0 - 2026-05-28

- Added full-screen 2D inspector overlays for team, finance, customers, partnerships, board, pipeline, and report review commands so the frontend can inspect live state without dropping back to CLI-style summaries
- Expanded panel data with structured inspector sections for sales deals, releases, roadmap projects, hiring candidates, board scorecards, recent funding, milestones, and event history
- Routed `review_*` and `view_report` commands inside the 2D shell to those inspectors so common coach and panel review actions now have explicit frontend coverage instead of only transient action messages
- Surfaced compact disabled-action reasons inline on 2D action buttons and deep-panel buttons so blocked actions explain missing prerequisites before the player clicks into dead ends
- Added regression coverage that panel inspector sections render, panel actions stay either executable or explicitly blocked, and enriched pipeline states keep their 2D command coverage
- Promoted package metadata and runtime versioning to `0.91.0`

## 0.90.0 - 2026-05-28

- Added a fuller 2D new-game wizard that lets the frontend choose scenario, difficulty, campaign start, campaign goal, company name, product name, save slot, and optional seed before opening a run
- Added in-shell save-slot management to the 2D title flow so slots can be loaded, renamed, duplicated, and deleted without dropping back to the CLI
- Expanded 2D deep-dive coverage with board, pipeline, and report panels plus broader action pickers for candidate funnel, release, sales-deal, and roadmap-project commands
- Added disabled-reason feedback for blocked 2D actions so the UI now explains missing employees, releases, deals, partnerships, pending events, and similar prerequisites directly
- Tightened title-scene modal handling so text entry and delete confirmations can be cancelled cleanly from the keyboard instead of leaking through to background menu shortcuts
- Expanded regression coverage for wizard catalogs, new panel surfacing, command availability reasons, and the wider 2D action picker set
- Promoted package metadata and runtime versioning to `0.90.0`

## 0.89.0 - 2026-05-27

- Added a 2D title flow with `menu-2d`, a save-slot browser, archive browser, and archived run review scene so the animated frontend can now open and inspect persistent runs without dropping back to the CLI first
- Added deep-dive 2D operational overlays for team, finance, customers, and partnerships, each with context-aware action buttons that surface pricing, packaging, capital-plan, functional-budget, and partner-recovery commands already supported by the simulation layer
- Added a reusable text input modal to the 2D shell and used it to name newly created products from inside the frontend instead of falling back to generated defaults only
- Promoted completed 2D runs into a dedicated review scene with postmortem findings, next-focus commands, and saved-run persistence controls instead of only showing a terminal overlay
- Expanded regression coverage for the new 2D menu launcher, deep-dive panel view models, review view models, and updated CLI routing
- Promoted package metadata and runtime versioning to `0.89.0`

## 0.88.0 - 2026-05-27

- Split the first `pygame-ce` frontend shell into a live `RunScene` plus an animated `TurnSummaryScene` so `end_turn` now resolves through a dedicated post-turn timeline instead of only dropping transient event cards into the dashboard
- Added a reusable 2D context-picker layer for strategy, roadmap, budget, support lane, hiring, employee assignment, pricing, channel creation, and partnership-targeted recovery commands so the frontend can collect deeper action context without falling back to the CLI as often
- Added clickable product cards, coach cards, modal options, save/continue controls, and a two-row action bar so the 2D shell is no longer keyboard-only
- Tightened the 2D HUD around snapshot chips, compact coach/risk cards, and a clearer action bar while keeping the existing animated gauges and product metrics
- Expanded regression coverage for picker generation, employee-context selection, turn-summary view models, and the updated headless frontend shell
- Promoted package metadata and runtime versioning to `0.88.0`

## 0.87.0 - 2026-05-27

- Added a lightweight `pygame-ce` 2D frontend shell with a real render loop, animated gauges, product cards, event overlays, and a keyboard-driven dashboard scene
- Added a view-model adapter, tween bank, event stream, input map, and widget layer so the simulation can render outside the Rich terminal without rewriting core game rules
- Added `play-2d`, `load-game-2d`, and `continue-last-game-2d` commands plus headless frame caps for smoke testing the 2D frontend in automation
- Added autosave-on-exit behavior for the 2D shell and support for resolving pending events, ending turns with warning confirmation, and applying a focused subset of high-signal gameplay actions
- Promoted package metadata and runtime versioning to `0.87.0`

## 0.86.0 - 2026-05-26

- Added explicit Turn Coach "Not Now" guidance so players see which commands should be delayed and why instead of only seeing the next recommended move
- Added end-turn warning confirmation gates that stop high-risk `end_turn` commits behind a clear warning panel when the sample turn points to shutdown, critical risk, or sharp governance deterioration
- Archived postmortem summaries and next-focus commands with completed runs so `list-archives`, `compare-archives`, and progression review keep the last run lesson attached to the meta layer
- Tuned autoplay decision rules and several stressed scenarios so `debt_crunch`, `vc_sprint`, `founder_journey`, `bootstrap_studio`, `agency_pivot`, and `enterprise_compliance` are less likely to fail for avoidable reasons during balance sweeps
- Made partnership creation ids deterministic across resumed runs so save/load replay stays stable when new channel deals open after a restore
- Expanded regression coverage for warning gates, archive review metadata, deterministic replay, balance resilience, and updated scenario finance seeds
- Promoted the package version to `0.86.0`

## 0.85.0 - 2026-05-26

- Added an End-Turn Preview panel that projects one deterministic sample turn ahead and surfaces cash, runway, reputation, user, board-pressure, support, and channel-risk deltas before the player commits
- Added Failure Postmortem and After-Action Review summaries so shutdown and victory screens rank the main strain lanes, the command that should have been run earlier, and the lesson for the next run
- Added explicit difficulty messaging across intro, dashboard, report, quick guide, and tutorial so `builder`, `standard`, and `founder` communicate intended play style and failure mode instead of only hidden tuning values
- Added balance threshold gates with pass/watch/fail expectations per scenario and difficulty to the matrix, audit readout, and Markdown balance report
- Expanded regression coverage for preview, postmortem, balance thresholds, difficulty guidance, and presentation rendering
- Promoted the package version to `0.85.0`

## 0.84.0 - 2026-05-26

- Added a guided opening checklist that adapts the first 6 turns around hiring, assignment, product stabilization, reporting, and first control reviews
- Expanded Turn Coach into a short mission board with action windows and explicit "if skipped" consequences for each ranked command
- Added a Risk Forecast panel to the dashboard and report so the next-turn failure modes and mitigations are visible without reading every subsystem
- Expanded the tutorial and quick guide around Turn Coach, Risk Forecast, and the safer early-turn control loop
- Upgraded Markdown balance reports with a tuning-priority summary so balance sweeps point to the highest-signal scenario and difficulty cells faster
- Added regression coverage for guided opening progression, risk forecast command validity, Turn Coach timing metadata, and balance report priorities
- Promoted the package version to `0.84.0`

## 0.83.0 - 2026-05-26

- Added a Turn Coach mission board that ranks the next commands from endgame gates, finance planning, support queues, channel dependency, and board pressure
- Surfaced the Turn Coach in the main dashboard and compact report so players can see the primary command plus ranked next actions without reading every deep panel
- Added command-source and urgency metadata to each coach recommendation for clearer triage
- Added regression coverage that the coach emits valid `TurnAction` commands and stays aligned with the endgame gate command alert
- Promoted the package version to `0.83.0`

## 0.82.0 - 2026-05-25

- Added concrete `TurnAction` command ids for every IPO, M&A, independence, and board-reset gate action
- Added a primary gate command alert so blocked gates now point to the exact command to run next
- Surfaced gate command alerts and command lists in victory, scorecard, and late-game dashboard/report panels
- Added regression coverage that gate commands stay valid against the `TurnAction` catalog
- Promoted the package version to `0.82.0`

## 0.81.0 - 2026-05-25

- Added actionable gate plans beside each IPO, M&A, independence, and board-reset outcome gate
- Added a primary gate alert to endgame pressure and exit evaluation so blocked routes point to the next concrete repair action
- Surfaced gate alerts and gate actions in victory, scorecard, and late-game dashboard/report panels
- Added regression coverage for gate action propagation and blocked-gate alert behavior
- Promoted the package version to `0.81.0`

## 0.80.0 - 2026-05-25

- Added path outcome gates to endgame pressure, exit evaluation, dashboard panels, and late-game readouts so IPO, M&A, independence, and board-reset routes show open/blocked status directly
- Added focused support-lane follow-up carryover so enterprise, billing, and onboarding lane focus keeps relieving matching account pressure between explicit recovery actions
- Added channel failure-mode and recovery-priority identity to partnership portfolio summaries and dashboard channel readouts
- Sharpened finance planning under board-reset pressure so reset runs prioritize board control stabilization and reserve/governance resilience signals
- Added regression coverage for outcome gates, focused support follow-up, channel failure identity, and board-reset finance priority
- Promoted the package version to `0.80.0`

## 0.79.0 - 2026-05-25

- Deepened the four late-game watch actions so they now promote recovered accounts back to `ACTIVE` when their metrics genuinely stabilize instead of only lowering raw pressure numbers
- Added board-reset follow-up relief behind the watch actions so enterprise, billing, onboarding, and white-glove recovery can directly cool `board_resolution_due`, governance heat, and restructuring pressure when reset pressure is lane-driven
- Expanded finance-planner logic so `run_enterprise_reference_watch` now surfaces inside `board_reset_risk` runs when flagship enterprise pressure is still one of the drivers of the reset path
- Upgraded `board_reset_operating_watch` from a pure ledger wrapper into a real follow-up event with extra lane-focus, board-pressure, and governance consequences
- Sharpened board-reset endgame identity by making reset watchlists, scorecards, recommendations, and restructure variants reflect reserve posture, hotspot lane, and cleared board resolutions more explicitly
- Added regression coverage for the new board-reset follow-up behavior, planner recommendation path, watch-event consequences, and `Controlled Recovery Reset` exit classification
- Promoted the package version to `0.79.0`

## 0.78.0 - 2026-05-25

- Added account-targeted watch actions `run_enterprise_reference_watch`, `run_billing_renewal_watch`, `run_onboarding_go_live_watch`, and `run_white_glove_retention_watch` so late-game support recovery can focus on individual at-risk accounts instead of only broad lane programs
- Added `set_board_reset_contingency_buffer` to push reserve-heavy board-reset posture changes deeper into endgame capital planning
- Added watch-stage path events `ipo_book_anchor_watch`, `buyer_close_anchor_watch`, `independence_cash_solvency_watch`, and `board_reset_operating_watch` so all four endgame routes gain another concrete recovery-or-penalty branch
- Added watch-stage channel events `reseller_service_oversight_watch`, `integration_cutover_oversight_watch`, and `marketplace_refund_oversight_watch` so reseller, integration, and marketplace pressure keeps diverging under deeper commercial strain
- Expanded planner recommendations, action sequencing, dashboard surfacing, CLI wiring, and event handlers so the new watch-stage controls only surface once account heat, path fragility, and channel strain are materially present
- Added regression coverage for the new actions and event handlers plus seeded long-run stability checks across IPO, acquisition, independence, and board-reset campaign starts
- Promoted the package version to `0.78.0`

## 0.77.0 - 2026-05-24

- Added `run_enterprise_lane_mesh`, `run_billing_lane_mesh`, `run_onboarding_lane_mesh`, `run_white_glove_lane_mesh`, and `set_path_cash_waterfall` so late-game recovery stops being another naming tier and becomes a broader account/lane and path-control loop
- Added ledger-stage path follow-up events `ipo_book_anchor_ledger`, `buyer_close_anchor_ledger`, `independence_cash_solvency_ledger`, and `board_reset_operating_ledger` so all four endgame routes gain one more concrete recovery-or-penalty branch
- Added ledger-stage channel follow-up events `reseller_service_oversight_ledger`, `integration_cutover_oversight_ledger`, and `marketplace_refund_oversight_ledger` so reseller, integration, and marketplace pressure keeps diverging under deeper commercial strain
- Expanded planner recommendations, action sequencing, dashboard surfacing, CLI wiring, and event handlers so the new lane meshes and path cash waterfall only surface once queue hotspots, dependency pressure, and path fragility are materially present
- Added regression coverage for the new actions and event handlers plus a seeded 720-turn board-recovery stability run
- Promoted the package version to `0.77.0`

## 0.76.0 - 2026-05-24

- Added `run_enterprise_reference_council`, `run_billing_liquidity_council`, `run_onboarding_continuity_council`, `run_channel_durability_council`, and `set_terminal_solvency_council` as one-more-turn controls above the current oversight tier
- Added path-chain follow-up events `ipo_book_anchor_council`, `buyer_close_anchor_council`, `independence_cash_solvency_council`, and `board_reset_operating_council` so all four late-game routes gain another concrete recovery-or-penalty branch
- Added channel-chain follow-up events `reseller_service_oversight_council`, `integration_cutover_oversight_council`, and `marketplace_refund_oversight_council` so reseller, integration, and marketplace lanes keep diverging under deeper terminal commercial pressure
- Expanded planner recommendations, action sequencing, dashboard surfacing, and CLI wiring so the new actions appear only once flagship proof, billing liquidity, onboarding drag, hotspot dependency, and terminal fragility move past the current oversight tier
- Added regression coverage for the new actions and event handlers plus a seeded 660-turn board-recovery stability run
- Promoted the package version to `0.76.0`

## 0.75.0 - 2026-05-24

- Added `run_enterprise_reference_oversight`, `run_billing_liquidity_oversight`, `run_onboarding_continuity_oversight`, `run_channel_durability_oversight`, and `set_terminal_solvency_oversight` as one-more-turn controls above the current commission tier
- Added path-chain follow-up events `ipo_book_anchor_oversight`, `buyer_close_anchor_oversight`, `independence_cash_solvency_oversight`, and `board_reset_operating_oversight` so all four late-game routes gain another concrete recovery-or-penalty branch
- Added channel-chain follow-up events `reseller_service_oversight`, `integration_cutover_oversight`, and `marketplace_refund_oversight` so reseller, integration, and marketplace lanes keep diverging under deeper terminal commercial pressure
- Expanded planner recommendations, action sequencing, dashboard surfacing, and CLI wiring so the new actions appear only once flagship proof, billing liquidity, onboarding drag, hotspot dependency, and terminal fragility move past the current commission tier
- Added regression coverage for the new actions and event handlers plus a seeded 620-turn board-recovery stability run
- Promoted the package version to `0.75.0`

## 0.74.0 - 2026-05-23

- Added `run_enterprise_reference_commission`, `run_billing_liquidity_commission`, `run_onboarding_continuity_commission`, `run_channel_durability_commission`, and `set_terminal_solvency_commission` as one-more-turn commission controls above the current authority and mandate tier
- Added path-chain follow-up events `ipo_book_anchor_commission`, `buyer_close_anchor_commission`, `independence_cash_solvency_commission`, and `board_reset_operating_commission` so all four late-game routes gain another concrete recovery-or-penalty branch
- Added channel-chain follow-up events `reseller_service_commission`, `integration_cutover_commission`, and `marketplace_refund_commission` so reseller, integration, and marketplace lanes keep diverging under deeper terminal commercial pressure
- Expanded planner recommendations, action sequencing, dashboard surfacing, and CLI wiring so the new actions appear only once flagship proof, billing liquidity, onboarding drag, hotspot dependency, and terminal fragility move past the current mandate tier
- Added regression coverage for the new actions and event handlers plus a seeded 580-turn board-recovery stability run
- Promoted the package version to `0.74.0`

## 0.73.0 - 2026-05-23

- Added `run_enterprise_reference_authority`, `run_billing_liquidity_authority`, `run_onboarding_continuity_authority`, `run_channel_durability_mandate`, and `set_terminal_solvency_mandate` as one-more-turn authority and mandate controls above the current secretariat and statute tier
- Added path-chain follow-up events `ipo_book_anchor_mandate`, `buyer_close_anchor_mandate`, `independence_cash_solvency_mandate`, and `board_reset_operating_mandate` so all four late-game routes gain another concrete recovery-or-penalty branch
- Added channel-chain follow-up events `reseller_service_mandate`, `integration_cutover_mandate`, and `marketplace_refund_mandate` so reseller, integration, and marketplace lanes keep diverging under deeper terminal commercial pressure
- Expanded planner recommendations, action sequencing, dashboard surfacing, and CLI wiring so the new actions appear only once flagship proof, billing liquidity, onboarding drag, hotspot dependency, and terminal fragility move past the current statute tier
- Added regression coverage for the new actions and event handlers plus a seeded 540-turn board-recovery stability run
- Promoted the package version to `0.73.0`

## 0.72.0 - 2026-05-22

- Added `run_enterprise_reference_secretariat`, `run_billing_liquidity_secretariat`, `run_onboarding_continuity_secretariat`, `run_channel_durability_statute`, and `set_terminal_solvency_statute` as one-more-turn terminal controls above the current directorate/covenant/resilience tier
- Added path-chain follow-up events `ipo_book_anchor_statute`, `buyer_close_anchor_statute`, `independence_cash_solvency_statute`, and `board_reset_operating_statute` so all four late-game routes gain another concrete recovery-or-penalty branch
- Added channel-chain follow-up events `reseller_service_statute`, `integration_cutover_statute`, and `marketplace_refund_statute` so reseller, integration, and marketplace lanes keep diverging under deeper terminal commercial pressure
- Expanded planner recommendations, action sequencing, dashboard surfacing, and CLI wiring so the new actions appear only once flagship proof, billing liquidity, onboarding drag, hotspot dependency, and terminal fragility move past the current covenant tier
- Added regression coverage for the new actions and event handlers plus a seeded 500-turn board-recovery stability run
- Promoted the package version to `0.72.0`

## 0.71.0 - 2026-05-22

- Added `run_enterprise_reference_directorate`, `run_billing_liquidity_directorate`, `run_onboarding_continuity_bureau`, `run_channel_assurance_covenant`, and `set_terminal_resilience_covenant` as one-more-turn convergence controls above the current summit/lattice/continuity tier
- Added path-chain follow-up events `ipo_book_integrity_covenant`, `buyer_close_integrity_covenant`, `independence_cash_backstop_covenant`, and `board_reset_execution_compact` so all four late-game routes gain another concrete recovery-or-penalty branch
- Added channel-chain follow-up events `reseller_service_backstop`, `integration_cutover_backstop`, and `marketplace_refund_covenant` so reseller, integration, and marketplace lanes keep diverging under deeper late-game commercial pressure
- Expanded planner recommendations, action sequencing, dashboard surfacing, and CLI wiring so the new actions appear only once flagship proof, billing liquidity, onboarding drag, hotspot dependency, and terminal fragility move past the current continuity tier
- Added regression coverage for the new actions and event handlers plus a seeded 460-turn board-recovery stability run
- Promoted the package version to `0.71.0`

## 0.70.0 - 2026-05-22

- Added `run_enterprise_reference_summit`, `run_billing_liquidity_summit`, `run_onboarding_continuity_lattice`, `run_channel_continuity_matrix`, and `set_terminal_continuity_matrix` as one-more-turn late-game control loops above the existing lattice/grid/command tier
- Added path-chain follow-up events `ipo_book_support_panel`, `buyer_close_assurance_panel`, `independence_cash_surety_charter`, and `board_reset_continuity_covenant` so each late-game route gains another concrete recovery-or-penalty branch
- Added channel-chain follow-up events `reseller_service_surety`, `integration_cutover_surety`, and `marketplace_refund_lattice` so reseller, integration, and marketplace lanes keep diverging under deeper commercial pressure
- Expanded planner recommendations, action sequencing, dashboard surfacing, and CLI wiring so the new control loops only appear once flagship proof, billing liquidity, onboarding drag, hotspot dependency, and terminal fragility move past the previous lattice tier
- Added regression coverage for the new actions and event handlers plus a seeded 420-turn board-recovery stability run
- Promoted the package version to `0.70.0`

## 0.69.0 - 2026-05-21

- Added `run_enterprise_reference_lattice`, `run_billing_liquidity_command`, `run_onboarding_durability_mesh`, `run_channel_resilience_grid`, and `set_terminal_recovery_lattice` as deeper terminal follow-up loops for flagship proof, billing/covenant containment, onboarding durability, hotspot-channel stabilization, and path-level capital recovery
- Added path-chain follow-up events `ipo_price_band_committee`, `buyer_close_warranty`, `independence_cash_conversion_charter`, and `board_reset_execution_lattice` so IPO, acquisition, independence, and board-reset routes each gain another concrete late-game recovery-or-penalty branch
- Added channel-chain follow-up events `reseller_service_escrow`, `integration_cutover_warranty`, and `marketplace_refund_backstop` so reseller, integration, and marketplace runs continue diverging under deeper commercial pressure
- Expanded finance-planner recommendations and action sequencing to surface the new terminal recovery actions once flagship queue heat, collections strain, onboarding drag, hotspot dependency, and path fragility converge
- Added regression coverage for the new actions and event handlers plus a seeded 400-turn board-recovery stability run
- Promoted the package version to `0.69.0`

## 0.68.0 - 2026-05-21

- Added `run_white_glove_reference_exchange`, `run_billing_cash_war_room`, `run_onboarding_assurance_grid`, `run_channel_conflict_lattice`, and `set_balance_sheet_recovery_mesh` as deeper late-game control loops for flagship proof, billing/covenant recovery, onboarding assurance, hotspot channel conflict reset, and balance-sheet defense
- Added path-chain follow-up events `ipo_price_support_commitment`, `buyer_close_certainty_grid`, `independence_cash_discipline_statute`, and `board_reset_recovery_ordinance` so each primary exit route gains another concrete recovery-or-penalty branch
- Added channel-chain follow-up events `reseller_service_dividend`, `integration_reliability_warranty`, and `marketplace_refund_surety` so reseller, integration, and marketplace runs continue diverging under deeper late-game commercial pressure
- Expanded finance-planner recommendations and action sequencing to surface the new premium, billing, onboarding, channel, and balance-sheet controls when flagship queue heat, collections stress, onboarding drag, hotspot dependency, and terminal fragility converge
- Added regression coverage for the new actions and event handlers plus a seeded 380-turn board-recovery stability run
- Promoted the package version to `0.68.0`

## 0.67.0 - 2026-05-21

- Added `run_enterprise_reference_forum`, `run_billing_settlement_board`, `run_onboarding_retention_mesh`, `run_channel_durability_mesh`, and `set_path_resilience_grid` as deeper late-game follow-up controls for flagship references, collections recovery, onboarding retention, hotspot channel stabilization, and path-specific capital defense
- Added path-chain follow-up events `ipo_demand_floor`, `buyer_synergy_holdback`, `independence_cash_conversion_pact`, and `board_reset_resilience_statute` so the four main endgame routes gain another concrete recovery-or-penalty branch
- Added channel-chain follow-up events `reseller_margin_reconciliation`, `integration_reliability_bridge`, and `marketplace_dispute_escrow` so reseller, integration, and marketplace runs continue diverging under late-game commercial pressure
- Expanded finance-planner recommendations and action sequencing to surface the new support, channel, and capital-control actions when flagship queue heat, collections drag, onboarding overflow, hotspot dependency, and path-specific fragility converge
- Added regression coverage for the new actions and event handlers plus a seeded 360-turn board-recovery stability run
- Promoted the package version to `0.67.0`

## 0.66.0 - 2026-05-20

- Added `run_enterprise_commitment_board`, `run_billing_collection_bridge`, `run_onboarding_adoption_hub`, `run_channel_dependency_reset`, and `set_capital_reallocation_grid` as deeper late-game follow-up actions for flagship account rescue, billing collections cleanup, onboarding stabilization, channel dependency relief, and path-aware capital control
- Added path-chain follow-up events `ipo_order_book_covenant`, `buyer_close_signoff`, `independence_reserve_compact`, and `board_reset_operating_charter` so each late-game route gains another concrete recovery-or-penalty branch
- Added channel-specific follow-up events `reseller_service_charter`, `integration_hypercare_board`, and `marketplace_refund_appeal` so reseller, integration, and marketplace runs continue diverging under late-game commercial pressure
- Expanded finance-planner recommendations and action sequencing to surface the new support, channel, and capital-control actions when enterprise renewal heat, billing drag, onboarding fragility, hotspot dependency, and route-specific pressure converge
- Added regression coverage for the new actions and event handlers plus a seeded 340-turn board-recovery stability run
- Promoted the package version to `0.66.0`

## 0.65.0 - 2026-05-20

- Added `run_white_glove_reference_bureau`, `run_billing_dispute_cabinet`, `run_onboarding_launch_cell`, and `set_terminal_liquidity_controls` as deeper late-game follow-up actions for flagship support rescue, billing/covenant cleanup, onboarding recovery, and path-aware liquidity control
- Added path-chain follow-up events `ipo_pricing_guardrail`, `buyer_close_committee`, `independence_liquidity_grid`, and `board_reset_runway_table` so each late-game route gains another concrete recovery-or-penalty branch
- Added channel-specific follow-up events `reseller_service_council`, `integration_hypercare_grid`, and `marketplace_refund_bench` so reseller, integration, and marketplace runs continue diverging under late-game pressure
- Expanded finance-planner recommendations and action sequencing to surface the new follow-up rescues and terminal-liquidity control when premium queue heat, billing pressure, onboarding drag, or route-specific fragility spikes
- Added regression coverage for the new actions and event handlers plus a seeded 320-turn board-recovery stability run
- Promoted the package version to `0.65.0`

## 0.64.0 - 2026-05-19

- Added `run_white_glove_escalation_cell`, `run_billing_dispute_desk`, `run_onboarding_control_tower`, and `set_exit_readiness_buffer` as deeper account-level rescue and path-control actions for premium support hotspots, billing/covenant stress, onboarding drag, and exit-readiness capital posture
- Added path-chain follow-up events `ipo_allocation_lock`, `buyer_close_cadence`, `independence_margin_charter`, and `board_reset_cash_charter` so each late-game route gains another concrete recovery-or-penalty branch
- Added channel-specific follow-up events `reseller_recovery_compact`, `integration_cutover_command`, and `marketplace_penalty_panel` so reseller, integration, and marketplace runs continue diverging under late-game pressure
- Expanded finance-planner recommendations and action sequencing to surface the new support rescues and exit-readiness capital move when premium queue heat, billing pressure, onboarding drag, or route-specific fragility spikes
- Added regression coverage for the new actions and event handlers plus a seeded 300-turn board-recovery stability run
- Promoted the package version to `0.64.0`

## 0.63.0 - 2026-05-19

- Added `run_white_glove_reference_committee`, `run_billing_covenant_reset`, and `set_endgame_capital_map` as deeper late-game follow-up actions for flagship support rescue, billing/covenant cleanup, and path-aware capital control
- Added path-specific follow-up events `ipo_bookbuild_corridor`, `buyer_board_alignment`, `independence_liquidity_charter`, and `board_reset_trust_vote` so IPO, acquisition, independence, and board-reset runs each gain another distinct late-game branch
- Added channel-specific follow-up events `reseller_pipeline_cadence`, `integration_go_live_shield`, and `marketplace_policy_appeal` so reseller, integration, and marketplace lanes continue diverging under late-game pressure
- Expanded finance-planner and endgame guidance to recommend the new support and capital actions once premium queue strain, billing heat, governance stress, and hotspot channel dependency start converging
- Added regression coverage for the new actions and event handlers plus a seeded 280-turn board-recovery stability run
- Promoted the package version to `0.63.0`

## 0.62.0 - 2026-05-18

- Added `run_white_glove_reference_ring` and `set_path_capital_posture` as deeper late-game follow-up actions for flagship premium-account recovery and route-aware capital control
- Added path-specific follow-up events `ipo_roadshow_lock`, `buyer_close_readiness`, `independence_cash_command`, and `board_reset_balance_sheet_treaty` so IPO, acquisition, independence, and board-reset runs each gain another distinct late-game branch
- Added channel-specific events `reseller_margin_council`, `integration_support_bridge`, and `marketplace_trust_reset` so reseller, integration, and marketplace lanes now create different late-game commercial failures and recoveries
- Expanded finance-planner and endgame guidance to recommend the new support and capital actions once white-glove queue drag, hotspot dependency, governance heat, and reserve fragility start converging
- Added regression coverage for the new actions and event chains plus a seeded 260-turn board-recovery stability run
- Promoted the package version to `0.62.0`

## 0.61.0 - 2026-05-15

- Added `run_enterprise_renewal_cabinet` and `set_growth_firebreak` as deeper late-game follow-up actions for flagship enterprise renewal repair and growth-to-resilience capital discipline
- Added follow-up events `reseller_commitment_review`, `integration_release_cutline`, `marketplace_refund_charter`, and `board_reset_governance_table` so reseller, integration, marketplace, and board-reset runs each gain another late-game decision layer
- Expanded finance-planner and endgame guidance to recommend the new enterprise-renewal and growth-firebreak actions once queue drag, board heat, governance risk, and capital fragility start converging
- Added regression coverage for the new actions and event handlers plus a seeded 240-turn board-recovery stability run
- Promoted the package version to `0.61.0`

## 0.60.0 - 2026-05-15

- Added `run_white_glove_renewal_guard`, `run_integration_cutover_reset`, and `set_debt_strategy` as deeper late-game follow-up actions for premium renewals, integration-channel cutovers, and debt-aware capital discipline
- Added follow-up events `reseller_reference_summit`, `integration_cutover_board`, `marketplace_dispute_program`, and `board_reset_operating_cadence` so reseller, integration, marketplace, and board-reset paths each gain another late-game branch
- Expanded finance-planner guidance to recommend the new support, channel, and debt actions once premium renewal stress, integration hotspot drag, and covenant heat become the main bottlenecks
- Added regression coverage for the new actions and event handlers plus a seeded 220-turn board-recovery stability run
- Promoted the package version to `0.60.0`

## 0.59.0 - 2026-05-14

- Added `run_white_glove_backstop`, `run_reseller_enablement_reset`, `run_marketplace_chargeback_reset`, and `set_covenant_firewall` as deeper late-game follow-up actions for flagship support rescue, reseller recovery, marketplace billing cleanup, and covenant defense
- Added path-specific follow-up events `ipo_reference_committee`, `buyer_signing_committee`, `independence_treasury_compact`, and `board_reset_execution_plan` so IPO, acquisition, independence, and board-reset runs each gain another decisive late-game branch
- Expanded finance-planner guidance to recommend the new support, channel, and covenant actions once premium queue drag, reseller or marketplace hotspot pressure, and covenant heat become the main bottlenecks
- Added regression coverage for the new actions and event chains plus a seeded 200-turn board-recovery stability run
- Promoted the package version to `0.59.0`

## 0.58.0 - 2026-05-14

- Added `run_enterprise_reference_cycle`, `run_billing_retention_reset`, `run_channel_stability_reset`, and `set_refinancing_posture` as deeper late-game follow-up actions for flagship support recovery, billing retention, hotspot channel durability, and debt-aware capital control
- Added path-specific follow-up events `ipo_pricing_committee`, `buyer_operating_memo`, and `independence_cash_yield_pact` so IPO, acquisition, and independence runs diverge more clearly after the previous late-game chain
- Added channel-specific event pressure through `reseller_enablement_gap`, `integration_cutover_risk`, and `marketplace_chargeback_wave` so reseller, integration, and marketplace lanes no longer fail in the same way
- Expanded finance-planner guidance to recommend the new support, channel, and refinancing actions when flagship queue risk, billing retention drag, hotspot dependency, and covenant heat become the main bottlenecks
- Added regression coverage for the new actions and event chains plus a seeded 190-turn channel-rebuild stability run
- Promoted the package version to `0.58.0`

## 0.57.0 - 2026-05-14

- Added `run_white_glove_recovery`, `run_partner_margin_reset`, and `lock_capital_buffer` as deeper late-game rescue actions for premium accounts, acquisition-channel economics, and independence durability
- Added path-specific follow-up events `ipo_syndicate_commitment`, `buyer_integration_blueprint`, and `independence_buffer_ratchet` so IPO, acquisition, and independence runs diverge further under late-game operating pressure
- Expanded finance-planner and endgame guidance to recommend the new actions when premium queue drag, channel hotspot economics, and capital fragility become the main path bottlenecks
- Added regression coverage for the new actions and event chains plus a seeded 170-turn board-recovery stability run
- Promoted the package version to `0.57.0`

## 0.56.0 - 2026-05-14

- Added `run_enterprise_queue_reset`, `run_channel_synergy_reset`, and `harden_financing_posture` as deeper late-game follow-up actions for enterprise queue hotspots, partner dependency cleanup, and capital resilience
- Added path-specific follow-up events `ipo_governance_lockstep`, `buyer_synergy_map`, and `independence_operating_covenant` so IPO, acquisition, and independence runs diverge further after the new late-game window events
- Expanded finance-planner and endgame guidance to recommend the new actions when enterprise queue drag, channel overlap, and financing fragility become the main path bottlenecks
- Added regression coverage for the new actions and event chains plus a seeded 180-turn IPO-launchpad stability run
- Promoted the package version to `0.56.0`

## 0.55.0 - 2026-05-14

- Added `run_onboarding_fast_track`, `run_channel_realignment`, and `step_up_reserve_discipline` as deeper late-game follow-up actions for hotspot accounts, channel mix, and independence capital control
- Added path-specific follow-up events `ipo_listing_window`, `buyer_term_sheet`, and `independence_profit_floor` so IPO, acquisition, and independence runs diverge more sharply late in the chain
- Expanded finance-planner and endgame guidance to recommend the new follow-up actions when onboarding drag, channel dependence, and reserve fragility become the main path bottlenecks
- Added regression coverage for the new actions and event chains plus a seeded 160-turn acquisition-diligence stability run
- Promoted the package version to `0.55.0`

## 0.54.0 - 2026-05-14

- Added `run_reference_rescue` and `run_channel_conflict_reset` as deeper late-game recovery actions for flagship accounts and noisy channel relationships
- Added path-specific follow-up events `ipo_reference_crack`, `buyer_channel_conflict_review`, and `independence_refinancing_wall` so IPO, acquisition, and independence runs branch more sharply under stress
- Expanded finance-planner and endgame guidance to recommend the new recovery actions when enterprise references, channel conflict, and refinancing strain become the dominant late-game bottlenecks
- Added regression coverage for the new actions and event chains plus a seeded 150-turn IPO-launchpad stability run
- Promoted the package version to `0.54.0`

## 0.53.0 - 2026-05-13

- Added `run_onboarding_recovery` and `run_channel_firebreak` as deeper late-game recovery actions for support and channel hotspots
- Added path-depth events `board_reset_showdown` and `channel_concentration_crackdown` for governance-reset and channel-fragility chains
- Expanded planner and endgame guidance to react to onboarding hotspots, channel firebreaks, and board-reset escalation
- Added regression coverage for the new actions/events plus a seeded 140-turn board-recovery stability run
- Promoted the package version to `0.53.0`

## 0.52.0 - 2026-05-13

- Added two new late-game operating actions: `run_billing_stabilization` to cool renewal-heavy billing hotspots and `run_partner_recovery_sprint` to rescue one strained or recovering channel before dependence hardens
- Added three path-specific late-game follow-up events: `ipo_audit_committee`, `buyer_reference_check`, and `independence_cash_crunch`, so IPO, acquisition, and independence runs now branch more distinctly after the first major pressure spike
- Deepened finance-planner guidance, event gating, and endgame watchlists around billing stability, partner recovery, and path-specific operating pressure
- Expanded regression coverage with targeted action and event tests plus a seeded 130-turn independence-compounder stability run
- Promoted the package version to `0.52.0`

## 0.51.0 - 2026-05-13

- Added two new late-game state-changing actions: `run_enterprise_assurance` to harden enterprise-support accounts ahead of IPO-style scrutiny, and `rebalance_channel_mix` to deconcentrate hotspot partner revenue before channel dependence distorts execution
- Deepened finance-planner guidance with explicit recommendations and sequencing around enterprise assurance and channel-mix rebalancing once queue hotspots, channel concentration, or paused dependency start shaping capital quality
- Tightened endgame and event pressure so IPO runs react more sharply to enterprise queue-risk cohorts, acquisition paths react more clearly to direct-sales and hotspot-channel dependence, and independence paths now surface rollover-style debt strain more coherently
- Expanded regression coverage with dedicated action tests for enterprise assurance and channel-mix rebalancing plus an additional seeded 120-turn IPO-launchpad stability run
- Promoted the package version to `0.51.0`

## 0.50.0 - 2026-05-13

- Added three new state-changing actions: `run_renewal_sweep`, `run_channel_qbr`, and `debt_rollover`, so late-game runs can now stabilize renewal cohorts, calm hotspot channels, and manage covenant pressure without relying only on passive planner advice
- Deepened finance-planner guidance with explicit recommendations and action sequencing around renewal sweeps, channel QBRs, and debt rollovers when support, channel concentration, and covenant pressure start interacting
- Tightened endgame and event pressure so acquisition runs react more sharply to direct-sales conflict and paused-channel dependency, independence runs react more sharply to rollover-style debt stress, and support meltdowns can now surface from renewal-heavy queue pressure
- Expanded regression coverage with new action tests for renewal sweeps, channel QBRs, and debt rollovers plus an additional seeded 110-turn channel-rebuild stability run
- Promoted the package version to `0.50.0`

## 0.49.0 - 2026-05-12

- Added `run_lane_recovery`, `pause_partnership`, and `raise_reserve_target` as real state-changing actions so late-game runs can now target support hotspots, intentionally cool noisy channels, and harden reserve discipline directly from the turn menu
- Deepened path-aware endgame pressure so IPO scrutiny now punishes enterprise support-focus mismatch harder, M&A diligence reacts more strongly to paused-channel dependency, and independence discipline now reflects underweight reserve allocation
- Tightened endgame and event gating around public-market scrutiny, acquirer diligence, independence reckoning, and partner breakdowns so late-game chains reflect the new support, channel, and capital signals more coherently
- Expanded regression coverage with dedicated action tests for lane recovery, partnership pause, and reserve-target raises plus new path-pressure assertions for paused-channel diligence and low-reserve independence stress
- Promoted the package version to `0.49.0`

## 0.48.0 - 2026-05-07

- Added targeted recovery actions through `run_account_rescue`, letting the player spend directly on one revenue-critical account to cut queue, billing, renewal, and churn pressure in a single move
- Added `rebalance_capital` as a real planning action that automatically retunes reserve, product, and GTM allocation around reserve stress, support hotspots, channel concentration, and the active board ask
- Strengthened the finance planner so it now recommends account rescues and capital rebalances when support exposure, renewal pressure, queue hotspots, or partner dependency start distorting late-game execution
- Extended regression coverage with dedicated action tests for account rescue and capital rebalance plus a seeded 100-turn board-recovery stability run
- Promoted the package version to `0.48.0`

## 0.47.0 - 2026-05-07

- Deepened support-lane realism by turning hotspot lane focus into a stronger immediate action, with targeted relief when the company shifts into the live enterprise, billing, or onboarding bottleneck
- Expanded partnership analytics with hotspot dependency scoring and hotspot status notes so recovering or concentrated channels now surface more clearly in planning, endgame pressure, and reporting
- Strengthened the finance planner with lane-focus and dependency-hotspot guidance plus more path-aware recommendations around support-lane focus, partnership recovery, and channel review
- Tightened endgame and commercial pressure so IPO, acquisition, and independence runs react more sharply to support-focus mismatch and hotspot channel dependency
- Added new regression coverage for support-focus relief, hotspot dependency-driven partner breakdowns, endgame mismatch pressure, and a seeded 100-turn independence-compounder stability run
- Promoted the package version to `0.47.0`

## 0.46.0 - 2026-05-07

- Deepened late-game path pressure again so IPO, acquisition, and independence runs react more sharply to enterprise queue hotspots, billing renewal stress, and concentrated partner revenue
- Expanded finance-planner guidance with explicit queue-hotspot and channel-hotspot notes plus stronger action sequencing around lane overflow and channel dependence
- Tightened event gating for public-market scrutiny, acquirer diligence, independence reckoning, support meltdowns, and partner breakdowns so they trigger from more realistic support or channel pressure
- Added new regression coverage for hotspot-triggered events, 100-turn acquisition-late-game stability, and save-load continuation under path-specific late-game pressure
- Promoted the package version to `0.46.0`

## 0.45.0 - 2026-05-07

- Deepened late-game branch pressure by letting IPO, acquisition, and independence outlooks amplify commercial stress differently once support or channel signals slip
- Expanded support-ops realism with enterprise and renewal queue-risk account counts plus hotspot-lane tracking that now feeds planning and board pressure
- Strengthened the finance planner with path-pressure bias, capital rebalance guidance, and clearer action recommendations tied to endgame posture
- Added new regression coverage for path-specific commercial pressure and a seeded 90-turn IPO-launchpad stability run
- Promoted the package version to `0.45.0`

## 0.44.0 - 2026-05-07

- Deepened support-ops realism with enterprise queue exposure, renewal queue exposure, white-glove queue-risk counts, and lane saturation signals that now feed finance, governance, and late-game pressure
- Expanded partnership analytics with recovery drag, paused dependency, and hotspot revenue share so channel fragility now reflects recovering or concentrated partner revenue more clearly
- Strengthened the finance planner with support-lane and channel-recovery guidance plus more concrete recommended actions around lane focus, channel review, and recovery sequencing
- Tightened late-game pressure scoring so support saturation and channel recovery drag shape path pressure, commercial fragility, and operating durability more directly
- Added long-run and persistence hardening through seeded 80-turn progression coverage and a save-load continuation regression under commercial pressure
- Fixed runway estimation under severe burn so forecast persistence no longer tries to write invalid negative runway turns
- Promoted the package version to `0.44.0`

## 0.43.0 - 2026-05-07

- Deepened endgame pressure with operating-durability scoring, path watchlists, and more path-aware late-game event eligibility so IPO, acquisition, and independence pressure trigger more distinctly
- Expanded support-ops realism with premium queue exposure, account-level queue-risk scoring, and stronger triage or escalation recovery effects on satisfaction, renewal health, and churn risk
- Extended partnership analytics with strained revenue share and channel-volatility indexing so recovery-stage and fatigue-heavy channels contribute clearer commercial pressure
- Strengthened finance-planner guidance with funding resilience, capital-discipline indexing, and more specific action recommendations around support routing, retention work, and partnership reactivation
- Improved terminal reporting so victory, scorecard, finance, support, partnership, and late-game panels now surface the new durability, watchlist, volatility, and commercial-risk signals directly
- Promoted the package version to `0.43.0`

## 0.42.0 - 2026-05-07

- Deepened support-ops pressure with premium queue exposure, account-level queue-risk scoring, stronger triage recovery effects, and richer commercial fallout when high-touch service quality slips
- Expanded partnership and channel analytics with strained revenue share, channel-volatility indexing, and heavier lane pressure from fatigued or recovery-stage channels
- Strengthened finance-planner guidance with funding-resilience framing, capital-discipline indexing, and more concrete recommended actions around escalation routing, retention work, and partnership reactivation
- Extended late-game evaluation with operating durability, path watchlists, and additional ending variants such as `Synergy Premium Acquisition` and `Trust-Backed Compounder`
- Increased hardening coverage with deeper regression assertions across support, finance, partnership, and endgame metrics plus a seeded sixty-turn late-game stability check
- Promoted the package version to `0.42.0`

## 0.41.0 - 2026-05-07

- Deepened support-ops realism with high-value account risk tracking, recovery-ready account detection, SLA credit operating cost, and a recovery loop that can claw back satisfaction and renewal health when support operations stabilize
- Expanded partnership and channel analytics with volatile revenue-share exposure, fatigue hotspot tracking, commercial dependency scoring, and stronger fatigue or recovery effects on partner-sourced user growth
- Strengthened finance-planner guidance with commercial financing risk, capital-priority framing, and recommended recovery actions that now react to revenue-at-risk, renewal pressure, and channel volatility
- Extended late-game pressure and exit evaluation with commercial fragility, capital fragility, strategic clarity, path-gap analysis, and new ending variants such as `Institutional Quality Listing`, `Capital-Disciplined Compounder`, and `Liquidity Containment Reset`
- Tightened event and persistence hardening by making independence-reckoning capital-plan updates atomic and syncing post-turn event outcomes back into the latest turn-history snapshot
- Promoted the package version to `0.41.0`

## 0.40.0 - 2026-05-06

- Deepened org and people pressure so unmanaged teams, overloaded managers, and succession blind spots now feed attrition, morale, and performance drift during turn resolution
- Extended employee progression with promotion leadership gains, manager compensation reviews that reduce succession risk, and succession reviews that materially prepare backup leads
- Linked organization strain back into governance so board team-health now reacts to org drag and succession gaps instead of treating people pressure as a side metric
- Improved the team dashboard and turn narrative with clearer org-risk messaging around management overload, span pressure, and succession exposure
- Expanded regression coverage across promotion, compensation, succession, unmanaged-team pressure, and org-drag effects on turn outcomes
- Promoted the package version to `0.40.0`

## 0.39.0 - 2026-05-06

- Deepened endgame classification with path scorecards, stronger support/channel fragility weighting, and new outcome variants such as `Customer-Trust Listing`, `Distribution-Led Acquisition`, `Service-Led Compounder`, and `Commercial Containment Reset`
- Expanded support-ops pressure with severe high-touch queue tracking, white-glove revenue-at-risk exposure, and stronger commercial fallout when premium service promises slip
- Extended partnership analytics with hotspot-channel detection, rev-share pressure tracking, and more realistic channel economics drift under fatigue and recovery
- Strengthened finance-planner output with liquidity-risk language, execution-drag cues, and prioritized action sequences that now react to support and channel strain
- Tightened event eligibility and regression coverage around support meltdowns, partner breakdowns, late-game scorecards, planner signals, and long-run seeded stability
- Promoted the package version to `0.39.0`

## 0.38.0 - 2026-05-06

- Deepened late-game pressure scoring with explicit `support_fragility`, `channel_fragility`, and `board_reset_risk` signals that now feed exit evaluation, board recommendations, and ending variants
- Expanded support-ops realism with premium-tier breach penalties, enterprise and premium revenue-at-risk valuation, and commercial-breach pressure that now pushes governance and board confidence directly
- Extended partnership and channel analysis with fatigued/recovery revenue share, concentration risk, renegotiation pressure, and higher decay for neglected high-fatigue channels
- Strengthened finance-planner guidance with reserve-recovery timing, capital-action windows, and trade-off notes so late-stage cash planning is easier to interpret during long runs
- Tightened event eligibility and hardening coverage around support meltdowns, partner breakdowns, board resets, extended late-game progression, and save/load persistence under multi-turn stress
- Promoted the package version to `0.38.0`

## 0.37.0 - 2026-05-06

- Added three archive-gated late-game campaign starts, `IPO Readiness Launchpad`, `Acquisition Diligence Sprint`, and `Independence Compounder`, so repeat runs can now begin from distinct public-market, M&A, and disciplined-bootstrap operating profiles
- Deepened progression logic with campaign-start reward unlocks, a higher `institution_builder` ladder stage, and richer archive comparison output around restructure leaders and path-balance guidance
- Strengthened commercial realism by valuing support exposure directly, escalating direct-sales channel conflict, and surfacing revenue-at-risk plus renewal-pressure money in end-of-turn governance pressure
- Expanded finance and partnership reporting with reserve-plan guidance, debt-rollover signals, funding-window cues, allocation actions, direct-conflict counts, and weighted rev-share visibility
- Extended terminal presentation and regression coverage for the new campaign starts, unlock rules, archive comparison notes, finance-planner diagnostics, and partnership conflict reporting
- Promoted the package version to `0.37.0`

## 0.36.0 - 2026-05-06

- Added archive-gated `campaign start` modifiers plus a new `list-campaign-starts` CLI catalog so repeat runs can begin from distinct commercial and governance pressure profiles instead of always replaying turn-one openings
- Wired campaign-start selection into `new-game`, the default root command, and the hidden `play` alias, including clean locked-content validation and intro-banner visibility for the chosen start profile
- Deepened end-of-turn operating realism with a dedicated commercial-pressure layer that translates support risk, renewal stress, and channel dependency into board pressure, governance risk, customer risk status, and turn-summary narrative output
- Extended terminal reporting so turn summaries now surface commercial pressure explicitly alongside existing operations, late-game, and scale signals
- Strengthened regression coverage for campaign-start application, campaign-start CLI gating, and end-of-turn commercial-pressure escalation
- Promoted the package version to `0.36.0`

## 0.35.0 - 2026-05-06

- Added `refinance_debt` as a playable finance action so late-stage runs can trade pricier debt for calmer covenant pressure instead of only choosing between new debt and repayment
- Deepened support-ops visibility with revenue-at-risk and renewal-pressure account tracking that now feeds post-sale decision-making and raises the consequence of long queue age or lane mismatch
- Expanded partnership portfolio reporting with dependency risk, paused-revenue share, and renegotiation readiness so channel scale is easier to manage as a commercial system instead of a flat count
- Introduced endgame-pressure modeling across public-market scrutiny, acquirer diligence, independence discipline, and restructure heat, and surfaced those signals directly in the dashboard and victory reporting
- Added three new late-game event paths: `public_market_scrutiny`, `acquirer_diligence`, and `independence_reckoning`, each tied to the new pressure model with explicit trade-offs
- Strengthened regression coverage for refinance flow, support commercial risk counts, partnership dependency reporting, and the new endgame event handlers
- Promoted the package version to `0.35.0`

## 0.34.0 - 2026-05-05

- Turned archive progression into real gameplay gating so locked reward scenarios, product templates, and rival archetypes now surface in terminal catalogs with status markers and stay unavailable until the local archive unlocks them
- Extended new-game validation and product-creation flows so progression-locked content fails cleanly with CLI guidance instead of leaking into playable runs
- Deepened finance planning through custom capital-plan tuning, allowing manual horizon, reserve target, and product versus GTM versus reserve allocation on top of the existing mode and source presets
- Strengthened terminal UX around progression and finance by exposing lock state directly in catalog views and by surfacing richer capital-plan summaries after changes
- Added regression coverage for locked scenario access, unlock-aware catalog rendering, archive reward gating, and custom capital-plan application
- Promoted the package version to `0.34.0`

## 0.33.0 - 2026-05-01

- Deepened finance planning with richer capital-mix diagnostics, funding-posture guidance, dilution outlook, covenant outlook, and clearer multi-scenario planning notes in the dashboard
- Expanded partnership lifecycle depth with an explicit `reactivate_partnership` action plus stronger portfolio-health reporting around neglect, recovery readiness, conflict load, and dominant-channel concentration
- Added playable people-ops depth through `run_comp_review` and `run_succession_review` so compensation pressure and backup leadership can now be managed directly instead of only passively
- Extended archive progression and archive comparison with reward-mix coverage, outcome-coverage progress, badge coverage, path-specific leaders, and clearer next-gap guidance
- Strengthened hardening coverage with a longer extended-play regression, deeper partnership-action tests, and richer finance/meta assertions across the existing deterministic test suite
- Promoted the package version to `0.33.0`

## 0.32.0 - 2026-04-30

- Added a true archive unlock catalog with typed rewards plus a new `list-unlocks` CLI command so progression now exposes exact scenario, template, rival, tool, and insight rewards instead of only hint text
- Deepened exit evaluation with sharper ending variants, outcome tags, richer archive-comparison guidance, and stronger late-game reporting around dominant and missing endgame paths
- Added partner renegotiation as a playable channel action, expanded channel fatigue logic by lane style, and introduced new partner-renegotiation event pressure to make margin-versus-stability trade-offs visible
- Strengthened finance planning with reserve-break risk, capital-allocation signals, and scenario-comparison notes alongside the existing planner posture alerts
- Added new strategic-crossroads event pressure plus new public-market and channel-margin content across scenarios, templates, and rival archetypes
- Expanded regression coverage for unlock catalogs, ending variants, partnership renegotiation, new late-game events, and updated finance-planner diagnostics
- Promoted the package version to `0.32.0`

## 0.31.0 - 2026-04-30

- Added a fuller archive meta layer with achievement rewards, archive comparison, and richer progression guidance so completed runs now feed an actual repeat-play loop instead of only one summary panel
- Deepened partnership scale behavior with derived channel fatigue, a new recovery state, richer portfolio health reporting, and new partner-breakdown event pressure
- Extended late-game event chains with partner-breakdown and board-recovery-window follow-ups plus richer finance-planner guidance around reserve stress and recommended posture
- Expanded the content pack again with new partner-recovery and archive-governance templates, new channel-rebuild and board-recovery scenarios, and new late-scale rival archetypes
- Added regression coverage for archive comparison, progression rewards, recovery-state persistence, and the new governance and partner event handlers
- Promoted the package version to `0.31.0`

## 0.30.0 - 2026-04-30

- Expanded archive-derived progression with a visible campaign ladder, richer archive benchmarks, and clearer next-goal guidance so repeat runs now read more like a structured campaign layer
- Deepened late-game reporting through explicit board readouts, next-chapter guidance, partnership portfolio summaries, and a multi-turn finance planner that surfaces reserve-break risk
- Added long-run hardening coverage for thirty-turn simulation stability, richer exit evaluation reporting, and multi-turn save/load round trips after live gameplay progression
- Expanded the content pack again with new campaign-ladder and reserve-planning templates, new governance and reserve-discipline scenarios, and matching late-scale rival archetypes
- Promoted the package version to `0.30.0`

## 0.29.0 - 2026-04-30

- Expanded archive-derived meta progression with campaign stages, achievement progress, outcome coverage, and archive highlights so late-game history now feels more like a real progression layer
- Added new chained scale-stage events for support meltdowns, board reckonings, partner QBRs, capital-market freezes, and succession gaps to deepen late-game variety without changing the offline scope
- Deepened org simulation through promotion pressure, compensation pressure, underperformance drag, and stronger overload or succession penalties inside team-management drift
- Improved support-ops realism with lane staffing plans, premium-tier service-cost pressure, and clearer lane staffing visibility in the dashboard
- Extended capital-planning diagnostics with reserve state, execution status, alignment scoring, and clearer recommended posture guidance
- Added regression coverage for new event handlers, support staffing behavior, employee career pressure, and richer meta progression summaries
- Promoted the package version to `0.29.0`

## 0.28.0 - 2026-04-30

- Added lane-capacity and lane-overflow modeling for support ops so onboarding, enterprise, and billing pressure now consume differentiated capacity instead of one flat queue
- Deepened board governance with scorecard-driven consequences plus recovery-plan tracks that now shift capital posture, support focus, team health, or roadmap focus based on the active board ask
- Expanded pricing and packaging depth with catalog-aware acquisition/churn modifiers, softer price-increase shock for deeper catalogs, and stronger package-expansion drift across seats, usage, and bundle depth
- Deepened partnerships with neglected-channel decay, multi-channel conflict pressure, enablement-driven rev-share improvement, and capital-plan-aware channel scaling
- Strengthened capital planning and finance forecasting with alignment checks across reserve posture, GTM execution, technical debt load, support backlog, and dilution-sensitive venture planning
- Extended terminal panels and regression coverage for the new support, governance, pricing, partnership, and finance depth
- Promoted the package version to `0.28.0`

## 0.27.0 - 2026-04-29

- Added real reseller, integration, and marketplace partnerships with channel-specific setup cost, enablement depth, sourced users, sourced revenue, support pressure, and conflict risk
- Added capital-planning posture with `conserve`, `balanced`, and `expand` modes plus bootstrap, debt, angel, and venture source preferences that now shape finance drift and reserve discipline
- Added archive-derived meta progression through a new `show-progression` CLI command plus campaign-tier and unlock summaries built from completed run history
- Added partnership and capital-plan persistence in SQLite, plus dedicated terminal review panels for channel state and reserve posture
- Added new scale-stage events for channel conflict, bridge capital, and inbound exit interest, and tied partner-offer events into the partnership system
- Expanded regression coverage for partnership actions, capital-plan actions, archive progression, new event flows, and round-trip persistence
- Promoted the package version to `0.27.0`

## 0.26.0 - 2026-04-29

- Added lane-aware support escalation routing so onboarding, enterprise, and billing pressure now resolve through different relief paths instead of one generic support action
- Deepened package-catalog and add-on-catalog actions so account expansion, package migration, and renewal posture respond more directly to monetization depth
- Added forced governance trade-offs whenever board resolutions or crises are active, pushing the run toward cash discipline, reliability, team recovery, or portfolio focus
- Expanded dashboard visibility with per-account support lanes, support lane mix, and active governance trade-off cues
- Added new archive/reporting flavor through billing, governance, and monetization run badges plus broader regression coverage for the new support, pricing, and governance behavior
- Promoted the package version to `0.26.0`

## 0.25.0 - 2026-04-29

- Added a `billing` support lane plus billing-pressure tracking from invoice risk, failed payments, and dunning so post-sale ops now cover revenue collection pressure too
- Extended support-lane mismatch logic to compare onboarding, enterprise, and billing demand instead of only two queue families
- Added endgame-readiness scoring across IPO readiness, acquisition interest, and profitable independence for clearer late-game strategic reading
- Extended archived run metadata with strategic outlook and modeled offer value so completed runs are easier to compare beyond raw score
- Extended dashboards, reports, victory output, SQLite persistence, and regression coverage for the new support and endgame depth
- Promoted the package version to `0.25.0`

## 0.24.0 - 2026-04-29

- Added a board scorecard across profitability, reliability, team health, and portfolio focus so governance pressure is easier to read and tune
- Added governance-crisis escalation with resolution-miss streaks so ignored board deadlines now compound into stronger late-game pressure
- Added deeper support-lane telemetry through onboarding versus enterprise queue pressure plus mismatch penalties when the lane focus drifts from demand
- Added archive badges such as capital discipline, board trust, and enterprise operation so completed runs are easier to compare as meta history
- Extended SQLite persistence, dashboard panels, and regression coverage for the new governance, support, and archive metadata
- Promoted the package version to `0.24.0`

## 0.23.0 - 2026-04-28

- Added support-lane focus with `balanced`, `onboarding`, and `enterprise` routing so support capacity can be aimed at the current customer mix
- Added typed renewal offers with `light_discount`, `bundle_upgrade`, and `term_extension` outcomes instead of treating every renewal save as the same play
- Added governance follow-through with formal board-resolution deadlines that raise pressure again when the company ignores the board response window
- Added deeper org-structure tracking through management layers, span risk, and cycle-safe reporting assignments
- Extended SQLite persistence and run archives with the new support, governance, customer, and score metadata
- Extended dashboards, CLI prompts, and regression coverage for support lanes, renewal types, board deadlines, and archive summaries
- Promoted the package version to `0.23.0`

## 0.22.0 - 2026-04-28

- Added board-recovery plans with recovery focus, board score tracking, and multi-turn governance stabilization pressure
- Added support-staffing investment plus explicit per-turn support service cost so post-sale scale creates clearer cash drag
- Added package-catalog and add-on-catalog expansion actions that deepen monetization without replacing existing pricing plays
- Added renewal-offer and win-back actions so fragile and churned accounts can re-enter the commercial loop
- Added completed-run archives in SQLite plus a `list-archives` CLI command for lightweight meta progression and run history review
- Extended dashboards, save/load coverage, and regression tests for the new governance, support, pricing, customer, and archive state
- Promoted the package version to `0.22.0`

## 0.21.0 - 2026-04-24

- Added add-on campaign and packaging-migration actions so healthy accounts can deepen monetization outside plain price increases
- Added support-tier routing with `standard`, `priority`, and `white_glove` post-sale depth plus an escalation action for at-risk accounts
- Added team-lead promotion, succession-risk tracking, and stronger management-capacity effects on coordination quality
- Added board resolutions, quarterly review counts, restructuring pressure, and a formal restructure action tied to governance stress
- Expanded the content catalog again with add-on, support-tier, and turnaround-focused templates, scenarios, and rival archetypes
- Extended SQLite persistence, dashboard panels, and regression coverage for the new governance, support, and org-structure state
- Promoted the package version to `0.21.0`

## 0.20.0 - 2026-04-24

- Added direct price-increase decisions plus healthier packaging-driven account expansion drift for deeper monetization trade-offs
- Added org-structure v2 with reorg actions, overloaded-manager pressure, and stronger coordination penalties when span-of-control slips
- Added board-response actions tied to the current board ask so governance pressure can be answered directly instead of only observed
- Added finance forecast scenarios for base, conservative, and aggressive runway review in the terminal finance panel
- Deepened support-ops pressure with weighted segment demand, staffing-gap penalties, and better visibility into support capacity
- Expanded the content catalog again with governance, pricing, and org-scale templates plus new board-intervention and org-reorg scenarios
- Promoted the package version to `0.20.0`

## 0.19.0 - 2026-04-24

- Added pricing and packaging depth with `streamlined`, `modular`, and `suite` packaging strategies that change monetization, acquisition, churn, and support cost posture
- Added org-structure depth with manager assignment, management capacity, org-drag pressure, and leadership tracking on employees
- Added support-program upgrade actions so the player can invest directly in knowledge base quality, automation depth, and SLA discipline
- Expanded governance with rotating board asks, warning levels, and stronger confidence penalties when the company misses operating expectations
- Extended SQLite persistence, CLI menus, dashboards, and regression coverage for packaging, management, support-program, and governance state
- Expanded the content catalog with packaging-first, support-SLA, and org-ops templates plus new turnaround scenarios and rival archetypes
- Promoted the package version to `0.19.0`

## 0.18.0 - 2026-04-24

- Added subscription-governed contract depth with package upgrades, renewal-health tracking, failed-payment risk, and dunning pressure
- Added support-ops interventions with backlog triage, escalation-queue tracking, SLA targets, and support deflection reporting
- Added hiring-pipeline screening plus offer negotiation, salary pressure, and deadline pressure before candidates expire
- Added a board and governance layer with burn multiple, board pressure, governance risk, directives, and a dedicated review panel
- Extended SQLite persistence, CLI actions, turn summaries, and dashboard panels for the new contract, support, hiring, and governance state
- Promoted the package version to `0.18.0`

## 0.17.0 - 2026-04-24

- Added subscription depth with plan-tier add-ons, annual prepay behavior, invoice-risk pressure, and richer deal packaging
- Added a shared support-program layer with knowledge base, automation, backlog queue, and SLA-breach tracking
- Added a persistent hiring pipeline with sourcing, interviews, offer conversion, and SQLite save/load coverage
- Added finance forecasting for net cash flow, projected runway, covenant risk, and missed board-target pressure
- Expanded content again with billing, support-automation, and forecast templates plus new renewal, support, and board-recovery scenarios
- Added new rival archetypes for support-heavy, revenue-optimized, and lock-in oriented competitors
- Promoted the package version to `0.17.0`

## 0.16.0 - 2026-04-23

- Added contract-economy depth with seat-based and usage-based customer billing models plus richer sales commitments
- Added support-ops depth through account ticket backlog, SLA pressure, and operations-load interaction
- Added employee performance tracking, underperformance pressure, and real attrition outcomes when burnout is ignored
- Added roadmap-project depth with epics, deadlines, dependency rules, and delivery-risk consequences
- Extended dashboards, tables, and SQLite persistence for the new contract, support, people, and roadmap state
- Promoted the package version to `0.16.0`

## 0.15.0 - 2026-04-23

- Added customer-success actions for onboarding investment and targeted retention plays
- Added contract-depth fields for cadence, discounting, onboarding health, and support load on customer accounts
- Added employee progression with training, promotion readiness, promotion actions, and attrition-risk tracking
- Added functional budget presets to rebalance engineering, marketing, customer success, and G&A priorities
- Extended terminal dashboards to show org mix, deeper customer account detail, and richer team progression stats
- Persisted functional budget state plus deeper customer-account and employee progression fields through SQLite schema version `12`
- Promoted the package version to `0.15.0`

## 0.14.0 - 2026-04-23

- Added product release planning with stability patches, minor releases, and major launches
- Added a lightweight sales pipeline with deal stages that can create key customer accounts
- Added multi-action roadmap projects for platform, enterprise, marketplace, and sales execution bets
- Added scenario objective tracking, hiring-market traits, competitor-intel notes, and balance profile discovery
- Expanded content with sales-enablement AI, data-quality, and release-ops templates plus three new objective-driven scenarios
- Persisted release plans, sales deals, roadmap projects, competitor intel, scenario objectives, event chain metadata, and hiring traits through SQLite schema version `11`
- Promoted the package version to `0.14.0`

## 0.13.0 - 2026-04-23

- Added a fifth content pack with open source, enterprise AI ops, vertical compliance, and community marketplace templates
- Added four scenario starts for open source commercialization, regulated AI scale, platform ecosystem pressure, and enterprise rescue runs
- Added new strategic roadmap initiatives for AI trust, community growth, and enterprise sales pushes
- Added event-chain follow-ups for audit reviews, launch aftershocks, and enterprise procurement delays
- Added deterministic hiring candidate pools plus `list-candidates`, `list-segments`, and `list-roadmaps` CLI discovery commands
- Promoted the package version to `0.13.0`

## 0.12.0 - 2026-04-22

- Added a first-run `tutorial` command and in-game tutorial utility for safer onboarding
- Added `validate-content` to check scenario/template/rival references and event handler coverage
- Tightened balance audit cash warnings so very short smoke runs do not create noisy findings
- Improved invalid scenario handling so normal CLI runs fail with a clear panel instead of traceback noise
- Promoted the package version to `0.12.0`

## 0.11.0 - 2026-04-22

- Added enterprise sales cycle, product launch window, platform outage, competitor acquisition, and regulatory shift events
- Added a CLI glossary for core stats, system terms, and decision families
- Added a Markdown `balance-report` export that combines scenario/difficulty matrix results with balance audit findings
- Added migration coverage for older SQLite schemas with additive columns
- Added release demo and release checklist documentation
- Promoted the package version to `0.11.0`

## 0.10.0 - 2026-04-22

- Added a fourth content pack with AI governance, developer marketplace, customer health, and incident command product templates
- Added four higher-scale scenarios focused on AI governance, ecosystem marketplaces, customer health renewals, and security trust rebuilds
- Added new competitor archetypes for AI fast followers, governance giants, and ecosystem brokers
- Added key-account expansion and security-audit events to connect new content with customer and trust systems
- Extended scenario content seeds with board confidence and competitor funding levels
- Promoted the package version to `0.10.0`

## 0.9.0 - 2026-04-21

- Added key customer accounts with contract revenue, satisfaction, renewal risk, churn, and expansion pressure
- Added board confidence as a finance signal affected by cash flow, investor pressure, and capital events
- Added exit outcomes for winning runs, including profitable independence, strategic acquisition, IPO-ready, and restructure paths
- Deepened competitors with funding levels that increase pressure from strong, high-momentum rivals
- Added `review_customers` and `export-balance-csv` for clearer demo review and external balance tuning
- Persisted key accounts, board confidence, competitor funding, and exit summaries through SQLite schema version `10`
- Promoted the package version to `0.9.0`

## 0.8.0 - 2026-04-21

- Expanded the content catalog with enterprise-data, field-service, and procurement templates plus board-tension, channel-defense, and late-scale drag scenarios
- Added new competitor archetypes for channel aggregators, trust monoliths, and vertical specialists
- Deepened rival behavior with archetype-specific move bias, pressure bonuses, and pivot thresholds
- Added late-game pressure dimensions for org drag, maintenance crisis, and innovation gap
- Added finance events for loan covenant pressure and down-round pressure
- Added progression milestones for capital discipline and resilience against direct rival pressure
- Added `list-events`, `balance-audit`, and `doctor` CLI commands for content discovery, tuning, and local diagnostics
- Advanced SQLite schema metadata to version `9` and persisted competitor archetype ids
- Promoted the package version to `0.8.0`

## 0.7.0 - 2026-04-18

- Added a competitor-archetype catalog so scenarios can seed stronger rival identities without hard-coding every competitor inline
- Expanded the content pack again with new billing-hub and partner-stack templates plus talent-race and moat-builder scenarios
- Added new dynamic events for talent bidding wars and platform breakthroughs to connect team scale and platform quality back into replayable trade-offs
- Added progression milestones for building a deeper talent bench and stronger platform credibility
- Added deterministic `balance-matrix` tuning runs across every supported difficulty profile
- Hardened save metadata with stored build and schema version markers plus a `check-saves` CLI health command
- Added `list-rivals` to surface available competitor archetypes directly from the terminal
- Promoted the package version to `0.7.0`

## 0.6.0 - 2026-04-18

- Added a dedicated late-game pressure layer for renewal risk, concentration risk, and legacy drag so larger runs pick up clearer endgame trade-offs
- Expanded the content catalog again with new customer-portal, renewal-cloud, and ops-intelligence templates plus renewal and channel-heavy scenarios
- Added new dynamic events for renewal risk and channel partner offers to connect mature products and go-to-market trade-offs back into the run
- Added new progression milestones for debt-free operation and building a stronger category moat
- Added a deterministic `compare-balance` CLI command to rank scenarios side by side during tuning work
- Promoted the package version to `0.6.0`

## 0.5.0 - 2026-04-17

- Added a late-game operations layer that turns support load, coordination drag, and portfolio sprawl into visible operating pressure
- Deepened competitor behavior so rivals can pivot toward the player's hottest segment during stronger tactical pushes
- Expanded content again with new templates and scenarios focused on support overload, price wars, and enterprise scale-up
- Added new events for support backlog surges and board scrutiny to connect finance and operations pressure back into the run
- Added a deterministic `simulate-balance` CLI command for multi-run tuning and regression checks
- Added milestone coverage for cleaner enterprise scale and operational discipline
- Promoted the package version to `0.5.0`

## 0.4.0 - 2026-04-14

- Added run difficulty profiles with `builder`, `standard`, and `founder` tuning
- Added campaign goals with alternate progression targets and victory paths
- Added late-game scale pressure from coordination drag, market saturation, cannibalization, and maintenance load
- Extended the dashboard, report view, and scenario catalog to surface difficulty, campaign goals, and scale state
- Persisted difficulty and campaign-goal state through SQLite save/load and schema version `7`

## 0.3.0 - 2026-04-13

- Added save-slot management with list, rename, and delete flows in the CLI
- Added a quick guide command, onboarding hints, and in-session guide utility for new runs
- Deepened competitor behavior so rival moves now reshape pricing posture and product-count pressure
- Expanded the scenario and template catalog with market-shock and portfolio-heavy starting runs
- Hardened packaging metadata and explicit content-file inclusion for release builds

## 0.2.0 - 2026-04-13

- Added richer event content with referral-wave and enterprise-compliance trade-off events
- Added new progression milestones for profitable streaks and multi-segment reach
- Expanded report output with funding, event, and milestone history panels
- Added CLI support for `list-templates` and `--version`
- Promoted the package version to `0.2.0` for the broader content-and-polish release
