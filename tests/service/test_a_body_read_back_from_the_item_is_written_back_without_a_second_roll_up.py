"""A body read back from `show --json` can be written back: a view tag it carries that is
already placed in the same state is kept in place, and any other view tag or marker is refused."""

import json

import pytest

from _helpers import create_item
from squads import __version__
from squads._errors import SquadsError
from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._rendering._engine import invalidate_squad_dir
from squads._services._service import Service
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

ROLLUP = markers.open_marker(markers.view_tag("milestone_rollup"))
ROLLUP_DISABLED = markers.open_marker(markers.view_tag("milestone_rollup", disabled=True))
PROSE = "# Goal\n\nShip the release.\n"

TASK_WITH_ROLLUP_TEMPLATE = (
    "<!-- sq:body -->\n## Description\n\n_TODO_\n"
    f"{ROLLUP}\n<!-- sq:body:end -->\n\n## Discussion\n\n"
    "<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"
)


async def milestone_with_prose(svc):
    milestone = (await create_item(svc, "milestone", "Ship")).item
    await svc.set_body(milestone.id, PROSE, force=True)
    return milestone


def file_text(svc, item) -> str:
    return item_file(svc.paths, item).read_text(encoding="utf-8")


def placed_tags(svc, item) -> int:
    return file_text(svc, item).count("sq:view:milestone_rollup")


# (name, incoming body from the stored one, expected prose in the file or None when refused)
WRITE_BACKS = {
    "unchanged": (lambda stored: stored, None),
    "edited prose": (lambda stored: stored.replace("Ship the", "Ship this"), "Ship this release."),
    "tag moved to the first line": (lambda stored: f"{ROLLUP}\n{PROSE}", None),
}


@pytest.mark.parametrize("name", list(WRITE_BACKS))
async def test_a_stored_body_written_back_keeps_exactly_one_tag_at_its_place(svc, name) -> None:
    milestone = await milestone_with_prose(svc)
    before = file_text(svc, milestone)
    stored = await svc.read_stored_body(milestone.id)
    assert ROLLUP in stored
    make_incoming, edited = WRITE_BACKS[name]

    await svc.set_body(milestone.id, make_incoming(stored), force=True)

    after = file_text(svc, milestone)
    assert placed_tags(svc, milestone) == 1
    if edited is None:
        assert after == before
    else:
        assert edited in after
        assert after.replace(edited, "Ship the release.") == before


async def test_a_tag_disabled_in_the_incoming_body_but_enabled_on_the_item_is_refused(svc) -> None:
    milestone = await milestone_with_prose(svc)
    before = file_text(svc, milestone)
    incoming = (await svc.read_stored_body(milestone.id)).replace(ROLLUP, ROLLUP_DISABLED)

    with pytest.raises(SquadsError) as raised:
        await svc.set_body(milestone.id, incoming, force=True)

    message = str(raised.value)
    assert "sq:view:milestone_rollup:disabled" in message
    assert "Leave it out" in message
    assert f"sq milestone {milestone.sequence_id} view disable milestone_rollup" in message
    assert file_text(svc, milestone) == before


async def test_a_tag_not_placed_on_the_item_is_refused_naming_the_view_verbs(svc) -> None:
    task = (await create_item(svc, "task", "Not a milestone")).item
    before = file_text(svc, task)

    with pytest.raises(SquadsError) as raised:
        await svc.set_body(task.id, f"{PROSE}{ROLLUP}\n", force=True)

    message = str(raised.value)
    assert "sq:view:milestone_rollup" in message
    assert "Leave it out" in message
    assert f"sq task {task.sequence_id} view add milestone_rollup" in message
    assert file_text(svc, task) == before


async def test_a_tag_naming_an_undeclared_view_is_refused_without_naming_view_verbs(svc) -> None:
    milestone = await milestone_with_prose(svc)
    unknown = markers.open_marker(markers.view_tag("no_such_view"))

    with pytest.raises(SquadsError) as raised:
        await svc.set_body(milestone.id, f"{PROSE}{unknown}\n", force=True)

    message = str(raised.value)
    assert "sq:view:no_such_view" in message
    assert "Leave it out" in message
    assert "view add" not in message
    assert "view disable" not in message


