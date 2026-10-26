"""One table: every malformed ``[items.*]`` / ``[subentity_kinds.*]`` entry of a workflow
override is listed by one lint run as written sentences, with a shape-specific hint."""

from pathlib import Path

import pytest

from squads._errors import SquadsError
from squads._workflow._loader import lint_workflow_spec, load_workflow_spec

#: override body -> the fragments, one per expected finding, in order.
_ROWS = {
    "two unknown item keys": (
        "[items.task]\nbogus = 1\n[items.bug]\nalsobogus = 2\n",
        ["'task': unknown key 'bogus'", "'bug': unknown key 'alsobogus'"],
    ),
    "three entries across items and subentity kinds": (
        "[items.task]\nbogus = 1\n[items.bug]\nalsobogus = 2\n[subentity_kinds.subtask]\nzzz = 3\n",
        [
            "'task': unknown key 'bogus'",
            "'bug': unknown key 'alsobogus'",
            "'subtask': unknown key 'zzz'",
        ],
    ),
    "two bad fields of one entry": (
        "[items.task]\nbogus = 1\nprefix = 4\n",
        ["'task': key 'prefix' is invalid", "'task': unknown key 'bogus'"],
    ),
    "a wrong type and an unknown key in different entries": (
        "[items.task]\nprefix = 4\n[subentity_kinds.subtask]\nzzz = 3\n",
        ["'task': key 'prefix' is invalid", "'subtask': unknown key 'zzz'"],
    ),
}


def _lint(squad_dir: Path, body: str) -> list[tuple[str, str, str, str]]:
    override = squad_dir / ".overrides" / "workflow.toml"
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text(body, encoding="utf-8")
    return [f for f in lint_workflow_spec(squad_dir) if "override-base stamp" not in f[2]]


@pytest.mark.parametrize("row", list(_ROWS))
def test_one_lint_run_lists_every_malformed_entry(tmp_path: Path, row: str) -> None:
    body, fragments = _ROWS[row]
    findings = _lint(tmp_path, body)
    assert len(findings) == len(fragments), findings
    for (_severity, _where, message, hint), fragment in zip(findings, fragments, strict=True):
        assert fragment in message
        assert "validation error" not in message
        assert "errors.pydantic.dev" not in message
        assert "Fix the referenced key" not in hint
        assert "or add it back" not in hint


@pytest.mark.parametrize("row", list(_ROWS))
def test_loading_still_refuses_on_the_first_malformed_entry(tmp_path: Path, row: str) -> None:
    body, fragments = _ROWS[row]
    override = tmp_path / ".overrides" / "workflow.toml"
    override.parent.mkdir(parents=True)
    override.write_text(body, encoding="utf-8")
    with pytest.raises(SquadsError) as excinfo:
        load_workflow_spec(tmp_path)
    assert fragments[0].split(":")[0] in str(excinfo.value)
