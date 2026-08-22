"""``search`` and ``inbox`` walk the whole corpus, so one unreadable item file must cost that
file's contribution and nothing else.

Letting the read error propagate discarded every result already accumulated from files that
*could* be read: ``sq search`` exited 1 with empty stdout, and with ``--json`` printed nothing
at all — not even ``[]`` — so a consumer got a parse failure on top of the exit. Next to
``list``/``tree``/``blocked``/``show``/``graph``, which walk the same corpus and are unaffected,
that also made the failure look arbitrary.

This is the per-file degradation posture ``check``/``repair``/``board list``/``memory list``
already hold, extended to these two: results first and complete for every readable file, one
message per skipped file, non-zero exit so a script knows the answer was partial.

The unreadable *causes* are covered as a family (an OS refusal, invalid UTF-8, a broken
symlink, a symlink out of the squad folder), because each reaches the reader as a different
exception and only one of them was ever exercised anywhere in this suite.
"""

import json
import os
from pathlib import Path

import pytest

from _helpers import create_item, make_unreadable_by_the_os, strip_ansi
from squads._index._resolver import item_file

pytestmark = pytest.mark.anyio

_NEEDLE = "quinoa"


def _make_unreadable(path, how: str, outside: Path):
    """Break *path* the way *how* names, and return an undo callable.

    *outside* is a directory outside the squad folder, for the shapes whose whole point is that
    the item's path no longer resolves inside it.
    """
    original = path.read_bytes()

    def _restore():
        if path.is_symlink() or path.exists():
            path.unlink()
        path.write_bytes(original)

    if how == "permission":
        path.chmod(0o000)
        return lambda: path.chmod(0o644)
    if how == "os-read-error":
        return make_unreadable_by_the_os(path)
    if how == "undecodable":
        path.write_bytes(b"---\nid: X\n---\n\xff\xfe not utf-8\n")
        return lambda: path.write_bytes(original)
    if how == "broken-symlink":
        path.unlink()
        path.symlink_to(path.parent / "nowhere-at-all.md")
        return _restore
    if how == "symlink-outside-squad":
        target = outside / "moved.md"
        target.write_bytes(original)
        path.unlink()
        path.symlink_to(target)
        return _restore
    if how == "broken-symlink-outside-squad":
        path.unlink()
        path.symlink_to(outside / "never-existed.md")
        return _restore
    raise AssertionError(how)


#: The unreadable-cause family. The last three are *path-resolution* failures rather than read
#: failures: ``SquadPaths.abspath`` resolves symlinks and refuses anything landing outside the
#: squad folder, so the item's path cannot even be produced. That call used to sit outside the
#: guard — evaluated as the argument that produced the path — so it aborted the whole walk
#: exactly the way an unguarded read would, on shapes the guard was believed to cover. Only the
#: *inside*-the-squad broken symlink was originally exercised, which is how a family that looked
#: covered by name was not covered by shape.
_CAUSES = [
    # POSIX-only instrument: `os.chmod` on Windows can only toggle the read-only attribute and
    # cannot withdraw read access, so this leaves the file readable and nothing degrades there.
    # `os-read-error` below stages the same OS-level read refusal on every platform, so the arm
    # of the guard this cause reaches stays covered where chmod cannot express it.
    pytest.param(
        "permission",
        marks=pytest.mark.skipif(
            os.name != "posix",
            reason="chmod(0o000) cannot withdraw read access on Windows -- the OS-level read "
            "refusal this cause stages is carried there by the os-read-error cause instead",
        ),
    ),
    "os-read-error",
    "undecodable",
    "broken-symlink",
    "symlink-outside-squad",
    "broken-symlink-outside-squad",
]

#: Causes whose message names the item id rather than a path — there is no trustworthy path to
#: name when path resolution is what failed.
_ID_NAMED_CAUSES = frozenset({"symlink-outside-squad", "broken-symlink-outside-squad"})


@pytest.fixture
def outside(tmp_path):
    """A directory that is deliberately *not* under the squad folder."""
    d = tmp_path.parent / "outside-the-squad"
    d.mkdir(exist_ok=True)
    return d


def _flat(text: str) -> str:
    """Strip ANSI so a colour code inserted mid-phrase is never mistaken for a miss."""
    return strip_ansi(text)


