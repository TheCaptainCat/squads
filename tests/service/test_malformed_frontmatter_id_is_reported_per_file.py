"""A frontmatter `id:` that is not a well-formed id must be reported per file, never abort the
scan -- and no command may describe the same file in a way another command contradicts.

The original defect: `check` parsed the line unguarded and took the whole board down with an
`InvalidIdError`, telling the operator their squad was unreadable while `repair` said nothing was
wrong at all. The reporting split that fixed it stands -- `check` reports, `repair` rebuilds what it
can, `renumber`/`repad` refuse because they rewrite identity across the corpus and cannot correctly
rewrite one they cannot read.

What this module now also pins is the **wording**, because the fix's own message went wrong in a way
one example could not show. It promised that `sq repair` "rebuilds the index from this file without
complaint", verified against `id: TASK-abc` -- for which it is true. Across the shape family it is
not: a non-string `id: 5` is refused by the load boundary, so `repair` reports the file and leaves
the previous index entry in place, and the same sentence is reused verbatim by `renumber`, which
refuses outright. The message also offered "or delete it" as a fix, and a file with no `id:` at all
is reported too. So the message is pinned to describe the *file* -- the shape the line must have and
the correction that clears it -- and to promise no other command's outcome, since it cannot know it.
"""

from pathlib import Path

import pytest

from _helpers import create_item
from squads._errors import SquadsError
from squads._sections import join_frontmatter, split_frontmatter

pytestmark = pytest.mark.anyio


def _set_id(path: Path, value: object) -> None:
    text = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    fm["id"] = value
    path.write_text(join_frontmatter(fm, body), encoding="utf-8")


#: The shapes `number_for_id` cannot read, one per raising path: a trailing segment that is not an
#: integer (`InvalidIdError`), and two non-strings (`AttributeError` -- a raw builtin, which is why
#: an `except InvalidIdError` alone would not have been enough).
_MALFORMED_IDS: list[tuple[str, object]] = [
    ("non_integer_segment", "TASK-abc"),
    ("no_hyphen_at_all", "TASK"),
    ("int", 5),
    ("list", ["TASK", "9"]),
]
_IDS = [name for name, _ in _MALFORMED_IDS]
_VALUES = [value for _, value in _MALFORMED_IDS]


@pytest.mark.parametrize("bad_id", _VALUES, ids=_IDS)
async def test_check_reports_a_malformed_id_and_keeps_scanning(svc, bad_id):
    """The load-bearing half is the *second* assertion: one bad `id` used to abort the scan before
    a single other item was reported, so a board-wide report became a one-line error."""
    good = (await create_item(svc, "task", "an unrelated task with its own problem")).item
    good_path = svc.paths.abspath(good.path)
    good_path.write_text(
        good_path.read_text(encoding="utf-8").replace("<!-- sq:body:end -->", ""),
        encoding="utf-8",
    )
    bad = (await create_item(svc, "task", "a task with a malformed id")).item
    bad_path = svc.paths.abspath(bad.path)
    _set_id(bad_path, bad_id)

    issues = await svc.check()

    assert any(i.level == "error" and bad_path.name in i.item for i in issues), issues
    assert any("sq:body" in i.message for i in issues), (
        f"the scan must have continued past the malformed id, got: {issues}"
    )


async def _malformed_id_report(svc, bad_path: Path) -> str:
    """`check`'s message for *bad_path*'s malformed `id`, asserted to exist rather than defaulted --
    a helper that returned `""` for "not reported" would let every wording assertion below pass
    vacuously on a file nothing reported at all."""
    reported = [i for i in await svc.check() if bad_path.name in i.item and "`id`" in i.message]
    assert reported, f"{bad_path.name} must be reported with an `id` message"
    return reported[0].message


@pytest.mark.parametrize("bad_id", _VALUES, ids=_IDS)
async def test_check_names_the_shape_the_id_must_have_and_the_correction(svc, bad_id):
    """Neither command ever said the `id` line was garbage, which is the sharper half of the
    original inconsistency. What the report has to carry is what the operator cannot see from the
    file: that this line is *load-bearing* (the prefix half of the item's identity is read from it,
    and nothing else in the file supplies one), the shape it must have, and the correction."""
    bad = (await create_item(svc, "task", "a task with a malformed id")).item
    bad_path = svc.paths.abspath(bad.path)
    _set_id(bad_path, bad_id)

    message = await _malformed_id_report(svc, bad_path)

    assert "malformed" in message
    assert "<PREFIX>-<number>" in message
    assert "sequence_id" in message


@pytest.mark.parametrize("bad_id", _VALUES, ids=_IDS)
async def test_check_promises_no_repair_outcome_it_cannot_know(svc, bad_id):
    """The pair, on one file, for every shape in the family -- the drift guard the wording needs.

    `repair`'s outcome here is not one outcome: `TASK-abc` rebuilds cleanly, a non-string `id` is
    reported and the previous entry kept. So any sentence that narrates *a* repair outcome is false
    for some shape, which is how the two commands came to describe one file two ways. The assertion
    is therefore structural -- `check` names no other command at all -- rather than a match against
    one blessed wording, which is what let the previous sentence pass while being wrong.
    """
    bad = (await create_item(svc, "task", "a task with a malformed id")).item
    bad_path = svc.paths.abspath(bad.path)
    _set_id(bad_path, bad_id)

    message = await _malformed_id_report(svc, bad_path)
    result = await svc.repair()
    repair_reported = any(bad_path.name in msg for msg in result.unreadable)

    assert "sq repair" not in message, (
        "check must not narrate repair's outcome; on this shape repair reported the file: "
        f"{repair_reported}"
    )
    assert "without complaint" not in message
    assert "sq renumber" not in message and "sq repad" not in message


