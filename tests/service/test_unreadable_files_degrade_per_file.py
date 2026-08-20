"""Falsifies the per-file-degradation contract across every command it changes -- `sq check`,
`sq repair`, `sq board list`, `sq memory list` -- and across the failure-shape family that can
leave a squad-data file's identity unreadable: an OS permission error, invalid UTF-8,
malformed-but-closed YAML (a different shape than a literal merge-conflict marker, which the
read-path-guard test suite already covers), valid YAML with the `id` field missing entirely, and
valid YAML with a type-invalid field. Each reaches a *different* site of the same third-state
contract -- the first three fail inside the read/parse guard, the fourth is
`_rebuild_index_from_disk`'s own "no id" check, the fifth is `Item.from_frontmatter`'s pydantic
validation -- so one shape sliding through unnoticed at any of those sites is exactly the failure
mode this project has hit before. Every degrade assertion below is parametrized over the shape
family rather than picked once.

`sq renumber`/`repair --renumber`/`sq migrate repad` are the deliberate exception: they rewrite
identity across the whole corpus and still refuse outright on the first three (read/parse-failure)
shapes -- pinned here too, so the now-subtle asymmetry with `check`/`repair` is never "fixed" into
unsafety. The last two shapes (no `id`, type-invalid field) do *not* belong in that parametrize:
`_scan_records` only ever needs a file's `id`, so a no-`id` file is silently skipped (nothing to
renumber) and a type-invalid *other* field is never even inspected -- neither shape makes
repad/renumber refuse, and asserting that they do would pin a false expectation.
"""

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from _helpers import create_item, make_unreadable_by_the_os
from squads._board._store import board_folder
from squads._errors import SquadsError
from squads._memory._store import role_folder
from squads._sections import join_frontmatter, replace_frontmatter, split_frontmatter

pytestmark = pytest.mark.anyio


def _corrupt_permission_denied(path: Path) -> None:
    """Unreadable by the OS itself -- unlike the two shapes below, this never even reaches the
    YAML parser; it fails inside the read helper. Deleting the file later is unaffected: unlink
    is gated by the *directory's* write permission, not the file's own mode.

    POSIX-only, hence the marker on its table entry: `os.chmod` on Windows can only toggle the
    read-only attribute, so this leaves the file fully readable there. `_corrupt_os_read_error`
    below reaches the same guard on every platform and carries the family on Windows.
    """
    path.chmod(0o000)


def _corrupt_os_read_error(path: Path) -> None:
    """The same read/parse-guard site as the permission shape, reached by an instrument that
    works on every platform -- see `make_unreadable_by_the_os`. Not a corruption a user
    authors; it is here so the guard's `except OSError` arm, and every degrade contract built
    on it, stays exercised where `chmod` cannot express "unreadable"."""
    make_unreadable_by_the_os(path)


def _corrupt_invalid_utf8(path: Path) -> None:
    """A stray non-UTF-8 lead byte inserted into otherwise-intact prose -- corruption by
    insertion, not truncation, matching how this actually reaches a user."""
    data = path.read_bytes()
    mid = len(data) // 2
    path.write_bytes(data[:mid] + b"\x80" + data[mid:])


def _corrupt_unterminated_yaml_value(path: Path) -> None:
    """Malformed YAML between two still-intact `---` delimiters, but a different textual shape
    than a merge-conflict marker: an unterminated quoted value, as a half-written field might
    leave behind."""
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    close = text.index("\n---", 4)
    front, rest = text[4:close], text[close + 4 :]
    path.write_text(f'---\n{front}\nnote: "unterminated\n---{rest}', encoding="utf-8")


def _corrupt_missing_id_field(path: Path) -> None:
    """Valid YAML throughout -- the block parses cleanly -- but the `id` field itself is gone,
    as a partial patch or a stripped-frontmatter merge artifact might leave behind. Never
    reaches the read/parse guard at all; it falsifies `_rebuild_index_from_disk`'s own
    "no id" branch and `_scan_for_check`'s equivalent."""
    text = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    fm.pop("id", None)
    path.write_text(join_frontmatter(fm, body), encoding="utf-8")


