"""Agent memory storage: file I/O + the shared ``.index.jsonl`` generator, and the
off-counter / outside-``.squads.json`` invariants that make it a lighter tier than an item.
"""

import json

import pytest

from squads._content_index import INDEX_FILENAME, header_record
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


async def test_repair_neither_rebuilds_nor_disturbs_memory_files(svc):
    entry = await svc.memory_add("python-dev", "repair should ignore me")
    path = _role_folder(svc, "python-dev") / f"{entry.slug}.md"
    before_text = path.read_text(encoding="utf-8")
    index_before = (_role_folder(svc, "python-dev") / INDEX_FILENAME).read_text(encoding="utf-8")
    counter_before = (await svc.store.load()).counter

    await svc.repair()

    assert path.read_text(encoding="utf-8") == before_text
    assert (_role_folder(svc, "python-dev") / INDEX_FILENAME).read_text(
        encoding="utf-8"
    ) == index_before
    assert (await svc.store.load()).counter == counter_before
