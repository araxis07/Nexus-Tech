"""Small drawing helpers for the lightweight 2D frontend."""

from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType

from nexus_tech.frontend_2d.accessibility import (
    ContrastMode,
    UiScale,
    normalize_contrast_mode,
    normalize_ui_scale,
)

_STANDARD_PALETTE = {
    "BACKGROUND": (8, 14, 23),
    "GRID": (14, 25, 39),
    "PANEL": (22, 36, 54),
    "PANEL_ALT": (13, 22, 34),
    "BORDER": (74, 98, 128),
    "TEXT": (232, 239, 245),
    "MUTED": (169, 184, 205),
    "GOOD": (72, 210, 139),
    "WARN": (250, 199, 83),
    "DANGER": (248, 104, 104),
    "INFO": (97, 181, 255),
    "SELECTION": (115, 207, 255),
    "OVERLAY": (8, 10, 14, 180),
}
_HIGH_CONTRAST_PALETTE = {
    "BACKGROUND": (0, 0, 0),
    "GRID": (28, 34, 42),
    "PANEL": (12, 18, 24),
    "PANEL_ALT": (5, 9, 13),
    "BORDER": (190, 207, 228),
    "TEXT": (255, 255, 255),
    "MUTED": (216, 226, 239),
    "GOOD": (0, 235, 158),
    "WARN": (255, 215, 74),
    "DANGER": (255, 118, 140),
    "INFO": (86, 194, 255),
    "SELECTION": (255, 226, 92),
    "OVERLAY": (0, 0, 0, 224),
}
_ACTIVE_CONTRAST_MODE = ContrastMode.STANDARD

BACKGROUND = _STANDARD_PALETTE["BACKGROUND"]
GRID = _STANDARD_PALETTE["GRID"]
PANEL = _STANDARD_PALETTE["PANEL"]
PANEL_ALT = _STANDARD_PALETTE["PANEL_ALT"]
BORDER = _STANDARD_PALETTE["BORDER"]
TEXT = _STANDARD_PALETTE["TEXT"]
MUTED = _STANDARD_PALETTE["MUTED"]
GOOD = _STANDARD_PALETTE["GOOD"]
WARN = _STANDARD_PALETTE["WARN"]
DANGER = _STANDARD_PALETTE["DANGER"]
INFO = _STANDARD_PALETTE["INFO"]
SELECTION = _STANDARD_PALETTE["SELECTION"]
OVERLAY = _STANDARD_PALETTE["OVERLAY"]


@dataclass(frozen=True)
class FontPack:
    """Fonts used by the 2D frontend."""

    title: object
    heading: object
    body: object
    small: object
    mono: object


@dataclass(frozen=True)
class TypographyAuditEvent:
    """One fitted or clamped text draw observed during a visual audit."""

    kind: str
    ratio: float
    severe: bool = False


_TYPOGRAPHY_AUDIT_EVENTS: list[TypographyAuditEvent] | None = None


def start_typography_audit() -> None:
    """Start recording fitted/clamped text draw calls for one frame."""

    global _TYPOGRAPHY_AUDIT_EVENTS
    _TYPOGRAPHY_AUDIT_EVENTS = []


def finish_typography_audit() -> tuple[TypographyAuditEvent, ...]:
    """Return recorded text draw calls and stop the current frame audit."""

    global _TYPOGRAPHY_AUDIT_EVENTS
    events = tuple(_TYPOGRAPHY_AUDIT_EVENTS or ())
    _TYPOGRAPHY_AUDIT_EVENTS = None
    return events


def configure_contrast_mode(
    value: ContrastMode | str,
    *,
    mirror_modules: tuple[ModuleType, ...] = (),
) -> ContrastMode:
    """Apply one semantic palette and mirror imported colors into scene modules."""

    global _ACTIVE_CONTRAST_MODE

    mode = normalize_contrast_mode(value)
    palette = _HIGH_CONTRAST_PALETTE if mode is ContrastMode.HIGH else _STANDARD_PALETTE
    globals().update(palette)
    _ACTIVE_CONTRAST_MODE = mode
    for module in mirror_modules:
        for name, color in palette.items():
            if hasattr(module, name):
                setattr(module, name, color)
    return mode


def active_contrast_mode() -> ContrastMode:
    """Return the palette profile currently applied to drawing helpers."""

    return _ACTIVE_CONTRAST_MODE


