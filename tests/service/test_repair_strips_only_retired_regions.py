"""``Service.repair()``'s corpus sweep: the retired marker regions and the stored role body it
removes, and — far more of this module — everything it must not touch.

The sweep runs inside the rebuild's per-file loop, on the same deferred list as the existing
ref canonicalisation. What it may remove is a **frozen list** of named regions, each of which
must satisfy three conditions in this same build: no live write path produces it, no read path
consumes it as authoritative because its computed replacement already ships, and its content
is derived rather than authored. ``test_the_live_write_path_produces_none_of_the_stripped_names``
is that list's falsifiable guard — restore a writer and it reddens, which is the signal that a
name has been added to the list before its writer retired. That ordering matters because the
failure it prevents is not dead bytes: it is a loop where the sweep and the writer undo each
other on alternate commands.

The authored-content risk here is not inside a region — it is choosing the wrong files. Every
skill, generated or authored, sits in the same folder with the same item type and the same
frontmatter shape, and the ``sq-`` prefix is not reserved, so the folder, the type and the
prefix are each cheap and each wrong. The negative assertions below are the ones that fail if
the discriminator is ever "fixed" to one of them.

A stored **skill** body is left alone for a stronger reason than any of those: whether a slug
is template-owned is a function of today's vocabulary, in both of its halves (a project can
declare a type, a release can bundle one), while the body was written under an earlier one. So
the classification can flip after the fact on a slug every supported command accepted, and at
the moment of the sweep an authored body and a generated one are indistinguishable. The role
half has no such gap: its refusal keys on the item type, which does not move.
"""

from typing import cast

import pytest

from _helpers import create_item
from squads._index._resolver import item_file
from squads._interactions import is_system_skill
from squads._itemfile import read_frontmatter
from squads._models import _markers as markers
from squads._models._extras import ExtraKey as X
from squads._models._metadata import RETIRED_ROLE_EXTRA_KEYS
from squads._sections import get_section, has_section, replace_frontmatter, replace_section
from squads._services import _service as service
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

#: A summary region in the shape the retired writer produced, inserted before its container
#: exactly as ``_discussion.ensure_summary`` did — its own blank separator line included, so
#: the strip has the real blank-line bookkeeping to get right and not a simplified stand-in.
_SUMMARY_REGION = """<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | First |  |
<!-- sq:summary:end -->

"""


#: The mirror shape a release before this one stored on every role item, written back onto a
#: file here because nothing produces it any more. ``model`` is included for both role shapes:
#: it is what separates a bundled role (mirror residue, removed) from a developer (an operator
#: setting with no catalog answer, kept), and a corpus that carried it for only one of them
#: could not tell the two apart.
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
    # No `ExtraKey` member: the skill-list cache and its member were deleted together, and
    # the name survives only so a corpus written before that can be cleaned of it.
    "skills": ["squads", "sq-task"],
}

#: The names the sweep takes off a role item. Read from the declaration the refusals share
#: rather than restated, so this module cannot pass while disagreeing with the product about
#: what is retired; ``model`` is added because it is retired for a bundled role only and the
#: shared declaration is deliberately silent on a per-shape question.
_RETIRED_MIRROR_KEYS: frozenset[str] = RETIRED_ROLE_EXTRA_KEYS | {X.MODEL}


def _stored_extra(path) -> dict[str, object]:
    """The ``extra`` mapping the file itself carries — read from the frontmatter, never from
    the index, since half of what is asserted here is that the two agree."""
    return read_frontmatter(text=path.read_text(encoding="utf-8"), source=str(path)).get(
        "extra", {}
    )


async def _role_carrying_the_retired_shape(svc, slug: str):
    """The role item for *slug*, with the retired mirror written into its ``extra`` and a
    definition written into its ``sq:body`` region.

    Written straight onto the file for the same reason the task helper above is: no live write
    path produces either shape any more, so a corpus carrying them has to be constructed. The
    keys already on the file (``slug``, and a developer's ``model``/``is_dev``/``tech``) are
    left exactly where they are, so their order in the mapping is a real legacy file's order
    and not one this helper chose.
    """
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
    """A badge region in the shape the retired writer produced, for the region tag *tag*.

    The tag was composed at write time as ``<kind>:<local-id>:head`` and was never declared as
    a constant, so there is nothing to import: a probe that looks for one in
    ``_models/_markers.py`` is answering a question about that module, not about a corpus.
    Local ids are uppercase for every bundled kind, which is what a scan assuming lowercase
    silently misses.
    """
    return f"""<!-- sq:{tag}:head -->
**Status:** ⚪ Todo
<!-- sq:{tag}:head:end -->

"""