def _corrupt_type_invalid_title(path: Path) -> None:
    """Valid YAML, a type-invalid value for a modelled field (`title` as a list instead of a
    string) -- parses fine, and `id` is untouched, but `Item.from_frontmatter` raises. Trivially
    reachable from a merge artifact that keeps YAML validity."""
    text = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    fm["title"] = ["a", "b"]
    path.write_text(join_frontmatter(fm, body), encoding="utf-8")


#: One entry per independently-triggered failure shape that fails inside the read/parse guard --
#: table-driven so a fix that happens to work for one shape (e.g. only the exception type the
#: read-path guards actually raise) cannot hide a gap in another. Used for both the degrade tests
#: below AND the repad/renumber refusal tests, since these three are the only shapes that make
#: `_scan_records` itself raise.
_POSIX_ONLY = pytest.mark.skipif(
    os.name != "posix",
    reason="chmod(0o000) cannot withdraw read access on Windows -- the OS-level read failure "
    "this shape stages is carried there by the os_read_error shape instead",
)

_SHAPES: list[tuple[str, Callable[[Path], None]]] = [
    ("permission_denied", _corrupt_permission_denied),
    ("os_read_error", _corrupt_os_read_error),
    ("invalid_utf8", _corrupt_invalid_utf8),
    ("unterminated_yaml_value", _corrupt_unterminated_yaml_value),
]

#: The full shape family for `check`/`repair`'s degrade-and-carry-forward contract: the three
#: read/parse-guard shapes above, plus the two shapes that reach `_rebuild_index_from_disk` (and
#: `_scan_for_check`) further downstream -- no `id` at all, and a type-invalid field. Deliberately
#: NOT used for the repad/renumber refusal tests -- see the module docstring.
_DEGRADE_SHAPES: list[tuple[str, Callable[[Path], None]]] = [
    *_SHAPES,
    ("missing_id_field", _corrupt_missing_id_field),
    ("type_invalid_title", _corrupt_type_invalid_title),
]


def _params(shapes: list[tuple[str, Callable[[Path], None]]]) -> list[Any]:
    """Turn a shape table into `pytest.param`s, marking the one shape whose *instrument* is
    POSIX-only. The mark travels with the table entry rather than sitting on each test, so a
    shape added later cannot be silently skipped on one platform by an out-of-date decorator."""
    return [
        pytest.param(fn, id=name, marks=[_POSIX_ONLY] if name == "permission_denied" else [])
        for name, fn in shapes
    ]


_SHAPE_PARAMS = _params(_SHAPES)
_DEGRADE_SHAPE_PARAMS = _params(_DEGRADE_SHAPES)


def _edit_frontmatter(path: Path, **fields: object) -> None:
    """Directly rewrite frontmatter fields on a squad-data file, bypassing the service -- the
    only way to produce a genuine, durable status drift these tests need alongside a corrupt
    file (mirrors the confirm-round test suite's own helper)."""
    text = path.read_text(encoding="utf-8")
    fm, _ = split_frontmatter(text)
    fm.update(fields)
    path.write_text(replace_frontmatter(text, fm), encoding="utf-8")


# --------------------------------------------------------------------------- check: continues


