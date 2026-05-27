"""Pygame bootstrap for the lightweight NEXUS TECH 2D frontend."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from nexus_tech.domain.models import GameState
from nexus_tech.persistence.save_coordinator import SaveLoadCoordinator
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

    from nexus_tech.frontend_2d.scenes import MainGameScene
    from nexus_tech.frontend_2d.widgets import create_fonts

    pygame.init()
    pygame.font.init()
    flags = pygame.RESIZABLE | (pygame.HIDDEN if headless else 0)
    surface = pygame.display.set_mode(window_size, flags)
    pygame.display.set_caption(f"NEXUS TECH 2D | {state.company.name}")
    fonts = create_fonts(pygame)
    coordinator = SaveLoadCoordinator(db_path)
    scene = MainGameScene(
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
    )
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
