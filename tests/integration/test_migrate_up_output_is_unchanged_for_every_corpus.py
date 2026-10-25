"""``sq migrate up`` over each frozen corpus, under a frozen clock, writes the files it always
has: every file the run adds or changes is compared, as text, with the reviewed copy under
``tests/goldens/migrated_corpus/``, and every file it removes is listed in that corpus's
``REMOVED.txt``. Files the run leaves alone are not recorded; the corpus fixture is their
reference. The reflog is left out, since it records the acting session.

A file several corpora write identically (the rendered surface) is stored once under
``_shared/`` and named in each corpus's ``SHARED.txt``; a corpus keeps its own copy only of what
differs. Covers squads without overrides only. A template edit or a schema bump legitimately
changes the copies: regenerate with ``UPDATE_GOLDENS=1 uv run pytest`` on this module and
review the diff of the golden files as the change.
"""

import difflib
import os
import shutil
import tomllib
from collections import Counter
from pathlib import Path

import pytest

from _helpers import make_service
from squads._models._config import SquadsConfig
from squads._paths import SquadPaths

pytestmark = pytest.mark.anyio

_TESTS = Path(__file__).parent.parent
_CORPUS_DIR = _TESTS / "fixtures" / "corpus"
_GOLDEN_DIR = _TESTS / "goldens" / "migrated_corpus"
_SHARED_DIR = _GOLDEN_DIR / "_shared"
_UPDATE = os.getenv("UPDATE_GOLDENS") == "1"
_UNRECORDED = ".reflog.jsonl"
_REMOVED = "REMOVED.txt"
_SHARED = "SHARED.txt"
_LISTS = frozenset({_REMOVED, _SHARED})
_CORPORA = sorted(p.name for p in _CORPUS_DIR.iterdir() if p.is_dir())

type Written = dict[str, str]


def _files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != _UNRECORDED
    }


async def _migrate(corpus: str, tmp_path: Path) -> tuple[Written, list[str]]:
    """What migrating *corpus* adds or changes (as text), and what it removes."""
    root = tmp_path / corpus
    shutil.copytree(_CORPUS_DIR / corpus, root)
    with (root / ".squads.toml").open("rb") as fh:
        cfg = SquadsConfig.from_toml_dict(tomllib.load(fh))
    paths = SquadPaths(root=root, squad_dir=root / cfg.squad_dir, config=cfg)
    before = _files(root)
    await make_service(paths).run_pending_migrations()
    after = _files(root)
    written = {n: d.decode("utf-8") for n, d in after.items() if before.get(n) != d}
    return written, sorted(set(before) - set(after))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


def _record(results: dict[str, tuple[Written, list[str]]]) -> None:
    """Store each content several corpora share once, and the rest per corpus."""
    shutil.rmtree(_GOLDEN_DIR, ignore_errors=True)
    counts: dict[str, Counter[str]] = {}
    for written, _ in results.values():
        for name, text in written.items():
            counts.setdefault(name, Counter())[text] += 1
    shared: Written = {}
    for name, tally in counts.items():
        text, n = min(tally.items(), key=lambda kv: (-kv[1], kv[0]))
        if n > 1:
            shared[name] = text
            _write(_SHARED_DIR / name, text)
    for corpus, (written, removed) in results.items():
        golden = _GOLDEN_DIR / corpus
        used = sorted(n for n, t in written.items() if shared.get(n) == t)
        for name, text in written.items():
            if name not in used:
                _write(golden / name, text)
        _write(golden / _SHARED, "".join(f"{n}\n" for n in used))
        _write(golden / _REMOVED, "".join(f"{n}\n" for n in removed))


def _expected(corpus: str) -> tuple[Written, list[str]]:
    golden = _GOLDEN_DIR / corpus
    expected = {
        p.relative_to(golden).as_posix(): p.read_text(encoding="utf-8")
        for p in sorted(golden.rglob("*"))
        if p.is_file() and p.name not in _LISTS
    }
    for name in (golden / _SHARED).read_text(encoding="utf-8").split("\n"):
        if name:
            expected[name] = (_SHARED_DIR / name).read_text(encoding="utf-8")
    return expected, (golden / _REMOVED).read_text(encoding="utf-8").split()


def _diff(name: str, expected: str, actual: str) -> str:
    lines = difflib.unified_diff(
        expected.splitlines(), actual.splitlines(), "golden", "migrated", lineterm="", n=2
    )
    return f"{name}:\n" + "\n".join(lines)


@pytest.mark.skipif(not _UPDATE, reason="set UPDATE_GOLDENS=1 to regenerate the reviewed copies")
async def test_regenerate_the_reviewed_copies(tmp_path: Path, frozen_time) -> None:
    _record({c: await _migrate(c, tmp_path / c) for c in _CORPORA})


@pytest.mark.skipif(_UPDATE, reason="the comparison rows would read the copies mid-rewrite")
@pytest.mark.parametrize("corpus", _CORPORA)
async def test_migrating_a_corpus_writes_the_files_it_always_has(
    corpus: str, tmp_path: Path, frozen_time
) -> None:
    written, removed = await _migrate(corpus, tmp_path)

    assert (_GOLDEN_DIR / corpus).is_dir(), f"no reviewed copy for {corpus}; set UPDATE_GOLDENS=1"
    expected, expected_removed = _expected(corpus)
    problems = [
        _diff(name, expected.get(name, ""), text)
        for name, text in written.items()
        if expected.get(name) != text
    ]
    problems += [
        f"{name}: in the golden but not written by the run"
        for name in sorted(expected.keys() - written.keys())
    ]
    assert not problems, "\n\n".join(problems)
    assert expected_removed == removed
