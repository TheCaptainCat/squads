"""`settled_requires_discussion` reads the `settled` flag of the role a status resolves to and the
comments the discussion parser finds in the item's own discussion region. Driven over every state
of each bundled lifecycle, over roles and statuses an override renames or declares, and over the
discussion shapes: empty, whitespace, text with no comment header, one or several comments, a
comment on a story, subtask or finding instead of the item, and a comment added after settling.
"""

import pytest

from _helpers import create_item
from _selection_table import (
    SETTLED_REQUIRES_DISCUSSION,
    WORK_AND_RECORDS_ROWS,
    TypeRow,
    member_findings,
    override_toml,
    service_with,
)
from squads import _sections as sections
from squads._models import _markers as markers
from squads._models._item import Item
from squads._services import _service as service
from squads._workflow import bundled_spec

pytestmark = pytest.mark.anyio

#: One status of each bundled settled role, on a type whose lifecycle reaches it.
_SETTLED_STATUSES = [
    ("task", "Done"),
    ("task", "Cancelled"),
    ("decision", "Accepted"),
    ("decision", "Superseded"),
    ("review", "Approved"),
    ("guide", "Published"),
    ("bug", "Verified"),
    ("contract", "Superseded"),
]
_NOT_SETTLED = [
    ("task", "Draft"),
    ("task", "InProgress"),
    ("task", "Blocked"),
    ("bug", "Open"),
    ("decision", "Proposed"),
]
_STATE_CELLS = [
    (row.type, status)
    for row in WORK_AND_RECORDS_ROWS
    if row.id in bundled_spec().items and not row.declaration
    for status in sorted(bundled_spec().machine_for(row.type).states)
]


async def _at(svc: service.Service, item_type: str, status: str) -> Item:
    item = (await create_item(svc, item_type, "t")).item
    await svc.update(item.id, status=status, force=True)
    return item


def _reported(issues, item_id: str) -> bool:
    return any(i == item_id for _, i, _ in member_findings(issues, SETTLED_REQUIRES_DISCUSSION))


@pytest.mark.parametrize(("item_type", "status"), _SETTLED_STATUSES)
async def test_one_status_of_each_settled_role_is_reported_with_an_empty_discussion(
    project, item_type: str, status: str
) -> None:
    svc = service_with(
        project.squad_dir,
        override_toml(TypeRow(item_type, item_type), ("settled_requires_discussion",)),
    )
    item = await _at(svc, item_type, status)
    assert _reported(await svc.check(), item.id)


@pytest.mark.parametrize(("item_type", "status"), _NOT_SETTLED)
async def test_a_status_whose_role_is_not_settled_is_silent(
    project, item_type: str, status: str
) -> None:
    svc = service_with(
        project.squad_dir,
        override_toml(TypeRow(item_type, item_type), ("settled_requires_discussion",)),
    )
    item = await _at(svc, item_type, status)
    assert not _reported(await svc.check(), item.id)


@pytest.mark.parametrize(("item_type", "status"), _STATE_CELLS)
async def test_every_state_is_reported_exactly_when_its_role_declares_settled(
    project, item_type: str, status: str
) -> None:
    spec = bundled_spec()
    svc = service_with(
        project.squad_dir,
        override_toml(TypeRow(item_type, item_type), ("settled_requires_discussion",)),
    )
    item = await _at(svc, item_type, status)
    assert (
        _reported(await svc.check(), item.id)
        is spec.roles[spec.statuses[status].role or "pending"].settled
    )


async def test_a_settled_role_renamed_by_an_override_is_reported(project) -> None:
    toml = (
        '[roles.closed]\nsettled = true\ncolor = "positive"\n\n'
        '[statuses.Done]\nrole = "closed"\n\n'
        '[items.task]\nvalidators = ["settled_requires_discussion"]\n'
    )
    svc = service_with(project.squad_dir, toml)
    done = await _at(svc, "task", "Done")
    cancelled = await _at(svc, "task", "Cancelled")
    open_item = await _at(svc, "task", "InProgress")
    issues = await svc.check()
    assert [_reported(issues, i.id) for i in (done, cancelled, open_item)] == [True, True, False]


