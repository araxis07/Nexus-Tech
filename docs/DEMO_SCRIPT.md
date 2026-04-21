# NEXUS TECH Demo Script

Use this when presenting the game live from a terminal.

## 1. Preflight

```bash
uv sync --extra dev
uv run nexus-tech doctor
uv run nexus-tech validate-content
uv run nexus-tech list-scenarios
uv run nexus-tech list-events
uv run nexus-tech tutorial
uv run nexus-tech glossary
```

Talk track:

- NEXUS TECH is a local, offline-first Python management simulation.
- The player runs a software company through products, employees, finance, competitors, key accounts, and events.
- Rich handles terminal presentation. Typer handles CLI commands. SQLite handles local saves.

## 2. Start a Run

```bash
uv run nexus-tech new-game --scenario founder_journey --difficulty standard --goal profit_machine --seed 7
```

Opening explanation:

- Review cash, reputation, board confidence, runway pressure, products, team, competitors, key accounts, and action points.
- Mention that seed-based runs make demos repeatable.

## 3. Show Core Loop

Recommended first few actions:

- Use `guide` or in-game `show_guide` if the audience is new.
- Hire one engineer or marketer.
- Assign the employee to the active product.
- Improve quality or market the product.
- End the turn and explain revenue, operating cost, churn, growth, and events.

Talk track:

- Features help growth but can increase bugs and debt.
- Quality and debt work reduce churn and support load.
- Hiring improves throughput but increases fixed cost and burnout risk.
- Finance decisions buy runway but increase debt, dilution, and investor pressure.

## 4. Show Tuning Tools

```bash
uv run nexus-tech simulate-balance --scenario founder_journey --runs 2 --turns 6 --seed-base 100
uv run nexus-tech balance-report --output balance-report.md --scenario founder_journey --runs 2 --turns 6 --seed-base 100
```

Talk track:

- Balance tools let the project grow without relying only on manual play.
- Reports compare scenarios and difficulties using deterministic autoplayer runs.

## 5. Save And Resume

During a run, use the save action from the utility menu.

Then show:

```bash
uv run nexus-tech list-saves
uv run nexus-tech continue-last-game
```

Close with:

- The game remains Python-only, terminal-first, and offline.
- The current scale is a serious CLI simulation with modular systems and expandable content.
