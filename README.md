# 🚀 NEXUS TECH

![CI](https://github.com/araxis07/Nexus-Tech/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.13%2B-blue)
![Offline First](https://img.shields.io/badge/offline-first-green)
![Terminal Game](https://img.shields.io/badge/interface-terminal-111827)

**NEXUS TECH** is a terminal-first, single-player business simulation game built entirely in Python.

You start with a small software company, a limited cash reserve, and one early product. From there, your job is to grow the business by making disciplined decisions about product strategy, team management, technical debt, marketing, operating costs, and unexpected business events.

Designed for local play and live demos, the project focuses on clean architecture, deterministic simulation, and a polished CLI experience instead of heavy graphics or web infrastructure.

## 🎮 What Kind of Game Is It?

NEXUS TECH is a:

- **single-player** management / simulation game
- **turn-based** business strategy game
- **terminal-first** experience powered by Rich and Typer
- **local and offline-first** project with SQLite save support

Each turn represents a business interval. You review the company, choose actions, resolve the simulation, react to events, and try to keep the company alive long enough to scale.

## ✨ Current Features

### 🏢 Company Simulation

- Manage company cash, reputation, turn progression, and failure state
- Set a company-wide strategic posture such as growth, quality, or efficiency
- Run a growing software business under financial pressure
- Balance revenue against fixed operating costs, product maintenance, and payroll

### 📦 Product Portfolio Management

- Own and manage multiple products at the same time
- Track quality, bugs, market fit, technical debt, users, acquisition, and churn
- Target different customer segments such as `indie`, `startup`, `SMB`, and `enterprise`
- Adjust pricing tiers to trade off growth, churn, and revenue per user
- Run explicit price-increase plays when you want to trade customer comfort for stronger monetization
- Shift each product between `streamlined`, `modular`, and `suite` packaging to rebalance monetization, acquisition, and support complexity
- Expand package catalogs and add-on catalogs over time so monetization depth can scale beyond the base packaging posture
- Open reseller, integration, and marketplace partnerships that add sourced growth, revenue-share trade-offs, support load, and direct-channel conflict
- Track partner fatigue and recovery posture so channel growth can stall, stabilize, and recover instead of scaling linearly forever
- Renegotiate stressed partnerships to deliberately trade margin for a calmer channel lane when scale starts to outrun trust
- Reactivate paused or strained partnerships with a direct recovery action when channel execution has to be repaired before growth can continue
- Create products from reusable templates, improve quality, add features, market products, reduce debt, and sunset weak products
- Plan and ship product releases such as stability patches, minor releases, and major launches
- Use multi-action roadmap projects for larger bets like platform rebuilds, enterprise certification, marketplace launches, and sales playbooks
- Track roadmap project epics, dependencies, deadlines, and delivery risk instead of treating every strategic bet as a flat progress bar
- Deal with segment-specific trade-offs like support cost, price sensitivity, and competitive pressure

### 🧩 Data-Driven Content

- Start runs from a scenario catalog instead of a single hard-coded opening
- Play six featured campaigns with persistent Commitment and Consequence choices that change real product, cash, debt, team, and governance state
- Audit featured campaigns against their scenario-native goals with per-route goal progress and completion evidence instead of forcing every journey through one profit metric
- Turn both campaign choices into a Campaign Legacy that explains the completed route, its future event pressure, and the final act mandate
- Keep the beta catalog frozen at 49 scenarios, 49 product templates, 32 rival archetypes, 194 internal actions, 99 player-facing programs, and 202 systemic events while validation replaces expansion
- Gate select reward scenarios behind archive progression while still surfacing them in the catalog with explicit locked or unlocked status
- Use reusable product templates such as SaaS tools, growth apps, developer platforms, and workflow suites
- Gate select reward templates and rival archetypes behind archive progression so repeat runs can unlock new starts without changing the offline scope
- Expand the catalog with AI copilot, analytics, support-ops, compliance, embedded API, and capital-pressure scenarios
- Extend the catalog further with renewal-cloud, customer-portal, and ops-intelligence templates plus channel and concentration-risk scenarios
- Add a second content-pack pass with billing-hub and partner-stack templates plus talent-race and moat-builder scenarios
- Add enterprise-data, field-service, and procurement templates plus board-tension, channel-defense, and late-scale drag scenarios
- Add AI-governance, developer-marketplace, customer-health, and incident-command templates plus higher-scale trust and ecosystem scenarios
- Add open-source, enterprise-AI-ops, vertical-compliance, and community-marketplace templates plus objective-driven scale scenarios
- Add sales-enablement AI, data-quality, and release-ops templates plus enterprise pipeline, data trust, and release-crunch scenarios
- Add subscription-billing, support-automation, and revenue-forecast templates plus renewal, support, and board-recovery scenarios
- Add campaign-ladder and reserve-planning templates plus governance-climb and reserve-discipline scenarios for heavier late-game practice runs
- Keep scenario and template definitions in JSON so the content layer can grow without rewriting core systems
- Track scenario-specific objectives with measurable progress such as closed deals, reputation, or enterprise users
- Support custom company and primary product overrides on top of scenario defaults

### 🌐 Market and Competition

- Run each company inside a live market cycle such as `cooling`, `steady`, `expanding`, or `frothy`
- Track lightweight competitor rosters that apply ongoing pressure by segment, pricing, aggression, and tactical momentum
- Simulate rival moves such as `hold`, `discount_push`, `feature_sprint`, and `retrench`
- Track rival funding levels so strong, high-momentum competitors become more dangerous over time
- Define reusable competitor archetypes such as price raiders, platform bulwarks, and feature blitzers
- Expand rival archetypes with channel aggregators, trust monoliths, and vertical specialists
- Add AI fast followers, governance giants, and ecosystem brokers as new rival archetypes
- Add open source challengers, regulatory incumbents, and platform consolidators as new competitor archetypes
- Add enterprise sales machines, data-quality specialists, and release-velocity rivals as higher-scale pressure archetypes
- Add support-swarm, revenue-optimizer, and renewal-lock-in rivals for heavier post-sale and monetization pressure
- Add bundle-empires and service-reliability rivals to pressure packaging posture and operational discipline
- Let rival moves reshape product count and pricing posture over time
- Capture compact competitor-intel notes when rival posture changes or momentum spikes
- Push into late-game scale pressure through market saturation, product cannibalization, coordination drag, and maintenance sprawl
- Track an explicit operations layer that converts support backlog and portfolio sprawl into real cost, morale drag, and execution risk
- Add a dedicated late-game layer for renewal risk, concentration risk, and legacy drag once a run reaches real scale
- Feel direct trade-offs between customer demand, churn pressure, rivalry, and product positioning
- Surface market state and competitor posture in dedicated terminal panels for live demos
- Let stronger rivals pivot toward the company's hottest customer segment as traction becomes more visible

### 💰 Finance and Capital

- Take local loans to extend runway and pay recurring interest
- Raise `angel` or `venture` funding when the company has enough traction
- Track debt, dilution, investor pressure, total capital raised, and funding history
- Track board confidence as a compact signal of governance trust, cash-flow discipline, and capital pressure
- Forecast near-term cash flow and runway instead of relying only on last-turn performance
- Track covenant risk and missed board targets so finance pressure is visible before collapse
- Track burn multiple, board pressure, governance risk, and board directives as the company scales
- Track an active board ask plus a warning ladder so governance pressure escalates before the company fully breaks
- Track a rolling board score and launch multi-turn board recovery plans when trust starts slipping
- Review a board scorecard across profitability, reliability, team health, and portfolio focus instead of relying on one opaque governance number
- Track quarterly board resolutions and restructuring pressure so repeated misses create visible strategic consequences
- Track formal board-response deadlines so ignored resolutions can re-intensify governance pressure a few turns later
- Let repeated board misses escalate into an explicit governance crisis so late-game pressure compounds when the company ignores follow-through
- Force governance trade-offs when a board resolution stays open so the company has to bias toward profitability, reliability, team recovery, or portfolio focus
- Set a capital plan with explicit reserve posture and preferred capital source so runway expectations can differ between conserve, balanced, and expand modes
- Tune capital plans manually with custom planning horizon, reserve target, and product versus GTM versus reserve allocation instead of relying only on posture presets
- Track explicit endgame readiness across IPO, acquisition, and profitable independence so late-game strategy is easier to read before the run ends
- Break endgame evaluations into sharper variants such as governance-premium IPO paths, platform acquisitions, independent compounders, and board-led resets
- Review base, conservative, and aggressive finance forecasts directly in the dashboard before committing to riskier turns
- Review a multi-turn finance planner with projected end-cash and reserve-break visibility instead of relying on one-turn forecast drift alone
- Get explicit recommended capital posture, reserve-break risk, allocation signals, and planner alerts when reserve stress or covenant pressure starts to dominate the run
- Read capital-mix guidance, funding posture, dilution outlook, and covenant outlook directly in the planner instead of inferring them from raw cash alone
- Execute direct board-response plays to answer profitability, reliability, team-health, or portfolio-focus pressure
- Execute a formal restructure plan when governance pressure becomes too high to ignore
- Balance growth capital against repayment pressure, score penalties, and long-term victory quality

### 🤝 Customer Accounts

- Turn strong product traction into named key customer accounts
- Source and advance sales deals through lead, demo, pilot, and closed stages
- Track account satisfaction, contract value, expansion potential, renewal timing, and churn risk
- Add contract cadence, discounting, onboarding health, and support load to make renewals more believable
- Support flat, seat-based, and usage-based contract models with different commercial expansion patterns
- Track per-account plan tier, add-ons, annual prepay posture, and invoice-risk pressure
- Track subscription package depth, renewal health, failed-payment risk, and dunning pressure on each account
- Route accounts into `standard`, `priority`, or `white_glove` support tiers as the portfolio matures
- Let healthy accounts expand between renewals through packaging-driven add-ons, suite upgrades, and contract growth
- Run explicit add-on campaigns and packaging migrations to rebalance monetization, support burden, and retention posture
- Let package-catalog depth and add-on-catalog depth prepare accounts for richer migrations, stronger renewal posture, and deeper contract expansion
- Make proactive renewal offers and run win-back plays so churned accounts can still become commercial recovery opportunities
- Choose renewal-offer types such as `light_discount`, `bundle_upgrade`, and `term_extension` so commercial saves carry clearer trade-offs
- Track open tickets and SLA pressure so support quality can directly affect renewals and retention
- Add recurring account revenue on top of product usage revenue
- Let weak product health, bugs, and technical debt create visible renewal pressure
- Invest directly in customer success and run targeted retention plays on fragile accounts
- Improve a shared support program with knowledge-base and automation depth that lowers ticket pressure across the portfolio
- Upgrade support operations directly through knowledge-base, automation, and SLA investments instead of relying only on passive drift
- Aim support operations at `balanced`, `onboarding`, `enterprise`, or `billing` lanes to change which queues get relief first
- Track onboarding and enterprise ticket pressure separately so support-lane focus creates clearer trade-offs instead of generic backlog relief
- Track billing pressure from invoice risk, failed payment risk, and dunning so post-sale operations now cover collections pressure too
- Route escalations differently for onboarding, enterprise, and billing accounts so support actions now match the real queue that is failing
- Invest in dedicated support staffing and pay visible service cost every turn as the installed base becomes heavier to serve
- Run explicit support triage actions that cut backlog, escalation pressure, and payment-risk spillover
- Review key accounts directly from the in-game `review_customers` action

### 👥 Employee and Team System

- Hire and fire employees
- Review deterministic candidate pools before hiring during demos or interactive runs
- Evaluate candidate traits such as steady operator, fast learner, expensive expert, and burnout risk
- Run a persistent hiring pipeline with sourcing, interviewing, and offer conversion instead of only instant hires
- Screen candidates before interviews and negotiate offers under salary-market pressure instead of using a flat one-step funnel
- Assign team members to specific products
- Manage core roles:
  - `engineer`
  - `designer`
  - `marketer`
  - `product_manager`
- Simulate morale, energy, burnout, recovery, and role-based impact on outcomes
- Train employees, track promotion readiness, promote strong contributors, and monitor attrition risk
- Track performance rating, underperformance streaks, and real resignation pressure when the company runs too hot
- Assign managers, track leadership strength, and absorb org-drag pressure as headcount grows beyond clean management coverage
- Track management layers and span-of-control risk so larger orgs create visible coordination drag instead of scaling cleanly forever
- Promote product-facing team leads and track succession risk when too much execution leverage sits on one person
- Run explicit org reorg actions to rebalance reporting lines and cut overloaded-manager drag
- Run explicit compensation reviews and succession reviews so people pressure can be managed directly instead of only showing up as passive attrition

### 🧭 Functional Budgeting

- Set an org-level allocation preset for engineering, marketing, customer success, and G&A
- Use presets such as `product_push`, `growth_push`, `customer_trust`, and `cash_guard`
- Let functional-budget choices shape execution speed, sales motion, retention stability, and org resilience

### 🎲 Dynamic Event Engine

- Weighted random business events with cooldowns and eligibility rules
- Event categories include:
  - product incidents
  - market opportunities
  - funding opportunities
  - reputation incidents
  - employee issues
- Some events create meaningful player trade-offs instead of simple bonuses
- New event content includes referral waves and enterprise compliance review pressure
- Additional event content now includes support backlog surges and board-level scrutiny over capital discipline
- Mature runs can now surface renewal-risk events and channel partner offers with visible product and GTM trade-offs
- Scale-stage runs can now trigger talent bidding wars and platform breakthroughs with clearer team and product trade-offs
- Finance-heavy runs can surface loan covenant pressure and down-round trade-offs
- Scale-stage runs can now surface channel-conflict, bridge-capital, and inbound exit-interest decisions tied to the new partnership and endgame systems
- Scale-stage runs can now surface partner-breakdown and board-recovery-window follow-up events when channel or governance pressure compounds
- Customer-heavy and enterprise-heavy runs can surface key-account expansion and security-audit trade-offs
- Scale-stage runs can now surface enterprise sales cycles, product launch windows, platform outages, competitor acquisitions, and regulatory shifts
- Follow-up event chains can now appear after related audit, launch, and enterprise-sales events
- Event chain metadata is now tracked in event history for cleaner future expansion
- Competitor pressure now also shows up through the simulation layer, not only through isolated events

### 🏁 Progression

- Choose or inherit a campaign goal such as `profit_machine`, `portfolio_empire`, or `category_leader`
- Run difficulty profiles with `builder`, `standard`, and `founder` pressure tuning
- Unlock company milestones as the business scales
- Track key moments such as traction, cash reserves, team growth, and portfolio expansion
- Recognize profitable streaks and multi-segment reach as the company matures
- Recognize operational discipline and enterprise footholds as higher-scale milestones
- Add milestone coverage for building a credible talent bench and a stronger platform foundation
- Add milestone coverage for capital discipline and resilience against direct rivals
- Set quarter-scale roadmap focuses such as growth push, platform rebuild, premium expansion, and portfolio consolidation
- Use higher-scale roadmap initiatives such as AI trust program, community growth, and enterprise sales push
- Set a budget stance such as `lean`, `balanced`, or `aggressive` and let it shape burn, marketing efficiency, and team fatigue
- Work against a quarter plan with explicit revenue, user, cash, and headcount targets
- Work against scenario objectives and larger roadmap projects in addition to campaign goals
- Track run score, estimated company value, turn history, and victory conditions in the terminal report
- Classify successful runs into exit paths such as profitable independence, strategic acquisition, IPO-ready, or restructure
- Summarize completed-run history into archive-driven meta progression with campaign tiers and unlock-style achievement tracking
- Surface a visible campaign ladder, archive benchmarks, and next-goal hints so repeat runs feel like structured progression instead of isolated saves
- Expose an explicit unlock catalog with player-facing reward names for archive-driven scenarios, templates, rivals, tools, and late-game insight lenses
- Apply archive-driven unlocks to real gameplay entry points so locked reward starts cannot be launched until the local archive progression earns them
- Compare archived runs directly through score, cash, offer, grade, and outcome coverage so late-game experimentation becomes easier to review
- Surface path-specific archive leaders, badge coverage, reward mix, and next-gap guidance so the meta layer can point toward what the player has not yet mastered
- Track discovery, victories, shutdowns, and average performance across all 24 authored campaign routes, then recommend the next unexplored route
- Connect the opening, both campaign decisions, endgame, final outcome, and first archive through one six-step First Archive Mission in terminal and 2D play

### 💾 Local Save / Load

- Save and load runs locally with SQLite
- Resume the latest save slot
- List, rename, and delete save slots directly from the CLI
- Archive completed runs and inspect them later through `list-archives`
- Use an explicit `Save & Archive` action at run review so completed-run progression is never confused with exiting unsaved
- Confirm completed saves as `Run Archived`, prevent duplicate archive clicks, and direct the player back to Progress for the next route
- Derive campaign-level progression from archived runs through `show-progression`
- Review the exact archive-driven unlock catalog through `list-unlocks`
- Compare archived runs directly through `compare-archives`
- Archive run score tier, campaign grade, and estimated valuation so completed runs are easier to compare later
- Archive compact run badges such as capital discipline, board trust, and enterprise execution so meta history is easier to scan quickly
- Archive strategic outlook and modeled offer value so completed runs can be compared by likely business outcome as well as score
- Archive after-action review summaries and next-focus commands so completed runs keep the main lesson attached to progression history
- Compare completed runs through archive benchmarks such as best score, best offer, and exit-path coverage directly in the terminal
- Unlock archive-driven reward hints for scenarios, templates, rivals, and review tools as progression achievements stack up
- Track unlocked archive rewards as explicit typed entries instead of only free-form hint text
- Persist roadmap state, market cycle, quarter plan, finance state, funding history, competitors, key accounts, product targeting, event history, team assignments, exit summaries, turn history, and the bounded Decision Ledger
- Persist partnerships and capital-plan posture so channel strategy and reserve discipline survive save/load boundaries
- Persist release plans, sales deals, roadmap projects, competitor intel, scenario objectives, and hiring traits
- Use SQLite schema versioning and additive migrations to keep local save files upgradeable
- Keep the entire project offline and self-contained

### 🖥️ Presentation and CLI

- Rich-powered dashboard panels, tables, summaries, and event notifications
- Lightweight `pygame-ce` 2D dashboard frontend with animated bars, motion-aware product cards, product drama effects, finance/board risk drama, pending-choice consequence cues, pending-event option preview motion, action/context pickers, clickable controls, persistent Back/Pause/Menu navigation rails, responsive run layouts, hover tooltips, targeted event-driven delta pulses, shape-based entity motion for stat lanes/product cards/deep panels, deterministic shape-sprite actor timelines for title/menu, run, inspector, endgame, summary, and review scenes, actor-state coverage gates, actor-readability collision gates, readability guards, text-fit clipping, visual-fatigue budgets, animation-pacing budgets, scene motion profiles, long-session motion stress gates, command-specific action feedback cues, blocked-action feedback cards, late-game command choreography cards, state-delta impact cue cards, modal overlay enter/exit transitions, turn-summary cinematic rail, metric reveal sequencing, compact outcome lanes, and outcome cinematic overlays, player-selectable full/reduced/off highlight motion, shared scene-entry transitions, a full title/new-game wizard flow, save-slot management, deep-dive overlays, interactive inspector overlays with per-panel memory and actionable/hotspot focus shortcuts, a meta board, a dedicated endgame board with path-fix cockpit controls, hotspot-review routing, cockpit handoff cues, coalesced event cards, adaptive live/title feed pacing, queue-aware feed TTL tuning, priority-aware backlog retention, pulse-pressure-aware motion damping, pulse-bank stabilization/pruning, deterministic headless motion-stability, visual QA capture with baseline signatures, summary reports, and CI artifacts, animation-completeness audits, scenario/seed animation matrix audits, long-run pressure, and request-path audits, turn-resolution event prioritization, path-specific late-game choreography cards, full surfaced-command motion audits, short-button detail suppression for compact layouts, a tighter 820-class action grid, compact action-bar labels, compact footer status copy, a reserved two-line footer band, compact score metadata, compact stacked-meta layouts, adaptive small-window inspector paging, ready/blocked inspector cues, recovery hints for empty filtered states, and staged review scenes
- The default 2D Focus View prioritizes Act Objective, Recommended Next, and End-Turn Risk with at most six controls; press `0` on standard windows to switch to the full ten-control dashboard
- Strategic Rhythm connects that objective to live Quarter Plan progress, the recommended move, the end-turn check, and one delayed follow-on; terminal play uses the same compact loop while the Run Report retains full Coach, Risk Forecast, and Preview diagnostics
- Decision Pattern derives the current operating-family mix, unique-choice coverage, and neutral repetition signals from the existing Decision Ledger; forced campaign and systemic event responses do not distort the pattern
- A deterministic decision-quality audit compares that pattern across six campaigns and three difficulties; coverage failures block CI, while repetition and low-variety results remain advisory until real-player notes agree
- The 2D Endgame Board starts with Recommended Fix and Review Main Risk; press `V` or click More to reveal every existing exit-path fix and specialist review without losing keyboard or inspector access
- Contextual 2D action footer keeps Coach, two recommended alternatives, Report, Save, and End Turn visible in Focus View while the full dashboard preserves phase-aware endgame, board, and partner routes
- Persistent Contextual, Product, Growth, and Resilience loadouts prioritize enabled action-bar choices without bypassing gameplay prerequisites or changing simulation balance
- Every 2D launch path supports optional `--ui-scale compact|standard|large`, `--contrast-mode standard|high`, and `--motion-mode full|reduced|off` session overrides; omitted flags reuse the local saved profile
- The title menu (`7 Settings`) and Pause menu (`T Settings`) apply text scale, contrast, motion, and action loadout immediately across scenes and persist them locally without changing gameplay save slots; Pause exposes title return only for title-shell launches, while direct play keeps `M` inert and reserves `Q` for explicit quit
- Player-facing command metadata preserves all 194 internal routes while collapsing repeated late-game ladders into 99 readable action concepts across 12 families; 2D and terminal presentation no longer expose raw command ids
- The new-game wizard leads with six featured tracks for learning, profit, quality recovery, portfolio scale, debt pressure, and endgame readiness, each with an authored Foundation plus mechanical Commitment and Consequence decisions
- Debt Crunch keeps its repayment-versus-growth pressure while a deterministic 20-turn gate protects Builder and Standard from unavoidable opening collapse
- The live HUD surfaces the current campaign act, objective, decision lens, and compact cash/runway/users/AP vital line; turn summaries now explain the cash, demand, pressure, and product causes behind each result
- Typer-based CLI commands for starting, loading, and continuing runs
- Dedicated board/governance review plus deeper support, hiring, and customer account panels for demo-friendly runs
- Guided Opening now adapts the first 6 turns into a live checklist instead of leaving onboarding as static text only
- Turn Coach now includes action windows and skip-consequence notes so the next 2-3 turns are easier to sequence
- Turn Coach now also marks "Not Now" commands when growth, hiring, or ending the turn would lock in avoidable risk
- Risk Forecast now surfaces the next-turn failure modes and mitigation commands directly in the dashboard and report
- End-Turn Preview now samples the next turn before you commit so cash, runway, board pressure, support load, and channel risk deltas are visible
- End-Turn Preview can require a confirmation step before risky `end_turn` commits when the sample outcome points to shutdown or critical pressure
- Victory and shutdown screens now include an after-action review that ranks the main strain lanes and the command that should have been run earlier
- Difficulty Profile panels and intro messaging now explain the intended play style, goal, and failure mode for `builder`, `standard`, and `founder`
- Finance and support panels now surface forecast scenarios, staffing capacity, and staffing gaps for faster live decision-making
- Partnership and archive panels now surface portfolio health, dominant channel, archive benchmarks, and campaign-ladder progress for cleaner late-game demos
- Progression and archive tools now surface unlock ids, missing endgame paths, and dominant archive outcomes for faster late-game review
- Built-in quick guide flow for onboarding and live demos
- Built-in first-run tutorial and glossary commands for new players
- Built-in `audit-onboarding-flow` command validates first-time player guidance across Guided Opening, Turn Coach, and Risk Forecast before visible-window onboarding playtests
- Built-in `onboarding-visible-playtest-packet` command exports the manual tutorial/menu/play packet across target windows and motion modes so visible onboarding QA does not rely on memory or source-code knowledge
- Built-in `validate-onboarding-visible-playtest-packet` command blocks stale or incomplete onboarding visible QA packets before CI uploads the manual handoff artifact
- Built-in `onboarding-visible-playtest-report`, `record-onboarding-visible-playtest-route`, and `validate-onboarding-visible-playtest-report` commands turn real visible-window onboarding observations into a checked evidence artifact
- Built-in `onboarding-visible-playtest-status` command shows visible onboarding QA progress plus the next visible command and recorder command for the next incomplete route
- Built-in `onboarding-visible-playtest-next` command writes a copy-ready next-step handoff with the exact visible command, recorder command, validation command, and evidence checklist
- Built-in `validate-onboarding-visible-playtest-next` command blocks stale next-step handoffs before CI uploads the manual QA artifact
- Built-in `onboarding-visible-playtest-batch-packet` and `validate-onboarding-visible-playtest-batch-packet` commands scope and verify the next focused set of incomplete onboarding visible QA routes without treating the packet as evidence
- Built-in `onboarding-visible-playtest-batch-preflight` command headlessly launches the current focused onboarding visible QA batch before real-window evidence recording begins
- Built-in `onboarding-visible-terminal-batch` and `validate-onboarding-visible-terminal-batch` commands package and verify the first three terminal onboarding routes before the 2D window matrix begins
- Built-in `onboarding-visible-terminal-evidence-sheet` and `validate-onboarding-visible-terminal-evidence-sheet` commands write and verify a terminal-route worksheet before manual observations are recorded
- Built-in `onboarding-visible-window-evidence-sheet` and `validate-onboarding-visible-window-evidence-sheet` commands write and verify 820x620, 1280x720, and 1440x900 visible-window onboarding worksheets before UI QA begins
- Built-in `onboarding-visible-evidence-matrix` and `validate-onboarding-visible-evidence-matrix` commands summarize terminal and visible-window worksheets into one closeout artifact before manual signoff
- Built-in `onboarding-visible-window-preflight` command headlessly launches title and first-turn onboarding routes across requested windows/motion modes before manual visible-window evidence begins
- Built-in `onboarding-visible-manual-session` and `validate-onboarding-visible-manual-session` commands assemble and verify the real-window operator packet before onboarding evidence recording starts
- Built-in `onboarding-visible-ux-issue-intake` and `validate-onboarding-visible-ux-issue-intake` commands capture observed UX/UI findings from real manual onboarding playtests without treating the intake as evidence
- Built-in `record-onboarding-visible-ux-issue` command updates one UX issue intake row from the same real visible-window observation before rebuilding the fix plan
- Built-in `onboarding-visible-ux-fix-plan` and `validate-onboarding-visible-ux-fix-plan` commands prioritize observed P0/P1/P2 UX findings from the intake before UI signoff
- Built-in `onboarding-visible-ux-triage-sprint` and `validate-onboarding-visible-ux-triage-sprint` commands turn the current fix plan into the next focused triage/fix sprint without fabricating manual evidence
- Built-in `onboarding-visible-ux-triage-next` and `validate-onboarding-visible-ux-triage-next` commands write and verify the exact next visible route, recorder command, and intake row to update from the triage sprint
- Built-in `onboarding-visible-ux-recording-queue` and `validate-onboarding-visible-ux-recording-queue` commands package all open UX rows with open/report/intake recorder commands for the next real manual pass
- Built-in `onboarding-visible-ux-progress` and `validate-onboarding-visible-ux-progress` commands summarize report evidence, intake severity, blockers, and queue rows before final UX signoff
- Built-in `onboarding-visible-ux-batch-packet` and `validate-onboarding-visible-ux-batch-packet` commands scope the next short visible-window UX pass from the recording queue without treating the packet as evidence
- Built-in `onboarding-visible-ux-batch-closeout` and `validate-onboarding-visible-ux-batch-closeout` commands compare the historical focused batch with current report/intake rows, keep P0/P1/P2 work open, and expose the exact refresh sequence before the next batch
- Built-in `play-2d`, `load-game-2d`, `continue-last-game-2d`, `menu-2d`, `audit-2d-motion`, `audit-2d-visual`, `audit-2d-layout-matrix`, `audit-2d-animation`, `audit-2d-animation-matrix`, `prepare-2d-animation-playtest`, `prepare-animation-playtest-session`, `draft-animation-playtest-report`, `animation-playtest-status`, `animation-playtest-commands`, `validate-animation-playtest-commands`, `animation-playtest-plan`, `animation-playtest-next`, `animation-playtest-recorder-next`, `animation-playtest-route-batches`, `validate-animation-playtest-route-batches`, `animation-playtest-ui-triage`, `validate-animation-playtest-ui-triage`, `animation-playtest-release-gate`, `validate-animation-playtest-release-gate`, `animation-playtest-progress`, `validate-animation-playtest-progress`, `animation-playtest-execution-guide`, `validate-animation-playtest-execution-guide`, `animation-playtest-issue-backlog`, `validate-animation-playtest-issue-backlog`, `animation-playtest-sprint`, `validate-animation-playtest-sprint`, `animation-playtest-evidence-sheet`, `validate-animation-playtest-evidence-sheet`, `animation-playtest-recorder-queue`, `validate-animation-playtest-recorder-queue`, `validate-animation-playtest-plan`, `validate-animation-playtest-session`, `animation-playtest-handoff`, and `validate-animation-playtest-report` commands for the animated frontend shell, now with shared `--motion-mode full|reduced|off` and `--window-size WIDTHxHEIGHT` launch controls, motion-mode differentiation gates, shared boot/title/run/summary/review transition sweeps, stat/product/panel entity-motion strips, scene-specific actor sprite clips, actor-state and actor-readability audit layers, readability guards, visual-fatigue and animation-pacing audit budgets, scene motion-profile gates, long-session motion stress gates, long-session visual readiness gates, command-specific action feedback cues, blocked-action feedback coverage, late-game command choreography cards, pending-event option previews, deterministic visual QA captures with baseline signatures, summary Markdown, responsive layout matrices, and CI artifact export for visual captures, layout matrices, animation readiness matrices, open-window playtest prep reports, manual session setup with validated plan artifacts, validated manual command queues, validated route-batch plans, validated UI triage backlogs, validated release gates, validated progress boards, validated execution guides, validated issue backlogs, validated sprint packets, validated evidence capture sheets, validated recorder queues, validated session packages, manual handoff sheets, validated grouped next-step animation playtest plans, single-next-action manual QA prompts, strict manual signoff report drafts, evidence-note validation for manual reports, grouped manual playtest status summaries, animation-completeness gates with advisory gaps, broad scenario/seed animation matrix gates with Markdown artifacts, a new-game wizard, save-slot management, archive browsing, a dedicated meta board, a dedicated endgame board, responsive layouts, interactive inspector overlays with remembered section/page state, adaptive per-window paging, actionable/hotspot controls, hover/help guidance, disabled-action explanations, staged post-turn summaries with outcome lanes, outcome cinematic overlays, cockpit brief and handoff events, quieter event-feed coalescing, adaptive feed-card pacing, queue-aware feed TTL tuning, prioritized turn-resolution cards, compact overlay action copy, contextual action-bar status lines, destination-aware cockpit tooltips, full surfaced-command specific choreography coverage, review/report-specific motion routing, and a shared motion layer that reacts to stat, product, overlay, governance, actor, and endgame deltas
- Focused manual animation QA helpers include `animation-playtest-batch-next`, `animation-playtest-batch-packet`, and `validate-animation-playtest-batch-packet` so the next open visible-window packet stays tied to the route-batch artifact
- Focused batch automation includes `animation-playtest-batch-preflight`, which runs the 820x620 menu/play commands headlessly across full, reduced, and off modes before manual visible-window evidence begins
- Responsive layout automation includes `audit-2d-layout-matrix`, which turns the existing visual captures into a viewport/motion Markdown gate for target spacing, text fitting, and layout containment before manual QA
- Compact-window layout guards now keep Quick Start cards and deep-panel actions clear of their footer controls, while terminal onboarding guidance wraps complete sentences at narrow console widths
- Tall 2D overlays now reserve the top navigation lane, center unpaired final actions, keep inspector sections clear of Close controls, and include the Help overlay in visual-audit coverage
- Session bundle validation includes `validate-animation-playtest-session-bundle`, which checks the manual report, queue, plan, recorder queue, route batches, focused next-batch packet, triage, release gate, progress, execution guide, backlog, sprint, evidence sheet, and handoff before CI uploads artifacts
- In-game reporting view for score, valuation, quarter-plan progress, competitor watch, and recent turn history
- Deterministic `simulate-balance` batch runs for tuning scenarios, difficulties, and goals without playing by hand
- Deterministic `compare-balance` scenario rankings for side-by-side tuning across multiple openings
- Deterministic `balance-matrix` runs to compare the same scenarios across every difficulty profile
- Deterministic `balance-audit` runs to flag rough scenario/difficulty combinations for tuning
- CI-backed 20-turn gameplay convergence coverage for Founder Journey across every campaign goal and difficulty profile
- Deterministic `export-balance-csv` output for external review of scenario and difficulty balance
- Deterministic `balance-report` output for Markdown tuning reports that combine matrix, audit data, threshold gates, and top tuning priorities
- Autoplay balance sweeps now degrade more gracefully around invalid funding/event branches so tuning runs fail as balance signals instead of crashing on input policy mistakes
- Founder-focused autoplay balance sweeps now respect angel funding caps, keep profit-first openings on viable standard pricing, and shift into cash-guard posture earlier when runway or board pressure tightens
- Built-in `glossary` command to explain core stats, pressure systems, and decision families
- Built-in `validate-content` command to check catalog references and event handler wiring before release
- Report now includes recent events, funding history, and milestone history
- Add `list-rivals`, `list-events`, `doctor`, and `check-saves` so content, install state, and local persistence health can be reviewed without entering a run
- Add `list-archives` so completed runs can be reviewed without opening the save database manually
- Add `list-candidates`, `list-segments`, and `list-roadmaps` for hiring, customer, and strategy discovery without entering a run
- Add `list-balance-profiles` plus in-game pipeline review for releases, sales deals, and roadmap projects
- Seeded demo support for reproducible simulations

### 🧪 Quality and Tooling

- Fast deterministic test suite with `pytest`
- Centralized linting and formatting with `Ruff`
- `uv`-based project workflow for dependency and run management
- GitHub Actions CI to run lint, formatting, content validation, tests, and 2D animation audit gates on pushes and pull requests

## 🧱 Tech Stack

- **Python 3.13+**
- **uv** for project and dependency management
- **sqlite3** from the Python standard library for persistence
- **Pydantic v2** for validated domain models
- **Rich** for terminal rendering
- **Typer** for CLI entrypoints
- **pytest** for tests
- **Ruff** for linting and formatting

## ▶️ Getting Started

Install dependencies:

```bash
uv sync --extra dev
```

Start a new game:

```bash
uv run nexus-tech --seed 7
```

Open the primary 2D title menu:

```bash
uv run nexus-tech menu-2d
```

Root help shows player-facing commands only. Balance, audit, CI, and manual-QA commands remain directly invocable and can be discovered with:

```bash
uv run nexus-tech developer-tools
uv run nexus-tech developer-tools --search campaign
```

List the available scenarios:

```bash
uv run nexus-tech list-scenarios
```

List the available product templates:

```bash
uv run nexus-tech list-templates
```

List the available competitor archetypes:

```bash
uv run nexus-tech list-rivals
```

List the event registry:

```bash
uv run nexus-tech list-events
```

List generated hiring candidates:

```bash
uv run nexus-tech list-candidates --seed 7 --count 3
```

List customer segment trade-offs:

```bash
uv run nexus-tech list-segments
```

List roadmap initiatives:

```bash
uv run nexus-tech list-roadmaps
```

List the available campaign goals:

```bash
uv run nexus-tech list-goals
```

Start a named run:

```bash
uv run nexus-tech new-game --company-name "Atlas Labs" --product-name "Signal"
```

Start from a specific scenario:

```bash
uv run nexus-tech new-game --scenario vc_sprint --seed 7
```

Override the difficulty and campaign goal:

```bash
uv run nexus-tech new-game --scenario vc_sprint --difficulty founder --goal portfolio_empire
```

Run a deterministic balance batch:

```bash
uv run nexus-tech simulate-balance --scenario founder_journey --difficulty standard --goal profit_machine --runs 5 --turns 10 --seed-base 100
```

Compare multiple scenarios side by side:

```bash
uv run nexus-tech compare-balance --scenario founder_journey --scenario technical_rebuild --runs 3 --turns 10 --seed-base 100
```

Run a full scenario-versus-difficulty balance matrix:

```bash
uv run nexus-tech balance-matrix --scenario founder_journey --scenario technical_rebuild --runs 2 --turns 10 --seed-base 100
```

Run a quick balance audit:

```bash
uv run nexus-tech balance-audit --scenario founder_journey --scenario technical_rebuild --runs 2 --turns 10 --seed-base 100
```

Export a balance matrix to CSV:

```bash
uv run nexus-tech export-balance-csv --output balance.csv --scenario founder_journey --runs 2 --turns 10 --seed-base 100
```

Export a Markdown balance report:

```bash
uv run nexus-tech balance-report --output balance-report.md --scenario founder_journey --runs 2 --turns 10 --seed-base 100
```

Load a saved game:

```bash
uv run nexus-tech load-game --slot active
```

Continue the latest save:

```bash
uv run nexus-tech continue-last-game
```

Run in debug mode:

```bash
uv run nexus-tech --debug --seed 7
```

Show CLI help:

```bash
uv run nexus-tech --help
```

Show the installed version:

```bash
uv run nexus-tech --version
```

Show the quick guide:

```bash
uv run nexus-tech guide
```

Show the first-run tutorial:

```bash
uv run nexus-tech tutorial
```

Run the automated first-time player clarity audit:

```bash
uv run nexus-tech audit-onboarding-flow --output /tmp/nexus-tech-onboarding-flow-audit.md
```

Prepare the manual visible-window onboarding packet:

```bash
uv run nexus-tech onboarding-visible-playtest-packet --output /tmp/nexus-tech-onboarding-visible-playtest.md
```

Validate the manual visible-window onboarding packet:

```bash
uv run nexus-tech validate-onboarding-visible-playtest-packet --input /tmp/nexus-tech-onboarding-visible-playtest.md
```

Prepare and validate the manual visible-window onboarding evidence report:

```bash
uv run nexus-tech onboarding-visible-playtest-report --input /tmp/nexus-tech-onboarding-visible-playtest.md --output /tmp/nexus-tech-onboarding-visible-playtest-report.md
uv run nexus-tech onboarding-visible-playtest-status --report /tmp/nexus-tech-onboarding-visible-playtest-report.md
uv run nexus-tech onboarding-visible-playtest-next --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --output /tmp/nexus-tech-onboarding-visible-playtest-next.md
uv run nexus-tech validate-onboarding-visible-playtest-next --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --input /tmp/nexus-tech-onboarding-visible-playtest-next.md
uv run nexus-tech onboarding-visible-playtest-batch-packet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --batch-size 3 --output /tmp/nexus-tech-onboarding-visible-playtest-batch-packet.md
uv run nexus-tech validate-onboarding-visible-playtest-batch-packet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --batch-size 3 --input /tmp/nexus-tech-onboarding-visible-playtest-batch-packet.md
uv run nexus-tech onboarding-visible-playtest-batch-preflight --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --batch-size 6 --frames 1 --output /tmp/nexus-tech-onboarding-visible-batch-preflight.md
uv run nexus-tech onboarding-visible-terminal-batch --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --output /tmp/nexus-tech-onboarding-visible-terminal-batch.md
uv run nexus-tech validate-onboarding-visible-terminal-batch --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --input /tmp/nexus-tech-onboarding-visible-terminal-batch.md
uv run nexus-tech onboarding-visible-terminal-evidence-sheet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --output /tmp/nexus-tech-onboarding-visible-terminal-evidence-sheet.md
uv run nexus-tech validate-onboarding-visible-terminal-evidence-sheet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --input /tmp/nexus-tech-onboarding-visible-terminal-evidence-sheet.md
uv run nexus-tech onboarding-visible-window-evidence-sheet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --window 820x620 --output /tmp/nexus-tech-onboarding-visible-820x620-evidence-sheet.md
uv run nexus-tech validate-onboarding-visible-window-evidence-sheet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --window 820x620 --input /tmp/nexus-tech-onboarding-visible-820x620-evidence-sheet.md
uv run nexus-tech onboarding-visible-window-evidence-sheet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --window 1280x720 --output /tmp/nexus-tech-onboarding-visible-1280x720-evidence-sheet.md
uv run nexus-tech validate-onboarding-visible-window-evidence-sheet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --window 1280x720 --input /tmp/nexus-tech-onboarding-visible-1280x720-evidence-sheet.md
uv run nexus-tech onboarding-visible-window-evidence-sheet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --window 1440x900 --output /tmp/nexus-tech-onboarding-visible-1440x900-evidence-sheet.md
uv run nexus-tech validate-onboarding-visible-window-evidence-sheet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --window 1440x900 --input /tmp/nexus-tech-onboarding-visible-1440x900-evidence-sheet.md
uv run nexus-tech onboarding-visible-evidence-matrix --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --output /tmp/nexus-tech-onboarding-visible-evidence-matrix.md
uv run nexus-tech validate-onboarding-visible-evidence-matrix --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --input /tmp/nexus-tech-onboarding-visible-evidence-matrix.md
uv run nexus-tech onboarding-visible-window-preflight --frames 1 --output /tmp/nexus-tech-onboarding-visible-window-preflight.md
uv run nexus-tech onboarding-visible-manual-session --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --output /tmp/nexus-tech-onboarding-visible-manual-session.md
uv run nexus-tech validate-onboarding-visible-manual-session --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --input /tmp/nexus-tech-onboarding-visible-manual-session.md
uv run nexus-tech onboarding-visible-ux-issue-intake --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --output /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md
uv run nexus-tech validate-onboarding-visible-ux-issue-intake --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --input /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md
uv run nexus-tech record-onboarding-visible-ux-issue --input /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --rank 4 --severity none --issue-notes "Observed title menu in a real window; layout, controls, and motion were readable with no UX issue to escalate." --follow-up none
uv run nexus-tech onboarding-visible-ux-fix-plan --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --input /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --output /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md
uv run nexus-tech validate-onboarding-visible-ux-fix-plan --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --input /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md
uv run nexus-tech onboarding-visible-ux-triage-sprint --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --plan /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md --output /tmp/nexus-tech-onboarding-visible-ux-triage-sprint.md
uv run nexus-tech validate-onboarding-visible-ux-triage-sprint --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --plan /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md --input /tmp/nexus-tech-onboarding-visible-ux-triage-sprint.md
uv run nexus-tech onboarding-visible-ux-triage-next --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --plan /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md --sprint /tmp/nexus-tech-onboarding-visible-ux-triage-sprint.md --output /tmp/nexus-tech-onboarding-visible-ux-triage-next.md
uv run nexus-tech validate-onboarding-visible-ux-triage-next --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --plan /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md --sprint /tmp/nexus-tech-onboarding-visible-ux-triage-sprint.md --input /tmp/nexus-tech-onboarding-visible-ux-triage-next.md
uv run nexus-tech onboarding-visible-ux-recording-queue --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --plan /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md --sprint /tmp/nexus-tech-onboarding-visible-ux-triage-sprint.md --output /tmp/nexus-tech-onboarding-visible-ux-recording-queue.md
uv run nexus-tech validate-onboarding-visible-ux-recording-queue --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --plan /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md --sprint /tmp/nexus-tech-onboarding-visible-ux-triage-sprint.md --input /tmp/nexus-tech-onboarding-visible-ux-recording-queue.md
uv run nexus-tech onboarding-visible-ux-progress --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --plan /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md --sprint /tmp/nexus-tech-onboarding-visible-ux-triage-sprint.md --queue /tmp/nexus-tech-onboarding-visible-ux-recording-queue.md --output /tmp/nexus-tech-onboarding-visible-ux-progress.md
uv run nexus-tech validate-onboarding-visible-ux-progress --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --plan /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md --sprint /tmp/nexus-tech-onboarding-visible-ux-triage-sprint.md --queue /tmp/nexus-tech-onboarding-visible-ux-recording-queue.md --input /tmp/nexus-tech-onboarding-visible-ux-progress.md
uv run nexus-tech onboarding-visible-ux-batch-packet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --plan /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md --sprint /tmp/nexus-tech-onboarding-visible-ux-triage-sprint.md --queue /tmp/nexus-tech-onboarding-visible-ux-recording-queue.md --batch-size 3 --output /tmp/nexus-tech-onboarding-visible-ux-batch-packet.md
uv run nexus-tech validate-onboarding-visible-ux-batch-packet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --plan /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md --sprint /tmp/nexus-tech-onboarding-visible-ux-triage-sprint.md --queue /tmp/nexus-tech-onboarding-visible-ux-recording-queue.md --batch-size 3 --input /tmp/nexus-tech-onboarding-visible-ux-batch-packet.md
uv run nexus-tech onboarding-visible-ux-batch-closeout --batch /tmp/nexus-tech-onboarding-visible-ux-batch-packet.md --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --output /tmp/nexus-tech-onboarding-visible-ux-batch-closeout.md
uv run nexus-tech validate-onboarding-visible-ux-batch-closeout --batch /tmp/nexus-tech-onboarding-visible-ux-batch-packet.md --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --input /tmp/nexus-tech-onboarding-visible-ux-batch-closeout.md
uv run nexus-tech record-onboarding-visible-playtest-route --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --rank 4 --result pass --notes "Observed title menu in a real window; wizard, help, and back/menu affordances were readable and separated."
uv run nexus-tech validate-onboarding-visible-playtest-report --report /tmp/nexus-tech-onboarding-visible-playtest-report.md
```

Show the glossary:

```bash
uv run nexus-tech glossary
```

Validate data catalogs and event wiring:

```bash
uv run nexus-tech validate-content
```

List save slots:

```bash
uv run nexus-tech list-saves
```

List archived completed runs:

```bash
uv run nexus-tech list-archives
```

Compare archived completed runs:

```bash
uv run nexus-tech compare-archives
```

Measure local featured-campaign archive coverage without claiming manual signoff:

```bash
uv run nexus-tech beta-evidence
```

The evidence view also reports authored-route discovery and mastery plus the next route to replay. These archive metrics remain advisory and never complete the human beta gate.

Audit deterministic operating-choice variety without treating autoplay as player evidence:

```bash
uv run nexus-tech decision-quality-audit --runs 3 --turns 12 \
  --seed-base 28600 --output /tmp/nexus-tech-decision-quality.md
```

The default matrix covers the six featured campaigns across Builder, Standard, and Founder. Missing operating-ledger coverage fails the command; repetition and low-variety watches require matching observations from real sessions before any command is consolidated or retuned.

Prepare the next observed session from the current coverage gap:

```bash
.venv313/bin/nexus-tech prepare-beta-playtest-session
```

The preparation command selects the next uncovered featured campaign, allocates unused anonymous session/tester codes, prints the visible launch and observation checklist, and writes `/tmp/nexus-tech-beta-playtest-next.md`. While current-version evidence remains `0/6`, the packet begins with a separate Owner Rehearsal Gate covering New Game, Guided Opening, Pause/Back/Menu/Continue recovery, both campaign choices, guided/full Endgame, Save & Archive, and the direct Progress handoff. Rehearsal and tester launches use different fresh temporary gameplay databases, while recorder/status commands retain the persistent evidence database; this prevents prior Continue, save, or archive state from contaminating a first-time session. Use `--session-db-path` or `--rehearsal-db-path` only for fresh explicit profiles because preparation rejects an existing profile. The rehearsal section has no recorder command and must never be entered as human evidence; the human recorder template remains in its separate post-session section. Generated beta, onboarding, and animation handoffs automatically reuse the `nexus-tech` executable that created them, so a `.venv313/bin/nexus-tech` launch no longer produces unusable `uv run` follow-up commands. Use `--command-prefix` only when the packet will run in another environment. Preparation never copies stored free-form notes, records a session, or treats an owner rehearsal, headless run, test, or screenshot as human evidence. Replace every ALL_CAPS field in its recorder template only after observing a real session.

Review structured evidence from observed real-human beta sessions:

```bash
uv run nexus-tech beta-playtest-status
```

After observing a real session, record it with an anonymous tester code. Replace the notes below with a concrete observation from that session; never include names, emails, local paths, tokens, or secrets:

```bash
uv run nexus-tech record-beta-playtest-session \
  --session-key beta-001 --tester-code T01 \
  --scenario founder_journey --interface 2d --viewport 1280x720 \
  --first-turn-seconds 94 --turn-one pass --pause-back pass \
  --tradeoff pass --act-three pass --blocker none \
  --notes "REPLACE with a concrete observation from the real session" \
  --confirm-human-session
```

The default SQLite file is local and ignored by Git. Session keys must be unique unless `--replace` is supplied for an explicit correction. The status command evaluates only rows recorded for the current game version, requires six distinct anonymous tester codes and all six featured campaigns, and still leaves the final release decision to a human reviewer. The repository currently contains no human-session evidence, so the baseline remains `0/6` rather than an automated pass.

Show archive-driven campaign progression:

```bash
uv run nexus-tech show-progression
```

The terminal dashboard and 2D shell expose a six-step First Archive Mission, while the terminal progression view and 2D Progress board include a six-campaign Route Atlas. Archive-derived progression remains separate from human playtest evidence.

List the archive unlock catalog:

```bash
uv run nexus-tech list-unlocks
```

Check local save integrity after at least one save exists:

```bash
uv run nexus-tech check-saves
```

Print local install, content, and save diagnostics:

```bash
uv run nexus-tech doctor
```

Run the deterministic 2D motion and request-path audit:

```bash
uv run nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 2
```

Run the deterministic 2D visual QA capture audit:

```bash
uv run nexus-tech audit-2d-visual --scenario founder_journey --seed 7
```

For a fast focused visual pass while iterating on a responsive layout, repeat
`--viewport` instead of rendering the full matrix:

```bash
uv run nexus-tech audit-2d-visual --scenario founder_journey --seed 7 \
  --viewport 820x620 --viewport 960x640 --viewport 1440x900 \
  --output-dir /tmp/nexus-tech-visual-audit/focused
```

When `--output-dir` is set, each viewport also writes a
`visual-audit-contact-sheet-WIDTHxHEIGHT.png` that combines every audited scene
for quick manual layout review. Individual captures and the Markdown summary
remain available for detail checks.

Run the responsive layout matrix before manual UI review:

```bash
uv run nexus-tech audit-2d-layout-matrix --scenario founder_journey --seed 7 \
  --viewport 820x620 --viewport 1280x720 \
  --output /tmp/nexus-tech-2d-layout-matrix.md
```

The layout matrix checks target spacing, text fitting, and containment across
full/reduced/off motion modes. It is an automated gate, not a replacement for
visible-window playtest evidence.

Run the combined 2D animation-completeness gate:

```bash
uv run nexus-tech audit-2d-animation --scenario founder_journey --seed 7 --frames 1
```

Run the broader scenario/seed animation readiness matrix before a presentation build:

```bash
uv run nexus-tech audit-2d-animation-matrix --frames 1 --output /tmp/nexus-tech-animation-matrix.md
```

Prepare the manual open-window playtest report from the same broad matrix evidence:

```bash
uv run nexus-tech prepare-2d-animation-playtest --matrix-input /tmp/nexus-tech-animation-matrix.md --output /tmp/nexus-tech-animation-playtest-prep.md
uv run nexus-tech animation-playtest-batch-preflight --output /tmp/nexus-tech-animation-batch-820x620-preflight.md
```

Create the strict manual report draft that the validator expects after the real open-window pass:

```bash
uv run nexus-tech draft-animation-playtest-report --auto-commit --prefill-automated-gates --output /tmp/nexus-tech-animation-playtest-report.md
uv run nexus-tech animation-playtest-status /tmp/nexus-tech-animation-playtest-report.md
uv run nexus-tech animation-playtest-commands --output /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech validate-animation-playtest-commands /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech animation-playtest-plan /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md --output /tmp/nexus-tech-animation-playtest-plan.md
uv run nexus-tech animation-playtest-recorder-queue /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md --output /tmp/nexus-tech-animation-recorder-queue.md
uv run nexus-tech validate-animation-playtest-recorder-queue /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech animation-playtest-next /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech animation-playtest-recorder-next /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech animation-playtest-route-batches /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md --output /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech validate-animation-playtest-route-batches /tmp/nexus-tech-animation-route-batches.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech animation-playtest-batch-next /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech animation-playtest-batch-packet /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md --output /tmp/nexus-tech-animation-next-batch.md --route-batches-output /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech validate-animation-playtest-batch-packet /tmp/nexus-tech-animation-next-batch.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech validate-animation-playtest-plan /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md
uv run nexus-tech prepare-animation-playtest-session --auto-commit --prefill-automated-gates --plan-output /tmp/nexus-tech-animation-playtest-plan.md --recorder-output /tmp/nexus-tech-animation-recorder-queue.md --route-batches-output /tmp/nexus-tech-animation-route-batches.md --next-batch-output /tmp/nexus-tech-animation-next-batch.md --triage-output /tmp/nexus-tech-animation-ui-triage.md --release-gate-output /tmp/nexus-tech-animation-release-gate.md --progress-output /tmp/nexus-tech-animation-progress.md --execution-guide-output /tmp/nexus-tech-animation-execution-guide.md --issue-backlog-output /tmp/nexus-tech-animation-issues.md --sprint-output /tmp/nexus-tech-animation-sprint.md --evidence-sheet-output /tmp/nexus-tech-animation-evidence-sheet.md --handoff-output /tmp/nexus-tech-animation-handoff.md
uv run nexus-tech validate-animation-playtest-session-bundle
uv run nexus-tech validate-animation-playtest-session /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md --route-batches /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech animation-playtest-handoff /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md --route-batches /tmp/nexus-tech-animation-route-batches.md --output /tmp/nexus-tech-animation-handoff.md
uv run nexus-tech animation-playtest-ui-triage /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md --route-batches /tmp/nexus-tech-animation-route-batches.md --output /tmp/nexus-tech-animation-ui-triage.md
uv run nexus-tech validate-animation-playtest-ui-triage /tmp/nexus-tech-animation-ui-triage.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md --route-batches /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech animation-playtest-release-gate /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --output /tmp/nexus-tech-animation-release-gate.md
uv run nexus-tech validate-animation-playtest-release-gate /tmp/nexus-tech-animation-release-gate.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech animation-playtest-progress /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --output /tmp/nexus-tech-animation-progress.md
uv run nexus-tech validate-animation-playtest-progress /tmp/nexus-tech-animation-progress.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech animation-playtest-execution-guide /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --progress-path /tmp/nexus-tech-animation-progress.md --output /tmp/nexus-tech-animation-execution-guide.md
uv run nexus-tech validate-animation-playtest-execution-guide /tmp/nexus-tech-animation-execution-guide.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --progress-path /tmp/nexus-tech-animation-progress.md
uv run nexus-tech animation-playtest-issue-backlog /tmp/nexus-tech-animation-playtest-report.md --output /tmp/nexus-tech-animation-issues.md
uv run nexus-tech validate-animation-playtest-issue-backlog /tmp/nexus-tech-animation-issues.md /tmp/nexus-tech-animation-playtest-report.md
uv run nexus-tech animation-playtest-sprint /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --progress-path /tmp/nexus-tech-animation-progress.md --execution-guide-path /tmp/nexus-tech-animation-execution-guide.md --issue-backlog-path /tmp/nexus-tech-animation-issues.md --output /tmp/nexus-tech-animation-sprint.md
uv run nexus-tech validate-animation-playtest-sprint /tmp/nexus-tech-animation-sprint.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --progress-path /tmp/nexus-tech-animation-progress.md --execution-guide-path /tmp/nexus-tech-animation-execution-guide.md --issue-backlog-path /tmp/nexus-tech-animation-issues.md
uv run nexus-tech animation-playtest-evidence-sheet /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --progress-path /tmp/nexus-tech-animation-progress.md --execution-guide-path /tmp/nexus-tech-animation-execution-guide.md --issue-backlog-path /tmp/nexus-tech-animation-issues.md --sprint-path /tmp/nexus-tech-animation-sprint.md --output /tmp/nexus-tech-animation-evidence-sheet.md
uv run nexus-tech validate-animation-playtest-evidence-sheet /tmp/nexus-tech-animation-evidence-sheet.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --progress-path /tmp/nexus-tech-animation-progress.md --execution-guide-path /tmp/nexus-tech-animation-execution-guide.md --issue-backlog-path /tmp/nexus-tech-animation-issues.md --sprint-path /tmp/nexus-tech-animation-sprint.md
```

If `uv` is not installed in the local shell, keep the same workflow but add
`--command-prefix .venv313/bin/nexus-tech` to `animation-playtest-commands`,
`validate-animation-playtest-commands`, `animation-playtest-plan`,
`animation-playtest-next`, `animation-playtest-recorder-queue`,
`animation-playtest-batch-next`, `animation-playtest-batch-packet`,
`validate-animation-playtest-batch-packet`,
`validate-animation-playtest-recorder-queue`, `animation-playtest-recorder-next`,
`animation-playtest-route-batches`, `validate-animation-playtest-route-batches`,
`animation-playtest-ui-triage`, `validate-animation-playtest-ui-triage`,
`animation-playtest-release-gate`, `validate-animation-playtest-release-gate`,
`animation-playtest-progress`, `validate-animation-playtest-progress`,
`animation-playtest-execution-guide`, `validate-animation-playtest-execution-guide`,
`animation-playtest-issue-backlog`, `validate-animation-playtest-issue-backlog`,
`animation-playtest-sprint`, `validate-animation-playtest-sprint`,
`animation-playtest-evidence-sheet`, `validate-animation-playtest-evidence-sheet`,
`animation-playtest-batch-preflight`, `validate-animation-playtest-plan`,
`prepare-animation-playtest-session`,
`validate-animation-playtest-session-bundle`,
`validate-animation-playtest-session`, and `animation-playtest-handoff` so
generated visible-window commands match the local virtualenv launcher.

The exported command queue, animation playtest plan, recorder queue, session
validator, route-batch plan, and handoff sheet include validated route evidence
prompts for all 18 required menu/play window and motion runs.
Use `--auto-commit` on the report/session draft commands so the manual QA packet
records the current short Git SHA; pass `--commit <sha>` only when testing a
specific build artifact that differs from the checked-out workspace.
`animation-playtest-next` and `animation-playtest-handoff` surface the next
visible command plus matching recorder command, while
`animation-playtest-route-batches` groups the visible pass into one batch per
target window, `animation-playtest-batch-next` prints the first unfinished
window, `animation-playtest-batch-packet` exports that focused packet, and
`validate-animation-playtest-batch-packet` blocks stale focused packets before
manual QA starts recording evidence. Route-batch validation still blocks stale
route-batch artifacts so manual QA can work through the matrix without losing
recorder commands between command generation and final signoff. Each route batch now
exports preflight checks, an evidence checklist, copy-paste command blocks, and
ordered operator steps that alternate visible-window launches with the matching
recorder command, so testers confirm the target window, pending modes, required
terms, and recorder timing before choosing pass, watch, or fail from observed
game-window behavior. The same batch
artifact also includes a result decision guide before the recorder placeholders,
making it explicit when to keep `--result pass` or change the command to
`--result watch` or `--result fail`. It now also includes defect-trigger rows
for layout containment, navigation recovery, motion readability, feedback
clarity, and evidence quality, plus a defect intake template for severity,
reproduction, evidence, recorder action, and follow-up ownership. That keeps
watch/fail notes tied to the actual blocker instead of becoming generic polish
comments. Focused batch and next-step handoff packets also print safe renderer
preview commands for game-only PNG captures and layout matrices by
window/motion pair, so layout checks can happen before manual visible-window
notes without taking full-desktop screenshots or replacing real evidence. A
closure checklist then requires route/window recorders, defect
classification, artifact refresh, route-batch validation, and status review
before testers move to the next target window. Post-recording refresh and
validation commands let testers confirm the batch and report status moved after
evidence is recorded.
`animation-playtest-ui-triage` turns the current manual gaps into P0/P1/P2
layout, typography, control, scene, motion, and signoff lanes so UI polish work
does not get mixed into generic notes before the final validator pass.
`animation-playtest-release-gate` then combines the session artifacts, UI triage
artifact, P0/P1 lanes, and final report into one go/no-go gate; it stays
`manual-required` until real visible-window evidence clears the report. The gate
also carries the next visible-window command and matching recorder command so a
tester can continue from the same artifact.
`animation-playtest-progress` adds a validated progress board for completion
percentage, open manual lanes, P0/P1 status, and the same next manual action; it
is advisory only and does not record tester evidence.
`animation-playtest-execution-guide` converts that board plus the recorder queue
into a validated operator loop with visible command, evidence prompt, required
terms, and recorder command for each remaining step. It still requires real
tester observations before any recorder command is valid.
`animation-playtest-issue-backlog` converts the current manual report into a
validated P0/P1/P2 fix queue, so fail/watch rows and missing evidence become
explicit follow-up work before the next release-candidate pass.
`animation-playtest-sprint` combines the next open observation rows with the
current P0/P1 blockers into a focused work packet for one manual QA pass. It
labels report-field blockers as post-observation signoff work until visible
evidence exists, includes a manual observation checklist for layout, navigation,
typography, motion, and evidence wording, adds manual execution batches for
artifact refresh, 820x620 layout, 960x640 recovery controls, 1440x900 motion
readability, and report closure, adds a defect intake table for
P0/P1/P2 UI or animation findings, adds a dedicated layout repair pass for
responsive frames, button grids, text containment, navigation affordance, and
motion separation, maps those layout checks to the exact window/control recorder
commands that must update the report, adds navigation recovery drills for pause,
resume, back/escape, menu return, and help/hover paths, maps those drills to the
exact control recorder commands that must update the report, includes exit
criteria for closing the pass, adds evidence capture prompts for every visible
step, provides note templates for pass/watch/fail evidence, keeps recorder
placeholders invalid until the visible command has been observed, and
`validate-animation-playtest-sprint` confirms the packet still matches the
current guide and backlog. The CLI output also prints the ordered execution
batch table directly, so the tester can see artifact refresh, 820x620 layout,
960x640 recovery, 1440x900 motion, and closure steps without opening the
Markdown packet first. The sprint packet and CLI also surface the next visible
command plus matching recorder command as `Next Sprint Action`, so the tester
can start the first real observation without hunting through the full queue.
`Next Sprint Copy Commands` repeats those commands as full copy-paste lines and
keeps the recorder placeholder explicit until real visible-window notes replace
it.
`animation-playtest-evidence-sheet` turns the focused sprint rows into a
validated capture worksheet with pass/watch/fail result choices, required note
terms, deterministic screenshot/clip filenames, recorder commands, and follow-up
columns for each live observation. It is generated by
`prepare-animation-playtest-session` and checked by
`validate-animation-playtest-evidence-sheet`, but it remains a worksheet only:
the visible game window still has to be observed before any recorder command is
valid.
`validate-animation-playtest-session-bundle` runs every generated artifact
validator plus handoff sheet checks in one command, so CI and local release
preflight fail if the manual report bundle is stale, incomplete, or missing the
focused next visible-window action before artifacts are uploaded.
`animation-playtest-batch-preflight` runs the first 820x620 batch in headless
mode across menu/play plus full, reduced, and off motion modes and writes a
Markdown preflight artifact. It only proves the launchers and focused batch
commands still run; visible-window tester notes are still required before any
route recorder command is valid.
`audit-2d-layout-matrix` runs the responsive layout safety pass across selected
viewports and full/reduced/off motion modes, then writes the spacing/text-fit
artifact that should be checked before visible-window layout review begins.
The plan also includes a validated `Manual Evidence Checklist` for the window
matrix, route notes, controls, scenes, game feel, and signoff fields so the
non-route manual evidence cannot be dropped from handoff notes.
It now also exports a validated `Manual Runbook` with artifact refresh, visible
window execution, evidence-fill, and final validator exit criteria, so handoff
notes cannot lose the order of work before manual QA starts.
The strict manual report also includes matching `Visible Route Evidence` rows;
`validate-animation-playtest-report` fails until all 18 rows are `pass` with
observed notes from the actual visible-window runs.
Those notes must be target-specific: menu rows cover title, wizard, save,
archive, meta, hover, and text checks; play rows cover dashboard, action,
pending, inspector, endgame, summary, pause, and motion checks.
The same final validator also checks concrete observed terms in window matrix,
control, scene, and game-feel evidence notes, so broad notes cannot pass
non-route manual signoff rows either.
The generated manual report draft now prints those required terms in each
affected row so testers can fill evidence notes without guessing the validator
contract. Final validation rejects that prompt text if it is left in place, so
completed reports must replace it with real observations from visible runs.
For a `pass` release decision, the same validator also requires release blocker
fields and required fixes to be clear, and the recorded validator result must be
passing.
Completed reports must keep the generated section structure, including build,
automated gates, window matrix, visible route evidence, controls, scenes, game
feel, release blockers, and decision sections.
They must also remove leftover draft warning copy and `owner/date if not pass`
follow-up placeholders before final validation.

The visual audit output also includes a deterministic baseline signature, and you can add `--output-dir /tmp/nexus-tech-visual-audit` when you want PNG captures plus `visual-audit-summary.md` for manual review without writing generated images into the repository. GitHub Actions uploads the full/off visual captures and summaries as `nexus-tech-2d-visual-audit`, uploads the broad animation matrix report as `nexus-tech-2d-animation-matrix`, uploads the window/motion checklist report as `nexus-tech-2d-animation-playtest-prep`, uploads the focused 820x620 headless batch preflight as `nexus-tech-820x620-animation-batch-preflight`, validates the complete manual QA session bundle with `validate-animation-playtest-session-bundle`, and uploads the manual report, command queue, route batches, focused next-batch packet, triage, release gate, progress board, execution guide, backlog, sprint, evidence sheet, and handoff as `nexus-tech-manual-animation-session` after the CI animation gates.

Use `--motion-mode reduced` or `--motion-mode off` on `play-2d`, `menu-2d`, `audit-2d-motion`, and `audit-2d-visual` when you want quieter highlight, entity, action-feedback, late-game choreography, pending-preview, summary-lane, and scene-transition animation while keeping the same gameplay state and controls. Use `--window-size 820x620`, `--window-size 960x640`, or `--window-size 1440x900` on visible `play-2d` and `menu-2d` runs to match the manual animation window matrix exactly. Use repeated `audit-2d-visual --viewport WIDTHxHEIGHT` values to capture only the responsive sizes under review; omit the option for the full CI matrix.

Use `docs/OPEN_WINDOW_ANIMATION_PLAYTEST.md` and `docs/ANIMATION_PLAYTEST_REPORT_TEMPLATE.md` for the manual open-window pass that checks compact, small, and presentation windows across full, reduced, and off motion modes after the automated gates pass.
Completed manual reports must include specific observed evidence in the required notes cells; generic notes such as `ok`, `clear`, `readable`, `stable`, or `none` fail `validate-animation-playtest-report`.

Rename a save slot:

```bash
uv run nexus-tech rename-save --slot active --to-slot archive
```

Delete a save slot:

```bash
uv run nexus-tech delete-save --slot archive --yes
```

## 🕹️ How to Play

The core loop is simple:

1. Follow the Focus View sequence: read the Act Objective and Plan progress, take or inspect the Recommended Move, then review the End Turn Check and delayed follow-on.
2. Spend action points on product or team decisions.
3. End the turn to resolve revenue, costs, growth, churn, burnout, and event outcomes.
4. Save locally and continue the run later if needed; after a completed run, choose `Save & Archive` to record route mastery and progression.

The HUD also tracks the full First Archive Mission: Guided Opening, Commitment, Consequence, Enter Endgame, Finish the Run, and Save & Archive. This journey indicator is guidance only and is derived from existing state, so older saves remain compatible.

If you are new to the game, run `nexus-tech guide`, `nexus-tech tutorial`, or use the in-session Guided Opening panel to follow Coach Move, Spend AP, and End Turn without exposing internal command ids. Coach executes the current recommended move instead of opening a read-only hint.

For the animated frontend shell, run `nexus-tech play-2d --scenario founder_journey --seed 7` or open the full menu flow with `nexus-tech menu-2d`; add `--motion-mode reduced` or `--motion-mode off` if you want quieter highlight, entity, actor, action-feedback, and transition animation. From the title scene you can start a fresh run with the wizard, manage save slots, inspect archives, open the progression board, or press `7` for Settings before entering play. Inside a run, `Choose This Turn` keeps one green `C Recommended` route ahead of two non-duplicated alternatives, Report, Save, and End Turn. You can click the Recommended Move and End Turn Check cards directly, plus product cards, modal options, deep-dive panel buttons, and the action bar, or use keys like `Tab`, `C`, `N`, `1`, `2`, `3`, `4`, `5`, `6`, `7`, `8`, `V`, `I`, `Q`, `F`, `M`, `D`, `H`, `A`, `O`, `Y`, `R`, `B`, `U`, `L`, `G`, `Space`, `S`, `P`, `Esc`, and `F1`. `V` toggles guided and full Endgame actions while that board is open. `P` opens Pause with Resume, Save, Menu, Settings, and Quit controls; `T` opens Settings while paused; and `Esc` returns from Settings to Pause before resuming the run. `M` saves and returns only when the run came from the title shell; direct play marks Menu unavailable and keeps `M` inert, while `Q` remains explicit quit. Action and impact cues use product names and metric labels rather than exposing internal identifiers. After a title-shell run uses `Save & Archive`, the completed review keeps Back/Menu available and adds `6 Open Progress` for a direct Route Atlas and next-route handoff. The shared responsive frame reserves navigation, header, content, and footer regions across title, run, review, and turn-summary scenes. The live run retains its shape-based entity motion, deterministic shape-sprite actors, command feedback, scene transitions, compact action copy, adaptive feed pacing, staged turn summaries, endgame cockpit, and remembered inspector controls. If a button is disabled, the 2D shell still tells you exactly which prerequisite is missing before you waste the click.

For a larger, high-contrast 2D profile, use Settings or append `--ui-scale large --contrast-mode high` to a 2D launch command. Settings changes persist in the local SQLite profile; keys `1` through `4` cycle text, contrast, motion, and action loadout. CLI flags override display settings for the current launch. When no save exists, Title Menu and Quick Start emphasize New Game and show Continue as unavailable; returning players retain Continue as the primary route. Their compact header reserves separate subtitle and archive-progress lanes so status copy stays clear of the panel frame. Title Menu, Turn Summary, and Review keep each contextual action in one visible owner region instead of repeating the same click target in both navigation and content. One pure scene-chrome policy keeps content, footer, top-rail, and Pause-overlay ownership mutually exclusive. The live run still reserves its top rail for Pause, Back, More, and Help recovery routes. The Report inspector and terminal report include a Decision Ledger with immediate impact, end-turn follow-on timing, and a derived Decision Pattern. Compact Focus View arranges its six preserved actions in two balanced rows, while wider layouts keep one six-action row. First-turn header, checkpoint, and footer instructions switch to complete short forms when their measured lane is narrow. Arbitrary key remapping is not included in 0.314.0; the documented keyboard bindings remain fixed for this release.

Difficulty guidance:

- `builder`: safest learning mode, good for understanding the core loop and preview panels
- `standard`: default pressure profile, expects balanced cash, support, and governance play
- `founder`: concentrated pressure mode where missed controls compound quickly

Typical decisions include:

- which product should get attention this turn
- which customer segment each product should target
- which budget stance fits the current runway and growth pressure
- whether to push features or stabilize quality
- when technical debt has become too expensive to ignore
- which roadmap focus should shape the next few turns
- how the current market cycle changes the right move
- whether competitor pressure means you should defend, reposition, or consolidate
- whether key accounts need product stability before the next renewal cycle
- when debt is useful fuel versus when it starts to distort the company
- whether dilution and investor pressure are worth the extra runway
- when to hire, assign, rest, or remove team members
- which scenario opening creates the best long-term position
- how to survive cash pressure while still building growth
- when the company is ready to push for a winning end-state instead of just surviving

## 🧪 Testing

Run the test suite:

```bash
uv run pytest
```

Run the local CI-equivalent checks:

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest -q
uv run nexus-tech validate-content
uv run nexus-tech campaign-readiness --runs 3 --turns 20 --seed-base 28500 --output /tmp/nexus-tech-campaign-readiness.md
uv run nexus-tech decision-quality-audit --runs 3 --turns 12 --seed-base 28600 --output /tmp/nexus-tech-decision-quality.md
uv run nexus-tech audit-onboarding-flow --output /tmp/nexus-tech-onboarding-flow-audit.md
uv run nexus-tech onboarding-visible-playtest-packet --output /tmp/nexus-tech-onboarding-visible-playtest.md
uv run nexus-tech validate-onboarding-visible-playtest-packet --input /tmp/nexus-tech-onboarding-visible-playtest.md
uv run nexus-tech onboarding-visible-playtest-report --input /tmp/nexus-tech-onboarding-visible-playtest.md --output /tmp/nexus-tech-onboarding-visible-playtest-report.md
uv run nexus-tech onboarding-visible-playtest-status --report /tmp/nexus-tech-onboarding-visible-playtest-report.md
uv run nexus-tech onboarding-visible-playtest-next --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --output /tmp/nexus-tech-onboarding-visible-playtest-next.md
uv run nexus-tech validate-onboarding-visible-playtest-next --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --input /tmp/nexus-tech-onboarding-visible-playtest-next.md
uv run nexus-tech onboarding-visible-playtest-batch-packet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --batch-size 3 --output /tmp/nexus-tech-onboarding-visible-playtest-batch-packet.md
uv run nexus-tech validate-onboarding-visible-playtest-batch-packet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --batch-size 3 --input /tmp/nexus-tech-onboarding-visible-playtest-batch-packet.md
uv run nexus-tech onboarding-visible-playtest-batch-preflight --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --batch-size 6 --frames 1 --output /tmp/nexus-tech-onboarding-visible-batch-preflight.md
uv run nexus-tech onboarding-visible-terminal-batch --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --output /tmp/nexus-tech-onboarding-visible-terminal-batch.md
uv run nexus-tech validate-onboarding-visible-terminal-batch --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --input /tmp/nexus-tech-onboarding-visible-terminal-batch.md
uv run nexus-tech onboarding-visible-terminal-evidence-sheet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --output /tmp/nexus-tech-onboarding-visible-terminal-evidence-sheet.md
uv run nexus-tech validate-onboarding-visible-terminal-evidence-sheet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --input /tmp/nexus-tech-onboarding-visible-terminal-evidence-sheet.md
uv run nexus-tech onboarding-visible-window-evidence-sheet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --window 820x620 --output /tmp/nexus-tech-onboarding-visible-820x620-evidence-sheet.md
uv run nexus-tech validate-onboarding-visible-window-evidence-sheet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --window 820x620 --input /tmp/nexus-tech-onboarding-visible-820x620-evidence-sheet.md
uv run nexus-tech onboarding-visible-window-evidence-sheet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --window 1280x720 --output /tmp/nexus-tech-onboarding-visible-1280x720-evidence-sheet.md
uv run nexus-tech validate-onboarding-visible-window-evidence-sheet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --window 1280x720 --input /tmp/nexus-tech-onboarding-visible-1280x720-evidence-sheet.md
uv run nexus-tech onboarding-visible-window-evidence-sheet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --window 1440x900 --output /tmp/nexus-tech-onboarding-visible-1440x900-evidence-sheet.md
uv run nexus-tech validate-onboarding-visible-window-evidence-sheet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --window 1440x900 --input /tmp/nexus-tech-onboarding-visible-1440x900-evidence-sheet.md
uv run nexus-tech onboarding-visible-evidence-matrix --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --output /tmp/nexus-tech-onboarding-visible-evidence-matrix.md
uv run nexus-tech validate-onboarding-visible-evidence-matrix --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --input /tmp/nexus-tech-onboarding-visible-evidence-matrix.md
uv run nexus-tech onboarding-visible-window-preflight --frames 1 --output /tmp/nexus-tech-onboarding-visible-window-preflight.md
uv run nexus-tech onboarding-visible-manual-session --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --output /tmp/nexus-tech-onboarding-visible-manual-session.md
uv run nexus-tech validate-onboarding-visible-manual-session --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --input /tmp/nexus-tech-onboarding-visible-manual-session.md
uv run nexus-tech onboarding-visible-ux-issue-intake --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --output /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md
uv run nexus-tech validate-onboarding-visible-ux-issue-intake --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --input /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md
uv run nexus-tech record-onboarding-visible-ux-issue --input /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --rank 4 --severity none --issue-notes "Observed title menu in a real window; layout, controls, and motion were readable with no UX issue to escalate." --follow-up none
uv run nexus-tech onboarding-visible-ux-fix-plan --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --input /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --output /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md
uv run nexus-tech validate-onboarding-visible-ux-fix-plan --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --input /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md
uv run nexus-tech onboarding-visible-ux-triage-sprint --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --plan /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md --output /tmp/nexus-tech-onboarding-visible-ux-triage-sprint.md
uv run nexus-tech validate-onboarding-visible-ux-triage-sprint --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --plan /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md --input /tmp/nexus-tech-onboarding-visible-ux-triage-sprint.md
uv run nexus-tech onboarding-visible-ux-triage-next --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --plan /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md --sprint /tmp/nexus-tech-onboarding-visible-ux-triage-sprint.md --output /tmp/nexus-tech-onboarding-visible-ux-triage-next.md
uv run nexus-tech validate-onboarding-visible-ux-triage-next --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --plan /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md --sprint /tmp/nexus-tech-onboarding-visible-ux-triage-sprint.md --input /tmp/nexus-tech-onboarding-visible-ux-triage-next.md
uv run nexus-tech onboarding-visible-ux-recording-queue --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --plan /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md --sprint /tmp/nexus-tech-onboarding-visible-ux-triage-sprint.md --output /tmp/nexus-tech-onboarding-visible-ux-recording-queue.md
uv run nexus-tech validate-onboarding-visible-ux-recording-queue --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --plan /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md --sprint /tmp/nexus-tech-onboarding-visible-ux-triage-sprint.md --input /tmp/nexus-tech-onboarding-visible-ux-recording-queue.md
uv run nexus-tech onboarding-visible-ux-progress --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --plan /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md --sprint /tmp/nexus-tech-onboarding-visible-ux-triage-sprint.md --queue /tmp/nexus-tech-onboarding-visible-ux-recording-queue.md --output /tmp/nexus-tech-onboarding-visible-ux-progress.md
uv run nexus-tech validate-onboarding-visible-ux-progress --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --plan /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md --sprint /tmp/nexus-tech-onboarding-visible-ux-triage-sprint.md --queue /tmp/nexus-tech-onboarding-visible-ux-recording-queue.md --input /tmp/nexus-tech-onboarding-visible-ux-progress.md
uv run nexus-tech onboarding-visible-ux-batch-packet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --plan /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md --sprint /tmp/nexus-tech-onboarding-visible-ux-triage-sprint.md --queue /tmp/nexus-tech-onboarding-visible-ux-recording-queue.md --batch-size 3 --output /tmp/nexus-tech-onboarding-visible-ux-batch-packet.md
uv run nexus-tech validate-onboarding-visible-ux-batch-packet --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --plan /tmp/nexus-tech-onboarding-visible-ux-fix-plan.md --sprint /tmp/nexus-tech-onboarding-visible-ux-triage-sprint.md --queue /tmp/nexus-tech-onboarding-visible-ux-recording-queue.md --batch-size 3 --input /tmp/nexus-tech-onboarding-visible-ux-batch-packet.md
uv run nexus-tech onboarding-visible-ux-batch-closeout --batch /tmp/nexus-tech-onboarding-visible-ux-batch-packet.md --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --output /tmp/nexus-tech-onboarding-visible-ux-batch-closeout.md
uv run nexus-tech validate-onboarding-visible-ux-batch-closeout --batch /tmp/nexus-tech-onboarding-visible-ux-batch-packet.md --report /tmp/nexus-tech-onboarding-visible-playtest-report.md --intake /tmp/nexus-tech-onboarding-visible-ux-issue-intake.md --input /tmp/nexus-tech-onboarding-visible-ux-batch-closeout.md
uv run nexus-tech validate-onboarding-visible-playtest-report --report /tmp/nexus-tech-onboarding-visible-playtest-report.md
uv run nexus-tech play-2d --scenario founder_journey --seed 7 --headless --max-frames 2 --motion-mode reduced
uv run nexus-tech menu-2d --headless --max-frames 2 --motion-mode reduced
uv run nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 2
uv run nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 1 --motion-mode reduced
uv run nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 1 --motion-mode off
uv run nexus-tech audit-2d-visual --scenario founder_journey --seed 7
uv run nexus-tech audit-2d-visual --scenario founder_journey --seed 7 --motion-mode off
uv run nexus-tech audit-2d-layout-matrix --scenario founder_journey --seed 7 --viewport 820x620 --viewport 1280x720 --output /tmp/nexus-tech-2d-layout-matrix.md
uv run nexus-tech audit-2d-animation --scenario founder_journey --seed 7 --frames 1
uv run nexus-tech audit-2d-animation-matrix --frames 1 --output /tmp/nexus-tech-animation-matrix.md
uv run nexus-tech prepare-2d-animation-playtest --matrix-input /tmp/nexus-tech-animation-matrix.md --output /tmp/nexus-tech-animation-playtest-prep.md
uv run nexus-tech animation-playtest-batch-preflight --output /tmp/nexus-tech-animation-batch-820x620-preflight.md
uv run nexus-tech draft-animation-playtest-report --auto-commit --prefill-automated-gates --output /tmp/nexus-tech-animation-playtest-report.md
uv run nexus-tech animation-playtest-status /tmp/nexus-tech-animation-playtest-report.md
uv run nexus-tech animation-playtest-commands --output /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech validate-animation-playtest-commands /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech animation-playtest-plan /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md --output /tmp/nexus-tech-animation-playtest-plan.md
uv run nexus-tech animation-playtest-recorder-queue /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md --output /tmp/nexus-tech-animation-recorder-queue.md
uv run nexus-tech validate-animation-playtest-recorder-queue /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech animation-playtest-next /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech animation-playtest-recorder-next /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech animation-playtest-route-batches /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md --output /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech validate-animation-playtest-route-batches /tmp/nexus-tech-animation-route-batches.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech animation-playtest-batch-next /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md
uv run nexus-tech animation-playtest-batch-packet /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md --output /tmp/nexus-tech-animation-next-batch.md --route-batches-output /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech validate-animation-playtest-batch-packet /tmp/nexus-tech-animation-next-batch.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech validate-animation-playtest-plan /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md
uv run nexus-tech prepare-animation-playtest-session --auto-commit --prefill-automated-gates --plan-output /tmp/nexus-tech-animation-playtest-plan.md --recorder-output /tmp/nexus-tech-animation-recorder-queue.md --route-batches-output /tmp/nexus-tech-animation-route-batches.md --next-batch-output /tmp/nexus-tech-animation-next-batch.md --triage-output /tmp/nexus-tech-animation-ui-triage.md --release-gate-output /tmp/nexus-tech-animation-release-gate.md --progress-output /tmp/nexus-tech-animation-progress.md --execution-guide-output /tmp/nexus-tech-animation-execution-guide.md --issue-backlog-output /tmp/nexus-tech-animation-issues.md --sprint-output /tmp/nexus-tech-animation-sprint.md --evidence-sheet-output /tmp/nexus-tech-animation-evidence-sheet.md --handoff-output /tmp/nexus-tech-animation-handoff.md
uv run nexus-tech validate-animation-playtest-session-bundle
uv run nexus-tech validate-animation-playtest-session /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md --route-batches /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech animation-playtest-handoff /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md --route-batches /tmp/nexus-tech-animation-route-batches.md --output /tmp/nexus-tech-animation-handoff.md
uv run nexus-tech animation-playtest-ui-triage /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md --route-batches /tmp/nexus-tech-animation-route-batches.md --output /tmp/nexus-tech-animation-ui-triage.md
uv run nexus-tech validate-animation-playtest-ui-triage /tmp/nexus-tech-animation-ui-triage.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md --route-batches /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech animation-playtest-release-gate /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --output /tmp/nexus-tech-animation-release-gate.md
uv run nexus-tech validate-animation-playtest-release-gate /tmp/nexus-tech-animation-release-gate.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech animation-playtest-progress /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --output /tmp/nexus-tech-animation-progress.md
uv run nexus-tech validate-animation-playtest-progress /tmp/nexus-tech-animation-progress.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md
uv run nexus-tech animation-playtest-execution-guide /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --progress-path /tmp/nexus-tech-animation-progress.md --output /tmp/nexus-tech-animation-execution-guide.md
uv run nexus-tech validate-animation-playtest-execution-guide /tmp/nexus-tech-animation-execution-guide.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --progress-path /tmp/nexus-tech-animation-progress.md
uv run nexus-tech animation-playtest-issue-backlog /tmp/nexus-tech-animation-playtest-report.md --output /tmp/nexus-tech-animation-issues.md
uv run nexus-tech validate-animation-playtest-issue-backlog /tmp/nexus-tech-animation-issues.md /tmp/nexus-tech-animation-playtest-report.md
uv run nexus-tech animation-playtest-sprint /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --progress-path /tmp/nexus-tech-animation-progress.md --execution-guide-path /tmp/nexus-tech-animation-execution-guide.md --issue-backlog-path /tmp/nexus-tech-animation-issues.md --output /tmp/nexus-tech-animation-sprint.md
uv run nexus-tech validate-animation-playtest-sprint /tmp/nexus-tech-animation-sprint.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --progress-path /tmp/nexus-tech-animation-progress.md --execution-guide-path /tmp/nexus-tech-animation-execution-guide.md --issue-backlog-path /tmp/nexus-tech-animation-issues.md
uv run nexus-tech animation-playtest-evidence-sheet /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --progress-path /tmp/nexus-tech-animation-progress.md --execution-guide-path /tmp/nexus-tech-animation-execution-guide.md --issue-backlog-path /tmp/nexus-tech-animation-issues.md --sprint-path /tmp/nexus-tech-animation-sprint.md --output /tmp/nexus-tech-animation-evidence-sheet.md
uv run nexus-tech validate-animation-playtest-evidence-sheet /tmp/nexus-tech-animation-evidence-sheet.md /tmp/nexus-tech-animation-playtest-report.md /tmp/nexus-tech-animation-playtest-commands.md /tmp/nexus-tech-animation-playtest-plan.md /tmp/nexus-tech-animation-recorder-queue.md /tmp/nexus-tech-animation-ui-triage.md --route-batches /tmp/nexus-tech-animation-route-batches.md --progress-path /tmp/nexus-tech-animation-progress.md --execution-guide-path /tmp/nexus-tech-animation-execution-guide.md --issue-backlog-path /tmp/nexus-tech-animation-issues.md --sprint-path /tmp/nexus-tech-animation-sprint.md
```

When `uv` is unavailable, rerun the manual playtest artifact commands with
`--command-prefix .venv313/bin/nexus-tech` so validators expect the same command
prefix printed in the queue.

## 🧹 Linting and Formatting

Check the codebase:

```bash
uv run ruff check src tests
```

Format the project:

```bash
uv run ruff format src tests
```

## 🗂️ Project Structure

- `docs/ARCHITECTURE.md`
  Short architecture overview and system boundaries.

- `docs/BALANCING.md`
  Balance workflow, tuning commands, and safe content expansion notes.

- `docs/DEMO_SCRIPT.md`
  Live presentation flow, demo commands, and talking points.

- `docs/RELEASE_CHECKLIST.md`
  Release verification steps, version checks, and scope guardrails.

- `src/nexus_tech/domain`
  Core validated entities, money helpers, and shared constants.

- `src/nexus_tech/simulation`
  Economy, product progression, growth, team systems, turn resolution, scenario bootstrap, and event logic.

- `src/nexus_tech/content`
  JSON-backed scenario definitions and product templates.

- `src/nexus_tech/persistence`
  SQLite schema, repositories, and save/load coordination.

- `src/nexus_tech/presentation`
  Rich-based terminal UI rendering.

- `src/nexus_tech/cli.py`
  Typer commands and interactive terminal session flow.

## 📌 Project Notes

- The project is intentionally **offline-first** and **local-only**
- Save data is stored in `nexus-tech.db` by default
- `--seed` is useful for repeatable demos and deterministic test scenarios
- `--scenario` selects a starting setup, while `list-scenarios` shows the current catalog
- Market cycles, quarter plans, competitor rosters, key accounts, debt, dilution, board confidence, and funding history are part of the persisted run state
- The focus is on correctness, stability, maintainability, and presentation quality

## 📄 License

MIT License. See `LICENSE`.
