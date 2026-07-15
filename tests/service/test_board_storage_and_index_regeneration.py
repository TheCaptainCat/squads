"""Team bulletin board storage: file I/O + the shared ``.index.jsonl`` generator, the
read-time expiry filter, and the off-counter / outside-``.squads.json`` invariants that make
it a lighter tier than an item.
"""

import json
from datetime import UTC, datetime

import pytest

from squads import _clock as clock
from squads._content_index import INDEX_FILENAME, header_record
from squads._errors import SquadsError

pytestmark = pytest.mark.anyio


def _board_folder(svc):
    return svc.paths.squad_dir / "board"


def _parse(index_path):
    lines = index_path.read_text(encoding="utf-8").splitlines()
    return json.loads(lines[0]), [json.loads(ln) for ln in lines[1:]]


async def test_post_writes_a_hash_named_markdown_file_with_light_frontmatter_over_the_body(
    svc, frozen_time
):
    notice = await svc.board_post("op-pierre", "the CI runners are down for maintenance")

    path = _board_folder(svc) / f"{notice.id}.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "id:" not in text  # derivable from the filename stem, never stored
    assert "author: op-pierre" in text
    assert "the CI runners are down for maintenance" in text
    assert notice.posted_at == frozen_time.isoformat().replace("+00:00", "Z")
    assert notice.until is None


async def test_post_with_until_records_a_normalised_expiry(svc):
    notice = await svc.board_post("tech-lead", "freeze on the schema", until="2026-07-10")
    assert notice.until == "2026-07-10T00:00:00Z"
    text = (_board_folder(svc) / f"{notice.id}.md").read_text(encoding="utf-8")
    assert "until: '2026-07-10T00:00:00Z'" in text or "until: 2026-07-10T00:00:00Z" in text


async def test_post_rejects_an_unparseable_until_value(svc):
    with pytest.raises(SquadsError):
        await svc.board_post("tech-lead", "bad expiry", until="not-a-date")


async def test_post_rejects_empty_text(svc):
    with pytest.raises(SquadsError):
        await svc.board_post("tech-lead", "   ")


async def test_board_content_files_carry_no_sq_markers(svc):
    notice = await svc.board_post("op-pierre", "a marker-free notice")
    path = _board_folder(svc) / f"{notice.id}.md"
    assert "<!-- sq:" not in path.read_text(encoding="utf-8")


async def test_two_distinct_posts_get_distinct_hash_ids_and_independent_files(svc):
    a = await svc.board_post("op-pierre", "distinct notice alpha")
    b = await svc.board_post("op-pierre", "distinct notice beta")

    assert a.id != b.id
    a_path = _board_folder(svc) / f"{a.id}.md"
    b_path = _board_folder(svc) / f"{b.id}.md"
    assert a_path.is_file()
    assert b_path.is_file()
    assert "distinct notice alpha" in a_path.read_text(encoding="utf-8")
    assert "distinct notice beta" in b_path.read_text(encoding="utf-8")


async def test_a_repeated_post_that_hashes_the_same_gets_a_disambiguating_suffix(svc, monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: datetime(2026, 6, 7, 10, 0, 0, tzinfo=UTC))
    first = await svc.board_post("op-pierre", "double-posted notice")
    second = await svc.board_post("op-pierre", "double-posted notice")

    assert second.id == f"{first.id}-2"
    first_path = _board_folder(svc) / f"{first.id}.md"
    second_path = _board_folder(svc) / f"{second.id}.md"
    assert first_path.is_file()
    assert second_path.is_file()
    assert "double-posted notice" in first_path.read_text(encoding="utf-8")
    assert "double-posted notice" in second_path.read_text(encoding="utf-8")

    listed = await svc.board_list()
    assert {n.id for n in listed} == {first.id, second.id}


async def test_index_is_regenerated_whole_with_a_header_and_one_entry_per_notice(svc):
    a = await svc.board_post("op-pierre", "notice one")
    b = await svc.board_post("op-pierre", "notice two")

    index_path = _board_folder(svc) / INDEX_FILENAME
    lines = index_path.read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0]) == header_record()
    entry_lines = [json.loads(ln) for ln in lines[1:]]
    assert {e["slug"] for e in entry_lines} == {a.id, b.id}
    for e in entry_lines:
        assert set(e) == {"slug", "filename", "description"}
        assert e["filename"] == f"{e['slug']}.md"


