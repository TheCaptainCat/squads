"""`blocked_has_blocker` reads the `blocked` flag of the role a status resolves to and the declared
role of each ref kind, never a status, role or kind name. Driven over the edge shapes, over the
status shapes, over the selection shapes, and over removing the edge.
"""

import pytest

from _helpers import create_item
from _selection_table import (
    BLOCKED_HAS_BLOCKER,
    TypeRow,
    member_findings,
    override_toml,
    service_with,
)
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_TASK = TypeRow("task", "task")
_SELECTED = override_toml(_TASK, ("blocked_has_blocker",))


def _reported(issues, item_id: str) -> bool:
    return any(i == item_id for _, i, _ in member_findings(issues, BLOCKED_HAS_BLOCKER))


async def _blocked_task(svc: service.Service, title: str = "waiting") -> str:
    item = (await create_item(svc, "task", title)).item
    await svc.update(item.id, status="Blocked", force=True)
    return item.id


#: (outgoing kinds on the blocked item, kinds of refs another item holds to it) -> reported.
#: An empty string is an unspelled ref, which is the default kind.
_EDGE_SHAPES: dict[str, tuple[list[str], list[str], bool]] = {
    "no-ref-at-all": ([], [], True),
    "outgoing-blocks": (["blocks"], [], False),
    "outgoing-depends-on": (["depends-on"], [], False),
    "incoming-blocks": ([], ["blocks"], False),
    "incoming-depends-on": ([], ["depends-on"], False),
    "both-directions": (["blocks"], ["depends-on"], False),
    "unspelled-only": ([""], [], True),
    "targets-only": (["targets"], [], True),
    "implements-only": (["implements"], [], True),
    "incoming-unspelled": ([], [""], True),
    "incoming-targets": ([], ["targets"], True),
    "other-kind-beside-a-dependency-kind": (["targets", "depends-on"], [], False),
}


@pytest.mark.parametrize("shape", _EDGE_SHAPES)
async def test_an_item_is_reported_exactly_when_no_dependency_kind_edge_touches_it(
    project, shape: str
) -> None:
    outgoing, incoming, expected = _EDGE_SHAPES[shape]
    svc = service_with(project.squad_dir, _SELECTED)
    waiting = await _blocked_task(svc)
    other = (await create_item(svc, "task", "other")).item
    for kind in outgoing:
        await svc.add_ref(waiting, other.id, kind=kind)
    for kind in incoming:
        await svc.add_ref(other.id, waiting, kind=kind)
    assert _reported(await svc.check(), waiting) is expected
    assert not _reported(await svc.check(), other.id)


async def test_an_incoming_edge_from_another_type_and_from_a_settled_item_counts(project) -> None:
    svc = service_with(project.squad_dir, _SELECTED)
    from_feature = await _blocked_task(svc, "from a feature")
    from_settled = await _blocked_task(svc, "from a settled item")
    feature = (await create_item(svc, "feature", "f")).item
    settled = (await create_item(svc, "task", "settled")).item
    await svc.add_ref(feature.id, from_feature, kind="blocks")
    await svc.add_ref(settled.id, from_settled, kind="blocks")
    await svc.update(settled.id, status="Done", force=True)
    issues = await svc.check()
    assert (_reported(issues, from_feature), _reported(issues, from_settled)) == (False, False)


async def test_an_outgoing_dependency_edge_to_a_missing_item_counts_and_is_reported_elsewhere(
    project,
) -> None:
    svc = service_with(project.squad_dir, _SELECTED)
    waiting = await _blocked_task(svc)
    sequence = int(waiting.rsplit("-", 1)[1])
    async with svc.store.transaction() as db:
        db.items[sequence].refs.append("TASK-000999:depends-on")
    issues = await svc.check()
    assert not _reported(issues, waiting)
    assert any(i.item == waiting and "dangling ref" in i.message for i in issues)


