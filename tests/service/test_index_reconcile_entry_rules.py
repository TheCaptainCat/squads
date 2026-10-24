"""The index rebuild that runs before any migration: which entry each index state and each file
shape gets, and which of its three result sets (newly indexed, dropped as missing, unindexable)
a file lands in. It resolves no vocabulary and writes nothing but the index.
"""

import hashlib
import json
import shutil
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from _helpers import make_unreadable_by_the_os
from squads import __version__
from squads._index._reconcile import ReconcileResult, reconcile_index
from squads._index._store import IndexStore
from squads._models._config import SquadsConfig
from squads._paths import SquadPaths
from squads._workflow import bundled_spec, load_workflow_spec

pytestmark = pytest.mark.anyio

_CORPUS_DIR = Path(__file__).parent.parent / "fixtures" / "corpus"
_TASK = "tasks/TASK-000003-implement-auth.md"
_ALL = ("ROLE-1", "FEAT-2", "TASK-3", "BUG-4", "ADR-5", "REV-6", "SKILL-7", "SKILL-8")


def paths_at(root: Path) -> SquadPaths:
    with (root / ".squads.toml").open("rb") as fh:
        cfg = SquadsConfig.from_toml_dict(tomllib.load(fh))
    return SquadPaths(root=root, squad_dir=root / cfg.squad_dir, config=cfg)


def copy_corpus(name: str, tmp_path: Path) -> Path:
    root = tmp_path / name
    shutil.copytree(_CORPUS_DIR / name, root)
    return root


async def run_reconcile(
    root: Path, schema: str = "0.11", *, spec: Any = None
) -> tuple[ReconcileResult, dict[str, Any]]:
    paths = paths_at(root)
    store = IndexStore(paths.index_path, paths.lock_path, spec=spec)
    result = await reconcile_index(paths.squad_dir, store, schema)
    return result, json.loads(paths.index_path.read_text(encoding="utf-8"))


def edit_index(root: Path, edit: Callable[[dict[str, Any]], None]) -> None:
    path = root / ".squads.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    edit(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def entry(data: dict[str, Any], seq: int) -> dict[str, Any]:
    items = data["items"]
    return items.get(str(seq)) or items[next(k for k in items if k.endswith(f"-{seq:06d}"))]


def stored_fields(data: dict[str, Any], seq: int) -> dict[str, Any]:
    """The entry's fields without the attribute mapping, slug marker and empty sub-entity
    pointer an entry of an older schema does not carry (they default to empty)."""
    fields = {
        k: v
        for k, v in entry(data, seq).items()
        if k not in ("attributes", "slug_in_file", "extra")
    }
    fields["subentities"] = [
        {k: v for k, v in sub.items() if not (k == "deferred_to" and v is None)}
        for sub in fields.get("subentities", [])
    ]
    return fields


def set_entry(seq: int, **fields: Any) -> Callable[[dict[str, Any]], None]:
    def _edit(data: dict[str, Any]) -> None:
        entry(data, seq).update(fields)

    return _edit


def drop_entry(seq: int) -> Callable[[dict[str, Any]], None]:
    def _edit(data: dict[str, Any]) -> None:
        for key in [k for k in data["items"] if int(str(k).rsplit("-", 1)[-1]) == seq]:
            del data["items"][key]

    return _edit


def forget_task(root: Path) -> None:
    """Drop the task's index entry but keep tasks/ a location, through another indexed task."""

    def _edit(data: dict[str, Any]) -> None:
        anchor = dict(entry(data, 3))
        drop_entry(3)(data)
        anchor.update(
            sequence_id=9, slug="anchor", title="Anchor", path="tasks/TASK-000009-anchor.md"
        )
        anchor.pop("id", None)
        data["items"]["9"] = anchor
        data["counter"] = max(data["counter"], 9)

    (root / "tasks/TASK-000009-anchor.md").write_text(
        _NEW.format(id="TASK-9", seq=9, type="task", status="Draft"), encoding="utf-8"
    )
    edit_index(root, _edit)


def replace_in(root: Path, rel: str, old: str, new: str) -> None:
    path = root / rel
    text = path.read_text(encoding="utf-8")
    assert old in text, (rel, old)
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def seqs(data: dict[str, Any]) -> set[int]:
    return {int(str(k).rsplit("-", 1)[-1]) for k in data["items"]}


# --------------------------------------------------------------------------- index state


