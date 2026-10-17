"""`sq override list`, `diff` and `update` run on a squad whose schema is behind the package's,
whatever its workflow override holds, and change only the stamp; `scaffold` and every direction
of ahead stay refused, with no file changed."""

import re
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from _gate_layouts import OVERRIDES, digest, squad
from squads import __version__
from squads._cli import app

_GATE = ("Run sq migrate up to upgrade it", "Upgrade the squads package")
_STALE = "# squads:override-base:0.14.0\n"
_STAMP = re.compile(r"^# squads:override-base:\S+\n")


def _stale(root: Path) -> None:
    path = root / ".overrides" / "workflow.toml"
    if path.is_file():
        path.write_text(_STAMP.sub(_STALE, path.read_text(encoding="utf-8")), encoding="utf-8")


def _run(args: list[str], cwd: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, "argv", ["sq", *args])
    return CliRunner().invoke(app, args)


_VERBS = {
    "list": ["override", "list"],
    "list-json": ["override", "list", "--json"],
    "diff-named": ["override", "diff", "workflow"],
    "diff-all": ["override", "diff"],
    "update-named": ["override", "update", "workflow"],
    "update-all": ["override", "update"],
}


@pytest.mark.parametrize("kind", OVERRIDES)
@pytest.mark.parametrize("verb", _VERBS)
def test_the_stamp_verbs_run_behind_the_package(
    verb: str, kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = squad(tmp_path, "behind", kind)
    _stale(root)

    result = _run(_VERBS[verb], root, monkeypatch)

    assert not any(message in result.output for message in _GATE), result.output
    assert result.exception is None or isinstance(result.exception, SystemExit), result.output
    if not (verb.endswith("-named") and kind == "none"):  # no file to name: a plain refusal
        assert result.exit_code == 0, result.output
    if verb in ("list", "diff-named") and kind != "none":
        assert "workflow" in result.output
    if verb.startswith("update") and kind in ("valid", "conflicting"):
        text = (root / ".overrides" / "workflow.toml").read_text(encoding="utf-8")
        assert text.startswith(f"# squads:override-base:{__version__}\n")


@pytest.mark.parametrize("verb", _VERBS)
def test_a_squad_ahead_of_the_package_is_still_refused(
    verb: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = squad(tmp_path, "ahead", "valid")
    before = digest(root)

    result = _run(_VERBS[verb], root, monkeypatch)

    assert result.exit_code == 1
    assert "Upgrade the squads package" in result.output
    assert digest(root) == before


@pytest.mark.parametrize("direction", ["behind", "ahead"])
def test_scaffold_stays_refused_and_writes_nothing(
    direction: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = squad(tmp_path, direction, "none")
    before = digest(root)

    result = _run(["override", "scaffold", "playbook"], root, monkeypatch)

    assert result.exit_code == 1
    assert any(message in result.output for message in _GATE), result.output
    assert digest(root) == before
