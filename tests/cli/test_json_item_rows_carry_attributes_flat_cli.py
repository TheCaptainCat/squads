"""A ``--json`` item row is the item's fields, then each stored attribute flat at the top level,
then the keys the command adds. One table crosses the four commands that emit generic rows with
the attribute shapes a row can meet: a declared one, one nobody declared, a nested mapping, and
a name that a row's own added key already owns, which stays in the file and out of the row."""

import json
from typing import Any

import pytest

from _helpers import create_item
from squads._sections import replace_frontmatter, split_frontmatter

pytestmark = pytest.mark.anyio

#: (id, key, value): the attribute shapes a row meets.
SHAPES = [
    ("declared", "tech", "go"),
    ("undeclared", "hand_key", "keep-me"),
    ("nested-mapping", "nested", {"a": {"b": 1}}),
]
#: Attributes named like a key the command adds: the row keeps the command's own value.
ADDED_KEY_SHAPES = [("badges", {"x": 1}), ("body", "stored"), ("matched_subentities", ["x"])]


async def _plant(svc, item, key: str, value: Any) -> None:
    path = svc.paths.abspath(item.path)
    text = path.read_text(encoding="utf-8")
    data, _ = split_frontmatter(text)
    data[key] = value
    path.write_text(replace_frontmatter(text, data), encoding="utf-8")
    await svc.repair()


async def _rows(invoke, svc, host) -> dict[str, dict[str, Any]]:
    """The host item's row as each command emits it."""
    seq = str(host.sequence_id)
    out: dict[str, dict[str, Any]] = {}
    listed = await invoke(["list", "--json", "--type", "guide"])
    out["list"] = next(r for r in json.loads(listed.output) if r["id"] == host.id)
    shown = await invoke(["show", host.id, "--json"])
    out["show"] = json.loads(shown.output)
    typed = await invoke(["guide", seq, "show", "--json"])
    out["typed show"] = json.loads(typed.output)
    return out


@pytest.mark.parametrize(("key", "value"), [s[1:] for s in SHAPES], ids=[s[0] for s in SHAPES])
async def test_every_row_carries_a_stored_attribute_flat(project, svc, invoke, key, value) -> None:
    host = (await create_item(svc, "guide", "A guide")).item
    await _plant(svc, host, key, value)

    for command, row in (await _rows(invoke, svc, host)).items():
        assert row[key] == value, command
        assert "attributes" not in row and "extra" not in row, command
        assert row["id"] == host.id and row["path"] == host.path, command


@pytest.mark.parametrize(("key", "value"), ADDED_KEY_SHAPES, ids=[s[0] for s in ADDED_KEY_SHAPES])
async def test_an_attribute_named_like_an_added_key_stays_in_the_file_and_out_of_the_row(
    project, svc, invoke, key, value
) -> None:
    host = (await create_item(svc, "guide", "A guide")).item
    await _plant(svc, host, key, value)

    stored, _ = split_frontmatter(project.squad_dir.joinpath(host.path).read_text("utf-8"))
    assert stored[key] == value
    for command, row in (await _rows(invoke, svc, host)).items():
        assert row.get(key) != value, command


async def test_the_create_and_mine_rows_carry_attributes_flat_too(project, svc, invoke) -> None:
    created = await invoke(
        [
            "create",
            "guide",
            "A guide",
            "--author",
            "manager",
            "--tech",
            "go",
            "--tag",
            "a",
            "--json",
        ]
    )
    row = json.loads(created.output)
    assert row["tech"] == "go" and row["tags"] == ["a"]
    assert "extra" not in row

    task = (await create_item(svc, "task", "Assigned", assignee="manager")).item
    await _plant(svc, task, "hand_key", "keep-me")
    mine = await invoke(["mine", "manager", "--json"])
    mine_row = next(r for r in json.loads(mine.output) if r["id"] == task.id)
    assert mine_row["hand_key"] == "keep-me"
    assert mine_row["matched_subentities"] == []