@dataclass(frozen=True)
class IndexRow:
    mutate: Callable[[Path], None]
    indexed: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    extra: tuple[int, ...] = ()
    check: Callable[[dict[str, Any]], None] = field(default=lambda _data: None)


def _write_index(root: Path, text: str) -> None:
    (root / ".squads.json").write_text(text, encoding="utf-8")


def _index_rows() -> dict[str, IndexRow]:
    return {
        "consistent": IndexRow(lambda r: None),
        "missing": IndexRow(lambda r: (r / ".squads.json").unlink(), indexed=_ALL),
        "not-json": IndexRow(lambda r: _write_index(r, "not json{"), indexed=_ALL),
        "fails-the-model": IndexRow(lambda r: _write_index(r, '{"counter": "abc"}'), indexed=_ALL),
        "type-the-spec-lacks": IndexRow(
            lambda r: edit_index(r, set_entry(3, type="zzz")),
            check=lambda d: _assert_field(d, 3, "type", "task"),
        ),
        "status-the-spec-lacks": IndexRow(
            lambda r: edit_index(r, set_entry(3, status="Nope")),
            check=lambda d: _assert_field(d, 3, "status", "InProgress"),
        ),
        "no-entry-for-a-file": IndexRow(lambda r: forget_task(r), indexed=("TASK-3",), extra=(9,)),
        "entry-whose-file-is-gone": IndexRow(
            lambda r: (r / _TASK).unlink(),
            missing=("TASK-3",),
            check=lambda d: _assert_absent(d, 3),
        ),
        "entry-at-an-old-path": IndexRow(_rename_task, check=_assert_renamed),
        "entry-whose-file-was-moved-by-hand-out-of-every-location": IndexRow(
            _move_task, missing=("TASK-3",), check=lambda d: _assert_absent(d, 3)
        ),
        "stale-field": IndexRow(
            lambda r: edit_index(r, set_entry(3, title="stale")),
            check=lambda d: _assert_field(d, 3, "title", "Implement auth"),
        ),
    }


def _move_task(root: Path) -> None:
    (root / "archive").mkdir()
    (root / _TASK).rename(root / "archive/TASK-000003-implement-auth.md")


def _assert_field(data: dict[str, Any], seq: int, key: str, value: object) -> None:
    assert entry(data, seq)[key] == value


def _assert_absent(data: dict[str, Any], seq: int) -> None:
    assert seq not in seqs(data)


def _rename_task(root: Path) -> None:
    (root / _TASK).rename(root / "tasks/TASK-000003-renamed.md")


def _assert_renamed(data: dict[str, Any]) -> None:
    assert entry(data, 3)["path"] == "tasks/TASK-000003-renamed.md"


@pytest.mark.parametrize("row", _index_rows())
async def test_each_index_state_gets_the_entries_its_files_describe(
    row: str, tmp_path: Path
) -> None:
    spec = _index_rows()[row]
    root = copy_corpus("v0_11", tmp_path)
    spec.mutate(root)

    result, data = await run_reconcile(root)

    assert result.indexed == spec.indexed
    assert result.missing == spec.missing
    assert result.unindexable == ()
    expected = (set(range(1, 9)) - ({3} if spec.missing else set())) | set(spec.extra)
    assert data["counter"] == (9 if spec.extra else 8)
    assert seqs(data) == expected
    assert data["schema_version"] == "0.11"
    spec.check(data)


# --------------------------------------------------------------------------- file shape


@dataclass(frozen=True)
class ShapeRow:
    """A damaged file at the task's path, in a folder the squad keeps tasks in. The flags say
    whether it is reported with a previous entry and without one: where it sits decides, so both
    are reported, and without an entry none exists for it."""

    mutate: Callable[[Path], None]
    unindexable_with_prev: bool
    unindexable_without_prev: bool


def _bytes(root: Path) -> None:
    (root / _TASK).write_bytes(b"---\nid: TASK-000003\n---\n\xff\xfe\x00bad")


def _unreadable(root: Path) -> None:
    make_unreadable_by_the_os(root / _TASK)


def _write(root: Path, text: str) -> None:
    (root / _TASK).write_text(text, encoding="utf-8")


