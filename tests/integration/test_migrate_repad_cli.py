"""`sq migrate repad` and the index-full guard it exists to fix, driven through the real CLI
(the `Service.repad` mechanism itself is proven at tests/integration/test_repad.py — this file
proves the command's own wiring: its message text and its exit-1-on-refuses-to-lower path).
"""

import json

import pytest

from squads._services._service import Service

pytestmark = pytest.mark.anyio


async def test_migrate_repad_renames_files_and_prints_a_summary(project, invoke):
    svc = Service(project)
    await svc.create("task", "task one")

    result = await invoke(["migrate", "repad", "7"])
    assert result.exit_code == 0, result.output
    assert "repad done" in result.output
    assert "6 → 7" in result.output
    assert "sq check" in result.output

    assert (await svc.store.load()).padding == 7

    # Every ID-prefixed item file now has a 7-digit width (slug-only skill files are skipped).
    for _, md in svc._iter_item_files():  # pyright: ignore[reportPrivateUsage]
        stem = md.stem
        _, sep, digits_slug = stem.partition("-")
        digit_run = digits_slug.split("-", 1)[0] if sep else ""
        if not digit_run.isdigit():
            continue
        assert len(digit_run) == 7, f"expected a 7-digit run, got {digit_run!r} in {md.name}"


async def test_migrate_repad_refuses_to_lower_the_width(project, invoke):
    result = await invoke(["migrate", "repad", "6"])
    assert result.exit_code == 1, result.output
    assert "must be greater than" in result.output


async def test_create_exits_1_and_names_migrate_repad_when_the_index_is_full(project, invoke):
    svc = Service(project)
    raw = json.loads(svc.store.index_path.read_text(encoding="utf-8"))
    raw["counter"] = 10**6 - 1  # all width-6 IDs exhausted
    svc.store.index_path.write_text(json.dumps(raw), encoding="utf-8")

    result = await invoke(["create", "task", "overflow task", "--author", "manager"])
    assert result.exit_code == 1, result.output
    assert "sq migrate repad" in result.output
