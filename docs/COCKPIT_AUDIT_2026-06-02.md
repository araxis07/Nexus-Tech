# 2D Late-Game Cockpit Audit

Date: 2026-06-02

## Scope

- Endgame board open flow in the 2D run scene
- Direct cockpit actions for gate-command and hotspot-review routing
- Inspector-side cockpit route coverage
- Deterministic regression checks and headless frontend smoke coverage

## What Changed

- Opening the `endgame` deep panel now emits an `Endgame Cockpit` brief event with blocked-path context plus the current gate alert.
- The endgame board now surfaces a dedicated `Hotspot Review` action in addition to `Gate Command` and path-specific fix actions.
- Running a cockpit command now emits a `Cockpit Handoff` event when focus moves into the matching finance, board, customer, partnership, or report workspace.
- Endgame inspector projection routes now include a dedicated `Cockpit Route` item so late-game diagnosis can launch the next command or hotspot review without backing out to the panel grid.

## Deterministic Checks

- `tests/test_frontend_2d.py::test_endgame_cockpit_actions_expose_all_path_fix_buttons`
- `tests/test_frontend_2d.py::test_run_scene_opening_endgame_panel_pushes_cockpit_brief_event`
- `tests/test_frontend_2d.py::test_run_scene_endgame_cockpit_command_pushes_handoff_event`
- `nexus_tech.cli play-2d --headless --max-frames 4`
- `nexus_tech.cli menu-2d --headless --max-frames 4`

## Remaining Friction To Watch

- Human playtest timing still matters for cockpit-event TTL and motion intensity; deterministic checks do not tell us if the handoff cards are visually too noisy.
- The cockpit currently routes into the correct workspace, but very long late-game sessions may still need another pass on card density and event ordering.
- A full GUI/manual pass is still worth doing before calling the 2D frontend beta-ready.
