"""Pygame bootstrap for the lightweight NEXUS TECH 2D frontend."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from nexus_tech.domain.models import GameState
from nexus_tech.frontend_2d.accessibility import ContrastMode, UiScale
from nexus_tech.frontend_2d.tween import MotionMode, normalize_motion_mode
from nexus_tech.persistence.save_coordinator import SaveLoadCoordinator
from nexus_tech.simulation.engine import create_new_game
from nexus_tech.simulation.randomness import RandomSource


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
    motion_mode: MotionMode | str = MotionMode.FULL,
    ui_scale: UiScale | str = UiScale.STANDARD,
    contrast_mode: ContrastMode | str = ContrastMode.STANDARD,
) -> FrontendRunResult:
    """Launch the lightweight animated 2D dashboard."""

    motion_mode = normalize_motion_mode(motion_mode)
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
    configure_contrast_mode(contrast_mode, mirror_modules=(scenes,))
    try:
        pygame.init()
        pygame.font.init()
        flags = pygame.RESIZABLE | (pygame.HIDDEN if headless else 0)
        surface = pygame.display.set_mode(window_size, flags)
        pygame.display.set_caption(f"NEXUS TECH 2D | {state.company.name}")
        fonts = create_fonts(pygame, ui_scale)
        coordinator = SaveLoadCoordinator(db_path)
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
            motion_mode=motion_mode,
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
        )
    finally:
        configure_contrast_mode(previous_contrast_mode, mirror_modules=(scenes,))


def launch_2d_menu(
    *,
    db_path: Path,
    headless: bool = False,
    max_frames: int | None = None,
    window_size: tuple[int, int] = (1440, 900),
    motion_mode: MotionMode | str = MotionMode.FULL,
    ui_scale: UiScale | str = UiScale.STANDARD,
    contrast_mode: ContrastMode | str = ContrastMode.STANDARD,
) -> FrontendRunResult:
    """Launch the title/save-load scene for the 2D frontend."""

    motion_mode = normalize_motion_mode(motion_mode)
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
    configure_contrast_mode(contrast_mode, mirror_modules=(scenes,))
    try:
        pygame.init()
        pygame.font.init()
        flags = pygame.RESIZABLE | (pygame.HIDDEN if headless else 0)
        surface = pygame.display.set_mode(window_size, flags)
        pygame.display.set_caption("NEXUS TECH 2D | Menu")
        fonts = create_fonts(pygame, ui_scale)
        coordinator = SaveLoadCoordinator(db_path)
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
            motion_mode=motion_mode,
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
        )
    finally:
        configure_contrast_mode(previous_contrast_mode, mirror_modules=(scenes,))


def _run_frontend_loop(
    *, pygame, surface, scene, flags: int, max_frames: int | None
) -> FrontendRunResult:
    """Run the shared event loop for any 2D frontend scene."""

    clock = pygame.time.Clock()
    frame_count = 0
    try:
        while not scene.should_exit:
            dt = clock.tick(60) / 1000
            for event in pygame.event.get():
                if event.type == pygame.VIDEORESIZE:
                    surface = pygame.display.set_mode(event.size, flags)
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
