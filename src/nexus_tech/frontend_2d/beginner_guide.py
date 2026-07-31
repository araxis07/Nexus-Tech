"""Beginner-first learning path shared by title and in-run help."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "ADVANCED_RUN_CONTROLS",
    "BEGINNER_GUIDE_PAGES",
    "ESSENTIAL_RUN_CONTROLS",
    "BeginnerGuidePage",
    "BeginnerGuideStep",
    "clamp_guide_page_index",
    "resolve_guide_page",
]


@dataclass(frozen=True)
class BeginnerGuideStep:
    """One short, actionable instruction inside a guide page."""

    marker: str
    title: str
    detail: str
    tone: str


@dataclass(frozen=True)
class BeginnerGuidePage:
    """One page in the progressive beginner learning path."""

    key: str
    eyebrow: str
    title: str
    summary: str
    steps: tuple[BeginnerGuideStep, ...]
    tip: str


BEGINNER_GUIDE_PAGES: tuple[BeginnerGuidePage, ...] = (
    BeginnerGuidePage(
        key="goal",
        eyebrow="START HERE",
        title="Build a company that survives",
        summary=(
            "Turn a small startup into a durable business, then reach IPO, acquisition, "
            "or independence before cash or pressure ends the run."
        ),
        steps=(
            BeginnerGuideStep(
                "1",
                "Read the objective",
                "The Current Focus card tells you what matters now.",
                "info",
            ),
            BeginnerGuideStep(
                "2",
                "Make one useful move",
                "Use the green Recommended action when unsure.",
                "success",
            ),
            BeginnerGuideStep(
                "3",
                "Protect the runway",
                "Check cash, risk, and warnings before ending a turn.",
                "warning",
            ),
        ),
        tip="You do not need to learn every panel before starting.",
    ),
    BeginnerGuidePage(
        key="turn",
        eyebrow="CORE LOOP",
        title="Play one turn in three steps",
        summary=(
            "Every turn follows the same rhythm: understand the objective, choose an action, "
            "then review the forecast before resolving."
        ),
        steps=(
            BeginnerGuideStep(
                "1", "Read NEXT", "Follow the highlighted NEXT coach move first.", "info"
            ),
            BeginnerGuideStep(
                "2",
                "Spend action points",
                "Choose Recommended or open a nearby alternative.",
                "success",
            ),
            BeginnerGuideStep(
                "3",
                "Review and resolve",
                "Open Report, clear warnings, then choose End Turn.",
                "warning",
            ),
        ),
        tip="LATER steps stay optional until the NEXT step is complete.",
    ),
    BeginnerGuidePage(
        key="screen",
        eyebrow="READ THE SCREEN",
        title="Four areas, one decision",
        summary=(
            "The dashboard is ordered from context at the top to the decision dock at the bottom. "
            "Read downward instead of scanning every block."
        ),
        steps=(
            BeginnerGuideStep(
                "A", "Run status", "Turn, act, goal, deadline, cash, runway, and AP.", "info"
            ),
            BeginnerGuideStep(
                "B",
                "Current Focus",
                "Your objective, coach move, and end-turn safety check.",
                "success",
            ),
            BeginnerGuideStep(
                "C",
                "Decision dock",
                "Recommended, alternatives, Report, Save, and End Turn.",
                "selection",
            ),
        ),
        tip="Blue means information, green advances play, amber needs review, red is risky.",
    ),
    BeginnerGuidePage(
        key="recovery",
        eyebrow="NEVER GET STUCK",
        title="Pause, go back, or save anytime",
        summary=(
            "Navigation is reversible. Closing a panel does not spend an action, and the pause "
            "menu keeps save, settings, menu, and quit controls together."
        ),
        steps=(
            BeginnerGuideStep(
                "ESC", "Back one layer", "Close help, picker, inspector, or panel first.", "info"
            ),
            BeginnerGuideStep(
                "P", "Pause the run", "Resume, save, change settings, or return to menu.", "warning"
            ),
            BeginnerGuideStep(
                "S", "Save progress", "Save from the decision dock or the pause menu.", "success"
            ),
        ),
        tip="If Esc has nothing to close, it opens Pause instead of quitting.",
    ),
    BeginnerGuidePage(
        key="controls",
        eyebrow="ESSENTIAL CONTROLS",
        title="Start with only six controls",
        summary=(
            "Mouse controls are enough for normal play. Keyboard shortcuts are optional and exist "
            "to make repeated actions faster."
        ),
        steps=(
            BeginnerGuideStep(
                "CLICK",
                "Choose and inspect",
                "Select buttons, cards, products, and panels.",
                "selection",
            ),
            BeginnerGuideStep(
                "C", "Run Coach move", "Execute the current Recommended action.", "success"
            ),
            BeginnerGuideStep(
                "F1", "Open this guide", "Return here whenever the next step is unclear.", "info"
            ),
        ),
        tip="Advanced panel shortcuts remain available, but they are never required.",
    ),
    BeginnerGuidePage(
        key="advanced",
        eyebrow="OPTIONAL REFERENCE",
        title="Power keys for experienced players",
        summary=(
            "These grouped shortcuts speed up repeated play. Ignore this page until the mouse "
            "flow and core loop already feel comfortable."
        ),
        steps=(
            BeginnerGuideStep(
                "0 / V",
                "Change action view",
                "Reveal more actions or full Endgame controls.",
                "info",
            ),
            BeginnerGuideStep(
                "1-8 / I",
                "Open workspaces",
                "Jump to panels and inspect their records.",
                "selection",
            ),
            BeginnerGuideStep(
                "GROUPS",
                "Run action families",
                "Use the grouped keys below as a reference.",
                "success",
            ),
        ),
        tip="Mouse controls remain fully supported; none of these keys are mandatory.",
    ),
)


ESSENTIAL_RUN_CONTROLS: tuple[tuple[str, str], ...] = (
    ("Mouse", "Choose actions and inspect cards"),
    ("C", "Run the Recommended coach move"),
    ("Space", "Review and end the current turn"),
    ("Esc", "Close one layer or open Pause"),
    ("P", "Open or close Pause"),
    ("F1", "Open or close this guide"),
)


ADVANCED_RUN_CONTROLS: tuple[tuple[str, str], ...] = (
    ("0 / V", "More actions / full Endgame actions"),
    ("1-8 / I", "Open a workspace / inspect it"),
    ("Q F M D", "Product quality, features, market, debt"),
    ("H A O", "Hire, assign, and partner"),
    ("Y R B U", "Strategy, roadmap, budget, support"),
    ("Z X Pg", "Inspector sort, filter, and pages"),
)


def clamp_guide_page_index(index: int) -> int:
    """Clamp arbitrary input to a valid guide page index."""

    return max(0, min(int(index), len(BEGINNER_GUIDE_PAGES) - 1))


def resolve_guide_page(index: int) -> BeginnerGuidePage:
    """Return the guide page for a safe, clamped index."""

    return BEGINNER_GUIDE_PAGES[clamp_guide_page_index(index)]
