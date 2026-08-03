"""Shared responsive frame geometry for the 2D frontend."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

MIN_FRONTEND_WIDTH = 820
MIN_FRONTEND_HEIGHT = 620
MIN_FRONTEND_VIEWPORT = (MIN_FRONTEND_WIDTH, MIN_FRONTEND_HEIGHT)
MAX_FRONTEND_CANVAS_WIDTH = 1440
MAX_FRONTEND_CANVAS_HEIGHT = 900
MAX_FRONTEND_CANVAS = (MAX_FRONTEND_CANVAS_WIDTH, MAX_FRONTEND_CANVAS_HEIGHT)


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
    canvas: RectBounds
    header: RectBounds
    content: RectBounds
    footer: RectBounds


def resolve_frontend_canvas_bounds(width: int, height: int) -> RectBounds:
    """Return a centered design canvas that stays readable on very large displays."""

    canvas_width = min(max(0, width), MAX_FRONTEND_CANVAS_WIDTH)
    canvas_height = min(max(0, height), MAX_FRONTEND_CANVAS_HEIGHT)
    return RectBounds(
        left=max(0, (width - canvas_width) // 2),
        top=max(0, (height - canvas_height) // 2),
        width=canvas_width,
        height=canvas_height,
    )


def build_balanced_grid(
    bounds: RectBounds,
    *,
    item_count: int,
    columns: int,
    row_height: int,
    column_gap: int,
    row_gap: int,
) -> tuple[RectBounds, ...]:
    """Build equal-width grid cells and center an incomplete final row."""

    if item_count <= 0 or bounds.width <= 0 or bounds.height <= 0:
        return ()
    safe_columns = max(1, min(columns, item_count))
    card_width = max(
        1,
        (bounds.width - column_gap * (safe_columns - 1)) // safe_columns,
    )
    cells: list[RectBounds] = []
    for index in range(item_count):
        row = index // safe_columns
        column = index % safe_columns
        remaining = item_count - row * safe_columns
        row_count = min(safe_columns, remaining)
        row_width = card_width * row_count + column_gap * max(0, row_count - 1)
        row_left = bounds.left + max(0, (bounds.width - row_width) // 2)
        cells.append(
            RectBounds(
                left=row_left + column * (card_width + column_gap),
                top=bounds.top + row * (row_height + row_gap),
                width=card_width,
                height=row_height,
            )
        )
    return tuple(cells)


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

    canvas = resolve_frontend_canvas_bounds(width, height)
    selected = profile or resolve_layout_profile(canvas.width, canvas.height)
    margin = selected.margin
    gap = selected.gap
    nav_band = selected.nav_band if nav_visible else 0
    available_width = max(0, canvas.width - margin * 2)
    content_left = canvas.left + margin
    header = RectBounds(
        content_left,
        canvas.top + margin + nav_band,
        available_width,
        header_height,
    )
    footer_top = max(
        header.top + header.height + gap,
        canvas.top + canvas.height - footer_height - margin,
    )
    footer = RectBounds(content_left, footer_top, available_width, footer_height)
    content_top = header.top + header.height + gap
    content_bottom = max(content_top, footer.top - gap)
    content = RectBounds(
        content_left,
        content_top,
        available_width,
        max(0, content_bottom - content_top),
    )
    return FrameLayout(
        profile=selected,
        canvas=canvas,
        header=header,
        content=content,
        footer=footer,
    )
