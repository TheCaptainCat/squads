"""The 0.16 step gives an operator written without a stored slug or full name (the shape an
older release's importer left) both, rewriting only that operator's frontmatter, so every reader
finds it without a fallback. It is planned with the rest of the step and writes nothing when the
step refuses."""

import re

import pytest

from _helpers import squad_tree
from _legacy_squad import read, reopen, roster, stamp_behind
from squads._errors import SquadsError
from squads._index._resolver import item_file

pytestmark = pytest.mark.anyio


async def _operator(svc, name: str, slug: str, *, drop: tuple[str, ...]):
    item = await svc.add_operator(name, slug=slug)
    path = item_file(svc.paths, item)
    text = await read(path)
    for key in drop:
        text = re.sub(rf"^  {key}: .*\n", "", text, count=1, flags=re.M)
    path.write_bytes(text.encode())
    return path


def _extra(text: str) -> dict[str, str]:
    return dict(re.findall(r"^  (slug|full_name): (.*)$", text, re.M))


#: (keys the file is missing, expected stored values after the run)
SHAPES = {
    "importer-shape": (("slug", "full_name"), {"slug": "op-imp", "full_name": "Imp Orted"}),
    "only-the-slug-missing": (("slug",), {"slug": "op-imp", "full_name": "Imp Orted"}),
    "only-the-name-missing": (("full_name",), {"slug": "op-imp", "full_name": "Imp Orted"}),
    "complete": ((), {"slug": "op-imp", "full_name": "Imp Orted"}),
}


@pytest.mark.parametrize(("drop", "expected"), SHAPES.values(), ids=list(SHAPES))
async def test_an_operator_is_given_exactly_what_it_lacks_and_nothing_else_changes(
    project, svc, drop, expected
) -> None:
    path = await _operator(svc, "Imp Orted", "op-imp", drop=drop)
    before = await read(path)
    stamp_behind(project.root)

    run = await reopen(project.root).run_pending_migrations()

    after = await read(path)
    assert _extra(after) == expected
    assert after.split("---\n", 2)[2] == before.split("---\n", 2)[2]  # the body is untouched
    filled = len(drop) > 0
    assert any(
        line.startswith(f"{int(filled)} operator(s) given a stored slug or full name")
        for report in run.reports.values()
        for line in report
    )
    if not filled:
        assert after == before


async def test_a_filled_in_operator_is_a_participant_for_every_reader(project, svc) -> None:
    await _operator(svc, "Imp Orted", "op-imp", drop=("slug", "full_name"))
    stamp_behind(project.root)
    await reopen(project.root).run_pending_migrations()
    migrated = reopen(project.root)

    task = (await migrated.create("task", "T", author="manager", assignee="op-imp")).item

    assert task.assignee == "op-imp"
    assert await migrated.author("op-imp") == "Imp Orted"


async def test_two_operators_and_the_other_files_are_handled_in_one_run(project, svc) -> None:
    await roster(svc)
    first = await _operator(svc, "Imp Orted", "op-imp", drop=("slug", "full_name"))
    second = await _operator(svc, "Other Person", "op-other", drop=("slug",))
    untouched = {
        k: v
        for k, v in squad_tree(project.root).items()
        if "operators" not in k or not k.endswith(("imp.md", "other.md"))
    }
    stamp_behind(project.root)

    await reopen(project.root).run_pending_migrations()

    assert _extra(await read(first))["slug"] == "op-imp"
    assert _extra(await read(second))["slug"] == "op-other"
    after = squad_tree(project.root)
    changed = {k for k, v in untouched.items() if after.get(k) != v}
    assert changed <= {".squads.toml", "squads/.squads.json", "squads/.reflog.jsonl"}


async def test_nothing_is_written_when_another_part_of_the_step_refuses(project, svc) -> None:
    path = await _operator(svc, "Imp Orted", "op-imp", drop=("slug", "full_name"))
    await svc.add_operator("Bad One", slug="op-bad")
    bad = item_file(svc.paths, await svc.roster_item("operator", "op-bad"))
    bad.write_bytes((await read(bad)).replace("slug: op-bad", "slug: bad").encode())
    before = await read(path)
    stamp_behind(project.root)

    with pytest.raises(SquadsError):
        await reopen(project.root).run_pending_migrations()

    assert await read(path) == before