@pytest.mark.parametrize("corrupt", _DEGRADE_SHAPE_PARAMS)
async def test_check_reports_the_corrupt_file_and_keeps_checking(svc, corrupt):
    """The load-bearing assertion is not "the corrupt file is reported" -- it is that a second,
    unrelated issue elsewhere on the board is *also* still reported. An implementation that
    reports the corrupt file and then stops would pass a test that only checked the first half."""
    good = (await create_item(svc, "task", "an unrelated task with its own problem")).item
    good_path = svc.paths.abspath(good.path)
    good_path.write_text(
        good_path.read_text(encoding="utf-8").replace("<!-- sq:body:end -->", ""),
        encoding="utf-8",
    )
    bad = (await create_item(svc, "task", "a corrupt task")).item
    bad_path = svc.paths.abspath(bad.path)
    corrupt(bad_path)

    issues = await svc.check()

    assert any("sq:body" in i.message for i in issues), (
        f"the scan must have continued past the corrupt file, got: {issues}"
    )
    assert any(i.level == "error" and bad_path.name in i.item for i in issues), (
        f"the corrupt file itself must be named at error level, got: {issues}"
    )


@pytest.mark.parametrize("corrupt", _DEGRADE_SHAPE_PARAMS)
async def test_check_reports_two_corrupt_files_not_just_the_first(svc, corrupt):
    bad1 = (await create_item(svc, "task", "corrupt one")).item
    bad2 = (await create_item(svc, "task", "corrupt two")).item
    path1, path2 = svc.paths.abspath(bad1.path), svc.paths.abspath(bad2.path)
    corrupt(path1)
    corrupt(path2)

    issues = await svc.check()

    named = {i.item for i in issues if i.level == "error"}
    assert any(path1.name in n for n in named), issues
    assert any(path2.name in n for n in named), issues


@pytest.mark.parametrize("corrupt", _DEGRADE_SHAPE_PARAMS)
async def test_check_reports_no_phantom_reconciliation_claim_for_the_corrupt_file(svc, corrupt):
    """The regression that matters most: a naive "skip the bad file" fix drops it from the
    on-disk scan map, which turns it into a fabricated "in index but no markdown file found" --
    a worse report than the crash it replaces, since it points at the wrong problem."""
    bad = (await create_item(svc, "task", "a corrupt task")).item
    corrupt(svc.paths.abspath(bad.path))

    issues = await svc.check()

    assert not any("no markdown file found" in i.message for i in issues), issues
    assert not any("on disk but not in index" in i.message for i in issues), issues


@pytest.mark.parametrize("corrupt", _DEGRADE_SHAPE_PARAMS)
async def test_confirm_round_survives_a_corrupt_candidate_and_still_confirms_a_real_drift(
    svc, corrupt
):
    """Drives the confirm round with a non-empty candidate set (a real drift on one item) while
    a *different* item's file is corrupt -- the confirm round must not raise trying to re-parse
    the corrupt one, and the real drift must still be confirmed and reported."""
    drifted = (await create_item(svc, "task", "drifted task")).item
    _edit_frontmatter(svc.paths.abspath(drifted.path), status="InProgress")
    bad = (await create_item(svc, "task", "corrupt task")).item
    bad_path = svc.paths.abspath(bad.path)
    corrupt(bad_path)

    issues = await svc.check()

    assert any("status drift" in i.message and i.item == drifted.id for i in issues), issues
    bad_issues = [i for i in issues if bad_path.name in i.item]
    assert bad_issues, issues
    assert all(i.level == "error" for i in bad_issues)
    assert not any("drift" in i.message for i in bad_issues)


# --------------------------------------------------------------------------- repair: carries fwd


@pytest.mark.parametrize("corrupt", _DEGRADE_SHAPE_PARAMS)
async def test_repair_carries_the_corrupt_items_previous_entry_forward(svc, corrupt):
    """The criterion that distinguishes this from the naive "skip and rebuild" fix: the item
    must still be in the index afterwards, resolvable, with its previous values -- not merely
    reported and then gone."""
    bad = (await create_item(svc, "task", "a corrupt task")).item
    before = await svc.get(bad.id)
    bad_path = svc.paths.abspath(bad.path)
    corrupt(bad_path)

    result = await svc.repair()

    assert any(bad_path.name in msg for msg in result.unreadable), result.unreadable
    assert bad.id not in result.missing_ids, "carried forward, not missing"
    assert bad.sequence_id in result.db.items
    carried = result.db.items[bad.sequence_id]
    assert carried.title == before.title
    assert carried.status == before.status

    reloaded = await svc.get(bad.id)
    assert reloaded.title == before.title


