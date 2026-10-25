"""Every path that creates a role or skill stamps ``origin`` from the one rule, and ``sq sync``
neither rewrites an existing value nor fills a missing one.

One table: creation path by shape. Each row creates something, then compares the stored value
with what the rule answers for the same item and with ``sq check``. A second table runs ``sq sync``
twice after every row and hashes the tree: the second run changes nothing.
"""

import hashlib
import json
from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest

from _helpers import make_service
from squads import __version__
from squads._interactions._skills import item_origin
from squads._models import _attributes as attrs
from squads._rendering._engine import invalidate_squad_dir
from squads._services import _service as service
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

_ROLE_FILE = (
    'full_name = "{name}"\ntitle = "{slug}"\n'
    'description = "A declared role."\nmission = "A declared role."\n'
)

_NEW_TYPE = """\
[lifecycles.triage]
initial = "Open"
transitions = { Open = ["Done"], Done = [] }

[items.zebra]
prefix = "ZEB"
folder = "zebras"
lifecycle = "triage"
"""


def _override(squad_dir: Path, name: str, text: str) -> None:
    path = squad_dir / ".overrides" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# squads:override-base:{__version__}\n{text}", encoding="utf-8")
    invalidate_squad_dir(squad_dir)


def _declare_role(squad_dir: Path, slug: str, *, capabilities: list[str] | None = None) -> None:
    extra = f"capabilities = {json.dumps(capabilities)}\n" if capabilities else ""
    _override(
        squad_dir, f"roles/{slug}.toml", _ROLE_FILE.format(name=slug.title(), slug=slug) + extra
    )


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


async def _mismatches(svc, spec) -> list[str]:
    """Role and skill items whose stored origin differs from the rule (or is missing)."""
    return [
        f"{item.id} {item.slug}: {attrs.origin(item)}"
        for item in (await svc.store.load()).items.values()
        if item.type in ("role", "skill") and attrs.origin(item) != item_origin(item, spec)
    ]


Create = Callable[..., Awaitable[None]]


async def _init_all(project, svc, invoke) -> None:
    """Nothing to do: the fixture already ran ``sq init`` with every role and the skills."""


async def _sync_after_a_declared_type(project, svc, invoke) -> None:
    _override(project.squad_dir, "workflow.toml", _NEW_TYPE)
    assert (await invoke(["sync"])).exit_code == 0


async def _activate_bundled(project, svc, invoke) -> None:
    assert (await invoke(["role", "activate", "qa"])).exit_code == 0


async def _activate_project_declared(project, svc, invoke) -> None:
    _declare_role(project.squad_dir, "security-analyst")
    assert (await invoke(["role", "activate", "security-analyst"])).exit_code == 0


async def _dev_add(project, svc, invoke) -> None:
    assert (await invoke(["dev", "add", "--tech", "rust"])).exit_code == 0


async def _activate_declared_developer(project, svc, invoke) -> None:
    _declare_role(project.squad_dir, "auditor-dev", capabilities=["dev"])
    assert (await invoke(["role", "activate", "auditor-dev"])).exit_code == 0


async def _skill_add(project, svc, invoke) -> None:
    assert (await invoke(["skill", "add", "Release Runbook", "--desc", "x"])).exit_code == 0


async def _import(project, svc, invoke) -> None:
    events = [
        {"op": "create", "as": "manager", "type": "skill", "title": "Imported Skill"},
        {"op": "create", "as": "manager", "type": "role", "title": "Imported Role"},
    ]
    (project.root / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8"
    )
    assert (await invoke(["import", "events.jsonl"])).exit_code == 0


#: path -> (how to create, (slug, expected origin) pairs that must now exist)
PATHS: dict[str, tuple[Create, list[tuple[str, str]]]] = {
    "init-with-every-role": (_init_all, [("manager", "system"), ("squads", "system")]),
    "sync-after-a-declared-type": (_sync_after_a_declared_type, [("sq-zebra", "system")]),
    "activate-a-bundled-role": (_activate_bundled, [("qa", "system")]),
    "activate-a-project-declared-role": (
        _activate_project_declared,
        [("security-analyst", "project")],
    ),
    "dev-add": (_dev_add, [("rust-dev", "system")]),
    "activate-a-declared-developer": (_activate_declared_developer, [("auditor-dev", "project")]),
    "skill-add": (_skill_add, [("release-runbook", "project")]),
    "import-a-skill-and-a-role": (
        _import,
        [("imported-skill", "project"), ("imported-role", "project")],
    ),
}


@pytest.fixture
async def seeded(tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="all")
    return result.paths


@pytest.mark.parametrize("path", list(PATHS))
async def test_the_stored_origin_equals_the_rule_on_every_row(path, seeded, invoke) -> None:
    create, expected = PATHS[path]
    svc = make_service(seeded)
    await create(seeded, svc, invoke)

    assert await _mismatches(svc, load_workflow_spec(squad_dir=seeded.squad_dir)) == []
    for slug, origin in expected:
        item = await svc.roster_item("role", slug) or await svc.roster_item("skill", slug)
        assert item is not None, slug
        assert attrs.origin(item) == origin, slug
    checked = await invoke(["check"])
    assert checked.exit_code == 0, checked.output


@pytest.mark.parametrize("path", list(PATHS))
async def test_sync_is_a_fixed_point_after_every_creation_path(path, seeded, invoke) -> None:
    create, _expected = PATHS[path]
    svc = make_service(seeded)
    await create(seeded, svc, invoke)
    assert (await invoke(["sync"])).exit_code == 0

    before = _tree_hash(seeded.root)
    assert (await invoke(["sync"])).exit_code == 0

    assert _tree_hash(seeded.root) == before


@pytest.mark.parametrize("verb", ["sync", "repair"])
async def test_a_hand_set_origin_survives_sync_and_repair(verb, seeded, invoke) -> None:
    svc = make_service(seeded)
    role = await svc.roster_item("role", "manager")
    assert role is not None
    role_file = next(seeded.squad_dir.rglob("ROLE-*-manager.md"))
    role_file.write_text(
        role_file.read_text(encoding="utf-8").replace("origin: system", "origin: project"),
        encoding="utf-8",
    )

    assert (await invoke([verb])).exit_code == 0

    assert "origin: project" in role_file.read_text(encoding="utf-8")


async def test_sync_does_not_fill_a_missing_origin(seeded, invoke) -> None:
    role_file = next(seeded.squad_dir.rglob("ROLE-*-manager.md"))
    role_file.write_text(
        role_file.read_text(encoding="utf-8").replace("origin: system\n", ""), encoding="utf-8"
    )

    assert (await invoke(["sync"])).exit_code == 0

    assert "origin:" not in role_file.read_text(encoding="utf-8")
    checked = await invoke(["check"])
    assert "missing required attribute 'origin'" in checked.output


async def test_the_retired_key_sweep_keeps_origin(seeded, invoke) -> None:
    role_file = next(seeded.squad_dir.rglob("ROLE-*-manager.md"))
    before = role_file.read_text(encoding="utf-8")

    for verb in ("sync", "repair"):
        assert (await invoke([verb])).exit_code == 0

    assert role_file.read_text(encoding="utf-8") == before
