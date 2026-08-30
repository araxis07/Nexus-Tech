"""Release boundaries for converging the current game toward beta."""

from __future__ import annotations

from dataclasses import dataclass

from nexus_tech.content.loader import (
    list_competitor_archetypes,
    list_product_templates,
    list_scenarios,
)
from nexus_tech.domain.models import TurnAction
from nexus_tech.simulation.action_catalog import get_action_presentation
from nexus_tech.simulation.empire import EMPIRE_SCENARIO_ID
from nexus_tech.simulation.event_registry import get_event_registry


@dataclass(frozen=True)
class CatalogSnapshot:
    """Measured size of the player-facing and systemic content catalogs."""

    scenarios: int
    product_templates: int
    competitor_archetypes: int
    turn_actions: int
    player_programs: int
    systemic_events: int


@dataclass(frozen=True)
class ManualBetaTarget:
    """A beta criterion that must be observed by a real tester."""

    key: str
    target: str
    minimum_sessions: int
    manual_evidence_required: bool = True


BETA_CATALOG_CEILING = CatalogSnapshot(
    scenarios=49,
    product_templates=49,
    competitor_archetypes=32,
    turn_actions=194,
    player_programs=99,
    systemic_events=202,
)

MANUAL_BETA_TARGETS = (
    ManualBetaTarget(
        key="first_turn_comprehension",
        target="At least 80% of first-time players complete turn one without operator help.",
        minimum_sessions=6,
    ),
    ManualBetaTarget(
        key="navigation_recovery",
        target="Every tester can pause, back out, and return to the title menu unaided.",
        minimum_sessions=6,
    ),
    ManualBetaTarget(
        key="campaign_choice_clarity",
        target="At least 80% can explain the trade-off in both campaign decisions.",
        minimum_sessions=6,
    ),
    ManualBetaTarget(
        key="layout_readability",
        target="No blocker-level clipping, overlap, or unreadable control is observed.",
        minimum_sessions=6,
    ),
    ManualBetaTarget(
        key="session_pacing",
        target="A representative run reaches Act 3 without decision fatigue blocking progress.",
        minimum_sessions=6,
    ),
)


def capture_catalog_snapshot() -> CatalogSnapshot:
    """Capture the current catalog sizes used by the beta feature-freeze gate."""

    beta_scenarios = tuple(
        scenario for scenario in list_scenarios() if scenario.scenario_id != EMPIRE_SCENARIO_ID
    )
    return CatalogSnapshot(
        scenarios=len(beta_scenarios),
        product_templates=len(list_product_templates()),
        competitor_archetypes=len(list_competitor_archetypes()),
        turn_actions=len(TurnAction),
        player_programs=len({get_action_presentation(action).program_key for action in TurnAction}),
        systemic_events=len(get_event_registry()),
    )


def catalog_ceiling_violations(
    snapshot: CatalogSnapshot | None = None,
) -> tuple[str, ...]:
    """Return catalog lanes that grew beyond the agreed beta ceiling."""

    current = snapshot or capture_catalog_snapshot()
    return tuple(
        field_name
        for field_name in CatalogSnapshot.__dataclass_fields__
        if getattr(current, field_name) > getattr(BETA_CATALOG_CEILING, field_name)
    )