async def _task_carrying_both_families(svc):
    """A task item whose file carries a summary region and two subtask badge regions.

    Written straight onto the file because no live write path produces either any more —
    which is the whole premise of the sweep, and the reason this corpus has to be constructed
    rather than driven.
    """
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
    # Precondition, asserted rather than assumed: a scan that finds nothing here would make
    # every assertion below pass against a corpus that never carried the regions at all.
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
    """Byte equality against a task the write path produced with no regions to begin with —
    the strip must land on the current shape, not merely leave the markers gone.

    This is what catches the blank-line bookkeeping: a cut that drops the region but keeps the
    separator line it owned leaves a doubled blank line, which no assertion about marker
    absence can see.
    """
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
    """The scan matches tag *shape*, never a list of declared sub-entity kinds — so a badge
    region belonging to a kind a project declared and later dropped is removed as well, and
    the sweep never has to consult the live spec's vocabulary to do it."""
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
    """A template-owned skill's stored body is left exactly where it is.

    It is a derived duplicate — ``sq skill <slug> show`` renders the definition on every read —
    but derived is not the bar the sweep has to clear before deleting something. The bar is
    proving nothing *authored* it, and for a skill nothing on the item answers that: whether a
    slug is template-owned is a function of today's vocabulary, and the body was written under
    an earlier one. The sibling below drives the flip that makes it concrete.

    Leaving it costs a stale duplicate on disk, which no read path consumes and which
    ``set_body`` still refuses to add to. Emptying it costs, in the case the corpus cannot
    distinguish, the only copy of someone's work.
    """
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
    assert (get_section(before.decode("utf-8"), markers.BODY) or "").strip()  # precondition

    result = await svc.repair()

    assert path.read_bytes() == before
    assert item.id not in result.stripped


async def test_declaring_an_item_type_does_not_delete_an_authored_skill_of_that_name(svc, tmp_path):
    """The destruction path this rule exists to close, driven through supported commands only.

    ``sq-onboarding`` is authored while no ``onboarding`` type exists — ``sq skill add`` accepts
    the slug (the ``sq-`` prefix is not reserved) and ``sq skill body`` accepts the write. The
    project then declares an item type of that name, which is a supported thing to do and which
    makes the very same slug read as template-owned from that moment on. Nothing about the
    stored body changed; only the answer to "is this generated" did.

    The same flip arrives without any override at all when a *release* adds a bundled type: a
    slug that was authorable on the previous version is template-owned on upgrade, for every
    squad at once. That is why the containment is on the sweep and not on the discriminator —
    ``is_system_skill`` is the correct classifier and stays exactly where it is, including in
    ``set_body``'s refusal, which is what stops the authored body being *extended* from here on.
    """
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
    assert is_system_skill("sq-onboarding", spec)  # precondition: the class really did flip
    declared = service.Service(svc.paths, spec=spec)

    await declared.repair()

    assert path.read_bytes() == before


# ------------------------------------------------------- what the sweep must not touch


@pytest.mark.parametrize("slug", ["house-style", "sq-onboarding"])
async def test_a_custom_skill_body_survives_byte_identical(svc, slug: str):
    """The one real destruction risk, and the assertion that fails for each of the three
    cheaper discriminators.

    ``sq-onboarding`` is the case a prefix-keyed sweep passes everything else while getting
    wrong: the ``sq-`` prefix is not reserved to squads, so an authored skill is free to carry
    it. Both slugs sit in the skills folder with the roster skill type, which is why neither
    the folder nor the type separates them from the generated files beside them either.
    """
    await svc.seed_bundled_skills()
    item = await svc.add_skill(slug, description="An authored runbook")
    await svc.set_body(item.id, "AUTHORED CONTENT — this body is storage, not a rendering.")
    path = item_file(svc.paths, item)
    before = path.read_bytes()

    await svc.repair()

    assert path.read_bytes() == before


