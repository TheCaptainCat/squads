"""``Service.repair()``'s corpus sweep strips a frozen list of retired marker regions and the
stored role mirror, but — far more of this module — leaves everything else untouched: a
skill's stored body, authored sub-entity content, and a role's own legacy prose region."""

from typing import cast

import pytest

from _helpers import create_item
from squads._index._resolver import item_file
from squads._interactions import SYSTEM_SKILL_VIEW_NAMES, is_system_skill
from squads._itemfile import read_frontmatter
from squads._models import _markers as markers
from squads._models._extras import ExtraKey as X
from squads._models._metadata import RETIRED_ROLE_EXTRA_KEYS
from squads._sections import get_section, has_section, replace_frontmatter, replace_section
from squads._services import _service as service
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

#: A summary region in the shape the retired writer produced, blank separator line included.
_SUMMARY_REGION = """<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | First |  |
<!-- sq:summary:end -->

"""


#: The mirror shape a past release stored on every role item, written back here since nothing
#: produces it any more.
_RETIRED_MIRROR: dict[str, object] = {
    X.FULL_NAME: "Stored Name",
    X.TITLE: "Stored title",
    X.MISSION: "A stored mission.",
    X.RESPONSIBILITIES: ["Stored responsibility"],
    X.AGREEMENTS: ["Stored agreement"],
    X.COLOR: "blue",
    X.CAN_SPAWN: True,
    X.DESCRIPTION: "A stored description.",
    X.MODEL: "opus",
    "skills": ["squads", "sq-task"],
}

#: The names the sweep takes off a role item.
_RETIRED_MIRROR_KEYS: frozenset[str] = RETIRED_ROLE_EXTRA_KEYS | {X.MODEL}


def _stored_extra(path) -> dict[str, object]:
    """The ``extra`` mapping the file itself carries, read from the frontmatter, never the index."""
    return read_frontmatter(text=path.read_text(encoding="utf-8"), source=str(path)).get(
        "extra", {}
    )


async def _role_carrying_the_retired_shape(svc, slug: str):
    """The role item for *slug*, with the retired mirror written into its ``extra`` and a
    definition written into its ``sq:body`` region, straight onto the file."""
    item = await svc.roster_item("role", slug)
    assert item is not None
    path = item_file(svc.paths, item)
    text = path.read_text(encoding="utf-8")
    data = read_frontmatter(text=text, source=str(path))
    extra = cast("dict[str, object]", data.get("extra") or {})
    data["extra"] = {**_RETIRED_MIRROR, **extra}
    text = replace_frontmatter(text, data, source=str(path))
    text = replace_section(text, markers.BODY, "# Stored Name\n\nA stored definition.")
    path.write_text(text, encoding="utf-8")
    return item, path


def _head_region(tag: str) -> str:
    """A badge region in the shape the retired writer produced, for the region tag *tag*."""
    return f"""<!-- sq:{tag}:head -->
**Status:** ⚪ Todo
<!-- sq:{tag}:head:end -->

"""


async def _task_carrying_both_families(svc):
    """A task item whose file carries a summary region and two subtask badge regions, straight
    onto the file, since no live write path produces either any more."""
    task = (await create_item(svc, "task", "Carries the retired regions")).item
    await svc.add_subtask(task.id, "First")
    await svc.add_subtask(task.id, "Second")
    path = item_file(svc.paths, task)
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        markers.open_marker(markers.SUBTASKS),
        _SUMMARY_REGION + markers.open_marker(markers.SUBTASKS),
        1,
    )
    for local_id in ("ST1", "ST2"):
        tag = markers.subtask_tag(local_id)
        text = text.replace(
            markers.open_marker(f"{tag}:body"),
            _head_region(tag) + markers.open_marker(f"{tag}:body"),
            1,
        )
    path.write_text(text, encoding="utf-8")
    return task, path


# --------------------------------------------------------------- what the sweep removes


async def test_repair_strips_both_retired_region_families(svc):
    task, path = await _task_carrying_both_families(svc)
    before = path.read_text(encoding="utf-8")
    assert has_section(before, markers.SUMMARY)
    assert has_section(before, "subtask:ST1:head")
    assert has_section(before, "subtask:ST2:head")

    result = await svc.repair()

    after = path.read_text(encoding="utf-8")
    assert not has_section(after, markers.SUMMARY)
    assert not has_section(after, "subtask:ST1:head")
    assert not has_section(after, "subtask:ST2:head")
    assert task.id in result.stripped


