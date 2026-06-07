# NEXUS TECH Release Checklist

Use this checklist before tagging or presenting a release.

## Version And Notes

- Update `pyproject.toml`.
- Update `src/nexus_tech/__init__.py`.
- Add a dated entry to `CHANGELOG.md`.
- Confirm the README lists any new commands, systems, or content.

## Local Verification

```bash
uv sync --extra dev
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest -q
uv run nexus-tech --version
uv run nexus-tech doctor
uv run nexus-tech validate-content
uv run nexus-tech play-2d --scenario founder_journey --seed 7 --headless --max-frames 2 --motion-mode reduced
uv run nexus-tech menu-2d --headless --max-frames 2 --motion-mode reduced
uv run nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 2
uv run nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 1 --motion-mode reduced
uv run nexus-tech audit-2d-motion --scenario founder_journey --seed 7 --frames 1 --motion-mode off
uv run nexus-tech audit-2d-visual --scenario founder_journey --seed 7
uv run nexus-tech audit-2d-visual --scenario founder_journey --seed 7 --motion-mode off
uv run nexus-tech audit-2d-animation --scenario founder_journey --seed 7 --frames 1
```

## Demo Verification

```bash
uv run nexus-tech glossary
uv run nexus-tech tutorial
uv run nexus-tech list-scenarios
uv run nexus-tech list-templates
uv run nexus-tech list-rivals
uv run nexus-tech list-events
uv run nexus-tech simulate-balance --scenario founder_journey --runs 1 --turns 3 --seed-base 7
uv run nexus-tech balance-audit --scenario founder_journey --scenario debt_crunch --runs 1 --turns 6 --seed-base 7
uv run nexus-tech simulate-balance --scenario founder_journey --difficulty founder --runs 2 --turns 10 --seed-base 700
uv run nexus-tech balance-report --output /tmp/nexus-balance-report.md --scenario founder_journey --runs 1 --turns 3 --seed-base 7
```

## Save Verification

```bash
uv run nexus-tech check-saves
uv run nexus-tech list-saves
```

If no save database exists yet, `doctor` should still run cleanly and explain that no save has been created.

## 2D Audit Notes

- Capture the latest internal playtest and balance findings in a repo doc before release so cockpit, friction, and tuning decisions stay attached to the build.
- Run `audit-2d-motion` whenever animation pacing, pulse-bank cooldown, staged-summary motion, or 2D request-path coverage changes.
- Run `audit-2d-animation` whenever a scene, overlay, pending-event, outcome, actor/sprite, or late-game choreography layer changes so required animation coverage and advisory gaps stay explicit.
- Treat missing `actor-readability` layers as release blockers before the remaining open-window readability pass.
- Treat `Visual Fatigue Budget` failures as release blockers before adding more animation density.
- Treat missing `blocked-action-feedback` as a release blocker when disabled or rejected command behavior changes.
- Keep `.github/workflows/ci.yml` aligned with these local gates so animation regressions fail before merge.
- Use `docs/ANIMATION_PLAYTEST_CHECKLIST_2026-06-06.md` for the remaining open-window readability pass before presenting the 2D build.
- If `balance-audit` still reports `watch` or worse cells, note whether they are intentional difficulty pressure or candidates for retuning before tagging.
- If founder-pressure openings were retuned, rerun at least one longer `simulate-balance` founder batch so angel-cap, pricing, and cash-guard policies are verified on real seeds instead of only short audits.

## Scope Guardrails

- Keep the game local and offline.
- Do not add GUI, web, cloud, accounts, telemetry, or multiplayer infrastructure.
- Keep simulation logic out of Rich rendering and Typer command handlers.
- Keep SQLite access inside the persistence layer.
- Keep randomness seedable for deterministic tests and demos.
