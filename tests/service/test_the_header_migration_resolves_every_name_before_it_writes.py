"""The comment-header contribution: every legacy header name is resolved against the whole
roster (live and retired, plus the two reserved names) before any file is written; a header that
cannot be resolved refuses the whole run, and a run that completes rewrites the header line of
each comment and nothing else."""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from _legacy_squad import TS, inject, read, reopen, roster, stamp_behind, task
from squads._errors import SquadsError
from squads._index._resolver import item_file
from squads._migrations import _v0_15_to_v0_16 as step
from squads._models import _markers as markers

pytestmark = pytest.mark.anyio


@dataclass(frozen=True)
class Row:
    header: str  # the line as the released writer left it, column 0
    migrated: str | None = None  # the line after the run, or None when the run must refuse
    refusal: str = ""  # a fragment of the failure line when it must refuse
    tail: str = "  - hello\n"  # what follows the header


def _legacy(name: str, ts: str = TS) -> str:
    return f"- [{ts}] {name}:"


def _new(slug: str, name: str, ts: str = TS) -> str:
    return f"- [{ts}] `{slug}` {name}:"


RESOLVING = {
    "bundled-role": Row(_legacy("Catherine Manager"), _new("manager", "Catherine Manager")),
    "bundled-role-activated": Row(_legacy("Paul Reviewer"), _new("reviewer", "Paul Reviewer")),
    "developer-role": Row(_legacy("Elias Python"), _new("python-dev", "Elias Python")),
    "operator-with-an-accent": Row(_legacy("Zoë Müller"), _new("op-zoe", "Zoë Müller")),
    "retired-role": Row(_legacy("Hugo Ops"), _new("devops", "Hugo Ops")),
    "retired-operator": Row(_legacy("Gone Person"), _new("op-gone", "Gone Person")),
    "anonymous-sentinel": Row(_legacy("Operator"), _new("operator", "Operator")),
    "system-entry": Row(_legacy("squads"), _new("squads", "squads")),
    "name-with-a-colon": Row(_legacy("Mara: the Tester"), _new("architect", "Mara: the Tester")),
    "already-migrated": Row(
        _new("manager", "Catherine Manager"), _new("manager", "Catherine Manager")
    ),
}

REFUSING = {
    "no-entry-for-a-renamed-author": Row(
        _legacy("Robert Architect"), refusal="'Robert Architect' matches no roster entry"
    ),
    "legacy-name-that-is-only-a-slug": Row(
        _legacy("manager"), refusal="'manager' matches no roster entry"
    ),
    "two-entries-share-a-name": Row(
        _legacy("Sam Lee"), refusal="'Sam Lee' matches 2 entries: op-sam, qa"
    ),
    "trailing-text-after-a-colon": Row(
        _legacy("Catherine Manager: and more"), refusal="'Catherine Manager: and more' matches no"
    ),
    "timestamp-not-in-the-grammar": Row(
        _legacy("Catherine Manager", "2025-05-20 11:00"),
        refusal="'2025-05-20 11:00' is not a timestamp sq writes",
    ),
    "timestamp-without-z": Row(
        _legacy("Catherine Manager", "2025-05-20T11:00:00"), refusal="is not a timestamp sq writes"
    ),
}

LEFT_ALONE = {
    "indented-header-shaped-line": Row(f"  {_legacy('Nobody Known')}"),
    "no-closing-colon": Row(f"- [{TS}] Nobody Known"),
    "other-bullet": Row(f"* [{TS}] Nobody Known:"),
    "text-before-the-bracket": Row(f"x - [{TS}] Nobody Known:"),
}


async def _squad(project, svc, row: Row, tag: str = markers.DISCUSSION):
    await roster(svc)
    item_id = await task(svc)
    path = await inject(svc, item_id, f"{row.header}\n{row.tail}", tag)
    stamp_behind(project.root)
    return item_id, path


def _hash(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and (p.suffix == ".md" or p.name == ".squads.toml")
    }


@pytest.mark.parametrize("row", RESOLVING.values(), ids=RESOLVING)
async def test_a_resolvable_header_is_rewritten_and_every_other_byte_is_kept(
    project, svc, row
) -> None:
    _, path = await _squad(project, svc, row)
    before = await read(path)

    run = await reopen(project.root).run_pending_migrations()

    assert [m.to_schema for m in run.applied] == ["0.16"]
    after = await read(path)
    assert after == before.replace(row.header, row.migrated, 1)
    assert after.count("\n") == before.count("\n")


@pytest.mark.parametrize("row", LEFT_ALONE.values(), ids=LEFT_ALONE)
async def test_a_line_that_is_not_a_header_is_left_as_it_is(project, svc, row) -> None:
    _, path = await _squad(project, svc, row)
    before = await read(path)

    await reopen(project.root).run_pending_migrations()

    assert await read(path) == before


@pytest.mark.parametrize("row", REFUSING.values(), ids=REFUSING)
async def test_an_unresolvable_header_refuses_the_run_and_writes_nothing(project, svc, row) -> None:
    await _squad(project, svc, row)
    before = _hash(project.root)

    with pytest.raises(SquadsError) as raised:
        await reopen(project.root).run_pending_migrations()

    assert row.refusal in str(raised.value)
    assert "This step wrote nothing and the schema stamp is unchanged." in str(raised.value)
    assert _hash(project.root) == before


