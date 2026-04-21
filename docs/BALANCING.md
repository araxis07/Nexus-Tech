# Balancing and Content Workflow

NEXUS TECH has enough systems that tuning should be data-assisted instead of based only on manual play.

## Core Commands

Run a short deterministic batch:

```bash
uv run nexus-tech simulate-balance --scenario founder_journey --runs 5 --turns 10 --seed-base 100
```

Compare scenarios:

```bash
uv run nexus-tech compare-balance --scenario founder_journey --scenario technical_rebuild --runs 3 --turns 10
```

Run the scenario/difficulty matrix:

```bash
uv run nexus-tech balance-matrix --scenario founder_journey --runs 2 --turns 10
```

Export matrix data:

```bash
uv run nexus-tech export-balance-csv --output balance.csv --scenario founder_journey --runs 2 --turns 10
```

Export a Markdown balance report:

```bash
uv run nexus-tech balance-report --output balance-report.md --scenario founder_journey --runs 2 --turns 10
```

## What to Watch

- Average score should climb with good decisions but not explode early.
- Founder difficulty should produce more shutdown risk than builder difficulty.
- Cash should matter without making every run feel doomed.
- Key accounts should become valuable only after product traction is real.
- Technical debt should become painful through bugs, churn, renewal risk, and operations load.
- Competitor funding should raise pressure gradually, not instantly decide the run.
- Endgame outcomes should reward durable revenue, cash discipline, reputation, and board confidence.

## Safe Content Additions

- Add new product templates in `src/nexus_tech/content/product_templates.json`.
- Add new scenarios in `src/nexus_tech/content/scenarios.json`.
- Add new rival patterns in `src/nexus_tech/content/competitor_archetypes.json`.
- Add new events through the event registry only when they create a clear trade-off.

Avoid adding persistence, web, networking, or GUI concerns to content work. The game should remain local, offline, and terminal-first.
