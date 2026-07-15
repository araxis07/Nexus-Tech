# NEXUS TECH Architecture

NEXUS TECH is a local Python management simulation with terminal and lightweight 2D presentation adapters. The codebase is split by responsibility so gameplay rules do not leak into rendering or SQLite code.

## Boundaries

- `domain`: Pydantic models, enums, money helpers, and shared validation.
- `simulation`: deterministic game systems such as economy, growth, products, team, events, finance, customers, competitors, milestones, scoring, and endgame evaluation.
- `content`: JSON-backed scenarios, product templates, and competitor archetypes.
- `persistence`: SQLite schema, repositories, and save/load orchestration.
- `presentation`: Rich panels and tables. This layer should render state, not mutate it.
- `frontend_2d`: pygame scenes, responsive layout, input routing, animation, and view-model adapters. This layer should route commands rather than own simulation rules.
- `cli.py`: Typer commands, interactive prompts, and command wiring.

## Turn Flow

1. The player selects actions through Typer/Rich or the pygame command adapter.
2. `simulation.engine.apply_action` mutates a copied `GameState` for immediate actions.
3. `simulation.engine.resolve_turn` calculates revenue, costs, growth, churn, team drift, events, milestones, customer renewals, market cycles, and scoring.
4. `presentation.dashboard` or `frontend_2d.viewmodels` renders the resulting summaries.
5. `persistence.save_coordinator` saves or loads a complete local SQLite state when requested.

## Design Rules

- Keep formulas centralized in `simulation.balance`.
- Keep SQL inside repositories and schema modules.
- Keep rendering free of business logic.
- Keep cross-system guidance derived and save-compatible; `simulation.strategic_rhythm` reads campaign, planning, coach, forecast, preview, and ledger state without creating a second source of truth.
- Use `Decimal` for money and quantize through domain money helpers.
- Use seeded randomness through `RandomSource` for deterministic tests and demos.
- Prefer additive SQLite migrations so existing local save files can be upgraded.

## Current Scale

The project is now a late-alpha beta candidate with multiple products, employees, events, finance, competitors, campaigns, persistence, balance tooling, key accounts, archive progression, and endgame classification across terminal and 2D play. The next meaningful scale step is observed usability, consolidation, and safe module extraction rather than more catalog breadth, a web stack, or online infrastructure.
