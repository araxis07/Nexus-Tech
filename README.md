# NEXUS TECH

`NEXUS TECH` is a terminal-first, single-player management/simulation game built in Python.  
You start as a small software founder, manage products and team assignments, react to business events, and try to keep the company alive long enough to grow.

## Stack

- Python 3.14+ target
- `uv` for environment and project management
- `sqlite3` from the standard library for local saves
- `Pydantic v2` for validated domain models
- `Rich` for terminal presentation
- `Typer` for CLI entrypoints
- `pytest` for tests
- `Ruff` for linting and formatting

## Install

```bash
uv sync --extra dev
```

## Run

Start a new game:

```bash
uv run nexus-tech --seed 7
```

Useful commands:

```bash
uv run nexus-tech --help
uv run nexus-tech new-game --company-name "Atlas Labs" --product-name "Signal"
uv run nexus-tech load-game --slot active
uv run nexus-tech continue-last-game
uv run nexus-tech --debug --seed 7
```

## Test

```bash
uv run pytest
```

## Lint And Format

```bash
uv run ruff check src tests
uv run ruff format src tests
```

## Gameplay Loop

Each turn is a fixed business interval:

1. Review the company dashboard, portfolio, team, and event panels.
2. Spend action points on product, team, or utility actions.
3. End the turn to resolve revenue, costs, growth, churn, burnout, and events.
4. Save locally to SQLite and continue later if needed.

## Architecture

- `src/nexus_tech/domain`
  Validated entities, shared money helpers, and scalar constants.
- `src/nexus_tech/simulation`
  Turn rules, economy, product progression, team effects, growth, and events.
- `src/nexus_tech/persistence`
  SQLite schema and repositories isolated from gameplay logic.
- `src/nexus_tech/presentation`
  Rich dashboard and terminal rendering only.
- `src/nexus_tech/cli.py`
  Typer entrypoints and interactive terminal session flow.

## Notes

- The project is local and offline-first.
- Saves are stored in `nexus-tech.db` by default.
- Use `--seed` during demos and tests to make runs reproducible.