def _shape_rows() -> dict[str, ShapeRow]:
    return {
        "undecodable-bytes": ShapeRow(_bytes, True, True),
        "read-refused": ShapeRow(_unreadable, True, True),
        "malformed-yaml": ShapeRow(
            lambda r: _write(r, "---\nid: [unclosed\n---\nbody\n"), True, True
        ),
        "no-frontmatter": ShapeRow(lambda r: _write(r, "# just prose\n"), True, True),
        "id-line-gone": ShapeRow(lambda r: replace_in(r, _TASK, "id: TASK-3\n", ""), True, True),
        "id-malformed": ShapeRow(
            lambda r: replace_in(r, _TASK, "id: TASK-3", "id: banana"), True, True
        ),
        "type-missing": ShapeRow(lambda r: replace_in(r, _TASK, "type: task\n", ""), True, True),
        "field-type-invalid": ShapeRow(
            lambda r: replace_in(r, _TASK, "status: InProgress", "status: [a, b]"), True, True
        ),
    }


@pytest.mark.parametrize("with_prev", [True, False], ids=["with-entry", "without-entry"])
@pytest.mark.parametrize("row", _shape_rows())
async def test_a_file_that_cannot_be_indexed_is_reported_and_its_entry_carried(
    row: str, with_prev: bool, tmp_path: Path
) -> None:
    spec = _shape_rows()[row]
    root = copy_corpus("v0_11", tmp_path)
    before = json.loads((root / ".squads.json").read_text(encoding="utf-8"))
    if not with_prev:
        forget_task(root)
    spec.mutate(root)

    result, data = await run_reconcile(root)

    reported = [u.path for u in result.unindexable]
    expect = spec.unindexable_with_prev if with_prev else spec.unindexable_without_prev
    assert reported == ([_TASK] if expect else [])
    assert result.indexed == ()
    assert result.missing == ()
    if with_prev:
        assert stored_fields(data, 3) == stored_fields(before, 3), "the previous entry is carried"
    else:
        assert 3 not in seqs(data)
    assert seqs(data) - {3} == (set(range(1, 9)) - {3}) | ({9} if not with_prev else set())
    assert all(u.cause for u in result.unindexable)


@dataclass(frozen=True)
class NewFile:
    rel: str
    text: str
    seq: int
    prefix: str


_NEW = (
    "---\nid: {id}\nsequence_id: {seq}\ntype: {type}\ntitle: T\nslug: s\nstatus: {status}\n"
    "created_at: '2025-01-01T00:00:00Z'\nupdated_at: '2025-01-01T00:00:00Z'\n---\nbody\n"
)


def _new(
    rel: str,
    item_id: str,
    seq: int,
    type_: str = "task",
    status: str = "Draft",
) -> NewFile:
    prefix = item_id.rpartition("-")[0]
    text = _NEW.format(id=item_id, seq=seq, type=type_, status=status)
    return NewFile(rel, text, seq, prefix)


_AT_A_LOCATION = {
    "slug-starting-with-digits": _new("tasks/TASK-000009-2024-plan.md", "TASK-9", 9),
}

#: Found by the tree walk, which is what runs when there is no readable index.
_FOUND_BY_THE_WALK = {
    "hyphenated-prefix": _new("runbooks/RUN-BOOK-000042-runbook.md", "RUN-BOOK-42", 42),
    "custom-type": _new("incidents/INC-000030-x.md", "INC-30", 30, "incident"),
    "an-archive-folder": _new("archive/MILE-000030-old.md", "MILE-30", 30, "milestone"),
    "deep-under-the-squad-directory": _new("a/b/c/TASK-000050-deep.md", "TASK-50", 50),
}

_OUTSIDE_EVERY_LOCATION = {
    "custom-folder-nothing-declares": _new("incidents/INC-000030-x.md", "INC-30", 30, "incident"),
    "deep-under-the-squad-directory": _new("a/b/c/TASK-000050-deep.md", "TASK-50", 50),
    "an-archive-folder": _new("archive/MILE-000030-old.md", "MILE-30", 30, "milestone"),
}

#: Inside a location's directory but not a location of their own prefix: not the squad's items,
#: though the directory's files are opened to learn whether they carry an item's id.
_WRONG_PREFIX_FOR_THE_FOLDER = {
    "another-types-prefix-inside-a-types-folder": _new(
        "tasks/BUG-000050-x.md", "BUG-50", 50, "bug"
    ),
    "the-right-prefix-in-another-types-folder": _new("bugs/TASK-000051-x.md", "TASK-51", 51),
}


