from __future__ import annotations

from pathlib import Path

from nexus_tech.cli_command_prefix import (
    detect_cli_command_prefix,
    resolve_cli_command_prefix,
)


def test_detect_cli_command_prefix_preserves_relative_console_script() -> None:
    assert detect_cli_command_prefix(".venv313/bin/nexus-tech") == ".venv313/bin/nexus-tech"


def test_detect_cli_command_prefix_shortens_project_local_absolute_path() -> None:
    project = Path("/tmp/nexus-tech-project")

    prefix = detect_cli_command_prefix(
        "/tmp/nexus-tech-project/.venv313/bin/nexus-tech",
        working_directory=project,
    )

    assert prefix == ".venv313/bin/nexus-tech"


def test_detect_cli_command_prefix_quotes_external_path() -> None:
    prefix = detect_cli_command_prefix(
        "/tmp/Nexus Tech/bin/nexus-tech",
        working_directory=Path("/tmp/another-project"),
    )

    assert prefix == "'/tmp/Nexus Tech/bin/nexus-tech'"


def test_command_prefix_falls_back_and_preserves_explicit_override() -> None:
    assert detect_cli_command_prefix("pytest") == "uv run nexus-tech"
    assert resolve_cli_command_prefix("custom nexus-tech") == "custom nexus-tech"
