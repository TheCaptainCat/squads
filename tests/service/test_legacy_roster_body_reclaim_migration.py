"""The migration step that reclaims a role's, permanently-system skill's, or per-item-type
skill's legacy plain-prose body onto its placement tag. Every roster-classified body is
overwritten unconditionally; a custom skill matching no declared type is left alone.

Table-driven over host family (role, system skill, per-item-type skill, custom skill) crossed
with body shape (empty, legacy prose, authored prose, already tagged, marker-shaped).
"""

import shutil
import tomllib
from pathlib import Path

import pytest

from squads import _actor as actor
from squads._aio import read_text, write_text
from squads._interactions import ITEM_SKILL_VIEW_NAME, SYSTEM_SKILL_VIEW_NAMES
from squads._itemfile import read_frontmatter
from squads._models import _markers as markers
from squads._models._config import SquadsConfig
from squads._paths import SquadPaths
from squads._sections import get_section, replace_frontmatter, replace_section
from squads._services._service import Service
from squads._workflow import load_workflow_spec
from squads._workflow._models import WorkflowSpec

pytestmark = pytest.mark.anyio

_FROM_SCHEMA = "0.14"
_LEGACY_PROSE = "# Stored Name\n\nA stale pre-0.14 rendering."


async def _downgraded(project, *, spec: WorkflowSpec | None = None) -> Service:
    """A fresh ``Service`` bound to the same squad, with its on-disk ``schema_version``
    hand-rewritten to :data:`_FROM_SCHEMA`, simulating a squad from before this migration.
    *spec* lets a caller pass a project-declared type the bundled default wouldn't see."""
    cfg_path = project.config_path
    text = await read_text(cfg_path)
    current = project.config.schema_version
    text = text.replace(f'schema_version = "{current}"', f'schema_version = "{_FROM_SCHEMA}"')
    await write_text(cfg_path, text)
    with cfg_path.open("rb") as fh:
        cfg = SquadsConfig.from_toml_dict(tomllib.load(fh))
    sp = SquadPaths(root=project.root, squad_dir=project.squad_dir, config=cfg)
    return Service(sp, spec=spec)


async def _text(paths: SquadPaths, item) -> str:
    return await read_text(paths.abspath(item.path))


async def _write_body(paths: SquadPaths, item, body: str) -> None:
    text = await _text(paths, item)
    await write_text(paths.abspath(item.path), replace_section(text, markers.BODY, body))


def _region(text: str) -> str:
    return (get_section(text, markers.BODY) or "").strip()


_WIDGET_OVERRIDE = (
    '[lifecycles.widget]\ninitial = "Open"\n[lifecycles.widget.transitions]\nOpen = ["Done"]\n'
    'Done = []\n\n[items.widget]\nprefix = "WID"\nfolder = "widgets"\nlifecycle = "widget"\n'
)


def _declare_widget_type(svc) -> WorkflowSpec:
    """Declares a project-level ``widget`` type through
    ``.overrides/workflow.toml`` — never a bundled type."""
    override_dir = svc.paths.squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(_WIDGET_OVERRIDE, encoding="utf-8")
    return load_workflow_spec(squad_dir=svc.paths.squad_dir)


# --------------------------------------------------------------------------- in-scope shapes


async def test_a_roles_legacy_prose_body_is_reclaimed_onto_its_tag(project, svc) -> None:
    role = await svc.roster_item("role", "manager")
    assert role is not None
    await _write_body(svc.paths, role, _LEGACY_PROSE)

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15") == 1
    assert _region(await _text(svc.paths, role)) == markers.open_marker(
        markers.view_tag("role_definition")
    )


@pytest.mark.parametrize("slug", sorted(SYSTEM_SKILL_VIEW_NAMES))
async def test_a_permanently_system_skills_legacy_prose_body_is_reclaimed(
    project, svc, slug: str
) -> None:
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", slug)
    assert skill is not None
    await _write_body(svc.paths, skill, _LEGACY_PROSE)

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15") == 1
    view_name = SYSTEM_SKILL_VIEW_NAMES[slug]
    assert _region(await _text(svc.paths, skill)) == markers.open_marker(
        markers.view_tag(view_name)
    )