def create_fonts(pygame, ui_scale: UiScale | str = UiScale.STANDARD) -> FontPack:
    """Build a compact font set with deterministic metrics across OS runners."""

    scale = normalize_ui_scale(ui_scale).factor
    return FontPack(
        title=_default_font(pygame, _scaled_font_size(34, scale), bold=True),
        heading=_default_font(pygame, _scaled_font_size(24, scale), bold=True),
        body=_default_font(pygame, _scaled_font_size(20, scale)),
        small=_default_font(pygame, _scaled_font_size(17, scale)),
        mono=_default_font(pygame, _scaled_font_size(18, scale)),
    )


def _scaled_font_size(size: int, scale: float) -> int:
    return max(12, round(size * scale))


def _default_font(pygame, size: int, *, bold: bool = False):
    font = pygame.font.Font(None, size)
    font.set_bold(bold)
    return font


def tone_color(tone: str) -> tuple[int, int, int]:
    """Resolve a semantic tone into a color."""

    if tone == "success":
        return GOOD
    if tone == "warning":
        return WARN
    if tone == "danger":
        return DANGER
    return INFO


def blend_color(
    source: tuple[int, int, int],
    target: tuple[int, int, int],
    amount: float,
) -> tuple[int, int, int]:
    """Blend one RGB color toward another."""

    safe_amount = max(0.0, min(1.0, amount))
    return tuple(
        int(source[index] + (target[index] - source[index]) * safe_amount) for index in range(3)
    )


def draw_grid(surface, pygame) -> None:
    """Paint a subtle background grid."""

    width, height = surface.get_size()
    surface.fill(BACKGROUND)
    for x_pos in range(0, width, 64):
        pygame.draw.line(surface, GRID, (x_pos, 0), (x_pos, height), 1)
    for y_pos in range(0, height, 64):
        pygame.draw.line(surface, GRID, (0, y_pos), (width, y_pos), 1)


def draw_panel(
    surface,
    pygame,
    rect,
    *,
    title: str,
    accent: tuple[int, int, int],
    emphasis: float = 0.0,
    lift: int = 0,
) -> object:
    """Draw a framed panel and return its inner content rect."""

    safe_emphasis = max(0.0, min(1.0, emphasis))
    visual_rect = pygame.Rect(rect.left, rect.top - lift, rect.width, rect.height)
    panel_fill = blend_color(PANEL, accent, safe_emphasis * 0.16)
    panel_border = blend_color(BORDER, accent, safe_emphasis * 0.48)
    header_fill = blend_color(PANEL_ALT, accent, safe_emphasis * 0.12)
    border_width = 2 if safe_emphasis >= 0.45 else 1
    accent_height = 4 + int(safe_emphasis * 2)

    pygame.draw.rect(surface, panel_fill, visual_rect, border_radius=18)
    pygame.draw.rect(surface, panel_border, visual_rect, width=border_width, border_radius=18)
    header_rect = pygame.Rect(visual_rect.left, visual_rect.top, visual_rect.width, 34)
    pygame.draw.rect(
        surface,
        header_fill,
        header_rect,
        border_top_left_radius=18,
        border_top_right_radius=18,
    )
    pygame.draw.rect(
        surface,
        blend_color(accent, TEXT, safe_emphasis * 0.15),
        (visual_rect.left + 1, visual_rect.top + 1, visual_rect.width - 2, accent_height),
        border_radius=4,
    )
    return pygame.Rect(
        visual_rect.left + 16,
        visual_rect.top + 44,
        visual_rect.width - 32,
        visual_rect.height - 60,
    )