@pytest.mark.parametrize("name", _AT_A_LOCATION)
async def test_a_new_item_file_at_a_location_is_indexed(name: str, tmp_path: Path) -> None:
    new = _AT_A_LOCATION[name]
    root = copy_corpus("v0_11", tmp_path)
    (root / new.rel).parent.mkdir(parents=True, exist_ok=True)
    (root / new.rel).write_text(new.text, encoding="utf-8")

    result, data = await run_reconcile(root)

    assert result.indexed == (f"{new.prefix}-{new.seq}",)
    assert result.unindexable == ()
    assert entry(data, new.seq)["path"] == new.rel
    assert data["counter"] == max(8, new.seq)


@pytest.mark.parametrize("name", _FOUND_BY_THE_WALK)
async def test_with_no_readable_index_every_item_named_file_in_the_tree_is_recognised(
    name: str, tmp_path: Path
) -> None:
    new = _FOUND_BY_THE_WALK[name]
    root = copy_corpus("v0_11", tmp_path)
    (root / ".squads.json").unlink()
    (root / new.rel).parent.mkdir(parents=True, exist_ok=True)
    (root / new.rel).write_text(new.text, encoding="utf-8")

    result, data = await run_reconcile(root)

    assert result.had_index is False
    assert set(result.indexed) == {*_ALL, f"{new.prefix}-{new.seq}"}
    assert result.unindexable == ()
    assert entry(data, new.seq)["path"] == new.rel
    assert data["counter"] == max(8, new.seq)


