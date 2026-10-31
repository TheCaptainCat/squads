"""Repo gate: the version the package reports is the version `pyproject.toml` declares. The
package holds it as a literal so a client reads it without the installed metadata."""

import tomllib
from pathlib import Path

import squads


def test_the_package_version_literal_equals_the_project_version() -> None:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    declared = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]
    assert squads.__version__ == declared
