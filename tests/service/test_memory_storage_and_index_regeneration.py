"""Agent memory storage: file I/O + the shared ``.index.jsonl`` generator, and the
off-counter / outside-``.squads.json`` invariants that make it a lighter tier than an item.
"""

import json

import pytest

from squads._content_index import INDEX_FILENAME, header_record
from squads._memory import _store as memory_store
from squads._memory._store import MemoryNotFoundError

pytestmark = pytest.mark.anyio


def _role_folder(svc, role_slug):
    return svc.paths.squad_dir / "agents" / "memory" / role_slug


async def test_add_writes_a_slug_named_markdown_file_with_light_frontmatter_over_the_body(
    svc, frozen_time
):
    entry = await svc.memory_add("python-dev", "the scale suite takes about 4 minutes")

    path = _role_folder(svc, "python-dev") / f"{entry.slug}.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "summary: the scale suite takes about 4 minutes" in text
    assert "the scale suite takes about 4 minutes" in text  # body defaults to the fact
    assert entry.slug == "the-scale-suite-takes-about-4-minutes"
    assert entry.created_at == frozen_time.isoformat().replace("+00:00", "Z")


async def test_add_with_file_body_and_tags_persists_both(svc):
    entry = await svc.memory_add(
        "python-dev",
        "pyright runs in strict mode",
        body="Longer freeform notes about strict mode gotchas.",
        tags=["typing", "gotcha"],
    )
    assert entry.body == "Longer freeform notes about strict mode gotchas."
    assert entry.tags == ("typing", "gotcha")

    reread = await svc.memory_show("python-dev", entry.slug)
    assert reread.body == entry.body
    assert reread.tags == entry.tags
    assert reread.summary == "pyright runs in strict mode"


async def test_memory_content_files_carry_no_sq_markers(svc):
    entry = await svc.memory_add("python-dev", "a marker-free fact")
    path = _role_folder(svc, "python-dev") / f"{entry.slug}.md"
    assert "<!-- sq:" not in path.read_text(encoding="utf-8")


async def test_a_repeated_fact_that_slugifies_the_same_gets_a_disambiguating_suffix(svc):
    first = await svc.memory_add("python-dev", "Watch out for xdist!!!")
    second = await svc.memory_add("python-dev", "Watch out for xdist???")
    assert first.slug == "watch-out-for-xdist"
    assert second.slug == "watch-out-for-xdist-2"
    assert await svc.memory_show("python-dev", first.slug)
    assert await svc.memory_show("python-dev", second.slug)


async def test_index_is_regenerated_whole_with_a_header_and_one_entry_per_memory(svc):
    a = await svc.memory_add("python-dev", "fact one")
    b = await svc.memory_add("python-dev", "fact two")

    index_path = _role_folder(svc, "python-dev") / INDEX_FILENAME
    lines = index_path.read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0]) == header_record()
    entry_lines = [json.loads(ln) for ln in lines[1:]]
    assert {e["slug"] for e in entry_lines} == {a.slug, b.slug}
    for e in entry_lines:
        assert set(e) == {"slug", "filename", "description"}
        assert e["filename"] == f"{e['slug']}.md"


async def test_index_is_regenerated_whole_after_forget_not_merely_appended(svc):
    a = await svc.memory_add("python-dev", "keep this one")
    b = await svc.memory_add("python-dev", "forget this one")
    await svc.memory_forget("python-dev", b.slug)

    index_path = _role_folder(svc, "python-dev") / INDEX_FILENAME
    _, entries = _parse(index_path)
    assert [e["slug"] for e in entries] == [a.slug]


def _parse(index_path):
    lines = index_path.read_text(encoding="utf-8").splitlines()
    return json.loads(lines[0]), [json.loads(ln) for ln in lines[1:]]


async def test_forget_deletes_the_memory_file_for_real(svc):
    entry = await svc.memory_add("python-dev", "a stale fact")
    path = _role_folder(svc, "python-dev") / f"{entry.slug}.md"
    assert path.is_file()

    await svc.memory_forget("python-dev", entry.slug)

    assert not path.exists()


async def test_forgetting_an_unknown_slug_raises_a_clean_error(svc):
    with pytest.raises(MemoryNotFoundError):
        await svc.memory_forget("python-dev", "never-existed")


