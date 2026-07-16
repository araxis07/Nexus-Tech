# NEXUS TECH Architecture

NEXUS TECH is a local Python management simulation with terminal and lightweight 2D presentation adapters. The codebase is split by responsibility so gameplay rules do not leak into rendering or SQLite code.

## Boundaries

- `domain`: Pydantic models, enums, money helpers, and shared validation.
- `simulation`: deterministic game systems such as economy, growth, products, team, events, finance, customers, competitors, milestones, scoring, and endgame evaluation.
- `content`: JSON-backed scenarios, product templates, and competitor archetypes.
- `persistence`: SQLite schema, repositories, and save/load orchestration.
- `presentation`: Rich panels and tables. This layer should render state, not mutate it.
- `frontend_2d`: pygame scenes, responsive layout, input routing, animation, and view-model adapters. This layer should route commands rather than own simulation rules.
- `frontend_2d.action_bar`: pure run-button catalog and local loadout policy; it must not evaluate availability, route input, or render controls.
- `frontend_2d.control_guide`: pure control-help content shared with layout regressions; it must not own input bindings or render surfaces.
- `frontend_2d.outcome_presentation`: pure completed-run copy and metric policy; it must not mutate the run, save an archive, or render pygame surfaces.
- `frontend_2d.panel_disclosure`: pure presentation policy for guided versus expanded deep-panel content; it must never remove commands from the underlying view model.
- `simulation.decision_patterns`: pure operating-choice analysis derived from Decision Ledger entries; it must not write state, classify forced event responses as operating choices, or tune balance automatically.
- `simulation.beta_playtest_preparation`: pure next-session targeting and command preparation; it must not persist evidence, retain free-form observation notes, or convert automation into human signoff.
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
- Keep gameplay-usage evidence derived from the existing bounded ledger; Decision Pattern is review context, not telemetry, a score modifier, or proof of human comprehension.
- Keep human-session preparation separate from evidence persistence; generated packets may guide an observer but only explicit post-session attestation may create a beta evidence row.
- Keep animated actor overlays in reserved presentation lanes; they must not cover copy, controls, or other non-interactive status decoration at any supported viewport.
- Use `Decimal` for money and quantize through domain money helpers.
- Use seeded randomness through `RandomSource` for deterministic tests and demos.
- Prefer additive SQLite migrations so existing local save files can be upgraded.

## Current Scale

The project is now a late-alpha beta candidate with multiple products, employees, events, finance, competitors, campaigns, persistence, balance tooling, key accounts, archive progression, and endgame classification across terminal and 2D play. Decision-density, action-bar, control-guide, completed-run, and responsive actor-placement policy are covered without changing behavior ownership. The next meaningful scale step remains observed usability, consolidation, and safe module extraction rather than more catalog breadth, a web stack, or online infrastructure.
