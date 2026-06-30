import tomllib
from pathlib import Path

import pytest

from squads import _docfiles
from squads._errors import SquadsError


def _repo_root() -> Path:
    return Path(_docfiles.__file__).resolve().parents[2]


def test_available_matches_repo_docs():
    stems = {stem for stem, _ in _docfiles.available()}
    expected = {p.stem for p in (_repo_root() / "docs").glob("*.md")}
    assert stems == expected
    assert {"internals", "workflow", "migration"} <= stems


def test_available_titles_from_first_heading():
    titles = dict(_docfiles.available())
    assert titles["internals"] == "squads internals"  # the doc's first '# ' heading


def test_read_is_case_insensitive_and_strips_suffix():
    assert _docfiles.read("INTERNALS").startswith("# squads internals")
    assert _docfiles.read("internals.md") == _docfiles.read("internals")


def test_read_unknown_raises():
    with pytest.raises(SquadsError, match="unknown doc"):
        _docfiles.read("does-not-exist")


def test_pyproject_force_includes_docs():
    # The wheel must carry docs under squads/_docs (the dev fallback would otherwise hide a drop).
    data = tomllib.loads((_repo_root() / "pyproject.toml").read_text(encoding="utf-8"))
    force_include = data["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    assert force_include["docs"] == "squads/_docs"


def test_workflow_doc_renders_without_error():
    # Verify the workflow doc (including override section) renders successfully.
    content = _docfiles.read("workflow")
    assert "squads workflow" in content
    assert "Project workflow overrides" in content
    assert ".overrides/workflow.toml" in content
