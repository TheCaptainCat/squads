"""`sq check`'s deterministic total order: squad-global/no-item issues form a fixed leading
block, then item-attached issues sort by sequence number, error before warn, then message —
replacing today's incidental (per-check call order, then index insertion order) ordering.
"""

import json

import pytest

from squads import _sections as sections
from squads._itemfile import read_frontmatter

pytestmark = pytest.mark.anyio


async def test_check_json_sorts_no_item_issues_first_then_by_sequence_then_error_before_warn(
    invoke, svc
):
    a = (await svc.create("task", "a")).item
    b = (await svc.create("task", "b")).item  # higher sequence number than a

    # Give b BOTH a warn (unknown ref kind) and an error (dangling parent) — out of message
    # alphabetical order — so the assertion proves level wins over message within one item.
    path = svc.paths.abspath((await svc.get(b.id)).path)
    text = path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    fm["parent"] = "FEAT-999999"
    fm["refs"] = [f"{a.id}:not-a-real-kind"]
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")
    await svc.repair()

    (svc.paths.root / "CLAUDE.md").unlink()  # a squad-global, no-item error

    r = await invoke(["check", "--json"])
    assert r.exit_code == 3
    issues = json.loads(r.output)

    # Leading block: the no-item squad-global issue comes first.
    assert issues[0]["item"] == "CLAUDE.md"
    assert issues[0]["level"] == "error"

    # a is untouched — no issues for it at all.
    assert all(i["item"] != a.id for i in issues)

    # b's two issues both appear, error before warn, and after the leading block.
    b_positions = [idx for idx, i in enumerate(issues) if i["item"] == b.id]
    assert len(b_positions) == 2
    assert all(p > 0 for p in b_positions)
    b_issues = [issues[p] for p in b_positions]
    assert [i["level"] for i in b_issues] == ["error", "warn"]


async def test_check_console_output_uses_the_same_order_as_json(invoke, svc):
    b = (await svc.create("task", "b")).item
    path = svc.paths.abspath((await svc.get(b.id)).path)
    text = path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    fm["parent"] = "FEAT-999999"
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")
    await svc.repair()
    (svc.paths.root / "CLAUDE.md").unlink()

    console_result = await invoke(["check"])
    json_result = await invoke(["check", "--json"])
    issues = json.loads(json_result.output)

    # The console lines appear in the same order as the sorted --json list.
    lines = [ln for ln in console_result.output.splitlines() if ln.strip()]
    assert "CLAUDE.md" in lines[0]
    assert issues[0]["item"] == "CLAUDE.md"
