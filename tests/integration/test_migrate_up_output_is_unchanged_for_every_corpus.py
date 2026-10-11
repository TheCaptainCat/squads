"""``sq migrate up`` over each frozen corpus, under a frozen clock, writes the files it always
has: every file the run adds or changes is compared, as text, with the reviewed copy under
``tests/goldens/migrated_corpus/<corpus>/``, and every file it removes is listed in that
corpus's ``REMOVED.txt``. Files the run leaves alone are not recorded; the corpus fixture is
their reference. The reflog is left out, since it records the acting session.

Covers squads without overrides only. The copies include template-rendered files and the schema
stamp, so a template edit or a schema bump legitimately changes them: regenerate with
``UPDATE_GOLDENS=1 uv run pytest`` on this module and review the diff of the golden files
as the change.
"""

import difflib
import os
import shutil
import tomllib
from pathlib import Path

import pytest

from squads._models._config import SquadsConfig
from squads._paths import SquadPaths
from squads._services._service import Service

pytestmark = pytest.mark.anyio

_TESTS = Path(__file__).parent.parent
_CORPUS_DIR = _TESTS / "fixtures" / "corpus"
_GOLDEN_DIR = _TESTS / "goldens" / "migrated_corpus"
_UPDATE = os.getenv("UPDATE_GOLDENS") == "1"
_UNRECORDED = ".reflog.jsonl"
_REMOVED = "REMOVED.txt"


def _files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != _UNRECORDED
    }


def _written_by_the_run(before: dict[str, bytes], after: dict[str, bytes]) -> dict[str, str]:
    return {name: data.decode("utf-8") for name, data in after.items() if before.get(name) != data}


def _record(golden: Path, written: dict[str, str], removed: list[str]) -> None:
    shutil.rmtree(golden, ignore_errors=True)
    for name, text in written.items():
        target = golden / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="")
    (golden / _REMOVED).parent.mkdir(parents=True, exist_ok=True)
    (golden / _REMOVED).write_text("".join(f"{n}\n" for n in removed), encoding="utf-8")


def _diff(name: str, expected: str, actual: str) -> str:
    lines = difflib.unified_diff(
        expected.splitlines(), actual.splitlines(), "golden", "migrated", lineterm="", n=2
    )
    return f"{name}:\n" + "\n".join(lines)


@pytest.mark.parametrize("corpus", sorted(p.name for p in _CORPUS_DIR.iterdir() if p.is_dir()))
async def test_migrating_a_corpus_writes_the_files_it_always_has(
    corpus: str, tmp_path: Path, frozen_time
) -> None:
    root = tmp_path / corpus
    shutil.copytree(_CORPUS_DIR / corpus, root)
    with (root / ".squads.toml").open("rb") as fh:
        cfg = SquadsConfig.from_toml_dict(tomllib.load(fh))
    paths = SquadPaths(root=root, squad_dir=root / cfg.squad_dir, config=cfg)
    before = _files(root)

    await Service(paths).run_pending_migrations()

    after = _files(root)
    written = _written_by_the_run(before, after)
    removed = sorted(set(before) - set(after))
    golden = _GOLDEN_DIR / corpus
    if _UPDATE:
        _record(golden, written, removed)
    assert golden.is_dir(), f"no reviewed copy for {corpus}; run with UPDATE_GOLDENS=1"
    expected = {
        p.relative_to(golden).as_posix(): p.read_text(encoding="utf-8")
        for p in sorted(golden.rglob("*"))
        if p.is_file() and p.name != _REMOVED
    }
    problems = [
        _diff(name, expected.get(name, ""), text)
        for name, text in written.items()
        if expected.get(name) != text
    ]
    problems += [
        f"{name}: in the golden but not written by the run"
        for name in expected.keys() - written.keys()
    ]
    assert not problems, "\n\n".join(problems)
    assert (golden / _REMOVED).read_text(encoding="utf-8").split() == removed