async def test_index_entries_are_written_in_chronological_listing_order_not_filename_order(
    svc, monkeypatch
):
    monkeypatch.setattr(clock, "now", lambda: datetime(2026, 6, 7, 10, 0, 0, tzinfo=UTC))
    first = await svc.board_post("op-pierre", "posted first")
    monkeypatch.setattr(clock, "now", lambda: datetime(2026, 6, 7, 11, 0, 0, tzinfo=UTC))
    second = await svc.board_post("op-pierre", "posted second")
    monkeypatch.setattr(clock, "now", lambda: datetime(2026, 6, 7, 12, 0, 0, tzinfo=UTC))
    third = await svc.board_post("op-pierre", "posted third")

    index_path = _board_folder(svc) / INDEX_FILENAME
    _, entries = _parse(index_path)
    assert [e["slug"] for e in entries] == [first.id, second.id, third.id]

    listed = await svc.board_list()
    assert [n.id for n in listed] == [first.id, second.id, third.id]


async def test_expired_notices_are_excluded_from_list_and_the_index(svc, monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: datetime(2026, 6, 7, 10, 0, 0, tzinfo=UTC))
    expired = await svc.board_post("op-pierre", "an old notice", until="2020-01-01")
    active = await svc.board_post("op-pierre", "a current notice")

    listed = await svc.board_list()
    assert [n.id for n in listed] == [active.id]

    index_path = _board_folder(svc) / INDEX_FILENAME
    _, entries = _parse(index_path)
    assert [e["slug"] for e in entries] == [active.id]
    # The expired notice's file survives on disk — expiry hides, it does not delete.
    assert (_board_folder(svc) / f"{expired.id}.md").is_file()


async def test_an_empty_or_never_posted_board_lists_as_empty_not_an_error(svc):
    assert await svc.board_list() == []


async def test_listing_never_mutates_the_notice_files(svc):
    notice = await svc.board_post("op-pierre", "read-only listing check")
    path = _board_folder(svc) / f"{notice.id}.md"
    before = path.read_text(encoding="utf-8")
    before_mtime = path.stat().st_mtime_ns

    await svc.board_list()
    await svc.board_list()

    assert path.read_text(encoding="utf-8") == before
    assert path.stat().st_mtime_ns == before_mtime


async def test_clear_resolves_the_nth_listed_notice_and_deletes_its_file(svc, monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: datetime(2026, 6, 7, 10, 0, 0, tzinfo=UTC))
    a = await svc.board_post("op-pierre", "notice a")
    monkeypatch.setattr(clock, "now", lambda: datetime(2026, 6, 7, 11, 0, 0, tzinfo=UTC))
    b = await svc.board_post("op-pierre", "notice b")
    monkeypatch.setattr(clock, "now", lambda: datetime(2026, 6, 7, 12, 0, 0, tzinfo=UTC))
    c = await svc.board_post("op-pierre", "notice c")

    cleared = await svc.board_clear(2)

    assert cleared.id == b.id
    assert not (_board_folder(svc) / f"{b.id}.md").is_file()
    remaining = await svc.board_list()
    assert [n.id for n in remaining] == [a.id, c.id]


async def test_clear_regenerates_the_index_without_the_cleared_notice(svc, monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: datetime(2026, 6, 7, 10, 0, 0, tzinfo=UTC))
    a = await svc.board_post("op-pierre", "keep this one")
    monkeypatch.setattr(clock, "now", lambda: datetime(2026, 6, 7, 11, 0, 0, tzinfo=UTC))
    b = await svc.board_post("op-pierre", "clear this one")

    await svc.board_clear(2)

    index_path = _board_folder(svc) / INDEX_FILENAME
    _, entries = _parse(index_path)
    assert [e["slug"] for e in entries] == [a.id]
    assert b.id not in {e["slug"] for e in entries}


async def test_clear_with_an_out_of_range_ordinal_raises_a_clean_error(svc):
    await svc.board_post("op-pierre", "the only notice")
    with pytest.raises(SquadsError):
        await svc.board_clear(2)
    with pytest.raises(SquadsError):
        await svc.board_clear(0)


async def test_board_post_and_clear_never_allocate_a_counter_id_or_touch_squads_json(svc):
    before = await svc.store.load()
    counter_before, item_count_before = before.counter, len(before.items)

    notice = await svc.board_post("op-pierre", "off the counter")
    await svc.board_clear(1)

    after = await svc.store.load()
    assert after.counter == counter_before
    assert len(after.items) == item_count_before
    assert not (_board_folder(svc) / f"{notice.id}.md").is_file()


async def test_repair_never_touches_board_content_files_or_the_counter(svc):
    notice = await svc.board_post("op-pierre", "repair should ignore me")
    path = _board_folder(svc) / f"{notice.id}.md"
    before_text = path.read_text(encoding="utf-8")
    counter_before = (await svc.store.load()).counter

    await svc.repair()

    assert path.read_text(encoding="utf-8") == before_text
    assert (await svc.store.load()).counter == counter_before


