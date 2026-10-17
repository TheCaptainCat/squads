"""``sq migrate up`` refuses, before its first runner writes anything, a corpus that does not fit
where and how the squad declares its items: with no readable index (every item-shaped file in the
tree is taken for an item), with an index (a file the index does not know where a type lives, an
entry where no type lives), and against the vocabulary the squad's overrides declare. A refused
run leaves every item file as it found it, names no command but ``sq migrate up``, and the
remedy it gives lets the next run complete.
"""

import dataclasses
import hashlib
import json
import re
import shutil
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from squads import __version__
from squads._index._reconcile import ReconcileResult, plan_reconcile
from squads._index._store import IndexStore
from squads._models._config import SquadsConfig
from squads._models._schema import SCHEMA_VERSION
from squads._paths import SquadPaths
from squads._services import _corpus_fit, _maintenance
from squads._services._service import Service
from squads._workflow import bundled_spec

pytestmark = pytest.mark.anyio

_CORPUS_DIR = Path(__file__).parent.parent / "fixtures" / "corpus"
_TASK = "tasks/TASK-000003-implement-auth.md"
_MILE = "milestones/MILE-000011-ship-the-auth-module.md"
_ITEM = (
    "---\nid: {id}\nsequence_id: {seq}\ntype: {type}\ntitle: T\nslug: s\nstatus: {status}\n"
    "created_at: '2025-01-01T00:00:00Z'\nupdated_at: '2025-01-01T00:00:00Z'\n---\nbody\n"
)


def _paths_at(root: Path) -> SquadPaths:
    with (root / ".squads.toml").open("rb") as fh:
        cfg = SquadsConfig.from_toml_dict(tomllib.load(fh))
    return SquadPaths(root=root, squad_dir=root / cfg.squad_dir, config=cfg)


def _stamp(root: Path) -> str:
    return tomllib.loads((root / ".squads.toml").read_text(encoding="utf-8"))["schema_version"]


def _md(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*.md"))
        if p.is_file()
    }


def _put(root: Path, rel: str, content: str | bytes) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        (root / rel).write_bytes(content)
    else:
        (root / rel).write_text(content, encoding="utf-8")


def _index(root: Path) -> dict[str, Any]:
    return json.loads((root / ".squads.json").read_text(encoding="utf-8"))


def _reflog_migrate_lines(root: Path) -> list[dict[str, Any]]:
    path = root / ".reflog.jsonl"
    if not path.exists():
        return []
    lines = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
    return [x for x in lines if x["op"] == "migrate"]


def _sq_commands(text: str) -> list[str]:
    return re.findall(r"`sq [^`]*`", text)


@pytest.fixture
def squad(tmp_path: Path, frozen_time: object) -> Path:
    root = tmp_path / "v0_14"
    shutil.copytree(_CORPUS_DIR / "v0_14", root)
    return root


# --------------------------------------------------------------------------- no readable index


def _no_index(root: Path) -> None:
    (root / ".squads.json").unlink()


def _corrupt_index(root: Path) -> None:
    (root / ".squads.json").write_text("{nope", encoding="utf-8")


_INDEX_GONE = {"missing": _no_index, "not-json": _corrupt_index}


def _archived_item(root: Path) -> None:
    _put(
        root,
        "archive/MILE-000030-old.md",
        _ITEM.format(id="MILE-30", seq=30, type="milestone", status="Draft"),
    )


def _unreadable_look_alike(root: Path) -> None:
    _put(root, "docs/ADR-20240116-x.md", b"\xff\xfe\x00 not utf-8")


def _numbered_record_of_another_tool(root: Path) -> None:
    _put(
        root,
        "docs/decisions/ADR-20240115-use-postgres.md",
        "---\nid: ADR-20240115\ntitle: Use Postgres\n---\nx\n",
    )


def _backup_copy(root: Path) -> None:
    _put(root, "backup-2025/tasks/TASK-000003-implement-auth.md", (root / _TASK).read_bytes())


#: (stray, text the refusal must carry)
_NO_INDEX_REFUSALS: dict[str, tuple[Callable[[Path], None], str]] = {
    "an-archived-item": (_archived_item, "archive/MILE-000030-old.md"),
    "a-look-alike-that-cannot-be-read": (_unreadable_look_alike, "ADR-20240116-x.md"),
    "another-tools-numbered-record": (
        _numbered_record_of_another_tool,
        "ADR-20240115-use-postgres.md",
    ),
    "a-backup-copy-repeating-an-id": (_backup_copy, "backup-2025/tasks/TASK-000003"),
}