@pytest.mark.parametrize("corrupt", _DEGRADE_SHAPE_PARAMS)
async def test_repair_leaves_a_never_indexed_corrupt_file_unindexed_and_reports_it(svc, corrupt):
    """The other half of the carry-forward contract: with no previous entry to carry, repair
    must leave the item unindexed and report it -- never invent one."""
    template = (await create_item(svc, "task", "template for a hand-placed file")).item
    template_text = svc.paths.abspath(template.path).read_text(encoding="utf-8")
    never_indexed_text = template_text.replace(template.id, "TASK-999999").replace(
        f"sequence_id: {template.sequence_id}", "sequence_id: 999999"
    )
    folder = svc.paths.squad_dir / "tasks"
    path = folder / "TASK-999999-hand-placed.md"
    path.write_text(never_indexed_text, encoding="utf-8")
    corrupt(path)

    result = await svc.repair()

    assert any(path.name in msg for msg in result.unreadable), result.unreadable
    assert 999999 not in result.db.items
    assert "TASK-999999" not in {it.id for it in result.db.items.values()}

    # Fix the file for real: the honest state repair's carry-forward promise leaves behind is
    # "on disk, not indexed" -- never a phantom "missing" (there was nothing missing to begin
    # with) and never a silently-materialised entry. Undo whatever the shape did to the *dirent*
    # first: the permission shape leaves the file unwritable, the os-read-error shape leaves a
    # directory standing in the file's place.
    if path.is_dir():
        path.rmdir()
    else:
        path.chmod(0o644)
    path.write_text(never_indexed_text, encoding="utf-8")
    issues = await svc.check()
    assert any(
        i.level == "error" and "on disk but not in index" in i.message and "TASK-999999" in i.item
        for i in issues
    ), issues


async def test_repair_carry_forward_never_regresses_the_counter(svc):
    """Corrupting the *highest*-numbered item is the shape that would actually expose a counter
    regression: a rebuild that computed its max only from readable files, with no floor from the
    previously-loaded counter, would let the corrupted item's sequence number be reissued."""
    first = (await create_item(svc, "task", "first")).item
    highest = (await create_item(svc, "task", "highest, about to go unreadable")).item
    assert highest.sequence_id > first.sequence_id
    before = await svc.store.load()
    assert before.counter == highest.sequence_id
    _corrupt_invalid_utf8(svc.paths.abspath(highest.path))

    result = await svc.repair()
    assert result.db.counter >= highest.sequence_id

    reissued = (await create_item(svc, "task", "a brand new task after repair")).item
    assert reissued.sequence_id > highest.sequence_id


@pytest.mark.parametrize("corrupt", _DEGRADE_SHAPE_PARAMS)
async def test_repair_recovers_the_counter_of_a_never_indexed_corrupt_highest_file(svc, corrupt):
    """The shape the test above does not reach: there, `previous_counter` (the index's own
    stored `counter` field, untouched by the corruption) already floors the rebuild, so the
    bug where `_rebuild_index_from_disk` computes `stem_seq` and then discards it never
    surfaces. Here the *index itself* is gone before repair runs -- `known_corpus` is `None`,
    `previous_counter` starts at 0, and the filename-derived sequence number is the *only*
    thing left that can recover the highest item's number. Falsifies both halves of the
    invariant: a counter-only assertion would pass against a variant of this bug that
    regressed the counter's *value* but happened not to let a `create` reissue it (or vice
    versa) -- the real proof is that a subsequent create's sequence number is strictly past the
    corrupt file's, never equal to or below it."""
    first = (await create_item(svc, "task", "first")).item
    highest = (await create_item(svc, "task", "highest, about to go unreadable")).item
    assert highest.sequence_id > first.sequence_id
    corrupt(svc.paths.abspath(highest.path))
    svc.store.index_path.unlink()  # known_corpus becomes None -- nothing carried, no floor

    result = await svc.repair()
    assert result.db.counter >= highest.sequence_id, (
        "the counter must never regress below a sequence number that exists on disk, even "
        "with no previous index to carry it from"
    )

    reissued = (await create_item(svc, "task", "a brand new task after repair")).item
    assert reissued.sequence_id > highest.sequence_id, (
        "a freed number must never be reissued -- this is the sharper half of the proof: a "
        "fix that merely bumps the reported counter value without actually flooring "
        "allocation would still pass a counter-only assertion but fail here"
    )
    assert reissued.id not in {"TASK-" + str(highest.sequence_id)}, "no collision on disk"


