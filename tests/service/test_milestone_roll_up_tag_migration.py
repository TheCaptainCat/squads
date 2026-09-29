"""The schema 0.14 -> 0.15 migration: seeds ``sq:view:milestone_rollup`` onto every existing
milestone body lacking it, through the same marker-safe primitive the placement verb is built
from (``squads._sections.insert_unpaired_marker`` + ``squads._views.resolve_view_target`` —
see ``tests/service/test_view_tag_placement.py`` for that primitive's own exhaustive coverage,
which this module does not re-derive).

Driven exclusively through ``Service.run_pending_migrations()`` — the sanctioned entry point
``sq migrate up`` itself calls — on a squad whose on-disk ``schema_version`` is hand-downgraded
to ``"0.14"``, mirroring ``tests/service/test_v0_3_migration_chain_reaches_current_schema.py``'s
own technique. Never imports the private runner module for its own sake.

Table-driven over body *shape* (empty, prose-only, already tagged, a different tag, other
marker pairs) rather than one test per implemented branch, plus the run-level properties: the
returned count matches files actually changed, only milestone is touched, and an override that
drops the tag from the template is respected.

A second table drives the corpus/spec/filesystem axis this shape table cannot reach: an
unresolvable ``(type, name)`` pair (a deselected view, a declared-but-templateless one) skips
the pair and the run still completes; a skewed item, a missing indexed file, a body with no
``sq:body`` region, or a tag already present outside it skips that one item and the run still
completes, reports it by id, and leaves the operator with a working command afterwards — never
a raise, and (the assertion that actually catches the ``moved_tag`` shape) never a duplicate
marker for ``sq check`` to report.
"""

import tomllib
from pathlib import Path

import pytest

from _helpers import create_item
from squads import __version__, _aio
from squads import _sections as sections
from squads._models import _markers as markers
from squads._models._config import SquadsConfig
from squads._paths import SquadPaths
from squads._rendering._engine import invalidate_squad_dir
from squads._services._service import Service

pytestmark = pytest.mark.anyio

_TAG = markers.view_tag("milestone_rollup")  # bare form, for remove/insert_unpaired_marker
_TAG_MARKER = markers.open_marker(_TAG)  # on-disk form, e.g. "<!-- sq:view:milestone_rollup -->"
_FROM_SCHEMA = "0.14"


async def _downgraded(project) -> Service:
    """A fresh ``Service`` bound to the same squad, with its on-disk ``schema_version``
    hand-rewritten to :data:`_FROM_SCHEMA` — simulates a squad created before this migration,
    without touching any migration runner directly."""
    cfg_path = project.config_path
    text = await _aio.read_text(cfg_path)
    current = project.config.schema_version
    text = text.replace(f'schema_version = "{current}"', f'schema_version = "{_FROM_SCHEMA}"')
    await _aio.write_text(cfg_path, text)
    with cfg_path.open("rb") as fh:
        cfg = SquadsConfig.from_toml_dict(tomllib.load(fh))
    return Service(SquadPaths(root=project.root, squad_dir=project.squad_dir, config=cfg))


async def _text(paths: SquadPaths, item) -> str:
    return await _aio.read_text(paths.abspath(item.path))


async def _write_text(paths: SquadPaths, item, text: str) -> None:
    await _aio.write_text(paths.abspath(item.path), text)


def _write_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )


async def _strip_tag(svc: Service, item) -> None:
    """Remove the tag a freshly-created milestone's body already carries by default, so the
    file reads like one written before this migration ever existed."""
    text = await _text(svc.paths, item)
    stripped, removed = sections.remove_unpaired_marker(text, markers.BODY, _TAG)
    assert removed, "fixture setup: the milestone body carried no tag to strip"
    await _write_text(svc.paths, item, stripped)


# --------------------------------------------------------------------------- shape coverage


async def test_seeds_the_tag_into_an_empty_body(project, svc) -> None:
    m = (await create_item(svc, "milestone", "M")).item
    text = await _text(svc.paths, m)
    emptied = sections.replace_section(text, markers.BODY, "")
    await _write_text(svc.paths, m, emptied)

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15") == 1
    body = sections.get_section(await _text(svc.paths, m), markers.BODY)
    assert body is not None
    assert body.strip() == _TAG_MARKER


async def test_places_the_tag_after_existing_prose_preserving_it_verbatim(project, svc) -> None:
    m = (await create_item(svc, "milestone", "M")).item
    await _strip_tag(svc, m)
    before = sections.get_section(await _text(svc.paths, m), markers.BODY)
    assert before is not None
    assert "Objective" in before  # the template's own prose, still there pre-migration

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15") == 1
    after = sections.get_section(await _text(svc.paths, m), markers.BODY)
    assert after is not None
    assert after.startswith(before)  # every prior byte preserved verbatim, at the front
    assert after.strip().endswith(_TAG_MARKER)