async def test_repair_regenerates_the_board_index_from_the_md_files_when_it_goes_missing(svc):
    a = await svc.board_post("op-pierre", "notice one")
    b = await svc.board_post("op-pierre", "notice two")
    index_path = _board_folder(svc) / INDEX_FILENAME
    index_path.write_text("<<<<<<< conflict garbage\n", encoding="utf-8")

    await svc.repair()

    header, entries = _parse(index_path)
    assert header == header_record()
    assert {e["slug"] for e in entries} == {a.id, b.id}


_REAL_GIT_CONFLICT_TEMPLATE = (
    '{{"schema": "squads.index/1", "generated": "x"}}\n'
    "<<<<<<< HEAD\n"
    '{{"slug": "{a}", "filename": "{a}.md", "description": "a"}}\n'
    "=======\n"
    '{{"slug": "{b}", "filename": "{b}.md", "description": "b"}}\n'
    ">>>>>>> other-branch\n"
)


async def test_repair_regenerates_the_board_index_left_with_real_git_conflict_markers(svc):
    """The shape a real ``git merge`` leaves behind when two branches each post a distinct
    notice: the committed index conflicts (both branches rewrote it whole), while the notice
    ``.md`` files themselves merge cleanly (independent files). Repair mechanically rebuilds
    the index whole from the ``.md`` files, discarding the conflict markers."""
    a = await svc.board_post("op-pierre", "notice one")
    b = await svc.board_post("op-pierre", "notice two")
    index_path = _board_folder(svc) / INDEX_FILENAME
    index_path.write_text(_REAL_GIT_CONFLICT_TEMPLATE.format(a=a.id, b=b.id), encoding="utf-8")

    await svc.repair()

    header, entries = _parse(index_path)
    assert header == header_record()
    assert {e["slug"] for e in entries} == {a.id, b.id}


async def test_sync_regenerates_the_board_index_that_went_stale(svc):
    a = await svc.board_post("op-pierre", "notice one")
    b = await svc.board_post("op-pierre", "notice two")
    index_path = _board_folder(svc) / INDEX_FILENAME
    index_path.write_text('{"stale": "conflict"}\n', encoding="utf-8")

    await svc.sync()

    header, entries = _parse(index_path)
    assert header == header_record()
    assert {e["slug"] for e in entries} == {a.id, b.id}


async def test_sync_regenerates_the_board_index_deleted_out_from_under_it(svc):
    notice = await svc.board_post("op-pierre", "surviving notice")
    index_path = _board_folder(svc) / INDEX_FILENAME
    index_path.unlink()

    await svc.sync()

    assert index_path.is_file()
    _, entries = _parse(index_path)
    assert [e["slug"] for e in entries] == [notice.id]


async def test_sync_on_a_board_never_posted_to_writes_no_folder(svc):
    """No ``squads/board/`` on disk yet -> sync leaves it that way, same as a role's memory
    pool that has never been added to."""
    await svc.sync()
    assert not _board_folder(svc).exists()


async def test_clear_ordinal_matches_the_physical_nth_entry_line_of_the_index_file(
    svc, monkeypatch
):
    """The ordinal is documented as *the entry's line position in the generated
    ``.index.jsonl``* (header line excluded), not merely an internal listing position that
    happens to agree with it. Pin that literally: read the raw file's own line 2 (1-based
    ordinal 2, after the header) and confirm ``clear(2)`` deletes exactly that notice."""
    monkeypatch.setattr(clock, "now", lambda: datetime(2026, 6, 7, 10, 0, 0, tzinfo=UTC))
    await svc.board_post("op-pierre", "notice a")
    monkeypatch.setattr(clock, "now", lambda: datetime(2026, 6, 7, 11, 0, 0, tzinfo=UTC))
    await svc.board_post("op-pierre", "notice b")
    monkeypatch.setattr(clock, "now", lambda: datetime(2026, 6, 7, 12, 0, 0, tzinfo=UTC))
    await svc.board_post("op-pierre", "notice c")

    index_path = _board_folder(svc) / INDEX_FILENAME
    raw_lines = [ln for ln in index_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    entry_lines = raw_lines[1:]  # header excluded, entry line n == ordinal n
    assert len(entry_lines) == 3
    slug_at_ordinal_2 = json.loads(entry_lines[1])["slug"]

    cleared = await svc.board_clear(2)

    assert cleared.id == slug_at_ordinal_2


async def test_listing_does_not_touch_the_index_file(svc):
    """Listing must be as read-only towards the generated index as it is towards the notice
    ``.md`` files (see ``test_listing_never_mutates_the_notice_files`` above) — a read must
    never regenerate or otherwise rewrite a git-tracked file."""
    await svc.board_post("op-pierre", "read-only index check")
    index_path = _board_folder(svc) / INDEX_FILENAME
    before_text = index_path.read_text(encoding="utf-8")
    before_mtime = index_path.stat().st_mtime_ns

    await svc.board_list()
    await svc.board_list()

    assert index_path.read_text(encoding="utf-8") == before_text
    assert index_path.stat().st_mtime_ns == before_mtime
