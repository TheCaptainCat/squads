"""``sq repair``'s advertised job is the index, and the sweep also rewrites content — so the
verb says so.

The ruling accepted this as announced, not prevented: an operator who ran repair to reconcile
an index gets a content diff they did not ask for, and the answer is that the diff is stated
rather than discovered. A flag would only be the one-shot maintenance verb again under another
name, and the population that needs the cleanup is exactly the population that does not know
it needs it.
"""

import pytest

from _helpers import create_item, strip_ansi
from squads._index._resolver import item_file
from squads._models import _markers as markers

pytestmark = pytest.mark.anyio


async def test_repair_reports_the_files_it_stripped(svc, invoke):
    task = (await create_item(svc, "task", "Carries a retired region")).item
    await svc.add_subtask(task.id, "First")
    path = item_file(svc.paths, task)
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            markers.open_marker(markers.SUBTASKS),
            f"{markers.open_marker(markers.SUMMARY)}\n| Subtask |\n"
            f"{markers.close_marker(markers.SUMMARY)}\n\n"
            f"{markers.open_marker(markers.SUBTASKS)}",
            1,
        ),
        encoding="utf-8",
    )

    result = await invoke(["repair"])

    assert result.exit_code == 0
    assert "stripped retired regions from 1 item file" in strip_ansi(result.output)


async def test_repair_says_nothing_about_a_corpus_that_carries_none(svc, invoke):
    await create_item(svc, "task", "Nothing retired here")

    result = await invoke(["repair"])

    assert result.exit_code == 0
    assert "stripped" not in strip_ansi(result.output)