async def test_a_non_view_marker_is_refused_with_the_generic_message(svc) -> None:
    milestone = await milestone_with_prose(svc)

    with pytest.raises(SquadsError, match="must not contain sq marker comments"):
        await svc.set_body(milestone.id, "text\n<!-- sq:body:end -->\n", force=True)


async def test_an_override_seeded_tag_on_another_type_round_trips_unchanged(project) -> None:
    template_dir = project.squad_dir / ".overrides" / "templates" / "items"
    template_dir.mkdir(parents=True)
    (template_dir / "task.md.j2").write_text(TASK_WITH_ROLLUP_TEMPLATE, encoding="utf-8")
    (project.squad_dir / ".overrides" / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n", encoding="utf-8"
    )
    invalidate_squad_dir(project.squad_dir)
    svc = Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))
    task = (await create_item(svc, "task", "Seeded")).item
    await svc.set_body(task.id, PROSE, force=True)
    before = file_text(svc, task)

    await svc.set_body(task.id, await svc.read_stored_body(task.id), force=True)

    assert file_text(svc, task) == before
    assert placed_tags(svc, task) == 1


async def test_an_appended_stored_body_keeps_exactly_one_tag(svc) -> None:
    milestone = await milestone_with_prose(svc)

    await svc.set_body(milestone.id, await svc.read_stored_body(milestone.id), append=True)

    assert placed_tags(svc, milestone) == 1


async def test_an_imported_stored_body_keeps_exactly_one_tag(svc) -> None:
    milestone = await milestone_with_prose(svc)
    line = json.dumps(
        {
            "op": "body",
            "target": milestone.id,
            "body": await svc.read_stored_body(milestone.id),
            "force": True,
            "as": "manager",
        }
    )

    result = await svc.import_events(line)

    assert result.plan.ok, [i.message for i in result.plan.issues]
    assert placed_tags(svc, milestone) == 1


async def test_an_unplaced_view_tag_on_a_type_without_view_verbs_names_none(svc) -> None:
    operator = (await create_item(svc, "operator", "Alice")).item

    with pytest.raises(SquadsError) as raised:
        await svc.set_body(operator.id, f"hello\n{ROLLUP}\n", force=True)

    message = str(raised.value)
    assert "sq:view:milestone_rollup" in message
    assert "view add" not in message
    assert "view disable" not in message


def body_op(target: str, body: str) -> str:
    return json.dumps(
        {"op": "body", "target": target, "body": body, "force": True, "as": "manager"}
    )


# (case, target kind, body builder from the stored body, expected plan issue on line 1)
DRY_RUNS = {
    "placed tag read back": ("milestone", lambda stored: stored, False),
    "tag not placed on the target": ("task", lambda stored: f"{PROSE}{ROLLUP}\n", True),
    "tag disabled against an enabled one": (
        "milestone",
        lambda stored: stored.replace(ROLLUP, ROLLUP_DISABLED),
        True,
    ),
}


@pytest.mark.parametrize("case", list(DRY_RUNS))
async def test_the_import_dry_run_lists_an_unplaced_view_tag_with_its_line(svc, case) -> None:
    kind, make_body, refused = DRY_RUNS[case]
    target = (await create_item(svc, kind, "Target")).item
    stored = await svc.read_stored_body(target.id)

    result = await svc.import_events(body_op(target.id, make_body(stored)), dry_run=True)

    if refused:
        assert [(i.line, "Leave it out" in i.message) for i in result.plan.issues] == [(1, True)]
    else:
        assert result.plan.ok, [i.message for i in result.plan.issues]


async def test_the_import_dry_run_checks_an_item_the_same_file_creates(svc) -> None:
    lines = [
        json.dumps(
            {"op": "create", "type": "task", "title": "New", "handle": "t", "as": "manager"}
        ),
        body_op("t", f"{PROSE}{ROLLUP}\n"),
    ]

    result = await svc.import_events("\n".join(lines), dry_run=True)

    assert [i.line for i in result.plan.issues] == [2]
