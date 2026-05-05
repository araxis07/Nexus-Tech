# Changelog

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
