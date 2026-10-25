"""Every reflog ``target`` after ``sq init`` is its item's formatted id, for the seeded skills of
the bundled types and of a type the workflow override declares."""

import json
import re
from pathlib import Path
from typing import Any

import pytest

from squads._cli import app
from squads._index._reflog import reflog_path
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_CUSTOM_TYPE = '[items.incident]\nprefix = "INC"\nfolder = "incidents"\nlifecycle = "guide"\n'
_OVERRIDES = {"bundled types": None, "custom type": _CUSTOM_TYPE}


_FORMATTED = re.compile(r"[A-Z]+-[1-9][0-9]*")


def _index(squad_dir: Path) -> dict[str, dict[str, str]]:
    """The index's items keyed by their formatted id."""
    items = json.loads((squad_dir / ".squads.json").read_text(encoding="utf-8"))["items"]
    return {item["id"]: item for item in items.values()}


def _creates(squad_dir: Path) -> list[dict[str, Any]]:
    lines = reflog_path(squad_dir).read_text(encoding="utf-8").splitlines()
    return [row for row in map(json.loads, lines) if row["op"] == "create"]


@pytest.mark.parametrize("declared", list(_OVERRIDES))
async def test_every_create_target_after_init_is_a_formatted_item_id(
    tmp_path, monkeypatch, frozen_time, declared: str
) -> None:
    monkeypatch.chdir(tmp_path)
    workflow = _OVERRIDES[declared]
    if workflow is not None:
        override = tmp_path / "squads" / ".overrides" / "workflow.toml"
        override.parent.mkdir(parents=True)
        override.write_text(workflow, encoding="utf-8")

    result = await service.init(root=tmp_path, roles_spec="all")

    creates = _creates(result.paths.squad_dir)
    assert any(row["target"].startswith("SKILL-") for row in creates)
    assert [row["target"] for row in creates if not _FORMATTED.fullmatch(row["target"])] == []
    indexed = _index(result.paths.squad_dir)
    for row in creates:
        assert row["target"] in indexed, row
    if workflow is not None:
        custom = [row for row in creates if row["delta"]["title"] == "sq-incident"]
        assert [indexed[row["target"]]["slug"] for row in custom] == ["sq-incident"]


def test_a_skill_added_after_init_logs_its_formatted_id(runner, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["init", "--roles", "minimal"]).exit_code == 0
    assert runner.invoke(app, ["skill", "add", "deploy-x"]).exit_code == 0

    creates = _creates(tmp_path / "squads")
    assert [row["target"] for row in creates if not _FORMATTED.fullmatch(row["target"])] == []
    added = _index(tmp_path / "squads")[creates[-1]["target"]]
    assert added["slug"] == "deploy-x"
