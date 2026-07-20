"""Schema 0.10 -> 0.11: a schema-stamp-only gate for the new `scopes` ref kind. The runner
itself touches no files; the whole point is to hard-stop a pre-0.11 client before it meets a
`scopes` edge it doesn't understand. This module proves the runner is a genuine no-op, that an
existing squad's skills (bundled, plus an authored custom skill and its role-scoping edges)
survive the upgrade unchanged, and that an old on-disk stamp is refused with a clear pointer to
`sq migrate up`.
"""

from pathlib import Path

import pytest

from squads._migrations._v0_10_to_v0_11 import migrate
from squads._models._schema import SCHEMA_VERSION
from squads._paths import SquadPaths

pytestmark = pytest.mark.anyio


def _file_snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.parts
    }


async def test_the_runner_is_a_genuine_noop_that_touches_no_files(project):
    before = _file_snapshot(project.root)

    acted = migrate(project)

    assert acted == 0
    assert _file_snapshot(project.root) == before


async def test_running_pending_migrations_on_a_squad_already_at_0_10_only_stamps_the_schema(
    project, frozen_time
):
    import tomllib

    cfg_path = project.config_path
    cfg_path.write_text(
        cfg_path.read_text(encoding="utf-8").replace(
            f'schema_version = "{SCHEMA_VERSION}"', 'schema_version = "0.10"'
        ),
        encoding="utf-8",
    )
    with cfg_path.open("rb") as fh:
        cfg = tomllib.load(fh)
    assert cfg["schema_version"] == "0.10"  # precondition

    from squads._models._config import SquadsConfig
    from squads._services._service import Service

    paths_010 = SquadPaths(
        root=project.root,
        squad_dir=project.squad_dir,
        config=SquadsConfig.from_toml_dict(cfg),
    )
    svc = Service(paths_010)

    applied = await svc.run_pending_migrations()

    assert [(m.from_schema, m.to_schema) for m in applied] == [("0.10", "0.11")]
    with cfg_path.open("rb") as fh:
        stamped = tomllib.load(fh)
    assert stamped["schema_version"] == SCHEMA_VERSION

    # A second run (against a freshly-resolved Service, the way a real CLI invocation
    # re-reads config each time) finds nothing pending — idempotent.
    with cfg_path.open("rb") as fh:
        cfg_after = tomllib.load(fh)
    paths_011 = SquadPaths(
        root=project.root,
        squad_dir=project.squad_dir,
        config=SquadsConfig.from_toml_dict(cfg_after),
    )
    again = await Service(paths_011).run_pending_migrations()
    assert again == []


async def test_upgrade_preserves_an_authored_custom_skill_body_and_its_role_scoping_edges(
    project, frozen_time
):
    import tomllib

    from squads._models._config import SquadsConfig
    from squads._services._service import Service

    svc = Service(project)
    manager = await svc.activate_role("manager")
    writer = await svc.activate_role("tech-writer")
    await svc.activate_role("devops")

    skill = await svc.add_skill("Release Runbook", description="Ship a release safely.")
    authored_body = "## Instructions\n\nCut the branch, tag it, then publish."
    await svc.set_body(skill.id, authored_body)
    await svc.link_role(skill.id, manager.id)
    await svc.link_role(skill.id, writer.id)

    before_body = await svc.read_body(skill.id)
    before_scope_refs = sorted(r for r in await svc.refs_out(skill.id) if r[1] == "scopes")
    before_manager_skills = await svc.resolved_skills_for_role("manager")
    before_writer_skills = await svc.resolved_skills_for_role("tech-writer")
    before_outsider_skills = await svc.resolved_skills_for_role("devops")
    assert "release-runbook" in before_manager_skills
    assert "release-runbook" in before_writer_skills
    assert "release-runbook" not in before_outsider_skills

    # Simulate an existing squad on the prior schema: downgrade the on-disk stamp only —
    # nothing else about the squad's content changes.
    cfg_path = project.config_path
    cfg_path.write_text(
        cfg_path.read_text(encoding="utf-8").replace(
            f'schema_version = "{SCHEMA_VERSION}"', 'schema_version = "0.10"'
        ),
        encoding="utf-8",
    )
    with cfg_path.open("rb") as fh:
        cfg = tomllib.load(fh)
    paths_010 = SquadPaths(
        root=project.root,
        squad_dir=project.squad_dir,
        config=SquadsConfig.from_toml_dict(cfg),
    )
    svc_010 = Service(paths_010)

    applied = await svc_010.run_pending_migrations()
    assert [m.to_schema for m in applied] == ["0.11"]

    with cfg_path.open("rb") as fh:
        stamped = tomllib.load(fh)
    assert stamped["schema_version"] == SCHEMA_VERSION

    # The authored body and the scopes edges survive unchanged.
    assert await svc_010.read_body(skill.id) == before_body == authored_body
    after_scope_refs = sorted(r for r in await svc_010.refs_out(skill.id) if r[1] == "scopes")
    assert after_scope_refs == before_scope_refs

    # No role's preloaded-skill set changed as a side effect of the upgrade alone.
    assert await svc_010.resolved_skills_for_role("manager") == before_manager_skills
    assert await svc_010.resolved_skills_for_role("tech-writer") == before_writer_skills
    assert await svc_010.resolved_skills_for_role("devops") == before_outsider_skills

    # `sq check` stays clean — invariant #1 (repair round-trips frontmatter-derivable state).
    errors = [i for i in await svc_010.check() if i.level == "error"]
    assert not errors


async def test_a_pre_0_11_stamp_hard_stops_an_ordinary_command_until_migrate_up_runs(
    project, invoke
):
    cfg_path = project.config_path
    cfg_path.write_text(
        cfg_path.read_text(encoding="utf-8").replace(
            f'schema_version = "{SCHEMA_VERSION}"', 'schema_version = "0.10"'
        ),
        encoding="utf-8",
    )

    blocked = await invoke(["list"])
    assert blocked.exit_code == 1
    assert "sq migrate up" in " ".join(blocked.output.split())

    done = await invoke(["migrate", "up"])
    assert done.exit_code == 0, done.output

    import tomllib

    with cfg_path.open("rb") as fh:
        assert tomllib.load(fh)["schema_version"] == SCHEMA_VERSION

    assert (await invoke(["list"])).exit_code == 0
