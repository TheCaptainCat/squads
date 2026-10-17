"""``sq migrate up`` gives every role and skill that stores no ``origin`` the one the rule answers,
keeps one that is stored, and a second run or a repair changes nothing.

Table A crosses corpus shape with step on the developer fixture (templated, overridden, retired,
declared and suffixed roles). Table B starts from a freshly initialised squad that holds every
shape, strips the stamp and the schema version back to 0.15, and requires the migration to write
exactly the bytes a fresh init wrote.
"""

import hashlib
import json
import re
import shutil
import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest

from squads import __version__
from squads._itemfile import read_frontmatter
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_CORPUS = Path(__file__).parent.parent / "fixtures" / "corpus"


def _origins(root: Path) -> dict[str, object]:
    """The origin each role and skill file stores, by file name."""
    out: dict[str, object] = {}
    for path in sorted(root.rglob("*.md")):
        front = read_frontmatter(text=path.read_text(encoding="utf-8"), source=path.name)
        if front.get("type") in ("role", "skill"):
            out[path.name] = front.get("origin")
    return out


def _indexed(root: Path) -> dict[str, object]:
    index = json.loads((root / ".squads.json").read_text(encoding="utf-8"))
    return {
        str(i["slug"]): i.get("attributes", {}).get("origin")
        for i in index["items"].values()
        if i["type"] in ("role", "skill")
    }


def _hashes(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.name not in (".reflog.jsonl", ".squads.json")
    }


def _declare_builder(root: Path) -> None:
    path = root / ".overrides" / "roles" / "builder.toml"
    path.write_text(path.read_text(encoding="utf-8") + 'capabilities = ["dev"]\n', "utf-8")


def _store_project_on_manager(root: Path) -> None:
    path = next(root.rglob("ROLE-*-manager.md"))
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("\n---\n", "\norigin: project\n---\n", 1), encoding="utf-8")


def _nothing(root: Path) -> None:
    return None


BASE: dict[str, object] = {
    "ROLE-000001-manager.md": "system",
    "ROLE-000002-python-dev.md": "system",
    "ROLE-000003-go-dev.md": "system",
    "ROLE-000004-rust-dev.md": "system",
    "ROLE-000005-legacy-dev.md": "project",
    "ROLE-000006-old-dev.md": "project",
    "ROLE-000007-builder.md": "project",
}

#: shape -> (edit applied to the copy, expected origin by role file)
SHAPES: dict[str, tuple[Callable[[Path], None], dict[str, object]]] = {
    "templated-overridden-retired-suffixed-and-project-roles": (_nothing, BASE),
    "a-declared-developer": (_declare_builder, BASE),
    "an-origin-already-stored": (
        _store_project_on_manager,
        {**BASE, "ROLE-000001-manager.md": "project"},
    ),
}


@pytest.mark.parametrize("shape", list(SHAPES))
async def test_every_role_gets_the_rule_origin_across_the_steps(
    shape, tmp_path, monkeypatch, invoke
) -> None:
    edit, expected = SHAPES[shape]
    root = tmp_path / "squad"
    shutil.copytree(_CORPUS / "v0_15_developers", root)
    edit(root)
    monkeypatch.chdir(root)

    first = await invoke(["migrate", "up"])

    assert first.exit_code == 0, first.output
    assert _origins(root) == expected
    assert re.search(r"\d+ role\(s\) stamped origin (system|project)", first.output)
    migrated = _hashes(root)
    index_origins = _indexed(root)
    assert index_origins == {
        slug: expected[name]
        for name in expected
        for slug in (name.split("-", 2)[2].removesuffix(".md"),)
    }

    second = await invoke(["migrate", "up"])
    assert second.exit_code == 0, second.output
    assert _hashes(root) == migrated

    (root / ".squads.json").unlink()
    rebuilt = await invoke(["repair"])
    assert rebuilt.exit_code == 0, rebuilt.output
    assert _hashes(root) == migrated
    assert _indexed(root) == index_origins
    checked = await invoke(["check"])
    assert checked.exit_code == 0, checked.output


_ROLE_FILE = (
    'full_name = "{name}"\ntitle = "{slug}"\n'
    'description = "A declared role."\nmission = "A declared role."\n'
)


@pytest.fixture
async def fresh_squad(tmp_path, monkeypatch, frozen_time, invoke):
    """A fresh init holding every shape: bundled and overridden roles, templated and declared
    developers, a project role, bundled and generated skills and a project skill."""
    monkeypatch.chdir(tmp_path)
    paths = (await service.init(root=tmp_path, roles_spec="all")).paths
    overrides = paths.squad_dir / ".overrides" / "roles"
    overrides.mkdir(parents=True, exist_ok=True)
    stamp = f"# squads:override-base:{__version__}\n"
    (overrides / "architect.toml").write_text(stamp + 'full_name = "Renamed"\n', encoding="utf-8")
    (overrides / "auditor-dev.toml").write_text(
        stamp + _ROLE_FILE.format(name="Auditor", slug="auditor-dev") + 'capabilities = ["dev"]\n',
        encoding="utf-8",
    )
    (overrides / "analyst.toml").write_text(
        stamp + _ROLE_FILE.format(name="Analyst", slug="analyst"), encoding="utf-8"
    )
    for args in (
        ["dev", "add", "--tech", "rust"],
        ["role", "activate", "auditor-dev"],
        ["role", "activate", "analyst"],
        ["skill", "add", "Release Runbook", "--desc", "Ship it."],
        ["role", "devops", "status", "Archived"],
    ):
        result = await invoke(args)
        assert result.exit_code == 0, result.output
    return paths


async def test_migrating_a_stripped_squad_writes_the_bytes_a_fresh_init_wrote(
    fresh_squad, invoke
) -> None:
    root = fresh_squad.squad_dir
    config = fresh_squad.root / ".squads.toml"
    fresh = _hashes(root)
    fresh_origins = _origins(root)
    assert set(fresh_origins.values()) == {"system", "project"}

    for path in root.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        path.write_text(
            re.sub(r"^origin: .*\n", "", text, flags=re.M), encoding="utf-8", newline=""
        )
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            'schema_version = "0.16"', 'schema_version = "0.15"'
        ),
        encoding="utf-8",
    )
    assert all(v is None for v in _origins(root).values())

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert tomllib.loads(config.read_text(encoding="utf-8"))["schema_version"] == "0.16"
    assert _origins(root) == fresh_origins
    changed = {k for k, v in _hashes(root).items() if fresh.get(k) != v}
    assert changed <= {".squads.toml"}, changed
    again = _hashes(root)
    assert (await invoke(["migrate", "up"])).exit_code == 0
    assert _hashes(root) == again
    synced = await invoke(["sync"])
    assert synced.exit_code == 0, synced.output
    assert _origins(root) == fresh_origins
    checked = await invoke(["check"])
    assert checked.exit_code == 0, checked.output


async def test_the_changelog_prints_the_origin_section_once_after_the_others(invoke) -> None:
    result = await invoke(["migrate", "chlog", "v0.15.0..v0.16.0"])

    assert result.exit_code == 0, result.output
    heading = "Every role and skill records its origin"
    assert result.output.count(heading) == 1
    assert result.output.index("A developer is a role that declares") < result.output.index(heading)