def draw_progress_bar(
    surface,
    pygame,
    rect,
    *,
    ratio: float,
    color: tuple[int, int, int],
    emphasis: float = 0.0,
) -> None:
    """Draw one compact progress bar."""

    safe_ratio = max(0.0, min(1.0, ratio))
    safe_emphasis = max(0.0, min(1.0, emphasis))
    pygame.draw.rect(
        surface,
        blend_color((31, 42, 58), color, safe_emphasis * 0.14),
        rect,
        border_radius=8,
    )
    if safe_emphasis >= 0.08:
        pygame.draw.rect(
            surface,
            blend_color(BORDER, color, safe_emphasis * 0.45),
            rect,
            width=1,
            border_radius=8,
        )
    fill_width = max(6, int(rect.width * safe_ratio)) if safe_ratio > 0 else 0
    if fill_width > 0:
        fill_rect = pygame.Rect(rect.left, rect.top, fill_width, rect.height)
        pygame.draw.rect(
            surface,
            blend_color(color, TEXT, safe_emphasis * 0.16),
            fill_rect,
            border_radius=8,
        )


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

    rect = surface.get_clip().clip(rect)
    if rect.width <= 0 or rect.height <= 0:
        return 0
    words = text.split()
    if not words:
        return 0
    lines: list[str] = []
    current_line = _fit_word(font, words[0], rect.width)
    for raw_word in words[1:]:
        word = _fit_word(font, raw_word, rect.width)
        candidate = f"{current_line} {word}"
        if font.size(candidate)[0] <= rect.width:
            current_line = candidate
            continue
        lines.append(current_line)
        current_line = word
    lines.append(current_line)
    height_limit = max(0, rect.height // max(1, line_height))
    line_limit = height_limit if max_lines is None else min(max_lines, height_limit)
    if line_limit <= 0:
        _record_typography_event("wrapped-hidden", 0.0, severe=True)
        return 0
    truncated = len(lines) > line_limit
    visible_lines = lines[:line_limit]
    if truncated and visible_lines:
        visible_lines[-1] = fit_text_line(font, f"{visible_lines[-1].rstrip('. ')}...", rect.width)
        _record_typography_event(
            "wrapped-clamp",
            line_limit / max(1, len(lines)),
            severe=False,
        )
    previous_clip = surface.get_clip()
    surface.set_clip(rect.clip(previous_clip))
    try:
        for index, line in enumerate(visible_lines):
            text_surface = font.render(line, True, color)
            surface.blit(text_surface, (rect.left, rect.top + index * line_height))
    finally:
        surface.set_clip(previous_clip)
    return len(visible_lines) * line_height


def fit_text_line(font, text: str, max_width: int) -> str:
    """Return a single line that fits inside max_width, using ASCII ellipsis."""

    clean_text = " ".join(text.split())
    if max_width <= 0 or not clean_text:
        return ""
    if font.size(clean_text)[0] <= max_width:
        return clean_text
    suffix = "..."
    if font.size(suffix)[0] > max_width:
        return ""
    low = 0
    high = len(clean_text)
    best = ""
    while low <= high:
        middle = (low + high) // 2
        candidate = f"{clean_text[:middle].rstrip()}{suffix}"
        if font.size(candidate)[0] <= max_width:
            best = candidate
            low = middle + 1
        else:
            high = middle - 1
    return best


def draw_text_line(
    surface,
    font,
    text: str,
    color: tuple[int, int, int],
    rect,
    *,
    align: str = "left",
    valign: str = "center",
) -> int:
    """Draw one clipped, fitted text line and return its rendered width."""

    rect = surface.get_clip().clip(rect)
    if rect.width <= 0 or rect.height <= 0:
        return 0
    line = fit_text_line(font, text, rect.width)
    if not line:
        if text.strip():
            _record_typography_event("line-hidden", 0.0, severe=True)
        return 0
    _record_text_fit_event("line-fit", font, text, line, rect.width, severe_threshold=0.36)
    text_surface = font.render(line, True, color)
    if align == "right":
        x_pos = rect.right - text_surface.get_width()
    elif align == "center":
        x_pos = rect.left + max(0, (rect.width - text_surface.get_width()) // 2)
    else:
        x_pos = rect.left
    if valign == "top":
        y_pos = rect.top
    elif valign == "bottom":
        y_pos = rect.bottom - text_surface.get_height()
    else:
        y_pos = rect.top + max(0, (rect.height - text_surface.get_height()) // 2)
    previous_clip = surface.get_clip()
    surface.set_clip(rect.clip(previous_clip))
    try:
        surface.blit(text_surface, (x_pos, y_pos))
    finally:
        surface.set_clip(previous_clip)
    return text_surface.get_width()


def _fit_word(font, word: str, max_width: int) -> str:
    if font.size(word)[0] <= max_width:
        return word
    return fit_text_line(font, word, max_width)


def draw_keycap(surface, pygame, font, *, rect, key_text: str, label: str) -> None:
    """Draw one compact keyboard hint chip."""

    pygame.draw.rect(surface, PANEL_ALT, rect, border_radius=12)
    pygame.draw.rect(surface, BORDER, rect, width=1, border_radius=12)
    key_width = 72
    draw_text_line(
        surface,
        font,
        key_text,
        TEXT,
        pygame.Rect(rect.left + 10, rect.top + 5, key_width, rect.height - 10),
    )
    draw_text_line(
        surface,
        font,
        label,
        MUTED,
        pygame.Rect(
            rect.left + key_width + 18,
            rect.top + 5,
            rect.width - key_width - 28,
            rect.height - 10,
        ),
    )


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
    selected: bool = False,
    emphasis: float = 0.0,
    lift: int = 0,
) -> None:
    """Draw one clickable action or modal button."""

    safe_emphasis = max(0.0, min(1.0, emphasis))
    visual_rect = pygame.Rect(rect.left, rect.top - lift, rect.width, rect.height)
    base_fill = (28, 40, 58) if selected and enabled else PANEL_ALT if enabled else (18, 22, 28)
    fill = blend_color(base_fill, accent, safe_emphasis * 0.18)
    border_seed = SELECTION if selected and enabled else accent if enabled else BORDER
    border = blend_color(border_seed, TEXT, safe_emphasis * 0.14)
    title_color = TEXT if enabled else MUTED
    detail_color = MUTED if enabled else (100, 112, 128)
    border_width = 2 if safe_emphasis >= 0.4 else 1
    pygame.draw.rect(surface, fill, visual_rect, border_radius=14)
    pygame.draw.rect(surface, border, visual_rect, width=border_width, border_radius=14)
    pygame.draw.rect(
        surface,
        border,
        (
            visual_rect.left + 1,
            visual_rect.top + 1,
            visual_rect.width - 2,
            4 + int(safe_emphasis * 2),
        ),
        border_radius=4,
    )
    if selected and enabled:
        pygame.draw.rect(
            surface,
            SELECTION,
            (visual_rect.left + 1, visual_rect.bottom - 5, visual_rect.width - 2, 3),
            border_radius=3,
        )
    show_detail = bool(detail) and visual_rect.height >= 46
    title_rect = pygame.Rect(
        visual_rect.left + 12,
        visual_rect.top + (8 if show_detail else 6),
        visual_rect.width - 24,
        22 if show_detail else visual_rect.height - 12,
    )
    fitted_title = fit_text_line(title_font, title, title_rect.width)
    _record_text_fit_event(
        "button-title-fit",
        title_font,
        title,
        fitted_title,
        title_rect.width,
        severe_threshold=0.58,
    )
    draw_text_line(surface, title_font, title, title_color, title_rect)
    if show_detail:
        detail_top = visual_rect.top + 28
        detail_rect = pygame.Rect(
            visual_rect.left + 12,
            detail_top,
            visual_rect.width - 24,
            max(0, visual_rect.bottom - detail_top - 5),
        )
        draw_wrapped_text(
            surface,
            detail_font,
            detail,
            detail_color,
            detail_rect,
            line_height=13 if visual_rect.height < 58 else 15,
            max_lines=2 if visual_rect.height >= 58 else 1,
        )


def _record_text_fit_event(
    kind: str,
    font,
    text: str,
    fitted_text: str,
    max_width: int,
    *,
    severe_threshold: float,
) -> None:
    clean_text = " ".join(text.split())
    if _TYPOGRAPHY_AUDIT_EVENTS is None or not clean_text:
        return
    original_width = font.size(clean_text)[0]
    if original_width <= max_width:
        return
    fitted_width = font.size(fitted_text)[0] if fitted_text else 0
    ratio = fitted_width / max(1, original_width)
    severe = ratio < severe_threshold or fitted_text in {"", "..."}
    _record_typography_event(kind, ratio, severe=severe)


def _record_typography_event(kind: str, ratio: float, *, severe: bool) -> None:
    if _TYPOGRAPHY_AUDIT_EVENTS is None:
        return
    _TYPOGRAPHY_AUDIT_EVENTS.append(
        TypographyAuditEvent(
            kind=kind,
            ratio=round(max(0.0, min(1.0, ratio)), 3),
            severe=severe,
        )
    )
