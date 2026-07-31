# UX Hierarchy Audit - 2026-07-30

## Scope

This audit covers NEXUS TECH 0.324.0. It improves responsive typography,
container hierarchy, blocking-overlay isolation, and spacious Focus cards
without changing gameplay actions, balance, controls, frozen content catalogs,
persistence schema 28, or human beta evidence.

## Decision

- Automated presentation readiness: `pass`
- Product position: late-alpha beta candidate, approximately `83%`
- Human readiness: `manual-required`
- Expansion decision: keep the feature freeze until the human gate closes

## Changes

- Compact 820x620 typography retains its established scale.
- Standard and spacious viewports apply bounded type multipliers only when both
  width and height provide the required room.
- Live resizing rebuilds the current scene font pack from the persisted player
  preference and new viewport.
- Spacious Focus cards promote their headline and detail font roles while
  compact cards retain their existing line budget.
- Secondary panel borders and accent rails are quieter than active or animated
  panel chrome.
- Blocking overlays use deterministic alpha floors, with Inspector and Deep
  Panel receiving the strongest isolation from the live scene.
- Runtime, visual audit, and motion audit use the same viewport typography
  policy.

## Automated Evidence

| Area | Result | Evidence |
| --- | --- | --- |
| Full test suite | pass | 1,243 tests |
| Formatting and lint | pass | 153 files formatted; Ruff reported no issues |
| Focused hierarchy regressions | pass | Viewport scale, panel chrome, overlay alpha, and Focus card role contracts |
| Responsive visual audit | pass | 45 captures across 820x620, 1280x720, and 1440x900 |
| Animation matrix | pass | 21 scenario/seed cells; manual timing advisory retained |
| Campaign readiness | pass | 18 difficulty cells and all 72 authored route cells |
| Decision quality | advisory | Ledger gate passed; 13 autoplay variety watches still require human confirmation |
| Package smoke | pass | Wheel contained 144 files, passed integrity, imported as 0.324.0, and completed an isolated headless 2D launch |
| Beta packet smoke | pass | Fresh 0.324.0 owner/tester profiles were isolated and packet preflight passed |
| Compact containment | pass | 820x620 retained complete controls and text-fit safety |
| Spacious hierarchy | pass | 1440x900 promoted Focus headline/detail roles without overlap |
| Overlay isolation | pass | 820x620 Inspector no longer exposed the underlying run heading through its backdrop |

## Human Boundary

Headless captures can prove containment, font-role selection, and backdrop
isolation. They cannot prove comfortable reading speed, perceived hierarchy,
mouse confidence, or motion feel. The owner rehearsal and six first-time human
sessions remain required, and current-version evidence remains `0/6`.
