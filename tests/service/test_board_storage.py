"""Team bulletin board storage: hash-named ``.md`` file I/O, the read-time expiry filter,
and the off-counter / outside-``.squads.json`` invariants that make it a lighter tier than
an item.
"""

from datetime import UTC, datetime

import pytest

from squads import _clock as clock
from squads._errors import SquadsError

pytestmark = pytest.mark.anyio


def _board_folder(svc):
    return svc.paths.squad_dir / "board"


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


async def test_listing_order_is_chronological_by_posted_at_not_filename(svc, monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: datetime(2026, 6, 7, 10, 0, 0, tzinfo=UTC))
    first = await svc.board_post("op-pierre", "posted first")
    monkeypatch.setattr(clock, "now", lambda: datetime(2026, 6, 7, 11, 0, 0, tzinfo=UTC))
    second = await svc.board_post("op-pierre", "posted second")
    monkeypatch.setattr(clock, "now", lambda: datetime(2026, 6, 7, 12, 0, 0, tzinfo=UTC))
    third = await svc.board_post("op-pierre", "posted third")

    listed = await svc.board_list()
    assert [n.id for n in listed] == [first.id, second.id, third.id]


async def test_expired_notices_are_excluded_from_the_live_listing(svc, monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: datetime(2026, 6, 7, 10, 0, 0, tzinfo=UTC))
    expired = await svc.board_post("op-pierre", "an old notice", until="2020-01-01")
    active = await svc.board_post("op-pierre", "a current notice")

    listed = await svc.board_list()
    assert [n.id for n in listed] == [active.id]
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


async def test_sync_on_a_board_never_posted_to_writes_no_folder(svc):
    """No ``squads/board/`` on disk yet -> sync leaves it that way, same as a role's memory
    pool that has never been added to."""
    await svc.sync()
    assert not _board_folder(svc).exists()