async def test_an_incoming_edge_written_at_another_id_width_counts(project) -> None:
    svc = service_with(project.squad_dir, _SELECTED)
    waiting = await _blocked_task(svc)
    other = (await create_item(svc, "task", "other")).item
    sequence = int(waiting.rsplit("-", 1)[1])
    wide = f"TASK-{sequence:06d}"
    assert wide != waiting
    async with svc.store.transaction() as db:
        db.items[other.sequence_id].refs.append(f"{wide}:blocks")
    assert not _reported(await svc.check(), waiting)


async def test_removing_the_edge_from_either_end_is_reported_on_the_next_check(project) -> None:
    svc = service_with(project.squad_dir, _SELECTED)
    own = await _blocked_task(svc, "own edge")
    incoming = await _blocked_task(svc, "incoming edge")
    blocker = (await create_item(svc, "task", "blocker")).item
    await svc.add_ref(own, blocker.id, kind="depends-on")
    await svc.add_ref(blocker.id, incoming, kind="blocks")
    before = await svc.check()
    assert (_reported(before, own), _reported(before, incoming)) == (False, False)
    await svc.rm_ref(own, blocker.id, kind="depends-on")
    await svc.rm_ref(blocker.id, incoming, kind="blocks")
    after = await svc.check()
    assert (_reported(after, own), _reported(after, incoming)) == (True, True)


async def test_the_message_names_the_status_and_the_declared_dependency_kinds(project) -> None:
    svc = service_with(project.squad_dir, _SELECTED)
    waiting = await _blocked_task(svc)
    messages = [
        m for _, i, m in member_findings(await svc.check(), BLOCKED_HAS_BLOCKER) if i == waiting
    ]
    assert messages == [
        "status is Blocked but no dependency edge is recorded "
        "(kinds: blocks, depends-on) — add the blocker with `ref add`"
    ]


# ------------------------------------------------------------------------------ status shapes

_BUNDLED_STATUSES = ["Draft", "Ready", "InProgress", "InReview", "Blocked", "Done", "Cancelled"]


@pytest.mark.parametrize("status", _BUNDLED_STATUSES)
async def test_only_the_bundled_blocked_status_is_reported_with_no_edge(
    project, status: str
) -> None:
    svc = service_with(project.squad_dir, _SELECTED)
    item = (await create_item(svc, "task", "t")).item
    await svc.update(item.id, status=status, force=True)
    assert _reported(await svc.check(), item.id) is (status == "Blocked")


@pytest.mark.parametrize(
    ("override", "status", "reported"),
    [
        pytest.param(
            '[roles.stalled]\nsettled = false\ncolor = "danger"\nblocked = true\n\n'
            '[statuses.Blocked]\nrole = "stalled"\n',
            "Blocked",
            True,
            id="bundled-status-moved-to-a-role-of-the-projects-own",
        ),
        pytest.param(
            '[roles.stalled]\nsettled = false\ncolor = "danger"\nblocked = true\n\n'
            '[statuses.Draft]\nrole = "stalled"\n',
            "Draft",
            True,
            id="another-status-moved-to-a-flagged-role",
        ),
        pytest.param(
            "[roles.blocked]\nblocked = false\n\n"
            '[roles.stalled]\nsettled = false\ncolor = "danger"\nblocked = true\n\n'
            '[statuses.Draft]\nrole = "stalled"\n',
            "Blocked",
            False,
            id="role-named-blocked-with-the-flag-cleared",
        ),
        pytest.param(
            "[roles.blocked]\nblocked = false\n\n"
            '[roles.stalled]\nsettled = false\ncolor = "danger"\nblocked = true\n\n'
            '[statuses.Draft]\nrole = "stalled"\n',
            "Draft",
            True,
            id="flagged-role-under-another-name",
        ),
    ],
)
async def test_the_flag_of_the_role_decides_not_the_role_or_status_name(
    project, override: str, status: str, reported: bool
) -> None:
    svc = service_with(
        project.squad_dir, f'{override}\n[items.task]\nvalidators = ["blocked_has_blocker"]\n'
    )
    item = (await create_item(svc, "task", "t")).item
    await svc.update(item.id, status=status, force=True)
    assert _reported(await svc.check(), item.id) is reported