_FLOW = (
    '[roles.wrapped]\nsettled = true\ncolor = "muted"\n\n'
    '[statuses.Todo2]\nrole = "pending"\n[statuses.Wrapped]\nrole = "wrapped"\n\n'
    '[lifecycles.flow]\ninitial = "Todo2"\n\n[lifecycles.flow.transitions]\n'
    'Todo2 = ["Wrapped"]\nWrapped = []\n\n'
    '[items.incident]\nprefix = "INC"\nfolder = "incidents"\nlifecycle = "flow"\n'
    'aliases = ["inc"]\ncategory = "work"\norder = 66\n'
    'validators = ["settled_requires_discussion"]\n'
)


@pytest.mark.parametrize(("status", "reported"), [("Todo2", False), ("Wrapped", True)])
async def test_a_role_and_status_the_project_declares_are_read_by_the_flag(
    project, status: str, reported: bool
) -> None:
    svc = service_with(project.squad_dir, _FLOW)
    item = await _at(svc, "incident", status)
    assert _reported(await svc.check(), item.id) is reported


def _edit_discussion(svc: service.Service, item: Item, inner: str) -> None:
    path = svc.paths.squad_dir / item.path
    text = path.read_text(encoding="utf-8")
    path.write_text(sections.replace_section(text, markers.DISCUSSION, inner), encoding="utf-8")


async def _task_done(project) -> tuple[service.Service, Item]:
    svc = service_with(
        project.squad_dir, override_toml(TypeRow("task", "task"), ("settled_requires_discussion",))
    )
    return svc, await _at(svc, "task", "Done")


async def test_the_discussion_as_created_holds_no_comment(project) -> None:
    svc, item = await _task_done(project)
    assert _reported(await svc.check(), item.id)


@pytest.mark.parametrize("inner", ["", "   \n\n  ", "just some text, no comment header\n"])
async def test_a_region_with_whitespace_or_text_but_no_comment_header_is_reported(
    project, inner: str
) -> None:
    svc, item = await _task_done(project)
    _edit_discussion(svc, item, inner)
    assert _reported(await svc.check(), item.id)


@pytest.mark.parametrize(
    "messages",
    [
        ["One comment."],
        ["First bullet.", "Second bullet.", "Third bullet."],
        ["Closed out:\n```\nfenced = true\n\nstill = fenced\n```"],
    ],
    ids=["one", "several-bullets", "fenced-code-block"],
)
async def test_one_top_level_comment_clears_the_finding(project, messages: list[str]) -> None:
    svc, item = await _task_done(project)
    await svc.comment(item.id, messages, as_slug="manager")
    assert not _reported(await svc.check(), item.id)


async def test_several_comments_and_a_comment_written_as_an_operator_are_counted(project) -> None:
    svc, item = await _task_done(project)
    await svc.add_operator("Alice Tester")
    await svc.comment(item.id, ["By an operator."], as_slug="op-alice")
    assert not _reported(await svc.check(), item.id)
    await svc.comment(item.id, ["And another."], as_slug="manager")
    assert not _reported(await svc.check(), item.id)


async def test_a_comment_added_after_the_item_settled_clears_the_finding(project) -> None:
    svc, item = await _task_done(project)
    assert _reported(await svc.check(), item.id)
    await svc.comment(item.id, ["Late note."], as_slug="manager")
    assert not _reported(await svc.check(), item.id)


@pytest.mark.parametrize(
    ("item_type", "kind"), [("feature", "story"), ("task", "subtask"), ("review", "finding")]
)
async def test_a_comment_on_a_sub_entity_does_not_count_for_the_item(
    project, item_type: str, kind: str
) -> None:
    svc = service_with(
        project.squad_dir,
        override_toml(TypeRow(item_type, item_type), ("settled_requires_discussion",)),
    )
    item = await _at(svc, item_type, svc.spec.first_settled_status(item_type) or "")
    block = await svc.add_block(item.id, kind, "a sub-entity")
    await svc.comment(
        item.id, ["On the sub-entity."], as_slug="manager", sub=(kind, block.local_id)
    )
    assert _reported(await svc.check(), item.id)
    await svc.comment(item.id, ["On the item."], as_slug="manager")
    assert not _reported(await svc.check(), item.id)