@pytest.mark.gate_for("squads/_migrations/_v0_14_to_v0_15.py::_reclaim_legacy_roster_bodies")
async def test_several_roles_and_skills_in_one_run_are_all_reclaimed_and_counted(
    project, svc
) -> None:
    """Every in-scope role/system-skill in one run is reclaimed and counted together."""
    await svc.seed_bundled_skills()
    role = await svc.roster_item("role", "manager")
    assert role is not None
    await _write_body(svc.paths, role, _LEGACY_PROSE)
    reclaimed = [(role, "role_definition")]
    for slug in sorted(SYSTEM_SKILL_VIEW_NAMES):
        skill = await svc.roster_item("skill", slug)
        assert skill is not None
        await _write_body(svc.paths, skill, _LEGACY_PROSE)
        reclaimed.append((skill, SYSTEM_SKILL_VIEW_NAMES[slug]))

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15") == len(reclaimed)
    for item, view_name in reclaimed:
        region = _region(await _text(svc.paths, item))
        assert region == markers.open_marker(markers.view_tag(view_name))


async def test_a_per_item_type_skills_legacy_shaped_body_is_reclaimed_onto_its_tag(
    project, svc
) -> None:
    """A per-item-type ``sq-<type>`` skill is in scope too, same as a role or system skill."""
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "sq-task")
    assert skill is not None
    await _write_body(svc.paths, skill, _LEGACY_PROSE)

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15") == 1
    assert _region(await _text(svc.paths, skill)) == markers.open_marker(
        markers.view_tag(ITEM_SKILL_VIEW_NAME)
    )


# --------------------------------------------------- project-declared or later-bundled types


async def test_a_project_declared_types_skill_is_overwritten_like_any_other(project, svc) -> None:
    """A project-declared type's skill is overwritten unconditionally, same as any other."""
    skill = await svc.add_skill("sq-widget", description="our widget runbook")
    await svc.set_body(skill.id, "Hand-written widget runbook: step 1, step 2.")
    declared_spec = _declare_widget_type(svc)

    down = await _downgraded(project, spec=declared_spec)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15") == 1
    assert _region(await _text(svc.paths, skill)) == markers.open_marker(
        markers.view_tag(ITEM_SKILL_VIEW_NAME)
    )


async def test_a_project_declared_types_marker_shaped_skill_is_skipped_like_any_other(
    project, svc
) -> None:
    """Marker-shaped content is skipped for a project-declared type's skill too."""
    skill = await svc.add_skill("sq-widget", description="our widget runbook")
    await _write_body(
        svc.paths, skill, f"stray content {markers.open_marker('something-unexpected')}"
    )
    declared_spec = _declare_widget_type(svc)
    before = await _text(svc.paths, skill)

    down = await _downgraded(project, spec=declared_spec)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15", 0) == 0
    assert run.skipped.get("0.15", []).count(skill.id) == 1
    assert await _text(svc.paths, skill) == before


async def test_a_project_declared_types_already_tagged_skill_is_not_reported_at_all(
    project, svc
) -> None:
    """A skill that already carries its tag needs no action, whatever its type."""
    skill = await svc.add_skill("sq-widget", description="our widget runbook")
    declared_spec = _declare_widget_type(svc)
    await _write_body(svc.paths, skill, markers.open_marker(markers.view_tag(ITEM_SKILL_VIEW_NAME)))
    before = await _text(svc.paths, skill)

    down = await _downgraded(project, spec=declared_spec)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15", 0) == 0
    assert skill.id not in run.skipped.get("0.15", [])
    assert await _text(svc.paths, skill) == before