@pytest.mark.parametrize("bad_id", _VALUES, ids=_IDS)
async def test_check_does_not_offer_deleting_the_id_line_as_a_fix(svc, bad_id):
    """The remedy half, driven rather than reasoned: the old wording said "Fix the `id:` line (or
    delete it) to clear this", and deleting it swaps one error for another -- a file with no `id:`
    at all is reported by `check` too. A message may not name an action that does not clear it."""
    bad = (await create_item(svc, "task", "a task with a malformed id")).item
    bad_path = svc.paths.abspath(bad.path)
    _set_id(bad_path, bad_id)

    assert "delete" not in await _malformed_id_report(svc, bad_path)

    # Why it is not offered: the same file with the line gone is still an error.
    fm, body = split_frontmatter(bad_path.read_text(encoding="utf-8"))
    fm.pop("id")
    bad_path.write_text(join_frontmatter(fm, body), encoding="utf-8")

    assert any(
        i.level == "error" and bad_path.name in i.item and "no `id`" in i.message
        for i in await svc.check()
    ), "deleting the line must still be reported, or the old remedy was fine after all"


@pytest.mark.parametrize("bad_id", _VALUES, ids=_IDS)
async def test_correcting_the_id_line_is_a_remedy_that_actually_clears_it(svc, bad_id):
    """The other side of the same coin, and the one that makes the message honest rather than merely
    quiet: the single action it names has to work, for every shape it is printed for."""
    bad = (await create_item(svc, "task", "a task with a malformed id")).item
    bad_path = svc.paths.abspath(bad.path)
    _set_id(bad_path, bad_id)
    await _malformed_id_report(svc, bad_path)

    _set_id(bad_path, bad.id)

    assert not [i for i in await svc.check() if bad_path.name in i.item], "the fix must clear it"
    assert not (await svc.repair()).unreadable


@pytest.mark.parametrize("bad_id", _VALUES, ids=_IDS)
async def test_check_makes_no_phantom_missing_claim_for_a_malformed_id(svc, bad_id):
    """A file reported but dropped from the on-disk map turns into a fabricated "in the index but
    no markdown file found" -- a worse report than the abort it replaced, since it points at the
    wrong problem. Keyed by the filename stem, which is still perfectly readable."""
    bad = (await create_item(svc, "task", "a task with a malformed id")).item
    _set_id(svc.paths.abspath(bad.path), bad_id)

    issues = await svc.check()

    assert not any("no markdown file found" in i.message for i in issues), issues
    assert not any("on disk but not in index" in i.message for i in issues), issues


async def test_repair_rebuilds_a_non_integer_id_from_the_sequence_id_without_complaint(svc):
    """`repair`'s correct behaviour on this one shape, pinned so the `check` report above is not
    "fixed" by making repair refuse too. Both halves of the identity survive `TASK-abc`: the prefix
    parses off the id's own prefix segment and the number comes from `sequence_id`, so there is
    nothing for repair to fail on -- and the rebuilt entry carries the item's real id, not the
    garbage. This is the shape, and the only shape, the withdrawn "rebuilds without complaint"
    wording was true of."""
    bad = (await create_item(svc, "task", "a task with a malformed id")).item
    _set_id(svc.paths.abspath(bad.path), "TASK-abc")

    result = await svc.repair()

    assert bad.sequence_id in result.db.items
    assert result.db.items[bad.sequence_id].id == bad.id
    assert bad.id not in result.missing_ids
    assert not result.unreadable


async def test_repair_third_states_a_non_string_id_rather_than_minting_an_unresolved_one(svc):
    """The non-string shapes are a different case from `TASK-abc` and must not be folded into it: a
    non-string `id` leaves nothing to derive the prefix from, so accepting it would put an item
    whose id renders as the UNRESOLVED sentinel into the index. The load boundary refuses it, and
    repair third-states the file the way it does any other unreadable one."""
    bad = (await create_item(svc, "task", "a task with a non-string id")).item
    before = await svc.get(bad.id)
    bad_path = svc.paths.abspath(bad.path)
    _set_id(bad_path, 5)

    result = await svc.repair()

    assert any(bad_path.name in msg for msg in result.unreadable), result.unreadable
    assert (await svc.get(bad.id)).title == before.title
    assert not any("UNRESOLVED" in it.id for it in result.db.items.values())


@pytest.mark.parametrize("bad_id", _VALUES, ids=_IDS)
async def test_renumber_refuses_a_malformed_id_with_a_clean_error(svc, bad_id):
    """`renumber`/`repad` rewrite identity across the whole corpus, so refusing is right where
    `repair` proceeding is right -- but as a `SquadsError` naming the file, never the raw
    `AttributeError`/`InvalidIdError` the unguarded parse threw."""
    bad = (await create_item(svc, "task", "a task with a malformed id")).item
    _set_id(svc.paths.abspath(bad.path), bad_id)

    with pytest.raises(SquadsError) as exc:
        await svc.renumber(from_seq=1, by=100)

    assert "`id`" in str(exc.value)
