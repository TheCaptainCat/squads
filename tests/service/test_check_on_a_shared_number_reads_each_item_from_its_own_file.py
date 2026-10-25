"""When two ids share one number, `check` reports the shared number once and runs each item's own
file checks against that item's own file, never the other id's."""

from pathlib import Path

import pytest

from _helpers import make_service
from squads import __version__
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


def _claim_number(other, held) -> None:
    """Rewrite *other*'s file so it carries *held*'s number under its own id."""
    text = other.path.read_text()
    data = split_frontmatter(text)[0]
    data["id"] = f"{other.item.id.rsplit('-', 1)[0]}-{held.item.sequence_id:06d}"
    data["sequence_id"] = held.item.sequence_id
    other.path.write_text(replace_frontmatter(text, data))


_SELECT_BANNER = (
    f"# squads:override-base:{__version__}\n"
    '[items.task]\nvalidators = ["no_status_banner"]\n'
    '[items.feature]\nvalidators = ["no_status_banner"]\n'
)
_RENAMED_PLURAL = (
    f'# squads:override-base:{__version__}\n[subentity_kinds.subtask]\nplural = "worksteps"\n'
)


def _reopen(squad_dir: Path, override: str) -> service.Service:
    (squad_dir / ".overrides").mkdir(parents=True, exist_ok=True)
    (squad_dir / ".overrides" / "workflow.toml").write_text(override, encoding="utf-8")
    return service.open_service()


async def test_a_banner_in_the_claimant_file_is_not_reported_on_the_indexed_item(svc):
    held = await svc.create("task", "Held", author="manager")
    other = await svc.create("feature", "Other", author="manager")
    await svc.set_body(other.item.id, "STATUS: draft")
    _claim_number(other, held)

    issues = await _reopen(svc.paths.squad_dir, _SELECT_BANNER).check()

    assert [i for i in issues if i.item == held.item.id] == []
    assert [i for i in issues if "under different ids" in i.message]


async def test_a_real_container_rename_is_still_reported_without_a_clash(svc):
    held = await svc.create("task", "Held", author="manager")
    await svc.add_subtask(held.item.id, "A subtask")

    issues = await _reopen(svc.paths.squad_dir, _RENAMED_PLURAL).check()

    assert any(i.item == held.item.id and "worksteps" in i.message for i in issues)


async def test_a_container_rename_finding_is_not_derived_from_the_claimant_file(svc):
    held = await svc.create("task", "Held", author="manager")
    other = await svc.create("bug", "Other", author="manager")
    _claim_number(other, held)

    issues = await _reopen(svc.paths.squad_dir, _RENAMED_PLURAL).check()

    assert [i for i in issues if i.item == held.item.id] == []