@pytest.mark.parametrize("state", _INDEX_GONE)
async def test_with_no_index_a_clean_squad_completes_with_every_item_indexed(
    state: str, squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    _INDEX_GONE[state](squad)
    monkeypatch.chdir(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert _stamp(squad) == SCHEMA_VERSION
    index = _index(squad)
    assert len(index["items"]) == 11
    assert (index["counter"], index["padding"]) == (11, 6)


@pytest.mark.parametrize("state", _INDEX_GONE)
@pytest.mark.parametrize("stray", _NO_INDEX_REFUSALS)
async def test_with_no_index_a_stray_is_refused_before_any_runner_and_no_index_is_left(
    stray: str, state: str, squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    apply, named = _NO_INDEX_REFUSALS[stray]
    apply(squad)
    _INDEX_GONE[state](squad)
    index_before = (squad / ".squads.json").read_bytes() if state == "not-json" else None
    files_before = _md(squad)
    monkeypatch.chdir(squad)

    first = await invoke(["migrate", "up"])
    second = await invoke(["migrate", "up"])

    for result in (first, second):
        out = " ".join(result.output.split())
        assert result.exit_code == 1, result.output
        assert named in out
        assert "no readable index" in out
        assert _sq_commands(out[out.index("no migration has run") :]) == ["`sq migrate up`"]
    assert _stamp(squad) == "0.14"
    assert _md(squad) == files_before
    assert _reflog_migrate_lines(squad) == []
    if state == "missing":
        assert not (squad / ".squads.json").exists()
    else:
        assert (squad / ".squads.json").read_bytes() == index_before


@pytest.mark.parametrize("stray", _NO_INDEX_REFUSALS)
async def test_once_the_index_is_restored_the_run_completes_and_the_stray_is_never_opened(
    stray: str, squad: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from squads import _aio

    original = (squad / ".squads.json").read_bytes()
    _NO_INDEX_REFUSALS[stray][0](squad)
    (squad / ".squads.json").write_bytes(original)
    stray_files = {rel for rel in _md(squad) if rel not in _md_of_corpus()}
    opened: list[Path] = []
    real = _aio.read_text

    async def _spy(path: Path) -> str:
        opened.append(path)
        return await real(path)

    monkeypatch.setattr(_aio, "read_text", _spy)

    run = await Service(_paths_at(squad)).run_pending_migrations()

    assert run.applied
    assert _stamp(squad) == SCHEMA_VERSION
    assert _index(squad)["counter"] == 11
    seen = {p.relative_to(squad).as_posix() for p in opened}
    assert not (
        seen & {rel for rel in stray_files if rel.startswith(("archive/", "docs/", "backup"))}
    )


def _md_of_corpus() -> dict[str, str]:
    return _md(_CORPUS_DIR / "v0_14")


@pytest.mark.parametrize("state", _INDEX_GONE)
@pytest.mark.parametrize(
    "rel", ["docs/RFC-2119-keywords.md", "docs/CVE-2024-1234.md"], ids=["rfc", "cve"]
)
async def test_with_no_index_a_look_alike_that_parses_without_an_id_is_passed_over(
    state: str, rel: str, squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    _put(squad, rel, "---\ntitle: a standard\n---\nx\n")
    _INDEX_GONE[state](squad)
    monkeypatch.chdir(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert rel not in result.output
    assert len(_index(squad)["items"]) == 11


async def test_a_refused_run_with_no_index_does_not_raise_the_counter_for_the_next_one(
    squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    _numbered_record_of_another_tool(squad)
    _no_index(squad)
    monkeypatch.chdir(squad)
    assert (await invoke(["migrate", "up"])).exit_code == 1
    (squad / "docs/decisions/ADR-20240115-use-postgres.md").unlink()

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert (_index(squad)["counter"], _index(squad)["padding"]) == (11, 6)


# --------------------------------------------------------------------------- with an index


def _move_task_to_an_undeclared_folder(root: Path) -> None:
    (root / "attic").mkdir()
    shutil.move(root / _TASK, root / "attic/TASK-000003-implement-auth.md")

    _point_the_task_entry_at(root, "attic/TASK-000003-implement-auth.md")


def _point_the_task_entry_at(root: Path, path: str) -> None:
    index = _index(root)
    for value in index["items"].values():
        if value["path"] in (_TASK, "attic/TASK-000003-implement-auth.md"):
            value["path"] = path
    (root / ".squads.json").write_text(json.dumps(index), encoding="utf-8")


async def test_an_indexed_file_where_no_type_lives_is_refused_and_moving_it_back_completes(
    squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    original = (squad / ".squads.json").read_bytes()
    _move_task_to_an_undeclared_folder(squad)
    before = _md(squad)
    monkeypatch.chdir(squad)

    refused = await invoke(["migrate", "up"])

    out = " ".join(refused.output.split())
    assert refused.exit_code == 1, refused.output
    assert "attic/TASK-000003-implement-auth.md" in out
    assert "its type lives in tasks/" in out
    assert "override" not in out
    assert _sq_commands(out[out.index("no migration has run") :]) == ["`sq migrate up`"]
    assert _stamp(squad) == "0.14" and _md(squad) == before
    shutil.move(squad / "attic/TASK-000003-implement-auth.md", squad / _TASK)
    again = await invoke(["migrate", "up"])
    assert again.exit_code == 1, "the rebuilt index dropped the entry, so the file is unseen"
    assert "holds no entry for them" in " ".join(again.output.split())
    (squad / ".squads.json").write_bytes(original)
    assert (await invoke(["migrate", "up"])).exit_code == 0


def _forget_the_milestone(root: Path) -> None:
    index = _index(root)
    index["items"] = {k: v for k, v in index["items"].items() if v["path"] != _MILE}
    (root / ".squads.json").write_text(json.dumps(index), encoding="utf-8")


def _incident_override(root: Path) -> None:
    _put(
        root,
        ".overrides/workflow.toml",
        f'# squads:override-base:{__version__}\n[items.incident]\nprefix = "INC"\n'
        'folder = "incidents"\nlifecycle = "guide"\n',
    )


def _unindexed_incident(root: Path) -> None:
    _incident_override(root)
    _put(
        root,
        "incidents/INC-000030-x.md",
        _ITEM.format(id="INC-30", seq=30, type="incident", status="Draft"),
    )


_UNKNOWN_TO_THE_INDEX: dict[str, tuple[Callable[[Path], None], str]] = {
    "the-first-item-of-a-bundled-type": (_forget_the_milestone, _MILE),
    "the-first-item-of-a-custom-type": (_unindexed_incident, "incidents/INC-000030-x.md"),
}


@pytest.mark.parametrize("row", _UNKNOWN_TO_THE_INDEX)
async def test_a_file_named_for_an_item_where_a_type_lives_with_no_entry_is_refused(
    row: str, squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    apply, named = _UNKNOWN_TO_THE_INDEX[row]
    apply(squad)
    before = _md(squad)
    monkeypatch.chdir(squad)

    refused = await invoke(["migrate", "up"])

    out = " ".join(refused.output.split())
    assert refused.exit_code == 1, refused.output
    assert named in out and "holds no entry for them" in out
    assert "a squads release that reads schema v0.14 (v0.14.0 is one)" in out
    assert _sq_commands(out[out.index("no migration has run") :]) == ["`sq migrate up`"]
    assert _stamp(squad) == "0.14" and _md(squad) == before


async def test_once_the_stamped_release_has_indexed_the_file_the_run_completes(
    squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    original = _index(squad)
    _forget_the_milestone(squad)
    monkeypatch.chdir(squad)
    assert (await invoke(["migrate", "up"])).exit_code == 1

    (squad / ".squads.json").write_text(json.dumps(original), encoding="utf-8")
    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert _stamp(squad) == SCHEMA_VERSION


# --------------------------------------------------------------------------- the invariants


@pytest.mark.parametrize("corpus", sorted(p.name for p in _CORPUS_DIR.iterdir() if p.is_dir()))
async def test_both_questions_pass_over_every_aged_corpus(corpus: str, tmp_path: Path) -> None:
    root = tmp_path / corpus
    shutil.copytree(_CORPUS_DIR / corpus, root)
    paths = _paths_at(root)
    store = IndexStore(paths.index_path, paths.lock_path)
    built, result = await plan_reconcile(
        paths.squad_dir, store, paths.config.schema_version, squads_version="9"
    )

    refusal = _corpus_fit.corpus_fit_refusal(
        built,
        bundled_spec(),
        paths.squad_dir,
        had_index=result.had_index,
        override_path=None,
        reader="a release",
    )

    assert result == ReconcileResult()
    assert refusal is None


_STRAYS_WITH_AN_INDEX: dict[str, Callable[[Path], None]] = {
    "archived": _archived_item,
    "backup-copy": _backup_copy,
    "another-tools-record": _numbered_record_of_another_tool,
    "unreadable-look-alike": _unreadable_look_alike,
}


@pytest.mark.parametrize("stray", _STRAYS_WITH_AN_INDEX)
async def test_with_an_index_no_run_the_checks_let_through_is_refused_by_the_trailing_repair(
    stray: str, squad: Path
) -> None:
    _STRAYS_WITH_AN_INDEX[stray](squad)
    before = set(_md(squad))

    run = await Service(_paths_at(squad)).run_pending_migrations()

    assert run.repair is not None and run.repair.unreadable == []
    assert before <= set(_md(squad))


async def test_a_copy_under_a_non_item_name_in_a_folder_the_index_never_held_is_the_known_limit(
    squad: Path,
) -> None:
    """Seen by neither question; left to the report `repair` makes after the stamp."""
    _forget_the_milestone(squad)
    shutil.move(squad / _MILE, squad / "milestones/ship.md")
    # the folder has no item-named file and no entry, so nothing is refused and nothing is lost
    run = await Service(_paths_at(squad)).run_pending_migrations()

    assert run.applied
    assert (squad / "milestones/ship.md").exists()


# --------------------------------------------------------------------------- vocabulary check


def _override(root: Path, body: str) -> None:
    _put(root, ".overrides/workflow.toml", f"# squads:override-base:{__version__}\n{body}")


def _edit_task(root: Path, old: str, new: str) -> None:
    text = (root / _TASK).read_text(encoding="utf-8")
    assert old in text, old
    (root / _TASK).write_text(text.replace(old, new, 1), encoding="utf-8")


def _drop_review_type(root: Path) -> None:
    kept = sorted(t for t in bundled_spec().items if t != "review")
    _override(root, f"[selected]\nitems = {kept!r}\n")


def _reprefix_task(root: Path) -> None:
    _override(root, '[items.task]\nprefix = "WORK"\n')


def _refolder_task(root: Path) -> None:
    _override(root, '[items.task]\nfolder = "work"\n')


def _shrink_priority(root: Path) -> None:
    _edit_task(root, "status: InProgress", "status: InProgress\npriority: high")
    _override(
        root,
        '[collections.priority]\nlabel = "Priority"\nordered = true\n'
        'badges = [{ code = "urgent", label = "Urgent" }]\n',
    )


def _undeclared_status_no_override(root: Path) -> None:
    _edit_task(root, "status: InProgress", "status: Triaged")


def _undeclared_type_no_override(root: Path) -> None:
    _edit_task(root, "type: task", "type: zzz")


def _undeclared_subentity_status(root: Path) -> None:
    _edit_task(root, "status: Todo", "status: Bogus")


#: row -> (apply, text naming the offending item or file, how the remedy is applied by hand)
_VOCABULARY_REFUSALS: dict[str, tuple[Callable[[Path], None], str, Callable[[Path], None]]] = {
    "override-drops-a-type-the-corpus-uses": (
        _drop_review_type,
        "REV-6",
        lambda r: (r / ".overrides/workflow.toml").unlink(),
    ),
    "override-re-prefixes-a-type-that-has-items": (
        _reprefix_task,
        "TASK-000003",
        lambda r: (r / ".overrides/workflow.toml").unlink(),
    ),
    "override-re-folders-a-type-that-has-items": (
        _refolder_task,
        "TASK-000003",
        lambda r: (r / ".overrides/workflow.toml").unlink(),
    ),
    "override-shrinks-a-badge-collection-a-value-names": (
        _shrink_priority,
        "TASK-3",
        lambda r: (r / ".overrides/workflow.toml").unlink(),
    ),
    "no-override-undeclared-status": (
        _undeclared_status_no_override,
        "TASK-3",
        lambda r: _edit_task(r, "status: Triaged", "status: InProgress"),
    ),
    "no-override-undeclared-subentity-status": (
        _undeclared_subentity_status,
        "TASK-3",
        lambda r: _edit_task(r, "status: Bogus", "status: Todo"),
    ),
    "no-override-undeclared-type": (
        _undeclared_type_no_override,
        "TASK-3",
        lambda r: _edit_task(r, "type: zzz", "type: task"),
    ),
}


@pytest.mark.parametrize("row", _VOCABULARY_REFUSALS)
async def test_the_service_refuses_a_corpus_that_does_not_fit_before_any_item_file_changes(
    row: str, squad: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    apply, named, remedy = _VOCABULARY_REFUSALS[row]
    apply(squad)
    before = _md(squad)
    runs: list[str] = []

    def _count(m: Any) -> Any:
        async def _run(ctx: Any) -> Any:
            runs.append(m.to_schema)
            return await m.run(ctx)

        return dataclasses.replace(m, run=_run)

    from squads._migrations import _registry

    monkeypatch.setattr(_maintenance, "MIGRATIONS", [_count(m) for m in _registry.MIGRATIONS])
    svc = Service(_paths_at(squad), spec=_spec_for(squad))

    with pytest.raises(Exception, match="no migration has run") as excinfo:
        await svc.run_pending_migrations()

    message = " ".join(str(excinfo.value).split())
    assert named in message
    assert runs == []
    assert _stamp(squad) == "0.14" and _md(squad) == before
    assert _sq_commands(message) == ["`sq migrate up`"]
    assert ("override" in message) == row.startswith("override")
    remedy(squad)
    assert (await Service(_paths_at(squad), spec=_spec_for(squad)).run_pending_migrations()).applied


def _spec_for(root: Path) -> Any:
    from squads._rendering._engine import invalidate_squad_dir
    from squads._workflow import load_workflow_spec

    invalidate_squad_dir(_paths_at(root).squad_dir)
    return load_workflow_spec(squad_dir=_paths_at(root).squad_dir)


@pytest.mark.parametrize("row", _VOCABULARY_REFUSALS)
async def test_the_cli_refuses_the_same_corpus_with_exit_1_and_the_remedy_completes_it(
    row: str, squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    apply, named, remedy = _VOCABULARY_REFUSALS[row]
    apply(squad)
    before = _md(squad)
    monkeypatch.chdir(squad)

    refused = await invoke(["migrate", "up"])

    out = " ".join(refused.output.split())
    assert refused.exit_code == 1, refused.output
    assert named in out
    assert _sq_commands(out[out.index("no migration has run") :]) == ["`sq migrate up`"]
    assert not {"`sq workflow lint`", "`sq repair`", "`sq check`"} & set(_sq_commands(out))
    assert _stamp(squad) == "0.14" and _md(squad) == before
    remedy(squad)
    again = await invoke(["migrate", "up"])
    assert again.exit_code == 0, again.output
    assert _stamp(squad) == SCHEMA_VERSION


@pytest.mark.parametrize("row", _VOCABULARY_REFUSALS)
async def test_every_row_the_check_refuses_is_refused_later_with_the_check_stubbed_out(
    row: str, squad: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    apply, _, _ = _VOCABULARY_REFUSALS[row]
    apply(squad)
    monkeypatch.setattr(_maintenance, "corpus_fit_refusal", lambda *a, **k: None)

    with pytest.raises(Exception):  # noqa: B017 - any refusal at all is the claim
        await Service(_paths_at(squad), spec=_spec_for(squad)).run_pending_migrations()

    assert _stamp(squad) == "0.14"


_CONSISTENT_OVERRIDES: dict[str, str] = {
    "a-type-declared-with-no-items": (
        '[items.incident]\nprefix = "INC"\nfolder = "incidents"\nlifecycle = "guide"\n'
    ),
    "a-ref-kind-added": '[ref_kinds.mirrors]\nlabel = "Mirrors"\nhint = "mirror"\n',
}


@pytest.mark.parametrize("row", _CONSISTENT_OVERRIDES)
async def test_an_override_consistent_with_the_corpus_completes(
    row: str, squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    _override(squad, _CONSISTENT_OVERRIDES[row])
    monkeypatch.chdir(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert _stamp(squad) == SCHEMA_VERSION


async def test_an_override_that_conflicts_only_with_a_stale_entry_completes(
    squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    """The file's own type and status are declared; only the index entry says otherwise."""
    _override(squad, _CONSISTENT_OVERRIDES["a-ref-kind-added"])
    index = _index(squad)
    for value in index["items"].values():
        if value["path"] == _TASK:
            value["type"], value["status"] = "zzz", "Nope"
    (squad / ".squads.json").write_text(json.dumps(index), encoding="utf-8")
    monkeypatch.chdir(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert _stamp(squad) == SCHEMA_VERSION


async def test_an_override_declaring_a_type_of_its_own_with_an_item_completes_at_0_14(
    squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    _unindexed_incident(squad)
    index = _index(squad)
    index["items"]["30"] = {
        "sequence_id": 30,
        "type": "incident",
        "title": "T",
        "slug": "s",
        "status": "Draft",
        "path": "incidents/INC-000030-x.md",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }
    index["counter"] = 30
    (squad / ".squads.json").write_text(json.dumps(index), encoding="utf-8")
    monkeypatch.chdir(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output


# --------------------------------------------------------------------------- loading refusals


def _bad_toml(root: Path) -> None:
    _put(root, ".overrides/workflow.toml", "[items.broken\nnot toml ===")


def _fails_validation(root: Path) -> None:
    _override(root, '[items.task]\nlifecycle = "no-such-lifecycle"\n')


def _bad_playbook(root: Path) -> None:
    _incident_override(root)
    _put(root, ".overrides/playbook.toml", f"# squads:override-base:{__version__}\n[types.nope\n")


_LOADING: dict[str, tuple[Callable[[Path], None], str]] = {
    "workflow-override-not-toml": (_bad_toml, "workflow.toml"),
    "workflow-override-fails-spec-validation": (_fails_validation, "workflow.toml"),
    "playbook-override-fails-beside-a-valid-workflow-override": (_bad_playbook, "playbook.toml"),
}


@pytest.mark.parametrize("row", _LOADING)
async def test_an_override_that_does_not_load_stops_the_run_before_the_index_is_touched(
    row: str, squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    apply, file = _LOADING[row]
    apply(squad)
    index_before = (squad / ".squads.json").read_bytes()
    files_before = _md(squad)
    monkeypatch.chdir(squad)

    refused = await invoke(["migrate", "up"])

    out = " ".join(refused.output.split())
    assert refused.exit_code == 1, refused.output
    assert file in out
    assert set(_sq_commands(out)) == {"`sq migrate up`"}
    assert (squad / ".squads.json").read_bytes() == index_before
    assert _md(squad) == files_before and _stamp(squad) == "0.14"
    shutil.rmtree(squad / ".overrides")
    assert (await invoke(["migrate", "up"])).exit_code == 0


async def test_the_service_carries_the_playbook_override_the_bypass_builder_used_to_drop(
    squad: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from squads._cli import _common

    _incident_override(squad)
    _put(
        squad,
        ".overrides/playbook.toml",
        f'# squads:override-base:{__version__}\n[types.incident]\noverview = "An incident."\n'
        'lifecycle = "Draft -> Active"\ncommands = ["sq create incident"]\n'
        'roles = [{ slug = "qa", authors = true }]\n',
    )
    monkeypatch.chdir(squad)
    from dataclasses import replace

    from squads._context import bind_context, get_context

    bind_context(replace(get_context(), client_cwd=squad))

    svc = _common._build_bypass_fallback_service(bundled_fallback=False)

    assert "incident" in svc.playbook.types


async def test_repair_still_falls_back_to_the_bundled_spec_for_an_override_that_does_not_load(
    squad: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import replace

    from squads._cli import _common
    from squads._context import bind_context, get_context

    _bad_toml(squad)
    monkeypatch.chdir(squad)
    bind_context(replace(get_context(), client_cwd=squad))

    svc = _common._build_bypass_fallback_service()

    assert svc.spec is bundled_spec()


# --------------------------------------------------------------------------- stopped runs


def _pre_0_7_squad_with_an_override(root: Path) -> None:
    _override(root, '[ref_kinds.mirrors]\nlabel = "Mirrors"\nhint = "mirror"\n')


async def test_a_run_stopped_on_a_pre_0_7_squad_with_an_override_completes_when_re_run(
    tmp_path: Path, frozen_time: object, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    root = tmp_path / "v0_5"
    shutil.copytree(_CORPUS_DIR / "v0_5", root)
    _pre_0_7_squad_with_an_override(root)
    _edit_in(root, _TASK, "status: InProgress", "status: Triaged")
    monkeypatch.chdir(root)

    first = await invoke(["migrate", "up"])
    assert first.exit_code == 1, first.output
    assert _stamp(root) == "0.5"
    assert not any(v.get("id", "").startswith("UNRESOLVED") for v in _index(root)["items"].values())
    _edit_in(root, _TASK, "status: Triaged", "status: InProgress")

    second = await invoke(["migrate", "up"])

    assert second.exit_code == 0, second.output
    assert _stamp(root) == SCHEMA_VERSION


async def test_the_second_route_an_unreadable_file_then_the_fix_completes_when_re_run(
    tmp_path: Path, frozen_time: object, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    root = tmp_path / "v0_5"
    shutil.copytree(_CORPUS_DIR / "v0_5", root)
    _pre_0_7_squad_with_an_override(root)
    bug = next((root / "bugs").glob("BUG-*.md"))
    good = bug.read_bytes()
    bug.write_bytes(good + b"\xff")
    monkeypatch.chdir(root)

    first = await invoke(["migrate", "up"])
    assert first.exit_code == 1, first.output
    assert not any(v.get("id", "").startswith("UNRESOLVED") for v in _index(root)["items"].values())
    bug.write_bytes(good)

    second = await invoke(["migrate", "up"])

    assert second.exit_code == 0, second.output
    assert _stamp(root) == SCHEMA_VERSION


def _edit_in(root: Path, rel: str, old: str, new: str) -> None:
    text = (root / rel).read_text(encoding="utf-8")
    assert old in text, (rel, old)
    (root / rel).write_text(text.replace(old, new, 1), encoding="utf-8")


# --------------------------------------------------------------------------- the release named


_SCHEMA_FIXTURES = [
    ("v0_3", "0.3"),
    ("v0_4", "0.4"),
    ("v0_5", "0.5"),
    ("v0_7", "0.7"),
    ("v0_8", "0.8"),
    ("v0_10", "0.10"),
    ("v0_11", "0.11"),
    ("v0_14", "0.14"),
]


@pytest.mark.parametrize(("corpus", "schema"), _SCHEMA_FIXTURES)
async def test_a_refusal_names_a_release_that_reads_the_squads_schema_not_the_last_sync(
    corpus: str, schema: str, tmp_path: Path, frozen_time: object
) -> None:
    from squads._migrations._registry import MIGRATIONS

    root = tmp_path / corpus
    shutil.copytree(_CORPUS_DIR / corpus, root)
    _archived_item(root)
    _no_index(root)
    synced = tomllib.loads((root / ".squads.toml").read_text(encoding="utf-8"))["squads_version"]

    with pytest.raises(Exception, match="no migration has run") as excinfo:
        await Service(_paths_at(root)).run_pending_migrations()

    message = " ".join(str(excinfo.value).split())
    named = re.search(rf"reads schema v{re.escape(schema)} \(v([\d.]+) is one\)", message)
    assert named, message
    assert any(m.version == named[1] and m.to_schema == schema for m in MIGRATIONS)
    assert f"v{synced}" not in message or synced == named[1]


# --------------------------------------------------------------------------- spellings of a folder


def _spec_with_override(root: Path, body: str) -> Any:
    _override(root, body)
    return _spec_for(root)


_FOLDER_SPELLINGS = {
    "trailing-slash": "incidents/",
    "leading-dot-slash": "./incidents",
    "both": "./incidents/",
    "nested": "ops/incidents/",
}


@pytest.mark.parametrize("state", ["indexed", "no-index"])
@pytest.mark.parametrize("spelling", _FOLDER_SPELLINGS)
async def test_a_declared_folder_spelled_with_a_slash_or_dot_completes(
    spelling: str, state: str, squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    folder = _FOLDER_SPELLINGS[spelling]
    spec = _spec_with_override(
        squad, f'[items.incident]\nprefix = "INC"\nfolder = "{folder}"\nlifecycle = "guide"\n'
    )
    await Service(_paths_at(squad), spec=spec).create("incident", "One", author="dev-agent")
    if state == "no-index":
        _no_index(squad)
    monkeypatch.chdir(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert _stamp(squad) == SCHEMA_VERSION


# --------------------------------------------------------------------------- a hand-edited type


async def test_a_hand_edited_type_with_no_override_is_not_refused_as_a_spec_change(
    squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    bug = next((squad / "bugs").glob("BUG-*.md"))
    bug.write_text(bug.read_text(encoding="utf-8").replace("type: bug", "type: task", 1), "utf-8")
    monkeypatch.chdir(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert _stamp(squad) == SCHEMA_VERSION
    assert "override" not in result.output


async def test_the_same_edit_on_a_squad_with_an_override_is_refused_naming_it(
    squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    _override(squad, _CONSISTENT_OVERRIDES["a-ref-kind-added"])
    bug = next((squad / "bugs").glob("BUG-*.md"))
    bug.write_text(bug.read_text(encoding="utf-8").replace("type: bug", "type: task", 1), "utf-8")
    monkeypatch.chdir(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 1, result.output
    assert ".overrides/workflow.toml" in result.output


# --------------------------------------------------------------------------- odd prefixes


_ODD_PREFIXES = {"underscore": "MY_INC", "leading-digit": "2FA"}


@pytest.mark.parametrize("prefix", _ODD_PREFIXES)
async def test_with_no_index_an_odd_prefix_item_is_recognised_and_the_run_completes(
    prefix: str, squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    code = _ODD_PREFIXES[prefix]
    spec = _spec_with_override(
        squad, f'[items.incident]\nprefix = "{code}"\nfolder = "incidents"\nlifecycle = "guide"\n'
    )
    await Service(_paths_at(squad), spec=spec).create("incident", "One", author="dev-agent")
    _no_index(squad)
    monkeypatch.chdir(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert f"{code}-" in result.output
    assert _stamp(squad) == SCHEMA_VERSION
    assert len(_index(squad)["items"]) == 12


async def test_a_declared_prefix_outside_the_walks_shape_is_refused_by_the_second_question(
    squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    spec = _spec_with_override(
        squad, '[items.incident]\nprefix = "v1.0"\nfolder = "incidents"\nlifecycle = "guide"\n'
    )
    await Service(_paths_at(squad), spec=spec).create("incident", "One", author="dev-agent")
    _no_index(squad)
    monkeypatch.chdir(squad)

    refused = await invoke(["migrate", "up"])

    out = " ".join(refused.output.split())
    assert refused.exit_code == 1, refused.output
    assert "v1.0-" in out and "holds no entry for them" in out
    assert not (squad / ".squads.json").exists()
    assert _stamp(squad) == "0.14"


@pytest.mark.parametrize("prefix", _ODD_PREFIXES)
async def test_with_an_index_a_second_odd_prefix_item_gains_an_entry_and_the_first_is_refreshed(
    prefix: str, squad: Path
) -> None:
    code = _ODD_PREFIXES[prefix]
    spec = _spec_with_override(
        squad, f'[items.incident]\nprefix = "{code}"\nfolder = "incidents"\nlifecycle = "guide"\n'
    )
    svc = Service(_paths_at(squad), spec=spec)
    first = (await svc.create("incident", "One", author="dev-agent")).item
    index = _index(squad)
    for value in index["items"].values():
        if value["sequence_id"] == first.sequence_id:
            value["title"] = "stale"
    (squad / ".squads.json").write_text(json.dumps(index), encoding="utf-8")
    _put(
        squad,
        f"incidents/{code}-000031-second.md",
        _ITEM.format(id=f"{code}-31", seq=31, type="incident", status="Draft"),
    )

    run = await Service(_paths_at(squad), spec=spec).run_pending_migrations()

    assert run.reconcile is not None and run.reconcile.indexed == (f"{code}-31",)
    titles = {v["sequence_id"]: v["title"] for v in _index(squad)["items"].values()}
    assert titles[first.sequence_id] == "One"
    assert 31 in titles


@pytest.mark.parametrize("name", ["my_notes-1-x.md", "3d-2-models.md"])
async def test_a_look_alike_under_the_wider_walk_shape_with_no_id_is_passed_over(
    name: str, squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    _put(squad, f"docs/{name}", "---\ntitle: notes\n---\nx\n")
    _no_index(squad)
    monkeypatch.chdir(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert len(_index(squad)["items"]) == 11


@pytest.mark.parametrize("prefix", _ODD_PREFIXES)
async def test_an_odd_prefix_item_with_its_entry_completes(
    prefix: str, squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    code = _ODD_PREFIXES[prefix]
    spec = _spec_with_override(
        squad, f'[items.incident]\nprefix = "{code}"\nfolder = "incidents"\nlifecycle = "guide"\n'
    )
    await Service(_paths_at(squad), spec=spec).create("incident", "One", author="dev-agent")
    monkeypatch.chdir(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output


# --------------------------------------------------------------------------- remedies on screen


async def test_moving_a_file_back_is_enough_when_its_folder_holds_another_indexed_item(
    squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    svc = Service(_paths_at(squad))
    await svc.create("milestone", "Second", author="dev-agent")
    index = _index(squad)
    entry = next(v for v in index["items"].values() if v["path"] == _MILE)
    entry["path"] = "attic/MILE-000011-ship-the-auth-module.md"
    (squad / ".squads.json").write_text(json.dumps(index), encoding="utf-8")
    _put(squad, entry["path"], (squad / _MILE).read_bytes())
    (squad / _MILE).unlink()
    monkeypatch.chdir(squad)

    refused = await invoke(["migrate", "up"])

    out = " ".join(refused.output.split())
    assert refused.exit_code == 1, refused.output
    assert "move each file into the folder its type lives in, then re-run" in out
    assert "rebuild" not in out
    shutil.move(squad / entry["path"], squad / _MILE)
    assert (await invoke(["migrate", "up"])).exit_code == 0


async def test_the_refusal_says_what_the_rebuild_dropped(
    squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    index = _index(squad)
    entry = next(v for v in index["items"].values() if v["path"] == _MILE)
    entry["path"] = "attic/MILE-000011-ship-the-auth-module.md"
    (squad / ".squads.json").write_text(json.dumps(index), encoding="utf-8")
    monkeypatch.chdir(squad)
    # the entry's file is gone and the milestone file sits unindexed where a type lives

    refused = await invoke(["migrate", "up"])

    out = " ".join(refused.output.split())
    assert refused.exit_code == 1, refused.output
    assert "The index was rebuilt first (dropped MILE-11" in out


async def test_an_index_with_no_items_points_at_removing_it(
    squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    index = _index(squad)
    index["items"] = {}
    (squad / ".squads.json").write_text(json.dumps(index), encoding="utf-8")
    monkeypatch.chdir(squad)

    refused = await invoke(["migrate", "up"])

    out = " ".join(refused.output.split())
    assert refused.exit_code == 1, refused.output
    assert "removing the index file lets this run read the tree" in out
    (squad / ".squads.json").unlink()
    assert (await invoke(["migrate", "up"])).exit_code == 0