async def test_a_skill_matching_a_type_bundled_after_it_was_written_is_overwritten(
    project, svc
) -> None:
    """A skill whose slug matches a type bundled only after the file was written is overwritten
    unconditionally too."""
    skill = await svc.add_skill("sq-milestone", description="our own milestone runbook")
    await _write_body(svc.paths, skill, "Hand-written milestone runbook: step 1, step 2.")

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15") == 1
    assert _region(await _text(svc.paths, skill)) == markers.open_marker(
        markers.view_tag(ITEM_SKILL_VIEW_NAME)
    )


# --------------------------------------------------------------------------- out-of-scope shapes


async def test_a_custom_skills_authored_body_is_left_untouched(project, svc) -> None:
    skill = await svc.add_skill("Release Runbook", description="Ship a release safely.")
    await svc.set_body(skill.id, _LEGACY_PROSE)
    before = await _text(svc.paths, skill)

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15", 0) == 0
    assert await _text(svc.paths, skill) == before


# --------------------------------------------------------------------------- shape coverage


async def test_an_empty_role_body_is_left_to_the_standing_sweep_not_this_step(project, svc) -> None:
    """An empty body is left to the standing sweep, never this one-time reclaim's job."""
    role = await svc.roster_item("role", "manager")
    assert role is not None
    await _write_body(svc.paths, role, "")

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15", 0) == 0


async def test_an_already_tagged_role_body_is_left_untouched(project, svc) -> None:
    role = await svc.roster_item("role", "manager")
    assert role is not None
    before = await _text(svc.paths, role)

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15", 0) == 0
    assert await _text(svc.paths, role) == before


async def test_a_marker_shaped_role_body_is_skipped_and_reported_not_overwritten(
    project, svc
) -> None:
    role = await svc.roster_item("role", "manager")
    assert role is not None
    await _write_body(
        svc.paths, role, f"stray content {markers.open_marker('something-unexpected')}"
    )
    before = await _text(svc.paths, role)

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15", 0) == 0
    assert role.id in run.skipped.get("0.15", [])
    assert await _text(svc.paths, role) == before


async def test_a_region_less_role_body_is_skipped_and_reported_not_raised(project, svc) -> None:
    """A hand-deleted ``sq:body`` marker pair must not raise, and is named in ``skipped``."""
    role = await svc.roster_item("role", "manager")
    assert role is not None
    text = await _text(svc.paths, role)
    text = text.replace(f"{markers.open_marker(markers.BODY)}\n", "").replace(
        f"{markers.close_marker(markers.BODY)}\n", ""
    )
    await write_text(svc.paths.abspath(role.path), text)

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15", 0) == 0
    assert role.id in run.skipped.get("0.15", [])
    assert _region(await _text(svc.paths, role)) == markers.open_marker(
        markers.view_tag("role_definition")
    )


async def test_a_marker_shaped_skips_own_remedy_names_the_four_step_sequence(project, svc) -> None:
    """A marker-shaped skip's remedy names the four-step sequence, never `view disable` alone."""
    role = await svc.roster_item("role", "manager")
    assert role is not None
    await _write_body(
        svc.paths, role, f"{_LEGACY_PROSE} {markers.open_marker('something-unexpected')}"
    )

    down = await _downgraded(project)
    run = await down.run_pending_migrations()
    assert role.id in run.skipped.get("0.15", [])

    await _write_body(down.paths, role, _LEGACY_PROSE)
    issues = await down.check()
    matches = [i for i in issues if "missing seeded view tag" in i.message]
    assert matches, [i.message for i in issues]
    message = matches[0].message
    assert "drop 'role_definition' from [selected]" in message
    assert "restore 'role_definition' to [selected]" in message
    assert "view add role_definition" in message
    assert "view disable" not in message