async def _two_items(svc):
    """One readable item carrying the needle and a mention, and one to break."""
    good = (await create_item(svc, "task", "readable")).item
    await svc.set_body(good.id, f"the {_NEEDLE} line, and @manager is called out")
    bad = (await create_item(svc, "task", "unreadable")).item
    await svc.set_body(bad.id, f"also {_NEEDLE}, also @manager")
    return good, bad


def _names_the_victim(message: str, bad, path_name: str, cause: str) -> bool:
    """A skipped-file message has to identify *which* item was skipped — by path where there
    is a trustworthy one, and by item id where path resolution is the thing that failed."""
    return bad.id in message if cause in _ID_NAMED_CAUSES else path_name in message


@pytest.mark.parametrize("cause", _CAUSES)
async def test_search_keeps_the_readable_results_and_names_the_skipped_file(svc, outside, cause):
    good, bad = await _two_items(svc)
    path_name = item_file(svc.paths, bad).name
    undo = _make_unreadable(item_file(svc.paths, bad), cause, outside)
    try:
        results, unreadable = await svc.search(_NEEDLE)
    finally:
        undo()

    assert [r.item.id for r in results] == [good.id]
    assert len(unreadable) == 1
    assert _names_the_victim(unreadable[0], bad, path_name, cause), unreadable


@pytest.mark.parametrize("cause", _CAUSES)
async def test_inbox_keeps_the_readable_hits_and_names_the_skipped_file(svc, outside, cause):
    good, bad = await _two_items(svc)
    path_name = item_file(svc.paths, bad).name
    undo = _make_unreadable(item_file(svc.paths, bad), cause, outside)
    try:
        hits, unreadable = await svc.inbox("manager")
    finally:
        undo()

    assert [h.item.id for h in hits] == [good.id]
    assert len(unreadable) == 1
    assert _names_the_victim(unreadable[0], bad, path_name, cause), unreadable


@pytest.mark.parametrize("command", ["search", "inbox"])
async def test_a_traversal_path_in_the_index_degrades_per_item(svc, command):
    """The same abort with no symlink anywhere: an index whose stored `path` escapes the squad
    folder, which is the shape the traversal guard exists for and is reachable from a tampered
    or badly-imported index. It reaches the walk through the *path helper*, not the read, which
    is why guarding only the read left it open.
    """
    good, bad = await _two_items(svc)
    async with svc.store.transaction() as db:
        db.get(bad.id).path = "../outside/TASK-000099-traversal-victim.md"

    if command == "search":
        found, unreadable = await svc.search(_NEEDLE)
    else:
        found, unreadable = await svc.inbox("manager")

    assert [r.item.id for r in found] == [good.id]
    assert len(unreadable) == 1
    assert bad.id in unreadable[0] and "escapes the squad folder" in unreadable[0]


async def test_an_unreadable_item_still_contributes_what_the_index_knows(svc, outside):
    """A title match needs no file read, so an unreadable item is dropped only as far as it
    has to be — the degradation is per *source*, not per item."""
    bad = (await create_item(svc, "task", f"a {_NEEDLE} in the title")).item
    undo = _make_unreadable(item_file(svc.paths, bad), "os-read-error", outside)
    try:
        results, unreadable = await svc.search(_NEEDLE)
    finally:
        undo()

    assert [r.item.id for r in results] == [bad.id]
    assert [h.region for h in results[0].hits] == ["title"]
    assert len(unreadable) == 1


async def test_a_healthy_corpus_reports_nothing_skipped(svc):
    """The channel must stay silent on the normal path, or the non-zero exit it drives would
    fire on every clean run."""
    await _two_items(svc)
    results, unreadable = await svc.search(_NEEDLE)
    hits, inbox_unreadable = await svc.inbox("manager")
    assert len(results) == 2
    assert len(hits) == 2
    assert unreadable == []
    assert inbox_unreadable == []


async def test_an_item_whose_file_is_simply_missing_is_not_reported_as_unreadable(svc):
    """Absent is repair's report to make, not this one's — a deleted file would otherwise be
    named on every search until someone repaired the index."""
    good, bad = await _two_items(svc)
    item_file(svc.paths, bad).unlink()

    results, unreadable = await svc.search(_NEEDLE)
    assert [r.item.id for r in results] == [good.id]
    assert unreadable == []


# ─── CLI contract ──────────────────────────────────────────────────────────────


