"""``sq repair`` and a version-drifted ``sq sync`` write each item file at most once per command,
whichever mix of repairs the file needs, and a second run writes nothing. Repair composes the body
tag, the retired-key strip and the ref encoding into one pending rewrite; sync's body-tag
backfill writes a file that none of its later steps touch.
"""

from typing import Any

import pytest

from _helpers import create_item
from squads._index._resolver import item_file
from squads._itemfile import read_frontmatter
from squads._models import _markers as markers
from squads._sections import replace_frontmatter, replace_section

pytestmark = pytest.mark.anyio


async def _target(svc: Any, kind: str) -> Any:
    if kind == "role":
        return await svc.roster_item("role", "manager")
    if kind == "system skill":
        await svc.seed_bundled_skills()
        return await svc.roster_item("skill", "squads")
    task = (await create_item(svc, "task", "Subject")).item
    other = (await create_item(svc, "bug", "Referenced")).item
    await svc.add_ref(task.id, other.id, kind="blocks")
    return task


def _damage(svc: Any, item: Any, *, tag: bool, frontmatter: bool) -> None:
    """Put the file in a state *tag* (an empty body region) and *frontmatter* (a retired role
    key, or a stale ref encoding) say needs repair."""
    path = item_file(svc.paths, item)
    text = path.read_text(encoding="utf-8")
    if tag:
        text = replace_section(text, markers.BODY, "")
    if frontmatter:
        data = read_frontmatter(text=text, source=str(path))
        if item.type == "role":
            data.update({"full_name": "Stored Name", "skills": ["squads"], "is_dev": True})
        else:
            data["refs"] = [
                f"{ref.split(':')[0]}:{svc.spec.default_ref_kind()}" for ref in data["refs"]
            ]
        text = replace_frontmatter(text, data)
    path.write_text(text, encoding="utf-8")


#: (kind, needs the body tag, needs the frontmatter rewrite). A work item has no placement tag,
#: and only a role carries retired keys.
ROWS = [
    pytest.param("role", True, False, id="role-tag"),
    pytest.param("role", False, True, id="role-retired-keys"),
    pytest.param("role", True, True, id="role-both"),
    pytest.param("role", False, False, id="role-neither"),
    pytest.param("system skill", True, False, id="skill-tag"),
    pytest.param("system skill", False, False, id="skill-neither"),
    pytest.param("work item", False, True, id="work-item-ref-encoding"),
    pytest.param("work item", False, False, id="work-item-neither"),
]


@pytest.mark.parametrize(("kind", "tag", "frontmatter"), ROWS)
async def test_repair_writes_each_item_file_once(svc, write_ledger, kind, tag, frontmatter):
    item = await _target(svc, kind)
    _damage(svc, item, tag=tag, frontmatter=frontmatter)
    path = item_file(svc.paths, item).resolve()
    write_ledger.seen.clear()

    await svc.repair()

    assert write_ledger.seen[path] == (1 if tag or frontmatter else 0)
    assert set(write_ledger.seen.values()) <= {1}
    write_ledger.seen.clear()
    await svc.repair()
    assert write_ledger.seen[path] == 0


@pytest.mark.parametrize(("kind", "tag", "frontmatter"), ROWS)
async def test_a_sync_writes_each_item_file_once(svc, write_ledger, kind, tag, frontmatter):
    item = await _target(svc, kind)
    _damage(svc, item, tag=tag, frontmatter=frontmatter)
    path = item_file(svc.paths, item).resolve()
    write_ledger.seen.clear()

    await svc.sync()

    converges_tag = tag and kind != "work item"
    assert write_ledger.seen[path] == (1 if converges_tag else 0)
    assert set(write_ledger.seen.values()) <= {1}
    write_ledger.seen.clear()
    await svc.sync()
    assert write_ledger.seen[path] == 0


async def test_repair_and_sync_cli_smoke(svc, invoke):
    assert (await invoke(["repair"])).exit_code == 0
    assert (await invoke(["sync"])).exit_code == 0