async def test_reading_an_unknown_slug_raises_a_clean_error_without_mutating_anything(svc):
    with pytest.raises(MemoryNotFoundError):
        await svc.memory_show("python-dev", "never-existed")
    assert not _role_folder(svc, "python-dev").exists()


async def test_an_empty_or_never_used_role_pool_lists_as_empty_not_an_error(svc):
    assert await svc.memory_list("some-role-with-no-memories-yet") == []


async def test_two_roles_get_independent_memory_pools(svc):
    await svc.memory_add("python-dev", "python fact")
    await svc.memory_add("dotnet-dev", "dotnet fact")

    assert [e.summary for e in await svc.memory_list("python-dev")] == ["python fact"]
    assert [e.summary for e in await svc.memory_list("dotnet-dev")] == ["dotnet fact"]


async def test_memory_add_and_forget_never_allocate_a_counter_id_or_touch_squads_json(svc):
    before = await svc.store.load()
    counter_before, item_count_before = before.counter, len(before.items)

    entry = await svc.memory_add("python-dev", "off the counter")
    await svc.memory_forget("python-dev", entry.slug)

    after = await svc.store.load()
    assert after.counter == counter_before
    assert len(after.items) == item_count_before


async def test_repair_never_touches_memory_content_files_or_the_counter(svc):
    """Repair rebuilds the counter-backed item index from item frontmatter only — it never
    writes to a memory ``.md`` content file or allocates/bumps the counter for memory. It does
    (separately, see the regeneration tests below) regenerate each role's ``.index.jsonl``."""
    entry = await svc.memory_add("python-dev", "repair should ignore me")
    path = _role_folder(svc, "python-dev") / f"{entry.slug}.md"
    before_text = path.read_text(encoding="utf-8")
    counter_before = (await svc.store.load()).counter

    await svc.repair()

    assert path.read_text(encoding="utf-8") == before_text
    assert (await svc.store.load()).counter == counter_before


async def test_repair_regenerates_a_roles_index_from_the_md_files_when_it_goes_missing(svc):
    """A merge-conflicted or hand-corrupted committed index has a one-command mechanical fix:
    re-run repair (or sync) and it is rebuilt whole from the .md files, discarding whatever
    conflict markers or stale content was there before."""
    a = await svc.memory_add("python-dev", "fact one")
    b = await svc.memory_add("python-dev", "fact two")
    index_path = _role_folder(svc, "python-dev") / INDEX_FILENAME
    index_path.write_text("<<<<<<< conflict garbage\n", encoding="utf-8")

    await svc.repair()

    header, entries = _parse(index_path)
    assert header == header_record()
    assert {e["slug"] for e in entries} == {a.slug, b.slug}


_REAL_GIT_CONFLICT_TEMPLATE = (
    '{{"schema": "squads.index/1", "generated": "x"}}\n'
    "<<<<<<< HEAD\n"
    '{{"slug": "{a}", "filename": "{a}.md", "description": "a"}}\n'
    "=======\n"
    '{{"slug": "{b}", "filename": "{b}.md", "description": "b"}}\n'
    ">>>>>>> other-branch\n"
)


async def test_repair_regenerates_a_roles_index_left_with_real_git_conflict_markers(svc):
    """The shape a real `git merge` actually leaves behind — multiple lines, some of them
    literal `<<<<<<<`/`=======`/`>>>>>>>` markers rather than parseable JSON — not just an
    arbitrary single corrupted line. Repair discards it and rebuilds whole from the .md files,
    same as the simpler corruption case above."""
    a = await svc.memory_add("python-dev", "fact one")
    b = await svc.memory_add("python-dev", "fact two")
    index_path = _role_folder(svc, "python-dev") / INDEX_FILENAME
    index_path.write_text(_REAL_GIT_CONFLICT_TEMPLATE.format(a=a.slug, b=b.slug), encoding="utf-8")

    await svc.repair()

    header, entries = _parse(index_path)
    assert header == header_record()
    assert {e["slug"] for e in entries} == {a.slug, b.slug}