async def test_a_body_already_carrying_the_tag_is_left_untouched(project, svc) -> None:
    m = (await create_item(svc, "milestone", "M")).item  # tag already seeded by the template
    before = await _text(svc.paths, m)
    before_mtime = svc.paths.abspath(m.path).stat().st_mtime_ns

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15", 0) == 0
    assert await _text(svc.paths, m) == before
    assert svc.paths.abspath(m.path).stat().st_mtime_ns == before_mtime


async def test_a_body_carrying_a_different_view_tag_gets_a_second_tag_added(project, svc) -> None:
    m = (await create_item(svc, "milestone", "M")).item
    await _strip_tag(svc, m)
    text = await _text(svc.paths, m)
    seeded, _ = sections.insert_unpaired_marker(text, markers.BODY, markers.view_tag("other"))
    await _write_text(svc.paths, m, seeded)

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15") == 1
    body = sections.get_section(await _text(svc.paths, m), markers.BODY)
    assert body is not None
    assert markers.open_marker(markers.view_tag("other")) in body
    assert _TAG_MARKER in body


async def test_the_discussion_region_and_other_markers_are_left_untouched(project, svc) -> None:
    m = (await create_item(svc, "milestone", "M")).item
    await _strip_tag(svc, m)
    await svc.comment(m.id, ["a discussion point"], as_slug="manager")

    down = await _downgraded(project)
    await down.run_pending_migrations()

    disc = sections.get_section(await _text(svc.paths, m), markers.DISCUSSION)
    assert disc is not None
    assert "a discussion point" in disc
    assert _TAG_MARKER not in disc


# --------------------------------------------------------------------------- run-level properties


async def test_several_milestones_in_one_run_are_all_seeded_and_counted(project, svc) -> None:
    milestones = []
    for i in range(3):
        m = (await create_item(svc, "milestone", f"M{i}")).item
        await _strip_tag(svc, m)
        milestones.append(m)

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15") == 3
    for m in milestones:
        body = sections.get_section(await _text(svc.paths, m), markers.BODY)
        assert body is not None
        assert _TAG_MARKER in body


async def test_a_corpus_with_zero_milestones_is_a_clean_no_op(project, svc) -> None:
    await create_item(svc, "task", "unrelated")

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15", 0) == 0
    errors = [i for i in await down.check() if i.level == "error"]
    assert not errors


async def test_only_milestone_files_are_written_every_other_type_stays_byte_identical(
    project, svc
) -> None:
    m = (await create_item(svc, "milestone", "M")).item
    await _strip_tag(svc, m)
    others = [
        (await create_item(svc, t, f"one {t}")).item
        for t in ("epic", "feature", "task", "bug", "decision", "contract", "guide", "review")
    ]
    before = {o.id: await _text(svc.paths, o) for o in others}

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15") == 1  # the milestone alone
    for o in others:
        assert await _text(svc.paths, o) == before[o.id], f"{o.id} was written by the run"


async def test_a_roster_type_is_out_of_scope_even_with_its_own_tag_stripped(project, svc) -> None:
    """The negative above is a weak proof for the roster exclusion on its own: a role's body
    already carries its own ``role_definition`` tag from creation, so a scope bug that let a
    roster type through would still be masked by the placement primitive's own idempotent-skip
    — no write, same as a correctly-scoped run. Strip the tag first so a roster type actually
    left in scope would show up as a real, counted write."""
    role = await svc.roster_item("role", "manager")
    assert role is not None
    text = await _text(svc.paths, role)
    stripped, removed = sections.remove_unpaired_marker(
        text, markers.BODY, markers.view_tag("role_definition")
    )
    assert removed, "fixture setup: the manager role carried no role_definition tag to strip"
    await _write_text(svc.paths, role, stripped)

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    # Not a body-content assertion: `run_pending_migrations`'s own trailing repair sweep
    # (`MaintenanceMixin._backfill_roster_body_tags`) re-seeds an emptied role's tag through
    # its own, unrelated mechanism regardless of this migration's scope, so the file ends up
    # tagged again either way. `changed` is this migration's own count, untouched by that
    # later step — the one assertion that actually isolates whether *this* migration reached
    # a roster-type item.
    assert run.changed.get("0.15", 0) == 0