async def test_a_role_body_is_emptied_and_keeps_its_markers(svc):
    """A role's definition is resolved and rendered on every ``sq role <slug> show``, so a
    stored copy is derived — and the only copy that can go stale, since nothing refreshes it.

    Keeping the marker pair is the half that is not about content: a *removed* region is what
    the show path reads as "no active item for this slug", a false and alarming answer for a
    role that is live.
    """
    item, path = await _role_carrying_the_retired_shape(svc, "manager")
    assert (get_section(path.read_text(encoding="utf-8"), markers.BODY) or "").strip()

    result = await svc.repair()

    text = path.read_text(encoding="utf-8")
    assert has_section(text, markers.BODY), "the body markers were deleted, not emptied"
    assert not (get_section(text, markers.BODY) or "").strip()
    assert item.id in result.stripped


@pytest.mark.parametrize("is_dev", [False, True], ids=["bundled", "developer"])
async def test_a_role_keeps_exactly_the_extra_keys_a_writer_still_produces(svc, is_dev: bool):
    """The data-loss edge of the whole sweep, from both sides at once.

    ``model`` is the key that makes it one. For a bundled role it is a catalog answer and the
    stored copy is mirror residue; for a developer it is an operator setting with no catalog
    answer at all, so a stripped one is not resolved back on the next read — the dev pool
    re-rolls a different value and the operator's choice is gone. The two shapes therefore
    have to be asserted against each other, not one of them against a hand-written list.

    ``is_default`` is asserted retained for a different reason: ``sq role set-default`` writes
    it, so it never joined the mirror's retirement even though the mirror also used to write
    it. ``is_dev``/``tech`` likewise.
    """
    role = (
        await svc.add_dev("rust", name="Rusty Dev", model="opus")
        if is_dev
        else await svc.activate_role("architect")
    )
    # A designation the *catalog* already answers is held with nothing stored, so it has to be
    # moved onto a role the catalog does not designate for the stored key to exist at all.
    await svc.set_default_role(role.id)
    slug = role.extra[X.SLUG]
    _item, path = await _role_carrying_the_retired_shape(svc, slug)
    stored = _stored_extra(path)
    # Preconditions: every name below is really on the file before the sweep runs, so an
    # assertion of absence afterwards cannot pass against a file that never carried it.
    assert set(stored) >= _RETIRED_MIRROR_KEYS
    assert stored[X.MODEL] == "opus"

    await svc.repair()

    retained: dict[str, object] = {X.SLUG: slug, X.IS_DEFAULT: True}
    if is_dev:
        retained |= {X.MODEL: "opus", X.IS_DEV: True, X.TECH: "rust"}
    # Equality, not a containment check on either side: the two halves of this — nothing
    # retired survived, and nothing live was taken — fail in opposite directions, and a
    # subset assertion would only ever catch one of them.
    assert _stored_extra(path) == retained
    assert (X.MODEL in _stored_extra(path)) is is_dev


async def test_the_index_loses_the_same_role_keys_the_file_does(svc):
    """File and index agree on exactly the keys just removed.

    The rebuild ends each iteration with ``db.add(item)``, where ``item`` was parsed from the
    very frontmatter the sweep rewrites, so an ``Item`` still carrying a key the file no
    longer does commits the disagreement. Asserted directly rather than inferred from a clean
    ``sq check``: the check would only report it if the skew guard covered these keys, and the
    guard is not what this is about.
    """
    item, path = await _role_carrying_the_retired_shape(svc, "manager")

    await svc.repair()

    indexed = (await svc.store.load()).items[item.sequence_id]
    assert indexed.extra == _stored_extra(path)
    assert set(indexed.extra) & _RETIRED_MIRROR_KEYS == set()


