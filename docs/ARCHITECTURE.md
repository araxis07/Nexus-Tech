# NEXUS TECH Architecture

NEXUS TECH is a local, terminal-first Python management simulation. The codebase is intentionally split by responsibility so gameplay can grow without pushing business rules into CLI rendering or SQLite code.

## Boundaries

- `domain`: Pydantic models, enums, money helpers, and shared validation.
- `simulation`: deterministic game systems such as economy, growth, products, team, events, finance, customers, competitors, milestones, scoring, and endgame evaluation.
- `content`: JSON-backed scenarios, product templates, and competitor archetypes.
- `persistence`: SQLite schema, repositories, and save/load orchestration.
- `presentation`: Rich panels and tables. This layer should render state, not mutate it.
- `cli.py`: Typer commands, interactive prompts, and command wiring.

## Turn Flow

1. The player selects actions through the Typer/Rich CLI.
2. `simulation.engine.apply_action` mutates a copied `GameState` for immediate actions.
3. `simulation.engine.resolve_turn` calculates revenue, costs, growth, churn, team drift, events, milestones, customer renewals, market cycles, and scoring.
4. `presentation.dashboard` renders the resulting summaries.
5. `persistence.save_coordinator` saves or loads a complete local SQLite state when requested.

## Design Rules

- Keep formulas centralized in `simulation.balance`.
- Keep SQL inside repositories and schema modules.
- Keep rendering free of business logic.
- Use `Decimal` for money and quantize through domain money helpers.
- Use seeded randomness through `RandomSource` for deterministic tests and demos.
- Prefer additive SQLite migrations so existing local save files can be upgraded.

## Current Scale

The project is now a mid-scale terminal simulation: multiple products, employees, events, finance, competitors, scenarios, milestones, persistence, balance tooling, key accounts, and endgame classification are all active systems. The next meaningful scale step is more authored content and balance tuning, not a web stack or GUI migration.
