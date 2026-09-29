"""The migration that seeds ``sq:view:milestone_rollup`` onto every existing milestone body
lacking it, table-driven over body shape, run-level properties, unresolvable-pair skipping,
and item-level damage (missing file, no body region, moved tag), each skipped and reported by
id without aborting the run."""

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
from squads._views import place_view_tags
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

_TAG = markers.view_tag("milestone_rollup")
_TAG_MARKER = markers.open_marker(_TAG)
_FROM_SCHEMA = "0.14"


async def _downgraded(project) -> Service:
    """A fresh ``Service`` bound to the same squad, its on-disk ``schema_version`` rewritten
    to simulate a squad created before this migration."""
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


async def _strip_tag(svc: Service, item, name: str = "milestone_rollup") -> None:
    """Remove *name*'s tag from *item*'s body, as if written before this migration existed."""
    text = await _text(svc.paths, item)
    region = sections.get_section(text, markers.BODY) or ""
    stripped_region, removed = sections.strip_marker_lines(
        region, lambda raw: raw != f"sq:{markers.view_tag(name)}"
    )
    assert removed, f"fixture setup: the item body carried no {name!r} tag to strip"
    await _write_text(
        svc.paths, item, sections.replace_section(text, markers.BODY, stripped_region)
    )


async def _seed_tag_directly(svc: Service, item, name: str) -> None:
    """Place *name*'s tag through the real placement routine, bypassing ``add_view``'s gate."""
    text = await _text(svc.paths, item)
    region = sections.get_section(text, markers.BODY) or ""
    new_inner = place_view_tags(
        region,
        None,
        seeded=frozenset({name}),
        spec=svc.spec,
        item_type=item.type,
        addr=item.sequence_id,
    )
    await _write_text(svc.paths, item, sections.replace_section(text, markers.BODY, new_inner))


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
    assert "Objective" in before

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15") == 1
    after = sections.get_section(await _text(svc.paths, m), markers.BODY)
    assert after is not None
    assert after.startswith(before)
    assert after.strip().endswith(_TAG_MARKER)


async def test_a_body_already_carrying_the_tag_is_left_untouched(project, svc) -> None:
    m = (await create_item(svc, "milestone", "M")).item
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
    await _seed_tag_directly(svc, m, "other")

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

    assert run.changed.get("0.15") == 1
    for o in others:
        assert await _text(svc.paths, o) == before[o.id], f"{o.id} was written by the run"


async def test_an_emptied_roster_body_is_out_of_scope_for_the_non_roster_step(project, svc) -> None:
    """A role, a roster type, is never reached by this step, empty body or not."""
    role = await svc.roster_item("role", "manager")
    assert role is not None
    await _strip_tag(svc, role, "role_definition")

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15", 0) == 0


async def test_a_rerun_after_the_first_reports_zero_and_writes_nothing(project, svc) -> None:
    """A squad whose milestone already carries the tag reports zero changed once migrated."""
    m = (await create_item(svc, "milestone", "M")).item
    before = await _text(svc.paths, m)

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15", 0) == 0
    assert await _text(svc.paths, m) == before


async def test_a_second_direct_call_after_seeding_reports_zero_and_writes_nothing(
    project, svc
) -> None:
    """Calling the runner itself a second time, directly, reports zero and writes nothing."""
    m = (await create_item(svc, "milestone", "M")).item
    await _strip_tag(svc, m)

    down = await _downgraded(project)
    await down.run_pending_migrations()
    seeded = await _text(svc.paths, m)

    from squads._migrations._v0_14_to_v0_15 import migrate
    from squads._paths import resolve as resolve_squad_paths

    fresh_paths = resolve_squad_paths(client_cwd=project.root)
    outcome = await migrate(fresh_paths)

    assert outcome.count == 0
    assert await _text(svc.paths, m) == seeded


