"""Pure control-guide content for the lightweight 2D frontend."""

from __future__ import annotations

__all__ = ["RUN_HELP_KEYCAPS"]


RUN_HELP_KEYCAPS: tuple[tuple[str, str], ...] = (
    ("Tab", "Next product / next inspector section"),
    ("1-8", "Open deep panels"),
    ("0", "Toggle Focus View / More Actions"),
    ("V", "Guided / full Endgame actions"),
    ("I", "Inspect the current deep panel"),
    ("C", "Run primary coach command"),
    ("Q/F/M/D", "Product actions"),
    ("H/A/O", "Hire / assign / partner"),
    ("Y/R/B/U", "Strategy, roadmap, budget, support"),
    ("Space", "End turn"),
    ("P", "Pause menu: all run and exit options"),
    ("Esc", "Back out of overlay, then pause"),
    ("Z/X", "Inspector sort / filter"),
    ("A/H", "Inspector actionable / hotspot focus"),
    ("PgUp/PgDn", "Inspector page"),
    ("Enter", "Run selected inspector action"),
    ("F1/?", "Toggle this help"),
)
