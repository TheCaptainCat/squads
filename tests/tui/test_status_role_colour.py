"""Tree row colour follows the status's role intent (positive/danger/neutral/...), and a
hidden-by-default role dims the whole row — mirroring the default-visibility model rather than
re-deriving a hidden set in the TUI.
"""

import pytest

pytest.importorskip("textual")

from rich.text import Text

from squads._tui._tree import _label, _status_style  # pyright: ignore[reportPrivateUsage]

pytestmark = pytest.mark.anyio


async def test_status_style_follows_the_roles_colour_intent(svc):
    assert _status_style("InProgress", svc.spec) == "green"  # role "active" -> positive
    assert _status_style("Blocked", svc.spec) == "red"  # role "blocked" -> danger
    assert _status_style("Draft", svc.spec) == ""  # role "pending" -> neutral, no override


def _full_span_styles(label: Text) -> set[str]:
    length = len(label.plain)
    return {str(span.style) for span in label.spans if span.start == 0 and span.end == length}


async def test_a_visible_status_label_is_not_dimmed(svc):
    task = (await svc.create("task", "In flight")).item
    await svc.update(task.id, status="InProgress", force=True)
    task = await svc.get(task.id)

    label = _label(task, path_only=False, spec=svc.spec)
    assert "dim" not in _full_span_styles(label)


async def test_a_hidden_by_default_status_dims_the_whole_row(svc):
    task = (await svc.create("task", "Shipped")).item
    for status in ("InProgress", "InReview", "Done"):
        await svc.update(task.id, status=status, force=True)
    task = await svc.get(task.id)
    assert svc.spec.hidden_by_default(task.type, task.status)  # "done" role is hidden

    label = _label(task, path_only=False, spec=svc.spec)
    assert "dim" in _full_span_styles(label)


async def test_path_only_ancestors_stay_dimmed_regardless_of_role(svc):
    task = (await svc.create("task", "Ancestor")).item
    label = _label(task, path_only=True, spec=svc.spec)
    assert "dim" in _full_span_styles(label)
