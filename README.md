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
- Expose an explicit unlock catalog with reward ids for archive-driven scenarios, templates, rivals, tools, and late-game insight lenses
- Apply archive-driven unlocks to real gameplay entry points so locked reward starts cannot be launched until the local archive progression earns them
- Compare archived runs directly through score, cash, offer, grade, and outcome coverage so late-game experimentation becomes easier to review
- Surface path-specific archive leaders, badge coverage, reward mix, and next-gap guidance so the meta layer can point toward what the player has not yet mastered

### 💾 Local Save / Load

- Save and load runs locally with SQLite
- Resume the latest save slot
- List, rename, and delete save slots directly from the CLI
- Archive completed runs and inspect them later through `list-archives`
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
- Persist roadmap state, market cycle, quarter plan, finance state, funding history, competitors, key accounts, product targeting, event history, team assignments, exit summaries, and turn history
- Persist partnerships and capital-plan posture so channel strategy and reserve discipline survive save/load boundaries
- Persist release plans, sales deals, roadmap projects, competitor intel, scenario objectives, and hiring traits
- Use SQLite schema versioning and additive migrations to keep local save files upgradeable
- Keep the entire project offline and self-contained

### 🖥️ Presentation and CLI

- Rich-powered dashboard panels, tables, summaries, and event notifications
- Lightweight `pygame-ce` 2D dashboard frontend with animated bars, product cards, action/context pickers, clickable controls, a full title/new-game wizard flow, save-slot management, deep-dive overlays, inspector overlays, and review scenes
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
- Built-in `play-2d`, `load-game-2d`, `continue-last-game-2d`, and `menu-2d` commands for the animated frontend shell, now with a new-game wizard, save-slot management, archive browsing, inspector overlays, disabled-action explanations, and post-turn summaries
- In-game reporting view for score, valuation, quarter-plan progress, competitor watch, and recent turn history
- Deterministic `simulate-balance` batch runs for tuning scenarios, difficulties, and goals without playing by hand
- Deterministic `compare-balance` scenario rankings for side-by-side tuning across multiple openings
- Deterministic `balance-matrix` runs to compare the same scenarios across every difficulty profile
- Deterministic `balance-audit` runs to flag rough scenario/difficulty combinations for tuning
- Deterministic `export-balance-csv` output for external review of scenario and difficulty balance
- Deterministic `balance-report` output for Markdown tuning reports that combine matrix, audit data, threshold gates, and top tuning priorities
- Autoplay balance sweeps now degrade more gracefully around invalid funding/event branches so tuning runs fail as balance signals instead of crashing on input policy mistakes
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
- GitHub Actions CI to run lint and tests on pushes and pull requests

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

Show archive-driven campaign progression:

```bash
uv run nexus-tech show-progression
```

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

1. Review Turn Coach, Risk Forecast, End-Turn Preview, and Difficulty Profile before spending actions.
2. Spend action points on product or team decisions.
3. End the turn to resolve revenue, costs, growth, churn, burnout, and event outcomes.
4. Save locally and continue the run later if needed.

If you are new to the game, run `nexus-tech guide`, `nexus-tech tutorial`, or use the in-session Guided Opening panel to get a compact opening checklist.

For the animated frontend shell, run `nexus-tech play-2d --scenario founder_journey --seed 7` or open the full menu flow with `nexus-tech menu-2d`. From the title scene you can start a fresh run with the wizard, manage save slots, or inspect archives before entering play. Inside a run you can click product cards, coach cards, modal options, deep-dive panel buttons, and the action bar directly, or use keys like `Tab`, `C`, `N`, `1`, `2`, `3`, `4`, `5`, `6`, `7`, `Q`, `F`, `M`, `D`, `H`, `A`, `Y`, `R`, `B`, `U`, `L`, `G`, `Space`, and `S`. Review commands now open structured inspectors for finance, customers, partnerships, board state, pipeline, and report history. If a button is disabled, the 2D shell now tells you exactly which prerequisite is missing before you waste the click.

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
uv run pytest -q
```

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