async def test_a_stripped_file_matches_what_the_live_write_path_writes_today(svc):
    """A stripped file matches, byte for byte, what the live write path writes today, catching
    any doubled blank line the strip could leave behind."""
    carrying, carrying_path = await _task_carrying_both_families(svc)
    clean = (await create_item(svc, "task", "Carries the retired regions")).item
    await svc.add_subtask(clean.id, "First")
    await svc.add_subtask(clean.id, "Second")
    clean_path = item_file(svc.paths, clean)

    await svc.repair()

    def _subtasks_section(text: str) -> str:
        start = text.index(markers.open_marker(markers.SUBTASKS))
        return text[start : text.index(markers.close_marker(markers.SUBTASKS))]

    stripped = _subtasks_section(carrying_path.read_text(encoding="utf-8"))
    never_carried = _subtasks_section(clean_path.read_text(encoding="utf-8"))
    assert stripped.replace(carrying.id, clean.id) == never_carried.replace(carrying.id, clean.id)


async def test_a_head_region_of_an_adopter_declared_kind_is_stripped_too(svc):
    """A badge region belonging to an adopter-declared sub-entity kind is stripped too."""
    task = (await create_item(svc, "task", "Carries a foreign kind")).item
    path = item_file(svc.paths, task)
    text = path.read_text(encoding="utf-8")
    block = (
        "\n<!-- sq:risk:RK1 -->\n### RK1 — Declared by an adopter\n\n"
        + _head_region("risk:RK1")
        + "<!-- sq:risk:RK1:body -->\nadopter-authored prose\n<!-- sq:risk:RK1:body:end -->\n"
        "<!-- sq:risk:RK1:end -->\n"
    )
    text = text.replace(
        markers.close_marker(markers.SUBTASKS), block + markers.close_marker(markers.SUBTASKS), 1
    )
    path.write_text(text, encoding="utf-8")

    await svc.repair()

    after = path.read_text(encoding="utf-8")
    assert not has_section(after, "risk:RK1:head")
    assert get_section(after, "risk:RK1:body") == "\nadopter-authored prose\n"


async def test_a_system_skill_body_survives_the_sweep(svc):
    """A template-owned skill's stored body is left exactly where it is, since nothing on the
    item proves it was never authored."""
    await svc.seed_bundled_skills()
    item = await svc.roster_item("skill", "sq-task")
    assert item is not None
    path = item_file(svc.paths, item)
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            f"{markers.open_marker(markers.BODY)}\n{markers.close_marker(markers.BODY)}",
            f"{markers.open_marker(markers.BODY)}\n# a stale stored rendering\n"
            f"{markers.close_marker(markers.BODY)}",
        ),
        encoding="utf-8",
    )
    before = path.read_bytes()
    assert (get_section(before.decode("utf-8"), markers.BODY) or "").strip()

    result = await svc.repair()

    assert path.read_bytes() == before
    assert item.id not in result.stripped


async def test_declaring_an_item_type_does_not_delete_an_authored_skill_of_that_name(svc, tmp_path):
    """Declaring an item type that makes an already-authored ``sq-<slug>`` skill read as
    template-owned from that moment on does not delete its stored body."""
    await svc.seed_bundled_skills()
    item = await svc.add_skill("sq-onboarding", description="An authored runbook")
    await svc.set_body(item.id, "AUTHORED CONTENT — this body is storage, not a rendering.")
    path = item_file(svc.paths, item)
    before = path.read_bytes()

    override_dir = svc.paths.squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        "[lifecycles.onboarding]\n"
        'initial = "Open"\n'
        "[lifecycles.onboarding.transitions]\n"
        'Open = ["Done"]\n'
        "Done = []\n"
        "\n"
        "[items.onboarding]\n"
        'prefix = "ONB"\n'
        'folder = "onboardings"\n'
        'lifecycle = "onboarding"\n',
        encoding="utf-8",
    )
    spec = load_workflow_spec(squad_dir=svc.paths.squad_dir)
    assert is_system_skill("sq-onboarding", spec)
    declared = service.Service(svc.paths, spec=spec)

    await declared.repair()

    assert path.read_bytes() == before


# ------------------------------------------------------- what the sweep must not touch


@pytest.mark.parametrize("slug", ["house-style", "sq-onboarding"])
async def test_a_custom_skill_body_survives_byte_identical(svc, slug: str):
    """A custom skill's body, including one with an ``sq-`` prefix, survives byte identical."""
    await svc.seed_bundled_skills()
    item = await svc.add_skill(slug, description="An authored runbook")
    await svc.set_body(item.id, "AUTHORED CONTENT — this body is storage, not a rendering.")
    path = item_file(svc.paths, item)
    before = path.read_bytes()

    await svc.repair()

    assert path.read_bytes() == before