async def test_a_milestone_carrying_the_tag_twice_collapses_to_one_and_is_counted(
    project, svc
) -> None:
    """A duplicate copy of the tag already inside ``sq:body`` collapses to one, and is counted
    as a change."""
    m = (await create_item(svc, "milestone", "M")).item
    text = await _text(svc.paths, m)
    doubled = sections.replace_section(text, markers.BODY, f"{_TAG_MARKER}\n\n{_TAG_MARKER}")
    assert doubled.count(_TAG_MARKER) == 2, "fixture setup: expected two copies of the tag"
    await _write_text(svc.paths, m, doubled)

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15") == 1
    body = sections.get_section(await _text(svc.paths, m), markers.BODY)
    assert body is not None
    assert body.count(_TAG_MARKER) == 1


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
    assert _TAG_MARKER not in body
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
    """A deselected view cannot resolve, so it is skipped, and the run still stamps current."""
    m1 = (await create_item(svc, "milestone", "One")).item
    await _strip_tag(svc, m1)
    m2 = (await create_item(svc, "milestone", "Two")).item
    await _strip_tag(svc, m2)
    _write_override(project.squad_dir, "[selected]\nviews = []\n")

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15", 0) == 0
    assert run.skipped.get("0.15", []) == []
    for m in (m1, m2):
        body = sections.get_section(await _text(svc.paths, m), markers.BODY)
        assert body is not None
        assert _TAG_MARKER not in body
    with project.config_path.open("rb") as fh:
        assert tomllib.load(fh)["schema_version"] == "0.15"
    await down.check()


async def test_a_deselected_view_over_zero_milestones_still_reaches_current(project, svc) -> None:
    """A deselected view over zero milestones still reaches current."""
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
    """A declared view with no presentation template also cannot resolve, and is skipped."""
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
    declared = Service(svc.paths, spec=load_workflow_spec(squad_dir=svc.paths.squad_dir))
    m = (await create_item(declared, "milestone", "M")).item
    body = sections.get_section(await _text(svc.paths, m), markers.BODY)
    assert body is not None
    assert "sq:view:templateless" in body

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
    """Place the tag outside ``sq:body``, as if an author hand-moved it there."""
    text = await _text(svc.paths, item)
    assert _TAG_MARKER not in text, "fixture setup: expected the tag already stripped"
    moved = text.replace("## Discussion", f"{_TAG_MARKER}\n\n## Discussion", 1)
    assert moved != text, "fixture setup: no '## Discussion' heading to place the tag before"
    await _write_text(svc.paths, item, moved)


@pytest.mark.parametrize(
    "damage",
    [_make_missing_file, _make_no_body_region, _make_moved_tag],
    ids=["missing_file", "no_body_region", "moved_tag"],
)
async def test_a_damaged_item_at_the_lower_sequence_id_is_skipped_the_healthy_one_still_lands(
    project, svc, damage
) -> None:
    """A damaged item at the lower sequence id is skipped and named; the healthy one, processed
    after it, is still tagged and counted, and the stamp still lands."""
    damaged = (await create_item(svc, "milestone", "A damaged one")).item
    await _strip_tag(svc, damaged)
    healthy = (await create_item(svc, "milestone", "A healthy one")).item
    await _strip_tag(svc, healthy)
    assert damaged.sequence_id < healthy.sequence_id

    await damage(svc, damaged)
    damaged_before = await _text(svc.paths, damaged) if damage is not _make_missing_file else None

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert damaged.id in run.skipped.get("0.15", [])
    if damaged_before is not None:
        assert await _text(svc.paths, damaged) == damaged_before
    assert run.changed.get("0.15") == 1
    healthy_body = sections.get_section(await _text(svc.paths, healthy), markers.BODY)
    assert healthy_body is not None
    assert _TAG_MARKER in healthy_body
    with project.config_path.open("rb") as fh:
        assert tomllib.load(fh)["schema_version"] == "0.15"
    errors = [i for i in await down.check() if i.level == "error"]
    if damage is _make_no_body_region:
        assert [i.message for i in errors] == [
            "missing seeded view tag <!-- sq:view:milestone_rollup --> — restore it with "
            f"`sq milestone {damaged.sequence_id} view add milestone_rollup`, or disable it "
            f"with `sq milestone {damaged.sequence_id} view disable milestone_rollup`"
        ]
        assert errors[0].item == Path(damaged.path).name
    else:
        assert not errors, [i.message for i in errors]


async def test_a_skewed_milestone_is_tagged_from_its_own_on_disk_frontmatter(project, svc) -> None:
    """A milestone whose on-disk frontmatter has diverged from the indexed copy is still
    tagged from its own on-disk frontmatter, not skipped."""
    m = (await create_item(svc, "milestone", "A skewed one")).item
    await _strip_tag(svc, m)
    await _make_skewed(svc, m)

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15") == 1
    assert m.id not in run.skipped.get("0.15", [])
    text = await _text(svc.paths, m)
    fm, _body = sections.split_frontmatter(text)
    assert fm["title"] == "Hand-edited on disk"
    body = sections.get_section(text, markers.BODY)
    assert body is not None
    assert _TAG_MARKER in body


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