async def test_an_operator_keeps_the_full_name_of_its_own(svc):
    """``full_name`` is a retired key on a *role* and a live one on an operator: ``add_operator``
    writes it and ``sq operator list`` reads it straight back. The sweep is keyed on the item's
    declared type for exactly this reason, and a key-name-only match would empty the operator
    roster of every name it shows."""
    item = await svc.add_operator("Alice Example")
    path = item_file(svc.paths, item)
    before = path.read_bytes()
    assert _stored_extra(path)[X.FULL_NAME] == "Alice Example"

    await svc.repair()

    assert path.read_bytes() == before


async def test_authored_sub_entity_content_survives_the_strip(svc):
    """Every authored region, heading and frontmatter key in a file the sweep *does* rewrite is
    byte-identical afterwards — the clause that proves "no authored content moves". An absence
    assertion about the stripped regions alone cannot: it says nothing about the rest."""
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
    """The negative case that stops the sweep becoming a reformatter: with nothing to match,
    no file is written at all and repair behaves exactly as it did before."""
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
    """One queued entry per path, carrying both transformations.

    The canonicalisation recorder builds its replacement from the file's original text. A
    second, independently-built entry for the same path would mean whichever was written last
    silently discarded the other's edit — and the two would cancel on exactly the files that
    need them both, which is the population least likely to be spot-checked.
    """
    other = (await create_item(svc, "task", "Ref target")).item
    task, path = await _task_carrying_both_families(svc)
    # A legacy `extra.ref_kinds` map is one of the two shapes the fold rewrites: on disk it is
    # a separate mapping, and canonicalisation folds it into the `refs` entry itself.
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "\ncreated_at:",
        f"\nrefs:\n- {other.id}\nextra:\n  ref_kinds:\n    {other.id}: blocks\ncreated_at:",
        1,
    )
    path.write_text(text, encoding="utf-8")
    assert "ref_kinds" in path.read_text(encoding="utf-8")  # precondition

    # The role shape is the second half of the same claim, and it composes differently: its
    # own transformation edits the frontmatter, which is the very thing canonicalisation
    # rewrites — so here the two do not merely have to survive each other, they have to be the
    # same rewrite. A role whose mirror is dropped from the file but not from the parsed
    # `Item` writes a canonical frontmatter that puts the key straight back.
    role, role_path = await _role_carrying_the_retired_shape(svc, "manager")
    role_text = role_path.read_text(encoding="utf-8")
    role_data = read_frontmatter(text=role_text, source=str(role_path))
    role_data["refs"] = [other.id]
    # Into the *existing* mapping: a role file already carries an `extra:` block, and a second
    # one appended as text would be a duplicate YAML key whose later value wins — silently
    # deleting the very mirror this case is here to watch survive.
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
    assert not (get_section(role_after, markers.BODY) or "").strip()
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
    """The frozen list's falsifiable guard: drive a fresh squad through the write path and it
    produces none of the names the sweep removes.

    Restore any of those writers and this reddens — which is exactly the signal wanted, since
    a name whose writer is still live puts the sweep and that writer into a loop where each
    undoes the other on alternate commands. This is checked once, when a name joins the list;
    it is never a runtime gate on corpus state.
    """
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

    for slug in ("sq-task", "squads"):
        item = await svc.roster_item("skill", slug)
        assert item is not None
        body = get_section(item_file(svc.paths, item).read_text(encoding="utf-8"), markers.BODY)
        assert not (body or "").strip(), f"the {slug} skill body is stored again"

    # The role half, driven through creation *and* a sync — the two commands whose retired
    # writers made this the loop the frozen list exists to prevent. Restore either and this
    # reddens: the sweep would strip on `repair` and the writer would put it back on `sync`.
    for slug in ("manager", dev.extra[X.SLUG]):
        item = await svc.roster_item("role", slug)
        assert item is not None
        text = item_file(svc.paths, item).read_text(encoding="utf-8")
        assert not (get_section(text, markers.BODY) or "").strip(), (
            f"the {slug} role body is stored again"
        )
        stored = set(_stored_extra(item_file(svc.paths, item)))
        assert stored & _RETIRED_MIRROR_KEYS <= (
            {X.MODEL} if item.extra.get(X.IS_DEV) else set()
        ), f"the {slug} role carries mirror keys again"
