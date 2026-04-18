"""JSON-backed content loading for scenarios and product templates."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources

from nexus_tech.content.models import (
    CompetitorArchetypeDefinition,
    ProductTemplateDefinition,
    ScenarioDefinition,
)


def list_scenarios() -> tuple[ScenarioDefinition, ...]:
    """Return all supported game scenarios."""

    return _load_scenarios()


def list_product_templates() -> tuple[ProductTemplateDefinition, ...]:
    """Return all supported product templates."""

    return _load_product_templates()


def list_competitor_archetypes() -> tuple[CompetitorArchetypeDefinition, ...]:
    """Return all supported competitor archetypes."""

    return _load_competitor_archetypes()


def get_scenario(scenario_id: str) -> ScenarioDefinition:
    """Load one scenario by id."""

    for scenario in _load_scenarios():
        if scenario.scenario_id == scenario_id:
            return scenario
    raise ValueError(f"Unknown scenario '{scenario_id}'.")


def get_product_template(template_id: str) -> ProductTemplateDefinition:
    """Load one product template by id."""

    for template in _load_product_templates():
        if template.template_id == template_id:
            return template
    raise ValueError(f"Unknown product template '{template_id}'.")


def get_competitor_archetype(archetype_id: str) -> CompetitorArchetypeDefinition:
    """Load one competitor archetype by id."""

    for archetype in _load_competitor_archetypes():
        if archetype.archetype_id == archetype_id:
            return archetype
    raise ValueError(f"Unknown competitor archetype '{archetype_id}'.")


@lru_cache(maxsize=1)
def _load_scenarios() -> tuple[ScenarioDefinition, ...]:
    payload = _read_json_file("scenarios.json")
    return tuple(ScenarioDefinition.model_validate(item) for item in payload)


@lru_cache(maxsize=1)
def _load_product_templates() -> tuple[ProductTemplateDefinition, ...]:
    payload = _read_json_file("product_templates.json")
    return tuple(ProductTemplateDefinition.model_validate(item) for item in payload)


@lru_cache(maxsize=1)
def _load_competitor_archetypes() -> tuple[CompetitorArchetypeDefinition, ...]:
    payload = _read_json_file("competitor_archetypes.json")
    return tuple(CompetitorArchetypeDefinition.model_validate(item) for item in payload)


def _read_json_file(filename: str) -> list[dict[str, object]]:
    package_root = resources.files("nexus_tech.content")
    return json.loads(package_root.joinpath(filename).read_text(encoding="utf-8"))
