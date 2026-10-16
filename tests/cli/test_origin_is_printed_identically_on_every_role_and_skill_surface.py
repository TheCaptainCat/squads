"""``origin`` under one name on every role and skill surface, equal to what the file stores.

One squad holds every shape (bundled and overridden roles, a retired role, templated and declared
developers, project roles, bundled and generated skills, a skill of a type the spec dropped, a
system skill whose view the project dropped, a project skill). Each shape is read through every
surface, before and after the index is deleted and rebuilt by ``sq repair``, and must print the
value the item's file stores.
"""

import json
import re
from pathlib import Path

import pytest

from squads import __version__
from squads import _sections as sections
from squads._cli._common import console
from squads._rendering._engine import invalidate_squad_dir
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_ROLE_FILE = (
    'full_name = "{name}"\ntitle = "{slug}"\n'
    'description = "A declared role."\nmission = "A declared role."\n'
)

#: Drops the guide type and the greeting skill's view, and declares one type of the project's own.
_WORKFLOW = """\
[lifecycles.triage]
initial = "Open"
transitions = { Open = ["Done"], Done = [] }

[items.zebra]
prefix = "ZEB"
folder = "zebras"
lifecycle = "triage"

[selected]
items = [
  "epic", "feature", "task", "bug", "decision", "contract", "milestone",
  "review", "role", "skill", "operator", "zebra",
]
views = ["milestone_rollup", "role_definition", "squads_skill", "memory_skill", "item_skill"]
"""

#: role shape -> (slug, expected origin)
ROLES: dict[str, tuple[str, str]] = {
    "bundled": ("manager", "system"),
    "bundled-with-a-project-override": ("architect", "system"),
    "bundled-and-retired": ("devops", "system"),
    "templated-developer": ("rust-dev", "system"),
    "declared-developer": ("auditor-dev", "project"),
    "project-role": ("security-analyst", "project"),
    "project-role-ending-in-dev": ("sandbox-dev", "project"),
    "bundled-with-a-stored-origin-the-rule-would-not-give": ("qa", "project"),
}

#: skill shape -> (slug, expected origin)
SKILLS: dict[str, tuple[str, str]] = {
    "bundled": ("squads", "system"),
    "generated": ("sq-task", "system"),
    "generated-for-a-project-declared-type": ("sq-zebra", "system"),
    "generated-for-a-type-the-spec-dropped": ("sq-guide", "system"),
    "system-skill-whose-view-is-dropped": ("greeting", "system"),
    "project": ("release-runbook", "project"),
    "bundled-with-a-stored-origin-the-rule-would-not-give": ("sq-memory", "project"),
}


def _override(squad_dir: Path, name: str, text: str) -> None:
    path = squad_dir / ".overrides" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# squads:override-base:{__version__}\n{text}", encoding="utf-8")


@pytest.fixture
async def squad(tmp_path, monkeypatch, frozen_time, invoke):
    monkeypatch.chdir(tmp_path)
    paths = (await service.init(root=tmp_path, roles_spec="all")).paths
    squad_dir = paths.squad_dir

    async def run(*args: str) -> None:
        result = await invoke(list(args))
        assert result.exit_code == 0, result.output

    await run("dev", "add", "--tech", "rust")
    _override(
        squad_dir,
        "roles/auditor-dev.toml",
        _ROLE_FILE.format(name="Auditor", slug="auditor-dev") + 'capabilities = ["dev"]\n',
    )
    _override(
        squad_dir,
        "roles/security-analyst.toml",
        _ROLE_FILE.format(name="Sentinel", slug="security-analyst"),
    )
    _override(
        squad_dir, "roles/sandbox-dev.toml", _ROLE_FILE.format(name="Sandbox", slug="sandbox-dev")
    )
    _override(squad_dir, "roles/architect.toml", 'full_name = "Renamed Architect"\n')
    invalidate_squad_dir(squad_dir)
    for slug in ("auditor-dev", "security-analyst", "sandbox-dev"):
        await run("role", "activate", slug)
    await run("role", "devops", "status", "Archived")
    await run("skill", "add", "Release Runbook", "--desc", "Ship a release.")
    _override(squad_dir, "workflow.toml", _WORKFLOW)
    invalidate_squad_dir(squad_dir)
    await run("sync")
    for folder, slug in (("roles", "qa"), ("skills", "sq-memory")):
        path = next((squad_dir / "agents" / folder).glob(f"*-{slug}.md"))
        path.write_text(
            path.read_text(encoding="utf-8").replace("origin: system", "origin: project"),
            encoding="utf-8",
        )
    await run("repair")
    return paths


