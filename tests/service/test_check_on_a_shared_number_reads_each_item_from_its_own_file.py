"""When two ids share one number, `check` reports the shared number once and runs each item's own
file checks against that item's own file, never the other id's."""

from pathlib import Path

import pytest

from _helpers import make_service
from squads._sections import replace_frontmatter, split_frontmatter
from squads._services import _service as service

pytestmark = pytest.mark.anyio

# (type holding the number in the index, type of the unindexed file that claims it)
_SHAPES = [
    pytest.param("task", "bug", id="task-and-bug"),
    pytest.param("bug", "task", id="bug-and-task"),
    pytest.param("task", "feature", id="task-and-feature"),
]


@pytest.fixture
async def svc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal")
    return make_service(result.paths)


@pytest.mark.parametrize(("indexed", "claimant"), _SHAPES)
async def test_a_shared_number_adds_no_file_error_for_the_indexed_item(svc, indexed, claimant):
    held = await svc.create(indexed, "Held", author="manager")
    other = await svc.create(claimant, "Other", author="manager")
    # The merged-tree state: the claimant's file now carries the held item's number, and the
    # index has never heard of it.
    text = other.path.read_text()
    data = split_frontmatter(text)[0]
    data["id"] = f"{other.item.id.rsplit('-', 1)[0]}-{held.item.sequence_id:06d}"
    data["sequence_id"] = held.item.sequence_id
    other.path.write_text(replace_frontmatter(text, data))

    issues = await svc.check()

    held_errors = [i for i in issues if i.item == held.item.id]
    assert held_errors == []
    assert [i for i in issues if "under different ids" in i.message]