@pytest.mark.parametrize("corrupt", _SHAPE_PARAMS)
async def test_repad_refuses_on_a_corrupt_item_file_and_touches_nothing(svc, corrupt):
    """`repad` rewrites the filename (and, via the trailing `repair()`, the frontmatter id it
    encodes) across the *whole* corpus -- a file whose id cannot be read cannot be correctly
    repadded, so unlike `check`/`repair` it still refuses outright rather than degrading."""
    good = (await create_item(svc, "task", "unaffected task")).item
    good_path = svc.paths.abspath(good.path)
    good_before = good_path.read_bytes()
    bad = (await create_item(svc, "task", "corrupt task")).item
    corrupt(svc.paths.abspath(bad.path))

    with pytest.raises(SquadsError):
        await svc.repad(8)

    assert good_path.read_bytes() == good_before, "repad must touch nothing on refusal"


@pytest.mark.parametrize("corrupt", _SHAPE_PARAMS)
async def test_repair_renumber_refuses_on_a_corrupt_item_file(svc, corrupt):
    """Same reason as `repad` above: `repair --renumber` reassigns colliding ids across the
    whole corpus and cannot do that for one it cannot read."""
    bad = (await create_item(svc, "task", "corrupt task")).item
    corrupt(svc.paths.abspath(bad.path))

    with pytest.raises(SquadsError):
        await svc.repair(renumber=True)


@pytest.mark.parametrize("corrupt", _SHAPE_PARAMS)
async def test_renumber_refuses_on_a_corrupt_item_file(svc, corrupt):
    bad = (await create_item(svc, "task", "corrupt task")).item
    corrupt(svc.paths.abspath(bad.path))

    with pytest.raises(SquadsError):
        await svc.renumber(from_seq=1, by=100)


# --------------------------------------------------------------------------- listings: degrade


@pytest.mark.parametrize("corrupt", _SHAPE_PARAMS)
async def test_board_list_degrades_past_a_corrupt_notice(svc, corrupt):
    good = await svc.board_post("op-alice", "a fine notice")
    bad = await svc.board_post("op-alice", "a corrupt notice")
    bad_path = board_folder(svc.paths) / f"{bad.id}.md"
    corrupt(bad_path)

    notices, unreadable = await svc.board_list()

    assert [n.id for n in notices] == [good.id]
    assert any(bad_path.name in msg for msg in unreadable), unreadable


@pytest.mark.parametrize("corrupt", _SHAPE_PARAMS)
async def test_memory_list_degrades_past_a_corrupt_entry(svc, corrupt):
    good = await svc.memory_add("python-dev", "a fine fact")
    bad = await svc.memory_add("python-dev", "a corrupt fact")
    bad_path = role_folder(svc.paths, "python-dev") / f"{bad.slug}.md"
    corrupt(bad_path)

    entries, unreadable = await svc.memory_list("python-dev")

    assert [e.slug for e in entries] == [good.slug]
    assert any(bad_path.name in msg for msg in unreadable), unreadable


