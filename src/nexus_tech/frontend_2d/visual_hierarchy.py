"""Pure visual hierarchy policies for the responsive 2D frontend."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.frontend_2d.layout import LayoutDensity, resolve_layout_profile


@dataclass(frozen=True)
class PanelChromePolicy:
    """Relative color and geometry weights for one panel shell."""

    fill_accent_mix: float
    border_mute_mix: float
    border_accent_mix: float
    header_accent_mix: float
    accent_line_mix: float
    border_width: int
    accent_height: int


@dataclass(frozen=True)
class FocusCardTextPolicy:
    """Font roles and line budget for one responsive decision card."""

    headline_role: str
    detail_role: str
    detail_max_lines: int


_OVERLAY_ALPHA_FLOORS = {
    "delete": 216,
    "help": 226,
    "inspector": 232,
    "outcome": 226,
    "panel": 228,
    "pause": 218,
    "pause_settings": 224,
    "pending": 212,
    "picker": 216,
    "text_input": 220,
}


def resolve_panel_chrome(emphasis: float) -> PanelChromePolicy:
    """Keep default containers quiet while preserving emphasized state changes."""

    safe_emphasis = max(0.0, min(1.0, emphasis))
    return PanelChromePolicy(
        fill_accent_mix=safe_emphasis * 0.16,
        border_mute_mix=0.34 * (1.0 - safe_emphasis),
        border_accent_mix=0.14 + safe_emphasis * 0.42,
        header_accent_mix=0.04 + safe_emphasis * 0.10,
        accent_line_mix=0.58 + safe_emphasis * 0.34,
        border_width=2 if safe_emphasis >= 0.45 else 1,
        accent_height=3 + round(safe_emphasis * 3),
    )


def resolve_overlay_backdrop_alpha(
    overlay_key: str,
    *,
    base_alpha: int,
    pulse: float = 0.0,
) -> int:
    """Return a stable dim level that keeps blocking overlays visually isolated."""

    normalized_key = overlay_key.strip().lower()
    floor = _OVERLAY_ALPHA_FLOORS.get(normalized_key, 212)
    safe_base = max(0, min(255, base_alpha))
    safe_pulse = max(0.0, min(1.0, pulse))
    return min(242, max(safe_base, floor) + round(safe_pulse * 8))


def resolve_viewport_typography_scale(width: int, height: int) -> float:
    """Use spare viewport area for readability without pressuring compact layouts."""

    density = resolve_layout_profile(width, height).density
    if density is LayoutDensity.SPACIOUS:
        return 1.12
    if density is LayoutDensity.STANDARD:
        return 1.03
    return 1.0


def resolve_focus_card_text_policy(
    *,
    width: int,
    height: int,
    compact: bool,
) -> FocusCardTextPolicy:
    """Increase decision-card hierarchy only when the card can contain it safely."""

    if not compact and width >= 340 and height >= 140:
        return FocusCardTextPolicy(
            headline_role="heading",
            detail_role="body",
            detail_max_lines=4,
        )
    if not compact and height >= 86:
        return FocusCardTextPolicy(
            headline_role="body",
            detail_role="small",
            detail_max_lines=3,
        )
    return FocusCardTextPolicy(
        headline_role="small",
        detail_role="small",
        detail_max_lines=2,
    )
