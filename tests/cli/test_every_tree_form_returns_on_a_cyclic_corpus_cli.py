"""Every ``sq tree`` form returns on a corpus whose parent relation holds a cycle.

The failure this pins is a *hang*: the caller gets no exit code and no message, so an assertion
made in-process would suspend the suite rather than fail it. Each form therefore runs as a
bounded subprocess — a regression comes back as ``TimeoutExpired`` or a non-zero code, which is
a red test, not a stalled worker. The same reason a bare shell pipe is avoided elsewhere in this
tree: the exit code is the thing under test.

The corpus is built by writing frontmatter and rebuilding the index from it, because the write
door no longer admits a cycle — this is the shape an adopted corpus, a hand-edited file, or a
squad poisoned before the gate existed arrives in.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from _helpers import create_item
from squads import _sections as sections
from squads._index._resolver import item_file
from squads._itemfile import read_frontmatter

pytestmark = pytest.mark.anyio

#: Generous next to a tree render over a dozen items, and far below "never returns".
_RETURN_BUDGET_SECONDS = 90


def _run_tree(cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", "squads", "tree", *args],
        cwd=cwd,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        timeout=_RETURN_BUDGET_SECONDS,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )


async def _poisoned_squad(svc) -> tuple[str, str, str]:
    """A mutual parent cycle plus an item with no path to it, written straight to frontmatter
    and then indexed by ``repair``."""
    a = (await create_item(svc, "bug", "Alpha")).item
    b = (await create_item(svc, "review", "Beta")).item
    unrelated = (await create_item(svc, "epic", "Unrelated")).item
    for item, parent_id in ((a, b.id), (b, a.id)):
        path = item_file(svc.paths, item)
        text = path.read_text(encoding="utf-8")
        fm = read_frontmatter(text=text)
        fm["parent"] = parent_id
        path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")
    await svc.repair()
    return a.id, b.id, unrelated.id


async def test_every_tree_form_returns_and_exits_zero(svc, project):
    a_id, b_id, unrelated_id = await _poisoned_squad(svc)
    forms: list[tuple[str, ...]] = [
        (),
        ("-a",),
        (a_id,),
        (b_id,),
        (unrelated_id,),
        ("--json",),
        (a_id, "--json"),
        ("--depth", "1"),
        (a_id, "--depth", "1"),
    ]
    for form in forms:
        result = _run_tree(project.root, *form)
        assert result.returncode == 0, (
            f"sq tree {' '.join(form)} -> {result.returncode}: "
            f"{result.stderr.decode('utf-8', 'replace')}"
        )


async def test_a_tree_rooted_inside_the_cycle_truncates_at_the_repeat(svc, project):
    a_id, b_id, _unrelated = await _poisoned_squad(svc)
    out = _run_tree(project.root, a_id).stdout.decode("utf-8", "replace")
    # Both members render — a poisoned corpus still shows the operator what they are looking
    # at — and neither is repeated, which is what "truncate, do not duplicate" means.
    assert out.count(a_id) == 1, out
    assert out.count(b_id) == 1, out