async def test_a_rerun_after_the_first_reports_zero_and_writes_nothing(project, svc) -> None:
    """The squad-level idempotency property the CLI relies on: once a squad has already
    reached the target schema, ``sq migrate up`` never re-invokes this (or any) runner —
    covered end-to-end via ``tests/cli/test_milestone_roll_up_tag_migration_cli.py``'s
    ``nothing to migrate`` assertion. This test instead pins the underlying primitive's own
    idempotent-skip through the run: a squad whose milestone already carries the tag before
    the migration is even due reports zero changed once it is."""
    m = (await create_item(svc, "milestone", "M")).item  # tag already present
    before = await _text(svc.paths, m)

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15", 0) == 0
    assert await _text(svc.paths, m) == before


# --------------------------------------------------------------------------- override-awareness


async def test_an_override_template_seeding_no_tag_leaves_untagged_milestones_untouched(
    project, svc
) -> None:
    override_path = project.squad_dir / ".overrides" / "templates" / "items" / "milestone.md.j2"
    override_path.parent.mkdir(parents=True, exist_ok=True)
    override_path.write_text(
        "<!-- sq:body -->\n## Objective\n\n_TODO: no roll-up tag here._\n<!-- sq:body:end -->\n\n"
        "## Discussion\n\n<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n",
        encoding="utf-8",
    )
    invalidate_squad_dir(project.squad_dir)
    m = (await create_item(svc, "milestone", "M")).item
    body = sections.get_section(await _text(svc.paths, m), markers.BODY)
    assert body is not None
    assert _TAG_MARKER not in body  # precondition: the override really did drop the tag
    before = await _text(svc.paths, m)

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15", 0) == 0
    assert await _text(svc.paths, m) == before


# --------------------------------------------------------------------------- an unresolvable
# (type, name) pair skips the pair, not the run


async def test_a_deselected_view_over_a_corpus_with_milestones_still_reaches_current(
    project, svc
) -> None:
    """The spec-side direction: the template still seeds the tag unconditionally, but the
    active spec no longer declares the view at all (``[selected].views = []``). The pair
    cannot resolve, so it is skipped -- the run still completes and stamps the squad current,
    rather than refusing the whole upgrade over an adopter's own customisation."""
    m1 = (await create_item(svc, "milestone", "One")).item
    await _strip_tag(svc, m1)
    m2 = (await create_item(svc, "milestone", "Two")).item
    await _strip_tag(svc, m2)
    _write_override(project.squad_dir, "[selected]\nviews = []\n")

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15", 0) == 0
    assert run.skipped.get("0.15", []) == []  # nothing to name -- the pair skipped, not an item
    for m in (m1, m2):
        body = sections.get_section(await _text(svc.paths, m), markers.BODY)
        assert body is not None
        assert _TAG_MARKER not in body
    # What the operator can do next: the squad is current, and check is reachable again.
    with project.config_path.open("rb") as fh:
        assert tomllib.load(fh)["schema_version"] == "0.15"
    await down.check()  # must not raise the schema hard-stop this deadlocked on before


async def test_a_deselected_view_over_zero_milestones_still_reaches_current(project, svc) -> None:
    """The sharper case: the run would not have written a single byte even on the old
    behaviour, and still used to refuse before ever reaching the item loop."""
    await create_item(svc, "task", "unrelated")
    _write_override(project.squad_dir, "[selected]\nviews = []\n")

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15", 0) == 0
    with project.config_path.open("rb") as fh:
        assert tomllib.load(fh)["schema_version"] == "0.15"
    await down.check()


async def test_a_name_the_template_still_seeds_with_no_resolvable_view_skips_that_pair(
    project, svc
) -> None:
    """The declared-but-templateless half of the same axis: the view stays declared (unlike
    the deselect above) but has no presentation template, so it still cannot resolve."""
    override_dir = project.squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    _write_override(
        project.squad_dir,
        '[views.templateless]\nsource = { kind = "subentity", name = "finding" }\n',
    )
    (override_dir / "templates" / "items").mkdir(parents=True, exist_ok=True)
    (override_dir / "templates" / "items" / "milestone.md.j2").write_text(
        "<!-- sq:body -->\n<!-- sq:view:templateless -->\n<!-- sq:body:end -->\n\n"
        "## Discussion\n\n<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n",
        encoding="utf-8",
    )
    invalidate_squad_dir(project.squad_dir)
    m = (await create_item(svc, "milestone", "M")).item
    body = sections.get_section(await _text(svc.paths, m), markers.BODY)
    assert body is not None
    assert "sq:view:templateless" in body  # precondition: the override template seeds it

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15", 0) == 0
    with project.config_path.open("rb") as fh:
        assert tomllib.load(fh)["schema_version"] == "0.15"
    await down.check()


# --------------------------------------------------------------------------- a skewed item, a
# missing file or a missing body region skips one item, reported by id


