"""The bundled-docs registry (`squads._docfiles`, backing `sq docs`): its available-doc list
matches the repo's `docs/*.md` exactly, each title comes from the doc's first `# ` heading,
lookup is case-insensitive and tolerates a `.md` suffix, an unknown doc raises a clean
`SquadsError`, `pyproject.toml` force-includes `docs/` into the wheel, and the workflow doc
(which embeds the override section) renders without error.
"""

import tomllib
from pathlib import Path

import pytest

from squads import _docfiles
from squads._errors import SquadsError


def _repo_root() -> Path:
    return Path(_docfiles.__file__).resolve().parents[2]


def test_available_docs_match_the_repo_docs_directory_with_titles_from_the_first_heading() -> None:
    available = dict(_docfiles.available())
    expected_stems = {p.stem for p in (_repo_root() / "docs").glob("*.md")}
    assert set(available) == expected_stems
    assert {"internals", "workflow", "migration"} <= set(available)
    assert available["internals"] == "squads internals"


def test_read_is_case_insensitive_and_tolerates_an_md_suffix() -> None:
    assert _docfiles.read("INTERNALS").startswith("# squads internals")
    assert _docfiles.read("internals.md") == _docfiles.read("internals")


def test_read_an_unknown_doc_raises_a_clean_squads_error() -> None:
    with pytest.raises(SquadsError, match="unknown doc"):
        _docfiles.read("does-not-exist")


def test_pyproject_force_includes_docs_into_the_wheel() -> None:
    data = tomllib.loads((_repo_root() / "pyproject.toml").read_text(encoding="utf-8"))
    force_include = data["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    assert force_include["docs"] == "squads/_docs"


def test_the_workflow_doc_renders_without_error_and_includes_the_overrides_section() -> None:
    content = _docfiles.read("workflow")
    assert "squads workflow" in content
    assert "Project workflow overrides" in content
    assert ".overrides/workflow.toml" in content
