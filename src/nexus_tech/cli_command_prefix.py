"""Runtime command prefixes for generated local CLI handoff artifacts."""

from __future__ import annotations

import shlex
import sys
from contextlib import suppress
from pathlib import Path

__all__ = ["detect_cli_command_prefix", "resolve_cli_command_prefix"]

_PORTABLE_FALLBACK = "uv run nexus-tech"


def detect_cli_command_prefix(
    executable: str | None = None,
    *,
    working_directory: Path | None = None,
) -> str:
    """Return a shell-safe launcher matching the current CLI executable."""

    raw_executable = (executable if executable is not None else sys.argv[0]).strip()
    if not raw_executable:
        return _PORTABLE_FALLBACK

    executable_path = Path(raw_executable).expanduser()
    if executable_path.name != "nexus-tech":
        return _PORTABLE_FALLBACK

    if executable_path.is_absolute():
        current_directory = working_directory or Path.cwd()
        try:
            executable_path = executable_path.relative_to(current_directory)
        except ValueError:
            with suppress(ValueError):
                executable_path = executable_path.resolve().relative_to(current_directory.resolve())

    return shlex.quote(str(executable_path))


def resolve_cli_command_prefix(value: str | None) -> str:
    """Preserve an explicit override or derive the launcher at command runtime."""

    if value is not None:
        return value
    return detect_cli_command_prefix()