async def test_a_ref_kind_renamed_by_an_override_still_satisfies_through_its_role(project) -> None:
    toml = (
        '[selected]\nref_kinds = ["related", "implements", "fixes", "addresses", "supersedes", '
        '"duplicates", "scopes", "targets", "waits-on", "gates"]\n\n'
        '[ref_kinds.waits-on]\nlabel = "Waits on"\nhint = "A waits on B"\n'
        'role = "dependency"\ndirection = "dependent"\n\n'
        '[ref_kinds.gates]\nlabel = "Gates"\nhint = "A gates B"\n'
        'role = "dependency"\ndirection = "blocker"\n\n'
        '[items.task]\nvalidators = ["blocked_has_blocker"]\n'
    )
    svc = service_with(project.squad_dir, toml)
    assert "blocks" not in svc.spec.ref_kinds
    own = await _blocked_task(svc, "renamed outgoing")
    incoming = await _blocked_task(svc, "renamed incoming")
    bare = await _blocked_task(svc, "bare")
    other = (await create_item(svc, "task", "other")).item
    await svc.add_ref(own, other.id, kind="waits-on")
    await svc.add_ref(other.id, incoming, kind="gates")
    await svc.add_ref(bare, other.id)
    issues = await svc.check()
    assert (_reported(issues, own), _reported(issues, incoming), _reported(issues, bare)) == (
        False,
        False,
        True,
    )


# ---------------------------------------------------------------------------- selection shapes

_SELECTION_SHAPES = [
    ("unselected", (), None),
    ("plain", ("blocked_has_blocker",), "warn"),
    ("warn-suffix", ("blocked_has_blocker@warn",), "warn"),
    ("error-suffix", ("blocked_has_blocker@error",), "error"),
]


@pytest.mark.parametrize(("shape", "entries", "level"), _SELECTION_SHAPES, ids=lambda v: str(v))
async def test_the_selection_decides_whether_and_at_what_level_it_reports(
    project, shape: str, entries: tuple[str, ...], level: str | None
) -> None:
    waiting = await _blocked_task(service_with(project.squad_dir, override_toml(_TASK, ())))
    svc = service_with(project.squad_dir, override_toml(_TASK, entries))
    found = [
        lv for lv, i, _ in member_findings(await svc.check(), BLOCKED_HAS_BLOCKER) if i == waiting
    ]
    assert found == ([level] if level else [])


async def test_a_type_that_does_not_select_it_is_silent_while_another_that_does_reports(
    project,
) -> None:
    toml = override_toml(_TASK, ("blocked_has_blocker",)) + "\n[items.bug]\nvalidators = []\n"
    svc = service_with(project.squad_dir, toml)
    task = await _blocked_task(svc, "task")
    bug = (await create_item(svc, "bug", "bug")).item
    await svc.update(bug.id, status="Blocked", force=True)
    issues = await svc.check()
    assert (_reported(issues, task), _reported(issues, bug.id)) == (True, False)


async def test_a_list_that_replaces_the_bundled_one_and_one_that_splats_it_both_select_it(
    project,
) -> None:
    replaced = service_with(
        project.squad_dir, '[items.epic]\nvalidators = ["blocked_has_blocker"]\n'
    )
    epic = (await create_item(replaced, "epic", "e")).item
    await replaced.update(epic.id, status="Blocked", force=True)
    assert _reported(await replaced.check(), epic.id)
    splatted = service_with(
        project.squad_dir,
        '[items.epic]\nvalidators = ["$(*items.epic.validators)", "blocked_has_blocker"]\n',
    )
    assert _reported(await splatted.check(), epic.id)
