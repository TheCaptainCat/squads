"""``sq check`` reports a parent cycle it did not admit, and ``sq repair`` leaves it alone.

A cycle can still reach a corpus without passing any write gate: ``repair`` rebuilds the index
from markdown with no gate, an adopted corpus arrives that way, and frontmatter is editable in
principle. So the condition needs a detector as well as a refusal — which the floor validator
supplies for free, since one engine backs both the gate and the report surface.

``repair`` reports and stops there. Breaking a cycle means choosing which edge to drop, which is
a judgement about someone's hierarchy rather than a mechanical rewrite, so both edges survive
the rebuild untouched.
"""

import json

import pytest

from _helpers import create_item
from squads import _sections as sections
from squads._index._resolver import item_file
from squads._itemfile import read_frontmatter

pytestmark = pytest.mark.anyio


async def _cycle_on_disk(svc) -> tuple[str, str]:
    a = (await create_item(svc, "bug", "Alpha")).item
    b = (await create_item(svc, "review", "Beta")).item
    for item, parent_id in ((a, b.id), (b, a.id)):
        path = item_file(svc.paths, item)
        text = path.read_text(encoding="utf-8")
        fm = read_frontmatter(text=text)
        fm["parent"] = parent_id
        path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")
    return a.id, b.id


async def test_check_exits_three_and_names_both_endpoints(svc, invoke):
    a_id, b_id = await _cycle_on_disk(svc)
    assert (await invoke(["repair"])).exit_code == 0

    result = await invoke(["check"])
    assert result.exit_code == 3, result.output
    assert "forms a cycle" in result.output
    assert a_id in result.output and b_id in result.output
    assert "--no-parent" in result.output


async def test_check_json_carries_the_cycle_as_an_error(svc, invoke):
    a_id, b_id = await _cycle_on_disk(svc)
    await invoke(["repair"])

    result = await invoke(["check", "--json"])
    assert result.exit_code == 3, result.output
    issues = json.loads(result.output)
    cycles = [i for i in issues if "forms a cycle" in i["message"]]
    assert {i["item"] for i in cycles} == {a_id, b_id}
    assert {i["level"] for i in cycles} == {"error"}


async def test_repair_exits_zero_and_leaves_both_edges_in_place(svc, invoke):
    a_id, b_id = await _cycle_on_disk(svc)
    result = await invoke(["repair"])
    assert result.exit_code == 0, result.output
    assert (await svc.get(a_id)).parent == b_id
    assert (await svc.get(b_id)).parent == a_id