@pytest.mark.parametrize("name", _OUTSIDE_EVERY_LOCATION)
async def test_an_item_shaped_file_outside_every_location_is_never_opened_or_counted(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    new = _OUTSIDE_EVERY_LOCATION[name]
    root = copy_corpus("v0_11", tmp_path)
    (root / new.rel).parent.mkdir(parents=True, exist_ok=True)
    (root / new.rel).write_text(new.text, encoding="utf-8")
    opened = _record_reads(monkeypatch)

    result, data = await run_reconcile(root)

    assert result == ReconcileResult()
    assert (data["counter"], data["padding"]) == (8, 6)
    assert seqs(data) == set(range(1, 9))
    assert root / new.rel not in opened


@pytest.mark.parametrize("name", _WRONG_PREFIX_FOR_THE_FOLDER)
async def test_a_file_with_another_types_prefix_inside_a_types_folder_is_not_an_item_there(
    name: str, tmp_path: Path
) -> None:
    new = _WRONG_PREFIX_FOR_THE_FOLDER[name]
    root = copy_corpus("v0_11", tmp_path)
    (root / new.rel).write_text(new.text, encoding="utf-8")

    result, data = await run_reconcile(root)

    assert result == ReconcileResult()
    assert (data["counter"], data["padding"]) == (8, 6)
    assert seqs(data) == set(range(1, 9))


def _record_reads(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    from squads import _aio

    opened: list[Path] = []
    original = _aio.read_text

    async def _spy(path: Path) -> str:
        opened.append(path)
        return await original(path)

    monkeypatch.setattr(_aio, "read_text", _spy)
    return opened


async def test_an_id_with_no_sequence_id_takes_its_number_from_the_id(tmp_path: Path) -> None:
    root = copy_corpus("v0_11", tmp_path)
    forget_task(root)
    replace_in(root, _TASK, "sequence_id: 3\n", "")

    result, data = await run_reconcile(root)

    assert result.indexed == ("TASK-3",)
    assert entry(data, 3)["sequence_id"] == 3


@pytest.mark.parametrize("with_prev", [True, False], ids=["with-entry", "without-entry"])
async def test_a_file_with_no_timestamps_keeps_its_indexed_ones(
    with_prev: bool, tmp_path: Path
) -> None:
    root = copy_corpus("v0_11", tmp_path)
    before = json.loads((root / ".squads.json").read_text(encoding="utf-8"))
    text = (root / _TASK).read_text(encoding="utf-8")
    assert "created_at:" in text and "updated_at:" in text
    stripped = "".join(
        line
        for line in text.splitlines(keepends=True)
        if not line.startswith(("created_at:", "updated_at:"))
    )
    (root / _TASK).write_text(stripped, encoding="utf-8")
    if not with_prev:
        forget_task(root)

    result, data = await run_reconcile(root)

    assert result.unindexable == ()
    if with_prev:
        assert entry(data, 3)["created_at"] == entry(before, 3)["created_at"]
        assert entry(data, 3)["updated_at"] == entry(before, 3)["updated_at"]
    else:
        assert result.indexed == ("TASK-3",)


_COPIES = {
    "same-name-in-another-types-folder": "adrs/TASK-000003-implement-auth.md",
    "other-slug-same-prefix": "tasks/TASK-000003-other.md",
    "a-name-that-is-not-an-items": "tasks/notes.md",
}


@pytest.mark.parametrize("with_prev", [True, False], ids=["with-entry", "without-entry"])
@pytest.mark.parametrize("copy", _COPIES)
async def test_two_files_carrying_one_id_are_both_named_and_neither_taken(
    copy: str, with_prev: bool, tmp_path: Path
) -> None:
    root = copy_corpus("v0_11", tmp_path)
    before = json.loads((root / ".squads.json").read_text(encoding="utf-8"))
    shutil.copy(root / _TASK, root / _COPIES[copy])
    if not with_prev:
        forget_task(root)

    result, data = await run_reconcile(root)

    assert sorted(u.path for u in result.unindexable) == sorted([_TASK, _COPIES[copy]])
    assert all("also claimed by" in u.cause for u in result.unindexable)
    assert not any(u.shared_number for u in result.unindexable)
    if with_prev:
        assert stored_fields(data, 3) == stored_fields(before, 3)
    else:
        assert 3 not in seqs(data)


async def test_a_copy_that_cannot_be_read_or_carries_no_id_is_left_alone(tmp_path: Path) -> None:
    root = copy_corpus("v0_11", tmp_path)
    (root / "tasks/notes.md").write_bytes(b"\xff\xfe")
    (root / "tasks/more.md").write_text("# prose\n", encoding="utf-8")

    result, _ = await run_reconcile(root)

    assert result == ReconcileResult()


async def test_two_ids_sharing_a_number_are_refused_with_the_number_both_ids_and_paths(
    tmp_path: Path,
) -> None:
    root = copy_corpus("v0_11", tmp_path)
    before = json.loads((root / ".squads.json").read_text(encoding="utf-8"))
    _plain(
        root, "bugs/BUG-000003-clash.md", _NEW.format(id="BUG-3", seq=3, type="bug", status="Open")
    )

    result, data = await run_reconcile(root)

    assert sorted(u.path for u in result.unindexable) == sorted([_TASK, "bugs/BUG-000003-clash.md"])
    for u in result.unindexable:
        assert "number 3" in u.cause
        assert "TASK-3" in u.cause and "BUG-3" in u.cause
        assert _TASK in u.cause and "bugs/BUG-000003-clash.md" in u.cause
        assert "one item per number" in u.cause
        assert "also claimed" not in u.cause
        assert u.shared_number
    assert stored_fields(data, 3) == stored_fields(before, 3)
    assert result.counter == 8


async def test_a_legacy_ref_kinds_map_is_stored_exactly_as_the_file_spells_it(
    tmp_path: Path,
) -> None:
    root = copy_corpus("v0_1", tmp_path)
    (root / ".squads.json").unlink()

    result, data = await run_reconcile(root, "0.1")

    task = entry(data, 3)
    assert result.unindexable == ()
    assert task["refs"] == ["BUG-000004", "ADR-000005"]
    assert task["attributes"]["extra"]["ref_kinds"] == {"BUG-000004": "fixes"}


# --------------------------------------------------------------------------- not items


def _plain(root: Path, rel: str, text: str) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text, encoding="utf-8")


_NOT_ITEMS = {
    "memory-note": ("memory/dev-agent/note.md", "---\nid: a-note\n---\nA note.\n"),
    "board-notice": ("board/0364b1c5a2.md", "---\ntitle: Notice\n---\nbody\n"),
    "slug-named-skill": ("agents/skills/sq-memory.md", "---\ntitle: x\n---\nbody\n"),
    "name-lacks-the-shape-no-id": ("docs/README.md", "# readme\n"),
    "name-lacks-the-shape-with-id": ("docs/notes-2024.md", "---\nid: TASK-000090\n---\nx\n"),
    "shape-no-frontmatter": ("docs/ADR-0090-x.md", "# a decision record\n"),
    "shape-id-of-another-shape-number": ("docs/FEAT-0091-y.md", "---\nid: 42\n---\ny\n"),
    "shape-id-of-another-shape-word": ("docs/FEAT-0092-z.md", "---\nid: abc\n---\nz\n"),
    "shape-id-gone": ("docs/FEAT-0093-w.md", "---\ntitle: w\n---\nw\n"),
    "shape-and-id-another-tools-record": (
        "docs/decisions/ADR-20240115-use-postgres.md",
        "---\nid: ADR-20240115\n---\nx\n",
    ),
    "lone-fixture-item": (
        "tests/fixtures/sample/tasks/TASK-000042-sample.md",
        _NEW.format(id="TASK-42", seq=42, type="task", status="Draft"),
    ),
    "backup-copy-of-an-indexed-item": (
        "backup-2025/tasks/TASK-000003-implement-auth.md",
        _NEW.format(id="TASK-3", seq=3, type="task", status="Draft"),
    ),
    "nested-tree-repeating-ids": (
        "fixture/tasks/TASK-000003-implement-auth.md",
        _NEW.format(id="TASK-3", seq=3, type="task", status="Draft"),
    ),
    "archived-milestone-the-index-never-held": (
        "archive/MILE-000030-old.md",
        _NEW.format(id="MILE-30", seq=30, type="milestone", status="Draft"),
    ),
    "copy-of-an-indexed-item-in-an-archive": (
        "archive/TASK-000003-implement-auth.md",
        _NEW.format(id="TASK-3", seq=3, type="task", status="Draft"),
    ),
}

#: Not named like an item, but in a directory the squad keeps items in, so opened for its id.
_IN_A_LOCATION_DIRECTORY = {"slug-named-skill"}

_LATIN_1 = {
    "latin-1-document": "docs/lesson-2-verbes.md",
    "item-shaped-latin-1-document": "docs/chapter-1-getting-started.md",
}


@pytest.mark.parametrize("name", _NOT_ITEMS)
async def test_a_markdown_file_that_is_not_an_item_is_never_opened_or_reported(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rel, text = _NOT_ITEMS[name]
    root = copy_corpus("v0_11", tmp_path)
    _plain(root, rel, text)
    opened = _record_reads(monkeypatch)

    result, data = await run_reconcile(root)

    assert result == ReconcileResult()
    assert seqs(data) == set(range(1, 9))
    assert (data["counter"], data["padding"]) == (8, 6)
    if name not in _IN_A_LOCATION_DIRECTORY:
        assert root / rel not in opened


@pytest.mark.parametrize("name", _LATIN_1)
async def test_a_document_that_does_not_decode_or_parse_is_never_opened(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rel = _LATIN_1[name]
    root = copy_corpus("v0_11", tmp_path)
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_bytes("---\nid: [x\n---\nle caf\xe9\n".encode("latin-1"))
    opened = _record_reads(monkeypatch)

    result, _ = await run_reconcile(root)

    assert result == ReconcileResult()
    assert root / rel not in opened


async def test_unrelated_markdown_named_after_an_indexed_item_is_not_that_item(
    tmp_path: Path,
) -> None:
    root = copy_corpus("v0_11", tmp_path)
    _plain(root, "docs/TASK-000003-notes.md", "# unrelated\n")

    result, _ = await run_reconcile(root)

    assert result == ReconcileResult()


async def test_unrelated_markdown_whose_name_and_id_both_have_the_item_shape_is_ignored(
    tmp_path: Path,
) -> None:
    """Outside every location it is nothing to the run, however much it looks like an item."""
    root = copy_corpus("v0_11", tmp_path)
    _plain(
        root,
        "docs/ADR-0090-x.md",
        _NEW.format(id="ADR-90", seq=90, type="decision", status="Proposed"),
    )
    _plain(root, "docs/ADR-0091-y.md", "---\nid: ADR-0091\ntitle: y\n---\ny\n")

    result, data = await run_reconcile(root)

    assert result == ReconcileResult()
    assert seqs(data) == set(range(1, 9))


# --------------------------------------------------------------------------- invariants


def _digest(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.name != ".squads.json"
    }


@pytest.mark.parametrize(
    ("corpus", "schema"), [("v0_1", "0.1"), ("v0_8", "0.8"), ("v0_11", "0.11")]
)
async def test_the_rebuild_writes_no_file_but_the_index_and_stamps_the_corpus_schema(
    corpus: str, schema: str, tmp_path: Path
) -> None:
    root = copy_corpus(corpus, tmp_path)
    (root / ".squads.json").unlink()
    before = _digest(root)

    _, data = await run_reconcile(root, schema)

    assert _digest(root) == before
    assert data["schema_version"] == schema


def _spec_variants(tmp_path: Path) -> dict[str, Any]:
    kept = sorted(t for t in bundled_spec().items if t != "review")
    kinds = sorted([k for k in bundled_spec().ref_kinds if k != "related"] + ["link"])

    def declared(name: str, body: str) -> Any:
        squad = tmp_path / name
        (squad / ".overrides").mkdir(parents=True)
        (squad / ".overrides" / "workflow.toml").write_text(
            f"# squads:override-base:{__version__}\n{body}", encoding="utf-8"
        )
        return load_workflow_spec(squad_dir=squad)

    return {
        "bundled": bundled_spec(),
        "type-dropped": declared("a", f"[selected]\nitems = {kept!r}\n"),
        "status-dropped": declared(
            "b",
            '[lifecycles.slim]\ninitial = "Draft"\n[lifecycles.slim.transitions]\n'
            'Draft = ["Ready", "Cancelled"]\nReady = ["Done"]\nDone = ["Draft"]\n'
            'Cancelled = []\n[items.task]\nlifecycle = "slim"\n',
        ),
        "re-prefixed": declared("c", '[items.task]\nprefix = "WORK"\nfolder = "work"\n'),
        "default-ref-kind": declared(
            "d",
            f"[selected]\nref_kinds = {kinds!r}\n"
            '[ref_kinds.link]\nlabel = "Link"\nhint = "default"\nrole = "default"\n',
        ),
    }


@pytest.mark.parametrize("corpus", ["v0_1", "v0_8", "v0_11", "v0_14"])
async def test_the_index_written_is_the_same_under_every_vocabulary(
    corpus: str, tmp_path: Path
) -> None:
    written: dict[str, bytes] = {}
    for label, spec in _spec_variants(tmp_path / "specs").items():
        root = copy_corpus(corpus, tmp_path / label)
        await run_reconcile(root, "0.1", spec=spec)
        written[label] = (root / ".squads.json").read_bytes()
    assert len(set(written.values())) == 1, sorted(written)


@pytest.mark.parametrize("corpus", sorted(p.name for p in _CORPUS_DIR.iterdir() if p.is_dir()))
async def test_over_every_corpus_the_rebuild_reports_nothing_and_keeps_the_indexed_set(
    corpus: str, tmp_path: Path
) -> None:
    root = copy_corpus(corpus, tmp_path)
    own = json.loads((root / ".squads.json").read_text(encoding="utf-8"))
    own_paths = {int(str(k).rsplit("-", 1)[-1]): v["path"] for k, v in own["items"].items()}

    result, data = await run_reconcile(root, own["schema_version"])

    assert result == ReconcileResult()
    assert {int(str(k)): v["path"] for k, v in data["items"].items()} == own_paths


# --------------------------------------------------------------------------- floors, old indexes


def _plain_bytes(root: Path, rel: str, data: bytes) -> None:
    (root / rel).write_bytes(data)


def _twice(root: Path) -> None:
    text = _NEW.format(id="TASK-20240118", seq=20240118, type="task", status="Draft")
    _plain(root, "tasks/TASK-20240118-a.md", text)
    _plain(root, "tasks/TASK-20240118-b.md", text)


def _big_name(rel: str, text: str) -> Callable[[Path], None]:
    def _apply(root: Path) -> None:
        _plain(root, rel, text)

    return _apply


_REJECTED_WITH_BIG_NUMBERS: dict[str, Callable[[Path], None]] = {
    "no-type": _big_name("tasks/TASK-20240115-x.md", "---\nid: TASK-20240115\ntitle: x\n---\nx\n"),
    "malformed-yaml": _big_name("tasks/TASK-20240116-x.md", "---\nid: [unclosed\n---\nx\n"),
    "undecodable": lambda r: _plain_bytes(r, "tasks/TASK-20240117-x.md", b"\xff\xfe"),
    "id-claimed-twice": lambda r: _twice(r),
}


@pytest.mark.parametrize("row", _REJECTED_WITH_BIG_NUMBERS)
async def test_a_file_that_is_not_accepted_as_an_item_moves_neither_floor(
    row: str, tmp_path: Path
) -> None:
    root = copy_corpus("v0_11", tmp_path)
    before = json.loads((root / ".squads.json").read_text(encoding="utf-8"))
    _REJECTED_WITH_BIG_NUMBERS[row](root)

    result, data = await run_reconcile(root)

    assert result.unindexable
    assert (data["counter"], data["padding"]) == (before["counter"], before["padding"])


async def test_a_refused_pass_then_the_fix_leaves_what_a_first_pass_would(tmp_path: Path) -> None:
    fixed = copy_corpus("v0_11", tmp_path / "fixed")
    await run_reconcile(fixed)
    refused = copy_corpus("v0_11", tmp_path / "refused")
    _REJECTED_WITH_BIG_NUMBERS["no-type"](refused)
    assert (await run_reconcile(refused))[0].unindexable
    (refused / "tasks/TASK-20240115-x.md").unlink()

    _, after = await run_reconcile(refused)
    _, first = await run_reconcile(fixed)

    assert (after["counter"], after["padding"]) == (first["counter"], first["padding"])


@pytest.mark.parametrize(("corpus", "schema"), [("v0_1", "0.1"), ("v0_5", "0.5")])
async def test_an_entry_from_an_index_without_ids_is_named_by_what_its_path_carries(
    corpus: str, schema: str, tmp_path: Path
) -> None:
    root = copy_corpus(corpus, tmp_path)
    (root / _TASK).unlink()

    result, _ = await run_reconcile(root, schema)

    assert result.missing == ("TASK-3",)


@pytest.mark.parametrize(("corpus", "schema"), [("v0_1", "0.1"), ("v0_5", "0.5")])
async def test_a_moved_file_that_cannot_be_indexed_keeps_its_entry_from_an_index_without_ids(
    corpus: str, schema: str, tmp_path: Path
) -> None:
    root = copy_corpus(corpus, tmp_path)
    (root / _TASK).rename(root / "tasks/TASK-000003-renamed.md")
    (root / "tasks/TASK-000003-renamed.md").write_bytes(b"\xff")

    result, data = await run_reconcile(root, schema)

    assert [u.path for u in result.unindexable] == ["tasks/TASK-000003-renamed.md"]
    assert result.missing == ()
    assert 3 in seqs(data)


# --------------------------------------------------------------------------- locations


@pytest.mark.parametrize("state", ["missing", "not-json"])
async def test_with_no_readable_index_a_stray_item_named_file_is_taken_for_an_item(
    state: str, tmp_path: Path
) -> None:
    """The price of having no locations, which the check before the first runner answers."""
    root = copy_corpus("v0_11", tmp_path)
    _plain(
        root,
        "archive/MILE-000030-old.md",
        _NEW.format(id="MILE-30", seq=30, type="milestone", status="Draft"),
    )
    _plain(root, "docs/notes-2024.md", "---\nid: TASK-000090\n---\nx\n")
    _plain(root, "docs/RFC-2119-keywords.md", "---\ntitle: keywords\n---\nx\n")
    _plain(root, "docs/CVE-2024-1234.md", "# a vulnerability\n")
    _index_rows()[state].mutate(root)

    result, data = await run_reconcile(root)

    assert set(result.indexed) == {*_ALL, "MILE-30"}
    assert result.unindexable == ()
    assert seqs(data) == {*range(1, 9), 30}
    assert data["counter"] == 30


async def test_a_custom_types_folder_is_found_through_its_entries_alone(tmp_path: Path) -> None:
    root = copy_corpus("v0_11", tmp_path)
    (root / ".squads.json").unlink()
    _plain(
        root,
        "incidents/INC-000030-x.md",
        _NEW.format(id="INC-30", seq=30, type="incident", status="Draft"),
    )
    first, _ = await run_reconcile(root)
    assert "INC-30" in first.indexed
    _plain(
        root,
        "incidents/INC-000031-y.md",
        _NEW.format(id="INC-31", seq=31, type="incident", status="Draft"),
    )

    result, data = await run_reconcile(root)

    assert result.indexed == ("INC-31",)
    assert entry(data, 31)["path"] == "incidents/INC-000031-y.md"


async def test_a_first_item_in_a_folder_the_index_never_held_is_not_seen_by_the_routine(
    tmp_path: Path,
) -> None:
    """Left to the check before the first runner, which asks whether such a file has an entry."""
    root = copy_corpus("v0_11", tmp_path)
    _plain(
        root,
        "incidents/INC-000030-x.md",
        _NEW.format(id="INC-30", seq=30, type="incident", status="Draft"),
    )
    _plain(
        root,
        "milestones/MILE-000031-first.md",
        _NEW.format(id="MILE-31", seq=31, type="milestone", status="Draft"),
    )

    result, data = await run_reconcile(root)

    assert result == ReconcileResult()
    assert seqs(data) == set(range(1, 9))
