# NEXUS TECH

`NEXUS TECH` is a terminal-first, single-player business management and simulation game built entirely in Python.

You start with a small amount of capital, one early software product, and a fragile company. From there, you manage a growing product portfolio, hire and assign employees, react to market and team events, and try to build a sustainable software business before cash runs out.

## What The Project Does

The current build already supports a complete playable loop in the terminal:

- turn-based company simulation
- multiple products under one company
- product strategy trade-offs such as quality, features, bugs, market fit, churn, and technical debt
- employee hiring, firing, assignment, burnout, recovery, and role-based impact
- dynamic business events with weighted selection and cooldowns
- local save and load with SQLite
- Rich dashboards, tables, summaries, and event panels for live demos

## Game Features

### Company Management

- track cash, reputation, current turn, and game-over state
- manage multiple active and sunset products
- balance revenue against operating costs, maintenance, and salary burn

### Product Management

- create new products
- improve product quality
- add features
- reduce technical debt
- market a product
- sunset weak products

### Team Simulation

- hire and fire employees
- assign or unassign employees to products
- manage four core roles:
  - engineer
  - designer
  - marketer
  - product_manager
- handle morale, energy, productivity, and burnout pressure

### Dynamic Event System

- product incidents
- market opportunities
- funding opportunities
- reputation incidents
- employee issues

### Local Persistence

- save and resume runs locally with SQLite
- continue the latest save slot
- keep the project fully offline and local-first

## Tech Stack

- Python 3.14+
- `uv` for project and dependency management
- `sqlite3` from the Python standard library for save data
- `Pydantic v2` for validated domain models
- `Rich` for terminal UI rendering
- `Typer` for CLI commands
- `pytest` for test coverage
- `Ruff` for linting and formatting

## Install

```bash
uv sync --extra dev
```

## Run The Game

Start a new game:

```bash
uv run nexus-tech --seed 7
```

Start a named run:

```bash
uv run nexus-tech new-game --company-name "Atlas Labs" --product-name "Signal"
```

Load a save:

```bash
uv run nexus-tech load-game --slot active
```

Continue the most recent save:

```bash
uv run nexus-tech continue-last-game
```

Run with debug output:

```bash
uv run nexus-tech --debug --seed 7
```

Show help:

```bash
uv run nexus-tech --help
```

## How To Play

Each turn represents a business interval:

1. Review the dashboard for company, products, team, and recent events.
2. Spend action points on product or team actions.
3. End the turn to resolve revenue, costs, growth, churn, burnout, and events.
4. Save the run locally and continue later if needed.

In practical terms, the main decisions are:

- which product deserves attention
- whether to push features or stabilize quality
- when to reduce technical debt
- when to hire, rest, or reassign team members
- how to survive cash pressure while still growing users

## Testing

```bash
uv run pytest
```

## Lint And Format

```bash
uv run ruff check src tests
uv run ruff format src tests
```

## Project Structure

- `src/nexus_tech/domain`
  Validated entities, money helpers, and shared constants.
- `src/nexus_tech/simulation`
  Economy, growth, product progression, team systems, turn resolution, and events.
- `src/nexus_tech/persistence`
  SQLite schema, repositories, and save/load coordination.
- `src/nexus_tech/presentation`
  Rich panels, tables, dashboard rendering, and turn summaries.
- `src/nexus_tech/cli.py`
  Typer commands and interactive terminal session flow.

## Notes

- The project is fully local and offline-first.
- Save data is stored in `nexus-tech.db` by default.
- Using `--seed` makes demo runs and tests reproducible.
