"""Agent memory storage: plain slug-named ``.md`` file I/O, and the off-counter /
outside-``.squads.json`` invariants that make it a lighter tier than an item.
"""

import pytest

from squads._memory._store import MemoryNotFoundError
from squads._sections import join_frontmatter

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
    assert entry.slug == "the-scale-suite-takes-about"  # short handle, not the whole fact
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


async def test_a_long_fact_yields_a_short_slug_while_the_summary_keeps_the_full_text(svc):
    fact = "except A, B without parens is valid Python 3.14 (PEP 758), it is not a bug"
    entry = await svc.memory_add("python-dev", fact)

    assert entry.slug.count("-") < 6  # capped at a handful of words, not the whole sentence
    assert len(entry.slug) <= 40
    assert entry.summary == fact
    reread = await svc.memory_show("python-dev", entry.slug)
    assert reread.body == fact


async def test_add_with_an_explicit_slug_override_uses_it_verbatim_slugified(svc):
    entry = await svc.memory_add("python-dev", "a fact worth remembering", slug="My Handle")
    assert entry.slug == "my-handle"
    assert entry.summary == "a fact worth remembering"


async def test_two_short_slugs_that_collide_still_get_a_disambiguating_suffix(svc):
    first = await svc.memory_add("python-dev", "watch out", slug="gotcha")
    second = await svc.memory_add("python-dev", "watch out again", slug="gotcha")
    assert first.slug == "gotcha"
    assert second.slug == "gotcha-2"


async def test_a_pre_existing_long_slug_memory_still_resolves_by_its_on_disk_slug(svc):
    """Derivation only changes what a NEW add() produces; an already-committed long-slug
    ``.md`` file (the shape every memory had before this change) must still resolve
    unchanged via show/forget — nothing here renames or migrates existing files."""
    folder = _role_folder(svc, "python-dev")
    folder.mkdir(parents=True, exist_ok=True)
    long_slug = "except-a-b-without-parens-is-valid-python-3-14-pep-758-it-is"
    text = join_frontmatter(
        {"summary": "a pre-existing long-slug fact", "created_at": "2026-01-01T00:00:00Z"},
        "the body",
    )
    (folder / f"{long_slug}.md").write_text(text, encoding="utf-8")

    shown = await svc.memory_show("python-dev", long_slug)
    assert shown.summary == "a pre-existing long-slug fact"

    await svc.memory_forget("python-dev", long_slug)
    with pytest.raises(MemoryNotFoundError):
        await svc.memory_show("python-dev", long_slug)


async def test_a_repeated_fact_that_slugifies_the_same_gets_a_disambiguating_suffix(svc):
    first = await svc.memory_add("python-dev", "Watch out for xdist!!!")
    second = await svc.memory_add("python-dev", "Watch out for xdist???")
    assert first.slug == "watch-out-for-xdist"
    assert second.slug == "watch-out-for-xdist-2"
    assert await svc.memory_show("python-dev", first.slug)
    assert await svc.memory_show("python-dev", second.slug)


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
    writes to a memory ``.md`` content file or allocates/bumps the counter for memory."""
    entry = await svc.memory_add("python-dev", "repair should ignore me")
    path = _role_folder(svc, "python-dev") / f"{entry.slug}.md"
    before_text = path.read_text(encoding="utf-8")
    counter_before = (await svc.store.load()).counter

    await svc.repair()

    assert path.read_text(encoding="utf-8") == before_text
    assert (await svc.store.load()).counter == counter_before
