# 2D Motion Pressure Audit

Date: `2026-06-03`
Version under audit: `0.114.0`

## Scope

- `pytest -q tests/test_frontend_2d.py`
- inspection of `PulseBank` activity and long-lived run/summary motion helpers
- dense-feed and dense-summary spot checks through targeted unit tests

## Findings

1. The 2D motion layer had no direct telemetry for how many active pulses were already on screen, so low-signal events could keep spawning full-strength pulses even during busy late-game moments.
2. Run-scene info cards already shortened their TTL under dense queues, but they were still triggering feed pulses at normal strength when the broader motion bank was already crowded.
3. Turn-summary timeline cues slowed for narrow or event-heavy scenes, but they did not react to already-dense pulse banks inside the summary itself.

## Fix Summary

- Added `PulseBank.live_count()` and `PulseBank.total_intensity()` so scenes can measure motion pressure directly instead of inferring it only from queue length.
- Run-scene event normalization now shortens `info` / `success` TTL further under high pulse pressure and slightly trims warning TTLs when the overlay/feed stack is already busy.
- Run-scene event motion now damps feed intensity more aggressively than primary target pulses when the pulse bank is crowded, preserving workspace cues while reducing feed spam.
- Turn summaries now compute their own pressure ratio and use it to slow reveal cadence slightly and damp target-lane pulses when the timeline is already busy.

## Verification

- `tests/test_frontend_2d.py::test_pulse_bank_reports_live_count_and_total_intensity`
- `tests/test_frontend_2d.py::test_run_scene_busy_motion_bank_shortens_info_ttl_further`
- `tests/test_frontend_2d.py::test_run_scene_busy_motion_bank_dampens_feed_pulse`
- `tests/test_frontend_2d.py::test_turn_summary_scene_busy_motion_bank_dampens_timeline_pulse`
- `tests/test_frontend_2d.py::test_turn_summary_scene_event_pacing_helpers_track_window_size`

## Remaining Risk

- This is still automated pressure testing, not a human-observed long session.
- The next meaningful proof step is still a real open-window playtest over multiple scenarios and difficulties.
