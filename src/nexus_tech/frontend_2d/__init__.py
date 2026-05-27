"""Minimal 2D frontend for the NEXUS TECH simulation."""

from nexus_tech.frontend_2d.app import (
    Frontend2DUnavailableError,
    FrontendRunResult,
    launch_2d_frontend,
    launch_2d_menu,
)

__all__ = [
    "Frontend2DUnavailableError",
    "FrontendRunResult",
    "launch_2d_frontend",
    "launch_2d_menu",
]