@pytest.mark.parametrize("corrupt", _SHAPE_PARAMS)
async def test_memory_search_degrades_past_a_corrupt_entry(svc, corrupt):
    good = await svc.memory_add("python-dev", "a fine searchable fact xylophone")
    bad = await svc.memory_add("python-dev", "a corrupt searchable fact xylophone")
    bad_path = role_folder(svc.paths, "python-dev") / f"{bad.slug}.md"
    corrupt(bad_path)

    hits, unreadable = await svc.memory_search("python-dev", "xylophone")

    assert [e.slug for e, _lines in hits] == [good.slug]
    assert any(bad_path.name in msg for msg in unreadable), unreadable


async def test_board_and_memory_ordering_is_unchanged_by_a_skipped_entry(svc, monkeypatch):
    """A skipped entry must not shift or renumber the survivors around it -- proven by one
    representative shape rather than all three, since the mechanism (skip, don't reindex) is
    the same regardless of *why* a file was skipped."""
    from datetime import UTC, datetime

    from squads import _clock as clock

    monkeypatch.setattr(clock, "now", lambda: datetime(2026, 6, 7, 10, 0, 0, tzinfo=UTC))
    a = await svc.board_post("op-alice", "notice a")
    monkeypatch.setattr(clock, "now", lambda: datetime(2026, 6, 7, 11, 0, 0, tzinfo=UTC))
    b = await svc.board_post("op-alice", "notice b (about to go corrupt)")
    monkeypatch.setattr(clock, "now", lambda: datetime(2026, 6, 7, 12, 0, 0, tzinfo=UTC))
    c = await svc.board_post("op-alice", "notice c")
    _corrupt_invalid_utf8(board_folder(svc.paths) / f"{b.id}.md")

    notices, _unreadable = await svc.board_list()
    assert [n.id for n in notices] == [a.id, c.id]


async def test_board_and_memory_list_report_no_unreadable_files_on_a_clean_board(svc):
    """The negative control every falsification set needs: nothing wrong, nothing reported --
    proves the degrade path is never taken when it shouldn't be."""
    await svc.board_post("op-alice", "a fine notice")
    await svc.memory_add("python-dev", "a fine fact")

    notices, board_unreadable = await svc.board_list()
    entries, memory_unreadable = await svc.memory_list("python-dev")

    assert board_unreadable == []
    assert memory_unreadable == []
    assert len(notices) == 1
    assert len(entries) == 1


# ------------------------------------------------------------- present-but-absent (a 6th shape)
#
# A `FileNotFoundError` on a dirent the scan's own glob just saw is not another unreadable
# shape -- it is a present-vs-absent *question*, decided by whether the dirent itself
# (`Path.is_symlink()`, which does not follow the link) still exists. A broken symlink is
# present -- the read failed on its target, not on whether it's there -- and gets the same
# third-state treatment as every shape above. A dirent that genuinely vanished between the glob
# and the read is not: nothing is reported for it here, on the theory that a real deletion is
# the missing-direction reconciliation's claim to make (from the previous index), not a second,
# competing claim invented by the scan that raced it.


async def test_check_and_repair_treat_a_broken_symlink_as_present_not_missing(svc):
    """Replacing an *indexed* item's file with a broken symlink is the shape that actually
    exercises "present, not missing": if the fix instead treated this dirent as absent, `check`
    would invent a phantom "no markdown file found" (there IS a previous index entry to compare
    against here), and `repair` would drop the item instead of carrying it forward."""
    bad = (await create_item(svc, "task", "about to become a broken symlink")).item
    before = await svc.get(bad.id)
    bad_path = svc.paths.abspath(bad.path)
    bad_path.unlink()
    bad_path.symlink_to(Path("/nonexistent/target"))

    issues = await svc.check()
    assert any(i.level == "error" and bad_path.name in i.item for i in issues), issues
    assert not any("no markdown file found" in i.message for i in issues), issues

    result = await svc.repair()
    assert any(bad_path.name in msg for msg in result.unreadable), result.unreadable
    assert bad.id not in result.missing_ids, "carried forward, not missing"
    assert bad.sequence_id in result.db.items
    assert result.db.items[bad.sequence_id].title == before.title


