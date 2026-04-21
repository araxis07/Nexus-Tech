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
- Create products from reusable templates, improve quality, add features, market products, reduce debt, and sunset weak products
- Deal with segment-specific trade-offs like support cost, price sensitivity, and competitive pressure

### 🧩 Data-Driven Content

- Start runs from a scenario catalog instead of a single hard-coded opening
- Use reusable product templates such as SaaS tools, growth apps, developer platforms, and workflow suites
- Expand the catalog with AI copilot, analytics, support-ops, compliance, embedded API, and capital-pressure scenarios
- Extend the catalog further with renewal-cloud, customer-portal, and ops-intelligence templates plus channel and concentration-risk scenarios
- Add a second content-pack pass with billing-hub and partner-stack templates plus talent-race and moat-builder scenarios
- Add enterprise-data, field-service, and procurement templates plus board-tension, channel-defense, and late-scale drag scenarios
- Add AI-governance, developer-marketplace, customer-health, and incident-command templates plus higher-scale trust and ecosystem scenarios
- Keep scenario and template definitions in JSON so the content layer can grow without rewriting core systems
- Support custom company and primary product overrides on top of scenario defaults

### 🌐 Market and Competition

- Run each company inside a live market cycle such as `cooling`, `steady`, `expanding`, or `frothy`
- Track lightweight competitor rosters that apply ongoing pressure by segment, pricing, aggression, and tactical momentum
- Simulate rival moves such as `hold`, `discount_push`, `feature_sprint`, and `retrench`
- Track rival funding levels so strong, high-momentum competitors become more dangerous over time
- Define reusable competitor archetypes such as price raiders, platform bulwarks, and feature blitzers
- Expand rival archetypes with channel aggregators, trust monoliths, and vertical specialists
- Add AI fast followers, governance giants, and ecosystem brokers as new rival archetypes
- Let rival moves reshape product count and pricing posture over time
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
- Balance growth capital against repayment pressure, score penalties, and long-term victory quality

### 🤝 Customer Accounts

- Turn strong product traction into named key customer accounts
- Track account satisfaction, contract value, expansion potential, renewal timing, and churn risk
- Add recurring account revenue on top of product usage revenue
- Let weak product health, bugs, and technical debt create visible renewal pressure
- Review key accounts directly from the in-game `review_customers` action

### 👥 Employee and Team System

- Hire and fire employees
- Assign team members to specific products
- Manage core roles:
  - `engineer`
  - `designer`
  - `marketer`
  - `product_manager`
- Simulate morale, energy, burnout, recovery, and role-based impact on outcomes

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
- Customer-heavy and enterprise-heavy runs can surface key-account expansion and security-audit trade-offs
- Scale-stage runs can now surface enterprise sales cycles, product launch windows, platform outages, competitor acquisitions, and regulatory shifts
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
- Set a budget stance such as `lean`, `balanced`, or `aggressive` and let it shape burn, marketing efficiency, and team fatigue
- Work against a quarter plan with explicit revenue, user, cash, and headcount targets
- Track run score, estimated company value, turn history, and victory conditions in the terminal report
- Classify successful runs into exit paths such as profitable independence, strategic acquisition, IPO-ready, or restructure

### 💾 Local Save / Load

- Save and load runs locally with SQLite
- Resume the latest save slot
- List, rename, and delete save slots directly from the CLI
- Persist roadmap state, market cycle, quarter plan, finance state, funding history, competitors, key accounts, product targeting, event history, team assignments, exit summaries, and turn history
- Use SQLite schema versioning and additive migrations to keep local save files upgradeable
- Keep the entire project offline and self-contained

### 🖥️ Presentation and CLI

- Rich-powered dashboard panels, tables, summaries, and event notifications
- Typer-based CLI commands for starting, loading, and continuing runs
- Built-in quick guide flow for onboarding and live demos
- Built-in first-run tutorial and glossary commands for new players
- In-game reporting view for score, valuation, quarter-plan progress, competitor watch, and recent turn history
- Deterministic `simulate-balance` batch runs for tuning scenarios, difficulties, and goals without playing by hand
- Deterministic `compare-balance` scenario rankings for side-by-side tuning across multiple openings
- Deterministic `balance-matrix` runs to compare the same scenarios across every difficulty profile
- Deterministic `balance-audit` runs to flag rough scenario/difficulty combinations for tuning
- Deterministic `export-balance-csv` output for external review of scenario and difficulty balance
- Deterministic `balance-report` output for Markdown tuning reports that combine matrix and audit data
- Built-in `glossary` command to explain core stats, pressure systems, and decision families
- Built-in `validate-content` command to check catalog references and event handler wiring before release
- Report now includes recent events, funding history, and milestone history
- Add `list-rivals`, `list-events`, `doctor`, and `check-saves` so content, install state, and local persistence health can be reviewed without entering a run
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

1. Review the dashboard for company health, products, team status, and recent events.
2. Spend action points on product or team decisions.
3. End the turn to resolve revenue, costs, growth, churn, burnout, and event outcomes.
4. Save locally and continue the run later if needed.

If you are new to the game, run `nexus-tech guide` or use the in-session guide utility to get a compact opening checklist.

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
