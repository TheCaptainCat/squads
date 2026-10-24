"""``sq migrate up`` rebuilds the index from the item files before its first runner, so every
runner reads one that mirrors the files; and it never stamps a squad holding an item file it
could not index. Driven through the service and through the CLI, over a squad stamped 0.14
whose milestone has no roll-up tag yet (the item the last runner enumerates from the index).
"""

import hashlib
import json
import re
import shutil
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from _helpers import make_unreadable_by_the_os
from squads._index._reconcile import ReconcileResult
from squads._migrations import _registry
from squads._models import _markers as markers
from squads._models._config import SquadsConfig
from squads._models._schema import SCHEMA_VERSION
from squads._paths import SquadPaths
from squads._services import _maintenance
from squads._services._service import Service

pytestmark = pytest.mark.anyio

_CORPUS_DIR = Path(__file__).parent.parent / "fixtures" / "corpus"
_MILE = "milestones/MILE-000011-ship-the-auth-module.md"
_TASK = "tasks/TASK-000003-implement-auth.md"
_TAG = markers.open_marker(markers.view_tag("milestone_rollup"))


def _paths_at(root: Path) -> SquadPaths:
    with (root / ".squads.toml").open("rb") as fh:
        cfg = SquadsConfig.from_toml_dict(tomllib.load(fh))
    return SquadPaths(root=root, squad_dir=root / cfg.squad_dir, config=cfg)


def _stamp(root: Path) -> str:
    return tomllib.loads((root / ".squads.toml").read_text(encoding="utf-8"))["schema_version"]


def _md_digest(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*.md"))
        if p.is_file()
    }


def _edit_index(root: Path, edit: Callable[[dict[str, Any]], None]) -> None:
    path = root / ".squads.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    edit(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def _entry(data: dict[str, Any], seq: int) -> dict[str, Any]:
    return next(v for k, v in data["items"].items() if int(str(k).rsplit("-", 1)[-1]) == seq)


@pytest.fixture
def squad(tmp_path: Path, frozen_time: object) -> Path:
    root = tmp_path / "v0_14"
    shutil.copytree(_CORPUS_DIR / "v0_14", root)
    return root


# --------------------------------------------------------------------------- index states


def _break_entry(**fields: Any) -> Callable[[Path], None]:
    return lambda root: _edit_index(root, lambda d: _entry(d, 11).update(fields))


def _write_index(root: Path, text: str) -> None:
    (root / ".squads.json").write_text(text, encoding="utf-8")


_INDEX_STATES: dict[str, Callable[[Path], None]] = {
    "consistent": lambda root: None,
    "missing": lambda root: (root / ".squads.json").unlink(),
    "not-json": lambda root: _write_index(root, "{nope"),
    "fails-the-model": lambda root: _write_index(root, '{"counter": "x"}'),
    "type-the-spec-lacks": _break_entry(type="zzz"),
    "status-the-spec-lacks": _break_entry(status="Nope"),
    "entry-whose-file-is-gone": lambda root: (root / _TASK).unlink(),
}


@pytest.mark.parametrize("state", _INDEX_STATES)
async def test_the_service_migrates_every_eligible_item_whatever_state_the_index_was_left_in(
    state: str, squad: Path
) -> None:
    _INDEX_STATES[state](squad)

    run = await Service(_paths_at(squad)).run_pending_migrations()

    assert _stamp(squad) == SCHEMA_VERSION
    assert run.changed["0.15"] >= 1
    assert _TAG in (squad / _MILE).read_text(encoding="utf-8")
    assert run.reconcile is not None