async def test_a_role_bodys_extra_keys_strip_leaves_a_legacy_prose_region_untouched(svc):
    """A role's legacy, pre-tag stored definition is left byte-for-byte unchanged, while its
    retired ``extra`` mirror keys still strip."""
    item, path = await _role_carrying_the_retired_shape(svc, "manager")
    before_region = (get_section(path.read_text(encoding="utf-8"), markers.BODY) or "").strip()
    assert before_region

    result = await svc.repair()

    text = path.read_text(encoding="utf-8")
    assert has_section(text, markers.BODY), "the body markers were deleted"
    region = (get_section(text, markers.BODY) or "").strip()
    assert region == before_region, "the legacy body was rewritten, not left alone"
    assert item.id in result.stripped


@pytest.mark.parametrize("is_dev", [False, True], ids=["bundled", "developer"])
async def test_a_role_keeps_exactly_the_extra_keys_a_writer_still_produces(svc, is_dev: bool):
    """A role keeps exactly the extra keys a live writer still produces, for both a bundled
    role (``model`` is mirror residue) and a developer (``model`` is a live operator setting)."""
    role = (
        await svc.add_dev("rust", name="Rusty Dev", model="opus")
        if is_dev
        else await svc.activate_role("architect")
    )
    await svc.set_default_role(role.id)
    slug = role.extra[X.SLUG]
    _item, path = await _role_carrying_the_retired_shape(svc, slug)
    stored = _stored_extra(path)
    assert set(stored) >= _RETIRED_MIRROR_KEYS
    assert stored[X.MODEL] == "opus"

    await svc.repair()

    retained: dict[str, object] = {X.SLUG: slug, X.IS_DEFAULT: True}
    if is_dev:
        retained |= {X.MODEL: "opus", X.IS_DEV: True, X.TECH: "rust"}
    assert _stored_extra(path) == retained
    assert (X.MODEL in _stored_extra(path)) is is_dev


async def test_the_index_loses_the_same_role_keys_the_file_does(svc):
    """The file and the index agree on exactly the role keys just removed."""
    item, path = await _role_carrying_the_retired_shape(svc, "manager")

    await svc.repair()

    indexed = (await svc.store.load()).items[item.sequence_id]
    assert indexed.extra == _stored_extra(path)
    assert set(indexed.extra) & _RETIRED_MIRROR_KEYS == set()


async def test_an_operator_keeps_the_full_name_of_its_own(svc):
    """``full_name`` is retired on a role but live on an operator, so it survives there."""
    item = await svc.add_operator("Alice Example")
    path = item_file(svc.paths, item)
    before = path.read_bytes()
    assert _stored_extra(path)[X.FULL_NAME] == "Alice Example"

    await svc.repair()

    assert path.read_bytes() == before


async def test_authored_sub_entity_content_survives_the_strip(svc):
    """Every authored region, heading and frontmatter key survives the strip byte-identical."""
    task, path = await _task_carrying_both_families(svc)
    await svc.set_subtask_body(task.id, "ST1", "Authored subtask prose.")
    await svc.comment(task.id, ["A recorded handoff."], as_slug="tech-lead", subtask="ST1")
    await svc.set_body(task.id, "The task's own authored body.")
    before = path.read_text(encoding="utf-8")
    authored_tags = [
        markers.BODY,
        markers.DISCUSSION,
        "subtask:ST1:body",
        "subtask:ST1:discussion",
        "subtask:ST2:body",
        "subtask:ST2:discussion",
    ]
    before_regions = {tag: get_section(before, tag) for tag in authored_tags}
    before_headings = [line for line in before.splitlines() if line.startswith("### ")]
    before_frontmatter = before.split("---\n")[1]

    await svc.repair()

    after = path.read_text(encoding="utf-8")
    assert {tag: get_section(after, tag) for tag in authored_tags} == before_regions
    assert [line for line in after.splitlines() if line.startswith("### ")] == before_headings
    assert after.split("---\n")[1] == before_frontmatter
    assert has_section(after, markers.SUBTASKS)


async def test_a_squad_that_never_carried_the_regions_is_byte_unchanged(svc):
    """With nothing to match, a squad never carrying the regions is byte unchanged."""
    await svc.seed_bundled_skills()
    task = (await create_item(svc, "task", "Nothing retired here")).item
    await svc.add_subtask(task.id, "First")
    before = {
        path: path.read_bytes()
        for path in sorted(svc.paths.squad_dir.rglob("*.md"))
        if path.is_file()
    }

    result = await svc.repair()

    assert result.stripped == []
    assert {path: path.read_bytes() for path in before} == before


# ------------------------------------------------------------------ composition & repeat


