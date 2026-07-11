# NEXUS TECH Release Readiness

Date: `2026-07-12`
Version: `0.279.0`
Commit: `9927fb834e9699aac92d4a286179468da54c250c`

## Decision

- Automated readiness: `pass`
- Manual visible-window signoff: `manual-required`
- Release decision: `do not tag yet`

The build is stable enough for a structured manual QA pass. This record does
not treat headless captures, generated packets, or source inspection as human
playtest evidence.

## Verified Automated Gates

| Area | Result | Evidence |
| --- | --- | --- |
| Python test suite | pass | `1013 passed` |
| Formatting and lint | pass | `ruff format --check .`, `ruff check .` |
| Content catalog | pass | 49 scenarios, 49 templates, 32 rivals, 202 events, 0 issues |
| Persistence health | pass | SQLite integrity and foreign keys healthy; schema 23 |
| 2D smoke routes | pass | menu and founder journey closed cleanly in headless mode |
| Motion | pass | full, reduced, and off modes passed across 3 viewports; 44 commands and 82 inspector actions covered |
| Visual captures | pass | 45/45 captures in full mode, baseline `45:9b0fb32e`; 45/45 in off mode, baseline `45:8103a99d` |
| Responsive layout | pass | 45/45 full and 45/45 off captures; 0 layout and 0 typography violations |
| Animation audit | pass | all automated areas passed; manual playtest remains advisory-required |
| Broad animation matrix | pass | 21 scenario/seed cells across 7 scenarios and 3 seeds |
| Balance preflight | pass | 0 critical/high findings across founder journey and debt crunch short cells |
| Onboarding route preflight | pass | 18/18 headless routes across 820x620, 1280x720, and 1440x900 in full/reduced/off |
| QA session artifacts | pass | onboarding and animation handoff/session validators passed with the local launcher |

## Security And Repository Hygiene

- The tracked tree contained no `.env`, database, private-key, credential, or
  virtualenv files.
- Current-tree and Git-history scans found no recognizable private-key, GitHub,
  OpenAI, Slack, or AWS credential patterns.
- `nexus-tech.db` and local virtualenv directories are ignored.
- No tracked binaries exceeded 1 MiB. `tests/test_simulation.py` is the only
  tracked file above that threshold and is plain Python test source.
- Generated PNGs, Markdown QA packets, and scratch databases remain in `/tmp`
  and are intentionally not part of this commit.

## Manual Release Blockers

1. Record the 18 remaining onboarding visible-window rows. The first route is
   `menu-2d --window-size 820x620 --motion-mode full` and must cover title,
   wizard, help, and back/menu recovery.
2. Complete the animation playtest matrix for all three windows and full,
   reduced, and off modes. The current session bundle has 69 open manual
   validation items; these are real observations, not automated failures.
3. Log each observed layout, text, control, navigation, or motion issue as
   `watch` or `fail`; repair only demonstrated problems and rerun the matching
   audit and visible route.
4. Run final report validators after every manual row has concrete notes, then
   repeat the automated release gates before tagging a release.

## Immediate Command

```bash
.venv313/bin/nexus-tech menu-2d --window-size 820x620 --motion-mode full
```

Use `.venv313/bin/nexus-tech onboarding-visible-playtest-next --command-prefix .venv313/bin/nexus-tech` to refresh the exact recorder command after the real window has been observed.
