"""Pure player-facing labels for internal 2D feedback targets."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

__all__ = ["build_feedback_target_text"]


def build_feedback_target_text(
    targets: Iterable[str],
    *,
    product_names: Mapping[str, str],
) -> str:
    """Describe internal motion targets without exposing product identifiers."""

    normalized_products = {
        _normalize_identifier(identifier): _clean_label(name, fallback="Selected Product")
        for identifier, name in product_names.items()
    }
    labels: list[str] = []
    for target in targets:
        parts = tuple(part.strip() for part in target.split(":") if part.strip())
        if not parts:
            continue
        if parts[0] == "product":
            product_id = _normalize_identifier(parts[1]) if len(parts) > 1 else ""
            _append_unique(labels, normalized_products.get(product_id, "Selected Product"))
            if len(parts) > 2:
                _append_unique(labels, _clean_label(parts[-1], fallback="Update"))
            continue
        _append_unique(labels, _clean_label(parts[-1], fallback="Update"))
    return " / ".join(labels) or "Run Update"


def _normalize_identifier(value: str) -> str:
    return value.replace("-", "").strip().lower()


def _clean_label(value: str, *, fallback: str) -> str:
    normalized = " ".join(value.replace("_", " ").replace("-", " ").split())
    return normalized.title() if normalized else fallback


def _append_unique(labels: list[str], value: str) -> None:
    if value not in labels:
        labels.append(value)
