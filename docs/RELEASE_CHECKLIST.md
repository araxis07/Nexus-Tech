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
uv run nexus-tech audit-2d-animation-matrix --frames 1 --output /tmp/nexus-tech-animation-matrix.md
uv run nexus-tech prepare-2d-animation-playtest --frames 1 --output /tmp/nexus-tech-animation-playtest-prep.md
uv run nexus-tech balance-audit --scenario founder_journey --scenario debt_crunch --runs 1 --turns 6 --seed-base 7
uv run nexus-tech simulate-balance --scenario founder_journey --difficulty founder --runs 2 --turns 10 --seed-base 700
# After the manual report is filled:
uv run nexus-tech validate-animation-playtest-report /tmp/nexus-tech-animation-playtest-report.md
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
- Run `audit-2d-animation-matrix --output /tmp/nexus-tech-animation-matrix.md` before presentation builds so actor/state, readability, pacing, and motion gates are checked beyond the single founder seed.
- Run `prepare-2d-animation-playtest --output /tmp/nexus-tech-animation-playtest-prep.md` before the human pass so the window/motion/control checklist starts from the same matrix baselines as CI.
- Run the balance and long-session preflight commands listed in the playtest prep artifact before opening the manual animation pass.
- Run `validate-animation-playtest-report` on the completed manual report before calling animation complete.
- Treat missing `actor-readability` layers as release blockers before the remaining open-window readability pass.
- Treat missing `actor-pose-depth` layers as release blockers before presenting new actor/sprite reactions.
- Treat `Actor State Coverage` failures as release blockers before presenting new actor/sprite reactions.
- Treat `Action Feedback Clarity` failures as release blockers before presenting new action, blocked-action, or impact feedback.
- Treat `Scene Transition Handoff` failures as release blockers before presenting scene-to-scene animation polish.
- Treat `Control Affordance Coverage` failures as release blockers before presenting navigation, pause, back, help, save, or summary/outcome flow changes.
- Treat `Control Replay Safety` failures as release blockers before presenting pause, Escape/back, help, save, hover-copy, or menu-return behavior.
- Treat `UI Layout Safety` failures as release blockers before presenting compact layouts, navigation rails, modal buttons, or actor-heavy scenes.
- Treat `Typography Safety` failures as release blockers before presenting compact buttons, modal copy, summary cards, or inspector-heavy scenes.
- Treat `Visual Fatigue Budget` failures as release blockers before adding more animation density.
- Treat `Animation Pacing Budget` failures as release blockers before adding more full-mode motion layers.
- Treat `Motion Mode Differentiation` failures as release blockers before changing full/reduced/off animation behavior.
- Treat `Long Session Motion Stress` failures as release blockers before presenting longer 2D playthroughs.
- Treat `Long Session Visual Readiness` failures as release blockers before presenting longer 2D playthroughs.
- Treat `Scene Motion Profile` failures as release blockers before shipping new scenes or adding denser scene-specific motion.
- Treat `Readability Guard` failures as release blockers before opening the manual playtest pass.
- Treat text clipping, unreadable compact buttons, or local gameplay database files appearing in `git status` as release blockers before presenting the 2D build.
- Treat missing visible Back/Pause/Menu controls, missing hover/cursor affordance on primary controls, or `Esc` quitting the run without pause confirmation as release blockers before presenting the 2D build.
- Treat 820x620 title/run/summary/review captures with overlapping navigation, cut-off cards, or action buttons spilling outside their panels as release blockers before presenting the 2D build.
- Treat `audit-2d-animation-matrix` failures as release blockers for the default seven-scenario, three-seed presentation matrix.
- Treat missing `blocked-action-feedback` as a release blocker when disabled or rejected command behavior changes.
- Keep `.github/workflows/ci.yml` aligned with these local gates so animation regressions fail before merge, review the uploaded `nexus-tech-2d-visual-audit` artifact summary before opening individual captures, and review the uploaded `nexus-tech-2d-animation-matrix` and `nexus-tech-2d-animation-playtest-prep` artifacts before manual presentation playtests.
- Use `docs/OPEN_WINDOW_ANIMATION_PLAYTEST.md`, `docs/ANIMATION_PLAYTEST_REPORT_TEMPLATE.md`, and `docs/ANIMATION_PLAYTEST_CHECKLIST_2026-06-06.md` for the remaining open-window readability pass before presenting the 2D build.
- If `balance-audit` still reports `watch` or worse cells, note whether they are intentional difficulty pressure or candidates for retuning before tagging.
- Treat unexplained balance preflight `watch` or `fail` cells as blockers for presentation builds, even when animation gates are green.
- Treat incomplete manual reports, blank result cells, `todo` cells, or missing validator PASS as blockers for presentation builds.
- If founder-pressure openings were retuned, rerun at least one longer `simulate-balance` founder batch so angel-cap, pricing, and cash-guard policies are verified on real seeds instead of only short audits.

## Scope Guardrails

- Keep the game local and offline.
- Do not add GUI, web, cloud, accounts, telemetry, or multiplayer infrastructure.
- Keep simulation logic out of Rich rendering and Typer command handlers.
- Keep SQLite access inside the persistence layer.
- Keep randomness seedable for deterministic tests and demos.
