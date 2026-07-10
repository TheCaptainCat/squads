"""`sq repair`'s own printed output, driven through the real CLI: it names the missing items
and reports the held counter/padding. The underlying mechanism (the counter/padding never
regress after a file is lost) is proven at tests/integration/test_repair_integrity.py — this
file proves the command surfaces that outcome in its own text.
"""

import json

import pytest

from squads._services._service import Service

pytestmark = pytest.mark.anyio


async def test_repair_cli_reports_missing_items_and_holds_the_counter(project, invoke):
    svc = Service(project)
    await svc.create("feature", "feat")
    top = (await svc.create("task", "task")).item

    svc.paths.abspath(top.path).unlink()

    result = await invoke(["repair"])
    assert result.exit_code == 0, result.output
    assert f"counter={top.sequence_id}" in result.output
    assert top.id in result.output


async def test_repair_cli_holds_the_padding_floor_after_file_loss(project, invoke):
    svc = Service(project)
    top = (await svc.create("task", "task")).item

    raw = json.loads(svc.store.index_path.read_text(encoding="utf-8"))
    raw["padding"] = 7  # simulate a squad that already went through a repad
    svc.store.index_path.write_text(json.dumps(raw), encoding="utf-8")

    svc.paths.abspath(top.path).unlink()

    result = await invoke(["repair"])
    assert result.exit_code == 0, result.output
    assert (await svc.store.load()).padding == 7  # held at the floor, not regressed to 6
