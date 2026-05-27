"""Small drawing helpers for the lightweight 2D frontend."""

from __future__ import annotations

from dataclasses import dataclass

BACKGROUND = (12, 18, 28)
GRID = (20, 32, 48)
PANEL = (22, 30, 43)
PANEL_ALT = (17, 24, 35)
BORDER = (58, 75, 99)
TEXT = (232, 239, 245)
MUTED = (143, 160, 184)
GOOD = (60, 190, 120)
WARN = (240, 184, 64)
DANGER = (237, 91, 91)
INFO = (88, 166, 255)
SELECTION = (115, 207, 255)
OVERLAY = (8, 10, 14, 180)


@dataclass(frozen=True)
class FontPack:
    """Fonts used by the 2D frontend."""

    title: object
    heading: object
    body: object
    small: object
    mono: object


def create_fonts(pygame) -> FontPack:
    """Build a compact font set with system fallbacks."""

    return FontPack(
        title=pygame.font.SysFont("Avenir Next, Helvetica Neue, Arial", 28, bold=True),
        heading=pygame.font.SysFont("Avenir Next, Helvetica Neue, Arial", 18, bold=True),
        body=pygame.font.SysFont("Avenir Next, Helvetica Neue, Arial", 15),
        small=pygame.font.SysFont("Avenir Next, Helvetica Neue, Arial", 12),
        mono=pygame.font.SysFont("Menlo, Monaco, Courier New", 14),
    )


def tone_color(tone: str) -> tuple[int, int, int]:
    """Resolve a semantic tone into a color."""

    if tone == "success":
        return GOOD
    if tone == "warning":
        return WARN
    if tone == "danger":
        return DANGER
    return INFO


def draw_grid(surface, pygame) -> None:
    """Paint a subtle background grid."""

    width, height = surface.get_size()
    surface.fill(BACKGROUND)
    for x_pos in range(0, width, 48):
        pygame.draw.line(surface, GRID, (x_pos, 0), (x_pos, height), 1)
    for y_pos in range(0, height, 48):
        pygame.draw.line(surface, GRID, (0, y_pos), (width, y_pos), 1)


def draw_panel(surface, pygame, rect, *, title: str, accent: tuple[int, int, int]) -> object:
    """Draw a framed panel and return its inner content rect."""

    pygame.draw.rect(surface, PANEL, rect, border_radius=18)
    pygame.draw.rect(surface, BORDER, rect, width=1, border_radius=18)
    header_rect = pygame.Rect(rect.left, rect.top, rect.width, 34)
    pygame.draw.rect(
        surface,
        PANEL_ALT,
        header_rect,
        border_top_left_radius=18,
        border_top_right_radius=18,
    )
    pygame.draw.rect(
        surface,
        accent,
        (rect.left + 1, rect.top + 1, rect.width - 2, 4),
        border_radius=4,
    )
    return pygame.Rect(rect.left + 16, rect.top + 44, rect.width - 32, rect.height - 60)


def draw_progress_bar(surface, pygame, rect, *, ratio: float, color: tuple[int, int, int]) -> None:
    """Draw one compact progress bar."""

    safe_ratio = max(0.0, min(1.0, ratio))
    pygame.draw.rect(surface, (31, 42, 58), rect, border_radius=8)
    fill_width = max(6, int(rect.width * safe_ratio)) if safe_ratio > 0 else 0
    if fill_width > 0:
        fill_rect = pygame.Rect(rect.left, rect.top, fill_width, rect.height)
        pygame.draw.rect(surface, color, fill_rect, border_radius=8)


def draw_wrapped_text(
    surface,
    font,
    text: str,
    color: tuple[int, int, int],
    rect,
    *,
    line_height: int = 18,
    max_lines: int | None = None,
) -> int:
    """Draw wrapped text and return the consumed height."""

    words = text.split()
    if not words:
        return 0
    lines: list[str] = []
    current_line = words[0]
    for word in words[1:]:
        candidate = f"{current_line} {word}"
        if font.size(candidate)[0] <= rect.width:
            current_line = candidate
            continue
        lines.append(current_line)
        current_line = word
    lines.append(current_line)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        if not lines[-1].endswith("..."):
            lines[-1] = f"{lines[-1].rstrip('.')}..."
    for index, line in enumerate(lines):
        text_surface = font.render(line, True, color)
        surface.blit(text_surface, (rect.left, rect.top + index * line_height))
    return len(lines) * line_height


def draw_keycap(surface, pygame, font, *, rect, key_text: str, label: str) -> None:
    """Draw one compact keyboard hint chip."""

    pygame.draw.rect(surface, PANEL_ALT, rect, border_radius=12)
    pygame.draw.rect(surface, BORDER, rect, width=1, border_radius=12)
    key_surface = font.render(key_text, True, TEXT)
    label_surface = font.render(label, True, MUTED)
    surface.blit(key_surface, (rect.left + 10, rect.top + 7))
    surface.blit(label_surface, (rect.left + 62, rect.top + 7))


def draw_button(
    surface,
    pygame,
    *,
    rect,
    title: str,
    detail: str,
    accent: tuple[int, int, int],
    title_font,
    detail_font,
    enabled: bool = True,
) -> None:
    """Draw one clickable action or modal button."""

    fill = PANEL_ALT if enabled else (18, 22, 28)
    border = accent if enabled else BORDER
    title_color = TEXT if enabled else MUTED
    detail_color = MUTED if enabled else (100, 112, 128)
    pygame.draw.rect(surface, fill, rect, border_radius=14)
    pygame.draw.rect(surface, border, rect, width=1, border_radius=14)
    pygame.draw.rect(
        surface,
        border,
        (rect.left + 1, rect.top + 1, rect.width - 2, 4),
        border_radius=4,
    )
    title_surface = title_font.render(title, True, title_color)
    detail_surface = detail_font.render(detail, True, detail_color)
    surface.blit(title_surface, (rect.left + 12, rect.top + 10))
    surface.blit(detail_surface, (rect.left + 12, rect.top + 34))
