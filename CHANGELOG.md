# Changelog

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
