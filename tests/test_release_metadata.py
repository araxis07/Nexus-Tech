from __future__ import annotations

import tomllib
from pathlib import Path

from nexus_tech import __version__

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_current_release_version_is_consistent() -> None:
    pyproject = tomllib.loads((REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project_version = pyproject["project"]["version"]

    assert __version__ == project_version

    expected_markers = {
        "README.md": f"**Stable Alpha | Version {project_version} | Maintenance mode**",
        "docs/PROJECT_STATUS.md": f"- Version: {project_version}",
        "docs/KNOWN_ISSUES.md": (f"Version {project_version} must not be described as Beta Ready."),
        "docs/RELEASE_CHECKLIST.md": (f"Treat version {project_version} as a Stable Alpha"),
    }
    for relative_path, marker in expected_markers.items():
        document = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
        assert marker in document, f"{relative_path} does not describe version {project_version}"


def test_ci_hardening_contract() -> None:
    workflow = (REPOSITORY_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "concurrency:" in workflow
    assert "group: ci-${{ github.workflow }}-${{ github.ref }}" in workflow
    assert "cancel-in-progress: true" in workflow
    assert workflow.index("run: uv run pytest -q -W error") < workflow.index(
        "name: Build package artifacts"
    )
    assert "name: Rebuild and install source distribution offline" in workflow
    assert "uv run --offline --no-project --with 'hatchling>=1.27.0'" in workflow
    assert "uv pip install --offline" in workflow
    assert "name: nexus-tech-release-readiness" in workflow
    assert "name: nexus-tech-onboarding-reports" in workflow
    assert workflow.count("uses: actions/upload-artifact@v4") == 8
