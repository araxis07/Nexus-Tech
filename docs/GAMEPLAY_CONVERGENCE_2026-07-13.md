# Gameplay Convergence Audit - 2026-07-13

## Current Product Level

NEXUS TECH is a late-alpha playable simulation with a complete vertical slice: a new player can choose a guided scenario, run the company through four pacing phases, use the major operating systems, reach an endgame path, and review or archive the result. The remaining beta work is broad real-player validation and specialist-scenario tuning, not another expansion of the command catalog.

## Shipped In 0.280.0

- All 194 internal turn commands resolve to readable labels and one of 12 stable action families.
- The live HUD identifies Opening (turns 1-4), Growth (5-9), Scale (10-14), and Endgame (15+), with one objective for the current phase.
- Coach, deferred-action, and risk guidance show player-facing labels instead of snake-case command ids.
- The action footer keeps a small core set, adds up to three contextual commands, and always retains Save and End Turn. Partner, Board, and Endgame panels appear when relevant while all keyboard routes remain available.
- Six featured scenarios form a guided journey: Founder Journey, Bootstrap Studio, Technical Rebuild, Portfolio Machine, Debt Crunch, and Public Market Countdown.
- Autoplay now establishes a viable product loop before automating governance, handles board-response prerequisites, and consolidates weak products when a profit run should not carry an unproductive portfolio.

## Automated Gates

`tests/test_gameplay_convergence.py` verifies action coverage, phase boundaries, scenario ordering, readable Coach output, and a deterministic 20-turn Founder Journey sweep across all three goals and all three difficulty modes. The representative sweep requires zero shutdowns and no failed balance cells.

Run it directly with:

```bash
uv run pytest -q tests/test_gameplay_convergence.py
```

Use the broader tuning tools after changing scenarios or economic constants:

```bash
uv run nexus-tech balance-matrix --scenario founder_journey --goal profit_machine --runs 5 --turns 20 --seed-base 1300
uv run nexus-tech balance-audit --scenario founder_journey --scenario debt_crunch --runs 2 --turns 10 --seed-base 100
```

## Remaining Beta Work

1. Complete the real-window onboarding and animation evidence routes. Headless audits cannot be recorded as human visual evidence.
2. Tune specialist scenarios independently, starting with Debt Crunch beyond turn 10. Its 20-turn deterministic bot run remains intentionally outside the representative release gate until a debt-specific strategy can meet Builder expectations without flattening Founder difficulty.
3. Run external playtests focused on first-turn comprehension, action-family discoverability, pause/back navigation, and endgame route choice.
4. Use playtest findings to remove or combine low-value commands before adding new systems.
5. Promote to beta only after the visible QA matrix is complete and representative sessions finish without operator explanation.
