"""Pygame bootstrap for the lightweight NEXUS TECH 2D frontend."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from nexus_tech.domain.models import GameState
from nexus_tech.frontend_2d.accessibility import ContrastMode, UiScale
from nexus_tech.frontend_2d.layout import clamp_frontend_viewport_size
from nexus_tech.frontend_2d.tween import MotionMode
from nexus_tech.persistence.save_coordinator import SaveLoadCoordinator
from nexus_tech.simulation.engine import create_new_game
from nexus_tech.simulation.randomness import RandomSource
from nexus_tech.user_preferences import FrontendPreferences


class Frontend2DUnavailableError(RuntimeError):
    """Raised when the optional 2D frontend dependency is unavailable."""


@dataclass(frozen=True)
class FrontendRunResult:
    """Compact result returned after the 2D frontend exits."""

    state: GameState
    rng: RandomSource
    slot_name: str
    exit_reason: str
    saved_on_exit: bool


def launch_2d_frontend(
    *,
    state: GameState,
    rng: RandomSource,
    db_path: Path,
    slot_name: str,
    headless: bool = False,
    max_frames: int | None = None,
    window_size: tuple[int, int] = (1440, 900),
    motion_mode: MotionMode | str | None = None,
    ui_scale: UiScale | str | None = None,
    contrast_mode: ContrastMode | str | None = None,
) -> FrontendRunResult:
    """Launch the lightweight animated 2D dashboard."""

    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    try:
        import pygame
    except ModuleNotFoundError as error:
        raise Frontend2DUnavailableError(
            "pygame-ce is not installed. Install the optional 2D runtime first."
        ) from error

    from nexus_tech.frontend_2d import scenes
    from nexus_tech.frontend_2d.widgets import (
        active_contrast_mode,
        configure_contrast_mode,
        create_fonts,
    )

    previous_contrast_mode = active_contrast_mode()
    try:
        pygame.init()
        pygame.font.init()
        window_size = clamp_frontend_viewport_size(window_size)
        flags = pygame.RESIZABLE | (pygame.HIDDEN if headless else 0)
        surface = pygame.display.set_mode(window_size, flags)
        pygame.display.set_caption(f"NEXUS TECH 2D | {state.company.name}")
        coordinator = SaveLoadCoordinator(db_path)
        (
            preferences,
            fonts,
            apply_preferences,
            preference_provider,
            resize_fonts,
        ) = _build_preference_runtime(
            pygame=pygame,
            scenes=scenes,
            coordinator=coordinator,
            create_fonts=create_fonts,
            configure_contrast_mode=configure_contrast_mode,
            motion_mode=motion_mode,
            ui_scale=ui_scale,
            contrast_mode=contrast_mode,
            viewport_size=window_size,
        )
        scene = scenes.RunScene(
            pygame=pygame,
            fonts=fonts,
            state=state,
            rng=rng,
            slot_name=slot_name,
            save_callback=lambda game_state, game_rng, current_slot: coordinator.save_game(
                current_slot,
                game_state,
                game_rng,
            ),
            motion_mode=preferences.motion_mode,
            preferences=preferences,
            preference_callback=apply_preferences,
            preference_provider=preference_provider,
            entry_transition="boot_run",
        )
    except Exception:
        pygame.quit()
        configure_contrast_mode(previous_contrast_mode, mirror_modules=(scenes,))
        raise
    try:
        return _run_frontend_loop(
            pygame=pygame,
            surface=surface,
            scene=scene,
            flags=flags,
            max_frames=max_frames,
            resize_fonts=resize_fonts,
        )
    finally:
        configure_contrast_mode(previous_contrast_mode, mirror_modules=(scenes,))


def launch_2d_menu(
    *,
    db_path: Path,
    headless: bool = False,
    max_frames: int | None = None,
    window_size: tuple[int, int] = (1440, 900),
    motion_mode: MotionMode | str | None = None,
    ui_scale: UiScale | str | None = None,
    contrast_mode: ContrastMode | str | None = None,
) -> FrontendRunResult:
    """Launch the title/save-load scene for the 2D frontend."""

    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    try:
        import pygame
    except ModuleNotFoundError as error:
        raise Frontend2DUnavailableError(
            "pygame-ce is not installed. Install the optional 2D runtime first."
        ) from error

    from nexus_tech.frontend_2d import scenes
    from nexus_tech.frontend_2d.widgets import (
        active_contrast_mode,
        configure_contrast_mode,
        create_fonts,
    )

    previous_contrast_mode = active_contrast_mode()
    try:
        pygame.init()
        pygame.font.init()
        window_size = clamp_frontend_viewport_size(window_size)
        flags = pygame.RESIZABLE | (pygame.HIDDEN if headless else 0)
        surface = pygame.display.set_mode(window_size, flags)
        pygame.display.set_caption("NEXUS TECH 2D | Menu")
        coordinator = SaveLoadCoordinator(db_path)
        (
            preferences,
            fonts,
            apply_preferences,
            preference_provider,
            resize_fonts,
        ) = _build_preference_runtime(
            pygame=pygame,
            scenes=scenes,
            coordinator=coordinator,
            create_fonts=create_fonts,
            configure_contrast_mode=configure_contrast_mode,
            motion_mode=motion_mode,
            ui_scale=ui_scale,
            contrast_mode=contrast_mode,
            viewport_size=window_size,
        )
        scene = scenes.TitleScene(
            pygame=pygame,
            fonts=fonts,
            state=create_new_game("NEXUS TECH", "Nexus One"),
            rng=RandomSource(seed=None),
            slot_name="active",
            save_callback=lambda game_state, game_rng, current_slot: coordinator.save_game(
                current_slot,
                game_state,
                game_rng,
            ),
            coordinator=coordinator,
            info_message="Load a save, review archives, or boot the default run from inside 2D.",
            motion_mode=preferences.motion_mode,
            preferences=preferences,
            preference_callback=apply_preferences,
            preference_provider=preference_provider,
            entry_transition="boot_title",
        )
    except Exception:
        pygame.quit()
        configure_contrast_mode(previous_contrast_mode, mirror_modules=(scenes,))
        raise
    try:
        return _run_frontend_loop(
            pygame=pygame,
            surface=surface,
            scene=scene,
            flags=flags,
            max_frames=max_frames,
            resize_fonts=resize_fonts,
        )
    finally:
        configure_contrast_mode(previous_contrast_mode, mirror_modules=(scenes,))


def _build_preference_runtime(
    *,
    pygame,
    scenes,
    coordinator: SaveLoadCoordinator,
    create_fonts,
    configure_contrast_mode,
    motion_mode: MotionMode | str | None,
    ui_scale: UiScale | str | None,
    contrast_mode: ContrastMode | str | None,
    viewport_size: tuple[int, int],
) -> tuple[
    FrontendPreferences,
    object,
    Callable[[FrontendPreferences], object],
    Callable[[], FrontendPreferences],
    Callable[[tuple[int, int]], object],
]:
    """Build one mutable preference bridge shared by every scene transition."""

    current = coordinator.load_frontend_preferences().with_overrides(
        motion_mode=motion_mode,
        ui_scale=ui_scale,
        contrast_mode=contrast_mode,
    )
    configure_contrast_mode(current.contrast_mode, mirror_modules=(scenes,))
    current_viewport = viewport_size
    fonts = create_fonts(pygame, current.ui_scale, viewport_size=current_viewport)

    def apply_preferences(preferences: FrontendPreferences):
        nonlocal current
        coordinator.save_frontend_preferences(preferences)
        configure_contrast_mode(preferences.contrast_mode, mirror_modules=(scenes,))
        current = preferences
        return create_fonts(
            pygame,
            preferences.ui_scale,
            viewport_size=current_viewport,
        )

    def preference_provider() -> FrontendPreferences:
        return current

    def resize_fonts(size: tuple[int, int]):
        nonlocal current_viewport
        current_viewport = size
        return create_fonts(
            pygame,
            current.ui_scale,
            viewport_size=current_viewport,
        )

    return current, fonts, apply_preferences, preference_provider, resize_fonts


def _run_frontend_loop(
    *,
    pygame,
    surface,
    scene,
    flags: int,
    max_frames: int | None,
    resize_fonts: Callable[[tuple[int, int]], object] | None = None,
) -> FrontendRunResult:
    """Run the shared event loop for any 2D frontend scene."""

    clock = pygame.time.Clock()
    frame_count = 0
    try:
        while not scene.should_exit:
            dt = clock.tick(60) / 1000
            for event in pygame.event.get():
                if event.type == pygame.VIDEORESIZE:
                    safe_size = clamp_frontend_viewport_size(event.size)
                    surface = pygame.display.set_mode(safe_size, flags)
                    if resize_fonts is not None:
                        scene.fonts = resize_fonts(safe_size)
                    continue
                scene.handle_event(event)
            scene.update(dt)
            next_scene = scene.pop_next_scene()
            if next_scene is not None:
                scene = next_scene
                continue
            scene.draw(surface)
            pygame.display.flip()
            frame_count += 1
            if max_frames is not None and frame_count >= max_frames:
                scene.should_exit = True
                scene.exit_reason = "max_frames"

        saved_on_exit = scene.maybe_save_on_exit()
        return FrontendRunResult(
            state=scene.state,
            rng=scene.rng,
            slot_name=scene.slot_name,
            exit_reason=scene.exit_reason,
            saved_on_exit=saved_on_exit,
        )
    finally:
        pygame.quit()