@pytest.mark.parametrize("state", ["missing", "not-json"])
async def test_the_cli_reconciles_a_missing_or_unparseable_index_and_says_so(
    state: str, squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    _INDEX_STATES[state](squad)
    monkeypatch.chdir(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert "index reconciled with the files: indexed" in result.output
    assert "MILE-11" in result.output
    assert _stamp(squad) == SCHEMA_VERSION


async def test_the_cli_prints_no_reconcile_line_on_a_consistent_squad(
    squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    monkeypatch.chdir(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert "index reconciled" not in result.output


async def test_the_reflog_line_names_the_entry_the_rebuild_dropped(
    squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    (squad / _TASK).unlink()
    monkeypatch.chdir(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert "dropped TASK-3" in result.output
    lines = [
        json.loads(x) for x in (squad / ".reflog.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    recorded = [x for x in lines if x["op"] == "migrate" and "reconcile" in x["delta"]]
    assert [x["delta"]["reconcile"]["missing"] for x in recorded] == [["TASK-3"]]


async def test_a_squad_already_at_the_current_schema_is_left_untouched(
    squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    monkeypatch.chdir(squad)
    first = await invoke(["migrate", "up"])
    assert first.exit_code == 0, first.output
    index_before = (squad / ".squads.json").read_bytes()
    files_before = _md_digest(squad)
    _break_current = (squad / ".squads.json").stat().st_mtime_ns

    second = await invoke(["migrate", "up"])

    assert second.exit_code == 0, second.output
    assert "nothing to migrate" in second.output
    assert (squad / ".squads.json").read_bytes() == index_before
    assert (squad / ".squads.json").stat().st_mtime_ns == _break_current
    assert _md_digest(squad) == files_before


# --------------------------------------------------------------------------- refusals


@dataclass(frozen=True)
class Damage:
    """Damage to one item file, how the OS error reads, and how to take it back."""

    apply: Callable[[Path, str], Callable[[], None]]
    cause: str


def _restore(path: Path, original: bytes) -> None:
    path.write_bytes(original)


def _rewrite(change: Callable[[str], str]) -> Callable[[Path, str], Callable[[], None]]:
    def _apply(root: Path, rel: str) -> Callable[[], None]:
        original = (root / rel).read_bytes()
        text = original.decode("utf-8")
        (root / rel).write_text(change(text), encoding="utf-8")
        return lambda: _restore(root / rel, original)

    return _apply


def _undecodable(root: Path, rel: str) -> Callable[[], None]:
    original = (root / rel).read_bytes()
    (root / rel).write_bytes(original + b"\xff\xfe\x00")
    return lambda: _restore(root / rel, original)


def _refused(root: Path, rel: str) -> Callable[[], None]:
    return make_unreadable_by_the_os(root / rel)


def _copy_into_the_folder(name: str) -> Callable[[Path, str], Callable[[], None]]:
    def _apply(root: Path, rel: str) -> Callable[[], None]:
        copy = (root / rel).parent / name
        shutil.copy(root / rel, copy)
        return copy.unlink

    return _apply


def _duplicate(root: Path, rel: str) -> Callable[[], None]:
    return _copy_into_the_folder(f"{Path(rel).stem}-copy.md")(root, rel)


_DAMAGE: dict[str, Damage] = {
    "undecodable-bytes": Damage(_undecodable, "not valid UTF-8"),
    "read-refused": Damage(_refused, "could not be read"),
    "malformed-yaml": Damage(
        _rewrite(lambda t: t.replace("---\n", "---\nbroken: [unclosed\n", 1)), "malformed"
    ),
    "id-gone": Damage(
        _rewrite(lambda t: re.sub(r"^id: .*\n", "", t, count=1, flags=re.M)), "no id"
    ),
    "field-type-invalid": Damage(
        _rewrite(lambda t: re.sub(r"^status: .*$", "status: [a, b]", t, count=1, flags=re.M)),
        "status",
    ),
    "id-claimed-twice": Damage(_duplicate, "also claimed by"),
    "id-copied-under-a-name-that-is-not-an-items": Damage(
        _copy_into_the_folder("notes.md"), "also claimed by"
    ),
    "no-frontmatter": Damage(_rewrite(lambda t: "# just prose\n"), "no id"),
}


class _Calls:
    def __init__(self) -> None:
        self.count = 0


def _count_runner_calls(monkeypatch: pytest.MonkeyPatch) -> _Calls:
    calls = _Calls()

    def _wrap(run: Any) -> Any:
        async def _counted(ctx: Any) -> Any:
            calls.count += 1
            return await run(ctx)

        return _counted

    import dataclasses

    monkeypatch.setattr(
        _maintenance,
        "MIGRATIONS",
        [dataclasses.replace(m, run=_wrap(m.run)) for m in _registry.MIGRATIONS],
    )
    return calls


def _no_sq_command_but_migrate_up(text: str) -> None:
    refusal = text[text.index("no migration has run") :]
    assert re.findall(r"`sq [^`]*`", refusal) == ["`sq migrate up`"]


@pytest.mark.parametrize("rel", [_MILE, _TASK], ids=["a-runner-reads-it", "no-runner-reads-it"])
@pytest.mark.parametrize("damage", _DAMAGE)
async def test_the_service_stops_before_any_runner_and_resumes_once_the_file_is_fixed(
    damage: str, rel: str, squad: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _count_runner_calls(monkeypatch)
    undo = _DAMAGE[damage].apply(squad, rel)
    before = _md_digest(squad)

    with pytest.raises(Exception, match="no migration has run") as excinfo:
        await Service(_paths_at(squad)).run_pending_migrations()

    message = str(excinfo.value)
    assert calls.count == 0
    assert _stamp(squad) == "0.14"
    assert _md_digest(squad) == before
    assert Path(rel).name in message
    assert _DAMAGE[damage].cause in message
    _no_sq_command_but_migrate_up(message)

    undo()
    run = await Service(_paths_at(squad)).run_pending_migrations()
    assert run.applied
    assert _stamp(squad) == SCHEMA_VERSION


@pytest.mark.parametrize("rel", [_MILE, _TASK], ids=["a-runner-reads-it", "no-runner-reads-it"])
@pytest.mark.parametrize("damage", _DAMAGE)
async def test_the_cli_exits_1_and_changes_nothing_when_an_item_file_cannot_be_indexed(
    damage: str, rel: str, squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    undo = _DAMAGE[damage].apply(squad, rel)
    before = _md_digest(squad)
    monkeypatch.chdir(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 1, result.output
    assert _stamp(squad) == "0.14"
    assert _md_digest(squad) == before
    assert Path(rel).name in result.output
    _no_sq_command_but_migrate_up(result.output)

    undo()
    again = await invoke(["migrate", "up"])
    assert again.exit_code == 0, again.output
    assert _stamp(squad) == SCHEMA_VERSION


async def test_an_unindexable_file_taken_out_of_the_squad_directory_lets_the_run_complete(
    squad: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    (squad / _TASK).write_bytes((squad / _TASK).read_bytes() + b"\xff")
    monkeypatch.chdir(squad)
    assert (await invoke(["migrate", "up"])).exit_code == 1

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    shutil.move(squad / _TASK, elsewhere / "TASK-000003-implement-auth.md")
    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert "dropped TASK-3" in result.output
    assert _stamp(squad) == SCHEMA_VERSION


async def test_the_refusal_carries_the_entry_forward_and_says_what_the_rebuild_did(
    squad: Path,
) -> None:
    (squad / _TASK).write_bytes((squad / _TASK).read_bytes() + b"\xff")
    (squad / "tasks/TASK-000099-new.md").write_text(
        "---\nid: TASK-99\nsequence_id: 99\ntype: task\ntitle: N\nstatus: Draft\n"
        "created_at: '2025-01-01T00:00:00Z'\nupdated_at: '2025-01-01T00:00:00Z'\n---\nb\n",
        encoding="utf-8",
    )

    with pytest.raises(Exception, match="no migration has run") as excinfo:
        await Service(_paths_at(squad)).run_pending_migrations()

    assert "indexed TASK-99" in str(excinfo.value)
    index = json.loads((squad / ".squads.json").read_text(encoding="utf-8"))
    assert _entry(index, 3)["title"] == "Implement auth"
    assert _entry(index, 99)["title"] == "N"
    assert index["schema_version"] == "0.14"


# --------------------------------------------------------------------------- convergence


def _tree(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.name != ".reflog.jsonl"
    }


async def _noop_reconcile(squad_dir: Path, store: Any, schema: str) -> tuple[Any, ReconcileResult]:
    return await store.load(validate_vocab=False), ReconcileResult()


@pytest.mark.parametrize("corpus", sorted(p.name for p in _CORPUS_DIR.iterdir() if p.is_dir()))
async def test_the_rebuild_changes_nothing_a_migration_produces_over_every_corpus(
    corpus: str, tmp_path: Path, frozen_time: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    with_rebuild = tmp_path / "with" / corpus
    without = tmp_path / "without" / corpus
    shutil.copytree(_CORPUS_DIR / corpus, with_rebuild)
    shutil.copytree(_CORPUS_DIR / corpus, without)

    await Service(_paths_at(with_rebuild)).run_pending_migrations()
    monkeypatch.setattr(_maintenance, "plan_reconcile", _noop_reconcile)
    await Service(_paths_at(without)).run_pending_migrations()

    assert _tree(with_rebuild) == _tree(without)


# --------------------------------------------------------------------------- stopped runs


_STRAY_DOC = "tasks/TASK-20240115-use-postgres.md"


def _stray_record(root: Path) -> None:
    (root / _STRAY_DOC).write_text("---\nid: TASK-20240115\ntitle: x\n---\nx\n", encoding="utf-8")


def _floors(root: Path) -> tuple[int, int]:
    data = json.loads((root / ".squads.json").read_text(encoding="utf-8"))
    return data["counter"], data["padding"]


async def test_a_refused_run_leaves_the_counter_and_padding_where_they_were(
    squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    before = _floors(squad)
    _stray_record(squad)
    monkeypatch.chdir(squad)

    refused = await invoke(["migrate", "up"])

    assert refused.exit_code == 1, refused.output
    assert _STRAY_DOC in refused.output
    assert _floors(squad) == before


async def test_a_refused_run_then_the_remedy_equals_a_first_run_on_the_fixed_squad(
    squad: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    fixed = tmp_path / "fixed"
    shutil.copytree(squad, fixed)
    monkeypatch.chdir(fixed)
    assert (await invoke(["migrate", "up"])).exit_code == 0

    _stray_record(squad)
    monkeypatch.chdir(squad)
    assert (await invoke(["migrate", "up"])).exit_code == 1
    (squad / _STRAY_DOC).unlink()
    assert (await invoke(["migrate", "up"])).exit_code == 0

    assert _floors(squad) == _floors(fixed)
    assert _floors(squad) == (11, 6)


async def test_what_a_stopped_run_dropped_stays_on_the_reflog_after_the_fix(
    squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    (squad / _TASK).unlink()
    (squad / _MILE).write_bytes((squad / _MILE).read_bytes() + b"\xff")
    monkeypatch.chdir(squad)
    assert (await invoke(["migrate", "up"])).exit_code == 1
    shutil.copy(_CORPUS_DIR / "v0_14" / _MILE, squad / _MILE)

    assert (await invoke(["migrate", "up"])).exit_code == 0

    lines = [
        json.loads(x) for x in (squad / ".reflog.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    dropped = [x for x in lines if x["delta"].get("reconcile", {}).get("missing") == ["TASK-3"]]
    assert len(dropped) == 1 and dropped[0]["op"] == "migrate"
    parsed = await invoke(["reflog", "--json"])
    assert parsed.exit_code == 0, parsed.output
    json.loads(parsed.output[parsed.output.index("[") :])


# --------------------------------------------------------------------------- locations


_ITEM = (
    "---\nid: {id}\nsequence_id: {seq}\ntype: {type}\ntitle: T\nslug: s\nstatus: {status}\n"
    "created_at: '2025-01-01T00:00:00Z'\nupdated_at: '2025-01-01T00:00:00Z'\n---\nbody\n"
)


def _put(root: Path, rel: str, content: str | bytes) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        (root / rel).write_bytes(content)
    else:
        (root / rel).write_text(content, encoding="utf-8")


def _archived_milestone_the_index_never_held(root: Path) -> None:
    _put(
        root,
        "archive/MILE-000030-old.md",
        _ITEM.format(id="MILE-30", seq=30, type="milestone", status="Draft"),
    )


def _copy_of_an_indexed_item_in_an_archive(root: Path) -> None:
    _put(root, "archive/TASK-000003-implement-auth.md", (root / _TASK).read_text(encoding="utf-8"))


def _backup_folder_copy(root: Path) -> None:
    _put(
        root,
        "backup-2025/tasks/TASK-000003-implement-auth.md",
        (root / _TASK).read_text(encoding="utf-8"),
    )


def _nested_fixture_tree(root: Path) -> None:
    for rel in (_TASK, _MILE):
        _put(root, f"fixture/{rel}", (root / rel).read_text(encoding="utf-8"))


def _lone_fixture_item(root: Path) -> None:
    _put(
        root,
        "tests/fixtures/sample/tasks/TASK-000042-sample.md",
        _ITEM.format(id="TASK-42", seq=42, type="task", status="Draft"),
    )


def _another_tools_record(root: Path) -> None:
    _put(
        root,
        "docs/decisions/ADR-20240115-use-postgres.md",
        "---\nid: ADR-20240115\ntitle: x\n---\nx\n",
    )


def _latin_1_document(root: Path) -> None:
    _put(root, "docs/lesson-2-verbes.md", "le caf\xe9\n".encode("latin-1"))
    _put(
        root,
        "docs/chapter-1-getting-started.md",
        "---\nid: [x\n---\nle caf\xe9\n".encode("latin-1"),
    )


def _non_yaml_block(root: Path) -> None:
    _put(root, "docs/chapter-2-setup.md", "---\n- not: [a mapping\n---\nbody\n")


def _another_types_prefix_in_a_types_folder(root: Path) -> None:
    _put(
        root, "tasks/BUG-000050-x.md", _ITEM.format(id="BUG-50", seq=50, type="bug", status="Open")
    )


_STRAYS: dict[str, Callable[[Path], None]] = {
    "archived-milestone-the-index-never-held": _archived_milestone_the_index_never_held,
    "copy-of-an-indexed-item-in-an-archive": _copy_of_an_indexed_item_in_an_archive,
    "backup-folder-copy": _backup_folder_copy,
    "nested-fixture-tree": _nested_fixture_tree,
    "lone-fixture-item": _lone_fixture_item,
    "another-tools-numbered-record": _another_tools_record,
    "documents-that-do-not-decode": _latin_1_document,
    "document-opening-with-a-non-yaml-block": _non_yaml_block,
    "another-types-prefix-in-a-types-folder": _another_types_prefix_in_a_types_folder,
}


@pytest.mark.parametrize("stray", _STRAYS)
async def test_a_file_outside_every_location_changes_nothing_and_is_named_nowhere(
    stray: str, squad: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    reference = tmp_path / "reference"
    shutil.copytree(squad, reference)
    known = set(_md_digest(reference))
    _STRAYS[stray](squad)
    strays = {rel: d for rel, d in _md_digest(squad).items() if rel not in known}
    assert strays
    monkeypatch.chdir(reference)
    assert (await invoke(["migrate", "up"])).exit_code == 0
    monkeypatch.chdir(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert _stamp(squad) == SCHEMA_VERSION
    assert _floors(squad) == _floors(reference)
    assert "index reconciled" not in result.output
    after = _md_digest(squad)
    for rel, digest in strays.items():
        assert after[rel] == digest
        assert rel not in result.output


@pytest.mark.parametrize("stray", _STRAYS)
async def test_the_trailing_repair_never_refuses_a_run_the_reconcile_let_through(
    stray: str, squad: Path
) -> None:
    _STRAYS[stray](squad)
    on_disk = set(_md_digest(squad))

    run = await Service(_paths_at(squad)).run_pending_migrations()

    assert run.repair is not None
    assert run.repair.unreadable == []
    assert on_disk <= set(_md_digest(squad))


async def test_a_milestone_moved_by_hand_into_an_archive_is_dropped_and_named(
    squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    (squad / "archive").mkdir()
    moved = squad / "archive" / Path(_MILE).name
    shutil.move(squad / _MILE, moved)
    content = moved.read_bytes()
    monkeypatch.chdir(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert "dropped MILE-11" in result.output
    assert moved.read_bytes() == content
    index = json.loads((squad / ".squads.json").read_text(encoding="utf-8"))
    assert all(int(str(k).rsplit("-", 1)[-1]) != 11 for k in index["items"])
    assert _stamp(squad) == SCHEMA_VERSION


_NEVER_INDEXED: dict[str, bytes | str] = {
    "undecodable-bytes": b"---\nid: TASK-99\n---\n\xff\xfe",
    "frontmatter-that-does-not-parse": "---\nid: [unclosed\n---\nx\n",
    "frontmatter-with-no-id": "---\ntitle: x\n---\nx\n",
    "no-frontmatter": "# prose\n",
}


@pytest.mark.parametrize("shape", _NEVER_INDEXED)
async def test_a_file_never_indexed_at_a_location_stops_the_run_and_the_remedy_completes_it(
    shape: str, squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    _put(squad, "tasks/TASK-000099-new.md", _NEVER_INDEXED[shape])
    before = _md_digest(squad)
    monkeypatch.chdir(squad)

    refused = await invoke(["migrate", "up"])

    assert refused.exit_code == 1, refused.output
    assert "TASK-000099-new.md" in refused.output
    assert (
        "when it is not one of the squad's items, move it out of the folder it sits in"
        in refused.output
    )
    assert _stamp(squad) == "0.14"
    assert _md_digest(squad) == before
    (squad / "tasks/TASK-000099-new.md").unlink()
    assert (await invoke(["migrate", "up"])).exit_code == 0
    assert _floors(squad) == (11, 6)


async def test_two_ids_sharing_a_number_stop_the_run_and_a_hand_renumber_completes_it(
    squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    _put(
        squad,
        "bugs/BUG-000003-clash.md",
        _ITEM.format(id="BUG-3", seq=3, type="bug", status="Open"),
    )
    before = _md_digest(squad)
    monkeypatch.chdir(squad)

    refused = await invoke(["migrate", "up"])

    out = " ".join(refused.output.split())
    assert refused.exit_code == 1, refused.output
    assert "number 3 is used by" in out and "TASK-3" in out and "BUG-3" in out
    assert _TASK in out and "bugs/BUG-000003-clash.md" in out
    assert "give it number 12" in out
    assert "sq renumber" not in out and "--renumber" not in out and "sq repair" not in out
    assert _stamp(squad) == "0.14"
    assert _md_digest(squad) == before
    (squad / "bugs/BUG-000003-clash.md").unlink()
    _put(
        squad,
        "bugs/BUG-000012-clash.md",
        _ITEM.format(id="BUG-12", seq=12, type="bug", status="Open"),
    )
    assert (await invoke(["migrate", "up"])).exit_code == 0
    assert _stamp(squad) == SCHEMA_VERSION


# --------------------------------------------------------------------------- agreement with repair


async def test_repair_reports_the_same_idless_file_in_a_types_folder_that_the_reconcile_stops_on(
    squad: Path,
) -> None:
    _put(squad, "tasks/TASK-000099-new.md", "---\ntitle: x\n---\nx\n")

    result = await Service(_paths_at(squad)).repair()

    assert any("TASK-000099-new.md" in line for line in result.unreadable)


async def test_repair_reports_the_same_copy_under_any_name_that_the_reconcile_stops_on(
    squad: Path,
) -> None:
    shutil.copy(squad / _TASK, squad / "tasks/notes.md")

    result = await Service(_paths_at(squad)).repair()

    assert any("notes.md" in line for line in result.unreadable)


async def test_repair_does_not_see_another_types_prefix_inside_a_types_folder(
    squad: Path,
) -> None:
    _another_types_prefix_in_a_types_folder(squad)

    result = await Service(_paths_at(squad)).repair()

    assert result.unreadable == []
    assert 50 not in result.db.items
