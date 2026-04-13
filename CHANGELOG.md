# Changelog

## 0.4.0 - 2026-04-14

- Added run difficulty profiles with `builder`, `standard`, and `founder` tuning
- Added campaign goals with alternate progression targets and victory paths
- Added late-game scale pressure from coordination drag, market saturation, cannibalization, and maintenance load
- Extended the dashboard, report view, and scenario catalog to surface difficulty, campaign goals, and scale state
- Persisted difficulty and campaign-goal state through SQLite save/load and schema version `7`

## 0.3.0 - 2026-04-13

- Added save-slot management with list, rename, and delete flows in the CLI
- Added a quick guide command, onboarding hints, and in-session guide utility for new runs
- Deepened competitor behavior so rival moves now reshape pricing posture and product-count pressure
- Expanded the scenario and template catalog with market-shock and portfolio-heavy starting runs
- Hardened packaging metadata and explicit content-file inclusion for release builds

## 0.2.0 - 2026-04-13

- Added richer event content with referral-wave and enterprise-compliance trade-off events
- Added new progression milestones for profitable streaks and multi-segment reach
- Expanded report output with funding, event, and milestone history panels
- Added CLI support for `list-templates` and `--version`
- Promoted the package version to `0.2.0` for the broader content-and-polish release