async def test_a_file_needing_both_a_strip_and_canonicalization_gets_both(svc):
    """One queued entry per path carries both transformations, for a task and a role alike."""
    other = (await create_item(svc, "task", "Ref target")).item
    task, path = await _task_carrying_both_families(svc)
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "\ncreated_at:",
        f"\nrefs:\n- {other.id}\nextra:\n  ref_kinds:\n    {other.id}: blocks\ncreated_at:",
        1,
    )
    path.write_text(text, encoding="utf-8")
    assert "ref_kinds" in path.read_text(encoding="utf-8")

    role, role_path = await _role_carrying_the_retired_shape(svc, "manager")
    role_text = role_path.read_text(encoding="utf-8")
    role_data = read_frontmatter(text=role_text, source=str(role_path))
    role_data["refs"] = [other.id]
    cast("dict[str, object]", role_data["extra"])["ref_kinds"] = {other.id: "blocks"}
    role_path.write_text(
        replace_frontmatter(role_text, role_data, source=str(role_path)), encoding="utf-8"
    )

    result = await svc.repair()

    after = path.read_text(encoding="utf-8")
    assert "ref_kinds" not in after, "the strip discarded the canonicalisation"
    assert f"{other.id}:blocks" in after
    assert not has_section(after, markers.SUMMARY), "the canonicalisation discarded the strip"
    assert not has_section(after, "subtask:ST1:head")
    assert task.id in result.stripped
    assert task.id in result.canonicalized

    role_after = role_path.read_text(encoding="utf-8")
    assert "ref_kinds" not in role_after, "the role strip discarded the canonicalisation"
    assert f"{other.id}:blocks" in role_after
    role_extra = _stored_extra(role_path)
    assert set(role_extra) & _RETIRED_MIRROR_KEYS == set(), (
        "the canonicalisation rewrote the mirror back onto the role"
    )
    role_region = (get_section(role_after, markers.BODY) or "").strip()
    assert role_region == "# Stored Name\n\nA stored definition."
    assert role.id in result.stripped
    assert role.id in result.canonicalized


async def test_the_sweep_is_idempotent(svc):
    await svc.seed_bundled_skills()
    _task, path = await _task_carrying_both_families(svc)
    await _role_carrying_the_retired_shape(svc, "manager")

    first = await svc.repair()
    corpus = {p: p.read_bytes() for p in sorted(svc.paths.squad_dir.rglob("*.md")) if p.is_file()}
    second = await svc.repair()

    assert first.stripped
    assert second.stripped == []
    assert {p: p.read_bytes() for p in corpus} == corpus
    assert path.read_bytes() == corpus[path]


# ------------------------------------------------------------------------ the frozen list


async def test_the_live_write_path_produces_none_of_the_stripped_names(svc):
    """The frozen list's falsifiable guard: driving a fresh squad through the live write path
    produces none of the names the sweep removes, except each roster body's own placement tag."""
    await svc.seed_bundled_skills()
    task = (await create_item(svc, "task", "Driven through the write path")).item
    await svc.add_subtask(task.id, "First")
    await svc.set_subtask_status(task.id, "ST1", "InProgress")
    review = (await create_item(svc, "review", "Driven through the write path")).item
    await svc.add_finding(review.id, "A finding")
    feature = (await create_item(svc, "feature", "Driven through the write path")).item
    await svc.add_story(feature.id, "A story")
    dev = await svc.add_dev("rust", name="Rusty Dev")
    await svc.sync()

    for path in sorted(svc.paths.squad_dir.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        assert not has_section(text, markers.SUMMARY), f"{path.name} carries a summary region"
        assert ":head -->" not in text, f"{path.name} carries a badge region"

    sq_task_item = await svc.roster_item("skill", "sq-task")
    assert sq_task_item is not None
    sq_task_body = get_section(
        item_file(svc.paths, sq_task_item).read_text(encoding="utf-8"), markers.BODY
    )
    assert (sq_task_body or "").strip() == markers.open_marker(markers.view_tag("item_skill")), (
        "the sq-task skill body carries something other than its own placement tag"
    )
    for slug, view_name in SYSTEM_SKILL_VIEW_NAMES.items():
        item = await svc.roster_item("skill", slug)
        assert item is not None
        body = get_section(item_file(svc.paths, item).read_text(encoding="utf-8"), markers.BODY)
        assert (body or "").strip() == markers.open_marker(markers.view_tag(view_name)), (
            f"the {slug} skill body carries something other than its own placement tag"
        )

    for slug in ("manager", dev.extra[X.SLUG]):
        item = await svc.roster_item("role", slug)
        assert item is not None
        text = item_file(svc.paths, item).read_text(encoding="utf-8")
        region = (get_section(text, markers.BODY) or "").strip()
        assert region == markers.open_marker(markers.view_tag("role_definition")), (
            f"the {slug} role body carries something other than its own placement tag"
        )
        stored = set(_stored_extra(item_file(svc.paths, item)))
        assert stored & _RETIRED_MIRROR_KEYS <= (
            {X.MODEL} if item.extra.get(X.IS_DEV) else set()
        ), f"the {slug} role carries mirror keys again"
