"""Tree row colour follows the status's role intent (positive/danger/neutral/...), and a
hidden-by-default role dims the whole row — mirroring the default-visibility model rather than
re-deriving a hidden set in the TUI.

Also: this browser roots at the bare forest, so it receives the roots the tree invents to reveal
a parent cycle, and it has to disclose them the way the terminal rendering does — legibly on a
row that may be dimmed for either of the two independent reasons above.
"""

import pytest

from _helpers import create_item

pytest.importorskip("textual")

from rich.text import Text

from squads._services._results import TREE_ANCHOR_MARKER
from squads._tui._tree import _label, _status_style

pytestmark = pytest.mark.anyio


async def test_status_style_follows_the_roles_colour_intent(svc):
    assert _status_style("InProgress", svc.spec) == "green"  # role "active" -> positive
    assert _status_style("Blocked", svc.spec) == "red"  # role "blocked" -> danger
    assert _status_style("Draft", svc.spec) == ""  # role "pending" -> neutral, no override


def _full_span_styles(label: Text) -> set[str]:
    length = len(label.plain)
    return {str(span.style) for span in label.spans if span.start == 0 and span.end == length}


async def test_a_visible_status_label_is_not_dimmed(svc):
    task = (await create_item(svc, "task", "In flight")).item
    await svc.update(task.id, status="InProgress", force=True)
    task = await svc.get(task.id)

    label = _label(task, path_only=False, anchor=False, spec=svc.spec)
    assert "dim" not in _full_span_styles(label)


async def test_a_hidden_by_default_status_dims_the_whole_row(svc):
    task = (await create_item(svc, "task", "Shipped")).item
    for status in ("InProgress", "InReview", "Done"):
        await svc.update(task.id, status=status, force=True)
    task = await svc.get(task.id)
    assert svc.spec.hidden_by_default(task.type, task.status)  # "done" role is hidden

    label = _label(task, path_only=False, anchor=False, spec=svc.spec)
    assert "dim" in _full_span_styles(label)


async def test_path_only_ancestors_stay_dimmed_regardless_of_role(svc):
    task = (await create_item(svc, "task", "Ancestor")).item
    label = _label(task, path_only=True, anchor=False, spec=svc.spec)
    assert "dim" in _full_span_styles(label)


async def test_an_invented_root_is_marked_and_its_marker_is_not_dimmed(svc):
    """The dim and the disclosure are independent: an anchor can also be a path-only or
    hidden-by-default row, and a dimmed marker is the failure mode worth pinning."""
    task = (await create_item(svc, "task", "On a cycle")).item
    for path_only in (False, True):
        label = _label(task, path_only=path_only, anchor=True, spec=svc.spec)
        assert TREE_ANCHOR_MARKER in label.plain
        marker_at = label.plain.index(TREE_ANCHOR_MARKER)
        dimmed = [s for s in label.spans if "dim" in str(s.style)]
        assert all(span.end <= marker_at for span in dimmed), label.spans

    assert (
        TREE_ANCHOR_MARKER not in _label(task, path_only=False, anchor=False, spec=svc.spec).plain
    )
