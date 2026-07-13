"""Authored three-act journeys for the featured campaign tracks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CampaignActId(StrEnum):
    """Stable identifiers for the three campaign chapters."""

    FOUNDATION = "foundation"
    COMMITMENT = "commitment"
    CONSEQUENCE = "consequence"


@dataclass(frozen=True)
class CampaignChapterDefinition:
    """One authored chapter that supplies a decision lens for a turn range."""

    act_id: CampaignActId
    title: str
    turn_window: str
    objective: str
    decision_lens: str
    primary_risk: str


@dataclass(frozen=True)
class CampaignJourneyDefinition:
    """The three-act identity of one featured scenario."""

    scenario_id: str
    featured_rank: int
    track_label: str
    theme: str
    chapters: tuple[CampaignChapterDefinition, ...]


@dataclass(frozen=True)
class CampaignJourneyProgress:
    """Current chapter derived from scenario and turn without save migration."""

    journey: CampaignJourneyDefinition
    chapter: CampaignChapterDefinition
    chapter_index: int

    @property
    def act_label(self) -> str:
        return f"Act {self.chapter_index + 1}/3: {self.chapter.title}"


def _chapter(
    act_id: CampaignActId,
    title: str,
    turn_window: str,
    objective: str,
    decision_lens: str,
    primary_risk: str,
) -> CampaignChapterDefinition:
    return CampaignChapterDefinition(
        act_id=act_id,
        title=title,
        turn_window=turn_window,
        objective=objective,
        decision_lens=decision_lens,
        primary_risk=primary_risk,
    )


_FEATURED_JOURNEYS = (
    CampaignJourneyDefinition(
        "founder_journey",
        1,
        "Learn",
        "Turn one product into a durable operating company.",
        (
            _chapter(
                CampaignActId.FOUNDATION,
                "Foundation Loop",
                "T1-T4",
                "Staff and stabilize the flagship.",
                "Focus beats breadth.",
                "Idle payroll or fragile quality.",
            ),
            _chapter(
                CampaignActId.COMMITMENT,
                "Strategic Focus",
                "T5-T9",
                "Prove repeatable demand without losing control.",
                "Choose the pressure worth carrying.",
                "Growth outruns support and runway.",
            ),
            _chapter(
                CampaignActId.CONSEQUENCE,
                "Durable Company",
                "T10+",
                "Clear the path gates and defend independence.",
                "Every system must reinforce the endgame.",
                "Unresolved debt, board, or trust gates.",
            ),
        ),
    ),
    CampaignJourneyDefinition(
        "bootstrap_studio",
        2,
        "Profit",
        "Compound a small studio without surrendering cash discipline.",
        (
            _chapter(
                CampaignActId.FOUNDATION,
                "Protect Runway",
                "T1-T4",
                "Reach a stable delivery cadence on current cash.",
                "Spend only where payback is visible.",
                "Early hiring or marketing burn.",
            ),
            _chapter(
                CampaignActId.COMMITMENT,
                "Repeatable Margin",
                "T5-T9",
                "Turn customer value into reliable margin.",
                "Prefer retention and pricing leverage.",
                "Revenue grows while margin erodes.",
            ),
            _chapter(
                CampaignActId.CONSEQUENCE,
                "Independent Compounder",
                "T10+",
                "Lock reserves and finish with strategic control.",
                "Optionality is the win condition.",
                "A late liquidity or dependency shock.",
            ),
        ),
    ),
    CampaignJourneyDefinition(
        "technical_rebuild",
        3,
        "Quality",
        "Recover a damaged platform and earn customer trust again.",
        (
            _chapter(
                CampaignActId.FOUNDATION,
                "Stop Incidents",
                "T1-T4",
                "Reduce bugs and contain support escalation.",
                "Stability before feature velocity.",
                "Churn compounds faster than repairs.",
            ),
            _chapter(
                CampaignActId.COMMITMENT,
                "Rebuild Platform",
                "T5-T9",
                "Pay down debt while restoring delivery throughput.",
                "Fix causes, not symptoms.",
                "Recovery work stalls commercial momentum.",
            ),
            _chapter(
                CampaignActId.CONSEQUENCE,
                "Restore Trust",
                "T10+",
                "Convert reliability into references and renewal strength.",
                "Proof matters more than promises.",
                "Technical health fails to rebuild demand.",
            ),
        ),
    ),
    CampaignJourneyDefinition(
        "portfolio_machine",
        4,
        "Portfolio",
        "Scale multiple products without losing strategic coherence.",
        (
            _chapter(
                CampaignActId.FOUNDATION,
                "Prove Flagship",
                "T1-T4",
                "Make the first product strong enough to fund expansion.",
                "One engine must work before two compete.",
                "Premature portfolio sprawl.",
            ),
            _chapter(
                CampaignActId.COMMITMENT,
                "Launch Second Engine",
                "T5-T9",
                "Create a complementary second growth loop.",
                "Share capabilities, not confusion.",
                "Split staffing and weak positioning.",
            ),
            _chapter(
                CampaignActId.CONSEQUENCE,
                "Control Sprawl",
                "T10+",
                "Balance capital, teams, and gates across the portfolio.",
                "The portfolio must be stronger than its parts.",
                "Hidden drag from the weakest product.",
            ),
        ),
    ),
    CampaignJourneyDefinition(
        "debt_crunch",
        5,
        "Debt",
        "Survive the capital stack and regain room to choose.",
        (
            _chapter(
                CampaignActId.FOUNDATION,
                "Stop the Bleeding",
                "T1-T4",
                "Protect cash and halt avoidable operating losses.",
                "Liquidity outranks vanity growth.",
                "A reserve break before recovery starts.",
            ),
            _chapter(
                CampaignActId.COMMITMENT,
                "Refinance the Model",
                "T5-T9",
                "Repair margin and reshape debt obligations.",
                "Sequence operations before capital moves.",
                "Covenants tighten around weak economics.",
            ),
            _chapter(
                CampaignActId.CONSEQUENCE,
                "Earn Freedom",
                "T10+",
                "Clear solvency gates and restore strategic choice.",
                "Capital resilience must survive a shock.",
                "One missed gate triggers terminal pressure.",
            ),
        ),
    ),
    CampaignJourneyDefinition(
        "public_market_countdown",
        6,
        "Endgame",
        "Build credible readiness before the market window closes.",
        (
            _chapter(
                CampaignActId.FOUNDATION,
                "Repair Readiness",
                "T1-T4",
                "Close the largest operating and governance gaps.",
                "Credibility starts with clean fundamentals.",
                "Visible weaknesses harden into blockers.",
            ),
            _chapter(
                CampaignActId.COMMITMENT,
                "Choose the Listing Story",
                "T5-T9",
                "Align growth, control, and board expectations.",
                "Commit to one defensible strategic path.",
                "Mixed signals dilute every exit option.",
            ),
            _chapter(
                CampaignActId.CONSEQUENCE,
                "Defend the Outcome",
                "T10+",
                "Clear final gates and withstand late scrutiny.",
                "Readiness must be resilient, not cosmetic.",
                "A final trust or capital gate closes the window.",
            ),
        ),
    ),
)

_JOURNEYS_BY_SCENARIO = {journey.scenario_id: journey for journey in _FEATURED_JOURNEYS}


def list_featured_campaign_journeys() -> tuple[CampaignJourneyDefinition, ...]:
    """Return the authored campaign journeys in recommended progression order."""

    return _FEATURED_JOURNEYS


def get_campaign_journey(scenario_id: str) -> CampaignJourneyDefinition | None:
    """Return a featured journey when the scenario has one."""

    return _JOURNEYS_BY_SCENARIO.get(scenario_id)


def get_campaign_journey_progress(
    scenario_id: str,
    current_turn: int,
) -> CampaignJourneyProgress | None:
    """Resolve the current act from turn boundaries shared by all featured tracks."""

    journey = get_campaign_journey(scenario_id)
    if journey is None:
        return None
    chapter_index = 0 if current_turn <= 4 else 1 if current_turn <= 9 else 2
    return CampaignJourneyProgress(
        journey=journey,
        chapter=journey.chapters[chapter_index],
        chapter_index=chapter_index,
    )
