"""``sq migrate up`` gives every skill file a discussion region, and a fresh squad already has one.

One table: skill file shape by step. A fresh squad holds every kind of skill; each shape strips
the region (and for one shape the stamp too) back to what a 0.15 squad stored, the schema is set
back to 0.15, and the migration must write exactly the bytes a fresh init wrote (in the file's
own line endings), touch no other file, and change nothing on a second run or after a repair.
"""

import hashlib
import re
from collections.abc import Callable
from pathlib import Path

import pytest

from squads._services import _service as service

pytestmark = pytest.mark.anyio

REGION = "\n## Discussion\n\n<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"


def _strip(text: str) -> str:
    assert REGION in text
    return text.replace(REGION, "", 1)


def _crlf(text: str) -> str:
    return text.replace("\n", "\r\n")


def _unstamped(text: str) -> str:
    return re.sub(r"^origin: .*\n", "", _strip(text), flags=re.M)


def _keep(text: str) -> str:
    return text


def _with_comment(text: str) -> str:
    return text.replace("<!-- sq:discussion -->\n", "<!-- sq:discussion -->\n- a note\n", 1)


#: shape -> (skill slug, the stored form of the fresh file, the form the migration leaves)
SHAPES: dict[str, tuple[str, Callable[[str], str], Callable[[str], str]]] = {
    "a-bundled-skill": ("squads", _strip, _keep),
    "a-generated-skill": ("sq-task", _strip, _keep),
    "a-project-skill-with-an-authored-body": ("release-runbook", _strip, _keep),
    "a-skill-that-already-has-the-region": ("sq-bug", _with_comment, _with_comment),
    "a-crlf-file": ("sq-epic", lambda t: _crlf(_strip(t)), _crlf),
    "a-file-without-a-final-newline": ("sq-guide", lambda t: _strip(t).rstrip("\n"), _keep),
    "a-file-with-no-stamp": ("sq-memory", _unstamped, _keep),
}


def _file(root: Path, slug: str) -> Path:
    return next(root.rglob(f"SKILL-*-{slug}.md"))


def _hashes(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.name not in (".reflog.jsonl", ".squads.json")
    }


@pytest.fixture
async def fresh(tmp_path, monkeypatch, frozen_time, invoke):
    monkeypatch.chdir(tmp_path)
    paths = (await service.init(root=tmp_path, roles_spec="all")).paths
    for args in (
        ["skill", "add", "Release Runbook", "--desc", "Ship a release."],
        ["skill", "release-runbook", "body", "-m", "Run the release checklist."],
    ):
        result = await invoke(args)
        assert result.exit_code == 0, result.output
    return paths


def _write(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def _read(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


async def test_every_skill_of_a_fresh_squad_has_the_region(fresh) -> None:
    files = list(fresh.squad_dir.rglob("SKILL-*.md"))
    assert len(files) > 10
    for path in files:
        assert REGION in _read(path), path.name


@pytest.mark.parametrize("shape", list(SHAPES))
async def test_migrating_writes_the_bytes_a_fresh_init_wrote(fresh, invoke, shape) -> None:
    slug, stored, after = SHAPES[shape]
    root = fresh.root
    config = root / ".squads.toml"
    target = _file(root, slug)
    fresh_text = _read(target)
    _write(target, stored(fresh_text))
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            'schema_version = "0.16"', 'schema_version = "0.15"'
        ),
        encoding="utf-8",
    )
    before = _hashes(root)
    lacking = stored(fresh_text) != after(fresh_text)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert ("1 skill(s) given a discussion region" in result.output) is lacking
    assert _read(target) == after(fresh_text)
    migrated = _hashes(root)
    changed = {k for k in migrated if before.get(k) != migrated[k]}
    assert changed == {".squads.toml", *([target.relative_to(root).as_posix()] if lacking else [])}

    again = await invoke(["migrate", "up"])
    assert again.exit_code == 0, again.output
    assert _hashes(root) == migrated
    (fresh.squad_dir / ".squads.json").unlink()
    rebuilt = await invoke(["repair"])
    assert rebuilt.exit_code == 0, rebuilt.output
    assert _hashes(root) == migrated
    synced = await invoke(["sync"])
    assert synced.exit_code == 0, synced.output
    assert _hashes(root) == migrated
    checked = await invoke(["check"])
    assert checked.exit_code == 0, checked.output