async def test_sync_resolves_a_roles_index_left_with_real_git_conflict_markers(svc):
    """The acceptance criterion is 'sq sync/repair mechanically regenerates the index' — both
    commands, not just repair. Currently only repair honours it for a genuinely
    conflict-marked index; sync should too."""
    a = await svc.memory_add("manager", "fact one")
    b = await svc.memory_add("manager", "fact two")
    index_path = _role_folder(svc, "manager") / INDEX_FILENAME
    index_path.write_text(_REAL_GIT_CONFLICT_TEMPLATE.format(a=a.slug, b=b.slug), encoding="utf-8")

    await svc.sync()

    header, entries = _parse(index_path)
    assert header == header_record()
    assert {e["slug"] for e in entries} == {a.slug, b.slug}


async def test_read_index_and_memory_list_survive_a_conflict_marked_index_untouched(svc):
    """Defensive-read guard: a genuinely git-conflict-marked ``.index.jsonl`` — no ``sync``/
    ``repair`` run yet — must never crash a reader. ``read_index`` degrades to an empty list
    (the same as an absent index) instead of propagating ``JSONDecodeError``, and ``sq memory
    list`` (which reads the ``.md`` files directly, not the index) is completely unaffected."""
    a = await svc.memory_add("manager", "fact one")
    b = await svc.memory_add("manager", "fact two")
    index_path = _role_folder(svc, "manager") / INDEX_FILENAME
    index_path.write_text(_REAL_GIT_CONFLICT_TEMPLATE.format(a=a.slug, b=b.slug), encoding="utf-8")

    entries = await memory_store.read_index(svc.paths, "manager")
    assert entries == []

    listed = await svc.memory_list("manager")
    assert {e.slug for e in listed} == {a.slug, b.slug}


async def test_repair_regenerates_a_roles_index_deleted_out_from_under_it(svc):
    entry = await svc.memory_add("python-dev", "surviving fact")
    index_path = _role_folder(svc, "python-dev") / INDEX_FILENAME
    index_path.unlink()

    await svc.repair()

    assert index_path.is_file()
    _, entries = _parse(index_path)
    assert [e["slug"] for e in entries] == [entry.slug]


async def test_sync_regenerates_a_roles_index_that_went_stale(svc):
    """sq sync's "regenerate every tool-owned managed file" pass covers the memory index too —
    a stale/conflicted committed index is rebuilt whole from the .md files on sync, the same
    way repair does."""
    a = await svc.memory_add("python-dev", "fact one")
    b = await svc.memory_add("python-dev", "fact two")
    index_path = _role_folder(svc, "python-dev") / INDEX_FILENAME
    index_path.write_text('{"stale": "conflict"}\n', encoding="utf-8")

    await svc.sync()

    header, entries = _parse(index_path)
    assert header == header_record()
    assert {e["slug"] for e in entries} == {a.slug, b.slug}


async def test_sync_regenerates_a_roles_index_deleted_out_from_under_it(svc):
    entry = await svc.memory_add("python-dev", "surviving fact")
    index_path = _role_folder(svc, "python-dev") / INDEX_FILENAME
    index_path.unlink()

    await svc.sync()

    assert index_path.is_file()
    _, entries = _parse(index_path)
    assert [e["slug"] for e in entries] == [entry.slug]


async def test_sync_regenerates_every_roles_memory_folder_in_one_pass(svc):
    """The regeneration pass is generic over every memory folder on disk, not a single
    hard-coded role."""
    py = await svc.memory_add("python-dev", "python fact")
    net = await svc.memory_add("dotnet-dev", "dotnet fact")
    for role in ("python-dev", "dotnet-dev"):
        (_role_folder(svc, role) / INDEX_FILENAME).unlink()

    await svc.sync()

    _, py_entries = _parse(_role_folder(svc, "python-dev") / INDEX_FILENAME)
    _, net_entries = _parse(_role_folder(svc, "dotnet-dev") / INDEX_FILENAME)
    assert [e["slug"] for e in py_entries] == [py.slug]
    assert [e["slug"] for e in net_entries] == [net.slug]


async def test_sync_regenerates_a_memory_folder_with_no_matching_role_item(svc):
    """Memory pools are addressed by a bare role-slug string, off the role roster entirely —
    sync must discover and regenerate a folder's index even for a slug with no corresponding
    role item, not only for slugs already in the roster."""
    entry = await svc.memory_add("a-role-with-no-item", "an orphaned fact")
    index_path = _role_folder(svc, "a-role-with-no-item") / INDEX_FILENAME
    index_path.unlink()

    await svc.sync()

    assert index_path.is_file()
    _, entries = _parse(index_path)
    assert [e["slug"] for e in entries] == [entry.slug]