async def test_a_rerun_after_reclaiming_reports_zero_and_writes_nothing(project, svc) -> None:
    role = await svc.roster_item("role", "manager")
    assert role is not None
    await _write_body(svc.paths, role, _LEGACY_PROSE)

    down = await _downgraded(project)
    await down.run_pending_migrations()
    reclaimed = await _text(svc.paths, role)

    from squads._migrations._v0_14_to_v0_15 import migrate
    from squads._paths import resolve as resolve_squad_paths

    fresh_paths = resolve_squad_paths(client_cwd=project.root)
    outcome = await migrate(fresh_paths)

    assert outcome.count == 0
    assert await _text(svc.paths, role) == reclaimed


async def test_a_freshly_initialised_corpus_needs_no_reclaim(project, svc) -> None:
    """A freshly initialised corpus needs no reclaim."""
    await svc.seed_bundled_skills()

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15", 0) == 0


# --------------------------------------------------------------------------- mid-chain skew


async def test_reclaims_every_role_and_skill_across_a_real_multi_runner_chain(tmp_path) -> None:
    """A corpus reaching current through several runners in one run reclaims every role
    and skill, none skipped."""
    src = Path(__file__).parent.parent / "fixtures" / "corpus" / "v0_7"
    assert src.is_dir(), f"corpus fixture not found at {src}"
    dst = tmp_path / "v0_7"
    shutil.copytree(src, dst)

    with (dst / ".squads.toml").open("rb") as fh:
        cfg = SquadsConfig.from_toml_dict(tomllib.load(fh))
    paths = SquadPaths(root=dst, squad_dir=dst / cfg.squad_dir, config=cfg)
    down = Service(paths)

    run = await down.run_pending_migrations()

    assert run.skipped.get("0.15", []) == []
    role = await down.roster_item("role", "dev-agent")
    assert role is not None
    assert _region(await _text(down.paths, role)) == markers.open_marker(
        markers.view_tag("role_definition")
    )
    for slug, view_name in (("greeting", "greeting_skill"), ("squads", "squads_skill")):
        skill = await down.roster_item("skill", slug)
        assert skill is not None
        assert _region(await _text(down.paths, skill)) == markers.open_marker(
            markers.view_tag(view_name)
        )


# --------------------------------------------------------------------------- modified_session


async def test_a_migrated_body_with_no_ambient_session_carries_no_modified_session_key(
    project, svc
) -> None:
    """Outside a session, a reclaimed file carries no ``modified_session`` key at all."""
    role = await svc.roster_item("role", "manager")
    assert role is not None
    await _write_body(svc.paths, role, _LEGACY_PROSE)

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15") == 1
    frontmatter = read_frontmatter(path=svc.paths.abspath(role.path))
    assert "modified_session" not in frontmatter


async def test_a_migrated_body_that_already_had_modified_session_keeps_its_value(
    project, svc
) -> None:
    """A file that already carried a ``modified_session`` value keeps it, with no session id
    to overwrite it."""
    role = await svc.roster_item("role", "manager")
    assert role is not None
    await _write_body(svc.paths, role, _LEGACY_PROSE)
    path = svc.paths.abspath(role.path)
    fm = read_frontmatter(path=path)
    fm["modified_session"] = "sid-preexisting"
    await write_text(path, replace_frontmatter(await read_text(path), fm))
    assert read_frontmatter(path=path)["modified_session"] == "sid-preexisting"

    down = await _downgraded(project)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15") == 1
    assert read_frontmatter(path=path)["modified_session"] == "sid-preexisting"


async def test_a_migrated_body_with_an_ambient_session_records_it(project, svc) -> None:
    """When a real session id is seeded, it is written."""
    role = await svc.roster_item("role", "manager")
    assert role is not None
    await _write_body(svc.paths, role, _LEGACY_PROSE)

    down = await _downgraded(project)
    actor.seed_session("sid-migrating", None)
    run = await down.run_pending_migrations()

    assert run.changed.get("0.15") == 1
    assert read_frontmatter(path=svc.paths.abspath(role.path))["modified_session"] == (
        "sid-migrating"
    )