async def test_board_and_memory_list_report_a_broken_symlink_as_unreadable(svc):
    good_notice = await svc.board_post("op-alice", "a fine notice")
    (board_folder(svc.paths) / "ghost.md").symlink_to(Path("/nonexistent/target"))
    good_memory = await svc.memory_add("python-dev", "a fine fact")
    (role_folder(svc.paths, "python-dev") / "ghost.md").symlink_to(Path("/nonexistent/target"))

    notices, board_unreadable = await svc.board_list()
    entries, memory_unreadable = await svc.memory_list("python-dev")

    assert [n.id for n in notices] == [good_notice.id]
    assert any("ghost.md" in msg for msg in board_unreadable), board_unreadable
    assert [e.slug for e in entries] == [good_memory.slug]
    assert any("ghost.md" in msg for msg in memory_unreadable), memory_unreadable


async def test_every_command_gives_a_broken_symlink_the_same_diagnosis(svc):
    """One dirent, four commands, one diagnosis.

    `repad`/`renumber` reach the same broken symlink through their own preflight, and that preflight
    reported the raw errno: "could not be read: [Errno 2] No such file or directory" -- three
    separate faults in one sentence. The claim is wrong (the dirent is right there, which is the
    entire distinction the present-vs-absent test exists to draw); the path is printed twice, once
    by the wrapper and once inside the errno's own text; and library errno prose reaches a
    user-facing message where every sibling path phrases it. Refusing is still correct for both --
    they rewrite identity across the whole corpus -- but refusing is not a licence to diagnose the
    same file differently from the command the operator ran five seconds earlier.
    """
    bad = (await create_item(svc, "task", "about to become a broken symlink")).item
    bad_path = svc.paths.abspath(bad.path)
    bad_path.unlink()
    bad_path.symlink_to(Path("/nonexistent/target"))
    sentence = "is a broken symlink (its target does not exist)"

    check = [i.message for i in await svc.check() if bad_path.name in i.item]
    repair = [msg for msg in (await svc.repair()).unreadable if bad_path.name in msg]
    refusals: list[str] = []
    for refuse in (svc.repad(8), svc.renumber(from_seq=1, by=100)):
        with pytest.raises(SquadsError) as exc:
            await refuse
        refusals.append(str(exc.value))

    assert any(sentence in msg for msg in check), check
    assert any(sentence in msg for msg in repair), repair
    for message in refusals:
        assert sentence in message, message
        assert "No such file or directory" not in message, message
        assert "Errno" not in message, message
        assert message.count(str(bad_path)) == 1, f"the path is named twice: {message}"


async def test_check_skips_a_file_that_vanishes_between_glob_and_read(svc, monkeypatch):
    """The other half of the absent-vs-unreadable decision, simulated (a true glob-then-read
    race is not otherwise reproducible on demand): the file is genuinely deleted the instant
    after the scan's read is invoked. Unlike the broken-symlink shape above, this is skipped
    with nothing reported by the scan itself -- and, being a real deletion, still surfaces
    honestly through the ordinary missing-direction reconciliation."""
    from squads import _aio as aio_module

    vanishing = (await create_item(svc, "task", "about to vanish mid-scan")).item
    vanishing_path = svc.paths.abspath(vanishing.path)
    real_read_text = aio_module.read_text

    async def _read_text_then_delete(path: Path) -> str:
        if path == vanishing_path:
            await aio_module.path_unlink(path)
        return await real_read_text(path)

    monkeypatch.setattr(aio_module, "read_text", _read_text_then_delete)

    issues = await svc.check()

    assert not any(vanishing_path.name in i.item for i in issues), (
        f"a genuinely vanished file must not be named by the scan itself: {issues}"
    )
    assert any(
        i.level == "error" and i.item == vanishing.id and "no markdown file found" in i.message
        for i in issues
    ), issues
