"""``sq tree`` covers ``sq list`` at equal filters, and says so when it had to invent a root.

Two surfaces answer "what is on this board", and before this they disagreed about whether an
item existed at all: on a corpus holding a parent cycle, ``list`` returned the component and the
bare ``tree`` rendered none of it, at exit 0, with nothing said. The coverage clause below is
scoped to the no-depth case on purpose — a depth bound legitimately makes the tree a subset of
the list, and an invariant written the other way would be red for a reason that is not a bug.

Two assertions run as a bounded subprocess rather than in process. The exit code, because a
pipeline reports its last element's status, so anything but a bare invocation would report the
reader's success no matter what ``sq`` did. And the anchor marker, because it is asserted on one
rendered line, which needs a terminal width the test sets rather than inherits.

The corpus is staged by writing frontmatter and re-indexing, because the write door refuses a
cycle — the shape an adopted corpus or a hand-edited file arrives in.
"""

import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from _helpers import strip_ansi
from squads import _sections as sections
from squads._index._resolver import item_file
from squads._itemfile import read_frontmatter
from squads._services._results import TREE_ANCHOR_MARKER

pytestmark = pytest.mark.anyio

#: Generous next to a tree render over a handful of items, and far below "never returns".
_RETURN_BUDGET_SECONDS = 90


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    """One bare ``sq`` invocation, so ``returncode`` is the command's own."""
    return subprocess.run(
        [sys.executable, "-m", "squads", *args],
        cwd=cwd,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        timeout=_RETURN_BUDGET_SECONDS,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "COLUMNS": "200"},
        check=False,
    )


def _set_parent_in_frontmatter(paths, item, parent_id: str, *, width: int) -> None:
    """Point *item* at *parent_id* at a chosen zero-pad width — the widths are mixed across the
    fixture because a stored parent may carry a different width than the item's own id."""
    path = item_file(paths, item)
    text = path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    prefix, _, number = parent_id.rpartition("-")
    fm["parent"] = f"{prefix}-{int(number):0{width}d}"
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")


async def _poisoned_squad(svc):
    """An item below the cycle carrying the lowest sequence of all, a five-item cycle, and one
    ordinary item outside the component."""
    below = (await svc.create("bug", "Hangs below the cycle", author="manager")).item
    ring = [(await svc.create("bug", f"Ring {n}", author="manager")).item for n in range(5)]
    for index, member in enumerate(ring):
        _set_parent_in_frontmatter(
            svc.paths, member, ring[(index + 1) % len(ring)].id, width=6 if index % 2 else 9
        )
    _set_parent_in_frontmatter(svc.paths, below, ring[2].id, width=9)
    unrelated = (await svc.create("epic", "Unrelated", author="manager")).item
    await svc.repair()
    return below, ring, unrelated


def _tree_ids(payload) -> list[str]:
    """Every id in the rendered forest, repeats kept — "exactly once" is an assertion here, not
    an assumption."""
    out: list[str] = []
    for node in payload:
        out.append(node["id"])
        out.extend(_tree_ids(node["children"]))
    return out


async def test_the_bare_tree_covers_the_list_at_equal_filters_and_renders_each_item_once(
    svc, invoke
):
    await _poisoned_squad(svc)
    for extra in ([], ["--all"]):
        listed = {
            row["id"] for row in json.loads((await invoke(["list", "--json", *extra])).output)
        }
        rendered = _tree_ids(json.loads((await invoke(["tree", "--json", *extra])).output))
        assert listed <= set(rendered), f"missing from the tree: {sorted(listed - set(rendered))}"
        repeated = [item_id for item_id, count in Counter(rendered).items() if count > 1]
        assert repeated == [], f"rendered more than once: {repeated}"


async def test_the_bare_tree_renders_every_item_a_targeted_tree_renders(svc, invoke):
    """Bare is the union of the targeted trees, on existence. The two forms may differ in scope
    — which subtree you asked about — never in whether an item exists."""
    await _poisoned_squad(svc)
    bare = set(_tree_ids(json.loads((await invoke(["tree", "--all", "--json"])).output)))
    for row in json.loads((await invoke(["list", "--all", "--json"])).output):
        targeted = _tree_ids(
            json.loads((await invoke(["tree", row["id"], "--all", "--json"])).output)
        )
        assert row["id"] in targeted, f"{row['id']} is missing from its own targeted tree"
        assert row["id"] in bare, f"{row['id']} renders when rooted at, but not from bare tree"


async def test_a_depth_bound_may_still_narrow_the_tree_below_the_list(svc, invoke):
    """The coverage clause is the no-depth one: a depth bound dropping items is existing,
    correct behaviour, not a coverage violation."""
    await _poisoned_squad(svc)
    unbounded = set(_tree_ids(json.loads((await invoke(["tree", "--all", "--json"])).output)))
    bounded = set(
        _tree_ids(json.loads((await invoke(["tree", "--all", "--depth", "0", "--json"])).output))
    )
    assert bounded < unbounded


async def test_the_invented_root_carries_a_field_on_the_wire(svc, invoke):
    _below, ring, _unrelated = await _poisoned_squad(svc)
    anchor_id = min(ring, key=lambda m: m.sequence_id).id
    payload = json.loads((await invoke(["tree", "--all", "--json"])).output)
    assert [node["id"] for node in payload if node["anchor"]] == [anchor_id]
    # Additive, and deliberately asymmetric: `path_only` is not on the wire and is not being
    # added as a rider to this change.
    assert "path_only" not in payload[0]


async def test_the_invented_root_is_marked_in_the_rendering(svc, project):
    _below, ring, _unrelated = await _poisoned_squad(svc)
    anchor_id = min(ring, key=lambda m: m.sequence_id).id
    rendered = strip_ansi(_run(project.root, "tree", "--all").stdout.decode("utf-8"))
    marker_line = next(line for line in rendered.splitlines() if anchor_id in line)
    assert TREE_ANCHOR_MARKER in marker_line
    assert rendered.count(TREE_ANCHOR_MARKER) == 1


async def test_every_form_still_exits_zero_on_the_cyclic_corpus(svc, project):
    """A tree that rendered everything asked for did not fail: the exit-code table is read by
    wrapper scripts and by the editor client, and this change does not touch it."""
    _below, ring, _unrelated = await _poisoned_squad(svc)
    forms: list[tuple[str, ...]] = [
        ("tree",),
        ("tree", "--all"),
        ("tree", "--all", "--json"),
        ("tree", ring[0].id),
        ("tree", "--depth", "1"),
    ]
    for form in forms:
        result = _run(project.root, *form)
        assert result.returncode == 0, (
            f"sq {' '.join(form)} -> {result.returncode}: "
            f"{result.stderr.decode('utf-8', 'replace')}"
        )