SHARED_LINE_SHAPES = {
    "open and close on one line": (
        lambda t: re.sub(
            re.escape(markers.open_marker(markers.DISCUSSION))
            + r"\s*"
            + re.escape(markers.close_marker(markers.DISCUSSION)),
            markers.open_marker(markers.DISCUSSION) + markers.close_marker(markers.DISCUSSION),
            t,
            count=1,
        )
    ),
    "header on the open marker's line": (
        lambda t: t.replace(
            markers.open_marker(markers.DISCUSSION),
            f"{markers.open_marker(markers.DISCUSSION)}{_legacy('Catherine Manager')}",
            1,
        )
    ),
    "text before the close marker": (
        lambda t: t.replace(
            markers.close_marker(markers.DISCUSSION),
            f"  - tail {markers.close_marker(markers.DISCUSSION)}",
            1,
        )
    ),
}


MALFORMED_MARKERS = {
    "no space after the opening dashes": lambda t: t.replace(
        "<!-- sq:discussion:end -->", "<!--sq:discussion:end -->", 1
    ),
    "two spaces around the tag": lambda t: t.replace(
        "<!-- sq:discussion -->", "<!--  sq:discussion  -->", 1
    ),
}


@pytest.mark.parametrize("edit", MALFORMED_MARKERS.values(), ids=MALFORMED_MARKERS)
async def test_a_lone_marker_spelled_unusually_is_called_malformed_not_shared(
    project, svc, edit
) -> None:
    await roster(svc)
    path = await inject(svc, await task(svc), "")
    path.write_bytes(edit(await read(path)).encode("utf-8"))
    stamp_behind(project.root)

    with pytest.raises(SquadsError) as raised:
        await reopen(project.root).run_pending_migrations()

    assert "is not a well-formed sq marker" in str(raised.value)
    assert "shares its line" not in str(raised.value)


@pytest.mark.parametrize("edit", SHARED_LINE_SHAPES.values(), ids=SHARED_LINE_SHAPES)
async def test_a_marker_that_shares_its_line_with_text_refuses_instead_of_leaving_a_header(
    project, svc, edit
) -> None:
    await roster(svc)
    path = await inject(svc, await task(svc), "")
    path.write_bytes(edit(await read(path)).encode("utf-8"))
    stamp_behind(project.root)
    before = _hash(project.root)

    with pytest.raises(SquadsError) as raised:
        await reopen(project.root).run_pending_migrations()

    assert "shares its line with text" in str(raised.value)
    assert _hash(project.root) == before


async def test_a_header_inside_an_item_body_is_not_looked_at(project, svc) -> None:
    await roster(svc)
    item_id = await task(svc)
    path = await inject(svc, item_id, f"{_legacy('Nobody Known')}\n", markers.BODY)
    stamp_behind(project.root)
    before = await read(path)

    await reopen(project.root).run_pending_migrations()

    assert await read(path) == before


async def test_a_discussion_that_is_never_closed_is_a_failure_of_its_own(project, svc) -> None:
    item_id, path = await _squad(project, svc, RESOLVING["bundled-role"])
    text = (await read(path)).replace(markers.close_marker(markers.DISCUSSION), "")
    path.write_bytes(text.encode("utf-8"))
    before = _hash(project.root)

    with pytest.raises(SquadsError) as raised:
        await reopen(project.root).run_pending_migrations()

    assert "discussion region `discussion` is not closed" in str(raised.value)
    assert _hash(project.root) == before
    assert item_file(svc.paths, await svc.get(item_id)).name in str(raised.value)


async def test_an_operator_imported_without_a_full_name_is_known_by_its_slug(project, svc) -> None:
    """The released writer named such an operator by its slug in every comment header."""
    created = await svc.import_events(
        json.dumps(
            {
                "op": "create",
                "type": "operator",
                "title": "Ann Person",
                "slug": "op-ann",
                "as": "manager",
            }
        )
    )
    assert created.applied is not None, created.plan.issues
    entry = item_file(svc.paths, await svc.roster_item("operator", "op-ann"))
    entry.write_bytes(
        re.sub(r"^  (slug|full_name): .*\n", "", await read(entry), flags=re.M).encode()
    )
    item_id = await task(svc)
    target = await inject(svc, item_id, f"{_legacy('op-ann')}\n  - hi\n")
    stamp_behind(project.root)

    await reopen(project.root).run_pending_migrations()

    assert _new("op-ann", "op-ann") in await read(target)


async def test_a_role_titled_operator_matches_two_entries_with_the_reserved_one(
    project, svc
) -> None:
    await svc.activate_role("reviewer", name="Operator")
    item_id = await task(svc)
    await inject(svc, item_id, f"{_legacy('Operator')}\n  - hi\n")
    stamp_behind(project.root)

    with pytest.raises(SquadsError, match="'Operator' matches 2 entries: operator, reviewer"):
        await reopen(project.root).run_pending_migrations()


async def test_the_step_is_the_only_thing_that_runs_on_a_0_15_squad_with_one_contribution(
    project, svc
) -> None:
    stamp_behind(project.root)

    run = await reopen(project.root).run_pending_migrations()

    assert [m.to_schema for m in run.applied] == ["0.16"]
    assert [c.name for c in step.CONTRIBUTIONS] == ["comment-headers"]
