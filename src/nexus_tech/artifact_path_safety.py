"""Shared local-path guards for generated artifacts and SQLite stores."""

from __future__ import annotations

from os.path import abspath
from pathlib import Path

SQLITE_ARTIFACT_SUFFIXES = ("", "-journal", "-wal", "-shm")


def normalize_local_path(value: str | Path) -> Path:
    """Resolve aliases without requiring the final path to exist."""

    return _absolute_local_path(value).resolve(strict=False)


def protected_sqlite_artifact_paths(
    *database_paths: str | Path,
) -> frozenset[Path]:
    """Return each SQLite database path and its possible sidecar paths."""

    protected_paths: set[Path] = set()
    for database_path in database_paths:
        lexical_database = _absolute_local_path(database_path)
        resolved_database = lexical_database.resolve(strict=False)
        for database_alias in {lexical_database, resolved_database}:
            for suffix in SQLITE_ARTIFACT_SUFFIXES:
                lexical_artifact = _absolute_local_path(f"{database_alias}{suffix}")
                protected_paths.add(lexical_artifact)
                protected_paths.add(lexical_artifact.resolve(strict=False))
    return frozenset(protected_paths)


def _absolute_local_path(value: str | Path) -> Path:
    return Path(abspath(Path(str(value).strip()).expanduser()))
