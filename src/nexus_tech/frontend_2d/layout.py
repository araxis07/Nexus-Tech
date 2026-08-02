"""Shared responsive frame geometry for the 2D frontend."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

MIN_FRONTEND_WIDTH = 820
MIN_FRONTEND_HEIGHT = 620
MIN_FRONTEND_VIEWPORT = (MIN_FRONTEND_WIDTH, MIN_FRONTEND_HEIGHT)


def clamp_frontend_viewport_size(size: tuple[int, int]) -> tuple[int, int]:
    """Keep live windows inside the layout contract supported by every scene."""

    width, height = size
    return max(MIN_FRONTEND_WIDTH, width), max(MIN_FRONTEND_HEIGHT, height)


def frontend_viewport_is_supported(size: tuple[int, int]) -> bool:
    """Return whether a viewport can render every scene without collapsing lanes."""

    width, height = size
    return width >= MIN_FRONTEND_WIDTH and height >= MIN_FRONTEND_HEIGHT


class LayoutDensity(StrEnum):
    """Named viewport-density bands used by every scene shell."""

    COMPACT = "compact"
    STANDARD = "standard"
    SPACIOUS = "spacious"


@dataclass(frozen=True)
class RectBounds:
    """Renderer-independent rectangle coordinates."""

    left: int
    top: int
    width: int
    height: int

    def as_tuple(self) -> tuple[int, int, int, int]:
        """Return coordinates accepted by pygame.Rect."""

        return self.left, self.top, self.width, self.height


@dataclass(frozen=True)
class ResponsiveLayoutProfile:
    """Spacing and shell dimensions for one viewport class."""

    density: LayoutDensity
    margin: int
    gap: int
    nav_band: int
    title_header_height: int
    run_header_height: int
    title_footer_height: int
    minimum_control_height: int


@dataclass(frozen=True)
class FrameLayout:
    """Non-overlapping header, content, and footer regions."""

    profile: ResponsiveLayoutProfile
    header: RectBounds
    content: RectBounds
    footer: RectBounds


def resolve_layout_profile(width: int, height: int) -> ResponsiveLayoutProfile:
    """Resolve deterministic spacing tokens for a viewport."""

    if width < 940 or height < 700:
        return ResponsiveLayoutProfile(
            density=LayoutDensity.COMPACT,
            margin=20,
            gap=12,
            nav_band=46,
            title_header_height=92,
            run_header_height=124,
            title_footer_height=72,
            minimum_control_height=40,
        )
    if width < 1260 or height < 820:
        return ResponsiveLayoutProfile(
            density=LayoutDensity.STANDARD,
            margin=22,
            gap=14,
            nav_band=46,
            title_header_height=104,
            run_header_height=148,
            title_footer_height=88,
            minimum_control_height=42,
        )
    return ResponsiveLayoutProfile(
        density=LayoutDensity.SPACIOUS,
        margin=24,
        gap=16,
        nav_band=46,
        title_header_height=104,
        run_header_height=148,
        title_footer_height=92,
        minimum_control_height=44,
    )


def build_frame_layout(
    width: int,
    height: int,
    *,
    header_height: int,
    footer_height: int,
    nav_visible: bool,
    profile: ResponsiveLayoutProfile | None = None,
) -> FrameLayout:
    """Build shell regions that reserve navigation and never overlap."""

    selected = profile or resolve_layout_profile(width, height)
    margin = selected.margin
    gap = selected.gap
    nav_band = selected.nav_band if nav_visible else 0
    available_width = max(0, width - margin * 2)
    header = RectBounds(margin, margin + nav_band, available_width, header_height)
    footer_top = max(header.top + header.height + gap, height - footer_height - margin)
    footer = RectBounds(margin, footer_top, available_width, footer_height)
    content_top = header.top + header.height + gap
    content_bottom = max(content_top, footer.top - gap)
    content = RectBounds(
        margin,
        content_top,
        available_width,
        max(0, content_bottom - content_top),
    )
    return FrameLayout(profile=selected, header=header, content=content, footer=footer)
