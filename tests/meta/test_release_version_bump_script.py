"""``scripts/bump_version.py`` automates the release version-bump: pure text-rewrite
helpers for ``pyproject.toml``/``clients/vscode/package.json``, plus a ``--dry-run`` mode
that must never write a file or invoke a subprocess. Not squads runtime behaviour — a
repo-tooling self-test, so it lives alongside the other ``scripts/`` self-tests here
rather than in the four behavioral layers.
"""

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import bump_version  # noqa: E402  # pyright: ignore[reportMissingImports]

# (`scripts/` is outside pyright's `include`, same as it's outside pytest's `testpaths` — this
# import is the deliberate scope-crossing edge, so the module isn't statically resolvable; the
# path must also be extended above before this import, hence the E402.)

_PYPROJECT_SNIPPET = """\
[project]
name = "squads"
version = "0.12.1"
description = "demo"

[project.optional-dependencies]
tui = ["textual>=0.29.0"]

[tool.ruff]
target-version = "py314"
"""

_PACKAGE_JSON_SNIPPET = """\
{
  "name": "squads-vscode",
  "version": "0.12.1",
  "engines": {
    "vscode": "^1.85.0"
  }
}
"""


def test_set_pyproject_version_replaces_only_the_project_version_field() -> None:
    rewritten = bump_version.set_pyproject_version(_PYPROJECT_SNIPPET, "0.13.0")
    assert bump_version.read_pyproject_version(rewritten) == "0.13.0"
    # Everything else — including a same-named key elsewhere in the file — is untouched.
    assert 'target-version = "py314"' in rewritten
    assert 'name = "squads"' in rewritten
    assert rewritten.count('version = "0.13.0"') == 1
    assert "0.12.1" not in rewritten


def test_set_pyproject_version_is_idempotent() -> None:
    once = bump_version.set_pyproject_version(_PYPROJECT_SNIPPET, "0.13.0")
    twice = bump_version.set_pyproject_version(once, "0.13.0")
    assert once == twice


def test_read_pyproject_version_rejects_a_file_with_no_project_section() -> None:
    with pytest.raises(ValueError, match=r"\[project\]"):
        bump_version.read_pyproject_version('[tool.ruff]\ntarget-version = "py314"\n')


def test_read_pyproject_version_rejects_a_project_section_with_no_version_field() -> None:
    with pytest.raises(ValueError, match="version"):
        bump_version.read_pyproject_version('[project]\nname = "squads"\n')


def test_set_pyproject_version_rejects_the_same_malformed_input() -> None:
    with pytest.raises(ValueError, match="version"):
        bump_version.set_pyproject_version('[project]\nname = "squads"\n', "0.13.0")


def test_set_package_json_version_replaces_only_the_version_field() -> None:
    rewritten = bump_version.set_package_json_version(_PACKAGE_JSON_SNIPPET, "0.13.0")
    assert bump_version.read_package_json_version(rewritten) == "0.13.0"
    assert '"vscode": "^1.85.0"' in rewritten
    assert rewritten.count('"version": "0.13.0"') == 1
    assert "0.12.1" not in rewritten


def test_set_package_json_version_is_idempotent() -> None:
    once = bump_version.set_package_json_version(_PACKAGE_JSON_SNIPPET, "0.13.0")
    twice = bump_version.set_package_json_version(once, "0.13.0")
    assert once == twice


def test_read_package_json_version_rejects_a_file_with_no_version_field() -> None:
    with pytest.raises(ValueError, match="version"):
        bump_version.read_package_json_version('{"name": "squads-vscode"}')


def test_set_package_json_version_rejects_the_same_malformed_input() -> None:
    with pytest.raises(ValueError, match="version"):
        bump_version.set_package_json_version('{"name": "squads-vscode"}', "0.13.0")


def test_bump_version_rejects_a_version_argument_that_is_not_x_y_z() -> None:
    with pytest.raises(SystemExit, match="does not look like a version"):
        bump_version.bump_version("not-a-version", dry_run=True)


def test_dry_run_prints_the_plan_and_makes_no_file_or_subprocess_side_effects(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _forbidden_run(*args: object, **kwargs: object) -> None:
        raise AssertionError(f"dry-run must not invoke subprocess.run, got: {args!r}")

    monkeypatch.setattr(bump_version.subprocess, "run", _forbidden_run)

    def _forbidden_write(self: Path, *args: object, **kwargs: object) -> None:
        raise AssertionError(f"dry-run must not write to {self}")

    monkeypatch.setattr(Path, "write_text", _forbidden_write)

    pyproject_path = bump_version._PYPROJECT_PATH
    package_json_path = bump_version._PACKAGE_JSON_PATH
    before_pyproject = pyproject_path.read_text(encoding="utf-8")
    before_package_json = package_json_path.read_text(encoding="utf-8")

    bump_version.bump_version("999.999.999", dry_run=True)

    assert pyproject_path.read_text(encoding="utf-8") == before_pyproject
    assert package_json_path.read_text(encoding="utf-8") == before_package_json

    out = capsys.readouterr().out
    assert "dry run" in out
    assert "999.999.999" in out
    assert "[8/8] summary" in out