async def test_cli_search_prints_the_results_on_stdout_and_the_error_on_stderr(
    svc, invoke, outside
):
    """The streams captured separately, not combined: a combined-output grep would pass on
    the defect this guards against (the human-mode error printed to stdout instead of
    stderr) -- checked here on the two streams typer's ``CliRunner`` keeps genuinely apart."""
    good, bad = await _two_items(svc)
    undo = _make_unreadable(item_file(svc.paths, bad), "os-read-error", outside)
    try:
        result = await invoke(["search", _NEEDLE])
    finally:
        undo()

    assert result.exit_code == 1
    out = _flat(result.stdout)
    err = _flat(result.stderr)
    assert good.id in out  # the answer is still delivered
    assert "could not be read" not in out
    assert "could not be read" in err


async def test_cli_inbox_prints_the_hits_on_stdout_and_the_error_on_stderr(svc, invoke, outside):
    """Same stream contract as search above, for `inbox`'s identical degrade path."""
    good, bad = await _two_items(svc)
    undo = _make_unreadable(item_file(svc.paths, bad), "os-read-error", outside)
    try:
        result = await invoke(["inbox", "manager"])
    finally:
        undo()

    assert result.exit_code == 1
    out = _flat(result.stdout)
    err = _flat(result.stderr)
    assert good.id in out
    assert "could not be read" not in out
    assert "could not be read" in err


async def test_cli_search_json_stays_a_parseable_array_with_the_error_on_stderr(
    svc, invoke, outside
):
    """The shape a machine consumer depends on: valid JSON on stdout even when degraded, the
    skipped files out-of-band on stderr, and the exit code carrying the 'partial' signal."""
    good, bad = await _two_items(svc)
    undo = _make_unreadable(item_file(svc.paths, bad), "os-read-error", outside)
    try:
        result = await invoke(["search", _NEEDLE, "--json"])
    finally:
        undo()

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert [r["id"] for r in payload] == [good.id]
    assert "could not be read" in _flat(result.stderr)


async def test_cli_inbox_json_stays_a_parseable_array_with_the_error_on_stderr(
    svc, invoke, outside
):
    good, bad = await _two_items(svc)
    undo = _make_unreadable(item_file(svc.paths, bad), "os-read-error", outside)
    try:
        result = await invoke(["inbox", "manager", "--json"])
    finally:
        undo()

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert [r["id"] for r in payload] == [good.id]
    assert "could not be read" in _flat(result.stderr)


async def test_cli_search_and_inbox_exit_zero_on_a_healthy_corpus(svc, invoke):
    await _two_items(svc)
    assert (await invoke(["search", _NEEDLE])).exit_code == 0
    assert (await invoke(["search", _NEEDLE, "--json"])).exit_code == 0
    assert (await invoke(["inbox", "manager"])).exit_code == 0
    assert (await invoke(["inbox", "manager", "--json"])).exit_code == 0


async def test_cli_search_with_no_matches_at_all_still_exits_zero(svc, invoke):
    """An empty answer is a real answer — only an unreadable file degrades the exit code."""
    await _two_items(svc)
    result = await invoke(["search", "nothing-matches-this"])
    assert result.exit_code == 0
    assert "no matches" in strip_ansi(result.stdout)


@pytest.mark.parametrize(
    ("command", "confident"),
    [(["search", "no-such-text-anywhere"], "no matches for"), (["inbox", "qa"], "nothing for @")],
    ids=["search", "inbox"],
)
async def test_cli_never_claims_an_empty_result_it_could_not_verify(
    svc, invoke, outside, command, confident
):
    """ "no matches" is a claim about the corpus, and on a degraded read the command has not
    seen the whole corpus. The skipped files are named either way, but the headline is what a
    reader acts on, and a confident negative is the one shape that stops them looking."""
    _good, bad = await _two_items(svc)
    # `inbox` validates its slug against the roster; qa is mentioned nowhere, which is the
    # genuinely-empty case this test needs on the readable side.
    await svc.activate_role("qa")

    # A genuinely empty result on a fully-read corpus still says so plainly.
    clean = strip_ansi((await invoke(command)).stdout)
    assert confident in clean
    assert "in what could be read" not in clean

    undo = _make_unreadable(item_file(svc.paths, bad), "os-read-error", outside)
    try:
        degraded = strip_ansi((await invoke(command)).stdout)
    finally:
        undo()

    assert "in what could be read" in degraded
    assert "skipped, listed below" in degraded
