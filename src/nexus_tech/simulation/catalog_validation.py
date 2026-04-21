"""Catalog and registry validation helpers for release hardening."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from nexus_tech.content.loader import (
    list_competitor_archetypes,
    list_product_templates,
    list_scenarios,
)
from nexus_tech.simulation.event_effects import EVENT_EFFECT_HANDLERS
from nexus_tech.simulation.event_registry import get_event_registry


@dataclass(frozen=True)
class CatalogValidationReport:
    """Validation summary for data-driven content and event wiring."""

    scenario_count: int
    template_count: int
    rival_count: int
    event_count: int
    issues: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.issues


def validate_content_catalogs() -> CatalogValidationReport:
    """Validate catalog references and event handler coverage."""

    scenarios = list_scenarios()
    templates = list_product_templates()
    rivals = list_competitor_archetypes()
    event_definitions = get_event_registry()

    issues: list[str] = []
    issues.extend(_find_duplicate_ids("scenario", [scenario.scenario_id for scenario in scenarios]))
    issues.extend(_find_duplicate_ids("template", [template.template_id for template in templates]))
    issues.extend(_find_duplicate_ids("rival", [rival.archetype_id for rival in rivals]))
    issues.extend(_find_duplicate_ids("event", [event.event_id for event in event_definitions]))

    template_ids = {template.template_id for template in templates}
    rival_ids = {rival.archetype_id for rival in rivals}
    for scenario in scenarios:
        product_keys = [product.key for product in scenario.products]
        issues.extend(
            f"Scenario '{scenario.scenario_id}' has duplicate product key '{key}'."
            for key in _find_duplicates(product_keys)
        )
        product_key_set = set(product_keys)
        for product in scenario.products:
            if product.template_id not in template_ids:
                issues.append(
                    f"Scenario '{scenario.scenario_id}' references missing "
                    f"template '{product.template_id}'."
                )
        for employee in scenario.employees:
            if (
                employee.assigned_product_key is not None
                and employee.assigned_product_key not in product_key_set
            ):
                issues.append(
                    f"Scenario '{scenario.scenario_id}' assigns employee "
                    f"'{employee.full_name}' to missing product key "
                    f"'{employee.assigned_product_key}'."
                )
        for competitor in scenario.competitors:
            if competitor.archetype_id is not None and competitor.archetype_id not in rival_ids:
                issues.append(
                    f"Scenario '{scenario.scenario_id}' references missing rival archetype "
                    f"'{competitor.archetype_id}'."
                )

    event_ids = {event.event_id for event in event_definitions}
    missing_handlers = sorted(event_ids - set(EVENT_EFFECT_HANDLERS))
    for event_id in missing_handlers:
        issues.append(f"Event '{event_id}' is registered but has no effect handler.")

    stale_handlers = sorted(set(EVENT_EFFECT_HANDLERS) - event_ids)
    for event_id in stale_handlers:
        issues.append(f"Event handler '{event_id}' has no registry definition.")

    return CatalogValidationReport(
        scenario_count=len(scenarios),
        template_count=len(templates),
        rival_count=len(rivals),
        event_count=len(event_definitions),
        issues=tuple(issues),
    )


def _find_duplicate_ids(label: str, values: list[str]) -> list[str]:
    return [f"Duplicate {label} id '{value}'." for value in _find_duplicates(values)]


def _find_duplicates(values: list[str]) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)
