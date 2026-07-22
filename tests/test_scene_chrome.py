from __future__ import annotations

import pytest

from nexus_tech.frontend_2d.scene_chrome import (
    SceneActionOwner,
    resolve_review_scene_chrome,
    resolve_run_scene_chrome,
    resolve_title_scene_chrome,
    resolve_turn_summary_scene_chrome,
)


@pytest.mark.parametrize(
    ("mode", "blocking_overlay_visible", "owner"),
    (
        ("menu", False, SceneActionOwner.CONTENT),
        ("guide", False, SceneActionOwner.NAVIGATION),
        ("wizard", False, SceneActionOwner.NAVIGATION),
        ("menu", True, SceneActionOwner.OVERLAY),
        ("slots", True, SceneActionOwner.OVERLAY),
    ),
)
def test_title_scene_chrome_assigns_one_action_owner(
    mode: str,
    blocking_overlay_visible: bool,
    owner: SceneActionOwner,
) -> None:
    policy = resolve_title_scene_chrome(
        mode=mode,
        blocking_overlay_visible=blocking_overlay_visible,
    )

    assert policy.action_owner is owner
    assert policy.navigation_visible is (owner is SceneActionOwner.NAVIGATION)


def test_run_scene_chrome_moves_action_ownership_to_pause() -> None:
    live = resolve_run_scene_chrome(pause_overlay_visible=False)
    paused = resolve_run_scene_chrome(pause_overlay_visible=True)

    assert live.action_owner is SceneActionOwner.NAVIGATION
    assert live.navigation_visible
    assert paused.action_owner is SceneActionOwner.OVERLAY
    assert not paused.navigation_visible


def test_completed_scenes_keep_actions_in_the_footer() -> None:
    review = resolve_review_scene_chrome()
    summary = resolve_turn_summary_scene_chrome()

    assert review.action_owner is SceneActionOwner.FOOTER
    assert summary.action_owner is SceneActionOwner.FOOTER
    assert not review.navigation_visible
    assert not summary.navigation_visible