def _file_origin(squad, item_type: str, slug: str) -> object:
    folder = "roles" if item_type == "role" else "skills"
    path = next((squad.squad_dir / "agents" / folder).glob(f"*-{slug}.md"))
    return sections.split_frontmatter(path.read_text(encoding="utf-8"))[0].get("origin")


async def _json(invoke, args: list[str]):
    result = await invoke([*args, "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def _cell(output: str, slug: str, column: str, next_column: str | None) -> str:
    lines = output.splitlines()
    header = next(line for line in lines if column in line and "Slug" in line)
    start = header.index(column)
    end = header.index(next_column) if next_column else None
    row = next(line for line in lines if line.split()[:1] == [slug])
    return row[start:end].strip()


def _panel_origin(output: str) -> str:
    match = re.search(r"origin: (\S+)", output)
    assert match, output
    return match.group(1)


ROLE_SURFACES = [
    "role list --json",
    "role list",
    "role show",
    "role show --json",
    "list -t role -a --json",
    "role catalog --json",
    "role catalog",
]
SKILL_SURFACES = ["skill show", "skill show --json", "list -t skill -a --json"]


async def _read(invoke, surface: str, kind: str, slug: str) -> object:
    if surface.endswith("--json"):
        base = surface.removesuffix(" --json").split()
        if base[0] == "list":
            rows = await _json(invoke, base)
        elif base[:2] == ["role", "show"] or base[:2] == ["skill", "show"]:
            return (await _json(invoke, [kind, slug, "show"])).get("origin")
        else:
            rows = await _json(invoke, base)
        return next((r.get("origin") for r in rows if r["slug"] == slug), "<no row>")
    if surface == "role list":
        out = (await invoke(["role", "list"])).output
        return _cell(out, slug, "Origin", "Live")
    if surface == "role catalog":
        out = (await invoke(["role", "catalog"])).output
        return _cell(out, slug, "Origin", None)
    result = await invoke([kind, slug, "show"])
    assert result.exit_code == 0, result.output
    return _panel_origin(result.output)


@pytest.fixture(params=["fresh", "after-repair"])
async def stage(request, squad, invoke, monkeypatch):
    monkeypatch.setattr(console, "width", 160)
    if request.param == "after-repair":
        (squad.squad_dir / ".squads.json").unlink()
        result = await invoke(["repair"])
        assert result.exit_code == 0, result.output
    return request.param


async def test_every_role_shape_prints_its_stored_origin_on_every_surface(
    squad, stage, invoke
) -> None:
    printed = {
        (shape, surface): await _read(invoke, surface, "role", ROLES[shape][0])
        for shape in ROLES
        for surface in ROLE_SURFACES
    }
    expected = {(shape, surface): ROLES[shape][1] for shape, surface in printed}
    assert {shape: _file_origin(squad, "role", ROLES[shape][0]) for shape in ROLES} == {
        shape: ROLES[shape][1] for shape in ROLES
    }
    assert printed == expected


async def test_every_skill_shape_prints_its_stored_origin_on_every_surface(
    squad, stage, invoke
) -> None:
    printed = {
        (shape, surface): await _read(invoke, surface, "skill", SKILLS[shape][0])
        for shape in SKILLS
        for surface in SKILL_SURFACES
    }
    expected = {
        (shape, surface): SKILLS[shape][1] for shape in SKILLS for surface in SKILL_SURFACES
    }
    assert {shape: _file_origin(squad, "skill", SKILLS[shape][0]) for shape in SKILLS} == {
        shape: SKILLS[shape][1] for shape in SKILLS
    }
    assert printed == expected


async def test_the_catalog_names_no_bundled_origin(squad, invoke) -> None:
    rows = await _json(invoke, ["role", "catalog"])
    assert {r["origin"] for r in rows} == {"system", "project"}, "a declared developer is project"
    slugs = {r["slug"] for r in rows}
    assert slugs >= {"rust-dev", "auditor-dev"}
    assert slugs >= {"security-analyst", "sandbox-dev"}


async def test_a_skill_show_payload_carries_origin_and_no_system_flag(squad, invoke) -> None:
    payload = await _json(invoke, ["skill", "squads", "show"])
    assert payload["origin"] == "system"
    assert "system" not in payload