async def _make_skewed(svc: Service, item) -> None:
    text = await _text(svc.paths, item)
    fm, body = sections.split_frontmatter(text)
    fm["title"] = "Hand-edited on disk"
    await _write_text(svc.paths, item, sections.join_frontmatter(fm, body))


async def _make_missing_file(svc: Service, item) -> None:
    svc.paths.abspath(item.path).unlink()


async def _make_no_body_region(svc: Service, item) -> None:
    text = await _text(svc.paths, item)
    await _write_text(svc.paths, item, sections.remove_section(text, markers.BODY))


async def _make_moved_tag(svc: Service, item) -> None:
    """Assumes the in-region tag was already stripped (every parametrized case's shared setup
    does this before calling *damage*) and places it elsewhere in the file instead -- the shape
    an author produces by hand-moving the tag out of ``sq:body``."""
    text = await _text(svc.paths, item)
    assert _TAG_MARKER not in text, "fixture setup: expected the tag already stripped"
    moved = text.replace("## Discussion", f"{_TAG_MARKER}\n\n## Discussion", 1)
    assert moved != text, "fixture setup: no '## Discussion' heading to place the tag before"
    await _write_text(svc.paths, item, moved)


@pytest.mark.parametrize(
    "damage",
    [_make_skewed, _make_missing_file, _make_no_body_region, _make_moved_tag],
    ids=["skewed", "missing_file", "no_body_region", "moved_tag"],
)
async def test_a_damaged_item_at_the_lower_sequence_id_is_skipped_the_healthy_one_still_lands(
    project, svc, damage
) -> None:
    """Table-driven over the four item-level failure shapes, each asserting three things: what
    happened to the damaged item (skipped, named, left off the count), what happened to the
    healthy one (tagged and counted, proving it was processed *after* the skip rather than
    before it -- the damaged item is created first, so it gets the lower ``sequence_id``), and
    what the operator can do next -- the stamp still lands and, the assertion that actually
    matters for the ``moved_tag`` shape, ``sq check`` reports no error afterwards. A byte-count
    or occurrence-count assertion would not catch a regression here: it is ``sq check``'s own
    duplicate-marker finding that proves whether a second, in-region copy was seeded alongside
    one already live outside the region, not what the file looks like on its own."""
    damaged = (await create_item(svc, "milestone", "A damaged one")).item
    await _strip_tag(svc, damaged)
    healthy = (await create_item(svc, "milestone", "A healthy one")).item
    await _strip_tag(svc, healthy)
    assert damaged.sequence_id < healthy.sequence_id  # precondition: processed first

    await damage(svc, damaged)
    damaged_before = await _text(svc.paths, damaged) if damage is not _make_missing_file else None

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    # 1. the damaged item: skipped, named by id, not counted as changed, and untouched on disk
    # wherever a file still exists to compare.
    assert damaged.id in run.skipped.get("0.15", [])
    if damaged_before is not None:
        assert await _text(svc.paths, damaged) == damaged_before
    # 2. the healthy item: tagged and counted -- proves the pass kept going past the skip.
    assert run.changed.get("0.15") == 1
    healthy_body = sections.get_section(await _text(svc.paths, healthy), markers.BODY)
    assert healthy_body is not None
    assert _TAG_MARKER in healthy_body
    # 3. what the operator can do next: the stamp landed, and sq check reports no error --
    # the deadlock (raise before the stamp, then every command refusing) is gone, and so is
    # any error the run's own write could otherwise have introduced.
    with project.config_path.open("rb") as fh:
        assert tomllib.load(fh)["schema_version"] == "0.15"
    errors = [i for i in await down.check() if i.level == "error"]
    assert not errors, [i.message for i in errors]
    await down.repair()  # the specific remedy the runbook now points a skewed item at


async def test_a_run_that_skips_nothing_reports_no_skipped_ids(project, svc) -> None:
    m = (await create_item(svc, "milestone", "M")).item
    await _strip_tag(svc, m)

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15") == 1
    assert run.skipped.get("0.15", []) == []


async def test_every_eligible_item_skipped_still_reaches_current_and_reports_zero_changed(
    project, svc
) -> None:
    m1 = (await create_item(svc, "milestone", "One")).item
    await _strip_tag(svc, m1)
    await _make_missing_file(svc, m1)
    m2 = (await create_item(svc, "milestone", "Two")).item
    await _strip_tag(svc, m2)
    await _make_missing_file(svc, m2)

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15", 0) == 0
    assert set(run.skipped.get("0.15", [])) == {m1.id, m2.id}
    with project.config_path.open("rb") as fh:
        assert tomllib.load(fh)["schema_version"] == "0.15"
