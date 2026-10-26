"""`add-<kind> --json` keys the item file as `path`, the key every read surface uses."""

import json

import pytest

pytestmark = pytest.mark.anyio

_ROWS = {
    "story": ("feature", "add-story", "US1"),
    "subtask": ("task", "add-subtask", "ST1"),
    "finding": ("review", "add-finding", "F1"),
}


@pytest.mark.parametrize("row", list(_ROWS))
async def test_the_write_surface_keys_the_item_file_as_path(project, invoke, row: str) -> None:
    item_type, verb, local_id = _ROWS[row]
    await invoke(["create", item_type, "Parent", "--author", "manager"])

    result = await invoke([item_type, "2", verb, "Added one", "--json"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["local_id"] == local_id
    assert data["path"].endswith(".md")
    assert "file" not in data
