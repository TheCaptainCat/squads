"""The 0.16 step checks every role and operator, live or retired, against its slug grammar and the
one author namespace before it resolves a header: an entry in breach refuses the run with one
file-level line, beside any header failure, and writes nothing."""

import re
from pathlib import Path

import pytest

from _helpers import squad_tree
from _legacy_squad import TS, inject, read, reopen, roster, stamp_behind, task
from squads._errors import SquadsError
from squads._index._resolver import item_file
from squads._migrations import _v0_15_to_v0_16 as step

pytestmark = pytest.mark.anyio


async def _set_slug(svc, item_type: str, old: str, new: str) -> Path:
    """Hand-edit an entry's slug in its file, the way a merge or an editor would."""
    path = item_file(svc.paths, await svc.roster_item(item_type, old))
    text = re.sub(rf"^(\s*slug): {re.escape(old)}$", rf"\1: {new}", await read(path), flags=re.M)
    path.write_bytes(text.encode())
    return path


# (item type, current slug, slug it is edited to, fragment of its line)
OPERATOR_START = "does not start with 'op-'"
BREACHES = {
    "system-slug": ("operator", "op-zoe", "squads", f"operator slug 'squads' {OPERATOR_START}"),
    "anonymous-slug": (
        "operator",
        "op-zoe",
        "operator",
        f"operator slug 'operator' {OPERATOR_START}",
    ),
    "capitals-and-a-space": (
        "operator",
        "op-zoe",
        "OP-Z oe",
        f"operator slug 'OP-Z oe' {OPERATOR_START}",
    ),
    "empty-tail": (
        "operator",
        "op-zoe",
        "op-",
        "operator slug 'op-' is not 'op-' followed by lowercase letters, digits and hyphens",
    ),
    "a-live-roles-slug": (
        "operator",
        "op-zoe",
        "reviewer",
        f"operator slug 'reviewer' {OPERATOR_START}; also held by ROLE-",
    ),
    "retired-operator": (
        "operator",
        "op-gone",
        "qa",
        f"operator slug 'qa' {OPERATOR_START}; also held by ROLE-",
    ),
    "role-holding-the-operator-prefix": (
        "role",
        "reviewer",
        "op-reviewer",
        "role slug 'op-reviewer' is reserved for operators",
    ),
    "role-holding-a-reserved-slug": (
        "role",
        "reviewer",
        "squads",
        "role slug 'squads' is reserved for system entries",
    ),
    "role-outside-the-grammar": (
        "role",
        "reviewer",
        "Bad_Slug",
        "role slug 'Bad_Slug' is not lowercase letters, digits",
    ),
    "retired-role": ("role", "devops", "op-ops", "role slug 'op-ops' is reserved for operators"),
    "operators-sharing-a-slug": (
        "operator",
        "op-zoe",
        "op-sam",
        "operator slug 'op-sam' is not unique; also held by OP-",
    ),
}


@pytest.mark.parametrize("beside_a_header_failure", [False, True], ids=["alone", "beside-header"])
@pytest.mark.parametrize(
    ("item_type", "old", "new", "fragment"), BREACHES.values(), ids=list(BREACHES)
)
async def test_a_breaching_entry_refuses_the_run_once_and_writes_nothing(
    project, svc, item_type, old, new, fragment, beside_a_header_failure
) -> None:
    await roster(svc)
    path = await _set_slug(svc, item_type, old, new)
    if beside_a_header_failure:
        await inject(svc, await task(svc), f"- [{TS}] Nobody Known:\n  - hi\n")
    stamp_behind(project.root)
    original = squad_tree(project.root)

    with pytest.raises(SquadsError) as raised:
        await reopen(project.root).run_pending_migrations()

    # The run rebuilds the index from the files before its first step; nothing else changes.
    settled = squad_tree(project.root)
    index = "squads/.squads.json"
    assert {k: v for k, v in settled.items() if k != index} == {
        k: v for k, v in original.items() if k != index
    }
    with pytest.raises(SquadsError):
        await reopen(project.root).run_pending_migrations()
    assert squad_tree(project.root) == settled
    message = str(raised.value)
    rel = path.relative_to(project.squad_dir).as_posix()
    lines = [ln for ln in message.splitlines() if ln.startswith(f"{rel}: ")]
    breach = [ln for ln in lines if fragment in ln]
    assert len(breach) == 1, message
    # the edit also leaves the stored slug unlike the file name's, which the flattening names
    assert [ln for ln in lines if ln not in breach] <= [
        ln for ln in lines if "differs from the file name's slug" in ln
    ], message
    assert ("'Nobody Known' matches no roster entry" in message) is beside_a_header_failure
    assert "This step wrote nothing and the schema stamp is unchanged." in message


async def test_every_breach_is_listed_in_one_report_with_the_count(project, svc) -> None:
    await roster(svc)
    await _set_slug(svc, "operator", "op-zoe", "squads")
    await _set_slug(svc, "role", "reviewer", "op-reviewer")
    stamp_behind(project.root)

    with pytest.raises(SquadsError) as raised:
        await reopen(project.root).run_pending_migrations()

    message = str(raised.value)
    # each edit is a breach and leaves its stored slug unlike the file name's: two lines apiece
    assert "4 problem(s) found." in message
    assert message.count("differs from the file name's slug") == 2


async def test_a_compliant_roster_migrates(project, svc) -> None:
    await roster(svc)
    stamp_behind(project.root)

    run = await reopen(project.root).run_pending_migrations()

    assert [m.to_schema for m in run.applied] == ["0.16"]


def test_the_manual_gives_the_remedy_and_no_longer_says_nothing_is_refused() -> None:
    text = " ".join(step.MANUAL.split())

    assert "nothing is refused" not in text
    assert "sq operator <id> remove --purge" in text
    assert 'sq operator add "<the same full name>"' in text
    assert "a plain `rm` drops the entry from the index but keeps its file" in text
    assert "sq role <id> remove --purge" in text
    assert "update --assignee <new slug>" in text


@pytest.mark.parametrize(("kind", "slug"), [("role", "list"), ("skill", "add")])
async def test_a_group_verb_slug_does_not_refuse_the_run(project, svc, monkeypatch, kind, slug):
    from squads._services import _base

    with monkeypatch.context() as unchecked:
        unchecked.setattr(_base, "_check_roster_slug", lambda *args, **kwargs: None)
        await svc.create(
            kind,
            "Verb Holder",
            slug=slug,
            author="manager",
        )
    stamp_behind(project.root)

    run = await reopen(project.root).run_pending_migrations()

    assert [m.to_schema for m in run.applied] == ["0.16"]
